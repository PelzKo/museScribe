"""Truth check against a vector PDF: written pitches per bar read straight from the PDF text layer.

    python scripts/pdf_truth_check.py ghost 20 Bass
    python scripts/pdf_truth_check.py ghost 20 PianoReduction          # piano staves (last two of each system)
    python scripts/pdf_truth_check.py ghost 20 Drums                   # x / normal heads by staff position
    python scripts/pdf_truth_check.py anastasia 4 PianoReduction --truth Klavierauszug

Works on Finale exports (Ghost parts: Engraver / Maestro fonts; Anastasia PianoReduction: Petrucci), not
on scans. Staves come from the staff-line drawings, barlines from vertical lines spanning a staff (a grand
staff: both staves), bar numbers from the system start (Ghost) or above every bar (Anastasia). Pitch =
notehead origin (= notehead centre) relative to the top line + clef + key + accidentals in the bar.

Prints the bars whose multiset of written pitches differs from the truth (`pdf-only` / `truth-only`) and
bars that differ only by octave. Known false hits: notes tied into a bar (the accidental is carried when
the same staff position ends the previous bar; sometimes wrongly), key-change bars, %-repeat bars, cut bars ("94 -> 97"),
notes between the staves of a grand staff, slash / x heads. Check every hit on the page before logging it
in docs/TRUTH_DEVIATIONS.md.
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omrbench import project as project_mod  # noqa: E402
from omrbench import truth as truth_mod  # noqa: E402

HEADS = {"œ": "filled", "˙": "half", "w": "whole", "Ï": "filled", "ú": "half", "W": "breve"}
TOPLINE = {"&": ("F", 5), "?": ("A", 3), "B": ("G", 4), "V": ("F", 5)}   # clef glyph -> top-line pitch
STEPS = "CDEFGAB"
# b # n, double flat / sharp, parenthesised natural / flat / sharp (Petrucci)
ALTER = {"b": -1, "#": 1, "n": 0, "º": -2, "Ü": 2, "N": 0, "A": -1, "‹": 1, "∫": -2}
SHARPS, FLATS = "FCGDAEB", "BEADGCF"
MUSIC_FONTS = ("Engraver", "Maestro", "Petrucci")
RESTS = set("ŒÓ‰∑îÎ≈Ó·")


def pages(spec) -> list[int]:
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out += range(int(a), int(b) + 1)
        elif part:
            out.append(int(part))
    return out


def keymap(fifths: int) -> dict:
    return {(SHARPS if fifths > 0 else FLATS)[i]: 1 if fifths > 0 else -1 for i in range(abs(fifths))}


def step_pitch(clef: str, pos: int) -> tuple[str, int]:
    """pos = half staff spaces below the top line -> (step, octave)."""
    s, o = TOPLINE[clef]
    idx = STEPS.index(s) + o * 7 - pos
    return STEPS[idx % 7], idx // 7


def chars(page) -> list[tuple]:
    return [(c["origin"][0], c["origin"][1], c["c"], s["font"], s["size"])
            for bl in page.get_text("rawdict")["blocks"] for l in bl.get("lines", []) for s in l["spans"]
            for c in s["chars"] if c["c"].strip()]


def staves_of(page) -> list[dict]:
    """5 equally spaced horizontal lines with the same start -> staff (top, spacing, x0, x1)."""
    hl = []
    for g in page.get_drawings():
        for it in g["items"]:
            if it[0] == "l" and abs(it[1].y - it[2].y) < 0.3 and abs(it[1].x - it[2].x) > 60:
                hl.append((it[1].y, min(it[1].x, it[2].x), max(it[1].x, it[2].x)))
            elif it[0] == "re" and it[1].height < 0.8 and it[1].width > 60:
                hl.append((it[1].y0 + it[1].height / 2, it[1].x0, it[1].x1))
    hl.sort()
    st, used = [], set()
    for i, (y, x0, x1) in enumerate(hl):
        if i in used:
            continue
        grp = [i]
        for j in range(i + 1, len(hl)):
            if j in used or abs(hl[j][1] - x0) > 2:
                continue
            if len(grp) < 5 and 2.5 < hl[j][0] - hl[grp[-1]][0] < 6.5 and \
                    (len(grp) < 2 or abs((hl[j][0] - hl[grp[-1]][0]) - (hl[grp[1]][0] - hl[grp[0]][0])) < 0.3):
                grp.append(j)
        if len(grp) == 5:
            used.update(grp)
            ys = [hl[k][0] for k in grp]
            st.append(dict(top=ys[0], sp=(ys[4] - ys[0]) / 4, x0=x0, x1=x1))
    return sorted(st, key=lambda s: s["top"])


def vlines(page) -> list[tuple]:
    out = []
    for g in page.get_drawings():
        for it in g["items"]:
            if it[0] == "l" and abs(it[1].x - it[2].x) < 0.5:
                out.append((it[1].x, min(it[1].y, it[2].y), max(it[1].y, it[2].y), g.get("width") or 0))
            elif it[0] == "re" and it[1].width < 4 and it[1].height > 10:
                out.append((it[1].x0, it[1].y0, it[1].y1, it[1].width))
    return out


def clusters(xs, gap=12) -> list[float]:
    """Barline x positions; a repeat sign's thin + thick lines and ':||:' are one barline."""
    out = []
    for x in sorted(xs):
        if not out or x - out[-1] > gap:
            out.append(x)
    return out


