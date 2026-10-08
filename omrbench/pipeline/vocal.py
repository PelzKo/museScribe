"""Vocal scores (piano reduction): lyrics, dynamics and hairpins from the page layout.

Audiveris OCRs the syllables well (lyric items with their syllabic, verse and staff) but
attaches only part of them to notes in its MusicXML, and homr reads no text at all.
Its dynamics and hairpins are found well too, but in its MusicXML they often hang on
the wrong part (piano marks on a voice) and hairpins get joined to far-away stops.
So all three are placed here from their position on the page:

- the x of every note comes from Audiveris' chords on the staff; the bar's notes
  (whichever engine they came from) are matched to them by order when the counts
  agree, else placed by onset across the bar
- a syllable goes to the note above it
- a dynamic / hairpin between the piano staves (or below them) is the piano's; above a
  vocal staff it is that voice's (vocal scores print voice dynamics above the staff)
- a hairpin runs from the note at its open end to the note at its tip; it never leaves
  its system, so its length is what is printed
"""
from __future__ import annotations

import re

from lxml import etree

from . import bars as B
from .layout import Mark, Page, Staff, System, Text

_LABEL = re.compile(r"^[A-Z][A-Z .'’+#\d]*[:;]$")     # "MEN:" read as a syllable
MARK_TYPES = ("dynamics", "wedge")


def _usable(t: Text) -> bool:
    v = t.value.strip()
    return bool(re.search(r"[^\W\d_]", v)) and not _LABEL.match(v)


def _positions(plan, gi: int, i: int, staves: list[Staff], page: Page, D: int,
               staff_no: int | None = None) -> list[tuple[float, int, etree._Element]]:
    """(x, onset, first note) of every onset with notes in bar i of group gi, on one
    staff of the group (staff_no) or on all of them."""
    l, r = plan.xs[i]
    il = staves[0].interline
    by_staff = B.sounding(plan.chosen[gi][i])
    notes: dict[int, etree._Element] = {}
    for s, evs in sorted(by_staff.items()):
        if staff_no is None or s == staff_no:
            for on, n in evs:
                notes.setdefault(on, n)
    if not notes:
        return []
    ids = {st.id for k, st in enumerate(staves, start=1) if staff_no is None or k == staff_no}
    xs: list[float] = []
    for c in sorted((c for c in page.chords if c.staff in ids and not c.small
                     and l <= c.x + c.w / 2 < r), key=lambda c: c.x):
        cx = c.x + c.w / 2
        if not xs or cx - xs[-1] >= 0.8 * il:
            xs.append(cx)
    ons = sorted(notes)
    if len(xs) != len(ons):
        length = B.bar_length(plan.times[i], D) or ons[-1] + 1
        lo, hi = l + 0.04 * (r - l), r - 0.04 * (r - l)
        xs = [lo + (hi - lo) * on / length for on in ons]
    return [(x, on, notes[on]) for x, on in zip(xs, ons)]


def _bar_index(plan, x: float) -> int | None:
    for i, (l, r) in enumerate(plan.xs):
        if r > l and l <= x < r:
            return i
    return None


# ----------------------------------------------------------------------------- lyrics

def _lyric(t: Text, extend: bool) -> etree._Element:
    ly = etree.Element("lyric", number=str(t.verse or 1))
    if t.syllabic in ("single", "begin", "middle", "end"):
        etree.SubElement(ly, "syllabic").text = t.syllabic
    etree.SubElement(ly, "text").text = t.value.strip()
    if extend:
        etree.SubElement(ly, "extend")
    return ly


def _put(note: etree._Element, ly: etree._Element) -> None:
    idx = next((i for i, c in enumerate(note) if c.tag in ("play", "listen")), len(note))
    note.insert(idx, ly)


def attach_lyrics(plans, pages: list[Page], D: int, stats) -> None:
    by_page = {p.number: p for p in pages}
    for plan in plans:
        sy = plan.system
        if sy.piano_group is None or not plan.n or sy.page not in by_page:
            continue
        for gi, g in enumerate(sy.groups()):
            if gi != sy.piano_group and gi in plan.chosen:
                _attach_staff(plan, gi, g[0], by_page[sy.page], D, stats)


