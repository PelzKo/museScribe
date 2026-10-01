"""Transcribe mode: run one engine on every PDF of the selected sample folders.

No ground truth, no scoring, no report. For every ``data/<sample>/<name>.pdf``:

    <name>.yaml         optional meta for this PDF; merged over the folder's meta.yaml
                        (keys here win). ``pages: "2-4,7"`` transcribes only those pages.
    <name>.musicxml     written next to the PDF (skipped if present, unless force)

Into ``results/transcribe-<timestamp>/``:

    <sample>--<name>.musicxml   copy of every selected PDF's <name>.musicxml (new or existing)
    combined.musicxml / .mscz   all of them stacked as parts of one score, all from bar 1;
                                parts named after the PDF (.mscz needs the MuseScore CLI)
    <engine>/<sample>--<name>/  engine work dirs
"""
from __future__ import annotations

import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pymupdf
from lxml import etree

from . import config as config_mod
from . import dataset
from . import log as logmod
from . import musicxml
from .rasterize import FITZ_LOCK, pdf_pages

WINDOWS_MUSESCORE = Path("/mnt/c/Program Files/MuseScore 4/bin/MuseScore4.exe")


LOG = logmod.get("transcribe")


def parse_pages(spec, n_pages: int) -> list[int]:
    """1-based page spec ("2-4,7", [2, 3, 4], 5) -> sorted 0-based indices."""
    if isinstance(spec, int):
        items = [str(spec)]
    elif isinstance(spec, (list, tuple)):
        items = [str(x) for x in spec]
    else:
        items = str(spec).split(",")
    pages: set[int] = set()
    for item in (x.strip() for x in items):
        if not item:
            continue
        lo, _, hi = item.partition("-")
        try:
            a, b = int(lo), int(hi or lo)
        except ValueError:
            raise ValueError(f"pages: bad range '{item}' (use e.g. \"2-4,7\")") from None
        if not 1 <= a <= b <= n_pages:
            raise ValueError(f"pages: '{item}' outside 1-{n_pages}")
        pages.update(range(a - 1, b))
    if not pages:
        raise ValueError("pages: empty page selection")
    return sorted(pages)


def subset_pdf(pdf: Path, spec, out: Path) -> Path:
    with FITZ_LOCK, pymupdf.open(pdf) as doc:
        keep = parse_pages(spec, doc.page_count)
        doc.select(keep)
        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out, garbage=3, deflate=True)
    return out


def find_musescore(configured: str | None) -> str | None:
    if configured:
        return configured
    for name in ("mscore", "musescore", "mscore4", "musescore4", "MuseScore4.exe"):
        if exe := shutil.which(name):
            return exe
    return str(WINDOWS_MUSESCORE) if WINDOWS_MUSESCORE.exists() else None


