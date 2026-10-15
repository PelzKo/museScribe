"""Combine Audiveris layout/directions, crop-recognizer (homr by default) staff-group
transcriptions and printed text.

Per system:
1. bar count = vote between Audiveris and the crop readings of each staff group
2. per staff group and bar: the crop reading if its bar count matches and the bar's voices fill
   the time signature, else Audiveris (and vice versa, order is configurable)
3. clef/key from the group's primary source, time signature from the crops where printed
4. Audiveris dynamics/wedges/tempo and layout text are attached by bar and onset
5. multi-measure rests are expanded from printed bar ranges ("15-17"), counts printed
   above the rest, or the crops' <multiple-rest>
6. bars are lined up with the printed bar numbers and cut marks ("[to] 97"): missing
   bars (cuts, unread multi-rest counts) become rest bars, so bar n is printed bar n
Then staff tracks become parts; percussion tracks are split by instrument labels.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from fractions import Fraction
from dataclasses import dataclass, field

from lxml import etree

from . import bars as B
from . import chords as CH
from . import vector as SL
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
    beats: dict[tuple[int, int], list[tuple[float, int]]] = field(default_factory=dict)  # (group, bar) -> [(x, onset)]
    # vocal score: (group, bar) -> [(onset, singer)] from "DMITRY:" labels; bar -> text
    # of the voices not on a vocal staff (dialogue, stage directions)
    singers: dict[tuple[int, int], list[tuple[int, str]]] = field(default_factory=dict)
    voice_text: dict[int, list[etree._Element]] = field(default_factory=dict)


@dataclass
class Stats:
    bars: Counter = field(default_factory=Counter)      # chosen source per staff-group bar
    systems: Counter = field(default_factory=Counter)   # how the bar count was decided
    multirest_bars_added: int = 0
    alignment_bars_added: int = 0
    keys_respelled: int = 0
    crops_failed: int = 0
    cue_notes_removed: int = 0
    chord_symbols: int = 0
    slash_bars: int = 0
    octave_bars: int = 0
    repeat_bars: int = 0
    times_set: int = 0
    pickup: bool = False
    letters: list = field(default_factory=list)   # lettered bars (n, "A") found by align_bars
    words: int = 0
    notes: list[str] = field(default_factory=list)
    failed_crops: list = field(default_factory=list)   # (system, group, staves, image, reasons)
    crops_expected: int = 0                    # of the failed: rests only, nothing to read
    lyrics: int = 0                # syllables attached to notes (vocal score)
    lyrics_unplaced: int = 0       # syllables with no note under them
    singer_labels: int = 0
    spoken: int = 0                # dialogue blocks found (kept as text or dropped)
    beamed: int = 0                # notes beamed by auto_beam
    dynamics: int = 0              # placed from the layout (vocal score)
    wedges: int = 0
    marks_unplaced: int = 0
    chord_marks_deduped: int = 0   # repeated staccatos etc. on the notes of one chord
    graces_retyped: int = 0        # flagless graces given the piece's grace type
    graces_dropped: int = 0        # half/whole "graces" (misreads)
    wedges_dropped: int = 0        # hairpins longer than max_wedge_bars / unpaired

    def to_dict(self) -> dict:
        return {"bars": dict(self.bars), "systems": dict(self.systems),
                "multirest_bars_added": self.multirest_bars_added,
                "alignment_bars_added": self.alignment_bars_added,
                "crops_failed": self.crops_failed, "words": self.words,
                "cue_notes_removed": self.cue_notes_removed,
                "crops_failed_rest_only": self.crops_expected,
                "lyrics": self.lyrics, "lyrics_unplaced": self.lyrics_unplaced,
                "singer_labels": self.singer_labels,
                "spoken": self.spoken, "beamed": self.beamed, "dynamics": self.dynamics,
                "wedges": self.wedges, "marks_unplaced": self.marks_unplaced,
                "chord_marks_deduped": self.chord_marks_deduped,
                "graces_retyped": self.graces_retyped, "graces_dropped": self.graces_dropped,
                "wedges_dropped": self.wedges_dropped,
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
        if root is None:
            continue                # this sheet's export failed: homr only there
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
                seg = bs[pos:pos + c]
                col = _fold_multirests(seg)
                # Audiveris writes a multi-rest as the count bar + count-1 empty bars; one bar
                # per stack lets its count meet homr's (the printed count expands it later)
                out[(k, pi + 1)] = col if len(col) == len(systems[k].stacks) != len(seg) else seg
                pos += c
    return out


def _fold_multirests(bars: list[B.Bar]) -> list[B.Bar]:
    out, skip = [], 0
    for b in bars:
        if skip and b.rest_only:
            skip -= 1
            continue
        skip = max(b.multirest - 1, 0)
        out.append(b)
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


def _clef_changed(bars: list[B.Bar], i: int) -> bool:
    """The clef in force at bar i differs (sign/line, any staff) from the system's first."""
    first, cur = bars[0].clefs, bars[i].clefs
    return any(first.get(s, c)[:2] != c[:2] for s, c in cur.items())


def _vote(a: int | None, crop_counts: list[int]) -> tuple[int, str]:
    votes = Counter(crop_counts)
    if a:
        votes[a] += 1
    if not votes:
        return 0, "none"
    best = max(votes.items(), key=lambda kv: (kv[1], kv[0] in crop_counts, kv[0]))[0]
    how = "agree" if len(votes) == 1 else ("crop" if best in crop_counts and best != a else "audiveris")
    return best, how


def _bar_at(plan: SysPlan, x: float) -> int:
    for i, (l, r) in enumerate(plan.xs):
        if x < r:
            return i
    return max(plan.n - 1, 0)


def _numbered_stacks(sy: System, labels: list[T.Placed]) -> int:
    """Audiveris stacks whose left barline has a bar number printed below it."""
    il = sy.staves[0].interline
    return sum(1 for st in sy.stacks
               if any(abs((pl.line.x + pl.line.right) / 2 - st.left) <= 2 * il for pl in labels))


def _number_x(line: T.Line) -> float:
    """x that falls into the bar a printed bar number belongs to: numbers start at the
    barline or are centred on it ("244" under the barline, its left half in the bar before)."""
    return max(line.x + line.h, (line.x + line.right) / 2 + 0.3 * line.h)


def _onset_at(plan: SysPlan, bar: B.Bar, i: int, x: float, length: int | None) -> int:
    l, r = plan.xs[i]
    if not length or r <= l:
        return 0
    raw = max(0.0, min(1.0, (x - l) / (r - l))) * length
    ons = sorted({o for o, el in B.onsets(bar) if el.tag == "note"})
    if not ons:
        return 0
    return min(ons, key=lambda o: abs(o - raw))


