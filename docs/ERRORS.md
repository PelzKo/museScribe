# Error overview: output vs truth

What is still wrong in the pipeline output, element by element, with no weighting. A basis for the next
improvement round. State: reference outputs `p1` (`results/<show>/runs/p1`, default `pipeline`), truths as of
2026-10-15 (Ghost 13 with the dialogue / vamp text removed). 88 truth parts, 24 024 truth notes, 6 + 1 songs
(Anastasia 1, 2, 4, 4A; Ghost 1a, 13, 20).

Made with `python scripts/error_report.py anastasia,ghost --run p1` (about 30 s; writes `results/errors/p1/errors.md`
and `errors.json` with every location). Pairing, `plain` parts and `unfinished` parts are the same as in
`omrbench bench`. Bars are aligned like the edit penalty (DP over bars, whole-part transposition, octave
sections). Inside every matched bar each note and each marking is compared one to one, and every difference is
counted under a kind. One note can count several times: a Bb. read as a B quarter is "accidental missing" plus
"dot missing". The counts are not the edit penalty. They say what is wrong, not what it costs.

How notes are paired inside a bar: exact match first, then the same beat and pitch (gives a rhythm error), the
same beat and length (gives a pitch error), the same pitch and length on another beat (onset shifted), the same
beat (pitch and rhythm error). The rest is missing or made up. Markings: same token on another beat = "at the
wrong beat", another token on the same beat = "wrong X instead of Y", a slur on a beat where the truth has a tie =
"tie read as a slur". Rehearsal marks, tempi and system text are compared once per song, like the penalty.

## Summary (7432 differences)

| group | total | Anastasia | Ghost | what most of it is |
|---|---|---|---|---|
| notes | 956 | 639 | 317 | missing notes: whole passages of singers (Anastasia 4 Dmitry 101–115, 169–206), Ghost 20 piano reduction, keyboard chords |
| articulations | 906 | 587 | 319 | accents / staccatos / tenutos missing on keyboards and piano reductions; staccatos made up on Ghost keyboards |
| pitch | 880 | 656 | 224 | accidentals missing or made up (a misread key in the crop, see 1), notes far below the bass staff |
| bars | 812 | 652 | 160 | whole-bar rests that are 4 beats long in 3/4 (175), missing / extra bars in Anastasia 4 singers |
| ties | 465 | 165 | 300 | missing ties (Ghost piano parts, often over a system break), ties read as slurs (138) |
| lyrics | 451 | 451 | 0 | Anastasia 4 singers: lyrics of missing notes, verse 2 instead of 1, `'` vs `‘` |
| dynamics | 399 | 329 | 70 | missing mp / mf / f / p / sfz; made-up p and f |
| barlines | 365 | 313 | 52 | double barlines never written (349) |
| words | 318 | 266 | 52 | made-up text ("solo", "div", patch names), missing "arco" / "pizz." / "gedämpft" |
| slurs | 289 | 140 | 149 | made-up slurs (150), missing slurs (113) |
| rhythm | 265 | 166 | 99 | notes at the wrong beat (102), note values x2 / x0.5 (93) |
| systemtext | 240 | 187 | 53 | words written as system text that the truth has on the part (229) |
| hairpins | 200 | 181 | 19 | crescendo / diminuendo hairpins missing (180) |
| keys | 200 | 162 | 38 | key changes one bar early / late (Anastasia 4 bars 144–176, after the lettered bars) |
| structure | 164 | 156 | 8 | repeat signs never written (forward 83, backward 81) |
| drums | 121 | 15 | 106 | Ghost 20 drum hits missing (simultaneous hits) |
| chords | 76 | 1 | 75 | Ghost guitar chord symbols one beat off, made up, missing |
| clefs | 73 | 51 | 22 | clef changes made up / missed on keyboards and piano reductions |
| times | 60 | 57 | 3 | Anastasia 4 time changes 2/4 <-> 4/4 one bar off (bars 192–197) |
| tremolos | 54 | 52 | 2 | single tremolos (3 strokes) missing on strings and cymbal |
| fermatas | 48 | 33 | 15 | missing 25, made up 22 |
| rehearsal | 34 | 0 | 34 | Ghost 13: marks in the wrong bar, J copied into seven %-bars |
| instruments | 29 | 19 | 10 | instrument changes made up (Anastasia 4 Männer) / missing (Ghost 1a) |
| tuplets | 15 | 14 | 1 | sextuplet 6:4 written as 3:2 (Anastasia 1 bar 1) |
| tempo, part, wrong staff | 12 | 7 | 5 | |

Parts with the most differences: Anastasia 4 Keyboard 1 (857), Ghost 20 Piano (634), Anastasia 4 Klavierauszug
(484), Anastasia 4 Männer (404), Dmitry (330), Frauen (319), Violine 1 (284), Ghost 20 Drum Kit (257), Ghost 20
Electric Guitar (239). The table "per part" at the end lists all 88.

## Systematic errors (what to fix next)

Ordered by how many differences one fix would remove (rough estimates from the counts below).

1. **Crop key misread, notes keep the wrong key (~450 pitch errors).** homr reads the key signature per crop
   and sometimes gets it wrong (Anastasia 4 Cello: crop s08 read as 2 sharps; its bar 32 is in 3 flats).
   The assembly writes the right key (Audiveris / song key), but the pitches stay the ones homr computed with its
   key: Ab is written as A, Bb as B (Cello bars 32, 37–38, 58–60; Keyboard 1, Violine 1 / 2, Kontrabass, Oboe in the
   same bars). Shows as "accidental missing" 334, "accidental made up" 94, "one staff step off + accidental" 25.
   Fix: where the crop's key differs from the chosen key, re-spell every note without an explicit `<accidental>`
   by the chosen key (and the accidentals carried in the bar).
2. **Whole-bar rests of the wrong length (175 bars).** A `<rest measure="yes">` taken from the crop keeps
   duration 4 quarters in 3/4 bars (Anastasia 2 Reed 3 bar 17, all brass and reeds of song 2). MuseScore
   then makes the bar 4/4 long. Fix: give every whole-bar rest the length of its bar's time signature.
3. **Double barlines (349) and repeat signs (164) are never written.** (User 2026-10-16: wanted, as printed.) Every section change in the truth has a
   light-light barline; the output has none. "Audiveris double barlines" was rejected earlier (+129), so the
   placement was the problem, not the idea. On vector pages the barline type comes straight from the PDF
   (`sheet_reader` `page_dump.get_barlines`, two strokes 2–4 pt apart = double; thick stroke = final; dots = repeat).
   On scans: double barline only where a rehearsal mark, key or time change sits at the same bar line.
4. **Ties (465).** 138 ties are read as slurs (a slur between two neighbouring notes of the same pitch is a tie);
   285 are missing, mostly in Ghost piano parts (Ghost 20 Piano 108, Electric Bass, Cello) and often over a system
   break (user report on Ghost 13). Fix: slur over two adjacent equal pitches -> tie; a tie that starts at the last
   note of a system continues to the first note of the next system when the pitch is the same.
5. **Articulations on keyboards and piano reductions (~600 missing).** Accents, staccatos and tenutos are
   missing mostly in Anastasia 4 Keyboard 1 (65 accents, 72 staccatos) and Klavierauszug (67 accents, 65 tenutos):
   homr drops articulations on dense two-staff music. Ghost 13 Cello / Bass: most missing accents and staccatos
   are on bars after "sim." (Cello 27–33, 99–105) where the truth writes the pattern's marks out (decided: the
   output does the same, IMPROVEMENTS #47).
   Made-up staccatos (136) are mostly on Ghost keyboards (Electric Piano 38, Piano 23, Drum Kit 20). On vector
   pages the glyphs are exact (see the sheet_reader section: Ghost 13 Cello marcatos 42 in the PDF = 42 in the truth,
   the pipeline has 26).
6. **Notes far below the bass staff.** Low notes with many ledger lines (Anastasia 4 Keyboard 1 bars 20, 23,
   65: G1 read as Cb2, C1 as F1, D2 as A2) give most of "wrong by more than a third" (221).
7. **Singers in Anastasia 4 (~1250 over Dmitry, Vlad, Männer, Frauen).** Whole passages missing (Dmitry 101–115,
   169–206 with their lyrics), Männer bars missing / extra around 42–62, Frauen with extra chord notes at 57–64
   (two voices on one staff written as chords?), lyrics in verse 2 where the truth uses verse 1 (~35), and
   instrument changes made up in Männer (19). Most of this is the singer-label routing of the piano reduction.
8. **Words and system text (~560).** 229 system texts are made up: in split-instrument books every word becomes
   system text (`assemble.py` line 924, `split or ...`), and texts like "gedämpft", "solo", "fill", "sim.",
   "Moderato, with movement" are moved to the top part as system text although the truths keep them on the part (or
   do not have them). Then words: made up "solo" ×12, "div" ×4, patch names ("str. ens. (loco)"); missing
   "arco" ×32, "pizz." ×25, "gedämpft" ×13, "offen" ×9.
9. **Hairpins (180 missing) and dynamics (~250 missing).** Crescendo hairpins are missing almost everywhere in
   Anastasia (Violine 1, Horn, Oboe, Piccolo). Dynamics: missing mp 52, mf 41, f 39, p 38, sfz 30; made up p 47,
   f 25.
10. **Key and time changes one bar off (keys 200, times 60).** Anastasia 4 strings: key changes at 144 / 148 /
   154 / 166 instead of 145 / 149 / 158 / 170, time 2/4 one bar early (192 / 193 instead of 196). These come with
   bar-count drift in the singers' and strings' bars around 128–131 (bars missing with notes, 30).
11. **Smaller ones.** Tremolos `trem:single:3` missing 49; fermatas 48; sextuplet notated 3:2 instead of 6:4 (6
   parts of Anastasia 1 bar 1); clefs on keyboards (73); Ghost guitar chord symbols one beat off (28); Ghost 20
   drums lose simultaneous hits (98); rehearsal marks: the %-bar write-out copies the rehearsal mark J into seven
   bars (Ghost 13 Bass 119–126), and both Ghost 13 outputs miss mark H.

Lyrics `'` vs `‘`: the Anastasia truths write apostrophes as `‘` (we‘re, don‘t, it‘s), the output `'` (about 15
"wrong" lyrics). Decided 2026-10-16: the metric treats them as the same (`musicxml._norm_text`).

## Full list by kind

Counts per show, the three parts with the most, and the first places (truth bar numbers; `#n` = n-th bar where
the truth bar number is not printable). Every location is in `results/errors/p1/errors.json`.

