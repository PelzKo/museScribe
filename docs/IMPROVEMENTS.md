# Improvements: what to do next, what worked, what did not

Backlog and memory of the pipeline work. Rewritten 2026-11-14 on the state `r69-a` = **9 111** actions
(Anastasia 6 762, Ghost 2 349). Error counts behind every item: `docs/ERRORS.md`. The long version with every
measurement note up to this date is `docs/archive/IMPROVEMENTS-2026-11-14.md`; item numbers (U.., R.., #..) are the
same there, so look an item up by its number when a detail is missing here. 2026-11-15: evidence run on dynamics,
hairpins and low keyboard notes after the 5A truth (sections "Dynamics and hairpins", "Keyboards"; items D2, D4, D9-D11,
K7-K9, T9 are new or rewritten; nothing benched, nothing changed in the pipeline). Same day: an independent second
investigation (`docs/CODEX_IMPROVEMENTS.md`, C1-C9) was checked against the source and the data; what held up is
merged below (D12, D13, S11 new; D1, D2, D7, D10, K7-K9 extended). The user fixed truths of songs 3, 5, 5A that day
(T1, T3): **rebench `r69-a` before judging any change**; the open truth errors are in `docs/ANASTASIA_TRUTH_FIXES.pdf`.

**2026-11-15 (later): metric M1-M4 implemented, new reference `r70-ref` = 9 941** (Anastasia + Ghost, 13 songs: 5A
work dirs copied into `h71`, reassembled with unchanged code; current truths). The same outputs score 8 961 under
the old metric: +980 = grace 219, hairpin ends 181, slur ends 177, technique (stopped) 164, ties without stop 59,
bowings 41, lyric syllabic / melisma 34, ornaments 33, pedals 27, dashes 16, arpeggios 14, glissandi 7, chord
degrees 7. User answers of the same day: section 3, "Answers". Accepted the same day (section 5): staff order /
short names / key fix (neutral), D2, D9, D12, D7, D1, D4: D4 on drum books (-11) and Ghost vector hairpins (-29): `r82-ref` = 9 665. 2026-11-26: singer labels S12 (section 5): **current reference `r83-lab2` = 9 629** (Anastasia 6 948, Ghost 2 681; copied into `results/<show>/<song>/`).
Born-digital books (Ghost, Anastasia piano reduction): what the PDF itself gives and the pipeline does not read is in
`docs/BORN_DIGITAL_IMPROVEMENTS.md` (B1-B13, TB1-TB4; sharpens D1, K2, K9, S1, P2).

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
| 2 | Dynamics and hairpins | 1 334 (1 088 without the sparse parts) | the user's worst pain; evidence run 2026-11-15: keyboard / drum hairpins are in the `.omr` (-86 simulated), a template detector finds 84 % of the missing dynamics (-100), R42 drops 79 right dynamics (-36); Ghost vector glyphs unused | D2, D9, D4, D1 |
| 3 | Score what is not scored | 0 today | the user wants grace notes, curve ends, lyric hyphens, ornaments scored; hairpin, slur and lyric work cannot be judged before | M1-M5 |
| 4 | Keyboard notes and pitches | about 1 100 | largest real note cluster (Anastasia keyboards 602, Ghost pianos 352 + 156); low ledger notes are right only 71 % (-79 simulated from the `.omr` heads) | K7, K1-K4 |
| 5 | Anastasia drum kit and percussion | 1 100 (44 % of typing it in) | second priority of the user; Schlagzeug 3 / 4 = 622 | P1-P4 |
| 6 | Singers | 1 071 | lyrics 297, routing, bars traded for delete + insert | V1-V3 |
| 7 | Structure and text | barlines 320, words 375 + playtech 129, chords 212, slurs 579 | many small rules, each 20-100 | S1-S8 |

Suggested order (2026-11-15): T1 (user, in parallel) -> bench 5A into a new reference -> D2 -> D9 -> D12 -> D4 -> K7 -> D1
-> M1-M4 (rebaseline) -> D11, D7 -> K2 / K9, K1 -> P1, P2 -> the rest by gain. D2, D9, D4, K7 are simulated on the
aligned bars (about -250..-300 together, D9 lies partly inside D4); each still has to pass the acceptance rule.

## 3. Open items

"Expected" is an estimate in actions against `r69-a`; "max" is everything in that error kind.

### Truth and data (user)

| # | item | actions | note |
|---|---|---|---|
| T1 | Complete Anastasia 3 Kontrabass, Trompete, Posaune, Keyboard 2 and 4 Trompete in B, Posaune | about -930 | start from the `r69-a` output of these parts, it carries the marks; TRUTH_DEVIATIONS section 4. 2026-11-15: 3 Kontrabass articulations done (100 -> 220), dynamics / hairpins not; per-bar lists of what is left (1 113 marks, 11 parts) in `docs/ANASTASIA_TRUTH_FIXES.pdf` |
| T2 | Marcatos in the former plain rows of Anastasia 4 (Fagott, Posaune, Keyboard 2, Klarinette 2, Flöte 2) | -65 | TRUTH_DEVIATIONS table 1 / section 3 |
| T3 | Printed double barlines the truth lacks: Anastasia 3 bars 4, 22, 46, 87; 5 bar 124 | about -100 (5 bars in every part of the song) | **fixed by the user 2026-11-15** (also 5A bars 5, 21 and Kontrabass "Arco"); not in the reference yet |
| T4 | Printed 2-note slurs the truths leave out (Anastasia 4 Trompete 52-55 and more) | part of 329 made-up slurs | to fix in the truth (user 2026-11-13) |
| T5 | Ghost 20 piano: chord symbols as printed (user 2026-11-15); the truth lacks them: truth deviation | +-16..100 | decides S5: write them on Ghost 20 too |
| T6 | Anastasia "sim." / % as printed (R13): truths of songs 1, 2, 4 still written out | ? | pipeline change waits for the truths |
| T7 | Anastasia 4 Männer 65-71 "(BASS SOLO:)": treble clef + "(8vb)" = one octave below (user 2026-11-15, R33) | -1..-5 | pipeline: read "(8vb)" next to a treble clef as an octave line |
| T8 | Top-most-staff rule applies across all instruments (user 2026-11-15) | decides D6 | the complete truth parts keep 95 % of the marks a higher part has: check against the truths before coding D6 |
| T9 | Anastasia 3 Violoncello looks like a seventh sparse part: truth 7 hairpins / 11 dynamics, output 18 / 26, 15 / 20 "made up"; the template detector finds 13 printed dynamics the truth lacks (bars 13, 70, 110, 130, 136, ...). Anastasia 4 Horn: 9 printed `mf` / other the truth lacks (bars 11, 88-91: cue passages?). Counting also the ones the output already has: 3 Violoncello 28 dynamics, 4 Fagott 15, 4 Horn 10 | about -35 + ? | found 2026-11-15; list: `results/errors/2026-11-15-dynamics/truth-gap-candidates.md` |

Answers (user 2026-11-15):
1. T8: the top-most-staff rule holds **across all instruments**: a dynamic / hairpin several staves have at the
   same time is written only in the top staff. So the 159 marks of the sparse parts that a higher part also has
   are right to be absent, and D6 may work across parts.
2. T5: Ghost 20 piano **with** chord symbols where the sheet prints them; a truth without them is a truth
   deviation (TRUTH_DEVIATIONS).
3. T7: Anastasia 4 Männer 65-71: treble clef with "(8vb)": one octave below the written treble.
4. P4: Anastasia 3 Empress and 5 Vlad are spoken lines above the bars: missing output is fine. 5 Mark Tree must be
   found at bar 88 (part of the drum book). 2 Triangel is printed normally and starts in the lower part of bar 1.
   The suspended cymbal is probably part of the Schlagzeug (drum kit).
5. M1-M4: 1 action each (implemented so).
6. T9: open, the user checks it; **ask again next time**.

### Dynamics and hairpins (first priority)

State `r69-a`: dynamics missing 432 / made up 305 / wrong beat 26; hairpins missing 298 / made up 162 / wrong beat 105.
Sources today: homr 0.7.1 dynamics first; `.omr` dynamics of ctx-grade >= 0.8 by x into bars with none (R54); `.omr`
hairpins by x on scanned single-staff parts only (R40, R56); Tesseract dynamic words from confidence 50; lone
dynamics / fermatas dropped by the cross-book rule (R42).

**Evidence run 2026-11-15** (Anastasia 1-5 from `h71` plus the new truth 5A, six sparse parts left out; scripts and
data in `results/errors/2026-11-15-dynamics/`, see section 7). For every bar: what homr, the `.omr` (any grade) and
Tesseract saw, what the plan held before the cross-book rules, what the output and the truth have. All numbers below
are simulated on the aligned bars, not benched.

Why a dynamic is missing:

| books | missing | no reader has it | read, then removed (R42 lone rule, singers: routing) | `.omr` >= 0.8 has it, not placed | `.omr` has another token | only OCR / `.omr` < 0.8 / neighbour bar |
|---|---|---|---|---|---|---|
| single-staff parts | 201 | 70 | **55** | 34 | 17 | 25 |
| drum books | 84 | 21 | 26 | 14 | 7 | 16 |
| keyboards | 26 | 2 | **18** | 5 | 1 | 0 |
| singers | 14 | 0 | 14 | 0 | 0 | 0 |

Why a hairpin is missing:

| books | missing | `.omr` has it | `.omr` has it in a neighbour bar | no reader |
|---|---|---|---|---|
| keyboards | 100 | **94** | 4 | 2 |
| drum books | 52 | **45** | 1 | 5 |
| single-staff parts | 63 | 21 (not in the output: D11) | 12 | 21 |

Song 5A (truth added 2026-11-14, about 40 differences, not in the reference yet) shows every cause: `ppp` for the
printed `mp` in 3 parts and `fz` for `f` in 2 (homr; the `.omr` had the right token in 1 of 3 and 1 of 2); `f` at
bar 18 missing in 4 single-staff parts and `mf` in the Horn (a clean glyph 4 to 5 interlines below the staff, no reader
or homr's `sfz`); Violine
1 `mp` bar 3 read by the `.omr` and Tesseract, then dropped by R42 (the other books have it in bar 2); all 5 missing
keyboard hairpins are in the `.omr` between the staves; drum book 6 dynamics missing, 1 in the `.omr`.

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| D2 | **Accepted 2026-11-15: -29 (`r71-d2` = 9 912).** `.omr` hairpins on keyboards between the two staves (placed on staff 1), on drum books below the staff; the readers' hairpins stay, a bar that has the hairpin gets none (`vocal.place_marks(zone=...)`). Simulated -86 under the old metric: with curve ends scored (M2) an added hairpin whose stop is wrong gains nothing, see D7 | | done | |
| D4 | **Accepted 2026-11-15: -43 (`r79-d4` = 9 705).** In the pipeline: `pipeline/dynamics.py`, templates from `.omr` boxes of grade >= 0.9 that look like their token's median (`scripts/derive_dyn_templates.py anastasia` -> `data/anastasia/dynamics_templates.npz`), overlapping hits keep the best (without: `sfz` + `fz` from one glyph, -1 only), template-token dynamics the detector does not see are removed (D8 / D10). Less than simulated: D9 / D12 took part of it, the remaining "made up" hits are mostly printed glyphs the truths lack (4 Klarinette 2 bar 106 `mp`, 3 Violoncello: T9). Drum books: run `r80-d4dr`. Was: **Dynamics detector by template correlation (tested).** The glyphs are one bold italic font per show. Templates: mean image per token of the `.omr` dynamics boxes of grade >= 0.9 (in the test: the ones the truth confirms; in the pipeline: the ones homr reads the same), scaled to 8 px per interline: `mf` `mp` `p` `f` `sfz` `fp` `fz`. Normalised cross-correlation in the band 0.3 to 7 interlines below the staff, per bar. Scores are bimodal: real glyphs >= 0.9, everything else <= 0.75; threshold 0.85 | 53 single-staff books, 4 459 bars: finds **118 of 141** missing dynamics of these tokens; misses 10 of 412 right ones; does not see 26 of 74 made-up ones; 34 hits the truth lacks (13 in Anastasia 3 Violoncello and 9 in 4 Horn, see T9); 9 sampled hits viewed on the page: all printed glyphs with the right token. 5A: 31 of 31 truth dynamics, 0 wrong | add where the output has none of the token: **-84**; detector as the only reader of its 7 tokens: **-100**. Needs D9's exemption (a detector hit is never "lone") | medium: new `pipeline/dynamics.py` (numpy FFT, about 80 lines), then drum books (below the staff), keyboards (between the staves), singers (above the staff) |
| D9 | **Accepted 2026-11-15: -60 (`r72-d9`).** Was: **R42: keep a lone dynamic that two readers agree on.** R42 drops a dynamic no other book has in the bar. Of 166 drops, 79 were right dynamics (the other books have the same mark one bar earlier or later, or rest). With two of homr / `.omr` glyph of any grade / Tesseract word agreeing: 51 right, 15 wrong; with one reader or none: 28 right, 72 wrong. Carry the agreement from the plan into the output (attribute on the `<direction>`), `drop_lone_marks` skips those | keyboards lose 18 of their 26 missing dynamics this way, singers 14 of 14 | **-36** (simulated); part of D4 once that exists | small |
| D10 | **Done inside D4** (the detector removes the token it does not see). Was: **Token conflicts: homr against the `.omr`.** One homr dynamic and one `.omr` dynamic of grade >= 0.8 with another token in the same bar (45 bars): `.omr` right 20, homr right 14, neither 11. Keep homr when Tesseract reads homr's token: 20 : 8. homr's `ppp` was `mp` in 5 of 5, `fz` was `f` / `sfz` in 6 of 9 | 5A: Cello, Klarinette 2, Horn bar 2; Kontrabass bar 18. C5: `place_dynamics` refuses a second dynamic anywhere in the bar; allowing one at another onset only pays with this token check (without it 31 right / 33 wrong, section 6) | -10..-15; D4 covers it | tiny |
| D1 | **Dynamics accepted 2026-11-15: -15 (`r75-d1` vs `r73-d12`)**: `vector.read_dynamics`, glyphs replace the readers' dynamics on vector pages except piano reductions; Ghost 20 loses a few printed dynamics the truth leaves out (T8). Hairpin lines not done yet. Was: **Ghost: dynamics glyphs and hairpin lines from the vector drawing.** `pipeline/vector.py` reads neither. Dynamics are music-font characters (sheet_reader `glyph_map.py`: p..fff, sfz, fp), hairpins two thin lines meeting at a point; place them by bar + x like `vector.read_marks`. C3: take only the exact font `EngraverFontSet` (`p`, `P` = mp, `F` = mf, `f`, `ƒ` = ff, `π` = pp; compound dynamics are one glyph); every font starting with `Maestro` also hits an `s` of `MaestroTimes-BoldItalic` text; `ß` is already read as accent + staccato (`vector.py`), so tell `sfz` apart by position. Start with Ghost 13 Cello and 5 Utility | Ghost dynamics 128 + hairpins 65 actions; sheet_reader's glyph dynamics beat the pipeline 33 : 58 on 14 parts; candidates on the pages: 13 Cello 9, 5 Utility 7, 4 / 5 / 20 PianoReduction 12 / 16 / 25 | -80..-140 | medium |
| D11 | **Small (2026-11-15):** songs 3-5 single-staff: 713 `.omr` hairpins placed, 13 unplaced (start and stop on one note: D7 places those now), 13 dropped by `limit_wedges`. Not worth a change. Was: **Single-staff hairpins the `.omr` has but the output lacks** (21, plus 12 placed in the neighbour bar): find where they go (pairing in `V.place_marks`, `limit_wedges`, a wedge starting just before a barline). Diagnose first | | -15..-30 | small |
| D7 | **Hairpin start and end notes.** 2026-11-15 (M2 scored): of the hairpins with the right start on `r71-d2`, 170 stop too early in the same bar, 22 too late, 10 in another bar: the truths (MuseScore export) stop at the *end* of the last note under the tip, `vocal.place_marks` used its start. Stop at the note end: songs 4 + 5A -59 (full run `r76-d7`). Before: 105 start on the wrong beat (single 91); the end is not scored yet (M2). Tune the R56 start rule on those 91, then the stop once M2 exists. Stops (C5): candidates are note ends, bar ends and rests, not only note starts (5A Horn truth stop at 2.5); place after the bar repairs (U4 `u4-a` lost by placing while assembling) | Anastasia 4 Horn 7, Violine 2 6, Violoncello 6; 5A Kontrabass, Fagott bar 16. Stops: 5A has 6 hairpins with the right start and another stop (Violine 1 twice, Violine 2, Horn, Trompete, Keyboard 2); all Anastasia songs at most 170 of 536 same-start pairs (single-staff parts paired by bar order, so an upper bound) | -30..-60 | small |
| D3 | **`.omr` dynamics on drum books** (grade >= 0.8, unused: 19 right / 14 wrong). Keyboards: nothing to gain (unused `.omr` dynamics 23 right / 40 wrong; their missing ones are R42 drops, D9) | 5A Pauken `f` bar 20 | -5; better through D4 on drum books | small |
| D5 | **Hairpins no reader sees**: only 28 left in Anastasia (single 21, drums 5, keys 2) once D2 is in: two thin diverging lines in the band below the staff | was estimated 100 before the evidence run | -15..-25 | medium-large |
| D6 | **Top-most-staff rule: no change (simulated 2026-11-15).** User: the rule holds across all instruments (T8). But of the `r71-d2` output dynamics that a higher part (show.yaml `staff_order`) has at the same bar, onset and token, the truths keep 573 and lack 260 (Anastasia; Ghost 42 : 12): dropping them loses about +300. Inside a two-staff part: 3 cases. Asked the user whether the truths should follow the rule | | 0 | - |
| D12 | **Accepted 2026-11-15: -15 (`r73-d12`)**, whole-token atoms only (no split off bar numbers). Was: **Dynamics Audiveris read as lyric text (C1, simulated).** The `.omr` holds `mf`, `f`, `p`, `fz` ... as text atoms of role `Lyrics`. They never become dynamics: `text.is_words` wants two letters (`f`, `p` fail), `text.classify` drops lines made only of lyric fragments, `ocr.supplement` adds no Tesseract word where an Audiveris text covers the box, and `ocr.DYNAMIC` lacks `fz`, `sffz`, `rfz`, `pppp`. Collect dynamic tokens from the single text atoms before the line grouping, into their own list; split them off a bar number or cut mark (`[to] 16 mf`); place like R54 where the bar has none of the token. Not on keyboards and piano reductions (0 right / 6 wrong), not on vocal staves | single-staff parts: 37 of the 201 missing dynamics (24 of them no other reader has), 11 wrong (some are T9 truth gaps); drum books 14 of 84, 7 wrong; all of role `Lyrics`. 5A: `mf` / `f` bars 16 / 18 in Cello, Horn, Reed 1, Trombone. `results/errors/2026-11-15-dynamics/textatoms.py` | **-26** single-staff, **-7** drums (simulated); lies inside D4, but needs no detector | small |
| D13 | **Owner of a mark from the `.omr` relation graph (C2).** `layout._parse_sheet` keeps shape, box and grade of a dynamics / wedge inter, `Mark.staff` stays 0, `vocal._owner` guesses by y (`piano_group` exists only on vocal scores). The `chord-dynamics` relation names the chord, so the staff, so kept or cue staff. Use it before the position rule of D2 / D3; check that the chord survives the cue removal. Not simulated on all songs | 5A Keyboard 1: 7 dynamics of grade >= 0.8: 3 belong to the cue staff, 4 to the piano staves; one unlinked `p` of grade 0.64. May turn the losing classes (`.omr` dynamics on keyboards 23 / 40, hairpins above the upper staff 30 / 22) into usable ones | ? (simulate first) | small-medium |
| D8 | **Done inside D4.** Was: **Made-up homr dynamics**: on single-staff parts 121 made up: homr alone 42, homr and `.omr` same token 28, placed from the `.omr` 27, homr against another `.omr` token 20. The detector (D4) does not see 26 of 74 made-up against 10 of 412 right ones: drop those | | -16, inside D4 | - |

Order (2026-11-15, after D2 D9 D12 D7 D1 D4): D4 on drum books -> D1 hairpin lines -> D13 -> D5. D6: no change (simulated).
D10 and D8 are part of D4; D3 waits for D4 on drum books.

Do not retry (measured, section 6): copying or voting dynamics across books, moving lone dynamics to the other
books' bar, grade or size cuts on `.omr` hairpins, `.omr` dynamics below grade 0.8, `max_wedge_bars` 4, lone-dynamic
threshold 3, a second `.omr` dynamic in a bar that has one, Tesseract tokens below confidence 50, `.omr` dynamics on
keyboards, `.omr` hairpins above the upper keyboard staff.

### Metric coverage (user wants all of it scored, 2026-11-14)

**M1-M4 implemented 2026-11-15** (`musicxml.part_staves` tokens, `edits.PART_CATS`; `error_report.py` reads the new
categories without change): grace notes `g:<sounding midi>[/]` at the main note's onset; slur / hairpin tokens carry
`><bars later>:<stop onset>` (`>?` without a stop), a tie without its stop reads `tie>?`; lyrics carry
`|begin|middle|end` and `_` for a melisma line; categories `arpeggios` (once per chord), `ornaments`, `glissandi`,
`bowings`, `technique`, `dashes`, `pedals`; chord tokens include `<degree>`s. Not done: the note / voice a mark hangs
on (R34 second half: voice numbers differ between readers and truths, needs its own design). New reference
`r70-ref` = 9 941. M5 and M6 still open.

| # | what | rule to settle | scope |
|---|---|---|---|
| M1 | Grace notes | a grace note is (staff, onset of its main note, pitch, slash yes / no); missing or made up = 1 | about 400 in the truths, 190 in the outputs; homr reads many as real 16ths (Anastasia 3 Violine 1 bar 26) |
| M2 | Curve end points and the note a mark hangs on (R34) | pair start and stop; one wrong curve = 1, not 2; renumbering is free; marks keep their voice / note | slur starts 2 498 against 2 178 stops in the outputs (pairing audit); makes U4, U8, D7 measurable |
| M3 | Lyric hyphens and melisma lines (R35) | syllabic begin / middle / end and extender start / end with the lyric; omitted = single; no double charge for a missing lyric | truths 137 extenders; U5's work scores 0 today |
| M4 | Ornaments and technique | arpeggio lines, trills / wavy lines, glissandi, bowings, "stopped", cresc. / dim. dash lines, pedal marks: 1 each per (staff, onset, token); chord degrees (R38: normalised chord token with added / altered degrees, `chords.KINDS` writes `<degree>`) | truths 215 / 51 / 18 / 79 / 162 / 62 / 4; degrees 35 |
| M5 | Bench provenance (R39) | store hashes of truth, workbook mapping / flags and metric code in `scores.json`; `compare_bench` refuses unlike inputs | a truth fix must never look like a pipeline gain; needed while T1-T4 change the truths |
| M6 | `%` signs (`<measure-repeat>`) | score the sign once, not the copied notes | only when the Anastasia truths keep the signs (T6) |

### Keyboards and piano reductions

Low notes (2026-11-15, `r69-a`, truth notes of keyboards and pianos by ledger lines below the staff, right = same
staff, beat and pitch): Anastasia in the staff 95 % of 6 483, one line 94 %, two lines 87 % of 454, **three or more
71 % of 329** (37 read too high, mostly 2 to 5 staff steps; 55 missing). Ghost pianos three or more: 83 % of 367 (37
too high, 25 missing). Notes above the staff are as good as inside it (94 %). Single-staff parts: 85 % of 55.

| # | idea | evidence | expected | effort |
|---|---|---|---|---|
| K7 | **Low keyboard notes from the `.omr` head positions (simulated).** Audiveris counts the ledger lines (`Chord.steps`, loaded since R45f); homr guesses them. For a homr note below the first ledger line: take the `.omr` head chord of the same staff at its x (`imgpos`, within 0.6 interlines); when the low heads differ and the `.omr` has at least as many, replace homr's low pitches by the `.omr` positions (same clef, key and accidentals) and add the heads homr lacks (the lower octave note) | Anastasia keyboards incl. 5A: 237 bars change, 52 better, 4 worse, rest equal; 5A Keyboard 1 bars 18-21: 4 of 5 note errors (C7: the Audiveris export has all 5 right there, also the E♭5 inside the staff, but its Keyboard 2 bar 1 is worse than homr's, 3 against 2: repair heads, never take the whole bar). One-for-one replacement only: -39. The same rule above the staff: +15, leave out. homr's `imgpos` y is too coarse for pitch (0.43 staff steps median error) | **-79** (simulated) | small-medium |
| K8 | **Deeper crops for keyboards.** A crop ends 5 interlines below the lowest staff (room for 4 ledger lines) or half-way to the next staff; the `-m4` / `-m3` retries cut more. Where the `.omr` has heads lower than that, crop that group with 8 interlines below and re-read it. C8: `_run` retries a crop only when homr fails; also retry a crop that reads but looks wrong (fewer heads than the `.omr`, a head at the crop edge), keep the first reading when the new one loses upper notes | 3+ ledger lines: 55 notes missing on Anastasia; 5A Keyboard 1 system 2: lowest chord 1 px above the crop's lower edge (2 446 of 2 447.1); not tested (needs a homr re-read of the 14 keyboard books) | ? | small, slow to measure |
| K9 | **Ghost pianos: pitch of low notes from the head glyph's y** in the vector drawing (exact), as a first step of K2: only correct the pitch of an existing note at that x. C9: `scripts/pdf_truth_check.py` has this reader already (heads, staff lines, clefs, accidentals): make it a verifier on the output's timeline; a run of notes shifted alike = check the clef first (K3) | Ghost 20 Piano 26, 5 Piano 18, 4 Klavier 10 wrong or missing with 3+ lines. Ghost 5 Piano: its pitch sets equal the truth in bars 19-22 (output E1 as A1 / B1) and 25-27 (wrong clef); it fails on the cue / repeat bars 3-7, 34-35 (negative tests) | -40..-60 | medium |
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
| P4 | Parts with no output (user 2026-11-15): 5 Mark Tree from bar 88 in the drum book, 2 Triangel from the lower part of bar 1, suspended cymbal = Schlagzeug; 3 Empress and 5 Vlad are spoken, may stay missing | 27 + small | -20..-40 | small |
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
| S11 | **Written "cresc." / "dim." as staff expressions (C6).** `assemble.TEMPO_TERMS` holds `cresc`, `dim`, `decresc`, `poco`: above the top staff they become system text (S7 made-up "cresc.", "poco"); Anastasia keyboards drop all words (`words: drop`). Classify them as expressions of their staff first; keep the word, no wedge; the dashed line as `<dashes>` | truths 62 `<dashes>`, outputs 0 (scored only with M4); "cresc." is both missing part text and made-up system text | -10..-30 now, more with M4 | small |
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
| 2026-11-15, 13 songs, metric M1-M4 | `r70-ref` 9 941 -> `r71-d2` 9 912 -> `r72-d9` 9 852 -> `r73-d12` 9 837 -> `r78-ref` 9 748 (+ D7, D1) -> `r79-d4` 9 705 -> `r82-ref` 9 665 -> `r83-lab2` **9 629** | 5A added (work dirs from run `20261114-102221` in `h71`), truths of 3 / 5 / 5A fixed by the user, grace notes / curve ends / lyric syllabic / ornaments scored (+980 on the same outputs) |

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

Dynamics and hairpins, 2026-11-15 (metric M1-M4, reference chain in section 4)
- D2 `.omr` hairpins on keyboards between the staves / drum books below the staff -29; D7 hairpin stop at the end of
  the last note under the tip -74 (the truths stop there; M2 made it visible).
- D9 R42 keeps a dynamic two readers agree on -60; D12 dynamics in Audiveris text atoms -15; D4 template detector
  (overlap suppression, removes template tokens it does not see) -43; D1 Ghost dynamics from the vector glyphs -15.

Singer labels of the vocal scores, 2026-11-26 (Anastasia 7 / 8 transcription)
- S12 **-36** (`r83-lab2`): text-layer labels in brackets ("(GLEB:)", `engine.py` read_lines pattern); labels of up
  to four words ("DRUNKS 2 & 4", `text._LABEL`); numbered labels are never OCR spellings of each other ("DRUNK 1" /
  "DRUNK 3", "GROUP 1" / "GROUP 2", "BLACK MARKETEER #1..#3"; `assemble._spelling`). Song 4 then has the parts
  Black Marketeer #3 and Group 2: workbook truth cells Black Marketeer #3=Frauen, Group 2=Frauen, Group 1=Männer
  (was Frauen + Männer) and `male_voices: [Dmitry, Vlad, Group 1]`. Ghost 4 Sam -3, Anastasia 4 Männer -26,
  Frauen -7. A label naming several singers by number ("DRUNKS 2 & 4") still needs `singer_groups`.

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

Metric-neutral user requests, done 2026-11-15 (`r70-lay` = 9 941, every part unchanged)
- combined.mscz: parts in show.yaml `staff_order` (the truths' order), show.yaml `short_names` as MuseScore short
  names; Ghost parts shown with the truths' names. The `.mscz` gets the key of transposing staves written in C
  (MuseScore's import drops it: 5A clarinet / trumpet showed concert C).

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
| D4 add-only, no overlap suppression (`r74-d4b`); with removal but no suppression (`r77-d4x`) | -1; -11 with Klarinette 2 +8 | `fz` inside `sfz`, `p` inside `mp`: two tokens from one glyph |
| D6 top-most-staff rule across instruments (simulated on `r71-d2`) | truths keep 573, lack 260 of the dynamics a higher part has | the truths do not follow it (asked the user) |
| A second `.omr` dynamic (grade >= 0.8) in a bar that has one (simulated 2026-11-15) | 31 right / 33 wrong | the bar's own dynamic is often the same glyph read as another token; needs the detector (D4) |
| Tesseract dynamic tokens below confidence 50, or the unused ones from 50 (simulated) | 1 / 9; 9 / 20 | |
| `.omr` dynamics on keyboards (simulated) | 23 right / 40 wrong | printed for a cue or the lower staff; the missing ones there are R42 drops (D9) |
| `.omr` hairpins above the upper keyboard staff (simulated) | 30 right / 22 wrong | cue staff, vocal line; between the staves 87 / 15 (D2) |
| Grade, width, height, distance cuts on placed `.omr` hairpins of single-staff parts (simulated) | no class separates | the 65 "made up" are mostly printed (T9, sparse parts) |
| Pitch from homr's `imgpos` y (K7 test) | 0.43 staff steps median error in the staff | one y per chord, not per head; use the `.omr` head positions |
| Low `.omr` heads replacing homr's also when the `.omr` has fewer (K7 test) | -57 with 15 bars worse, against -79 / 4 | Audiveris misses heads too: never drop |
| `.omr` text atoms as dynamics on keyboards and piano reductions (D12 test, simulated) | 0 right / 6 wrong | printed for a cue or the other staff; single-staff 37 / 11, drums 14 / 7 |
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
- **Ask every reader before building one** (`results/errors/2026-11-15-dynamics/diag.py`): it reassembles a work
  dir, tags each dynamic / hairpin in the plan with its source and dumps per bar what homr, the `.omr` (all grades)
  and Tesseract saw. `truthitems.py` gives truth and output items per aligned output bar, `join.py` / `lone.py` /
  `sim.py` the tables of section 3, `tmpl.py` the template detector test, `ledger.py` / `ledger2.py` / `l2eval.py`
  the ledger-line tables. The folder is not in git (`results/`).
- **A reader's text is a reader too.** Audiveris files bold italic `mf` / `f` under lyrics; 51 missing dynamics sat
  in the `.omr` texts while only its dynamics inters and Tesseract were asked (D12). `allitems.py` dumps every truth
  and output marking per aligned bar; `truthfix_pdf.py` builds `docs/ANASTASIA_TRUTH_FIXES.pdf` from it.
- **Join by the aligned bar, not by the printed number.** Anastasia 4 has lettered bars (131A): keyed by the truth's
  bar number, a fifth of the dynamics landed in the wrong bar and printed glyphs looked like detector errors.
- **A cross-book filter needs to know how sure a mark is.** R42 removes as many right dynamics as wrong ones when it
  only counts books; with the readers' agreement it is 51 : 15.
- **Counting bugs:** pairs keyed by `id()` of lxml proxies gave 454 phantom duplicate slurs; key by position.
- Traps: `sorted(glob)` puts `s01-g1-m3` before `s01-g1`; the workbook `bars` cell is text; `data/` is gitignored,
  so workbook and show.yaml edits must be listed in the commit message or here.
- `scripts/derive_drumkit.py <show>` must be re-run after every new drum truth.
