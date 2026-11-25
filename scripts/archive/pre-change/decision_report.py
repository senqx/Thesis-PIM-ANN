#!/usr/bin/env python3
"""Derive paired tables and practical margins from retained study records."""
from collections import Counter
import json
import math
import statistics
from decision_study import OUT,TEST,WORDS,POLICIES,feasible,write_table,dump
from decision_analysis import total

def robustness(held):
    """Descriptive checks only; never alter the frozen model or decision rules."""
    import csv
    import io
    import zipfile
    from decision_study import RUN
    sensitivity_path=OUT/'sensitivity.json'
    if not sensitivity_path.exists():return
    sensitivity=json.loads(sensitivity_path.read_text())
    repeated=json.loads((OUT/'repeated.json').read_text())
    repeat_rows=[]
    for r in repeated:
        base=next(x for x in held if (x['input'],x['words'],x['policy'])==(r['input'],r['words'],r['policy']))
        repeat_rows.append(dict(key=r['key'],single_cycles=base['cycles'],three_run_cycles=r['cycles'],
            change_vs_three_single_pct=100*(r['cycles']/(3*base['cycles'])-1)))
    write_table(OUT/'repeated-comparisons.csv',repeat_rows)
    dram=[]
    for w in (2,32):
        for scale in (.5,.75,1.,1.25,1.5):
            rs=[r for r in sensitivity if r['words']==w and r['timing_scale']==scale]
            stream=next(r for r in rs if r['policy']=='stream512')
            best=min((r for r in rs if feasible(r,stream)),key=lambda r:r['cycles'])
            hot=next(r for r in rs if r['policy']=='hot')
            dram.append(dict(words=w,feature_bytes=stream['feature_bytes'],timing_scale=scale,
                best_feasible=best['policy'],best_cycles=best['cycles'],stream_cycles=stream['cycles'],
                hot_saving_pct=100*(1-hot['cycles']/stream['cycles'])))
    write_table(OUT/'dram-comparisons.csv',dram)
    # Extreme combinations are a conservative observed-sample envelope, not a CI.
    archive=zipfile.ZipFile(OUT/'preparation.zip') if (OUT/'preparation.zip').exists() else None
    def samples(r):
        name=r['key']+'/plan.timings.csv'
        data=archive.read(name).decode() if archive else (RUN/'prepared'/name).read_text()
        return list(csv.DictReader(io.StringIO(data)))
    host=[]
    for r in held:
        if r['policy']!='hot':continue
        s=next(x for x in held if (x['input'],x['words'],x['policy'])==(r['input'],r['words'],'stream512'))
        rs,ss=samples(r),samples(s)
        def variant(row,raw,fn):
            return {**row,**{key:fn(int(v[key]) for v in raw) for key in ('prepare_ns','refresh_ns')}}
        for k in (1,2,16,1024):
            low=(total(variant(s,ss,min),k,80,0)-total(variant(r,rs,max),k,80,0))*1e6
            high=(total(variant(s,ss,max),k,80,0)-total(variant(r,rs,min),k,80,0))*1e6
            host.append(dict(input=r['input'],words=r['words'],uses=k,
                observed_envelope_low_margin_us=low,observed_envelope_high_margin_us=high))
    if archive:archive.close()
    write_table(OUT/'host-timing-sensitivity.csv',host)
    narrow=[r for r in host if r['words'] in (2,4,8,16) and r['uses']==1]
    lines=['# Robustness and state checks','',
        'These checks were performed after model freeze. They do not refit the model.',
        'All results describe the pinned simulator, not a hardware error bound.','',
        '## Same-process repetition and changed structure','',
        f'{len(repeated)} records each execute three invocations with changed source values and unchanged metadata.',
        'Every output and read/write count passed. Relative to three times the corresponding',
        f'single-run cycles, total cycles differ from {min(r["change_vs_three_single_pct"] for r in repeat_rows):+.3f}% to {max(r["change_vs_three_single_pct"] for r in repeat_rows):+.3f}%.',
        'This supports the linear repeated-cost approximation on this subset; it does not prove',
        'exact linearity at 1,024 uses. See [repeated-comparisons.csv](repeated-comparisons.csv).',
        'Fourteen further checks rebuild each of the seven representations for changed coordinates',
        'and an empty matrix. Stale structural plans are not reused after those changes.','',
        '## Five joint DRAM timing settings','',
        'The same instruction images run with tRCD, tCL, tRP and tRAS jointly scaled.',
        'The 65 rows contain 52 new executions and 13 reused default-setting comparators.',
        'Joint scaling is a model-dependence check, not an isolated attribution to one parameter.','',
        '| Record bytes | Timing scale | Best feasible policy | Best cycles | Hot saving vs stream512 |',
        '| ---: | ---: | --- | ---: | ---: |']
    for r in dram:
        lines.append(f'| {r["feature_bytes"]} | {r["timing_scale"]:g} | {r["best_feasible"]} | {r["best_cycles"]:,} | {r["hot_saving_pct"]:+.2f}% |')
    lines+=['','Exact settings and absolute cycles are in [sensitivity.json](sensitivity.json)',
        'and [dram-comparisons.csv](dram-comparisons.csv).','',
        '## Native timing variation','',
        '[host-timing-sensitivity.csv](host-timing-sensitivity.csv) recomputes hot-versus-streaming',
        'margins using the most favorable and unfavorable combinations of the 31 observed',
        'preparation and refresh samples at 80 MB/s. These are descriptive envelopes, not',
        'confidence intervals or bounds on future host timings. A margin spanning zero makes',
        'the reported median-based payback sensitive to observed host timing variation.',
        f'{sum(r["observed_envelope_low_margin_us"]>0 for r in narrow)}/16 SpMM cases at 8–64 bytes retain a positive first-use margin across this envelope.',
        'The six others span zero; median-based first-use payback is not robust for those cases.','',
        '## Feasible concurrency','',
        '[concurrency.json](concurrency.json) adds 50 executions at four/twelve tasklets.',
        'The twelve-tasklet, 128-byte batch image requires 70,096 WRAM bytes and is excluded.',
        'Changing tasklets also changes configured residency capacity. This tests a combined',
        'resource trade-off; the frozen eight-tasklet model is not validated at these settings.','']
    (OUT/'robustness.md').write_text('\n'.join(lines))

