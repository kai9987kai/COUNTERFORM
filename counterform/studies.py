"""Execute a bounded, frozen development plan without hiding failed cases."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import re
import sys

from .evidence import canonical, make_receipt, verify_receipt, build_bundle, report_html, source_digest

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ('passive', 'random', 'active', 'counterform')


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError('Study plan must be an object')
    allowed = {'schema', 'name', 'protocol', 'seeds', 'worlds', 'strategies', 'budget', 'noise', 'purpose', 'prepared_on'}
    if set(plan) - allowed or plan.get('schema') != 'counterform.study.v1':
        raise ValueError('Unsupported study schema or fields')
    if not isinstance(plan.get('name'), str) or re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', plan['name']) is None:
        raise ValueError('Study name must use lowercase letters, numbers and hyphens')
    if plan.get('purpose', 'development') not in ('development', 'confirmation'):
        raise ValueError('Study purpose must be explicit development or confirmation')
    for key, limit in [('seeds', 8), ('worlds', 5), ('strategies', 4)]:
        values = plan.get(key)
        if not isinstance(values, list) or not 1 <= len(values) <= limit:
            raise ValueError(f'{key} must contain 1..{limit} unique entries')
        if any(isinstance(v, (list, dict)) for v in values) or len(set(values)) != len(values):
            raise ValueError(f'{key} must not contain duplicates')
    if any(s not in STRATEGIES for s in plan['strategies']):
        raise ValueError('Unknown study strategy')
    count = len(plan['seeds']) * len(plan['worlds']) * len(plan['strategies'])
    if count > 64:
        raise ValueError('Study plan exceeds 64 cases')
    from .protocols import normalize_request
    clean = {**plan, 'purpose': plan.get('purpose', 'development')}
    for world in clean['worlds']:
        for seed in clean['seeds']:
            for strategy in clean['strategies']:
                normalize_request({'protocol': clean.get('protocol'), 'seed': seed, 'world': world,
                                   'strategy': strategy, 'budget': clean.get('budget'), 'noise': clean.get('noise')})
    canonical(clean)
    return {**clean, 'case_count': count}


def _metrics(result: dict) -> dict:
    challenges = result['challenges']
    if not isinstance(challenges, list) or not challenges:
        raise ValueError('Study has no challenge evidence')
    baseline, selected, reductions = [], [], []
    for challenge in challenges:
        b, s = challenge['baseline_rms'], challenge['design_rms']
        if isinstance(b, bool) or isinstance(s, bool) or not isinstance(b, (float, int)) or not isinstance(s, (float, int)):
            raise ValueError('Challenge RMS must be numeric')
        if not math.isfinite(b) or not math.isfinite(s) or b <= 0 or s < 0:
            raise ValueError('Challenge RMS must be finite with positive baseline')
        baseline.append(b * b); selected.append(s * s)
        reductions.append(100 * (1-s/b))
    reduction = 100 * (1-math.sqrt(math.fsum(selected)/math.fsum(baseline)))
    if not math.isclose(reduction, result['summary']['reduction_pct'], abs_tol=1e-8):
        raise ValueError('Stored summary disagrees with challenge RMS')
    if not math.isclose(min(reductions), result['summary']['worst_reduction_pct'], abs_tol=1e-8):
        raise ValueError('Stored worst-case summary disagrees with challenges')
    return {'reduction_pct': reduction, 'worst_reduction_pct': min(reductions),
            'design_rms': math.sqrt(math.fsum(selected)/len(selected)),
            'adequate': bool(result['summary']['adequate']),
            'abstain': result.get('recommendation', {}).get('status') == 'abstain',
            'negative_challenges': sum(v < 0 for v in reductions),
            'constraint_violations': sum(bool(c['constraint_violation']) for c in challenges)}


def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _summarize(plan, records, failures, plan_sha, code_sha):
    comparisons, paired = [], []
    for world in plan['worlds']:
        for strategy in plan['strategies']:
            subset = [r for r in records if r['world'] == world and r['strategy'] == strategy]
            comparisons.append({'world': world, 'strategy': strategy, 'n': len(subset),
                                'mean_reduction_pct': math.fsum(r['reduction_pct'] for r in subset)/len(subset) if subset else None,
                                'mean_worst_reduction_pct': math.fsum(r['worst_reduction_pct'] for r in subset)/len(subset) if subset else None,
                                'adequacy_passes': sum(r['adequate'] for r in subset),
                                'abstentions': sum(r['abstain'] for r in subset),
                                'negative_challenges': sum(r['negative_challenges'] for r in subset),
                                'constraint_violations': sum(r['constraint_violations'] for r in subset)})
    lookup = {(r['world'], r['seed'], r['strategy']): r for r in records}
    for world in plan['worlds']:
        for seed in plan['seeds']:
            cf = lookup.get((world, seed, 'counterform'))
            if cf is None:
                continue
            for control in ('active', 'random', 'passive'):
                other = lookup.get((world, seed, control))
                if other is not None:
                    paired.append({'world': world, 'seed': seed, 'comparison': 'counterform-minus-'+control,
                                   'reduction_delta_pp': cf['reduction_pct']-other['reduction_pct'],
                                   'worst_delta_pp': cf['worst_reduction_pct']-other['worst_reduction_pct'],
                                   'acquisitions_equal': cf['acquisitions'] == other['acquisitions'],
                                   'selected_grid_equal': cf['selected_grid_index'] == other['selected_grid_index']})
    return {'schema': 'counterform.study-summary.v1', 'name': plan['name'], 'purpose': plan['purpose'],
            'protocol': plan['protocol'], 'plan_sha256': plan_sha, 'source_sha256': code_sha,
            'planned_cases': plan['case_count'], 'completed_cases': len(records), 'failed_cases': len(failures),
            'complete': len(records) == plan['case_count'] and not failures,
            'comparisons': comparisons, 'paired': paired, 'failures': failures,
            'notes': ['Descriptive bounded study; no statistical efficacy or novelty claim.',
                      'Candidate-design reductions are separate from the abstention recommendation.',
                      'Equal acquisition counts and common physical grid within v0.2 do not imply equal CPU or forcing-energy costs.',
                      'Every case, including failures and negative outcomes, is accounted for.']}


def _html(summary):
    esc = lambda v: html.escape(str(v))
    rows = ''.join('<tr>'+''.join(f'<td>{esc(c[k] if c[k] is not None else "unavailable")}</td>'
                                 for k in ('world', 'strategy', 'n', 'mean_reduction_pct', 'mean_worst_reduction_pct',
                                           'adequacy_passes', 'abstentions', 'negative_challenges', 'constraint_violations'))+'</tr>'
                   for c in summary['comparisons'])
    pairs = ''.join('<tr>'+''.join(f'<td>{esc(p[k])}</td>' for k in ('world', 'seed', 'comparison', 'reduction_delta_pp',
                                                                 'worst_delta_pp', 'acquisitions_equal'))+'</tr>' for p in summary['paired'])
    failures = ('<ul>' + ''.join(f'<li><code>{esc(f["case"])}</code>: {esc(f["error"])}</li>'
                                for f in summary['failures']) + '</ul>'
                if summary['failures'] else '<p>No failed cases.</p>')
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>COUNTERFORM study report</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 22px;background:#171d18;color:#e7e8df}}p{{line-height:1.5}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:9px;border:1px solid #465146}}a{{color:#e1b26b}}code{{overflow-wrap:anywhere}}.scroll{{overflow-x:auto}}</style>
<h1>COUNTERFORM {esc(summary['name'])}</h1><p>Protocol {esc(summary['protocol'])} · {esc(summary['purpose'])} study · {summary['completed_cases']}/{summary['planned_cases']} completed · {summary['failed_cases']} failed.</p>
<p>Candidate design results, not operational guarantees. Means are arithmetic means of each run's pooled RMS reduction. Every negative outcome and abstention is retained. No confidence interval or significance claim is made.</p>
<h2>All strategy cells</h2><div class="scroll"><table><tr><th>World</th><th>Strategy</th><th>n</th><th>Mean pooled reduction %</th><th>Mean worst reduction %</th><th>Audit passes</th><th>Abstentions</th><th>Negative conditions</th><th>Constraint violations</th></tr>{rows}</table></div>
<h2>Failed cases</h2>{failures}
<h2>Paired descriptive differences</h2><p>Difference direction is COUNTERFORM minus control, in percentage points. A single pair does not establish an acquisition benefit.</p><div class="scroll"><table><tr><th>World</th><th>Seed</th><th>Comparison</th><th>Pooled delta pp</th><th>Worst delta pp</th><th>Same acquisitions</th></tr>{pairs}</table></div>
<h2>Provenance</h2><p>Plan SHA-256 <code>{summary['plan_sha256']}</code></p><p>Source SHA-256 <code>{summary['source_sha256']}</code></p><p><a href="summary.json">Complete JSON</a> · <a href="results.csv">Per-run CSV</a> · <a href="protocol.json">Frozen plan</a></p></html>'''


def run_plan(plan: dict, output: Path | str, progress=None) -> dict:
    clean = validate_plan(plan)
    destination = Path(output).resolve()
    protected = [ROOT / 'runs/benchmark', ROOT / 'runs/example', ROOT / 'paper', ROOT / 'publications']
    if any(destination == p.resolve() or destination.is_relative_to(p.resolve()) for p in protected):
        raise ValueError('Refusing to write into protected historical evidence')
    if destination.exists():
        raise ValueError('Study output already exists; choose a new directory to preserve evidence')
    from .protocols import run_study
    code_sha = source_digest()
    frozen = {k: v for k, v in clean.items() if k != 'case_count'}
    plan_sha = hashlib.sha256(canonical(frozen)).hexdigest()
    destination.mkdir(parents=True)
    (destination / 'protocol.json').write_bytes(canonical(frozen))
    records, failures = [], []
    case_number = 0
    for world in clean['worlds']:
        for seed in clean['seeds']:
            for strategy in clean['strategies']:
                case_number += 1
                case_id = f'{world}/{seed}/{strategy}'
                if source_digest() != code_sha:
                    raise RuntimeError('Scientific source changed during the study; preserve this partial run and start a new one')
                if progress: progress(case_number, clean['case_count'], case_id)
                try:
                    config = dict(protocol=clean['protocol'], seed=seed, world=world, strategy=strategy,
                                  budget=clean['budget'], noise=clean['noise'])
                    result = run_study(config)
                    if source_digest() != code_sha:
                        raise RuntimeError('Scientific source changed while computing a study case')
                    metrics = _metrics(result)
                    receipt = make_receipt(result)
                    verify_receipt(receipt)
                    case_dir = destination / case_id
                    case_dir.mkdir(parents=True)
                    (case_dir / 'receipt.json').write_bytes(canonical(receipt))
                    (case_dir / 'evidence.zip').write_bytes(build_bundle(receipt))
                    (case_dir / 'report.html').write_bytes(report_html(receipt).encode('utf-8'))
                    records.append({'world': world, 'seed': seed, 'strategy': strategy, 'protocol': clean['protocol'],
                                    **metrics, 'selected_grid_index': result['validation'].get('selected_grid_index'),
                                    'acquisitions': [[e['frequency'], e['amplitude']] for e in result['experiments']]})
                except Exception as exc:
                    failures.append({'case': case_id, 'error': f'{type(exc).__name__}: {exc}'})
                    if 'source changed' in str(exc).lower():
                        raise
                summary = _summarize(clean, records, failures, plan_sha, code_sha)
                (destination / 'summary.json').write_bytes(canonical(summary))
                _write_csv(destination / 'results.csv', records)
                _write_csv(destination / 'paired.csv', summary['paired'])
                (destination / 'report.html').write_text(_html(summary), encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.plan.stat().st_size > 100_000:
            raise ValueError('Study plan exceeds 100 kB')
        plan = json.loads(args.plan.read_text(encoding='utf-8'))
        summary = run_plan(plan, args.output, progress=lambda n, total, case: print(f'{n}/{total}: {case}', file=sys.stderr, flush=True))
        print(json.dumps(summary, indent=2))
        return 0 if summary['complete'] else 1
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        print(f'COUNTERFORM study: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
