# Independent reviews of correction A-00-001

Each subdirectory holds one review by a separate reviewer agent that took no
part in writing the correction. The reviewer worked in its own clones and
changed nothing in the repository or on GitHub. Its report and reproduction
scripts are kept as it wrote them, with one exception: in `9e025c9/`, one
search term that is part of a personal name was replaced by
`<name terms, redacted>` (docs/identity.md). The scripts refer to the
reviewer's scratch paths (`$W/...`), so they show method and are not meant to
run unchanged. Ruff skips this directory (`pyproject.toml`). The third
reviewer created an empty, git-ignored `.venv/` in its own review copy by
accident; no tracked file changed.

## `ee46423/`: first final review

Verdict: NOT VERIFIED. 260 tests passed, ruff, mypy and `check` were clean.
F-01 to F-23 were partly confirmed fixed (§2 of the report), and 16 new
findings were raised.

The report numbers them N-01 to N-16. The repository calls them **V-01 to
V-16**, because "N-01" was already used in the message of commit `373045d`
for the defect now called S-01. V-*n* is the report's N-*n*.

All sixteen were reproduced. Their regression tests failed on `135e4ac`, with
the corrected tests run against the old code
(`../fail-first/results-135e4ac.txt`: 36 failed, 269 passed). The fixes are in
`5749e9c`.

| Id | Finding | Disposition |
|---|---|---|
| V-01 | partial test run (ini override, other ini file, conftest drop, `collect_ignore`) recorded as complete | fixed for those runs: they are partial, and every committed test file must have run. The second review found bypasses (X-02, X-03) |
| V-02 | a URL, or one pinned file among unpinned ones, counted as pinned gate evidence | fixed: URLs are not pinned, and each unpinned file is an error |
| V-03 | stage overrides could weaken the schema-fixed policy; handoff not always required | fixed in the schema (artifact list, executor per stage) and in `_artifacts_for` |
| V-04 | CI check run through an entry point that `pyproject.toml` can redirect | fixed for entry points: CI runs `python -P -m` from `src`, with a guard step. The second review found a bypass through `src/sitecustomize.py` (X-04). Residual: `pyproject.toml` and `uv.lock` are not owned (R-016) |
| V-05 | an amendment test report exempted arbitrary files from the manifest | fixed: only enhancement reports are exempt, and others are hash-checked |
| V-06 | memory parser skipped some heading forms | fixed: fields outside a recognised heading are `MEMORY_MALFORMED`; topics are compared after NFKC, separator and case folding |
| V-07 | owner-reference reuse checked only against history | fixed for amendments (case 3). Cases 1 and 2, one message covering several decisions, are allowed by design (GOVERNANCE.md invariant 2, R-002) |
| V-08 | one correction amendment justified several reopenings | fixed: `HISTORY_AMENDMENT_REUSED` |
| V-09 | duplicate amendment and blocker ids accepted | fixed: `AMENDMENT_DUPLICATE_ID`, `BLOCKER_DUPLICATE_ID` |
| V-10 | remaining tracebacks (schema missing or damaged, `{}` registry, undecodable memory) | fixed: named errors, exit 1 |
| V-11 | default times could precede the last history entry | fixed; R-012 now states that a fast clock still blocks (detected, fail closed) |
| V-12 | a nested `.gitattributes` changed evidence hashes | fixed: `ATTRIBUTES_NESTED` error for a tracked nested file |
| V-13 | `git replace` hid owned-path drift | fixed: every git call uses `--no-replace-objects` |
| V-14 | ruleset and fixture tests read JSON last-key-wins | fixed: `loads_strict`. No fail-first run is possible, because the defect is in the test itself; reproduced by hand |
| V-15 | test gaps in the new checks | tests added. They pass on the old code by design, because they kill mutants rather than reproduce a defect. The mutation check at `5749e9c` still found three rules without a test of their own (M26, M35, M37); tests for them were added in `9e025c9` and `7138d6d` |
| V-16 | a report into a missing directory crashed the plugin | fixed: the directory is created |

The report's §7 items that it did not reproduce are not counted as findings.
`collect_ignore` is now covered by V-01's file enumeration.

## `9e025c9/`: second final review

Verdict: NOT VERIFIED. 308 tests passed and every tool was clean. The
reviewer reproduced the first review's findings against `9e025c9` and tried
to get around each fix (§2 of the report), then raised 14 findings, X-01 to
X-14 (1 medium, 5 low-medium, 8 low; none critical). All fourteen were
reproduced. The tests for X-01 to X-13 fail on `7138d6d`
(`../fail-first/results-7138d6d.txt`: 46 failed, 317 passed), and the fixes
are in `564030b`.

