# COUNTERFORM v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Track completed checks and rulings in docs/v02-progress.md.

**Goal:** Advance the local scientific engine, evidence workflow and workbench while preserving the published v0.1 study.

**Architecture:** Add a protocol-specific numerical package alongside the untouched legacy engine, one shared version dispatcher, and backwards-compatible UI fields. Independent workers own science, integration and frontend; root owns study protocol/CI/documentation and final review.

**Tech Stack:** Existing Python3.12+, NumPy/SciPy/FastAPI, pytest, JavaScript/Three.js/Vite; no new required scientific or runtime dependency.

**Spec:** docs/superpowers/specs/2026-11-03-counterform-v02-design.md; exact interfaces in docs/api-v02-contract.md.

## Global Constraints
- Keep engine.py, old study records, all paper files and published PDF/ZIP byte-identical.
- CPU-local deterministic finite results; no hidden truth in learner, no audit/challenge leakage.
- Default protocol0.2.0 with exact legacy replay routing; no source-match claims from numerical equality alone.
- No claimed research benefit before the new bounded study; retain negative decisions/outcomes.
- Work on codex/counterform-v02 in the existing checkout; do not publish from worker tasks.

## Review Focus
- Drag present in all new model paths, memory world truly outside instantaneous library.
- Posterior fantasy decisions use one fixed grid and the actual downstream rule, retaining negative score values.
- One identical model must pass both independent audits; no recomputation may tune frozen design.
- Old receipts/history survive defaults and exporter version changes; cancellation releases exactly once.
- Cross-run comparison rejects duplicated/malformed evidence and withholds incompatible paired deltas.

### Task 1 Scientific protocol
- [x] Write and observe failing numerical tests for compositions, analytic response, fixed grids, planted decision-vs-nuisance utility, joint audit and deterministic replay.
- [x] Implement counterform/v2 modules and required schema; record all candidate diagnostics and finite common oracle.
- [x] Run science tests, profile representative/extreme inputs, inspect all outcomes; independent scientific review.

### Task 2 Versioned integration
- [x] Write/observe failures for old/new dispatch, legacy replay, recorded report version, bounded reads, cancellation and comparison compatibility.
- [x] Implement protocols, API, receipts/export, CLI preflight/replay; preserve complete old history bytes.
- [x] Run integration tests and review concurrency/version handling independently.

### Task 3 Workbench
- [x] Add protocol controls and diagnostics, joint audit, recommendation, cancellation and paired comparison.
- [x] Add meaningful frontend data/keyboard/playback checks where logic warrants; npm build/test.
- [x] Browser-check old/new runs, history, cancellation, mismatched comparison, exports and mobile layout.

### Task 4 Reproducible study and delivery
- [x] Save hashes of all protected legacy records and test preservation; add CI and update version metadata.
- [x] Freeze paired development protocol before outcomes; implement runner/report with preflight and receipt-verified metrics.
- [x] Run full checks, actual frozen development study, independent whole-project review and necessary regression fixes.
- [x] Document observed v0.2 findings/limits, preserve the original paper, run the local upgraded workbench.
