#!/usr/bin/env python3
"""Bounded preparation/work-size sweep; preserves the earlier study unchanged."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import struct
import sys
import time
from types import SimpleNamespace
import zipfile

from access_plan import graph, pack, batch_plan
from access_plan_artifact import IMAGES, options
from wram_platform import ROOT, compile_sources, invoke, bytefile

OUT = ROOT/'experiments/access-plan-scaling'
RUNS = ROOT/'runs/access-plan-scaling'
POLICIES = ('stream16','batch16','batch32','batch64')
CONTROLS = ('stream16_256','stream16_1024')
SIZES = (192,768,3072)
CASES = ('community','uniform','grqc')
SEEDS = (23,61)
T = 12


def sha(data):
    return hashlib.sha256(data).hexdigest()


def csv_write(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def csv_read(path):
    with path.open() as f: return list(csv.DictReader(f))


def encode(refs, policy):
    if policy.startswith('stream16'):
        return struct.pack(f'<{len(refs)}H', *refs), 0
    window = int(policy.removeprefix('batch'))
    per = len(refs)//T
    segments = []
    for first in range(0,len(refs),per):
        segment = bytearray()
        for start in range(first,first+per,window):
            part = refs[start:start+window]
            ids = list(dict.fromkeys(part))
            mapping = {v:i for i,v in enumerate(ids)}
            raw = pack(ids)
            segment += pack([len(ids),window])+raw+bytes((-len(raw))%8)
            segment += bytes(mapping[v] for v in part)
        segments.append(segment)
    stride = (max(map(len,segments))+7)//8*8
    return b''.join(s+bytes(stride-len(s)) for s in segments),stride


def validate(refs, policy, encoded):
    data,stride = encoded
    if policy.startswith('stream16'):
        assert list(struct.unpack(f'<{len(refs)}H',data)) == refs
        return len(refs), len(data)
    window = int(policy.removeprefix('batch'))
    per = len(refs)//T
    loads,metadata = 0,0
    for tid in range(T):
        start = cursor = tid*stride
        for first in range(tid*per,(tid+1)*per,window):
            unique,n = struct.unpack_from('<II',data,cursor)
            assert n == window and 0 < unique <= 64
            cursor += 8
            ids = struct.unpack_from(f'<{unique}I',data,cursor)
            cursor += (unique*4+7)//8*8
            codes = data[cursor:cursor+n]; cursor += n
            assert [ids[i] for i in codes] == refs[first:first+n]
            loads += unique
        metadata += cursor-start
        assert not any(data[cursor:start+stride])
    if policy == 'batch64':
        assert (data,loads,metadata,stride) == batch_plan(refs,T)
    return loads,metadata


def compile_new():
    for window in (16,32):
        compile_sources(SimpleNamespace(tasklets=T,sdk=window==16,
            benchmark=f'scale_batch{window}',source=OUT/'task.c',
            define=['-DMODE=3','-DINDEX_BYTES=256','-DFEATURE_BYTES=8',f'-DBATCH_REFS={window}']))


def compile_controls():
    for size in (256,1024):
        compile_sources(SimpleNamespace(tasklets=T,sdk=False,benchmark=f'scale_stream16_{size}',
            source=ROOT/'experiments/access-plan/task.c',
            define=['-DMODE=0','-DINDEX_BITS=16','-DFEATURE_BYTES=8',f'-DINDEX_BYTES={size}']))


def templates():
    result = {}
    with zipfile.ZipFile(ROOT/'experiments/access-plan/replay.zip') as archive:
        records = json.loads(archive.read('records.json'))
        for policy, old in (('stream16','stream16'),('batch64','batch')):
            record = records[f'validation/community-s23-{old}-t12-f8']
            directory = RUNS/f'linked-{policy}'
            directory.mkdir(parents=True,exist_ok=False)
            for file in IMAGES:
                (directory/file).write_bytes(archive.read('blobs/'+record['files'][file]))
            result[policy] = directory
    for policy in ('batch16','batch32'):
        directory = RUNS/f'linked-{policy}'
        assert not directory.exists()
        invoke('link',directory,f'scale_{policy}',T)
        result[policy] = directory
    return result


def run_one(job):
    row,refs,features,encoded,template = job
    policy = row['policy']
    directory = RUNS/row['key']
    directory.mkdir(parents=True,exist_ok=False)
    for file in IMAGES: (directory/file).write_bytes((template/file).read_bytes())
    indices,stride = encoded
    loads,metadata = validate(refs,policy,encoded)
    expected = pack([sum(features[v*2+i] for v in refs[first:first+8])
                     for first in range(0,len(refs),8) for i in range(2)])
    data = indices+pack(features)
    assert len(data)+len(expected) <= 64*1024*1024
    bytefile(directory/'input_DPU_INPUT_ARGUMENTS_0_0.bin',pack([len(refs),len(indices),len(data),stride]))
    bytefile(directory/'input_dpu_mram_heap_pointer_name_0_0_0.bin',data)
    bytefile(directory/f'output_dpu_mram_heap_pointer_name_{len(data)}_0_0.bin',expected)
    (directory/'num_executions.txt').write_text('1\n')
    benchmark = {'stream16':'ap_stream16_f8','batch64':'ap_batch_f8'}.get(policy,f'scale_{policy}')
    elapsed = invoke('simulate',directory,benchmark,T)
    stats = dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines())
    assert int(stats['RowBuffer[0_0_0]_read_bytes']) == metadata+loads*8
    assert int(stats['RowBuffer[0_0_0]_write_bytes']) == len(expected)
    vals = dict(line.split(': ') for line in (directory/'values.txt').read_text().splitlines())
    wram = int(vals['__sys_heap_pointer_reset']); assert wram <= 65536
    row.update(cycles=int(stats['Logic[0_0_0]_logic_cycle']),
               instructions=int(stats['Logic[0_0_0]_num_instructions']),
               read_bytes=metadata+loads*8,write_bytes=len(expected),feature_loads=loads,
               stored_metadata_bytes=len(indices),read_metadata_bytes=metadata,
               wram_reserved_bytes=wram,simulator_wall_seconds=round(elapsed,3),
               logical_sha256=sha(pack(refs)+pack(features)),input_sha256=sha(data),
               output_sha256=sha(expected),iram_sha256=sha((directory/'iram.bin').read_bytes()),
               output_check='passed',traffic_check='passed')
    (directory/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print(row['key'],row['cycles'],'cycles',flush=True)
    return row


def run_all():
    linked = templates()
    jobs,measurements = [],[]
    rng = random.Random(20261123)
    for case in CASES:
        for seed in SEEDS:
            for size in SIZES:
                refs,vertices = graph(case,seed,destinations=size)
                assert len(refs)%(T*64) == 0
                features = [(v*17+i*13+3)%251 for v in range(vertices) for i in range(2)]
                encodings = {p:encode(refs,p) for p in POLICIES}  # warm-up
                for p in POLICIES: validate(refs,p,encodings[p])
                times = {p:[] for p in POLICIES}
                for trial in range(11):
                    order = list(POLICIES); rng.shuffle(order)
                    for rank,p in enumerate(order):
                        begin = time.perf_counter_ns()
                        output = encode(refs,p)
                        elapsed = time.perf_counter_ns()-begin
                        assert output == encodings[p]
                        del output  # do not time destruction of the previous policy's result
                        times[p].append(elapsed)
                        measurements.append(dict(case=case,seed=seed,destinations=size,policy=p,
                                                 trial=trial,order=rank,preparation_ns=elapsed))
                for p in POLICIES:
                    quartiles = statistics.quantiles(times[p],n=4,method='inclusive')
                    row = dict(key=f'{case}-s{seed}-n{size}-{p}',case=case,seed=seed,
                               destinations=size,references=len(refs),source_vertices=vertices,
                               policy=p,tasklets=T,feature_bytes=8,
                               preparation_median_ns=int(statistics.median(times[p])),
                               preparation_q1_ns=quartiles[0],preparation_q3_ns=quartiles[2])
                    jobs.append((row,refs,features,encodings[p],linked[p]))
    csv_write(OUT/'preparation.csv',measurements)
    cpu = next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
               if line.startswith('model name'))
    environment = dict(python=sys.version,platform=platform.platform(),cpu=cpu,
                       allowed_cpus=sorted(os.sched_getaffinity(0)),timer='perf_counter_ns',
                       trials=11,exclusive_host=False,concurrent_simulation_during_preparation=False)
    (OUT/'host.json').write_text(json.dumps(environment,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=2) as pool: rows = list(pool.map(run_one,jobs))
    csv_write(OUT/'results.csv',rows)
    print(f'Completed {len(rows)} output-checked configurations.',flush=True)


def summarize():
    rows = csv_read(OUT/'results.csv')+csv_read(OUT/'controls.csv')
    lut = {(r['case'],r['seed'],r['destinations'],r['policy']):r for r in rows}
    paired, sensitivity = [],[]
    for r in rows:
        if r['policy'].startswith('stream16'): continue
        b = min((lut[r['case'],r['seed'],r['destinations'],p] for p in ('stream16',*CONTROLS)),
                key=lambda x:int(x['cycles']))
        saving_ns = (int(b['cycles'])-int(r['cycles']))/0.35
        extra_ns = int(r['preparation_median_ns'])-int(b['preparation_median_ns'])
        extra_bytes = int(r['stored_metadata_bytes'])-int(b['stored_metadata_bytes'])
        def threshold(overhead):
            if saving_ns > 0: return max(1,math.floor(overhead/saving_ns)+1)
            return 1 if overhead-saving_ns < 0 else 'never'
        def last_faster(overhead):
            if saving_ns >= 0:
                return 'unbounded' if saving_ns > 0 or overhead < 0 else 'never'
            last = math.ceil(overhead/saving_ns)-1
            return last if last >= 1 else 'never'
        paired.append(dict(key=r['key'],case=r['case'],seed=r['seed'],destinations=r['destinations'],
                           policy=r['policy'],comparator=b['policy'],cycle_change_percent=100*(int(r['cycles'])/int(b['cycles'])-1),
                           saved_cycles=int(b['cycles'])-int(r['cycles']),saved_kernel_ns=saving_ns,
                           read_change_percent=100*(int(r['read_bytes'])/int(b['read_bytes'])-1),
                           extra_preparation_ns=extra_ns,extra_installed_bytes=extra_bytes,
                           first_faster_reuse_no_install=threshold(extra_ns)))
        for bandwidth in (0,0.1,1,5):  # zero denotes ignoring differential installation
            overhead = extra_ns+(extra_bytes/bandwidth if bandwidth else 0)
            for uses in (1,10,100,1000,10000):
                sensitivity.append(dict(key=r['key'],bandwidth_GBps=bandwidth,
                                         installation_model='ignored' if not bandwidth else 'bytes/rate',
                                         uses=uses,extra_total_ns=overhead-uses*saving_ns,
                                         first_faster_reuse=threshold(overhead),last_faster_reuse=last_faster(overhead)))
    csv_write(OUT/'paired.csv',paired); csv_write(OUT/'amortization.csv',sensitivity)
    lines = ['# Descriptive size and window comparisons','',
             'Means of two paired seeds. Negative percentages mean fewer cycles/bytes.',
             'Preparation is the mean of the two per-input medians, excluding validation.', '',
             'Each cycle comparison uses the fastest tested streaming buffer for that input.',
             'The 256/1,024-byte controls reuse identical stream16 host-encoding samples.', '',
             '| Input | Destinations | Policy | Preparation (µs) | Cycle change | Read change |',
             '| --- | ---: | --- | ---: | ---: | ---: |']
    for case in CASES:
        for size in SIZES:
            for policy in (*POLICIES,*CONTROLS):
                rr = [lut[case,str(s),str(size),policy] for s in SEEDS]
                bb = [min((lut[case,str(s),str(size),p] for p in ('stream16',*CONTROLS)),
                          key=lambda x:int(x['cycles'])) for s in SEEDS]
                prep = statistics.mean(int(r['preparation_median_ns'])/1000 for r in rr)
                dc = statistics.mean(100*(int(r['cycles'])/int(b['cycles'])-1) for r,b in zip(rr,bb))
                db = statistics.mean(100*(int(r['read_bytes'])/int(b['read_bytes'])-1) for r,b in zip(rr,bb))
                lines.append(f'| {case} | {size:,} | {policy} | {prep:,.1f} | {dc:+.2f}% | {db:+.2f}% |')
    (OUT/'comparisons.md').write_text('\n'.join(lines)+'\n')


def run_controls():
    jobs=[]
    baseline=[r for r in csv_read(OUT/'results.csv') if r['policy']=='stream16']
    for policy in CONTROLS:
        template=RUNS/f'linked-{policy}'
        assert not template.exists()
        invoke('link',template,f'scale_{policy}',T)
        for b in baseline:
            row=dict(b)
            row['policy']=policy
            row['key']=f'{b["case"]}-s{b["seed"]}-n{b["destinations"]}-{policy}'
            refs,vertices=graph(b['case'],int(b['seed']),destinations=int(b['destinations']))
            features=[(v*17+i*13+3)%251 for v in range(vertices) for i in range(2)]
            jobs.append((row,refs,features,encode(refs,policy),template))
    with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(run_one,jobs))
    csv_write(OUT/'controls.csv',rows)


def plot():
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/matplotlib-scaling'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    rows=csv_read(OUT/'results.csv')
    paired=csv_read(OUT/'paired.csv')
    fig,axes=plt.subplots(1,3,figsize=(14,4.4))
    for policy in POLICIES:
        ys=[statistics.mean(int(r['preparation_median_ns'])/1e6 for r in rows
                            if r['case']=='community' and r['destinations']==str(n) and r['policy']==policy)
            for n in SIZES]
        axes[0].plot(SIZES,ys,'o-',label=policy)
    axes[0].set(xscale='log',yscale='log',xlabel='Destinations per invocation',
                ylabel='CPU preparation (ms)',title='Preparation grows with work\nCommunity inputs')
    axes[0].legend(fontsize=8)
    for case,label,color in (('community','Community','tab:blue'),('grqc','Sampled ca-GrQc','tab:green'),
                             ('uniform','Uniform','tab:orange')):
        ys=[statistics.mean(float(r['cycle_change_percent']) for r in paired
                            if r['case']==case and r['destinations']==str(n) and r['policy']=='batch64')
            for n in SIZES]
        axes[1].plot(SIZES,ys,'o-',label=label,color=color)
        if case=='uniform': continue
        low,high=[],[]
        for n in SIZES[1:]:
            vals=[int(r['first_faster_reuse_no_install']) for r in paired if r['case']==case
                  and r['destinations']==str(n) and r['policy']=='batch64']
            low.append(min(vals));high.append(max(vals))
        means=[(a+b)/2 for a,b in zip(low,high)]
        axes[2].plot(SIZES[1:],means,'o-',label=label,color=color)
        axes[2].fill_between(SIZES[1:],low,high,color=color,alpha=.15)
    axes[1].axhline(0,color='black',linewidth=.8)
    axes[1].set(xscale='log',xlabel='Destinations per invocation',ylabel='DPU cycle change (%)',
                title='Larger work can change the ranking\n64-reference batches; lower is better')
    axes[1].legend(fontsize=8)
    axes[2].set(xscale='log',yscale='log',xlabel='Destinations per invocation',ylabel='First faster reuse count',
                title='Repeated use must repay preparation\nExtra installation omitted')
    axes[2].text(.04,.96,'192 destinations: no break-even\nUniform: no break-even at any tested size',
                 transform=axes[2].transAxes,va='top',fontsize=8)
    for ax in axes:
        ax.set_xticks(SIZES if ax!=axes[2] else SIZES[1:])
        ax.set_xticklabels([f'{n:,}' for n in (SIZES if ax!=axes[2] else SIZES[1:])])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(alpha=.2)
    axes[2].legend(fontsize=8,loc='lower left')
    fig.suptitle('Work size, preparation and reuse — measured Python construction + unvalidated DPU simulation',fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT/'scaling.png',dpi=160)
    plt.close(fig)


def record():
    blobs,records = {},{}
    for row in csv_read(OUT/'results.csv')+csv_read(OUT/'controls.csv'):
        directory = RUNS/row['key']
        files = list(IMAGES)+['num_executions.txt']
        files += [p.name for p in sorted(directory.glob('input_*.bin'))]
        files += [p.name for p in sorted(directory.glob('output_*.bin'))]
        mappings = {}
        for file in files:
            data = (directory/file).read_bytes(); digest=sha(data)
            blobs[digest]=data; mappings[file]=digest
        records[row['key']] = dict(row=row,files=mappings,
            options=(directory/'options.txt').read_text(),
            statistics=dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines()),
            completion=(directory/'simulate.stdout.txt').read_text())
    with zipfile.ZipFile(OUT/'replay.zip','w',zipfile.ZIP_DEFLATED) as z:
        members = {f'blobs/{k}':v for k,v in blobs.items()}
        members['records.json'] = json.dumps(records,indent=2,sort_keys=True).encode()
        for name,data in sorted(members.items()):
            info = zipfile.ZipInfo(name,date_time=(2026,11,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    paths = [p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
    paths += [ROOT/'scripts'/s for s in ('access_plan_scaling.py','access_plan.py','access_plan_artifact.py','wram_platform.py')]
    paths += [ROOT/'experiments/wram/THIRD_PARTY_NOTICES.txt',ROOT/'experiments/access-plan/manifest.json']
    manifest = dict(records=len(records),sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')


def verify():
    manifest = json.loads((OUT/'manifest.json').read_text())
    for path,digest in manifest['sha256'].items(): assert sha((ROOT/path).read_bytes())==digest,path
    with zipfile.ZipFile(OUT/'replay.zip') as z:
        records = json.loads(z.read('records.json'))
        blobs = {n[6:]:z.read(n) for n in z.namelist() if n.startswith('blobs/')}
    assert len(records)==manifest['records']==108
    for digest,data in blobs.items(): assert sha(data)==digest
    groups = {}
    for row in csv_read(OUT/'results.csv')+csv_read(OUT/'controls.csv'):
        r = records[row['key']]; assert r['row']==row
        assert r['completion'].strip()=='execution (0) is finished...'
        assert row['output_check']==row['traffic_check']=='passed'
        assert int(row['wram_reserved_bytes'])<=65536
        for column,counter in (('cycles','Logic[0_0_0]_logic_cycle'),('instructions','Logic[0_0_0]_num_instructions'),
                               ('read_bytes','RowBuffer[0_0_0]_read_bytes'),('write_bytes','RowBuffer[0_0_0]_write_bytes')):
            assert row[column]==r['statistics'][counter]
        for digest in r['files'].values(): assert digest in blobs
        decode = lambda f:bytes(map(int,blobs[r['files'][f]].split()))
        assert sha(decode('input_dpu_mram_heap_pointer_name_0_0_0.bin'))==row['input_sha256']
        out = next(f for f in r['files'] if f.startswith('output_'))
        assert sha(decode(out))==row['output_sha256']
        assert sha(blobs[r['files']['iram.bin']])==row['iram_sha256']
        groups.setdefault((row['case'],row['seed'],row['destinations']),[]).append(row)
    for group in groups.values():
        assert {r['policy'] for r in group}==set((*POLICIES,*CONTROLS))
        assert len({r['logical_sha256'] for r in group})==len({r['output_sha256'] for r in group})==1
    timings = csv_read(OUT/'preparation.csv')
    assert len(timings)==72*11
    for group in groups.values():
        for r in group:
            source_policy='stream16' if r['policy'] in CONTROLS else r['policy']
            samples=[int(t['preparation_ns']) for t in timings if t['policy']==source_policy
                     and all(t[k]==r[k] for k in ('case','seed','destinations'))]
            assert len(samples)==11 and int(statistics.median(samples))==int(r['preparation_median_ns'])
    paired={r['key']:r for r in csv_read(OUT/'paired.csv')}
    for r in csv_read(OUT/'amortization.csv'):
        p=paired[r['key']]; rate=float(r['bandwidth_GBps'])
        cost=float(p['extra_preparation_ns'])+(int(p['extra_installed_bytes'])/rate if rate else 0)
        saving=float(p['saved_kernel_ns'])
        assert math.isclose(float(r['extra_total_ns']),cost-int(r['uses'])*saving,abs_tol=1e-6)
        if r['first_faster_reuse']!='never':
            first=int(r['first_faster_reuse'])
            assert cost-first*saving < 0
            assert first==1 or cost-(first-1)*saving >= 0
        else: assert saving<=0 and cost-saving>=0
    print('Verified 108 configurations, 792 host timing samples, hashes, counters and paired work.')
    return records,blobs


def replay(args):
    records,blobs = verify()
    keys = sorted(records) if args.all else (args.records or [
        'community-s23-n3072-stream16','community-s23-n3072-stream16_1024',
        'community-s23-n3072-batch64','grqc-s61-n768-batch16','uniform-s23-n192-batch32'])
    for key in keys:
        r=records[key]; directory=args.destination/key
        directory.mkdir(parents=True,exist_ok=False)
        for file,digest in r['files'].items():
            assert Path(file).name==file
            (directory/file).write_bytes(blobs[digest])
        opts=options(r['options'])
        invoke('simulate',directory,opts['benchmark'],T)
        assert dict(line.split(': ') for line in (directory/'log.txt').read_text().splitlines())==r['statistics']
        new=options((directory/'options.txt').read_text())
        assert all(new[k]==v for k,v in opts.items() if k not in ('bin_dirpath','log_dirpath','root_dirpath'))
        print('Exact replay:',key,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['compile','compile-controls','run','run-controls','summarize','plot','record','verify','replay'])
    p.add_argument('--all',action='store_true')
    p.add_argument('--records',nargs='+')
    p.add_argument('--destination',type=Path,default=ROOT/'build/access-plan-scaling-replay')
    args=p.parse_args()
    if args.action=='replay': replay(args)
    else: {'compile':compile_new,'compile-controls':compile_controls,'run':run_all,
           'run-controls':run_controls,'summarize':summarize,'plot':plot,'record':record,'verify':verify}[args.action]()
