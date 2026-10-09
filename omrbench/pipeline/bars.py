"""Engine-neutral measures ("bars") that can be mixed across engines.

A Bar holds copies of one engine's measure content with every duration rescaled to
one common <divisions> value, plus the clef/key/time in force at its start, so bars
from homr and Audiveris can be concatenated and the attributes re-emitted only where
they really change.
"""
from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass, field
from fractions import Fraction

from lxml import etree

from .. import log as logmod

# direction types taken over from Audiveris (text is rebuilt from the page layout)
KEEP_DIRECTION_TYPES = {"dynamics", "wedge", "metronome", "rehearsal", "pedal",
                        "octave-shift", "dashes", "bracket", "segno", "coda"}

Clef = tuple[str, str, str]      # sign, line, octave change


@dataclass
class Bar:
    items: list[etree._Element]            # note/backup/forward/direction/... in order
    source: str                            # homr | audiveris | rest
    staves: int = 1
    clefs: dict[int, Clef] = field(default_factory=dict)   # in force at start, per staff
    key: str | None = None                 # fifths
    time: tuple[str, str] | None = None    # beats, beat-type
    multirest: int = 0                     # printed <multiple-rest> count (homr)

    def notes(self) -> list[etree._Element]:
        return [e for e in self.items if e.tag == "note"]

    @property
    def rest_only(self) -> bool:
        ns = self.notes()
        return all(n.find("rest") is not None for n in ns)

    @property
    def empty(self) -> bool:
        return not self.notes()


def common_divisions(roots) -> int:
    d = 1
    for r in roots:
        for el in r.iter("divisions"):
            try:
                v = int(float(el.text))
            except (TypeError, ValueError):
                continue
            if v > 0:
                d = math.lcm(d, v)
    return d


def _scale(el: etree._Element, factor: Fraction) -> None:
    for tag in ("duration", "offset"):
        for d in el.iter(tag):
            if d.text and d.text.strip():
                d.text = str(int(round(Fraction(d.text.strip()) * factor)))


def _clef(c) -> Clef:
    return (c.findtext("sign", "G"), c.findtext("line", ""), c.findtext("clef-octave-change", ""))


LOG = logmod.get("bars")


def part_bars(part: etree._Element, D: int, source: str, staves: int = 1) -> list[Bar]:
    """Split a MusicXML <part> into Bars (durations rescaled to D divisions). Lyrics are
    dropped: vocal scores get them from the page layout (lyrics.py)."""
    bars: list[Bar] = []
    div = Fraction(1)
    clefs: dict[int, Clef] = {}
    key = None
    time = None
    for m in part.findall("measure"):
        items: list[etree._Element] = []
        start = None             # (clefs, key, time) in force when the first note starts
        multirest = 0
        seen_content = False
        for el in m:
            if el.tag == "attributes":
                if el.findtext("divisions"):
                    try:
                        new_div = Fraction(el.findtext("divisions").strip())
                    except ValueError:
                        new_div = Fraction(0)
                    if new_div > 0:
                        div = new_div
                    else:
                        # Audiveris exports <divisions>0</divisions> for a bar whose rhythm
                        # it gave up on (seen on bar 1); keep the last. That bar's length is
                        # off, but the bar-length checks pick the other engine's bar there
                        LOG.debug(f"{source}: invalid <divisions>{el.findtext('divisions')}"
                                    f"</divisions> in measure {m.get('number')}, kept {div}")
                if el.findtext("staves"):
                    staves = max(staves, int(el.findtext("staves")))
                mr = el.find("measure-style/multiple-rest")
                if mr is not None and (mr.text or "").strip().isdigit():
                    multirest = int(mr.text)
                for k in el.findall("key"):
                    key = k.findtext("fifths", key)
                for t in el.findall("time"):
                    time = (t.findtext("beats", "4"), t.findtext("beat-type", "4"))
                new_clefs = {int(c.get("number", "1")): _clef(c) for c in el.findall("clef")}
                if not seen_content:
                    clefs.update(new_clefs)
                elif new_clefs:
                    # mid-bar clef change: keep inline, clef only
                    a = etree.Element("attributes")
                    for c in el.findall("clef"):
                        a.append(copy.deepcopy(c))
                    items.append(a)
                    clefs.update(new_clefs)
                continue
            if el.tag in ("print", "barline", "sound"):
                continue
            if el.tag in ("note", "backup", "forward") and not seen_content:
                seen_content = True
                start = (dict(clefs), key, time)
            c = copy.deepcopy(el)
            _scale(c, Fraction(D) / div)
            if c.tag == "note":
                for ly in c.findall("lyric"):
                    c.remove(ly)
            if c.tag == "direction" and not _keep_direction(c):
                continue
            items.append(c)
        if start is None:
            start = (dict(clefs), key, time)
        bars.append(Bar(items, source, staves, start[0], start[1], start[2], multirest))
    return bars


