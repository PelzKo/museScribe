"""scripts/review_edit.py: spanners / del_spanner / add_arpeggio / del_artics on a tiny score."""
import sys
from fractions import Fraction as F
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_edit as E  # noqa: E402

XML = """<museScore><Score><Staff id="1">
<Measure><voice><Chord><durationType>half</durationType>
  <Spanner type="Slur"><Slur/><next><location><measures>1</measures><fractions>1/4</fractions></location></next></Spanner>
  <Articulation><subtype>articStaccatoBelow</subtype></Articulation><Note><pitch>60</pitch></Note></Chord>
  <Rest><durationType>half</durationType></Rest></voice></Measure>
<Measure><voice><Chord><durationType>quarter</durationType><Note><pitch>62</pitch></Note></Chord>
  <Spanner type="Slur"><prev><location><measures>-1</measures><fractions>-1/4</fractions></location></prev></Spanner>
  <Chord><durationType>half</durationType><dots>1</dots><Note><pitch>64</pitch></Note></Chord></voice></Measure>
</Staff></Score></museScore>"""


def test_del_spanner_arpeggio_artics():
    score = etree.fromstring(XML).find("Score")
    sp = E.spanners(score, 1, "Slur")
    assert [(b, t, s) for _, b, t, s in sp] == [(1, F(0), True), (2, F(1, 4), False)]
    assert E.del_spanner(score, 1, "Slur", 1) == (2, F(1, 4))
    assert E.spanners(score, 1, "Slur") == []
    c = E.chords(score, 1, 1)[0]
    E.del_artics(c)
    assert c.find("Articulation") is None
    E.add_arpeggio(c)
    assert c[-1].tag == "Arpeggio" and c[-1].findtext("subtype") == "0"


def test_pc_set_voice_slur_barline():
    assert E.pc("F#4") == (66, 20) and E.pc("Bb3") == (58, 12) and E.pc("C4") == (60, 14)
    score = etree.fromstring(XML).find("Score")
    E.del_spanner(score, 1, "Slur", 1)
    v = E.set_voice(score, 1, 2, "C#4/8 A3/8 r/4 E4+G#4/4.", vi=1)
    assert [E.dur(c) for c in v] == [F(1, 8), F(1, 8), F(1, 4), F(3, 8)]
    assert len(E.bar(score, 1, 2).findall("voice")) == 2
    E.add_slur_voice(score, 1, (1, 0), (2, 1))
    sp = E.spanners(score, 1, "Slur")
    assert [(b, t, s) for _, b, t, s in sp] == [(1, F(0), True), (2, F(1, 4), False)]
    E.add_barline(score, 1, 2)
    assert E.bar(score, 1, 2).find("voice")[-1].findtext("subtype") == "double"


TRANS = """<museScore><Score><Part><Staff/><Instrument><transposeChromatic>-7</transposeChromatic>
<transposeDiatonic>-4</transposeDiatonic></Instrument></Part><Staff id="1">
<Measure><voice><TimeSig><sigN>3</sigN><sigD>4</sigD></TimeSig><Rest><durationType>measure</durationType>
<duration>3/4</duration></Rest></voice></Measure>
<Measure><voice><Rest><durationType>measure</durationType><duration>3/4</duration></Rest></voice></Measure>
</Staff></Score></museScore>"""


def test_set_voice_written_pitch_tuplet_tie_and_location():
    score = etree.fromstring(TRANS).find("Score")
    E.set_voice(score, 1, 2, "G4/2.")
    v = E.set_voice(score, 1, 1, "3:2{ C5/8 D5/8 E5/8 } Bb4/4 G4/4~")
    notes = [(n.findtext("pitch"), n.findtext("tpc"), n.findtext("tpc2")) for n in v.iter("Note")]
    assert notes[0] == ("65", "13", "14")                  # written C5 in F horn = concert F4
    assert notes[3] == ("63", "11", "12")                  # written Bb4 = concert Eb4
    assert E.voice_len(v) == F(3, 4)
    assert [t for c, t in E.timeline(v) if c.tag == "Chord"] == [0, F(1, 12), F(1, 6), F(1, 4), F(1, 2)]
    tie = v.findall("Chord")[-1].find("Note/Spanner[@type='Tie']/next/location")
    assert tie.findtext("measures") == "1" and tie.findtext("fractions") == "-1/2"
    d = etree.Element("Dynamic")
    E.insert_at(v, F(1, 8), d)                            # between tuplet notes: cursor moves around it
    assert [t for c, t in E.timeline(v) if c is d] == [F(1, 8)]
    assert [t for c, t in E.timeline(v) if c.tag == "Chord"][1:3] == [F(1, 12), F(1, 6)]
    try:
        E.set_voice(score, 1, 2, "G4/2")
    except ValueError:
        pass
    else:
        raise AssertionError("short bar accepted")


def test_set_voice_keeps_markings_and_checks_first():
    score = etree.fromstring(TRANS).find("Score")
    E.set_voice(score, 1, 1, "C5/4 D5/4 E5/4")
    E.add_dynamic(score, 1, 1, F(1, 2), "mf")
    E.set_voice(score, 1, 1, "3:2{ C5/4 D5/8 } r/4 E5/4")
    v = E.bar(score, 1, 1).find("voice")
    assert [t for c, t in E.timeline(v) if c.tag == "Dynamic"] == [F(1, 2)]     # stays on beat 3
    assert v.find("Tuplet").findtext("baseNote") == "eighth"                     # from the whole group
    before = etree.tostring(v)
    for bad in ("C5/4~ r/4 C5/4", "C5/2", "3:2{ C5/8 D5/8 E5/8 C5/2"):
        try:
            E.set_voice(score, 1, 1, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)
        assert etree.tostring(v) == before                                       # refused before any change
