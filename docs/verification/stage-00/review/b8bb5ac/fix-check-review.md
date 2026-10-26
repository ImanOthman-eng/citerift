# Fix check of CITERIFT Stage 00 at `b8bb5ac` (Z-01 to Z-05, D1 to D7)

Reviewer: an independent reviewer agent. It wrote none of the reviewed code. The scope was a bounded fix check of
correction A-00-001 at `b8bb5acf9905f83bfe83f8a56b493cd8c632c435`: are Z-01 to Z-05 of the confirmation review of
`97b2051` fixed (`6d1fa00` for code, CI and tests, `47dbd00` for mutants M91 to M96, `b8bb5ac` for documents)? Did the
fixes cause regressions? Are the corrected statements D1 to D7 accurate? Stage 01 is out of scope.

`$W` = `/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review5`. `$W/base` is a
`git clone` of the review working copy at `b8bb5ac`, set up with `uv sync --locked --offline`. Every experiment ran in a
throwaway clone or sandbox under `$W/sandbox-*`. Nothing in `/home/user/citerift` or in `review5-tree` was changed. In
`review5-tree` I only ran the read-only `check` and `render-status --check` with `PYTHONDONTWRITEBYTECODE=1` and
`-B`. `git status --porcelain --ignored` there showed 0 entries before and after. No git remote, GitHub or network
service was used. `uv lock --check` and the pip-audit step need the network and were **not run**. The statement that
CI on `b8bb5ac` is green cannot be checked offline, and nothing here relies on it. Scripts are in `$W/scripts/` and
outputs in `$W/out/`. In saved outputs the repository account login is written as `<repository account>`.

Severity scale as given by the caller. A defect counts only if I reproduced it.

## 1 Baseline at `b8bb5ac`

Run from `$W/base` (`$W/out/baseline.txt`).

