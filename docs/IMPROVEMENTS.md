# Improvement ideas

Ideas for making museScribe better, roughly in order of value. Status and results of the planned phases are in
`PLAN.md`; this file is the backlog of things not planned yet.

## Acceptance rule (every improvement, user 2026-10-15 / 16)

Every change to the pipeline (and every item below) is measured before it is kept:

1. Reassemble (or re-transcribe) all truth songs of Anastasia and Ghost with the default `pipeline` and bench
   them; compare with the current reference bench id (`docs/PLAN.md` section 5) via
   `python scripts/compare_bench.py BASE NEW`.
2. **Accept only if** the all-song total edit penalty drops by at least 1, **and** no single part (one song, one
   instrument) gets worse by more than half of that total drop.
3. Otherwise reject it (keep the result in `PLAN.md` / here as "rejected, measured +N"). Accepted changes get
   one commit each on branch `improvements`; the new bench id becomes the reference.
4. Work through the fixes in order of expected gain and stop when the gains flatten out.

## User requests (2026-11-09): try these first

The user's feedback after opening the outputs in MuseScore, plus two tasks the user wrote up. These items are
**user-requested and come before every other item in this file**; each still goes through the acceptance rule.
Items that do not change the metric (U1, U2, U10, U11) are accepted when the total does not get worse and the
check named in the item passes. Reference: `r13-ref`, every song reassembled with the code of 2026-11-09 after the
workbook changes of the same day (song 5 truth linked, `plainArticulation` flags of songs 1 / 2 / 4 / 4A removed,
Anastasia Klavierauszug piano no longer scored: `Piano=-` in every PianoReduction `truth` cell). `r13-ref` = **13 863**
(Anastasia 9 999: 1 430, 2 380, 3 2 942, 4 5 084, 4A 138, 5 1 025; Ghost 3 864). The outputs of `r13-ref` were copied into
`results/anastasia/<song>/` with a new combined.mscz (2026-11-09), so the user reviews today's code. There the
unpitched percussion parts (Cymbal, Triangle, Bell Tree, Tambourine, Wood Block, Castanets, the song 4 mallet
Xylophon) still import as `percussion-synthesizer`; Timpani, Glock, Crotales, Drum Set are right (U1).
Counts below: Anastasia songs 1, 2, 3, 4, 4A, outputs `r12-a` (Klavierauszug left out).

| # | Improvement | Max | Expected | Effort | Needs the user |
|---|---|---|---|---|---|
| U1 | Percussion parts import as the real instrument (not "percussion-synthesizer" / piano) | 0 (metric reads the MusicXML) | 0; saves re-assigning every percussion part | medium | no |
| U2 | "Hide if empty" on every part of the MuseScore file, as in the truths | 0 | 0 | small | no |
| U3 | Dynamics: more found, on the right bar and beat | 727 missing + 349 made up | -100..-300 (detector: R7 / #33) | large | no |
| U4 | Hairpins attached to notes (no `<offset>`), more found | 539 missing + 81 made up | -50..-200 | medium | no |
| U5 | Lyrics: hyphens on the right syllables, melisma lines | lyrics share of the score | -30..-100 | medium | no |
| U6 | Bar lengths: no bar longer or shorter than its time signature | ~10 bars Anastasia 3 / 5 (+ MuseScore "corrupted" bars) | -10..-20 | small | no |
| U7 | Rest-only bars as one full-bar rest | done for rest-only voices (R9, `r11-a2`) | check what is left | small | no |
| U8 | Ties span at most 2 bars, slurs at most 6 | 5 ties, 1 slur (`r12-a`) | -5..-6 | tiny | no |
| U9 | "con sord." / "sordino" = gedämpft, "senza sord." = offen | 0 in the current truths | 0 | tiny | no |
| U10 | German instrument names as in the truths | 0 | 0 | small | no |
| U11 | Anastasia Klavierauszug piano not generated | 0 (not scored since 2026-11-09) | 0; saves time | small | no |
| U12 | Cut bars placed at the system break (align_bars) | Anastasia 5A: 4 parts × 10 bars | 5A has no truth: 0; fewer misplaced bars | small | no |
| U13 | Duet labels into both singers (`singer_groups`, "DIMITRY") | song 6, no truth | 0 | small | no |

U1. **Percussion instruments (user 2026-11-09: "they all have a midi mix instead of Glockenspiel or Bells").** The
truths use the MuseScore instruments `crash-cymbal` (Hängendes Becken), `splash-cymbal`, `triangle`, `mark-tree`,
`bell-tree`, `glockenspiel`, `crotales`, `timpani`, `tambourine`, `wood-blocks`, `castanets`, `xylophone`,
`drum-kit-5` (Schlagzeug). Song 5 `combined.mscz` (code of 2026-11-02): Crotales, Glock and Timpani import right,
but Cymbal, Triangle and Bell Tree become `percussion-synthesizer`, because MuseScore maps an unpitched part with an
`<instrument-sound>` it does not know as an unpitched kit to the synthesizer. Song 1–4A outputs of 2026-10-18 had no
sounds at all (piano). Plan: (1) per song, the instrument names of the book map to the truth's instrument (song 5
"Cymbal" = Hängendes Becken = crash, songs 1 / 4 = Splash-Becken): `sound` per instrument in `show.yaml`, a song
override in the `instruments` cell ("Cymbal (sound: metal.cymbal.crash)"); (2) unpitched parts get a full
`<score-instrument>` + `<midi-instrument>` with `<midi-unpitched>` and notes with `<unpitched>` + `<instrument id>`,
tested with a `to_mscz` round trip per instrument; if MuseScore still falls back, (3) post-process the `.mscz`: swap
the `<Instrument>` block of the part for the one MuseScore writes for that instrument id (taken from a score saved
by MuseScore, e.g. the truth). Check: open each combined.mscz, the `<Instrument id>` of every percussion part equals
the truth's. The metric's `instrument` category reads the output MusicXML, so it does not see this; add the check
to the bench report (instrument id after the round trip).

