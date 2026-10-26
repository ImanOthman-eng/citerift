# Stage 00 Risk Analysis and Adversarial Review

The live register is `RISKS.md` (R-001 to R-015). This document analyzes the
risks that bear on Stage 00 and records the adversarial review of the
orchestrator, memory and CI. Likelihoods are qualitative judgments.

## 1. Threat model

The asset being protected is the integrity of the stage record: that a stage
is shown as verified only with real evidence, accepted only by the owner, and
that no later stage starts without the owner's authorization.

Adversaries considered:

- **A careless or over-eager agent** (the most likely case): skips a step,
  reuses stale evidence, or treats its own report as approval.
- **A dishonest writer with repository write access**: edits the registry or
  evidence by hand.
- **External input**: pull request content, workflow triggers, dependencies.

Fact that shapes everything below (verified 2026-10-25, `get_me`): the agent's
GitHub actions run as the owner's account `ImanOthman-eng`. GitHub cannot tell
the two apart (R-001), so owner decisions are attested by reference to the
owner's own words (D-005), not by GitHub identity.

## 2. Adversarial review

Each attack was attempted against the implementation in a sandbox repository.
"Test" names a test in `tests/stage00/` that performs the attack and passes
only if it is refused or detected.

| # | Attack | Outcome | Test |
|---|---|---|---|
| 1 | Agent records acceptance as `engineering-agent` | refused: `OWNER_DECISION_REQUIRED` | `test_06_missing_owner_acceptance` |
| 2 | Owner transition with no `owner_ref` | refused: `OWNER_REF_REQUIRED` | `test_01b_authorization_requires_owner_and_reference` |
| 3 | Write `ACCEPTED_CLOSED` into the registry by hand | detected: `STATUS_HISTORY_CONFLICT`, `RECORD_MISSING` | `test_06b_fabricated_acceptance_in_files_is_detected` |
| 4 | Add a fake acceptance history entry without a matching verification | detected: `ACCEPTANCE_UNTRACEABLE` | `test_06b_…` |
| 4b | Record an acceptance for a revision other than the verified one, or dated before the verification | detected: `ACCEPTANCE_STALE` | `test_06c_acceptance_of_another_revision_is_detected` |
| 5 | Verify with no test report, a dirty-tree report, a report for another revision, or a failing report | refused: `TEST_EVIDENCE_*`, `TESTS_FAILED` | `test_03_…`, `test_04_…` |
| 6 | Verify with an empty or 10-byte artifact, or with gates missing | refused: `EVIDENCE_TRIVIAL`, `GATE_*` | `test_05b_trivial_artifact_and_gates_block_verification` |
| 7 | Handoff missing sections or citing the wrong commit | refused: `HANDOFF_INCOMPLETE`, `HANDOFF_WRONG_REVISION` | `test_05_…` |
| 8 | Edit an evidence file after verification | detected: `EVIDENCE_STALE` | `test_09_missing_or_stale_verification_evidence` |
| 9 | Commit to a stage-owned path after verification without an amendment | detected: `VERIFICATION_STALE` | `test_09_…` |
| 10 | Authorize Stage 02 while a dependency is only verified, not accepted | refused: `DEPENDENCY_NOT_ACCEPTED` | `test_07_unauthorized_next_stage_request` |
| 11 | Rework a verified stage while another engineering stage is active | refused: `MULTIPLE_ACTIVE_STAGES` (the defect the simulation found) | `test_07_…`, `test_08_…`, differential test in `test_simulation.py` |
| 12 | Reopen an accepted stage while its successor is active | refused | `test_11b_reopening_while_successor_active_is_refused` |
| 13 | Evidence path `../../etc/passwd` or an absolute path | refused: `EVIDENCE_OUTSIDE_REPOSITORY` | `test_evidence_paths_outside_repository_rejected` |
| 14 | Cite a commit that does not exist, or is not in `HEAD`'s history (for example after a squash merge) | detected: `REVISION_NOT_FOUND` / `REVISION_NOT_IN_HISTORY` | `test_09_…` |
| 15 | Verify a stage with an open blocker or an open critical defect | refused: `BLOCKER_OPEN`, `OPEN_CRITICAL_DEFECT` | `test_open_blocker_prevents_verification`, `test_open_critical_defect_prevents_verification` |
| 16 | Two accepted decisions on one topic in `DECISIONS.md` | detected: `DECISION_CONTRADICTION` | `test_unit_model_evidence_memory.py` |
| 16b | Any of 19 single hand edits to the registry or `RISKS.md` (dependency cycle, history reordering, records for unreached states, and others) | each detected by its specific code | `test_registry_tampering.py` |
| 17 | Stale `PROJECT_STATUS.md` | detected: `STATUS_DOC_OUT_OF_DATE`; CI step `render-status --check` | `test_08_…`, `test_cli.py` |
| 18 | Shell injection through stage ids or paths | not possible: governance code calls git with argument lists, never a shell | `test_governance_code_runs_no_shell` |
| 19 | Secret committed to the repository | detected by the repository secret scan; the scanner is itself tested on a planted token | `test_no_secrets_in_repository_files`, `test_secret_scanner_detects_a_planted_token` |
| 20 | Workflow script injection through event fields | no `${{ github.event.* }}` in `run:` steps; zizmor (offline) reports no findings | `test_repository.py` workflow hardening test |

Mutation testing confirms these tests have teeth: 9 mutants that each disable
one rule (single-active, owner-only edge, absence-must-be-uncertain, report
revision, drift, history replay, evidence hash, dependency, accepted revision)
were all killed (TEST_RESULTS.md).

### Findings fixed during the review

