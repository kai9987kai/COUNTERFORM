"""Local-only HTTP workbench and bounded asynchronous study jobs."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import math
import os
from pathlib import Path
from threading import Lock, BoundedSemaphore, Event
from typing import Literal
import uuid
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .evidence import canonical, make_receipt, verify_receipt, build_bundle, design_document, design_stl, report_html, read_evidence, parse_json
from .protocols import DEFAULT_PROTOCOL, SUPPORTED_PROTOCOLS, StudyCancelled, normalize_request, receipt_protocol, run_study
from .comparison import compare_receipts


class StudyConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)
    protocol: Literal['0.1.0', '0.2.0'] = DEFAULT_PROTOCOL
    world: Literal['linear', 'cubic', 'friction', 'unmodelled', 'memory'] = 'cubic'
    strategy: Literal['passive', 'random', 'active', 'counterform'] = 'counterform'
    budget: int = Field(default=5, ge=2, le=8, strict=True)
    noise: float = Field(default=.01, ge=0, le=.05, allow_inf_nan=False, strict=True)

    @model_validator(mode='after')
    def protocol_configuration(self):
        normalize_request(self.model_dump())
        return self


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_ids: list[str] = Field(min_length=2, max_length=2)

    @field_validator('run_ids')
    @classmethod
    def identities(cls, values):
        if len(set(values)) != 2 or any(re.fullmatch(r'[0-9a-f]{16}', value) is None for value in values):
            raise ValueError('Comparison needs two distinct valid run IDs')
        return values


class RunStore:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.slots = BoundedSemaphore(3)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='counterform')
        self.jobs = {}
        self.cancellations = {}
        for path in sorted(directory.glob('*.json'), reverse=True):
            try:
                job = parse_json(read_evidence(path))
                self._validate_saved_job(job, path.stem)
                if job['status'] in ('queued', 'running'):
                    job.update(status='failed', error='Server stopped before this study completed. Start a new run.', message='Interrupted by restart')
                    self._save(job)
                self.jobs[job['id']] = job
            except (ValueError, OSError, KeyError, TypeError):
                logging.warning('Skipping invalid or inconsistent saved run %s', path.name)

    @staticmethod
    def _validate_saved_job(job, stem):
        if not isinstance(job, dict) or job.get('id') != stem or re.fullmatch(r'[0-9a-f]{16}', stem) is None:
            raise ValueError('Invalid saved run identity')
        if job['status'] not in ('queued', 'running', 'complete', 'failed', 'cancelled'):
            raise ValueError('Invalid saved status')
        created = datetime.fromisoformat(job['created_at'])
        if created.tzinfo is None or not isinstance(job['message'], str):
            raise ValueError('Invalid saved metadata')
        progress = job['progress']
        if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not math.isfinite(progress) or not 0 <= progress <= 1:
            raise ValueError('Invalid saved progress')
        protocol = job.get('protocol', '0.1.0')
        config = job['config']
        if not isinstance(config, dict) or set(config) != {'seed', 'world', 'strategy', 'budget', 'noise'}:
            raise ValueError('Invalid saved configuration')
        normalize_request({**config, 'protocol': protocol})
        if 'cancel_requested' in job and type(job['cancel_requested']) is not bool:
            raise ValueError('Invalid saved cancellation state')
        if job['status'] == 'complete':
            receipt = job['receipt']
            verify_receipt(receipt)
            if receipt_protocol(receipt) != protocol:
                raise ValueError('Saved job protocol and receipt disagree')
            if canonical(job['result']) != canonical(receipt['result']) or job['config'] != receipt['config']:
                raise ValueError('Saved display result and evidence receipt disagree')
        elif 'receipt' in job or 'result' in job:
            raise ValueError('Unfinished saved job contains completed evidence')

    def _save(self, job: dict):
        path = self.directory / (job['id'] + '.json')
        temporary = path.with_suffix('.tmp')
        temporary.write_bytes(canonical(job))
        os.replace(temporary, path)

    def submit(self, config: dict) -> dict:
        request = normalize_request(config)
        protocol = request.pop('protocol')
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, 'Three studies are already queued or running. Wait for one to finish.')
        job = {'id': uuid.uuid4().hex[:16], 'protocol': protocol, 'status': 'queued', 'progress': 0.,
               'message': 'Waiting for the local solver', 'created_at': datetime.now(timezone.utc).isoformat(),
               'config': request, 'cancel_requested': False}
        try:
            with self.lock:
                self.jobs[job['id']] = job
                self.cancellations[job['id']] = Event()
                self._save(job)
            self.pool.submit(self._run, job['id'])
        except Exception:
            with self.lock:
                self.jobs.pop(job['id'], None)
                self.cancellations.pop(job['id'], None)
            try:
                (self.directory / (job['id'] + '.json')).unlink(missing_ok=True)
            finally:
                self.slots.release()
            raise
        return self.get(job['id'])

    def _run(self, run_id: str):
        def progress(fraction, message):
            with self.lock:
                self.jobs[run_id].update(progress=max(0., min(1., float(fraction))), message=message)
        try:
            with self.lock:
                job = self.jobs[run_id]
                event = self.cancellations[run_id]
                if event.is_set():
                    raise StudyCancelled('Study cancelled before execution')
                job.update(status='running', message='Collecting synthetic observations')
                self._save(job)
                request = {**job['config'], 'protocol': job['protocol']}
            result = run_study(request, progress=progress, cancelled=event.is_set)
            if event.is_set():
                raise StudyCancelled('Study cancelled before evidence export')
            receipt = make_receipt(result)
            with self.lock:
                if event.is_set():
                    raise StudyCancelled('Study cancelled before evidence publication')
                job.update(status='complete', progress=1., message='Evidence ready', result=result, receipt=receipt)
                self._save(job)
        except StudyCancelled:
            with self.lock:
                job = self.jobs[run_id]
                job.pop('result', None)
                job.pop('receipt', None)
                job.update(status='cancelled', cancel_requested=True, message='Study cancelled; no completed evidence was saved')
                self._save(job)
        except Exception as exc:
            logging.exception('Study %s failed', run_id)
            with self.lock:
                self.jobs[run_id].pop('result', None)
                self.jobs[run_id].pop('receipt', None)
                self.jobs[run_id].update(status='failed', message='Study failed', error=f'{type(exc).__name__}: {exc}')
                self._save(self.jobs[run_id])
        finally:
            self.slots.release()

    def cancel(self, run_id: str) -> dict:
        with self.lock:
            job = self.jobs.get(run_id)
            if job is None:
                raise HTTPException(404, 'Run not found')
            if job['status'] in ('queued', 'running'):
                self.cancellations[run_id].set()
                job.update(cancel_requested=True, message='Cancellation requested; waiting for a numerical checkpoint')
                self._save(job)
        return self.get(run_id)

    def shutdown(self):
        with self.lock:
            for event in self.cancellations.values():
                event.set()
        self.pool.shutdown(wait=True)

    def get(self, run_id: str, include_receipt=False) -> dict:
        with self.lock:
            job = self.jobs.get(run_id)
            if job is None:
                raise HTTPException(404, 'Run not found')
            public = {k: deepcopy(v) for k, v in job.items() if include_receipt or k != 'receipt'}
            public.setdefault('protocol', '0.1.0')
            return public

    def listing(self) -> list:
        with self.lock:
            return [{**{k: deepcopy(v) for k, v in job.items() if k not in ('result', 'receipt')},
                     'protocol': job.get('protocol', '0.1.0')}
                    for job in sorted(self.jobs.values(), key=lambda j: j['created_at'], reverse=True)[:50]]


def create_app(run_dir: Path | str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = RunStore(Path(run_dir) if run_dir is not None else Path.cwd() / 'runs' / 'history')
        try:
            yield
        finally:
            app.state.store.shutdown()

    app = FastAPI(title='COUNTERFORM local laboratory', version=__version__, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]', 'testserver'])

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'version': __version__, 'protocols': list(SUPPORTED_PROTOCOLS)}

    @app.get('/api/runs')
    def runs():
        return {'runs': app.state.store.listing()}

    @app.post('/api/runs', status_code=202)
    def start(config: StudyConfig):
        return app.state.store.submit(config.model_dump())

    @app.get('/api/runs/{run_id}')
    def get(run_id: str):
        return app.state.store.get(run_id)

    @app.post('/api/runs/{run_id}/cancel')
    def cancel(run_id: str):
        return app.state.store.cancel(run_id)

    @app.post('/api/compare')
    def compare(request: CompareRequest):
        jobs = [app.state.store.get(run_id, include_receipt=True) for run_id in request.run_ids]
        if any(job['status'] != 'complete' for job in jobs):
            raise HTTPException(409, 'Both studies must complete before comparison')
        try:
            comparison = compare_receipts([job['receipt'] for job in jobs])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        for item, job in zip(comparison['runs'], jobs):
            item['id'] = job['id']
        return comparison

    @app.get('/api/runs/{run_id}/{artifact}')
    def download(run_id: str, artifact: str):
        if artifact not in ('receipt', 'bundle', 'design.stl', 'design.json', 'report'):
            raise HTTPException(404, 'Unknown artifact')
        job = app.state.store.get(run_id, include_receipt=True)
        if job['status'] != 'complete':
            raise HTTPException(409, 'This study has not completed')
        receipt = job['receipt']
        options = {
            'receipt': lambda: (canonical(receipt), 'application/json', 'receipt.json'),
            'bundle': lambda: (build_bundle(receipt), 'application/zip', 'evidence.zip'),
            'design.stl': lambda: (design_stl(job['result']['design']).encode(), 'model/stl', 'concept-mm.stl'),
            'design.json': lambda: (canonical(design_document(job['result']['design'])), 'application/json', 'design.json'),
            'report': lambda: (report_html(receipt).encode(), 'text/html', 'report.html'),
        }
        data, media_type, filename = options[artifact]()
        return Response(data, media_type=media_type, headers={'Content-Disposition': f'attachment; filename="counterform-{run_id}-{filename}"'})

    assets = Path(__file__).parent / 'web'
    if (assets / 'index.html').exists():
        app.mount('/', StaticFiles(directory=assets, html=True), name='workbench')
    else:
        @app.get('/', response_class=HTMLResponse, status_code=503)
        def missing_build():
            return '<h1>COUNTERFORM</h1><p>Build the local workbench with <code>npm ci</code> then <code>npm run build</code>, and restart the server.</p>'
    return app
