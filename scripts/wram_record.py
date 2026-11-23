#!/usr/bin/env python3
"""Retain compact evidence and summarize the completed local execution pilot."""
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import zipfile
from wram_platform import ROOT, BUILD
from wram_experiment import POLICIES, CASES

OUT = ROOT / "experiments/wram"
rows = list(csv.DictReader((OUT / "results.csv").open()))
assert len(rows) == 160
assert len({(r['case'], r['seed'], r['policy'], r['tasklets']) for r in rows}) == 160
assert all(r['output_check'] == r['traffic_check'] == 'passed' for r in rows)

with zipfile.ZipFile(OUT / "linked-images.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for t in (1, 4):
        for p in POLICIES:
            for name in ("addresses.txt", "values.txt", "atomic.bin", "iram.bin", "wram.bin", "mram.bin"):
                info = zipfile.ZipInfo(f"{p}-t{t}/{name}", date_time=(2026, 11, 23, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (BUILD / f"linked-{p}-t{t}" / name).read_bytes())

records = {}
for r in rows:
    key = f"{r['case']}-s{r['seed']}-{r['policy']}-t{r['tasklets']}"
    d = ROOT / "runs/wram" / key
    log = d / "log.txt"
    records[key] = {"statistics": dict(line.split(": ") for line in log.read_text().splitlines()),
                    "options": (d / "options.txt").read_text(),
                    "completion": (d / "simulate.stdout.txt").read_text()}
(OUT / "simulator-records.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
smokes = {}
for t in (1, 4):
    d = ROOT / f"runs/wram/va-t{t}"
    smokes[str(t)] = {"result": json.loads((d / "result.json").read_text()),
                      "statistics": dict(line.split(": ") for line in (d / "log.txt").read_text().splitlines())}
(OUT / "smoke-checks.json").write_text(json.dumps(smokes, indent=2, sort_keys=True) + "\n")

lookup = {(r['case'], r['seed'], r['policy'], int(r['tasklets'])): r for r in rows}
table = ["| Tasklets | Workload | Policy | Mean cycles | Mean cycle difference | Cycle change vs stream2048 | Read-byte change |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
for t in (1, 4):
    for c in CASES:
        for p in POLICIES:
            deltas = {}
            for metric in ("cycles", "read_bytes"):
                deltas[metric] = statistics.mean(100 * (int(lookup[c, str(seed), p, t][metric]) /
                    int(lookup[c, str(seed), 'stream2048', t][metric]) - 1) for seed in (7, 23))
            mean_cycles = statistics.mean(int(lookup[c, str(s), p, t]['cycles']) for s in (7, 23))
            difference = statistics.mean(int(lookup[c, str(s), p, t]['cycles']) -
                int(lookup[c, str(s), 'stream2048', t]['cycles']) for s in (7, 23))
            table.append(f"| {t} | {c} | {p} | {mean_cycles:,.1f} | {difference:+,.1f} | {deltas['cycles']:+.2f}% | {deltas['read_bytes']:+.2f}% |")
(OUT / "comparisons.md").write_text("# Paired exploratory comparisons\n\n"
    "Arithmetic mean of two paired percentage changes (seeds 7 and 23). Negative\n"
    "means fewer cycles or bytes. These are descriptive results, not confidence\n"
    "intervals. Total local reads include indices, metadata and cache fills.\n\n" + "\n".join(table) + "\n")

os.environ.setdefault('MPLCONFIGDIR', str(BUILD / 'matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
colors = dict(zip(POLICIES, plt.get_cmap('tab10').colors))
for axis, t in zip(axes, (1, 4)):
    for p in POLICIES:
        if p == 'stream2048':
            continue
        xs, ys = [], []
        for c in CASES:
            xs.append(statistics.mean(int(lookup[c, str(s), p, t]['read_bytes']) /
                int(lookup[c, str(s), 'stream2048', t]['read_bytes']) for s in (7, 23)))
            ys.append(statistics.mean(int(lookup[c, str(s), p, t]['cycles']) /
                int(lookup[c, str(s), 'stream2048', t]['cycles']) for s in (7, 23)))
        axis.scatter(xs, ys, s=32, label=p, color=colors[p], alpha=.85)
    axis.axhline(1, color='black', linewidth=.8)
    axis.axvline(1, color='black', linewidth=.8)
    axis.set_xscale('log')
    axis.set_title(f'{t} tasklet' + ('s' if t != 1 else ''))
    axis.set_xlabel('MRAM read bytes / streaming baseline (log scale)')
    axis.grid(alpha=.15)
axes[0].set_ylabel('Complete simulated DPU cycles / streaming baseline')
axes[1].legend(fontsize=8, loc='upper left')
fig.suptitle('Fewer MRAM reads need not mean faster execution', fontsize=12)
fig.tight_layout()
fig.savefig(OUT / 'traffic-versus-cycles.png', dpi=160)
plt.close(fig)

paths = [p for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json']
paths += sorted((ROOT / 'scripts').glob('wram_*.py'))
manifest = {"date": "2026-11-23", "records": len(rows), "unique_graphs": 8,
            "workload_order_conditions": 10, "hardware_validation": False,
            "simulator_commit": "870d916334e9ff0b190f555f951a9ec3c4257781",
            "sdk_mirror_commit": "84a0dcd3f57ded98ea049f2be5d45c71eda96ace",
            "sdk_version": "2023.1.0", "sha256": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths if p.name != 'manifest.json'}}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(f"Retained {len(rows)} records, frozen images, smoke checks, paired comparisons and figure.")
