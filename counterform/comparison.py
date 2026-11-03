"""Descriptive comparisons of verified completed evidence; never efficacy claims."""
from __future__ import annotations

from copy import deepcopy
import math
from numbers import Real

from .evidence import canonical, verify_receipt
from .protocols import CONFIG_FIELDS, normalize_request, receipt_protocol


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f'Malformed finite metric: {name}')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'Metric must be positive: {name}')
    return value


def _same_metric(value, expected, name):
    actual = _number(value, name)
    if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8):
        raise ValueError(f'Stored metric disagrees with challenge evidence: {name}')


def _challenge_spec(challenge, name):
    spec = {'name': name}
    for key in ('frequency', 'amplitude', 'primary_peak_limit', 'absorber_stroke_limit'):
        spec[key] = _number(challenge.get(key), f'{name}.{key}', positive=True)
    spec['harmonic'] = _number(challenge.get('harmonic'), f'{name}.harmonic')
    tolerance = challenge.get('tolerance')
    if not isinstance(tolerance, dict) or set(tolerance) != {'mass', 'stiffness', 'damping'}:
        raise ValueError(f'Missing or malformed component tolerance settings: {name}')
    spec['tolerance'] = {key: _number(tolerance[key], f'{name}.tolerance.{key}', positive=True)
                         for key in ('mass', 'stiffness', 'damping')}
    return spec


def _physical_grid(result, validation):
    grid = result.get('design_grid')
    if not isinstance(grid, list) or not 1 <= len(grid) <= 128:
        raise ValueError('Missing, empty or unbounded physical design grid')
    if 'design_grid_size' in validation:
        declared = validation['design_grid_size']
        if type(declared) is not int or declared != 30 or len(grid) != declared:
            raise ValueError('Physical design grid does not match the declared 30-design budget')
    for index, design in enumerate(grid):
        if not isinstance(design, dict):
            raise ValueError('Malformed physical design grid entry')
        for key in ('mass', 'stiffness', 'damping'):
            _number(design.get(key), f'design_grid[{index}].{key}', positive=True)
        for key in ('mass_ratio', 'tuning_ratio', 'damping_ratio'):
            if key in design:
                _number(design[key], f'design_grid[{index}].{key}', positive=True)
    return grid


