"""MusicXML I/O and event extraction shared by all metrics.

Everything works on `score-partwise` lxml trees. `.mxl` containers and timewise
files are normalised on load.
"""
from __future__ import annotations

import copy
import re
import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from lxml import etree

MUSICXML_SUFFIXES = (".musicxml", ".xml", ".mxl")

_PARSER = etree.XMLParser(remove_blank_text=True, recover=True, resolve_entities=False,
                          no_network=True, huge_tree=True)


def load(path: Path) -> etree._Element:
    """Return the <score-partwise> root of a .musicxml/.xml/.mxl file."""
    path = Path(path)
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            inner = None
            if "META-INF/container.xml" in names:
                c = etree.fromstring(z.read("META-INF/container.xml"), _PARSER)
                rf = c.find(".//{*}rootfile")
                if rf is not None:
                    inner = rf.get("full-path")
            if inner is None:
                inner = next(n for n in names
                             if n.endswith((".xml", ".musicxml")) and not n.startswith("META-INF"))
            data = z.read(inner)
    else:
        data = path.read_bytes()
    root = etree.fromstring(data, _PARSER)
    _strip_ns(root)
    if root.tag == "score-timewise":
        root = _timewise_to_partwise(root)
    if root.tag != "score-partwise":
        raise ValueError(f"{path}: not a MusicXML score (root <{root.tag}>)")
    return root


def write(root: etree._Element, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doctype = ('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
               '"http://www.musicxml.org/dtds/partwise.dtd">')
    path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                    doctype=doctype, pretty_print=True))


def _strip_ns(root: etree._Element) -> None:
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.startswith("{"):
            el.tag = el.tag.split("}", 1)[1]


def _timewise_to_partwise(tw: etree._Element) -> etree._Element:
    pw = etree.Element("score-partwise", version=tw.get("version", "4.0"))
    for child in tw:
        if child.tag != "measure":
            pw.append(copy.deepcopy(child))
    parts: dict[str, etree._Element] = {}
    for sp in tw.iterfind("part-list/score-part"):
        parts[sp.get("id")] = etree.SubElement(pw, "part", id=sp.get("id"))
    for m in tw.iterfind("measure"):
        for p in m.iterfind("part"):
            if p.get("id") not in parts:
                parts[p.get("id")] = etree.SubElement(pw, "part", id=p.get("id"))
            dst = parts[p.get("id")]
            nm = etree.SubElement(dst, "measure", dict(m.attrib))
            for c in p:
                nm.append(copy.deepcopy(c))
    return pw


def merge_pages(roots: list[etree._Element]) -> etree._Element:
    """Concatenate per-page scores (homr/oemer output) into one score.

    Parts are matched by index. Pages with more parts than the first page add new
    parts padded with nothing (they simply start later). Measures are renumbered.
    """
    if not roots:
        raise ValueError("no pages to merge")
    out = copy.deepcopy(roots[0])
    out_parts = out.findall("part")
    part_list = out.find("part-list")
    for page in roots[1:]:
        for i, p in enumerate(page.findall("part")):
            if i >= len(out_parts):
                new_id = f"P{len(out_parts) + 1}"
                sp = page.findall("part-list/score-part")
                if part_list is not None and i < len(sp):
                    sp_copy = copy.deepcopy(sp[i])
                    sp_copy.set("id", new_id)
                    part_list.append(sp_copy)
                np_ = etree.SubElement(out, "part", id=new_id)
                out_parts.append(np_)
            dst = out_parts[i]
            for m in p.findall("measure"):
                dst.append(copy.deepcopy(m))
    for p in out_parts:
        for n, m in enumerate(p.findall("measure"), start=1):
            m.set("number", str(n))
    return out


def _rename_ids(el: etree._Element, old: str, new: str) -> None:
    for e in el.iter():
        v = e.get("id")
        if v is not None and (v == old or v.startswith(old + "-")):
            e.set("id", new + v[len(old):])


