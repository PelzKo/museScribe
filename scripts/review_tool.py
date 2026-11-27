"""Helpers for checking a transcribed song by hand or by an agent (docs/REVIEW_AGENT_PROMPT.md).

python scripts/review_tool.py extract <score.mscz> <dir>          unzip; the score is <dir>/combined.mscx
python scripts/review_tool.py pack <dir> <score.mscz>             zip <dir> back into a .mscz
python scripts/review_tool.py parts <file.mscx>                   parts, staff ids, bars per staff
python scripts/review_tool.py splice <base.mscx> <donor.mscx> <ids> <out.mscx>   copy staves (ids "3,4") from donor
python scripts/review_tool.py check <score.mscz|.mscx> [--bars N]  MuseScore export + bar count / bar length per part
python scripts/review_tool.py dump <file.mscx> <staff ids> [--bars 10-20,40-45] [--letters 49A-B]   part as text,
                         one line per bar and voice, written pitch, lyrics in quotes; with the workbook `letters`
                         a bar whose printed number differs shows it: 50[49A]
python scripts/review_tool.py lint <file.mscx> [--staves 3,4] [--fix-safe 1] [--plain "Part A,Part B"]   suspicious bars from the score alone
                                                                    (scripts/review_lint.py); fix-safe edits in place
python scripts/review_tool.py render <pdf> <page> <out.png> [--dpi 150] [--clip y0,y1[,x0,x1]]   page (1-based) to
                                                                    PNG; clip = band as page fractions, e.g. 0,0.33
"""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from fractions import Fraction
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))

MS = "/mnt/c/Program Files/MuseScore 4/bin/MuseScore4.exe"


def win(p: Path) -> str:
    return subprocess.run(["wslpath", "-w", str(Path(p).resolve())], check=True,
                          capture_output=True, text=True).stdout.strip()


def extract(mscz, d):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(mscz) as z:
        names = z.namelist()
        z.extractall(d)
    mscx = next(n for n in names if n.endswith(".mscx") and "/" not in n)
    if mscx != "combined.mscx":
        (d / mscx).rename(d / "combined.mscx")
    print(f"{d / 'combined.mscx'}")


def pack(d, mscz):
    d, mscz = Path(d), Path(mscz)
    tmp = mscz.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(d.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(d).as_posix())
    shutil.move(tmp, mscz)
    print(mscz)


def _score(path):
    return etree.parse(str(path)).getroot().find("Score")


def parts(path):
    score = _score(path)
    bars = {s.get("id"): len(s.findall("Measure")) for s in score.findall("Staff")}
    n = 0
    for p in score.findall("Part"):   # MuseScore 4 numbers the staves 1, 2, ... in part order
        ids = [str(n + k + 1) for k in range(len(p.findall("Staff")))]
        n += len(ids)
        name = p.findtext("trackName") or p.findtext("Instrument/longName")
        print(f"{name}: staves {','.join(ids)}; bars {', '.join(str(bars.get(i)) for i in ids)}")


def splice(base, donor, ids, out):
    ids = set(ids.split(","))
    tree = etree.parse(str(base))
    score = tree.getroot().find("Score")
    new = {s.get("id"): s for s in _score(donor).findall("Staff") if s.get("id") in ids}
    if new.keys() != ids:
        raise SystemExit(f"donor lacks staves {sorted(ids - new.keys())}")
    for s in score.findall("Staff"):
        if s.get("id") in ids:
            s.addprevious(new[s.get("id")])
            score.remove(s)
    tree.write(str(out), xml_declaration=True, encoding="UTF-8")
    print(out)


