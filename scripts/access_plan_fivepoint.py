#!/usr/bin/env python3
"""Add two workload sizes using frozen programs; preserve the three-point study."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import zipfile

import access_plan_scaling as s

PRIOR = s.OUT
s.OUT = s.ROOT/'experiments/access-plan-fivepoint'
s.RUNS = s.ROOT/'runs/access-plan-fivepoint'
s.SIZES = (192,384,768,1536,3072)


def run():
    with zipfile.ZipFile(PRIOR/'replay.zip') as z:
        retained=json.loads(z.read('records.json'))
        templates={}
        for policy in (*s.POLICIES,*s.CONTROLS):
            r=retained[f'community-s23-n192-{policy}']
            template=s.RUNS/f'linked-{policy}'
            template.mkdir(parents=True,exist_ok=False)
            for name in s.IMAGES:
                (template/name).write_bytes(z.read('blobs/'+r['files'][name]))
            templates[policy]=template
        jobs,measurements,rows=[],[],[]
        rng=random.Random(20261124)
        for case in s.CASES:
            for seed in s.SEEDS:
                for n in s.SIZES:
                    refs,vertices=s.graph(case,seed,destinations=n)
                    features=[(v*17+i*13+3)%251 for v in range(vertices) for i in range(2)]
                    encodings={p:s.encode(refs,p) for p in s.POLICIES}
                    for p in s.POLICIES: s.validate(refs,p,encodings[p])
                    times={p:[] for p in s.POLICIES}
                    for trial in range(11):
                        order=list(s.POLICIES); rng.shuffle(order)
                        for rank,p in enumerate(order):
                            start=time.perf_counter_ns(); data=s.encode(refs,p)
                            elapsed=time.perf_counter_ns()-start
                            assert data==encodings[p]
                            del data
                            times[p].append(elapsed)
                            measurements.append(dict(case=case,seed=seed,destinations=n,policy=p,
                                                     trial=trial,order=rank,preparation_ns=elapsed))
                    for p in (*s.POLICIES,*s.CONTROLS):
                        key=f'{case}-s{seed}-n{n}-{p}'
                        source='stream16' if p in s.CONTROLS else p
                        q=statistics.quantiles(times[source],n=4,method='inclusive')
                        row=dict(key=key,case=case,seed=seed,destinations=n,references=len(refs),
                                 source_vertices=vertices,policy=p,tasklets=12,feature_bytes=8,
                                 preparation_median_ns=int(statistics.median(times[source])),
                                 preparation_q1_ns=q[0],preparation_q3_ns=q[2],
                                 cycle_source='retained-three-point' if key in retained else 'new-size')
                        if key in retained:
                            r=retained[key]
                            updated=dict(r['row']); updated.update(row)
                            assert updated['logical_sha256']==s.sha(s.pack(refs)+s.pack(features))
                            directory=s.RUNS/key; directory.mkdir(parents=True,exist_ok=False)
                            for name,digest in r['files'].items():
                                assert Path(name).name==name
                                (directory/name).write_bytes(z.read('blobs/'+digest))
                            for name,text in (('options.txt',r['options']),('simulate.stdout.txt',r['completion']),
                                              ('log.txt',''.join(f'{k}: {v}\n' for k,v in r['statistics'].items()))):
                                (directory/name).write_text(text)
                            rows.append(updated)
                        else:
                            jobs.append((row,refs,features,encodings[source],templates[p]))
        s.csv_write(s.OUT/'preparation.csv',measurements)
    cpu=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
             if line.startswith('model name'))
    (s.OUT/'host.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),
        cpu=cpu,allowed_cpus=sorted(os.sched_getaffinity(0)),timer='perf_counter_ns',trials=11,
        exclusive_host=False,concurrent_simulation_during_preparation=False),indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=2) as pool: rows+=list(pool.map(s.run_one,jobs))
    rows.sort(key=lambda r:(r['case'],int(r['seed']),int(r['destinations']),r['policy']))
    # Normalize column order across inherited and new records.
    fields=list(rows[0])
    rows=[{k:r[k] for k in fields} for r in rows]
    s.csv_write(s.OUT/'results.csv',[r for r in rows if r['policy'] in s.POLICIES])
    s.csv_write(s.OUT/'controls.csv',[r for r in rows if r['policy'] in s.CONTROLS])
    print(f'Combined {len(rows)} configurations: 108 retained, {len(jobs)} new.',flush=True)


def record():
    s.record()
    path=s.OUT/'manifest.json'; manifest=json.loads(path.read_text())
    manifest.update(new_simulations=72,retained_simulations=108,preparation_samples=1320,
                    sizes=list(s.SIZES),hardware_validation=False)
    for p in (Path(__file__).resolve(),PRIOR/'manifest.json'):
        manifest['sha256'][str(p.relative_to(s.ROOT))]=s.sha(p.read_bytes())
    path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')


def verify():
    manifest=json.loads((s.OUT/'manifest.json').read_text())
    for name,digest in manifest['sha256'].items(): assert s.sha((s.ROOT/name).read_bytes())==digest,name
    with zipfile.ZipFile(s.OUT/'replay.zip') as z:
        records=json.loads(z.read('records.json'))
        blobs={n[6:]:z.read(n) for n in z.namelist() if n.startswith('blobs/')}
    assert len(records)==manifest['records']==180
    for digest,data in blobs.items(): assert s.sha(data)==digest
    with zipfile.ZipFile(PRIOR/'replay.zip') as z: old=json.loads(z.read('records.json'))
    rows=s.csv_read(s.OUT/'results.csv')+s.csv_read(s.OUT/'controls.csv')
    times=s.csv_read(s.OUT/'preparation.csv'); assert len(times)==1320
    assert len({r['key'] for r in rows})==180
    assert sum(r['cycle_source']=='new-size' for r in rows)==72
    for r in rows:
        saved=records[r['key']]; assert saved['row']==r
        assert r['output_check']==r['traffic_check']=='passed'
        assert saved['completion'].strip()=='execution (0) is finished...'
        for digest in saved['files'].values(): assert digest in blobs
        for field,counter in (('cycles','Logic[0_0_0]_logic_cycle'),('instructions','Logic[0_0_0]_num_instructions'),
                              ('read_bytes','RowBuffer[0_0_0]_read_bytes'),('write_bytes','RowBuffer[0_0_0]_write_bytes')):
            assert r[field]==saved['statistics'][counter]
        decode=lambda f:bytes(map(int,blobs[saved['files'][f]].split()))
        assert s.sha(decode('input_dpu_mram_heap_pointer_name_0_0_0.bin'))==r['input_sha256']
        out=next(f for f in saved['files'] if f.startswith('output_'))
        assert s.sha(decode(out))==r['output_sha256']
        assert int(r['wram_reserved_bytes'])<=65536
        assert saved['files']['iram.bin']==r['iram_sha256']
        source='stream16' if r['policy'] in s.CONTROLS else r['policy']
        samples=[int(t['preparation_ns']) for t in times if t['policy']==source and
                 all(t[k]==r[k] for k in ('case','seed','destinations'))]
        assert len(samples)==11 and int(statistics.median(samples))==int(r['preparation_median_ns'])
        if r['key'] in old:
            assert saved['files']==old[r['key']]['files']
            assert saved['statistics']==old[r['key']]['statistics']
    for c in s.CASES:
        for seed in s.SEEDS:
            for n in s.SIZES:
                group=[r for r in rows if r['case']==c and r['seed']==str(seed) and r['destinations']==str(n)]
                assert {r['policy'] for r in group}==set((*s.POLICIES,*s.CONTROLS))
                assert len({r['logical_sha256'] for r in group})==len({r['output_sha256'] for r in group})==1
    print('Verified 180 configurations (72 new), 1,320 timings and five sizes for every input/policy.')
    return records,blobs


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['run','summarize','record','verify','replay'])
    p.add_argument('--all',action='store_true')
    p.add_argument('--records',nargs='+',default=['community-s23-n384-batch64',
        'community-s61-n1536-stream16_1024','grqc-s23-n1536-batch32','uniform-s61-n384-batch16'])
    p.add_argument('--destination',type=Path,default=s.ROOT/'build/access-plan-fivepoint-replay')
    args=p.parse_args()
    if args.action=='replay':
        s.verify=verify
        s.replay(args)
    else: {'run':run,'summarize':s.summarize,'record':record,'verify':verify}[args.action]()
