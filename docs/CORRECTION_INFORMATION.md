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
- Notes printed under another part's label ("Util.", "MOLLY:") are cues: always removed (user, 2026-10-15).
- Male voices in treble-8vb only for chorus labels and the singers in `male_voices` (Dmitry, Vlad).
- Anastasia 4 Dmitry / Vlad: the truth is right and the PDF is an octave off. Not visible from the PDF; accepted.

Bars:
- Lettered bars take bars of their own. A cut to a plain number ("to 14") keeps the bars in between as empty
  bars; a cut to a lettered bar ("-> 132C") skips the earlier letters (132A, 132B do not exist). Anastasia 4 =
  211 bars (206 + 131A, 132C, 148A–C).
- A curve joining two neighbouring notes of the same pitch is a tie, never a slur; a slur joins notes of
  different pitch (user, 2026-10-16). `truth.load` converts such slurs in the truths to ties.
- Double barlines as printed (user, 2026-10-16; Ghost 13 truths have them).
- Measure repeats (%) are written out (Ghost 20 Drums truth), with the articulations of the source bar; bars after
  "sim." get the pattern bar's articulations written out too (user, 2026-10-16; Ghost 13 Cello 27–33).

Marks:
- `plain` parts (workbook column; Anastasia: Violin 2, Cello, Bass, Reed 2, Reed 3, Trumpet, Trombone, Männer; Ghost: none)
  keep notes, ties, note dots, tuplets, tremolos and playing words only. Dropped: articulations (staccato dots,
  accents, ...), dynamics, cresc. / dim. / rit., hairpins, slurs, fermatas, ornaments, tempo marks. Violin 1, Horn,
  Reed 1, solo singers, Frauen, the piano reduction, keyboards and percussion keep everything.

Text:
- Playing instructions in German, as the truth writes them: Mute / St. Mute / Cup Mute -> "gedämpft", Open ->
  "offen" (not at the start of a part), "to Mute" / "to Open" (preparations) left out; "pizz." and "Arco" stay.
- Spoken dialogue dropped in the vocal parts; singer cue lines, "Vamp until ...", "Then ON to m. 60" dropped in
  instrument parts (both shows); lyrics verse 1; singer part names as printed; duet labels
  A+B go to both parts.
