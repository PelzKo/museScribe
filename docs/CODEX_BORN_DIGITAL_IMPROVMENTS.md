# Born-digital improvements: what to read next, what worked, what did not

Investigation, 2026-11-15. Scope: **Anastasia PianoReduction and all nine Ghost books**.
Companion to [IMPROVEMENTS.md](IMPROVEMENTS.md), using the same backlog / evidence / rejected-trial structure.
The spelling of this filename follows the request.

**There is substantially more usable notation in these files.** A small direct reader recovered
**1,510 notes in 506 bars** of six Ghost Cello/Bass excerpts, with zero note-edit actions against
the current truths on those accepted bars. It derived pitch, onset and duration from PDF glyphs and
paths, with workbook key/meter context. It abstained on another 65 printed bars. This establishes a
useful limited reader, not a complete replacement engine or a measured 1,510-action improvement.

The other strong opportunity is direct dynamics and hairpins. Their extraction is straightforward;
**staff ownership and the source-to-output bar mapping are the harder problems**. Naive placement and
pitch substitution still cause regressions. No production changes were accepted or applied here.

## 1. Rules for every change

1. **Read the file, not a rendering.** Use decoded character codes, font resources, glyph origins,
   text spans and vector path coordinates. No homr, Audiveris, OCR, image templates, pixel segmentation
   or learned image recognizer supplies the new evidence in this investigation.
2. **Enable capabilities per page and feature.** A usable text layer alone does not establish readable
   notation. Require a supported music font/encoding for glyphs, staff geometry for pitch, and suitable
   paths for hairpins. Unknown encodings and ambiguous groups abstain. Scans and OCR overlays provide
   no direct-notation evidence; existing handling of those pages stays outside this work.
3. Keep `(PDF hash, page, font resource/code or path index, coordinates, system, source staff,
   printed bar)` with every candidate. Preserve its connection to the assembled bar through cuts,
   multirest expansion, inserted bars and instrument splits. An output array index is not a source bar ID.
4. Distinguish **extracted objects**, **correct musical assignments**, **local metric simulations** and
   **accepted pipeline gains**. Counts below are labelled accordingly; do not add them together.
5. Before accepting an implementation, reassemble a fresh reference and candidate with the same current
   truth/workbook/metric inputs. Follow [IMPROVEMENTS.md §1](IMPROVEMENTS.md): score every configured truth
   song of both shows, total drops by at least one, and no part worsens by more than half the total gain.
   Use cached work where available, including the separate 5A work directory; no new OMR is needed to
   evaluate a direct-PDF assembly addition. Do not edit truths to make an experiment pass.
6. Score complete hairpin/slur spans before accepting span work. The **metric snapshot used here**
   counts starts, not complete spans. A correct start does not validate an extracted ending,
   continuation, display staff or playback behavior.

The experiments use frozen **`r69-a` output files against current truth exports**, not a fresh reference.
The historical 9,111 total is therefore not their denominator. Mark and pitch-substitution trials keep
the baseline metric alignment fixed and score matched bars with `_items_cost` / `_notes_cost`.
They omit insertion/deletion and other category changes; they are not full benchmark runs.
Written-to-sounding calibration uses the truth part's declared transposition for these diagnostics;
a production reader must obtain instrument state from the workbook/source, never from the truth.

**Metric-version note:** during the final check, concurrent workspace changes added endpoint, grace,
lyric and ornament scoring. They were left untouched. To preserve comparable measurements, the probe
loads `musicxml.py`, `metrics/notef1.py` and `metrics/edits.py` from commit
`8154724410854eb45b4d06c0a33adbff97fc8e18` into a separate research package under `results/`.
All numbers here use that older metric. Rebaseline with the expanded metric before implementation;
do not interpret the start-only hairpin trial as an endpoint-score improvement.

## 2. Where to start (ranked)

