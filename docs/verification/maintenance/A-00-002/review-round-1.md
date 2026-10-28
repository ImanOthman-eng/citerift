# A-00-002 adversarial review, round 1

A separate pass of the same AI model (not human review), run read-only on the uncommitted implementation on
2026-10-28. It was asked to find scope escapes and report forgeries. Its repro scripts were kept in the
session scratchpad. They are not committed, because they import test helpers by path. Every scenario is
covered by a regression test in `tests/stage00/test_maintenance.py`.

| # | Finding (reproduced) | Fix | Regression test |
|---|---|---|---|
| 1 | `--at` dated before the pending record let Stage 02 be verified while maintenance was pending (the barrier compared times only). | The barrier is anchored to history positions (`opened_after_seq`, `finalized_after_seq`); an entry dated on the wrong side of the window is an error. | `test_a_verification_dated_before_the_pending_record_is_still_barred` |
| 2 | Rewriting `recorded_at` after validation moved the window (only baseline, candidate, scope and digest were compared with the validated revision). | The whole record at V is compared, except for the finalization fields; reports must finish after the prepare. | `test_rewriting_the_prepare_time_after_validation_cannot_finalize`, `test_a_report_from_before_the_prepare_cannot_finalize` |
| 3 | A finalized maintenance skipped the contract-version checks. | `_enhancement_contract_findings` runs on maintenance records. | `test_a_contract_change_in_the_patch_needs_its_version_raised` |
| 4 | An ordinary enhancement at V covered the pending patch, and the pending record could then be deleted. | `add_amendment` refuses an enhancement while one is pending; `check` flags an enhancement tested where a maintenance is pending. | `test_an_ordinary_enhancement_cannot_cover_a_pending_patch` |
| 5 | A gitlink was recorded as a deletion, and mode changes were not covered by the digest. | Declared files must be regular non-executable blobs (`git ls-tree`); a "deleted" file must be absent. | `test_an_executable_bit_on_a_declared_file_is_not_the_declared_patch`, `test_prepare_refuses_a_directory_or_a_non_regular_entry` |
| 6 | Superseding in the same second was refused as owner-reference reuse (failed closed). | The supersession chain is exempt in both directions. | `test_superseding_in_the_same_second_may_cite_the_same_decision` |
| 7 | A directory in `--path` crashed `prepare` with a traceback. | It is refused as `MAINTENANCE_SCOPE`. | `test_prepare_refuses_a_directory_or_a_non_regular_entry` |

Checked and found to hold:
- undeclared or changed bytes, unowned or unchanged declared paths, a missing candidate;
- path traversal and non-ASCII paths (schema);
- the baseline after re-acceptance;
- a validated revision outside history, or with changed code, or without the pending record;
- failed, dirty, partial, edited or wrong-revision reports;
- two pending transactions, hand-finalization without reports, forged digests, broken supersession links;
- drift detection after finalization;
- the single-active rule;
- old amendments without `maintenance`.

The reviewer's verdict on the implementation it was given: NOT VERIFIED.
