"""Local-only HTTP workbench and bounded asynchronous study jobs."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
from threading import Lock, BoundedSemaphore
from typing import Literal
import uuid
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .evidence import canonical, make_receipt, verify_receipt, build_bundle, design_document, design_stl, report_html


class StudyConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)
    world: Literal['linear', 'cubic', 'friction', 'unmodelled'] = 'cubic'
    strategy: Literal['passive', 'random', 'active', 'counterform'] = 'counterform'
    budget: int = Field(default=5, ge=2, le=8, strict=True)
    noise: float = Field(default=.01, ge=0, le=.05, allow_inf_nan=False, strict=True)


class RunStore:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.slots = BoundedSemaphore(3)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='counterform')
        self.jobs = {}
        for path in sorted(directory.glob('*.json'), reverse=True):
            try:
                job = json.loads(path.read_text(encoding='utf-8'))
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
        if job['status'] not in ('queued', 'running', 'complete', 'failed'):
            raise ValueError('Invalid saved status')
        created = datetime.fromisoformat(job['created_at'])
        if created.tzinfo is None or not isinstance(job['message'], str):
            raise ValueError('Invalid saved metadata')
        progress = job['progress']
        if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not math.isfinite(progress) or not 0 <= progress <= 1:
            raise ValueError('Invalid saved progress')
        StudyConfig.model_validate(job['config'])
        if job['status'] == 'complete':
            receipt = job['receipt']
            verify_receipt(receipt)
            if canonical(job['result']) != canonical(receipt['result']) or job['config'] != receipt['config']:
                raise ValueError('Saved display result and evidence receipt disagree')

    def _save(self, job: dict):
        path = self.directory / (job['id'] + '.json')
        temporary = path.with_suffix('.tmp')
        temporary.write_bytes(canonical(job))
        os.replace(temporary, path)

    def submit(self, config: dict) -> dict:
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, 'Three studies are already queued or running. Wait for one to finish.')
        job = {'id': uuid.uuid4().hex[:16], 'status': 'queued', 'progress': 0., 'message': 'Waiting for the local solver', 'created_at': datetime.now(timezone.utc).isoformat(), 'config': config}
        try:
            with self.lock:
                self.jobs[job['id']] = job
                self._save(job)
            self.pool.submit(self._run, job['id'])
        except Exception:
            self.slots.release()
            raise
        return self.get(job['id'])

    def _run(self, run_id: str):
        def progress(fraction, message):
            with self.lock:
                self.jobs[run_id].update(progress=max(0., min(1., float(fraction))), message=message)
        try:
            from .engine import run_study
            with self.lock:
                job = self.jobs[run_id]
                job.update(status='running', message='Collecting synthetic observations')
                self._save(job)
            result = run_study(job['config'], progress=progress)
            receipt = make_receipt(result)
            with self.lock:
                job.update(status='complete', progress=1., message='Evidence ready', result=result, receipt=receipt)
                self._save(job)
        except Exception as exc:
            logging.exception('Study %s failed', run_id)
            with self.lock:
                self.jobs[run_id].update(status='failed', message='Study failed', error=f'{type(exc).__name__}: {exc}')
                self._save(self.jobs[run_id])
        finally:
            self.slots.release()

    def get(self, run_id: str, include_receipt=False) -> dict:
        with self.lock:
            job = self.jobs.get(run_id)
            if job is None:
                raise HTTPException(404, 'Run not found')
            return {k: v for k, v in job.items() if include_receipt or k != 'receipt'}

    def listing(self) -> list:
        with self.lock:
            return [{k: v for k, v in job.items() if k not in ('result', 'receipt')} for job in sorted(self.jobs.values(), key=lambda j: j['created_at'], reverse=True)[:50]]


def create_app(run_dir: Path | str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = RunStore(Path(run_dir) if run_dir is not None else Path.cwd() / 'runs' / 'history')
        yield
        app.state.store.pool.shutdown(wait=True)

    app = FastAPI(title='COUNTERFORM local laboratory', version=__version__, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]', 'testserver'])

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'version': __version__}

    @app.get('/api/runs')
    def runs():
        return {'runs': app.state.store.listing()}

    @app.post('/api/runs', status_code=202)
    def start(config: StudyConfig):
        return app.state.store.submit(config.model_dump())

    @app.get('/api/runs/{run_id}')
    def get(run_id: str):
        return app.state.store.get(run_id)

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
