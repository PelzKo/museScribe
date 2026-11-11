from omrbench.pipeline import assemble as A
from omrbench.project import bar_map


def test_bar_map_and_positions():
    spec = bar_map("1: 4/4, 68: 2/4, 69: 4/4, 132B: 3/4")
    assert spec[1] == (68, "", "2/4") and spec[-1] == (132, "B", "3/4")
    pos = A.song_positions(spec, [(131, "A"), (132, "A"), (132, "B")], False, 140)
    assert pos[66:69] == ["4/4", "2/4", "4/4"]
    assert pos[131 + 1] == "4/4" and pos[132 + 2] == "3/4"     # 131A and 132A take positions too
    cut = A.song_positions(bar_map("1: 4/4, 2C: 3/4, 3: 2/4"), [(2, "C")], False, 4)
    assert cut == ["4/4", "4/4", "3/4", "2/4"]      # a cut to 2C: 1, 2, 2C, 3 (no 2A, 2B)
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


def test_rest_only_voice_becomes_a_measure_rest():
    from lxml import etree
    from omrbench.pipeline import bars as B
    x = [etree.fromstring(s) for s in (
        "<note><pitch><step>C</step><octave>5</octave></pitch><duration>3</duration><voice>1</voice></note>",
        "<backup><duration>3</duration></backup>",
        "<note><rest/><duration>12</duration><voice>2</voice></note>",          # whole rest in 3/4
        "<backup><duration>9</duration></backup>",
        "<note><pitch><step>D</step><octave>5</octave></pitch><duration>6</duration><voice>1</voice></note>",
        "<note><rest/><duration>6</duration><voice>3</voice></note>",           # 2 + 2 quarters of rests
        "<note><rest/><duration>6</duration><voice>3</voice></note>")]
    bar = B.Bar(x, "crop")
    B.fit_measure_rests(bar, 9)
    assert [e.findtext("duration") for e in bar.items] == ["3", "3", "9", "6", "6", "9"]
    assert bar.items[2].find("rest").get("measure") == "yes"


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


def test_sim_copies_a_slur_inside_the_pattern_bar():
    from lxml import etree
    from omrbench.pipeline import bars as B

    def bar(slur, word=None):
        items = [etree.fromstring(f"<direction><direction-type><words>{word}</words></direction-type></direction>")] \
            if word else []
        for t in ("start", "stop"):
            n = etree.fromstring("<note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration></note>")
            if slur:
                etree.SubElement(etree.SubElement(n, "notations"), "slur", type=t)
            items.append(n)
        return B.Bar(items, "crop")

    bars = [bar(True), bar(False, "sim."), bar(False)]
    assert B.apply_sim(bars) == 2
    assert [s.get("type") for s in bars[2].items[0].iter("slur")] == ["start"]


def test_letter_list():
    from omrbench.project import letter_list
    assert letter_list("131A, 132C, 148A-C") == [(131, "A"), (132, "C"), (148, "A"), (148, "B"), (148, "C")]


def test_doublings_one_part():
    from omrbench.project import part_meta
    row = {"file": "Reed", "pages": "14", "skip": "", "instruments": "Flute, Clarinet", "extra": ""}
    show = {"instruments": {"Clarinet": {"transpose": "Bb"}}}
    assert part_meta(row, show, {})["split_instruments"] is True
    meta = part_meta(row, {**show, "doublings": "one_part"}, {})
    assert meta["doubling"] is True and "split_instruments" not in meta


def test_short_bar_gets_a_rest_after_its_last_chord():
    from lxml import etree
    from omrbench.pipeline import bars as B
    x = [etree.fromstring(s) for s in (
        "<note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><voice>1</voice></note>",
        "<note><chord/><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><voice>1</voice></note>",
        "<backup><duration>4</duration></backup>",
        "<note><pitch><step>C</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice></note>")]
    bar = B.Bar(x, "crop")
    B.pad_short_bar(bar, 8)                     # 2 of 4 quarters filled
    assert [(e.tag, e.findtext("duration")) for e in bar.items] == [
        ("note", "4"), ("note", "4"), ("note", "4"), ("backup", "8"), ("note", "2")]
    assert bar.items[2].find("rest") is not None and bar.items[2].findtext("voice") == "1"


