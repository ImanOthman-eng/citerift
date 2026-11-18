# Corrective cycle: brief for the fresh independent reviewers (owner decision D-071, section 10)

You are an independent reviewer of a correction to the CITERIFT Stage 04 detection engine. You did not write it. Your
job is to find what is wrong, missing, or overstated, and to classify each finding. Agreement is not the goal.

## What happened

- The frozen engine (commit `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0`, engine 0.2.0, decision table dt-1) failed
  its pre-registered evaluation (gate 04-I). The owner accepted the failed evaluation and authorized one corrective
  cycle: `DECISIONS.md`, entry D-071 (read it first; it is the owner's instruction in summary).
- One false positive drove the English G3 failure: `en-39868218` unit `un-00011`, DOI `10.1002/asi.23238`, a
  Retraction Watch record (ordinal 33558) whose OriginalPaperDOI equals its RetractionDOI. dt-1 gave
  `RETRACTED_WORK_CITED`.
- Root cause and census: `docs/verification/stage-04/corrective/ROOT_CAUSE.md`, `corrective/census/`.

## What changed (working tree on top of commit `f207bc0`; compare with `git diff f207bc0` and `git status`)

- Production: `src/citerift/investigation/dt1.py` (table dt-2: functions `attached_keys`, `notice_elsewhere`,
  `role_collided`, `role_ambiguous`; guard `_d10`; reason `IDENTIFIER_ROLE_COLLISION`),
  `adapters/detector.py` (event flags and `notice_hit_count` passed into the view), `adapters/plan.py`,
  `adapters/detect.py`, `explanations.py`, `__init__.py` (engine 0.3.0).
- Schemas: `schemas/investigation/v1/common.schema.json` (4.0.0), `claim.schema.json` (3.0.0).
- Specification: `docs/verification/stage-04/SPECIFICATION.md` section 7.3 (D-10) and new 7.3a;
  `MATHEMATICAL_MODEL.md` (D-10, `rc(c)`); `RISK_ANALYSIS.md` R4-04.
- Reference model and oracle: `simulations/stage04/dt2_reference.py`, `decision_space_dt2.py`, `oracle-dt2/`;
  summary `corrective/simulation/decision_space_dt2_summary.json`. The frozen `dt1_reference.py` and `oracle/` are
  unchanged.
- Tests: `tests/stage04/test_corrective_role_collision.py` (adversarial suite on an attributed Retraction Watch
  subset fixture, `tests/stage04/fixtures/corrective/`), `test_corrective_oracle.py`, `test_corrective_runner.py`,
  plus identity-string updates in existing test support files.
- Fail-first evidence: `corrective/evidence/`.
- Evaluation runner fix: `corrective/runner/s13_run_v2.py` (the historical `evaluation/tools/s13_run.py` is unchanged
  and must stay so).
- Regression (when present): `corrective/regression/`.
- Exposure manifest v2 builder: `docs/verification/stage-04/freeze-2/exposure/build_exposure_manifest.py`.

## Fixed constraints (from the owner; do not recommend violating them)

- The failed campaign (`docs/verification/stage-04/evaluation-campaign/`, `evaluation/`) is never altered, rescored or
  rerun; P files are untouched.
- No DOI, publisher, "Withdrawal", English or string special case; no hard-coded DOI in production code.
- Fail closed: abstain (preferably `UNRESOLVED_IDENTITY`) on an unresolved role collision; never `NOTICE_CITED` unless
  production evidence proves the notice; prefer abstention over false attachment.
- Precedence contradiction → unresolved → operational failure → positive → notice/no-finding must not weaken.
- Stage 02 is not changed in this cycle (any Stage 02 maintenance needs a separate owner decision).
- One working assumption awaits the owner: a second, clean identifier of the citation that names the same Retraction
  Watch event resolves a DOI collision (mirroring dt-1's existing treatment of the PMID collision). Review it on the
  merits.

## How to work

- Read code and evidence. You may run targeted commands (`uv run pytest tests/stage04/<one file> -q -p
  no:cacheprovider`, small Python probes). Do **not** run the whole test suite (CPU is shared), do not use the network,
  do not modify, stage, commit or delete any file except your own review file.
- The pinned Stage 02 index, if you need it, is
  `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/s14/index/rw-2f116e9ffed718e6.sqlite`
  (read-only; open it with `sqlite3` URI `mode=ro`).
- Write your review to `docs/verification/stage-04/corrective/review/REVIEW_<YOUR LETTER>.md` with: scope read,
  method, findings (each with id, severity CRITICAL / HIGH / MEDIUM / LOW / INFO, evidence with file:line or command
  output, and a concrete recommendation), and a one-line verdict. Distinguish verified fact from inference.
- CRITICAL: the correction can still produce a false positive attachment of the failure's kind, or breaks a stated
  invariant. HIGH: a material defect in correctness, evidence or claims that must be fixed before a refreeze.
