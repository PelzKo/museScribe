# museScribe – OMR engine benchmark (`omrbench`)

Runs several OMR engines on your own sample PDFs, scores their MusicXML against hand-corrected ground truth, measures runtime / CPU / memory / GPU and writes a Markdown report. Implements the evaluation protocol (section 12) from the OMR research notes.

| Engine | How it runs | Notes |
|---|---|---|
| `audiveris` | Audiveris 5.11 batch CLI (`-batch -transcribe -export`) | stock settings |
| `audiveris-meta` | same, with switches from `meta.yaml` | drums, OCR languages, small heads, ... |
| `homr` | `homr page.png`, one call per page | CPU or CUDA |
| `oemer` | `oemer page.png`, one call per page | CPU or CUDA; disabled by default |
| `pipeline` | Audiveris layout + homr per cropped staff group + repairs | see below |
| *external* | `data/<sample>/external/<tool>.musicxml` | Soundslice, Newzik, PlayScore, ...; scored, not timed |

Every engine is a subprocess from the same harness, measured the same way.

## Setup (WSL / Ubuntu)

```bash
bash setup.sh            # add --gpu for onnxruntime-gpu (needs an NVIDIA GPU visible in WSL)
source ~/.local/share/omrbench/env.sh
omrbench doctor
```

`setup.sh` needs no root. It puts everything under `~/.local/share/omrbench` (venvs on `/mnt/c` are slow):
- a harness venv
- a separate venv for each of homr and oemer (their dependencies conflict)
- Audiveris, unpacked from the official `.deb` with its bundled JRE
- Tesseract data for `deu lat eng ita`, from the full `tessdata` repo, since Audiveris needs the legacy models
- the homr and oemer model downloads, so they don't count towards the first run's time

To smoke-test the setup, `omrbench demo` engraves two corpus pieces with Verovio into `data/demo-*`. Engraved PDFs are much easier than scans, so don't draw conclusions from them.

## Your samples

```bash
omrbench new-sample choir-01      # creates data/choir-01/ with meta.yaml template
```

```
data/choir-01/
  input.pdf          2-3 pages, scan or phone photo
  gt.musicxml        hand-corrected in MuseScore (File > Export > MusicXML); gt.mxl/gt.mscz also OK
  meta.yaml          type (choir|piano|piano_reduction|part|orchestral|drums|other), languages, switches, correction times
  external/          optional: soundslice.musicxml, playscore.mxl, ...
```

The ground truth must cover exactly the pages in `input.pdf`. See `meta.example.yaml` for all keys.

## Running

```bash
omrbench run                              # all engines, all samples -> results/<timestamp>/report.md
omrbench run --engines audiveris,homr --samples choir-01
omrbench run --exclude demo --prefix_matching   # skip every demo-* sample
omrbench run --resume 20260927-1300       # re-use finished engine outputs, retry failures
omrbench score results/<run>              # re-score, e.g. after fixing a GT file
omrbench report results/<run>             # re-render, e.g. after adding correction times
```

### Transcribe only

```bash
omrbench transcribe                                # pipeline on every PDF of every sample
omrbench transcribe --samples anastasia --prefix_matching --force
```

Runs one engine (`--engine`, default `pipeline`) on every `*.pdf` in the selected sample folders
(same `--samples` / `--exclude` / `--prefix_matching` as `run`) and writes `<name>.musicxml` next to
`<name>.pdf`. No ground truth needed, nothing is scored, no report. PDFs that already have a
`<name>.musicxml` are skipped unless `--force`.

Several PDFs run at once (`--jobs N`, default `transcribe_jobs: 2` in `bench.yaml`), longest
first, so Audiveris on one PDF overlaps homr on another. All homr crops go to one pool of
persistent homr workers (default 8 workers x 2 ONNX threads on a 16-thread CPU, ~1 GB RAM each;
`workers` / `threads` under the `homr` settings). On the 8-core laptop this was tuned on, a
crop takes ~0.9 s instead of ~3.5 s. Measured on 4 anastasia-4 parts (25 pages): 1380 s
before, 554 s now; 3 PDFs at once or niced workers were slower. `parallel_sheets: true` (Audiveris
settings) processes the sheets of a PDF in parallel, ~2x faster, but Audiveris 5.11 has a race
there that drops symbols (`"this.parameters" is null` in its log) and kills some PDFs, so it is
off; a parallel run that exports nothing is redone serially.

`results/transcribe-<timestamp>/` then holds:

