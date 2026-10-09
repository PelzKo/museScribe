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
    # vocal scores (classify(vocal=True)); words then holds only the other text
    singers: list[tuple[Placed, str]] = field(default_factory=list)   # "DMITRY:" -> "Dmitry"
    spoken: list[tuple[Placed, str]] = field(default_factory=list)    # "GLEB: We hear you, ..."
    stage: list[Placed] = field(default_factory=list)                 # "(VLAD POPOV enters.)"


def running_headers(pages: list[Page]) -> set[str]:
    """Texts printed at the top or bottom of most pages ("A Rumor In St. Petersburg -
    pg. 4", "ANASTASIA"), as keys of _run_key. Audiveris gives them varying roles, so
    position and role alone miss some, and they end up as lyrics or words."""
    seen: dict[str, set[int]] = {}
    for page in pages:
        if not page.height:
            continue
        for ln in lines(page):
            if ln.bottom < 0.12 * page.height or ln.top > 0.92 * page.height:
                if re.search(r"[:;‘'’]", ln.text):
                    continue        # "DMITRY:" starts many pages, it is a singer label
                k = _run_key(ln.text)
                if len(k) >= 4:
                    seen.setdefault(k, set()).add(page.number)
    need = max(2, min(3, len(pages) // 2))
    return {k for k, ps in seen.items() if len(ps) >= need}


def _run_key(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


RUNNING_PAGE = re.compile(r"\bpg\.?\s*\d+\s*$|\bpage\s+\d+\s*$", re.I)


# ------------------------------------------------------------------- vocal scores

# "DMITRY:", "SOLO WOMAN:", "(2nd x:) WOMEN:", "ALL (NO DMITRY):", "BLACK MARKETEER #3:"; OCR
# often turns the colon into ";", "‘" or a few junk letters ("WOMENtss")
_LABEL = re.compile(r"^(?:\([^)]*\)\s*)?\(?([A-Z][A-Z'’.+&-]*(?:\s+(?:[A-Z][A-Z'’.+&-]*|#?\d+)){0,2})"
                    r"\)?\s*(\([^)]*\))?\s*([:;‘'’]|[a-z]{1,3}\b)?\s*(.*)$")
_NOT_SINGERS = {"PED", "SFZ", "FP", "MP", "MF", "PP", "FF", "SOP", "ALTO", "TACET", "TUTTI"}


def parse_label(text: str, bold: bool) -> tuple[str, str] | None:
    """(singer, rest of the line) of a line starting with a singer label, else None."""
    m = _LABEL.match(text.strip())
    if not m:
        return None
    name, colon, rest = m.group(1).strip(" .'’"), m.group(3), m.group(4).strip()
    letters = re.sub(r"[^A-Z]", "", name)
    if len(letters) < 3 or name.upper() != name or name in _NOT_SINGERS:
        return None
    if not colon and not (bold and not rest):
        return None             # caps words without colon: "ANASTASIA", "SFZ"
    return name, rest


def singer_name(label: str) -> str:
    """"SOLO WOMAN" -> "Solo Woman", "DMITRY+ALL" -> "Dmitry+All"."""
    return re.sub(r"[A-Za-z’']+", lambda m: m.group(0).capitalize(), label)


def _bold(ln: Line) -> bool:
    return any(a.font.startswith("B") for a in ln.atoms)


def _is_lyrics(ln: Line) -> bool:
    return all(a.role == "Lyrics" or a.kind in ("syllable", "hyphen") for a in ln.atoms)


def _prose(text: str) -> bool:
    """Dialogue: a sentence, not a direction ("(+1 SOP 8va)", "cresc.")."""
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        return False
    return len(re.findall(r"[^\W\d_]{2,}", t)) >= 3


def _rows(page_lines: list[Line]) -> list[Line]:
    """Lines of one printed row joined (dialogue has wide gaps, lines() splits it)."""
    rows: list[Line] = []
    for ln in sorted(page_lines, key=lambda l: (l.top, l.x)):
        row = next((r for r in rows if min(r.bottom, ln.bottom) - max(r.top, ln.top)
                    >= 0.5 * min(r.h, ln.h)), None)
        if row is None:
            rows.append(Line(ln.page, list(ln.atoms)))
        else:
            row.atoms.extend(ln.atoms)
    return rows


def vocal_blocks(page_lines: list[Line]) -> tuple[list[tuple[Line, str, list[Line]]],
                                                  list[tuple[Line, str, list[Line]]]]:
    """Singer labels and spoken dialogue of a vocal score page.

    Returns (labels, spoken): (anchor line, text, member lines). A label is a caps name
    ending in a colon ("DMITRY:"), possibly over two rows ("FIRST" / "WOMAN:"). It
    starts dialogue when prose follows on its row or right below it ("GLEB: (cont.)" /
    "We hear you, comrades, ..."); the text is "GLEB: (cont.) We hear you, ...".
    """
    lyric = [ln for ln in page_lines if _is_lyrics(ln) and not parse_label(ln.text, _bold(ln))]
    others = [ln for ln in page_lines if ln not in lyric]
    used: set[int] = set()
    labels, spoken = [], []
    for ln in sorted(others, key=lambda l: (l.top, l.x)):
        if id(ln) in used:
            continue
        lab = parse_label(ln.text, _bold(ln))
        members = [ln]
        if lab is None or not lab[1] and not re.search(r"[:;‘'’]\s*$", ln.text) and _bold(ln):
            # "FIRST" over "WOMAN:", "ALL" over "(NO DMITRY):"
            below = next((o for o in others if id(o) not in used and o is not ln
                          and 0 <= o.top - ln.bottom <= 0.8 * ln.h
                          and abs(o.x - ln.x) <= 3 * ln.h), None)
            if below is not None and re.fullmatch(r"[A-Z][A-Z'’.+&\s-]*", ln.text.strip()):
                two = parse_label(f"{ln.text} {below.text}", _bold(ln) or _bold(below))
                if two:
                    lab, members = two, [ln, below]
        if lab is None:
            continue
        name, rest = lab
        # same row to the right ("GLEB:" ... "to raise spirits)"), then rows below
        row = [o for o in others if o not in members and id(o) not in used
               and min(o.bottom, ln.bottom) - max(o.top, ln.top) >= 0.5 * min(o.h, ln.h)
               and 0 <= o.x - ln.right <= 8 * ln.h and not parse_label(o.text, _bold(o))]
        text_parts = [rest] + [o.text for o in sorted(row, key=lambda o: o.x)]
        block, last = [], members[-1]
        while True:
            nxt = [o for o in others if o not in members and o not in block and id(o) not in used
                   and 0 <= o.top - last.bottom <= (0.8 if block else 1.2) * last.h
                   and o.x >= ln.x - 3 * ln.h
                   and not parse_label(o.text, _bold(o))]
            if not nxt:
                break
            row_lines = _rows(nxt)[0]
            members_row = [o for o in nxt if min(o.bottom, row_lines.bottom) - max(o.top, row_lines.top)
                           >= 0.5 * min(o.h, row_lines.h)]
            if not (_prose(row_lines.text) or block and is_words(row_lines.text)):
                break
            block += members_row
            text_parts.append(Line(ln.page, [a for o in members_row for a in o.atoms]).text)
            last = max(members_row, key=lambda o: o.bottom)
        full = " ".join(t for t in text_parts if t).strip()
        if block or _prose(full):
            members = members + row + block
            spoken.append((members[0], f"{name}: {full}".strip(), members))
        else:
            labels.append((members[0], name, members))
        for o in members:
            used.add(id(o))
    return labels, spoken


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


def _staff_below(systems: list[System], y: float) -> tuple[System, Staff] | None:
    """The staff right below height y (labels and dialogue sit above their staff)."""
    cands = [(st.top, sy, st) for sy in systems for st in sy.all_staves if st.top >= y]
    if not cands:
        return None
    _, sy, st = min(cands, key=lambda c: c[0])
    return sy, st


def classify(page: Page, vocal: bool = False, running: set[str] | None = None) -> PageText:
    """vocal: a vocal score (piano reduction): singer labels and dialogue are picked out,
    lyric lines are left to the notes (Audiveris attaches them), stage directions above
    the music go with the voices."""
    res = PageText()
    systems = [s for s in page.systems if s.staves]
    if not systems:
        res.credits = [ln for ln in lines(page) if ln.text]
        return res
    page_lines = lines(page)
    is_running = lambda ln: _run_key(ln.text) in (running or ()) or bool(RUNNING_PAGE.search(ln.text))
    for ln in page_lines:
        if is_running(ln) and ln.text:
            res.credits.append(ln)
    page_lines = [ln for ln in page_lines if not is_running(ln)]
    taken: set[int] = set()
    if vocal:
        labels, spoken = vocal_blocks(page_lines)
        for found, out in ((labels, res.singers), (spoken, res.spoken)):
            for anchor, value, members in found:
                taken.update(id(m) for m in members)
                sy, st = _staff_below(systems, anchor.top) or (systems[-1], systems[-1].all_staves[-1])
                if sy.skip:
                    continue
                if st not in sy.staves:          # dropped staff: onto the top kept one
                    st = sy.staves[0]
                out.append((Placed(anchor, sy, st, True), value))
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

    for ln in page_lines:
        t = ln.text
        if not t or id(ln) in taken:
            continue
        # a number well below the last staff is the page number, not a bar number
        footer = ln.top > last_bottom + (4 if NUMBER.match(t) else 8) * il
        if is_header(ln, first_top) or footer:
            if is_words(t) or NUMBER.match(t):
                res.credits.append(ln)
            continue
        all_staves = [st for s in systems for st in s.all_staves]
        staff, above = nearest_staff(all_staves, ln.cy)
        if above:
            # printed like a bar number, below the staff it belongs to: often nearer to the
            # next system than the 1.5 rule allows
            up = [s for s in all_staves if s.bottom < ln.cy]
            if up:
                st_up = max(up, key=lambda s: s.bottom)
                gap_up, gap_down = ln.top - st_up.bottom, staff.top - ln.bottom
                if to_bar(t) is not None or LETTERED.match(t.replace(" ", "")):
                    if gap_up <= 8 * st_up.interline:
                        staff, above = st_up, False
                elif NUMBER.match(t) and ln.h < 1.4 * st_up.interline and gap_up <= gap_down:
                    # a plain bar number (small print) nearer the staff above; a multi-rest
                    # count over the staff below is twice as tall and sits right on it
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
            # "184-192" closing a text line ("Poco agitato J = 184-192") is a tempo range;
            # OCR sometimes returns it as a line of its own as well
            in_words = any(o is not ln and re.search(r"[^\W\d_]{3,}", o.text)
                           and o.top < ln.bottom and ln.top < o.bottom
                           and o.x < ln.right + il and ln.x < o.right + il for o in page_lines)
            if int(m.group(1)) < int(m.group(2)) and not in_words:
                res.ranges.append((pl, int(m.group(1)), int(m.group(2))))
        elif lm := LETTERED.match(t.replace(" ", "")):
            res.lettered.append((pl, (int(lm.group(1)), lm.group(2))))
        elif NUMBER.match(t):
            if above and ln.x < staff.left + 4 * staff.interline:
                res.rehearsals.append((pl, t))       # boxed number at the system start
            else:
                res.numbers.append((pl, int(t)))
        elif vocal and _is_lyrics(ln):
            continue            # sung text: Audiveris attaches it to the notes
        elif is_words(t) and (any(a.kind == "word" for a in ln.atoms)
                              or re.search(r"[^\W\d_]{3,}", t)):
            # lines made only of lyric fragments need a real word ('"lf', 'P' are noise)
            if vocal and len(re.findall(r"[^\W\d_]{2,}", t)) >= 6 and re.search(r"[.?!,]", t) \
                    and not t.startswith("("):
                res.spoken.append((pl, t))      # dialogue whose speaker label OCR lost
            elif vocal and (t.startswith("(") and len(t.split()) >= 2 or t.endswith(")") and "(" not in t) \
                    and (staff in sy.vocal_staves or above and staff is sy.staves[0]):
                # "(VLAD POPOV enters.)"; a row ending in ")" continues one
                res.stage.append(pl)
            else:
                res.words.append(pl)
    return res


def clean_words(t: str) -> str:
    """Drop a metronome remnant ("Maestoso = 92" -> "Maestoso"); tempo comes from Audiveris."""
    return re.sub(r"\s*[=♩]\s*\d{2,3}\s*$", "", t).strip()
