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

## 7. Confirmation campaign and complete verification matrix at `e6b3d7b` (owner instruction D-034, 2026-11-03)

Sections 1 to 6 describe the work of 2026-11-02 under D-033. This section is the release verification of D-034
(owner instruction section 10).

### 7.1 Revisions

| Role | Revision |
|---|---|
| Confirmation candidate, frozen in `0d46ba4` (`MANIFEST.json`) | `3e51792a38e227bd986bfbe63f16605d303c6d6c` |
| Complete verification matrix below | `e6b3d7b78dc2d6026923fc4da1c858925f827beb` |

`git diff 3e51792 e6b3d7b -- src schemas pyproject.toml uv.lock` is empty: the engine verified here is the engine
evaluated. Only documents and retained reports are added after `e6b3d7b`.

### 7.2 Matrix

Each suite ran in its own clean detached worktree of `e6b3d7b` (`git status --porcelain` empty before and after),
after `uv sync --locked --python <version>` (`run_suite.sh.txt`). The other checks ran in the main worktree at
`e6b3d7b` with an empty `git status --porcelain`. Reports: `final-checks/e6b3d7b/`.

| Check | Result |
|---|---|
| Complete suite, Python 3.12.3 (`python -P -m pytest -p no:cacheprovider --citerift-report`) | **1834 passed**, 0 failed or skipped, 532 s, exit 0 (`pytest-3.12.txt`) |
| Complete suite, Python 3.13.18 | **1834 passed**, 0 failed or skipped, 516 s, exit 0 (`pytest-3.13.txt`) |
| `citerift-gov check-report` on both reports (report copied to an untracked path in the clean worktree) | 0 problems each (`check-report-*.txt`) |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 316 files already formatted |
| `mypy` | no issues in 51 source files |
| `citerift-gov check`, `render-status --check` | 0 errors, 0 warnings; PROJECT_STATUS.md up to date |
| `uv lock --check` | consistent |
| `citerift.contracts.validate check-schemas` | 2 schemas checked, 0 problems |
| Dependency audit (`uv export --locked --all-groups`, `pip-audit --strict --disable-pip --require-hashes`) | No known vulnerabilities found |
| Protected paths against `94ac4f8` (Stage 00/02 code, `.github`, governance code and schemas, `GOVERNANCE.md`, `CLAUDE.md`) | no change (`protected-paths.json`) |
| Installed wheel (`uv build --wheel`; Python 3.12 venv with the hash-checked locked runtime dependencies; external schema copy; relocated bundles; `wheel_smoke.py.txt`) | SMOKE PASS. The module loads from site-packages. The three earlier cases pass as before; two confirmation-campaign bundles (ar-76524679, exit 6 `partial`; en-1383058278, retraction challenge) extract, verify and replay, and **both extractions are byte-identical** to the committed campaign predictions |
| Simulations: fetch policy 5000 / 20261028; reconciliation 200 / 20261028; campaign driver 2000 / 20261028 | 0 failures each; the first two byte-identical to the earlier outputs (SIMULATION_REPORT.md, 2026-11-03 addendum) |

The suite includes the security, negative, contract and schema, cross-language, Retry-After, worker-containment,
reproducibility, offline verify and replay and synthetic challenge (G11) tests by marker, and the campaign tools'
tests. Since `eca4389`, every test change is a new file under `tests/stage03/`; no test that existed at `eca4389`
was modified, skipped or removed.

### 7.3 Campaign evidence

| Item | Result | Evidence |
|---|---|---|
| Gates, adjudicated labels | ar: all G1-G7 pass. en: all pass except **G5c 0.869 < 0.95** | `evaluation/confirmation-2026-11/campaign/REPORT.md` section 4 |
| G8 verify / G10 replay | 54 / 54 exit 0 / 54 / 54 exit 0 at `3e51792` | `campaign/prediction/runs.json` |
| G9 acquisition | 54 / 54 complete | `campaign/capture/capture_states.json` |
| Score reproduction | `locked.json`, `adjudicated.json`, `challenge.json` byte-identical on re-run | `campaign/audit/EVIDENCE_AUDIT.json`, check 9 |
| Evidence integrity | 27 / 27 checks pass | `campaign/audit/EVIDENCE_AUDIT.json` |

### 7.4 GitHub CI

The run on the final pull-request head is given in the pull request #5 description and the owner handoff, because
a commit cannot contain its own CI run. Runs on intermediate heads of 2026-11-03 show `ci-gate` failures that are
cancellations by a newer push (for example run 41566509876 on `cfd10b2`: verify 3.13 success, verify 3.12
cancelled), not test failures.

