# The `pipeline` engine

One engine that combines the others (`omrbench/pipeline/`); its runtime is the sum of its steps.

1. **Audiveris** (with the `meta.yaml` switches) gives the page layout: systems, staves, bar
   positions, the parts of each system, and all OCR'd text with positions (`.omr` project).
2. **homr on crops:** every staff group (a single staff, or a piano's grand staff) of every
   system is cut out and read by homr. That makes homr usable on vocal scores and condensed
   parts, which it cannot read as whole pages. homr sometimes fails on one crop and works on
   a slightly different one, so failed crops are retried with other margins (`crop_margins`).
   The crop reader is pluggable (`recognizer:`, `pipeline/recognizer.py`): `homr` (default),
   `zeus` (solo-staff and grand-staff models), `smt-sys` (SMT system-level grand staff),
   `transcoda` and `smt-fp`. Groups a recognizer can't read (kern models: anything but a grand
   staff; zeus: 3+ staves) go to `fallback:` (default homr). In the steps below, "homr" stands
   for whichever recognizer read the crop (source label `crop`; `prefer` takes `crop` or the
   recognizer's name). bench.yaml has `pipeline-zeus`, `pipeline-smt`, `pipeline-transcoda`.
3. **Bar count per system** by vote between Audiveris and the homr crops.
4. **Bar choice:** per staff group and bar, the preferred engine's bar if its voices fill the
   time signature, else the other one. `prefer: auto` puts homr first on scans and Audiveris
   first on vector PDFs (it is near perfect there and, unlike homr, has ties). Percussion
   staves always prefer Audiveris (homr reads them as pitched). Where only one engine saw a
   clef change inside the system, its bar is taken (the other one reads the pitches in the old
   clef). homr sometimes places a voice's notes after the other staff's (the voice then runs
   past the bar end with gaps): a voice whose durations fit the bar is laid out note after note.
5. **Signatures:** time signature from homr where printed (Audiveris misreads 4/4 as 2/4),
   clef and key from the group's preferred engine. Parts not printed in a system follow its key.
   A key change to C printed as naturals only is read as sharps by homr: where Audiveris reads
   no key there, homr's notes are re-read in C.
6. **Directions and text:** dynamics, hairpins and tempo from Audiveris. Words are rebuilt
   from the positioned OCR text, because Audiveris files bar numbers as lyrics and expression
   text as page credits. Header and footer text become credits. Tempo and expression marks go
   to the top part (the full-score convention), labels and dialogue stay on their staff.
   `text_onset: bar` puts words at the start of their bar, as in the ground truths here.
7. **Multi-measure rests** are expanded from the printed evidence: the count above the rest,
   printed ranges ("15-17"), and gaps in the printed bar numbers. Systems of rests only are
   rebuilt from that evidence (neither engine finds their barlines reliably). A tiny bar at
   the end of a page (page-turn reminder) is dropped. Ranges over 99 bars are OCR slips and
   ignored; a homr rest count the printed numbers leave no room for is not used.
   **Bar numbers line up with the printed ones** (`align_bar_numbers: true`): wherever the
   printed numbers jump ahead of the output, rest bars are inserted, so output bar n is
   printed bar n in every part. A cut mark `[to] 97` (or `[to 16]`) printed at a barline means
   the bar there is bar 97 and the bars before it were cut from this part: they become rests.
   An arrow before the number (`—> 14`, `→ 14`) is a cut mark too.
   Without a cut mark the rests go after the last rest bar before the number (an unread
   multi-rest count), else right before it. Lettered bars added in a revision (`131A`,
   `[to] 132C`) count as bars of their own, if the plain numbers around them agree (a "7A"
   among bars 70-73 is a misread "72A" and would shift every bar from 8 on). OCR misreads numbers, so the step function that
   agrees with most numbers is used; a single stray number shifts nothing. Bars are never
   removed, except empty bars before printed bar 1. Where the output has more bars than the
   numbers say (an extra bar was read), `run.log` says where.
   **Second OCR pass** (`ocr_bar_numbers: true`): Audiveris' OCR misses whole pages of bar
   numbers now and then, so Tesseract reads the strips above and below every staff (one call
   per page, about 1 s) and adds the numbers, ranges, counts and cut marks Audiveris has no
   text for. A count-sized number only counts when a multi-measure rest bar is printed under
   it (notes are often read as "4"). The Tesseract binary bundled in Audiveris' jars is
   extracted into `$OMRBENCH_HOME/tools/tesseract` on first use (a `tesseract` on PATH wins);
   results are cached in the work dir's `ocr/`.
8. **Vocal scores** (`type: piano_reduction`): the lowest two staves of every system are the
   piano, each staff above it a voice. A voice staff belongs to the singer whose label was
   printed last on it ("DMITRY:", "FIRST WOMAN:", "ALL (NO DMITRY):"), carried over to the
   staff at the same position in later systems; a label inside a bar splits the bar there.
   Every distinct label becomes a part; a duet label ("DOWAGER+ANASTASIA:", also `&` / `AND`)
   puts the line into each singer's part (a name that starts a longer label elsewhere, "DOWAGER"
   -> "DOWAGER EMPRESS", takes that part). Parts named Men / Male / Tenor / Bass / Baritone,
   and the names in `male_voices`, are written in treble-8vb clef, an octave down (the
   ground-truth convention for male voices printed in treble clef). Unison notes two voices of
   a staff share are kept once. Lyrics, dynamics and hairpins are placed from their
   position on the page (Audiveris' MusicXML hangs piano dynamics on voices and joins
   hairpins to far-away stops): a syllable goes to the note above it, a mark between the
   piano staves is the piano's, one above a vocal staff that voice's. Dialogue (a speaker
   label followed by prose: "GLEB: (cont.)" / "We hear you, ...") is dropped, or with
   `spoken_text: text` kept as one text over the voices. Stage directions ("(VLAD POPOV
   enters.)") go to the voices. The piano gets no sung or spoken text. `transcribe` writes
   `<name> - Voices.musicxml` and `<name> - Piano.musicxml`; tempo and other system text
   is in both.
