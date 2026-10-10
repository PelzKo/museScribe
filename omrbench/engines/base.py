from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import log as logmod
from ..dataset import Sample
from ..monitor import RunStats

LOG = logmod.get("engine")


@dataclass
class EngineResult:
    engine: str
    sample: str
    output: Path | None = None           # merged MusicXML for the whole sample
    stats: RunStats | None = None        # None when the engine failed before running
    prep_s: float = 0.0                  # rasterisation etc., not in stats
    pages: int = 0
    error: str | None = None
    extras: dict = field(default_factory=dict)   # engine-specific (e.g. .omr path)

    def to_dict(self) -> dict:
        return {
            "engine": self.engine, "sample": self.sample,
            "output": str(self.output) if self.output else None,
            "stats": self.stats.to_dict() if self.stats else None,
            "prep_s": self.prep_s, "pages": self.pages, "error": self.error,
            "extras": {k: str(v) for k, v in self.extras.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EngineResult":
        st = d.get("stats")
        stats = None
        if st:
            st = {k: v for k, v in st.items() if k != "cpu_s"}
            stats = RunStats(**st)
        return cls(d["engine"], d["sample"], Path(d["output"]) if d.get("output") else None,
                   stats, d.get("prep_s", 0.0), d.get("pages", 0), d.get("error"),
                   {k: Path(v) for k, v in (d.get("extras") or {}).items()})


class Engine:
    kind = "base"
    runs_locally = True

    def __init__(self, name: str, cfg: dict, bench: dict):
        self.name = name
        self.cfg = cfg
        self.bench = bench
        self.home = Path(bench["home"]).expanduser()
        self.timeout_s = float(cfg.get("timeout_s", bench.get("timeout_s", 1800)))

    # -- to override -------------------------------------------------------
    def check(self) -> tuple[bool, str]:
        """(available, version-or-reason)."""
        raise NotImplementedError

    def _run(self, sample: Sample, workdir: Path, result: EngineResult) -> None:
        raise NotImplementedError

    # -- common ------------------------------------------------------------
    def env(self) -> dict:
        env = {}
        if self.bench.get("device", "cpu") == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = ""
        env.update({str(k): str(v) for k, v in (self.cfg.get("env") or {}).items()})
        return env

    def run(self, sample: Sample, workdir: Path) -> EngineResult:
        workdir.mkdir(parents=True, exist_ok=True)
        res = EngineResult(self.name, sample.id)
        crashed = False
        try:
            self._run(sample, workdir, res)
        except Exception as e:  # engine failures are results, not crashes
            res.error = f"{type(e).__name__}: {e}"
            LOG.error(f"{self.name} crashed: {res.error} (work dir {workdir})", exc_info=True)
            crashed = True
        if res.output is None and res.error is None:
            res.error = "engine produced no MusicXML"
        if res.stats and res.stats.timed_out and not res.error:
            res.error = f"timeout after {self.timeout_s:.0f}s"
        if res.error and not crashed:
            LOG.error(f"{self.name} failed: {res.error} (work dir {workdir})")
        elif res.extras.get("warning"):
            LOG.debug(f"{self.name}: {res.extras['warning']}")
        res.extras.setdefault("log", workdir / "engine.log")
        (workdir / "result.json").write_text(json.dumps(res.to_dict(), indent=2))
        return res
