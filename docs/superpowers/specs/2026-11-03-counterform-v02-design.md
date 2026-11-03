# COUNTERFORM v0.2 design

The user requested broad innovation and improvement of the whole existing project. Builder choices below implement that request using the current CPU-local Python and Three.js architecture. The published v0.1 paper and negative evidence remain historical records.

## Approach and boundaries

Prefer a new, versioned scientific protocol plus better evidence and workbench controls. Expanding immediately into neural world models/free-form manufactured CAD would add unvalidated subsystems; cosmetic changes would not address the measured weaknesses. This upgrade instead tests finite decision-risk acquisition, richer structural coverage and independent trajectory criticism. No physical reliability or new research benefit is assumed.

Preserve `counterform/engine.py`, all `runs/benchmark`, `runs/example`, `paper` and the published PDF/source ZIP byte for byte. Keep old numeric replay available. Implement v0.2 in `counterform/v2/` and dispatch through `counterform/protocols.py`. Current package/API defaults become 0.2.0; legacy requests explicitly select 0.1.0. A historical package-source mismatch must not be confused with failed numerical replay.

## Scientific upgrade

- Eight finite model families enumerate subsets of cubic stiffness, smooth friction and quadratic drag, alongside positive linear k/c. All numerical paths must include each term consistently. This remains bounded composition selection, not open-ended equation discovery.
- Deterministic parameter particles from measured-data perturbation/refitting retain parameter uncertainty. Weights/perturbations are explicitly heuristic, not calibrated posteriors. Fit, acquisition and design see sensor data/fitted parameters only.
- Use a shared physical 30-design grid, independent of fitted coefficients, with reference 6 rad/s, masses .08/.16 kg, tuning .75/.9/1/1.1/1.25 and damping ratios .05/.15/.3.
- Cache particle/design losses. The downstream rule minimises .7 weighted CVaR of the worst 20% particle mass plus .3 mean loss. Loss is approximate mean squared displacement over a fixed design forcing envelope, normalised by that particle's no-absorber mean squared displacement. Declare exact envelope/constants in the numerical record.
- COUNTERFORM selects experiments by finite expected decision-risk reduction: fantasy observations reweight particles; the actual downstream rule chooses a design; generating-particle loss is averaged across particles and Gaussian quadrature outcomes. Keep negative scores. Predictive disagreement is a separate control using the same ensemble. No forced policy divergence or efficacy assertions.
- Archive all candidates, selected ID, both scores, before/after expected risk, observation/fantasy assumptions and deterministic tie rule. A planted nuisance-versus-decision unit example must distinguish the two selectors; this proves implementation, not empirical superiority.
- Add a `memory` world with a hidden relaxing force, tau dz/dt + z = eta v. This lies outside the instantaneous library. Existing `unmodelled` is now the covered combined nonlinear world under v0.2; protocol-aware labels must explain that change.
- Freeze fits, particles, design and nominal control before audit. The SAME fitted candidate must pass both measured force-balance residual and a free-running position forecast from known rest/commanded forcing. Report every audit trial and the engineering thresholds; do not claim calibrated error control.
- Explicitly recommend `candidate` or `abstain`, based on audit and pre-challenge design predictions. An unsupported candidate remains visible for exploration. The recommendation cannot use held-out performance to change the design or status.
- Evaluate three separate nonlinear challenges, retain negative outcomes, selected/nominal/no-absorber controls, per-condition oracle diagnostics, and one common constraint-feasible finite-grid oracle across challenges. Include a no-absorber oracle fallback. Check selected and baseline trajectories with independent integration; scope must be explicit.

## Operation and evidence

Add protocol-aware run validation/CLI replay/history. Preserve legacy configurations exactly; top-level job protocol is separate from its five-field engine config. Add cooperative cancellation at progress checkpoints with no partial completed receipt. Compare two verified completed runs descriptively; provide paired deltas only when world/seed/noise/budget/protocol/challenge/grid/evaluation settings match. Duplicated evidence and malformed metrics reject cleanly.

Bound file/archive/manifest/member reads, preserve intact historical bundles, and label reports using recorded simulation version rather than current exporter version. Benchmark preflight rejects duplicates/invalid cases before any output or solver call and defaults away from protected historical directories.

## Workbench

Retain current visual style. Add protocol choice, new model/world names, acquisition-candidate diagnostics, force/forecast audit columns, explicit recommendation, cancellation and isolated two-run comparison. Old histories remain inspectable. Fix stale playback, missing metric handling, invalid chart coordinates and experiment keyboard/focus behavior. Mobile layout must remain usable.

## Verification and delivery

Test meaningful numerical and lifecycle behavior first, run the full suite/build, independently review code, verify old hashes and actual legacy replay, inspect browser workflows. Add repeatable CI. Freeze a new small paired development protocol before running it; report all its outcomes and abstentions without rewriting the v0.1 paper. Keep research work on `codex/counterform-v02` in the existing checkout.
