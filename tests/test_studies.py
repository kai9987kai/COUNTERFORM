import json
from pathlib import Path

import pytest

from counterform.studies import validate_plan, run_plan


def plan():
    return {'schema': 'counterform.study.v1', 'name': 'test-study', 'protocol': '0.1.0',
            'seeds': [3], 'worlds': ['linear'], 'strategies': ['passive'], 'budget': 2, 'noise': .01,
            'purpose': 'development'}


@pytest.mark.parametrize('change', [
    {'seeds': [3, 3]}, {'seeds': [True]}, {'seeds': [-1]}, {'seeds': []},
    {'worlds': ['linear', 'linear']}, {'strategies': ['passive', 'passive']},
    {'protocol': '9.0.0'}, {'budget': 20}, {'noise': float('nan')},
    {'worlds': ['memory']}, {'extra': 'ignored'},
])
def test_study_preflight_rejects_invalid_cells_before_output_creation(tmp_path, change):
    destination = tmp_path / 'must-not-exist'
    with pytest.raises(ValueError):
        run_plan({**plan(), **change}, destination)
    assert not destination.exists()


def test_study_preflight_requires_unique_bounded_cells():
    valid = validate_plan(plan())
    assert valid['case_count'] == 1
    with pytest.raises(ValueError):
        validate_plan({**plan(), 'protocol': '0.2.0', 'seeds': list(range(8)),
                       'worlds': ['linear', 'cubic', 'friction', 'unmodelled', 'memory'],
                       'strategies': ['passive', 'random', 'active', 'counterform']})


def test_study_runner_persists_verified_complete_evidence_and_is_not_implicitly_overwritten(tmp_path):
    destination = tmp_path / 'study'
    summary = run_plan(plan(), destination)
    assert summary['complete'] is True
    assert summary['completed_cases'] == 1
    assert summary['failed_cases'] == 0
    assert (destination / 'linear/3/passive/evidence.zip').is_file()
    assert (destination / 'report.html').is_file()
    assert 'Constraint violations' in (destination / 'report.html').read_text(encoding='utf-8')
    assert json.loads((destination / 'summary.json').read_text())['complete']
    with pytest.raises(ValueError, match='exist'):
        run_plan(plan(), destination)


def test_failed_cases_are_visible_in_report_and_preserved_in_summary(tmp_path, monkeypatch):
    def failed_run(*args, **kwargs):
        raise RuntimeError('deliberate <solver> failure')
    monkeypatch.setattr('counterform.protocols.run_study', failed_run)
    destination = tmp_path / 'failed-study'
    summary = run_plan(plan(), destination)
    report = (destination / 'report.html').read_text(encoding='utf-8')
    assert summary['complete'] is False
    assert summary['failed_cases'] == 1
    assert 'linear/3/passive' in report
    assert 'deliberate &lt;solver&gt; failure' in report
