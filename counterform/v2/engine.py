"""Finite composition/particle decision laboratory, separate from legacy evidence.

All weights, response likelihoods and audit thresholds are declared engineering
surrogates. They are not calibrated probabilities or physical qualification.
"""
from __future__ import annotations

import itertools
import math
from numbers import Real
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, lsq_linear, minimize_scalar

from .. import engine as legacy

VERSION = "0.2.0"
TIMES = legacy.TIMES
FREQUENCIES = legacy.FREQUENCIES
PRIMARY_MASS = 1.0
SMOOTH_VELOCITY = .04
DEFAULT_CONFIG = dict(legacy.DEFAULT_CONFIG)
TERMS = ("cubic", "friction", "drag")
FAMILIES = tuple(tuple(term for term, included in zip(TERMS, mask) if included)
                 for mask in itertools.product((False, True), repeat=3))
PARAMETERS = ("k", "c", "alpha", "friction", "drag")
LOWER = np.array([5., .015, 0., 0., 0.])
UPPER = np.array([80., 5., 1500., 3., 8.])
TRAIN_FREQUENCIES = np.linspace(3., 9., 13)
TRAIN_AMPLITUDES = (.75, 1.5, 2.)
GRID_ID = "physical-30-ref6-v1"
QUADRATURE_NODES = np.array([-math.sqrt(3.), 0., math.sqrt(3.)])
QUADRATURE_WEIGHTS = np.array([1 / 6, 2 / 3, 1 / 6])
AUDIT_PROTOCOL = ((4.85, 2.3), (7.85, .9))
RESPONSE_ROOT_LIMIT = 128.
ROOT_XTOL = 1e-13
FRICTION_DERIVATIVE_SAMPLES = 129
CHALLENGES = (
    {"name": "Shifted frequency", "frequency": 5.15, "amplitude": 1.25, "harmonic": .12,
     "tolerance": {"mass": 1., "stiffness": 1., "damping": 1.}},
    {"name": "High load and harmonic", "frequency": 6.55, "amplitude": 2.1, "harmonic": .22,
     "tolerance": {"mass": 1., "stiffness": 1., "damping": 1.}},
    {"name": "Component tolerance", "frequency": 7.45, "amplitude": 1.6, "harmonic": .17,
     "tolerance": {"mass": 1.08, "stiffness": .85, "damping": .8}},
)


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("config must be a dictionary")
    unknown = set(config) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError("unknown configuration fields: " + ", ".join(sorted(map(str, unknown))))
    result = {**DEFAULT_CONFIG, **config}
    for key, low, high in (("seed", 0, 2147483647), ("budget", 2, 8)):
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError(f"{key} must be an integer in [{low}, {high}]")
    noise = result["noise"]
    if isinstance(noise, bool) or not isinstance(noise, Real) or not math.isfinite(float(noise)) or not 0 <= noise <= .05:
        raise ValueError("noise must be a finite number in [0, 0.05]")
    result["noise"] = float(noise)
    if result["world"] not in ("linear", "cubic", "friction", "unmodelled", "memory"):
        raise ValueError("world must be linear, cubic, friction, unmodelled or memory")
    if result["strategy"] not in ("passive", "random", "active", "counterform"):
        raise ValueError("strategy must be passive, random, active or counterform")
    return result


def _world(world: str, seed: int) -> dict:
    parameters = legacy._world(world if world != "memory" else "linear", seed)
    return {**parameters, "memory_eta": 4.5 if world == "memory" else 0.,
            "memory_tau": .22 if world == "memory" else 1.}


def _restoring(parameters, x, v):
    return (parameters["k"] * x + parameters["c"] * v + parameters.get("alpha", 0.) * x ** 3
            + parameters.get("friction", 0.) * np.tanh(v / SMOOTH_VELOCITY)
            + parameters.get("drag", 0.) * np.abs(v) * v)


def _simulate(parameters, frequency, amplitude, designs=None, *, harmonic=0., tolerance=None, method="DOP853"):
    """Batch independent systems in one solve; memory is simulator-only state."""
    parameter_list = parameters if isinstance(parameters, list) else [parameters]
    count = len(designs) if designs is not None else len(parameter_list)
    if len(parameter_list) == 1:
        parameter_list = parameter_list * count
    p = {key: np.asarray([item.get(key, 1. if key == "memory_tau" else 0.) for item in parameter_list])
         for key in (*PARAMETERS, "memory_eta", "memory_tau")}
    coupled = designs is not None
    if coupled:
        factors = tolerance or {"mass": 1., "stiffness": 1., "damping": 1.}
        masses = np.asarray([d["mass"] * factors["mass"] for d in designs])
        stiffness = np.asarray([d["stiffness"] * factors["stiffness"] for d in designs])
        damping = np.asarray([d["damping"] * factors["damping"] for d in designs])
    dimension = 5 if coupled else 3
    def rhs(t, state):
        parts = state.reshape(dimension, count)
        x, v, z = parts[:3]
        drive = legacy._force(t, frequency, amplitude, harmonic)
        restoring = _restoring(p, x, v) + z
        relaxation = (p["memory_eta"] * v - z) / p["memory_tau"]
        if not coupled:
            return np.asarray([v, drive - restoring, relaxation]).ravel()
        y, vy = parts[3:]
        coupling = stiffness * (x - y) + damping * (v - vy)
        return np.asarray([v, drive - restoring - coupling, relaxation, vy, coupling / masses]).ravel()
    solution = solve_ivp(rhs, (0., 14.), np.zeros(dimension * count), t_eval=TIMES, method=method,
                         rtol=2e-8, atol=2e-10, max_step=.08)
    if not solution.success or not np.isfinite(solution.y).all():
        raise RuntimeError("v0.2 oscillator integration failed")
    parts = solution.y.reshape(dimension, count, len(TIMES))
    drive = legacy._force(TIMES, frequency, amplitude, harmonic)
    output = {"t": TIMES, "x": parts[0], "v": parts[1], "force": drive,
              "a": drive - _restoring({k: v[:, None] for k, v in p.items()}, parts[0], parts[1]) - parts[2]}
    if coupled:
        output.update(absorber=parts[3], absorber_v=parts[4])
        output["a"] -= stiffness[:, None] * (parts[0] - parts[3]) + damping[:, None] * (parts[1] - parts[4])
    return output


