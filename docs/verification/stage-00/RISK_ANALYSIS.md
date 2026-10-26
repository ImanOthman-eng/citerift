# Stage 00 Risk Analysis and Adversarial Review (correction A-00-001)

The live register is `RISKS.md`. This document covers four things:

- how each Stage 00 control works: whether it **prevents** the action,
  only **detects** it, or **cannot** address it
- the adversarial review of the corrected code
- the residual exposure

The accepted analysis is kept in `superseded/741476c/RISK_ANALYSIS.md`. The
independent review in `docs/audits/stage-00-2026-10-25/` found that version
overstated enforcement (F-21). The tables below replace its claims.

## 1. Threat model

Asset: the integrity of the stage record. A stage is verified only with real
evidence, accepted only by the owner, and no later stage starts without the
owner's authorization.

Adversaries:

- **A1, careless or over-eager agent.** This is the likeliest case. It skips a
  step, reuses stale evidence, or treats its own report as approval.
- **A2, dishonest writer with write access.** It edits the registry, evidence
  or workflow by hand. That includes a writer able to rewrite everything
  consistently.
- **A3, external input.** Pull request content, workflow triggers,
  dependencies.

Verified fact that shapes the analysis: the agent's GitHub token acts as the
owner's account `ImanOthman-eng` (R-001). GitHub identity therefore cannot
separate the owner from the agent.

## 2. Prevent, detect, or not enforceable

"Prevents" means the tool refuses to write the change. That binds only writers
who use `citerift-gov`. "Detects" means `citerift-gov check` reports it. CI
runs `check` on every push and pull request, and so can anyone with an honest
copy of the code. Detection does not stop a commit.

