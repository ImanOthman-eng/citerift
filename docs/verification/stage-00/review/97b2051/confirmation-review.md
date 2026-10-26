# Confirmation review of CITERIFT Stage 00 at `97b2051`

Reviewer: an independent reviewer agent that wrote none of the reviewed code. Scope: the Stage 00 governance
foundation under correction A-00-001 at `97b2051978ab70159cd5eb8bba56642613272276`: are the earlier findings
(F-01..F-19, V-01..V-16, X-01..X-13, Y-01..Y-13) really fixed, did the Y fixes break anything, are the documents
accurate. Stage 01 is out of scope; nothing here concerns its findings. `TEST_RESULTS.md`, `HANDOFF.md` and the
`{{RVER7}}` / `{{HANDOFF_PASSED}}` placeholders are expected to be missing and are not counted.

`$W` = `/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4`.
`$W/base` is a `git clone` of the review working copy at `97b2051` with `uv sync --locked --offline`. Every
experiment ran in a throwaway clone or sandbox under `$W/sandbox-*`, `$W/x2/exp/*` or `$W/tmp*`. Nothing in
`/home/user/citerift` or in the `review4-tree` working copy was changed (in `review4-tree` I only ran the read-only
`check` and `render-status --check` with `PYTHONDONTWRITEBYTECODE=1`; `git status --porcelain --ignored` there is
empty). No git remote, GitHub or network service was used. Scripts are in `$W/scripts/`, outputs in `$W/out/`.

Severity scale as given by the caller. A defect counts only if I reproduced it.

## 1 Baseline

Run from `$W/base`. Every `uv run` also printed `warning: The UV_NATIVE_TLS environment variable is deprecated ...`.

