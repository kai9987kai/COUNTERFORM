"""Behavioral safeguards for the separate v0.2 scientific protocol."""
import importlib.util
import json

import numpy as np
import pytest


def _engine():
    assert importlib.util.find_spec("counterform.v2") is not None, "v0.2 scientific protocol is missing"
    from counterform.v2 import engine
    return engine


def test_v2_protocol_exists_with_original_configuration_boundary():
    engine = _engine()
    assert engine.validate_config({"world": "memory"})["world"] == "memory"
    for patch in ({"seed": True}, {"budget": 9}, {"noise": float("nan")}, {"protocol": "0.2.0"}):
        with pytest.raises(ValueError):
            engine.validate_config(patch)


def test_all_compositions_fit_measured_force_balance_including_drag():
    engine = _engine()
    observations = [engine.simulate_observation("unmodelled", 11, w, 1.8, 0., i)
                    for i, w in enumerate((4.6, 6.8, 8.0))]
    models, particles = engine.fit_ensemble(observations, 0.)
    assert {m["name"] for m in models} == {"linear", "cubic", "friction", "drag", "cubic_friction",
                                        "cubic_drag", "friction_drag", "cubic_friction_drag"}
    combined = next(m for m in models if m["name"] == "cubic_friction_drag")
    assert combined["fit_rmse"] < 1e-6
    assert combined["parameters"]["drag"] == pytest.approx(3.2, abs=1e-4)
    assert len(particles) == 24
    assert sum(p["weight"] for p in particles) == pytest.approx(1.)


def test_fixed_physical_grid_and_linear_limit_and_drag_response():
    engine = _engine()
    grid = engine.design_grid()
    assert len(grid) == 30
    assert grid == engine.design_grid()
    linear = {"k": 36., "c": .5, "alpha": 0., "friction": 0., "drag": 0.}
    assert engine.frequency_response(linear, [6.], 1.5)[0] == pytest.approx(.5, rel=1e-9)
    assert engine.frequency_response({**linear, "drag": 3.2}, [6.], 1.5)[0] < .5
    # Allowed low damping can exceed 20m in the unqualified approximation;
    # do not silently clip that response or fail the entire study.
    low_damping = {**linear, "c": .015, "friction": .001}
    assert engine.frequency_response(low_damping, [6.], 2.)[0] > 20.


def test_decision_selector_values_decision_information_over_large_nuisance_variance():
    engine = _engine()
    # A/B differ strongly on nuisance, while C/D alter the best design.
    weights = np.full(4, .25)
    losses = np.array([[0., 1.], [0., 1.], [1., 0.], [1., 0.]])
    predictions = np.array([[0., 10., 0., 10.], [0., 0., 1., 1.]])
    rows = engine.score_candidates(weights, losses, predictions, np.array([.03, .03]))
    assert np.argmax([r["disagreement"] for r in rows]) == 0
    assert np.argmax([r["decision_gain"] for r in rows]) == 1


def test_cvar_respects_fractional_worst_particle_mass():
    engine = _engine()
    # The worst atom has 10% mass, then half the next atom completes the tail.
    actual = engine.weighted_cvar(np.array([[10.], [4.], [0.]]), np.array([.1, .2, .7]), .2)
    assert actual[0] == pytest.approx(7.)


@pytest.fixture(scope="module")
def result():
    return _engine().run_study({"seed": 42, "world": "cubic", "strategy": "counterform", "budget": 2, "noise": .01})


def test_result_retains_candidates_dual_audit_recommendation_and_controls(result):
    r = result
    json.dumps(r, allow_nan=False)
    assert r["version"] == r["protocol"] == "0.2.0"
    assert len(r["models"]) == 8
    assert len(r["design_grid"]) == 30
    assert r["decision"]["particle_count"] == 24
    assert r["recommendation"]["status"] in ("candidate", "abstain")
    for model in r["models"]:
        assert model["adequate"] == (model["force_passed"] and model["forecast_passed"])
        assert len(model["audit_trials"]) == 2
    candidate_rows = r["experiments"][1]["candidates"]
    assert len(candidate_rows) == 15
    assert sum(row["selected"] for row in candidate_rows) == 1
    assert all(set(("risk_before", "risk_after", "decision_gain", "disagreement", "fantasy_count")) <= row.keys()
               for row in candidate_rows)
    assert r["validation"]["solver_relative_error"] < 1e-4
    assert len(r["validation"]["solver_checks"]) == 2
    assert all(c["common_oracle_rms"] <= c["baseline_rms"] + 1e-10 or r["oracle"]["common_grid_index"] is not None
               for c in r["challenges"])


