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
from datetime import datetime
from pathlib import Path

import pymupdf
from lxml import etree

from . import config as config_mod
from . import dataset
from . import musicxml

WINDOWS_MUSESCORE = Path("/mnt/c/Program Files/MuseScore 4/bin/MuseScore4.exe")


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


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
    with pymupdf.open(pdf) as doc:
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
               prefix_matching=False, force=False, run_id=None) -> int:
    """Return the number of failed PDFs."""
    engines = config_mod.engines(cfg, set(), [engine])
    if not engines:
        raise SystemExit(f"unknown engine '{engine}' (configured: {', '.join(cfg.get('engines') or {})})")
    eng = engines[0]
    if eng.kind == "external":
        raise SystemExit(f"engine '{engine}' is external and can't be run")
    ok, ver = eng.check()
    if not ok:
        raise SystemExit(f"engine {engine} unavailable: {ver}")
    _log(f"engine {engine}: {ver}")

    dirs, warnings = dataset.select_dirs(Path(cfg["data_dir"]), samples_only, samples_exclude,
                                         prefix_matching)
    for w in warnings:
        _log("WARN " + w)
    run_dir = Path(cfg["results_dir"]) / (run_id or f"transcribe-{datetime.now():%Y%m%d-%H%M%S}")
    done = skipped = failed = 0
    outputs: list[tuple[Path, Path]] = []   # (pdf, musicxml) of every selected PDF with output
    for d in dirs:
        folder_meta = dataset.load_meta(d / "meta.yaml")
        for pdf in sorted(d.glob("*.pdf")):
            out = pdf.with_suffix(".musicxml")
            label = f"{d.name}/{pdf.name}"
            if out.exists() and not force:
                _log(f"{label}: {out.name} exists, skipped (--force to redo)")
                skipped += 1
                outputs.append((pdf, out))
                continue
            sid = f"{d.name}--{pdf.stem}"
            wd = run_dir / engine / sid
            try:
                meta = {**folder_meta, **dataset.load_meta(pdf.with_suffix(".yaml"))}
                src = pdf
                if meta.get("pages") is not None:
                    src = subset_pdf(pdf, meta["pages"], wd / "subset.pdf")
            except Exception as e:  # bad meta / page range is per-PDF
                _log(f"{label}: FAILED {type(e).__name__}: {e}")
                failed += 1
                continue
            sample = dataset.Sample(sid, d, src, None, meta)
            pages = f" (pages {meta['pages']})" if meta.get("pages") is not None else ""
            _log(f"{label}{pages}: running {engine} ...")
            r = eng.run(sample, wd)
            if r.error or r.output is None:
                _log(f"{label}: FAILED {r.error}; see {wd}")
                failed += 1
                continue
            shutil.copyfile(r.output, out)
            took = f" in {r.stats.wall_s:.0f}s" if r.stats else ""
            _log(f"{label}: -> {out.name}{took}" + (f" ({r.extras['warning']})"
                                                    if "warning" in r.extras else ""))
            done += 1
            outputs.append((pdf, out))
    _log(f"done: {done} written, {skipped} skipped, {failed} failed")
    if outputs:
        _combine(outputs, run_dir, cfg)
    _log(f"results in {run_dir}")
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
        _log(f"combine FAILED {type(e).__name__}: {e}")
        return
    _log(f"combined {len(files)} files -> {combined.name}")
    exe = find_musescore(cfg.get("musescore_cli"))
    if not exe:
        _log("WARN MuseScore CLI not found (set musescore_cli in bench.yaml); no combined.mscz")
        return
    try:
        clean = to_mscz(combined, combined.with_suffix(".mscz"), exe)
        _log("-> combined.mscz" + ("" if clean else " (MuseScore flagged differing bar counts/"
                                    "lengths between parts and filled them; saved with -f)"))
    except Exception as e:  # noqa: BLE001
        _log(f"combined.mscz FAILED {type(e).__name__}: {e}")