def test_long_bar_loses_the_overshoot_from_its_longest_note():
    from lxml import etree
    from omrbench.pipeline import bars as B
    x = [etree.fromstring(s) for s in (
        "<note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice></note>",
        "<note><pitch><step>D</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice>"
        "<type>whole</type></note>",
        "<note><chord/><pitch><step>F</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice></note>",
        "<backup><duration>10</duration></backup>",
        "<note><pitch><step>C</step><octave>3</octave></pitch><duration>8</duration><voice>2</voice></note>")]
    bar = B.Bar(x, "crop")
    B.cut_long_bar(bar, 8)                      # 5 quarters in a 4/4 bar
    assert [e.findtext("duration") for e in bar.items] == ["2", "6", "6", "8", "8"]
    assert bar.items[1].find("type") is None


def test_voice_after_another_voice_without_backup_rewinds_in_a_long_bar():
    from lxml import etree
    from omrbench.pipeline import bars as B

    def n(step, dur, voice, staff):
        return etree.fromstring(f"<note><pitch><step>{step}</step><octave>4</octave></pitch><duration>{dur}"
                                f"</duration><voice>{voice}</voice><staff>{staff}</staff></note>")
    bar = B.Bar([n("C", 6, 5, 2), n("E", 3, 1, 1), n("F", 3, 1, 1)], "crop", staves=2)
    B.rewind_voices(bar, 6)                     # 3/4: voice 1 starts at the bar start, not after voice 5
    assert [(e.tag, e.findtext("duration")) for e in bar.items] == [
        ("note", "6"), ("backup", "6"), ("note", "3"), ("note", "3")]
    ok = B.Bar([n("C", 3, 1, 1), n("E", 3, 2, 1)], "crop")
    B.rewind_voices(ok, 6)                      # a voice change mid-bar that fits stays
    assert len(ok.items) == 2


def test_long_bar_of_equal_notes_loses_its_last_notes():
    from lxml import etree
    from omrbench.pipeline import bars as B
    bar = B.Bar([etree.fromstring(f"<note><pitch><step>E</step><octave>3</octave></pitch><duration>2</duration>"
                                  f"<voice>1</voice></note>") for _ in range(4)], "crop")
    while B.cut_long_bar(bar, 4):               # 4 quarters in a 2/4 bar
        pass
    assert [e.findtext("duration") for e in bar.items] == ["2", "2"]


def test_staff_of_rests_keeps_one_full_bar_rest():
    from lxml import etree
    from omrbench.pipeline import bars as B

    def r(d, v):
        return etree.fromstring(f"<note><rest/><duration>{d}</duration><voice>{v}</voice></note>")
    bar = B.Bar([r(8, 1), etree.fromstring("<backup><duration>8</duration></backup>"),
                 r(2, 2), r(2, 2), r(4, 2)], "crop")
    B.fit_measure_rests(bar, 8)                 # 4/4: a whole rest and a voice of 1 + 1 + 2 quarters of rests
    assert [(e.tag, e.findtext("duration")) for e in bar.items] == [("note", "8")]
    assert bar.items[0].find("rest").get("measure") == "yes"


def test_bar_of_rests_on_two_interleaved_staves_gets_one_measure_rest_each():
    from lxml import etree
    from omrbench.pipeline import bars as B
    x = [etree.fromstring(s) for s in (
        "<note><rest/><duration>4</duration><voice>1</voice><staff>1</staff></note>",
        "<backup><duration>4</duration></backup>",
        "<note><rest/><duration>4</duration><voice>5</voice><staff>2</staff></note>",
        "<note><rest/><duration>4</duration><voice>1</voice><staff>1</staff></note>",
        "<backup><duration>4</duration></backup>",
        "<note><rest/><duration>4</duration><voice>5</voice><staff>2</staff></note>")]
    bar = B.Bar(x, "crop", staves=2)
    B.fit_measure_rests(bar, 8)
    assert [(e.tag, e.findtext("duration"), e.findtext("staff")) for e in bar.items] == [
        ("note", "8", "1"), ("backup", "8", None), ("note", "8", "2")]