### notes (956)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note missing | 705 | anastasia 428, ghost 277 | ghost 20 Piano 130, anastasia 4 Dmitry 110, anastasia 4 Keyboard 1 88 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 1 bar 26 |
| note made up | 140 | anastasia 109, ghost 31 | anastasia 4 Keyboard 1 27, anastasia 2 Keyboard 1 12, anastasia 4 Posaune 8 | anastasia 1 Kontrabass bar 28; anastasia 1 Kontrabass bar 29 |
| chord note missing | 58 | anastasia 53, ghost 5 | anastasia 4 Keyboard 1 23, anastasia 4 Frauen 9, anastasia 4 Klavierauszug 7 | anastasia 1 Keyboard 1 bar 2; anastasia 1 Keyboard 1 bar 7 |
| extra chord note | 53 | anastasia 49, ghost 4 | anastasia 4 Frauen 34, anastasia 4 Keyboard 1 4, anastasia 4 Männer 4 | anastasia 2 Keyboard 1 bar 29; anastasia 4 Violine 2 bar 125 |

### articulations (906)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `accent` | 280 | anastasia 200, ghost 80 | anastasia 4 Klavierauszug 67, anastasia 4 Keyboard 1 65, ghost 13 Cello 28 | anastasia 1 Violine 1 bar 5; anastasia 1 Violine 1 bar 7 |
| missing `staccato` | 180 | anastasia 122, ghost 58 | anastasia 4 Keyboard 1 72, ghost 13 Cello 49, anastasia 4 Klavierauszug 31 | anastasia 4 Violine 1 bar 1; anastasia 4 Violine 1 bar 2 |
| missing `tenuto` | 145 | anastasia 139, ghost 6 | anastasia 4 Klavierauszug 65, anastasia 4A Violine 1 32, anastasia 4 Horn in F 25 | anastasia 1 Violine 1 bar 6; anastasia 1 Violine 1 bar 7 |
| made up `staccato` | 136 | ghost 95, anastasia 41 | ghost 20 Electric Piano 38, ghost 20 Piano 23, ghost 20 Drum Kit 20 | anastasia 1 Klavierauszug bar 2; anastasia 1 Klavierauszug bar 10 |
| made up `accent` | 29 | ghost 16, anastasia 13 | ghost 20 Drum Kit 8, anastasia 4 Oboe 4, anastasia 4 Keyboard 1 4 | anastasia 1 Klavierauszug bar 10; anastasia 4 Oboe bar 106 |
| missing `strong-accent` | 27 | ghost 20, anastasia 7 | ghost 13 Cello 15, anastasia 4 Klavierauszug 5, ghost 20 Trumpet in Bb 3 | anastasia 4 Violine 1 bar 81; anastasia 4 Violine 1 bar 202 |
| made up `tenuto` | 21 | anastasia 18, ghost 3 | anastasia 1 Keyboard 1 6, anastasia 1 Klavierauszug 6, anastasia 4 Oboe 2 | anastasia 1 Keyboard 1 bar 9; anastasia 1 Keyboard 2 bar 6 |
| made up `strong-accent` | 17 | ghost 14, anastasia 3 | ghost 20 Piano 12, anastasia 1 Klavierauszug 1, anastasia 2 The Dowager Empress 1 | anastasia 1 Klavierauszug bar 6; anastasia 2 The Dowager Empress bar 30 |
| at the wrong beat `staccato` | 15 | anastasia 10, ghost 5 | anastasia 4 Keyboard 1 5, anastasia 4 Klavierauszug 5, ghost 13 Cello 3 | anastasia 4 Keyboard 1 bar 89; anastasia 4 Keyboard 1 bar 98 |
| at the wrong beat `accent` | 12 | ghost 10, anastasia 2 | ghost 20 Electric Guitar 7, ghost 13 Cello 2, anastasia 4 Oboe 1 | anastasia 4 Oboe bar 43; anastasia 4 Frauen bar 62 |
| wrong `accent` instead of `tenuto` | 6 | anastasia 5, ghost 1 | anastasia 4 Klavierauszug 3, anastasia 4 Oboe 2, ghost 20 Trumpet in Bb 1 | anastasia 4 Oboe bar 113; anastasia 4 Oboe bar 142 |
| made up `caesura` | 5 | ghost 4, anastasia 1 | anastasia 2 Keyboard 1 1, ghost 20 Violoncello 1, ghost 20 Electric Bass 1 | anastasia 2 Keyboard 1 bar 29; ghost 20 Violoncello bar 5 |
| wrong `staccato` instead of `accent` | 5 | anastasia 5 | anastasia 4 Klavierauszug 3, anastasia 4 Keyboard 1 1, anastasia 4 Frauen 1 | anastasia 4 Keyboard 1 bar 73; anastasia 4 Klavierauszug bar 42 |
| wrong `staccato` instead of `tenuto` | 4 | anastasia 3, ghost 1 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 1, ghost 20 Clarinet in Bb 1 | anastasia 4 Keyboard 1 bar 92; anastasia 4 Klavierauszug bar 158 |
| missing `caesura` | 3 | anastasia 3 | anastasia 2 Flöte 1 1, anastasia 2 Keyboard 2 1, anastasia 2 Glockenspiel 1 | anastasia 2 Flöte 1 bar 29; anastasia 2 Keyboard 2 bar 29 |
| wrong `accent` instead of `strong-accent` | 3 | ghost 2, anastasia 1 | anastasia 4 Violine 1 1, ghost 13 Cello 1, ghost 20 Piano 1 | anastasia 4 Violine 1 bar 206; ghost 13 Cello bar 40 |
| missing `falloff` | 3 | anastasia 2, ghost 1 | anastasia 4 Keyboard 1 2, ghost 13 Bass 1 | anastasia 4 Keyboard 1 bar 70; anastasia 4 Keyboard 1 bar 137 |
| missing `breath-mark` | 2 | anastasia 2 | anastasia 2 The Dowager Empress 1, anastasia 4 Frauen 1 | anastasia 2 The Dowager Empress bar 24; anastasia 4 Frauen bar 73 |
| wrong `staccatissimo` instead of `staccato` | 2 | anastasia 2 | anastasia 4 Violine 1 2 | anastasia 4 Violine 1 bar 44; anastasia 4 Violine 1 bar 52 |
| at the wrong beat `tenuto` | 2 | anastasia 2 | anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 81; anastasia 4 Klavierauszug bar 159 |
| made up `staccatissimo` | 2 | anastasia 2 | anastasia 4 Klavierauszug 1, anastasia 4 Frauen 1 | anastasia 4 Klavierauszug bar 113; anastasia 4 Frauen bar 69 |
| wrong `accent` instead of `staccato` | 2 | ghost 2 | ghost 20 Clarinet in Bb 1, ghost 20 Trumpet in Bb 1 | ghost 20 Clarinet in Bb bar 90; ghost 20 Trumpet in Bb bar 90 |
| wrong `tenuto` instead of `staccato` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 172 |
| missing `scoop` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 138 |
| missing `doit` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 51 |
| wrong `strong-accent` instead of `accent` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 202 |
| made up `breath-mark` | 1 | ghost 1 | ghost 20 Electric Guitar 1 | ghost 20 Electric Guitar bar 62 |

### pitch (880)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| accidental missing | 334 | anastasia 314, ghost 20 | anastasia 4 Keyboard 1 104, anastasia 4 Violoncello 57, anastasia 4 Violine 2 46 | anastasia 1 Violine 2 bar 5; anastasia 1 Flöte 2 bar 5 |
| wrong by more than a third | 221 | anastasia 128, ghost 93 | anastasia 4 Keyboard 1 72, ghost 20 Piano 60, anastasia 4 Klavierauszug 17 | anastasia 1 Klarinette in B 2 bar 3; anastasia 1 Klavierauszug bar 23 |
| accidental made up | 94 | anastasia 91, ghost 3 | anastasia 4 Violine 2 28, anastasia 4 Violine 1 22, anastasia 4 Keyboard 1 16 | anastasia 1 Keyboard 1 bar 17; anastasia 2 Keyboard 1 bar 57 |
| one staff step off | 80 | ghost 50, anastasia 30 | ghost 20 Piano 29, ghost 13 Cello 16, anastasia 4 Keyboard 1 9 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 2 bar 4 |
| two staff steps off (a third) | 69 | ghost 40, anastasia 29 | ghost 20 Piano 26, anastasia 4 Keyboard 1 20, ghost 13 Cello 8 | anastasia 1 Flöte 2 bar 4; anastasia 1 Klarinette in B 1 bar 30 |
| one staff step off + accidental | 25 | anastasia 13, ghost 12 | ghost 20 Piano 9, anastasia 4 Keyboard 1 7, anastasia 4 Frauen 2 | anastasia 4 Violoncello bar 70; anastasia 4 Oboe bar 51 |
| octave off (+1) | 22 | anastasia 16, ghost 6 | anastasia 1 Klavierauszug 8, ghost 20 Piano 6, anastasia 4 Keyboard 1 4 | anastasia 1 Keyboard 1 bar 1; anastasia 1 Klavierauszug bar 17 |
| octave off (-1) | 12 | anastasia 12 | anastasia 1 Klavierauszug 11, anastasia 4 Dmitry 1 | anastasia 1 Klavierauszug bar 21; anastasia 1 Klavierauszug bar 25 |
| bar in an octave-off section (+1 octave) | 10 | anastasia 10 | anastasia 4 Männer 5, anastasia 4 Dmitry 3, anastasia 4 Posaune 1 | anastasia 4 Posaune bar 197; anastasia 4 Keyboard 1 bar 153 |
| wrong accidental | 6 | anastasia 6 | anastasia 4 Klavierauszug 6 | anastasia 4 Klavierauszug bar 51; anastasia 4 Klavierauszug bar 81 |
| bar in an octave-off section (+2 octave) | 3 | anastasia 3 | anastasia 4 Männer 3 | anastasia 4 Männer bar 65; anastasia 4 Männer bar 66 |
| enharmonic spelling (sounds right) | 2 | anastasia 2 | anastasia 4 Keyboard 1 2 | anastasia 4 Keyboard 1 bar 38 |
| bar in an octave-off section (-1 octave) | 1 | anastasia 1 | anastasia 1 Klavierauszug 1 | anastasia 1 Klavierauszug bar 23 |
| octave off (+2) | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 1 |

