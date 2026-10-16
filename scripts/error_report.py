"""Error overview: every difference between output and truth, sorted by kind and counted.

    python scripts/error_report.py anastasia,ghost --run p1 [--songs 13] [--out results/errors/p1]

Same pairing (workbook `truth` cells, `plain` rows, `unfinished`) and the same bar alignment as
`omrbench bench` (metrics/edits.py: DP over bars, whole-part shift, octave sections). Inside each
matched bar the notes and markings are diffed one by one and every difference gets a kind (wrong
octave, missing dot, missing staccato, ...). No weights: one note can count several times (wrong
pitch + wrong length = 2). Writes <out>/errors.json (counts, examples, per part) and errors.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omrbench import config as config_mod  # noqa: E402
from omrbench import musicxml  # noqa: E402
from omrbench import project as project_mod  # noqa: E402
from omrbench import truth as truth_mod  # noqa: E402
from omrbench.bench import _norm, _unique, resolve  # noqa: E402
from omrbench.metrics import edits, notef1  # noqa: E402
from omrbench.transcribe import output_names  # noqa: E402

_STEP = "CDEFGAB"
FREE_TEXT = ("words", "lyrics", "systemtext", "rehearsal", "chords", "tempo")   # token = text: no per-token rows


# --------------------------------------------------------------------------- notes with details

def detailed_notes(part) -> list[dict]:
    """notef1.notes plus what a note looks like: spelling, note value, dots, tuplet."""
    plain = notef1.notes(part)
    out, k = [], 0
    for mi, measure in enumerate(part.findall("measure")):
        for el in measure.iter("note"):
            if el.find("grace") is not None or el.find("rest") is not None or el.find("cue") is not None \
                    or (el.find("type") is not None and el.find("type").get("size") == "cue"):
                continue
            bar, staff, onset, midi, dur = plain[k]
            k += 1
            p = el.find("pitch")
            tm = el.find("time-modification")
            out.append({"bar": bar, "staff": staff, "onset": onset, "midi": midi, "dur": dur,
                        "step": p.findtext("step", "").strip() if p is not None else None,
                        "alter": int(float(p.findtext("alter") or 0)) if p is not None else 0,
                        "oct": int(p.findtext("octave") or 4) if p is not None else None,
                        "type": (el.findtext("type") or "").strip(), "dots": len(el.findall("dot")),
                        "tup": f"{tm.findtext('actual-notes')}:{tm.findtext('normal-notes')}" if tm is not None else ""})
    assert k == len(plain), (k, len(plain))
    return out


def _dur_kinds(p: dict, t: dict) -> list[str]:
    if p["tup"] != t["tup"]:
        return ["rhythm: wrong tuplet" if p["tup"] and t["tup"] else
                "rhythm: triplet / tuplet missing" if t["tup"] else "rhythm: tuplet made up"]
    if p["type"] == t["type"] and p["dots"] != t["dots"]:
        return ["rhythm: dot missing" if p["dots"] < t["dots"] else "rhythm: dot made up"]
    r = p["dur"] / t["dur"] if t["dur"] else None
    if r in (2, 4):
        return [f"rhythm: note value x{r} too long"]
    if r in (Fraction(1, 2), Fraction(1, 4)):
        return [f"rhythm: note value 1/{int(1 / r)} too short"]
    return ["rhythm: other wrong length (" + ("longer" if r and r > 1 else "shorter") + ")"]


def _pitch_kinds(p: dict, t: dict) -> list[str]:
    if isinstance(t["midi"], str) or isinstance(p["midi"], str):
        return ["drums: wrong kit instrument (staff position)"]
    if p["midi"] is None or t["midi"] is None:
        return ["pitch: slash vs pitched note"]
    d = p["midi"] - t["midi"]
    if d and d % 12 == 0:
        return [f"pitch: octave off ({d // 12:+d})"]
    if p["step"] and t["step"]:
        sd = (_STEP.index(p["step"]) + 7 * p["oct"]) - (_STEP.index(t["step"]) + 7 * t["oct"])
        if sd == 0:
            return ["pitch: accidental missing" if t["alter"] and not p["alter"] else
                    "pitch: accidental made up" if p["alter"] and not t["alter"] else "pitch: wrong accidental"]
        if abs(sd) == 1:
            return ["pitch: one staff step off" + ("" if p["alter"] == t["alter"] else " + accidental")]
        if abs(sd) == 2:
            return ["pitch: two staff steps off (a third)"]
    return ["pitch: wrong by more than a third"]


def diff_notes(P: list[dict], T: list[dict], log) -> None:
    """Pair the bar's notes and log one error per wrong attribute."""
    slash = {(n["staff"], n["onset"]) for n in T if n["midi"] is None}
    if slash:      # truth slashes: rhythm only (one per onset), like the edit penalty
        seen, folded = set(), []
        for n in P:
            k = (n["staff"], n["onset"])
            if k in slash:
                if (k, n["dur"]) in seen:
                    continue
                seen.add((k, n["dur"]))
                n = {**n, "midi": None, "step": None}
            folded.append(n)
        P = folded
    P, T = list(P), list(T)

    def take(match):
        for t in list(T):
            for p in P:
                if match(p, t):
                    P.remove(p)
                    T.remove(t)
                    yield p, t
                    break

    full = lambda p, t: all(p[k] == t[k] for k in ("staff", "onset", "midi", "dur"))  # noqa: E731
    matched_onsets = set()
    for p, t in take(full):
        matched_onsets.add((t["staff"], t["onset"]))
        if p["step"] and t["step"] and (p["step"], p["alter"]) != (t["step"], t["alter"]):
            log("pitch: enharmonic spelling (sounds right)")
        elif p["type"] and t["type"] and (p["type"], p["dots"], p["tup"]) != (t["type"], t["dots"], t["tup"]):
            log("rhythm: same length, other notation")
    same = lambda *ks: lambda p, t: all(p[k] == t[k] for k in ks)  # noqa: E731
    for p, t in take(same("staff", "onset", "midi")):
        for k in _dur_kinds(p, t):
            log(k)
    for p, t in take(same("staff", "onset", "dur")):
        for k in _pitch_kinds(p, t):
            log(k)
    for p, t in take(same("onset", "midi", "dur")):
        log("note on the wrong staff (piano)")
    for p, t in take(same("staff", "midi", "dur")):
        log("rhythm: note at the wrong beat (onset shifted)")
    for p, t in take(same("staff", "onset")):
        for k in _pitch_kinds(p, t) + _dur_kinds(p, t):
            log(k)
    t_onsets = Counter((t["staff"], t["onset"]) for t in T)
    for t in T:
        drum = isinstance(t["midi"], str)
        if drum:
            log("drums: hit missing")
        elif (t["staff"], t["onset"]) in matched_onsets:
            log("notes: chord note missing")
        else:
            log("notes: note missing")
    for p in P:
        if isinstance(p["midi"], str):
            log("drums: hit made up")
        elif (p["staff"], p["onset"]) in matched_onsets or t_onsets[(p["staff"], p["onset"])]:
            log("notes: extra chord note")
        else:
            log("notes: note made up")


