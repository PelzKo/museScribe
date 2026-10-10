"""Clarity-OMR: whole PDF in, one MusicXML out (YOLO staff detection + DaViT token model). Container only."""
from __future__ import annotations

import shutil
from pathlib import Path

from .. import containers
from ..dataset import Sample
from ..rasterize import pdf_pages
from .base import Engine, EngineResult


class Clarity(Engine):
    kind = "clarity"
    container_image = "clarity"
    container_exe = "clarity"

    def check(self) -> tuple[bool, str]:
        if not self.container:
            return False, "clarity runs only in its container (omrbench images build clarity)"
        return containers.check_image(self.container)

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        res.pages = pdf_pages(sample.pdf)
        src = workdir / "input.pdf"          # Clarity renders next to its work dir, never next to the data
        shutil.copyfile(sample.pdf, src)
        out = workdir / "output.musicxml"
        out.unlink(missing_ok=True)
        device = self.bench.get("device", "cpu")
        cmd = ["clarity", src, "-o", out, "--work-dir", workdir / "work", "--device", device,
               "--pdf-dpi", str(int(self.cfg.get("dpi", self.bench.get("dpi", 300))))]
        if self.cfg.get("beam_width"):
            cmd += ["--beam-width", str(self.cfg["beam_width"])]
        cmd += self.cfg.get("extra_args") or []
        log = workdir / "engine.log"
        log.unlink(missing_ok=True)
        res.stats = self.exec_cmd(cmd, workdir, log, env=self.env())
        if out.exists() and out.stat().st_size:
            res.output = out
        else:
            res.error = f"no MusicXML (exit {res.stats.exit_code}); see engine.log"
