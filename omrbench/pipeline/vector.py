"""Born-digital pages read from their vector drawing: slash (rhythm) notation, measure repeats, barlines.

Neither Audiveris nor homr reads slash noteheads (Ghost 20 Guitar: 76 of 608 slash rhythms right).
On a born-digital page they are music-font glyphs on the middle staff line, with stems (lines),
beams (filled shapes), flags, rests, dots and ties (filled curves) as vector drawings, so their
rhythm can be read exactly. A bar is used only if it holds slashes and no normal noteheads, and its
durations fill the bar.

shortcut: glyph codes of the EngraverFontSet font (Ghost / Finale engravings); add a font's codes
to GLYPHS when another show uses another music font.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

GLYPHS = {   # font -> {char: (kind, quarters)}
    "EngraverFontSet": {"Û": ("slash", None), "Ó": ("rest", Fraction(2)),
                        "∑": ("rest", Fraction(4)), "‰": ("rest", Fraction(1, 2)),
                        "Œ": ("rest", Fraction(1)), "œ": ("head", None),
                        "Ï": ("head", None), "ú": ("head", None), "w": ("head", None),
                        "J": ("flag", None), "j": ("flag", None), ".": ("dot", None)},
}


@dataclass
class Event:
    x: float
    kind: str                       # slash | rest
    dur: Fraction                   # quarters
    tie_start: bool = False
    tie_stop: bool = False


@dataclass
class SlashBar:
    page: int                       # Page.number
    x0: float                       # bar left / right, page (image) coordinates
    x1: float
    top: float                      # staff top / bottom
    bottom: float
    events: list[Event] = field(default_factory=list)

    @property
    def length(self) -> Fraction:
        return sum((e.dur for e in self.events), Fraction(0))


def _staves(lines: list[tuple]) -> list[list[float]]:
    """Five-line staves from long horizontal lines (x0, x1, y)."""
    ys = sorted({round(y, 1) for _, _, y in lines})
    out, cur = [], []
    for y in ys:
        if cur and y - cur[-1] > 1.5 * (cur[1] - cur[0] if len(cur) > 1 else 6):
            if len(cur) == 5:
                out.append(cur)
            cur = []
        cur.append(y)
    if len(cur) == 5:
        out.append(cur)
    return out


def _barlines(vlines: list[tuple], top: float, bottom: float, left: float, right: float) -> list[float]:
    """x of the barlines inside a staff: vertical lines over its full height (stems are drawn
    0.5-1 pt wide and skipped before); a double or final barline counts once."""
    sp = (bottom - top) / 4
    xs = sorted(x for x, y0, y1 in vlines if y0 <= top + 0.5 and y1 >= bottom - 0.5 and left + sp < x < right - sp)
    out: list[float] = []
    for x in xs:
        if out and x - out[-1] < sp:
            continue
        out.append(x)
    return out


def read_page(pdf_page, page) -> list[SlashBar]:
    """Slash bars of one vector page, in the coordinates of `page` (layout.Page)."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    glyphs = []                     # (x, y, w, kind, dur)
    for block in pdf_page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                table = next((t for f, t in GLYPHS.items() if span["font"].startswith(f)), None)
                if table is None:
                    continue
                for ch in span["chars"]:
                    g = table.get(ch["c"])
                    if g:
                        b = ch["bbox"]
                        glyphs.append((b[0], ch["origin"][1], b[2] - b[0], *g))
    if not any(k == "slash" for *_, k, _ in glyphs):
        return []
    hlines, vthin, stems, fills, curves = [], [], [], [], []
    for d in pdf_page.get_drawings():
        r = d["rect"]
        for it in d["items"]:
            if it[0] == "l" and d["type"] == "s":
                (a, b) = it[1], it[2]
                if abs(a.y - b.y) < 0.1 and abs(b.x - a.x) > 100:
                    hlines.append((a.x, b.x, a.y))
                elif abs(a.x - b.x) < 0.1:
                    (stems if 0.5 < (d.get("width") or 0) < 1.0 else vthin).append((a.x, min(a.y, b.y), max(a.y, b.y)))
        if d["type"] == "f" and any(it[0] == "c" for it in d["items"]):
            curves.append((r.x0, r.x1, r.y0, r.y1))
        elif d["type"] == "f":
            fills.append((r.x0, r.x1, r.y0, r.y1))
            if r.height > 4 * r.width:      # a thick barline drawn as a filled box
                vthin.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
    out = []
    for st in _staves(hlines):
        top, mid, bottom = st[0], st[2], st[4]
        sp = (bottom - top) / 4
        left = min(x0 for x0, _, y in hlines if abs(y - top) < 0.2)
        right = max(x1 for _, x1, y in hlines if abs(y - top) < 0.2)
        edges = [left] + _barlines(vthin, top, bottom, left, right) + [right]
        mine = [g for g in glyphs if top - 3 * sp <= g[1] <= bottom + 4 * sp]
        heads = sorted((g for g in mine if g[3] == "slash" and abs(g[1] - mid) < sp / 2), key=lambda g: g[0])
        events_by_x = {}
        for x, y, w, kind, dur in heads:
            stem = next((s for s in stems if x - 1 <= s[0] <= x + w + 1 and s[1] < mid + sp and s[2] > mid), None)
            if dur is None:
                dur = Fraction(1)
                if stem:
                    end = stem[2] if stem[2] > mid + sp else stem[1]
                    beams = [f for f in fills if f[0] - 0.5 <= stem[0] <= f[1] + 0.5 and end - 2.5 * sp <= f[2] <= end + sp]
                    flag = any(g[3] == "flag" and abs(g[0] - stem[0]) < w and abs(g[1] - end) < 3 * sp for g in mine)
                    n = max(len(beams), 1 if flag else 0)
                    dur = Fraction(1, 2 ** n)
            events_by_x[x] = Event(x, "slash", dur)
        for x, y, w, kind, dur in mine:
            if kind == "rest" and abs(y - mid) < 1.5 * sp:
                events_by_x[x] = Event(x, "rest", dur)
        evs = sorted(events_by_x.values(), key=lambda e: e.x)
        for e in evs:   # augmentation dot: right of the head / rest, in the space above the middle line
            if any(g[3] == "dot" and e.x + 3 <= g[0] <= e.x + 0.9 * 4 * sp and abs(g[1] - (mid - sp / 2)) < sp / 2
                   for g in mine):
                e.dur *= Fraction(3, 2)
        slash_evs = [e for e in evs if e.kind == "slash"]
        for x0, x1, y0, y1 in curves:   # ties: a curve from one slash to the next
            if not (mid - 3 * sp <= y0 <= mid + 3 * sp):
                continue
            a = next((e for e in slash_evs if abs(e.x - x0) < 2 * sp), None)
            b = next((e for e in slash_evs if e.x > (a.x if a else x0) and abs(e.x - x1) < 2 * sp), None)
            if a and b:
                a.tie_start, b.tie_stop = True, True
        normal = [g for g in mine if g[3] == "head"]
        for l, r in zip(edges, edges[1:]):
            bar_evs = [e for e in evs if l <= e.x < r]
            if not any(e.kind == "slash" for e in bar_evs) or any(l <= g[0] < r for g in normal):
                continue
            out.append(SlashBar(page.number, l * sx, r * sx, top * sx, bottom * sx,
                                [Event(e.x * sx, e.kind, e.dur, e.tie_start, e.tie_stop) for e in bar_evs]))
    return out