| Threat | Prevented by | Detected by | Not enforceable by repository code |
|---|---|---|---|
| R-001 agent acts as the owner on GitHub | nothing in the repository | nothing: GitHub shows one account | separating the identities; needs D-006 (owner signature) or a bot identity |
| R-002 owner reference that does not contain approval | `OWNER_REF_REQUIRED` refuses owner edges without a reference; `OWNER_REF_REUSED` refuses an acceptance citing a reference used before the verification by a history entry or an amendment, and an amendment citing a reference cited at or before its own time (F-17, V-07, X-13, Y-07) | `HISTORY_OWNER_REF_MISSING`, `OWNER_REF_REUSED`, `RECORD_HISTORY_MISMATCH` on hand edits | whether the cited message says what is claimed; the owner reads it |
| Owner authorization skipped (agent authorizes, accepts, withdraws or reopens) | `OWNER_DECISION_REQUIRED`; owner edges require an `owner_ref`; reopening requires a correction amendment not used by an earlier reopening; acceptance requires no open blocker | replay of every history entry: `HISTORY_ACTOR`, `HISTORY_AMENDMENT_MISSING`, `HISTORY_AMENDMENT_REUSED`, `HISTORY_BLOCKER`, `HISTORY_DEPENDENCY`, `HISTORY_SINGLE_ACTIVE` (F-04, F-05, V-08, X-10) | `--actor owner` is a flag the agent can pass; the reference is the only control (R-002) |
| R-003 registry hand edit | none (any writer can edit the file) | schema, including fixed policy values, artifact list, executor, dependencies and `ci_required`; per-entry replay; record/history match; definition hash; duplicate keys and duplicate amendment or blocker ids; future times; amendments dated when the stage was not accepted; non-ASCII digits in memory ids and stages (F-03 to F-05, F-16 to F-18, V-03, V-09, X-07, Y-04, Y-06) | a forgery that is consistent everywhere: history, records, evidence and hashes rewritten together |
| Forged or stale evidence | verification refuses missing, trivial, unpinned, stale, malformed or partial evidence. Partial includes a run narrowed by ini override, other ini file, changed collection settings, a conftest that drops or repeats tests, an uncommitted conftest, a `-p` or `PYTEST_PLUGINS` plugin, skipped or expected-to-fail tests, and a run missing a committed test file. A dirty tree includes tracked files flagged so that `git status` hides them, tracked files whose bytes differ from the index although the stat cache says they do not, and a report written over a tracked file of any name. The CI record URL must be exactly a run URL of this repository (F-02, F-07, V-01, V-02, X-02, X-03, X-05, Y-01 to Y-03, Y-10, Z-01, Z-02, Z-05) | `EVIDENCE_STALE`, `EVIDENCE_MISSING`, `EVIDENCE_UNLISTED` over every file in the verification directory; `GATE_EVIDENCE_UNPINNED` (a URL, a path through `..` or a symbolic link, or an owned file not committed at the verified revision, is not pinned, Y-09); owned-path content compared with the verified revision, with replace refs and grafts ignored (F-01, V-13, X-01, X-09); nested `.gitattributes` (V-12) | who produced a test report or CI record (R-004): they are self-reported files whose content and hashes are checked; code inside the test process (committed tests, conftests, untracked or ignored imported modules, dependencies) can write a false report, and a writer can edit a report after the run |
| CI trust (R-004, R-016) | ruleset 25824038 requires `ci-gate` and merge commits, and refuses force-push and deletion; CI runs the owned sources with `python -P -m`, not entry points that `pyproject.toml` defines, and asserts the package comes from `src` (V-04); a shell step refuses anything in `src/` beside the `citerift` package before any Python runs (X-04); before the governance check CI installs only the locked dependencies as wheels, without building the project; the check runs before the lock check, the project install, ruff, mypy and pytest, which `pyproject.toml` configures (Y-08, Z-04) | a change to `.github/workflows`, `.github/rulesets` or `.gitattributes` makes Stage 00 `VERIFICATION_STALE` (F-20 detection); `SRC_FOREIGN_MODULE` for a tracked module beside the package; after the tests CI checks its own report and fails if `git status` shows an unstaged or staged change or a new file other than the report (Y-08, O-6, D4) | CI independent of the change it gates: the gated pull request can edit the workflow, and 0 approvals are needed; `pyproject.toml` and `uv.lock` are not owned: code in a locked wheel (a `.pth` file) runs during the governance check, and the build backend or a tool setting can run code in the steps after it (and restore what it changed) without being detected as Stage 00 drift |
| Enhancement that changes an accepted contract | an enhancement amendment needs an owner reference not cited before and an accepted stage (X-13, Y-06, Y-07) | `CONTRACT_VERSION_NOT_INCREASED`; `CONTRACT_INCOMPATIBLE` when an accepted valid fixture no longer validates (X-13) | whether the change keeps the contract's meaning; an enhancement has no CI record of its own |
| Uncommitted local changes | none | `UNCOMMITTED_OWNED_CHANGE` (warning, F-19); the test report records a dirty tree | changes never committed are invisible to CI |

## 3. Adversarial review

Each attack was run against the corrected code in a sandbox repository by the
named test. The test passes only if the attack is refused or detected. The 20
attacks of the accepted review (`superseded/741476c/RISK_ANALYSIS.md` §2)
still pass. The new attacks below are the audit's bypasses and their variants.

