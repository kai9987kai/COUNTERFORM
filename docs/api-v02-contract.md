# Version 0.2 integration contract

## Scientific worker ownership
Own `counterform/v2/**`, `tests/test_v2*.py`. Public import: `from counterform.v2 import run_study, validate_config`. Both accept only the original five fields (seed/world/strategy/budget/noise); world additionally accepts `memory`; defaults otherwise match v0.1. `run_study(config: dict, progress=None) -> dict` deterministic, finite JSON; result.version and result.protocol are `0.2.0`. Never edit legacy engine.py. Use original result field schema in docs/api-contract.md, with additions below. Root/other workers never depend on private numeric helpers.

Required additions:
```
models[i]: {name,equation,weight,parameters:{k,c,alpha,friction,drag},
  audit_nrmse,forecast_nrmse,adequate,force_passed,forecast_passed,
  parameter_intervals:{parameter:[low,high]},audit_trials:[...]}
experiments[i]: {existing fields..., selector:{name,score_label,tie_rule,...},
  candidates:[{id,frequency,amplitude,score,disagreement,decision_gain,
                risk_before,risk_after,fantasy_count,selected}]}
recommendation: {status:'candidate'|'abstain',message:string,reasons:[string],
                 selected_control:'absorber'|'no_absorber'}
decision: {particle_count,grid_id,selection_rule,loss_definition,...}
validation: {existing fields...,forecast_threshold,force_threshold,
              solver_scope:string,solver_checks:[...],design_grid_id,
              acquisition_experiments,forecast_audit_experiments,...}
oracle: {common_grid_index:int|null,feasible_count,common_reduction_pct,...}
challenges[i]: {existing fields...,common_oracle_rms,recommended_rms}
```
All model names are underscore combinations in order cubic/friction/drag (or linear). Forecast threshold is common engineering diagnostic; audit model errors are finite, solver failures explicitly fail rather than NaN/Infinity. `validation.solver_relative_error` is maximum checked discrepancy. Include exact design envelope, particle construction, quadrature and all operational budgets in the result. The legacy `summary` and response/playback shapes continue to work; `summary.reduction_pct` remains tentative selected-design pooled RMS reduction (not recommendation-policy gain).

## Integration worker ownership
Own `counterform/protocols.py`, `server.py`, `evidence.py`, `__main__.py`, `comparison.py` plus `tests/test_protocols.py`, `test_comparison.py`, `test_server_v2.py`, `test_evidence_v2.py`, `test_cli_v2.py`. May minimally adjust existing server/CLI tests for explicit legacy protocol where needed; never change assertions merely to hide failures. Root owns __init__.py and packaging version.

`protocols.DEFAULT_PROTOCOL='0.2.0'`, SUPPORTED_PROTOCOLS=('0.1.0','0.2.0').
`normalize_request(flat_request: dict, *, default_protocol=DEFAULT_PROTOCOL)->dict` returns flat validated five fields plus protocol. `run_study(flat_request, progress=None, *, cancelled=None)->dict` strips protocol, calls the selected engine and wraps progress to raise `StudyCancelled` when `cancelled()` returns true. Legacy result/config unchanged. `receipt_protocol(receipt)->str` derives old records from result.version, never selects new default for an old version. `replay_result(receipt, progress=None)->dict` convenience routes by recorded protocol.

POST /api/runs accepts original flat request plus protocol (optional, default0.2.0). Jobs expose `protocol` at top level and original clean five-field config, result on completion. Missing protocol on persisted pre-upgrade jobs means 0.1.0. GET /api/health adds `protocols:['0.1.0','0.2.0']`.
POST /api/runs/{id}/cancel -> job; terminal statuses include cancelled. Cooperative checkpoint cancellation may wait for in-flight SciPy solve. Artifacts unavailable until complete (409). Never persist partial receipts.
POST /api/compare body `{run_ids:[id1,id2]}` -> `{paired:bool,mismatches:[string],runs:[{id,protocol,config,summary,recommendation}],deltas:{reduction_pct,worst_reduction_pct,design_rms,challenge_reductions:[{name,delta}]}|null,note:string}`. Delta direction is second minus first. Incompatible records still return descriptive summaries with paired=false; duplicates/malformed evidence/unfinished runs return 422/409. Backend owns compatibility and metric recomputation.
`comparison.compare_receipts(receipts:list[dict])->dict` provides same comparison excluding job IDs. Use source result protocol/challenge specs/design grid, never imply efficacy from one pair.
CLI run/benchmark adds --protocol. Replay routes recorded version. Benchmark rejects duplicates and invalid full plan before writes; new defaults runs/manual-v02 and runs/benchmark-v02; refuse protected historical output directories. New bundle semantics may be versioned/optional; intact original bundle validation must keep passing. Reports show recorded version plus current exporter separately.

## Frontend worker ownership
Own `web/**`, generated `counterform/web/**`, package.json/lockfile/vite config if needed; optional frontend node tests under `tests/web/` and npm test script. API fields above fixed. New protocol dropdown values exactly0.1.0/0.2.0; sends protocol flat in POST. Legacy history lacks protocol; derive result.version or0.1.0. New combined world is covered, memory is omitted. Both audits/recommendation/candidate ranking conditional on actual fields, not inferred zero defaults. Comparison state cannot overwrite current job/playback/export; candidate rows use selected boolean, no rounded-score winner reconstruction. New cancelling status handles cancel_requested and cancelled.

## Root ownership
Docs, __init__.py/pyproject version0.2.0, .github CI, frozen experiment protocol, validation scripts, research runner/report (`counterform/studies.py`, `tests/test_studies.py`), legacy preservation tests. Root will run final paired study after all code checks; no worker may overwrite runs/benchmark/runs/example/paper/publications artifacts. Do not commit or push from workers.
