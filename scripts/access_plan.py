#!/usr/bin/env python3
"""Compile/run compact access-plan experiments, separate from the retained pilot."""
import argparse
from collections import defaultdict, deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics
import struct
import time
from types import SimpleNamespace
from wram_platform import ROOT, BUILD, compile_sources, invoke, bytefile

POLICIES = {'stream128': (0,128), 'stream256': (0,256), 'stream16': (0,128), 'history': (1,128),
            'plan_direct': (2,128), 'plan_lru': (2,128), 'plan_nextuse': (2,128),
            'batch': (3,256)}
DATA_SHA = 'a254442cdf5d684712578b630c2e0d7543518ab154ef2341cabb607572ce7230'


def pack(xs):
    return struct.pack(f'<{len(xs)}I', *xs)


def graph(case, seed, destinations=192):
    rng = random.Random(seed)
    if case == 'grqc':
        path = ROOT / '.downloads/ca-GrQc.txt.gz'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == DATA_SHA
        adj = defaultdict(set)
        for line in gzip.open(path, 'rt'):
            if line.startswith('#'): continue
            a,b = map(int,line.split())
            if a != b: adj[a].add(b); adj[b].add(a)
        vertices = sorted(adj)
        remap = {v:i for i,v in enumerate(vertices)}
        selected = rng.sample(vertices, destinations)
        rows = [[remap[rng.choice(sorted(adj[v]))] for _ in range(8)] for v in selected]
        return [v for row in rows for v in row],len(vertices)
    refs = []
    for dst in range(destinations):
        for _ in range(8):
            if case == 'community':
                v = ((dst//8)%32)*16 + rng.randrange(16) if rng.random()<.9 else rng.randrange(512)
            elif case == 'hubs':
                v = rng.randrange(8) if rng.random()<.65 else rng.randrange(512)
            elif case == 'uniform': v = rng.randrange(512)
            else: raise ValueError(case)
            refs.append(v)
    return refs,512


def plan(refs, tasklets, feature_bytes, policy):
    """Build a one-word/edge plan. Graph order and tasklet boundaries are fixed."""
    slots = 512//feature_bytes
    words,loads = [],0
    per = len(refs)//tasklets
    for start in range(0,len(refs),per):
        part = refs[start:start+per]
        resident = [-1]*slots
        location = {}
        recency = OrderedDict()
        future = defaultdict(deque)
        if policy == 'plan_nextuse':
            for p,v in enumerate(part): future[v].append(p)
        for p,v in enumerate(part):
            if policy == 'plan_nextuse': future[v].popleft()
            if policy in ('history','plan_direct'):
                slot = v % slots
                miss = resident[slot] != v
            else:
                miss = v not in location
                if not miss: slot = location[v]
                elif len(location)<slots: slot = resident.index(-1)
                elif policy == 'plan_lru': slot = location[next(iter(recency))]
                else:
                    # Furthest next reference; deterministic tie-break by slot.
                    slot = max(range(slots), key=lambda s: future[resident[s]][0] if future[resident[s]] else len(part))
            if miss:
                old = resident[slot]
                location.pop(old,None);recency.pop(old,None)
                resident[slot] = v; location[v] = slot; loads += 1
            recency.pop(v,None);recency[v] = None
            assert v < 1<<22
            words.append((0x80000000 | v<<9 if miss else 0) | slot*feature_bytes)
    # An independent interpreter validates every hit and load in the encoded plan.
    for start in range(0,len(refs),per):
        state = [-1]*slots
        for v,token in zip(refs[start:start+per],words[start:start+per]):
            slot = (token&511)//feature_bytes
            assert token&511 == slot*feature_bytes
            if token>>31: state[slot] = (token&0x7fffffff)>>9
            assert state[slot] == v
    return words,loads


def compile_all(args):
    for t in args.tasklets:
        first = True
        for f in args.features:
            for name in args.policies:
                if name == 'batch' and f != 8: continue
                mode,index = POLICIES[name]
                compile_sources(SimpleNamespace(tasklets=t,sdk=first,
                    benchmark=f'ap_{name}_f{f}',source=ROOT/'experiments/access-plan/task.c',
                    define=[f'-DMODE={mode}',f'-DINDEX_BYTES={index}',f'-DFEATURE_BYTES={f}',
                            f'-DINDEX_BITS={16 if name=="stream16" else 32}']))
                first = False


def batch_plan(refs, tasklets):
    segments,loads,metadata = [],0,0
    count=len(refs)//tasklets
    assert count%64 == 0
    for start in range(0,len(refs),count):
        segment=bytearray()
        for pos in range(start,start+count,64):
            part=refs[pos:pos+64]
            ids=list(dict.fromkeys(part));mapping={v:i for i,v in enumerate(ids)}
            codes=bytes(mapping[v] for v in part)
            assert [ids[c] for c in codes] == part
            raw=pack(ids)
            segment += pack([len(ids),64])+raw+bytes((-len(raw))%8)+codes
            loads += len(ids)
        metadata += len(segment)
        segments.append(segment)
    stride=(max(map(len,segments))+7)//8*8
    data=b''.join(s+bytes(stride-len(s)) for s in segments)
    return data,loads,metadata,stride


def run_one(job):
    case,seed,policy,t,f,template,args = job
    directory = args.run_directory/f'{case}-s{seed}-{policy}-t{t}-f{f}'
    if directory.exists(): raise FileExistsError(directory)
    shutil.copytree(template,directory)
    refs,nvertices = graph(case,seed)
    assert len(refs)% (t*8) == 0
    features = [[(v*17+i*13+3+args.value_epoch*19)%251 for i in range(f//4)] for v in range(nvertices)]
    expected = [sum(features[v][i] for v in refs[p:p+8]) for p in range(0,len(refs),8) for i in range(f//4)]
    planning = []
    stride=0
    if policy == 'batch':
        assert f == 8
        for _ in range(5):
            begin=time.perf_counter_ns()
            indices,loads,metadata,stride=batch_plan(refs,t)
            planning.append(time.perf_counter_ns()-begin)
    elif policy.startswith('stream'):
        words,loads = refs,len(refs)
    else:
        for _ in range(5):
            begin = time.perf_counter_ns()
            encoded,loads = plan(refs,t,f,policy)
            planning.append(time.perf_counter_ns()-begin)
        words = encoded if policy.startswith('plan_') else refs
    if policy != 'batch':
        indices = struct.pack(f'<{len(words)}H',*words) if policy == 'stream16' else pack(words)
        metadata=len(indices)
    data = indices+pack([x for row in features for x in row])
    output = len(data)
    bytefile(directory/'input_DPU_INPUT_ARGUMENTS_0_0.bin',pack([len(refs),len(indices),output,stride]))
    bytefile(directory/'input_dpu_mram_heap_pointer_name_0_0_0.bin',data)
    bytefile(directory/f'output_dpu_mram_heap_pointer_name_{output}_0_0.bin',pack(expected))
    (directory/'num_executions.txt').write_text('1\n')
    elapsed = invoke('simulate',directory,f'ap_{policy}_f{f}',t)
    stats = {k:int(v) for k,v in (line.split(': ') for line in (directory/'log.txt').read_text().splitlines())}
    reads,writes = metadata+loads*f,len(refs)//8*f
    assert reads == stats['RowBuffer[0_0_0]_read_bytes']
    assert writes == stats['RowBuffer[0_0_0]_write_bytes']
    values = dict(line.split(': ') for line in (directory/'values.txt').read_text().splitlines())
    wram = int(values['__sys_heap_pointer_reset'])
    assert wram <=65536
    result = dict(case=case,seed=seed,policy=policy,tasklets=t,feature_bytes=f,
        value_epoch=args.value_epoch,source_vertices=nvertices,references=len(refs),
        cycles=stats['Logic[0_0_0]_logic_cycle'],instructions=stats['Logic[0_0_0]_num_instructions'],
        read_bytes=reads,write_bytes=writes,feature_loads=loads,
        index_or_plan_bytes=len(indices),wram_reserved_bytes=wram,
        host_plan_median_ns=int(statistics.median(planning)) if policy.startswith('plan_') or policy=='batch' else 0,
        plan_builder_includes_validation=bool(planning),simulator_wall_seconds=round(elapsed,3),
        logical_input_sha256=hashlib.sha256(pack(refs)+pack([x for row in features for x in row])).hexdigest(),
        input_sha256=hashlib.sha256(data).hexdigest(),expected_sha256=hashlib.sha256(pack(expected)).hexdigest(),
        iram_sha256=hashlib.sha256((directory/'iram.bin').read_bytes()).hexdigest(),
        output_check='passed',traffic_check='passed')
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{directory.name}: {result["cycles"]} cycles, {reads} read bytes',flush=True)
    return result


def run_all(args):
    jobs=[]
    for t in args.tasklets:
        for f in args.features:
            for policy in args.policies:
                if policy == 'batch' and f != 8:continue
                template=args.run_directory/f'linked-{policy}-t{t}-f{f}'
                if template.exists():raise FileExistsError(template)
                invoke('link',template,f'ap_{policy}_f{f}',t)
                for case in args.cases:
                    for seed in args.seeds:jobs.append((case,seed,policy,t,f,template,args))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(run_one,jobs))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w') as file:
        w=csv.DictWriter(file,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    print(f'Wrote {len(results)} checked records to {args.output}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['compile','run'])
    p.add_argument('--tasklets',nargs='+',type=int,default=[4])
    p.add_argument('--features',nargs='+',type=int,choices=[8,64,256],default=[64])
    p.add_argument('--policies',nargs='+',choices=list(POLICIES),default=list(POLICIES))
    p.add_argument('--cases',nargs='+',choices=['community','uniform','hubs','grqc'],default=['community','uniform','hubs'])
    p.add_argument('--seeds',nargs='+',type=int,default=[7])
    p.add_argument('--value-epoch',type=int,default=0)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--run-directory',type=Path,default=ROOT/'runs/access-plan-screen')
    p.add_argument('--output',type=Path,default=ROOT/'experiments/access-plan/screen.csv')
    args=p.parse_args()
    if args.action=='compile':compile_all(args)
    else:run_all(args)
