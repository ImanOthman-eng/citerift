#!/usr/bin/env bash
# A-03-001 fail-first demonstration. Runs the accepted-contract test of OLD and NEW revisions in clones that hold
# only the history of BRANCH (no side branches), with and without contract drift, and with a shallow clone that
# lacks the baseline. Usage: fail_first_demo.sh <repo url or path> <branch> <old rev> <new rev> <python> <work dir>
set -u
REPO=$1 BRANCH=$2 OLD=$3 NEW=$4 PY=$5 WORK=$6
TEST_FILE=tests/stage03/test_wiki_properties.py
TEST_ID="$TEST_FILE::test_accepted_contract_schemas_are_untouched"
rm -rf "$WORK" && mkdir -p "$WORK"
git clone -q --no-local --single-branch --branch "$BRANCH" "$REPO" "$WORK/full"
git clone -q --no-local --single-branch --branch "$BRANCH" --depth 1 "$REPO" "$WORK/shallow"
for c in full shallow; do for r in "$OLD" "$NEW"; do git -C "$WORK/$c" fetch -q --depth 1 origin "$r" 2>/dev/null; done; done
echo "branches in full clone: $(git -C "$WORK/full" branch -a | tr -d ' ' | tr '\n' ' ')"
echo "c3346d1 in full clone: $(git -C "$WORK/full" cat-file -t c3346d1 2>&1 | head -1)"
echo "0c21182 in full clone: $(git -C "$WORK/full" cat-file -t 0c21182e5871f772c3a76c75a1217c7641a63bbb 2>&1)"
echo "0c21182 in shallow clone: $(git -C "$WORK/shallow" cat-file -t 0c21182e5871f772c3a76c75a1217c7641a63bbb 2>&1)"
run() {  # clone, rev of the test file, label
  local dir="$WORK/$1"
  git -C "$dir" show "$2:$TEST_FILE" > "$dir/$TEST_FILE"
  local out
  out=$(cd "$dir" && PYTHONPATH=src "$PY" -P -m pytest -q -p no:cacheprovider "$TEST_ID" -rs 2>&1 | tail -1)
  printf '%-8s %-48s %s\n' "$(git -C "$dir" rev-parse --short "$2")" "$3" "$out"
}
drift_on()  { printf ' ' >> "$WORK/full/schemas/contracts/v1/common.schema.json"; echo '{}' > "$WORK/full/schemas/contracts/v1/injected.schema.json"; }
drift_off() { git -C "$WORK/full" checkout -q -- schemas/contracts; rm -f "$WORK/full/schemas/contracts/v1/injected.schema.json"; }
for rev in "$OLD" "$NEW"; do
  run full "$rev" "single-branch clone, no drift"
  drift_on; run full "$rev" "single-branch clone, contract drift injected"; drift_off
  run shallow "$rev" "shallow clone (baseline missing), no drift"
done
