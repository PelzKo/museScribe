import importlib.util
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

spec = importlib.util.spec_from_file_location("error_report", Path(__file__).parent.parent / "scripts/error_report.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)


def n(onset, midi, dur, step, alter=0, octave=4, typ="quarter", dots=0, tup=""):
    return {"staff": 1, "onset": F(onset), "midi": midi, "dur": F(dur), "step": step, "alter": alter, "oct": octave,
            "type": typ, "dots": dots, "tup": tup}


def test_one_note_counts_every_wrong_attribute():
    log = Counter()
    truth = [n(0, 70, F(3, 2), "B", -1, 4, dots=1), n(2, 72, 1, "C", 0, 5), n(3, 74, 1, "D", 0, 5)]
    pred = [n(0, 71, 1, "B", 0, 4), n(2, 84, 1, "C", 0, 6)]     # Bb. -> B: accidental + dot; C5 -> C6
    er.diff_notes(pred, truth, lambda k, t=None: log.update([k]))
    assert log == Counter({"pitch: accidental missing": 1, "rhythm: dot missing": 1,
                           "pitch: octave off (+1)": 1, "notes: note missing": 1})


def test_tie_read_as_slur():
    log = Counter()
    er.diff_items(Counter({("slurs", 1, F(0), "slur"): 1}), Counter({("ties", 1, F(0), "tie"): 1}),
                  lambda k, t=None: log.update([k]))
    assert log == Counter({"ties: tie read as a slur": 1})