| Command | Exit | Output line |
|---|---|---|
| `uv run --no-sync pytest -q -p no:cacheprovider` | 0 | `400 passed in 265.87s (0:04:25)` |
| `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| `uv run --no-sync ruff format --check .` | 0 | `57 files already formatted` |
| `uv run --no-sync mypy` | 0 | `Success: no issues found in 12 source files` |
| `uv run --no-sync citerift-gov check` | 0 | `Consistency check: 0 errors, 0 warnings` |
| `uv run --no-sync citerift-gov render-status --check` | 0 | `PROJECT_STATUS.md is up to date` |

After the run, `git status --porcelain` in `$W/base` was empty. The same `check` and `render-status --check`, run
read-only on `review5-tree`, gave `0 errors, 0 warnings` and `up to date`. The commits `6d1fa00`, `47dbd00` and `b8bb5ac`
each carry the `Assisted-by: Claude Code (AI coding agent)` trailer and no `Co-Authored-By` or `Claude-Session` line.

Mutants (`$W/scripts/run_selected_mutants.py`, run in the clone `$W/sandbox-mut` with the harness's own suite command
and pattern rules; `$W/out/mutants.txt`):

| Mutant | Result | Killing test (first failure, suite run with `-x`) |
|---|---|---|
| M87 Y-10 CI run of another repository accepted | KILLED (`1 failed, 259 passed`) | `test_y10_the_ci_run_must_belong_to_the_project_repository` |
| M91 Z-01 content check skipped | KILLED (`1 failed, 266 passed`) | `test_z01_an_edit_hidden_by_the_stat_cache_still_makes_the_tree_dirty` |
| M92 Z-02 URL matched as a prefix | KILLED (`1 failed, 267 passed`) | `test_z02_a_ci_url_that_leaves_the_project_repository_is_refused[/../../../../../someone-else/other/actions/runs/7]` |
| M93 Z-03 unknown changes printed as a count | KILLED (`1 failed, 261 passed`) | `test_y11_more_damaged_inputs_are_reported_not_crashed[damaged_index]` |
| M94 Z-04 project installed before the check | KILLED (`1 failed, 270 passed`) | `test_z04_ci_runs_the_governance_check_before_anything_builds_the_project` |
| M95 D4 staged and new files not checked | KILLED (`1 failed, 271 passed`) | `test_z_ci_fails_on_staged_or_new_files_too` |
| M96 Z-05 path read as a pathspec | KILLED (`1 failed, 272 passed`) | `test_z05_a_report_written_over_a_tracked_colon_file_does_not_hide_its_change` |

Every pattern was found exactly once, and `git status --porcelain` in the clone was empty afterwards. The full 96-mutant
check was not run. None of these mutants affects R5-01, R5-02 or R5-03, which no test covers.

## 2 Z-01 to Z-05: original attack and close variants

The reviewer's scripts were copied unchanged to `$W/scripts/orig_z/` and run with `W=$W` against `b8bb5ac`
(`$W/out/orig_z.txt`, `$W/out/Z04_new_order.txt`).

| Id | Original attack at `b8bb5ac` | Variants tried | Result |
|---|---|---|---|
| Z-01 | **stopped.** 11 of 11 test files edited, `git status` empty, no flag, `44 passed` → report `dirty: True` with all 11 paths, `check_test_report` `TEST_EVIDENCE_DIRTY`, `check-report` `1 problems` | `v_z01_content_check.py`: `core.checkStat=minimal`, a clean filter in `.git/info/attributes` that returns the committed blob, a `core.fsmonitor` hook that reports no change, `--assume-unchanged`, `--skip-worktree`, a staged edit, `core.worktree` pointed at a clean copy, a sha256 repository → all give `dirty_paths: ['a.py']` (or the edited path). **Not caught:** an edit inside a committed submodule hidden by a local `submodule.<name>.ignore=all` or `diff.ignoreSubmodules=all` → R5-02 | **partly fixed**: every hiding setting for the repository's own tracked files is caught; the submodule variant is not |
| Z-02 | **stopped.** `dot segments: allowed=False ['CI_WRONG_REPOSITORY']` | `v_z02_url_forms.py`: percent-encoded dots, `..` inside the repository part → `CI_WRONG_REPOSITORY`; trailing newline, query, fragment, `/attempts/2`, userinfo, port, `http`, fullwidth digits → `REGISTRY_SCHEMA`; control exact and upper-case → allowed. **Accepted:** `…/<repository account>/cıterift/…` (U+0131) and `…/cİterift/…` (U+0130) → R5-03 | **fixed** for the attack (a URL that leads to another repository's run). The low residual R5-03 contradicts the "exactly" wording |
| Z-03 | **stopped.** Damaged index: `Uncommitted changes: unknown (git could not list them; see the errors below)` plus `ERROR REVISION_UNVERIFIABLE … index file smaller than expected`; `--json` `None` | `v_z03_recover.sh`: git missing from `PATH` → `ERROR REVISION_UNVERIFIABLE: … git executable not found`, no traceback; a copy without `.git` → `unknown (… see the errors below)`, but no error follows (`Consistency: 0 errors`), see observation O-1 | **fixed** |
| Z-04 | **stopped.** In the new step order (`Z04_new_order.py`): dependency-only sync exit 0 with the tree clean, governance step **exit 1** (`STATUS_DOC_OUT_OF_DATE`, the honest result). The backend rewrites `cli.py` only in the later `uv sync --locked` | `v_z04_committed_venv.py`: a committed `.venv` (force-added past `.gitignore`) whose `bin/python` is a wrapper script. `uv sync --frozen --no-install-project --no-build` runs it to query the interpreter, it rewrites `cli.py` there, and the governance step prints `0 errors` for a registry the honest checker reports with 5 → R5-01. The documented residual (a `.pth` in a locked wheel) was not reproduced | **partly fixed**: the build backend no longer runs first, but other committed code still runs before the check |
| Z-05 | **stopped.** `dirty: True, dirty_paths: [':cases.json']`, `TEST_EVIDENCE_DIRTY` | `v_z01_content_check.py` (R7): `is_tracked` is `True` for tracked `:x.txt`, `:(top)y.txt`, `:!z.txt`, `*.txt`, `a?.py`, `[ab].py`, `sp ace.txt` and a non-UTF-8 name, and `False` for `untracked.txt` and the glob `*.py` (not a tracked name). The plugin resolves the report path before the test, so `./` and `..` forms reach `is_tracked` in normal form | **fixed** |

## 3 Regressions

| Check | Result | Evidence |
|---|---|---|
| Honest complete run accepted | yes: `400 passed`, `check-report` `Test report ci-test-report.json at b8bb5acf9905: 0 problems`, report `dirty: False`, `collected: 400`, `complete True` | `$W/out/ci_replay_new_order.txt` |
| CI steps replayed locally in the new order on an honest fresh clone (uv steps `--offline`) | every local step exit 0 in the order of ci.yml: guard, `uv sync --frozen --no-install-project --no-build`, `check` (`0 errors, 0 warnings`), `render-status --check`, `uv sync --locked`, package-from-checkout, ruff, ruff format, mypy, schemas (`2 schemas checked, 0 problems`), pytest, `check-report`, tree check (`git diff --exit-code` and the new `git status` filter: no output). `uv lock --check` and pip-audit were not run (network) | `$W/scripts/ci_replay_new_order.sh` |
| Content check with CRLF settings | clone with `core.autocrlf=true`, `core.eol=crlf`: `git status` empty, `dirty_paths: []` (the root `.gitattributes` keeps LF). Outside this repository's setup it fails closed: with no `.gitattributes` and `autocrlf=true`, or with a local `.git/info/attributes` set to `* text eol=crlf`, the CRLF files are reported dirty while `git status` is empty (O-2) | `v_z01_content_check.py` R2 to R4 |
| Symlinks | a tracked symlink is not flagged (honest). With `core.symlinks=false` the link is checked out as a regular file and reported dirty while `git status` is empty: fails closed (O-2). This repository tracks no symlink (`git ls-files -s`: 229 × `100644`, 1 × `100755`) | R1, R5 |
| Executable bits | an honest `100755` file is not flagged. A mode-only change under `core.fileMode=false` is not seen; the bytes are unchanged, so test content is not affected (O-3) | R1, case 10 |
| Missing file | `git status` ` D b.txt`, `dirty_paths: ['b.txt']` | R6 |
| Tracked file with a non-UTF-8 name | honest → `dirty_paths: []`; edited → `['caf\udce9.txt']` (surrogate-escaped); `is_tracked` `True`; no traceback | R7, R7b |
| sha256 object format | honest `[]`, edited `['b.txt']` | R8 |
| Cost of the content check | 230 tracked files, 1,519,678 bytes: `_content_changed` 7.3 ms, `dirty_paths` 12.8 ms (best of 5, measured while the CI replay ran). `check` wall time 0.19 s at both `97b2051` and `b8bb5ac`. At this revision `check` makes no `dirty_paths` call (no stage verified or accepted); each test-report start and each verified or accepted stage with owned paths costs one call | `$W/out/cost_content_check.txt` |
| `recover` output | exit 0, `HEAD: b8bb5ac… on claude/project-thread-84z62e`, `Uncommitted changes: 0`, `IN_PROGRESS: 00`, `AUTHORIZED: 01`, `Consistency: 0 errors, 0 warnings` | `$W/out/v_z03_recover.txt` |

No regression found. The fail-closed cases in O-2 give a false "dirty" only on checkouts that differ from this
repository's setup.

## 4 New defects (reproduced)

| Id | Severity | File:line | Description | Reproduction | Expected vs actual |
|---|---|---|---|---|---|
| R5-01 | low | `.github/workflows/ci.yml:41` (the guard checks only `src`), `:53` (dependency-only `uv sync`), `:60` (governance step) | Close variant of Z-04. The new order stops the build backend, but uv still runs a committed interpreter. A `.venv/pyvenv.cfg` and `.venv/bin/python` force-added to the commit (`.venv/` is in `.gitignore`, so it is visible only as a forced add in the diff) are used by `uv sync --frozen --no-install-project --no-build`, which runs `bin/python` to query the interpreter, and by every later `uv run`. The wrapper rewrites the checker before the governance step. As with Z-04, the final tree check sees the change unless the same code restores it in a later step; it runs on every `uv run`, so it can (R-016 class). Not run in the replay: actions/checkout and setup-uv (replaced by `git clone` and local uv 0.11.32) | `cd $W/scripts && W=$W $W/base/.venv/bin/python v_z04_committed_venv.py` | Expected: the governance step gives the honest `5 errors`, exit 1. Actual: the wrapper ran during the sync (`wrapper ran: -I -B -c … get_interpreter_info …`), `git status`: `M src/citerift/governance/cli.py`, governance step `exit 0: Consistency check: 0 errors, 0 warnings` |
| R5-02 | low | `src/citerift/governance/gitutil.py:188` (`160000` entries skipped), `:142-151` (`git status` honours the submodule ignore settings) | Close variant of Z-01. A test imports a helper from a committed submodule. The helper is edited so that the test passes trivially, and a local `submodule.vendor.ignore=all` (or `diff.ignoreSubmodules=all`) in `.git/config` hides the edit from `git status`. The content check skips gitlinks, so nothing sees it. This needs a submodule to be committed first; this repository has none, and adding one is visible in review | `cd $W/scripts && W=$W $W/base/.venv/bin/python -P v_z01_submodule_report.py` | Expected `TEST_EVIDENCE_DIRTY` (control without the setting: `dirty_paths=['vendor']`, `TEST_EVIDENCE_DIRTY`). Actual with either setting: `git status ''`, `2 passed`, `dirty=False dirty_paths=[] complete=True`, `check_test_report problems: []` |
| R5-03 | low | `src/citerift/governance/orchestrator.py:822-823` (`re.fullmatch(…, re.I)` on a `str` pattern uses Unicode case folding); schema `stage_registry.schema.json:228` allows non-ASCII in the path | Close variant of Z-02. With `re.I`, U+0131 (dotless i) and U+0130 (capital I with dot) match `i`, so `https://github.com/<repository account>/cıterift/actions/runs/123` is accepted. GitHub owner and repository names are ASCII, so the URL names no run of any repository; it does not reach another repository's run, but it contradicts "the run URL must be exactly …" | `cd $W/scripts && W=$W $W/base/.venv/bin/python v_z02_url_forms.py` | Expected `CI_WRONG_REPOSITORY`. Actual: `allowed=True []`, applied, `check after verification: 0 errors`, `recorded run_url is ASCII: False`. `re.ASCII` with `re.I`, or comparing `casefold()` of an ASCII-only URL, would refuse it |