def diff_items(p: Counter, t: Counter, log, rest_only: bool = False) -> None:
    """Markings of one bar: (cat, staff, onset, token) multisets."""
    P, T = list((p - t).elements()), list((t - p).elements())
    for k in [k for k in P if k[0] == "slurs"]:                  # a tie read as a slur
        m = next((x for x in T if x[0] == "ties" and x[1:3] == k[1:3]), None)
        if m:
            P.remove(k)
            T.remove(m)
            log("ties: tie read as a slur")
    for cat in sorted({k[0] for k in P + T}):
        if cat == "barlen":
            if any(k[0] == cat for k in P) and any(k[0] == cat for k in T):
                log("bars: bar length wrong" + (" (whole-bar rest with the wrong duration)" if rest_only
                                                else " (notes / rests do not add up like the truth bar)"))
            continue
        cp = [k for k in P if k[0] == cat]
        ct = [k for k in T if k[0] == cat]
        label = (lambda tok: "") if cat in FREE_TEXT else (lambda tok: f" `{tok}`")
        for t in list(ct):                                       # same token elsewhere in the bar
            m = next((k for k in cp if k[3] == t[3] and k[1] == t[1]), None)
            if m:
                cp.remove(m)
                ct.remove(t)
                log(f"{cat}: at the wrong beat{label(t[3])}")
        for t in list(ct):                                       # other token at the same beat
            m = next((k for k in cp if k[2] == t[2] and k[1] == t[1]), None)
            if m:
                cp.remove(m)
                ct.remove(t)
                log(f"{cat}: wrong" + ("" if cat in FREE_TEXT else f" `{m[3]}` instead of `{t[3]}`"),
                    f"{m[3]!s} / {t[3]!s}"[:80] if cat in FREE_TEXT else None)
        for t in ct:
            log(f"{cat}: missing{label(t[3])}", str(t[3])[:60] if cat in FREE_TEXT else None)
        for k in cp:
            log(f"{cat}: made up{label(k[3])}", str(k[3])[:60] if cat in FREE_TEXT else None)


