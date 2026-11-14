# museScribe plan

State, rules and how things are built. Rewritten 2026-11-14; the long version with every baseline and round up to
this date is `docs/archive/PLAN-2026-11-14.md`.

Other docs: `docs/IMPROVEMENTS.md` (**what to do next**, what worked, what failed), `docs/ERRORS.md` (what is still
wrong, by kind and cost), `docs/TRUTH_DEVIATIONS.md` (truth vs printed page), `docs/CORRECTION_INFORMATION.md`
(conventions of the corrected scores), `docs/shows.md` (workbook, transcribe, bench), `docs/pipeline.md` (engine,
meta keys), `docs/engine-benchmark.md` (samples, `run`), `docs/sheet_reader_requests.md`.

## 1. Goal and rules

Goal: **the best possible transcription of the two shows Anastasia and Ghost**, which are then corrected by hand in
MuseScore. No held-out set: every finished hand-corrected song becomes truth and is used for tuning right away.
The measure is **how much hand work an output needs to become the truth** (edit penalty, section 6).

User rules:
- Zero budget, local only, free tools; non-commercial use (GPL / AGPL / CC-BY-SA / NC are fine). No cloud. Local
  VLMs only as an OCR component.
- Everything runs in Docker. Accuracy first; speed never at the cost of quality.
- The best scorer is the default (`pipeline` = Audiveris layout + homr crops + repairs).
- Truth = MusicXML / MuseScore only. No metric that needs extra user input.
- `data/` may be edited by hand or by Claude (show.yaml, workbook; user 2026-11-11), **never `data/<show>/truth/`**.
  Everything generated goes to `results/`. Both are gitignored.
- Same commands and `bench.yaml` on both machines. A wrong bar count is a soft error.
- Every pipeline change passes the acceptance rule (`docs/IMPROVEMENTS.md` section 1).

Dropped for good: LEGATO, ijdar-e2e-pianoform, student CV repos except Mozart, moonlight, handwritten / mensural
tools, `external` engine, tromr, tfe2e, MeasureDetector.

## 2. Machines

| | PC (benchmark machine) | Laptop (dev box) |
|---|---|---|
| Host | `SuperGamer3000`, Windows + WSL2 Ubuntu-24.04, Docker Desktop | `DESKTOP-606ME4E`, same setup |
| CPU / RAM | Ryzen 7 3700X (16 threads), 32 GB; WSL `memory=28GB` | Ryzen 7 7840U (16 threads), 27 GB |
| GPU | RTX 2070 SUPER 8 GB (fp16 yes, bf16 no), CUDA 13.3 | Radeon 780M, no CUDA |

- Repo `~/museScribe` on the WSL ext4 filesystem (never `/mnt/c`). Data in `~/museScribe/data/` (copied by hand).
- Harness venv: `source ~/.local/share/omrbench/env.sh`. Tesseract 5.5.2 + tessdata in
  `~/.local/share/omrbench/tools`. Qwen GGUF in `~/.local/share/omrbench/models/qwen25vl-7b`.
- `gh` is logged in, `git push` works. `wsl --shutdown` also kills the Claude session.
- MuseScore 4 on the Windows default path, used to export `.mscz` truth and for `to_mscz`.
- `results-laptop/` = the laptop's results as a reference (untracked). Keep.

## 3. Commands

```bash
source ~/.local/share/omrbench/env.sh
omrbench doctor | images build [names] | images list
omrbench check anastasia                           # validate the workbook
omrbench transcribe anastasia --songs 1,2 [--run-id ID] [--jobs 2]
omrbench bench anastasia [--songs 1] [--run ID] [--bench-id ID] [--full]
python scripts/reassemble.py <show> --from h71 --to NEW [--songs 20] [--combine]   # assembly only, no re-reading
python scripts/compare_bench.py BASE NEW           # total delta + acceptance rule
python scripts/error_report.py anastasia,ghost --run NEW    # every difference by kind -> results/errors/NEW/
python scripts/derive_drumkit.py [show]            # drum legend from the truth drum parts; re-run after a new drum truth
python scripts/pdf_truth_check.py <show> <song> <part>      # vector PDF pitches vs truth
omrbench sweep anastasia,ghost --id ID [--engines a,b] [--grid "k=v1,v2"] [--resume | --rebench | --report-only]
omrbench components layout|ocr <show> --run <run>
bash scripts/smoke_docker.sh
python -m pytest -q tests                          # no Docker; must pass before a commit
```

