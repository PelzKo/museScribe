# Dynamics, hairpins and low piano notes: investigation and proposals

Investigated 2026-11-15. Start with the information already being read: recover dynamic text that is
discarded during classification, retain the owner of an Audiveris mark, and use a second reading to
repair individual keyboard notes. For Ghost, read the relevant symbols directly from the PDF.

These are proposals supported by source inspection and local diagnostic experiments. **No production
pipeline change has been accepted or applied.** A successful source probe is not an all-song benchmark gain.

## 1. What I checked

- Read [IMPROVEMENTS.md](IMPROVEMENTS.md), [ERRORS.md](ERRORS.md), the rejected experiments, correction
  conventions, and the relevant pipeline, extractor and metric code.
- Compared the new Anastasia **5A** truth with run `20261114-102221`: **14 parts, 275 truth notes**.
  The truth is `05a_Undescore_after_In_my_dreams.mscz`, SHA-256 prefix `ce0db521887d`.
  Its output manifest records code `e48f910`; the code inspected here is `8154724`.
- Reviewed the detailed `r69-a` error data for Anastasia **1, 2, 3, 4, 4A, 5** and Ghost
  **1a, 4, 5, 11a, 13, 20**. Ran additional note and hairpin diagnostics on their current truth exports
  and saved outputs: **188 mapped parts / 40,576 truth notes including 5A**.
- Inspected 5A's original Keyboard 1, Keyboard 2, Cello, Horn and percussion pages, homr crops,
  Audiveris exports, `.omr` objects and cached OCR. Checked Ghost vector symbols and selected piano
  passages against both truth and output. This is a corpus-wide machine comparison with focused visual
  checks, not a visual audit of every printed mark in all thirteen songs.

The older docs still say 5A has no truth; that is now stale. The Anastasia piano reduction remains excluded
by the workbook. The new low-note evidence in 5A concerns **Keyboard 1**, which plays piano in bars 16–21.
Sparse truth parts and the missing source pages documented elsewhere still affect the older totals.

### Dynamics and hairpins across all truth songs

These are **differences from `error_report.py`, not edit-penalty actions**. The first twelve rows come
from the saved `r69-a/errors.json`; 5A is a fresh report. They should not be added to the historical
9,111-action reference. A wrong token can also appear as a missing/made-up pair when its position differs.

| Show | Song | Dynamics differences | Hairpin-start differences |
|---|---|---:|---:|
| Anastasia | 1 | 33 | 23 |
| Anastasia | 2 | 15 | 17 |
| Anastasia | 3 | 207 | 153 |
| Anastasia | 4 | 298 | 226 |
| Anastasia | 4A | 6 | 4 |
| Anastasia | 5 | 103 | 79 |
| Anastasia | **5A** | **19** | **10** |
| Ghost | 1a | 11 | 1 |
| Ghost | 4 | 31 | 18 |
| Ghost | 5 | 34 | 24 |
| Ghost | 11a | 8 | 4 |
| Ghost | 13 | 10 | 6 |
| Ghost | 20 | 37 | 11 |

The older detailed data contains **30 wrong dynamic tokens**, beyond missing, extra and misplaced marks.
Examples include `f` for `mf`, `ff`/`fff` for `sffz`, and `ppp` for `mp` in Ghost 11a Cello bar 8 and
Ghost 13 Cello bar 154. Recovering missing symbols alone will not address these substitutions.

## 2. What 5A reveals

The fresh report has **61 differences**, including **19 dynamics and 10 hairpin-start differences**.
They account for 29/61 of the reported differences; wrong hairpin ends add further work that is not scored.

