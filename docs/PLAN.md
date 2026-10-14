# museScribe plan

Single source of state, decisions, results and next steps. Replaces `PC_PLAN.md` and `PLAN_full.md`
(2026-10-13). Backlog ideas without a slot yet: `docs/IMPROVEMENTS.md`. How-to docs: `docs/shows.md`
(workbook, transcribe, bench), `docs/pipeline.md` (pipeline engine, meta keys), `docs/engine-benchmark.md`
(samples, `run`).

## 1. Goal and rules

Goal: **the best possible transcription of the two shows Anastasia and Ghost**, which are then corrected
by hand in MuseScore. No need to generalise to unseen shows, so no held-out set: every finished
hand-corrected song becomes truth and is used for tuning right away.

The quality measure that matters is **how much hand work an output needs to become the truth**:
notes, rhythm, bar count, dynamics, articulations, lyrics, text, instrument changes, everything. Note
F1 alone is not enough (section 6).

User rules:

- Zero budget, local only, free tools. Non-commercial use, so GPL / AGPL / CC-BY-SA / NC licences are fine.
  No cloud, paid or commercial tools. Local VLMs only as an OCR component, not as a full engine.
- Everything runs in Docker (Audiveris, homr and every other engine).
- Accuracy first. Speed never at the cost of quality (e.g. Audiveris parallel sheets stay off).
- The best scorer is the default (`pipeline` = Audiveris layout + homr crops + repairs).
- Truth = MusicXML / MuseScore only. No metric that needs extra user input.
- `data/` is read-only for the tool (edited by hand only); everything generated goes to `results/`.
- Same commands and `bench.yaml` on both machines; no per-machine config.
- A wrong bar count is a soft error (the user can add bars or delete empty ones), not a hard failure.
- Big benchmark runs only on the PC and may take several days.

