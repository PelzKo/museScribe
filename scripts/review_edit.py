"""lxml helpers for editing a MuseScore 4 combined.mscx (docs/REVIEW_AGENT_PROMPT.md).

Positions are (bar 1-based, Fraction of a whole note from the bar start). Use from Python:
    import sys; sys.path.insert(0, "scripts"); import review_edit as E
    tree, score = E.load(path); E.add_hairpin(score, 14, (1, F(1, 4)), (3, F(0))); E.save(tree, path)
Spanner <location>: <measures> = bar index difference, <fractions> = position difference in whole notes (may be
negative); start has <next>, end has <prev> with the opposite values. HairPin subtype 0 = cresc, 1 = dim.
timeline() follows tuplets and the <location> cursor moves MuseScore writes into voices.

Writing notes: set_voice(score, sid, bar, "C4+E4/8 r/8 3:2{ D4/8 E4/8 F4/8 } G4/4.~ G4/8 rM") takes WRITTEN pitch
(as dump prints it; transposing parts get <pitch>/<tpc> in concert and <tpc2> as written), '~' = tie to the next chord
(same pitches, also into the next bar), 'n:2{ ... }' = tuplet (n notes in the time of 2), 'grace:D5/8' = acciaccatura,
'rM' = whole-bar rest. Drum staves: the drum name from dump with '_' for spaces (Acoustic_Snare/8).
"""
from fractions import Fraction as F
from lxml import etree

DUR = {"breve": F(2), "whole": F(1), "half": F(1, 2), "quarter": F(1, 4), "eighth": F(1, 8), "16th": F(1, 16),
       "32nd": F(1, 32), "64th": F(1, 64), "128th": F(1, 128)}
GRACE = ("grace", "acciaccatura", "appoggiatura")
E = etree.SubElement


def load(path):
    tree = etree.parse(path)
    return tree, tree.getroot().find("Score")


def save(tree, path):
    tree.write(path, xml_declaration=True, encoding="UTF-8")


def staff(score, sid):
    return next(s for s in score.findall("Staff") if s.get("id") == str(sid))


def bar(score, sid, n):
    return staff(score, sid).findall("Measure")[n - 1]


def dur(el):
    """Written duration (dots included, tuplet ratio not) in whole notes."""
    if el.findtext("durationType") == "measure":
        return F(el.findtext("duration"))
    d = DUR[el.findtext("durationType")]
    dots = int(el.findtext("dots") or 0)
    return d * (2 - F(1, 2 ** dots))


def is_grace(el):
    return any(g.tag.startswith(GRACE) for g in el)


def _walk(voice):
    """(element, start, length) for every child of the voice; length 0 for non-notes and grace notes."""
    t, ratio, stack = F(0), F(1), []
    for c in voice:
        ln = F(0)
        if c.tag == "Tuplet":
            stack.append(ratio)
            ratio *= F(int(c.findtext("normalNotes")), int(c.findtext("actualNotes")))
        elif c.tag == "endTuplet":
            ratio = stack.pop() if stack else F(1)
        elif c.tag in ("Chord", "Rest") and not is_grace(c):
            ln = dur(c) * ratio
        elif c.tag == "MeasureRepeat" and c.findtext("duration"):
            ln = F(c.findtext("duration"))
        yield c, t, ln
        t += F(c.findtext("fractions") or 0) if c.tag == "location" else ln


def timeline(voice):
    """[(element, start position)] for every child of the voice: chords / rests advance by duration x tuplet ratio,
    grace notes take no time, a voice-level <location> moves the cursor (MuseScore writes them around elements that
    sit between notes)."""
    return [(c, t) for c, t, _ in _walk(voice)]


def voice_len(voice):
    """End of the last chord / rest of the voice (whole notes)."""
    return max((t + ln for c, t, ln in _walk(voice) if c.tag in ("Chord", "Rest", "MeasureRepeat")), default=F(0))


def part_of(score, sid):
    """The <Part> that owns staff sid (MuseScore 4 numbers staves 1, 2, ... in part order)."""
    n = 0
    for p in score.findall("Part"):
        n += len(p.findall("Staff"))
        if int(sid) <= n:
            return p
    return None


