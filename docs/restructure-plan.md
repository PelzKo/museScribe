# museScribe restructure plan

Decisions (2026-10-10): virtual song folders, truth mapping in workbook, results = latest + run history,
delete old data folders, prune old results (incl. dev-baseline), keep multi-engine `run`,
keep oemer, drop `_` prefix (data/anastasia, data/ghost, data/samples/), song 4 truth skipped for now.

## Target layout

```
data/                              read-only, edited by hand only
  anastasia/                       (was _anastasia)
    show.yaml
    songs.xlsx                     B2 = truth file per sheet; column `truth` per row
    pdfs/*.pdf                     full books, never copied
    truth/
      01_Opening_….mscz            (was data/_truth)
  ghost/                           (was _ghost)
  samples/                         single-PDF benchmark samples: demo-*, threelittlewords
results/                           everything generated
  anastasia/
    <song>/<part>.musicxml         latest transcription per song (+ combined.musicxml/.mscz)
    runs/<ts>/                     run.log, pipeline/ work dirs, pipeline.json, manifest.json
    bench/<ts>/                    scores.json, metrics.csv, report.md
  runs/<ts>/                       legacy multi-engine `run` on samples/
  cache/                           truth mscz -> musicxml, page renders, OCR (keyed by file hash)
```

Project discovery: a folder in data/ with `show.yaml` = project; `data/samples/*` = samples.
No more `_` prefix convention.

## Phase 0 – safety (small, do first)  — DONE 2026-10-10
1. Pin `homr==0.7.0` in setup.sh (next homr release breaks `_homr_worker.py` ProcessingConfig
   positional args). Switch worker to keyword args so a later upgrade is easy.
2. Note in README: Audiveris 5.11.0 = latest; oemer 0.1.8 frozen/unmaintained.

## Phase 1 – song spec from workbook (replaces generated folders)  — DONE 2026-10-10
(genmeta.py -> project.py; `gen-meta` replaced by `check`; truth cell/column parsed, not yet used;
truth part names are not validated against the score yet -> Phase 3)
1. Refactor genmeta.py into `project.py`: `load_project(show.yaml) -> Project`,
   `Project.songs(ids) -> [Song]`, `Song.parts -> [PartJob(pdf, pages, meta, truth_parts)]`.
   Pure, in-memory; same merge rules as gen-meta today (show meta < part defaults < instruments < extra).
2. `gen-meta` becomes `omrbench check <project> [--songs]`: validates workbook (pages vs PDF page
   count, unknown instruments, date-mangled cells, truth file exists, truth part names exist in
   the truth score) and prints the resolved yaml per part. Optional `--export DIR` writes yamls.
3. Workbook additions: cell A2/B2 `truth` = path relative to project; column `truth` after
   `instruments` (comma list, same order as instruments; single name otherwise; PianoReduction
   rows: `Piano=Klavierauszug; Voices=auto`).

## Phase 2 – transcribe writes only to results/  — DONE 2026-10-10 except item 5 (cache), deferred
(sample transcribe writes to results/samples/<sample>/; folders renamed: data/anastasia, data/ghost,
data/anastasia/truth, data/samples/ — part of Phase 5 already done)
1. `omrbench transcribe anastasia --songs 1,2,4A [--parts Horn,Bass] [--force] [--keep-awake]`.
   Old form `omrbench transcribe --samples …` stays for data/samples.
2. Pages taken straight from `pdfs/` (subset.pdf only inside work dir). No PDF copies anywhere.
3. Outputs: `results/<proj>/runs/<ts>/…` then promoted to `results/<proj>/<song>/` on success.
4. Skip logic: a part is skipped when `results/<proj>/<song>/manifest.json` has the same
   input hash (pdf sha + pages + resolved meta + code version/git sha), unless `--force`.
   Replaces "musicxml exists next to PDF".
5. Page renders + OCR cache move to `results/cache/` keyed by pdf hash + page + dpi
   (shared across runs; today re-rendered per run).

## Phase 3 – benchmark against full-score truth
1. `truth.py`: convert .mscz via MuseScore 4 CLI (reuse transcribe.to_mscz lookup incl. WSL
   .exe fallback; dataset._find_gt lacks it) into `results/cache/truth/<hash>.musicxml`.
   Split into parts by part name; drop placeholder parts (map value `-`).
2. Port scratchpad eval (note F1 by bar, staff, onset, sounding midi, duration; index-aligned
   bars) into `metrics/notef1.py` as main metric. Conventions: sounding pitch, 8va, cues dropped,
   voices octave-insensitive option. Add per-part bar-count check vs truth.
3. `omrbench bench anastasia --songs 1,2,4A [--run <ts> | --transcribe]`: default scores the
   latest results/<proj>/<song>/; writes results/<proj>/bench/<ts>/ with per-song/per-part table,
   delta vs previous bench. musicdiff/TEDn behind `--full` (slow).
4. Multi-instrument parts: output split parts (Reed 1 – Piccolo, Reed 1 – Flute) map 1:1 to
   truth parts listed in the `truth` column.

## Phase 4 – legacy benchmark cleanup
1. `run` stays for data/samples; GT conversion writes to results/cache, not data/.
2. Reuse truth.py + notef1 so both commands share metrics.

## Phase 5 – data/results migration (manual, after phases 1-3 work)
1. Move `_anastasia`->`anastasia`, `_ghost`->`ghost`, `_truth/*`->`anastasia/truth/`,
   demos + threelittlewords -> `samples/`.
2. Song 4 truth: skipped for now (Theresa's not finished). Before deleting, move her files
   (`final_result.mscz`, `correct_piano_reduction.musicxml`) to anastasia/truth/wip/ (not linked).
3. Delete `_old_folders`, `feedback-v1`, `anastasia-1/2/4A` (≈1 GB).
4. Prune results/ (2.9 GB): all old runs, zips, transcribe-v2, a12-base, dev-baseline.
5. Fill truth cells in songs.xlsx for 1, 2, 4A.

## Phase 6 – docs
README -> quickstart (setup, transcribe, bench); move pipeline internals to docs/pipeline.md,
workbook format to docs/workbook.md.

## Verification
- transcribe song 4A via new path; byte-compare musicxml with current transcribe output.
- bench songs 1/2/4A reproduces F1 ≈ 0.935 / 0.967 / 0.985 from 2026-10-09.
- `git status` + checksum of data/ unchanged after transcribe and bench.
