from copy import deepcopy
import json
from pathlib import Path

import pytest

from counterform.__main__ import main
from counterform.evidence import canonical, digest, make_receipt
from counterform.protocols import replay_result, run_study


def test_benchmark_preflight_rejects_duplicate_and_invalid_plans_before_writes(tmp_path, capsys):
    for options in (['--seeds', '7', '7'], ['--worlds', 'linear', 'linear'], ['--seeds', '7', '-1']):
        output = tmp_path / str(len(list(tmp_path.iterdir())))
        assert main(['benchmark', '--protocol', '0.1.0', '--output', str(output), *options]) == 2
        assert not output.exists()
    assert 'COUNTERFORM:' in capsys.readouterr().err


@pytest.mark.parametrize('directory', ['runs/example', 'runs/benchmark', 'runs/benchmark/linear'])
def test_new_commands_refuse_protected_historical_outputs(directory, capsys):
    assert main(['run', '--protocol', '0.1.0', '--output', directory]) == 2
    assert 'historical' in capsys.readouterr().err.lower()


def test_cli_archived_replay_reports_actual_hash_comparison_and_exit_status(capsys):
    path = Path(__file__).resolve().parents[1] / 'runs' / 'example' / 'receipt.json'
    receipt = json.loads(path.read_text(encoding='utf-8'))
    actual_hash = digest(canonical(replay_result(receipt)))
    matches = actual_hash == receipt['result_sha256']
    assert main(['replay', str(path)]) == (0 if matches else 1)
    output = json.loads(capsys.readouterr().out)
    assert output['protocol'] == '0.1.0'
    assert output['reproduced'] is matches
    assert output['expected_sha256'] == receipt['result_sha256']
    assert output['actual_sha256'] == actual_hash
    assert output['source_matches'] is False


@pytest.fixture(scope='module')
def fresh_legacy_result():
    return run_study({'protocol': '0.1.0', 'strategy': 'passive', 'budget': 2})


@pytest.mark.parametrize('matches', [True, False])
def test_cli_replay_distinguishes_exact_numeric_match_from_source_match(
        matches, fresh_legacy_result, tmp_path, capsys):
    result = deepcopy(fresh_legacy_result)
    actual_hash = digest(canonical(result))
    if not matches:
        # An internally valid receipt can record values that its config will not replay.
        result['summary']['reduction_pct'] += 1.
    receipt = make_receipt(result)
    receipt['software']['source_sha256'] = '0' * 64
    receipt['payload_sha256'] = digest(canonical({key: value for key, value in receipt.items()
                                                 if key != 'payload_sha256'}))
    path = tmp_path / 'receipt.json'
    path.write_bytes(canonical(receipt))
    assert main(['replay', str(path)]) == (0 if matches else 1)
    output = json.loads(capsys.readouterr().out)
    assert output['protocol'] == '0.1.0'
    assert output['reproduced'] is matches
    assert output['expected_sha256'] == receipt['result_sha256']
    assert output['actual_sha256'] == actual_hash
    assert output['source_matches'] is False
