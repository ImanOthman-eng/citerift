# Stage 03 completion checklist — ChatGPT/Codex, 2026-10-30

- [x] Recover remote PR #5, refs, clean local tree and processes; no final campaign output recovered.
- [x] Locked Python 3.12 environment; governance recover/check: 0 errors, 0 warnings.
- [x] Retain current owner directive; preserve prior directives and D-031.
- [x] Reproduce all five original V1/V2 modified-document failures before production edits.
- [x] Complete focused repair, bilingual regressions and read-only integration review.
- [ ] Freeze candidate/protocol; validate exposure and run one final campaign with separate evaluators.
- [ ] Commit annotation lock/reserve decisions before predictions; score/adjudicate without tuning.
- [ ] Complete regression, static/audit/schema/protected-path checks and clean reports on both Pythons.
- [x] Current CLI/real-bundle/replay/resource/wheel/relocation evidence.
- [ ] Durable export, download verification, final docs, green CI and updated unmerged PR #5.
- [ ] Advance to verified only if every scientific and delivery condition passes; owner alone accepts/merges.

## Evidence index

- Authority: `authorization/OWNER_DIRECTIVE_2026-10-30_HANDOFF.md` (retained-document delivery reference).
- Pre-fix production: `d1b64499ab7b53d5e486f3cc6db6d86f51bf3399`.
- V1/RF-56 and V2/RF-57 originals: `review/failfirst/v1-v2/RESULTS.json`, unchanged synthetic bundles and full
  genuine/modified documents, verifier outputs and replay comparisons in that directory.
- Runnable variants: `tests/stage03/test_wiki_v1_v2.py`; copy that test into a detached pre-fix checkout to rerun.
- Historical results quoted in the owner's review remain historical, not executions by this executor.

## 31 October checkpoint

GitHub access enabled by the owner; ec9453a pushed to the existing Stage 03 branch and PR #5 updated.
Clean complete repository reports at cd085dd: 1663 passed on Python 3.12.14 and1663 on3.13.5.
Both reports pass the governance report checker. CI for the pushed checkpoint is running.
Fresh initial20 and two ordered reserve pairs per language are captured; labels through14 per
language are committed before predictions. Counts require the last pair and the amendment
permits a bounded Arabic sixteenth draw. No fresh predictions yet; no acceptance or later stage.

## 2 November completion (Claude Code, owner instruction D-033)

- [x] Recovery: the remote head was `d151507`. No newer or local-only work and no running jobs were found.
  `src` and `schemas` at `d151507` equal the frozen candidate `48cfeab`.
- [x] Independent adjudication of all 37 disputed items: 34 confirmed, 3 corrected. The adjudicated scores were made
  with the unchanged scorer, and the locked scores reproduce exactly (`evaluation/final/adjudication/`).
- [x] Gates under adjudicated labels:
  - Arabic G5a fails at 0.914.
  - The Arabic identifier denominator is 33, against a minimum of 50.
  - English G2 fails at 0.0192.
  - All other gates pass.
- [x] G8 and G10 at `48cfeab`: 32 / 32 verify and replay.
- [x] RF-60, post-exposure: fail-first, fix, independent integration review R5 and its fixes. The 70 retained real
  bundles change in one document only. Post-exposure re-extraction is labelled as non-gate evidence.
- [x] Documents updated:
  - risk, mathematical model and simulation addenda;
  - differentiation review 7.1 and 7.2;
  - specification 11.4;
  - RISKS.md R-034 and R-035;
  - the decision record.
- [x] TEST_RESULTS.md and HANDOFF.md, with the complete verification matrix at the final code commit (`8c6fe9f`): 1690 passed on Python 3.12 and 3.13; static checks, audit, wheel smoke and CI green.
- [ ] Owner decision on the unmet gate 03-G (`evaluation/final/DECISION_RECORD.md`). No verification transition is
  recorded while 03-G is unmet. Acceptance and merge are the owner's.

## 2 to 3 November: corrective engineering and confirmation campaign (Claude Code, owner instruction D-034)

- [x] Short-footnote semantics decided and implemented (`design/sfn-semantics/`); DOI audit with D-1 and D-2 fixed;
  Retry-After audit with G-1 and G-2 fixed and a resumable campaign driver.
- [x] One adversarial review (R6) and one focused review (R7); every confirmed finding fixed before the freeze.
- [x] Prospective protocol (amendment, guide 1.1, briefs) committed; candidate `3e51792` frozen; exposure set
  committed before the draw.
- [x] One campaign: draw, capture, AI evaluator labels locked before predictions, reserve decisions from locked
  counts, one prediction run, locked scores, adjudication, adjudicated scores, intervals, warning challenge
  (`evaluation/confirmation-2026-11/campaign/REPORT.md`). 263 attempts, 12.6 MB.
- [x] Evidence-integrity audit: 27 / 27 checks pass (`campaign/audit/EVIDENCE_AUDIT.json`).
- [x] Documents updated, decision record written, RISKS.md R-036 added.
- [x] Complete verification matrix at the final head (TEST_RESULTS.md section 7).
- [ ] English G5c is 0.869 against 0.95, so no verification transition is recorded. The owner decides
  (`evaluation/confirmation-2026-11/DECISION_RECORD.md`). Acceptance and merge are the owner's.

## 3 November: G5c semantic correction and one further confirmation (Claude Code, owner instruction D-035)

- [x] Fail-first reproduction of the 19 English false positives (`design/unit-semantics/FAIL_FIRST_BEFORE.txt`);
  citation-unit classes A-H, `unstructured_text` only on positive evidence (`design/unit-semantics/SEMANTIC_DECISION.md`).
- [x] Differential checks on the 146 retained bundles; one independent adversarial review and a second independent
  review, every confirmed finding fixed before the freeze (`design/unit-semantics/review/`, `review2/`).
- [x] Prospective amendment and copied scripts (`1483024`); candidate `fff0e5b` frozen (`b1e069e`); exposure set
  committed before the draw (`fdc8b66`).
- [x] One bilingual campaign: draw, capture, AI evaluator labels locked before predictions, two reserve blocks for
  English from locked counts, one prediction run, locked scores, adjudication (45 confirmed, 1 corrected), adjudicated
  scores, intervals (`evaluation/confirmation-d035/campaign/REPORT.md`). 280 attempts, 9.2 MB.
- [x] Evidence-integrity audit: 28 / 28 checks pass (`evaluation/confirmation-d035/campaign/audit/EVIDENCE_AUDIT.json`).
- [x] English G5c 0.994 and G5d 0.994; Arabic 1.000 and 0.992.
- [ ] **Arabic G6b fails** (2 false attachments against a limit of 1), caused by a verified engine defect (RISKS.md
  R-038). No repair is allowed after the run, so no verification transition is recorded. The owner decides
  (`evaluation/confirmation-d035/DECISION_RECORD.md`). Acceptance and merge are the owner's.
- [x] Documents, decision record, RISKS.md R-038 and the R-036 update.
- [x] Complete verification matrix at `6c499a7` (TEST_RESULTS.md section 8).
