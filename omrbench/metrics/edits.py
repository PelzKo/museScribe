"""Hand-edit penalty: how many MuseScore actions turn an output part into its truth part.

The headline benchmark number (lower is better). Cost model (user decisions, 2026-10-13); every
action costs 1:

  notes      a note is (staff, onset, sounding pitch, duration); per matched bar the unmatched
             output and truth notes pair up as changes (retype pitch and/or duration = 1), the
             rest are inserts / deletes: cost = max(unmatched output, unmatched truth). Rests are
             free (they follow from the notes). Slash noteheads: rhythm only; drums: staff position.
  elements   per category and bar: exact (staff, onset, token) matches are free, the rest costs
             max(unmatched output, unmatched truth): a move to another beat, p -> f, a made-up
             fermata are one action each. Clef / key / time count only where they change.
  bars       bars are aligned by dynamic programming: deleting an extra output bar = 1 (its
             contents go with it), inserting a missing bar = 1 + everything in it.
  shift      a whole part off by an octave or a transposition = 1 bulk action (select all,
             transpose), then scored after the shift.
  system     rehearsal marks, tempi and system text (rit., a tempo: <words system="only-top"> in
             the truth) are entered once per score: `system_penalty` scores them per song (union of
             all output parts), not per part; output words equal to a truth system text go there too.

`from_scratch` = the penalty of an empty output: add the instrument (1) + type in everything (the
bars exist, they are score-wide), so penalty / from_scratch is the share of the hand work left.
"""
from __future__ import annotations

from collections import Counter

from lxml import etree

from ..musicxml import Staff, part_staves
from . import notef1

SYSTEM_CATS = ("rehearsal", "tempo", "systemtext")
PART_CATS = ("clefs", "keys", "times", "dynamics", "hairpins", "articulations", "fermatas", "slurs",
             "ties", "tuplets", "tremolos", "lyrics", "words", "chords", "instruments", "structure",
             "barlines")
_CHANGES_ONLY = ("clefs", "keys", "times")
BAND = 40                 # DP band around the diagonal (+ the bar count difference)

Bar = tuple[Counter, Counter]   # notes (staff, onset, pitch, dur), items (cat, staff, onset, token)


def part_bars(parts: list[etree._Element], system_words: frozenset = frozenset()) -> list[Bar]:
    """Bars of one or more output parts compared with one truth part (split instruments: the
    parts are overlaid by bar index; a switch of the part that plays counts as an instrument
    change)."""
    nbars = max((len(p.findall("measure")) for p in parts), default=0)
    bars: list[Bar] = [(Counter(), Counter()) for _ in range(nbars)]
    playing = [None] * nbars
    for k, part in enumerate(parts):
        for b, staff, onset, pitch, dur in notef1.notes(part):
            bars[b][0][(staff, onset, pitch, dur)] += 1
            playing[b] = k if playing[b] is None else playing[b]
        _add_items(bars, part_staves(part), system_words)
    if len(parts) > 1:
        last = None
        for b, k in enumerate(playing):
            if k is not None:
                if last is not None and k != last:
                    bars[b][1][("instruments", 1, 0, "ic")] += 1
                last = k
    _changes_only(bars)
    return bars


def _add_items(bars: list[Bar], staves: list[Staff], system_words: frozenset) -> None:
    for s in staves:
        for cat in PART_CATS:
            for mi, onset, tok in s.events[cat]:
                if not (cat == "words" and tok in system_words):
                    bars[mi][1][(cat, s.staff_no, onset, tok)] += 1


def _changes_only(bars: list[Bar]) -> None:
    """Drop clef / key / time tokens that restate the current one (also duplicates of overlaid parts)."""
    prev: dict = {}
    for _, items in bars:
        for it in sorted(k for k in items if k[0] in _CHANGES_ONLY):
            cat, staff, _, tok = it
            if prev.get((cat, staff)) == tok:
                del items[it]
            else:
                items[it] = 1
                prev[(cat, staff)] = tok


