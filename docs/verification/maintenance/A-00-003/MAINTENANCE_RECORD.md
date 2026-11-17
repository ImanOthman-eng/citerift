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

Filled in after validation.
