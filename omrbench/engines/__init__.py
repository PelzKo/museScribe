from .audiveris import Audiveris
from .base import Engine, EngineResult
from .external import External
from .pagewise import Homr, Oemer

KINDS: dict[str, type[Engine]] = {
    "audiveris": Audiveris,
    "homr": Homr,
    "oemer": Oemer,
    "external": External,
}


def build(name: str, cfg: dict, bench: dict) -> Engine:
    kind = cfg.get("type", name)
    if kind not in KINDS:
        raise ValueError(f"engine '{name}': unknown type '{kind}' (known: {list(KINDS)})")
    return KINDS[kind](name, cfg, bench)


__all__ = ["Engine", "EngineResult", "KINDS", "build"]
