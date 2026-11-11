"""homr >= 0.7.1 output brought back to the printed staff, and bars with a part-bar second voice."""
from lxml import etree

from omrbench.pipeline import bars as B

NOTE = "<note><pitch><step>C</step><octave>4</octave></pitch><duration>{d}</duration><voice>{v}</voice></note>"
REST = '<note><rest measure="yes"/><duration>4</duration><voice>1</voice></note>'


def _part(*measures: str) -> etree._Element:
    return etree.fromstring("<part>" + "".join(f"<measure>{m}</measure>" for m in measures) + "</part>")


def test_estimated_time_dropped_printed_time_kept():
    est = _part("<attributes><divisions>1</divisions><time><beats>3</beats><beat-type>4</beat-type></time></attributes>"
                "<attributes><clef><sign>G</sign><line>2</line></clef></attributes>" + NOTE.format(d=3, v=1))
    B.homr_as_printed(est)
    assert B.part_bars(est, 1, "crop")[0].time is None
    printed = _part("<attributes><divisions>1</divisions></attributes><attributes><clef><sign>G</sign><line>2</line></clef>"
                    "<time><beats>3</beats><beat-type>4</beat-type></time></attributes>" + NOTE.format(d=3, v=1))
    B.homr_as_printed(printed)
    assert B.part_bars(printed, 1, "crop")[0].time == ("3", "4")


def test_multirest_is_one_bar():
    mr = "<attributes><measure-style><multiple-rest>3</multiple-rest></measure-style></attributes>"
    part = _part("<attributes><divisions>1</divisions></attributes>" + mr + REST, REST, REST, REST,
                 NOTE.format(d=4, v=1))
    B.homr_as_printed(part)
    bars = B.part_bars(part, 1, "crop")
    assert [b.multirest for b in bars] == [3, 0, 0]       # the 4th measure is a printed rest bar


def test_empty_measure_before_repeat_start_is_no_bar():
    part = _part("<attributes><divisions>1</divisions></attributes><attributes><key><fifths>-3</fifths></key></attributes>",
                 '<barline location="right"><repeat direction="forward"/></barline>' + NOTE.format(d=4, v=1),
                 NOTE.format(d=4, v=1))
    B.homr_as_printed(part)
    bars = B.part_bars(part, 1, "crop")
    assert len(bars) == 2 and bars[0].key == "-3" and "repeat-start" in bars[0].barlines


def test_side_voice_inside_the_bar():
    def bar(xml: str) -> B.Bar:
        return B.part_bars(_part("<attributes><divisions>1</divisions></attributes>" + xml), 1, "crop")[0]
    side = bar(NOTE.format(d=2, v=1) + NOTE.format(d=2, v=1) + "<backup><duration>2</duration></backup>" + NOTE.format(d=2, v=2))
    assert not B.bar_ok(side, 4) and B.bar_ok(side, 4, side_voices=True)
    past_end = bar(NOTE.format(d=4, v=1) + "<backup><duration>1</duration></backup>" + NOTE.format(d=2, v=2))
    assert not B.bar_ok(past_end, 4, side_voices=True)
    short = bar(NOTE.format(d=2, v=1))
    assert not B.bar_ok(short, 4, side_voices=True)