### bars (812)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| bar length wrong (whole-bar rest with the wrong duration) | 175 | anastasia 173, ghost 2 | anastasia 2 Kontrabass 17, anastasia 2 Trompete in B 16, anastasia 2 Posaune 13 | anastasia 1 Kontrabass bar 14; anastasia 1 Kontrabass bar 30 |
| note inside a missing bar | 162 | anastasia 131, ghost 31 | anastasia 4 Männer 115, ghost 20 Drum Kit 26, anastasia 4 Frauen 7 | anastasia 4 Violine 1 bar 129; anastasia 4 Violoncello bar 128 |
| bar missing (empty or rests only) | 117 | anastasia 102, ghost 15 | anastasia 4 Vlad 14, anastasia 4 Männer 13, anastasia 4 Horn in F 10 | anastasia 1 Klarinette in B 2 bar 4; anastasia 1 Klarinette in B 2 bar 5 |
| bar length wrong (notes / rests do not add up like the truth bar) | 114 | anastasia 69, ghost 45 | ghost 20 Drum Kit 17, ghost 20 Electric Guitar 14, ghost 20 Piano 9 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 1 bar 26 |
| extra bar (with notes) | 100 | anastasia 84, ghost 16 | anastasia 4 Männer 28, anastasia 4 Vlad 12, anastasia 4 Horn in F 8 | anastasia 1 Klarinette in B 2 (extra bar after output bar 4); anastasia 1 Klarinette in B 2 (extra bar after output bar 5) |
| extra bar (empty) | 66 | anastasia 33, ghost 33 | ghost 13 Cello 8, anastasia 4 Violine 1 5, ghost 13 Bass 5 | anastasia 2 Violoncello (extra bar after output bar 74); anastasia 2 Keyboard 1 (extra bar after output bar 45) |
| marking inside a missing bar | 48 | anastasia 35, ghost 13 | anastasia 4 Frauen 9, anastasia 4 Männer 6, ghost 20 Drum Kit 5 | anastasia 1 Klarinette in B 2 bar 4; anastasia 1 Klarinette in B 2 bar 5 |
| bar missing (with notes) | 30 | anastasia 25, ghost 5 | anastasia 4 Männer 16, ghost 20 Drum Kit 4, anastasia 4 Violoncello 2 | anastasia 4 Violine 1 bar 129; anastasia 4 Violoncello bar 128 |

### ties (465)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `tie` | 285 | ghost 191, anastasia 94 | ghost 20 Piano 108, ghost 20 Electric Piano 25, anastasia 4 Keyboard 1 16 | anastasia 1 Violine 2 bar 2; anastasia 1 Violoncello bar 10 |
| tie read as a slur | 138 | ghost 88, anastasia 50 | ghost 20 Piano 38, ghost 1a Piano 14, ghost 20 Electric Bass 11 | anastasia 1 Violine 1 bar 2; anastasia 1 Violine 1 bar 31 |
| made up `tie` | 39 | ghost 21, anastasia 18 | anastasia 4 Klavierauszug 11, ghost 1a Electric Guitar 10, ghost 1a Electric Piano 4 | anastasia 4 Violine 1 bar 6; anastasia 4 Violine 1 bar 29 |
| at the wrong beat `tie` | 3 | anastasia 3 | anastasia 4 Klavierauszug 3 | anastasia 4 Klavierauszug bar 24; anastasia 4 Klavierauszug bar 147 |

### lyrics (451)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing | 220 | anastasia 220 | anastasia 4 Dmitry 123, anastasia 4 Frauen 39, anastasia 4 Vlad 25 | anastasia 1 Frauen bar 6; anastasia 1 Frauen bar 7 — e.g. "v1:a" ×15, "v1:the" ×9, "v1:ah" ×8, "v1:and" ×6 |
| made up | 135 | anastasia 135 | anastasia 4 Männer 74, anastasia 4 Frauen 37, anastasia 4 Vlad 23 | anastasia 4 Männer bar 5; anastasia 4 Männer bar 6 — e.g. "v1:you" ×6, "v1:it" ×4, "v1:a" ×4, "v1:the" ×3 |
| wrong | 85 | anastasia 85 | anastasia 4 Frauen 45, anastasia 4 Dmitry 17, anastasia 4 Vlad 17 | anastasia 1 Frauen bar 10; anastasia 2 The Dowager Empress bar 22 — e.g. "v1:my / v1:roy" ×4, "v1:we'll / v1:we‘ll" ×3, "v1:we're / v1:we‘re" ×2, "v1:tvvo / v1:two" ×2 |
| at the wrong beat | 11 | anastasia 11 | anastasia 4 Frauen 4, anastasia 4 Dmitry 4, anastasia 4 Vlad 3 | anastasia 4 Frauen bar 3; anastasia 4 Frauen bar 5 |

### dynamics (399)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `mp` | 52 | anastasia 46, ghost 6 | anastasia 4 Horn in F 13, anastasia 4 Keyboard 1 13, anastasia 4 Oboe 10 | anastasia 2 Violine 1 bar 66; anastasia 2 Keyboard 1 bar 25 |
| made up `p` | 47 | anastasia 40, ghost 7 | anastasia 4 Violine 1 8, anastasia 4 Keyboard 1 6, anastasia 4 Oboe 5 | anastasia 1 Flöte 1 bar 18; anastasia 1 Keyboard 1 bar 27 |
| missing `mf` | 41 | anastasia 38, ghost 3 | anastasia 4 Keyboard 1 9, anastasia 4 Oboe 8, anastasia 4 Horn in F 6 | anastasia 1 Violine 1 bar 1; anastasia 1 Piccolo bar 1 |
| missing `f` | 39 | ghost 23, anastasia 16 | ghost 20 Violin 6, ghost 20 Violoncello 6, anastasia 4 Keyboard 1 4 | anastasia 1 Piccolo bar 2; anastasia 1 Horn in F bar 2 |
| missing `p` | 38 | anastasia 33, ghost 5 | anastasia 4 Oboe 7, anastasia 4 Horn in F 6, anastasia 4 Keyboard 1 4 | anastasia 1 Flöte 1 bar 14; anastasia 1 Flöte 1 bar 20 |
| missing `sfz` | 30 | anastasia 30 | anastasia 4 Horn in F 10, anastasia 4 Keyboard 1 8, anastasia 4 Violine 1 5 | anastasia 4 Violine 1 bar 1; anastasia 4 Violine 1 bar 32 |
| made up `f` | 25 | anastasia 16, ghost 9 | anastasia 4 Klavierauszug 6, ghost 20 Drum Kit 3, ghost 20 Piano 3 | anastasia 1 Piccolo bar 1; anastasia 1 Horn in F bar 1 |
| made up `mp` | 17 | anastasia 17 | anastasia 4 Keyboard 1 9, anastasia 4 Horn in F 4, anastasia 2 Keyboard 2 2 | anastasia 2 Keyboard 2 bar 25; anastasia 2 Keyboard 2 bar 66 |
| made up `mf` | 16 | anastasia 13, ghost 3 | anastasia 4 Keyboard 1 6, anastasia 4 Oboe 2, anastasia 4 Horn in F 2 | anastasia 1 Keyboard 1 bar 6; anastasia 1 Keyboard 2 bar 6 |
| missing `fz` | 11 | anastasia 11 | anastasia 4 Horn in F 4, anastasia 4 Keyboard 1 3, anastasia 4 Violine 1 2 | anastasia 4 Violine 1 bar 51; anastasia 4 Violine 1 bar 177 |
| missing `fp` | 9 | anastasia 5, ghost 4 | ghost 20 Clarinet in Bb 2, ghost 20 Trumpet in Bb 2, anastasia 1 Violine 1 1 | anastasia 1 Violine 1 bar 10; anastasia 1 Keyboard 1 bar 10 |
| missing `ff` | 8 | anastasia 8 | anastasia 4 Piccolo 3, anastasia 4 Horn in F 2, anastasia 4 Keyboard 1 2 | anastasia 4 Violine 1 bar 181; anastasia 4 Piccolo bar 181 |
| made up `sf` | 7 | ghost 4, anastasia 3 | ghost 20 Electric Guitar 2, ghost 20 Piano 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 202; anastasia 4 Frauen bar 42 |
| at the wrong beat `mf` | 6 | anastasia 6 | anastasia 4 Violine 1 3, anastasia 4 Klavierauszug 2, anastasia 2 Keyboard 1 1 | anastasia 2 Keyboard 1 bar 1; anastasia 4 Violine 1 bar 137 |
| at the wrong beat `f` | 5 | ghost 4, anastasia 1 | ghost 20 Piano 3, anastasia 4 Violine 1 1, ghost 13 Cello 1 | anastasia 4 Violine 1 bar 69; ghost 13 Cello bar 26 |
| made up `sfz` | 4 | anastasia 4 | anastasia 4 Violine 1 2, anastasia 4 Oboe 1, anastasia 4 Horn in F 1 | anastasia 4 Violine 1 bar 36; anastasia 4 Violine 1 bar 89 |
| made up `pp` | 3 | anastasia 3 | anastasia 1 Horn in F 1, anastasia 1 Klavierauszug 1, anastasia 2 Violine 1 1 | anastasia 1 Horn in F bar 18; anastasia 1 Klavierauszug bar 30 |
| missing `pp` | 3 | anastasia 2, ghost 1 | anastasia 1 Horn in F 1, anastasia 2 Splash-Becken 1, ghost 1a Violoncello 1 | anastasia 1 Horn in F bar 20; anastasia 2 Splash-Becken bar 64 |
| made up `fp` | 3 | anastasia 3 | anastasia 1 Keyboard 1 1, anastasia 1 Keyboard 2 1, anastasia 4 Keyboard 1 1 | anastasia 1 Keyboard 1 bar 10; anastasia 1 Keyboard 2 bar 10 |
| made up `ff` | 3 | anastasia 3 | anastasia 1 Klavierauszug 1, anastasia 4 Violine 1 1, anastasia 4 Keyboard 1 1 | anastasia 1 Klavierauszug bar 30; anastasia 4 Violine 1 bar #132 |
| made up `fz` | 3 | anastasia 3 | anastasia 4 Violine 1 1, anastasia 4 Oboe 1, anastasia 4 Horn in F 1 | anastasia 4 Violine 1 bar 55; anastasia 4 Oboe bar 24 |
| wrong `p` instead of `mf` | 3 | anastasia 3 | anastasia 4 Violine 1 1, anastasia 4 Keyboard 1 1, anastasia 4A Violine 1 1 | anastasia 4 Violine 1 bar 164; anastasia 4 Keyboard 1 bar 164 |
| missing `fff` | 3 | anastasia 3 | anastasia 4 Piccolo 1, anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Piccolo bar 205; anastasia 4 Keyboard 1 bar 205 |
| wrong `p` instead of `mp` | 2 | anastasia 2 | anastasia 4 Violine 1 1, anastasia 4 Frauen 1 | anastasia 4 Violine 1 bar 74; anastasia 4 Frauen bar 68 |
| at the wrong beat `p` | 2 | anastasia 2 | anastasia 4 Oboe 1, anastasia 4 Keyboard 1 1 | anastasia 4 Oboe bar 71; anastasia 4 Keyboard 1 bar 29 |
| missing `sffz` | 2 | anastasia 2 | anastasia 4 Piccolo 1, anastasia 4 Horn in F 1 | anastasia 4 Piccolo bar 206; anastasia 4 Horn in F bar 206 |
| made up `fff` | 2 | anastasia 2 | anastasia 4 Horn in F 1, anastasia 4 Keyboard 1 1 | anastasia 4 Horn in F bar 180; anastasia 4 Keyboard 1 bar 176 |
| wrong `f` instead of `fp` | 1 | anastasia 1 | anastasia 1 Frauen 1 | anastasia 1 Frauen bar 10 |
| at the wrong beat `mp` | 1 | anastasia 1 | anastasia 2 Glockenspiel 1 | anastasia 2 Glockenspiel bar 1 |
| wrong `mp` instead of `sfz` | 1 | anastasia 1 | anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 119 |
| wrong `fz` instead of `sfz` | 1 | anastasia 1 | anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 185 |
| at the wrong beat `sfz` | 1 | anastasia 1 | anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 200 |
| wrong `mp` instead of `p` | 1 | anastasia 1 | anastasia 4 Oboe 1 | anastasia 4 Oboe bar #153 |
| wrong `f` instead of `p` | 1 | anastasia 1 | anastasia 4 Oboe 1 | anastasia 4 Oboe bar 166 |
| wrong `f` instead of `mf` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 3 |
| wrong `fz` instead of `mf` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 72 |
| wrong `mf` instead of `mp` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 106 |
| wrong `ff` instead of `mp` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 178 |
| wrong `mf` instead of `p` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 65 |
| wrong `f` instead of `sfz` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 51 |
| wrong `ff` instead of `sffz` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 206 |
| wrong `mf` instead of `f` | 1 | ghost 1 | ghost 20 Drum Kit 1 | ghost 20 Drum Kit bar 74 |

