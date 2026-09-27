"""TEDn (Hajič et al. 2016) via the OLiMPiC implementation.

Zhang-Shasha tree edit distance is O(n^2) in time and memory, which is fine for
one system (how OLiMPiC uses it) but not for a 3-page score. Parts are therefore
compared whole only if both trees are below `max_nodes`; otherwise measures are
first aligned (Levenshtein over measure content signatures) and TEDn is summed
over aligned measure pairs. Missing measures cost their gold cost, extra
measures cost one delete per node. Parts are paired by index.

TEDn = edit_cost / gold_cost (0 = perfect, can exceed 1 for very bad output).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import Levenshtein
from lxml import etree

from ._olimpic_tedn import TEDn


def _to_et(el) -> ET.Element:
    return ET.fromstring(etree.tostring(el))


def _count(el) -> int:
    return sum(1 for _ in el.iter())


def _gold_cost(el: ET.Element) -> int:
    return TEDn(ET.Element(el.tag), el).edit_cost


def _wrap(measures: list[ET.Element]) -> ET.Element:
    p = ET.Element("part")
    p.extend(measures)
    return p


def _sig(m: ET.Element) -> str:
    toks = []
    for n in m.iter("note"):
        if n.find("rest") is not None:
            toks.append("R" + (n.findtext("type") or ""))
        else:
            p = n.find("pitch")
            toks.append((p.findtext("step", "") + p.findtext("alter", "") + p.findtext("octave", "")
                         if p is not None else "~") + (n.findtext("type") or ""))
    return " ".join(sorted(toks))


def _measure_mode(pred: ET.Element, gold: ET.Element) -> tuple[int, int]:
    pm, gm = pred.findall("measure"), gold.findall("measure")
    edit = 0
    gold_total = sum(_gold_cost(_wrap([m])) for m in gm) + 1
    for op, i1, i2, j1, j2 in Levenshtein.opcodes([_sig(m) for m in pm], [_sig(m) for m in gm]):
        pa, ga = pm[i1:i2], gm[j1:j2]
        k = min(len(pa), len(ga))
        for a, b in zip(pa[:k], ga[:k]):
            edit += TEDn(_wrap([a]), _wrap([b])).edit_cost
        for a in pa[k:]:
            edit += _count(a)
        for b in ga[k:]:
            edit += _gold_cost(_wrap([b]))
    return edit, gold_total


def tedn(pred_root, gt_root, max_nodes: int = 2500) -> dict:
    pred_parts = [_to_et(p) for p in pred_root.findall("part")]
    gold_parts = [_to_et(p) for p in gt_root.findall("part")]
    edit = gold = 0
    modes = []
    for i, g in enumerate(gold_parts):
        if i >= len(pred_parts):
            gc = _gold_cost(g)
            edit += gc
            gold += gc
            modes.append("missing")
            continue
        p = pred_parts[i]
        if _count(p) <= max_nodes and _count(g) <= max_nodes:
            r = TEDn(p, g)
            edit += r.edit_cost
            gold += r.gold_cost
            modes.append("part")
        else:
            e, gc = _measure_mode(p, g)
            edit += e
            gold += gc
            modes.append("measure")
    for p in pred_parts[len(gold_parts):]:
        edit += _count(p)
        modes.append("extra")
    return {"tedn": edit / gold if gold else None, "edit_cost": edit, "gold_cost": gold,
            "mode": ",".join(modes)}