def test_hairpins_hang_on_the_nearest_note():
    from lxml import etree
    from omrbench.pipeline import bars as B

    def n(d):
        return etree.fromstring(f"<note><pitch><step>C</step><octave>4</octave></pitch>"
                                f"<duration>{d}</duration><voice>1</voice></note>")
    bar = B.Bar([n(2), n(2), n(4)], "crop")
    B.add_direction(bar, etree.fromstring('<direction><direction-type><wedge type="crescendo"/>'
                                          '</direction-type></direction>'), 1, None)
    B.add_direction(bar, etree.fromstring('<direction><direction-type><wedge type="stop"/>'
                                          '</direction-type></direction>'), 7, None)
    B.attach_wedges(bar)                        # start at 1 -> the note at 0 or 2, stop at 7 -> bar end
    assert [e.tag if e.tag == "note" else e.find("direction-type/wedge").get("type") for e in bar.items] == \
        ["crescendo", "note", "note", "note", "stop"]
    assert not any(e.find("offset") is not None for e in bar.items)


def test_song_override_and_unpitched_sound():
    from lxml import etree
    from omrbench.musicxml import set_sounds
    from omrbench.project import part_meta, under
    show = under({"songs": {"5": {"Cymbal": {"sound": "metal.cymbal.crash", "ms_name": "Suspended Cymbal"}}}},
                 {"instruments": {"Cymbal": {"sound": "metal.cymbal.splash"}, "Glock": {"sound": "g"}}})
    row = {"file": "Drums", "pages": "1", "skip": "", "instruments": "Cymbal, Glock", "extra": "type: drums"}
    assert part_meta(row, show, {"song": "1"})["instruments"][0]["sound"] == "metal.cymbal.splash"
    cym = part_meta(row, show, {"song": "5"})["instruments"][0]
    assert cym["sound"] == "metal.cymbal.crash" and cym["ms_name"] == "Suspended Cymbal"
    root = etree.fromstring(
        "<score-partwise><part-list><score-part id='P1'><part-name>Cymbal</part-name></score-part></part-list>"
        "<part id='P1'><measure><note><unpitched><display-step>E</display-step><display-octave>4"
        "</display-octave></unpitched><duration>4</duration><voice>1</voice></note></measure></part>"
        "</score-partwise>")
    assert set_sounds(root, {"Cymbal": cym}) == 1
    assert root.findtext(".//score-instrument/instrument-name") == "Suspended Cymbal"
    assert root.findtext(".//midi-instrument/midi-unpitched") == "58"
    assert [c.tag for c in root.find(".//note")][2] == "instrument"


def test_hide_empty_staves(tmp_path):
    import zipfile
    from omrbench.transcribe import hide_empty_staves
    f = tmp_path / "x.mscz"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("x.mscx", "<Score>\n  <Part id=\"1\">\n    <trackName>A</trackName>\n    <Instrument/>\n  </Part>\n"
                             "  <Part id=\"2\">\n    <trackName>B</trackName>\n  </Part>\n</Score>\n")
        z.writestr("score_style.mss", "<Style>\n  <hideEmptyStaves>1</hideEmptyStaves>\n    </Style>\n")
    assert hide_empty_staves(f) == 2
    assert hide_empty_staves(f) == 0       # once only
    with zipfile.ZipFile(f) as z:
        mscx, mss = z.read("x.mscx").decode(), z.read("score_style.mss").decode()
    assert mscx.count("<hideWhenEmpty>on</hideWhenEmpty>") == 2
    assert "<hideEmptyStaves>0<" in mss and "<dontHideStavesInFirstSystem>1<" in mss
