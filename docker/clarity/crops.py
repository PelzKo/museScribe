"""Clarity-OMR stage B (staff reader) on pipeline crops: `clarity-crops --staves N img...` writes
`<img>.musicxml` per crop, one part with N staves (pipeline/recognizer.py). Stage A (YOLO staff
detection) is skipped: the pipeline's Audiveris layout already cut the crops. A 2-staff crop is
split at the emptiest row between its staves; Clarity reads each staff on its own."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "/opt/clarity")
from src.cli import run_assemble  # noqa: E402
from src.eval.evaluate_stage_b_checkpoint import _run_stage_b_inference_with_progress  # noqa: E402
from src.model_assets import ensure_default_stage_b_checkpoint  # noqa: E402
from src.pipeline.export_musicxml import (  # noqa: E402
    _write_musicxml_safe, assembled_score_to_music21, load_assembled_score)


def split(img: Path, n: int, out_dir: Path) -> list[Path]:
    """n staff images: cut at the row with the least ink in the middle half between staves."""
    if n == 1:
        return [img]
    im = Image.open(img).convert("L")
    ink = (255 - np.asarray(im, dtype=np.float32)).sum(axis=1)
    h = im.height
    cuts = []
    for i in range(1, n):
        lo, hi = int(h * (i - 0.5) / n), int(h * (i + 0.5) / n)
        cuts.append(lo + int(np.argmin(ink[lo:hi])))
    out = []
    for j, (top, bottom) in enumerate(zip([0, *cuts], [*cuts, h])):
        p = out_dir / f"{img.stem}__staff{j:02d}.png"
        im.crop((0, top, im.width, bottom)).save(p)
        out.append(p)
    return out


def write(assembly: Path, n: int, out: Path) -> None:
    from music21 import layout, stream
    score = assembled_score_to_music21(load_assembled_score(assembly))
    if n > 1:
        # one part with n staves (music21 joins PartStaffs in a StaffGroup into one <part>)
        parts = list(score.parts)
        joined = stream.Score()
        staffs = []
        for p in parts:
            ps = stream.PartStaff(id=p.id)
            for el in p.elements:
                ps.append(el)
            staffs.append(ps)
            joined.insert(0, ps)
        joined.insert(0, layout.StaffGroup(staffs, symbol="brace"))
        score = joined
        # Clarity names voices "voice_1"; music21 needs numbers to join staves into one part
        for m in score.recurse().getElementsByClass(stream.Measure):
            for i, v in enumerate(m.voices, 1):
                v.id = i
    _write_musicxml_safe(score, out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staves", type=int, default=1)
    ap.add_argument("--device", default=None)
    ap.add_argument("--beam-width", type=int, default=5)
    ap.add_argument("images", nargs="+", type=Path)
    a = ap.parse_args()
    root = Path("/opt/clarity")
    rows = []
    for i, img in enumerate(a.images):
        work = img.parent / f"{img.stem}.clarity"
        work.mkdir(exist_ok=True)
        for j, p in enumerate(split(img, a.staves, work)):
            w, h = Image.open(p).size
            rows.append({"sample_id": f"crop_{i:04d}:{p.stem}", "crop_path": str(p.resolve()),
                         "system_index": 0, "staff_index": j, "page_index": i,
                         "bbox": {"x_min": 0.0, "y_min": float(j * h), "x_max": float(w), "y_max": float((j + 1) * h)}})
    work = a.images[0].parent
    manifest, preds = work / "clarity_crops.jsonl", work / "clarity_preds.jsonl"
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows))
    _run_stage_b_inference_with_progress(
        project_root=root, crops_manifest=manifest, output_predictions=preds,
        checkpoint=ensure_default_stage_b_checkpoint(root), beam_width=a.beam_width,
        max_decode_steps=512, image_height=250, image_max_width=2500, device_name=a.device,
        progress_every_seconds=30.0, quiet=True)
    by_crop: dict[int, list[str]] = {}
    for line in preds.read_text().splitlines():
        by_crop.setdefault(json.loads(line)["page_index"], []).append(line)
    for i, img in enumerate(a.images):
        if i not in by_crop:
            print(f"{img.name}: no prediction", file=sys.stderr)
            continue
        cw = img.parent / f"{img.stem}.clarity"
        p, asm = cw / "preds.jsonl", cw / "assembled.json"
        p.write_text("\n".join(by_crop[i]) + "\n")
        try:
            run_assemble(argparse.Namespace(staff_predictions=p, output_assembly=asm))
            write(asm, a.staves, img.with_suffix(".musicxml"))
        except Exception as exc:  # one bad crop must not lose the batch
            print(f"{img.name}: {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
