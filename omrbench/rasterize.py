from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


def pdf_pages(pdf: Path) -> int:
    with fitz.open(pdf) as doc:
        return doc.page_count


def rasterize(pdf: Path, out_dir: Path, dpi: int = 300, grayscale: bool = True) -> list[Path]:
    """Render every page to PNG (cached: re-uses existing files)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc, start=1):
            p = out_dir / f"page{i:02d}.png"
            if not p.exists():
                cs = fitz.csGRAY if grayscale else fitz.csRGB
                page.get_pixmap(dpi=dpi, colorspace=cs, alpha=False).save(p)
            paths.append(p)
    return paths