### 7.5 What these results do not show

Engineering verification is complete at `e6b3d7b`. It is not scientific acceptance: English G5c is unmet
(`evaluation/confirmation-2026-11/DECISION_RECORD.md`), so no verification transition is recorded.

## 8. D-035 confirmation campaign and complete verification matrix at `6c499a7` (owner instruction D-035, 2026-11-03)

### 8.1 Revisions

| Role | Revision |
|---|---|
| Confirmation candidate, frozen in `b1e069e` (`evaluation/confirmation-d035/MANIFEST.json`) | `fff0e5b` |
| Complete verification matrix below | `6c499a724c6d690f72c1bd1caf2f1b5ea3befb55` |

`git diff fff0e5b 6c499a7 -- src schemas pyproject.toml uv.lock tests` is empty: the engine verified here is the
engine evaluated. Only campaign evidence and documents are added after the candidate.

### 8.2 Matrix

Each suite ran in its own clean detached worktree of `6c499a7` (`git status --porcelain` empty before and after),
after `uv sync --locked --python <version>` (`run_suite.sh.txt`). The other checks ran in the main worktree at
`6c499a7` with an empty `git status --porcelain`. Reports: `final-checks/6c499a7/`.

| Check | Result |
|---|---|
| Complete suite, Python 3.12.3 (`python -P -m pytest -p no:cacheprovider --citerift-report`) | **1972 passed**, 0 failed or skipped, 627 s, exit 0 (`pytest-3.12.txt`) |
| Complete suite, Python 3.13.18 | **1972 passed**, 0 failed or skipped, 580 s, exit 0 (`pytest-3.13.txt`) |
| By suite marker (both versions) | unit 531, integration 324, negative 844, regression 600, reproducibility 14, security 372, contracts 103, simulation 82 (`test-report-*.json`) |
| `citerift-gov check-report` on both reports | 0 problems each (`check-report-*.txt`) |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 345 files already formatted |
| `mypy` | no issues in 52 source files |
| `citerift-gov check`, `render-status --check` | 0 errors, 0 warnings; PROJECT_STATUS.md up to date |
| `uv lock --check` | consistent |
| `citerift.contracts.validate check-schemas` | 2 schemas checked, 0 problems |
| Dependency audit (`uv export --locked --all-groups`, `pip-audit --strict --disable-pip --require-hashes`) | No known vulnerabilities found |
| Protected paths against `94ac4f8` (Stage 00/02 code and tests, `.github`, governance code and schemas, `GOVERNANCE.md`, `CLAUDE.md`) | no change (`protected-paths.json`) |
| Installed wheel (`uv build --wheel`; Python 3.12 venv with the hash-checked locked runtime dependencies; external schema copy; relocated bundles; `wheel_smoke.py.txt`, `wheel_and_sims.sh.txt`) | SMOKE PASS. The module loads from site-packages. The three earlier cases pass as before. Three D-035 campaign bundles (`ar-9335702`, partial, no render; `en-1473997`, reserve block 2; `ar-10469946`, the G6b infobox article) extract, verify and replay, and **all three extractions are byte-identical** to the committed campaign predictions |
| Simulations: fetch policy 5000 / 20261028; reconciliation 200 / 20261028; campaign driver 2000 / 20261028 | 0 failures each; all three **byte-identical** to the runs at `e6b3d7b` (`sims-exit.txt`) |

**Test changes since the last externally reviewed head `f88bdd7`.** Every change is in `tests/stage03/`. New files:
`test_g5c_unit_semantics.py`, `test_g5c_review2.py`, `test_confirmation_d035_scripts.py`. Modified:
`test_wiki_mf1_tokenizer.py` (additions only: the MF-1 v3 classification tests) and
`fixtures/observed/expected.json` (the two expected extraction digests, which change with the engine version 1.1.0;
every other expected value is unchanged, `11bb5b2`). No test was skipped, removed or weakened.

### 8.3 Campaign evidence

| Item | Result | Evidence |
|---|---|---|
| Gates, adjudicated labels | en: every G1-G7 and minimum passes (G5c 0.994, G5d 0.994). ar: every gate passes except **G6b (2 false attachments, limit 1)** | `evaluation/confirmation-d035/campaign/REPORT.md` section 4 |
| G8 verify / G10 replay | 48 / 48 exit 0 / 48 / 48 exit 0 at `fff0e5b` | `campaign/prediction/runs.json` |
| G9 acquisition | 48 / 48 recorded; 47 complete, 1 partial (ar 23 / 24 with render) | `campaign/capture/capture_states.json` |
| G11 synthetic challenge | passes (part of the complete suite above) | `pytest-*.txt` |
| Score reproduction | `locked.json` and `adjudicated.json` byte-identical on re-run | `campaign/audit/EVIDENCE_AUDIT.json`, check 9 |
| Evidence integrity | 28 / 28 checks pass | `campaign/audit/EVIDENCE_AUDIT.json` |

