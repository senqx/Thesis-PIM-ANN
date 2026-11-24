#!/usr/bin/env python3
"""Build the thesis draft from its readable Markdown source and retained data."""
import csv
from html import escape
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps/thesis-pdf'))
import mistune
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,
                               Image,KeepTogether,Preformatted,PageBreak)

THESIS=ROOT/'thesis'
SOURCE=THESIS/'short-thesis.md'
PDF=THESIS/'short-thesis.pdf'
WIDTH=A4[0]-40*mm
TITLE='When Is WRAM Reuse Worth It?'
RESEARCH_DATE='24 November 2026'


def register_fonts():
    files=[]
    for family,path,prefix in (
        ('Body',Path('/usr/share/fonts/liberation-serif'),'LiberationSerif'),
        ('Sans',Path('/usr/share/fonts/gnu-free'),'FreeSans')):
        for suffix,style in (('','Regular'),('-Bold','Bold'),('-Italic','Italic'),('-BoldItalic','BoldItalic')):
            if family=='Sans':
                tail={'Regular':'','Bold':'Bold','Italic':'Oblique','BoldItalic':'BoldOblique'}[style]
                file=path/f'{prefix}{tail}.ttf'
            else:file=path/f'{prefix}-{style}.ttf'
            pdfmetrics.registerFont(TTFont(family+suffix,str(file)));files.append(file)
        pdfmetrics.registerFontFamily(family,normal=family,bold=family+'-Bold',
                                      italic=family+'-Italic',boldItalic=family+'-BoldItalic')
    file=Path('/usr/share/fonts/liberation-mono/LiberationMono-Regular.ttf')
    pdfmetrics.registerFont(TTFont('Mono',str(file)));files.append(file)
    return files


def refresh_table():
    with (ROOT/'experiments/access-plan-fivepoint/paired.csv').open() as f:rows=list(csv.DictReader(f))
    from statistics import mean
    lines=['| Destinations | Community | Sampled ca-GrQc | Uniform |','| ---: | ---: | ---: | ---: |']
    for n in (192,384,768,1536,3072):
        values=[]
        for c in ('community','grqc','uniform'):
            vals=[float(r['cycle_change_percent']) for r in rows if r['case']==c
                  and r['destinations']==str(n) and r['policy']=='batch64']
            assert len(vals)==2
            values.append(f'{mean(vals):+.2f}%'.replace('-','−'))
        lines.append(f'| {n:,} | '+ ' | '.join(values)+' |')
    text=SOURCE.read_text()
    text,count=re.subn(r'(?s)(<!-- begin:cycle-table -->\n).*?(\n<!-- end:cycle-table -->)',
                      lambda m:m[1]+'\n'.join(lines)+m[2],text)
    assert count==1
    with (ROOT/'experiments/baseline-gates/comparisons.csv').open() as f:
        controls=list(csv.DictReader(f))
    lines=['| Input | Control | Saved cycles | Cycle change | Local reads | Indices |',
           '| --- | --- | ---: | ---: | ---: | ---: |']
    for case,label,policies in (
            ('community','Community',('compact64','preload128')),
            ('grqc','Sampled ca-GrQc',('compact64',)),
            ('uniform','Uniform',('compact64','preload128'))):
        for policy in policies:
            paired=[r for r in controls if r['case']==case and r['policy']==policy]
            assert len(paired)==2
            fields=('cycle_change_vs_stream_pct','read_change_vs_stream_pct',
                    'installed_metadata_change_vs_stream_pct')
            values=[f'{mean(float(r[k]) for r in paired):+.2f}%'.replace('-','−') for k in fields]
            saved=f'{mean(float(r["saved_cycles_vs_stream"]) for r in paired):,.1f}'.replace('-','−')
            name='Compact batch' if policy=='compact64' else 'Shared preload'
            lines.append(f'| {label} | {name} | {saved} | '+' | '.join(values)+' |')
    text,count=re.subn(r'(?s)(<!-- begin:control-table -->\n).*?(<!-- end:control-table -->)',
                      lambda m:m[1]+'\n'.join(lines)+'\n'+m[2],text)
    assert count==1
    decision=ROOT/'experiments/decision-study'
    if (decision/'decision-table.md').exists():
        new_table=(decision/'decision-table.md').read_text().rstrip()
        text,count=re.subn(r'(?s)(<!-- begin:decision-table -->\n).*?(<!-- end:decision-table -->)',
                          lambda m:m[1]+new_table+'\n'+m[2],text)
        assert count==1
        summary=json.loads((decision/'summary.json').read_text())
        lines=['| Valid uses | Model | Fixed rule | Capacity-first | Reuse-only |',
               '| ---: | ---: | ---: | ---: | ---: |']
        for k in (1,16,1024):
            lines.append(f'| {k:,} | '+' | '.join(f'{summary[p][str(k)]["mean_regret_pct"]:.2f}%'
                         for p in ('model','fixed','capacity','reuse'))+' |')
        text,count=re.subn(r'(?s)(<!-- begin:regret-table -->\n).*?(<!-- end:regret-table -->)',
                          lambda m:m[1]+'\n'.join(lines)+'\n'+m[2],text)
        assert count==1
    SOURCE.write_text(text)


