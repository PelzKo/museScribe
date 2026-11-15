"""D4: dynamics found by template correlation on the page image (scanned single-staff parts).

The dynamics of a show are printed in one bold italic font. A template per token is the mean image
of the `.omr` dynamics boxes Audiveris reads with grade >= 0.9 that look like the median of their
token (`scripts/derive_dyn_templates.py` -> data/<show>/dynamics_templates.npz). In the band below
the staff of every bar, normalised cross-correlation with each template: real glyphs score >= 0.9,
everything else <= 0.75 (evidence run 2026-11-15: 118 of 141 missing dynamics found, 10 of 412 right
ones missed). Of hits that overlap only the best counts (fz inside sfz). A hit adds its dynamic
where the bar has none of that token, and R42 never drops it; a reader's dynamic of a template
token the detector does not see in the bar goes (D8 / D10: homr's ppp for a printed mp).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

IL = 8                   # template scale: pixels per interline
THRESHOLD = 0.85
TOKENS = ("mf", "mp", "p", "f", "sfz", "fp", "fz")
FILE = "dynamics_templates.npz"


def cut(image: Image.Image, box: tuple, il: float) -> np.ndarray:
    """The page region `box` (x0, y0, x1, y1) scaled to IL px per interline, ink = 1."""
    im = image.crop(tuple(int(round(v)) for v in box))
    s = IL / il
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BILINEAR)
    return 1.0 - np.asarray(im, dtype=np.float32) / 255.0


def ncc(band: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Normalised cross-correlation of template t at every position inside band (valid part)."""
    h, w = t.shape
    H, W = band.shape
    if H < h or W < w:
        return np.zeros((0, 0), np.float32)
    z = t - t.mean()
    z /= np.sqrt((z ** 2).sum()) or 1.0
    fh, fw = H + h - 1, W + w - 1
    num = np.fft.irfft2(np.fft.rfft2(band, (fh, fw)) * np.fft.rfft2(z[::-1, ::-1], (fh, fw)), (fh, fw))
    num = num[h - 1:H, w - 1:W]
    c1 = np.pad(band, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    c2 = np.pad(band ** 2, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    win = lambda c: c[h:, w:] - c[:-h, w:] - c[h:, :-w] + c[:-h, :-w]  # noqa: E731
    s1, s2 = win(c1), win(c2)
    den = np.sqrt(np.maximum(s2 - s1 ** 2 / (h * w), 1e-6))
    return num / den


def build(samples: list[tuple[np.ndarray, str]], keep: float = 0.8, minimum: int = 4) -> dict[str, np.ndarray]:
    """Templates from (scaled glyph box, token) samples: per token the median-size mean image of the
    samples whose correlation with the token's median image is >= keep (drops misread boxes)."""
    by: dict[str, list[np.ndarray]] = {}
    for im, tok in samples:
        by.setdefault(tok, []).append(im)
    out = {}
    for tok, ims in by.items():
        if len(ims) < minimum:
            continue
        h = int(np.median([i.shape[0] for i in ims]))
        w = int(np.median([i.shape[1] for i in ims]))
        st = np.stack([np.asarray(Image.fromarray((i * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
                                  dtype=np.float32) / 255 for i in ims])
        med = np.median(st, axis=0)
        good = [s for s in st if ncc(s, med).max() >= keep]
        if len(good) >= minimum:
            out[tok] = np.mean(good, axis=0)
    return out


def load(data_dir: Path) -> dict[str, np.ndarray]:
    f = Path(data_dir) / FILE
    if not f.exists():
        return {}
    with np.load(f) as z:
        return {k: z[k] for k in z.files}


def detect(band: np.ndarray, templates: dict[str, np.ndarray]) -> list[tuple[float, str, float]]:
    """(score, token, x of the glyph centre in band pixels) of each token's best match >= THRESHOLD;
    of matches that overlap (fz inside sfz, p inside mp) only the best one."""
    cand = []
    for tok, t in templates.items():
        sc = ncc(band, t)
        if not sc.size:
            continue
        i = np.unravel_index(int(np.argmax(sc)), sc.shape)
        if sc[i] >= THRESHOLD:
            cand.append((float(sc[i]), tok, i[1], i[1] + t.shape[1]))
    out: list = []
    for s, tok, x0, x1 in sorted(cand, reverse=True):
        if all(x1 <= k0 or x0 >= k1 for _, _, k0, k1 in out):
            out.append((s, tok, x0, x1))
    return [(s, tok, (x0 + x1) / 2) for s, tok, x0, x1 in out]


def place(plans, pages, images: list[Path], templates: dict[str, np.ndarray], stats) -> int:
    """Add the detected dynamics to single-staff bars without that token (see the module doc).
    Returns the number added."""
    from . import assemble as A
    if not templates:
        return 0
    n = removed = 0
    imgs: dict[int, Image.Image] = {}
    for p in plans:
        if not p.n or not p.chosen or p.system.skip:
            continue
        for gi, g in p.chosen.items():
            staves = p.system.groups()[gi]
            if len(staves) != 1 or p.system.page - 1 >= len(images):
                continue
            st = staves[0]
            il = st.interline
            if p.system.page not in imgs:
                imgs.clear()
                imgs[p.system.page] = Image.open(images[p.system.page - 1]).convert("L")
            for i, bar in enumerate(g):
                if i >= len(p.xs):
                    break
                l, r = p.xs[i]
                if r - l < 2 * il:
                    continue
                x0 = l - 1.0 * il
                band = cut(imgs[p.system.page], (x0, st.bottom + 0.3 * il, r - 0.5 * il, st.bottom + 7 * il), il)
                hits = detect(band, templates)
                # D8 / D10: a dynamic of a template token the detector does not see in the bar is a misread
                seen = {tok for _, tok, _ in hits}
                for el in list(bar.items):
                    d = el.find("direction-type/dynamics") if el.tag == "direction" else None
                    if d is not None and len(d) == 1 and d[0].tag in templates and d[0].tag not in seen \
                            and len(el.findall("direction-type")) == 1:
                        bar.items.remove(el)
                        removed += 1
                for _, tok, bx in hits:
                    if any(e.tag == "direction" and e.find(f"direction-type/dynamics/{tok}") is not None
                           for e in bar.items):
                        continue
                    if A._put_dynamic(bar, staves, 1, "below", x0 + bx * il / IL, "DYNAMICS_" + tok.upper()):
                        for el in bar.items:       # the bar had none of tok: this is the new one
                            if el.tag == "direction" and el.find(f"direction-type/dynamics/{tok}") is not None:
                                el.set(A.AGREE_ATTR, "1")       # a detector hit is never "lone" (R42)
                        n += 1
    stats.dynamics += n - removed
    return n
