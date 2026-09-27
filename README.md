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
   the end of a page (page-turn reminder) is dropped.
8. **Percussion split:** for `type: drums` (or `split_instruments: true`), a shared staff is
   split into one part per instrument at the printed labels ("Timpani", "Bell Tree", ...).
   Instrument names come from `instruments:` in `meta.yaml`, or else from the header lines that
   also appear as labels. A clef change without a readable label switches to the next listed
   instrument.

`<run>/pipeline/<sample>/pipeline.json` records what was taken from where (bars per source,
multi-rest expansions, crops that failed).

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
