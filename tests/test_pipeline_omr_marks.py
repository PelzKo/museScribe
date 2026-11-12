import xml.etree.ElementTree as ET

from omrbench.pipeline import bars as B
from omrbench.pipeline.assemble import SysPlan, repeat_dots
from omrbench.pipeline.layout import Page, Staff, Stack, System, _parse_sheet

SHEET = """<sheet><picture width="1000" height="500"/>
  <barline id="4" shape="THIN_BARLINE" staff="1"><bounds x="400" y="0" w="3" h="80"/></barline>
  <barline id="5" shape="THIN_BARLINE" staff="1"><bounds x="700" y="0" w="3" h="80"/></barline>
  <repeat-dot id="10" staff="1"><bounds x="390" y="30" w="8" h="7"/></repeat-dot>
  <repeat-dot id="11" staff="1"><bounds x="710" y="30" w="8" h="7"/></repeat-dot>
  <sig><relations>
    <relation source="10" target="4"><repeat-dot-bar/></relation>
    <relation source="11" target="5"><repeat-dot-bar/></relation>
  </relations></sig></sheet>"""


def test_repeat_dots_give_repeat_signs():
    page = _parse_sheet(ET.fromstring(SHEET), 1)
    assert page.repeats == [(1, 394.0, "repeat-end"), (1, 714.0, "repeat-start")]
    sy = System(1, 1, [Staff(1, 0, 0, 80, 100, 1000)], [Stack(1, 100, 400), Stack(2, 400, 700), Stack(3, 700, 1000)])
    plan = SysPlan(sy, 0, 3, [(100, 400), (400, 700), (700, 1000)])
    plan.chosen = {0: [B.Bar([], "crop") for _ in range(3)]}
    page.systems = [sy]
    repeat_dots([plan], [page])
    assert [set(b.barlines) for b in plan.chosen[0]] == [{"repeat-end"}, set(), {"repeat-start"}]


ARTS_SHEET = """<sheet><picture width="1000" height="500"/>
  <head-chord id="20" staff="1"><bounds x="296" y="20" w="12" h="40"/></head-chord>
  <articulation id="21" shape="ACCENT" ctx-grade="0.9"><bounds x="296" y="5" w="12" h="6"/></articulation>
  <sig><relations><relation source="20" target="21"><chord-articulation/></relation></relations></sig></sheet>"""


def test_place_arts_by_imgpos():
    from lxml import etree
    from omrbench.pipeline.assemble import Stats, place_arts
    page = _parse_sheet(ET.fromstring(ARTS_SHEET), 1)
    assert [(a.shape, a.staff) for a in page.arts] == [("ACCENT", 1)]
    sy = System(1, 1, [Staff(1, 0, 20, 60, 100, 1000)], [Stack(1, 100, 1000)])
    page.systems = [sy]
    plan = SysPlan(sy, 0, 1, [(100, 1000)])
    # crop left edge = staff left - 3 interlines = 70: the second note (x 232 + 70 = 302) is under the accent
    notes = [etree.fromstring(f"<note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration>"
                              f"<staff>1</staff><!-- imgpos: {x}, 40 --></note>") for x in (100, 232)]
    plan.chosen = {0: [B.Bar(notes, "crop")]}
    place_arts([plan], [page], Stats())
    assert [n.find("notations/articulations/accent") is not None for n in notes] == [False, True]
    place_arts([plan], [page], Stats())     # an onset with the mark gets no second one
    assert len(notes[1].findall("notations/articulations/accent")) == 1


DYN_SHEET = """<sheet><picture width="1000" height="500"/>
  <dynamics id="30" shape="DYNAMICS_P" ctx-grade="0.9"><bounds x="296" y="70" w="12" h="10"/></dynamics>
  <dynamics id="31" shape="DYNAMICS_F" ctx-grade="0.5"><bounds x="166" y="70" w="12" h="10"/></dynamics>
</sheet>"""


def test_place_dynamics_by_imgpos():
    from lxml import etree
    from omrbench.pipeline.assemble import Stats, place_dynamics
    page = _parse_sheet(ET.fromstring(DYN_SHEET), 1)
    sy = System(1, 1, [Staff(1, 0, 20, 60, 100, 1000)], [Stack(1, 100, 1000)])
    page.systems = [sy]
    plan = SysPlan(sy, 0, 1, [(100, 1000)])
    notes = [etree.fromstring(f"<note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration>"
                              f"<staff>1</staff><!-- imgpos: {x}, 40 --></note>") for x in (100, 232)]
    bar = B.Bar(list(notes), "crop")
    plan.chosen = {0: [bar]}
    place_dynamics([plan], [page], Stats())
    # the p (grade 0.9) goes to the second note's onset; the f (grade 0.5) is left out
    dyn = [(on, el.find("direction-type/dynamics")[0].tag) for on, el in B.onsets(bar) if el.tag == "direction"]
    assert dyn == [(1, "p")]
    place_dynamics([plan], [page], Stats())     # the bar has a dynamic now: no second one
    assert sum(el.tag == "direction" for el in bar.items) == 1


def test_positions_from_imgpos():
    from lxml import etree
    from omrbench.pipeline.vocal import _positions
    page = _parse_sheet(ET.fromstring(DYN_SHEET), 1)
    sy = System(1, 1, [Staff(1, 0, 20, 60, 100, 1000)], [Stack(1, 100, 1000)])
    plan = SysPlan(sy, 0, 1, [(100, 1000)])
    notes = [etree.fromstring(f"<note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration>"
                              f"<staff>1</staff><!-- imgpos: {x}, 40 --></note>") for x in (100, 232)]
    plan.chosen = {0: [B.Bar(notes, "crop")]}
    # homr's x plus the crop's left edge (staff left 100 - 3 interlines = 70), not spread over the bar
    assert [(x, on) for x, on, _ in _positions(plan, 0, 0, sy.staves, page, 1)] == [(170, 0), (302, 1)]