def _main_time(song_time: list[tuple[int, str, str]]) -> tuple[str, str]:
    """The time signature that covers most bars of the song (entries in bar order)."""
    span: Counter = Counter()
    for (n, _, v), nxt in zip(song_time, song_time[1:] + [(song_time[-1][0] + 1, "", "")]):
        span[v] += max(nxt[0] - n, 1)
    return tuple(span.most_common(1)[0][0].split("/"))


def song_positions(spec: list[tuple[int, str, str]], letters: list, pickup: bool, n: int) -> list[str | None]:
    """The song setting in force at each of the n output bars (after align_bars: output bar j is
    printed position j + 1, or j with a pickup bar; lettered bars take positions of their own)."""
    def position(num: int, letter: str) -> int:
        return num + sum(1 for m, _ in letters if m < num) + (ord(letter) - ord("A") + 1 if letter else 0)
    marks = sorted((position(num, letter), v) for num, letter, v in spec)
    out, cur, k = [], marks[0][1] if marks else None, 0
    for j in range(n):
        pos = j if pickup else j + 1
        while k < len(marks) and marks[k][0] <= pos:
            cur = marks[k][1]
            k += 1
        out.append(cur)
    return out


def apply_song_time(plans: list[SysPlan], spec: list[tuple[int, str, str]], stats: Stats) -> None:
    """The time signatures of the song's `time` row onto the aligned bars."""
    flat = [(p, i) for p in plans for i in range(p.n)]
    for (p, i), v in zip(flat, song_positions(spec, stats.letters, stats.pickup, len(flat))):
        t = tuple(v.split("/")) if v else None
        if t and p.times[i] != t:
            p.times[i] = t
            stats.times_set += 1


