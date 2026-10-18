import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("pdf_truth_check", ROOT / "scripts/pdf_truth_check.py")
ptc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ptc)


def test_pitch_helpers():
    assert ptc.step_pitch("&", 0) == ("F", 5)          # treble top line
    assert ptc.step_pitch("?", 4) == ("D", 3)          # bass middle line
    assert ptc.keymap(-2) == {"B": -1, "E": -1}
    assert ptc.clusters([100, 104, 200, 260, 271]) == [100, 200, 260]   # ':||:' is one barline


def test_bar_labels():
    rows = {"bars": [0, 8], "letters": [0, "3A-B"], "time": [0, "0: 2/4, 1: 4/4"]}
    assert ptc.bar_labels(rows) == ["0", "1", "2", "3", "3A", "3B", "4", "5"]


@pytest.mark.skipif(not (ROOT / "data/ghost/pdfs/Bass.pdf").exists(), reason="Ghost data not here")
def test_ghost_20_bass():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        lines = ptc.compare("ghost", "20", "Bass")
    except RuntimeError as e:   # no MuseScore and no cached truth export
        pytest.skip(str(e))
    finally:
        os.chdir(cwd)
    assert not [line for line in lines if " bar " in line]   # bar 135 fixed in the truth 2026-10-18
