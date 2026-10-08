"""Page layout from an Audiveris .omr project: systems, staves, measure stacks, text.

Audiveris gets the geometry (staff lines, barlines) right far more often than the
music, so the pipeline uses it as the frame that everything else is placed on.
Coordinates are pixels of the sheet image Audiveris worked on (`Page.width/height`).
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Staff:
    id: int                  # global id on the sheet (as used by inter "staff" attributes)
    part: int                # index of the Audiveris part within the system
    top: float
    bottom: float
    left: float
    right: float
    clef: str = ""           # first clef shape in the header, e.g. G_CLEF, PERCUSSION_CLEF
    header: float = 0.0      # x where the header (clef, key) ends
    apart: int = 0           # index of the Audiveris part (`part` may be regrouped)
    pstaff: int = 1          # staff number within that Audiveris part

    @property
    def interline(self) -> float:
        return (self.bottom - self.top) / 4 if self.bottom > self.top else 20.0


@dataclass
class Stack:
    id: int
    left: float
    right: float
    special: str | None = None   # MULTI_REST, CAUTIONARY, ...


@dataclass
class System:
    page: int
    id: int
    staves: list[Staff]
    stacks: list[Stack]      # measures as exported (cautionary stacks removed)
    logical: list[int] = field(default_factory=list)  # output track id per group
    book: int = 0            # index of the Audiveris book (per-sheet fallback = one per sheet)
    alogical: list[int] = field(default_factory=list)  # Audiveris logical part id per part index
    dropped: list[Staff] = field(default_factory=list)  # staves left out (meta keep_staves)
    skip: bool = False       # left out entirely (meta skip_systems)
    regrouped: bool = False  # groups are not the Audiveris parts
    piano_group: int | None = None   # vocal score: index of the piano group (the last)

    @property
    def all_staves(self) -> list[Staff]:
        return sorted(self.staves + self.dropped, key=lambda s: s.top)

    @property
    def vocal_staves(self) -> list[Staff]:
        """Vocal score: the staves above the piano."""
        if self.piano_group is None:
            return []
        return [st for gi, g in enumerate(self.groups()) if gi != self.piano_group for st in g]

    @property
    def top(self) -> float:
        return min(s.top for s in self.staves)

    @property
    def bottom(self) -> float:
        return max(s.bottom for s in self.staves)

    def groups(self) -> list[list[Staff]]:
        """Staves grouped by Audiveris part (a piano is one group of two)."""
        out: dict[int, list[Staff]] = {}
        for s in self.staves:
            out.setdefault(s.part, []).append(s)
        return [out[k] for k in sorted(out)]

    def stack_at(self, x: float) -> int | None:
        """Index into self.stacks of the measure containing x (None if left of all)."""
        for i, st in enumerate(self.stacks):
            if st.left - 5 <= x < st.right:
                return i
        return len(self.stacks) - 1 if self.stacks and x >= self.stacks[-1].right else None


@dataclass
class Text:
    page: int
    staff: int               # related staff id (0 if unknown)
    x: float
    y: float
    w: float
    h: float
    value: str
    kind: str                # word | number | hyphen | syllable | punctuation
    role: str = ""           # sentence role (Direction, Title, UnknownRole, Lyrics, ...)
    line: int = 0            # id of the sentence / lyric line it belongs to
    font: str = ""           # Audiveris font code, e.g. "BIS-35" = bold italic serif 35
    syllabic: str = ""       # lyric items: single | begin | middle | end
    verse: int = 1           # lyric items: number of their lyric line


@dataclass
class Chord:
    staff: int               # staff id
    x: float
    y: float
    w: float
    h: float
    small: bool              # cue-size heads (Audiveris small-chord)
    grade: float = 0.0


@dataclass
class Mark:
    kind: str                # dynamics | wedge
    shape: str               # DYNAMICS_MF, CRESCENDO, DIMINUENDO, ...
    x: float
    y: float
    w: float
    h: float
    grade: float = 0.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Page:
    number: int
    width: int
    height: int
    systems: list[System] = field(default_factory=list)
    texts: list[Text] = field(default_factory=list)
    chords: list[Chord] = field(default_factory=list)
    marks: list[Mark] = field(default_factory=list)

    def staff(self, sid: int) -> tuple[System, Staff] | None:
        for sy in self.systems:
            for st in sy.staves:
                if st.id == sid:
                    return sy, st
        return None


def _f(el, name, default=0.0) -> float:
    try:
        return float(el.get(name))
    except (TypeError, ValueError):
        return default


def _bounds(el) -> tuple[float, float, float, float]:
    b = el.find("bounds")
    if b is None:
        return 0.0, 0.0, 0.0, 0.0
    return _f(b, "x"), _f(b, "y"), _f(b, "w"), _f(b, "h")


def _staff_geometry(staff_el) -> tuple[float, float]:
    ys = []
    for line in staff_el.findall("lines/line"):
        pts = [_f(p, "y") for p in line.findall("point")]
        if pts:
            ys.append(sum(pts) / len(pts))
    if not ys:
        return 0.0, 0.0
    return min(ys), max(ys)


def _logical_ids(book_xml: bytes) -> dict[int, list[list[int]]]:
    """sheet number -> per system (in order) the logical part id of each part."""
    out: dict[int, list[list[int]]] = {}
    root = ET.fromstring(book_xml)
    for sh in root.iter("sheet"):
        systems = []
        for sy in sh.iter("system"):
            systems.append([int(p.get("logical-id") or 0) for p in sy.findall("part")])
        out[int(sh.get("number"))] = systems
    return out


def _parse_sheet(root: ET.Element, number: int) -> Page:
    pic = root.find("picture")
    page = Page(number, int(_f(pic, "width")) if pic is not None else 0,
                int(_f(pic, "height")) if pic is not None else 0)
    shapes: dict[str, str] = {}
    for el in root.iter():
        if el.get("id") and el.get("shape"):
            shapes[el.get("id")] = el.get("shape")
    for sy_el in root.iter("system"):
        staves = []
        for pi, part in enumerate(sy_el.findall("part")):
            for si, st in enumerate(part.findall("staff"), start=1):
                top, bottom = _staff_geometry(st)
                clef = ""
                c = st.find("header/clef")
                if c is not None and c.text:
                    clef = shapes.get(c.text.strip(), "")
                h = st.find("header")
                staves.append(Staff(int(st.get("id")), pi, top, bottom,
                                    _f(st, "left"), _f(st, "right"), clef,
                                    _f(h, "stop") if h is not None else 0.0, pi, si))
        stacks = [Stack(int(s.get("id")), _f(s, "left"), _f(s, "right"), s.get("special"))
                  for s in sy_el.findall("stack") if s.get("special") != "CAUTIONARY"]
        page.systems.append(System(number, int(sy_el.get("id")), staves, stacks))

    # text: words live inside sentences, lyric items inside lyric lines (by bounds)
    lines = []
    verse: dict[int, int] = {}
    for tag in ("sentence", "lyric-line"):
        for el in root.iter(tag):
            lines.append((int(el.get("id")), el.get("role", ""), _bounds(el)))
            if tag == "lyric-line" and (el.get("number") or "").isdigit():
                verse[int(el.get("id"))] = int(el.get("number"))

    def owner(x, y, w, h):
        for lid, role, (lx, ly, lw, lh) in lines:
            if lx - 2 <= x and x + w <= lx + lw + 2 and ly - 2 <= y and y + h <= ly + lh + 2:
                return lid, role
        return 0, ""

    for el in root.iter("word"):
        x, y, w, h = _bounds(el)
        lid, role = owner(x, y, w, h)
        page.texts.append(Text(number, int(el.get("staff") or 0), x, y, w, h,
                               el.get("value", ""), "word", role, lid, el.get("font", "")))
    for tag, small in (("head-chord", False), ("small-chord", True)):
        for el in root.iter(tag):
            x, y, w, h = _bounds(el)
            page.chords.append(Chord(int(el.get("staff") or 0), x, y, w, h, small,
                                     _f(el, "grade")))
    for tag in ("dynamics", "wedge"):
        for el in root.iter(tag):
            if el.get("shape"):
                page.marks.append(Mark(tag, el.get("shape"), *_bounds(el), _f(el, "ctx-grade")))
    for el in root.iter("lyric-item"):
        x, y, w, h = _bounds(el)
        lid, role = owner(x, y, w, h)
        page.texts.append(Text(number, int(el.get("staff") or 0), x, y, w, h,
                               el.get("value", ""), (el.get("kind") or "syllable").lower(),
                               role or "Lyrics", lid, el.get("font", ""),
                               (el.get("syllabic") or "single").lower(), verse.get(lid, 1)))
    return page


def load(omr: Path) -> list[Page]:
    """Pages in order from one .omr, or from a folder of per-sheet .omr books."""
    books = sorted(omr.rglob("*.omr")) if omr.is_dir() else [omr]
    pages: list[Page] = []
    for bi, book in enumerate(books):
        with zipfile.ZipFile(book) as z:
            names = sorted((n for n in z.namelist() if re.fullmatch(r"sheet#\d+/sheet#\d+\.xml", n)),
                           key=lambda n: int(re.search(r"#(\d+)/", n).group(1)))
            logical = _logical_ids(z.read("book.xml")) if "book.xml" in z.namelist() else {}
            for n in names:
                page = _parse_sheet(ET.fromstring(z.read(n)), len(pages) + 1)
                ids = logical.get(int(re.search(r"#(\d+)/", n).group(1)), [])
                for i, sy in enumerate(page.systems):
                    sy.book = bi
                    n_parts = len(sy.groups())
                    sy.logical = ids[i] if i < len(ids) and len(ids[i]) == n_parts \
                        else list(range(1, n_parts + 1))
                    sy.alogical = list(sy.logical)
                # after the book.xml mapping (which counts every system): drop empty ones
                page.systems = [sy for sy in page.systems if sy.staves]
                pages.append(page)
    return pages


def where(systems: list[System], k: int) -> str:
    """Global system k for messages: page, system on that page, and the 1-based global
    number that skip_systems uses."""
    sy = systems[k]
    on_page = [s for s in systems if s.page == sy.page].index(sy) + 1
    return f"page {sy.page} system {on_page} (#{k + 1})"


PIANO_TRACK = 1000      # output track of the piano in a vocal score (after the voices)


def regroup(pages: list[Page], keep_bottom: int | None = None, singles: bool = False,
            skip: set[int] | None = None, piano_bottom: int | None = None) -> None:
    """Change what the pipeline reads as staff groups, in place.

    keep_bottom: only the lowest n staves of every system, read as one group (a
        conductor part: reference / vocal staves above the piano); the others are kept
        in `System.dropped` so text above them can still be placed
    singles: every staff its own group (condensed percussion: Timpani over a
        percussion staff are two instruments, not a grand staff)
    skip: systems (1-based, counted over all pages) to leave out entirely
    piano_bottom: vocal score: the lowest n staves are the piano (track PIANO_TRACK),
        every staff above it its own group (track = position from the top)
    Group k of a system then becomes output track k (not the Audiveris part), so the
    same group lands in the same part whatever Audiveris made of the staves above it.
    """
    k = 0
    for page in pages:
        for sy in page.systems:
            k += 1
            if skip and k in skip:
                sy.skip = True
            staves = sorted(sy.staves, key=lambda s: s.top)
            if piano_bottom:
                n_voc = max(0, len(staves) - piano_bottom)
                for i, st in enumerate(staves):
                    st.part = i if i < n_voc else n_voc
                sy.staves = staves
                sy.regrouped = True
                sy.piano_group = n_voc
                sy.logical = list(range(1, n_voc + 1)) + [PIANO_TRACK]
                continue
            if keep_bottom and len(staves) > keep_bottom:
                sy.dropped = staves[:-keep_bottom]
                staves = staves[-keep_bottom:]
            if keep_bottom:
                for st in staves:
                    st.part = 0
            elif singles:
                for i, st in enumerate(staves):
                    st.part = i
            else:
                continue
            sy.staves = staves
            sy.regrouped = True
            sy.logical = list(range(1, len(sy.groups()) + 1))
