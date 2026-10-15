"""Drum legend (drumkit.yaml, derived from the truths by scripts/derive_drumkit.py) applied to drum parts.

Every unpitched note gets the kit instrument of its staff position (MuseScore then plays and shows it as
that drum) and the legend's notehead; a position the kit doesn't use is snapped to a kit position one
staff step away (a misread line / space), else left as read.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from lxml import etree

KIT_FILE = Path(__file__).resolve().parents[2] / "drumkit.yaml"
STEPS = "CDEFGAB"
MIN_POSITIONS = 3          # a drum set, not a one-line percussion part


def kit_for(show: str | None, path: Path = KIT_FILE) -> dict | None:
    """The show's largest kit {position: {notehead, instrument, midi}} (None: no drum-set truth yet)."""
    if not show or not path.exists():
        return None
    kits = ((yaml.safe_load(path.read_text()) or {}).get(show) or {}).get("kits") or {}
    best = max(kits.values(), key=lambda k: len(k["positions"]), default=None)
    return best["positions"] if best and len(best["positions"]) >= MIN_POSITIONS else None


def _step(pos: str) -> int:
    return STEPS.index(pos[0]) + 7 * int(pos[1:])


def _pos(step: int) -> str:
    return f"{STEPS[step % 7]}{step // 7}"


def _insert_after(note: etree._Element, el: etree._Element, after: tuple[str, ...]) -> None:
    last = max((i for i, c in enumerate(note) if c.tag in after), default=-1)
    note.insert(last + 1, el)


def apply(score: etree._Element, kit: dict) -> int:
    """Map the unpitched notes of every all-unpitched part through `kit`; returns the notes snapped."""
    ids = {pos: f"I{n}" for n, pos in enumerate(kit, start=1)}
    snapped = 0
    for part in score.findall("part"):
        notes = [n for n in part.iter("note") if n.find("rest") is None]
        if not notes or any(n.find("unpitched") is None for n in notes):
            continue
        pid = part.get("id")
        sp = score.find(f"part-list/score-part[@id='{pid}']")
        for pos, e in kit.items():
            si = etree.SubElement(sp, "score-instrument", id=f"{pid}-{ids[pos]}")
            etree.SubElement(si, "instrument-name").text = e["instrument"]
        for pos, e in kit.items():
            mi = etree.SubElement(sp, "midi-instrument", id=f"{pid}-{ids[pos]}")
            etree.SubElement(mi, "midi-channel").text = "10"
            etree.SubElement(mi, "midi-unpitched").text = str(e["midi"])
        for n in notes:
            u = n.find("unpitched")
            pos = f"{u.findtext('display-step', 'C')}{u.findtext('display-octave', '4')}"
            if pos not in kit:
                near = [p for p in kit if abs(_step(p) - _step(pos)) == 1]
                if len(near) != 1:
                    continue
                pos = near[0]
                u.find("display-step").text, u.find("display-octave").text = pos[0], pos[1:]
                snapped += 1
            for old in n.findall("instrument") + n.findall("notehead"):
                n.remove(old)
            _insert_after(n, etree.Element("instrument", id=f"{pid}-{ids[pos]}"), ("duration", "tie"))
            if kit[pos]["notehead"] != "normal":
                head = etree.Element("notehead")
                head.text = kit[pos]["notehead"]
                _insert_after(n, head, ("instrument", "voice", "type", "dot", "accidental",
                                        "time-modification", "stem"))
    return snapped
