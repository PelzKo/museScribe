"""A pool of persistent homr workers (see _homr_worker.py), shared by all samples.

On this kind of machine (8 cores / 16 threads, CPU inference) 8 workers x 2 ONNX
threads transcribe crops ~4x faster than one `homr` process per crop with all threads:
no per-crop model loading, and many small inferences scale better across processes
than across threads. Results are identical.

bench.yaml, under the homr (or pipeline: homr:) engine:
    workers: auto      # auto = logical CPUs / threads
    threads: 2         # ONNX intra-op threads per worker
    nice: 0            # >0: lower CPU priority (measured slower here: homr is on the critical path too)
"""
from __future__ import annotations

import atexit
import json
import os
import queue
import select
import subprocess
import tempfile
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from .. import log as logmod

WORKER = Path(__file__).with_name("_homr_worker.py")
LOG = logmod.get("homr")


@dataclass
class CropResult:
    image: Path
    ok: bool
    error: str = ""
    log: str = ""
    wall_s: float = 0.0
    cpu_s: float = 0.0
    rss_mb: float = 0.0
    timed_out: bool = False


class _Worker:
    def __init__(self, python: Path, threads: int, env: dict, idx: int, nice: int = 0):
        self.python, self.threads, self.env, self.idx = python, threads, env, idx
        self.nice = nice
        self.proc: subprocess.Popen | None = None
        self.errf = None
        self.n = 0

    def start(self, timeout_s: float = 300) -> None:
        # stderr to a file: native libraries may write there outside a task, a pipe
        # nobody reads would fill up and block the worker
        self.kill()                      # a dead predecessor: reap it, close its files
        self.errf = tempfile.TemporaryFile()
        self.proc = subprocess.Popen([str(self.python), str(WORKER), str(self.threads), str(self.nice)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.errf, text=True, bufsize=1,
                                     env={**os.environ, **self.env})
        msg = self._read(timeout_s)
        if not msg or not msg.get("ready"):
            err = self._stderr_tail()
            self.kill()
            raise RuntimeError(f"homr worker {self.idx} did not start: {err or 'no reply'}")
        LOG.debug(f"homr worker {self.idx} ready (pid {self.proc.pid}, {self.threads} threads, "
                  f"gpu={msg.get('gpu')})", extra={"sample": "-"})

    def _read(self, timeout_s: float | None) -> dict | None:
        out = self.proc.stdout
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while True:
            wait = None if deadline is None else max(0.0, deadline - time.monotonic())
            r, _, _ = select.select([out], [], [], wait)
            if not r:
                return None              # timeout
            line = out.readline()
            if not line:
                return None              # worker died
            try:
                return json.loads(line)
            except ValueError:
                continue

    def _stderr_tail(self) -> str:
        try:
            self.errf.seek(0, os.SEEK_END)
            size = self.errf.tell()
            self.errf.seek(max(0, size - 3000))
            return self.errf.read().decode(errors="replace").strip()[-1500:]
        except Exception:  # noqa: BLE001
            return ""

    def run(self, image: Path, timeout_s: float) -> CropResult:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        self.n += 1
        self.proc.stdin.write(json.dumps({"id": self.n, "image": str(image)}) + "\n")
        self.proc.stdin.flush()
        t0 = time.perf_counter()
        msg = self._read(timeout_s)
        if msg is None:
            died = self.proc.poll() is not None
            err = self._stderr_tail()
            self.kill()
            if died:
                return CropResult(image, False, f"homr worker crashed: {err[-300:]}", err,
                                  time.perf_counter() - t0)
            return CropResult(image, False, f"timeout after {timeout_s:.0f}s", "",
                              time.perf_counter() - t0, timed_out=True)
        return CropResult(image, bool(msg.get("ok")), msg.get("error", ""), msg.get("log", ""),
                          float(msg.get("wall_s", 0)), float(msg.get("cpu_s", 0)),
                          float(msg.get("rss_mb", 0)))

    def kill(self) -> None:
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                pass
            for pipe in (self.proc.stdin, self.proc.stdout):
                try:
                    pipe.close()
                except Exception:  # noqa: BLE001
                    pass
            self.proc = None
        if self.errf is not None:
            self.errf.close()
            self.errf = None


class HomrPool:
    def __init__(self, python: Path, workers: int, threads: int, env: dict, nice: int = 0):
        self.workers = [_Worker(python, threads, env, i + 1, nice) for i in range(workers)]
        self.q: queue.Queue = queue.Queue()
        self.threads = []
        self.closed = False
        t0 = time.perf_counter()
        # start the workers in parallel: each loads the models
        errs = []

        def boot(w):
            try:
                w.start()
            except Exception as e:  # noqa: BLE001
                errs.append(str(e))
        boots = [threading.Thread(target=boot, args=(w,)) for w in self.workers]
        [b.start() for b in boots]
        [b.join() for b in boots]
        if errs:
            self.close()
            raise RuntimeError(errs[0])
        LOG.info(f"homr pool: {workers} workers x {threads} threads, started in "
                 f"{time.perf_counter() - t0:.1f}s", extra={"sample": "-"})
        for w in self.workers:
            th = threading.Thread(target=self._loop, args=(w,), daemon=True)
            th.start()
            self.threads.append(th)

    def _loop(self, w: _Worker) -> None:
        while True:
            item = self.q.get()
            if item is None:
                return
            image, timeout_s, fut = item
            if not fut.set_running_or_notify_cancel():
                continue
            try:
                fut.set_result(w.run(image, timeout_s))
            except Exception as e:  # noqa: BLE001 - a broken worker fails only this crop
                w.kill()
                fut.set_result(CropResult(image, False, f"{type(e).__name__}: {e}"))

    def submit(self, image: Path, timeout_s: float) -> Future:
        fut: Future = Future()
        self.q.put((Path(image).resolve(), timeout_s, fut))
        return fut

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        for _ in self.threads:
            self.q.put(None)
        for th in self.threads:
            th.join(timeout=5)
        for w in self.workers:
            if w.proc is not None:
                try:
                    w.proc.stdin.close()
                except Exception:  # noqa: BLE001
                    pass
            w.kill()


_POOL: HomrPool | None = None
_LOCK = threading.Lock()


def default_workers(threads: int) -> int:
    return max(1, (os.cpu_count() or 2) // max(1, threads))


def get_pool(python: Path, workers, threads: int, env: dict, nice: int = 0) -> HomrPool:
    """The process-wide pool (created on first use, closed at exit)."""
    global _POOL
    with _LOCK:
        if _POOL is None or _POOL.closed:
            n = default_workers(threads) if workers in (None, "auto") else int(workers)
            _POOL = HomrPool(python, n, threads, env, nice)
            atexit.register(_POOL.close)
        return _POOL
