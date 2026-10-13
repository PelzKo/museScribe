# Plan: many OMR engines, components, routing + ensemble

## Context
Goal: benchmark as many free, local OMR tools as possible, individually and as components. Find out which is best per score type (orchestral, part, piano_reduction, choir/vocal, drums) and per element (notes, rhythm, text, dynamics…). Then build a pipeline that routes and combines them.

Constraints from the user:
- Zero budget, local only. No cloud, paid or commercial tools, no `external/` dir. Non-commercial use, so GPL/AGPL/CC-BY-SA/NC are fine.
- Runs on the Windows PC with RTX 2070 SUPER (WSL2 + Docker Desktop). Turing GPU means fp16, no bf16, no FlashAttention-2.
- **Everything in Docker**, including Audiveris and homr.
- GT = MusicXML only. Drop metrics needing extra user input (`correction_minutes`, 70 % rule). User provides GT samples of all score types.
- PDFs mixed scan/vector. Detect the type, use the text layer on vector pages. Native vector-glyph parsing → `docs/TODO.md` only.
- Local VLM: OCR component only, not a full engine.
- Dropped: LEGATO (Llama 3.2 Vision EU licence), ijdar-e2e-pianoform (no weights, superseded by SMT), student CV repos except Mozart, wrappers/forks, moonlight, handwritten/mensural tools.

Current state (from exploration):
- Engine registry `omrbench/engines/__init__.py:6-21` (`KINDS`, `build()`), base `engines/base.py` (`Engine`, `EngineResult`, `run()`).
- Subprocess monitor `omrbench/monitor.py:109` `run_monitored`.
- Pipeline `omrbench/pipeline/engine.py`: Audiveris layout → `_crop_jobs` (:119) → `_homr_batch` (:155), the only recognizer call → `assemble()` (assemble.py), which hard-codes `"homr"` source labels (:337, :357-363, `plan_systems` :205, `_vote` :163, `_multirest_counts` :610, `expand_multirests` :827, `Stats.homr_crops_*`).
- homr pool: `engines/homr_pool.py` (JSON-lines over stdin/stdout to `_homr_worker.py`).
- Rasterize `omrbench/rasterize.py` (`is_scan()` :31). OCR `pipeline/ocr.py` (Tesseract).
- No tests, no Docker.

## Phase 0 — Cleanup
- Remove `external`. Delete `engines/external.py` and its refs in `engines/__init__.py:3,10`, `config.py:38-41`, `dataset.py:11,44-49`, `runner.py:90,96,172-173`, `cli.py:60,78,82`, `transcribe.py:298,302-303`, `report.py:186`, `base.py:19`, `bench.yaml:34-36`, README, docs, pyproject description.
- Remove `correction_minutes` and the 70 % rule: `dataset.py:51`, `report.py:374-415`, `bench.yaml:46`, `meta.example.yaml`.
- Keep `audiveris_flags`: it uses the engine's own `.omr`, no extra input.

## Phase 1 — Docker infrastructure (foundation for everything)
- `docker/base/Dockerfile`: slim Python base plus `omr-run`, a small in-container monitor (port of `monitor.py`: psutil RSS/CPU, pynvml GPU). It wraps the adapter command and writes `stats.json`. Host-side sampling can't see into the Docker Desktop VM, hence in-container.
- `docker/<engine>/Dockerfile` + `adapter.py` per engine. Uniform contract:
  `adapter page --in /work/in/*.png --out /work/out [--device cuda|cpu]` and `adapter crops --in ... --out ...`
  It writes one `<stem>.<fmt>` per input (musicxml / kern / abc / tokens) plus `adapter.json` (format, versions, errors per input).
