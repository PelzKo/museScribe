"""Run OMR tools in Docker containers.

Paths: a container mounts its work directory at the SAME absolute path as on the host, so
commands and file arguments need no translation, and the homr crop pool can read crops from
the results tree. The container runs as the host user (no root-owned outputs).

Stats: single commands run through `omr-run` (docker/base/omr_run.py), which writes stats.json
into the mounted work directory; the host reads it back. The host only starts `docker run`.
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import fields
from pathlib import Path

from .monitor import RunStats, run_monitored

REPO = Path(__file__).resolve().parent.parent
REPO_DOCKER = REPO / "docker"

# name -> (tag, Dockerfile dir under docker/, build args)
IMAGES = {
    "base-cpu": ("omrbench/base:cpu", "base", {"BASE_IMAGE": "ubuntu:24.04"}),
    "base-cuda": ("omrbench/base:cuda", "base", {"BASE_IMAGE": "nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04"}),
    "audiveris": ("omrbench/audiveris:5.11.0", "audiveris", {"BASE_IMAGE": "omrbench/base:cpu"}),
    "homr": ("omrbench/homr:0.7.0", "homr", {"BASE_IMAGE": "omrbench/base:cuda"}),
    "oemer": ("omrbench/oemer:0.1.8", "oemer", {"BASE_IMAGE": "omrbench/base:cuda"}),
    "clarity": ("omrbench/clarity:c6bb8a4", "clarity", {"BASE_IMAGE": "omrbench/base:cpu"}),
    "transcoda": ("omrbench/transcoda:b529f8a", "transcoda", {"BASE_IMAGE": "omrbench/base:cpu"}),
}
# GPU check: a CUDA base image that only has nvidia-smi
GPU_PROBE_IMAGE = "nvidia/cuda:12.6.3-base-ubuntu24.04"
HOMR_WORKER = "/opt/homr/bin/python"
HOMR_WORKER_SCRIPT = "/opt/homr/worker.py"


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


def check_image(name: str) -> tuple[bool, str]:
    """(available, reason) for an engine that runs in image `name`."""
    ok, ver = docker_ok()
    if not ok:
        return False, f"docker not available: {ver}"
    tag = IMAGES[name][0]
    if not image_present(tag):
        return False, f"image {tag} not built (run: omrbench images build {name})"
    return True, f"{tag} (container)"


def build_cmd(name: str) -> list[str]:
    """Build context is the repo root, so Dockerfiles can COPY files from omrbench/."""
    tag, ctx, args = IMAGES[name]
    cmd = ["docker", "build", "-t", tag, "-f", str(REPO_DOCKER / ctx / "Dockerfile")]
    for k, v in args.items():
        cmd += ["--build-arg", f"{k}={v}"]
    return cmd + [str(REPO)]


def run_cmd(image: str, cmd: list[str], *, mounts: dict[Path, str], gpu: bool = False,
            env: dict | None = None, cwd: str | None = None, interactive: bool = False,
            name: str | None = None, stats_file: str | None = None) -> list[str]:
    """The `docker run` argv. mounts: host path -> container path (identical in our use).

    stats_file (absolute container path): wrap cmd in omr-run, which writes stats there.
    """
    args = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    if interactive:
        args.append("-i")
    if name:
        args += ["--name", name]
    if gpu:
        args += ["--gpus", "all"]
    for k, v in (env or {}).items():
        args += ["-e", f"{k}={v}"]
    for host, target in mounts.items():
        args += ["-v", f"{host}:{target}"]
    if cwd:
        args += ["-w", cwd]
    args.append(image)
    if stats_file:
        args += ["omr-run", "--stats", stats_file, "--"]
    return args + [str(c) for c in cmd]


def pool_cmd(image: str, *, mounts: dict[Path, str], gpu: bool, env: dict | None) -> list[str]:
    """Launch prefix for a long-lived homr worker (JSON lines on stdin/stdout)."""
    return run_cmd(image, [HOMR_WORKER, HOMR_WORKER_SCRIPT], mounts=mounts, gpu=gpu, env=env,
                   interactive=True)


def kill(name: str) -> None:
    subprocess.run(["docker", "kill", name], capture_output=True)


def run_in_container(image: str, cmd: list[str], *, workdir: Path, log_path: Path,
                     gpu: bool = False, env: dict | None = None, cwd: Path | None = None,
                     timeout_s: float | None = None, stats_name: str = "stats.json") -> RunStats:
    """Run `cmd` in `image` with `workdir` mounted at its own path; return omr-run's stats.

    Falls back to the host-side stats of the `docker run` process if omr-run wrote nothing.
    On timeout the container is killed by name (`docker run` alone would keep it alive).
    """
    stats = workdir / stats_name
    stats.unlink(missing_ok=True)
    name = f"omrbench-{uuid.uuid4().hex[:12]}"
    argv = run_cmd(image, cmd, mounts={workdir: str(workdir)}, gpu=gpu, env=env,
                   cwd=str(cwd or workdir), name=name, stats_file=str(stats))
    st = run_monitored(argv, log_path=log_path, timeout_s=timeout_s)
    if st.timed_out:
        kill(name)
    if not stats.exists():
        return st
    data = json.loads(stats.read_text(encoding="utf-8"))
    names = {f.name for f in fields(RunStats)}
    inside = RunStats(**{k: v for k, v in data.items() if k in names})
    inside.timed_out = st.timed_out
    return inside