Dropped for good: LEGATO (Llama 3.2 licence), ijdar-e2e-pianoform (no weights), student CV repos
except Mozart, moonlight, handwritten / mensural tools, `external` engine, `correction_minutes` and
the 70 % rule, tromr (homr's transformer derives from TrOMR) and tfe2e (monophonic incipits only),
MeasureDetector (same Faster R-CNN family OLA beat, TF1.13).

## 2. Machines

| | PC (benchmark machine) | Laptop (dev box) |
|---|---|---|
| Host | `SuperGamer3000`, Windows + WSL2 Ubuntu-24.04, Docker Desktop 29.8.2 | `DESKTOP-606ME4E`, same setup |
| CPU / RAM | Ryzen 7 3700X (16 threads), 32 GB; WSL `memory=28GB` (`.wslconfig`) | Ryzen 7 7840U (16 threads), 27 GB |
| GPU | RTX 2070 SUPER 8 GB, Turing (fp16 yes, bf16 no, no FlashAttention-2), driver 610.53, CUDA 13.3 | Radeon 780M, no CUDA; `omrbench doctor` shows `docker gpu: skipped` |

- Repo `~/museScribe` on the WSL ext4 filesystem on both (never `/mnt/c`, I/O is much slower). User develops on
  the laptop and pulls on the PC. Data in `~/museScribe/data/` (not in git, copied by hand).
- Harness venv: `source ~/.local/share/omrbench/env.sh` (`~/.local/share/omrbench/venvs/harness`).
- Tesseract 5.5.2 + tessdata are copied out of the Audiveris image once into `~/.local/share/omrbench/tools`
  (needed for the bar-number OCR pass). Qwen GGUF in `~/.local/share/omrbench/models/qwen25vl-7b`.
- No global git identity on the PC: `git -c user.name="Konstantin Pelz" -c user.email="konstantin.pelz@online.de" commit ...`.
  `gh` is logged in, `git push` works.
- `wsl --shutdown` also kills the Claude session.
- MuseScore 4 on the Windows default path (`/mnt/c/Program Files/MuseScore 4/...`), used to export `.mscz` truth.
- `results-laptop/` = the laptop's results as a reference (untracked). Keep.

## 3. Commands

```bash
source ~/.local/share/omrbench/env.sh
omrbench doctor                                   # docker, GPU, images
omrbench images build [names] | list
omrbench check anastasia                          # validate the workbook
omrbench transcribe anastasia --songs 1,2 [--run-id ID] [--jobs 2]
omrbench bench anastasia [--songs 1] [--run ID] [--full]   # score against truth; --full adds OMR-NED + TEDn
omrbench bench ghost --songs 20 --transcribe       # transcribe + score
omrbench sweep anastasia,ghost --id ID [--engines a,b] [--grid "k=v1,v2;k2=..."] [--grid-reuse BASE] [--songs 1,1a]
                                                   # every engine/variant -> transcribe (or reassemble from BASE) + bench,
                                                   # then results/sweeps/ID/report.md (ranking, best per part / category)
omrbench sweep --id ID --resume                    # after a crash: skips finished engines and PDFs
omrbench sweep --id ID --rebench | --report-only   # re-score finished engines / rebuild the report
python scripts/reassemble.py ghost --from WORKRUN --to NEWRUN [--engine pipeline-raw] [--songs 20]
                                                   # assembly only, on a run's work dirs (~90 s)
omrbench run --engines pipeline,homr --samples demo-*      # multi-engine run on data/samples
omrbench components layout|ocr <show> --run <run>  # P6 component benchmarks
bash scripts/smoke_docker.sh                       # demo sample through the containers
python -m pytest -q tests                          # no Docker needed; must pass before a commit
python -m pyflakes omrbench tests                  # 4 old warnings: report.py, runner.py, _olimpic_tedn.py, pipeline/vocal.py
```

Fast iteration: `scripts/reassemble.py` (`PipelineEngine.reassemble`) reruns only the assembly on a finished
work dir (`results/<show>/runs/<id>/pipeline/<sid>/`). All Anastasia 1/2/4A parts take about 90 s. Use it for
every assembly change; then `omrbench bench <show> --run <id>`.

Gotcha: `omrbench transcribe --engine X` overwrites `results/<show>/<song>/`. Back it up or rerun `pipeline` after.

## 4. Architecture (as built)

Data and outputs:

```
data/<show>/{show.yaml, songs.xlsx, pdfs/, truth/}   read-only; workbook sheet per song, B2 = truth file,
                                                     row column `truth` maps output part -> truth part(s)
data/samples/<id>/                                   single-PDF samples with meta.yaml (type) + GT
results/<show>/<song>/                               latest outputs + manifest.json (+ combined.mscz)
results/<show>/runs/<id>/                            run history: outputs per song, pipeline/<sid>/ work dirs, run.log
results/<show>/bench/<id>/                           report.md, scores.json, metrics.csv
results/<show>/components/<id>/                      layout / OCR component reports
results/cache/                                       truth exports
```

Code map:

- Engines: `omrbench/engines/` (`build()` registry; `Engine.container` image key, `container: native` turns
  Docker off; `exec_cmd`; `pagewise.py`; `KernPages` = one container call per sample for page-image engines).
- Containers: `omrbench/containers.py` (`IMAGES`, `run_cmd`, `run_in_container` reads `stats.json`, kills the
  container by name on timeout, `pool_cmd` for long-lived workers, `build_cmd` with repo-root context).
  `docker/base/omr_run.py` = in-container monitor (psutil + NVML) writing `stats.json`.
- Pipeline: `omrbench/pipeline/engine.py` (Audiveris layout -> crop jobs -> recognizer -> `assemble.py`),
  `recognizer.py` (`recognizer:` / `fallback:`; readers `homr`, `zeus`, `smt-sys`, `transcoda`, `smt-fp`,
  `clarity`; groups a reader can't read go to homr), `ocr.py` (bar numbers: PDF text layer on vector pages,
  Tesseract otherwise; `ocr_engine:` option), assembly source label is `crop` (generic).
- homr pool: `engines/homr_pool.py` (JSON lines over stdin/stdout to `_homr_worker.py`, copied into the image).
- PDF kind: `omrbench/pdfkind.py`, per page `scan | scan+ocr | vector | vector-outlined | text`.
- Converters: `omrbench/convert/kern.py` (**kern/bekern -> MusicXML via music21, header/terminator and
  spine-count repair), `convert/mozart.py`.
- Metrics: `metrics/edits.py` (**edit penalty**, the headline), `metrics/notef1.py` (note F1 by bar index +
  bar-aligned), `metrics/elements.py` (LCS F1 per element category), `metrics/omrned.py` (OMR-NED, musicdiff),
  `metrics/tedn.py`, `metrics/flags.py`. `omrbench/bench.py` = show benchmark, `omrbench/sweep.py` = all engines.
- Components: `omrbench/components.py`.

Design rules:

1. Identical paths: a container mounts its run dir at the same absolute path as on the host.
2. `docker run --user <uid>:<gid> -e HOME=/tmp`, so outputs belong to the user.
3. Single commands run as `omr-run --stats <dir>/stats.json -- <cmd>`; long-lived pools have host-side stats only.
4. Host tool paths (`TESSDATA_PREFIX`, ...) are not passed into containers.
5. `device: auto` = `cuda` when host `nvidia-smi -L` works, else `cpu`. `cpu` sets `CUDA_VISIBLE_DEVICES=`
   and runs without `--gpus`. Engines with `requires_gpu: true` are skipped on CPU machines.

Images (all built and verified on the PC, GPU visible where used):

| Image | Base | Notes |
|---|---|---|
| `omrbench/audiveris:5.11.0` | cpu | needs `libgtk-3` even in `-batch`; tessdata at `/opt/tessdata`; `JAVA_TOOL_OPTIONS` legacy merge sort |
| `omrbench/homr:0.7.0` | cuda13 | pinned 0.7.0 (main has a breaking ProcessingConfig change); onnxruntime-gpu 1.31.0 needs CUDA 13; holds fp32 + fp16 models; honours `CUDA_VISIBLE_DEVICES=""` |
| `omrbench/oemer:0.1.8` | cuda | patched to ask for CPU when `CUDA_VISIBLE_DEVICES=""` (onnxruntime-gpu 1.19 segfaults otherwise) |
| `omrbench/clarity:c6bb8a4` | cpu | whole-PDF engine + `clarity-crops` staff reader (stage B on our crops) |
| `omrbench/transcoda:b529f8a` | cpu | full-page pianoform -> kern |
| `omrbench/smt:fp-grandstaff`, `omrbench/smt:grandstaff` | cpu | full page / system-level grand staff |
| `omrbench/zeus:c8569eb` | cuda11 | solo-staff `ayce-2026-08-03` (CC BY-NC-SA) + grand-staff `zeus-olimpic-1.0` (CC BY-SA) |
| `omrbench/mozart:a51c9d7` | cpu | classic-CV floor |
| `omrbench/ola:2.0` | clarity | layout YOLO, must run at imgsz 640 |
| `omrbench/ocr:easyocr1.7.2-doctr0.11`, `omrbench/paddle:3.3` | clarity / cpu | OCR components |
| llama.cpp `server-cuda` (by digest `sha256:c4348afb…`) | | Qwen2.5-VL-7B Q4_K_M, 7.3 GB VRAM |

## 5. Data, truth and current baselines

### Shows

- `data/anastasia/pdfs/`: 14 full-book PDFs, all scans (97–405 pages each) except the vector `PianoReduction`.
  Expected bar counts: song 1: 32, 2: 78 (1–76 + 72A/72B), 3: 245, 4: 213 (206 + 131A, 132A–C, 148A–C; lettered
  and cut lettered bars count), 4A: 6.
- `data/ghost/pdfs/`: 9 PDFs, born-digital vector pages (music fonts `Maestro`, `EngraverFontSet`) with a few
  scanned covers. 31 sheets (1..24 incl. 1a, 11a, 13A, 14a, 20A–C), titles "English / German". Every song starts
  on a fresh page; blank page-turn pages excluded via comma ranges (Utility 6, 8). PianoReduction = German
  Klavierauszug, no #24. TACET parts stay empty. Only Guitar #2 and Drums #15 were checked for hidden vocal
  staves (`keep_staves: 1`).
- Samples `data/samples/`: `demo-bach-chorale` (choir), `demo-lindenbaum` (piano), `demo-violin-part` (part),
  `anastasia-pr-1` (PianoReduction p. 7–9, piano_reduction), `anastasia-pr-4a` (p. 58, piano).

### Truth

| Show / song | File | Linked in workbook | Notes |
|---|---|---|---|
| Anastasia 1 | `truth/01_Opening_Fanfare_and_Opening_Scene.mscz` | yes | |
| Anastasia 2 | `truth/02_Prologue_Once_upon_a_december_fertig.mscz` | yes | Klavierauszug empty = not annotated (`Piano=-`) |
| Anastasia 4A | `truth/04a_Underscore_after_A_rumor_in_St_Petersburg.mscz` | yes | "Xylophon" = placeholder for drum-set x-notes (Drums row truth `-`) |
| Anastasia 4 | coming shortly (includes choir) | no | transcribed 2026-10-13, run `20261013-222736` |
| Ghost 20 | `truth/#20 - I'm Outta Here_Fertig.mscz` | yes | 7377 truth notes (Anastasia 1/2/4A together: 2708) |
| Ghost 1a | `truth/#1a - Don't want the bubble to burst.mscz` | yes (2026-10-14; backup `songs.xlsx.bak-20261013`) | TACET rows `-` |

Theresa's earlier song 4 corrections are deleted and no longer relevant.

Truth conventions (user decisions): sounding pitch under 8va (pipeline can't read 8va yet); Glock / Crotales
sound 15ma; full-size notes over a whole-bar rest voice are cues (dropped); male voices in treble-8vb only for
chorus labels; duet labels A+B go to both parts; singer part names as printed; lyrics verse 1; spoken dialogue
dropped; piano dynamics on staff 1; grace notes as 16ths. German truth part names: Flöte 1 = Reed 1 Flute,
Klarinette in B 1 = Reed 2 in song 1 but Reed 1 in song 2, Fagott = Reed 3, Pauken = Timpani, Glockenbaum =
Mark Tree, Splash-Becken = Cymbal, Frauen = "Russian Chorus", Klavierauszug = PianoReduction Piano.

Most truth songs contain keyboard, guitar and drums; Anastasia 4 adds choir.

### Baselines (kept run dirs)

Edit penalty = MuseScore actions to reach the truth (lower is better; section 6); "left" = penalty / typing the
parts in from scratch.

| Show | Work dirs (reassemble from these) | Scored outputs | Bench id | Edit penalty (left) | Total note F1 | bar-aligned |
|---|---|---|---|---|---|---|
| Anastasia 1/2/4A | `results/anastasia/runs/20261013-020114` (also holds `crops-zeus`, `crops-clarity`, `crops-smt-sys`, `ocr-doctr/easyocr/paddle`, `ola` caches) | `runs/fix4` | `edits-fix4` | **1528** (32.0 %) | **0.953** (1: 0.933, 2: 0.966, 4A: 0.985) | 0.955 |
| Ghost 20 | `results/ghost/runs/ghost20-pc` | `runs/g20-fix4` | `edits-g20-fix4` | **3458** (35.7 %) | **0.705** | 0.766 |
| Ghost 1a | `results/ghost/runs/g1a-base` | `runs/g1a-fix4` | `edits-g1a-fix4` | **235** (32.5 %) | 0.622 | 0.941 |
| Ghost 11a (smoke, no truth) | `results/ghost/runs/ghost11a-final` | `runs/g11a-fix` | – | – | – |
| Anastasia 4 | `results/anastasia/runs/20261013-222736` | | – | waits for truth | |

Small output-only runs of the comparisons are kept too (`lvl2-*`, `l3-ola`, `ocr-*`, `p7-*`); older work
dirs were deleted 2026-10-13. All bench reports stay in `results/<show>/bench/`.

Note F1 changed slightly on 2026-10-14: drum notes are keyed by staff position (was rhythm only) and truth
slashes are scored on rhythm (Ghost 20 0.719 -> 0.705: Drums 0.481 -> 0.333, Guitar 0.067 -> 0.150).
Ghost 1a: index note F1 0.622 vs aligned 0.941 = bar-count errors (Cello 25/28, Guitar 25/28, Piano 29/28).

Ghost 20 per part (note F1 / aligned, before 2026-10-14): Violin 0.992, Cello 0.978, Bass 0.998, Reed 0.947, Trumpet 0.521 / 0.883
(134/135 bars), **Guitar 0.067** (slash notation, 608 of 725 truth notes are slashes), **Utility (E-piano) 0.582**
(pitch class 0.772: octave convention), **Drums 0.481** (692 notes out vs 1329; chords of hits lost),
PianoReduction 0.856. Truth part "Voice 1" has no workbook row.

Anastasia weak spots (fix3): song 2 Trombone 0.875 (77/78 bars), Crotales 0.769, Mark Tree 0.000, Cymbal 0.500,
Triangle and Schlagzeug no output; several parts one bar short or long.

## 6. Metrics

### Edit penalty (headline, `metrics/edits.py`)

Number of MuseScore actions that turn the output into the truth; minimise it. Every action costs 1 (user
decisions 2026-10-13): a wrong note (pitch and/or duration) = 1 retype; a missing / made-up / changed / moved
element (p -> f, fermata, slur, tie, hairpin, lyric, chord symbol, tuplet, tremolo, word, clef / key / time
change, barline, repeat / volta / navigation, instrument change) = 1; rests free. Bars aligned by DP: delete an
extra bar = 1 (contents go with it), insert a missing bar = 1 + its contents. A whole part off by an octave /
transposition = 1 bulk action (the `shift` column; also logged as a warning). A part with no output = 1 (add the
instrument; bars are score-wide) + contents = `from_scratch`. Rehearsal marks, tempi and system text
(`system="only-top"` words in the truth, e.g. rit.) count once per song over the union of all output parts.
Slash noteheads: rhythm only; drums: by staff position (kit instrument), simultaneous hits kept.
Known limits: an octave-off *region* (Celesta after an instrument change in Ghost 20 Utility) is charged per
note; a chord with a wrong duration costs one per note; split-instrument outputs compare instrument changes by
position only.

### In `omrbench bench`

Per part, per song (+ system items) and total: edit penalty, from scratch, left %, bars to fix (insert / delete
/ change), shift, penalty by category; note F1 (notes, pitch, pc, rhythm, aligned); element F1 per category
(`musicxml.CATEGORIES`: notes, pitch, rhythm, rests, clefs, keys, times, dynamics, hairpins, articulations,
slurs, ties, lyrics, words, tempo, fermatas, tuplets, tremolos, instruments, structure, barlines, rehearsal,
chords, multirest, systemtext); runtime / memory per PDF; `--full` adds OMR-NED + TEDn. Every bench appends to
`results/<show>/bench/trend.csv`. `omrbench check` suggests `truth` cells for rows without one.

Not scored: grace notes and cue notes; per-kit-instrument drum report (penalty covers it).
Open: cross-check the penalty against OMR-NED (`--full`) on a few parts.

## 7. Findings and learnings

### Readers and engines (Anastasia 1/2/4A, PC)

Full pipeline per crop reader, total note F1: homr **0.955**, SMT 0.769, Clarity 0.696, Zeus 0.659.
Zeus's solo-staff model breaks on scanned orchestral parts (bar counts up to 6x, one crop looped into 177 bars);
SMT-sys ruins piano reductions (346 / 1581 bars) and drops most keyboard notes; Clarity is better only on 4A
Keyboard 2 (1.000 vs 0.983). Samples: pipeline-clarity pr-1 0.881, pr-4a 1.000, lindenbaum 0.960 (homr
0.942 / 1.000 / 0.986).

Recognizer comparison without homr tuning (27 parts every level has output for):

| level | reader | note F1 (bars by index) | bar-aligned |
|---|---|---|---|
| 1 page | Audiveris | 0.234 | 0.473 |
| 1 page | homr | 0.398 | 0.631 |
| 2 crops, no repairs | homr | 0.644 | 0.957 |
| 2 crops, no repairs | Clarity | 0.520 | 0.889 |
| 2 crops, no repairs | Zeus | 0.501 | 0.765 |
| 3 full pipeline | homr | 0.976 | 0.980 |
| 3 full pipeline | Clarity | 0.723 | 0.904 |
| 3 full pipeline | Zeus | 0.640 | 0.785 |

All 41 parts, level 2 aligned: homr 0.907, Clarity 0.806, Zeus 0.682, SMT 0.592. Zeus / Clarity beat homr on 2
parts each (Pauken, Crotales / Frauen, 4A Keyboard 2) and lose on 30+. Conclusion: homr is the best reader even
without tuning; the Audiveris-layout crops add most (level 1 -> 2), the repairs mostly fix bar counts.
Level 1 runs via `omrbench transcribe --engine homr|audiveris`; level 2 by reassembling with `repairs: false`
(bench entries `pipeline-raw`, `pipeline-<reader>-raw`). Index-based note F1 scores raw outputs with a missing
bar near 0; use `aligned` for reader quality.

Page engines on the demo samples: see `docs/engine-benchmark.md`. oemer on laptop CPU: 260 s / page, 6 GB,
note F1 94 % on demo.

### Layout and OCR components

- OLA v2.0 vs Audiveris: on vector samples about equal; on Anastasia scans OLA finds 242 systems vs 385 and misses
  many single-staff systems. As an extra bar-count vote (`pipeline-ola`): 0.955 -> 0.929. Audiveris stays.
- Bar-number OCR (`ocr_engine`): Tesseract 0.955, docTR 0.948, PaddleOCR (CPU) 0.948, EasyOCR 0.944. The filters in
  `ocr.supplement` (MIN_CONF, lone digits) were tuned on Tesseract. Tesseract stays.
- Qwen2.5-VL-7B reads strip numbers well where Tesseract misses them, but its `bbox_2d` via llama.cpp is not in
  image coordinates, so numbers can't be placed on bars. Follow-up only if bar alignment errors matter: ask per
  Audiveris bar segment (~4000 requests for Anastasia 1/2/4A), expected gain ~0.01.
- Part labels and rehearsal marks: not benchmarked (Audiveris text is used).

### Ensemble (P7)

`ensemble: [zeus, clarity, smt-sys]` adds those readers' crop bars as per-bar candidates (`assemble.plan_systems`
`alts`; picks `agree`, `fallback`, weighted, `agree-keep`). All variants lose: 0.937 / 0.937 / 0.937 / 0.946 vs 0.955.
A homr bar whose voices don't add up is still usually the best reading. Routing says homr for every part type
with the current truth. Revisit only with new readers or truth of new score types.

### Hardware and runtime

- homr fp16 on the GPU: 0.928 vs 0.955 (fp32 CPU), and 8 GPU workers on 8 GB stalled into 1800 s timeouts (GPU run
  6987 s vs CPU 988 s). homr runs on the CPU by default everywhere (`device: cuda` opts in). fp32 ONNX on CUDA
  (patched worker, scratch test) = CPU-identical output, no speed-up. Don't move homr back to GPU without re-benching.
- On the CUDA 12.6 base, homr's CUDA provider failed to load (`libcublasLt.so.13`) and silently fell back to CPU.
- Speed comes from the homr pool (8 workers x 2 ONNX threads) and `--jobs 2`; 3 jobs or niced workers were slower.
  One transcribe peaks at ~10 GB; with 15.6 GB WSL two parallel transcribes were OOM-killed.
- Audiveris `processAllStubsInParallel=true` halves wall time but a race drops symbols (an accent in song 4 Trumpet)
  and crashed song 4 Violin 2 in 3/3 tries; `parallel_sheets` stays off (opt-in, failed parallel run is redone serially).
- `pdfkind` takes ~100 s for a 405-page scan.

### Pipeline behaviour

- Vector pages: bar numbers and multi-rest counts come from the PDF text layer; pages without fonts skip it.
- Ghost 20 multi-rests: text-layer counts + Audiveris MULTI_REST stacks keep Audiveris' count (0.538 -> 0.719).
- Repairs tuned on homr: `_vote` breaks 1-vs-1 ties between Audiveris and the crop reader toward the crop reader;
  homr's courtesy-signature rest bar is dropped; multi-rests and bar numbers fixed around homr's habits.
- MuseScore 4 drops mid-part `<transpose>` changes and `<sound><instrument-change>` on MusicXML import (the part keeps
  the first transposition); `<score-instrument><instrument-sound>` does set the instrument. So doubling books use
  `split_instruments: true` (one part per instrument), not `doubling: true`.
- Piano reductions give two files: `- Voices` (one part per printed singer label, lyrics) and `- Piano`
  (no sung / spoken text); `spoken_text: drop|text`; uncertain articulations / dynamics dropped; hairpins at most 2 bars.
- Reed 2 song 2 bar 17: "(Flute)" is a cue label; parenthesised labels are ignored by the matcher unless `paren_aliases`.

### What the edit penalty shows (2026-10-14, baselines fix4)

- Anastasia 1/2/4A (1528): words 196, articulations 168, slurs 151, notes 156, ties 121, dynamics 115, barlines
  ~130, systemtext 99, hairpins 89, structure (repeats) 68, keys 62. Notes are no longer the main cost.
- Ghost 20 (3458): notes 2130 (Guitar slashes, Drums, Utility), ties 303, chords 253 (no chord symbols in the
  output), slurs 217, articulations 203.
- Pipeline outputs had no barlines at all (`bars.part_bars` drops them) and wrote boxed bar numbers as rehearsal
  marks. Fixed 2026-10-14: final light-heavy barline on every part, numeric rehearsal marks dropped (Anastasia
  -42, Ghost 20 -100, 1a -12). Double barlines and repeats (Audiveris reads some) are still not carried over.
- `pipeline-ensemble*` used to read `crops-<reader>/` caches only, so on a fresh run it equalled `pipeline`; the
  pipeline now runs the ensemble readers on the same crops itself.

### Open workbook / data items

- Ghost 20 truth "Voice 1" = Oda Mae, not finished: workbook `unfinished: Voice 1` (bench skips it), PianoReduction
  row already maps `Oda Mae=Voice 1`.

- Drums song 4 p15 sys 1 (bars 90–97): upper staff Timpani, lower unlabeled = Triangle -> instruments cell
  `Triangle (lower_staff)`. Drums song 4 p17 sys 3 (bars 174–177): x-heads marked "sticks" are still Castanets;
  Timpani from bar 177.
- Keyboard 2 scan lacks printed p. 11 of No. 3 (bars 218–229) and p. 12 of No. 4 (~196–206); user is getting them.
  `Keyboard 1.pdf` ends at No. 14 (Act Two book missing).
- Later songs: Violin 2 plays Viola (alto clef) in No. 11 and 26; Bass "Acoustic Bass" in No. 26; No. 24A not in the
  PianoReduction TOC; song 5 Reed 1 English Horn needs a `show.yaml` entry (transpose F), not added yet.
- MuseScore instrument mapping: "Bass" opens as the voice register, "Cello" is not mapped to Violoncello; most
  instruments have to be reassigned by hand (IMPROVEMENTS #18).

## 8. Next steps (in order)

1. **Big run** (user decision 2026-10-13): a weed-out sweep of every engine on Anastasia 1 + 4A and Ghost 1a
   (`--id weed`; 17 of 19 engines done when the PC crashed on 2026-10-14 in `smt-fp`; resume with
   `omrbench sweep --id weed --resume`), then the full grid on all truth songs (`--id full`: base
   `pipeline-allreaders` + 42 variants reassembled from it, Tesseract only). Weed so far: `pipeline` 1186 = best within 0.3 %
   (`ensemble-wk` 1182 at 18x the time); OCR variants within 1 %; other main readers 40-110 % worse; page
   engines 2.3-4.3x worse. Open questions: `CHECKS.md`. Includes the gated SMT models once the Hugging Face access is approved
   (`HF_TOKEN`; `PRAIG/smt-fp-mozarteum`, `-polish-scores`).
2. **Truth wiring**: link Anastasia 4 when its truth arrives (incl. choir; `omrbench check` suggests the cells)
   and bench run `20261013-222736`; remove `unfinished: Voice 1` from Ghost 20 when Oda Mae is done.
3. **Regression safety** (IMPROVEMENTS #3): small regression samples from real failures (Ghost Trumpet system 8,
   Reed system 1, Anastasia 2 Violin 1) with stored work dirs, checked in pytest via `reassemble()`.
4. **Quality work, biggest penalty first** (from the sweep's "penalty by category"; current order):
   - Ghost Guitar slash notation + chord symbols (IMPROVEMENTS #7, #11); chords 253 actions in Ghost 20.
   - Drums: kit mapping, keep simultaneous hits (#8); Anastasia percussion without output (Triangle, Schlagzeug).
   - Words / system text / dynamics / hairpins / ties / slurs: route from the best source per element.
   - Barlines + repeats / voltas from Audiveris onto the output bars.
   - Octave regions after instrument changes (Celesta in Ghost Utility; #9).
   - Generic bar-count guards (#10); tuplets, fermatas, tremolos (homr reads single tremolos as two-note).
   - MuseScore instrument mapping in the output (#18).
5. **Speed** (#13–#15): two songs in parallel, per-page Audiveris cache, homr GPU fp32 with larger batches.
6. **Routing / ensemble revisit** (P7): from the sweep's best-per-part and best-per-category tables, write
   `routing.yaml` (score type x pdfkind x element).
7. **Optional / later**: results viewer (#16), `transcribe` refuses to start on workbook errors (#17), README per
   song folder (#18), container script tests (#19), pin remaining assets (#20), native vector glyph parsing for
   born-digital PDFs (#12), vector pages at a higher render dpi, report split by pdfkind, Qwen per-bar-segment bar
   numbers, re-test the Audiveris parallel race on a newer Audiveris.

## 9. Conventions

- `python -m pytest -q tests` passes before every commit; no Docker needed for tests.
- Do not commit `data/` or `results/` (gitignored).
- New GPU-only engines get `requires_gpu: true` in `bench.yaml`.
- Every new engine / recognizer lands with image, adapter, converter test and `bench.yaml` entry, and is run on
  demo + one real sample before moving on. Failures are recorded, not crashes.
- Assembly changes: reassemble the baseline work dirs, bench with `--run`, and compare to the baseline ids above
  (default path must stay byte-identical unless the change is meant to alter it).
