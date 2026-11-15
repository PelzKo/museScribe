"""Build the dynamics templates of a show (D4) -> data/<show>/dynamics_templates.npz.

    python scripts/derive_dyn_templates.py <show> [--run h71]

Samples: every `.omr` dynamics box of grade >= 0.9 in the scanned books of the run's work dirs
(results/<show>/runs/<run>/pipeline/*/audiveris/out, page images in runs/<run>/_pages/). No truth is
used: `dynamics.build` keeps per token the boxes that look like the token's median image. Writes a
contact sheet next to the file (dynamics_templates.png) to look at.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from omrbench import config as config_mod  # noqa: E402
from omrbench.pipeline import dynamics, layout  # noqa: E402
from omrbench.transcribe import project_jobs  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("show")
    ap.add_argument("--run", default="h71")
    ap.add_argument("-c", "--config", default="bench.yaml")
    a = ap.parse_args()
    cfg = config_mod.load(Path(a.config))
    root, _, jobs, _ = project_jobs(cfg, a.show)
    samples = []
    for job in jobs:
        wd = root / "runs" / a.run / "pipeline" / job.sid
        imgs = sorted((root / "runs" / a.run / "_pages" / job.sid / "300dpi").glob("page*.png"))
        if not (wd / "audiveris" / "out").is_dir() or not imgs:
            continue
        for page in layout.load(wd / "audiveris" / "out"):
            marks = [(m, m.shape.split("_", 1)[1].lower()) for m in page.marks
                     if m.kind == "dynamics" and m.grade >= 0.9 and "_" in m.shape]
            marks = [(m, t) for m, t in marks if t in dynamics.TOKENS]
            if not marks or page.number > len(imgs):
                continue
            im = Image.open(imgs[page.number - 1]).convert("L")
            staves = [s for sy in page.systems for s in sy.all_staves]
            for m, tok in marks:
                st = min(staves, key=lambda s: abs((s.top + s.bottom) / 2 - m.cy), default=None)
                if st is None:
                    continue
                samples.append((dynamics.cut(im, (m.x - 2, m.y - 2, m.x + m.w + 2, m.y + m.h + 2), st.interline),
                                tok))
    print("samples:", dict(Counter(t for _, t in samples)))
    T = dynamics.build(samples)
    out = Path(cfg["data_dir"]) / a.show / dynamics.FILE
    np.savez_compressed(out, **T)
    print("templates:", {k: v.shape for k, v in T.items()}, "->", out)
    W = sum(t.shape[1] + 6 for t in T.values())
    H = max((t.shape[0] for t in T.values()), default=1)
    sheet = Image.new("L", (max(W, 1) * 3, H * 3), 255)
    x = 0
    for t in T.values():
        sheet.paste(Image.fromarray(((1 - t) * 255).astype(np.uint8)).resize((t.shape[1] * 3, t.shape[0] * 3)), (x * 3, 0))
        x += t.shape[1] + 6
    sheet.save(out.with_suffix(".png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
