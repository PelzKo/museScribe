from __future__ import annotations

import threading
from pathlib import Path

import pymupdf as fitz

# PyMuPDF is not thread-safe; samples run in threads (transcribe --jobs)
FITZ_LOCK = threading.RLock()


def pdf_pages(pdf: Path) -> int:
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return doc.page_count


def rasterize(pdf: Path, out_dir: Path, dpi: int = 300, grayscale: bool = True) -> list[Path]:
    """Render every page to PNG (cached: re-uses existing files)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with FITZ_LOCK, fitz.open(pdf) as doc:
        for i, page in enumerate(doc, start=1):
            p = out_dir / f"page{i:02d}.png"
            if not p.exists():
                cs = fitz.csGRAY if grayscale else fitz.csRGB
                page.get_pixmap(dpi=dpi, colorspace=cs, alpha=False).save(p)
            paths.append(p)
    return paths


def is_scan(pdf: Path) -> bool:
    """True if every page is essentially one embedded image (a scan), not vector engraving."""
    with FITZ_LOCK, fitz.open(pdf) as doc:
        for page in doc:
            area = page.rect.width * page.rect.height or 1
            covered = 0.0
            for img in page.get_images(full=True):
                for r in page.get_image_rects(img[0]):
                    covered += r.width * r.height
            if covered < 0.5 * area:
                return False
    return True