def check(path, bars=None):
    path = Path(path)
    with tempfile.TemporaryDirectory(dir=path.parent.parent) as t:   # outside a work dir that gets packed
        t = Path(t)
        if path.suffix == ".mscx":           # a work dir: pack its folder
            src = t / "check.mscz"
            files = [f for f in path.parent.rglob("*") if f.is_file()]
            with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as z:
                for f in files:
                    z.write(f, "combined.mscx" if f == path else f.relative_to(path.parent).as_posix())
        else:
            src = path
        xml = t / "check.musicxml"
        r = subprocess.run([MS, "-o", win(xml), win(src)], capture_output=True, timeout=600)
        clean = r.returncode == 0 and xml.exists()
        if not clean:
            subprocess.run([MS, "-f", "-o", win(xml), win(src)], capture_output=True, timeout=600)
        if not xml.exists():
            raise SystemExit(f"MuseScore cannot open the score (exit {r.returncode})")
        print(f"MuseScore export: {'clean' if clean else f'only with -f (exit {r.returncode}: bar counts or lengths differ)'}")
        root = etree.parse(str(xml)).getroot()
    from omrbench.metrics.notef1 import bar_lengths
    names = {p.get("id"): p.findtext("part-name") for p in root.iter("score-part")}
    bad_total = 0
    for part in root.findall("part"):
        measures, lens = part.findall("measure"), bar_lengths(part)
        beats = beat_type = None
        bad = []
        for m, ln in zip(measures, lens):
            t = m.find("attributes/time")
            if t is not None and t.findtext("beats"):
                beats, beat_type = int(t.findtext("beats")), int(t.findtext("beat-type"))
            want = Fraction(4 * beats, beat_type) if beats else None
            if ln and want and ln != want and not (m.get("implicit") == "yes" and ln < want):   # pickup
                bad.append(f"{m.get('number')}:{ln}/{want}")
        n = len(measures)
        flag = "" if bars is None or n == bars else f"  <-- expected {bars} bars"
        bad_total += len(bad) + bool(flag)
        print(f"{names[part.get('id')]}: {n} bars, {len(bad)} wrong length (bar:filled/meter in quarters) "
              f"{' '.join(bad)}{flag}")
    if path.suffix == ".mscx":          # whole-bar rests of the wrong length pass MuseScore's export unnoticed
        import review_lint
        rests = [ln for ln in review_lint.lint(path).splitlines() if "whole-bar rest" in ln]
        bad_total += len(rests)
        if rests:
            print(f"{len(rests)} whole-bar rests of the wrong length (lint --fix-safe 1 fixes them)")
    print("OK" if clean and not bad_total else "NOT OK")
    if not (clean and not bad_total):
        sys.exit(1)


DUR = {"whole": "1", "half": "2", "quarter": "4", "eighth": "8", "16th": "16", "32nd": "32", "64th": "64",
       "breve": "0", "measure": "M"}


def _name(tpc, midi):
    step = "FCGDAEB"[(tpc + 1) % 7]
    alter = (tpc + 1) // 7 - 2
    semis = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]
    octave = (midi - alter - semis) // 12 - 1
    return f"{step}{'#' * alter if alter > 0 else 'b' * -alter}{octave}"


WHOLE = {"whole": Fraction(1), "half": Fraction(1, 2), "quarter": Fraction(1, 4), "eighth": Fraction(1, 8),
         "16th": Fraction(1, 16), "32nd": Fraction(1, 32), "64th": Fraction(1, 64), "breve": Fraction(2)}


