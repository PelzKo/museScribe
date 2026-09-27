"""Uncertainty flags and how well they predict real errors.

Flag sources (unit = one measure of one part):
  * validator  - engine-agnostic: voice durations vs. time signature
                 (short first/last bars and implicit bars are allowed)
  * audiveris  - `abnormal` measures and stacks with `excess` duration from the
                 saved .omr project

Ground-truth errors (unit = one measure of one staff): per paired staff, measure
content signatures of prediction and GT are aligned; prediction measures outside
exactly-matching blocks are erroneous. A part flag covers all its staves.
"""
from __future__ import annotations

import re
import zipfile
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import Levenshtein

from ..musicxml import Staff
from .elements import prf


def validator_flags(root) -> dict[tuple[int, int], str]:
    flags: dict[tuple[int, int], str] = {}
    for pi, part in enumerate(root.findall("part")):
        divisions = Fraction(1)
        expected: Fraction | None = None
        measures = part.findall("measure")
        for mi, m in enumerate(measures):
            for a in m.findall("attributes"):
                d = a.findtext("divisions")
                if d:
                    divisions = Fraction(d.strip())
                t = a.find("time")
                if t is not None and t.findtext("beats") and t.findtext("beat-type"):
                    try:
                        beats = sum(Fraction(x) for x in t.findtext("beats").split("+"))
                        expected = beats * 4 / Fraction(t.findtext("beat-type").strip())
                    except (ValueError, ZeroDivisionError):
                        expected = None
            if expected is None or m.get("implicit") == "yes":
                continue
            per_voice: dict[str, Fraction] = {}
            for n in m.findall("note"):
                if n.find("chord") is not None or n.find("grace") is not None:
                    continue
                if n.find("rest") is not None and n.find("rest").get("measure") == "yes":
                    per_voice.setdefault(n.findtext("voice", "1"), expected)
                    continue
                v = (n.findtext("voice") or "1").strip()
                per_voice[v] = per_voice.get(v, Fraction(0)) + Fraction(
                    (n.findtext("duration") or "0").strip()) / divisions
            edge = mi in (0, len(measures) - 1)
            bad = [f"v{v}={d}" for v, d in per_voice.items()
                   if d > expected or (d < expected and not edge)]
            if bad:
                flags[(pi, mi)] = f"duration {', '.join(bad)} != {expected}"
    return flags


def audiveris_flags(omr: Path) -> dict[tuple[int, int], str]:
    """Map .omr abnormal measures / excess stacks to (part, global measure index)."""
    flags: dict[tuple[int, int], str] = {}
    with zipfile.ZipFile(omr) as z:
        sheets = sorted((n for n in z.namelist() if re.fullmatch(r"sheet#\d+/sheet#\d+\.xml", n)),
                        key=lambda n: int(re.search(r"#(\d+)/", n).group(1)))
        offset = 0
        for n in sheets:
            root = ET.fromstring(z.read(n))
            for page in root.iter("page"):
                count = int(page.get("measure-count") or 0)
                n_parts = 0
                for sys_ in page.findall("system"):
                    parts = sys_.findall("part")
                    n_parts = max(n_parts, len(parts))
                    for pi, p in enumerate(parts):
                        for m in p.findall("measure"):
                            if m.get("abnormal") == "true":
                                flags[(pi, offset + int(m.get("id")) - 1)] = "audiveris abnormal"
                    for s in sys_.iter("stack"):
                        if s.get("excess"):
                            for pi in range(len(parts)):
                                flags.setdefault((pi, offset + int(s.get("id")) - 1),
                                                 f"audiveris excess {s.get('excess')}")
                offset += count
    return flags


def measure_errors(pred: list[Staff], gt: list[Staff],
                   pairs: list[tuple[int | None, int | None]]) -> tuple[set, int, int, int]:
    """Return (erroneous pred units, total pred units, matched gt units, total gt units)."""
    wrong, total_pred, ok_gt, total_gt = set(), 0, 0, 0
    for i, j in pairs:
        ps = pred[i].measure_signatures() if i is not None else []
        gs = gt[j].measure_signatures() if j is not None else []
        total_pred += len(ps)
        total_gt += len(gs)
        good = set()
        for op, i1, i2, j1, j2 in Levenshtein.opcodes(ps, gs):
            if op == "equal":
                good.update(range(i1, i2))
                ok_gt += j2 - j1
        wrong.update((i, k) for k in range(len(ps)) if k not in good)
    return wrong, total_pred, ok_gt, total_gt


def flag_scores(flags: dict[tuple[int, int], str], pred: list[Staff], wrong: set) -> dict:
    """Expand part flags to staves and score them against erroneous measures."""
    by_part: dict[int, list[int]] = {}
    for si, s in enumerate(pred):
        by_part.setdefault(s.part_index, []).append(si)
    flagged = {(si, mi) for (pi, mi) in flags for si in by_part.get(pi, [])}
    n_units = sum(s.n_measures for s in pred)
    tp = len(flagged & wrong)
    res = prf(tp, len(flagged), len(wrong))
    res["flag_rate"] = len(flagged) / n_units if n_units else None
    return res
