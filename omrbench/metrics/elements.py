"""Per-element precision / recall / F1.

For every staff and category the prediction and ground truth are turned into
token sequences in musical order (e.g. notes "C#4:quarter.", dynamics "f",
lyrics "v1:ky"). True positives = longest common subsequence, so a dropped or
extra measure only costs its own content instead of shifting everything after it.

Staves are paired by index when both scores have the same number; otherwise
greedily by note-sequence similarity. Unpaired staves count fully as FN / FP.
"""
from __future__ import annotations

import Levenshtein

from ..musicxml import CATEGORIES, Staff


def lcs_len(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    # Levenshtein.ratio is the normalised Indel similarity: 1 - indel / (|a|+|b|),
    # and indel = |a| + |b| - 2 * LCS.
    return round(Levenshtein.ratio(a, b) * (len(a) + len(b)) / 2)


def pair_staves(pred: list[Staff], gt: list[Staff]) -> list[tuple[int | None, int | None]]:
    """Return (pred_idx, gt_idx) pairs covering every staff of both sides."""
    if len(pred) == len(gt):
        return [(i, i) for i in range(len(gt))]
    sims = []
    for i, p in enumerate(pred):
        ps = p.seq("notes")
        for j, g in enumerate(gt):
            gs = g.seq("notes")
            sims.append((Levenshtein.ratio(ps, gs) if ps or gs else 0.0, -abs(i - j), i, j))
    sims.sort(reverse=True)
    used_p, used_g, pairs = set(), set(), []
    for _, _, i, j in sims:
        if i not in used_p and j not in used_g:
            used_p.add(i)
            used_g.add(j)
            pairs.append((i, j))
    pairs += [(i, None) for i in range(len(pred)) if i not in used_p]
    pairs += [(None, j) for j in range(len(gt)) if j not in used_g]
    return sorted(pairs, key=lambda x: (x[1] if x[1] is not None else 999, x[0] or 0))


def prf(tp: int, n_pred: int, n_gt: int) -> dict:
    p = tp / n_pred if n_pred else None
    r = tp / n_gt if n_gt else None
    f = (2 * p * r / (p + r) if p and r else 0.0) if p is not None and r is not None else None
    return {"tp": tp, "pred": n_pred, "gt": n_gt, "precision": p, "recall": r, "f1": f}


def element_scores(pred: list[Staff], gt: list[Staff],
                   pairs: list[tuple[int | None, int | None]]) -> dict[str, dict]:
    out = {}
    for cat in CATEGORIES:
        tp = n_pred = n_gt = 0
        for i, j in pairs:
            ps = pred[i].seq(cat) if i is not None else []
            gs = gt[j].seq(cat) if j is not None else []
            tp += lcs_len(ps, gs)
            n_pred += len(ps)
            n_gt += len(gs)
        out[cat] = prf(tp, n_pred, n_gt)
    return out
