# Final corrective cycle: brief for the fresh independent reviewers (owner decision D-083, item 10)

You are an independent reviewer of a change to the CITERIFT Stage 04 detection engine. You did not write it. Your job
is to find what is wrong, missing, or overstated, and to classify each finding. Agreement is not the goal.

## What happened

- Two prospective evaluations failed gate 04-I and stay NOT PASSED, unchanged: P with engine dt-1 (frozen
  `b5bf8ed`) and P2 with engine dt-2 (freeze-2, `28ba646`). Read `DECISIONS.md` D-071 to D-083 first; D-083 is the
  owner's authorization of this final cycle (its 14 items are the requirements).
- The P2 failure: `en-27958530` unit `un-00004`, a `{{cite journal}}` by "Robert Garry" titled "… – Comments", whose
  DOI and PMID are the original identifiers of the retracted Retraction Watch record by Hon, Ng and Leung. dt-2
  decided from identifiers only and gave `RETRACTED_WORK_CITED`.
- Root cause and architecture: `docs/verification/stage-04/final-cycle/ROOT_CAUSE_AND_ARCHITECTURE.md`.

## What changed (compare with `git diff 6663314 HEAD`; the branch has no uncommitted engine change)

- Specification (normative): `final-cycle/BIBLIOGRAPHIC_SPEC.md` (bib-1 and table dt-3); stage documents
  `SPECIFICATION.md` 7.3 (row D-13a) and 7.3b, `MATHEMATICAL_MODEL.md` (`bc(c)`), `RISK_ANALYSIS.md` R4-04a.
- Production: `src/citerift/investigation/bibliographic.py` (new, bib-1), `data/bib-profile-1.json` (CS1 alias
  profile), `dt1.py` (table dt-3: rule D-13a, comparisons), `adapters/normalize.py` (cited object per unit),
  `adapters/lookup.py` (observation v3 `records`), `adapters/detector.py`, `adapters/detect.py`, `adapters/plan.py`,
  `explanations.py`, `__init__.py` (engine 0.4.0); `fold.py`, `errors.py`, `operations.py`, `controller.py` (E-07
  engine-identity guard); `cli.py` (E-05 memory-root redaction).
- Schemas: `schemas/investigation/v1/common.schema.json` (5.0.0), `claim.schema.json` (4.0.0),
  `candidate-inputs.schema.json` (2.0.0), `lookup-observation.schema.json` (3.0.0).
- Reference model and oracle: `simulations/stage04/bib_reference.py` (+ `bib-reference-profile.json`),
  `dt3_reference.py`, `decision_space_dt3.py`, `oracle-dt3/` (when present). The dt-1 and dt-2 models and oracles are
  unchanged.
- Tests: `tests/stage04/test_final_bib.py` (corpus, differential, detector level), `test_final_lows.py`,
  `test_corrective_compat.py` (E-07), `test_final_oracle.py` (when present), and identity updates in support files.
  `test_p2_evaluation.py` and `test_step13_evaluation.py` were amended in a separate commit pending an owner decision
  (they check the old engines from git; review that commit too).
- Evidence: `final-cycle/corpus/` (58-case adversarial corpus), `final-cycle/fail-first/` (the dt-2 engine at
  `6663314` versus dt-3 on the same inputs), `final-cycle/lows/` (A-04 census, D-05 and E-05 fail-first logs),
  `final-cycle/bounds/`, `final-cycle/regression/` (when present), `final-cycle/BUILD_VS_ADOPT.md`.
- Exposure manifest v3 builder: `docs/verification/stage-04/freeze-3/exposure/build_exposure_manifest.py`.

## Fixed constraints (from the owner; do not recommend violating them)

- Gate 04-I is not amended or weakened; neither historical evaluation is modified, rescored or rerun; P and P2 files,
  seeds, draws, labels, runs, scores and reports stay unchanged.
- No DOI, Garry, Virology Journal, literal "Comments"-suffix or publisher-specific exception; no rule derived only from
  the P2 failing item; no fuzzy threshold without an independent specification and adversarial evidence; a comment,
  reply, editorial or erratum must not be classified as the retracted work just because it carries its DOI or PMID.
- A material conflict is never positive; prefer abstention. D-072 (strict role-collision rule) stays unless proven
  safe. Stage 02 and Stage 03 are not changed (maintenance would need a separate owner decision).
- No new dependency (Build-vs-Adopt review); D-064 is not weakened; the 5 s p95 target stays NOT_MET if not met.

## How to work

- Read code and evidence. You may run targeted commands (`uv run pytest tests/stage04/<one file> -q -p
  no:cacheprovider`, small Python probes). Do **not** run the whole test suite or any long tool (CPU is shared with
  measurements), do not use the network, do not modify, stage, commit or delete any file except your own review file.
- The pinned Stage 02 index, if you need it, is
  `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/s14/index/rw-2f116e9ffed718e6.sqlite`
  (read-only; open it with `sqlite3` URI `mode=ro`, or `citerift.retraction.query.Index(Path(...))`).
- Never read campaign labels to judge the engine's regression (`LOCK.json`, adjudications, `SCORES.json`): reviewer
  finding F-08 of the corrective cycle forbids joining regression results with campaign labels.
- Write your review to `docs/verification/stage-04/final-cycle/review/REVIEW_<YOUR LETTER>.md` with: scope read,
  method, findings (each with id `<LETTER>-NN`, severity CRITICAL / HIGH / MEDIUM / LOW / INFO, evidence with
  file:line or command output, and a concrete recommendation), and a one-line verdict. Distinguish verified fact [V]
  from inference [I].
- CRITICAL: the change can still produce a false positive attachment of the failure's kind, or breaks a stated
  invariant (a material conflict yields a positive; bib-1 creates, restores or moves a decision; dt-3 differs from
  dt-2 without a material conflict). HIGH: a material defect in correctness, evidence or claims that must be fixed
  before a freeze. MEDIUM: a defect or gap that an owner decision or a fix must settle. LOW: a minor defect, an
  overstated sentence, a missing test. INFO: an observation with no action.