def transposition(score, sid):
    """(chromatic, diatonic) from written to concert pitch of the staff's instrument, e.g. Horn in F (-7, -4)."""
    p = part_of(score, sid)
    i = p.find("Instrument") if p is not None else None
    if i is None:
        return 0, 0
    return int(i.findtext("transposeChromatic") or 0), int(i.findtext("transposeDiatonic") or 0)


def drum_map(score, sid):
    """{drum name: (pitch, head)} of a drum staff ({} for pitched staves)."""
    p = part_of(score, sid)
    return {} if p is None else {d.findtext("name"): (int(d.get("pitch")), d.findtext("head")) for d in p.iter("Drum")}


def bar_len(score, sid, n):
    """Length of bar n in whole notes: <Measure len> or the time signature in force."""
    sig = F(1)
    for i, m in enumerate(staff(score, sid).findall("Measure"), 1):
        for ts in m.iter("TimeSig"):
            sig = F(int(ts.findtext("sigN")), int(ts.findtext("sigD")))
        if i == n:
            return F(m.get("len")) if m.get("len") else sig
    raise IndexError(f"staff {sid} has no bar {n}")


def insert_at(voice, pos, el, after=False):
    """Put el at position pos of the voice: before the chord / rest starting there; with after=True (or when none
    starts there) after the one ending there; otherwise inside the covering chord's time with a <location> cursor
    move before and after it, the way MuseScore writes it."""
    notes = [(c, t, ln) for c, t, ln in _walk(voice) if c.tag in ("Chord", "Rest")]
    start = next((c for c, t, ln in notes if t == pos), None)
    end = next((c for c, t, ln in reversed(notes) if t + ln == pos and ln), None)
    if start is not None and not (after and end is not None):
        start.addprevious(el)
        return
    if end is not None:
        end.addnext(el)
        return
    cov = next(((c, t) for c, t, ln in notes if t < pos < t + ln), None)
    if cov is None:
        raise ValueError(f"no chord/rest at {pos}")
    c, t = cov
    for x in (_move(pos - t), el, _move(t - pos)):
        c.addprevious(x)


def _move(frac):
    m = etree.Element("location")
    E(m, "fractions").text = str(frac)
    return m


def loc(parent, tag, measures, frac, voices=0):
    w = E(parent, tag)
    l = E(w, "location")
    if voices:
        E(l, "voices").text = str(voices)
    if measures:
        E(l, "measures").text = str(measures)
    if frac:
        E(l, "fractions").text = str(frac)


def spanner_ends(score, sid, kind="HairPin"):
    """[(start Spanner, bar, pos), ...] and the same for ends."""
    starts, ends = [], []
    for i, m in enumerate(staff(score, sid).findall("Measure"), 1):
        for v in m.findall("voice"):
            for c, t in timeline(v):
                if c.tag == "Spanner" and c.get("type") == kind:
                    (starts if c.find("next") is not None else ends).append((c, i, t))
    return starts, ends


def del_hairpin(score, sid, b, pos=None):
    """Delete the hairpin starting in bar b (at pos, if given) and the end marker at exactly its end position."""
    return del_spanner(score, sid, "HairPin", b, pos)


def add_hairpin(score, sid, start, end, cresc=True, end_after=True):
    (sb, sp), (eb, ep) = start, end
    s = etree.Element("Spanner", type="HairPin")
    h = E(s, "HairPin")
    E(h, "subtype").text = "0" if cresc else "1"
    loc(s, "next", eb - sb, ep - sp)
    insert_at(bar(score, sid, sb).find("voice"), sp, s)
    e = etree.Element("Spanner", type="HairPin")
    loc(e, "prev", sb - eb, sp - ep)
    v = bar(score, sid, eb).find("voice")
    if ep == 0:
        v.insert(0, e)
    else:
        try:
            insert_at(v, ep, e)
        except ValueError:
            insert_at(v, ep, e, after=True)


def add_dynamic(score, sid, b, pos, sub):
    d = etree.Element("Dynamic")
    E(d, "subtype").text = sub
    insert_at(bar(score, sid, b).find("voice"), pos, d)


def add_text(score, sid, b, pos, text, kind="SystemText"):
    """Text at bar b, pos (Fraction of a whole note): SystemText (tempo headings, "Attacca": on the top staff),
    StaffText (expression words) or PlayTechAnnotation (playing words: "pizz.", "gedämpft")."""
    el = etree.Element(kind)
    E(el, "text").text = text
    insert_at(bar(score, sid, b).find("voice"), pos, el)
    return el


