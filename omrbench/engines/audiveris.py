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

    def _cmd(self, sample: Sample, src: Path, out_dir: Path, sheet: int | None = None) -> list:
        # no -save: the .omr is written anyway, and -save makes Audiveris 5.11 reload
        # stored sheets before export, which can crash (RunTable.afterUnmarshal NPE)
        cmd = [self.exe, "-batch", "-transcribe", "-export", "-output", out_dir]
        if sheet is not None:
            cmd += ["-sheets", str(sheet)]
        for k, v in self.constants(sample).items():
            cmd += ["-constant", f"{k}={v}"]
        cmd += self.cfg.get("extra_args") or []
        return cmd + ["--", src]

    @staticmethod
    def _exports(out_dir: Path) -> list[Path]:
        return sorted(out_dir.rglob("*.mxl")) or sorted(out_dir.rglob("*.xml"))

    def _run(self, sample: Sample, workdir: Path, res: EngineResult) -> None:
        out_dir = workdir / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        res.pages = pdf_pages(sample.pdf)
        # copy so the book name is stable and Audiveris never writes next to the data
        src = workdir / "input.pdf"
        shutil.copyfile(sample.pdf, src)
        log = workdir / "engine.log"
        res.stats = run_monitored(self._cmd(sample, src, out_dir), log_path=log, env=self.env(),
                                  timeout_s=self.timeout_s)
        mxls = self._exports(out_dir)
        if not mxls and res.pages > 1 and not res.stats.timed_out:
            # book-level passes can still crash on reloading a sheet; transcribing each
            # sheet as its own book avoids them, the pages are concatenated below
            self._run_per_sheet(sample, src, out_dir, log, res)
            return
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

    def _run_per_sheet(self, sample: Sample, src: Path, out_dir: Path, log: Path,
                       res: EngineResult) -> None:
        book_exit = res.stats.exit_code
        shutil.rmtree(out_dir)
        # stats include the failed book run: that is what a user waits for
        total, sheet_exits = res.stats, []
        roots, failed = [], []
        for n in range(1, res.pages + 1):
            sheet_dir = out_dir / f"sheet{n:02d}"
            sheet_dir.mkdir(parents=True)
            with log.open("a") as f:
                f.write(f"\n### book run failed (exit {book_exit}); retrying sheet {n} alone\n")
            st = run_monitored(self._cmd(sample, src, sheet_dir, sheet=n), log_path=log,
                               env=self.env(), timeout_s=self.timeout_s)
            total.add(st)
            sheet_exits.append(st.exit_code)
            mxls = self._exports(sheet_dir)
            if mxls:
                roots += [musicxml.load(p) for p in mxls]
            else:
                failed.append(n)
        total.exit_code = max(sheet_exits, key=lambda c: c not in (0, None))
        res.stats = total
        if not roots:
            res.error = f"no export (book exit {book_exit}, per-sheet retry failed); see engine.log"
            return
        # audiveris_flags reads every sheetNN/*.omr in order
        res.extras["omr"] = out_dir
        res.output = src.parent / "output.musicxml"
        musicxml.write(musicxml.merge_pages(roots), res.output)
        msg = f"book run failed (exit {book_exit}); transcribed per sheet and concatenated"
        if failed:
            msg += f"; sheets {failed} produced no export"
        res.extras["warning"] = msg