| Id | Finding | Disposition |
|---|---|---|
| X-01 | gate evidence through `..` or a symlink inside an owned path counted as pinned | fixed: a cited file must be named by a plain path |
| X-02 | one committed `python_functions` line in `pyproject.toml` ran 92 of 308 tests, report complete | fixed: collection settings that differ from the fixed values make the run partial |
| X-03 | a conftest padding the item list with repeats, also uncommitted or as a `-p` plugin, gave a complete report for 21 of 308 tests | fixed for those cases: dropped tests are compared by node id, repeats, `-p` and `PYTEST_PLUGINS` plugins and uncommitted conftests make the run partial. Residual, stated in R-004: code inside the test process can still forge the report |
| X-04 | `src/sitecustomize.py` or a shadowing package under `src/` ran inside every CI check | fixed: a shell step refuses it before any Python runs; `check` reports `SRC_FOREIGN_MODULE` |
| X-05 | 16 more inputs ended in a traceback | fixed: named errors (17 cases tested) |
| X-06 | bold, lowercase or indented fields under a non-standard heading hid a critical defect; invisible characters split topics | fixed: misformatted entry fields are errors; format characters are removed from topics. An entry with neither a recognisable heading nor recognisable fields is still not seen (GOVERNANCE.md invariant 7) |
| X-07 | removing a dependency before authorization let Stage 02 be accepted without Stage 01 | fixed: the schema fixes every stage's dependencies (D-010) |
| X-08 | add, block and resolve within one second was refused, with the error labelled pre-existing | fixed |
| X-09 | `.git/info/grafts` was still honoured | fixed: `GIT_GRAFT_FILE` points at an empty file |
| X-10 | an acceptance with an open blocker passed the replay; the model had no such guard | fixed in the replay and in the model; the model output therefore changed (SIMULATION_REPORT §1) |
| X-11 | `zh-classical` rejected by the language pattern | fixed in 1.0.1 (unreleased): subtags of up to 12 characters |
| X-12 | a Stage 00 test asserted today's state and would fail after the next owner decisions | fixed: the test asserts the authorization rule. A defect in a test, so there is no fail-first run |
| X-13 | an enhancement amendment changed an accepted contract with a reused owner reference and no version | fixed: amendments need an owner reference not cited before; a contract change needs a version increase and must keep the accepted valid fixtures valid. Residual: whether the change keeps the contracts' meaning is the owner's judgment, and an enhancement has no CI record |
| X-14 | M35 and M37 survived | fixed in `7138d6d`; the mutation check now also runs a baseline first |

The report's §4 lists overstated documentation. GOVERNANCE.md, RISKS.md
(R-003, R-004, R-016, new R-019), CHANGELOG.md, docs/data-contracts.md and
the documents in this directory were corrected after it.

## `4a396fb/`: third final review

Verdict: NOT VERIFIED. 363 tests passed and every tool was clean. The
reviewer rechecked variants of X-01, X-03, X-07, X-09, X-10 and X-11 (still
stopped), then raised 13 findings, Y-01 to Y-13 (2 medium, 4 low-medium, 7
low; none critical), and seven observations (O-1 to O-7). All thirteen were
reproduced. Their tests fail on `4a396fb`
(`../fail-first/results-4a396fb.txt`: 27 failed, 366 passed), and the fixes
are in `aa06a40`. The reviewer's own scripts, run against `aa06a40`, no
longer reproduce Y-01 to Y-07 or Y-09 to Y-13. The Y-08 script runs the old
CI step order itself (mypy before the check), so it still shows the rewrite;
the fix is the new step order in `ci.yml`, tested by
`test_y_ci_checks_its_own_report_and_runs_the_checker_before_configured_tools`.

| Id | Finding | Disposition |
|---|---|---|
| Y-01 | a report written over a tracked test file hid that file's change | fixed: the report path is left out of the dirty check only when it is untracked |
| Y-02 | changes hidden with `--skip-worktree` or `--assume-unchanged` gave a clean tree | fixed: such flagged files count as changed; `git status` is read with `-z` (which also settles O-5) |
| Y-03 | skipped and xfailed tests counted as a complete run | fixed: every test must pass; any other outcome makes the run partial |
| Y-04 | `Stage` or ids in Arabic-Indic or fullwidth digits passed validation but did not block | fixed: ASCII digits only; other digits are `RISK_INVALID_FIELD` or `MEMORY_MALFORMED` |
| Y-05 | a retraction conflict could hold an absence of record, or values that agree | fixed in 1.0.1 (unreleased): only positive records as alternatives (schema), at least two different values (semantic check, every assertion) |
| Y-06 | a hand-written enhancement on a verified stage passed `check` and covered owned changes | fixed: an amendment must be recorded while its stage is accepted; only enhancements of the current acceptance cover changes |
| Y-07 | the amendment reference rule could be passed with a chosen time | fixed: same-second citations count as earlier, and a back-dated amendment falls under Y-06 |
| Y-08 | a mypy plugin named in `pyproject.toml` rewrote the checker before the CI check step | fixed as far as CI order can: the check runs before ruff, mypy and pytest, and CI fails if a tracked file changed. Residual, stated in R-016: code run by a tool setting or a dependency still runs in the later steps and can restore what it changed |
| Y-09 | an ignored or untracked file under an owned path counted as pinned gate evidence | fixed: it must be committed at the verified revision |
| Y-10 | the CI record was not tied to the project's repository | fixed: `CI_WRONG_REPOSITORY` |
| Y-11 | five more inputs ended in a traceback | fixed: named errors, and a last-resort handler for git failures in the CLI |
| Y-12 | a verified retraction date was accepted next to `not_found_in_checked_sources` | fixed in 1.0.1 (unreleased): no date may stand without a retraction record |
| Y-13 | the DOI pattern rejected a subdivided registrant code | fixed in 1.0.1 (unreleased) |

Observations: O-1 (Arabic tatweel and short-vowel marks in topics) is now
folded; O-5 is settled by Y-02; O-6 (CI did not check its own report) is
fixed by the `check-report` step. O-2 (a `pull_request` run tests the merge
commit) is stated in R-004: the CI record cites the `push` run. O-3 (owner
references compared as exact strings) and O-4 (accepted decisions need no
owner reference) stay within R-002. O-7 is the identity scan; it found no
issue.

The report's §4 lists overstated documentation. GOVERNANCE.md, RISKS.md
(R-003, R-004, R-016, new R-020), CHANGELOG.md, docs/data-contracts.md and
the documents in this directory were corrected after it. The 73-mutant check
at `564030b` also found four rules without a test of their own (M52, M57, M58,
M59); `aa06a40` adds tests for M57 to M59, and `a93c64f` makes M52 remove
both replace-object controls, since either one alone still stops the attack.
