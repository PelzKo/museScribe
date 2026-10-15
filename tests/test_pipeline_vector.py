from fractions import Fraction as F

from omrbench.pipeline import assemble as A
from omrbench.pipeline import bars as B
from omrbench.pipeline import vector as SL


def test_slash_bar_rhythm_ties_and_kept_directions():
    old = B.rest_bar(1, 8, 2)
    from lxml import etree
    old.items.insert(0, etree.fromstring("<harmony><root><root-step>F</root-step></root><kind>major</kind></harmony>"))
    sb = SL.SlashBar(1, 0, 100, 0, 20, [SL.Event(0, "rest", F(1)), SL.Event(10, "slash", F(3, 2)),
                                        SL.Event(20, "slash", F(1, 2), tie_start=True),
                                        SL.Event(30, "slash", F(1), tie_stop=True)])
    assert sb.length == 4
    bar = A.slash_bar(sb, old, 2)
    notes = bar.notes()
    assert bar.items[0].tag == "harmony" and len(notes) == 4
    assert [n.findtext("duration") for n in notes] == ["2", "3", "1", "2"]
    assert notes[1].findtext("type") == "quarter" and notes[1].find("dot") is not None
    assert notes[1].findtext("notehead") == "slash" and notes[0].find("rest") is not None
    assert notes[2].find("tie").get("type") == "start" and notes[3].find("notations/tied").get("type") == "stop"
    assert A.slash_bar(SL.SlashBar(1, 0, 1, 0, 1, [SL.Event(0, "slash", F(5, 4))]), old, 2) is None
    marked = A.slash_bar(SL.SlashBar(1, 0, 1, 0, 1, [SL.Event(0, "slash", F(4), marks=["accent", "accent"])]), old, 2)
    assert [a.tag for a in marked.notes()[0].find("notations/articulations")] == ["accent"]


def _bar(text=None, notes=("C4",)):
    from lxml import etree
    items = []
    if text:
        items.append(etree.fromstring(f"<direction><direction-type><words>{text}</words></direction-type></direction>"))
    for p in notes:
        items.append(etree.fromstring(f"<note><pitch><step>{p[0]}</step><octave>{p[1]}</octave></pitch>"
                                      "<duration>4</duration><voice>1</voice></note>"))
    return B.Bar(items, "crop")


def test_patch_octaves_from_loco_8va_until_loco():
    plan = A.SysPlan(None, 0, n=4)
    plan.chosen = {0: [_bar(), _bar("STR. ENS. (loco &amp; 8va)"), _bar(), _bar("STR. ENS. (loco)")]}
    A.patch_octaves([plan], A.Stats())
    octs = [b.notes()[0].findtext("pitch/octave") for b in plan.chosen[0]]
    assert octs == ["4", "5", "5", "4"]
    assert plan.chosen[0][1].items[0].find("direction-type/octave-shift").get("type") == "down"
    assert plan.chosen[0][3].items[0].find("direction-type/octave-shift").get("type") == "stop"


def test_repeat_copies_the_bar_before_by_printed_number():
    plan = A.SysPlan(None, 0, n=4)
    plan.chosen = {0: [_bar(notes=("C4",)), _bar(notes=("D4",)), _bar("sim.", notes=()), _bar(notes=())]}
    A.apply_repeats([plan], [SL.Repeat(1, 0, 0, 1, number=3), SL.Repeat(1, 0, 0, 1, number=4)], A.Stats())
    bars = plan.chosen[0]
    assert [b.notes()[0].findtext("pitch/step") for b in bars] == ["C", "D", "D", "D"]
    assert bars[2].items[-1].tag == "direction"          # the bar keeps its own text


def test_barlines_dedupe_double_bars():
    v = [(50, 0, 40), (51.5, 0, 40), (100, 0, 40), (30, 5, 20)]        # double bar; a stem
    assert SL._barlines(v, 0, 40, 0, 200) == [50, 100]


def test_copy_ties_from_audiveris_by_onset_and_pitch():
    from lxml import etree
    aud = _bar(notes=("C4", "D4"))
    aud.items[0].insert(2, etree.Element("tie", type="start"))
    crop = _bar(notes=("C4", "D4"))
    assert B.copy_ties(crop, aud) == 1
    n = crop.notes()[0]
    assert [c.tag for c in n][:3] == ["pitch", "duration", "tie"] and n.find("notations/tied").get("type") == "start"
    assert crop.notes()[1].find("tie") is None


def test_cue_text_of_instrument_parts():
    from types import SimpleNamespace as NS
    pl = NS(line=NS(right=500), staff=NS(left=100))
    for t in ["DMITRY:", "GLEB: (cont)", "+ Kbd", "w/ Hn, Tbn", "Cl 2/Bsn", "[to] 29",
              "We hear you, comrades, the Revolution hears you."]:
        assert A._cue_text(t, pl), t
    for t in ["arco", "pizz.", "solo 1", "cresc.", "STR. ENS. (loco & 8va)", "Moderato"]:
        assert not A._cue_text(t, pl), t
    assert A._cue_text("Util.", NS(line=NS(right=90), staff=NS(left=100)))     # left of the staff