def merge_parts(roots: list[etree._Element]) -> etree._Element:
    """Stack the parts of several scores (e.g. per-instrument GT exports) into one score.

    Header (work, identification, defaults) comes from the first score. Part ids are
    renumbered P1..Pn in the given order. System text (tempo, rall. ...; MuseScore marks
    it system="only-top"/"also-top" and repeats it in every part export) is kept only in
    the first part, as printed.
    """
    if not roots:
        raise ValueError("no scores to merge")
    out = copy.deepcopy(roots[0])
    part_list = out.find("part-list")
    for el in list(part_list) + out.findall("part"):
        el.getparent().remove(el)
    k = 0
    for r in roots:
        parts = {p.get("id"): p for p in r.findall("part")}
        for sp in r.iterfind("part-list/score-part"):
            old = sp.get("id")
            k += 1
            new = f"P{k}"
            sp, part = copy.deepcopy(sp), copy.deepcopy(parts[old])
            _rename_ids(sp, old, new)
            _rename_ids(part, old, new)
            if k > 1:
                for d in part.findall("measure/direction"):
                    if d.get("system") in ("only-top", "also-top"):
                        d.getparent().remove(d)
            part_list.append(sp)
            out.append(part)
    return out


PLAY_WORDS = re.compile(r"pizz|arco|gedämpft|offen|\bdiv|unis|\bsul\b|solo|tutti|sord|col legno|harm|^zu ", re.I)
KEEP_DIRECTIONS = {"rehearsal", "segno", "coda", "octave-shift"}


def slurs_to_ties(root: etree._Element) -> int:
    """A slur from a note to the next note of the same pitch (same staff and voice) is a tie (truth
    convention, user 2026-10-16: a slur only joins different pitches). Returns how many were turned."""
    turned = 0
    for part in root.iter("part"):
        last: dict[tuple, etree._Element] = {}
        for n in part.iter("note"):
            if n.find("rest") is not None or n.find("chord") is not None or n.find("grace") is not None:
                continue
            key = (n.findtext("staff") or "1", n.findtext("voice") or "1")
            a, last[key] = last.get(key), n
            p, q = (x.find("pitch") if x is not None else None for x in (a, n))
            if p is None or q is None or [p.findtext(k) or "0" for k in ("step", "alter", "octave")] != \
                    [q.findtext(k) or "0" for k in ("step", "alter", "octave")]:
                continue
            for s in a.findall("notations/slur[@type='start']"):
                stop = n.find(f"notations/slur[@type='stop'][@number='{s.get('number', '1')}']")
                if stop is None and s.get("number") is None:
                    stop = n.find("notations/slur[@type='stop']")
                if stop is None or a.find("notations/tied[@type='start']") is not None:
                    continue
                for el, typ, sl in ((a, "start", s), (n, "stop", stop)):
                    nt = sl.getparent()
                    nt.replace(sl, etree.Element("tied", type=typ))
                    tie = etree.Element("tie", type=typ)
                    anchor = el.find("duration")
                    if anchor is not None:
                        anchor.addnext(tie)
                turned += 1
                break
    return turned


def _pitch_key(n: etree._Element) -> tuple:
    p = n.find("pitch")
    return tuple(p.findtext(k) or "0" for k in ("step", "alter", "octave")) if p is not None else ()


def _add_tie(n: etree._Element, typ: str) -> None:
    if n.find(f"notations/tied[@type='{typ}']") is not None:
        return
    nt = n.find("notations")
    if nt is None:
        nt = etree.SubElement(n, "notations")
    nt.append(etree.Element("tied", type=typ))
    anchor = (n.findall("tie") or n.findall("duration") or [None])[-1]
    if anchor is not None:
        anchor.addnext(etree.Element("tie", type=typ))


def tie_held_chords(root: etree._Element) -> int:
    """A chord tied to the next chord of exactly the same pitches (same staff and voice) gets a tie
    on every note: a reader often ties only one, and the untied notes would be played again (user
    2026-10-18). Returns how many ties were added."""
    added = 0
    for part in root.iter("part"):
        seq: dict[tuple, list[list]] = {}       # (staff, voice) -> its chords in order
        for n in part.iter("note"):
            if n.find("grace") is not None:
                continue
            key = (n.findtext("staff") or "1", n.findtext("voice") or "1")
            if n.find("chord") is not None and seq.get(key):
                seq[key][-1].append(n)
            else:
                seq.setdefault(key, []).append([n])
        for chords in seq.values():
            for a, b in zip(chords, chords[1:]):
                if len(a) < 2 or any(x.find("rest") is not None for x in a + b) \
                        or not any(x.find("notations/tied[@type='start']") is not None for x in a):
                    continue
                pa = sorted(map(_pitch_key, a))
                if pa != sorted(map(_pitch_key, b)) or len(set(pa)) != len(pa):
                    continue
                by_pitch = {_pitch_key(x): x for x in b}
                for x in a:
                    if x.find("notations/tied[@type='start']") is None:
                        _add_tie(x, "start")
                        _add_tie(by_pitch[_pitch_key(x)], "stop")
                        added += 1
    return added