9. **Clean-up for MuseScore** (all scores): eighths and shorter without beams are beamed by
   beat (`auto_beam`), hairpins over `max_wedge_bars` (2) bars are dropped, graces whose
   flag was missed (read as quarters) get the piece's grace type, half/whole "graces" are
   dropped, articulations are kept once per chord.
10. **Percussion split:** for `type: drums` (or `split_instruments: true`), a shared staff is
   split into one part per instrument at the printed labels ("Timpani", "Bell Tree", ...).
   Instrument names come from `instruments:` in `meta.yaml`, or else from the header lines that
   also appear as labels. A clef change without a readable label switches to the next listed
   instrument.

`<run>/pipeline/<sample>/pipeline.json` records what was taken from where (bars per source,
multi-rest expansions, alignment rest bars, crops that failed); `<run>/run.log` has the details.

## Meta keys

Per-PDF meta (samples): `<name>.yaml` next to `<name>.pdf`, merged over the folder's `meta.yaml` (its keys
win). Shows get the same keys from their workbook. Extra key `pages: "2-4,7"` (1-based; a list `[2, 3, 4]` works too) transcribes only those pages
of the PDF; the original file is not changed.

For orchestra parts the `pipeline` engine also reads these meta keys (all optional; commented
examples in `meta.example.yaml`):

| Key | Example | Effect |
|---|---|---|
| `pages` | `"2-4,7"` or `[2, 3, 4]` | Transcribe only these PDF pages (1-based). Per-PDF yaml only. |
| `skip_systems` | `[1, 2, 3, 4, 5]` | Leave these systems out entirely. **A list of system numbers, not a count**: to skip the first 5 systems, list all five. `[5]` skips only the 5th. 1-based, counted over the transcribed pages (after `pages`), so system 1 is the first system of the first selected page. Use it for the end of the previous piece at the top of a page. Skipped systems produce no bars. |
| `keep_staves` | `2` | Read only the lowest n staves of every system as one part (conductor part: vocal/reference staves above the piano). Tempo and rehearsal marks above the system are kept; lyrics and labels of dropped staves are not. |
| `transpose` | `F`, `Bb`, `Bb 8vb`, `8vb`, or `{diatonic, chromatic, octave_change}` | Transposing instrument, written to sounding pitch. The key names the pitch below written C. `8va`/`8vb` add an octave. |
| `instruments` | `[{name: Clarinet, transpose: Bb}, Flute]` | Instruments the part plays. Each entry: `name`, optional `aliases`, `transpose`, `clef` (`pitched` / `percussion`), `lower_staff`. Printed labels in the score select the instrument. A label matches an instrument when it starts with its name or an alias ("Glock - soft mallets"), or else contains a word of 4+ letters that belongs to only one listed instrument ("Sus Cymbal" -> Cymbal; "Tree" alone matches nothing when Bell Tree and Mark Tree are both listed). `lower_staff: true` names the instrument of an unlabeled lower staff: when a system has two single-line staves (e.g. Timpani above, cymbal below) and the lower one has no label yet, it starts as this instrument instead of the next unused one in the list. It has no effect on the top staff, so it is harmless on songs where the instrument shares one staff with the others. |
| `split_instruments` | `true` | One MusicXML part per instrument (each with its own transposition). Use for Reed 1/2 and percussion. Default: on for `type: drums`. |
| `doubling` | `true` | Alternative to `split_instruments`: one part that changes instrument at the labels. MuseScore 4 ignores the change on import, so add the Instrument Change by hand. |
| `small_heads` | `true` | Tell Audiveris to read small note heads (cue notes). Needed for `cues: drop`. |
| `cues` | `keep` (default) / `drop` | `drop` turns cue-size notes into rests and removes the `(Clar)` label above them. Notes over a whole-bar rest in another voice of the staff are cues too (printed full size in these parts). |
| `male_voices` | `[Dmitry, Vlad]` | Vocal scores: singer parts written in treble-8vb besides Men / Male / Tenor / Bass / Baritone. |

Combine as needed, for example a horn part whose first page starts with the tail of the
previous number:

```yaml
pages: "1-3"
transpose: F
skip_systems: [1, 2]      # the first two systems of page 1
cues: drop
small_heads: true
```
