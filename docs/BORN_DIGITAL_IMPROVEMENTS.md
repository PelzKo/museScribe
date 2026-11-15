# Born-digital improvements: what the PDF itself says, and what the pipeline does not read yet

Backlog for the born-digital books only: all Ghost books (Finale export, fonts `EngraverFontSet`, `Maestro`,
`MaestroPercussion`, text in Times New Roman) and the Anastasia `PianoReduction` (font `Petrucci`, lyrics
`FinaleLyrics`). Written 2026-11-15 on the state `r69-a` (Ghost 2 349 actions; Anastasia singers 864, the only scored
parts of the Anastasia reduction). Built like `docs/IMPROVEMENTS.md`; items there that this file replaces or sharpens
are named (D1, K2, K9, S1, S5, P2, M1-M4).

Goal (user 2026-11-15): on pages that carry the information, take it out of the file (glyph codes, vector drawings,
text layer), not through homr, Audiveris or Tesseract. Scanned pages are not touched by anything here.

**Everything below was probed, nothing was benched and nothing in the pipeline was changed.** The probe reads the
page, puts every item into its truth bar and compares with truth and with the `r69-a` output. Numbers are
**differences** (one per missing or made-up item in a bar), not actions. Three limits of the probe:
- The page bars are aligned to the **truth** bars by note counts. The pipeline will place by its own bars, so bar
  errors of the output (Ghost bars 110 actions) stay.
- "bar level" = the token is in the right bar; "onset level" = also on the right beat, counted only in bars whose
  rhythm the probe could read.
- It is first-try code (`results/errors/2026-11-15-vector/`, section 7). Where it loses against the output this
  says little; where it wins the gain is real.

## 1. Rules

The acceptance rule of `docs/IMPROVEMENTS.md` section 1 holds for every item. Two more for this file:
1. A vector reader runs only on pages `pdfkind.classify_page` calls `vector`, and only for fonts it has a table for
   (`vector.GLYPHS`). Another show with another music font gets nothing until its table exists.
2. A vector reading replaces a reader's result only where it is complete (a bar whose durations fill the bar, a mark
   with a head to hang on). Otherwise the reader's result stays. This rule made the slash and drum readers safe.

## 2. Where to start (ranked)

In scope: 3 213 actions (Ghost 2 349 + Anastasia singers 864).

| rank | item | probe result | expected (actions) | effort |
|---|---|---|---|---|
| 1 | B1 notes of two-staff parts from the glyphs | piano reductions: 378 -> 95 differences on the 85 % of staff bars read; Utility 109 -> 17 (octave-free) | -200..-300 | large |
| 2 | B2 "sim." on two-staff parts | Ghost 5 Piano / Electric Piano bars 14-22: 108 articulations the page does not print | -80..-100 (diagnose first) | small |
| 3 | B3 dynamics from the glyphs | 119 -> 51 (bar level), 12 of the 51 are truth errors | -65..-80 | small |
| 4 | B4 text classes from font, size and box | exact strings; 55 made-up and 50 missing words listed | -60..-90 | medium |
| 5 | B5 hairpins from the two-line path | 60 -> 14 (bar level), 57 -> 28 (start beat) | -40..-50 | small |
| 6 | B6 articulations of the singers (Anastasia) | 82 -> 42 (bar level) | -30..-40 | small |
| 7 | B7 barline types | reader is exact; gain only after the truth fix TB2 | 0 now, -50 after TB2 | small |
| 8 | B8 tremolos | 12 -> 1 | -11 | tiny |

Together about -500..-650 of 3 213. Suggested order: B3 -> B5 -> B8 (small, one shared glyph / drawing pass) -> B2 ->
B4 -> B1 -> B6. TB1-TB3 (user) in parallel; B7 after TB2.

## 3. Open items

"Expected" is an estimate in actions against `r69-a`.

### Truth and data (user)

Found by the probe: the page and the truth disagree, and the page is exact. Lists with every bar:
`results/errors/2026-11-15-vector/ghost-dynamics.txt`, `ghost-barlines.txt`.