- **Long-lived mode** for hot paths (homr, other crop recognizers): `docker run -i` speaking the same JSON-lines protocol as `_homr_worker.py`. `HomrPool` becomes a generic `ContainerPool`.
- `omrbench/engines/docker.py`: `DockerEngine(Engine)` with `image`, `granularity` (page|staff|grandstaff|group), `output_format` and `gpu`. It builds `docker run --rm [--gpus all] -v workdir:/work -v omrbench-models:/models`, reads `stats.json` into `RunStats`, then calls the converter.
- Model weights go in the named volume `omrbench-models`, downloaded on first run or at build time when the licence allows.
- Audiveris image: JRE + Audiveris 5.11 + tessdata (logic from `setup.sh:50-74`). homr image: homr 0.7.0, onnxruntime-gpu. oemer image: its pinned stack (`setup.sh:91-113`).
- The existing `Audiveris`, `Homr` and `Oemer` classes switch to the Docker runner. Pipeline is unchanged except it now gets its sub-engines through Docker.
- CLI:
  - `omrbench images build [names] | list`
  - `omrbench doctor` checks docker, `--gpus` (runs `nvidia-smi` in a CUDA base image), image presence and the models volume.
- `setup.sh`: reduced to the harness venv + `omrbench images build`.
- Docs: keep the repo on the WSL ext4 filesystem on the PC, not `/mnt/c` (I/O).

## Phase 2 — Converters (`omrbench/convert/`)
Everything is normalised to MusicXML in the harness, so scoring is uniform.
- `kern.py`: **kern / **bekern → MusicXML. music21 first, verovio humdrum→MEI→music21 as fallback. SMT and Transcoda need this, and failure rates are high, so the converter strips or repairs bad tokens.
- `lmx.py`: Zeus writes MusicXML itself; just pass through.
- `semantic.py`: PrIMuS semantic tokens (tf-end-to-end) and Polyphonic-TrOMR tokens (`note-C4_eighth|…`) → music21 stream → MusicXML.
- `mozart.py`: Mozart's text format (`{[ \meter… e1/4 {e1/4,g1/4} ]}`) → MusicXML.
- `tests/` (new, pytest): one golden fixture per converter, plus an adapter contract test (dummy image) and `pdfkind` on synthetic PDFs (a demo-engraved vector PDF vs. the same page rasterised into a PDF).

## Phase 3 — PDF kind detection + text layer
- `omrbench/pdfkind.py`: per page → `scan | scan+ocr | vector | vector-outlined`, using PyMuPDF:
  - image coverage ≥ 90 % → scan (an invisible render-mode-3 text layer → `scan+ocr`, and that text is ignored)
  - `len(get_drawings())`
  - music fonts in `get_fonts()` (Bravura, Leland, Emmentaler, MScore, Opus, Maestro, Petrucci, Gonville…)
  - SMuFL code points in `get_text("rawdict")`
  - Replaces `rasterize.is_scan`.
- Vector pages:
  - Render at higher dpi (configurable, default 400).
  - Extract positioned text spans (bar numbers, part labels, rehearsal marks, tempo words) into the same structure `ocr.read_pages` produces, so `ocr.supplement` (`pipeline/ocr.py:147`) uses exact text instead of Tesseract.
  - `prefer: auto` (pipeline/engine.py:361) keys off pdfkind.
- Report: a pdfkind column per sample, so results can be split scan vs vector.
- `docs/TODO.md`: idea for a native vector parser. Read SMuFL glyphs + drawn paths (staff lines, stems, beams) via PyMuPDF and rebuild notation geometrically, for near-exact results on engraved PDFs. Notes on fonts, outlined-glyph exporters, prior art.

## Phase 4 — Page-level engines (each a Docker image + adapter)
| Engine | Source | Output | Scope / note |
|---|---|---|---|
| `clarity` | clquwu/Clarity-OMR (GPL-3, CC-BY-SA weights) | MusicXML | YOLO staff det + DaViT; piano-tuned |
| `transcoda` | btrkeks/Transcoda (AGPL, CC-BY-4.0, 59M) | kern | full-page pianoform, best paper numbers |
| `smt-fp` | antoniorv6/SMT, PRAIG/smt-fp-{grandstaff,mozarteum,polish-scores} (MIT) | bekern | full-page pianoform; variant = config |
| `mozart` | aashrafh/Mozart (Apache, py3.8) | own text | classic-CV floor |
| `audiveris`, `audiveris-meta`, `homr`, `oemer` | existing | MusicXML | moved to Docker in P1 |

- Pianoform-only engines still run on all samples, as the user wants the full matrix. The report marks them "out of scope" for non-pianoform types instead of hiding them.
- `bench.yaml`: one entry per engine/variant with `granularity`, `scope`, `gpu`.

