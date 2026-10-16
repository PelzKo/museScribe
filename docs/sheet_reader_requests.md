# sheet_reader: test results and feature requests from museScribe

For the developer of `sheet_reader` (vector glyph reader for born-digital PDFs). museScribe transcribes the
Ghost part books (`Bass.pdf`, `Cello.pdf`, `Drums.pdf`, `Guitar.pdf`, `Reed.pdf`, `Trumpet.pdf`, `Utility.pdf`,
`Violin.pdf`, `PianoReduction.pdf`; Finale, fonts EngraverFontSet / Maestro / MaestroPercussion) and scores the
output against hand-corrected MuseScore truths by the number of edits left. Nothing in sheet_reader was changed;
everything below is a suggestion. Details of the test: `docs/ERRORS.md` (section sheet_reader).

## Test (2026-10-16, commit `cafd455`)

14 Ghost parts (songs 1a, 13, 20), the pages each song covers. The part books have **one staff per system and
several systems per page**, so a small adapter chained the staves of each page into one part and took barlines per
staff (plus the staff's left edge as the first barline). Under 6 s per part. Every music-font character on the
tested pages has a `glyph_map` entry (good coverage).

| | sheet_reader | museScribe pipeline (Audiveris + homr) |
|---|---|---|
| edits left, 14 parts | 7111 | 1341 |
| bars with all notes right (of 1132) | 354 | 1003 |
| best part, note F1 with bars aligned | Ghost 13 Cello 0.76 | 0.88 |

The notes it reads are mostly right; the losses come from structure (bars, keys, transposition) and from the marks
it does not export yet. The marks it *sees* are better than ours: Ghost 13 Cello has 42 marcatos in the PDF and 42
in the truth, the pipeline finds 26; dynamics 9 in the PDF, 10 in the truth, pipeline 5.

## Feature requests (most useful first)

1. **Part books: several systems per page.** Group staves into systems (a system = staves joined by a barline
   or a brace / bracket; single-staff systems are the norm in parts) and take barlines per system, not "more than
   half of the page's staves". A single-staff system has no barline at its left edge: the first bar starts after
   clef / key / time.
2. **Multi-rests.** A thick horizontal bar in the staff with a number above (Maestro digits, e.g. "8", "19") = that
   many empty bars. Today one bar, so a part loses 10–40 bars (Ghost 13 Cello 156 of 199, 1a Cello 8 of 28).
3. **Key, clef and time changes inside a line**, also after a double barline (Ghost 1a Cello p. 10: 5 sharps ->
   3 flats with a new 4/4 in the middle of the second line). Pitches after the change are wrong today.
4. **Export the marks with their positions**: articulations (accent `>`, marcato `^`, staccato = dot above / below
   the head, tenuto `-`), dynamics, fermatas, hairpins (two thin diverging lines), slurs, words (with font: bold =
   tempo / instruction, italic = expression), rehearsal marks (boxed letters), tempo (`EngraverTextT` note glyph +
   "= 130"). In MusicXML, and ideally also as a list of events (page, x, y, staff, bar, meaning), so another
   program can use them without its notes.
5. **Ties vs slurs**: a curve between two equal pitches is a tie, otherwise a slur, and export slurs too. Ties at
   the end of a system continue to the first note of the next system.
6. **Barline types and repeats**: double (two thin strokes 2–4 pt apart), final (thin + thick), repeat dots, voltas
   (bracket line with a number). Today a double barline is collapsed to one stroke and its type is lost.
7. **Grand staff** (Utility / keyboard, piano reduction): two staves joined by a brace = one part with two staves.
   Chained one by one they double the bar count (329 instead of 135).
8. **Transposition from the instrument**: Bass and Guitar sound an octave lower (8vb), Clarinet / Trumpet in Bb,
   Alto Sax in Eb. A `<transpose>` in the part (from a part-name table or a command-line option) makes the output
   sound right.
9. **Glyphs still unmapped on the Ghost parts**: `˙` (EngraverFontSet, the open notehead; `note_shapes` returns
   "half?"), `˘` ×20 on Reed / Trumpet 20 pages, `,` (breath mark?), `¨`, Maestro digits `6`, `7`, `0` (time
   signature / multi-rest numbers), all `EngraverTextT` characters (tempo marks). 47 entries are still `# guess`.
10. **Slash notation and "sim."** (lower priority): slash noteheads get their length from stem / beam like normal
   heads; museScribe reads them already (`omrbench/pipeline/vector.py`, could be a reference).
11. **An API that returns structured events**, not only files: e.g. `read_pages(pdf, pages) -> list of systems, each
   with staves, bars (x0, x1, barline types) and events (x, y, kind, pitch, duration, marks)`. museScribe would then
   use single pieces (marks, ties, barline types, pitch checks) next to its own notes.

## How to test against the Ghost truths

The truths and PDFs stay with the user (not public). With museScribe set up, an output folder of MusicXML files
named like the books (`Cello.musicxml`, ...) per song can be scored:

```bash
omrbench bench ghost --run <run-folder> --bench-id <name>          # edits left, note F1 per part
python scripts/error_report.py ghost --run <run-folder> --out results/errors/<name>   # every difference by kind
```
