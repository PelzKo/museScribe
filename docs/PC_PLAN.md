# PC plan: museScribe on the GPU machine

Hand-off document for a Claude instance on the PC. Read this first, then `docs/PLAN_full.md`
(the master plan, phases 0–7). Everything here is meant to be enough without the original
machine's memory or `~/.claude` folder.

## 1. Goal

Benchmark many free, local OMR tools (Audiveris, homr, and later Zeus, Transcoda, SMT, TrOMR, …),
each alone and as components, and build a routed ensemble that picks the best per score type.
Everything runs in Docker. Zero budget, local only, non-commercial use.

Master plan: `docs/PLAN_full.md`. Phases: P0 cleanup, P1 Docker infrastructure, P2 converters,
P3 PDF kind + text layer, P4 page-level engines, P5 pluggable crop recognizers, P6 component
benchmarks, P7 routing + ensemble.

## 2. Machine (PC)

| Item | Value |
|---|---|
| Host | Windows, Docker Desktop 29.8.2, WSL2 |
| WSL distro | Ubuntu-24.04 (WSL 2) |
| WSL user | `konstantin` (shell prompt `konstantin@SuperGamer3000`) |
| GPU | NVIDIA GeForce RTX 2070 SUPER, 8 GB, Turing (fp16 yes, bf16 no, no FlashAttention-2) |
| Driver | NVIDIA 610.53, CUDA UMD 13.3 (`nvidia-smi` in WSL works) |
| CPU / RAM | Ryzen 7 3700X (16 threads), 32 GB (WSL: 28 GB) |
| Repo | `~/museScribe` (`/home/konstantin/museScribe`), branch `phase1-docker` |
| Data | `~/museScribe/data/` (not in git; copied by hand, same layout as the Windows copy) |
| Harness venv | `~/.local/share/omrbench/venvs/harness`, activate with `source ~/.local/share/omrbench/env.sh` |
| Path rule | Keep paths identical to the original machine. The repo is on the WSL ext4 filesystem, not `/mnt/c` (I/O is much slower there). |

Second machine (laptop, dev box): `DESKTOP-606ME4E`, Ryzen 7 7840U (16 threads), 27 GB RAM, Radeon 780M iGPU (no CUDA),
Docker Desktop 29.8.2 with WSL integration. Same user, same paths (`~/museScribe`, same harness venv). Runs CPU-only;
`omrbench doctor` shows `docker gpu: skipped`.

Access from Windows: Explorer `\\wsl$\Ubuntu-24.04\home\konstantin\museScribe`, or PowerShell `wsl -d Ubuntu-24.04`.

## 3. What is already verified on the PC

- `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` shows the RTX 2070 SUPER.
- `omrbench images build` succeeded for all four images: `omrbench/base:cpu`, `omrbench/base:cuda`,
  `omrbench/audiveris:5.11.0`, `omrbench/homr:0.7.0`.
  (Built from an earlier Dockerfile version; see section 5, the build context changed.)
- `docker run --rm --gpus all omrbench/homr:0.7.0 /opt/homr/bin/python -c "import onnxruntime as o; print(o.get_available_providers())"`
  lists `CUDAExecutionProvider`.
- `omrbench doctor` reports docker OK, docker GPU OK, all four images present.
- The file-owner check (uid `0` vs `1000`) was run by the user; the fix is in section 5.

Not verified yet: any real OMR run inside a container. This is the next step (section 6).

## 4. Repository state

Branch `phase1-docker` (commit `5fb5b17` pushed by the user; `11ee92f` is local until pushed), on top of `main` (`7de48c6 started rework`, which holds
the earlier Phase 0 cleanup, the `pdfkind` classifier and the kern converter):

| Commit | Content |
|---|---|
| `5fb5b17` | `docker/base`, `docker/audiveris`, `docker/homr`, `omrbench/containers.py`, `omrbench images`, doctor checks, tests |
| `11ee92f` | Audiveris and homr run inside their containers by default; homr pool in container; `scripts/smoke_docker.sh` |