def _starts(part: etree._Element):
    """(bar index, onset in quarters, note) for every first note of a chord and every rest."""
    div = 1
    for bi, m in enumerate(part.findall("measure")):
        pos = Fraction(0)
        for el in m:
            if el.tag == "attributes" and el.findtext("divisions"):
                div = int(el.findtext("divisions"))
            elif el.tag in ("backup", "forward"):
                d = Fraction(int(el.findtext("duration") or 0), div)
                pos += d if el.tag == "forward" else -d
            elif el.tag == "note" and el.find("grace") is None:
                if el.find("chord") is not None:
                    continue
                yield bi, pos, el
                pos += Fraction(int(el.findtext("duration") or 0), div)


def share_fermatas(parts: list[etree._Element], bars: int | None = None) -> int:
    """A fermata that at least half of the parts with a note or rest starting at that bar and beat
    have goes onto the others (the readers miss many, mostly over rests; user 2026-10-18). Returns
    how many were added. Only parts with the song's bar count `bars` (else the most common one) take
    part: an extra or missing bar would move the fermata."""
    counts = [len(p.findall("measure")) for p in parts]
    common = bars or max(set(counts), key=counts.count, default=0)
    parts = [p for p, c in zip(parts, counts) if c == common]
    have: dict[tuple, int] = {}
    starts = []
    for p in parts:
        s = {}
        for bi, on, el in _starts(p):
            s.setdefault((bi, on), el)
        starts.append(s)
        for k in {k for k, el in s.items() if el.find("notations/fermata") is not None}:
            have[k] = have.get(k, 0) + 1
    added = 0
    for k, n in have.items():
        present = [s[k] for s in starts if k in s]
        if 2 * n < len(present) or len(present) < 2:
            continue
        for el in present:
            if el.find("notations/fermata") is None:
                nt = el.find("notations")
                if nt is None:
                    nt = etree.Element("notations")
                    lyric = el.find("lyric")
                    (lyric.addprevious if lyric is not None else el.append)(nt)
                nt.append(etree.Element("fermata", type="upright"))
                added += 1
    return added


def strip_marks(part: etree._Element) -> None:
    """A "plain" part (workbook column `plain`): notes with their dots, ties, tuplets and tremolos
    only. Articulations (staccato, accents), dynamics, hairpins, slurs, fermatas, ornaments,
    tempo marks and expression text go; playing words (pizz., Arco, gedämpft), rehearsal marks,
    navigation and 8va lines stay."""
    for nt in list(part.iter("notations")):
        for el in list(nt):
            if el.tag == "ornaments":
                for o in [o for o in el if o.tag != "tremolo"]:
                    el.remove(o)
            if el.tag not in ("tied", "tuplet") and not (el.tag == "ornaments" and len(el)):
                nt.remove(el)
        if not len(nt):
            nt.getparent().remove(nt)
    for d in list(part.iter("direction")):
        for dt in d.findall("direction-type"):
            for el in list(dt):
                if el.tag not in KEEP_DIRECTIONS and not (el.tag == "words" and PLAY_WORDS.search(
                        "".join(w.text or "" for w in dt.findall("words")))):
                    dt.remove(el)
            if not len(dt):
                d.remove(dt)
        if d.find("direction-type") is None:
            d.getparent().remove(d)


def drop_measures(root: etree._Element, numbers: list) -> list[str]:
    """Remove measures by their `number` attribute from every part. Returns warnings."""
    wanted = {str(n) for n in numbers}
    found: set[str] = set()
    warnings = []
    for part in root.findall("part"):
        for m in part.findall("measure"):
            num = m.get("number")
            if num not in wanted:
                continue
            found.add(num)
            for a in m.findall("attributes"):
                if any(a.find(t) is not None for t in ("divisions", "key", "time", "clef", "staves")):
                    warnings.append(f"dropped measure {num} of {part.get('id')} contained "
                                    "key/time/clef/divisions changes; they are lost")
            part.remove(m)
    for n in sorted(wanted - found):
        warnings.append(f"measure {n} to drop not found")
    return warnings


