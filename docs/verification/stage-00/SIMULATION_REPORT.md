# Stage 00 Simulation Report

All results below are **simulated**, over the abstract model in
`simulations/stage00/state_machine_model.py` with synthetic guard inputs. They
say whether the governance rule design is sound. They are not empirical
results about Wikipedia, citations or retractions, and Stage 00 produces none.

The model imports nothing from `citerift`; it was written from the
mathematical model (MATHEMATICAL_MODEL.md) before the orchestrator.

## Raw results

| File | sha256 | Content |
|---|---|---|
| `simulation/iteration-1-results.json` | `d225f9d6b7f5a97e99f2ad34b54e1d99081d9bc972316d6c276e2f2039c706a5` | first design, before the fix |
| `simulation/final-results.json` | `55ed9851ea007d4fb10253aad1a6cfe733c474dbc876097d6923e2985dcb2ff0` | corrected design |

Reproduce: `uv run python simulations/stage00/state_machine_model.py --output out.json`
(defaults: 20,000 walks of length 200, seed 20261025). Re-run on 2026-10-25 at
revisions `ecaa845`, `2bf7d60` and `30e4462`: output identical to
`final-results.json` each time (compared as parsed JSON), runtime about 17.5 s
on 4 vCPU. The only change to the model file after the results were recorded is
a corrected path in its docstring (`2bf7d60`).

## Iteration 1: defect found

Exhaustive search of the reduced model (engineering chain 0→1→2 plus an
independent external stage 3, adversarial actor and inputs):

| Measure | Value |
|---|---|
| Reachable nodes | 1,141 |
| Transition attempts | 4,089,344 |
| Permitted / rejected | 387,968 / 3,701,376 |
| Invariant violations | **279,664**, all I3 (more than one active engineering stage) |
| All-accepted reachable | yes |

Shortest counterexample (12 moves, minimal because the search is breadth-first):

1. stage 0: NS→AU→IP→IM→VA→AC (5 moves, owner where required)
2. stage 1: NS→AU→IP→IM→VA (4 moves)
3. stage 0: AC→IP (owner reopen; stage 1 is VA, not active, so it was allowed)
4. stage 1: VA→IP (rework) → stages 0 and 1 both active. **VIOLATION I3.**

Root cause: the single-active rule was attached to authorize and reopen only.
VA→IP also enters the active set. Fix: apply the rule to every edge that
enters the active set from outside it (DECISIONS.md D-016). The implementation
enforces it as a state invariant (`MULTIPLE_ACTIVE_STAGES`) checked on every
proposed successor state, which covers any edge added in future.

The seeded random walks of iteration 1 (4,000,000 attempts, 44,607 permitted)
reported **0 violations**: random sampling missed the defect, because reaching
it needs one stage accepted and a second one verified, which a uniform walk
rarely does (the maximum in iteration 1 was 1 stage accepted per walk). This is
why the exhaustive search, not the random walks, is the primary evidence.

## Final iteration: corrected design

| Analysis | Result |
|---|---|
| Exhaustive reduced model | 490 nodes, 1,756,160 attempts (106,400 permitted), **0 violations**, all-accepted reachable, AC entered only from VA |
| Random walks, full 10-stage graph | 20,000 walks × 200 = 4,000,000 attempts, 263,926 permitted, **0 violations**, 0 authorizations without owner, at most 2 stages accepted in one walk |
| Guided completion, full graph | all 10 stages reach AC in 50 moves (no deadlock of legitimate progress) |

After iteration 1 the walk was changed so that half of the attempted targets
are drawn from the edges that exist from the current state (shaped sampling)
and half are arbitrary. That raised the permitted moves from 44,607 to 263,926
and the depth reached from 1 to 2 accepted stages. The walks still cover deep
states poorly; the exhaustive search does not have this weakness, but only for
4 stages.

## Model versus implementation

`tests/stage00/test_simulation.py::test_differential_model_vs_implementation`
drives the model and `Orchestrator.propose` with the same random moves in a
sandbox repository and requires identical permit/reject decisions.

| Seed | Attempts | Disagreements | Permitted | Distinct edges exercised |
|---|---|---|---|---|
| 7 | 200 | 0 | 56 | 8 of 11 |
| 20261025 | 200 | 0 | 54 | 9 of 11 |

The sandbox uses the real Stage 00 to 03 shape (02 and 03 depend on 00 and 01;
01 is external). Per-seed counts were re-measured on 2026-10-25 by running a
scratch copy of the test with a print added; the committed test asserts 0
disagreements, at least 40 permitted moves and at least 8 distinct edges.

The same file also re-runs the exhaustive reduced search and the guided
completion, checks that the model's edge table equals the implementation's,
and re-introduces iteration 1's rule for VA→IP to require that the search finds
the I3 violation, so a regression to the old design would be caught.

## What the simulation does not cover

- Whether real evidence files are truthful, or whether an `owner_ref` contains
  approval (R-002).
- Hand edits of the registry: those are covered by the consistency check
  (history replay, record coherence, hashes), tested in
  `test_integration_scenarios.py`, not by transition guards.
- Stage counts above 4 exhaustively; 10 stages are covered only by sampling and
  the guided path.
- Concurrency: the orchestrator is a single-writer library; two writers at once
  are serialized by git, and a conflicting registry merge would fail the check.