### barlines (365)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `bar:light-light` | 349 | anastasia 300, ghost 49 | anastasia 4 Violine 1 13, anastasia 4 Violine 2 13, anastasia 4 Violoncello 13 | anastasia 1 Violine 1 bar 5; anastasia 1 Violine 1 bar 9 |
| at the wrong beat `bar:light-heavy` | 9 | anastasia 9 | anastasia 1 Kontrabass 1, anastasia 1 Flöte 1 1, anastasia 1 Fagott 1 | anastasia 1 Kontrabass bar 32; anastasia 1 Flöte 1 bar 32 |
| missing `bar:light-heavy` | 5 | ghost 3, anastasia 2 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1, ghost 1a Clarinet in Bb 1 | whole part; ghost 1a Clarinet in Bb bar 28 |
| made up `bar:light-heavy` | 2 | anastasia 2 | anastasia 4 Dmitry 1, anastasia 4 Vlad 1 | anastasia 4 Dmitry bar 206; anastasia 4 Vlad bar 206 |

### words (318)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 182 | anastasia 148, ghost 34 | anastasia 4 Keyboard 1 34, anastasia 1 Klavierauszug 13, anastasia 2 Keyboard 1 10 | anastasia 1 Violine 1 bar 14; anastasia 1 Violine 1 bar 27 — e.g. "solo" ×12, "div" ×4, "str. ens. (loco)" ×4, "(to all, with ironicjoy)" ×3 |
| missing | 123 | anastasia 110, ghost 13 | anastasia 4 Violine 1 18, anastasia 4 Violoncello 16, anastasia 4 Violine 2 14 | anastasia 1 Horn in F bar 20; anastasia 1 Posaune bar 20 — e.g. "arco" ×32, "pizz." ×25, "gedämpft" ×13, "offen" ×9 |
| wrong | 7 | ghost 4, anastasia 3 | anastasia 4 Violine 1 3, ghost 20 Electric Piano 2, ghost 1a Electric Guitar 1 | anastasia 4 Violine 1 bar 29; anastasia 4 Violine 1 bar 58 — e.g. "[to 29 / pizz." ×1, "p000 apoco / cresc." ×1, "(”to / arco" ×1, "molto legato / zu akustische gitarre" ×1 |
| at the wrong beat | 6 | anastasia 5, ghost 1 | anastasia 4 Violoncello 2, anastasia 4 Kontrabass 1, anastasia 4A Kontrabass 1 | anastasia 4 Violoncello bar 78; anastasia 4 Violoncello bar 157 |

### slurs (289)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `slur` | 150 | anastasia 89, ghost 61 | ghost 20 Piano 23, anastasia 4 Klavierauszug 19, anastasia 4 Oboe 13 | anastasia 1 Piccolo bar 1; anastasia 1 Piccolo bar 5 |
| missing `slur` | 117 | ghost 72, anastasia 45 | ghost 20 Piano 15, ghost 20 Electric Piano 13, anastasia 4 Keyboard 1 12 | anastasia 1 Keyboard 1 bar 7; anastasia 1 Frauen bar 9 |
| at the wrong beat `slur` | 22 | ghost 16, anastasia 6 | ghost 20 Electric Guitar 4, anastasia 4 Keyboard 1 3, ghost 20 Clarinet in Bb 3 | anastasia 4 Violine 1 bar 77; anastasia 4 Violine 1 bar 107 |

### rhythm (265)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note at the wrong beat (onset shifted) | 102 | anastasia 58, ghost 44 | anastasia 4 Klavierauszug 26, anastasia 4 Keyboard 1 20, ghost 20 Drum Kit 20 | anastasia 1 Keyboard 2 bar 7; anastasia 2 Keyboard 1 bar 1 |
| note value x2 too long | 54 | anastasia 27, ghost 27 | ghost 20 Piano 15, ghost 20 Electric Guitar 8, anastasia 4 Violoncello 5 | anastasia 1 Flöte 2 bar 4; anastasia 1 Horn in F bar 26 |
| note value 1/2 too short | 39 | anastasia 26, ghost 13 | anastasia 4 Keyboard 1 10, anastasia 4 Klavierauszug 9, ghost 20 Drum Kit 9 | anastasia 1 Splash-Becken bar 2; anastasia 1 Klavierauszug bar 23 |
| same length, other notation | 36 | anastasia 36 | anastasia 1 Violine 1 6, anastasia 1 Violine 2 6, anastasia 1 Flöte 2 6 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| note value x4 too long | 9 | ghost 8, anastasia 1 | ghost 20 Electric Guitar 4, ghost 20 Piano 4, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 70; ghost 20 Electric Guitar bar 5 |
| dot missing | 7 | ghost 6, anastasia 1 | ghost 20 Piano 4, ghost 20 Drum Kit 2, anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 79; ghost 20 Drum Kit bar 95 |
| other wrong length (longer) | 6 | anastasia 6 | anastasia 1 Flöte 1 2, anastasia 1 Fagott 2, anastasia 4 Posaune 1 | anastasia 1 Flöte 1 bar 26; anastasia 1 Flöte 1 bar 27 |
| tuplet made up | 4 | anastasia 4 | anastasia 4 Klavierauszug 4 | anastasia 4 Klavierauszug bar 137 |
| triplet / tuplet missing | 3 | anastasia 3 | anastasia 1 Piccolo 2, anastasia 1 Klarinette in B 2 1 | anastasia 1 Piccolo bar 1; anastasia 1 Klarinette in B 2 bar 2 |
| note value 1/4 too short | 3 | anastasia 2, ghost 1 | anastasia 4 Keyboard 1 2, ghost 20 Drum Kit 1 | anastasia 4 Keyboard 1 bar 23; anastasia 4 Keyboard 1 bar 176 |
| dot made up | 2 | anastasia 2 | anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 26; anastasia 4 Klavierauszug bar 169 |

### systemtext (240)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 229 | anastasia 180, ghost 49 | anastasia 4 (system items) 106, ghost 20 (system items) 39, anastasia 2 (system items) 35 | anastasia 1 (system); anastasia 2 (system) — e.g. "gedämpft" ×10, "solo" ×8, "fill" ×7, "sim." ×6 |
| wrong | 5 | anastasia 4, ghost 1 | anastasia 2 (system items) 2, anastasia 1 (system items) 1, anastasia 4 (system items) 1 | anastasia 1 (system); anastasia 2 (system) — e.g. "poco rit. / rit." ×1, "poco ritard. / rit." ×1, "poco mosso / accel." ×1, "nat. / sicherheitswiederholung" ×1 |
| at the wrong beat | 3 | ghost 2, anastasia 1 | ghost 13 (system items) 2, anastasia 1 (system items) 1 | anastasia 1 (system); ghost 13 (system) |
| missing | 3 | anastasia 2, ghost 1 | anastasia 2 (system items) 1, anastasia 4 (system items) 1, ghost 13 (system items) 1 | anastasia 2 (system); anastasia 4 (system) — e.g. "rit." ×1, "sicherheitswiederholung" ×1, "accel." ×1 |

### hairpins (200)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `crescendo` | 126 | anastasia 115, ghost 11 | anastasia 4 Horn in F 27, anastasia 4 Violine 1 22, anastasia 4 Keyboard 1 22 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 1 bar 8 |
| missing `diminuendo` | 54 | anastasia 48, ghost 6 | anastasia 4 Violine 1 9, anastasia 4 Keyboard 1 7, anastasia 4 Oboe 6 | anastasia 1 Violine 1 bar 10; anastasia 1 Violine 1 bar 32 |
| at the wrong beat `crescendo` | 8 | anastasia 6, ghost 2 | anastasia 4 Klavierauszug 3, anastasia 1 Klavierauszug 1, anastasia 4 Violine 1 1 | anastasia 1 Klavierauszug bar 1; anastasia 4 Violine 1 bar 199 |
| made up `crescendo` | 8 | anastasia 8 | anastasia 4 Klavierauszug 5, anastasia 4 Keyboard 1 2, anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 165; anastasia 4 Keyboard 1 bar 162 |
| made up `diminuendo` | 2 | anastasia 2 | anastasia 4 Klavierauszug 2 | anastasia 4 Klavierauszug bar 6; anastasia 4 Klavierauszug bar 14 |
| at the wrong beat `diminuendo` | 2 | anastasia 2 | anastasia 4 Klavierauszug 2 | anastasia 4 Klavierauszug bar 114; anastasia 4 Klavierauszug bar 119 |