### 8.4 GitHub CI

The run on the final pull-request head is given in the pull request #5 description and the owner handoff, because a
commit cannot contain its own CI run. The `ci-gate` run on `b8d9834` failed the Stage 00 secret scan; the cause and
its handling are in `evaluation/confirmation-d035/campaign/REPORT.md` section 6. Other runs on intermediate heads of
2026-11-03 that show `ci-gate` failures were cancelled by a newer push.

### 8.5 What these results do not show

Engineering verification is complete at `6c499a7`. It is not scientific acceptance: Arabic G6b is unmet because of a
verified engine defect (RISKS.md R-038; `evaluation/confirmation-d035/DECISION_RECORD.md`), so no verification
transition is recorded.

## 9. D-036 final confirmation and complete verification matrix at the delivery revision `b93314d` (owner instructions D-036 and D-038, 2026-11-09)

### 9.1 Revisions

| Role | Revision |
|---|---|
| Accepted main baseline, the only parent of the delivery revision | `94ac4f8df27383a03a810a4501ed1439bf8bcaea` |
| D-036 candidate, frozen in `10db8cb` (`evaluation/confirmation-d036/MANIFEST.json`) | `8901a597015b7c6d6eb8464554e79b4fa1383615` |
| Final head of the scientific record (branch `claude/project-thread-o4amfd`, continuing PR #5) | `80852e48732607129bdf7407480d417f588caf5d` |
| Delivery revision (branch `claude/stage03-delivery`), where the matrix below was run | `b93314dfde749a7cf977744a44b70a3a0d900ef2` |

`git diff 8901a59 b93314d -- src schemas pyproject.toml uv.lock tests` is empty: the engine verified here is the
engine evaluated (`src` tree `cda4a4b6`, `schemas` tree `360501fc`). `git diff --name-only 80852e4 b93314d` lists
only `governance/stage_registry.json` and `PROJECT_STATUS.md` (Stage 03 returned to `IN_PROGRESS` through
`citerift-gov`, because the candidate is not an ancestor on the delivery history). After `b93314d` only this
document, the verification record, the reports below, `HANDOFF.md`, `COMPLETION_CHECKLIST.md` and the registry change.

### 9.2 Matrix

The Python 3.12 suite ran in the delivery worktree at `b93314d` with an empty `git status --porcelain`
(`run_matrix.sh.txt`); its report is `test-report.json`. The Python 3.13 suite ran in a clean detached worktree of
`b93314d` after `uv sync --locked --python 3.13`, with the report written outside the tree (`run_suite.sh.txt`); its
report is `evidence/test-report-py3.13.json`. A first 3.13 run in the delivery worktree also passed (2051) but
records a dirty tree, because the 3.12 report was then an untracked file there; it is kept as
`pytest-3.13-first-run-dirty.txt` and is not used. The other checks ran in the delivery worktree at `b93314d`.
Reports: `final-checks/b93314d/`.

| Check | Result |
|---|---|
| Complete suite, Python 3.12.3 (`python -P -m pytest --citerift-report`) | **2051 passed**, 0 failed or skipped, 517 s, exit 0 (`pytest-3.12.txt`) |
| Complete suite, Python 3.13.18 (`python -P -m pytest -p no:cacheprovider --citerift-report`) | **2051 passed**, 0 failed or skipped, 484 s, exit 0 (`pytest-3.13.txt`) |
| By suite marker (both versions) | unit 531, integration 343, negative 874, regression 614, reproducibility 14, security 388, contracts 103, simulation 83 |
| `citerift-gov check-report` on both reports | 0 problems each (`check-report-*.txt`) |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 387 files already formatted |
| `mypy` | no issues in 52 source files |
| `citerift-gov check`, `render-status --check` | 0 errors, 0 warnings; PROJECT_STATUS.md up to date |
| `uv lock --check` | consistent |
| `citerift.contracts.validate check-schemas` | 2 schemas checked, 0 problems |
| Dependency audit (`uv export --locked --all-groups`, `pip-audit --strict --disable-pip --require-hashes`) | No known vulnerabilities found |
| Protected paths against `94ac4f8` (Stage 00/02 code and tests, `.github`, governance code and schemas, `GOVERNANCE.md`, `CLAUDE.md`) | no change (`protected-paths.json`) |
| Installed wheel (`uv build --wheel`; Python 3.12 venv with the hash-checked locked runtime dependencies; external schema copy; relocated bundles; `wheel_smoke.py.txt`, `wheel_and_sims.sh.txt`) | SMOKE PASS. The module loads from site-packages. The three earlier cases pass as before. Three D-036 bundles (`ar-10531419-a1`, partial; `en-32105383-a1`, reserve block 1, partial; `en-11579232-a1`, reserve block 1) extract, verify and replay, and **all three extractions are byte-identical** to the committed campaign predictions |
| Offline verify and replay of every D-036 prediction (no network namespace, `unshare -n`; `offline_verify_replay.py.txt`) | 44 / 44 verified, 44 / 44 replays reproduced (`offline-verify-replay.json`) |
| Simulations: fetch policy 5000 / 20261028; reconciliation 200 / 20261028; campaign driver 2000 / 20261028; template order 200 / 20261104 | 0 failures each; the first three **byte-identical** to the 2026-11-04 runs (`continuation/codex-d036-2026-11-04/sim-*.json`), the fourth byte-identical to `design/r038-reconciliation/simulation/template_order_sim.re-review-fixes.json` (`sims-exit.txt`) |
| Demonstrations (`demonstrations/run_demos.sh`, offline; `demos/transcript.txt`) | 57 operations: 52 exit 0 and 5 exit 6 (`partial`), 14 replays reproduced. Every demonstration document is byte-identical to `current-checks/current-demos/` except `demo5_extractions.json`, whose digests follow the engine version. One bundle, `en-1381772671`, is now `partial` instead of `complete` (15 `RENDER_NOTE_AMBIGUOUS` warnings, entries in one shared region): the R-038 design's documented change (`design/r038-reconciliation/DESIGN.md` section 11). Its extraction and three others are byte-identical to the R-038 differential (`differential/OUTPUTS.re-review-fixes.sha256`); the two fixture extractions have the digests in `tests/stage03/fixtures/observed/expected.json` |

**Test changes since the D-035 matrix `6c499a7`.** New: `tests/stage03/test_r038_template_output_order.py` and
`tests/stage03/test_confirmation_d036_scripts.py`. Modified: `tests/stage03/fixtures/observed/expected.json`, the two
expected extraction digests only (engine 1.2.0). No test was skipped, removed or weakened.

### 9.3 Campaign evidence

| Item | Result | Evidence |
|---|---|---|
| Gates, adjudicated labels | **Every G1-G11 gate and every minimum passes in both languages** (ar 24, en 20 articles) | `evaluation/confirmation-d036/campaign/REPORT.md` section 4 |
| G8 verify / G10 replay | 44 / 44 exit 0 / 44 / 44 reproduced at `8901a59`; again offline at `b93314d` | `campaign/prediction/runs.json`; `final-checks/b93314d/offline-verify-replay.json` |
| G9 acquisition | 44 / 44 recorded, each with source and render (ar 24 / 24, en 20 / 20); 2 extractions `partial` | `campaign/REPORT.md` section 4; `campaign/prediction/runs.json` |
| G11 synthetic challenge | passes (part of the complete suite above) | `pytest-*.txt` |
| Score reproduction | `locked.json` and `adjudicated.json` byte-identical on re-run | `campaign/audit/EVIDENCE_AUDIT.json` |
| Evidence integrity | 25 / 25 checks pass | `campaign/audit/EVIDENCE_AUDIT.json` |

### 9.4 GitHub CI

| Revision | Run | Result |
|---|---|---|
| `b93314d` (delivery, verified revision) | push https://github.com/ImanOthman-eng/citerift/actions/runs/42624868434 | success: `verify (python 3.12)`, `verify (python 3.13)`, `ci-gate` |
| `80852e4` (scientific record, final head) | push https://github.com/ImanOthman-eng/citerift/actions/runs/42624578687 | success |
| `1cd45a1`, `0ebcceb` (scientific record) | runs 42623565349, 42624522677 | failure: `ruff format --check` on `campaign/audit/evidence_audit.py` (layout only), fixed in `80852e4` |

The run on the commit that adds this section is given in the pull request description and the owner handoff,
because a commit cannot contain its own CI run.

### 9.5 What these results do not show

They verify the engine at `8901a59` and the D-036 evidence. They are not owner acceptance. The limits of the sample
(one vendor's AI labels, Arabic G2 decided by one adjudicated correction, English G5c's interval reaching 0.929, G7
vacuous in this sample) are in HANDOFF.md, "Known limitations".