def del_dynamics(score, sid, b, subs=None):
    for d in bar(score, sid, b).iter("Dynamic"):
        if subs is None or d.findtext("subtype") in subs:
            d.getparent().remove(d)


def artic(chord, sub):
    a = etree.Element("Articulation")
    E(a, "subtype").text = sub
    chord.find("Note").addprevious(a)


def chords(score, sid, b):
    return bar(score, sid, b).find("voice").findall("Chord")


def spanners(score, sid, kind):
    """[(Spanner, bar, pos, is_start)] of one kind on a staff, at voice level and inside chords / notes."""
    out = []
    for i, m in enumerate(staff(score, sid).findall("Measure"), 1):
        for v in m.findall("voice"):
            for c, t in timeline(v):
                for s in ([c] if c.tag == "Spanner" else c.iter("Spanner") if c.tag == "Chord" else []):
                    if s.get("type") == kind:
                        out.append((s, i, t, s.find("next") is not None))
    return out


def del_spanner(score, sid, kind, b, pos=None):
    """Delete the spanner of this kind starting in bar b (at pos, if given) and its matching end."""
    sp = spanners(score, sid, kind)
    s, sb, st, _ = next(x for x in sp if x[3] and x[1] == b and (pos is None or x[2] == pos))
    l = s.find("next/location")
    eb, ep = sb + int(l.findtext("measures") or 0), st + F(l.findtext("fractions") or 0)
    for e, b2, t2, start in sp:
        if not start and b2 == eb and t2 == ep:
            e.getparent().remove(e)
            break
    s.getparent().remove(s)
    return eb, ep


def add_arpeggio(chord, sub="0"):
    """Arpeggio (subtype 0 = plain wavy line) after the chord's notes, as the truths write it."""
    a = E(chord, "Arpeggio")
    E(a, "subtype").text = sub
    return a


def del_artics(chord, subs=None):
    for a in chord.findall("Articulation"):
        if subs is None or a.findtext("subtype") in subs:
            chord.remove(a)


def _chord_pos(score, sid, b, idx):
    """(chord, position) of the idx-th Chord in voice 1 of bar b (negative idx counts from the end)."""
    cs = [(c, t) for c, t in timeline(bar(score, sid, b).find("voice")) if c.tag == "Chord"]
    return cs[idx]


def add_tie(score, sid, b, idx, b2=None, idx2=None, vi=0):
    """Tie every note of chord idx (voice vi) in bar b to the same pitches in the next chord (same bar, else the
    first chord of the next bar), or in chord idx2 of bar b2."""
    v1 = bar(score, sid, b).findall("voice")[vi]
    cs = [c for c in v1 if c.tag == "Chord" and not is_grace(c)]
    c1 = cs[idx]
    if b2 is None and idx2 is None and cs.index(c1) + 1 < len(cs):
        b2, c2, v2 = b, cs[cs.index(c1) + 1], v1
    else:
        b2 = b + 1 if b2 is None else b2
        v2 = bar(score, sid, b2).findall("voice")[vi]
        c2 = [c for c in v2 if c.tag == "Chord" and not is_grace(c)][idx2 or 0]
    _tie_chords(score, sid, (b, c1), (b2, c2), v1, v2)


def add_slur(score, sid, start, end):
    """Slur from chord (bar, idx) to chord (bar, idx); MuseScore 4 keeps slurs inside the chords."""
    (c1, p1), (c2, p2) = _chord_pos(score, sid, *start), _chord_pos(score, sid, *end)
    (b1, _), (b2, _) = start, end
    s = etree.Element("Spanner", type="Slur")
    E(s, "Slur")
    loc(s, "next", b2 - b1, p2 - p1)
    c1.find("Note").addprevious(s)
    e = etree.Element("Spanner", type="Slur")
    loc(e, "prev", b1 - b2, p1 - p2)
    c2.find("Note").addprevious(e)