- Simulation iteration 1: VA→IP bypassed the single-active rule (D-016).
- Resolving the last blocker of a `BLOCKED` stage left it blocked without a
  blocker (`BLOCKED_WITHOUT_BLOCKER`); resolution now records BLOCKED→IN_PROGRESS
  in the same write.
- zizmor flagged `${{ matrix.python }}` expanded inside a `run:` step; the
  workflow now passes it through the `UV_PYTHON` environment variable.
- Final review (section 4): `registry_version` used `\d`, which Python's `re`
  matches against any Unicode digit and JavaScript validators against ASCII
  digits only, so the Stage 07 backend and Stage 08 frontend could disagree
  on the same input. Replaced by `[0-9]` in `2bf7d60`.
- Final review: `ACCEPTANCE_STALE` was implemented but no test exercised it.
  `test_06c` added in `2bf7d60`; mutant M9 confirms the test fails without the
  check.
- Final review: 25 more finding codes were not asserted by any test. Added
  `test_registry_tampering.py` (19 hand edits plus 2 refusal tests) and 2
  contract tests in `30e4462`; every code is now asserted by name.

### Residual weaknesses (not fixed in Stage 00, stated plainly)

- **Structural, not semantic, evidence checks.** The 300-byte minimum, the
  handoff section headings and gate evidence paths are checked for presence;
  their content is not judged. Padding defeats the size check. The owner's
  review of the handoff is the control.
- **Owner references are not read** (R-002) and **a fully consistent forgery is
  detectable only by review** (R-003). Optional signed acceptance (D-006) would
  close the first for acceptance.
- **CI records are entered by the agent** (R-004). The run URL is public and
  the required `ci-gate` check is the independent control (active since
  2026-10-25).
- **Shared infrastructure is not drift-tracked** (D-012). A change to
  `pyproject.toml` or the workflow does not make Stage 00 stale; CI re-running
  every stage's tests on every change is the control.
- **Branch protection depends on the owner's account settings.** It became
  active on 2026-10-25 (R-015 closed, B-00-002 resolved). The owner, as
  repository admin, can still edit or disable it; the read back in
  TEST_RESULTS.md section 7 shows its state on that date only.

## 3. Stage 00 risk register summary

| Risk | Severity | Status | Effect on Stage 00 |
|---|---|---|---|
| R-001 agent acts as owner's GitHub account | high | open | owner decisions attested by reference (D-005) |
| R-002 owner refs not machine-verified | high | open | owner checks `owner_ref`s |
| R-003 registry can be hand-edited | medium | open | detection only |
| R-004 CI evidence entered by agent | medium | open | public run URL, required check |
| R-005, R-006 contract checks fixture-based, formats permissive | medium | open | tighten in Stages 02 and 03 |
| R-009 no license | high | open | owner decision D-007; blocks Stage 09, not Stage 00 |
| R-010 hackathon deadline | high | open | owner acceptance turnaround is on the critical path |
| R-011 ephemeral container | medium | mitigated | everything pushed; recovery tested |
| R-012 clock-dependent ordering | low | accepted | fail-closed |
| R-014 Actions jobs not started (billing lock) | high | closed | resolved by the owner; CI passed at `741476c` (B-00-001 resolved) |
| R-015 protection defined but inactive | high | closed | owner created ruleset 25824038; read back active (B-00-002 resolved) |

No open critical defect is recorded; `citerift-gov check` reports
`OPEN_CRITICAL_DEFECT` for none.

## 4. Final connected-system review

Prompt 02 section 21 asks for a review from nine perspectives. It was done by
the same agent that built the stage, so it is a structured self-review, not
independent proof. Each line names what was checked in the actual artifacts.

| Perspective | Checked | Finding |
|---|---|---|
| Chief Architect | Orchestrator and memory are one library plus files; no daemon, service or agent framework (D-004). Investigation Workflow Controller and Investigation Memory (Stages 04, 07) are not built and nothing in Stage 00 presumes their design. | no defect |
| Senior Engineer | `ruff`, `mypy --strict` clean; no shell in governance code; atomic registry writes. | no defect |
| Mathematical Reviewer | Attempt count 490 × 3,584 = 1,756,160 matches the output; completeness argument for the single-active rule (MATHEMATICAL_MODEL.md section 3); simulation output reproduced byte-for-byte as JSON on re-run. | no defect |
| QA Engineer | Listed every finding code in the governance and contract code and searched the tests for each. | 26 codes were never asserted by name: `ACCEPTANCE_STALE` and 25 others (including the section 7.4 rules on invalid dependencies and history order): **fixed** in `2bf7d60` and `30e4462` |
| Security Reviewer | Workflow permissions `contents: read`, SHA-pinned actions, `persist-credentials: false`, zizmor offline clean, pip-audit clean, secret scan. | protection of `main` was inactive (blocker B-00-002); **resolved** when the owner created ruleset 25824038, read back active |
| Stage 02 developer | DOI/PMID patterns are permissive by design (R-006); `retraction_status` has no "not retracted" value; absence must be `uncertain` with checked sources. Stage 02 can add new schema files under `v1/` as a minor version. | no defect; tighten formats with real data |
| Stage 06 AI engineer | `ai_assessment` requires a model reference and confidence in [0, 1], allows abstention, and can never carry `verified_fact`. Confidence is documented as uncalibrated until Stage 06 calibrates it. | no defect |
| Stage 07 backend engineer | Schemas resolve by URN through `load_contracts`, so a FastAPI service can reuse the validator without network access. | no defect |
| Stage 08 frontend engineer | All schema `pattern`s were listed and checked for regex features that behave differently in JavaScript. | `\d` in `registry_version`: **fixed** (`\S` behaves the same for the ASCII and common Unicode whitespace that matters here) |