def systems(pdf: Path, spec) -> list[dict]:
    d = pymupdf.open(pdf)
    res = []
    for pnum in pages(spec):
        p = d[pnum - 1]
        st, vl, ch = staves_of(p), vlines(p), chars(p)
        spans = [(s["bbox"], s["font"], s["size"], s["text"].strip()) for bl in p.get_text("dict")["blocks"]
                 for l in bl.get("lines", []) for s in l["spans"]]
        groups = []   # a system = staves joined by the vertical line at the system start
        for s in st:
            bot = s["top"] + 4 * s["sp"]
            if groups and any(abs(x - s["x0"]) < 3 and y0 <= groups[-1][-1]["top"] + 1 and y1 >= bot - 1
                              for x, y0, y1, _ in vl):
                groups[-1].append(s)
            else:
                groups.append([s])
        for g in groups:
            labs = sorted((b[0], t, z >= 9.5) for b, f, z, t in spans
                          if (f == "Helvetica" and z < 8 or f.startswith("Times") and "BoldIt" not in f and z < 11.5)
                          and re.fullmatch(r"\d+[A-Z]?", t) and -16 < b[3] - g[0]["top"] < 3)
            for s in g:
                bot = s["top"] + 4 * s["sp"]
                # stems are 0.6-2 pt wide, barlines thinner (thick final / repeat lines wider)
                s["bars"] = clusters(x for x, y0, y1, w in vl if y0 <= s["top"] + 0.6 and y1 >= bot - 0.6
                                     and x > s["x0"] + 5 and not 0.6 < w < 2)
                s["chars"] = [c for c in ch if s["top"] - 6 * s["sp"] < c[1] < bot + 6 * s["sp"]
                              and c[3].startswith(MUSIC_FONTS)]
            if len(g) >= 2:   # grand staff at the bottom: barlines run through both staves (stems never do)
                a, b = g[-2], g[-1]
                gb = clusters(x for x, y0, y1, w in vl if y0 <= a["top"] + 0.6
                              and y1 >= b["top"] + 4 * b["sp"] - 0.6 and x > b["x0"] + 5)
                if gb:
                    a["bars"] = b["bars"] = gb
            first = (g[-1]["bars"] or [1e9])[0]   # the system's own number stands before its first barline
            # small numbers first: a larger one may be the page number or a boxed rehearsal number
            labs = sorted((big, x, lab) for x, lab, big in labs if x < min(first, 70))
            res.append(dict(page=pnum, num=labs[0][2] if labs else None, staves=g))
    return res