def _attach_staff(plan, gi: int, st: Staff, page: Page, D: int, stats) -> None:
    il = st.interline
    # sung text is printed below its staff
    syls = [t for t in page.texts if t.staff == st.id and t.kind == "syllable"
            and t.y >= st.bottom - il and _usable(t)]
    exts = [t for t in page.texts if t.staff == st.id and t.kind == "extension"]
    for i in range(plan.n):
        l, r = plan.xs[i]
        if r <= l:
            continue                # rest bar inserted by the alignment
        here = sorted((t for t in syls if l <= t.x + t.w / 2 < r), key=lambda t: t.x)
        if not here:
            continue
        pos = _positions(plan, gi, i, [st], page, D, staff_no=1)
        if not pos:
            stats.lyrics_unplaced += len(here)
            continue
        for verse in sorted({t.verse for t in here}):
            last = -1
            for t in (t for t in here if t.verse == verse):
                cx = t.x + t.w / 2
                cands = [k for k in range(last + 1, len(pos))
                         if abs(pos[k][0] - cx) <= max(3 * il, 0.75 * t.w)]
                if not cands:
                    stats.lyrics_unplaced += 1
                    continue
                k = min(cands, key=lambda k: abs(pos[k][0] - cx))
                note = pos[k][2]
                if any(ly.get("number") == str(verse) for ly in note.findall("lyric")):
                    stats.lyrics_unplaced += 1
                    continue
                extend = any(e.verse == t.verse and 0 <= e.x - (t.x + t.w) <= 1.5 * il for e in exts)
                _put(note, _lyric(t, extend))
                stats.lyrics += 1
                last = k


# ------------------------------------------------------------------ dynamics, wedges

def strip_marks(bar: B.Bar) -> None:
    """Remove the engines' dynamics and hairpins (placed again from the layout)."""
    items = []
    for el in bar.items:
        if el.tag == "direction":
            for dt in el.findall("direction-type"):
                for k in [k for k in dt if k.tag in MARK_TYPES]:
                    dt.remove(k)
                if not len(dt):
                    el.remove(dt)
            if el.find("direction-type") is None:
                continue
        elif el.tag == "note":
            for nt in el.findall("notations"):
                for d in nt.findall("dynamics"):
                    nt.remove(d)
        items.append(el)
    bar.items = items


def _owner(sy: System, y: float) -> tuple[int, int, str] | None:
    """(group, staff number in it, placement) of a mark at height y."""
    staves = sorted(sy.staves, key=lambda s: s.top)
    groups = sy.groups()

    def where(st: Staff) -> tuple[int, int]:
        for gi, g in enumerate(groups):
            if st in g:
                return gi, g.index(st) + 1
        return 0, 1

    piano = groups[sy.piano_group] if sy.piano_group is not None and sy.piano_group < len(groups) else []
    inside = next((s for s in staves if s.top <= y <= s.bottom), None)
    if inside is not None:
        gi, no = where(inside)
        return gi, no, "below"
    above = [s for s in staves if s.bottom < y]
    below = [s for s in staves if s.top > y]
    if piano and len(piano) > 1 and above and below and above[-1] in piano and below[0] in piano:
        gi, _ = where(piano[0])
        return gi, 1, "below"           # between the piano staves: both hands
    if not below:
        gi, no = where(above[-1])
        return gi, no, "below"
    if above and below[0] in piano and above[-1] not in piano:
        # between a voice and the piano: the nearer one
        if y - above[-1].bottom < below[0].top - y:
            gi, no = where(above[-1])
            return gi, no, "below"
    gi, no = where(below[0])
    return gi, no, "above"


