from lxml import etree

from omrbench import musicxml
from omrbench.metrics import edits, notef1


def note(p="C4", d=1, extra="", head=""):
    """A note; "uF4" = unpitched (drum) at staff position F4."""
    alter = "<alter>1</alter>" if "#" in p else ""
    t = {1: "quarter", 2: "half", 4: "whole"}[d]
    if p[0] == "u":
        pitch = f"<unpitched><display-step>{p[1]}</display-step><display-octave>{p[-1]}</display-octave></unpitched>"
    else:
        pitch = f"<pitch><step>{p[0]}</step>{alter}<octave>{p[-1]}</octave></pitch>"
    nh = f"<notehead>{head}</notehead>" if head else ""
    return f"<note>{pitch}<duration>{d}</duration><type>{t}</type>{nh}{extra}</note>"


def part(*bars, first="<attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>"):
    ms = "".join(f'<measure number="{i + 1}">{first if i == 0 else ""}{b}</measure>' for i, b in enumerate(bars))
    return etree.fromstring(f'<part id="P1">{ms}</part>')


Q4 = note("C4") + note("D4") + note("E4") + note("F4")


def pen(pred, truth):
    return edits.penalty(pred if isinstance(pred, list) else [pred], truth)


def test_identical_is_free():
    t = part(Q4, Q4)
    e = pen(part(Q4, Q4), t)
    assert e["penalty"] == 0 and e["bars_to_fix"] == 0
    assert e["from_scratch"] == 1 + 2 * 4 + 1      # add the part, 2 bars of 4 notes, the time signature
    assert pen([], t)["penalty"] == e["from_scratch"]


def test_retype_and_move_cost_one():
    t = part(Q4)
    assert pen(part(note("C4") + note("D4") + note("E4") + note("G4")), t)["penalty"] == 1
    # wrong pitch and wrong duration of one note: one retype (plus nothing for the rest)
    assert pen(part(note("C4") + note("D4") + note("G4", 2)), t)["penalty"] == 2   # retype + missing F4


def test_bars_insert_and_delete():
    t = part(Q4, note("G4", 4), Q4)
    e = pen(part(Q4, Q4), t)               # missing bar: 1 + its note
    assert e["penalty"] == 2 and e["bars_insert"] == 1
    e = pen(part(Q4, note("G4", 4), note("A4", 4), Q4), t)   # extra bar: 1, contents go with it
    assert e["penalty"] == 1 and e["bars_delete"] == 1


def test_whole_part_octave_is_one_bulk_action():
    t = part(Q4, Q4)
    up = note("C5") + note("D5") + note("E5") + note("F5")
    e = pen(part(up, up), t)
    assert e["penalty"] == 1 and e["shift"] == -12


def test_octave_off_section_is_one_action():
    up = note("C5") + note("D5") + note("E5") + note("F5")
    t = part(Q4, Q4, Q4, Q4, Q4)
    e = pen(part(Q4, up, "", up, Q4), t)     # bars 2-4 an octave up (bar 3 empty: part of the section)
    assert e["penalty"] == 1 + 4 and e["by_cat"]["octave"] == 1 and e["shift"] == 0
    e = pen(part(Q4, note("C5") + note("D4") + note("E4") + note("F4"), Q4), part(Q4, Q4, Q4))
    assert e["penalty"] == 1 and "octave" not in e["by_cat"]       # one wrong note: retype, no section


def test_dynamics_and_fermata():
    def dyn(d):
        return f'<direction><direction-type><dynamics><{d}/></dynamics></direction-type></direction>'
    ferm = "<notations><fermata/></notations>"
    t = part(dyn("p") + note("C4", 4, ferm))
    assert pen(part(dyn("p") + note("C4", 4, ferm)), t)["penalty"] == 0
    assert pen(part(dyn("f") + note("C4", 4, ferm)), t)["by_cat"] == {"dynamics": 1}      # p -> f
    assert pen(part(dyn("p") + note("C4", 4)), t)["by_cat"] == {"fermatas": 1}            # missing
    assert pen(part(dyn("p") + dyn("ff") + note("C4", 4, ferm)), t)["by_cat"] == {"dynamics": 1}  # made up


def test_slash_is_rhythm_only():
    t = part("".join(note("B4", head="slash") for _ in range(4)))
    chords = "".join(note("C4") + "<note><chord/>" + note("E4")[6:] for _ in range(4))
    assert pen(part(chords), t)["penalty"] == 0
    assert notef1.compare(notef1.notes(part(chords)), notef1.notes(t))["notes"]["f1"] == 1.0


def test_drums_keep_simultaneous_hits_by_staff_position():
    kick, hat = note("uF4"), note("uG5")
    both = kick + "<note><chord/>" + hat[6:]
    t = part(both * 4)
    assert pen(part(both * 4), t)["penalty"] == 0
    assert pen(part(kick * 4), t)["penalty"] == 4                 # hi-hats missing
    assert pen(part((note("uA4") + "<note><chord/>" + hat[6:]) * 4), t)["penalty"] == 4   # wrong drum


