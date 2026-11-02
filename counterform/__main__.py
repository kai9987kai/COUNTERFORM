"""Command-line entrypoints for studies, evidence replay and the local app."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys
import zipfile

from . import __version__
from .evidence import canonical, digest, make_receipt, verify_receipt, verify_bundle, build_bundle, report_html, source_digest


def load_receipt(path: Path) -> dict:
    if path.suffix.lower() == '.zip':
        data = path.read_bytes()
        verify_bundle(data)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return json.loads(z.read('receipt.json'))
    receipt = json.loads(path.read_text(encoding='utf-8'))
    verify_receipt(receipt)
    return receipt


def save_study(result: dict, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    receipt = make_receipt(result)
    (output / 'receipt.json').write_bytes(canonical(receipt))
    (output / 'evidence.zip').write_bytes(build_bundle(receipt))
    (output / 'report.html').write_text(report_html(receipt), encoding='utf-8')
    return receipt


def study_args(parser):
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--world', choices=['linear', 'cubic', 'friction', 'unmodelled'], default='cubic')
    parser.add_argument('--strategy', choices=['passive', 'random', 'active', 'counterform'], default='counterform')
    parser.add_argument('--budget', type=int, default=5)
    parser.add_argument('--noise', type=float, default=.01)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='counterform', description='CPU-local synthetic mechanical research laboratory')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve', help='Open the local workbench server')
    serve.add_argument('--port', type=int, default=8768)
    serve.add_argument('--runs', type=Path, default=Path('runs/history'))
    run = commands.add_parser('run', help='Compute one study and export evidence')
    study_args(run)
    run.add_argument('--output', type=Path, default=Path('runs/manual'))
    for name in ('verify', 'replay'):
        cmd = commands.add_parser(name, help='Check evidence integrity' if name == 'verify' else 'Recompute deterministic numerical evidence')
        cmd.add_argument('path', type=Path)
    benchmark = commands.add_parser('benchmark', help='Paired descriptive comparison; no statistical efficacy claim')
    benchmark.add_argument('--seeds', type=int, nargs='+', default=[11, 23])
    benchmark.add_argument('--worlds', nargs='+', choices=['linear', 'cubic', 'friction', 'unmodelled'], default=['cubic', 'unmodelled'])
    benchmark.add_argument('--budget', type=int, default=3)
    benchmark.add_argument('--noise', type=float, default=.01)
    benchmark.add_argument('--output', type=Path, default=Path('runs/benchmark'))
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            import uvicorn
            from .server import create_app
            uvicorn.run(create_app(args.runs), host='127.0.0.1', port=args.port, log_level='info')
        elif args.command == 'verify':
            if args.path.suffix.lower() == '.zip':
                result = verify_bundle(args.path.read_bytes())
            else:
                result = verify_receipt(load_receipt(args.path))
            print(json.dumps(result))
        elif args.command == 'replay':
            from .engine import run_study
            receipt = load_receipt(args.path)
            actual = run_study(receipt['config'])
            same = digest(canonical(actual)) == receipt['result_sha256']
            print(json.dumps({'reproduced': same, 'source_matches': source_digest() == receipt['software'].get('source_sha256'), 'expected_sha256': receipt['result_sha256'], 'actual_sha256': digest(canonical(actual)), 'note': 'Exact numerical replay depends on the recorded numerical dependency versions.'}))
            return 0 if same else 1
        elif args.command == 'run':
            from .engine import run_study
            config = {k: getattr(args, k) for k in ('seed', 'world', 'strategy', 'budget', 'noise')}
            result = run_study(config, progress=lambda f, m: print(f'{f:3.0%} {m}', file=sys.stderr))
            save_study(result, args.output)
            print(json.dumps({'output': str(args.output.resolve()), 'summary': result['summary']}, indent=2))
        elif args.command == 'benchmark':
            from .engine import run_study
            import numpy as np
            rows = []
            for world in args.worlds:
                for seed in args.seeds:
                    for strategy in ('passive', 'random', 'active', 'counterform'):
                        config = dict(seed=seed, world=world, strategy=strategy, budget=args.budget, noise=args.noise)
                        print(f'{world} / seed {seed} / {strategy}', file=sys.stderr)
                        result = run_study(config)
                        save_study(result, args.output / world / str(seed) / strategy)
                        summary = result['summary']
                        rows.append({'world': world, 'seed': seed, 'strategy': strategy, 'budget': args.budget, 'noise': args.noise, **{key: summary[key] for key in ('reduction_pct', 'worst_reduction_pct', 'adequate', 'constraint_violations', 'design_rms')}})
            args.output.mkdir(parents=True, exist_ok=True)
            with (args.output / 'results.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            comparison = []
            for world in args.worlds:
                for strategy in ('passive', 'random', 'active', 'counterform'):
                    subset = [r for r in rows if r['world'] == world and r['strategy'] == strategy]
                    comparison.append({'world': world, 'strategy': strategy, 'n': len(subset), 'mean_reduction_pct': float(np.mean([r['reduction_pct'] for r in subset])), 'adequacy_passes': sum(r['adequate'] for r in subset), 'constraint_violations': sum(r['constraint_violations'] for r in subset)})
            report = {'schema': 'counterform.benchmark.v1', 'protocol': {'seeds': args.seeds, 'worlds': args.worlds, 'budget': args.budget, 'noise': args.noise, 'strategies': ['passive', 'random', 'active', 'counterform']}, 'comparisons': comparison, 'notes': ['Descriptive pilot only; no statistical efficacy or novelty claim.', 'Equal acquisition counts and finite design grid, not equal wall-clock computation.', 'Audit/challenge simulations are outside acquisition budget and never used to refit the selected design.']}
            (args.output / 'summary.json').write_bytes(canonical(report))
            print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'COUNTERFORM: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
