"""Classify PDF pages as scan, scan+ocr, vector, vector-outlined or text.

scan          page is (almost) one embedded image, no text layer
scan+ocr      same, with an invisible text layer on top (OCR'd scan)
vector        engraved with a music font or SMuFL glyphs, or drawn paths with real text
vector-outlined  many drawn paths and no text at all (glyphs converted to outlines)
text          anything else: cover, lyrics, prose pages with no notation

A document's kind is the most common kind among its non-text pages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz

from .rasterize import FITZ_LOCK

SCAN_COVER = 0.9      # image covers this share of the page -> scan
DRAWINGS_MIN = 50     # drawn paths that make a page look engraved
MUSIC_FONT_HINTS = ("bravura", "leland", "emmentaler", "mscore", "opus", "maestro", "petrucci",
                    "gonville", "sebelius", "engraver", "finale", "musica", "jazz", "smufl")
SMUFL_RANGE = (0xE000, 0xF8FF)   # Unicode private use area, where SMuFL glyphs live


@dataclass
class PageKind:
    page: int                       # 1-based
    kind: str
    image_cover: float = 0.0
    drawings: int = 0
    words: int = 0
    music_fonts: list[str] = field(default_factory=list)


def _music_fonts(page) -> list[str]:
    return sorted({f[3] for f in page.get_fonts() if any(h in f[3].lower() for h in MUSIC_FONT_HINTS)})


def _has_smufl(page) -> bool:
    lo, hi = SMUFL_RANGE
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if any(lo <= ord(c["c"]) <= hi for c in span.get("chars", [])):
                    return True
    return False


def classify_page(page, number: int = 1) -> PageKind:
    area = page.rect.width * page.rect.height or 1
    cover = sum(r.width * r.height for img in page.get_images(full=True)
                for r in page.get_image_rects(img[0])) / area
    words = len(page.get_text("words"))
    if cover >= SCAN_COVER:   # scans are the common case: skip the costly path/font checks
        return PageKind(number, "scan+ocr" if words else "scan", min(cover, 1.0), 0, words, [])
    drawings = len(page.get_drawings())
    fonts = _music_fonts(page)
    pk = PageKind(number, "text", min(cover, 1.0), drawings, words, fonts)
    if fonts or _has_smufl(page):
        pk.kind = "vector"
    elif drawings >= DRAWINGS_MIN:
        pk.kind = "vector" if words else "vector-outlined"
    return pk


def page_kinds(pdf: Path) -> list[PageKind]:
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return [classify_page(p, i) for i, p in enumerate(doc, start=1)]


def doc_kind(pdf: Path) -> str:
    """Most common kind among the non-text pages ("text" if the document has no notation)."""
    counts: dict[str, int] = {}
    for pk in page_kinds(pdf):
        if pk.kind != "text":
            counts[pk.kind] = counts.get(pk.kind, 0) + 1
    return max(counts, key=counts.get) if counts else "text"


def is_scan(pdf: Path) -> bool:
    """True if the document's notation is mostly scanned pages (scan or scan+ocr)."""
    return doc_kind(pdf).startswith("scan")
