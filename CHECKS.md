# Open questions

Answer inline (or tell Claude); resolved items move into `docs/PLAN.md`.

## Big run

1. **Full grid scope.** Proposed (after the weed run): one fresh base run `pipeline-allreaders` (homr + crops of
   zeus, clarity, smt-sys, transcoda) on every truth song, then 168 variants reassembled from it (assembly only,
   reassembled = fresh run, checked on Ghost 1a / Anastasia 4A):
   `ocr_engine` {tesseract, easyocr, paddle, doctr} x `measure_vote` {none, ola} x `prefer` {auto, crop first,
   audiveris first} x `ensemble` {none, [zeus, clarity, smt-sys], [clarity, transcoda], all four} x
   `ensemble_pick` {agree, agree-keep}. Estimate ~20 h. Left out: `repairs: false`, other main readers and all page
   engines (40 %+ worse in the weed run), `auto_beam` (beams don't count in the penalty), tuned
   `ensemble_weights` (only `pipeline-ensemble-wk` has them; it scored 1182 vs `pipeline` 1186 at 18x the time).
   OK, or add / drop axes?
2. **OMR-NED / TEDn (`--full`)** in the big run? It is the slow, exact musicdiff edit cost; on 168 variants it would
   add days. Proposal: only on the final top 3.
3. **smt-fp and the crash.** The PC crashed while `smt-fp` ran (full-page model on CPU). If it crashes there again,
   drop `smt-fp` from the weed run (it can't win: page engines are 2-4x worse than the pipeline)?
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
