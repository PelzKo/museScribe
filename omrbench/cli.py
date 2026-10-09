"""omrbench command line.

  omrbench doctor                      check engines, GPU and data folder
  omrbench new-sample NAME             create data/NAME with a meta.yaml template
  omrbench demo                        create 2 synthetic samples to smoke-test the setup
  omrbench run [--engines a,b] [--samples x,y] [--exclude x,y] [--prefix_matching]
               [--resume RUN_ID]
  omrbench transcribe [--engine pipeline] [--samples x,y] [--exclude x,y] [--prefix_matching]
               [--force] [--jobs N] [--keep-awake]
                                       <pdf>.musicxml next to every PDF + combined.mscz
  omrbench gen-meta SHOW_YAML [--songs 5,6] [--dry-run]
                                       song folders (yamls + PDFs) from a songs.xlsx workbook
  omrbench score RUN_DIR               re-score an existing run (e.g. after fixing a GT)
  omrbench report RUN_DIR              regenerate report.md (e.g. after adding correction times)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import config as config_mod
from . import dataset

META_TEMPLATE = Path(__file__).resolve().parent.parent / "meta.example.yaml"


def _csv(s: str | None) -> list[str] | None:
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def cmd_doctor(cfg: dict, _args) -> int:
    from .runner import host_info

    h = host_info()
    print(f"host   : {h['cpu']} | {h['cores_logical']} threads | {h['ram_gb']} GB | WSL={h['wsl']}")
    print(f"gpu    : {h['gpus'] or 'none visible to NVML'}   (device setting: {cfg['device']})")
    if cfg["device"] == "cuda" and not h["gpus"]:
        print("         WARNING device=cuda but no GPU visible; install the NVIDIA Windows driver "
              "with WSL support and check `nvidia-smi` inside WSL")
    print(f"home   : {cfg['home']}")
    data = Path(cfg["data_dir"])
    ext: set[str] = set()
    if data.is_dir():
        samples, warns = dataset.discover(data, None, cfg.get("musescore_cli"))
        ext = {n for s in samples for n in s.external}
        print(f"data   : {data} -> {len(samples)} samples "
              f"({', '.join(f'{s.id}[{s.score_type}]' for s in samples)})")
        for w in warns:
            print(f"         WARN {w}")
    else:
        print(f"data   : {data} does not exist (omrbench new-sample NAME)")
    ok_all = True
    for e in config_mod.engines(cfg, ext):
        ok, ver = e.check()
        ok_all &= ok
        print(f"engine : {e.name:<16} {'OK ' if ok else 'MISSING'} {ver}")
    return 0 if ok_all else 1


def cmd_new_sample(cfg: dict, args) -> int:
    d = Path(cfg["data_dir"]) / args.name
    d.mkdir(parents=True, exist_ok=True)
    (d / "external").mkdir(exist_ok=True)
    if not (d / "meta.yaml").exists():
        shutil.copyfile(META_TEMPLATE, d / "meta.yaml")
    print(f"created {d}\n  put the score as {d / 'input.pdf'}\n  ground truth as {d / 'gt.musicxml'}"
          f"\n  edit {d / 'meta.yaml'}\n  optional manual exports in {d / 'external'}/<tool>.musicxml")
    return 0


def cmd_demo(cfg: dict, _args) -> int:
    from .demo import make_demos

    for d in make_demos(Path(cfg["data_dir"])):
        print(f"created {d}")
    return 0


def cmd_run(cfg: dict, args) -> int:
    from .runner import run

    if args.jobs:
        cfg.setdefault("scoring", {})["jobs"] = args.jobs
    run_dir = run(cfg, engines_only=_csv(args.engines), samples_only=_csv(args.samples),
                  samples_exclude=_csv(args.exclude), prefix_matching=args.prefix_matching,
                  run_id=args.resume or args.run_id, resume=bool(args.resume),
                  do_score=not args.no_score)
    print(f"\nreport: {run_dir / 'report.md'}")
    return 0


def cmd_transcribe(cfg: dict, args) -> int:
    from .transcribe import transcribe

    failed = transcribe(cfg, engine=args.engine, samples_only=_csv(args.samples),
                        samples_exclude=_csv(args.exclude), prefix_matching=args.prefix_matching,
                        force=args.force, run_id=args.run_id, jobs=args.jobs,
                        awake=args.keep_awake)
    return 1 if failed else 0


def cmd_gen_meta(cfg: dict, args) -> int:
    from .genmeta import generate

    try:
        problems = generate(Path(args.show), Path(cfg["data_dir"]), _csv(args.songs), args.dry_run)
    except (OSError, ValueError) as e:
        print(f"ERROR {e}")
        return 1
    return 1 if problems else 0


def cmd_score(cfg: dict, args) -> int:
    from .runner import rescore

    if args.jobs:
        cfg.setdefault("scoring", {})["jobs"] = args.jobs
    rescore(Path(args.run_dir), cfg)
    print(f"report: {Path(args.run_dir) / 'report.md'}")
    return 0


def cmd_report(_cfg: dict, args) -> int:
    from .report import write_report

    print(f"report: {write_report(Path(args.run_dir))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="omrbench", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", default="bench.yaml", help="config file (default bench.yaml)")
    ap.add_argument("--data", help="override data_dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    p = sub.add_parser("new-sample")
    p.add_argument("name")
    sub.add_parser("demo")
    p = sub.add_parser("run")
    p.add_argument("--engines", help="comma-separated engine names (default: all enabled)")
    p.add_argument("--samples", help="comma-separated sample ids (default: all)")
    p.add_argument("--exclude", help="comma-separated sample ids to skip")
    p.add_argument("--prefix_matching", "--prefix-matching", action="store_true",
                   help="match --samples/--exclude as id prefixes (e.g. --exclude demo)")
    p.add_argument("--run-id", help="name of the results folder (default: timestamp)")
    p.add_argument("--resume", metavar="RUN_ID", help="continue a run, re-using successful engine outputs")
    p.add_argument("--jobs", type=int, help="parallel scoring workers")
    p.add_argument("--no-score", action="store_true", help="only run engines")
    p = sub.add_parser("transcribe", help="transcribe every PDF of the samples to <pdf>.musicxml")
    p.add_argument("--engine", default="pipeline", help="engine to run (default: pipeline)")
    p.add_argument("--samples", help="comma-separated sample ids (default: all)")
    p.add_argument("--exclude", help="comma-separated sample ids to skip")
    p.add_argument("--prefix_matching", "--prefix-matching", action="store_true",
                   help="match --samples/--exclude as id prefixes")
    p.add_argument("--force", action="store_true", help="overwrite existing <pdf>.musicxml")
    p.add_argument("--jobs", type=int,
                   help="PDFs transcribed at the same time (default: transcribe_jobs in bench.yaml, 2)")
    p.add_argument("--run-id", help="name of the work folder in results/ (default: transcribe-<timestamp>)")
    p.add_argument("--keep-awake", "--keep_awake", action="store_true",
                   help="keep Windows (also from WSL) from sleeping until the run ends")
    p = sub.add_parser("gen-meta", help="write song folders from data/_<show>/show.yaml + songs.xlsx")
    p.add_argument("show", help="show file, e.g. data/_anastasia/show.yaml")
    p.add_argument("--songs", help="comma-separated sheet names (default: all)")
    p.add_argument("--dry-run", action="store_true", help="only print what would change")
    p = sub.add_parser("score")
    p.add_argument("run_dir")
    p.add_argument("--jobs", type=int)
    p = sub.add_parser("report")
    p.add_argument("run_dir")
    args = ap.parse_args(argv)

    from . import log as logmod
    logmod.setup()
    cfg = config_mod.load(Path(args.config))
    if args.data:
        cfg["data_dir"] = str(Path(args.data).resolve())
    return {"doctor": cmd_doctor, "new-sample": cmd_new_sample, "demo": cmd_demo, "run": cmd_run,
            "transcribe": cmd_transcribe, "gen-meta": cmd_gen_meta, "score": cmd_score, "report": cmd_report}[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
