"""Second OCR pass for bar numbers, ranges, multi-rest counts and cut marks.

Audiveris' text recognition misses whole pages of bar numbers now and then ("230-237"
under a rest, "[to] 194"), and without them the bars can't be lined up. Here Tesseract
reads strips above and below every staff (the rest of the page masked white, one call
per page); tokens that look like bar evidence are added as text atoms where Audiveris
has no text, so text.classify treats them like its own.

Vector pages (pdfkind) have the exact words in the PDF text layer: those are read from the
same strips instead of running Tesseract.

The Tesseract binary is the one bundled in Audiveris' jars (extracted once into
$OMRBENCH_HOME/tools/tesseract); a `tesseract` on PATH is used if there is one. Without a
native Audiveris, the jars and tessdata are copied out of the Audiveris image first.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .. import log as logmod
from .layout import Page, Text

LOG = logmod.get("ocr")

STRIP = 4.5             # interlines above / below a staff that are read
MIN_CONF = 30.0         # Tesseract word confidence (bar numbers score 90+, noise mostly < 30)
# what bar evidence looks like: 97, 15-17, 131A, [to], [to]97
KEEP = re.compile(r"^(\d{1,4}[A-E]?([-–—]\d{1,4}[A-E]?)?|\[?to\]?(\d{1,4}[A-E]?\]?)?)$", re.I)
_EDGE = re.compile(r"^[^\w\[]+|[^\w\]]+$")      # accents / slurs stuck to a number: "203>"


IMAGE_JARS = "/opt/audiveris-root/opt/audiveris/lib/app"


def _from_image(home: Path) -> None:
    """Copy the Tesseract/Leptonica jars and tessdata of the Audiveris image to
    tools/audiveris-image/ and tools/tessdata/ (Audiveris runs in its container)."""
    from .. import containers
    tag = containers.IMAGES["audiveris"][0]
    dest = home / "tools" / "audiveris-image" / "opt" / "audiveris" / "lib" / "app"
    try:
        names = subprocess.run(["docker", "run", "--rm", tag, "ls", IMAGE_JARS], capture_output=True,
                               text=True, timeout=120, check=True).stdout.split()
        cid = subprocess.run(["docker", "create", tag, "true"], capture_output=True, text=True,
                             timeout=120, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        LOG.debug(f"no tesseract from {tag}: {e}")
        return
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for n in names:
            if n.startswith(("tesseract-", "leptonica-")) and n.endswith("-linux-x86_64.jar"):
                subprocess.run(["docker", "cp", f"{cid}:{IMAGE_JARS}/{n}", str(dest / n)], check=True,
                               capture_output=True, timeout=300)
        if not (home / "tools" / "tessdata").is_dir():
            subprocess.run(["docker", "cp", f"{cid}:/opt/tessdata", str(home / "tools" / "tessdata")],
                           check=True, capture_output=True, timeout=300)
        LOG.info(f"tesseract jars and tessdata copied from {tag} into {home / 'tools'}")
    except (OSError, subprocess.SubprocessError) as e:
        LOG.warning(f"copying tesseract from {tag} failed: {e}")
    finally:
        subprocess.run(["docker", "rm", cid], capture_output=True, timeout=120)


def find_tesseract(home: Path) -> tuple[str, dict] | None:
    """(executable, environment) or None if neither PATH nor Audiveris has one."""
    if not shutil.which("tesseract") and not (home / "tools" / "tesseract" / "tesseract").exists() \
            and not list((home / "tools").glob("audiveris*/opt/audiveris/lib/app/tesseract-*-linux-x86_64.jar")):
        _from_image(home)
    env = dict(os.environ)
    tessdata = home / "tools" / "tessdata"
    if tessdata.is_dir():
        env.setdefault("TESSDATA_PREFIX", str(tessdata))
    exe = shutil.which("tesseract")
    if exe:
        return exe, env
    tdir = home / "tools" / "tesseract"
    exe = tdir / "tesseract"
    if not exe.exists():
        jars = sorted((home / "tools").glob("audiveris*/opt/audiveris/lib/app/*-linux-x86_64.jar"))
        jars = [j for j in jars if j.name.startswith(("tesseract-", "leptonica-"))]
        if len(jars) < 2:
            return None
        tdir.mkdir(parents=True, exist_ok=True)
        for jar in jars:
            with zipfile.ZipFile(jar) as z:
                for name in z.namelist():
                    base = name.rsplit("/", 1)[-1]
                    if base == "tesseract" or ".so" in base:
                        (tdir / base).write_bytes(z.read(name))
        if not exe.exists():
            return None
        exe.chmod(0o755)
        LOG.debug(f"tesseract extracted from the Audiveris jars into {tdir}")
    env["LD_LIBRARY_PATH"] = str(tdir) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    return str(exe), env


def _strips(page: Page) -> list[tuple[float, float, float, float]]:
    """(x0, y0, x1, y1) in page coordinates: the bands above and below every staff that are read."""
    out = []
    for sy in page.systems:
        if sy.skip:
            continue
        for st in sy.all_staves:
            il = st.interline
            for top, bot in ((st.top - STRIP * il, st.top - 0.1 * il),
                             (st.bottom + 0.1 * il, st.bottom + STRIP * il)):
                out.append((st.left - 4 * il, top, st.right + 2 * il, bot))
    return out


def _mask(page: Page, img_path: Path, out: Path) -> None:
    """The page with everything but the strips around the staves painted white."""
    with Image.open(img_path) as im0:
        im = im0.convert("L")
    sx = im.width / page.width if page.width else 1.0
    canvas = Image.new("L", im.size, 255)
    for x0, y0, x1, y1 in _strips(page):
        box = (max(0, int(x0 * sx)), max(0, int(y0 * sx)),
               min(im.width, int(x1 * sx)), min(im.height, int(y1 * sx)))
        if box[2] > box[0] and box[3] > box[1]:
            canvas.paste(im.crop(box), box[:2])
    canvas.save(out)


def _finish(page: Page, img_path: Path, raw: list[dict]) -> list[dict]:
    """Words in image pixels -> page coordinates, with the multi-rest flag."""
    with Image.open(img_path) as im0:
        im = im0.convert("L")
    sx = im.width / page.width if page.width else 1.0
    staves = sorted((st for sy in page.systems for st in sy.all_staves), key=lambda s: s.top)
    px = im.load()

    def multirest_below(x: float, w: float, bottom: float) -> bool:
        """A multi-measure rest bar (thick, on the middle line) under the word."""
        st = next((s for s in staves if s.top >= bottom - 0.5 * s.interline), None)
        if st is None or st.top - bottom > 1.5 * st.interline:
            return False
        il = st.interline
        mid = (st.top + st.bottom) / 2
        cx = x + w / 2
        y0, y1 = int((mid - 0.7 * il) * sx), int((mid + 0.7 * il) * sx)
        x0, x1 = int((cx - 1.5 * il) * sx), int((cx + 1.5 * il) * sx)
        if x0 < 0 or y0 < 0 or x1 >= im.width or y1 >= im.height:
            return False
        need = 0.6 * il * sx
        cols = sum(1 for xx in range(x0, x1) if sum(px[xx, yy] < 128 for yy in range(y0, y1)) >= need)
        return cols >= 0.8 * (x1 - x0)

    words = []
    for r in raw:
        if r["conf"] < MIN_CONF:
            continue
        x, y, w, h = r["x"] / sx, r["y"] / sx, r["w"] / sx, r["h"] / sx
        words.append({"text": r["text"], "conf": r["conf"], "x": x, "y": y, "w": w, "h": h,
                      "multirest": multirest_below(x, w, y + h)})
    return words


def _tesseract(img: Path, tess: tuple[str, dict]) -> list[dict]:
    """Tesseract's words in image pixels."""
    exe, env = tess
    r = subprocess.run([exe, str(img), "stdout", "--psm", "11", "-l", "eng",
                        "-c", "tessedit_create_tsv=1"],
                       capture_output=True, text=True, env=env, timeout=300)
    words = []
    for row in csv.DictReader(io.StringIO(r.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        try:
            if row.get("level") != "5":
                continue
            words.append({"text": row["text"], "conf": float(row["conf"]), "x": int(row["left"]),
                          "y": int(row["top"]), "w": int(row["width"]), "h": int(row["height"])})
        except (KeyError, TypeError, ValueError):
            continue
    return words


def _read_page(page: Page, img_path: Path, tess: tuple[str, dict], tmp: Path) -> list[dict]:
    """Words read in the strips around the staves, in page coordinates."""
    _mask(page, img_path, tmp)
    raw = _tesseract(tmp, tess)
    tmp.unlink(missing_ok=True)
    return _finish(page, img_path, raw)


def _text_layer(page: Page, pdf_page) -> list[dict]:
    """Words of a vector PDF page's text layer that lie in the strips, in page coordinates.

    shortcut: digits drawn as music-font glyphs (multi-rest counts, SMuFL time-signature digits)
    are not in the text layer and multirest is always False; map SMuFL digits if vector scores
    lose multi-rest counts.
    """
    sx = page.width / pdf_page.rect.width if pdf_page.rect.width else 1.0
    strips = _strips(page)
    words = []

    def add(chars: list[dict], size: float) -> None:
        if not chars:
            return
        # glyph box, not the line box: digits are ~0.7 font size tall above the baseline
        h = 0.7 * size * sx
        x, y = chars[0]["bbox"][0] * sx, chars[0]["origin"][1] * sx - h
        w = chars[-1]["bbox"][2] * sx - x
        if any(a <= x + w / 2 <= c and b <= y + h / 2 <= d for a, b, c, d in strips):
            words.append({"text": "".join(ch["c"] for ch in chars), "conf": 100.0,
                          "x": x, "y": y, "w": w, "h": h, "multirest": False})

    for block in pdf_page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                cur: list[dict] = []
                for ch in span["chars"]:
                    if ch["c"].isspace():
                        add(cur, span["size"])
                        cur = []
                    else:
                        cur.append(ch)
                add(cur, span["size"])
    return words


def text_layer_pages(pages: list[Page], pdf: Path) -> dict[int, list[dict]]:
    """0-based page index -> text-layer words, for the vector pages of `pdf` (pages[i] is PDF page i)."""
    import pymupdf as fitz

    from ..pdfkind import classify_page
    from ..rasterize import FITZ_LOCK
    with FITZ_LOCK, fitz.open(pdf) as doc:
        return {i: _text_layer(pages[i], p) for i, p in enumerate(doc)
                # no fonts = no text layer (scans): skips the costly classification
                if i < len(pages) and p.get_fonts() and classify_page(p, i + 1).kind == "vector"}


# OCR engines other than Tesseract (component benchmark, PLAN_full.md P6): image key, `ocr-words` engine
ENGINES = {"easyocr": "ocr", "doctr": "ocr", "paddle": "paddle"}
CPU_ONLY = {"paddle"}    # the paddle image has the CPU build of PaddlePaddle


def _engine_pages(pages: list[Page], images: list[Path], todo: list[int], cache: Path,
                  engine: str, device: str) -> None:
    """Read the masked pages `todo` with a container OCR engine (one call), cache as JSON."""
    from .. import containers
    cache = cache.resolve()     # mounted at its own path in the container
    if engine in CPU_ONLY:
        device = "cpu"
    masks = {i: cache / f"page{i + 1:02d}-mask.png" for i in todo}
    for i, m in masks.items():
        _mask(pages[i], images[i], m)
    out = cache / "words.json"
    st = containers.run_in_container(
        containers.IMAGES[ENGINES[engine]][0],
        ["ocr-words", "--engine", engine, "--out", str(out), "--device", device, *map(str, masks.values())],
        workdir=cache, log_path=cache / "ocr.log", gpu=device == "cuda",
        env={} if device == "cuda" else {"CUDA_VISIBLE_DEVICES": ""})
    raw = json.loads(out.read_text()) if out.exists() else {}
    if not raw:     # not cached: the next run retries
        LOG.warning(f"{engine} read nothing (exit {st.exit_code}); see {cache / 'ocr.log'}")
        for m in masks.values():
            m.unlink(missing_ok=True)
        return
    stats = json.loads((cache / "stats.json").read_text()) if (cache / "stats.json").exists() else {}
    for i, m in masks.items():
        (cache / f"page{i + 1:02d}.json").write_text(json.dumps(_finish(pages[i], images[i], raw.get(m.name, []))))
        m.unlink(missing_ok=True)
    # runtime / memory of the OCR call, for the component report
    (cache / "run.json").write_text(json.dumps({"engine": engine, "pages": len(todo), **stats}))
    out.unlink(missing_ok=True)


def read_pages(pages: list[Page], images: list[Path], tess: tuple[str, dict] | None, cache: Path,
               jobs: int = 4, pdf: Path | None = None, engine: str = "tesseract",
               device: str = "cpu") -> list[list[dict]]:
    """Words per page; cached as JSON in `cache` (reassemble reuses them).

    With `pdf`, vector pages use the PDF text layer instead of the OCR (tess may then be None).
    engine: tesseract, or a container engine of ENGINES.
    """
    cache.mkdir(parents=True, exist_ok=True)
    vector = text_layer_pages(pages, pdf) if pdf is not None else {}
    if engine != "tesseract":
        todo = [i for i in range(min(len(pages), len(images)))
                if i not in vector and not (cache / f"page{i + 1:02d}.json").exists()]
        if todo:
            _engine_pages(pages, images, todo, cache, engine, device)

    def one(i: int) -> list[dict]:
        if i in vector:
            return vector[i]
        f = cache / f"page{i + 1:02d}.json"
        if f.exists():
            return json.loads(f.read_text())
        if tess is None or i >= len(images) or engine != "tesseract":
            return []
        words = _read_page(pages[i], images[i], tess, cache / f"page{i + 1:02d}-mask.png")
        f.write_text(json.dumps(words))
        return words

    with ThreadPoolExecutor(max(1, jobs)) as ex:
        return list(ex.map(one, range(len(pages))))


def _overlaps(a: Text, x: float, y: float, w: float, h: float) -> bool:
    return a.x < x + w and x < a.x + a.w and a.y < y + h and y < a.y + a.h


def supplement(page: Page, words: list[dict]) -> int:
    """Add the bar-evidence words that no Audiveris text covers. Returns the number added."""
    added = 0
    old = list(page.texts)
    for wd in words:
        t = _EDGE.sub("", wd["text"].strip())
        if not t or not KEEP.match(t) or not re.search(r"\d|to", t, re.I):
            continue
        x, y, w, h = wd["x"], wd["y"], wd["w"], wd["h"]
        st = min((s for sy in page.systems for s in sy.all_staves),
                 key=lambda s: abs((s.top + s.bottom) / 2 - (y + h / 2)), default=None)
        il = st.interline if st else 20.0
        if not 0.6 * il <= h <= 3.5 * il:
            continue        # specks, or a note stem read as "1"
        if len(t) == 1 and wd["conf"] < 80:
            continue        # lone digits are mostly note heads, fingerings, tuplet marks
        if h > 1.8 * il and not wd.get("multirest"):
            continue        # count-sized but no multi-rest under it: notes read as digits
        if any(_overlaps(a, x, y, w, h) for a in old):
            continue
        kind = "number" if t.isdigit() else "word"
        page.texts.append(Text(page.number, 0, x, y, w, h, t, kind, role="", font="ocr"))
        added += 1
    return added
