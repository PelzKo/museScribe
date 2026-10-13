"""Benchmark a show's transcriptions against its full-score truth.

For every selected song with a truth file (songs.xlsx, B2), every part's output in
results/<show>/<song>/ (or a run's copy, --run) is compared with the truth part(s) named in
the row's `truth` cell:

  Violine 1                       the row's only output part
  Piccolo, Flöte 1                one per instrument, in `instruments` order (split parts);
                                  "-" leaves that instrument out
  Piano=Klavierauszug, Men=Männer by output part name (piano reductions: the parts of both
                                  output files; singer parts are named after the printed label)

Several output parts naming the same truth part are compared together (Bell Tree + Mark Tree
-> Glockenbaum). Metrics: note F1 (metrics/notef1.py) per truth part and per song (micro:
summed over the parts); with --full also OMR-NED and TEDn per truth part (slow).

Writes results/<show>/bench/<timestamp>/: scores.json, metrics.csv, report.md, and with
--full the per-part files that were compared (parts/<song>/).
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from . import log as logmod
from . import musicxml
from . import project as project_mod
from . import truth as truth_mod
from .metrics import notef1
from .transcribe import MANIFEST, output_names

LOG = logmod.get("bench")
MAIN = "notes"           # the headline variant


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def resolve(part: project_mod.Part, outputs: list[tuple[str, object]]) -> tuple[dict, list[str], list[str]]:
    """Map the row's `truth` cell onto its output parts.

    outputs: (part name, <part>) of all of the row's output files.
    Returns ({truth name: [output part names]}, unmapped output part names, problems).
    A truth name whose output part is missing maps to [] (scored as all missed)."""
    mapping: dict[str, list[str]] = {}
    problems = []
    by_name = {_norm(n): n for n, _ in outputs}
    positional = []
    for entry in part.truth:
        out, eq, tru = entry.partition("=")
        if eq:
            out, tru = out.strip(), tru.strip()
            if tru == "-":
                by_name.pop(_norm(out), None)
                continue
            if _norm(out) not in by_name:   # nothing read for it: scored as all missed
                mapping.setdefault(tru, [])
                continue
            mapping.setdefault(tru, []).append(by_name.pop(_norm(out)))
        else:
            positional.append(entry.strip())
    if positional:
        if len(positional) == 1 and len(outputs) <= 1 and len(part.instruments) <= 1:
            names = [n for n, _ in outputs]
            if positional[0] != "-":
                mapping.setdefault(positional[0], []).extend(names)
            for n in names:
                by_name.pop(_norm(n), None)
        elif len(positional) == len(part.instruments):
            for inst, tru in zip(part.instruments, positional):
                hit = by_name.pop(_norm(inst), None)
                if tru == "-":
                    continue
                mapping.setdefault(tru, []).extend([hit] if hit else [])
        else:
            problems.append(f"{part.name}: truth '{', '.join(part.truth)}' has {len(positional)} "
                            f"names for {len(part.instruments) or len(outputs)} "
                            f"{'instruments' if part.instruments else 'output parts'}; "
                            "use 'Output=Truth' entries")
    return mapping, sorted(by_name.values()), problems


def _sum(rows: list[dict], variant: str) -> dict:
    tp = sum(r["metrics"][variant]["tp"] for r in rows)
    p = sum(r["metrics"][variant]["pred"] for r in rows)
    t = sum(r["metrics"][variant]["truth"] for r in rows)
    return notef1.prf(tp, p, t)


def _previous(bench_root: Path, this: Path) -> dict:
    """{(song, truth part): f1} of the latest earlier bench."""
    runs = sorted((d for d in bench_root.iterdir() if d.is_dir() and d != this
                   and (d / "scores.json").exists()),
                  key=lambda d: (d / "scores.json").stat().st_mtime) if bench_root.is_dir() else []
    if not runs:
        return {}
    data = json.loads((runs[-1] / "scores.json").read_text(encoding="utf-8"))
    return {"_id": runs[-1].name, **{(r["song"], r["truth"]): r["metrics"][MAIN]["f1"]
                                    for r in data["rows"]}}


def _perf(root: Path, src_root: Path, sid: str, entry: dict) -> dict | None:
    """Runtime and memory of the engine run that wrote a PDF's output: the work dir's result.json
    (the run named in the song's manifest, or with --run the work dirs of that run)."""
    if src_root != root:        # --run: that run's own work dirs
        cands = sorted(src_root.glob(f"*/{sid}/result.json"))
    elif entry.get("run") and entry.get("engine"):
        cands = [root / "runs" / entry["run"] / entry["engine"] / sid / "result.json"]
    else:
        cands = []
    f = next((c for c in cands if c.exists()), None)
    if f is None:
        return None
    r = json.loads(f.read_text(encoding="utf-8"))
    st = r.get("stats") or {}
    return {"engine": r.get("engine"), "pages": r.get("pages"), "wall_s": st.get("wall_s"),
            "cpu_s": (st.get("cpu_user_s") or 0) + (st.get("cpu_sys_s") or 0),
            "peak_rss_mb": st.get("peak_rss_mb"), "peak_gpu_mem_mb": st.get("peak_gpu_mem_mb"),
            "timed_out": st.get("timed_out")}


def bench(cfg: dict, show: str, *, songs=None, run: str | None = None, full: bool = False,
          bench_id: str | None = None) -> int:
    """Return the number of problems (missing outputs, unmappable truth cells)."""
    folder = project_mod.find(Path(cfg["data_dir"]), show)
    if folder is None:
        raise SystemExit(f"no show '{show}' (a folder with show.yaml in {cfg['data_dir']})")
    proj = project_mod.load(folder)
    selected, missing = proj.select(songs)
    selected = [s for s in selected if s.truth]
    if missing or not selected:
        raise SystemExit("nothing to benchmark" + "".join(f"\n  no sheet for song {s}" for s in missing)
                         + ("" if selected else "\n  no selected song has a truth file (songs.xlsx, B2)"))
    root = Path(cfg["results_dir"]) / proj.name
    src_root = root / "runs" / run if run else root
    if run and not src_root.is_dir():
        raise SystemExit(f"no run {src_root}")
    out_dir = root / "bench" / (bench_id or datetime.now().strftime("%Y%m%d-%H%M%S"))
    logmod.setup(out_dir)
    cache = Path(cfg["results_dir"]) / "cache"
    LOG.info(f"bench {proj.name} songs {', '.join(s.id for s in selected)} on "
             f"{'run ' + run if run else 'latest outputs'} -> {out_dir}")

    rows: list[dict] = []
    perf: list[dict] = []
    songs_out: list[dict] = []
    problems: list[str] = []
    for song in selected:
        with logmod.context(f"{proj.name}-{song.id}"):
            try:
                tpath = truth_mod.convert(song.truth, cache, cfg.get("musescore_cli"))
            except Exception as e:  # noqa: BLE001 - one song never stops the others
                problems.append(f"{song.id}: truth {song.truth.name}: {e}")
                LOG.error(problems[-1])
                continue
            troot = musicxml.load(tpath)
            tparts = {_norm(n): (n, p) for n, p in truth_mod.parts(troot)}
            t_bars = musicxml.measure_count(troot)
            manifest = json.loads((src_root / song.id / MANIFEST).read_text(encoding="utf-8")) \
                if (src_root / song.id / MANIFEST).exists() else {}
            used: set[str] = set()
            song_rows = []
            for part in song.parts:
                if not part.truth:
                    continue
                pf = _perf(root, src_root, f"{proj.name}-{song.id}--{part.name}", manifest.get(part.name) or {})
                if pf:
                    perf.append({"song": song.id, "part": part.name, **pf})
                files = [src_root / song.id / n for n in output_names(part.name, part.meta)]
                if not all(f.exists() for f in files):
                    problems.append(f"{song.id}/{part.name}: no output in {src_root / song.id} "
                                    f"(omrbench transcribe {proj.name} --songs {song.id})")
                    LOG.error(problems[-1])
                    outputs, oroots = [], []
                else:
                    oroots = [musicxml.load(f) for f in files]
                    outputs = [x for r in oroots for x in truth_mod.parts(r)]
                owner = {n: r for r in oroots for n, _ in truth_mod.parts(r)}
                mapping, unmapped, probs = resolve(part, outputs)
                problems += [f"{song.id}/{p}" for p in probs]
                for p in probs:
                    LOG.error(p)
                if unmapped:
                    LOG.warning(f"{part.name}: output parts not compared: {', '.join(unmapped)}")
                el = dict(outputs)
                for tname, onames in mapping.items():
                    if _norm(tname) not in tparts:
                        problems.append(f"{song.id}/{part.name}: no part '{tname}' in "
                                        f"{song.truth.name} (has {', '.join(n for n, _ in tparts.values())})")
                        LOG.error(problems[-1])
                        continue
                    tn, tpart = tparts[_norm(tname)]
                    used.add(_norm(tname))
                    pred = [n for o in onames for n in notef1.notes(el[o])]
                    tru = notef1.notes(tpart)
                    row = {"song": song.id, "part": part.name, "outputs": onames, "truth": tn,
                           "bars_pred": max((len(el[o].findall("measure")) for o in onames), default=0),
                           "bars_truth": t_bars, "metrics": notef1.compare(pred, tru),
                           "wrong_bars": notef1.wrong_bars(pred, tru),
                           "run": (manifest.get(part.name) or {}).get("run")}
                    if full:
                        row["full"] = _full(out_dir / "parts" / song.id, tn, troot, tpart,
                                            [(owner[o], el[o]) for o in onames], cfg)
                    song_rows.append(row)
            not_compared = [n for k, (n, p) in tparts.items()
                            if k not in used and notef1.notes(p)]
            summary = {"song": song.id, "title": song.title, "truth_file": song.truth.name,
                       "bars_truth": t_bars,
                       "metrics": {v: _sum(song_rows, v) for v in notef1.VARIANTS},
                       "truth_parts_not_compared": not_compared}
            if not_compared:
                LOG.warning(f"truth parts with notes that no row names: {', '.join(not_compared)}")
            rows += song_rows
            songs_out.append(summary)

    prev = _previous(root / "bench", out_dir)
    data = {"show": proj.name, "source": str(src_root), "time": datetime.now().isoformat(timespec="seconds"),
            "previous": prev.get("_id"), "songs": songs_out, "rows": rows, "perf": perf, "problems": problems,
            "total": {v: _sum(rows, v) for v in notef1.VARIANTS}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scores.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    _csv(out_dir / "metrics.csv", rows)
    text = _report(data, prev)
    (out_dir / "report.md").write_text(text, encoding="utf-8")
    print(text)
    LOG.info(f"report: {out_dir / 'report.md'}")
    return len(problems)


def _full(d: Path, tname: str, troot, tpart, preds: list, cfg: dict) -> dict:
    """OMR-NED / TEDn of one truth part against its output part(s)."""
    from .metrics import omrned
    from .scoring import _tedn, with_timeout

    sc = cfg.get("scoring", {})
    timeout = float(sc.get("metric_timeout_s", 900))
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in tname)
    tfile, pfile = d / f"{safe}.truth.musicxml", d / f"{safe}.pred.musicxml"
    musicxml.write(truth_mod.extract(troot, [tpart]), tfile)
    if not preds:
        return {"error": "no output part"}
    scores = [truth_mod.extract(r, [p]) for r, p in preds]
    pscore = musicxml.merge_parts(scores) if len(scores) > 1 else scores[0]
    musicxml.write(pscore, pfile)
    out: dict = {}
    for name, detail in (sc.get("omr_ned_variants") or {"all": "AllObjects"}).items():
        try:
            out[f"omr_ned_{name}"] = with_timeout(omrned.omr_ned, pfile, tfile, detail,
                                                  timeout=timeout)["omr_ned"]
        except Exception as e:  # noqa: BLE001
            out[f"omr_ned_{name}"] = None
            out.setdefault("errors", {})[name] = str(e)
    try:
        out["tedn"] = with_timeout(_tedn, pfile, tfile, int(sc.get("tedn_max_nodes", 2500)),
                                   timeout=timeout).get("tedn")
    except Exception as e:  # noqa: BLE001
        out["tedn"] = None
        out.setdefault("errors", {})["tedn"] = str(e)
    return out


def _f(x) -> str:
    return "-" if x is None else f"{x:.3f}"


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["song", "part", "outputs", "truth", "bars_pred", "bars_truth"]
                   + [f"{v}_{k}" for v in notef1.VARIANTS for k in ("f1", "precision", "recall")]
                   + ["omr_ned_all", "tedn", "run"])
        for r in rows:
            m = r["metrics"]
            w.writerow([r["song"], r["part"], "|".join(r["outputs"]), r["truth"], r["bars_pred"],
                        r["bars_truth"]]
                       + [m[v][k] for v in notef1.VARIANTS for k in ("f1", "precision", "recall")]
                       + [(r.get("full") or {}).get("omr_ned_all"), (r.get("full") or {}).get("tedn"),
                          r["run"]])