def plan_systems(pages: list[Page], aud: dict, crop: dict, D: int, prefer: list[str],
                 stats: Stats, raw: bool = False, extra_votes: dict | None = None,
                 alts: dict | None = None, pick_mode: str = "agree",
                 weights: dict | None = None, song_time: list | None = None,
                 vector_bars: dict | None = None) -> list[SysPlan]:
    """raw: the crop reader's bars as read (no vote with Audiveris, no repairs); Audiveris
    bars only for groups whose crop failed. For comparing readers without homr tuning.
    extra_votes: {system index: bar count} of another layout provider (OLA), one more vote.
    alts: {reader name: crop bars like `crop`} of more crop readers (ensemble). Their bars join the
    candidates of systems where they read the planned bar count; among the candidates that fill
    their bar, the one that agrees most with all others wins (ties: crop, audiveris, alts).
    pick_mode "agree": score = own weight + sum of other readings' weight x agreement (weights per
    source: crop, audiveris, alt:<name>; default 1); "fallback": alts only where neither crop nor
    Audiveris fills the bar; "agree-keep": like agree, the crop reading always takes part."""
    systems = [sy for p in pages for sy in p.systems]
    chords = {p.number: [c for c in p.chords if not c.small] for p in pages}
    plans: list[SysPlan] = []
    cur_time = None
    allowed = {tuple(v.split("/")) for _, _, v in song_time or ()}
    main_time = _main_time(song_time) if song_time else None
    # bar numbers printed below each system (one per bar in parts that number every bar)
    labels: dict[int, list[T.Placed]] = {}
    for p in pages:
        pt = T.classify(p)
        for pl, _ in pt.numbers + pt.lettered + pt.jumps:
            if not pl.above:
                labels.setdefault(id(pl.system), []).append(pl)
    for k, sy in enumerate(systems):
        plan = SysPlan(sy, k)
        if sy.skip:
            plans.append(plan)
            continue
        groups = sy.groups()
        a_bars = {gi: aud.get((k, gi)) for gi in range(len(groups))}
        a_n = max((len(v) for v in a_bars.values() if v), default=0) or None
        h_bars = {gi: crop.get((k, gi)) for gi in range(len(groups))}
        il = sy.staves[0].interline
        if not raw and sy.stacks and 2 * il <= max(s.right for s in sy.staves) - sy.stacks[-1].right < 8 * il:
            # homr reads the courtesy key/time signature after the last barline as a rest
            # bar of its own; Audiveris leaves that space out of its stacks
            for gi, v in h_bars.items():
                if v and len(v) == len(sy.stacks) + 1 and v[-1].rest_only:
                    h_bars[gi] = v[:-1]
        h_ns = [len(v) for v in h_bars.values() if v]
        if raw:
            n, how = (Counter(h_ns).most_common(1)[0][0], "crop") if h_ns else (a_n or 0, "audiveris")
        else:
            n, how = _vote(a_n, h_ns + ([extra_votes[k]] if extra_votes and extra_votes.get(k) else []))
        sy_labels = labels.get(id(sy), [])
        if not raw and a_n and how == "crop" and Counter(h_ns)[n] == 1 and a_n not in h_ns \
                and a_n == len(sy.stacks) >= 2 and len(sy_labels) <= a_n \
                and _numbered_stacks(sy, sy_labels) >= max(a_n - 1, 2):
            # one homr reading against Audiveris is a tie: parts that number every bar
            # decide it (homr splits bars at dashed barlines / long notes); more numbers
            # than stacks means Audiveris missed a barline
            n, how = a_n, "audiveris"
        if not raw and a_n and how == "crop" and Counter(h_ns)[n] == 1 and a_n not in h_ns \
                and a_n == len(sy.stacks) and any(st.special == "MULTI_REST" for st in sy.stacks) \
                and max(st.right for st in sy.staves) - sy.stacks[-1].right < 8 * il:
            # homr splits systems with multi-measure rests (at the key changes between them,
            # or the count read as a note): Audiveris' stacks are the better count there,
            # unless they stop short of the staff end (a missed barline)
            n, how = a_n, "audiveris"
        if n == 0 and sy.staves:
            # neither engine found a bar: a staff of multi-measure rests ("5" over "5-9").
            # One rest bar; expand_multirests / resegment_rest_systems count it out
            n, how = 1, "empty"
            for gi, group in enumerate(groups):
                bar = B.rest_bar(len(group), B.bar_length(cur_time, D), D)
                h_bars[gi] = [bar]
        vx = None
        if not raw and vector_bars and len(sy.staves) == 1:
            # born-digital part: the printed barlines are the bar count and the bar x ranges
            # (multi-staff systems: piano and vocal staves are barred apart, not handled)
            top = sy.staves[0].top
            vx = next((xs for t, xs in vector_bars.get(sy.page, ()) if abs(t - top) < il), None)
            if vx:
                n, how = len(vx), "vector"
            else:
                vx = None
        stats.systems[how] += 1
        plan.n = n
        if n == 0:
            plans.append(plan)
            continue
        # x-range per bar: Audiveris stacks if they match, else an even split
        staff_right = max(s.right for s in sy.staves) if sy.staves else 0
        if vx:
            plan.xs = vx
        elif len(sy.stacks) == n:
            plan.xs = [(s.left, s.right) for s in sy.stacks]
        elif sy.stacks and len(sy.stacks) < n and staff_right - sy.stacks[-1].right >= 8 * il:
            # Audiveris missed the last barline(s): its stacks for the bars they cover, the
            # rest of the staff split among the bars it missed
            left, extra = sy.stacks[-1].right, n - len(sy.stacks)
            w = (staff_right - left) / extra
            plan.xs = [(s.left, s.right) for s in sy.stacks] + \
                [(left + i * w, left + (i + 1) * w) for i in range(extra)]
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
            if allowed and t not in allowed:
                t = main_time       # the song never has this time: a misread
            plan.times.append(t)
            cur_time = t
        for gi, group in enumerate(groups):
            if raw:
                src, s = (h_bars.get(gi), "crop") if h_bars.get(gi) else (a_bars.get(gi), "audiveris")
                chosen = []
                for i in range(n):
                    if src and i < len(src):
                        bar = copy.deepcopy(src[i])
                    else:
                        s = "rest"
                        bar = B.rest_bar(len(group), B.bar_length(plan.times[i], D), D)
                    stats.bars[s] += 1
                    bar.staves = max(bar.staves, len(group))
                    chosen.append(bar)
                plan.chosen[gi] = chosen
                continue
            hb = h_bars.get(gi) if h_bars.get(gi) and len(h_bars[gi]) == n else None
            ab = a_bars.get(gi) if a_bars.get(gi) and len(a_bars[gi]) == n else None
            order = prefer
            perc = all(st.clef == "PERCUSSION_CLEF" for st in group)
            if perc:
                # homr reads percussion staves as pitched (often with a C clef): its bars only
                # where Audiveris lacks the system's bar count (Ghost 20 Drums: 1180 vs 695 notes)
                order = ["audiveris", "crop"]
                hb = None if ab else hb and [B.to_unpitched(b) for b in hb]
            options = {"crop": hb, "audiveris": ab}
            alt_opts = {f"alt:{name}": [B.to_unpitched(b) for b in v] if perc else v
                        for name, d in (alts or {}).items() if (v := d.get((k, gi))) and len(v) == n}
            primary = next((options[s] for s in order if options.get(s)), None)
            chosen = []
            for i in range(n):
                length = B.bar_length(plan.times[i], D)
                bar_order, clef_src = order, primary
                seen = [s for s in order if options.get(s) and _clef_changed(options[s], i)]
                if len(seen) == 1 and len([s for s in order if options.get(s)]) == 2:
                    # a clef change inside the system that only one engine saw: the other
                    # one's pitches are read in the old clef there
                    bar_order = seen + [s for s in order if s != seen[0]]
                    clef_src = options[seen[0]]
                cands = [(s, B.close_voice_gaps(options[s][i], length) if s == "crop" else options[s][i])
                         for s in bar_order if options.get(s)]
                cands += [(s, B.close_voice_gaps(v[i], length)) for s, v in alt_opts.items()]
                l, r = plan.xs[i]
                ids = {st.id for st in group}
                printed = any(c.staff in ids and l <= c.x + c.w / 2 < r for c in chords.get(sy.page, ()))
                if printed:
                    # noteheads are printed: a rest-only reading lost a voice whose rhythm
                    # didn't add up (Audiveris), the other engine's notes are better
                    with_notes = [(s, b) for s, b in cands if not b.rest_only]
                    cands = with_notes + [c for c in cands if c not in with_notes]
                ok = [(s, b) for s, b in cands if B.bar_ok(b, length)]
                st_i = sy.stacks[i] if i < len(sy.stacks) else None
                if vx:      # printed bars: the Audiveris stack in this bar
                    st_i = next((st for st in sy.stacks if l <= (st.left + st.right) / 2 < r), None)
                multirest = st_i is not None and st_i.special == "MULTI_REST" and \
                    (vx is not None or plan.xs[i] == (st_i.left, st_i.right))
                if multirest:
                    # Audiveris' multi-rest (its stack kept for this bar): homr reads the printed
                    # count above it as notes. Its rest bar, else a rest bar of the right length
                    ab_i = options["audiveris"][i] if options.get("audiveris") else None
                    ok = [("audiveris", ab_i)] if ab_i is not None and ab_i.rest_only else \
                        [("rest", B.rest_bar(len(group), length, D))]
                if pick_mode == "fallback" and any(not s.startswith("alt:") for s, _ in ok):
                    ok = [c for c in ok if not c[0].startswith("alt:")]
                if pick_mode == "agree-keep" and not multirest:
                    # homr's reading stays a candidate even when its voices don't fill the bar
                    ok += [c for c in cands if c[0] == "crop" and not c[1].empty and c not in ok]
                if alt_opts and pick_mode.startswith("agree") and len(ok) >= 2:
                    # ensemble: the full bar that agrees most with every other reading
                    if printed:
                        ok = [c for c in ok if not c[1].rest_only] or ok
                    sigs = [B.signature(b) for _, b in cands]
                    w = [(weights or {}).get(s, 1.0) for s, _ in cands]
                    score = {id(b): w[j] + sum(w[m] * B.similarity(sigs[j], sigs[m])
                                               for m in range(len(cands)) if m != j)
                             for j, (_, b) in enumerate(cands)}
                    pick = max(ok, key=lambda c: (round(score[id(c[1])], 6), -ok.index(c)))
                else:
                    pick = (ok[0] if ok else None) or next(((s, b) for s, b in cands if not b.empty), None)
                if pick is None:
                    # neither source has this system's bar count: best effort by position
                    loose = [v for v in ((a_bars.get(gi), h_bars.get(gi)) if perc else (h_bars.get(gi), a_bars.get(gi))) if v]
                    src = next((v for v in loose if i < len(v)), None)
                    if src:
                        pick = ("fallback", B.to_unpitched(src[i]) if perc and src is h_bars.get(gi) else src[i])
                    else:
                        pick = ("rest", B.rest_bar(len(group), length, D))
                s, bar = pick
                stats.bars[s] += 1
                bar = copy.deepcopy(bar)
                bar.staves = max(bar.staves, len(group))
                if clef_src is not None:
                    bar.clefs = dict(clef_src[i].clefs) or bar.clefs
                    bar.key = clef_src[i].key if clef_src[i].key is not None else bar.key
                a_key = ab[i].key if ab else None
                h_key = hb[i].key if hb else None
                if s == "crop" and str(a_key) == "0" and h_key not in (None, "0"):
                    # homr reads a key of naturals only (a change to C) as sharps, where
                    # Audiveris reads no key: homr's notes are re-read in C (elsewhere
                    # homr's key is the better one: Audiveris drops faint flats)
                    B.respell(bar, int(a_key))
                    bar.key = a_key
                    stats.keys_respelled += 1
                # Audiveris directions (dynamics, wedges, tempo) onto non-Audiveris bars
                if s != "audiveris" and bar.source != "audiveris" and a_n:   # a fallback bar may be Audiveris'
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


