# COUNTERFORM

**A local laboratory for falsification-driven mechanical design.**

COUNTERFORM observes an unknown synthetic oscillator, fits competing physical laws, selects experiments, searches for a tuned mass absorber, and challenges the design under held-out conditions. Every study produces an inspectable receipt, an integrity manifest, a standalone report and conceptual CAD exports.

**Version 0.2** adds a separate scientific protocol with eight physical-law compositions, parameter sensitivity particles, downstream decision-risk acquisition, a fixed physical design grid and joint force/trajectory audits. It records all candidate experiment scores and can abstain from recommending its exploratory absorber. The original v0.1 engine and published evidence remain available.

Model discovery is selection and calibration within a declared finite library. The absorber is a bounded parametric design, and its CAD is conceptual. The software does not establish real-world reliability, autonomous scientific invention or research novelty.

## What changed in v0.2

- The decision-sensitive selector performs a finite fantasy calculation of downstream design risk instead of multiplying predictive disagreement by a local score.
- All strategies use the same 30 physical candidate designs. A finite CVaR/mean objective considers 24 sensitivity particles; their weights and likelihoods are engineering approximations.
- Eight fixed laws combine cubic stiffness, smooth friction and quadratic drag. A new relaxing-force memory world lies outside that instantaneous library.
- The same fitted candidate must pass both a force-balance audit and a free-running trajectory forecast. Unsupported or predicted-unhelpful designs receive an explicit abstention; measured challenge performance remains visible.
- The workbench supports protocol selection, candidate score inspection, dual audit details, cancellation and compatibility-checked paired comparisons.
- Protocol-aware replay retains v0.1 numerical results. A preservation test checks the original paper, evidence and engine bytes. CI defines Windows/Linux test and build checks.

See [the v0.2 method and limitations](docs/research-v02.md), [the change log](CHANGELOG.md), and the [frozen development plan](docs/protocols/v02-development.json). The original paper below reports v0.1, not the new protocol.

The [completed 48-run v0.2 development study](docs/v02-results.md) found different COUNTERFORM/disagreement experiment sequences but identical selected designs and challenge outcomes in all 12 paired cases. It shows no acquisition-performance advantage. The audit also rejected every combined-world run and accepted 7 of 16 omitted-memory runs; its limitations and all negative outcomes remain in the report.

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

1. Choose a protocol, then a hidden world. In v0.2 the combined nonlinear world is covered by the expanded library; the memory world is intentionally omitted.
2. Choose passive, random, predictive disagreement, or COUNTERFORM's decision-sensitive heuristic.
3. Set an acquisition budget, noise and seed; run the study.
4. Inspect fitted model weights **and** independent adequacy checks. In v0.2 the force-balance and trajectory checks must pass for the same candidate. Concentrated weights do not establish a correct model.
5. Inspect robust design, nominal/no-absorber controls, nonlinear challenges and solver agreement.
6. Download evidence ZIP, JSON receipt, standalone HTML report, STL or parametric assembly.

The experiment budget counts acquisition trials. Audit/challenge overhead is disclosed separately. Version 0.2 uses the same physical grid across strategies; v0.1 uses a fit-dependent grid recipe. Computation time and forcing energy are not equalised. A negative reduction means the exploratory absorber worsened displacement RMS. Recommendation/abstention is separate from this candidate-design outcome.

## CLI and evidence

```powershell
python -m counterform run --protocol 0.2.0 --world cubic --strategy counterform --seed 42 --budget 5 --output runs/example-v02
python -m counterform verify runs/example-v02/evidence.zip
python -m counterform replay runs/example-v02/receipt.json
python -m counterform run --protocol 0.1.0 --world cubic --budget 3 --output runs/legacy-replay
python -m counterform.studies docs/protocols/v02-development.json --output runs/v02-development
python -m pytest -q
npm test
npm run build
python -m pip wheel . --no-deps --wheel-dir dist
```

Replay dispatches the recorded scientific protocol, recomputes numerical content and compares its SHA-256; exact reproduction depends on numerical dependencies/platform. A changed package-source hash after an upgrade is reported separately from numerical reproduction. `requirements-validated.txt` records the scientific environment. Hashes detect changes relative to a manifest; they do not authenticate its author. No archive extraction is needed for verification.

`requirements-lock.txt` records the full fresh validation environment. Install it before the project for that dependency snapshot: `python -m pip install -r requirements-lock.txt`, then `python -m pip install -e .`.

STL uses illustrative millimetre dimensions. Spring stiffness and damping are SI numerical parameters; the exported connection does not implement a manufacturable spring. See [research protocol and limitations](docs/research.md), [design](docs/design.md) and [implementation plan](docs/superpowers/plans/2026-11-02-counterform.md).

## First local pilot

The retained v0.1 16-study pilot found identical outcomes for COUNTERFORM and predictive-disagreement acquisition on the two sampled worlds/seeds. It does not support an advantage for its decision-sensitive heuristic. Two random-acquisition studies accepted an out-of-library world, showing that its adequacy gate is fallible. See [pilot results](docs/results.md) and `runs/benchmark` for original evidence.

The original paper's analysis checks the original package-source digest. To reproduce that complete historical environment, use its self-contained source ZIP; today's package intentionally differs. Its numerical engine remains selectable with protocol 0.1.0, and original receipts continue to verify.