def _report(data: dict, prev: dict) -> str:
    full = any("full" in r for r in data["rows"])
    delta = bool(prev.get("_id"))
    lines = [f"# Bench {data['show']} ({data['time']})", "",
             f"Outputs: `{data['source']}`" + (f"; Δ vs bench {prev['_id']}" if delta else ""), "",
             "Note F1: notes = bar, staff, onset, sounding pitch, duration; pitch = without duration; "
             "pc = pitch class; rhythm = without pitch; aligned = notes with bars matched by best "
             "alignment instead of by index (reading quality without bar-count errors).", ""]
    hdr = ["song", "part", "truth", "bars", "notes F1", "P", "R", "pitch", "pc", "rhythm", "aligned"]
    hdr += ["OMR-NED", "TEDn"] if full else []
    hdr += ["Δ notes"] if delta else []
    lines += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]

    def line(cells):
        lines.append("| " + " | ".join(cells) + " |")

    for s in data["songs"]:
        for r in (r for r in data["rows"] if r["song"] == s["song"]):
            m = r["metrics"]
            name = r["part"] + (f" ({', '.join(r['outputs'])})" if r["outputs"] else " (no output)")
            bars = f"{r['bars_pred']}/{r['bars_truth']}" + ("" if r["bars_pred"] == r["bars_truth"] else " ⚠")
            cells = [s["song"], name, r["truth"], bars, _f(m["notes"]["f1"]), _f(m["notes"]["precision"]),
                     _f(m["notes"]["recall"]), _f(m["pitch"]["f1"]), _f(m["pc"]["f1"]), _f(m["rhythm"]["f1"]),
                     _f(m["aligned"]["f1"])]
            if full:
                fr = r.get("full") or {}
                cells += [_f(fr.get("omr_ned_all")), _f(fr.get("tedn"))]
            if delta:
                old, new = prev.get((r["song"], r["truth"])), m["notes"]["f1"]
                cells.append("new" if old is None else "-" if new is None else f"{new - old:+.3f}")
            line(cells)
        m = s["metrics"]
        cells = [f"**{s['song']}**", "**all**", "", "", f"**{_f(m['notes']['f1'])}**", _f(m["notes"]["precision"]),
                 _f(m["notes"]["recall"]), _f(m["pitch"]["f1"]), _f(m["pc"]["f1"]), _f(m["rhythm"]["f1"]),
                     _f(m["aligned"]["f1"])]
        cells += ["", ""] if full else []
        cells += [""] if delta else []
        line(cells)
    t = data["total"]
    lines += ["", f"**Total note F1 {_f(t['notes']['f1'])}** (P {_f(t['notes']['precision'])}, "
                  f"R {_f(t['notes']['recall'])}; {t['notes']['truth']} truth notes); "
                  f"bar-aligned {_f(t['aligned']['f1'])}", ""]
    perf = data.get("perf") or []
    if perf:
        def n(x, fmt="{:.0f}"):
            return "-" if x is None else fmt.format(x)
        pages = sum(p["pages"] or 0 for p in perf)
        wall = sum(p["wall_s"] or 0 for p in perf)
        lines += ["## Runtime and memory", "",
                  "Per PDF, from the run that wrote the output (work dir result.json). Time = summed step wall "
                  "times (Audiveris + crop reader + assembly); the crop reader pool is shared by the PDFs "
                  "transcribed at the same time, so its RAM (workers x worker RSS) is the pool's. VRAM = "
                  "NVML peak of the whole GPU (other processes included).", "",
                  "| song | part | engine | pages | time s | s/page | CPU s | peak RAM MB | peak VRAM MB |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for p in perf:
            spp = p["wall_s"] / p["pages"] if p["wall_s"] and p["pages"] else None
            lines.append(f"| {p['song']} | {p['part']} | {p['engine']} | {n(p['pages'])} | {n(p['wall_s'])}"
                         f"{' ⏱' if p.get('timed_out') else ''} | {n(spp, '{:.1f}')} | {n(p['cpu_s'])} | "
                         f"{n(p['peak_rss_mb'])} | {n(p['peak_gpu_mem_mb'])} |")
        lines += ["", f"**Total** {len(perf)} PDFs, {pages} pages: {wall:.0f} s summed "
                      f"({wall / pages:.1f} s/page), peak RAM {max(p['peak_rss_mb'] or 0 for p in perf):.0f} MB, "
                      f"peak VRAM {max(p['peak_gpu_mem_mb'] or 0 for p in perf):.0f} MB."
                  if pages else "", ""]
    worst = sorted((r for r in data["rows"] if r["wrong_bars"]),
                   key=lambda r: (r["metrics"]["notes"]["f1"] or 0))
    if worst:
        lines += ["## Bars that differ", ""]
        for r in worst:
            wb = r["wrong_bars"]
            lines.append(f"- {r['song']} {r['part']} → {r['truth']}: "
                         + ", ".join(map(str, wb[:30])) + (f" … ({len(wb)})" if len(wb) > 30 else ""))
        lines.append("")
    nc = [(s["song"], s["truth_parts_not_compared"]) for s in data["songs"] if s["truth_parts_not_compared"]]
    if nc or data["problems"]:
        lines += ["## Not compared", ""]
        lines += [f"- {song}: truth parts with notes no row names: {', '.join(n)}" for song, n in nc]
        lines += [f"- {p}" for p in data["problems"]]
        lines.append("")
    return "\n".join(lines)