None of these is critical or medium. Each needs a committed, reviewable change (R5-01, R5-02) or a deliberately
crafted record (R5-03).

## 5 Documentation: D1 to D7

| # | Corrected statement | Accurate now? |
|---|---|---|
| D1 | GOVERNANCE.md:52-56, RISKS.md:95-101 (R-004), SPECIFICATION.md:93-97, MATHEMATICAL_MODEL.md:173-178, RISK_ANALYSIS.md:47: a dirty tree covers `git status`, flags, bytes against the index entry, and a report over a tracked file of any name | **Accurate** for what is checked (§2 Z-01, Z-05). R-004's "Local git state outside these checks, such as …" gives examples and does not claim to be complete. **Overstated:** review/README.md:161 says the documents "now list exactly … what local git state it does not (R-004)". The submodule ignore settings (R5-02) are not listed, and neither is `core.fileMode` (harmless, O-3). Minor: R-004 and RISK_ANALYSIS.md:167 list "an index rewritten with the files" as not bound. A staged or index-rewritten edit is in fact caught (`v_z01_content_check.py` case 7: `M  a.py`, `dirty_paths: ['a.py']`). This understates, it does not overstate, and I did not test every way of forging an index |
| D2 | GOVERNANCE.md:49-50, RISKS.md:80-82, SPECIFICATION.md:104-106, RISK_ANALYSIS.md:47 and :167: "the run URL must be exactly `https://github.com/<repository>/actions/runs/<id>`" | **Overstated in a small way** (R5-03): the match ignores case with Unicode folding, so a non-ASCII spelling is accepted. MATHEMATICAL_MODEL.md:234-236 ("as a whole and compared without case") is accurate for ASCII. Dot segments can no longer lead to another repository: true |
| D3 | GOVERNANCE.md:212-226, RISKS.md:254-266 (R-016), RISK_ANALYSIS.md:48 and :168, ci.yml:55-57, review/README.md:156 and :163: before the check only locked wheels are installed, so no build backend runs; code in locked wheels is the stated residual | **True for `pyproject.toml`** (Z-04 replay: the governance step fails before the backend runs). **Incomplete:** the documents name locked wheels as the only code that runs before or during the check. A committed `.venv` interpreter also runs before it (R5-01). GOVERNANCE.md:225-226 ("Such code must be committed or locked, so it is visible in the reviewed diff") still holds |
| D4 | GOVERNANCE.md:218-221, RISKS.md:258-260, RISK_ANALYSIS.md:48, CHANGELOG.md: CI fails if `git status` shows an unstaged or staged change or a new file other than the report | **Accurate** as worded with "`git status` shows". The CI replay's tree check passes on an honest tree. CHANGELOG.md:107-108 says the last step "fails on staged changes and new files" without the qualifier: a new file in an ignored path is not seen (O-4). RISK_ANALYSIS.md:134 (row 69, "a changed tracked file fails CI") was not edited, but it is now true in the same sense, with the R-016 caveat |
| D5 | RISK_ANALYSIS.md:185-191 lists every workflow change | **Accurate** against `git diff 741476c b8bb5ac -- .github/workflows/ci.yml` (python -P, import check, src guard, step order for Y-08 and Z-04, `check-report`, tree check) |
| D6 | a report over a tracked file makes the tree dirty "whatever its name" | **Accurate** (Z-05 row of §2) |
| D7 | SPECIFICATION.md numbered list | **Fixed**: the items run 1 to 6 at :63, :73, :78, :85, :104, :107 |

