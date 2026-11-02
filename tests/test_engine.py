"""Behavioral checks for finite synthetic identification and held-out design.

These tests protect physical response, rejection, replay and input boundaries;
no test asserts that the COUNTERFORM heuristic beats another strategy.
"""
import json
import math

import numpy as np
import pytest

from counterform.engine import (
    fit_models,
    frequency_response,
    run_study,
    simulate_observation,
    validate_config,
)


BASE = {"seed": 42, "world": "cubic", "strategy": "counterform", "budget": 3, "noise": 0.01}


def test_linear_response_matches_hand_calculated_resonance():
    # m=1, k=36, c=.5, omega=6, force=1.5 => |x|=1.5/(.5*6)=.5.
    response = frequency_response({"k": 36.0, "c": 0.5, "alpha": 0.0, "friction": 0.0}, [6.0], 1.5)
    assert response[0] == pytest.approx(0.5, rel=1e-10)
    assert frequency_response({"k": 36.0, "c": .5}, [0.0], 1.5)[0] == pytest.approx(1 / 24)


def test_observations_replay_and_contain_only_instrument_channels():
    a = simulate_observation("cubic", 19, 5.5, 1.2, 0.01, 0)
    b = simulate_observation("cubic", 19, 5.5, 1.2, 0.01, 0)
    assert a == b
    assert set(a) == {"t", "x", "v", "a", "force"}
    assert 100 < len(a["t"]) <= 500
    assert len({len(a[key]) for key in a}) == 1
    assert np.isfinite(np.asarray(list(a.values()))).all()


def test_noise_free_cubic_force_balance_recovers_coefficients_without_truth_metadata():
    observations = [simulate_observation("cubic", 7, frequency, 1.7, 0.0, i)
                    for i, frequency in enumerate([4.5, 6.0, 7.5])]
    models = fit_models(observations, noise=0.0)
    cubic = next(m for m in models if m["name"] == "cubic")
    assert cubic["parameters"]["alpha"] > 100
    assert cubic["weight"] > .99
    # Predict the observed physical balance, independently of coefficient truth.
    obs = observations[-1]
    p = cubic["parameters"]
    prediction = p["k"] * np.array(obs["x"]) + p["c"] * np.array(obs["v"]) + p["alpha"] * np.array(obs["x"]) ** 3
    measured_balance = np.array(obs["force"]) - np.array(obs["a"])
    assert np.linalg.norm(prediction - measured_balance) / np.linalg.norm(measured_balance) < 1e-5


@pytest.mark.parametrize("patch", [
    {"seed": -1}, {"seed": 2147483648}, {"seed": True}, {"seed": 1.2},
    {"budget": 1}, {"budget": 9}, {"budget": 3.0}, {"budget": False},
    {"noise": -0.01}, {"noise": .051}, {"noise": float("nan")}, {"noise": True},
    {"world": "unknown"}, {"strategy": "magic"}, {"extra": 1},
])
def test_standalone_config_rejects_invalid_or_ambiguous_inputs(patch):
    with pytest.raises(ValueError):
        validate_config({**BASE, **patch})


def test_config_accepts_extreme_valid_values_and_has_stable_defaults():
    assert validate_config({}) == {"seed": 42, "world": "cubic", "strategy": "counterform", "budget": 5, "noise": .01}
    result = validate_config({"seed": 2147483647, "budget": 8, "noise": .05, "world": "unmodelled", "strategy": "passive"})
    assert result["noise"] == .05


@pytest.fixture(scope="module")
def cubic_result():
    return run_study(BASE)


def test_study_replay_is_exact_and_progress_completes(cubic_result):
    messages = []
    replay = run_study(BASE, progress=lambda fraction, message: messages.append((fraction, message)))
    assert replay == cubic_result
    assert messages[-1][0] == 1.0
    assert all(0 <= value <= 1 for value, _ in messages)
    assert [value for value, _ in messages] == sorted(value for value, _ in messages)
    json.dumps(replay, allow_nan=False)


def test_results_have_real_measurements_controls_and_finite_heldout_metrics(cubic_result):
    r = cubic_result
    assert len(r["experiments"]) == BASE["budget"]
    assert all("a" in e["trace"] for e in r["experiments"])
    assert r["validation"]["held_out"] is True
    assert r["validation"]["solver_relative_error"] < 1e-4
    assert len(r["challenges"]) >= 3
    assert all(c["baseline_rms"] > 0 and c["design_rms"] > 0 and c["nominal_rms"] > 0 for c in r["challenges"])
    assert all(c["oracle_rms"] <= c["design_rms"] + 1e-9 for c in r["challenges"])
    assert 0 < r["design"]["mass_ratio"] <= .2
    assert len(r["playback"]["t"]) == len(r["playback"]["primary"])
    assert r["summary"]["best_model"] == "cubic"
    assert r["summary"]["adequate"] is True
    assert r["summary"]["reduction_pct"] == pytest.approx(100 * (1-r["summary"]["design_rms"]/r["summary"]["baseline_rms"]))


def test_omitted_physics_can_reject_every_model_despite_relative_weights():
    r = run_study({**BASE, "world": "unmodelled", "budget": 4, "noise": 0.0})
    assert not r["summary"]["adequate"]
    assert not any(m["adequate"] for m in r["models"])
    assert max(m["weight"] for m in r["models"]) > .9
    assert "reject" in r["summary"]["verdict"].lower()


@pytest.mark.parametrize("strategy", ["passive", "random", "active", "counterform"])
def test_strategies_honor_equal_experiment_and_design_budgets(strategy):
    r = run_study({**BASE, "world": "linear", "strategy": strategy, "budget": 2, "noise": .05, "seed": 0})
    assert len(r["experiments"]) == 2
    assert r["validation"]["design_grid_size"] == 30
    assert r["validation"]["audit_experiments"] == 2
    assert all(math.isfinite(c["reduction_pct"]) for c in r["challenges"])

def test_independent_audit_flags_cannot_tune_the_selected_design():
    # Changing audit support flags must not feed held-out observations back into search.
    from copy import deepcopy
    from counterform.engine import _design_grid, _search_design
    hypotheses = [
        {"name": "linear", "parameters": {"k": 25., "c": .3, "alpha": 0., "friction": 0.}, "weight": .5, "adequate": False},
        {"name": "cubic", "parameters": {"k": 49., "c": .3, "alpha": 0., "friction": 0.}, "weight": .5, "adequate": False},
    ]
    grid = _design_grid(hypotheses)
    selected_before_audit = _search_design(hypotheses, grid)
    hypotheses_with_audit = deepcopy(hypotheses)
    hypotheses_with_audit[0]["adequate"] = True
    selected_after_audit = _search_design(hypotheses_with_audit, grid)
    assert selected_after_audit == selected_before_audit