- `<sample>--<name>.musicxml`: a copy of every selected PDF's output (new or already existing)
- `combined.musicxml` / `combined.mscz`: all of them stacked as parts of one score, all starting at
  bar 1, in folder/PDF order. Parts are named after the PDF (`<folder>/<name>` if the name occurs in
  several folders; `<name> – <part>` for multi-part outputs such as split percussion). No padding:
  if parts differ in bar count, MuseScore calls the score corrupted and fills the gaps; it is then
  saved with `-f`. The `.mscz` needs the MuseScore CLI (`musescore_cli` in `bench.yaml`, `mscore` on
  PATH, or the default Windows MuseScore 4 install when running in WSL)
- `<engine>/<sample>--<name>/`: engine work dirs
- `run.log`: everything the run reported, one line each:
  `2026-10-01 10:39:12 | WARNING | anastasia-4--Horn | homr failed on page 3 system 2 (#12) ...`
  (time, level DEBUG/INFO/WARNING/ERROR, the PDF it is about, message). Every failed homr crop
  with its reason and crop image, Audiveris errors (its warnings at DEBUG), bar-number
  alignment (rest bars added, numbers ignored as misread, places where an extra bar was read),
  engine crashes with traceback. The console shows INFO and up. `omrbench run` writes one too.

Per-PDF meta: `<name>.yaml` next to `<name>.pdf`, merged over the folder's `meta.yaml` (its keys
win). Extra key `pages: "2-4,7"` (1-based; a list `[2, 3, 4]` works too) transcribes only those pages
of the PDF; the original file is not changed.

For orchestra parts the `pipeline` engine also reads these meta keys (all optional; commented
examples in `meta.example.yaml`):

| Key | Example | Effect |
|---|---|---|
| `pages` | `"2-4,7"` or `[2, 3, 4]` | Transcribe only these PDF pages (1-based). Per-PDF yaml only. |
| `skip_systems` | `[1, 2, 3, 4, 5]` | Leave these systems out entirely. **A list of system numbers, not a count**: to skip the first 5 systems, list all five. `[5]` skips only the 5th. 1-based, counted over the transcribed pages (after `pages`), so system 1 is the first system of the first selected page. Use it for the end of the previous piece at the top of a page. Skipped systems produce no bars. |
| `keep_staves` | `2` | Read only the lowest n staves of every system as one part (conductor part: vocal/reference staves above the piano). Tempo and rehearsal marks above the system are kept; lyrics and labels of dropped staves are not. |
| `transpose` | `F`, `Bb`, `Bb 8vb`, `8vb`, or `{diatonic, chromatic, octave_change}` | Transposing instrument, written to sounding pitch. The key names the pitch below written C. `8va`/`8vb` add an octave. |
| `instruments` | `[{name: Clarinet, transpose: Bb}, Flute]` | Instruments the part plays. Each entry: `name`, optional `aliases`, `transpose`, `clef` (`pitched` / `percussion`), `lower_staff`. Printed labels in the score select the instrument. A label matches an instrument when it starts with its name or an alias ("Glock - soft mallets"), or else contains a word of 4+ letters that belongs to only one listed instrument ("Sus Cymbal" -> Cymbal; "Tree" alone matches nothing when Bell Tree and Mark Tree are both listed). `lower_staff: true` names the instrument of an unlabeled lower staff: when a system has two single-line staves (e.g. Timpani above, cymbal below) and the lower one has no label yet, it starts as this instrument instead of the next unused one in the list. It has no effect on the top staff, so it is harmless on songs where the instrument shares one staff with the others. |
| `split_instruments` | `true` | One MusicXML part per instrument (each with its own transposition). Use for Reed 1/2 and percussion. Default: on for `type: drums`. |
| `doubling` | `true` | Alternative to `split_instruments`: one part that changes instrument at the labels. MuseScore 4 ignores the change on import, so add the Instrument Change by hand. |
| `small_heads` | `true` | Tell Audiveris to read small note heads (cue notes). Needed for `cues: drop`. |
| `cues` | `keep` (default) / `drop` | `drop` turns cue-size notes into rests and removes the `(Clar)` label above them. |

Combine as needed, for example a horn part whose first page starts with the tail of the
previous number:

```yaml
pages: "1-3"
transpose: F
skip_systems: [1, 2]      # the first two systems of page 1
cues: drop
small_heads: true
```

### Song folders from a workbook (`gen-meta`)

For a show transcribed song by song from the same full-book parts, keep everything in
`data/_<show>/` (folders starting with `_` are not samples):

```
data/_anastasia/show.yaml    constants: meta.yaml block, per-part defaults, instrument library
data/_anastasia/songs.xlsx   one sheet per song (sheet name = song id, B1 = title)
data/_anastasia/pdfs/        the full-book PDFs
```

```bash
omrbench gen-meta data/_anastasia/show.yaml --dry-run      # show what would change
omrbench gen-meta data/_anastasia/show.yaml --songs 5      # write data/anastasia-5/
```

