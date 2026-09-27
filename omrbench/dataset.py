"""Discover benchmark samples.

Layout::

    data/
      <sample-id>/
        input.pdf                 # 2-3 page score (any *.pdf; first one wins)
        gt.musicxml               # ground truth (gt.mxl / gt.xml / gt.mscz also accepted)
        meta.yaml                 # optional, see meta.example.yaml
        external/                 # optional: outputs of tools the harness can't run
          soundslice.musicxml     #   engine name = file stem
          playscore.mxl
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .musicxml import MUSICXML_SUFFIXES

SCORE_TYPES = ["choir", "piano", "part", "orchestral", "drums", "other"]


@dataclass
class Sample:
    id: str
    dir: Path
    pdf: Path
    gt: Path
    meta: dict = field(default_factory=dict)

    @property
    def score_type(self) -> str:
        return str(self.meta.get("type", "other"))

    @property
    def external(self) -> dict[str, Path]:
        d = self.dir / "external"
        if not d.is_dir():
            return {}
        return {p.stem: p for p in sorted(d.iterdir()) if p.suffix.lower() in MUSICXML_SUFFIXES}

    @property
    def correction_minutes(self) -> dict[str, float]:
        return {str(k): float(v) for k, v in (self.meta.get("correction_minutes") or {}).items()}


def _find_gt(d: Path, mscore: str | None) -> Path | None:
    for suf in MUSICXML_SUFFIXES:
        p = d / f"gt{suf}"
        if p.exists():
            return p
    mscz = d / "gt.mscz"
    if mscz.exists():
        out = d / "gt.converted.musicxml"
        if out.exists() and out.stat().st_mtime >= mscz.stat().st_mtime:
            return out
        exe = mscore or shutil.which("mscore") or shutil.which("musescore") or shutil.which("mscore4")
        if not exe:
            raise RuntimeError(f"{mscz}: MuseScore CLI not found; export gt.musicxml manually "
                               "or set musescore_cli in bench.yaml")
        subprocess.run([exe, "-o", str(out), str(mscz)], check=True, capture_output=True)
        return out
    return None


def discover(data_dir: Path, only: list[str] | None = None,
             mscore: str | None = None) -> tuple[list[Sample], list[str]]:
    """Return (samples, warnings)."""
    samples, warnings = [], []
    for d in sorted(p for p in Path(data_dir).iterdir() if p.is_dir()):
        if only and d.name not in only:
            continue
        pdfs = sorted(d.glob("*.pdf"))
        if not pdfs:
            warnings.append(f"{d.name}: no PDF, skipped")
            continue
        pdf = next((p for p in pdfs if p.stem == "input"), pdfs[0])
        try:
            gt = _find_gt(d, mscore)
        except Exception as e:  # conversion failure is per-sample
            warnings.append(f"{d.name}: {e}")
            continue
        if gt is None:
            warnings.append(f"{d.name}: no gt.musicxml/gt.mxl/gt.mscz, skipped")
            continue
        meta = {}
        mp = d / "meta.yaml"
        if mp.exists():
            meta = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
        if meta.get("type") and meta["type"] not in SCORE_TYPES:
            warnings.append(f"{d.name}: unknown type '{meta['type']}' (expected {SCORE_TYPES})")
        samples.append(Sample(d.name, d, pdf, gt, meta))
    return samples, warnings
