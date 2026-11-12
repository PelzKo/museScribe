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
    shift = [[o.get("type") for d in b.items for o in d.findall("direction-type/octave-shift")] for b in plan.chosen[0]]
    assert shift[1] == ["down"] and shift[3] == ["stop"]


def test_add_direction_keeps_order_so_hairpins_pair():
    from lxml import etree
    bar = _bar(notes=("C4",))
    for kind, on in (("crescendo", 0), ("stop", 2)):
        d = etree.Element("direction")
        etree.SubElement(etree.SubElement(d, "direction-type"), "wedge", type=kind)
        B.add_direction(bar, d, on, None)
    kinds = [w.get("type") for d in bar.items for w in d.findall("direction-type/wedge")]
    assert kinds == ["crescendo", "stop"]


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


def test_copy_marks_from_audiveris_only_onto_unmarked_notes():
    from lxml import etree
    aud, crop = _bar(notes=("C4", "D4")), _bar(notes=("C4", "D4"))
    for n, marks in zip(aud.notes(), (["accent", "staccato"], ["tenuto"])):
        etree.SubElement(etree.SubElement(n, "notations"), "articulations").extend(etree.Element(m) for m in marks)
    etree.SubElement(etree.SubElement(crop.notes()[1], "notations"), "articulations").append(etree.Element("staccato"))
    assert B.copy_marks(crop, aud) == 1
    assert [[a.tag for a in n.find("notations/articulations")] for n in crop.notes()] == [["accent"], ["staccato"]]


def test_read_marks_from_glyphs():
    import pymupdf
    from types import SimpleNamespace as NS

    def ch(c, x, y, w=7.2):
        return {"c": c, "bbox": (x, y - 10, x + w, y + 10), "origin": (x, y)}
    lines = [{"type": "s", "rect": None, "width": 0.5,
              "items": [("l", pymupdf.Point(50, y), pymupdf.Point(450, y))]} for y in (100, 105, 110, 115, 120)]
    lines.append({"type": "s", "rect": None, "width": 1.2,
                  "items": [("l", pymupdf.Point(250, 100), pymupdf.Point(250, 120))]})    # barline
    chars = [ch("œ", 100, 110), ch(">", 100, 125), ch(".", 102.4, 128, 2.4),     # accent + staccato below
             ch("œ", 150, 110), ch(".", 160, 107.5, 2.4),                         # augmentation dot
             ch("œ", 300, 130), ch("-", 300, 125),                                # ledger line
             ch("œ", 350, 105), ch("ß", 350, 92, 14.4)]                           # accent + staccato (wide)
    page = NS(rect=NS(width=500), get_drawings=lambda: lines,
              get_text=lambda kind: {"blocks": [{"lines": [{"spans": [
                  {"font": "EngraverFontSet", "size": 20, "chars": chars}]}]}]})
    bars = SL.read_marks(page, NS(number=1, width=1000))
    assert [b.x0 for b in bars] == [100, 500]
    assert [[e.marks for e in b.events] for b in bars] == [[["accent", "staccato"], []], [[], ["accent", "staccato"]]]


def test_cue_text_of_instrument_parts():
    from types import SimpleNamespace as NS
    pl = NS(line=NS(right=500), staff=NS(left=100))
    for t in ["DMITRY:", "GLEB: (cont)", "+ Kbd", "w/ Hn, Tbn", "Cl 2/Bsn", "[to] 29", "attacca", "Fast applause Segue",
              "We hear you, comrades, the Revolution hears you."]:
        assert A._cue_text(t, pl), t
    for t in ["arco", "pizz.", "solo 1", "cresc.", "STR. ENS. (loco & 8va)", "Moderato"]:
        assert not A._cue_text(t, pl), t
    assert A._cue_text("Util.", NS(line=NS(right=90), staff=NS(left=100)))     # left of the staff


def test_single_tremolos():
    from lxml import etree
    bar = _bar(notes=("C4", "C4"))
    for n, kind in zip(bar.notes(), ("start", "stop")):
        orn = etree.SubElement(etree.SubElement(n, "notations"), "ornaments")
        etree.SubElement(orn, "tremolo", type=kind).text = "3"
    assert B.single_tremolos([bar]) == 2
    assert [t.get("type") for t in bar.items[0].iter("tremolo")] == ["single"]


