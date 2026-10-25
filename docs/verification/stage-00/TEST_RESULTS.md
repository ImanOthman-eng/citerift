# Stage 00 Test Results

Revision under test: `30e4462e9ae71016dbc6f04cdda19106babd4a34` (branch
`claude/project-thread-9lab67`, PR #1). It is the implementation revision
recorded in the registry. It adds the final-review fixes to `ecaa845` in two
commits: `2bf7d60` (regex and `ACCEPTANCE_STALE` test) and `30e4462` (tests
for every finding code; no production code change). See RISK_ANALYSIS.md
sections 2 and 4. Every result here was produced and
read on 2026-10-25. Local results come from the CITERIFT cloud container.
**No GitHub Actions job has run successfully** (section 6). CI has not been
triggered for `30e4462` yet; it is pushed together with this package.

## 1. Test suite

| Report | sha256 | Python | Collected | Passed | Failed | Dirty tree |
|---|---|---|---|---|---|---|
| `test-report.json` | `804b76c61af42a22de11e64c1f25cdc0f534ae8770b2eb2a893728604c9f768e` | 3.12.3 | 161 | 161 | 0 | no |
| `test-report-python3.13.json` | `35a438a949e998bdc17385e924bc66a94dbf4ae35c6bd9b00e539e281e8438ba` | 3.13.17 | 161 | 161 | 0 | no |

Both reports: format `citerift.test-report/1`, revision `30e4462…`,
`exit_status` 0, pytest 9.1.1. Produced with
`uv run pytest --citerift-report <file>` in a separate git worktree checked out
at that revision, one report at a time so each saw a clean tree. Earlier reports
are kept in `superseded/`: `ecaa845` (137 passed on both versions) and
`2bf7d60` (138 passed on both versions).

Per suite (a test can belong to more than one suite, so the sum exceeds 161):

| Suite | Passed |
|---|---|
| unit | 29 |
| integration | 59 |
| negative | 107 |
| regression | 12 |
| reproducibility | 3 |
| security | 8 |
| contracts | 49 |
| simulation | 6 |

## 2. The 12 mandatory integration scenarios

All in `tests/stage00/test_integration_scenarios.py`, each run against a fresh
git sandbox repository with its own registry and evidence.

| # | Scenario | Test | Result |
|---|---|---|---|
| 1 | Valid stage authorization | `test_01_valid_stage_authorization`, `test_01b_…` | pass |
| 2 | All tests passing: verified, not accepted | `test_02_stage_with_all_tests_passing_is_verified_but_not_accepted` | pass |
| 3 | Missing tests block verification | `test_03_missing_tests_block_verification` (parametrized) | pass |
| 4 | Failed or untrustworthy tests block verification | `test_04_failed_or_untrustworthy_tests_block_verification` | pass |
| 5 | Incomplete handoff blocks verification | `test_05_…`, `test_05b_trivial_artifact_and_gates_block_verification` | pass |
| 6 | Missing owner acceptance | `test_06_missing_owner_acceptance`, `test_06b_fabricated_acceptance_in_files_is_detected`, `test_06c_acceptance_of_another_revision_is_detected` | pass |
| 7 | Unauthorized next-stage request | `test_07_unauthorized_next_stage_request` | pass |
| 8 | Conflicting stage-state records | `test_08_conflicting_stage_state_records` | pass |
| 9 | Missing or stale verification evidence | `test_09_missing_or_stale_verification_evidence` | pass |
| 10 | Session restart, recovery from repository only | `test_10_…` and `test_recovery.py` (fresh clone, separate isolated process) | pass |
| 11 | Evidence-supported correction of an accepted stage | `test_11_…`, `test_11b_reopening_while_successor_active_is_refused` | pass |
| 12 | Future enhancement preserving contracts | `test_12_future_enhancement_preserving_contracts` | pass |

Additional: blocker lifecycle, open blocker and open critical defect each
prevent verification.

## 3. Hand edits of project memory

`tests/stage00/test_registry_tampering.py` starts from a sandbox in which
Stage 00 is legitimately verified, applies one hand edit, and requires the
specific error code. 19 edits: dependency cycle, unknown dependency, duplicate
stage, history sequence gap, history time reversed, invalid history edge,
unknown history stage, registry schema violation, record for a state never
reached, undefined gate, duplicate risk id, invalid risk field, blocker
resolved without resolution, unknown amendment, artifact or test report
missing from the verification record, gates or test suites removed, amendment
filed under the wrong stage. Also: a copy without git history cannot vouch
for revisions (`REVISION_UNVERIFIABLE`), and an unknown stage or a missing
implementation revision is refused.

After this file was added, every finding code emitted by
`src/citerift/governance` and `src/citerift/contracts` is asserted by name in
at least one test (checked with a grep over the source codes on 2026-10-25).

## 3b. Contracts

- `citerift-contracts check-schemas`: 2 schemas, 0 problems.
- 3 valid synthetic fixtures (`investigation_minimal`, `investigation_full`,
  `investigation_uncertain_conflicting`) validate.
- 35 invalid cases (`invalid_cases.json`), each a single mutation of a valid
  fixture, are each rejected with the expected error, including: a
  "not retracted" value, absence of a retraction record marked as fact or as
  model inference, a fact carrying model confidence, an inference without a
  model, conflicting status with fewer than two sourced alternatives, dangling
  references, out-of-order events, missing limitations.
- Malformed or unversioned schemas report `SCHEMA_INVALID` and
  `SCHEMA_UNVERSIONED`; structural violations report `SCHEMA_VIOLATION`.
- Backward-compatibility check: an additive minor version is accepted, and a
  deliberately breaking variant is reported (`test_contracts.py`).

## 4. Static checks (run 2026-10-25 on the working tree: source at `30e4462` plus
the uncommitted Stage 00 evidence and registry)