def _multirest_count(m: etree._Element) -> int:
    el = m.find("attributes/measure-style/multiple-rest")
    try:
        return int(el.text.strip()) if el is not None and el.text else 1
    except ValueError:
        return 1


def _rest_only(m: etree._Element) -> bool:
    notes = m.findall("note")
    return bool(notes) and all(n.find("rest") is not None for n in notes)


def _rest_copy(m: etree._Element, suffix: int) -> etree._Element:
    c = copy.deepcopy(m)
    for el in list(c):
        if el.tag not in ("note", "backup", "forward"):
            c.remove(el)
    c.set("number", f"{m.get('number', '')}.{suffix}")
    return c


def expand_multirests(root: etree._Element) -> list[int] | None:
    """Expand measures marked <multiple-rest>N into N whole-rest measures, in place.

    MuseScore stores a multi-measure rest as N real measures (the first carries the
    measure-style); some engines emit a single measure. Blocks already followed by
    N-1 rest-only measures are left alone. Returns old->new measure index map, or
    None if nothing changed.
    """
    parts = root.findall("part")
    measures = [p.findall("measure") for p in parts]
    n = max((len(ms) for ms in measures), default=0)
    index_map, offset = [], 0
    for i in range(n):
        index_map.append(i + offset)
        # a part's multirest is already expanded if its own next N-1 measures are rests
        # (other parts may hold notes there: MuseScore part exports merged into one score)
        counts = [(ms, _multirest_count(ms[i])) for ms in measures if i < len(ms)]
        if not any(kp > 1 and not (i + kp <= len(ms) and
                                   all(_rest_only(ms[i + j]) for j in range(1, kp)))
                   for ms, kp in counts):
            continue
        k = max(kp for _, kp in counts)
        for ms in measures:
            if i >= len(ms):
                continue
            src = ms[i]
            copies = [_rest_copy(src, j) for j in range(1, k)]
            for bl in src.findall("barline"):
                if bl.get("location", "right") == "right":
                    copies[-1].append(bl)
            anchor = src
            for c in copies:
                anchor.addnext(c)
                anchor = c
        offset += k - 1
    return index_map if offset else None


# --------------------------------------------------------------------------- events

CATEGORIES = [
    "notes",          # pitch + duration of pitched/unpitched notes
    "pitch",          # pitch only
    "rhythm",         # duration only (notes and rests)
    "rests",
    "clefs",
    "keys",
    "times",
    "dynamics",
    "hairpins",
    "articulations",
    "slurs",
    "ties",
    "lyrics",
    "words",          # tempo / expression text (<words>)
    "tempo",          # <metronome>
    "fermatas",       # on notes, rests and barlines
    "tuplets",        # tuplet start: actual:normal
    "tremolos",       # single-note and two-note tremolos with stroke count
    "instruments",    # instrument change (<instrument-change> or a mid-part <transpose>), position only
    "structure",      # repeats, voltas, segno / coda / D.S. / D.C. / fine / to coda
    "barlines",       # double / final / dashed ... barlines (not repeats)
    "rehearsal",      # rehearsal marks
    "chords",         # chord symbols (<harmony>)
    "multirest",      # multi-rest counts
    "systemtext",     # <words> marked system="only-top"/"also-top" (MuseScore system text: rit., a tempo)
]

_NAV = ("segno", "coda", "dacapo", "dalsegno", "fine", "tocoda")


@dataclass
class Staff:
    part_index: int
    part_name: str
    staff_no: int
    # category -> list of (measure_index, onset_quarters, token)
    events: dict[str, list[tuple[int, Fraction, str]]] = field(
        default_factory=lambda: {c: [] for c in CATEGORIES})
    # measure_index -> tuple of (onset, token) for notes+rests (content signature)
    measures: dict[int, list[tuple[Fraction, str]]] = field(default_factory=dict)
    n_measures: int = 0

    @property
    def label(self) -> str:
        return f"{self.part_name or 'P' + str(self.part_index + 1)}/s{self.staff_no}"

    def seq(self, cat: str) -> list[str]:
        """Tokens of one category in musical order (chords/voices normalised)."""
        return [t for _, _, t in sorted(self.events[cat], key=lambda e: (e[0], e[1], e[2]))]

    def measure_signatures(self) -> list[str]:
        return ["|".join(f"{o}:{t}" for o, t in sorted(self.measures.get(i, [])))
                for i in range(self.n_measures)]


