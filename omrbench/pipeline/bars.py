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
                d = math.lcm(d, int(float(el.text)))
            except (TypeError, ValueError):
                pass
    return d


def _scale(el: etree._Element, factor: Fraction) -> None:
    for tag in ("duration", "offset"):
        for d in el.iter(tag):
            if d.text and d.text.strip():
                d.text = str(int(round(Fraction(d.text.strip()) * factor)))


def _clef(c) -> Clef:
    return (c.findtext("sign", "G"), c.findtext("line", ""), c.findtext("clef-octave-change", ""))


def part_bars(part: etree._Element, D: int, source: str, staves: int = 1) -> list[Bar]:
    """Split a MusicXML <part> into Bars (durations rescaled to D divisions)."""
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
                    div = Fraction(el.findtext("divisions").strip())
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
