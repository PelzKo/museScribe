"""Suspicious bars of a combined.mscx, found from the score alone (no images): `review_tool.py lint`.

python scripts/review_tool.py lint <file.mscx> [--staves 3,4] [--fix-safe 1] [--plain "Part A,Part B"]

Prints one line per finding, grouped by staff: `bar: [kind] what`. Kinds:
  length     a voice does not fill its bar (or overfills it); a whole-bar rest of the wrong length (fix-safe)
  range      note more than 2 semitones outside the instrument's range (misread clef / ledger lines / octave line)
  spelling   double accidentals
  clef       clef change in a non-keyboard part (almost always a misread; cello / bassoon / trombone can be real)
  span       slur or hairpin over more than 4 bars; spanner half without its partner (cross-staff glissandi:
             looked up on the other staff); duplicate hairpin (fix-safe)
  tie        two ties on one note
  rest-mark  articulation on a rest (fix-safe: removed)
  text       system / tempo text repeated on several staves (fix-safe: kept on the top one); staff text in 3+ parts,
             spelled a little differently, within +-1 bar (fix-safe: one system text on the top staff at the bar
             most copies have; copies at other bars only listed; playing, expression and dynamic words excluded); label words (solo, to ..., Harp); playing words not as German playing technique;
             expression text in a keyboard
  fermata    2/3 of the parts have a fermata at this position, this one none in the bar (fix-safe: added); 3+ have
             one; parts named in --plain (workbook plainArticulation, by part name) are left out
  cue        a keyboard bar contains all notes of the other keyboard part for 2+ bars (its line printed as a cue?)
  doubling   two single-staff parts that agree in 75 % of their bars differ here with the same rhythm (misread?)
Calibrated on the truths of songs 2, 4, 5, 5A (few findings there); checks that fired on correct scores were dropped
(hairpin end positions, mixed accidentals, repeated dynamics).
Findings are hints: look at the page before changing anything they name (except the fix-safe ones).
"""
import re
import sys
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_edit as E  # noqa: E402

LABEL = re.compile(r"^\s*(solo|soli|to\s|harp|eng\.?\s*h|picc\b|fl\.|cl\.|tpt\.?|tbn\.?|hn\.|lh:|rh:|snares|tacet)",
                   re.I)
PLAYWORD = re.compile(r"^\s*(mute|st\.?\s*mute|cup\s*mute|con\s*sord|open|senza\s*sord)", re.I)
TEXT_TAGS = ("StaffText", "Expression", "SystemText", "TempoText", "PlayTechAnnotation")
SPAN_KINDS = ("HairPin", "Slur", "Tie", "Glissando")


def _text(el):
    t = el.find("text")
    return "".join(t.itertext()).strip() if t is not None else ""


def _name(tpc, midi):
    step = "FCGDAEB"[(tpc + 1) % 7]
    alter = (tpc + 1) // 7 - 2
    semis = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]
    return f"{step}{'#' * alter if alter > 0 else 'b' * -alter}{(midi - alter - semis) // 12 - 1}", step, alter


class Staff:
    """Everything lint needs from one staff, positions as (bar, Fraction of a whole note)."""

    def __init__(self, score, sid, part, pidx):
        self.sid, self.part, self.pidx = sid, part, pidx
        inst = part.find("Instrument")
        self.name = part.findtext("trackName") or inst.findtext("longName") or f"part {pidx}"
        self.iid = inst.findtext("instrumentId") or ""
        self.keyboard = self.iid.startswith("keyboard")
        self.drum = inst.find("Drum") is not None
        self.lo, self.hi = (int(inst.findtext(t)) if inst.findtext(t) else None for t in ("minPitchP", "maxPitchP"))
        self.trans = E.transposition(score, sid)
        self.measures = E.staff(score, sid).findall("Measure")
        self.lens, self.notes, self.dyn, self.ferm, self.texts = [], defaultdict(list), [], set(), []
        self.findings = []
        sig = F(1)
        for b, m in enumerate(self.measures, 1):
            for ts in m.iter("TimeSig"):
                sig = F(int(ts.findtext("sigN")), int(ts.findtext("sigD")))
            ln = F(m.get("len")) if m.get("len") else sig
            self.lens.append(ln)
            for vi, v in enumerate(m.findall("voice")):
                for c, t, d in E._walk(v):
                    if c.tag == "Chord" and d:
                        for n in c.findall("Note"):
                            self.notes[b].append((t, int(n.findtext("pitch")),
                                                  int(n.findtext("tpc2") or n.findtext("tpc") or 14), n))
                    elif c.tag == "Dynamic":
                        self.dyn.append((b, t, c.findtext("subtype")))
                    elif c.tag == "Fermata":
                        self.ferm.add((b, t))
                    elif c.tag in TEXT_TAGS:
                        self.texts.append((b, c.tag, _text(c), c, t))

    def add(self, bar, kind, msg, fix=None):
        self.findings.append((bar, kind, msg, fix))

    def chord_starts(self, b):
        return {t for t, *_ in self.notes.get(b, [])}