| Check | Result |
|---|---|
| `uv lock --check` | lockfile consistent with `pyproject.toml` |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 41 files (Python and Markdown) already formatted, after formatting `mutation/mutation_check.py` (section 5) |
| `mypy` (strict, `src/`) | Success: no issues found in 11 source files |
| `citerift-gov check` | 0 errors, 2 warnings (`BLOCKER_OPEN` B-00-001 and B-00-002) |
| `citerift-gov render-status --check` | PROJECT_STATUS.md is up to date |
| `pip-audit --require-hashes` on `uv export --frozen` | No known vulnerabilities found |
| zizmor 1.x `--offline .github/workflows/ci.yml` | No findings (3 online-only audits skipped: impostor-commit, ref-confusion, known-vulnerable-actions) |

## 5. Mutation testing

`mutation/mutation_check.py` disables one safety rule at a time and runs the
Stage 00 tests; a mutant is killed if the suite fails.

| Mutant | Result |
|---|---|
| M1 single-active rule disabled | killed |
| M2 owner-only edge check disabled | killed |
| M3 absence-of-record must be `uncertain` (schema) | killed |
| M4 test-report revision check disabled | killed |
| M5 drift detection disabled | killed |
| M6 history replay conflict disabled | killed |
| M7 evidence hash check disabled | killed |
| M8 dependency check disabled | killed |

| M9 acceptance-of-other-revision check disabled | killed |

9 of 9 killed at `30e4462` (`mutation/results-30e4462.txt`, sha256
`03407e76…`); also 9 of 9 at `2bf7d60` (`superseded/2bf7d60/`). M9 was added
with `test_06c`. At `ecaa845` the first 8 mutants
were also all killed, before and after the script was made lint-clean and
location-independent (`superseded/ecaa845/results-ecaa845*.txt`). Every
mutated file was restored; `git status` showed no change under `src/` or
`schemas/` afterwards.

## 6. GitHub Actions (gate 00-K): BLOCKED

| Run | Event | Commit | Conclusion | Cause (check-run annotation, read via the API) |
|---|---|---|---|---|
| [40185612324](https://github.com/ImanOthman-eng/citerift/actions/runs/40185612324) | push | `b13f910` | failure | "The job was not started because your account is locked due to a billing issue." |
| [40185625790](https://github.com/ImanOthman-eng/citerift/actions/runs/40185625790) | pull_request | `b13f910` | failure | same |
| [40186100011](https://github.com/ImanOthman-eng/citerift/actions/runs/40186100011) | push | `ecaa845` | failure | same (annotation read for job 121147086302) |
| [40186103825](https://github.com/ImanOthman-eng/citerift/actions/runs/40186103825) | pull_request | `ecaa845` | failure | same (annotation read for job 121147096876); job logs return HTTP 404 because no runner started |

Every job finished within about 2 seconds with no steps executed. These runs
say nothing about the code; they show the workflow is registered and triggers
on push and pull request. CI evidence for Stage 00 does not exist yet.

## 7. Branch protection (gate 00-L): BLOCKED

Read back on 2026-10-25 with the session's token:

- `GET /repos/ImanOthman-eng/citerift/rulesets` → HTTP 200, `[]` (no rulesets).
- `GET /repos/ImanOthman-eng/citerift/rules/branches/main` → HTTP 200, `[]`
  (no rules apply to `main`).
- `GET /repos/ImanOthman-eng/citerift/branches/main/protection` → HTTP 403.
- Creating the ruleset (`POST …/rulesets`) was refused earlier by the session's
  GitHub proxy: "Write access to this GitHub API path is not permitted through
  this proxy". The classic protection API returned 403 "Resource not
  accessible by integration".

The ruleset is defined in `.github/rulesets/main-protection.json` and its
content is checked by `test_branch_ruleset_definition`, but **`main` is not
protected**.

## 8. Governance dry run

With Stage 00 in `IMPLEMENTED_NOT_VERIFIED` at `30e4462` and both blockers open, a dry-run
transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE` is refused by the
orchestrator (output recorded in HANDOFF.md). This is the expected result: the
orchestrator will not let this stage be called verified without CI evidence.

## 9. Gaps in test coverage

- Content of evidence documents is not judged by any test (structural checks only).
- No test runs inside GitHub Actions yet (section 6).
