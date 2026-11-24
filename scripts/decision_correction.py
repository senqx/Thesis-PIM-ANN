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
    study.dump(OUT/'accounting-provenance.json',dict(prediction_timing='new-measurement',note='Fresh reproduction; native and prediction timings may vary.'))
    analysis.evaluate();render()

def reaccount():
    """Recompute accounting from retained costs; no timing or simulator work."""
    from review_decision_costs import checkpoint_bytes, verify_checkpoint
    verify_checkpoint()
    raw=checkpoint_bytes(HISTORY/'corrected/scenarios.csv.gz')
    previous=list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode())))
    costs={}
    for r in previous:
        if r['rule']!='model':continue
        key=(r['input'],int(r['words']),r['constrained']=='True',int(r['uses']),int(r['bandwidth_mb_s']))
        value=float(r['decision_ns'])
        if key in costs:assert costs[key]==value
        costs[key]=value
    assert len(costs)==1920
    # This is a disclosed post-review accounting revision, not a timing freeze.
    study.dump(OUT/'freeze.json',freeze())
    analysis.OUT=OUT;report.OUT=OUT
    study.dump(OUT/'accounting-provenance.json',dict(prediction_timing='retained',source_commit='898052a9acfc09ddcefcab73662feb62d76b2456',source_scenarios_sha256=study.sha(raw),prediction_intervals=1920,native_measurements_changed=False,simulation_records_changed=False,refresh_estimates='Per-input retained medians granted free of collection cost; optimistic information assumption.'))
    analysis.evaluate(prediction_costs=costs)
    render()


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
    paths += [HISTORY/'prepare.cpp',HISTORY/'archive/pre-direct.zip',ROOT/'scripts/review_decision_costs.py']
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
        # Independent ledger: compute header rejections without invoking the lazy
        # controller. Inspect hot/batch only when their reuse threshold is needed.
        m,z,f,c=(stream[key] for key in ('columns','nnz','feature_bytes','resident_capacity'))
        full_ok=m*f<=c and (not constrained or m<=z)
        hot_ok=not constrained or z>=min(m,c//f)
        if d['rule']=='model':
            prepared=list(rs);inspected=list(rs)
        elif d['rule'] in ('fixed','capacity') or (d['rule']=='reuse' and full_ok):
            expected=(model['fixed'] if hot_ok else 'stream512') if d['rule']=='fixed' else ('full' if full_ok else 'stream512')
            assert chosen==expected
            prepared=[chosen];inspected=[]
        else:
            h=min(m,c//f)
            visit_hot=bool(z and h and hot_ok)
            prepared=['hot'] if visit_hot else []
            known_hot=visit_hot and 2*(h*(z//m)+min(h,z%m))>=z
            inspected=['hot'] if visit_hot and not known_hot else []
            if chosen!='hot':
                prepared.append('batch');inspected.append('batch')
            if chosen=='stream512':prepared.append('stream512')
        setup=sum(rs[p]['prepare_ns'] for p in prepared)+sum(rs[p]['inspect_ns'] for p in inspected)
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
        assert abs(means['model']-float(c['model_mean_seconds']))<1e-12
        assert abs(min(means[p] for p in ('fixed','capacity','reuse'))-float(c['best_simple_mean_seconds']))<1e-12
        assert abs(worst-float(c['worst_slowdown_vs_best_simple_pct']))<1e-9
        zero_times=[];zero_slowdowns=[]
        for r in group:
            if r['rule']!='model':continue
            selected=next(v for v in held if (v['input'],v['words'],v['policy'])==(r['input'],int(r['words']),r['chosen']))
            ztime=(selected['prepare_ns']*1e-9+selected['stored_metadata_bytes']/80e6
                +int(c['uses'])*(selected['cycles']/350e6+selected['refresh_ns']*1e-9
                    +(selected['rows']+selected['columns'])*selected['feature_bytes']/80e6))
            simple=min(float(v['total_seconds']) for v in group if v['rule']!='model'
                       and (v['input'],v['words'])==(r['input'],r['words']))
            zero_times.append(ztime);zero_slowdowns.append(100*(ztime/simple-1))
        zmean=statistics.mean(zero_times);zworst=max(zero_slowdowns)
        assert abs(zmean-float(c['zero_overhead_model_mean_seconds']))<1e-12
        assert abs(zworst-float(c['zero_overhead_worst_slowdown_vs_best_simple_pct']))<1e-9
        assert str(zmean<min(means[p] for p in ('fixed','capacity','reuse')) and zworst<=5)==c['zero_overhead_passes']
    audit_path=OUT/'accounting-audit.json'
    if audit_path.exists():
        audit=read(audit_path)
        for name,digest in audit['input_sha256'].items():
            assert study.sha((ROOT/name).read_bytes())==digest,name
        assert audit['avoidable_capacity_charge_us']==[0,0]
        assert not audit['zero_refresh_changed_choices']
        for criterion,diagnostic in zip(criteria,audit['zero_selection_overhead']):
            assert int(criterion['uses'])==diagnostic['uses']
            assert (criterion['zero_overhead_passes']=='True')==diagnostic['passes']
            assert abs(float(criterion['best_simple_mean_seconds'])*1000-diagnostic['best_simple_mean_ms'])<1e-9
            assert abs(float(criterion['zero_overhead_worst_slowdown_vs_best_simple_pct'])-diagnostic['worst_slowdown_pct'])<1e-9
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
    from review_decision_costs import verify_checkpoint, checkpoint_bytes
    verify_checkpoint()
    previous=list(csv.DictReader(io.StringIO(gzip.decompress(checkpoint_bytes(HISTORY/'corrected/scenarios.csv.gz')).decode())))
    def scenario_key(r):return tuple(r[k] for k in ('input','words','constrained','uses','bandwidth_mb_s','launch_us','rule'))
    old={scenario_key(r):r for r in previous}
    retained=read(OUT/'accounting-provenance.json')['prediction_timing']=='retained'
    for r in rows:
        prior=old[scenario_key(r)]
        if retained or r['rule']!='model':assert r['chosen']==prior['chosen']
        if retained:assert r['decision_ns']==prior['decision_ns']
        if retained and r['rule']=='model':
            assert r==prior, 'Model totals must remain exactly unchanged.'
    print(f'PASS: {len(native)} retained corrected native preparations, 511 identical invocation inputs, unchanged kernel decisions, 23,040 corrected scenarios and hashes.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','analyze','reaccount','render','check','record','verify'))
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--run-directory',type=Path,default=RUN)
    a=parser.parse_args();OUT=a.output.resolve();RUN=a.run_directory.resolve()
    if OUT==HISTORY:raise ValueError('Cannot overwrite historical artifact.')
    globals()[a.action]()