| Passage | Observed problem | Source evidence / implication |
|---|---|---|
| Cello, Clarinet 2, Horn, bar 2 | `ppp` instead of `mp` | The page prints `mp`. Treat compound dynamics as a recognition problem; do not globally rewrite `ppp`. |
| Cello and Bass, bar 18 | `fz` instead of `f` | Another token substitution; adding a second dynamic would leave a conflict. |
| Horn bar 16; Horn, English Horn and Trombone bar 18 | Missing `mf` / `f` | Correct text atoms already exist in the `.omr`, but are classified as lyric syllables and do not reach dynamic placement. |
| Keyboard 1, bars 3, 16 and 21 | All three hairpins missing | All three are present as `.omr` wedges. Keyboard recovery is disabled in `engine.assemble`. |
| Keyboard 2, bars 1 and 21; percussion, bars 1 and 17 | Four more hairpins missing | Corresponding wedges also exist in the `.omr`. Thus **seven of the eight missing hairpins** in 5A already have source detections. Routing and timing still need validation. |
| Keyboard 2, bar 1 | `mf` one beat early | The printed quarter rest is absent from the output's opening sequence. C5 and E-flat5 move from beats 2/3 to beats 1/2; moving only `mf` would hide the underlying rhythm error. |
| Keyboard 1, bars 18 and 19 | A-flat1 missing from the lower octave dyads | Audiveris has both A-flat1 notes; homr loses them. |
| Keyboard 1, bar 20, beats 1 and 3 | F1 becomes B-flat1 and G1 | Audiveris has F1 in both places. These are local head/pitch failures, not a missing clef for the entire passage. |
| Keyboard 1, bar 18, beat 2 | E-flat5 missing from the right-hand chord | The same passage also needs a non-ledger chord repair. Audiveris has this note too. |

Two particularly useful checks:

1. **Existing alternative reading:** comparing note edit costs for Keyboard 1 bars 16–21 gives output
   costs `0, 0, 2, 1, 2, 0`; the corresponding Audiveris piano bars cost `0, 0, 0, 0, 0, 0`.
   All five note errors in bars 18–20 are therefore recoverable from an existing reading in this sample.
   This is a selected-passage diagnostic, not proof of a general replacement rule. As a counterexample,
   Keyboard 2 bar 1 costs **2** in the output and **3** in Audiveris: blindly preferring Audiveris loses there.
2. **Unscored ends:** pairing 5A hairpins by staff and number finds **six with the same start but a different
   stop**: Violin 1 twice, Violin 2, Horn, Trumpet and Keyboard 2. For example, Keyboard 2's crescendo
   starts at bar 16 beat 2 in both files, but stops at offset 2 in bar 17 instead of offset 3 (the bar end).
   Horn's corresponding stop is offset 1 instead of 2.5. Offsets here are quarter-note units from bar start.

## 3. Proposed improvements, in implementation order

### C1. Give dynamics their own text-classification path

**First small experiment; extends D4 with a concrete source of already-read marks.**

`text.is_words()` requires a run of at least two letters. Later, `text.classify()` rejects short lines
made solely of lyric fragments. Consequently a standalone `f`/`p` fails the first condition, and an
`mf` read as a lyric syllable can fail the second. `assemble.place_text()` knows how to turn a dynamic
token into `<dynamics>`, but that code only receives classified words. The same problem can affect
single-letter tokens successfully added by `ocr.supplement()`.

In the 5A probe, Cello, Horn and English Horn each have correct `mf` and `f` atoms marked `Lyrics`.
`[to] 16 mf` is split at the cut mark, but the remaining lyric-typed `mf` still fails classification.
Trombone also shows a dynamic joined to nearby bar-number/noise text. None of these tested dynamic-bearing
lines survives as a dynamic word.

Proposed change:

- Collect dynamic candidates from **individual text atoms before prose/lyric grouping**, preserving
  their boxes, source role and confidence. Use a dedicated result list, rather than relaxing `is_words()`
  for all text.
- Validate the dynamic vocabulary and position/size relative to the owning staff. Extract a dynamic
  next to a cut/bar number without consuming the number. On vocal pages, require extra visual evidence
  before converting a real lyric syllable such as `p` or `sf`.
- Merge competing readings of the **same physical mark**. A correct `f` candidate should challenge an
  `fz` reading at that location, not create simultaneous `f` and `fz` directions.
- Expand the vocabulary deliberately: the current OCR regex omits `sffz`, `fz`, `rfz`, `pppp`, etc.,
  although some occur in the truths. Keep word modifiers such as `più` separate from the symbol.

Test the five 5A parts above first, then every truth song. Measure rescued correct tokens, conflicts,
and false candidates separately. This is more specific than lowering OCR confidence across the page.

### C2. Preserve ownership, then enable keyboard and percussion mark recovery

**Extends D2/D3; the missing prerequisite is visible in the cached `.omr`.**

