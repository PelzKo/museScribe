"""Run every engine on every sample, then score in parallel.

Run directory layout::

    results/<run-id>/
      manifest.json               # config, host, engine versions, samples
      <engine>/<sample>/          # engine workdir: output.musicxml, engine.log, result.json
      scores.json                 # all metrics
      metrics.csv                 # flat table for spreadsheets
      report.md
"""
from __future__ import annotations

import csv
import json
import os
import platform
import socket
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import psutil

from . import config as config_mod
from . import dataset
from .engines import Engine, EngineResult
from .scoring import score


def host_info() -> dict:
    cpu = platform.processor()
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "wsl": "microsoft" in platform.release().lower(),
        "cpu": cpu,
        "cores_logical": psutil.cpu_count(),
        "cores_physical": psutil.cpu_count(logical=False),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "python": platform.python_version(),
        "gpus": [],
    }
    try:
        import pynvml

        pynvml.nvmlInit()
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            info["gpus"].append({"name": name.decode() if isinstance(name, bytes) else name,
                                 "mem_gb": round(pynvml.nvmlDeviceGetMemoryInfo(h).total / 2**30, 1)})
    except Exception:
        pass
    return info


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def run_engines(engines: list[Engine], samples: list[dataset.Sample], run_dir: Path,
                resume: bool) -> list[EngineResult]:
    results = []
    for eng in engines:
        for s in samples:
            wd = run_dir / eng.name / s.id
            rj = wd / "result.json"
            if resume and rj.exists():
                r = EngineResult.from_dict(json.loads(rj.read_text()))
                if r.error is None:
                    _log(f"{eng.name:>16} | {s.id}: cached")
                    results.append(r)
                    continue
            if eng.kind == "external" and eng.name not in s.external:
                continue
            _log(f"{eng.name:>16} | {s.id}: running ...")
            r = eng.run(s, wd)
            st = r.stats
            took = f"{st.wall_s:.1f}s, {st.peak_rss_mb:.0f} MB" if st else "external"
            _log(f"{eng.name:>16} | {s.id}: {'FAILED ' + r.error if r.error else 'ok'} ({took})")
            results.append(r)
    return results


def _score_job(r: dict, s: dataset.Sample, cfg: dict) -> tuple[str, str, dict, float]:
    t0 = time.perf_counter()
    out = score(EngineResult.from_dict(r), s, cfg)
    return r["engine"], r["sample"], out, time.perf_counter() - t0


def score_all(results: list[EngineResult], samples: list[dataset.Sample], cfg: dict,
              run_dir: Path) -> dict:
    by_id = {s.id: s for s in samples}
    path = run_dir / "scores.json"
    scores: dict = json.loads(path.read_text()) if path.exists() else {}
    jobs = int(cfg.get("scoring", {}).get("jobs", 4))
    todo = [r for r in results if r.sample in by_id]
    _log(f"scoring {len(todo)} outputs with {jobs} workers ...")
    with ProcessPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = [ex.submit(_score_job, r.to_dict(), by_id[r.sample], cfg) for r in todo]
        for f in as_completed(futs):
            eng, sid, out, took = f.result()
            out["scoring_s"] = took
            scores.setdefault(eng, {})[sid] = out
            errs = "; ".join(out.get("errors", {}).keys())
            _log(f"scored {eng} | {sid} in {took:.0f}s" + (f" (errors: {errs})" if errs else ""))
            path.write_text(json.dumps(scores, indent=1, default=str))
    return scores


def write_csv(scores: dict, results: list[EngineResult], path: Path) -> None:
    res = {(r.engine, r.sample): r for r in results}
    rows = []
    for eng, per in scores.items():
        for sid, sc in per.items():
            r = res.get((eng, sid))
            row = {"engine": eng, "sample": sid}
            for v, d in (sc.get("omr_ned") or {}).items():
                row[f"omr_ned_{v}"] = d.get("omr_ned")
            row["tedn"] = (sc.get("tedn") or {}).get("tedn")
            for cat, d in (sc.get("elements") or {}).items():
                row[f"f1_{cat}"] = d.get("f1")
            row["measure_error_rate"] = (sc.get("measures") or {}).get("measure_error_rate")
            for fs, d in (sc.get("flags") or {}).items():
                row[f"flag_{fs}_precision"] = d.get("precision")
                row[f"flag_{fs}_recall"] = d.get("recall")
            if r and r.stats:
                row.update({"wall_s": r.stats.wall_s, "cpu_s": r.stats.cpu_s,
                            "peak_rss_mb": r.stats.peak_rss_mb,
                            "peak_gpu_mem_mb": r.stats.peak_gpu_mem_mb})
            row["pages"] = r.pages if r else None
            row["error"] = r.error if r else None
            rows.append(row)
    keys = []
    for row in rows:
        keys += [k for k in row if k not in keys]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def load_results(run_dir: Path) -> list[EngineResult]:
    return [EngineResult.from_dict(json.loads(p.read_text()))
            for p in sorted(run_dir.glob("*/*/result.json"))]


def run(cfg: dict, *, engines_only=None, samples_only=None, run_id=None, resume=False,
        do_score=True) -> Path:
    samples, warnings = dataset.discover(Path(cfg["data_dir"]), samples_only, cfg.get("musescore_cli"))
    for w in warnings:
        _log("WARN " + w)
    if not samples:
        raise SystemExit(f"no samples in {cfg['data_dir']}")
    ext = {n for s in samples for n in s.external}
    engines = config_mod.engines(cfg, ext, engines_only)
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(cfg["results_dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    versions = {}
    usable = []
    for e in engines:
        ok, ver = e.check()
        versions[e.name] = {"type": e.kind, "available": ok, "version": ver, "config": e.cfg}
        _log(f"engine {e.name}: {'ok ' + ver if ok else 'UNAVAILABLE ' + ver}")
        if ok:
            usable.append(e)
    manifest = {"run_id": run_id, "started": datetime.now().isoformat(timespec="seconds"),
                "host": host_info(), "config": cfg, "engines": versions,
                "samples": [{"id": s.id, "pdf": str(s.pdf), "gt": str(s.gt), "meta": s.meta}
                            for s in samples],
                "warnings": warnings, "env": {"OMRBENCH_HOME": os.environ.get("OMRBENCH_HOME")}}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))

    results = run_engines(usable, samples, run_dir, resume)
    manifest["finished_engines"] = datetime.now().isoformat(timespec="seconds")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    if do_score:
        rescore(run_dir, cfg)
    return run_dir


def rescore(run_dir: Path, cfg: dict | None = None) -> None:
    from .report import write_report

    manifest = json.loads((run_dir / "manifest.json").read_text())
    cfg = cfg or manifest["config"]
    samples, _ = dataset.discover(Path(cfg["data_dir"]), None, cfg.get("musescore_cli"))
    results = load_results(run_dir)
    (run_dir / "scores.json").unlink(missing_ok=True)
    scores = score_all(results, samples, cfg, run_dir)
    write_csv(scores, results, run_dir / "metrics.csv")
    write_report(run_dir)
