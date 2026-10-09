"""Run log: every info, warning and error of a run in results/<run>/run.log.

    2026-10-01 10:39:12 | WARNING | anastasia-4--Horn | homr failed on 6/50 crops: ...

The console gets INFO and up; the file also gets DEBUG (per-crop timings, full homr
error output, Audiveris warnings). The third column is the sample being processed
(set with `context`, it follows the thread, so parallel samples don't mix up).
"""
from __future__ import annotations

import contextvars
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

_sample: contextvars.ContextVar[str] = contextvars.ContextVar("omrbench_sample", default="-")
LOG = logging.getLogger("omrbench")


class _SampleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.sample = getattr(record, "sample", None) or _sample.get()
        # console: "[sample] " unless the message names it already ("song/Part.pdf: ...")
        s = record.sample
        named = s == "-" or record.getMessage().startswith(s.replace("--", "/", 1))
        record.tag = "" if named else f"[{s}] "
        return True


def setup(run_dir: Path | None = None, console: bool = True) -> Path | None:
    """Console handler (once) and, with run_dir, a file handler for run_dir/run.log."""
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = False
    if console and not any(getattr(h, "_omr_console", False) for h in LOG.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.INFO)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-7s %(tag)s%(message)s", "%H:%M:%S"))
        h.addFilter(_SampleFilter())
        h._omr_console = True
        LOG.addHandler(h)
    if run_dir is None:
        return None
    path = Path(run_dir) / "run.log"
    for h in [h for h in LOG.handlers if getattr(h, "_omr_file", None)]:
        if h._omr_file == path:
            return path
        LOG.removeHandler(h)
        h.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(sample)s | %(message)s",
                                      "%Y-%m-%d %H:%M:%S"))
    fh.addFilter(_SampleFilter())
    fh._omr_file = path
    LOG.addHandler(fh)
    return path


@contextmanager
def context(sample: str):
    """Tag every record logged inside (in this thread) with `sample`."""
    tok = _sample.set(sample)
    try:
        yield
    finally:
        _sample.reset(tok)


def current() -> str:
    return _sample.get()


def get(name: str = "") -> logging.Logger:
    return LOG.getChild(name) if name else LOG
