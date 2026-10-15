"""OLA layout boxes: `ola --out boxes.json [--device cpu|cuda] img...` writes
{image path: [{"cls": name, "conf": c, "box": [x1, y1, x2, y2]} ...]} in image pixels."""
import argparse
import json
from pathlib import Path

from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--device", default="cpu")
ap.add_argument("--conf", type=float, default=0.25)
ap.add_argument("--imgsz", type=int, default=640)   # the training size
ap.add_argument("images", nargs="+")
a = ap.parse_args()
model = YOLO("/opt/ola/model.pt")
out = {}
for img in a.images:   # one at a time: pages are large, batching gains little
    r = model.predict(img, device=0 if a.device == "cuda" else "cpu", conf=a.conf, imgsz=a.imgsz,
                      verbose=False, max_det=1000)[0]
    out[img] = [{"cls": r.names[int(c)], "conf": round(float(p), 3), "box": [round(float(v), 1) for v in b]}
                for b, c, p in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
a.out.write_text(json.dumps(out, indent=0))
