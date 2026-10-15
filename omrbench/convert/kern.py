"""**kern / **bekern (Humdrum) -> MusicXML via music21.

Model output is often a bare spine body (Transcoda's canonical form, SMT's bekern): the `**kern`
header and the `*-` terminator are added when missing, bekern separators (`·`, `@`) removed, and
records are fitted to the active spine count. Other parse failures raise.
"""
from __future__ import annotations

from pathlib import Path

from music21 import converter


def _spines_after(cols: list[str]) -> int:
    """Active spine count after an interpretation record (*^ splits, a run of *v merges, *- ends)."""
    n, i = 0, 0
    while i < len(cols):
        if cols[i] == "*v":
            while i < len(cols) and cols[i] == "*v":
                i += 1
            n += 1
            continue
        n += {"*^": 2, "*+": 2, "*-": 0}.get(cols[i], 1)
        i += 1
    return n


def complete(text: str) -> str:
    """Add the header and terminators if the body lacks them, and fit every record to the active
    spine count (models emit rows with a column too many or too few after splits and merges)."""
    text = text.replace("·", "").replace("@", "")       # bekern -> kern
    out: list[str] = []
    n = None
    for ln in (ln for ln in text.strip("\n").split("\n") if ln.strip()):
        cols = ln.split("\t")
        if ln.startswith("!!"):
            out.append(ln)
            continue
        if n is None:
            n = len(cols)
            if cols[0].startswith("**"):
                out.append(ln)
                continue
            out.append("\t".join(["**kern"] * n))
        if n == 0:
            break
        if len(cols) != n:   # shortcut: pads or cuts at the right edge, so a misplaced column loses its notes
            c0 = cols[0][:1]
            cols = (cols + ([c0] if c0 in "=*!" else ["."]) * n)[:n]
        if cols[0].startswith("*") and not cols[0].startswith("**"):
            cols = [c if c != "*v" or "*v" in cols[max(0, i - 1):i] + cols[i + 1:i + 2] else "*"
                    for i, c in enumerate(cols)]           # a lone *v merges nothing
            n = _spines_after(cols)
        out.append("\t".join(cols))
    if n:
        out.append("\t".join(["*-"] * n))
    return "\n".join(out) + "\n"


def kern_to_musicxml(src: Path | str, out: Path) -> Path:
    """Parse a Humdrum file (path or text) and write it as MusicXML to `out`."""
    text = complete(Path(src).read_text(encoding="utf-8") if isinstance(src, Path) else src)
    score = converter.parseData(text, format="humdrum")
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out))
    return out
