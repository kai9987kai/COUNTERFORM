"""Create publication figures from saved evidence without generating new trials."""
from pathlib import Path
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
EXTRA = ROOT / 'output' / 'paper-deps'
if EXTRA.exists():
    sys.path.insert(0, str(EXTRA))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = ROOT / 'paper' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.labelsize': 9,
                     'axes.titlesize': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'pdf.fonttype': 42, 'savefig.facecolor': 'white'})


def read_csv(name):
    with (ROOT / 'paper' / 'data' / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def save(fig, name):
    for suffix in ('png', 'pdf', 'svg'):
        fig.savefig(OUT / f'{name}.{suffix}', dpi=320, bbox_inches='tight', pad_inches=.07)
    plt.close(fig)


def main():
    runs = read_csv('runs.csv')
    # Receipts supply named fields directly, keeping plotting independent of CSV schema aliases.
    receipts = {}
    for p in sorted((ROOT / 'runs' / 'benchmark').rglob('receipt.json')):
        r = json.loads(p.read_text(encoding='utf-8'))['result']
        c = r['config']
        receipts[(c['world'], c['seed'], c['strategy'])] = r
    worlds = [('cubic', 'Cubic world'), ('unmodelled', 'Omitted-law world')]
    strategies = ['passive', 'random', 'active', 'counterform']
    labels = ['Passive', 'Random', 'Disagreement', 'COUNTERFORM']
    colors = ['#677280', '#677280', '#246b96', '#a15c20']
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.65), layout='constrained', sharey=True)
    for ax, (world, title) in zip(axes, worlds):
        for i, strategy in enumerate(strategies):
            ys = [receipts[(world, seed, strategy)]['summary']['reduction_pct'] for seed in [11, 23]]
            ax.plot([i, i], [min(ys), max(ys)], color=colors[i], lw=1.1, zorder=1)
            for seed, marker, y in zip([11, 23], ['o', '^'], ys):
                ax.scatter(i, y, marker=marker, color=colors[i], edgecolor='white', lw=.5, s=42, zorder=3,
                           label=f'Seed {seed}' if world == 'cubic' and i == 0 else None)
        ax.set_xticks(range(4), labels, rotation=27, ha='right')
        ax.set_title(title, loc='left', fontweight='bold')
        ax.grid(axis='y', color='#e6e6e6', lw=.6)
        ax.set_axisbelow(True)
        ax.set_ylim(18, 41)
    axes[0].set_ylabel('Pooled RMS reduction (%)')
    axes[0].legend(frameon=False, loc='lower left', fontsize=8)
    save(fig, 'performance')

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.65), layout='constrained', sharey=True)
    for ax, (world, title) in zip(axes, worlds):
        ax.axhline(.1, color='#a15c20', linestyle='--', lw=1, label='Audit threshold')
        for i, strategy in enumerate(strategies):
            for offset, seed, marker in [(-.075, 11, 'o'), (.075, 23, '^')]:
                r = receipts[(world, seed, strategy)]
                best = max(r['models'], key=lambda m: m['weight'])
                passed = r['summary']['adequate']
                ax.scatter(i+offset, best['audit_nrmse'], marker=marker,
                           facecolors=colors[i] if passed else 'white', edgecolors=colors[i],
                           s=42, linewidth=1.1, zorder=3)
        ax.set_xticks(range(4), labels, rotation=27, ha='right')
        ax.set_title(title, loc='left', fontweight='bold')
        ax.set_ylim(0, .41)
        ax.grid(axis='y', color='#e6e6e6', lw=.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Top-weight candidate audit NRMSE')
    axes[0].legend(frameon=False, loc='upper right', fontsize=7.5)
    save(fig, 'audit')

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.65), layout='constrained', sharey=True)
    condition_labels = ['Frequency\nshift', 'High load\n+ 2nd tone', 'Component\ntolerance']
    for ax, (world, title) in zip(axes, worlds):
        ax.axhline(0, color='#444444', lw=.8)
        for offset, seed, color in [(-.17, 11, '#246b96'), (.17, 23, '#a15c20')]:
            values = [c['reduction_pct'] for c in receipts[(world, seed, 'counterform')]['challenges']]
            ax.bar(np.arange(3)+offset, values, width=.30, color=color, label=f'Seed {seed}')
        ax.set_xticks(range(3), condition_labels)
        ax.set_title(title, loc='left', fontweight='bold')
        ax.set_ylim(-19, 65)
        ax.grid(axis='y', color='#e6e6e6', lw=.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Per-condition RMS reduction (%)')
    axes[0].legend(frameon=False, loc='upper left', fontsize=8)
    save(fig, 'challenges')
    print('Three figures exported in PNG, SVG and PDF')


if __name__ == '__main__':
    main()
