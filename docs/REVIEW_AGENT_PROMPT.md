# Review and fix an Anastasia transcription (prompt template for a new chat)

Copy everything below the line into a new Claude Code chat in `~/museScribe`. Replace `<SONG>` (the workbook sheet
name, e.g. `6`) everywhere. Everything else the agent finds itself.

---

## Task

Song: **Anastasia `<SONG>`** (workbook `data/anastasia/songs.xlsx`, sheet `<SONG>`)
Score to fix: `results/anastasia/<SONG>/combined.mscz`
Result: `results/anastasia/<SONG>/combined_checked.mscz`

The score was made by our OMR pipeline from scanned orchestra parts. There is **no ground truth** for this song.
Compare the score with the printed PDF pages and edit it until it matches the print as closely as possible,
following the conventions below. Fix the file; no list of suggestions. Work on your own until the end: the user
only reads the final report and checks the doubts you list.

Start **every** shell command with `source ~/.local/share/omrbench/env.sh && ...` (venv with lxml, PyMuPDF,
music21, `omrbench`; `python` does not exist without it).

## Budget: Claude usage is the scarce resource

Runtime and Codex usage are not a concern; Claude tokens are. So:
- **Codex reads first.** Codex (GPT, via `scripts/review_codex.py`) compares every book with the print; Claude checks
  only what Codex and `lint` flag, plus a full pass on Keyboard 1 and the drum book, where most errors are. (Song 5
  test: Codex found 67-88 % of the bars with errors at 63-90 % precision in Violine 2, Horn and Keyboard 2.)
- **Images are the expensive part.** Each image costs up to about 1 600 tokens and stays in the context for every
  later turn. Look at one system (a `--clip` band) at 150-200 dpi, not whole pages at high dpi; zoom (300 dpi, with
  an x range) only on a bar you still cannot read. Never load the same image twice: write down what you read
  (`review/<book>/notes.md`, one line per bar) and work from the notes.
- **Subagents run on Sonnet** (Agent tool, `model: "sonnet"`), each for at most 4 pages, so their context stays
  small. The lead stays short too: it does not read pages itself except to settle structure.
- **No tool building.** `review_tool.py`, `review_lint.py`, `review_edit.py` cover the edits seen so far. A one-off
  loop over their helpers is fine; a missing helper goes into the report, not into a new script.
- Read only this prompt and `review/plan.md`; `docs/CORRECTION_INFORMATION.md` only for a rule question this prompt
  does not answer.
- **Usage limit:** keep `review/progress.md` current (phase, books done / in progress with their last page, open
  points). After a stop, a new lead reads it and `review/plan.md` and goes on from there.

## Rules

- Never change `combined.mscz`. Work in `results/anastasia/<SONG>/review/` and write the result to
  `combined_checked.mscz` (update it after each phase, so a stop midway still leaves a usable file).
- Keep the parts: do not add, remove, rename or reorder parts or staves. A part that is missing entirely goes into
  the doubts list.
- Do not read anything that contains a hand-corrected version of this song: its file in `data/anastasia/truth/`,
  `results/cache/`, `results/anastasia/bench/`, `results/errors/`, `docs/ANASTASIA_TRUTH_FIXES.pdf`. Truth files of
  **other** songs are fine as style examples.
- Never touch `data/` or the pipeline code; do not run `omrbench transcribe` (it rebuilds the song folder).
- The printed page is the reference. Where a convention below says otherwise (cues, German words, octave lines),
  follow the convention. Where the scan is unreadable or a page is missing, leave the bar and list it as a doubt.
- Change a bar only when the page shows clearly that it is wrong. A wrong "fix" costs as much as a missed error.
  Codex and `lint` findings are hints, not facts: look at the system before acting on one.
- Before you add notes the pipeline did not have (a whole figure, a passage), check that they are not another
  book's line printed as a cue or for reference: if another book of the song has the same notes in the same bars,
  leave them out (list it as a doubt if unsure).

## Files

