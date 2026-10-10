"""Run OMR tools in Docker containers, with resource stats taken inside the container.

Every image runs its command through `omr-run` (docker/base/omr_run.py), which writes
stats.json into the mounted work directory. The host only starts `docker run`.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import fields
from pathlib import Path

from .monitor import RunStats, run_monitored

REPO_DOCKER = Path(__file__).resolve().parent.parent / "docker"

# image name -> (tag, Dockerfile dir, build args)
IMAGES = {
    "base-cpu": ("omrbench/base:cpu", "base", {"BASE_IMAGE": "ubuntu:24.04"}),
    "base-cuda": ("omrbench/base:cuda", "base", {"BASE_IMAGE": "nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04"}),
    "audiveris": ("omrbench/audiveris:5.11.0", "audiveris", {"BASE_IMAGE": "omrbench/base:cpu"}),
    "homr": ("omrbench/homr:0.7.0", "homr", {"BASE_IMAGE": "omrbench/base:cuda"}),
}
# GPU check: a CUDA base image that only has nvidia-smi
GPU_PROBE_IMAGE = "nvidia/cuda:12.6.3-base-ubuntu24.04"


def docker_ok() -> tuple[bool, str]:
    out = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                         capture_output=True, text=True)
    return out.returncode == 0, (out.stdout.strip() or out.stderr.strip()[-200:])


def gpu_ok() -> tuple[bool, str]:
    out = subprocess.run(["docker", "run", "--rm", "--gpus", "all", GPU_PROBE_IMAGE, "nvidia-smi",
                          "--query-gpu=name,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True)
    return out.returncode == 0, (out.stdout.strip() or out.stderr.strip()[-200:])


def image_present(tag: str) -> bool:
    return subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode == 0


def build_cmd(name: str) -> list[str]:
    tag, ctx, args = IMAGES[name]
    cmd = ["docker", "build", "-t", tag]
    for k, v in args.items():
        cmd += ["--build-arg", f"{k}={v}"]
    return cmd + [str(REPO_DOCKER / ctx)]


def run_cmd(image: str, cmd: list[str], *, mounts: dict[Path, str], gpu: bool = False,
            stats_name: str = "stats.json", workdir: str = "/work", read_only: set[str] = frozenset()) -> list[str]:
    """`docker run` line: mounts maps host dir -> container dir (ro if the container path is in read_only)."""
    args = ["docker", "run", "--rm"]
    if gpu:
        args += ["--gpus", "all"]
    for host, target in mounts.items():
        mode = ":ro" if target in read_only else ""
        args += ["-v", f"{host}:{target}{mode}"]
    args += ["-w", workdir, image, "omr-run", "--stats", f"{workdir}/{stats_name}", "--"] + cmd
    return args


def run_in_container(image: str, cmd: list[str], *, mounts: dict[Path, str], log_path: Path,
                     gpu: bool = False, timeout_s: float | None = None,
                     stats_name: str = "stats.json") -> RunStats:
    """Run `cmd` in `image` with /work mounted; return the stats omr-run wrote there.

    Falls back to the host-side stats of the `docker run` process if omr-run wrote nothing.
    """
    work = next(h for h, t in mounts.items() if t == "/work")
    (work / stats_name).unlink(missing_ok=True)
    st = run_monitored(run_cmd(image, cmd, mounts=mounts, gpu=gpu, stats_name=stats_name),
                       log_path=log_path, timeout_s=timeout_s)
    if not (work / stats_name).exists():
        return st
    data = json.loads((work / stats_name).read_text(encoding="utf-8"))
    names = {f.name for f in fields(RunStats)}
    inside = RunStats(**{k: v for k, v in data.items() if k in names})
    inside.timed_out = st.timed_out
    return inside