def test_slash_bar_drum_voices():
    old = B.rest_bar(1, 8, 2)
    sb = SL.SlashBar(1, 0, 100, 0, 20, [SL.Event(0, "drum", F(2), voice=1, pos=("C5", "G5"), marks=["accent"]),
                                        SL.Event(50, "drum", F(2), voice=1, pos=("C5",)),
                                        SL.Event(0, "drum", F(3), voice=2, pos=("F4",)),
                                        SL.Event(70, "rest", F(1), voice=2)])
    assert sb.length == 4
    bar = A.slash_bar(sb, old, 2)
    assert [e.tag for e in bar.items] == ["note", "note", "note", "backup", "note", "note"]
    assert bar.items[3].findtext("duration") == "8"
    n = bar.items[1]
    assert n.find("chord") is not None and n.findtext("unpitched/display-step") == "G"
    assert bar.items[0].find("notations/articulations/accent") is not None and n.find("notations") is None
    assert bar.items[4].findtext("voice") == "2" and bar.items[4].findtext("stem") == "down"
    assert bar.items[4].find("dot") is not None and bar.items[5].find("rest") is not None


def test_place_sim_from_text_layer_into_the_bar_above():
    from types import SimpleNamespace as NS
    st = NS(id=1, top=100, bottom=140, interline=10, part=1)
    plan = A.SysPlan(NS(page=1, staves=[st], groups=lambda: [[st]]), 0, n=2)
    plan.xs = [(0, 100), (100, 200)]
    plan.chosen = {0: [_bar(), _bar()]}
    A.place_sim([plan], [(1, 150, 150, "sim."), (1, 150, 400, "sim.")])     # the second is no staff's
    assert [len(b.items) for b in plan.chosen[0]] == [1, 2]
    assert plan.chosen[0][1].items[0].findtext("direction-type/words") == "sim."


def test_apply_sim_uniform_pattern_goes_on_over_longer_bars():
    from lxml import etree
    pat = _bar(notes=("E2", "E2"))
    for n in pat.notes():
        etree.SubElement(etree.SubElement(n, "notations"), "articulations").append(etree.Element("accent"))
    bars = [pat, _bar("sim.", notes=("E2", "E2")), _bar(notes=("E2",) * 4), _bar(notes=())]
    assert B.apply_sim(bars) == 2
    assert all(n.find("notations/articulations/accent") is not None for b in bars[1:3] for n in b.notes())


def test_tie_curves_pair_a_head_with_the_same_height_in_the_next_column():
    from omrbench.pipeline.vector import _ties
    st = [100, 105, 110, 115, 120]                         # staff lines, space 5
    a, b = (10, 112.5, 5, "œ"), (10, 102.5, 5, "œ")        # a chord: two heads
    c = (40, 112.5, 5, "œ")                                # next column: only the lower one
    groups = [[a, b], [c], [(70, 110, 5, "œ")]]
    curves = [(16, 39, 114, 117),                          # a -> c: a tie
              (16, 39, 98, 101),                           # b -> nothing at its height: no tie
              (76, 199, 106, 109)]                         # last column off the system end
    found = list(_ties(curves, groups, st, lambda y: st, right=200))
    assert found == [(0, a), (2, groups[2][0])]


def test_continue_patterns_repeats_a_short_groove_over_a_longer_slash_bar():
    # R44: a 2/4 groove goes on over the 2/4 and 4/4 slash bars after it
    from types import SimpleNamespace as NS
    plan = A.SysPlan(NS(logical={0: 0}), 0, n=3, times=[("2", "4"), ("2", "4"), ("4", "4")])
    groove = _bar(notes=("D5", "F4"))                      # two quarters at D=4
    plan.chosen = {0: [groove, B.Bar([], "slash"), B.Bar([], "slash")]}
    A.continue_patterns([plan], 4, A.Stats())
    assert [len(b.notes()) for b in plan.chosen[0]] == [2, 2, 4]
    assert plan.chosen[0][2].source == "pattern"
