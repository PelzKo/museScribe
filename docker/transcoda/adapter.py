"""Transcoda page adapter: adapter --out DIR [--device cpu|cuda] [--beams N] PAGE.png...

Loads the model once, writes DIR/<stem>.krn per page. A failed page is reported on stderr and skipped.
Preprocessing and generation follow the model card (btrkeks/transcoda-59M-zeroshot-v1).
"""
import argparse
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast

REPO = "btrkeks/transcoda-59M-zeroshot-v1"
REVISION = os.environ["TRANSCODA_REVISION"]
W, H = 1050, 1485


def preprocess(path: Path) -> torch.Tensor:
    img = Image.open(path).convert("RGB")
    img = img.resize((W, max(1, int(img.height * W / img.width))), Image.BILINEAR)
    arr = np.array(img)[:H]
    if arr.shape[0] < H:
        arr = np.concatenate([arr, np.full((H - arr.shape[0], W, 3), 255, dtype=arr.dtype)])
    t = torch.from_numpy(arr).permute(2, 0, 1).float() / 255.0
    return ((t - 0.5) / 0.5).unsqueeze(0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--beams", type=int, default=3)     # the paper's headline setting
    ap.add_argument("pages", type=Path, nargs="+")
    a = ap.parse_args()
    model = AutoModelForCausalLM.from_pretrained(REPO, revision=REVISION, trust_remote_code=True)
    model = model.to(a.device).eval()
    tok = PreTrainedTokenizerFast.from_pretrained(REPO, revision=REVISION)
    failed = 0
    for p in a.pages:
        t0 = time.perf_counter()
        try:
            with torch.no_grad():
                out = model.generate(pixel_values=preprocess(p).to(a.device),
                                     image_sizes=torch.tensor([[H, W]], device=a.device),
                                     max_length=2048, do_sample=False, num_beams=a.beams,
                                     repetition_penalty=1.1)
            (a.out / f"{p.stem}.krn").write_text(tok.decode(out[0], skip_special_tokens=True))
            print(f"{p.name}: ok {time.perf_counter() - t0:.1f}s", file=sys.stderr, flush=True)
        except Exception:
            failed += 1
            print(f"{p.name}: FAILED\n{traceback.format_exc()}", file=sys.stderr, flush=True)
    return 1 if failed == len(a.pages) else 0


if __name__ == "__main__":
    sys.exit(main())
