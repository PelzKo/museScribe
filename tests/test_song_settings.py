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
