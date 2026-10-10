# Engine benchmark on samples (`run`)

Runs several OMR engines on single-PDF samples, scores their MusicXML against hand-corrected
ground truth, measures runtime / CPU / memory / GPU and writes a Markdown report. Implements
the evaluation protocol (section 12) from the OMR research notes.

| Engine | How it runs | Notes |
|---|---|---|
| `audiveris` | Audiveris 5.11 batch CLI (`-batch -transcribe -export`) | stock settings |
| `audiveris-meta` | same, with switches from `meta.yaml` | drums, OCR languages, small heads, ... |
| `homr` | homr 0.7.0 (pinned, `HOMR_VERSION` in `setup.sh`), one call per page | CPU or CUDA |
| `oemer` | oemer 0.1.8, `oemer page.png`, one call per page | CPU or CUDA; disabled by default; unmaintained since 2024 |
| `pipeline` | Audiveris layout + homr per cropped staff group + repairs | see below |
| `clarity` | Clarity-OMR (commit `c6bb8a4`): whole PDF, YOLO staves + DaViT tokens -> MusicXML | piano-tuned; ~20 s per staff on CPU |
| `transcoda` | Transcoda 59M (HF revision `b529f8a`): full page -> `**kern` | pianoform; ~70 s/page on CPU |
| `smt-fp` | Sheet Music Transformer, `PRAIG/smt-fp-grandstaff`: full page -> bekern | pianoform; slow on CPU (no KV cache); the Mozarteum and Polish variants are gated on HF |
| `mozart` | Mozart (commit `a51c9d7`), classic CV | treble staves only, no rests or barlines; a floor, not a contender |

Every engine is a subprocess from the same harness, measured the same way. All of them run in Docker
(`omrbench images build`); the four above run only there. Their text outputs are converted in the
harness (`omrbench/convert/`: `kern.py` repairs bare or inconsistent model output, `mozart.py`).
Pianoform engines still run on every sample, so the matrix is complete.

## Samples

```bash
omrbench new-sample choir-01      # creates data/samples/choir-01/ with meta.yaml template
```

```
data/samples/choir-01/
  input.pdf          2-3 pages, scan or phone photo
  gt.musicxml        hand-corrected in MuseScore (File > Export > MusicXML); gt.mxl/gt.mscz also OK
  meta.yaml          type (choir|piano|piano_reduction|part|orchestral|drums|other), languages, switches
```

The ground truth must cover exactly the pages in `input.pdf`. See `meta.example.yaml` for all keys.

To smoke-test the setup, `omrbench demo` engraves two corpus pieces with Verovio into
`data/samples/demo-*`. Engraved PDFs are much easier than scans, so don't draw conclusions from them.

## Running

```bash
omrbench run                              # all engines, all samples -> results/samples/bench/<ts>/report.md
omrbench run --engines audiveris,homr --samples choir-01
omrbench run --exclude demo --prefix_matching   # skip every demo-* sample
omrbench run --resume 20260927-1300       # re-use finished engine outputs, retry failures
omrbench score results/samples/bench/<run>            # re-score, e.g. after fixing a GT file
omrbench report results/samples/bench/<run>            # re-render, e.g. after editing sample meta
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

Outputs go to `results/samples/bench/<run>/`:
- `report.md`
- `scores.json`, with every number plus the flagged measures and the per-category musicdiff breakdown
- `metrics.csv`
- `<engine>/<sample>/output.musicxml`, which you can open in MuseScore to inspect the output
- `engine.log`

## Known engine behaviour

- **Audiveris** OCRs the part label on every system. If the label changes (for example "Soprano" becomes "S.", or an OCR slip turns "Voice" into "Voico"), it opens a new part. The Structure table in the report shows this. The fix is post-processing with the known instrument list, not the benchmark.
- **oemer** handles only 1–2 staves per system (it asserts on choir and orchestral systems). It takes about 5 min of wall time and about 60 CPU-min per 300-dpi page on a laptop CPU. It needs pinned old `numpy`, `opencv` and `onnxruntime`; the `omrbench/oemer:0.1.8` image has them. Because of the cost it is disabled in `bench.yaml`; run it with `--engines oemer` (or set `enabled: true`).
- **homr** reads notes only: no lyrics, dynamics or text. The `notes` OMR-NED variant is the fair comparison for it.
- **GPU:** `device: auto` (default) picks `cuda` only when an NVIDIA GPU is visible inside WSL (`nvidia-smi` works), else `cpu`. AMD iGPUs (Radeon 780M, for example) can't be used from WSL by these engines, so they run on CPU; engines marked `requires_gpu: true` are skipped there.
