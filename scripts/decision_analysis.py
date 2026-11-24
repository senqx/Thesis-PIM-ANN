#!/usr/bin/env python3
"""Frozen decision rules and transparent setup-inclusive scenario accounting."""
import argparse
import json
import math
from pathlib import Path
import statistics
import time
from collections import Counter
from decision_study import OUT, POLICIES, TEST, WORDS, feasible, matrix, dump, write_table

def total(r,k,bw,launch,cycles=None,setup=None):
    """Seconds; metadata installed once, current features/output move each use."""
    return ((r['prepare_ns'] if setup is None else setup)*1e-9+
            r['stored_metadata_bytes']/(bw*1e6)+k*(
            (r['cycles'] if cycles is None else cycles)/350e6+r['refresh_ns']*1e-9+
            (r['rows']+r['columns'])*r['feature_bytes']/(bw*1e6)+launch*1e-6))

def choose(rs,model,k,bw,launch,constrained=True):
    """This function uses structural counters and calibration coefficients only."""
    s=next(r for r in rs if r['policy']=='stream512')
    eligible={r['policy']:r for r in rs if not constrained or feasible(r,s)}
    allrows={r['policy']:r for r in rs}
    prediction={p:sum(c*f for c,f in zip(model['models'][p]['coefficients'],r['model_features'])) for p,r in eligible.items()}
    # All representations were inspected; their one-time preparation is common to
    # the selector's alternatives. Do not charge the chosen preparation twice.
    pmodel=min(eligible,key=lambda p:total(eligible[p],k,bw,launch,cycles=prediction[p],setup=0))
    fixed=model['fixed'] if model['fixed'] in eligible else 'stream512'
    capacity='full' if 'full' in eligible else 'stream512'
    hot=allrows['hot']
    stream_metadata_reads=s['expected_reads']-s['nnz']*s['feature_bytes']
    misses=(hot['expected_reads']-stream_metadata_reads-hot['hot_entries']*hot['feature_bytes'])/hot['feature_bytes']
    fraction=1-misses/s['nnz'] if s['nnz'] else 0
    # Decode measured structural read counters, not test cycles, to estimate batch reuse.
    batch=allrows['batch']
    # Native inspection exposes total source + metadata bytes. A 50% reduction in
    # overall local reads is a conservative, explicit reuse-only threshold.
    reuse=('full' if 'full' in eligible else 'hot' if fraction>=.5 and 'hot' in eligible
           else 'batch' if batch['expected_reads']<=.5*s['expected_reads'] and 'batch' in eligible else 'stream512')
    inspection=sum(r['prepare_ns']+r['inspect_ns'] for r in rs)
    reuse_setup=(allrows['full']['prepare_ns'] if reuse=='full' else
                 sum(allrows[p]['prepare_ns']+allrows[p]['inspect_ns'] for p in ('hot','batch','stream512')))
    fixed_setup=allrows[model['fixed']]['prepare_ns']+allrows[model['fixed']]['inspect_ns']
    if fixed!=model['fixed']:fixed_setup+=s['prepare_ns']
    return dict(model=(pmodel,inspection),fixed=(fixed,fixed_setup),
                capacity=(capacity,allrows[capacity]['prepare_ns']),reuse=(reuse,reuse_setup)),prediction

def input_header(row):
    """Only CSR dimensions/counts and configured residency, known before encoding."""
    return {k: row[k] for k in ('rows', 'columns', 'nnz', 'feature_bytes', 'resident_capacity')}