# --------------------------------------------------------------------------- per part

class Log:
    def __init__(self):
        self.count = Counter()
        self.examples: dict[str, list] = defaultdict(list)
        self.per_part: dict[str, Counter] = defaultdict(Counter)
        self.texts: dict[str, Counter] = defaultdict(Counter)

    def at(self, where: str, part: str):
        def log(kind: str, text: str | None = None):
            self.count[kind] += 1
            self.per_part[part][kind] += 1
            if where not in self.examples[kind][-1:]:
                self.examples[kind].append(where)
            if text:
                self.texts[kind][text] += 1
        return log


def part_errors(pred_parts, tpart, sys_words, name: str, L: Log) -> None:
    t_numbers = [m.get("number", str(i + 1)) for i, m in enumerate(tpart.findall("measure"))]
    pred, truth = edits.part_bars(pred_parts, sys_words), edits.part_bars([tpart])
    tnotes = defaultdict(list)
    for n in detailed_notes(tpart):
        tnotes[n["bar"]].append(n)
    pnotes = defaultdict(list)
    for part in pred_parts:
        for n in detailed_notes(part):
            pnotes[n["bar"]].append(n)
    if not any(n or i for n, i in pred):
        log = L.at("whole part", name)
        log("part: no output at all (every truth item below counts as missing)")
        for j, t in enumerate(truth):
            diff_notes([], tnotes[j], log)
            diff_items(Counter(), t[1], log)
        return
    cost, path = edits._align(pred, truth)
    shift = 0
    s = edits._best_shift(pred, truth)
    if s and edits._align(edits._shifted(pred, s), truth)[0] + 1 < cost:
        shift = s
        pred = edits._shifted(pred, s)
        path = edits._align(pred, truth)[1]
        L.at("whole part", name)(f"part: whole part transposed ({-s:+d} semitones; 1 bulk action)")
    _, shifted = edits._octave_regions(pred, truth, path)
    for i, j in path:
        num = t_numbers[j] if j is not None and not t_numbers[j].startswith("X") else f"#{(j or 0) + 1}"
        where = f"{name} bar {num}" if j is not None else f"{name} (extra bar after output bar {i + 1})"
        log = L.at(where, name)
        if i is None:
            n = len(tnotes[j])
            log("bars: bar missing (" + ("with notes" if n else "empty or rests only") + ")")
            for _ in range(n):
                log("bars: note inside a missing bar")
            items = sum(c for k, c in truth[j][1].items() if k[0] != "barlen")
            for _ in range(items):
                log("bars: marking inside a missing bar")
            continue
        if j is None:
            log("bars: extra bar (" + ("with notes" if pnotes[i] else "empty") + ")")
            continue
        sec = next((x for x in edits.REGION_SHIFTS if x and edits._shifted(pred, x)[i] == shifted[i]), 0) \
            if shifted[i] != pred[i] else 0
        P = [{**n, "midi": n["midi"] + shift + sec} if isinstance(n["midi"], int) else n for n in pnotes[i]]
        if sec:
            log(f"pitch: bar in an octave-off section ({-sec // 12:+d} octave)")
            P = [{**n, "step": None} if isinstance(n["midi"], int) else n for n in P]
        elif shift:
            P = [{**n, "step": None} if isinstance(n["midi"], int) else n for n in P]
        diff_notes(P, tnotes[j], log)
        diff_items(shifted[i][1], truth[j][1], log, rest_only=not pnotes[i])


