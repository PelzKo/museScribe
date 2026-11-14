# Error overview: output vs truth

What is still wrong in the pipeline output, how often, and what it costs. State **2026-11-14, run `r69-a`**
(`results/<show>/runs/r69-a`, reassembled from the `h71` work dirs, homr 0.7.1). The plan that follows from it is in
`docs/IMPROVEMENTS.md`. The version before this rewrite (state `r3-f`, 2026-10-18, with the full per-part lists) is
`docs/archive/ERRORS-2026-11-14.md`.

Reproduce (about 1 minute; writes `results/errors/r69-a/errors.md` and `errors.json` with every location):

```bash
source ~/.local/share/omrbench/env.sh
python scripts/error_report.py anastasia,ghost --run r69-a
```

Two numbers are used below. Do not mix them.
- **Actions** = edit penalty (`omrbench bench`, `results/<show>/bench/r69-a/scores.json`): MuseScore actions to turn
  the output into the truth. This is the score.
- **Differences** = error report: every note and mark compared one to one inside the aligned bars. One note can
  count twice (wrong pitch + wrong length). It says what is wrong, not what it costs.

## 1. Totals

**9 111 actions** (Anastasia 6 762, Ghost 2 349); 9 441 differences; 12 songs, 174 truth parts, 40 301 truth notes.
Typing everything in by hand would be 64 134 actions, so 14 % of the hand work is left.

| song | actions | left | note F1 | bars insert / delete | worst parts (actions) |
|---|---|---|---|---|---|
| Anastasia 1 | 260 | 13.7 % | 0.952 | 5 / 5 | Keyboard 1 49, Violine 1 28 |
| Anastasia 2 | 244 | 15.9 % | 0.935 | 4 / 4 | Keyboard 1 57; Triangel and Schlagzeug have no output |
| Anastasia 3 | 2 165 | 17.2 % | 0.954 | 63 / 63 | Keyboard 2 328, Schlagzeug 230, Kontrabass 193, Trompete 184, Keyboard 1 172, Posaune 159, Männer 154 |
| Anastasia 4 | 3 291 | 16.2 % | 0.899 | 74 / 75 | Schlagzeug 392, Keyboard 1 376, Trompete 334, Posaune 274, Keyboard 2 242, Violoncello 167, Männer 165 |
| Anastasia 4A | 62 | 8.4 % | 0.985 | 0 / 0 | |
| Anastasia 5 | 740 | 11.4 % | 0.838 | 1 / 2 | Keyboard 1 198; Mark Tree and Vlad have no output |
| Ghost 1a | 83 | 11.8 % | 0.993 | 0 / 0 | |
| Ghost 4 | 652 | 11.4 % | 0.663 | 24 / 24 | Klavier 178, Elektrisches Piano 123 |
| Ghost 5 | 679 | 30.0 % | 0.782 | 10 / 10 | Piano 240, Electric Piano 130 |
| Ghost 11a | 112 | 20.3 % | 0.786 | 5 / 5 | Piano |
| Ghost 13 | 97 | 6.1 % | 0.933 | 7 / 7 | |
| Ghost 20 | 726 | 7.5 % | 0.950 | 9 / 9 | Piano 286, Electric Guitar 128, Electric Piano 115 |

Bar counts: right in every part with an output but Anastasia 4 Keyboard 1 (212 / 211) and Anastasia 5 Keyboard 1
(157 / 156). No output at all: Anastasia 2 Triangel and Schlagzeug, 3 Empress, 5 Mark Tree, 5 Vlad.

## 2. Where the actions are

By category (part rows; rehearsal / tempo / system text are scored once per song):

| category | Anastasia | Ghost | total | share |
|---|---|---|---|---|
| notes (incl. drum hits) | 1 746 | 756 | 2 502 | 27 % |
| articulations | 1 599 | 280 | 1 879 | 21 % |
| dynamics | 641 | 128 | 769 | 8 % |
| slurs | 388 | 191 | 579 | 6 % |
| hairpins | 500 | 65 | 565 | 6 % |
| bars (insert / delete) | 296 | 110 | 406 | 4 % |
| words | 270 | 105 | 375 | 4 % |
| ties | 217 | 116 | 333 | 4 % |
| barlines | 203 | 117 | 320 | 4 % |
| lyrics | 242 | 55 | 297 | 3 % |
| chords | 0 | 212 | 212 | 2 % |
| tremolos | 174 | 12 | 186 | 2 % |
| playtech | 122 | 7 | 129 | 1 % |
| fermatas 93, clefs 90, system text 79, keys 67, structure 62, instruments 55, tuplets 31, rest 82 | 364 | 195 | 559 | 6 % |