Each song sheet has a header row `file | pages | skip | instruments | extra | notes`, one row per
PDF. The generator writes `meta.yaml` and one `<file>.yaml` per row into the song folder and copies
the PDFs there. Changed files are shown as a diff, then overwritten: the workbook is the source of
truth.

| Column | Example | Becomes |
|---|---|---|
| `pages` | `11-16` | `pages`. Empty: part not in this song, no yaml, no PDF copied. Also leave it empty for a TACET part when the show uses `cues: drop` (it would come out as rests only). |
| `skip` | `1-3` | `skip_systems: [1, 2, 3]` |
| `instruments` | `Clarinet, Flute` | Names looked up in the `instruments` library of `show.yaml` (transpose, aliases, clef). Several on a non-drums part: `split_instruments: true`. A single one only sets the part's `transpose`. Keys in brackets apply to this song only and win over the library: `Triangle (lower_staff)` (a bare key means `true`), `Clarinet (transpose: A)`. Marking one instrument `lower_staff` takes it off every other instrument of that song. |
| `extra` | `chord_names: false` | Raw YAML keys, win over everything. `lyrics: null` drops a part default. |
| `notes` | `Bassoon` | Ignored. |

New song: duplicate the previous sheet in Excel, rename it, set the title and pages. The cells
are formatted as Text so Excel keeps `5-9` from becoming a date (the generator stops with an
error if that happens anyway).

Engines run one at a time so the resource numbers are clean. Scoring runs in parallel (`scoring.jobs`). A 3-page piano score takes roughly 1–2 minutes per engine to score, mostly in musicdiff.

## What gets measured

| Metric | Source | Meaning |
|---|---|---|
| OMR-NED `all` / `notes` | musicdiff | symbol edit distance / (GT + output symbols); `notes` = notes and rests only, which is fairer to homr/oemer, since they don't read lyrics or dynamics |
| TEDn | OLiMPiC (vendored, MIT) | tree edit distance on MusicXML; large parts are scored measure by measure after alignment |
| Per-element P/R/F1 | own | notes, pitch, rhythm, rests, clefs, keys, times, dynamics, hairpins, articulations, slurs, ties, lyrics, words (tempo/expression text), metronome; LCS-matched per staff |
| Measure error rate | own | share of output measures whose notes/rests differ from the aligned GT measure |
| Flag precision/recall | own | how well `validator` (duration ≠ time signature) and Audiveris `.omr` abnormal/excess measures predict the wrong measures |
| Wall / CPU / RAM / GPU | psutil + NVML | whole process tree, sampled every 0.1 s; also per page |
| Correction time | you | `correction_minutes` in `meta.yaml`; the report applies the 70 % rule |

Outputs go to `results/<run>/`:
- `report.md`
- `scores.json`, with every number plus the flagged measures and the per-category musicdiff breakdown
- `metrics.csv`
- `<engine>/<sample>/output.musicxml`, which you can open in MuseScore to time corrections
- `engine.log`

## Known engine behaviour

- **Audiveris** OCRs the part label on every system. If the label changes (for example "Soprano" becomes "S.", or an OCR slip turns "Voice" into "Voico"), it opens a new part. The Structure table in the report shows this. The fix is post-processing with the known instrument list, not the benchmark.
- **oemer** handles only 1–2 staves per system (it asserts on choir and orchestral systems). It takes about 5 min of wall time and about 60 CPU-min per 300-dpi page on a laptop CPU. It needs the pinned old `numpy`, `opencv` and `onnxruntime` that `setup.sh` installs. Because of the cost it is disabled in `bench.yaml`; run it with `--engines oemer` (or set `enabled: true`).
- **homr** reads notes only: no lyrics, dynamics or text. The `notes` OMR-NED variant is the fair comparison for it.
- **GPU:** `--gpu` and `device: cuda` only help with an NVIDIA GPU that is visible inside WSL (`nvidia-smi` works). AMD iGPUs (Radeon 780M, for example) can't be used from WSL by these engines, so they run on CPU.

## The `pipeline` engine

One engine that combines the others (`omrbench/pipeline/`); its runtime is the sum of its steps.

1. **Audiveris** (with the `meta.yaml` switches) gives the page layout: systems, staves, bar
   positions, the parts of each system, and all OCR'd text with positions (`.omr` project).
