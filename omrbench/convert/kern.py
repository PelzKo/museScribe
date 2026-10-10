"""**kern / **bekern (Humdrum) -> MusicXML via music21.

shortcut: bekern beam/ligature markers are not stripped, parse failures raise instead of repairing;
          add a repair pass once SMT-fp output shows which tokens music21 rejects
"""
from __future__ import annotations

from pathlib import Path

from music21 import converter


def kern_to_musicxml(src: Path | str, out: Path) -> Path:
    """Parse a Humdrum file (path or text) and write it as MusicXML to `out`."""
    text = Path(src).read_text(encoding="utf-8") if isinstance(src, Path) else src
    score = converter.parseData(text, format="humdrum")
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out))
    return out