Other changed statements I checked and found accurate: fail-first/README.md (7 failed, 393 passed; per-finding counts
sum to 7; `results-97b2051.txt` ends `7 failed, 393 passed`, with 7 `FAILED` lines); 96 mutants in CREATIVE_DIFFERENTIATION_REVIEW.md and
RISK_ANALYSIS.md:155-157 (M1 to M96 in `mutation_check.py`); RISK_ANALYSIS.md rows 73 to 76; SPECIFICATION.md rule 8 (Z-03);
review/README.md "the reviewer's Z-01, Z-02, Z-03 and Z-05 scripts … no longer reproduce" (true at `b8bb5ac` too);
RISKS.md R-021.

One more inaccuracy in a changed statement. MATHEMATICAL_MODEL.md:176-177 says "The bytes are read when the report is
written, by the test process". In fact `dirty_paths`, which runs the content check, is called once in
`pytest_configure` (src/citerift/governance/pytest_report.py:85), at the start of the run. The report is written at
the end, and nothing re-reads the tree then (`grep -n dirty_paths src/citerift/governance/pytest_report.py`: only
:85, :88, :197, :218). An edit made during the run and left in place is therefore not in the report. It would still
show in a later `check` of the tree, and code that runs inside the test process is the stated R-004 residual. Low,
wording only.