Gotcha: `omrbench transcribe --engine X` overwrites `results/<show>/<song>/`.

## 4. Architecture (as built)

```
data/<show>/{show.yaml, songs.xlsx, pdfs/, truth/}   workbook sheet per song, B2 = truth file, column `truth`
                                                     maps output part -> truth part(s)
results/<show>/<song>/                               latest outputs + combined.mscz (the user reviews these)
results/<show>/runs/<id>/                            outputs per song, pipeline/<sid>/ work dirs, run.log
results/<show>/bench/<id>/                           report.md, scores.json, metrics.csv; trend.csv
results/errors/<id>/                                 errors.md, errors.json
results/cache/                                       truth exports
```

Code map:
- Engines `omrbench/engines/`; containers `omrbench/containers.py`; homr pool `engines/homr_pool.py`.
- Pipeline `omrbench/pipeline/`: `engine.py` (Audiveris layout -> crop jobs -> homr -> assembly), `layout.py`
  (reads the Audiveris `.omr`: systems, head chords with stem side, dynamics, wedges, articulations, repeat dots),
  `assemble.py` (plan, align, repairs, write), `bars.py` (bar repairs), `vector.py` (born-digital pages: text layer,
  slashes, drum heads, articulation glyphs, ties, time signatures, lyric marks), `vocal.py` (piano reductions:
  singers, lyrics, marks by x), `drumkit.py`, `ocr.py`, `chords.py`, `text.py`.
- Song level: `transcribe.share_marks` (cross-book votes and filters), `musicxml.py` (extractor, sounds, last passes).
- Metrics: `metrics/edits.py` (edit penalty), `notef1.py`, `elements.py`; `bench.py`; `scripts/error_report.py`.

Design rules: a container mounts its run dir at the host's path; `docker run --user <uid>:<gid> -e HOME=/tmp`;
`device: auto` (homr runs on CPU by default); engines with `requires_gpu: true` are skipped on CPU machines.

Images in use: `omrbench/audiveris:5.11.0`, `omrbench/homr:0.7.1` (CUDA 13 base, worker with
`title_detection=False`). Benchmarked and kept for comparison: oemer, clarity, transcoda, smt, zeus, mozart, ola,
ocr (EasyOCR / docTR), paddle, llama.cpp + Qwen2.5-VL-7B (table in the archive file).

## 5. Data, truth and the current reference

- Anastasia: 14 full-book PDFs, all scans except the vector `PianoReduction`. Lettered bars count; a cut to a plain
  number keeps the bars between as empty bars; a cut to a lettered bar skips the earlier letters.
- Ghost: 9 PDFs, born-digital vector pages (fonts `Maestro`, `EngraverFontSet`, `MaestroPercussion`).
- Workbook rows per song: `time`, `key`, `bars`, `letters`; columns `truth`, `plainArticulation`, `plainText`,
  `unfinished`, `extra`.

Truth songs (12, 174 scored parts, 40 301 notes):

| Show | Songs (bars) | Notes |
|---|---|---|
| Anastasia | 1 (32), 2 (78), 3 (245), 4 (211), 4A (6), 5 (156) | Klavierauszug piano not generated, not scored (`Piano=-`); song 3 Violine 2 / Klarinette 2 are `plainArticulation`; six sparse parts in songs 3 / 4 (TRUTH_DEVIATIONS section 4), the user completes them |
| Ghost | 1a (28), 4 (80), 5 (44), 11a (19), 13 (199; Bass, Cello only), 20 (135) | 20 "Voice 1" unfinished |

No truth yet: Anastasia 5A, 6 (sheets made; outputs in `results/anastasia/`), all later songs.

**Reference: `r69-a` = 9 111 actions** (Anastasia 6 762, Ghost 2 349; 14 % of typing everything in; 2026-11-13).
Outputs `results/<show>/runs/r69-a`, bench id `r69-a`, work dirs `results/<show>/runs/h71/pipeline/` (homr 0.7.1
crops of the 12 truth songs). History of the reference: `docs/IMPROVEMENTS.md` section 4.

## 6. Metrics

Edit penalty (`metrics/edits.py`, headline): MuseScore actions that turn the output into the truth; every action
costs 1. A wrong note (pitch and / or duration) = 1; a missing, made-up, changed or moved element (dynamic, hairpin,
articulation, fermata, slur, tie, tuplet, tremolo, lyric, word, chord symbol, clef / key / time change, barline,
repeat, instrument change) = 1; rests free. Bars aligned by DP: delete a bar = 1, insert = 1 + contents; a matched
bar of the wrong length = 1 (`barlen`). A whole part transposed = 1 (`shift`); a section an octave off = 1
(`octave`). Playing techniques (`playtech`) and the part's instrument (`instrument`) = 1 each. Rehearsal marks,
tempi and system text once per song. Slash noteheads: rhythm only; drums: by staff position.

