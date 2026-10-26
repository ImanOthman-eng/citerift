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
| Y-08 | a mypy plugin named in `pyproject.toml` rewrote the checker before the CI check step | fixed as far as CI order can: the check runs before ruff, mypy and pytest, and CI fails if an unstaged tracked file changed (the confirmation review found the build backend still ran first, Z-04, and staged or new files unchecked, D4; both fixed in `6d1fa00`). Residual, stated in R-016: code run by a tool setting or the build backend still runs in the later steps and can restore what it changed |
| Y-09 | an ignored or untracked file under an owned path counted as pinned gate evidence | fixed: it must be committed at the verified revision |
| Y-10 | the CI record was not tied to the project's repository | fixed: `CI_WRONG_REPOSITORY` (a prefix test; `..` segments still escaped it, Z-02, fixed in `6d1fa00`) |
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

## `97b2051/`: confirmation review

This review followed the option recommended to the owner on 2026-10-25 for
ending the review rounds: after the Y fixes, one fresh reviewer re-checks
every earlier finding and looks for regressions at the final revision, and any
new edge case is reported as residual rather than starting another open-ended
round. The owner has not yet answered that question.

Verdict: NOT VERIFIED. 393 tests passed and every tool was clean. Of the 61
earlier findings (F-01 to F-19, V-01 to V-16, X-01 to X-13, Y-01 to Y-13), 57
were fixed and 4 partly fixed (Y-01, Y-02, Y-08, Y-10): their original attack
is stopped, but a close variant was not. The reviewer found no regression,
reran the fail-first check of the Y tests (27 failed, 366 passed, the same
test ids), and killed 24 targeted mutants. It reproduced five new defects,
Z-01 to Z-05 (1 low-medium, 4 low; none critical), and six overstated
statements in the documents (D1 to D6; D7 was cosmetic).

The Z fixes are in `6d1fa00`. Their tests fail on `97b2051`
(`../fail-first/results-97b2051.txt`), and the reviewer's Z-01, Z-02, Z-03 and
Z-05 scripts, run against `6d1fa00`, no longer reproduce. The Z-04 script runs
the old CI step order itself, like the Y-08 script; the same attack replayed in
the new order fails at the governance step (`5 errors`, exit 1) before the
build backend runs. The fix check below (`b8bb5ac/`) is the independent
check of these fixes.

| Id | Finding | Disposition |
|---|---|---|
| Z-01 | an edit that kept the file's size and mtime, with a local `core.trustctime=false`, was hidden from `git status`; a run of 44 of 393 tests reported a clean tree | fixed: every tracked file's bytes are hashed and compared with its index entry; `git status` runs with fsmonitor and the untracked cache off |
| Z-02 | a CI run URL with the project prefix could reach another repository through `..` segments | fixed: the whole URL must match the project's run URL pattern |
| Z-03 | with a damaged index, `recover` printed `Uncommitted changes: 0` | fixed: it prints `unknown` |
| Z-04 | the build backend named in `pyproject.toml` ran in `uv sync --locked`, before the governance check, and rewrote the checker | fixed: CI first installs only the locked dependencies as wheels (`--frozen --no-install-project --no-build`), runs the check, then the lock check and the project install. Residual, stated in R-016: code in a locked wheel (a `.pth` file) runs during the check |
| Z-05 | a tracked file whose name starts with `:` was read as pathspec magic and looked untracked, so a report written over it hid its change | fixed: the path is read literally |

| Id | Overstated statement | Correction |
|---|---|---|
| D1 | a dirty tree "includes files hidden from `git status`" | the documents now list what the dirty check covers and name local git state it does not (R-004); the fix check found submodule ignore settings missing from that list (R5-02, now covered) |
| D2 | the CI record "names a run of this repository" | now an exact URL match (Z-02); the documents say so |
| D3 | the governance check runs before any code `pyproject.toml` configures | true after Z-04 for the build backend and tool settings; code in locked wheels is stated as residual |
| D4 | CI fails "if any tracked file was changed" | the last step now also fails on staged changes and on new files that git does not ignore; R-016 keeps the residual that earlier code can change or restore what this step sees |
| D5 | RISK_ANALYSIS.md §5 listed only three workflow changes | updated |
| D6 | a report written over a tracked file makes the tree dirty | now true for any name (Z-05) |
| D7 | numbered list in SPECIFICATION.md ran 4, 6, 5 | renumbered |

The reviewer's report and scripts are kept as written; it replaced the
repository login with `<repository account>` in its saved outputs itself, and
the name-term scan of this directory found nothing to redact.

## `b8bb5ac/`: fix check of Z-01 to Z-05

