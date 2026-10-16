# Truth deviations to check

Places where a truth score seems to differ from the printed parts. Each one is either a deliberate convention
(then the pipeline may copy it, and the entry says so) or a mistake in the truth. Check and mark each entry; add
new ones whenever a benchmark shows something odd. Fixed entries are removed (last cleanup 2026-10-16); parts not
corrected yet are in the workbook column `unfinished` (`docs/PLAN.md` section 5), not here.

Status: `open` = not checked yet, `convention` = intended, keep (pipeline follows it).

## Ghost

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 20 | Drums | 1, 41 | "Open H.H." | every hi-hat note is Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| 20 | Utility | 3 sections | patch label "STR. ENS. (loco & 8va)", no 8va line | 8va line over staff 1, notes an octave up until "(loco)" | convention (pipeline copies it) |
| 20 | Reed, Trumpet | whole part | 16 accent glyphs in the PDF (each) | 33 / 36 accents (more than printed; e.g. on bars the PDF does not mark) | open (2026-10-16: reading the accents exactly from the PDF glyphs made Reed 20 worse by 19, so the truth has accents the page lacks) |
| 20 | Utility | 8va sections | | the truth's 8va spans hold 271 staff-1 notes, but output and truth differ by only ~115 notes an octave; check where the spans start and end | open |
| 20 | Guitar | | | 9 diamond noteheads (harmonics?) | open |
| 20 | PianoReduction | 92–106, 130–132 | chord symbols above the piano staff | none (as in all piano-reduction truths) | convention (pipeline writes none on piano reductions) |
| 13, 20 | all | e.g. 20 Drums 6, 7, 14; 13 Bass 115–129; 13 Cello 27–33, 99–105 | one- and two-bar repeat signs (%), "sim." after a marked bar | the bars written out, with the articulations of the pattern bar | convention (user 2026-10-16; pipeline writes %-bars out, copying the marks is IMPROVEMENTS #47) |
| all | all | | a curve joining two neighbouring notes of the same pitch | sometimes a slur (Ghost 13 Cello 18, Bass 7, Ghost 1a 17, Ghost 20 15, Anastasia 4 34) | convention: it is a tie (user 2026-10-16); `truth.load` turns such slurs into ties (`musicxml.slurs_to_ties`), the .mscz files stay as they are |
| 13 | Bass | 55 | single barline (the repeat starts at 56) | double barline | mistake (minor) |
| 13 | Bass | | Bass, sounding 8vb | "Elektrischer Bass", written an octave above sounding | convention (output uses `transpose: 8vb`) |

## Anastasia

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 4 | all | 132A–C | cut "-> 132C" | 132A and 132B don't exist: 211 bars (a cut to a lettered bar skips the earlier letters; a cut to a plain number keeps empty bars) | convention (pipeline follows it) |
| 1, 2, 4 | brass | | "Mute", "St. Mute", "Cup Mute", "to Cup" + cup mute, "Open", "to Mute" | "gedämpft", "offen"; "to ..." and an "Open" at the start left out | convention (pipeline translates, 2026-10-15) |
| 4 | Dmitry, Vlad | | octave as printed | an octave below the output | convention: the truth is right, the PDF is wrong (user, 2026-10-15); not visible from the PDF, error accepted |
| 4A | Drums | 1–3 | x-notes, "mallets" | a "Xylophon" part: mallets = xylophone | convention (Drums row -> Xylophon, 2026-10-15) |
| 1, 2, 4 | singers | | apostrophes `'` | typographic `‘` (we‘re, don‘t) | convention: the metric treats typographic and plain quotes as the same (user 2026-10-16) |
