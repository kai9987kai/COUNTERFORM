"""Derive publication tables and figures from the frozen 48-run evidence."""
from pathlib import Path
import csv
import json
import math
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
extra = ROOT / 'output/paper-deps'
if extra.exists():
    sys.path.insert(0, str(extra))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from counterform.evidence import verify_receipt, verify_bundle, source_digest

PAPER = Path(__file__).resolve().parent
STUDY = ROOT / 'runs/v02-development-20261103'
WORLDS = [('cubic', 'Cubic'), ('unmodelled', 'Combined'), ('memory', 'Memory')]
ARMS = [('passive', 'Passive'), ('random', 'Random'), ('active', 'Disagreement'), ('counterform', 'COUNTERFORM')]


def main():
    figures, data = PAPER / 'figures', PAPER / 'data'
    figures.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    summary = json.loads((STUDY / 'summary.json').read_bytes())
    receipts = []
    for path in sorted(STUDY.rglob('receipt.json')):
        receipt = json.loads(path.read_bytes())
        verify_receipt(receipt)
        verify_bundle(path.with_name('evidence.zip').read_bytes())
        receipts.append(receipt['result'])
    assert len(receipts) == 48 and summary['complete'] and not summary['failures']
    # The source match is informative, not an authorship or physical-validity claim.
    assert source_digest() == summary['source_sha256'], 'Use the frozen scientific source to rebuild these artifacts'
    for filename in ('results.csv', 'paired.csv', 'summary.json', 'protocol.json'):
        shutil.copyfile(STUDY / filename, data / filename)
    for cell in summary['comparisons']:
        runs = [r for r in receipts if r['config']['world'] == cell['world'] and r['config']['strategy'] == cell['strategy']]
        pooled = [100 * (1 - math.sqrt(sum(c['design_rms']**2 for c in r['challenges']) /
                                        sum(c['baseline_rms']**2 for c in r['challenges']))) for r in runs]
        assert len(runs) == cell['n'] == 4
        assert math.isclose(sum(pooled) / 4, cell['mean_reduction_pct'], abs_tol=1e-10)
        assert sum(r['summary']['adequate'] for r in runs) == cell['adequacy_passes']
    with (data / 'aggregates.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary['comparisons'][0]))
        writer.writeheader(); writer.writerows(summary['comparisons'])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.fonttype': 'none', 'savefig.facecolor': 'white'})
    palette = {'cubic': '#27648a', 'unmodelled': '#8a6b34', 'memory': '#774d79'}
    pairs = summary['paired']
    ordered = [(world, seed) for world, _ in WORLDS for seed in [101, 103, 107, 109]]
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 3.6), sharey=True, layout='constrained')
    for axis, (control, label) in zip(axes, [('active', 'Disagreement'), ('random', 'Random'), ('passive', 'Passive')]):
        for row, (world, seed) in enumerate(ordered):
            pair = next(p for p in pairs if p['world'] == world and p['seed'] == seed and p['comparison'] == 'counterform-minus-' + control)
            axis.plot(pair['reduction_delta_pp'], row, 'o', ms=4.8, color=palette[world])
        axis.axvline(0, color='#777777', lw=.7, ls='--')
        axis.set_xlim(-23, 18); axis.set_xticks([-20, 0, 15])
        axis.set_title('vs ' + label, loc='left', fontsize=9, fontweight='bold')
        axis.grid(axis='x', color='#e7e7e7', lw=.5); axis.set_axisbelow(True)
    axes[0].set_yticks(range(12), [f'{dict(WORLDS)[world]} {seed}' for world, seed in ordered])
    axes[0].invert_yaxis()
    fig.supxlabel('COUNTERFORM minus control: pooled reduction difference (percentage points)', fontsize=8.5)
    for ext in ('png', 'svg'):
        fig.savefig(figures / ('paired_deltas.' + ext), dpi=320, bbox_inches='tight', pad_inches=.06)
    plt.close(fig)
    matrix = np.array([[next(c['adequacy_passes'] for c in summary['comparisons'] if c['world'] == world and c['strategy'] == strategy)
                        for strategy, _ in ARMS] for world, _ in WORLDS])
    fig, axis = plt.subplots(figsize=(6.8, 2.5), layout='constrained')
    axis.imshow(matrix, vmin=0, vmax=4, cmap='Blues', aspect='auto')
    for row in range(3):
        for col in range(4):
            axis.text(col, row, f'{matrix[row,col]}/4', ha='center', va='center', fontsize=12,
                      color='white' if matrix[row,col] >= 3 else '#172430')
    axis.set_xticks(range(4), [label for _, label in ARMS])
    axis.set_yticks(range(3), ['Cubic (represented)', 'Combined (represented)', 'Memory (omitted)'])
    axis.tick_params(length=0)
    axis.set_title('Runs passing the finite joint audit; passing does not establish correct physics', loc='left', fontsize=9, pad=12)
    for spine in axis.spines.values(): spine.set_visible(False)
    for ext in ('png', 'svg'):
        fig.savefig(figures / ('audit_outcomes.' + ext), dpi=320, bbox_inches='tight', pad_inches=.06)
    plt.close(fig)
    appendix = ['## Appendix A. Complete run-level results', '',
                'All 48 exploratory absorber outcomes are included. A = joint audit pass; abstain means no absorber recommendation. Every run had zero violations at sampled output times within the 7-14 s evaluation window. Continuous peaks and the initial 0-7 s trajectory are not bounded by these checks.', '']
    for world, label in WORLDS:
        appendix += [f'### {label} world', '', '| Seed | Strategy | Pooled % | Worst % | A | Recommendation | Adverse / 3 |',
                     '|---|---|---:|---:|---|---|---:|']
        for seed in [101, 103, 107, 109]:
            for strategy, arm in ARMS:
                r = next(r for r in receipts if r['config']['world'] == world and r['config']['seed'] == seed and r['config']['strategy'] == strategy)
                negative = sum(c['reduction_pct'] < 0 for c in r['challenges'])
                appendix.append(f"| {seed} | {arm} | {r['summary']['reduction_pct']:.2f} | {r['summary']['worst_reduction_pct']:.2f} | {'yes' if r['summary']['adequate'] else 'no'} | {r['recommendation']['status']} | {negative} |")
        appendix.append('')
    (PAPER / 'appendix.md').write_text('\n'.join(appendix) + '\n', encoding='utf-8')
    print('Verified 48 receipts/bundles; generated two figures, source tables and complete appendix.')


if __name__ == '__main__':
    main()
