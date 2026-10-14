"""Sweep: every engine / pipeline variant on every truth song of one or more shows, then one
report that says what to use for what.

For each engine (bench.yaml names, plus `--grid` variants of a base engine) and show:
  omrbench transcribe <show> --engine E --run-id <sweep>-E   (only into the run folder; resumes)
  omrbench bench <show> --run <sweep>-E --bench-id <sweep>-E
then results/sweeps/<sweep>/report.md + parts.csv: engines ranked by edit penalty (the headline:
MuseScore actions to reach the truth), the best engine per workbook part and per category, and
runtime. A crashed engine is recorded and the sweep goes on.

Crash-safe: the plan (shows, engines, grid, songs, options) is saved in results/sweeps/<id>/sweep.json
and every finished (show, engine) in status.json. `omrbench sweep --id <id> --resume` reruns the
saved plan and skips what is finished; inside an unfinished engine, every PDF whose output is already
in the run folder is skipped too (outputs are written atomically). `--rebench` re-scores finished
engines without transcribing (after a metric change).

Grid: "recognizer=homr,clarity;ocr_engine=tesseract,doctr" on base `pipeline` makes the 4
variants pipeline+recognizer-homr+ocr_engine-tesseract, ... (values are YAML: true, 2, [a, b]).
With `--grid-reuse E` the grid variants are not transcribed: they are reassembled (assembly only,
minutes) from engine E's work dirs of the same sweep, which must hold everything the variants read
(E's `ensemble` readers' crops; OCR / OLA caches are filled on first use). Only for options the
assembly reads: ocr_engine, measure_vote, prefer, ensemble, ensemble_pick, ensemble_weights, repairs.
"""
from __future__ import annotations

import csv
import itertools
import json
import time
from pathlib import Path

import yaml

from . import log as logmod
from . import project as project_mod

LOG = logmod.get("sweep")


def grid_engines(cfg: dict, base: str, grid: str) -> list[str]:
    """Add the grid's variants of `base` to cfg["engines"]; return their names."""
    spec = (cfg.get("engines") or {}).get(base)
    if spec is None:
        raise SystemExit(f"--grid base engine '{base}' is not in bench.yaml")
    axes = []
    for part in filter(None, (p.strip() for p in grid.split(";"))):
        key, _, vals = part.partition("=")
        axes.append([(key.strip(), yaml.safe_load(v.strip())) for v in _split(vals)])
    names, seen = [], set()
    for combo in itertools.product(*axes):
        # without an ensemble its ensemble_* options change nothing: one variant, not one per pick mode
        eff = tuple((k, _slug(v)) for k, v in combo
                    if not (k.startswith("ensemble_") and not dict(combo).get("ensemble", True)))
        if eff in seen:
            continue
        seen.add(eff)
        name = base + "".join(f"+{k}-{_slug(v)}" for k, v in combo
                              if (k, _slug(v)) in eff)
        cfg["engines"][name] = {**spec, **dict(combo)}
        names.append(name)
    return names


def _split(vals: str) -> list[str]:
    """Split on commas outside [...] ("a,[b, c]" -> ["a", "[b, c]"])."""
    out, depth, cur = [], 0, ""
    for ch in vals:
        depth += (ch == "[") - (ch == "]")
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return [v for v in out + [cur] if v.strip()]


def _slug(v) -> str:
    return "_".join(map(str, v)) if isinstance(v, list) else str(v).lower()


def _truth_songs(cfg: dict, show: str, songs: list[str] | None) -> list[str]:
    folder = project_mod.find(Path(cfg["data_dir"]), show)
    if folder is None:
        raise SystemExit(f"no show '{show}'")
    proj = project_mod.load(folder)
    return [s.id for s in proj.songs.values() if s.truth and (not songs or s.id in songs)]


def plan_file(cfg: dict, sweep_id: str) -> Path:
    return Path(cfg["results_dir"]) / "sweeps" / sweep_id / "sweep.json"


def save_plan(cfg: dict, sweep_id: str, plan: dict) -> None:
    f = plan_file(cfg, sweep_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(plan, indent=1))