- Numeric rehearsal marks (boxed bar numbers) dropped; letter marks kept. (Ghost 13 truth has none since 2026-10-16: open, `docs/TRUTH_DEVIATIONS.md`.)
- Typographic and plain quotes are the same (we‘re = we're; the metric normalises them, user 2026-10-16).
- Piano reductions: no chord symbols; dynamics on staff 1; hairpins at most 2 bars; uncertain articulations /
  dynamics dropped.

Parts and instruments:
- German part names (Flöte 1 = Reed 1 Flute, Fagott = Reed 3, Pauken = Timpani, Glockenbaum = Mark Tree,
  Splash-Becken = Cymbal, Frauen = "Russian Chorus", Klavierauszug = PianoReduction Piano, ...).
- "Mallets" in the Anastasia drum book = xylophone (truth part "Xylophon").
- Doubling books: one part per instrument (MuseScore drops mid-part instrument changes on MusicXML import).
- Parts not corrected yet are listed in the workbook row `unfinished` and not scored (Anastasia 2 Klavierauszug).
- A truth may be a single corrected part per file (Ghost #13): B2 lists the files separated by ";".

## Music rule information

General rules of music notation that the pipeline (and a checker) can use to validate what it reads. Researched
2026-10-16 from engraving references (Gould "Behind Bars", Read "Music Notation", MusicXML spec, MuseScore /
Dorico docs); **for the user to validate**. Tags: **reliable** = a violation is almost always a reading error, safe
to fix automatically or score; **hint only** = raise suspicion, flag, do not change. Pitch names: C4 = middle C;
"written" = as printed in the part. Rules marked (used) are already applied by the pipeline or the metric.

### 1. Ties and slurs

- **Same pitch means tie (reliable, used in `truth.load`).** A curve between two neighbouring notes in the same
  voice with the same step, octave and sounding alteration is a tie. A curve between different pitches is a slur.
  Exceptions: portato (repeated notes under one slur with staccato dots / tenuto lines; the curve spans 3+ notes);
  a slur over a whole tie chain (nested curves, outer one ends on another pitch); enharmonic ties (G#4 to Ab4, rare,
  at key changes: compare MIDI pitch, not spelling); laissez-vibrer ties without an end note (harp, piano, cymbal,
  vibraphone; MusicXML `tied type="let-ring"`); in chords only some notes may be tied; ties cross barlines, system
  and page breaks.
  Check: two adjacent notes, same voice, same MIDI pitch, curve touches only them -> tie. "Tie" between different
  pitches -> slur. Tie start without a matching next note -> flag (or let-ring).
- **A tie never jumps (reliable).** It joins a note to the very next note of the same voice; nothing in between.
  Check: a "tie" with notes in between is a slur.
- **A slur joins at least two notes (reliable).** Exception: a slur continuing over a system break.

### 2. Bar duration

- **Each voice fills the bar (reliable, used: `barlen` in the metric, song `time` row).** Note and rest values
  of each voice add up to the time signature; tuplets count by their ratio; grace notes count zero.
  Exceptions: pickup bar at the start (the last bar of the section is often short by the same amount); short bars
  before a repeat / section change / second ending; cadenzas, "ad lib", "colla voce", "freely"; a whole-bar rest
  means the full bar in any meter (3/8, 7/4 too); a partial second voice may have hidden rests / `<forward>`;
  vamp and safety bars keep the normal length.
  Check: too long -> look for a missed dot, missed tuplet or misread value, fix if exactly one change makes it fit;
  too short mid-song -> flag; short first / last bar of a section = pickup.
- **Grace notes have no time value (reliable).** Check: a bar too long by exactly the value of some small notes ->
  make them grace notes.

### 3. Tuplets

- **Tuplet arithmetic (reliable).** n:m = n notes in the time of m of the same kind (eighth triplet 3:2 = one
  quarter); the notes inside, rests included, fill exactly n units.
  Exceptions: mixed units (quarter + eighth = 3 eighth units); the number is left out after the first bars
  ("sim."); 6:4 and two 3:2 sound the same, but a "6" over six sixteenths is one 6:4 group (Gould), two "3"s are
  two groups.
  Check: content does not fill n units -> number or value wrong; a bar too long by 1/3 or 1/2 beat often hides a
  missed triplet.

### 4. Accidentals

- **An accidental lasts to the barline (reliable).** Same line / space, same octave, same staff, rest of the bar.
  Exceptions: does not apply to other octaves (courtesy signs often repeat it there); rare older / modern scores
  apply it to one note only.
- **Ties carry the accidental over the barline (reliable).** Later untied notes in the new bar do not get it.
  After a line break the tied note may show it again.
- **The key signature applies to every octave (reliable).**
- **Courtesy accidentals (hint only).** Often in brackets, change nothing; a note in the bar after an accidental
  usually gets one. Check: a sign that repeats what is already true must not change the computed pitch.
- **Spelling fits the key (hint only).** Flat keys use flats for chromatic notes, sharp keys sharps; rising lines
  often sharps, falling lines flats; double sharps / flats are rare in theatre parts.
  Check: flag double sharps / flats and E#, B#, Cb, Fb in a simple key (likely a misread accidental).

### 5. Key signatures

- **Valid shapes only (reliable).** Sharps in the order F C G D A E B, flats B E A D G C F; 0–7 of one kind,
  never mixed. Check: 3 sharps where one is not F# -> nearest valid key, or flag.
- **Printed at every system start (reliable for engraving).** A change appears where it happens, usually at a
  double barline, with a courtesy key at the end of the line before. Check: a key at a line start that differs
  from the one before, with no courtesy key and no change mark -> likely misread (the crop key error, ERRORS #1).
- **Cancellation naturals (reliable).** Naturals before a new key (to C major or fewer sharps) are not notes and
  not a key of their own.
- **All parts change key in the same bar (reliable, used: song `key` row).** Each part transposed (concert Eb =
  written F for a Bb instrument). Drums and unpitched percussion have no key. Check: concert key = written key
  minus the transposition; all pitched parts agree.

### 6. Time signatures

- **Same bar in all parts (reliable, used: song `time` row).** Always at a barline, often a double barline;
  courtesy time at the end of the previous system. C = 4/4, cut C = 2/2. Exception: polymeter (very rare in
  theatre). Check: majority vote across parts per bar; bar lengths fit the new meter.

### 7. Barlines, rehearsal marks, tempo

- **Final barline (reliable).** Thin-thick at the end of a song; one per song file.
- **Double barline at section changes (hint only).** Key changes, often meter changes and new sections; rehearsal
  marks often sit on them.
- **All parts share bars, rehearsal marks and tempo (reliable within one score).** Same bar count, marks and tempo
  changes in the same bars; cuts and lettered bars (12A, 12B) match across parts. Check: line up parts by
  rehearsal mark; an extra / missing bar between two marks -> flag.

### 8. Repeats and endings

- **Pairing (reliable).** Every end repeat `:|` has a start `|:` (or the start of the piece / section) before it.
- **Voltas (reliable).** Ending 1 ends with a backward repeat, ending 2 follows right after; numbers go up; the
  last ending has no backward repeat.
- **Jumps (reliable).** D.S. needs a segno, "To Coda" a coda sign, D.C. nothing.
  Check: an unpaired repeat is probably a misread double / final barline; flag missing segno / coda signs.

### 9. Rests, multi-measure rests, repeat signs

- **Multi-measure rest (reliable, used).** Thick bar with a number = N empty bars; broken at rehearsal marks, key /
  meter changes and double barlines. Check: expand to N bars, compare bar counts with other parts; a misread
  number is a common cause of bar-count errors.
- **Bar repeat % (reliable, used).** One-bar sign = same as the bar before; the two-bar sign (with "2", on the
  barline) repeats the last two bars; numbers above a run of % only count. Check: expand, never count as a rest.
- **Slash notation (reliable, used).** Slashes = play in time, no pitch; never turn them into pitched notes.

### 10. Beams and stems

- **Only notes shorter than a quarter are beamed (reliable).** Beams = flags (1 = eighth, 2 = sixteenth).
  Exceptions: tremolo beams between half / whole notes, feathered beams.
- **Beams follow the beat (hint only).** 4/4 eighths in 2 or 4, not across beat 3; 6/8 in 3s; pop / jazz parts
  break this often. Use only to choose between two readings.
- **Stem direction (hint only, do not validate).** Usually down from the middle line up; voice 1 up, voice 2 down.
  Use it to find voices, not to check pitch.

### 11. Dynamics and hairpins

- **Placement (hint only).** Instruments below the staff, voices above (lyrics below), piano between the staves.
  Check: assign a dynamic to the staff above it (instruments) or below it (voices).
- **One dynamic per voice and time position (reliable).** Two at the same moment on one staff = duplicate read.
  A hairpin has a start and an end, often ending on a new dynamic. Check: remove duplicates; flag zero-length
  hairpins; a crescendo ending softer is only a hint (subito happens on purpose).
- **Valid tokens (reliable).** pppp..ffff, mp, mf, sf, sfz, sffz, fp, sfp, rf, rfz, fz, n, plus cresc., dim.,
  subito. Check: map OCR text to the closest token ("rnf" -> mf); a word that is only a dynamic is a dynamic
  (IMPROVEMENTS #40).

### 12. Articulations and ornaments

- **Only on notes (reliable).** Staccato, accent, tenuto, marcato, staccatissimo attach to notes / chords, never to
  rests. Exception: fermata (rest or barline too); breath marks and caesuras sit between notes.
  Check: an articulation on a rest is a misread or belongs to the next note.
- **Placement (hint only).** Staccato / tenuto on the notehead side; marcato and fermata usually above.

### 13. Clefs

- **Clef by instrument (hint only).** Treble: violin, flute, oboe, clarinet, sax, trumpet, horn, guitar, glock,
  xylophone, S/A voices, tenor (treble-8). Bass: cello, bass, bassoon, trombone, tuba, timpani, bass guitar, bass
  voice. Alto: viola. Tenor clef: high cello / bassoon / trombone. Keyboards: grand staff. Drums: percussion clef.
  Check: a clef unusual for the instrument (alto clef in a trumpet part) is probably a misread.
- **Clef changes (hint only).** Usually at a barline or system start; mid-bar changes (small clef) are common on
  keyboards, suspicious in wind / string parts.

### 14. Instrument ranges and transpositions

Written practical ranges; allow ~2 semitones tolerance. A note far outside is almost always a reading error
(wrong clef, missed octave line, miscounted ledger lines): **reliable for big misses, hint only near the edges**.

| Instrument | Written range | Sounds |
|---|---|---|
| Piccolo | D4–C7 | 1 octave higher |
| Flute | C4 (B3)–C7 | as written |
| Alto flute | C4–C7 | P4 lower |
| Oboe | Bb3–A6 | as written |
| English horn | B3–G6 | P5 lower |
| Clarinet in Bb | E3–C7 | M2 lower |
| Clarinet in A | E3–C7 | m3 lower |
| Bass clarinet (treble) | Eb3 (C3)–G6 | M9 lower |
| Bassoon | Bb1–E5 | as written |
| Soprano sax | Bb3–F#6 | M2 lower |
| Alto sax | Bb3–F#6 | M6 lower |
| Tenor sax | Bb3–F#6 | M9 lower |
| Baritone sax | Bb3–F#6 | octave + M6 lower |
| Horn in F | F#2–C6 | P5 lower |
| Trumpet in Bb | F#3–C6 (D6) | M2 lower |
| Flugelhorn in Bb | F#3–C6 | M2 lower |
| Trombone | E2–F5 (pedals to Bb1) | as written |
| Bass trombone | Bb1 (C1)–F4 | as written |
| Tuba | D1–F4 | as written |
| Violin | G3–E7 | as written |
| Viola | C3–E6 | as written |
| Cello | C2–A5 | as written |
| Double bass | E2 (C2)–G4 | 1 octave lower |
| Guitar | E3–B5 | 1 octave lower |
| Bass guitar | E2 (B1 on 5-string)–G4 | 1 octave lower |
| Piano | A0–C8 | as written |
| Celesta | C3 (C4)–C7 | 1 octave higher |
| Glockenspiel | G3–C6 | 2 octaves higher |
| Xylophone | F3 (C4)–C7 | 1 octave higher |
| Vibraphone | F3–F6 | as written |
| Marimba | C2 (A2)–C7 | as written |
| Timpani | D2–A3 (C2–C4) | as written |
| Soprano voice | C4–A5 (C6) | as written |
| Alto voice | G3–E5 | as written |
| Tenor voice | written C4–A5 in treble-8 | 1 octave lower than written |
| Bass voice | E2–E4 | as written |

Exceptions: horn in old-notation bass clef is written an octave lower; reed books switch instrument at "To Clar."
etc. (check range per section); keyboard / synth parts can have any range; concert-pitch (C) scores write
transposing instruments at sounding pitch. Note: our truths are in sounding pitch under 8va lines (Conventions).
Check: a whole passage off by exactly one octave -> missed 8va / 8vb or misread clef; a single far-off note ->
miscounted ledger lines (ERRORS #6, IMPROVEMENTS #27, #48).

### 15. Octave lines and octave-transposing instruments

- **Octave lines (reliable).** 8va = an octave higher, 8vb = lower, 15ma / 15mb = two octaves; the line ends with a
  hook or "loco" and applies only to notes under it on its own staff. Check: no end found -> end at the last note
  under the line or at "loco", never at the end of the piece; a line that pushes notes out of range was misread.
- **Octave-transposing instruments (reliable).** Piccolo, celesta, xylophone sound 1 octave up, glockenspiel 2;
  guitar, bass guitar, double bass, tenor voice 1 octave down (part of the instrument, not a printed line).
  Check: compare in the same convention (written or sounding), never "fix" by moving notes.

### 16. Drum and percussion parts

- **No key, percussion clef (reliable).** Drum set: percussion clef, no key signature, no accidentals. Timpani:
  bass clef. Mallets: normal clefs and keys. Check: drop keys / accidentals read on a percussion staff.
- **Staff position = instrument (hint only, differs by publisher).** Common map: kick space 1, snare space 3,
  hi-hat x above the staff (foot: x below), ride x on the top line, crash x above, toms between. Use the part's
  own legend (ours: `drumkit.yaml` from the truths).
- **Two voices (hint only).** Hands stems up, feet stems down; bar duration per voice.

### 17. Lyrics

- **One syllable per note (reliable).** Hyphens between syllables of a word; a melisma (one syllable over several
  notes) has an extender line and the notes are slurred or beamed. Exceptions: a tie chain carries one syllable;
  more verses stacked; elisions (two syllables on one note). Check: a syllable on a tied continuation note ->
  move to the first note of the chain.
- **Lyrics under the staff (hint only).** Text instructions and chord symbols sit above.

### 18. Chord symbols

- **Above the staff, on beats (hint only).** Usually change on beat 1 or 3 in 4/4. Grammar: root (A–G, #/b),
  quality (m, maj7, 7, dim, aug, sus4, add9), optional slash bass (/E). Check: parse against the grammar, map OCR
  to the closest valid symbol; chord roots are transposed in transposing parts; snap the beat to the note / slash
  under it (IMPROVEMENTS #37).

### 19. Cross-part checks for a whole song

- **Same structure in every part (reliable).** Bar count, repeats, voltas, rehearsal marks, meter and key changes
  (transposed), tempo marks and fermatas on the same bars. Check: line up all parts, majority vote per bar, flag
  outliers.
- **Concert pitch agreement (hint only).** Doubling instruments give the same concert pitches; tie-breaker only.

Sources: Gould, *Behind Bars* (2011); Read, *Music Notation* (1979) (both via secondary sources);
https://en.wikipedia.org/wiki/Accidental_(music); https://blog.henle.de/en/2014/05/12/best-until-how-long-does-an-accidental-last/;
https://musescore.org/en/handbook/3/accidentals; https://forums.steinberg.net/t/enharmonic-notes-tie/793980;
https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tied;
https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/multiple-rest;
https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/measure-repeat/;
https://steinberg.help/dorico/v1/en/dorico/topics/notation_reference/notation_reference_dynamics_placement_c.html;
https://michaelnorris.info/theory/transposinginstrumentscheatsheet; https://faculty.gvsu.edu/duitmanh/home/321transposition.html.
The range table was not checked entry by entry against an orchestration text: use only big misses as errors.
