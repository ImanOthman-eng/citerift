#!/usr/bin/env bash
# Re-derive every Stage 01 data file, the manifest and the live re-verification, in order.
# Usage: reproduce.sh RW_CSV CACHE_DIR
#   RW_CSV     retraction_watch.csv at GitLab commit a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4
#              (SHA-256 2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655)
#   CACHE_DIR  response cache outside the repository; with a warm cache no request is sent
#              except by the final `verify`, which always re-fetches (--refresh).
# Run from the repository root.
set -euo pipefail
CSV=$1
C=$2
P="python3 -I docs/verification/stage-01/scripts/stage01_probe.py --cache $C"
D=docs/verification/stage-01/data
F=$D/followups
WAKEFIELD="10.1016/S0140-6736(97)11096-0"
MMR_AR="لقاح الحصبة والنكاف والحصبة الألمانية"

# 01-A: snapshot profile, sample and Retraction Watch + Crossref lookups
$P rw-profile --csv "$CSV" --out $D/rw_profile.json
$P sample --csv "$CSV" --out $D/sample_S.json
# shellcheck disable=SC2046
$P lookup --csv "$CSV" --dois $(python3 -I -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))))" \
    $D/purposive_dois.json) 10.1056/NEJMc2021225 --out $D/purposive_lookup.json
$P lookup --csv "$CSV" --dois 10.1038/171737a0 --out $F/nc3_lookup.json

# 01-B / 01-E: discovery (P with M1 and M2, S with M2)
$P discover --dois-file $D/purposive_dois.json --methods m1,m2 --out $D/purposive_discovery.json
$P discover --dois-file $D/sample_S.json --methods m2 --out $D/sample_S_discovery.json

# 01-D: interlanguage follow-up and revision-history timelines
$P crosswiki --discovery $D/purposive_discovery.json --src en --dst ar --out $F/crosswiki_en_to_ar.json
$P crosswiki --discovery $D/purposive_discovery.json --src ar --dst en --out $F/crosswiki_ar_to_en.json
$P crosswiki --discovery $D/sample_S_discovery.json --src en --dst ar --out $F/crosswiki_S_en_to_ar.json
$P crosswiki --discovery $D/sample_S_discovery.json --src ar --dst en --out $F/crosswiki_S_ar_to_en.json
for what in cited marked; do
    $P first-revision --wiki en --title "MMR vaccine" --doi "$WAKEFIELD" --what $what --out $F/timeline_en_mmr_$what.json
    $P first-revision --wiki ar --title "$MMR_AR" --doi "$WAKEFIELD" --what $what --out $F/timeline_ar_mmr_$what.json
done

# 01-C: independent substring check of the NC-02 revisions
NEEDLES=(11096 "S0140-6736(97)" 9500320 PIIS0140673697110960 Wakefield ويكفيلد)
$P absence-check --wiki en --revids 153716034 --needles "${NEEDLES[@]}" --out $F/nc2_absence_check_en.json
$P absence-check --wiki ar --revids 18119085 76772881 --needles "${NEEDLES[@]}" --out $F/nc2_absence_check_ar.json
# Retraction wording in the en MMR revisions just before and at the first {{Retracted}} (FEASIBILITY_REPORT.md §7.4)
$P absence-check --wiki en --revids 483589591 483915164 --needles "fully retracted" "{{Retracted" retracted \
    --context 150 --out $F/en_mmr_retraction_text_check.json

# Rendered (parser HTML) check of the citing references, POS-02 and POS-01, both languages (FEASIBILITY_REPORT.md §7.3)
$P render-check --wiki en --revids 1372543632 --doi 10.1038/nature12968 --out $F/render_check_en_obokata.json
$P render-check --wiki ar --revids 76190003 --doi 10.1038/nature12968 --out $F/render_check_ar_obokata.json
$P render-check --wiki en --revids 1381772671 --doi "$WAKEFIELD" --out $F/render_check_en_mmr.json
$P render-check --wiki ar --revids 72523566 --doi "$WAKEFIELD" --out $F/render_check_ar_mmr.json

# Prior art and Arabic template checks (CREATIVE_FEASIBILITY.md §1, FEASIBILITY_REPORT.md §7.3)
$P api-query --host meta.wikimedia.org --param meta=globaluserinfo --param guiuser=RetractionBot \
    --param guiprop=merged --out $F/prior_art_retractionbot_global.json
for w in en ar; do
    $P api-query --host $w.wikipedia.org --param list=usercontribs --param ucuser=RetractionBot --param uclimit=5 \
        --out $F/prior_art_retractionbot_${w}wiki.json
done
$P api-query --host en.wikipedia.org --param prop=categoryinfo \
    --param "titles=Category:Articles citing retracted publications|Category:Articles intentionally citing retracted publications" \
    --out $F/prior_art_en_categories.json
$P api-query --host ar.wikipedia.org --param prop=info --param "titles=قالب:Retracted|قالب:مصدر مسحوب" \
    --out $F/ar_templates_info.json
$P api-query --host ar.wikipedia.org --param list=embeddedin --param "eititle=قالب:Retracted" --param einamespace=0 \
    --param eilimit=500 --out $F/ar_embeddedin_retracted.json
$P api-query --host ar.wikipedia.org --param list=embeddedin --param "eititle=قالب:مصدر_مسحوب" --param einamespace=0 \
    --param eilimit=500 --out $F/ar_embeddedin_masdar_mashub.json
$P api-query --host ar.wikipedia.org --param prop=revisions --param "titles=قالب:مصدر مسحوب" --param rvdir=newer \
    --param rvlimit=1 --param "rvprop=ids|timestamp" --out $F/ar_masdar_mashub_first_revision.json

# 01-F: manifest from the data files, then live re-verification of every pinned revision and notice
python3 -I docs/verification/stage-01/scripts/build_manifest.py --out docs/verification/stage-01/EVIDENCE_MANIFEST.json
# A separate cache keeps the refreshed responses from replacing the ones the data files were derived from.
python3 -I docs/verification/stage-01/scripts/stage01_probe.py --cache "$C/verify-refresh" --refresh \
    verify --manifest docs/verification/stage-01/EVIDENCE_MANIFEST.json --out $D/verify_result.json
