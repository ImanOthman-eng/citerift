# Independent final review of CITERIFT Stage 00 at `4a396fb`

Reviewer: a separate reviewer agent that took no part in writing the code. Scope: the Stage 00
governance foundation under correction A-00-001, at revision
`4a396fb31601b94965df8ba9823447225c30bd04`. Stage 01 is out of scope; no Stage 01 finding is made
or predicted. `TEST_RESULTS.md`, `HANDOFF.md` and the `{{RVER7}}` / `{{HANDOFF_PASSED}}` placeholders
are expected to be missing and are not counted.

`$W` below is `/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review3`.
Every experiment ran in throwaway sandboxes or clones under `$W/sandbox-*`. Nothing in
`/home/user/citerift` was changed. No git remote, GitHub or network service was used.

One disclosure about the reviewed copy: the `.venv/` of the review working copy was empty. My first
`uv run --no-sync pytest` there created that empty, git-ignored `.venv/` directory
(timestamp 20:30:17, 35 seconds after the checkout). It failed to import the plugin (see 1.1). No
tracked file was changed (`git status --porcelain` is empty; only `!! .venv/` is listed under
`--ignored`). I did not delete the directory. All later runs used `$W/base`, a `git clone` of the
review copy at the same revision, with `uv sync --locked --offline` (from the local uv cache, no network).

Severity scale: as given by the caller. A finding counts only if I reproduced it. Items I did not
reproduce, or that match a documented design choice, are listed as observations.

## 1 Baseline (commands and outputs)

### 1.1 In the review working copy (`review3-tree`, empty `.venv`)

```
$ uv run --no-sync pytest -q -p no:cacheprovider
ImportError: Error importing plugin "citerift.governance.pytest_report": No module named 'citerift'
```

The environment there was not synced, so `uv run --no-sync` fell back to the system Python 3.13 `pytest`.

### 1.2 In `$W/base` (clone of `4a396fb`, `uv sync --locked --offline`)

Every command also printed `warning: The UV_NATIVE_TLS environment variable is deprecated ...`.

| Command | Exit | Output |
|---|---|---|
| `uv run --no-sync pytest -q` | 0 | `363 passed in 250.09s (0:04:10)` |
| `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| `uv run --no-sync mypy` | 0 | `Success: no issues found in 12 source files` |
| `uv run --no-sync citerift-gov check` | 0 | `Consistency check: 0 errors, 0 warnings` |

Raw output: `$W/out/baseline_pytest_full.txt`, `$W/out/baseline_static.txt`. `node` was
available (`/opt/node22/bin/node`), so no test was skipped. The `uv.lock` sha256 matches
SPECIFICATION.md:171 (`52980fe6…fe50`). The `model-results.json` sha256 matches SIMULATION_REPORT.md
(`f41c757f…6dcd`).

## 2 Earlier fixes rechecked

For each fix I ran variants of the original attack (`$W/scripts/recheck_x.py`, output
`$W/out/recheck_x.txt`, plus the finding scripts).

| Id | Variants tried | Result |
|---|---|---|
| X-01 | gate evidence `a/../../../NOTES.md`, `a//b`, `./a`, a path through a committed directory symlink, a trailing `/`, `http://` | all refused (`GATE_EVIDENCE_UNPINNED`, or `REGISTRY_SCHEMA` for `http://`). **Bypass of the intent:** a plain path to a git-ignored or untracked file under an owned path counts as pinned (Y-09). |
| X-02 | `-o python_functions=…`, another ini file, `--deselect`, `-k`, `-m`, `--keep-duplicates tests tests`, `--co`, `--setup-only`, `-x` | all partial or failing, as specified. **Bypasses of the intent:** a run narrowed by editing tracked test files is recorded as clean and complete when the report path is that file (Y-01) or when the edit is hidden with `--skip-worktree` / `--assume-unchanged` (Y-02). Skipped tests never count against completeness (Y-03). |
| X-03 | `PYTEST_ADDOPTS="-p plug"`, `-pplug` (no space), `--deselect`, `--keep-duplicates` | all `complete=false`. A tracked conftest modified in the working tree escapes the "committed conftest" rule through Y-01 or Y-02, because only the path is checked, not the content. |
| X-04 | `ls -A src` guard; `.pth` in `src` (refused by the guard) | the guard holds for files beside the package. **Bypass:** a one-line `pyproject.toml` mypy-plugin setting rewrites `src/citerift/governance/cli.py` on disk before the CI check step (Y-08). |
| X-05 | non-UTF-8 file name in the evidence directory, damaged git index, absolute `verification_dir`, deeply nested JSON | **5 more tracebacks** (Y-11). |
| X-06 | bold, indented and lower-case fields, zero-width joiner in topics | refused or folded as specified. **Bypass:** non-ASCII decimal digits in `Stage` make a valid open critical defect stop blocking (Y-04). |
| X-07 | removing Stage 01, duplicating Stage 02 | `DEPENDENCY_UNKNOWN`, `STAGE_DUPLICATE`: holds. |
| X-08 | not re-attacked beyond the sandbox flows used here (all blocker flows behaved as specified) | holds as far as tested. |
| X-09 | `.git/shallow` naming `HEAD` | fails closed (`REVISION_NOT_IN_HISTORY`, `VERIFICATION_STALE`): holds. |
| X-10 | blocker open at the acceptance second (refused); resolved in the same second (allowed, by the `resolved_at <= at` rule) | holds. |
| X-11 | 18 real edition codes (`zh-classical`, `zh-min-nan`, `be-x-old`, `be-tarask`, `roa-tara`, `map-bms`, `bat-smg`, `cbk-zam`, `fiu-vro`, `nds-nl`, …) | all accepted: holds. |
| X-12 | read only | holds. |
| X-13 | reuse of the acceptance's owner reference with the default time (refused) | **Bypass:** the same reuse is accepted with `amend --at` set to the acceptance second or back-dated between verification and acceptance (Y-07). An enhancement written on a verified, not yet accepted stage passes `check` and covers owned-code drift (Y-06). |

