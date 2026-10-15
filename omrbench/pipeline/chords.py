"""Chord symbols from the text layer of born-digital pages -> <harmony> on the output bars.

Audiveris finds almost none of them (Ghost 20 Guitar: 2 of 237) and OCRs the rest into junk words
("Bl? F"). In the PDF they are plain text: a Times root letter, the flat / sharp as a music-font
glyph, a suffix ("m7", "Maj7") and "/bass". A run of text above a staff counts only if it parses as
chord symbols from start to end ("Fill", "scratch", bar numbers are left alone).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

# printed suffix -> MusicXML kind (+ the kind@text MuseScore writes)
KINDS = {"": "major", "m": "minor", "-": "minor", "7": "dominant", "9": "dominant-ninth",
         "Maj7": "major-seventh", "maj7": "major-seventh", "M7": "major-seventh", "m7": "minor-seventh",
         "-7": "minor-seventh", "5": "power", "4": "suspended-fourth", "sus4": "suspended-fourth",
         "sus": "suspended-fourth", "sus2": "suspended-second", "6": "major-sixth", "m6": "minor-sixth",
         "dim": "diminished", "o": "diminished", "aug": "augmented", "+": "augmented",
         "dim7": "diminished-seventh", "m7b5": "half-diminished", "11": "dominant-11th",
         "13": "dominant-13th", "add9": "major", "2": "major"}
_SUFFIX = "|".join(sorted((re.escape(k) for k in KINDS if k), key=len, reverse=True))
CHORD = re.compile(rf"([A-G])([b#]?)({_SUFFIX})?(?:/([A-G])([b#]?))?")
ALTER = {"": 0, "b": -1, "#": 1}


@dataclass
class Symbol:
    page: int            # Page.number
    x: float             # left edge, page (image) coordinates
    y: float             # top
    w: float
    h: float
    root: str
    alter: int
    kind: str
    text: str            # printed suffix
    bass: str = ""
    bass_alter: int = 0


def parse(run: str) -> list[tuple[int, re.Match]] | None:
    """(start index, match) of every chord in `run` (spaces allowed between them), or None when the
    run is not chord symbols from start to end."""
    out, i = [], 0
    while i < len(run):
        if run[i] == " ":
            i += 1
            continue
        m = CHORD.match(run, i)
        if not m or m.end() == i:
            return None
        out.append((i, m))
        i = m.end()
    return out or None


def _chars(span) -> list[tuple[str, tuple]]:
    """(char, bbox) of a span; a music-font flat / sharp glyph counts as b / #."""
    music = not span["font"].startswith("Times")
    out = []
    for ch in span["chars"]:
        c = ch["c"]
        if music:
            c = {"b": "b", "#": "#", "♭": "b", "♯": "#"}.get(c)
            if c is None:
                return []
        out.append((c, ch["bbox"]))
    return out


def read_page(pdf_page, page) -> list[Symbol]:
    """Chord symbols of one vector PDF page, in the coordinates of `page` (layout.Page)."""
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    out = []
    for block in pdf_page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            if not spans or any("Bold" in s["font"] for s in spans):
                continue       # rehearsal letters are bold
            chars = [c for s in spans for c in _chars(s)]
            if not chars or not any(s["font"].startswith("Times") for s in spans):
                continue
            run = "".join(c for c, _ in chars)
            found = parse(run)
            if not found:
                continue
            for start, m in found:
                boxes = [b for _, b in chars[start:m.end()]]
                x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
                x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
                root, acc, suffix, bass, bacc = m.groups()
                out.append(Symbol(page.number, x0 * sx, y0 * sx, (x1 - x0) * sx, (y1 - y0) * sx,
                                  root, ALTER[acc], KINDS[suffix or ""], suffix or "",
                                  bass or "", ALTER[bacc or ""]))
    return out


def read(pdf: Path, pages: list) -> list[Symbol]:
    """Chord symbols of the vector pages of `pdf` (pages[i] is PDF page i)."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return [s for i, p in enumerate(doc) if i < len(pages) and p.get_fonts()
                and classify_page(p, i + 1).kind == "vector" for s in read_page(p, pages[i])]


def harmony(s: Symbol) -> etree._Element:
    h = etree.Element("harmony")
    r = etree.SubElement(h, "root")
    etree.SubElement(r, "root-step").text = s.root
    if s.alter:
        etree.SubElement(r, "root-alter").text = str(s.alter)
    k = etree.SubElement(h, "kind")
    k.text = s.kind
    if s.text:
        k.set("text", s.text)
    if s.bass:
        b = etree.SubElement(h, "bass")
        etree.SubElement(b, "bass-step").text = s.bass
        if s.bass_alter:
            etree.SubElement(b, "bass-alter").text = str(s.bass_alter)
    return h


def overlaps(s: Symbol, x: float, y: float, w: float, h: float) -> bool:
    return x < s.x + s.w and s.x < x + w and y < s.y + s.h and s.y < y + h