| File | What it gives you |
|---|---|
| `data/anastasia/songs.xlsx`, sheet `<SONG>` | rows `time` (bar: meter), `key` (bar: sharps + / flats -, concert pitch), `bars` (expected bar count, lettered bars included), `letters` (e.g. `49A-B`); then one row per PDF book: `pages` (1-based PDF pages), `skip` (systems at the top of the first page that belong to the previous song), `instruments` (doubling or drum book instruments, in order), `extra` / `notes` (special handling, e.g. duet labels) |
| `data/anastasia/show.yaml` | `parts:` (transposition, German name per book), `instruments:` library, `male_voices` |
| `data/anastasia/pdfs/<book>.pdf` | the printed parts: Violin 1, Violin 2, Cello, Bass, Reed 1-3, Horn, Trumpet, Trombone, Keyboard 1, Keyboard 2, Drums-Percussion (scans), PianoReduction (vector PDF with a text layer) |
| `results/anastasia/runs/<run>/run.log` | per book: failed crops, inserted rest bars, extra bars read (run id in `results/anastasia/<SONG>/manifest.json`) |
| `data/anastasia/truth/*.mscz` of other songs | hand-made scores in the house style: how a drum kit, a cut, an octave line, a tremolo is written (`extract` + `dump` work on them too) |
| `drumkit.yaml` | the drum legend of the truths: staff position and notehead -> MuseScore drum instrument |

## Tools

```bash
T=scripts/review_tool.py; R=results/anastasia/<SONG>/review
python $T extract results/anastasia/<SONG>/combined.mscz $R/work     # -> $R/work/combined.mscx
python $T parts $R/work/combined.mscx                                 # parts, staff ids, bars per staff
python $T check $R/work/combined.mscx --bars <N>                      # MuseScore export: bar count / length per part
python $T lint $R/work/combined.mscx [--staves 12,13] [--fix-safe 1] [--plain "Violine 1"]  # suspicious bars
python $T dump $R/work/combined.mscx 12,13 --bars 1-20,40-45 [--letters 49A-B]  # staves as text
python $T splice $R/work/combined.mscx $R/kb2/combined.mscx 12,13 $R/work/combined.mscx   # take staves from a copy
python $T pack $R/work results/anastasia/<SONG>/combined_checked.mscz
python $T render "data/anastasia/pdfs/Violin 1.pdf" 25 $R/img/vl1-25a.png --dpi 200 --clip 0,0.2          # one system
python $T render "data/anastasia/pdfs/Violin 1.pdf" 25 $R/img/vl1-25z.png --dpi 300 --clip 0.05,0.15,0.4,0.7  # zoom
python scripts/review_codex.py $R/work/combined.mscx 12,13 "data/anastasia/pdfs/Keyboard 2.pdf" 32-38 $R/codex/kb2 \
  --song <SONG> --label "staves 12, 13 = Keyboard 2 (right / left hand)" [--skip K] [--letters 49A-B] [--passes 2]
```

- `dump` prints written pitch (as printed in the part; drum staves: the drum instrument name and notehead),
  `C5/4.` = dotted quarter, `rM` = whole-bar rest, `~` = tie, `[articTenutoAbove]` / `[arpeggio]` / `[trem:r16]` =
  marks on the chord, `Fermata` before a chord = fermata on it, `<mf>` = dynamic, `cresc(->17@3)` = hairpin start with
  its end (bar 17, 3 quarters after the bar start), `)hairpin` = its end, `Slur(` / `)Slur`, `gliss(`, `"word"` after
  a note = lyric (`-` = more syllables follow, `+2` = verse 2), `<mf>@3/2` = a mark between notes, 3/2 quarters
  after the bar start; `50[49A]:` = transcription bar 50 is printed bar 49A (with `--letters` from the workbook).
  Read the score with it; read raw XML only to edit.
- `check` exits with status 1 unless it ends with `OK`, and it ends with `OK` only when MuseScore opens the score without complaint (same bar count everywhere, every bar
  filled, no whole-bar rest of the wrong length) and every part has `<N>` bars.