## 3 New findings

Reproduced: 2 medium, 4 low-medium, 7 low, none critical.

| Id | Severity | File:line | Description | Reproduction | Expected vs actual |
|---|---|---|---|---|---|
| Y-01 | medium | src/citerift/governance/pytest_report.py:75-81 (`exclude`), gitutil.py:134-144 | The plugin leaves the report path out of the dirty check, whatever that path is, even a tracked source or test file. Cut a tracked test file down to 2 tests, run `pytest --citerift-report <that file>`, copy the report out and `git checkout` the file. The result is a report of a modified tree with `dirty:false`. No git flag, plugin or committed code is needed. | `$W/base/.venv/bin/python $W/scripts/Y01_report_path_hides_dirty.py` | Expected `dirty:true` or `TEST_EVIDENCE_DIRTY`. Actual: `214 passed` (of 363), `dirty:false`, `dirty_paths:[]`, `complete:true`, and `check_test_report` returns no problems. |
| Y-02 | low-medium | pytest_report.py:81, gitutil.py:134-137 (`git status --porcelain`) | "Clean tree" is decided by `git status`, which does not show tracked files flagged `--skip-worktree` or `--assume-unchanged`. Every test file is narrowed to 2 tests and the edits are hidden. R-004 and GOVERNANCE invariant 1 do not list this path. | `… $W/scripts/Y02_skip_worktree.py` | Expected dirty or partial. Actual: `44 passed`, `revision=HEAD`, `dirty:false`, `complete:true`, no problems. |
| Y-03 | low-medium | evidence.py:109-179 (`check_test_report`, only `failed`/`error`/`not_run` are counted), pytest_report.py:203-209 | Completeness covers selection, not execution. Skipped (and xfailed) outcomes never count against the evidence; one passed test per required suite is enough. Here a committed conftest marks 355 of 363 tests skip. It forges nothing, and the report is truthful. | `… $W/scripts/Y03_skipped_tests_complete.py` | Expected the evidence to be refused, or at least a warning, as for other narrowing. Actual: `8 passed, 355 skipped`, `complete:true`, no problems. |
| Y-04 | medium | src/citerift/governance/memory.py:233 (`\d{2}` in the Stage check), memory.py:238-247 (`open_critical_defects`); also memory.py:20 (`\d{3}` in `_HEADING`) | Python `\d` matches every Unicode decimal digit. An open critical defect with `Stage: ٠٠` (Arabic-Indic) or `Stage: ００` (fullwidth) passes the RISKS.md validation, reads as Stage 00, and does not block it: Stage 00 is verified and accepted with 0 errors. Control: ASCII `00` gives `OPEN_CRITICAL_DEFECT`. The same applies to entry ids: `R-001` and `R-٠٠١` are two ids, so `RISK_DUPLICATE_ID` is not raised. The owner writes in Arabic, so these digits are a plausible input. | `… $W/scripts/Y04_unicode_digit_stage.py` | Expected `RISK_INVALID_FIELD` or `OPEN_CRITICAL_DEFECT`. Actual: `memory problems: []`, verification and acceptance allowed, and `check` shows no error after acceptance. |
| Y-05 | low-medium | schemas/contracts/v1/investigation.schema.json:46-71; common.schema.json:121-124 | A `conflicting` retraction status accepts alternatives that all agree, including two `not_found_in_checked_sources`. It also accepts `retracted` against `not_found_in_checked_sources`. In both cases an absence of records is stored as one side of a disagreement, and the alternative carries no `uncertain` status. docs/data-contracts.md:32 ("Missing records are not evidence") and :44-46 ("`not_found_in_checked_sources` … always `uncertain` with provenance") say otherwise. No "not retracted" value and no `verified_fact` results, so this is not critical. | `… $W/scripts/Y05_Y12_Y13_contracts.py` (cases a) | Expected rejection, or a rule that conflicting alternatives differ and are positive records. Actual: both records `valid`. |
| Y-06 | low-medium | orchestrator.py:1039-1098 (`_amendment_findings`), :969-973 (`covering`) | `check` does not require an amendment to belong to an accepted stage, or to be recorded after its acceptance. The CLI refuses one (`AMENDMENT_NOT_APPLICABLE`). A hand-written enhancement on a VERIFIED stage passes `check` and covers owned-path drift, so the owner can accept "the verified revision" while the owned code at HEAD is another revision that has no CI record. | `… $W/scripts/Y06_enhancement_on_verified_stage.py` | Expected an error (R-003: hand edits that break a tool rule are detected). Actual: `check` shows no error, and the acceptance of the verified revision (`1fa1151e…` in the saved run) is allowed while owned code is at `846fc1bd…`. |
| Y-07 | low | orchestrator.py:1100-1121 (`_amendment_ref_findings`, `at < recorded_at` at :1110), :1489 (`at or self._now()`) | The X-13 rule "an amendment cites an owner statement not cited before" compares self-chosen times. The acceptance's own reference is refused with the default time, but accepted with `amend --at` equal to the acceptance second (the documented "same time" exception), or back-dated between verification and acceptance. In the back-dated case the stage was not yet accepted at the amendment's recorded time. | `… $W/scripts/Y07_amendment_ref_timing.py` | Expected `OWNER_REF_REUSED`, or an error for an amendment that predates the acceptance. Actual: `check errors: none` in both cases. |
| Y-08 | low | .github/workflows/ci.yml:61-72 (mypy step before the governance step); pyproject.toml (not owned) | X-04 residual. A committed root file named in `pyproject.toml` `[tool.mypy] plugins` runs during the CI "Static analysis" step. It rewrites the checked-out `src/citerift/governance/cli.py` before `python -P -m citerift.governance.cli check`, so the check prints `0 errors` for a registry with 5 errors. No owned path is changed in git, so Stage 00 does not become stale. The demonstration patches `check` only; `render-status --check` and pytest would need the same treatment in a real attack. This falls under R-016's general statement that `pyproject.toml` changes can change what CI executes, but the documents present `-P` and the src guard as protecting the checker from `pyproject.toml` (see §4). | `… $W/scripts/Y08_mypy_plugin_rewrites_ci_checker.py` | Expected the honest result (`5 errors`, exit 1). Actual: the guard passes, mypy succeeds, and the check prints `0 errors, 0 warnings` with exit 0. `git status`: `M src/citerift/governance/cli.py`. |
| Y-09 | low | orchestrator.py:878 and :904-905 (`_owned` counts as pinned) | A gate may cite a git-ignored (or untracked) file under an owned path. It counts as hash-pinned although nothing pins it: verification is allowed, and the file can then be rewritten with `check` still at 0 errors. Only a fresh clone, where the file is missing, reports it. Detected in CI, so the severity is low. | `… $W/scripts/Y09_ignored_owned_file_as_gate_evidence.py` | Expected `GATE_EVIDENCE_UNPINNED` (not tracked at the verified revision). Actual: allowed, then `0 errors` after the rewrite. In the clone: `GATE_EVIDENCE_MISSING`, `GATE_EVIDENCE_UNPINNED`. |
| Y-10 | low | orchestrator.py:813-829; schemas/governance/stage_registry.schema.json:223 | The CI record is not tied to `project.repository`. A run URL from any other GitHub repository is accepted. The sandbox helper itself uses `example/repo`. | `… $W/scripts/Y10_ci_run_other_repository.py` | Expected a mismatch error. Actual: allowed, no findings. |
| Y-11 | low | evidence.py:36-37 and gitutil.py:45-58 (`ignored`, text-mode stdin); orchestrator.py:1591 (`recover` → `dirty_paths`); evidence.py:36 (`relative_to` for an absolute `verification_dir`); formats.py `loads_strict` callers (RecursionError is not a ValueError) | Five inputs still end in a traceback: (A) a non-UTF-8 file name in the evidence directory (`UnicodeEncodeError` at verification); (B) a damaged `.git/index` (`GitUnavailableError` from `recover` and from a verification); (C) an absolute `verification_dir`, which the schema accepts (`ValueError` at verification); (D) a deeply nested registry (`RecursionError` in `check`) and the same in `citerift-contracts validate`. | `… $W/scripts/Y11_tracebacks.py` | Expected named errors, exit 1 or 2. Actual: a Python traceback in each case. |
| Y-12 | low | schemas/contracts/v1/investigation.schema.json:72-83 | A `verified_fact` `retraction_date` is accepted next to `retraction_status: not_found_in_checked_sources`. The record then states a verified retraction date for a paper whose sources hold no retraction record. No semantic check covers it. | `… $W/scripts/Y05_Y12_Y13_contracts.py` (case b) | Expected `SCHEMA_VIOLATION` or a semantic problem. Actual: `valid`. |
| Y-13 | low | schemas/contracts/v1/common.schema.json:19-24 | The DOI pattern rejects a subdivided registrant code such as `10.1000.10/abc`, which the DOI Handbook (§2.2.2) allows. The schema's own description says the pattern "only rejects strings that cannot be a DOI". | same script (case c) | Expected `valid`. Actual: `INVALID … does not match '^10\.[0-9]{4,9}/…'`. |

