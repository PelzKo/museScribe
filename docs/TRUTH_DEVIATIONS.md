# Truth deviations

Places where a truth score differs from the printed parts. Each one is either still to be decided / fixed (table 1)
or a deliberate convention that the pipeline may copy (table 2). Fixed entries are removed (last cleanup
2026-10-18, after the user's fixes of Anastasia 1 / 4, Ghost 1a / 20); parts not corrected yet are in the workbook
row `unfinished` (`docs/PLAN.md` section 5), not here. Both tables are sorted by project, song, part, bar.

Vector PDFs (Ghost parts, Anastasia PianoReduction): `python scripts/pdf_truth_check.py <show> <song> <part>` lists
the bars whose pitches differ from the truth (check each hit on the page; it applies the first transposition of a
part to the whole part, so bars after an instrument change give false hits). Spelling-only differences (F♯ for a
printed G♭) are logged only as a pattern (user 2026-10-16). The user corrects the truth files.

Status in table 1: `mistake` = probable truth error, `question` = a convention decision is needed, `open` = known,
not decided.

## 1. Open

| Project | Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|---|
| Anastasia | 4 | all | 101 | double barline at the end of 101 (every part) | single barline (all 38 parts; the other double barlines are fixed) | mistake |
| Anastasia | 4 | Horn, Oboe, Piccolo, Keyboard 1, Klavierauszug, Schlagzeug, Pauken, Xylophon (+ plain rows) | see section 3 | marcato (^) | accent (&gt;) | mistake (marcato = strong-accent); list in section 3 |
| Anastasia | 4 | Keyboard 1 | 32, 43 | right-hand beat-4 chord with marcato | no mark at all | mistake |
| Anastasia | 4 | Keyboard 2 | 26 | "RH: Trem Strings sounding 8vb" | 8va line (sounds D6–D7) | mistake: 8vb line as in 82–84 |
| Anastasia | 4 | Keyboard 2 | 196–206 | not in the scan (PDF page 29 is already 4A, printed page 30 missing) | rests | open: unverifiable |
| Anastasia | 4 | Posaune | 98 | "St. Mute" (a reminder, muted since 89) | no word | mistake (minor): reminder words are written (user 2026-10-18) |
| Anastasia | 4 | Schlagzeug | 144 | lower voice F4 beat 1, rest beat 3, F4 (accent, fz) beat 4 | F4 beat 1, rest, F4 on beat 3: the voice holds only 3 beats | mistake |
| Ghost | 4 | all | 1 | "Moderato (♩=95)" | metronome only | mistake (minor) |
| Ghost | 4 | all | 15, 30, 40, 48 | double barline | final barline (light-heavy) | mistake |
| Ghost | 4 | all | 16, 31, 41, 49, 62 | rehearsal letters A–E | none | mistake (letters are kept) |
| Ghost | 4 | all | 43 | single barline | double barline | mistake |
| Ghost | 4 | all | 49–80 | 4/4 continues (no part prints 2/2) | 2/2 from 49 | mistake (workbook `1: 4/4` is right) |
| Ghost | 4 | all | 61 | double barline before E | single | mistake |
| Ghost | 4 | Bass | 1 | mp | mp twice | mistake |
| Ghost | 4 | Bass | 15–16 | G3 tied, slide line into C3 | slur G3–C3 | question (minor): slide as slur? |
| Ghost | 4 | Bass | 23 | mf | missing (the Drums truth has an unprinted mf at 23) | mistake |
| Ghost | 4 | Bass | 45 | no ties | ties on both F3 | mistake |
| Ghost | 4 | Bass | 61 | cresc. hairpin | missing | mistake |
| Ghost | 4 | Cello | 3, 16 | "pizz.", "arco", "(solo)" | missing | mistake (minor) |
| Ghost | 4 | Cello | 10 | r, 8th r, G3 B3 C4 (quarter) G4 | B3 missing, G3 an eighth late | mistake |
| Ghost | 4 | Cello | 18 | &gt; hairpin after the &lt; | missing | mistake (minor) |
| Ghost | 4 | Cello, Violin | 56–57 | C4 / E4 whole tied into 57 | no tie | mistake |
| Ghost | 4 | Drums | 11, 16 | mp + "ride" (11), mp + "brushes lightly" (16) | missing | mistake |
| Ghost | 4 | Drums | 17–34, 50–57, 63–67, 71–74 | %-bars: accents of the pattern bar (4th and 13th 16th) | accents vary (19, 20, 23, 25, 53 on the 14th; 22, 52, 72 one missing; 26, 28, 31, 57, 65 extra) | mistake |
| Ghost | 4 | Drums | 21, 38, 45, 48, 50, 54, 62, 63, 66 | no ties | ties | mistake (minor) |
| Ghost | 4 | Drums | 23 | no dynamic | mf | mistake |
| Ghost | 4 | Drums | 39, 40 | ⊗ dotted half tied into an x eighth (39), ⊗ half (40) | ⊗ dotted quarter + rest, no tie | mistake (minor) |
| Ghost | 4 | Drums | 62, 76, 77 | f (62), dim. hairpin (76), mp + "ride" (77) | missing | mistake |
| Ghost | 4 | Drums | 67 | % bar | staccato on the last snare | mistake (minor) |
| Ghost | 4 | Drums | 69 | ride x + accent on beats 1 and 3 (as 68) | rests | mistake |
| Ghost | 4 | Drums | 75 | "cym." quarter triplet x x x tied into ⊗ | four x quarters, no triplet | mistake |
| Ghost | 4 | Guitar | 1 | mp, "(fingerpicking)" | missing | mistake |
| Ghost | 4 | Guitar | 15–79 | ~60 chord symbols | only 10 (58, 59, 75, 77–79); the rest are in the Klavier part | mistake |
| Ghost | 4 | Guitar | 58–61 | Fadd9 whole, Fm whole, Gsus4 /F halves, /E /D halves (diamonds) | 58–59 Gsus4 diamond halves, 60–61 the pattern | mistake (shifted) |
| Ghost | 4 | Guitar | 62 | f, "(light strumming/fingerpicking)" | missing | mistake |
| Ghost | 4 | Guitar | 74–78 | 74 Am Gsus4 diamond halves, 75 Fadd9, 77 Gsus4 Gsus4/F, 78 /E /D | 74 pattern, 75 "F", 77–78 Gsus4 ×4 | mistake |
| Ghost | 4 | PianoReduction | 3 | right hand 8th + 16th G3 | 16th rest | mistake |
| Ghost | 4 | PianoReduction | 36 | right hand F4 G4 A4 chord (whole) + C4 | C4 only | mistake |
| Ghost | 4 | PianoReduction | 41–46 | "Strings" F3 A3 C4 tenuto eighths, "Bass" F2 … | empty bars | mistake |
| Ghost | 4 | PianoReduction | 69 | right-hand quarter chords F4+A4, F4+B4 | A4+A4, B4+B4 | mistake |
| Ghost | 4 | PianoReduction | 78–80 | C4 D4 G4 whole, tied on from 77 | D4 D4 G4 (C4 lost) | mistake |
| Ghost | 4 | Reed | 10 | "1st time only" | missing | mistake (minor) |
| Ghost | 4 | Reed | 16, 30 | one dim. hairpin | 3 / 2 stacked hairpins | mistake |
| Ghost | 4 | Reed | 28 | pp + cresc. | cresc. only | mistake |
| Ghost | 4 | Reed | 78 | F♯4 E4 halves | a stray fingering mark on F♯4 | mistake (minor) |
| Ghost | 4 | Reed | 79 | E4 whole (tied 78–80) | E4 32nd + rests | mistake |
| Ghost | 4 | Trumpet | 10 | TACET; small "SAM" cue | 4 cue notes (written key C, not D) | mistake (cues are removed; workbook row `-`) |
| Ghost | 4 | Utility | 10 | SAM cue in small notes | cue notes kept | mistake |
| Ghost | 4 | Utility | 17 | multirest (16–19) | left hand A2 dotted half + C3 quarter | mistake |
| Ghost | 4 | Utility | 44–46 | concert C5 D5 E5 B♭4 / A4 / A♭4 | written under the B♭ change: sounds B4 C5 D5 C5 / A4 / A4 | mistake |
| Ghost | 4 | Utility | 49–57 | "STR. ENS. (loco & 8vb)" | 8va line, notes an octave up | mistake: by the Ghost 20 rule an 8vb line, notes an octave down |
| Ghost | 4 | Utility | 62 | f | fz | mistake |
| Ghost | 4 | Utility | 76–78 | C4 D4 G4 whole, tied 76–78, dim. | let-ring tie + slur at 76; 77–78 D4 doubled, C4 lost; staccato at 78 | mistake |
| Ghost | 4 | Violin | 2, 4 | harmonic circles on G5, C6 | none | mistake (minor) |
| Ghost | 4 | Violin | 10 | SAM cue | cue G3 16th kept | mistake |
| Ghost | 4 | Violin | 20, 25 | "solo"; slur starts at 25 | no word; slur starts at 26 | mistake (minor) |
| Ghost | 4 | Violin | 76 | dim. hairpin | missing | mistake |
| Ghost | 5 | all | 13 | 2/4, 4/4 from 14 (every part; workbook right) | 4/4 from 13: bar 13 holds 4 beats (Cello, Bass, Guitar, Utility, PianoReduction, Drums 4 notes instead of 2) | mistake |
| Ghost | 5 | all | 23, 33 | nothing | 4/4 restated at 23, 12/8 at 33 | mistake (minor) |
| Ghost | 5 | all | 1, 3, 24 | ♪=165 at 3; ♩.=57 at 24 | ♪=165 at 1; ♩.=57 missing | mistake (minor) |
| Ghost | 5 | all | 24, 36 | rehearsal letters A (24), B (36) | B at 27, C at 33, D at 43 | mistake |
| Ghost | 5 | all | whole song | playing words (waterphone w/bow, col legno, arco, heavy dist., e-bow, fade out, hot-rods, soft mallets, sim.) | none | mistake: playing words are written in Ghost (user 2026-10-18) |
| Ghost | 5 | Bass | 8, 43–44 | f; dim. hairpin | missing | mistake |
| Ghost | 5 | Cello | 5, 8 | "col legno", "arco" | missing | mistake |
| Ghost | 5 | Drums | 8 | f; plain F4 quarters | no f; accent + staccato on 8–22 | mistake (f); the marks: see 9–22 |
| Ghost | 5 | Drums | 9–22 | slashes "Toms w/ ad lib. accents" | bar 8 written out | question (like Ghost 20 Drums 45) |
| Ghost | 5 | Drums | 23 | fermata chord F4 A4 D5 | rest with fermata | mistake |
| Ghost | 5 | Drums | 38, 40 | sub. p | p | question (minor) |
| Ghost | 5 | Drums | 38–43 | ⊗ rolls tied 38–39, 40–41, 42–43 | no ties | mistake |
| Ghost | 5 | Drums | 39 | ⊗ dotted quarter, then rests; toms mp | ⊗ 3.5 quarters; toms mf | mistake |
| Ghost | 5 | Guitar | 10–22 | accent + staccato on both quarters of 10, then "sim." | marks only on the first quarter of each bar | mistake |
| Ghost | 5 | Guitar | 36–37, 42–44 | hollow diamond slashes (G5 / E♭5), tie 43–44, dim. | rests + chord symbols; an extra E♭5 symbol at 44; no hairpin | question (user 2026-10-18: undecided): diamonds on B as in Ghost 20, or rests? |
| Ghost | 5 | Guitar | 38 | last eighth B♭ (A G A G A G A B♭, like Violin 40) | G4 | mistake |
| Ghost | 5 | Guitar | 38, 40 | no dynamic | ff (38), mf (40) | mistake (minor) |
| Ghost | 5 | PianoReduction | 3, 5 | mf only at 1; 3–6 are %-bars | extra mf at 3 and 5 | mistake (minor) |
| Ghost | 5 | PianoReduction | 3–7 | left hand E2 tied half 3–4, E2 quarters 5–7 ("Util: (Synth Bass), Bs, Dr.") | rests | mistake |
| Ghost | 5 | PianoReduction (Männer) | 25–34 | lower choir staff (men, user 2026-10-18) in treble-8: sounds G3–G4 | "Männer" in bass clef with the written pitches G4–G5: an octave too high | mistake: treble-8vb, an octave down |
| Ghost | 5 | PianoReduction | 27 | left hand C2 G2 E3 G3 | E2 B2 E3 G3 | mistake |
| Ghost | 5 | PianoReduction | 29 | left hand C2 G2 C3 E3 | E2 B2 G3 G3 (a copy of 27) | mistake |
| Ghost | 5 | PianoReduction | 34–35 | "Util: (Bn.)" r B2 G3 D4~D4 over B1+B2 | B1+B2 only | mistake (PR cues are kept) |
| Ghost | 5 | PianoReduction | 36 | ff | missing | mistake |
| Ghost | 5 | Reed | 13–17 | Tenor Sax F♯5 half tied to a whole (13–14), f, cresc. to ff at the end of 14; 15–17 rest | p at 13, F♯5 in 13, 14 and 15, ff at 15 | mistake (one bar too many, f printed as p) |
| Ghost | 5 | Trumpet | 13–17 | as Reed (G♯4) | the same error | mistake |
| Ghost | 5 | Utility | 1–3 | timpani roll E2 tied 1–2–3, ending on an E2 quarter in 3 | A2 in 1–2, no tie into 3, 3 a rest | mistake |
| Ghost | 5 | Utility | 8 | f (staff 2) | missing | mistake |
| Ghost | 5 | Utility | 20 | "GUNSHOT": x-head quarter with accent | rest | mistake: written like a playing word (user 2026-10-18) |
| Ghost | 5 | Utility | 35 | D4 quarter + eighth rest | D4 dotted quarter | mistake (minor) |
| Ghost | 5 | Utility | 35–39 | "STR. ENS. (loco & 8va)" | printed pitch, no 8va line | mistake by the Ghost 20 rule (8va line) |
| Ghost | 5 | Violin | 5, 29, 36 | mf, mf, ff | no dynamics | mistake |
| Ghost | 5 | Violin | 8–22 | 8–12 slashes "ad lib." after the waterphone F5 harmonic (5–7); 13–22 rests | F5 diamond tied through 8–22 | mistake (13–22); 8–12 question |
| Ghost | 11a | all | 1, 6, 18 | Freely, Moderato (♩=c.108), Rall. | missing | mistake (minor) |
| Ghost | 11a | all | 6 | no rehearsal mark | "A" | mistake |
| Ghost | 11a | Guitar | 2–5 | "Play": hollow diamond slashes with fermatas + chord symbols (bar 1 a Cl. cue) | rests + chord symbols | question (user 2026-10-18: undecided; as Ghost 5 Guitar 36–44) |
| Ghost | 11a | PianoReduction | 16 | first right-hand chord C4 F4 C5 (FMaj7) | C4 G4 C5 | mistake |
| Ghost | 11a | PianoReduction | 18–19 | dim. hairpin | missing | mistake |
| Ghost | 11a | PianoReduction | 19 | right-hand chords G3 B3 E4 (3×) | G3 C4 E4 | mistake |
| Ghost | 13 | Bass | 3 | "Sim." | word kept | mistake: the truths drop "sim." / "fill" (the pattern is written out) |
| Ghost | 13 | Cello | 27, 99, 114 | "sim." | word kept | mistake (same) |
| Ghost | 20 | Drums | 1, 41 | "Open H.H." | every hi-hat note Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| Ghost | 20 | Drums | 45–46 | 45 "Fill" (four slashes), crash on beat 1 of 46 | 45 a written-out groove with the crash, 46 without | mistake (crash a bar early); how to write a slash "Fill" bar: question |
| Ghost | 20 | Guitar | 59, 61 | last eighth C5 (written) | D (61 with accent) | mistake |
| Ghost | 20 | Guitar | 60 | first eighth C5, as in 58 | eighth rest | mistake |
| Ghost | 20 | PianoReduction | 92–106, 130–132 | chord symbols above the piano staff | none | open: Ghost piano reductions keep chord symbols (1a, 4, 11a have them); the user adds them later (2026-10-18) |
| Ghost | 20 | PianoReduction | 135 | upper staff F4 + F5 eighth, accent (&gt;) | F3 + F5 quarter, marcato + staccato (the lower staff is fixed) | mistake |

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
| Anastasia | 4 | Keyboard 2, Klarinette in B 2, Flöte 2 | whole parts | dynamics, hairpins, accents, tenuto, slurs, ... | missing | `plain` rows get no marks and none are scored (user 2026-10-18; Keyboard 2 `plain` in every Anastasia sheet) |
| Anastasia | 4 | Triangel | 94, 97 | triangle noteheads | x head (94), normal head (97) | MuseScore can't set a triangle head here (user 2026-10-18) |
| Anastasia | 4, 4A | Xylophon (drum book) | 4: 1–27, 169–173; 4A: 1–3 | "mallets": x / ⊗ heads, rolls, "choke"; 4 bar 27 kit notes (bass drum F4 + x "choke") | a Xylophon part with pitches, incl. the kit notes of 27 | "mallets" = xylophone, everything in the mallets sections is Xylophon (user 2026-10-18); Drums rows `Xylophon` / `Xylophone`, alias `mallets` |
| Ghost | 4 | Guitar | 15–38, 47–57, 60–74 | slashes + chord symbols ("cont. in same style … ad lib.") after a written fingerpicking pattern | the last written pattern continued over the slash bars | user 2026-10-18: the pipeline continues the last written pattern as long as the slashes last |
| Ghost | 4, 5 | Reed, Guitar, Utility | e.g. 4 Reed 7–22, 4 Utility 39, 44, 49, 58, 5 Reed 30 | doubling labels (FLUTE / CLARINET) and patch labels (HARP, STR. ENS., ...) | one part with instrument changes ("Zu Flöte", Harfe, Streichinstrumente, ...) | doublings stay in one part in Ghost, are split per instrument in Anastasia (user 2026-10-18; show.yaml `doublings: one_part` in Ghost) |
| Ghost | 11a | PianoReduction | 1–5 | right hand Cl. line in full size, G4 whole 4–5 ("+Util. (Strings), Vln, Vc."), left hand Gtr diamond slashes | rests | the piano plays only its own part (user 2026-10-18) |
| Ghost | 1a, 4, 11a | PianoReduction | | chord symbols above the piano staff | chord symbols | Ghost piano reductions keep them (Anastasia's have none; user 2026-10-18); Ghost 20 still missing them (table 1) |
| Ghost | 13, 20 | all | e.g. 20 Drums 6, 7, 14; 13 Bass 115–129; 13 Cello 27–33, 99–105 | one- and two-bar repeat signs (%), "sim." after a marked bar | the bars written out, with the articulations of the pattern bar | user 2026-10-16; pipeline writes %-bars out, copying the marks is IMPROVEMENTS #47 |
| Ghost | 13 | Bass | | Bass, sounding 8vb | "Elektrischer Bass", written an octave above sounding | output uses `transpose: 8vb` |
| Ghost | 20 | Guitar | 9, 10, 17, 18, 28, 54, 55, 62, 63 | hollow (half / whole) rhythm slashes | diamond noteheads on B | the diamonds stand for the hollow slashes, no harmonics (2026-10-16) |
| Ghost | 20 | Utility | 21–49, 66–91, 115–135 | patch label "STR. ENS. (loco & 8va)" at 21, 66, 115, no 8va line | 8va line over staff 1, notes an octave up until "(loco)" | pipeline copies it (spans checked 2026-10-16) |
| all | all | all | | a curve joining two neighbouring notes of the same pitch | sometimes a slur (Ghost 13 Cello 18, Bass 7, Ghost 1a 17, Ghost 20 15, Anastasia 4 34) | it is a tie (user 2026-10-16); `truth.load` turns such slurs into ties, the .mscz files stay as they are |

## 3. Marcatos written as accents (Anastasia 4)

Printed marcato (^), truth accent (&gt;): change to marcato (2026-10-18 check). Printed bar numbers; beat in the bar;
pitches as written in the truth. Song 1 and the 4A Klavierauszug print no marcatos; song 2 and the 4A scan parts
are not checked.

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
- Xylophon: 27 b1 (the page has the ^ on the choke x; the truth has an accent on the F4 of the chord).
- Plain rows (not scored, no marks by convention; listed only for completeness): Klar 2 27, 32, 43, 85, 93, 136,
  177; Flöte 2 202; Keyboard 2 51, 81, 177, 185, 194; Fagott 31, 32, 42, 43, 70, 85, 93, 135, 136, 177, 185, 202,
  206; Posaune 32, 43, 52, 70, 81, 85, 93, 101, 136, 177, 202, 206.
