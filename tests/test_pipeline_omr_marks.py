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
