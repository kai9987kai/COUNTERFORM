# First descriptive local pilot — 2 November 2026

Protocol: seeds 11 and 23, cubic and unmodelled worlds, budget 3, noise .01, all four acquisition strategies. Sixteen studies total. This is an exploratory development pilot, not frozen confirmation or independent physical validation. All receipts, traces, challenge controls, reports and export manifests are retained in `runs/benchmark`.

Values below are the arithmetic mean across two seeds of each study's **pooled RMS reduction** across its three challenges. They are not mean per-challenge percentage reductions.

| World | Strategy | Mean pooled reduction | Audit passes | Constraint violations |
|---|---|---:|---:|---:|
| Cubic | Passive | 32.35% | 0/2 | 0 |
| Cubic | Random | 32.36% | 2/2 | 0 |
| Cubic | Disagreement | 32.51% | 2/2 | 0 |
| Cubic | COUNTERFORM | 32.51% | 2/2 | 0 |
| Unmodelled | Passive | 27.49% | 0/2 | 0 |
| Unmodelled | Random | 21.91% | 2/2 | 0 |
| Unmodelled | Disagreement | 27.14% | 0/2 | 0 |
| Unmodelled | COUNTERFORM | 27.14% | 0/2 | 0 |

COUNTERFORM and predictive disagreement selected the same acquisitions/outcomes on these cases. This pilot does **not** demonstrate a benefit for the decision-sensitive heuristic. The out-of-library random runs falsely passed the finite audit, while passive cubic runs failed despite an available true law. Model inadequacy decisions depend on excitation, fit quality, measurement noise and the finite audit threshold; they are not correctness guarantees.

The default seed42/cubic/COUNTERFORM/budget5 study achieved approximately 24.05% pooled reduction but **−8.35%** on its worst challenge. Aggregation can hide adverse conditions; inspect the full challenge table.

Each strategy receives the same acquisition count and 30-entry relative grid recipe. Physical candidates depend on the fit; CPU costs differ. Every study additionally runs two audit experiments, three nonlinear challenge conditions, retrospective grid controls and one independent selected-trajectory solver check. An oracle can choose a different design per challenge and is not a deployable policy or a constraint-feasible optimum.

These results motivate investigation rather than a breakthrough claim. A later confirmation study would need a frozen protocol, more paired unseen seeds/worlds, stronger adequacy calibration and matched computational controls.
