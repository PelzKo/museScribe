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
            dst = parts.setdefault(p.get("id"), etree.SubElement(pw, "part", id=p.get("id")))
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
]


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


def _norm_text(s: str) -> str:
    s = s.lower().replace(" ", " ")
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
        pstaves: dict[int, Staff] = {}

        def st(n: int) -> Staff:
            if n not in pstaves:
                pstaves[n] = Staff(pi, names.get(part.get("id"), ""), n)
            return pstaves[n]

        st(1)
        divisions = Fraction(1)
        measures = part.findall("measure")
        for mi, measure in enumerate(measures):
            cur = Fraction(0)
            last_onset = Fraction(0)
            for el in measure:
                tag = el.tag
                if tag == "attributes":
                    d = _txt(el, "divisions")
                    if d:
                        divisions = Fraction(d)
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
                            ev["articulations"].append((mi, onset, "fermata"))
                        for sl in notations.findall("slur"):
                            if sl.get("type") == "start":
                                ev["slurs"].append((mi, onset, "slur"))
                        for ti in notations.findall("tied"):
                            if ti.get("type") == "start":
                                ev["ties"].append((mi, onset, "tie"))
                        for dyn in notations.findall("dynamics/*"):
                            ev["dynamics"].append((mi, onset, _dyn_token(dyn)))
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
                        for w in dt.findall("words"):
                            if w.text and w.text.strip():
                                s.events["words"].append((mi, onset, _norm_text(w.text)))
                        for mm in dt.findall("metronome"):
                            unit = _txt(mm, "beat-unit", "?") + "." * len(mm.findall("beat-unit-dot"))
                            s.events["tempo"].append((mi, onset, f"{unit}={_txt(mm, 'per-minute', '?')}"))
        for s in pstaves.values():
            s.n_measures = len(measures)
        staves.extend(pstaves[k] for k in sorted(pstaves))
    return staves


def _dyn_token(el) -> str:
    if el.tag == "other-dynamics":
        return _norm_text(el.text or "other")
    return el.tag


# --------------------------------------------------------------------------- stats

def measure_count(root: etree._Element) -> int:
    return max((len(p.findall("measure")) for p in root.findall("part")), default=0)
