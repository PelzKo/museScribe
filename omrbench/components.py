"""Component benchmarks (PLAN_full.md Phase 6). `omrbench components layout`: layout providers on
the pages of a finished pipeline run, compared with Audiveris (the pipeline's layout) and the
ground-truth bar count.

Provider `ola` (v-dvorak/omr-layout-analysis v2.0, image `omrbench/ola:2.0`): YOLO boxes for
systems, staves and system measures. Its boxes are cached next to each work dir
(`<workdir>/ola/boxes.json`), so the pipeline can reuse them (`measures: ola`).

Per work dir (= one PDF / sample): systems, staves per system and measures, for Audiveris and
OLA; their per-system agreement; measures vs the truth bar count. Printed measures are not bars:
a multi-measure rest is one printed measure, so parts with multirests read low for every provider.
Runtime and memory of each OLA call come from the container's monitor (stats.json).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PIL import Image

from . import containers, log as logmod
from .monitor import RunStats
from .pipeline import layout

LOG = logmod.get("components")


def ola_boxes(run_root: Path, wd: Path, images: list[Path], device: str) -> tuple[dict, RunStats | None]:
    """{page image file name: boxes} for the pages of one work dir; cached in <wd>/ola/boxes.json."""
    out = wd / "ola" / "boxes.json"

    def by_name(d):
        return {Path(k).name: v for k, v in d.items()}
    if out.exists():
        return by_name(json.loads(out.read_text())), None
    out.parent.mkdir(exist_ok=True)
    cmd = ["ola", "--out", str(out), "--device", device, *[str(i) for i in images]]
    stats_name = f"ola-stats-{wd.name}.json".replace(" ", "_")
    st = containers.run_in_container(
        containers.IMAGES["ola"][0], cmd, workdir=run_root, log_path=wd / "ola" / "ola.log",
        gpu=device == "cuda", env={} if device == "cuda" else {"CUDA_VISIBLE_DEVICES": ""},
        stats_name=stats_name)
    (run_root / stats_name).unlink(missing_ok=True)
    if not out.exists():
        raise RuntimeError(f"ola wrote no boxes (exit {st.exit_code}); see {wd / 'ola' / 'ola.log'}")
    return by_name(json.loads(out.read_text())), st


def _inside(box, top: float, bottom: float) -> bool:
    cy = (box[1] + box[3]) / 2
    return top <= cy <= bottom


def ola_systems(boxes: list[dict]) -> list[dict]:
    """OLA systems top to bottom: {"box", "staves", "measures"} (counts of the boxes inside)."""
    systems = sorted((b["box"] for b in boxes if b["cls"] == "systems"), key=lambda b: b[1])
    return [{"box": s,
             "staves": sum(1 for b in boxes if b["cls"] == "staves" and _inside(b["box"], s[1], s[3])),
             "measures": sum(1 for b in boxes if b["cls"] == "system_measures" and _inside(b["box"], s[1], s[3]))}
            for s in systems]


def compare_page(page: layout.Page, img: Path, boxes: list[dict]) -> dict:
    """Audiveris vs OLA systems of one page, matched by vertical overlap."""
    with Image.open(img) as im:
        sy_ = im.height / page.height if page.height else 1.0
    ola = ola_systems(boxes)
    aud = [{"top": min(s.top for s in sy.staves) * sy_, "bottom": max(s.bottom for s in sy.staves) * sy_,
            "staves": len(sy.staves), "measures": len(sy.stacks)} for sy in page.systems]
    pairs = []
    for a in aud:
        best = max(ola, key=lambda o: min(a["bottom"], o["box"][3]) - max(a["top"], o["box"][1]), default=None)
        if best is not None and min(a["bottom"], best["box"][3]) > max(a["top"], best["box"][1]):
            pairs.append((a, best))
    return {"aud_systems": len(aud), "ola_systems": len(ola),
            "aud_measures": sum(a["measures"] for a in aud), "ola_measures": sum(o["measures"] for o in ola),
            "matched": len(pairs),
            "same_staves": sum(a["staves"] == o["staves"] for a, o in pairs),
            "same_measures": sum(a["measures"] == o["measures"] for a, o in pairs)}


def ola_measures(pages: list[layout.Page], images: list[Path], boxes: dict) -> dict[int, int]:
    """{global system index: OLA measure count} for systems whose matched OLA system has the
    same staff count (the pipeline's `measure_vote: ola`)."""
    out, k = {}, 0
    for page, img in zip(pages, images):
        with Image.open(img) as im:
            sy_ = im.height / page.height if page.height else 1.0
        ola = ola_systems(boxes.get(img.name, []))
        for sy in page.systems:
            staves = sy.all_staves     # meta keep_staves may have left some out
            top, bottom = min(s.top for s in staves) * sy_, max(s.bottom for s in staves) * sy_
            best = max(ola, key=lambda o: min(bottom, o["box"][3]) - max(top, o["box"][1]), default=None)
            if best and min(bottom, best["box"][3]) > max(top, best["box"][1]) \
                    and best["staves"] == len(staves) and best["measures"]:
                out[k] = best["measures"]
            k += 1
    return out


def truth_bars(show: str, results: Path) -> dict[str, int]:
    """{work dir id: truth bar count} from the latest bench of a show (rows per PDF)."""
    benches = sorted((results / show / "bench").glob("*/scores.json"), key=lambda p: p.stat().st_mtime)
    if not benches:
        return {}
    out: dict[str, int] = {}
    for r in json.loads(benches[-1].read_text())["rows"]:
        sid = f"{show}-{r['song']}--{r['part']}"
        out[sid] = max(out.get(sid, 0), r.get("bars_truth") or 0)
    return out


def sample_truth_bars(data: Path) -> dict[str, int]:
    from lxml import etree
    out = {}
    for gt in sorted(data.glob("samples/*/gt.musicxml")):
        part = etree.parse(str(gt)).getroot().find("part")
        if part is not None:
            out[gt.parent.name] = len(part.findall("measure"))
    return out


def layout_bench(cfg: dict, run_root: Path, truth: dict[str, int], out_dir: Path, dpi: int) -> dict:
    device = cfg.get("device", "cpu")
    rows = []
    for wd in sorted(p for p in (run_root / "pipeline").iterdir() if (p / "audiveris" / "out").exists()):
        images = sorted((run_root / "_pages" / wd.name / f"{dpi}dpi").glob("page*.png"))
        pages = layout.load(wd / "audiveris" / "out")
        if not images or len(images) < len(pages):
            LOG.warning(f"{wd.name}: {len(images)} page images for {len(pages)} pages, skipped")
            continue
        t0 = time.perf_counter()
        try:
            boxes, st = ola_boxes(run_root, wd, images, device)
        except RuntimeError as e:
            LOG.error(f"{wd.name}: {e}")
            continue
        per_page = [compare_page(p, img, boxes.get(img.name, [])) for p, img in zip(pages, images)]
        tot = {k: sum(pp[k] for pp in per_page) for k in per_page[0]} if per_page else {}
        row = {"id": wd.name, "pages": len(pages), **tot, "truth_bars": truth.get(wd.name),
               "stats": asdict(st) if st else None, "wall_s": round(time.perf_counter() - t0, 1)}
        rows.append(row)
        LOG.info(f"{wd.name}: systems aud {tot.get('aud_systems')} / ola {tot.get('ola_systems')}, "
                 f"measures aud {tot.get('aud_measures')} / ola {tot.get('ola_measures')} / truth {row['truth_bars']}")
    data = {"run": str(run_root), "time": datetime.now().isoformat(timespec="seconds"), "device": device,
            "rows": rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "layout.json").write_text(json.dumps(data, indent=1))
    (out_dir / "layout.md").write_text(report(data))
    return data


def report(data: dict) -> str:
    rows = data["rows"]

    def err(r, k):
        return None if not r["truth_bars"] else r[k] - r["truth_bars"]

    lines = [f"# Layout components ({data['time']})", "", f"Pipeline run: `{data['run']}`; OLA on {data['device']}.",
             "", "Measures = printed measures (a multi-measure rest is one), truth = bars of the truth part. "
             "Agreement = share of Audiveris systems with an overlapping OLA system that has the same "
             "staff / measure count.", "",
             "| part | pages | systems aud/ola | matched | same staves | same measures | measures aud/ola/truth | OLA time s | OLA peak RAM MB | OLA peak VRAM MB |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        st = r.get("stats") or {}
        lines.append(f"| {r['id']} | {r['pages']} | {r['aud_systems']}/{r['ola_systems']} | {r['matched']} | "
                     f"{r['same_staves']} | {r['same_measures']} | {r['aud_measures']}/{r['ola_measures']}/"
                     f"{r['truth_bars'] if r['truth_bars'] is not None else '-'} | {st.get('wall_s', 0):.1f} | "
                     f"{st.get('peak_rss_mb', 0):.0f} | {st.get('peak_gpu_mem_mb') or 0:.0f} |")
    with_truth = [r for r in rows if r["truth_bars"]]
    m = sum(r["matched"] for r in rows) or 1
    lines += ["", f"**Totals** ({len(rows)} parts): systems Audiveris {sum(r['aud_systems'] for r in rows)}, "
              f"OLA {sum(r['ola_systems'] for r in rows)}; same staves {sum(r['same_staves'] for r in rows) / m:.1%}, "
              f"same measures {sum(r['same_measures'] for r in rows) / m:.1%} of matched systems."]
    if with_truth:
        exact = {k: sum(err(r, k) == 0 for r in with_truth) for k in ("aud_measures", "ola_measures")}
        mae = {k: sum(abs(err(r, k)) for r in with_truth) / len(with_truth) for k in ("aud_measures", "ola_measures")}
        lines.append(f"Measures vs truth bars ({len(with_truth)} parts): exact Audiveris {exact['aud_measures']}, "
                     f"OLA {exact['ola_measures']}; mean abs error Audiveris {mae['aud_measures']:.1f}, "
                     f"OLA {mae['ola_measures']:.1f}.")
    return "\n".join(lines) + "\n"
