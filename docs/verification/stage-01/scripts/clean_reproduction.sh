#!/usr/bin/env bash
# Bounded clean-cache reproduction of one positive case (POS-02, Obokata 2014, en and ar) and one negative control
# (NC-03, Watson & Crick 1953), compared field by field with the committed data (FEASIBILITY_REPORT.md §9.2).
# Usage: clean_reproduction.sh RW_CSV WORK_DIR
#   RW_CSV    the pinned retraction_watch.csv (see reproduce.sh)
#   WORK_DIR  an empty directory outside the repository; it receives a fresh response cache and the raw outputs
# Sends about 15 live requests (15 on 2026-10-27). Run from the repository root.
set -euo pipefail
CSV=$1
W=$2
if [ -e "$W/cache" ]; then
    echo "WORK_DIR already has a cache; use an empty directory" >&2
    exit 2
fi
mkdir -p "$W/cache"
P="python3 -I docs/verification/stage-01/scripts/stage01_probe.py --cache $W/cache"
POS=10.1038/nature12968
NEG=10.1038/171737a0
echo "[\"$POS\"]" >"$W/pos.json"
$P lookup --csv "$CSV" --dois $POS --out "$W/pos_lookup.json"
$P discover --dois-file "$W/pos.json" --methods m1,m2 --out "$W/pos_discovery.json"
$P lookup --csv "$CSV" --dois $NEG --out "$W/neg_lookup.json"
python3 -I docs/verification/stage-01/scripts/compare_clean.py --work "$W" \
    --out docs/verification/stage-01/data/clean_reproduction.json
