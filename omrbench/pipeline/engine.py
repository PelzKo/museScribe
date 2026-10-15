"""`pipeline` engine: Audiveris layout + a crop recognizer (homr) per staff group + repairs.

Steps (all timed into the engine's runtime):
1. Audiveris (meta.yaml switches) -> MusicXML + .omr (layout, text, directions)
2. rasterise the PDF; crop every staff group (a single staff, or a piano's grand staff)
   of every system using the Audiveris staff positions; Tesseract reads bar numbers,
   ranges and cut marks around the staves where Audiveris' OCR found none (ocr.py)
3. the crop recognizer on each crop (recognizer.py; homr only reads 1-2 staff
   systems, crops make it usable on vocal scores and condensed parts)
4. assemble (see assemble.py): per-bar source choice, directions, printed text,
   multi-measure rests, bars lined up with the printed bar numbers, percussion split
   by instrument labels

Config (bench.yaml):
  pipeline:
    type: pipeline
    recognizer: homr            # crop recognizer (recognizer.py); its options under its name
    prefer: auto                # bar source order when both are valid ("crop", "audiveris");
                                #   auto = crop first on scans, audiveris first on vector PDFs
    split_percussion: auto      # auto = score type drums; true/false to force
    crop_margins: [5, 4, 3]     # interlines above/below a staff group; retried in order
    text_onset: bar             # bar = words at the bar start (as in the GTs); estimated
    align_bar_numbers: true     # rest bars where printed numbers / "[to] 97" cuts skip bars
    auto_beam: true             # beam unbeamed eighths and shorter by beat
    max_wedge_bars: 2           # longer hairpins are misread pairings: dropped (0 = keep)
    ocr_bar_numbers: true       # second OCR pass (Tesseract) for bar numbers / ranges
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from lxml import etree
from PIL import Image

from .. import log as logmod
from .. import musicxml
from ..dataset import Sample
from ..engines.audiveris import Audiveris
from ..engines.base import Engine, EngineResult
from ..monitor import RunStats
from ..pdfkind import is_scan
from ..project import bar_map
from ..rasterize import rasterize
from . import assemble as A
from . import bars as B
from . import chords as CH
from . import drumkit
from . import layout
from . import ocr
from . import recognizer as R
from . import vocal as V
from .layout import where


LOG = logmod.get("pipeline")


def book_roots(mxls: list[Path]) -> list:
    """The Audiveris MusicXML of every .omr book, in layout.load's book order (None for
    a book without export). Sheet by sheet, a sheet whose export failed has its .omr
    but no .mxl: the exports alone would put every later page's bars on the page
    before. Several movements of a book (book.mvt1.mxl, ...) are concatenated."""
    if not mxls:
        return []
    out_dir = min((p.parent for p in mxls), key=lambda d: len(d.parts))
    while out_dir.name.startswith("sheet") and out_dir.parent != out_dir:
        out_dir = out_dir.parent
    out = []
    for omr in sorted(out_dir.rglob("*.omr")):
        # book.mvt2.mxl before book.mvt10.mxl
        mine = sorted((p for p in mxls if p.parent == omr.parent),
                      key=lambda p: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", p.name)])
        if not mine:
            out.append(None)
            continue
        roots = [musicxml.load(p) for p in mine]
        for r in roots[1:]:
            # a movement starts a new system, but its first <print> doesn't say so
            for part in r.findall("part"):
                m = part.find("measure")
                if m is None:
                    continue
                pr = m.find("print")
                if pr is None:
                    pr = etree.Element("print")
                    m.insert(0, pr)
                if pr.get("new-page") != "yes":
                    pr.set("new-system", "yes")
        out.append(roots[0] if len(roots) == 1 else musicxml.merge_pages(roots))
    return out


class Pipeline(Engine):
    kind = "pipeline"

    def __init__(self, name: str, cfg: dict, bench: dict):
        super().__init__(name, cfg, bench)
        self.audiveris = Audiveris(f"{name}/audiveris",
                                   {**(cfg.get("audiveris") or {}), "type": "audiveris",
                                    "use_metadata": True}, bench)
        self.recognizer = R.build(name, cfg, bench)

    def check(self) -> tuple[bool, str]:
        ok_a, va = self.audiveris.check()
        ok_h, vh = self.recognizer.check()
        return ok_a and ok_h, f"audiveris {va}; {self.recognizer.name} {vh}"

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
        ocr_dir = workdir / "ocr"
        if ocr_dir.exists():
            shutil.rmtree(ocr_dir)
        self.add_ocr_text(pages, images, ocr_dir, sample.pdf)
        res.prep_s = time.perf_counter() - t0

        # 3. recognizer per crop; homr is sensitive to the crop (e.g. "No noteheads found" at one
        #    margin, fine at another), so failed crops are retried with other margins
        roots: dict[tuple[int, int], object] = {}
        stats = A.Stats()
        systems = [sy for p in pages for sy in p.systems]
        reasons: dict[tuple[int, int], list[str]] = {}
        todo = jobs
        rec = self.recognizer
        LOG.info(f"{rec.name} on {len(jobs)} crops of {sum(not sy.skip for sy in systems)} systems")
        t_h = time.perf_counter()
        for attempt, margin in enumerate(margins):
            if attempt:
                wanted = {(k, gi) for k, gi, _, _ in todo}
                todo = [j for j in self._crop_jobs(pages, images, crop_dir, margin, f"-m{margin:g}")
                        if (j[0], j[1]) in wanted]
            failed = []
            for job, err in rec.recognize(todo, crop_dir, log, total, self.timeout_s):
                k, gi, n_staves, img = job
                if err is None:
                    out = rec.output(img, crop_dir)
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
                LOG.debug(f"{rec.name}: {len(failed)} crops failed at margin {margin:g}, retrying")
            todo = failed
            if not todo:
                break
        stats.crops_failed = len(todo)
        stats.failed_crops = [(k, gi, n, img, reasons.get((k, gi), [])) for k, gi, n, img in todo]
        LOG.info(f"{rec.name} done in {time.perf_counter() - t_h:.0f}s: {len(roots)}/{len(jobs)} crops read")
        self._ensemble_crops(jobs, workdir, log, total)

        # 4. assemble
        t1 = time.perf_counter()
        score, summary, files = self.assemble(sample, pages, books, roots, stats, workdir)
        summary["crops"] = len(jobs)
        res.output = workdir / "output.musicxml"
        musicxml.write(score, res.output)
        if files:
            # vocal score: the piano and the voices as files of their own (transcribe
            # writes them next to the PDF); output.musicxml has both, for scoring
            res.extras["split_outputs"] = {}
            for name, root in files.items():
                path = workdir / f"output-{name.lower()}.musicxml"
                musicxml.write(root, path)
                res.extras["split_outputs"][name] = path
        assemble_s = time.perf_counter() - t1
        # assembly runs in this process: count its wall time, CPU is negligible
        total.wall_s += assemble_s
        total.wall_clock_s += assemble_s
        res.stats = total
        summary["assemble_s"] = round(assemble_s, 2)
        (workdir / "pipeline.json").write_text(json.dumps(summary, indent=2))
        res.extras["summary"] = workdir / "pipeline.json"
        if stats.crops_failed:
            exp = stats.crops_expected
            res.extras["warning"] = (f"{rec.name} failed on {stats.crops_failed}/{len(jobs)} crops"
                                     + (f", {exp} of them rest-only systems" if exp else ""))
            log_fn = LOG.info if exp == stats.crops_failed else LOG.warning
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
        if self.vocal(sample):
            layout.regroup(pages, skip=skip, piano_bottom=2)
            return
        layout.regroup(pages, keep_bottom=keep, singles=self.split(sample) and not keep, skip=skip)

    @staticmethod
    def vocal(sample: Sample) -> bool:
        """Vocal score: piano = the lowest two staves, voices split by singer labels,
        written as two files (transcribe.SPLIT_TYPES)."""
        return sample.score_type == "piano_reduction"

    def measure_votes(self, sample: Sample, pages: list[layout.Page], workdir: Path) -> dict | None:
        """`measure_vote: ola`: OLA's measure count per system as one more bar-count vote."""
        if self.cfg.get("measure_vote") != "ola":
            return None
        from .. import components
        dpi = int(self.cfg.get("dpi", self.bench.get("dpi", 300)))
        run_root = workdir.parent.parent
        images = sorted((run_root / "_pages" / sample.id / f"{dpi}dpi").glob("page*.png"))
        boxes, _ = components.ola_boxes(run_root, workdir, images, self.bench.get("device", "cpu"))
        return components.ola_measures(pages, images, boxes)

    def _ensemble_crops(self, jobs: list, workdir: Path, log: Path, total: RunStats) -> None:
        """`ensemble` readers read the same crops (first margin) into <workdir>/crops-<reader>/."""
        for name in self.cfg.get("ensemble") or []:
            edir = workdir / f"crops-{name}"
            if edir.exists():
                shutil.rmtree(edir)
            edir.mkdir(parents=True)
            rec = R._one(name, self.name, self.cfg, self.bench)
            mine = []
            for k, gi, n, img in jobs:
                if rec.staves is None or n in rec.staves:
                    shutil.copyfile(img, edir / img.name)
                    mine.append((k, gi, n, edir / img.name))
            t0 = time.perf_counter()
            bad = sum(err is not None for _, err in rec.recognize(mine, edir, log, total, self.timeout_s))
            LOG.info(f"ensemble {name}: {len(mine) - bad}/{len(mine)} crops read in {time.perf_counter() - t0:.0f}s")

    def ensemble_roots(self, workdir: Path, systems: list) -> dict:
        """`ensemble: [zeus, clarity, ...]`: {reader: {(k, gi): <score>}} of more crop readers, read
        from <workdir>/crops-<reader>/s<k>-g<g>.musicxml (same crops as the main reader)."""
        out = {}
        for name in self.cfg.get("ensemble") or []:
            roots = {}
            for f in sorted((workdir / f"crops-{name}").glob("s*-g*.musicxml")):
                m = re.fullmatch(r"s(\d+)-g(\d+)", f.stem)
                if not m:
                    continue
                k, gi = int(m.group(1)) - 1, int(m.group(2)) - 1
                if k >= len(systems) or gi >= len(systems[k].groups()):
                    continue
                try:
                    roots[(k, gi)] = musicxml.load(f)
                except Exception as e:  # noqa: BLE001 - one unreadable crop is no reading
                    LOG.debug(f"{name} {f.name}: {e}")
            out[name] = roots
        return out

    @staticmethod
    def ensemble_bars(ens: dict, systems: list, D: int) -> dict | None:
        """Bars of the ensemble readers' crops (`ensemble_roots`) that have the crop's staves."""
        out = {}
        for name, roots in ens.items():
            bars = {}
            for (k, gi), r in roots.items():
                part = r.find("part")
                n_staves = len(systems[k].groups()[gi])
                bs = B.part_bars(part, D, "crop", staves=n_staves) if part is not None else []
                if bs and max(b.staves for b in bs) == n_staves:
                    bars[(k, gi)] = bs
            out[name] = bars
        return out or None

    def assemble(self, sample: Sample, pages: list[layout.Page], books: list[Path],
                 roots: dict, stats: A.Stats, workdir: Path | None = None):
        """Steps after the engines ran; also usable on a finished work dir (see reassemble)."""
        a_roots = book_roots(books)
        systems = [sy for p in pages for sy in p.systems]
        ens = self.ensemble_roots(workdir, systems) if workdir else {}
        # the ensemble readers' divisions too (Clarity / SMT 10080, Zeus 3 or 56): no rounding
        D = B.common_divisions([r for r in a_roots if r is not None] + list(roots.values())
                               + [r for e in ens.values() for r in e.values()])
        rec = self.recognizer.name
        crop_bars = {}
        for (k, gi), r in roots.items():
            part = r.find("part")
            n_staves = len(systems[k].groups()[gi])
            bars = B.part_bars(part, D, "crop", staves=n_staves) if part is not None else []
            if bars and max(b.staves for b in bars) == n_staves:
                crop_bars[(k, gi)] = bars
            else:
                stats.crops_failed += 1
                got = max((b.staves for b in bars), default=0)
                LOG.warning(f"{rec} output of {where(systems, k)} staff group {gi + 1} unusable: "
                            + (f"read {got} staves, expected {n_staves}" if bars else "no bars")
                            + " -> Audiveris bars used")
        vocal = self.vocal(sample)
        aud_bars = A.group_bars(A.audiveris_bars(a_roots, systems, D), systems)
        for k, gi, n_staves, img, why in stats.failed_crops:
            ab = aud_bars.get((k, gi))
            # "No noteheads found" on a staff of rests is homr working as designed
            expected = bool(ab) and all(b.rest_only for b in ab) and all("noteheads" in w for w in why)
            stats.crops_expected += expected
            (LOG.info if expected else LOG.warning)(
                f"{rec} failed on {where(systems, k)} staff group {gi + 1} ({n_staves} staves)"
                f"{' (Audiveris reads only rests there: expected)' if expected else ''} -> Audiveris "
                f"bars used; {'; '.join(why)}; crop {img}")
        prefer = self.cfg.get("prefer") or "auto"
        if prefer == "auto":
            # homr reads scans better; on born-digital PDFs Audiveris is near perfect
            # and also has ties, which homr never outputs
            prefer = ["crop", "audiveris"] if is_scan(sample.pdf) else ["audiveris", "crop"]
        # the recognizer's name (e.g. "homr") stands for its crops
        prefer = ["crop" if s in rec.split("+") else s for s in prefer]
        self.last_prefer = prefer
        # repairs: false = level 2 of the recognizer comparison (PLAN.md section 7): crop bars as read
        repairs = bool(self.cfg.get("repairs", True))
        votes = self.measure_votes(sample, pages, workdir) if workdir else None
        alts = self.ensemble_bars(ens, systems, D)
        song_time = bar_map(sample.meta["song_time"]) if sample.meta.get("song_time") else None
        plans = A.plan_systems(pages, aud_bars, crop_bars, D, prefer, stats, raw=not repairs, extra_votes=votes,
                                 alts=alts, pick_mode=self.cfg.get("ensemble_pick", "agree"),
                                 weights=self.cfg.get("ensemble_weights"), song_time=song_time)
        if vocal:
            V.attach_lyrics(plans, pages, D, stats)
            V.place_marks(plans, pages, D, stats)
        if sample.meta.get("cues") == "drop":
            A.drop_cues(plans, pages, D, stats)
        split = self.split(sample)
        # text_onset: bar = at the start of the bar it is printed in (the convention of the
        # ground truths here); estimated = beat estimated from its x position
        estimate = self.cfg.get("text_onset", "bar") == "estimated"
        # chord symbols of born-digital pages from the PDF text layer (Audiveris misses them)
        symbols = [] if is_scan(sample.pdf) else CH.read(sample.pdf, pages)
        if sample.score_type != "piano_reduction":     # the truths have no chord symbols there
            A.place_chords(plans, pages, symbols, D, stats)
        credits, instruments = A.place_text(plans, pages, D, stats, sample.meta, split, estimate, symbols)
        if repairs:
            A.expand_multirests(plans, crop_bars, D, stats)
        if repairs and self.cfg.get("align_bar_numbers", True):
            A.align_bars(plans, D, stats, LOG)
        if song_time:
            A.apply_song_time(plans, song_time, stats)
        beam = bool(self.cfg.get("auto_beam", True))
        max_wedge = int(self.cfg.get("max_wedge_bars", 2))
        files: dict[str, object] = {}
        if vocal:
            # male_voices: extra singer names written in treble-8vb ("Dmitry", "Vlad")
            male = [A.MALE_VOICES] + [re.escape(str(n)) for n in sample.meta.get("male_voices") or []]
            voices, piano, times = A.build_vocal_parts(
                plans, D, stats, re.compile("|".join(male), re.I))
            A.share_system_text([voices, [piano]], times, D)
            parts = voices + [piano]
            if max_wedge:
                A.limit_wedges(parts, max_wedge, stats)
            sk = self.song_key(sample, stats, len(times))
            files = {"Voices": A.write_score(voices, times, credits, D, beam, stats, sk),
                     "Piano": A.write_score([piano], times, credits, D, beam, stats, sk)}
            score = musicxml.merge_parts([files["Voices"], files["Piano"]])
        else:
            names = {}
            # regrouped tracks are not the Audiveris parts, their names don't apply
            for r in [r for r in a_roots if r is not None][:1] \
                    if not any(sy.regrouped for sy in systems) else []:
                for i, sp in enumerate(r.findall("part-list/score-part"), start=1):
                    names[i] = sp.findtext("part-name") or f"Part {i}"
            parts, times = A.build_parts(plans, split and bool(instruments), instruments, names,
                                         doubling=bool(sample.meta.get("doubling")),
                                         transpose=sample.meta.get("transpose"))
            if max_wedge:
                A.limit_wedges(parts, max_wedge, stats)
            score = A.write_score(parts, times, credits, D, beam, stats, self.song_key(sample, stats, len(times)))
            if sample.score_type == "drums" and (kit := drumkit.kit_for(sample.meta.get("show"))):
                LOG.info(f"drum legend: {drumkit.apply(score, kit)} notes snapped to a kit position")
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
        return score, summary, files

    def song_key(self, sample: Sample, stats: A.Stats, n: int) -> list | None:
        """The concert key of each output bar from the song's `key` row (None: not given)."""
        if not sample.meta.get("song_key"):
            return None
        return A.song_positions(bar_map(sample.meta["song_key"]), stats.letters, stats.pickup, n)

    def add_ocr_text(self, pages: list[layout.Page], images: list[Path], ocr_dir: Path, pdf: Path) -> None:
        """Bar numbers where Audiveris' OCR has no text: the PDF text layer on vector pages,
        Tesseract elsewhere (cached in ocr_dir)."""
        if not self.cfg.get("ocr_bar_numbers", True):
            return
        tess = ocr.find_tesseract(self.home)
        if tess is None:
            LOG.warning("tesseract not found (PATH or Audiveris jars): bar numbers from the text layer only")
        t0 = time.perf_counter()
        engine = self.cfg.get("ocr_engine", "tesseract")
        if engine != "tesseract":
            # own cache per engine (component benchmark); the default keeps `ocr/`
            ocr_dir = ocr_dir.with_name(f"ocr-{engine}")
        words = ocr.read_pages(pages, images, tess, ocr_dir, pdf=pdf, engine=engine,
                               device=self.bench.get("device", "cpu"))
        added = sum(ocr.supplement(p, w) for p, w in zip(pages, words))
        LOG.info(f"bar-number OCR: {added} text items added on {len(words)} pages "
                 f"in {time.perf_counter() - t0:.0f}s")

    def reassemble(self, sample: Sample, workdir: Path):
        """Re-run only the assembly on an existing work dir (development aid).
        Returns (score, summary, split files)."""
        omr_src = workdir / "audiveris" / "out"
        pages = layout.load(omr_src)
        self.regroup(sample, pages)
        if self.cfg.get("ocr_bar_numbers", True):
            dpi = int(self.cfg.get("dpi", self.bench.get("dpi", 300)))
            images = rasterize(sample.pdf, workdir.parent.parent / "_pages" / sample.id / f"{dpi}dpi", dpi=dpi)
            self.add_ocr_text(pages, images, workdir / "ocr", sample.pdf)
        roots = {}
        for f in sorted((workdir / "crops").glob("s*-g*.musicxml")):
            k, g = f.stem[1:].split("-g")
            key = (int(k) - 1, int(g.split("-")[0]) - 1)
            roots.setdefault(key, musicxml.load(f))
        stats = A.Stats()
        return self.assemble(sample, pages, sorted(omr_src.rglob("*.mxl")), roots, stats, workdir)
