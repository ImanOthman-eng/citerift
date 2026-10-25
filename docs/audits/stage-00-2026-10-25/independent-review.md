# Independent review: CITERIFT Stage 00 Engineering Foundation

Reviewed: `/home/user/citerift` at HEAD `c8618a3` (main merge of PR #1). Nothing in
`/home/user/citerift` was changed. All experiments ran in clones under the scratchpad:

- `S=/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad`
- `C=$S/audit-clone` (clean clone, `uv sync --locked`), `GOV=$C/.venv/bin/citerift-gov`, `PY=$C/.venv/bin/python`
- each mutation ran in its own clone `$S/exp/<name>` (`git clone -q $C $S/exp/<name>`), checked with `$GOV --root <clone> check`
- helper scripts: `$S/audit-scripts/mutate.py`, `$S/audit-scripts/policy_edit.py`, `$S/audit-scripts/contracts_probe.py`,
  `$S/audit-scripts/reopen_liveness.py`, `$S/audit-scripts/single_active_flip.py`

No network was used except by `uv sync`. GitHub-side state (ruleset, CI runs) was not exercised.

Scope note: while this review ran, the branch checked out in `/home/user/citerift` gained a commit I did not make,
`99319aa` ("Add owner identity, ownership record and AI-assistance attribution rule"). It touches `.claude/settings.json`,
`.github/CODEOWNERS`, CHANGELOG.md, CLAUDE.md, DECISIONS.md, GOVERNANCE.md, OWNERSHIP.md, README.md, docs/identity.md and
pyproject.toml, and no Stage 00 owned path. It is outside this review, which covers `c8618a3` as requested. Its CODEOWNERS
file may bear on F-20 but was not assessed.

## 1. Tool results (actual output, clean clone at c8618a3)

| Command | Output |
|---|---|
| `uv run pytest -q` | `161 passed in 35.14s` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `41 files already formatted` |
| `uv run mypy` | `Success: no issues found in 11 source files` |
| `uv run citerift-gov check` | `Consistency check: 0 errors, 0 warnings` (exit 0) |
| `uv run citerift-contracts check-schemas` | `2 schemas checked, 0 problems` |
| `uv run citerift-gov render-status --check` | `PROJECT_STATUS.md is up to date` |
| `uv lock --check` | `Resolved 45 packages` (ok) |
| mutation script re-run (`docs/verification/stage-00/mutation/mutation_check.py`, in `$S/exp/mutation`) | 9/9 KILLED, same as the recorded results |

All tool claims of the builder reproduce. The findings below are defects the tests do not cover.

## 2. Summary of findings

| # | Finding | Classification | Severity |
|---|---|---|---|
| F-01 | Drift detection bypassed by a merge commit that reverts owned paths | Confirmed engineering defect | Medium |
| F-02 | Gate evidence files are not hash-pinned; changing/committing them is not detected; `.` counts as evidence | Confirmed engineering defect | Medium |
| F-03 | Rules live in the registry they check: policy flag, `ci_required`, gates, suites, owned paths, handoff sections can be weakened by hand edit with 0 errors | Verified security weakness | Medium-High |
| F-04 | History replay checks edges/actors only; history recording a past violation of invariants 3 and 4 passes | Confirmed engineering defect | Medium |
| F-05 | Rules enforced only in `propose`, not in `check`: reopen without correction amendment; IN_PROGRESS with open blocker | Confirmed engineering defect | Medium |
| F-06 | RISKS.md/DECISIONS.md parser silently ignores malformed entries (fail-open for invariant 7) | Confirmed engineering defect | Medium |
| F-07 | Any passing subset of tests satisfies the test-report check (8 of 161 tests accepted) | Verified security weakness | Medium |
| F-08 | Contract loophole: `conflicting` alternatives are untyped (`"not_retracted"`, `false` accepted); model output storable in `retraction_status` as `uncertain` | Confirmed engineering defect | Medium-High |
| F-09 | `EVENT_ORDER` compares timestamp strings; fractional seconds give false positives and false negatives | Confirmed engineering defect | Low-Medium |
| F-10 | Python and JavaScript validators disagree on schema patterns (`$` before trailing newline, `\S`); impossible dates accepted | Confirmed engineering defect | Low-Medium |
| F-11 | A foundation stage can never be reopened for correction once a dependent is accepted; the simulation model allows it (model and implementation disagree) | Confirmed engineering defect | Medium |
| F-12 | CRLF checkout (`core.autocrlf=true`) gives 8 false `EVIDENCE_STALE` errors | Confirmed engineering defect | Low-Medium |
| F-13 | Malformed registry JSON crashes `check` and `recover` with a traceback | Confirmed engineering defect | Low |
| F-14 | pytest plugin INTERNALERROR when `--citerift-report` is outside the repository | Confirmed engineering defect | Low |
| F-15 | `blocker resolve` records the stage executor as `actor` and `recorded_by`, whoever ran it | Confirmed engineering defect | Low |
| F-16 | No upper bound on timestamps: a fast clock blocks all correct-clock transitions; R-012 says only "fail-closed" | Confirmed engineering defect | Low |
| F-17 | Owner refs can be reused across decisions; record timestamps not cross-checked with history | Verified security weakness | Low |
| F-18 | JSON duplicate keys accepted (last wins); a reviewer can be shown a different value | Verified security weakness | Low |
| F-19 | `check` ignores uncommitted changes to owned paths | Documented design limitation | Low |
| F-20 | `ci-gate` is defined by a workflow the gated PR can edit; 0 approvals + shared identity | Verified security weakness (inspection; GitHub not exercised) | Medium |
| F-21 | Risk and review documents overstate what is enforced (R-001, R-003, GOVERNANCE.md, RISK_ANALYSIS, CREATIVE review) | Unfulfilled Stage 00 requirement (00-M, 00-N accuracy) | Medium |
| F-22 | Stage 02 can consume v1 contracts freely, but extending `schemas/contracts/v1` requires a Stage 00 amendment | Future-stage dependency | Low |
| F-23 | mypy covers `src/` only; package has no `py.typed` | Optional enhancement | Low |

## 3. Findings in detail

### F-01 Drift detection bypassed by a merge commit (Confirmed engineering defect, Medium)

- Code: `src/citerift/governance/orchestrator.py:566-593` (`_drift_findings`), `src/citerift/governance/gitutil.py:62-69` (`git log -1 --format=%H HEAD -- <paths>`).
- Reproduction (`$S/exp/evilmerge2`):
  ```
  OWNED="src/citerift/__init__.py src/citerift/governance src/citerift/contracts schemas/governance schemas/contracts/v1 simulations/stage00 tests/stage00"
  git checkout -b old 2bf7d60; echo "side note" > side-note.txt; git add side-note.txt; git commit -m "unrelated side commit"
  git checkout -b evil c8618a3; git merge --no-ff --no-commit old
  git rm -rq $OWNED; git checkout old -- $OWNED; git commit -m "Merge branch old"
  $GOV --root $S/exp/evilmerge2 check
  ```
- Observed: owned content differs from the verified revision (`git diff --stat 741476c HEAD -- $OWNED` -> `tests/stage00/test_registry_tampering.py | 181 ----`, `test_contracts.py | 16 ---`), `git log -1 -- $OWNED` returns `2bf7d60` (an ancestor of 741476c), and `check` prints `Consistency check: 0 errors, 0 warnings`. The 19 tamper tests were deleted without making Stage 00 stale. Control: the same revert as an ordinary commit is detected (`VERIFICATION_STALE`).
- Root cause: staleness is decided by "which commit last touched the paths" through git history simplification. A merge that is TREESAME to an old parent is skipped, so its content change is never attributed to it. The ruleset requires merge commits on `main`, so merges are the normal path.
- Smallest correction: compare content, not history: stale unless `git diff --quiet <covering-revision> HEAD -- <owned paths>` succeeds for the verified revision or a covering enhancement amendment. Add a regression test with this merge.

### F-02 Gate evidence is not hash-pinned (Confirmed engineering defect, Medium)

- Code: `orchestrator.py:556-560` checks gate evidence only for existence (`exists()`, which is true for directories and for `.`). Only the 7 required artifacts and `test-report.json` are hashed (`orchestrator.py:823-831`).
- Reproduction (`$S/exp/gateev`): edit and commit `docs/verification/stage-00/mutation/results-30e4462.txt` (`M1 survived`), set `test-report-python3.13.json` totals to `{"passed":1,"failed":160}` with `exit_status 1`, overwrite `simulation/final-results.json` with `{}`; then `check`.
- Observed: `Consistency check: 0 errors, 0 warnings`. These files are cited by gates 00-B, 00-F, 00-H, 00-K. Also `$PY $S/audit-scripts/policy_edit.py <clone> gate_dot` (every gate's evidence set to `["."]`) gives `0 errors`.
- Root cause: GOVERNANCE.md invariant 6 says "changing an evidence file makes the stage stale", but gate evidence has no recorded hash, and `docs/verification/stage-00/` is not an owned path.
- Smallest correction: record a sha256 for every gate evidence path at verification (as for artifacts) and compare in `_gate_findings`; require `is_file()`, not `exists()`.

### F-03 The registry holds the rules it is checked against (Verified security weakness, Medium-High)

- Code: `orchestrator.py:347` (`if not policy["single_active_engineering_stage"]: return []`), `orchestrator.py:128-129` (`ci_required`), `schemas/governance/stage_registry.schema.json:41,114` (plain booleans); gate list, `required_test_suites`, `owned_paths`, `handoff_required_sections` are free data.
- Reproductions (each in a fresh clone, then `render-status --write` and `check`):
  - `policy_edit.py <clone> drop_ci` (stage 00 `ci_required: false`, CI record removed): `0 errors`.
  - `policy_edit.py <clone> shrink_gates` (1 gate, suites `["unit"]`, no handoff sections): `0 errors`.
  - `policy_edit.py <clone> drop_owned_paths`, then commit a change to `orchestrator.py`: `0 errors`.
  - `$PY $S/audit-scripts/single_active_flip.py $C $S/exp` (sandbox): `authorize 03 while 02 AUTHORIZED, policy true -> False ['MULTIPLE_ACTIVE_STAGES']`, then after flipping the flag: `authorize 03 -> True`, `check errors: []`, `active: [('02','AUTHORIZED'), ('03','AUTHORIZED')]`.
- Root cause: definitions and policy are not separated from state, and not pinned. One edit to one JSON file switches off invariants 1 and 4 and drift detection, with no finding.
- Smallest correction: move the policy into the owned schema as `const` values (for example `"single_active_engineering_stage": {"const": true}`), or record a hash of each stage's definition (everything except status/records/history) in its verification record and report a change as `DEFINITION_CHANGED`.

### F-04 History replay does not check invariants per step (Confirmed engineering defect, Medium)

- Code: `orchestrator.py:270-344` replays edges and actors only; invariants 3 and 4 are checked on the final state only (`orchestrator.py:346-354`, `394-409`).
- Reproduction: `$PY $S/audit-scripts/mutate.py <clone> past_violation` inserts, between seq 3 and 4, `02 NOT_STARTED -> AUTHORIZED` (owner) and `02 AUTHORIZED -> NOT_STARTED`, while Stage 00 was IN_PROGRESS and Stage 01 not accepted.
- Observed: `Consistency check: 0 errors, 0 warnings`.
- Root cause: the replay never evaluates "dependencies accepted when authorized" or "single active stage" at each prefix, so the history can record violations of invariants 3 and 4.
- Smallest correction: during replay keep the replayed status vector and, on every entry, apply the single-active rule (for edges entering ACTIVE) and the dependency rule (for edges leaving NOT_STARTED, and for verify/accept).

### F-05 Rules enforced by `propose` only (Confirmed engineering defect, Medium)

- Code: `AMENDMENT_REQUIRED` exists only in `_edge_problems` (`orchestrator.py:812-817`); the open-blocker refusal only in `propose` (`orchestrator.py:779-780`); `check` reports an open blocker on an IN_PROGRESS stage as a warning (`orchestrator.py:377`).
- Reproductions:
  - `mutate.py <clone> reopen_without_amendment` (history `00 ACCEPTED_CLOSED -> IN_PROGRESS` by owner, no `amendment`, records cleared): `Consistency check: 0 errors, 0 warnings`.
  - `mutate.py <clone> inprogress_with_open_blocker`: `0 errors, 1 warnings  WARNING BLOCKER_OPEN`.
- Root cause: contradicts SPECIFICATION.md:39-40 ("a hand edit and a CLI transition are held to the same rules") and the orchestrator docstring (lines 6-9).
- Smallest correction: in `_history_findings`, require every `ACCEPTED_CLOSED -> IN_PROGRESS` entry to cite an existing `correction` amendment of that stage; make an open blocker at `AUTHORIZED -> IN_PROGRESS` / `BLOCKED -> IN_PROGRESS` a replay error.

### F-06 Memory parser fails open on malformed entries (Confirmed engineering defect, Medium)

- Code: `src/citerift/governance/memory.py:19` (heading needs exactly `## R-NNN — `, em dash), `memory.py:58` (any other `## ` line ends the entry silently), `memory.py:151-159` (critical defects with `Stage: project` block no stage), `memory.py:63-65` (duplicate field: last wins), `memory.py:91` (topic compared case-sensitively).
- Reproduction: append an open critical defect for stage 00 to RISKS.md in a fresh clone, then `check`:

  | Variant | Result |
  |---|---|
  | `## R-016 — ...` (em dash) | `ERROR OPEN_CRITICAL_DEFECT` (exit 1) |
  | `## R-016 - ...` (ASCII hyphen) | `0 errors` |
  | `## R-016 – ...` (en dash) | `0 errors` |
  | `### R-016 — ...` | `0 errors` |
  | `Stage: project` | `0 errors` |
  | extra `- Status: closed` after `- Status: open` | `0 errors` |
  | DECISIONS.md second accepted decision, `Topic: Python-version` | `0 errors` (exact `python-version` gives `DECISION_CONTRADICTION`) |
  | DECISIONS.md `## D-017 - ...` | `0 errors` |
- Root cause: entries that do not match the strict pattern are dropped, not reported. A critical defect typed with an ordinary hyphen does not block verification (invariant 7).
- Smallest correction: treat any line matching `^#+\s*[DR]-\d+` that fails the strict heading regex as `MEMORY_MALFORMED` (error); reject duplicate fields; normalize topics (strip, lowercase); decide and document whether `project` critical defects block every stage.

### F-07 Partial test runs satisfy the test-report check (Verified security weakness, Medium)

- Code: `src/citerift/governance/evidence.py:77-131` checks `passed > 0`, no failures, exit 0, one pass per required suite. It never checks `collected` against the full suite or for deselection.
- Reproduction (`$S/exp/partial`): select one test per suite (8 node ids), run `python -m pytest --citerift-report docs/verification/stage-00/test-report.json <8 ids>`, then call `evidence.check_test_report(...)`.
- Observed: `8 passed`, report `collected 8 totals {'passed': 8} dirty False`, `problems: []`.
- Root cause: invariant 1 ("a passing test report") is checked structurally; a run of 8 of 161 tests is accepted as verification evidence.
- Smallest correction: record the command line and the set of collected node ids (or a hash of it) in the report; reject reports where `-k`, `-m`, `--deselect` or explicit node ids were used, or where `collected` is below the count of the full collection.

### F-08 Contract loopholes against the integrity rules (Confirmed engineering defect, Medium-High)

- Code: `schemas/contracts/v1/common.schema.json:85-95` (alternative `value: true`, any JSON), `:122`; `common.schema.json:78-84` (`model` and `confidence` allowed for every status except `verified_fact`); `investigation.schema.json` `retraction_status` only forbids status `model_inference`.
- Reproduction: `cd $C && .venv/bin/python $S/audit-scripts/contracts_probe.py $C`.
- Observed:
  - `A retraction_status conflicting with alternatives 'not_retracted' and false: VALID`
  - `B retraction_status from a model, labelled uncertain with model+confidence: VALID`
  - `B2 not_found + model confidence 0.99: VALID`
- Root cause: the value enum and the absence rule apply to `value` only, not to `alternatives[].value`; the "no model" rule is a status label check. This contradicts docs/data-contracts.md:31-36 ("There is no value meaning 'not retracted'", "A retraction status cannot come from a model") and CREATIVE_DIFFERENTIATION_REVIEW.md:34-37 ("cannot be represented in a valid record"). `test_no_field_can_express_claim_truth` (tests/stage00/test_contracts.py:91-95) only searches the schema text for the word.
- Smallest correction: in `retraction_status`, constrain `alternatives.items.properties.value` to the same enum (minus null) and add `"not": {"anyOf": [{"required": ["model"]}, {"required": ["confidence"]}]}`; add both cases to `invalid_cases.json`.

### F-09 Event order compared as strings (Confirmed engineering defect, Low-Medium)

- Code: `src/citerift/contracts/validate.py:94-95` (`times != sorted(times)`), with optional fractional seconds allowed by `common.schema.json:13-16`.
- Observed (`contracts_probe.py`): `events 00:00:00Z then 00:00:00.5Z (chronological): INVALID -> EVENT_ORDER`; `events 00:00:00.5Z then 00:00:00Z (NOT chronological): VALID`.
- Root cause: `'.'` sorts before `'Z'`.
- Smallest correction: sort on `datetime.fromisoformat(t.replace("Z", "+00:00"))`.

### F-10 Python and JavaScript disagree on patterns; impossible dates accepted (Confirmed engineering defect, Low-Medium)

- Code: every `^...$` pattern in `schemas/contracts/v1/*.json` and `schemas/governance/stage_registry.schema.json` (for example `common.schema.json:11`, `stage_registry.schema.json:55,59`); `\S` in `common.schema.json:21` and the `owner_ref` pattern.
- Observed (`contracts_probe.py`, Python jsonschema): `schema_version '1.0.0\n'`, `investigation_id` and `created_at` with a trailing newline are VALID, and `created_at 2026-02-31T00:00:00Z` is VALID. Node 22 (`/opt/node22/bin/node`): `/^1\.[0-9]+\.[0-9]+$/u.test("1.0.0\n")` -> `false`; `/^\S+$/u.test("ab\x1ccd")` -> `true`, while Python rejects that DOI. Registry: `mutate.py <clone> trailing_newline_ref` (owner_ref ending in `\n`) and `bad_calendar` (`2026-10-25T99:99:99Z`, `2026-13-45T99:99:99Z`) both give `0 errors`.
- Root cause: Python `re.search` lets `$` match before a final newline and treats U+001C to U+001F as whitespace; ECMA-262 does neither. This contradicts CREATIVE_DIFFERENTIATION_REVIEW.md:88-90 and RISK_ANALYSIS.md:136.
- Smallest correction: end patterns with `(?!\n)$`, or forbid control characters with `[^\s\x00-\x1f]`, and add a cross-check test that runs the patterns in Node. Validate timestamps by parsing them in the semantic layer.

### F-11 Correction of a foundation stage is impossible once a dependent is accepted (Confirmed engineering defect, Medium)

- Code: `orchestrator.py:394-409` flags any non-NOT_STARTED dependent of an unaccepted stage, including ACCEPTED_CLOSED dependents. The simulation `guard` for `reopen` (`simulations/stage00/state_machine_model.py:119-120`) does not.
- Reproduction: `$PY $S/audit-scripts/reopen_liveness.py $C $S/exp` (sandbox: accept 00, 01, 02; add a correction amendment to 00; owner reopens 00).
- Observed: `REFUSED  ERROR DEPENDENCY_NOT_ACCEPTED: [stage 02] status ACCEPTED_CLOSED but dependency 00 is not ACCEPTED_CLOSED`. Model on the same state: `model guard: reopen stage 0 (AC->IP) while stage 2 is AC -> True`.
- Root cause: GOVERNANCE.md "Changing an accepted stage" (correction = reopen) cannot be carried out for Stage 00 after Stage 02 is accepted. The differential test (`tests/stage00/test_simulation.py:131-176`) never reaches this state with its two seeds, so the disagreement between model and implementation is untested.
- Smallest correction: decide the rule (cascade reopen of dependents, or allow ACCEPTED dependents with a warning), put it in both the model and the orchestrator, and add this scenario as a fixed differential case.

### F-12 CRLF checkout breaks the evidence hashes (Confirmed engineering defect, Low-Medium)

- Code: `evidence.py` `sha256_file` hashes working-tree bytes; the repository has no `.gitattributes`.
- Reproduction: `git -c core.autocrlf=true clone -q $C $S/exp/crlf; $GOV --root $S/exp/crlf check`.
- Observed: `Consistency check: 8 errors` (7 `EVIDENCE_STALE`, 1 `TEST_EVIDENCE_STALE`), exit 1. `core.autocrlf=true` is the Git for Windows default.
- Smallest correction: add `.gitattributes` with `* text=auto eol=lf`, or hash the committed blob (`git cat-file blob HEAD:<path>`) and report working-tree differences separately.

### F-13 Malformed registry JSON crashes (Confirmed engineering defect, Low)

- Code: `orchestrator.py:98` (`json.loads` in `__init__`), `cli.py` `main` does not catch it; the schema file is read the same way (`orchestrator.py:105`).
- Reproduction: `echo '{"stages": [' > $S/exp/e2/governance/stage_registry.json; $GOV --root $S/exp/e2 check; $GOV --root $S/exp/e2 recover`.
- Observed: both print a Python traceback ending in `json.decoder.JSONDecodeError: Expecting value: line 2 column 1 (char 13)`; `check` exits 1, so it fails closed, but `recover` gives no git or state information. With the schema deleted: `FileNotFoundError` traceback. The test named "corrupt registry" (`tests/stage00/test_recovery.py:72-77`) only edits a status.
- Smallest correction: catch `OSError`/`JSONDecodeError` in `main`, print a `REGISTRY_UNREADABLE` finding and exit 1; let `recover` still print HEAD, branch and dirty paths.

### F-14 Report path outside the repository crashes pytest (Confirmed engineering defect, Low)

- Code: `src/citerift/governance/pytest_report.py:55` (`relative_to` sits before the `try` at line 56).
- Reproduction: `python -m pytest -q tests/stage00/test_unit_model_evidence_memory.py --citerift-report $S/exp/outside/report.json` (in `$S/exp/outreport`).
- Observed: `INTERNALERROR> ValueError: '.../outside/report.json' is not in the subpath of '.../outreport'`; no report is written.
- Smallest correction: compute `exclude` inside the `try`, or exclude only when the path is inside the root.

### F-15 Auto-unblock misattributes the transition (Confirmed engineering defect, Low)

- Code: `orchestrator.py:907-908` (`actor=` and `recorded_by=Actor(stage["executor"])`).
- Reproduction (`$S/exp/clock`): drive Stage 01 to BLOCKED, then the engineering agent runs `citerift-gov blocker resolve 01 "resolved by engineering agent" --id B-01-001`.
- Observed: last history entry `{'stage': '01', 'from': 'BLOCKED', 'to': 'IN_PROGRESS', 'actor': 'external-agent', 'recorded_by': 'external-agent', ...}`.
- Smallest correction: add `--actor`/`--recorded-by` to `blocker resolve` and pass them through; default `recorded_by` to `engineering-agent`, as `transition` does.

### F-16 Future timestamps are accepted (Confirmed engineering defect, Low)

- Code: `orchestrator.py:279` (only non-decreasing order); `utc_now`/`--at` are not bounded.
- Reproduction (`$S/exp/clock`): `transition 01 IN_PROGRESS --actor external-agent --at 2030-01-01T00:00:00Z --apply`, then a normal transition.
- Observed: the first is `ALLOWED` with `check` at 0 errors; the next real-time transition is `REJECTED  ERROR HISTORY_TIME_ORDER: entry 12 is earlier than the one before`.
- Root cause: R-012 (RISKS.md:127-135) covers only a slow clock. A fast clock is accepted and then blocks every correct machine until real time catches up, unless `--at` backdating is used.
- Smallest correction: reject `at` later than now plus a small skew in `propose`, and say so in R-012.

### F-17 Owner refs and record times are not cross-checked (Verified security weakness, Low)

- Reproductions: acceptance and its history entry both set to the authorization's `owner_ref`: `0 errors`. `mutate.py <clone> acceptance_before_history` (acceptance `recorded_at` before its history entry, authorization `recorded_at` after everything): `0 errors`.
- Code: `orchestrator.py:595-621` compares only the acceptance `owner_ref` with the last history entry.
- Smallest correction: require distinct `owner_ref`s per owner decision, and require each record's `recorded_at` to equal the `at` of the history entry that created it.

### F-18 Duplicate JSON keys (Verified security weakness, Low)

- Reproduction (`$S/exp/dupkey`): insert `"status": "ACCEPTED_CLOSED",` before Stage 02's `"status": "NOT_STARTED"`.
- Observed: `check` gives `0 errors` (line 407 of the file shows `ACCEPTED_CLOSED`, the parser uses the later value). A reviewer reading the raw diff sees a value the tool ignores. The same applies to contract records (`validate.py:108,156`).
- Smallest correction: `json.loads(..., object_pairs_hook=...)` that raises on duplicate keys, reported as `REGISTRY_DUPLICATE_KEY`.

### F-19 Dirty tree is not reported by `check` (Documented design limitation, Low)

- Reproduction (`$S/exp/e4`): append to `src/citerift/governance/orchestrator.py` without committing; `check` gives `0 errors, 0 warnings`. `recover` reports `Uncommitted changes: 1`.
- Invariant 6 is worded for committed changes, and CI checks a clean checkout, so this is consistent with the docs. A warning `UNCOMMITTED_OWNED_CHANGE` would help local sessions.

### F-20 `ci-gate` is not independent of the change it gates (Verified security weakness, Medium; verified by inspection, GitHub-side not exercised)

- Facts verified in files: `.github/workflows/ci.yml:3-8` runs on `pull_request` from the PR head; `ci-gate` (`ci.yml:79-91`) is a job in the same file; `.github/rulesets/main-protection.json` requires the context `ci-gate` from app 15368 with `required_approving_review_count: 0`; RISKS.md R-001 states that the agent acts as the owner's account.
- Inference (GitHub semantics, not exercised): a same-repository PR that edits `ci.yml` (or adds another workflow with a job named `ci-gate`) produces a green `ci-gate` for that PR, and with 0 approvals the same identity can merge it. So the ruleset blocks only edits that keep the honest workflow. RISKS.md:55 and RISK_ANALYSIS.md:91 call the check "the independent control", and RISKS.md:21 says "the agent cannot skip CI".
- What is fine: `ci-gate` uses `if: always()` and `test "$RESULT" = "success"`, so skipped, cancelled or failed matrix jobs fail the gate. There is no `pull_request_target`, permissions are `contents: read`, `persist-credentials: false`, `fetch-depth: 0`, the three actions are pinned to 40-character SHAs (the version comments could not be verified offline), and no `${{ github.event.* }}` appears in `run:`.
- Smallest correction: make the docs accurate. For a technical control: a CODEOWNERS entry for `.github/` and `governance/` with one required code-owner review from an identity the agent does not hold (needs D-006 or a bot account).

### F-21 Documents overstate enforcement (Unfulfilled Stage 00 requirement, accuracy of 00-M/00-N, Medium)

- GOVERNANCE.md:108 "Enforced (by `citerift-gov check` and CI): everything in 'Stage lifecycle' above": F-02 to F-06 contradict it.
- RISKS.md:41 (R-003) "detects inconsistent hand edits (history replay, record coherence, evidence hashes, revisions)": F-03, F-04, F-05, F-17 and F-18 are inconsistent edits that are not detected; R-003 presents only fully consistent forgeries as undetectable.
- RISKS.md:21 (R-001) "the agent cannot skip CI either": see F-20.
- RISK_ANALYSIS.md:133 "Stage 02 can add new schema files under `v1/` as a minor version": it makes Stage 00 stale (F-22).
- CREATIVE_DIFFERENTIATION_REVIEW.md:58-60 cites TEST_RESULTS.md section 8 for "refuses to mark Stage 00 verified while CI evidence is missing"; section 8 (TEST_RESULTS.md:217-223) records `BLOCKER_OPEN` and `GATE_NOT_PASSED`, not missing CI evidence.
- CREATIVE review 2.1 and 2.5: see F-08 and F-10.
- Smallest correction: amend these lines, and add F-01 to F-08 to RISKS.md (as defects with stage 00) until fixed.

### F-22 Handoff to Stage 02 (Future-stage dependency, Low)

- Reproduction (`$S/exp/stage02`): a fake `tests/stage02/test_consumer.py` loads `schemas/contracts/v1`, validates all three valid fixtures, and resolves a new `schemas/contracts/stage02/retraction_record.schema.json` that `$ref`s v1 by URN: `2 passed`, `check-schemas` `3 schemas checked, 0 problems`, and after committing, governance `check` `0 errors`. Consuming the contracts outside Stage 00 owned paths works without changing Stage 00 files.
- Moving the schema into `schemas/contracts/v1/` (the "minor version" path in docs/data-contracts.md:53-61) and committing gives `ERROR VERIFICATION_STALE` for Stage 00. A v1 minor version therefore needs an owner-approved `enhancement` amendment to Stage 00.
- `transition 02 AUTHORIZED --actor owner --owner-ref cmsg_FAKEOWNERREF01 --reason test` (dry run and with `--apply` in `$S/exp/e1`): `REJECTED  ERROR DEPENDENCY_NOT_ACCEPTED: [stage 02] status AUTHORIZED but dependency 01 is not ACCEPTED_CLOSED`; nothing written. Correct.

### F-23 Type checking scope (Optional enhancement, Low)

`pyproject.toml` `[tool.mypy] files = ["src"]`; `mypy simulations tests` reports 20 errors, including `missing library stubs or py.typed marker` for `citerift.governance.model`. Later stages that type-check against the package will need `src/citerift/py.typed`.

## 4. Main invariants (GOVERNANCE.md:44-58) against the code

| Inv. | Claim | Result |
|---|---|---|
| 1 | Verified only with artifacts, clean passing report at the revision, gates with existing evidence, CI | Partly holds. Artifacts and report are hashed and checked. Bypasses: partial report (F-07), unpinned and `.` gate evidence (F-02), CI and gate requirements removable from the registry (F-03). |
| 2 | Accepted only from verified, by owner, for verified revision | Holds against the registry: `mutate.py acc_rev_mismatch` gives `ERROR ACCEPTANCE_STALE`; agent-actor acceptance refused (`test_06`). Owner identity is self-declared (`--actor owner` with an invented `cmsg_` ref is ALLOWED, E1c), as documented in R-002. |
| 3 | Authorized only when dependencies accepted | Holds for proposals and the current state (E1 refused). Not checked over history (F-04). |
| 4 | At most one active engineering stage | Holds for the current state (`mutate.py two_active` gives `MULTIPLE_ACTIVE_STAGES`). Not checked over history (F-04); switched off by a policy flag (F-03). |
| 5 | Status equals replayed history | Holds: `mutate.py status_mismatch` gives `STATUS_HISTORY_CONFLICT`. Replay ignores the amendment requirement (F-05). |
| 6 | Evidence immutable; owned-path commits make the stage stale | Artifacts and report: holds (`EVIDENCE_MISSING` and `EVIDENCE_STALE` reproduced). Gate evidence: no (F-02). Merge revert: no (F-01). Owned paths removable (F-03). CRLF false positives (F-12). |
| 7 | No open blocker or open critical defect on a verified or accepted stage | Holds for well-formed RISKS.md entries (`OPEN_CRITICAL_DEFECT` reproduced). Fails open on malformed headings and for `Stage: project` (F-06). |

Failure and recovery: corrupt JSON fails closed with a traceback (F-13); missing registry exits 2 with a clear message; a missing artifact gives `EVIDENCE_MISSING` plus `GATE_EVIDENCE_MISSING`; a missing gate-only file gives `GATE_EVIDENCE_MISSING`; a dirty tree is not reported (F-19). Shallow clones (`--depth 1` and `--depth 4`) fail closed with `REVISION_NOT_FOUND ... (repository is shallow; fetch full history)` and a misleading extra `VERIFICATION_STALE`. CI uses `fetch-depth: 0`.

## 5. Risks R-001, R-002, R-003

- **R-001** (agent acts under owner's GitHub identity). The fact matches DECISIONS.md D-005. Of its mitigations, `owner_ref` is implemented (`_edge_problems` `OWNER_REF_REQUIRED`, `HISTORY_OWNER_REF_MISSING`, schema pattern `stage_registry.schema.json:56-60`). But `--actor owner` is a self-declared CLI flag, and any `cmsg_` plus 10 alphanumerics passes (E1c: withdraw Stage 01, ALLOWED; E1d: `--actor external-agent` for Stage 01, ALLOWED). "No bypass actors" is true of the ruleset file; "the agent cannot skip CI" is inaccurate (F-20). The description of the risk is accurate; the mitigation claim is overstated.
- **R-002** (owner refs not machine-verified). Accurate. The code checks only presence, pattern and acceptance/history equality. Gaps the entry does not mention: reuse of one ref for several decisions, and a trailing newline in a ref (F-10, F-17).
- **R-003** (hand edits). The prevention part is accurate. The detection part is overstated: several inconsistent edits are not detected (F-03, F-04, F-05, F-17, F-18), and the docs present only fully consistent forgery as undetectable.

## 6. Contracts against docs/data-contracts.md

Checked each row of the assertion table (data-contracts.md:18-24) against `common.schema.json:72-124`: `verified_fact` (provenance minItems 1, no model or confidence, value not null), `model_inference` (model and confidence required), `uncertain` (reason), `unavailable` (null value plus reason), `conflicting` (null value, 2 or more alternatives with provenance) all match. The absence rule and the `not model_inference` rule match for `value`/`status`, but not for `alternatives` or for `model` on `uncertain` (F-08). The semantic checks match the description (`validate.py:70-102`), except for the ordering bug (F-09). "Synthetic data is labeled" is a convention: `synthetic` is optional and nothing enforces the `10.5555` prefix. The fixture count is right: 35 invalid cases, 3 valid fixtures, `ar` and `en` citations present.

## 7. CREATIVE_DIFFERENTIATION_REVIEW.md claims against the code

| Claim | Where it is real | Status |
|---|---|---|
| 2.1 five statuses with structural rules | `schemas/contracts/v1/common.schema.json:66-124` | present; "cannot be represented" is false (F-08) |
| 2.1 35 invalid fixtures, mutant M3 killed | `tests/stage00/fixtures/contracts/v1/invalid_cases.json` (35), `mutation_check.py` M3 (re-run: KILLED) | reproduced |
| 2.2 12 mandatory scenarios | `tests/stage00/test_integration_scenarios.py:24-367` (test_01 to test_12, 17 functions) | present |
| 2.2 19 hand edits | `tests/stage00/test_registry_tampering.py:156` (`len(CASES) == 19`) | present |
| 2.2 9/9 mutants | `docs/verification/stage-00/mutation/mutation_check.py` (re-run 9/9 KILLED) | reproduced; not run in CI |
| 2.2 refusal "while CI evidence is missing (TEST_RESULTS §8)" | TEST_RESULTS.md:217-223 records other codes | documented only, citation mismatch |
| 2.3 differential test; iteration-1 defect re-found | `tests/stage00/test_simulation.py:131-176`, `:55-69` | present; misses F-11 |
| 2.4 recovery in an isolated process | `tests/stage00/test_recovery.py:24-27` (`sys.executable -I -m citerift.governance.cli`), `:35-70` | present |
| 2.5 language and revision id on citations | `investigation.schema.json` `wiki_citation.article` (required `language`, `revision_id`) | present |
| 2.5 patterns behave the same in Python and JS | no test; RISK_ANALYSIS.md:136 is a manual review | false (F-10) |

## 8. Areas checked with nothing found

Duplicate stage ids (`STAGE_DUPLICATE` reproduced); uppercase SHA and leading-space `owner_ref` (rejected by schema); dependency cycles (Kahn check, tested); evidence path traversal and absolute paths (`inside()` resolves symlinks; an outside symlink gives `EVIDENCE_OUTSIDE_REPOSITORY`, reproduced); no shell in git calls (list arguments, `gitutil.py:17-26`); atomic registry writes (`orchestrator.py:1087-1095`); `render-status` exact match; history `seq` contiguity; the verified commit's owned paths equal the implementation revision's (`git diff --stat 30e4462 741476c -- <owned>` is empty); later commits touch no owned path; PR #1 is a true merge commit (`c8618a3` parents `e19b559 70ce78e`); the test reports are at `741476c`, clean, 161/161; lockfile is current.

## 9. Reproduced facts and inference

Reproduced in this audit: everything under "Observed" in F-01 to F-19 and F-22, the tool results in section 1, the mutation re-run and the invariant table. Inference, not exercised: the GitHub behavior in F-20 (PR-modified workflow satisfying the required check), the claim that `core.autocrlf=true` is the Git for Windows default (F-12), and the severity ratings.

## Verdict

The builder's tool results reproduce, but the claim that the governance layer enforces GOVERNANCE.md invariants 1, 3, 4, 6 and 7 does not hold: there are reproducible bypasses (F-01 to F-08) and a model/implementation divergence (F-11). The 00-F, 00-M, 00-N and 00-P gate conclusions should be re-examined by the owner. This review does not change any stage state; only the owner can decide on a correction amendment.

NOT VERIFIED
