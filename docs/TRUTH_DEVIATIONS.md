# Truth deviations to check

Places where a truth score seems to differ from the printed parts. Each one is either a deliberate convention
(then the pipeline may copy it, and the entry says so) or a mistake in the truth. Check and mark each entry; add
new ones whenever a benchmark shows something odd.

Status: `open` = not checked yet, `convention` = intended, keep (pipeline follows it), `fixed` = truth corrected.

## Ghost

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 20 | Drums | 1, 41 | "Open H.H." | every hi-hat note is Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| 20 | Utility | 3 sections | patch label "STR. ENS. (loco & 8va)", no 8va line | 8va line over staff 1, notes an octave up until "(loco)" | convention (pipeline copies it) |
| 20 | Utility | 8va sections | | the truth's 8va spans hold 271 staff-1 notes, but output and truth differ by only ~115 notes an octave; check where the spans start and end | open |
| 20 | Guitar | | | 9 diamond noteheads (harmonics?) | open |
| 20 | PianoReduction | 92–106, 130–132 | chord symbols above the piano staff | none (as in all piano-reduction truths) | convention (pipeline writes none on piano reductions) |
| 20 | Drums | 6, 7, 14, 15, ... | one- and two-bar repeat signs (%), "sim." | the repeated bars written out | convention (pipeline copies them) |
| 20 | Voice 1, Voice 2 | | | not finished (`unfinished` in the workbook) | open |
| 13 | Bass, Cello | | singer cue lines ("SAM: ...", "W'ALLACE:"), "Vamp until ...", "Then ON to m. 60" | kept as words (Anastasia truths drop dialogue / cue lines; the pipeline drops them) | open: keep them in Ghost? |
| 13 | Bass, Cello | | | part named "Voice" in both files (bench names them Bass / Cello from the file name) | convention |

## Anastasia

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 4 | all | 132A–C | cut "-> 132C" | 132A and 132B don't exist: 211 bars (a cut to a lettered bar skips the earlier letters; a cut to a plain number keeps empty bars) | convention (pipeline follows it) |
| 4 | Trumpet (Trompete in B), Trombone (Posaune) | | the reader finds ~285 / ~298 articulations (Horn: 319, its truth 333) | 72 / 122 articulations | open (truth incomplete? ~320 actions) |
| 1, 2, 4 | brass | | "Mute", "St. Mute", "Cup Mute", "Open", "to Mute" | "gedämpft", "offen"; "to ..." and an "Open" at the start left out | convention (pipeline translates, 2026-10-15) |
| 1 | Trombone | 11–20 | "to Cup", then a cup mute | "gedämpft" | convention (Cup -> gedämpft) |
| 4 | Cello | 199 | "arco" | "arco" here, "Arco" everywhere else | open (harmless: the metric ignores case) |
| 4 | Dmitry, Vlad | | octave as printed | an octave below the output | convention: the truth is right, the PDF is wrong (user, 2026-10-15); not visible from the PDF, error accepted |
| 4 | Reed 2, Reed 3, Keyboard 2, percussion | | | empty (not scored) | open |
| 4A | Drums | 1–3 | x-notes, "mallets" | a "Xylophon" part: mallets = xylophone | convention (Drums row -> Xylophon, 2026-10-15) |
| 2 | PianoReduction | | | Klavierauszug not corrected yet | `unfinished` in the workbook |
