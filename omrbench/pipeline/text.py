"""Printed text rebuilt from the positioned words and lyric items in the .omr.

Audiveris OCRs most text but files much of it wrongly: bar numbers and bar ranges
become lyrics, expression text becomes page credits. Here every text atom is
regrouped into lines by position and classified by where it sits and what it says:

- page header/footer lines        -> <credit>
- "15-17" style ranges, numbers   -> bar-number evidence (multi-measure rests)
- other lines inside the music    -> <words> on the nearest staff
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .layout import Page, Staff, System, Text

RANGE = re.compile(r"^\[?(\d{1,4})\s*[-–—]\s*(\d{1,4})\]?$")
NUMBER = re.compile(r"^\d{1,4}$")
HEADER_ROLES = {"Title", "Number", "CreatorComposer", "CreatorLyricist", "CreatorArranger",
                "Rights", "PartName"}


@dataclass
class Line:
    page: int
    atoms: list[Text] = field(default_factory=list)

    @property
    def x(self) -> float:
        return min(a.x for a in self.atoms)

    @property
    def right(self) -> float:
        return max(a.x + a.w for a in self.atoms)

    @property
    def top(self) -> float:
        return min(a.y for a in self.atoms)

    @property
    def bottom(self) -> float:
        return max(a.y + a.h for a in self.atoms)

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def h(self) -> float:
        hs = sorted(a.h for a in self.atoms)
        return hs[len(hs) // 2]

    @property
    def text(self) -> str:
        out, prev = "", None
        for a in sorted(self.atoms, key=lambda a: a.x):
            if prev is not None and a.x - (prev.x + prev.w) > 0.12 * max(self.h, 1):
                out += " "
            out += a.value
            prev = a
        return re.sub(r"\s+", " ", out).strip()

    @property
    def roles(self) -> set[str]:
        return {a.role for a in self.atoms if a.role}


def lines(page: Page) -> list[Line]:
    """Group text atoms into lines: vertical overlap and small horizontal gaps."""
    out: list[Line] = []
    for a in sorted(page.texts, key=lambda a: a.x):
        if not a.value.strip():
            continue
        best = None
        for ln in out:
            ov = min(ln.bottom, a.y + a.h) - max(ln.top, a.y)
            gap = a.x - ln.right
            if ov >= 0.5 * min(a.h, ln.h) and -a.h <= gap <= 1.6 * max(a.h, ln.h):
                best = ln
                break
        if best is None:
            best = Line(page.number)
            out.append(best)
        best.atoms.append(a)
    return out


def is_words(text: str) -> bool:
    """Real text: at least one alphabetic run of two or more letters."""
    return re.search(r"[^\W\d_]{2,}", text) is not None


@dataclass
class Placed:
    line: Line
    system: System
    staff: Staff
    above: bool


@dataclass
class PageText:
    credits: list[Line] = field(default_factory=list)
    words: list[Placed] = field(default_factory=list)
    ranges: list[tuple[Placed, int, int]] = field(default_factory=list)
    numbers: list[tuple[Placed, int]] = field(default_factory=list)
    rehearsals: list[tuple[Placed, str]] = field(default_factory=list)


def nearest_staff(staves: list[Staff], y: float) -> tuple[Staff, bool]:
    """Staff a text line at height y refers to. In the gap between two staves, text
    usually belongs to the staff below (labels, tempo, expression marks) unless it is
    much closer to the staff above."""
    staves = sorted(staves, key=lambda s: s.top)
    for st in staves:
        if st.top <= y <= st.bottom:
            return st, False
    below = [s for s in staves if s.top > y]
    above = [s for s in staves if s.bottom < y]
    if below and above:
        d_b, d_a = below[0].top - y, y - above[-1].bottom
        return (below[0], True) if d_b <= 1.5 * d_a else (above[-1], False)
    if below:
        return below[0], True
    return above[-1], False


def classify(page: Page) -> PageText:
    res = PageText()
    systems = [s for s in page.systems if s.staves]
    if not systems:
        res.credits = [ln for ln in lines(page) if ln.text]
        return res
    il = systems[0].staves[0].interline
    first_top = systems[0].top
    last_bottom = systems[-1].bottom
    for ln in lines(page):
        t = ln.text
        if not t:
            continue
        header = ln.bottom < first_top - 12 * il or (
            ln.bottom < first_top and ln.roles & HEADER_ROLES and is_words(t)
            and ln.bottom < first_top - 4 * il)
        footer = ln.top > last_bottom + 8 * il
        if header or footer:
            if is_words(t) or NUMBER.match(t):
                res.credits.append(ln)
            continue
        staff, above = nearest_staff([st for s in systems for st in s.staves], ln.cy)
        sy = next(s for s in systems if staff in s.staves)
        atoms = sorted(ln.atoms, key=lambda a: a.x)
        if len(atoms) > 1 and NUMBER.match(atoms[0].value) and is_words(t):
            # boxed rehearsal number printed right before a label ("10 Bell Tree")
            res.rehearsals.append((Placed(Line(ln.page, atoms[:1]), sy, staff, above),
                                   atoms[0].value))
            ln = Line(ln.page, atoms[1:])
            t = ln.text
        pl = Placed(ln, sy, staff, above)
        m = RANGE.match(t.replace(" ", ""))
        if m:
            if int(m.group(1)) < int(m.group(2)):
                res.ranges.append((pl, int(m.group(1)), int(m.group(2))))
        elif NUMBER.match(t):
            if above and ln.x < staff.left + 4 * staff.interline:
                res.rehearsals.append((pl, t))       # boxed number at the system start
            else:
                res.numbers.append((pl, int(t)))
        elif is_words(t) and (any(a.kind == "word" for a in ln.atoms)
                              or re.search(r"[^\W\d_]{3,}", t)):
            # lines made only of lyric fragments need a real word ('"lf', 'P' are noise)
            res.words.append(pl)
    return res


def clean_words(t: str) -> str:
    """Drop a metronome remnant ("Maestoso = 92" -> "Maestoso"); tempo comes from Audiveris."""
    return re.sub(r"\s*[=♩]\s*\d{2,3}\s*$", "", t).strip()