def _rested_cues(bar: B.Bar, staff: int, length: int | None) -> set[int]:
    """Onsets of the notes on `staff` when another voice there rests the whole bar: the
    player rests, the notes above the rest are a cue (printed full size in these parts)."""
    voices: dict[str, list] = {}
    for on, el in B.onsets(bar):
        if el.tag == "note" and int(el.findtext("staff", "1") or 1) == staff \
                and el.find("chord") is None and el.find("grace") is None:
            voices.setdefault(el.findtext("voice", "1"), []).append(el)
    if len(voices) < 2:
        return set()
    def whole_rest(els) -> bool:
        return len(els) == 1 and els[0].find("rest") is not None and (
            els[0].find("rest").get("measure") == "yes" or els[0].findtext("type") == "whole"
            or (length is not None and int(els[0].findtext("duration", "0") or 0) == length))
    rest_voices = {v for v, els in voices.items() if whole_rest(els)}
    if not rest_voices or len(rest_voices) == len(voices):
        return set()
    return {on for on, el in B.onsets(bar) if el.tag == "note" and el.find("rest") is None
            and int(el.findtext("staff", "1") or 1) == staff
            and el.findtext("voice", "1") not in rest_voices}


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
                    rested = _rested_cues(plan.chosen[gi][i], si, B.bar_length(plan.times[i], D))
                    if rested:
                        removed = B.cues_to_rests(plan.chosen[gi][i], si, rested)
                        stats.cue_notes_removed += removed
                        plan.cues.add((gi, i))
                        continue
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


TYPES = {Fraction(4): ("whole", 0), Fraction(3): ("half", 1), Fraction(2): ("half", 0),
         Fraction(3, 2): ("quarter", 1), Fraction(1): ("quarter", 0), Fraction(3, 4): ("eighth", 1),
         Fraction(1, 2): ("eighth", 0), Fraction(1, 4): ("16th", 0)}


def slash_bar(sb: SL.SlashBar, old: B.Bar, D: int) -> B.Bar | None:
    """The bar of a slash reading: slashes on the middle line (B4), the old bar's directions kept."""
    items = [e for e in old.items if e.tag in ("direction", "harmony")]
    for ev in sb.events:
        if ev.dur not in TYPES:
            return None
        typ, dots = TYPES[ev.dur]
        n = etree.Element("note")
        if ev.kind == "rest":
            etree.SubElement(n, "rest")
        else:
            pitch = etree.SubElement(n, "pitch")
            etree.SubElement(pitch, "step").text = "B"
            etree.SubElement(pitch, "octave").text = "4"
        etree.SubElement(n, "duration").text = str(int(ev.dur * D))
        for kind, on in (("stop", ev.tie_stop), ("start", ev.tie_start)):
            if on:
                etree.SubElement(n, "tie", type=kind)
        etree.SubElement(n, "voice").text = "1"
        etree.SubElement(n, "type").text = typ
        for _ in range(dots):
            etree.SubElement(n, "dot")
        if ev.kind != "rest":
            etree.SubElement(n, "stem").text = "down"
            etree.SubElement(n, "notehead").text = "slash"
            if ev.tie_start or ev.tie_stop or ev.marks:
                nt = etree.SubElement(n, "notations")
                for kind, on in (("stop", ev.tie_stop), ("start", ev.tie_start)):
                    if on:
                        etree.SubElement(nt, "tied", type=kind)
                if ev.marks:
                    arts = etree.SubElement(nt, "articulations")
                    for m in dict.fromkeys(ev.marks):
                        etree.SubElement(arts, m)
        items.append(n)
    return B.Bar(items, "slash", old.staves, dict(old.clefs), old.key, old.time)


def place_slashes(plans: list[SysPlan], slash_bars: list[SL.SlashBar], D: int, stats: Stats) -> None:
    """Bars read from the slash glyphs replace the readers' bars on single-staff parts."""
    for sb in slash_bars:
        for plan in plans:
            if plan.system.page != sb.page or not plan.n:
                continue
            st = next((st for st in plan.system.staves if abs(st.top - sb.top) < st.interline), None)
            if st is None:
                continue
            gi, _ = _group_of(plan.system, st.id)
            if gi not in plan.chosen or len(plan.system.groups()[gi]) != 1:
                break
            i = _bar_at(plan, (sb.x0 + sb.x1) / 2)
            if sb.length * D != B.bar_length(plan.times[i], D):
                break
            bar = slash_bar(sb, plan.chosen[gi][i], D)
            if bar is not None:
                plan.chosen[gi][i] = bar
                stats.slash_bars += 1
                on = 0
                for ev in sb.events:      # where each beat is printed: chord symbols line up with it
                    plan.beats.setdefault((gi, i), []).append((ev.x, int(on * D)))
                    on += ev.dur
            break


OTTAVA_ON = re.compile(r"\(.*\b8va\)", re.I)       # "STR. ENS. (loco & 8va)": a patch an octave up
OTTAVA_OFF = re.compile(r"\(loco\)", re.I)


def _octave_shift(kind: str) -> etree._Element:
    d = etree.Element("direction", placement="above")
    etree.SubElement(etree.SubElement(d, "direction-type"), "octave-shift", type=kind, size="8")
    return d


def patch_octaves(plans: list[SysPlan], stats: Stats) -> None:
    """Keyboard patch labels "(loco & 8va)" .. "(loco)": staff 1 an octave up with an 8va line
    (the truths' convention, user 2026-10-15)."""
    on: dict[int, bool] = {}
    for plan in plans:
        for gi, bars in plan.chosen.items():
            for bar in bars:
                texts = [w.text or "" for d in bar.items if d.tag == "direction" for w in d.iter("words")]
                was = on.setdefault(gi, False)
                if any(OTTAVA_ON.search(t) for t in texts):
                    on[gi] = True
                elif any(OTTAVA_OFF.search(t) for t in texts):
                    on[gi] = False
                if on.get(gi) != was:
                    B.add_direction(bar, _octave_shift("down" if on[gi] else "stop"), 0, 1)
                if not on.get(gi):
                    continue
                stats.octave_bars += 1
                for n in bar.notes():
                    o = n.find("pitch/octave")
                    if o is not None and (n.findtext("staff") or "1") == "1":
                        o.text = str(int(o.text) + 1)