By kind of book (the same 9 111; 107 system items left out):

| books | parts | actions | left | largest categories |
|---|---|---|---|---|
| Anastasia single-staff parts (strings, winds, brass) | 71 | 3 200 | 13.3 % | articulations 1 070, notes 456, dynamics 420, hairpins 294, slurs 229, words 216, playtech 122 |
| Anastasia keyboards | 12 | 1 522 | 11.7 % | notes 602, articulations 348, hairpins 136, ties 111, dynamics 104, slurs 98 |
| Anastasia drums / percussion | 33 | 1 100 | **43.8 %** | notes 475, dynamics 97, articulations 94, tremolos 83, bars 82, hairpins 62 |
| Anastasia singers | 14 | 864 | 21.5 % | lyrics 242, notes 213, articulations 87, bars 74 |
| Ghost piano reductions (piano) | 5 | 812 | 15.8 % | notes 352, articulations 125, chords 116, bars 50 |
| Ghost single-staff parts | 22 | 424 | 6.9 % | barlines 70, dynamics 65, slurs 60, notes 52, hairpins 41 |
| Ghost keyboards (Utility) | 5 | 384 | 16.6 % | notes 156, articulations 78, slurs 32, words 30 |
| Ghost guitar | 5 | 317 | 11.8 % | chords 95, notes 79, slurs 51 |
| Ghost singers | 4 | 207 | 17.2 % | notes 71, lyrics 55, bars 30 |
| Ghost drums | 3 | 174 | 5.8 % | notes 46, articulations 40, dynamics 24 |

**The six sparse truth parts** (Anastasia 3 Kontrabass, Trompete, Posaune, Keyboard 2; Anastasia 4 Trompete in B,
Posaune) hold **1 472 actions = 16 % of the score**: articulations 773 (41 % of all articulation actions), notes 193,
dynamics 142, hairpins 104, slurs 68. 928 of their about 1 000 "made-up" marks are in another truth part at the same
bar and beat, so they are gaps in the truth, not reading errors (`docs/TRUTH_DEVIATIONS.md` section 4). The user
completes these truths (2026-11-14); until then they stay in the score and inflate every "made up" row below.

## 3. Error kinds (differences), by cause

"sparse" = the six parts above. Classes: single = single-staff parts, keys = keyboards and Ghost pianos, perc =
drums / percussion.