def simulate_observation(world, seed, frequency, amplitude, noise, sequence):
    clean = _simulate(_world(world, seed), frequency, amplitude)
    rng = np.random.default_rng(np.random.SeedSequence([seed, sequence, 1701]))
    scales = {"x": .1, "v": .75, "a": 4., "force": max(amplitude, .25)}
    result = {"t": TIMES.tolist()}
    for key, scale in scales.items():
        values = clean[key] if key == "force" else clean[key][0]
        result[key] = (values + rng.normal(0., noise * scale, len(TIMES))).tolist()
    return result


def _features(observations):
    x, v, balance = legacy._features(observations)
    return np.column_stack([x, v, x ** 3, np.tanh(v / SMOOTH_VELOCITY), np.abs(v) * v]), balance


def _fit(matrix, target, columns):
    chosen = matrix[:, columns]
    scale = np.maximum(np.linalg.norm(chosen, axis=0), 1e-12)
    fit = lsq_linear(chosen / scale, target, bounds=(LOWER[columns] * scale, UPPER[columns] * scale),
                     tol=1e-10, max_iter=150)
    if not fit.success:
        raise RuntimeError("v0.2 bounded model fitting did not converge")
    coefficients = np.zeros(5)
    coefficients[columns] = fit.x / scale
    return {key: float(value) for key, value in zip(PARAMETERS, coefficients)}


