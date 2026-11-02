import io
import json
import zipfile

import pytest

from counterform.evidence import make_receipt, verify_receipt, build_bundle, verify_bundle, design_stl


@pytest.fixture
def result():
    return {
        'config': {'seed': 7, 'world': 'linear', 'strategy': 'passive', 'budget': 2, 'noise': .01},
        'summary': {'reduction_pct': -2., 'adequate': False, 'verdict': 'Insufficient evidence'},
        'design': {'mass': .1, 'stiffness': 2., 'damping': .03, 'tuning_ratio': 1., 'mass_ratio': .1, 'objective': .2},
        'models': [], 'challenges': [], 'limitations': ['Synthetic only'],
        'response': {'frequencies': [1., 2.], 'baseline': [.2, .4], 'selected': [.1, .3], 'nominal': [.2, .3]},
    }


def test_receipt_verifies_and_detects_changed_numerical_evidence(result):
    receipt = make_receipt(result)
    assert verify_receipt(receipt)['valid']
    receipt['result']['summary']['reduction_pct'] = 99.
    with pytest.raises(ValueError, match='checksum'):
        verify_receipt(receipt)


def test_bundle_exports_design_and_detects_changed_or_unexpected_files(result):
    bundle = build_bundle(make_receipt(result))
    assert verify_bundle(bundle)['valid']
    with zipfile.ZipFile(io.BytesIO(bundle)) as source:
        entries = {n: source.read(n) for n in source.namelist()}
    assert json.loads(entries['design.json'])['units'] == 'mm'
    assert b'facet normal' in entries['design.stl']
    entries['design.stl'] += b'changed'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, value in entries.items():
            z.writestr(name, value)
    with pytest.raises(ValueError, match='checksum'):
        verify_bundle(output.getvalue())


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'C:/drive', 'sub\\escape'])
def test_verifier_rejects_unsafe_archive_names(name):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr(name, 'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        verify_bundle(output.getvalue())


def test_receipt_rejects_nonfinite_result_and_stl_has_closed_box_facets(result):
    result['summary']['reduction_pct'] = float('nan')
    with pytest.raises(ValueError):
        make_receipt(result)
    stl = design_stl({'mass': .1, 'stiffness': 2., 'damping': .03})
    assert stl.count('facet normal') == 48


@pytest.mark.parametrize('manifest', [None, [], {'schema': 'counterform.bundle.v1', 'files': []}])
def test_malformed_manifest_is_rejected_with_usable_validation_error(manifest):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('manifest.json', json.dumps(manifest))
    with pytest.raises(ValueError, match='manifest'):
        verify_bundle(output.getvalue())
