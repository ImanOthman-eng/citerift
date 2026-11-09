# V1/V2 correction record — 30 October 2026

Project owner: EVE TELOS. Implementer: ChatGPT/Codex (AI coding agent).
Baseline: d1b64499ab7b53d5e486f3cc6db6d86f51bf3399. External review findings V1 and V2 are mapped to new IDs
RF-56 and RF-57; prior RF-01 through RF-55 and F1–F4 are unchanged.

## RF-56 / V1 — outside-region warning attribution

Severity: medium. A modified extraction document could borrow an actual warning word from an unrelated
paragraph or another note. Its locator/digest were valid but did not prove reference attribution. Genuine
extraction did not produce the forged warning. English and Arabic originals independently reproduced here:
verify=true, replay=differs, with recomputed accounting and extraction digest and unchanged capture bytes.

Repair: authorize regions from a reconstructed retained-source binding and retained DOM. Compare marker region
and complete witness against that reconstruction, never the result document's region fields. Multi-element
template output and common-ancestor locators remain valid. Disposition: repaired in current code; focused
regressions pass. Final-stage status requires the remaining campaign, complete verification and delivery.

## RF-57 / V2 — supplied substring/context classification

Severity: medium. The original verifier checked regex boundaries on the supplied substring and trusted its
exclusion/classification. Removing negation/quotation exclusions or quoting retracted within unretracted passed.
All three originals independently reproduced here (verify=true, replay=differs). These are forged-document
acceptance defects, not observed extraction mistakes.

Repair: reconstruct marker matches on the entire authorized region with existing folding, boundaries, quotation,
negation, title prefix, Arabic attachment, citation/hidden-channel and interrupted-boundary rules. Compare complete
occurrences with multiplicity rather than existential membership. Shared deterministic marker reconstruction is
explicit; replay still compares the entire independently re-extracted document. Existing local caches remain and
new reconstruction uses the established offline worker limits. Disposition: repaired; bilingual/context tests pass.

## RF-58 / independent review R3-V12-01 — malformed configuration exception

Severity: medium. The first repair introduced an uncaught ValueError for schema-valid integer-valued JSON floats
such as max_nodes=400000.0, after consistent config/extraction digests. The separate read-only reviewer reproduced
it. Repair: catch configuration conversion errors and return BUNDLE_SCHEMA_INVALID, matching replay. A regression
asserts a report rather than an exception. The review's original report remains unedited; its later confirmation
records the fixed file hashes and checks. Disposition: repaired and separately rechecked.

## Evidence and limits

- `failfirst/v1-v2/`: all five original synthetic bundles, genuine/forged documents, actual before verify/replay,
  RESULTS.json and pytest-before.txt. Five originals all accepted before; all genuine controls reproduced.
- `tests/stage03/test_wiki_v1_v2.py`: 22 bilingual variants plus RF-58. Before: 18 failed, 4 passed (existing
  hidden/citation checks already caught four variants). After: 23 passed in 25.21 seconds on Python 3.12.14.
- Existing F1–F4 plus initial 22 variants: 145 passed in 65.19 seconds. These are focused, dirty-tree development
  runs, not clean complete-run reports.
- Initial full Stage 03 development run: 500 passed, 3 failed because the command sandbox refused socket creation
  used by existing localhost transport tests. Re-running those three with the environment's supported network
  permission: 3 passed in 3.18 seconds. No test or product weakening was used.
- Independent reviewer output is retained under `round-4/`; its report identifies its own scope and hashes.
- No final-cohort article content, annotations or predictions has been accessed during these corrections.
- No actual development token/spend counter is exposed; no cost estimate is fabricated. Product runtime uses no AI.