def stream_reference(header):
    r, z, f = (header[k] for k in ('rows', 'nnz', 'feature_bytes'))
    return dict(stored_metadata_bytes=((4 * (r + 1) + 31) // 32) * 32 + 8 * z,
                expected_reads=8 * r + 8 * z + z * f, expected_writes=r * f)


def header_feasible(policy, header, constrained=True):
    """Exact traffic/metadata tests for the frozen stream/full/hot encoders."""
    m, z, f, c = (header[k] for k in ('columns', 'nnz', 'feature_bytes', 'resident_capacity'))
    if policy in ('stream128', 'stream512'):
        return True
    if policy == 'full':
        return m * f <= c and (not constrained or m <= z)
    if policy == 'hot':
        # The top H frequency counts sum to at least H iff Z >= H.
        return not constrained or z >= min(m, c // f)
    raise ValueError(f'No header-only feasibility proof for {policy}')


def simple_policy(rule, header, fixed, prepare, inspect, constrained=True):
    """Lazy decision path; callbacks construct/inspect only visited encoders.

    The accounting adapter supplies retained encoder costs. A caller may instead
    supply encoder operations. No measured cycles or refresh timings are read.
    Header checks and simple dispatch remain outside the timed interval.
    """
    if rule == 'fixed':
        p = fixed if header_feasible(fixed, header, constrained) else 'stream512'
        return p, prepare(p)
    if rule in ('capacity', 'reuse') and header_feasible('full', header, constrained):
        return 'full', prepare('full')
    if rule == 'capacity':
        return 'stream512', prepare('stream512')
    if rule != 'reuse':
        raise ValueError(rule)
    reference = stream_reference(header)
    z, f = header['nnz'], header['feature_bytes']
    h = min(header['columns'], header['resident_capacity'] // f)
    if z and h and header_feasible('hot', header, constrained):
        plan = prepare('hot')
        # The smallest possible top-H sum occurs with frequencies balanced over
        # M records. If even that sum reaches 50%, the header proves acceptance.
        q, remainder = divmod(z, header['columns'])
        if 2 * (h * q + min(h, remainder)) >= z:
            return 'hot', plan
        counters = inspect('hot', plan)
        misses = (counters['expected_reads'] - 8 * header['rows'] - 8 * z - h * f) / f
        if 1 - misses / z >= .5:
            return 'hot', plan
    plan = prepare('batch')
    counters = inspect('batch', plan)
    if (counters['expected_reads'] <= .5 * reference['expected_reads']
            and (not constrained or feasible(counters, reference))):
        return 'batch', plan
    return 'stream512', prepare('stream512')


def simple_accounting(rs, model, constrained=True):
    by = {r['policy']: r for r in rs}
    header = input_header(by['stream512'])
    decisions, work = {}, {}
    for rule in ('fixed', 'capacity', 'reuse'):
        steps = dict(prepare=[], inspect=[])
        def prepare(p):
            assert p not in steps['prepare'], 'An encoder must not be built twice.'
            steps['prepare'].append(p)
            return by[p]
        def inspect(p, plan):
            steps['inspect'].append(p)
            return plan
        p, _ = simple_policy(rule, header, model['fixed'], prepare, inspect, constrained)
        setup = (sum(by[q]['prepare_ns'] for q in steps['prepare'])
                 + sum(by[q]['inspect_ns'] for q in steps['inspect']))
        decisions[rule] = (p, setup)
        work[rule] = steps
    return decisions, work


def choose_corrected(rs,model,k,bw,launch,constrained=True):
    """Frozen model with direct simple baselines and explicit cost accounting.

    Model scoring receives per-input refresh estimates at no acquisition cost:
    an optimistic assumption, not a measured runtime profiling mechanism.
    """
    s=next(r for r in rs if r['policy']=='stream512')
    eligible={r['policy']:r for r in rs if not constrained or feasible(r,s)}
    prediction={p:sum(c*f for c,f in zip(model['models'][p]['coefficients'],r['model_features'])) for p,r in eligible.items()}
    pmodel=min(eligible,key=lambda p:total(eligible[p],k,bw,launch,cycles=prediction[p],setup=0))
    decisions,_=simple_accounting(rs,model,constrained)
    return dict(model=(pmodel,sum(r['prepare_ns']+r['inspect_ns'] for r in rs)),
                **decisions),prediction


def candidate_work(rs,model,reuse=None,constrained=True):
    """Audit ledger captured from the same lazy paths used by simple policies."""
    decisions,work=simple_accounting(rs,model,constrained)
    if reuse is not None:
        assert reuse==decisions['reuse'][0]
    work['model']=dict(prepare=[r['policy'] for r in rs],inspect=[r['policy'] for r in rs])
    return work


def evaluate(prediction_costs=None):
    if OUT.name!='corrected':
        raise RuntimeError('Preserve historical results: use decision_correction.py analyze.')
    model=json.loads((OUT/'frozen-model.json').read_text())
    rows=json.loads((OUT/'heldout-t8.json').read_text())
    results=[];kernel=[]
    for n in TEST:
        for w in WORDS:
            rs=[r for r in rows if r['input']==n and r['words']==w];by={r['policy']:r for r in rs};s=by['stream512']
            for constraint in (True,False):
                eligible=[r for r in rs if not constraint or feasible(r,s)]
                oracle=min(eligible,key=lambda r:r['cycles'])
                predicted=min(eligible,key=lambda r:sum(c*f for c,f in zip(model['models'][r['policy']]['coefficients'],r['model_features'])))
                kernel.append(dict(input=n,words=w,constrained=constraint,oracle=oracle['policy'],chosen=predicted['policy'],
                    chosen_cycles=predicted['cycles'],best_cycles=oracle['cycles'],
                    regret_pct=100*(predicted['cycles']/oracle['cycles']-1),
                    stream_cycles=s['cycles'],improvement_vs_stream_pct=100*(1-predicted['cycles']/s['cycles'])))
                for k in model['valid_uses']:
                    for bw in model['bandwidth_mb_s']:
                        # Launch is common across methods: scenarios change ratios, not choices.
                        decisions,pred=choose_corrected(rs,model,k,bw,0,constraint)
                        if prediction_costs is None:
                            start=time.perf_counter_ns()
                            for _ in range(31):
                                # Time arithmetic prediction/selection; structural inspection is native and charged separately.
                                prediction={r['policy']:sum(c*f for c,f in zip(model['models'][r['policy']]['coefficients'],r['model_features'])) for r in eligible}
                                chosen=min(eligible,key=lambda r:total(r,k,bw,0,cycles=prediction[r['policy']],setup=0))
                            predict_ns=(time.perf_counter_ns()-start)/31
                            assert chosen['policy']==decisions['model'][0]
                        else:
                            # The predictor arithmetic is unchanged; reuse its exact retained
                            # measurement so this accounting revision introduces no new timing.
                            predict_ns=prediction_costs[(n,w,constraint,k,bw)]
                        for launch in model['launch_us']:
                            oracle=min(eligible,key=lambda r:total(r,k,bw,launch));best=total(oracle,k,bw,launch)
                            for rule,(p,setup) in decisions.items():
                                decision_time=predict_ns if rule=='model' else 0
                                elapsed=total(by[p],k,bw,launch,setup=setup+decision_time)
                                results.append(dict(input=n,words=w,constrained=constraint,uses=k,bandwidth_mb_s=bw,
                                    launch_us=launch,rule=rule,chosen=p,oracle=oracle['policy'],
                                    total_seconds=elapsed,oracle_seconds=best,regret_pct=100*(elapsed/best-1),
                                    saving_vs_stream_pct=100*(1-elapsed/total(s,k,bw,launch)),
                                    setup_ns=setup,decision_ns=decision_time,budget_pass=feasible(by[p],s)))
    import csv,gzip,io
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    (OUT/'scenarios.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))
    write_table(OUT/'decisions.csv',[r for r in results if r['bandwidth_mb_s']==80 and r['launch_us']==0])
    write_table(OUT/'kernel-decisions.csv',kernel)
    summary={}
    for rule in ('model','fixed','capacity','reuse'):
        group=[r for r in results if r['constrained'] and r['bandwidth_mb_s']==80 and r['launch_us']==0 and r['rule']==rule]
        summary[rule]={str(k):dict(mean_regret_pct=statistics.mean(r['regret_pct'] for r in group if r['uses']==k),
            worst_regret_pct=max(r['regret_pct'] for r in group if r['uses']==k),
            mean_saving_vs_stream_pct=statistics.mean(r['saving_vs_stream_pct'] for r in group if r['uses']==k),
            right_choices=sum(r['chosen']==r['oracle'] for r in group if r['uses']==k),conditions=24)
            for k in model['valid_uses']}
    summary['kernel']={str(c):dict(mean_regret_pct=statistics.mean(r['regret_pct'] for r in kernel if r['constrained']==c),
          worst_regret_pct=max(r['regret_pct'] for r in kernel if r['constrained']==c),
          right_choices=sum(r['chosen_cycles']==r['best_cycles'] for r in kernel if r['constrained']==c),conditions=24) for c in (True,False)}
    train=json.loads((OUT/'calibration-t8.json').read_text())
    summary['calibration']={'simulated_cycles':sum(r['cycles'] for r in train),
        'modelled_serial_seconds_at_80MB_s':sum(total(r,1,80,0,setup=r['prepare_ns']+r['inspect_ns']) for r in train),
        'fit_seconds':model.get('fit_seconds'),
        'note':'Includes native preparation and structural inspection. One-time calibration excluded from deployed-rule totals; add this and original fit time for a cold deployment. The fixed rule also uses calibration; capacity/reuse do not.'}
    dump(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2))

def figures():
    import sys
    from decision_study import ROOT
    sys.path.insert(0,str(ROOT/'.deps/thesis-pdf'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from datetime import datetime,timezone
    from decision_study import table
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    plotted=[]
    def save(fig,name):
        fig.savefig(OUT/f'{name}.png',dpi=220)
        stamp=datetime(2026,11,24,tzinfo=timezone.utc)
        fig.savefig(OUT/f'{name}.pdf',metadata={'CreationDate':stamp,'ModDate':stamp})
        plt.close(fig)
    colors={'stream128':'#78909c','stream512':'#263238','hot':'#16817a','full':'#4575b4','batch':'#d9822b','bcsr2':'#9352a3','bcsr4':'#cb4b63'}
    controlled=json.loads((OUT/'controlled-t8.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(7,3.3),constrained_layout=True)
    for ax,kind in zip(axes,('uniform','clustered')):
        for p in POLICIES:
            rs=sorted([r for r in controlled if r['input'].startswith(kind) and r['policy']==p],key=lambda r:r['columns'])
            x=[];y=[]
            for r in rs:
                s=next(v for v in controlled if v['input']==r['input'] and v['policy']=='stream512')
                x.append(r['columns']*8/r['resident_capacity']);y.append(r['cycles']/s['cycles'])
            # Full residency is infeasible at two sizes; show only measured feasible points.
            ax.plot(x,y,'o-',label=p,color=colors[p],markersize=4)
            plotted.append(dict(figure='capacity',panel=kind,policy=p,x=x,y=y,keys=[r['key'] for r in rs]))
        ax.axhline(1,color='gray',lw=.7);ax.axvline(1,color='gray',lw=.7,ls=':')
        ax.set(xscale='log',xticks=[.25,.5,1,2,4],xticklabels=['0.25','0.5','1','2','4'],
               xlabel='Source bytes / configured resident capacity',ylabel='Cycles / stream512',title=kind.capitalize())
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside upper center',fontsize=7,ncol=4);save(fig,'capacity')
    held=json.loads((OUT/'heldout-t8.json').read_text())
    fig,axes=plt.subplots(2,2,figsize=(7,5.5),constrained_layout=True)
    for ax,n in zip(axes.flat,TEST):
        for p in POLICIES:
            rs=sorted([r for r in held if r['input']==n and r['policy']==p and r['words']>1],key=lambda r:r['words'])
            y=[r['cycles']/next(v['cycles'] for v in held if v['input']==n and v['words']==r['words'] and v['policy']=='stream512') for r in rs]
            ax.plot([r['feature_bytes'] for r in rs],y,'o-',color=colors[p],label=p,markersize=3)
            plotted.append(dict(figure='widths',panel=n,policy=p,x=[r['feature_bytes'] for r in rs],y=y,keys=[r['key'] for r in rs]))
        ax.set(xscale='log',xticks=[8,16,32,64,128],xticklabels=['8','16','32','64','128'],title=n,
               xlabel='Feature record bytes',ylabel='Cycles / stream512');ax.axhline(1,color='gray',lw=.7)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside upper center',fontsize=7,ncol=4);save(fig,'widths')
    summary=json.loads((OUT/'summary.json').read_text());fig,ax=plt.subplots(figsize=(7,3.8),constrained_layout=True)
    for rule in ('model','fixed','capacity','reuse'):
        data=summary[rule];ks=sorted(int(k) for k in data)
        ax.plot(ks,[data[str(k)]['mean_regret_pct'] for k in ks],'o-',label=rule)
        plotted.append(dict(figure='decision-cost',policy=rule,x=ks,y=[data[str(k)]['mean_regret_pct'] for k in ks],kind='modelled'))
    ax.set(xscale='log',yscale='log',xlabel='Valid uses of the prepared structure (modelled)',ylabel='Mean excess time over feasible oracle (%)')
    ax.set_xticks(ks,labels=[str(k) for k in ks]);ax.set_yticks([1,2,5,10,20,50,100],labels=['1','2','5','10','20','50','100'])
    ax.legend();save(fig,'decision-cost')
    dump(OUT/'plotted-data.json',plotted)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('evaluate','figures'));a=p.parse_args()
    evaluate() if a.action=='evaluate' else figures()
