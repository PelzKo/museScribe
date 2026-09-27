from __future__ import annotations

import os
from pathlib import Path

import yaml

from .engines import Engine, build

DEFAULTS = {
    "home": "~/.local/share/omrbench",
    "data_dir": "data",
    "results_dir": "results",
    "dpi": 300,
    "device": "cpu",
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
    for k in ("data_dir", "results_dir"):
        p = Path(cfg[k]).expanduser()
        cfg[k] = str(p if p.is_absolute() else base / p)
    return cfg


def engines(cfg: dict, external_names: set[str], only: list[str] | None = None) -> list[Engine]:
    specs = dict(cfg.get("engines") or {})
    for name in sorted(external_names):
        specs.setdefault(name, {"type": "external"})
    out = []
    for name, spec in specs.items():
        spec = spec or {}
        if only and name not in only:
            continue
        if not only and spec.get("enabled", True) is False:
            continue
        out.append(build(name, spec, cfg))
    return out