def set_lyric(chord, text, syllabic=None):
    """Set (or add) the verse-1 lyric of a chord; syllabic: None/single, begin, middle, end."""
    ly = next((l for l in chord.findall("Lyrics") if not l.findtext("no")), None)
    if ly is None:
        ly = etree.Element("Lyrics")
        after = [c for c in chord if c.tag in ("eid", "durationType", "dots", "duration")]
        (after[-1].addnext(ly) if after else chord.insert(0, ly))
    for t in ("syllabic", "text"):
        if ly.find(t) is not None:
            ly.remove(ly.find(t))
    if syllabic and syllabic != "single":
        ly.insert(0, etree.Element("syllabic"))
        ly.find("syllabic").text = syllabic
    E(ly, "text").text = text


def self_test():
    """assert-based check of add_tie / add_slur / set_lyric on a tiny two-bar staff."""
    xml = ("<museScore><Score><Staff id='1'>" + "<Measure><voice><Chord><durationType>half</durationType><dots>1</dots>"
           "<Note><pitch>60</pitch></Note></Chord></voice></Measure>" * 2 + "</Staff></Score></museScore>")
    score = etree.fromstring(xml).find("Score")
    add_tie(score, 1, 1, 0)
    add_slur(score, 1, (1, 0), (2, 0))
    c1, c2 = chords(score, 1, 1)[0], chords(score, 1, 2)[0]
    assert c1.findtext("Note/Spanner/next/location/measures") == "1"
    assert c2.findtext("Note/Spanner/prev/location/measures") == "-1"
    assert c1.find("Spanner[@type='Slur']/next") is not None and c2.find("Spanner[@type='Slur']/prev") is not None
    set_lyric(c1, "Ah")
    set_lyric(c1, "Ah", "begin")
    assert [l.findtext("text") for l in c1.findall("Lyrics")] == ["Ah"] and c1.findtext("Lyrics/syllabic") == "begin"
    add_text(score, 1, 2, 0, "Attacca")
    assert bar(score, 1, 2).find("voice")[0].findtext("text") == "Attacca"


def mk_rest(d="quarter", dots=0, measure=None):
    """Rest element; measure='3/4' gives a whole-bar rest."""
    r = etree.Element("Rest")
    if measure:
        E(r, "durationType").text = "measure"
        E(r, "duration").text = measure
        return r
    if dots:
        E(r, "dots").text = str(dots)
    E(r, "durationType").text = d
    return r


def mk_chord(pitches, d="quarter", dots=0, trem=None, artics=(), head=None):
    """Chord of (pitch, tpc) notes; trem = TremoloSingleChord subtype (e.g. 'r32'), head = notehead name."""
    c = etree.Element("Chord")
    if dots:
        E(c, "dots").text = str(dots)
    E(c, "durationType").text = d
    for a in artics:
        E(E(c, "Articulation"), "subtype").text = a
    for p, tpc in pitches:
        n = E(c, "Note")
        E(n, "pitch").text = str(p)
        E(n, "tpc").text = str(tpc)
        if head:
            E(n, "head").text = head
    if trem:
        E(E(c, "TremoloSingleChord"), "subtype").text = trem
    return c


def set_bar(score, sid, n, items):
    """Replace voice 1 of bar n by items (Chord / Rest elements); keeps header clef / key / time, StaffText and the
    barline, drops old notes, dynamics, fermatas and spanners (run drop_orphans afterwards for their other ends)."""
    v = bar(score, sid, n).find("voice")
    for c in list(v):
        if c.tag in ("Chord", "Rest", "Dynamic", "Spanner", "Fermata", "Tuplet", "endTuplet"):
            v.remove(c)
    bl = v.find("BarLine")
    for it in items:
        (bl.addprevious(it) if bl is not None else v.append(it))


def drop_orphans(score, sid, kind):
    """Remove spanner starts / ends of this kind (HairPin, Tie, Slur) on a staff whose partner is gone."""
    def tgt(s, b, t, tag):
        l = s.find(tag + "/location")
        return b + int(l.findtext("measures") or 0), t + F(l.findtext("fractions") or 0)
    sp = [x for x in spanners(score, sid, kind) if x[0].find(".//staves") is None]   # other staff: not checkable here
    pairs_s = {((b, t), tgt(s, b, t, "next")) for s, b, t, st in sp if st}
    pairs_e = {(tgt(s, b, t, "prev"), (b, t)) for s, b, t, st in sp if not st}
    gone = 0
    for s, b, t, st in sp:
        if (((b, t), tgt(s, b, t, "next")) if st else (tgt(s, b, t, "prev"), (b, t))) not in (pairs_e if st else pairs_s):
            s.getparent().remove(s)
            gone += 1
    return gone


