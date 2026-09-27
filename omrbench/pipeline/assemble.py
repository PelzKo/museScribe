"""Combine Audiveris layout/directions, homr staff-group transcriptions and printed text.

Per system:
1. bar count = vote between Audiveris and the homr crops of each staff group
2. per staff group and bar: homr if its bar count matches and the bar's voices fill
   the time signature, else Audiveris (and vice versa, order is configurable)
3. clef/key from the group's primary source, time signature from homr where printed
4. Audiveris dynamics/wedges/tempo and layout text are attached by bar and onset
5. multi-measure rests are expanded from printed bar ranges ("15-17"), counts printed
   above the rest, or homr <multiple-rest>
Then staff tracks become parts; percussion tracks are split by instrument labels.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass, field

from lxml import etree

from . import bars as B
from . import text as T
from .layout import Page, System


@dataclass
class SysPlan:
    system: System
    index: int
    n: int = 0
    xs: list[tuple[float, float]] = field(default_factory=list)
    chosen: dict[int, list[B.Bar]] = field(default_factory=dict)      # group -> bars
    times: list[tuple[str, str] | None] = field(default_factory=list)
    labels: dict[tuple[int, int], str] = field(default_factory=dict)  # (group, bar) -> instrument
    printed: dict[int, int] = field(default_factory=dict)             # bar -> printed bar number
    mr: dict[int, tuple[str, int, int]] = field(default_factory=dict) # bar -> multi-rest evidence
    evidence: list[tuple[float, str, int, int]] = field(default_factory=list)  # x, kind, a, b
    aud: list[B.Bar] | None = None       # Audiveris bars of the system, if their count is n


@dataclass
class Stats:
    bars: Counter = field(default_factory=Counter)      # chosen source per staff-group bar
    systems: Counter = field(default_factory=Counter)   # how the bar count was decided
    multirest_bars_added: int = 0
    homr_crops_failed: int = 0
    words: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"bars": dict(self.bars), "systems": dict(self.systems),
                "multirest_bars_added": self.multirest_bars_added,
                "homr_crops_failed": self.homr_crops_failed, "words": self.words,
                "notes": self.notes}


def _split_systems(part: etree._Element) -> list[int]:
    counts, cur = [], 0
    for m in part.findall("measure"):
        pr = m.find("print")
        if pr is not None and (pr.get("new-system") == "yes" or pr.get("new-page") == "yes") and cur:
            counts.append(cur)
            cur = 0
        cur += 1
    if cur:
        counts.append(cur)
    return counts


def audiveris_bars(books: list[etree._Element], systems: list[System], D: int
                   ) -> dict[tuple[int, int], list[B.Bar]]:
    """(global system index, logical part id) -> Audiveris bars of that system."""
    out: dict[tuple[int, int], list[B.Bar]] = {}
    for bi, root in enumerate(books):
        idx = [k for k, sy in enumerate(systems) if sy.book == bi and sy.stacks]
        parts = root.findall("part")
        if not parts or not idx:
            continue
        counts = _split_systems(parts[0])
        if len(counts) != len(idx):
            counts = [len(systems[k].stacks) for k in idx]
        for pi, part in enumerate(parts):
            bs = B.part_bars(part, D, "audiveris")
            pos = 0
            for k, c in zip(idx, counts):
                out[(k, pi + 1)] = bs[pos:pos + c]
                pos += c
    return out


def _vote(a: int | None, homr_counts: list[int]) -> tuple[int, str]:
    votes = Counter(homr_counts)
    if a:
        votes[a] += 1
    if not votes:
        return 0, "none"
    best = max(votes.items(), key=lambda kv: (kv[1], kv[0] in homr_counts, kv[0]))[0]
    how = "agree" if len(votes) == 1 else ("homr" if best in homr_counts and best != a else "audiveris")
    return best, how


def _bar_at(plan: SysPlan, x: float) -> int:
    for i, (l, r) in enumerate(plan.xs):
        if x < r:
            return i
    return max(plan.n - 1, 0)


def _onset_at(plan: SysPlan, bar: B.Bar, i: int, x: float, length: int | None) -> int:
    l, r = plan.xs[i]
    if not length or r <= l:
        return 0
    raw = max(0.0, min(1.0, (x - l) / (r - l))) * length
    ons = sorted({o for o, el in B.onsets(bar) if el.tag == "note"})
    if not ons:
        return 0
    return min(ons, key=lambda o: abs(o - raw))


def plan_systems(pages: list[Page], aud: dict, homr: dict, D: int, prefer: list[str],
                 stats: Stats) -> list[SysPlan]:
    systems = [sy for p in pages for sy in p.systems]
    plans: list[SysPlan] = []
    cur_time = None
    for k, sy in enumerate(systems):
        plan = SysPlan(sy, k)
        groups = sy.groups()
        a_bars = {L: aud.get((k, L)) for L in sy.logical}
        a_n = max((len(v) for v in a_bars.values() if v), default=0) or None
        h_bars = {gi: homr.get((k, gi)) for gi in range(len(groups))}
        n, how = _vote(a_n, [len(v) for v in h_bars.values() if v])
        stats.systems[how] += 1
        plan.n = n
        if n == 0:
            plans.append(plan)
            continue
        # x-range per bar: Audiveris stacks if they match, else an even split
        if len(sy.stacks) == n:
            plan.xs = [(s.left, s.right) for s in sy.stacks]
        else:
            left = sy.stacks[0].left if sy.stacks else min(s.left for s in sy.staves)
            right = sy.stacks[-1].right if sy.stacks else max(s.right for s in sy.staves)
            w = (right - left) / n
            plan.xs = [(left + i * w, left + (i + 1) * w) for i in range(n)]
        # time signature per bar: homr where printed, else carried, else Audiveris
        h_src = next((v for v in h_bars.values() if v and len(v) == n), None)
        a_src = next((v for v in a_bars.values() if v and len(v) == n), None)
        plan.aud = a_src
        for i in range(n):
            t = h_src[i].time if h_src and h_src[i].time else None
            if t is None:
                t = cur_time or (a_src[i].time if a_src else None)
            plan.times.append(t)
            cur_time = t
        for gi, group in enumerate(groups):
            L = sy.logical[gi]
            hb = h_bars.get(gi) if h_bars.get(gi) and len(h_bars[gi]) == n else None
            ab = a_bars.get(L) if a_bars.get(L) and len(a_bars[L]) == n else None
            order = prefer
            if all(st.clef == "PERCUSSION_CLEF" for st in group):
                # homr reads percussion staves as pitched (often with a C clef)
                order = ["audiveris", "homr"]
                if hb:
                    hb = [B.to_unpitched(b) for b in hb]
            options = {"homr": hb, "audiveris": ab}
            primary = next((options[s] for s in order if options.get(s)), None)
            chosen = []
            for i in range(n):
                length = B.bar_length(plan.times[i], D)
                cands = [(s, options[s][i]) for s in order if options.get(s)]
                pick = next(((s, b) for s, b in cands if B.bar_ok(b, length)), None) \
                    or next(((s, b) for s, b in cands if not b.empty), None)
                if pick is None:
                    # neither source has this system's bar count: best effort by position
                    loose = [v for v in (h_bars.get(gi), a_bars.get(L)) if v]
                    src = next((v for v in loose if i < len(v)), None)
                    pick = ("fallback", src[i]) if src else ("rest", B.rest_bar(len(group), length, D))
                s, bar = pick
                stats.bars[s] += 1
                bar = copy.deepcopy(bar)
                bar.staves = max(bar.staves, len(group))
                if primary is not None:
                    bar.clefs = dict(primary[i].clefs) or bar.clefs
                    bar.key = primary[i].key if primary[i].key is not None else bar.key
                # Audiveris directions (dynamics, wedges, tempo) onto non-Audiveris bars
                if s != "audiveris" and a_n:
                    src = a_bars.get(L)
                    if src:
                        j = i if len(src) == n else min(len(src) - 1, round(i * len(src) / n))
                        for on, el in B.onsets(src[j]):
                            if el.tag == "direction":
                                st = el.findtext("staff")
                                B.add_direction(bar, el, on, int(st) if st and st.isdigit() else None)
                chosen.append(bar)
            plan.chosen[gi] = chosen
        plans.append(plan)
    return plans


def _group_of(sy: System, staff_id: int) -> tuple[int, int]:
    for gi, g in enumerate(sy.groups()):
        for si, st in enumerate(g):
            if st.id == staff_id:
                return gi, si + 1
    return 0, 1


def place_text(plans: list[SysPlan], pages: list[Page], D: int, stats: Stats,
               meta: dict, split: bool, estimate_onset: bool = False
               ) -> tuple[list[T.Line], list[dict]]:
    by_sys = {id(p.system): p for p in plans}
    classified = [T.classify(page) for page in pages]
    credits = [ln for pt in classified for ln in pt.credits]
    words = [pl.line.text for pt in classified for pl in pt.words]
    instruments = instruments_from(meta, credits, words) if split else []
    for pt in classified:
        for pl in pt.words:
            plan = by_sys.get(id(pl.system))
            if not plan or not plan.n:
                continue
            gi, staff_no = _group_of(pl.system, pl.staff.id)
            if gi not in plan.chosen:
                continue
            i = _bar_at(plan, pl.line.x + 1)
            bar = plan.chosen[gi][i]
            mm = re.search(r"[=♩]\s*(\d{2,3})\s*$", pl.line.text)
            if mm and not any(e.find("direction-type/metronome") is not None
                              for g in plan.chosen.values() for e in g[i].items):
                # "Maestoso ♩ = 92" where Audiveris found no metronome (unit assumed quarter)
                B.add_direction(bar, B.metronome_direction(mm.group(1)), 0, staff_no)
            text = T.clean_words(pl.line.text)
            if not T.is_words(text):
                continue
            on = _onset_at(plan, bar, i, pl.line.x, B.bar_length(plan.times[i], D)) \
                if estimate_onset else 0
            d = B.add_direction(bar, B.words_direction(text, "above" if pl.above else "below"),
                                on, staff_no)
            stats.words += 1
            name = match_instrument(text, instruments) if instruments else None
            if name:
                plan.labels[(gi, i)] = name
            elif split or (pl.above and pl.staff is min(pl.system.staves, key=lambda s: s.top)
                           and is_system_text(text)):
                d.set("system-text", "yes")   # moved to the top part when writing
        for pl, value in pt.rehearsals:
            plan = by_sys.get(id(pl.system))
            if not plan or not plan.n or 0 not in plan.chosen:
                continue
            i = _bar_at(plan, pl.line.x + 1)
            d = etree.Element("direction", placement="above")
            etree.SubElement(etree.SubElement(d, "direction-type"), "rehearsal").text = value
            B.add_direction(plan.chosen[0][i], d, 0, 1)
        for pl, n in pt.numbers:
            plan = by_sys.get(id(pl.system))
            if plan and plan.n and not pl.above:
                # bar numbers are printed below the start of their bar
                plan.printed.setdefault(_bar_at(plan, pl.line.x + pl.line.h), n)
        _multirest_evidence(pt, by_sys)
    return credits, instruments


def _multirest_evidence(pt: T.PageText, by_sys: dict) -> None:
    for pl, a, b in pt.ranges:
        plan = by_sys.get(id(pl.system))
        if plan:
            plan.evidence.append(((pl.line.x + pl.line.right) / 2, "range", a, b))
    for pl, n in pt.numbers:
        plan = by_sys.get(id(pl.system))
        if plan:
            kind = "count" if pl.above else "number"
            x = (pl.line.x + pl.line.right) / 2 if pl.above else pl.line.x
            plan.evidence.append((x, kind, n, n))
    for pl, a, b in pt.ranges:
        plan = by_sys.get(id(pl.system))
        if plan and plan.n:
            i = _bar_at(plan, (pl.line.x + pl.line.right) / 2)
            plan.mr[i] = ("range", a, b)
    for pl, n in pt.numbers:
        plan = by_sys.get(id(pl.system))
        if plan and plan.n and pl.above and 2 <= n <= 99:
            cx = (pl.line.x + pl.line.right) / 2
            i = _bar_at(plan, cx)
            l, r = plan.xs[i]
            if l + 0.2 * (r - l) <= cx <= r - 0.2 * (r - l):
                plan.mr.setdefault(i, ("count", n, n))


def _multirest_counts(plans: list[SysPlan], homr: dict, stats: Stats) -> dict[tuple[int, int], int]:
    """(system, bar) -> number of bars a multi-measure rest stands for.

    Evidence, strongest first: the count printed above the rest; a printed range
    ("15-17", checked against the next bar number); the gap in printed bar numbers
    around a bar that is a multi-rest (Audiveris MULTI_REST stack or homr
    <multiple-rest>, whose own counts are unreliable); homr's count if all its crops agree.
    """
    glob: list[tuple[int, int]] = [(k, i) for k, p in enumerate(plans) for i in range(p.n)]
    rest_only = {(k, i): all(g[i].rest_only for g in p.chosen.values()) if p.chosen else False
                 for k, p in enumerate(plans) for i in range(p.n)}
    printed = {(k, i): v for k, p in enumerate(plans) for i, v in p.printed.items()}
    known: dict[tuple[int, int], int] = {}
    unknown: set[tuple[int, int]] = set()
    homr_count: dict[tuple[int, int], int] = {}
    for k, p in enumerate(plans):
        for i, (kind, a, b) in p.mr.items():
            if not rest_only.get((k, i)):
                continue
            if kind == "count":
                known[(k, i)] = a
            elif (k, i) not in known:
                count = b - a + 1
                nxt = printed.get((k, i + 1)) or (printed.get((k + 1, 0)) if i + 1 >= p.n else None)
                if nxt is not None and a < nxt <= a + 99 and nxt - a != count:
                    stats.notes.append(f"system {k + 1}: range {a}-{b}, next bar number {nxt}"
                                       f" -> {nxt - a} bars")
                    count = nxt - a
                known[(k, i)] = count
        stacks_ok = len(p.system.stacks) == p.n
        for i in range(p.n):
            if not rest_only.get((k, i)) or (k, i) in known:
                continue
            counts = {hb[i].multirest for gi in range(len(p.system.groups()))
                      if (hb := homr.get((k, gi))) and len(hb) == p.n and hb[i].multirest > 1}
            flagged = stacks_ok and p.system.stacks[i].special == "MULTI_REST"
            if counts or flagged:
                unknown.add((k, i))
                if len(counts) == 1:
                    homr_count[(k, i)] = counts.pop()
    # bar-number gaps: number at the rest = previous printed + bars since; count = next - it
    for pos, key in enumerate(glob):
        if key not in unknown:
            continue
        prev = next(((j, printed[glob[j]]) for j in range(pos - 1, -1, -1) if glob[j] in printed), None)
        nxt = next(((j, printed[glob[j]]) for j in range(pos + 1, len(glob)) if glob[j] in printed), None)
        if prev and nxt and not any(glob[j] in unknown for j in range(prev[0] + 1, nxt[0]) if j != pos):
            size = lambda j: known.get(glob[j], 1)
            here = prev[1] + sum(size(j) for j in range(prev[0], pos))
            count = nxt[1] - here - sum(size(j) for j in range(pos + 1, nxt[0]))
            if 2 <= count <= 99:
                known[key] = count
                continue
        if key in homr_count:
            known[key] = homr_count[key]
    return known


def drop_courtesy_bars(plans: list[SysPlan], stats: Stats) -> None:
    """A tiny bar at the end of a system is a page-turn reminder ("3" over a short
    multi-rest, courtesy key signature), not a bar of its own."""
    for k, plan in enumerate(plans):
        if plan.n < 2 or len(plan.system.stacks) != plan.n or not plan.chosen:
            continue
        last_on_page = k + 1 == len(plans) or plans[k + 1].system.page != plan.system.page
        st = plan.system.stacks[-1]
        il = plan.system.staves[0].interline
        rests = all(g[-1].rest_only for g in plan.chosen.values()) or (
            plan.aud is not None and plan.aud[-1].rest_only)
        # both engines tend to read the courtesy key/rest glyphs there as notes, so on the
        # last system of a page the width alone decides
        if st.right - st.left < (6 if rests else 5) * il and (rests or last_on_page):
            for g in plan.chosen.values():
                g.pop()
            plan.times.pop()
            plan.xs.pop()
            plan.mr.pop(plan.n - 1, None)
            plan.printed.pop(plan.n - 1, None)
            plan.n -= 1
            stats.notes.append(f"system {k + 1}: dropped {(st.right - st.left) / il:.1f}-interline"
                               " rest bar at the system end")


def resegment_rest_systems(plans: list[SysPlan], D: int, stats: Stats) -> None:
    """Rebuild systems that hold only rests from the printed numbers.

    homr finds no noteheads on such staves and Audiveris often misses the barlines
    between multi-measure rests, so "14 | 3 over 15-17" comes out as one bar. The
    printed bar number, ranges and counts tell how many bars there are.
    """
    for k, plan in enumerate(plans):
        if not plan.n or not plan.chosen or not all(b.rest_only for g in plan.chosen.values() for b in g):
            continue
        ev = sorted(plan.evidence)
        if not ev:
            continue
        sy = plan.system
        width = (max(s.right for s in sy.staves) - min(s.left for s in sy.staves)) or 1
        segs: list[dict] = []          # one per printed bar: x, number, count
        for x, kind, a, b in ev:
            near = next((s for s in segs if abs(s["x"] - x) < 0.12 * width), None)
            if kind == "range":
                if near and (near.get("count") is None or near.get("kind") == "count"):
                    near.update(kind="range", number=a, count=b - a + 1, x=x)
                elif near and near.get("number") == a:
                    near.update(kind="range", count=b - a + 1)
                else:
                    segs.append({"x": x, "kind": "range", "number": a, "count": b - a + 1})
            elif kind == "count":
                if near and near["kind"] == "range":
                    continue
                segs.append({"x": x, "kind": "count", "number": None, "count": a})
            else:  # printed bar number at the start of a bar
                if any(s.get("number") == a for s in segs):
                    continue
                segs.append({"x": x, "kind": "number", "number": a, "count": None})
        segs.sort(key=lambda s: s["x"])
        if len(segs) <= plan.n:
            continue
        stats.notes.append(f"system {k + 1}: rest-only, {plan.n} -> {len(segs)} bars from printed numbers")
        m = len(segs)
        xs = [s["x"] for s in segs]
        bounds = [min(st.left for st in sy.staves)] + [(xs[i] + xs[i + 1]) / 2 for i in range(m - 1)] \
            + [max(st.right for st in sy.staves)]
        for gi, g in plan.chosen.items():
            proto = g[0]
            new = []
            for i in range(m):
                bar = B.rest_bar(proto.staves, B.bar_length(plan.times[0], D), D)
                bar.clefs, bar.key = proto.clefs, proto.key
                new.append(bar)
            new[0].items = [e for b in g for e in b.items if e.tag == "direction"] + new[0].items
            plan.chosen[gi] = new
        plan.times = [plan.times[0]] * m
        plan.xs = [(bounds[i], bounds[i + 1]) for i in range(m)]
        plan.n = m
        plan.mr = {i: ("range", s["number"], s["number"] + s["count"] - 1) if s["kind"] == "range"
                   else ("count", s["count"], s["count"]) for i, s in enumerate(segs) if s["count"]}
        plan.printed = {i: s["number"] for i, s in enumerate(segs) if s["number"] is not None}


def expand_multirests(plans: list[SysPlan], homr: dict, D: int, stats: Stats) -> None:
    drop_courtesy_bars(plans, stats)
    resegment_rest_systems(plans, D, stats)
    counts = _multirest_counts(plans, homr, stats)
    for k, plan in enumerate(plans):
        for i in sorted((i for (kk, i) in counts if kk == k), reverse=True):
            count = counts[(k, i)]
            if count <= 1:
                continue
            length = B.bar_length(plan.times[i], D)
            for gi, g in plan.chosen.items():
                first = B.rest_bar(g[i].staves, length, D)
                first.items = [e for e in g[i].items if e.tag == "direction"] + first.items
                first.clefs, first.key = g[i].clefs, g[i].key
                extra = [B.rest_bar(g[i].staves, length, D) for _ in range(count - 1)]
                g[i:i + 1] = [first] + extra
            plan.times[i:i + 1] = [plan.times[i]] * count
            plan.xs[i:i + 1] = [plan.xs[i]] * count
            plan.labels = {(g_, j + (count - 1 if j > i else 0)): v for (g_, j), v in plan.labels.items()}
            plan.n += count - 1
            stats.multirest_bars_added += count - 1


# ----------------------------------------------------------------------------- parts

TEMPO_TERMS = re.compile(
    r"\b(rall|rit|ritard|riten|accel|tempo|poco|mosso|meno|pi[uù]|attacca|segue|maestoso|"
    r"lento|largo|adagio|andante|moderato|allegro|allegretto|presto|vivace|rubato|"
    r"fermata|colla|freely|slowly|broadly|tacet|cresc|dim|decresc|morendo|dolce)\b", re.I)
STAFF_TERMS = re.compile(r"\b(loco|8va|8vb|15ma|pizz|arco|div|unis|solo|tutti|rh|lh|mute|"
                         r"senza|con|sord|ped|pedal)\b", re.I)


def is_system_text(text: str) -> bool:
    """Tempo / expression marks ("Maestoso", "poco rall.", "Regal, ghostly") apply to the
    whole system; labels, dialogue and playing instructions belong to their staff."""
    t = text.strip()
    if ":" in t or t.startswith(("(", "[")) or STAFF_TERMS.search(t):
        return False
    if TEMPO_TERMS.search(t):
        return True
    words = t.split()
    return len(words) <= 3 and not (len(words) > 1 and t[-1] in ".?!;,")


def _norm(s: str) -> list[str]:
    return [w for w in re.split(r"[^\w]+", s.lower()) if len(w) >= 3]


def match_instrument(text: str, instruments: list[dict]) -> str | None:
    words = _norm(text)
    if not words:
        return None
    for ins in instruments:
        for alias in [ins["name"], *ins.get("aliases", [])]:
            aw = _norm(alias)
            if alias.startswith("(") and alias.lower() in text.lower():
                return ins["name"]
            if aw and (words[:len(aw)] == aw or any(w in words for w in aw if len(w) >= 4)):
                return ins["name"]
    return None


def instruments_from(meta: dict, credits: list[T.Line], words: list[str]) -> list[dict]:
    spec = meta.get("instruments")
    if spec:
        out = []
        for it in spec:
            if isinstance(it, str):
                out.append({"name": it, "aliases": []})
            else:
                out.append({"name": it["name"], "aliases": list(it.get("aliases") or [])})
        return out
    # header lines listing the instruments ("Timpani", "Sus Cymbal", ...) that also
    # appear as a label inside the music
    out = []
    for ln in credits:
        cand = {"name": ln.text, "aliases": []}
        if T.is_words(ln.text) and len(ln.text) <= 30 and \
                any(match_instrument(w, [cand]) for w in words):
            out.append(cand)
    return out


def _clef_class(bar: B.Bar) -> str:
    sign = (bar.clefs.get(1) or ("", "", ""))[0]
    return "perc" if sign == "percussion" else ("pitched" if sign else "")


@dataclass
class OutPart:
    name: str
    staves: int
    bars: list[B.Bar | None]


def build_parts(plans: list[SysPlan], split: bool, instruments: list[dict],
                part_names: dict[int, str]) -> tuple[list[OutPart], list]:
    total = sum(p.n for p in plans)
    times: list = []
    for p in plans:
        times += p.times
    tracks: dict[int, list[B.Bar | None]] = {}
    staves: dict[int, int] = {}
    owner: dict[int, list[str | None]] = {}
    pos = 0
    cur: dict[int, str | None] = {}
    last_class: dict[int, str] = {}
    used: list[str] = []
    for p in plans:
        for gi, g in enumerate(p.system.groups()):
            if gi not in p.chosen:
                continue
            L = p.system.logical[gi]
            tracks.setdefault(L, [None] * total)
            owner.setdefault(L, [None] * total)
            staves[L] = max(staves.get(L, 1), len(g))
            cls = _clef_class(p.chosen[gi][0]) if p.chosen[gi] else ""
            if split and len(g) == 1:
                label0 = p.labels.get((gi, 0))
                if label0 is None and cls and last_class.get(L) and cls != last_class[L]:
                    nxt = next((i["name"] for i in instruments if i["name"] not in used), None)
                    if nxt:
                        cur[L] = nxt
                last_class[L] = cls or last_class.get(L, "")
            for i, bar in enumerate(p.chosen[gi]):
                tracks[L][pos + i] = bar
                if split and len(g) == 1:
                    if (gi, i) in p.labels:
                        cur[L] = p.labels[(gi, i)]
                    if cur.get(L) is None:
                        cur[L] = next((x["name"] for x in instruments if x["name"] not in used), None)
                    owner[L][pos + i] = cur[L]
                    if cur[L] and cur[L] not in used:
                        used.append(cur[L])
        pos += p.n
    parts: list[OutPart] = []
    if not split:
        for L in sorted(tracks):
            parts.append(OutPart(part_names.get(L, f"Part {L}"), staves[L], tracks[L]))
        return parts, times
    by_name: dict[str, OutPart] = {}
    order = [i["name"] for i in instruments if i["name"] in used]
    for name in order:
        by_name[name] = OutPart(name, 1, [None] * total)
    for L in sorted(tracks):
        if staves[L] > 1 or not any(owner[L]):
            by_name[f"__{L}"] = OutPart(part_names.get(L, f"Part {L}"), staves[L], tracks[L])
            continue
        for g, bar in enumerate(tracks[L]):
            if bar is not None and owner[L][g]:
                by_name[owner[L][g]].bars[g] = bar
    return list(by_name.values()), times


# ----------------------------------------------------------------------------- output

def _attr_clef(a, staff: int, clef: B.Clef, staves: int) -> None:
    c = etree.SubElement(a, "clef")
    if staves > 1:
        c.set("number", str(staff))
    etree.SubElement(c, "sign").text = clef[0]
    if clef[1]:
        etree.SubElement(c, "line").text = clef[1]
    if clef[2]:
        etree.SubElement(c, "clef-octave-change").text = clef[2]


def write_score(parts: list[OutPart], times: list, credits: list[T.Line], D: int) -> etree._Element:
    root = etree.Element("score-partwise", version="4.0")
    ident = etree.SubElement(root, "identification")
    etree.SubElement(etree.SubElement(ident, "encoding"), "software").text = "omrbench pipeline"
    for ln in sorted(credits, key=lambda l: (l.page, l.top, l.x)):
        cr = etree.SubElement(root, "credit", page=str(ln.page))
        etree.SubElement(cr, "credit-words").text = ln.text
    pl = etree.SubElement(root, "part-list")
    for k, p in enumerate(parts, start=1):
        sp = etree.SubElement(pl, "score-part", id=f"P{k}")
        etree.SubElement(sp, "part-name").text = p.name
    for p in parts:
        p.bars = [b if b is not None else B.rest_bar(p.staves, B.bar_length(times[g] if g < len(times)
                  else None, D), D) for g, b in enumerate(p.bars)]
    # parts not printed in a system still follow its key changes
    for g in range(len(times)):
        keys = [p.bars[g].key for p in parts if p.bars[g].source != "rest" and p.bars[g].key is not None]
        if keys:
            for p in parts:
                if p.bars[g].source == "rest" and p.bars[g].key is None:
                    p.bars[g].key = Counter(keys).most_common(1)[0][0]
    # system-wide text and tempo belong to the top part (as in a full score)
    for p in parts[1:]:
        for g, bar in enumerate(p.bars):
            for el in [e for e in bar.items if e.get("system-text") or
                       (e.tag == "direction" and e.find("direction-type/metronome") is not None)]:
                bar.items.remove(el)
                for st in el.findall("staff"):
                    el.remove(st)
                parts[0].bars[g].items.insert(0, el)
    for p in parts:
        for bar in p.bars:
            for el in bar.items:
                if "system-text" in el.attrib:
                    del el.attrib["system-text"]
                if el.tag == "direction" and p.staves > 1 and el.find("staff") is None:
                    etree.SubElement(el, "staff").text = "1"
    for k, p in enumerate(parts, start=1):
        part = etree.SubElement(root, "part", id=f"P{k}")
        state_key, state_time, state_clefs = None, None, {}
        first_clefs = next((b.clefs for b in p.bars if b is not None and b.clefs), {})
        for g, bar in enumerate(p.bars):
            t = times[g] if g < len(times) else None
            length = B.bar_length(t, D)
            if bar is None:
                bar = B.rest_bar(p.staves, length, D)
            m = etree.SubElement(part, "measure", number=str(g + 1))
            a = etree.Element("attributes")
            if g == 0:
                etree.SubElement(a, "divisions").text = str(D)
            key = bar.key if bar.key is not None else (state_key if g else "0")
            if key is not None and key != state_key:
                etree.SubElement(etree.SubElement(a, "key"), "fifths").text = key
                state_key = key
            if t and t != state_time:
                tm = etree.SubElement(a, "time")
                etree.SubElement(tm, "beats").text = t[0]
                etree.SubElement(tm, "beat-type").text = t[1]
                state_time = t
            if g == 0 and p.staves > 1:
                etree.SubElement(a, "staves").text = str(p.staves)
            clefs = bar.clefs or (first_clefs if g == 0 else {})
            if g == 0 and not clefs:
                clefs = {s: ("G", "2", "") for s in range(1, p.staves + 1)}
            for s in range(1, p.staves + 1):
                c = clefs.get(s)
                if c and c != state_clefs.get(s):
                    _attr_clef(a, s, c, p.staves)
                    state_clefs[s] = c
            if len(a):
                m.append(a)
            for el in bar.items:
                if p.staves == 1:
                    for st in el.findall("staff"):
                        el.remove(st)
                if el.tag == "attributes":
                    for c in el.findall("clef"):
                        state_clefs[int(c.get("number", "1"))] = B._clef(c)
                m.append(el)
    return root
