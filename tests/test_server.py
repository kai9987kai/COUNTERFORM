import json
import time

from fastapi.testclient import TestClient

from counterform.server import create_app


def test_config_validation_and_unknown_ids(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        assert client.get('/api/runs/missing').status_code == 404
        for config in [{'budget': 99}, {'seed': True}, {'world': 'unknown'}, {'noise': -1}, {'noise': True}, {'noise': False}, {'noise': '0.01'}, {'extra': 1}]:
            assert client.post('/api/runs', json=config).status_code == 422


def test_real_job_lifecycle_download_and_restart_history(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/runs', json={'seed': 7, 'budget': 2, 'world': 'linear', 'strategy': 'passive'})
        assert response.status_code == 202
        run_id = response.json()['id']
        deadline = time.monotonic() + 80
        while time.monotonic() < deadline:
            job = client.get(f'/api/runs/{run_id}').json()
            if job['status'] in ['complete', 'failed']:
                break
            time.sleep(.05)
        assert job['status'] == 'complete', job.get('error')
        assert job['result']['config']['seed'] == 7
        for suffix, mime in [('receipt', 'application/json'), ('bundle', 'application/zip'), ('design.stl', 'model/stl'), ('design.json', 'application/json'), ('report', 'text/html')]:
            artifact = client.get(f'/api/runs/{run_id}/{suffix}')
            assert artifact.status_code == 200
            assert artifact.headers['content-type'].startswith(mime)
            assert len(artifact.content) > 50
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/runs').json()['runs'][0]['id'] == run_id
        assert client.get(f'/api/runs/{run_id}').json()['status'] == 'complete'
    path = tmp_path / f'{run_id}.json'
    saved = json.loads(path.read_text())
    saved['result']['design']['mass'] += .5
    path.write_text(json.dumps(saved))
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/runs').json()['runs'] == []
        assert client.get(f'/api/runs/{run_id}').status_code == 404


def test_malformed_and_interrupted_history_has_usable_restart(tmp_path):
    (tmp_path / 'bad.json').write_text('{bad')
    (tmp_path / 'incomplete.json').write_text(json.dumps({'id': 'incomplete', 'status': 'complete'}))
    interrupted = {'id': '0123456789abcdef', 'status': 'running', 'created_at': '2026-11-02T12:00:00+00:00', 'config': {'seed': 42, 'world': 'linear', 'strategy': 'passive', 'budget': 2, 'noise': .01}, 'progress': .5, 'message': 'Running'}
    (tmp_path / (interrupted['id'] + '.json')).write_text(json.dumps(interrupted))
    with TestClient(create_app(tmp_path)) as client:
        jobs = client.get('/api/runs').json()['runs']
        assert len(jobs) == 1
        assert jobs[0]['status'] == 'failed'
        assert 'restart' in jobs[0]['message'].lower()
