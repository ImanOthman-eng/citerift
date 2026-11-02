# Stage 03 test results

Project owner: EVE TELOS. Executor of this document: Claude Code (owner instruction of 2026-11-02, DECISIONS.md D-033).
Earlier test evidence by Claude Code (to 2026-10-29) and ChatGPT/Codex (2026-10-30 to 2026-10-31) stays in
`current-checks/`, `review/` and `evaluation/`. It is not restated here as this executor's runs.

## 1. Revisions

| Role | Revision |
|---|---|
| Accepted main baseline | `94ac4f8df27383a03a810a4501ed1439bf8bcaea` |
| Frozen production candidate (the single final prediction run) | `48cfeab2c093ea0e853fe2ccb2cd1d5ff87a528b` |
| Last head before this work (`src` and `schemas` equal to `48cfeab`) | `d151507504bc1157ba92dc90541ccf4ec70868ab` |
| Final code, where the complete verification matrix below was run | `8c6fe9f80bc6557bb48ca36e9d7003b3f897c142` |

Only documents and retained reports are added after `8c6fe9f`. The GitHub CI run on the final pull-request head is
listed in section 3.

## 2. Complete verification matrix at `8c6fe9f` (clean worktrees, 2026-11-02)

Each command was run on a clean detached worktree of `8c6fe9f` (`git status --porcelain` empty), after
`uv sync --locked`. Reports are in `final-checks/8c6fe9f/`.

| Check | Command | Result |
|---|---|---|
| Complete suite, Python 3.12.3 | `.venv/bin/python -m pytest -p no:cacheprovider --citerift-report test-report-3.12.json` | **1690 passed**, 0 failed or skipped, 551 s, exit 0 (`pytest-3.12.txt`, `test-report-3.12.json`) |
| Complete suite, Python 3.13.18 | same, on Python 3.13 | **1690 passed**, 0 failed or skipped, 513 s, exit 0 (`pytest-3.13.txt`, `test-report-3.13.json`) |
| Governance test-report check | `citerift-gov check-report` on both reports | 0 problems for each report, checked in a clean worktree at `8c6fe9f` with the report on an untracked path (`check-report-*.txt`) |
| Lint | `uv run ruff check .` | All checks passed (exit 0) |
| Format | `uv run ruff format --check .` | 266 files already formatted (exit 0) |
| Types | `uv run mypy` | no issues in 51 source files (exit 0) |
| Governance | `uv run citerift-gov check` | 0 errors, 0 warnings (exit 0) |
| Lock | `uv lock --check` | consistent (exit 0) |
| Dependency audit | `uv export --frozen --no-emit-project --all-groups`, then `pip-audit --strict --require-hashes --disable-pip -r` | No known vulnerabilities found (exit 0) |
| Protected paths | `git diff --name-only 94ac4f8 8c6fe9f -- <Stage 00/02 paths, .github, GOVERNANCE.md, CLAUDE.md>` | no change (`protected-paths.json`) |
| Installed wheel | `uv build --wheel`, a Python 3.12 venv with the locked runtime dependencies (hash-checked) and the wheel, `CITERIFT_SCHEMAS` = external copy, relocated bundles (`wheel_smoke.py`) | PASS: the module was imported from site-packages. ar observed: extract partial (6), verify 0, replay reproduced. en observed: 0 / 0 / reproduced. The RF-60 Wiley bundle: 0 / 0 / reproduced, key `10.1111/0004-5608.00043`. |
| Simulations | `simulations/stage03/fetch_policy_sim.py 5000 20261028`; `reconcile_perturbation_sim.py 200 20261028` | 0 failures. Output identical to 2026-10-30 (`final-checks/sim-*.json`). |

The complete suite contains the contract and schema, security, negative, reproducibility, simulation and
synthetic challenge (G11) tests by marker. A complete run of every committed test with no failure covers all of them.

## 3. GitHub CI

| Revision | Run | Result |
|---|---|---|
| `8c6fe9f` (final code) | push https://github.com/ImanOthman-eng/citerift/actions/runs/41447945211 and pull request https://github.com/ImanOthman-eng/citerift/actions/runs/41447954078 | success (Python 3.12 and 3.13) |
| `949cdc4` (RF-60) | push https://github.com/ImanOthman-eng/citerift/actions/runs/41446299843 and pull request https://github.com/ImanOthman-eng/citerift/actions/runs/41446310477 | success |
| final pull-request head (this document's commit) | given in the pull request #5 description and the owner handoff message, because a commit cannot contain its own CI run | — |

## 4. Evaluation evidence (frozen candidate, final campaign)

| Item | Result | Evidence |
|---|---|---|
| Locked scores reproduce with the frozen scorer | identical, field by field | `evaluation/final/run/scores_adjudicated.json` (`locked` sections) against `scores_locked.json` |
| Adjudicated gates | ar G5a 0.914 fail; ar identifiers 33 < 50; en G2 0.0192 fail; every other gate passes | `evaluation/final/adjudication/README.md` |
| G8 verify / G10 replay at `48cfeab` | 32 / 32 exit 0 / 32 / 32 exit 0 | `evaluation/final/adjudication/verify_replay_frozen_48cfeab.json` |
| G9 acquisition | 32 / 32 complete | `evaluation/final/capture/capture_states.json` |
| Verify / replay at `949cdc4` (RF-60) | 32 / 32 verify. Replay differs for en-1377523963 only, as expected. | `verify_replay_rf60_949cdc4.json` |
| Post-exposure re-extraction (not a gate) | 31 documents byte-identical. en G2 0.000 on exposed data; ar unchanged. | `evaluation/final/post-exposure-rf60/` |

## 5. Fail-first regressions of this work

| Finding | Before | After | Evidence |
|---|---|---|---|
| RF-60 (page-view route in a publisher DOI key) | at `d151507`: 11 failed, 6 controls passed | 17 passed | `review/failfirst/rf-60/` |
| R5: RV-1, RV-2, RV-7, RV-8, RV-10 | at `949cdc4`: the 10 new cases failed, 17 passed | 27 passed | `review/round-5/pytest-before-949cdc4.txt` |
| Real-bundle impact (70 retained real bundles, exposed, regression only) | — | RF-60 changes 1 document (en-1377523963). R5 changes none. | `review/failfirst/rf-60/real_bundles_impact.json` |

No existing test was modified, skipped or removed by this work. The only test change is the new file
`tests/stage03/test_wiki_rf60_page_view_segment.py`.

## 6. What these results do not show

- The complete suite and CI show engineering consistency. They are not scientific acceptance. Gate 03-G is not met
  (`evaluation/final/DECISION_RECORD.md`).
- RF-60 is evaluated only on exposed and synthetic data.
- Only Linux was exercised. Browser visibility is never evaluated.