def add_fermata(score, sid, b, pos, sub="fermataAbove"):
    """Fermata on the chord / rest starting at pos in bar b (written before it, as MuseScore does)."""
    f = etree.Element("Fermata")
    E(f, "subtype").text = sub
    insert_at(bar(score, sid, b).find("voice"), pos, f)


STEP_TPC = {"F": 13, "C": 14, "G": 15, "D": 16, "A": 17, "E": 18, "B": 19}
STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pc(name):
    """'F#4' / 'Bb3' / 'Cbb5' / 'E4' -> (MIDI pitch, tpc) (concert pitch: transposing parts need tpc2 too)."""
    step, acc, octv = name[0], name[1:-1], int(name[-1])
    alt = acc.count("#") - acc.count("b")
    return 12 * (octv + 1) + STEP_PC[step] + alt, STEP_TPC[step] + 7 * alt


SHARP_TPC = [14, 21, 16, 23, 18, 13, 20, 15, 22, 17, 24, 19]   # default spelling of a pitch class (drums)


def make_chord(notes, dtype, dots=0, trans=(0, 0), drums=None):
    """Chord of WRITTEN note names ('F#4', ...) or a Rest when notes is empty. trans = transposition(score, sid):
    <pitch> / <tpc> become concert pitch and <tpc2> keeps the written spelling. drums = drum_map(): names
    ('Acoustic_Snare') instead of pitches."""
    c = etree.Element("Chord" if notes else "Rest")
    if dots:
        E(c, "dots").text = str(dots)
    E(c, "durationType").text = dtype
    ch, di = trans
    for n in notes:
        ne = E(c, "Note")
        if drums is not None:
            pitch, head = drums[n.replace("_", " ")]
            E(ne, "pitch").text = str(pitch)
            E(ne, "tpc").text = str(SHARP_TPC[pitch % 12])
            if head and head not in ("normal", "0"):
                E(ne, "head").text = head
            continue
        p, t = pc(n)
        E(ne, "pitch").text = str(p + ch)
        E(ne, "tpc").text = str(t + 7 * ch - 12 * di)
        if (ch, di) != (0, 0):
            E(ne, "tpc2").text = str(t)
    return c


DTYPE = {"0": "breve", "1": "whole", "2": "half", "4": "quarter", "8": "eighth", "16": "16th", "32": "32nd",
         "64": "64th"}


def parse_items(text, trans=(0, 0), drums=None, measure=None):
    """'F#4/8 C#4+A3/4. r/8 3:2{ D4/8 E4/8 F4/8 } G4/2~ grace:A4/8 rM' -> elements. '/4.' = dotted, '~' = tie the
    chord to the next one (applied by set_voice), 'n:m{' ... '}' = tuplet, 'grace:' = acciaccatura before the next
    chord, 'rM' = whole-bar rest (measure = bar length as 'N/D')."""
    out, ties, tup = [], [], None
    for tok in text.split():
        if tok == "}":
            group = out[out.index(tup) + 1:]
            base = sum((dur(c) for c in group if not is_grace(c)), F(0)) / int(tup.findtext("actualNotes"))
            names = {v: k for k, v in DUR.items()}
            if base not in names:
                raise ValueError(f"tuplet {tup.findtext('actualNotes')}:{tup.findtext('normalNotes')} of {base}: "
                                 "no plain base note value")
            E(tup, "baseNote").text = names[base]
            num = E(tup, "Number")
            E(num, "style").text = "tuplet"
            E(num, "text").text = tup.findtext("actualNotes")
            out.append(etree.Element("endTuplet"))
            tup = None
            continue
        if tok.endswith("{"):
            n, m = tok[:-1].split(":")
            tup = etree.Element("Tuplet")
            E(tup, "normalNotes").text = m
            E(tup, "actualNotes").text = n
            out.append(tup)
            continue
        if tok == "rM":
            out.append(mk_rest(measure=measure or "4/4"))
            continue
        grace = tok.startswith("grace:")
        tok = tok.removeprefix("grace:")
        tie = tok.endswith("~")
        notes, d = tok.rstrip("~").split("/")
        dots = d.count(".")
        el = make_chord([] if notes == "r" else notes.split("+"), DTYPE[d.rstrip(".")], dots, trans, drums)
        if grace:
            el.insert(0, etree.Element("acciaccatura"))
        if tie:
            ties.append(el)
        out.append(el)
    if tup is not None:
        raise ValueError("tuplet without closing '}'")
    return out, ties


