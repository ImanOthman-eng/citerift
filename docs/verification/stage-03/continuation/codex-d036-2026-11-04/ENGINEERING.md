# Recovery engineering verification

CITERIFT — Created and Directed by EVE TELOS · IM

Executor: OpenAI Codex, 2026-11-04. Source under test:
`80000f292b1991ab14c0dfa5edc8e78d2e3ed06a`, clean tree before each full run.
No code, tests, dependencies, schemas, frozen artifacts or methodology changed.
The reports in this directory are recovery evidence, not a Stage 03 verification
record. Any continuation-head CI is identified separately in the final handoff.

## Commands and retained evidence

From repository root (output files were initially written outside the checkout):

```sh
UV_CACHE_DIR=/workspace/uv-cache uv sync --locked --python 3.12
UV_CACHE_DIR=/workspace/uv-cache UV_PROJECT_ENVIRONMENT=/workspace/citerift-venv313 \
  uv sync --locked --python /usr/bin/python3.13
.venv/bin/citerift-gov recover
.venv/bin/citerift-gov check
.venv/bin/python -m pytest --citerift-report <external>/test-report-3.12.json
/workspace/citerift-venv313/bin/python -m pytest --citerift-report <external>/test-report-3.13.json
```

The first pair ran in the restricted command sandbox, which disallowed creation
of AF_INET sockets and socketpair. Each collected 2,051 tests and recorded
**2,046 passed, 3 failed, 2 errors**, no skipped tests. The five outcomes are:

- Stage 02 S3 redirects and S8 whole-response deadline: fixture socket denied.
- Stage 03 drip-fed body deadline and complete Content-Length response: local server socket denied.
- Stage 03 C-level socket containment: socketpair denied before the test could apply `forbid_network`.

See original `pytest-3.12.txt`, `pytest-3.13.txt` and matching JSON reports.
These are actual nonpassing runs, retained without alteration. Both complete
suites were then rerun with normal process/socket permissions, using the same
commands and `-sockets` output suffixes. No tests were weakened or selected out.
This is an execution-environment distinction, not a product repair.

Static checks (the locked tools from `.venv/bin/`):

| Command | Observed result | Evidence |
|---|---|---|
| `citerift-gov check` | 0 errors, 0 warnings | `governance.txt` |
| `ruff check .` | All checks passed | `ruff.txt` |
| `ruff format --check .` | 377 files already formatted | `format.txt` |
| `mypy` | no issues in 52 source files | `mypy.txt` |
| `citerift-contracts check-schemas` | 2 schemas, 0 problems | `schemas.txt` |
| `uv lock --check` | resolves 47 packages, exit 0 | `lock.txt` |
| dependency audit below | No known vulnerabilities found | `dependency-audit.txt` |

```sh
uv export --locked --no-emit-project --all-groups > <external>/audit-requirements.txt
.venv/bin/pip-audit --strict --disable-pip --require-hashes -r <external>/audit-requirements.txt
```

The environment uses uv 0.13.4, while the workflow uses 0.11.32. The build warns
that the selected uv build version differs from the build-system range; the
locked build backend still builds successfully. No lock/dependency change was
made. Interpreter versions and timing are recorded by each test-report JSON.

## Installed wheel, offline verify/replay and simulations

`uv build --wheel --out-dir <external>/wheel/dist`; export the locked runtime
requirements without the project/dev group, install with `uv pip install
--require-hashes` into a fresh Python 3.12 venv, then install the wheel with
`--no-deps`. Run the existing
`final-checks/6c499a7/wheel_smoke.py.txt` with repository, wheel venv bin and a
fresh external output directory as its three positional arguments.

Result: **SMOKE PASS** (`wheel-smoke.txt`, `wheel-build.txt`), module imported
from site-packages with relocated bundles and external schema resources.
Six historical cases: Arabic/English observed fixtures, RF-60 Wiley,
D-035 Arabic no-render, English reserve2 and Arabic infobox G6b regression.
All six verify and replay successfully; partial extraction exit 6 is retained
where expected. The RF-60 key remains `10.1111/0004-5608.00043`.
No historical prediction was overwritten, and no D-036 holdout was extracted.

```sh
.venv/bin/python -P simulations/stage03/fetch_policy_sim.py 5000 20261028
.venv/bin/python -P simulations/stage03/reconcile_perturbation_sim.py 200 20261028
.venv/bin/python -P simulations/stage03/campaign_driver_sim.py 2000 20261028
```

All three report `failure_count: 0`: `sim-fetch.json`, `sim-reconcile.json`,
`sim-driver.json`. These are simulations, not prospective scientific results.

## Reproduce the read-only recovery audits

From repository root, using the unchanged locked environment:

```sh
uv run python docs/verification/stage-03/continuation/codex-d036-2026-11-04/integrity_audit.py.txt
uv run python docs/verification/stage-03/continuation/codex-d036-2026-11-04/chronology_audit.py.txt
uv run python docs/verification/stage-03/continuation/codex-d036-2026-11-04/security_audit.py.txt
```

These scripts inspect bytes, existing locks, committed history, packets and
journal accounting only. They never call capture, extract, score, lock or the
network. `integrity.json`, `chronology.json` and `security.json` hold this run's
outputs. Output `source_revision` changes when rerun at a later documentation
commit; pinned candidate/file/lock checks must still pass.

From this directory, run `sha256sum -c SHA256SUMS` to verify the checkpoint files.
Original raw evaluator transcripts/private exports remain unavailable; these
checks do not certify their underlying independent-evaluator provenance.

## Completed socket-enabled full matrix

| Python | Result | Duration | Report check |
|---|---|---|---|
| 3.12.14 | 2,051 passed, zero failed/errors/skipped | 438.48 s | 0 problems |
| 3.13.5 | 2,051 passed, zero failed/errors/skipped | 424.67 s | 0 problems |

`test-report-3.12-sockets.json` and `test-report-3.13-sockets.json` both
record revision `80000f292b1991ab14c0dfa5edc8e78d2e3ed06a`, `dirty: false`,
complete collection and exit status 0. Both passed `citerift-gov check-report
--stage 03` while copied temporarily to an untracked repository-relative report
path; the copies were moved outside again before adding the supplement. The
checked-report copies were byte-identical to the retained reports.

The matrix includes R-038, bilingual integration, contracts, schemas, security,
worker containment, network policy, reproducibility and replay tests. No passing
source-head test result is represented as scientific holdout validation.