def load_plan(cfg: dict, sweep_id: str) -> dict:
    """The saved plan; its grid variants are added to cfg["engines"] again."""
    f = plan_file(cfg, sweep_id)
    if not f.exists():
        raise SystemExit(f"no sweep '{sweep_id}' to resume ({f} missing)")
    plan = json.loads(f.read_text())
    for g in plan.get("grids") or []:
        grid_engines(cfg, g["base"], g["grid"])
    unknown = [e for e in plan["engines"] if e not in (cfg.get("engines") or {})]
    if unknown:
        raise SystemExit(f"sweep '{sweep_id}': engines no longer in bench.yaml: {', '.join(unknown)}")
    return plan


def _docker_up() -> bool:
    from .containers import docker_ok
    try:
        return docker_ok()[0]
    except OSError:          # no docker binary (Docker Desktop's WSL integration off)
        return False


def _need_docker() -> None:
    if not _docker_up():
        raise SystemExit("Docker is not available (start Docker Desktop / its WSL integration), then "
                         "continue with: omrbench sweep --id <id> --resume")


def sweep(cfg: dict, shows: list[str], engines: list[str], *, sweep_id: str, songs=None,
          full: bool = False, jobs=None, force: bool = False, resume: bool = False,
          rebench: bool = False, reuse: dict | None = None) -> Path:
    """reuse: {variant: base engine} = reassemble the variant from the base's work dirs."""
    from .bench import bench
    from .transcribe import reassemble_run, transcribe

    out = Path(cfg["results_dir"]) / "sweeps" / sweep_id
    out.mkdir(parents=True, exist_ok=True)
    status_f = out / "status.json"
    status = json.loads(status_f.read_text()) if status_f.exists() else {}
    if songs:
        found = {i for show in shows for i in _truth_songs(cfg, show, songs)}
        if missing := [s for s in songs if s not in found]:
            LOG.warning(f"--songs {', '.join(missing)}: no song with a truth file in {', '.join(shows)} "
                        "(song ids are case-sensitive: 4A, 1a)")
    for engine in engines:
        for show in shows:
            sel = _truth_songs(cfg, show, songs)
            if not sel:
                continue
            run_id = f"{sweep_id}-{engine}"
            key = f"{show}/{engine}"
            done = (status.get(key) or {}).get("ok")
            if done and resume and not rebench and status[key].get("failed_pdfs"):
                LOG.info(f"=== {key}: {status[key]['failed_pdfs']} PDF(s) failed earlier, retried")
                done = False
            if done and not rebench and (resume or not force):
                LOG.info(f"=== {key}: finished earlier, skipped")
                continue
            if rebench and not done:
                continue
            t0 = time.time()
            try:
                failed = status.get(key, {}).get("failed_pdfs", 0)
                base = (reuse or {}).get(engine)
                if base and not rebench:
                    if not (status.get(f"{show}/{base}") or {}).get("ok"):
                        raise RuntimeError(f"base engine {base} has not finished")
                    LOG.info(f"=== {key}: reassemble from {base}")
                    failed = reassemble_run(cfg, show, sel, src_run=f"{sweep_id}-{base}", work_engine=base,
                                            dst_run=run_id, engine=engine, force=force)
                elif not rebench:
                    _need_docker()
                    LOG.info(f"=== {key}: transcribe {', '.join(sel)}")
                    failed = transcribe(cfg, project=show, songs=sel, engine=engine, run_id=run_id,
                                        jobs=jobs, force=force, latest=False)
                LOG.info(f"=== {key}: bench")
                bench(cfg, show, songs=sel, run=run_id, full=full, bench_id=run_id)
                s_ = status.get(key, {}).get("s", 0) if rebench else round(time.time() - t0)
                status[key] = {"ok": True, "failed_pdfs": failed, "s": s_}
            except (Exception, SystemExit) as e:  # noqa: BLE001 - one engine never stops the sweep
                if not rebench and not _docker_up():
                    # Docker died (or never ran): not the engine's fault; stop, resume later
                    LOG.error(f"{key}: {type(e).__name__}: {e}")
                    raise SystemExit("Docker is not available; start it, then: "
                                     f"omrbench sweep --id {sweep_id} --resume") from e
                LOG.error(f"{key}: {type(e).__name__}: {e}")
                status[key] = {"ok": False, "error": f"{type(e).__name__}: {e}", "s": round(time.time() - t0)}
            tmp = status_f.with_suffix(".tmp")
            tmp.write_text(json.dumps(status, indent=1))
            tmp.replace(status_f)
    report(cfg, shows, engines, sweep_id)
    return out


