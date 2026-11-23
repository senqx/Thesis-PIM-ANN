#!/usr/bin/env python3
"""Preserve, audit and replay the bounded access-plan study without relinking."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
from types import SimpleNamespace
import zipfile

from access_plan import run_one
from wram_platform import ROOT, invoke

OUT = ROOT / 'experiments/access-plan'
IMAGES = ('addresses.txt', 'values.txt', 'atomic.bin', 'iram.bin', 'wram.bin', 'mram.bin')
STAGES = {'screen': 18, 'footprints': 63, 'batch-screen': 3, 'validation': 48,
          'value-check': 2, 'memory-probe': 3}
SMOKE = ('validation/community-s23-stream16-t12-f8',
         'validation/community-s23-batch-t12-f8',
         'validation/grqc-s61-plan_nextuse-t12-f8', 'memory-probe/probe_1024')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def csv_rows(stage):
    with (OUT / f'{stage}.csv').open() as f:
        return list(csv.DictReader(f))


def name(row):
    if 'policy' not in row:
        return f'probe_{row["transfer_bytes"]}'
    return (f'{row["case"]}-s{row["seed"]}-{row["policy"]}'
            f'-t{row["tasklets"]}-f{row["feature_bytes"]}')


def stats(directory):
    return dict(line.split(': ') for line in (directory / 'log.txt').read_text().splitlines())


def options(text):
    return dict(line.split('  -->  ') for line in text.splitlines() if '  -->  ' in line)


def value_check():
    """Use the held-out linked images with unchanged plans and changed values."""
    rows = []
    for policy in ('plan_nextuse', 'batch'):
        original = ROOT / f'runs/access-plan-validation/community-s23-{policy}-t12-f8'
        template = ROOT / f'build/access-plan-values/{policy}'
        template.mkdir(parents=True, exist_ok=False)
        for file in IMAGES:
            (template / file).write_bytes((original / file).read_bytes())
        args = SimpleNamespace(run_directory=ROOT/'runs/access-plan-value-check', value_epoch=1)
        row = run_one(('community', 23, policy, 12, 8, template, args))
        new = args.run_directory / name(row)
        def bytes_at(d, file):
            return bytes(map(int, (d/file).read_text().split()))
        file = 'input_dpu_mram_heap_pointer_name_0_0_0.bin'
        old_data, new_data = bytes_at(original, file), bytes_at(new, file)
        boundary = row['index_or_plan_bytes']
        assert old_data[:boundary] == new_data[:boundary]
        assert old_data[boundary:] != new_data[boundary:]
        rows.append(row)
    with (OUT/'value-check.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def record():
    records, blobs = {}, {}
    for stage, count in STAGES.items():
        rows = csv_rows(stage)
        assert len(rows) == count and len({name(r) for r in rows}) == count
        for row in rows:
            directory = ROOT / f'runs/access-plan-{stage}' / name(row)
            files = list(IMAGES) + ['num_executions.txt']
            files += [p.name for p in sorted(directory.glob('input_*.bin'))]
            files += [p.name for p in sorted(directory.glob('output_*.bin'))]
            mappings = {}
            for file in files:
                data = (directory / file).read_bytes()
                digest = sha(data)
                blobs[digest] = data
                mappings[file] = digest
            records[f'{stage}/{name(row)}'] = dict(
                row=row, files=mappings, statistics=stats(directory),
                options=(directory/'options.txt').read_text(),
                completion=(directory/'simulate.stdout.txt').read_text())
    with zipfile.ZipFile(OUT/'replay.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        members = {f'blobs/{k}': v for k,v in blobs.items()}
        members['records.json'] = (json.dumps(records, indent=2, sort_keys=True)+'\n').encode()
        for file, data in sorted(members.items()):
            info = zipfile.ZipInfo(file, date_time=(2026,11,23,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    paths = [p for p in OUT.iterdir() if p.is_file() and p.name != 'manifest.json']
    paths += [ROOT/'scripts'/p for p in ('access_plan.py', 'access_plan_artifact.py',
                                      'dpu_memory_probe.py', 'wram_platform.py')]
    paths += [ROOT/'experiments/wram/THIRD_PARTY_NOTICES.txt']
    manifest = dict(date='2026-11-23', stage_records=STAGES,
                    simulator_commit='870d916334e9ff0b190f555f951a9ec3c4257781',
                    hardware_validation=False,
                    sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(paths)})
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(f'Retained {len(records)} records and {len(blobs)} distinct file contents.')


def verify():
    manifest = json.loads((OUT/'manifest.json').read_text())
    assert manifest['stage_records'] == STAGES
    for file, digest in manifest['sha256'].items():
        assert sha((ROOT/file).read_bytes()) == digest, file
    with zipfile.ZipFile(OUT/'replay.zip') as archive:
        records = json.loads(archive.read('records.json'))
        blobs = {file.removeprefix('blobs/'): archive.read(file)
                 for file in archive.namelist() if file.startswith('blobs/')}
    for digest, data in blobs.items():
        assert sha(data) == digest
    assert len(records) == sum(STAGES.values())
    paired = {}
    for stage in STAGES:
        rows = csv_rows(stage)
        assert len(rows) == STAGES[stage]
        for row in rows:
            record = records[f'{stage}/{name(row)}']
            assert record['row'] == row
            assert row['output_check'] == row['traffic_check'] == 'passed'
            assert record['completion'].strip() == 'execution (0) is finished...'
            for digest in record['files'].values():
                assert digest in blobs
            for column, counter in (('cycles','Logic[0_0_0]_logic_cycle'),
                                    ('instructions','Logic[0_0_0]_num_instructions'),
                                    ('read_bytes','RowBuffer[0_0_0]_read_bytes'),
                                    ('write_bytes','RowBuffer[0_0_0]_write_bytes')):
                assert row[column] == record['statistics'][counter]
            if 'policy' not in row:
                continue
            assert int(row['wram_reserved_bytes']) <= 65536
            assert sha(blobs[record['files']['iram.bin']]) == row['iram_sha256']
            decode = lambda file: bytes(map(int, blobs[record['files'][file]].split()))
            data = decode('input_dpu_mram_heap_pointer_name_0_0_0.bin')
            assert sha(data) == row['input_sha256']
            output = next(f for f in record['files'] if f.startswith('output_'))
            assert sha(decode(output)) == row['expected_sha256']
            key = (stage, row['case'], row['seed'], row['tasklets'], row['feature_bytes'])
            paired.setdefault(key, {})[row['policy']] = row
    for group in paired.values():
        assert len({r['logical_input_sha256'] for r in group.values()}) == 1
        assert len({r['expected_sha256'] for r in group.values()}) == 1
        if 'plan_direct' in group:
            for field in ('feature_loads', 'read_bytes', 'write_bytes'):
                assert group['plan_direct'][field] == group['history'][field]
    print(f'Verified {len(records)} records, {len(blobs)} blobs, hashes, counters, outputs and paired controls.')
    return records, blobs


def replay(args):
    records, blobs = verify()
    keys = sorted(records) if args.all else (args.records or SMOKE)
    results = []
    for key in keys:
        record = records[key]
        directory = args.destination/key
        directory.mkdir(parents=True, exist_ok=False)
        for file, digest in record['files'].items():
            assert Path(file).name == file
            (directory/file).write_bytes(blobs[digest])
        opts = options(record['options'])
        invoke('simulate', directory, opts['benchmark'], int(opts['num_tasklets']))
        assert stats(directory) == record['statistics'], key
        actual = options((directory/'options.txt').read_text())
        for field in opts:
            if field not in ('bin_dirpath','log_dirpath','root_dirpath'):
                assert actual[field] == opts[field], (key,field)
        results.append(dict(record=key, output_check='passed', all_counters='exact'))
        print(f'Exact fresh replay: {key}', flush=True)
    (args.destination/'reproduction.json').write_text(json.dumps(results, indent=2)+'\n')


def summarize():
    rows = csv_rows('validation')
    lookup = {(r['case'],r['seed'],r['policy']):r for r in rows}
    lines = ['# Held-out descriptive comparisons', '',
             'Twelve tasklets, 8-byte feature rows, seeds 23 and 61. Percentage',
             'changes are arithmetic means of paired changes. Negative means fewer',
             'cycles or bytes. These are two-input summaries, not confidence intervals.', '',
             '| Workload | Policy | Comparator | Mean cycles | Cycle difference | Cycle change | Read-byte change |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for case in ('community','uniform','hubs','grqc'):
        for policy in ('stream16','batch','history','plan_nextuse'):
            a = [lookup[case,s,policy] for s in ('23','61')]
            b = [min((lookup[case,s,k] for k in ('stream128','stream256')),
                     key=lambda r:int(r['cycles'])) if policy=='stream16' else
                 lookup[case,s,'stream16'] for s in ('23','61')]
            mean = statistics.mean(int(x['cycles']) for x in a)
            delta = statistics.mean(int(x['cycles'])-int(y['cycles']) for x,y in zip(a,b))
            percent = [statistics.mean(100*(int(x[k])/int(y[k])-1) for x,y in zip(a,b))
                       for k in ('cycles','read_bytes')]
            baseline = 'best 32-bit stream' if policy=='stream16' else 'stream16'
            lines.append(f'| {case} | {policy} | {baseline} | {mean:,.1f} | {delta:+,.1f} | {percent[0]:+.2f}% | {percent[1]:+.2f}% |')
    (OUT/'comparisons.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['value-check','record','verify','replay','summarize'])
    p.add_argument('--records', nargs='+')
    p.add_argument('--all', action='store_true')
    p.add_argument('--destination', type=Path, default=ROOT/'build/access-plan-replay')
    args = p.parse_args()
    if args.action == 'replay': replay(args)
    elif args.action == 'value-check': value_check()
    else: {'record':record, 'verify':verify, 'summarize':summarize}[args.action]()
