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


def test_kit_moves_a_bar_read_in_bass_clef_up_a_tenth():
    score = etree.fromstring(
        '<score-partwise><part-list><score-part id="P1"><part-name>Drums</part-name></score-part></part-list>'
        f'<part id="P1"><measure number="1">{note("E3")}{note("A2")}</measure>'
        f'<measure number="2">{note("E3")}{note("C5")}</measure></part></score-partwise>')
    drumkit.apply(score, KIT)
    pos = [n.findtext("unpitched/display-step") + n.findtext("unpitched/display-octave") for n in score.iter("note")]
    assert pos == ["C5", "F4", "E3", "C5"]                 # bar 2 has a kit hit: left as read


def test_kit_events_from_omr_chords():
    from fractions import Fraction as F
    from omrbench.pipeline.assemble import kit_events
    from omrbench.pipeline.layout import Chord

    def c(x, stem, steps, dur, small=False):
        return Chord(1, x, 0, 10, 10, small, 1.0, stem, steps, dur)
    # bass drum quarters (stems down), snare off-beat eighths (up), a flam and only one of four rests read:
    # the bass drum alone fills the bar and places the snare hits by x
    chords = [c(100 + 200 * k, "down", (3,), F(1)) for k in range(4)] + \
             [c(200 + 200 * k, "up", (-1,), F(1, 2)) for k in range(4)] + [c(170, "up", (-1,), F(1), small=True)]
    evs = kit_events(chords, [c(98, "", (), F(1, 2))], F(4), 900, 20)
    v1 = [(e.kind, e.dur, e.pos) for e in evs if e.voice == 1]
    assert v1 == [("rest", F(1, 2), ()), ("drum", F(1, 2), ("C5",))] * 4
    assert [(e.dur, e.pos) for e in evs if e.voice == 2] == [(F(1), ("F4",))] * 4
    assert kit_events(chords[:3], [], F(4), 900, 20) is None      # 3 quarters: an unread beat, no guess
    # walk: quarter, quarter rest, half (C5 + E5)
    evs = kit_events([c(100, "up", (-1,), F(1)), c(500, "up", (-3, -1), F(2))], [c(300, "", (), F(1))], F(4), 900, 20)
    assert [(e.kind, e.dur, e.pos) for e in evs] == [("drum", 1, ("C5",)), ("rest", 1, ()), ("drum", 2, ("E5", "C5"))]