def _q(fr):  # whole-note fraction -> quarters as text
    q = fr * 4
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def _token(el, trans, drums=None, bar=0, pos=Fraction(0)):
    tag = el.tag
    if tag in ("Chord", "Rest"):
        d = DUR.get(el.findtext("durationType"), el.findtext("durationType")) + "." * int(el.findtext("dots") or 0)
        if tag == "Rest":
            return f"r{d}"
        grace = next((g.tag for g in el if g.tag.startswith(("grace", "acciaccatura", "appoggiatura"))), None)
        notes = []
        for n in el.findall("Note"):
            midi = int(n.findtext("pitch")) - trans
            tpc = int(n.findtext("tpc2") or n.findtext("tpc"))
            tie = "~" if n.find("Spanner[@type='Tie']/next") is not None else ""
            gl = " gliss(" if n.find("Spanner[@type='Glissando']/next") is not None else ""
            name = drums.get(int(n.findtext("pitch")), f"drum{n.findtext('pitch')}") if drums else _name(tpc, midi)
            notes.append(name + (f"({n.findtext('head')})" if drums and n.findtext("head") else "") + tie + gl)
        marks = [a.findtext("subtype") or a.tag for a in el if a.tag in ("Articulation", "Fermata", "Ornament")]
        marks += [f"trem:{t.findtext('subtype')}" for t in el.iter("TremoloSingleChord", "Tremolo", "TremoloTwoChord")]
        marks += ["arpeggio" for _ in el.findall("Arpeggio")]
        slurs = [s for s in el.findall("Spanner") if s.get("type") == "Slur"]   # MuseScore 4 keeps slurs in the chord
        pre = "".join("Slur( " for s in slurs if s.find("next") is not None)
        post = "".join(" )Slur" for s in slurs if s.find("prev") is not None)
        return (pre + ("grace:" if grace else "") + "+".join(notes) + "/" + d + "".join(f"[{m}]" for m in marks)
                + post)
    if tag == "Dynamic":
        return f"<{el.findtext('subtype')}>"
    if tag == "Spanner":
        kind = el.get("type")
        if kind == "HairPin":
            sub = el.findtext("HairPin/subtype")
            kind = {"0": "cresc", "1": "dim", "2": "cresc.line", "3": "dim.line"}.get(sub, "hairpin")
        loc = el.find("next/location")
        if loc is None:
            return f"){kind}"
        end_bar = bar + int(loc.findtext("measures") or 0)
        end_pos = pos + Fraction(loc.findtext("fractions") or 0)
        return f"{kind}(->{end_bar}@{_q(end_pos)})"
    if tag == "Tuplet":
        return f"tuplet{el.findtext('actualNotes')}:{el.findtext('normalNotes')}{{"
    if tag == "endTuplet":
        return "}"
    if tag in ("StaffText", "Expression", "SystemText", "TempoText", "RehearsalMark", "PlayTechAnnotation"):
        text = "".join(el.find("text").itertext()) if el.find("text") is not None else ""
        return f'{tag}"{text}"'
    if tag == "TimeSig":
        return f"time{el.findtext('sigN')}/{el.findtext('sigD')}"
    if tag == "KeySig":
        return f"key{el.findtext('concertKey') or el.findtext('accidental')}(concert)"
    if tag == "Clef":
        return f"clef{el.findtext('concertClefType')}"
    if tag in ("eid", "location", "BarLine", "Beam", "linkedMain", "Harmony") and tag != "BarLine":
        return ""
    if tag == "BarLine":
        return f"barline:{el.findtext('subtype')}"
    return tag


def _ranges(bars):
    """'1-20,40,52-60' -> [(1, 20), (40, 40), (52, 60)]; None = every bar."""
    if not bars:
        return [(1, 10 ** 6)]
    out = []
    for r in str(bars).split(","):
        lo, _, hi = r.partition("-")
        out.append((int(lo), int(hi or lo)))
    return out


def _lyrics(chord):
    out = ""
    for ly in chord.findall("Lyrics"):
        s = ly.findtext("text") or ""
        if ly.findtext("syllabic") in ("begin", "middle"):
            s += "-"
        if ly.findtext("no"):
            s += "+" + str(int(ly.findtext("no")) + 1)
        out += f'"{s}"'
    return out


