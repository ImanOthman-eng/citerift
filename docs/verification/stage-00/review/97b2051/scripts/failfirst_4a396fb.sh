#!/bin/sh
# Re-run the fail-first procedure of docs/verification/stage-00/fail-first/README.md: the tests of 97b2051 against
# the code of 4a396fb, in a throwaway clone.
R="$W/sandbox-ff"; rm -rf "$R"; git clone -q "$W/base" "$R"; git -C "$R" checkout -q --detach 4a396fb
rm -rf "$R/tests/stage00" && cp -a "$W/base/tests/stage00" "$R/tests/stage00" && rm -rf "$R/tests/stage00/__pycache__"
cd "$R" && PYTHONPATH="$R/src" "$W/base/.venv/bin/python" -m pytest -p no:cacheprovider -q -rf tests/stage00 2>&1 | grep -E "^FAILED|passed|failed"
