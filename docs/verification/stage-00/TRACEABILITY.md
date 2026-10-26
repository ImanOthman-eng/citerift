# Stage 00 Requirements Traceability Matrix (correction A-00-001)

Revision traced: `0c21182e5871f772c3a76c75a1217c7641a63bbb`. Each row links a
Stage 00 requirement to the code that implements it, the tests that check it,
and the evidence in this directory. Test counts are collected test items
(parametrized cases counted) from `pytest --collect-only` at that revision:
404 in total. Suite membership comes from the markers in `tests/stage00/`; a
test can belong to more than one suite.

This matrix was added on 2026-10-26 at the owner's request for a traceability
check. It restates, in one place, links that the other documents in this
directory already make; it adds no new result.

## 1. Acceptance gates

The sixteen gates are those of `governance/stage_registry.json` (stage 00,
`acceptance_gates`). The gate evidence that the orchestrator checks is in
`verification-record.json`.

| Gate | Requirement | Implemented by | Verified by | Evidence |
|---|---|---|---|---|
| 00-A | Repository initialized safely with verified Git revision | `.gitattributes`; `gitutil.py` (git runs with replace refs and grafts disabled); ruleset definition `.github/rulesets/main-protection.json` | `test_repository.py` (17); `test_registry_tampering.py::test_copy_without_git_history_cannot_vouch_for_revisions`; `test_failure_simulation.py::test_shallow_clone_fails_closed_without_a_false_staleness_report` | HANDOFF.md "Verified Git commit" |
| 00-B | Reproducible engineering environment | `pyproject.toml`, `uv.lock` (unchanged since `741476c`), CI `uv sync --frozen` and `uv lock --check` | `test_repository.py::test_python_constraints_are_consistent`; reproducibility suite (5) | `test-report.json` (3.12.3), `test-report-python3.13.json` (3.13.14); `handoff/results-0c21182.json` (clean-clone install) |
| 00-C | Operational Project Orchestrator | `src/citerift/governance/orchestrator.py`, `model.py`, `cli.py` | `test_cli.py` (9); `test_integration_scenarios.py` (29); `test_unit_model_evidence_memory.py` (29) | TEST_RESULTS.md §1, §2; SPECIFICATION.md "Components" |
| 00-D | Persistent Project Memory | `governance/stage_registry.json`, its schema, `memory.py`, `PROJECT_STATUS.md`, `DECISIONS.md`, `RISKS.md` | `test_recovery.py` (3); `test_failure_simulation.py` (12); `test_registry_tampering.py` (23); `test_properties.py` (6) | TEST_RESULTS.md §1 to §3; handoff points 3 and 10 |
| 00-E | Orchestrator-Memory integration | `orchestrator.py` replay of the history against the records and memory files | `test_integration_scenarios.py` scenarios 08, 09, 10, 11; `test_repository.py::test_status_document_is_generated_from_registry` | TEST_RESULTS.md §2 |
| 00-F | Validated stage-transition rules | `model.py` (edge table), `orchestrator.py` (guards replayed per entry) | `test_simulation.py` (8); `test_unit_model_evidence_memory.py` transition tests; `test_corrections.py` F-04, F-05, X-10 tests | SIMULATION_REPORT.md; MATHEMATICAL_MODEL.md; `simulation/model-results.json`; `simulation/replay-conformance-full.json` |
| 00-G | Versioned data contracts with positive and negative tests | `schemas/contracts/v1/` (1.0.1), `src/citerift/contracts/` | contracts suite (87): `test_contracts.py` (82) and 5 in `test_corrections.py` | 3 valid fixtures, 52 invalid cases; `docs/data-contracts.md`; TEST_RESULTS.md §1 |
| 00-H | Completed relevant pre-implementation simulations | `simulations/stage00/state_machine_model.py`, `replay_conformance.py` | simulation suite (20) | SIMULATION_REPORT.md; `simulation/` |
| 00-I | Successful unit and integration tests | the whole package | unit (29), integration (141) | `test-report.json` |
| 00-J | Successful regression and consistency tests | `orchestrator.py` `check`; `pytest_report.py` | regression suite (214); fail-first runs | `fail-first/`; `test-report.json`; `check` 0 errors |
| 00-K | Successful GitHub Actions verification | `.github/workflows/ci.yml` (verify on 3.12 and 3.13, `ci-gate`) | `test_repository.py::test_workflow_hardening`, `::test_required_check_name_exists`, `::test_ci_runs_the_owned_sources_not_an_entry_point`; Y-08, Z-04, D4 and R5-01 CI tests in `test_corrections.py` | push run 40273320614 and pull_request run 40273323339 at `0c21182` (TEST_RESULTS.md §7); CI record in `verification-record.json` |
| 00-L | Effective branch protection verified | ruleset 25824038 `main-protection` (owner-created), file `.github/rulesets/main-protection.json` | `test_repository.py::test_branch_ruleset_definition`; read-back from the GitHub API | TEST_RESULTS.md §8. Limits: R-001, R-016 |
| 00-M | Security and adversarial review completed | every fix listed in RISK_ANALYSIS.md | security suite (202) | RISK_ANALYSIS.md; `review/` (six independent reviews); TEST_RESULTS.md §9 |
| 00-N | Creative Differentiation Review completed | CREATIVE_DIFFERENTIATION_REVIEW.md | structural check of the handoff by `orchestrator.py` | CREATIVE_DIFFERENTIATION_REVIEW.md |
| 00-O | Reproducible Stage 00 documentation and handoff | the seven artifacts and this directory | handoff simulation, 12 checks | HANDOFF.md; `handoff/results-0c21182.json` |
| 00-P | No known unresolved critical foundational defect | `memory.py` (critical defects block verification) | `test_integration_scenarios.py::test_open_critical_defect_prevents_verification` | RISKS.md: no open critical defect |

