# Improvement ideas

Ideas for making museScribe better, roughly in order of value. Status and results of the planned phases are in
`PLAN.md`; this file is the backlog of things not planned yet.

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
22. **Route by element, not only by part.** The sweep's best-per-part routing saves only 465 actions (4.3 %); the
category table shows bigger gaps per element: ties 625 -> 520 and slurs 617 -> 565 when Audiveris is preferred and no
ensemble is used, dynamics 693 -> 651, keys 350 -> 308. Take ties, slurs, dynamics, hairpins from the source that
reads them best and notes from the crop reader (`routing.yaml`, PLAN step 6).
23. **Articulations and words need new code.** Second and sixth largest categories (1354 and 603 actions in the
sweep winner), and no grid variant moves them (best 1346 / 601). Find out per element which reader sees them at all
(homr, Audiveris, the ensemble readers, OCR) and why the rest are lost, before any tuning.

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

