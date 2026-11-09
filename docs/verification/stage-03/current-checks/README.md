# Current candidate checks — provenance

These checks were executed by ChatGPT/Codex, not copied from the owner's external review.
The runtime source at 48cfeab is byte-identical to 3d91429; only RF-59 changes a stress
test. `current-evidence` is regression re-extraction of 46 distinct already exposed real
captures, not the fresh final cohort. All 46 verified and replayed; 37 complete and 9
partial. `V1_V2_AFTER.json` records the five mandatory altered-document CLI cases and
the genuine controls. Modified accounting and self-digests are consistent.

`current-demos/transcript.txt`: 57 operations, 53 exit 0 and four expected exit 6,
14 reproduced replays. `wheel-smoke-final`: wheel imported from site-packages outside
the checkout, external CITERIFT_SCHEMAS, fresh relocated ar/en bundle directories;
extract/verify/replay succeed, with the Arabic extraction explicitly partial. Linux only.
`current-resources`: default bounded extraction and verification on the 46 exposed
bundles, one fresh interpreter per bundle; no OS-cache flush. CPU/RSS definitions and
concurrent-load limitations are in RESULTS.json.

Full-run failures remain named by their actual run. The initial Python 3.12 failures
are retained under review/memory-test. The `full-final-*` runs passed all product tests
but failed the repository documentation-link test because two reviewer attachments had
not been copied; cd085dd supplies the unchanged missing files. They are failed runs,
not partial evidence represented as a complete pass. The complete suites are refreshed
after that correction. `test-report-313.json` is the earlier genuine 3d91429 full pass.

The first wheel setup attempted a cache-only pip sync with an index mismatch, leaving
missing runtime dependencies. The successful wheel-smoke-final run followed locked uv
sync plus installation of the same wheel; the failed setup is kept in the external
export archive. No packaging code was altered. An initial exposed-data scoring harness
used unavailable historical absolute paths and produced no score; corrected specs map
by capture hash. A reserve-step invocation initially lacked its parent output directory
and made no decision or network request; creating that directory allowed the retained
unchanged helper to complete.

Raw execution scripts are retained as .py.txt without changing their bytes. Absolute
paths in original transcripts/specs are historical run provenance; the export reproduction
procedure supplies explicit path remapping. Old frozen outputs are never overwritten.