Root causes shared between findings: Y-01 and Y-02 both trust `git status` and the working-tree path.
Y-06 and Y-07 both come from the absence of any check that an amendment is recorded after its stage's
acceptance.

### Observations (not counted)

- O-1, reproduced but documented. Topic folding covers case, separators and format (Cf) characters,
  as GOVERNANCE.md:93-94 says. Arabic tatweel (U+0640) and harakat are not folded, so two accepted
  Arabic decisions that differ only by them are not a `DECISION_CONTRADICTION`
  (`$W/scripts/obs_arabic_topics.py`). Worth adding, given that the owner writes in Arabic.
- O-2, not reproducible offline. For `pull_request` events, `actions/checkout` tests the merge commit,
  while the run's `head_sha` is the PR head. A CI record with `head_sha == revision` from a
  pull_request run therefore did not test exactly that revision.
- O-3. `owner_ref` reuse is compared as an exact string. The same statement cited in another spelling
  (for example two URL forms) is not recognized as reused. This is within R-002.
- O-4. `DECISIONS.md` entries with `Status: accepted` need no reference to the owner's words. Nothing
  claims otherwise.
- O-5. `dirty_paths` parses porcelain v1 without `-z`. An untracked file named `x -> <report path>`
  is parsed as the report path and dropped from the dirty list. It gives no more than
  `.git/info/exclude` already gives (R-004).
