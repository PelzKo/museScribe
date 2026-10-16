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

33. **Dynamics and hairpins on scans.** (2026-10-15) 699 + 387 actions, almost all missing (not misplaced): Audiveris doesn't
see them on the scanned parts and homr writes none. Truth hairpins are 0-1 bars long, so `max_wedge_bars` is not the cause.
Needs a detector (template matching of p / mf / f glyphs, hairpin lines) on the crops.
34. **Ties on born-digital piano reductions.** (2026-10-15) Ghost 20 piano: truth 381 ties, Audiveris reads 346 over the whole
book (233 on the piano). The tie curves are filled paths in the PDF (as used for slashes); pairing them with the noteheads
would read them all.
35. **Barlines of multi-staff vector systems.** (2026-10-15) `vector.read_systems` bars single-staff systems only; on piano /
vocal systems the staves are barred apart and the Anastasia piano reduction got +3500 actions. Group the staves of a system
(braces, shared barlines) first.
36. **Single tremolos homr misses.** (2026-10-15) After turning homr's start / stop pairs into single tremolos (-140), about
100 single tremolos are still not read at all (Anastasia strings).
37. **Chord symbols on normal-note bars.** (2026-10-15) Over slash bars the beat comes from the slash under the symbol; over
normal notes it is still the eighth-grid estimate from x. Use the Audiveris chord (notehead) x positions of the bar.
38. **Repeat signs and voltas.** (2026-10-15, Ghost 13 corrections: "repeat signs missing throughout", rated medium.)
Audiveris reads some repeat barlines; carry them (and voltas) onto the output bars, checked against the other parts.
39. **Ties over system breaks.** (2026-10-15, Ghost 13: ties not exact, mostly at line breaks.) A tie at the end of a
system has its end on the next system's first note; homr crops never see both. Join them in the assembly.
40. **Real dynamics instead of text.** (2026-10-15, Ghost 13 Cello, rated medium.) Dynamics ("mp", "sub. mp") read
as words; turn dynamic-only words into `<dynamics>` (with "sub." / "subito" as a word next to it).
41. **Cue bars marked by a part label.** (2026-10-15, Ghost 13 Bass bar 1: a note for orientation under "Util.".)
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
truth alternates pizz. / arco strictly (music rule): a missing "arco" between two "pizz." is certain, but its bar is not.
55. **Ties from the vector curves** (#34 again, 2026-10-16): Audiveris' ties are copied (72 on the Ghost 20 piano, plus edge
notes by pitch -6), 108 are still missing there. Pair each tie curve with the notehead columns at both ends.

## Prior knowledge (cheap to enter in advance)

Facts known before a run that the pipeline could check its readings against. `show.yaml` already has transposition,
clef type, aliases, doubling and cues. Ranked by value for the effort.

25. **Time signature and key per song, by bar.** (Done 2026-10-15: workbook rows `time`, `key`, `bars`; time -1279,
key -134 over the 6 truth songs.) A few minutes per song from the piano reduction (workbook column or
song-level yaml: `time: {1: 4/4, 68: 2/4, 69: 4/4}`, same for `key`). Fixes #21 directly and helps keys (350 actions in
the full sweep). The no-work version is the cross-part vote in #21, but a known answer beats a vote.
26. **Bar count per song as a pipeline input.** (The `bars` row exists since 2026-10-15, as meta `song_bars`; not used
by the pipeline yet.) Already collected for the bench (Anastasia bar counts); fed into the
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

