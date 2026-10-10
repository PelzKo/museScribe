"""**kern / **bekern (Humdrum) -> MusicXML via music21.

Model output is often a bare spine body (Transcoda's canonical form): the `**kern` header and the
`*-` terminator are added when missing.

shortcut: bekern beam/ligature markers are not stripped, other parse failures raise instead of repairing;
          extend complete() once SMT-fp output shows which tokens music21 rejects
"""
from __future__ import annotations

from pathlib import Path

from music21 import converter


def complete(text: str) -> str:
    """Add the exclusive-interpretation header and spine terminators if the body lacks them."""
    lines = [ln for ln in text.strip("\n").split("\n") if ln.strip()]
    data = [ln for ln in lines if not ln.startswith("!!")]
    if not data:
        return text
    if not data[0].startswith("**"):
        lines.insert(lines.index(data[0]), "\t".join(["**kern"] * len(data[0].split("\t"))))
    if not all(c == "*-" for c in data[-1].split("\t")):
        lines.append("\t".join(["*-"] * len(data[-1].split("\t"))))
    return "\n".join(lines) + "\n"


def kern_to_musicxml(src: Path | str, out: Path) -> Path:
    """Parse a Humdrum file (path or text) and write it as MusicXML to `out`."""
    text = complete(Path(src).read_text(encoding="utf-8") if isinstance(src, Path) else src)
    score = converter.parseData(text, format="humdrum")
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out))
    return out
