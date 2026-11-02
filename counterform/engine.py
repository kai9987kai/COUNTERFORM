"""Finite, instrumented oscillator research; all numbers are computed locally.

The learner functions consume sensor channels or fitted models only. Hidden
world coefficients are confined to the simulator and final truth disclosure.
The acquisition scores are heuristics, not Bayesian information gain.
"""
from __future__ import annotations

import math
from numbers import Real
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, lsq_linear

VERSION = "0.1.0"
PRIMARY_MASS = 1.0
SMOOTH_VELOCITY = 0.04
NAMES = ("linear", "cubic", "friction")
DEFAULT_CONFIG = {"seed": 42, "world": "cubic", "strategy": "counterform", "budget": 5, "noise": 0.01}
EQUATIONS = {
    "linear": "m a + c v + k x = F",
    "cubic": "m a + c v + k x + alpha x^3 = F",
    "friction": "m a + c v + k x + f tanh(v / 0.04) = F",
}
TIMES = np.linspace(0.0, 14.0, 421)
FREQUENCIES = np.linspace(3.0, 9.0, 61)


def validate_config(config: dict) -> dict:
    """Reject ambiguous numeric inputs at the standalone public boundary."""
    if not isinstance(config, dict):
        raise ValueError("config must be a dictionary")
    unknown = set(config) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError("unknown configuration fields: " + ", ".join(sorted(map(str, unknown))))
    result = {**DEFAULT_CONFIG, **config}
    for key, low, high in (("seed", 0, 2147483647), ("budget", 2, 8)):
        value = result[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{key} must be an integer in [{low}, {high}]")
    noise = result["noise"]
    if isinstance(noise, bool) or not isinstance(noise, Real) or not math.isfinite(float(noise)) or not 0 <= noise <= .05:
        raise ValueError("noise must be a finite number in [0, 0.05]")
    result["noise"] = float(noise)
    if result["world"] not in ("linear", "cubic", "friction", "unmodelled"):
        raise ValueError("world must be linear, cubic, friction or unmodelled")
    if result["strategy"] not in ("passive", "random", "active", "counterform"):
        raise ValueError("strategy must be passive, random, active or counterform")
    return result


def _world(world: str, seed: int) -> dict:
    rng = np.random.default_rng(np.random.SeedSequence([seed, 8841]))
    return {
        "k": float(rng.uniform(33.0, 39.0)),
        "c": float(rng.uniform(.26, .40)),
        "alpha": float(rng.uniform(180., 260.)) if world in ("cubic", "unmodelled") else 0.,
        "friction": float(rng.uniform(.28, .40)) if world == "friction" else (.70 if world == "unmodelled" else 0.),
        "drag": 3.2 if world == "unmodelled" else 0.,
    }


def _force(t, frequency: float, amplitude: float, harmonic: float = 0.):
    return amplitude * (np.sin(frequency * t) + harmonic * np.sin(1.73 * frequency * t + .37))


def _restoring(x, v, parameters):
    return (parameters["k"] * x + parameters["c"] * v + parameters.get("alpha", 0.) * x ** 3
            + parameters.get("friction", 0.) * np.tanh(v / SMOOTH_VELOCITY)
            + parameters.get("drag", 0.) * np.abs(v) * v)


def _simulate(parameters: dict, frequency: float, amplitude: float, designs=None, *, harmonic=0., tolerance=None,
              method="DOP853"):
    """Integrate all finite designs together; each remains a separate system."""
    if designs is None:
        def rhs(t, state):
            x, v = state
            return [v, (_force(t, frequency, amplitude, harmonic) - _restoring(x, v, parameters)) / PRIMARY_MASS]
        solution = solve_ivp(rhs, (0., float(TIMES[-1])), [0., 0.], t_eval=TIMES, method=method,
                             rtol=2e-8, atol=2e-10, max_step=.08)
        if not solution.success or not np.isfinite(solution.y).all():
            raise RuntimeError("primary oscillator integration failed")
        x, v = solution.y
        applied = _force(TIMES, frequency, amplitude, harmonic)
        return {"t": TIMES, "x": x, "v": v, "a": (applied - _restoring(x, v, parameters)) / PRIMARY_MASS,
                "force": applied}
    factors = tolerance or {"mass": 1., "stiffness": 1., "damping": 1.}
    mass = np.asarray([d["mass"] * factors["mass"] for d in designs])
    stiffness = np.asarray([d["stiffness"] * factors["stiffness"] for d in designs])
    damping = np.asarray([d["damping"] * factors["damping"] for d in designs])
    count = len(designs)
    def rhs(t, state):
        x, v, y, vy = state.reshape(4, count)
        coupling = stiffness * (x - y) + damping * (v - vy)
        return np.asarray([v, (_force(t, frequency, amplitude, harmonic) - _restoring(x, v, parameters) - coupling) / PRIMARY_MASS,
                           vy, coupling / mass]).ravel()
    solution = solve_ivp(rhs, (0., float(TIMES[-1])), np.zeros(4 * count), t_eval=TIMES, method=method,
                         rtol=2e-8, atol=2e-10, max_step=.08)
    if not solution.success or not np.isfinite(solution.y).all():
        raise RuntimeError("coupled oscillator integration failed")
    states = solution.y.reshape(4, count, len(TIMES))
    return {"t": TIMES, "x": states[0], "v": states[1], "absorber": states[2], "absorber_v": states[3]}


def simulate_observation(world: str, seed: int, frequency: float, amplitude: float, noise: float, sequence: int) -> dict:
    """Synthetic instrument output; no coefficients or clean state are exposed."""
    clean = _simulate(_world(world, seed), frequency, amplitude)
    rng = np.random.default_rng(np.random.SeedSequence([seed, sequence, 1701]))
    scales = {"x": .1, "v": .75, "a": 4., "force": max(amplitude, .25)}
    output = {"t": clean["t"].tolist()}
    for key, scale in scales.items():
        output[key] = (clean[key] + rng.normal(0., noise * scale, len(TIMES))).tolist()
    return output


def _features(observations):
    x = np.concatenate([np.asarray(o["x"], dtype=float) for o in observations])
    v = np.concatenate([np.asarray(o["v"], dtype=float) for o in observations])
    balance = np.concatenate([np.asarray(o["force"], dtype=float) - PRIMARY_MASS * np.asarray(o["a"], dtype=float)
                              for o in observations])
    return x, v, balance


def _prediction(parameters, x, v):
    return (parameters["k"] * x + parameters["c"] * v + parameters.get("alpha", 0.) * x ** 3
            + parameters.get("friction", 0.) * np.tanh(v / SMOOTH_VELOCITY))


def fit_models(observations: list[dict], noise: float = .01) -> list[dict]:
    """Bounded force-balance least squares, scored with a BIC-style penalty.

    Relative weights are not calibrated posterior probabilities. Regressor
    noise causes errors-in-variables bias; independent audit tests adequacy.
    """
    x, v, balance = _features(observations)
    models, scores = [], []
    columns = {"linear": [x, v], "cubic": [x, v, x ** 3], "friction": [x, v, np.tanh(v / SMOOTH_VELOCITY)]}
    upper = {"linear": [80., 5.], "cubic": [80., 5., 1500.], "friction": [80., 5., 3.]}
    for name in NAMES:
        matrix = np.column_stack(columns[name])
        # Scaling avoids a tiny x^3 column making the fit ill-conditioned.
        scale = np.maximum(np.linalg.norm(matrix, axis=0), 1e-12)
        fit = lsq_linear(matrix / scale, balance, bounds=(np.asarray([5., .015] + ([0.] if name != "linear" else [])) * scale,
                                                        np.asarray(upper[name]) * scale), tol=1e-10, max_iter=100)
        if not fit.success:
            raise RuntimeError("bounded model fitting did not converge")
        coefficients = fit.x / scale
        parameters = {"k": float(coefficients[0]), "c": float(coefficients[1]), "alpha": 0., "friction": 0.}
        if name != "linear":
            parameters["alpha" if name == "cubic" else "friction"] = float(coefficients[2])
        residual = matrix @ coefficients - balance
        mse = float(np.mean(residual ** 2))
        # The numerical floor prevents exact arithmetic fits dividing by zero.
        score = len(balance) * math.log(max(mse, 1e-16)) + matrix.shape[1] * math.log(len(balance))
        scores.append(score)
        models.append({"name": name, "equation": EQUATIONS[name], "parameters": parameters,
                       "weight": 0., "fit_rmse": math.sqrt(mse), "audit_nrmse": 0., "adequate": False,
                       "complexity": matrix.shape[1]})
    relative = np.exp(-.5 * np.clip(np.asarray(scores) - min(scores), 0., 1400.))
    relative /= relative.sum()
    for model, weight in zip(models, relative):
        model["weight"] = float(weight)
    return models


def _equivalent(parameters: dict, frequency: np.ndarray, amplitude: float):
    k, c = parameters["k"], parameters["c"]
    alpha, friction = parameters.get("alpha", 0.), parameters.get("friction", 0.)
    if alpha == 0 and friction == 0:
        return np.full_like(frequency, k), np.full_like(frequency, c)
    stiffness, damping = [], []
    # Lowest positive harmonic-balance branch; nonlinear jump/hysteresis is
    # deliberately not claimed to be represented by this design approximation.
    grid = np.geomspace(1e-7, 10., 180)
    for omega in frequency:
        def balance(response):
            elastic = k + .75 * alpha * response ** 2 - PRIMARY_MASS * omega ** 2
            dissipative = c * omega + (4. / math.pi) * friction * np.tanh(response * omega / SMOOTH_VELOCITY) / np.maximum(response, 1e-12)
            return response ** 2 * (elastic ** 2 + dissipative ** 2) - amplitude ** 2
        values = balance(grid)
        crossings = np.flatnonzero(values >= 0.)
        if len(crossings):
            index = int(crossings[0])
            response = brentq(balance, 0. if index == 0 else grid[index-1], grid[index], xtol=1e-11)
        else:
            response = 10.
        stiffness.append(k + .75 * alpha * response ** 2)
        damping.append(c + 4. * friction * np.tanh(response * omega / SMOOTH_VELOCITY)
                       / (math.pi * max(response * omega, 1e-8)))
    return np.asarray(stiffness), np.asarray(damping)


def frequency_response(parameters: dict, frequencies, amplitude: float = 1., design: dict | None = None) -> list[float]:
    """Describing-function frequency-response approximation (peak metres)."""
    omega = np.asarray(frequencies, dtype=float)
    stiffness, damping = _equivalent(parameters, omega, amplitude)
    dynamic = stiffness - PRIMARY_MASS * omega ** 2 + 1j * damping * omega
    if design is not None:
        coupling = design["stiffness"] + 1j * omega * design["damping"]
        dynamic = dynamic + coupling - coupling ** 2 / (coupling - design["mass"] * omega ** 2)
    return (amplitude / np.maximum(np.abs(dynamic), 1e-10)).tolist()


def _design_grid(models):
    reference = math.sqrt(sum(m["weight"] * m["parameters"]["k"] for m in models) / PRIMARY_MASS)
    return [{"mass": mass, "stiffness": mass * (reference * ratio) ** 2,
             "damping": 2. * damping_ratio * mass * reference * ratio,
             "tuning_ratio": ratio, "mass_ratio": mass / PRIMARY_MASS,
             "damping_ratio": damping_ratio}
            for mass in (.08, .16) for ratio in (.75, .9, 1., 1.1, 1.25) for damping_ratio in (.05, .15, .3)]


def _search_design(models, grid, *, nominal=False):
    if nominal:
        used = [max(models, key=lambda model: model["weight"])]
    else:
        # Independent audit flags must never select the search hypotheses.
        used = [m for m in models if m["weight"] >= .025] or models
    weights = np.asarray([m["weight"] for m in used])
    weights /= weights.sum()
    # Describe nonlinear stiffness from the baseline orbit once, not once per grid entry.
    dynamic = []
    for model in used:
        k, c = _equivalent(model["parameters"], FREQUENCIES, 1.5)
        dynamic.append(k - PRIMARY_MASS * FREQUENCIES ** 2 + 1j * c * FREQUENCIES)
    scores = []
    for design in grid:
        coupling = design["stiffness"] + 1j * FREQUENCIES * design["damping"]
        absorber = coupling - coupling ** 2 / (coupling - design["mass"] * FREQUENCIES ** 2)
        worst = np.asarray([np.max(1.5 / np.maximum(np.abs(base + absorber), 1e-10)) / math.sqrt(2.) for base in dynamic])
        scores.append(float(.7 * worst.max() + .3 * (weights @ worst)))
    index = int(np.argmin(scores))
    return {**grid[index], "objective": scores[index]}, index


def _choose_experiment(models, strategy, index, rng, used):
    if index == 0:
        return 3.4, .35, 0., "Shared low-amplitude initial instrument experiment."
    if strategy == "passive":
        return 3.4 + .13 * index, .35, 0., "Fixed low-amplitude passive schedule."
    candidates = [(float(w), float(a)) for w in (3.5, 4.6, 5.7, 6.8, 8.0) for a in (.45, 1., 1.8) if (w, a) not in used]
    if strategy == "random":
        frequency, amplitude = candidates[int(rng.integers(len(candidates)))]
        return frequency, amplitude, 0., "Uniform random choice from the common finite experiment pool."
    # Exploration floor avoids treating an early point estimate as certainty;
    # it is a policy convention, not a calibrated probability distribution.
    weights = .9 * np.asarray([m["weight"] for m in models]) + .1 / len(models)
    grid = _design_grid(models)
    robust, _ = _search_design(models, grid)
    preferred = [_search_design([dict(m, weight=1.)], grid, nominal=True)[0] for m in models]
    scores = []
    for frequency, amplitude in candidates:
        responses = np.asarray([frequency_response(m["parameters"], [frequency], amplitude)[0] for m in models])
        mean = float(weights @ responses)
        disagreement = float(weights @ (responses - mean) ** 2) / max(mean ** 2, 1e-10)
        if strategy == "counterform":
            selected = np.asarray([frequency_response(m["parameters"], [frequency], amplitude, robust)[0] for m in models])
            own = np.asarray([frequency_response(m["parameters"], [frequency], amplitude, d)[0] for m, d in zip(models, preferred)])
            regret = np.maximum(selected - own, 0.) / np.maximum(responses, 1e-8)
            score = disagreement * (.15 + 5. * float(weights @ regret))
        else:
            score = disagreement
        scores.append(score)
    choice = int(np.argmax(scores))
    reason = ("Decision-sensitive predictive-disagreement heuristic: response disagreement weighted by predicted absorber regret."
              if strategy == "counterform" else "Predictive response disagreement with a fixed exploration floor.")
    return *candidates[choice], float(scores[choice]), reason


def _audit(models, observations, threshold):
    x, v, balance = _features(observations)
    scale = max(float(np.sqrt(np.mean(balance ** 2))), .1)
    for model in models:
        residual = _prediction(model["parameters"], x, v) - balance
        model["audit_nrmse"] = float(np.sqrt(np.mean(residual ** 2)) / scale)
        model["adequate"] = bool(model["audit_nrmse"] <= threshold)


def _rms(values):
    return np.sqrt(np.mean(np.asarray(values)[..., TIMES >= 7.] ** 2, axis=-1))


def _held_out(world, seed, selected, nominal, grid):
    truth = _world(world, seed)
    protocols = [
        {"name": "Shifted frequency", "frequency": 5.15, "amplitude": 1.25, "harmonic": .12,
         "tolerance": {"mass": 1., "stiffness": 1., "damping": 1.}},
        {"name": "High load and harmonic", "frequency": 6.55, "amplitude": 2.1, "harmonic": .22,
         "tolerance": {"mass": 1., "stiffness": 1., "damping": 1.}},
        {"name": "Component tolerance", "frequency": 7.45, "amplitude": 1.6, "harmonic": .17,
         "tolerance": {"mass": 1.08, "stiffness": .85, "damping": .8}},
    ]
    challenges, playback, comparison = [], None, None
    for protocol in protocols:
        kwargs = {key: protocol[key] for key in ("harmonic", "tolerance")}
        baseline = _simulate(truth, protocol["frequency"], protocol["amplitude"], harmonic=protocol["harmonic"])
        # Same solver, horizon and challenge for selected, nominal and every oracle grid member.
        trajectories = _simulate(truth, protocol["frequency"], protocol["amplitude"], [selected, nominal] + grid, **kwargs)
        values = _rms(trajectories["x"])
        base_rms = float(_rms(baseline["x"]))
        design_rms, nominal_rms = float(values[0]), float(values[1])
        primary_peak = float(np.max(np.abs(trajectories["x"][0, TIMES >= 7.])))
        stroke_peak = float(np.max(np.abs(trajectories["absorber"][0, TIMES >= 7.] - trajectories["x"][0, TIMES >= 7.])))
        violation = primary_peak > .5 or stroke_peak > .65
        oracle_index = int(np.argmin(values[2:]))
        challenges.append({**protocol, "baseline_rms": base_rms, "design_rms": design_rms, "nominal_rms": nominal_rms,
                           "oracle_rms": float(values[oracle_index+2]), "oracle_grid_index": oracle_index,
                           "reduction_pct": 100. * (1. - design_rms / base_rms), "constraint_violation": bool(violation),
                           "primary_peak": primary_peak, "absorber_stroke_peak": stroke_peak,
                           "primary_peak_limit": .5, "absorber_stroke_limit": .65})
        if playback is None:
            playback = {"t": TIMES.tolist(), "baseline": baseline["x"].tolist(), "primary": trajectories["x"][0].tolist(),
                        "absorber": trajectories["absorber"][0].tolist(), "challenge": protocol["name"]}
            comparison = (protocol, trajectories["x"][0].copy())
    protocol, reference = comparison
    independent = _simulate(truth, protocol["frequency"], protocol["amplitude"], [selected],
                            harmonic=protocol["harmonic"], tolerance=protocol["tolerance"], method="Radau")
    solver_error = float(np.linalg.norm(independent["x"][0] - reference) / max(np.linalg.norm(reference), 1e-12))
    return challenges, playback, solver_error


def run_study(config: dict, progress: Callable | None = None) -> dict:
    """Run a deterministic finite-model study; no file I/O, timestamps or IDs."""
    config = validate_config(config)
    report = progress or (lambda fraction, message: None)
    report(.02, "Preparing synthetic instruments")
    observations, experiments, ledger = [], [], []
    rng = np.random.default_rng(np.random.SeedSequence([config["seed"], 902]))
    used, models = set(), None
    for index in range(config["budget"]):
        frequency, amplitude, score, reason = _choose_experiment(models, config["strategy"], index, rng, used)
        used.add((frequency, amplitude))
        observation = simulate_observation(config["world"], config["seed"], frequency, amplitude, config["noise"], index)
        observations.append(observation)
        models = fit_models(observations, config["noise"])
        experiments.append({"index": index+1, "frequency": frequency, "amplitude": amplitude, "score": score, "reason": reason,
                            "weights": {m["name"]: m["weight"] for m in models}, "trace": observation})
        ledger.append({"kind": "experiment", "message": f"Experiment {index+1}: {amplitude:g} N at {frequency:g} rad/s. {reason}"})
        report(.06 + .45 * (index+1) / config["budget"], f"Acquired {index+1}/{config['budget']} experiments")
    ledger.append({"kind": "observation", "message": f"Fit uses {len(observations)*len(TIMES)} instrument samples of x, v, a and applied force; known primary mass is 1 kg."})
    report(.55, "Freezing the common finite absorber search before audit")
    grid = _design_grid(models)
    selected, selected_index = _search_design(models, grid)
    nominal, nominal_index = _search_design(models, grid, nominal=True)
    ledger.append({"kind": "design", "message": f"Selected absorber {selected_index+1}/{len(grid)} by a finite describing-function search, frozen before independent audit. This is an approximate conceptual design."})
    audit_protocol = [(4.85, 2.3), (7.85, .9)]
    audit = [simulate_observation(config["world"], config["seed"], frequency, amplitude, config["noise"], 100+i)
             for i, (frequency, amplitude) in enumerate(audit_protocol)]
    threshold = .08 + 2. * config["noise"]
    _audit(models, audit, threshold)
    adequate = any(m["adequate"] for m in models)
    best = max(models, key=lambda m: m["weight"])
    ledger.append({"kind": "hypothesis", "message": f"Relative fit weights favour {best['name']}; independent force-balance audit {'accepts at least one candidate' if adequate else 'rejects every candidate'}."})
    report(.65, "Independent audit evaluated against the frozen fits and design")
    report(.7, "Evaluating separate nonlinear held-out challenges and oracle controls")
    challenges, playback, solver_error = _held_out(config["world"], config["seed"], selected, nominal, grid)
    baseline_rms = float(np.sqrt(np.mean([c["baseline_rms"] ** 2 for c in challenges])))
    design_rms = float(np.sqrt(np.mean([c["design_rms"] ** 2 for c in challenges])))
    violations = sum(c["constraint_violation"] for c in challenges)
    verdict = ("At least one finite candidate passes the independent audit. Held-out results remain conditional on this synthetic challenge set."
               if adequate else "All candidate laws rejected by independent audit. The displayed design is exploratory and has no adequate model support.")
    ledger.append({"kind": "validation", "message": f"Three independent challenge conditions; selected-design DOP853/Radau relative trajectory discrepancy {solver_error:.3g}."})
    result = {
        "version": VERSION, "config": config,
        "summary": {"reduction_pct": 100. * (1. - design_rms / baseline_rms), "baseline_rms": baseline_rms,
                    "design_rms": design_rms, "worst_reduction_pct": min(c["reduction_pct"] for c in challenges),
                    "adequate": bool(adequate), "verdict": verdict, "best_model": best["name"],
                    "constraint_violations": violations},
        "models": models, "experiments": experiments, "design": selected,
        "response": {"frequencies": FREQUENCIES.tolist(),
                     "baseline": frequency_response(best["parameters"], FREQUENCIES, 1.5),
                     "selected": frequency_response(best["parameters"], FREQUENCIES, 1.5, selected),
                     "nominal": frequency_response(best["parameters"], FREQUENCIES, 1.5, nominal),
                     "amplitude": 1.5, "kind": "describing-function approximation, peak displacement"},
        "challenges": challenges,
        "validation": {"solver_relative_error": solver_error, "audit_threshold": threshold, "held_out": True,
                       "audit_experiments": len(audit), "design_grid_size": len(grid), "selected_grid_index": selected_index,
                       "nominal_grid_index": nominal_index, "known_primary_mass": PRIMARY_MASS,
                       "solver_methods": ["DOP853", "Radau"], "rms_window_seconds": [7., 14.],
                       "notes": ["Audit observations never enter fitting, acquisition, design search or coefficient updates; the selected design is frozen first.",
                                 "Held-out challenge settings are fixed and are never used for selection.",
                                 "Oracle is the retrospective unconstrained minimum within the same 30-design grid, separately for each challenge.",
                                 "Relative model weights use a BIC-style complexity penalty; weights do not prove adequacy.",
                                 "Design response is an approximation; nonlinear held-out simulation owns reported reductions.",
                                 "Solver agreement is measured on the first held-out selected-design trajectory, not every grid member."]},
        "audit": [{"frequency": frequency, "amplitude": amplitude, "trace": trace} for (frequency, amplitude), trace in zip(audit_protocol, audit)],
        "playback": playback, "ledger": ledger,
        "ground_truth": {"disclosure": "Simulator-only coefficients disclosed after design selection; never passed to the learner.",
                         "primary_mass": PRIMARY_MASS, **_world(config["world"], config["seed"])},
        "design_grid": grid,
        "limitations": [
            "Instrumented synthetic one-dimensional oscillator with known mass; this is not identification from video or physical hardware.",
            "Finite hand-authored candidate laws and bounded coefficient fits; no free-form symbolic discovery or learned neural model.",
            "COUNTERFORM uses a decision-sensitive predictive-disagreement heuristic, not exact Bayesian information gain or an established research benefit.",
            "Sensor-noise regression has errors-in-variables bias; relative model weights are not calibrated probabilities.",
            "Adequacy threshold is a fixed engineering diagnostic with a noise allowance, not a calibrated hypothesis test.",
            "Frequency-response search uses a lowest-branch describing-function approximation and can miss nonlinear jumps, transients and hysteresis.",
            "The finite design grid and three deterministic challenge protocols are narrow; reductions may be negative and do not establish deployment reliability.",
            "The 7–14 second RMS window retains transient effects; steady-state convergence is not established.",
            "Grid oracle knows the held-out simulator retrospectively and is a diagnostic, not an attainable acquisition strategy.",
            "Conceptual absorber parameters and displacement limits are illustrative; no manufacturing, fatigue, stability or safety qualification is provided.",
        ],
    }
    report(1., "Study complete")
    return result

