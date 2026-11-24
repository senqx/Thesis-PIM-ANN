#!/usr/bin/env python3
"""Archive, verify and replay the decision study; additional state/model checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import inspect
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile
from decision_study import (OUT,RUN,ROOT,T,POLICIES,IMAGES,sha,dump,pack,ints,width,
    capacity,matrix,prepare_one,decode,link,namekey,options,TRAIN,TEST,WORDS,table,run_one)
from wram_platform import BUILD,bytefile,invoke

def statistics(d):return dict(line.split(': ') for line in (d/'log.txt').read_text().splitlines())
def byte_read(data):return bytes(map(int,data.split()))

def repeats():
    """Three invocations in the same simulator process, with new source values."""
    results=[]
    for w in (2,32):
        for p in POLICIES:
            a=matrix('494_bus')
            if p=='full' and a['columns']*width(w)>capacity(w):continue
            key=f'repeated-494_bus-w{w}-{p}';d=RUN/'executions'/key
            if (d/'result.json').exists():results.append(json.loads((d/'result.json').read_text()));continue
            d.mkdir(parents=True,exist_ok=True);template,reserved=link(w,p,T)
            for file in IMAGES:(d/file).write_bytes((template/file).read_bytes())
            ms=[];hashes=[];firstmeta=None
            for epoch in range(3):
                data,args,out,m,prepared=prepare_one(a,w,p,epoch)
                meta=data[:m['stored_metadata_bytes']]
                if firstmeta is None:firstmeta=meta
                else:assert firstmeta==meta,'Feature changes must not rebuild structural decisions.'
                hashes.append(sha(out));ms.append(m)
                bytefile(d/f'input_DPU_INPUT_ARGUMENTS_{epoch}_0.bin',args)
                bytefile(d/f'input_dpu_mram_heap_pointer_name_0_{epoch}_0.bin',data)
                bytefile(d/f'output_dpu_mram_heap_pointer_name_{len(data)}_{epoch}_0.bin',out)
            assert len(set(hashes))==3
            (d/'num_executions.txt').write_text('3\n');elapsed=invoke('simulate',d,f'decision_{p}_w{w}',T)
            stats=statistics(d)
            assert int(stats['RowBuffer[0_0_0]_read_bytes'])==sum(m['expected_reads'] for m in ms)
            assert int(stats['RowBuffer[0_0_0]_write_bytes'])==sum(m['expected_writes'] for m in ms)
            assert all(f'execution ({i}) is finished' in (d/'simulate.stdout.txt').read_text() for i in range(3))
            r=dict(key=key,input='494_bus',words=w,policy=p,tasklets=T,split='repeated',executions=3,
                cycles=int(stats['Logic[0_0_0]_logic_cycle']),expected_reads=sum(m['expected_reads'] for m in ms),
                expected_writes=sum(m['expected_writes'] for m in ms),wram_reserved_bytes=reserved,
                output_hashes=hashes,structural_plan_sha256=sha(firstmeta),output_check='passed',traffic_check='passed',simulator_wall_seconds=elapsed)
            dump(d/'result.json',r);results.append(r);print(key,'passed',flush=True)
    dump(OUT/'repeated.json',results)

def sensitivity():
    base=[r for r in json.loads((OUT/'heldout-t8.json').read_text()) if r['input']=='494_bus' and r['words'] in (2,32)]
    jobs=[(r,scale) for r in base for scale in (.5,.75,1.25,1.5)]
    def one(job):
        row,scale=job;key=row['key']+f'-dram{scale}';d=RUN/'executions'/key
        if (d/'result.json').exists():return json.loads((d/'result.json').read_text())
        source=RUN/'executions'/row['key'];d.mkdir(parents=True,exist_ok=True)
        names=list(IMAGES)+['num_executions.txt']+[p.name for p in source.glob('input_*.bin')]+[p.name for p in source.glob('output_*.bin')]
        for name in names:(d/name).write_bytes((source/name).read_bytes())
        flags={k:round(v*scale) for k,v in {'t_rcd':32,'t_cl':32,'t_rp':32,'t_ras':78}.items()}
        cmd=[str(BUILD/'simulator'),'--root_dirpath',str(BUILD/'t8'),'--bin_dirpath',str(d),
             '--log_dirpath',str(d),'--benchmark',f'decision_{row["policy"]}_w{row["words"]}',
             '--num_tasklets','8','--num_simulation_threads','1']
        for k,v in flags.items():cmd.extend(['--'+k,str(v)])
        started=time.monotonic()
        with (d/'simulate.stdout.txt').open('w') as f:subprocess.run(cmd,env={**os.environ,'WRAM_STAGE':'simulate'},stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
        stats=statistics(d)
        assert int(stats['RowBuffer[0_0_0]_read_bytes'])==row['expected_reads']
        assert int(stats['RowBuffer[0_0_0]_write_bytes'])==row['expected_writes']
        r={**row,'key':key,'split':'sensitivity','timing_scale':scale,'timing_parameters':flags,
           'cycles':int(stats['Logic[0_0_0]_logic_cycle']),'instructions':int(stats['Logic[0_0_0]_num_instructions']),
           'simulator_wall_seconds':time.monotonic()-started}
        dump(d/'result.json',r);print(key,r['cycles'],'cycles',flush=True);return r
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(one,jobs))
    results+=[{**r,'timing_scale':1.,'timing_parameters':{'t_rcd':32,'t_cl':32,'t_rp':32,'t_ras':78}} for r in base]
    dump(OUT/'sensitivity.json',results)

def concurrency():
    jobs=[];excluded=[]
    for t in (4,12):
        for w in (2,32):
            for p in POLICIES:
                try:link(w,p,t)
                except AssertionError as error:
                    excluded.append(dict(tasklets=t,words=w,policy=p,reason=str(error)));continue
                for name in ('494_bus','can__256'):
                    a=matrix(name)
                    if p=='full' and a['columns']*width(w)>capacity(w,t):continue
                    prepare_one(a,w,p,0,t);jobs.append((name,w,p,t,0))
    with ThreadPoolExecutor(max_workers=4) as pool:results=[r for r in pool.map(run_one,jobs) if r]
    dump(OUT/'concurrency.json',dict(results=results,allocation_exclusions=excluded,
        note='Post-freeze robustness check; model remains calibrated at eight tasklets. Changed tasklets also change feasible retention capacity.'))

def structure_checks():
    original=matrix('edgecase');changed={**original,'name':'edgecase_changed',
        'entries':[[0,1,2],[0,5,3],[1,2,1],[8,4,2]]}
    empty={**original,'name':'edgecase_empty','entries':[]}
    dump(OUT/'inputs/edgecase_changed.json',changed);dump(OUT/'inputs/edgecase_empty.json',empty)
    results=[]
    for p in POLICIES:
        for a in (changed,empty):
            data,args,expected,metrics,prepared=prepare_one(a,2,p)
            olddata,oldargs,oldexpected,oldmetrics,oldprepared=prepare_one(original,2,p)
            assert data[:metrics['stored_metadata_bytes']]!=olddata[:oldmetrics['stored_metadata_bytes']]
            assert expected!=oldexpected
            results.append(run_one((a['name'],2,p,T,0)))
    dump(OUT/'structure-checks.json',results)

def record():
    records={};blobs={}
    for file in sorted((RUN/'executions').glob('*/result.json')):
        d=file.parent;r=json.loads(file.read_text())
        names=list(IMAGES)+['num_executions.txt']+[p.name for p in sorted(d.glob('input_*.bin'))]+[p.name for p in sorted(d.glob('output_*.bin'))]
        files={}
        for name in names:
            data=(d/name).read_bytes();digest=sha(data);blobs[digest]=data;files[name]=digest
        records[r['key']]=dict(row=r,files=files,statistics=statistics(d),options=(d/'options.txt').read_text(),completion=(d/'simulate.stdout.txt').read_text())
    with zipfile.ZipFile(OUT/'replay.zip','w',zipfile.ZIP_DEFLATED) as z:
        members={f'blobs/{k}':v for k,v in blobs.items()};members['records.json']=json.dumps(records,sort_keys=True).encode()
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    # Native raw samples, not only medians; reference construction is reproducible.
    with zipfile.ZipFile(OUT/'preparation.zip','w',zipfile.ZIP_DEFLATED) as z:
        for d in sorted((RUN/'prepared').iterdir()):
            for name in ('plan.timings.csv','plan.memory.json','plan.metrics.json'):
                info=zipfile.ZipInfo(d.name+'/'+name,date_time=(2026,11,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(d/name).read_bytes())
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json']
    paths+=[ROOT/'scripts'/name for name in ('decision_study.py','decision_analysis.py','decision_report.py','decision_artifact.py','wram_platform.py','access_plan_artifact.py')]
    from decision_study import write_table
    flat=[]
    fields=sorted(set().union(*(r['row'].keys() for r in records.values())))
    for r in records.values():
        flat.append({k:json.dumps(r['row'][k]) if isinstance(r['row'].get(k),(list,dict)) else r['row'].get(k,'') for k in fields})
    write_table(OUT/'results.csv',flat)
    paths.append(OUT/'results.csv')
    manifest=dict(records=len(records),kernel_invocations=sum(int(blobs[r['files']['num_executions.txt']].decode()) for r in records.values()),
        counts=dict(__import__('collections').Counter('concurrency' if r['row']['tasklets']!=T else r['row']['split'] for r in records.values())),
        simulator_commit='870d916334e9ff0b190f555f951a9ec3c4257781',hardware_validated=False,
        sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)})
    dump(OUT/'manifest.json',manifest);print('Archived',len(records),'distinct records.')

def verify():
    from decision_analysis import choose,total
    import csv
    import gzip
    import io
    import statistics as native_statistics
    manifest=json.loads((OUT/'manifest.json').read_text())
    # Retained measurements were produced by pre-correction sources. Verify those
    # exact historical files from immutable archive copies, not the working sources.
    historical_sources={
        'experiments/decision-study/prepare.cpp':'experiments/decision-study/archive/pre-change/prepare.cpp',
        'scripts/decision_analysis.py':'scripts/archive/pre-change/decision_analysis.py',
        'scripts/decision_artifact.py':'scripts/archive/pre-change/decision_artifact.py',
    }
    for name,digest in manifest['sha256'].items():
        archived=historical_sources.get(name,name)
        assert sha((ROOT/archived).read_bytes())==digest,name
    frozen=json.loads((OUT/'frozen-model.json').read_text())
    assert sha((OUT/'calibration-t8.json').read_bytes())==frozen['calibration_sha256']
    assert sha((OUT/'PROTOCOL.md').read_bytes())==frozen['protocol_sha256']
    assert sha((ROOT/'scripts/decision_study.py').read_bytes())==frozen['script_sha256']
    assert sha((OUT/'task.c').read_bytes())==frozen['kernel_sha256']
    assert sha((ROOT/'experiments/decision-study/archive/pre-change/prepare.cpp').read_bytes())==frozen['native_source_sha256']
    assert sha((inspect.getsource(choose)+inspect.getsource(total)).encode())==frozen['decision_rule_sha256']
    for name,digest in frozen['heldout_inputs'].items():assert sha((OUT/'inputs'/f'{name}.json').read_bytes())==digest
    with zipfile.ZipFile(OUT/'replay.zip') as z:
        records=json.loads(z.read('records.json'));blobs={name[6:]:z.read(name) for name in z.namelist() if name.startswith('blobs/')}
    assert len(records)==manifest['records']
    assert sum(int(blobs[r['files']['num_executions.txt']]) for r in records.values())==manifest['kernel_invocations']
    for digest,data in blobs.items():assert sha(data)==digest
    for key,record in records.items():
        r=record['row'];files={name:blobs[digest] for name,digest in record['files'].items()};stats=record['statistics']
        assert r['cycles']==int(stats['Logic[0_0_0]_logic_cycle'])
        assert r['expected_reads']==int(stats['RowBuffer[0_0_0]_read_bytes'])
        assert r['expected_writes']==int(stats['RowBuffer[0_0_0]_write_bytes'])
        vals=dict(line.split(': ') for line in files['values.txt'].decode().splitlines())
        assert int(vals['__sys_heap_pointer_reset'])==r['wram_reserved_bytes']<=65536
        a=matrix(r['input']);w=r['words'];fb=width(w)
        reads=writes=0
        for epoch in range(int(files['num_executions.txt'])):
            data=byte_read(files[f'input_dpu_mram_heap_pointer_name_0_{epoch}_0.bin'])
            args=ints(byte_read(files[f'input_DPU_INPUT_ARGUMENTS_{epoch}_0.bin']))
            assert args[:3]==[a['rows'],a['columns'],args[3]] and args[4]==len(data)
            from collections import Counter
            counts=Counter(e[1] for e in a['entries'])
            perm=sorted(range(a['columns']),key=lambda v:(-counts[v],v)) if r['policy']=='hot' else list(range(a['columns']))
            m=decode(a,w,r['policy'],data[:args[3]],perm,args[5],r['tasklets']);reads+=m['expected_reads'];writes+=m['expected_writes']
            if 'model_features' in r:assert m['model_features']==r['model_features'],key
            expected_x=pack([((v*17+f*13+3+args[7]*7)%19+1) if f<w else 0 for v in perm for f in range(fb//4)])
            assert data[args[3]:]==expected_x,key
            x=ints(data[args[3]:]);inverse={v:i for i,v in enumerate(perm)}
            output=[[0]*(fb//4) for _ in range(a['rows'])]
            for row,col,value in a['entries']:
                for f in range(w):output[row][f]+=value*x[inverse[col]*(fb//4)+f]
            expected=pack([v for row in output for v in row])
            assert byte_read(files[f'output_dpu_mram_heap_pointer_name_{len(data)}_{epoch}_0.bin'])==expected,key
            if int(files['num_executions.txt'])==1:
                assert sha(data)==r['input_sha256'] and sha(expected)==r['output_sha256']
                assert sha((OUT/'inputs'/f'{r["input"]}.json').read_bytes())==r['matrix_sha256']
            assert f'execution ({epoch}) is finished' in record['completion']
        assert reads==r['expected_reads'] and writes==r['expected_writes']
    # Native summaries must describe the retained samples, not unrelated timings.
    with zipfile.ZipFile(OUT/'preparation.zip') as z:
        for record in records.values():
            r=record['row']
            if r['split']=='repeated':continue
            key=namekey(r['input'],r['words'],r['policy'],r['tasklets'],r['epoch'])
            samples=list(csv.DictReader(io.StringIO(z.read(key+'/plan.timings.csv').decode())))
            assert len(samples)==31,key
            for metric in ('prepare_ns','inspect_ns','refresh_ns'):
                assert r[metric]==native_statistics.median(int(v[metric]) for v in samples),(key,metric)
    for phase in ('smoke-t8','calibration-t8','heldout-t8','controlled-t8','repeated','structure-checks','sensitivity'):
        for r in json.loads((OUT/f'{phase}.json').read_text()):
            stored=records[r['key']]['row']
            assert all(stored.get(k)==v for k,v in r.items() if k not in ('timing_scale','timing_parameters')),(phase,r['key'])
    for r in json.loads((OUT/'concurrency.json').read_text())['results']:assert records[r['key']]['row']==r
    # Every standard width is present; infeasible full residency is explicit.
    for split,names in (('calibration',TRAIN),('heldout',TEST)):
        rows=json.loads((OUT/f'{split}-t8.json').read_text())
        for name in names:
            for w in WORDS:
                expected={p for p in POLICIES if p!='full' or matrix(name)['columns']*width(w)<=capacity(w)}
                assert {r['policy'] for r in rows if r['input']==name and r['words']==w}==expected
        if split=='heldout':assert all(r['frozen_model_sha256']==sha((OUT/'frozen-model.json').read_bytes()) for r in rows)
    # Recompute all analytical scenarios without remeasuring prediction overhead.
    held=json.loads((OUT/'heldout-t8.json').read_text())
    scenarios=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'scenarios.csv.gz').read_bytes()).decode())))
    assert len(scenarios)==23040
    for d in scenarios:
        rs=[r for r in held if r['input']==d['input'] and r['words']==int(d['words'])]
        s=next(r for r in rs if r['policy']=='stream512')
        constrained=d['constrained']=='True';k=int(d['uses']);bw=float(d['bandwidth_mb_s']);launch=float(d['launch_us'])
        rules,prediction=choose(rs,frozen,k,bw,launch,constrained)
        policy,setup=rules[d['rule']];assert policy==d['chosen'] and setup==float(d['setup_ns'])
        chosen=next(r for r in rs if r['policy']==policy)
        from decision_study import feasible
        eligible=[r for r in rs if not constrained or feasible(r,s)]
        best=min(total(r,k,bw,launch) for r in eligible)
        elapsed=total(chosen,k,bw,launch,setup=setup+float(d['decision_ns']))
        assert abs(elapsed-float(d['total_seconds']))<1e-12
        assert abs(best-float(d['oracle_seconds']))<1e-12
        assert abs(100*(elapsed/best-1)-float(d['regret_pct']))<1e-9
    for series in json.loads((OUT/'plotted-data.json').read_text()):
        assert series['x']==sorted(series['x']) and len(series['x'])==len(series['y'])
        if series['figure']=='decision-cost':
            summary=json.loads((OUT/'summary.json').read_text())
            assert len(series['x'])==8
            for x,y in zip(series['x'],series['y']):assert y==summary[series['policy']][str(x)]['mean_regret_pct']
        else:
            assert len(series['x'])==5 if series['policy']!='full' else len(series['x'])<=5
            for x,y,key in zip(series['x'],series['y'],series['keys']):
                r=records[key]['row'];base=records[namekey(r['input'],r['words'],'stream512')]['row']
                expected_x=r['feature_bytes'] if series['figure']=='widths' else r['columns']*r['feature_bytes']/r['resident_capacity']
                assert x==expected_x and abs(y-r['cycles']/base['cycles'])<1e-12
    print(f'PASS: {len(records)} records; weighted outputs, decoded coordinates, bytes, allocations, frozen inputs, native samples, 23,040 scenarios and hashes.')

def replay(destination=None,keys=None,all_records=False):
    selected=keys or ('494_bus-w2-hot-t8-e0','can__256-w32-bcsr4-t8-e0','repeated-494_bus-w32-batch')
    with zipfile.ZipFile(OUT/'replay.zip') as z:
        records=json.loads(z.read('records.json'))
        if all_records:selected=sorted(records)
        for key in selected:
            r=records[key];d=(destination or RUN/'reproduction')/key;d.mkdir(parents=True,exist_ok=False)
            for name,digest in r['files'].items():(d/name).write_bytes(z.read('blobs/'+digest))
            opts=options(r['options'])
            local={**opts,'root_dirpath':str(BUILD/f't{opts["num_tasklets"]}'),
                   'bin_dirpath':str(d.resolve()),'log_dirpath':str(d.resolve())}
            cmd=[str(BUILD/'simulator')]
            for k,v in local.items():cmd.extend(['--'+k,str(v)])
            with (d/'simulate.stdout.txt').open('w') as f:
                subprocess.run(cmd,env={**os.environ,'WRAM_STAGE':'simulate'},stdout=f,
                    stderr=subprocess.STDOUT,check=True,timeout=600)
            assert statistics(d)==r['statistics'],key
            fresh=options((d/'options.txt').read_text())
            for k,v in opts.items():
                if not k.endswith('dirpath'):assert fresh[k]==v
            print(key,'all counters reproduced',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('repeat','sensitivity','concurrency','structure','record','verify','replay'))
    p.add_argument('--replay-directory',type=Path)
    select=p.add_mutually_exclusive_group();select.add_argument('--key',action='append');select.add_argument('--all',action='store_true')
    a=p.parse_args()
    if a.action=='replay':replay(a.replay_directory,a.key,a.all)
    else:{'repeat':repeats,'sensitivity':sensitivity,'concurrency':concurrency,'structure':structure_checks,'record':record,'verify':verify}[a.action]()
