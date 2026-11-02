# Implementation interfaces

## Scientific engine (owned by scientific-core agent)
`counterform.engine.run_study(config: dict, progress=None) -> dict`. Config: `seed` integer 0..2147483647, `world` one of `linear`, `cubic`, `friction`, `unmodelled`, `strategy` one of `passive`, `random`, `active`, `counterform`, `budget` integer 2..8, `noise` float 0.0..0.05. `progress(fraction: float, message: str)` is optional. Deterministic output, ordinary JSON types, finite floats. No timestamps or random IDs in output. Engine validates standalone calls too. Use version `0.1.0`.

Result fields (all required):
```
{
 "config": {"seed":42,"world":"cubic","strategy":"counterform","budget":5,"noise":0.01},
 "summary": {"reduction_pct":0.0,"baseline_rms":0.0,"design_rms":0.0,"worst_reduction_pct":0.0,"adequate":true,"verdict":"...","best_model":"cubic","constraint_violations":0},
 "models": [{"name":"linear","equation":"...","weight":0.0,"parameters":{"k":1.0,"c":0.1,"alpha":0.0,"friction":0.0},"audit_nrmse":0.0,"adequate":false}],
 "experiments": [{"index":1,"frequency":1.0,"amplitude":1.0,"score":0.0,"reason":"...","weights":{"linear":0.0,"cubic":0.0,"friction":0.0},"trace":{"t":[],"x":[],"v":[],"force":[]}}],
 "design": {"mass":0.1,"stiffness":1.0,"damping":0.1,"tuning_ratio":1.0,"mass_ratio":0.1,"objective":0.0},
 "response": {"frequencies":[],"baseline":[],"selected":[],"nominal":[]},
 "challenges": [{"name":"...","baseline_rms":0.0,"design_rms":0.0,"nominal_rms":0.0,"reduction_pct":0.0,"constraint_violation":false}],
 "validation": {"solver_relative_error":0.0,"audit_threshold":0.0,"held_out":true,"notes":[]},
 "playback": {"t":[],"baseline":[],"primary":[],"absorber":[]},
 "ledger": [{"kind":"observation|hypothesis|experiment|design|validation","message":"..."}],
 "limitations": ["..."]
}
```
Additional meaningful fields allowed. Trace arrays may be decimated to <=500 samples. Measured raw acceleration data must be available in evidence (additional fields acceptable). Units: seconds, metres, kilograms, newtons, radians/second unless UI converts Hz explicitly.

## API (owned by root)
`GET /api/health` returns `{status:'ok', version:'0.1.0'}`.
`POST /api/runs` config -> HTTP 202 `{id,status,progress,message,created_at,config}`. Poll `GET /api/runs/{id}` -> same plus `result` when `status='complete'`, `error` if failed; status queued/running/complete/failed. Progress in [0,1]. `GET /api/runs` -> `{runs:[job summaries newest first]}`.
`GET /api/runs/{id}/receipt` JSON attachment; `/bundle` ZIP; `/design.stl` conceptual STL; `/design.json` parameterised CAD JSON. `/report` standalone HTML evidence report. Unknown run 404, unfinished download 409, invalid input 422. No truth metadata from engine is made available until run completion.

## UI (owned by frontend agent)
Own `web/` and root `package.json`, `package-lock.json`, `vite.config.js`. Vite builds to `counterform/web/` (emptyOutDir permitted only that exact generated directory), main index uses local bundled dependencies. Root Python mounts compiled web directory after API routes. No separate production frontend server. Use API contract above. Include helpful first-run empty state and no fabricated preloaded result. UI can show illustrative moving apparatus before a run, labelled preview. Use local SVG/icon geometry, no image generation needed. All visible control actions must work. Bundle/report/CAD links attach current run ID. UI may use tabs Lab / Evidence / Protocol, history, play/pause and camera reset.