def check_lengths(st):
    for b, (m, ln) in enumerate(zip(st.measures, st.lens), 1):
        for vi, v in enumerate(m.findall("voice")):
            got = E.voice_len(v)
            rests = [c for c in v if c.tag == "Rest" and c.findtext("durationType") == "measure"]
            if vi == 0 and rests and len([c for c in v if c.tag in ("Chord", "Rest")]) == 1 and F(rests[0].findtext("duration")) != ln:
                r = rests[0]
                st.add(b, "length", f"voice {vi + 1}: whole-bar rest of {r.findtext('duration')}, bar is {ln}",
                       lambda r=r, ln=ln: r.find("duration").__setattr__("text", f"{ln.numerator}/{ln.denominator}"))
            elif (vi == 0 and got != ln) or got > ln:
                st.add(b, "length", f"voice {vi + 1} fills {got * 4} of {ln * 4} quarters")


def check_pitches(st):
    if st.drum:
        return
    ch, di = st.trans
    for b, notes in st.notes.items():
        for t, p, tpc, _ in notes:
            name, step, alter = _name(tpc, p - ch)
            if st.lo is not None and not st.lo - 2 <= p <= st.hi + 2:
                st.add(b, "range", f"{name} (written) outside the range of {st.iid}")
            if abs(alter) > 1:
                st.add(b, "spelling", f"double accidental {name}")


def check_clefs(st):
    if st.keyboard or st.drum:
        return
    for b, m in enumerate(st.measures, 1):
        for v in m.findall("voice"):
            for c, t in E.timeline(v):
                if c.tag == "Clef" and c.findtext("isHeader") != "1" and not (b == 1 and t == 0):
                    st.add(b, "clef", f"clef change to {c.findtext('concertClefType')} "
                                      "(in a wind / string part almost always a misread)")


def _target(s, b, t, tag):
    loc = s.find(tag + "/location")
    return b + int(loc.findtext("measures") or 0), t + F(loc.findtext("fractions") or 0)


def _cross(s):
    """Staff offset of a spanner half that links to another staff of the part (cross-staff glissando), else 0."""
    return int(s.findtext("next/location/staves") or s.findtext("prev/location/staves") or 0)


def _partner(score, sid, kind, s, b, t, is_start):
    """True when the other staff holds the opposite half that points back to (b, t)."""
    other = str(int(sid) + _cross(s))
    tb, tt = _target(s, b, t, "next" if is_start else "prev")
    try:
        sp = E.spanners(score, other, kind)
    except StopIteration:
        return False
    return any(s2 is not s and is_start != st2 and (b2, t2) == (tb, tt)
               and _target(s2, b2, t2, "prev" if is_start else "next") == (b, t) for s2, b2, t2, st2 in sp)


def check_spanners(st, score):
    sid = st.sid
    for kind in SPAN_KINDS:
        sp = E.spanners(score, sid, kind)
        starts = Counter()
        local = [x for x in sp if not _cross(x[0])]
        ends = Counter((_target(s, b, t, "prev"), (b, t)) for s, b, t, is_start in local if not is_start)
        begins = Counter(((b, t), _target(s, b, t, "next")) for s, b, t, is_start in local if is_start)
        for s, b, t, is_start in sp:
            if _cross(s):
                if kind != "Tie" and not _partner(score, sid, kind, s, b, t, is_start):
                    st.add(b, "span", f"cross-staff {kind} {'start' if is_start else 'end'} without its partner "
                                      f"on staff {int(sid) + _cross(s)}")
                continue
            if not is_start:
                key = (_target(s, b, t, "prev"), (b, t))
                if key not in begins and kind != "Tie":   # two end halves at the score's end: MuseScore's own way
                    st.add(b, "span", f"{kind} end without its start")
                continue
            (eb, ep) = _target(s, b, t, "next")
            if kind != "Tie" and ((b, t), (eb, ep)) not in ends:
                st.add(b, "span", f"{kind} start without its end (->{eb}@{ep * 4})")
            if kind in ("HairPin", "Slur") and eb - b > 4:
                st.add(b, "span", f"{kind} over {eb - b} bars (->{eb}): misread end?")
            if kind == "HairPin":
                key = (b, t, eb, ep, s.findtext("HairPin/subtype"))
                starts[key] += 1
                if starts[key] == 2:
                    st.add(b, "span", "two identical hairpins", lambda s=s, sb=b, st_=t: _drop_pair(score, sid, s, sb, st_))
    for b, notes in st.notes.items():
        for _, _, _, n in notes:
            ties = n.findall("Spanner[@type='Tie']")
            nxt = [x for x in ties if x.find("next") is not None]
            if len(nxt) > 1:
                st.add(b, "tie", "two ties on one note (remove one tie and its end on the next note)")


