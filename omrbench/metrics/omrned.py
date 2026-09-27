"""OMR-NED (Martinez-Sevilla et al. 2025) via musicdiff.

OMR-NED = symbolic edit distance / (symbols in GT + symbols in prediction),
0 = identical, 1 = nothing in common. musicdiff also returns the edit distance
split by symbol category, which the report shows per engine.
"""
from __future__ import annotations

from pathlib import Path

from musicdiff import DetailLevel
from musicdiff import _diff_omr_ned_metrics  # public API only prints; this returns the numbers


def detail_level(spec: str | int) -> int:
    if isinstance(spec, int):
        return spec
    val = 0
    for name in str(spec).split("|"):
        val |= int(getattr(DetailLevel, name.strip()))
    return val


def omr_ned(pred: Path, gt: Path, detail: str | int = "AllObjects") -> dict:
    m = _diff_omr_ned_metrics(Path(pred), Path(gt), detail_level(detail))
    if m is None:
        raise RuntimeError("musicdiff could not parse prediction or ground truth")
    return {
        "omr_ned": m.omr_ned,
        "edit_distance": m.omr_edit_distance,
        "gt_symbols": m.gt_numsyms,
        "pred_symbols": m.pred_numsyms,
        "by_category": {k: v for k, v in m.edit_distances_dict.items() if v},
    }