## Phase 5 — Pluggable crop recognizer in the pipeline
- `omrbench/pipeline/recognizer.py`: `Recognizer` protocol, `recognize(crops: list[CropJob]) -> dict[key, ET.Element|None]` (batch, long-lived container). Each recognizer declares `granularity`.
- `_crop_jobs` (engine.py:119) emits crops at the granularity the recognizer asks for:
  - `group` (current)
  - `grandstaff` (2-staff braced groups only)
  - `staff` (single staves; the per-staff results are merged back into one group root with N staves)
- Groups a recognizer can't handle fall back to a configured `fallback` recognizer (default homr).
- **Rename `homr` → `crop` source in assemble.py**, generic on source name: `part_bars`, `prefer`, `plan_systems`, `_vote`, `_multirest_counts`, `expand_multirests`, `Stats.*_crops_*`, and the `reassemble` glob (:444).
- Must be a **no-behaviour-change refactor for homr**: verify with `reassemble()` on Anastasia 1/2/4A, same note F1 as before.
- Recognizers:
  - `homr` (group)
  - `zeus` OLiMPiC/Zeus (staff, grandstaff; TF 2.12 / py3.10; writes MusicXML)
  - `smt-sys` smt-grandstaff / camera-grandstaff (grandstaff)
  - `transcoda` (grandstaff/group)
  - `tromr` Polyphonic-TrOMR (staff, torch 1.11 pins)
  - `tfe2e` tf-end-to-end semantic model (staff, mono; TF1 compat)
  - `clarity` (staff recognition stage only, if its API allows; otherwise page-only)
- Bench entries: `pipeline-<recognizer>` (type pipeline, `recognizer: zeus`, `fallback: homr`).

## Phase 6 — Component benchmarks (`omrbench components`)
Only metrics derivable from GT MusicXML + PDF.
- **Layout**: providers `audiveris` (.omr via `layout.load`), `ola-yolo` (v-dvorak/omr-layout-analysis v2.0, Ultralytics), `measuredetector` (TF1.13 image, frozen .pb). Metrics:
  - total measure count vs GT
  - staves per system vs GT part/staff count
  - per-page system count consistency
  - downstream: pipeline note F1 when this provider's boxes drive the crops. Needs a `Layout` adapter producing `Page`/`System`/`Staff` (layout.py:17-134) from YOLO boxes; Audiveris stays the source for part labels/text.
- **Text/OCR**: providers `tesseract` (existing), `paddleocr`, `doctr`, `easyocr`, `qwen-vl` (Qwen2.5-VL-7B Q4 GGUF via llama.cpp server image, ~6 GB VRAM; prompt per crop), `pdftext` (vector pages). Same crops (above-staff bar-number region, left part-label region). Metrics:
  - bar numbers: read value ∈ GT measure numbers and monotonic per page; downstream bar-alignment error
  - part labels: fuzzy match to GT part names
  - rehearsal marks: set match with GT `<rehearsal>`
- Results to `results/samples/components/<ts>/report.md` + json.
- **Recognizer comparison without homr tuning** (user request 2026-10-13). The `pipeline` repairs were tuned on
  homr output: `_vote` (assemble.py) breaks a 1-vs-1 tie between Audiveris and the crop reader in favour of the crop
  reader, homr's courtesy-signature rest bar is dropped, multirests and bar numbers are fixed around homr's habits.
  Zeus lost on full Anastasia mainly through this: one Zeus crop looped into 177 bars (Song 1 Violin 2, system 5),
  and the tie rule accepted it. So each recognizer is benchmarked at three levels on the same samples/songs:
  1. **raw**: the engine alone on the page (`homr`, `audiveris`, `oemer`, `clarity`, ... as page engines). Zeus and
     smt-sys have no page mode, so for them level 2 is the lowest.
  2. **plain crops**: same Audiveris layout and crops for every reader, crop measures concatenated per part, no vote,
     no repairs (a `repairs: false` pipeline switch).
  3. **full pipeline**: as now (`pipeline`, `pipeline-<recognizer>`).
  The level 2 → 3 gain shows how much of homr's lead is tuning. Generic guards that help every reader
  (e.g. reject a crop with more bars than 2x the Audiveris stacks) go into level 3 for all readers.
