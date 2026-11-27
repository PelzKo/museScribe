# Truth deviations

Places where a truth score differs from the printed parts. Each one is either still to be decided / fixed (table 1)
or a deliberate convention that the pipeline may copy (table 2). Fixed entries are removed (last cleanup
2026-10-18, after the user's fixes of Anastasia 1 / 4, Ghost 1a / 20); parts not corrected yet are in the workbook
row `unfinished` (`docs/PLAN.md` section 5), not here. Both tables are sorted by project, song, part, bar.

Vector PDFs (Ghost parts, Anastasia PianoReduction): `python scripts/pdf_truth_check.py <show> <song> <part>` lists
the bars whose pitches differ from the truth (check each hit on the page; it applies the first transposition of a
part to the whole part, so bars after an instrument change give false hits). Spelling-only differences (F♯ for a
printed G♭) are logged only as a pattern (user 2026-10-16). The user corrects the truth files.

Anastasia 3 and 5 (checked 2026-11-06): the scanned parts were checked only where the output has notes that the truth
lacks (all of these were OMR errors); their marks were not checked. The Anastasia Klavierauszug piano is not checked,
generated or scored any more (user 2026-11-09): its rows were removed; the vocal staves still count.

Anastasia 5A (checked 2026-11-15): every part page against the truth, plus the diff of run 20261114-102221. Notes,
dynamics, hairpins, slurs and articulations match the scans; the remaining diffs are pipeline errors. Patch / doubling
labels ("Harp", "Piano", "Eng Hn", "Solo", "(under winds)") are left out by convention and not listed.

Checked 2026-11-09 against the user's corrected truths: rows fixed since then were removed (Anastasia 3 Empress 108–110,
Frauen 186 / 210, Kontrabass marks, Männer 186 / 202 / 204 / 210; Anastasia 4 bar 101 double barline, Keyboard 1
32 / 43 marcatos, Keyboard 2 bar 26 octave line, Posaune 98 "gedämpft"; Anastasia 5 Keyboard 1 104; the double
barlines of song 1 bar 3, song 2 bars 29 / 65, song 3 bars 66 / 229). The section 2 row on song 4 `plain` parts went
too: the `plainArticulation` flags of songs 1, 2, 4, 4A are removed (user 2026-11-09), their truths carry the marks.

**Fix pass 2026-11-11** (one-time user permission, done by Claude in the .mscz files; backups `*.mscz.bak-20261111`
next to each file): every table 1 row that could be confirmed on the page was fixed and removed here: Ghost 4, 5,
11a, 13, 20 (and unprinted rehearsal letters in Ghost 1a / 20), Anastasia 3 (empty extra part, Posaune 63), Anastasia 4
Xylophon 27. Already right before the pass: Ghost 4 Trumpet 10, Ghost 20 Guitar 59–61, Anastasia 4 Schlagzeug 144.
What is left below are questions, unverifiable rows and things seen but not checked.

