# Shows: transcribe and benchmark song by song

A show is a folder `data/<show>/` with a `show.yaml`; its songs come from one workbook, its
parts from full-book PDFs, its ground truth from MuseScore full scores.

## Workbook

For a show transcribed song by song from the same full-book parts, keep everything in
`data/<show>/` (any folder of `data/` with a `show.yaml`):

```
data/anastasia/show.yaml    constants: meta block, per-part defaults, instrument library
data/anastasia/songs.xlsx   one sheet per song (sheet name = song id, B1 = title, B2 = truth file)
data/anastasia/pdfs/        the full-book PDFs (read in place, never copied)
data/anastasia/truth/       ground-truth MuseScore files, linked from the workbook
```

```bash
omrbench check anastasia                 # validate the workbook: pages vs PDFs, truth files, ...
omrbench check anastasia --songs 5 -v    # also print every part's resolved meta
omrbench transcribe anastasia --songs 5
```

Each song sheet has `title` (A1/B1), optionally `truth` (A2/B2, path relative to the show
folder; several single-part files separated by ";" are merged, each part named after the text behind the last
" - " of its file name: "truth/#13 - Bass.mscz; truth/#13 - Cello.mscz" -> parts Bass, Cello) and optionally `unfinished` (next key row: truth part names not hand-corrected yet,
"Voice 1, Drum Kit"; `bench` leaves them out until you remove them) above a header row `file | pages | skip | instruments | extra | truth | plain | notes` (`plain`: "x" = notes, ties and dots only, see `project.py`), one row
per PDF. Nothing is generated on disk: `transcribe` builds every part's meta from the workbook
when it runs, so the workbook is the only place to edit (`check --export DIR` writes the
resolved yamls for inspection).

| Column | Example | Becomes |
|---|---|---|
| `pages` | `11-16` | `pages`. Empty: part not in this song. Also leave it empty for a TACET part when the show uses `cues: drop` (it would come out as rests only). |
| `skip` | `1-3` | `skip_systems: [1, 2, 3]` |
| `instruments` | `Clarinet, Flute` | Names looked up in the `instruments` library of `show.yaml` (transpose, aliases, clef). Several on a non-drums part: `split_instruments: true`. A single one only sets the part's `transpose`. Keys in brackets apply to this song only and win over the library: `Triangle (lower_staff)` (a bare key means `true`), `Clarinet (transpose: A)`. Marking one instrument `lower_staff` takes it off every other instrument of that song. |
| `extra` | `chord_names: false` | Raw YAML keys, win over everything. `lyrics: null` drops a part default. |
| `truth` | `Piccolo, Flöte 1` | Part name(s) in the song's truth score this row is compared with, in `instruments` order. Optional. |
| `notes` | `Bassoon` | Ignored. |

New song: duplicate the previous sheet in Excel, rename it, set the title and pages. The cells
are formatted as Text so Excel keeps `5-9` from becoming a date (the generator stops with an
error if that happens anyway). `omrbench check` then shows what the new sheet resolves to.

## Transcribe

```bash
omrbench transcribe anastasia --songs 1,2              # every part of songs 1 and 2
omrbench transcribe anastasia --songs 4A --parts Horn --force
omrbench transcribe                                    # every PDF of every sample in data/samples
omrbench transcribe --samples demo --prefix_matching
```

Runs one engine (`--engine`, default `pipeline`) on every part of the selected songs of a show
(pages read straight from the full-book PDFs, see "Workbook" below), or on every `*.pdf` of the
selected sample folders (same `--samples` / `--exclude` / `--prefix_matching` as `run`). No ground
truth needed, nothing is scored, no report. A PDF is skipped when its inputs (PDF, resolved meta,
engine settings) are unchanged since its last output, as recorded in `manifest.json`; a code
change alone doesn't redo it, so use `--force` after changing the pipeline.

`--keep-awake` keeps Windows (also when running in WSL) from going to sleep until the run ends,
so long overnight runs don't pause; the screen may still turn off. Off by default; when on, the
log says so at the start and end. It holds a PowerShell `SetThreadExecutionState` request that
ends with the run, also if it crashes.

