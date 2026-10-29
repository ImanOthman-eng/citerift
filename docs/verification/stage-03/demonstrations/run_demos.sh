#!/usr/bin/env bash
# Stage 03 demonstrations (directive section 12): actual CLI commands on retained bundles, offline.
# Usage: bash docs/verification/stage-03/demonstrations/run_demos.sh OUT_DIR   (from the repository root)
# Every command and its exit code is written to OUT_DIR/transcript.txt; the documents to OUT_DIR.
set -u
out=$1
test ! -e "$out" || { echo "OUT_DIR exists"; exit 2; }
mkdir -p "$out"
here=docs/verification/stage-03/demonstrations
obs=tests/stage03/fixtures/observed
cap=docs/verification/stage-03/evaluation/capture/bundles
log="$out/transcript.txt"
run() {
  echo "\$ $*" >> "$log"
  "$@" > "$out/last.stdout" 2> "$out/last.stderr"
  code=$?
  echo "exit $code" >> "$log"
  grep -v UV_NATIVE_TLS "$out/last.stderr" | sed 's/^/  stderr: /' >> "$log"
  return 0
}
summary() {  # the CLI's JSON summary, reduced to status, digest and component states
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('  stdout:', json.dumps({k: d.get(k) for k in ('status','extraction_digest','verified','replay') if k in d}, ensure_ascii=False)[:400])" "$out/last.stdout" >> "$log"
}
for b in "$obs/ar-76190003" "$obs/en-1372543632" "$here/bundles/en-1372543632-recapture-2026-10-29" \
         "$here/bundles/en-1381772671" "$here/bundles/en-1374726997" "$cap/holdout/en-81119391-a1"; do
  n=$(basename "$b")
  run uv run citerift-wiki verify --bundle "$b"; summary
  run uv run citerift-wiki extract --bundle "$b" --out "$out/$n.extraction.json"; summary
  run uv run citerift-wiki verify --bundle "$b" --extraction "$out/$n.extraction.json"; summary
  run uv run citerift-wiki replay --bundle "$b" --extraction "$out/$n.extraction.json"; summary
done
# 1. source marker and missing-template rendering (ar), rendered warning (en)
python3 "$here/show.py" marker "$out/ar-76190003.extraction.json" > "$out/demo1_ar_markers.json"
python3 "$here/show.py" marker "$out/en-1372543632.extraction.json" > "$out/demo1_en_markers.json"
# 2. one reference reused at several places
python3 "$here/show.py" reuse "$out/en-1372543632.extraction.json" rasko > "$out/demo2_en_reuse.json"
python3 "$here/show.py" reuse "$out/ar-76190003.extraction.json" rasko > "$out/demo2_ar_reuse.json"
# 3. notice identifiers next to the cited work (real), never promoted
python3 "$here/show.py" roles "$out/en-1374726997.extraction.json" > "$out/demo3_en_roles.json"
python3 "$here/show.py" roles "$out/ar-76190003.extraction.json" > "$out/demo3_ar_roles.json"
# 4. several works in one reference
python3 "$here/show.py" multiwork "$out/en-1381772671.extraction.json" > "$out/demo4_en_multiwork.json"
# 5. differing render captures of one revision, and a source-only capture after a render failure
python3 "$here/show.py" captures "$obs/en-1372543632" "$here/bundles/en-1372543632-recapture-2026-10-29" > "$out/demo5_captures.json"
python3 -c "import json,sys; a,b=(json.load(open(p)) for p in sys.argv[1:3]); print(json.dumps({'digest_2026_10_28': a['extraction_digest'], 'digest_2026_10_29': b['extraction_digest'], 'same_reference_facts': [a[k] == b[k] for k in ('containers','uses','units')], 'same_identifiers_except_render_hashes': [ {k: v for k, v in x.items() if k != 'render'} for x in a['identifiers']] == [ {k: v for k, v in x.items() if k != 'render'} for x in b['identifiers']]}, indent=1))" "$out/en-1372543632.extraction.json" "$out/en-1372543632-recapture-2026-10-29.extraction.json" > "$out/demo5_extractions.json"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({'status': d['status'], 'components': d['components'], 'markers': sorted({m['state'] for m in d['markers']}), 'render_failure': [ {k: a.get(k) for k in ('operation','status','code','retry_after_s')} for a in json.load(open(sys.argv[2]))['attempts'] if a['operation']=='render']}, indent=1))" "$out/en-81119391-a1.extraction.json" "$cap/holdout/en-81119391-a1/capture.json" > "$out/demo5_source_only.json"
rm -f "$out/last.stdout" "$out/last.stderr"
echo done