def to_mscz(src: Path, out: Path, exe: str) -> bool:
    """Convert with the MuseScore CLI; a Windows MuseScore (from WSL) gets Windows paths.

    Returns False if MuseScore only saved it with -f (it calls a score "corrupted" when
    parts differ in bar count or bar length, and fills the gaps itself).
    """
    def arg(p: Path) -> str:
        if not exe.lower().endswith(".exe"):
            return str(p)
        return subprocess.run(["wslpath", "-w", str(p.resolve())], check=True,
                              capture_output=True, text=True).stdout.strip()
    out.unlink(missing_ok=True)
    for force in (False, True):
        r = subprocess.run([exe, *(["-f"] if force else []), "-o", arg(out), arg(src)],
                           capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and out.exists():
            return not force
    raise RuntimeError(f"MuseScore exit {r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}")


def combine(files: list[tuple[str, Path]], out: Path) -> Path:
    """Stack the parts of every (name, musicxml) into one score, named after `name`."""
    roots = [musicxml.load(p) for _, p in files]
    counts = {name: len(r.find("part").findall("measure")) if r.find("part") is not None else 0
              for (name, _), r in zip(files, roots)}
    if len(set(counts.values())) > 1:
        LOG.warning("bar counts differ between the combined files: "
                    + ", ".join(f"{n}: {c}" for n, c in counts.items()))
    else:
        LOG.info(f"all {len(files)} combined files have {next(iter(counts.values()), 0)} bars")
    labels = []
    for (name, _), r in zip(files, roots):
        parts = r.findall("part-list/score-part")
        for sp in parts:
            pn = sp.findtext("part-name") or ""
            labels.append(f"{name} – {pn}" if len(parts) > 1 and pn else name)
    score = musicxml.merge_parts(roots)
    # title/credits of the first piece don't describe the combination
    for el in score.findall("credit") + score.findall("work") + score.findall("movement-title"):
        score.remove(el)
    for sp, label in zip(score.findall("part-list/score-part"), labels):
        pn = sp.find("part-name")
        if pn is None:
            pn = etree.SubElement(sp, "part-name")
            sp.insert(0, pn)
        pn.text = label
        for el in sp.findall("part-abbreviation"):
            sp.remove(el)
    musicxml.write(score, out)
    return out


def transcribe(cfg: dict, *, engine: str = "pipeline", samples_only=None, samples_exclude=None,
               prefix_matching=False, force=False, run_id=None, jobs=None) -> int:
    """Return the number of failed PDFs."""
    run_dir = Path(cfg["results_dir"]) / (run_id or f"transcribe-{datetime.now():%Y%m%d-%H%M%S}")
    log_path = logmod.setup(run_dir)
    LOG.info(f"transcribe run {run_dir.name}; log: {log_path}")
    engines = config_mod.engines(cfg, set(), [engine])
    if not engines:
        raise SystemExit(f"unknown engine '{engine}' (configured: {', '.join(cfg.get('engines') or {})})")
    eng = engines[0]
    if eng.kind == "external":
        raise SystemExit(f"engine '{engine}' is external and can't be run")
    ok, ver = eng.check()
    if not ok:
        LOG.error(f"engine {engine} unavailable: {ver}")
        raise SystemExit(f"engine {engine} unavailable: {ver}")
    LOG.info(f"engine {engine}: {ver}")

    dirs, warnings = dataset.select_dirs(Path(cfg["data_dir"]), samples_only, samples_exclude,
                                         prefix_matching)
    for w in warnings:
        LOG.warning(w)
    skipped = failed = 0
    outputs: dict[Path, Path] = {}     # pdf -> musicxml of every selected PDF with output
    order: list[Path] = []
    todo = []                          # (label, pdf, out, sample, work dir, pages)
    for d in dirs:
        folder_meta = dataset.load_meta(d / "meta.yaml")
        for pdf in sorted(d.glob("*.pdf")):
            out = pdf.with_suffix(".musicxml")
            label = f"{d.name}/{pdf.name}"
            order.append(pdf)
            if out.exists() and not force:
                LOG.info(f"{label}: {out.name} exists, skipped (--force to redo)")
                skipped += 1
                outputs[pdf] = out
                continue
            sid = f"{d.name}--{pdf.stem}"
            wd = run_dir / engine / sid
            try:
                meta = {**folder_meta, **dataset.load_meta(pdf.with_suffix(".yaml"))}
                src = pdf
                if meta.get("pages") is not None:
                    src = subset_pdf(pdf, meta["pages"], wd / "subset.pdf")
                n_pages = pdf_pages(src)
            except Exception as e:  # bad meta / page range is per-PDF
                LOG.error(f"{label}: FAILED {type(e).__name__}: {e}", extra={"sample": sid})
                failed += 1
                continue
            todo.append((label, pdf, out, dataset.Sample(sid, d, src, None, meta), wd, n_pages))

    # several PDFs at once: Audiveris of one overlaps homr of another (homr crops of all
    # of them share one worker pool); the longest first so the last one doesn't run alone
    n_jobs = max(1, int(jobs or cfg.get("transcribe_jobs", 2)))
    todo.sort(key=lambda j: -j[5])
    LOG.info(f"{len(todo)} PDFs to transcribe ({sum(j[5] for j in todo)} pages), "
             f"{min(n_jobs, len(todo) or 1)} at a time")
    t0 = time.perf_counter()

    def one(job):
        label, pdf, out, sample, wd, n_pages = job
        with logmod.context(sample.id):
            pages = f" (pages {sample.meta['pages']})" if sample.meta.get("pages") is not None else ""
            LOG.info(f"{label}{pages}: running {engine} on {n_pages} pages ...")
            r = eng.run(sample, wd)
            if r.error or r.output is None:
                LOG.error(f"{label}: FAILED {r.error}; see {wd}")
                return pdf, None
            shutil.copyfile(r.output, out)
            took = f" in {r.stats.wall_s:.0f}s" if r.stats else ""
            msg = f"{label}: -> {out.name}{took}"
            if "warning" in r.extras:
                LOG.warning(f"{msg} ({r.extras['warning']})")
            else:
                LOG.info(msg)
            return pdf, out

    done = 0
    with ThreadPoolExecutor(max_workers=n_jobs) as ex:
        for fut in as_completed([ex.submit(one, j) for j in todo]):
            try:
                pdf, out = fut.result()
            except Exception as e:  # noqa: BLE001 - one PDF never stops the others
                LOG.error(f"transcription crashed: {type(e).__name__}: {e}", exc_info=True)
                failed += 1
                continue
            if out is None:
                failed += 1
            else:
                done += 1
                outputs[pdf] = out
    LOG.info(f"done in {time.perf_counter() - t0:.0f}s: {done} written, {skipped} skipped, "
             f"{failed} failed")
    if outputs:
        _combine([(pdf, outputs[pdf]) for pdf in order if pdf in outputs], run_dir, cfg)
    LOG.info(f"results in {run_dir}")
    return failed


def _combine(outputs: list[tuple[Path, Path]], run_dir: Path, cfg: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    stems = [pdf.stem for pdf, _ in outputs]
    files = []
    for pdf, out in outputs:
        sid = f"{pdf.parent.name}--{pdf.stem}"
        shutil.copyfile(out, run_dir / f"{sid}.musicxml")
        # same PDF name in several folders (input.pdf): add the folder
        name = pdf.stem if stems.count(pdf.stem) == 1 else f"{pdf.parent.name}/{pdf.stem}"
        files.append((name, out))
    try:
        combined = combine(files, run_dir / "combined.musicxml")
    except Exception as e:  # noqa: BLE001 - the individual files are still there
        LOG.error(f"combine FAILED {type(e).__name__}: {e}", exc_info=True)
        return
    LOG.info(f"combined {len(files)} files -> {combined.name}")
    exe = find_musescore(cfg.get("musescore_cli"))
    if not exe:
        LOG.warning("MuseScore CLI not found (set musescore_cli in bench.yaml); no combined.mscz")
        return
    try:
        clean = to_mscz(combined, combined.with_suffix(".mscz"), exe)
        if clean:
            LOG.info("-> combined.mscz")
        else:
            LOG.warning("-> combined.mscz (MuseScore flagged differing bar counts/lengths "
                        "between parts and filled them; saved with -f)")
    except Exception as e:  # noqa: BLE001
        LOG.error(f"combined.mscz FAILED {type(e).__name__}: {e}")
