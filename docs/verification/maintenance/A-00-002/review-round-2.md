# A-00-002 adversarial review, round 2 (of the round-1 fixes)

The same reviewer pass re-ran all round-1 scenarios against the fixes: all were refused, and
superseding in the same second was allowed as intended. It found three more:

| # | Finding (reproduced) | Fix | Regression test |
|---|---|---|---|
| 1 | A hand finalization set `finalized_after_seq` back to the opening value, hiding a verification that the validated revision's registry already held. | `finalized_after_seq` must be at least V's history length, and `finalized_at` must not be earlier than V's last entry. | `test_a_finalization_cannot_end_the_window_before_the_validated_history` |
| 2 | While pending, raising `opened_after_seq` by hand hid a back-dated verification (an internally consistent edit). | `opened_after_seq` must equal the history length in the registry at the candidate revision. Between the candidate commit and the prepare, the patch makes Stage 00 stale, so no transition can be recorded. | `test_a_raised_window_opening_is_an_error` |
| 3 | A legitimate transition in the second of the finalization was refused (failed closed). | The window ends by position; `_now()` also takes `finalized_at` into account. | `test_a_transition_in_the_second_of_the_finalization_is_allowed` |

Also checked and found to hold:
- `as_prepared` covers `recorded_at`, `owner_ref`, `kind`, `supersedes` and `opened_after_seq`;
- no owned file in the real repository has a mode other than 100644;
- superseded windows are contiguous;
- the barrier cannot fire on the real registry's existing history.

Remaining limitation: a consistent forgery by someone with repository write access (MAINTENANCE_MODEL.md, section 7).

The reviewer's verdict on the round-1 fixes: NOT VERIFIED (because of finding 1, since fixed).