`layout._parse_sheet()` reads the relation graph for chords/articulations, but reduces a dynamics/wedge
object to shape, bounding box and grade. Its `Mark.staff` remains zero. `vocal._owner()` then reconstructs
ownership from vertical distance; its special grand-staff handling depends on `piano_group`, which is
set for piano reductions, not generally for keyboard parts. This is too weak for a conductor book.

In 5A Keyboard 1, the `.omr` contains seven dynamics above grade 0.8. Their `chord-dynamics` relations
identify **three on the discarded cue staff and four on the retained piano staves**. There is also an
unlinked, low-grade `p` candidate near the end. This directly demonstrates why keeping every high-grade
mark is insufficient, and why the relation graph is useful.

Proposed change:

- Preserve original staff ID, chord/voice relation, object ID, relation confidence and wedge endpoint
  relations where present. Use kept/dropped staff membership before geometric fallback. A relation is
  evidence, not an infallible assignment: check its geometry and whether its chord survives cue removal.
- Distinguish a mark's **source owner**, its musical scope (part or one hand), and its exported display staff.
  In 5A Keyboard 1 the truth puts the bar-16 hairpin on staff 2, while its `mf` is on staff 1. A blanket
  “put everything on staff 1” rule would introduce discrepancies.
- On percussion, carry ownership through the instrument split: the two missing 5A wedges belong to the
  drum staff; the later `f` on the upper staff belongs to Timpani.
- Add supported missing marks and reconcile overlapping detections. Do not simply invoke
  `vocal.place_marks()` unchanged: it strips the existing kinds before rebuilding them.

Pilot: recover the seven detected-but-missing 5A hairpins, exclude all three cue dynamics, and preserve
the valid existing marks. Then test the large song-3/4 keyboard and percussion clusters. This addresses
the failure mode behind R40 rather than repeating its rejected blanket placement.

### C3. Read Ghost dynamic glyphs and hairpin strokes directly

**D1 remains strong; use font-specific mappings and staff ownership.**

A small extraction using only the exact `EngraverFontSet` font finds 9 dynamic candidates in Ghost 13
Cello, 16 in Ghost 5 PianoReduction, 12 in Ghost 4 PianoReduction, 25 in Ghost 20 PianoReduction, and 7
in Ghost 5 Utility. These are whole-page candidates, including other staves, not counts of recoverable
errors. Compound symbols can be single glyphs (`P` for `mp`, `F` for `mf`).

The font restriction matters: a trial accepting every font beginning with `Maestro` also matched an `s`
in ordinary `MaestroTimes-BoldItalic` text in Ghost 13 Cello. Likewise, the existing vector articulation
reader treats `ß` as an accent/staccato candidate while the external glyph map also associates it with
`sfz`. Verify each font/code combination with a rendered crop and its placement before assigning meaning.

Build a small verified atlas for the fonts actually in these PDFs. Extract glyph origin, box and font;
group split glyphs where necessary; assign them to a kept staff/part; reconcile with current dynamics.
For hairpins, pair thin strokes with a shared tip and opposite slopes, allowing a small opening at the tip.
Retain both endpoints. Exclude ledger lines, beams, ties, accents and text underlines using geometry and
staff context. Join system-break fragments only when continuation evidence agrees.

Start with Ghost 13 Cello and Ghost 5 Utility before the piano reductions. Keep this inside
`pipeline/vector.py`; the prior poor full-score results of `sheet_reader` are not a reason to replace the
engine or edit that external repository. Its glyph table is a lead, and labels some mappings as guesses.

### C4. Re-read uncertain compound dynamics as complete symbols

**D4/D8, with safeguards suggested by 5A.**

After C1–C3, distinguish “not detected”, “detected but rejected”, and “wrong token”. Re-read local image
patches for conflicts such as `mp`/`ppp`, `mf`/`f`, `f`/`fz`, and `sffz`/`ff`. Use the full word-shaped
symbol, with enough lateral padding to include an `m`, initial `s`, or final `z`; a crop centred only on
the detected `p` cannot recover the missing prefix reliably.

Begin with staff-scale-normalized templates from visually verified examples in these books, allowing
scan skew and modest stroke variation. Include hard negatives: bar numbers, lyrics, ledger lines, beams,
ornaments and ordinary italic words. Compare the best and second-best labels, and abstain on ambiguity.
Use the image evidence to propose replacement of a conflicting token. Adjacent dynamics or harmony can
rank a candidate for inspection, but cannot establish what was printed.