def _shifted(bars: list[Bar], s: int) -> list[Bar]:
    return [(Counter({(st, o, p + s if isinstance(p, int) else p, d): c for (st, o, p, d), c in n.items()}), i)
            for n, i in bars]


def _notes_cost(p: Counter, t: Counter) -> int:
    slash = {(st, o) for st, o, pitch, _ in t if pitch is None}
    if slash:
        folded = Counter()
        for (st, o, pitch, d), c in p.items():
            if (st, o) in slash:
                folded[(st, o, None, d)] = 1
            else:
                folded[(st, o, pitch, d)] += c
        p = folded
    return max(sum((p - t).values()), sum((t - p).values()))


def _items_cost(p: Counter, t: Counter, detail: Counter | None = None) -> int:
    """Per category max(unmatched output, unmatched truth): a moved, changed, missing or made-up
    element is one action each."""
    if p == t:
        return 0
    pc = Counter(k[0] for k in (p - t).elements())
    tc = Counter(k[0] for k in (t - p).elements())
    total = 0
    for cat in pc.keys() | tc.keys():
        cost = max(pc[cat], tc[cat])
        if detail is not None:
            detail[cat] += cost
        total += cost
    return total


def _bar_cost(p: Bar, t: Bar, detail: Counter | None = None) -> int:
    n = _notes_cost(p[0], t[0])
    if detail is not None:
        detail["notes"] += n
    return n + _items_cost(p[1], t[1], detail)


_EMPTY: Bar = (Counter(), Counter())


def _align(pred: list[Bar], truth: list[Bar]) -> tuple[int, list[tuple[int | None, int | None]]]:
    """Minimum total cost and the bar path [(pred index | None, truth index | None)]."""
    n, m = len(pred), len(truth)
    ins = [1 + _bar_cost(_EMPTY, t) for t in truth]
    w = BAND + abs(n - m)
    inf = float("inf")
    D = [[inf] * (m + 1) for _ in range(n + 1)]
    D[0][0] = 0
    for j in range(1, m + 1):
        D[0][j] = D[0][j - 1] + ins[j - 1]
    for i in range(1, n + 1):
        lo, hi = max(0, i - w), min(m, i + w)
        if lo == 0:
            D[i][0] = i
        for j in range(max(1, lo), hi + 1):
            best = D[i - 1][j] + 1
            if D[i][j - 1] + ins[j - 1] < best:
                best = D[i][j - 1] + ins[j - 1]
            if D[i - 1][j - 1] < best:
                c = D[i - 1][j - 1] + _bar_cost(pred[i - 1], truth[j - 1])
                if c < best:
                    best = c
            D[i][j] = best
    path = []
    i, j = n, m
    while i or j:
        if i and j and D[i][j] == D[i - 1][j - 1] + _bar_cost(pred[i - 1], truth[j - 1]):
            path.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and D[i][j] == D[i - 1][j] + 1:
            path.append((i - 1, None))
            i -= 1
        else:
            path.append((None, j - 1))
            j -= 1
    return int(D[n][m]), path[::-1]


def _best_shift(pred: list[Bar], truth: list[Bar]) -> int:
    """The non-zero semitone shift that lines up most (onset, duration, pitch) of the part."""
    def keys(bars, s=0):
        return Counter((o, d, p + s) for n, _ in bars for (_, o, p, d), c in n.items()
                       for _ in range(c) if isinstance(p, int))
    t = keys(truth)
    if not t:
        return 0
    score = {s: sum((keys(pred, s) & t).values()) for s in range(-24, 25)}
    s = max((s for s in score if s), key=lambda s: (score[s], -abs(s)))
    return s if score[s] > score[0] else 0


def system_words(truth_root: etree._Element) -> frozenset:
    """The truth's system text tokens (output words equal to one are scored per song)."""
    from ..musicxml import extract_staves
    return frozenset(t for s in extract_staves(truth_root) for _, _, t in s.events["systemtext"])