| Command | Exit | Output line |
|---|---|---|
| `uv run --no-sync pytest -q -p no:cacheprovider` | 0 | `393 passed in 263.23s (0:04:23)` |
| `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| `uv run --no-sync ruff format --check .` | 0 | `57 files already formatted` |
| `uv run --no-sync mypy` | 0 | `Success: no issues found in 12 source files` |
| `uv run --no-sync citerift-gov check` | 0 | `Consistency check: 0 errors, 0 warnings` |
| `uv run --no-sync citerift-gov render-status --check` | 0 | `PROJECT_STATUS.md is up to date` |
| `uv run --no-sync citerift-gov recover` | 0 | `Consistency: 0 errors, 0 warnings`; Stage 00 `IN_PROGRESS`, Stage 01 `AUTHORIZED` |

The same `check` and `render-status --check`, run read-only on the `review4-tree` working copy itself: `0 errors,
0 warnings` and `up to date`. After the full test run `git status --porcelain` in `$W/base` is empty (only ignored
caches). `node` was available, so no test was skipped. `uv.lock` sha256 is `52980fe6…fe50` and
`simulation/model-results.json` sha256 is `f41c757f…6dcd`, as SPECIFICATION.md:190 and SIMULATION_REPORT.md:30 say.
Raw output: `$W/baseline-pytest.txt`, `$W/baseline-static.txt`. In the saved outputs the repository account login is replaced by `<repository account>`.

## 2 Confirmation table

Evidence scripts (all in `$W/scripts/`; outputs in `$W/out/<name>.txt`):

- `orig_y/Y*.py`: the third reviewer's scripts, unchanged except `lib.py` pointed at `$W` (run with `W=$W`).
- `orig_x/*.py`: the second reviewer's scripts, paths repointed to `$W/x2` and `9e025c9` → `97b2051`; base sandbox
  from its own `mkbase.py`.
- `orig_f/*.py` + `run_audit_scripts.sh`: the audit's scripts (F findings); `reopen_liveness_adapted.py` (two
  adaptations: Stage 02 gets an owned path, the amendment gets a new owner reference, both required by later fixes).
- Mine: `confirm_governance.py`, `confirm_governance2.py`, `confirm_pytest_tiny.py`, `confirm_contracts.py`,
  `confirm_misc.py`, `confirm_v06.py`, `Y08_ci_replay_new_order.py`, `y01_pathspec_names.py`, `targeted_mutants.py`,
  `failfirst_4a396fb.sh`, and the Z-01..Z-05 scripts of §6.

Result key: **fixed** = the original attack and the close variants I tried are refused or detected; **partly fixed**
= the original attack is stopped but a close variant still works (the variant is a new defect in §6).

### 2.1 Third review, Y-01..Y-13

| Id | Original attack | Result | Evidence |
|---|---|---|---|
| Y-01 | report written over a modified tracked test file hides its change | **partly fixed** | `orig_y/Y01…py`: `220 passed`, `dirty: True, dirty_paths: ['tests/stage00/test_corrections.py']`, `check_test_report problems: ['TEST_EVIDENCE_DIRTY']`. Variants refused (`confirm_pytest_tiny.py`): untracked symlink report path to the tracked file, report path `./tests/../tests/test_b.py` → `TEST_EVIDENCE_DIRTY`; file names with `[`, `*`, `?`, space are recognised as tracked (`y01_pathspec_names.py`). **Not refused:** a tracked file whose name starts with `:` (pathspec magic) → Z-05 |
| Y-02 | edits hidden with `--skip-worktree` / `--assume-unchanged` | **partly fixed** | `orig_y/Y02…py`: `44 passed`, `dirty: True`, `TEST_EVIDENCE_DIRTY`; tiny project: both flags → `TEST_EVIDENCE_DIRTY`. **Not refused:** the same edits hidden from `git status` through git's stat cache (same size and mtime, `core.trustctime=false` in `.git/config`): 44 of 393 tests, `dirty: False`, `check-report` 0 problems → Z-01 |
| Y-03 | skipped / xfailed tests counted as a complete run | fixed | `orig_y/Y03…py`: `8 passed, 385 skipped`, `TEST_EVIDENCE_PARTIAL`. Variants (`confirm_pytest_tiny.py`): `xfail(strict=False)` on passing tests (`9 xpassed`), module-level `pytest.importorskip`, module-level `skipif` → all `TEST_EVIDENCE_PARTIAL` |
| Y-04 | `Stage: ٠٠` / `００` passes validation and does not block | fixed | `orig_y/Y04…py`: `RISK_INVALID_FIELD`; the error then blocks the sandbox's first transition (the script's assertion stops there: fail closed). Variants (`confirm_governance.py`): ids `R-٠٠٢`, `R-００٢`, `R-⁰⁰²` and `D-٠٠١` → `MEMORY_MALFORMED`; `Stage: 00, ٠٢` → `RISK_INVALID_FIELD`; `Stage: 02,00` (valid) blocks 00 |
| Y-05 | conflicting alternatives holding an absence of record, or agreeing values | fixed | `orig_y/Y05…py` (a): both `SCHEMA_VIOLATION` (enum). `confirm_contracts.py`: `retracted`/`retracted` → `CONFLICT_WITHOUT_DISAGREEMENT`; agreeing conflicting `retraction_date` → same; one alternative, missing provenance, `not_retracted` → `SCHEMA_VIOLATION`; control `retracted`/`correction` valid |
| Y-06 | hand-written enhancement on a verified stage covers owned drift | fixed | `orig_y/Y06…py`: `check errors: ['AMENDMENT_NOT_APPLICABLE', 'VERIFICATION_STALE']`, acceptance refused. Variants (`confirm_governance.py`): enhancement back-dated between verification and acceptance → `AMENDMENT_NOT_APPLICABLE`, `VERIFICATION_STALE`; an enhancement of an earlier acceptance no longer covers after reopen and re-acceptance (`VERIFICATION_STALE`) |
| Y-07 | reuse of the acceptance's reference with a chosen `--at` | fixed | `orig_y/Y07…py`: default time and same second → `OWNER_REF_REUSED`; back-dated → `AMENDMENT_NOT_APPLICABLE`. Variants: same reference as an earlier amendment in the same second, Stage 00 authorization reference → `OWNER_REF_REUSED` |
| Y-08 | a `pyproject.toml` mypy plugin rewrites the checker before the CI check | **partly fixed** | `Y08_ci_replay_new_order.py` (CI steps replayed in the new order): A, the original attack → the governance step runs first and fails (`exit 1`). **Not stopped:** code that `pyproject.toml` runs in `uv sync --locked`, which precedes the governance step: an in-tree build backend rewrites `cli.py`, and the governance step prints `0 errors` for a registry with 5 errors → Z-04. Documented residual, reproduced as stated in R-016: B, a mypy plugin that writes an untracked `src/sitecustomize.py` patching `check_test_report`, plus `-k` in `addopts`: every step green with `1 passed, 392 deselected`, `check-report` 0 problems, `git diff --exit-code` 0. C: a rewritten **and staged** tracked file passes `git diff --exit-code` (doc point D4) |
| Y-09 | an ignored file under an owned path counted as pinned gate evidence | fixed | `orig_y/Y09…py`: `GATE_EVIDENCE_UNPINNED`. Variants: untracked not-ignored file (`confirm_governance2.py`), a file committed only after the verified revision, a committed symlink under an owned path → `GATE_EVIDENCE_UNPINNED`; control (committed at the revision) allowed |
| Y-10 | CI record from another repository accepted | **partly fixed** | `orig_y/Y10…py`: `CI_WRONG_REPOSITORY`; `<repo>-fork` prefix → refused. **Not refused:** `https://github.com/<repo>/actions/runs/1/../../../../../other-owner/other-repo/actions/runs/2` (resolves to another repository's run) → allowed, `check` 0 errors → Z-02 |
| Y-11 | five more inputs end in a traceback | fixed | `orig_y/Y11…py`: A, B, C, D all named (`REJECTED`, `REGISTRY_SCHEMA`, `REGISTRY_UNREADABLE … nested too deeply`), no traceback. Variants (`confirm_governance2.py`): non-UTF-8 untracked name at the root with `recover`, `--json recover`, `check`, `status`; deep `--record`; deep, missing, outside-repository report and unknown stage for `check-report` → named, no traceback. Side effect of the fix: `recover` prints `Uncommitted changes: 0` when it cannot list them → Z-03 |
| Y-12 | verified retraction date next to `not_found_in_checked_sources` | fixed | `orig_y/Y05…py` (b): `SCHEMA_VIOLATION … not of type 'null'`. Variants: `uncertain` and `model_inference` dates with a value, a `conflicting` date → rejected; control `unavailable` null → valid |
| Y-13 | DOI with subdivided registrant code rejected | fixed | `10.1000.10/abc`, `10.1000.10.5/abc` valid; `10.1000./abc`, `10.1000..10/abc`, `10.1000.x/abc`, trailing newline → rejected |

### 2.2 Second review, X-01..X-13

| Id | Original attack | Result | Evidence |
|---|---|---|---|
| X-01 | gate evidence through `..` or a symlink inside an owned path | fixed | `orig_x/x_gate_owned_alias.py`: dotdot and symlink `REJECTED ['GATE_EVIDENCE_UNPINNED']`; committed symlink variant refused (`confirm_governance.py`) |
| X-02 | one `python_functions` line in `pyproject.toml` narrows the run | fixed | `confirm_pytest_tiny.py`: `2 passed`, `TEST_EVIDENCE_PARTIAL`. Variant `norecursedirs = ["tests"]` does not narrow (all 10 ran; accepted correctly) |
| X-03 | padding conftest, uncommitted conftest, `-p`, `PYTEST_PLUGINS` | fixed | all four → `TEST_EVIDENCE_PARTIAL` (`confirm_pytest_tiny.py`); variant git-ignored conftest → `TEST_EVIDENCE_PARTIAL` |
| X-04 | `src/sitecustomize.py` beside the package | fixed | `check`: `SRC_FOREIGN_MODULE`; CI guard `test "$(ls -A src)" = "citerift"` exit 1 (`confirm_governance.py`). A file created *after* the guard by later code is the R-016 residual (Y-08 B) |
| X-05 | 16 more inputs ending in a traceback | fixed | `orig_x/x_tracebacks.py`: all 17 cases named, exit 1 or 2 (`recover` exits 0 by design) |
| X-06 | bold / lowercase / indented fields under a missed heading; invisible characters | fixed | `orig_x/x_memory.py`: `MEMORY_MALFORMED` for all field forms; ZWSP and soft hyphen → `DECISION_CONTRADICTION`. Not seen, as documented (GOVERNANCE.md invariant 7): table row; also not folded and not claimed: Cyrillic homoglyph `sаndbox`, `sand.box` |
| X-07 | remove a dependency before authorization | fixed | `orig_x/x_history.py` B: authorizing Stage 02 after the edit is refused (schema error), the script's assertion stops there |
| X-08 | add, block, resolve in one second | fixed | `orig_x/x_same_second.py`: `resolve ALLOWED` |
| X-09 | `.git/info/grafts` honoured | fixed | `orig_x/x_graft.py`: `7 errors` with and without the graft file |
| X-10 | acceptance with an open blocker passes the replay | fixed | `orig_x/x_history.py` A and `x_history_a2.py`: `HISTORY_BLOCKER` |
| X-11 | `zh-classical` rejected | fixed | `orig_x/x_contracts.py`: 15 edition codes `VALID` |
| X-12 | repository test asserted today's state | fixed | `confirm_misc.py` prints the rewritten test: it asserts the authorization rule and that every acceptance was recorded by the owner |
| X-13 | enhancement changes a contract with reused reference and no version | fixed | `orig_x/x_enhancement.py`: `REJECTED … CONTRACT_VERSION_NOT_INCREASED … OWNER_REF_REUSED` |

### 2.3 First review, V-01..V-16

| Id | Original attack | Result | Evidence |
|---|---|---|---|
| V-01 | `-o python_files`, `-c other.ini`, dropping conftest, `collect_ignore` | fixed | `confirm_pytest_tiny.py`: all four `TEST_EVIDENCE_PARTIAL` |
| V-02 | URL-only gate; pinned file next to an unpinned one | fixed | `confirm_governance.py`: both `GATE_EVIDENCE_UNPINNED` |
| V-03 | stage overrides weaken the policy | fixed | `orig_x/x_v03.py`: `REGISTRY_SCHEMA` for all four edits |
| V-04 | entry point redirected to a shim | fixed (for entry points) | `confirm_misc.py`: shim in `[project.scripts]`, CI command `python -P -m citerift.governance.cli check` → `5 errors`, exit 1. Other `pyproject.toml` code paths: Z-04 / R-016 |
| V-05 | correction test report exempt from the manifest | fixed | `EVIDENCE_UNLISTED` |
| V-06 | en dash, U+2011, `_`, fullwidth R, setext, HTML headings; topic spellings | fixed | `confirm_v06.py`: every heading form `MEMORY_MALFORMED`; four topic spellings → `DECISION_CONTRADICTION` |
| V-07 | acceptance citing the amendment's reference (case 3) | fixed | `OWNER_REF_REUSED`. Cases 1 and 2 are allowed by design (invariant 2) |
| V-08 | second reopening with one amendment | fixed | `HISTORY_AMENDMENT_REUSED` |
| V-09 | duplicate amendment and blocker ids | fixed | `confirm_governance2.py`: `AMENDMENT_DUPLICATE_ID`, `BLOCKER_DUPLICATE_ID` |
| V-10 | schema deleted/truncated, `{}` registry, `0xff` in RISKS.md | fixed | `orig_x/x_v10_v12_orig.py`: all named, exit 1 |
| V-11 | default time before the last entry | fixed | `confirm_misc.py`: blocker after a +4 min entry opens at `…:32Z` ≥ `…:31Z`, `check` 0 errors |
| V-12 | nested `.gitattributes` | fixed | `ATTRIBUTES_NESTED` (same tree and fresh clone) |
| V-13 | `git replace` hides drift | fixed | `confirm_governance.py`: `VERIFICATION_STALE` before and after the replace; mutant M52 killed |
| V-14 | tests read JSON last-key-wins | fixed | `confirm_misc.py`: ruleset and fixtures read with `loads_strict`; remaining `json.loads` only parse node output and the canonical-form check |
| V-15 | rules without a test of their own | fixed (targeted) | `targeted_mutants.py`: see §2.5 |
| V-16 | report into a missing directory crashes | fixed | `confirm_pytest_tiny.py`: report written to `new/dir/report.json` |

### 2.4 Audit findings F-01..F-19 (where a test exists)

The regression tests `test_f01_*` … `test_f19_*` all pass in the 393-test run. In addition:

| Id | Result | Evidence |
|---|---|---|
| F-01 | fixed | `confirm_misc.py`: merge commit restoring pre-verification owned content → `VERIFICATION_STALE` |
| F-02 / F-03 | fixed | `run_audit_scripts.sh`: `gate_dot` 32 errors (`GATE_EVIDENCE_MISSING`, `…UNPINNED`); `drop_ci`, `shrink_gates` → `REGISTRY_SCHEMA`; `drop_owned_paths` → `DEFINITION_CHANGED`, `DEFINITION_WEAK`; `single_active_flip.py` → `REGISTRY_SCHEMA` |
| F-04 | fixed | `mutate.py two_active` → `HISTORY_SINGLE_ACTIVE`; `past_violation` → `HISTORY_DEPENDENCY`, `HISTORY_SINGLE_ACTIVE` |
| F-05 | fixed | `reopen_without_amendment` → `HISTORY_AMENDMENT_MISSING`; `inprogress_with_open_blocker` → `HISTORY_BLOCKER` |
| F-06 | fixed | V-06 and X-06 rows; mutant M26 killed |
| F-07 | fixed | path argument subset → `TEST_EVIDENCE_PARTIAL` |
| F-08 / F-09 / F-10 | fixed | `contracts_probe.py`: every case INVALID except the chronological control (C, VALID); `confirm_contracts.py`: `2023-02-29` `INVALID_DATE`, `2024-02-29` valid |
| F-11 | fixed | `reopen_liveness_adapted.py`: reopening 00 while 02 is accepted `ALLOWED` with warning `DEPENDENCY_REOPENED` |
| F-12 | fixed | CRLF clone (`core.autocrlf=true`) of an accepted sandbox: `0 errors` |
| F-13 | fixed | V-10 row |
| F-14 | fixed | report outside the repository written (`confirm_pytest_tiny.py`) |
| F-15 | fixed (by its test only) | `test_f15_blocker_resolution_records_who_resolved_it` passes; not probed separately |
| F-16 | fixed | `--at 2030-…` → `TIMESTAMP_IN_FUTURE` |
| F-17 | fixed | `acceptance_before_history` → `RECORD_HISTORY_MISMATCH`; V-07 row |
| F-18 | fixed | duplicate key in the registry → `REGISTRY_UNREADABLE … duplicate JSON key` |
| F-19 | fixed | uncommitted owned change → warning `UNCOMMITTED_OWNED_CHANGE` |

### 2.5 Mutants and fail-first

- `targeted_mutants.py` applied the mutants of `mutation/mutation_check.py` for M26, M35, M37, M52, M57–M59 and
  M74–M90 (the Y fixes) in `$W/sandbox-mut`, each against `test_corrections.py`, `test_contracts.py` and
  `test_unit_model_evidence_memory.py` with `-x` (a mutant killed by that subset is killed by the full suite;
  survivors would have been re-run on the full suite). Result: all 24 KILLED by the subset, each by the test written for its rule (for example M74 by `test_y01_…`, M85 by `test_y07_…`, M90 by
  `test_multilingual_and_precise_values_accepted`); the sandbox tree was clean afterwards. The first run hit the
  30-minute background limit after M87 and was stopped (the half-applied M88 file in the sandbox was restored with
  `git checkout`); M88–M90 were then run again on their own (`$W/out/targeted_mutants.txt`,
  `$W/out/targeted_mutants_part2.txt`). The full 90-mutant check was not run
  (about 2 to 3 hours here).
- `failfirst_4a396fb.sh` re-ran the fail-first procedure (tests of `97b2051`, code of `4a396fb`): `27 failed, 366 passed in 264.17s`,
  and the 27 failing test ids are exactly those in `fail-first/results-4a396fb.txt` (`diff` of the sorted lists is
  empty; `$W/out/failfirst_4a396fb.txt`).

**Count.** Of the 61 earlier findings checked (V-01..V-16, X-01..X-13, Y-01..Y-13, F-01..F-19): **57 fixed, 4
partly fixed (Y-01, Y-02, Y-08, Y-10), 0 not fixed.** For all four partly fixed findings the original reproduction
no longer works; a close variant does.

## 3 Regressions

| Check | Result | Evidence |
|---|---|---|
| Correction amendment and reopening in the same second, one owner statement (CLI, `--at` equal) | works: `Recorded amendment A-00-001`, `Transition … IN_PROGRESS: ALLOWED`, `check` 0 errors | `confirm_governance2.py` |
| Legitimate enhancement on an accepted stage (CLI `amend`, new statement, report at the new revision) | covers its change: `VERIFICATION_STALE` before, 0 errors after | `confirm_governance2.py` |
| Enhancement recorded in the acceptance's own second with a new statement | accepted, 0 errors (the Y-06 same-second rule works both ways) | `confirm_governance2.py` |
| Honest complete test run | accepted: CI replay `393 passed`, `check-report` `0 problems`, `dirty: False`, `complete: True`; tiny project control `ACCEPTED` | `ci_replay_honest.sh`, `confirm_pytest_tiny.py` |
| CI workflow new steps vs what the tests write | consistent: after the full run the only new file is the untracked `ci-test-report.json`; `git diff --exit-code` exit 0; no tracked file is rewritten by the suite | `ci_replay_honest.sh` (all 11 local steps exit 0; `uv lock --check` and `pip-audit` need the network and were not run) |
| Real repository `check` and `render-status --check` | clean in `$W/base` and in `review4-tree` | §1 |
| Reopening a foundation stage after a dependent was accepted (F-11) | still allowed with a warning | `reopen_liveness_adapted.py` |
| X-08 same-second blocker flow | still allowed | `orig_x/x_same_second.py` |

No regression found. One observation on the Y-03 fix: a local run without `node` skips the two ECMA-262 tests, and a
skipped test now makes the report partial, so honest local verification evidence needs `node` (fail closed; not
claimed otherwise; SPECIFICATION.md:192-194 says the test is skipped locally without `node`).

## 4 Documentation accuracy

Each line is a claim I found false or overstated, with the evidence. Substantive: D1–D6. Cosmetic: D7.

| # | Location | Claim | Evidence |
|---|---|---|---|
| D1 | RISK_ANALYSIS.md:47; GOVERNANCE.md:47-52 ("a passing test report produced at the verified revision from a clean tree"); R-004 (RISKS.md:93-95) does not list the gap | "A dirty tree includes files hidden from `git status`"; the report is produced at the verified revision | Z-01: edits hidden from `git status` by git's stat cache (`core.trustctime=false`, same size and mtime) give `dirty: False` and an accepted report for 44 of 393 tests, at content that is not the verified revision |
| D2 | GOVERNANCE.md:49; RISKS.md:80-81 (R-004); RISK_ANALYSIS.md:47, :162; SPECIFICATION.md:102-103; CHANGELOG.md:95; review/README.md (Y-10 row) | the CI record must name / names "a run of this repository" | Z-02: a `run_url` that starts with the repository prefix and leaves it with `..` segments is accepted. MATHEMATICAL_MODEL.md §6 states the actual rule (a prefix test) correctly |
| D3 | GOVERNANCE.md:208-211 and :213-216; RISKS.md:248, :252-254 (R-016); RISK_ANALYSIS.md:48, :163; `.github/workflows/ci.yml:62-63` (comment "Runs before any tool that pyproject.toml configures"); review/README.md (Y-08 row) | the governance check runs before the code that `pyproject.toml` can configure; code from tool settings "executes in the steps after the governance check" | Z-04: `[build-system]` in `pyproject.toml` runs code during `uv sync --locked`, before the governance step; the governance step printed `0 errors` for 5 errors |
| D4 | GOVERNANCE.md:211-213; RISKS.md:249; CHANGELOG.md:92-93; RISK_ANALYSIS.md:48, :134 | CI "fails if any tracked file was changed" / "a changed tracked file fails CI" | `git diff --exit-code` compares the work tree with the index only: a rewritten tracked file that was staged passes (Y-08 replay, case C: `exit 0`, `M  src/citerift/governance/evidence.py`). Untracked files (case B: `src/sitecustomize.py`) are not seen either. R-016 does say later code can change what the tree-check step does, so this is an overstatement of the short claims rather than a hidden risk |
| D5 | RISK_ANALYSIS.md:180-182 (§5) | "The workflow changed only to run the owned sources with `python -P -m` …, to assert where the package was imported from, and to refuse anything in `src/`" | Since `741476c` the workflow also moved the governance step before static analysis and added the `check-report` and `git diff --exit-code` steps (`git diff 741476c 97b2051 -- .github/workflows/ci.yml`) |
| D6 | RISKS.md:94-95 (R-004); SPECIFICATION.md:94-95; MATHEMATICAL_MODEL.md:174-175; CHANGELOG.md:80-82 | a report written over a tracked file makes the tree dirty | Z-05: not for a tracked file whose name starts with `:`; `dirty: False`, report accepted |
| D7 | SPECIFICATION.md:85-104 | numbered list runs 4, 6, 5 | cosmetic |

Claims I checked and found accurate (selection): GOVERNANCE.md invariants 2, 3, 5, 6, 7 and "Changing an accepted
stage" against the probes of §2; the Y-03, Y-04, Y-06, Y-07, Y-09, Y-11 statements in RISKS.md R-003 and
SPECIFICATION.md rules 5, 8, 9, 13; data-contracts.md:19-25, :32-50, :63-71, :87-89, :97-101 (three valid fixtures,
52 invalid cases, 1.0.0 fixtures of `ae2ce9e` and `741476c` still valid under 1.0.1: `confirm_contracts.py`);
CREATIVE_DIFFERENTIATION_REVIEW.md (52 invalid cases, 90 mutants named, the bounded wording "cannot rule out a form
nobody has thought of yet"); fail-first/README.md (27 failed, 366 passed; per-finding counts sum to 27); the
review/README.md statement that the third reviewer's scripts no longer reproduce Y-01..Y-07 and Y-09..Y-13 (true at
`97b2051` too); SIMULATION_REPORT.md hashes. Not checkable offline: GOVERNANCE.md:198 ("active on GitHub").

Identity (docs/identity.md rules 2-4; `identity_scan.py`, terms read from the environment only): `<name terms>`
outside the repository account login: not found. Trademark marks: found only at docs/identity.md:44 (the rule itself)
and in the scanner's own pattern (review/4a396fb/scripts/identity_scan.py:30). AI tool presented as creator or owner:
not found. Commits `aa06a40`, `a93c64f`, `97b2051` carry the `Assisted-by: Claude Code (AI coding agent)` trailer and
no `Co-Authored-By` / `Claude-Session` line. The term list was derived from the account login and the session's
account context, so the scan cannot prove the absence of every form of a legal name.

## 5 Residual risks: are they stated honestly?

| Risk | Prevented | Only detected | Not enforceable | Assessment |
|---|---|---|---|---|
| R-001 shared GitHub identity | nothing | nothing | identity separation | Honest. |
| R-002 owner references | owner edges without a reference (CLI); acceptance and amendment reference reuse (CLI) | the same rules on hand edits | the content of a reference | Honest. Reuse is compared as exact strings (O-3 of the third review), so the rules bind honest writers. R-002 itself mentions only the acceptance rule; the amendment rule is in R-003 and SPECIFICATION.md. |
| R-003 hand edits | nothing | the listed rules; every hand edit I tried that the tool would refuse was reported (Y-06, Y-07, V-09, X-07, F-03..F-05, F-17) | consistent forgery | Honest as far as tested. |
| R-004 test report and CI record | narrowing an honest run can show | the same, by `check` | code inside the test process | **Understated.** The rule "dirty when `git status` shows a change, or a flag, or a report over a tracked file" is stated accurately, but R-004 does not say that local git state can make `git status` blind to an edit with no flag (Z-01) or that `:` names escape the tracked-file test (Z-05); "names a run of this repository" is a prefix test (Z-02). |
| R-016 CI gate editable | the `src/` guard at the start of the job; the step order against tool settings used by ruff, mypy and pytest | owned-path drift for the workflow and ruleset | CI independence | **Partly overstated.** The general residual (later steps can be changed, files restored) is stated honestly and reproduced as stated (Y-08 replay B: CI green with 1 of 393 tests). Overstated: that such code runs only after the governance check (Z-04: the build backend runs in `uv sync --locked`, before it) and that CI fails on any tracked change (D4). |

## 6 New defects (Z-01..)

Reproduced: 1 low-medium, 4 low; none critical. Z-01, Z-02, Z-04 and Z-05 are close variants of Y-02, Y-10, Y-08
and Y-01 (they are why those four are "partly fixed"); Z-03 is a side effect of the Y-11 fix. They are counted once,
here.

| Id | Severity | File:line | Description | Reproduction | Expected vs actual |
|---|---|---|---|---|---|
| Z-01 | low-medium | src/citerift/governance/gitutil.py:137-160 (`dirty_paths` trusts `git status` and the `ls-files -v` flags); pytest_report.py:85 | Variant of Y-02. `git status` decides from the index's stat cache. Keep each edited test file's size (rename `def test_` to `def xest_`) and restore its mtime, set `core.trustctime=false` in `.git/config` (local, not committed), and `git status` shows nothing; no file is flagged. Deliberate, like the original. | `W=$W $W/base/.venv/bin/python $W/scripts/Z01_statcache_hides_edits_real.py` (~1 min); tiny version in `confirm_pytest_tiny.py` and `z_trustctime_tiny.py` | Expected `TEST_EVIDENCE_DIRTY` (content differs from HEAD in 11 of 11 test files). Actual: `44 passed`, `revision=97b2051…`, `dirty: False`, `complete: True`, `check_test_report problems: []`, `citerift-gov check-report … 0 problems`. A content comparison (for example `git -c core.trustctime=true -c core.checkStat=default update-index --really-refresh` before `git status`, or `git diff --quiet HEAD` after a forced refresh) would catch it. |
| Z-02 | low | src/citerift/governance/orchestrator.py:820 (prefix test); schemas/governance/stage_registry.schema.json:228 (`[^\s…]+` allows `..`) | Variant of Y-10. `https://github.com/<repo>/actions/runs/1/../../../../../other-owner/other-repo/actions/runs/2` starts with the required prefix and passes the schema; by RFC 3986 dot-segment removal it is a run of `other-owner/other-repo`. | `W=$W $W/base/.venv/bin/python $W/scripts/Z02_ci_url_dot_segments.py` | Expected `CI_WRONG_REPOSITORY`. Actual: verification allowed, `check` 0 errors (control with the plain other URL: `CI_WRONG_REPOSITORY`). |
| Z-03 | low | src/citerift/governance/cli.py:223 (`len(data['uncommitted_changes'] or [])`); orchestrator.py `recover` | Side effect of the Y-11 fix. With a damaged index `recover` cannot list uncommitted changes (`uncommitted_changes: null` in `--json`), but the text report says `Uncommitted changes: 0`. `recover` is the first command of every session (CLAUDE.md). The error line further down names the damage. | `W=$W $W/base/.venv/bin/python $W/scripts/Z03_recover_unknown_changes_as_zero.py` | Expected `Uncommitted changes: unknown (…)` (as `_git_hint`, cli.py:360, already prints). Actual: `Uncommitted changes: 0` with an untracked file present (intact index: `1`). |
| Z-04 | low | .github/workflows/ci.yml:54 (`uv sync --locked`) before :61-66 (governance step); pyproject.toml `[build-system]` (not owned) | Variant of Y-08. The step order protects the check from tool settings used by ruff, mypy and pytest, but `uv sync --locked` builds the project with the backend `pyproject.toml` names. An in-tree backend (`backend-path = ["."]`, a committed root file, no network, `uv sync --locked` still passes) rewrites `src/citerift/governance/cli.py` before the governance step. At the end `git diff --exit-code` would see the change unless it is restored or staged, and the suite's own real-repository test would fail unless the test step is also changed, which is the R-016 residual. | `W=$W $W/base/.venv/bin/python $W/scripts/Z04_build_backend_before_check.py` | Expected the honest `5 errors`, exit 1 at the governance step. Actual: guard 0, `uv sync --locked --offline` 0, package-from-checkout 0, governance step `Consistency check: 0 errors, 0 warnings`, exit 0; `git status`: `M src/citerift/governance/cli.py`. Not reproduced, inference only: a locked dependency's `.pth` file would also run inside the governance step. |
| Z-05 | low | src/citerift/governance/gitutil.py:163-165 (`ls-files --error-unmatch -- PATH` reads PATH as a pathspec); pytest_report.py:82 | Edge variant of Y-01. A tracked file whose name starts with `:` is reported untracked (pathspec magic), so the report path is left out of the dirty check. Tiny project whose tests are parametrized from a tracked `:cases.json`: cut it to one case, write the report over it, restore it. Needs such a file to be committed first (visible in review). | `W=$W $W/base/.venv/bin/python -I $W/scripts/Z05_colon_name_report_path.py`; function level: `y01_pathspec_names.py` | Expected `TEST_EVIDENCE_DIRTY`. Actual: `1 passed` (of 8), `dirty: False`, `dirty_paths: []`, `complete: True`, `check_test_report problems: []`. `GIT_LITERAL_PATHSPECS=1` or `:(literal)` would fix it. |

Observations, not counted: the Cyrillic-homoglyph and `sand.box` topic spellings are not folded (nothing claims
they are); `recover` exits 0 on errors by design; Arabic topic folding (O-1) now works for tatweel, fatha, shadda
and U+0670 (`confirm_misc.py`).

## 7 Verdict

All 61 earlier findings that I checked have their original reproduction stopped; 57 are fixed with every close variant
I tried, and 4 (Y-01, Y-02, Y-08, Y-10) are only partly fixed, because a close variant still works (Z-05, Z-01, Z-04,
Z-02). No regression was found. Five new defects were reproduced (1 low-medium, 4 low, none critical), and six
substantive documentation claims are false or overstated (D1–D6), plus one cosmetic error.

NOT VERIFIED