def apply_repeats(plans: list[SysPlan], repeats: list[SL.Repeat], stats: Stats) -> None:
    """Measure-repeat signs: the bar(s) get the notes of the bar(s) before them (the truths write
    them out). Placed by printed bar number after align_bars (output bar j = printed position
    j + 1); in bar order, so a repeat of a repeated bar copies the copy."""
    track: dict[int, list[tuple[SysPlan, int]]] = {}
    for plan in plans:
        for gi in plan.chosen:
            track.setdefault(gi, []).extend((plan, i) for i in range(plan.n))
    pos_of = {}
    for r in repeats:
        if r.number:
            for k in range(r.bars):
                num = r.number + k
                pos_of[num] = (num + sum(1 for m, _ in stats.letters if m < num) - (0 if stats.pickup else 1), r.bars)
    for gi, bars in track.items():
        for j, n in sorted(pos_of.values()):
            if not (0 <= j - n and j < len(bars)):
                continue
            (dp, di), (sp, si) = bars[j], bars[j - n]
            old, src = dp.chosen[gi][di], sp.chosen[gi][si]
            if src.rest_only:
                continue
            bar = copy.deepcopy(src)
            bar.items = [e for e in bar.items if e.tag not in ("direction", "harmony")] + \
                [e for e in old.items if e.tag in ("direction", "harmony")]
            dp.chosen[gi][di] = bar
            stats.repeat_bars += 1