Do not require an `.omr`/OCR corroboration for every existing homr dynamic: the 5A `mp` failures show
that these other readers can also miss a real mark. Do not globally map `ppp` to `mp`, or copy dynamics
between instruments. Those would erase real distinctions and repeat earlier losing experiments.

### C5. Anchor marks to the repaired musical timeline, and score both hairpin ends

**D7 plus M2; recognition and anchoring need separate tests.**

Store page/system/staff, mark box, endpoint coordinates and supporting note/rest IDs until bar cuts,
multi-rest expansion, voice construction and note repairs have settled. Maintain explicit coordinate
transforms for page, crop and resized image coordinates. Then attach the mark to the final timeline.

Use notehead columns **and rests**, across both hands when the mark applies to the piano as a whole.
A missing opening rest must not shift every subsequent mark, as in 5A Keyboard 2. Endpoints need release
times, bar ends and supported intermediate offsets as candidates, not just note attacks. The 5A Horn
truth's offset-2.5 stop is a useful test of that distinction. Keep visual horizontal offsets separate
from musical onset; MusicXML distinguishes these concepts in its
[offset definition](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/offset/).

`assemble.place_dynamics()` currently refuses another dynamic anywhere on the same staff in a bar if
one already exists. Change that to conflict detection near the candidate's onset and image box: `p`
early in a bar and `f` later are different legitimate events. The text path's same-token check is also
bar-wide, so it needs the same scrutiny.

For evaluation, pair start/stop objects and compare `(scope, kind, start time, end time)`. Normalize
equivalent bar-end/next-bar-start positions and ignore arbitrary numbering. Count a wrong span once,
not as separate deletion and insertion of its ends. Report orphan starts/stops separately. The
[MusicXML wedge definition](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/wedge/)
provides explicit start types, stops and numbering for overlapping wedges.

Add this measurement and rebaseline before judging endpoint work. Until then, retain a separate endpoint
report and the six 5A examples. Merely increasing `max_wedge_bars` is not an endpoint solution; R16 lost.

### C6. Treat written cresc./dim. as staff expressions with optional spans

The word form needs its own path alongside `p`/`mf` and graphical hairpins. `assemble.TEMPO_TERMS`
currently includes `cresc`, `dim`, `decresc`, `poco` and other expression words. A mark above the top staff
can therefore become system text. Anastasia keyboards additionally use `words: drop`, which deletes
word directions at the end of the pipeline.

Classify `cresc.`, `dim.`, `decresc.`, `poco a poco cresc.` and modifiers as expressions before deciding
tempo/system scope. Use the source staff and geometry rather than the word `poco` alone. Preserve the
printed word form; do not automatically replace it with a wedge or invent an ending dynamic.
When a continuation line is printed, retain it as a paired span: MusicXML has
[dashes specifically for expressions such as cresc. and dim.](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/dashes/).
Keep cue/patch-label filtering separate from expression handling, and test the intended keyboard output
convention before changing `words: drop` behavior.

This is measurable once M4 is added: the recent report counted 62 truth `<dashes>` elements and zero in
the outputs. They are element counts, not necessarily 62 complete spans. The detailed error data also
contains `cresc.` both as missing part text and as extra system text, so deduplication and scope matter.

### C7. Repair low notes/chords using local source evidence

**K1, narrowed to the demonstrated failures before attempting wholesale per-staff rebuilding.**

The pitch audit below compares truth notes with exact `(staff, onset, MIDI pitch, duration)` matches after
the benchmark's bar alignment and pitch-shift handling. “Below C2” means MIDI <36; it is a convenient
low-register proxy, not an actual ledger-line detector. Missing matches include rhythm/voice/alignment
errors, so these are not all wrong pitches or independent edit actions.

| Keyboard/piano group | Below-C2 notes without exact match / truth notes | C2-and-higher notes without exact match / truth notes |
|---|---:|---:|
| Anastasia, including 5A | 111 / 304 (36.5%) | 444 / 9,078 (4.9%) |
| Ghost | 78 / 413 (18.9%) | 422 / 5,220 (8.1%) |
| Both | **189 / 717 (26.4%)** | **866 / 14,298 (6.1%)** |