| # | Attack | Outcome now | At `ae2ce9e` | Test |
|---|---|---|---|---|
| 21 | Merge an old branch that restores pre-verification owned content (TREESAME merge) | `VERIFICATION_STALE` | not detected | `test_f01_*` |
| 22 | Edit a gate evidence file, cite `.` as evidence, or add a file to the evidence directory after verification | `EVIDENCE_STALE`, `GATE_EVIDENCE_MISSING` or `GATE_EVIDENCE_UNPINNED`, `EVIDENCE_UNLISTED` | not detected | `test_f02_*` |
| 23 | Turn off `single_active`, drop artifacts or handoff sections, set `ci_required: false`, remove gates, suites or owned paths | `REGISTRY_SCHEMA` before verification, `DEFINITION_CHANGED` after, `DEFINITION_WEAK` at verify | 0 errors | `test_f03_*` |
| 24 | History in which two stages were active, or a stage was authorized before its dependency was accepted, later repaired | `HISTORY_SINGLE_ACTIVE`, `HISTORY_DEPENDENCY` | not detected | `test_f04_*`, replay conformance |
| 25 | Reopen without a correction amendment; start or verify with an open blocker; block with no blocker | `HISTORY_AMENDMENT_MISSING`, `HISTORY_BLOCKER` | not detected | `test_f05_*` |
| 26 | Malformed `RISKS.md` heading on a critical defect; `Stage: project` critical defect; topic differing only in case | `MEMORY_MALFORMED`, `OPEN_CRITICAL_DEFECT`, `DECISION_CONTRADICTION` | ignored | `test_f06_*` |
| 27 | Verify with a report from `-k`, `-m`, a node id, `--deselect`, `--lf`, or a subset path | `TEST_EVIDENCE_PARTIAL` | accepted (8 of 161 tests sufficed) | `test_f07_*` |
| 28 | Store "not retracted" or a boolean as a conflicting alternative; store model output as `uncertain` | `SCHEMA_VIOLATION` | accepted | `test_contracts.py` invalid cases |
| 29 | Strings that Python and JavaScript validators read differently (trailing newline, `\S` versus Unicode spaces) | rejected by both; 0 differences against Node on all patterns and on seeded random strings | 2 engines disagreed | `test_schema_patterns_agree_with_ecma262*` |
| 30 | Accepted dependent blocks the correction of its foundation | allowed, with `DEPENDENCY_REOPENED` as a warning | permanent error | `test_f11_*`, `test_differential_fixed_case_*` |
| 31 | CRLF checkout | hashes stable (`.gitattributes`) | 8 false `EVIDENCE_STALE` | `test_f12_*` |
| 32 | Truncated, empty or BOM-prefixed registry | `REGISTRY_UNREADABLE`, exit 1, no traceback | traceback | `test_f13_*`, `test_failure_simulation.py` |
| 33 | Future timestamp to block correct clocks | refused at write; `HISTORY_FUTURE_TIMESTAMP` at check | accepted | `test_f16_*` |
| 34 | Reuse the authorization reference for the acceptance; record time not equal to its history entry | `OWNER_REF_REUSED`, `RECORD_HISTORY_MISMATCH` | accepted | `test_f17_*` |
| 35 | Duplicate JSON key showing a reviewer one value and the checker another | `REGISTRY_UNREADABLE` / `UNREADABLE` | last value silently won | `test_f18_*`, `test_duplicate_json_keys_rejected` |
| 36 | Weaken the workflow, the ruleset file or `.gitattributes` after verification | `VERIFICATION_STALE` (detection only) | not detected | `test_f20_*` |
| 37 | Byte-code cache in the evidence directory pinned at verification, so every clone reports missing evidence (found during this correction, S-01) | ignored files left out of the manifest; a non-ignored added file is still `EVIDENCE_UNLISTED` | false errors | `test_s01_*` |

Attacks 38 to 50 are the bypasses found by the first final independent review
(`review/ee46423/`, V-01 to V-16). The column "At `135e4ac`" is the revision
before their fixes.