def _keep_direction(d: etree._Element) -> bool:
    """Drop <words> (rebuilt from layout); keep the other direction types."""
    for dt in list(d.findall("direction-type")):
        for mm in dt.findall("metronome"):
            # Audiveris sometimes turns text into a metronome ("Celesta - sounds 8va")
            if not re.fullmatch(r"\d{2,3}(\.\d+)?", (mm.findtext("per-minute") or "").strip()):
                dt.remove(mm)
        for r in dt.findall("rehearsal"):
            # Audiveris turns boxed labels ("Bell", "Glock mallets") into rehearsal marks
            if not re.fullmatch(r"[A-Z0-9]{1,3}", (r.text or "").strip()):
                dt.remove(r)
        kids = [k for k in dt if k.tag in KEEP_DIRECTION_TYPES]
        if not kids:
            d.remove(dt)
    return d.find("direction-type") is not None


def bar_length(time: tuple[str, str] | None, D: int) -> int | None:
    if not time:
        return None
    try:
        beats = sum(Fraction(x) for x in time[0].split("+"))
        return int(beats * 4 * D / Fraction(time[1]))
    except (ValueError, ZeroDivisionError):
        return None


def voice_lengths(bar: Bar) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for n in bar.notes():
        if n.find("chord") is not None or n.find("grace") is not None:
            continue
        k = (n.findtext("staff", "1"), n.findtext("voice", "1"))
        out[k] = out.get(k, 0) + int(n.findtext("duration", "0") or 0)
    return out


def bar_ok(bar: Bar, length: int | None) -> bool:
    """Every voice fills the bar exactly (whole-bar rests count as full)."""
    if length is None or bar.empty:
        return not bar.empty
    lens = voice_lengths(bar)
    for n in bar.notes():
        r = n.find("rest")
        if r is not None and r.get("measure") == "yes":
            lens[(n.findtext("staff", "1"), n.findtext("voice", "1"))] = length
    return bool(lens) and all(v == length for v in lens.values())


def onsets(bar: Bar) -> list[tuple[int, etree._Element]]:
    """(onset, element) for every note/direction, in document order."""
    out, cur, last = [], 0, 0
    for el in bar.items:
        if el.tag == "note":
            is_chord = el.find("chord") is not None
            on = last if is_chord else cur
            out.append((on, el))
            if not is_chord and el.find("grace") is None:
                last = cur
                cur += int(el.findtext("duration", "0") or 0)
        elif el.tag == "backup":
            cur -= int(el.findtext("duration", "0") or 0)
        elif el.tag == "forward":
            cur += int(el.findtext("duration", "0") or 0)
        elif el.tag == "direction":
            off = el.findtext("offset")
            out.append((cur + (int(off) if off and off.strip().lstrip("-").isdigit() else 0), el))
    return out


def rest_bar(staves: int, length: int | None, D: int) -> Bar:
    items = []
    for s in range(1, staves + 1):
        if s > 1 and length:
            b = etree.Element("backup")
            etree.SubElement(b, "duration").text = str(length)
            items.append(b)
        n = etree.Element("note")
        etree.SubElement(n, "rest", measure="yes")
        etree.SubElement(n, "duration").text = str(length or 4 * D)
        etree.SubElement(n, "voice").text = str(1 + 4 * (s - 1))
        if staves > 1:
            etree.SubElement(n, "staff").text = str(s)
        items.append(n)
    return Bar(items, "rest", staves)


