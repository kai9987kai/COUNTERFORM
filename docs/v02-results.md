# COUNTERFORM v0.2 development study

Author: kai9987kai · 3 November 2026 · protocol 0.2.0

The completed 48-run development study does **not** show a design-performance advantage for COUNTERFORM over predictive-disagreement acquisition. Their experiment sequences differed in all 12 paired cases, but they selected the same physical grid design and produced identical challenge outcomes in every pair. The new method changes experiment selection without improving the selected design in this sample.

All 48 cases completed; all 48 receipts and evidence ZIPs verified after serialization. No case was dropped or retried. The frozen plan and Python source remained unchanged during execution. These are local synthetic development results, not a confirmatory trial or physical validation. The original v0.1 paper and its evidence remain unchanged.

## Protocol and artifacts

The [frozen plan](protocols/v02-development.json) crossed seeds 101, 103, 107 and 109 with cubic, combined nonlinearities (`unmodelled`, the historical identifier), and omitted-memory worlds. Each used passive, random, predictive disagreement (`active`), and COUNTERFORM acquisition with budget 4 and noise 0.01. Each run evaluated three held-out conditions. The [method](research-v02.md) specifies the eight-law library, 24 sensitivity particles, common 30-design grid, approximate CVaR/mean decision rule, joint audit and abstention policy.

- [Standalone study report](../runs/v02-development-20261103/report.html)
- [Complete summary](../runs/v02-development-20261103/summary.json)
- [All 48 run records](../runs/v02-development-20261103/results.csv)
- [All 36 paired comparisons](../runs/v02-development-20261103/paired.csv)
- [Per-case receipts, reports and ZIPs](../runs/v02-development-20261103/)

## Candidate design outcomes

Each cell contains four seeds. Pooled reduction is computed within each run from the ratio of pooled displacement RMS values; the table then takes an arithmetic mean across seeds. Worst reduction is each run's least favourable condition, averaged across seeds. Negative-condition counts use all 12 conditions in a cell. These describe the **exploratory absorber**, including runs that abstained from recommending it.

| World | Strategy | Mean pooled reduction % | Mean worst reduction % | Joint audit passes / 4 | Abstentions / 4 | Negative conditions / 12 |
|---|---|---:|---:|---:|---:|---:|
| Cubic | Passive | 31.65 | −19.40 | 0 | 4 | 3 |
| Cubic | Random | 35.49 | −26.60 | 4 | 0 | 4 |
| Cubic | Disagreement | 30.50 | −23.91 | 4 | 0 | 4 |
| Cubic | COUNTERFORM | 30.50 | −23.91 | 4 | 0 | 4 |
| Combined | Passive | 29.50 | 3.03 | 0 | 4 | 0 |
| Combined | Random | 29.50 | 3.03 | 0 | 4 | 0 |
| Combined | Disagreement | 29.50 | 3.03 | 0 | 4 | 0 |
| Combined | COUNTERFORM | 29.50 | 3.03 | 0 | 4 | 0 |
| Memory | Passive | 34.77 | 6.70 | 0 | 4 | 1 |
| Memory | Random | 39.11 | −13.60 | 2 | 2 | 4 |
| Memory | Disagreement | 39.11 | −13.60 | 3 | 1 | 4 |
| Memory | COUNTERFORM | 39.11 | −13.60 | 2 | 2 | 4 |

Across all runs, 28 of 144 challenge conditions worsened RMS displacement. No selected design violated the two declared illustrative displacement/stroke limits at sampled output times within 7-14 s. These checks do not bound continuous peaks or the initial 0-7 s trajectory, and do not establish stability, manufacturing suitability or safety. The maximum independent solver discrepancy was 3.58 × 10⁻⁸, covering only each run's first-challenge baseline and selected displacement trajectories.

## Paired experiment-selection findings

Differences below are COUNTERFORM minus control, in percentage points of each run's pooled reduction. There are 12 matched world/seed pairs per row. These are descriptive comparisons without confidence intervals or significance claims.

| Control | Mean paired difference | Minimum | Maximum | Same selected grid design / 12 | Same acquisition sequence / 12 |
|---|---:|---:|---:|---:|---:|
| Predictive disagreement | 0.00 | 0.00 | 0.00 | 12 | 0 |
| Random | −1.66 | −19.97 | 0.00 | 11 | 0 |
| Passive | 1.06 | −19.97 | 15.36 | 7 | 0 |

The random-control difference comes from one cubic case; the other 11 pairs have equal design outcomes. COUNTERFORM's modest mean difference from passive combines positive and negative pairs. Neither comparison supports a general advantage. Different acquisitions alone are insufficient evidence of decision value, and this finite grid often maps different fits to the same design.

## Audit and recommendation limits

The joint audit passed 19 of 48 runs; the other 29 abstained. All 16 combined-world runs failed despite the new library representing its cubic/friction/drag terms. All four passive cubic runs also failed. Adding terms therefore did not solve noisy identification or trajectory adequacy in this study.

Conversely, seven of the 16 omitted-memory runs passed: random and COUNTERFORM at seeds 101 and 107, and disagreement at seeds 101, 107 and 109. The instantaneous library can approximate this hidden mechanism sufficiently to pass these finite diagnostics. The gate is not a calibrated detector of missing physics. COUNTERFORM and disagreement had identical memory-world candidate designs but different audit/recommendation decisions at seed 109; recommendation outcomes must not be inferred from candidate-design reductions.

These findings motivate separate future work on identification bias, audit discrimination and richer decision-sensitive design spaces. They do not justify tuning thresholds on this same study or claiming that the stricter gate reliably rejects omitted mechanisms.

## Verification and reproduction

Validation used Python 3.12.10, NumPy 2.4.3 and SciPy 1.17.1. At the pre-study source freeze, the complete Python suite passed 152 tests; 11 frontend checks and the production build passed. Independent science, integration and delivery reviews resulted in regression fixes for oracle feasibility, narrow response roots, malformed comparison settings and missing failure/constraint details in the report. The 82-artifact preservation manifest passed, and an original legacy receipt reproduced numerically while correctly reporting changed package source. A separately installed wheel completed a v0.2 memory study and verified its receipt.

The frozen plan SHA-256 is `a6ec7a0e6118f56535b3242fd321cd54baa3060ff725edd07b24967424e892cf`. The study's recursive Python source SHA-256 is `c6111b4f22b3919f1a15cecc35a97406dc93720b0ba7d4ca01f3129e91f5db59`. Hashes detect changes relative to these records; they do not authenticate authorship.

Install the recorded numerical environment and use a new output directory:

```powershell
python -m pip install -r requirements-validated.txt
python -m pip install -e ".[dev]"
python -m counterform.studies docs/protocols/v02-development.json --output runs/v02-development-replay
python -m counterform verify runs/v02-development-20261103/memory/101/counterform/evidence.zip
python -m counterform replay runs/v02-development-20261103/memory/101/counterform/receipt.json
```

Exact numerical equality depends on dependencies and platform. Four seeds, related world variants, approximate likelihoods, sensitivity weights, a small physical grid, and transient RMS windows restrict interpretation. Equal acquisition counts do not equal forcing-energy or computation budgets. No quantitative v0.1-to-v0.2 performance comparison is claimed because the scientific protocol and design grid changed.
