"""First reading of a book by Codex: it compares the printed pages with our transcription and lists differences.

python scripts/review_codex.py <work/combined.mscx> <staff ids> "<book pdf>" <pages> <out dir>
       [--skip K] [--per 2] [--jobs 3] [--dpi 200] [--bars 1-80] [--label "staff 3 = Flöte 1, 5 = Piccolo"]
       [--song 5] [--letters 49A-B] [--passes 2]

pages: PDF pages (1-based) of the book, e.g. "3-8" or "3,5,7-9"; skip: systems at the top of the first page that
belong to the previous song. Every `per` pages go to one Codex call (run `jobs` at once) in its own empty temp folder,
so Codex never sees the repository (it could find the truth). Answers land in <out dir>/codex-p<a>-<b>.txt as lines
    bar | staff | transcription has | page shows | kind | sure/unsure
ending with "covered | <bars> | unreadable: <bars>"; a summary line per call is printed. --passes 2 runs a second,
independent reading per chunk (codex-p<a>-<b>.r2.txt): points both passes report are the most likely real ones.
--letters (workbook `letters` row) shows printed bar labels of lettered bars in the dump. A failed call (usage limit, network) is retried once after 2 minutes; if it
fails again its file says FAILED and the caller works without it.
"""
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_tool as T  # noqa: E402

PROMPT = """Do not read or search any files and do not run commands; use only the attached images and the text below.

The images {images} are pages {pages} of a scanned part book "{book}" of the musical Anastasia{song}.{skip}
Below is our transcription of the staves that come from this book. Compare it with the printed pages bar by bar
and list every place where the transcription differs from the print.
Staves: {label}

Transcription format: one line per bar (and voice), "<bar>: <items>", bars numbered like the print (multi-bar rests
expanded; "50[49A]:" = bar 50 of the transcription is printed bar 49A). C5/4. = dotted quarter (written pitch as printed, C4 = middle C), + joins chord notes, r8 = eighth rest,
rM = whole-bar rest, ~ = tie to the next note, [..] = marks on the note (articStaccatoAbove, articTenutoBelow,
articAccentAbove, articMarcatoAbove, trem:r16 = tremolo strokes (r8 = 1, r16 = 2, r32 = 3), arpeggio), Fermata before
a note = fermata on it, <mf> = dynamic, cresc(->17@3) / dim(...) = hairpin starting here and ending in bar 17,
3 quarters after the bar start, )hairpin = its end, Slur( / )Slur, gliss( = glissando, tuplet3:2{{ ... }},
grace: = grace note, "word" after a note = lyric, StaffText"..." / PlayTechAnnotation"..." = words, clefF = clef
change. Drum staves name the instrument instead of the pitch.

Conventions: these are NOT differences, do not report them:
- Under an 8va line the transcription has the notes one octave higher than printed (sounding pitch).
- Cue notes (small heads, or after another instrument's label up to "Play") are rests in the transcription; a line
  marked as another player's (label, small notes) is left out.
- Labels ("Solo", "to Flute", "Harp", "snares on"), boxed bar numbers, tempo words, "rit." and metronome marks are
  left out (tempo text lives on another staff). "Mute" / "con sord." = "gedämpft", "Open" / "senza sord." = "offen".
- "l.v." ties are left out.
- A hairpin starts on the note under its open end and ends at the dynamic it leads into, or at the end of the last
  note under its tip: report a hairpin only when it is missing, extra, the wrong kind, or off by more than one note.
- A tied chord held into the same chord has a tie on every note.

Answer ONLY with lines, one per difference, nothing else:
bar | staff | transcription has | page shows | kind | sure/unsure
kind = notes, rhythm, accidental, tie, dynamic, hairpin, articulation, slur, text, fermata, tremolo, clef, other.
Report only bars printed on these pages. If the print cannot be matched to the transcription at all (other bars,
other instrument), write one line saying so. Always end with exactly one line
covered | <first bar>-<last bar> | unreadable: <bars or "none">

{dump}
"""