| # | error | differences | where | cause | actions |
|---|---|---|---|---|---|
| 1 | articulations made up | 1 206: staccato 475, accent 377, tenuto 278, marcato 67 | sparse 714, single 225, keys 160, singers 54, perc 46 | truth gaps (sparse); the rest: Audiveris / homr dots, printed marks the truth leaves out | part of 1 879 |
| 2 | notes missing | 915 (825 notes, 90 chord notes) | keys 528, singers 144, sparse 110, single 80, guitar 48 | keyboards: dense two-voice bars, low ledger notes, homr drops a voice or a hand; singers: label routing, missing passages | part of 2 502 |
| 3 | articulations missing | 568: accent 264, staccato 180, tenuto 100 | keys 241 (Ghost 5 Piano 74), single 161, perc 66 | marks no reader finds (thin tenuto dashes, lower staff); Ghost pianos: glyphs not read on two-staff systems | part of 1 879 |
| 4 | pitch wrong | 756: more than a third 187, accidental missing 161 / made up 125, one or two steps 144, octave 125 | keys 315 + 67 + 40, single 220, singers 80 | keyboards: Ghost 5 / 20 Piano clef return missed, ledger notes; accidentals: crop key / carried accidentals | part of 2 502 |
| 5 | dynamics missing | 432: mp 119, mf 79, p 77, f 56, sfz 34, fp 23 | single 225, perc 98, keys 57, sparse 29 | no reader has them (not misplaced: only 4 of 409 have the same token made up in a neighbour bar); drum books and keyboards get no `.omr` dynamics | 769 with #6 |
| 6 | dynamics made up | 305: mp 64, f 62, mf 55, p 46, sfz 32 | sparse 110, single 100, keys 67 | truth gaps (sparse); homr misreads on keyboards / brass | |
| 7 | hairpins missing | 298 (cresc. 193, dim. 105) | keys 104, single 100, perc 59, sparse 28 | keyboards and drum books are left out of the `.omr` hairpins (R40); single: no reader finds them | 565 with #8, #9 |
| 8 | hairpins made up | 162 | sparse 70, single 65 | truth gaps; `.omr` wedges on the wrong staff | |
| 9 | hairpins at the wrong beat | 105 | single 91 | start note chosen by x; the stop is not scored at all | |
| 10 | drum hits missing / made up / wrong position | 279 / 126 / 62 | Anastasia 4 Schlagzeug 113 / 65 / 13, 3 Schlagzeug 64 / 44, 4 Tamburin 27 | two voices on one staff, grace notes read as hits, slash bars, kit bars routed to another instrument, kit 2-5 bars off around 180-206 | 475 + 46 |
| 11 | bars: missing / extra and their contents | 661: extra with notes 173, notes inside a missing bar 172, missing empty 145, marks inside 73, missing with notes 57 | singers 171, sparse 132, single 124, perc 121, keys 103 | mostly not bar errors: the alignment trades a badly read bar for delete + insert (drum kit bars, singers on the wrong staff, Ghost 4 Klavier 2-10) | 406 |
| 12 | slurs made up | 329 | single 131, keys 75, sparse 61 | printed 2-note slurs the truths leave out (TRUTH_DEVIATIONS), grace-note slurs, Audiveris pairing a tie end as a slur | 579 with #13 |
| 13 | slurs missing | 210 | single 97, keys 54, guitar 42 (Ghost 4 Electric Guitar 36) | not read; Ghost: Finale curves between different heads are not read from the drawing | |
| 14 | ties missing / made up / read as a slur | 211 / 87 / 24 | keys 72 / 41 (Anastasia 3 Keyboard 2 32), perc 35, singers 35 | keyboards: chords and second voices; over system breaks | 333 |
| 15 | barlines: double made up / missing | 184 / 116 | all books (a vote decision repeats in every part) | about 10 song-level decisions; Ghost 13 Cello / Bass 24 missing; made up: printed double barlines the truth lacks (Anastasia 3 bars 4, 22, 46, 87; 5 bar 124) | 320 |
| 16 | words made up / missing | 177 / 170 | single 108 / 91 | made up: "solo" 23, "to clarinet / flute / oboe" 12, "= 160 (in 3)" 7; missing: "arco" 38, "pizz." 31, "offen" 12, "gedämpft" 6 | 375 + playtech 129 |
| 17 | lyrics missing / made up / wrong | 154 / 96 / 37 | Anastasia 3 Frauen 35 / Männer 48, 4 Männer 24, Ghost 4 Sam 20, 5 Frauen 20 | choir syllables ("ah", "dah") on the wrong staff; a stray text line counted as a verse | 297 |
| 18 | rhythm | 254: x2 too long 67, onset shifted 52, 1/2 too short 46 | keys 59, single 56, perc 51 | Ghost 5 Piano 16ths read as 8ths; drum onsets | part of 2 502 |
| 19 | chords missing / made up / wrong beat | 134 / 71 / 34 | Ghost 4 Klavier 59 / 26, Ghost 20 Electric Guitar 21 wrong beat | piano reduction chord symbols (Ghost 20 truth has none: open user question), beat from x on an eighth grid | 212 |
| 20 | tremolos missing | 153 (+22 three strokes instead of one, Anastasia 5 Violins) | perc 83 (Schlagzeug 3 / 4, Becken 5), single 65 (Anastasia 3 Violine 2 21) | no reader sees the strokes; homr's token has no stroke count | 186 |
| 21 | playing techniques missing | arco 38, pizz 32, open 13 | Anastasia 4 Violine 1 20, Violoncello 16, Violine 2 14 | the word is not read; each costs 2 (word + technique) | 129 |
| 22 | fermatas missing / made up | 69 / 15 | spread, 1-3 per part | the vote needs 3 books; lower-staff fermatas not seen | 93 |
| 23 | clefs made up | 50 | keys 29, singers 13 | keyboard clef changes misread | 90 |
| 24 | system text made up | 66 | Anastasia 3: 19, 5: 15, 4: 8 | "tempo", "cresc.", "poco", "colla voce" taken as system text | 79 |
| 25 | small: structure 59 (repeat start missing 32), instruments 55, keys 53, tuplets 33, rehearsal 17, tempo 14 | | Ghost keyboards: instrument changes missing 24; singers: made-up instrument changes 30 | | 200 |

