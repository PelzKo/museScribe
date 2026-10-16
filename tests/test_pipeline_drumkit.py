from lxml import etree

from omrbench.pipeline import drumkit

KIT = {"F4": {"notehead": "normal", "instrument": "Bass Drum 1", "midi": 37},
       "C5": {"notehead": "normal", "instrument": "Acoustic Snare", "midi": 39},
       "G5": {"notehead": "x", "instrument": "Closed Hi-Hat", "midi": 43}}


def note(pos):
    return (f"<note><unpitched><display-step>{pos[0]}</display-step><display-octave>{pos[1]}</display-octave>"
            "</unpitched><duration>1</duration><voice>1</voice><type>quarter</type><stem>up</stem></note>")


def test_kit_maps_snaps_and_names_instruments():
    score = etree.fromstring(
        '<score-partwise><part-list><score-part id="P1"><part-name>Drums</part-name></score-part></part-list>'
        f'<part id="P1"><measure number="1">{note("G5")}{note("A5")}{note("D5")}{note("D4")}</measure></part>'
        '</score-partwise>')
    assert drumkit.apply(score, KIT) == 2                  # A5 -> G5, D5 -> C5; D4 has no kit neighbour
    ns = score.findall(".//note")
    assert [n.findtext("unpitched/display-step") + n.findtext("unpitched/display-octave") for n in ns] == \
        ["G5", "G5", "C5", "D4"]
    assert ns[0].findtext("notehead") == "x" and ns[2].find("notehead") is None
    assert [c.tag for c in ns[0]] == ["unpitched", "duration", "instrument", "voice", "type", "stem", "notehead"]
    assert ns[0].find("instrument").get("id") == "P1-I3" and ns[3].find("instrument") is None
    assert len(score.findall(".//score-instrument")) == 3


def test_kit_for_needs_a_drum_set(tmp_path):
    f = tmp_path / "k.yaml"
    f.write_text("a:\n  kits:\n    Triangel:\n      positions: {E4: {notehead: normal, instrument: T, midi: 82}}\n")
    assert drumkit.kit_for("a", f) is None and drumkit.kit_for("b", f) is None
    assert drumkit.kit_for("ghost") is not None
