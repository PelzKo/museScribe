"""scripts/review_lint.py on a tiny two-part score: findings and the fix-safe edits."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_lint as L  # noqa: E402

BAR = ("<Measure><voice>{ts}<Chord><durationType>half</durationType><dots>1</dots><Note><pitch>{p}</pitch>"
       "<tpc>14</tpc></Note></Chord></voice></Measure>")
PART = ("<Part><Staff/><trackName>{n}</trackName><Instrument><instrumentId>strings.violin</instrumentId>"
        "<minPitchP>55</minPitchP><maxPitchP>103</maxPitchP></Instrument></Part>")
TS = "<TimeSig><sigN>3</sigN><sigD>4</sigD></TimeSig>"


def test_lint_findings_and_fixes(tmp_path):
    s1 = BAR.format(ts=TS, p=60) + BAR.format(ts="", p=40) + (
        "<Measure><voice><Rest><durationType>measure</durationType><duration>4/4</duration></Rest></voice></Measure>")
    hp = ('<Spanner type="HairPin"><HairPin><subtype>0</subtype></HairPin><next><location><measures>1</measures>'
          '</location></next></Spanner>')
    s2 = (BAR.format(ts=TS, p=60).replace("<Chord>", hp + hp + "<Chord>")
          + BAR.format(ts="", p=62).replace("<Chord>", '<Spanner type="HairPin"><prev><location><measures>-1'
                                                       '</measures></location></prev></Spanner>' * 2 + "<Chord>")
          + BAR.format(ts="", p=64))
    xml = (f"<museScore><Score>{PART.format(n='A')}{PART.format(n='B')}<Staff id='1'>{s1}</Staff>"
           f"<Staff id='2'>{s2}</Staff></Score></museScore>")
    f = tmp_path / "s.mscx"
    f.write_text(xml)
    out = L.lint(f)
    assert "2: [range]" in out and "3: [length] voice 1: whole-bar rest of 4/4" in out
    assert "1: [span] two identical hairpins  [fix-safe]" in out
    L.lint(f, fix_safe=True)
    again = L.lint(f)
    assert "[length]" not in again and "[span]" not in again and "[range]" in again
