#!/bin/sh
# Replay the CI workflow steps (ci.yml, in order) on an honest clone of 97b2051; network steps (uv lock --check,
# pip-audit) are left out. Uses the locked environment of $W/base.
set -u
R="$W/sandbox-ci"; rm -rf "$R"; git clone -q "$W/base" "$R"; cd "$R" || exit 1
VPY="$W/base/.venv/bin/python"; export PYTHONPATH=src
step() { name="$1"; shift; out=$("$@" 2>&1); rc=$?; echo "[$name] exit $rc: $(echo "$out" | grep -v UV_NATIVE | tail -1)"; [ $rc -eq 0 ] || exit $rc; }
step guard test "$(ls -A src)" = "citerift"
step package-from-checkout "$VPY" -P -c "import citerift, pathlib, sys; sys.exit(not pathlib.Path(citerift.__file__).resolve().is_relative_to(pathlib.Path('src').resolve()))"
step check "$VPY" -P -m citerift.governance.cli check
step render-status "$VPY" -P -m citerift.governance.cli render-status --check
step ruff "$W/base/.venv/bin/ruff" check .
step ruff-format "$W/base/.venv/bin/ruff" format --check .
step mypy "$W/base/.venv/bin/mypy"
step schemas "$VPY" -P -m citerift.contracts.validate check-schemas
step pytest "$VPY" -P -m pytest --citerift-report ci-test-report.json
step check-report "$VPY" -P -m citerift.governance.cli check-report ci-test-report.json
step git-diff git diff --exit-code
echo "git status --porcelain: $(git status --porcelain | tr '\n' ' ')"
"$VPY" -c "import json; r=json.load(open('ci-test-report.json')); print({k: r[k] for k in ('revision','dirty','collected','totals','exit_status')}, 'complete', r['selection']['complete'])"
