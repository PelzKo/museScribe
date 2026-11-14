# Error overview: output vs truth

What is still wrong in the pipeline output, element by element, with no weighting. The basis for the next
improvement round. State 2026-10-18: outputs `r3-f` (`results/<show>/runs/r3-f`, default `pipeline` at commit
`2ad9819`, reassembled from the work dirs of run `r3`), truths as of 2026-10-18: Anastasia 1, 2, 4 (finished,
all parts), 4A; Ghost 1a, 4, 5, 11a (new), 13 (Bass, Cello), 20. 129 truth parts, 32 814 truth notes, 10 songs.
Edit penalty of these outputs: **11 946** (Anastasia 5979, Ghost 5967; bench id `r3-f`).

Made with `python scripts/error_report.py anastasia,ghost --run r3-f` (about 40 s; writes
`results/errors/r3-f/errors.md` and `errors.json` with every location). Pairing, `plain` parts and `unfinished`
parts are the same as in `omrbench bench`. Bars are aligned like the edit penalty (DP over bars, whole-part
transposition, octave sections). Inside every matched bar each note and each marking is compared one to one,
and every difference is counted under a kind. One note can count several times: a Bb. read as a B quarter is
"accidental missing" plus "dot missing". The counts are not the edit penalty. They say what is wrong, not what
it costs; the cost per category is in the second table.

How notes are paired inside a bar: exact match first, then the same beat and pitch (gives a rhythm error), the
same beat and length (gives a pitch error), the same pitch and length on another beat (onset shifted), the same
beat (pitch and rhythm error). The rest is missing or made up. Markings: same token on another beat = "at the
wrong beat", another token on the same beat = "wrong X instead of Y", a slur on a beat where the truth has a tie =
"tie read as a slur". Rehearsal marks, tempi and system text are compared once per song, like the penalty.

## Summary (12 302 differences)

| group | total | Anastasia | Ghost | what most of it is |
|---|---|---|---|---|
| notes | 2118 | 697 | 1421 | Ghost 4 guitar: the truth writes the fingerpicking out under the slash bars (731); Ghost 20 / 5 piano, Anastasia 4 singers |
| articulations | 1560 | 674 | 886 | accents / staccatos missing (Ghost 5 bass, e-piano, drums, cello; Anastasia 4 keyboards, piano reduction, drum set); staccatos made up on Ghost keyboards / drums |
| drums | 1546 | 666 | 880 | Anastasia 4 drum set never written (592 hits); Ghost 4 / 5 drum kit 16th hi-hats read as 8 notes per bar |
| bars | 1263 | 702 | 561 | bars in the wrong place (an extra bar here, one missing there: Anastasia 4 Tamburin, Männer, Ghost 5 Frauen); 182 bars of the wrong length |
| barlines | 827 | 696 | 131 | double barlines never written (772; Anastasia 4: 21 in every part) |
| pitch | 757 | 437 | 320 | wrong by more than a third (Ghost 20 / 5 piano, Anastasia 4 Keyboard 1), accidentals missing / made up |
| lyrics | 639 | 430 | 209 | Anastasia 4 Dmitry (missing passages), Männer / Frauen (made up, wrong voice), Ghost 4 Sam / Molly |
| dynamics | 521 | 367 | 154 | missing mp / mf / p / f / sfz (Anastasia scans), made up p / f |
| rhythm | 502 | 202 | 300 | onsets shifted (157), Ghost 4 drum 16ths read 4x too long (115), x2 / 1/2 values on piano parts |
| slurs | 401 | 136 | 265 | made up 191, missing 184 (Ghost 4 guitar 70) |
| words | 400 | 278 | 122 | made up 253 (Anastasia 4 Keyboard 1, piano reduction labels), missing 122 (arco, pizz., gedämpft on Anastasia strings) |
| ties | 396 | 129 | 267 | missing 280 (Ghost 20 piano 67, guitar 20), made up 61, read as a slur 47 |
| structure | 318 | 233 | 85 | repeat signs never written (forward 162, backward 156) |
| hairpins | 263 | 199 | 64 | crescendo 163 / diminuendo 77 missing (Anastasia 4 Horn, Violine 1, Keyboard 1) |
| chords | 234 | 1 | 233 | Ghost piano reductions keep chord symbols in 1a / 4 / 11a (114 missing), made up 94, at the wrong beat 26 (Ghost 20 guitar) |
| clefs, tremolos, fermatas, keys, times | 400 | 251 | 149 | clefs on keyboards 119, single tremolos 94, fermatas 70, keys 68, times 49 |
| systemtext, instruments, rehearsal, tuplets, tempo, part, staff | 157 | 80 | 77 | |

Edit penalty by category (MuseScore actions, `r3-f`, part rows only; system items add 77):

| category | Anastasia | Ghost | total |
|---|---|---|---|
| notes (incl. drum hits, wrong notes) | 2008 | 2944 | 4952 |
| articulations | 659 | 878 | 1537 |
| barlines | 710 | 136 | 846 |
| lyrics | 434 | 209 | 643 |
| bars (insert / delete) | 353 | 207 | 560 |
| dynamics | 352 | 153 | 505 |
| slurs | 153 | 298 | 451 |
| ties | 130 | 281 | 411 |
| words | 274 | 121 | 395 |
| structure (repeats) | 238 | 94 | 332 |
| hairpins | 195 | 67 | 262 |
| barlen (bar of the wrong length) | 118 | 115 | 233 |
| chords | 1 | 215 | 216 |
| clefs / tremolos / fermatas / keys / times / instruments / rest | 321 | 205 | 526 |

Parts with the most differences: Ghost 4 Electric Guitar (971), Ghost 4 Drum Kit (864), Anastasia 4 Schlagzeug
(787, no output at all), Anastasia 4 Keyboard 1 (686), Ghost 20 Piano (553), Anastasia 4 Klavierauszug (461),
Ghost 5 Drum Kit (442), Anastasia 4 Männer (401), Ghost 5 Piano (321), Anastasia 4 Dmitry (319), Frauen (308),
Violine 1 (242), Ghost 4 Klavier (234), Ghost 20 Electric Guitar (233).

