# Stage 03 review findings

Four review perspectives were applied to the engine after the protocol freeze (`afa0115`) and before any holdout
prediction existed, by the implementing agent (not an independent reviewer; the independent evaluation is the
separate evaluator's annotation, `../evaluation/`). Every defect that was fixed has a fail-first case under
`failfirst/`: `RF-nn_case.py` runs the case through the public API or the CLI, `RF-nn_before.json` is its output on
the code before the fix and `RF-nn_after.json` on the fixed code (re-run on the final code and byte-identical). Each
fix also has a regression test in `tests/stage03/`.

| Perspective | Question asked |
|---|---|
| P1 semantic correctness | does every identifier get the role and binding MediaWiki gives it; is any render region attached to the wrong container? |
| P2 observation honesty | can any failure, hidden text or missing evidence turn into "no warning", or anything into a statement about retraction? |
| P3 security and robustness | can input (bundles, records, configurations, network answers) make the tools run unsafely, misreport, or crash? |
| P4 reproducibility, packaging and evaluation integrity | do replay, the wheel, a clean clone and the scorer behave as documented? |

## Findings

| Id | Perspective | Severity | Finding | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-01 | P1 | high | A citation template that repeats `doi=` reported both values as `primary_citation_field`, although MediaWiki uses only the last one: the overridden value was presented as the cited work's DOI. | Fixed (`bb8756b`): the overridden value is `unresolved` with `IDENTIFIER_PARAMETER_OVERRIDDEN`; the last value stays primary. | `failfirst/RF-01_*`; `test_wiki_source_extraction.py` |
| RF-02 | P2 | high | A warning term present only in text the HTML hides (`display:none`) gave `no_recognized_warning_in_inspected_region`: what a reader saw is not evaluated, so this was a failure-to-absence path. | Fixed (`bb8756b`): `ambiguous_text`, evidence kept with `kind: hidden`. | `failfirst/RF-02_*`; `test_wiki_render_ledger.py` |
| RF-03 | P1 | high | When two reference-list items share one DOM id, or two containers point to one note, both containers were `matched` to the same item and container `a` received the text of note "two" (a wrong attachment feeding a marker observation). | Fixed (`bb8756b`): `note_ambiguous` with `RENDER_NOTE_AMBIGUOUS`; no region attached; marker `not_inspected`. | `failfirst/RF-03_*`; `test_wiki_render_ledger.py` |
| RF-04 | P3 | medium | `ExtractConfig` accepted any value: `worker_wall_s=-1`, `worker_memory_mib=true`, `max_nodes="400000"` or `max_depth=0` ran and published an extraction failure (exit 9) that blamed the article instead of refusing the configuration. | Fixed (`93f5ffb`): every value validated; the CLI exits 3 with the reason. | `failfirst/RF-04_*`; `test_wiki_bundle_verify.py::test_invalid_configurations_are_refused` |
| RF-05 | P3 | medium | `replay` of a recorded extraction whose `config` held an unknown key ended in an internal error (exit 1); out-of-range values replayed with them. The schema allowed any numbers in `config`. | Fixed (`93f5ffb`): the schema pins the configuration object; replay reports `BUNDLE_SCHEMA_INVALID` (exit 3). | `failfirst/RF-05_*`; `test_wiki_cli.py` |
| RF-06 | P3 | high | `replay` compared only the recorded `extraction_digest` with the new one, so a recorded document edited after extraction (here a forged normalized DOI) was reported `reproduced` with exit 0. | Fixed (`93f5ffb`): replay checks the record's own digest (`BUNDLE_DIGEST_MISMATCH`, exit 5) and compares whole documents. | `failfirst/RF-06_*`; `test_wiki_bundle_verify.py::test_replay_refuses_forged_mismatched_and_foreign_records` |

## Checked without a defect

- P1: a field anchor covers the parameter value as written, with surrounding whitespace; the Stage 02 normalizer
  records `TRIM_OUTER_WHITESPACE`. This is documented behavior (SPECIFICATION.md 11.4), not a defect; the scorer
  matches identifiers by overlap.
- P3: an unlisted file in a bundle is a warning (`BUNDLE_UNLISTED_FILE`) and does not fail verification: it changes
  no claim of the capture, and it is always reported.
- P3: a 1.8 MB synthetic article with 20 000 named references exceeds the 30 s worker deadline at 256 MiB and the
  memory limit at 64-128 MiB; both end in their stable failure codes. Real articles are within budget
  (`TEST_RESULTS.md`).
