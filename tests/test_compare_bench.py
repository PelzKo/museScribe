import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("compare_bench", Path(__file__).parent.parent / "scripts/compare_bench.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)


def test_acceptance_rule():
    base = {("g", "1", "A", ""): 100, ("g", "1", "B", ""): 100}
    assert cb.compare(base, {("g", "1", "A", ""): 80, ("g", "1", "B", ""): 100})[0]
    assert not cb.compare(base, {("g", "1", "A", ""): 50, ("g", "1", "B", ""): 120})[0]   # drop 30, +20 > 15
    assert cb.compare(base, {("g", "1", "A", ""): 70, ("g", "1", "B", ""): 110})[0]       # drop 20, +10 <= 10
    assert not cb.compare(base, base)[0]
