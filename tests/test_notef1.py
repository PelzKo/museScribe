from fractions import Fraction as F

from omrbench.metrics import notef1


def test_aligned_forgives_a_missing_bar():
    truth = [(b, 1, F(0), 60 + b, F(1)) for b in range(4)]
    pred = [(b - 1, 1, F(0), 60 + b, F(1)) for b in range(1, 4)]   # bar 0 missing, the rest shifted
    m = notef1.compare(pred, truth)
    assert m["notes"]["tp"] == 0
    assert m["aligned"]["tp"] == 3 and m["aligned"]["recall"] == 0.75
    assert notef1.compare(truth, truth)["aligned"]["f1"] == 1.0