def pdf_notes(pdf: Path, spec, seq: list[str], key_at, nstaves: int, perc: bool = False, cues: bool = False):
    """{(staff from the bottom group, truth bar index): [(step, alter, octave)]} for the last `nstaves`
    staves of every system. `seq` = the song's bar labels in truth order ("1", "72A", ...)."""
    sy = systems(pdf, spec)
    out = collections.defaultdict(list)
    cur = 1
    for s in sy:
        if s["num"] in seq:
            cur = seq.index(s["num"]) + 1
        s["start"] = cur
        digits = sorted({(round(c[0], 1), round(c[1]), c[2]) for t in s["staves"] for c in t["chars"]
                         if c[3].startswith("Maestro") and c[2].isdigit() and c[1] < t["top"] and c[4] > 3.4 * t["sp"]})
        mrest = []   # multirest numbers: neighbouring digit glyphs form one number ("1" "0" -> 10)
        for x, y, c in digits:
            if mrest and abs(mrest[-1][2] - y) < 2 and x - mrest[-1][3] < 14:
                mrest[-1] = (mrest[-1][0], mrest[-1][1] * 10 + int(c), y, x)
            else:
                mrest.append((x, int(c), y, x))
        mrest = [(x, m) for x, m, _, _ in mrest]
        for t in s["staves"]:   # a start-repeat after the key signature is no bar end: nothing stands left of it
            content = [c[0] for c in t["chars"] if c[2] in HEADS or c[2] in RESTS or c[2] == "x"
                       or c[3].startswith("Maestro") and c[2].isdigit() and c[1] < t["top"]]
            dots = [c for c in t["chars"] if c[2] in (".", "..") and t["top"] < c[1] < t["top"] + 4 * t["sp"]
                    and t["bars"] and 0 < c[0] - t["bars"][0] < 10]   # repeat dots inside the staff
            if t["bars"] and not any(x < t["bars"][0] for x in content) \
                    and (len(dots) >= 2 or any(c[2] == ".." for c in dots)):
                t["bars"] = t["bars"][1:]
        for si, t in enumerate(s["staves"][-nstaves:]):
            def bar_of(x):
                return cur + sum(1 for b in t["bars"] if b < x) + sum(m - 1 for mx, m in mrest if mx < x)
            clefs = sorted([c for c in t["chars"] if c[2] in TOPLINE and c[4] > 1.8 * t["sp"]
                            and t["top"] - 2 < c[1] < t["top"] + 4 * t["sp"] + 2])
            local = {}
            for x, y, c, font, size in sorted(t["chars"]):
                if perc:
                    if c not in ("œ", "x", "˙", "w") or not font.startswith("Maestro") or size < 2.6 * t["sp"]:
                        continue
                elif c not in HEADS or size < (2.6 if cues else 3.4) * t["sp"]:   # 2.6: cue-size heads count
                    continue
                if min(s["staves"], key=lambda u: abs(y - (u["top"] + 2 * u["sp"]))) is not t:
                    continue
                cl = [k for k in clefs if k[0] < x]
                if not cl and not perc:
                    continue
                b = bar_of(x)
                stp, octv = step_pitch("&" if perc else cl[-1][2], round((y - t["top"]) / (t["sp"] / 2)))
                if perc:
                    out[(si, b)].append((stp, "x" if c == "x" else 0, octv))
                    continue
                key = keymap(key_at(b))
                acc = [a for a in t["chars"] if a[2] in ALTER and abs(a[1] - y) < 0.3 * t["sp"]
                       and 0 < x - a[0] < 3.3 * t["sp"]]
                prev = out.get((si, b - 1), [])
                if acc:
                    alt = local[(b, stp, octv)] = ALTER[max(acc)[2]]
                elif (b, stp, octv) in local:
                    alt = local[(b, stp, octv)]
                elif not any(q[0] == stp and q[2] == octv for q in out[(si, b)]) and \
                        any(q[0] == stp and q[2] == octv and q[1] != key.get(stp, 0) for q in prev[-4:]):
                    # shortcut: assumes a tie from the previous bar keeps the accidental; check such hits by eye
                    alt = local[(b, stp, octv)] = next(q[1] for q in reversed(prev) if q[0] == stp and q[2] == octv)
                else:
                    alt = key.get(stp, 0)
                out[(si, b)].append((stp, alt, octv))
        cur += len(s["staves"][-1]["bars"]) + sum(m - 1 for _, m in mrest)
    return out, sy


def truth_notes(part, perc: bool = False):
    out = collections.defaultdict(list)
    for i, m in enumerate(part.findall("measure"), 1):
        for n in m.findall("note"):
            if n.find("rest") is not None or n.find("grace") is not None or n.findtext("notehead") == "slash":
                continue
            st = int(n.findtext("staff") or 1) - 1
            if perc and n.find("unpitched") is not None:
                u = n.find("unpitched")
                out[(st, i)].append((u.findtext("display-step"), "x" if n.findtext("notehead") == "x" else 0,
                                     int(u.findtext("display-octave"))))
            elif not perc and n.find("pitch") is not None:
                p = n.find("pitch")
                out[(st, i)].append((p.findtext("step"), int(float(p.findtext("alter") or 0)), int(p.findtext("octave"))))
    return out


