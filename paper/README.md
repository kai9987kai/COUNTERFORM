# COUNTERFORM paper source package

This package accompanies **COUNTERFORM A Synthetic Pilot Study of Experiment Selection and Model Adequacy**, dated 2 November 2026 and attributed to the author identifier kai9987kai. It contains the editable Markdown manuscript, bibliography, analysis, numerical evidence, publication figures and scientific implementation. It records a negative exploratory pilot, not an independently confirmed strategy benefit.

## Read the paper

- `output/pdf/counterform_pilot_paper.pdf` is the typeset 12-page paper.
- `paper/manuscript.md` is the editable manuscript, including equations and the full results table.
- `paper/references.bib` contains the seven references.
- `paper/figures` contains three figures in PNG, SVG and vector PDF formats.

The package does not supply a journal submission, DOI, publication record or physical validation. No application source or retained experimental evidence was changed while writing the paper.

## Reproduce the saved-data analysis

From the package root:

```powershell
python paper/analyze_results.py
```

This analysis uses the Python standard library. It does not import the engine, fit models or simulate new observations. It verifies 16 pilot receipts and ZIP manifests plus the separate example, recomputes metrics and audit residuals from saved data, checks policy/control coincidence, and writes `paper/data`.

The pilot comprises two worlds, two shared parameter seeds, four strategies and three acquisitions per run. The two worlds are not independent parameter draws. Neither the 16 runs nor the 48 within-run challenge evaluations should be treated as independent population replicates.

## Rebuild figures and manuscript PDF

Use an authoring environment separate from the frozen scientific replay environment:

```powershell
python -m pip install -r paper/requirements-paper.txt
python paper/build_figures.py
python paper/build_pdf.py
```

The scripts use locally installed libraries, embed fonts and generate figures directly from the retained receipts. The optional `output/paper-deps` search path supports the original task's isolated authoring dependencies; it is not required after installing the requirements above. In the original authoring run, the Codex bundled Python runtime was used with ReportLab 4.4.9 and Matplotlib 3.11.2. Figure authoring used NumPy 2.5.4; the numerical studies used NumPy 2.4.3. Plotting does not recompute the scientific studies.

Optional page rasterisation requires `pypdf` and `pypdfium2`, then `python paper/render_pdf.py`. The final PDF's twelve rendered pages were visually inspected; equations, tables and captions were checked for clipping and overlap. Page PNGs are QA intermediates and are not included in this source archive.

## Recompute the scientific studies

The retained records identify Python 3.12.10, NumPy 2.4.3 and SciPy 1.17.1. Install `requirements-validated.txt` and then `python -m pip install -e .`. The full original fresh validation dependency snapshot is `requirements-lock.txt`.

```powershell
python -m counterform verify runs/benchmark/cubic/11/counterform/evidence.zip
python -m counterform replay runs/benchmark/cubic/11/counterform/receipt.json
python -m counterform benchmark --seeds 11 23 --worlds cubic unmodelled --budget 3 --noise 0.01 --output runs/recomputed
```

Use a new output directory for recomputed studies. The retained benchmark contains all 16 original runs and a separate, excluded five-acquisition example. Raw records can be checked without running the scientific engine. Exact numerical replay requires a compatible numerical environment; hash verification alone is not a numerical recomputation.

## Integrity

The outer source archive has a SHA-256 manifest for every included file. Each original evidence ZIP also retains its own manifest. Checksums detect changes relative to these records, not author authenticity. Original standalone HTML reports use CRLF line endings while archived HTML uses LF; their normalised text agrees. Receipt and numerical checks are unaffected.

## Main findings

COUNTERFORM and predictive disagreement select identical experiments in all four world–seed instances. Selected and nominal designs match in all 16 runs. The residual audit accepts a structurally incomplete friction candidate in two omitted-law random runs, while both cubic passive runs reject every acquired fit. Eight of 48 challenges worsen displacement, despite positive pooled reductions in all 16 runs. The paper explains why these are bounded diagnostic findings rather than general strategy equivalence or a reliability guarantee.
