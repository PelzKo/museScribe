"""SMT full-page adapter: adapter --out DIR [--device cpu|cuda] PAGE.png...

Loads $SMT_MODEL (revision $SMT_REVISION) once, writes DIR/<stem>.krn (bekern body, no header) per page.
The page is scaled to the model's training width (config maxw), height capped at maxh, as in the repo's
full-page data preparation. A failed page is reported on stderr and skipped.
"""
import argparse
import os
import sys
import time
import traceback
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from smt_model import SMTModelForCausalLM


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("pages", type=Path, nargs="+")
    a = ap.parse_args()
    model = SMTModelForCausalLM.from_pretrained(os.environ["SMT_MODEL"], revision=os.environ["SMT_REVISION"])
    model = model.to(a.device).eval()
    maxw, maxh = model.config.maxw, model.config.maxh
    failed = 0
    for p in a.pages:
        t0 = time.perf_counter()
        try:
            img = Image.open(p).convert("L")
            img = img.resize((maxw, min(maxh, round(img.height * maxw / img.width))), Image.BILINEAR)
            x = transforms.ToTensor()(img).unsqueeze(0).to(a.device)
            with torch.no_grad():
                pred, _ = model.predict(x, convert_to_str=True)
            krn = "".join(pred).replace("<b>", "\n").replace("<s>", " ").replace("<t>", "\t")
            (a.out / f"{p.stem}.krn").write_text(krn)
            print(f"{p.name}: ok {time.perf_counter() - t0:.1f}s", file=sys.stderr, flush=True)
        except Exception:
            failed += 1
            print(f"{p.name}: FAILED\n{traceback.format_exc()}", file=sys.stderr, flush=True)
    return 1 if failed == len(a.pages) else 0


if __name__ == "__main__":
    sys.exit(main())
