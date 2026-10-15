# Correction information

What we know about the hand corrections that turn a pipeline output into the truth: what had to be fixed, how
much work each fix is, and the conventions the corrected scores follow. Use it to rank pipeline work (fix the
expensive corrections first) and to keep the edit penalty (`metrics/edits.py`, `docs/PLAN.md` section 6) close to
the real effort. Add every new correction report here.

## Effort scale

The user rates each kind of fix in MuseScore (`data/ghost/comments.md`, German):

| Rating | Meaning | Typical fixes |
|---|---|---|
| gering (low) | a few clicks, local | a wrong tempo text, a misread bar number, missing slurs, a cue note to delete |
| mittel (medium) | repeated work over the whole part | repeat signs missing everywhere, measure repeats (%) half right, dynamics written as text |
| hoch (high) | the part breaks until fixed | wrong time signature (every bar has the wrong length) |

The rating is per kind of fix, not per occurrence. The edit penalty counts occurrences (each action 1), so a
"mittel" fix that occurs 20 times weighs 20; a wrong time signature costs 1 per wrong-length bar (`barlen`, since
2026-10-15), which matches its "hoch".

## Edit cost model (user decisions 2026-10-13 / 14)

- Every MuseScore action costs 1: a wrong note (pitch and / or duration) = 1 retype; a missing, made-up, changed
  or moved element (dynamic, articulation, fermata, slur, tie, hairpin, lyric, chord symbol, tuplet, tremolo,
  word, clef / key / time change, barline, repeat / volta / navigation, instrument change) = 1. Rests are free.
- Bars: deleting an extra bar = 1 (its contents go with it); inserting a missing bar = 1 + everything typed into it.
  A wrong bar count is a soft error (bars can be added or deleted).
- A whole part an octave / transposition off = 1 bulk action; a section one or two octaves off = 1 per section.
- A part with no output = 1 (add the instrument) + typing it in from scratch.
- In a truth bar written only in chords, a chord with the right pitches and one wrong duration = 1.
- Every bar whose filled length differs from the truth bar = 1 (it breaks in MuseScore).
- Rehearsal marks, tempi and system text count once per song, not per part.

## Correction reports

### Ghost #13 (2026-10-15, truth `#13 - Bass.mscz`, `#13 - Cello.mscz`)

| Part | Fix | Rating | Pipeline status |
|---|---|---|---|
| Bass | bar 1 is only a hint: its first note is for orientation, "Util." above it means only the Utility plays it (a cue) | gering | open: cue notes with a part label above are not dropped on vector pages |
| Bass | repeat signs missing throughout | mittel | open (Audiveris repeats are not carried over; IMPROVEMENTS #38) |
| Bass | tempo not taken over, written as text over the bar | gering | fixed 2026-10-15: "Driving (J = 130)" -> word "Driving" + metronome |
| Bass, Cello | bar number 111 becomes "III" | gering | fixed 2026-10-15: "III" / "lll" words left out |
| Bass | slurs missing | gering | open |
| Bass | exactly repeated bars (%-like sign) only partly work | mittel | open (measure repeats written out since 2026-10-15; some missed) |
| Bass | ties not exact, mostly over system breaks | (not rated) | open (IMPROVEMENTS #39) |
| Cello | time signature misread | hoch | fixed by the song's `time` row (workbook, 2026-10-15) |
| Cello | dynamics not reliable, often text instead of a real dynamic | mittel | open (IMPROVEMENTS #40) |
| Cello | otherwise like the Bass | | |

Bench after the fixes (`g13-m3`): Bass 88, Cello 208, system 37 = 333 actions (21 % of typing in).

## Conventions of the corrected scores

What "correct" means in the truths (user decisions; deviations to check are in `docs/TRUTH_DEVIATIONS.md`).

Notes and pitch:
- Sounding pitch under 8va (the pipeline can't read 8va lines yet); Glock / Crotales sound 15ma.
- Full-size notes over a whole-bar rest voice are cues: deleted. Grace notes as 16ths.
- Male voices in treble-8vb only for chorus labels and the singers in `male_voices` (Dmitry, Vlad).
- Anastasia 4 Dmitry / Vlad: the truth is right and the PDF is an octave off. Not visible from the PDF; accepted.

Bars:
- Lettered bars take bars of their own. A cut to a plain number ("to 14") keeps the bars in between as empty
  bars; a cut to a lettered bar ("-> 132C") skips the earlier letters (132A, 132B do not exist). Anastasia 4 =
  211 bars (206 + 131A, 132C, 148A–C).
- Measure repeats (%) are written out (Ghost 20 Drums truth).

Marks:
- `plain` parts (workbook column; Anastasia: Violin 2, Cello, Bass, Reed 2, Reed 3, Trumpet, Trombone, Männer; Ghost: none)
  keep notes, ties, note dots, tuplets, tremolos and playing words only. Dropped: articulations (staccato dots,
  accents, ...), dynamics, cresc. / dim. / rit., hairpins, slurs, fermatas, ornaments, tempo marks. Violin 1, Horn,
  Reed 1, solo singers, Frauen, the piano reduction, keyboards and percussion keep everything.

Text:
- Playing instructions in German, as the truth writes them: Mute / St. Mute / Cup Mute -> "gedämpft", Open ->
  "offen" (not at the start of a part), "to Mute" / "to Open" (preparations) left out; "pizz." and "Arco" stay.
- Spoken dialogue dropped in the vocal parts; singer cue lines, "Vamp until ...", "Then ON to m. 60" dropped in
  instrument parts (both shows; the Ghost 13 truth still has them); lyrics verse 1; singer part names as printed; duet labels
  A+B go to both parts.
- Numeric rehearsal marks (boxed bar numbers) dropped; letter marks kept.
- Piano reductions: no chord symbols; dynamics on staff 1; hairpins at most 2 bars; uncertain articulations /
  dynamics dropped.

Parts and instruments:
- German part names (Flöte 1 = Reed 1 Flute, Fagott = Reed 3, Pauken = Timpani, Glockenbaum = Mark Tree,
  Splash-Becken = Cymbal, Frauen = "Russian Chorus", Klavierauszug = PianoReduction Piano, ...).
- "Mallets" in the Anastasia drum book = xylophone (truth part "Xylophon").
- Doubling books: one part per instrument (MuseScore drops mid-part instrument changes on MusicXML import).
- Parts not corrected yet are listed in the workbook row `unfinished` and not scored (Anastasia 2 Klavierauszug).
- A truth may be a single corrected part per file (Ghost #13): B2 lists the files separated by ";".