def pdf_link(url):
    """Repository links must remain usable when the PDF is downloaded alone."""
    if urlsplit(url).scheme or url.startswith('#'):
        return url
    path,sep,anchor=url.partition('#')
    target=(THESIS/path).resolve()
    assert target.exists(),url
    relative=target.relative_to(ROOT)
    return 'https://github.com/senqx/Thesis-PIM-ANN/blob/main/'+str(relative)+(sep+anchor if sep else '')


def inline(nodes):
    parts=[]
    for n in nodes:
        kind=n['type']; inner=lambda:inline(n.get('children',[]))
        if kind=='text':parts.append(escape(n['raw']))
        elif kind=='strong':parts.append('<b>'+inner()+'</b>')
        elif kind=='emphasis':parts.append('<i>'+inner()+'</i>')
        elif kind=='codespan':parts.append('<font name="Mono" size="8.5">'+escape(n['raw'])+'</font>')
        elif kind=='link':parts.append('<link href="'+escape(pdf_link(n['attrs']['url']),quote=True)+'" color="#22668a">'+inner()+'</link>')
        elif kind=='softbreak':parts.append(' ')
        elif kind=='linebreak':parts.append('<br/>')
        else:raise ValueError(f'Unsupported inline Markdown: {kind}')
    return ''.join(parts)


class Document(SimpleDocTemplate):
    def afterFlowable(self,item):
        if hasattr(item,'outline_title'):
            key='heading-'+str(self.seq.nextf('heading'))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(item.outline_title,key,level=item.outline_level)


