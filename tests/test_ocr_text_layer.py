"""Vector pages: bar numbers come from the PDF text layer (no Tesseract), only inside the staff strips."""
import pymupdf as fitz

from omrbench.pipeline import ocr
from omrbench.pipeline.layout import Page, Staff, System


def test_vector_page_bar_number_from_text_layer(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    for i in range(60):   # enough drawn paths to classify as vector (with real text)
        page.draw_line((50, 100 + i * 8), (550, 100 + i * 8))
    page.insert_text((60, 295), "12", fontsize=12)       # just above the staff: a bar number
    page.insert_text((60, 700), "34", fontsize=12)       # far from any staff: ignored
    pdf = tmp_path / "v.pdf"
    doc.save(pdf)

    # Audiveris page at twice the PDF scale; staff at PDF y 300..340
    lp = Page(number=1, width=1200, height=1600,
              systems=[System(page=1, id=1, staves=[Staff(1, 0, 600, 680, 100, 1100)], stacks=[])])
    words = ocr.read_pages([lp], [], None, tmp_path / "ocr", pdf=pdf)
    assert [w["text"] for w in words[0]] == ["12"]
    assert ocr.supplement(lp, words[0]) == 1
    assert lp.texts[-1].value == "12" and lp.texts[-1].kind == "number"