Key files:

- `omrbench/containers.py`: `IMAGES` registry, `run_cmd` (the `docker run` argv), `run_in_container`
  (reads `stats.json` written by `omr-run`, kills the container on timeout), `pool_cmd` (homr worker
  via `docker run -i`), `check_image`, `build_cmd` (build context = repo root).
- `omrbench/engines/base.py`: `Engine.container` (image key; `container: native` in the engine config turns it off),
  `Engine.exec_cmd` (native or container), `container_env` (drops host-side tool paths).
- `omrbench/engines/audiveris.py`, `omrbench/engines/pagewise.py`: use `exec_cmd`. Homr's pool uses `pool_cmd`.
- `omrbench/engines/homr_pool.py`: `get_pool(launch_argv, …)`; the launch prefix is native python or the container command.
- `docker/base/omr_run.py`: in-container monitor, psutil + NVML, writes `stats.json` in the `RunStats` shape.
- `omrbench/pdfkind.py`: per-page kind `scan | scan+ocr | vector | vector-outlined | text`; `is_scan` = majority of non-text pages.
- `omrbench/convert/kern.py`: `**kern` → MusicXML via music21.
- `scripts/smoke_docker.sh`: the smoke test (section 6).
- `tests/`: 17 tests, run with `~/.local/share/omrbench/venvs/harness/bin/python -m pytest -q tests`.

Design rules that the code follows:

1. **Identical paths.** A container mounts its run directory at the same absolute path it has on the host
   (`-v /home/konstantin/museScribe/results/...:/home/konstantin/museScribe/results/...`). No path translation.
2. **Host user.** `docker run --user <uid>:<gid> -e HOME=/tmp`, so outputs are owned by the user, not root.
3. **Monitor in the container.** Single commands run as `omr-run --stats <dir>/stats.json -- <cmd>`.
   The homr pool has no `omr-run` wrapper, so its stats are the host-side numbers only.
4. **One worker script.** The homr image copies `omrbench/engines/_homr_worker.py` to `/opt/homr/worker.py`
   at build time; the native pool uses the same file.
5. **Host tool paths are not passed in.** `TESSDATA_PREFIX` and other host paths are filtered out; the image sets its own.
6. **Devices.** `bench.yaml` `device: auto` (default) resolves to `cuda` when host `nvidia-smi -L` works, else `cpu`.
   `cpu` sets `CUDA_VISIBLE_DEVICES=` and runs without `--gpus`; `cuda` runs with `--gpus all`.
   Engines with `requires_gpu: true` in `bench.yaml` are skipped (warning) when the device is `cpu`.
   Same repo and `bench.yaml` on PC and laptop; no per-machine config.

## 5. Known issues and fixes to check

- **Rebuild the images.** The build context changed (now the repo root) and `docker/base` and `docker/homr`
  copy files from the repo. Run `omrbench images build` again on the PC. The cache makes most of it fast.
- **Root-owned files.** Previously the containers wrote as root. The `--user` flag fixes this for new runs.
  Old root-owned output under `results/` may need `sudo rm -rf` once.
  Check with: `docker run --rm -v ~/omr-test:/work omrbench/base:cpu sh -c 'echo hi > /work/x.txt' && ls -ln ~/omr-test`
  (`1000` is good).
- **Homr models.** `homr --init` runs at image build time and fails the build if it fails
  (native `setup.sh` ignores the error).
- **Audiveris in container:** `JAVA_TOOL_OPTIONS` (legacy merge sort) is passed with `-e`. The OCR language data is baked
  in at `/opt/tessdata` via `TESSDATA_PREFIX`.
- **Timeouts** kill the container by name (`docker kill omrbench-…`). Check with `docker ps` after a timeout.
- **Native engines still installed by `setup.sh`.** `setup.sh --skip-audiveris --skip-homr --skip-oemer` is the current
  setup on the PC. The native Audiveris and homr paths in `omrbench doctor` show MISSING. That is expected and harmless
  with containers. Remove or ignore those lines later.
