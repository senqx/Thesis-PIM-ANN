#!/usr/bin/env python3
"""Remeasure corrected preparation separately; preserve historical DPU evidence."""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import os
import zipfile

import decision_study as study
import decision_analysis as analysis
import decision_report as report
from decision_artifact import byte_read

ROOT=study.ROOT
HISTORY=study.OUT
OUT=HISTORY/'corrected'
RUN=ROOT/'runs/decision-corrected'
PHASES=('calibration-t8','heldout-t8','controlled-t8')
NATIVE=('prepare_ns','inspect_ns','refresh_ns','prepare_min_ns','prepare_max_ns',
        'process_peak_rss_kib','metadata_bytes','source_feature_bytes')
REPLAY_KEYS=('494_bus-w2-hot-t8-e0','can__256-w32-bcsr4-t8-e0',
             'repeated-494_bus-w32-batch','494_bus-w2-hot-t8-e0-dram0.5')

def read(p):return json.loads(p.read_text())
def archive_records():
    with zipfile.ZipFile(HISTORY/'replay.zip') as z:
        return json.loads(z.read('records.json')),{n[6:]:z.read(n) for n in z.namelist() if n.startswith('blobs/')}

def freeze():
    files=[OUT/'PROTOCOL.md',HISTORY/'prepare.cpp',ROOT/'scripts/decision_analysis.py',
           HISTORY/'frozen-model.json',HISTORY/'manifest.json']
    return {str(p.relative_to(ROOT)):study.sha(p.read_bytes()) for p in files}