def add_direction(bar: Bar, direction: etree._Element, onset: int,
                  staff: int | None) -> etree._Element:
    """Insert a direction at `onset` (divisions from bar start) via <offset>."""
    d = copy.deepcopy(direction)
    for old in d.findall("offset"):
        d.remove(old)
    for old in d.findall("staff"):
        d.remove(old)
    if onset:
        off = etree.Element("offset")
        off.text = str(onset)
        # <offset> goes after direction-type(s), before staff/sound
        idx = max(i for i, c in enumerate(d) if c.tag == "direction-type") + 1
        d.insert(idx, off)
    if staff and bar.staves > 1:
        st = etree.Element("staff")
        st.text = str(staff)
        idx = max(i for i, c in enumerate(d) if c.tag in ("direction-type", "offset")) + 1
        d.insert(idx, st)
    bar.items.insert(0, d)
    return d


def to_unpitched(bar: Bar) -> Bar:
    """homr has no percussion support: keep its rhythm, turn pitches into staff positions."""
    b = copy.deepcopy(bar)
    for n in b.notes():
        p = n.find("pitch")
        if p is None:
            continue
        u = etree.Element("unpitched")
        etree.SubElement(u, "display-step").text = p.findtext("step", "C")
        etree.SubElement(u, "display-octave").text = p.findtext("octave", "4")
        n.replace(p, u)
    b.clefs = {s: ("percussion", "", "") for s in (b.clefs or {1: None})}
    b.key = "0"
    return b


def words_direction(text: str, placement: str) -> etree._Element:
    d = etree.Element("direction", placement=placement)
    dt = etree.SubElement(d, "direction-type")
    etree.SubElement(dt, "words").text = text
    return d


def metronome_direction(per_minute: str, unit: str = "quarter") -> etree._Element:
    d = etree.Element("direction", placement="above")
    mm = etree.SubElement(etree.SubElement(d, "direction-type"), "metronome")
    etree.SubElement(mm, "beat-unit").text = unit
    etree.SubElement(mm, "per-minute").text = per_minute
    etree.SubElement(d, "sound", tempo=per_minute)
    return d


# elements a <note> may have before <staff> (MusicXML order)
_BEFORE_STAFF = {"grace", "cue", "chord", "pitch", "unpitched", "rest", "duration", "tie",
                 "instrument", "footnote", "level", "voice", "type", "dot", "accidental",
                 "time-modification", "stem", "notehead", "notehead-text"}


def _set_staff(note: etree._Element, staff: int | None) -> None:
    for old in note.findall("staff"):
        note.remove(old)
    if staff is None:
        return
    st = etree.Element("staff")
    st.text = str(staff)
    idx = max((i for i, c in enumerate(note) if c.tag in _BEFORE_STAFF), default=-1) + 1
    note.insert(idx, st)