| rank | direction | evidence from this investigation | items |
|---|---|---|---|
| 1 | Source bar/staff identity plus direct dynamics and hairpins | Exact glyphs/strokes exist; Ghost 13 Bass pilot rescues four dynamics and two hairpin starts; broad placement still loses dynamics | B1–B3 |
| 2 | Petrucci support for Anastasia | Existing articulation reader returns **zero bars on 62 examined pages**, despite 11,887 ordinary notehead glyphs; current barline-width rule also fails | B4 |
| 3 | Direct notes and rhythm on supported simple staves | **506/506 accepted bars**, 1,510 notes, zero note actions; 65 abstentions | B5 |
| 4 | Piano pitch/clef verification | Narrow pitch trial saves 14 local actions in Ghost 5 Piano and 28 in Ghost 20 Piano; broad deployment fails | B6 |
| 5 | Barline types, curves and remaining text semantics | Their primitives are already present; useful extensions, not yet measured here | B7–B9 |

Suggested order: **B1 → B2/B3 → B4 → B5 → B6 → B7/B8/B9**. B1 is a prerequisite for dependable
placement, not a large new recognition project. Keep the first integration to supported instrumental
staves; extend to cue-rich utility books, two-hand piano and singers with explicit ownership rules.

## 3. Open items

### Eligibility, fonts and musical structure

| # | idea | evidence | expected / effort |
|---|---|---|---|
| B1 | **Preserve source system/staff/bar identity; gate direct reading per page.** Reuse `pdfkind.classify_page`, then expose separate glyph, path and staff-geometry capabilities. Group connected staves before numbering measures. Carry the source interval into final assembly rather than joining by ordinal bar. | Ghost has **8 scan pages and 68 text pages** inside the target books. Ghost 13 Cello output bar 34 aligns to truth bar 39; output 63 aligns to truth 68. The failed pitch trial looked up printed bars 34/63 instead. Ghost 11a Piano also drifts by two bars. | Required infrastructure; medium. No standalone action claim. |
| B4 | **Add a verified Petrucci font profile and geometry rules.** Separate music symbols from ordinary text; normalize subset prefixes but retain encoding/resource identity. Add Petrucci heads, rests, clefs, time digits, articulations and dynamics deliberately. | All 316 Anastasia notation pages are vector pages. `vector.read_marks()` accepts only EngraverFontSet. Its `GLYPHS`, repeat table and time-signature font selection also omit Petrucci. On page 7, current `read_systems()` produces one bar per staff and no times; connected piano geometry exposes 3, 2 and 4 bars in the three systems. | Broad enabling change; medium. Anastasia piano itself is excluded from the normal benchmark, so judge vocal/structure effects and use an explicit piano diagnostic. |

Do not generalize Ghost's stroke widths. On Anastasia page 7, **0.68256 pt** strokes include staff
lines, stems and barlines. `read_systems()` rejects vertical widths between 0.5 and 1.0 pt to exclude
Ghost stems; that excludes these barlines too. A line spanning both piano staves is strong barline
evidence regardless of this width. Vocal staves may be barred separately. Retain thin/thick members
and repeat dots before collapsing a barline cluster.

Do not use Unicode alone as a music-symbol name. The sampled Ghost EngraverFontSet resource has a
custom `/Encoding` and `/ToUnicode`; Anastasia Petrucci uses `/MacRomanEncoding` without `/ToUnicode`.
The extracted `F` is a dynamic glyph, not the letter F. Keep font resource identity and the original
code/glyph ID so that a later font substitution cannot silently change its meaning.

### Dynamics and hairpins

| # | idea | evidence | expected / effort |
|---|---|---|---|
| B2 | **Read supported dynamic glyphs directly.** Initial table: `p→p`, `P→mp`, `F→mf`, `f→f`, `ƒ→ff`, `π→pp`, `∏→ppp`, scoped to EngraverFontSet/Petrucci. Match competing readings of the same physical symbol before adding another direction. | Full-book inventory: **1,553 Ghost + 565 Anastasia candidates** from this seven-token table. Ghost 4 Cello bar 16 has a recoverable `mp`; Ghost 13 Bass has recoverable `f` at 2/90 and `mp` at 40/162. | High-priority source; small reader, medium integration. No defensible corpus-wide gain yet. Extends D1/C3. |
| B3 | **Read hairpins as paired vector segments, preserving both endpoints.** Start with two stroked lines in one path, a common tip, opposite slopes and horizontal extent. Then investigate separate-path and system-break fragments. | **839 Ghost + 453 Anastasia paths** meet the conservative geometric filter. Ghost 4 Violin/Cello bar 39 and Ghost 13 Bass bars 68/180 yield missing starts. The prototype stores path index and both x endpoints. | Small extractor, medium routing/span work. Ghost broad start-only simulation: **49→43** local actions. Not an accepted gain. |