### keys (200)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `key:0` | 40 | anastasia 37, ghost 3 | anastasia 4 Keyboard 1 6, anastasia 4 Klavierauszug 6, anastasia 4 Violine 1 3 | anastasia 1 Keyboard 1 bar 14; whole part |
| made up `key:0` | 35 | anastasia 33, ghost 2 | anastasia 4 Keyboard 1 6, anastasia 4 Klavierauszug 6, anastasia 4 Violine 1 3 | anastasia 4 Violine 1 bar 144; anastasia 4 Violine 1 bar 152 |
| missing `key:1` | 18 | anastasia 16, ghost 2 | anastasia 4 Horn in F 3, anastasia 4 Trompete in B 2, anastasia 4 Keyboard 1 2 | anastasia 4 Violine 1 bar 149; anastasia 4 Violine 2 bar 149 |
| made up `key:1` | 16 | anastasia 15, ghost 1 | anastasia 4 Horn in F 2, anastasia 4 Trompete in B 2, anastasia 4 Keyboard 1 2 | anastasia 4 Violine 1 bar 148; anastasia 4 Violine 2 bar #151 |
| missing `key:-5` | 14 | anastasia 12, ghost 2 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 158; anastasia 4 Violine 2 bar 158 |
| missing `key:5` | 12 | anastasia 12 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 170; anastasia 4 Violine 2 bar 170 |
| made up `key:-5` | 11 | anastasia 10, ghost 1 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 154; anastasia 4 Violine 2 bar 155 |
| made up `key:5` | 11 | anastasia 11 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 166; anastasia 4 Violine 2 bar 167 |
| made up `key:2` | 6 | anastasia 4, ghost 2 | anastasia 4 Trompete in B 3, anastasia 4 Horn in F 1, ghost 13 Cello 1 | anastasia 4 Horn in F bar 148; anastasia 4 Trompete in B bar 101 |
| missing `key:-4` | 6 | ghost 5, anastasia 1 | ghost 20 Electric Piano 2, anastasia 4 Horn in F 1, ghost 20 Violoncello 1 | anastasia 4 Horn in F bar 158; ghost 20 Violoncello bar 100 |
| missing `key:-1` | 6 | ghost 6 | ghost 20 Electric Guitar 3, ghost 20 Violin 1, ghost 20 Violoncello 1 | ghost 20 Violin bar 110; ghost 20 Violoncello bar 110 |
| missing `key:2` | 4 | anastasia 2, ghost 2 | anastasia 4 Trompete in B 2, ghost 13 Cello 1, ghost 13 Bass 1 | anastasia 4 Trompete in B bar 102; anastasia 4 Trompete in B bar 180 |
| made up `key:-1` | 4 | ghost 4 | ghost 20 Violin 1, ghost 20 Violoncello 1, ghost 20 Electric Bass 1 | ghost 20 Violin bar 109; ghost 20 Violoncello bar 109 |
| missing `key:-2` | 3 | ghost 3 | ghost 13 Bass 1, ghost 20 Electric Bass 1, ghost 20 Electric Guitar 1 | ghost 13 Bass bar 114; ghost 20 Electric Bass bar 92 |
| made up `key:-2` | 2 | ghost 2 | ghost 13 Bass 1, ghost 20 Electric Guitar 1 | ghost 13 Bass bar 110; ghost 20 Electric Guitar bar 90 |
| made up `key:-4` | 2 | ghost 2 | ghost 20 Electric Bass 1, ghost 20 Electric Guitar 1 | ghost 20 Electric Bass bar 99; ghost 20 Electric Guitar bar 97 |
| made up `key:6` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 168 |
| missing `key:6` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 170 |
| wrong `key:3` instead of `key:2` | 1 | anastasia 1 | anastasia 4 Trompete in B 1 | anastasia 4 Trompete in B bar 145 |
| wrong `key:2` instead of `key:3` | 1 | anastasia 1 | anastasia 4 Trompete in B 1 | anastasia 4 Trompete in B bar 149 |
| wrong `key:-3` instead of `key:2` | 1 | anastasia 1 | anastasia 4 Trompete in B 1 | anastasia 4 Trompete in B bar 156 |
| missing `key:-3` | 1 | anastasia 1 | anastasia 4 Trompete in B 1 | anastasia 4 Trompete in B bar 158 |
| made up `key:7` | 1 | anastasia 1 | anastasia 4 Trompete in B 1 | anastasia 4 Trompete in B bar 168 |
| wrong `key:-5` instead of `key:0` | 1 | anastasia 1 | anastasia 4 Posaune 1 | anastasia 4 Posaune bar 156 |
| wrong `key:0` instead of `key:1` | 1 | anastasia 1 | anastasia 4A Xylophon 1 | anastasia 4A Xylophon bar 1 |
| wrong `key:7` instead of `key:-5` | 1 | ghost 1 | ghost 1a Clarinet in Bb 1 | ghost 1a Clarinet in Bb bar 1 |

### structure (164)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `repeat:forward` | 83 | anastasia 79, ghost 4 | anastasia 4 Violine 1 3, anastasia 4 Violine 2 3, anastasia 4 Violoncello 3 | anastasia 2 Violine 1 bar #73; anastasia 2 Violine 2 bar #73 |
| missing `repeat:backward` | 81 | anastasia 77, ghost 4 | anastasia 4 Violine 1 3, anastasia 4 Violine 2 3, anastasia 4 Violoncello 3 | anastasia 2 Violine 1 bar #73; anastasia 2 Violine 2 bar #73 |

### drums (121)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| hit missing | 108 | ghost 98, anastasia 10 | ghost 20 Drum Kit 98, anastasia 1 Splash-Becken 4, anastasia 2 Triangel 4 | anastasia 1 Splash-Becken bar 3; anastasia 1 Splash-Becken bar 4 |
| wrong kit instrument (staff position) | 11 | ghost 6, anastasia 5 | ghost 20 Drum Kit 6, anastasia 2 Splash-Becken 3, anastasia 1 Splash-Becken 1 | anastasia 1 Splash-Becken bar 2; anastasia 2 Splash-Becken bar 64 |
| hit made up | 2 | ghost 2 | ghost 20 Drum Kit 2 | ghost 20 Drum Kit bar 36; ghost 20 Drum Kit bar 46 |

### chords (76)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| at the wrong beat | 28 | ghost 28 | ghost 20 Electric Guitar 25, ghost 1a Electric Guitar 3 | ghost 1a Electric Guitar bar 9; ghost 1a Electric Guitar bar 16 |
| made up | 27 | ghost 26, anastasia 1 | ghost 20 Piano 16, ghost 1a Electric Guitar 5, ghost 20 Electric Guitar 4 | anastasia 4 Klavierauszug bar 136; ghost 1a Electric Guitar bar 11 — e.g. "F:major" ×16, "Eb:suspended-fourth" ×3, "Db:major-seventh" ×3, "Ab:dominant-ninth/Eb" ×2 |
| missing | 21 | ghost 21 | ghost 1a Piano 12, ghost 1a Electric Guitar 5, ghost 20 Electric Guitar 4 | ghost 1a Electric Guitar bar 12; ghost 1a Electric Guitar bar 13 — e.g. "Eb:suspended-fourth" ×7, "Ab:dominant-ninth/Eb" ×6, "Db:major-seventh" ×3, "G#:minor" ×1 |

### clefs (73)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `clef:G2` | 20 | anastasia 14, ghost 6 | anastasia 4 Keyboard 1 6, ghost 20 Piano 4, anastasia 4 Klavierauszug 2 | anastasia 1 Pauken bar 9; anastasia 1 Klavierauszug bar 30 |
| made up `clef:F4` | 16 | anastasia 14, ghost 2 | anastasia 4 Keyboard 1 7, anastasia 4 Klavierauszug 4, anastasia 1 Klarinette in B 2 1 | anastasia 1 Klarinette in B 2 bar 6; anastasia 1 Keyboard 1 bar 17 |
| missing `clef:F4` | 13 | anastasia 9, ghost 4 | anastasia 4 Klavierauszug 4, anastasia 4 Keyboard 1 3, anastasia 1 Klavierauszug 2 | anastasia 1 Klavierauszug bar 6; anastasia 1 Klavierauszug bar 24 |
| missing `clef:G2` | 12 | anastasia 6, ghost 6 | ghost 20 Piano 4, anastasia 1 Klavierauszug 2, anastasia 4 Keyboard 1 2 | anastasia 1 Klavierauszug bar 23; anastasia 1 Klavierauszug bar 31 |
| missing `clef:percussion` | 2 | anastasia 2 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1 | whole part |
| wrong `clef:G2` instead of `clef:G2^-1` | 2 | ghost 2 | ghost 1a Electric Guitar 1, ghost 20 Electric Guitar 1 | ghost 1a Electric Guitar bar 1; ghost 20 Electric Guitar bar 1 |
| wrong `clef:F4` instead of `clef:G2` | 2 | ghost 2 | ghost 1a Electric Piano 1, ghost 1a Piano 1 | ghost 1a Electric Piano bar 1; ghost 1a Piano bar 1 |
| at the wrong beat `clef:G2` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 51 |
| at the wrong beat `clef:F4` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 184 |
| made up `clef:C3` | 1 | anastasia 1 | anastasia 4 Frauen 1 | anastasia 4 Frauen bar 201 |
| wrong `clef:G2^-1` instead of `clef:F4` | 1 | anastasia 1 | anastasia 4 Vlad 1 | anastasia 4 Vlad bar 1 |
| missing `clef:G2^-1` | 1 | anastasia 1 | anastasia 4 Vlad 1 | anastasia 4 Vlad bar 83 |
| wrong `clef:percussion` instead of `clef:G2` | 1 | anastasia 1 | anastasia 4A Xylophon 1 | anastasia 4A Xylophon bar 1 |

### times (60)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `time:4/4` | 16 | anastasia 16 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 193; anastasia 4 Violine 2 bar 194 |
| missing `time:2/4` | 16 | anastasia 13, ghost 3 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, ghost 1a Piano 2 | anastasia 4 Violine 1 bar 196; anastasia 4 Violine 2 bar 196 |
| missing `time:4/4` | 16 | anastasia 16 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2, anastasia 4 Violine 2 1 | anastasia 4 Violine 2 bar 197; anastasia 4 Violoncello bar 197 |
| made up `time:2/4` | 10 | anastasia 10 | anastasia 4 Violine 1 1, anastasia 4 Violine 2 1, anastasia 4 Violoncello 1 | anastasia 4 Violine 1 bar 192; anastasia 4 Violine 2 bar 193 |
| missing `time:3/4` | 2 | anastasia 2 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1 | whole part |

### tremolos (54)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `trem:single:3` | 49 | anastasia 48, ghost 1 | anastasia 4 Violoncello 13, anastasia 4 Violine 1 11, anastasia 1 Violine 1 8 | anastasia 1 Violine 1 bar 2; anastasia 1 Violine 1 bar 3 |
| made up `trem:single:3` | 2 | anastasia 2 | anastasia 1 Keyboard 1 1, anastasia 4 Violine 2 1 | anastasia 1 Keyboard 1 bar 16; anastasia 4 Violine 2 bar 121 |
| missing `trem:start:3` | 1 | anastasia 1 | anastasia 1 Klarinette in B 2 1 | anastasia 1 Klarinette in B 2 bar 2 |
| at the wrong beat `trem:single:3` | 1 | anastasia 1 | anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 8 |
| missing `trem:single:2` | 1 | ghost 1 | ghost 20 Violin 1 | ghost 20 Violin bar 108 |