def _drop_pair(score, sid, s, b, t):
    eb, ep = _target(s, b, t, "next")
    for e, b2, t2, is_start in E.spanners(score, sid, "HairPin"):
        if not is_start and (b2, t2) == (eb, ep) and _target(e, b2, t2, "prev") == (b, t):
            e.getparent().remove(e)
            break
    s.getparent().remove(s)


def check_marks(st):
    for b, m in enumerate(st.measures, 1):
        for r in m.iter("Rest"):
            arts = r.findall("Articulation")
            if arts:
                st.add(b, "rest-mark", f"{arts[0].findtext('subtype')} on a rest",
                       lambda r=r, a=arts: [r.remove(x) for x in a])
    for b, tag, text, el, t in st.texts:
        if LABEL.match(text):
            st.add(b, "text", f'{tag} "{text}": a label (convention: left out)')
        elif PLAYWORD.match(text) and tag != "PlayTechAnnotation":
            st.add(b, "text", f'{tag} "{text}": playing word -> PlayTechAnnotation "gedämpft" / "offen"')
        elif st.keyboard and tag in ("StaffText", "Expression"):
            st.add(b, "text", f'{tag} "{text}" in a keyboard (convention: none)')


NOT_TEMPO = re.compile(r"^(pizz|arco|div|unis|sim|solo|soli|tutti|gedämpft|offen|mute|open|senza|con sord|l\.?v|"
                       r"let ring)|cresc|dim\b|dim\.|decresc|\bsub\b|\b(ppp|pp|p|mp|mf|f|ff|fff|sfz|fp)\b|poco\s*f\b",
                       re.I)   # playing, expression and dynamic words stay staff text


def _norm(text):
    """Text compared without case, brackets, dots and extra spaces ("Con mosso (In 1))" = "con mosso (in 1)")."""
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


def _balanced(text):
    return text.count("(") == text.count(")")


def check_texts(staves, score=None):
    seen = defaultdict(list)
    for st in staves:
        for b, tag, text, el, t in st.texts:
            if text:
                seen[(b, t, text.lower())].append((st, tag, el))
    for (b, _, text), hits in seen.items():
        system = [h for h in hits if h[1] in ("SystemText", "TempoText")]
        for st, tag, el in system[1:]:
            st.add(b, "text", f'{tag} "{text}" also on staff {system[0][0].sid}: kept once on the top staff',
                   lambda el=el: el.getparent().remove(el))
    # staff text in 3+ parts (any bar, spelling variants joined): a tempo / system word copied into every part
    groups, sys_texts = defaultdict(list), set()
    for st in staves:
        for b, tag, text, el, t in st.texts:
            if tag in ("SystemText", "TempoText"):
                sys_texts.add(_norm(text))
            elif tag in ("StaffText", "Expression") and text and not NOT_TEMPO.search(text.strip()):
                groups[_norm(text)].append((st, b, t, text, el))
    for key, hits in groups.items():
        if len({h[0].pidx for h in hits}) < 3:
            continue
        (b, t), _ = Counter((h[1], h[2]) for h in hits).most_common(1)[0]
        near = [h for h in hits if abs(h[1] - b) <= 1]       # the copies of one printed mark
        far = sorted({f"{h[0].sid}@{h[1]}" for h in hits if abs(h[1] - b) > 1}, key=lambda x: int(x.split("@")[0]))
        if len({h[0].pidx for h in near}) < 3:
            continue
        forms = Counter(h[3] for h in near if (h[1], h[2]) == (b, t))
        text = max(forms, key=lambda x: (_balanced(x), forms[x]))
        def fix(near=near, b=b, t=t, text=text, key=key):
            for h in near:
                h[4].getparent().remove(h[4])
            if key not in sys_texts and score is not None:
                E.add_text(score, staves[0].sid, b, t, text)
        near[0][0].add(b, "text", f'"{text}" as staff text in {len({h[0].pidx for h in near})} parts at bar {b}'
                       f"{'+-1' if any(h[1] != b for h in near) else ''}: tempo / system word (fix-safe: one system "
                       f"text on staff {staves[0].sid})" + (f"; same text at other bars, check: {', '.join(far)}"
                                                           if far else ""), fix)


