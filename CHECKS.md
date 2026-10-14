# Open questions

Answer inline (or tell Claude); resolved items move into `docs/PLAN.md`.

## Big run

1. ~~Full grid scope~~ **Decided 2026-10-14:** base `pipeline-allreaders` + 42 reassembled variants, Tesseract only
   (OCR variants were within 1 % in the weed run): `measure_vote` {none, ola} x `prefer` {auto, crop first,
   audiveris first} x `ensemble` {none, [zeus, clarity, smt-sys], [clarity, transcoda], all four} x
   `ensemble_pick` {agree, agree-keep}. Tuned `ensemble_weights` left out.
2. **OMR-NED / TEDn (`--full`)** in the big run? It is the slow, exact musicdiff edit cost; on 168 variants it would
   add days. Proposal: only on the final top 3.
3. ~~smt-fp and the crash~~ **Decided:** keep it and resume; drop it only if it crashes the PC again.
4. **Page engines and piano reductions.** Page engines (homr, Audiveris, Clarity, ...) can't write the separate
   `- Voices` / `- Piano` files, so the PianoReduction row counts as "no output" (typed from scratch). Fine, or
   score their single file against the Piano truth part?

## Metric (edit penalty)

5. **Chords:** a chord with a wrong duration costs one action per note (MuseScore: one action for the chord).
   Charge 1 per chord instead?
6. **Octave regions:** a section an octave off after an instrument change (Celesta in Ghost 20 Utility) is charged
   per note. Charge 1 per region (select range + Ctrl+Up)?
7. **Rehearsal marks:** neither truth has numeric rehearsal marks, so the pipeline now drops boxed numbers
   (bar numbers). Is that your convention for all shows?

## Workbook / truth

8. **`unfinished`**: a song key row (like `truth`): `unfinished | Voice 1, Drum Kit` lists truth parts that are not
   hand-corrected yet; bench skips them until you remove them. Ghost 20 has `unfinished: Voice 1` and the
   PianoReduction row maps `Oda Mae=Voice 1` already. Song-level OK, or do you want a per-row column?
9. **Anastasia 4 truth**: when does it come, and which choir parts does it have (for the workbook mapping)?
10. **Gated SMT models** (`PRAIG/smt-fp-mozarteum`, `-polish-scores`): is the Hugging Face access approved? Then set
    `HF_TOKEN` and they go into the big run.