- O-6. The CI pytest step does not validate its own `ci-test-report.json` for completeness. A green CI
  run can therefore come from a partial run. The local report is checked separately.
- O-7, identity (docs/identity.md rules 2 to 4). In tracked files I found no `<name terms>` outside the
  repository account login. I could only derive the terms from the account login and the session's
  account context, so the scan cannot prove the absence of every form of the legal name. Trademark
  marks: the only hit is the rule itself at docs/identity.md:44. No AI tool is presented as creator or
  owner. The last commits use the `Assisted-by: Claude Code (AI coding agent)` trailer
  (`$W/scripts/identity_scan.py`, terms read from the environment).

## 4 Documentation accuracy

| Location | Claim | Evidence against it |
|---|---|---|
| GOVERNANCE.md:47-48 (invariant 1) | a passing test report "produced at the verified revision from a clean tree" | Y-01: the report of a modified tree says `dirty:false` with no git trick; Y-02: skip-worktree/assume-unchanged. |
| GOVERNANCE.md:49-58 | "The report must record a complete run … These rules make an honest narrowing visible" | Y-03: 355 of 363 tests skipped by committed code, accepted as complete; Y-01 (214 of 363). |
| GOVERNANCE.md:55-56; SPECIFICATION.md:63-66; MATHEMATICAL_MODEL.md:209-210 | a file under an owned path is pinned, "its content is then bound by I7's drift rule" | Y-09: an ignored or untracked file under an owned path is not bound by anything, because the drift rule compares committed trees. |
| GOVERNANCE.md:88-89 (invariant 7); RISKS.md:5-7 | "A verified or accepted stage has no … open critical defect"; Stage is "two-digit ids" | Y-04: `Stage: ٠٠` is accepted as valid and does not block. |
| GOVERNANCE.md:116-118; data-contracts.md versioning | an enhancement needs "an owner statement not cited before" | Y-07: reuse is accepted with a chosen `--at`. |
| GOVERNANCE.md:169-170; RISKS.md:48-49 (R-003) | `check` detects "hand edits that break invariants 1 to 7"; "reports a hand edit that breaks any rule a transition is checked against" | Y-06: a hand-written amendment on a non-accepted stage, which the tool refuses to write, is not reported, and it changes what the drift rule accepts. |
| GOVERNANCE.md:162-163 | "Prevented: … an owner decision taken by another actor" | The actor is a self-declared CLI flag. RISK_ANALYSIS.md:45 says so ("`--actor owner` is a flag the agent can pass"). GOVERNANCE.md should say "recorded with another actor". |
| GOVERNANCE.md:189-197; RISK_ANALYSIS.md:48 | `-P`/`PYTHONPATH=src` mean "changing the entry points in `pyproject.toml` does not replace the checker"; the residual is "a change of dependencies or pytest options" / "build and pytest settings" | Y-08: a mypy setting, which is neither a build nor a pytest setting, replaces the checker's code on disk before the check. The residual should say that any tool configuration in `pyproject.toml` can run code before the governance step, including code that rewrites owned files. |
| GOVERNANCE.md:59-60 vs RISKS.md:88-89 (R-004) | GOVERNANCE: "an untracked file the run imports"; R-004: "a module the run imports from outside the tree" | They disagree. R-004 omits untracked or ignored files inside the tree (for example an excluded `tests/stage00/__init__.py`), and neither covers Y-01/Y-02 (modified tracked files that pass as clean). |
| RISKS.md:78-80 (R-004) | the check "verifies that the recorded CI run tested the verified revision"; "The run URL is public for this repository" | It verifies only that a field of the record equals the revision. The URL is not tied to this repository (Y-10). See also O-2. |
| docs/data-contracts.md:32-34, 44-46; SPECIFICATION.md:151-153 | "Missing records are not evidence"; `not_found_in_checked_sources` is "always `uncertain` with provenance" | Y-05: allowed as a status-less conflicting alternative, including all-agreeing "conflicts". |
| CREATIVE_DIFFERENTIATION_REVIEW.md:48-50 | in Stages 04 to 06 the share of records that state absence of retraction as anything other than `uncertain` "must be 0, checked by validating every record" | Validation with 1.0.1 accepts such records (Y-05), so validating every record would not measure it. |
| common.schema.json:20 | DOI pattern "only rejects strings that cannot be a DOI" | Y-13. |
| docs/verification/stage-00/review/README.md:65; RISK_ANALYSIS.md:113; CHANGELOG.md:69-71 | X-05 "fixed: named errors" | True for the 17 tested inputs; Y-11 lists 5 more. RISK_ANALYSIS.md:126 ("Random byte damage never produces an exception") is literally true. |

