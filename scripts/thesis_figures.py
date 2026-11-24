#!/usr/bin/env python3
"""Generate thesis evidence plots and explanatory architecture/method diagrams."""
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
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import NullFormatter


def read(name):
    with (DATA/name).open() as f:return list(csv.DictReader(f))


def save_figure(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=220)
    stamp=datetime(2026,11,23,tzinfo=timezone.utc)
    fig.savefig(OUT/f'{name}.pdf',metadata={'CreationDate':stamp,'ModDate':stamp})


def explanatory_figures():
    """Schematics explain boundaries; their positions are not measured data."""
    blue,green,grey='#e8f1f7','#e8f4ee','#536875'
    def box(ax,x,y,w,h,title,body,face):
        ax.add_patch(FancyBboxPatch((x,y),w,h,
                     boxstyle='round,pad=0.012,rounding_size=0.025',
                     facecolor=face,edgecolor='#8da9bb',linewidth=.9))
        ax.text(x+w/2,y+h*.73,title,ha='center',va='center',
                fontsize=9.5,weight='bold',color='#16374b')
        ax.text(x+w/2,y+h*.34,body,ha='center',va='center',
                fontsize=8.5,linespacing=1.4,color='#202b33')
    def arrow(ax,start,end,both=False):
        ax.annotate('',xy=end,xytext=start,arrowprops=dict(
                    arrowstyle='<->' if both else '->',color=grey,lw=1.2))

    fig,ax=plt.subplots(figsize=(6.6,3.5));ax.set_axis_off()
    ax.set(xlim=(0,1),ylim=(0,1))
    box(ax,.02,.42,.25,.37,'Host CPU','Prepare work\nInstall inputs\nRetrieve results',blue)
    ax.add_patch(FancyBboxPatch((.40,.07),.57,.83,boxstyle='round,pad=.01',
                 facecolor='#f7f9fa',edgecolor='#9cacb5',linestyle='--'))
    ax.text(.685,.94,'One DPU and its local memory',ha='center',fontsize=10,
            weight='bold',color='#16374b')
    box(ax,.45,.49,.22,.31,'MRAM','64 MiB\nSource table + IDs',blue)
    box(ax,.73,.49,.20,.31,'WRAM','64 KiB total\nData + other state',green)
    box(ax,.61,.12,.32,.23,'DPU execution','Tasklets + registers',green)
    arrow(ax,(.275,.62),(.438,.62),True)
    ax.text(.35,.37,'Host–DPU\ntransfers',ha='center',fontsize=8,color=grey)
    arrow(ax,(.68,.63),(.718,.63),True)
    ax.text(.698,.44,'Local DMA',ha='center',fontsize=8,color=grey)
    arrow(ax,(.83,.475),(.83,.365),True)
    ax.text(.18,.18,'Separate boundaries:\nlocal savings need not\nreduce host traffic.',
            ha='center',va='center',fontsize=8.5,color=grey)
    fig.tight_layout(pad=.6);save_figure(fig,'architecture');plt.close(fig)

    fig,ax=plt.subplots(figsize=(6.6,3.4));ax.set_axis_off()
    ax.set(xlim=(0,1),ylim=(0,1))
    box(ax,.02,.59,.43,.32,'1. Observe the work',
        'Size, reuse, width, lifetime\nCharge inspection cost',blue)
    box(ax,.55,.59,.43,.32,'2. Check feasible choices',
        'WRAM, installed bytes, traffic\nKeep streaming as a candidate',blue)
    box(ax,.55,.08,.43,.32,'3. Compare accounted costs',
        'Setup + installation + valid uses\nAccount for refresh and uncertainty',green)
    box(ax,.02,.08,.43,.32,'4. Test the recommendation',
        'Freeze model; use held-out inputs\nReport wrong choices and their cost',green)
    arrow(ax,(.47,.75),(.53,.75))
    arrow(ax,(.765,.56),(.765,.43))
    arrow(ax,(.53,.24),(.47,.24))
    ax.text(.22,.48,'Evaluated process',ha='center',va='center',
            fontsize=9,color=grey,style='italic')
    fig.tight_layout(pad=.6);save_figure(fig,'decision');plt.close(fig)


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
    explanatory_figures()
    (OUT/'plotted-data.json').write_text(json.dumps(plotted,indent=2)+'\n')
    assert len(plotted)==12 and all(len(s['x'])==5 for s in plotted)
    print('Generated two data figures: all 12 series contain five points; plus three explanatory diagrams.')


if __name__=='__main__':build()
