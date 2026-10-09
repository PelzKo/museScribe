"""Second OCR pass for bar numbers, ranges, multi-rest counts and cut marks.

Audiveris' text recognition misses whole pages of bar numbers now and then ("230-237"
under a rest, "[to] 194"), and without them the bars can't be lined up. Here Tesseract
reads strips above and below every staff (the rest of the page masked white, one call
per page); tokens that look like bar evidence are added as text atoms where Audiveris
has no text, so text.classify treats them like its own.

The Tesseract binary is the one bundled in Audiveris' jars (extracted once into
$OMRBENCH_HOME/tools/tesseract); a `tesseract` on PATH is used if there is one.
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


def find_tesseract(home: Path) -> tuple[str, dict] | None:
    """(executable, environment) or None if neither PATH nor Audiveris has one."""
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


def _read_page(page: Page, img_path: Path, tess: tuple[str, dict], tmp: Path) -> list[dict]:
    """Words read in the strips around the staves, in page coordinates."""
    with Image.open(img_path) as im0:
        im = im0.convert("L")
    sx = im.width / page.width if page.width else 1.0
    canvas = Image.new("L", im.size, 255)
    for sy in page.systems:
        if sy.skip:
            continue
        for st in sy.all_staves:
            il = st.interline
            for top, bot in ((st.top - STRIP * il, st.top - 0.1 * il),
                             (st.bottom + 0.1 * il, st.bottom + STRIP * il)):
                box = (max(0, int((st.left - 4 * il) * sx)), max(0, int(top * sx)),
                       min(im.width, int((st.right + 2 * il) * sx)), min(im.height, int(bot * sx)))
                if box[2] > box[0] and box[3] > box[1]:
                    canvas.paste(im.crop(box), box[:2])
    canvas.save(tmp)
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

    exe, env = tess
    r = subprocess.run([exe, str(tmp), "stdout", "--psm", "11", "-l", "eng",
                        "-c", "tessedit_create_tsv=1"],
                       capture_output=True, text=True, env=env, timeout=300)
    tmp.unlink(missing_ok=True)
    words = []
    for row in csv.DictReader(io.StringIO(r.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        try:
            if row.get("level") != "5" or float(row["conf"]) < MIN_CONF:
                continue
            x, y = int(row["left"]) / sx, int(row["top"]) / sx
            w, h = int(row["width"]) / sx, int(row["height"]) / sx
            words.append({"text": row["text"], "conf": float(row["conf"]), "x": x, "y": y,
                          "w": w, "h": h, "multirest": multirest_below(x, w, y + h)})
        except (KeyError, TypeError, ValueError):
            continue
    return words


def read_pages(pages: list[Page], images: list[Path], tess: tuple[str, dict], cache: Path,
               jobs: int = 4) -> list[list[dict]]:
    """Words per page; cached as JSON in `cache` (reassemble reuses them)."""
    cache.mkdir(parents=True, exist_ok=True)

    def one(i: int) -> list[dict]:
        f = cache / f"page{i + 1:02d}.json"
        if f.exists():
            return json.loads(f.read_text())
        words = _read_page(pages[i], images[i], tess, cache / f"page{i + 1:02d}-mask.png")
        f.write_text(json.dumps(words))
        return words

    with ThreadPoolExecutor(max(1, jobs)) as ex:
        return list(ex.map(one, range(min(len(pages), len(images)))))


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
