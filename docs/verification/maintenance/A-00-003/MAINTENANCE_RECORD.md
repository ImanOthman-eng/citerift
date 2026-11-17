# A-00-003: Stage 00 maintenance transaction (CI verify job timeout 20 → 30 minutes)

Owner authorization: owner decision OD-S12-2 in the Stage 04 Step 12 thread, 2026-11-17T18:45:34Z
(`cmsg_018VCB51nDHP6HXmLU4ea5yPQBMQAvkyRYvCrNmrZM88n8`): "APPROVED — increase the GitHub CI verify job timeout from 20
minutes to 30 minutes", "Change only: timeout-minutes: 20 to: timeout-minutes: 30 for the existing verify matrix job.
No other .github/ change is authorized by this decision." That message is the authorization; this file records what
was done under it. Decision record: DECISIONS.md D-065. Mechanism: the maintenance transaction of D-024 (model in
`docs/verification/maintenance/A-00-002/MAINTENANCE_MODEL.md`), unchanged; precedents A-03-001 and A-02-001. Stage 00
is not reopened and its acceptance (`0c21182e5871f772c3a76c75a1217c7641a63bbb`) is not rewritten.

## 1. Need [verified]

`.github/workflows/ci.yml` is a Stage 00 owned path: committing a change to it without an amendment makes Stage 00
`VERIFICATION_STALE` (checked: `citerift-gov check` reports 1 error on a commit holding only this change).

| Run | Commit | Python 3.12 test step | Python 3.13 test step | Result |
|---|---|---|---|---|
| 332 | `9499c49` (before the Step 12 corrections) | 10 m 16 s, 3187 passed | 11 m 29 s | green |
| 333 | `75e7b26` | 19 m 53 s, still running when the job hit 20 min | 17 m 07 s | cancelled |
| 334 | `00c2d6c` | 19 m 40 s, 3248 passed; job cancelled at 20 min during pip-audit | 11 m 28 s, 3248 passed | cancelled |

Per-file timings from the job logs (runs 332 and 334, Python 3.12.3 both): untouched Stage 00 to 03 test files ran a
median 1.89× slower in run 334; Stage 04 files 1.91×; in run 334 Python 3.12 against 3.13 on the same commit, 1.73×.
The new Step 12 test files take about 21 s on 3.13. The owner classified this as GitHub-hosted runner-speed variance,
not a Step 12 runtime regression.

## 2. Patch (candidate `0c643e66ec68aee8f9d5430e90b9baf4d4ae3fb4`)

One owned file, one line: `.github/workflows/ci.yml`, job `verify`, `timeout-minutes: 20` → `timeout-minutes: 30`.
The `ci-gate` job (5 min), the matrix (3.12, 3.13), every step, the tests and their assertions are unchanged.

## 3. Runtime policy (OD-S12-2)

18 minutes stays a diagnostic threshold, not a correctness gate: a required job over 18 minutes is recorded and
investigated; a run is not blocked solely for it when a runner-wide slowdown is demonstrated. The hard infrastructure
timeout is 30 minutes; a required job that reaches 30 minutes stops the work for an owner decision before any further
CI change, and so does evidence of a code-induced runtime regression (both Python versions regress after a change, the
slowdown localizes to new or modified tests or code, or comparable runners show sustained growth attributable to
Step 12). Slow runs are not classified as runner noise automatically. Nothing else changes: D-061, the ≤ 5 s p95
target, the Step 12 performance work, D-062/D-064 verification semantics, test completeness, zero skips and the full
Python 3.12 + 3.13 matrix.

## 4. Transaction record

| Step | Record |
|---|---|
| Baseline | `0c21182e5871f772c3a76c75a1217c7641a63bbb` (Stage 00 accepted revision; unchanged) |
| P (candidate) | `0c643e66ec68aee8f9d5430e90b9baf4d4ae3fb4`: `.github/workflows/ci.yml` only (one line). Against A-00-002's candidate `8b1db57`, every other Stage 00 owned path is identical (`git diff 8b1db57 0c643e6 -- <owned paths except .github/workflows>` is empty) |
| Scope | The mechanism compares the owned content with the accepted baseline (`_patch_problems`: "baseline plus exactly the declared patch", and the baseline must be the accepted revision), so a second transaction on Stage 00 declares the cumulative patch. A first `prepare` declaring only `ci.yml` was refused (`MAINTENANCE_PATCH_MISMATCH` for the eight A-00-002 files). The declared scope is therefore the eight A-00-002 files at their finalized content, unchanged, plus `ci.yml` (9 files, patch digest `b7389cbc45a0c1d2eec77fd97d56895972af681d3da3b313d1e5ebc2f926aeba`). No governance code was changed. |
| prepare | `citerift-gov maintenance prepare 00 --candidate 0c643e6… --path <9 files> --owner-ref cmsg_018VCB51nDHP6HXmLU4ea5yPQBMQAvkyRYvCrNmrZM88n8 …` gave A-00-003, `pending_validation`, recorded 2026-11-17T18:47:51Z; check: 0 errors, 1 warning (`MAINTENANCE_PENDING`) |
| V (validated) | `47bdbe2c025e8091567b58bc5608b17bc998819b`: the registry with the pending record, D-065 and this file; owned content identical to P |
| Python 3.12.3 | clean single-branch clone (`git clone --no-local --single-branch`), detached at V, environment from `uv.lock` (`uv sync --locked -p 3.12`), `PYTHONPATH=src python -P -m pytest -q -p no:cacheprovider --citerift-report …` (`validate.sh`): **3248 passed**, 0 skipped, exit 0, tree clean after the run (20 min 37 s). `test-report-py3.12.json`, SHA-256 `2e8439bc005191695defd726b4a065b5995f7185ae767d6911ecb1578ef39c34`; log `validation-py3.12.log` |
| Python 3.13.18 | the same, `uv sync --locked -p 3.13`: **3248 passed**, 0 skipped, exit 0, clean (18 min 54 s). `test-report-py3.13.json`, SHA-256 `0ac97cc7eb40c84e33594e2b6d76c2a2cfd595aefd182e3515339eb62f44ee1e`; log `validation-py3.13.log` |
| Suites (each report) | unit 632, integration 821, negative 1336, regression 663, reproducibility 30, security 412, contracts 242, simulation 245 (a test may carry several markers) |
| check-report | both reports: 0 problems at V |
| finalize | `citerift-gov maintenance finalize 00 A-00-003 --revision 47bdbe2… --report …py3.12.json --report …py3.13.json`: finalized 2026-11-17T19:28:51Z; check afterwards: 0 errors, 0 warnings; `render-status --check`: up to date |
| F (bookkeeping) | the commit that records the finalization, the reports, the logs, `validate.sh` and this table; no owned file changes after V |

The local wall times are this container's (4 vCPU, the two runs one after the other); they are not CI timings. The CI
run on F is the green-run requirement of OD-S12-2.
