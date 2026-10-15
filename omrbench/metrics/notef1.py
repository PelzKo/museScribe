"""Note F1 per part: fast, transposition-proof comparison against a full-score truth.

A note is (bar index, staff, onset in quarters, sounding pitch, duration in quarters). Bars are
matched by index (the pipeline aligns bar numbers to the printed ones, the truth starts at bar
1). Predicted and truth notes are multisets; TP = their intersection.

Variants:
  notes   the full tuple
  pitch   without duration (onset and pitch right)
  pc      pitch class instead of pitch, without duration (octave-insensitive: singer parts
          whose octave convention differs, treble vs treble-8vb)
  rhythm  without pitch (onset and duration right; the fair one for percussion)
  aligned the full tuple, but bars matched by the best monotonic alignment instead of by index:
          a missing or extra bar costs only its own notes, not every bar after it (reading quality
          without bar bookkeeping; for comparing readers without the pipeline's repairs)

Sounding pitch = written pitch + the part's <transpose> (chromatic, octave-change). Unpitched
(drum kit) notes are keyed by their staff position ("u:E4" = display step/octave = kit
instrument), so simultaneous hits stay apart. Slash noteheads have no pitch (None): they are
scored on rhythm only, and `fold_slashes` turns the output notes at a truth slash onset into one
rhythm-only note. Cue notes, grace notes and rests are left out.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction

from lxml import etree

_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
VARIANTS = ("notes", "pitch", "pc", "rhythm", "aligned")


def _num(el, path, default="0") -> Fraction:
    t = el.findtext(path)
    try:
        return Fraction(t.strip()) if t and t.strip() else Fraction(default)
    except ValueError:
        return Fraction(default)


def notes(part: etree._Element) -> list[tuple[int, int, Fraction, int | str | None, Fraction]]:
    """(bar index, staff, onset, sounding midi | "u:<step><octave>" | None, duration) of every
    sounding note (None = slash)."""
    out = []
    divisions = Fraction(1)
    shift = 0
    for mi, measure in enumerate(part.findall("measure")):
        cur = last = Fraction(0)
        if measure.find(".//instrument-change") is not None and measure.find("attributes/transpose") is None:
            shift = 0       # MuseScore writes <transpose> only for a non-zero interval
        for el in measure:
            if el.tag == "attributes":
                if el.findtext("divisions"):
                    divisions = _num(el, "divisions", "0") or divisions     # Audiveris writes <divisions>0
                tr = el.find("transpose")
                if tr is not None:
                    shift = int(_num(tr, "chromatic")) + 12 * int(_num(tr, "octave-change"))
            elif el.tag == "backup":
                cur -= _num(el, "duration") / divisions
            elif el.tag == "forward":
                cur += _num(el, "duration") / divisions
            elif el.tag == "note":
                chord = el.find("chord") is not None
                grace = el.find("grace") is not None
                dur = _num(el, "duration") / divisions
                onset = last if chord else cur
                if not chord and not grace:
                    last = cur
                    cur += dur
                if grace or el.find("rest") is not None or el.find("cue") is not None \
                        or (el.find("type") is not None and el.find("type").get("size") == "cue"):
                    continue
                p, u = el.find("pitch"), el.find("unpitched")
                midi = None
                if el.findtext("notehead", "").strip() == "slash":
                    pass
                elif p is not None:
                    midi = (_STEP.get(p.findtext("step", "C").strip(), 0) + int(_num(p, "alter"))
                            + 12 * (int(_num(p, "octave", "4")) + 1) + shift)
                elif u is not None:
                    midi = f"u:{u.findtext('display-step', '?').strip()}{u.findtext('display-octave', '?').strip()}"
                out.append((mi, int(el.findtext("staff") or 1), onset, midi, dur))
    return out


def _key(n, variant: str):
    bar, staff, onset, midi, dur = n
    if variant == "rhythm" or midi is None:
        return bar, staff, onset, dur if variant in ("notes", "rhythm") else None
    if variant == "notes":
        return bar, staff, onset, midi, dur
    if variant == "pitch":
        return bar, staff, onset, midi
    return bar, staff, onset, midi % 12 if isinstance(midi, int) else midi


def prf(tp: int, n_pred: int, n_truth: int) -> dict:
    p = tp / n_pred if n_pred else None
    r = tp / n_truth if n_truth else None
    f = 2 * tp / (n_pred + n_truth) if n_pred + n_truth else None
    return {"precision": p, "recall": r, "f1": f, "tp": tp, "pred": n_pred, "truth": n_truth}


def aligned(pred: list, truth: list) -> dict:
    """Note F1 with bars aligned by dynamic programming (max matched notes, order kept)."""
    def by_bar(ns):
        bars: dict[int, Counter] = {}
        for n in ns:
            bars.setdefault(n[0], Counter())[_key(n, "notes")[1:]] += 1
        return [bars.get(i, Counter()) for i in range(max(bars) + 1)] if bars else []
    a, b = by_bar(pred), by_bar(truth)
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(max(prev[j + 1], cur[j], prev[j] + (sum((ca & cb).values()) if ca and cb else 0)))
        prev = cur
    return prf(prev[-1], len(pred), len(truth))


def fold_slashes(pred: list, truth: list) -> list:
    """Output notes where the truth has slashes (same bar, staff, onset): one rhythm-only note per
    (bar, staff, onset, duration), since a slash only says "play here for this long"."""
    at = {n[:3] for n in truth if n[3] is None}
    if not at:
        return pred
    out = [n for n in pred if n[:3] not in at]
    return out + sorted({(*n[:3], None, n[4]) for n in pred if n[:3] in at})


def compare(pred: list, truth: list) -> dict:
    """{variant: prf} for two note lists (see `notes`)."""
    pred = fold_slashes(pred, truth)
    out = {"aligned": aligned(pred, truth)}
    for v in VARIANTS[:-1]:
        a = Counter(_key(n, v) for n in pred)
        b = Counter(_key(n, v) for n in truth)
        out[v] = prf(sum((a & b).values()), len(pred), len(truth))
    return out


def wrong_bars(pred: list, truth: list) -> list[int]:
    """1-based bar indices whose notes differ (full tuple)."""
    a: dict[int, Counter] = {}
    b: dict[int, Counter] = {}
    for n in pred:
        a.setdefault(n[0], Counter())[_key(n, "notes")] += 1
    for n in truth:
        b.setdefault(n[0], Counter())[_key(n, "notes")] += 1
    return [i + 1 for i in sorted(set(a) | set(b)) if a.get(i) != b.get(i)]
