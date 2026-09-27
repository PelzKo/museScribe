"""Engines that take one page image per call (homr, oemer).

The PDF is rasterised once per sample (cached, time reported as prep_s), each page
is processed by a separate CLI invocation and the page outputs are concatenated.
Stats are summed over pages (wall/CPU) or maxed (memory).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import musicxml
from ..dataset import Sample
from ..monitor import RunStats, run_monitored
from ..rasterize import rasterize
from .base import Engine, EngineResult


class PagewiseEngine(Engine):
    venv_name = ""
    cli_name = ""
    package = ""

    @property
    def venv(self) -> Path:
        return Path(self.cfg.get("venv") or self.home / "venvs" / self.venv_name)

    @property
    def exe(self) -> Path:
        return self.venv / "bin" / self.cli_name

    def check(self) -> tuple[bool, str]:
        if not self.exe.exists():
            return False, f"not found: {self.exe} (run setup.sh)"
        probe = (f"import importlib.metadata as m, onnxruntime as o, {self.package}; "
                 f"print(m.version('{self.package}'), 'onnxruntime', o.__version__, o.get_device())")
        out = subprocess.run([str(self.venv / "bin" / "python"), "-c", probe],
                             capture_output=True, text=True)
        return out.returncode == 0, (out.stdout.strip() or out.stderr.strip()[-200:])

    def page_cmd(self, image: Path, out_dir: Path) -> list:
        raise NotImplementedError

    def find_output(self, image: Path, out_dir: Path) -> Path | None:
        raise NotImplementedError

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        import time
        dpi = int(self.cfg.get("dpi", self.bench.get("dpi", 300)))
        t0 = time.perf_counter()
        cache = workdir.parent.parent / "_pages" / sample.id / f"{dpi}dpi"
        pages = rasterize(sample.pdf, cache, dpi=dpi)
        res.prep_s = time.perf_counter() - t0
        res.pages = len(pages)

        pdir = workdir / "pages"
        if pdir.exists():
            shutil.rmtree(pdir)
        pdir.mkdir(parents=True)
        total = RunStats()
        roots, failed = [], []
        for img in pages:
            local = pdir / img.name
            shutil.copyfile(img, local)
            st = run_monitored(self.page_cmd(local, pdir), log_path=workdir / "engine.log",
                               cwd=pdir, env=self.env(), timeout_s=self.timeout_s)
            total.add(st)
            out = self.find_output(local, pdir)
            if out is None or st.timed_out:
                failed.append(img.name)
                continue
            try:
                roots.append(musicxml.load(out))
            except Exception as e:
                failed.append(f"{img.name} ({e})")
        res.stats = total
        if failed:
            res.extras["failed_pages"] = ", ".join(failed)
        if not roots:
            res.error = f"all pages failed ({', '.join(failed)}); see engine.log"
            return
        res.output = workdir / "output.musicxml"
        musicxml.write(musicxml.merge_pages(roots), res.output)


class Homr(PagewiseEngine):
    kind = "homr"
    venv_name = "homr"
    cli_name = "homr"
    package = "homr"

    def page_cmd(self, image, out_dir):
        return [self.exe, *(self.cfg.get("extra_args") or []), image]

    def find_output(self, image, out_dir):
        p = image.with_suffix(".musicxml")
        return p if p.exists() else None


class Oemer(PagewiseEngine):
    kind = "oemer"
    venv_name = "oemer"
    cli_name = "oemer"
    package = "oemer"

    def page_cmd(self, image, out_dir):
        cmd = [self.exe, "-o", out_dir]
        if self.cfg.get("without_deskew"):
            cmd.append("--without-deskew")
        return cmd + [*(self.cfg.get("extra_args") or []), image]

    def find_output(self, image, out_dir):
        p = out_dir / f"{image.stem}.musicxml"
        return p if p.exists() else None