def restaff(sources: list[tuple[Bar, list[int]]]) -> Bar:
    """One bar from staves of other bars: [(bar, [staff numbers to keep])...], renumbered
    1..n in that order (voices renumbered per staff). Directions keep their onset."""
    voices: dict[tuple[int, str], list[tuple[int, etree._Element]]] = {}
    extras: list[tuple[int, int, etree._Element]] = []   # onset, new staff, direction/attributes
    clefs: dict[int, Clef] = {}
    new_no = 0
    src_name = sources[0][0].source if sources else "rest"
    key = time = None
    for bi, (bar, keep) in enumerate(sources):
        mapping = {}
        for s in keep:
            new_no += 1
            mapping[s] = new_no
            if s in bar.clefs:
                clefs[new_no] = bar.clefs[s]
        key = key if key is not None else bar.key
        time = time or bar.time
        cur = last = 0
        for el in bar.items:
            if el.tag == "note":
                s = int(el.findtext("staff", "1") or 1)
                is_chord = el.find("chord") is not None
                on = last if is_chord else cur
                if not is_chord and el.find("grace") is None:
                    last = cur
                    cur += int(el.findtext("duration", "0") or 0)
                if s in mapping:
                    voices.setdefault((mapping[s], f"{bi}.{el.findtext('voice', '1')}"), []).append((on, el))
            elif el.tag == "backup":
                cur -= int(el.findtext("duration", "0") or 0)
            elif el.tag == "forward":
                cur += int(el.findtext("duration", "0") or 0)
            elif el.tag == "direction":
                st = el.findtext("staff")
                # no <staff>: staff 1 of its part (MusicXML default), not every group
                s = int(st) if st and st.isdigit() else 1
                if s in mapping:
                    off = el.findtext("offset")
                    extras.append((cur + (int(off) if off and off.strip().lstrip("-").isdigit() else 0),
                                   mapping[s], el))
            elif el.tag == "attributes":
                a = etree.Element("attributes")
                for c in el.findall("clef"):
                    s = int(c.get("number", "1"))
                    if s in mapping:
                        c2 = copy.deepcopy(c)
                        c2.set("number", str(mapping[s]))
                        a.append(c2)
                if len(a):
                    extras.append((cur, mapping[int(a[0].get("number"))], a))
    n = new_no
    out = Bar([], src_name, max(n, 1), clefs, key, time,
              max((b.multirest for b, _ in sources), default=0))
    per_staff: dict[int, int] = {}
    pos_total = 0
    for (staff, _), evs in sorted(voices.items(), key=lambda kv: kv[0][0]):
        per_staff[staff] = per_staff.get(staff, 0) + 1
        voice = str(per_staff[staff] + 4 * (staff - 1))
        if pos_total:
            b = etree.Element("backup")
            etree.SubElement(b, "duration").text = str(pos_total)
            out.items.append(b)
        pos = 0
        clef_changes = sorted((on, a) for on, s, a in extras if a.tag == "attributes" and s == staff)
        for on, el in evs:
            is_chord = el.find("chord") is not None
            if not is_chord and on > pos:
                f = etree.Element("forward")
                etree.SubElement(f, "duration").text = str(on - pos)
                etree.SubElement(f, "voice").text = voice
                if n > 1:
                    etree.SubElement(f, "staff").text = str(staff)
                out.items.append(f)
                pos = on
            while clef_changes and clef_changes[0][0] <= pos and not is_chord:
                out.items.append(copy.deepcopy(clef_changes.pop(0)[1]))
            c = copy.deepcopy(el)
            for v in c.findall("voice"):
                v.text = voice
            _set_staff(c, staff if n > 1 else None)
            out.items.append(c)
            if not is_chord and c.find("grace") is None:
                pos += int(c.findtext("duration", "0") or 0)
        pos_total = pos
    for on, staff, el in extras:
        if el.tag == "direction":
            add_direction(out, el, on, staff)
    return out


def _staff_of(el: etree._Element) -> int:
    return int(el.findtext("staff", "1") or 1)


def sounding(bar: Bar) -> dict[int, list[tuple[int, etree._Element]]]:
    """staff -> (onset, note) of the first note of every chord (no rests, no graces)."""
    out: dict[int, list[tuple[int, etree._Element]]] = {}
    for on, el in onsets(bar):
        if el.tag == "note" and el.find("rest") is None and el.find("chord") is None \
                and el.find("grace") is None:
            out.setdefault(_staff_of(el), []).append((on, el))
    return out