def test_audit_cannot_change_frozen_selection_or_use_cross_candidate_passes(monkeypatch, result):
    engine = _engine()
    original = engine.audit_models
    def reject(*args, **kwargs):
        original(*args, **kwargs)
        for i, model in enumerate(args[0]):
            model.update(force_passed=i == 0, forecast_passed=i == 1, adequate=False)
    monkeypatch.setattr(engine, "audit_models", reject)
    r = engine.run_study(result["config"])
    assert r["design"] == result["design"]
    assert r["experiments"] == result["experiments"]
    assert r["recommendation"]["status"] == "abstain"
    assert r["recommendation"]["selected_control"] == "no_absorber"


def test_memory_observations_have_no_hidden_state_and_exact_replay():
    engine = _engine()
    a = engine.simulate_observation("memory", 4, 6.2, 1.4, .01, 1)
    assert set(a) == {"t", "x", "v", "a", "force"}
    assert a == engine.simulate_observation("memory", 4, 6.2, 1.4, .01, 1)


def test_coupled_acceleration_obeys_primary_force_balance():
    engine = _engine()
    parameters = {"k": 36., "c": .3, "alpha": 0., "friction": 0., "drag": 0.}
    design = engine.design_grid()[19]
    trajectory = engine._simulate(parameters, 5.7, 1.5, [design])
    x, v = trajectory["x"][0], trajectory["v"][0]
    coupling = design["stiffness"] * (x - trajectory["absorber"][0]) + design["damping"] * (v - trajectory["absorber_v"][0])
    assert trajectory["a"][0] == pytest.approx(trajectory["force"] - 36. * x - .3 * v - coupling, abs=1e-10)


def test_forecast_solver_failure_is_finite_explicit_rejection(monkeypatch):
    engine = _engine()
    observation = engine.simulate_observation("linear", 7, 4.85, 2.3, 0., 100)
    models, _ = engine.fit_ensemble([observation], 0.)
    def fail(*args, **kwargs):
        raise RuntimeError("deliberate integration failure")
    monkeypatch.setattr(engine, "_simulate", fail)
    engine.audit_models(models, [{"frequency": 4.85, "amplitude": 2.3, "trace": observation}], 0.)
    assert not any(m["adequate"] or m["forecast_passed"] for m in models)
    assert all(m["audit_trials"][0]["forecast_error"] == "deliberate integration failure" for m in models)
    json.dumps(models, allow_nan=False)


def test_control_arms_share_initial_experiment_and_random_menu_is_uniform_mechanism(result):
    engine = _engine()
    for strategy in ("passive", "random", "active", "counterform"):
        chosen = engine._choose_experiment(None, strategy, 0, np.random.default_rng(1), set(), .01, engine.design_grid())
        assert chosen[:3] == (3.4, .35, 0.)
    # Replaying RNG state replays selection; no model weight ranks the random arm.
    args = (result["decision"]["particles"], "random", 1)
    first = engine._choose_experiment(*args, np.random.default_rng(19), {(3.4, .35)}, .01, engine.design_grid())
    second = engine._choose_experiment(*args, np.random.default_rng(19), {(3.4, .35)}, .01, engine.design_grid())
    assert first == second
    assert sum(row["selected"] for row in first[4]) == 1


def test_common_oracle_does_not_rank_an_infeasible_baseline_above_feasible_designs():
    engine = _engine()
    assert hasattr(engine, "choose_common_oracle"), "actual oracle chooser must expose feasibility selection"
    # Baseline RMS1 violates a peak constraint. Design0 costs more RMS but is
    # the only constraint-feasible control; design1 is lower RMS and infeasible.
    oracle = engine.choose_common_oracle(np.array([[2., .5], [2., .5]]), np.array([True, False]), [1., 1.], False)
    assert oracle["control"] == "absorber"
    assert oracle["common_grid_index"] == 0
    assert oracle["common_reduction_pct"] == pytest.approx(-100.)
    assert oracle["common_constraint_feasible"]


