"""`pipeline` engine: Audiveris layout + homr per staff group + repairs.

Steps (all timed into the engine's runtime):
1. Audiveris (meta.yaml switches) -> MusicXML + .omr (layout, text, directions)
2. rasterise the PDF; crop every staff group (a single staff, or a piano's grand staff)
   of every system using the Audiveris staff positions
3. homr on each crop (homr only reads 1-2 staff systems, crops make it usable on
   vocal scores and condensed parts)
4. assemble (see assemble.py): per-bar source choice, directions, printed text,
   multi-measure rests, percussion split by instrument labels

Config (bench.yaml):
  pipeline:
    type: pipeline
    prefer: auto                # bar source order when both are valid; auto = homr
                                #   first on scans, audiveris first on vector PDFs
    split_percussion: auto      # auto = score type drums; true/false to force
    crop_margins: [5, 4, 3]     # interlines above/below a staff group; retried in order
    text_onset: bar             # bar = words at the bar start (as in the GTs); estimated
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from PIL import Image

from .. import musicxml
from ..dataset import Sample
from ..engines.audiveris import Audiveris
from ..engines.base import Engine, EngineResult
from ..engines.pagewise import Homr
from ..monitor import RunStats, run_monitored
from ..rasterize import is_scan, rasterize
from . import assemble as A
from . import bars as B
from . import layout


class Pipeline(Engine):
    kind = "pipeline"

    def __init__(self, name: str, cfg: dict, bench: dict):
        super().__init__(name, cfg, bench)
        self.audiveris = Audiveris(f"{name}/audiveris",
                                   {**(cfg.get("audiveris") or {}), "type": "audiveris",
                                    "use_metadata": True}, bench)
        self.homr = Homr(f"{name}/homr", {**(cfg.get("homr") or {}), "type": "homr"}, bench)

    def check(self) -> tuple[bool, str]:
        ok_a, va = self.audiveris.check()
        ok_h, vh = self.homr.check()
        return ok_a and ok_h, f"audiveris {va}; homr {vh}"

    # -- steps ----------------------------------------------------------------
    def _crop_jobs(self, pages: list[layout.Page], images: list[Path], crop_dir: Path,
                   margin: float, tag: str = ""):
        jobs = []
        k = 0
        for page, img_path in zip(pages, images):
            with Image.open(img_path) as im:
                sx = im.width / page.width if page.width else 1.0
                sy_ = im.height / page.height if page.height else 1.0
                # left-out staves still bound the crops, so none shows up in a neighbour
                staves = sorted((st for sy in page.systems for st in sy.all_staves), key=lambda s: s.top)
                for sy in page.systems:
                    if sy.skip:
                        k += 1
                        continue
                    for gi, g in enumerate(sy.groups()):
                        il = g[0].interline
                        above = [s.bottom for s in staves if s.bottom < g[0].top]
                        below = [s.top for s in staves if s.top > g[-1].bottom]
                        top = g[0].top - margin * il
                        if above:
                            top = max(top, (max(above) + g[0].top) / 2)
                        bottom = g[-1].bottom + margin * il
                        if below:
                            bottom = min(bottom, (min(below) + g[-1].bottom) / 2)
                        top = min(top, g[0].top - 2.5 * il)
                        bottom = max(bottom, g[-1].bottom + 2.5 * il)
                        left = min(s.left for s in g) - 3 * il
                        right = max(s.right for s in g) + 3 * il
                        box = (max(0, int(left * sx)), max(0, int(top * sy_)),
                               min(im.width, int(right * sx)), min(im.height, int(bottom * sy_)))
                        out = crop_dir / f"s{k + 1:02d}-g{gi + 1}{tag}.png"
                        im.crop(box).save(out)
                        jobs.append((k, gi, len(g), out))
                    k += 1
        return jobs

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        # bad meta fails now, not after the engines ran
        A.parse_transpose(sample.meta.get("transpose"))
        for it in sample.meta.get("instruments") or []:
            if isinstance(it, dict):
                A.parse_transpose(it.get("transpose"))
                if it.get("clef") and str(it["clef"]).lower() not in A.CLEF_CLASS:
                    raise ValueError(f"instruments: clef '{it['clef']}' (use {', '.join(A.CLEF_CLASS)})")
        log = workdir / "engine.log"
        if log.exists():
            log.unlink()
        total = RunStats()

        # 1. Audiveris
        a_res = self.audiveris.run(sample, workdir / "audiveris")
        res.pages = a_res.pages
        if a_res.stats:
            total.add(a_res.stats)
        omr_src = workdir / "audiveris" / "out"
        books = sorted(omr_src.rglob("*.mxl"))
        if a_res.error or not books:
            res.stats = total
            res.error = f"audiveris step failed: {a_res.error}"
            return
        pages = layout.load(omr_src)
        self.regroup(sample, pages)

        # 2. raster + crops
        t0 = time.perf_counter()
        dpi = int(self.cfg.get("dpi", self.bench.get("dpi", 300)))
        images = rasterize(sample.pdf, workdir.parent.parent / "_pages" / sample.id / f"{dpi}dpi", dpi=dpi)
        crop_dir = workdir / "crops"
        if crop_dir.exists():
            shutil.rmtree(crop_dir)
        crop_dir.mkdir(parents=True)
        margins = [float(m) for m in self.cfg.get("crop_margins", [5, 4, 3])]
        jobs = self._crop_jobs(pages, images, crop_dir, margins[0])
        res.prep_s = time.perf_counter() - t0

        # 3. homr per crop; homr is sensitive to the crop (e.g. "No noteheads found" at one
        #    margin, fine at another), so failed crops are retried with other margins
        roots: dict[tuple[int, int], object] = {}
        stats = A.Stats()
        todo = jobs
        for attempt, margin in enumerate(margins):
            if attempt:
                wanted = {(k, gi) for k, gi, _, _ in todo}
                todo = [j for j in self._crop_jobs(pages, images, crop_dir, margin, f"-m{margin:g}")
                        if (j[0], j[1]) in wanted]
            failed = []
            for job in todo:
                k, gi, n_staves, img = job
                st = run_monitored(self.homr.page_cmd(img, crop_dir), log_path=log, cwd=crop_dir,
                                   env=self.homr.env(), timeout_s=self.timeout_s)
                total.add(st)
                out = self.homr.find_output(img, crop_dir)
                try:
                    if out is None or st.timed_out:
                        raise ValueError("no output")
                    roots[(k, gi)] = musicxml.load(out)
                except Exception:  # noqa: BLE001 - a broken crop is just a missing candidate
                    failed.append(job)
            todo = failed
            if not todo:
                break
        stats.homr_crops_failed = len(todo)

        # 4. assemble
        t1 = time.perf_counter()
        score, summary = self.assemble(sample, pages, books, roots, stats)
        summary["crops"] = len(jobs)
        res.output = workdir / "output.musicxml"
        musicxml.write(score, res.output)
        assemble_s = time.perf_counter() - t1
        # assembly runs in this process: count its wall time, CPU is negligible
        total.wall_s += assemble_s
        total.wall_clock_s += assemble_s
        res.stats = total
        summary["assemble_s"] = round(assemble_s, 2)
        (workdir / "pipeline.json").write_text(json.dumps(summary, indent=2))
        res.extras["summary"] = workdir / "pipeline.json"
        if stats.homr_crops_failed:
            res.extras["warning"] = f"homr failed on {stats.homr_crops_failed}/{len(jobs)} crops"

    def split(self, sample: Sample) -> bool:
        split_cfg = self.cfg.get("split_percussion", "auto")
        split = sample.score_type == "drums" if split_cfg == "auto" else bool(split_cfg)
        return bool(sample.meta.get("split_instruments", split))

    def regroup(self, sample: Sample, pages: list[layout.Page]) -> None:
        """meta keep_staves / skip_systems, and one staff per group when splitting."""
        m = sample.meta
        keep = int(m["keep_staves"]) if m.get("keep_staves") else None
        skip = {int(x) for x in (m.get("skip_systems") or [])}
        layout.regroup(pages, keep_bottom=keep, singles=self.split(sample) and not keep, skip=skip)

    def assemble(self, sample: Sample, pages: list[layout.Page], books: list[Path],
                 roots: dict, stats: A.Stats):
        """Steps after the engines ran; also usable on a finished work dir (see reassemble)."""
        a_roots = [musicxml.load(p) for p in books]
        D = B.common_divisions(a_roots + list(roots.values()))
        systems = [sy for p in pages for sy in p.systems]
        homr_bars = {}
        for (k, gi), r in roots.items():
            part = r.find("part")
            n_staves = len(systems[k].groups()[gi])
            bars = B.part_bars(part, D, "homr", staves=n_staves) if part is not None else []
            if bars and max(b.staves for b in bars) == n_staves:
                homr_bars[(k, gi)] = bars
            else:
                stats.homr_crops_failed += 1
        aud_bars = A.group_bars(A.audiveris_bars(a_roots, systems, D), systems)
        prefer = self.cfg.get("prefer") or "auto"
        if prefer == "auto":
            # homr reads scans better; on born-digital PDFs Audiveris is near perfect
            # and also has ties, which homr never outputs
            prefer = ["homr", "audiveris"] if is_scan(sample.pdf) else ["audiveris", "homr"]
        prefer = list(prefer)
        self.last_prefer = prefer
        plans = A.plan_systems(pages, aud_bars, homr_bars, D, prefer, stats)
        if sample.meta.get("cues") == "drop":
            A.drop_cues(plans, pages, D, stats)
        split = self.split(sample)
        # text_onset: bar = at the start of the bar it is printed in (the convention of the
        # ground truths here); estimated = beat estimated from its x position
        estimate = self.cfg.get("text_onset", "bar") == "estimated"
        credits, instruments = A.place_text(plans, pages, D, stats, sample.meta, split, estimate)
        A.expand_multirests(plans, homr_bars, D, stats)
        names = {}
        # regrouped tracks are not the Audiveris parts, their names don't apply
        for r in a_roots[:1] if not any(sy.regrouped for sy in systems) else []:
            for i, sp in enumerate(r.findall("part-list/score-part"), start=1):
                names[i] = sp.findtext("part-name") or f"Part {i}"
        parts, times = A.build_parts(plans, split and bool(instruments), instruments, names,
                                     doubling=bool(sample.meta.get("doubling")),
                                     transpose=sample.meta.get("transpose"))
        score = A.write_score(parts, times, credits, D)
        self.last_plans = plans
        summary = {**stats.to_dict(), "divisions": D,
                   "systems_bars": [p.n for p in plans],
                   "instruments": [i["name"] for i in instruments],
                   "parts": [p.name for p in parts]}
        return score, summary

    def reassemble(self, sample: Sample, workdir: Path):
        """Re-run only the assembly on an existing work dir (development aid)."""
        omr_src = workdir / "audiveris" / "out"
        pages = layout.load(omr_src)
        self.regroup(sample, pages)
        roots = {}
        for f in sorted((workdir / "crops").glob("s*-g*.musicxml")):
            k, g = f.stem[1:].split("-g")
            key = (int(k) - 1, int(g.split("-")[0]) - 1)
            roots.setdefault(key, musicxml.load(f))
        stats = A.Stats()
        return self.assemble(sample, pages, sorted(omr_src.rglob("*.mxl")), roots, stats)
