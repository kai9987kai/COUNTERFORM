# COUNTERFORM v0.2 scientific protocol

Version 0.2 addresses diagnostic failures in the original pilot by changing the method and making its decisions inspectable. The [completed development study](v02-results.md) found no design-performance advantage over disagreement acquisition and retained substantial audit limitations.

## Model and uncertainty representation

The instantaneous library enumerates all eight subsets of cubic stiffness, smooth friction and quadratic drag, in addition to linear stiffness/damping. Every fit, force prediction, response approximation and free-running forecast includes the declared terms. The combined nonlinear world from v0.1 is now covered. A new memory world adds a relaxing force satisfying `tau dz/dt + z = eta v`, with eta = 4.5 and tau = 0.22; this mechanism is outside the instantaneous library.

The learner sees measured time, displacement, velocity, acceleration and applied force, with known primary mass 1 kg. It does not read hidden truth parameters. Each family supplies its fitted point and two deterministic residual-perturbation refits, creating 24 particles. The perturbations use alternating 21-sample blocks. Effective complexity score count is 20 times acquisition-trial count, with 5% family exploration mass. These are sensitivity and weighting conventions, not posterior coverage or an errors-in-variables correction.

## Design and experiment selection

The same physical grid is used across seeds, strategies and hypothetical posterior updates: masses 0.08/0.16 kg; reference 6 rad/s; tuning 0.75/0.9/1/1.1/1.25; damping ratios 0.05/0.15/0.3. This creates 30 designs with fixed SI stiffness and damping. The training envelope has 39 forcing pairs: frequencies 3 through 9 rad/s in 0.5 increments and amplitudes 0.75, 1.5 and 2 N. The loss for each particle/design is its mean squared approximate displacement divided by that particle's no-absorber mean squared displacement.

The downstream decision rule minimises 0.7 times the upper 20%-mass weighted CVaR plus 0.3 times the weighted mean loss. Fractional probability atoms are handled explicitly. A describing-function surrogate estimates equivalent stiffness/damping from the baseline orbit, then attaches the absorber. Polynomial cases partition roots at analytic stationary points. Friction cases locate derivative extrema numerically with 129 samples and bounded local refinement; they have no global guarantee of finding the lowest branch. The record saves root bounds and solver tolerances. The surrogate can miss nonlinear branches and changes caused by coupling.

For each candidate experiment, three Gaussian quadrature outcomes per generating particle reweight the frozen ensemble. The actual downstream CVaR/mean rule selects a hypothetical design. Its loss under the generating particle is averaged across particles and quadrature outcomes. Acquisition uses current expected loss minus this hypothetical expected loss. Negative values are retained. The quadrature nodes are minus/zero/plus sqrt(3) with weights 1/6, 2/3 and 1/6. The scalar peak-displacement likelihood floor and exact surrogate constants are saved in each record.

The fantasy update only reweights particles, whereas the next actual observation refits the family coefficients. This mismatch is explicit: the score is an approximate decision-risk surrogate, not exact Bayesian value of information. Predictive disagreement uses the same particles and menu as a separate control. A planted nuisance-versus-decision test establishes that the implementations can choose differently; it establishes no empirical advantage on oscillator data.

All scored menu candidates are retained, including unselected cases, their likelihood scales, disagreement, decision gain, prior/post-update expected risk, fantasy count and selected flag. Scheduled/warmup trials are labelled as such. Deterministic ties use the first menu entry.

## Audit and abstention

Fitted coefficients, particles, selected design and nominal control freeze before audit. Audit frequencies/amplitudes remain outside the acquisition menu. Force-balance residual error and free-running position-forecast error must BOTH pass for the SAME fitted family across audit trials. The forecast starts from known rest and uses commanded forcing; measured audit states are not forecast inputs. Failed integration visibly fails forecast support.

The force threshold is 0.08 + 2 × noise and forecast threshold 0.15 + 3 × noise. These engineering diagnostics have no calibrated statistical error guarantee. Support plus a predicted design objective below the no-absorber reference permits a conditional conceptual candidate recommendation. Otherwise the system abstains while retaining the exploratory design and its actual challenge outcomes. Recommendation is fixed before held-out evaluation.

## Controls and evaluation

The three held-out nonlinear conditions and illustrative displacement/stroke limits are recorded independently. Their secondary forcing tone at 1.73 times the primary frequency is not an integer harmonic. Selected, nominal and finite-grid controls share forcing, component tolerances and integration settings. Constraint peaks and oracle feasibility use sampled output times within 7-14 s, not continuous peaks or the initial 0-7 s trajectory. A common constraint-feasible oracle selects one grid member across all three conditions. A no-absorber control is eligible only if it also satisfies every sampled primary displacement limit. If no control is eligible, oracle metrics are null and the record explicitly reports no feasible control. Separate per-condition unconstrained optima remain diagnostics.

The RMS window remains 7–14 s and includes transient effects. Pooled reduction is a ratio of pooled RMS values, not a mean of condition percentages. Every adverse condition, constraint violation and abstention is retained. Independent integration checks state their exact trajectory scope and error, without implying physical validation.

## Study and prior art

`docs/protocols/v02-development.json` is a fixed development plan, prepared before its outcomes: seeds 101, 103, 107 and 109; cubic/combined/memory worlds; all four acquisition strategies; budget 4; noise 0.01. It contains 48 runs. This is not externally preregistered confirmation. Seeds share primary parameters across world variants, and within-run challenges are not independent replicates. Matched trial counts and physical grid do not match forcing-energy or CPU costs. Descriptive paired differences and failure counts are reported without significance claims.

Downstream-objective experimental design is established prior work, for example [GoBOED](https://arxiv.org/abs/2605.26093). Model-discrepancy-aware design already includes a spring–mass–damper setting in [Catanach and Das](https://arxiv.org/abs/2304.07949). This implementation does not reproduce those methods or inherit their theoretical results. Its contribution is an inspectable finite computational protocol, contingent on the new measured outcomes.

The v0.1 paper, source archive and numerical artifacts remain unchanged. New results must be interpreted within this protocol; expanding a library alone cannot establish better design, calibrated model rejection, manufacturing qualification or real-world reliability.
