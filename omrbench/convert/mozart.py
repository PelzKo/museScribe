"""Mozart (aashrafh/Mozart) text output -> MusicXML via music21.

Format: one `[ ... ]` line per staff, several staves wrapped in `{ }`; tokens `\\meter<"4/4">`, notes
`<a-g><accidental><octave>/<duration>[.]*` (accidentals # ## & &&; octave 1 = the octave from middle C),
chords `{e1/4,g1/4}`. Mozart reads one treble staff at a time and writes no rests, clefs or barlines,
so the staves are concatenated into one treble part and music21 makes the bars from the meter.
"""
from __future__ import annotations

import re
from pathlib import Path

from music21 import chord, clef, meter, note, stream

NOTE = re.compile(r"^([a-g])(##|#|&&|&)?(\d)/(\d+)(\.*)$")
METER = re.compile(r'\\meter<"(\d+/\d+)">')
ACC = {"#": "#", "##": "##", "&": "-", "&&": "--"}


def _note(tok: str) -> note.Note:
    m = NOTE.match(tok)
    if not m:
        raise ValueError(f"not a Mozart note: {tok!r}")
    step, acc, octave, dur, dot = m.groups()
    n = note.Note(f"{step.upper()}{ACC.get(acc or '', '')}{int(octave) + 3}")
    dots = min(len(dot), 3)       # Mozart sometimes stacks dots: "c1/1...."
    n.quarterLength = 4 / int(dur) * (2 - 0.5 ** dots)
    return n


def parse(text: str) -> stream.Part:
    part = stream.Part()
    part.append(clef.TrebleClef())
    m = METER.search(text)
    part.append(meter.TimeSignature(m.group(1) if m else "4/4"))
    for line in re.findall(r"\[(.*?)\]", METER.sub("", text)):
        for tok in re.findall(r"\{[^}]*\}|\S+", line):
            if not tok.strip("."):
                continue        # a dot Mozart could not attach to a note
            if tok.startswith("{"):
                notes = [_note(t) for t in tok[1:-1].split(",") if t]
                c = chord.Chord(notes)
                c.quarterLength = notes[0].quarterLength
                part.append(c)
            else:
                part.append(_note(tok))
    return part


def mozart_to_musicxml(src: Path | str, out: Path) -> Path:
    text = Path(src).read_text(encoding="utf-8") if isinstance(src, Path) else src
    score = stream.Score([parse(text)])
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out), makeNotation=True)
    return out
