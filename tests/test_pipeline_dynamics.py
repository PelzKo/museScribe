import numpy as np

from omrbench.pipeline import dynamics


def test_ncc_finds_the_glyph_and_build_drops_outliers():
    rng = np.random.default_rng(0)
    glyph = (rng.random((10, 12)) > 0.5).astype(np.float32)
    band = np.zeros((30, 60), np.float32)
    band[12:22, 33:45] = glyph
    sc = dynamics.ncc(band, glyph)
    assert np.unravel_index(int(np.argmax(sc)), sc.shape) == (12, 33) and sc.max() > 0.99
    hits = dynamics.detect(band, {"mf": glyph})
    assert hits and hits[0][1] == "mf" and abs(hits[0][2] - 39) < 1e-6
    noise = (rng.random((10, 12)) > 0.5).astype(np.float32)
    t = dynamics.build([(glyph, "p")] * 5 + [(noise, "p")])
    assert np.allclose(t["p"], glyph, atol=0.02)          # the misread box is left out
