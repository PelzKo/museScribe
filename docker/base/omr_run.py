"""omr-run: run a command inside a container and write its resource use to stats.json.

Host-side sampling can't see into the Docker Desktop VM, so the monitor lives in the image.
Usage: omr-run --stats /work/stats.json -- <command...>
Samples the process tree every 0.1 s (summed RSS, CPU time) and GPU memory via NVML if present.
"""
import argparse
import json
import subprocess
import sys
import time

import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    _GPU = pynvml.nvmlDeviceGetHandleByIndex(0)
except Exception:  # no GPU in this container (CPU image) or no driver
    _GPU = None


def _tree(proc: psutil.Process) -> list[psutil.Process]:
    try:
        return [proc] + proc.children(recursive=True)
    except psutil.Error:
        return [proc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--interval", type=float, default=0.1)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        ap.error("no command given")

    stats = {"wall_s": 0.0, "cpu_user_s": 0.0, "cpu_sys_s": 0.0, "peak_rss_mb": 0.0,
             "peak_gpu_mem_mb": None, "exit_code": None, "timed_out": False, "commands": [" ".join(cmd)]}
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd)
    ps = psutil.Process(proc.pid)
    gpu_peak = None
    cpu = None
    while proc.poll() is None:
        procs = _tree(ps)
        rss = 0
        for p in procs:
            try:
                rss += p.memory_info().rss
            except psutil.Error:
                pass
        stats["peak_rss_mb"] = max(stats["peak_rss_mb"], rss / 2**20)
        try:  # last sample before exit is kept: the process is gone once poll() returns
            cpu = ps.cpu_times()
        except psutil.Error:
            pass
        if _GPU is not None:
            try:
                used = pynvml.nvmlDeviceGetMemoryInfo(_GPU).used / 2**20
                gpu_peak = max(gpu_peak or 0.0, used)
            except pynvml.NVMLError:
                pass
        time.sleep(args.interval)
    stats["wall_s"] = time.perf_counter() - t0
    if cpu is not None:  # children_* include finished grandchildren, so this is the whole tree
        stats["cpu_user_s"], stats["cpu_sys_s"] = cpu.user + cpu.children_user, cpu.system + cpu.children_system
    stats["peak_gpu_mem_mb"] = gpu_peak
    stats["exit_code"] = proc.returncode
    with open(args.stats, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