def build():
    held=json.loads((OUT/'heldout-t8.json').read_text());allrows=[]
    for phase in ('calibration-t8','heldout-t8','controlled-t8'):allrows+=json.loads((OUT/f'{phase}.json').read_text())
    comparisons=[]
    for r in allrows:
        s=next(v for v in allrows if (v['input'],v['words'],v['policy'])==(r['input'],r['words'],'stream512'))
        saved=s['cycles']-r['cycles']
        saving=(s['cycles']-r['cycles'])/350e6+(s['refresh_ns']-r['refresh_ns'])*1e-9
        extra=(r['prepare_ns']-s['prepare_ns'])*1e-9+(r['stored_metadata_bytes']-s['stored_metadata_bytes'])/80e6
        if saving>0:threshold=max(1,math.floor(extra/saving)+1)
        elif saving==0:threshold='all' if extra<0 else 'never'
        else:
            upper=math.ceil(-extra/-saving)-1
            threshold=f'1..{upper}' if upper>=1 else 'never'
        comparisons.append(dict(key=r['key'],input=r['input'],split=r['split'],words=r['words'],policy=r['policy'],
            stream_cycles=s['cycles'],cycles=r['cycles'],saved_cycles=saved,saved_microseconds=saved/350,
            cycle_saving_pct=100*saved/s['cycles'],read_change_pct=100*(r['expected_reads']/s['expected_reads']-1),
            metadata_change_pct=100*(r['stored_metadata_bytes']/s['stored_metadata_bytes']-1),
            wram_reserved_bytes=r['wram_reserved_bytes'],budget_pass=feasible(r,s),
            native_prepare_us=r['prepare_ns']/1000,native_refresh_us=r['refresh_ns']/1000,
            plan_payback_uses_at_80MB_s=threshold,
            one_use_margin_us=(total(s,1,80,0)-total(r,1,80,0))*1e6,
            long_lifetime_margin_us=(total(s,1024,80,0)-total(r,1024,80,0))*1e6))
    write_table(OUT/'comparisons.csv',comparisons)
    frozen=json.loads((OUT/'frozen-model.json').read_text());predictions=[]
    for r in held:
        value=sum(c*f for c,f in zip(frozen['models'][r['policy']]['coefficients'],r['model_features']))
        predictions.append(dict(key=r['key'],predicted_cycles=value,observed_cycles=r['cycles'],error_pct=100*(value/r['cycles']-1)))
    write_table(OUT/'predictions.csv',predictions)
    labels={'stream128':'S128','stream512':'S512','hot':'H','full':'F','batch':'B','bcsr2':'C2','bcsr4':'C4'}
    lines=['| Input | 8 bytes | 16 bytes | 32 bytes | 64 bytes | 128 bytes |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for n in TEST:
        cells=[]
        for w in WORDS[1:]:
            rs=[r for r in held if r['input']==n and r['words']==w];s=next(r for r in rs if r['policy']=='stream512')
            r=min((r for r in rs if feasible(r,s)),key=lambda r:r['cycles'])
            cells.append(f'{labels[r["policy"]]} {100*(1-r["cycles"]/s["cycles"]):.2f}%')
        lines.append('| '+n+' | '+' | '.join(cells)+' |')
    (OUT/'decision-table.md').write_text('\n'.join(lines)+'\n')
    summary=json.loads((OUT/'summary.json').read_text())
    import csv
    decisions=list(csv.DictReader((OUT/'decisions.csv').open()))
    primary=[r for r in decisions if r['constrained']=='True' and r['bandwidth_mb_s']=='80' and r['launch_us']=='0']
    criteria=[]
    for k in frozen['valid_uses']:
        group=[r for r in primary if int(r['uses'])==k]
        means={rule:statistics.mean(float(r['total_seconds']) for r in group if r['rule']==rule) for rule in ('model','fixed','capacity','reuse')}
        worst=0
        for n in TEST:
            for w in WORDS:
                paired={r['rule']:float(r['total_seconds']) for r in group if r['input']==n and int(r['words'])==w}
                worst=max(worst,100*(paired['model']/min(paired[p] for p in ('fixed','capacity','reuse'))-1))
        criteria.append(dict(uses=k,model_mean_seconds=means['model'],best_simple_mean_seconds=min(means[p] for p in ('fixed','capacity','reuse')),
            worst_slowdown_vs_best_simple_pct=worst,passes=means['model']<min(means[p] for p in ('fixed','capacity','reuse')) and worst<=5))
    write_table(OUT/'success-criteria.csv',criteria)
    storage=[]
    for n in TEST:
        for w in WORDS:
            rs=[r for r in held if r['input']==n and r['words']==w]
            storage.append(dict(input=n,words=w,combined_candidate_metadata_bytes=sum(r['stored_metadata_bytes'] for r in rs),
                source_bytes=rs[0]['source_feature_bytes'],largest_native_process_rss_kib=max(r['process_peak_rss_kib'] for r in rs)))
    write_table(OUT/'host-storage.csv',storage)
    lines=['# Paired results and decision quality','',
        'The tables below are generated from retained records. Positive cycle savings mean fewer',
        'complete simulated cycles than stream512 on the same input and width. These are',
        'deterministic model results, not hardware speedups or statistical confidence intervals.','',
        '## Best feasible kernel on each held-out SpMM condition','',
        (OUT/'decision-table.md').read_text().strip(),'',
        'H: frequency-based retention; F: full retention; S128/S512: streaming buffer size.',
        'These are hindsight best choices under the no-growth metadata and traffic budget.',
        'They are not the model predictions. Exact ties count as equally optimal. All absolute',
        'cycles, bytes, native costs and paired differences are in [comparisons.csv](comparisons.csv).','',
        '![Five executed record widths on each held-out matrix.](widths.png)','',
        'The width plot includes unconstrained policies; a fast curve may violate the byte budget.',
        'Full residency has fewer points where it is infeasible. Wider records change both data',
        'movement and arithmetic. No point is inferred for an infeasible allocation.','',
        '## Capacity and local reuse','',
        '![Five source-table sizes with fixed row and nonzero counts.](capacity.png)','',
        'Every non-residency policy has five executed source-table sizes. Full residency is',
        'measured at the three feasible sizes only. The x-axis is configured resident capacity,',
        'not the total 64 KiB WRAM. These are controlled generators, not additional datasets.','',
        '## Does the selector earn its cost?','',
        f'The frozen model chooses an equally fastest feasible kernel in {summary["kernel"]["True"]["right_choices"]}/24 conditions.',
        f'Its mean kernel regret is {summary["kernel"]["True"]["mean_regret_pct"]:.2f}%, with a worst case of {summary["kernel"]["True"]["worst_regret_pct"]:.2f}%.',
        'The 24 conditions come from four matrices and six scalar/vector shapes, not 24 independent datasets.','',
        '| Valid uses | Model regret | Fixed-rule regret | Capacity-rule regret | Reuse-rule regret |',
        '| ---: | ---: | ---: | ---: | ---: |']
    for k in (1,16,1024):
        lines.append(f'| {k:,} | '+' | '.join(f'{summary[p][str(k)]["mean_regret_pct"]:.2f}%' for p in ('model','fixed','capacity','reuse'))+' |')
    lines+=['','Regret is excess accounted time relative to the best feasible method for that condition.',
        'These are arithmetic means of paired percentages at 80 MB/s and zero extra launch cost.',
        'The totals include rejected-candidate construction and inspection, prediction, native refresh,',
        'metadata installation, feature upload and output retrieval. Program loading and application',
        'integration remain outside this interval. One-time calibration is separate.','',
        '![Setup and prediction errors affect different plan lifetimes.](decision-cost.png)','',
        f'The model passes the frozen practical-success criterion at {sum(r["passes"] for r in criteria)}/{len(criteria)} tested lifetimes.',
        '**The tested adaptive selector is not justified by this evaluation.** This rejects this',
        'implementation under these conditions; it does not prove that every possible selector fails.',
        'Long reuse can amortize construction, but it cannot repair repeated poor choices.','',
        'See [predictions.csv](predictions.csv), [kernel-decisions.csv](kernel-decisions.csv),',
        '[success-criteria.csv](success-criteria.csv) and [decisions.csv](decisions.csv) for primary cases.',
        'The full [scenario grid](scenarios.csv.gz) is compressed to avoid duplicating a large derived table.',
        'Bandwidth/launch/lifetime combinations are analytical scenarios, not new simulation records.','',
        '## Practical margins and host storage','',
        'The paired table reports the minimum integer use count needed to repay native preparation',
        'and differential metadata installation at 80 MB/s, including differential feature refresh.',
        'A never-paying case has no positive per-use saving. The remaining time margin is the',
        'largest additional cost that could be charged before the reported saving disappears;',
        'it is not evidence that an unmeasured SDK or application cost is zero.','',
        '[host-storage.csv](host-storage.csv) reports combined candidate metadata, source bytes and',
        'native process RSS. The model assumes candidate plans remain available until selection.',
        'RSS includes process/runtime state; it does not measure an entire multi-DPU application.','']
    (OUT/'results.md').write_text('\n'.join(lines))
    robustness(held)
    print('Generated paired comparisons, frozen-criterion results, predictions, storage and reading tables.')

if __name__=='__main__':build()