def keep_span(bar: Bar, start: int, end: int | None) -> Bar:
    """Copy of the bar with only what starts in [start, end): other notes become rests
    (a staff two singers share), their directions are dropped."""
    out = copy.deepcopy(bar)
    on_of = {id(el): on for on, el in onsets(out)}
    inside = lambda el: start <= on_of.get(id(el), 0) and (end is None or on_of.get(id(el), 0) < end)
    items = []
    for el in out.items:
        if el.tag == "direction" and not inside(el):
            continue
        if el.tag == "note" and el.find("rest") is None and not inside(el):
            if el.find("chord") is not None or el.find("grace") is not None:
                continue
            r = etree.Element("note")
            etree.SubElement(r, "rest")
            for tag in ("duration", "voice", "type", "dot", "time-modification", "staff"):
                for x in el.findall(tag):
                    r.append(copy.deepcopy(x))
            items.append(r)
            continue
        items.append(el)
    out.items = items
    return out


def dedupe_chord_marks(bar: Bar) -> int:
    """Articulations / fermatas once per chord, on its first note: the engines put a
    staccato on every note of a chord, MuseScore then stacks them. Returns the number
    removed."""
    removed = 0
    seen: set[str] = set()
    for el in bar.items:
        if el.tag != "note":
            continue
        if el.find("chord") is None:
            seen = set()
        for nt in el.findall("notations"):
            for art in nt.findall("articulations"):
                for a in list(art):
                    if a.tag in seen:
                        art.remove(a)
                        removed += 1
                    else:
                        seen.add(a.tag)
                if not len(art):
                    nt.remove(art)
            for f in nt.findall("fermata"):
                if "fermata" in seen:
                    nt.remove(f)
                    removed += 1
                seen.add("fermata")
            if not len(nt):
                el.remove(nt)
    return removed


GRACE_FLAGGED = ("eighth", "16th", "32nd")


def fix_graces(bars: list[Bar]) -> tuple[int, int]:
    """Grace notes are printed with flags (eighth / 16th); the engines often miss them
    and write quarter. Those get the piece's most common flagged grace type; "graces"
    of half or whole length are misreads and are dropped. Returns (retyped, dropped)."""
    graces = [n for b in bars for n in b.notes() if n.find("grace") is not None]
    flagged = [n.findtext("type") for n in graces if n.findtext("type") in GRACE_FLAGGED]
    typ = max(set(flagged), key=flagged.count) if flagged else "eighth"
    retyped = dropped = 0
    for b in bars:
        keep = []
        for el in b.items:
            if el.tag == "note" and el.find("grace") is not None:
                t = el.find("type")
                if t is not None and t.text in ("half", "whole", "breve"):
                    dropped += 1
                    continue
                if t is not None and t.text not in GRACE_FLAGGED + ("64th",):
                    t.text = typ
                    retyped += 1
                for d in el.findall("dot"):
                    el.remove(d)
            keep.append(el)
        if dropped:
            # a dropped grace that started a chord: its chord notes start the chord now
            for k, el in enumerate(keep):
                if el.tag == "note" and el.find("chord") is not None and el.find("grace") is not None:
                    prev = keep[k - 1] if k else None
                    if prev is None or prev.tag != "note" or prev.find("grace") is None:
                        el.remove(el.find("chord"))
        b.items = keep
    return retyped, dropped


# ----------------------------------------------------------------------------- beams

BEAM_LEVELS = {"eighth": 1, "16th": 2, "32nd": 3, "64th": 4, "128th": 5}
_AFTER_BEAM = ("notations", "lyric", "play", "listen")


def _beat_group(time: tuple[str, str] | None, D: int) -> tuple[int, bool]:
    """(beam group length in divisions, 4/4-like: two eighth beats may join)."""
    try:
        beats, btype = int(time[0]), int(time[1])
    except (TypeError, ValueError, IndexError):
        beats, btype = 4, 4
    unit = 4 * D // btype if btype else D
    if btype == 8 and beats % 3 == 0:
        return 3 * unit, False          # 6/8, 9/8, 12/8, 3/8: dotted quarters
    return unit, beats == 4 and btype == 4