def read(pdf, pages: list) -> list[SlashBar]:
    """Slash bars of the vector pages of `pdf` (pages[i] is PDF page i)."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return [b for i, p in enumerate(doc) if i < len(pages) and p.get_fonts()
                and classify_page(p, i + 1).kind == "vector" for b in read_page(p, pages[i])]


REPEAT_GLYPHS = {"EngraverFontSet": {"‘": 1, "«": 2}}   # one-bar repeat (%), two-bar repeat


@dataclass
class Repeat:
    page: int
    x: float            # glyph centre (a two-bar repeat sits on the barline between its bars)
    top: float          # staff top
    bars: int
    index: int = -1     # bar of the sign within the system (by the printed barlines), its first bar
    count: int = 0      # bars of the system
    number: int = 0     # printed bar number of that bar (0: unknown)


def read_repeats(pdf_page, page) -> list[Repeat]:
    """Measure-repeat signs on the middle of a staff, in the coordinates of `page`."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    signs, numbers = [], []
    for block in pdf_page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = "".join(ch["c"] for ch in span["chars"]).strip()
                if text.isdigit() and span["chars"]:
                    numbers.append((span["bbox"][0], span["bbox"][3], int(text)))
                table = next((t for f, t in REPEAT_GLYPHS.items() if span["font"].startswith(f)), {})
                for ch in span["chars"]:
                    if ch["c"] in table:
                        b = ch["bbox"]
                        signs.append(((b[0] + b[2]) / 2, ch["origin"][1], table[ch["c"]]))
    if not signs:
        return []
    hlines, vthin = [], []
    for d in pdf_page.get_drawings():
        for it in d["items"]:
            if it[0] == "l" and d["type"] == "s":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.1 and abs(b.x - a.x) > 100:
                    hlines.append((a.x, b.x, a.y))
                elif abs(a.x - b.x) < 0.1 and not 0.5 < (d.get("width") or 0) < 1.0:
                    vthin.append((a.x, min(a.y, b.y), max(a.y, b.y)))
        r = d["rect"]
        if d["type"] == "f" and r.height > 4 * r.width:
            vthin.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
    out = []
    for st in _staves(hlines):
        sp = (st[4] - st[0]) / 4
        left = min(x0 for x0, _, y in hlines if abs(y - st[0]) < 0.2)
        right = max(x1 for _, x1, y in hlines if abs(y - st[0]) < 0.2)
        inner = _barlines(vthin, st[0], st[4], left, right)
        # the system's first bar number, printed above the staff start
        start = next((v for x, y, v in numbers if x < left + 3 * sp and st[0] - 4 * sp < y <= st[0] + sp), 0)
        for x, y, n in signs:
            if abs(y - st[2]) < 1.5 * sp:
                first = x - (2 * sp if n == 2 else 0)      # a two-bar sign sits on the barline
                index = sum(1 for b in inner if b < first)
                out.append(Repeat(page.number, x * sx, st[0] * sx, n, index, len(inner) + 1,
                                  start + index if start else 0))
    return out