**Recheck 2026-11-15** (all Anastasia truths as saved that day against every row below and against the `r69-a` /
5A outputs): fixed by the user and removed here: song 3 double barlines 4 / 22 / 46 / 87, song 4 Keyboard 2 82–84, song 5
bar 124, 5A double barlines 5 / 21 and Kontrabass "Arco"; song 3 Kontrabass articulations completed (100 -> 220; Posaune
+9, Trompete +6, Violoncello +26). Everything still open for Anastasia, with per-bar lists of the marks the sparse parts
lack (1 113 marks in 11 parts: output has it, the part's truth not, another truth part has it at the same bar and beat),
is in `docs/ANASTASIA_TRUTH_FIXES.pdf` for the person correcting the truths (generator:
`results/errors/2026-11-15-dynamics/truthfix_pdf.py`). Spot checks on the scans: 3 Kontrabass 35 `fp`, 4 Trompete 52.

**Ghost recheck 2026-11-15** (every truth song 1a, 4, 5, 11a, 13, 20): all parts through `pdf_truth_check.py`
(no pitch difference left besides the known false hits: instrument changes, slash bars, accidentals not carried over a
barline, as Ghost 20 bar 90 A4); fermatas, dynamics and articulations counted per bar from the PDF glyphs against the
truth (scratch script) and every hit looked up on the page; slurs, ties, hairpins and double barlines only where the
`r82-ref` output differs. Removed as right or not fixable: Ghost 4 Drums 37–59 accents and bar 39 tie, 4 Utility 60 / 61,
4 Violin 78–79, 5 Drums 36 / 39 / 43, 20 PianoReduction 130 / 131. The open Ghost rows, in German for the person
correcting the truths: `docs/GHOST_TRUTH_FIXES.pdf` (generator `results/errors/2026-11-15-dynamics/ghost_truthfix_pdf.py`).

Status in table 1: `mistake` = probable truth error, `question` = a convention decision is needed, `open` = known,
not decided.

## 1. Open

| Project | Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|---|
| Anastasia | 1, 2, 4 | all | every "sim." and % bar | "sim." after a marked bar; one- / two-bar repeat signs (%) | may be written out (marks copied onto the "sim." bars, %-bars as notes) | to fix: Anastasia keeps "sim." without the marks and keeps the % signs (expert 2026-10-28). Not done in the 2026-11-11 pass (needs every scan page). 4A checked 2026-11-11 as a trial: its books print no "sim." and no %, nothing to change |
| Anastasia | 3, 4 | Kontrabass, Trompete, Posaune, Keyboard 2 (song 3); Trompete in B, Posaune (song 4) | whole parts | articulations, dynamics, hairpins, slurs | about half of them missing | to fix: sparse parts, the user completes them (2026-11-14); counts and the check against the top-most-staff rule in section 4. 2026-11-15: 3 Kontrabass articulations done, its dynamics / hairpins not; 3 Violoncello, 3 / 4 Fagott, 4 Klarinette 2, 4 Keyboard 2 lack marks too (PDF) |
| Anastasia | 3 | Posaune | 38, 47, 57, 63–65 | mp + hairpin (38), mf (47, 57), cresc. 63–64 to f (65) | no dynamics | open: sparse part (incomplete truth, user 2026-11-10); only the tenutos of 63 were added |
| Anastasia | 4 | Fagott, Posaune, Keyboard 2, Klarinette 2, Flöte 2 | section 3 "plain rows" (Fagott 31, 32, 42, 43, 70, 85, 93, 135, 136, 177, 185, 202, 206; ...) | marcato (^) | accent (&gt;) | to fix: these rows were skipped in the 2026-11-01 marcato fix because the parts were `plain`; the flags are gone since 2026-11-09, so `r69-a` charges 65 "marcato instead of accent" (Fagott 38, Posaune 7, Keyboard 2 7) |
| Anastasia | 4 | Keyboard 2 | 196–206 | not in the scan (PDF page 29 is already 4A, printed page 30 missing) | rests | open: unverifiable |
| Anastasia | 4 | Trompete | 52–55 (and more, R65) | 2-note slurs (52 B♭–A, 53 A–B♭, 54 A–G, E–F) | no slurs | to fix in the truth (user 2026-11-13): add the printed slurs; the pipeline keeps them (18 made-up slurs in the part; other parts may lack printed 2-note slurs too, R65) |
| Anastasia | 4 | Männer | 65–71 | "(BASS SOLO:)" over a plain treble staff, bar 66 starts C5 | in Männer (treble-8vb) at C3 sounding: two octaves below the print | open: which octave (user checks later) |
| Anastasia | 5A | all | 1, 16, 21 | "Slightly Relaxed Tempo (In 3)" (1), "Con mosso (In 1) (Transition)" (16), "Slower" and "Attacca" (21) | no tempo text, no tempo mark | decided (user 2026-11-26): tempo headings and transitions are kept as printed; the truths that lack them deviate. Was: 4A and 5 also lack the heading tempo words (4A has only a ♩ = 120 mark), but song 5 keeps "rit.", "rall.", "a tempo" and "Applause segue", so at least "Slower" and "Attacca" may be missing |
| Anastasia | 5A | Keyboard 1 | 21 | wavy glissando line from the last LH chord up to the top of the RH staff | none | open |
| Anastasia | 5A | Pauken | 18–20 | treble staff with rests up to 19, bass clef at the end of 19 (box "Timpani" at 20) | clef change at the start of 18 | open (minor) |
| Anastasia | 5A | Schlagzeug | 1–2, 16–18 | ⊗ head with tremolo for the rolls (1, 17), x heads with l.v. curves (2, 16, 18) | Ride Cymbal, same head for all, no l.v. | not verified (minor): head / instrument convention |
| Ghost | 1a | all | 8 | double barline at the end of 8 (key change) | plain barline | mistake |
| Ghost | 1a | Clarinet in Bb | 17 | p ("molto legato") | no dynamic | mistake |
| Ghost | 1a | Electric Guitar | 10, 14; 16 | tie G eighth to G half (10, 14); no fermata in 16 | no tie; fermata on the half of 16 | mistake |
| Ghost | 1a | Electric Piano | 10, 12, 14 | fermatas over both staves | none | mistake |
| Ghost | 1a | Piano | 10; 12, 14; 16, 22 | fermatas over the rests of both hands (10), also over the LH rest (12, 14); none in 16, 22 | none in 10, RH only in 12, 14; fermata on the half in 16, 22 | mistake |
| Ghost | 4 | Bass | 15–16 | G3 dotted half tied to a quarter, straight slide line into C3 | tie + slur G3–C3 | question (minor): slide as slur? |
| Ghost | 4 | Drums | 61, 62 | one cresc. hairpin (61); crash on beat 1 without accent (62) | two stacked hairpins; accent on the crash | mistake (minor) |
| Ghost | 4 | Molly | 16 | mf before the entry | no dynamic | mistake |
| Ghost | 4 | PianoReduction (Klavier) | 62 | f | fz | mistake |
| Ghost | 4 | PianoReduction (Klavier) | 76–77 | dim. hairpin (76) and mp (77) belong to the cue staff (Cl.) | hairpin in the piano, no mp | question |
| Ghost | 4 | PianoReduction | whole part | — | — | only the bars the checks reported were looked at; no bar-by-bar comparison of marks (also Ghost 5, 20) |
| Ghost | 4 | Violin, Cello | 39–40 | dim. hairpin ends on the quarter of 40 | ends at the end of 39 | mistake (minor) |
| Ghost | 5 | Drums | 38, 40; 41 | sub. p; ^ over the ⊗ of 41 | p; no mark | question (minor); mistake (minor) |
| Ghost | 5 | Reed, Trumpet | 13, 18 | "flt." | tremolo, no word | question (minor) |
| Ghost | 5 | Utility | 35–36 | cresc. hairpin ends at the barline, ff on beat 1 of 36 | hairpin runs to the end of 36, ff at the end of 36 | mistake (minor) |
| Ghost | 11a | all | 6 | "Moderato (♩=c.108)" | written so, but MuseScore exports only the metronome sign ("c." is not a number) | open (minor; same in Ghost 1a "♩ = c. 72"; nothing to fix in the file) |
| Ghost | 11a | Bass, Utility, Piano, Violin, Cello | 3 | fermata in bar 3 (Bass: over the rest; the others: in the cue, Clarinet, Guitar) | fermatas only in 2 and 5 | mistake (fermatas are copied to every part) |
| Ghost | 11a | Clarinet in Bb | 1 | p | no dynamic | mistake |
| Ghost | 13 | Bass, Cello | 1 | fermata over bar 1 (cue "Util: SFX") | whole rest without fermata | mistake |
| Ghost | 13 | Cello | 38, 44 | double barline (pipeline reading) | plain | not checked on the page |
| Ghost | 20 | all | 65, 74, 123, 130 | double barline at the end of the bar | plain barline | mistake |
| Ghost | 20 | Bass, Guitar, Drums (1); Drums (46); Utility (5, 115); Trumpet (25, 70) | see parts | f | no dynamic | mistake |
| Ghost | 20 | Cello, Utility, Guitar, Piano | 100 | mf | no dynamic | mistake (Guitar 92 mp and Piano 29 / 110 f: reader hits, not seen on the page) |
| Ghost | 20 | Drums | 1, 46 | "Open H.H." | every hi-hat note Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| Ghost | 20 | Drums | 3, 8, 11, 130, 135 | accent on the last eighth | none (9, 17, 19, 61 have it) | mistake |
| Ghost | 20 | Guitar | 47, 48, 130 | accent on the E♭ quarter (47), on the last eighth (48, 130) | none | mistake |
| Ghost | 20 | PianoReduction | 5–28 | piano staves labelled "Util: (Str. Ens), Vln, Vc" | notes kept | question: also other-instrument notes? (bars 1–3 "Gtr." / "Bs." were removed 2026-11-11) |
| Ghost | 20 | PianoReduction | 9–134 | a chord symbol under almost every bar (PianoReduction.pdf pages 257–274) | none (the truth guitar has 105) | truth deviation (user 2026-11-15): chord symbols belong where the sheet prints them; the truth must get them |
| Ghost | 20 | PianoReduction | 134 | pdf_truth_check: no F6 | F5 + F6 on the last eighth | not checked on the page (130 / 131 A4 is right: chord symbol F) |
| Ghost | 20 | Trumpet | 135 | slanted line (scoop) into the last note | none | not verified (minor) |
| Ghost | 20 | Utility | 50, 52, 56, 58, 60, 64; 109; 131 | staccato dots on both voices; accent under the bell whole note (109); no accent in 131 | no staccatos; no accent; accent on the tied notes of 131 | mistake (56–64 by glyph count) |
| Ghost | 20 | Violin, Cello | 7, 13, 15, 52, 58, 60; 131 | no f (only at 5 and 50); no accent in 131 (only on the eighth of 130) | f in each of these bars; accent on the tied dotted half | mistake |
| Ghost | 20 | Violin | 108, 109 | trill (tr + wavy line) on the whole note; accent on the eighth of 109 | tremolo + text "Tremolo"; no accent | mistake |

## 2. Conventions

| Project | Song | Part | Bars | Printed | Truth | Note |
|---|---|---|---|---|---|---|
| Anastasia | 1, 2, 4 | brass | | "Mute", "St. Mute", "Cup Mute", "to Cup" + cup mute, "Open", "to Mute" | "gedämpft", "offen"; "to ..." and an "Open" at the start left out | pipeline translates (2026-10-15) |
| Anastasia | 1, 2, 4 | singers | | apostrophes `'` | typographic `‘` (we‘re, don‘t) | the metric treats both as the same (user 2026-10-16) |
| Anastasia | 4 | all | 25, 28, 95–96, 99–100, 121–122, 186–193 | cuts "[to] 26", "[to] 29", "[to] 97", "[to] 101", … | the skipped bars are empty bars | user 2026-10-17 |
| Anastasia | 4 | all | 132A–C | cut "-> 132C" | 132A and 132B don't exist: 211 bars (a cut to a lettered bar skips the earlier letters) | pipeline follows it |
| Anastasia | 4 | Dmitry, Vlad | | octave as printed | an octave below the output | the truth is right, the PDF is wrong (user 2026-10-15); error accepted |
| Anastasia | 4 | Keyboard 1, Keyboard 2, winds, Drums | whole parts | patch labels and playing words ("LH: Tuba", "RH: Celesta [bring out]", "Solo", "lead", "poco a poco cresc.", "choke", "pick up tamb.", "snares on / off", ...) | none | user 2026-10-18 |
| Anastasia | 4 | Keyboard 2 | 82–84 | "RH: Bassoon – sounding 8vb" | 8vb line, no label | patch octaves as octave lines (as Ghost 20 Utility) |
| Anastasia | 4 | Triangel | 94, 97 | triangle noteheads | x head (94), normal head (97) | MuseScore can't set a triangle head here (user 2026-10-18) |
| Anastasia | 4, 4A | Xylophon (drum book) | 4: 1–27, 169–173; 4A: 1–3 | "mallets": x / ⊗ heads, rolls, "choke"; 4 bar 27 kit notes (bass drum F4 + x "choke") | a Xylophon part with pitches, incl. the kit notes of 27 | "mallets" = xylophone, everything in the mallets sections is Xylophon (user 2026-10-18); Drums rows `Xylophon` / `Xylophone`, alias `mallets` |
| Ghost | 4 | Guitar | 15–38, 47–57, 60–74 | slashes + chord symbols ("cont. in same style … ad lib.") after a written fingerpicking pattern | the last written pattern continued over the slash bars | user 2026-10-18: the pipeline continues the last written pattern as long as the slashes last |
| Ghost | 4, 5 | Reed, Guitar, Utility | e.g. 4 Reed 7–22, 4 Utility 39, 44 (clarinet patch: written a tone up with key signature), 49, 58, 5 Reed 30 | doubling labels (FLUTE / CLARINET) and patch labels (HARP, STR. ENS., ...) | one part with instrument changes ("Zu Flöte", Harfe, Streichinstrumente, ...) | doublings stay in one part in Ghost, are split per instrument in Anastasia (user 2026-10-18; show.yaml `doublings: one_part` in Ghost) |
| Ghost | 11a | PianoReduction | 1–5 | right hand Cl. line in full size, G4 whole 4–5 ("+Util. (Strings), Vln, Vc."), left hand Gtr diamond slashes | rests | the piano plays only its own part (user 2026-10-18) |
| Ghost | 1a, 4, 11a | PianoReduction | | chord symbols above the piano staff | chord symbols | Ghost piano reductions keep them (Anastasia's have none; user 2026-10-18); Ghost 20 still missing them (table 1) |
| Ghost | 13, 20 | all | e.g. 20 Drums 6, 7, 14; 13 Bass 115–129; 13 Cello 27–33, 99–105 | one- and two-bar repeat signs (%), "sim." after a marked bar | the bars written out, with the articulations of the pattern bar | user 2026-10-16; pipeline writes %-bars out, copying the marks is IMPROVEMENTS #47 |
| Ghost | 13 | Bass | | Bass, sounding 8vb | "Elektrischer Bass", written an octave above sounding | output uses `transpose: 8vb` |
| Ghost | 4, 5, 11a, 20 | Guitar | 20: 9, 10, 17, 18, 28, 54, 55, 62, 63; 5: 36–37, 42–44; 11a: 2–5; 4: 39–40, 58–61, 74–80 | hollow (half / whole) rhythm slashes | diamond noteheads on B | the diamonds stand for the hollow slashes, no harmonics (2026-10-16; all Ghost songs, user 2026-11-11) |
| Ghost | all | PianoReduction | e.g. 4: 41–46, 5: 3–7, 34–35, 20: 1–3, 1a: 9–10, 11a: 1–5 | notes labelled as another instrument ("Gtr.", "Bs.", "Strings", "Util: (Bn.)", "Cl.") | rests | the piano reduction has only its own part; the other notes are a reference (user 2026-11-11) |
| Ghost | all | all | e.g. 5 Drums 9–22, 5 Violin 8–12, 20 Drums 45 | slash bars ("ad lib.", "Fill") | a copy of the bar before: same notes, accents, staccatos | "Fill" = continue exactly the same (user 2026-11-11) |
| Ghost | 20 | Utility | 21–49, 66–91, 115–135 | patch label "STR. ENS. (loco & 8va)" at 21, 66, 115, no 8va line | 8va line over staff 1, notes an octave up until "(loco)" | pipeline copies it (spans checked 2026-10-16) |
| all | all | all | | a curve joining two neighbouring notes of the same pitch | sometimes a slur (Ghost 13 Cello 18, Bass 7, Ghost 1a 17, Ghost 20 15, Anastasia 4 34) | it is a tie (user 2026-10-16); `truth.load` turns such slurs into ties, the .mscz files stay as they are |

## 3. Marcatos written as accents (Anastasia 4)

Printed marcato (^), truth accent (&gt;): change to marcato (2026-10-18 check). Printed bar numbers; beat in the bar;
pitches as written in the truth. Song 1 and the 4A Klavierauszug print no marcatos; song 2 and the 4A scan parts
are not checked.

**Fixed 2026-11-01** (user-approved one-off truth edit): the 52 accents of Horn, Oboe, Piccolo, Keyboard 1, Klavierauszug,
Schlagzeug and Pauken below are marcatos now (27 above, 25 below; Keyboard 1 / Klavierauszug 206 below). Only the
`<subtype>` of these 52 articulations changed in the .mscx, checked line by line; backup
`data/anastasia/truth/04_A_rumor_in_St_Petersburg_fertig.mscz.bak-20261101`. Not changed: Keyboard 1 LH 32 / 43 (the
truth has no mark there) and the plain rows (no beat / pitch given); Xylophon 27 followed on 2026-11-11.

- Horn: 27 b1 D5; 32 b3.5 E4 + b4 D4; 43 b3.5 E4 + b4 D4; 51 b4 D5; 70 b2 D4; 81 b4 D5; 85 b3.5 E4 + b4 D4;
  93 b4 B4; 101 b1 A4 + b2 B4 (b3 D5 stays an accent); 136 b3.5 F4 + b4 E4; 177 b4 B4; 185 b4 D5; 200 b3 E5; 202 b3 D5.
- Oboe: 27 b1 G5; 32 b4 B5; 43 b4 B5; 85 b4 B5; 93 b4 E5; 136 b4 C6.
- Piccolo: 202 b3 G6.
- Keyboard 1: 32 LH b4 G1; 43 LH b4 G1; 70 LH b2 G1; 85 RH b4 F5 + LH b4 G1; 93 RH b4 C5 + LH b4 C2;
  136 RH b4 G5 + LH b4 A1; 185 RH b4 G4 + LH b4 G1; 196 LH b2 C2; 200 RH b3 C5 + LH b3 G1; 202 RH b3 F4 + LH b3 G1;
  206 LH b4 C1 (marcato below). 32 and 43 RH b4 chord: no mark at all (table 1).
- Klavierauszug: 43 LH b4 G1; 136 LH b4 A1; 196 LH b2 C2; 200 RH b3 C5 chord + LH b3 G1; 202 LH b3 G3 chord;
  206 LH b4 C1.
- Schlagzeug: 61 b3 C5; 81 b4 C5; 159 b3 C5.
- Pauken: 177 b4 F2.
- Xylophon: 27 b1 (the page has the ^ on the choke x): marcato on the chord since 2026-11-11.
- Plain rows (not scored, no marks by convention; listed only for completeness): Klar 2 27, 32, 43, 85, 93, 136,
  177; Flöte 2 202; Keyboard 2 51, 81, 177, 185, 194; Fagott 31, 32, 42, 43, 70, 85, 93, 135, 136, 177, 185, 202,
  206; Posaune 32, 43, 52, 70, 81, 85, 93, 101, 136, 177, 202, 206.

## 4. Sparse Anastasia parts (user completes them, 2026-11-14)

Six truth parts lack marks the page prints. They stay in the score until they are completed (user 2026-11-14), so
they hold **1 472 of the 9 111** actions of `r69-a` (articulations 773, notes 193, dynamics 142, hairpins 104, slurs 68).

Check against the Anastasia rule "a dynamic or text that several staves have at the same time in the same pattern is
written only in the top-most staff" (user 2026-11-14). Method (scratch script, 2026-11-14): bars aligned like the
metric; every articulation, dynamic, hairpin, slur, fermata and word of the `r69-a` output is looked up in the truth
of its own part (kept / missing) and in every other truth part of the song at the same bar, beat and token ("above"
= a part higher in the score order has it, "below" = only a lower part, "unique" = no other part).

| Song | Part | has it above: kept / missing | only below: kept / missing | unique: kept / missing | dynamics above: kept / missing | hairpins above: kept / missing |
|---|---|---|---|---|---|---|
| 3 | Kontrabass | 107 / 133 | 0 / 1 | 5 / 10 | 11 / 19 | 1 / 13 |
| 3 | Trompete | 111 / 113 | 16 / 2 | 18 / 19 | 8 / 9 | 10 / 7 |
| 3 | Posaune | 102 / 114 | 62 / 1 | 15 / 11 | 4 / 16 | 2 / 12 |
| 3 | Keyboard 2 | 131 / 154 | 11 / 0 | 29 / 5 | 12 / 18 | 1 / 5 |
| 4 | Trompete in B | 74 / 224 | 13 / 4 | 9 / 13 | 4 / 23 | 1 / 10 |
| 4 | Posaune | 92 / 171 | 51 / 11 | 19 / 18 | 7 / 18 | 7 / 9 |
| | **six parts** | **617 / 909** | 153 / 19 | 95 / 76 | 46 / 103 | 22 / 56 |
| 3 | Violine 1 (complete part, for comparison) | 323 / 13 | 19 / 3 | 32 / 14 | 26 / 5 | 17 / 5 |
| 3 | Horn (complete) | 172 / 6 | 43 / 1 | 45 / 11 | 17 / 1 | 12 / 0 |
| 3 | Keyboard 1 (complete) | 439 / 21 | 58 / 7 | 93 / 20 | 20 / 9 | 11 / 2 |
| 4 | Violine 1 (complete) | 488 / 6 | 63 / 1 | 9 / 25 | 33 / 2 | 19 / 1 |
| 4 | Horn in F (complete) | 222 / 5 | 89 / 8 | 82 / 15 | 16 / 3 | 11 / 1 |

Result:
- **928 of the 1 004 missing marks are real gaps by the evidence**: the part's own page gives the mark (the reader
  found it) and another truth part has the same mark on the same bar and beat. Only 76 have no second witness (those
  may be misreads).
- **The top-most-staff rule does not explain them.** The complete parts keep 95 % of the marks a higher part also
  has (Violine 1 sits at the bottom of the score and keeps 811 of 830). The six parts keep 617 and lack 909 of the
  same kind, mixed inside one part, so they follow neither "write everything" nor "only the top-most staff".
- Dynamics and hairpins alone (the rule's own scope): 159 missing ones have the same mark in a higher part. If the
  rule is meant for these parts, these 159 are right as they are and the pipeline has to drop them (IMPROVEMENTS
  D6); the 750 articulations and slurs are gaps in any case.
- Candidates with the same pattern, smaller: song 3 Violoncello dynamics 5 kept / 16 missing and hairpins 3 / 10
  with a higher part; song 4 Fagott 40 + 28 marks missing that another part has; song 4 Keyboard 2 dynamics 20 / 13.
- Song 3 Violine 2 and Klarinette 2 are `plainArticulation` parts (marks stripped on both sides), not in this list.

Not checked: the scan pages themselves. To complete a part, start from the output of `r69-a`
(`results/anastasia/3/`, `results/anastasia/4/`): it already carries these marks.