def auto_beam(bar: Bar, time: tuple[str, str] | None, D: int) -> int:
    """Beam runs of unbeamed eighths and shorter by beat (MuseScore shows notes without
    <beam> with flags). Runs end at rests, longer notes, beat boundaries and notes that
    already have beams. In 4/4 two beats of plain eighths join (beats 1-2, 3-4).
    Returns the number of notes beamed."""
    group, join_halves = _beat_group(time, D)
    voices: dict[tuple[int, str], list[dict]] = {}
    cur = last = 0
    for el in bar.items:
        if el.tag == "note":
            chord = el.find("chord") is not None
            on = last if chord else cur
            if el.find("grace") is None:
                key = (_staff_of(el), el.findtext("voice", "1"))
                evs = voices.setdefault(key, [])
                if chord and evs and evs[-1]["on"] == on:
                    evs[-1]["notes"].append(el)
                else:
                    dur = int(el.findtext("duration", "0") or 0)
                    evs.append({"on": on, "dur": dur, "notes": [el],
                                "rest": el.find("rest") is not None,
                                "level": BEAM_LEVELS.get(el.findtext("type", ""), 0)})
                if not chord:
                    last = cur
                    cur += int(el.findtext("duration", "0") or 0)
        elif el.tag == "backup":
            cur -= int(el.findtext("duration", "0") or 0)
        elif el.tag == "forward":
            cur += int(el.findtext("duration", "0") or 0)
    beamed = 0
    for evs in voices.values():
        evs.sort(key=lambda e: e["on"])
        runs: list[list[dict]] = []
        for e in evs:
            ok = (not e["rest"] and e["level"] and e["dur"] > 0
                  and not any(n.find("beam") is not None for n in e["notes"]))
            if not ok:
                runs.append([])
                continue
            prev = runs[-1][-1] if runs and runs[-1] else None
            if prev and prev["on"] + prev["dur"] == e["on"] and prev["on"] // group == e["on"] // group:
                runs[-1].append(e)
            else:
                runs.append([e])
        runs = [r for r in runs if r]
        if join_halves:
            merged: list[list[dict]] = []
            for r in runs:
                p = merged[-1] if merged else None
                plain = lambda rr: len(rr) == 2 and all(x["level"] == 1 for x in rr) \
                    and rr[0]["on"] % group == 0
                if p and plain(p) and plain(r) and p[0]["on"] % (2 * group) == 0 \
                        and r[0]["on"] == p[0]["on"] + group:
                    p.extend(r)
                else:
                    merged.append(r)
            runs = merged
        for r in runs:
            if len(r) < 2:
                continue
            for k, e in enumerate(r):
                for lvl in range(1, e["level"] + 1):
                    has_prev = k > 0 and r[k - 1]["level"] >= lvl
                    has_next = k + 1 < len(r) and r[k + 1]["level"] >= lvl
                    if has_prev and has_next:
                        kind = "continue"
                    elif has_next:
                        kind = "begin"
                    elif has_prev:
                        kind = "end"
                    else:
                        kind = "forward hook" if k == 0 else "backward hook"
                    for n in e["notes"]:
                        b = etree.Element("beam", number=str(lvl))
                        b.text = kind
                        idx = next((i for i, c in enumerate(n) if c.tag in _AFTER_BEAM), len(n))
                        n.insert(idx, b)
                beamed += 1
    return beamed


def cues_to_rests(bar: Bar, staff: int, onsets_: set[int]) -> int:
    """Turn the notes of `staff` starting at the given onsets into rests (cue notes the
    player doesn't play). Returns the number of notes removed."""
    removed = 0
    items = []
    order = {id(el): on for on, el in onsets(bar)}
    for el in bar.items:
        if el.tag != "note" or int(el.findtext("staff", "1") or 1) != staff or \
                el.find("rest") is not None or order.get(id(el)) not in onsets_:
            items.append(el)
            continue
        removed += 1
        if el.find("chord") is not None or el.find("grace") is not None:
            continue            # the chord's first note becomes the rest; graces go
        r = etree.Element("note")
        etree.SubElement(r, "rest")
        for tag in ("duration", "voice", "type", "dot", "time-modification", "staff"):
            for x in el.findall(tag):
                r.append(copy.deepcopy(x))
        items.append(r)
    bar.items = items
    return removed