| # | item | count | note |
|---|---|---|---|
| TB1 | Ghost 20 Violin and Violoncello: truth has `f` in bars 7, 13, 15, 52, 58, 60. The page prints an up-bow there and no dynamic (the figure of bar 5, which has the `f`, repeats: copied bars?) | 12 | checked on the page for Violin bar 7 |
| TB2 | Printed double barlines the truth lacks: Ghost 20 bars 4, 49, 65, 74, 99, 123, 130 in 7 to 8 parts each; Ghost 1a bar 8 (3 parts). The output has 4 of the 7 (vote R1) and is charged for them. Other way round: Ghost 4 bar 43 has a double barline in the truth of 5 parts, the page a single one | 53 + 3; 5 | same kind as T3 of IMPROVEMENTS |
| TB3 | Printed dynamics the truth lacks (full-size glyph in the part's own staff): Ghost 20 bar 1 `f` (Bass, Guitar, Piano), bar 100 `mf` (Violoncello, Guitar, Piano, Electric Piano), Trumpet 25 / 70 `f`, Guitar 92 `mp`, Electric Piano 5 / 115 `f`, Piano 29 / 50 / 110 `f`, Drum Kit 1 / 46 / 74 `f`; Ghost 4 Klavier 1 / 16 `mp`; Ghost 5 Guitar 17, Piano 8, Electric Piano 7 `f`; Ghost 1a Clarinet 17, Piano 9 `p`; Ghost 11a Bass 6, Piano 6 `mp` | about 28 | some may be a neighbour bar or a deliberate omission: check on the page |
| TB4 | Ghost 4 / 5 / 20 final bar: the page ends with a single barline (segue), truth and output write a final barline | 0 | convention, both agree; listed so nobody "fixes" it from the drawing |

### Notes

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| B1 | **Notes of two-staff parts from the glyphs (replaces K2, K9).** Heads are `EngraverFontSet` characters (`œ` `Ï` black, `˙` `ú` half, `w` whole), the head's origin y is its centre, so the staff position is exact. Value: stem (stroked line 0.5-1.0 pt) -> beams (filled polygons at its free end) or flags (`j` `J` = 1, `r` `R` = 2) -> dot (`.` right of the head). Rests are glyphs (`Œ` `Î` 1, `‰` `ä` 1/2, `≈` `Å` 1/4, `Ó` `î` 2, `∑` `·` whole bar). Onsets: the columns in x order when their values fill the bar, else stems up / down as two voices. Pitch: clef glyph left of the head, key from the workbook, accidental glyph left of the head, held through the bar and over a tie into the next bar. `vector.read_drum_page` already does all of this for drum staves | Rhythm fills the bar in **1 882 of 2 025** staff bars with notes (93 %) at the first try. Piano reductions (5 songs): 449 of 530 staff bars read; on those, note differences (onset, pitch, value) **378 -> 95**; staff bars exactly right 361 -> 432. Utility: 287 of 328 read, 109 -> 17 when octaves are ignored (with octaves 573: the 8va lines and patch octaves of #9 must be applied to the vector notes too). Single-staff parts: 73 -> 60, the readers are right there already (pitch 43 -> 26 of 4 172 notes). The tie rule alone took the piano reductions' pitch differences from 376 to 268 | **-200..-300** (Ghost pianos 352 + Utility 156 note actions; their ties and articulations come with a right bar) | large: a `read_note_page` beside `read_drum_page`, then `place_notes` like `place_slashes` (only bars that fill) |
| B1a | What B1 does not read yet: tuplets (the digit is an `EngraverTextT` character at 10 pt, the bracket a stroked path of two lines), two voices that share stems, chords of a whole and a stemmed note, cross-staff beams, cue-size heads (kept in the reductions, dropped in the parts), grace notes (`œ` at 12 pt with flag `r`) | 81 unread staff bars in the reductions, 41 in Utility | part of B1 | |
| B1b | Clef and octave from the glyphs (K3): clef glyphs `&` `?` `B` `V` (treble 8vb) at any size, octave signs `√` 8va, `◊` / `×` 8vb | used inside the probe, not measured on its own; Ghost clef differences 49 | -20..-40 | small, with B1 |
| B9 | **Singers' notes from the vocal staves** (Anastasia and Ghost reductions). Same reader, per vocal staff | Not shown. The pooled probe (all singers of a song against all vocal staves) is worse than the output, 88 -> 162 octave-free: singer routing, voices printed once and sung by two parts, cue staves, tenor clef all blur it. Rhythm fills the bar in 504 of 571 vocal staff bars | ? (singers notes 213 + 71) | medium: test inside the pipeline, per staff, after routing |

### Dynamics, hairpins, tremolos (first priority of the user)

Ghost has 128 dynamics and 65 hairpin actions; `vector.py` reads neither today (D1).

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| B3 | **Dynamics from the glyphs (D1, first half).** `EngraverFontSet`: `p`, `P` mp, `F` mf, `f`, `ƒ` / `Ä` ff, `π` / `¹` pp, `Í` fp, `§` sfz. `Petrucci`: the same plus `ß` sfz, `Z` fz, `Ï` fff, `ç` sffz. Compound dynamics are one glyph. In `EngraverFontSet` `ß` is accent + staccato (already read), not sfz. Rules that came out of the probe: only the exact font; a glyph below 0.8 of the page's head size is a cue dynamic (drop in parts: Ghost 11a bar 1, all parts); between the two staves of a keyboard -> staff 1; beat = the nearest head column. A glyph dynamic must never be dropped as "lone" (R42) | Bar level, all 40 Ghost books with a truth: truth 176; output wrong **119**, glyphs wrong **51**. By kind of book: parts 74 -> 31, drums 23 -> 5, Utility 7 -> 4, reductions 15 -> 11. Onset level: 101 -> 58. Of the 51: 12 are TB1, about 28 are TB3 (printed, truth lacks), the rest a neighbour bar or a vocal-staff dynamic in a reduction | **-65..-80** | small: a `read_dynamics` next to `read_marks`, placed like R54 but first |
| B5 | **Hairpins from the drawing (D1, second half).** A hairpin is one stroked path of two lines that share the point: `<` crescendo, `>` diminuendo; start and end x are exact, so the stop note comes with it (M2, D7) | Bar level: truth 76; output wrong **60**, drawing wrong **14**. Parts 42 -> 4. Start beat: 57 -> 28. Not found: Ghost 5 bar 35 crescendo in four parts and Drum Kit 35-42 (another drawing form or a written "cresc."; look at the page) | **-40..-50** | small |
| B8 | **Tremolos (P2 on vector pages).** Three strokes are the glyph `æ` (`¾` at cue size) on the stem | truth 17; output wrong 12, glyphs wrong 1 | -11 | tiny |

### Articulations

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| B2 | **"sim." on two-staff parts.** Ghost 5 Piano bars 14-22 have 8 marks each in the truth (accent + staccato), the page prints none and the output writes none; Electric Piano gets half. The page has "sim." under staff 2 in bar 8 and bar 11. `apply_sim` (#47, R52) works on single-staff parts | 72 + 36 = 108 of the 208 articulation differences on Ghost keyboards | -80..-100 | small; diagnose which staff / voice the copy misses |
| B6 | **Articulations of the singers from the glyphs.** `place_marks` (R5) covers only staves where onset count = head columns; the vocal staves of the Anastasia reduction (`Petrucci`: `>` `^` `-` `.` `˘` `ﬂ`) gain | Anastasia singers pooled, bar level: truth 93; output wrong 82, glyphs wrong 42 | -30..-40 (singers articulations 87) | small: add the `Petrucci` table to `vector.MARKS`, check the font test in `read_marks` |
| B10 | Glyph articulations on the Ghost keyboards as they are: no gain. Reductions 128 -> 132, Utility 80 -> 151 with the probe; the output already uses the glyphs. What is left is B2 and marks more than 4.5 spaces from the head (Ghost 5: accent + staccato far below the staff) | | 0 | - |

### Text layer

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| B4 | **Class of a text from font, size and box, string from the text layer.** Today most words come from OCR and regex. In the Ghost books the class is printed: Bold 12 in a box, one letter = rehearsal mark; Bold 12 = tempo / system text ("Driving", "Vamp", "Segue to #6"); Bold 10 in a box = patch label of the Utility book ("STR. ENS. (loco & 8va)"); Bold 10 = stage cue or vamp instruction ("(WILLIE pulls out gun)", "On to m. 8"); Regular 10 = playing word ("pizz.", "ride", "cr. cym. soft mallets") or a quoted dialogue line; Italic 10 = expression ("sim.", "dim.", "solo"); Bold Italic 12 = "sub."; Italic 8 at a system start = bar number; Regular 12 number = page number; Regular 7 / Bold 7 = cue lyric / cue speaker | Ghost words 105 actions. Made up today: vamp instructions 13 ("on to m. 8"), stage cues and dialogue 9, OCR spellings 8 ("paco' accel.", "(ﬁngelpieking)", "er. cym.", "il5 str. ens.", "submp"), patch labels 11. Missing: playing words about 20 ("ride" 4, "pizz." / "arco", "fade out", "sub."), instrument changes 17 words + 24 `instrument` items (truth writes the patch label as "zu Streichinstrumente" with an instrument change: a name table in `data/ghost/show.yaml`), rehearsal letters 13 made up. The run log shows page numbers taken for bar numbers on every book ("printed bar number 2 at page 2 ... ignored") | **-60..-90** (words, instruments, rehearsal, system text) | medium: `text.classify` gets the font class of vector pages; table per show |
| B11 | Chord symbols: already from the text layer (#11). Left: beat of the symbol (34), Ghost 4 Klavier, T5. Not probed again | S5 | see S5 | - |
| B12 | Lyrics: done (R66, R69, U5). Not probed again | | | - |

### Structure

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| B7 | **Barline types from the line cluster (S1).** Two thin lines 2.5 pt apart = double; a stroke 2.5 pt wide = thick; repeat = thick line + two `.` glyphs in the staff, left of it = end, right of it = start | The reader is exact, but with today's truths it gains nothing: Ghost barlines bar level, output wrong 105, drawing wrong 109, because 56 printed doubles are missing in the truths (TB2). Repeats: the vote (R1, R47) is right already (output wrong 20, most are vamps the truth writes without signs) | 0 now; about -50 once TB2 is fixed | small |
| B13 | **Bar boxes and bar numbers from the drawing, for placing.** `plan.xs` is not kept in step with the bars `align_bars` inserts: Ghost 13 Cello, system with the 15- and 4-bar rests, the whole note printed in the box of plan bar 55 is output bar 56. Every x-based placement that runs after the alignment is one bar off there. `vector.read_systems` has the exact boxes | found while building the probe; not measured | ? (check the call order first) | small |

### Metric coverage (M1-M4): what the glyphs give

Not scored yet, so no gain today; when M1-M4 exist these are free on vector pages.

| what | glyph or drawing |
|---|---|
| Grace notes (M1) | `œ` at 12 pt (full size 20) with flag `j` / `r`; 7 on the Ghost truth pages |
| Curve ends (M2) | a slur / tie is one filled path of two curves: both end points are exact |
| Arpeggio, trill, glissando (M4) | `g` (44 on Anastasia 3-5 reduction pages), `Ÿ` / `Ù` tr, `~` wavy segment |
| Pedal (M4) | `°` Ped. (47), `*` release |
| Bowing, breath, caesura, harmonics | `≥` down-bow, `≤` up-bow (105 on the Ghost truth pages), `,`, `"`, `O` / `\|` diamond heads |
| Fermata | `U` above, `u` below (probe: no gain over the output, 24 -> 25) |

## 4. What is read from the file today

`pipeline/vector.py`: slash bars, drum-kit bars, measure repeats, printed barlines and time signatures
(`read_systems`), articulations and tie curves on staves with matching onset counts (`read_marks`), "sim." and
"Play" lines, lyric words, hyphens and melisma lines. `chords.py`: chord symbols. `scripts/pdf_truth_check.py`:
pitches, for checking truths only.

Not read: dynamics, hairpins, tremolos, pitched notes and rests, clefs, accidentals, octave signs, barline types,
text classes, bar numbers, ornaments.

## 5. Glyph tables found

`EngraverFontSet` (Ghost), from the 47 work dirs of the truth songs; `Petrucci` uses the same codes unless noted.

| kind | codes |
|---|---|
| heads | `œ` `Ï` black, `˙` `ú` half, `w` whole, `Û` `Õ` `ó` `’` slashes, `À` `¿` x, `O` `\|` diamond |
| rests | `Œ` `Î` quarter, `‰` `ä` eighth, `≈` `Å` 16th, `Ó` `î` half, `∑` `·` whole |
| flags, dots | `j` `J` eighth, `r` `R` 16th, `.` dot or staccato (by position) |
| accidentals | `b` `#` `n`, `A` (♭), `a` (♯), `N` (♮) in brackets |
| clefs | `&`, `?`, `B`, `V` treble 8vb; percussion clef is `Maestro` `ã` |
| articulations | `>` accent, `^` `¨` `¬` `²` marcato, `-` tenuto, `˘` `ﬂ` `ß` accent + staccato (`ß` is sfz in `Petrucci`) |
| dynamics | `p` `P` `F` `f` `ƒ` `Ä` `π` `¹` `Í` `§`; `Petrucci` also `ß` `Z` `Ï` `ç` |
| other | `U` `u` fermata, `æ` `¾` tremolo, `‘` `«` measure repeats, `≥` `≤` bows, `Ÿ` `Ù` `~` trill, `×` 8vb, `,` breath, `"` caesura, `o` open, `+` (`EngraverFontExtras`) closed |
| numbers | `Maestro` digits: time signatures and multi-rest counts; `EngraverTextT`: tuplet digits and the metronome note |

Drawings: staff lines and barlines are stroked lines 0.37 pt wide, stems 0.73 pt, thick barlines 2.49 pt; beams are
filled polygons; slurs and ties filled paths of two curves; hairpins and tuplet brackets stroked paths of two lines.

## 6. What did not work or is not shown

| tried | result | why |
|---|---|---|
| Slurs and ties from the curves with the probe's simple rule | slurs 175 -> 348, ties 95 -> 310 differences | the pipeline already uses the curves (R8, #46); the probe's tie / slur split is cruder. No evidence for a gain here |
| Glyph articulations on Ghost keyboards as they are | 128 -> 132, 80 -> 151 | see B10 |
| Fermatas from `U` / `u` | 24 -> 25 | the vote (R36) is about as good |
| Repeat signs from the drawing | 20 -> 49 | the probe's bar boxes are too coarse at a system start; the vote is right already |
| Singers' notes, pooled | 88 -> 162 | see B9 |
| Barline types with today's truths | 105 -> 109 | TB2 |
| Aligning page bars to the **output** bars for the probe | every region after an inserted bar is one bar off | align to the truth bars by note counts; and B13 |

## 7. Learnings and scripts

- **The class of a glyph is its code, the class of a text is its font.** No threshold, no confidence: the 119 -> 51 on
  dynamics came from a ten-entry table.
- **Size tells cue from part.** Cue heads, cue dynamics and cue lyrics are the same glyphs at 0.6-0.75 of the size.
- **A vector reading can be checked against itself.** Durations that fill the bar are right in 96 % of the staff
  bars of the reductions (432 of 449); take only those.
- **An exact reader shows truth gaps.** 12 dynamics, 56 double barlines and about 28 more dynamics are in the page
  and not in the truth (TB1-TB3); fix the truth before benching B3 and B7, or they look like losses.
- **Accidentals over a tie.** A third of the pitch differences of the first run were tied notes without a repeated
  accidental.
- **Doubling books change the transposition** (Reed): compare sounding pitch with the transposition in force.
- Traps: the probe's bar boxes come from `plan.xs` (B13); multi-rest copies share one box, so edge marks belong
  only to the first and the last copy; `ß` means two different things in the two fonts.

Scripts, all in `results/errors/2026-11-15-vector/` (not in git):

```bash
source ~/.local/share/omrbench/env.sh
V=results/errors/2026-11-15-vector
python $V/allnotes.py ghost r69-a 1a,4,5,11a,13,20 $V/ghost-items.json   # truth / output items and notes per aligned bar
python $V/vgeo.py ghost h71 1a,4,5,11a,13,20 $V/ghost-geo.json           # page boxes of the bars (reassembles h71)
python $V/vitems.py ghost                                                # glyphs and drawings -> ghost-vec.json
python $V/veval.py ghost [kind] [book type] [n]                          # tables; examples of one kind
python $V/dyn.py ghost                                                   # dynamics only, per part
```

`vread.py` holds the shared parts (bar alignment, glyph tables); `ghost-eval.txt` / `anastasia-eval.txt` the tables
behind sections 2 and 3. For Anastasia: `allnotes.py anastasia r69-a 1,2,3,4,4A,5`, `vgeo.py anastasia h71 1,2,3,4,5`,
then `vitems.py anastasia` (vocal staves of the reduction, singers pooled per song).
