"""Mozart text -> MusicXML: pitches, accidentals, chords, dots, and bars made from the meter."""
from music21 import converter

from omrbench.convert.mozart import mozart_to_musicxml

TEXT = """{
[ \\meter<"4/4">c1/4 e#1/4 {e1/4,g1/4} b&1/8. d2/16 ]
[ \\meter<"4/4">c2/2.. c2/8 ]
}"""


def test_round_trip(tmp_path):
    score = converter.parse(mozart_to_musicxml(TEXT, tmp_path / "out.musicxml"))
    els = list(score.recurse().notes)
    assert [str(p) for e in els for p in e.pitches] == ["C4", "E#4", "E4", "G4", "B-4", "D5", "C5", "C5"]
    assert els[3].quarterLength == 0.75
    assert len(score.parts[0].getElementsByClass("Measure")) == 2
