from omrbench.pipeline import assemble as A
from omrbench.project import bar_map


def test_bar_map_and_positions():
    spec = bar_map("1: 4/4, 68: 2/4, 69: 4/4, 132B: 3/4")
    assert spec[1] == (68, "", "2/4") and spec[-1] == (132, "B", "3/4")
    pos = A.song_positions(spec, [(131, "A"), (132, "A"), (132, "B")], False, 140)
    assert pos[66:69] == ["4/4", "2/4", "4/4"]
    assert pos[131 + 1] == "4/4" and pos[132 + 2] == "3/4"     # 131A and 132A take positions too
    assert A.song_positions(spec, [], True, 3) == ["4/4", "4/4", "4/4"]     # pickup = position 0
    assert A._main_time(spec) == ("4", "4")


def test_written_key():
    assert A.written_key(0, 0) == 0 and A.written_key(-3, -2) == -1      # Eb concert: F for a Bb clarinet
    assert A.written_key(0, -9) == 3 and A.written_key(-5, -2) == -3     # A for an Eb alto sax; Db -> Eb
    assert A.written_key(0, -12) == 0 and A.written_key(6, -2) == -4     # octave only; F# + 2 -> Ab (not G#)


def test_apply_song_time_fixes_rest_bars_of_a_misread_time():
    from omrbench.pipeline import bars as B
    plan = A.SysPlan(None, 0, n=2)
    plan.times = [("2", "4"), ("4", "4")]
    plan.chosen = {0: [B.rest_bar(1, 4, 2), B.rest_bar(1, 8, 2)]}       # 2/4 rest bar, D = 2
    stats = A.Stats()
    A.apply_song_time([plan], bar_map("1: 4/4"), 2, stats)
    assert plan.times == [("4", "4"), ("4", "4")] and stats.times_set == 1
    assert plan.chosen[0][0].notes()[0].findtext("duration") == "8"


def test_measure_rest_gets_the_bar_length():
    from omrbench.pipeline import bars as B
    bar = B.rest_bar(2, 8, 2)          # 4/4 rest bar, two staves
    B.fit_measure_rests(bar, 6)        # written into a 3/4 bar
    assert [e.findtext("duration") for e in bar.items] == ["6", "6", "6"]


def test_sim_copies_the_pattern_articulations():
    from lxml import etree
    from omrbench.pipeline import bars as B

    def bar(marked, word=None):
        items = []
        if word:
            items.append(etree.fromstring(f"<direction><direction-type><words>{word}</words></direction-type></direction>"))
        for _ in range(2):
            n = etree.fromstring("<note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration></note>")
            if marked:
                etree.SubElement(etree.SubElement(n, "notations"), "articulations").append(etree.Element("accent"))
            items.append(n)
        return B.Bar(items, "crop")

    bars = [bar(True), bar(False, "sim."), bar(False), bar(True)]
    assert B.apply_sim(bars) == 2
    assert all(len(B._marked(b)) == 2 for b in bars)