def build():
    refresh_table()
    assert SOURCE.read_text().splitlines()[0]=='# '+TITLE,'Source and PDF title differ'
    assert RESEARCH_DATE in SOURCE.read_text().split('## Abstract')[0],'Source and PDF date differ'
    fontfiles=register_fonts()
    body=ParagraphStyle('body',fontName='Body',fontSize=10.5,leading=14,
                        textColor=colors.HexColor('#202b33'),spaceAfter=6,
                        allowWidows=0,allowOrphans=0)
    title=ParagraphStyle('title',parent=body,fontName='Sans-Bold',fontSize=19,
                         leading=24,textColor=colors.HexColor('#16374b'),spaceAfter=11)
    heading=ParagraphStyle('heading',parent=body,fontName='Sans-Bold',fontSize=12.1,
                           leading=15.5,spaceBefore=12,spaceAfter=6,keepWithNext=True)
    subheading=ParagraphStyle('subheading',parent=heading,fontSize=10.5,
                              leading=13.5,spaceBefore=9,spaceAfter=5)
    caption=ParagraphStyle('caption',parent=body,fontSize=9,leading=11.5,
                           textColor=colors.HexColor('#45545e'),spaceAfter=10)
    cell=ParagraphStyle('cell',parent=body,fontSize=9,leading=11.5,spaceAfter=0)
    code=ParagraphStyle('code',parent=body,fontName='Mono',fontSize=8.5,leading=11,
                        backColor=colors.HexColor('#eef3f6'),borderPadding=8,
                        spaceBefore=3,spaceAfter=10)
    story=[]
    ast=mistune.create_markdown(renderer='ast',plugins=['table'])(SOURCE.read_text())
    i=0
    while i<len(ast):
        node=ast[i];kind=node['type'];i+=1
        if kind=='blank_line':continue
        if kind=='block_html':
            assert node['raw'].strip().startswith('<!--')
            continue
        if kind=='heading':
            text=inline(node['children'])
            if text=='References':story.append(PageBreak())
            level=node['attrs']['level']
            p=Paragraph(text,title if level==1 else heading if level==2 else subheading)
            if level>1:
                p.outline_title=re.sub('<[^>]+>','',text)
                p.outline_level=level-2
            story.append(p)
        elif kind=='paragraph':
            children=node['children']
            if len(children)==1 and children[0]['type']=='image':
                path=THESIS/children[0]['attrs']['url']
                image=Image(str(path)); scale=WIDTH/image.imageWidth
                image.drawWidth=WIDTH;image.drawHeight=image.imageHeight*scale
                block=[Spacer(1,4),image]
                j=i
                while j<len(ast) and ast[j]['type']=='blank_line':j+=1
                if j<len(ast) and ast[j]['type']=='paragraph':
                    assert ast[j]['children'][0]['type']=='emphasis','Figure requires a caption'
                    block.append(Paragraph(inline(ast[j]['children']),caption));i=j+1
                story.append(KeepTogether(block))
            else:
                text=inline(children)
                style=caption if text.startswith('<i>Table ') else body
                story.append(Paragraph(text,style))
        elif kind=='table':
            matrix=[]
            for section in node['children']:
                rr=[section] if section['type']=='table_head' else section['children']
                for row in rr:
                    matrix.append([Paragraph(('<b>'+inline(c['children'])+'</b>') if not matrix
                                             else inline(c['children']),cell) for c in row['children']])
            columns=len(matrix[0])
            widths=([.28*WIDTH,.72*WIDTH] if columns==2 else
                    [v*WIDTH for v in (.18,.19,.17,.14,.16,.16)] if columns==6 else
                    [v*WIDTH for v in (.20,.25,.18,.19,.18)] if columns==5 else
                    [WIDTH/columns]*columns)
            table=Table(matrix,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([
                ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfeaf0')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f8')]),
                ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#8fa8b7')),
                ('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6)]))
            block=[Spacer(1,3),table,Spacer(1,6)]
            j=i
            while j<len(ast) and ast[j]['type']=='blank_line':j+=1
            if j<len(ast) and ast[j]['type']=='paragraph':
                text=inline(ast[j]['children'])
                if text.startswith('<i>Table '):
                    block.append(Paragraph(text,caption));i=j+1
            if story and hasattr(story[-1],'outline_title'):
                block.insert(0,story.pop())
            story.append(KeepTogether(block))
        elif kind=='list':
            for item in node['children']:
                text=' '.join(inline(block.get('children',[])) for block in item['children'])
                style=ParagraphStyle('bullet',parent=body,leftIndent=12,firstLineIndent=-8)
                story.append(Paragraph('• '+text,style))
        elif kind=='block_code':
            block=Preformatted(node['raw'].rstrip(),code)
            if story and isinstance(story[-1],Paragraph) and story[-1].getPlainText().rstrip().endswith(':'):
                story.append(KeepTogether([story.pop(),block]))
            else:story.append(block)
        else:raise ValueError(f'Unsupported block Markdown: {kind}')
    def page(canvas,doc):
        canvas.saveState()
        canvas.setFont('Sans',8);canvas.setFillColor(colors.HexColor('#5c6e78'))
        if doc.page>1:canvas.drawString(20*mm,A4[1]-13*mm,TITLE)
        canvas.drawString(20*mm,12*mm,'Artashes Atanesyan · Research thesis draft · '+RESEARCH_DATE)
        canvas.drawRightString(A4[0]-20*mm,12*mm,str(doc.page))
        canvas.restoreState()
    doc=Document(str(PDF),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,
                 topMargin=20*mm,bottomMargin=20*mm,title=TITLE,
                 author='Artashes Atanesyan',subject='UPMEM local reuse: resource boundaries, native costs and held-out decision evidence',
                 invariant=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
    info=subprocess.check_output(['pdfinfo',str(PDF)],text=True)
    pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
    paths=[SOURCE,PDF,ROOT/'scripts/build_short_thesis.py',ROOT/'scripts/thesis_figures.py',
           ROOT/'experiments/access-plan-fivepoint/manifest.json',
           ROOT/'experiments/baseline-gates/manifest.json',THESIS/'requirements.txt']
    paths+=sorted((THESIS/'figures').glob('*'))
    decision=ROOT/'experiments/decision-study'
    for name in ('manifest.json','frozen-model.json','summary.json','plotted-data.json',
                 'capacity.png','widths.png','decision-cost.png'):
        if (decision/name).exists():paths.append(decision/name)
    manifest=dict(pages=pages,research_date=RESEARCH_DATE,source_words=len(SOURCE.read_text().split()),
        dependencies={p:importlib.metadata.version(p) for p in ('reportlab','mistune','matplotlib','Pillow','charset-normalizer')},
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        fonts={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fontfiles})
    (THESIS/'build.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Built {PDF.relative_to(ROOT)}: {pages} pages; source and figure hashes in thesis/build.json.')


if __name__=='__main__':build()
