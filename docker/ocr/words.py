"""Word boxes from an OCR engine: `ocr-words --engine easyocr|doctr|paddle --out OUT.json img...`
writes {image file name: [{"text", "conf" (0-100), "x", "y", "w", "h"} in image pixels]}.
The images are the pipeline's masked strip pages (pipeline/ocr.py): text bands around the staves."""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--engine", required=True, choices=["easyocr", "doctr", "paddle"])
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--device", default="cpu")
ap.add_argument("images", nargs="+", type=Path)
a = ap.parse_args()
gpu = a.device == "cuda"


def box(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return {"x": float(min(xs)), "y": float(min(ys)), "w": float(max(xs) - min(xs)), "h": float(max(ys) - min(ys))}


out = {}
if a.engine == "easyocr":
    import easyocr
    reader = easyocr.Reader(["en"], gpu=gpu, model_storage_directory="/opt/ocr/easyocr", download_enabled=False)
    for img in a.images:
        out[img.name] = [{"text": t, "conf": round(100 * float(c), 1), **box(b)}
                         for b, t, c in reader.readtext(str(img))]
elif a.engine == "doctr":
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    model = ocr_predictor(pretrained=True)
    if gpu:
        model = model.cuda()
    for img in a.images:
        page = model(DocumentFile.from_images([str(img)])).pages[0]
        h, w = page.dimensions
        words = []
        for block in page.blocks:
            for line in block.lines:
                for wd in line.words:
                    (x0, y0), (x1, y1) = wd.geometry
                    words.append({"text": wd.value, "conf": round(100 * float(wd.confidence), 1),
                                  "x": x0 * w, "y": y0 * h, "w": (x1 - x0) * w, "h": (y1 - y0) * h})
        out[img.name] = words
else:
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_textline_orientation=False, device="gpu" if gpu else "cpu")
    for img in a.images:
        r = ocr.predict(str(img))[0]
        out[img.name] = [{"text": t, "conf": round(100 * float(c), 1), **box(p.tolist())}
                         for t, c, p in zip(r["rec_texts"], r["rec_scores"], r["rec_polys"])]
a.out.write_text(json.dumps(out))
