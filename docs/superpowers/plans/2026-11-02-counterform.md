# COUNTERFORM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build and run the first usable COUNTERFORM synthetic mechanical research lab.

**Architecture:** Separate deterministic scientific engine, evidence/CLI/API, and a locally bundled 3D workbench. The API contract fixes shared boundaries so core and UI can be built concurrently and reviewed together.

**Tech Stack:** Python 3.12+, NumPy, SciPy, FastAPI, pytest; JavaScript, Vite, Three.js.

**Spec:** `docs/design.md`; interfaces: `docs/api-contract.md`.

## Global Constraints
- CPU local, no credentials, server default 127.0.0.1.
- Real computed results, finite model library, separate held-out audit and challenges.
- Deterministic numerical payloads; reject malformed configs and archive tampering.
- CAD is a conceptual assembly, not manufacturing validation.
- Existing workspace is empty and not a Git repository; build here as requested, no checkout relocation or publishing.

## Review Focus
- All-model rejection despite concentrated weights in omitted-physics cases.
- No hidden truth data enters fit, acquisition or selected-design search.
- No division by zero, nonfinite metrics or unstable solver output at allowed input boundaries.
- Concurrent jobs, restart history, invalid IDs and missing static builds have usable outcomes.
- Replay and archive verification detect changed values and files; conceptual CAD units/limits are explicit.

### Task 1: Scientific engine
**Files:** `counterform/engine.py`, focused numerical modules as useful, `tests/test_engine.py`.
**Interfaces:** produces `run_study(config, progress=None)` and the result schema in `docs/api-contract.md`.
- [x] Write tests for analytic linear response, deterministic hidden observation, model recovery, omitted-model rejection, finite held-out design controls and config boundaries; run to observe missing behavior.
- [x] Implement dynamics, fitting, acquisition, finite robust search and held-out evaluation without leaking truth.
- [x] Run `python -m pytest tests/test_engine.py -q`; inspect actual adequacy and negative challenge outcomes.

### Task 2: Local 3D workbench
**Files:** `web/*`, `package.json`, lockfile, `vite.config.js`, generated `counterform/web/*`.
**Interfaces:** consumes HTTP API from `docs/api-contract.md`; produces static build.
- [x] Build labelled runnable controls, instrument scene, real-data charts, experiment/model panels, evidence/history views and working exports.
- [x] Run `npm run build`; use a browser to exercise real run, history, downloads, mobile layout and errors after API integration.

### Task 3: Evidence, API and CLI
**Files:** `counterform/evidence.py`, `server.py`, `__main__.py`, `__init__.py`, `tests/test_evidence.py`, `tests/test_server.py`, `pyproject.toml`, launch scripts.
**Interfaces:** consumes deterministic engine result, produces API in contract plus receipt/export/replay commands.
- [x] Write failing tests for receipt hash verification, archive tampering, safe paths, invalid API config, real job lifecycle and download content.
- [x] Implement canonical receipts, manifests, replay, conceptual CAD, bounded async job persistence, local static serving, benchmark and launch commands.
- [x] Run `python -m pytest -q`, build wheel, install to a clean dependency-isolated target with existing scientific dependencies and smoke-test packaged assets/CLI.

### Task 4: Integration and review
**Files:** `README.md`, `docs/research.md`, `docs/progress.md`, retained `runs/` examples, browser artifacts.
- [x] Run representative studies and paired baseline benchmark; document actual findings and limitations.
- [x] Request independent code review, fix consequential findings with regression tests, run full suite and browser smoke checks.
- [x] Start local server, open workbench, provide URL and concise launch/test instructions.
