"""Paired deltas require comparable evidence and independently checked metrics."""
from copy import deepcopy
from importlib import import_module

import pytest

from counterform.evidence import make_receipt


def receipt(*, selected=1., strategy='active', seed=7, protocol='0.2.0'):
    result = {
        'version': protocol, 'config': {'seed': seed, 'world': 'linear',
            'strategy': strategy, 'budget': 2, 'noise': .01},
        'summary': {'reduction_pct': 100 * (1-selected/2), 'worst_reduction_pct': 100 * (1-selected/2),
            'baseline_rms': 2., 'design_rms': selected, 'constraint_violations': 0, 'adequate': True},
        'challenges': [{'name': name, 'frequency': f, 'amplitude': 1., 'harmonic': 0.,
            'tolerance': {'mass': 1., 'stiffness': 1., 'damping': 1.},
            'baseline_rms': 2., 'design_rms': selected, 'nominal_rms': 1.2,
            'reduction_pct': 100 * (1-selected/2), 'constraint_violation': False,
            'primary_peak_limit': .5, 'absorber_stroke_limit': .65}
            for name, f in [('first', 5.), ('second', 7.)]],
        'validation': {'design_grid_size': 30, 'design_grid_id': 'fixed-test',
            'audit_experiments': 2, 'forecast_audit_experiments': 2,
            'solver_methods': ['DOP853', 'Radau'], 'rms_window_seconds': [7., 14.]},
        'decision': {'grid_id': 'fixed-test', 'particle_count': 8,
            'loss_definition': 'test loss', 'selection_rule': 'test rule'},
        'design_grid': [{'mass': m, 'stiffness': m * (6. * ratio) ** 2,
            'damping': 2. * zeta * m * 6. * ratio}
            for m in (.08, .16) for ratio in (.75, .9, 1., 1.1, 1.25) for zeta in (.05, .15, .3)],
        'recommendation': {'status': 'candidate', 'selected_control': 'absorber', 'reasons': [], 'message': 'test'},
    }
    if protocol == '0.2.0':
        result['protocol'] = protocol
    return make_receipt(result)


def test_comparison_uses_second_minus_first_and_retains_negative_outcomes():
    compare = import_module('counterform.comparison').compare_receipts
    data = compare([receipt(selected=1., strategy='active'), receipt(selected=2.4, strategy='counterform')])
    assert data['paired'] is True
    assert data['mismatches'] == []
    assert data['runs'][1]['summary']['reduction_pct'] == pytest.approx(-20.)
    assert data['deltas']['reduction_pct'] == pytest.approx(-70.)
    assert data['deltas']['design_rms'] == pytest.approx(1.4)
    assert data['deltas']['challenge_reductions'] == [
        {'name': 'first', 'delta': pytest.approx(-70.)},
        {'name': 'second', 'delta': pytest.approx(-70.)}]


@pytest.mark.parametrize('change,label', [
    (lambda r: r['config'].update(seed=8), 'seed'),
    (lambda r: r['config'].update(budget=3), 'budget'),
    (lambda r: r['validation'].update(design_grid_id='other'), 'grid'),
    (lambda r: r['validation'].update(forecast_audit_experiments=4), 'budget'),
    (lambda r: r['challenges'][0].update(amplitude=2.), 'challenge'),
    (lambda r: r['decision'].update(particle_count=12), 'budget'),
    (lambda r: r['validation'].update(integration={'rtol': 1e-4}), 'settings'),
    (lambda r: r['decision'].update(surrogate={'branch': 'other'}), 'settings'),
])
def test_incompatible_evidence_remains_descriptive_without_deltas(change, label):
    compare = import_module('counterform.comparison').compare_receipts
    first, second = receipt(), receipt(strategy='counterform')
    modified = deepcopy(second['result'])
    change(modified)
    second = make_receipt(modified)
    data = compare([first, second])
    assert data['paired'] is False
    assert data['deltas'] is None
    assert len(data['runs']) == 2
    assert any(label in text.lower() for text in data['mismatches'])


