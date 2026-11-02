import json

from counterform.__main__ import main
from counterform.evidence import make_receipt


def test_verify_cli_returns_failure_for_corrupt_receipt(tmp_path, capsys):
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps({'schema': 'counterform.receipt.v1', 'payload_sha256': 'wrong'}))
    assert main(['verify', str(path)]) == 2
    assert 'checksum' in capsys.readouterr().err


def test_verify_cli_reads_json_evidence(tmp_path, capsys):
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps(make_receipt({'config': {'seed': 1}, 'summary': {'adequate': False}})))
    assert main(['verify', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['valid']
