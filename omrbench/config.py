from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import yaml

from .engines import Engine, build

LOG = logging.getLogger("omrbench")

DEFAULTS = {
    "home": "~/.local/share/omrbench",
    "data_dir": "data",
    "samples_dir": "data/samples",
    "results_dir": "results",
    "dpi": 300,
    "device": "auto",
    "timeout_s": 1800,
    "engines": {},
    "scoring": {},
}


def load(path: Path | None) -> dict:
    cfg = dict(DEFAULTS)
    base = Path.cwd()
    if path and Path(path).exists():
        cfg.update(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})
        base = Path(path).resolve().parent
    if os.environ.get("OMRBENCH_HOME"):
        cfg["home"] = os.environ["OMRBENCH_HOME"]
    cfg["home"] = str(Path(cfg["home"]).expanduser())
    for k in ("data_dir", "samples_dir", "results_dir"):
        p = Path(cfg[k]).expanduser()
        cfg[k] = str(p if p.is_absolute() else base / p)
    if cfg["device"] == "auto":
        cfg["device"] = "cuda" if has_gpu() else "cpu"
    return cfg


def has_gpu() -> bool:
    # shortcut: host nvidia-smi, not `docker run --gpus` (slow); add the docker probe if they ever disagree
    try:
        return subprocess.run(["nvidia-smi", "-L"], capture_output=True).returncode == 0
    except OSError:  # missing, or a non-executable one on PATH (Windows PATH under WSL)
        return False


def engines(cfg: dict, only: list[str] | None = None) -> list[Engine]:
    specs = dict(cfg.get("engines") or {})
    out = []
    for name, spec in specs.items():
        spec = spec or {}
        if only and name not in only:
            continue
        if not only and spec.get("enabled", True) is False:
            continue
        if spec.get("requires_gpu") and cfg["device"] != "cuda":
            LOG.warning(f"engine {name} skipped: requires_gpu and device is {cfg['device']}")
            continue
        out.append(build(name, spec, cfg))
    return out