| # | Attack | Outcome now | At `135e4ac` | Test |
|---|---|---|---|---|
| 38 | Narrow the run with `-o python_files=...`, `-o testpaths=...`, `-c other.ini`, a conftest that drops items, or `collect_ignore` | `TEST_EVIDENCE_PARTIAL` | recorded as complete | `test_v01_*` |
| 39 | Cite only a URL, or one pinned file next to unpinned ones, as gate evidence | `GATE_EVIDENCE_UNPINNED` | accepted | `test_f02_*[url_only]`, `[pinned_plus_unpinned]` |
| 40 | Override a stage's artifact list with a shorter one, drop the handoff, or set Stage 01 to `engineering-agent` | `REGISTRY_SCHEMA`; handoff always required | accepted | `test_v03_*` |
| 41 | Point the `citerift-gov` entry point in `pyproject.toml` at a shim that prints a clean result | CI no longer uses the entry point; guard step fails if the package is not from `src` | CI passed | `test_ci_runs_the_owned_sources_not_an_entry_point` |
| 42 | List an arbitrary file as a correction amendment's test report to exempt it from the manifest | `EVIDENCE_UNLISTED`; the report itself is hash-checked | exempt | `test_v05_*` |
| 43 | Write a RISKS.md entry with an en dash or non-breaking hyphen in the id, a setext or HTML heading, or a topic spelled with spaces or full-width letters | `MEMORY_MALFORMED`, `DECISION_CONTRADICTION` | ignored | `test_v06_*` |
| 44 | Accept citing the amendment's owner reference | `OWNER_REF_REUSED` | accepted | `test_v07_*` |
| 45 | Reopen twice with one correction amendment | `HISTORY_AMENDMENT_REUSED` | accepted | `test_v08_*` |
| 46 | Two amendments or two blockers with the same id, so replay and `propose` read different records | `AMENDMENT_DUPLICATE_ID`, `BLOCKER_DUPLICATE_ID` | accepted | `test_v09_*` |
| 47 | Delete or truncate the schema, write `{}` as the registry, or put a non-UTF-8 byte in RISKS.md | named error, exit 1 | traceback | `test_v10_*` |
| 48 | Add a blocker on a correct clock right after a forward-dated entry | default time follows the last entry | `HISTORY_BLOCKER` on a correct history | `test_v11_*`, `test_v15_*` |
| 49 | Commit a nested `.gitattributes` that changes line endings of evidence | `ATTRIBUTES_NESTED` | false `EVIDENCE_STALE` in fresh clones | `test_v12_*` |
| 50 | Hide owned-path drift with `git replace` | `VERIFICATION_STALE` | 0 errors | `test_v13_*` |

V-14 (tests reading JSON last-key-wins) and V-16 (report into a missing
directory) are test and robustness defects, not attacks. Both are fixed
(`review/README.md`).

Attacks 51 to 61 are the bypasses found by the second final independent
review (`review/9e025c9/`, X-01 to X-14). The column "At `7138d6d`" is the
revision before their fixes.

| # | Attack | Outcome now | At `7138d6d` | Test |
|---|---|---|---|---|
| 51 | Cite gate evidence as `docs/../src/x` or through a symbolic link inside an owned path | `GATE_EVIDENCE_UNPINNED` | accepted | `test_x01_*` |
| 52 | Commit `python_functions = test_[a-m]*` in `pyproject.toml` so 92 of 308 tests run | `TEST_EVIDENCE_PARTIAL` | complete | `test_x02_*` |
| 53 | A conftest that removes tests and pads the list with repeats; the same as an uncommitted conftest, a `-p` plugin or `PYTEST_PLUGINS` | `TEST_EVIDENCE_PARTIAL` | complete with 21 of 308 tests | `test_x03_*` |
| 54 | Commit `src/sitecustomize.py` that changes the checker's output inside every CI step | CI step fails before Python runs; `SRC_FOREIGN_MODULE` | CI passed | `test_ci_refuses_modules_beside_the_package_before_running_python`, `test_x04_*` |
| 55 | 17 malformed inputs (counts as strings, a list as `--record`, a symlinked schema, an unknown stage, undecodable HANDOFF) | named error, exit 1 or 2 | traceback | `test_x05_*` |
| 56 | Write a critical defect's fields as `- **Status**: open`, `- status: open` or indented, under a heading the parser misses; split a topic with a zero-width character | `MEMORY_MALFORMED`, `DECISION_CONTRADICTION` | ignored | `test_x06_*` |
| 57 | Remove Stage 01 from Stage 02's `depends_on` before authorizing it | `REGISTRY_SCHEMA` | Stage 02 accepted without Stage 01 | `test_x07_*` |
| 58 | Add, block and resolve a blocker within one second | allowed | refused, labelled pre-existing | `test_x08_*` |
| 59 | Hide owned-path drift with `.git/info/grafts` | `VERIFICATION_STALE` | 0 errors | `test_x09_*` |
| 60 | Accept a stage while a blocker is open | `HISTORY_BLOCKER` | accepted by the replay and the model | `test_x10_*`, replay conformance |
| 61 | Change an accepted contract through an enhancement amendment with a reused owner reference and no version change | `OWNER_REF_REUSED`, `CONTRACT_VERSION_NOT_INCREASED`, `CONTRACT_INCOMPATIBLE` | accepted | `test_x13_*` |

