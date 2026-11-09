# Stage 04 registry definition (owner decision D-1)

Owner decision D-1 of 2026-11-09 (`cmsg_018VCB51nDHP6HXmLU4ea5yPRpb2tWYwbQwCYA5ps9aLth`, DECISIONS.md D-040): one
manual edit of the Stage 04 definition, because `citerift-gov` has no command that defines a stage's owned paths,
test suites or gates. It is a controlled Stage 04 initialization, not a general permission to edit governance state.

## What changed

Only three fields of Stage 04 in `governance/stage_registry.json`:

| Field | Before | After |
|---|---|---|
| `owned_paths` | `[]` | `src/citerift/investigation`, `schemas/investigation`, `tests/stage04`, `simulations/stage04` |
| `required_test_suites` | `unit, integration, negative, regression` | `unit, integration, negative, regression, reproducibility, security, contracts, simulation` (as Stages 02 and 03) |
| `acceptance_gates` | 04-A | 04-A unchanged, plus 04-B to 04-J (wording in `stage04_definition.py` and the registry) |

Not changed (verified by `stage04_definition.py verify`): Stage 04 `authorization`, `status`, `implementation`,
`verification`, `acceptance`, `blockers`, `amendments`, `name`, `executor`, `depends_on`, `verification_dir`; every
other stage; `policy`, `project` and `history`.

Required artifacts: the registry schema fixes them for every engineering stage (`required_artifacts` must equal the
seven documents; the policy names them and `test-report.json`). Stages 02 and 03 do not repeat them in their
definitions, so Stage 04 does not either; nothing to add.

`PROJECT_STATUS.md` is written only by `citerift-gov render-status --write`. The rendered status does not show
definition fields, so the file is byte-identical before and after (see the diff).

## Procedure

1. `python stage04_definition.py apply <root>`: refuses unless Stage 04 is `IN_PROGRESS` and the three fields are in
   the expected prior state; writes the registry with citerift-gov's serialization.
2. `citerift-gov render-status --write`, then `render-status --check`.
3. `python stage04_definition.py verify <root> <registry before>`: unchanged fields, ownership collisions against
   every other stage's owned paths and verification directory (component-wise containment both ways), no tracked file
   already under a new owned path.
4. JSON Schema validation of the registry against `schemas/governance/stage_registry.schema.json`.
5. `citerift-gov check`.
6. Full test and static matrix (Python 3.12 and 3.13, ruff check and format, mypy).

The verifier was also run against a deliberately wrong edit in a scratch worktree (a Stage 03 field changed, Stage 04
status changed, a path inside `src/citerift/wiki` added) and reported all four problems with `RESULT: FAIL`.

## Results

`registry.diff` is the exact `git diff` of the edit. `verification.log` holds the output of steps 2 to 5. The matrix
results are in `../PLANNING_RECORD.md`.