def prepare():
    if (OUT/'native.json').exists():raise RuntimeError('Retained timing exists; use a fresh --output directory.')
    if RUN.exists():raise RuntimeError('Use a fresh --run-directory to avoid cached native timings.')
    OUT.mkdir(parents=True,exist_ok=True)
    study.dump(OUT/'freeze.json',freeze())
    study.RUN=RUN
    study.native_build()
    host=read(RUN/'host-reproduction.json')
    assert '15.1.0' in host['compiler'],'Use the declared compiler or explicitly revise the protocol first.'
    shutil.copyfile(RUN/'host-reproduction.json',OUT/'host.json')
    records,blobs=archive_records();prepared={};proof=[]
    for key,record in sorted(records.items()):
        r=record['row'];files={n:blobs[d] for n,d in record['files'].items()}
        for epoch in range(int(files['num_executions.txt'])):
            old_args=byte_read(files[f'input_DPU_INPUT_ARGUMENTS_{epoch}_0.bin'])
            actual_epoch=study.ints(old_args)[7]
            nk=study.namekey(r['input'],r['words'],r['policy'],r['tasklets'],actual_epoch)
            if nk not in prepared:
                a=study.matrix(r['input'])
                data,args,expected,m,d=study.prepare_one(a,r['words'],r['policy'],actual_epoch,r['tasklets'])
                prepared[nk]=(data,args,expected,m,d)
            data,args,expected,m,d=prepared[nk]
            assert data==byte_read(files[f'input_dpu_mram_heap_pointer_name_0_{epoch}_0.bin']),key
            assert args==old_args,key
            assert expected==byte_read(files[f'output_dpu_mram_heap_pointer_name_{len(data)}_{epoch}_0.bin']),key
            proof.append(dict(record=key,epoch=epoch,preparation=nk,input_sha256=study.sha(data),
                              args_sha256=study.sha(args),output_sha256=study.sha(expected)))
    native={k:v[3] for k,v in prepared.items()}
    study.dump(OUT/'native.json',native);study.dump(OUT/'identity.json',proof)
    with zipfile.ZipFile(OUT/'preparation.zip','w',zipfile.ZIP_DEFLATED) as z:
        for key,(_,_,_,_,d) in sorted(prepared.items()):
            for p in sorted(d.iterdir()):
                info=zipfile.ZipInfo(key+'/'+p.name,date_time=(2026,11,24,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    for phase in PHASES:
        rows=read(HISTORY/f'{phase}.json')
        for r in rows:
            m=native[r['key']]
            for k,v in m.items():
                if k not in NATIVE:assert r[k]==v,(r['key'],k)
            r.update({k:m[k] for k in NATIVE})
        study.dump(OUT/f'{phase}.json',rows)
    # Explicit unchanged inputs for the existing report/plot functions.
    for name in ('frozen-model.json','sensitivity.json','repeated.json','concurrency.json'):
        shutil.copyfile(HISTORY/name,OUT/name)
    print(f'PASS: {len(prepared)} native preparations; {len(proof)} byte-identical archived invocations.',flush=True)

def analyze():
    assert read(OUT/'freeze.json')==freeze(),'Correction inputs changed after timing freeze.'
    analysis.OUT=OUT;report.OUT=OUT
    analysis.evaluate();render()

def render():
    analysis.OUT=OUT;report.OUT=OUT
    analysis.figures();report.build()

def check():
    """Sanitizers and accounting tests; capture completed fresh replay evidence."""
    destination=RUN/'sanitizers';destination.mkdir(parents=True,exist_ok=True)
    binary=destination/'prepare'
    command=['g++','-O1','-g','-std=c++17','-fsanitize=address,undefined',
             '-fno-omit-frame-pointer','-fno-pie','-no-pie',str(HISTORY/'prepare.cpp'),'-o',str(binary)]
    subprocess.run(command,check=True)
    checked=[]
    with zipfile.ZipFile(OUT/'preparation.zip') as z:
        for key in sorted(read(OUT/'native.json')):
            if not key.startswith('edgecase'):continue
            d=destination/key;d.mkdir(exist_ok=True)
            (d/'matrix.bin').write_bytes(z.read(key+'/matrix.bin'))
            _,w,p,t,e=key.rsplit('-',4);w=int(w[1:]);t=int(t[1:]);e=int(e[1:])
            result=subprocess.run([str(binary),str(d/'matrix.bin'),p,str(w),str(study.width(w)),
                str(e),str(d/'plan'),'1',str(t)],check=True,capture_output=True,text=True,
                env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
            assert not result.stderr,result.stderr
            for suffix in ('meta','features','metrics.json'):
                assert (d/f'plan.{suffix}').read_bytes()==z.read(key+f'/plan.{suffix}')
            checked.append(key)
    regression=subprocess.run(['python3',str(ROOT/'scripts/test_decision_correction.py')],check=True,capture_output=True,text=True)
    from decision_artifact import statistics as counters
    records,_=archive_records();replays={}
    for key in REPLAY_KEYS:
        d=RUN/'replay'/key;r=records[key]
        assert counters(d)==r['statistics']
        fresh=study.options((d/'options.txt').read_text());old=study.options(r['options'])
        assert {k:v for k,v in fresh.items() if not k.endswith('dirpath')}=={k:v for k,v in old.items() if not k.endswith('dirpath')}
        stdout=(d/'simulate.stdout.txt').read_text()
        count=int((d/'num_executions.txt').read_text())
        assert all(f'execution ({e}) is finished' in stdout for e in range(count))
        replays[key]=dict(counters=counters(d),options=fresh,invocations=count,
            stdout=stdout,log_sha256=study.sha((d/'log.txt').read_bytes()))
    study.dump(OUT/'checks.json',dict(sanitizer_command=command,sanitizer_cases=checked,
        regression_output=regression.stdout+regression.stderr,replays=replays))
    print(f'PASS: {len(checked)} sanitizer cases, accounting regressions, four fresh replay records.')

def record():
    paths=[p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
    paths += [ROOT/'scripts'/s for s in ('decision_correction.py','decision_analysis.py',
               'decision_report.py','test_decision_correction.py')]
    paths += [HISTORY/'prepare.cpp']
    study.dump(OUT/'manifest.json',dict(historical_manifest_sha256=study.sha((HISTORY/'manifest.json').read_bytes()),
        native_preparations=len(read(OUT/'native.json')),matched_invocations=len(read(OUT/'identity.json')),
        reused_simulation_records=485,scenarios=23040,
        sha256={str(p.relative_to(ROOT)):study.sha(p.read_bytes()) for p in paths}))

def verify():
    manifest=read(OUT/'manifest.json')
    for name,digest in manifest['sha256'].items():assert study.sha((ROOT/name).read_bytes())==digest,name
    assert manifest['historical_manifest_sha256']==study.sha((HISTORY/'manifest.json').read_bytes())
    assert read(OUT/'freeze.json')==freeze()
    records,blobs=archive_records();native=read(OUT/'native.json');proof=read(OUT/'identity.json')
    assert len(proof)==sum(int(blobs[r['files']['num_executions.txt']]) for r in records.values())==511
    assert {(p['record'],p['epoch']) for p in proof}=={(k,e) for k,r in records.items() for e in range(int(blobs[r['files']['num_executions.txt']]))}
    with zipfile.ZipFile(OUT/'preparation.zip') as z:
        for key,m in native.items():
            samples=list(csv.DictReader(io.StringIO(z.read(key+'/plan.timings.csv').decode())))
            assert len(samples)==31 and [int(s['sample']) for s in samples]==list(range(31))
            for metric in ('prepare_ns','inspect_ns','refresh_ns'):
                assert m[metric]==statistics.median(int(s[metric]) for s in samples),(key,metric)
            assert m['prepare_min_ns']==min(int(s['prepare_ns']) for s in samples)
            assert m['prepare_max_ns']==max(int(s['prepare_ns']) for s in samples)
            assert json.loads(z.read(key+'/plan.metrics.json'))==m['model_features']
        for p in proof:
            r=records[p['record']];row=r['row'];e=p['epoch'];key=p['preparation']
            data=z.read(key+'/plan.meta')+z.read(key+'/plan.features')
            old=byte_read(blobs[r['files'][f'input_dpu_mram_heap_pointer_name_0_{e}_0.bin']])
            args=byte_read(blobs[r['files'][f'input_DPU_INPUT_ARGUMENTS_{e}_0.bin']])
            expected=byte_read(blobs[r['files'][f'output_dpu_mram_heap_pointer_name_{len(data)}_{e}_0.bin']])
            assert data==old and study.sha(data)==p['input_sha256']
            assert study.sha(args)==p['args_sha256'] and study.sha(expected)==p['output_sha256']
            a=study.matrix(row['input']);w=row['words'];fb=study.width(w)
            from collections import Counter
            counts=Counter(c for _,c,_ in a['entries'])
            perm=sorted(range(a['columns']),key=lambda c:(-counts[c],c)) if row['policy']=='hot' else list(range(a['columns']))
            m=study.decode(a,w,row['policy'],z.read(key+'/plan.meta'),perm,study.ints(args)[5],row['tasklets'])
            assert all(native[key][k]==v for k,v in m.items())
    for phase in PHASES:
        old={r['key']:r for r in read(HISTORY/f'{phase}.json')}
        fresh=read(OUT/f'{phase}.json');assert set(old)=={r['key'] for r in fresh}
        for r in fresh:
            assert {k:v for k,v in r.items() if k not in NATIVE}=={k:v for k,v in old[r['key']].items() if k not in NATIVE}
            assert all(r[k]==native[r['key']][k] for k in NATIVE)
    for name in ('frozen-model.json','sensitivity.json','repeated.json','concurrency.json'):
        assert (OUT/name).read_bytes()==(HISTORY/name).read_bytes(),name
    held=read(OUT/'heldout-t8.json');model=read(OUT/'frozen-model.json')
    rows=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'scenarios.csv.gz').read_bytes()).decode())))
    assert len(rows)==23040
    assert len({tuple(d[k] for k in ('input','words','constrained','uses','bandwidth_mb_s','launch_us','rule')) for d in rows})==23040
    # Independently express each visited path and the accounting equation.
    for d in rows:
        rs={r['policy']:r for r in held if r['input']==d['input'] and r['words']==int(d['words'])}
        stream=rs['stream512'];constrained=d['constrained']=='True'
        eligible={p:r for p,r in rs.items() if not constrained or study.feasible(r,stream)}
        k=int(d['uses']);bw=float(d['bandwidth_mb_s'])*1e6;launch=float(d['launch_us'])*1e-6
        def elapsed(r,setup):
            return setup*1e-9+r['stored_metadata_bytes']/bw+k*(r['cycles']/350e6+r['refresh_ns']*1e-9+(r['rows']+r['columns'])*r['feature_bytes']/bw+launch)
        rules,_=analysis.choose_corrected(list(rs.values()),model,k,bw/1e6,launch*1e6,constrained)
        chosen,reported_setup=rules[d['rule']];assert chosen==d['chosen']
        path=['stream512'];inspection=True
        if d['rule']=='model':path=list(rs)
        elif d['rule']=='fixed':
            candidate=model['fixed'] if model['fixed'] in rs else 'stream512'
            if constrained and candidate!='stream512':path.append(candidate)
            else:path=[candidate];inspection=False
        elif d['rule']=='capacity' or chosen=='full':
            if 'full' not in rs:inspection=False
            elif constrained:path.append('full')
            else:path=['full'];inspection=False
        else:
            if constrained and 'full' in rs:path.append('full')
            path.append('hot')
            if chosen!='hot':path.append('batch')
        setup=sum(rs[p]['prepare_ns']+(rs[p]['inspect_ns'] if inspection else 0) for p in set(path))
        assert setup==reported_setup==float(d['setup_ns'])
        if d['rule']!='model':assert float(d['decision_ns'])==0
        best=min(elapsed(r,r['prepare_ns']) for r in eligible.values())
        value=elapsed(rs[chosen],setup+float(d['decision_ns']))
        assert abs(value-float(d['total_seconds']))<1e-12
        assert abs(best-float(d['oracle_seconds']))<1e-12
        assert abs(100*(value/best-1)-float(d['regret_pct']))<1e-9
        assert abs(100*(1-value/elapsed(stream,stream['prepare_ns']))-float(d['saving_vs_stream_pct']))<1e-9
    assert (OUT/'kernel-decisions.csv').read_bytes()==(HISTORY/'kernel-decisions.csv').read_bytes()
    summary=read(OUT/'summary.json')
    assert summary['kernel']==read(HISTORY/'summary.json')['kernel']
    train=read(OUT/'calibration-t8.json')
    calibration=sum((r['prepare_ns']+r['inspect_ns']+r['refresh_ns'])*1e-9+r['cycles']/350e6+
                    (r['stored_metadata_bytes']+(r['rows']+r['columns'])*r['feature_bytes'])/80e6 for r in train)
    assert abs(summary['calibration']['modelled_serial_seconds_at_80MB_s']-calibration)<1e-12
    allrows={r['key']:r for phase in PHASES for r in read(OUT/f'{phase}.json')}
    comparisons=study.table(OUT/'comparisons.csv')
    assert {r['key'] for r in comparisons}==set(allrows)
    for c in comparisons:
        r=allrows[c['key']];s=allrows[study.namekey(r['input'],r['words'],'stream512')]
        assert int(c['saved_cycles'])==s['cycles']-r['cycles']
        def margin(k):
            return (s['prepare_ns']-r['prepare_ns'])*1e-9+(s['stored_metadata_bytes']-r['stored_metadata_bytes'])/80e6+k*((s['cycles']-r['cycles'])/350e6+(s['refresh_ns']-r['refresh_ns'])*1e-9)
        assert abs(float(c['one_use_margin_us'])-margin(1)*1e6)<1e-7
        assert abs(float(c['long_lifetime_margin_us'])-margin(1024)*1e6)<1e-6
        threshold=c['plan_payback_uses_at_80MB_s']
        if threshold.isdigit():
            k=int(threshold);assert margin(k)>0 and (k==1 or margin(k-1)<=0)
    with zipfile.ZipFile(OUT/'preparation.zip') as z:
        for h in study.table(OUT/'host-timing-sensitivity.csv'):
            r=allrows[study.namekey(h['input'],int(h['words']),'hot')]
            s=allrows[study.namekey(h['input'],int(h['words']),'stream512')];k=int(h['uses'])
            def bounds(r,f):
                samples=list(csv.DictReader(io.StringIO(z.read(r['key']+'/plan.timings.csv').decode())))
                return f(int(x['prepare_ns']) for x in samples)*1e-9+r['stored_metadata_bytes']/80e6+k*(r['cycles']/350e6+f(int(x['refresh_ns']) for x in samples)*1e-9)
            assert abs(float(h['observed_envelope_low_margin_us'])-(bounds(s,min)-bounds(r,max))*1e6)<1e-6
            assert abs(float(h['observed_envelope_high_margin_us'])-(bounds(s,max)-bounds(r,min))*1e6)<1e-6
    primary=[r for r in rows if r['constrained']=='True' and float(r['bandwidth_mb_s'])==80 and float(r['launch_us'])==0]
    for rule in ('model','fixed','capacity','reuse'):
        for k in model['valid_uses']:
            group=[r for r in primary if r['rule']==rule and int(r['uses'])==k]
            assert len(group)==24
            s=summary[rule][str(k)]
            assert abs(s['mean_regret_pct']-statistics.mean(float(r['regret_pct']) for r in group))<1e-10
            assert s['worst_regret_pct']==max(float(r['regret_pct']) for r in group)
    criteria=study.table(OUT/'success-criteria.csv')
    for c in criteria:
        group=[r for r in primary if r['uses']==c['uses']]
        means={rule:statistics.mean(float(r['total_seconds']) for r in group if r['rule']==rule) for rule in ('model','fixed','capacity','reuse')}
        worst=max(100*(float(r['total_seconds'])/min(float(s['total_seconds']) for s in group if s['rule']!='model' and (r['input'],r['words'])==(s['input'],s['words']))-1) for r in group if r['rule']=='model')
        passed=means['model']<min(means[p] for p in ('fixed','capacity','reuse')) and worst<=5
        assert str(passed)==c['passes']
        assert abs(worst-float(c['worst_slowdown_vs_best_simple_pct']))<1e-9
    for series in read(OUT/'plotted-data.json'):
        assert series['x']==sorted(series['x'])
        if series['figure']=='decision-cost':
            assert series['x']==model['valid_uses']
            assert series['y']==[summary[series['policy']][str(k)]['mean_regret_pct'] for k in series['x']]
        else:
            assert len(series['x'])==5 if series['policy']!='full' else len(series['x'])<=5
            for x,y,key in zip(series['x'],series['y'],series['keys']):
                r=records[key]['row'];s=records[study.namekey(r['input'],r['words'],'stream512')]['row']
                assert x==(r['feature_bytes'] if series['figure']=='widths' else r['columns']*r['feature_bytes']/r['resident_capacity'])
                assert abs(y-r['cycles']/s['cycles'])<1e-12
    checks=read(OUT/'checks.json');assert len(checks['sanitizer_cases'])==28
    assert set(checks['replays'])==set(REPLAY_KEYS)
    for key,r in checks['replays'].items():assert r['counters']==records[key]['statistics']
    print(f'PASS: {len(native)} new native preparations, 511 identical invocation inputs, unchanged kernel decisions, 23,040 corrected scenarios and hashes.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','analyze','render','check','record','verify'))
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--run-directory',type=Path,default=RUN)
    a=parser.parse_args();OUT=a.output.resolve();RUN=a.run_directory.resolve()
    if OUT==HISTORY:raise ValueError('Cannot overwrite historical artifact.')
    globals()[a.action]()