### fermatas (48)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `fermata` | 25 | anastasia 15, ghost 10 | ghost 1a Electric Guitar 5, anastasia 1 Keyboard 2 4, anastasia 1 Klavierauszug 4 | anastasia 1 Trompete in B bar 31; anastasia 1 Keyboard 2 bar 31 |
| made up `fermata` | 22 | anastasia 18, ghost 4 | anastasia 4 Violine 1 6, anastasia 4 Klavierauszug 3, anastasia 2 Keyboard 1 2 | anastasia 2 Klarinette in B 1 bar #74; anastasia 2 Keyboard 1 bar 29 |
| at the wrong beat `fermata` | 1 | ghost 1 | ghost 1a Electric Guitar 1 | ghost 1a Electric Guitar bar 8 |

### rehearsal (34)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 21 | ghost 21 | ghost 13 (system items) 17, ghost 20 (system items) 4 | ghost 13 (system); ghost 20 (system) — e.g. "reh:d" ×3, "reh:j" ×3, "reh:e" ×2, "reh:b" ×1 |
| at the wrong beat | 9 | ghost 9 | ghost 13 (system items) 7, ghost 20 (system items) 2 | ghost 13 (system); ghost 20 (system) |
| missing | 4 | ghost 4 | ghost 1a (system items) 2, ghost 13 (system items) 1, ghost 20 (system items) 1 | ghost 1a (system); ghost 13 (system) — e.g. "reh:a" ×1, "reh:b" ×1, "reh:p" ×1, "reh:f" ×1 |

### instruments (29)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `ic` | 19 | anastasia 19 | anastasia 4 Frauen 13, anastasia 4 Männer 5, anastasia 4 Dmitry 1 | anastasia 4 Männer bar 41; anastasia 4 Männer bar 47 |
| missing `ic` | 10 | ghost 10 | ghost 20 Electric Piano 4, ghost 1a Electric Piano 2, ghost 1a Piano 2 | ghost 1a Electric Guitar bar 9; ghost 1a Electric Piano bar 1 |

### tuplets (15)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `tuplet:3:2` | 7 | anastasia 7 | anastasia 1 Violine 1 1, anastasia 1 Violine 2 1, anastasia 1 Flöte 2 1 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| wrong `tuplet:3:2` instead of `tuplet:6:4` | 6 | anastasia 6 | anastasia 1 Violine 1 1, anastasia 1 Violine 2 1, anastasia 1 Flöte 2 1 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| missing `tuplet:6:4` | 1 | anastasia 1 | anastasia 1 Piccolo 1 | anastasia 1 Piccolo bar 1 |
| missing `tuplet:3:2` | 1 | ghost 1 | ghost 13 Cello 1 | ghost 13 Cello bar 25 |

### tempo (7)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing | 3 | ghost 2, anastasia 1 | anastasia 4A (system items) 1, ghost 13 (system items) 1, ghost 20 (system items) 1 | anastasia 4A (system); ghost 13 (system) — e.g. "quarter=130" ×2, "quarter=120" ×1 |
| made up | 2 | anastasia 1, ghost 1 | anastasia 4 (system items) 1, ghost 13 (system items) 1 | anastasia 4 (system); ghost 13 (system) — e.g. "quarter=124" ×1, "quarter=122" ×1 |
| at the wrong beat | 2 | ghost 2 | ghost 13 (system items) 2 | ghost 13 (system) |

### part (3)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| no output at all (every truth item below counts as missing) | 2 | anastasia 2 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1 | whole part |
| whole part transposed (+12 semitones; 1 bulk action) | 1 | anastasia 1 | anastasia 2 Kontrabass 1 | whole part |

### note on the wrong staff (piano) (2)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note on the wrong staff (piano) | 2 | anastasia 2 | anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 22; anastasia 4 Klavierauszug bar 147 |

### Per part (top 6 kinds)