def place_chords(plans: list[SysPlan], pages: list[Page], symbols: list[CH.Symbol], D: int,
                 stats: Stats) -> None:
    """Chord symbols onto the bar and beat under them: the staff right below (within 5 staff
    spaces), the beat by x. Bars that get one lose any chords Audiveris read there."""
    lyrics = {p.number: [t for t in p.texts if t.role == "Lyrics" or t.kind == "syllable"] for p in pages}
    cleared: set = set()
    for sym in symbols:
        if any(CH.overlaps(sym, t.x, t.y, t.w, t.h) for t in lyrics.get(sym.page, ())):
            continue
        bottom = sym.y + sym.h
        best = None
        for plan in plans:
            if plan.system.page != sym.page or not plan.n:
                continue
            for st in plan.system.staves:
                gap = st.top - bottom
                if -st.interline <= gap <= 5 * st.interline and st.left - st.interline <= sym.x <= st.right \
                        and (best is None or gap < best[0]):
                    best = (gap, plan, st)
        if best is None:
            continue
        _, plan, st = best
        gi, staff_no = _group_of(plan.system, st.id)
        if gi not in plan.chosen:
            continue
        i = _bar_at(plan, sym.x + 1)
        bar = plan.chosen[gi][i]
        if id(bar) not in cleared:
            bar.items = [e for e in bar.items if e.tag != "harmony"]
            cleared.add(id(bar))
        h = CH.harmony(sym)
        # chord symbols sit over slashes / rests more than notes: beat by x on an eighth grid
        length = B.bar_length(plan.times[i], D) or 4 * D
        l, r = plan.xs[i]
        step = max(D // 2, 1)
        on = min(round(max(0.0, (sym.x - l) / (r - l)) * length / step) * step, length - step) if r > l else 0
        if plan.beats.get((gi, i)):     # a slash bar: the slash / rest the symbol stands over
            on = min(plan.beats[(gi, i)], key=lambda b: abs(b[0] - sym.x))[1]
        if on:
            etree.SubElement(h, "offset").text = str(on)
        if bar.staves > 1:
            etree.SubElement(h, "staff").text = str(staff_no)
        bar.items.insert(0, h)
        stats.chord_symbols += 1


def _group_of(sy: System, staff_id: int) -> tuple[int, int]:
    for gi, g in enumerate(sy.groups()):
        for si, st in enumerate(g):
            if st.id == staff_id:
                return gi, si + 1
    return 0, 1


SPOKEN_TEXT = ("drop", "text")


def _label_onset(plan: SysPlan, page: Page, staff_id: int, x: float, D: int) -> tuple[int, int]:
    """(bar, onset) a singer label printed at x refers to: the first chord at or right of
    it (labels are left-aligned with their first note). Chords are matched to the bar's
    note onsets by order when their counts agree, else by position."""
    i = _bar_at(plan, x + 1)
    sy = plan.system
    il = next((s.interline for s in sy.staves if s.id == staff_id), 20.0)
    gi, staff_no = _group_of(sy, staff_id)
    bar = plan.chosen[gi][i]
    length = B.bar_length(plan.times[i], D)
    l, r = plan.xs[i]
    chords = sorted((c for c in page.chords if c.staff == staff_id and l <= c.x + c.w / 2 < r),
                    key=lambda c: c.x)
    xs: list[float] = []
    for c in chords:
        if not xs or c.x - xs[-1] >= 0.8 * il:
            xs.append(c.x)
    ons = sorted({on for on, el in B.onsets(bar) if el.tag == "note" and el.find("rest") is None
                  and el.find("grace") is None and int(el.findtext("staff", "1") or 1) == staff_no})
    after = [k for k, cx in enumerate(xs) if cx >= x - 1.5 * il]
    if xs and not after:
        return i, 10 ** 9           # right of the bar's last note: from the next bar on
    if len(xs) == len(ons) and after:
        return i, ons[after[0]]
    return i, _onset_at(plan, bar, i, x, length) if ons else 0


def _place_vocal_text(classified: list[T.PageText], pages: list[Page], by_sys: dict, D: int,
                      stats: Stats, meta: dict) -> None:
    """Singer labels -> SysPlan.singers; dialogue (meta spoken_text: text) and stage
    directions -> SysPlan.voice_text."""
    mode = str(meta.get("spoken_text", "drop")).lower()
    if mode not in SPOKEN_TEXT:
        raise ValueError(f"spoken_text: '{mode}' (use {' or '.join(SPOKEN_TEXT)})")
    for page, pt in zip(pages, classified):
        for pl, label in pt.singers:
            plan = by_sys.get(id(pl.system))
            if not plan or not plan.n:
                continue
            gi, _ = _group_of(pl.system, pl.staff.id)
            if gi == pl.system.piano_group or gi not in plan.chosen:
                continue            # no vocal staff below the label
            i, on = _label_onset(plan, page, pl.staff.id, pl.line.x, D)
            plan.singers.setdefault((gi, i), []).append((on, label))
            stats.singer_labels += 1
        texts = [(pl, t, True) for pl, t in pt.spoken] + [(pl, pl.line.text, False) for pl in pt.stage]
        for pl, t, spoken in texts:
            stats.spoken += spoken
            plan = by_sys.get(id(pl.system))
            if not plan or not plan.n or (spoken and mode == "drop"):
                continue
            i = _bar_at(plan, pl.line.x + 1)
            plan.voice_text.setdefault(i, []).append(B.words_direction(t, "above"))


def place_text(plans: list[SysPlan], pages: list[Page], D: int, stats: Stats,
               meta: dict, split: bool, estimate_onset: bool = False,
               symbols: list[CH.Symbol] = ()) -> tuple[list[T.Line], list[dict]]:
    by_sys = {id(p.system): p for p in plans}
    vocal = any(p.system.piano_group is not None for p in plans)
    running = T.running_headers(pages)
    classified = [T.classify(page, vocal, running) for page in pages]
    if vocal:
        _place_vocal_text(classified, pages, by_sys, D, stats, meta)
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
            if symbols:
                # chord symbols placed from the text layer: Audiveris' OCR of them ("Bl? F") goes
                atoms = [a for a in pl.line.atoms if not any(
                    sy.page == a.page and CH.overlaps(sy, a.x, a.y, a.w, a.h) for sy in symbols)]
                if not atoms:
                    continue
                if len(atoms) < len(pl.line.atoms):
                    pl = T.Placed(T.Line(pl.line.page, atoms), pl.system, pl.staff, pl.above)
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
            if value.isdigit():
                # a bar number printed (or boxed) at the system start: evidence for the bar
                # count; the truth scores keep letter rehearsal marks only
                plan.printed.setdefault(i, int(value))
                continue
            d = etree.Element("direction", placement="above")
            etree.SubElement(etree.SubElement(d, "direction-type"), "rehearsal").text = value
            B.add_direction(plan.chosen[0][i], d, 0, 1)
        for pl, n in pt.numbers:
            plan = by_sys.get(id(pl.system))
            if not plan or not plan.n:
                continue
            i = _bar_at(plan, _number_x(pl.line))
            il = pl.staff.interline
            if not pl.above:
                # bar numbers are printed below the start of their bar (parts)
                plan.printed.setdefault(i, n)
            elif vocal and pl.staff is pl.system.staves[0] and abs(pl.line.x - plan.xs[i][0]) <= 3 * il:
                # vocal scores print them above the bar, at its barline (a centred number
                # there is a multi-rest count)
                plan.printed.setdefault(i, n)
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
                plan.lettered.setdefault(_bar_at(plan, _number_x(pl.line)), n)
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
            if kind == "count" and not 2 <= n <= MAX_GAP:
                continue    # a boxed rehearsal number ("238") above a rest is no count
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


def _multirest_counts(plans: list[SysPlan], crop: dict, stats: Stats) -> dict[tuple[int, int], int]:
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
    crop_count: dict[tuple[int, int], int] = {}
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
                # a next number inside the range ("124-131" then "131" for 131A whose
                # letter OCR lost) contradicts it: the printed range wins
                if nxt is not None and b < nxt <= a + 99 and nxt - a != count:
                    stats.notes.append(f"system {k + 1}: range {a}-{b}, next bar number {nxt}"
                                       f" -> {nxt - a} bars")
                    count = nxt - a
                known[(k, i)] = count
        stacks_ok = len(p.system.stacks) == p.n
        for i in range(p.n):
            if not rest_only.get((k, i)) or (k, i) in known:
                continue
            counts = {hb[i].multirest for gi in range(len(p.system.groups()))
                      if (hb := crop.get((k, gi))) and len(hb) == p.n and hb[i].multirest > 1}
            flagged = stacks_ok and p.system.stacks[i].special == "MULTI_REST"
            if counts or flagged:
                unknown.add((k, i))
                if len(counts) == 1:
                    crop_count[(k, i)] = counts.pop()
    size = lambda j: known.get(glob[j], 1)

    def agrees(j: int) -> bool:
        """The printed number at j fits the nearest printed number before or after it
        (OCR drops digits: "26" read as "2" would make the next rest 27 bars long)."""
        for rng in (range(j - 1, -1, -1), range(j + 1, len(glob))):
            for i in rng:
                if glob[i] in unknown:
                    break
                if glob[i] in printed:
                    a, b = sorted((i, j))
                    if printed[glob[b]] - printed[glob[a]] == sum(size(x) for x in range(a, b)):
                        return True
                    break
        return False

    def anchor(rng) -> tuple[int, int] | None:
        """Nearest printed number in rng that agrees with its neighbours, else the nearest."""
        cands = [j for j in rng if glob[j] in printed]
        j = next((j for j in cands if agrees(j)), cands[0] if cands else None)
        return (j, printed[glob[j]]) if j is not None else None

    # bar-number gaps: number at the rest = previous printed + bars since; count = next - it
    for pos, key in enumerate(glob):
        if key not in unknown:
            continue
        prev = anchor(range(pos - 1, -1, -1))
        nxt = anchor(range(pos + 1, len(glob)))
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
        if key in crop_count:
            known[key] = crop_count[key]
    return known


def _clamp_vocal(plan: SysPlan) -> None:
    """After bars at the system end were removed: labels there act from the end of the
    last bar (i.e. from the next one), text moves onto the last bar."""
    last = plan.n - 1
    singers: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for (g, j), marks in plan.singers.items():
        marks = marks if j <= last else [(10 ** 9, name) for _, name in marks]
        singers.setdefault((g, min(j, last)), []).extend(marks)
    plan.singers = singers
    text: dict[int, list[etree._Element]] = {}
    for j, els in plan.voice_text.items():
        text.setdefault(min(j, last), []).extend(els)
    plan.voice_text = text


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
            _clamp_vocal(plan)
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
        plan.singers = {(g, 0): v for (g, _), v in plan.singers.items()}
        plan.voice_text = {0: [e for v in plan.voice_text.values() for e in v]} if plan.voice_text else {}
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


def expand_multirests(plans: list[SysPlan], crop: dict, D: int, stats: Stats) -> None:
    drop_courtesy_bars(plans, stats)
    resegment_rest_systems(plans, D, stats)
    counts = _multirest_counts(plans, crop, stats)
    for k, plan in enumerate(plans):
        # "15-17" over a rest: its first bar is printed bar 15
        for i, (kind, a, b) in plan.mr.items():
            if kind == "range" and i < plan.n:
                plan.printed.setdefault(i, a)
                # "124-131" then "131": that is 131A with the letter lost to OCR
                nk, ni = (k, i + 1) if i + 1 < plan.n else (k + 1, 0)
                if nk < len(plans) and plans[nk].printed.get(ni) == b and ni not in plans[nk].lettered:
                    del plans[nk].printed[ni]
                    plans[nk].lettered[ni] = (b, "A")
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
            plan.singers = _shift(plan.singers, i + 1, count - 1, keyed_by_group=True)
            plan.voice_text = _shift(plan.voice_text, i + 1, count - 1)
            plan.n += count - 1
            stats.multirest_bars_added += count - 1


# ------------------------------------------------------------------------ bar numbers

MAX_GAP = 99            # longest multi-rest / cut taken from printed numbers
ALIGN_PENALTY = 1.2     # a gap must be backed by more than one printed bar number ...
JUMP_WEIGHT = 1.5       # ... or by a cut mark ("[to] 97"), which is explicit
LETTER_NEAR = 12        # a lettered number ("131A") needs a plain number this close (bars, value)


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
    plan.singers = _shift(plan.singers, i, count, keyed_by_group=True)
    plan.voice_text = _shift(plan.voice_text, i, count)
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
    # labels and text of a dropped (empty) bar act from the next one
    singers: dict = {}
    for (g, j), v in plan.singers.items():
        singers.setdefault((g, j - 1 if j > i else j), []).extend(
            [(0, name) for _, name in v] if j == i else v)
    plan.singers = singers
    text: dict = {}
    for j, v in plan.voice_text.items():
        text.setdefault(j - 1 if j > i else j, []).extend(v)
    plan.voice_text = text
    plan.n -= 1
    if plan.n:
        _clamp_vocal(plan)


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
    # a lettered number counts only when plain numbers near it agree ("7A" is a misread
    # "72A"; taken as bar 7A it would shift every bar from 8 on)
    plain = [(start[k] + i, v) for k, p in enumerate(plans) for i, v in p.printed.items()
             if i < p.n and 0 < v <= 9999]

    def plausible(j: int, n: int) -> bool:
        near = sorted(v for jj, v in plain if abs(jj - j) <= LETTER_NEAR)
        return not near or abs(near[len(near) // 2] - n) <= LETTER_NEAR

    extra: set[tuple[int, str]] = set()
    bogus: set[tuple[int, int]] = set()
    for k, p in enumerate(plans):
        for i, (n, letter) in list(p.lettered.items()) + list(p.jumps.items()):
            if letter and not plausible(start[k] + i, n):
                bogus.add((k, i))
                continue
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
            if i < p.n and 0 < n <= 9999 and (k, i) not in bogus:
                obs.append(_Obs(start[k] + i, position(n, letter), 1.0, "number", f"{n}{letter}"))
        for i, (n, letter) in p.jumps.items():
            if start[k] + i < len(flat) and 0 < n <= 9999 and (k, i) not in bogus:
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
    stats.pickup, stats.letters = base == -1, sorted(extra)
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
    """The instrument a label names: the text starts with a name/alias ("Glock - soft
    mallets"), else it holds a 4+ letter word of exactly one instrument ("Sus Cymbal" ->
    Cymbal; "Tree" is no match when Bell Tree and Mark Tree are both listed)."""
    words = _norm(text)
    if not words:
        return None
    owners: dict[str, set[str]] = {}
    for ins in instruments:
        for alias in [ins["name"], *ins.get("aliases", [])]:
            aw = _norm(alias)
            if alias.startswith("(") and alias.lower() in text.lower():
                return ins["name"]
            if aw and words[:len(aw)] == aw:
                return ins["name"]
            for w in aw:
                if len(w) >= 4:
                    owners.setdefault(w, set()).add(ins["name"])
    hits = {next(iter(owners[w])) for w in words if len(owners.get(w, ())) == 1}
    return hits.pop() if len(hits) == 1 else None


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
                  "G": (-3, -5), "F#": (-4, -6), "F": (-4, -7), "E": (-5, -8), "Eb": (-5, -9),
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


def _canonical_singers(plans: list[SysPlan]) -> dict[str, str]:
    """OCR spellings of one label ("DMITRY", "DMlTRY") -> the most frequent one."""
    import Levenshtein

    counts = Counter(name for p in plans for v in p.singers.values() for _, name in v)
    out: dict[str, str] = {}
    for name, _ in counts.most_common():
        out[name] = next((c for c in out.values() if c == out.get(c) and
                          Levenshtein.ratio(c, name) >= 0.85), name)
    return out


MALE_VOICES = r"\b(men|male|tenors?|bass(es)?|baritones?)\b"


_DUET = re.compile(r"\s*(?:\+|&|\bAND\b)\s*")


def _singers_of(label: str, known: set[str]) -> list[str]:
    """"DOWAGER+ANASTASIA" -> ["DOWAGER EMPRESS", "ANASTASIA"]: each name, or the one
    single label elsewhere in the score that starts with it; a single label -> [label]."""
    names = [s.strip() for s in _DUET.split(label) if s.strip()]
    if len(names) < 2:
        return [label]
    out = []
    for n in names:
        longer = [k for k in known if k.startswith(n + " ")]
        out.append(longer[0] if len(longer) == 1 else n)
    return out


def _octave_treble(part: OutPart) -> None:
    """A male voice printed in treble clef sounds an octave lower: treble-8vb clef with the
    pitches an octave down (the convention of the ground truths here)."""
    for bar in part.bars:
        if bar is None or bar.clefs.get(1, ("G", "2", ""))[:2] != ("G", "2") \
                or bar.clefs.get(1, ("", "", ""))[2]:
            continue
        bar.clefs = {**bar.clefs, 1: ("G", "2", "-1")}
        for n in bar.notes():
            o = n.find("pitch/octave")
            if o is not None and o.text:
                o.text = str(int(o.text) - 1)


def build_vocal_parts(plans: list[SysPlan], D: int, stats: Stats,
                      male: re.Pattern | None = None) -> tuple[list[OutPart], OutPart, list]:
    """Vocal score -> (one part per singer label, the piano, times).

    The singer of a vocal staff is the last label printed on it ("DMITRY:"), carried
    over to the staff at the same position in the next systems; a label inside a bar
    splits the bar there. Before the first label a staff is "Voice <n>". Dialogue and
    stage directions go to the top voice part. Parts whose name matches `male` are
    written in treble-8vb clef.
    """
    total = sum(p.n for p in plans)
    times: list = []
    for p in plans:
        times += p.times
    canon = _canonical_singers(plans)
    known = {c for c in canon.values() if len(_DUET.split(c)) == 1}
    piano = OutPart("Piano", 2, [None] * total)
    voices: dict[str, OutPart] = {}
    cur: dict[int, str] = {}
    texts: dict[int, list[etree._Element]] = {}
    clashes = 0
    pos = 0
    for p in plans:
        for i, els in p.voice_text.items():
            g = pos + min(i, p.n - 1) if p.n else pos - 1     # system left empty: previous bar
            if 0 <= g < total:
                texts.setdefault(g, []).extend(els)
        for gi, g in enumerate(p.system.groups()):
            if gi not in p.chosen:
                continue
            if gi == p.system.piano_group:
                for i, bar in enumerate(p.chosen[gi]):
                    piano.bars[pos + i] = bar
                continue
            L = p.system.logical[gi]
            for i, bar in enumerate(p.chosen[gi]):
                length = B.bar_length(p.times[i], D) or 10 ** 9
                segs: list[tuple[int, str | None]] = [(0, cur.get(L))]
                for on, name in sorted(p.singers.get((gi, i), [])):
                    name = canon.get(name, name)
                    on = min(on, length)
                    if segs[-1][0] == on:
                        segs[-1] = (on, name)
                    elif segs[-1][1] != name:
                        segs.append((on, name))
                cur[L] = segs[-1][1] if segs[-1][1] else cur.get(L)
                for k, (start, name) in enumerate(segs):
                    end = segs[k + 1][0] if k + 1 < len(segs) else None
                    if start >= length or end == start:
                        continue
                    piece = bar if (start == 0 and end is None) else B.keep_span(bar, start, end)
                    if name is None:
                        if piece.rest_only:
                            continue
                        name = f"Voice {L}"
                    # a duet label ("DOWAGER+ANASTASIA") puts the line into each singer's part
                    for k, single in enumerate(_singers_of(name, known)):
                        part = voices.setdefault(single, OutPart(T.singer_name(single), 1,
                                                                 [None] * total))
                        old = part.bars[pos + i]
                        if old is None or old.rest_only:
                            part.bars[pos + i] = piece if k == 0 else copy.deepcopy(piece)
                        elif not piece.rest_only:
                            clashes += 1    # two staves with one singer: the first is kept
        pos += p.n
    parts = list(voices.values()) or [OutPart("Voice", 1, [None] * total)]
    for part in parts:
        for bar in part.bars:
            if bar is not None:
                B.dedupe_unison(bar)
        if male and male.search(part.name):
            _octave_treble(part)
    for g, els in texts.items():
        top = parts[0]
        if top.bars[g] is None:
            top.bars[g] = B.rest_bar(1, B.bar_length(times[g], D), D)
        for el in els:
            B.add_direction(top.bars[g], el, 0, None)
    if clashes:
        stats.notes.append(f"vocal: {clashes} bar(s) where two staves had the same singer "
                           "(the upper one kept)")
    return parts, piano, times


def share_system_text(groups: list[list[OutPart]], times: list, D: int) -> None:
    """System-wide text and tempo onto the top part of every output score (vocal score:
    the voices and the piano file each get a copy)."""
    for g in range(len(times)):
        found = []
        for parts in groups:
            for p in parts:
                bar = p.bars[g]
                if bar is None:
                    continue
                for el in [e for e in bar.items if e.get("system-text") or
                           (e.tag == "direction" and e.find("direction-type/metronome") is not None)]:
                    bar.items.remove(el)
                    for st in el.findall("staff"):
                        el.remove(st)
                    el.set("system-text", "yes")
                    found.append(el)
        if not found:
            continue
        for parts in groups:
            if not parts:
                continue
            top = parts[0]
            if top.bars[g] is None:
                top.bars[g] = B.rest_bar(top.staves, B.bar_length(times[g], D), D)
            for el in reversed(found):
                top.bars[g].items.insert(0, copy.deepcopy(el))


def limit_wedges(parts: list[OutPart], max_bars: int, stats: Stats) -> None:
    """Drop hairpins that span more than max_bars bars (a misread pairing: Audiveris
    joins a start with a far-away stop) and starts/stops without a partner."""
    for p in parts:
        open_: dict[tuple[str, str], tuple[int, etree._Element, etree._Element]] = {}
        bad: list[tuple[int, etree._Element, etree._Element]] = []
        for g, bar in enumerate(p.bars):
            if bar is None:
                continue
            for el in bar.items:
                if el.tag != "direction":
                    continue
                for w in el.findall("direction-type/wedge"):
                    key = (w.get("number", "1"), el.findtext("staff", "1"))
                    if w.get("type") in ("crescendo", "diminuendo"):
                        if key in open_:
                            bad.append(open_.pop(key))
                        open_[key] = (g, el, w)
                    elif w.get("type") == "stop":
                        start = open_.pop(key, None)
                        if start is None:
                            bad.append((g, el, w))
                        elif g - start[0] > max_bars:
                            bad += [start, (g, el, w)]
        bad += open_.values()
        for g, el, w in bad:
            dt = w.getparent()
            dt.remove(w)
            if not len(dt):
                el.remove(dt)
            if el.find("direction-type") is None and el in p.bars[g].items:
                p.bars[g].items.remove(el)
            stats.wedges_dropped += w.get("type") != "stop"


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


def written_key(concert: int, chromatic: int) -> int:
    """Key signature of a part whose written pitch is `chromatic` semitones above sounding."""
    shift = (-chromatic * 7) % 12
    f = concert + (shift - 12 if shift > 6 else shift)
    return f - 12 if f > 7 else f + 12 if f < -7 else f


def write_score(parts: list[OutPart], times: list, credits: list[T.Line], D: int,
                beam: bool = True, stats: Stats | None = None,
                song_key: list[str | None] | None = None) -> etree._Element:
    """song_key: the concert key (fifths) of every bar from the song's `key` row, written into
    every pitched part in its own transposition."""
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
        retyped, dropped = B.fix_graces(p.bars)
        if stats is not None:
            stats.graces_retyped += retyped
            stats.graces_dropped += dropped
        for g, bar in enumerate(p.bars):
            n = B.dedupe_chord_marks(bar)
            if stats is not None:
                stats.chord_marks_deduped += n
            if beam:
                n = B.auto_beam(bar, times[g] if g < len(times) else None, D)
                if stats is not None:
                    stats.beamed += n
            for el in bar.items:
                if "system-text" in el.attrib:
                    del el.attrib["system-text"]
                    # one copy per output file (vocal score); a merge keeps the first
                    el.set("system", "only-top")
                if el.tag == "direction" and p.staves > 1 and el.find("staff") is None:
                    etree.SubElement(el, "staff").text = "1"
    for k, p in enumerate(parts, start=1):
        part = etree.SubElement(root, "part", id=f"P{k}")
        state_key, state_time, state_clefs = None, None, {}
        state_tr = (0, 0, 0)
        first_clefs = next((b.clefs for b in p.bars if b is not None and b.clefs), {})
        perc = bool(first_clefs) and all(c and c[0] == "percussion" for c in first_clefs.values())
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
            if song_key and g < len(song_key) and song_key[g] is not None and not perc:
                tr = parse_transpose(p.changes[g].get("transpose")) if g in p.changes else state_tr
                key = str(written_key(int(song_key[g]), tr[1]))
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
            if g == len(p.bars) - 1:
                # final barline, as in the truth scores (MuseScore adds none on import)
                bl = etree.SubElement(m, "barline", location="right")
                etree.SubElement(bl, "bar-style").text = "light-heavy"
    return root