Concentrations include Anastasia Keyboard 1: song 3 **28/138**, song 4 **41/88**, song 5 **34/63**,
5A **4/7**; Ghost Piano/Klavier: song 4 **9/65**, song 5 **19/60**, 11a **6/10**, song 20 **44/278**.
These diagnostics support targeting low notes, rather than a generic instrument-range check.

At a suspicious onset, compare homr's heads with Audiveris's retained-staff chord, head positions and
exported pitches. Match by page x, staff and stem group; confirm pitch against local staff-line geometry,
the clef at that x, the key and local accidentals. Prefer a missing head or pitch correction that retains
the trusted duration/voice. Do not replace the entire two-hand bar just because one bass head is missing.

The 5A `.omr` retains the required lower heads as well as the correct Audiveris export. Its staff-position
values reach `12` below the middle line for F1. Detecting the expected octave partner is a useful trigger,
but only add it when the image or independent source has a head there: an octave pattern is not proof.
Preserve spelling and accidental carry; pitch-class agreement alone is insufficient.

Pilot on 5A bars 18–20, then Anastasia 1 Keyboard 1 bars 1–2, song 3 bars 28–32, song 4's low-note
clusters, and song 5. Require donor superiority by evidence available at transcription time. The
selected-passage result of five available corrections is an upper bound for that sample, not a trained rule.

### C8. Make crop coverage depend on symbol extent; retry suspicious successful crops

`engine._crop_jobs()` uses fixed margins, and `_run()` retries `[5, 4, 3]` only when the recognizer reports
failure. A syntactically valid crop with several wrong bass notes therefore gets no second look.

In 5A Keyboard 1's second system, the bottom staff is at approximately y=2362.45 and the five-interline
crop ends at y=2447.14. The lowest detected chord reaches y=2446: approximately **one pixel of clearance**
in layout coordinates. The actual crop is 2152×464. The image shows the low notes very close to the bottom.
This is evidence of fragile coverage, **not proof that clipping caused every error**: A-flat1 is farther
from the edge, and the final F1 is read correctly.

Extend the boundary to include detected head/ledger/stem extents plus a safety margin. Estimate staff
lines at the note's x on skewed scans. If `.omr` also misses the lowest head, use connected components
and ledger-line evidence below the staff to propose a larger crop. Respect neighboring staff ownership.
Separate mark-reading regions from note-reading regions so a distant dynamic need not enlarge every note crop.

Try an asymmetric larger bottom margin, or a separate bass-staff crop retaining its clef and rhythm
context, only on suspicious systems. Use a quality trigger such as source head-count disagreement or a
head near an image edge, even when homr exits successfully. Compare the resulting candidates locally;
retain the original if the new crop loses upper notes, voices or timing. This experiment has **not** been
run through homr here. It differs from the previously rejected global margin-3 setting.

### C9. Start Ghost pitched-note work with a verifier, not a complete replacement reader

**K2/K3 can begin more narrowly than building every rhythm and voice from scratch.**

The existing `scripts/pdf_truth_check.py` already derives written pitches from vector head positions,
staff lines, clefs and accidentals. With the workbook's key changes, its per-staff pitch multisets match
the truth on both piano staves in Ghost 5 bars **19–22 and 25–27**.

These cover two different faults visible in the output:

- Bar 19 has one E1 read as A1; bars 20–22 have their four E1 notes per bar read as B1. The PDF retains
  unambiguous notehead positions for all of them.
- Bars 25–27 have the right-hand pitches interpreted under the wrong clef, producing a consistent
  diatonic displacement. This needs local clef-state repair before individual-note correction.

Promote the useful parts of that checker into a verifier which aligns vector head columns with the
existing timeline. Correct a pitch or propose a missing chord member only when the head/staff/clef
association is secure. For a run of consistently displaced notes, first check the clef state. Keep
rhythm and voice assignment from the stronger source until there is evidence to replace them.

The current checker is not a production reader: the complete Ghost 5 check still differs in cue/repeat
passages around bars 3–7 and in bars 34–35; it compares pitch multisets, not onsets, durations or voices.
Cross-staff notes, courtesy clefs, accidentals carried through ties, ottava/patch transposition and cues
need explicit treatment. Use these failure cases as negative tests when extracting the verifier.

