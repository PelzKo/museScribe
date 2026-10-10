from .audiveris import Audiveris
from .base import Engine, EngineResult
from .clarity import Clarity
from .pagewise import Homr, Oemer, Transcoda

KINDS: dict[str, type[Engine]] = {
    "audiveris": Audiveris,
    "homr": Homr,
    "oemer": Oemer,
    "clarity": Clarity,
    "transcoda": Transcoda,
}


def build(name: str, cfg: dict, bench: dict) -> Engine:
    if "pipeline" not in KINDS:
        from ..pipeline.engine import Pipeline  # imports engines itself: register lazily
        KINDS["pipeline"] = Pipeline
    kind = cfg.get("type", name)
    if kind not in KINDS:
        raise ValueError(f"engine '{name}': unknown type '{kind}' (known: {list(KINDS)})")
    return KINDS[kind](name, cfg, bench)


__all__ = ["Engine", "EngineResult", "KINDS", "build"]