def set_voice(score, sid, b, text, vi=0):
    """Replace the chords / rests / beams / tuplets of voice vi (0-based; created if missing) in bar b by
    parse_items(text) (written pitch). Other children (dynamics, hairpin ends, clefs, texts) keep their positions.
    Checks everything before changing the score: refuses a voice 1 that does not fill the bar, any voice that
    overfills it, a tie onto a rest, and a removed chord that still carries a tie / slur / glissando (delete it
    first: del_spanner, or drop the tie on its partner)."""
    m = bar(score, sid, b)
    ln = bar_len(score, sid, b)
    items, ties = parse_items(text, transposition(score, sid), drum_map(score, sid) or None,
                              f"{ln.numerator}/{ln.denominator}")
    probe = etree.Element("voice")
    probe.extend(items)
    got = voice_len(probe)
    if (vi == 0 and got != ln) or got > ln:
        raise ValueError(f"staff {sid} bar {b}: voice fills {got} of {ln} (whole notes)")
    timed = [c for c in probe if c.tag in ("Chord", "Rest") and not is_grace(c)]
    for c in ties:
        k = timed.index(c)
        if k + 1 < len(timed) and timed[k + 1].tag == "Rest":
            raise ValueError(f"staff {sid} bar {b}: '~' before a rest")
    vs = m.findall("voice")
    v = vs[vi] if len(vs) > vi else None
    old = [c for c in v if c.tag in ("Chord", "Rest", "Beam", "Tuplet", "endTuplet", "location")] if v is not None else []
    if any(c.find(".//Spanner") is not None for c in old):
        raise ValueError(f"staff {sid} bar {b}: a chord to replace carries a tie / slur; delete it first")
    if ties and timed[-1] in ties:
        nxt = None
        if b < len(staff(score, sid).findall("Measure")):
            nvs = bar(score, sid, b + 1).findall("voice")
            nxt = next((x for x in nvs[vi] if x.tag in ("Chord", "Rest") and not is_grace(x)), None) \
                if len(nvs) > vi else None
        if nxt is None or nxt.tag != "Chord":
            raise ValueError(f"staff {sid} bar {b}: tie into bar {b + 1}, which has no chord there yet: write it first")
    # all checks passed: change the score
    while len(vs) <= vi:
        vs[-1].addnext(etree.Element("voice"))
        vs = m.findall("voice")
    v = vs[vi]
    keep = [(c, t) for c, t in timeline(v) if c not in old and c.tag not in ("BarLine",)]
    for c in list(v):
        if c.tag != "BarLine":
            v.remove(c)
    tail = v.find("BarLine")
    for el in items:
        (tail.addprevious(el) if tail is not None else v.append(el))
    for c, t in keep:                       # markings back at their old positions
        if t == 0:
            first = next((x for x in v if x.tag in ("Chord", "Rest", "Tuplet")), None)
            (first.addprevious(c) if first is not None else v.insert(0, c))
        else:
            insert_at(v, t, c)
    for c in ties:
        k = timed.index(c)
        if k + 1 < len(timed):
            _tie_chords(score, sid, (b, c), (b, timed[k + 1]), v, v)
        else:
            nv = bar(score, sid, b + 1).findall("voice")[vi]
            nxt = next(x for x in nv if x.tag == "Chord" and not is_grace(x))
            _tie_chords(score, sid, (b, c), (b + 1, nxt), v, nv)
    return v


def _tie_chords(score, sid, a, z, va, vz):
    """Tie every note of chord a=(bar, Chord) to the note of the same pitch in z=(bar, Chord)."""
    (b1, c1), (b2, c2) = a, z
    p1 = next(t for c, t in timeline(va) if c is c1)
    p2 = next(t for c, t in timeline(vz) if c is c2)
    for n1 in c1.findall("Note"):
        n2 = next((n for n in c2.findall("Note") if n.findtext("pitch") == n1.findtext("pitch")), None)
        if n2 is None:
            raise ValueError(f"staff {sid} bar {b1}: no pitch {n1.findtext('pitch')} to tie to in bar {b2}")
        if n1.find("Spanner[@type='Tie']/next") is not None:
            continue
        s = etree.Element("Spanner", type="Tie")
        E(s, "Tie")
        loc(s, "next", b2 - b1, p2 - p1)
        n1.find("pitch").addprevious(s)
        e = etree.Element("Spanner", type="Tie")
        loc(e, "prev", b1 - b2, p1 - p2)
        n2.find("pitch").addprevious(e)


