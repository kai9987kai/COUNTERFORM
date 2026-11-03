import io
import json
from pathlib import Path
import zipfile

import pytest

from counterform import evidence


ARCHIVED = Path(__file__).resolve().parents[1] / 'runs' / 'example'


def test_old_report_records_simulation_version_separately_from_exporter(monkeypatch):
    receipt = json.loads((ARCHIVED / 'receipt.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(evidence, '__version__', '9.9.9')
    html = evidence.report_html(receipt)
    assert 'simulation v0.1.0' in html
    assert 'exporter v9.9.9' in html
    assert 'Recorded adequacy' in html
    assert 'Joint adequacy' not in html
    assert evidence.verify_bundle((ARCHIVED / 'evidence.zip').read_bytes())['valid']


def test_bounded_path_reads_reject_before_loading_oversized_input(tmp_path, monkeypatch):
    path = tmp_path / 'receipt.json'
    path.write_bytes(b' ' * 33)
    monkeypatch.setattr(evidence, 'MAX_RECEIPT_BYTES', 32, raising=False)
    with pytest.raises(ValueError, match='size limit'):
        evidence.read_evidence(path)
    path = tmp_path / 'evidence.zip'
    path.write_bytes(b' ' * 65)
    monkeypatch.setattr(evidence, 'MAX_ARCHIVE_BYTES', 64, raising=False)
    with pytest.raises(ValueError, match='size limit'):
        evidence.read_evidence(path)


def test_bundle_bounds_manifest_and_individual_members(monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('manifest.json', ' ' * 33)
    monkeypatch.setattr(evidence, 'MAX_MANIFEST_BYTES', 32, raising=False)
    with pytest.raises(ValueError, match='size limit'):
        evidence.verify_bundle(output.getvalue())
    monkeypatch.setattr(evidence, 'MAX_MEMBER_BYTES', 10, raising=False)
    with pytest.raises(ValueError, match='size limit'):
        evidence.verify_bundle((ARCHIVED / 'evidence.zip').read_bytes())


def test_v2_report_preserves_abstention_and_both_audits():
    result = json.loads((ARCHIVED / 'receipt.json').read_text(encoding='utf-8'))['result']
    result.update(version='0.2.0', protocol='0.2.0', recommendation={
        'status': 'abstain', 'selected_control': 'no_absorber',
        'message': 'Use the <control> while support is inadequate.', 'reasons': ['Forecast failed.']})
    result['models'][0].update(forecast_nrmse=.42, force_passed=True, forecast_passed=False)
    html = evidence.report_html(evidence.make_receipt(result))
    assert 'Recommendation: abstain' in html
    assert 'Use the &lt;control&gt; while support is inadequate.' in html
    assert 'Forecast NRMSE' in html
    assert 'Force audit' in html