Claims I checked that are accurate: the ruleset file matches GOVERNANCE.md:182-184. The CI `node`
requirement (test_contracts.py:266-268) matches SPECIFICATION.md:173-174. The 47 invalid contract
cases and 3 valid fixtures match data-contracts.md. The `uv.lock` and `model-results.json` hashes
match.

### 4.1 Residual risks: are they stated honestly?

| Risk | Prevented | Only detected | Not enforceable | Assessment |
|---|---|---|---|---|
| R-001 shared GitHub identity | nothing | nothing | identity separation | Honest. |
| R-002 owner references | owner edges without a reference are refused (CLI); reuse before verification is refused | reuse before verification on hand edits | content of the reference | Honest. Add: the reuse rules compare exact strings (O-3) and self-chosen times (Y-07), so they bind only an honest writer. |
| R-003 hand edits | nothing | most rules, by `check` | consistent forgery | Mostly honest. Overstated: amendment placement is not checked (Y-06). |
| R-004 test report and CI record | narrowing options, ini overrides, plugins, uncommitted conftests (honest runs) | the same, by `check` on the report | code inside the test process | Understated. A modified tracked file passes as a clean tree with no in-process code (Y-01, Y-02). Skipped tests are not narrowing at all (Y-03). The CI record is not tied to the repository (Y-10). |
| R-016 CI gate editable | the src guard for files beside the package | owned-path drift for the workflow and ruleset | CI independence | Honest in general ("a change to them can change what CI executes"), but it frames that change as dependencies and pytest options. A one-line tool setting replaces the checker on disk (Y-08). |