U2. **Hide empty staves (user 2026-11-09).** The truths keep the style `hideEmptyStaves` 0 and
`dontHideStavesInFirstSystem` 1, and set `<hideWhenEmpty>on</hideWhenEmpty>` on every `<Part>` ("Hide if empty:
always" per instrument in MuseScore 4). MusicXML has no such setting, so do it after `to_mscz`: open the .mscz
(zip), add the element to every `<Part>` of the .mscx and the style keys, write it back. Check: the combined.mscz
of song 5 has 23 `<hideWhenEmpty>on` parts and opens without a warning.

U3. **Dynamics (user: "dynamics is bad and a lot is missing; often in the wrong bar").** Of 952 truth dynamics 727
are missing and 349 output dynamics are made up; 21 missing ones are in the output one bar off, 27 in the right bar
on another beat (same token). Most missing ones are on the scans, where Audiveris does not find them (R7, #33). Plan:
(1) the detector (#33: template match of p / mp / mf / f / ff / sfz glyphs under the staff, OCR fallback);
(2) placement: a dynamic goes to the note whose head is nearest in x *within the bar the glyph's x lies in* (now the
onset comes from the Audiveris direction offset, which can cross the barline); (3) cross-part vote: a dynamic found in
most parts of a book group at the same bar and beat is a strong hint for the parts that miss it (orchestral tutti),
but only as a check, never copied blindly (dynamics differ per instrument).

U4. **Hairpins attached to notes (user: "crescendi and decrescendi (the symbols) should be attached to notes and not
moved or placed by hand; many are wrong").** The outputs write wedges as `<direction>` with an `<offset>` (e.g.
Anastasia 4 Violin 1, 42 wedges, offsets 36 / 60 / 84): MuseScore then puts the hairpin at a time position that
may hold no note, and the user drags it. Plan: drop `<offset>` on wedges, put the start direction right before the
note at the start onset and the stop before the note (or after the last note) at the end onset, both snapped to the
nearest note / rest onset of that staff; a stop that lands on the start's onset moves to the next note. 539 of 624
truth hairpins are missing and 81 made up: same detector work as U3 (hairpins are two lines meeting at a point:
Hough lines on the scans, vector lines on the born-digital pages). Measure the attachment part separately (wedge
items move from "wrong beat" to matched).

U5. **Lyrics: blanks, hyphens and melisma lines (user: "between 'in my dreams' there should be blanks not dashes,
especially underscores 147, 148, 149").** Song 5 Anya: the syllable pairing is shifted by one: "found" (begin) +
"by" (end) shows "found-by", "road." (begin) + "There" (end), "a" (begin) "round," (middle) "it" (end); the real
"re-cent-ly" is right. Melisma lines: the outputs have none (0 of 942 lyrics), the truths 42; song 5 bars 147–149
"back___" needs one. Plan: (1) take the hyphen from the PDF text layer of the vector PianoReductions (a "-" glyph
between two syllables) instead of inferring it; a syllable is `begin` / `middle` only when a hyphen follows it on
the page; (2) an underscore line (a horizontal line at lyric height after a syllable) gives `<extend/>` on that
syllable and `<extend type="continue|stop">` up to the line's end note; (3) test on song 5 bars 8–15, 147–149.

U6. **Bar lengths (user: "Anastasia 3 or 5, bars 77, 79, 87, 115, 145, 156 have a wrong length; MuseScore says the bar
is corrupt and the note values do not add up").** It is song 5 (`results/anastasia/5`, code of 2026-11-02): Keyboard 2
bars 77, 79 (4.5 quarters), 87, 115 (7), Keyboard 1 145 (4), Reed 2 156 (4); song 3 has Keyboard 2 87, 145 and
Trumpet 156. Cause (R9 leftover): the voices of two staves follow each other with no `<backup>` between them, or a
voice is split by `<forward>`, so the bar's length is the sum. Plan: a last pass per bar and voice in
`write_score`: each voice's notes must end at or before the bar length; a voice that starts after another voice's
end without a `<backup>` gets one (rewind to the bar start), else the overflow is cut as in `cut_long_bar`. Check:
MuseScore converts every song without `-f` ("corrupted") where the bar counts agree.

U7. **Full-bar rests (user: "a bar of only rests gets the full-bar rest, not single rests").** Done for whole voices
of rests in R9 (`r11-a2`, -125). Check in the refreshed outputs which bars still show several rests (likely a second
voice of rests next to a full bar rest, or rests in a bar with an empty voice 1), then extend `fit_measure_rests`.

U8. **Tie and slur length (user: "ties can only be in 2 bars, slurs maximum in 6 bars").** `r12-a`: 5 ties over more
than 2 bars (Anastasia 3 Fagott, Keyboard 1, Klarinette 1 / 2, 4 Trompete), 1 slur over more than 6 bars (4 Violine 1).
Plan: in the last pass with `drop_duplicate_curves`, drop a tie whose stop is not in the same or the next bar (and
the dangling start), and a slur whose stop is more than 5 bars after its start.

U9. **Mute words (user: "con sord., sordino, con sordino all mean gedämpft; senza sord., senza sordino stop it").**
`text.MUTE_ON` already takes "con sord." / "con sordino", `MUTE_OFF` "senza sord." / "senza sordino"; add "sordino",
"sord.", "con sordini", "mit Dämpfer" / "ohne Dämpfer", and make sure the translated word also gets the playback
(`musicxml.play_techniques`: "gedämpft" -> mute on, "offen" -> off). These words are not in the current truths, so
the check is a unit test.

U10. **German instrument names (user: like the truths).** Output part names and instrument names as in the song 4
truth: Violine 1 / 2, Violoncello, Kontrabass, Piccolo, Flöte n, Oboe, Englisch Horn, Klarinette in B n, Fagott,
Horn in F, Trompete in B, Posaune, Pauken, Glockenspiel, Crotales, Xylophon, Glockenbaum, Mark Tree, Triangel,
Hängendes Becken / Splash-Becken, Holzblöcke, Kastagnetten, Tamburin, Schlagzeug; Keyboard 1 / 2 keep their names;
singers keep their labels (Frauen, Männer for Women / Men). The number n is the reed book's (Reed 2 Flute = Flöte 2)
or the truth's. Source: a `german` name per instrument in the `show.yaml` library (one place), used by
`set_sounds` for `<part-name>` and `<instrument-name>`. Not scored (bench maps by the workbook). Check: the
combined.mscz part list reads like the truth's.

U11. **Anastasia Klavierauszug piano (user 2026-11-09: "can be ignored in the future, both in generating and in
scoring").** Scoring: done in the workbook (`Piano=-`). Generating: a `show.yaml` meta key (`piano_part: false`)
makes the vocal-score engine write only "PianoReduction - Voices" (no "- Piano" file, not in combined.mscz); the
piano staves are still read, because the voices' bars, barlines and system text come from the same systems.
Check: songs 1–5A bench unchanged, no "- Piano" file.

U12. **Empty bars of a cut at the system break (user task, 2026-11-09).** Anastasia 5A (`omrbench transcribe
anastasia --songs 5A`, output `results/anastasia/5A/`, run `20261105-010953`): the parts print bars 1–5, then a new
system starting with "[to] 16" (cut; bars 6–15 stay as empty bars, workbook `bars` 21). In Violin 1, Cello, Horn and
Reed 2 the "[to] 16" label was not read, so the first number after the gap is "17" at system 2 bar 2. `align_bars`
takes the else branch ("printed bar number 17") and inserts the 10 rest bars right before bar 17: printed 16 lands at
output bar 6 and output bar 16 is empty (log: "10 rest bar(s) inserted before page 1 system 2 (#2) bar 2 (printed bar
number 17)"). Fix: when a gap is closed by a printed number and a system break lies between the last confirmed bar and
that number, insert the rests at the system break (end of the previous system, where cuts are printed), not right
before the numbered bar. The rest-extension branch ("after the rest at ...") keeps priority; fall back to "right before
the number" only without a system break in the gap. Check: reassemble 5A from its run (`scripts/reassemble.py`);
bars with notes: Violin 1 1–5 and 16–21, Cello / Horn / Reed 2 2–5 and 16–21; Bass, Reed 1, Reed 3, Trumpet, Trombone,
Keyboard 1, Keyboard 2, Violin 2 unchanged; bench both shows (acceptance rule); a test in `tests/` for a gap closed by a
mid-system number after a system break. Out of scope (OCR misreads): Drums bar 1 "1" read as "11"; PianoReduction
"[to] 16" read as "[to] 15".

U13. **Duet labels in the No. 6 PianoReduction (user task, 2026-11-09).** "Learn To Do It", PianoReduction.pdf pages
78–96; labels VLAD:, DMITRY:, ANYA:, "VLAD & DMITRY:" (2×), "VLAD & DIMITRY:" (3×, a typo in the PDF), "BOTH:" (1×).
Every duet bar goes into both the Vlad and the Dmitry part (the song 4 truth convention Both=Dmitry, Both=Vlad); no
separate "Vlad & Dmitry" or "Both" part. `build_vocal_parts` splits "&" / "+" / "AND" labels (`_singers_of`) and merges
OCR spellings (`_canonical_singers`, Levenshtein ratio >= 0.85), so "VLAD & DIMITRY" probably merges into "VLAD &
DMITRY", but nothing guarantees it: check whether the split "DIMITRY" makes its own part; if so, map split names onto
known single labels with the same fuzzy match. "BOTH" names nobody: a per-song mapping in the PianoReduction `extra`
cell of sheet 6, `singer_groups: {Both: [Vlad, Dmitry]}`, read in `pipeline/engine.py` next to `male_voices` and passed
to `build_vocal_parts`; a grouped label puts the line into each listed singer's part like `_singers_of`. Vlad and Dmitry
are in `male_voices` (treble-8vb); `voice_sounds` has both. Check: `omrbench transcribe anastasia --songs 6 --parts
PianoReduction`; the Voices output has exactly Vlad, Dmitry, Anya (plus a "Voice n" part for bars before the first
label); duet bars in both Vlad and Dmitry; tests for `singer_groups` and the "DIMITRY" spelling; `omrbench bench
anastasia` unchanged for songs 1–5. Sheet 6 `plainText` lists "Vlad & Dmitry, Vlad & Dimitry, Both": after the fix it
needs only "Vlad, Dmitry, Anya" (the user's workbook).

## Round 4 (2026-10-18): ranked by expected gain

Reference: bench `r3-f` = **11 946** actions over all 10 truth songs (Anastasia 1, 2, 4, 4A; Ghost 1a, 4, 5, 11a, 13,
20), outputs reassembled from the work dirs of run `r3` (`scripts/reassemble.py <show> --from r3 --to NEW`). Error
counts: `docs/ERRORS.md`. Gains are estimates in edit-penalty actions; "max" = everything in that category.
User priority (2026-10-18): bar count and bar lengths must match the workbook, because chord symbols, dynamics
and every other mark land on the wrong beat otherwise.

| # | Improvement | Max | Expected | Effort | Needs the user |
|---|---|---|---|---|---|
| R1 | Double barlines + repeat signs by cross-part vote | 1178 | done -439 (Audiveris, vote per book) | medium | no |
| R2 | Anastasia drum set: "sticks" alias + labelled hits only | 975 | done -183 | small | done |
| R3 | Ghost drum kits: rhythm from the vector glyphs | 1487 | done -896 | large | no |
| R4 | Ghost 4 guitar fingerpicking over the slash bars | 967 | done -733 | medium | done |
| R5 | Articulations from the vector glyphs (Ghost); scans: Audiveris marks onto homr notes | 878 | done: scans -56 (`r7-c`), Ghost glyphs -107 (`r7-d`), "sim." -64 (`r7-e`) / -8 (`r7-f`) | medium | no |
| R6 | Anastasia 4 singers: routing + lyrics | ~1500 | part done -557 (labels from the text layer) | large | no |
| R7 | Dynamics + hairpins detector on the scans (#33) | 767 | part: hairpin order -8 (`r8-a`), OCR conf 50 -13 (`r8-b`); detector open | large | no |
| R8 | Ties + slurs from the vector curves (#55) | 579 | part: slur beside a tie -246 (`r9-a2`), vector ties -53 (`r9-a`), sim. slurs -9 (`r9-b`), made-up slurs -15 (`r9-d`), half heads -39 (`r9-e`) | medium | no |
| R9 | Bars in the right place and of the right length | 793 | part: rest-only voices -125 (`r11-a2`), short bars padded -164 (`r11-b`), long bars cut -62 (`r11-c`) | medium | no |
| R10 | Chord symbols: Ghost piano reductions per song, beat snapping (#37) | 216 | -30..-120 | small | yes: Ghost 20 piano |
| R11 | Vocal cues under a singer label ("SAM:") (#41) | ~40 | -20..-40 | small | no |
| R12 | Made-up words on keyboards and piano reductions | ~250 | -50..-100 | small | no |

R1. **Double barlines and repeats by a vote across the parts.** (barlines 846, structure 332.) Every section change
has a light-light barline in the truths, in every part (Anastasia 4: 21 per part); repeats 162 forward / 156 backward.
Audiveris reads many of them on the scans, but taking them per part was rejected (+129, 2026-10-15) when the bar
counts were still off. Now 115 of 126 parts have the right count: collect Audiveris' barline style per output bar
in every part, write a double barline / repeat where at least half the parts with that bar count have one (song
step like `transcribe.share_marks`). Vector pages: the barline type straight from the drawing (two thin strokes
2–4 pt apart = double, dots = repeat; sheet_reader `page_dump.get_barlines`).

R2. **Anastasia 4 drum set (Schlagzeug 787: no output at all; Tamburin 198).** The drum book marks the kit only with
"sticks" (no `Drum Set` alias), and the boxed "Tambourine" at bar 32 switches the rest of the kit into the Tamburin
part. The truth has Tamburin only for the labelled hits (bars 32, 43, 51, ...) and the kit in Schlagzeug.
Measured in memory 2026-10-18: alias `sticks` alone -24 (Drum Set gets bars 72–75 only). Needed: (a) `Drum Set:
{aliases: [sticks]}` in `data/anastasia/show.yaml`; (b) a rule for labels that name a kit instrument inside a kit
passage (applies to the labelled bar / hits only, then back to the kit). Ask the user for the rule.

R3. **Ghost drum kits from the vector drawing (Ghost 4 864, Ghost 5 442, Ghost 20 230 differences).** 16th hi-hat /
snare on one beam plus the foot voice: the truth has 19 notes per bar, the output 8 (values 4x too long 115, wrong
kit position 77). `pipeline/vector.py` already reads slash heads, stems, beams, flags and rests; extend it to the
x / normal drum heads with their staff positions, then map them through `drumkit.yaml`.

R4. **Ghost 4 guitar (971).** From bar 15 the page prints slashes with chord symbols; the truth writes the 16th
fingerpicking pattern of bars 1–4 out over the chords (731 notes). Not on the page. Either the truth keeps slashes
(user decision) or the pipeline realises "sim." fingerpicking over chord symbols (pattern of the last written bar,
moved to each chord's tones; risky). Bars 12–13 (one-bar repeats after the vamp) are not written out: -32 alone.

R5. **Articulations from the vector glyphs (Ghost: missing accent 353, staccato 255, made-up staccato 152).** Tried
2026-10-16 with only Ghost 13 / 20 as truth: +13 (Ghost 20 Reed truth has accents the page lacks). Ghost 4, 5, 11a
add many parts where homr misses them (Ghost 5 Bass / Electric Piano / Drum Kit / Cello about 50 accents + 50
staccatos each). Re-test: marks from the glyphs (sheet_reader `glyph_map.py`) on the output note by bar + x order.

R6. **Anastasia 4 singers (Männer 401, Dmitry 319, Frauen 308, Vlad 201; lyrics 643 actions).** See #49: passages
missing, bars shifted (Männer: 131 notes inside missing bars), lyrics made up / in the wrong voice.

R7. **Dynamics and hairpins on the scans (#33).** Dynamics 505, hairpins 262, almost all missing on Anastasia 4
(Horn, Violine 1, Oboe, Keyboard 1). Plan in #33 (letter templates from the scans, FFT correlation below the staves).

R8. **Ties and slurs from the vector curves (#34, #55).** Ghost ties 281 (Ghost 20 piano 67 missing), slurs 298
(made up 102, missing 145). A curve whose ends sit on two equal pitches is a tie, else a slur.

R9. **Bars in the right place and of the right length.** The count is right in 115 / 126 parts, but an extra bar
early plus a missing bar later still costs 2 + contents (bars 560 actions: Anastasia 1 Klarinette 2 bars 4–5,
Anastasia 4 Tamburin, Ghost 5 Frauen), 182 bars do not add up like the truth bar (barlen 233) and 51 whole-bar rests
still have the wrong length. Ideas: (a) the 11 parts with one extra bar with notes: drop the bar the other parts of
the song have no counterpart for (vote by bar content / rest pattern across parts); (b) the song's `time` row checked
against every written bar: a bar that fills a different length than its time gets its rests fitted or its longest
note cut (rule "each voice fills the bar", CORRECTION_INFORMATION 2); (c) find why `fit_measure_rests` misses 51.

R10. **Chord symbols.** Ghost piano reductions 1a / 4 / 11a keep chord symbols in the truth (11 / 59 / 22), Ghost 20
has none. Checked 2026-11-02: the Ghost 20 PianoReduction PDF prints a chord symbol under almost every bar from
bar 9 to 134 (pages 257-274, text layer "B♭/F", "E♭/B♭", "A♭m7", ...); the user remembers them only around bar 70.
The output has 16 bars with chords (30, 31, 39, 40, 75-87, 119-122, 131), the truth piano none (the truth guitar
has 105). Open: does the Ghost 20 truth piano get the chords (then +R10 helps, about -100), or stays the truth
without them (then the 16 output bars cost 16 and `chord_names` should be off for this book). Turning them on for every Ghost piano reduction: +72 (Ghost 20 +62, Ghost 4 +10), rejected. Ask the user
whether Ghost 20's piano should have them (the PDF prints them?). Guitar: 26 chords at the wrong beat (Ghost 20),
snap to the slash / note under the symbol (#37); with the bars now right this is cheap.

R11. **Vocal cues under a singer label (#41).** Ghost 4 Drums bar 2: the "SAM:" cue line (small notes) is still in.
Extend `drop_play_cues`: a bar whose staff carries a singer label ("SAM:", "MOLLY:") and only small or cue-sized
notes is a cue.

R12. **Made-up words (253).** Anastasia 4 Keyboard 1 (28), Klavierauszug labels, Frauen. Check them one by one
(`results/errors/r3-f/errors.json`, "words: made up") and extend `_cue_text` / `_loose_text`.

Status 2026-10-18 evening: reference `r3-k` = **10 962**. R2 done (alias `sticks`, `kit: true` in the Anastasia show.yaml,
`build_parts`: a label of another percussion instrument inside a kit passage takes only the hits of its bar from the
label's beat; Schlagzeug 787 -> 689, the rest is the kit reading itself, see R3). R4 done (slash glyph `’`,
`continue_patterns`; Ghost 4 Guitar 967 -> ~260; left: hollow half / whole slashes `|` at 58–61, 74–79 need durations,
and the %-bars 12–13 after the vamp repeat are not written out). Bar count right in 125 of 126 parts (R9 count part:
no guessed pickup, courtesy copies, bars past the Audiveris stacks; left: Anastasia 4 Keyboard 1, last system).

## From the expert review of the music rules (2026-10-28)

The expert checked `CORRECTION_INFORMATION.md` ("Music rule information" and the conventions); the rules there are
updated. New items, gains in edit-penalty actions against `r3-k` (10 962), estimated from `docs/ERRORS.md`:

| # | Improvement | Max | Expected | Effort | Needs the user |
|---|---|---|---|---|---|
| R13 | "sim." and %-bars per show: Anastasia keeps "sim." / % as printed | ? | -10..-60 | small | Anastasia truths being updated |
| R14 | Clef sanity: no clef changes in wind / string parts (except cello), clef by instrument | ~40 clefs + notes under them | -20..-60 | small | no |
| R15 | Range check with neighbour-staff test for single far-off notes | 246 + part of 192 | -30..-80 | medium | no |
| R16 | Hairpins longer than 2 bars kept (`max_wedge_bars`) | 262 | 0..-15 (may cost) | tiny | no |
| R17 | Two voices on one staff: marks below go to the lower voice | ~100 | -20..-50 | medium (with R5) | no |
| R18 | Token lists: dynamics pf / rf / rfz / fz / sffz, chord kinds add11 / add13 / ... | small | 0..-10 | tiny | no |
| R19 | Octave lines: 15va / 15vb, lines below the notes, "ad lib." | ? | 0..-30 | medium | no |

R13. **"sim." and %-bars per show (expert, CORRECTION_INFORMATION K2.4).** Checked: not done. `bars.apply_sim`
copies the pattern bar's articulations onto the following bars in every show, `bars.drop_words` drops "sim."
everywhere, and `assemble.apply_repeats` writes %-bars out everywhere. Ghost wants exactly that; Anastasia wants
"sim." kept with the following bars unmarked, and the % signs kept (MusicXML `<measure-repeat>`, check that the
metric scores them). Add a show.yaml key (e.g. `repeats: write_out | keep`) and skip the three steps for `keep`.
The user is updating the Anastasia truths (`docs/TRUTH_DEVIATIONS.md`); measure after that, before it the change
comes out worse.

R14. **Clef sanity per instrument (expert 13.1 / 13.2).** Made-up clefs in non-keyboard parts (Anastasia 1
Klarinette 2 bar 6 `F4`, Pauken bar 9 `G2`, Ghost 11a Cello `G2` instead of `F4`, ...) shift every note after them
until the next clef. Rule: in wind and string parts except cello, drop clef changes; the starting clef comes from
the instrument (treble for alto / tenor sax, bass for baritone sax, bass for timpani). Keyboards keep their
changes (119 clef errors there are a different problem). Gain: the clefs plus the wrongly pitched notes in the
passages after them.

R15. **Range check with the corrected ranges (expert 14, #27, #48).** Per instrument, notes far outside the written
range (table in CORRECTION_INFORMATION 14, guitar to E6, theatre soprano to A3 / alto to E3) are suspect. A whole
passage off by one octave: missed 8va / clef. A single far-off note: first check whether the staff above or below
has that pitch at the same onset (the crop took a neighbour's note): then drop it; else flag (or use the Audiveris
head position, #48). Targets "wrong by more than a third" (246) and part of "note made up" (192, Anastasia 4
Keyboard 1, Klarinette 2). Also a guard for double flats / sharps: plausible only in keys with 4+ accidentals of
that kind (expert 4.5), so never "fix" them there.

R16. **Hairpins over 2 bars (expert K4.6).** `max_wedge_bars: 2` drops longer hairpins as misread pairings. The
2-bar rule is no fixed rule. Truth hairpins are mostly 0–1 bars, so the gain is small and dropping fewer may add
made-up hairpins: measure `max_wedge_bars: 4` and `0`, keep only if the acceptance rule passes.

R17. **Marks of two voices on one staff (expert 12.2).** With two voices, articulations and fermatas of the upper
voice sit above the staff, of the lower voice below. Assign a mark by its side of the staff (needs the mark's y:
vector glyphs on Ghost, Audiveris on scans). Targets Ghost drum kits (hands up / feet down: accents at the wrong
beat 35 on Ghost 4 Drum Kit, made-up staccatos on drums 56), keyboard parts with two voices, fermatas on the
lower voice. Best done together with R5.

R18. **Token lists (expert 11.3, 18.1).** `ocr.DYNAMIC` knows p..fff, mp, mf, sfz, sf, fp, sfp: add pf, rf, rfz,
fz, sffz. `chords.KINDS` lacks add11, add13, m9, maj9, 7sus4, 7b9 / 7#9 / 7#11: a chord with such a suffix does
not parse and is lost. Near zero effort; gain small (Ghost chords 216, most are placement).

R19. **Octave lines (expert 15.1).** 15va / 15vb mean two octaves like 15ma / 15mb; a line may sit below the notes
it covers (8vb under the staff); "8va ad lib." means optional. Today only keyboard patch labels ("loco & 8va")
become octave sections. Read the octave-line texts (OCR / PDF text layer: "8va", "8vb", "15ma", "15va", "15vb",
"loco") and apply them to the span; "8va ad lib." counts as 8va (the truth writes the notes an octave up, user
2026-10-28).

## From the user's work in MuseScore (2026-11-01)

What still costs hand work after opening the output in MuseScore. Gains in edit-penalty actions against `r3-k`
(10 962); counts measured on the current `results/<show>/<song>/` outputs of the 10 truth songs. R22–R24 change
nothing in the metric (it compares the printed text) but save the user work in every song.

| # | Improvement | Max | Expected | Effort | Needs the user |
|---|---|---|---|---|---|
| R20 | Duplicate slurs / ties removed | 2 + ties | done -2 (estimate was a counting bug) | tiny | no |
| R21 | `plainText`: shared lyrics only in the first voice | ~150 | done: -93 (`r10-a`) | small | yes: song 2 truth |
| R22 | "pizz." / "arco" as playing techniques (playback) | 0 | 0 (about 40 words per song to re-enter) | tiny | no |
| R23 | Real instruments instead of piano (playback, names) | 0 | 0 (every part to re-assign) | small | no |
| R24 | "gedämpft" / "offen" as mute on / off (playback) | 0 | 0 | tiny | no |
| R25 | Duplicate dynamics / words at the same spot removed | 26 | -10..-26 | tiny | no |
| R26 | `plainArticulation` = only the marks another part already has are dropped | metric: ~2 465 hidden | song 3 Violin 2 / Reed 2: about -550 of +663 (against scoring them in full) | medium | yes: flags of songs 1/2/4/4A, metric change |

R20. **Duplicate slurs and ties (user 2026-11-01).** Two slurs (or ties) that join exactly the same two notes: keep
one. Measured on the outputs: 454 duplicate slurs in the truth songs (Anastasia 4 186, Ghost 20 125, Ghost 13 61,
Ghost 4 36, Anastasia 2 21, Anastasia 1 12, Ghost 1a 10, Anastasia 4A 2, Ghost 11a 1), 18 duplicate ties; MuseScore
keeps both, and the metric charges every extra one (its items are multisets). They mostly come from merging two
sources (homr crop slurs + `slurs_to_ties` / chord ties copied from Audiveris). Fix: a last pass in
`assemble.write_score` (or `musicxml.write`): pair every slur start with its stop by number, drop a pair whose start
and stop notes equal another pair's; ties: drop a second `<tied type="start">` / `<tie>` on the same note. Same pass on
a slur that duplicates a tie on the same two notes (the tie wins, music rule: a slur joins different pitches).

R21. **`plainText` voices: shared lyrics only in the first voice (user 2026-11-01).** Workbook column `plainText`
(PianoReduction rows of all Anastasia songs: every singer label and Frauen, Männer, Women, Men; entered 2026-11-01).
Rule: when several `plainText` voices sing the same text in the same rhythm at the same time, only the first voice in
score order keeps the lyrics; the others keep the notes without lyrics. Match per bar run: same onset, same duration,
same syllable text (case- and quote-insensitive) for every lyric note of the run; partial matches keep both. Runs on
the Voices output after the label routing (`pipeline/vocal.py`), before the combined file is written. The truth is not
changed (user 2026-11-01): the Anastasia 4 truth already follows the rule (3 duplicate syllables of 679; the output
has 135), the song 2 truth keeps 13 (output 12), so song 2 gets about +12 until its truth is updated. Code: read the
column in `project.py` (HEADER, a `plain_row`-like label resolution into `meta["plain_text"]`).

R22. **"pizz." / "arco" as playing techniques (user 2026-11-01).** Now they are plain staff text, so playback stays
arco and the user deletes and re-enters each one. Tested 2026-11-01 with MuseScore 4 (`to_mscz` round trip): a
`<direction>` with `<words>pizz.</words>` plus `<sound pizzicato="yes"/>` imports as a `PlayTechAnnotation`
(pizzicato), "arco" with `<sound pizzicato="no"/>` as the normal technique; words without `<sound>` stay
`StaffText`. This is also how MuseScore exports the truths. Fix: when a direction's words match `^pizz` / `^arco`, add
the `<sound>` after its `<direction-type>` (one place: the writer, for all parts). Related: #51, #54 (missing arco).

R23. **Instruments that MuseScore knows (user 2026-11-01; also #18).** The output `<score-part>` carries only a
`<part-name>`, so MuseScore imports every part as a piano (tested: no `<score-instrument>` -> `keyboard.piano.grand`).
Tested 2026-11-01: `<score-instrument><instrument-name>` + `<instrument-sound>` (MusicXML sound id, as in the
truth exports, e.g. `strings.cello`) selects the instrument, but the instrument name must be unambiguous: "Bass"
with `pluck.bass.electric` became `voice.bass`; "Electric Bass" / "Contrabass" were right. Fix: a `sound:` field per
instrument in the `show.yaml` library (with a default table for the usual names: violin, cello, contrabass vs
electric bass per show, flute, piccolo, oboe, clarinet in Bb, bassoon, horn, trumpet in Bb, trombone, timpani, drum
set, glockenspiel, xylophone, piano, voices soprano / alto / tenor / bass by the singer's clef), written as
`<score-instrument>` with MuseScore's instrument name; `<part-name>` keeps the book's name. Drum parts already write
their kit instruments (`drumkit.py`); give them `drum.group.set`. Doubling parts with instrument changes keep the first
instrument only (MuseScore ignores mid-part instrument changes on import); Anastasia splits them per instrument anyway.

R24. **"gedämpft" / "offen" with playback (found 2026-11-01).** The truth exports carry `<sound><play><mute>on</mute>`
(and `off` for "offen") on these words; add it the same way as R22. Brass playback then switches to the mute.

R25. **Duplicate dynamics / words at the same position.** 26 bars of the outputs have the same `<direction>` twice
(PianoReduction mostly; Ghost 4 Bass "mp twice" is a known truth case). Drop exact duplicates at the same onset and
staff in the same last pass as R20.

R26. **`plainArticulation` = shared marks dropped, unique marks kept (user 2026-11-02).** The flag does not mean "no
marks". The arranger (or truth writer) leaves out a mark that another instrument already has at the same time, and
keeps every mark only this part has. It works like `plainText`, but per mark. Measured 2026-11-02 on outputs rebuilt
without the flag (`x-noplain`, scratch run, `project.plain_row` patched out; no code change):
- **Only song 3 really drops marks.** Violine 2 (504 notes) keeps 10 of the ~350 marks the PDF has, Klarinette 2 keeps
  24 of ~340, Flöte 2 none. In songs 1, 2, 4 and 4A the flagged truth parts keep almost everything (song 4 Violine 2
  keeps 462 of the output's 519 marks, Violoncello 433 of 529), so their flags no longer match the truths.
- **The rule fits song 3.** A mark is "shared" if another truth part has the same mark (category, token) on the same
  bar and onset. Violine 2: shared marks 4 kept / ~330 dropped, unique ones 1 kept / 17 dropped. Klarinette 2: shared
  18 kept / ~305 dropped, unique 5 kept / 11 dropped. Most unique marks the truth drops may be misreads (no other part
  has them). A per-bar view says the same: in bars where Klarinette 2 has its own material (no other part with the
  same pitches or rhythm) it keeps 8 of 9 marks; in doubled bars it keeps 14 of 328.
- **The metric hides this now.** The flag strips marks in output and truth, so the parts score no mark costs at all.
  Bench with the flag off: Anastasia +2 465 (song 3 Violin 2 +345, Reed 2 +318; song 4 Trumpet +289, Trombone +246,
  Violin 2 +186, Cello +176, Keyboard 2 +172, Reed 3 +123, Bass +119, Reed 2 +117; 4A Violin 2 +37).
Plan:
1. Metric: score the truth part as it is (no stripping); the output is judged on what it prints.
2. Pipeline, song level (`transcribe.share_marks`, which already sees every part of a song): in a flagged part drop a
   dynamic, hairpin, articulation, slur or fermata when a part without the flag has the same one on the same bar and
   onset (slurs / hairpins: same start and stop onset); keep the rest. Expressive words the same way. Compare by
   concert onset, not pitch, so transposing parts match.
3. Which parts carry the flag: song 3 Violine 2 / Klarinette 2 / Flöte 2. The flags of songs 1, 2, 4, 4A were removed
   (user 2026-11-09); the new reference `r13-ref` scores those parts in full.
Expected: song 3 Violin 2 / Reed 2 recover most of their +663 against the "flag off" scoring (they keep ~5 % of marks
and the rule drops ~95 % of the shared ones); the other flagged parts are scored in full (their marks are mostly read
right already). The new reference rises by about the hidden cost, so this is measured as a metric change first, then
the pipeline change against the new reference.

Done 2026-11-01 (data only, no pipeline change): workbook column `plain` renamed to `plainArticulation` in both shows
(`project.py` reads the new name); Anastasia song 3 (no truth) has no `plainArticulation` cells any more, later
Anastasia songs get none (user); column `plainText` added (R21, read since `r10-a`); Anastasia 4 truth: 52 accents
corrected to marcatos (`TRUTH_DEVIATIONS.md` section 3). Re-benched `r3-k` outputs: `r4-t` **11 026** (+64, the truth fix
alone). Metric (user-approved 2026-11-01): category `playtech` (every `<sound>` playing technique: pizz / arco, mute /
open, `other-play` types, 1 action each) and `instrument` (the part's `<instrument-sound>` differs from the truth
part's = 1; parts whose truth has none are not scored). New reference `r4-ref` **11 259** (+233).

## From the Anastasia truth review (2026-11-02)

All Anastasia truths (songs 1, 2, 3, 4, 4A) against the reference outputs `r12-a` (Anastasia **8 134**, all shows
11 998). Every scored part re-aligned bar by bar like `metrics/edits.py`, the left-over output-only / truth-only items
counted per category, token and bar (scratch script, no code change), the big patterns checked on the PDF pages.
Where the Anastasia cost sits: notes 2 583, articulations 1 547, dynamics 618, words 444, barlines 424, slurs 392,
lyrics 358, bars 347, hairpins 345, ties 256, tremolos 221, playtech 112, structure (repeats) 111. Song 3's sparse
truth parts (Bass, Trombone, Trumpet, Keyboard 2) and the known singer routing (R6), dynamics / hairpins (R7) are
left out below. Gains in edit-penalty actions against `r12-a`.

| # | Improvement | Max | Expected | Effort | Needs the user |
|---|---|---|---|---|---|
| R27 | Barline / repeat vote: missed repeat starts, marks at system ends, cuts | 535 | -120..-250 | medium | yes: 5 truth bars (about 115 actions) |
| R28 | Anastasia 4 drum kit lost to Tamburin after "tamb." / "pick up tamb." | ~140 | -100..-130 | small | no |
| R29 | Drum slash bars after "etc." written out (scans) | ~170 | -60..-120 | medium | no |
| R30 | Instrument-switch labels of split books dropped as words | ~60 | -35..-50 | small | no |
| R31 | Marcato (^) read as accent (>) on the scans | 70 | -20..-35 | medium | no |
| R32 | Semitone errors in the bar before a key change | 66 | -10..-30 | small (check first) | no |
| R33 | "(BASS SOLO:)" over a treble staff: male voice, octave down | ~15 | -1..-5 (one octave fix per passage in MuseScore) | small | yes: which octave |

R27. **Barline and repeat vote (barlines 424 + structure 111).** Almost all of it is about 20 song-level decisions of
`musicxml.share_barlines`, each one repeated in every part (20–28 actions each):
- Repeat starts are missed: Audiveris reads backward repeats (Anastasia 4: 2–3 per book) far more often than forward
  ones (0–2). Anastasia 4 bar 1 (vamp 1–2, the end repeat at 2 is in the output) misses its start in all 28 parts;
  4 bars 158–159 (printed 153–154, "Safety") miss both (56); song 2 bar 73 (printed 72A, a one-bar repeat) has the
  start but not the end (20). Plan: pair the kept marks: a kept repeat end without a start since the song start or
  the previous end gets the start with the most votes in between (any count), else bar 1; a kept start without an
  end gets the end with the most votes before the next start (else the same bar). About -76..-104.
- Double barlines missed in every part: Anastasia 4 bars 38, 138, 160, 164, 182, 186 (168), song 1 bar 5 (22).
  Song 1 bar 5 and Anastasia 4 160 / 164 (printed 155 / 159) end a system on the page; the others not checked. Next
  step: log the votes per mark (books with the song's bar count that have it / all voting books) to see whether a
  lower threshold (1/3) or a system-end bonus finds them without adding marks the truth lacks.
- Cuts: Anastasia 1 Violin 1 prints the double barline after 11 and then "[to] 14"; the truth (bars 12–13 kept as
  bars) puts it on 13, the bar before the jump target, and so do the other books (44 = 22 parts × 2). Rule: a double
  barline right before a "[to] N" cut goes to bar N-1 (CORRECTION_INFORMATION: skipped bars stay as empty bars).
- Parts whose bar count differs from the song's (Anastasia 3 Violin 1, PianoReduction: 246 / 245) lose every mark
  (about 22); fixing the extra bar (R9 (a)) gives them back.
- Truth candidates (`docs/TRUTH_DEVIATIONS.md`, user): the page prints a double barline the truth lacks in Anastasia
  1 bar 3 (before the key change at 4; 22 parts), song 2 bars 29 and 65 (65 before the key change at 66; 19 parts
  each), song 3 bar 229 (before "Slower" 230; 20 parts) and probably song 3 bar 66 (key change at 67, page not
  checked; 16 parts). The output has them; about 115 actions are truth gaps.

R28. **Anastasia 4 kit routed into Tamburin.** Schlagzeug has 48 truth bars with notes where the output kit has none
(290 actions). Bars 179–186 and 199–211 (printed 174–181 / 194–206, drum book page 18: "tamb." at 178, "pick up
tamb." at 197) are written kit bars, and the Tamburin output carries them instead (8–11 notes per bar against a
truth with 0–4). The R2 rule (a percussion label inside a kit passage takes only the hits of its bar) does not catch
these labels: check `build_parts` for "pick up tamb." (a TRUTH_DEVIATIONS convention word, no label of its own in
the truth) and a "tamb." label at the start of a system / after the two-staff system 174–177 (Timpani + kit).
Schlagzeug notes there ~116, Tamburin extra bars and marks ~20.

R29. **Drum slash bars after "etc." (scans).** The Anastasia 4 drum book prints one groove bar, then "etc." and
slash bars (page 13: 33 groove, 34–38 slashes, "stop"; page 14: 44 groove, 45, 46, 48, 52–54 slashes). The truth
writes the groove out (6–9 notes per bar), the output has empty bars. 10 bars checked (~70 actions); the other empty
kit bars without R28 (80–85, 98, 105, 113, 115, 162–163, 31, 44, 50: ~100) are not checked on the page (31, 44 and
50 are written notes the reader missed). Plan: like `continue_patterns` (Ghost 4 guitar, R4): a bar under an "etc."
/ "sim." word with no notes read, up to the next written bar or "stop", gets the last written bar of that staff
copied. Scans have no slash reader (#7), so the trigger is the word plus an empty bar (no rest glyph either).
Anastasia keeps "sim." / % as printed (R13), but these truths write the slash bars out.

R30. **Instrument labels of split books as words.** After a book is split by instrument, the switch label stays as a
word in the part: "timpani" 8 (Pauken), "tamb." / "tamb" 14, "bell tree" 5, "triangle" 5, "glock" 4, "glock - soft
mallets" 2, "crotales" 2, "castanets" 3, "flute" 3, "clarinet" 2, "to oboe" 2, about 50; the truths have none.
Drop a word that names an instrument (or alias, or "to <instrument>") of the book's library once it has served the
split. Same pass: "= 160 (in 3)" written as part text in 8 parts of song 3 (the system tempo already has it).

R31. **Marcato read as accent.** 44 output accents sit where the truth has a marcato (Anastasia 4 Horn 18, Keyboard 1
12, Oboe 6; the truth was corrected to marcatos 2026-11-01), 26 accents where it has a tenuto. Audiveris reads 4
marcatos in the Horn book (46 accents), homr none. Check the mark's shape on the crop (^ is taller than wide and
open at the bottom, > is wider than tall and open to the left) before writing an accent.

R32. **Semitone errors near key changes.** 309 notes are off by one or two semitones (same onset and duration);
52 of them in the bar before a key change and 14 in the change bar (Anastasia 4 Keyboard 1 bars 31–32: 28, the
right hand a semitone off in both directions). Not checked on the page: either the courtesy key signature at a
system end is read as the bar's key, or `respell_key` uses the new key one bar early. Look at Anastasia 4 Keyboard 1
31–32 first; the rest of the 309 is spread thin (Klarinette 2 35, Violine 2 29, Violine 1 21).

R33. **"(BASS SOLO:)" over a treble staff.** Anastasia 4 bars 65–71, PianoReduction page 43: the label "(BASS
SOLO:)" stands over a plain treble-clef staff. The label parser makes a voice "Solo" (workbook: Solo=Männer) at the
written pitch (bar 66 starts C5). The truth has it in Männer (treble-8vb clef) at C3, two octaves below the output;
rhythm and pitch classes match 22 / 22. "BASS" in the label is not used to mark a male voice (8vb). The metric
already folds this into one octave section (+4 notes, 7 lyrics, 2 instrument changes in these bars), so the gain is
small, but the user moves the passage by hand. Plan: a singer label with BASS / BARITONE / TENOR (or a mapped male
group) writes treble-clef notes into a treble-8vb clef one octave down. Whether the truth's second octave is right
(a bass sounding C3 from a printed C5) is a user question.

Notes on older items from this review: #36 single tremolos: now 214 missing (output 9): Anastasia 3 Violin 2 39,
Violin 1 30, Drums 24, Keyboard 2 23, Anastasia 4 Drums 20, Cello 16, Violin 1 13 (half / dotted-half notes with
three strokes on the stem). #54 "arco" / "pizz.": since `playtech` is scored a missing word costs 2 (word +
technique): truth-only "arco" 42 / "pizz." 33 words plus 40 / 33 techniques, about 150 actions (Anastasia 4 Violin 1
44, Cello 40, Violin 2 30); the Tesseract words measured -2 before `playtech` existed, re-measure.

Round 5 results (reassembled from `r3`: `scripts/reassemble.py <show> --from r3 --to ID`,
`omrbench bench <show> --run ID --bench-id ID`; `r4-0` reproduces `r4-ref` exactly):
- R22 + R24 accepted, `r4-b` **11 229** (-30): `musicxml.play_techniques` at the end of `write_score` gives "pizz." /
  "arco" `<sound pizzicato>` and "gedämpft" / "offen" `<play><mute>`; only the bare word (keyboard patch labels
  "Pizz. Strings [both hands]" got a technique and cost +5 in a first try, `r4-a` -25). Left: most truth techniques
  have no word in the output at all (#54); Ghost has 12 techniques in its truths.
- R23 accepted, `r4-e` **11 115** (-114 against `r4-b`): `musicxml.set_sounds` writes a `<score-instrument>` with the
  MusicXML sound id as both `<instrument-name>` and `<instrument-sound>` (with a name MuseScore knows, "Bass" or
  "Voice", the part name wins and gives voice / piano; tested on all 27 ids). Ids: `show.yaml` (gitignored data)
  `parts: <book>: {sound}` (one-part outputs), instrument library `sound` (split parts by name; the first instrument
  of a row unless the book has its own: Ghost Reed stays clarinet as in the truths), PianoReduction `voice_sounds`
  per singer label (mixed groups: women's voice). Unpitched percussion got the truths' ids too (not scored: their
  truth parts carry none). Left: Ghost 5 Utility (output parts "Part 0" + "Utility", 1).
- R20 accepted, `r4-g` **11 113** (-2): `musicxml.drop_duplicate_curves` after `play_techniques`. The 454 duplicate
  slurs counted on 2026-11-01 were a bug in the count (pairs keyed by `id()` of lxml proxies, which Python reuses);
  keyed by note position the outputs hold 2. The first version of the pass had the same bug and removed real slurs.
- Metric fix: a truth part scored against overlaid output parts (singers: Men + Voice 1 + All) counted every barline /
  repeat once per output part; now once per bar (like clef / key / time). Reference `r4-g2` **11 105** (-8).
- R1 accepted, `r4-j` **10 666** (-439 against `r4-g2`): `bars.part_bars` keeps Audiveris' (and homr's) barline marks
  per bar (`Bar.barlines`: double, repeat-start, repeat-end; a final barline inside the song counts as double),
  `write_score` writes them, `transcribe.share_marks` -> `musicxml.share_barlines` votes: one vote per book (a drum
  book or a piano reduction's singers are many parts but one page), a mark at least half of the books with the song's
  bar count have goes into every part with that count, all other marks are removed. First try with one vote per
  part: +2 (the 17 singer parts and 9 drum parts have no marks of their own and outvoted the rest). Found on the way:
  the workbook's `bars` is text, so `share_fermatas` never had voters when a song has a `bars` row (measured next).
  Left: Ghost 20 +4 in every part (a mark the truth lacks or at the wrong bar); vector barline types not read yet.
- Fermata vote with the `bars` row as a number: accepted, `r4-k` **10 662** (-4).
- R3 accepted, `r5-b` **9 766** (-896 against `r4-k`; Ghost 4 Drums 818 -> 86, Ghost 20 Drums 232 -> 69):
  `vector.read_drum_page` reads the MaestroPercussion heads (black / x, ⊗ half and whole; cue-size heads skipped)
  with their staff position, stem up = voice 1 / down = voice 2, values from beams / flags / dots (shared
  `_stem_value` with the slash reader), rests by height, accents and ties (curve above = voice 1); a bar is kept
  only if every head has a value and both voices have the same length. `assemble.slash_bar` writes them as
  unpitched chords with a `<backup>`, `place_slashes` now runs on drum books too (`drumkit.apply` maps the
  positions as before). Without ties `r5-a` -886. Left: Ghost 5 Drums +5 (bar 3 lands in bar 2: the reader bars of
  the 2/4 system are offset; toms at D5 snap to the snare C5 because the kit comes from Ghost 20 only; slash bars
  and tremolos in drum books not read); Ghost 4 13 ties and 29 articulations (bars not read: whole / half ⊗).
- R6 (part) accepted, `r6-a` **13 178** (-557 against `r6-ref` 13 735; Anastasia 3 PianoReduction -243 / +7,
  Anastasia 4 -241, Ghost 4 -80): on vector pages `assemble._place_vocal_text` adds the singer labels of the PDF text
  layer that Audiveris did not read (`text.missed_labels`: "NAME:" lines via `vector.read_lines(left=True)`, none
  within 2 / 3 interlines of an OCR label or dialogue line, no prose after the colon). Anastasia 4 Dmitry 295 -> 135
  ("DMITRY: (cont.)" at 101, "BOTH:" 113 / 176, "DMITRY:" 164 / 199), Vlad 177 -> 134. Left: the new correct labels
  "Solo" (Männer 65-71) and "Black Marketeer #1" (Frauen 138-146) are not in the workbook `truth` cell of Anastasia 4
  (user: add `Solo=Männer, Black Marketeer #1=Frauen, Black Marketeer #3=Frauen`); `_canonical_singers` merges
  "BLACK MARKETEER #1/#2/#3" into one (Levenshtein); keeping numbered labels apart was rejected, `r6-b` -7 with
  one part +20 (the workbook maps only #2, so #3 / #1 bars count as missing until the cell is extended); finale 199-211 "+DMITRY & VLAD:" and the men
  (truth puts Dmitry / Vlad with the men), Frauen chords 57-64, lyrics verse 2.
- Workbook (2026-11-02): Anastasia 3 truth linked (singer labels by note match: Voice 1 / Voice 2 / All = Frauen +
  Männer, All Women = Frauen; Violin 2 and Reed 2 `plainArticulation`, user; the leftover part "PianoReduction - Voices
  – All" is not mapped). Its work dirs are in run `s3` (rb.sh: song 3 from `s3`, the rest from `r3`); `r6-ref` 13 735
  = `r5-b` 9 766 + song 3. Anastasia 4 cell extended by `Solo=Männer, Black Marketeer #1=Frauen` (note match 6 / 22
  octave-off and 50 / 50; #3 is not in the output): the `r6-a` outputs score `r6-a3` **13 060** (-118). Anastasia 5
  "In My Dreams" sheet added (pages from the page headers, Reed 1 Flute + English Horn, library entry in F); its
  time / key / bars rows come from the first transcription.
- R5 / Audiveris marks on scans accepted, `r7-c` **13 004** (-56 against `r6-a3`): homr misses articulations below
  the staff (Anastasia 3 Cello 8-13: accents under stem-up notes), Audiveris has them. On scanned pages
  `bars.copy_marks` (next to `copy_ties` in `assemble.build_plans`) puts Audiveris' accent / marcato / tenuto onto
  homr notes with the same onset, staff and pitch that carry no mark. Variants: all kinds on every page `r7-a` -4
  (Audiveris staccatos are made-up dots: Keyboard 1 / PianoReduction +13 each), no staccato `r7-b` -45 but FAIL
  (vector PianoReductions +10 / +4: there Audiveris makes marks up). Gains Cello -35, Keyboard 1 -27, Reed 3 -19;
  worse Anastasia 3 Bass +27, Keyboard 2 +17, Trumpet / Trombone +4: the page prints the marks, the truth lacks them
  (TRUTH_DEVIATIONS). Left: Anastasia 3 made-up marks are mostly those sparse truths (Bass, Trombone, Trumpet,
  Keyboard 2: about 530 of 870 articulation differences); Ghost glyph marks (R5 proper) not done.
- R5 / Ghost glyph marks accepted, `r7-d` **12 897** (-107 against `r7-c`, no part worse; Ghost 13 Cello -17,
  20 Utility -12, 20 PianoReduction -9): `vector.read_marks` reads the EngraverFontSet heads (œ Ï ú w Î, cue size
  skipped) per staff and bar, one column per x, and the marks centred on a head (or starting with it): ">" accent,
  "^" marcato, "." staccato (a dot beside the head is an augmentation dot), "-" tenuto (between the head and the
  staff outside it: a ledger line), "˘" / "ﬂ" / "ß" accent + staccato above / below (ß is sfz elsewhere: only
  centred on a head). A mark goes to the head nearest to it vertically, not by the nearest staff (marks below a
  low bass note sit closer to the next staff). `assemble.place_marks` replaces the readers' marks where the staff's
  note onsets in the chosen bar equal the head columns. Not marks: "≥" / "≤" down- / up-bow, "u" fermata below,
  "Å" 16th rest, "¾" tremolo. Left: Ghost 5 Bass / Cello / PianoReduction / Utility (about 300): the truths write
  the marks out after "sim." across the 2/4 -> 4/4 change, but Audiveris does not read that "sim." (PDF text
  layer, italic) and `bars.apply_sim` stops where the rhythm changes; Ghost 5 Bass bars 1-7 misaligned; drum kits;
  two voices on one staff (R17, marks go to the first note of the onset).
- R5 / "sim." from the text layer accepted, `r7-e` **12 833** (-64 against `r7-d`; Ghost 5 Utility -56, Bass -8):
  on vector pages `assemble.place_sim` puts every "sim." line of the PDF text layer (`vector.read_lines`) into the
  bar it is printed under (staff right above it), so `bars.apply_sim` sees the word Audiveris missed. Anastasia's
  vector PianoReductions unchanged (R13 still open).
- R5 / "sim." over other bar lengths accepted, `r7-f` **12 825** (-8 against `r7-e`, Ghost 5 Cello): when every
  note of the pattern bar has the same value and the same marks, `bars.apply_sim` goes on over following bars that
  hold only notes of that value, whatever their count (2/4 -> 4/4 under one "sim."). Left: Ghost 5 Bass (bars 1-7
  of the output misaligned: an empty bar breaks the run), Ghost 5 PianoReduction / Guitar / Drums.
- R7 / hairpin order accepted, `r8-a` **12 817** (-8 against `r7-f`; Anastasia 4 Violin 1 -10, worst Anastasia 3
  Cello +3): `bars.add_direction` put every direction first in the bar, so copying a bar's Audiveris directions onto
  a homr bar reversed them; a hairpin inside one bar then had its stop before its start and `limit_wedges` dropped
  both as unpaired (Anastasia 4 Violin 1: Audiveris 21 hairpins of 0-1 bars, output 8). Now it inserts after the
  directions already at the front (`vocal` adds start then stop). Output hairpins 153 -> 221 over Anastasia; most
  of the new ones are made up / at the wrong beat where Audiveris misreads, so the gain is small. Left: about 300
  hairpins and 330 dynamics Audiveris never sees on the scans (detector, #33).
- R7 / OCR dynamics at confidence 50 accepted, `r8-b` **12 804** (-13 against `r8-a`; Anastasia 3 Violin 1 -6, worst
  +1): `ocr.supplement` keeps a word that is exactly a dynamic token from Tesseract confidence 50 (was 70). The
  cached OCR of Anastasia 3 / 4 has about 90 more such tokens at 50-69 (mf 44, p 21, f 19), most are already
  covered by an Audiveris text or filtered by height. Confidence 40: `r8-c` -11 (two more made-up ones).
- R16 / `max_wedge_bars` 4 (with the hairpin order fixed) rejected, `r8-d` measured +2 against `r8-b` (Anastasia 3
  PianoReduction +3): Audiveris' longer pairings on the scans are mostly misreads; 2 stays. State after `r8-b`
  (Anastasia): hairpins missing 273, made up 60, wrong beat 20; dynamics missing 327, made up 254 (Anastasia 3
  Cello 31 / Kontrabass 22 / Keyboard 2 20 against truths with 10 / 11 / 17 dynamics: check whether those truths
  are sparse). The detector (#33) is still the only way to the missing ones.
- R8 / slur beside a tie accepted, `r9-a2` **12 558** (-246 against `r8-b`; Anastasia 3 Violin 1 -33, Trombone -26,
  Reed 1 -25, Trumpet -24, worst Anastasia 3 PianoReduction +1): homr writes a slur and a tie on the same two notes of
  one pitch (the scans print one curve); `musicxml.slurs_to_ties` skipped such a slur, now it drops it (the tie stays).
  Left: Anastasia 3 made-up slurs (432 in `r8-b`, many on grace notes homr reads as 16ths: Violin 1 bar 26).
- R8 / ties from the vector curves accepted, `r9-a` **12 505** (-53 against `r9-a2`; Ghost 20 PianoReduction -43,
  worst Ghost 13 Bass +2): `vector.read_marks` also pairs the flat filled curves (`_ties`) of a staff with the head
  columns: a curve from a head to a head at the same height in the next column, or off the system end from the last
  column (#39), is a tie; `assemble.place_marks` puts the tie start on the k-th highest note of that onset (only when
  the onset has as many notes as the column heads), `musicxml.close_ties` gives every tie start its stop on the
  same pitch in the next chord (also over system breaks). Ghost 20 ties 145 -> 100. Left: Finale slurs (curves
  between different heads) not read yet; Anastasia's vector PianoReductions use Petrucci (heads œ ˙ w), not read.
- R8 / slurs after "sim." accepted, `r9-b` **12 496** (-9 against `r9-a`, Ghost 4 Guitar): `bars.apply_sim` also
  copies the pattern bar's slurs when each of them ends inside it (fingerpicking pattern: one slur per bar in the
  truth), onto bars without a slur of their own. Left: Ghost 4 Guitar bars 12-13 read as a rest bar and an empty
  bar (notes, not slurs) end the run, about 50 slurs.
- R8 / made-up slurs on vector pages accepted, `r9-d` **12 481** (-15 against `r9-b`; Ghost 20 PianoReduction -13,
  worst Ghost 4 PianoReduction +1): `vector.read_marks` marks every head column where a filled curve starts
  (`Event.curved`; a curve narrower than 2 spaces is a brace), `assemble.place_marks` drops the slur starts of an
  onset whose column has none (Audiveris pairs a tie end with the next note as a slur: Ghost 20 left hand Bb1-Bb2),
  `musicxml.drop_duplicate_curves` then drops the slur stops left without a start. First try with curves under 5
  spaces high only: `r9-c` +8 (Ghost 4 Guitar +11: a one-bar slur is 11 spaces high). Left: adding the missing
  slurs from the curves (Ghost missing about 140, 75 of them Ghost 4 Guitar notes, see above).
- R8 / half heads "˙" accepted, `r9-e` **12 442** (-39 against `r9-d`; Ghost 20 Utility -13, Ghost 1a Guitar -5, no
  part worse): `vector.HEADS` lacked the EngraverFontSet half head "˙" (138 on the Ghost 20 pages), so bars with a
  half note had one head column too few and `place_marks` skipped them (marks, ties, slur check). Measured together
  with reading Petrucci (Anastasia's vector PianoReductions, heads œ ˙ w): no change on Anastasia, left out.
  Left: why Petrucci heads change nothing on Anastasia (read_marks finds them: Anastasia 3 page 2, 156 columns) is
  not checked yet (R13).
- R21 / `plainText` accepted, `r10-a` **12 349** (-93 against `r9-e`; Anastasia 4 PianoReduction -90, song 3 -15,
  song 2 +12 as expected, its truth keeps the shared lyrics): `musicxml.dedup_lyrics` clears a bar's lyrics in a
  listed voice when an earlier listed voice has the same (onset, duration, text) for every lyric note of that bar.
- R9 / rest-only voices accepted, `r11-a2` **12 224** (-125 against `r10-a`; Anastasia 3 Keyboard 1 -24, Keyboard 2
  -17, worst Anastasia 1 Keyboard 1 +2): in `r10-a` 351 bars had a length other than the truth bar (`barlen`: 177
  short, 110 long, 64 rest-only); `bars` (537) is mostly a made-up bar against an empty truth bar charged as
  delete + insert (2) instead of its notes, not a misplaced bar. `bars.fit_measure_rests` only fitted rests marked
  `measure="yes"`; now every voice of rests only (homr's whole rest of 4 quarters in a 3/4 bar, 3 + 2 quarters of
  rests) becomes one measure rest of the song's bar length, the `<backup>` after it moves by the difference so later
  onsets stay. A first run crashed on Anastasia 3 Keyboard 1 (indices of interleaved voices after a removal).
- R9 / short bars padded accepted, `r11-b` **12 060** (-164 against `r11-a2`; Anastasia 4 Drums -23, Ghost 5 Cello -14,
  Anastasia 3 Violin 2 -11, worst Ghost 1a Cello +1): `bars.pad_short_bar` (in `write_score` after
  `fit_measure_rests`, not on the first and last bar: pickup) adds a rest after the note (chord) that ends last
  when every voice ends before the song's bar length; the `<backup>` after it moves along. Notes keep their onsets,
  so only the bar length changes.
- R9 / long bars cut accepted, `r11-c` **11 998** (-62 against `r11-b`, no part worse; Ghost 20 Guitar -9, Anastasia 3
  Keyboard 1 -5): `bars.cut_long_bar` (after `pad_short_bar`, every bar) takes the overshoot of a bar longer than the
  song's bar length off the voice segment that ends last (after its last `<backup>`): from its last rest long enough,
  else from its longest note (chord notes alike, `<type>` / `<dot>` dropped so MuseScore takes the duration); the
  `<backup>` after it moves along. Left after `r11-c`: `barlen` 54 (41 long, 7 short, 6 rest-only), each a
  malformed bar: two staves' voices without a `<backup>` between them (Anastasia 3 Keyboard 2 bars 14 / 68 / 145),
  voices split by `<forward>`s (Anastasia 4 Keyboard 1 bar 14), a 48-quarter rest in Anastasia 1 Flute bar 26;
  fixing them belongs where the `<backup>` is lost, about 1 each. `bars` 491: mostly a made-up bar against an
  empty truth bar (delete + insert = 2, Ghost 4 PianoReduction bars 2-10, Anastasia 4 Tamburin) or the singer
  routing of Anastasia 3 Männer / Frauen (R6); true offsets are small (Ghost 13 Cello 16: a rest of 8 bars read as
  1 and 7 extra empty bars later, Ghost 5 Violin / Frauen about 10 each). Idea (a) was not tried: every part has
  the workbook bar count but Anastasia 4 Keyboard 1 (212 / 211) and Anastasia 3 PianoReduction (246 / 245).
- One track for one-staff books, `r12-a` **11 998** (no change on the benched songs): `build_parts` puts every
  bar on one track when each system has a single staff group. Anastasia 5 Bass: Audiveris read the boxed rehearsal
  number 83 as a part name and made bars 83-86 a second part (found while transcribing song 5).

Done in round 3 (2026-10-18, `r3-base` 12 423 -> `r3-f` 11 946, commits `c385426`, `2ad9819`): chord ties (-69), cues
up to "Play" (#41 partly, -29), fermatas shared across parts, extra rest bars dropped where the numbers show the
output ahead + trim to the workbook bar count (-327), workbook bar count as the song-end anchor of `align_bars`
(#26, -52). Rejected: chord symbols on all Ghost piano reductions (+72).

## Ground truth and evaluation

1. **More truth scores of different types.** Every new score type exposed bugs that the existing truth could not:
Ghost 20 (first born-digital show) showed the multi-rest problem (0.538 -> 0.719 after fixes). Most valuable next:
choir / vocal scores, drum parts, keyboard books, and songs with many instrument changes (Reed books).
2. **One command for a new truth score.** (Partly done 2026-10-14: `omrbench check` suggests the `truth` cell of
unmapped rows; the B2 cell is still typed by hand.) `omrbench bench <show> --songs 20 --transcribe` exists, but linking the truth
needs a manual workbook edit (B2 + `truth` column). A helper that lists the truth parts, proposes the mapping
from part / instrument names and prints the cells to paste would make a new truth score a five-minute job.
3. **Regression samples from real failures.** Cut the systems that broke (Ghost Trumpet system 8, Reed system 1,
Anastasia 2 Violin 1) into small samples with their truth bars, and test them in `pytest` via `reassemble()` on a
stored work dir. Then a change that fixes Ghost can't silently break Anastasia again.
4. **Metric for slash notation.** (Done 2026-10-14, `notef1.fold_slashes` / `edits.py`.) Ghost Guitar truth is 608 slash notes of 725. Compare slash noteheads on rhythm only
(any note at that onset and duration matches), so the score reflects what can be read from the page.
5. **Report what matters to the user.** (Done 2026-10-14: edit penalty, bars to fix, element F1 per category.) Next to note F1: bar count right (yes/no), key and time signature changes,
dynamics, lyrics. A part with right notes but one missing bar is almost usable; the index-based note F1 calls it 0.
The bar-aligned F1 is a start; a per-part "fix effort" estimate (bars to correct) would be closer to the real use.
6. **Track results over time.** (Done 2026-10-14: `results/<show>/bench/trend.csv`.) A small CSV / chart of total note F1 per show and commit (bench ids already exist), so
regressions show up as a dip, not in a table diff.
24. **Charge wrong-length bars in the edit penalty.** (Done 2026-10-15: category `barlen`, 1 per matched bar whose
filled length differs from the truth bar. On the fix4 outputs +1349 actions: Anastasia 2 +767, Anastasia 4 +339,
Ghost 20 +183.) A wrong time signature costs about one action today and padded
rests are free, so Anastasia 2 written in 4/4 (truth 3/4, ~55 bars 4 quarters long) is barely penalised. In MuseScore
every bar of the wrong length breaks (user, 2026-10-14), so each one needs an action. Fix this before re-running the grid
for the time-signature work (#21), or the gain won't show.

## Pipeline quality

7. **Slash and rhythm notation reader.** (Done 2026-10-15 for born-digital pages: `pipeline/vector.py` reads slash
heads, stems, beams, flags, rests, dots and ties from the vector glyphs; Ghost 20 Guitar -615 actions. Scanned slash
parts would need an image detector.) Slashes (guitar, keyboard comping), rhythm-only drum parts and chord symbols
are where Ghost loses most. Audiveris and homr have no slash support; a small detector on the crops (slash heads
are simple shapes) plus a rhythm-only bar would cover them. Full sweep (2026-10-14): Ghost Guitar costs 1032-1034
actions = 80 % of typing it in from scratch, in every variant; no grid setting helps.
8. **Drum parts.** (Done 2026-10-15: Audiveris bars on percussion staves -106, printed barlines on vector parts -503,
measure repeats written out -46; Ghost 20 Drums 887 -> 256.) Ghost Drums: 692 notes out vs 1329 in the truth (chords of hits get lost), note F1 0.48. A drum-kit
mapping (staff line -> instrument) and keeping all simultaneous hits would help; the truth uses `x` heads.
Full sweep (2026-10-14): Ghost Drums 848-1078 actions = 61-77 % of from scratch; with Guitar the worst parts relative
to their size, so the first quality targets.
9. **Octave conventions per instrument.** (Partly done 2026-10-15: keyboard patch labels "(loco & 8va)" .. "(loco)"
become 8va sections, Ghost 20 Utility -251.) Guitar and electric piano parts are written an octave off from sounding pitch
in some scores but not others. A per-part `transpose` in the workbook exists; a check that warns when the output and
truth differ by exactly an octave on most notes would find these fast.
10. **Generic sanity guards in the bar-count vote.** Reject a crop reading with more than 2x the Audiveris stacks (a
Zeus crop looped into 177 bars) and keep Audiveris' count when its stacks carry MULTI\_REST (done for Ghost).
11. **Chord symbols and lyrics.** (Chord symbols done 2026-10-15 on born-digital pages, from the PDF text layer: -109.
Open: the beat is estimated from x on an eighth grid, about half of Ghost 20 Guitar's 237 chords land half a beat off
(118 actions left); snap them to the slash / note x positions of the bar.) Chord names are dropped (`chord\\\_names: false` on piano reductions); for guitar and
keyboard books they are the main content. Audiveris reads chord symbols; route them into the output.
12. **Vector PDFs without OCR.** (Partly done 2026-10-15: bar count and bar x ranges from the printed barlines on
single-staff systems, -487. Multi-staff systems (piano, vocal scores) are barred apart and made the Anastasia piano
reduction much worse; not handled yet.) Ghost pages are born digital: bar numbers, counts, rehearsal marks and even note glyphs
are in the PDF. Reading the music-font glyphs directly (`docs/PLAN.md` step 8: native vector parsing) would beat any OCR.
21. **Time signatures checked against the bars and the other parts.** (Done 2026-10-15 via #25: the song's time row
replaces impossible readings and is written per printed bar; -1279.) `plan_systems` takes the time from homr where
printed, else carries it; nothing checks it. Full sweep (2026-10-14): Anastasia 4 Reed 1 planned in 2/4 (truth 4/4),
Keyboard 1 7/4, Reed 2 1/4; Anastasia 2 (3/4) written as 4/4 in every part (none read, measure rests 4 quarters
long); Ghost 20 Guitar 3/4 and 10/4 (truth 4/4). A wrong time makes `bar_ok` reject homr's correct bars, so `agree`
picks a worse reading (Reed 1 Oboe 359 of 546 notes, 643 actions). `agree-keep` hides it there (244 actions) but
costs on Anastasia 2 and Ghost 20. Fix: per system, the length most readers' voices fill decides when it disagrees
with the printed time; per song, a vote across parts by bar (user, 2026-10-14: all books of a song print the exact
same time signature at the same bar, but misread bar counts shift the bar numbers, so align before voting).
22. **Route by element, not only by part.** (2026-10-15, default pipeline: ties copied from Audiveris onto crop notes with the
same onset and pitch -69, kept. Slurs taken from Audiveris instead of homr: +106 on the Anastasia scans, rejected. Double /
final barlines from Audiveris: +129, rejected, its double barlines land on the wrong bars.) The sweep's best-per-part routing saves only 465 actions (4.3 %); the
category table shows bigger gaps per element: ties 625 -> 520 and slurs 617 -> 565 when Audiveris is preferred and no
ensemble is used, dynamics 693 -> 651, keys 350 -> 308. Take ties, slurs, dynamics, hairpins from the source that
reads them best and notes from the crop reader (`routing.yaml`, PLAN step 6).
23. **Articulations and words need new code.** (Words 2026-10-15: cue lines, dialogue, part labels and stage-management notes
left out of instrument parts, -264. Articulations: about 320 of the remaining 1280 are Anastasia 4 Trumpet / Trombone,
whose truths look incomplete (TRUTH_DEVIATIONS). Slash articulations read from the glyphs -46.) Second and sixth largest categories (1354 and 603 actions in the
sweep winner), and no grid variant moves them (best 1346 / 601). Find out per element which reader sees them at all
(homr, Audiveris, the ensemble readers, OCR) and why the rest are lost, before any tuning.

33. **Dynamics and hairpins on scans.** (Next round, user 2026-10-16. Tesseract already reads some: dynamics with conf >= 70
become `<dynamics>` at their beat, -3; on Anastasia 4 only ~120 mp / mf tokens over 14 books, few p / f. Plan: per-letter
templates (m, p, f, s, z in the publisher's bold italic) cut from the scans where OCR is sure, numpy-FFT correlation in the
bands below the staves, tokens from adjacent letters; then hairpins as two thin diverging lines.) (2026-10-15) 699 + 387 actions, almost all missing (not misplaced): Audiveris doesn't
see them on the scanned parts and homr writes none. Truth hairpins are 0-1 bars long, so `max_wedge_bars` is not the cause.
Needs a detector (template matching of p / mf / f glyphs, hairpin lines) on the crops.
34. **Ties on born-digital piano reductions.** (2026-10-15) Ghost 20 piano: truth 381 ties, Audiveris reads 346 over the whole
book (233 on the piano). The tie curves are filled paths in the PDF (as used for slashes); pairing them with the noteheads
would read them all.
35. **Barlines of multi-staff vector systems.** (2026-10-15) `vector.read_systems` bars single-staff systems only; on piano /
vocal systems the staves are barred apart and the Anastasia piano reduction got +3500 actions. Group the staves of a system
(braces, shared barlines) first.
36. **Single tremolos homr misses.** (2026-10-15) After turning homr's start / stop pairs into single tremolos (-140), about
100 single tremolos are still not read at all (Anastasia strings). (2026-11-02: 214 missing in `r12-a`, see the Anastasia truth review.)
37. **Chord symbols on normal-note bars.** (2026-10-15) Over slash bars the beat comes from the slash under the symbol; over
normal notes it is still the eighth-grid estimate from x. Use the Audiveris chord (notehead) x positions of the bar.
38. **Repeat signs and voltas.** (2026-10-15, Ghost 13 corrections: "repeat signs missing throughout", rated medium.)
Audiveris reads some repeat barlines; carry them (and voltas) onto the output bars, checked against the other parts.
39. **Ties over system breaks.** (2026-10-15, Ghost 13: ties not exact, mostly at line breaks.) A tie at the end of a
system has its end on the next system's first note; homr crops never see both. Join them in the assembly.
40. **Real dynamics instead of text.** (2026-10-15, Ghost 13 Cello, rated medium.) Dynamics ("mp", "sub. mp") read
as words; turn dynamic-only words into `<dynamics>` (with "sub." / "subito" as a word next to it).
41. **Cue bars marked by a part label.** (Partly done 2026-10-18: full-size cues from a part label ("Cl.", "Pno.") up to
"Play" are dropped, `assemble.drop_play_cues`; singer-label cues without "Play" are open, R11.) (2026-10-15, Ghost 13 Bass bar 1: a note for orientation under "Util.".)
Notes under another part's label at the start are a cue; drop them like small-note cues.
42. **Drop marks per part (`plain` parts).** (Done 2026-10-15: workbook column `plain`, `musicxml.strip_marks`, applied to
the output and to the truth part it is scored against; reference 8369 -> 7005.) Some parts get only notes, ties, dots,
tuplets, tremolos and playing words; articulations, dynamics, hairpins, slurs, fermatas, ornaments and tempo / expression text go.

Items 43–52 come from the error overview `docs/ERRORS.md` (2026-10-16, outputs `p1`, 7432 differences; counts are
differences, not edit-penalty actions). Related older items: repeats #38 (164 missing), ties over system breaks
#39, dynamics / hairpins #33 (~250 / 180 missing), tremolos #36 (49), cue bars under a part label #41 (user
2026-10-15: always a cue, also vocal cues like "MOLLY:").

43. **Re-spell notes when the crop's key was misread.** (Done 2026-10-16: `bars.respell_key` at write time; homr writes no
`<accidental>`, so a note that differs from the crop key is taken as printed; keys 7+ fifths apart (enharmonic) are left: -81.) (~450 pitch differences, the largest pitch kind.) homr
reads the key per crop and sometimes wrongly (Anastasia 4 Cello crop s08: 2 sharps in a 3-flat bar); the assembly
writes the right key but keeps homr's pitches (Ab -> A, Bb -> B; Anastasia 4 Cello 32, 37–38, 58–60, same bars in
Keyboard 1, Violins, Bass, Oboe). Where the crop key differs from the chosen key, re-spell every note without its
own `<accidental>` by the chosen key and the accidentals carried in the bar.
44. **Whole-bar rests get the bar's length.** (Done 2026-10-16, `bars.fit_measure_rests`: -153.) (175 bars.) `<rest measure="yes">` from the crop keeps 4 quarters in
3/4 bars (Anastasia 2 brass and reeds), MuseScore makes the bar 4/4 long. Set the duration from the bar's time.
45. **Double barlines.** (2026-10-16: a double barline before every key change of the song's `key` row was rejected, +99:
Ghost 20 changes key three times without one. Needs the printed barline.) (349 missing, every section change in the truths; the user wants them, 2026-10-16.) Audiveris' double barlines were rejected
(+129, wrong bars). Vector pages: the barline type from the drawing (two strokes 2–4 pt apart, thick final stroke,
repeat dots). Scans: a double barline where a rehearsal mark, key or time change starts a bar.
46. **Tie read as a slur.** (Done 2026-10-16: `musicxml.slurs_to_ties` on the output too: -288.) (138.) A slur between two neighbouring notes of the same pitch is a tie (confirmed by
the user 2026-10-16: a slur only joins different pitches). Together with
#39 this covers most of the 285 missing ties (Ghost 20 Piano 108).
47. **Copy marks onto "sim." and %-bars.** (Done 2026-10-16: `bars.apply_sim` -105; %-bars in systems without a printed
bar number were skipped, now placed by page position -56. Open: the rehearsal mark copied into %-bars.) (User 2026-10-16: like the truth.) After "sim." the pattern bar's
articulations go onto the following bars that repeat its rhythm (Ghost 13 Cello 27–33, 99–105); written-out
%-bars keep the source bar's articulations (Ghost 13 Bass 114–129, ~45 accents). `assemble.apply_repeats` copies
notes; check the articulations survive. Also: it copies the rehearsal mark into every %-bar (Ghost 13 Bass: J
seven times); drop rehearsal marks from the copies.
48. **Notes far below the bass staff.** Low notes with many ledger lines are misread (Anastasia 4 Keyboard 1 bars 20,
23, 65: G1 -> Cb2, C1 -> F1, D2 -> A2); most of the 221 "wrong by more than a third". Check against the staff
position of the Audiveris head, or add 8vb lines if printed.
49. **Anastasia 4 singers.** (~1250 differences in Dmitry, Vlad, Männer, Frauen.) Whole passages missing (Dmitry
101–115, 169–206, with lyrics), Männer bars missing / extra around 42–62, made-up instrument changes in Männer (19),
Frauen two voices on one staff written as chords (57–64), lyrics in verse 2 where the truth uses verse 1 (~35).
Mostly the singer-label routing of the piano reduction.
50. **Words wrongly made system text.** (Done 2026-10-16: system text only for tempo terms, other short text above the top
staff that is no playing word is left out: -178.) (229.) In split-instrument books every word becomes system text
(`assemble.py` `split or ...`), and "gedämpft", "solo", "fill", "sim." and tempo words are moved to the top part;
the truths keep them on the part. Only rit. / a tempo / accel. style texts should be system text.
51. **Small ones from the overview.** Sextuplets written 3:2 instead of 6:4 (Anastasia 1 bar 1, 6 parts); key / time
changes one bar off after the lettered bars of Anastasia 4 (bar drift around 128–131); Ghost guitar chord symbols
one beat off (28, see #37); missing "arco" ×32, "pizz." ×25, made-up "solo" ×12.
52. **What sheet_reader (`~/sheet_reader`, external, developed by a friend; no changes there) can bring.** Tested
2026-10-16 on 14 Ghost parts (`docs/ERRORS.md`): as an engine 7111 actions vs 1341 for the pipeline, note-perfect
in only 14 bars where the pipeline is not. Not an engine candidate now. Where it helps, all on born-digital pages
(Ghost only, 2133 of 7432 differences):
    - **Glyph knowledge** for `pipeline/vector.py`: its `glyph_map.py` names 65 EngraverFontSet / Maestro /
      MaestroPercussion characters (dynamics p..fff, sfz, fp, accent, marcato, fermata, harmonic, bow marks,
      accidentals, clefs, time digits, rests, flags; 47 still marked guess). Our `vector.GLYPHS` knows 14. Reading articulations, dynamics
      and fermatas from the glyphs and putting them on the output note by bar + x order would replace homr's marks
      on vector pages (Ghost: articulations 319, dynamics 70, fermatas 15). Evidence: Ghost 13 Cello marcatos PDF 42
      = truth 42, pipeline 26; dynamics PDF 9, truth 10, pipeline 5.
    - **Ties and slurs from curves** (`export_musicxml.get_slurs_and_ties`, `resolve_ties`: a curve whose ends sit
      on two equal pitches is a tie). Ghost: ties 300, slurs 149.
    - **Pitch from the notehead's y position** (`pitch.py`, exact on vector pages) as a check of homr's pitch per
      onset (Ghost one / two staff steps off: 90; accidental and key errors 38 + 20).
    - **Key, clef, time per staff from glyphs** (`staff_info.py`) as a check of the crop's key (#43 on Ghost).
    - **Barline types** (#45) from `page_dump.get_barlines`.
    - **Re-test 2026-10-16 (commit `b6b04f0`)**: 6440 actions vs 1387 for the pipeline on the same 14 parts (was 7111);
      note-perfect where the pipeline is not: 15 bars. Now exports articulations, dynamics, hairpins, chords, lyrics,
      repeats / voltas, mid-line key changes. Better than the pipeline only on dynamics (33 vs 58 actions), repeats /
      voltas (all 8 found) and key changes (22 vs 36). Still one system per page, no multi-rests, no grand staff, no
      transposition, slurs / barline types not exported. Reading the accents from the glyphs ourselves was tried: +13
      (Ghost 20 Reed truth has accents the page lacks). Left to port: dynamics from glyphs (~20-25), mid-line key glyphs
      (~10-15), repeat barlines / voltas (~5-8).
  Import as a library (pinned commit, `~/sheet_reader/tools` on `sys.path`, or a git submodule) once its API returns
  positions (page, x, y, bar) and not only MusicXML; until then copy ideas, not code. Feature requests for its
  developer: `docs/sheet_reader_requests.md`.

53. **Lettered bars per song (workbook row `letters`).** (Code done 2026-10-16: `131A, 132C, 148A-C` seeds `align_bars`;
Anastasia 4 -394 with the row. Each part read only some of the letters, so the key / time rows and the bars drifted 1-4 bars.)
Needs the row in the workbook (user).
54. **"arco" / "pizz." on scans.** Tesseract reads 13 of the 26 in Anastasia 4 Violin 1; adding them was -2 (rejected). The
truth alternates pizz. / arco strictly (music rule): a missing "arco" between two "pizz." is certain, but its bar is not. (2026-11-02: with `playtech` a missing word costs 2, about 150 actions; re-measure, see the Anastasia truth review.)
55. **Ties from the vector curves** (#34 again, 2026-10-16): Audiveris' ties are copied (72 on the Ghost 20 piano, plus edge
notes by pitch -6), 108 are still missing there. Pair each tie curve with the notehead columns at both ends.

## Prior knowledge (cheap to enter in advance)

Facts known before a run that the pipeline could check its readings against. `show.yaml` already has transposition,
clef type, aliases, doubling and cues. Ranked by value for the effort.

25. **Time signature and key per song, by bar.** (Done 2026-10-15: workbook rows `time`, `key`, `bars`; time -1279,
key -134 over the 6 truth songs.) A few minutes per song from the piano reduction (workbook column or
song-level yaml: `time: {1: 4/4, 68: 2/4, 69: 4/4}`, same for `key`). Fixes #21 directly and helps keys (350 actions in
the full sweep). The no-work version is the cross-part vote in #21, but a known answer beats a vote.
26. **Bar count per song as a pipeline input.** (Done 2026-10-18: `song_bars` anchors the song end in `align_bars`, rest
bars past it are trimmed, fermata sharing uses it; together with dropping extra rest bars -379.) Already collected for the bench (Anastasia bar counts); fed into the
bar-count vote it turns it into a check against a known total. Check first whether the pipeline reads it today.
27. **Written range per instrument** in the `instruments` library of `show.yaml` (standard ranges, near zero work).
Catches octave and clef misreads and wild notes from bad crops (clefs, octave, part of notes).
28. **Staves and clef per book.** Keyboard = grand staff, Trombone / Bass in bass clef, Violin 2 plays viola in alto clef
in No. 11 / 26. Catches misread clefs and wrong staff grouping.
29. **Drum legend per show.** (Done 2026-10-15: no show prints one, so `scripts/derive_drumkit.py` learns it from the
truth drum parts into `drumkit.yaml`. **Re-run it after every new drum truth** and check the `notes:`; the pipeline
maps drum notes through the show's largest kit.) Staff line / notehead -> instrument, copied once from the drum book's legend page. Needed
for #8; Drums are the worst part.
30. **"Slash / rhythm part" flag per book.** (Not needed on born-digital pages: slash bars are detected per bar.) Marks Guitar and keyboard comping parts so the pipeline expects slashes and
chord symbols there (#7, #11).
31. **Rehearsal marks and tempo list per song.** From the piano reduction (reads best), shared to every part (system
text 292 actions in the full sweep).
32. **Libretto text for lyrics.** Corrects OCR of the vocal-score lyrics (452 actions); more work, piano reductions only.

## Speed and resources

13. **Parallel songs instead of parallel PDFs.** One transcribe peaks at \~10 GB with `--jobs 2`; with 28 GB, two songs
side by side would use the machine better on long shows.
14. **Skip unchanged work.** `transcribe` already skips unchanged PDFs; also cache Audiveris per page so a changed page
range doesn't redo the whole PDF.
15. **homr on the GPU at fp32.** fp32 models on CUDA gave CPU-identical output but no speed-up (scratch test). Worth
retrying with larger batches per worker; homr is most of the runtime.

## Usability

16. **A results viewer.** A small HTML page per song: page image, our bars and the truth side by side, wrong bars
highlighted. Faster to judge a transcription than opening MuseScore.
17. **Workbook checks before a long run.** `omrbench check` validates the workbook; make `transcribe` refuse to start
on errors (page ranges outside the PDF, unknown instrument names) instead of failing per part.
18. **Clear output naming for split parts.** Piano reductions give `- Voices` / `- Piano` files; doubling books give
one part per instrument. A short README in each `results/<show>/<song>/` folder listing what each file holds. Also the Instruments sometimes dont match up with the ones in musescore. The Instrument Bass is not interpreted as the electric bass musescore knows, but as the voice register bass. Also Cello is not mapped to violoncello. So most Instruments have to be reconfigured in musescore. Adding a mapping would probably help.

## Engineering

19. **Tests for the container scripts** (`docker/\\\*/` entry points) with a tiny image fixture, run on demand
(`pytest -m docker`), so image rebuilds are checked.
20. **Pin the remaining unpinned assets.** Clarity weights (HF main), llama.cpp image (by digest only), OCR model
downloads at build time.

