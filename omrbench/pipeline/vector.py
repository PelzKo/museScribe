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
    "EngraverFontSet": {"Û": ("slash", None), "’": ("slash", None), "Ó": ("rest", Fraction(2)),
                        "∑": ("rest", Fraction(4)), "‰": ("rest", Fraction(1, 2)),
                        "Œ": ("rest", Fraction(1)), "œ": ("head", None),
                        "Ï": ("head", None), "ú": ("head", None), "w": ("head", None),
                        "J": ("flag", None), "j": ("flag", None), ".": ("dot", None),
                        ">": ("accent", None), "-": ("tenuto", None), "≈": ("rest", Fraction(1, 4)),
                        "ﬂ": ("accent-staccato", None), "˘": ("accent-staccato", None)},  # one glyph, both marks
    # drum heads: black normal / x heads take their value from the stem; ⊗ half (X), ⊗ / normal whole
    "MaestroPercussion": {"œ": ("drum", None), "x": ("drum", None), "X": ("drum", Fraction(2)),
                          "Y": ("drum", Fraction(4)), "w": ("drum", Fraction(4))},
}


@dataclass
class Event:
    x: float
    kind: str                       # slash | rest | drum
    dur: Fraction                   # quarters
    tie_start: bool = False
    tie_stop: bool = False
    marks: list = field(default_factory=list)   # accent | staccato | tenuto
    voice: int = 1                  # drums: 1 = stems up, 2 = stems down
    pos: tuple = ()                 # drums: staff positions of the chord ("C5", "F4")
    heads: int = 0                  # read_marks: heads in the column
    ties: list = field(default_factory=list)    # read_marks: tied heads, index from the top
    curved: bool = False            # read_marks: a tie / slur curve starts at the column


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
        return sum((e.dur for e in self.events if e.voice == 1), Fraction(0))


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