def _pages(spec):
    out = []
    for r in spec.split(","):
        a, _, b = r.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def _dump(mscx, ids, bars, letters=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        T.dump(mscx, ids, bars, letters)
    return buf.getvalue()


def _call(prompt, images, answer, log):
    """One Codex run; True when it wrote an answer that ends with the 'covered' line."""
    answer.unlink(missing_ok=True)                 # never take a stale answer for a fresh one
    try:
        with tempfile.TemporaryDirectory(prefix="codex-") as tmp:   # empty folder: Codex sees only the images
            imgs = []
            for img in images:
                shutil.copy(img, Path(tmp) / Path(img).name)
                imgs += ["-i", str(Path(tmp) / Path(img).name)]
            with open(log, "w") as lf:
                r = subprocess.run(["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C",
                                    tmp, *imgs, "-o", str(answer), "-"], input=prompt, text=True, stdout=lf,
                                   stderr=subprocess.STDOUT, timeout=3600)
    except (subprocess.TimeoutExpired, OSError) as e:
        with open(log, "a") as lf:
            lf.write(f"\n{type(e).__name__}: {e}\n")
        return False
    return r.returncode == 0 and answer.exists() and any(
        x.strip().lower().startswith("covered") for x in answer.read_text().splitlines())


def run_chunk(dump, pdf, chunk, out, skip, dpi, label, song, first, run=1):
    """One Codex call for the pages of chunk; dump = the staves as text (made once in the main thread); run = pass
    number (independent second readings go to codex-p<a>-<b>.r2.txt)."""
    a, b = chunk[0], chunk[-1]
    stem = f"codex-p{a}-{b}" + (f".r{run}" if run > 1 else "")
    answer, log, prompt_file = out / f"{stem}.txt", out / f"{stem}.log", out / f"{stem}.prompt"
    imgdir = out / "img"
    images = []
    for p in chunk:
        images.append(imgdir / f"p{p}.png")   # rendered by main()
    prompt = PROMPT.format(images=", ".join(i.name for i in images), pages=f"{a}-{b}" if a != b else a,
                           book=Path(pdf).stem, song=f", song {song}" if song else "",
                           skip=f" Ignore the first {skip} system(s) on page {first}: they belong to the previous "
                                "song." if skip and first in chunk else "",
                           label=label, dump=dump)
    prompt_file.write_text(prompt)
    for attempt in (1, 2):
        if _call(prompt, images, answer, log):
            lines = [x for x in answer.read_text().splitlines() if x.count("|") >= 4]
            return f"pages {a}-{b}{f' pass {run}' if run > 1 else ''}: {len(lines)} differences -> {answer}"
        if attempt == 1:
            time.sleep(120)
    answer.write_text("FAILED: see " + log.name + "\n")
    return f"pages {a}-{b}: FAILED (see {log}; last lines: {' / '.join(log.read_text().splitlines()[-2:])})"


def main(argv):
    args, opts = [], {}
    it = iter(argv)
    for x in it:
        if x.startswith("--"):
            opts[x[2:]] = next(it)
        else:
            args.append(x)
    if len(args) != 5:
        raise SystemExit(__doc__)
    mscx, ids, pdf, pages, out = args
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pages = sorted(set(_pages(pages)))
    per = int(opts.get("per", 2))
    chunks = [pages[i:i + per] for i in range(0, len(pages), per)]
    dump = _dump(mscx, ids, opts.get("bars"), opts.get("letters"))        # stdout redirection is not thread-safe: do it here, once
    (out / "img").mkdir(exist_ok=True)
    dpi = int(opts.get("dpi", 200))
    with contextlib.redirect_stdout(io.StringIO()):
        for p in pages:
            T.render(pdf, p, out / "img" / f"p{p}.png", dpi=dpi)
    with ThreadPoolExecutor(int(opts.get("jobs", 3))) as ex:
        futs = [ex.submit(run_chunk, dump, pdf, c, out, int(opts.get("skip", 0)), dpi,
                          opts.get("label") or f"staff ids {ids}", opts.get("song"), pages[0], r)
                for r in range(1, int(opts.get("passes", 1)) + 1) for c in chunks]
        for f in futs:
            print(f.result(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