- **Windows MuseScore path** (`omrbench/transcribe.py`, `/mnt/c/Program Files/MuseScore 4/...`) is only needed for
  `mscz` ground truth. Not part of the container work.
- **Not verified:** Audiveris exporting from a container; homr output inside a container vs. the native run;
  the pool path (`pool: true`, the default); GPU speed for homr.

## 6. Status and next steps

Done (smoke test passed on PC and laptop):
- P1: Audiveris, homr and oemer images. Audiveris needs `libgtk-3` in the image (it loads GTK at startup, even in
  `-batch`). oemer: onnxruntime-gpu 1.19 segfaults when CUDA is requested without a GPU, so the image patches oemer
  to ask for CPU only when `CUDA_VISIBLE_DEVICES=""` (= `device: cpu`). oemer on the laptop CPU: demo page 260 s,
  6 GB, note F1 94 %.
- homr image: onnxruntime-gpu always lists `CUDAExecutionProvider`, so homr picked its fp16 GPU models even with
  `device: cpu` (slower on CPU, and different output: Anastasia 1 piano reduction 0.932 -> 0.745 note F1, one extra bar).
  The worker and the CLI now honour `CUDA_VISIBLE_DEVICES=""`; the image holds both model sets; onnxruntime-gpu pinned
  to 1.31.0. With `device: cuda` (PC) homr uses the fp16 models, so PC and laptop results can differ slightly.
- P3: on vector pages the bar-number pass reads the PDF text layer instead of Tesseract (`pipeline/ocr.py`,
  `text_layer_pages`); pages without fonts (scans) skip the check. Run reports have a `PDF` (pdfkind) column.

- P4: `clarity`, `transcoda`, `smt-fp`, `mozart` images and engines (all CPU-capable, none `requires_gpu`).
  Page-image engines share `KernPages` (one container call per sample, `batch_cmd`); converters
  `convert/kern.py` (header/terminator, bekern separators, spine-count repair) and `convert/mozart.py`.
  Demo note F1 on the laptop CPU: see `docs/engine-benchmark.md` and the run reports.

On the PC after pulling: `omrbench images build clarity transcoda smt-fp mozart`, then
`omrbench run --engines clarity,transcoda,smt-fp,mozart --samples demo-*` (`--prefix-matching` if needed) on the GPU.

- P4 verified on the PC (2026-10-12): all images build; `docker run --gpus all` sees the GPU in homr (after the
  CUDA 13 fix below), zeus (TF), smt, transcoda, clarity (torch).
- P5 started: `pipeline/recognizer.py` (`recognizer:` / `fallback:` in a pipeline entry). The source label `homr` in
  assemble.py is now `crop`; parity: `reassemble()` on all 41 Anastasia 1/2/4A work dirs gives byte-identical
  MusicXML before/after. Recognizers: `homr`, `zeus` (image `omrbench/zeus:c8569eb`, base-cuda11; solo-staff
  `ayce-2026-08-03` CC BY-NC-SA + grand-staff `zeus-olimpic-1.0` CC BY-SA), `smt-sys` (`omrbench/smt:grandstaff`,
  `PRAIG/smt-grandstaff`), `transcoda`, `smt-fp`; groups a recognizer can't read go to homr. bench.yaml entries
  `pipeline-zeus`, `pipeline-smt`, `pipeline-transcoda`.
