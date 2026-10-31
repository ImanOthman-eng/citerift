#!/usr/bin/env bash
# Stage 03 clean-clone and installed-wheel check (gate 03-I). Usage: packaging_check.sh REPO_DIR WORK_DIR
# 1. clone the committed tree (no working-tree files), sync the locked environment, run the Stage 03 tests;
# 2. build the wheel, install it with its dependencies into a fresh virtual environment outside the clone, and run
#    the installed citerift-wiki on a committed observed bundle without and with CITERIFT_SCHEMAS.
set -u
repo=$1; work=$2
test ! -e "$work" || { echo "WORK_DIR exists"; exit 2; }
mkdir -p "$work"
echo "== clean clone of $(git -C "$repo" rev-parse HEAD)"
git clone -q --no-hardlinks "$repo" "$work/clone" && cd "$work/clone" || exit 1
uv sync --locked -q 2>&1 | grep -v UV_NATIVE_TLS
uv run --frozen pytest -q -p no:cacheprovider tests/stage03 2>&1 | tail -1
echo "== wheel"
uv build --wheel -q -o "$work/dist" 2>&1 | grep -v UV_NATIVE_TLS
ls "$work/dist"
whl=$(ls "$work/dist"/*.whl)
python3 -m zipfile -l "$whl" | grep -E "citerift/wiki/(data/profile-v1.json|cli.py)" | awk '{print "in wheel:", $1}'
python3 -m zipfile -l "$whl" | grep -c "schemas/" | awk '{print "schema files in wheel:", $1}'
uv venv -q -p 3.12 "$work/venv" 2>&1 | grep -v UV_NATIVE_TLS
VIRTUAL_ENV="$work/venv" uv pip install -q "$whl" 2>&1 | grep -v UV_NATIVE_TLS
cd "$work" || exit 1
b="$work/clone/tests/stage03/fixtures/observed/en-1372543632"
echo "== installed citerift-wiki verify without CITERIFT_SCHEMAS (expected exit 3, SCHEMA_ROOT_UNAVAILABLE)"
env -u CITERIFT_SCHEMAS "$work/venv/bin/citerift-wiki" verify --bundle "$b" > "$work/v1.json" 2> "$work/v1.err"; echo "exit=$?"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print('verified', r['verified'], sorted({i['code'] for i in r['issues']}))" "$work/v1.json"
echo "== installed citerift-wiki verify and extract with CITERIFT_SCHEMAS=<clone>/schemas (expected exit 0)"
CITERIFT_SCHEMAS="$work/clone/schemas" "$work/venv/bin/citerift-wiki" verify --bundle "$b" > "$work/v2.json"; echo "exit=$?"
CITERIFT_SCHEMAS="$work/clone/schemas" "$work/venv/bin/citerift-wiki" extract --bundle "$b" --out "$work/x.json" > "$work/x.summary.json"; echo "exit=$?"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print('status', r['status'], 'digest', r['extraction_digest'])" "$work/x.summary.json"
grep -o '"extraction_digest": "[0-9a-f]*"' "$work/clone/tests/stage03/fixtures/observed/expected.json" | head -1 | sed 's/^/expected (first fixture) /'
CITERIFT_SCHEMAS="$work/clone/schemas" "$work/venv/bin/citerift-wiki" replay --bundle "$b" --extraction "$work/x.json" > "$work/r.json"; echo "replay exit=$?"