Reading it: without the sparse parts the largest real causes are (1) **keyboard notes and pitches** (about 1 100
actions over Anastasia keyboards and Ghost pianos), (2) **dynamics and hairpins** (about 1 100 actions without the
sparse parts; the user's worst pain, 2026-11-14), (3) **the Anastasia drum kit** (Schlagzeug 3 / 4: 622 actions,
half of typing them in), (4) articulations on keyboards and single-staff parts (about 1 100), (5) the singers
(lyrics + routing, about 1 070 over both shows).

## 4. Not in the score today, but hand work

The user wants all four groups scored (2026-11-14). Counts are XML elements in the truths / in the `r69-a` outputs,
not measured errors. Plan: `docs/IMPROVEMENTS.md` M1-M4.

| element | truths | outputs | today |
|---|---|---|---|
| grace notes | about 400 (221 with a slash) | 190 | left out of the note comparison; homr reads many as real 16ths (then scored as made-up notes) |
| curve end points (slur, tie, hairpin) | every curve | | only the start counts: a slur that ends on the wrong note, a tie without a stop, a hairpin of the wrong length cost 0; so does a mark on the wrong voice at the same beat |
| lyric hyphens and melisma lines | 935 syllabic begin / middle / end, 137 extenders | 1 098 / 161 | only verse and text count |
| arpeggio lines | 215 | 56 | not scored |
| "stopped" marks (+) | 162 | 0 | not scored |
| cue notes | 160 | 0 | left out |
| bowings (up / down) | 79 | 61 | not scored |
| cresc. / dim. dash lines | 62 | 0 | not scored |
| trills and wavy lines | 51 | 13 | not scored |
| octave lines | 30 | 15 | scored only through the pitches (1 action per section) |
| chord degrees (add9, ...) | 35 | 0 | C and Cadd9 compare equal |
| glissandi | 18 | 0 | not scored |
| pedal marks | 4 | 29 | not scored (25 made up) |

Also outside the score: `%` signs (`<measure-repeat>`, none in truths or outputs yet), the MuseScore instrument after
import (checked by the bench's "Percussion instruments" report, not counted), syllable hyphen display, and anything
in parts with no truth (Anastasia 5A, 6, the Klavierauszug piano).

## 5. sheet_reader (external vector reader, tested 2026-10-16)

`~/sheet_reader` (a friend's project, never edited from here) reads born-digital PDFs from the font glyphs. As an
engine on 14 Ghost parts it scored 6 440 actions against 1 387 for the pipeline (first test 7 111 / 1 341); bars
note-perfect only in sheet_reader: 15 of 1 132. It has no multi-rests, no grand staff, no transposition, one system
per page. Better than the pipeline only on dynamics (33 against 58 actions), repeats / voltas (all 8 found) and
mid-line key changes (22 against 36). The glyphs themselves are exact (Ghost 13 Cello: marcatos PDF 42 = truth 42,
pipeline 26 at the time; dynamics PDF 9, truth 10, pipeline 5). Decision (user 2026-10-16): no engine, no vote, no
code in its repo; ideas are ported into `pipeline/vector.py`, requests go to `docs/sheet_reader_requests.md`.
Details: archive file, section "sheet_reader".

## 6. Decisions that shape the counts

- A curve joining two neighbouring notes of the same pitch is a tie (applied when a truth is loaded). Double
  barlines stay as printed.
- "sim." and %-bars: Ghost writes them out with the pattern bar's marks; Anastasia keeps them as printed (truths not
  changed yet, TRUTH_DEVIATIONS table 1).
- Typographic quotes count as plain ones. Lyrics: verse 1 only.
- The Anastasia Klavierauszug piano is not generated and not scored (user 2026-11-09).
- The sparse parts stay in the score until the user has completed them (2026-11-14).
