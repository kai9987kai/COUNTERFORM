# Research position and prototype protocol

## What this build tests

Can a decision-sensitive experiment-selection heuristic improve finite absorber decisions relative to passive, random and predictive-disagreement acquisition, under a shared measurement budget? Can an independent adequacy audit reject a misspecified model library even when the model weights are concentrated?

These are hypotheses. A small local pilot does not establish a benefit. Retain failure cases and negative reductions.

## Related primary work

- [AutoSciLab](https://arxiv.org/abs/2412.12347) connects active experiments, learned representations and interpretable equation discovery. An autonomous hypothesis/experiment loop is established prior art.
- [Active Learning of Model Discrepancy with Bayesian Experimental Design](https://arxiv.org/abs/2502.05372) studies sequential experiment selection for learning simulator discrepancy. Detecting a mismatch is not by itself a novel contribution.
- [Goal-driven Bayesian Optimal Experimental Design](https://arxiv.org/abs/2605.26093) optimises experiments for downstream decision objectives. COUNTERFORM's finite disagreement heuristic is not an implementation of that paper and is not exact Bayesian information gain.

The prototype is an independently implemented bounded experiment, not a reproduction of these systems. No world-first or publication-quality result is claimed.

## Data and assumptions

Synthetic instrumented one-dimensional motion supplies position, velocity, acceleration and applied force with known primary mass. Force-balance regression assumes these channels are available. It is not equation discovery from images or noisy position derivatives. Candidate laws, forcing menu, search grid, audit threshold and challenge envelope are explicit in the engine and the saved validation record. Measurement noise is not a calibrated physical sensor model.

Acquisition, audit and challenge cases are separate. Audit data may inform a support/abstention verdict but are not used to refit coefficients or tune the chosen design. Ground-truth coefficients belong only to the synthetic observation/evaluation layer. The out-of-library world tests a declared omission; it cannot represent arbitrary unknown physics.

Model weights use a finite-library scoring approximation rather than a calibrated posterior over all physical laws. The design-sensitive selector is a heuristic; solver agreement checks integration accuracy for shared dynamics, not correctness of the physical equations. Frequency-response search uses an approximation, whereas challenge outcomes come from nonlinear time-domain simulation.

## Controls and reporting

Use paired world seeds and identical noise/budget settings across passive/random/active/counterform strategies. Compare selected absorber to no absorber and nominal fit. Any oracle is a retrospective per-challenge finite-grid diagnostic and not a globally optimal or necessarily constraint-feasible invention. Report pooled RMS reduction across challenges, worst challenge reduction, unsupported model sets, constraint violations and raw per-run records. Pooled reduction is `100 * (1 - sqrt(mean(selected_rms**2)) / sqrt(mean(baseline_rms**2)))`; it is not the arithmetic mean of challenge reductions. Equal experiment counts are not equal CPU budgets. The shared 30-entry grid recipe is rescaled from each fit's reference stiffness. Report acquisition/audit/evaluation counts separately where available.

The benchmark CLI writes all receipts, a CSV and descriptive summary. It makes no significance claim. Freeze protocol and reserve unseen seeds before any confirmation study; do not tune parameters on confirmation outcomes.

## Boundaries

No free-form symbolic search, neural world model training, topology synthesis, material optimisation, hardware control, cross-domain transfer, fatigue/stress analysis, manufacturing validation or real-world guarantee is implemented. The first build supplies interfaces and evidence for investigating a small part of the larger COUNTERFORM proposal.
