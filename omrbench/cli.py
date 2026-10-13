"""omrbench command line.

  omrbench doctor                      check engines, GPU, shows and samples
  omrbench transcribe SHOW [--songs 1,2] [--parts Horn,Bass] [--force] [--jobs N] [--keep-awake]
                                       songs of data/SHOW -> results/SHOW/<song>/*.musicxml
  omrbench transcribe [--samples x,y] [--exclude x,y] [--prefix_matching] [--force]
                                       every PDF of data/samples/* -> results/samples/<sample>/
  omrbench bench SHOW [--songs 1,2] [--run TS] [--transcribe] [--full]
                                       note F1 of the latest outputs vs data/SHOW/truth
  omrbench check SHOW [--songs 1,2] [-v] [--export DIR]
                                       validate songs.xlsx, show what every part resolves to
  omrbench images list|build [base-cpu base-cuda base-cuda11 base-cuda13 audiveris homr oemer clarity transcoda smt-fp smt-sys zeus mozart]
                                       list or build the Docker images (docker/)
  omrbench new-sample NAME             create data/samples/NAME with a meta.yaml template
  omrbench demo                        create 2 synthetic samples to smoke-test the setup
  omrbench run [--engines a,b] [--samples x,y] [--exclude x,y] [--prefix_matching]
               [--resume RUN_ID]       benchmark engines on data/samples
  omrbench score RUN_DIR               re-score an existing run (e.g. after fixing a GT)
  omrbench report RUN_DIR              regenerate report.md (e.g. after editing sample meta)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import config as config_mod
from . import dataset

META_TEMPLATE = Path(__file__).resolve().parent.parent / "meta.example.yaml"


def _csv(s: str | None) -> list[str] | None:
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def _doctor_docker(device: str) -> None:
    from . import containers as C

    ok, ver = C.docker_ok()
    print(f"docker : {'OK ' if ok else 'MISSING'} {ver}")
    if not ok:
        return
    if device == "cuda":
        ok, info = C.gpu_ok()
        print(f"docker gpu: {'OK ' if ok else 'FAILED'} {info}")
    else:
        print("docker gpu: skipped (device cpu, requires_gpu engines are skipped)")
    for name, (tag, _, _) in C.IMAGES.items():
        print(f"image  : {name:<10} {'OK ' if C.image_present(tag) else 'MISSING'} {tag}")


def cmd_images(_cfg: dict, args) -> int:
    from . import containers as C

    names = args.names or list(C.IMAGES)
    unknown = [n for n in names if n not in C.IMAGES]
    if unknown:
        raise SystemExit(f"unknown image(s) {unknown} (known: {list(C.IMAGES)})")
    if args.action == "list":
        for n in names:
            tag = C.IMAGES[n][0]
            print(f"{n:<10} {'built' if C.image_present(tag) else 'not built':<10} {tag}")
        return 0
    for n in names:  # base images first, in the order they are listed
        print(f"==> building {n}")
        if subprocess.run(C.build_cmd(n)).returncode != 0:
            print(f"build of {n} failed")
            return 1
    return 0


def cmd_doctor(cfg: dict, _args) -> int:
    from .runner import host_info

    h = host_info()
    print(f"host   : {h['cpu']} | {h['cores_logical']} threads | {h['ram_gb']} GB | WSL={h['wsl']}")
    print(f"gpu    : {h['gpus'] or 'none visible to NVML'}   (device setting: {cfg['device']})")
    if cfg["device"] == "cuda" and not h["gpus"]:
        print("         WARNING device=cuda but no GPU visible; install the NVIDIA Windows driver "
              "with WSL support and check `nvidia-smi` inside WSL")
    print(f"home   : {cfg['home']}")
    _doctor_docker(cfg["device"])
    from . import project

    for folder in project.projects(Path(cfg["data_dir"])):
        try:
            p = project.load(folder)
            print(f"show   : {folder} -> {len(p.songs)} songs, "
                  f"truth for {', '.join(s.id for s in p.songs.values() if s.truth) or 'none'}")
        except Exception as e:  # noqa: BLE001
            print(f"show   : {folder} ERROR {type(e).__name__}: {e}")
    data = Path(cfg["samples_dir"])
    if data.is_dir():
        samples, warns = dataset.discover(data, None, cfg.get("musescore_cli"),
                                          cache=dataset.cache_dir(cfg))
        print(f"data   : {data} -> {len(samples)} samples "
              f"({', '.join(f'{s.id}[{s.score_type}]' for s in samples)})")
        for w in warns:
            print(f"         WARN {w}")
    else:
        print(f"data   : {data} does not exist (omrbench new-sample NAME)")
    ok_all = True
    for e in config_mod.engines(cfg):
        ok, ver = e.check()
        ok_all &= ok
        print(f"engine : {e.name:<16} {'OK ' if ok else 'MISSING'} {ver}")
    return 0 if ok_all else 1


def cmd_new_sample(cfg: dict, args) -> int:
    d = Path(cfg["samples_dir"]) / args.name
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "meta.yaml").exists():
        shutil.copyfile(META_TEMPLATE, d / "meta.yaml")
    print(f"created {d}\n  put the score as {d / 'input.pdf'}\n  ground truth as {d / 'gt.musicxml'}"
          f"\n  edit {d / 'meta.yaml'}")
    return 0


def cmd_demo(cfg: dict, _args) -> int:
    from .demo import make_demos

    for d in make_demos(Path(cfg["samples_dir"])):
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

    if args.show and (args.samples or args.exclude):
        raise SystemExit("--samples/--exclude are for data/samples; with a show use --songs/--parts")
    if not args.show and (args.songs or args.parts):
        raise SystemExit("--songs/--parts need a show, e.g. `omrbench transcribe anastasia --songs 1`")
    failed = transcribe(cfg, project=args.show, songs=_csv(args.songs), parts=_csv(args.parts),
                        engine=args.engine, samples_only=_csv(args.samples),
                        samples_exclude=_csv(args.exclude), prefix_matching=args.prefix_matching,
                        force=args.force, run_id=args.run_id, jobs=args.jobs,
                        awake=args.keep_awake)
    return 1 if failed else 0


def cmd_bench(cfg: dict, args) -> int:
    from .bench import bench

    if args.transcribe:
        from . import project
        from .transcribe import transcribe

        if args.run:
            raise SystemExit("--transcribe benchmarks the new outputs; leave out --run")
        folder = project.find(Path(cfg["data_dir"]), args.show)
        if folder is None:
            raise SystemExit(f"no show '{args.show}' in {cfg['data_dir']}")
        songs, _ = project.load(folder).select(_csv(args.songs))
        if not (with_truth := [s.id for s in songs if s.truth]):
            raise SystemExit("no selected song has a truth file (songs.xlsx, B2)")
        transcribe(cfg, project=args.show, songs=with_truth,
                   force=args.force, jobs=args.jobs, awake=args.keep_awake)
    problems = bench(cfg, args.show, songs=_csv(args.songs), run=args.run, full=args.full,
                     bench_id=args.bench_id)
    return 1 if problems else 0


def cmd_components(cfg: dict, args) -> int:
    from datetime import datetime

    from . import components as C

    results = Path(cfg["results_dir"])
    if args.show:
        run_root = results / args.show / "runs" / args.run
        truth = C.truth_bars(args.show, results)
        out = results / args.show / "components"
    else:
        run_root = results / "samples" / "bench" / args.run
        truth = C.sample_truth_bars(Path(cfg["data_dir"]))
        out = results / "samples" / "components"
    if not (run_root / "pipeline").is_dir():
        raise SystemExit(f"no pipeline work dirs in {run_root}")
    out = out / (args.id or datetime.now().strftime("%Y%m%d-%H%M%S"))
    if args.what == "ocr":
        C.ocr_bench(run_root, truth, ["tesseract", "easyocr", "doctr", "paddle"], out)
        print(f"report: {out / 'ocr.md'}")
    else:
        C.layout_bench(cfg, run_root, truth, out, int(cfg.get("dpi", 300)))
        print(f"report: {out / 'layout.md'}")
    return 0


def cmd_check(cfg: dict, args) -> int:
    from . import project

    folder = project.find(Path(cfg["data_dir"]), args.show)
    if folder is None:
        print(f"ERROR no show '{args.show}' (a folder with show.yaml in {cfg['data_dir']})")
        return 1
    try:
        problems = project.check(project.load(folder), _csv(args.songs), args.verbose,
                                 Path(args.export) if args.export else None,
                                 Path(cfg["results_dir"]) / "cache", cfg.get("musescore_cli"))
    except (OSError, ValueError) as e:
        print(f"ERROR {e}")
        return 1
    print(f"{problems} problem(s)" if problems else "ok")
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
    p = sub.add_parser("images", help="list or build the Docker images")
    p.add_argument("action", choices=["list", "build"])
    p.add_argument("names", nargs="*", help="base-cpu base-cuda base-cuda11 base-cuda13 audiveris homr oemer clarity transcoda smt-fp smt-sys zeus mozart (default: all)")
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
    p = sub.add_parser("transcribe", help="transcribe the songs of a show (or the samples) to results/")
    p.add_argument("show", nargs="?", help="show in data/ (e.g. anastasia); omit for data/samples")
    p.add_argument("--songs", help="comma-separated song ids = sheet names (default: all)")
    p.add_argument("--parts", help="comma-separated part names = PDF stems (default: all)")
    p.add_argument("--engine", default="pipeline", help="engine to run (default: pipeline)")
    p.add_argument("--samples", help="comma-separated sample ids (default: all)")
    p.add_argument("--exclude", help="comma-separated sample ids to skip")
    p.add_argument("--prefix_matching", "--prefix-matching", action="store_true",
                   help="match --samples/--exclude as id prefixes")
    p.add_argument("--force", action="store_true", help="redo PDFs whose inputs are unchanged")
    p.add_argument("--jobs", type=int,
                   help="PDFs transcribed at the same time (default: transcribe_jobs in bench.yaml, 2)")
    p.add_argument("--run-id", help="name of the run folder in results/<show>/runs/ (default: timestamp)")
    p.add_argument("--keep-awake", "--keep_awake", action="store_true",
                   help="keep Windows (also from WSL) from sleeping until the run ends")
    p = sub.add_parser("bench", help="score a show's outputs against its truth scores")
    p.add_argument("show", help="show in data/ (e.g. anastasia)")
    p.add_argument("--songs", help="comma-separated song ids (default: all with a truth file)")
    p.add_argument("--run", metavar="TS", help="score the outputs of results/<show>/runs/TS instead of the latest")
    p.add_argument("--transcribe", action="store_true", help="transcribe the songs first (unchanged parts are skipped)")
    p.add_argument("--force", action="store_true", help="with --transcribe: redo every part")
    p.add_argument("--jobs", type=int, help="with --transcribe: PDFs at the same time")
    p.add_argument("--keep-awake", "--keep_awake", action="store_true", help="with --transcribe")
    p.add_argument("--full", action="store_true", help="also OMR-NED and TEDn per part (slow)")
    p.add_argument("--bench-id", help="name of the folder in results/<show>/bench/ (default: timestamp)")
    p = sub.add_parser("components", help="component benchmarks on a finished pipeline run (layout, ocr)")
    p.add_argument("what", choices=["layout", "ocr"],
                   help="layout: OLA vs Audiveris; ocr: bar-number tokens per OCR engine (from the caches "
                        "of pipeline runs with ocr_engine: X on the same run)")
    p.add_argument("show", nargs="?", help="show in data/ (runs in results/<show>/runs/); omit for samples "
                                          "(runs in results/samples/bench/)")
    p.add_argument("--run", required=True, help="run folder with pipeline/<id> work dirs and _pages/")
    p.add_argument("--id", help="name of the report folder (default: timestamp)")
    p = sub.add_parser("check", help="validate data/<show>/songs.xlsx and show the resolved parts")
    p.add_argument("show", help="show in data/ (e.g. anastasia) or its folder")
    p.add_argument("--songs", help="comma-separated sheet names (default: all)")
    p.add_argument("-v", "--verbose", action="store_true", help="print every part's resolved meta")
    p.add_argument("--export", metavar="DIR", help="also write <DIR>/<song>/<part>.yaml (inspection only)")
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
        cfg["samples_dir"] = str(Path(args.data).resolve() / "samples")
    return {"doctor": cmd_doctor, "images": cmd_images, "new-sample": cmd_new_sample, "demo": cmd_demo, "run": cmd_run,
            "transcribe": cmd_transcribe, "check": cmd_check, "components": cmd_components, "bench": cmd_bench, "score": cmd_score, "report": cmd_report}[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