# --------------------------------------------------------------------------- report

def _load(cfg: dict, shows: list[str], engines: list[str], sweep_id: str) -> dict:
    """{engine: {show: scores.json}} of the benches that exist."""
    res = Path(cfg["results_dir"])
    out: dict = {}
    for e in engines:
        for show in shows:
            f = res / show / "bench" / f"{sweep_id}-{e}" / "scores.json"
            if f.exists():
                out.setdefault(e, {})[show] = json.loads(f.read_text(encoding="utf-8"))
    return out


def _engines_of(cfg: dict, shows: list[str], sweep_id: str) -> list[str]:
    res = Path(cfg["results_dir"])
    found = set()
    for show in shows:
        for d in (res / show / "bench").glob(f"{sweep_id}-*"):
            if (d / "scores.json").exists():
                found.add(d.name[len(sweep_id) + 1:])
    return sorted(found)


def report(cfg: dict, shows: list[str], engines: list[str] | None, sweep_id: str) -> Path:
    engines = engines or _engines_of(cfg, shows, sweep_id)
    out = Path(cfg["results_dir"]) / "sweeps" / sweep_id
    out.mkdir(parents=True, exist_ok=True)
    status = json.loads((out / "status.json").read_text()) if (out / "status.json").exists() else {}
    # a failed (re)bench leaves an older scores.json behind: not ranked, its error is listed
    data = {e: d for e, by_show in _load(cfg, shows, engines, sweep_id).items()
            if (d := {sh: x for sh, x in by_show.items() if (status.get(f"{sh}/{e}") or {"ok": True}).get("ok")})}
    # parts every engine was scored on, so totals compare like with like
    keys = {}
    for e, by_show in data.items():
        # page engines can't write a piano reduction's Voices / Piano files: those rows leave the
        # ranking (user decision 2026-10-14), for every engine via `common`
        page = (cfg.get("engines", {}).get(e) or {}).get("type") != "pipeline"
        keys[e] = {(sh, r["song"], r["part"], r["truth"]): r for sh, d in by_show.items() for r in d["rows"]
                   if not (page and r.get("split"))}
    complete = [e for e in engines if e in keys]
    common = set.intersection(*(set(keys[e]) for e in complete)) if complete else set()

    def tot(e, field):
        return sum(keys[e][k]["edits"][field] for k in common)

    songs = {(k[0], k[1]) for k in common}

    def systems(e):
        return [s["system"] for sh in shows if sh in data[e] for s in data[e][sh]["songs"] if (sh, s["song"]) in songs]

    def sys_pen(e):
        return sum(s["penalty"] for s in systems(e))

    def wall(e):
        return sum(p.get("wall_s") or 0 for d in data[e].values() for p in d.get("perf") or [])

    def f1(e, variant):
        tp = sum(keys[e][k]["metrics"][variant]["tp"] for k in common)
        n = sum(keys[e][k]["metrics"][variant]["pred"] + keys[e][k]["metrics"][variant]["truth"] for k in common)
        return 2 * tp / n if n else None

    def ned(e):
        # mean OMR-NED over the common parts (bench --full); None without it
        v = [x for k in common if (x := (keys[e][k].get("full") or {}).get("omr_ned_all")) is not None]
        return sum(v) / len(v) if v else None

    show_ned = any(ned(e) is not None for e in complete)
    rank = sorted(complete, key=lambda e: tot(e, "penalty") + sys_pen(e))
    scratch = (sum(keys[rank[0]][k]["edits"]["from_scratch"] for k in common)
               + sum(s["from_scratch"] for s in systems(rank[0]))) if rank else 0
    lines = [f"# Sweep {sweep_id}", "",
             f"Shows: {', '.join(shows)}; {len(common)} truth parts scored by all {len(complete)} engines "
             "(totals use only those). Penalty = MuseScore actions to turn the output into the truth "
             "(lower is better; `omrbench/metrics/edits.py`); system = rehearsal marks / tempi / system "
             f"text once per song. Typing every part in from scratch: {scratch} actions.", "",
             "## Ranking", "",
             "| # | engine | penalty | parts | system | left | bars to fix | notes F1 | aligned | "
             + ("OMR-NED | " if show_ned else "") + "time s |",
             "|---" * (11 if show_ned else 10) + "|"]
    for i, e in enumerate(rank, 1):
        p, sp = tot(e, "penalty"), sys_pen(e)
        lines.append(f"| {i} | {e} | **{p + sp}** | {p} | {sp} | {_pct((p + sp) / scratch if scratch else None)} | "
                     f"{tot(e, 'bars_to_fix')} | {_f(f1(e, 'notes'))} | {_f(f1(e, 'aligned'))} | "
                     + (f"{_f(ned(e))} | " if show_ned else "") + f"{wall(e):.0f} |")
    bad = {k: v for k, v in status.items() if not v.get("ok") and k.split("/", 1)[1] not in keys}
    missing = [e for e in engines if e not in keys]
    if bad or missing:
        lines += ["", "Not ranked: " + "; ".join([f"{k}: {v['error']}" for k, v in bad.items()]
                                                 + [f"{e}: no bench" for e in missing if not any(
                                                     k.endswith('/' + e) for k in bad)])]

    # best engine per workbook part (show / part row), summed over songs
    groups: dict[tuple, dict[str, int]] = {}
    for e in complete:
        for (sh, song, part, tr), r in keys[e].items():
            if (sh, song, part, tr) in common:
                g = groups.setdefault((sh, part), {})
                g[e] = g.get(e, 0) + r["edits"]["penalty"]
    if rank:
        ref = rank[0]
        lines += ["", "## Best engine per part", "",
                  f"Penalty summed over the songs; Δ = best minus the overall winner ({ref}). Routing every "
                  "part to its best engine would save the sum of the Δ column.", "",
                  "| show | part | best | penalty | runner-up | " + ref + " | Δ |", "|---|---|---|---|---|---|---|"]
        saved = 0
        for (sh, part), g in sorted(groups.items()):
            order = sorted(g, key=lambda e: (g[e], rank.index(e)))
            best, second = order[0], (order[1] if len(order) > 1 else None)
            d = g[best] - g[ref]
            saved -= d
            lines.append(f"| {sh} | {part} | {best} | {g[best]} | "
                         f"{f'{second} ({g[second]})' if second else '-'} | {g[ref]} | {d:+d} |")
        ref_pen = tot(ref, 'penalty') + sys_pen(ref)
        lines += ["", f"Routing per part would save {saved} actions "
                      f"({_pct(saved / ref_pen if ref_pen else None)} of {ref}'s penalty)."]

        # per category
        cats: dict[str, dict[str, int]] = {}
        for e in complete:
            for k in common:
                for c, v in keys[e][k]["edits"]["by_cat"].items():
                    cats.setdefault(c, {}).setdefault(e, 0)
                    cats[c][e] += v
            for s in systems(e):
                for c, v in s["by_cat"].items():
                    cats.setdefault(c, {}).setdefault(e, 0)
                    cats[c][e] += v
        lines += ["", "## Penalty by category", "",
                  "Where the actions go (top 5 engines); best per category in bold.", ""]
        top = rank[:5]
        lines += ["| category | " + " | ".join(top) + " | best of all |", "|---" * (len(top) + 2) + "|"]
        for c in sorted(cats, key=lambda c: -cats[c].get(ref, 0)):
            vals = {e: cats[c].get(e, 0) for e in complete}
            lo = min(vals.values())
            best = min(vals, key=lambda e: (vals[e], rank.index(e)))
            lines.append(f"| {c} | " + " | ".join(f"**{vals[e]}**" if vals[e] == lo else str(vals[e]) for e in top)
                         + f" | {best} ({vals[best]}) |")

    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (out / "parts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["engine", "show", "song", "part", "truth", "penalty", "from_scratch", "bars_to_fix",
                    "shift", "notes_f1", "aligned_f1", "by_cat"])
        for e in complete:
            for (sh, song, part, tr), r in sorted(keys[e].items()):
                ed = r["edits"]
                w.writerow([e, sh, song, part, tr, ed["penalty"], ed["from_scratch"], ed["bars_to_fix"],
                            ed["shift"], r["metrics"]["notes"]["f1"], r["metrics"]["aligned"]["f1"],
                            " ".join(f"{c}:{v}" for c, v in sorted(ed["by_cat"].items()))])
    LOG.info(f"sweep report: {out / 'report.md'}")
    print("\n".join(lines))
    return out / "report.md"


def _f(x) -> str:
    return "-" if x is None else f"{x:.3f}"


def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"