def check_fermatas(score, staves, plain=()):
    """Vote per bar and position; parts in `plain` (workbook plainArticulation) carry no fermatas."""
    by_part = defaultdict(list)
    for st in staves:
        if st.name not in plain:
            by_part[st.pidx].append(st)
    nparts = len(by_part)
    have = defaultdict(set)                       # (bar, pos) -> parts
    for p, sts in by_part.items():
        for st in sts:
            for b, t in st.ferm:
                have[(b, t)].add(p)
    for (b, pos), hit in sorted(have.items()):
        if len(hit) < 3:
            continue
        for p, sts in by_part.items():
            if p in hit or any(fb == b for st in sts for fb, _ in st.ferm):
                continue
            st = sts[0]
            if len(hit) * 3 >= nparts * 2:
                st.add(b, "fermata", f"{len(hit)} of {nparts} parts have a fermata @{pos * 4}: added",
                       lambda st=st, b=b, pos=pos: _add_fermata(st, b, pos))
            else:
                st.add(b, "fermata", f"{len(hit)} of {nparts} parts have a fermata @{pos * 4}, fewer than 2/3")


def _add_fermata(st, b, pos):
    v = st.measures[b - 1].find("voice")
    for c, t, d in E._walk(v):
        if c.tag in ("Chord", "Rest") and d and t <= pos < t + d:
            f = etree.Element("Fermata")
            etree.SubElement(f, "subtype").text = "fermataAbove"
            c.addprevious(f)
            return


def _bar_notes(st, b, pc=False):
    return frozenset((t, p % 12 if pc else p) for t, p, *_ in st.notes.get(b, []))


def check_cues(staves):
    kbs = [s for s in staves if s.keyboard]
    for kb in kbs:
        for o in (s for s in kbs if s.pidx != kb.pidx):   # other parts doubled by a keyboard are often real
            run = []
            for b in range(1, len(kb.measures) + 2):
                on, kn = _bar_notes(o, b), _bar_notes(kb, b)
                if len(on) >= 3 and on <= kn:
                    run.append(b)
                    continue
                if len(run) >= 2:
                    kb.add(run[0], "cue", f"bars {run[0]}-{run[-1]} contain all notes of {o.name}: "
                                          "cue / reference line of another book? (rule: left out)")
                run = []


def check_doublings(staves):
    single = [s for s in staves if not s.keyboard and not s.drum and sum(x.pidx == s.pidx for x in staves) == 1]
    for i, a in enumerate(single):
        for b_ in single[i + 1:]:
            both = [k for k in range(1, len(a.measures) + 1) if a.notes.get(k) and b_.notes.get(k)]
            same = [k for k in both if _bar_notes(a, k, True) == _bar_notes(b_, k, True)]
            if len(same) < 8 or len(same) < 0.75 * len(both):
                continue
            diff = [k for k in both if k not in same and {t for t, _ in _bar_notes(a, k)} == {t for t, _ in _bar_notes(b_, k)}]
            for k in diff[:15]:
                for x, y in ((a, b_), (b_, a)):
                    x.add(k, "doubling", f"differs from {y.name}, which it doubles in {len(same)} of {len(both)} "
                                         "bars: one of them misread?")


def lint(path, staves=None, fix_safe=False, plain=""):
    tree = etree.parse(str(path))
    score = tree.getroot().find("Score")
    sts, n = [], 0
    for pidx, part in enumerate(score.findall("Part")):
        for _ in part.findall("Staff"):
            n += 1
            sts.append(Staff(score, str(n), part, pidx))
    for st in sts:
        check_lengths(st)
        check_pitches(st)
        check_clefs(st)
        check_spanners(st, score)
        check_marks(st)
    check_texts(sts, score)
    check_fermatas(score, sts, {x.strip() for x in plain.split(",") if x.strip()})
    check_cues(sts)
    check_doublings(sts)
    want = set(str(staves).split(",")) if staves else None
    kinds, fixed = Counter(), 0
    out = []
    for st in sts:
        if want and st.sid not in want or not st.findings:
            continue
        out.append(f"== staff {st.sid} {st.name}")
        for b, kind, msg, fix in sorted(st.findings, key=lambda f: (f[0], f[1])):
            kinds[kind] += 1
            done = ""
            if fix_safe and fix:
                fix()
                fixed += 1
                done = "  [fixed]"
            elif fix:
                done = "  [fix-safe]"
            out.append(f"{b}: [{kind}] {msg}{done}")
    if fixed:
        tree.write(str(path), xml_declaration=True, encoding="UTF-8")
    out.append("summary: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()) + (f"; fixed {fixed}" if fixed else ""))
    return "\n".join(out)


def main(path, staves=None, fix_safe=False, plain=""):
    print(lint(path, staves, fix_safe, plain))
