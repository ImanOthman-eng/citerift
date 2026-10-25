# Stage 00 Simulation Report (correction A-00-001)

All results here are **simulated**: over the abstract model, over synthetic
sandbox repositories, or over fault injection. They show whether the
governance design and its implementation behave as specified. They are not
empirical results about Wikipedia, citations or retractions. Stage 00 produces
none of those, and no scientific source data was created.

Raw outputs are files in this directory, pinned by the evidence manifest of
the verification record.

## 1. Abstract model, re-run

`simulations/stage00/state_machine_model.py` has not changed since `741476c`.
It was re-run at `{{RVER7}}` with the default seed 20261025:

```
uv run python simulations/stage00/state_machine_model.py --output simulation/model-results.json
```

The output is byte-identical to the accepted `final-results.json`. Both files
have sha256 `55ed9851ea007d4fb10253aad1a6cfe733c474dbc876097d6923e2985dcb2ff0`.

| Analysis | Result |
|---|---|
| Exhaustive reduced model (4 stages) | 490 nodes, 1,756,160 attempts, 106,400 permitted, **0 violations** |
| Random walks, full 10-stage graph | 4,000,000 attempts, 263,926 permitted, **0 violations** |
| Guided completion | all 10 stages reach AC in 50 moves |

The iteration-1 defect (D-016) is still re-found when its rule is
re-introduced (`test_simulation.py`).

## 2. History replay conformance, exhaustive (new)

`simulations/stage00/replay_conformance.py` checks that `check` accepts
exactly the histories the model permits, one move beyond every reachable
state. The method is in MATHEMATICAL_MODEL.md §5.

| Run | Revision | Cases | Disagreements | Output |
|---|---|---|---|---|
| full config | `{{RVER7}}` | 205,632 | **0** | `simulation/replay-conformance-full.json` |
| full config, before the correction | `ae2ce9e` | 205,632 | **12,872** | `simulation/replay-conformance-full-ae2ce9e.json` |
| small config (in the test suite) | every CI run | 45,024 | 0 | `test_history_replay_conforms_to_the_model_exhaustively` |
| small config, before the correction | `ae2ce9e` | 45,024 | **2,458** | `simulation/replay-conformance-small-ae2ce9e.json` |

The 12,872 disagreements at `ae2ce9e` are histories the model refuses but the
old replay accepted. Examples: authorizing a stage with unaccepted
dependencies, reopening without an amendment, two stages active at once.
They are the measurable form of F-04 and F-05.

## 3. Model versus implementation, differential (extended)

`test_differential_model_vs_implementation` drives the model and
`Orchestrator.propose` with the same random moves, for seeds 7 and 20261025
with 200 moves each. It requires identical permit and refuse decisions, at
least 40 permitted moves and at least 8 distinct edges. A fixed case was
added for F-11: reopen Stage 00 after Stage 02 was accepted. The model always
allowed it. The old implementation refused it, and the corrected one allows
it (`test_differential_fixed_case_reopen_foundation_after_dependent_accepted`).
The differential test now uses a new owner reference for every owner move,
because reuse is refused (F-17).

## 4. Failure simulations (new)

`tests/stage00/test_failure_simulation.py`, each in a fresh sandbox:

| Fault | Injected how | Result |
|---|---|---|
| Write interrupted mid-file | `fdopen` writes half, then raises | old registry intact, no temp file left, `check` clean |
| Rename fails | `os.replace` raises | same |
| Process killed before rename | real subprocess, `os._exit(9)` | old registry intact; one temp file left, ignored by `check`; next transition succeeds |
| Crash between registry and status writes | second write raises | `check` reports only `STATUS_DOC_OUT_OF_DATE`; `render-status --write` recovers |
| Corrupted registry: truncated, empty, bad enum, wrong type, BOM | file damaged | exit 1, no traceback; `git checkout` restores; `check` clean |
| Transition applied but never committed | clone of the last commit | clone shows the committed state; local `recover` lists the uncommitted file |
| Session lost during a correction cycle | fresh `Orchestrator` from disk at every step | reopen, implement, verify again; recover shows the new revision |
| Shallow clone | `--depth 1` | `REVISION_NOT_FOUND` with a "shallow" hint; no false `VERIFICATION_STALE` |

Seeded property tests (`test_properties.py`, seeds 11 and 20261025) cover two
more cases. 19 mutation classes of an accepted registry are all detected. And
random byte damage (25 cases per seed) always ends with exit 0 or 1, never an
exception.

## 5. Handoff simulation, 10 points (new)

`handoff/handoff_simulation.py REVISION OUTPUT` clones the repository at the
revision into a temporary directory. It installs the locked environment
offline, then acts as a later-stage engineer with a minimal environment. No
inherited variable is kept except `PATH` and the uv cache.

| # | Point | Check |
|---|---|---|
| 1 | Clean checkout | `HEAD` equals the revision; tree clean |
| 2 | Orchestrator usable | `status` and `check` run; 0 errors |
| 3 | Persistent memory usable | `recover --json` gives state, open risks and next actions with no consistency error |
| 4 | Contracts usable | `check-schemas`; the three valid fixtures validate |
| 5 | Dependencies enforced | owner authorization of Stage 02 refused with `DEPENDENCY_NOT_ACCEPTED` |
| 6 | Approval gates enforced | agent self-authorization, owner without reference, and agent self-acceptance all refused |
| 7 | Synthetic downstream consumer | a Stage 02-style schema outside the owned paths reuses v1 definitions; a valid record passes and four invalid ones are rejected; `check` stays clean |
| 8 | No hidden dependency | `uv sync --locked` from the lock file alone; the CLIs run with `python -I` |
| 9 | Clear diagnostics | truncated registry gives `REGISTRY_UNREADABLE`; a forged actor gives a named error; no traceback |
| 10 | Recovery does not change state | registry and status document byte-identical after `recover`; state intact after the simulation |

Result at `{{RVER7}}`: `handoff/results-{{RVER7}}.json`, {{HANDOFF_PASSED}}.

## 6. What the simulations do not cover

- Whether real evidence is truthful, or whether an `owner_ref` contains
  approval (R-002).
- Histories longer than 28 entries or other dependency shapes, exhaustively.
  Ten stages are covered only by sampling and the guided path.
- Concurrency: the orchestrator is a single-writer library. Git serializes
  writers, and a conflicting registry merge fails `check`.
- The GitHub side of R-016. A pull request that edits the workflow was not
  exercised on GitHub, because doing so would mean pushing a weakened
  workflow.