The mark simulation adds only before the first printed head/rest, at onset zero, and only when that
category is absent from the output bar. It is intentionally a weak placement baseline. Across the
32 tested Ghost instrumental/piano comparisons, dynamics worsen **91→95** while hairpin starts improve
**49→43**. In five Anastasia piano diagnostics, the corresponding figures are **33→32** and **15→17**.
This is evidence against “read every glyph, then put it at the start of the nearest bar.”

Implement ownership before widening coverage: retained versus cue staff, piano grand staff versus
vocal staff, and a whole-part expression versus a mark specific to one hand. The prototype assigns
between-staves marks to the upper piano staff and uses proximity elsewhere; that is a hypothesis,
not a verified universal convention. Ghost 5 Utility's successful `mf`/hairpin additions are on staff 2.
Do not enforce a blanket upper-staff rule on marks printed below the lower staff.

For onset placement, use the direct note/rest columns and their derived timing where available.
Carry endpoint positions until the final timeline is known. Do not infer beats by proportional
horizontal distance: engraving is not a linear time axis. Record direct-PDF provenance so R42's
cross-book lone-mark filter does not silently discard supported additions; test that exemption too.

Compound dynamics remain open. The existing reader treats `ß` as accent/staccato, while earlier
investigation found a conflicting `sfz` interpretation. This experiment **excludes it**, along with
unverified compound codes. Resolve font/code/position using the embedded glyph and page context;
do not globally reinterpret it or match every font beginning with `Maestro` (which includes text fonts).

### Pitched notes and rhythm

| # | idea | evidence | expected / effort |
|---|---|---|---|
| B5 | **Build a direct reader in supported increments.** Staff-relative head origin plus local clef/key/accidentals gives pitch. Half/whole head code, stem connection, beams, flag and augmentation dot give duration. Accumulate note/rest durations for onset; require the meter to fill. | Standalone prototype: 506 accepted monophonic bars, 1,510 notes, all exact under the note metric. It used no output timeline for event construction or acceptance. | Strong feasibility result; medium for production-quality simple staves. These passages are already mostly correct in the baseline, so zero donor error is not equivalent to a large gain. |
| B6 | **Use verified direct head/clef evidence for piano corrections.** Preserve rhythm initially; require source bar identity, correct staff/clef/accidental state and supported head-to-column association. Treat a displaced passage as a possible clef error before changing many pitches. | Ghost 5 Piano bars 19–22: **13→0** note actions from E1 heads; bar 29 adds another gain in the narrow trial. Ghost 4 Piano bar 37: broad trial **13→0**. Ghost 20 Piano narrow trial **146→118**, but four bars worsen. | Promising localized gains, not deployable as tested; medium. Extends K2/K3/C9. |

Two pitch experiments were tested on equal-head-count staff-bars:

- **Broad:** assign source pitches in x/y order to output events ordered by onset/descending pitch.
  Across 32 Ghost comparisons, local note actions rise **549→1,057**. Anastasia's five diagnostic
  piano parts rise **267→547**. Chord ordering, voices, bar drift and instrument state make this unsafe.
- **Narrow:** require exactly one distinct excess pitch and one distinct missing pitch, equal
  multiplicity, and a change smaller than an octave. Replace that pitch while preserving event timing.
  Ghost improves **549→542**, but Ghost 4 Utility worsens **85→106**: this fails the per-part rule even
  before a full benchmark. Anastasia worsens **267→408**. Equal counts and a small interval are insufficient.