def run(cfg: dict, show: str, run_id: str, songs, L: Log, totals: Counter) -> None:
    proj = project_mod.load(project_mod.find(Path(cfg["data_dir"]), show))
    selected, _ = proj.select(songs)
    src = Path(cfg["results_dir"]) / proj.name / "runs" / run_id
    cache = Path(cfg["results_dir"]) / "cache"
    for song in [s for s in selected if s.truth]:
        troot = truth_mod.load(song.truth_files, cache, cfg.get("musescore_cli"))
        tparts = {_norm(n): (n, p) for n, p in truth_mod.parts(troot)}
        for n in {_norm(n) for p in song.parts for n in p.plain} & tparts.keys():
            musicxml.strip_marks(tparts[n][1])
        sys_words = edits.system_words(troot)
        unfinished = {_norm(n) for n in song.unfinished}
        roots = []
        for part in song.parts:
            if not part.truth:
                continue
            files = [src / song.id / n for n in output_names(part.name, part.meta)]
            oroots = [musicxml.load(f) for f in files if f.exists()]
            roots += oroots
            outputs = [(n, p) for n, p, _ in _unique([(n, p, r) for r in oroots for n, p in truth_mod.parts(r)])]
            mapping, _, _ = resolve(part, outputs)
            el = dict(outputs)
            for tname, onames in mapping.items():
                if _norm(tname) in unfinished or _norm(tname) not in tparts:
                    continue
                tn, tpart = tparts[_norm(tname)]
                label = f"{show} {song.id} {tn}"
                totals["truth notes"] += len(notef1.notes(tpart))
                totals["parts"] += 1
                part_errors([el[o] for o in onames], tpart, sys_words, label, L)
        # rehearsal marks, tempi, system text: once per song (edits.system_penalty)
        t_st = musicxml.extract_staves(troot)
        t = edits._system_items(t_st)
        p = edits._system_items([s for r in roots for s in musicxml.extract_staves(r)], cluster=2,
                                words=frozenset(x for s in t_st for _, _, x in s.events["systemtext"]), truth=t)
        log = L.at(f"{show} {song.id} (system)", f"{show} {song.id} (system items)")
        as_items = lambda c: Counter({(cat, 0, b, tok): 1 for cat, b, tok in c})  # noqa: E731
        diff_items(as_items(p), as_items(t), log)


def markdown(L: Log, totals: Counter) -> str:
    groups = defaultdict(list)
    for kind, n in L.count.most_common():
        groups[kind.split(":")[0]].append((kind, n))
    out = [f"Parts compared: {totals['parts']}, truth notes: {totals['truth notes']}, "
           f"differences: {sum(L.count.values())}", ""]
    for g, rows in sorted(groups.items(), key=lambda x: -sum(n for _, n in x[1])):
        out += [f"### {g} ({sum(n for _, n in rows)})", "",
                "| error | count | by show | most in | first at |", "|---|---|---|---|---|"]
        for kind, n in rows:
            parts = Counter({p: c[kind] for p, c in L.per_part.items() if c[kind]})
            shows = Counter()
            for p, c in parts.items():
                shows[p.split()[0]] += c
            ex = "; ".join(L.examples[kind][:2])
            if L.texts.get(kind):
                ex += " — e.g. " + ", ".join(f"\"{t}\" ×{c}" for t, c in L.texts[kind].most_common(4))
            out.append(f"| {kind.split(': ', 1)[-1]} | {n} | " + ", ".join(f"{s} {c}" for s, c in shows.most_common())
                       + " | " + ", ".join(f"{p} {c}" for p, c in parts.most_common(3)) + f" | {ex} |")
        out.append("")
    out += ["### per part (top 6 kinds)", "", "| part | total | top kinds |", "|---|---|---|"]
    for part, c in sorted(L.per_part.items(), key=lambda x: -sum(x[1].values())):
        out.append(f"| {part} | {sum(c.values())} | " + ", ".join(f"{k} {n}" for k, n in c.most_common(6)) + " |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shows", help="comma list")
    ap.add_argument("--run", required=True)
    ap.add_argument("--songs")
    ap.add_argument("--out")
    ap.add_argument("-c", "--config", default="bench.yaml")
    a = ap.parse_args()
    cfg = config_mod.load(Path(a.config))
    L, totals = Log(), Counter()
    for show in a.shows.split(","):
        run(cfg, show, a.run, a.songs.split(",") if a.songs else None, L, totals)
    out = Path(a.out or Path(cfg["results_dir"]) / "errors" / a.run)
    out.mkdir(parents=True, exist_ok=True)
    (out / "errors.json").write_text(json.dumps(
        {"totals": totals, "count": L.count, "locations": L.examples, "texts": L.texts,
         "per_part": L.per_part}, indent=1, ensure_ascii=False), encoding="utf-8")
    text = markdown(L, totals)
    (out / "errors.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
