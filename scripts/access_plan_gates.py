#!/usr/bin/env python3
"""Run, archive and replay two bounded controls; never modify prior evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import statistics
import struct
from types import SimpleNamespace
import zipfile

from access_plan import graph, pack
from access_plan_artifact import IMAGES, options, sha
from wram_platform import ROOT, bytefile, compile_sources, invoke

OUT = ROOT / 'experiments/baseline-gates'
PRIOR = ROOT / 'experiments/access-plan-fivepoint'
RUNS = ROOT / 'runs/baseline-gates'
T, N = 12, 3072
SPECS = {'compact64': (3, 256), 'preload128': (4, 128), 'preload512': (4, 512)}
OLD = ('stream16', 'stream16_256', 'stream16_1024', 'batch64')


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def compile_all():
    for policy, (mode, size) in SPECS.items():
        compile_sources(SimpleNamespace(tasklets=T, sdk=False,
            benchmark='gate_' + policy, source=OUT/'task.c',
            define=[f'-DMODE={mode}', '-DINDEX_BITS=16', '-DFEATURE_BYTES=8',
                    f'-DINDEX_BYTES={size}']))


def encode(refs):
    per = len(refs)//T
    segments = []
    for first in range(0, len(refs), per):
        segment = bytearray()
        for pos in range(first, first+per, 64):
            part = refs[pos:pos+64]
            ids = list(dict.fromkeys(part))
            assert max(ids) < 65536
            locations = {v:i for i,v in enumerate(ids)}
            raw = struct.pack(f'<{len(ids)}H', *ids)
            segment += pack([len(ids), 64]) + raw + bytes((-len(raw)) % 8)
            segment += bytes(locations[v] for v in part)
        segments.append(segment)
    stride = max(map(len, segments))
    assert stride % 8 == 0
    return b''.join(s+bytes(stride-len(s)) for s in segments), stride


def check_encoding(refs, data, stride):
    """Decode independently; count bytes actually fetched, excluding padding."""
    per, loads, metadata = len(refs)//T, 0, 0
    for tid in range(T):
        start = cursor = tid*stride
        for pos in range(tid*per, (tid+1)*per, 64):
            unique, count = struct.unpack_from('<II', data, cursor)
            assert 0 < unique <= count == 64
            cursor += 8
            ids = struct.unpack_from(f'<{unique}H', data, cursor)
            cursor += (2*unique+7)//8*8
            slots = data[cursor:cursor+count]
            cursor += count
            assert [ids[s] for s in slots] == refs[pos:pos+count]
            loads += unique
        metadata += cursor-start
        assert cursor <= start+stride and not any(data[cursor:start+stride])
    return loads, metadata


def run_one(job):
    case, seed, policy, template, baseline = job
    key = f'{case}-s{seed}-n{N}-{policy}'
    directory = RUNS/key
    directory.mkdir(exist_ok=False)
    for name in IMAGES:
        (directory/name).write_bytes((template/name).read_bytes())
    refs, vertices = graph(case, seed, destinations=N)
    features = [(v*17+i*13+3)%251 for v in range(vertices) for i in range(2)]
    expected = pack([sum(features[v*2+i] for v in refs[p:p+8])
                     for p in range(0, len(refs), 8) for i in range(2)])
    if policy == 'compact64':
        indices, stride = encode(refs)
        loads, metadata = check_encoding(refs, indices, stride)
    else:
        assert vertices == 512
        indices, stride = struct.pack(f'<{len(refs)}H', *refs), 0
        loads, metadata = vertices, len(indices)
    data = indices + pack(features)
    args = pack([len(refs), len(indices), len(data), stride])
    bytefile(directory/'input_DPU_INPUT_ARGUMENTS_0_0.bin', args)
    bytefile(directory/'input_dpu_mram_heap_pointer_name_0_0_0.bin', data)
    bytefile(directory/f'output_dpu_mram_heap_pointer_name_{len(data)}_0_0.bin', expected)
    (directory/'num_executions.txt').write_text('1\n')
    elapsed = invoke('simulate', directory, 'gate_'+policy, T)
    stats = dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines())
    assert int(stats['RowBuffer[0_0_0]_read_bytes']) == metadata+loads*8
    assert int(stats['RowBuffer[0_0_0]_write_bytes']) == len(expected)
    vals = dict(line.split(': ') for line in (directory/'values.txt').read_text().splitlines())
    wram = int(vals['__sys_heap_pointer_reset'])
    assert wram <= 65536
    logical = sha(pack(refs)+pack(features))
    assert logical == baseline['logical_sha256'] and sha(expected) == baseline['output_sha256']
    row = dict(key=key, case=case, seed=seed, destinations=N, policy=policy,
        provenance='new', references=len(refs), source_vertices=vertices,
        tasklets=T, feature_bytes=8, cycles=stats['Logic[0_0_0]_logic_cycle'],
        instructions=stats['Logic[0_0_0]_num_instructions'],
        read_bytes=metadata+loads*8, write_bytes=len(expected), feature_loads=loads,
        stored_metadata_bytes=len(indices), read_metadata_bytes=metadata,
        wram_reserved_bytes=wram, logical_sha256=logical, input_sha256=sha(data),
        output_sha256=sha(expected), iram_sha256=sha((directory/'iram.bin').read_bytes()),
        simulator_wall_seconds=round(elapsed,3), output_check='passed', traffic_check='passed')
    (directory/'result.json').write_text(json.dumps(row, indent=2)+'\n')
    print(key, row['cycles'], 'cycles', flush=True)
    return row


def run_all():
    assert not (OUT/'results.csv').exists(), 'Preserve the retained screen; use a fresh copy.'
    RUNS.mkdir(exist_ok=False)
    retained = {}
    with zipfile.ZipFile(PRIOR/'replay.zip') as z:
        records = json.loads(z.read('records.json'))
        for key, r in records.items():
            row = r['row']
            if int(row['destinations']) != N or row['policy'] not in OLD:
                continue
            directory = RUNS/key
            directory.mkdir()
            for name, digest in r['files'].items():
                assert Path(name).name == name
                (directory/name).write_bytes(z.read('blobs/'+digest))
            (directory/'options.txt').write_text(r['options'])
            (directory/'simulate.stdout.txt').write_text(r['completion'])
            (directory/'log.txt').write_text(''.join(f'{k}: {v}\n' for k,v in r['statistics'].items()))
            retained[key] = row
    assert len(retained) == 24
    jobs = []
    for policy in SPECS:
        template = RUNS/('linked-'+policy)
        invoke('link', template, 'gate_'+policy, T)
        for case in ('community','uniform','grqc'):
            if case == 'grqc' and policy.startswith('preload'):
                continue
            for seed in (23,61):
                baseline = retained[f'{case}-s{seed}-n{N}-stream16']
                jobs.append((case, seed, policy, template, baseline))
    assert len(jobs) == 14
    with ThreadPoolExecutor(max_workers=2) as pool:
        new = list(pool.map(run_one, jobs))
    fields = list(new[0])
    old = [{k: ('retained-fivepoint' if k == 'provenance' else r[k]) for k in fields}
           for r in retained.values()]
    with (OUT/'results.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(new+old, key=lambda r:r['key']))


def record():
    records, blobs = {}, {}
    for row in rows(OUT/'results.csv'):
        directory = RUNS/row['key']
        names = list(IMAGES)+['num_executions.txt']
        names += [p.name for p in sorted(directory.glob('input_*.bin'))]
        names += [p.name for p in sorted(directory.glob('output_*.bin'))]
        files = {}
        for name in names:
            data = (directory/name).read_bytes()
            digest = sha(data)
            files[name] = digest
            blobs[digest] = data
        records[row['key']] = dict(row=row, files=files,
            options=(directory/'options.txt').read_text(),
            statistics=dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines()),
            completion=(directory/'simulate.stdout.txt').read_text())
    with zipfile.ZipFile(OUT/'replay.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        members = {f'blobs/{k}':v for k,v in blobs.items()}
        members['records.json'] = json.dumps(records, indent=2, sort_keys=True).encode()
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026,11,23,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    paths = [p for p in OUT.iterdir() if p.is_file() and p.name != 'manifest.json']
    paths += [Path(__file__), ROOT/'scripts/access_plan.py', ROOT/'scripts/access_plan_artifact.py',
              ROOT/'scripts/wram_platform.py', PRIOR/'manifest.json']
    manifest = dict(new_records=14, retained_records=24, hardware_validation=False,
        sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)})
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')


def summarize():
    tab = rows(OUT/'results.csv')
    comparisons = []
    for row in tab:
        if row['provenance'] != 'new':
            continue
        paired = [r for r in tab if (r['case'],r['seed']) == (row['case'],row['seed'])]
        stream = min((r for r in paired if r['policy'].startswith('stream')),
                     key=lambda r:int(r['cycles']))
        batch = next(r for r in paired if r['policy'] == 'batch64')
        pct = lambda value, base: 100*(int(value)/int(base)-1)
        comparisons.append(dict(key=row['key'], case=row['case'], seed=row['seed'],
            policy=row['policy'], stream_comparator=stream['key'],
            cycle_change_vs_stream_pct=pct(row['cycles'],stream['cycles']),
            saved_cycles_vs_stream=int(stream['cycles'])-int(row['cycles']),
            cycle_change_vs_batch32dict_pct=pct(row['cycles'],batch['cycles']),
            read_change_vs_stream_pct=pct(row['read_bytes'],stream['read_bytes']),
            installed_metadata_change_vs_stream_pct=pct(row['stored_metadata_bytes'],stream['stored_metadata_bytes']),
            wram_reserved_bytes=row['wram_reserved_bytes']))
    with (OUT/'comparisons.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    text = ['# Baseline-gate results', '',
        'Two-seed arithmetic means of paired percentage changes at 3,072 destinations.',
        'Negative changes mean less time or fewer bytes. The comparator is the fastest',
        'retained streaming buffer for each input; this is a hindsight comparator.',
        'These are descriptive results from the Go simulator, not hardware measurements.', '',
        '| Input | New control | Cycles vs streaming | Reads vs streaming | Installed metadata vs streaming |',
        '| --- | --- | ---: | ---: | ---: |']
    for case in ('community','grqc','uniform'):
        for policy in SPECS:
            group = [r for r in comparisons if r['case']==case and r['policy']==policy]
            if not group:
                continue
            assert len(group) == 2
            fields = ('cycle_change_vs_stream_pct','read_change_vs_stream_pct',
                      'installed_metadata_change_vs_stream_pct')
            values = [statistics.mean(r[f] for r in group) for f in fields]
            text.append(f'| {case} | {policy} | '+ ' | '.join(f'{v:+.2f}%' for v in values)+' |')
    text += ['', 'The [CSV](comparisons.csv) includes both seeds, absolute cycle differences,',
             'original-batch comparisons and complete WRAM reservations. No size trend',
             'or preparation payback is inferred from this single-size screen.', '']
    (OUT/'comparisons.md').write_text('\n'.join(text))


def verify():
    manifest = json.loads((OUT/'manifest.json').read_text())
    for name, digest in manifest['sha256'].items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    with zipfile.ZipFile(OUT/'replay.zip') as z:
        records = json.loads(z.read('records.json'))
        blobs = {n[6:]:z.read(n) for n in z.namelist() if n.startswith('blobs/')}
    assert len(records) == 38
    for digest, data in blobs.items():
        assert sha(data) == digest
    with zipfile.ZipFile(PRIOR/'replay.zip') as z:
        prior = json.loads(z.read('records.json'))
    tab = rows(OUT/'results.csv')
    assert len(tab) == 38 and len({r['key'] for r in tab}) == 38
    assert sum(r['provenance']=='new' for r in tab) == 14
    for row in tab:
        saved = records[row['key']]
        assert saved['row'] == row
        assert saved['completion'].strip() == 'execution (0) is finished...'
        for digest in saved['files'].values():
            assert digest in blobs
        decode = lambda r, f: bytes(map(int, blobs[r['files'][f]].split()))
        args = struct.unpack('<IIII', decode(saved, 'input_DPU_INPUT_ARGUMENTS_0_0.bin'))
        data = decode(saved, 'input_dpu_mram_heap_pointer_name_0_0_0.bin')
        output_name = f'output_dpu_mram_heap_pointer_name_{args[2]}_0_0.bin'
        output = decode(saved, output_name)
        assert sha(data) == row['input_sha256'] and sha(output) == row['output_sha256']
        assert saved['files']['iram.bin'] == row['iram_sha256']
        values_text = blobs[saved['files']['values.txt']].decode()
        symbols = dict(line.split(': ') for line in values_text.splitlines())
        assert int(row['wram_reserved_bytes']) == int(symbols['__sys_heap_pointer_reset'])
        assert int(row['wram_reserved_bytes']) <= 65536
        assert row['output_check'] == row['traffic_check'] == 'passed'
        for field, counter in (('cycles','Logic[0_0_0]_logic_cycle'),
                ('instructions','Logic[0_0_0]_num_instructions'),
                ('read_bytes','RowBuffer[0_0_0]_read_bytes'),
                ('write_bytes','RowBuffer[0_0_0]_write_bytes')):
            assert row[field] == saved['statistics'][counter]
        if row['provenance'] == 'retained-fivepoint':
            original = prior[row['key']]
            assert saved['files'] == original['files']
            assert saved['statistics'] == original['statistics']
            continue
        baseline = records[f'{row["case"]}-s{row["seed"]}-n{N}-stream16']
        raw = decode(baseline, 'input_dpu_mram_heap_pointer_name_0_0_0.bin')
        refs = list(struct.unpack(f'<{N*8}H', raw[:N*16]))
        features = raw[N*16:]
        assert data[args[1]:] == features
        assert sha(pack(refs)+features) == row['logical_sha256'] == baseline['row']['logical_sha256']
        values = struct.unpack(f'<{len(features)//4}I', features)
        reference = pack([sum(values[v*2+i] for v in refs[p:p+8])
                          for p in range(0,len(refs),8) for i in range(2)])
        assert output == reference
        if row['policy'] == 'compact64':
            loads, metadata = check_encoding(refs, data[:args[1]], args[3])
        else:
            assert row['case'] != 'grqc' and data[:args[1]] == raw[:N*16]
            loads, metadata = 512, N*16
        assert int(row['read_bytes']) == metadata+loads*8
        assert int(row['write_bytes']) == len(reference)
        assert int(row['stored_metadata_bytes']) == args[1]
        assert int(row['read_metadata_bytes']) == metadata
        assert int(row['feature_loads']) == loads
    print('Verified 14 new and 24 retained records, reference outputs, exact traffic and WRAM limits.')
    return records, blobs


def replay(destination):
    records, blobs = verify()
    for key in ('community-s23-n3072-preload128', 'grqc-s61-n3072-compact64'):
        saved = records[key]
        directory = destination/key
        directory.mkdir(parents=True, exist_ok=False)
        for name, digest in saved['files'].items():
            assert Path(name).name == name
            (directory/name).write_bytes(blobs[digest])
        old = options(saved['options'])
        invoke('simulate', directory, old['benchmark'], T)
        stats = dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines())
        assert stats == saved['statistics']
        new = options((directory/'options.txt').read_text())
        assert all(new[k] == v for k,v in old.items()
                   if k not in ('bin_dirpath','log_dirpath','root_dirpath'))
        print('Exact replay:', key, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['compile','run','summarize','record','verify','replay'])
    p.add_argument('--destination', type=Path, default=ROOT/'build/baseline-gates-replay')
    a = p.parse_args()
    if a.action == 'replay':
        replay(a.destination)
    else:
        {'compile':compile_all, 'run':run_all, 'summarize':summarize,
         'record':record, 'verify':verify}[a.action]()