Not scored yet (the user wants them in, 2026-11-14; IMPROVEMENTS M1-M4): grace notes, curve end points, lyric
hyphens / melisma lines, ornaments and technique marks, chord degrees. Counts: ERRORS section 4.

`omrbench bench` also reports note F1 (by bar index and bar-aligned), element F1 per category, bars to fix,
runtime, and the "Percussion instruments" check after the MuseScore round trip.

## 7. Findings that still hold

Readers and components
- homr is the best crop reader at every level (full pipeline note F1 0.955; SMT 0.769, Clarity 0.696, Zeus 0.659).
  The Audiveris-layout crops add most (page 0.63 -> crops 0.96 aligned); the repairs mostly fix bar counts.
- Ensembles of readers lose (0.937-0.946 against 0.955). OLA as layout or vote loses. Tesseract beats docTR,
  PaddleOCR, EasyOCR for bar numbers. Qwen reads numbers but its boxes are not in image coordinates.
- homr fp16 on the GPU: 0.928 against 0.955 and stalls; homr stays on the CPU (8 workers x 2 threads, `--jobs 2`).
- Audiveris `processAllStubsInParallel` drops symbols and crashes; stays off.
- homr 0.7.1 output is not the printed staff (estimated time per crop, multi-rests written out, an empty measure
  before a repeat start): `bars.homr_as_printed` undoes it. Check again at the next homr bump.

Pipeline
- Audiveris' `.omr` holds far more than its MusicXML export (hairpins, dynamics, articulations, repeat dots, stem
  sides); marks are placed on homr's notes by image x (`imgpos`).
- Vector pages: text layer and glyphs are exact; bar numbers, lyrics, labels, chord symbols, drum heads, slashes,
  time signatures come from them.
- Cross-book votes work for bar structure (barlines, repeats, fermatas, lone-mark filters), not for copying marks.
- MuseScore 4 drops mid-part `<transpose>` and instrument changes on import: doubling books are split per
  instrument in Anastasia (`split_instruments`), one part in Ghost (`doublings: one_part`).
- Piano reductions give `- Voices` (one part per singer label) and `- Piano`.

More learnings and every rejected experiment: `docs/IMPROVEMENTS.md` sections 6 and 7.

Open workbook / data items
- Keyboard 2 scan lacks printed p. 11 of No. 3 (bars 218-229) and p. 12 of No. 4 (about 196-206).
  `Keyboard 1.pdf` ends at No. 14 (Act Two book missing).
- Later songs: Violin 2 plays Viola (alto clef) in No. 11 and 26; Bass "Acoustic Bass" in No. 26; No. 24A not in
  the PianoReduction TOC.
- Anastasia workbook: duets into both singers before song 6 is reviewed; drum book lower staff (`lower_staff:
  Triangle` in song 4 is right for 90-97, wrong for 78-81 / 174-177).

## 8. Next steps

The ranked list is `docs/IMPROVEMENTS.md` section 2. Short form (2026-11-14):
1. User: complete the six sparse truth parts (T1, about -930) and the other truth items T2-T4.
2. Dynamics and hairpins (the user's worst pain): D1 Ghost vector glyphs and lines, D2 / D3 `.omr` marks on
   keyboards and drum books, D8 filter for made-up homr dynamics.
3. Metric: score grace notes, curve ends, lyric hyphens, ornaments (M1-M4) and bench provenance (M5); rebaseline.
4. Detectors for dynamics / hairpins no reader sees (D4, D5), hairpin start / end (D7).
5. Keyboard notes: K2 (Ghost pianos from the drawing), K1 (Anastasia per-staff reading).
6. Anastasia drum kit and tremolos (P1, P2); then singers and the small structure items.

## 9. Conventions

- `python -m pytest -q tests` passes before every commit. Do not commit `data/` or `results/`.
- One commit per accepted change on branch `improvements`; after a reassembly run refresh `results/<show>/<song>/`
  and `combined.mscz`.
- New engines land with image, adapter, converter test and `bench.yaml` entry; GPU-only ones get `requires_gpu`.
- `data/` edits (workbook cells, show.yaml keys) are listed in the commit message, because `data/` is not in git.
