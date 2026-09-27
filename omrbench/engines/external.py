"""Outputs of tools that can't be scripted (Soundslice, Newzik, PlayScore, ...).

Drop `data/<sample>/external/<engine>.musicxml|.mxl`; the file stem becomes the
engine name. They are scored like everything else; runtime is not measured.
"""
from __future__ import annotations

from pathlib import Path

from .. import musicxml
from ..dataset import Sample
from ..rasterize import pdf_pages
from .base import Engine, EngineResult


class External(Engine):
    kind = "external"
    runs_locally = False

    def check(self) -> tuple[bool, str]:
        return True, "manual export"

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        src = sample.external.get(self.name)
        if src is None:
            res.error = "no external file for this sample"
            return
        res.pages = pdf_pages(sample.pdf)
        res.output = workdir / "output.musicxml"
        musicxml.write(musicxml.load(src), res.output)
        res.extras["source"] = src