## 4. How to turn the proposals into accepted changes

First create a current reference that includes **all thirteen truth songs**. Reassemble the twelve older
songs from `h71` and 5A from `20261114-102221`, using the same current code and settings for the reference
and each candidate. The historical 9,111-action total excludes 5A and must not be used as the new denominator.
Record hashes of truth files, workbook, show configuration and metric code; the probe artifacts already
record the input hashes used in this investigation.

Recommended sequence: **C1 → C2 → endpoint/expression measurement → C3 → C7 → C8/C9 → C4**, with C5/C6
implemented against the expanded measurement. C1 and C2 exploit detections already paid for; C7 has a
small, concrete donor test. Build new scan detectors only for the residual cases. For missing hairpins
such as 5A Cello bar 16, a staff-aware line-pair detector remains a justified later experiment (D5).

For every candidate, retain a short diagnostic breakdown:

| Check | What it prevents |
|---|---|
| Missing / extra / wrong-token / wrong-onset dynamics separately | Trading omitted markings for conflicting or incorrect ones |
| Hairpin kind, start, stop, owner and unpaired endpoints | A correct start hiding a wrong-length or misrouted crescendo |
| Written expression text, scope and paired dashes | Losing cresc./dim. while improving graphical wedges |
| Pitch and missing-head errors by **actual ledger depth**, clef and hand | A higher global note score hiding unchanged deep-bass failures |
| Original page → raw reader → retained candidate → final output provenance | Confusing a recognition failure with a classifier, routing or later-filter failure |
| Per-part action totals and selected printed-page checks | Repeating prior large regressions on cue-rich keyboards and percussion |

Use the existing acceptance rule after rebaselining: total actions must fall by at least one and no part
may worsen by more than half the total gain. Sparse truth parts remain in the score; do not “fix” them
by dropping supported marks. Do not turn input/metric changes into claimed pipeline gains. Reassembly is
enough for cached-source recovery; crop changes require new recognizer runs in separate experiment folders.

Keep meaningful regression examples: 5A's lyric-typed `f`/`mf`, cue-staff dynamics, left-hand hairpin,
missing opening rest, repeated dynamic within a bar, six wrong stops, and A-flat1/F1 notes; Ghost's
text-font `s` false match, compound dynamic glyphs, E1 repetitions and clef-change passage. Validate
the MusicXML-to-MuseScore round trip for spans and display staff, as well as XML event equality.

## 5. Reproduction and local evidence

Generated diagnostics are under `results/` (gitignored); the production code and truths were not changed.

```bash
source ~/.local/share/omrbench/env.sh
python scripts/error_report.py anastasia --run 20261114-102221 --songs 5A \
  --out results/errors/codex-5A-20261115
python results/analysis/codex-20261115/audit.py
python results/analysis/codex-20261115/probes.py
python scripts/pdf_truth_check.py ghost 5 PianoReduction
```

- [Fresh 5A errors](../results/errors/codex-5A-20261115/errors.md) and
  [machine-readable locations](../results/errors/codex-5A-20261115/errors.json).
- [Corpus note/span audit](../results/analysis/codex-20261115/audit.json): low-register exact-match
  counts and endpoint candidates. Keyboard parts use benchmark bar alignment; other parts use ordinal
  bars for the span diagnostic, so inspect those candidates before treating them as errors. The six
  5A stop discrepancies quoted above were checked individually.
- [Focused source probes](../results/analysis/codex-20261115/probes.json): donor note costs, crop extent,
  discarded dynamic text, chord ownership, vector candidates, pitch checks and input hashes.
- [Full Ghost 5 vector-check output](../results/analysis/codex-20261115/ghost5-vector-check.txt), including
  the checker's remaining mismatches.

Primary implementation touchpoints: `pipeline/layout.py:_parse_sheet`, `text.py:classify`,
`ocr.py:supplement`, `assemble.py:place_text/place_dynamics`, `vocal.py:_owner/place_marks`,
`engine.py:_crop_jobs/_run/assemble`, `vector.py:read_marks`, and `musicxml.py:part_staves` plus
`metrics/edits.py` for the expanded measurement. This complements D1–D8, K1–K4 and M2/M4/M5 in
[IMPROVEMENTS.md](IMPROVEMENTS.md), with specific failure cases and narrower first experiments.
