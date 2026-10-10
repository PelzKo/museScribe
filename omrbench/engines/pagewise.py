"""Engines that take one page image per call (homr, oemer).

The PDF is rasterised once per sample (cached, time reported as prep_s), each page
is processed by a separate CLI invocation and the page outputs are concatenated.
Stats are summed over pages (wall/CPU) or maxed (memory).
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .. import containers
from .. import log as logmod
from .. import musicxml
from ..dataset import Sample
from ..monitor import RunStats
from ..rasterize import rasterize
from .base import Engine, EngineResult


LOG = logmod.get("pagewise")


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

    def use_pool(self) -> bool:
        return False

    def find_output(self, image: Path, out_dir: Path) -> Path | None:
        raise NotImplementedError

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
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
        locals_ = []
        for img in pages:
            local = pdir / img.name
            shutil.copyfile(img, local)
            locals_.append(local)
        log = workdir / "engine.log"
        if self.use_pool():
            pool = self.pool()
            t1 = time.perf_counter()
            results = [f.result() for f in [pool.submit(p, self.timeout_s) for p in locals_]]
            wall = time.perf_counter() - t1
            rss = max((r.rss_mb for r in results), default=0.0)
            with log.open("a", encoding="utf-8") as f:
                for r in results:
                    f.write(f"$ {self.kind} {r.image}\n{r.log}\n[ok={r.ok} wall={r.wall_s:.1f}s]\n")
                    if not r.ok:
                        LOG.warning(f"{self.kind} failed on {r.image.name}: {r.error}")
            total.add(RunStats(wall_s=wall, wall_clock_s=wall, cpu_user_s=sum(r.cpu_s for r in results),
                               peak_rss_mb=rss * min(len(results), len(pool.workers)),
                               peak_single_rss_mb=rss, exit_code=0,
                               timed_out=any(r.timed_out for r in results)))
            timed_out = {r.image.name for r in results if r.timed_out}
        else:
            timed_out = set()
            for local in locals_:
                st = self.exec_cmd(self.page_cmd(local, pdir), workdir, log, env=self.env(), cwd=pdir)
                total.add(st)
                if st.timed_out:
                    timed_out.add(local.name)
        for img, local in zip(pages, locals_):
            out = self.find_output(local, pdir)
            if out is None or local.name in timed_out:
                failed.append(img.name)
                continue
            try:
                roots.append(musicxml.load(out))
            except Exception as e:
                failed.append(f"{img.name} ({e})")
        res.stats = total
        if failed:
            res.extras["failed_pages"] = ", ".join(failed)
            LOG.warning(f"{self.kind}: {len(failed)}/{len(pages)} pages failed: {', '.join(failed)}")
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
    container_image = "homr"
    container_exe = "homr"

    def check(self) -> tuple[bool, str]:
        if self.container:
            return containers.check_image(self.container)
        return super().check()

    def page_cmd(self, image, out_dir):
        return [self.exe, *(self.cfg.get("extra_args") or []), image]

    def use_pool(self) -> bool:
        """Persistent workers (homr_pool.py); CLI options need the one-process-per-image path."""
        return bool(self.cfg.get("pool", True)) and not self.cfg.get("extra_args")

    def pool(self):
        from .homr_pool import WORKER, get_pool
        env = self.env()
        if self.container:
            # the crops live under results/, so the image sees results/ at the same path
            results = Path(self.bench["results_dir"])
            launch = containers.pool_cmd(containers.IMAGES[self.container][0], mounts={results: str(results)},
                                         gpu=self.bench.get("device", "cpu") == "cuda",
                                         env=self.container_env(env))
        else:
            launch = [str(self.venv / "bin" / "python"), str(WORKER)]
        return get_pool(launch, self.cfg.get("workers", "auto"), int(self.cfg.get("threads", 2)),
                        env, int(self.cfg.get("nice", 0)))

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