The existing `scripts/pdf_truth_check.py` is useful scaffolding, not a production pitch decoder.
It uses nearest-staff ownership, guessed carried accidentals from the previous bar, fixed font/size
thresholds, and a special “last two staves” assumption. Its key handling also needs instrument changes.
Retain its successful cases, but replace the guess about an accidental continuing across a barline
with an actual tie connection. In a cross-staff chord, stem/beam membership must supplement head y.

The direct rhythm pilot is deliberately monophonic. It rejects ambiguous stems, multiple nearby
heads, unsupported multiple dots, head-count disagreement and bars that do not fill the meter.
Full polyphony still needs stem/beam components, chord grouping, rests per voice, tuplets, grace notes,
cross-staff notation and cue policy. “Adds up to 4/4” alone cannot validate those cases. Do not discard
otherwise exact pitch evidence just because the rhythm decoder abstains.

### Other direct information

| # | idea | evidence and next experiment | status |
|---|---|---|---|
| B7 | **Barline types, repeats, multirests and endings.** Preserve line widths, cluster members, repeat-dot positions, number glyphs and bracket paths. Distinguish a start-repeat after the clef from a measure boundary. | Existing vector code largely collapses barline clusters to x coordinates. The structure failures in the trials show why numbers and multirests must be part of the source timeline. Compare extracted double/final/repeat signs against `barlines`/`structure`, separately from mere bar count. | Not scored here; extends S1/S2. Avoid repeating the rejected multi-staff barline replacement. |
| B8 | **Ties, slurs, ottava, tuplets and expression dashes from paths plus text.** Keep Bézier control points, path connectivity and endpoint coordinates, not only bounding rectangles. | `_drawings()` reduces filled curves to bounding boxes; `_ties()` uses proximity and equal-height heads. The source retains more shape information. Pair ties with equal pitches and slurs with actual endpoints; parse ottava text together with line/bracket continuation. | Not scored here; evaluate with the expanded endpoint metric after rebaselining. Extends S6/S9/S11 and M2/M4. |
| B9 | **Use direct text and PDF tags where they carry actual semantics.** Retain font, position, baseline, character order and source role for lyrics, singer names, directions and chord suffixes. | Chord/lyric/text extraction already works in parts of the pipeline. Anastasia's structure tree additionally has **250 dialogue tags, 56 stage-direction tags and 2 song-lyrics tags**. These can help classify script material where present, but do not encode notes. | Untested improvement; small metadata probe, medium mapping. Do not assume these sparse tags cover all sung text. |

The metadata probe found no embedded-file attachments in any of the ten target PDFs. Ghost's piano
reduction has generic Part/Paragraph/Span tags; its `ActualText` values are 111 spaces and one dash.
Anastasia's only `ActualText` value found is a soft hyphen. Neither structure tree yielded a hidden
note/time/voice representation. Use the engraving objects rather than expecting an attached MusicXML
score. This conclusion concerns the inspected attachments/tags, not every conceivable producer extension.

## 4. Measurements and coverage

### Complete-book inventory

Every page of all target books was inspected, plus Anastasia Keyboard 1 as a scanned negative control.
“Heads” below counts ordinary pitched-head codes in EngraverFontSet/Petrucci, including cue glyphs;
it excludes MaestroPercussion heads. Dynamic/path counts are candidates, not verified error recoveries.

| book | pages | vector / text / scan | ordinary heads | dynamic candidates | paired-stroke hairpins |
|---|---:|---|---:|---:|---:|
| Ghost Bass | 75 | 66 / 8 / 1 | 7,118 | 120 | 67 |
| Ghost Cello | 65 | 57 / 7 / 1 | 4,930 | 139 | 82 |
| Ghost Drums | 87 | 77 / 9 / 1 | 0 | 190 | 87 |
| Ghost Guitar | 77 | 68 / 8 / 1 | 4,489 | 122 | 43 |
| Ghost PianoReduction | 290 | 285 / 5 / 0 | 49,801 | 396 | 275 |
| Ghost Reed | 55 | 48 / 6 / 1 | 1,999 | 164 | 83 |
| Ghost Trumpet | 53 | 46 / 6 / 1 | 1,336 | 138 | 60 |
| Ghost Utility | 115 | 102 / 12 / 1 | 10,157 | 154 | 78 |
| Ghost Violin | 63 | 55 / 7 / 1 | 4,328 | 130 | 64 |
| **Ghost total** | **880** | **804 / 68 / 8** | **84,158** | **1,553** | **839** |
| **Anastasia PianoReduction** | **335** | **316 / 19 / 0** | **61,947** | **565** | **453** |
| Anastasia Keyboard 1, negative control | 405 | 0 / 0 / 405 | 0 | 0 | 0 |

