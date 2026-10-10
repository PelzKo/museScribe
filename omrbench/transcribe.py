"""Transcribe mode: run one engine on the parts of a show's songs, or on every PDF of the
selected sample folders. No ground truth, no scoring, no report. data/ is only read.

A show (data/<show>/, see project.py): every part of every selected song, with its pages
taken straight from the full-book PDF in data/<show>/pdfs/. A sample folder
(data/samples/<sample>/): every *.pdf, with meta.yaml merged under <name>.yaml (keys there win).

Outputs, per song (results/<show>/<song>/) or sample (results/samples/<sample>/):

    <name>.musicxml             latest transcription of the PDF <name>
    <name> - Voices.musicxml,   instead, for a piano reduction (type: piano_reduction): the
    <name> - Piano.musicxml     singers (one part per printed label, with lyrics) and the piano
    combined.musicxml / .mscz   all of the folder's files stacked as parts of one score, from
                                bar 1, parts named after the file (.mscz needs the MuseScore CLI)
    manifest.json               per PDF: input key, run, engine, code version, time

A PDF whose input key (PDF size/mtime, resolved meta, engine settings) is unchanged since its
last output is skipped unless --force; a code change alone doesn't redo it.

Per run, results/<show>/runs/<timestamp>/ (results/samples/runs/... for samples):

    <song>/<name>.musicxml      this run's outputs
    <engine>/<id>/              engine work dirs (subset.pdf, crops, pipeline.json)
    _pages/                     rendered pages
    run.log
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pymupdf
from lxml import etree

from . import config as config_mod
from . import dataset
from . import log as logmod
from . import musicxml
from . import project as project_mod
from .rasterize import FITZ_LOCK, pdf_pages

WINDOWS_MUSESCORE = Path("/mnt/c/Program Files/MuseScore 4/bin/MuseScore4.exe")
SPLIT_TYPES = {"piano_reduction": ("Voices", "Piano")}   # score type -> output files
MANIFEST = "manifest.json"                               # per output folder: what made each file


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


# ES_CONTINUOUS | ES_SYSTEM_REQUIRED for as long as this PowerShell runs; it blocks reading
# stdin, so it exits (and Windows may sleep again) when transcribe ends or dies
_AWAKE_PS = (
    "Add-Type -Name P -Namespace W -MemberDefinition '[DllImport(\"kernel32.dll\")] public static "
    "extern uint SetThreadExecutionState(uint f);'; "
    "if ([W.P]::SetThreadExecutionState([uint32]2147483649) -eq 0) { exit 1 }; "
    "[void][Console]::In.ReadToEnd()"
)


@contextmanager
def keep_awake(enabled: bool):
    """Keep Windows (also from WSL) from sleeping while the block runs; the screen may
    still turn off."""
    if not enabled:
        yield
        return
    ps = shutil.which("powershell.exe")
    if not ps:
        LOG.warning("--keep-awake: powershell.exe not found (only Windows / WSL supported); "
                    "the PC may sleep during the run")
        yield
        return
    proc = subprocess.Popen([ps, "-NoProfile", "-NonInteractive", "-Command", _AWAKE_PS],
                            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    time.sleep(3)
    if proc.poll() is not None:
        LOG.warning(f"--keep-awake: PowerShell exited (code {proc.returncode}); "
                    "the PC may sleep during the run")
        yield
        return
    LOG.info("keep-awake on: Windows won't sleep until the run ends (the screen may turn off)")
    try:
        yield
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        LOG.info("keep-awake off: Windows may sleep again")


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


def output_names(name: str, meta: dict) -> list[str]:
    """The MusicXML file name(s) transcribe writes for the PDF `name`."""
    split = SPLIT_TYPES.get(meta.get("type"))
    return [f"{name} - {n}.musicxml" for n in split] if split else [f"{name}.musicxml"]


@dataclass
class Job:
    group: str            # song id / sample folder: one output folder, one combined score
    name: str             # PDF stem
    pdf: Path
    meta: dict
    sid: str              # log / work dir id, "anastasia-1--Horn"


def input_key(job: Job, engine: str, spec: dict) -> str:
    """Changes when the PDF, its meta or the engine settings change (not with the code)."""
    st = job.pdf.stat()
    blob = json.dumps({"pdf": job.pdf.name, "size": st.st_size, "mtime": st.st_mtime_ns,
                       "meta": job.meta, "engine": engine, "spec": spec},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def code_version() -> str:
    repo = Path(__file__).resolve().parent.parent
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, check=True,
                             capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "omrbench"], cwd=repo,
                               capture_output=True, text=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_manifest(d: Path) -> dict:
    f = d / MANIFEST
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def project_jobs(cfg: dict, name: str, songs=None, parts=None) -> tuple[Path, list[str], list[Job], list[str]]:
    """(output root, group order, jobs, problems) for the songs of a show in data/."""
    folder = project_mod.find(Path(cfg["data_dir"]), name)
    if folder is None:
        raise SystemExit(f"no show '{name}' (a folder with show.yaml in {cfg['data_dir']})")
    proj = project_mod.load(folder)
    selected, missing = proj.select(songs)
    problems = [f"no sheet for song {s}" for s in missing]
    jobs = []
    for song in selected:
        problems += [f"{proj.name}-{song.id}: {e}" for e in song.errors]
        for part in song.parts:
            if parts and part.name not in parts:
                continue
            jobs.append(Job(song.id, part.name, part.pdf, part.meta, f"{proj.name}-{song.id}--{part.name}"))
    if parts and (unknown := set(parts) - {p.name for s in selected for p in s.parts}):
        problems.append(f"no part {', '.join(sorted(unknown))} in the selected songs")
    return Path(cfg["results_dir"]) / proj.name, [s.id for s in selected], jobs, problems


def sample_jobs(cfg: dict, only=None, exclude=None, prefix=False) -> tuple[Path, list[str], list[Job], list[str]]:
    """Every PDF of the selected sample folders (data/samples/<sample>/*.pdf)."""
    dirs, problems = dataset.select_dirs(Path(cfg["samples_dir"]), only, exclude, prefix)
    jobs = []
    for d in dirs:
        folder_meta = dataset.load_meta(d / "meta.yaml")
        for pdf in sorted(d.glob("*.pdf")):
            try:
                meta = {**folder_meta, **dataset.load_meta(pdf.with_suffix(".yaml"))}
            except Exception as e:  # bad meta is per-PDF
                problems.append(f"{d.name}/{pdf.name}: {type(e).__name__}: {e}")
                continue
            jobs.append(Job(d.name, pdf.stem, pdf, meta, f"{d.name}--{pdf.stem}"))
    return Path(cfg["results_dir"]) / "samples", [d.name for d in dirs], jobs, problems


def transcribe(cfg: dict, *, project: str | None = None, songs=None, parts=None,
               engine: str = "pipeline", samples_only=None, samples_exclude=None,
               prefix_matching=False, force=False, run_id=None, jobs=None, awake=False) -> int:
    """Return the number of failed PDFs. awake: keep Windows from sleeping meanwhile.

    With `project`, the songs of that show; else every PDF of the selected sample folders."""
    if project:
        root, groups, todo, problems = project_jobs(cfg, project, songs, parts)
    else:
        root, groups, todo, problems = sample_jobs(cfg, samples_only, samples_exclude, prefix_matching)
    if not todo:
        raise SystemExit("nothing selected" + "".join(f"\n  {p}" for p in problems))
    run_dir = root / "runs" / (run_id or datetime.now().strftime("%Y%m%d-%H%M%S"))
    log_path = logmod.setup(run_dir)
    LOG.info(f"transcribe run {run_dir}; log: {log_path}")
    for p in problems:
        LOG.error(p)
    with keep_awake(awake):
        failed = _transcribe(cfg, root, run_dir, groups, todo, engine, force, jobs)
    return failed + len(problems)


def _transcribe(cfg: dict, root: Path, run_dir: Path, groups: list[str], jobs_in: list[Job],
                engine: str, force: bool, jobs) -> int:
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
    spec = (cfg.get("engines") or {}).get(engine) or {}
    code = code_version()

    skipped = failed = 0
    manifests = {g: _read_manifest(root / g) for g in groups}
    order = {g: [] for g in groups}          # group -> PDF names in order (for combined)
    todo = []                                # (job, key, outs, sample, work dir, pages)
    for job in jobs_in:
        label = f"{job.sid.replace('--', '/', 1)}.pdf"
        order[job.group].append(job)
        outs = output_names(job.name, job.meta)
        try:
            key = input_key(job, engine, spec)
        except OSError as e:
            LOG.error(f"{label}: FAILED {e}")
            failed += 1
            continue
        prev = manifests[job.group].get(job.name) or {}
        if not force and prev.get("key") == key and all((root / job.group / o).exists() for o in outs):
            LOG.info(f"{label}: unchanged since run {prev.get('run')}, skipped (--force to redo)")
            skipped += 1
            continue
        wd = run_dir / engine / job.sid
        try:
            src = job.pdf
            if job.meta.get("pages") is not None:
                src = subset_pdf(job.pdf, job.meta["pages"], wd / "subset.pdf")
            n_pages = pdf_pages(src)
        except Exception as e:  # bad meta / page range is per-PDF
            LOG.error(f"{label}: FAILED {type(e).__name__}: {e}", extra={"sample": job.sid})
            failed += 1
            continue
        todo.append((job, key, outs, dataset.Sample(job.sid, job.pdf.parent, src, None, job.meta),
                     wd, n_pages))

    # several PDFs at once: Audiveris of one overlaps homr of another (homr crops of all
    # of them share one worker pool); the longest first so the last one doesn't run alone
    n_jobs = max(1, int(jobs or cfg.get("transcribe_jobs", 2)))
    todo.sort(key=lambda j: -j[5])
    LOG.info(f"{len(todo)} PDFs to transcribe ({sum(j[5] for j in todo)} pages), "
             f"{min(n_jobs, len(todo) or 1)} at a time")
    t0 = time.perf_counter()

    def one(item):
        job, key, outs, sample, wd, n_pages = item
        label = f"{job.sid.replace('--', '/', 1)}.pdf"
        with logmod.context(sample.id):
            pages = f" (pages {sample.meta['pages']})" if sample.meta.get("pages") is not None else ""
            LOG.info(f"{label}{pages}: running {engine} on {n_pages} pages ...")
            r = eng.run(sample, wd)
            if r.error or r.output is None:
                LOG.error(f"{label}: FAILED {r.error}; see {wd}")
                return item, None
            split = r.extras.get("split_outputs") or {}
            if len(outs) > 1:
                if len(split) != len(outs):
                    LOG.error(f"{label}: FAILED engine {engine} wrote no separate "
                              f"{' / '.join(SPLIT_TYPES[sample.meta.get('type')])} files")
                    return item, None
                srcs = list(split.values())
            else:
                srcs = [r.output]
            took = f" in {r.stats.wall_s:.0f}s" if r.stats else ""
            msg = f"{label}: -> {', '.join(outs)}{took}"
            if "warning" in r.extras:
                LOG.warning(f"{msg} ({r.extras['warning']})")
            else:
                LOG.info(msg)
            return item, srcs

    done = 0
    changed: set[str] = set()
    with ThreadPoolExecutor(max_workers=n_jobs) as ex:
        for fut in as_completed([ex.submit(one, j) for j in todo]):
            try:
                (job, key, outs, _, wd, _), srcs = fut.result()
            except Exception as e:  # noqa: BLE001 - one PDF never stops the others
                LOG.error(f"transcription crashed: {type(e).__name__}: {e}", exc_info=True)
                failed += 1
                continue
            if srcs is None:
                failed += 1
                continue
            done += 1
            # the run keeps its own copy; the group folder holds the latest output
            for dest in (run_dir / job.group, root / job.group):
                dest.mkdir(parents=True, exist_ok=True)
                for out, src in zip(outs, srcs):
                    shutil.copyfile(src, dest / out)
            manifests[job.group][job.name] = {
                "key": key, "outputs": outs, "run": run_dir.name, "engine": engine,
                "code": code, "pdf": str(job.pdf), "pages": job.meta.get("pages"),
                "time": datetime.now().isoformat(timespec="seconds")}
            (root / job.group / MANIFEST).write_text(
                json.dumps(manifests[job.group], indent=1, ensure_ascii=False), encoding="utf-8")
            changed.add(job.group)
    LOG.info(f"done in {time.perf_counter() - t0:.0f}s: {done} written, {skipped} unchanged, "
             f"{failed} failed")
    for g in groups:
        files = [(Path(o).stem, root / g / o) for job in order[g]
                 for o in output_names(job.name, job.meta) if (root / g / o).exists()]
        if files and (g in changed or not (root / g / "combined.musicxml").exists()):
            _combine(g, files, root / g, cfg)
    LOG.info(f"latest outputs in {root}/<{'song' if root.name != 'samples' else 'sample'}>/, "
             f"this run in {run_dir}")
    return failed


def _combine(group: str, files: list[tuple[str, Path]], dest: Path, cfg: dict) -> None:
    """Stack the group's latest files into dest/combined.musicxml (+ .mscz)."""
    exe = find_musescore(cfg.get("musescore_cli"))
    with logmod.context(group):
        try:
            combined = combine(files, dest / "combined.musicxml")
        except Exception as e:  # noqa: BLE001 - the individual files are still there
            LOG.error(f"combine FAILED {type(e).__name__}: {e}", exc_info=True)
            return
        LOG.info(f"combined {len(files)} files -> {combined}")
        if not exe:
            LOG.warning("MuseScore CLI not found (set musescore_cli in bench.yaml); no .mscz written")
            return
        mscz = combined.with_suffix(".mscz")
        try:
            if to_mscz(combined, mscz, exe):
                LOG.info(f"-> {mscz.name}")
            else:
                LOG.warning(f"-> {mscz.name} (MuseScore flagged differing bar counts/lengths "
                            "between parts and filled them; saved with -f)")
        except Exception as e:  # noqa: BLE001
            LOG.error(f"{mscz.name} FAILED {type(e).__name__}: {e}")
