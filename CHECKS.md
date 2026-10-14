# Open questions

Answer inline (or tell Claude); resolved items move into `docs/PLAN.md`.

## Big run

1. ~~Full grid scope~~ **Decided 2026-10-14:** base `pipeline-allreaders` + 42 reassembled variants, Tesseract only
   (OCR variants were within 1 % in the weed run): `measure_vote` {none, ola} x `prefer` {auto, crop first,
   audiveris first} x `ensemble` {none, [zeus, clarity, smt-sys], [clarity, transcoda], all four} x
   `ensemble_pick` {agree, agree-keep}. Tuned `ensemble_weights` left out.
2. ~~OMR-NED / TEDn~~ **Decided 2026-10-14:** `--full` on every variant of the full run (adds days). The sweep
   ranking shows a mean OMR-NED column; `--full` now also works with `--resume` / `--rebench`.
3. ~~smt-fp and the crash~~ **Decided:** keep it and resume; drop it only if it crashes the PC again.
4. ~~Page engines and piano reductions~~ **Decided (c):** PianoReduction rows leave the sweep ranking when a page
   engine is in it (`split` rows, for every engine, so totals compare like with like). Was: The pipeline writes a PianoReduction as two files, `- Voices` (a part per
   singer) and `- Piano`; the workbook maps those parts by name (`Piano=Klavierauszug, Anya=...`). Whole-page
   engines (homr, Audiveris, Clarity, ...) write one file whose parts are called "Voice", "Piano", "" etc., so
   no name matches and their PianoReduction row is charged as typed in from scratch. Options: (a) keep it so (the
   pipeline's split is part of what it does better), (b) compare their whole file with the Piano truth part only,
   (c) leave the PianoReduction row out of the ranking for page engines.

## Metric (edit penalty)

5. **Chords:** a chord with a wrong duration costs one action per note (MuseScore: one action for the chord).
   **Done (a):** in truth bars written only in chords, a chord with the right pitches and one wrong duration = 1.
6. ~~Octave regions~~ **Done 2026-10-14:** 1 action per section one or two octaves off (`edits._octave_regions`).
7. ~~Rehearsal marks~~ **Decided:** numeric marks are dropped in every show. Every numeric mark Audiveris read was a
   boxed / printed bar number (Anastasia 1 and 2: "10", "18", "30", "54", "66" over bars 10 ... 66; Ghost 20: one
   over nearly every system, "9", "15", "17", "26", ...; Ghost 1a: "11", "16", "22", "28"). They are now used as
   bar-number evidence in every score type (was: vocal scores only).

## Workbook / truth

8. ~~`unfinished`~~ **Decided:** song-level key row stays.
9. ~~Anastasia 4 truth~~ **Wired 2026-10-14** (`04_A_rumor_in_St_Petersburg.mscz`, partial: no Reed 2 / 3,
   Keyboard 2, percussion yet; Gleb and Black Marketeer #2 read over the Frauen staff). Was: the run `20261013-222736` read 17 singer labels from the PianoReduction: Voice 1, Men,
   Dmitry, All, First Woman, Second Woman, First, Second, Others, Women, Solo Woman, Vlad, Gleb, Black
   Marketeer #2, Both, Ensemble, Group 1. The workbook needs `label=truth part` entries for them, so: which
   singer / choir parts will the truth file have, and where do group labels (All, Ensemble, Both, Men, Women)
   go? Open: see the question in chat.
10. **Gated SMT models** (`PRAIG/smt-fp-mozarteum`, `-polish-scores`): access not approved yet (2026-10-14). Then set
    `HF_TOKEN` and they go into the big run.