def _checked(receipt):
    verify_receipt(receipt)
    result = receipt['result']
    protocol = receipt_protocol(receipt)
    config = receipt['config']
    if not isinstance(config, dict) or set(config) != set(CONFIG_FIELDS):
        raise ValueError('Malformed complete study configuration')
    normalize_request({**config, 'protocol': protocol})
    challenges, summary = result.get('challenges'), result.get('summary')
    if not isinstance(challenges, list) or not 1 <= len(challenges) <= 32 or not isinstance(summary, dict):
        raise ValueError('Malformed challenge evidence or summary')
    names, baseline, selected, reductions, specs, violations = set(), [], [], [], [], 0
    for challenge in challenges:
        if not isinstance(challenge, dict):
            raise ValueError('Malformed challenge record')
        name = challenge.get('name')
        if not isinstance(name, str) or not name or len(name) > 200 or name in names:
            raise ValueError('Invalid or duplicate challenge name')
        names.add(name)
        specs.append(_challenge_spec(challenge, name))
        b = _number(challenge.get('baseline_rms'), 'baseline_rms', positive=True)
        d = _number(challenge.get('design_rms'), 'design_rms', positive=True)
        _number(challenge.get('nominal_rms'), 'nominal_rms', positive=True)
        reduction = _number(100. * (1. - d / b), 'reduction_pct')
        _same_metric(challenge.get('reduction_pct'), reduction, f'{name}.reduction_pct')
        violation = challenge.get('constraint_violation')
        if type(violation) is not bool:
            raise ValueError('Malformed challenge constraint flag')
        violations += int(violation)
        baseline.append(b)
        selected.append(d)
        reductions.append(reduction)
    count = len(challenges)
    baseline_rms = _number(math.hypot(*baseline) / math.sqrt(count), 'pooled baseline_rms', positive=True)
    design_rms = _number(math.hypot(*selected) / math.sqrt(count), 'pooled design_rms', positive=True)
    metrics = {'baseline_rms': baseline_rms, 'design_rms': design_rms,
               'reduction_pct': _number(100. * (1. - design_rms / baseline_rms), 'pooled reduction_pct'),
               'worst_reduction_pct': min(reductions)}
    for key, value in metrics.items():
        _same_metric(summary.get(key), value, key)
    if type(summary.get('constraint_violations')) is not int or summary['constraint_violations'] != violations:
        raise ValueError('Stored constraint violations disagree with challenge evidence')
    if type(summary.get('adequate')) is not bool:
        raise ValueError('Malformed model adequacy flag')
    validation = result.get('validation')
    if not isinstance(validation, dict):
        raise ValueError('Missing evaluation settings')
    grid = _physical_grid(result, validation)
    decision = result.get('decision', {})
    if not isinstance(decision, dict):
        raise ValueError('Malformed decision settings')
    summary = {**deepcopy(summary), **metrics, 'constraint_violations': violations}
    public = {'protocol': protocol, 'config': deepcopy(config), 'summary': summary,
              'recommendation': deepcopy(result.get('recommendation'))}
    # Outcome-dependent fit particles, scores, selected indices and solver errors are deliberately excluded.
    settings = {k: v for k, v in validation.items() if k in (
        'solver_methods', 'rms_window_seconds', 'audit_threshold', 'force_threshold', 'forecast_threshold',
        'audit_experiments', 'acquisition_experiments', 'forecast_audit_experiments',
        'design_grid_size', 'operational_budgets', 'budgets', 'solver_scope', 'integration',
        'known_primary_mass', 'coefficient_bounds', 'audit_normalisation', 'audit_aggregation')}
    decision_settings = {k: v for k, v in decision.items() if k in (
        'particle_count', 'selection_rule', 'loss_definition', 'envelope', 'design_envelope',
        'forcing_envelope', 'quadrature', 'quadrature_nodes', 'quadrature_weights',
        'fantasy_count', 'operational_budgets', 'budgets', 'particle_construction',
        'tail_mass', 'cvar_weight', 'mean_weight', 'surrogate', 'recommendation_criterion')}
    return public, {'challenges': specs, 'grid': grid,
                    'grid_id': validation.get('design_grid_id', decision.get('grid_id')),
                    'evaluation budgets/settings': settings,
                    'decision budgets/settings': decision_settings}, reductions


def compare_receipts(receipts: list[dict]) -> dict:
    if not isinstance(receipts, list) or len(receipts) != 2:
        raise ValueError('Comparison requires exactly two receipts')
    try:
        checked = [_checked(receipt) for receipt in receipts]
        if receipts[0]['result_sha256'] == receipts[1]['result_sha256']:
            raise ValueError('Duplicate numerical evidence cannot form a comparison')
        first, second = checked[0][0], checked[1][0]
        mismatches = []
        if first['protocol'] != second['protocol']:
            mismatches.append('Numerical protocol differs')
        for key in ('world', 'seed', 'noise', 'budget'):
            if first['config'][key] != second['config'][key]:
                mismatches.append(f'Configuration {key} differs')
        for key in checked[0][1]:
            if canonical(checked[0][1][key]) != canonical(checked[1][1][key]):
                mismatches.append(f'{key.capitalize()} differ')
        deltas = None
        if not mismatches:
            deltas = {key: second['summary'][key] - first['summary'][key]
                      for key in ('reduction_pct', 'worst_reduction_pct', 'design_rms')}
            deltas['challenge_reductions'] = [
                {'name': c['name'], 'delta': b - a}
                for c, a, b in zip(receipts[0]['result']['challenges'], checked[0][2], checked[1][2])]
        return {'paired': not mismatches, 'mismatches': mismatches, 'runs': [first, second],
                'deltas': deltas, 'note': 'Descriptive comparison of two finite synthetic studies. '
                'Deltas are second minus first; one pair does not establish acquisition efficacy.'}
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError(f'Malformed comparison evidence: {exc}') from exc
