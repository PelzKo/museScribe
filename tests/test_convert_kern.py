"""kern -> MusicXML: a Humdrum file with two spines keeps every pitch and both parts."""
from music21 import converter

from omrbench.convert.kern import kern_to_musicxml

KERN = """**kern\t**kern
*clefG2\t*clefG2
*M3/4\t*M3/4
=1\t=1
4c 4e 4g\t4d
4d\t4f 4a
=2\t=2
2c 2e\t2e
*-\t*-
"""


def test_two_spines_round_trip(tmp_path):
    out = kern_to_musicxml(KERN, tmp_path / "out.musicxml")
    score = converter.parse(out)
    assert len(score.parts) == 2
    assert sum(len(n.pitches) for n in score.recurse().notes) == 10


def test_single_spine_pitches_in_order(tmp_path):
    kern = "**kern\n*clefG2\n*M4/4\n4c\n4e\n4g\n4b\n*-\n"
    out = kern_to_musicxml(kern, tmp_path / "out.musicxml")
    pitches = [str(n.pitch) for n in converter.parse(out).recurse().notes]
    assert pitches == ["C4", "E4", "G4", "B4"]


def test_bare_body_gets_header_and_terminator(tmp_path):
    body = "*clefG2\t*clefF4\n*M2/4\t*M2/4\n4c\t4C\n4e\t4E\n=\t=\n2g\t2G\n"
    out = kern_to_musicxml(body, tmp_path / "out.musicxml")
    assert len(converter.parse(out).parts) == 2