_TYPE_Q = {"maxima": 32, "long": 16, "breve": 8, "whole": 4, "half": 2, "quarter": 1,
           "eighth": Fraction(1, 2), "16th": Fraction(1, 4), "32nd": Fraction(1, 8),
           "64th": Fraction(1, 16), "128th": Fraction(1, 32), "256th": Fraction(1, 64),
           "512th": Fraction(1, 128), "1024th": Fraction(1, 256)}


def _txt(el, path, default=None):
    x = el.find(path)
    return x.text.strip() if x is not None and x.text else default


_QUOTES = str.maketrans("‘’‚ʼ`“”„", "'''''\"\"\"")   # typographic quotes = plain ones (user, 2026-10-16)


def _norm_text(s: str) -> str:
    s = s.lower().replace(" ", " ").translate(_QUOTES)
    return re.sub(r"\s+", " ", s).strip()


def _alone_in_voice(note, measure) -> bool:
    key = (_txt(note, "voice", "1"), _txt(note, "staff", "1"))
    return all(n is note or (_txt(n, "voice", "1"), _txt(n, "staff", "1")) != key
               for n in measure.iterfind("note"))


def _duration_token(note, measure=None) -> str:
    rest = note.find("rest")
    typ = _txt(note, "type")
    dots = len(note.findall("dot"))
    tm = note.find("time-modification")
    if rest is not None and (rest.get("measure") == "yes" or (
            typ in (None, "whole") and not dots and tm is None
            and measure is not None and _alone_in_voice(note, measure))):
        # engines differ on whether a whole-bar rest carries measure="yes" and/or <type>
        return "measure"
    tup = ""
    if tm is not None:
        tup = f"/{_txt(tm, 'actual-notes', '?')}:{_txt(tm, 'normal-notes', '?')}"
    if typ is None:
        return "?"
    return typ + "." * dots + tup


def _pitch_token(note) -> str | None:
    p = note.find("pitch")
    if p is not None:
        alter = _txt(p, "alter", "0")
        try:
            a = int(float(alter))
        except ValueError:
            a = 0
        acc = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}.get(a, f"[{alter}]")
        return f"{_txt(p, 'step', '?')}{acc}{_txt(p, 'octave', '?')}"
    u = note.find("unpitched")
    if u is not None:
        return f"u:{_txt(u, 'display-step', '?')}{_txt(u, 'display-octave', '?')}"
    return None


def extract_staves(root: etree._Element) -> list[Staff]:
    """Split a score into staves and collect categorised events per staff."""
    names = {sp.get("id"): _txt(sp, "part-name", "") for sp in root.iterfind("part-list/score-part")}
    staves: list[Staff] = []
    for pi, part in enumerate(root.findall("part")):
        staves.extend(part_staves(part, pi, names.get(part.get("id"), "")))
    return staves


