# Verification — COUNTERFORM v0.1.0

Verified locally on Windows, 2 November 2026.

- `python -m pytest -q`: 42 passed in the existing Python environment; one upstream Starlette/httpx deprecation warning.
- `.venv/Scripts/python -m pytest -q`: 42 passed in a newly created virtual environment with freshly installed dependencies and httpx2; no warnings.
- `npm run build`: succeeds with local Three.js assets; Vite reports its standard large-chunk advisory (614 kB minified JavaScript).
- Wheel built from a fresh build directory; archive contains the five Python modules, one index, one CSS asset and one JS asset, plus package metadata. No stale frontend bundles included.
- Installed wheel tested from `output/installed-smoke`, outside source import resolution: API health, HTML index and every referenced JS/CSS asset return 200. Its real unmodelled-world CLI run completed and its numerical receipt replayed exactly, with matching source hash.
- Default cubic CLI study: evidence ZIP verifies; complete numerical replay reproduces the result SHA-256 with matching source hash.
- Browser: real default study completed; result-based Three.js playback, history reload, Evidence and Protocol routes, controls, and evidence ZIP download exercised. The downloaded ZIP verifies.
- Desktop and 390px mobile screenshots inspected. Mobile document width does not exceed viewport width. WebGL renders; latest build emits no browser warnings/errors on reload after replacing a removed Three.js shadow-map constant.
- Paired 16-study pilot rerun from the final source with the clean environment. All 16 exported ZIPs pass integrity verification. Outcomes are recorded in `docs/results.md`; they establish no decision-sensitive acquisition advantage.

Independent review checked scientific leakage, audit/design separation, challenge controls, boundary inputs, model rejection, replay and persistence integrity. Reporting-unit/aggregation labels and corrupted-history inconsistencies were corrected. Source tests cover those consequential persistence fixes; a separate core regression protects the audit/design boundary.

These checks verify the implementation within its declared finite synthetic scope. They do not validate the physical model, manufacturing geometry, statistical efficacy or broad reliability.
