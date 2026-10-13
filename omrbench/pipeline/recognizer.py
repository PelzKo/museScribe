"""Crop recognizers: read the staff-group crops of the pipeline (engine.py step 3).

A recognizer gets crop jobs `(system, group, staves, image)` and writes the MusicXML of
each image next to it; `output` finds that file. `recognize` returns (job, error or None)
per job, in order. `staves`: the staff-group sizes (of `Pipeline._crop_jobs`) it reads;
the other groups go to the `fallback` recognizer.

Recognizers: `homr` (any group); `zeus` (single staves and grand staves, a model for each);
the pianoform kern models on grand staves (2-staff groups): `smt-sys` (SMT system-level
grand-staff model), `transcoda`, `smt-fp` (page models, here on one system).

Config (bench.yaml): `recognizer: homr` (default) and `fallback: homr` in the pipeline
entry; a recognizer's own options under its name (`homr: {workers: auto, threads: 2}`).
"""
from __future__ import annotations

import time
from pathlib import Path

from .. import log as logmod
from ..engines.pagewise import Homr, SmtFp, SmtSys, Transcoda, Zeus
from ..monitor import RunStats, run_monitored


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


class HomrRecognizer:
    name = "homr"
    staves = None   # any group

    def __init__(self, pipeline_name: str, cfg: dict, bench: dict):
        self.engine = Homr(f"{pipeline_name}/homr", {**(cfg.get("homr") or {}), "type": "homr"}, bench)

    def check(self) -> tuple[bool, str]:
        return self.engine.check()

    def output(self, img: Path, crop_dir: Path) -> Path | None:
        return self.engine.find_output(img, crop_dir)

    def recognize(self, jobs: list, crop_dir: Path, log: Path, total: RunStats, timeout_s: float):
        """The persistent worker pool by default; one `homr` process per crop with
        `pool: false` or extra_args."""
        if not jobs:
            return []
        homr = self.engine
        if not homr.use_pool():
            out = []
            for job in jobs:
                img = job[3]
                st = run_monitored(homr.page_cmd(img, crop_dir), log_path=log, cwd=crop_dir,
                                   env=homr.env(), timeout_s=timeout_s)
                total.add(st)
                err = None
                if st.timed_out:
                    err = f"timeout after {timeout_s:.0f}s"
                elif homr.find_output(img, crop_dir) is None:
                    err = f"exit {st.exit_code}: {_last_error(log)}"
                out.append((job, err))
            return out
        pool = homr.pool()
        t0 = time.perf_counter()
        futs = [pool.submit(job[3], timeout_s) for job in jobs]
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


class BatchRecognizer:
    """A container engine run once per batch of crops (model loaded once). Default: a kern
    engine (engines/pagewise.KernPages) on grand staves; the kern is converted to
    `<crop>.musicxml` next to the crop."""
    staves = {2}

    def __init__(self, name: str, engine_cls, pipeline_name: str, cfg: dict, bench: dict):
        self.name = name
        self.engine = engine_cls(f"{pipeline_name}/{name}", {**(cfg.get(name) or {}), "type": name}, bench)

    def check(self) -> tuple[bool, str]:
        return self.engine.check()

    def output(self, img: Path, crop_dir: Path) -> Path | None:
        p = img.with_suffix(".musicxml")
        return p if p.exists() else None

    def commands(self, jobs: list, crop_dir: Path) -> list[tuple[list, list]]:
        """(jobs, command) per container call."""
        return [(jobs, self.engine.batch_cmd([j[3] for j in jobs], crop_dir))]

    def written(self, img: Path, crop_dir: Path) -> Path | None:
        """The MusicXML of a crop after its call (kern: converted now)."""
        return self.engine.find_output(img, crop_dir)

    def recognize(self, jobs: list, crop_dir: Path, log: Path, total: RunStats, timeout_s: float):
        done = {}
        for part, cmd in self.commands(jobs, crop_dir) if jobs else []:
            eng = self.engine
            st = eng.exec_cmd(cmd, crop_dir, log, env=eng.env(), cwd=crop_dir,
                              timeout_s=timeout_s * len(part))   # timeout_s is per crop
            total.add(st)
            for job in part:
                err = None
                if st.timed_out:
                    err = f"timeout after {timeout_s * len(part):.0f}s (batch)"
                elif self.written(job[3], crop_dir) is None:
                    err = f"exit {st.exit_code}: no MusicXML ({_last_error(log)})"
                done[job[:2]] = err
        return [(j, done[j[:2]]) for j in jobs]


class ZeusRecognizer(BatchRecognizer):
    """Zeus: the solo-staff model on single staves, the grand-staff model on 2-staff groups."""
    staves = {1, 2}

    def commands(self, jobs, crop_dir):
        return [(part, self.engine.staves_cmd(n, [j[3] for j in part]))
                for n in sorted({j[2] for j in jobs}) if (part := [j for j in jobs if j[2] == n])]

    def written(self, img, crop_dir):
        return self.output(img, crop_dir)


class WithFallback:
    """`main` on the staff groups it reads, `fallback` on the others."""

    def __init__(self, main, fallback):
        self.main, self.fallback = main, fallback
        self.name = f"{main.name}+{fallback.name}"

    def check(self) -> tuple[bool, str]:
        (ok_m, vm), (ok_f, vf) = self.main.check(), self.fallback.check()
        return ok_m and ok_f, f"{vm}; fallback {self.fallback.name} {vf}"

    def output(self, img: Path, crop_dir: Path) -> Path | None:
        return self.main.output(img, crop_dir) or self.fallback.output(img, crop_dir)

    def recognize(self, jobs: list, crop_dir: Path, log: Path, total: RunStats, timeout_s: float):
        mine = [j for j in jobs if j[2] in self.main.staves]
        rest = [j for j in jobs if j[2] not in self.main.staves]
        done = {j[:2]: r for j, r in self.main.recognize(mine, crop_dir, log, total, timeout_s)
                + self.fallback.recognize(rest, crop_dir, log, total, timeout_s)}
        return [(j, done[j[:2]]) for j in jobs]


BATCH = {"zeus": (ZeusRecognizer, Zeus), "smt-sys": (BatchRecognizer, SmtSys),
         "transcoda": (BatchRecognizer, Transcoda), "smt-fp": (BatchRecognizer, SmtFp)}
KNOWN = ["homr", *BATCH]


def _one(name: str, pipeline_name: str, cfg: dict, bench: dict):
    if name == "homr":
        return HomrRecognizer(pipeline_name, cfg, bench)
    if name in BATCH:
        cls, engine_cls = BATCH[name]
        return cls(name, engine_cls, pipeline_name, cfg, bench)
    raise ValueError(f"recognizer '{name}' (known: {', '.join(KNOWN)})")


def build(pipeline_name: str, cfg: dict, bench: dict):
    main = _one(cfg.get("recognizer", "homr"), pipeline_name, cfg, bench)
    if main.staves is None:
        return main
    return WithFallback(main, _one(cfg.get("fallback", "homr"), pipeline_name, cfg, bench))