Attacks 62 to 72 are the bypasses found by the third final independent review
(`review/4a396fb/`, Y-01 to Y-13). The column "At `4a396fb`" is the revision
before their fixes.

| # | Attack | Outcome now | At `4a396fb` | Test |
|---|---|---|---|---|
| 62 | Narrow a tracked test file and write the report over it, then restore the file | `TEST_EVIDENCE_DIRTY` | clean, complete (214 of 363 tests) | `test_y01_*` |
| 63 | Hide narrowed test files with `git update-index --skip-worktree` or `--assume-unchanged` | `TEST_EVIDENCE_DIRTY` | clean, complete (44 of 363 tests) | `test_y02_*` |
| 64 | A committed conftest that skips or xfails all but a few tests | `TEST_EVIDENCE_PARTIAL` | complete (8 passed, 355 skipped) | `test_y03_*` |
| 65 | Write an open critical defect's `Stage` in Arabic-Indic or fullwidth digits; duplicate an id in other digits | `RISK_INVALID_FIELD`, `MEMORY_MALFORMED`; verification refused | valid; Stage 00 verified and accepted | `test_y04_*` |
| 66 | Store an absence of record as one side of a retraction conflict, or a conflict whose values agree | `SCHEMA_VIOLATION` (`enum`), `CONFLICT_WITHOUT_DISAGREEMENT` | valid | invalid cases `retraction_conflict_*`, `title_conflict_whose_values_agree` |
| 67 | Hand-write an enhancement amendment on a verified, not accepted, stage to cover owned changes | `AMENDMENT_NOT_APPLICABLE`, `VERIFICATION_STALE` | 0 errors; acceptance allowed | `test_y06_*` |
| 68 | Reuse the acceptance's owner reference in an amendment dated the same second, or back-dated before the acceptance | `OWNER_REF_REUSED`, `AMENDMENT_NOT_APPLICABLE` | 0 errors | `test_y07_*` |
| 69 | A mypy plugin named in `pyproject.toml` rewrites the checker before the CI check step | the check now runs before mypy; a changed tracked file fails CI | CI check printed 0 errors for 5 | `test_y_ci_checks_its_own_report_*` |
| 70 | Cite a git-ignored file under an owned path as gate evidence, then rewrite it | `GATE_EVIDENCE_UNPINNED` | verification allowed | `test_y09_*` |
| 71 | Record another repository's successful run as the CI record | `CI_WRONG_REPOSITORY` | accepted | `test_y10_*` |
| 72 | A non-UTF-8 evidence file name, a damaged index, an absolute `verification_dir`, deeply nested JSON | named errors | traceback | `test_y11_*` |
| 73 | Edit test files keeping size and mtime, with a local `core.trustctime=false` | `TEST_EVIDENCE_DIRTY` | clean, complete (44 of 393 tests) | `test_z01_*` |
| 74 | A CI run URL with the project prefix that leaves it through `..` segments | `CI_WRONG_REPOSITORY` | verification allowed | `test_z02_*` |
| 75 | An in-tree build backend named in `pyproject.toml` rewrites the checker during `uv sync --locked` | the check now runs before the project is built; a changed file fails CI | CI check printed 0 errors for 5 | `test_z04_*`, `test_z_ci_fails_on_staged_or_new_files_too` |
| 76 | A report written over a tracked file whose name starts with `:` | `TEST_EVIDENCE_DIRTY` | clean, complete | `test_z05_*` |

Y-12 (a verified retraction date next to `not_found_in_checked_sources`) and
Y-13 (a subdivided DOI registrant code rejected) are contract defects; both
are fixed and tested (`retraction_date_stated_without_a_retraction_record`,
`test_multilingual_and_precise_values_accepted`).

X-11 (`zh-classical` rejected by the language pattern) is a contract defect,
X-12 a defect in a test and X-14 two surviving mutants. All three are fixed.

