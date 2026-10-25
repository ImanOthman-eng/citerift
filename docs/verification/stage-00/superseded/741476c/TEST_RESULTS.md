# Stage 00 Test Results

Revision verified: `741476c7da8dde4d077e97ae0302a331ef5fdef5` (branch
`claude/project-thread-9lab67`, PR #1), the commit GitHub Actions tested
successfully (section 6). Its code is identical to the implementation revision
`30e4462` recorded in the registry; `741476c` adds only this package, evidence
and registry state, none of it under a Stage 00 owned path. `30e4462` adds the
final-review fixes to `ecaa845` in two commits: `2bf7d60` (regex and
`ACCEPTANCE_STALE` test) and `30e4462` (tests for every finding code; no
production code change). See RISK_ANALYSIS.md sections 2 and 4. Every result
here was produced and read on 2026-10-25.

## 1. Test suite

| Report | sha256 | Python | Collected | Passed | Failed | Dirty tree |
|---|---|---|---|---|---|---|
| `test-report.json` | `a371e89a02195e64babdfac0cce8946c211908f3123a0203ae728745850dea6e` | 3.12.3 | 161 | 161 | 0 | no |
| `test-report-python3.13.json` | `ac2643ba6bf4d3213a5e4f4be19cb809d7d2faa63fd462ce9e76709f6d299837` | 3.13.14 | 161 | 161 | 0 | no |

Both reports were produced **on GitHub-hosted runners** by CI run
[40188172695](https://github.com/ImanOthman-eng/citerift/actions/runs/40188172695)
(attempt 2) at revision `741476c…` and are copied unchanged from its artifacts:
`test-report-python-3.12` (artifact 12599957779, zip sha256 `67a60bfa…`) and
`test-report-python-3.13` (artifact 12599728087, zip sha256 `e9d23872…`).
Each zip's sha256 equals the digest the upload step printed in the job log.
Format `citerift.test-report/1`, `exit_status` 0, pytest 9.1.1, platform
`Linux-6.17.0-1022-azure-x86_64`.

Earlier local reports, produced in a separate clean git worktree in the
CITERIFT container, are kept in `superseded/`: `ecaa845` (137 passed on both
versions), `2bf7d60` (138) and `30e4462` (161 on Python 3.12.3 and 3.13.17,
the same code as `741476c`).

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
| `citerift-gov check` | 0 errors, 2 warnings (`BLOCKER_OPEN` B-00-001 and B-00-002, both open at the time; both resolved since) |
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

## 6. GitHub Actions (gate 00-K): PASSED

After the owner updated GitHub billing, the two latest runs on PR #1 were
re-run on 2026-10-25 at 13:19 UTC. Both ran on GitHub-hosted runners and
succeeded:

| Run (attempt 2) | Event | Commit | Jobs | Conclusion |
|---|---|---|---|---|
| [40188172695](https://github.com/ImanOthman-eng/citerift/actions/runs/40188172695) | push | `741476c` | verify (python 3.12) 121180206311, verify (python 3.13) 121180206446, ci-gate 121180395707 | success |
| [40188175045](https://github.com/ImanOthman-eng/citerift/actions/runs/40188175045) | pull_request | `741476c` | verify (python 3.13) 121180211905, verify (python 3.12) 121180212159, ci-gate 121180397278 | success |

Every step of every verify job succeeded: checkout with full history, uv
install, lockfile check, locked install, ruff lint and format, mypy strict,
schema validation, governance check, tests, dependency audit, report upload.
Read from the job logs: `Consistency check: 0 errors, 2 warnings` (the two
then-open blockers); `161 passed` (32.51 s on 3.12, 28.96 s on 3.13 in the
push run); pip-audit `No known vulnerabilities found`. All six check runs
belong to the GitHub Actions app (id 15368), the integration the ruleset
requires for `ci-gate`.

Earlier runs, kept for the record: attempt 1 of runs 40185612324,
40185625790, 40186100011, 40186103825, 40188172695 and 40188175045 (commits
`b13f910`, `ecaa845`, `741476c`) all failed in about 2 seconds with zero
steps, with the check-run annotation "The job was not started because your
account is locked due to a billing issue." They said nothing about the code.
Blocker B-00-001 is resolved.

## 7. Branch protection (gate 00-L): PASSED

History: this session cannot create rulesets. `POST …/rulesets` was refused by
the session's GitHub proxy ("Write access to this GitHub API path is not
permitted through this proxy"), also when retried after CI passed (about 13:22
UTC), and the classic protection API returned 403 "Resource not accessible by
integration". Read backs until 13:29 UTC returned `[]`. Blocker B-00-002.

The owner then created the ruleset on GitHub (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPBsct46wZA6iBixZ1ZLXboz`). Read back directly
from the GitHub API on 2026-10-25 with the session's token:

- `GET /repos/ImanOthman-eng/citerift/rulesets` → HTTP 200: one ruleset,
  id `25824038`, name `main-protection`, target `branch`, source
  `ImanOthman-eng/citerift`, enforcement `active`, created
  `2026-10-25T18:30:30.932+04:00` (14:30:30 UTC).
- `GET /repos/ImanOthman-eng/citerift/rulesets/25824038` → HTTP 200.
  Compared field by field with `.github/rulesets/main-protection.json`:
  name, target, enforcement, conditions (`include: ["~DEFAULT_BRANCH"]`,
  `exclude: []`), `bypass_actors: []` and the four rule types all match, and
  every parameter in the file has the same value on GitHub.
  `current_user_can_bypass` is `never` for this session's token, which acts as
  the owner's account.
- `GET /repos/ImanOthman-eng/citerift/rules/branches/main` → HTTP 200: the
  rules in effect on `main` are exactly those of ruleset 25824038:
  `deletion`; `non_fast_forward`; `pull_request` with 0 required approvals and
  `allowed_merge_methods: ["merge"]`; `required_status_checks` with
  `ci-gate`, integration id 15368, `strict_required_status_checks_policy:
  true`, `do_not_enforce_on_create: false`.
- `GET /repos/ImanOthman-eng/citerift/branches/main` → `protected: true`;
  default branch is `main` (`GET /repos/ImanOthman-eng/citerift`).
- PR #1 reports `mergeable_state: clean` at head `0cda54e`, where both
  `ci-gate` check runs (runs 40197530986 and 40197535146) succeeded and
  belong to the GitHub Actions app, id 15368, the integration the rule requires.

Two parameters appear on GitHub that the file does not contain:
`required_reviewers: []` (empty, no effect) and
`require_extra_approval_for_unattributed_changes: true`. Both were added by
GitHub when the ruleset was created; neither removes a rule from the file, so
the protection is at least as strict as defined. The effect of the second one
on merging PR #1 has not been observed yet.

Not done: a test push straight to `main` to watch it be refused. If protection
were not in force, that push would change `main`, so the gate rests on the
read backs above, which report the rules GitHub enforces on `main`.

## 8. Governance dry run

The orchestrator refuses the transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE`
while any gate is unpassed or any blocker is open. Before the ruleset existed
the dry run at `741476c` raised only `BLOCKER_OPEN` B-00-002 and
`GATE_NOT_PASSED` 00-L; after B-00-002 was resolved and 00-L recorded as
passed, the dry run raised nothing (output in HANDOFF.md).

## 9. Gaps in test coverage

- Content of evidence documents is not judged by any test (structural checks only).
