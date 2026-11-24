#!/usr/bin/env python3
"""Bounded standard-kernel decision study: prepare, compile, run, fit, archive."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import struct
import subprocess
import time
from types import SimpleNamespace
import zipfile

from access_plan_artifact import IMAGES, options, sha
from wram_platform import ROOT, bytefile, compile_sources, invoke

OUT=ROOT/'experiments/decision-study'
RUN=ROOT/'runs/decision-study'
POLICIES=('stream128','stream512','hot','full','batch','bcsr2','bcsr4')
WORDS=(1,2,4,8,16,32)
TRAIN=('bcsstk01','bcsstk06','west0067')
TEST=('494_bus','1138_bus','can__144','can__256')
GROUPS={'bcsstk01':'bcsstruc1','bcsstk06':'bcsstruc1','west0067':'chemwest',
        '494_bus':'psadmit','1138_bus':'psadmit','can__144':'cannes','can__256':'cannes'}
T=8

def pack(v):return struct.pack('<'+'I'*len(v),*v)
def ints(b):return list(struct.unpack('<'+'I'*(len(b)//4),b))
def align(v,n=8):return (v+n-1)//n*n
def width(w):return max(8,w*4)
def capacity(w,t=T):return ((65536-49152-t*(512+5*width(w)+32)-2048)//2048)*2048
def dump(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def table(path):
    with path.open() as f:return list(csv.DictReader(f))
def write_table(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def matrix(name):return json.loads((OUT/'inputs'/f'{name}.json').read_text())
def namekey(name,w,p,t=T,epoch=0):return f'{name}-w{w}-{p}-t{t}-e{epoch}'

def inputs():
    dest=OUT/'inputs';dest.mkdir(exist_ok=True)
    sources=[]
    for name in TRAIN+TEST:
        file=ROOT/'.downloads/decision-study'/f'{name}.mtx.gz'
        text=gzip.decompress(file.read_bytes()).decode()
        header=text.splitlines()[0].lower().split()
        assert header[:3]==['%%matrixmarket','matrix','coordinate']
        lines=[line.split() for line in text.splitlines()[1:] if line.strip() and not line.startswith('%')]
        n,m,z=map(int,lines[0]);assert len(lines)-1==z
        coords=set()
        for line in lines[1:]:
            r,c=int(line[0])-1,int(line[1])-1
            if len(line)>2 and float(line[2].replace('D','E'))==0:continue
            coords.add((r,c))
            if header[-1] in ('symmetric','hermitian') and r!=c:coords.add((c,r))
        a={'name':name,'split':'calibration' if name in TRAIN else 'heldout',
           'original_rows':n,'original_columns':m,'rows':align(n,4),'columns':align(m,4),
           'entries':[(r,c,1+(r+3*c)%3) for r,c in sorted(coords)]}
        dump(dest/f'{name}.json',a)
        url=f'https://math.nist.gov/pub/MatrixMarket2/Harwell-Boeing/{GROUPS[name]}/{name}.mtx.gz'
        sources.append(dict(name=name,url=url,sha256=sha(file.read_bytes()),
                            original_header=text.splitlines()[0],stored_coordinates=z,
                            expanded_nonzero_coordinates=len(coords),split=a['split']))
    # Keep exact public source bytes separately from structural projections.
    with zipfile.ZipFile(OUT/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in TRAIN+TEST:
            info=zipfile.ZipInfo(f'{name}.mtx.gz',date_time=(2026,11,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,(ROOT/'.downloads/decision-study'/f'{name}.mtx.gz').read_bytes())
    base=capacity(2)//8
    for kind in ('uniform','clustered'):
        for ratio in (.25,.5,1,2,4):
            cols=int(base*ratio);name=f'{kind}-c{cols}';rng=random.Random(271)
            entries=[]
            for r in range(512):
                if kind=='uniform':ids=rng.sample(range(cols),16)
                else:
                    # Neighboring groups share a 32-source region; no duplicates in a row.
                    start=((r//4)*37)%(cols-32)
                    ids=rng.sample(range(start,start+32),16)
                entries.extend((r,c,1+(r+3*c)%3) for c in sorted(ids))
            dump(dest/f'{name}.json',dict(name=name,split='controlled',original_rows=512,
                original_columns=cols,rows=512,columns=cols,capacity_ratio=ratio,entries=entries))
    # Edge cases include an empty group, empty rows and dimensions not divisible by four.
    dump(dest/'edgecase.json',dict(name='edgecase',split='correctness',original_rows=9,
        original_columns=7,rows=12,columns=8,entries=[(0,0,2),(0,6,3),(2,2,1),(8,6,2)]))
    dump(OUT/'sources.json',sources)
    print('Prepared seven public structures, ten capacity controls and one correctness input.')

def compile_all(tasklets=T):
    first=True
    for w in WORDS:
        for policy in POLICIES:
            mode=0 if policy.startswith('stream') else {'hot':1,'full':2,'batch':3,'bcsr2':4,'bcsr4':4}[policy]
            compile_sources(SimpleNamespace(tasklets=tasklets,sdk=first,
                benchmark=f'decision_{policy}_w{w}',source=OUT/'task.c',
                define=[f'-DMODE={mode}',f'-DWORDS={w}',f'-DFEATURE_BYTES={width(w)}',
                    f'-DINDEX_BYTES={128 if policy=="stream128" else 512}',
                    f'-DRESIDENT_BYTES={capacity(w,tasklets)}',f'-DBLOCK={2 if policy=="bcsr2" else 4}']))
            first=False

def native_build():
    (RUN/'native').mkdir(parents=True,exist_ok=True)
    subprocess.run(['g++','-O3','-std=c++17',str(OUT/'prepare.cpp'),'-o',str(RUN/'native/prepare')],check=True)
    host_path=OUT/'host.json' if not (OUT/'host.json').exists() else RUN/'host-reproduction.json'
    dump(host_path,dict(compiler=subprocess.check_output(['g++','--version'],text=True),
        machine=os.uname().machine,system=os.uname().sysname,
        cpu=next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),''),
        samples=31,warmup=3,frequency_mhz=350,tasklets=T,compile_flags='-O3 -std=c++17'))

def prepare_one(a,w,p,epoch=0,t=T):
    d=RUN/'prepared'/namekey(a['name'],w,p,t,epoch);d.mkdir(parents=True,exist_ok=True)
    rows,cols=a['rows'],a['columns'];entries=a['entries']
    ptr=[0]*(rows+1)
    for r,c,v in entries:ptr[r+1]+=1
    for r in range(rows):ptr[r+1]+=ptr[r]
    raw=pack([rows,cols,len(entries)]+ptr+[e[1] for e in entries]+[e[2] for e in entries])
    (d/'matrix.bin').write_bytes(raw)
    if not (d/'plan.meta').exists():
        result=subprocess.run([str(RUN/'native/prepare'),str(d/'matrix.bin'),p,str(w),str(width(w)),
                        str(epoch),str(d/'plan'),'31',str(t)],check=True,capture_output=True,text=True)
        (d/'plan.memory.json').write_text(result.stdout)
    meta=(d/'plan.meta').read_bytes();x=(d/'plan.features').read_bytes()
    counts=Counter(e[1] for e in entries)
    perm=sorted(range(cols),key=lambda v:(-counts[v],v)) if p=='hot' else list(range(cols))
    expected_x=pack([((v*17+f*13+3+epoch*7)%19+1) if f<w else 0
                     for v in perm for f in range(width(w)//4)])
    assert x==expected_x
    out=[[0]*(width(w)//4) for _ in range(rows)]
    for r,c,v in entries:
        for f in range(w):out[r][f]+=v*((c*17+f*13+3+epoch*7)%19+1)
    assert max(max(r) for r in out)<2**31
    expected=pack([v for r in out for v in r])
    features=len(meta);output=features+len(x);hot=min(cols,capacity(w,t)//width(w))
    args=pack([rows,cols,len(meta),features,output,hot,len(entries),epoch])
    metrics=decode(a,w,p,meta,perm,hot,t)
    assert metrics['model_features']==json.loads((d/'plan.metrics.json').read_text())
    timing=table(d/'plan.timings.csv')
    metrics.update(prepare_ns=statistics.median(int(r['prepare_ns']) for r in timing),
                   inspect_ns=statistics.median(int(r['inspect_ns']) for r in timing),
                   refresh_ns=statistics.median(int(r['refresh_ns']) for r in timing),
                   prepare_min_ns=min(int(r['prepare_ns']) for r in timing),
                   prepare_max_ns=max(int(r['prepare_ns']) for r in timing))
    memory=json.loads((d/'plan.memory.json').read_text())
    memory['source_feature_bytes']=memory.pop('feature_bytes')
    metrics.update(memory)
    return meta+x,args,expected,metrics,d

def decode(a,w,p,meta,perm,hot,t):
    """Independent representation decoder and exact transfer accounting."""
    rows=a['rows'];fb=width(w);entries=[]
    read=[0]*t;calls=[0]*t;ops=[0]*t
    u=lambda pos:struct.unpack_from('<I',meta,pos)[0]
    if p in ('hot','full'):
        for pos in range(0,hot*fb,2048):
            tid=(pos//2048)%t;read[tid]+=min(2048,hot*fb-pos);calls[tid]+=1
    for first in range(0,rows,4):
        tid=(first//4)%t
        if p.startswith('stream') or p in ('hot','full'):
            read[tid]+=32;calls[tid]+=1;base=align((rows+1)*4,32)
            for r in range(first,first+4):
                lo,hi=u(r*4),u(r*4+4);count=hi-lo
                read[tid]+=count*8;calls[tid]+=math.ceil(count/(16 if p=='stream128' else 64))
                for pos in range(lo,hi):
                    c,v=u(base+pos*8),u(base+pos*8+4);entries.append((r,perm[c],v));ops[tid]+=w
                    if p.startswith('stream') or (p=='hot' and c>=hot):read[tid]+=fb;calls[tid]+=1
        elif p=='batch':
            g=first//4;cursor,end=u(g*4),u(g*4+4);read[tid]+=16;calls[tid]+=1
            while cursor<end:
                unique,n=u(cursor),u(cursor+4);cursor+=8;read[tid]+=8;calls[tid]+=1
                assert 0<unique<=min(64,512//fb) and 0<n<=64
                ids=ints(meta[cursor:cursor+4*unique]);cursor+=align(4*unique)
                weights=ints(meta[cursor:cursor+4*n]);cursor+=align(4*n)
                slots=meta[cursor:cursor+n];cursor+=align(n)
                read[tid]+=align(4*unique)+align(4*n)+align(n)+unique*fb;calls[tid]+=3+unique
                for slot,v in zip(slots,weights):
                    assert slot&63<unique
                    entries.append((first+(slot>>6),ids[slot&63],v));ops[tid]+=w
            assert cursor==end
        else:
            b=2 if p=='bcsr2' else 4
            for rr in range(0,4,b):
                g=(first+rr)//b;cursor,end=u(g*4),u(g*4+4);read[tid]+=16;calls[tid]+=1
                while cursor<end:
                    col=u(cursor);assert col%b==0 and col+b<=a['columns']
                    vals=ints(meta[cursor+8:cursor+8+4*b*b]);cursor+=8+4*b*b
                    read[tid]+=8+4*b*b+b*fb;calls[tid]+=3
                    for r in range(b):
                        for c in range(b):
                            v=vals[r*b+c]
                            if v:entries.append((first+rr+r,col+c,v));ops[tid]+=w
                assert cursor==end
    assert sorted(entries)==[tuple(e) for e in a['entries']],(a['name'],p,'coordinate mismatch')
    return dict(expected_reads=sum(read),expected_writes=rows*fb,dma_calls=sum(calls)+rows//4,
        max_dma_calls=max(calls),max_products=max(ops),max_thread_reads=max(read),
        stored_metadata_bytes=len(meta),hot_entries=hot if p in ('hot','full') else 0,
        model_features=[1,max(ops),sum(read)/8,max(calls),rows*w])

def link(w,p,t):
    template=RUN/'linked'/f'{p}-w{w}-t{t}'
    if not (template/'iram.bin').exists():invoke('link',template,f'decision_{p}_w{w}',t)
    vals=dict(line.split(': ') for line in (template/'values.txt').read_text().splitlines())
    assert int(vals['__sys_heap_pointer_reset'])<=65536,(p,w,t,vals['__sys_heap_pointer_reset'])
    return template,int(vals['__sys_heap_pointer_reset'])

def run_one(job):
    name,w,p,t,epoch=job;key=namekey(name,w,p,t,epoch);d=RUN/'executions'/key
    if (d/'result.json').exists():return json.loads((d/'result.json').read_text())
    a=matrix(name)
    if p=='full' and a['columns']*width(w)>capacity(w,t):return None
    data,args,out,m,prepared=prepare_one(a,w,p,epoch,t)
    template,reserved=link(w,p,t);d.mkdir(parents=True,exist_ok=True)
    for file in IMAGES:(d/file).write_bytes((template/file).read_bytes())
    bytefile(d/'input_DPU_INPUT_ARGUMENTS_0_0.bin',args)
    bytefile(d/'input_dpu_mram_heap_pointer_name_0_0_0.bin',data)
    bytefile(d/f'output_dpu_mram_heap_pointer_name_{len(data)}_0_0.bin',out)
    (d/'num_executions.txt').write_text('1\n')
    elapsed=invoke('simulate',d,f'decision_{p}_w{w}',t)
    stats=dict(line.split(': ') for line in (d/'log.txt').read_text().splitlines())
    assert int(stats['RowBuffer[0_0_0]_read_bytes'])==m['expected_reads'],(key,'reads',stats['RowBuffer[0_0_0]_read_bytes'],m)
    assert int(stats['RowBuffer[0_0_0]_write_bytes'])==m['expected_writes']
    row=dict(key=key,input=name,split=a['split'],words=w,feature_bytes=width(w),policy=p,
        tasklets=t,epoch=epoch,rows=a['rows'],columns=a['columns'],nnz=len(a['entries']),
        cycles=int(stats['Logic[0_0_0]_logic_cycle']),instructions=int(stats['Logic[0_0_0]_num_instructions']),
        wram_reserved_bytes=reserved,resident_capacity=capacity(w,t),**m,
        input_sha256=sha(data),output_sha256=sha(out),matrix_sha256=sha((OUT/'inputs'/f'{name}.json').read_bytes()),
        simulator_wall_seconds=round(elapsed,3),output_check='passed',traffic_check='passed')
    if a['split']=='heldout':row['frozen_model_sha256']=sha((OUT/'frozen-model.json').read_bytes())
    dump(d/'result.json',row);print(key,row['cycles'],'cycles',flush=True);return row

def jobs(split,t=T):
    if split=='smoke':return [('edgecase',w,p,t,0) for w in (1,32) for p in POLICIES]
    if split=='calibration':names=TRAIN;ws=WORDS
    elif split=='heldout':
        assert (OUT/'frozen-model.json').exists(),'Freeze the selector before evaluating held-out timings.'
        names=TEST;ws=WORDS
    elif split=='controlled':names=tuple(p.stem for p in sorted((OUT/'inputs').glob('*.json')) if p.stem.startswith(('uniform','clustered')));ws=(2,)
    elif split=='concurrency':names=('494_bus','can__256');ws=(2,32)
    elif split=='refresh':return [('494_bus',w,p,t,e) for w in (2,32) for p in POLICIES for e in (1,2)]
    else:raise ValueError(split)
    return [(n,w,p,t,0) for n in names for w in ws for p in POLICIES]

def run_split(split,t=T):
    work=jobs(split,t)
    # Link each distinct image serially; the linker writes shared build state.
    for w,p in sorted({(w,p) for n,w,p,tt,e in work}):link(w,p,t)
    # Measure native preparation without this study's DPU simulations competing for CPU.
    for n,w,p,tt,e in work:
        a=matrix(n)
        if p!='full' or a['columns']*width(w)<=capacity(w,t):prepare_one(a,w,p,e,t)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=[r for r in pool.map(run_one,work) if r]
    output=OUT/f'{split}-t{t}.json'
    if output.exists():output=RUN/f'{split}-t{t}-reproduction.json'
    dump(output,rows)
    print(f'Completed {len(rows)} {split} executions.',flush=True)

def fit():
    import itertools
    import inspect
    import numpy as np
    from decision_analysis import choose, total
    started=time.perf_counter()
    assert not (OUT/'frozen-model.json').exists(),'Do not overwrite the frozen selector.'
    train=json.loads((OUT/'calibration-t8.json').read_text());models={}
    for p in POLICIES:
        rows=[r for r in train if r['policy']==p]
        x=np.array([r['model_features'] for r in rows],dtype=float);y=np.array([r['cycles'] for r in rows],dtype=float)
        scale=np.maximum(np.max(x,axis=0),1);xs=x/scale;best=None
        # Five explanatory terms; enumerate active sets for nonnegative least squares.
        for size in range(1,6):
            for subset in itertools.combinations(range(5),size):
                beta=np.linalg.lstsq(xs[:,subset],y,rcond=None)[0]
                if min(beta)<-1e-7:continue
                coeff=np.zeros(5);coeff[list(subset)]=np.maximum(beta,0)
                error=float(np.sum((xs@coeff-y)**2))
                if best is None or error<best[0]:best=(error,coeff/scale)
        models[p]={'coefficients':best[1].tolist(),'training_rmse_cycles':math.sqrt(best[0]/len(rows)),'records':len(rows)}
    # Choose a deployable fixed non-full method by geometric mean ratio; reject budget violators per input.
    scores={}
    for p in POLICIES:
        if p=='full':continue
        ratios=[]
        for n in TRAIN:
            for w in WORDS:
                rs=[r for r in train if r['input']==n and r['words']==w]
                s=next(r for r in rs if r['policy']=='stream512')
                r=next(r for r in rs if r['policy']==p)
                if not feasible(r,s):r=s
                ratios.append(r['cycles']/s['cycles'])
        scores[p]=math.exp(statistics.mean(math.log(v) for v in ratios))
    model=dict(models=models,fixed=min(scores,key=scores.get),fixed_training_scores=scores,
        features=['constant','max_tasklet_products','total_read_bytes_div8','max_tasklet_dma_calls','output_values'],
        calibration_sha256=sha((OUT/'calibration-t8.json').read_bytes()),
        protocol_sha256=sha((OUT/'PROTOCOL.md').read_bytes()),
        script_sha256=sha(Path(__file__).read_bytes()),kernel_sha256=sha((OUT/'task.c').read_bytes()),
        native_source_sha256=sha((OUT/'prepare.cpp').read_bytes()),
        decision_rule_sha256=sha((inspect.getsource(choose)+inspect.getsource(total)).encode()),
        heldout_inputs={n:sha((OUT/'inputs'/f'{n}.json').read_bytes()) for n in TEST},
        reuse_rule='full if feasible; otherwise hot if top-capacity frequency >= 0.5; otherwise batch if total local reads <= half of streaming; otherwise stream512',
        capacity_rule='full if it fits, otherwise stream512',frequency_mhz=350,
        valid_uses=[1,2,4,8,16,64,256,1024],bandwidth_mb_s=[20,40,80,160,320],launch_us=[0,10,100],
        claim_threshold='repay inspection, improve over simple rules; no >5% primary regression',fit_seconds=time.perf_counter()-started)
    dump(OUT/'frozen-model.json',model);print('Frozen model; fixed policy:',model['fixed'])

def feasible(r,s):return r['stored_metadata_bytes']<=s['stored_metadata_bytes'] and r['expected_reads']+r['expected_writes']<=s['expected_reads']+s['expected_writes']

def main():
    global RUN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inputs','native','compile','run','fit'))
    parser.add_argument('--split',default='smoke',choices=('smoke','calibration','heldout','controlled','refresh','concurrency'))
    parser.add_argument('--tasklets',type=int,default=T)
    parser.add_argument('--run-directory',type=Path)
    args=parser.parse_args()
    if args.run_directory:RUN=args.run_directory.resolve()
    if args.action=='inputs':inputs()
    elif args.action=='native':native_build()
    elif args.action=='compile':compile_all(args.tasklets)
    elif args.action=='run':run_split(args.split,args.tasklets)
    else:fit()

if __name__=='__main__':main()