- `lint` lists per staff: wrong bar lengths, notes out of range, double accidentals, clef changes in wind / string
  parts, slurs / hairpins over more than 4 bars, spanner halves without partner, duplicate hairpins and ties,
  articulations on rests, repeated system text, labels and playing words, fermatas most parts have, a keyboard
  playing the other keyboard's line, doubling parts that disagree. `--fix-safe 1` applies the safe ones (marked
  `[fix-safe]`: whole-bar rest lengths, duplicate hairpins, rest marks, repeated system text, fermatas 2/3 of the parts
  have at the same position). Pass the workbook `plainArticulation` parts as `--plain` (part names, comma-separated).
- `review_codex.py` renders the pages at 200 dpi, sends every 2 pages with the staves' `dump` and a short conventions
  list to Codex in an empty folder (Codex never sees the repository) and writes `codex-p<a>-<b>.txt`: lines
  `bar | staff | transcription has | page shows | kind | sure/unsure`, ending with `covered | <bars> | unreadable:
  <bars>`. Bars of your pages outside `covered`, and the `unreadable` ones, are yours to read. `--passes 2` adds an
  independent second reading (`*.r2.txt`): a point both passes report is very likely real. It retries a failed call
  once; a file saying `FAILED` means: work on that book without Codex and say so in the report. Never stop Codex
  processes by name.
- `PianoReduction.pdf` has exact text: `fitz.open(pdf)[page-1].get_text("words")`.

**Editing** (`scripts/review_edit.py`, read its docstring; positions are bar + `Fraction` of a whole note):

```python
import sys; sys.path.insert(0, "scripts"); import review_edit as E; from fractions import Fraction as F
tree, score = E.load(path)
E.set_voice(score, 13, 25, "C4+E4/8 r/8 3:2{ D4/8 E4/8 F4/8 } G4/4.~")   # bar 25, voice 1 (vi=1: voice 2)
E.add_hairpin(score, 13, (25, F(1, 4)), (27, F(0)), cresc=True);  E.del_hairpin(score, 13, 25)
E.add_dynamic(score, 13, 25, F(0), "mf");  E.del_dynamics(score, 13, 25, {"ff"})
E.artic(E.chords(score, 13, 25)[0], "articTenutoAbove");  E.del_artics(chord, {"articStaccatoAbove"})
E.add_tie(score, 13, 25, -1);  E.add_slur(score, 13, (25, 0), (26, 2));  E.add_fermata(score, 13, 25, F(1, 2))
E.add_arpeggio(chord);  E.add_gliss(score, 13, (25, 0, 0, 60), (25, 0, 1, 67), sid2=None);  E.add_barline(score, 13, 25)
E.set_lyric(chord, "dreams", "end");  E.del_spanner(score, 13, "Slur", 25);  E.drop_orphans(score, 13, "Tie")
E.save(tree, path)
```

- `set_voice` takes **written** pitch as `dump` prints it (transposing parts get concert `<pitch>` / `<tpc>` and the
  written `<tpc2>`); `~` ties to the next chord (write the next bar first when the tie crosses the barline),
  `n:m{ ... }` = tuplet, `grace:D5/8` = grace note, `rM` = whole-bar rest, drum staves take the `dump` names
  (`Acoustic_Snare/8`). It refuses a bar that does not add up, and a chord that still carries a tie / slur.
- `.mscx` facts: `<pitch>` is concert MIDI; spanners (ties, slurs, hairpins, glissandi) are pairs with
  `<next>` / `<prev><location>` (`<measures>` = bar difference, `<fractions>` = position difference in whole notes);
  slurs sit inside the chord, ties and glissandi inside the note; HairPin subtype 0 = cresc, 1 = dim. Give new
  elements no `<eid>`. A bar inserted / deleted to repair one part's drift goes into that part's staves only (phase
  1); the bar count must end equal in every staff.

## How the score was made (where the errors come from)