Bar counts (the user's priority, 2026-10-18: bar count and bar lengths must match the workbook): right in 115 of 126
scored parts (`r3-base` before round 3: about 66). The 11 left (Anastasia 4 Cello, Trombone, Keyboard 1, piano
reduction 212 / 211, Keyboard 1 213; Ghost 1a piano 29 / 28, 11a Reed 20 / 19, 20 Utility 136 / 135) have an extra
bar with notes, which the repairs do not delete.

## Systematic errors (what to fix next)

Ordered by the edit actions one fix would remove (estimates from the tables above and below; the ranked plan is in
`docs/IMPROVEMENTS.md`, "Round 4").

1. **Double barlines and repeat signs are never written (846 + 332 actions).** Every section change in the truths
   has a light-light barline (Anastasia 4: 21 per part, 34 parts); repeats 162 / 156. All parts of a song share
   them, so with the bar counts now right a vote across the parts' Audiveris barlines (like the fermatas) should
   place them; on vector pages the barline type is in the drawing.
2. **Anastasia 4 drum set never written (Schlagzeug 787, Tamburin 198).** The kit sections are marked "sticks"
   (no alias), and the boxed "Tambourine" (bar 32) switches the rest of the kit into the Tamburin part. In the
   truth only the labelled hits are Tamburin; the kit goes on in Schlagzeug.
3. **Ghost drum kits (Ghost 4: 864, Ghost 5: 442, Ghost 20: 230).** 16th hi-hats and snare on one beam plus the foot
   voice: the truth has 19 notes per bar, the output 8 (values read 4x too long, kit positions wrong 77). The page
   is vector: heads, stems, beams and flags are in the drawing (`pipeline/vector.py` reads them for slashes).
4. **Ghost 4 guitar fingerpicking (971).** Bars 1–4 are a 16th pattern, 5–9 and 12–14 are one-bar repeats (bars
   12–13 not written out), and from bar 15 the page prints slashes with chord symbols, but the truth writes the
   fingerpicking out over the chords (16 notes per bar, 731 missing). Not readable from the page; see the open
   question in `docs/IMPROVEMENTS.md`.
5. **Articulations on vector pages (Ghost 886 differences, 878 actions).** homr drops accents / staccatos on dense
   bars and makes staccatos up on keyboards; Ghost 5 Bass, Electric Piano, Drum Kit and Cello each miss about 50
   accents and 50 staccatos. The glyphs are exact on these pages (sheet_reader section below).
6. **Anastasia 4 singers (Männer 401, Dmitry 319, Frauen 308, Vlad 201; lyrics 434 actions).** Passages missing,
   bars shifted (Männer 131 notes inside missing bars), lyrics made up or in the wrong voice: the singer-label
   routing of the piano reduction.
7. **Dynamics and hairpins on the scans (505 + 262).** Missing mp / mf / p / f / sfz and crescendo / diminuendo
   hairpins on Anastasia 4 (Horn, Violine 1, Oboe, Keyboard 1). Needs the detector of IMPROVEMENTS #33.
8. **Ties and slurs on Ghost (ties 281, slurs 298).** Ghost 20 piano 67 ties missing, guitar 20; slurs made up
   and missing on piano parts. Read the curves from the vector drawing (IMPROVEMENTS #55).
9. **Bars in the wrong place and of the wrong length (bars 560, barlen 233).** With the count right, an extra bar
   early and a missing bar later still cost 2 + contents (Anastasia 1 Klarinette 2 bars 4–5, Anastasia 4
   Tamburin); 182 bars do not add up like the truth bar, 51 whole-bar rests have the wrong length.
10. **Smaller ones.** Chord symbols: Ghost 1a / 4 / 11a piano reductions keep them, Ghost 20 does not (tried on all
   Ghost piano reductions: +72, rejected); 26 guitar chords at the wrong beat (Ghost 20). Vocal cues under a singer
   label ("SAM:" in Ghost 4 Drums bar 2). Words made up on Anastasia 4 Keyboard 1 (28). Notes far below the bass
   staff (wrong by more than a third 246). Single tremolos 94, fermatas 70, clefs 119.

Fixed in round 3 (2026-10-18, `r3-base` 12 423 -> `r3-f` 11 946): held chords get a tie on every note (ties
-69); cue notes from another part's label up to "Play" (Ghost 11a, -29); fermatas shared across parts with the
song's bar count; extra rest bars dropped where the printed numbers show the output ahead, rest bars past the
workbook bar count trimmed, and the workbook bar count anchors the song end (-379 together).

## Full list by kind

Counts per show, the three parts with the most, and the first places (truth bar numbers; `#n` = n-th bar where
the truth bar number is not printable). Every location is in `results/errors/r3-f/errors.json`.

### notes (2118)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note missing | 1783 | ghost 1338, anastasia 445 | ghost 4 Electric Guitar 731, ghost 20 Piano 130, anastasia 4 Dmitry 111 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 1 bar 26 |
| note made up | 192 | anastasia 141, ghost 51 | anastasia 4 Keyboard 1 29, anastasia 4 Klarinette in B 2 16, anastasia 2 Keyboard 1 12 | anastasia 1 Kontrabass bar 28; anastasia 1 Kontrabass bar 29 |
| chord note missing | 78 | anastasia 55, ghost 23 | anastasia 4 Keyboard 1 24, anastasia 4 Frauen 9, ghost 4 Elektrisches Piano 8 | anastasia 1 Keyboard 1 bar 2; anastasia 1 Keyboard 1 bar 7 |
| extra chord note | 65 | anastasia 56, ghost 9 | anastasia 4 Frauen 34, anastasia 4 Männer 8, anastasia 4 Keyboard 1 5 | anastasia 2 Keyboard 1 bar 29; anastasia 4 Violine 2 bar 125 |

### articulations (1560)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `accent` | 620 | ghost 353, anastasia 267 | anastasia 4 Klavierauszug 67, anastasia 4 Keyboard 1 63, anastasia 4 Schlagzeug 63 | anastasia 1 Violine 1 bar 5; anastasia 1 Violine 1 bar 7 |
| missing `staccato` | 388 | ghost 255, anastasia 133 | anastasia 4 Keyboard 1 72, ghost 5 Electric Bass 56, ghost 5 Drum Kit 55 | anastasia 4 Violine 1 bar 1; anastasia 4 Violine 1 bar 2 |
| made up `staccato` | 195 | ghost 152, anastasia 43 | ghost 20 Electric Piano 38, ghost 4 Drum Kit 33, ghost 20 Drum Kit 23 | anastasia 1 Klavierauszug bar 2; anastasia 1 Klavierauszug bar 10 |
| missing `tenuto` | 147 | anastasia 139, ghost 8 | anastasia 4 Klavierauszug 65, anastasia 4A Violine 1 32, anastasia 4 Horn in F 25 | anastasia 1 Violine 1 bar 6; anastasia 1 Violine 1 bar 7 |
| at the wrong beat `accent` | 44 | ghost 40, anastasia 4 | ghost 4 Drum Kit 35, ghost 20 Electric Guitar 4, anastasia 4 Keyboard 1 2 | anastasia 4 Oboe bar 43; anastasia 4 Keyboard 1 bar 32 |
| made up `accent` | 38 | ghost 22, anastasia 16 | ghost 20 Drum Kit 9, anastasia 4 Oboe 4, anastasia 4 Keyboard 1 4 | anastasia 1 Klavierauszug bar 10; anastasia 4 Oboe bar 106 |
| missing `strong-accent` | 30 | ghost 20, anastasia 10 | ghost 13 Cello 14, anastasia 4 Klavierauszug 5, ghost 20 Trumpet in Bb 3 | anastasia 4 Violine 1 bar 81; anastasia 4 Violine 1 bar 202 |
| made up `tenuto` | 23 | anastasia 17, ghost 6 | anastasia 1 Keyboard 1 6, anastasia 1 Klavierauszug 6, anastasia 4 Oboe 2 | anastasia 1 Keyboard 1 bar 9; anastasia 1 Klavierauszug bar 21 |
| made up `strong-accent` | 19 | ghost 15, anastasia 4 | ghost 20 Piano 12, anastasia 1 Klavierauszug 1, anastasia 2 The Dowager Empress 1 | anastasia 1 Klavierauszug bar 6; anastasia 2 The Dowager Empress bar 30 |
| at the wrong beat `staccato` | 13 | anastasia 10, ghost 3 | anastasia 4 Keyboard 1 5, anastasia 4 Klavierauszug 5, ghost 20 Violoncello 2 | anastasia 4 Keyboard 1 bar 89; anastasia 4 Keyboard 1 bar 98 |
| made up `caesura` | 6 | ghost 5, anastasia 1 | anastasia 2 Keyboard 1 1, ghost 5 Electric Piano 1, ghost 20 Violoncello 1 | anastasia 2 Keyboard 1 bar 29; ghost 5 Electric Piano bar 2 |
| wrong `accent` instead of `tenuto` | 6 | anastasia 5, ghost 1 | anastasia 4 Klavierauszug 3, anastasia 4 Oboe 2, ghost 20 Trumpet in Bb 1 | anastasia 4 Oboe bar 113; anastasia 4 Oboe bar 142 |
| wrong `staccato` instead of `accent` | 5 | anastasia 5 | anastasia 4 Klavierauszug 3, anastasia 4 Keyboard 1 1, anastasia 4 Frauen 1 | anastasia 4 Keyboard 1 bar 73; anastasia 4 Klavierauszug bar 42 |
| wrong `staccato` instead of `tenuto` | 4 | anastasia 3, ghost 1 | anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 1, ghost 20 Clarinet in Bb 1 | anastasia 4 Keyboard 1 bar 92; anastasia 4 Klavierauszug bar 158 |
| wrong `accent` instead of `strong-accent` | 3 | ghost 2, anastasia 1 | ghost 13 Cello 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 206; ghost 13 Cello bar 40 |
| missing `falloff` | 3 | anastasia 2, ghost 1 | anastasia 4 Keyboard 1 2, ghost 13 Bass 1 | anastasia 4 Keyboard 1 bar 70; anastasia 4 Keyboard 1 bar 137 |
| missing `caesura` | 2 | anastasia 2 | anastasia 2 Flöte 1 1, anastasia 2 Glockenspiel 1 | anastasia 2 Flöte 1 bar 29; anastasia 2 Glockenspiel bar 29 |
| missing `breath-mark` | 2 | anastasia 2 | anastasia 2 The Dowager Empress 1, anastasia 4 Frauen 1 | anastasia 2 The Dowager Empress bar 24; anastasia 4 Frauen bar 73 |
| wrong `staccatissimo` instead of `staccato` | 2 | anastasia 2 | anastasia 4 Violine 1 2 | anastasia 4 Violine 1 bar 44; anastasia 4 Violine 1 bar 52 |
| at the wrong beat `tenuto` | 2 | anastasia 2 | anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 81; anastasia 4 Klavierauszug bar 159 |
| made up `staccatissimo` | 2 | anastasia 2 | anastasia 4 Klavierauszug 1, anastasia 4 Frauen 1 | anastasia 4 Klavierauszug bar 113; anastasia 4 Frauen bar 69 |
| wrong `accent` instead of `staccato` | 2 | ghost 2 | ghost 20 Clarinet in Bb 1, ghost 20 Trumpet in Bb 1 | ghost 20 Clarinet in Bb bar 90; ghost 20 Trumpet in Bb bar 90 |
| wrong `tenuto` instead of `staccato` | 1 | anastasia 1 | anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 172 |
| missing `scoop` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 138 |
| missing `doit` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 51 |
| wrong `strong-accent` instead of `accent` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 202 |

### drums (1546)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| hit missing | 1416 | ghost 784, anastasia 632 | anastasia 4 Schlagzeug 592, ghost 4 Drum Kit 457, ghost 5 Drum Kit 260 | anastasia 1 Splash-Becken bar 3; anastasia 1 Splash-Becken bar 4 |
| wrong kit instrument (staff position) | 105 | ghost 85, anastasia 20 | ghost 4 Drum Kit 77, anastasia 4 Tamburin 7, anastasia 4 Xylophon 7 | anastasia 1 Splash-Becken bar 2; anastasia 2 Splash-Becken bar 64 |
| hit made up | 25 | anastasia 14, ghost 11 | anastasia 4 Tamburin 9, ghost 4 Drum Kit 9, anastasia 4 Triangel 2 | anastasia 4 Tamburin bar 61; anastasia 4 Tamburin bar 140 |

### bars (1263)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note inside a missing bar | 311 | anastasia 172, ghost 139 | anastasia 4 Männer 131, ghost 4 Electric Guitar 65, ghost 20 Drum Kit 26 | anastasia 4 Violine 1 bar 129; anastasia 4 Violoncello bar 120 |
| extra bar (with notes) | 226 | anastasia 160, ghost 66 | anastasia 4 Tamburin 48, anastasia 4 Männer 26, ghost 5 Frauen 20 | anastasia 1 Klarinette in B 2 (extra bar after output bar 4); anastasia 1 Klarinette in B 2 (extra bar after output bar 5) |
| bar missing (empty or rests only) | 209 | anastasia 139, ghost 70 | anastasia 4 Tamburin 42, ghost 5 Frauen 20, anastasia 4 Vlad 12 | anastasia 1 Klarinette in B 2 bar 4; anastasia 1 Klarinette in B 2 bar 5 |
| bar length wrong (notes / rests do not add up like the truth bar) | 182 | ghost 94, anastasia 88 | ghost 20 Drum Kit 17, ghost 5 Violoncello 15, ghost 20 Electric Guitar 11 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 1 bar 26 |
| marking inside a missing bar | 159 | ghost 100, anastasia 59 | ghost 20 Electric Guitar 14, anastasia 4 Tamburin 13, anastasia 4 Männer 13 | anastasia 1 Klarinette in B 2 bar 4; anastasia 1 Klarinette in B 2 bar 5 |
| bar missing (with notes) | 65 | anastasia 33, ghost 32 | anastasia 4 Männer 18, ghost 4 Klavier 9, anastasia 4 Tamburin 6 | anastasia 4 Violine 1 bar 129; anastasia 4 Violoncello bar 120 |
| extra bar (empty) | 60 | ghost 39, anastasia 21 | ghost 4 Electric Guitar 8, ghost 13 Cello 7, anastasia 4 Violine 1 5 | anastasia 2 Keyboard 1 (extra bar after output bar 45); anastasia 4 Violine 1 (extra bar after output bar 26) |
| bar length wrong (whole-bar rest with the wrong duration) | 51 | anastasia 30, ghost 21 | ghost 4 Electric Guitar 12, anastasia 2 Keyboard 1 5, anastasia 4 Xylophon 4 | anastasia 1 Splash-Becken bar 5; anastasia 2 Violine 1 bar 54 |

### barlines (827)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `bar:light-light` | 772 | anastasia 686, ghost 86 | anastasia 4 Violine 1 21, anastasia 4 Violine 2 21, anastasia 4 Violoncello 21 | anastasia 1 Violine 1 bar 5; anastasia 1 Violine 1 bar 9 |
| missing `bar:light-heavy` | 45 | ghost 41, anastasia 4 | ghost 4 Violin 4, ghost 4 Violoncello 4, ghost 4 Electric Bass 4 | whole part; anastasia 4 Keyboard 2 bar 206 |
| at the wrong beat `bar:light-heavy` | 7 | anastasia 4, ghost 3 | anastasia 4A Horn in F 1, anastasia 4A Trompete in B 1, anastasia 4A Keyboard 2 1 | anastasia 4A Horn in F bar 6; anastasia 4A Trompete in B bar 6 |
| made up `bar:light-heavy` | 3 | anastasia 2, ghost 1 | anastasia 4 Dmitry 1, anastasia 4 Vlad 1, ghost 5 Electric Piano 1 | anastasia 4 Dmitry bar 206; anastasia 4 Vlad bar 206 |

### pitch (757)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| wrong by more than a third | 246 | ghost 150, anastasia 96 | ghost 20 Piano 58, ghost 5 Piano 34, anastasia 4 Keyboard 1 23 | anastasia 1 Klavierauszug bar 23; anastasia 4 Violine 1 bar 70 |
| accidental missing | 125 | anastasia 100, ghost 25 | anastasia 4 Klarinette in B 2 18, ghost 20 Piano 17, anastasia 4 Keyboard 1 16 | anastasia 2 Klarinette in B 2 bar 69; anastasia 4 Violine 1 bar 33 |
| accidental made up | 116 | anastasia 114, ghost 2 | anastasia 4 Keyboard 1 33, anastasia 4 Violine 2 14, anastasia 4 Klarinette in B 2 14 | anastasia 2 Keyboard 1 bar 57; anastasia 4 Violine 1 bar 6 |
| one staff step off | 72 | ghost 46, anastasia 26 | ghost 20 Piano 29, anastasia 4 Keyboard 1 8, anastasia 4 Violine 2 7 | anastasia 1 Piccolo bar 1; anastasia 1 Flöte 2 bar 4 |
| octave off (+1) | 48 | anastasia 34, ghost 14 | anastasia 4 Keyboard 2 17, anastasia 1 Klavierauszug 8, ghost 20 Piano 5 | anastasia 1 Keyboard 1 bar 1; anastasia 1 Klavierauszug bar 17 |
| two staff steps off (a third) | 41 | ghost 31, anastasia 10 | ghost 20 Piano 15, ghost 5 Piano 7, ghost 20 Clarinet in Bb 3 | anastasia 1 Flöte 2 bar 4; anastasia 2 Keyboard 2 bar 9 |
| one staff step off + accidental | 29 | anastasia 19, ghost 10 | anastasia 4 Keyboard 1 10, ghost 20 Piano 9, anastasia 4 Klarinette in B 2 3 | anastasia 4 Violoncello bar 70; anastasia 4 Oboe bar 51 |
| octave off (-1) | 25 | anastasia 14, ghost 11 | anastasia 1 Klavierauszug 11, ghost 4 Elektrisches Piano 11, anastasia 4 Klarinette in B 2 1 | anastasia 1 Klavierauszug bar 21; anastasia 1 Klavierauszug bar 25 |
| bar in an octave-off section (-1 octave) | 21 | ghost 18, anastasia 3 | ghost 20 Electric Piano 16, anastasia 4 Keyboard 2 2, ghost 4 Elektrisches Piano 2 | anastasia 1 Klavierauszug bar 23; anastasia 4 Keyboard 2 bar 168 |
| bar in an octave-off section (+1 octave) | 21 | anastasia 11, ghost 10 | ghost 4 Sam 6, anastasia 4 Männer 5, ghost 4 Elektrisches Piano 4 | anastasia 4 Posaune bar 197; anastasia 4 Keyboard 1 bar 153 |
| wrong accidental | 8 | anastasia 6, ghost 2 | anastasia 4 Klavierauszug 6, ghost 4 Elektrisches Piano 2 | anastasia 4 Klavierauszug bar 51; anastasia 4 Klavierauszug bar 81 |
| bar in an octave-off section (+2 octave) | 3 | anastasia 3 | anastasia 4 Männer 3 | anastasia 4 Männer bar 65; anastasia 4 Männer bar 66 |
| octave off (+2) | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 1 |
| octave off (-2) | 1 | ghost 1 | ghost 5 Piano 1 | ghost 5 Piano bar 25 |

### lyrics (639)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing | 370 | anastasia 210, ghost 160 | anastasia 4 Dmitry 123, ghost 4 Sam 98, ghost 4 Molly 52 | anastasia 1 Frauen bar 6; anastasia 1 Frauen bar 7 — e.g. "v1:a" ×15, "v1:the" ×10, "v1:ah" ×8, "v1:and" ×6 |
| made up | 146 | anastasia 140, ghost 6 | anastasia 4 Männer 80, anastasia 4 Frauen 35, anastasia 4 Vlad 23 | anastasia 4 Männer bar 5; anastasia 4 Männer bar 6 — e.g. "v1:you" ×6, "v1:it" ×5, "v1:a" ×5, "v1:the" ×4 |
| wrong | 112 | anastasia 69, ghost 43 | anastasia 4 Frauen 38, ghost 4 Molly 24, ghost 5 Frauen 16 | anastasia 1 Frauen bar 10; anastasia 2 The Dowager Empress bar 22 — e.g. "v1:my / v1:roy" ×4, "v1:tvvo / v1:two" ×2, "v2:a / v1:a" ×2, "v2:you / v1:you" ×2 |
| at the wrong beat | 11 | anastasia 11 | anastasia 4 Frauen 4, anastasia 4 Dmitry 4, anastasia 4 Vlad 3 | anastasia 4 Frauen bar 3; anastasia 4 Frauen bar 5 |

### dynamics (521)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `mp` | 67 | anastasia 45, ghost 22 | anastasia 4 Keyboard 1 12, anastasia 4 Horn in F 11, anastasia 4 Oboe 9 | anastasia 2 Violine 1 bar 66; anastasia 2 Keyboard 1 bar 25 |
| missing `mf` | 62 | anastasia 45, ghost 17 | anastasia 4 Keyboard 1 9, anastasia 4 Oboe 7, anastasia 4 Schlagzeug 7 | anastasia 1 Violine 1 bar 1; anastasia 1 Piccolo bar 1 |
| made up `p` | 56 | anastasia 37, ghost 19 | anastasia 4 Violine 1 6, anastasia 4 Keyboard 1 6, anastasia 4 Oboe 5 | anastasia 1 Flöte 1 bar 18; anastasia 1 Keyboard 1 bar 27 |
| missing `p` | 53 | anastasia 41, ghost 12 | anastasia 4 Oboe 7, anastasia 4 Horn in F 6, anastasia 4 Keyboard 1 4 | anastasia 1 Flöte 1 bar 14; anastasia 1 Flöte 1 bar 20 |
| missing `f` | 42 | ghost 25, anastasia 17 | ghost 20 Violin 6, ghost 20 Violoncello 6, anastasia 4 Keyboard 1 4 | anastasia 1 Piccolo bar 2; anastasia 1 Horn in F bar 2 |
| missing `sfz` | 39 | anastasia 38, ghost 1 | anastasia 4 Horn in F 9, anastasia 4 Keyboard 1 8, anastasia 4 Schlagzeug 8 | anastasia 4 Violine 1 bar 1; anastasia 4 Violine 1 bar 32 |
| made up `f` | 33 | anastasia 17, ghost 16 | anastasia 4 Klavierauszug 6, ghost 20 Drum Kit 3, ghost 20 Piano 3 | anastasia 1 Piccolo bar 1; anastasia 1 Horn in F bar 1 |
| made up `mf` | 21 | anastasia 15, ghost 6 | anastasia 4 Keyboard 1 6, anastasia 4 Oboe 2, anastasia 4 Horn in F 2 | anastasia 1 Keyboard 1 bar 6; anastasia 4 Violine 1 bar 1 |
| missing `ff` | 20 | anastasia 11, ghost 9 | anastasia 4 Piccolo 3, anastasia 4 Schlagzeug 3, anastasia 4 Horn in F 2 | anastasia 4 Violine 1 bar 181; anastasia 4 Piccolo bar 181 |
| made up `mp` | 20 | anastasia 17, ghost 3 | anastasia 4 Keyboard 1 11, anastasia 4 Horn in F 4, anastasia 4 Oboe 2 | anastasia 4 Oboe bar 109; anastasia 4 Oboe bar #151 |
| missing `fz` | 15 | anastasia 13, ghost 2 | anastasia 4 Horn in F 4, anastasia 4 Violine 1 2, anastasia 4 Oboe 2 | anastasia 4 Violine 1 bar 51; anastasia 4 Violine 1 bar 177 |
| missing `fp` | 8 | anastasia 4, ghost 4 | ghost 20 Clarinet in Bb 2, ghost 20 Trumpet in Bb 2, anastasia 1 Violine 1 1 | anastasia 1 Violine 1 bar 10; anastasia 1 Keyboard 1 bar 10 |
| at the wrong beat `mf` | 7 | anastasia 6, ghost 1 | anastasia 4 Violine 1 3, anastasia 4 Klavierauszug 2, anastasia 2 Keyboard 1 1 | anastasia 2 Keyboard 1 bar 1; anastasia 4 Violine 1 bar 137 |
| made up `sfz` | 7 | anastasia 6, ghost 1 | anastasia 4 Violine 1 3, anastasia 4 Oboe 1, anastasia 4 Horn in F 1 | anastasia 4 Violine 1 bar 36; anastasia 4 Violine 1 bar 47 |
| made up `sf` | 7 | ghost 4, anastasia 3 | ghost 20 Electric Guitar 2, ghost 20 Piano 2, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 202; anastasia 4 Frauen bar 42 |
| made up `pp` | 5 | anastasia 4, ghost 1 | anastasia 1 Horn in F 1, anastasia 1 Klavierauszug 1, anastasia 2 Violine 1 1 | anastasia 1 Horn in F bar 18; anastasia 1 Klavierauszug bar 30 |
| missing `pp` | 5 | anastasia 4, ghost 1 | anastasia 4 Schlagzeug 2, anastasia 1 Horn in F 1, anastasia 2 Splash-Becken 1 | anastasia 1 Horn in F bar 20; anastasia 2 Splash-Becken bar 64 |
| made up `ff` | 5 | anastasia 3, ghost 2 | anastasia 1 Klavierauszug 1, anastasia 4 Keyboard 1 1, anastasia 4 Tamburin 1 | anastasia 1 Klavierauszug bar 30; anastasia 4 Keyboard 1 bar 173 |
| at the wrong beat `mp` | 5 | anastasia 5 | anastasia 4 Horn in F 2, anastasia 2 Glockenspiel 1, anastasia 4 Oboe 1 | anastasia 2 Glockenspiel bar 1; anastasia 4 Oboe bar 160 |
| made up `fp` | 4 | anastasia 2, ghost 2 | ghost 4 Drum Kit 2, anastasia 1 Keyboard 1 1, anastasia 4 Keyboard 1 1 | anastasia 1 Keyboard 1 bar 10; anastasia 4 Keyboard 1 bar 74 |
| at the wrong beat `f` | 4 | ghost 3, anastasia 1 | ghost 20 Piano 3, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 69; ghost 20 Piano bar 1 |
| missing `fff` | 4 | anastasia 4 | anastasia 4 Piccolo 1, anastasia 4 Keyboard 1 1, anastasia 4 Schlagzeug 1 | anastasia 4 Piccolo bar 205; anastasia 4 Keyboard 1 bar 205 |
| made up `fz` | 3 | anastasia 3 | anastasia 4 Violine 1 1, anastasia 4 Oboe 1, anastasia 4 Horn in F 1 | anastasia 4 Violine 1 bar 55; anastasia 4 Oboe bar 24 |
| wrong `p` instead of `mp` | 3 | anastasia 2, ghost 1 | anastasia 4 Violine 1 1, anastasia 4 Frauen 1, ghost 4 Violoncello 1 | anastasia 4 Violine 1 bar 74; anastasia 4 Frauen bar 68 |
| wrong `p` instead of `mf` | 3 | anastasia 3 | anastasia 4 Violine 1 1, anastasia 4 Keyboard 1 1, anastasia 4A Violine 1 1 | anastasia 4 Violine 1 bar 164; anastasia 4 Keyboard 1 bar 164 |
| at the wrong beat `p` | 3 | anastasia 2, ghost 1 | anastasia 4 Oboe 1, anastasia 4 Keyboard 1 1, ghost 5 Trumpet in Bb 1 | anastasia 4 Oboe bar 71; anastasia 4 Keyboard 1 bar 29 |
| missing `sffz` | 3 | anastasia 3 | anastasia 4 Piccolo 1, anastasia 4 Horn in F 1, anastasia 4 Schlagzeug 1 | anastasia 4 Piccolo bar 206; anastasia 4 Horn in F bar 206 |
| made up `fff` | 2 | anastasia 2 | anastasia 4 Horn in F 1, anastasia 4 Keyboard 1 1 | anastasia 4 Horn in F bar 180; anastasia 4 Keyboard 1 bar 176 |
| wrong `f` instead of `fp` | 1 | anastasia 1 | anastasia 1 Frauen 1 | anastasia 1 Frauen bar 10 |
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
| wrong `mp` instead of `fz` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 177 |
| wrong `f` instead of `sfz` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 51 |
| wrong `ff` instead of `sffz` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 206 |
| wrong `mf` instead of `f` | 1 | ghost 1 | ghost 20 Drum Kit 1 | ghost 20 Drum Kit bar 74 |

### rhythm (502)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note at the wrong beat (onset shifted) | 157 | ghost 86, anastasia 71 | ghost 4 Drum Kit 33, anastasia 4 Klavierauszug 26, anastasia 4 Keyboard 1 22 | anastasia 1 Keyboard 2 bar 7; anastasia 2 Keyboard 1 bar 1 |
| note value x4 too long | 121 | ghost 120, anastasia 1 | ghost 4 Drum Kit 115, ghost 20 Piano 4, anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 70; ghost 4 Drum Kit bar 16 |
| note value x2 too long | 91 | ghost 57, anastasia 34 | ghost 5 Piano 24, ghost 20 Piano 15, ghost 20 Electric Guitar 8 | anastasia 1 Flöte 2 bar 4; anastasia 1 Horn in F bar 26 |
| note value 1/2 too short | 60 | anastasia 41, ghost 19 | anastasia 4 Keyboard 1 11, anastasia 4 Keyboard 2 10, anastasia 4 Klavierauszug 9 | anastasia 1 Splash-Becken bar 2; anastasia 1 Klavierauszug bar 23 |
| same length, other notation | 36 | anastasia 36 | anastasia 1 Violine 1 6, anastasia 1 Violine 2 6, anastasia 1 Flöte 2 6 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| dot missing | 11 | ghost 9, anastasia 2 | ghost 20 Piano 4, ghost 5 Piano 2, ghost 20 Drum Kit 2 | anastasia 4 Klarinette in B 2 bar 84; anastasia 4 Horn in F bar 79 |
| other wrong length (longer) | 10 | anastasia 6, ghost 4 | anastasia 1 Flöte 1 2, anastasia 1 Fagott 2, ghost 4 Drum Kit 2 | anastasia 1 Flöte 1 bar 26; anastasia 1 Flöte 1 bar 27 |
| dot made up | 5 | ghost 3, anastasia 2 | ghost 5 Piano 2, anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 26; anastasia 4 Klavierauszug bar 169 |
| tuplet made up | 5 | anastasia 4, ghost 1 | anastasia 4 Klavierauszug 4, ghost 4 Drum Kit 1 | anastasia 4 Klavierauszug bar 137; ghost 4 Drum Kit bar 75 |
| triplet / tuplet missing | 4 | anastasia 4 | anastasia 1 Piccolo 2, anastasia 1 Klarinette in B 2 1, anastasia 4 Klarinette in B 2 1 | anastasia 1 Piccolo bar 1; anastasia 1 Klarinette in B 2 bar 2 |
| note value 1/4 too short | 2 | anastasia 1, ghost 1 | anastasia 4 Keyboard 1 1, ghost 20 Drum Kit 1 | anastasia 4 Keyboard 1 bar 23; ghost 20 Drum Kit bar 100 |

### slurs (401)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `slur` | 191 | ghost 102, anastasia 89 | ghost 20 Piano 25, anastasia 4 Klavierauszug 19, ghost 5 Piano 15 | anastasia 1 Piccolo bar 1; anastasia 1 Piccolo bar 5 |
| missing `slur` | 184 | ghost 145, anastasia 39 | ghost 4 Electric Guitar 70, ghost 20 Piano 15, anastasia 4 Keyboard 1 13 | anastasia 1 Keyboard 1 bar 7; anastasia 1 Frauen bar 9 |
| at the wrong beat `slur` | 26 | ghost 18, anastasia 8 | anastasia 4 Violine 1 4, anastasia 4 Keyboard 1 3, ghost 20 Violoncello 3 | anastasia 4 Violine 1 bar 77; anastasia 4 Violine 1 bar 81 |

### words (400)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 253 | anastasia 166, ghost 87 | anastasia 4 Keyboard 1 28, anastasia 1 Klavierauszug 13, anastasia 4 Frauen 12 | anastasia 1 Violine 1 bar 14; anastasia 1 Violine 1 bar 27 — e.g. "solo" ×19, "str. ens. (loco)" ×6, "on to m. 13" ×5, "glock" ×4 |
| missing | 122 | anastasia 98, ghost 24 | anastasia 4 Violine 1 19, anastasia 4 Violoncello 16, anastasia 4 Violine 2 14 | anastasia 1 Posaune bar 20; anastasia 1 Klavierauszug bar 8 — e.g. "arco" ×33, "pizz." ×25, "cresc." ×7, "offen" ×5 |
| at the wrong beat | 13 | anastasia 12, ghost 1 | anastasia 4 Posaune 3, anastasia 4 Violoncello 2, anastasia 4 Horn in F 2 | anastasia 4 Violoncello bar 78; anastasia 4 Violoncello bar 157 |
| wrong | 12 | ghost 10, anastasia 2 | anastasia 4 Violine 1 2, ghost 4 Clarinet in Bb 2, ghost 20 Electric Piano 2 | anastasia 4 Violine 1 bar 29; anastasia 4 Violine 1 bar 58 — e.g. "[to 29 / pizz." ×1, "p000 apoco / cresc." ×1, "molto legato / zu akustische gitarre" ×1, "piano/ / zu oboe" ×1 |

### ties (396)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `tie` | 280 | ghost 200, anastasia 80 | ghost 20 Piano 67, ghost 20 Electric Guitar 20, anastasia 4 Schlagzeug 16 | anastasia 1 Flöte 1 bar 26; anastasia 1 Keyboard 2 bar 10 |
| made up `tie` | 61 | ghost 33, anastasia 28 | ghost 4 Klavier 8, anastasia 4 Klavierauszug 5, anastasia 4 Fagott 4 | anastasia 4 Violine 1 bar 6; anastasia 4 Violine 1 bar 29 |
| tie read as a slur | 47 | ghost 29, anastasia 18 | ghost 20 Piano 11, anastasia 4 Keyboard 1 6, anastasia 4 Klavierauszug 6 | anastasia 1 Klavierauszug bar 22; anastasia 1 Klavierauszug bar 26 |
| at the wrong beat `tie` | 8 | ghost 5, anastasia 3 | anastasia 4 Klavierauszug 3, ghost 5 Electric Guitar 2, ghost 4 Molly 1 | anastasia 4 Klavierauszug bar 24; anastasia 4 Klavierauszug bar 147 |

### structure (318)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `repeat:forward` | 162 | anastasia 118, ghost 44 | anastasia 4 Violine 1 3, anastasia 4 Violine 2 3, anastasia 4 Violoncello 3 | anastasia 2 Violine 1 bar #73; anastasia 2 Violine 2 bar #73 |
| missing `repeat:backward` | 156 | anastasia 115, ghost 41 | anastasia 4 Violine 1 3, anastasia 4 Violine 2 3, anastasia 4 Violoncello 3 | anastasia 2 Violine 1 bar #73; anastasia 2 Violine 2 bar #73 |

### hairpins (263)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `crescendo` | 163 | anastasia 135, ghost 28 | anastasia 4 Horn in F 27, anastasia 4 Violine 1 22, anastasia 4 Keyboard 1 22 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 1 bar 8 |
| missing `diminuendo` | 77 | anastasia 46, ghost 31 | anastasia 4 Violine 1 9, anastasia 4 Keyboard 1 7, anastasia 4 Oboe 6 | anastasia 1 Violine 1 bar 10; anastasia 1 Violine 1 bar 32 |
| made up `crescendo` | 9 | anastasia 8, ghost 1 | anastasia 4 Klavierauszug 5, anastasia 4 Keyboard 1 2, anastasia 4 Horn in F 1 | anastasia 4 Horn in F bar 165; anastasia 4 Keyboard 1 bar 162 |
| at the wrong beat `crescendo` | 8 | anastasia 6, ghost 2 | anastasia 4 Klavierauszug 3, anastasia 1 Klavierauszug 1, anastasia 4 Violine 1 1 | anastasia 1 Klavierauszug bar 1; anastasia 4 Violine 1 bar 199 |
| made up `diminuendo` | 4 | anastasia 2, ghost 2 | anastasia 4 Klavierauszug 2, ghost 5 Piano 1, ghost 11a Piano 1 | anastasia 4 Klavierauszug bar 6; anastasia 4 Klavierauszug bar 14 |
| at the wrong beat `diminuendo` | 2 | anastasia 2 | anastasia 4 Klavierauszug 2 | anastasia 4 Klavierauszug bar 114; anastasia 4 Klavierauszug bar 119 |

### chords (234)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing | 114 | ghost 114 | ghost 4 Klavier 59, ghost 11a Piano 22, ghost 1a Piano 11 | ghost 1a Electric Guitar bar 12; ghost 1a Electric Guitar bar 13 — e.g. "C:major" ×15, "C:major/E" ×12, "G:suspended-fourth" ×11, "F:major" ×10 |
| made up | 94 | ghost 93, anastasia 1 | ghost 4 Electric Guitar 38, ghost 4 Klavier 26, ghost 20 Piano 16 | anastasia 4 Klavierauszug bar 136; ghost 1a Electric Guitar bar 11 — e.g. "F:major" ×21, "G:suspended-fourth" ×16, "C:major" ×13, "A:minor" ×9 |
| at the wrong beat | 26 | ghost 26 | ghost 20 Electric Guitar 21, ghost 1a Electric Guitar 3, ghost 4 Electric Guitar 1 | ghost 1a Electric Guitar bar 9; ghost 1a Electric Guitar bar 16 |

### clefs (119)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `clef:G2` | 36 | anastasia 20, ghost 16 | anastasia 4 Keyboard 1 6, anastasia 4 Keyboard 2 4, ghost 20 Piano 4 | anastasia 1 Pauken bar 9; anastasia 1 Klavierauszug bar 30 |
| made up `clef:F4` | 30 | anastasia 19, ghost 11 | anastasia 4 Keyboard 1 7, anastasia 4 Keyboard 2 4, anastasia 4 Klavierauszug 4 | anastasia 1 Klarinette in B 2 bar 6; anastasia 1 Keyboard 1 bar 17 |
| missing `clef:F4` | 16 | anastasia 10, ghost 6 | anastasia 4 Klavierauszug 4, anastasia 4 Keyboard 1 3, anastasia 1 Klavierauszug 2 | anastasia 1 Klavierauszug bar 6; anastasia 1 Klavierauszug bar 24 |
| missing `clef:G2` | 16 | anastasia 8, ghost 8 | ghost 20 Piano 4, anastasia 1 Klavierauszug 2, anastasia 4 Keyboard 1 2 | anastasia 1 Klavierauszug bar 23; anastasia 1 Klavierauszug bar 31 |
| wrong `clef:G2` instead of `clef:G2^-1` | 4 | ghost 4 | ghost 1a Electric Guitar 1, ghost 5 Electric Guitar 1, ghost 11a Electric Guitar 1 | ghost 1a Electric Guitar bar 1; ghost 5 Electric Guitar bar 1 |
| missing `clef:percussion` | 3 | anastasia 3 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1, anastasia 4 Schlagzeug 1 | whole part |
| wrong `clef:percussion` instead of `clef:G2` | 2 | anastasia 2 | anastasia 4 Xylophon 1, anastasia 4A Xylophon 1 | anastasia 4 Xylophon bar 1; anastasia 4A Xylophon bar 1 |
| made up `clef:percussion` | 2 | anastasia 1, ghost 1 | anastasia 4 Xylophon 1, ghost 5 Electric Piano 1 | anastasia 4 Xylophon bar 172; ghost 5 Electric Piano bar 22 |
| made up `clef:G2^-1` | 2 | ghost 2 | ghost 4 Sam 1, ghost 5 Männer 1 | ghost 4 Sam bar 58; ghost 5 Männer bar 28 |
| at the wrong beat `clef:G2` | 1 | anastasia 1 | anastasia 4 Keyboard 1 1 | anastasia 4 Keyboard 1 bar 51 |
| at the wrong beat `clef:F4` | 1 | anastasia 1 | anastasia 4 Klavierauszug 1 | anastasia 4 Klavierauszug bar 184 |
| made up `clef:C3` | 1 | anastasia 1 | anastasia 4 Frauen 1 | anastasia 4 Frauen bar 201 |
| wrong `clef:G2^-1` instead of `clef:F4` | 1 | anastasia 1 | anastasia 4 Vlad 1 | anastasia 4 Vlad bar 1 |
| missing `clef:G2^-1` | 1 | anastasia 1 | anastasia 4 Vlad 1 | anastasia 4 Vlad bar 83 |
| wrong `clef:F4` instead of `clef:G2` | 1 | ghost 1 | ghost 1a Piano 1 | ghost 1a Piano bar 1 |
| made up `clef:F3` | 1 | ghost 1 | ghost 4 Klavier 1 | ghost 4 Klavier bar 36 |
| wrong `clef:G2` instead of `clef:F4` | 1 | ghost 1 | ghost 11a Violoncello 1 | ghost 11a Violoncello bar 1 |

### tremolos (94)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `trem:single:3` | 87 | anastasia 72, ghost 15 | anastasia 4 Schlagzeug 20, anastasia 4 Violine 1 11, anastasia 4 Violoncello 11 | anastasia 1 Violine 1 bar 2; anastasia 1 Violine 1 bar 3 |
| missing `trem:single:2` | 3 | anastasia 2, ghost 1 | anastasia 4 Xylophon 2, ghost 20 Violin 1 | anastasia 4 Xylophon bar 169; anastasia 4 Xylophon bar 172 |
| made up `trem:single:3` | 2 | anastasia 2 | anastasia 1 Keyboard 1 1, anastasia 4 Violine 2 1 | anastasia 1 Keyboard 1 bar 16; anastasia 4 Violine 2 bar 121 |
| missing `trem:start:3` | 1 | anastasia 1 | anastasia 1 Klarinette in B 2 1 | anastasia 1 Klarinette in B 2 bar 2 |
| at the wrong beat `trem:single:3` | 1 | anastasia 1 | anastasia 4 Violine 1 1 | anastasia 4 Violine 1 bar 8 |

### fermatas (70)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `fermata` | 38 | ghost 28, anastasia 10 | anastasia 1 Klavierauszug 4, ghost 1a Electric Guitar 4, ghost 11a Electric Piano 3 | anastasia 1 Trompete in B bar 31; anastasia 1 Klavierauszug bar 31 |
| made up `fermata` | 30 | anastasia 18, ghost 12 | anastasia 4 Violine 1 6, anastasia 4 Klavierauszug 3, ghost 4 Klavier 3 | anastasia 2 Klarinette in B 1 bar #74; anastasia 2 Keyboard 1 bar 29 |
| at the wrong beat `fermata` | 2 | ghost 2 | ghost 1a Electric Guitar 2 | ghost 1a Electric Guitar bar 8; ghost 1a Electric Guitar bar 28 |

### keys (68)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `key:0` | 26 | anastasia 19, ghost 7 | anastasia 4 Xylophon 7, anastasia 4 Violoncello 3, anastasia 1 Keyboard 1 2 | anastasia 1 Keyboard 1 bar 14; whole part |
| made up `key:0` | 11 | anastasia 7, ghost 4 | anastasia 4 Violoncello 3, anastasia 4 Klavierauszug 2, ghost 11a Piano 2 | anastasia 4 Violoncello bar 144; anastasia 4 Violoncello bar 155 |
| missing `key:5` | 7 | anastasia 7 | anastasia 4 Klavierauszug 2, anastasia 4 Violoncello 1, anastasia 4 Posaune 1 | anastasia 4 Violoncello bar 170; anastasia 4 Posaune bar 170 |
| missing `key:-5` | 3 | anastasia 2, ghost 1 | anastasia 4 Violoncello 1, anastasia 4 Xylophon 1, ghost 13 Cello 1 | anastasia 4 Violoncello bar 158; anastasia 4 Xylophon bar 158 |
| wrong `key:7` instead of `key:-5` | 3 | anastasia 2, ghost 1 | anastasia 4 Klarinette in B 2 1, anastasia 4 Trompete in B 1, ghost 1a Clarinet in Bb 1 | anastasia 4 Klarinette in B 2 bar 170; anastasia 4 Trompete in B bar 170 |
| missing `key:2` | 3 | ghost 3 | ghost 4 Elektrisches Piano 2, ghost 13 Bass 1 | ghost 4 Elektrisches Piano bar 44; ghost 13 Bass bar 182 |
| made up `key:5` | 2 | anastasia 2 | anastasia 4 Violoncello 1, anastasia 4 Posaune 1 | anastasia 4 Violoncello bar 169; anastasia 4 Posaune bar 169 |
| missing `key:-3` | 2 | anastasia 2 | anastasia 4 Xylophon 2 | anastasia 4 Xylophon bar 37; anastasia 4 Xylophon bar 44 |
| missing `key:-1` | 2 | anastasia 2 | anastasia 4 Xylophon 2 | anastasia 4 Xylophon bar 98; anastasia 4 Xylophon bar 115 |
| missing `key:-2` | 2 | anastasia 1, ghost 1 | anastasia 4 Xylophon 1, ghost 20 Electric Guitar 1 | anastasia 4 Xylophon bar 112; ghost 20 Electric Guitar bar 92 |
| made up `key:1` | 1 | anastasia 1 | anastasia 4 Violoncello 1 | anastasia 4 Violoncello bar #153 |
| made up `key:-5` | 1 | anastasia 1 | anastasia 4 Violoncello 1 | anastasia 4 Violoncello bar 157 |
| wrong `key:0` instead of `key:-3` | 1 | anastasia 1 | anastasia 4 Xylophon 1 | anastasia 4 Xylophon bar 1 |
| missing `key:4` | 1 | anastasia 1 | anastasia 4 Xylophon 1 | anastasia 4 Xylophon bar 82 |
| missing `key:1` | 1 | anastasia 1 | anastasia 4 Xylophon 1 | anastasia 4 Xylophon bar 149 |
| wrong `key:0` instead of `key:1` | 1 | anastasia 1 | anastasia 4A Xylophon 1 | anastasia 4A Xylophon bar 1 |
| made up `key:-1` | 1 | ghost 1 | ghost 20 Violin 1 | ghost 20 Violin bar 109 |

### times (49)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `time:4/4` | 15 | anastasia 12, ghost 3 | anastasia 4 Schlagzeug 4, anastasia 4 Keyboard 1 2, anastasia 4 Klavierauszug 2 | anastasia 4 Violoncello bar 197; anastasia 4 Posaune bar 197 |
| missing `time:2/2` | 12 | ghost 12 | ghost 4 Elektrisches Piano 2, ghost 4 Klavier 2, ghost 4 Violin 1 | ghost 4 Violin bar 49; ghost 4 Violoncello bar 49 |
| missing `time:2/4` | 6 | anastasia 3, ghost 3 | anastasia 4 Schlagzeug 3, ghost 1a Piano 2, ghost 1a Violoncello 1 | whole part; ghost 1a Violoncello bar 8 |
| wrong `time:4/4` instead of `time:2/4` | 5 | anastasia 5 | anastasia 4 Klavierauszug 2, anastasia 4 Violoncello 1, anastasia 4 Posaune 1 | anastasia 4 Violoncello bar 196; anastasia 4 Posaune bar 196 |
| made up `time:4/4` | 4 | ghost 3, anastasia 1 | ghost 5 Piano 2, anastasia 4 Violine 1 1, ghost 5 Violoncello 1 | anastasia 4 Violine 1 bar 199; ghost 5 Violoncello bar 14 |
| made up `time:2/4` | 4 | anastasia 4 | anastasia 4 Klavierauszug 2, anastasia 4 Violoncello 1, anastasia 4 Posaune 1 | anastasia 4 Violoncello bar 195; anastasia 4 Posaune bar 195 |
| missing `time:3/4` | 2 | anastasia 2 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1 | whole part |
| made up `time:12/8` | 1 | ghost 1 | ghost 5 Drum Kit 1 | ghost 5 Drum Kit bar 22 |

### systemtext (46)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 34 | anastasia 27, ghost 7 | anastasia 1 (system items) 8, anastasia 4 (system items) 8, anastasia 2 (system items) 7 | anastasia 1 (system); anastasia 2 (system) — e.g. "poco" ×3, "poco rall." ×2, "cresc." ×2, "moderato" ×2 |
| missing | 6 | anastasia 3, ghost 3 | ghost 13 (system items) 3, anastasia 4 (system items) 2, anastasia 2 (system items) 1 | anastasia 2 (system); anastasia 4 (system) — e.g. "sicherheitswiederholung" ×2, "driving" ×2, "rit." ×1, "poco accel." ×1 |
| wrong | 4 | anastasia 3, ghost 1 | anastasia 2 (system items) 2, anastasia 1 (system items) 1, ghost 1a (system items) 1 | anastasia 1 (system); anastasia 2 (system) — e.g. "poco rit. / rit." ×1, "poco ritard. / rit." ×1, "poco mosso / accel." ×1, "very freely ( = c. 72) / = c. 72" ×1 |
| at the wrong beat | 2 | anastasia 1, ghost 1 | anastasia 1 (system items) 1, ghost 13 (system items) 1 | anastasia 1 (system); ghost 13 (system) |

### instruments (43)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing `ic` | 23 | ghost 23 | ghost 5 Electric Piano 4, ghost 20 Electric Piano 4, ghost 4 Elektrisches Piano 3 | ghost 1a Electric Guitar bar 9; ghost 1a Electric Piano bar 1 |
| made up `ic` | 20 | anastasia 20 | anastasia 4 Frauen 13, anastasia 4 Männer 6, anastasia 4 Dmitry 1 | anastasia 4 Männer bar 41; anastasia 4 Männer bar 47 |

### rehearsal (33)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up | 22 | ghost 22 | ghost 4 (system items) 9, ghost 13 (system items) 9, ghost 5 (system items) 2 | ghost 4 (system); ghost 5 (system) — e.g. "reh:a" ×5, "reh:d" ×5, "reh:b" ×3, "reh:c" ×2 |
| missing | 8 | ghost 8 | ghost 1a (system items) 2, ghost 5 (system items) 2, ghost 13 (system items) 2 | ghost 1a (system); ghost 5 (system) — e.g. "reh:a" ×2, "reh:b" ×1, "reh:c" ×1, "reh:d" ×1 |
| at the wrong beat | 3 | ghost 3 | ghost 20 (system items) 2, ghost 5 (system items) 1 | ghost 5 (system); ghost 20 (system) |

### tuplets (20)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| made up `tuplet:3:2` | 8 | anastasia 7, ghost 1 | anastasia 1 Violine 1 1, anastasia 1 Violine 2 1, anastasia 1 Flöte 2 1 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| wrong `tuplet:3:2` instead of `tuplet:6:4` | 6 | anastasia 6 | anastasia 1 Violine 1 1, anastasia 1 Violine 2 1, anastasia 1 Flöte 2 1 | anastasia 1 Violine 1 bar 1; anastasia 1 Violine 2 bar 1 |
| missing `tuplet:3:2` | 4 | anastasia 4 | anastasia 4 Klarinette in B 2 2, anastasia 4 Kastagnetten 2 | anastasia 4 Klarinette in B 2 bar 107; anastasia 4 Klarinette in B 2 bar 165 |
| missing `tuplet:6:4` | 1 | anastasia 1 | anastasia 1 Piccolo 1 | anastasia 1 Piccolo bar 1 |
| missing `tuplet:2:3` | 1 | ghost 1 | ghost 5 Violoncello 1 | ghost 5 Violoncello bar 33 |

### tempo (7)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| missing | 3 | ghost 2, anastasia 1 | anastasia 4A (system items) 1, ghost 5 (system items) 1, ghost 20 (system items) 1 | anastasia 4A (system); ghost 5 (system) — e.g. "quarter=120" ×1, "eighth=165" ×1, "quarter=130" ×1 |
| made up | 2 | anastasia 1, ghost 1 | anastasia 4 (system items) 1, ghost 13 (system items) 1 | anastasia 4 (system); ghost 13 (system) — e.g. "quarter=124" ×1, "quarter=122" ×1 |
| at the wrong beat | 2 | ghost 2 | ghost 13 (system items) 2 | ghost 13 (system) |

### part (6)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| no output at all (every truth item below counts as missing) | 3 | anastasia 3 | anastasia 2 Triangel 1, anastasia 2 Schlagzeug 1, anastasia 4 Schlagzeug 1 | whole part |
| whole part transposed (-12 semitones; 1 bulk action) | 2 | ghost 2 | ghost 4 Electric Bass 1, ghost 4 Electric Guitar 1 | whole part |
| whole part transposed (+12 semitones; 1 bulk action) | 1 | anastasia 1 | anastasia 2 Kontrabass 1 | whole part |

### note on the wrong staff (piano) (2)

| error | count | by show | most in | first at |
|---|---|---|---|---|
| note on the wrong staff (piano) | 2 | anastasia 2 | anastasia 4 Keyboard 1 1, anastasia 4 Klavierauszug 1 | anastasia 4 Keyboard 1 bar 22; anastasia 4 Klavierauszug bar 147 |

### Per part (top 6 kinds)

| part | total | top kinds |
|---|---|---|
| ghost 4 Electric Guitar | 971 | notes: note missing 731, slurs: missing `slur` 70, bars: note inside a missing bar 65, chords: made up 38, bars: bar length wrong (whole-bar rest with the wrong duration) 12, bars: extra bar (empty) 8 |
| ghost 4 Drum Kit | 864 | drums: hit missing 457, rhythm: note value x4 too long 115, drums: wrong kit instrument (staff position) 77, articulations: missing `accent` 59, articulations: at the wrong beat `accent` 35, rhythm: note at the wrong beat (onset shifted) 33 |
| anastasia 4 Schlagzeug | 787 | drums: hit missing 592, articulations: missing `accent` 63, barlines: missing `bar:light-light` 21, tremolos: missing `trem:single:3` 20, ties: missing `tie` 16, hairpins: missing `crescendo` 15 |
| anastasia 4 Keyboard 1 | 686 | notes: note missing 82, articulations: missing `staccato` 72, articulations: missing `accent` 63, pitch: accidental made up 33, notes: note made up 29, words: made up 28 |
| ghost 20 Piano | 553 | notes: note missing 130, ties: missing `tie` 67, pitch: wrong by more than a third 58, pitch: one staff step off 29, slurs: made up `slur` 25, articulations: made up `staccato` 23 |
| anastasia 4 Klavierauszug | 461 | articulations: missing `accent` 67, articulations: missing `tenuto` 65, articulations: missing `staccato` 31, rhythm: note at the wrong beat (onset shifted) 26, barlines: missing `bar:light-light` 21, slurs: made up `slur` 19 |
| ghost 5 Drum Kit | 442 | drums: hit missing 260, articulations: missing `accent` 61, articulations: missing `staccato` 55, bars: marking inside a missing bar 13, tremolos: missing `trem:single:3` 7, bars: note inside a missing bar 6 |
| anastasia 4 Männer | 401 | bars: note inside a missing bar 131, lyrics: made up 80, bars: extra bar (with notes) 26, notes: note missing 23, bars: bar missing (with notes) 18, barlines: missing `bar:light-light` 18 |
| ghost 5 Piano | 321 | notes: note missing 91, articulations: missing `accent` 46, articulations: missing `staccato` 38, pitch: wrong by more than a third 34, rhythm: note value x2 too long 24, slurs: made up `slur` 15 |
| anastasia 4 Dmitry | 319 | lyrics: missing 123, notes: note missing 111, barlines: missing `bar:light-light` 21, lyrics: wrong 12, articulations: missing `accent` 7, ties: missing `tie` 5 |
| anastasia 4 Frauen | 308 | lyrics: missing 39, lyrics: wrong 38, lyrics: made up 35, notes: extra chord note 34, barlines: missing `bar:light-light` 21, notes: note missing 16 |
| anastasia 4 Violine 1 | 242 | hairpins: missing `crescendo` 22, barlines: missing `bar:light-light` 21, words: missing 19, pitch: accidental made up 13, articulations: missing `accent` 11, tremolos: missing `trem:single:3` 11 |
| ghost 4 Klavier | 234 | chords: missing 59, chords: made up 26, notes: note missing 21, pitch: wrong by more than a third 15, bars: extra bar (with notes) 14, bars: bar missing (with notes) 9 |
| ghost 20 Electric Guitar | 233 | notes: note missing 68, chords: at the wrong beat 21, ties: missing `tie` 20, bars: marking inside a missing bar 14, bars: note inside a missing bar 12, bars: bar length wrong (notes / rests do not add up like the truth bar) 11 |
| ghost 20 Drum Kit | 230 | drums: hit missing 67, bars: note inside a missing bar 26, articulations: made up `staccato` 23, rhythm: note at the wrong beat (onset shifted) 20, bars: bar length wrong (notes / rests do not add up like the truth bar) 17, ties: missing `tie` 11 |
| anastasia 4 Horn in F | 216 | hairpins: missing `crescendo` 27, articulations: missing `tenuto` 25, barlines: missing `bar:light-light` 21, notes: note missing 11, dynamics: missing `mp` 11, bars: bar missing (empty or rests only) 9 |
| ghost 4 Sam | 209 | lyrics: missing 98, notes: note missing 67, ties: missing `tie` 7, pitch: bar in an octave-off section (+1 octave) 6, barlines: missing `bar:light-heavy` 4, lyrics: wrong 3 |
| anastasia 4 Vlad | 201 | notes: note missing 43, lyrics: missing 25, lyrics: made up 23, barlines: missing `bar:light-light` 20, lyrics: wrong 13, bars: bar missing (empty or rests only) 12 |
| anastasia 4 Tamburin | 198 | bars: extra bar (with notes) 48, bars: bar missing (empty or rests only) 42, barlines: missing `bar:light-light` 18, drums: hit missing 17, bars: note inside a missing bar 16, bars: marking inside a missing bar 13 |
| anastasia 4 Oboe | 186 | barlines: missing `bar:light-light` 21, hairpins: missing `crescendo` 17, pitch: accidental made up 13, slurs: made up `slur` 13, dynamics: missing `mp` 9, dynamics: missing `p` 7 |
| ghost 5 Electric Piano | 183 | articulations: missing `staccato` 52, articulations: missing `accent` 52, notes: note missing 20, bars: marking inside a missing bar 8, instruments: missing `ic` 4, words: missing 4 |
| ghost 5 Electric Bass | 171 | articulations: missing `staccato` 56, articulations: missing `accent` 56, notes: note missing 18, bars: marking inside a missing bar 13, bars: bar length wrong (notes / rests do not add up like the truth bar) 8, bars: note inside a missing bar 4 |
| anastasia 4 Keyboard 2 | 170 | notes: note missing 26, barlines: missing `bar:light-light` 21, pitch: octave off (+1) 17, pitch: wrong by more than a third 12, rhythm: note value 1/2 too short 10, pitch: accidental made up 10 |
| ghost 20 Electric Piano | 166 | articulations: made up `staccato` 38, notes: note missing 21, ties: missing `tie` 16, pitch: bar in an octave-off section (-1 octave) 16, slurs: made up `slur` 13, slurs: missing `slur` 13 |
| ghost 4 Elektrisches Piano | 153 | notes: note missing 49, pitch: octave off (-1) 11, pitch: wrong by more than a third 9, notes: chord note missing 8, rhythm: note at the wrong beat (onset shifted) 6, notes: note made up 6 |
| ghost 5 Electric Guitar | 144 | notes: note missing 27, articulations: missing `staccato` 21, articulations: missing `accent` 21, pitch: wrong by more than a third 13, bars: bar length wrong (notes / rests do not add up like the truth bar) 10, bars: marking inside a missing bar 5 |
| anastasia 4 Violoncello | 140 | barlines: missing `bar:light-light` 21, words: missing 16, tremolos: missing `trem:single:3` 11, pitch: wrong by more than a third 10, notes: note missing 10, pitch: accidental missing 8 |
| anastasia 4 Klarinette in B 2 | 127 | barlines: missing `bar:light-light` 21, pitch: accidental missing 18, notes: note made up 16, pitch: accidental made up 14, notes: note missing 11, bars: bar length wrong (notes / rests do not add up like the truth bar) 10 |
| ghost 5 Violoncello | 122 | notes: note missing 28, articulations: missing `accent` 26, articulations: missing `staccato` 24, bars: bar length wrong (notes / rests do not add up like the truth bar) 15, words: made up 4, structure: missing `repeat:forward` 3 |
| ghost 4 Molly | 119 | lyrics: missing 52, lyrics: wrong 24, articulations: made up `staccato` 5, barlines: missing `bar:light-heavy` 4, slurs: made up `slur` 4, ties: missing `tie` 3 |
| anastasia 4 Xylophon | 116 | barlines: missing `bar:light-light` 21, notes: note missing 9, drums: wrong kit instrument (staff position) 7, keys: missing `key:0` 7, bars: bar length wrong (notes / rests do not add up like the truth bar) 5, hairpins: missing `crescendo` 5 |
| anastasia 1 Klavierauszug | 110 | articulations: missing `accent` 16, words: made up 13, pitch: octave off (-1) 11, pitch: octave off (+1) 8, rhythm: same length, other notation 6, articulations: made up `staccato` 6 |
| anastasia 4 Violine 2 | 93 | barlines: missing `bar:light-light` 21, pitch: accidental made up 14, words: missing 14, pitch: accidental missing 8, pitch: one staff step off 7, tremolos: missing `trem:single:3` 4 |
| ghost 13 Cello | 84 | barlines: missing `bar:light-light` 17, articulations: missing `strong-accent` 14, bars: bar missing (empty or rests only) 8, bars: extra bar (empty) 7, words: missing 6, ties: missing `tie` 5 |
| ghost 5 Frauen | 81 | bars: bar missing (empty or rests only) 20, bars: extra bar (with notes) 20, lyrics: wrong 16, bars: marking inside a missing bar 5, lyrics: missing 5, structure: missing `repeat:forward` 2 |
| anastasia 4 Posaune | 80 | barlines: missing `bar:light-light` 21, notes: note missing 14, notes: note made up 8, bars: bar length wrong (notes / rests do not add up like the truth bar) 4, pitch: accidental missing 4, structure: missing `repeat:forward` 3 |
| ghost 11a Piano | 75 | chords: missing 22, notes: note missing 17, bars: marking inside a missing bar 11, bars: bar missing (empty or rests only) 5, bars: extra bar (with notes) 5, pitch: one staff step off 4 |
| anastasia 1 Keyboard 1 | 73 | slurs: made up `slur` 12, articulations: missing `accent` 10, notes: note missing 10, words: made up 6, articulations: made up `tenuto` 6, barlines: missing `bar:light-light` 3 |
| anastasia 4 Trompete in B | 68 | barlines: missing `bar:light-light` 21, notes: note missing 12, bars: extra bar (with notes) 5, bars: bar length wrong (notes / rests do not add up like the truth bar) 4, bars: bar missing (empty or rests only) 4, structure: missing `repeat:forward` 3 |
| anastasia 2 Keyboard 1 | 62 | notes: note made up 12, words: made up 10, slurs: made up `slur` 8, bars: bar length wrong (whole-bar rest with the wrong duration) 5, dynamics: made up `p` 3, ties: tie read as a slur 2 |
| anastasia 4 Fagott | 61 | barlines: missing `bar:light-light` 21, ties: made up `tie` 4, pitch: accidental missing 4, pitch: wrong by more than a third 4, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3 |
| anastasia 4 Kastagnetten | 59 | barlines: missing `bar:light-light` 21, drums: hit missing 8, bars: bar missing (empty or rests only) 7, bars: extra bar (with notes) 7, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3 |
| ghost 5 Violin | 58 | ties: missing `tie` 15, notes: note missing 15, bars: bar length wrong (whole-bar rest with the wrong duration) 4, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, words: made up 3 |
| anastasia 4 Piccolo | 53 | barlines: missing `bar:light-light` 21, hairpins: missing `crescendo` 4, slurs: missing `slur` 4, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, articulations: missing `accent` 3 |
| ghost 20 Violoncello | 52 | slurs: missing `slur` 8, slurs: made up `slur` 7, dynamics: missing `f` 6, ties: missing `tie` 4, notes: note missing 4, barlines: missing `bar:light-light` 3 |
| anastasia 4 Triangel | 50 | barlines: missing `bar:light-light` 20, bars: extra bar (with notes) 6, bars: bar missing (empty or rests only) 5, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, drums: hit made up 2 |
| ghost 20 Trumpet in Bb | 48 | articulations: missing `accent` 4, pitch: two staff steps off (a third) 3, pitch: one staff step off 3, notes: note missing 3, notes: note made up 3, slurs: at the wrong beat `slur` 3 |
| anastasia 4 Holzblöcke | 47 | barlines: missing `bar:light-light` 20, bars: bar missing (empty or rests only) 6, bars: extra bar (with notes) 6, drums: hit missing 5, bars: marking inside a missing bar 4, structure: missing `repeat:forward` 3 |
| ghost 5 Clarinet in Bb | 46 | structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, hairpins: missing `crescendo` 3, tremolos: missing `trem:single:3` 3, bars: extra bar (empty) 3, pitch: accidental missing 3 |
| anastasia 4 Kontrabass | 45 | barlines: missing `bar:light-light` 21, words: missing 6, pitch: accidental made up 4, pitch: accidental missing 4, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3 |
| ghost 1a Electric Guitar | 45 | chords: made up 5, chords: missing 5, fermatas: missing `fermata` 4, ties: missing `tie` 4, chords: at the wrong beat 3, articulations: made up `staccato` 3 |
| ghost 20 Clarinet in Bb | 45 | notes: note missing 6, articulations: missing `staccato` 5, pitch: two staff steps off (a third) 3, notes: note made up 3, slurs: at the wrong beat `slur` 3, barlines: missing `bar:light-light` 3 |
| ghost 20 Violin | 44 | slurs: made up `slur` 9, dynamics: missing `f` 6, articulations: missing `accent` 4, slurs: missing `slur` 3, ties: missing `tie` 3, barlines: missing `bar:light-light` 3 |
| ghost 1a Piano | 43 | chords: missing 11, notes: note missing 5, ties: tie read as a slur 4, ties: missing `tie` 3, dynamics: made up `p` 3, instruments: missing `ic` 2 |
| ghost 13 Bass | 42 | barlines: missing `bar:light-light` 18, dynamics: missing `mp` 3, words: made up 3, words: missing 2, structure: missing `repeat:forward` 2, structure: missing `repeat:backward` 2 |
| ghost 4 Clarinet in Bb | 40 | hairpins: missing `diminuendo` 6, dynamics: missing `mp` 5, barlines: missing `bar:light-heavy` 4, words: made up 3, instruments: missing `ic` 2, words: wrong 2 |
| anastasia 4A Violine 1 | 38 | articulations: missing `tenuto` 32, dynamics: wrong `p` instead of `mf` 1, hairpins: missing `diminuendo` 1, dynamics: missing `p` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 1 Violine 1 | 37 | tremolos: missing `trem:single:3` 8, rhythm: same length, other notation 6, articulations: missing `accent` 4, barlines: missing `bar:light-light` 4, words: made up 4, articulations: missing `tenuto` 3 |
| ghost 5 Trumpet in Bb | 34 | notes: note missing 4, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, hairpins: missing `crescendo` 3, ties: missing `tie` 2, tremolos: missing `trem:single:3` 2 |
| anastasia 4 Pauken | 33 | barlines: missing `bar:light-light` 21, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, words: made up 2, dynamics: missing `mf` 1, dynamics: made up `mf` 1 |
| anastasia 4 Glockenspiel | 33 | barlines: missing `bar:light-light` 21, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, words: made up 3, dynamics: missing `sfz` 1, slurs: made up `slur` 1 |
| ghost 11a Clarinet in Bb | 32 | rhythm: note value 1/2 too short 5, notes: note missing 5, notes: note made up 5, bars: bar length wrong (notes / rests do not add up like the truth bar) 3, slurs: missing `slur` 3, dynamics: made up `p` 2 |
| anastasia 2 Violine 1 | 31 | slurs: made up `slur` 7, notes: note made up 4, hairpins: missing `diminuendo` 4, dynamics: missing `p` 3, words: made up 3, bars: bar length wrong (whole-bar rest with the wrong duration) 2 |
| anastasia 4 Crotales | 31 | barlines: missing `bar:light-light` 21, structure: missing `repeat:backward` 3, structure: missing `repeat:forward` 2, dynamics: missing `p` 1, words: made up 1, bars: bar missing (empty or rests only) 1 |
| ghost 4 Violin | 31 | barlines: missing `bar:light-heavy` 4, ties: tie read as a slur 4, slurs: missing `slur` 3, dynamics: missing `mp` 2, hairpins: missing `diminuendo` 2, slurs: made up `slur` 2 |
| anastasia 4 Flöte 2 | 29 | barlines: missing `bar:light-light` 21, structure: missing `repeat:forward` 3, structure: missing `repeat:backward` 3, pitch: two staff steps off (a third) 2 |
| ghost 5 Männer | 29 | lyrics: missing 5, structure: missing `repeat:forward` 3, notes: note made up 2, ties: made up `tie` 2, bars: bar missing (empty or rests only) 2, bars: extra bar (with notes) 2 |
| anastasia 1 Flöte 1 | 25 | barlines: missing `bar:light-light` 4, slurs: made up `slur` 3, notes: note missing 3, words: made up 2, dynamics: missing `p` 2, rhythm: other wrong length (longer) 2 |
| anastasia 1 Piccolo | 24 | notes: note missing 4, notes: note made up 4, barlines: missing `bar:light-light` 4, rhythm: triplet / tuplet missing 2, slurs: made up `slur` 2, pitch: one staff step off 1 |
| anastasia 1 Klarinette in B 2 | 23 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 3, bars: bar missing (empty or rests only) 2, bars: marking inside a missing bar 2, bars: extra bar (with notes) 2, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1 |
| anastasia 1 Keyboard 2 | 23 | notes: note missing 11, barlines: missing `bar:light-light` 4, notes: chord note missing 4, ties: missing `tie` 2, rhythm: note at the wrong beat (onset shifted) 1, bars: bar length wrong (notes / rests do not add up like the truth bar) 1 |
| anastasia 2 The Dowager Empress | 23 | words: missing 6, words: made up 5, lyrics: missing 3, articulations: made up `staccato` 2, lyrics: wrong 1, articulations: missing `breath-mark` 1 |
| anastasia 1 Splash-Becken | 22 | tremolos: missing `trem:single:3` 5, drums: hit missing 4, barlines: missing `bar:light-light` 4, hairpins: missing `crescendo` 3, ties: missing `tie` 2, drums: wrong kit instrument (staff position) 1 |
| ghost 4 Violoncello | 22 | barlines: missing `bar:light-heavy` 4, hairpins: missing `diminuendo` 2, bars: bar missing (empty or rests only) 1, dynamics: wrong `p` instead of `mp` 1, pitch: two staff steps off (a third) 1, notes: note made up 1 |
| anastasia 1 Frauen | 21 | words: made up 5, barlines: missing `bar:light-light` 4, lyrics: missing 4, ties: missing `tie` 2, articulations: made up `staccato` 1, words: missing 1 |
| anastasia 1 Horn in F | 19 | barlines: missing `bar:light-light` 4, dynamics: missing `mf` 2, hairpins: missing `crescendo` 2, rhythm: note value x2 too long 2, bars: bar length wrong (notes / rests do not add up like the truth bar) 2, dynamics: made up `f` 1 |
| anastasia 1 Pauken | 19 | notes: note made up 6, barlines: missing `bar:light-light` 4, slurs: made up `slur` 3, words: made up 2, dynamics: missing `mf` 1, hairpins: missing `crescendo` 1 |
| ghost 13 (system items) | 19 | rehearsal: made up 9, systemtext: missing 3, rehearsal: missing 2, tempo: at the wrong beat 2, systemtext: at the wrong beat 1, systemtext: made up 1 |
| ghost 20 Electric Bass | 19 | ties: missing `tie` 5, words: made up 3, barlines: missing `bar:light-light` 3, slurs: made up `slur` 2, dynamics: made up `f` 1, articulations: made up `caesura` 1 |
| anastasia 1 Flöte 2 | 18 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, rhythm: note value x2 too long 1, pitch: two staff steps off (a third) 1 |
| anastasia 2 Glockenspiel | 17 | words: made up 3, slurs: made up `slur` 3, dynamics: at the wrong beat `mp` 1, dynamics: missing `mf` 1, dynamics: missing `mp` 1, articulations: missing `caesura` 1 |
| anastasia 4A Xylophon | 17 | bars: bar length wrong (whole-bar rest with the wrong duration) 3, notes: note missing 2, articulations: missing `accent` 1, clefs: wrong `clef:percussion` instead of `clef:G2` 1, dynamics: missing `mf` 1, keys: wrong `key:0` instead of `key:1` 1 |
| anastasia 2 Keyboard 2 | 16 | bars: bar length wrong (notes / rests do not add up like the truth bar) 8, pitch: two staff steps off (a third) 2, rhythm: note at the wrong beat (onset shifted) 1, notes: chord note missing 1, ties: missing `tie` 1, barlines: missing `bar:light-light` 1 |
| ghost 1a Electric Piano | 16 | articulations: made up `staccato` 7, instruments: missing `ic` 2, words: missing 2, dynamics: missing `p` 1, dynamics: made up `p` 1, notes: note missing 1 |
| ghost 4 Electric Bass | 16 | barlines: missing `bar:light-heavy` 4, dynamics: missing `mp` 2, part: whole part transposed (-12 semitones; 1 bulk action) 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, slurs: missing `slur` 1 |
| ghost 11a Electric Guitar | 16 | notes: note made up 5, chords: made up 2, chords: missing 2, clefs: wrong `clef:G2` instead of `clef:G2^-1` 1, fermatas: made up `fermata` 1, bars: bar missing (empty or rests only) 1 |
| anastasia 1 Männer | 14 | lyrics: missing 5, barlines: missing `bar:light-light` 4, ties: missing `tie` 2, notes: note missing 2, notes: chord note missing 1 |
| anastasia 1 Violine 2 | 13 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, words: made up 1 |
| anastasia 1 Trompete in B | 13 | rhythm: same length, other notation 6, barlines: missing `bar:light-light` 4, tuplets: wrong `tuplet:3:2` instead of `tuplet:6:4` 1, tuplets: made up `tuplet:3:2` 1, fermatas: missing `fermata` 1 |
| anastasia 2 Flöte 1 | 13 | words: made up 4, hairpins: missing `diminuendo` 1, slurs: made up `slur` 1, articulations: missing `caesura` 1, dynamics: missing `p` 1, barlines: missing `bar:light-light` 1 |
| anastasia 2 Triangel | 13 | drums: hit missing 4, part: no output at all (every truth item below counts as missing) 1, clefs: missing `clef:percussion` 1, dynamics: missing `mp` 1, keys: missing `key:0` 1, times: missing `time:3/4` 1 |
| anastasia 2 Splash-Becken | 13 | drums: wrong kit instrument (staff position) 3, ties: tie read as a slur 2, tremolos: missing `trem:single:3` 2, barlines: missing `bar:light-light` 1, words: made up 1, dynamics: missing `pp` 1 |
| anastasia 2 Young Anastasia | 12 | words: missing 4, words: made up 1, articulations: made up `staccato` 1, fermatas: missing `fermata` 1, articulations: made up `strong-accent` 1, lyrics: missing 1 |
| anastasia 4A Keyboard 1 | 12 | words: made up 3, notes: note missing 3, dynamics: missing `mf` 1, structure: missing `repeat:forward` 1, articulations: missing `staccato` 1, bars: bar length wrong (notes / rests do not add up like the truth bar) 1 |
| ghost 4 (system items) | 12 | rehearsal: made up 9, systemtext: made up 3 |
| anastasia 2 Violoncello | 11 | notes: note missing 3, words: made up 1, bars: bar missing (empty or rests only) 1, bars: extra bar (with notes) 1, words: missing 1, barlines: missing `bar:light-light` 1 |
| anastasia 4 (system items) | 11 | systemtext: made up 8, systemtext: missing 2, tempo: made up 1 |
| anastasia 1 (system items) | 10 | systemtext: made up 8, systemtext: at the wrong beat 1, systemtext: wrong 1 |
| anastasia 2 (system items) | 10 | systemtext: made up 7, systemtext: wrong 2, systemtext: missing 1 |
| anastasia 4A Klavierauszug | 10 | words: made up 2, fermatas: missing `fermata` 2, dynamics: made up `p` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, pitch: accidental missing 1 |
| anastasia 1 Kontrabass | 9 | barlines: missing `bar:light-light` 4, notes: note made up 4, tremolos: missing `trem:single:3` 1 |
| anastasia 2 Klarinette in B 1 | 9 | barlines: missing `bar:light-light` 1, dynamics: missing `p` 1, hairpins: missing `crescendo` 1, words: made up 1, slurs: made up `slur` 1, hairpins: missing `diminuendo` 1 |
| anastasia 2 Crotales | 9 | notes: note made up 3, dynamics: missing `p` 1, words: made up 1, slurs: made up `slur` 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1 |
| anastasia 2 Glockenbaum | 9 | barlines: missing `bar:light-light` 1, words: made up 1, fermatas: made up `fermata` 1, drums: hit missing 1, dynamics: missing `p` 1, structure: missing `repeat:forward` 1 |
| ghost 1a Violoncello | 9 | bars: bar missing (empty or rests only) 2, bars: extra bar (empty) 2, dynamics: missing `pp` 1, hairpins: missing `crescendo` 1, dynamics: missing `p` 1, hairpins: missing `diminuendo` 1 |
| anastasia 1 Fagott | 8 | barlines: missing `bar:light-light` 4, rhythm: other wrong length (longer) 2, bars: bar length wrong (notes / rests do not add up like the truth bar) 2 |
| anastasia 1 Glockenbaum | 8 | barlines: missing `bar:light-light` 4, drums: hit missing 1, dynamics: missing `fp` 1, hairpins: missing `diminuendo` 1, words: made up 1 |
| anastasia 2 Schlagzeug | 8 | part: no output at all (every truth item below counts as missing) 1, clefs: missing `clef:percussion` 1, keys: missing `key:0` 1, times: missing `time:3/4` 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1 |
| ghost 11a Violoncello | 8 | fermatas: missing `fermata` 2, clefs: wrong `clef:G2` instead of `clef:F4` 1, clefs: made up `clef:F4` 1, dynamics: missing `p` 1, barlines: missing `bar:light-light` 1, dynamics: missing `mp` 1 |
| anastasia 1 Klarinette in B 1 | 7 | barlines: missing `bar:light-light` 4, words: made up 3 |
| anastasia 1 Glockenspiel | 7 | barlines: missing `bar:light-light` 4, words: made up 1, dynamics: missing `p` 1, slurs: made up `slur` 1 |
| anastasia 2 Violine 2 | 7 | words: made up 2, notes: note made up 1, bars: bar length wrong (notes / rests do not add up like the truth bar) 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| ghost 5 (system items) | 7 | rehearsal: missing 2, rehearsal: made up 2, rehearsal: at the wrong beat 1, systemtext: made up 1, tempo: missing 1 |
| ghost 11a Electric Piano | 7 | fermatas: missing `fermata` 3, instruments: missing `ic` 1, words: wrong 1, articulations: made up `staccato` 1, barlines: missing `bar:light-light` 1 |
| anastasia 2 Klarinette in B 2 | 6 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, barlines: missing `bar:light-light` 1, pitch: accidental missing 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 2 Posaune | 6 | notes: note made up 2, barlines: missing `bar:light-light` 1, words: missing 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Horn in F | 6 | dynamics: missing `mf` 1, structure: missing `repeat:forward` 1, hairpins: missing `diminuendo` 1, structure: missing `repeat:backward` 1, bars: bar length wrong (whole-bar rest with the wrong duration) 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| ghost 1a Clarinet in Bb | 6 | slurs: made up `slur` 3, keys: wrong `key:7` instead of `key:-5` 1, fermatas: missing `fermata` 1, words: made up 1 |
| ghost 11a Violin | 6 | fermatas: missing `fermata` 2, dynamics: made up `p` 1, barlines: missing `bar:light-light` 1, keys: missing `key:0` 1, keys: made up `key:0` 1 |
| ghost 20 (system items) | 6 | rehearsal: at the wrong beat 2, rehearsal: made up 2, rehearsal: missing 1, tempo: missing 1 |
| anastasia 1 Violoncello | 5 | barlines: missing `bar:light-light` 4, tremolos: missing `trem:single:3` 1 |
| anastasia 1 Posaune | 5 | barlines: missing `bar:light-light` 4, words: missing 1 |
| anastasia 2 Kontrabass | 5 | part: whole part transposed (+12 semitones; 1 bulk action) 1, notes: note made up 1, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 2 Fagott | 5 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 2 Trompete in B | 5 | bars: bar length wrong (whole-bar rest with the wrong duration) 2, barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Kontrabass | 5 | rhythm: note at the wrong beat (onset shifted) 2, structure: missing `repeat:forward` 1, words: at the wrong beat 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Klarinette in B 1 | 5 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, dynamics: missing `mf` 1, fermatas: made up `fermata` 1, hairpins: missing `diminuendo` 1 |
| anastasia 4A Keyboard 2 | 5 | pitch: wrong by more than a third 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, bars: bar length wrong (whole-bar rest with the wrong duration) 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 4A (system items) | 5 | systemtext: made up 4, tempo: missing 1 |
| ghost 11a Electric Bass | 5 | fermatas: missing `fermata` 2, barlines: missing `bar:light-light` 1, dynamics: missing `mp` 1, hairpins: missing `diminuendo` 1 |
| anastasia 4A Violoncello | 4 | ties: made up `tie` 2, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Trompete in B | 4 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, bars: bar length wrong (whole-bar rest with the wrong duration) 1, barlines: at the wrong beat `bar:light-heavy` 1 |
| anastasia 2 Flöte 2 | 3 | barlines: missing `bar:light-light` 1, structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Violine 2 | 3 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, rhythm: note value x2 too long 1 |
| anastasia 4A Fagott | 3 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1, words: made up 1 |
| ghost 1a (system items) | 3 | rehearsal: missing 2, systemtext: wrong 1 |
| ghost 11a (system items) | 3 | systemtext: made up 2, rehearsal: missing 1 |
| anastasia 4A Klarinette in B 2 | 2 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |
| anastasia 4A Posaune | 2 | structure: missing `repeat:forward` 1, structure: missing `repeat:backward` 1 |

(The sections below are from round 2, 2026-10-16, on the outputs `p1`; their findings still hold.)

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