2. **homr on crops:** every staff group (a single staff, or a piano's grand staff) of every
   system is cut out and read by homr. That makes homr usable on vocal scores and condensed
   parts, which it cannot read as whole pages. homr sometimes fails on one crop and works on
   a slightly different one, so failed crops are retried with other margins (`crop_margins`).
3. **Bar count per system** by vote between Audiveris and the homr crops.
4. **Bar choice:** per staff group and bar, the preferred engine's bar if its voices fill the
   time signature, else the other one. `prefer: auto` puts homr first on scans and Audiveris
   first on vector PDFs (it is near perfect there and, unlike homr, has ties). Percussion
   staves always prefer Audiveris (homr reads them as pitched).
5. **Signatures:** time signature from homr where printed (Audiveris misreads 4/4 as 2/4),
   clef and key from the group's preferred engine. Parts not printed in a system follow its key.
6. **Directions and text:** dynamics, hairpins and tempo from Audiveris. Words are rebuilt
   from the positioned OCR text, because Audiveris files bar numbers as lyrics and expression
   text as page credits. Header and footer text become credits. Tempo and expression marks go
   to the top part (the full-score convention), labels and dialogue stay on their staff.
   `text_onset: bar` puts words at the start of their bar, as in the ground truths here.
7. **Multi-measure rests** are expanded from the printed evidence: the count above the rest,
   printed ranges ("15-17"), and gaps in the printed bar numbers. Systems of rests only are
   rebuilt from that evidence (neither engine finds their barlines reliably). A tiny bar at
   the end of a page (page-turn reminder) is dropped. Ranges over 99 bars are OCR slips and
   ignored; a homr rest count the printed numbers leave no room for is not used.
   **Bar numbers line up with the printed ones** (`align_bar_numbers: true`): wherever the
   printed numbers jump ahead of the output, rest bars are inserted, so output bar n is
   printed bar n in every part. A cut mark `[to] 97` (or `[to 16]`) printed at a barline means
   the bar there is bar 97 and the bars before it were cut from this part: they become rests.
   Without a cut mark the rests go after the last rest bar before the number (an unread
   multi-rest count), else right before it. Lettered bars added in a revision (`131A`,
   `[to] 132C`) count as bars of their own. OCR misreads numbers, so the step function that
   agrees with most numbers is used; a single stray number shifts nothing. Bars are never
   removed, except empty bars before printed bar 1. Where the output has more bars than the
   numbers say (an extra bar was read), `run.log` says where.
8. **Vocal scores** (`type: piano_reduction`): the lowest two staves of every system are the
   piano, each staff above it a voice. A voice staff belongs to the singer whose label was
   printed last on it ("DMITRY:", "FIRST WOMAN:", "ALL (NO DMITRY):"), carried over to the
   staff at the same position in later systems; a label inside a bar splits the bar there.
   Every distinct label becomes a part. Lyrics, dynamics and hairpins are placed from their
   position on the page (Audiveris' MusicXML hangs piano dynamics on voices and joins
   hairpins to far-away stops): a syllable goes to the note above it, a mark between the
   piano staves is the piano's, one above a vocal staff that voice's. Dialogue (a speaker
   label followed by prose: "GLEB: (cont.)" / "We hear you, ...") is dropped, or with
   `spoken_text: text` kept as one text over the voices. Stage directions ("(VLAD POPOV
   enters.)") go to the voices. The piano gets no sung or spoken text. `transcribe` writes
   `<name> - Voices.musicxml` and `<name> - Piano.musicxml`; tempo and other system text
   is in both.
9. **Clean-up for MuseScore** (all scores): eighths and shorter without beams are beamed by
   beat (`auto_beam`), hairpins over `max_wedge_bars` (2) bars are dropped, graces whose
   flag was missed (read as quarters) get the piece's grace type, half/whole "graces" are
   dropped, articulations are kept once per chord.
10. **Percussion split:** for `type: drums` (or `split_instruments: true`), a shared staff is
   split into one part per instrument at the printed labels ("Timpani", "Bell Tree", ...).
   Instrument names come from `instruments:` in `meta.yaml`, or else from the header lines that
   also appear as labels. A clef change without a readable label switches to the next listed
   instrument.

`<run>/pipeline/<sample>/pipeline.json` records what was taken from where (bars per source,
multi-rest expansions, alignment rest bars, crops that failed); `<run>/run.log` has the details.

## Layout

```
omrbench/
  cli.py  runner.py  scoring.py  report.py  config.py  dataset.py
  monitor.py        resource measurement
  musicxml.py       loading, page merging, per-staff event extraction
  rasterize.py      PDF -> PNG (PyMuPDF)
  engines/          audiveris.py  pagewise.py (homr, oemer)  external.py
  pipeline/         layout.py (.omr)  bars.py  text.py  assemble.py  engine.py
  metrics/          omrned.py  tedn.py  elements.py  flags.py  _olimpic_tedn.py
bench.yaml          engines, dpi, device, timeouts, scoring options
```

To add an engine, subclass `engines.base.Engine` (or `PagewiseEngine` for one-image CLIs), register it in `engines/__init__.py:KINDS` and list it in `bench.yaml`.
