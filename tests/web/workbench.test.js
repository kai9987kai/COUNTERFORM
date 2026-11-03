import test from 'node:test';
import assert from 'node:assert/strict';
import { number, compact, lineChart } from '../../web/src/charts.js';

const data = await import('../../web/src/study-data.js').catch(() => ({}));

test('missing values are not presented as measured zero', () => {
  for (const value of [null, undefined, '', ' ', false, NaN, Infinity]) {
    assert.equal(number(value), '—');
    assert.equal(compact(value), '—');
  }
  assert.equal(number(0), '0.00');
});

test('invalid chart samples break paths without poisoning finite coordinates', () => {
  const chart = lineChart({x: [0, 1, 2, 3, NaN], series: [{name: 'Observed', values: [0, NaN, 2, 3, 4], color: '#abc'}], title: 'Trace', xLabel: 'Time', yLabel: 'x'});
  assert.doesNotMatch(chart, /NaN|Infinity/);
  assert.match(chart, /M[^ML]+ M/);
  assert.match(lineChart({x: [null], series: [{values: [1]}]}), /chart-empty/);
});

test('historical jobs retain recorded protocol instead of inheriting the new default', () => {
  assert.equal(data.recordedProtocol?.({config: {world: 'cubic'}}), '0.1.0');
  assert.equal(data.recordedProtocol?.({result: {version: '0.2.0'}}), '0.2.0');
  assert.equal(data.recordedProtocol?.({protocol: '0.2.0', config: {}}), '0.2.0');
});

test('world availability and coverage change with protocol', () => {
  assert.equal(data.worldOptions?.('0.1.0')?.some(w => w.value === 'memory'), false);
  assert.equal(data.worldOptions?.('0.2.0')?.some(w => w.value === 'memory'), true);
  assert.match(data.worldOptions?.('0.1.0')?.find(w => w.value === 'unmodelled')?.help ?? '', /out.of.library/i);
  assert.match(data.worldOptions?.('0.2.0')?.find(w => w.value === 'unmodelled')?.help ?? '', /covered/i);
  assert.equal(data.modelName?.('cubic_friction_drag'), 'Cubic + friction + drag');
});

test('the same candidate must pass both audits and absent legacy forecasts stay absent', () => {
  assert.deepEqual(data.auditMetrics?.({audit_nrmse: .1, adequate: true}, {audit_threshold: .2}), {force: .1, forceThreshold: .2, forecast: null, forecastThreshold: null, forcePassed: true, forecastPassed: null, adequate: true});
  const joint = data.auditMetrics?.({audit_nrmse: .1, forecast_nrmse: .3, force_passed: true, forecast_passed: false, adequate: false}, {force_threshold: .2, forecast_threshold: .2});
  assert.equal(joint?.adequate, false);
  assert.equal(joint?.forecastPassed, false);
  assert.equal(joint?.forcePassed, true);
});

test('recommendation is independent of model adequacy and legacy status is explicit', () => {
  assert.equal(data.recommendationView?.({summary: {adequate: true}, recommendation: {status: 'abstain', message: 'Prediction exceeded bound', reasons: ['bound'], selected_control: 'no_absorber'}})?.status, 'abstain');
  assert.equal(data.recommendationView?.({summary: {adequate: true}})?.status, 'legacy');
});

test('candidate ranking preserves negative scores and explicit selected identity', () => {
  const original = [{id: 'low', score: -3, selected: true}, {id: 'high', score: -1, selected: false}, {id: 'missing', score: null}];
  const ranked = data.rankCandidates?.(original);
  assert.deepEqual(ranked?.map(c => c.id), ['high', 'low', 'missing']);
  assert.equal(ranked?.find(c => c.selected)?.id, 'low');
  assert.equal(original[0].id, 'low');
});

test('playback rejects missing, unaligned, nonfinite and unordered traces', () => {
  const trace = {t: [0, 1, 2], primary: [0, 1, 0], absorber: [0, 0, 1], baseline: [0, 2, 0]};
  assert.equal(data.validPlayback?.(trace), true);
  assert.equal(data.validPlayback?.(null), false);
  assert.equal(data.validPlayback?.({...trace, primary: [0]}), false);
  assert.equal(data.validPlayback?.({...trace, absorber: [0, NaN, 1]}), false);
  assert.equal(data.validPlayback?.({...trace, t: [0, 2, 1]}), false);
});

test('experiment tab navigation wraps and supports Home and End', () => {
  assert.equal(data.tabDestination?.('ArrowRight', 2, 3), 0);
  assert.equal(data.tabDestination?.('ArrowLeft', 0, 3), 2);
  assert.equal(data.tabDestination?.('Home', 2, 3), 0);
  assert.equal(data.tabDestination?.('End', 0, 3), 2);
  assert.equal(data.tabDestination?.('Enter', 0, 3), null);
});

test('unpaired comparisons never expose supplied deltas', () => {
  assert.equal(data.pairedDeltas?.({paired: false, deltas: {reduction_pct: 99}}), null);
  assert.deepEqual(data.pairedDeltas?.({paired: true, deltas: {reduction_pct: -2}}), {reduction_pct: -2});
});

test('scheduled experiments do not claim a scored menu choice when diagnostic candidates exist', () => {
  const experiment = {selector: {name: 'passive', selection_origin: 'passive_schedule'},
    candidates: [{id: 'other', score: 0, decision_gain: .3, selected: false}]};
  assert.equal(data.acquisitionSelection?.(experiment)?.kind, 'predefined');
  assert.equal(data.acquisitionSelection?.(experiment)?.selectedId, null);
  assert.match(data.acquisitionSelection?.(experiment)?.message ?? '', /diagnostic.*not.*selection/i);
  assert.equal(data.acquisitionSelection?.({selector: {selection_origin: 'menu'},
    candidates: [{id: 'chosen', score: -2, selected: true}]})?.selectedId, 'chosen');
});