def labels(letters):
    """Workbook `letters` ('49A-B, 132A-C') -> {ordinal bar: printed label} for the bars after which lettered bars
    follow: 49A-B makes ordinal 50 = 49A, 51 = 49B, 52 = 50, ..."""
    extra = {}
    for spec in (letters or "").replace(";", ",").split(","):
        spec = spec.strip()
        if not spec:
            continue
        n = int("".join(ch for ch in spec if ch.isdigit()))
        a, _, z = spec[len(str(n)):].partition("-")
        extra[n] = [chr(c) for c in range(ord(a), ord(z or a) + 1)]
    out, printed, i = {}, 0, 0
    while i < 10 ** 4:
        printed += 1
        i += 1
        out[i] = str(printed)
        for ch in extra.get(printed, []):
            i += 1
            out[i] = f"{printed}{ch}"
        if printed > 2000:
            break
    return out


def dump(path, ids, bars=None, letters=None):
    import review_edit as E
    root = etree.parse(str(path)).getroot().find("Score")
    trans, drums, n = {}, {}, 0
    for p in root.findall("Part"):
        kit = {int(d.get("pitch")): d.findtext("name").replace(" ", "_") for d in p.iter("Drum")}
        for _ in p.findall("Staff"):
            n += 1
            trans[str(n)] = int(p.findtext("Instrument/transposeChromatic") or 0)
            drums[str(n)] = kit
    ranges = _ranges(bars)
    lab = labels(letters) if letters else {}
    for sid in str(ids).split(","):
        staff = root.find(f"Staff[@id='{sid}']")
        print(f"== staff {sid} ({'drum set: instrument names' if drums[sid] else 'written pitch'}; "
              f"transposeChromatic {trans[sid]}; spanner ends as ->bar@quarters from the bar start)")
        for i, m in enumerate(staff.findall("Measure"), 1):
            if not any(lo <= i <= hi for lo, hi in ranges):
                continue
            for v, voice in enumerate(m.findall("voice"), 1):
                toks = []
                walk = list(E._walk(voice))
                starts = {p for e, p, ln in walk if ln}
                for e, pos, _ in walk:
                    t = _token(e, trans[sid], drums[sid], i, pos)
                    if t and e.tag not in ("Chord", "Rest") and pos not in starts and pos:
                        t += f"@{_q(pos)}"           # sits between notes: show where
                    if t and e.tag == "Chord":
                        t += _lyrics(e)
                    if t:
                        toks.append(t)
                if toks and not (v > 1 and all(t.startswith("r") for t in toks)):
                    tag = f"[{lab[i]}]" if lab.get(i, str(i)) != str(i) else ""
                    print(f"{i}{tag}{'' if v == 1 else f' v{v}'}{' len=' + m.get('len') if m.get('len') else ''}: {' '.join(toks)}")


def render(pdf, page, out, dpi=150, clip=None):
    import pymupdf as fitz
    pg = fitz.open(pdf)[int(page) - 1]
    rect = pg.rect
    if clip:
        y0, y1, x0, x1 = ([float(x) for x in clip.split(",")] + [0, 1])[:4]
        rect = fitz.Rect(rect.width * x0, rect.height * y0, rect.width * x1, rect.height * y1)
    pg.get_pixmap(dpi=int(dpi), clip=rect).save(out)
    print(out)


def main(argv):
    if not argv or argv[0] not in {"extract", "pack", "parts", "splice", "check", "render", "dump", "lint"}:
        raise SystemExit(__doc__)
    cmd, args = argv[0], argv[1:]
    opts = {}
    while "--" in " ".join(args):
        i = next(i for i, a in enumerate(args) if a.startswith("--"))
        opts[args[i][2:]] = args[i + 1]
        del args[i:i + 2]
    if cmd == "check" and "bars" in opts:
        opts["bars"] = int(opts["bars"])
    if cmd == "lint":
        import review_lint
        return review_lint.main(*args, staves=opts.get("staves"), fix_safe=opts.get("fix-safe") == "1",
                                plain=opts.get("plain", ""))
    globals()[cmd](*args, **opts)


if __name__ == "__main__":
    main(sys.argv[1:])
