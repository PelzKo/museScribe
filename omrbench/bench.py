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
-> Glockenbaum). Metrics per truth part and per song (micro: summed over the parts):
  edit penalty (metrics/edits.py), the headline: MuseScore actions to turn the output into the
               truth, bars to fix; rehearsal marks and tempi once per song
  note F1      (metrics/notef1.py)
  element F1   per category (metrics/elements.py: dynamics, fermatas, chords, ...)
with --full also OMR-NED and TEDn per truth part (slow). Every bench appends a line to
results/<show>/bench/trend.csv.

Writes results/<show>/bench/<timestamp>/: scores.json, metrics.csv, report.md, and with
--full the per-part files that were compared (parts/<song>/).
"""
from __future__ import annotations

import csv
import subprocess
import json
from datetime import datetime
from pathlib import Path

from . import log as logmod
from . import musicxml
from . import project as project_mod
from . import truth as truth_mod
from .metrics import edits, elements, notef1
from .transcribe import MANIFEST, output_names

LOG = logmod.get("bench")
MAIN = "notes"           # the headline variant


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _unique(named: list[tuple]) -> list[tuple]:
    """Page engines name every part alike ("Voice", "Voice"): number the repeats ("Voice #2"), so
    each part is compared once."""
    seen: dict[str, int] = {}
    out = []
    for n, *rest in named:
        k = seen[_norm(n)] = seen.get(_norm(n), 0) + 1
        out.append((n if k == 1 else f"{n} #{k}", *rest))
    return out


def resolve(part: project_mod.Part, outputs: list[tuple[str, object]]) -> tuple[dict, list[str], list[str]]:
    """Map the row's `truth` cell onto its output parts.

    outputs: (part name, <part>) of all of the row's output files.
    Returns ({truth name: [output part names]}, unmapped output part names, problems).
    A truth name whose output part is missing maps to [] (scored as all missed)."""
    mapping: dict[str, list[str]] = {}
    problems = []
    by_name = {_norm(n): n for n, _ in outputs}
    unused = dict(by_name)      # an output part may feed several truth parts (duet label -> both)
    positional = []
    for entry in part.truth:
        out, eq, tru = entry.partition("=")
        if eq:
            out, tru = out.strip(), tru.strip()
            unused.pop(_norm(out), None)
            if tru == "-":
                continue
            if _norm(out) not in by_name:   # nothing read for it: scored as all missed
                mapping.setdefault(tru, [])
                continue
            mapping.setdefault(tru, []).append(by_name[_norm(out)])
        else:
            positional.append(entry.strip())
    if positional:
        if len(positional) == 1 and (len(part.instruments) <= 1 or part.meta.get("doubling")):
            # several output parts for one truth part (a page engine splitting a keyboard book):
            # compared together, like split instruments
            names = [n for n, _ in outputs if _norm(n) in unused]
            if positional[0] != "-":
                mapping.setdefault(positional[0], []).extend(names)
            for n in names:
                unused.pop(_norm(n), None)
        elif len(positional) == len(part.instruments):
            for inst, tru in zip(part.instruments, positional):
                hit = unused.pop(_norm(inst), None)
                if tru == "-":
                    continue
                mapping.setdefault(tru, []).extend([hit] if hit else [])
        else:
            problems.append(f"{part.name}: truth '{', '.join(part.truth)}' has {len(positional)} "
                            f"names for {len(part.instruments) or len(outputs)} "
                            f"{'instruments' if part.instruments else 'output parts'}; "
                            "use 'Output=Truth' entries")
    return mapping, sorted(unused.values()), problems


def _sum(rows: list[dict], variant: str) -> dict:
    tp = sum(r["metrics"][variant]["tp"] for r in rows)
    p = sum(r["metrics"][variant]["pred"] for r in rows)
    t = sum(r["metrics"][variant]["truth"] for r in rows)
    return notef1.prf(tp, p, t)


_EDIT_SUMS = ("penalty", "from_scratch", "bars_insert", "bars_delete", "bars_changed", "bars_to_fix",
              "bars_truth")


def _sum_edits(rows: list[dict], systems: list[dict]) -> dict:
    out = {k: sum(r["edits"].get(k, 0) for r in rows) for k in _EDIT_SUMS}
    by_cat: dict[str, int] = {}
    for e in [r["edits"] for r in rows] + systems:
        for c, v in e["by_cat"].items():
            by_cat[c] = by_cat.get(c, 0) + v
    out["penalty"] += sum(s["penalty"] for s in systems)
    out["from_scratch"] += sum(s["from_scratch"] for s in systems)
    out["ratio"] = out["penalty"] / out["from_scratch"] if out["from_scratch"] else None
    out["by_cat"] = by_cat
    return out


def _sum_elements(rows: list[dict]) -> dict:
    out = {}
    for c in musicxml.CATEGORIES:
        tp, p, g = (sum(r["elements"][c][k] for r in rows) for k in ("tp", "pred", "gt"))
        out[c] = elements.prf(tp, p, g)
    return out


def _trend(path: Path, bench_id: str, data: dict) -> None:
    """One line per bench, so regressions show up as a jump."""
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                cwd=Path(__file__).parent).stdout.strip()
    except OSError:
        commit = ""
    t, e = data["total"], data["total"]["edits"]
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["bench", "time", "commit", "source", "songs", "penalty", "from_scratch", "ratio",
                        "bars_to_fix", "bars_truth", "notes_f1", "aligned_f1"])
        w.writerow([bench_id, data["time"], commit, data["source"], " ".join(s["song"] for s in data["songs"]),
                    e["penalty"], e["from_scratch"], f"{e['ratio']:.4f}" if e["ratio"] is not None else "",
                    e["bars_to_fix"], e["bars_truth"], t["notes"]["f1"], t["aligned"]["f1"]])


def _previous(bench_root: Path, this: Path) -> dict:
    """{(song, truth part): edit penalty} of the latest earlier bench."""
    runs = sorted((d for d in bench_root.iterdir() if d.is_dir() and d != this
                   and (d / "scores.json").exists()),
                  key=lambda d: (d / "scores.json").stat().st_mtime) if bench_root.is_dir() else []
    if not runs:
        return {}
    data = json.loads((runs[-1] / "scores.json").read_text(encoding="utf-8"))
    return {"_id": runs[-1].name, **{(r["song"], r["truth"]): (r.get("edits") or {}).get("penalty")
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
                troot = truth_mod.load(song.truth_files, cache, cfg.get("musescore_cli"))
            except Exception as e:  # noqa: BLE001 - one song never stops the others
                problems.append(f"{song.id}: truth {song.truth.name}: {e}")
                LOG.error(problems[-1])
                continue
            tparts = {_norm(n): (n, p) for n, p in truth_mod.parts(troot)}
            for n in {_norm(n) for p in song.parts for n in p.plain} & tparts.keys():
                musicxml.strip_marks(tparts[n][1])     # `plain` rows: scored without marks
            t_bars = musicxml.measure_count(troot)
            manifest = json.loads((src_root / song.id / MANIFEST).read_text(encoding="utf-8")) \
                if (src_root / song.id / MANIFEST).exists() else {}
            used: set[str] = set()
            sys_words = edits.system_words(troot)
            unfinished = {_norm(n) for n in song.unfinished}
            used |= unfinished
            song_rows = []
            song_roots = []
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
                    oroots = []
                else:
                    oroots = [musicxml.load(f) for f in files]
                    song_roots += oroots
                named = _unique([(n, p, r) for r in oroots for n, p in truth_mod.parts(r)])
                outputs = [(n, p) for n, p, _ in named]
                owner = {n: r for n, _, r in named}
                mapping, unmapped, probs = resolve(part, outputs)
                problems += [f"{song.id}/{p}" for p in probs]
                for p in probs:
                    LOG.error(p)
                if unmapped:
                    LOG.warning(f"{part.name}: output parts not compared: {', '.join(unmapped)}")
                el = dict(outputs)
                for tname, onames in mapping.items():
                    if _norm(tname) in unfinished:
                        used.add(_norm(tname))
                        LOG.info(f"{part.name} -> {tname}: truth part marked unfinished, not scored")
                        continue
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
                           "split": len(files) > 1,      # piano reduction: Voices + Piano files
                           "bars_pred": max((len(el[o].findall("measure")) for o in onames), default=0),
                           "bars_truth": t_bars, "metrics": notef1.compare(pred, tru),
                           "wrong_bars": notef1.wrong_bars(pred, tru),
                           "run": (manifest.get(part.name) or {}).get("run")}
                    if full:
                        row["full"] = _full(out_dir / "parts" / song.id, tn, troot, tpart,
                                            [(owner[o], el[o]) for o in onames], cfg)
                    onodes = [el[o] for o in onames]
                    row["edits"] = edits.penalty(onodes, tpart, sys_words)
                    if row["edits"]["shift"]:
                        LOG.warning(f"{part.name} -> {tn}: output is {-row['edits']['shift']:+d} semitones off "
                                    "the truth as a whole (octave convention? workbook `transpose`)")
                    ps = [st for o in onodes for st in musicxml.part_staves(o)]
                    ts = musicxml.part_staves(tpart)
                    row["elements"] = elements.element_scores(ps, ts, elements.pair_staves(ps, ts))
                    song_rows.append(row)
            not_compared = [n for k, (n, p) in tparts.items()
                            if k not in used and notef1.notes(p)]
            summary = {"song": song.id, "title": song.title, "truth_file": "; ".join(f.name for f in song.truth_files),
                       "bars_truth": t_bars,
                       "metrics": {v: _sum(song_rows, v) for v in notef1.VARIANTS},
                       "system": edits.system_penalty(song_roots, troot),
                       "truth_parts_not_compared": not_compared}
            if not_compared:
                LOG.warning(f"truth parts with notes that no row names: {', '.join(not_compared)}")
            rows += song_rows
            songs_out.append(summary)

    prev = _previous(root / "bench", out_dir)
    data = {"show": proj.name, "source": str(src_root), "time": datetime.now().isoformat(timespec="seconds"),
            "previous": prev.get("_id"), "songs": songs_out, "rows": rows, "perf": perf, "problems": problems,
            "total": {v: _sum(rows, v) for v in notef1.VARIANTS}}
    for s in songs_out:
        s["edits"] = _sum_edits([r for r in rows if r["song"] == s["song"]], [s["system"]])
        s["elements"] = _sum_elements([r for r in rows if r["song"] == s["song"]])
    data["total"]["edits"] = _sum_edits(rows, [s["system"] for s in songs_out])
    data["total"]["elements"] = _sum_elements(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "scores.json.tmp"      # the sweep report reads it: never half-written
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out_dir / "scores.json")
    _csv(out_dir / "metrics.csv", rows)
    _trend(root / "bench" / "trend.csv", out_dir.name, data)
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


def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["song", "part", "outputs", "truth", "bars_pred", "bars_truth"]
                   + [f"{v}_{k}" for v in notef1.VARIANTS for k in ("f1", "precision", "recall")]
                   + ["omr_ned_all", "tedn", "run"] + list(_EDIT_SUMS) + ["shift", "edits_by_cat"]
                   + [f"el_{c}_f1" for c in musicxml.CATEGORIES])
        for r in rows:
            m, e = r["metrics"], r["edits"]
            w.writerow([r["song"], r["part"], "|".join(r["outputs"]), r["truth"], r["bars_pred"],
                        r["bars_truth"]]
                       + [m[v][k] for v in notef1.VARIANTS for k in ("f1", "precision", "recall")]
                       + [(r.get("full") or {}).get("omr_ned_all"), (r.get("full") or {}).get("tedn"),
                          r["run"]]
                       + [e[k] for k in _EDIT_SUMS] + [e["shift"], " ".join(f"{c}:{v}" for c, v in
                                                                        sorted(e["by_cat"].items()))]
                       + [r["elements"][c]["f1"] for c in musicxml.CATEGORIES])


def _report(data: dict, prev: dict) -> str:
    full = any("full" in r for r in data["rows"])
    delta = bool(prev.get("_id"))
    lines = [f"# Bench {data['show']} ({data['time']})", "",
             f"Outputs: `{data['source']}`" + (f"; Δ vs bench {prev['_id']}" if delta else ""), "",
             "Edit penalty = MuseScore actions to turn the output into the truth (notes, bars, every "
             "marking; lower is better; metrics/edits.py); left = penalty / typing it all in by hand; "
             "bars fix = bars to insert + delete + change; shift = whole part transposed (semitones).", "",
             "Note F1: notes = bar, staff, onset, sounding pitch, duration; pitch = without duration; "
             "pc = pitch class; rhythm = without pitch; aligned = notes with bars matched by best "
             "alignment instead of by index (reading quality without bar-count errors).", ""]
    hdr = ["song", "part", "truth", "bars", "penalty", "left", "bars fix", "shift",
           "notes F1", "P", "R", "pitch", "pc", "rhythm", "aligned"]
    hdr += ["OMR-NED", "TEDn"] if full else []
    hdr += ["Δ penalty"] if delta else []
    lines += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]

    def line(cells):
        lines.append("| " + " | ".join(cells) + " |")

    for s in data["songs"]:
        for r in (r for r in data["rows"] if r["song"] == s["song"]):
            m = r["metrics"]
            name = r["part"] + (f" ({', '.join(r['outputs'])})" if r["outputs"] else " (no output)")
            bars = f"{r['bars_pred']}/{r['bars_truth']}" + ("" if r["bars_pred"] == r["bars_truth"] else " ⚠")
            e = r["edits"]
            cells = [s["song"], name, r["truth"], bars, str(e["penalty"]), _pct(e["ratio"]), str(e["bars_to_fix"]),
                     f"{e['shift']:+d}" if e["shift"] else "", _f(m["notes"]["f1"]), _f(m["notes"]["precision"]),
                     _f(m["notes"]["recall"]), _f(m["pitch"]["f1"]), _f(m["pc"]["f1"]), _f(m["rhythm"]["f1"]),
                     _f(m["aligned"]["f1"])]
            if full:
                fr = r.get("full") or {}
                cells += [_f(fr.get("omr_ned_all")), _f(fr.get("tedn"))]
            if delta:
                old, new = prev.get((r["song"], r["truth"])), e["penalty"]
                cells.append("new" if old is None else f"{new - old:+d}")
            line(cells)
        m = s["metrics"]
        e = s["edits"]
        sysp = s["system"]["penalty"]
        cells = [f"**{s['song']}**", "**all**" + (f" (+{sysp} rehearsal/tempo/system text)" if sysp else ""), "", "",
                 f"**{e['penalty']}**", _pct(e["ratio"]), str(e["bars_to_fix"]), "",
                 f"**{_f(m['notes']['f1'])}**", _f(m["notes"]["precision"]),
                 _f(m["notes"]["recall"]), _f(m["pitch"]["f1"]), _f(m["pc"]["f1"]), _f(m["rhythm"]["f1"]),
                     _f(m["aligned"]["f1"])]
        cells += ["", ""] if full else []
        cells += [""] if delta else []
        line(cells)
    t = data["total"]
    e = t["edits"]
    lines += ["", f"**Total edit penalty {e['penalty']}** ({_pct(e['ratio'])} of typing it in: "
                  f"{e['from_scratch']}); bars to fix {e['bars_to_fix']} of {e['bars_truth']} "
                  f"(insert {e['bars_insert']}, delete {e['bars_delete']}, change {e['bars_changed']})"]
    lines += ["", f"**Total note F1 {_f(t['notes']['f1'])}** (P {_f(t['notes']['precision'])}, "
                  f"R {_f(t['notes']['recall'])}; {t['notes']['truth']} truth notes); "
                  f"bar-aligned {_f(t['aligned']['f1'])}", ""]
    cats = sorted(e["by_cat"].items(), key=lambda x: -x[1])
    lines += ["## Edit penalty by category", "", "| " + " | ".join(c for c, _ in cats) + " |",
              "|" + "---|" * len(cats), "| " + " | ".join(str(v) for _, v in cats) + " |", ""]
    el = t["elements"]
    cats = [c for c in musicxml.CATEGORIES if el[c]["pred"] or el[c]["gt"]]
    lines += ["## Element F1 (all parts)", "", "| category | output | truth | matched | P | R | F1 |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| {c} | {el[c]['pred']} | {el[c]['gt']} | {el[c]['tp']} | {_f(el[c]['precision'])} | "
              f"{_f(el[c]['recall'])} | {_f(el[c]['f1'])} |" for c in cats]
    lines.append("")
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