- Audiveris finds the systems and staves of each scanned page; homr reads each staff crop; the pipeline joins them,
  numbers the bars like the print and adds marks from Audiveris (dynamics, hairpins, articulations by x position).
- Output bar n = printed bar n. Lettered bars (`49A`) are bars of their own. A cut to a plain number ("[to] 26")
  keeps the skipped bars as empty bars; a cut to a lettered bar ("-> 132C") skips the earlier letters.
- Multi-measure rests are expanded from the printed count and bar numbers; a misread count shifts bars.
- Doubling books are split per instrument (Reed 1 -> Flöte 1, Piccolo, Oboe, ...) at the printed labels; the drum
  book per instrument (Triangel, Pauken, Schlagzeug, ...) per the workbook `instruments` cell.
- Keyboard 1 is a conductor book: only its lowest two staves (the piano) are read. Its piano staves also show
  other players' lines at times (often Keyboard 2's figures, or a reed / string line): those notes belong to the
  other book, not to Keyboard 1. PianoReduction: only the singers (one part per printed singer label); the piano of
  the Klavierauszug is not generated and not your job.
- Cue notes (small heads, or after another part's label up to "Play") are already turned into rests.

## Workflow

You are the **lead**. You own the structure, start Codex and the subagents, and splice their work back.

**Phase 1 (lead): structure.**
1. Read the workbook sheet; `extract`; `parts`; `check --bars <N>`. Make a table: part, staff ids, book, PDF pages,
   skip, bar count, wrong-length bars.
2. Bar count: for a part with too many / too few bars, find where it drifts (printed bar numbers at system starts,
   rehearsal letters, multi-rest counts, page turns, cut marks, lettered bars; use `dump` first, a system image only
   to confirm). Insert / delete bars **in that part's staves only**, so every part ends with `<N>` bars and the key
   / time changes and rehearsal letters line up across parts.
3. Time and key signatures against the workbook rows (key transposed for the part; drums have none).
4. `lint --fix-safe 1`, then `lint` again and keep its list. `check`, `pack`. Write `review/plan.md`: the table,
   the workbook facts (meter, keys, bars, letters), the conventions that matter for this song, and per book the
   `lint` lines of its staves. Start `review/progress.md`.

**Phase 2 (lead): Codex first reading of every book.** One `review_codex.py` call per book (staves of that book,
its pages, `--skip` and `--letters` from the workbook, `--passes 2` for keyboards, drum book and singers), all books
at once in the background (`&`, then `wait`), output to `review/codex/<book>/`. The `--label` is all Codex knows
about the book: name each staff and its instrument; for doubling books where the printed labels switch; for the drum
book the staff of each instrument and, for the kit, the `drumkit.yaml` positions; for singers which printed label
goes to which part (duets to both); and "no articulations / dynamics / hairpins / slurs / fermatas" for a
`plainArticulation` part. This takes a while; Claude does nothing meanwhile.

**Phase 3 (subagents, Sonnet): verify and fix, one book or up to 4 pages each.** Up to 4 at once; subagents of
the same staves (a long book split by pages) run one after the other on the same copy. Each gets this brief (fill in
the brackets):

> Check and fix the part(s) [names] (staves [ids]) of Anastasia <SONG>, `data/anastasia/pdfs/[book].pdf` pages
> [pages] (skip the first [k] systems of the first page). Read `docs/REVIEW_AGENT_PROMPT.md` sections Budget, Rules,
> Tools, Common errors, Conventions, and your book's rows in `results/anastasia/<SONG>/review/plan.md`. Copy
> `review/work/` to `review/[book]/` (if it does not exist yet) and edit only your staves in
> `review/[book]/combined.mscx`; never change the bar count.
> Your list of points: the Codex answers `review/codex/[book]/codex-p*.txt` for your pages and the `lint` lines of
> your staves. For each point: render that system once (`--clip`, 200 dpi), read it, write one line to
> `review/[book]/notes.md`, then fix it, reject it (Codex / lint wrong), or list it as a doubt. Codex misreads too:
> fix only what the page confirms; a point both Codex passes report (`*.txt` and `*.r2.txt`) is very likely real.
> Bars of your pages outside Codex's `covered` line or listed `unreadable` you read yourself. [Keyboard 1 and
> drum book only:] Then go through your pages system by system yourself (same system images, no second load)
> for what Codex missed: bar lengths, pitches and accidentals, ties, missing notes and voices, dynamics, hairpins,
> articulations, slurs, fermatas, tremolos, words.
> Run `check` after each page and `lint --staves [ids]` at the end. Reply in at most 15 lines: staff ids, fixes per
> kind (counts), Codex points used / rejected, last `check` result, doubts (bar, what, why).

