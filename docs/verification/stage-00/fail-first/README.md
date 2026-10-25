# Fail-first evidence for correction A-00-001

`results-ae2ce9e.txt` is the result of running the corrected test suite
against the code and schemas of `ae2ce9e`, the revision at which Stage 00 was
reopened. A regression test counts only if it fails there and passes after
the correction.

How it was produced on 2026-10-25:

    git worktree add --detach $W ae2ce9e
    rm -rf $W/tests/stage00 && cp -a tests/stage00 $W/tests/stage00   # corrected tests, old code
    cd $W && PYTHONPATH=$W/src python -m pytest -p no:cacheprovider -q -rf tests/stage00

Result: 82 failed, 178 passed. The 178 passing tests are the unchanged
suite plus the controls, such as `test_f12_..._does_not_change_evidence_hashes[False]`.
The same suite passes completely on the corrected revision (TEST_RESULTS.md).

| File | Failing at `ae2ce9e` | Why it fails there |
|---|---|---|
| `test_corrections.py` | 51 (every F-01 to F-20 and F-23 test except one control) | the defect each test reproduces |
| `test_contracts.py` | 19 | F-08, F-09, F-10, F-18: invalid records accepted, patterns differing from ECMA-262, impossible dates accepted, duplicate keys |
| `test_failure_simulation.py` | 4 | F-13 traceback on a damaged registry (3); false `VERIFICATION_STALE` in a shallow clone (1) |
| `test_properties.py` | 4 | the old record has no `evidence_manifest` to mutate (2); damaged registry raised `JSONDecodeError` (2, F-13) |
| `test_simulation.py` | 2 | F-11 differential case; replay conformance (2,458 disagreements in the small configuration) |
| `test_integration_scenarios.py` | 1 | `test_08` now requires `RECORD_HISTORY_MISMATCH` (F-17) |
| `test_recovery.py` | 1 | the old CLI fails on a record with the new required field `evidence_manifest` |

Two of the failures come from the new record format, not from a defect: the
two `test_properties.py` mutation cases, and `test_recovery.py`. They show
that the old code cannot read the new evidence, not that it accepts a
violation. They are listed so that the count is complete.

Defect N-01 was found during this correction, after the reviewed audit. Its
test (`test_n01_files_git_ignores_are_not_evidence`) failed on `ee46423`
before its fix in `373045d`. It is not in this file, because `ae2ce9e` has no
evidence manifest at all.