def part_staves(part: etree._Element, pi: int = 0, name: str = "") -> list[Staff]:
    """The staves of one <part> with their categorised events (see `extract_staves`)."""
    pstaves: dict[int, Staff] = {}

    def st(n: int) -> Staff:
        if n not in pstaves:
            pstaves[n] = Staff(pi, name, n)
        return pstaves[n]

    st(1)
    divisions = Fraction(1)
    transpose = None
    measures = part.findall("measure")
    for mi, measure in enumerate(measures):
        cur = mend = Fraction(0)
        last_onset = Fraction(0)
        changed = False     # instrument change in this measure
        if measure.find(".//instrument-change") is not None and measure.find("attributes/transpose") is None:
            transpose = ("0", "0")    # MuseScore writes <transpose> only for a non-zero interval
        for el in measure:
            tag = el.tag
            mend = max(mend, cur)
            if tag == "attributes":
                d = _txt(el, "divisions")
                if d and Fraction(d) > 0:      # Audiveris sometimes writes <divisions>0
                    divisions = Fraction(d)
                tr = el.find("transpose")
                if tr is not None:
                    t = (_txt(tr, "chromatic", "0"), _txt(tr, "octave-change", "0"))
                    changed |= transpose is not None and t != transpose
                    transpose = t
                mr = el.find("measure-style/multiple-rest")
                if mr is not None and mr.text:
                    st(1).events["multirest"].append((mi, cur, f"mr:{mr.text.strip()}"))
                ns = _txt(el, "staves")
                if ns and ns.isdigit():
                    for k in range(1, int(ns) + 1):
                        st(k)
                for key in el.findall("key"):
                    tok = f"key:{_txt(key, 'fifths', '?')}"
                    targets = [int(key.get("number"))] if key.get("number") else list(pstaves)
                    for k in targets:
                        st(k).events["keys"].append((mi, cur, tok))
                for time_ in el.findall("time"):
                    if time_.find("senza-misura") is not None:
                        tok = "time:senza"
                    else:
                        tok = f"time:{_txt(time_, 'beats', '?')}/{_txt(time_, 'beat-type', '?')}"
                    targets = [int(time_.get("number"))] if time_.get("number") else list(pstaves)
                    for k in targets:
                        st(k).events["times"].append((mi, cur, tok))
                for clef in el.findall("clef"):
                    oc = _txt(clef, "clef-octave-change", "")
                    tok = f"clef:{_txt(clef, 'sign', '?')}{_txt(clef, 'line', '')}{oc and '^' + oc}"
                    st(int(clef.get("number", "1"))).events["clefs"].append((mi, cur, tok))
            elif tag == "backup":
                cur -= Fraction(_txt(el, "duration", "0")) / divisions
            elif tag == "forward":
                cur += Fraction(_txt(el, "duration", "0")) / divisions
            elif tag == "note":
                is_chord = el.find("chord") is not None
                is_grace = el.find("grace") is not None
                onset = last_onset if is_chord else cur
                s = st(int(_txt(el, "staff", "1") or 1))
                dur_tok = _duration_token(el, measure)
                if is_grace:
                    dur_tok = "grace:" + dur_tok
                ev = s.events
                if el.find("rest") is not None:
                    ev["rests"].append((mi, onset, "R:" + dur_tok))
                    ev["rhythm"].append((mi, onset, "R:" + dur_tok))
                    s.measures.setdefault(mi, []).append((onset, "R:" + dur_tok))
                else:
                    pt = _pitch_token(el) or "~"
                    ev["notes"].append((mi, onset, f"{pt}:{dur_tok}"))
                    ev["pitch"].append((mi, onset, pt))
                    if not is_chord:
                        ev["rhythm"].append((mi, onset, "N:" + dur_tok))
                    s.measures.setdefault(mi, []).append((onset, f"{pt}:{dur_tok}"))
                for notations in el.findall("notations"):
                    for art in notations.findall("articulations/*"):
                        ev["articulations"].append((mi, onset, art.tag))
                    for f in notations.findall("fermata"):
                        ev["fermatas"].append((mi, onset, "fermata"))
                    for sl in notations.findall("slur"):
                        if sl.get("type") == "start":
                            ev["slurs"].append((mi, onset, "slur"))
                    for ti in notations.findall("tied"):
                        if ti.get("type") == "start":
                            ev["ties"].append((mi, onset, "tie"))
                    for dyn in notations.findall("dynamics/*"):
                        ev["dynamics"].append((mi, onset, _dyn_token(dyn)))
                    for tu in notations.findall("tuplet"):
                        if tu.get("type") == "start":
                            tm = el.find("time-modification")
                            ratio = (f"{_txt(tm, 'actual-notes', '?')}:{_txt(tm, 'normal-notes', '?')}"
                                     if tm is not None else "?")
                            ev["tuplets"].append((mi, onset, f"tuplet:{ratio}"))
                    for tr in notations.findall("ornaments/tremolo"):
                        if tr.get("type", "single") in ("single", "start"):
                            ev["tremolos"].append((mi, onset, f"trem:{tr.get('type', 'single')}:"
                                                              f"{(tr.text or '').strip()}"))
                for ly in el.findall("lyric"):
                    text = "".join(t.text or "" for t in ly.findall("text"))
                    if text.strip():
                        verse = ly.get("number", "1")
                        ev["lyrics"].append((mi, onset, f"v{verse}:{_norm_text(text)}"))
                if not is_chord and not is_grace:
                    last_onset = cur
                    cur += Fraction(_txt(el, "duration", "0")) / divisions
                elif not is_chord:
                    last_onset = cur
            elif tag == "direction":
                s = st(int(_txt(el, "staff", "1") or 1))
                off = el.find("offset")
                onset = cur + (Fraction(off.text.strip()) / divisions
                               if off is not None and off.text else 0)
                for dt in el.findall("direction-type"):
                    for dyn in dt.findall("dynamics/*"):
                        s.events["dynamics"].append((mi, onset, _dyn_token(dyn)))
                    for w in dt.findall("wedge"):
                        if w.get("type") in ("crescendo", "diminuendo"):
                            s.events["hairpins"].append((mi, onset, w.get("type")))
                    cat = "systemtext" if el.get("system") in ("only-top", "also-top") else "words"
                    # one text split over several <words> runs (line break, tempo glyph) is one token
                    text = re.sub(r"[\ue000-\uf8ff]", "", "".join(w.text or "" for w in dt.findall("words")))
                    if text.strip():
                        s.events[cat].append((mi, onset, _norm_text(text)))
                    for mm in dt.findall("metronome"):
                        unit = _txt(mm, "beat-unit", "?") + "." * len(mm.findall("beat-unit-dot"))
                        s.events["tempo"].append((mi, onset, f"{unit}={_txt(mm, 'per-minute', '?')}"))
                    for r in dt.findall("rehearsal"):
                        if r.text and r.text.strip():
                            s.events["rehearsal"].append((mi, onset, "reh:" + _norm_text(r.text)))
                    for nav in ("segno", "coda"):
                        if dt.find(nav) is not None:
                            s.events["structure"].append((mi, onset, nav))
                snd = el.find("sound")
                if snd is not None:
                    _sound(snd, st(1), mi, onset, skip=("segno", "coda"))
                    changed |= snd.find("instrument-change") is not None
            elif tag == "sound":
                _sound(el, st(1), mi, cur)
                changed |= el.find("instrument-change") is not None
            elif tag == "harmony":
                s = st(int(_txt(el, "staff", "1") or 1))
                off = el.find("offset")
                onset = cur + (Fraction(off.text.strip()) / divisions
                               if off is not None and off.text else 0)
                acc = {"-1": "b", "1": "#", "-2": "bb", "2": "##"}
                bass = _txt(el, "bass/bass-step")
                tok = (f"{_txt(el, 'root/root-step', '?')}{acc.get(_txt(el, 'root/root-alter', '0'), '')}:"
                       f"{_txt(el, 'kind', '')}"
                       + (f"/{bass}{acc.get(_txt(el, 'bass/bass-alter', '0'), '')}" if bass else ""))
                s.events["chords"].append((mi, onset, tok))
            elif tag == "barline":
                s = st(1)
                at = max(mend, cur) if el.get("location", "right") != "left" else Fraction(0)
                if el.find("fermata") is not None:
                    s.events["fermatas"].append((mi, at, "fermata"))
                rep = el.find("repeat")
                if rep is not None:
                    s.events["structure"].append((mi, at, f"repeat:{rep.get('direction')}"))
                end = el.find("ending")
                if end is not None and end.get("type") == "start":
                    s.events["structure"].append((mi, at, f"ending:{end.get('number', '?')}"))
                for nav in ("segno", "coda"):
                    if el.find(nav) is not None:
                        s.events["structure"].append((mi, at, nav))
                style = _txt(el, "bar-style")
                if rep is None and style and style not in ("regular", "none"):
                    s.events["barlines"].append((mi, at, f"bar:{style}"))
        if changed:
            st(1).events["instruments"].append((mi, Fraction(0), "ic"))
    for s in pstaves.values():
        s.n_measures = len(measures)
    return [pstaves[k] for k in sorted(pstaves)]


def _sound(snd, s: Staff, mi: int, onset, skip=()) -> None:
    """Navigation (D.S., D.C., fine, to coda, ...) carried by a <sound> element."""
    for nav in _NAV:
        if nav not in skip and snd.get(nav):
            s.events["structure"].append((mi, onset, nav))


def _dyn_token(el) -> str:
    if el.tag == "other-dynamics":
        return _norm_text(el.text or "other")
    return el.tag


# --------------------------------------------------------------------------- stats

def measure_count(root: etree._Element) -> int:
    return max((len(p.findall("measure")) for p in root.findall("part")), default=0)
