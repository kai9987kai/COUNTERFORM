import json
from pathlib import Path
import sys

import pytest

from counterform.__main__ import main


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


@pytest.mark.skipif(sys.platform != 'win32', reason='Original numerical hash was recorded on Windows; no cross-platform bit guarantee')
def test_cli_replay_reports_numeric_reproduction_without_claiming_package_source_match(capsys):
    path = Path(__file__).resolve().parents[1] / 'runs' / 'example' / 'receipt.json'
    assert main(['replay', str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['protocol'] == '0.1.0'
    assert output['reproduced'] is True
    assert output['source_matches'] is False