def fit_ensemble(observations, noise=.01):
    """Three deterministic residual-perturbation refits per finite family.

    The base fit plus two opposite block perturbations reflect sensitivity to
    measured data; these are deliberately not posterior/coverage intervals.
    """
    matrix, target = _features(observations)
    effective_count = max(20, 20 * len(observations))
    models, scores, particles = [], [], []
    block_signs = np.where((np.arange(len(target)) // 21) % 2, -1., 1.)
    for family in FAMILIES:
        name = "_".join(family) or "linear"
        columns = [0, 1] + [2 + TERMS.index(term) for term in family]
        parameters = _fit(matrix, target, columns)
        predicted = matrix @ np.array([parameters[key] for key in PARAMETERS])
        residual = target - predicted
        mse = float(np.mean(residual ** 2))
        score = effective_count * math.log(max(mse, 1e-16)) + len(columns) * math.log(effective_count)
        scores.append(score)
        equation = "m a + c v + k x" + "".join({"cubic": " + alpha x^3", "friction": " + f tanh(v/0.04)",
                                                 "drag": " + q |v|v"}[term] for term in family) + " = F"
        family_particles = []
        # Include a declared instrument-scale floor; it is sensitivity analysis,
        # not a calibrated noise reconstruction or errors-in-variables repair.
        perturbation = block_signs * np.maximum(np.abs(residual), .25 * noise)
        for variant in (0, -1, 1):
            fitted = parameters if variant == 0 else _fit(matrix, target + variant * perturbation, columns)
            item = {"family": name, "variant": variant, "parameters": fitted, "weight": 0.}
            family_particles.append(item)
            particles.append(item)
        intervals = {key: [min(p["parameters"][key] for p in family_particles),
                           max(p["parameters"][key] for p in family_particles)] for key in PARAMETERS}
        models.append({"name": name, "equation": equation, "parameters": parameters, "weight": 0.,
                       "fit_rmse": math.sqrt(mse), "complexity": len(columns), "audit_nrmse": 0.,
                       "forecast_nrmse": 0., "adequate": False, "force_passed": False,
                       "forecast_passed": False, "parameter_intervals": intervals, "audit_trials": []})
    relative = np.exp(-.5 * np.clip(np.asarray(scores) - min(scores), 0., 1400.))
    relative /= relative.sum()
    for model, value in zip(models, relative):
        model["weight"] = float(value)
        for particle in particles:
            if particle["family"] == model["name"]:
                particle["weight"] = float((.95 * value + .05 / len(models)) / 3)
    return models, particles


def design_grid():
    return [{"mass": mass, "stiffness": mass * (6. * ratio) ** 2,
             "damping": 2. * zeta * mass * 6. * ratio, "tuning_ratio": ratio,
             "mass_ratio": mass, "damping_ratio": zeta}
            for mass in (.08, .16) for ratio in (.75, .9, 1., 1.1, 1.25) for zeta in (.05, .15, .3)]


def _polynomial_stationary_points(elastic_offset, cubic, viscous, quadratic):
    """Positive extrema of E(R)^2+D(R)^2 without smooth friction.

    Its derivative divided by R is quartic. All positive real stationary
    points partition the polynomial balance into monotonic intervals, so a
    narrow positive lobe cannot disappear between response scan samples.
    """
    if cubic == 0. or elastic_offset >= 0.:
        return []
    if quadratic == 0.:
        discriminant = elastic_offset ** 2 - 3. * viscous ** 2
        if discriminant < 0.:
            return []
        root = math.sqrt(discriminant)
        points = [math.sqrt((-2. * elastic_offset + sign * root) / (3. * cubic)) for sign in (-1., 1.)]
    else:
        coefficients = [6. * cubic ** 2, 0., 4. * (2. * elastic_offset * cubic + quadratic ** 2),
                        6. * viscous * quadratic, 2. * (elastic_offset ** 2 + viscous ** 2)]
        roots = np.roots(coefficients)
        points = [float(root.real) for root in roots
                  if root.real > 0. and abs(root.imag) <= 1e-8 * max(1., abs(root.real))]
    return sorted(set(point for point in points if math.isfinite(point) and point > 0.))


def _first_balance_root(parameters, frequency, amplitude):
    """First polynomial root; first numerically isolated friction root.

    Smooth friction uses sampled and minimisation-refined analytic derivative
    extrema. That path is explicitly a qualified numerical approximation,
    not a guarantee that every possible narrow feature has been resolved.
    """
    omega = abs(float(frequency))
    applied = abs(float(amplitude))
    offset, cubic = parameters["k"] - omega ** 2, .75 * parameters.get("alpha", 0.)
    viscous = parameters["c"] * omega
    quadratic = 8. * parameters.get("drag", 0.) * omega ** 2 / (3. * math.pi)
    friction = 4. * parameters.get("friction", 0.) / math.pi
    slope = omega / SMOOTH_VELOCITY
    def equation(response):
        elastic = offset * response + cubic * response ** 3
        dissipative = viscous * response + quadratic * response ** 2 + friction * math.tanh(slope * response)
        return elastic ** 2 + dissipative ** 2 - applied ** 2
    def derivative(response):
        elastic = offset * response + cubic * response ** 3
        elastic_prime = offset + 3. * cubic * response ** 2
        smooth = math.tanh(slope * response)
        dissipative = viscous * response + quadratic * response ** 2 + friction * smooth
        dissipative_prime = viscous + 2. * quadratic * response + friction * slope * (1. - smooth ** 2)
        return 2. * (elastic * elastic_prime + dissipative * dissipative_prime)
    stationary = _polynomial_stationary_points(offset, cubic, viscous, quadratic)
    if friction > 0. and len(stationary) >= 2 and stationary[0] < RESPONSE_ROOT_LIMIT:
        # Adding positive smooth-friction dissipation increases the derivative.
        # Its negative portions can therefore only occur between the two
        # polynomial stationary points. Refine sampled minima there, then
        # bracket sign-changing derivative roots before solving the balance.
        low, high = stationary[0], min(stationary[-1], RESPONSE_ROOT_LIMIT)
        samples = np.linspace(low, high, FRICTION_DERIVATIVE_SAMPLES).tolist()
        values = [derivative(point) for point in samples]
        minimum_intervals = [(low, high)]
        minimum_intervals.extend((samples[i - 1], samples[i + 1]) for i in range(1, len(samples) - 1)
                                 if values[i] <= values[i - 1] and values[i] <= values[i + 1])
        for left, right in minimum_intervals:
            minimum = minimize_scalar(derivative, bounds=(left, right), method="bounded",
                                      options={"xatol": 1e-12, "maxiter": 64})
            if not minimum.success:
                raise RuntimeError("friction harmonic-balance extremum refinement failed")
            samples.append(float(minimum.x))
        samples = sorted(set(samples))
        values = [derivative(point) for point in samples]
        stationary = []
        for left, right, left_value, right_value in zip(samples, samples[1:], values, values[1:]):
            if left_value == 0.:
                stationary.append(left)
            if left_value * right_value < 0.:
                stationary.append(brentq(derivative, left, right, xtol=ROOT_XTOL))
    elif friction > 0.:
        # The no-friction polynomial is monotonic; the added positive
        # dissipative derivative preserves monotonicity.
        stationary = []
    low = 0.
    if applied == 0.:
        return 0.
    for high in [*(point for point in stationary if point < RESPONSE_ROOT_LIMIT), RESPONSE_ROOT_LIMIT]:
        value = equation(high)
        if value == 0.:
            return float(high)
        if value > 0.:
            return float(brentq(equation, low, high, xtol=ROOT_XTOL))
        low = high
    raise RuntimeError("harmonic balance root exceeds declared search bound")


def _equivalent(parameters, frequencies, amplitudes):
    """Baseline-orbit equivalents with stationary-point branch isolation."""
    omega, applied = np.broadcast_arrays(np.asarray(frequencies, dtype=float), np.asarray(amplitudes, dtype=float))
    k, c = parameters["k"], parameters["c"]
    alpha, friction, drag = (parameters.get(key, 0.) for key in ("alpha", "friction", "drag"))
    if alpha == friction == drag == 0.:
        return np.full_like(omega, k), np.full_like(omega, c)
    response = np.array([_first_balance_root(parameters, w, a) for w, a in zip(omega.flat, applied.flat)]).reshape(omega.shape)
    velocity = response * np.abs(omega)
    stiffness = k + .75 * alpha * response ** 2
    smooth_ratio = np.divide(np.tanh(velocity / SMOOTH_VELOCITY), velocity,
                             out=np.full_like(velocity, 1. / SMOOTH_VELOCITY), where=velocity != 0.)
    damping = c + 4. * friction * smooth_ratio / math.pi + 8. * drag * velocity / (3. * math.pi)
    return stiffness, damping


def frequency_response(parameters, frequencies, amplitude=1., design=None):
    omega = np.asarray(frequencies, dtype=float)
    stiffness, damping = _equivalent(parameters, omega, amplitude)
    dynamic = stiffness - omega ** 2 + 1j * damping * omega
    if design is not None:
        coupling = design["stiffness"] + 1j * omega * design["damping"]
        dynamic = dynamic + coupling - coupling ** 2 / (coupling - design["mass"] * omega ** 2)
    return (amplitude / np.maximum(np.abs(dynamic), 1e-10)).tolist()


def loss_matrix(particles, grid):
    omega, amplitudes = np.meshgrid(TRAIN_FREQUENCIES, TRAIN_AMPLITUDES)
    omega, amplitudes = omega.ravel(), amplitudes.ravel()
    coupling = np.array([d["stiffness"] + 1j * omega * d["damping"] for d in grid])
    absorber = coupling - coupling ** 2 / (coupling - np.array([d["mass"] for d in grid])[:, None] * omega ** 2)
    losses = []
    for particle in particles:
        k, c = _equivalent(particle["parameters"], omega, amplitudes)
        base = k - omega ** 2 + 1j * c * omega
        baseline_squared = np.mean((amplitudes / np.maximum(np.abs(base), 1e-10)) ** 2)
        candidate_squared = np.mean((amplitudes[None, :] / np.maximum(np.abs(base[None, :] + absorber), 1e-10)) ** 2, axis=1)
        losses.append(candidate_squared / max(baseline_squared, 1e-12))
    return np.asarray(losses)


def weighted_cvar(losses, weights, tail=.2):
    """Exact fractional-atom upper tail mean for each finite design column."""
    losses, weights = np.asarray(losses), np.asarray(weights)
    order = np.argsort(-losses, axis=0, kind="stable")
    sorted_loss = np.take_along_axis(losses, order, axis=0)
    sorted_weights = weights[order]
    before = np.cumsum(sorted_weights, axis=0) - sorted_weights
    taken = np.minimum(sorted_weights, np.maximum(tail - before, 0.))
    return np.sum(taken * sorted_loss, axis=0) / tail


def _decision(losses, weights):
    objective = .7 * weighted_cvar(losses, weights) + .3 * (weights @ losses)
    index = int(np.argmin(objective))
    return index, float(objective[index])


def score_candidates(weights, losses, predictions, noise_scales):
    """Finite generating-particle expected loss after the actual CVaR rule.

    Three Gaussian quadrature observations per generating particle are used.
    Negative estimated gains remain visible; no nonnegativity is imposed.
    """
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()
    losses, predictions = np.asarray(losses), np.asarray(predictions)
    current_index, _ = _decision(losses, weights)
    risk_before = float(weights @ losses[:, current_index])
    result = []
    for prediction, scale in zip(predictions, noise_scales):
        after = 0.
        for generator, mean in enumerate(prediction):
            for node, quadrature_weight in zip(QUADRATURE_NODES, QUADRATURE_WEIGHTS):
                outcome = mean + node * scale
                log_likelihood = -.5 * ((outcome - prediction) / scale) ** 2
                posterior = weights * np.exp(np.maximum(log_likelihood - log_likelihood.max(), -700.))
                posterior /= posterior.sum()
                selected, _ = _decision(losses, posterior)
                after += weights[generator] * quadrature_weight * losses[generator, selected]
        mean = float(weights @ prediction)
        # Absolute predicted peak variance makes the disagreement control
        # sensitive to nuisance variation independently of downstream loss.
        disagreement = float(weights @ (prediction - mean) ** 2)
        result.append({"disagreement": disagreement, "decision_gain": risk_before - float(after),
                       "risk_before": risk_before, "risk_after": float(after),
                       "fantasy_count": int(len(weights) * len(QUADRATURE_NODES))})
    return result


def _candidate_diagnostics(particles, grid, used, noise):
    pool = [(float(w), float(a)) for w in (3.5, 4.6, 5.7, 6.8, 8.) for a in (.45, 1., 1.8)
            if (w, a) not in used]
    weights = np.array([p["weight"] for p in particles])
    losses = loss_matrix(particles, grid)
    frequencies = np.array([w for w, _ in pool])
    amplitudes = np.array([a for _, a in pool])
    predictions = np.array([frequency_response(p["parameters"], frequencies, amplitudes) for p in particles]).T
    # Response-summary uncertainty is deliberately broader than instrument
    # position noise; neither this floor nor the likelihood is calibrated.
    scales = np.maximum(.05 * (predictions @ weights), max(.1 * noise, .002))
    scores = score_candidates(weights, losses, predictions, scales)
    return [{"id": f"w{w:g}-a{a:g}", "frequency": w, "amplitude": a, **score,
             "likelihood_scale": float(scale), "score": 0., "selected": False}
            for (w, a), score, scale in zip(pool, scores, scales)]


def _choose_experiment(particles, strategy, index, rng, used, noise, grid):
    selector = {"name": strategy, "tie_rule": "first in ascending frequency/amplitude menu order",
                "score_label": "expected generating-particle loss reduction" if strategy == "counterform"
                else "predicted peak-displacement variance" if strategy == "active" else "schedule/random control",
                "selection_origin": "shared_warmup" if index == 0 else "passive_schedule" if strategy == "passive" else "menu",
                "selected_id": None, "menu_role": "not_available" if index == 0 else "diagnostic_only" if strategy == "passive" else "selection"}
    if index == 0:
        selector.update(score_label="shared warmup schedule", tie_rule="fixed shared initial experiment")
        return 3.4, .35, 0., "Shared low-amplitude initial experiment.", [], selector
    rows = _candidate_diagnostics(particles, grid, used, noise)
    if strategy == "passive":
        selector["tie_rule"] = "fixed passive schedule; diagnostic menu does not select the experiment"
        return 3.4 + .13 * index, .35, 0., "Fixed low-amplitude passive schedule; menu scores are diagnostic only.", rows, selector
    if strategy == "random":
        selected = int(rng.integers(len(rows)))
        reason = "Uniform random experiment from the common remaining finite menu."
    else:
        key = "decision_gain" if strategy == "counterform" else "disagreement"
        selected = int(np.argmax([row[key] for row in rows]))
        reason = ("One-step fantasy expected decision-risk surrogate using the actual finite CVaR decision rule."
                  if strategy == "counterform" else "Predictive peak-displacement disagreement using the same particle ensemble.")
    for i, row in enumerate(rows):
        row["score"] = float(row["decision_gain"] if strategy == "counterform" else row["disagreement"] if strategy == "active" else 0.)
        row["selected"] = i == selected
    chosen = rows[selected]
    selector["selected_id"] = chosen["id"]
    return chosen["frequency"], chosen["amplitude"], chosen["score"], reason, rows, selector


def audit_models(models, audit, noise):
    force_threshold, forecast_threshold = .08 + 2. * noise, .15 + 3. * noise
    per_model_residuals, per_model_observed, per_model_forecasts = [[] for _ in models], [[] for _ in models], [[] for _ in models]
    for trial in audit:
        observation = trial["trace"]
        matrix, target = _features([observation])
        try:
            forecasts = _simulate([m["parameters"] for m in models], trial["frequency"], trial["amplitude"])["x"]
            forecast_error = None
        except RuntimeError as error:
            forecasts, forecast_error = None, str(error)
        observed = np.asarray(observation["x"])
        balance_scale = max(float(np.sqrt(np.mean(target ** 2))), .1)
        forecast_scale = max(float(np.sqrt(np.mean(observed ** 2))), .02)
        for index, model in enumerate(models):
            residual = matrix @ np.array([model["parameters"][k] for k in PARAMETERS]) - target
            force_error = float(np.sqrt(np.mean(residual ** 2)) / balance_scale)
            predicted_error = (float(np.sqrt(np.mean((forecasts[index] - observed) ** 2)) / forecast_scale)
                               if forecasts is not None else 1e6)
            model["audit_trials"].append({"frequency": trial["frequency"], "amplitude": trial["amplitude"],
                                          "force_nrmse": force_error, "forecast_nrmse": predicted_error,
                                          "force_passed": force_error <= force_threshold,
                                          "forecast_passed": predicted_error <= forecast_threshold,
                                          "forecast_error": forecast_error})
            per_model_residuals[index].append(residual)
            per_model_observed[index].append(target)
            per_model_forecasts[index].append(predicted_error)
    for index, model in enumerate(models):
        residual = np.concatenate(per_model_residuals[index])
        target = np.concatenate(per_model_observed[index])
        model["audit_nrmse"] = float(np.sqrt(np.mean(residual ** 2)) / max(float(np.sqrt(np.mean(target ** 2))), .1))
        model["forecast_nrmse"] = float(max(per_model_forecasts[index]))
        # Every trial must pass, and both criteria refer to this SAME fitted law.
        model["force_passed"] = all(t["force_passed"] for t in model["audit_trials"])
        model["forecast_passed"] = all(t["forecast_passed"] for t in model["audit_trials"])
        model["adequate"] = model["force_passed"] and model["forecast_passed"]


def _rms(values):
    return np.sqrt(np.mean(np.asarray(values)[..., TIMES >= 7.] ** 2, axis=-1))


def choose_common_oracle(rms_matrix, feasible, baseline_rms, baseline_feasible):
    """Select the common retrospective control from measured challenge arrays."""
    matrix, baseline = np.asarray(rms_matrix), np.asarray(baseline_rms)
    feasible_indices = np.flatnonzero(feasible)
    baseline_squared = float(np.mean(baseline ** 2))
    common_index = None
    common_squared = baseline_squared if baseline_feasible else math.inf
    if len(feasible_indices):
        best = int(feasible_indices[np.argmin(np.mean(matrix[:, feasible_indices] ** 2, axis=0))])
        candidate_squared = float(np.mean(matrix[:, best] ** 2))
        if candidate_squared < common_squared:
            common_index, common_squared = best, candidate_squared
    available = math.isfinite(common_squared)
    return {"common_grid_index": common_index, "feasible_count": int(np.sum(feasible)),
            "common_reduction_pct": 100. * (1. - math.sqrt(common_squared / baseline_squared)) if available else None,
            "rms_per_challenge": matrix[:, common_index].tolist() if common_index is not None else baseline.tolist() if available else [None] * len(baseline),
            "control": "absorber" if common_index is not None else "no_absorber" if available else "none",
            "common_constraint_feasible": available,
            "no_absorber_constraint_feasible": bool(baseline_feasible),
            "fallback": "no absorber is eligible only when its primary displacement satisfies every challenge limit; no eligible control yields none/null metrics",
            "scope": "retrospective pooled RMS minimum over all common constraint-feasible grid designs and an eligible no-absorber control"}


def _held_out(world, seed, selected, nominal, grid, recommended):
    truth = _world(world, seed)
    challenges, oracle_values, feasible, playback = [], [], np.ones(len(grid), dtype=bool), None
    baseline_feasible = True
    check_references = []
    for protocol in CHALLENGES:
        baseline = _simulate(truth, protocol["frequency"], protocol["amplitude"], harmonic=protocol["harmonic"])
        trajectories = _simulate(truth, protocol["frequency"], protocol["amplitude"], [selected, nominal] + grid,
                                 harmonic=protocol["harmonic"], tolerance=protocol["tolerance"])
        values = _rms(trajectories["x"])
        base_rms = float(_rms(baseline["x"])[0])
        baseline_feasible &= bool(np.max(np.abs(baseline["x"][0, TIMES >= 7.])) <= .5)
        peaks = np.max(np.abs(trajectories["x"][:, TIMES >= 7.]), axis=1)
        stroke = np.max(np.abs(trajectories["absorber"][:, TIMES >= 7.] - trajectories["x"][:, TIMES >= 7.]), axis=1)
        candidate_feasible = (peaks[2:] <= .5) & (stroke[2:] <= .65)
        feasible &= candidate_feasible
        oracle_values.append(values[2:])
        oracle_index = int(np.argmin(values[2:]))
        challenges.append({**protocol, "baseline_rms": base_rms, "design_rms": float(values[0]),
                           "nominal_rms": float(values[1]), "oracle_rms": float(values[oracle_index + 2]),
                           "oracle_grid_index": oracle_index, "reduction_pct": 100. * (1. - float(values[0]) / base_rms),
                           "constraint_violation": bool(peaks[0] > .5 or stroke[0] > .65),
                           "primary_peak": float(peaks[0]), "absorber_stroke_peak": float(stroke[0]),
                           "primary_peak_limit": .5, "absorber_stroke_limit": .65,
                           "recommended_rms": float(values[0]) if recommended else base_rms})
        if playback is None:
            playback = {"t": TIMES.tolist(), "baseline": baseline["x"][0].tolist(),
                        "primary": trajectories["x"][0].tolist(), "absorber": trajectories["absorber"][0].tolist(),
                        "challenge": protocol["name"]}
            check_references = [("baseline", baseline["x"][0]), ("selected", trajectories["x"][0])]
    oracle = choose_common_oracle(oracle_values, feasible, [c["baseline_rms"] for c in challenges], baseline_feasible)
    for index, challenge in enumerate(challenges):
        challenge["common_oracle_rms"] = oracle["rms_per_challenge"][index]
    checks = []
    protocol = CHALLENGES[0]
    for control, reference in check_references:
        independent = _simulate(truth, protocol["frequency"], protocol["amplitude"],
                                None if control == "baseline" else [selected], harmonic=protocol["harmonic"],
                                tolerance=protocol["tolerance"], method="Radau")
        discrepancy = float(np.linalg.norm(independent["x"][0] - reference) / max(np.linalg.norm(reference), 1e-12))
        checks.append({"control": control, "challenge": protocol["name"], "relative_error": discrepancy,
                       "methods": ["DOP853", "Radau"]})
    return challenges, playback, checks, oracle


def run_study(config: dict, progress: Callable | None = None) -> dict:
    config = validate_config(config)
    report = progress or (lambda fraction, message: None)
    report(.02, "Preparing v0.2 finite composition instruments")
    observations, experiments, ledger = [], [], []
    rng = np.random.default_rng(np.random.SeedSequence([config["seed"], 902]))
    grid, used, particles = design_grid(), set(), None
    for index in range(config["budget"]):
        frequency, amplitude, score, reason, candidates, selector = _choose_experiment(
            particles, config["strategy"], index, rng, used, config["noise"], grid)
        used.add((frequency, amplitude))
        trace = simulate_observation(config["world"], config["seed"], frequency, amplitude, config["noise"], index)
        observations.append(trace)
        models, particles = fit_ensemble(observations, config["noise"])
        experiments.append({"index": index + 1, "frequency": frequency, "amplitude": amplitude,
                            "score": score, "reason": reason, "weights": {m["name"]: m["weight"] for m in models},
                            "trace": trace, "selector": selector, "candidates": candidates})
        ledger.append({"kind": "experiment", "message": f"Experiment {index + 1}: {amplitude:g} N at {frequency:g} rad/s. {reason}"})
        report(.06 + .44 * (index + 1) / config["budget"], f"Acquired {index + 1}/{config['budget']} experiments")
    report(.54, "Freezing particle fits, common-grid design and nominal control before dual audit")
    losses = loss_matrix(particles, grid)
    weights = np.array([p["weight"] for p in particles])
    selected_index, objective = _decision(losses, weights)
    best = max(models, key=lambda m: m["weight"])
    nominal_losses = loss_matrix([{"parameters": best["parameters"]}], grid)
    nominal_index = int(np.argmin(nominal_losses[0]))
    selected = {**grid[selected_index], "objective": objective}
    nominal = {**grid[nominal_index], "objective": float(nominal_losses[0, nominal_index])}
    audit = [{"frequency": frequency, "amplitude": amplitude,
              "trace": simulate_observation(config["world"], config["seed"], frequency, amplitude, config["noise"], 100 + i)}
             for i, (frequency, amplitude) in enumerate(AUDIT_PROTOCOL)]
    audit_models(models, audit, config["noise"])
    adequate = any(m["adequate"] for m in models)
    reasons = []
    if not adequate:
        reasons.append("No single frozen fitted law passes both force-balance and free-running trajectory audits on every trial.")
    if objective >= 1.:
        reasons.append("Selected design does not beat the no-absorber normalised loss of 1 under the declared pre-challenge CVaR/mean rule.")
    recommended = not reasons
    recommendation = {"status": "candidate" if recommended else "abstain",
                      "selected_control": "absorber" if recommended else "no_absorber", "reasons": reasons,
                      "message": "Conditional conceptual candidate; finite diagnostics do not establish physical reliability." if recommended
                      else "Abstain from recommending the exploratory absorber; use the no-absorber control in the recommendation comparison."}
    report(.65, "Independent force/forecast audit and prediction-only recommendation frozen")
    challenges, playback, checks, oracle = _held_out(config["world"], config["seed"], selected, nominal, grid, recommended)
    baseline_rms = float(np.sqrt(np.mean([c["baseline_rms"] ** 2 for c in challenges])))
    design_rms = float(np.sqrt(np.mean([c["design_rms"] ** 2 for c in challenges])))
    verdict = ("A frozen fitted law passes both independent diagnostics; support remains conditional on these synthetic trials."
               if adequate else "All frozen fitted laws rejected by at least one independent diagnostic; the absorber remains exploratory.")
    decision = {"particle_count": len(particles), "grid_id": GRID_ID,
                "selection_rule": "0.7 upper weighted CVaR over worst 20% particle mass + 0.3 weighted mean loss; first grid minimum",
                "loss_definition": "mean approximate peak displacement squared over envelope / same particle no-absorber mean approximate peak displacement squared",
                "design_envelope": {"frequencies_rad_s": TRAIN_FREQUENCIES.tolist(), "amplitudes_N": list(TRAIN_AMPLITUDES),
                                    "harmonic": 0., "weights": "uniform over the 39 frequency/amplitude pairs"},
                "predicted_objective": objective, "predicted_mean_loss": float(weights @ losses[:, selected_index]),
                "recommendation_criterion": "same fitted law passes both audits on all trials AND predicted CVaR/mean objective < 1",
                "particle_construction": {"per_family": 3, "variants": [0, -1, 1], "block_samples": 21,
                                          "target_perturbation": "variant * alternating block sign * max(abs(base force residual), 0.25*noise)",
                                          "score_effective_count": max(20, 20 * config["budget"]),
                                          "family_score": "effective_count*log(MSE floor1e-16)+parameter_count*log(effective_count)",
                                          "weight_rule": "(0.95*relative family score weight+0.05/8)/3 per particle",
                                          "interpretation": "deterministic measured-data sensitivity particles and heuristic weights, not calibrated posterior or confidence intervals"},
                "surrogate": {"smoothing_velocity_m_s": SMOOTH_VELOCITY,
                              "response_root_upper_bound_metres": RESPONSE_ROOT_LIMIT, "root_absolute_tolerance_metres": ROOT_XTOL,
                              "branch_methods": {"polynomial_without_friction": "first positive root bracketed by all positive analytic/quartic stationary points of squared force balance",
                                                 "friction_mixtures": "first root isolated after analytic derivative sampling and bounded-minimum refinement within the possible nonmonotone interval; no global branch guarantee",
                                                 "monotonic_cases": "single positive balance root"},
                              "friction_extrema": {"derivative_samples": FRICTION_DERIVATIVE_SAMPLES,
                                                   "minimizer": "bounded scalar on whole stationary interval and each sampled local-minimum bracket",
                                                   "minimum_xatol_metres": 1e-12, "minimum_maxiter": 64},
                              "equivalent_stiffness": "k+0.75*alpha*response^2",
                              "equivalent_damping": "c+4*friction*tanh(response*omega/0.04)/(pi*response*omega) + 8*drag*response*omega/(3*pi); continuous ratio limit25 at zero velocity",
                              "coupling": "baseline-orbit equivalents reused across all absorber candidates; no coupled-orbit iteration"},
                "quadrature": {"nodes": QUADRATURE_NODES.tolist(), "weights": QUADRATURE_WEIGHTS.tolist(),
                               "observation": "scalar approximate baseline peak displacement",
                               "update": "fantasies reweight frozen current particles; actual acquisitions refit measured force channels, so this approximates subsequent inference",
                               "likelihood": "Gaussian around each particle peak prediction with common candidate scale",
                               "scale": "max(0.05*weighted predicted peak, 0.1*noise, 0.002 metres)",
                               "score": "current weighted generating-particle loss minus post-update selected-design generating-particle loss, averaged over particles and quadrature",
                               "negative_gains": "retained; finite approximation and CVaR decision rule need not have nonnegative gains"},
                "particles": particles, "particle_design_losses": losses.tolist(), "nominal_design": nominal}
    notes = ["Audit and challenge data never enter fitting, acquisition or design selection; designs freeze before both audits.",
             "Recommendation is frozen before nonlinear challenges and uses audit diagnostics plus pre-challenge predicted loss only.",
             "The same fixed physical 30-design grid is used across strategies, worlds and fantasy updates.",
             "Per-challenge oracle is unconstrained and retrospective; common oracle enforces all declared challenge constraints across one design.",
             "Gaussian response likelihood, particle perturbations, scoring effective count and audit thresholds are engineering conventions, not calibrated inference.",
             "Unmodelled is the historical world identifier; its cubic/friction/drag combination is represented in v0.2. Memory remains outside the instantaneous library."]
    ledger.extend([{"kind": "design", "message": f"Frozen selected design {selected_index + 1}/30 on {GRID_ID}; prediction objective {objective:.5g}."},
                   {"kind": "hypothesis", "message": verdict},
                   {"kind": "recommendation", "message": recommendation["message"]},
                   {"kind": "validation", "message": "Held-out nonlinear challenges retain adverse outcomes; two independent solver comparisons cover first-challenge baseline and selected trajectories only."}])
    result = {"version": VERSION, "protocol": VERSION, "config": config,
              "summary": {"reduction_pct": 100. * (1. - design_rms / baseline_rms), "baseline_rms": baseline_rms,
                          "design_rms": design_rms, "worst_reduction_pct": min(c["reduction_pct"] for c in challenges),
                          "adequate": adequate, "verdict": verdict, "best_model": best["name"],
                          "constraint_violations": sum(c["constraint_violation"] for c in challenges)},
              "models": models, "experiments": experiments, "design": selected, "design_grid": grid,
              "recommendation": recommendation, "decision": decision, "oracle": oracle,
              "response": {"frequencies": FREQUENCIES.tolist(), "baseline": frequency_response(best["parameters"], FREQUENCIES, 1.5),
                           "selected": frequency_response(best["parameters"], FREQUENCIES, 1.5, selected),
                           "nominal": frequency_response(best["parameters"], FREQUENCIES, 1.5, nominal),
                           "amplitude": 1.5, "kind": "stationary-point-qualified describing-function approximation, peak displacement"},
              "challenges": challenges, "playback": playback, "audit": audit, "ledger": ledger,
              "validation": {"solver_relative_error": max(c["relative_error"] for c in checks),
                             "solver_scope": "first held-out challenge baseline and selected displacement trajectories only; not all designs or challenges",
                             "solver_checks": checks, "solver_methods": ["DOP853", "Radau"], "held_out": True,
                             "audit_threshold": .08 + 2. * config["noise"], "force_threshold": .08 + 2. * config["noise"],
                             "forecast_threshold": .15 + 3. * config["noise"], "audit_experiments": 2,
                             "acquisition_experiments": config["budget"], "forecast_audit_experiments": 2,
                             "design_grid_size": len(grid), "design_grid_id": GRID_ID, "selected_grid_index": selected_index,
                             "nominal_grid_index": nominal_index, "known_primary_mass": 1., "rms_window_seconds": [7., 14.],
                             "integration": {"horizon_seconds": 14., "samples": len(TIMES), "rtol": 2e-8, "atol": 2e-10, "max_step": .08},
                             "coefficient_bounds": {key: [float(low), float(high)] for key, low, high in zip(PARAMETERS, LOWER, UPPER)},
                             "audit_normalisation": "force RMS/max(measured force-balance RMS,0.1N); forecast position RMS/max(measured position RMS,0.02m), entire14s",
                             "audit_aggregation": "every trial passes both criteria for the same fitted family; forecast_nrmse is worst trial",
                             "operational_budgets": {"acquisition_trials": config["budget"], "audit_trials": 2,
                                                     "challenge_conditions": 3, "designs_per_challenge": 32,
                                                     "independent_solver_checks": 2, "maximum_menu_candidates": 15,
                                                     "fantasies_per_candidate": 72}, "notes": notes},
              "ground_truth": {"disclosure": "Simulator-only parameters disclosed after selection/recommendation; never passed to learner.",
                               "primary_mass": 1., **_world(config["world"], config["seed"])},
              "limitations": ["Finite instrumented synthetic oscillator with directly measured x/v/a/force and known1kg mass; no hardware validation.",
                              "Eight predetermined instantaneous compositions and bounded coefficient fits; no unrestricted symbolic or neural discovery.",
                              "Errors-in-variables bias is unresolved; parameter intervals are sensitivity ranges, not confidence intervals.",
                              "One-step risk acquisition uses approximate peak response, heuristic weights and three-point quadrature; it is not exact Bayesian value of information.",
                              "Fantasy reweighting holds current particles fixed, while actual acquisitions refit all instrument data; the hypothetical inference update is approximate.",
                              "Polynomial harmonic balance partitions stationary points numerically; smooth-friction branch isolation uses sampled/refined extrema and has no global lowest-branch guarantee.",
                              "Baseline-orbit harmonic equivalents reused under absorber coupling can miss jumps, hysteresis, transient effects and orbit changes.",
                              "Fixed audit thresholds are uncalibrated engineering diagnostics; represented worlds may fail and omitted memory may pass.",
                              "Equal acquisition counts do not equal computational budgets; all arms archive the same diagnostic candidate calculations.",
                              "Pooled outcomes can hide negative challenge reductions. Narrow grids/protocols and a transient7–14s RMS window do not establish reliability.",
                              "No-absorber recommendation fallback is an experimental control, not a claim that physical operation without an absorber is safe.",
                              "Conceptual limits do not provide manufacturing, fatigue, stress, stability or safety qualification."]}
    report(1., "v0.2 study complete")
    return result
