"""`pipeline` engine: Audiveris layout + homr per staff group + repairs.

Steps (all timed into the engine's runtime):
1. Audiveris (meta.yaml switches) -> MusicXML + .omr (layout, text, directions)
2. rasterise the PDF; crop every staff group (a single staff, or a piano's grand staff)
   of every system using the Audiveris staff positions
3. homr on each crop (homr only reads 1-2 staff systems, crops make it usable on
   vocal scores and condensed parts)
4. assemble (see assemble.py): per-bar source choice, directions, printed text,
   multi-measure rests, bars lined up with the printed bar numbers, percussion split
   by instrument labels

Config (bench.yaml):
  pipeline:
    type: pipeline
    prefer: auto                # bar source order when both are valid; auto = homr
                                #   first on scans, audiveris first on vector PDFs
    split_percussion: auto      # auto = score type drums; true/false to force
    crop_margins: [5, 4, 3]     # interlines above/below a staff group; retried in order
    text_onset: bar             # bar = words at the bar start (as in the GTs); estimated
    align_bar_numbers: true     # rest bars where printed numbers / "[to] 97" cuts skip bars
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from PIL import Image

from .. import log as logmod
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
from .layout import where


LOG = logmod.get("pipeline")


def _last_error(log: Path) -> str:
    try:
        lines = [ln for ln in log.read_text(errors="replace").splitlines() if ln.strip()]
    except OSError:
        return "no output"
    for ln in reversed(lines[-60:]):
        if "Error" in ln or "Exception" in ln:
            return ln.strip()[-200:]
    return "no output"


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
                        im.crop(box).save(out, compress_level=1)
                        jobs.append((k, gi, len(g), out))
                    k += 1
        return jobs

    def _homr_batch(self, jobs: list, crop_dir: Path, log: Path, total: RunStats):
        """(job, error or None) per crop job, in order. The persistent worker pool by
        default; one `homr` process per crop with `pool: false` or extra_args."""
        if not jobs:
            return []
        if not self.homr.use_pool():
            out = []
            for job in jobs:
                img = job[3]
                st = run_monitored(self.homr.page_cmd(img, crop_dir), log_path=log, cwd=crop_dir,
                                   env=self.homr.env(), timeout_s=self.timeout_s)
                total.add(st)
                err = None
                if st.timed_out:
                    err = f"timeout after {self.timeout_s:.0f}s"
                elif self.homr.find_output(img, crop_dir) is None:
                    err = f"exit {st.exit_code}: {_last_error(log)}"
                out.append((job, err))
            return out
        pool = self.homr.pool()
        t0 = time.perf_counter()
        futs = [pool.submit(job[3], self.timeout_s) for job in jobs]
        results = [f.result() for f in futs]
        wall = time.perf_counter() - t0
        out = []
        with log.open("a", encoding="utf-8") as f:
            for job, r in zip(jobs, results):
                f.write(f"$ homr {r.image}\n{r.log}\n[ok={r.ok} wall={r.wall_s:.1f}s "
                        f"cpu={r.cpu_s:.1f}s{' timed_out' if r.timed_out else ''}]\n")
                LOG.debug(f"homr {r.image.name}: {'ok' if r.ok else r.error} ({r.wall_s:.1f}s)")
                out.append((job, None if r.ok else (r.error or "failed")))
        # workers run side by side: count the batch's elapsed time, the summed CPU time,
        # memory of the workers that were busy
        busy = min(len(jobs), len(pool.workers))
        rss = max((r.rss_mb for r in results), default=0.0)
        st = RunStats(wall_s=wall, wall_clock_s=wall, cpu_user_s=sum(r.cpu_s for r in results),
                      peak_rss_mb=rss * busy, peak_single_rss_mb=rss,
                      exit_code=0, timed_out=any(r.timed_out for r in results),
                      commands=[f"homr pool ({len(pool.workers)} workers): {len(jobs)} crops"])
        total.add(st)
        return out

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
        systems = [sy for p in pages for sy in p.systems]
        reasons: dict[tuple[int, int], list[str]] = {}
        todo = jobs
        LOG.info(f"homr on {len(jobs)} crops of {sum(not sy.skip for sy in systems)} systems")
        t_h = time.perf_counter()
        for attempt, margin in enumerate(margins):
            if attempt:
                wanted = {(k, gi) for k, gi, _, _ in todo}
                todo = [j for j in self._crop_jobs(pages, images, crop_dir, margin, f"-m{margin:g}")
                        if (j[0], j[1]) in wanted]
            failed = []
            for job, err in self._homr_batch(todo, crop_dir, log, total):
                k, gi, n_staves, img = job
                if err is None:
                    out = self.homr.find_output(img, crop_dir)
                    try:
                        if out is None:
                            raise ValueError("no MusicXML written")
                        roots[(k, gi)] = musicxml.load(out)
                    except Exception as e:  # noqa: BLE001 - a broken crop is just a missing candidate
                        err = f"unreadable output: {e}"
                if err is not None:
                    reasons.setdefault((k, gi), []).append(f"margin {margin:g}: {err}")
                    failed.append(job)
            if failed and attempt + 1 < len(margins):
                LOG.debug(f"homr: {len(failed)} crops failed at margin {margin:g}, retrying")
            todo = failed
            if not todo:
                break
        stats.homr_crops_failed = len(todo)
        stats.failed_crops = [(k, gi, n, img, reasons.get((k, gi), [])) for k, gi, n, img in todo]
        LOG.info(f"homr done in {time.perf_counter() - t_h:.0f}s: {len(roots)}/{len(jobs)} crops read")

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
            exp = stats.homr_crops_expected
            res.extras["warning"] = (f"homr failed on {stats.homr_crops_failed}/{len(jobs)} crops"
                                     + (f", {exp} of them rest-only systems" if exp else ""))
            log_fn = LOG.info if exp == stats.homr_crops_failed else LOG.warning
            log_fn(res.extras["warning"] + " (each listed above; details in engine.log)")

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
                got = max((b.staves for b in bars), default=0)
                LOG.warning(f"homr output of {where(systems, k)} staff group {gi + 1} unusable: "
                            + (f"read {got} staves, expected {n_staves}" if bars else "no bars")
                            + " -> Audiveris bars used")
        aud_bars = A.group_bars(A.audiveris_bars(a_roots, systems, D), systems)
        for k, gi, n_staves, img, why in stats.failed_crops:
            ab = aud_bars.get((k, gi))
            # "No noteheads found" on a staff of rests is homr working as designed
            expected = bool(ab) and all(b.rest_only for b in ab) and all("noteheads" in w for w in why)
            stats.homr_crops_expected += expected
            (LOG.info if expected else LOG.warning)(
                f"homr failed on {where(systems, k)} staff group {gi + 1} ({n_staves} staves)"
                f"{' (Audiveris reads only rests there: expected)' if expected else ''} -> Audiveris "
                f"bars used; {'; '.join(why)}; crop {img}")
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
        if self.cfg.get("align_bar_numbers", True):
            A.align_bars(plans, D, stats, LOG)
        names = {}
        # regrouped tracks are not the Audiveris parts, their names don't apply
        for r in a_roots[:1] if not any(sy.regrouped for sy in systems) else []:
            for i, sp in enumerate(r.findall("part-list/score-part"), start=1):
                names[i] = sp.findtext("part-name") or f"Part {i}"
        parts, times = A.build_parts(plans, split and bool(instruments), instruments, names,
                                     doubling=bool(sample.meta.get("doubling")),
                                     transpose=sample.meta.get("transpose"))
        score = A.write_score(parts, times, credits, D)
        for note in stats.notes:
            if not note.startswith("bar numbers:"):     # those were logged as they happened
                LOG.info(f"assemble: {note}")
        LOG.info(f"assembled {len(times)} bars in {len(parts)} part(s); bar sources "
                 f"{dict(stats.bars)}; {stats.multirest_bars_added} multi-rest and "
                 f"{stats.alignment_bars_added} alignment rest bars added")
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
