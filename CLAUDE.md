# museScribe

Benchmark and transcription harness for OMR tools (Audiveris, homr, ...), run in Docker.

**Start with `docs/PC_PLAN.md`** (state, commands, known issues, next steps), then `docs/PLAN_full.md` (master plan).

Quick commands:
- `source ~/.local/share/omrbench/env.sh` (harness venv)
- `omrbench images build | list`, `omrbench doctor`
- `bash scripts/smoke_docker.sh` (GPU, demo sample through the containers)
- `python -m pytest -q tests` (no Docker needed)
