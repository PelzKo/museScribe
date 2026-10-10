# museScribe (`omrbench`)

Transcribes printed sheet music (scanned orchestra parts, vocal scores) to MusicXML / MuseScore,
and benchmarks the result against hand-corrected ground truth.

- **Transcribe** a show song by song: `omrbench transcribe anastasia --songs 1`
- **Benchmark** it against MuseScore truth scores: `omrbench bench anastasia`

The default engine, `pipeline`, combines Audiveris (layout, text, OCR) with homr on cropped
staff groups plus repairs ([docs/pipeline.md](docs/pipeline.md)). Audiveris, homr and oemer can
also be compared on their own ([docs/engine-benchmark.md](docs/engine-benchmark.md)).

## Setup (WSL / Ubuntu)

```bash
bash setup.sh            # add --gpu for onnxruntime-gpu (needs an NVIDIA GPU visible in WSL)
source ~/.local/share/omrbench/env.sh
omrbench doctor          # engines, GPU, shows and samples found
```

`setup.sh` needs no root. It puts everything under `~/.local/share/omrbench` (venvs on `/mnt/c` are slow):
- a harness venv
- a separate venv for each of homr and oemer (their dependencies conflict)
- Audiveris, unpacked from the official `.deb` with its bundled JRE
- Tesseract data for `deu lat eng ita`, from the full `tessdata` repo, since Audiveris needs the legacy models
- the homr and oemer model downloads, so they don't count towards the first run's time

Engine versions: Audiveris 5.11.0 and homr 0.7.0 (both pinned in `setup.sh`; newer homr
changes its API and output, so re-run `omrbench bench` after bumping it), oemer 0.1.8
(unmaintained since 2024, off by default). MuseScore 4 is needed for `.mscz` output and to
read truth `.mscz` files (`musescore_cli` in `bench.yaml`, `mscore` on PATH, or the default
Windows install when running in WSL).

## Data and results

`data/` is input only: the tool never writes there. Everything it makes goes to `results/`.

```
data/<show>/                 a show (docs/shows.md)
  show.yaml                  constants: meta, per-part defaults, instrument library
  songs.xlsx                 one sheet per song: parts, pages, instruments, truth mapping
  pdfs/                      full-book PDFs, read in place
  truth/                     ground-truth MuseScore full scores
data/samples/<sample>/       single-PDF samples for the engine benchmark
results/<show>/<song>/       latest transcription of every part + combined.mscz + manifest.json
results/<show>/runs/<ts>/    one transcribe run: its outputs, work dirs, run.log
results/<show>/bench/<ts>/   omrbench bench: report.md, scores.json, metrics.csv
results/samples/...          the same for samples; bench/<ts>/ = omrbench run
results/cache/               truth exports, generated sample GT
```

## Quickstart

```bash
omrbench check anastasia                       # validate songs.xlsx against the PDFs and truth
omrbench transcribe anastasia --songs 1,2      # -> results/anastasia/1/, results/anastasia/2/
omrbench bench anastasia                       # note F1 of the latest outputs vs the truth
omrbench bench anastasia --songs 1 --transcribe --force   # after changing the pipeline
```

Open `results/<show>/<song>/combined.mscz` in MuseScore to see a whole song. A part is only
transcribed again when its PDF, workbook row or engine settings changed; use `--force` after
changing the code. `--keep-awake` keeps Windows from sleeping during long runs.

**New song:** duplicate the previous sheet in `songs.xlsx`, rename it to the song id, set
title, pages, skipped systems and instruments, then `omrbench check anastasia --songs <id> -v`.
To benchmark it, put the corrected MuseScore score in `truth/`, link it in B2 and fill the
`truth` column ([docs/shows.md](docs/shows.md#benchmark-against-the-truth-bench)).

**New show:** a folder `data/<show>/` with `show.yaml` (copy one), `songs.xlsx` and `pdfs/`.

## Commands

| Command | Does |
|---|---|
| `omrbench doctor` | check engines, GPU, shows, samples |
| `omrbench check SHOW [--songs] [-v] [--export DIR]` | validate the workbook, show every part's resolved meta |
| `omrbench transcribe SHOW [--songs] [--parts] [--force] [--jobs N] [--keep-awake]` | transcribe songs to `results/SHOW/<song>/` |
| `omrbench bench SHOW [--songs] [--run TS] [--transcribe] [--full]` | score against the truth |
| `omrbench transcribe [--samples] [--exclude] [--prefix_matching]` | transcribe every PDF of `data/samples/*` |
| `omrbench run / score / report / new-sample / demo` | engine benchmark on samples ([docs](docs/engine-benchmark.md)) |

## Docs

- [docs/shows.md](docs/shows.md): workbook format, transcribe outputs and logs, truth mapping and metrics
- [docs/pipeline.md](docs/pipeline.md): how the pipeline engine works, all meta keys
- [docs/engine-benchmark.md](docs/engine-benchmark.md): samples, `omrbench run`, metrics, engine quirks
- [docs/restructure-plan.md](docs/restructure-plan.md): the 2026-10 restructure

## Code layout

```
omrbench/
  cli.py  runner.py  scoring.py  report.py  config.py  dataset.py
  project.py        show = show.yaml + songs.xlsx -> parts with their meta; `check`
  transcribe.py     transcribe a show's songs / the samples into results/
  bench.py  truth.py  bench a show against its MuseScore truth
  monitor.py        resource measurement
  musicxml.py       loading, page merging, per-staff event extraction
  rasterize.py      PDF -> PNG (PyMuPDF)
  engines/          audiveris.py  pagewise.py (homr, oemer)
  pipeline/         layout.py (.omr)  bars.py  text.py  assemble.py  engine.py
  metrics/          notef1.py  omrned.py  tedn.py  elements.py  flags.py  _olimpic_tedn.py
bench.yaml          engines, dpi, device, timeouts, scoring options
```

To add an engine, subclass `engines.base.Engine` (or `PagewiseEngine` for one-image CLIs), register it in `engines/__init__.py:KINDS` and list it in `bench.yaml`.
