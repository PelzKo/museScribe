# Improvement ideas

Ideas for making museScribe better, roughly in order of value. Status and results of the planned phases are in
`PC_PLAN.md` and `PLAN_full.md`; this file is the backlog of things not planned yet.

## Ground truth and evaluation

1. **More truth scores of different types.** Every new score type exposed bugs that the existing truth could not:
   Ghost 20 (first born-digital show) showed the multi-rest problem (0.538 -> 0.719 after fixes). Most valuable next:
   choir / vocal scores, drum parts, keyboard books, and songs with many instrument changes (Reed books).
2. **One command for a new truth score.** `omrbench bench <show> --songs 20 --transcribe` exists, but linking the truth
   needs a manual workbook edit (B2 + `truth` column). A helper that lists the truth parts, proposes the mapping
   from part / instrument names and prints the cells to paste would make a new truth score a five-minute job.
3. **Regression samples from real failures.** Cut the systems that broke (Ghost Trumpet system 8, Reed system 1,
   Anastasia 2 Violin 1) into small samples with their truth bars, and test them in `pytest` via `reassemble()` on a
   stored work dir. Then a change that fixes Ghost can't silently break Anastasia again.
4. **Metric for slash notation.** Ghost Guitar truth is 608 slash notes of 725. Compare slash noteheads on rhythm only
   (any note at that onset and duration matches), so the score reflects what can be read from the page.
5. **Report what matters to the user.** Next to note F1: bar count right (yes/no), key and time signature changes,
   dynamics, lyrics. A part with right notes but one missing bar is almost usable; the index-based note F1 calls it 0.
   The bar-aligned F1 is a start; a per-part "fix effort" estimate (bars to correct) would be closer to the real use.
6. **Track results over time.** A small CSV / chart of total note F1 per show and commit (bench ids already exist), so
   regressions show up as a dip, not in a table diff.

## Pipeline quality

7. **Slash and rhythm notation reader.** Slashes (guitar, keyboard comping), rhythm-only drum parts and chord symbols
   are where Ghost loses most. Audiveris and homr have no slash support; a small detector on the crops (slash heads
   are simple shapes) plus a rhythm-only bar would cover them.
8. **Drum parts.** Ghost Drums: 692 notes out vs 1329 in the truth (chords of hits get lost), note F1 0.48. A drum-kit
   mapping (staff line -> instrument) and keeping all simultaneous hits would help; the truth uses `x` heads.
9. **Octave conventions per instrument.** Guitar and electric piano parts are written an octave off from sounding pitch
   in some scores but not others. A per-part `transpose` in the workbook exists; a check that warns when the output and
   truth differ by exactly an octave on most notes would find these fast.
10. **Generic sanity guards in the bar-count vote.** Reject a crop reading with more than 2x the Audiveris stacks (a
    Zeus crop looped into 177 bars) and keep Audiveris' count when its stacks carry MULTI_REST (done for Ghost).
11. **Chord symbols and lyrics.** Chord names are dropped (`chord_names: false` on piano reductions); for guitar and
    keyboard books they are the main content. Audiveris reads chord symbols; route them into the output.
12. **Vector PDFs without OCR.** Ghost pages are born digital: bar numbers, counts, rehearsal marks and even note glyphs
    are in the PDF. Reading the music-font glyphs directly (`docs/TODO.md`: native vector parsing) would beat any OCR.

## Speed and resources

13. **Parallel songs instead of parallel PDFs.** One transcribe peaks at ~10 GB with `--jobs 2`; with 28 GB, two songs
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
    one part per instrument. A short README in each `results/<show>/<song>/` folder listing what each file holds.

## Engineering

19. **Tests for the container scripts** (`docker/*/` entry points) with a tiny image fixture, run on demand
    (`pytest -m docker`), so image rebuilds are checked.
20. **Pin the remaining unpinned assets.** Clarity weights (HF main), llama.cpp image (by digest only), OCR model
    downloads at build time.
