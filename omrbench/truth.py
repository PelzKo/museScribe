"""Ground-truth scores: MuseScore files converted once and cached, split into parts by name.

  results/cache/truth/<stem>-<hash>.musicxml   the MuseScore export of data/<show>/truth/<stem>.mscz

The hash is of the .mscz content, so an edited truth file is converted again and the
data folder is never written. .musicxml/.mxl truth files are used as they are.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from lxml import etree

from .musicxml import MUSICXML_SUFFIXES


def convert(src: Path, cache_dir: Path, musescore: str | None) -> Path:
    from .transcribe import find_musescore, to_mscz

    src = Path(src)
    if src.suffix.lower() in MUSICXML_SUFFIXES:
        return src
    digest = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
    out = Path(cache_dir) / "truth" / f"{src.stem}-{digest}.musicxml"
    if out.exists():
        return out
    exe = find_musescore(musescore)
    if not exe:
        raise RuntimeError(f"{src.name}: MuseScore CLI not found (set musescore_cli in bench.yaml)")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.musicxml")
    to_mscz(src, tmp, exe)   # the MuseScore CLI converts by the output's extension
    tmp.replace(out)
    return out


def load(srcs: list[Path], cache_dir: Path, musescore: str | None) -> etree._Element:
    """The song's truth as one score. Several files (one hand-corrected part each, "#13 - Bass.mscz",
    "#13 - Cello.mscz") are merged in order; there a one-part file's part is named after the text
    behind the last " - " of its file name ("Bass"), whatever the part is called inside."""
    from .musicxml import load as load_xml, merge_parts

    roots = [load_xml(convert(s, cache_dir, musescore)) for s in srcs]
    if len(roots) == 1:
        return roots[0]
    for src, root in zip(srcs, roots):
        if len(sps := root.findall("part-list/score-part")) == 1:
            name = sps[0].find("part-name")
            if name is None:
                name = etree.Element("part-name")
                sps[0].insert(0, name)
            name.text = Path(src).stem.rsplit(" - ", 1)[-1]
    return merge_parts(roots)


def parts(root: etree._Element) -> list[tuple[str, etree._Element]]:
    """(part name, <part>) in score order."""
    names = {sp.get("id"): (sp.findtext("part-name") or "").strip()
             for sp in root.iterfind("part-list/score-part")}
    return [(names.get(p.get("id"), ""), p) for p in root.findall("part")]


def extract(root: etree._Element, keep: list[etree._Element]) -> etree._Element:
    """A copy of the score with only the parts in `keep` (for musicdiff / TEDn per part)."""
    ids = {p.get("id") for p in keep}
    out = copy.deepcopy(root)
    for sp in out.findall("part-list/score-part"):
        if sp.get("id") not in ids:
            sp.getparent().remove(sp)
    for grp in out.findall("part-list/part-group"):
        grp.getparent().remove(grp)
    for p in out.findall("part"):
        if p.get("id") not in ids:
            out.remove(p)
    return out
