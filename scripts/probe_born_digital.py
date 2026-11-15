"""Read-only PDF experiments for docs/CODEX_BORN_DIGITAL_IMPROVMENTS.md.

No rasterization, OCR, OMR engine, or production edits. Existing MusicXML is used
only as the baseline/timeline for diagnostics. Run from the repository root:
    python scripts/probe_born_digital.py --inventory
    python scripts/probe_born_digital.py --experiments
    python scripts/probe_born_digital.py --metadata
Results go to results/analysis/born-digital-20261115/.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import subprocess
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openpyxl
import pymupdf

from omrbench import musicxml, project, truth
from omrbench.metrics import edits
from omrbench.pdfkind import classify_page
from omrbench.pipeline import vector
from scripts import pdf_truth_check as q

OUT = Path('results/analysis/born-digital-20261115')
METRIC_REVISION = '8154724410854eb45b4d06c0a33adbff97fc8e18'
# Deliberately excludes disputed compound symbols (especially ß).
DYNAMICS = {'p': 'p', 'P': 'mp', 'F': 'mf', 'f': 'f', 'ƒ': 'ff', 'π': 'pp', '∏': 'ppp'}
FONTS = {'EngraverFontSet', 'Petrucci'}


def metric_snapshot():
    """Isolate the measured metric from concurrent workspace changes.

    Only these three historical Python modules are loaded, under a separate
    package name. Production modules/files and the Git worktree are untouched.
    """
    global edits, musicxml
    root=OUT/'metric_snapshot'
    package=root/'born_digital_metrics'
    (package/'metrics').mkdir(parents=True,exist_ok=True)
    for p in [package/'__init__.py',package/'metrics/__init__.py']: p.write_text('')
    hashes={}
    for name in ['musicxml.py','metrics/notef1.py','metrics/edits.py']:
        src=subprocess.run(['git','show',f'{METRIC_REVISION}:omrbench/{name}'],
                           check=True,capture_output=True).stdout
        (package/name).write_bytes(src)
        hashes[f'{METRIC_REVISION}:omrbench/{name}']=hashlib.sha256(src).hexdigest()
    sys.path.insert(0,str(root.resolve()))
    musicxml=importlib.import_module('born_digital_metrics.musicxml')
    edits=importlib.import_module('born_digital_metrics.metrics.edits')
    return hashes


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + '\n')


def wedges(page):
    """Only two straight segments in one stroked path, forming a horizontal wedge.

    This intentionally misses split-path and system-break fragments. No pixels.
    """
    out = []
    for idx, d in enumerate(page.get_drawings()):
        it = d['items']
        if d['type'] != 's' or len(it) != 2 or any(i[0] != 'l' for i in it):
            continue
        a, b = sorted(it[0][1:], key=lambda p: p.x)
        c, e = sorted(it[1][1:], key=lambda p: p.x)
        if abs(a.x-c.x) > .3 or abs(b.x-e.x) > .3:
            continue
        width = b.x-a.x
        left, right = abs(a.y-c.y), abs(b.y-e.y)
        if width < 12 or min(left, right) > .4 or not 1.5 < max(left, right) < 14:
            continue
        if (b.y-a.y)*(e.y-c.y) >= 0 or max(left, right)/width > .35:
            continue
        out.append(dict(x=a.x, x1=b.x, y=(a.y+b.y+c.y+e.y)/4,
                        token='crescendo' if left < right else 'diminuendo', path=idx))
    return out


def inventory():
    report = []
    files = sorted(Path('data/ghost/pdfs').glob('*.pdf')) + [Path('data/anastasia/pdfs/PianoReduction.pdf')]
    # Negative control: a scanned keyboard book, not a target for direct extraction.
    files += [Path('data/anastasia/pdfs/Keyboard 1.pdf')]
    for path in files:
        with pymupdf.open(path) as doc:
            rows, fonts = [], Counter()
            for page in doc:
                pk = classify_page(page, page.number+1)
                ch = q.chars(page) if pk.kind.startswith('vector') else []
                fonts.update(c[3] for c in ch)
                dyn = Counter(DYNAMICS[c] for x,y,c,f,z in ch if f in FONTS and c in DYNAMICS)
                heads = sum(c in q.HEADS and f in FONTS for x,y,c,f,z in ch)
                rows.append(dict(page=page.number+1, kind=pk.kind, drawings=pk.drawings,
                                 chars=len(ch), heads=heads, dynamics=dyn,
                                 wedges=len(wedges(page)) if ch else 0))
            report.append(dict(file=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               pages=len(doc), attachments=doc.embfile_names(), metadata=doc.metadata,
                               kinds=Counter(r['kind'] for r in rows), fonts=fonts,
                               heads=sum(r['heads'] for r in rows),
                               dynamics=sum(sum(r['dynamics'].values()) for r in rows),
                               wedges=sum(r['wedges'] for r in rows), detail=rows))
            print(path.name, report[-1]['kinds'], 'heads/dyn/wedges',
                  report[-1]['heads'], report[-1]['dynamics'], report[-1]['wedges'], flush=True)
    save('inventory.json', report)


def metadata():
    report=[]
    for path in sorted(Path('data/ghost/pdfs').glob('*.pdf'))+[Path('data/anastasia/pdfs/PianoReduction.pdf')]:
        with pymupdf.open(path) as doc:
            tags=Counter(); actual=Counter(); alt=[]; fontrows=[]; seen=set(); taggedpages=[]
            for xr in range(1,doc.xref_length()):
                role=doc.xref_get_key(xr,'S')
                if role[0]=='name' and doc.xref_get_key(xr,'P')[0]!='null': tags[role[1]]+=1
                at=doc.xref_get_key(xr,'ActualText')
                if at[0]!='null': actual[at[1]]+=1
                av=doc.xref_get_key(xr,'Alt')
                if av[0]!='null': alt.append(av[1])
            for p in doc:
                if doc.xref_get_key(p.xref,'StructParents')[0]!='null': taggedpages.append(p.number+1)
                for f in p.get_fonts():
                    if f[0] in seen or f[3].split('+')[-1] not in FONTS: continue
                    seen.add(f[0])
                    fontrows.append(dict(xref=f[0],base_font=f[3],subtype=f[2],
                                         encoding=doc.xref_get_key(f[0],'Encoding'),
                                         to_unicode=doc.xref_get_key(f[0],'ToUnicode')))
            report.append(dict(file=str(path),structure_root=doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot'),
                               roles=tags,actual_text=actual,alt=alt,tagged_pages=taggedpages,
                               music_fonts=fontrows,bookmarks=len(doc.get_toc()),attachments=doc.embfile_names()))
    save('metadata.json',report)
    for x in report: print(x['file'],x['roles'],'ActualText',x['actual_text'])


def midi(p):
    step, alt, octv = p
    return (octv+1)*12 + {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11}[step] + alt


def source_marks(part, systems, nstaves):
    """Attach to printed bars. Keep only the lower group on reduction/utility books.

    Ownership is intentionally a simple nearest-staff baseline to expose failures.
    Dynamics/wedges between piano staves are displayed on the upper piano staff.
    """
    out = []
    with pymupdf.open(part.pdf) as doc:
        bypage = defaultdict(list)
        for s in systems:
            bypage[s['page']].append(s)
        for pn, sy in bypage.items():
            page = doc[pn-1]
            candidates = [dict(x=x, y=y, token=DYNAMICS[c], font=f, code=c, kind='dynamics')
                          for x,y,c,f,z in q.chars(page) if f in FONTS and c in DYNAMICS]
            candidates += [dict(w, kind='hairpins') for w in wedges(page)]
            allstaves = [(s,t) for s in sy for t in s['staves']]
            for m in candidates:
                # Prefer a staff immediately above the symbol, as appropriate for
                # instrumental dynamics; do not assign below a distant system.
                near = [(s,t) for s,t in allstaves
                        if t['x0']-t['sp'] <= m['x'] <= t['x1']+t['sp']
                        and -2*t['sp'] <= m['y']-(t['top']+4*t['sp']) <= 9*t['sp']]
                if not near:
                    continue
                s,t = min(near, key=lambda st: abs(m['y']-(st[1]['top']+4*st[1]['sp'])))
                kept = s['staves'][-nstaves:]
                if t not in kept:
                    continue
                st = kept.index(t)+1
                if nstaves == 2 and kept[0]['top']+4*kept[0]['sp'] < m['y'] < kept[1]['top']:
                    st,t = 1,kept[0]
                b = s['start'] + sum(x < m['x'] for x in t['bars'])
                # q.pdf_notes has corrected start-repeat edges but exposes no
                # multirest spans; consequently those bars remain an explicit risk.
                left = max([t['x0']] + [x for x in t['bars'] if x < m['x']])
                right = min([t['x1']] + [x for x in t['bars'] if x > m['x']])
                content = sorted(set(round(c[0],2) for c in t['chars']
                                     if c[2] in q.HEADS or c[2] in q.RESTS
                                     if left <= c[0] < right
                                     if c[4] >= 3.4*t['sp']))
                out.append(dict(m, page=pn, staff=st, bar=b,
                                before_first=bool(content) and m['x'] <= content[0]+t['sp'],
                                left=left, right=right))
    return out


def direct_rhythm(part, systems, pitches, seq, times, target):
    """Small independent monophonic reader: note/rest glyphs + stems/beams/dots.

    Accept only a single staff, one head per column, and a complete printed meter.
    No output timeline or truth is consulted before selecting a bar. This is an
    experiment, not a general reader (tuplets, repeats, multi-voice bars abstain).
    """
    row = dict(part=part.name, considered=0, accepted=0, exact=0, notes=0,
               note_actions=0, rejected=Counter(), examples=[])
    rest_codes = {'Œ':Fraction(1),'Ó':Fraction(2),'‰':Fraction(1,2),
                  '≈':Fraction(1,4),'∑':None}
    with pymupdf.open(part.pdf) as doc:
        for s in systems:
            if len(s['staves'])!=1:
                continue
            t=s['staves'][0]; sp=t['sp']; page=doc[s['page']-1]
            _,_,stems,fills,_=vector._drawings(page)
            chars=[dict(x=c['origin'][0],y=c['origin'][1],code=c['c'],w=c['bbox'][2]-c['bbox'][0],size=span['size'])
                   for block in page.get_text('rawdict')['blocks'] for line in block.get('lines',[])
                   for span in line['spans'] if span['font']=='EngraverFontSet' for c in span['chars']
                   if t['top']-6*sp<c['origin'][1]<t['top']+10*sp]
            edges=[t['x0']]+t['bars']
            if not edges or edges[-1]<t['x1']-sp: edges.append(t['x1'])
            for k,(left,right) in enumerate(zip(edges,edges[1:])):
                b=s['start']+k
                if not 1<=b<=len(seq): continue
                row['considered']+=1
                num=int(re.match(r'\d+',seq[b-1]).group())
                meter=next((v for start,_,v in reversed(times) if start<=num),times[0][2])
                length=4*Fraction(str(meter))
                mine=[c for c in chars if left<=c['x']<right]
                events=[]; bad=None
                for c in sorted(mine,key=lambda c:(c['x'],c['y'])):
                    if c['size']<3.4*sp: continue
                    code=c['code']; dur=None
                    if code in q.HEADS:
                        dur=Fraction(2) if q.HEADS[code]=='half' else Fraction(4) if code=='w' else None
                        if dur is None:
                            ss=[v for v in stems if c['x']-1<=v[0]<=c['x']+c['w']+1
                                and v[1]-.6*sp<=c['y']<=v[2]+.6*sp]
                            if len(ss)!=1: bad='ambiguous_stem'; break
                            stem=ss[0]; end=max(stem[1:],key=lambda y:abs(y-c['y']))
                            beams=[f for f in fills if f[0]-.5<=stem[0]<=f[1]+.5
                                   and min(abs(end-f[2]),abs(end-f[3]))<2.5*sp
                                   and f[1]-f[0]>sp]
                            flags=any(c2['code'] in ('J','j') and abs(c2['x']-stem[0])<sp
                                      and abs(c2['y']-end)<3*sp for c2 in mine)
                            dur=Fraction(1,2**max(len(beams),int(flags)))
                        kind='head'
                    elif code in rest_codes and abs(c['y']-(t['top']+2*sp))<2*sp:
                        dur=rest_codes[code] or length; kind='rest'
                    else: continue
                    dots=[d for d in mine if d['code']=='.' and c['w']*.8<d['x']-c['x']<c['w']+1.5*sp
                          and abs(d['y']-c['y'])<=.6*sp]
                    if len(dots)>1: bad='multiple_dots'; break
                    if dots: dur*=Fraction(3,2)
                    events.append((c['x'],kind,dur))
                if bad: row['rejected'][bad]+=1; continue
                if any(abs(a[0]-b2[0])<sp for a,b2 in zip(events,events[1:])):
                    row['rejected']['multiple_heads_or_voices']+=1;continue
                if sum(e[2] for e in events)!=length:
                    row['rejected']['does_not_fill_meter']+=1;continue
                ps=pitches.get((0,b),[])
                if sum(e[1]=='head' for e in events)!=len(ps):
                    row['rejected']['pitch_head_disagreement']+=1;continue
                if not ps:
                    row['rejected']['no_pitched_notes']+=1;continue
                notes=Counter(); onset=Fraction(0); it=iter(ps)
                for x,kind,dur in events:
                    if kind=='head': notes[(1,onset,midi(next(it)),dur)]+=1
                    onset+=dur
                # Cello and Bass have octave-transposing playback conventions;
                # compare written pitches here by removing declared truth transpose.
                tgt=target[b-1][0] if b<=len(target) else Counter()
                cost=edits._notes_cost(notes,tgt)
                row['accepted']+=1;row['exact']+=cost==0
                row['notes']+=sum(notes.values());row['note_actions']+=cost
                row['examples'].append(dict(bar=b,cost=cost,notes=list(notes.elements())))
    return row


def experiments():
    result = {'pitch':[], 'marks':[], 'rhythm':[], 'reader_coverage':[], 'hashes':metric_snapshot(),
              'metric_revision':METRIC_REVISION, 'notes':[
        'Frozen r69-a outputs versus current truth exports; not a freshly reassembled baseline.',
        'Pitch replacement uses equal head counts and output onset/duration order; no truth-gated selection.',
        'Mark simulation adds at onset zero only, before the first printed head/rest, when the category is absent.',
        'Diagnostic written-to-sounding calibration takes transpose from the truth part; production must use workbook/source instrument state.',
        'Frozen baseline alignment used for local costs; these are not acceptance-benchmark gains.',
        'Anastasia reduction piano is excluded from normal benchmark; its comparison here is diagnostic only.']}
    for show in ['ghost','anastasia']:
        proj = project.load(Path('data')/show)
        wb = openpyxl.load_workbook(proj.workbook)
        for path in [proj.workbook,proj.dir/'show.yaml',Path('scripts/pdf_truth_check.py'),Path(__file__)]:
            result['hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for sid,song in proj.songs.items():
            if not song.truth_files or sid in ('4A','5A'):
                continue
            for path in song.truth_files:
                result['hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            tr = truth.load(song.truth_files,Path('results/cache'),None)
            tparts = dict(truth.parts(tr))
            rows = {r[0]:r for r in wb[sid].iter_rows(values_only=True) if r[0]}
            seq, keys = q.bar_labels(rows), project.bar_map(rows['key'][1])
            for part in song.parts:
                if part.name not in ('PianoReduction','Utility','Cello','Bass','Violin','Reed','Trumpet'):
                    continue
                if show=='anastasia' and part.name!='PianoReduction':
                    continue
                names = [v.split('=')[-1] for v in part.truth if not v.endswith('=-')]
                tn = 'Klavierauszug' if show=='anastasia' else next(iter(names),None)
                if tn not in tparts:
                    continue
                tp = tparts[tn]
                nstaves = 2 if part.name in ('PianoReduction','Utility') else 1
                suffix = ' - Piano' if part.name=='PianoReduction' else ''
                base = Path('results')/show/'runs/r69-a'/sid
                output = base/('vote' if show=='anastasia' else '')/(part.name+suffix+'.musicxml')
                if not output.exists():
                    continue
                pp = musicxml.load(output).find('part')
                result['hashes'][str(output)] = hashlib.sha256(output.read_bytes()).hexdigest()
                chrom = int(tp.findtext('.//transpose/chromatic') or 0)
                fifthshift = (-chrom*7+6)%12-6
                def key_at(b):
                    num = int(re.match(r'\d+',seq[max(0,min(b,len(seq))-1)]).group())
                    key = int(next((v for start,_,v in reversed(keys) if start<=num),keys[0][2]))
                    return (key+fifthshift+6)%12-6 if fifthshift else key
                pb,sy = q.pdf_notes(part.pdf,part.meta['pages'],seq,key_at,nstaves,cues=part.name=='PianoReduction')
                P,T = edits.part_bars([pp]), edits.part_bars([tp])
                if show=='ghost' and part.name in ('Cello','Bass') and sid in ('4','5','13'):
                    trshift=chrom+12*int(tp.findtext('.//transpose/octave-change') or 0)
                    rr=direct_rhythm(part,sy,pb,seq,project.bar_map(rows['time'][1]),edits._shifted(T,-trshift))
                    rr['part']=f'{show} {sid} {part.name}'
                    result['rhythm'].append(rr)
                _, alignment = edits._align(P,T)
                # Same whole-part/region normalization as the benchmark.
                shift = edits._best_shift(P,T)
                if shift and edits._align(edits._shifted(P,shift),T)[0]+1 < edits._align(P,T)[0]:
                    P = edits._shifted(P,shift)
                    _, alignment = edits._align(P,T)
                _, P = edits._octave_regions(P,T,alignment)
                label = f'{show} {sid} {part.name}'
                row = dict(part=label,truth_part=tn,staff_bars=0,nonempty=0,exact_pitch_bags=0,
                           baseline_notes=0,trial_notes=0,eligible_staff_bars=0,changed=0,
                           improved=0,worsened=0,neutral=0,examples=[],
                           narrow_notes=0,narrow_changed=0,narrow_improved=0,narrow_worsened=0,
                           narrow_examples=[])
                truthbag = q.truth_notes(tp)
                for st in range(nstaves):
                    for b in range(1,len(seq)+1):
                        src,tgt = Counter(pb.get((st,b),[])),Counter(truthbag.get((st,b),[]))
                        row['staff_bars'] += 1
                        if src or tgt:
                            row['nonempty'] += 1
                            row['exact_pitch_bags'] += src == tgt
                for i,j in alignment:
                    if i is None or j is None:
                        continue
                    # Source indexed by output bar, never by aligned truth index.
                    old = P[i][0]
                    new = old.copy()
                    narrow = old.copy()
                    for st in range(1,nstaves+1):
                        ns = [k for k in old.elements() if k[0]==st]
                        src = pb.get((st-1,i+1),[])
                        if not ns or len(ns)!=len(src) or any(not isinstance(k[2],int) for k in ns):
                            continue
                        ns.sort(key=lambda k:(k[1],-k[2]))
                        row['eligible_staff_bars'] += 1
                        # Written pitch -> sounding pitch; use part's declared transpose.
                        octave_change = 12*int(tp.findtext('.//transpose/octave-change') or 0)
                        source_pitches = [midi(p)+chrom+octave_change for p in src]
                        have, want = Counter(k[2] for k in ns),Counter(source_pitches)
                        extra,missing = have-want,want-have
                        # A deliberately conservative second trial: one distinct
                        # wrong pitch, equally many source heads, under an octave.
                        # Match by pitch identity, retaining each event's timing.
                        if len(extra)==len(missing)==1 and sum(extra.values())==sum(missing.values()):
                            a,b = next(iter(extra)),next(iter(missing))
                            if 0 < abs(a-b) < 12 and have[a]==extra[a]:
                                for k in ns:
                                    if k[2]==a:
                                        narrow[k]-=1
                                        narrow[(st,k[1],b,k[3])]+=1
                        for k,pitch in zip(ns,src):
                            new[k]-=1
                            new[(st,k[1],midi(pitch)+chrom+octave_change,k[3])]+=1
                    new += Counter()
                    narrow += Counter()
                    oldcost,newcost = edits._notes_cost(old,T[j][0]),edits._notes_cost(new,T[j][0])
                    narrowcost = edits._notes_cost(narrow,T[j][0])
                    row['narrow_notes'] += narrowcost
                    if narrow != old:
                        row['narrow_changed'] += 1
                        row['narrow_improved'] += narrowcost < oldcost
                        row['narrow_worsened'] += narrowcost > oldcost
                        row['narrow_examples'].append(dict(output_bar=i+1,truth_bar=j+1,before=oldcost,after=narrowcost,
                            removed=list((old-narrow).elements()),added=list((narrow-old).elements())))
                    row['baseline_notes'] += oldcost
                    row['trial_notes'] += newcost
                    if new != old:
                        row['changed'] += 1
                        row['improved' if newcost<oldcost else 'worsened' if newcost>oldcost else 'neutral']+=1
                        row['examples'].append(dict(output_bar=i+1,truth_bar=j+1,before=oldcost,after=newcost))
                result['pitch'].append(row)
                marks = source_marks(part,sy,nstaves)
                mr = dict(part=label,candidates=Counter(m['kind'] for m in marks),
                          token_matches=Counter(), unmatched=Counter(), before=Counter(),after=Counter(),
                          added=Counter(),improved=Counter(),worsened=Counter(), rows=[],all_candidates=marks)
                lookup = {i:j for i,j in alignment if i is not None and j is not None}
                for m in marks:
                    j=lookup.get(m['bar']-1)
                    if j is None:
                        continue
                    match=any(k[0]==m['kind'] and k[3]==m['token'] for k in T[j][1])
                    mr['token_matches' if match else 'unmatched'][m['kind']]+=1
                for i,j in alignment:
                    if i is None or j is None:
                        continue
                    for cat in ['dynamics','hairpins']:
                        old=Counter({k:v for k,v in P[i][1].items() if k[0]==cat})
                        target=Counter({k:v for k,v in T[j][1].items() if k[0]==cat})
                        new=old.copy()
                        ms=[m for m in marks if m['bar']==i+1 and m['kind']==cat and m['before_first']]
                        if not old:
                            for m in ms:
                                new[(cat,m['staff'],0,m['token'])]=1
                        before,after=edits._items_cost(old,target),edits._items_cost(new,target)
                        mr['before'][cat]+=before; mr['after'][cat]+=after
                        if new!=old:
                            mr['added'][cat]+=sum((new-old).values())
                            mr['improved'][cat]+=before>after; mr['worsened'][cat]+=after>before
                            mr['rows'].append(dict(kind=cat,output_bar=i+1,truth_bar=j+1,
                                                   before=before,after=after,source=ms))
                result['marks'].append(mr)
                with pymupdf.open(part.pdf) as doc:
                    for pn in q.pages(part.meta['pages']):
                        page=doc[pn-1]; proxy=SimpleNamespace(width=page.rect.width,number=pn)
                        current_systems=vector.read_systems(page,proxy)
                        result['reader_coverage'].append(dict(part=label,page=pn,
                            source_staves=len(q.staves_of(page)),
                            vector_staves=len(current_systems),
                            current_staff_bars=[len(bs) for top,bs,ts in current_systems],
                            current_times=[ts for top,bs,ts in current_systems],
                            grouped_staff_bar_counts=[[len(t['bars']) for t in s['staves']]
                                                      for s in sy if s['page']==pn],
                            vector_mark_bars=len(vector.read_marks(page,proxy)),
                            source_heads=sum(c in q.HEADS and f in FONTS for x,y,c,f,z in q.chars(page))))
                print(label,'pitch',row['baseline_notes'],row['trial_notes'],
                      'narrow',row['narrow_notes'],
                      'marks',mr['before'],mr['after'],flush=True)
    save('experiments.json',result)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inventory',action='store_true')
    ap.add_argument('--experiments',action='store_true')
    ap.add_argument('--metadata',action='store_true')
    args=ap.parse_args()
    if args.inventory: inventory()
    if args.experiments: experiments()
    if args.metadata: metadata()