| part | total | top kinds |
|---|---|---|
| anastasia 4 Keyboard 1 | 849 | pitch: accidental missing 104, notes: note missing 88, pitch: wrong by more than a third 72, articulations: missing `staccato` 72, articulations: missing `accent` 65, words: made up 34 |
| ghost 20 Piano | 634 | notes: note missing 130, ties: missing `tie` 108, pitch: wrong by more than a third 60, ties: tie read as a slur 38, pitch: one staff step off 29, pitch: two staff steps off (a third) 26 |
| anastasia 4 Klavierauszug | 484 | articulations: missing `accent` 67, articulations: missing `tenuto` 65, articulations: missing `staccato` 31, rhythm: note at the wrong beat (onset shifted) 26, slurs: made up `slur` 19, pitch: wrong by more than a third 17 |
| anastasia 4 Männer | 404 | bars: note inside a missing bar 115, lyrics: made up 74, notes: note missing 47, bars: extra bar (with notes) 28, lyrics: missing 20, bars: bar missing (with notes) 16 |
| anastasia 4 Dmitry | 330 | lyrics: missing 123, notes: note missing 110, lyrics: wrong 17, barlines: missing `bar:light-light` 13, articulations: missing `accent` 7, ties: missing `tie` 5 |
| anastasia 4 Frauen | 319 | lyrics: wrong 45, lyrics: missing 39, lyrics: made up 37, notes: extra chord note 34, notes: note missing 15, barlines: missing `bar:light-light` 13 |
| anastasia 4 Violine 1 | 280 | pitch: accidental missing 29, hairpins: missing `crescendo` 22, pitch: accidental made up 22, words: missing 18, barlines: missing `bar:light-light` 13, articulations: missing `accent` 11 |
| ghost 20 Drum Kit | 257 | drums: hit missing 98, bars: note inside a missing bar 26, articulations: made up `staccato` 20, rhythm: note at the wrong beat (onset shifted) 20, bars: bar length wrong (notes / rests do not add up like the truth bar) 17, ties: missing `tie` 11 |
| ghost 20 Electric Guitar | 239 | notes: note missing 76, chords: at the wrong beat 25, bars: bar length wrong (notes / rests do not add up like the truth bar) 14, ties: missing `tie` 13, pitch: wrong by more than a third 10, slurs: missing `slur` 9 |
| anastasia 4 Horn in F | 234 | hairpins: missing `crescendo` 27, articulations: missing `tenuto` 25, dynamics: missing `mp` 13, barlines: missing `bar:light-light` 13, notes: note missing 11, bars: bar missing (empty or rests only) 10 |
| ghost 13 Cello | 215 | articulations: missing `staccato` 49, articulations: missing `accent` 28, pitch: one staff step off 16, articulations: missing `strong-accent` 15, barlines: missing `bar:light-light` 13, notes: note missing 10 |
| anastasia 4 Oboe | 213 | pitch: accidental missing 24, hairpins: missing `crescendo` 17, slurs: made up `slur` 13, barlines: missing `bar:light-light` 13, dynamics: missing `mp` 10, dynamics: missing `mf` 8 |
| anastasia 4 Vlad | 208 | notes: note missing 50, lyrics: missing 25, lyrics: made up 23, lyrics: wrong 17, bars: bar missing (empty or rests only) 14, barlines: missing `bar:light-light` 12 |
| anastasia 4 Violoncello | 176 | pitch: accidental missing 57, words: missing 16, tremolos: missing `trem:single:3` 13, barlines: missing `bar:light-light` 13, pitch: wrong by more than a third 11, notes: note missing 10 |
| ghost 20 Electric Piano | 166 | articulations: made up `staccato` 38, ties: missing `tie` 25, notes: note missing 20, slurs: missing `slur` 13, slurs: made up `slur` 12, words: made up 8 |
| anastasia 4 Violine 2 | 162 | pitch: accidental missing 46, pitch: accidental made up 28, words: missing 14, barlines: missing `bar:light-light` 13, pitch: one staff step off 7, ties: missing `tie` 7 |
| anastasia 1 Klavierauszug | 111 | articulations: missing `accent` 16, words: made up 13, pitch: octave off (-1) 11, pitch: octave off (+1) 8, rhythm: same length, other notation 6, articulations: made up `staccato` 6 |
| anastasia 4 (system items) | 109 | systemtext: made up 106, systemtext: wrong 1, systemtext: missing 1, tempo: made up 1 |
| anastasia 4 Posaune | 93 | notes: note missing 14, barlines: missing `bar:light-light` 13, notes: note made up 8, ties: missing `tie` 7, words: missing 6, pitch: accidental made up 5 |
| anastasia 4 Trompete in B | 89 | barlines: missing `bar:light-light` 13, notes: note missing 12, bars: bar missing (empty or rests only) 7, bars: extra bar (with notes) 5, words: missing 4, bars: bar length wrong (notes / rests do not add up like the truth bar) 4 |
| anastasia 4 Kontrabass | 83 | pitch: accidental missing 29, barlines: missing `bar:light-light` 13, pitch: accidental made up 7, words: missing 6, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3 |
| anastasia 1 Keyboard 1 | 81 | articulations: missing `accent` 10, notes: note missing 10, slurs: made up `slur` 8, words: made up 7, articulations: made up `tenuto` 6, ties: tie read as a slur 6 |
| ghost 13 Bass | 77 | articulations: missing `accent` 24, barlines: missing `bar:light-light` 11, bars: extra bar (empty) 5, ties: tie read as a slur 5, words: made up 4, words: missing 2 |
| ghost 1a Piano | 75 | notes: note missing 18, ties: tie read as a slur 14, chords: missing 12, slurs: missing `slur` 5, ties: missing `tie` 4, dynamics: made up `p` 3 |
| anastasia 2 Keyboard 1 | 66 | notes: note made up 12, words: made up 10, slurs: made up `slur` 8, bars: bar length wrong (whole-bar rest with the wrong duration) 7, bars: bar length wrong (notes / rests do not add up like the truth bar) 3, dynamics: made up `p` 3 |
| ghost 1a Electric Guitar | 65 | slurs: missing `slur` 10, ties: made up `tie` 10, notes: note missing 6, fermatas: missing `fermata` 5, chords: made up 5, chords: missing 5 |
| ghost 20 Violoncello | 63 | slurs: missing `slur` 9, ties: tie read as a slur 7, dynamics: missing `f` 6, slurs: made up `slur` 5, ties: missing `tie` 4, notes: note missing 4 |
| anastasia 4 Piccolo | 57 | barlines: missing `bar:light-light` 13, bars: bar missing (empty or rests only) 4, bars: extra bar (empty) 4, hairpins: missing `crescendo` 4, slurs: missing `slur` 4, structure: missing `repeat:forward` 3 |
| ghost 20 Trumpet in Bb | 54 | notes: note missing 4, articulations: missing `accent` 4, pitch: two staff steps off (a third) 3, pitch: one staff step off 3, notes: note made up 3, slurs: at the wrong beat `slur` 3 |
| ghost 20 Clarinet in Bb | 52 | notes: note missing 6, articulations: missing `staccato` 5, ties: tie read as a slur 4, pitch: two staff steps off (a third) 3, notes: note made up 3, slurs: at the wrong beat `slur` 3 |
| ghost 20 Violin | 50 | slurs: made up `slur` 9, dynamics: missing `f` 6, ties: missing `tie` 4, articulations: missing `accent` 4, ties: tie read as a slur 4, slurs: missing `slur` 3 |
| anastasia 1 Keyboard 2 | 47 | notes: note missing 11, words: made up 4, barlines: missing `bar:light-light` 4, notes: chord note missing 4, bars: bar length wrong (notes / rests do not add up like the truth bar) 4, fermatas: missing `fermata` 4 |
| ghost 20 (system items) | 47 | systemtext: made up 39, rehearsal: made up 4, rehearsal: at the wrong beat 2, rehearsal: missing 1, tempo: missing 1 |
| anastasia 2 Violine 1 | 44 | bars: bar length wrong (whole-bar rest with the wrong duration) 12, slurs: made up `slur` 7, hairpins: missing `diminuendo` 4, bars: bar missing (empty or rests only) 3, dynamics: missing `p` 3, words: made up 3 |
| ghost 1a Electric Piano | 41 | pitch: wrong by more than a third 8, articulations: made up `staccato` 7, ties: missing `tie` 7, slurs: missing `slur` 4, ties: made up `tie` 4, instruments: missing `ic` 2 |
| anastasia 1 Violine 1 | 39 | tremolos: missing `trem:single:3` 8, rhythm: same length, other notation 6, articulations: missing `accent` 4, barlines: missing `bar:light-light` 4, words: made up 4, articulations: missing `tenuto` 3 |
| anastasia 2 (system items) | 38 | systemtext: made up 35, systemtext: wrong 2, systemtext: missing 1 |
| anastasia 4A Violine 1 | 38 | articulations: missing `tenuto` 32, dynamics: wrong `p` instead of `mf` 1, hairpins: missing `diminuendo` 1, dynamics: missing `p` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| ghost 13 (system items) | 37 | rehearsal: made up 17, rehearsal: at the wrong beat 7, systemtext: made up 5, systemtext: at the wrong beat 2, tempo: at the wrong beat 2, rehearsal: missing 1 |
| anastasia 2 Keyboard 2 | 36 | bars: bar length wrong (notes / rests do not add up like the truth bar) 8, slurs: made up `slur` 5, words: made up 4, pitch: two staff steps off (a third) 2, hairpins: missing `diminuendo` 2, dynamics: made up `mp` 2 |
| ghost 20 Electric Bass | 34 | ties: tie read as a slur 11, ties: missing `tie` 5, words: made up 3, barlines: missing `bar:light-light` 3, dynamics: made up `f` 1, articulations: made up `caesura` 1 |
| anastasia 1 Flöte 1 | 32 | ties: tie read as a slur 6, barlines: missing `bar:light-light` 4, notes: note missing 3, bars: bar length wrong (whole-bar rest with the wrong duration) 3, dynamics: missing `p` 2, rhythm: other wrong length (longer) 2 |
| anastasia 1 (system items) | 30 | systemtext: made up 28, systemtext: at the wrong beat 1, systemtext: wrong 1 |
| anastasia 1 Piccolo | 24 | notes: note missing 4, notes: note made up 4, barlines: missing `bar:light-light` 4, rhythm: triplet / tuplet missing 2, slurs: made up `slur` 2, pitch: one staff step off 1 |
| anastasia 1 Klarinette in B 2 | 24 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 3, bars: bar missing (empty or rests only) 2, bars: marking inside a missing bar 2, bars: extra bar (with notes) 2, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1 |
| anastasia 1 Splash-Becken | 24 | tremolos: missing `trem:single:3` 5, drums: hit missing 4, barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 3, hairpins: missing `crescendo` 3, ties: missing `tie` 2 |
| anastasia 2 Glockenspiel | 23 | bars: bar missing (empty or rests only) 4, words: made up 3, slurs: made up `slur` 3, bars: bar length wrong (whole-bar rest with the wrong duration) 3, dynamics: at the wrong beat `mp` 1, dynamics: missing `mf` 1 |
| anastasia 2 Kontrabass | 22 | bars: bar length wrong (whole-bar rest with the wrong duration) 17, part: whole part transposed (+12 semitones; 1 bulk action) 1, notes: note made up 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 1 Horn in F | 21 | barlines: missing `bar:light-light` 4, dynamics: missing `mf` 2, hairpins: missing `crescendo` 2, rhythm: note value x2 too long 2, bars: bar length wrong (notes / rests do not add up like the truth bar) 2, dynamics: made up `f` 1 |
| anastasia 2 Trompete in B | 21 | bars: bar length wrong (whole-bar rest with the wrong duration) 16, barlines: missing `bar:light-light` 1, words: missing 1, bars: bar missing (empty or rests only) 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 2 The Dowager Empress | 21 | words: missing 6, lyrics: missing 3, words: made up 3, articulations: made up `staccato` 2, lyrics: wrong 1, articulations: missing `breath-mark` 1 |
| anastasia 2 Posaune | 20 | bars: bar length wrong (whole-bar rest with the wrong duration) 13, notes: note made up 2, barlines: missing `bar:light-light` 1, words: missing 1, bars: bar missing (empty or rests only) 1, structure: missing `repeat:forward` 1 |
| anastasia 1 Flöte 2 | 19 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, rhythm: note value x2 too long 1, pitch: two staff steps off (a third) 1 |
| anastasia 1 Trompete in B | 19 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, ties: missing `tie` 1 |
| anastasia 1 Pauken | 19 | notes: note made up 6, barlines: missing `bar:light-light` 4, slurs: made up `slur` 3, dynamics: missing `mf` 1, hairpins: missing `crescendo` 1, words: made up 1 |
| anastasia 1 Frauen | 19 | barlines: missing `bar:light-light` 4, lyrics: missing 4, words: made up 3, ties: missing `tie` 2, articulations: made up `staccato` 1, words: missing 1 |
| anastasia 2 Violine 2 | 19 | bars: bar length wrong (whole-bar rest with the wrong duration) 12, words: made up 2, notes: note made up 1, bars: bar length wrong (notes / rests do not add up like the truth bar) 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1 |
| anastasia 2 Splash-Becken | 19 | bars: bar length wrong (whole-bar rest with the wrong duration) 3, drums: wrong kit instrument (staff position) 3, bars: bar missing (empty or rests only) 3, ties: tie read as a slur 2, tremolos: missing `trem:single:3` 2, barlines: missing `bar:light-light` 1 |
| anastasia 4A Xylophon | 19 | bars: bar length wrong (whole-bar rest with the wrong duration) 5, notes: note missing 2, articulations: missing `accent` 1, clefs: wrong `clef:percussion` instead of `clef:G2` 1, dynamics: missing `mf` 1, keys: wrong `key:0` instead of `key:1` 1 |
| anastasia 2 Crotales | 18 | bars: bar length wrong (whole-bar rest with the wrong duration) 6, notes: note made up 3, bars: bar missing (empty or rests only) 3, dynamics: missing `p` 1, words: made up 1, slurs: made up `slur` 1 |
| anastasia 1 Violine 2 | 15 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, ties: missing `tie` 1, pitch: accidental missing 1 |
| anastasia 1 Kontrabass | 15 | barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 4, notes: note made up 4, tremolos: missing `trem:single:3` 1, ties: missing `tie` 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 2 Klarinette in B 2 | 15 | bars: bar length wrong (whole-bar rest with the wrong duration) 10, ties: missing `tie` 1, barlines: missing `bar:light-light` 1, pitch: accidental missing 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 2 Fagott | 15 | bars: bar length wrong (whole-bar rest with the wrong duration) 12, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 1 Fagott | 14 | barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 4, rhythm: other wrong length (longer) 2, bars: bar length wrong (notes / rests do not add up like the truth bar) 2, ties: missing `tie` 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 1 Männer | 14 | lyrics: missing 5, barlines: missing `bar:light-light` 4, ties: missing `tie` 2, notes: note missing 2, notes: chord note missing 1 |
| anastasia 2 Violoncello | 14 | notes: note missing 3, words: made up 1, bars: bar missing (empty or rests only) 1, bars: extra bar (with notes) 1, words: missing 1, barlines: missing `bar:light-light` 1 |
| anastasia 2 Triangel | 13 | drums: hit missing 4, part: no output at all (every truth item below counts as missing) 1, clefs: missing `clef:percussion` 1, dynamics: missing `mp` 1, keys: missing `key:0` 1, times: missing `time:3/4` 1 |
| anastasia 2 Glockenbaum | 13 | bars: bar missing (empty or rests only) 3, barlines: missing `bar:light-light` 1, words: made up 1, drums: hit missing 1, dynamics: missing `p` 1, structure: missing `repeat:forward` 1 |
| anastasia 1 Posaune | 12 | barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 4, ties: missing `tie` 2, words: missing 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 2 Flöte 1 | 12 | words: made up 2, bars: bar length wrong (whole-bar rest with the wrong duration) 2, hairpins: missing `diminuendo` 1, slurs: made up `slur` 1, articulations: missing `caesura` 1, dynamics: missing `p` 1 |
| anastasia 4A Keyboard 1 | 12 | words: made up 3, notes: note missing 3, dynamics: missing `mf` 1, structure: missing `repeat:forward` 1, articulations: missing `staccato` 1, bars: bar length wrong (notes / rests do not add up like the truth bar) 1 |
| anastasia 4A (system items) | 12 | systemtext: made up 11, tempo: missing 1 |
| anastasia 2 Klarinette in B 1 | 11 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, barlines: missing `bar:light-light` 1, dynamics: missing `p` 1, hairpins: missing `crescendo` 1, words: made up 1, slurs: made up `slur` 1 |
| anastasia 2 Young Anastasia | 11 | words: missing 4, articulations: made up `staccato` 1, fermatas: missing `fermata` 1, articulations: made up `strong-accent` 1, lyrics: missing 1, barlines: missing `bar:light-light` 1 |
| anastasia 4A Klavierauszug | 10 | words: made up 2, fermatas: missing `fermata` 2, dynamics: made up `p` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, pitch: accidental missing 1 |
| ghost 1a Violoncello | 10 | bars: bar missing (empty or rests only) 2, bars: extra bar (empty) 2, pitch: one staff step off 1, dynamics: missing `pp` 1, hairpins: missing `crescendo` 1, dynamics: missing `p` 1 |
| ghost 1a Clarinet in Bb | 9 | slurs: made up `slur` 3, keys: wrong `key:7` instead of `key:-5` 1, fermatas: missing `fermata` 1, words: made up 1, ties: tie read as a slur 1, barlines: missing `bar:light-heavy` 1 |
| anastasia 1 Glockenbaum | 8 | barlines: missing `bar:light-light` 4, drums: hit missing 1, dynamics: missing `fp` 1, hairpins: missing `diminuendo` 1, words: made up 1 |
| anastasia 2 Schlagzeug | 8 | part: no output at all (every truth item below counts as missing) 1, clefs: missing `clef:percussion` 1, keys: missing `key:0` 1, times: missing `time:3/4` 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1 |
| anastasia 4A Keyboard 2 | 8 | words: made up 2, bars: bar length wrong (whole-bar rest with the wrong duration) 2, pitch: wrong by more than a third 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| ghost 1a (system items) | 8 | systemtext: made up 5, rehearsal: missing 2, systemtext: wrong 1 |
| anastasia 1 Klarinette in B 1 | 7 | barlines: missing `bar:light-light` 4, bars: bar length wrong (whole-bar rest with the wrong duration) 1, ties: missing `tie` 1, pitch: two staff steps off (a third) 1 |
| anastasia 1 Glockenspiel | 7 | barlines: missing `bar:light-light` 4, words: made up 1, dynamics: missing `p` 1, slurs: made up `slur` 1 |
| anastasia 4A Horn in F | 7 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, dynamics: missing `mf` 1, structure: missing `repeat:forward` 1, hairpins: missing `diminuendo` 1, structure: missing `repeat:backward` 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 1 Violoncello | 6 | barlines: missing `bar:light-light` 4, tremolos: missing `trem:single:3` 1, ties: missing `tie` 1 |
| anastasia 2 Flöte 2 | 6 | bars: bar length wrong (whole-bar rest with the wrong duration) 3, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Klarinette in B 1 | 6 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, ties: tie read as a slur 1, dynamics: missing `mf` 1, fermatas: made up `fermata` 1, hairpins: missing `diminuendo` 1 |
| anastasia 4A Kontrabass | 5 | rhythm: note at the wrong beat (onset shifted) 2, structure: missing `repeat:forward` 1, words: at the wrong beat 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Trompete in B | 5 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 4A Klarinette in B 2 | 4 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Violine 2 | 3 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, rhythm: note value x2 too long 1 |
| anastasia 4A Fagott | 3 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, words: made up 1 |
| anastasia 4A Posaune | 3 | structure: missing `repeat:forward` 1, ties: missing `tie` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Violoncello | 2 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |

## sheet_reader (vector glyph reader) on the Ghost parts

`~/sheet_reader` reads born-digital PDFs from their vector data: staff lines and barlines as drawn lines, notes,
rests, clefs, accidentals, articulations and dynamics as characters of the music fonts (`EngraverFontSet`,
`Maestro`, `MaestroPercussion`), mapped by `tools/glyph_map.py`. Pitch from the notehead's y position, length from
stem / beam / flag / dot geometry, ties from curved paths, `%` bars copied, triplets from a lone "3". It exports
MusicXML via music21. It was built against a Ghost full score (`GHOST_Partitur_Akt1.pdf`, one system per page) and
has no multi-rests, no key / clef changes inside a line, no slash notation, no grand staff, no transposition and no
articulations / dynamics / text in the export yet.

### Test

Scratch adapter (not in the repo): the part books have one staff per system and several systems per page, so the
staves of each page are chained in order into one part, barlines are taken per staff (`get_barlines` of that staff,
plus the staff's left edge as the first barline; `get_system_barlines` needs a barline through more than half the
staves of the page). Pages from the workbook. Run on the 14 Ghost truth parts it can do (not the piano
reductions, not the split Reed of 13): under 6 s per part. Glyph coverage on these pages is complete: every
music-font character on a page of each book has a `glyph_map` entry. Scored with `omrbench bench ghost --run sr`
(bench `sr1`) and this error report (`results/errors/sr`).

| part | bars out / truth | penalty sheet_reader | penalty pipeline | aligned note F1 sheet_reader | pipeline |
|---|---|---|---|---|---|
| 13 Cello | 156 / 199 | 442 | 209 | 0.760 | 0.876 |
| 13 Bass | 194 / 199 | 542 | 82 | 0.025 (8vb, see below) | 0.999 |
| 20 Violin | 116 / 135 | 475 | 54 | 0.542 | 0.989 |
| 20 Cello | 146 / 135 | 528 | 68 | 0.531 | 0.976 |
| 20 Drums | 132 / 135 | 773 | 256 | 0.638 | 0.918 |
| 20 Guitar | 135 / 135 | 1093 | 231 | 0.084 | 0.862 |
| 20 Utility | 329 / 135 | 1480 | 166 | 0.174 | 0.969 |
| 14 parts | | **7111** | **1341** | | |

Bars where every note is right (1132 truth bars with notes, same 14 parts): both 340, only the pipeline 663, only
sheet_reader **14**, neither 115. So as a full engine or as a per-bar vote it adds almost nothing today.

Why it loses: multi-rests read as one bar (13 Cello, 1a Cello 8 / 28 bars); key, clef and time changes inside a
line ignored (pitches after a mid-line key change are wrong); keyboards (grand staff) chained staff by staff, so the
bar count doubles (Utility 329 / 135); no `<transpose>` (Bass 8vb, Clarinet, Trumpet: the penalty takes it as one
bulk shift, but aligned F1 is 0); slash notation has no duration; and none of the marks are exported, so every
articulation, slur, dynamic and word counts as missing.

### Where it would help: exact marks on vector pages

The glyphs themselves are exact. Counted straight from the PDF pages vs pipeline output vs truth:

| part | marcato (strong accent) PDF / pipeline / truth | dynamics PDF / pipeline / truth | accents PDF / pipeline / truth |
|---|---|---|---|
| 13 Cello | 42 / 26 / 42 | 9 / 5 / 10 | 52 / 53 / 79 (truth adds them on "sim." bars) |
| 13 Bass | 0 / 0 / 0 | 7 / 3 / 6 | 13 / 10 / 34 (truth adds them on %-bars) |
| 20 Reed | 2 / 1 / 3 | 9 / 5 / 9 | 16 / 35 / 33 |
| 20 Trumpet | 2 / 0 / 3 | 9 / 4 / 7 | 16 / 35 / 36 |
| 1a Cello | – | 2 / 0 / 2 | – |

(Reed / Trumpet 20: 16 accent glyphs in the PDF but 33 / 36 in the truth, so the truth adds accents on bars the PDF
does not mark, e.g. written-out %-bars. Unmapped glyphs on those pages: `˘` ×20, `-` ×4 (tenuto; `pipeline/vector.py`
maps it), `˙` ×2 (the open notehead sheet_reader calls "half?"), `,` ×2, `¨` ×1.)

**Decision (user, 2026-10-16): sheet_reader stays an external project** (a friend develops it); nothing is built
inside it. museScribe already has its own small vector reader (`omrbench/pipeline/vector.py`: slash rhythms,
measure repeats, single-staff barlines). The ideas from sheet_reader worth taking over into museScribe, and the
feature requests for its developer, are in `docs/IMPROVEMENTS.md` #52 and `docs/sheet_reader_requests.md`.

### Re-test 2026-10-16 (sheet_reader `b6b04f0`, 47 commits later)

Same 14 parts, scratch adapter (each staff read as a one-staff system; marks to the nearest staff), run `sr2`,
bench `sr2`, error report `results/errors/sr2`. Edits left **6440** (was 7111) vs **1387** for the pipeline (`p1-t`);
bars note-perfect only in sheet_reader: 15 (was 14). New since the first test: mid-line key / clef / time changes,
export of articulations, dynamics, hairpins, metronome marks, chord symbols, lyrics, repeat barlines and voltas,
segno / coda / D.S., slash notation, ties over page breaks. Still missing: several systems per page, multi-rests,
grand staff, transposition (only from printed "in Bb"), slurs and barline types in the export, words / rehearsal
marks, fermatas (1 of 12). New problems: chord suffixes and "sim." read as lyrics (33), chord symbols on the wrong
beat (195 of 217), 3 made-up tuplets.

| category (penalty) | sheet_reader | pipeline | better |
|---|---|---|---|
| notes / pitch | 3839 | 375 | pipeline |
| articulations | 566 | 306 | pipeline (sheet_reader: few false ones, low recall) |
| dynamics | 33 | 58 | **sheet_reader** |
| hairpins | 21 | 21 | equal |
| ties / slurs | 466 / 279 | 164 / 136 | pipeline |
| repeats / voltas | 4 | 8 | **sheet_reader** (all 8 found) |
| key changes | 22 | 36 | **sheet_reader** |
| chords | 225 | 46 | pipeline |

Verdict: still no engine and no per-bar vote. Worth porting into `pipeline/vector.py` (not importing): dynamics from
glyphs (~20-25 actions), mid-line key glyphs (~10-15), repeat barlines and voltas (~5-8). Accents from glyphs were tried
in the pipeline and rejected (+13, `docs/TRUTH_DEVIATIONS.md`).

## Ghost 13 truth (checked bar by bar 2026-10-16, rechecked after the user's fixes)

Notes: every truth bar with notes agrees with the pipeline or sheet_reader. Marks, text, ties, slurs and barlines
checked by eye against the PDF, hairpin directions from the vector lines. All earlier findings are fixed; slurs
between two equal pitches are turned into ties when the truth is loaded. Left: an extra double barline after Bass
bar 55 (`docs/TRUTH_DEVIATIONS.md`).

## Decisions (2026-10-16)

- "sim." and %-bars: the output copies the pattern bar's articulations onto them, exactly like the truth
  (IMPROVEMENTS #47).
- Typographic quotes count as plain ones in the metric (`musicxml._norm_text`; reference `p1` 7336 -> 7342 as
  bench `p1-q`: quotes -16, Ghost 13 truth changes +22).
- sheet_reader: no code in its repo; ideas go to `docs/sheet_reader_requests.md`.
- A curve joining two neighbouring notes of the same pitch is a tie, a slur joins different pitches (applied to
  every truth in `truth.load`; reference `p1-q` 7342 -> `p1-t` 7377, together with the Ghost 13 truth fixes).
  Double barlines stay as printed.
