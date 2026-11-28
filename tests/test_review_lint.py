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


def test_tempo_staff_text_to_one_system_text_and_cross_staff_gliss(tmp_path):
    st = lambda txt: f"<StaffText><text>{txt}</text></StaffText>"
    bars = lambda first, txt="": BAR.format(ts=TS, p=60) + BAR.format(ts="", p=62).replace("<Chord>", txt + "<Chord>")
    parts = "".join(PART.format(n=n) for n in "ABCD")
    staves = (f"<Staff id='1'>{bars(1, st('Con mosso (In 1)'))}</Staff>"
              f"<Staff id='2'>{bars(1, st('Con mosso (In 1))'))}</Staff>"
              f"<Staff id='3'>{bars(1, st('con mosso (in 1)'))}</Staff>"
              f"<Staff id='4'>{bars(1, st('pizz.'))}</Staff>")
    f = tmp_path / "t.mscx"
    f.write_text(f"<museScore><Score>{parts}{staves}</Score></museScore>")
    out = L.lint(f)
    assert '2: [text] "Con mosso (In 1)" as staff text in 3 parts at bar 2' in out and "pizz" not in out
    L.lint(f, fix_safe=True)
    xml = f.read_text()
    assert xml.count("Con mosso") == 1 and "<SystemText><text>Con mosso (In 1)</text>" in xml and "pizz." in xml
    # a glissando from staff 2 to staff 1 of one keyboard part: both halves found, no finding
    kb = PART.replace("<Staff/>", "<Staff/><Staff/>").replace("strings.violin", "keyboard.piano")
    g1 = ('<Spanner type="Glissando"><prev><location><staves>1</staves></location></prev></Spanner>')
    g2 = ('<Spanner type="Glissando"><Glissando><subtype>1</subtype></Glissando><next><location><staves>-1</staves>'
          '</location></next></Spanner>')
    b1 = BAR.format(ts=TS, p=72).replace("<pitch>", g1 + "<pitch>")
    b2 = BAR.format(ts=TS, p=48).replace("<pitch>", g2 + "<pitch>")
    f.write_text(f"<museScore><Score>{kb.format(n='K')}<Staff id='1'>{b1}</Staff><Staff id='2'>{b2}</Staff>"
                 "</Score></museScore>")
    assert "[span]" not in L.lint(f)
    f.write_text(f.read_text().replace(g1, ""))
    assert "cross-staff Glissando start without its partner on staff 1" in L.lint(f)