def fmt(c: collections.Counter) -> str:
    acc = {1: "#", -1: "b", 2: "x", -2: "bb", "x": "(x)"}
    return " ".join(f"{s}{acc.get(a, '')}{o}" + (f"*{k}" if k > 1 else "")
                    for (s, a, o), k in sorted(c.items(), key=lambda kv: (kv[0][2], STEPS.index(kv[0][0]))))


def bar_labels(rows: dict) -> list[str]:
    """Truth order of the printed bars: pickup "0", lettered bars after their number."""
    n_bars = int(rows["bars"][1])
    letters = project_mod.letter_list(rows["letters"][1]) if rows.get("letters") and rows["letters"][1] else []
    seq = ["0"] if str(rows.get("time", [0, ""])[1] or "").startswith("0:") else []
    n = 1
    while len(seq) < n_bars:
        seq.append(str(n))
        seq += [f"{m}{l}" for m, l in letters if m == n]
        n += 1
    return seq[:n_bars]


def compare(show: str, song: str, part: str, tname: str | None = None, nstaves: int | None = None) -> list[str]:
    import openpyxl
    data = Path("data") / show
    ws = openpyxl.load_workbook(data / "songs.xlsx")[song]
    rows = {r[0]: r for r in ws.iter_rows(values_only=True) if r[0]}
    head = list(rows["file"])
    if not tname:
        cell = str(rows[part][head.index("truth")])
        tname = cell.split(",")[0].split("=")[-1].strip()
    perc = part.startswith("Drums")
    nstaves = nstaves or (2 if part in ("Utility", "PianoReduction") or part.startswith("Keyboard") else 1)
    seq = bar_labels(rows)
    keys = project_mod.bar_map(rows["key"][1])

    troot = truth_mod.load([data / t.strip() for t in rows["truth"][1].split(";")], Path("results/cache"), None)
    tpart = dict(truth_mod.parts(troot))[tname]
    chrom = int(tpart.findtext(".//transpose/chromatic") or 0)
    shift_fifths = (-chrom * 7 + 6) % 12 - 6   # written key of a transposing part (Bb: +2, F: +1)

    def key_at(i):
        num = int(re.match(r"\d+", seq[min(i, len(seq)) - 1]).group())
        concert = int(next((v for b, _, v in reversed(keys) if b <= num), keys[0][2]))
        return (concert + shift_fifths + 6) % 12 - 6 if shift_fifths else concert
    tn = truth_notes(tpart, perc)
    # the piano reductions print band intros in cue size and the truths have them; parts drop cues
    pb, _ = pdf_notes(data / "pdfs" / f"{part}.pdf", rows[part][1], seq, key_at, nstaves, perc,
                      cues=part == "PianoReduction")
    # a whole-part octave offset (guitar written an octave up) is not an error
    shift = collections.Counter(to - po for k in pb for (s, a, po) in pb[k] for (s2, a2, to) in tn.get(k, []) if (s, a) == (s2, a2))
    off = shift.most_common(1)[0][0] if shift else 0
    lines, octave_only = [f"=== {show} {song} {part} vs truth {tname!r} (octave offset {off:+d})"], []
    for st in range(nstaves):
        for i in range(1, len(seq) + 1):
            P = collections.Counter((s, a, o + off) for s, a, o in pb.get((st, i), []))
            T = collections.Counter(tn.get((st, i), []))
            if P == T:
                continue
            pc = lambda C: collections.Counter((s, a) for (s, a, _), k in C.items() for _ in range(k))  # noqa: E731
            if pc(P) == pc(T):
                octave_only.append(f"s{st + 1}:{seq[i - 1]}")
                continue
            lines.append(f"  staff {st + 1} bar {seq[i - 1]:>5}  pdf-only [{fmt(P - T)}]  truth-only [{fmt(T - P)}]"
                         f"  ({sum(P.values())} / {sum(T.values())} notes)")
    lines.append(f"  octave only: {' '.join(octave_only) or '-'}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("show")
    ap.add_argument("song")
    ap.add_argument("part", help="workbook row / PDF name (Bass, PianoReduction, Drums, ...)")
    ap.add_argument("--truth", help="truth part name (default: the first one in the row's truth cell)")
    ap.add_argument("--staves", type=int, help="compare the last N staves of each system (default 1, piano 2)")
    a = ap.parse_args()
    print("\n".join(compare(a.show, a.song, a.part, a.truth, a.staves)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
