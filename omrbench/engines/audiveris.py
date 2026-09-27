"""Audiveris batch CLI.

Variants are configured in bench.yaml. With `use_metadata: true` the sample's
meta.yaml drives processing switches (drums, OCR languages, ...), as proposed in
section 7 of the research notes.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import musicxml
from ..dataset import Sample
from ..monitor import run_monitored
from ..rasterize import pdf_pages
from .base import Engine, EngineResult

SWITCH = "org.audiveris.omr.sheet.ProcessingSwitches."
LANG = "org.audiveris.omr.text.Language.defaultSpecification"

# meta.yaml boolean key -> Audiveris processing switch
META_SWITCHES = {
    "drums": "drumNotation",
    "one_line_percussion": "oneLineStaves",
    "small_heads": "smallHeads",
    "cross_heads": "crossHeads",
    "lyrics": "lyrics",
    "lyrics_above_staff": "lyricsAboveStaff",
    "articulations": "articulations",
    "implicit_tuplets": "implicitTuplets",
    "chord_names": "chordNames",
    "poor_input": "poorInputMode",
}


class Audiveris(Engine):
    kind = "audiveris"

    @property
    def exe(self) -> Path:
        return Path(self.cfg.get("exe") or self.home / "tools" / "audiveris")

    def env(self) -> dict:
        env = super().env()
        tess = self.home / "tools" / "tessdata"
        if tess.is_dir():
            env.setdefault("TESSDATA_PREFIX", str(tess))
        return env

    def check(self) -> tuple[bool, str]:
        if not self.exe.exists():
            return False, f"not found: {self.exe} (run setup.sh)"
        try:
            out = subprocess.run([str(self.exe), "-batch", "-version"], capture_output=True,
                                 text=True, timeout=120, env={**__import__("os").environ, **self.env()})
            info = {}
            for line in (out.stdout + out.stderr).splitlines():
                if line.startswith("- ") and ":" in line:
                    k, v = line[2:].split(":", 1)
                    info[k.strip()] = v.strip()
            ver = info.get("Version", "?")
            ocr = info.get("OCR Engine", "")
            return True, f"{ver} ({ocr})" if ocr else ver
        except Exception as e:
            return False, str(e)

    def constants(self, sample: Sample) -> dict[str, str]:
        consts: dict[str, str] = {}
        for k, v in (self.cfg.get("constants") or {}).items():
            consts[k] = str(v).lower() if isinstance(v, bool) else str(v)
        if self.cfg.get("use_metadata"):
            m = sample.meta
            if sample.score_type == "drums":
                consts[SWITCH + "drumNotation"] = "true"
            for key, sw in META_SWITCHES.items():
                if key in m:
                    consts[SWITCH + sw] = str(bool(m[key])).lower()
            langs = m.get("languages")
            if langs:
                consts[LANG] = "+".join(langs) if isinstance(langs, list) else str(langs)
            for k, v in (m.get("audiveris_constants") or {}).items():
                consts[k] = str(v).lower() if isinstance(v, bool) else str(v)
        return consts

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        out_dir = workdir / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        res.pages = pdf_pages(sample.pdf)
        # copy so the book name is stable and Audiveris never writes next to the data
        src = workdir / "input.pdf"
        shutil.copyfile(sample.pdf, src)
        cmd = [self.exe, "-batch", "-transcribe", "-export", "-save", "-output", out_dir]
        for k, v in self.constants(sample).items():
            cmd += ["-constant", f"{k}={v}"]
        cmd += self.cfg.get("extra_args") or []
        cmd += ["--", src]
        res.stats = run_monitored(cmd, log_path=workdir / "engine.log", env=self.env(),
                                  timeout_s=self.timeout_s)
        mxls = sorted(out_dir.rglob("*.mxl")) or sorted(out_dir.rglob("*.xml"))
        if not mxls:
            res.error = f"no export (exit {res.stats.exit_code}); see engine.log"
            return
        omr = next(iter(sorted(out_dir.rglob("*.omr"))), None)
        if omr:
            res.extras["omr"] = omr
        # several movements -> several files (book.mvt1.mxl, ...); concatenate
        roots = [musicxml.load(p) for p in mxls]
        merged = roots[0] if len(roots) == 1 else musicxml.merge_pages(roots)
        res.output = workdir / "output.musicxml"
        musicxml.write(merged, res.output)
        if res.stats.exit_code not in (0, None):
            res.extras["warning"] = f"exit code {res.stats.exit_code} but export present"
