from fractions import Fraction as F

from omrbench.pipeline import assemble as A
from omrbench.pipeline import bars as B
from omrbench.pipeline import vector as SL


def test_slash_bar_rhythm_ties_and_kept_directions():
    old = B.rest_bar(1, 8, 2)
    from lxml import etree
    old.items.insert(0, etree.fromstring("<harmony><root><root-step>F</root-step></root><kind>major</kind></harmony>"))
    sb = SL.SlashBar(1, 0, 100, 0, 20, [SL.Event(0, "rest", F(1)), SL.Event(10, "slash", F(3, 2)),
                                        SL.Event(20, "slash", F(1, 2), tie_start=True),
                                        SL.Event(30, "slash", F(1), tie_stop=True)])
    assert sb.length == 4
    bar = A.slash_bar(sb, old, 2)
    notes = bar.notes()
    assert bar.items[0].tag == "harmony" and len(notes) == 4
    assert [n.findtext("duration") for n in notes] == ["2", "3", "1", "2"]
    assert notes[1].findtext("type") == "quarter" and notes[1].find("dot") is not None
    assert notes[1].findtext("notehead") == "slash" and notes[0].find("rest") is not None
    assert notes[2].find("tie").get("type") == "start" and notes[3].find("notations/tied").get("type") == "stop"
    assert A.slash_bar(SL.SlashBar(1, 0, 1, 0, 1, [SL.Event(0, "slash", F(5, 4))]), old, 2) is None