def test_duplicate_or_rehashed_malformed_metrics_are_rejected():
    compare = import_module('counterform.comparison').compare_receipts
    first = receipt()
    with pytest.raises(ValueError, match='[Dd]uplicate'):
        compare([first, deepcopy(first)])
    for patch in ({'reduction_pct': 99.}, {'design_rms': 0.}, {'constraint_violations': True}):
        changed = deepcopy(receipt(strategy='counterform')['result'])
        changed['summary'].update(patch)
        with pytest.raises(ValueError):
            compare([first, make_receipt(changed)])


def test_different_protocols_do_not_produce_paired_deltas():
    compare = import_module('counterform.comparison').compare_receipts
    result = compare([receipt(protocol='0.1.0'), receipt(strategy='counterform')])
    assert result['paired'] is False
    assert result['deltas'] is None
    assert any('protocol' in m.lower() for m in result['mismatches'])


@pytest.mark.parametrize('field', ['frequency', 'amplitude', 'harmonic', 'tolerance',
                                  'primary_peak_limit', 'absorber_stroke_limit'])
def test_shared_missing_challenge_settings_cannot_create_paired_deltas(field):
    compare = import_module('counterform.comparison').compare_receipts
    records = []
    for strategy in ('active', 'counterform'):
        result = receipt(strategy=strategy)['result']
        for challenge in result['challenges']:
            challenge.pop(field)
        records.append(make_receipt(result))
    with pytest.raises(ValueError):
        compare(records)


@pytest.mark.parametrize('field,value', [
    ('frequency', 0.), ('frequency', -2.), ('frequency', True), ('frequency', '5'),
    ('amplitude', 0.), ('amplitude', -1.), ('amplitude', False), ('amplitude', None),
    ('harmonic', None), ('harmonic', True), ('harmonic', '0'),
    ('primary_peak_limit', 0.), ('primary_peak_limit', -.5), ('primary_peak_limit', False),
    ('absorber_stroke_limit', 0.), ('absorber_stroke_limit', -.65), ('absorber_stroke_limit', None),
    ('tolerance', {}), ('tolerance', {'mass': 1., 'stiffness': 1.}),
    ('tolerance', {'mass': 0., 'stiffness': 1., 'damping': 1.}),
    ('tolerance', {'mass': 1., 'stiffness': -1., 'damping': 1.}),
    ('tolerance', {'mass': 1., 'stiffness': 1., 'damping': True}),
])
def test_rehashed_invalid_challenge_settings_are_rejected(field, value):
    compare = import_module('counterform.comparison').compare_receipts
    changed = receipt(strategy='counterform')['result']
    changed['challenges'][0][field] = value
    with pytest.raises(ValueError):
        compare([receipt(), make_receipt(changed)])


@pytest.mark.parametrize('change', [
    lambda r: r.update(design_grid=[]),
    lambda r: r.pop('design_grid'),
    lambda r: r['design_grid'][0].pop('mass'),
    lambda r: r['design_grid'][0].update(mass=0.),
    lambda r: r['design_grid'][0].update(stiffness=-1.),
    lambda r: r['design_grid'][0].update(damping=True),
    lambda r: r['design_grid'][0].update(damping='0.03'),
    lambda r: r['design_grid'].pop(),
    lambda r: r['validation'].update(design_grid_size=29),
    lambda r: r['validation'].update(design_grid_size=True),
])
def test_rehashed_empty_invalid_or_miscounted_grid_is_rejected(change):
    compare = import_module('counterform.comparison').compare_receipts
    records = []
    for strategy in ('active', 'counterform'):
        result = receipt(strategy=strategy)['result']
        change(result)
        records.append(make_receipt(result))
    with pytest.raises(ValueError):
        compare(records)