- **Runtime and memory in every benchmark** (user request 2026-10-13). `omrbench run` reports already show runtime per
  page and peak RSS, but `omrbench bench` (shows) does not, and long-lived workers (homr pool, Zeus/SMT/Transcoda
  batch containers) only report host-side numbers. Goal: per engine and part, wall time, CPU time, peak RAM
  (including container processes, e.g. `docker stats` or cgroup `memory.peak`) and peak VRAM (NVML), in
  `report.md` and the JSON, and a per-engine total in the summary table.

## Phase 7 — Routing + ensemble
- **Matrix report**: after `run`, aggregate per (score type × pdfkind × element metric) → best engine/recognizer, written to `results/samples/bench/<run>/routing.yaml`. Element metrics come from `metrics/elements.py`: notes, pitch, rhythm, rests, clefs, keys, dynamics, lyrics, words.
- **`combo` engine** (`omrbench/pipeline/combo.py`):
  - Runs layout + N crop recognizers (+ optionally page engines aligned via measure alignment from scoring).
  - Per (system, group, measure) candidates are scored by validator (duration = time sig), agreement (medoid by note-set similarity) and prior weights from `routing.yaml` for that score type. This generalises the existing Audiveris/homr `_vote` (assemble.py:163).
  - Element routing: text, dynamics and lyrics from the routed source (Audiveris/pdftext/best OCR); notes from the vote winner.
  - Then the existing post-processing (show.yaml instruments, transpositions, cue/unison dedup, key respelling).
- Transcribe: `--engine combo --routing <routing.yaml>`. Score type comes from sample `meta.yaml type` / show part config, with auto fallback (2-staff braced → piano_reduction, lyrics → choir, percussion clef → drums).
- Leakage guard: report combo scores with leave-one-sample-out routing weights, so its benchmark number is honest.

## Order / deliverable checkpoints
P0 → P1 (Audiveris+homr in Docker, identical scores to native) → P2+P3 → P4 (one engine at a time: clarity, transcoda, smt-fp, mozart) → P5 (refactor first, then zeus, smt-sys, transcoda, tromr, tfe2e) → P6 → P7. Each engine lands with image, adapter, converter test and bench.yaml entry, and is run on demo + one real sample before moving on.

## Critical files
- New:
  - `docker/**`
  - `omrbench/engines/docker.py`
  - `omrbench/convert/*`
  - `omrbench/pdfkind.py`
  - `omrbench/pipeline/recognizer.py`
  - `omrbench/pipeline/combo.py`
  - `omrbench/components.py`
  - `tests/`
  - `docs/TODO.md`
  - `docs/engines.md` (per-engine licence/scope table)
- Modified:
  - `engines/__init__.py`, `engines/base.py`, `engines/audiveris.py`, `engines/pagewise.py`, `engines/homr_pool.py`
  - `pipeline/engine.py`, `pipeline/assemble.py`, `pipeline/ocr.py`
  - `rasterize.py`, `runner.py`, `report.py`, `config.py`, `dataset.py`, `cli.py`, `transcribe.py`
  - `bench.yaml`, `setup.sh`, README/docs

## Verification
1. `omrbench doctor` on the PC: docker OK, `--gpus` OK (nvidia-smi inside a container), all images present.
2. `pytest tests/`: converters, pdfkind, adapter contract.
3. Docker parity: `omrbench run --engines audiveris,homr,pipeline` on the samples. Scores equal the last native run (same versions); stats.json populated incl. GPU.
4. Recognizer refactor parity: `reassemble()` on Anastasia 1/2/4A with homr gives the same note F1 as before (memory baseline ~90 %+). `omrbench bench` on Anastasia unchanged.
5. Each new engine/recognizer: `omrbench run --engines <name> --samples demo-*,<one real>` produces a valid MusicXML and scores. Failures are recorded, not crashes.
6. pdfkind: a demo PDF → vector; a rasterised copy → scan; pdftext bar numbers on a vector sample match GT.
7. `omrbench components` produces layout and OCR reports.
8. `combo` beats or equals best single engine per score type under leave-one-out routing; report shows the matrix.