## 5 Evidence scripts

All in `$W/scripts/`. Run with `$W/base/.venv/bin/python <script>` from `$W/scripts`. Outputs from
the final run are in `$W/out/<script name>.txt`. `lib.py` holds the shared helpers: it puts
`$W/base/src` and `$W/base/tests/stage00` on the path and reuses the repository's own `sandbox_repo.py`.

| Script | Finding | Runtime |
|---|---|---|
| `Y01_report_path_hides_dirty.py` | Y-01 | ~3 min (runs 214 real tests) |
| `Y02_skip_worktree.py` | Y-02 | ~1 min |
| `Y03_skipped_tests_complete.py` | Y-03 | ~10 s |
| `Y04_unicode_digit_stage.py` | Y-04 | seconds |
| `Y05_Y12_Y13_contracts.py` | Y-05, Y-12, Y-13 | seconds |
| `Y06_enhancement_on_verified_stage.py` | Y-06 | seconds |
| `Y07_amendment_ref_timing.py` | Y-07 | seconds |
| `Y08_mypy_plugin_rewrites_ci_checker.py` | Y-08 | ~1 min |
| `Y09_ignored_owned_file_as_gate_evidence.py` | Y-09 | seconds |
| `Y10_ci_run_other_repository.py` | Y-10 | seconds |
| `Y11_tracebacks.py` | Y-11 | seconds |
| `recheck_x.py` | §2 variants | ~10 s |
| `obs_arabic_topics.py` | O-1 | seconds |
| `identity_scan.py` | O-7 (reads `NAME_TERMS` and `ALLOWED_TOKENS` from the environment; no name term is stored) | seconds |

## 6 Verdict

13 findings were reproduced: 2 medium, 4 low-medium, 7 low. None is critical. Under the stated rule
(any reproduced finding), the verdict is:

NOT VERIFIED