def add_slur_voice(score, sid, start, end, vi=0, kind="Slur"):
    """Slur from chord index start=(bar, i) to end=(bar, i) of voice vi, in the chord-internal form of this file."""
    (b1, i1), (b2, i2) = start, end
    def at(b, i):
        v = bar(score, sid, b).findall("voice")[vi]
        tl = [(c, t) for c, t in timeline(v) if c.tag == "Chord"]
        return tl[i]
    (c1, t1), (c2, t2) = at(b1, i1), at(b2, i2)
    s = etree.Element("Spanner", type=kind)
    E(s, kind)
    loc(s, "next", b2 - b1, t2 - t1)
    c1.find("Note").addprevious(s)
    e = etree.Element("Spanner", type=kind)
    loc(e, "prev", b1 - b2, t1 - t2)
    c2.find("Note").addprevious(e)


def add_barline(score, sid, b, sub="double"):
    v = bar(score, sid, b).find("voice")
    bl = E(v, "BarLine")
    E(bl, "subtype").text = sub


def tie_note(score, sid, b, idx, pitch, b2=None, idx2=0, vi=0, vi2=None):
    """Tie one note (MIDI pitch) of chord idx (voice vi) in bar b to the same pitch in chord idx2 of bar b2."""
    b2 = b + 1 if b2 is None else b2
    vi2 = vi if vi2 is None else vi2
    def at(bb, i, v):
        return [(c, t) for c, t in timeline(bar(score, sid, bb).findall("voice")[v]) if c.tag == "Chord"][i]
    (c1, p1), (c2, p2) = at(b, idx, vi), at(b2, idx2, vi2)
    n1 = next(n for n in c1.findall("Note") if n.findtext("pitch") == str(pitch))
    n2 = next(n for n in c2.findall("Note") if n.findtext("pitch") == str(pitch))
    s = etree.Element("Spanner", type="Tie")
    E(s, "Tie")
    loc(s, "next", b2 - b, p2 - p1, vi2 - vi)
    n1.find("pitch").addprevious(s)
    e = etree.Element("Spanner", type="Tie")
    loc(e, "prev", b - b2, p1 - p2, vi - vi2)
    n2.find("pitch").addprevious(e)


def add_gliss(score, sid, start, end, sub="1", sid2=None):
    """Glissando (subtype 1 = wavy, 0 = straight) from note start=(bar, voice idx, chord idx, pitch) to end=(...),
    also across voices (<voices>) or, with sid2, to a note on another staff of the part (<staves>); <notes> = note
    index difference. Pitches are concert MIDI."""
    sid2 = sid if sid2 is None else sid2
    def at(st, b, v, i, p):
        c, t = [(c, t) for c, t in timeline(bar(score, st, b).findall("voice")[v]) if c.tag == "Chord"][i]
        ns = c.findall("Note")
        k = next(j for j, n in enumerate(ns) if n.findtext("pitch") == str(p))
        return ns[k], t, k
    (b1, v1, _, _), (b2, v2, _, _) = start, end
    (n1, t1, k1), (n2, t2, k2) = at(sid, *start), at(sid2, *end)
    def mk(tag, sign):
        s = etree.Element("Spanner", type="Glissando")
        if sign > 0:
            g = E(s, "Glissando")
            E(g, "subtype").text = sub
            E(g, "diagonal").text = "1"
        w = E(E(s, tag), "location")
        for name, val in (("staves", int(sid2) - int(sid)), ("voices", v2 - v1), ("measures", b2 - b1),
                          ("fractions", t2 - t1), ("notes", k2 - k1)):
            if val:
                E(w, name).text = str(sign * val)
        return s
    n1.find("pitch").addprevious(mk("next", 1))
    n2.find("pitch").addprevious(mk("prev", -1))
