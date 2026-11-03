"""Version routing must preserve historical numerical evidence."""
from importlib import import_module
from copy import deepcopy
import json
from pathlib import Path

import pytest

from counterform.evidence import canonical, digest, make_receipt


ARCHIVED = Path(__file__).resolve().parents[1] / 'runs' / 'example' / 'receipt.json'


def _assert_legacy_replay_close(actual, expected, path=(), *, exact=False):
    """Keep decisions exact while permitting only derived floating-point roundoff."""
    assert type(actual) is type(expected), path
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        # Inputs, sample grids and the finite design identity are not fitted outputs.
        exact_fields = {'config', 'ground_truth', 'frequency', 'frequencies', 'amplitude',
                        'harmonic', 't', 'mass', 'mass_ratio', 'tuning_ratio', 'damping_ratio',
                        'tolerance', 'primary_peak_limit', 'absorber_stroke_limit',
                        'audit_threshold', 'known_primary_mass', 'rms_window_seconds'}
        for key in expected:
            _assert_legacy_replay_close(actual[key], expected[key], (*path, key),
                                       exact=exact or key in exact_fields)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for index, (left, right) in enumerate(zip(actual, expected)):
            _assert_legacy_replay_close(left, right, (*path, index), exact=exact)
    elif isinstance(expected, float) and not exact:
        # CPU-dispatched BLAS can change the last bits even on Windows with identical
        # Python/NumPy/SciPy versions. Haswell vs Sandybridge changed this archive by
        # at most 8.1e-13. These bounds are 200x/20x tighter than the integrator's
        # rtol=2e-8 / atol=2e-10; they are regression bounds, not a bit-replay claim.
        assert actual == pytest.approx(expected, rel=1e-10, abs=1e-11), path
    else:
        assert actual == expected, path


def test_legacy_archive_replays_original_values_and_exact_decisions():
    protocols = import_module('counterform.protocols')
    receipt = json.loads(ARCHIVED.read_text(encoding='utf-8'))
    assert protocols.receipt_protocol(receipt) == '0.1.0'
    actual = protocols.replay_result(receipt)
    assert actual['config'] == receipt['config']
    assert 'protocol' not in actual['config']
    assert receipt['result_sha256'] == '674194079aa121b2109a5595c50eaa8d9449fa6c2f455b8e30ac123f24f7d068'
    assert digest(canonical(receipt['result'])) == receipt['result_sha256']
    _assert_legacy_replay_close(actual, receipt['result'])


@pytest.mark.parametrize(('path', 'changed'), [
    (('summary', 'design_rms'), 0.1),
    (('experiments', 0, 'trace', 'x', 0), 0.01),
    (('config', 'noise'), 0.010000000001),
    (('experiments', 0, 'frequency'), 3.400000000001),
    (('design', 'tuning_ratio'), 0.900000000001),
    (('validation', 'selected_grid_index'), 19),
    (('models', 1, 'adequate'), False),
    (('models', 1, 'adequate'), 1),
    (('ledger', 0, 'message'), 'Changed acquisition'),
    (('response', 'selected'), []),
])
def test_legacy_comparison_rejects_numeric_drift_and_changed_decisions(path, changed):
    expected = json.loads(ARCHIVED.read_text(encoding='utf-8'))['result']
    actual = deepcopy(expected)
    target = actual
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = changed
    with pytest.raises(AssertionError):
        _assert_legacy_replay_close(actual, expected)


def test_fresh_legacy_receipt_replays_its_exact_hash_in_the_same_environment():
    protocols = import_module('counterform.protocols')
    result = protocols.run_study({'protocol': '0.1.0', 'strategy': 'passive', 'budget': 2})
    receipt = make_receipt(result)
    assert protocols.receipt_protocol(receipt) == '0.1.0'
    replay = protocols.replay_result(receipt)
    assert digest(canonical(replay)) == receipt['result_sha256']


def test_default_request_is_new_but_explicit_legacy_remains_clean():
    protocols = import_module('counterform.protocols')
    assert protocols.normalize_request({})['protocol'] == '0.2.0'
    old = protocols.normalize_request({'protocol': '0.1.0', 'budget': 2})
    assert old == {'protocol': '0.1.0', 'seed': 42, 'world': 'cubic',
                   'strategy': 'counterform', 'budget': 2, 'noise': .01}
    for bad in ({'protocol': 'future'}, {'protocol': '0.1.0', 'world': 'memory'}, {'extra': 1}):
        with pytest.raises(ValueError):
            protocols.normalize_request(bad)


def test_replay_rejects_unsupported_or_conflicting_versions():
    protocols = import_module('counterform.protocols')
    for receipt in ({'result': {'version': 'future'}},
                    {'protocol': '0.2.0', 'result': {'version': '0.1.0'}},
                    {'result': {'version': '0.1.0', 'protocol': '0.2.0'}}):
        with pytest.raises(ValueError):
            protocols.receipt_protocol(receipt)


def test_cancellation_checks_before_start_and_at_legacy_checkpoints():
    protocols = import_module('counterform.protocols')
    with pytest.raises(protocols.StudyCancelled):
        protocols.run_study({'protocol': '0.1.0'}, cancelled=lambda: True)
    reached = []
    with pytest.raises(protocols.StudyCancelled):
        protocols.run_study({'protocol': '0.1.0', 'budget': 2},
                            progress=lambda f, m: reached.append(f),
                            cancelled=lambda: bool(reached))
    assert reached == [.02]


def test_new_dispatch_and_receipt_replay_use_the_recorded_composition_protocol():
    protocols = import_module('counterform.protocols')
    result = protocols.run_study({'world': 'memory', 'strategy': 'passive', 'budget': 2, 'seed': 5})
    assert result['version'] == result['protocol'] == '0.2.0'
    assert 'protocol' not in result['config']
    assert len(result['models']) == 8
    assert result['recommendation']['status'] in ('candidate', 'abstain')
    receipt = make_receipt(result)
    replay = protocols.replay_result(receipt)
    assert digest(canonical(replay)) == receipt['result_sha256']
