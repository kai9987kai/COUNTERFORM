# COUNTERFORM

**A local laboratory for falsification-driven mechanical design.**

COUNTERFORM observes an unknown synthetic oscillator, fits competing physical laws, selects experiments, searches for a tuned mass absorber, and challenges the design under held-out conditions. Every study produces an inspectable receipt, an integrity manifest, a standalone report and conceptual CAD exports.

This is a working first research prototype. Model discovery is selection and calibration within a declared finite library. The absorber is a bounded parametric design, and its CAD is conceptual. The software does not establish real-world reliability, autonomous scientific invention or research novelty.

## Paper and reproducibility

Read [COUNTERFORM A Synthetic Pilot Study of Experiment Selection and Model Adequacy](publications/counterform_pilot_paper.pdf), by kai9987kai, dated 2 November 2026. The 12-page paper includes methods, three figures, seven references and all 16 pilot runs, retaining negative results and study limitations.

The [editable manuscript](paper/manuscript.md), [paper source and data archive](publications/counterform_paper_sources.zip), [analysis scripts and tables](paper/) and [original experimental evidence](runs/benchmark/) are included. Start with the [publication index](publications/README.md) or [reproduction instructions](paper/README.md).

## Run on Windows

Python 3.12+ and Node.js 22.12+ are needed to build from source. The workbench is bundled locally; no network or model credentials are needed at runtime.

```powershell
python -m pip install -e ".[dev]"
npm ci
npm run build
python -m counterform serve
```

Open [COUNTERFORM](http://127.0.0.1:8768). Use `launch.ps1` or double-click `run.bat` after dependencies/build are ready. The server binds to loopback. Runs persist in `runs/history`; restarting marks interrupted jobs failed and preserves completed evidence.

## Scientific workflow

1. Choose a hidden world: linear, cubic stiffness, smooth friction, or an out-of-library mechanism.
2. Choose passive, random, predictive disagreement, or COUNTERFORM's decision-sensitive heuristic.
3. Set an acquisition budget, noise and seed; run the study.
4. Inspect fitted model weights **and** independent adequacy checks. Concentrated weights do not establish a correct model.
5. Inspect robust design, nominal/no-absorber controls, nonlinear challenges and solver agreement.
6. Download evidence ZIP, JSON receipt, standalone HTML report, STL or parametric assembly.

The experiment budget counts acquisition trials. Audit/challenge overhead is disclosed separately. Strategies use the same experiment count and 30-candidate grid recipe; physical candidate stiffness/damping depends on the fitted reference stiffness, and computation time is not equalised. A negative reduction means the absorber worsened displacement RMS. Rejected model sets retain exploratory designs without promoting them as supported results.

## CLI and evidence

```powershell
python -m counterform run --world cubic --strategy counterform --seed 42 --budget 5 --output runs/example
python -m counterform verify runs/example/evidence.zip
python -m counterform replay runs/example/receipt.json
python -m counterform benchmark --seeds 11 23 --worlds cubic unmodelled --budget 3 --output runs/benchmark
python -m pytest -q
npm run build
python -m pip wheel . --no-deps --wheel-dir dist
```

Replay recomputes numerical content and compares its SHA-256; exact reproduction depends on the recorded numerical dependency versions. `requirements-validated.txt` records the development environment. Hashes detect changes relative to a manifest; they do not authenticate its author. No archive extraction is needed for verification.

`requirements-lock.txt` records the full fresh validation environment. Install it before the project for that dependency snapshot: `python -m pip install -r requirements-lock.txt`, then `python -m pip install -e .`.

STL uses illustrative millimetre dimensions. Spring stiffness and damping are SI numerical parameters; the exported connection does not implement a manufacturable spring. See [research protocol and limitations](docs/research.md), [design](docs/design.md) and [implementation plan](docs/superpowers/plans/2026-11-02-counterform.md).

## First local pilot

The retained 16-study pilot found identical outcomes for COUNTERFORM and predictive-disagreement acquisition on the two sampled worlds/seeds. It does not support an advantage for the decision-sensitive heuristic. Two random-acquisition studies accepted an out-of-library world, showing that the adequacy gate is fallible. See [pilot results](docs/results.md) and `runs/benchmark` for raw evidence.
