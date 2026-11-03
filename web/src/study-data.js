export const finiteValue = value => value !== null && value !== undefined && typeof value !== 'boolean' && !(typeof value === 'string' && !value.trim()) && Number.isFinite(Number(value)) ? Number(value) : null;

export function recordedProtocol(job) {
  return job?.protocol || job?.result?.protocol || job?.result?.version || job?.version || '0.1.0';
}

export function worldOptions(protocol) {
  return [
    {value: 'cubic', name: 'Cubic stiffness', help: 'A nonlinear restoring force challenges the linear assumption.'},
    {value: 'linear', name: 'Linear oscillator', help: 'The simplest law in the library, with linear damping and stiffness.'},
    {value: 'friction', name: 'Smooth Coulomb friction', help: 'Velocity-dependent smooth friction challenges the damping model.'},
    {value: 'unmodelled', name: 'Combined nonlinearities', help: protocol === '0.2.0' ? 'Cubic stiffness, friction and quadratic drag are covered by the expanded composition library.' : 'Combined cubic stiffness, friction and drag form the intentionally out-of-library case.'},
    ...(protocol === '0.2.0' ? [{value: 'memory', name: 'Relaxing force memory', help: 'A hidden relaxing force lies outside the instantaneous eight-law library.'}] : []),
  ];
}

export function modelName(name) {
  if (name === 'linear') return 'Linear oscillator';
  const labels = {cubic: 'Cubic', friction: 'friction', drag: 'drag'};
  const parts = String(name || '').split('_');
  if (!parts.every(part => labels[part])) return name || 'Unknown model';
  if (parts.length === 1) return {cubic: 'Cubic stiffness', friction: 'Smooth friction', drag: 'Quadratic drag'}[name];
  const label = parts.map(part => labels[part]).join(' + ');
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function auditMetrics(model, validation = {}) {
  const force = finiteValue(model.audit_nrmse);
  const forceThreshold = finiteValue(validation.force_threshold ?? validation.audit_threshold);
  const forecast = finiteValue(model.forecast_nrmse);
  const forecastThreshold = finiteValue(validation.forecast_threshold);
  return {
    force, forceThreshold, forecast, forecastThreshold,
    forcePassed: typeof model.force_passed === 'boolean' ? model.force_passed : force !== null && forceThreshold !== null ? force <= forceThreshold : null,
    forecastPassed: typeof model.forecast_passed === 'boolean' ? model.forecast_passed : forecast !== null && forecastThreshold !== null ? forecast <= forecastThreshold : null,
    adequate: model.adequate === true,
  };
}

export function recommendationView(result) {
  const value = result?.recommendation;
  if (!value || !['candidate', 'abstain'].includes(value.status)) return {status: 'legacy', title: 'Legacy study · no recommendation gate recorded', message: result?.summary?.verdict || 'This study records model adequacy and an exploratory selected design.', reasons: [], selectedControl: null};
  return {status: value.status, title: value.status === 'candidate' ? 'Candidate design supported for further investigation.' : 'Abstain · retain the design for exploration.', message: value.message || '', reasons: Array.isArray(value.reasons) ? value.reasons : [], selectedControl: value.selected_control};
}

export function rankCandidates(candidates = []) {
  return candidates.map((candidate, index) => ({...candidate, originalIndex: index})).sort((a, b) => {
    const av = finiteValue(a.score), bv = finiteValue(b.score);
    if (av === null) return bv === null ? a.originalIndex - b.originalIndex : 1;
    if (bv === null) return -1;
    return bv - av || a.originalIndex - b.originalIndex;
  });
}

export function acquisitionSelection(experiment = {}) {
  const rows = experiment.candidates;
  if (!Array.isArray(rows)) return {kind: 'legacy', selectedId: null, message: 'Candidate selection details were not recorded.'};
  const origin = experiment.selector?.selection_origin;
  const scheduled = origin === 'shared_warmup' || origin === 'passive_schedule' || experiment.selector?.name === 'passive' || rows.length === 0;
  if (scheduled) return {kind: 'predefined', selectedId: null, message: 'Diagnostic menu values were not used for this selection.'};
  const chosen = rows.find(row => row.selected === true);
  return {kind: 'menu', selectedId: chosen?.id ?? null, message: chosen ? 'The selected menu identity was recorded.' : 'No selected menu identity was recorded.'};
}

export function validPlayback(trace) {
  if (!Array.isArray(trace?.t) || trace.t.length < 2 || !trace.t.every(Number.isFinite) || trace.t[0] < 0 || trace.t.at(-1) <= 0) return false;
  if (!trace.t.every((time, index) => !index || time > trace.t[index - 1])) return false;
  return ['primary', 'absorber', 'baseline'].every(key => Array.isArray(trace[key]) && trace[key].length === trace.t.length && trace[key].every(Number.isFinite));
}

export function tabDestination(key, index, count) {
  if (!count) return null;
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  if (key === 'ArrowRight') return (index + 1) % count;
  if (key === 'ArrowLeft') return (index + count - 1) % count;
  return null;
}

export const pairedDeltas = comparison => comparison?.paired === true ? comparison.deltas ?? null : null;