## 6 Observations (not counted)

- O-1 Outside a git repository (a copy without `.git`), `recover` prints `Uncommitted changes: unknown (git could not
  list them; see the errors below)`, but no error follows: `Consistency: 0 errors, 0 warnings`. The text promises an
  error line that is not there (cli.py:225).
- O-2 The content check reads raw bytes, so it fails closed whenever checked-out bytes legitimately differ from the
  blob. Examples: `core.symlinks=false`, a local `.git/info/attributes` that overrides the LF rule, or (for a later
  stage) Git LFS or other filters. An honest run is then reported dirty although `git status` is empty. This does not
  affect this repository's current setup.
- O-3 A mode-only change hidden by `core.fileMode=false` is not seen. File content is unchanged.
- O-4 The CI tree check uses `git status`, so it does not see new files in ignored paths, and it is subject to the
  stat cache like Z-01. Earlier code can arrange both, which falls under the stated R-016 residual. The test report's
  own content check covers edits made before pytest starts.

## 7 Verdict

The original attacks of Z-01 to Z-05 are all stopped at `b8bb5ac`. Z-02, Z-03 and Z-05 are fixed. Z-01 and Z-04 are
partly fixed, because a close variant still works: R5-02 (a submodule edit hidden by a local ignore setting) and R5-01
(a committed `.venv` interpreter that runs before the governance step). R5-03 is a low residual of Z-02. All three are
low, and none is critical or medium. No regression was found. D5, D6 and D7 are accurate. D4 is accurate as worded.
D1 is accurate in the main documents, but its disposition says "exactly", which is overstated. D2 ("exactly") and D3
(only locked wheels run before the check) remain slightly overstated or incomplete. The new MATHEMATICAL_MODEL.md
sentence on when the bytes are read is wrong: they are read at the start of the run, not when the report is written.

NOT VERIFIED
