"""Create synthetic samples (engraved with Verovio) to smoke-test the harness.

Scores from the music21 corpus are rendered to a vector PDF; the source MusicXML
becomes the ground truth. Real benchmarking should use your own scans/photos.
"""
from __future__ import annotations

from pathlib import Path

import yaml

DEMOS = {
    "demo-lindenbaum": ("schubert/lindenbaum", {"type": "piano_reduction", "languages": ["deu"]}),
    "demo-bach-chorale": ("bach/bwv66.6", {"type": "choir", "languages": ["deu"]}),
    # first violin only -> single-staff part
    "demo-violin-part": ("mozart/k156/movement4#0", {"type": "part"}),
}


def _toolkit():
    import verovio

    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 2100, "pageHeight": 2970, "scale": 45,
                   "adjustPageHeight": False, "footer": "none", "header": "auto"})
    return tk


def page_count(musicxml_path: Path) -> int:
    tk = _toolkit()
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError(f"verovio could not load {musicxml_path}")
    return tk.getPageCount()


def render_pdf(musicxml_path: Path, pdf_path: Path) -> int:
    import cairosvg  # MuPDF's SVG support mis-renders Verovio output
    import pymupdf

    tk = _toolkit()
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError(f"verovio could not load {musicxml_path}")
    out = pymupdf.open()
    for i in range(1, tk.getPageCount() + 1):
        pdf_bytes = cairosvg.svg2pdf(bytestring=tk.renderToSVG(i).encode(), background_color="white")
        out.insert_pdf(pymupdf.open("pdf", pdf_bytes))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(pdf_path)
    return out.page_count


def make_demos(data_dir: Path, max_pages: int = 3) -> list[Path]:
    import music21

    made = []
    for sid, (work, meta) in DEMOS.items():
        d = data_dir / sid
        d.mkdir(parents=True, exist_ok=True)
        work, _, part_idx = work.partition("#")
        full = music21.converter.parse(music21.corpus.getWork(work))
        if part_idx:
            single = music21.stream.Score()
            single.append(full.parts[int(part_idx)])
            full = single
        gt = d / "gt.musicxml"
        full.write("musicxml", fp=gt)
        if page_count(gt) > max_pages:
            # keep the longest prefix that still fits on max_pages (binary search)
            lo, hi = 1, len(full.parts[0].getElementsByClass("Measure"))
            while lo < hi:
                mid = (lo + hi + 1) // 2
                full.measures(0, mid - 1, indicesNotNumbers=True).write("musicxml", fp=gt)
                if page_count(gt) <= max_pages:
                    lo = mid
                else:
                    hi = mid - 1
            full.measures(0, lo - 1, indicesNotNumbers=True).write("musicxml", fp=gt)
        pages = render_pdf(gt, d / "input.pdf")
        (d / "meta.yaml").write_text(yaml.safe_dump(
            {**meta, "source": f"music21 corpus {work}, rendered with Verovio ({pages} pages)"},
            sort_keys=False, allow_unicode=True), encoding="utf-8")
        made.append(d)
    return made
