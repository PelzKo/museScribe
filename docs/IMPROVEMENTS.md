# Improvements: what to do next, what worked, what did not

Backlog and memory of the pipeline work. Rewritten 2026-11-14 on the state `r69-a` = **9 111** actions
(Anastasia 6 762, Ghost 2 349). Error counts behind every item: `docs/ERRORS.md`. The long version with every
measurement note up to this date is `docs/archive/IMPROVEMENTS-2026-11-14.md`; item numbers (U.., R.., #..) are the
same there, so look an item up by its number when a detail is missing here.

## 1. Rules for every change

Acceptance rule (user 2026-10-15 / 16):
1. Reassemble all truth songs of both shows with the default `pipeline`, bench them, compare with the reference:
   `python scripts/reassemble.py <show> --from h71 --to NEW`, `omrbench bench <show> --run NEW --bench-id NEW`,
   `python scripts/compare_bench.py BASE NEW`. Work dirs with the homr 0.7.1 crops of the 12 truth songs:
   `results/<show>/runs/h71/pipeline/`. No re-reading is needed for assembly changes.
2. **Accept only if** the all-song total drops by at least 1 **and** no single part gets worse by more than half of
   that drop. Else reject and note "rejected, measured +N" in section 6.
3. One commit per accepted change on branch `improvements`; its bench id becomes the reference.
4. Metric-neutral user requests (playback, names, layout) are accepted when the total does not rise and the check
   named in the item passes. Metric changes are not gains: rebench the reference under the new metric first.
5. After a reassembly run refresh `results/<show>/<song>/` and `combined.mscz` (the user reviews those folders).

User priorities: (2026-11-14) **dynamics and hairpins hurt most**, drums / percussion second. (2026-10-18) bar
count and bar lengths must match the workbook. The six sparse truth parts stay in the score; the user completes
them (`docs/TRUTH_DEVIATIONS.md` section 4). Never edit `data/<show>/truth/`; `data/` otherwise may be edited.

## 2. Where to start (ranked)

The picture from `r69-a` (`docs/ERRORS.md` sections 2 and 3):

| rank | direction | actions in it | why here | items |
|---|---|---|---|---|
| 1 | Complete the six sparse truths (user) | 1 472, about 930 of them truth gaps | no code; 16 % of the score is not a pipeline error, and these parts block the acceptance rule for correct changes | T1 |
| 2 | Dynamics and hairpins | 1 334 (1 088 without the sparse parts) | the user's worst pain; three cheap sources are unused (vector glyphs on Ghost, `.omr` marks on keyboards and drum books) | D1-D8 |
| 3 | Score what is not scored | 0 today | the user wants grace notes, curve ends, lyric hyphens, ornaments scored; hairpin, slur and lyric work cannot be judged before | M1-M5 |
| 4 | Keyboard notes and pitches | about 1 100 | largest real note cluster (Anastasia keyboards 602, Ghost pianos 352 + 156) | K1-K4 |
| 5 | Anastasia drum kit and percussion | 1 100 (44 % of typing it in) | second priority of the user; Schlagzeug 3 / 4 = 622 | P1-P4 |
| 6 | Singers | 1 071 | lyrics 297, routing, bars traded for delete + insert | V1-V3 |
| 7 | Structure and text | barlines 320, words 375 + playtech 129, chords 212, slurs 579 | many small rules, each 20-100 | S1-S8 |

Suggested order: T1 (user, in parallel) -> D1, D2, D3, D8 (each small, measurable now) -> M1-M4 (rebaseline) -> D4,
D5, D7 -> K2, K1 -> P1, P2 -> the rest by gain.

## 3. Open items

"Expected" is an estimate in actions against `r69-a`; "max" is everything in that error kind.

### Truth and data (user)

| # | item | actions | note |
|---|---|---|---|
| T1 | Complete Anastasia 3 Kontrabass, Trompete, Posaune, Keyboard 2 and 4 Trompete in B, Posaune | about -930 | start from the `r69-a` output of these parts, it carries the marks; TRUTH_DEVIATIONS section 4 |
| T2 | Marcatos in the former plain rows of Anastasia 4 (Fagott, Posaune, Keyboard 2, Klarinette 2, Flöte 2) | -65 | TRUTH_DEVIATIONS table 1 / section 3 |
| T3 | Printed double barlines the truth lacks: Anastasia 3 bars 4, 22, 46, 87; 5 bar 124 | about -100 (5 bars in every part of the song) | confirmed 2026-11-13 |
| T4 | Printed 2-note slurs the truths leave out (Anastasia 4 Trompete 52-55 and more) | part of 329 made-up slurs | to fix in the truth (user 2026-11-13) |
| T5 | Ghost 20 piano: chord symbols or not (PDF prints them from bar 9 to 134) | +-16..100 | open since 2026-10-18; decides S5 |
| T6 | Anastasia "sim." / % as printed (R13): truths of songs 1, 2, 4 still written out | ? | pipeline change waits for the truths |
| T7 | Anastasia 4 Männer 65-71 "(BASS SOLO:)": which octave (R33) | -1..-5 | |
| T8 | Does the top-most-staff rule apply across instruments, or only inside one part / system? | decides D6 | the complete truth parts keep 95 % of the marks a higher part has |

Open questions for the user (asked 2026-11-14, not answered yet):
1. T8: is the top-most-staff rule meant across instruments, or only inside one part's staves? It decides D6 and
   whether the 159 dynamics / hairpins of the sparse parts that a higher part also has are gaps or right.
2. T5: Ghost 20 piano with or without chord symbols.
3. T7: octave of Anastasia 4 Männer 65-71.
4. P4: are Anastasia 2 Triangel / Schlagzeug, 3 Empress, 5 Mark Tree, 5 Vlad (no output) workbook mappings to fix
   or parts the pipeline must find?
5. M1-M4: how much is one grace note, one arpeggio line, one wrong slur end worth: 1 action each (assumed)?

### Dynamics and hairpins (first priority)

State: dynamics missing 432 / made up 305 / wrong beat 26; hairpins missing 298 / made up 162 / wrong beat 105.
The missing ones are missing, not misplaced (4 of 409 dynamics and 12 of 295 hairpins have the same token made up in
a neighbour bar). Sources today: homr 0.7.1 dynamics first; `.omr` dynamics of ctx-grade >= 0.8 by x into bars with
none (R54); `.omr` hairpins by x on scanned single-staff parts only (R40, R56); Tesseract dynamic words from
confidence 50; lone dynamics / fermatas dropped by the cross-book rule (R42).

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| D1 | **Ghost: dynamics glyphs and hairpin lines from the vector drawing.** `pipeline/vector.py` reads neither. Dynamics are music-font characters (sheet_reader `glyph_map.py`: p..fff, sfz, fp), hairpins two thin lines meeting at a point; place them by bar + x like `vector.read_marks` | Ghost dynamics 128 + hairpins 65 actions; sheet_reader's glyph dynamics beat the pipeline 33 : 58 on 14 parts | -80..-140 | medium |
| D2 | **`.omr` hairpins on keyboards and drum books.** R40 left them out: naive placement cost +62 on keyboards (cue staves and the conductor's vocal line: Anastasia 4 Keyboard 1 has 131 `.omr` dynamics, truth 50). Take only marks whose owner staff is a kept staff (`keep_staves`), a mark between the two piano staves once; drum books after the instrument split | hairpins missing: keys 104 (Anastasia 4 Keyboard 1 29, Keyboard 2 21, 3 Keyboard 2 20, 5 Keyboard 1 / 2 31), perc 59 | -60..-120 | small-medium |
| D3 | **`.omr` dynamics (R54) on keyboards and drum books**, same filter | dynamics missing: perc 98 (Anastasia 4 Schlagzeug 25, 5 Becken 18), keys 57 | -40..-90 | small |
| D4 | **Dynamics no reader sees (single-staff scans 225 missing).** First diagnose 50 of them: `.omr` inter of any grade, Tesseract word, or nothing at all? At most about 50 sit under the 0.8 grade (R60). Then the detector of #33: letter templates (m, p, f, s, z in the publisher's bold italic) cut from sure OCR hits, correlation in the band below each staff | mp 119, mf 79, p 77, f 56, sfz 34, fp 23 missing | -100..-200 | large |
| D5 | **Hairpins no reader sees** (single 100): two thin diverging lines in the band below the staff (Hough lines), after D2 | every `.omr` wedge is already placed | -40..-80 | medium-large |
| D6 | **Top-most-staff rule** (user 2026-11-14): a dynamic or text that several staves have at the same time in the same pattern is written only in the top staff. Safe reading: inside one two-staff part (keyboards, piano reductions) keep it on the top staff only. Across instruments the truths do not follow it (T8) | made-up dynamics on keys 67; six sparse parts: 159 dynamics / hairpins a higher part also has | -20..-50 inside a part; across parts only after T8 | small |
| D7 | **Hairpin start and end notes.** 105 start on the wrong beat (single 91); the end is not scored yet (M2). Tune the R56 start rule on those 91, then the stop once M2 exists | Anastasia 4 Horn 7, Violine 2 6, Violoncello 6 | -30..-60 | small |
| D8 | **Made-up homr dynamics** (single 100, keys 67 without the sparse parts): keep a homr dynamic only when an `.omr` dynamics inter (any grade) or an OCR token lies within the bar's x range | R58: homr 670 kept / 211 made up on Anastasia | -30..-80; measure, may cost right ones | small |

Do not retry (measured, section 6): copying or voting dynamics across books, moving lone dynamics to the other
books' bar, grade or size cuts on `.omr` hairpins, `.omr` dynamics below grade 0.8, `max_wedge_bars` 4, lone-dynamic
threshold 3.

### Metric coverage (user wants all of it scored, 2026-11-14)

**None of M1-M6 is implemented yet** (state 2026-11-14: `metrics/edits.py` is unchanged). Each one is a measurement change: implement in `musicxml.part_staves` + `metrics/edits.py` + `scripts/error_report.py`,
rebench `r69-a`, write the new reference here, only then judge pipeline changes. Counts: ERRORS section 4.

| # | what | rule to settle | scope |
|---|---|---|---|
| M1 | Grace notes | a grace note is (staff, onset of its main note, pitch, slash yes / no); missing or made up = 1 | about 400 in the truths, 190 in the outputs; homr reads many as real 16ths (Anastasia 3 Violine 1 bar 26) |
| M2 | Curve end points and the note a mark hangs on (R34) | pair start and stop; one wrong curve = 1, not 2; renumbering is free; marks keep their voice / note | slur starts 2 498 against 2 178 stops in the outputs (pairing audit); makes U4, U8, D7 measurable |
| M3 | Lyric hyphens and melisma lines (R35) | syllabic begin / middle / end and extender start / end with the lyric; omitted = single; no double charge for a missing lyric | truths 137 extenders; U5's work scores 0 today |
| M4 | Ornaments and technique | arpeggio lines, trills / wavy lines, glissandi, bowings, "stopped", cresc. / dim. dash lines, pedal marks: 1 each per (staff, onset, token); chord degrees (R38: normalised chord token with added / altered degrees, `chords.KINDS` writes `<degree>`) | truths 215 / 51 / 18 / 79 / 162 / 62 / 4; degrees 35 |
| M5 | Bench provenance (R39) | store hashes of truth, workbook mapping / flags and metric code in `scores.json`; `compare_bench` refuses unlike inputs | a truth fix must never look like a pipeline gain; needed while T1-T4 change the truths |
| M6 | `%` signs (`<measure-repeat>`) | score the sign once, not the copied notes | only when the Anastasia truths keep the signs (T6) |

### Keyboards and piano reductions

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| K1 | **Anastasia keyboards: per-staff reading instead of per-bar.** Notes missing 528 on keyboards. Today a bar is taken from one reader for both staves. Use the `.omr` head chords (stem side, pitches, values: loaded since R45f) per staff: where homr's staff has fewer heads than Audiveris found, rebuild that staff like `assemble.kit_bars`, keep the other. Diagnose 30 bars first (which hand, which voice) | Anastasia 4 Keyboard 2 63, 3 Keyboard 2 59, 4 Keyboard 1; chord notes missing 90 | -100..-250 | medium |
| K2 | **Ghost pianos: notes from the vector drawing.** Heads, stems, beams and flags are exact on vector pages; `read_drum_page` / `read_marks` already read them per staff. A two-staff note reader (pitch from the head's y and the clef glyph, values from beams / flags) checks or replaces homr's bar | Ghost 5 Piano 240 (16ths read as 8ths, treble return missed 25-27, E1 read as B1), 20 Piano 286, 4 Klavier 178; "wrong by more than a third" 111 on Ghost; Ghost piano articulations 125 come with it | -150..-300 | large |
| K3 | Keyboard clef changes (clefs 90 + the pitches after them): clef glyphs from the drawing on Ghost, the `.omr` clef inters on scans | made-up clefs keys 29 | -30..-60 | small-medium |
| K4 | Accidentals: 161 missing, 125 made up (Anastasia 120). homr writes no `<accidental>`; check against the `.omr` accidental inters by x, and the bar's carried accidentals (R32: 66 semitone errors around key changes, Anastasia 4 Keyboard 1 bars 31-32) | Anastasia 4 Keyboard 1 26, Violine 2 17, Klarinette 2 17 | -50..-100 | medium |
| K5 | Ties on keyboards: missing 72, made up 41 (Anastasia 3 Keyboard 2 32 is a sparse part: wait for T1) | | -20..-40 | small |
| K6 | Ghost 4 Klavier 2-10 / 41-46: the truth keeps only the piano's own hand (other-instrument notes are rests) | bars 30 + notes | -20..-40 | small |

### Drums and percussion

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| P1 | **Anastasia kit, what R45 left.** (a) around 180-206 of song 4 the kit is 2-5 bars ahead (extra groove bars next to the 182-184 multi-rest); (b) grace notes (flams) read as hits: made up D4 / F5 / E5; drop small heads; (c) ride F5 read as G5 / E5 in 197-204; (d) still empty: 34-38, 44-45, 80-85; (e) lower-staff hi-hat bars 174-177 need the "sticks" label or head shape | Schlagzeug 4: 392 (hits missing 113, made up 65), 3: 230 (64 / 44) | -100..-200 | medium |
| P2 | **Tremolos (rolls).** 153 missing: drums 83 (Schlagzeug 3 / 4, Becken 5), strings 65. No reader gives the stroke count. Detect the strokes on the stem of homr's note (`imgpos` x, short thick diagonal lines across the stem); drum rule: a half / whole roll has 3 strokes. Anastasia 5 Violins: 1 stroke written as 3 (22) | | -60..-120 | medium |
| P3 | Dynamics and hairpins in drum books | = D2 / D3 | | |
| P4 | Parts with no output: Anastasia 2 Triangel and Schlagzeug, 5 Mark Tree (and 3 Empress, 5 Vlad): workbook mapping or routing | 27 + small | -20..-40 | small |
| P5 | Ghost 4 Drum Kit: accents at the wrong beat 15, wrong position 15 (two voices: marks above = hands, below = feet, R17) | | -10..-25 | medium |

### Singers

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| V1 | Choir syllables on the right staff: Anastasia 3 Frauen 35 missing / Männer 48 made up ("ah", "dah"); a stray text line next to the lyrics still becomes a verse (Anastasia 4 Frauen "(I tenor)") | lyrics 297 | -50..-100 | medium |
| V2 | Anastasia 4 Männer / Vlad: notes inside missing bars 29 / 25, made-up instrument changes on singers 30, finale 199-211 "+DMITRY & VLAD:", Frauen two voices as chords 57-64 | singers notes 213, bars 74 | -50..-120 | medium-large |
| V3 | Ghost 5 Frauen (20 lyrics, no output part in places), Ghost 4 Sam 20 | | -20..-40 | small |
| V4 | Label spellings from the generic-voice list (U16): "Vvomen", "Ens", "Willie", "Cue" | | small | tiny |

### Structure, text, curves

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| S1 | Barline types from the vector drawing on Ghost (two thin strokes = double, dots = repeat), never built | Ghost barlines 117 + structure 25; Ghost 13 Cello / Bass 24 missing | -60..-100 | medium |
| S2 | Repeat starts still missing 32 (Anastasia 28); song 2 bar 30 in every part | structure 62 | -20..-40 | small |
| S3 | "arco" / "pizz." missing 70 words, each also a technique (2 actions): strict alternation rule (a missing "arco" between two "pizz." is certain), OCR at lower confidence on string parts only | Anastasia 4 Violine 1 20, Violoncello 16, Violine 2 14 | -40..-90; -2 before `playtech` existed, re-measure | small |
| S4 | Made-up words: "solo" 23, "to clarinet / flute / oboe" 12, "= 160 (in 3)" 7 as part text (R30 leftover; the lone-word rule keeps playing words) | words made up 177 | -30..-50 | small |
| S5 | Chord symbols: 34 at the wrong beat (snap to the slash / note x under the symbol, #37), Ghost 4 Klavier 59 missing / 26 made up, Ghost 20 piano after T5; missing suffixes add11, add13, m9, maj9, 7sus4, 7b9 (R18) | chords 212 | -40..-100 | small |
| S6 | Slurs: grace-note slurs (R70: count them in the truths first), slurs from the vector curves on Ghost (missing 98, Electric Guitar 36), ties over system breaks (#39) | slurs 579 | -40..-100 | medium |
| S7 | System text made up 66 ("tempo", "cresc.", "poco", "colla voce") and Ghost rehearsal letters made up 15 | | -30..-50 | small |
| S8 | Fermatas: vote per book and with lower-staff marks (R36); 69 missing, 1-3 per part | fermatas 93 | -20..-40 | medium |
| S9 | Octave lines: 15va / 15vb, lines below the staff, "8va ad lib." = 8va (R19) | | 0..-30 | medium |
| S10 | Tie repairs by musical time (R37): `close_ties`, `slurs_to_ties`, `tie_held_chords` bridge a `<forward>` gap | unmeasured; needs M2 to show | ? | small-medium |

### Not quality (kept short)

- Speed: parallel songs instead of parallel PDFs (#13); cache Audiveris per page (#14); homr on GPU at fp32 gave
  no speed-up (#15).
- Usability: results viewer page per song (#16); `transcribe` refuses to start on workbook errors (#17); README per
  song folder (#18); one command to link a new truth (#2).
- Engineering: tests for the container scripts (#19); pin Clarity weights, llama.cpp image, OCR models (#20);
  regression samples from real failures via `reassemble()` (#3).
- Prior knowledge not used yet: written range per instrument (#27; R15 found nothing to gain on single-staff parts),
  staves / clef per book (#28), rehearsal and tempo list per song (#31), libretto for lyrics (#32).
- More truth songs of other types (#1): choir, drum parts, keyboards, reed books with many instrument changes.

## 4. Score history

Totals are comparable only inside one block; the blocks differ in songs, truths or metric.

| block | reference chain | what changed between blocks |
|---|---|---|
| 2026-10-14..16, 6 truth songs | sweep / `fix4` -> `p1` 7 336 -> `p1-q` 7 342 -> `p1-t` 7 377 | quotes normalised, tie-vs-slur convention, Ghost 13 truth fixes |
| 2026-10-18, 10 songs | `r3-base` 12 423 -> `r3-f` 11 946 -> `r3-k` 10 962 | Ghost 4, 5, 11a and Anastasia 4 finished added |
| 2026-11-01/02 | `r4-t` 11 026 (truth marcatos +64) -> `r4-ref` 11 259 (`playtech`, `instrument` scored +233) -> `r4-k` 10 662 -> `r5-b` 9 766 | metric additions |
| 2026-11-02, + Anastasia 3 | `r6-ref` 13 735 -> `r6-a3` 13 060 -> `r12-a` 11 998 | song 3 linked |
| 2026-11-09, 12 songs | `r13-ref` 13 863 -> `r14-h70` 13 555 -> `r14-h71` 12 243 -> ... -> `r69-a` **9 111** | song 5 added, `plainArticulation` flags of songs 1 / 2 / 4 / 4A removed, Klavierauszug piano not scored |

## 5. What worked (accepted)

Gain in actions at the time it was measured; the code name tells where it lives.

Readers and engine
- **homr 0.7.1 (R49): -1 312.** Needed `bars.homr_as_printed` (drop the estimated time of crops without a printed
  time, fold n-measure multi-rests back, merge the empty measure before a repeat start: alone 13 486 -> 12 844),
  homr dynamics first (Audiveris' of that bar not added), `bar_ok(side_voices=True)` (-345: one voice per staff must
  fill the bar, further voices only lie inside it), pattern bars must add up, main crop loaded before its `-m4` /
  `-m3` retries. As a plain version bump it was +253.
- Song rows `time`, `key`, `bars` in the workbook (#25 -1 279 / -134; #26 -379 with dropping extra rest bars);
  `letters` row (#53 -394 on Anastasia 4).
- `bars.respell_key` (#43 -81); `fit_measure_rests` (#44 -153; rest-only voices -125; U7 -13); `pad_short_bar`
  -164; `cut_long_bar` -62; `rewind_voices` (U6 -39).
- R50a printed time signatures from the vector drawing -164; R14 `keep_first_clef` on one-staff parts -15.

Marks placed by image x (homr `imgpos`), the pattern that paid most in November
- R51 `.omr` articulations onto homr notes by x (staccatos only from ctx-grade 0.8; kit accents too): **-263**.
- R40 `.omr` hairpins on scanned single-staff parts -217; R56 hairpin start on the nearest note + homr's head x -127.
- R54 `.omr` dynamics of grade >= 0.8 into bars with none -19; R58 no Audiveris-export dynamics on homr bars -127.
- R7 hairpin order in `add_direction` -8; Tesseract dynamic words from confidence 50 -13; U4 `attach_wedges` -2.
- `bars.copy_marks` (Audiveris accent / marcato / tenuto onto homr notes, scans, no staccato) -56.

Cross-book rules (`transcribe.share_marks`, one vote per book, parts with the song's bar count)
- R1 double barlines and repeats by vote -439 (one vote per part was +2); R27a threshold 45 % and a repeat end for
  a kept start -101; R27b double barline before a cut moves to the last inserted bar -41; R47 repeat signs from the
  `.omr` repeat dots -103.
- R41 words only one book has dropped (playing words kept) -263; R42 lone dynamics (>= 4 books playing) and lone
  fermatas (>= 3) dropped -135; fermata vote with the `bars` row as a number -4.

Vector pages (Ghost, Anastasia piano reductions)
- Slash reader (#7 -615), printed barlines on single-staff systems (#12 -487; #8 -503 on drums), chord symbols from
  the text layer (#11 -109), measure repeats written out (-46), octave sections from patch labels (#9 -251).
- R3 drum kits from the MaestroPercussion glyphs -896; R4 guitar pattern continued over slash bars -733.
- R5 glyph articulations -107; "sim." from the text layer -64, over other bar lengths -8; R52 "sim." window 5
  interlines -72; `apply_sim` (#47) -105, %-bars by page position -56.
- R8 slur beside a tie dropped -246; ties from the vector curves -53; made-up slurs without a curve -15; half
  heads "˙" -39; slurs copied after "sim." -9; `slurs_to_ties` on the output (#46) -288; chord ties -69.
- R44 Ghost 5 drums: groove over slash bars -61, kit re-derived -194, "sim." marks -26, pseudo-bars at repeat
  barlines dropped -131.
- R66 lyrics from the PDF text layer **-224**; R69 lyric lines numbered from 1 per bar -31; R6 singer labels from
  the text layer -557.

Drums and percussion (Anastasia scans)
- R2 "sticks" alias + a percussion label inside a kit passage takes only its bar -183; R45a kit re-derived, bar
  read in bass clef moved up -33; R45b label after a pitched bar -52; R45c groove copied over unread slash bars
  -42; R45e two-position bars of the lower staff go to the kit -38; R45f kit bars rebuilt from the `.omr` head
  chords (stems up / down = two voices) -99; R45g cut mark joined with a dynamic -15.
- R43 one-instrument percussion on the truth's staff line -71; Audiveris bars on percussion staves (#8) -106.

Singers and text
- R62 unlabelled choir staff takes its first later label -104; R67 instrument cue staves stay out of the singers
  -38; R50b "ALL MEN" not merged into "ALL WOMEN" -82; R21 `plainText` shared lyrics only in the first voice -93.
- Words: cue lines, dialogue, part labels out of instrument parts (#23 -264); system text only for tempo terms
  (#50 -178); R12 `words: drop` on Anastasia Keyboard 1 / 2 -103; R25 duplicate directions -5.
- R65a slurs to or from a rest dropped -40; U8 `drop_long_curves` (ties > 2 bars, slurs > 6) -4; R20 duplicate
  curves -2; cues up to "Play" -29.
- U12 cut bars placed at the system break -39.

Metric-neutral user requests, done (2026-11-11 / 12)
- U1 percussion instruments import as the truth's (33 of 33), U2 / U15 "hide if empty" per show, U5 printed
  hyphens and melisma lines, U9 sordino words, U10 German names, U11 Klavierauszug piano to `<song>/vote/`, U13
  duet labels into both singers, U14 overrides moved into `data/`, U16 generic voice for unknown singers, U17
  checked (no change needed), R22-R24 pizz. / arco / mute playback (-30) and real instruments (-114).

## 6. What did not work (do not retry without a new idea)

| tried | result | why |
|---|---|---|
| Copying a mark into the books that lack it (R42, R60) | dynamics +35 / +57 (half the books) / +23 (three quarters), hairpins +19, tremolos +10, articulations +1 597 | marks differ per instrument far more than the bar structure |
| Moving a lone dynamic / hairpin to the other books' bar | +7 / +8 | |
| Dropping lone hairpins / tremolos / slurs / ties / tenutos | +15 / +53 / +88 / +197 / +94 | they are mostly real |
| Lone-dynamic rule from 3 books (R59) | +1 | |
| `.omr` dynamics of every grade (R54a) / next to homr's (R40) | +1 / +43 | half are made up below grade 0.8 |
| Dynamics moved to the note under their `.omr` glyph (R55, U3 placement) | +1 / +0 | they already sit on the glyph's onset |
| Grade or size cut on `.omr` hairpins (R61, not run) | every class is 80 % right | a cut drops four right ones per made-up one |
| `max_wedge_bars` 4 (R16) | +2 | long pairings are misreads |
| `.omr` marks naively on keyboards / drum books (R40) | keyboards +176, drums +11 | cue staves, vocal line; see D2 |
| Marcato from the `.omr` shape (R46) | +1 | Audiveris reads the same accent; only homr's token or a crop shape check could tell |
| Audiveris staccatos copied (R5 `r7-a`, R50c) | -4 with parts +13 / +12 | made-up dots; use grade 0.8 by x (R51) |
| homr bars first on percussion staves (R49) | +180 (second candidate +60) | Audiveris first is better there |
| Kit rebuild also on equal hits (R45h); kit accents by onset (kacc) | +33; +20 / +6 | filled readings beat x-placed onsets; carry accents by x |
| Kit default for the lower staff (R45d); unpitched bars to the kit (R68) | +0; +0 / +10 | the kit bars there do not match the truth anyway |
| Cut mark split off any following text (R45g-a) | +313 | only when the rest is dynamics |
| Gap rests not before a numbered system start (R63) | +19 | cannot tell a system-start number from a misread cut label |
| `imgpos` x only for instrument parts (R57) | +14 / +12 | the vocal marks gain from it |
| `piano_part: false` without the piano's vote (U11 first try) | +40 | `share_marks` needs the piano as a voter |
| Chord symbols on every Ghost piano reduction | +72 | Ghost 20 truth has none (T5) |
| Double barline before every key change (#45) | +99 | Ghost 20 changes key without one |
| Audiveris double barlines per part (#22) | +129 | wrong bars; the vote (R1) fixed it |
| Slurs from Audiveris instead of homr (#22) | +106 | |
| Accents from the Ghost glyphs with only Ghost 13 / 20 as truth | +13 | Ghost 20 Reed truth has accents the page lacks; later accepted with more truths (R5) |
| Vector barlines on multi-staff systems (#35) | +3 500 on the Anastasia piano reduction | staves barred apart; group the system first |
| Numbered singer labels kept apart (R6 `r6-b`) | -7 with one part +20 | workbook maps only one of them |
| Placing wedges while assembling (U4 `u4-a`) | +14 | later bar repairs reorder the items |
| Dropping a tie over a voice change (U8 `u8-a`) | +4 | the truth ties it |
| homr 0.7.1 as a plain bump; margin-3 crops | +253; song 1 538 against 413 | see R49; retry order 5, 4, 3 is right |
| sheet_reader as engine or per-bar vote | 6 440 against 1 387 | ERRORS section 5 |
| Zeus, SMT, Clarity, Oemer as readers; OLA, EasyOCR, docTR, Paddle, Qwen as components; fp16 homr on GPU | all worse than homr on CPU + Audiveris + Tesseract | `docs/PLAN.md` section 7, `docs/engine-benchmark.md` |
| Range check on single-staff parts (R15) | nothing to gain | no note is more than a whole tone outside its range; the far-off notes are on keyboards |

## 7. Learnings

- **Audiveris finds more than it exports.** Hairpins, dynamics, articulations, repeat dots and head chords with stem
  sides are in the `.omr`; the MusicXML export drops what it cannot link. Read the `.omr` (`layout.py`) and place by
  image x on homr's notes (`imgpos`). This gave about -800 in November (R51, R40, R56, R47, R45f, R54). Check the `.omr` before building a
  detector.
- **Bar structure can be voted across books, marks cannot.** Barlines, repeats, fermatas and "only one book has it"
  filters work; copying dynamics, hairpins or articulations between books always lost.
- **On vector pages the drawing is exact.** Text layer (lyrics, labels, "sim.", chord symbols) and glyphs (drum
  heads, slashes, articulations, ties, time signatures) beat every OCR. Not read yet: dynamics, hairpins, barline
  types, slur curves, pitched notes on two-staff systems.
- **A large "made up" count on one part is usually the truth.** Sparse parts, printed slurs, printed double
  barlines, marcatos: check another truth part at the same bar and beat (TRUTH_DEVIATIONS section 4 method) before
  writing a filter.
- **`bars` actions are rarely bar errors.** The alignment trades a badly read bar for delete + insert; fix the
  bar's contents (kit bars, singer routing), not the count.
- **Measure on the same inputs.** Truth fixes, workbook flags and metric changes moved the total by hundreds
  (section 4). Rebench the base first (M5).
- **Simulate before coding.** A rule simulated on the aligned bars of the reference landed close to the real
  change: R41 simulated -247, real -263; R43 -69 / -71.
- **Counting bugs:** pairs keyed by `id()` of lxml proxies gave 454 phantom duplicate slurs; key by position.
- Traps: `sorted(glob)` puts `s01-g1-m3` before `s01-g1`; the workbook `bars` cell is text; `data/` is gitignored,
  so workbook and show.yaml edits must be listed in the commit message or here.
- `scripts/derive_drumkit.py <show>` must be re-run after every new drum truth.
