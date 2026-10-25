# Development Setup

## Requirements

- Python 3.12 (baseline) or 3.13. Decision: DECISIONS.md D-001.
- uv 0.11 (CI pins 0.11.32). Install: https://docs.astral.sh/uv/getting-started/installation/
- git with full history (revision checks need it; a shallow clone is reported
  as an error, not silently accepted).

## Setup

```bash
git clone https://github.com/ImanOthman-eng/citerift.git
cd citerift
uv sync --locked          # exact versions from uv.lock, into .venv
```

`--locked` fails if `pyproject.toml` and `uv.lock` disagree, so an environment
is never silently re-resolved. After changing dependencies run `uv lock` and
commit both files.

## Everyday commands

```bash
uv run pytest                                  # all tests
uv run pytest -m negative                      # one suite (unit, integration, negative,
                                               # regression, reproducibility, security,
                                               # contracts, simulation)
uv run ruff check . && uv run ruff format --check .
uv run mypy                                    # strict type check of src/
uv run citerift-contracts check-schemas        # meta-validate all contract schemas
uv run citerift-gov check                      # governance consistency (CI runs this)
uv run citerift-gov status
uv run citerift-gov recover                    # full state reconstruction
python simulations/stage00/state_machine_model.py --output sim.json
```

## Producing stage test evidence

Commit first, then run from a clean tree:

```bash
uv run pytest --citerift-report docs/verification/stage-NN/test-report.json
```

The report records the commit and whether the tree was dirty. The orchestrator
only accepts a report produced at the verified revision from a clean tree.

## Recording stage state

```bash
uv run citerift-gov transition 00 IMPLEMENTED_NOT_VERIFIED --actor engineering-agent \
    --reason "..." --revision <full sha>              # dry run
uv run citerift-gov transition ... --apply          # write registry + PROJECT_STATUS.md
```

Commit `governance/stage_registry.json` and `PROJECT_STATUS.md` together.

## Cloud environment notes

The CITERIFT cloud container is temporary. Push everything that matters. The
container has no GPU and no Docker daemon. Wikimedia endpoints rate-limit this
environment (HTTP 429); see RISKS.md R-008.

## Branch workflow

`main` is protected (ruleset: pull request required, `ci-gate` must pass, no
force-push, no deletion). Work on a branch, open a pull request, wait for CI.
