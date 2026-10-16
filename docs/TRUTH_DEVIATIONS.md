# Truth deviations to check

Places where a truth score seems to differ from the printed parts. Each one is either a deliberate convention
(then the pipeline may copy it, and the entry says so) or a mistake in the truth. Check and mark each entry; add
new ones whenever a benchmark shows something odd. Fixed entries are removed (last cleanup 2026-10-16); parts not
corrected yet are in the workbook column `unfinished` (`docs/PLAN.md` section 5), not here.

Vector PDFs (Ghost parts, Anastasia PianoReduction): `python scripts/pdf_truth_check.py <show> <song> <part>` lists
the bars whose pitches differ from the truth (check each hit on the page). Spelling-only differences (F♯ for a printed
G♭) are logged only as a pattern (user 2026-10-16). The user corrects the truth files.

Status: `open` = not checked yet, `convention` = intended, keep (pipeline follows it).

## Ghost

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 20 | Drums | 1, 41 | "Open H.H." | every hi-hat note is Closed Hi-Hat (G5, x head) | open (pipeline follows the truth) |
| 20 | Utility | 3 sections | patch label "STR. ENS. (loco & 8va)", no 8va line | 8va line over staff 1, notes an octave up until "(loco)" | convention (pipeline copies it) |
| 20 | Reed, Trumpet | whole part | 16 accent glyphs in the PDF (each) | 33 / 36 accents (more than printed; e.g. on bars the PDF does not mark) | open (2026-10-16: reading the accents exactly from the PDF glyphs made Reed 20 worse by 19, so the truth has accents the page lacks) |
| 20 | Utility | 8va sections | "STR. ENS. (loco & 8va)" at 21, 66, 115 | 8va spans 21–49, 66–91, 115–135 | checked 2026-10-16: the spans match the labels (truth an octave above the page in exactly these bars); the ~115 notes are the pipeline's own gap |
| 20 | Guitar | 9, 10, 17, 18, 28, 54, 55, 62, 63 | hollow (half / whole) rhythm slashes | diamond noteheads on B | explained 2026-10-16: the diamonds stand for the hollow slashes, no harmonics |
| 20 | PianoReduction | 92–106, 130–132 | chord symbols above the piano staff | none (as in all piano-reduction truths) | convention (pipeline writes none on piano reductions) |
| 13, 20 | all | e.g. 20 Drums 6, 7, 14; 13 Bass 115–129; 13 Cello 27–33, 99–105 | one- and two-bar repeat signs (%), "sim." after a marked bar | the bars written out, with the articulations of the pattern bar | convention (user 2026-10-16; pipeline writes %-bars out, copying the marks is IMPROVEMENTS #47) |
| all | all | | a curve joining two neighbouring notes of the same pitch | sometimes a slur (Ghost 13 Cello 18, Bass 7, Ghost 1a 17, Ghost 20 15, Anastasia 4 34) | convention: it is a tie (user 2026-10-16); `truth.load` turns such slurs into ties (`musicxml.slurs_to_ties`), the .mscz files stay as they are |
| 13 | Bass | 55 | single barline (the repeat starts at 56) | double barline | mistake (minor) |
| 13 | Bass | | Bass, sounding 8vb | "Elektrischer Bass", written an octave above sounding | convention (output uses `transpose: 8vb`) |
| 13 | Bass | 3 | "Sim." | word "Sim." kept | open: the truths drop "sim." / "fill" (user 2026-10-16, the pattern is written out); remove the word from the truth |
| 13 | Cello | 27, 99, 114 | "sim." | word "sim." kept | open: remove the word from the truth (same convention) |
| 20 | Bass | 135 | half rest, F3 eighth (accent), rests | bar empty (rest only) | open: probable mistake |
| 20 | Guitar | 58–61 | real C5 noteheads (written): 58 / 60 single C5 eighths between the chords, 59 / 61 four C5 eighths | slash noteheads (pitch B) in their place | open: probable mistake (the pitch is lost) |
| 20 | Utility | 11, 19 | last chord of staff 1: G3 + E4 G4, the same as the chord before | G3 C4 E4 | open: probable mistake |
| 20 | Utility | 39 | staff 1 fourth 16th E♭5 (flat printed, the lower staff has E♭ too) | E5 natural | open: probable mistake |
| 20 | Utility | 90 | last eighth A in both staves (no accidental, key F) | B♭ like the seven before | open: probable mistake |
| 20 | Utility | 92–107 | "CELESTA (loco)", staff 1 at the printed pitch | an octave below the printed notes, no 8va line | open: probable mistake |
| 20 | Utility | 99 | staff 1 second four eighths F5 G5 A♭5 B♭5, as in the other bars 92–107 | G A♭ B♭ C, a step higher (besides the octave above) | open: probable mistake |
| 20 | PianoReduction | 26, 27, 71, 72 | last chord of the upper piano staff: lower note B♭3 (26, 71) / A♭3 (27, 72), the same as in the first chord | G3 / F3 | open: probable mistake (the repeat 71–72 copies it) |
| 20 | PianoReduction | 111–114 | lowest bass note F1 (on the 4th ledger line; chord symbol F): last eighth of 111–113, four eighths in 114 | A1 | open: probable mistake (checked at 400 dpi) |
| 20 | PianoReduction | 135 | upper F4 + F5 eighth (accent), lower F1 + F2 eighth | upper F3 + F5 quarter, lower A2 + A3 eighth | open: probable mistake |
| 20 | Drums | 36 | snare (C5) on beat 2 under the hi-hat | no snare | open: probable mistake |
| 20 | Drums | 45–46 | 45 "Fill" (four slashes), crash on beat 1 of 46 | 45 a written-out groove with the crash, 46 without crash | open: crash one bar early; how to write a slash "Fill" bar is a convention question |
| 20 | Drums | 131–133 | snare on beat 2 on C5, the same line as beat 4 ("ride (bell)") | B4 on beat 2 | open: probable mistake |
| 1a | Cello | 4 | second 16th C♯4, a step above the B3 | D♯4 | open: probable mistake |
| 1a | Guitar | 10, 14, 19, 25 | third eighth B♭4 (written), E♭sus4 pattern E♭ A♭ B♭ | A♭ | open: probable mistake (the same in all four bars) |
| 1a | Utility | 1–4 | lower staff in bass clef (B3, C♯4, E3) | lower staff in treble clef: the same positions read G♯5, A♯5, C♯5 | open: probable mistake (wrong clef) |
| 1a | PianoReduction | 2 | upper piano staff G♯4 dotted half tied to a G♯4 eighth, F♯4 eighth | dotted half, eighth rest, F♯4 | open: probable mistake |
| 1a | PianoReduction | 9–10 | piano staves rest; the notes are a "Gtr. (acoustic)" cue on the staff above | the cue notes in the piano right hand | mistake (user 2026-10-16): the piano rests there |

## Anastasia

| Song | Part | Bars | Printed | Truth | Status |
|---|---|---|---|---|---|
| 4 | all | 132A–C | cut "-> 132C" | 132A and 132B don't exist: 211 bars (a cut to a lettered bar skips the earlier letters; a cut to a plain number keeps empty bars) | convention (pipeline follows it) |
| 1, 2, 4 | brass | | "Mute", "St. Mute", "Cup Mute", "to Cup" + cup mute, "Open", "to Mute" | "gedämpft", "offen"; "to ..." and an "Open" at the start left out | convention (pipeline translates, 2026-10-15) |
| 4 | Dmitry, Vlad | | octave as printed | an octave below the output | convention: the truth is right, the PDF is wrong (user, 2026-10-15); not visible from the PDF, error accepted |
| 4A | Drums | 1–3 | x / ⊗ heads, rolls, "mallets": a suspended cymbal played with mallets | a "Xylophon" part with pitches | mistake (user 2026-10-17): replace the Xylophon by a cymbal in the truth; then the workbook Drums row (`Xylophon`) and the `mallets` alias in show.yaml must follow |
| 1, 2, 4 | singers | | apostrophes `'` | typographic `‘` (we‘re, don‘t) | convention: the metric treats typographic and plain quotes as the same (user 2026-10-16) |
| 1 | Flöte 2, Violine 2 | 5 | beat 3 E♮6 / E♮5 (natural printed), then F♯ | E♭ (D♯ in the export) | open: probable mistake (the Klavierauszug truth has E) |
| 1 | Klarinette in B 2 | 3 | "1, 2 Clarinet": F♯5 A5 A5 B5 (written) | F♯5 E5 A5 B5 | open: probable mistake |
| 1 | Klarinette in B 1 | 30 | first quarter E4 (written, bottom line), then (♮)B4 C♯5 E5 | G♯4 | open: probable mistake |
| 4 | Violine 2 | 90 | third note B4 (r E♯4 B4 ♮D5 …) | G♯4 | open: probable mistake |
| 4 | Oboe | 18 | eighths G4 F4 E♮4 F4, then G4 | fourth eighth D4 | open: probable mistake |
| 4 | Trompete in B | 76 | last eighth B♭4 (written) | G4 | open: probable mistake |
| 4 | Trompete in B | 174 | A♭4 F4 A♭4 D♭5 (written, key 5 flats: F natural) | F♭4 | open: probable mistake |
| 4 | Posaune | 205 | second eighth B♭3 (flat printed) | B3 | open: probable mistake |
| 4 | Keyboard 1 | 114 | left hand last eighth E♮2 (natural printed) | E♭2 | open: probable mistake |
| 4 | Violoncello, Kontrabass (Posaune, Keyboard 1 likely) | 60, 98, 140 | G♭ (60) / E♭ (98, 140) | F♯ / D♯ (sounds the same) | open: spelling only; a pattern, so logged (user 2026-10-16: log spelling only when many) |
| 4 | Klavierauszug | 87 | right hand: a dotted-half F♯4 (courtesy "(♯)") under the A4, then G♯4 A4 16ths and F♯5 | the A4 quarter, 16ths and F♯5 only: the lower dotted half is missing | open: probable mistake |
| 4 | Klavierauszug | 103 | first right-hand chord with D♯5 (sharp printed) | D5 | open: probable mistake (the Oboe truth has D♯5 here) |
| 4 | Klavierauszug | 105 | second right-hand chord with D♯5 (sharp printed) | D5 | open: probable mistake |
| 4 | Klavierauszug | 148C | second chord B4 D♯5 F♯5 B5 (two sharps printed) | B4 E5 G♯5 B5 | open: probable mistake |
| 4 | Violine 1 (and other strings) | 26 places | Tesseract finds 13 "pizz." / "arco" on the scan | 26, strictly alternating pizz. / Arco | open: check whether every Arco is printed or added by the corrector (2026-10-16) |
| 4 | all | 32, 81, 97, 101, 114, 144, 157, 159, 177, 181 | double barline (Violin 1, Reed 3, Keyboard 2; mostly before key changes or rehearsal marks) | single barline; 97, 101, 144, 157 were in the previous truth and are gone in `_fertig` | open: probable mistake |
| 4 | Posaune, Fagott | 29–36 | Bassoon: 29–30 grace F♯3 + G3 whole, 31–32 G2 eighth figures, 33–36 A♭3 B3 / C4 B3 / C4 G3 E4 / F♯4 D4 F4; Trombone: 31 r + four G3 eighths, 32 r G3 r A♭3 G3 A♭2 G2 r, 33–36 rests | the Bassoon line in Posaune, Fagott rests | open: probable mistake (the previous truth had the Trombone right) |
| 4 | Fagott | 41–43 | 41 r G3 E3 C3 D3 (accent) r; 42 G2 r G2 r G2 D3 G2 D3; 43 G2 r G2 A♭3 G3 A♭2 G2 r | rests | open: probable mistake |
| 4 | Klarinette in B 2, Flöte 2 | whole part | Klar 2: ~20 dynamics after bar 32 (33 mp … 171 mf), sfz 43 / 136, hairpins 42–43, 101, 105, 135–136, 148, 148C, 163, accents 42 / 62 / 64, tenuto 35, slurs 123 / 125, tenuto (not accent) 163; Flöte 2: f + cresc 181, p 182, sfz 185 | missing | open: probable mistake, low priority (Reed 2 is a `plain` row, marks are not scored) |
| 4 | Xylophon | 1–27, 169–173 | "mallets": x / ⊗ heads, rolls, "choke" = suspended cymbal with mallets | a Xylophon part with pitches (G5, G♭5 169–170, G♯5 172–173) | mistake (user 2026-10-17): cymbal, not xylophone (same as 4A; songs 1 and 2 have no Xylophon notes) |
| 4 | Keyboard 1, Keyboard 2, winds, Drums | whole parts | patch labels and playing words ("LH: Tuba", "RH: Celesta [bring out]", "Pizz. Strings [both hands]", "Solo", "lead", "(under strings)", "poco a poco cresc.", "choke", "R.S.", "pick up tamb.", "snares on / off", "+ Tamb") | none (the keyboard truths have no words at all) | open: probable mistake (user 2026-10-17: log it) |
| 4 | Keyboard 2 | 26, 82 | "RH: Trem Strings sounding 8vb", "RH: Bassoon – sounding 8vb" | printed pitch, no 8vb line, no label | open: how to write it (Ghost 20 Utility writes the patch octave as an 8va line) |
| 4 | Keyboard 2 | 82–84 | slurs from the grace notes | no slurs | open: probable mistake (minor) |
| 4 | Triangel | 94, 97 | triangle noteheads | x head (94), normal head on the last eighth of 97 | open: probable mistake (one head type) |
| 4 | all | 25, 28, 95–96, 99–100, 121–122, 186–193 | cuts "[to] 26", "[to] 29", "[to] 97", "[to] 101", … | the skipped bars are empty bars | convention (user 2026-10-17): cut bars stay empty |
| 4 | Xylophon | 27 | drum set: bass drum F4 (accent, f) + x cymbal "choke" | the kit notes in Xylophon (F4 + F5 x) | open: probable mistake |
| 4 | Xylophon | 32 | snare / bass drum bar ("sticks"), already in Schlagzeug and Tamburin | the same bar again in Xylophon | open: probable mistake (duplicate) |
| 4 | Schlagzeug | 41 | bass drum F4 on beats 1, 2, 3 | beats 1 and 3 | open: probable mistake |
| 4 | Schlagzeug | 70 | beat 1 snare + x cymbal, beat 2 snare C5 (accent), no bass drum | bass drum F4 (accent) on beat 1, beat 2 empty | open: probable mistake |
| 4 | Schlagzeug | 72, 73, 76, 77 | bass drum F4 + foot hi-hat x on D4 ("foot hat a la piatti") | F4 only (106, 107, 164, 165, 204 have the D4 x) | open: probable mistake |
| 4 | Tamburin, Schlagzeug | 140 | Tambourine quarter, quarter, eighth, then three snare C5 eighths | four Tambourine eighths, Schlagzeug empty | open: probable mistake |
| 4 | Schlagzeug | 144 | bass drum F4 beat 1, rest beat 3, F4 (accent, fz) beat 4 | F4 beat 1, F4 (accent) beat 2 | open: probable mistake |
| 4 | Schlagzeug | 196 | lower voice: quarter rest, F4 on beat 2 | F4 on beat 1 | open: probable mistake |
| 4 | Schlagzeug, Tamburin | 199–202 | "tamb.": diamond-head rolls (199, 200, 202), hits 200 beat 3 (marcato), 201 beats 2 and 4 | x heads on F5 in Schlagzeug, Tamburin empty | open: probable mistake |
| 4 | Keyboard 2 | 32 | first right-hand chord D4 G4 A♮4 (natural printed, as in 31) | A♭4 | open: probable mistake |
| 4 | Keyboard 2 | 57 | left hand F2 G2 A♭2 C3 | last eighth D3 | open: probable mistake |
| 4 | Keyboard 2 | 75 | third right-hand chord E♮4 G4 C5 (natural printed); left hand C4 B♮3 B♭3 (flat printed) | E♭4; left-hand third note B3 | open: probable mistake |
| 4 | Keyboard 2 | 103 | first right-hand chord B4 D♯5 (as in the Klavierauszug) | D5 | open: probable mistake (same as the Klavierauszug row above) |
| 4 | Keyboard 2 | 126–127 | right hand D4 whole note tied over both bars, &lt; &gt; | right hand rests | open: probable mistake |
| 4 | Keyboard 2 | 138 | first right-hand chord B♭4 D5 G5 | D5 G5 B♭5 | open: probable mistake (B♭ an octave up) |
| 4 | Keyboard 2 | 137 | last chord A4 B♮4 D5 F5, staccato | the same with a falloff | open: probable mistake (no falloff printed) |
| 4 | Keyboard 2 | whole part | dynamics 1 f, 32 sfz, 41 mf, 43 sfz, 62 / 64 / 69 f, 71 mp, 81 mp + sfz, 102 / 115 / 149 mp, 136 sfz, 158 / 170 / 178 mf; hairpins 14, 22, 31–32, 40, 42–43, 69, 81, 135–136; accents 41; 57 staccato / tenuto / LH slur; "poco a poco cresc." 58 | missing | open: probable mistake |
| 4 | Keyboard 2 | 196–206 | not in the scan (PDF page 29 is already 4A, printed page 30 missing) | rests | open: unverifiable; truth rests may be wrong |
| 4 | Klar 2, Flöte 2, Keyboard 2, percussion | e.g. Klar 2 27, 32, 43; KB2 51, 81, 177, 185, 194; Drums 27, 61, 144, 177 | marcato (^) | accent (&gt;); the string truths use strong-accent (81, 202, 206) | mistake (user 2026-10-17): marcato = strong-accent in the truth, as in the strings |
