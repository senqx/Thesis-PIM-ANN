#!/usr/bin/env python3
"""Generate short-thesis figures directly from the five-point evidence."""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'experiments/access-plan-fivepoint'
OUT=ROOT/'thesis/figures'
SIZES=(192,384,768,1536,3072)
CASES=(('community','Community','#2471a3'),('grqc','Sampled ca-GrQc','#16876c'),
       ('uniform','Uniform','#bd6617'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/thesis-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter


def read(name):
    with (DATA/name).open() as f:return list(csv.DictReader(f))


def save_figure(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=220)
    stamp=datetime(2026,11,23,tzinfo=timezone.utc)
    fig.savefig(OUT/f'{name}.pdf',metadata={'CreationDate':stamp,'ModDate':stamp})


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    paired=read('paired.csv')
    rows=read('results.csv')+read('controls.csv')
    lut={r['key']:r for r in rows}
    plt.rcParams.update({'font.size':8.5,'axes.titlesize':10,'legend.fontsize':8,
                         'axes.spines.top':False,'axes.spines.right':False})
    plotted=[]
    def line(ax,x,groups,label,color,name):
        assert len(x)==len(groups)==5
        ys=[statistics.mean(g) for g in groups]
        ax.plot(x,ys,'o-',label=label,color=color,linewidth=1.5,markersize=4)
        ax.fill_between(x,[min(g) for g in groups],[max(g) for g in groups],color=color,alpha=.12)
        plotted.append(dict(figure=name,series=label,x=list(x),mean=ys,seed_values=groups))
    def finish(fig,axes,name,xvalues=SIZES):
        for ax in axes:
            ax.set_xscale('log');ax.set_xticks(xvalues)
            ax.set_xticklabels([f'{n:,}' for n in xvalues],fontsize=7.5)
            ax.xaxis.set_minor_formatter(NullFormatter());ax.grid(alpha=.18)
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False)
        fig.tight_layout(rect=(0,0,1,.91))
        save_figure(fig,name)
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(6.6,3.1))
    for case,label,color in CASES:
        for ax,field in zip(axes,('cycle_change_percent','read_change_percent')):
            groups=[[float(r[field]) for r in paired if r['case']==case and r['destinations']==str(n)
                     and r['policy']=='batch64'] for n in SIZES]
            assert all(len(g)==2 for g in groups)
            line(ax,SIZES,groups,label,color,'performance-'+field)
    for ax,title in zip(axes,('Complete DPU kernel cycles','Local MRAM read bytes')):
        ax.axhline(0,color='black',linewidth=.8)
        ax.set(title=title,xlabel='Destinations per invocation',ylabel='Change vs streaming (%)')
    finish(fig,axes,'performance')

    fig,axes=plt.subplots(1,2,figsize=(6.6,3.2))
    uses=(1,10,100,1000,10000)
    for case,label,color in CASES:
        groups=[[int(r['preparation_median_ns'])/1e6 for r in rows if r['case']==case
                 and r['destinations']==str(n) and r['policy']=='batch64'] for n in SIZES]
        line(axes[0],SIZES,groups,label,color,'cost-preparation')
        group=[]
        for k in uses:
            points=[]
            for p in paired:
                if p['case']!=case or p['destinations']!='3072' or p['policy']!='batch64':continue
                r=lut[p['key']]
                b=lut[f'{case}-s{r["seed"]}-n3072-{p["comparator"]}']
                baseline=int(b['preparation_median_ns'])+k*int(b['cycles'])/.35
                difference=float(p['extra_preparation_ns'])-k*float(p['saved_kernel_ns'])
                points.append(100*difference/baseline)
            group.append(points)
        line(axes[1],uses,group,label,color,'cost-reuse')
    axes[0].set(yscale='log',title='CPU preparation for batch64',
                xlabel='Destinations per invocation',ylabel='Construction time (ms)')
    axes[1].set(title='Accounted total at 3,072 destinations',
                xlabel='Valid uses of the same plan',ylabel='Change vs streaming (%)')
    axes[1].set_yscale('symlog',linthresh=10)
    axes[1].axhline(0,color='black',linewidth=.8)
    for ax,x in zip(axes,(SIZES,uses)):
        ax.set_xscale('log'); ax.set_xticks(x)
        ax.set_xticklabels([f'{n:,}' for n in x],fontsize=7.5)
        ax.xaxis.set_minor_formatter(NullFormatter());ax.grid(alpha=.18)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,0,1,.91));save_figure(fig,'costs');plt.close(fig)

    fig,ax=plt.subplots(figsize=(6.6,1.5));ax.set_axis_off()
    boxes=[(.01,'CPU prepares once','IDs: 7, 12, 7, 4\nunique: 7, 12, 4\nslots: 0, 1, 0, 2'),
           (.36,'DPU loads current values','MRAM → WRAM\nread each unique ID once'),
           (.71,'DPU follows slot order','x[7] + x[12]\n+ x[7] + x[4]')]
    for x,title,body in boxes:
        ax.text(x+.135,.75,title,ha='center',weight='bold',fontsize=9)
        ax.text(x+.135,.36,body,ha='center',va='center',fontsize=9,
                bbox=dict(boxstyle='round,pad=.55',facecolor='#edf3f7',edgecolor='#8da9bb'))
    for left,right in ((.30,.345),(.65,.70)):
        ax.annotate('',xy=(right,.40),xytext=(left,.40),arrowprops=dict(arrowstyle='->',color='#455a64'))
    fig.tight_layout(pad=.4);save_figure(fig,'method');plt.close(fig)
    (OUT/'plotted-data.json').write_text(json.dumps(plotted,indent=2)+'\n')
    assert len(plotted)==12 and all(len(s['x'])==5 for s in plotted)
    print('Generated two data figures: all 12 series contain five points; plus the method diagram.')


if __name__=='__main__':build()
