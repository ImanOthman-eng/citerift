# Bounded independent review of the R5 fixes at `0c21182`

Reviewer: a separate reviewer agent with no part in writing the code or the
fixes. Requested by the owner on 2026-10-26
(`cmsg_018VCB51nDHP6HXmLU4ea5yP3BFvQvWtWFp37ndPPex2k9`, section 3): a narrowly
scoped check of R5-01, R5-02 and R5-03 only, not an open-ended audit.

The reviewer's environment did not let it write this file, so it returned the
report as text. The engineering agent saved that text here unchanged except
for this header and the path names: `$R` below is the reviewer's scratch
directory, whose `scripts/` and `out/` are copied unchanged into this
directory.

`$R` = `/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review6`

---

**Overall verdict: VERIFIED.** R5-01, R5-02 and R5-03 are all FIXED. I found
no new defect caused by the three fixes, nothing release-blocking, and no
regression.

## 1. Scope and revisions tested

| Role | SHA |
|---|---|
| Pre-fix | `b8bb5acf9905f83bfe83f8a56b493cd8c632c435` |
| Fix | `cbb4659d00127ed6a14074622ba2732648749e1e` |
| Mutants | `738a2df7ba476fccc6c0eaa90b2ba27e8990d161` |
| Candidate (tested) | `0c21182e5871f772c3a76c75a1217c7641a63bbb` |
| Head (static checks and `check` only) | `03631fc12ac0db167b36e8219aba374006043c49` |

- **Code is the same from fix to head.** `git diff --stat cbb4659 0c21182 -- src .github tests pyproject.toml uv.lock schemas` is empty, and so is the same diff from `0c21182` to `03631fc`. After `0c21182` the mutation script changes only for M75 (`out/revisions.txt`).
- **Tools:** git 2.43.0, uv 0.11.32, Python 3.12.
- **Where it ran:** only in clones under `$R`: `repo`, `w-pre`, `w-fix`, `w-head`, `w-pretests` (`cbb4659` tests over `b8bb5ac` `src/` and `.github/`) and `w-mut`. Nothing was pushed and no GitHub or remote state was touched.
- **Original repo:** I did not modify `/home/user/citerift`; its HEAD is still `03631fc`. Its `git status` shows two untracked files I did not create: `docs/verification/stage-00/RISK_DECISION_PACKAGE.md` and `TRACEABILITY.md`.

## 2. Per finding

### R5-01: committed `.venv` — FIXED

**Correction.** A new CI step, `test ! -e .venv && test ! -L .venv`, sits after checkout and the `src` guard, and before `setup-uv` and `uv sync`. It runs no Python.

**How I replayed CI (`scripts/r5_01_ci_replay.py`).**
- It reads the revision's own `ci.yml` and replays its `run:` steps in order on a fresh clone, under `bash -eo pipefail`, with `UV_PYTHON=3.12` and `PYTHONPATH=src`. It stops at the first failing step.
- `actions/checkout` is replaced by `git clone`, and `setup-uv` by the local uv 0.11.32. `uv sync` gets `--offline`.
- The test commit carries the same registry hand edit as the previous reviewer used. The honest `check` reports 4 errors on it. `PROJECT_STATUS.md` is regenerated so only `check` objects.

**Reproduced on `b8bb5ac`** (`out/r5_01_ci_replay_pre.txt`), with a `.venv` directory holding a wrapper `bin/python`:
- uv ran the wrapper 3 times and it rewrote `cli.py`.
- The governance step then printed `exit 0: Consistency check: 0 errors, 0 warnings / PROJECT_STATUS.md is up to date`.

**Refused on `0c21182`** (`out/r5_01_ci_replay_fix.txt`): `[No committed environment] exit 1 -> job stops`. The wrapper ran 0 times and the tree stayed clean.

**Regression test.** `test_r5_01_...` passes on `0c21182`. On `b8bb5ac` code it fails with `ValueError: substring not found` (`out/regression_tests_r5.txt`).

**Boundary cases (pre → fix):**

| Committed variant | `b8bb5ac` | `0c21182` |
|---|---|---|
| `.venv` → `tools/env` (symlink to a committed environment) | governance exit 0, exploit works | guard exit 1 |
| Dangling relative symlink | `uv sync` exit 2 (fails closed) | guard exit 1 |
| Symlink to a missing absolute path | `uv sync` exit 2 | guard exit 1 |
| Regular file | `uv sync` exit 2 | guard exit 1 |
| Gitlink (checkout makes an empty dir) | honest failure, exit 1 | guard exit 1 |
| `docs/.venv` | not used by uv | guard passes; not used, honest exit 1 |
| `.VENV` | not used by uv | guard passes; not used, honest exit 1 |
| No `.venv` (control) | honest exit 1 | guard exit 0, honest exit 1 |

### R5-02: submodule ignore settings — FIXED

**Correction.** `--ignore-submodules=none` is added to the `git status` call in `dirty_paths`.

**Reproduced on `b8bb5ac`** with the previous reviewer's `v_z01_submodule_report.py` (`out/v_z01_submodule_report_pre.txt`). With `submodule.vendor.ignore=all` or `diff.ignoreSubmodules=all`: `git status ''`, `2 passed`, `dirty=False dirty_paths=[]`, and `check_test_report` returns no problems.

**Refused on `0c21182`** (`out/v_z01_submodule_report_fix.txt`): both settings give `dirty=True dirty_paths=['vendor']` and `TEST_EVIDENCE_DIRTY`.

**Regression tests.** Both `test_r5_02_...` cases pass on the fix. On pre-fix code both fail with `AssertionError: assert 'sub' in []`.

