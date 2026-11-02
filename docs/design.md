# COUNTERFORM v0.1 — local falsification-driven invention lab

Build instruction: the user chose “build it” after supplying the COUNTERFORM proposal. Implementation defaults below are builder decisions, not extra requirements attributed to the user.

## Intent and scope
An executable CPU-local research workbench closes the loop from observations, finite model selection, informative experiments, robust absorber search, and held-out challenges to inspectable evidence. Python 3.12+, NumPy, SciPy and FastAPI own the numerical work; a locally bundled Three.js interface visualises the mechanism and actual results. No cloud model, GPU or credentials are needed.

The initial domain is a forced one-dimensional oscillator with known primary mass. Candidate laws are linear damping/stiffness, cubic stiffness, and smooth Coulomb friction. Hidden combined nonlinearities provide an out-of-library case. Measurements include position, velocity, acceleration and applied force; this is an instrumented synthetic identification task, not discovery from video. The learner cannot consume hidden truth parameters.

## Chosen approach and alternatives
The broad autonomous CAD/science engine is a roadmap. The first build uses a finite interpretable law library, bounded numerical design search and a conceptual parametric absorber. A neural world model would add training requirements without establishing the research question; a visual-only mockup would lack scientific evidence. The local numerical lab is the builder's selected implementation of the user's prototype request.

## Scientific contract
Four acquisition strategies share observation and design budgets: passive low-amplitude sampling, random experiments, predictive disagreement, and a decision-sensitive disagreement heuristic (COUNTERFORM). Do not call the heuristic exact Bayesian information gain. Fit nonnegative physical coefficients from force balance with complexity-aware model weights. Keep audit experiments separate from acquisition. An adequacy threshold may reject every candidate; model weights alone do not establish adequacy.

Search a finite grid of tuned mass absorber mass/stiffness/damping with a frequency-response approximation across plausible models. Evaluate the selected design and controls against separate nonlinear truth simulations under changed load, frequency and component tolerance. Include no absorber, nominal fit, and finite-grid oracle diagnostics. Report negative outcomes, constraint violations, audit residuals and solver agreement. Any percentage reduction is conditional on the selected synthetic challenge set.

No free-form symbolic discovery, learned neural dynamics, manufacturing qualification, topology invention, physical hardware, cross-domain transfer or real-world guarantee is claimed. CAD exports describe a conceptual assembly; dimensions are illustrative and not validated spring manufacture.

## Workbench
Dark instrument-panel interface with a 3D oscillator/absorber scene, runnable scenario controls, experiment timeline, model probabilities and equations, response plots, held-out comparisons, explicit adequacy verdict, and downloadable JSON/ZIP/STL/parametric design. Idle state is clearly labelled. Completed traces drive playback. Responsive layouts, keyboard labels and visible errors are required.

## Evidence and operation
Async local API jobs, bounded inputs and queue, deterministic numeric results, saved run history, canonical JSON receipts and SHA-256 manifests. A CLI reruns a receipt and compares numerical content. An archive verifier rejects missing/changed/unexpected entries and unsafe archive paths. Host binds to 127.0.0.1 by default. Packaging includes web assets, one-command launch instructions, benchmark command, tests and research limitations.

## Acceptance
Run actual studies end to end; demonstrate reproducibility and tamper detection; verify independent integration agreement and finite held-out metrics; exercise API invalid inputs and browser run/download/history flows; retain representative local evidence without claiming an established research benefit.
