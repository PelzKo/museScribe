"""Printed text rebuilt from the positioned words and lyric items in the .omr.

Audiveris OCRs most text but files much of it wrongly: bar numbers and bar ranges
become lyrics, expression text becomes page credits. Here every text atom is
regrouped into lines by position and classified by where it sits and what it says:

- page header/footer lines        -> <credit>
- "15-17" style ranges, numbers   -> bar-number evidence (multi-measure rests)
- "[to] 97" (a cut: the bar there is bar 97) -> bar-number evidence, and kept as <words>
- other lines inside the music    -> <words> on the nearest staff
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .layout import Page, Staff, System, Text

RANGE = re.compile(r"^\[?(\d{1,4})\s*[-–—]\s*(\d{1,4})\]?$")
NUMBER = re.compile(r"^\d{1,4}$")
TO_BAR = re.compile(r"^\[?\s*to\s*\]?\s*(\d[\d ]{0,6})\s*([A-E])?\s*\]?$", re.I)  # "[to] 97", "[to 16]"
# "131A": a bar added after bar 131 (A-E: later letters are OCR noise, "120V")
LETTERED = re.compile(r"^(\d{1,4})([A-E])$")


def to_bar(text: str) -> tuple[int, str] | None:
    """Target bar of a cut mark: "[to] 97" -> (97, ""), "[to] 132C" -> (132, "C")."""
    m = TO_BAR.match(text.strip())
    if not m:
        return None
    letter = (m.group(2) or "").upper()
    return int(m.group(1).replace(" ", "")), letter


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
    jumps: list[tuple[Placed, tuple[int, str]]] = field(default_factory=list)  # "[to] 97" -> (97, "")
    lettered: list[tuple[Placed, tuple[int, str]]] = field(default_factory=list)  # "131A"
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
    first_top = systems[0].all_staves[0].top
    last_bottom = systems[-1].bottom
    # first system that is read when the ones above it are skipped (the end of the
    # previous piece): the new title above it is a header too
    first_read = next((s for s in systems if not s.skip), None)
    if first_read is systems[0]:
        first_read = None

    def is_header(ln: Line, top: float) -> bool:
        return ln.bottom < top - 12 * il or (
            ln.bottom < top and bool(ln.roles & HEADER_ROLES) and is_words(ln.text)
            and ln.bottom < top - 4 * il)

    for ln in lines(page):
        t = ln.text
        if not t:
            continue
        footer = ln.top > last_bottom + 8 * il
        if is_header(ln, first_top) or footer:
            if is_words(t) or NUMBER.match(t):
                res.credits.append(ln)
            continue
        all_staves = [st for s in systems for st in s.all_staves]
        staff, above = nearest_staff(all_staves, ln.cy)
        if above and (to_bar(t) is not None or LETTERED.match(t.replace(" ", ""))):
            # printed like a bar number, below the staff it belongs to: often nearer to the
            # next system than the 1.5 rule allows
            up = [s for s in all_staves if s.bottom < ln.cy]
            if up:
                st_up = max(up, key=lambda s: s.bottom)
                if ln.top - st_up.bottom <= 8 * st_up.interline:
                    staff, above = st_up, False
        sy = next(s for s in systems if staff in s.staves or staff in s.dropped)
        if sy.skip:
            continue
        if sy is first_read and is_header(ln, sy.all_staves[0].top):
            if is_words(t):
                res.credits.append(ln)
            continue
        if staff in sy.dropped:
            # above the system: tempo, rehearsal marks, labels -> onto the top kept staff;
            # lyrics and labels of a left-out staff are dropped with it
            if not (above and staff is sy.all_staves[0]):
                continue
            staff = sy.staves[0]
        atoms = sorted(ln.atoms, key=lambda a: a.x)
        if len(atoms) > 1 and NUMBER.match(atoms[0].value) and is_words(t):
            # boxed rehearsal number printed right before a label ("10 Bell Tree")
            res.rehearsals.append((Placed(Line(ln.page, atoms[:1]), sy, staff, above),
                                   atoms[0].value))
            ln = Line(ln.page, atoms[1:])
            t = ln.text
        pl = Placed(ln, sy, staff, above)
        if (target := to_bar(t)) is not None:
            res.jumps.append((pl, target))
            res.words.append(pl)          # the text stays in the score too
            continue
        m = RANGE.match(t.replace(" ", ""))
        if m:
            if int(m.group(1)) < int(m.group(2)):
                res.ranges.append((pl, int(m.group(1)), int(m.group(2))))
        elif lm := LETTERED.match(t.replace(" ", "")):
            res.lettered.append((pl, (int(lm.group(1)), lm.group(2))))
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
