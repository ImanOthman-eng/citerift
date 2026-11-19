# Stage 04 final closure audit, item 14: full test matrix

Revision tested: `6daedeefeea0dd2ffd0be6bb24e01ae7ad36ac12` (the audit record; its tree is the closure candidate plus
`AUDIT.md` and its evidence files). Every run is the whole suite with no narrowing option, written to a test report
and checked with `citerift-gov check-report` (complete run of a clean tree).

| Run | Result |
|---|---|
| Local, Python 3.12.3 (repository environment) | 3,421 passed, 0 failed, 0 skipped in 1,328 s; report at `6daedeefeea0`: 0 problems (`evidence/pytest_py312_at_6daedee.txt`) |
| Local, Python 3.13.18 (separate locked environment, detached worktree at the same revision) | 3,421 passed, 0 failed, 0 skipped in 1,240 s; report at `6daedeefeea0`: 0 problems (`evidence/pytest_py313_at_6daedee.txt`) |
| GitHub CI run 382 (`44599876248`) | success: `verify (python 3.12)`, `verify (python 3.13)` (governance and memory consistency, lockfile, ruff, format, mypy strict, schema validation, full tests, test-report check, no changed files, `pip-audit --strict`) and `ci-gate` |

The oracle suites (`test_corrective_oracle.py` for dt-2, `test_simulation_step4.py` and `test_step9_b8.py` for the
frozen dt-1 oracle) are part of these runs.

Note: the first local runs on the closure candidate `49c7a58` were stopped after one failure,
`test_documented_links_exist`, because `HANDOFF.md` linked `final-closure/AUDIT.md` before that file existed; CI run
381 on `49c7a58` was cancelled by the next push. `6daedee` adds the file; no test was changed, skipped or narrowed.
