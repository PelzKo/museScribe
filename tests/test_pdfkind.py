"""pdfkind on synthetic PDFs: engraved vector page, the same page rasterised, cover-style text page."""
from pathlib import Path

import pymupdf as fitz
import pytest

from omrbench import pdfkind


def _staff_page(doc: fitz.Document) -> fitz.Page:
    """Vector page: 60 short paths (stems, staff lines) and no text, like outlined engraving."""
    page = doc.new_page(width=600, height=800)
    for i in range(60):   # separate paths: one shape would count as a single drawing
        y = 100 + i * 8
        page.draw_line((50, y), (550, y))
    return page


@pytest.fixture
def vector_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    _staff_page(doc)
    p = tmp_path / "vector.pdf"
    doc.save(p)
    return p


@pytest.fixture
def scan_pdf(tmp_path: Path, vector_pdf: Path) -> Path:
    """The vector page rasterised, then embedded as a full-page image (a scan)."""
    pix = fitz.open(vector_pdf)[0].get_pixmap(dpi=100)
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_image(page.rect, pixmap=pix)
    p = tmp_path / "scan.pdf"
    doc.save(p)
    return p


@pytest.fixture
def scan_ocr_pdf(tmp_path: Path, scan_pdf: Path) -> Path:
    """Scan plus an invisible text layer (render mode 3), as OCR tools write it."""
    doc = fitz.open(scan_pdf)
    doc[0].insert_text((50, 50), "Violin I", render_mode=3, fontname="helv", fontsize=10)
    p = tmp_path / "scan_ocr.pdf"
    doc.save(p)
    return p


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Cover: a few words of prose", fontsize=14)
    p = tmp_path / "text.pdf"
    doc.save(p)
    return p


def test_vector_outlined_page(vector_pdf):
    assert pdfkind.page_kinds(vector_pdf)[0].kind == "vector-outlined"
    assert pdfkind.doc_kind(vector_pdf) == "vector-outlined"
    assert not pdfkind.is_scan(vector_pdf)


def test_scan_page(scan_pdf):
    pk = pdfkind.page_kinds(scan_pdf)[0]
    assert pk.kind == "scan" and pk.image_cover >= pdfkind.SCAN_COVER
    assert pdfkind.is_scan(scan_pdf)


def test_scan_with_text_layer_is_scan_ocr(scan_ocr_pdf):
    assert pdfkind.page_kinds(scan_ocr_pdf)[0].kind == "scan+ocr"
    assert pdfkind.is_scan(scan_ocr_pdf)


def test_text_page_is_text(text_pdf):
    assert pdfkind.page_kinds(text_pdf)[0].kind == "text"
    assert pdfkind.doc_kind(text_pdf) == "text"   # no notation at all
    assert not pdfkind.is_scan(text_pdf)