def _glyphs(pdf_page) -> list[tuple]:
    """(x, y, w, kind, quarters) of the music-font glyphs in GLYPHS; y = the head centre / baseline."""
    glyphs = []
    spans = [sp for b in pdf_page.get_text("rawdict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]]
    full = max((sp["size"] for sp in spans if sp["font"].startswith("MaestroPercussion")), default=0)
    for span in spans:
        table = next((t for f, t in GLYPHS.items() if span["font"].startswith(f)), None)
        if table is None:
            continue
        for ch in span["chars"]:
            g = table.get(ch["c"])
            if g and not (g[0] == "drum" and span["size"] < 0.8 * full):    # cue-size drum heads
                b = ch["bbox"]
                # "’" (Ghost 4 slashes) has its baseline a space below the head: use the box centre
                y = (b[1] + b[3]) / 2 if ch["c"] in CENTRED else ch["origin"][1]
                glyphs.append((b[0], y, b[2] - b[0], *g))
    return glyphs


def _drawings(pdf_page) -> tuple[list, list, list, list, list]:
    """Staff lines, barline candidates, stems, filled shapes (beams) and filled curves (ties)."""
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
    return hlines, vthin, stems, fills, curves


def _stem_value(stem, end: float, fills, mine, w: float, sp: float) -> Fraction:
    """Value of a black head from the beams / flag at its stem's free end."""
    beams = [f for f in fills if f[0] - 0.5 <= stem[0] <= f[1] + 0.5 and end - 2.5 * sp <= f[2] <= end + sp]
    flag = any(g[3] == "flag" and abs(g[0] - stem[0]) < w and abs(g[1] - end) < 3 * sp for g in mine)
    return Fraction(1, 2 ** max(len(beams), 1 if flag else 0))


def read_page(pdf_page, page) -> list[SlashBar]:
    """Slash bars of one vector page, in the coordinates of `page` (layout.Page)."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    glyphs = _glyphs(pdf_page)
    if not any(k == "slash" for *_, k, _ in glyphs):
        return []
    hlines, vthin, stems, fills, curves = _drawings(pdf_page)
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
                    dur = _stem_value(stem, stem[2] if stem[2] > mid + sp else stem[1], fills, mine, w, sp)
            events_by_x[x] = Event(x, "slash", dur)
        for x, y, w, kind, dur in mine:
            if kind == "rest" and abs(y - mid) < 1.5 * sp:
                events_by_x[x] = Event(x, "rest", dur)
        evs = sorted(events_by_x.values(), key=lambda e: e.x)
        for e in evs:   # articulations right above / below a slash (a dot there is a staccato)
            if e.kind == "slash":
                for g in mine:
                    if g[3] in ("accent", "tenuto", "dot") and abs(g[0] - e.x) < sp and sp < abs(g[1] - mid) < 4 * sp:
                        e.marks.append("staccato" if g[3] == "dot" else g[3])
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
                                [Event(e.x * sx, e.kind, e.dur, e.tie_start, e.tie_stop, e.marks) for e in bar_evs]))
    return out


STEPS = "CDEFGAB"


def read_drum_page(pdf_page, page) -> list[SlashBar]:
    """Drum-kit bars of one vector page: heads by staff position, stems up = voice 1, down = voice 2,
    values from beams / flags / dots, rests by height. A bar is kept only if every head has a value and
    voice 2 (if any) is as long as voice 1."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    glyphs = _glyphs(pdf_page)
    if not any(k == "drum" for *_, k, _ in glyphs):
        return []
    hlines, vthin, stems, fills, curves = _drawings(pdf_page)
    out = []
    for st in _staves(hlines):
        top, mid, bottom = st[0], st[2], st[4]
        sp = (bottom - top) / 4
        left = min(x0 for x0, _, y in hlines if abs(y - top) < 0.2)
        right = max(x1 for _, x1, y in hlines if abs(y - top) < 0.2)
        edges = [left] + _barlines(vthin, top, bottom, left, right) + [right]
        # marks sit beyond the stem end (Ghost 5: accent + staccato 6 spaces below the staff)
        mine = [g for g in glyphs if top - 4 * sp <= g[1] <= bottom + 4 * sp
                or (g[3] in ("accent", "tenuto", "accent-staccato") and top - 7 * sp <= g[1] <= bottom + 7 * sp)]
        chords: dict = {}           # stem (or the head itself) -> [heads]
        for g in mine:
            if g[3] != "drum":
                continue
            x, y, w = g[:3]
            stem = next((s for s in stems if x - 1 <= s[0] <= x + w + 1 and s[1] - sp / 2 <= y <= s[2] + sp / 2), None)
            chords.setdefault(stem or g, []).append(g)
        evs = []
        for stem, heads in chords.items():
            x, w = min(h[0] for h in heads), heads[0][2]
            up = stem is None or len(stem) == 5 or abs(stem[2] - heads[0][1]) < abs(stem[1] - heads[0][1])
            dur = heads[0][4]
            if dur is None and len(stem) == 3:
                dur = _stem_value(stem, stem[1] if up else stem[2], fills, mine, w, sp)
            # E4 = bottom line, one step per half space
            steps = [30 + round((bottom - h[1]) / (sp / 2)) for h in heads]
            ev = Event(x, "drum", dur, voice=1 if up else 2,
                       pos=tuple(dict.fromkeys(f"{STEPS[n % 7]}{n // 7}" for n in sorted(steps))))
            if dur is not None and any(g[3] == "dot" and h[0] + w <= g[0] <= h[0] + w + 2 * sp
                                       and abs(g[1] - h[1]) <= 0.6 * sp for h in heads for g in mine):
                ev.dur *= Fraction(3, 2)
            evs.append(ev)
        for x, y, w, kind, dur in mine:
            if kind == "rest" and abs(y - mid) < 4 * sp:
                rest = Event(x, "rest", dur, voice=2 if y > mid else 1)
                if any(g[3] == "dot" and x + w <= g[0] <= x + w + 2 * sp and abs(g[1] - y) <= sp for g in mine):
                    rest.dur *= Fraction(3, 2)
                evs.append(rest)
            elif kind in ("accent", "tenuto", "accent-staccato"):
                near = [e for e in evs if e.kind == "drum" and abs(e.x - x) < sp and (e.voice == 1) == (y < mid)]
                if near:
                    near[0].marks.extend(kind.split("-"))
        notes = sorted((e for e in evs if e.kind == "drum"), key=lambda e: e.x)
        for x0, x1, y0, y1 in curves:   # ties: a curve from one head to the next of its voice (above = 1)
            if not (top - 3 * sp <= y0 <= bottom + 3 * sp):
                continue
            v = 1 if y0 < mid else 2
            a = next((e for e in notes if e.voice == v and abs(e.x - x0) < 2 * sp), None)
            b = a and next((e for e in notes if e.voice == v and e.x > a.x), None)
            if b and abs(b.x - x1) < 2 * sp:
                a.tie_start, b.tie_stop = True, True
        for l, r in zip(edges, edges[1:]):
            bar = sorted((e for e in evs if l <= e.x < r), key=lambda e: (e.voice, e.x))
            if not any(e.kind == "drum" for e in bar) or any(e.dur is None for e in bar):
                continue
            if len({e.voice for e in bar if e.kind == "drum"}) == 1:      # one voice: rests and all
                for e in bar:
                    e.voice = 1
            lens = {v: sum(e.dur for e in bar if e.voice == v) for v in {e.voice for e in bar}}
            if len(set(lens.values())) != 1:
                continue
            out.append(SlashBar(page.number, l * sx, r * sx, top * sx, bottom * sx,
                                [Event(e.x * sx, e.kind, e.dur, e.tie_start, e.tie_stop, e.marks, e.voice, e.pos)
                                 for e in bar]))
    return out


HEADS = set("œÏúwÎ˙")             # EngraverFontSet note heads (black, half: Ï ú ˙, whole)
# "˘" / "ﬂ" (or "ß", else sfz: only centred on a head): accent + staccato above / below in one glyph
MARKS = {">": ["accent"], "^": ["strong-accent"], "˘": ["accent", "staccato"], "ﬂ": ["accent", "staccato"],
         "ß": ["accent", "staccato"], ".": ["staccato"], "-": ["tenuto"]}


def read_marks(pdf_page, page) -> list[SlashBar]:
    """Articulations of the notes of one vector page: per staff and bar one Event per onset (heads
    at the same x), its `marks` from the glyphs centred on it. A "." beside a head is an augmentation
    dot, a "-" on the staff side of a head outside the staff a ledger line; cue-size heads are skipped."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    spans = [sp for b in pdf_page.get_text("rawdict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]
             if sp["font"].startswith("EngraverFontSet")]
    full = max((sp["size"] for sp in spans), default=0)
    heads, marks = [], []
    for sp in spans:
        for ch in sp["chars"]:
            g = (ch["bbox"][0], ch["origin"][1], ch["bbox"][2] - ch["bbox"][0], ch["c"])
            if ch["c"] in HEADS and sp["size"] >= 0.8 * full:
                heads.append(g)
            elif ch["c"] in MARKS:
                marks.append(g)
    if not heads:
        return []
    hlines, vthin, _, _, curves = _drawings(pdf_page)
    staves = _staves(hlines)
    if not staves:
        return []
    def staff_of(y):
        return min(staves, key=lambda s: max(s[0] - y, y - s[4], 0))
    out = []
    for st in staves:
        top, bottom = st[0], st[4]
        sp = (bottom - top) / 4
        left = min(x0 for x0, _, y in hlines if abs(y - top) < 0.2)
        right = max(x1 for _, x1, y in hlines if abs(y - top) < 0.2)
        edges = [left] + _barlines(vthin, top, bottom, left, right) + [right]
        groups: list[list] = []         # heads of one onset (a chord; a second sits one head to the side)
        for h in sorted((h for h in heads if staff_of(h[1]) is st), key=lambda h: h[0]):
            if groups and h[0] - groups[-1][0][0] <= 1.1 * h[2]:
                groups[-1].append(h)
            else:
                groups.append([h])
        evs = [Event(g[0][0], "head", Fraction(0), heads=len(g)) for g in groups]
        for x0, x1, y0, y1 in curves:
            k = next((k for k, g in enumerate(groups) if g[0][0] - sp <= x0 <= g[0][0] + g[0][2] + 1.5 * sp), None)
            if k is not None and x1 - x0 > 2 * sp and staff_of((y0 + y1) / 2) is st:     # not a brace
                evs[k].curved = True
        for k, h in _ties(curves, groups, st, staff_of, right):
            evs[k].ties.append(sorted(groups[k], key=lambda g: g[1]).index(h))
        for x, y, w, c in marks:
            # the head right below / above: centred on it, or starting with it ("ß" also comes 2 heads wide)
            near = min((h for h in heads if min(abs(h[0] + h[2] / 2 - x - w / 2), abs(h[0] - x)) <= 0.4 * h[2]),
                       key=lambda h: abs(h[1] - y), default=None)
            k = next((k for k, g in enumerate(groups) if near in g), None)
            if k is None or not 0.6 * sp <= abs(near[1] - y) <= 4.5 * sp:
                continue
            if c == "-" and (near[1] < y < top - 0.2 * sp or bottom + 0.2 * sp < y < near[1]):
                continue        # a ledger line between the head and the staff
            evs[k].marks.extend(m for m in MARKS[c] if m not in evs[k].marks)
        for l, r in zip(edges, edges[1:]):
            bar = [e for e in evs if l <= e.x < r]
            if bar:
                out.append(SlashBar(page.number, l * sx, r * sx, top * sx, bottom * sx,
                                    [Event(e.x * sx, e.kind, e.dur, marks=e.marks, heads=e.heads, ties=e.ties,
                                           curved=e.curved)
                                     for e in bar]))
    return out


def _ties(curves, groups: list[list], st, staff_of, right: float):
    """(column, head) of the tie curves of one staff: a flat curve from a head to the head at the
    same height in the next column, or off the system end from the last column (#39)."""
    sp = (st[4] - st[0]) / 4
    for x0, x1, y0, y1 in curves:
        yc = (y0 + y1) / 2
        if y1 - y0 > 2 * sp or staff_of(yc) is not st:
            continue
        k = max((k for k, g in enumerate(groups) if g[0][0] + g[0][2] <= x0 + sp), default=None)
        if k is None or abs(groups[k][0][0] + groups[k][0][2] - x0) > 2 * sp:
            continue
        near = [h for h in groups[k] if abs(h[1] - yc) <= 1.5 * sp]
        if k + 1 < len(groups) and abs(groups[k + 1][0][0] - x1) <= 2 * sp:
            near = [h for h in near if any(abs(h[1] - g[1]) < 0.3 for g in groups[k + 1])]
        elif not (k == len(groups) - 1 and x1 >= right - 2 * sp):
            continue
        if near:
            yield k, min(near, key=lambda h: abs(h[1] - yc))


def read(pdf, pages: list, drums: bool = False, marks: bool = False) -> list[SlashBar]:
    """Slash bars (drum-kit bars) of the vector pages of `pdf` (pages[i] is PDF page i)."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return [b for i, p in enumerate(doc) if i < len(pages) and p.get_fonts()
                and classify_page(p, i + 1).kind == "vector"
                for b in (read_marks if marks else read_drum_page if drums else read_page)(p, pages[i])]


CENTRED = {"’"}

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
                if text.isdecimal() and span["chars"]:
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


def read_lines(pdf, pages: list, pattern, left: bool = False) -> list[tuple[int, float, float, str]]:
    """(page number, centre x (left: left x), top y, text) of every text-layer line of the vector
    pages that matches `pattern` as a whole, in page coordinates (small labels like "Play" that
    Audiveris misses)."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    out = []
    with FITZ_LOCK, fitz.open(pdf) as doc:
        for i, p in enumerate(doc):
            if i >= len(pages) or not p.get_fonts() or classify_page(p, i + 1).kind != "vector":
                continue
            sx = pages[i].width / p.rect.width if p.rect.width else 1.0
            for block in p.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(sp["text"] for sp in line["spans"]).strip()
                    if pattern.match(text):
                        x0, y0, x1, _ = line["bbox"]
                        out.append((pages[i].number, (x0 if left else (x0 + x1) / 2) * sx, y0 * sx, text))
    return out


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
        sp = (st[4] - st[0]) / 4
        # no bars: the gap inside a repeat barline ":||:" (< 1.5 spaces), the clef / time before a start
        # repeat and the courtesy signature after the last barline (< 6 spaces at a staff end; Ghost 5 drums)
        bars = [(a, b) for k, (a, b) in enumerate(zip(edges, edges[1:]))
                if b - a >= (6 if k in (0, len(edges) - 2) else 1.5) * sp]
        out.append((st[0] * sx, [(a * sx, b * sx) for a, b in bars]))
    return out


def read_all_systems(pdf, pages: list) -> dict[int, list]:
    """Page.number -> read_systems of the vector pages of `pdf`."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return {pages[i].number: read_systems(p, pages[i]) for i, p in enumerate(doc)
                if i < len(pages) and p.get_fonts() and classify_page(p, i + 1).kind == "vector"}


def read_lyric_marks(pdf, pages: list) -> dict[int, tuple[list, list]]:
    """U5: page number -> (lyric hyphens: (x centre, y centre) of every "-" text item, horizontal lines:
    (x0, x1, y)) of the vector pages, in page coordinates. Audiveris pairs syllables by guess ("found" +
    "by" read as "found-by"); the text layer has every printed hyphen and melisma line."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    out = {}
    with FITZ_LOCK, fitz.open(pdf) as doc:
        for i, p in enumerate(doc):
            if i >= len(pages) or not p.get_fonts() or classify_page(p, i + 1).kind != "vector":
                continue
            sx = pages[i].width / p.rect.width if p.rect.width else 1.0
            hyphens = [((sp["bbox"][0] + sp["bbox"][2]) / 2 * sx, (sp["bbox"][1] + sp["bbox"][3]) / 2 * sx)
                       for block in p.get_text("dict")["blocks"] for line in block.get("lines", [])
                       for sp in line["spans"] if sp["text"].strip() == "-"]
            lines = [(r.x0 * sx, r.x1 * sx, r.y0 * sx) for d in p.get_drawings()
                     if (r := d["rect"]).height < 1 and r.width > 0]
            out[pages[i].number] = (hyphens, lines)
    return out
