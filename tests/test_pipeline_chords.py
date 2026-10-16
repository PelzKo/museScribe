from omrbench.pipeline import chords


def names(run):
    found = chords.parse(run)
    return None if found is None else [m.group(0) for _, m in found]


def test_parse_whole_runs_only():
    assert names("Eb/Bb Bb Ab") == ["Eb/Bb", "Bb", "Ab"]
    assert names("AbEb/Ab") == ["Ab", "Eb/Ab"]            # printed without a space
    assert names("DbMaj7") == ["DbMaj7"] and names("Am") == ["Am"]
    assert names("Fill ") is None and names("scratch") is None and names("34") is None


def test_harmony_element():
    found = chords.parse("Ebm7/Bb")
    _, m = found[0]
    root, acc, suffix, bass, bacc = m.groups()
    s = chords.Symbol(1, 0, 0, 1, 1, root, chords.ALTER[acc], chords.KINDS[suffix], suffix, bass, chords.ALTER[bacc])
    h = chords.harmony(s)
    assert h.findtext("root/root-step") == "E" and h.findtext("root/root-alter") == "-1"
    assert h.findtext("kind") == "minor-seventh" and h.find("kind").get("text") == "m7"
    assert h.findtext("bass/bass-step") == "B" and h.findtext("bass/bass-alter") == "-1"
