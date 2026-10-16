from pathlib import Path

from omrbench import truth
from omrbench.pipeline.text import playing_words


def test_playing_words_follow_the_truth():
    seq, muted, out = ["Open", "to St Mute", "St. Mute", "to Open", "Open", "PiZZ-", "arco", "Open H.H."], False, []
    for t in seq:
        text, muted = playing_words(t, muted)
        out.append(text)
    assert out == ["", "", "gedämpft", "", "offen", "pizz.", "arco", "Open H.H."]


XML = """<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
<part id="P1"><measure number="1"/></part></score-partwise>"""


def test_truth_files_merged_and_named_by_file(tmp_path: Path):
    files = []
    for name in ("#13 - Bass", "#13 - Cello"):
        files.append(tmp_path / f"{name}.musicxml")
        files[-1].write_text(XML)
    root = truth.load(files, tmp_path, None)
    assert [n for n, _ in truth.parts(root)] == ["Bass", "Cello"]
    assert len({p.get("id") for p in root.findall("part")}) == 2


def test_tempo_in_brackets_left_to_the_metronome():
    from omrbench.pipeline.text import clean_words
    assert clean_words("Driving (J = 130)") == "Driving"
    assert clean_words("subito (J = 122 )") == "subito"
    assert clean_words("Maestoso = 92") == "Maestoso"


PLAIN = """<part id="P1"><measure number="1">
<direction><direction-type><dynamics><p/></dynamics></direction-type></direction>
<direction><direction-type><words>pizz.</words></direction-type></direction>
<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>92</per-minute></metronome></direction-type></direction>
<direction><direction-type><rehearsal>A</rehearsal></direction-type></direction>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>3</duration><type>quarter</type><dot/>
<notations><tied type="start"/><slur type="start"/><articulations><staccato/></articulations><fermata/>
<ornaments><tremolo type="single">3</tremolo><trill-mark/></ornaments></notations></note>
<note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><notations><articulations><accent/></articulations></notations></note>
</measure></part>"""


def test_strip_marks_keeps_notes_ties_dots_tremolos():
    from lxml import etree
    from omrbench.musicxml import strip_marks
    part = etree.fromstring(PLAIN)
    strip_marks(part)
    assert [w.text for w in part.iter("words")] == ["pizz."]
    assert part.find(".//rehearsal") is not None
    assert not part.findall(".//dynamics") and not part.findall(".//metronome")
    n1, n2 = part.findall(".//note")
    assert [e.tag for e in n1.find("notations")] == ["tied", "ornaments"]
    assert [e.tag for e in n1.find("notations/ornaments")] == ["tremolo"]
    assert n1.find("dot") is not None and n2.find("notations") is None


def test_plain_cell_of_a_piano_reduction_picks_the_labels():
    from omrbench.project import Part, plain_row
    part = Part("4", "PianoReduction", Path("x.pdf"), {},
                ["Piano=Klavierauszug", "Men=Männer", "First=Männer", "All=Frauen", "All=Männer"])
    plain_row(part, "Männer, Men")
    assert part.meta["plain"] == ["Men", "First", "Männer"] and part.plain == ["Männer", "Men"]
    part = Part("4", "Violin 2", Path("x.pdf"), {}, ["Violine 2"])
    plain_row(part, "x")
    assert part.meta["plain"] is True and part.plain == ["Violine 2"]


def _n(step, octave, *slurs):
    s = "".join(f'<slur type="{t}" number="{k}"/>' for t, k in slurs)
    return (f"<note><pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>4</duration>"
            f"<voice>1</voice><notations>{s}</notations></note>")


def test_slur_between_equal_pitches_becomes_tie():
    from lxml import etree
    from omrbench import musicxml
    # G-(B~B): the outer slur G..B stays, the inner B-B curve is a tie; C-D stays a slur
    xml = (f'<score-partwise><part id="P1"><measure number="1">{_n("G", 3, ("start", 1))}'
           f'{_n("B", 3, ("start", 2))}</measure><measure number="2">{_n("B", 3, ("stop", 2), ("stop", 1))}'
           f'{_n("C", 4, ("start", 1))}{_n("D", 4, ("stop", 1))}</measure></part></score-partwise>')
    root = etree.fromstring(xml)
    assert musicxml.slurs_to_ties(root) == 1
    notes = root.findall(".//note")
    assert [t.get("type") for t in notes[1].iter("tied")] == ["start"]
    assert [t.get("type") for t in notes[2].iter("tied")] == ["stop"]
    assert [s.get("type") for s in notes[2].iter("slur")] == ["stop"]
    assert notes[3].find("notations/slur").get("type") == "start"
