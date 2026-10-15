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

## Anastasia

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 4 | all | | 213 bars expected (206 + lettered bars) | 217 bars | open |
| 4 | Trumpet (Trompete in B), Trombone (Posaune) | | the reader finds ~285 / ~298 articulations (Horn: 319, its truth 333) | 72 / 122 articulations | open (truth incomplete? ~320 actions) |
| 4 | Dmitry, Vlad | | | an octave below the output (tenor / baritone clef reading) | open |
| 4 | Reed 2, Reed 3, Keyboard 2, percussion | | | empty (not scored) | open |
| 4A | Drums | | drum-set x-notes | written in a "Xylophon" part as a placeholder | convention |
| 2 | PianoReduction | | | Klavierauszug empty (not annotated) | open |