## 2. Verification requirements (SPECIFICATION.md, "Verification requirements")

Tests in `tests/stage00/test_corrections.py` are named after the finding they
reproduce (`test_f02_…`, `test_v02_…`, `test_x01_…`, `test_y09_…`,
`test_z01_…`, `test_r5_02_…`). The per-finding lists are in
`fail-first/README.md`.

| Requirement | Findings | Tests |
|---|---|---|
| 1. Every file in the verification directory pinned; gate evidence pinned and named by a plain path | F-02, V-02, X-01, S-01, Y-09 | `test_f02_*`, `test_v02_*`, `test_x01_*`, `test_s01_*`, `test_y09_*`; scenario 09 |
| 2. Stage definition and policy pinned; weak definitions refused | F-03 | `test_f03_*`; scenario 05b |
| 3. Policy, artifacts, executor and dependencies fixed by the schema | F-03, V-03, X-07 | `test_v03_*`, `test_x07_*`; `test_registry_tampering.py::test_dependency_graph_checks_still_hold_behind_the_schema` |
| 4. Complete test selection and clean tree | F-07, V-01, X-02, X-03, Y-01, Y-02, Y-03, Z-01, Z-05, R5-02 | `test_f07_*`, `test_v01_*`, `test_x02_*`, `test_x03_*`, `test_y01_*`, `test_y02_*`, `test_y03_*`, `test_z01_*`, `test_z05_*`, `test_r5_02_*`; scenarios 03, 04 |
| 5. CI record URL is the project's run URL; revision and success | Y-10, Z-02, R5-03 | `test_y10_*`, `test_z02_*`, `test_r5_03_*` |
| 6. Handoff, report and record read with duplicate-key rejection | F-18 | `test_f18_*`; `test_contracts.py::test_duplicate_json_keys_rejected` |

## 3. Persistent memory integrity rules (SPECIFICATION.md)

| Rule | Findings | Tests |
|---|---|---|
| 2. Replay against the transition guards | F-04, F-05, X-10 | `test_f04_*`, `test_f05_*`, `test_x10_*`; `test_simulation.py::test_history_replay_conforms_to_the_model_exhaustively` |
| 3. Ordering and future times | F-16, V-11 | `test_f16_*`, `test_v11_*` |
| 5. Records equal their history entry; owner references | F-17, V-07, V-09, X-13, Y-06, Y-07 | `test_f17_*`, `test_v07_*`, `test_v09_*`, `test_x13_*`, `test_y06_*`, `test_y07_*`; scenarios 06, 06b, 06c |
| 7. Hashes over the whole directory; line endings | F-02, F-12, V-12 | `test_f12_*`, `test_v12_*` |
| 8. Content-based drift; replace refs and grafts off; unknown changes reported | F-01, F-19, V-13, X-09, Z-03 | `test_f01_*`, `test_f19_*`, `test_v13_*`, `test_x09_*`, `test_z03_*` |
| 9. Memory records parsed strictly | F-06, V-06, V-10, X-06, Y-04 | `test_f06_*`, `test_v06_*`, `test_v10_*`, `test_x06_*`, `test_y04_*`; `test_unit_model_evidence_memory.py` memory tests |
| 11. Source tree | X-04 | `test_x04_*`; `test_repository.py::test_ci_refuses_modules_beside_the_package_before_running_python` |
| 12. Enhancements keep the contracts | X-13 | `test_x13_*`; scenario 12 |
| 13. Damaged inputs give named errors | X-05, Y-11 | `test_x05_*`, `test_y11_*`; `test_properties.py::test_random_byte_damage_never_crashes` |

## 4. The twelve mandatory integration scenarios

All in `tests/stage00/test_integration_scenarios.py`, each in a fresh git
sandbox: `test_01_*` authorization, `test_02_*` verified but not accepted,
`test_03_*` missing tests, `test_04_*` failed or untrustworthy tests,
`test_05_*` incomplete handoff, `test_06_*` missing owner acceptance,
`test_07_*` unauthorized next stage, `test_08_*` conflicting records,
`test_09_*` missing or stale evidence, `test_10_*` recovery from the
repository alone, `test_11_*` evidence-supported correction, `test_12_*`
enhancement preserving contracts.

## 5. Findings to regression tests

Every finding that reproduces a behavior has a test that fails on the
revision it was reported against and passes at `0c21182`:

| Findings | Fail-first run | Per-finding table |
|---|---|---|
| F-01 to F-19 | `fail-first/results-ae2ce9e.txt` | `fail-first/README.md` |
| V-01 to V-16 | `fail-first/results-135e4ac.txt` | `fail-first/README.md` |
| X-01 to X-13 | `fail-first/results-7138d6d.txt` | `fail-first/README.md` |
| Y-01 to Y-13 | `fail-first/results-4a396fb.txt` | `fail-first/README.md` |
| Z-01 to Z-05 | `fail-first/results-97b2051.txt` | `fail-first/README.md` |
| R5-01 to R5-03 | `fail-first/results-b8bb5ac.txt` | `fail-first/README.md` |

Each rule added for a finding also has a mutant in
`mutation/mutation_check.py` (M1 to M99) that a test kills
(`mutation/results-0c21182.txt`).

## 6. Not traced to a test

- Document content (structure is checked, wording is not).
- The GitHub-side behavior of the ruleset (read back, not exercised by a push
  to `main`).
- The trust boundaries in RISKS.md R-001 to R-004 and R-016: tests show the
  checks behave as specified, not that the boundary is secure.