**Boundary cases (`scripts/r5_02_boundary.py`).**
- **Coverage:** four kinds of change (worktree edit, untracked file, staged edit, new submodule commit), each against:
  - `submodule.sub.ignore` and `diff.ignoreSubmodules` set to none, untracked, dirty and all in `.git/config`;
  - `submodule.sub.ignore` set to untracked, dirty and all in a committed `.gitmodules`;
  - the combined cases.
- **`b8bb5ac`:** every combination that `git status` hides is also hidden from `dirty_paths`.
- **`0c21182`:** all 56 combinations give `dirty_paths=['sub']`.

**Honest states (`scripts/r5_02_honest.py`).** A clean submodule under each setting, a clone without `--recurse-submodules`, and a clone with it all give `[]`. So the fix adds no false "dirty".

### R5-03: Unicode case folding in the run URL — FIXED

**Correction.** The flags change from `re.I` to `re.I | re.A`. This is the only run-URL check in `src/`.

**Reproduced on `b8bb5ac`** with `v_z02_url_forms.py` (`out/v_z02_url_forms_pre.txt`):
- the U+0131 and U+0130 forms are `allowed=True`;
- the U+0131 URL could be applied, and `check after verification: 0 errors`.

**Refused on `0c21182`:** both forms give `CI_WRONG_REPOSITORY`, and the apply is refused. Every other form behaves as before: exact and upper-case ASCII are allowed; dot segments, percent-encoding, newline, query, fragment, attempt, userinfo, port, http and fullwidth digits are refused.

**Regression test.** `test_r5_03_...` passes on the fix. On pre-fix code it fails with `AssertionError: assert (not True)`.

**Boundary cases (`scripts/r5_03_boundary.py`).**
- **Exhaustive scan** of U+0080 to U+10FFFF for code points that match an ASCII letter:
  - under `re.I`: exactly 4 (U+0130→i, U+0131→i, U+017F→s, U+212A→k);
  - under `re.I | re.A`: 0;
  - none match `[0-9]` under either.
- **End to end**, with the sandbox repository renamed to `kis-owner/skik-repo` so that i, s and k all occur:
  - each of the four characters, and all four at once, is allowed on pre-fix and refused on the fix;
  - fullwidth i/I, Cyrillic і, I + combining dot (U+0307) and ß are refused on both;
  - exact, upper-case and mixed-case ASCII are still allowed on the fix.
- **Already-recorded URL:** a dotless-i URL committed at `b8bb5ac` is flagged by the `0c21182` checker: `exit 1 … ERROR CI_WRONG_REPOSITORY`.

## 3. Regression checks

On `0c21182`:

| Command | Exit | Output |
|---|---|---|
| `uv run pytest -q` | 0 | `404 passed in 322.42s (0:05:22)` (400 before + the 4 new R5 tests) |
| `uv run ruff check .` | 0 | `All checks passed!` |
| `uv run ruff format --check .` | 0 | `57 files already formatted` |
| `uv run mypy` | 0 | `Success: no issues found in 12 source files` |
| `uv run citerift-gov check` | 0 | `Consistency check: 0 errors, 0 warnings` |
| `uv run citerift-gov render-status --check` | 0 | `PROJECT_STATUS.md is up to date` |

- **Tree after the suite:** clean.
- **On `03631fc`:** the same commands give the same results, except `59 files already formatted`. I did not re-run pytest there because the code is identical.
- **Not run (needs network):** `uv lock --check`, pip-audit, and the real `checkout` and `setup-uv` actions.

## 4. Mutants

Run in the clean worktree `w-mut` at `0c21182` with `scripts/run_selected_mutants.py`, using the harness's own `_suite()`:

| Mutant | Result | Failing test |
|---|---|---|
| Baseline (unmutated) | PASS, `404 passed` | — |
| M97 | KILLED | `test_r5_02_...[submodule.sub.ignore]` |
| M98 | KILLED | `test_r5_03_...` |
| M99 | KILLED | `test_r5_01_...` |

The worktree was clean afterwards (`out/mutants_M97_M99.txt`).

## 5. New findings

**No new confirmed defect from the three fixes, and nothing release-blocking.**

**Residual near R5-02 (reproduced, not counted).** State inside the submodule's own repository can still hide a change, identically on `b8bb5ac` and `0c21182`:
- `--assume-unchanged` or `--skip-worktree` on a file inside the submodule hides an edit;
- `status.showUntrackedFiles=no` in the submodule's config hides an untracked file;
- in each case `dirty_paths=[]`.

This is local git state outside the superproject's checks, which RISKS.md R-004 already says is not bound, so it is outside this review. It needs a committed submodule, and the repo has none. If you don't treat it as covered by R-004, I would rate it low and not release-blocking: it is not the original exploit and the fix did not cause it.

**Observation, not a defect.** `test_r5_01` checks only the text order of the steps. It would not notice if `&& test ! -L .venv` were dropped. The case that part covers, a dangling symlink, still fails closed at `uv sync` (exit 2).

**Hypotheses, not reproduced.** uv might be pointed at a committed interpreter through other committed files, such as a path in `.python-version` or a `[tool.uv]`/`uv.toml` setting. RISKS.md R-016 already lists these inputs as uncovered, and in CI the `UV_PYTHON` env overrides `.python-version`. I did not test them.

**Out of scope, not assessed:** nothing noted.

**Privacy:** the repository account handle is written as `<repository account>` in every saved output. No personal names appear in `out/` or `scripts/` (grep checked).

## 6. Overall verdict

VERIFIED
