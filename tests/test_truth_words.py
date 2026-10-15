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
