"""Run a subprocess and measure wall time, CPU time, peak memory and GPU usage.

Memory is sampled over the whole process tree (JVM launchers and Python CLIs fork
children), so peak RSS is the peak of the *sum* over all live descendants.
CPU time and the largest single-process RSS come from `wait4` rusage of the direct
child, cross-checked against psutil per-process accounting.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psutil

SAMPLE_INTERVAL_S = 0.1


@dataclass
class RunStats:
    wall_s: float = 0.0
    wall_clock_s: float = 0.0         # time.time() delta; differs from wall_s if the VM was paused
    cpu_user_s: float = 0.0
    cpu_sys_s: float = 0.0
    peak_rss_mb: float = 0.0          # peak of summed RSS over process tree
    peak_single_rss_mb: float = 0.0   # ru_maxrss of largest waited child
    avg_cpu_util_pct: float = 0.0     # (user+sys)/wall*100; >100 means multi-core
    peak_gpu_mem_mb: float | None = None
    avg_gpu_util_pct: float | None = None
    exit_code: int | None = None
    timed_out: bool = False
    commands: list[str] = field(default_factory=list)

    @property
    def cpu_s(self) -> float:
        return self.cpu_user_s + self.cpu_sys_s

    def add(self, other: "RunStats") -> None:
        """Accumulate a sequential run (e.g. one page) into this one."""
        self.wall_s += other.wall_s
        self.wall_clock_s += other.wall_clock_s
        self.cpu_user_s += other.cpu_user_s
        self.cpu_sys_s += other.cpu_sys_s
        self.peak_rss_mb = max(self.peak_rss_mb, other.peak_rss_mb)
        self.peak_single_rss_mb = max(self.peak_single_rss_mb, other.peak_single_rss_mb)
        if other.peak_gpu_mem_mb is not None:
            self.peak_gpu_mem_mb = max(self.peak_gpu_mem_mb or 0.0, other.peak_gpu_mem_mb)
        if other.avg_gpu_util_pct is not None:
            # wall-weighted mean is recomputed by caller via finalize(); keep max as proxy
            self.avg_gpu_util_pct = max(self.avg_gpu_util_pct or 0.0, other.avg_gpu_util_pct)
        self.timed_out = self.timed_out or other.timed_out
        if other.exit_code not in (0, None):
            self.exit_code = other.exit_code
        elif self.exit_code is None:
            self.exit_code = other.exit_code
        self.commands += other.commands
        self.avg_cpu_util_pct = 100.0 * self.cpu_s / self.wall_s if self.wall_s else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cpu_s"] = self.cpu_s
        return d


class _Gpu:
    """Optional NVML sampler. Silently disabled if no NVIDIA driver is visible."""

    def __init__(self) -> None:
        self.ok = False
        try:
            import pynvml  # provided by nvidia-ml-py

            pynvml.nvmlInit()
            self.nv = pynvml
            self.handles = [pynvml.nvmlDeviceGetHandleByIndex(i)
                            for i in range(pynvml.nvmlDeviceGetCount())]
            self.baseline = [pynvml.nvmlDeviceGetMemoryInfo(h).used for h in self.handles]
            self.ok = bool(self.handles)
        except Exception:
            pass

    def sample(self, pids: set[int]) -> tuple[float, float] | None:
        """Return (memory MB attributable to run, utilisation %)."""
        if not self.ok:
            return None
        mem = 0.0
        util = 0.0
        for h, base in zip(self.handles, self.baseline):
            per_proc = None
            try:
                procs = self.nv.nvmlDeviceGetComputeRunningProcesses(h)
                per_proc = sum((p.usedGpuMemory or 0) for p in procs if p.pid in pids)
            except Exception:
                pass
            if not per_proc:
                # WSL often hides per-process info: fall back to device delta
                per_proc = max(0, self.nv.nvmlDeviceGetMemoryInfo(h).used - base)
            mem += per_proc / 2**20
            try:
                util = max(util, float(self.nv.nvmlDeviceGetUtilizationRates(h).gpu))
            except Exception:
                pass
        return mem, util


def run_monitored(cmd: list[str], *, log_path: Path, cwd: Path | None = None,
                  env: dict | None = None, timeout_s: float | None = None) -> RunStats:
    """Run `cmd`, stream stdout/stderr to `log_path`, return resource stats."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    full_env = {**os.environ, **(env or {})}
    gpu = _Gpu()

    cpu_by_pid: dict[int, tuple[float, float]] = {}
    peak_rss = 0.0
    gpu_mem_peak = None
    gpu_utils: list[float] = []
    stop = threading.Event()

    with open(log_path, "ab") as log:
        log.write(f"$ {' '.join(map(str, cmd))}\n".encode())
        log.flush()
        t0 = time.perf_counter()
        t0_clock = time.time()
        proc = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env=full_env,
                                stdout=log, stderr=subprocess.STDOUT)
        root = psutil.Process(proc.pid)

        def sampler() -> None:
            nonlocal peak_rss, gpu_mem_peak
            while not stop.is_set():
                try:
                    tree = [root] + root.children(recursive=True)
                except psutil.Error:
                    tree = []
                rss = 0
                pids = set()
                for p in tree:
                    try:
                        with p.oneshot():
                            rss += p.memory_info().rss
                            ct = p.cpu_times()
                            cpu_by_pid[p.pid] = (ct.user + ct.children_user,
                                                 ct.system + ct.children_system)
                            pids.add(p.pid)
                    except psutil.Error:
                        pass
                peak_rss = max(peak_rss, rss / 2**20)
                g = gpu.sample(pids)
                if g is not None:
                    gpu_mem_peak = max(gpu_mem_peak or 0.0, g[0])
                    gpu_utils.append(g[1])
                stop.wait(SAMPLE_INTERVAL_S)

        th = threading.Thread(target=sampler, daemon=True)
        th.start()
        timed_out = False
        ru = None
        while True:
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            if timeout_s is not None and time.perf_counter() - t0 > timeout_s:
                timed_out = True
                try:
                    tree = [root] + root.children(recursive=True)
                except psutil.Error:
                    tree = []
                for p in tree:
                    try:
                        p.kill()
                    except psutil.Error:
                        pass
                _, status, ru = os.wait4(proc.pid, 0)
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            time.sleep(0.05)
        wall = time.perf_counter() - t0
        wall_clock = time.time() - t0_clock
        stop.set()
        th.join()
        log.write(f"\n[exit={proc.returncode} wall={wall:.1f}s timed_out={timed_out}]\n".encode())

    # wait4 rusage covers the child plus every descendant it reaped. psutil
    # additionally sees processes that were sampled but orphaned. Take the larger.
    ps_user = sum(u for u, _ in cpu_by_pid.values())
    ps_sys = sum(s for _, s in cpu_by_pid.values())
    if ru.ru_utime + ru.ru_stime >= ps_user + ps_sys:
        user, sys_ = ru.ru_utime, ru.ru_stime
    else:
        user, sys_ = ps_user, ps_sys

    stats = RunStats(
        wall_s=wall,
        wall_clock_s=wall_clock,
        cpu_user_s=user,
        cpu_sys_s=sys_,
        peak_rss_mb=peak_rss,
        peak_single_rss_mb=ru.ru_maxrss / 1024.0,  # Linux: KiB
        peak_gpu_mem_mb=gpu_mem_peak,
        avg_gpu_util_pct=(sum(gpu_utils) / len(gpu_utils)) if gpu_utils else None,
        exit_code=proc.returncode,
        timed_out=timed_out,
        commands=[" ".join(map(str, cmd))],
    )
    stats.avg_cpu_util_pct = 100.0 * stats.cpu_s / wall if wall else 0.0
    return stats