- PC findings (2026-10-12):
  - homr's onnxruntime-gpu 1.31 is a CUDA 13 build; on the CUDA 12.6 base its CUDA provider failed to load
    (`libcublasLt.so.13`) and homr silently ran its fp16 models on the CPU. homr is now on `base-cuda13`.
  - Even on the GPU, the fp16 models score lower (Anastasia 1/2/4A total note F1 0.928 vs 0.955 with the fp32 CPU
    models) and 8 GPU workers on 8 GB stalled into 1800 s timeouts. homr therefore runs on the CPU by default on
    every machine (`device: cuda` in its config opts in). homr's fp32 models on CUDA (patched worker, tested in a
    scratch script only) gave CPU-identical output but no speed-up.
  - Without native Audiveris there was no Tesseract, so the bar-number OCR pass was skipped on scans. `ocr.py`
    now copies Tesseract 5.5.2 + tessdata out of the Audiveris image once into `~/.local/share/omrbench/tools`.
  - With both fixes the PC matches the laptop: total note F1 0.955 on Anastasia 1/2/4A (laptop outputs re-scored
    with the same code: 0.955). Laptop results are kept as reference in `results-laptop/`.
- Samples `data/samples/anastasia-pr-1` (PianoReduction p. 7-9, GT Klavierauszug + Frauen + Männer) and
  `anastasia-pr-4a` (p. 58, type piano, GT Klavierauszug), GT extracted from the truth scores.

Open: `PRAIG/smt-fp-mozarteum` and `-polish-scores` are gated on Hugging Face (manual approval + token).
- Full Anastasia 1/2/4A with other crop recognizers (2026-10-13, bench ids `pc-pipeline-zeus`, `pc-pipeline-smt`):
  `pipeline` (homr) 0.955, `pipeline-smt` 0.769, `pipeline-zeus` 0.659 total note F1. Zeus's solo-staff model
  breaks on scanned orchestral parts (bar counts up to 6x, Song 2 winds/brass near 0) and on keyboards; smt-sys
  ruins the piano reductions (346 / 1581 bars) and drops most keyboard notes. homr stays the default `pipeline`.
- tromr and tfe2e skipped: homr's transformer is derived from TrOMR, and tfe2e (PrIMuS CRNN) reads monophonic
  incipits only; neither is likely to beat homr or Zeus anywhere.
Next: P5 rest (clarity's staff stage), then P6. WSL now has 28 GB (`.wslconfig` `memory=28GB`); transcribes
still run one engine at a time (`--jobs 2`; peak about 10 GB used).
P2's remaining converters land with their recognizers (`semantic.py` with tromr/tfe2e; Zeus writes MusicXML).
Not done: vector pages at a higher render dpi (P3), split of the report by pdfkind.

## 7. Data facts (from this machine's survey)

- `data/anastasia/pdfs/`: 13 PDFs, all scans (`scan` kind, one image per page), 97–405 pages each. The piano reduction is vector.
- `data/ghost/pdfs/`: 9 PDFs, vector pages with a few scanned cover pages (`text` or `scan`). Pages with a music font
  (`Maestro`, `EngraverFontSet`) are `vector`.
- `data/samples/demo-*`: engraved demo samples (vector, DejaVu fonts).
- `pdfkind` timing: about 100 s for a 405-page scan document on this machine (before the scan fast path, it was about 200 s).
- Ground-truth and truth-score layout: see `docs/shows.md` and `docs/engine-benchmark.md`.

## 8. Questions for the user (to answer on the PC)

1. Is `~/museScribe/data` complete (all PDFs and GT), and does `omrbench doctor` list all samples?
2. Should the old native installs (`~/.local/share/omrbench/tools/audiveris`, `venvs/homr`) be removed once the container runs pass?
3. Is the PC user name `konstantin` correct for the paths in this document (it is what the shell shows)?

## 9. Tests and conventions

- `pytest -q tests` must pass before a commit. There are 28 tests; none need Docker.
- Lint: `python -m pyflakes omrbench tests` (only four warnings predate this work: `report.py:435`, `runner.py:193`,
  `metrics/_olimpic_tedn.py:110`, `pipeline/vocal.py:25`).
- Commit messages end with `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>` when made by Claude.
- Do not commit `data/` or `results/` (both are gitignored).