A bounded check by a new independent reviewer of only the Z fixes and the
corrected statements, with regressions. Anything new it found was to be
reported to the owner as residual, not to start another open-ended round.

Verdict: NOT VERIFIED. 400 tests passed and every tool was clean; mutants M87
and M91 to M96 were killed. All five original Z attacks are stopped, with no
regression (an honest CI replay in the new order passes; the content check
handles CRLF settings, symbolic links, executable bits, missing files and
non-UTF-8 names, and costs 7.3 ms for 230 files). Z-02, Z-03 and Z-05 are
fixed; Z-01 and Z-04 are partly fixed because of R5-02 and R5-01:

| Id | Finding (all low) | Disposition |
|---|---|---|
| R5-01 | a committed `.venv` (forced past `.gitignore`) made uv run its interpreter wrapper during the first install, before the governance check, which then printed 0 errors for 5 | fixed in `cbb4659`: a CI step refuses a `.venv` before uv runs. Residual, stated in R-016: uv's other unowned inputs (`.python-version`, uv settings, locked wheels) |
| R5-02 | a local `submodule.<name>.ignore=all` or `diff.ignoreSubmodules=all` hid an edit inside a submodule | fixed in `cbb4659`: `git status --ignore-submodules=none` |
| R5-03 | `re.I` folded a dotless i (U+0131) or dotted capital I (U+0130) to `i` in the CI URL | fixed in `cbb4659`: case is folded for ASCII only |

Statements: D5 to D7 accurate; "exactly" for the CI URL (D2) was overstated
until R5-03; review/README.md overstated the dirty-check list (D1) and the
documents named locked wheels as the only code before the check (D3), both
corrected; MATHEMATICAL_MODEL.md said the tree is read when the report is
written, but it is read when the run starts, corrected; CHANGELOG.md now says
that new files git ignores are not seen. Observations, not counted: outside a
git repository `recover` refers to errors below that do not follow; a
mode-only change under `core.fileMode=false` is not seen (content unchanged).

The R5 fixes have tests that fail on `b8bb5ac`
(`../fail-first/results-b8bb5ac.txt`), and the reviewer's scripts no longer
reproduce R5-02 and R5-03 (`b8bb5ac/recheck-cbb4659/`, written by the agent
that made the fixes). The R5 fixes were checked by a separate independent
reviewer at `0c21182` (below).
In the reviewer's saved files, one upper-case spelling of the repository
login was replaced by `<repository account>`, the convention the reviewer
used elsewhere.

## `0c21182/`: bounded review of the R5 fixes

Requested by the owner on 2026-10-26
(`cmsg_018VCB51nDHP6HXmLU4ea5yP3BFvQvWtWFp37ndPPex2k9`): a narrowly scoped
check of R5-01, R5-02 and R5-03 by a new reviewer agent that wrote none of
the code, with no open-ended search for other defects.

Verdict: **VERIFIED**. All three fixes are FIXED. For each one the reviewer
reproduced the original attack on `b8bb5ac`, showed that `0c21182` refuses
it, showed that its regression test fails on the `b8bb5ac` code and passes
on `0c21182`, and checked the directly related boundary cases (R5-01: eight
committed `.venv` variants; R5-02: 56 combinations of change kind and ignore
setting, and honest submodule states with no false "dirty"; R5-03: a scan of
every code point from U+0080 to U+10FFFF, of which exactly four fold to an
ASCII letter under `re.I` and none under `re.I | re.A`). At `0c21182`: 404
passed, ruff, ruff format, mypy, `check` and `render-status --check` clean;
mutants M97, M98 and M99 killed. No new confirmed defect, nothing
release-blocking, no regression. `report.md` is the reviewer's report;
`scripts/` and `out/` are its scripts and outputs, unchanged.

| Item from the report | Disposition |
|---|---|
| state inside a submodule's own repository (index flags, `status.showUntrackedFiles=no` in the submodule's config) hides a change, on `b8bb5ac` and `0c21182` alike | reproduced by the reviewer, not caused by the fixes, and needs a committed submodule (the repository has none). Local git state outside the checks is already stated as not bound in R-004; R-004 now names this case. Not a defect of this review, not release-blocking |
| `test_r5_01` checks the text order of the steps, so dropping `&& test ! -L .venv` alone would not fail it | observation, not a defect: a dangling symlink still fails closed at `uv sync` (exit 2), and M99 (the whole guard removed) is killed. Not changed, because a test change is a change under a Stage 00 owned path and would need a new implementation revision |
| a committed `.python-version` path or uv setting pointing uv at a committed interpreter | hypothesis, not reproduced; already listed as an uncovered input in R-016 |

