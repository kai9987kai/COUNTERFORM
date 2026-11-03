# COUNTERFORM v0.2 development paper

This separate paper, by kai9987kai and dated 3 November 2026, reports the fixed 48-run v0.2 development study. The original v0.1 paper and archive are preserved. The new study found different COUNTERFORM/disagreement acquisitions but identical selected designs and candidate-design challenge RMS outcomes in all 12 pairs; it establishes no acquisition advantage. Recommendation outcomes can differ. It also documents every adverse condition and the joint audit's acceptance of seven omitted-memory runs.

The editable manuscript is `manuscript.md`, references are in `references.bib`, and `appendix.md` includes all 48 cases. Generated figures include both raster PNG and vector SVG forms. The `data` directory copies the frozen study inputs and tables; authoritative per-case receipts and ZIPs remain under `runs/v02-development-20261103` at the repository root.

From the repository root:

```powershell
python -m pip install -r requirements-validated.txt
python -m pip install -r paper/v02/requirements-paper.txt
python -m pip install -e .
python paper/v02/build_figures.py
python paper/v02/build_pdf.py
python paper/v02/render_pdf.py
python paper/v02/package_sources.py
```

The render step requires Poppler's `pdftoppm` on PATH and writes QA images under `output/paper-v02-render`. The paper PDF and source archive are produced under `output/pdf`, then copied byte-for-byte to `publications/v02` for publication. Rebuilding the figures verifies all 48 saved receipts and evidence ZIPs without generating new experiments. Re-running the scientific study uses a new output directory and the commands in `docs/v02-results.md`.

Exact numerical replay is platform/CPU/library dependent. The frozen receipts preserve their original exact hashes; the CLI reports a mismatch rather than claiming portable bitwise reproduction. The paper is a local research manuscript, not a peer-reviewed publication or hardware validation.