When a subagent is done: `splice` its staves into `review/work/combined.mscx`, `check`, `pack`, update
`progress.md`. If `check` is no longer OK after a splice, find the cause or leave that book out and list it.

Book order (largest gain first): Keyboard 1, Keyboard 2, Drums-Percussion, PianoReduction singers, then strings,
reeds, brass. Single-staff books without Codex points and without `lint` lines need no subagent.

**Phase 4 (lead): whole score.** Second Codex round for keyboards, drum book and singers: `review_codex.py` again
on the spliced score into `review/codex2/<book>/`; give the new points (not those already decided in the book's
`notes.md`) to one short Sonnet subagent per book, same brief. Then `lint` on the whole score (fermatas, repeated texts, keyboards playing each
other's lines, doubling parts that disagree): fix what the page confirms (one system image per point). Same
rehearsal letters, key / time changes, double barlines and repeats as printed in each book. Final `check` (must say
OK), `pack`, report.

## Common errors in Anastasia outputs (measured on songs 1-5)

- **Keyboards:** notes missing in dense two-voice bars; a hand or voice dropped; low notes with 3+ ledger lines
  read 2-5 steps too high or missing; accidentals missing or extra (around key changes, carried accidentals); ties
  in chords missing; made-up clef changes; hairpins between the staves missing.
- **Drum book:** the worst book (about 44 % of the hand work left): kit hits missing or at the wrong staff
  position, flams read as hits, hands / feet voices mixed, kit bars routed to another instrument, the kit a few bars
  off after a multi-rest, rolls (tremolos) missing, dynamics and hairpins missing.
- **Singers:** lyrics on the wrong singer or staff, choir syllables on the wrong staff, a stray text line taken as
  a verse, passages missing after a label change, duets that belong to both singers.
- **Single-staff parts:** articulations made up (staccato from dirt) or missing (thin tenuto dashes), dynamics
  missing (`mp`, `mf`, `p`, `f`, `sfz`, `fp`) or the wrong token (`ppp` for `mp`, `fz` for `f`), hairpins missing or
  ending on the wrong note, made-up 2-note slurs or a slur where a tie belongs, "arco" / "pizz." missing, made-up
  words ("solo", "to clarinet"), fermatas missing, tremolo strokes missing.
- **Everywhere:** made-up or missing double barlines, missing repeat starts, made-up system text ("tempo",
  "cresc.", "poco", "colla voce" as a tempo mark).

Rules that catch reading errors: a curve between two neighbouring notes of the same pitch is a tie; an accidental
lasts to the barline in its octave, a tie carries it over, nothing else; all parts change key and meter in the same
bar; a note far outside the instrument's range is a misread (clef, octave line, ledger lines, neighbouring staff);
a clef change in a wind or string part (except cello) is almost always a misread; articulations sit on notes, not
rests (fermatas excepted).

## Conventions (what "correct" means here)

- **Pitch:** sounding pitch under 8va lines (notes an octave up, keep the line). Transposing parts as their part
  is set up (Horn in F, Trompete in B, Klarinette in B, Kontrabass 8vb); remember `<pitch>` is concert pitch.
- **Marks:** every dynamic and hairpin the part's own page prints, also when another part has the same. Every part
  keeps all its marks, except a part marked in the workbook column `plainArticulation`: it keeps only notes, ties,
  dots, tuplets, tremolos and playing words (no articulations, dynamics, hairpins, slurs, fermatas, tempo marks).
  Marcato (^) = strong accent, accent (>) = accent.
- **Hairpins:** start on the note under the open end. A hairpin that leads straight into a printed dynamic (no rest
  between) ends **where that dynamic is** (the start of its note, e.g. `->18@0` for an `f` on beat 1 of bar 18),
  even when the printed tip stops a little earlier. A hairpin over a single held note starts on that note.
  Otherwise it ends at the **end of the last note under the tip** (often the barline), never at the start of that
  note. `dump` shows every hairpin's end as `cresc(->bar@quarters)`: check it against this rule.
- **Clefs:** as printed, also an unusual one (a drum-book timpani staff in treble clef until its bass clef).
- **Tempo and system text:** tempo headings and transitions as printed ("Moderato", "Con mosso (In 1)", "Slower",
  "rit.", "a tempo", "Attacca", metronome marks): once per score, as system text / tempo on the top part, at the bar
  where they are printed; not repeated as staff text in every part. Older truths lack some of them; the print wins.
- **Arpeggios and glissandi:** write them as printed (MuseScore Arpeggio / Glissando elements).
- **Tremolos:** as many strokes as printed. MuseScore's tremolo subtype counts strokes, not a note value: 1 stroke =
  `r8`, 2 strokes = `r16`, 3 strokes = `r32` (also on eighth notes). Drum rolls as printed (usually 3 strokes).
- **Cues:** notes printed small, or under another part's label ("Cl.", "Pno.") up to "Play", are rests.
- **Words:** playing words as MuseScore playing-technique text (PlayTechAnnotation), in German: Mute / St. Mute /
  Cup Mute / con sord. -> "gedämpft", Open / senza sord. -> "offen" (not at the start); "to Mute" / "to Open" left
  out; "pizz." and "Arco" stay. Expression words as printed, as staff text: "cresc.", "molto cresc.", "poco a poco
  cresc.", "rall.", "poco a poco rit.", "molto". A printed "Safety" repeat gets the system text
  "Sicherheitswiederholung". Dynamics only as MuseScore dynamics (p ... fff, fp, sf, sfz, sffz, fz, ...); a printed
  token MuseScore lacks ("sfzp") -> the closest one, listed as a doubt. Patch and doubling labels ("Harp", "Eng Hn",
  "Solo", "LH: Tuba", "snares on") left out. Keyboards carry no expression text. Boxed bar numbers dropped, letters
  kept.
- **"sim." and % signs:** as printed (keep the % sign, keep "sim." without copying the marks).
- **Ties:** a tied chord held into exactly the same chord has a tie on every note.
- **Fermatas:** every part has one where most parts do.
- **Drum book:** "Mallets" = Xylophon (also its x heads); "sticks" marks the kit; a label of another instrument
  inside a kit passage ("tamb.") names only the hits under it. Kit instrument by staff position and notehead from
  `drumkit.yaml`; when a head / position is not in the legend, use the closest instrument the legend has for that
  head and list it as a doubt; laissez-vibrer ties ("l.v.") are left out.
- **Singers:** lyrics verse 1; spoken dialogue dropped; duet labels ("VLAD & DMITRY", "BOTH") go to both singers;
  Dmitry, Vlad and men's choir in treble-8vb.
- **Bars:** double barlines as printed; a double barline printed before a cut "[to] N" goes at the end of the last
  bar before the skipped bars. A pickup bar may be short.

## Report

At the end, in the chat (and the same text in `review/report.md`, written with a shell heredoc if the Write tool
refuses):
- the final `check` result and the `lint` summary line before and after,
- per part: what kinds of fixes were made (one line each),
- Codex: calls made / failed, points used / rejected,
- missing helpers you would have needed (if any),
- **doubts**: every bar you could not settle, as `part, bar: what, why` (unreadable scan, missing page, two
  possible readings, a missing part). These are the only places the user will check by hand.
