#!/usr/bin/env python3
"""Check retained hashes and optional fresh replay against deterministic fields."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'experiments/wram'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reproduction', type=Path)
args = parser.parse_args()
manifest = json.loads((OUT / 'manifest.json').read_text())
for name, expected in manifest['sha256'].items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Hash mismatch: {name}')
rows = list(csv.DictReader((OUT / 'results.csv').open()))
key = lambda r: tuple(r[k] for k in ('case', 'seed', 'policy', 'tasklets'))
baseline = {key(r): r for r in rows}
if len(rows) != manifest['records'] or len(rows) != len(baseline):
    raise SystemExit('Record count or uniqueness mismatch')
print(f"Verified {len(manifest['sha256'])} file hashes and {len(rows)} distinct records.")
if args.reproduction:
    reproduced = list(csv.DictReader(args.reproduction.open()))
    if not reproduced or len({key(r) for r in reproduced}) != len(reproduced):
        raise SystemExit('Empty or duplicate reproduction records')
    for row in reproduced:
        original = baseline[key(row)]
        for field in original:
            if field in ('simulator_wall_seconds', 'host_generation_seconds'):
                continue
            if row[field] != original[field]:
                raise SystemExit(f'Mismatch {key(row)} {field}: {row[field]} != {original[field]}')
    print(f'Fresh replay matches every deterministic field in {len(reproduced)} records.')