def _system_of(page: Page, plans_on_page, y: float):
    best, dist = None, float("inf")
    for p in plans_on_page:
        sy = p.system
        d = 0.0 if sy.top <= y <= sy.bottom else min(abs(y - sy.top), abs(y - sy.bottom))
        if d < dist:
            best, dist = p, d
    if best is None or dist > 8 * best.system.staves[0].interline:
        return None
    return best


def _nearest_onset(pos, x: float, il: float, at_or_after: bool = False) -> int | None:
    if not pos:
        return None
    if at_or_after:
        later = [p for p in pos if p[0] >= x - 1.5 * il]
        if later:
            return later[0][1]
        return None
    return min(pos, key=lambda p: abs(p[0] - x))[1]


def _dynamics_el(shape: str, placement: str) -> etree._Element:
    d = etree.Element("direction", placement=placement)
    dyn = etree.SubElement(etree.SubElement(d, "direction-type"), "dynamics")
    etree.SubElement(dyn, shape.split("_", 1)[1].lower())
    return d


def _wedge_el(kind: str, placement: str) -> etree._Element:
    d = etree.Element("direction", placement=placement)
    etree.SubElement(etree.SubElement(d, "direction-type"), "wedge", type=kind, number="1")
    return d


def place_marks(plans, pages: list[Page], D: int, stats) -> None:
    """Replace the engines' dynamics and hairpins with the ones on the page."""
    for plan in plans:
        for g in plan.chosen.values():
            for bar in g:
                strip_marks(bar)
    on_page: dict[int, list] = {}
    for p in plans:
        if p.n and p.chosen and not p.system.skip:
            on_page.setdefault(p.system.page, []).append(p)
    for page in pages:
        for mk in page.marks:
            plan = _system_of(page, on_page.get(page.number, []), mk.cy)
            if plan is None:
                stats.marks_unplaced += 1
                continue
            sy = plan.system
            gi, staff_no, placement = _owner(sy, mk.cy)
            if gi not in plan.chosen:
                stats.marks_unplaced += 1
                continue
            g = sy.groups()[gi]
            il = g[0].interline
            if mk.kind == "dynamics":
                i = _bar_index(plan, mk.x + mk.w / 2)
                if i is None:
                    stats.marks_unplaced += 1
                    continue
                pos = _positions(plan, gi, i, g, page, D)
                on = _nearest_onset(pos, mk.x + mk.w / 2, il) or 0
                B.add_direction(plan.chosen[gi][i], _dynamics_el(mk.shape, placement), on, staff_no)
                stats.dynamics += 1
                continue
            kind = {"CRESCENDO": "crescendo", "DIMINUENDO": "diminuendo"}.get(mk.shape)
            i0 = _bar_index(plan, mk.x + 1)
            i1 = _bar_index(plan, mk.x + mk.w - 1)
            if kind is None or i0 is None:
                stats.marks_unplaced += 1
                continue
            pos0 = _positions(plan, gi, i0, g, page, D)
            on0 = _nearest_onset(pos0, mk.x, il, at_or_after=True)
            if on0 is None:                 # opens after the bar's last note
                on0 = B.bar_length(plan.times[i0], D) or 0
            if i1 is None:                  # runs to the system end
                i1 = max(k for k in range(plan.n) if plan.xs[k][1] > plan.xs[k][0])
                on1 = B.bar_length(plan.times[i1], D) or 0
            else:
                pos1 = _positions(plan, gi, i1, g, page, D)
                end = mk.x + mk.w
                before = [p for p in pos1 if p[0] <= end + 1.5 * il]
                after_last = not pos1 or end > pos1[-1][0] + 2 * il
                on1 = (B.bar_length(plan.times[i1], D) or 0) if after_last or not before \
                    else before[-1][1]
            if (i1, on1) <= (i0, on0):
                stats.marks_unplaced += 1
                continue
            # add_direction puts it first in the bar: the stop first, so that in a bar
            # with both the start comes before it
            B.add_direction(plan.chosen[gi][i1], _wedge_el("stop", placement), on1, staff_no)
            B.add_direction(plan.chosen[gi][i0], _wedge_el(kind, placement), on0, staff_no)
            stats.wedges += 1
