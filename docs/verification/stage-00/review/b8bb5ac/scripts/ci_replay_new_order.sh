#!/bin/bash
# Replay the steps of .github/workflows/ci.yml at b8bb5ac, in their order, on an honest fresh clone; uv steps run
# with --offline. Left out (network): `uv lock --check` and the pip-audit step. setup-uv and checkout are replaced by
# the local uv 0.11.32 and git clone.
set -u
W="$1"; R="$W/sandbox-ci"; rm -rf "$R"; git clone -q "$W/base" "$R"; cd "$R" || exit 1
export PYTHONPATH=src UV_PYTHON=3.12
step() { name="$1"; shift; out=$("$@" 2>&1); rc=$?; echo "[$name] exit $rc: $(echo "$out" | grep -v UV_NATIVE | tail -1)"; [ $rc -eq 0 ] || exit $rc; }
step guard test "$(ls -A src)" = "citerift"
step "uv sync --frozen --no-install-project --no-build" uv sync --frozen --no-install-project --no-build --offline
step check uv run --no-sync python -P -m citerift.governance.cli check
step render-status uv run --no-sync python -P -m citerift.governance.cli render-status --check
echo "[uv lock --check] not run (needs the network)"
step "uv sync --locked" uv sync --locked --offline
step package-from-checkout uv run --no-sync python -P -c "import citerift, pathlib, sys; sys.exit(not pathlib.Path(citerift.__file__).resolve().is_relative_to(pathlib.Path('src').resolve()))"
step ruff uv run --no-sync ruff check .
step ruff-format uv run --no-sync ruff format --check .
step mypy uv run --no-sync mypy
step schemas uv run --no-sync python -P -m citerift.contracts.validate check-schemas
step pytest uv run --no-sync python -P -m pytest --citerift-report ci-test-report.json
step check-report uv run --no-sync python -P -m citerift.governance.cli check-report ci-test-report.json
tree_check() { git diff --exit-code || return 1; changes="$(git status --porcelain=v1 --untracked-files=all | grep -vx '?? ci-test-report.json' || true)"; test -z "$changes" || { echo "$changes"; return 1; }; }
step "tree check (diff + status)" tree_check
echo "[pip-audit] not run (needs the network)"
uv run --no-sync python -c "import json; r=json.load(open('ci-test-report.json')); print({k: r[k] for k in ('revision','dirty','collected','totals','exit_status')}, 'complete', r['selection']['complete'])"
