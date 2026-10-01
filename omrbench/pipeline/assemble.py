"""Combine Audiveris layout/directions, homr staff-group transcriptions and printed text.

Per system:
1. bar count = vote between Audiveris and the homr crops of each staff group
2. per staff group and bar: homr if its bar count matches and the bar's voices fill
   the time signature, else Audiveris (and vice versa, order is configurable)
3. clef/key from the group's primary source, time signature from homr where printed
4. Audiveris dynamics/wedges/tempo and layout text are attached by bar and onset
5. multi-measure rests are expanded from printed bar ranges ("15-17"), counts printed
   above the rest, or homr <multiple-rest>
6. bars are lined up with the printed bar numbers and cut marks ("[to] 97"): missing
   bars (cuts, unread multi-rest counts) become rest bars, so bar n is printed bar n
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
from .layout import Page, System, where


@dataclass
class SysPlan:
    system: System
    index: int
    n: int = 0
    xs: list[tuple[float, float]] = field(default_factory=list)
    chosen: dict[int, list[B.Bar]] = field(default_factory=dict)      # group -> bars
    times: list[tuple[str, str] | None] = field(default_factory=list)
    labels: dict[tuple[int, int], str] = field(default_factory=dict)  # (group, bar) -> instrument
    pending: dict[tuple[int, int], str] = field(default_factory=dict) # "to Flute": from the next played bar
    cues: set[tuple[int, int]] = field(default_factory=set)           # (group, bar) cue notes removed
    printed: dict[int, int] = field(default_factory=dict)             # bar -> printed bar number
    jumps: dict[int, tuple[int, str]] = field(default_factory=dict)   # bar -> "[to] 97C" there
    lettered: dict[int, tuple[int, str]] = field(default_factory=dict) # bar -> printed "131A"
    mr: dict[int, tuple[str, int, int]] = field(default_factory=dict) # bar -> multi-rest evidence
    evidence: list[tuple[float, str, int, int]] = field(default_factory=list)  # x, kind, a, b
    aud: list[B.Bar] | None = None       # Audiveris bars of the system, if their count is n


@dataclass
class Stats:
    bars: Counter = field(default_factory=Counter)      # chosen source per staff-group bar
    systems: Counter = field(default_factory=Counter)   # how the bar count was decided
    multirest_bars_added: int = 0
    alignment_bars_added: int = 0
    homr_crops_failed: int = 0
    cue_notes_removed: int = 0
    words: int = 0
    notes: list[str] = field(default_factory=list)
    failed_crops: list = field(default_factory=list)   # (system, group, staves, image, reasons)
    homr_crops_expected: int = 0                         # of the failed: rests only, nothing to read

    def to_dict(self) -> dict:
        return {"bars": dict(self.bars), "systems": dict(self.systems),
                "multirest_bars_added": self.multirest_bars_added,
                "alignment_bars_added": self.alignment_bars_added,
                "homr_crops_failed": self.homr_crops_failed, "words": self.words,
                "cue_notes_removed": self.cue_notes_removed,
                "homr_crops_failed_rest_only": self.homr_crops_expected,
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


def group_bars(aud: dict, systems: list[System]) -> dict[tuple[int, int], list[B.Bar] | None]:
    """(system, group) -> Audiveris bars of that staff group. Regrouped systems take
    their staves out of the Audiveris parts (and join them if they span several)."""
    out: dict[tuple[int, int], list[B.Bar] | None] = {}
    for k, sy in enumerate(systems):
        for gi, g in enumerate(sy.groups()):
            if not sy.regrouped:
                out[(k, gi)] = aud.get((k, sy.alogical[gi]))
                continue
            srcs: list[tuple[list[B.Bar] | None, list[int]]] = []
            for st in g:
                bars = aud.get((k, sy.alogical[st.apart])) if st.apart < len(sy.alogical) else None
                if srcs and srcs[-1][0] is bars:
                    srcs[-1][1].append(st.pstaff)
                else:
                    srcs.append((bars, [st.pstaff]))
            if any(not b for b, _ in srcs) or len({len(b) for b, _ in srcs}) != 1:
                out[(k, gi)] = None
            elif len(srcs) == 1 and srcs[0][1] == list(range(1, srcs[0][0][0].staves + 1)):
                out[(k, gi)] = srcs[0][0]
            else:
                out[(k, gi)] = [B.restaff([(b[i], keep) for b, keep in srcs])
                                for i in range(len(srcs[0][0]))]
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
        if sy.skip:
            plans.append(plan)
            continue
        groups = sy.groups()
        a_bars = {gi: aud.get((k, gi)) for gi in range(len(groups))}
        a_n = max((len(v) for v in a_bars.values() if v), default=0) or None
        h_bars = {gi: homr.get((k, gi)) for gi in range(len(groups))}
        n, how = _vote(a_n, [len(v) for v in h_bars.values() if v])
        if n == 0 and sy.staves:
            # neither engine found a bar: a staff of multi-measure rests ("5" over "5-9").
            # One rest bar; expand_multirests / resegment_rest_systems count it out
            n, how = 1, "empty"
            for gi, group in enumerate(groups):
                bar = B.rest_bar(len(group), B.bar_length(cur_time, D), D)
                h_bars[gi] = [bar]
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
            hb = h_bars.get(gi) if h_bars.get(gi) and len(h_bars[gi]) == n else None
            ab = a_bars.get(gi) if a_bars.get(gi) and len(a_bars[gi]) == n else None
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
                    loose = [v for v in (h_bars.get(gi), a_bars.get(gi)) if v]
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
                    src = a_bars.get(gi)
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


def drop_cues(plans: list[SysPlan], pages: list[Page], D: int, stats: Stats) -> None:
    """Cue notes (small heads, Audiveris small-chord) become rests: they show what another
    instrument plays, the player doesn't play them. Bars with only cue chords on a staff
    lose all its notes; in mixed bars the chords are matched to note onsets by x order."""
    by_page = {p.number: p for p in pages}
    for plan in plans:
        if not plan.n or not plan.chosen:
            continue
        page = by_page.get(plan.system.page)
        if page is None:
            continue
        for gi, g in enumerate(plan.system.groups()):
            if gi not in plan.chosen:
                continue
            for si, st in enumerate(g, start=1):
                il = st.interline
                chords = [c for c in page.chords if c.staff == st.id
                          and c.x > st.header + 2.5 * il and (not c.small or c.grade >= 0.7)]
                for i in range(plan.n):
                    l, r = plan.xs[i]
                    here = sorted((c for c in chords if l <= c.x + c.w / 2 < r), key=lambda c: c.x)
                    normal = [c for c in here if not c.small]
                    # a small chord right before a normal one is a grace note, not a cue
                    small = [c for c in here if c.small and not any(
                        0 <= n.x - (c.x + c.w) <= 4 * il for n in normal)]
                    if not small:
                        continue
                    bar = plan.chosen[gi][i]
                    ons = sorted({on for on, el in B.onsets(bar) if el.tag == "note"
                                  and el.find("rest") is None and el.find("grace") is None
                                  and int(el.findtext("staff", "1") or 1) == si})
                    if not ons:
                        continue
                    if not normal:
                        # Audiveris may miss the real notes too (and read a rest as a
                        # small chord): the cue chords must account for the bar's notes
                        if len(small) != len(ons) and not (len(small) >= 2 and 2 * len(small) >= len(ons)):
                            continue
                        drop = set(ons)
                    else:
                        events: list[tuple[float, bool]] = []
                        for c in here:
                            if events and abs(c.x - events[-1][0]) < 0.8 * il:
                                continue    # same chord
                            events.append((c.x, c in small))
                        # only when every chord pairs with a note onset; a guess by x
                        # would turn played notes into rests
                        if len(events) != len(ons):
                            continue
                        drop = {on for on, (_, sm) in zip(ons, events) if sm}
                    removed = B.cues_to_rests(bar, si, drop)
                    if removed:
                        stats.cue_notes_removed += removed
                        plan.cues.add((gi, i))


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
    instruments = instruments_from(meta, credits, words) if split or meta.get("doubling") else []
    # without "(Vln)"-style aliases, parenthesized text is never an instrument label
    paren_aliases = any(a.startswith("(") for i in instruments for a in i["aliases"])
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
            if (gi, i) in plan.cues and text.startswith("("):
                continue            # "(Clar)": the label of cue notes that were removed
            on = _onset_at(plan, bar, i, pl.line.x, B.bar_length(plan.times[i], D)) \
                if estimate_onset else 0
            d = B.add_direction(bar, B.words_direction(text, "above" if pl.above else "below"),
                                on, staff_no)
            stats.words += 1
            name = match_instrument(text, instruments) if instruments else None
            if name and text.startswith("(") and not paren_aliases:
                name = None         # "(Clar)" names cue notes, "(still Oboe)" changes nothing
            if name and TO_LABEL.match(text):
                plan.pending[(gi, i)] = name
            elif name:
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
        for pl, n in pt.jumps:
            plan = by_sys.get(id(pl.system))
            if plan and plan.n:
                # "[to] 97" starts just left of the barline where bar 97 begins; at the
                # system end it names the first bar of the next system (index n)
                edges = [l for l, _ in plan.xs] + [plan.xs[-1][1]]
                i = min(range(len(edges)), key=lambda e: abs(edges[e] - pl.line.x))
                plan.jumps[i] = n
        for pl, n in pt.lettered:
            plan = by_sys.get(id(pl.system))
            if plan and plan.n:
                plan.lettered.setdefault(_bar_at(plan, pl.line.x + pl.line.h), n)
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
    for k, p in enumerate(plans):
        for i, (kind, a, _) in p.mr.items():
            if kind == "range":
                printed.setdefault((k, i), a)     # "15-17": that bar is bar 15
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
                if count > MAX_GAP:
                    # "149-1488": an OCR'd range that long is a misread, not a rest
                    stats.notes.append(f"system {k + 1}: range {a}-{b} ignored (over {MAX_GAP} bars)")
                    continue
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
        size = lambda j: known.get(glob[j], 1)
        if prev and nxt and not any(glob[j] in unknown for j in range(prev[0] + 1, nxt[0]) if j != pos):
            here = prev[1] + sum(size(j) for j in range(prev[0], pos))
            count = nxt[1] - here - sum(size(j) for j in range(pos + 1, nxt[0]))
            if 2 <= count <= 99:
                known[key] = count
                continue
            if count <= 1:
                stats.notes.append(f"system {key[0] + 1}: bar {key[1] + 1} not a multi-rest "
                                   f"(printed {prev[1]} and {nxt[1]} leave no room)")
                continue
        elif prev is None and nxt and not any(glob[j] in unknown for j in range(0, nxt[0]) if j != pos):
            # before the first printed number the piece is taken to start at bar 1: only to
            # veto a count (the empty stack before a start repeat is no 8-bar rest)
            here = 1 + sum(size(j) for j in range(0, pos))
            if nxt[1] - here - sum(size(j) for j in range(pos + 1, nxt[0])) <= 1:
                stats.notes.append(f"system {key[0] + 1}: bar {key[1] + 1} not a multi-rest "
                                   f"(printed {nxt[1]} follows too soon)")
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
            plan.lettered.pop(plan.n - 1, None)
            plan.n -= 1
            plan.jumps = {min(j, plan.n): v for j, v in plan.jumps.items()}
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
        plan.jumps = {(m if j >= plan.n else j): v for j, v in plan.jumps.items()}
        plan.lettered = {}
        plan.n = m
        plan.mr = {i: ("range", s["number"], s["number"] + s["count"] - 1) if s["kind"] == "range"
                   else ("count", s["count"], s["count"]) for i, s in enumerate(segs) if s["count"]}
        plan.printed = {i: s["number"] for i, s in enumerate(segs) if s["number"] is not None}


def _shift(d: dict, at: int, by: int, keyed_by_group: bool = False) -> dict:
    """Re-index a per-bar dict after `by` bars were inserted before bar `at`."""
    if keyed_by_group:
        return {(g, j + (by if j >= at else 0)): v for (g, j), v in d.items()}
    return {j + (by if j >= at else 0): v for j, v in d.items()}


def _shift_set(s: set, at: int, by: int) -> set:
    return {(g, j + (by if j >= at else 0)) for g, j in s}


def expand_multirests(plans: list[SysPlan], homr: dict, D: int, stats: Stats) -> None:
    drop_courtesy_bars(plans, stats)
    resegment_rest_systems(plans, D, stats)
    counts = _multirest_counts(plans, homr, stats)
    for plan in plans:
        # "15-17" over a rest: its first bar is printed bar 15
        for i, (kind, a, _) in plan.mr.items():
            if kind == "range" and i < plan.n:
                plan.printed.setdefault(i, a)
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
            plan.pending = {(g_, j + (count - 1 if j > i else 0)): v for (g_, j), v in plan.pending.items()}
            plan.printed = _shift(plan.printed, i + 1, count - 1)
            plan.jumps = _shift(plan.jumps, i + 1, count - 1)
            plan.lettered = _shift(plan.lettered, i + 1, count - 1)
            plan.cues = _shift_set(plan.cues, i + 1, count - 1)
            plan.n += count - 1
            stats.multirest_bars_added += count - 1


# ------------------------------------------------------------------------ bar numbers

MAX_GAP = 99            # longest multi-rest / cut taken from printed numbers
ALIGN_PENALTY = 1.2     # a gap must be backed by more than one printed bar number ...
JUMP_WEIGHT = 1.5       # ... or by a cut mark ("[to] 97"), which is explicit


@dataclass
class _Obs:
    j: int              # global bar index
    value: int          # position of that bar in the printed numbering (lettered bars count)
    weight: float
    kind: str           # number | jump
    label: str = ""     # as printed: "97", "131A"

    @property
    def offset(self) -> int:
        return self.value - (self.j + 1)


def _insert_rests(plan: SysPlan, i: int, count: int, D: int) -> None:
    """`count` rest bars before bar i of the plan (i == n: at its end)."""
    if not plan.n:
        return
    ref = min(i, plan.n - 1)
    time = plan.times[i - 1] if i > 0 else plan.times[0]
    length = B.bar_length(time, D)
    for gi, g in plan.chosen.items():
        staves = g[ref].staves
        g[i:i] = [B.rest_bar(staves, length, D) for _ in range(count)]
    plan.times[i:i] = [time] * count
    x = plan.xs[i][0] if i < plan.n else plan.xs[-1][1]
    plan.xs[i:i] = [(x, x)] * count
    plan.labels = _shift(plan.labels, i, count, keyed_by_group=True)
    plan.pending = _shift(plan.pending, i, count, keyed_by_group=True)
    plan.printed = _shift(plan.printed, i, count)
    plan.jumps = _shift(plan.jumps, i, count)
    plan.lettered = _shift(plan.lettered, i, count)
    plan.cues = _shift_set(plan.cues, i, count)
    plan.n += count


def _drop_bar(plans: list[SysPlan], k: int, i: int) -> None:
    """Remove bar i of plan k; its directions (tempo, text) move to the next bar."""
    plan = plans[k]
    nxt = (k, i + 1) if i + 1 < plan.n else next(((kk, 0) for kk in range(k + 1, len(plans))
                                                   if plans[kk].n), None)
    for gi, g in plan.chosen.items():
        dirs = [e for e in g[i].items if e.tag == "direction"]
        if dirs and nxt is not None and gi in plans[nxt[0]].chosen:
            plans[nxt[0]].chosen[gi][nxt[1]].items[0:0] = dirs   # index before the delete
        del g[i]
    del plan.times[i]
    del plan.xs[i]
    for attr in ("labels", "pending"):
        d = getattr(plan, attr)
        setattr(plan, attr, _shift({kk: v for kk, v in d.items() if kk[1] != i}, i + 1, -1,
                                   keyed_by_group=True))
    plan.printed = _shift({j: v for j, v in plan.printed.items() if j != i}, i + 1, -1)
    plan.jumps = _shift(plan.jumps, i + 1, -1)
    plan.lettered = _shift({j: v for j, v in plan.lettered.items() if j != i}, i + 1, -1)
    plan.cues = _shift_set({c for c in plan.cues if c[1] != i}, i + 1, -1)
    plan.n -= 1


def align_bars(plans: list[SysPlan], D: int, stats: Stats, log=None) -> None:
    """Insert rest bars so that bar n of the output is printed bar n.

    Evidence: printed bar numbers, the first number of printed ranges ("15-17"), and
    cut marks ("[to] 97": the bar there is bar 97, the bars before it were cut).
    Lettered bars ("131A", "[to] 132C") are bars added in a revision: each takes a
    position of its own, so all parts showing them line up. OCR
    misreads some numbers, so the offset (printed - position) is chosen as the
    non-decreasing step function that agrees with the most evidence; every step costs
    ALIGN_PENALTY, so one stray number never shifts the rest of the part. Bars are
    only added, never removed: evidence that the output is ahead is reported.
    """
    flat = [(k, i) for k, p in enumerate(plans) for i in range(p.n)]
    if not flat:
        return
    systems = [p.system for p in plans]
    start = {}
    pos = 0
    for k, p in enumerate(plans):
        start[k] = pos
        pos += p.n
    # lettered bars ("131A": added after 131) shift every later number by one; a cut to
    # "132C" means 132A and 132B exist (in other parts) and were cut here
    extra: set[tuple[int, str]] = set()
    for p in plans:
        for n, letter in list(p.lettered.values()) + list(p.jumps.values()):
            for c in range(ord("A"), ord(letter) + 1 if letter else ord("A")):
                extra.add((n, chr(c)))

    def position(n: int, letter: str = "") -> int:
        return n + sum(1 for m, _ in extra if m < n) + (ord(letter) - ord("A") + 1 if letter else 0)

    obs: list[_Obs] = []
    for k, p in enumerate(plans):
        for i, v in p.printed.items():
            if i < p.n and 0 < v <= 9999:
                obs.append(_Obs(start[k] + i, position(v), 1.0, "number", str(v)))
        for i, (n, letter) in p.lettered.items():
            if i < p.n and 0 < n <= 9999:
                obs.append(_Obs(start[k] + i, position(n, letter), 1.0, "number", f"{n}{letter}"))
        for i, (n, letter) in p.jumps.items():
            if start[k] + i < len(flat) and 0 < n <= 9999:
                obs.append(_Obs(start[k] + i, position(n, letter), JUMP_WEIGHT, "jump", f"{n}{letter}"))
    obs.sort(key=lambda o: (o.j, o.kind != "jump"))
    if not obs:
        return

    def at(j: int) -> str:
        k, i = flat[j]
        return f"{where(systems, k)} bar {i + 1}"

    # the step function: a chain of agreeing evidence; between links the offset may
    # change (each change costs ALIGN_PENALTY)
    score = [0.0] * len(obs)
    back: list[int | None] = [None] * len(obs)
    for t, o in enumerate(obs):
        # start at offset 0, or -1: a pickup bar before bar 1 (it stays the output's bar 1)
        best, arg = o.weight - (0.0 if o.offset in (0, -1) else ALIGN_PENALTY), None
        if abs(o.offset) > MAX_GAP:
            best = float("-inf")
        for u in range(t):
            q = obs[u]
            if q.j == o.j and q.offset != o.offset or abs(q.offset - o.offset) > MAX_GAP:
                continue
            cand = score[u] + o.weight - (ALIGN_PENALTY if q.offset != o.offset else 0.0)
            if cand > best:
                best, arg = cand, u
        score[t], back[t] = best, arg
    end = max(range(len(obs)), key=lambda t: score[t])
    chain: list[int] = []
    if score[end] > 0:
        t = end
        while t is not None:
            chain.append(t)
            t = back[t]
        chain.reverse()
    if chain and obs[chain[0]].offset < 0:
        # more bars before the first number than it allows: empty ones are no music (a
        # stack before a start repeat, a misread rest count); a pickup bar has notes
        n_extra = -obs[chain[0]].offset
        lead = flat[:n_extra]
        if len(lead) == n_extra and all(all(g[i].rest_only for g in plans[k].chosen.values())
                                      for k, i in lead):
            msg = (f"bar numbers: dropped {n_extra} empty bar(s) at {at(0)} before printed bar "
                   f"{obs[chain[0]].label} at {at(obs[chain[0]].j)}")
            stats.notes.append(msg)
            if log:
                log.warning(msg)
            for k, i in reversed(lead):
                _drop_bar(plans, k, i)
            return align_bars(plans, D, stats, log)
    # offset before the first anchor: 0, or -1 when bar 1 is preceded by a pickup bar
    base = -1 if chain and obs[chain[0]].offset == -1 else 0
    # numbers inside a step whose offsets lie between its two sides split it: the total
    # padding stays, part of it moves to where the evidence puts it (a cut mark whose
    # "[to]" OCR lost leaves only the number)
    refined: list[int] = []
    prev_off, prev_j = base, -1
    for t in chain + [None]:
        nxt_off = obs[t].offset if t is not None else None
        nxt_j = obs[t].j if t is not None else len(flat)
        if nxt_off is not None and nxt_off != prev_off:
            lo, hi = sorted((prev_off, nxt_off))
            up = nxt_off > prev_off
            mids = [u for u in range(len(obs)) if prev_j < obs[u].j < nxt_j
                    and lo < obs[u].offset < hi]
            # longest run of them that is monotone in the step's direction
            best: dict[int, list[int]] = {}
            for u in mids:
                cands = [best[v] for v in best if obs[v].j < obs[u].j and
                         (obs[v].offset <= obs[u].offset if up else obs[v].offset >= obs[u].offset)]
                best[u] = max(cands, key=len, default=[]) + [u]
            refined += max(best.values(), key=len, default=[])
        if t is not None:
            refined.append(t)
            prev_off, prev_j = nxt_off, nxt_j
    chain = refined
    on_chain = set(chain)

    steps = []          # (anchor obs, previous offset, previous anchor j)
    prev_off, prev_j = base, -1
    for t in chain:
        o = obs[t]
        if o.offset != prev_off:
            steps.append((o, prev_off, prev_j))
        prev_off, prev_j = o.offset, o.j

    def offset_at(j: int) -> int:
        off = base
        for t in chain:
            if obs[t].j <= j:
                off = obs[t].offset
        return off

    # numbers off the chain: the output bar there follows from the padding before it
    # (padding = the increases so far); report the ones that disagree
    def output_bar(j: int) -> int:
        pad = 0
        prev = base
        for t in chain:
            if obs[t].j > j:
                break
            if obs[t].offset > prev:
                pad += obs[t].offset - prev
            prev = obs[t].offset
        return j + 1 + pad

    rejected = 0
    for t, o in enumerate(obs):
        if t in on_chain or o.value == o.j + 1 + offset_at(o.j):
            continue
        what = "cut mark [to]" if o.kind == "jump" else "printed bar number"
        msg = (f"bar numbers: {what} {o.label} at {at(o.j)} ignored (output bar "
               f"{output_bar(o.j)}): not confirmed by the numbers around it (likely misread)")
        stats.notes.append(msg)
        rejected += 1
        if log and rejected <= 25:
            log.warning(msg)
    if log and rejected > 25:
        log.warning(f"bar numbers: {rejected - 25} more ignored numbers (see pipeline.json notes)")
    for o, before, pj in steps:
        if o.offset < before and o.label == "1":
            msg = (f"bar numbers: numbering restarts at 1 at {at(o.j)}: the next piece? "
                   "(check pages / skip_systems)")
            stats.notes.append(msg)
            if log:
                log.warning(msg)
        elif o.offset < before:
            # bars can only be added: from here on the output runs ahead
            ahead = output_bar(o.j) - o.value
            msg = (f"bar numbers: output is {ahead} bar(s) ahead from {at(o.j)} on (printed "
                   f"{o.label}, output bar {output_bar(o.j)}): {before - o.offset} extra bar(s) "
                   f"read since {at(pj) if pj >= 0 else 'the start'}; bars kept")
            stats.notes.append(msg)
            if log:
                log.warning(msg)

    rest_only = {j: all(g[i].rest_only for g in plans[k].chosen.values()) if plans[k].chosen else False
                 for j, (k, i) in enumerate(flat)}
    inserts = []        # (global position: insert before this bar, count, why)
    for o, before, pj in steps:
        d = o.offset - before
        if d <= 0:
            continue
        if o.kind == "jump":
            inserts.append((o.j, d, f"cut mark [to] {o.label}"))
            continue
        # no cut mark: most likely a rest whose count was not read; extend the last rest
        # bar before the number, else put the bars right before it
        rests = [j for j in range(max(pj, 0), o.j) if rest_only[j]]
        if rests:
            inserts.append((rests[-1] + 1, d, f"after the rest at {at(rests[-1])}, printed bar "
                                             f"number {o.label} at {at(o.j)}"))
        else:
            inserts.append((o.j, d, f"printed bar number {o.label}"))
    for j, d, why in sorted(inserts, key=lambda x: -x[0]):
        if j < len(flat):
            k, i = flat[j]
        else:
            k, i = flat[-1][0], plans[flat[-1][0]].n
        if i == 0 and j > 0:
            # between systems: at the end of the previous one (where the cut is printed)
            k, i = flat[j - 1][0], flat[j - 1][1] + 1
        _insert_rests(plans[k], i, d, D)
        stats.alignment_bars_added += d
        msg = f"bar numbers: {d} rest bar(s) inserted before {at(min(j, len(flat) - 1))} ({why})"
        stats.notes.append(msg)
        if log:
            log.info(msg)


# ----------------------------------------------------------------------------- parts

TEMPO_TERMS = re.compile(
    r"\b(rall|rit|ritard|riten|accel|tempo|poco|mosso|meno|pi[uù]|attacca|segue|maestoso|"
    r"lento|largo|adagio|andante|moderato|allegro|allegretto|presto|vivace|rubato|"
    r"fermata|colla|freely|slowly|broadly|tacet|cresc|dim|decresc|morendo|dolce)\b", re.I)
TO_LABEL = re.compile(r"^\W*to\s", re.I)     # "to Flute - fast", "[to Drum Set]"
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
                out.append({**it, "aliases": list(it.get("aliases") or [])})
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


CLEF_CLASS = {"percussion": "perc", "perc": "perc", "pitched": "pitched", "treble": "pitched",
              "bass": "pitched"}


def _clef_class(bar: B.Bar) -> str:
    sign = (bar.clefs.get(1) or ("", "", ""))[0]
    return "perc" if sign == "percussion" else ("pitched" if sign else "")


TRANSPOSE_KEYS = {"C": (0, 0), "B": (-1, -1), "Bb": (-1, -2), "A": (-2, -3), "Ab": (-2, -4),
                  "G": (-3, -5), "F#": (-3, -6), "F": (-4, -7), "E": (-5, -8), "Eb": (-5, -9),
                  "D": (-6, -10), "Db": (-6, -11)}


def parse_transpose(spec) -> tuple[int, int, int]:
    """(diatonic, chromatic, octave-change) from written to sounding pitch.

    "Bb" / "F" / "Eb" / "A": the key's pitch below written C (clarinet, horn, alto sax, ...);
    "8va" / "8vb" add an octave ("Bb 8vb" tenor sax, "8vb" double bass, "8va" piccolo);
    or a dict {diatonic, chromatic, octave_change}.
    """
    if not spec:
        return 0, 0, 0
    if isinstance(spec, dict):
        return (int(spec.get("diatonic", 0)), int(spec.get("chromatic", 0)),
                int(spec.get("octave_change", spec.get("octave-change", 0))))
    d = c = o = 0
    for tok in str(spec).replace("♭", "b").replace("♯", "#").split():
        t = tok.lower()
        if t in ("8va", "8ve"):
            o += 1
        elif t == "8vb":
            o -= 1
        elif t == "15mb":
            o -= 2
        elif t == "15ma":
            o += 2
        else:
            key = next((k for k in TRANSPOSE_KEYS if k.lower() == t), None)
            if key is None:
                raise ValueError(f"transpose: unknown '{tok}' (use e.g. Bb, F, Eb, \"Bb 8vb\", 8vb)")
            d, c = TRANSPOSE_KEYS[key]
    return d, c, o


@dataclass
class OutPart:
    name: str
    staves: int
    bars: list[B.Bar | None]
    changes: dict[int, dict] = field(default_factory=dict)   # bar -> instrument (name, transpose)


def build_parts(plans: list[SysPlan], split: bool, instruments: list[dict],
                part_names: dict[int, str], doubling: bool = False,
                transpose=None) -> tuple[list[OutPart], list]:
    """Tracks (output track id per staff group) -> parts.

    split: single-staff tracks are cut into one part per instrument; doubling: they stay
    one part that changes instrument. The instrument of a bar: a printed label there;
    else a pending "to X" once the track plays again; else, if the clef class changes
    (percussion <-> pitched): with `clef:` given in the instruments, the one that played
    most bars of that class on this track (the main instrument), else the next unused
    one; else the current one.
    A lower track that never had one starts with the `lower_staff` instrument.
    """
    total = sum(p.n for p in plans)
    times: list = []
    for p in plans:
        times += p.times
    switching = (split or doubling) and bool(instruments)
    tracks: dict[int, list[B.Bar | None]] = {}
    staves: dict[int, int] = {}
    owner: dict[int, list[str | None]] = {}
    pos = 0
    cur: dict[int, str | None] = {}
    pend: dict[int, str] = {}
    klass: dict[str, str] = {x["name"]: CLEF_CLASS[str(x["clef"]).lower()]
                             for x in instruments if x.get("clef")}
    declared = bool(klass)
    track_cls: dict[int, str] = {}   # clef class of the track's last bar
    used: list[str] = []             # first-use order
    played: Counter = Counter()      # (track, instrument) -> bars with notes
    lower = next((x["name"] for x in instruments if x.get("lower_staff")), None)

    def unused(cls: str | None = None) -> str | None:
        return next((x["name"] for x in instruments if x["name"] not in used
                     and (cls is None or klass.get(x["name"], cls) == cls)), None)

    for p in plans:
        for gi, g in enumerate(p.system.groups()):
            if gi not in p.chosen:
                continue
            L = p.system.logical[gi]
            tracks.setdefault(L, [None] * total)
            owner.setdefault(L, [None] * total)
            staves[L] = max(staves.get(L, 1), len(g))
            for i, bar in enumerate(p.chosen[gi]):
                tracks[L][pos + i] = bar
                if not (switching and len(g) == 1):
                    continue
                cls = _clef_class(bar)
                label = p.labels.get((gi, i))
                if label:
                    cur[L] = label
                    pend.pop(L, None)
                elif pend.get(L) and not bar.rest_only:
                    cur[L] = pend.pop(L)
                elif cls and track_cls.get(L) and cls != track_cls[L] and cur.get(L):
                    back = max((n for (t, n) in played if t == L and klass.get(n) == cls),
                               key=lambda n: played[(L, n)], default=None)
                    cur[L] = ((back or unused(cls)) if declared else unused()) or cur[L]
                if cur.get(L) is None:
                    cur[L] = (lower if L > 1 else None) or unused() or instruments[0]["name"]
                if (gi, i) in p.pending:
                    pend[L] = p.pending[(gi, i)]
                name = cur[L]
                owner[L][pos + i] = name
                if name not in used:
                    used.append(name)
                if not bar.rest_only:
                    played[(L, name)] += 1
                    if cls:
                        klass.setdefault(name, cls)
                if cls:
                    track_cls[L] = cls
        pos += p.n
    ins = {x["name"]: x for x in instruments}
    parts: list[OutPart] = []
    if not split:
        for L in sorted(tracks):
            part = OutPart(part_names.get(L, f"Part {L}"), staves[L], tracks[L])
            if switching and any(owner[L]):
                prev = None
                for g, name in enumerate(owner[L]):
                    if name and name != prev:
                        part.changes[g] = ins[name]
                        prev = name
            elif transpose:
                part.changes[0] = {"transpose": transpose}
            parts.append(part)
        return parts, times
    by_name: dict[str, OutPart] = {}
    order = [i["name"] for i in instruments if i["name"] in used]
    for name in order:
        by_name[name] = OutPart(name, 1, [None] * total, {0: ins[name]})
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
        state_tr = (0, 0, 0)
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
            if g in p.changes:
                tr = parse_transpose(p.changes[g].get("transpose"))
                if tr != state_tr:
                    t_el = etree.SubElement(a, "transpose")
                    etree.SubElement(t_el, "diatonic").text = str(tr[0])
                    etree.SubElement(t_el, "chromatic").text = str(tr[1])
                    if tr[2]:
                        etree.SubElement(t_el, "octave-change").text = str(tr[2])
                    state_tr = tr
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