def penalty(pred_parts: list[etree._Element], truth_part: etree._Element,
            sys_words: frozenset = frozenset()) -> dict:
    """Edit penalty of output part(s) against one truth part (see the module doc)."""
    pred, truth = part_bars(pred_parts, sys_words), part_bars([truth_part])
    # bars are score-wide in MuseScore: a part with nothing read = add the instrument (1) + its contents
    scratch = 1 + sum(_bar_cost(_EMPTY, t) for t in truth)
    if not any(n or i for n, i in pred):
        detail = Counter(part=1)
        for t in truth:
            _bar_cost(_EMPTY, t, detail)
        return {"penalty": scratch, "from_scratch": scratch, "ratio": 1.0, "bars_insert": 0,
                "bars_delete": 0, "bars_changed": sum(1 for t in truth if t != _EMPTY), "bars_to_fix":
                sum(1 for t in truth if t != _EMPTY), "bars_truth": len(truth), "shift": 0, "by_cat": dict(+detail)}
    cost, path = _align(pred, truth)
    shift = 0
    s = _best_shift(pred, truth)
    if s:
        sp = _shifted(pred, s)
        c2, p2 = _align(sp, truth)
        if c2 + 1 < cost:
            cost, path, pred, shift = c2 + 1, p2, sp, s
    detail: Counter = Counter()
    ins = dele = changed = 0
    for i, j in path:
        if i is None:
            ins += 1
            detail["bars"] += 1
            _bar_cost(_EMPTY, truth[j], detail)
        elif j is None:
            dele += 1
            detail["bars"] += 1
        elif _bar_cost(pred[i], truth[j], detail):
            changed += 1
    if shift:
        detail["shift"] += 1
    assert sum(detail.values()) == cost, (dict(detail), cost)
    return {"penalty": cost, "from_scratch": scratch, "ratio": cost / scratch if scratch else None,
            "bars_insert": ins, "bars_delete": dele, "bars_changed": changed,
            "bars_to_fix": ins + dele + changed, "bars_truth": len(truth), "shift": shift,
            "by_cat": dict(+detail)}


# --------------------------------------------------------------------------- system items

def _system_items(staves: list[Staff], cluster: int = 0, words: frozenset = frozenset()) -> Counter:
    """(cat, bar, token) of rehearsal marks, tempi and system text (plus <words> in `words`);
    with `cluster`, the same token within `cluster` bars (read in several parts, bars slightly off)
    counts once."""
    seen: dict[tuple, list[int]] = {}
    for s in staves:
        for cat in SYSTEM_CATS:
            for mi, _, tok in s.events[cat]:
                seen.setdefault((cat, tok), []).append(mi)
        for mi, _, tok in s.events["words"]:
            if tok in words:
                seen.setdefault(("systemtext", tok), []).append(mi)
    out = Counter()
    for (cat, tok), bars in seen.items():
        start = None
        for b in sorted(set(bars)):
            if start is None or b - start > cluster:
                out[(cat, b, tok)] = 1
                start = b
    return out


def system_penalty(pred_roots: list[etree._Element], truth_root: etree._Element) -> dict:
    """Rehearsal marks, tempi and system text of a song: entered once per score, so compared once
    per song."""
    from ..musicxml import extract_staves
    t_staves = extract_staves(truth_root)
    sw = frozenset(t for s in t_staves for _, _, t in s.events["systemtext"])
    p = _system_items([s for r in pred_roots for s in extract_staves(r)], cluster=2, words=sw)
    t = _system_items(t_staves)
    detail = Counter({cat: max(sum(1 for k in p - t if k[0] == cat), sum(1 for k in t - p if k[0] == cat))
                      for cat in SYSTEM_CATS})
    detail = +detail
    return {"penalty": sum(detail.values()), "from_scratch": len(t), "by_cat": dict(detail)}
