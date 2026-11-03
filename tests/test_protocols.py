"""Version routing must preserve historical numerical evidence."""
from importlib import import_module
import json
from pathlib import Path
import sys

import pytest

from counterform.evidence import canonical, digest, make_receipt


ARCHIVED = Path(__file__).resolve().parents[1] / 'runs' / 'example' / 'receipt.json'


@pytest.mark.skipif(sys.platform != 'win32', reason='Original numerical hash was recorded on Windows; no cross-platform bit guarantee')
def test_legacy_archive_replays_its_original_numeric_hash():
    protocols = import_module('counterform.protocols')
    receipt = json.loads(ARCHIVED.read_text(encoding='utf-8'))
    assert protocols.receipt_protocol(receipt) == '0.1.0'
    actual = protocols.replay_result(receipt)
    assert actual['config'] == receipt['config']
    assert 'protocol' not in actual['config']
    assert digest(canonical(actual)) == receipt['result_sha256']


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
