# museScribe – OMR engine benchmark (`omrbench`)

Runs several OMR engines on your own sample PDFs, scores their MusicXML against hand-corrected ground truth, measures runtime / CPU / memory / GPU and writes a Markdown report. Implements the evaluation protocol (section 12) from the OMR research notes.

| Engine | How it runs | Notes |
|---|---|---|
| `audiveris` | Audiveris 5.11 batch CLI (`-batch -transcribe -export -save`) | stock settings |
| `audiveris-meta` | same, with switches from `meta.yaml` | drums, OCR languages, small heads, ... |
| `homr` | `homr page.png`, one call per page | CPU or CUDA |
| `oemer` | `oemer page.png`, one call per page | CPU or CUDA |
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
  meta.yaml          type (choir|piano|part|orchestral|drums|other), languages, switches, correction times
  external/          optional: soundslice.musicxml, playscore.mxl, ...
```

The ground truth must cover exactly the pages in `input.pdf`. See `meta.example.yaml` for all keys.

## Running

```bash
omrbench run                              # all engines, all samples -> results/<timestamp>/report.md
omrbench run --engines audiveris,homr --samples choir-01
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

- **Audiveris** OCRs the part label on every system. If the label changes (for example "Soprano" becomes "S.", or an OCR slip turns "Voice" into "Voico"), it opens a new part. The Structure table in the report shows this. The fix is post-processing from `meta.yaml` instruments, not the benchmark.
- **oemer** handles only 1–2 staves per system (it asserts on choir and orchestral systems). It takes about 5 min of wall time and about 60 CPU-min per 300-dpi page on a laptop CPU. It needs the pinned old `numpy`, `opencv` and `onnxruntime` that `setup.sh` installs.
- **homr** reads notes only: no lyrics, dynamics or text. The `notes` OMR-NED variant is the fair comparison for it.
- **GPU:** `--gpu` and `device: cuda` only help with an NVIDIA GPU that is visible inside WSL (`nvidia-smi` works). AMD iGPUs (Radeon 780M, for example) can't be used from WSL by these engines, so they run on CPU.

## Layout

```
omrbench/
  cli.py  runner.py  scoring.py  report.py  config.py  dataset.py
  monitor.py        resource measurement
  musicxml.py       loading, page merging, per-staff event extraction
  rasterize.py      PDF -> PNG (PyMuPDF)
  engines/          audiveris.py  pagewise.py (homr, oemer)  external.py
  metrics/          omrned.py  tedn.py  elements.py  flags.py  _olimpic_tedn.py
bench.yaml          engines, dpi, device, timeouts, scoring options
```

To add an engine, subclass `engines.base.Engine` (or `PagewiseEngine` for one-image CLIs), register it in `engines/__init__.py:KINDS` and list it in `bench.yaml`.
