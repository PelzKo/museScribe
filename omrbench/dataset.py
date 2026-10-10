"""Discover benchmark samples.

Layout::

    data/samples/
      <sample-id>/
        input.pdf                 # 2-3 page score (any *.pdf; first one wins)
        gt.musicxml               # ground truth (gt.mxl / gt.xml / gt.mscz also accepted)
        gt-<part>.musicxml        #   ...or one file per part, stacked in meta `gt_parts` order
        meta.yaml                 # optional, see meta.example.yaml

Generated GT files (gt.mscz exported, part files merged, gt_drop_measures applied) go to
results/cache/samples/<sample-id>/, never into data/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import musicxml
from .musicxml import MUSICXML_SUFFIXES

SCORE_TYPES = ["choir", "piano", "piano_reduction", "part", "orchestral", "drums", "other"]


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


def cache_dir(cfg: dict) -> Path:
    return Path(cfg["results_dir"]) / "cache" / "samples"


def _find_gt(d: Path, mscore: str | None, cache: Path) -> Path | None:
    from . import truth

    for suf in MUSICXML_SUFFIXES:
        p = d / f"gt{suf}"
        if p.exists():
            return p
    mscz = d / "gt.mscz"
    return truth.convert(mscz, cache, mscore) if mscz.exists() else None


def _gt_part_files(d: Path, meta: dict) -> tuple[list[Path], list[str]]:
    """gt-<name>.* files, ordered by meta `gt_parts` (unlisted ones appended)."""
    files = {p.stem[3:]: p for p in sorted(d.iterdir())
             if p.name.startswith("gt-") and p.suffix.lower() in MUSICXML_SUFFIXES}
    order = [str(x) for x in (meta.get("gt_parts") or [])]
    missing = [n for n in order if n not in files]
    if missing:
        raise RuntimeError(f"gt_parts {missing} have no gt-<name> file (found {sorted(files)})")
    rest = [n for n in files if n not in order]
    warns = [f"gt-{n} not listed in gt_parts, appended" for n in rest] if order else []
    return [files[n] for n in order + rest], warns


def _prepare_gt(d: Path, meta: dict, mscore: str | None, cache: Path) -> tuple[Path | None, list[str]]:
    """Return the GT path to score against, merging part files / dropping measures if needed."""
    base = _find_gt(d, mscore, cache)
    parts, warns = _gt_part_files(d, meta)
    drop = meta.get("gt_drop_measures") or []
    if base and parts:
        warns.append(f"both {base.name} and gt-*.musicxml present; using {base.name}")
    if base is None and not parts:
        return None, warns
    if base is not None and not drop:
        return base, warns
    if base is not None:
        root = musicxml.load(base)
    else:
        roots = [musicxml.load(p) for p in parts]
        counts = {p.name: musicxml.measure_count(r) for p, r in zip(parts, roots)}
        if len(set(counts.values())) > 1:
            warns.append(f"GT part files differ in measure count: {counts}")
        root = musicxml.merge_parts(roots)
    if drop:
        warns += musicxml.drop_measures(root, drop)
    out = cache / d.name / "gt.prepared.musicxml"
    musicxml.write(root, out)
    return out, warns


def _matches(name: str, patterns: list[str], prefix: bool) -> bool:
    return any(name.startswith(p) if prefix else name == p for p in patterns)


def select_dirs(data_dir: Path, only: list[str] | None = None, exclude: list[str] | None = None,
                prefix: bool = False) -> tuple[list[Path], list[str]]:
    """Sample folders picked by `only` / `exclude` (exact names, or name prefixes if `prefix`).

    Folders starting with "_" are skipped (parked samples).
    """
    warnings = []
    dirs = sorted(p for p in Path(data_dir).iterdir() if p.is_dir() and not p.name.startswith("_"))
    for pat in (only or []) + (exclude or []):
        if not any(_matches(d.name, [pat], prefix) for d in dirs):
            warnings.append(f"'{pat}' matches no sample folder")
    dirs = [d for d in dirs if not (only and not _matches(d.name, only, prefix))
            and not (exclude and _matches(d.name, exclude, prefix))]
    return dirs, warnings


def load_meta(path: Path) -> dict:
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


def discover(data_dir: Path, only: list[str] | None = None,
             mscore: str | None = None, exclude: list[str] | None = None,
             prefix: bool = False, *, cache: Path) -> tuple[list[Sample], list[str]]:
    """Return (samples, warnings).

    `only` / `exclude` select sample ids by exact name, or by name prefix if `prefix`.
    cache: where generated GT files go (results/cache/samples).
    """
    samples = []
    dirs, warnings = select_dirs(data_dir, only, exclude, prefix)
    for d in dirs:
        pdfs = sorted(d.glob("*.pdf"))
        if not pdfs:
            warnings.append(f"{d.name}: no PDF, skipped")
            continue
        pdf = next((p for p in pdfs if p.stem == "input"), pdfs[0])
        meta = load_meta(d / "meta.yaml")
        try:
            gt, gt_warns = _prepare_gt(d, meta, mscore, Path(cache))
        except Exception as e:  # conversion failure is per-sample
            warnings.append(f"{d.name}: {e}")
            continue
        warnings += [f"{d.name}: {w}" for w in gt_warns]
        if gt is None:
            warnings.append(f"{d.name}: no gt.musicxml/gt.mxl/gt.mscz/gt-*.musicxml, skipped")
            continue
        if meta.get("type") and meta["type"] not in SCORE_TYPES:
            warnings.append(f"{d.name}: unknown type '{meta['type']}' (expected {SCORE_TYPES})")
        samples.append(Sample(d.name, d, pdf, gt, meta))
    return samples, warnings
