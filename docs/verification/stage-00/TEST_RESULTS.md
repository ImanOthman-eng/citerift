# Stage 00 Test Results (correction A-00-001)

Revision tested: `0c21182e5871f772c3a76c75a1217c7641a63bbb` (branch
`claude/project-thread-84z62e`, PR #2). Its last change under a Stage 00 owned
path is `cbb4659`; `0c21182` adds only documents in this directory, the
memory files and the changelog. Every result here was produced and read on
2026-10-26 unless a section says otherwise. The accepted package of `741476c`
is kept unchanged in `superseded/741476c/`.

## 1. Test suite

| Report | sha256 | Python | Collected | Passed | Failed or other | Dirty tree | Complete selection |
|---|---|---|---|---|---|---|---|
| `test-report.json` | `dff930681421ab5ed38c69e1570b338f172859eb57ef7fb4bf049d733088fd0d` | 3.12.3 | 404 | 404 | 0 | no | yes |
| `test-report-python3.13.json` | `dc5b28fd728f0d44b4f847e94d3e5f2fb49b936f4306e9af82d07f3e105d50d5` | 3.13.14 | 404 | 404 | 0 | no | yes |

Both reports were produced **on GitHub-hosted runners** by the push run
[40273320614](https://github.com/ImanOthman-eng/citerift/actions/runs/40273320614)
at `0c21182`, and are copied unchanged from its artifacts
`test-report-python-3.12` (artifact 12629566270, zip sha256
`dc45bfb4dde139cd17f6bf0e03b7c8cf2dafa7c083aed8089234705da22f15b0`) and
`test-report-python-3.13` (artifact 12629491243, zip sha256
`bfe5a3c67c66c22d9603fd377604c3e071023fab1687ee922431f960f8087c67`). Each
zip's sha256 equals the digest GitHub reports for the artifact. Format
`citerift.test-report/1`, `exit_status` 0, pytest 9.1.1, platform
`Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`. Each report records the
whole `tests` tree (11 test files, 1 conftest), no narrowing option, no ini
override, no extra plugin, nothing deselected, dropped or repeated, and an
empty `dirty_paths`. In the same job, `citerift-gov check-report
ci-test-report.json` printed `0 problems`.

Locally, in the CITERIFT container at the same code (`cbb4659` and
`0c21182`): `404 passed` (Python 3.12.3).

Per suite (a test can belong to more than one suite):

| Suite | Passed |
|---|---|
| unit | 29 |
| integration | 141 |
| negative | 240 |
| regression | 214 |
| reproducibility | 5 |
| security | 202 |
| contracts | 87 |
| simulation | 20 |

## 2. The 12 mandatory integration scenarios

Unchanged from the accepted package and still passing, in
`tests/stage00/test_integration_scenarios.py`, each against a fresh git
sandbox: valid authorization; all tests passing gives verified, not accepted;
missing tests block; failed or untrustworthy tests block; incomplete handoff
blocks; missing owner acceptance (including fabricated acceptance and
acceptance of another revision); unauthorized next-stage request; conflicting
records; missing or stale evidence; recovery from the repository alone;
evidence-supported correction of an accepted stage; future enhancement
preserving contracts.

## 3. Regression tests for every finding (fail-first)

Every finding of every review that reproduces a behavior has a regression
test that fails on the revision it was reported against and passes now. The
runs are in `fail-first/`; the method and the per-finding tables are in
`fail-first/README.md`.

| Findings | Reported at | Tests run against | Result there | Fixed in |
|---|---|---|---|---|
| F-01 to F-19 (audit) | `741476c` | `ae2ce9e` | 82 failed, 178 passed | `373045d` and earlier |
| V-01 to V-16 (first final review) | `ee46423` | `135e4ac` | 36 failed, 269 passed | `5749e9c` |
| X-01 to X-14 (second final review) | `9e025c9` | `7138d6d` | 46 failed, 317 passed | `564030b` |
| Y-01 to Y-13 (third final review) | `4a396fb` | `4a396fb` | 27 failed, 366 passed | `aa06a40` |
| Z-01 to Z-05, D4 (confirmation review) | `97b2051` | `97b2051` | 7 failed, 393 passed | `6d1fa00` |
| R5-01 to R5-03 (fix check) | `b8bb5ac` | `b8bb5ac` | 4 failed, 400 passed | `cbb4659` |

F-20 to F-23 are documentation and detection items, X-12 is a defect in a
test and X-14 two surviving mutants; they have no fail-first run.

## 4. Static checks

In both CI verify jobs at `0c21182` (job logs of run 40273320614):

| Check | Result |
|---|---|
| `src` guard and committed-environment guard (no Python) | passed |
| `uv sync --frozen --no-install-project --no-build` | `Installed 43 packages` (dependencies only) |
| `citerift-gov check` (from `src`, before the project is built) | `Consistency check: 0 errors, 0 warnings` |
| `citerift-gov render-status --check` | `PROJECT_STATUS.md is up to date` |
| `uv lock --check` | `Resolved 45 packages` |
| package imported from the checkout | passed |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `57 files already formatted` |
| `mypy` (strict) | `Success: no issues found in 12 source files` |
| `citerift-contracts check-schemas` | `2 schemas checked, 0 problems` |
| `pytest --citerift-report ci-test-report.json` | `404 passed` |
| `citerift-gov check-report ci-test-report.json` | `0 problems` |
| tree check (`git diff --exit-code` and `git status`) | no change, no new file but the report |
| `pip-audit --strict --require-hashes` | `No known vulnerabilities found` |

Locally at `0c21182`: the same results for ruff, ruff format, mypy, `check`
and `render-status --check`.

## 5. Mutation testing

`mutation/mutation_check.py` disables one rule at a time (99 mutants, M1 to
M99) and runs the suite; a mutant is killed if the suite fails. It first runs
the unmutated suite as a baseline. The full run at `0c21182` was split into
two halves run in separate clean worktrees:

| Run | Baseline | Killed | Survived |
|---|---|---|---|
| M1 to M50 at `0c21182` | passed (404) | 50 | 0 |
| M51 to M99 at `0c21182` | passed (404) | 48 | 1: M75 |
| M75 redefined, at `06e7ab7` (same code) | passed (404) | 1 | 0 |

M75 disabled the Y-02 flag rule (files flagged `--skip-worktree` or
`--assume-unchanged` count as changed). It survived because the Z-01 content
check, added later, catches every edit that rule caught, so the mutant was
equivalent. Like M52 before it, M75 now removes both the flag rule and the
content check, and is killed; M91 removes the content check alone and is
killed by the Z-01 test. Result: 99 of 99 rules have a test that fails when
the rule is disabled (`mutation/results-0c21182.txt`, sha256
`af2d70d7cf7b6f012e817cf7dcd524a4638ba34dadd4bb6bd1337f217ca90508`). Every
mutated file was restored; `git status` in both worktrees was clean
afterwards.

Earlier targeted runs: the 17 new mutants for Y-01 to Y-13 and the four
survivors of the 73-mutant check at `564030b` (22 of 22 killed at
`a93c64f`); M87 and M91 to M96 for the Z rules (7 of 7 killed at `47dbd00`).
The fix check also killed M87 and M91 to M96 independently, in its own clone.

## 6. Simulation and model checking

From SIMULATION_REPORT.md, rerun at `0c21182`:

- State-machine model: output byte-identical to the committed
  `simulation/model-results.json` (sha256 `f41c757f…`): exhaustive reduced
  model 490 nodes, 1,756,160 attempts, 103,936 permitted, 0 violations;
  4,000,000 random-walk attempts, 0 violations.
- History replay conformance, full configuration: byte-identical to the
  committed `simulation/replay-conformance-full.json`: 205,632 cases, 0
  disagreements (12,872 at `ae2ce9e`).
- Seeded property tests (19 mutation classes, 2 seeds, 120 cases) and the
  failure simulations are part of the suite in section 1.
- Handoff simulation (10 points): `handoff/results-0c21182.json`, 12 of 12
  checks passed (the ten points, with 7b and 10b).

## 7. GitHub Actions (gate 00-K)

| Run | Event | Commit | Jobs | Conclusion |
|---|---|---|---|---|
| [40273320614](https://github.com/ImanOthman-eng/citerift/actions/runs/40273320614) | push | `0c21182` | verify (python 3.12) 121410674762, verify (python 3.13) 121410674483, ci-gate 121411929336 | success |
| [40273323339](https://github.com/ImanOthman-eng/citerift/actions/runs/40273323339) | pull_request | merge of `0c21182` into `main` | verify 3.12, verify 3.13, ci-gate | success |

The CI record cites the push run, because a `pull_request` run tests a merge
commit, not the head commit (R-004). Every step of both verify jobs
succeeded, in the order of section 4. Earlier green runs on this branch, for
the record: `97b2051` (40247422015, 40247426869), `b8bb5ac` (40253644266,
40253647891).

## 8. Branch protection (gate 00-L)

Read back from the GitHub API on 2026-10-26 with the session's token:

- `GET /repos/ImanOthman-eng/citerift/rulesets/25824038`: name
  `main-protection`, enforcement `active`, `bypass_actors: []`,
  `current_user_can_bypass: never`, last updated 2026-10-25 14:30:31 UTC
  (unchanged since the owner created it). Compared with
  `.github/rulesets/main-protection.json`: name, target, enforcement,
  conditions, bypass actors and the four rule types match, and every
  parameter in the file has the same value on GitHub. GitHub also shows
  `required_reviewers: []` and
  `require_extra_approval_for_unattributed_changes: true`, which the file
  does not contain; neither removes a rule.
- `GET /repos/ImanOthman-eng/citerift/rules/branches/main`: `deletion`,
  `non_fast_forward`, `pull_request` and `required_status_checks`, all from
  ruleset 25824038.

The ruleset requires 0 approvals and `ci-gate` is defined by a file the gated
pull request can change, so it does not make CI independent (R-016). Not
done: a test push to `main`.

## 9. Independent reviews

Five separate reviewer agents, none of which wrote the code, reviewed the
correction. Reports, scripts and dispositions are in `review/`.

| Review | Revision | Verdict | Findings |
|---|---|---|---|
| first final review | `ee46423` | NOT VERIFIED | V-01 to V-16 (1 medium, 3 low-medium, 12 low) |
| second final review | `9e025c9` | NOT VERIFIED | X-01 to X-14 (1 medium, 5 low-medium, 8 low) |
| third final review | `4a396fb` | NOT VERIFIED | Y-01 to Y-13 (2 medium, 4 low-medium, 7 low) |
| confirmation review | `97b2051` | NOT VERIFIED | 57 of 61 earlier findings fixed, 4 partly; no regression; Z-01 to Z-05 (1 low-medium, 4 low); D1 to D7 |
| fix check of the Z fixes | `b8bb5ac` | NOT VERIFIED | Z attacks stopped; no regression; R5-01 to R5-03 (3 low); wording |

No review found a critical defect. Every finding was reproduced and fixed
with a regression test (section 3). **The R5 fixes in `cbb4659` have not been
checked by an independent reviewer**, and no review has returned a clean
verdict.

## 10. Gaps in test coverage

- Document content is not judged by any test (structural checks only).
- Code inside the test process can forge the report (R-004); the dirty-tree
  check reads the tree when the run starts.
- The governance check in CI runs after the locked dependencies are
  installed; code in a locked wheel runs inside it (R-016).
- Each review round so far has found new low-severity variants; a further
  round may find more.
