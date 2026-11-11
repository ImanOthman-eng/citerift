#!/usr/bin/env bash
# A-02-001 fail-first demonstration: the new Stage 02 tests against the accepted Stage 02 code.
# Run from the repository root with the candidate's test file present:
#   bash docs/verification/maintenance/A-02-001/fail_first.sh
# It checks out the accepted revision cf06083 into a temporary worktree, adds only
# tests/stage02/test_rde_gather_bounded.py from the working tree, and runs it there.
set -u
repo=$(pwd)
tmp=$(mktemp -d)
trap 'git -C "$repo" worktree remove --force "$tmp/wt" >/dev/null 2>&1; rm -rf "$tmp"' EXIT
git -C "$repo" worktree add --detach "$tmp/wt" cf060834afedfa4a82712ca247ad2fc2b2fa9665 >/dev/null 2>&1
echo "accepted revision: $(git -C "$tmp/wt" rev-parse HEAD)"
echo "query.py sha256 at the accepted revision: $(sha256sum "$tmp/wt/src/citerift/retraction/query.py" | cut -d' ' -f1)"
cp "$repo/tests/stage02/test_rde_gather_bounded.py" "$tmp/wt/tests/stage02/"
cd "$tmp/wt" || exit 1
PYTHONPATH=src "$repo/.venv/bin/python" -P -m pytest -q -p no:cacheprovider tests/stage02/test_rde_gather_bounded.py 2>&1 \
  | grep -E "^(FAILED|ERROR|[0-9]+ (passed|failed))|Error|error" | sed "s#$tmp/wt#<accepted-worktree>#g" | head -40
echo "exit: ${PIPESTATUS[0]}"
