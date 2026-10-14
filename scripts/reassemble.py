"""Re-run only the pipeline assembly on a finished run's work dirs and write a new output run.

    python scripts/reassemble.py anastasia --from 20261013-020114 --to fix4 [--engine pipeline] [--songs 1,2]
    omrbench bench anastasia --run fix4

Work dirs: results/<show>/runs/<from>/<--work-engine>/<sid>/ (default `pipeline`). The engine's
bench.yaml options (--engine) are applied to the assembly (e.g. pipeline-raw = repairs off).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omrbench import config as config_mod  # noqa: E402
from omrbench import log as logmod  # noqa: E402
from omrbench.transcribe import reassemble_run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("show")
    ap.add_argument("--from", dest="src", required=True, help="run with the work dirs")
    ap.add_argument("--to", dest="dst", required=True, help="new run folder for the outputs")
    ap.add_argument("--engine", default="pipeline", help="bench.yaml engine whose options to assemble with")
    ap.add_argument("--work-engine", default="pipeline", help="engine folder of the work dirs in --from")
    ap.add_argument("--songs")
    ap.add_argument("-c", "--config", default="bench.yaml")
    a = ap.parse_args()
    cfg = config_mod.load(Path(a.config))
    logmod.setup(Path(cfg["results_dir"]) / a.show / "runs" / a.dst)
    failed = reassemble_run(cfg, a.show, a.songs.split(",") if a.songs else None, src_run=a.src,
                            work_engine=a.work_engine, dst_run=a.dst, engine=a.engine, force=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