The eight Ghost scan pages are page 2 of the separate instrumental books. Whole-document
`is_scan()` correctly calls these predominantly vector documents, but is insufficient as the only
gate for a new extractor. Existing `vector.read()` already checks individual pages; retain that practice.

### Standalone direct-note pilot

Selection depends on source geometry and workbook context, not agreement with the truth. Evaluation
uses the printed bar sequence against the truth and removes its declared playback transposition to
compare written pitches. No duplicated accepted bar IDs were found.

| excerpt | printed bars considered | accepted | exact accepted bars | notes | note actions |
|---|---:|---:|---:|---:|---:|
| Ghost 4 Cello | 80 | 70 | 70 | 178 | 0 |
| Ghost 4 Bass | 80 | 80 | 80 | 190 | 0 |
| Ghost 5 Cello | 44 | 33 | 33 | 77 | 0 |
| Ghost 5 Bass | 44 | 40 | 40 | 77 | 0 |
| Ghost 13 Cello | 141 | 125 | 125 | 343 | 0 |
| Ghost 13 Bass | 182 | 158 | 158 | 645 | 0 |
| **Total** | **571** | **506** | **506** | **1,510** | **0** |

These are printed bars enumerated by the prototype, not all logical measures including multirests.
The metric checks pitch/onset/duration/staff, not voice IDs, enharmonic spelling, markings or rest
notation. This is an in-corpus pilot without a held-out generalization test.

### Limits of the correction comparisons

The 32 Ghost comparisons cover Cello, Bass, Violin, Reed, Trumpet, Utility and piano where configured
truth/output pairs exist in songs 1a, 4, 5, 11a, 13 and 20. Guitar, drums and singer routing were
inventoried but not included in these correction trials. The five Anastasia comparisons are the
diagnostic reduction-piano parts for songs 1–5, loaded from `vote/`.

Anastasia's `piano_part: false` excludes that piano from normal scoring. Moreover, song 2's
Klavierauszug truth contains **zero pitched notes**: it cannot validate piano extraction. Its
standalone source counts and zero matched-bar trial costs must not be presented as accuracy.
The piano comparisons here neither reverse that user setting nor count as pipeline acceptance.

## 5. What worked (experiments, not accepted changes)

- **Direct monophonic decoding:** the 506-bar result above establishes that useful musical events can
  be recovered without reading an image or borrowing an OMR timeline.
- **Font-scoped dynamic extraction:** `P`/`F` recover compound `mp`/`mf` without letter recognition.
  Ghost 13 Bass's conservative mark pilot improves dynamics **5→1**, hairpin starts **3→1**.
- **Hairpin geometry:** the same two-line predicate extracts candidates from both engraving families
  despite different stroke widths. It retains endpoints; stop-time correctness remains untested.
- **Concrete piano repairs exist:** Ghost 5 E1 errors and Ghost 4 bar 37 are recoverable from source
  heads/clefs. The lesson is to preserve their source association, not to copy every checker result.
- **Negative control:** all 405 Anastasia Keyboard 1 pages are scans and produce no direct candidates.

## 6. What did not work (do not retry without a new idea)