def read_all_repeats(pdf, pages: list) -> list[Repeat]:
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return [r for i, p in enumerate(doc) if i < len(pages) and p.get_fonts()
                and classify_page(p, i + 1).kind == "vector" for r in read_repeats(p, pages[i])]


def read_systems(pdf_page, page) -> list[tuple[float, list[tuple[float, float]]]]:
    """(staff top, [(left, right) of every printed bar]) of each staff, in the coordinates of `page`:
    the exact bar count and bar x ranges of a born-digital page."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    hlines, vlines = [], []
    for d in pdf_page.get_drawings():
        r = d["rect"]
        for it in d["items"]:
            if it[0] == "l" and d["type"] == "s":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.1 and abs(b.x - a.x) > 100:
                    hlines.append((a.x, b.x, a.y))
                elif abs(a.x - b.x) < 0.1 and not 0.5 < (d.get("width") or 0) < 1.0:
                    vlines.append((a.x, min(a.y, b.y), max(a.y, b.y)))
        if d["type"] == "f" and r.height > 4 * r.width:
            vlines.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
    out = []
    for st in _staves(hlines):
        left = min(x0 for x0, _, y in hlines if abs(y - st[0]) < 0.2)
        right = max(x1 for _, x1, y in hlines if abs(y - st[0]) < 0.2)
        edges = [left] + _barlines(vlines, st[0], st[4], left, right) + [right]
        out.append((st[0] * sx, [(a * sx, b * sx) for a, b in zip(edges, edges[1:])]))
    return out


def read_all_systems(pdf, pages: list) -> dict[int, list]:
    """Page.number -> read_systems of the vector pages of `pdf`."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return {pages[i].number: read_systems(p, pages[i]) for i, p in enumerate(doc)
                if i < len(pages) and p.get_fonts() and classify_page(p, i + 1).kind == "vector"}