def test_common_oracle_has_no_winner_when_all_controls_are_infeasible():
    engine = _engine()
    assert hasattr(engine, "choose_common_oracle"), "actual oracle chooser must expose infeasible outcome"
    oracle = engine.choose_common_oracle(np.array([[2.], [2.]]), np.array([False]), [1., 1.], False)
    assert oracle["control"] == "none"
    assert oracle["common_grid_index"] is None
    assert oracle["common_reduction_pct"] is None
    assert oracle["rms_per_challenge"] == [None, None]
    assert not oracle["common_constraint_feasible"]


def test_cubic_first_branch_is_not_skipped_between_log_scan_points():
    engine = _engine()
    parameters = {"k": 5.238505351109361, "c": .158321691990931, "alpha": 696.2353080309489,
                  "friction": 0., "drag": 0.}
    response = engine.frequency_response(parameters, [3.9716644978666853], .5773743957002031)[0]
    assert response == pytest.approx(.0794966678392, rel=1e-10)


def test_near_fold_positive_lobe_is_solved_rather_than_snapped_to_stationary_point():
    from scipy.optimize import brentq
    engine = _engine()
    p = {"k": 5.238505351109361, "c": .158321691990931, "alpha": 696.2353080309489,
         "friction": 0., "drag": 0.}
    omega = 3.9716644978666853
    offset, cubic, damping = p["k"] - omega ** 2, .75 * p["alpha"], p["c"] * omega
    critical = np.sqrt((-2 * offset - np.sqrt(offset ** 2 - 3 * damping ** 2)) / (3 * cubic))
    def squared_force(response):
        return (offset * response + cubic * response ** 3) ** 2 + (damping * response) ** 2
    amplitude = np.sqrt(squared_force(critical)) * (1 - 1e-12)
    expected = brentq(lambda response: squared_force(response) - amplitude ** 2, 0., critical, xtol=1e-14)
    actual = engine._first_balance_root(p, omega, amplitude)
    assert actual == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("family", ["cubic", "friction", "drag", "cubic_friction", "cubic_drag", "friction_drag", "cubic_friction_drag"])
def test_nonlinear_surrogate_paths_match_independent_dense_first_crossing(family):
    from scipy.optimize import brentq
    engine = _engine()
    p = {"k": 5.238505351109361, "c": .158321691990931,
         "alpha": 696.2353080309489 if "cubic" in family else 0.,
         "friction": .0001 if "friction" in family else 0., "drag": .02 if "drag" in family else 0.}
    omega, amplitude = 3.9716644978666853, .5773743957002031
    def balance(response):
        elastic = (p["k"] - omega ** 2) * response + .75 * p["alpha"] * response ** 3
        dissipative = p["c"] * omega * response + 4 * p["friction"] / np.pi * np.tanh(omega * response / .04)
        dissipative += 8 * p["drag"] / (3 * np.pi) * (omega * response) ** 2
        return elastic ** 2 + dissipative ** 2 - amplitude ** 2
    dense = np.linspace(0., 1., 100001)
    index = np.flatnonzero(balance(dense) >= 0.)[0]
    expected = brentq(balance, dense[index - 1], dense[index], xtol=1e-14)
    actual = engine.frequency_response(p, [omega], amplitude)[0]
    assert actual == pytest.approx(expected, rel=1e-9)


def test_selector_records_schedule_origin_separately_from_diagnostic_menu(result):
    engine = _engine()
    warmup = engine._choose_experiment(None, "counterform", 0, np.random.default_rng(1), set(), .01, engine.design_grid())
    assert warmup[-1].get("selection_origin") == "shared_warmup"
    assert warmup[-1].get("selected_id") is None
    passive = engine._choose_experiment(result["decision"]["particles"], "passive", 1, np.random.default_rng(1),
                                        {(3.4, .35)}, .01, engine.design_grid())
    assert passive[-1].get("selection_origin") == "passive_schedule"
    assert passive[-1].get("selected_id") is None
    assert passive[-1].get("menu_role") == "diagnostic_only"
    assert not any(row["selected"] for row in passive[4])