| tried or inspected | result | new idea required |
|---|---|---|
| Equal-count pitch replacement in source x order | Ghost **+508**, Anastasia diagnostic piano **+280** local note actions | Source-to-output provenance; chord/stem/voice grouping; local instrument/accidental state |
| Restricting that repair to one distinct pitch substitution under an octave | Ghost **−7**, but Utility 4 **+21**; Anastasia **+141** | Count agreement is not an ownership or bar-identity check. The Ghost result fails the per-part rule. |
| Add every eligible bar-start dynamic when the output has none | Ghost **+4** local dynamic actions | Staff/cue ownership, exact source bar, actual onset, conflicts and duplicate physical marks |
| The same naive hairpin placement on Anastasia piano | **+2** local start actions | Hand ownership and onset; measure stops separately |
| Reuse Ghost's vertical-stroke width filter for Anastasia | Page 7 loses its internal bar divisions | Use staff-spanning geometry and system connections, with per-profile widths only as supporting evidence |
| Existing `read_marks()` on Anastasia truth excerpts | **0 mark bars on 62 pages**, despite **11,887 heads** | Petrucci profile; this is a missing capability, not absent file information |
| Seek note semantics in attachments / accessibility replacement text | No attachments; only whitespace, dash or soft-hyphen replacement text | Decode the music-font glyphs and drawing relationships; use prose tags only for their actual roles |

The earlier rejected full `sheet_reader` engine and multi-staff barline replacement remain relevant
warnings in [IMPROVEMENTS.md §6](IMPROVEMENTS.md). They do not invalidate these directly verified
objects, but are reasons to integrate supported features incrementally and keep abstention explicit.

## 7. Learnings and reproduction

- **A PDF stores engraving, not necessarily music semantics.** Exact geometry removes recognition
  uncertainty; clef, accidental, voice, staff ownership and musical time still require interpretation.
- **Source mapping can dominate recognition quality.** Ghost 13 Cello's direct accepted bars are exact,
  yet ordinal-based corrections to its shifted output damage already-correct notes.
- **Anastasia needs its own profile.** Font and stroke assumptions, not image quality, explain several
  current omissions. Its excluded/incomplete reduction truth also limits claims about gains.
- **Separate decoding from placement.** Emit a source object first, then associate it with a retained
  staff and musical event; preserve ambiguity instead of converting every plausible object.
- **Do not conflate coverage with gain.** Thousands of available marks are not thousands of errors.
  The useful next benchmark asks which currently wrong or missing items become correct after routing.

The reproducible probe is [scripts/probe_born_digital.py](../scripts/probe_born_digital.py). It writes
only research artifacts under `results/analysis/born-digital-20261115/`; normal transcription outputs,
truths, pipeline code and the existing improvement documents were not edited by this investigation.

```bash
source ~/.local/share/omrbench/env.sh
python scripts/probe_born_digital.py --inventory
python scripts/probe_born_digital.py --metadata
python scripts/probe_born_digital.py --experiments
```

- [inventory.json](../results/analysis/born-digital-20261115/inventory.json): every page, capabilities,
  glyph/path counts, PDF hashes and producer metadata.
- [metadata.json](../results/analysis/born-digital-20261115/metadata.json): font encodings, Unicode maps,
  structure roles, replacement text, bookmarks and attachment results.
- [experiments.json](../results/analysis/born-digital-20261115/experiments.json): per-part costs, every
  accepted direct-note bar, rejected-bar reasons, all mark coordinates, correction examples and hashes
  of baseline outputs, truths, workbook/configuration and relevant code.
- [experiments.log](../results/analysis/born-digital-20261115/experiments.log): compact run output.

`results/` is gitignored; the probe in `scripts/` can regenerate these artifacts against the local data.
The numbers above describe the captured inputs, not a promise that later truth edits reproduce them.

Primary implementation touchpoints: `pdfkind.py:classify_page`; `pipeline/vector.py:_glyphs`,
`_drawings`, `read_marks`, `read_systems`, `_ties`; `scripts/pdf_truth_check.py:systems/pdf_notes`;
the source-coordinate mapping in `pipeline/assemble.py` / `engine.py`; `musicxml.py:drop_lone_marks`;
and `metrics/edits.py` / `musicxml.py:part_staves` for metric coverage.
