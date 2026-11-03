from copy import deepcopy
import json
from pathlib import Path
from threading import Event
import time

import pytest

from fastapi.testclient import TestClient

from counterform import server
from counterform.evidence import canonical, make_receipt


ARCHIVED = Path(__file__).resolve().parents[1] / 'runs' / 'example' / 'receipt.json'


def saved_job(run_id, receipt):
    return {'id': run_id, 'status': 'complete', 'created_at': '2026-11-02T12:00:00+00:00',
            'progress': 1., 'message': 'Evidence ready', 'config': receipt['config'],
            'result': receipt['result'], 'receipt': receipt}


def wait_terminal(client, run_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = client.get(f'/api/runs/{run_id}').json()
        if job['status'] in ('complete', 'failed', 'cancelled'):
            return job
        time.sleep(.01)
    raise AssertionError('job did not terminate')


def test_old_completed_history_retains_bytes_and_reports_legacy_protocol(tmp_path):
    receipt = json.loads(ARCHIVED.read_text(encoding='utf-8'))
    path = tmp_path / '0123456789abcdef.json'
    original = canonical(saved_job(path.stem, receipt))
    path.write_bytes(original)
    with TestClient(server.create_app(tmp_path)) as client:
        assert client.get('/api/health').json()['protocols'] == ['0.1.0', '0.2.0']
        job = client.get(f'/api/runs/{path.stem}').json()
        assert job['status'] == 'complete'
        assert job['protocol'] == '0.1.0'
        assert job['config'] == receipt['config']
        assert 'protocol' not in job['config']
        assert client.get(f'/api/runs/{path.stem}/bundle').status_code == 200
    assert path.read_bytes() == original


def test_default_protocol_and_cooperative_cancellation_release_capacity(tmp_path, monkeypatch):
    started = Event()

    def checkpoint_run(config, progress=None, *, cancelled=None):
        started.set()
        while not cancelled():
            time.sleep(.002)
        from counterform.protocols import StudyCancelled
        raise StudyCancelled('Study cancelled')

    monkeypatch.setattr(server, 'run_study', checkpoint_run, raising=False)
    with TestClient(server.create_app(tmp_path)) as client:
        jobs = [client.post('/api/runs', json={}).json() for _ in range(3)]
        assert all(j['protocol'] == '0.2.0' for j in jobs)
        assert all('protocol' not in j['config'] for j in jobs)
        assert started.wait(2)
        assert client.post('/api/runs', json={}).status_code == 429
        for job in jobs:
            cancelled = client.post(f"/api/runs/{job['id']}/cancel")
            assert cancelled.status_code == 200
        for job in jobs:
            final = wait_terminal(client, job['id'])
            assert final['status'] == 'cancelled'
            assert 'result' not in final
            assert client.get(f"/api/runs/{job['id']}/receipt").status_code == 409
            assert client.post(f"/api/runs/{job['id']}/cancel").json()['status'] == 'cancelled'
            saved = json.loads((tmp_path / f"{job['id']}.json").read_text(encoding='utf-8'))
            assert 'receipt' not in saved
        next_job = client.post('/api/runs', json={})
        assert next_job.status_code == 202
        assert client.post(f"/api/runs/{next_job.json()['id']}/cancel").status_code == 200
        assert wait_terminal(client, next_job.json()['id'])['status'] == 'cancelled'


def test_compare_api_pairs_verified_history_and_handles_duplicates_and_unfinished(tmp_path):
    first = json.loads(ARCHIVED.read_text(encoding='utf-8'))
    changed = deepcopy(first['result'])
    changed['config']['strategy'] = 'active'
    second = make_receipt(changed)
    ids = ['0123456789abcdef', '1123456789abcdef']
    for run_id, receipt in zip(ids, [first, second]):
        (tmp_path / f'{run_id}.json').write_bytes(canonical(saved_job(run_id, receipt)))
    interrupted = {'id': '2123456789abcdef', 'status': 'queued',
        'created_at': '2026-11-02T12:00:00+00:00', 'progress': 0., 'message': 'Waiting',
        'config': first['config']}
    (tmp_path / f"{interrupted['id']}.json").write_bytes(canonical(interrupted))
    with TestClient(server.create_app(tmp_path)) as client:
        data = client.post('/api/compare', json={'run_ids': ids})
        assert data.status_code == 200
        assert data.json()['paired'] is True
        assert [r['id'] for r in data.json()['runs']] == ids
        assert data.json()['deltas']['reduction_pct'] == 0.
        assert client.post('/api/compare', json={'run_ids': [ids[0], ids[0]]}).status_code == 422
        assert client.post('/api/compare', json={'run_ids': [ids[0], interrupted['id']]}).status_code == 409
        assert client.post('/api/compare', json={'run_ids': ids, 'extra': 1}).status_code == 422


def test_executor_rejection_does_not_persist_a_phantom_queued_study(tmp_path):
    store = server.RunStore(tmp_path)
    store.shutdown()
    with pytest.raises(RuntimeError):
        store.submit({'protocol': '0.1.0', 'budget': 2})
    assert store.listing() == []
    restarted = server.RunStore(tmp_path)
    try:
        assert restarted.listing() == []
    finally:
        restarted.shutdown()


@pytest.mark.parametrize('change', [
    lambda r: [c.pop('frequency') for c in r['challenges']],
    lambda r: r['challenges'][0].update(tolerance={'mass': 1., 'stiffness': 1., 'damping': 0.}),
    lambda r: r.update(design_grid=[]),
    lambda r: r['design_grid'][0].update(stiffness=-1.),
    lambda r: r['design_grid'].pop(),
])
def test_compare_api_rejects_rehashed_incomplete_or_invalid_settings(tmp_path, change):
    first = json.loads(ARCHIVED.read_text(encoding='utf-8'))
    changed = deepcopy(first['result'])
    changed['config']['strategy'] = 'active'
    change(changed)
    second = make_receipt(changed)
    ids = ['0123456789abcdef', '1123456789abcdef']
    for run_id, record in zip(ids, [first, second]):
        (tmp_path / f'{run_id}.json').write_bytes(canonical(saved_job(run_id, record)))
    with TestClient(server.create_app(tmp_path)) as client:
        response = client.post('/api/compare', json={'run_ids': ids})
        assert response.status_code == 422