def test_new_categories_are_extracted():
    x = etree.fromstring(
        '<score-partwise><part-list><score-part id="P1"><part-name>A</part-name></score-part></part-list>'
        '<part id="P1"><measure number="1"><attributes><divisions>2</divisions>'
        '<transpose><chromatic>-2</chromatic></transpose></attributes>'
        '<harmony><root><root-step>C</root-step></root><kind>major</kind></harmony>'
        '<direction><direction-type><rehearsal>A</rehearsal></direction-type></direction>'
        '<barline location="left"><bar-style>heavy-light</bar-style><repeat direction="forward"/></barline>'
        '<note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type>'
        '<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'
        '<notations><tuplet type="start"/><ornaments><tremolo type="single">3</tremolo></ornaments></notations></note>'
        '<barline><bar-style>light-light</bar-style></barline></measure>'
        '<measure number="2"><attributes><transpose><chromatic>-3</chromatic></transpose></attributes>'
        '<sound><instrument-change id="x"/></sound>'
        '<direction><direction-type><words>D.S. al Coda</words></direction-type><sound dalsegno="1"/></direction>'
        '</measure></part></score-partwise>')
    ev = musicxml.extract_staves(x)[0].events
    toks = {c: [t for _, _, t in ev[c]] for c in ev if ev[c]}
    assert toks["chords"] == ["C:major"]
    assert toks["rehearsal"] == ["reh:a"]
    assert toks["structure"] == ["repeat:forward", "dalsegno"]
    assert toks["barlines"] == ["bar:light-light"]
    assert toks["tuplets"] == ["tuplet:3:2"]
    assert toks["tremolos"] == ["trem:single:3"]
    assert toks["instruments"] == ["ic"]         # transpose change + instrument-change in one bar


def test_split_parts_switch_is_an_instrument_change():
    rest = '<note><rest measure="yes"/><duration>4</duration></note>'
    flute, clar = part(Q4, rest), part(rest, Q4)
    t = part(Q4, Q4 + "<sound><instrument-change id='i'/></sound>")
    assert pen([flute, clar], t)["penalty"] == 0
    assert pen([part(Q4, Q4)], t)["by_cat"] == {"instruments": 1}


def test_system_penalty_counts_once_per_song():
    def score(*marks):
        bars = "".join(f'<measure number="{i + 1}"><direction><direction-type><rehearsal>{m}</rehearsal>'
                       f'</direction-type></direction></measure>' if m else f'<measure number="{i + 1}"/>'
                       for i, m in enumerate(marks))
        return etree.fromstring(f'<score-partwise><part-list><score-part id="P1"/></part-list>'
                                f'<part id="P1">{bars}</part></score-partwise>')
    t = score(None, "A", None, "B")
    # two parts read A (one a bar late): counted once; B missing and a bar number read as "12": 1 change
    e = edits.system_penalty([score(None, "A"), score(None, None, "A", "12")], t)
    assert e["penalty"] == 1 and e["from_scratch"] == 2
    assert edits.system_penalty([score(None, "A", None, "B", "12")], t)["penalty"] == 1   # made up


def test_system_text_in_every_output_part_is_not_made_up():
    def rit(system=""):
        return f'<direction{system}><direction-type><words>rit.</words></direction-type></direction>'
    t = etree.fromstring('<score-partwise><part-list><score-part id="P1"/><score-part id="P2"/></part-list>'
                         f'<part id="P1"><measure number="1">{rit(" system=\"only-top\"")}{Q4}</measure></part>'
                         f'<part id="P2"><measure number="1">{Q4}</measure></part></score-partwise>')
    sw = edits.system_words(t)
    assert sw == {"rit."}
    t1, t2 = t.findall("part")
    p1, p2 = part(rit() + Q4, first=""), part(rit() + Q4, first="")
    assert edits.penalty([p2], t2, sw)["penalty"] == 0          # not a made-up word in part 2
    assert edits.penalty([p1], t1, sw)["penalty"] == 0
    roots = [etree.fromstring(f'<score-partwise><part-list/>{etree.tostring(p).decode()}</score-partwise>')
             for p in (p1, p2)]
    assert edits.system_penalty(roots, t)["penalty"] == 0
    assert edits.system_penalty(roots[:0], t)["by_cat"] == {"systemtext": 1}


def test_barline_after_backup_and_split_words():
    p = part(note("C4", 4) + "<backup><duration>4</duration></backup>"
             + '<direction><direction-type><words>Spoken</words><words> line</words></direction-type></direction>'
             + '<barline location="right"><bar-style>light-heavy</bar-style></barline>')
    ev = musicxml.part_staves(p)[0].events
    assert ev["barlines"] == [(0, 4, "bar:light-heavy")]
    assert [t for *_, t in ev["words"]] == ["spoken line"]


def test_instrument_change_without_transpose_resets_it():
    tr = "<attributes><transpose><diatonic>0</diatonic><chromatic>0</chromatic><octave-change>1</octave-change></transpose></attributes>"
    ic = '<sound><instrument-change><instrument-sound>strings</instrument-sound></instrument-change></sound>'
    p = part(tr + note("C4", 4), ic + note("C4", 4))
    assert [n[3] for n in notef1.notes(p)] == [72, 60]


def test_chord_with_wrong_duration_is_one_retype_in_chord_only_bars():
    def chord(d, *ps):
        return note(ps[0], d) + "".join(note(p, d).replace("<note>", "<note><chord/>") for p in ps[1:])
    t = part(chord(2, "C4", "E4", "G4") + chord(2, "D4", "F4", "A4"))
    fwd = "<forward><duration>1</duration></forward>"
    assert pen(part(chord(1, "C4", "E4", "G4") + fwd + chord(1, "D4", "F4", "A4") + fwd), t)["penalty"] == 2
    # a bar with a single note too: per note as before
    t = part(chord(2, "C4", "E4", "G4") + note("D4", 2))
    assert pen(part(chord(1, "C4", "E4", "G4") + fwd + note("D4", 2)), t)["penalty"] == 3