Several PDFs run at once (`--jobs N`, default `transcribe_jobs: 2` in `bench.yaml`), longest
first, so Audiveris on one PDF overlaps homr on another. All homr crops go to one pool of
persistent homr workers (default 8 workers x 2 ONNX threads on a 16-thread CPU, ~1 GB RAM each;
`workers` / `threads` under the `homr` settings). On the 8-core laptop this was tuned on, a
crop takes ~0.9 s instead of ~3.5 s. Measured on 4 anastasia-4 parts (25 pages): 1380 s
before, 554 s now; 3 PDFs at once or niced workers were slower. `parallel_sheets: true` (Audiveris
settings) processes the sheets of a PDF in parallel, ~2x faster, but Audiveris 5.11 has a race
there that drops symbols (`"this.parameters" is null` in its log) and kills some PDFs, so it is
off; a parallel run that exports nothing is redone serially.

`results/<show>/<song>/` (or `results/samples/<sample>/`) then holds the latest output of every part:

- `<name>.musicxml` (`<name> - Voices.musicxml` / `<name> - Piano.musicxml` for a piano reduction)
- `combined.musicxml` / `combined.mscz`: all of the folder's files stacked as parts of one score,
  all starting at bar 1, in sheet (PDF) order, rebuilt whenever a part changes. Parts are named
  after the PDF (`<name> – <part>` for multi-part outputs such as split percussion). No padding:
  if parts differ in bar count, MuseScore calls the score corrupted and fills the gaps; it is then
  saved with `-f`. The `.mscz` needs the MuseScore CLI (`musescore_cli` in `bench.yaml`, `mscore` on
  PATH, or the default Windows MuseScore 4 install when running in WSL)
- `manifest.json`: per PDF the run, engine, code version and input key of its latest output

and `results/<show>/runs/<timestamp>/` the run itself:

- `<song>/<name>.musicxml`: this run's outputs
- `<engine>/<show>-<song>--<name>/`: engine work dirs (`subset.pdf`, crops, `pipeline.json`)
- `run.log`: everything the run reported, one line each:
  `2026-10-01 10:39:12 | WARNING | anastasia-4--Horn | homr failed on page 3 system 2 (#12) ...`
  (time, level DEBUG/INFO/WARNING/ERROR, the PDF it is about, message). Every failed homr crop
  with its reason and crop image, Audiveris errors (its warnings at DEBUG), bar-number
  alignment (rest bars added, numbers ignored as misread, places where an extra bar was read),
  engine crashes with traceback. The console shows INFO and up. `omrbench run` writes one too.

The meta keys the pipeline reads (pages, transposition, instruments, cues, ...) are listed in
[pipeline.md](pipeline.md#meta-keys).

## Benchmark against the truth (`bench`)

```bash
omrbench bench anastasia                       # latest outputs of every song with a truth file
omrbench bench anastasia --songs 1 --transcribe   # transcribe song 1 first (unchanged parts skipped)
omrbench bench anastasia --run 20261010-1530   # the outputs of one transcribe run instead
omrbench bench anastasia --full                # also OMR-NED and TEDn per part (minutes)
```

The truth is a full score made in MuseScore, as it is: `data/<show>/truth/<song>.mscz`, linked
from the song's sheet (A2 `truth`, B2 the path). It is exported once with the MuseScore CLI to
`results/cache/truth/` (again when the file changes). Each row's `truth` cell names the truth
part(s) its output is compared with:

| `truth` cell | Meaning |
|---|---|
| `Violine 1` | the row's only output part |
| `Piccolo, Flöte 1` | one name per instrument, in `instruments` order (split parts); `-` leaves one out |
| `Piano=Klavierauszug, Men=Männer` | by output part name; for piano reductions (parts of both files, singers named after the printed label); `Voice=-` ignores an output part |

Output parts that name the same truth part are compared together. `omrbench check` checks the
names against the truth score and lists truth parts with notes that no row names.

The metric is note F1 per truth part: a note is (bar, staff, onset, sounding pitch, duration),
bars matched by index, sounding pitch = written + `<transpose>` (so transposing parts compare
fine either way); cue and grace notes are left out. Variants: `pitch` (no duration), `pc` (pitch
class: octave conventions of singer parts), `rhythm` (no pitch: percussion). Per song the
counts are summed (micro F1). A bench takes seconds.

`results/<show>/bench/<timestamp>/` holds `report.md` (also printed: per part F1, precision,
recall, bar counts, change since the previous bench; the bars that differ; what wasn't
compared), `scores.json` and `metrics.csv`; with `--full` also the per-part files compared.
