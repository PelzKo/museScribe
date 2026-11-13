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

Status in table 1: `mistake` = probable truth error, `question` = a convention decision is needed, `open` = known,
not decided.

## 1. Open

| Project | Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|---|
| Anastasia | 1, 2, 4 | all | every "sim." and % bar | "sim." after a marked bar; one- / two-bar repeat signs (%) | may be written out (marks copied onto the "sim." bars, %-bars as notes) | to fix: Anastasia keeps "sim." without the marks and keeps the % signs (expert 2026-10-28). Not done in the 2026-11-11 pass (needs every scan page). 4A checked 2026-11-11 as a trial: its books print no "sim." and no %, nothing to change |
| Anastasia | 3 | all | 4, 22, 46, 87 | double barline (user confirmed 2026-11-13) | single barline | open: the truth lacks the printed double barlines |
| Anastasia | 3 | Posaune | 38, 47, 57, 63–65 | mp + hairpin (38), mf (47, 57), cresc. 63–64 to f (65) | no dynamics | open: sparse part (incomplete truth, user 2026-11-10); only the tenutos of 63 were added |
| Anastasia | 4 | Keyboard 2 | 82–84 | LH bass clef C♯3 / G♯2 (box "RH: Bassoon - sounding 8vb" names the RH only) | LH an octave lower (C♯2 / G♯1), RH as printed | fixed by user 2026-11-13 (the octave was in the wrong hand) |
| Anastasia | 4 | Keyboard 2 | 196–206 | not in the scan (PDF page 29 is already 4A, printed page 30 missing) | rests | open: unverifiable |
| Anastasia | 4 | Männer | 65–71 | "(BASS SOLO:)" over a plain treble staff, bar 66 starts C5 | in Männer (treble-8vb) at C3 sounding: two octaves below the print | open: which octave (user checks later) |
| Anastasia | 5 | all | 124 | double barline (user confirmed 2026-11-13) | single barline | open: the truth lacks the printed double barline |
| Ghost | 4 | Bass | 15–16 | G3 dotted half tied to a quarter, straight slide line into C3 | tie + slur G3–C3 | question (minor): slide as slur? |
| Ghost | 4 | Drums | 37, 38, 47, 48, 58, 59 | written bars | accents as before | not re-checked (the text layer was not readable there) |
| Ghost | 4 | Drums | 39 | ⊗ dotted half tied into the x eighth | no tie (different drum pitches cannot be tied) | open (minor) |
| Ghost | 4 | Drums | 61 | one cresc. hairpin | two stacked cresc. hairpins | mistake (minor) |
| Ghost | 4 | PianoReduction | whole part | — | — | only the rows of the old table were fixed; no bar-by-bar comparison of marks |
| Ghost | 4 | Utility | 60, 61 | whole-note clusters | C4 D4 G4 / B3 D4 G4 | not checked |
| Ghost | 4 | Violin | 39–40, 78–79 | dim. hairpin ends on the C4 of 40 / runs into 79 | ends at the end of 39 / 78 | mistake (minor) |
| Ghost | 5 | Drums | 36, 41, 43 | ⊗ with dot, kick dotted quarter below | ⊗ dotted whole | not verified (39 is a dotted quarter + rests, fixed) |
| Ghost | 5 | Drums | 38, 40 | sub. p | p | question (minor) |
| Ghost | 5 | Drums | 41 | ^ over the ⊗ | none | not verified (minor) |
| Ghost | 5 | Reed, Trumpet | 13, 18 | "flt." | tremolo, no word | open (minor) |
| Ghost | 11a | all | 6 | "Moderato (♩=c.108)" | written so, but MuseScore exports only the metronome sign ("c." is not a number) | open (minor; same in Ghost 1a "♩ = c. 72") |
| Ghost | 20 | Drums | 1, 41 | "Open H.H." | every hi-hat note Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| Ghost | 20 | PianoReduction | 5–28 | piano staves labelled "Util: (Str. Ens), Vln, Vc" | notes kept | question: also other-instrument notes? (bars 1–3 "Gtr." / "Bs." were removed 2026-11-11) |
| Ghost | 20 | PianoReduction | 9–134 | a chord symbol under almost every bar (PianoReduction.pdf pages 257–274) | none (the truth guitar has 105) | open: Ghost piano reductions keep chord symbols; the user checks later (2026-10-18, again 2026-11-09) |
| Ghost | 20 | PianoReduction | 130, 131, 134 | pdf_truth_check: A♭4 (130, 131); no F6 in 134 | A4; F5 + F6 on the last eighth of 134 | not checked on the page (may be false hits) |

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
| Ghost | 4, 5 | Reed, Guitar, Utility | e.g. 4 Reed 7–22, 4 Utility 39, 44, 49, 58, 5 Reed 30 | doubling labels (FLUTE / CLARINET) and patch labels (HARP, STR. ENS., ...) | one part with instrument changes ("Zu Flöte", Harfe, Streichinstrumente, ...) | doublings stay in one part in Ghost, are split per instrument in Anastasia (user 2026-10-18; show.yaml `doublings: one_part` in Ghost) |
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