Seeded property tests apply 19 classes of single mutation to an accepted
registry, 60 cases for each of 2 seeds. Every mutation is detected
(`test_properties.py`). Random byte damage never produces an exception.

Mutation testing: 96 mutants each disable one rule (M1 to M96, including the
new checks for S-01, V-01 to V-16, X-01 to X-13, Y-01 to Y-13 and Z-01 to
Z-05). Results are in
TEST_RESULTS.md §5.

## 4. Residual exposure, stated plainly

| Risk | Severity | Status | What remains |
|---|---|---|---|
| R-001 shared GitHub identity | high | open | the agent can do on GitHub whatever the owner can, including merging and editing the ruleset; nothing in the repository changes that |
| R-002 owner references not read | high | open | a reference that does not contain approval is accepted if it is present, well-formed and not reused |
| R-003 hand edits | medium | open | detection only; a consistent forgery is not detectable; stage definitions other than the schema-fixed fields (executor, artifacts, dependencies, policy) can be edited *before* verification, visible only in the reviewed diff |
| R-004 CI record and test report entered by the agent | medium | open | the offline check cannot fetch the run, only check that the record's URL has the exact form of a run of this repository; the run URL is public. Local git state outside the dirty-tree checks (`.git/info/exclude`, an index rewritten with the files) is not bound. Code inside the test process, committed, untracked or from a dependency, can write a false test report, and a report can be edited after the run; in CI such code must be committed or locked, so it is visible in review |
| R-016 CI gate editable by the gated change | medium | open | a pull request can change `ci.yml` so that `ci-gate` passes; Stage 00 then becomes stale, but only someone running `check` from an honest copy sees it. `pyproject.toml` and `uv.lock` are not owned: later stages must be able to add dependencies. Code in a locked wheel runs during the governance step; the build backend or a tool setting there can run code after it, in the test, report and tree-check steps |
| Structural evidence checks | medium | disclosed | document *content* is not judged; the owner's reading of the handoff is the control |
| R-012 clock dependence | low | accepted | the 5-minute bound is relative to the writer's clock: a writer whose clock is fast can record a time that blocks correct machines until real time catches up (detected, fail closed) |

Prevention of R-001, R-002 and R-016 needs a required review from an identity
the agent does not hold: owner-signed acceptance (D-006) or a separate bot
account with code-owner review. Both are owner decisions, and neither is
implemented. They add no paid infrastructure, but they do add process.

## 5. Security review of the correction itself

- No new runtime dependency. The date-time checker uses the standard library.
  `uv.lock` is unchanged.
- No shell: new git calls (`diff --no-renames`, `check-ignore --stdin`,
  `ls-tree`, `show`) use argument lists, `--no-replace-objects`,
  `GIT_NO_REPLACE_OBJECTS=1` and an empty graft file
  (`test_governance_code_runs_no_shell`).
- The workflow changed to run the owned sources with `python -P -m` from
  `src`, to assert where the package was imported from (V-04), to refuse
  anything in `src/` beside the package (X-04), to run the governance check
  before the tools that `pyproject.toml` configures (Y-08) and before the
  project is built (Z-04), and to add the `check-report` step and the final
  tree check (Y-08, D4).
  Permissions stay `contents: read` and actions stay SHA-pinned.
- New failure modes fail closed. An unreadable registry or report is an error,
  a shallow clone reports `REVISION_NOT_FOUND` without a false staleness
  report, and an interrupted write leaves the old registry
  (`test_failure_simulation.py`).

## 6. Independent review

Separate reviewer agents with no part in writing the correction review the
integrated revision. The first review, at `ee46423`, found V-01 to V-16. The
second, at `9e025c9`, found X-01 to X-14, and the third, at `4a396fb`, found
Y-01 to Y-13. A confirmation review at `97b2051` re-checked every earlier
finding and found Z-01 to Z-05 (close variants) and six overstated document
statements; these were fixed in `6d1fa00` and the documents corrected, with
no independent review of those last fixes. Their dispositions are in
`review/README.md`. The final review and its dispositions are in
TEST_RESULTS.md §9 and `review/`.
