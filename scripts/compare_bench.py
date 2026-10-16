"""Compare two benchmark states by edit penalty and apply the acceptance rule.

    python scripts/compare_bench.py BASE NEW

BASE / NEW: a bench id present for every show (`ref`), or a comma list of `show/id` (`ghost/m24-g20,
anastasia/m24-a4`). Rule (user, 2026-10-15): accepted only if the all-song total drops and no part
(song system items count as a part) gets worse by more than half of that drop.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "results"
SHOWS = ("anastasia", "ghost")


def load(spec: str) -> dict[tuple, int]:
    dirs = [s.split("/", 1) for s in spec.split(",")] if "/" in spec else [(sh, spec) for sh in SHOWS]
    out: dict[tuple, int] = {}
    for show, bid in dirs:
        d = json.loads((ROOT / show / "bench" / bid / "scores.json").read_text())
        for r in d["rows"]:
            if r.get("edits"):
                out[(show, r["song"], r["part"], r["truth"])] = r["edits"]["penalty"]
        for s in d["songs"]:
            if s.get("system"):
                out[(show, s["song"], "(system)", "")] = s["system"]["penalty"]
    return out


def compare(base: dict, new: dict) -> tuple[bool, list[str]]:
    keys = sorted(base.keys() | new.keys())
    lost = [k for k in keys if k not in new]
    tb, tn = sum(base.values()), sum(new.values())
    drop = tb - tn
    deltas = sorted(((new.get(k, 0) - base.get(k, 0), k) for k in keys), reverse=True)
    lines = [f"total {tb} -> {tn} ({-drop:+d}, {-drop / tb:+.1%})" if tb else f"total {tb} -> {tn}"]
    worst = deltas[0] if deltas else (0, None)
    ok = drop > 0 and worst[0] <= drop / 2 and not lost
    for d, k in [x for x in deltas if x[0]][:12] + [x for x in deltas if x[0] < 0][-12:]:
        lines.append(f"  {d:+5d}  {'/'.join(k[:3])}")
    if lost:
        lines.append(f"  missing in NEW: {lost}")
    lines.append(f"worst part {worst[0]:+d} {'/'.join(worst[1][:3]) if worst[1] else ''}, limit {drop / 2:.0f}: "
                 + ("PASS" if ok else "FAIL"))
    return ok, lines


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    ok, lines = compare(load(argv[0]), load(argv[1]))
    print("\n".join(dict.fromkeys(lines)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
