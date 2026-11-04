# Readiness review of the R-038 correction: dispositions

*CITERIFT — Created and Directed by EVE TELOS · IM*

Owner instruction D-036 section 7: two independent reviewers, then fixes of every confirmed critical or high defect,
then one focused re-review. Reviewer A examined the reconciliation subsystem and reviewer B the integration boundary,
each at `10bf0d2` in its own detached worktree and without the implementer's notes. Their reports are copied here
as `REVIEW_A_reconciliation.md` and `REVIEW_B_integration.md`. Their scripts and outputs are in the checksummed
evidence export.

Verdicts: A, NOT VERIFIED (2 high, 3 medium, 2 low). B, no critical or high (3 medium, 3 low, 2 info).

Each fix below was made fail-first. The new tests fail on `2a94110`, the engine before these fixes
(`../evidence/FAIL_FIRST_review_fixes.txt`, `../evidence/FAIL_FIRST_B2_walk_budget.txt`), and pass after.

| id | severity | confirmed? | disposition | evidence after |
|---|---|---|---|---|
| A-01 | high | yes (S1, S1b reproduced) | **Fixed.** Support is now an over-approximation. Whole-word occurrence anywhere in the before-marker text, the same after case/digit/separator folding, and number runs for values without letters. `_settle` only accepts a class when the uses with support are exactly as many as the markers that support some use. The safety argument is in `MATHEMATICAL_MODEL.md` ("Safety") | `test_r038_a_restyled_value_never_takes_another_values_marker` (4 cases), `test_r038_grouped_digits_and_case_still_anchor`; simulations (DESIGN.md section 10) |
| A-02 | medium | yes | **Fixed.** Template-output uses are grouped by transclusion (`about`), not by top-level source template, so the parts of one multi-part transclusion share one reconciliation and no marker is claimed twice | `test_r038_templates_of_one_transclusion_never_claim_one_marker_twice`, `test_r038_a_name_reused_across_templates_of_one_transclusion_pairs_by_evidence`; labelled links 1,376 → 1,387 correct |
| A-03 | high | yes (S6 reproduced) | **Fixed.** A region claimed by several bibliography entries goes to none of them. Each such entry takes its own list item, the one holding a link to its identifier that no other entry claims; otherwise it is `note_ambiguous` (`RENDER_NOTE_AMBIGUOUS`) | `test_r038_bibliography_entries_of_one_list_template_get_their_own_items`, `test_r038_bibliography_entries_without_their_own_item_are_ambiguous`; differential (DESIGN.md section 11) |
| A-04 | medium | yes (S5 reproduced) | **Fixed.** A count-only anonymous pair in template output is refused when readable texts disagree | `test_r038_a_count_only_pair_in_template_output_needs_agreeing_text` |
| A-05 | medium | yes (S3 reproduced) | **Fixed.** A name repeated among one reference's nested uses is paired by `_same_name`, not by document order; anything left unpaired is abstained | `test_r038_nested_uses_of_one_name_pair_by_evidence_not_order`; the one real case (`en-38148109-a1`, Warren919) keeps its markers, now on an evidence basis |
| A-06 | low | yes | **Fixed.** `_settle` is now propagation over the support relation; the old and new versions agreed on 200,000 random cases before the support change | `../evidence/PERFORMANCE_after_fixes.txt` (3 names × 2,000 uses: 30.3 s failed → 5.5 s) |
| A-07 | low | yes | **Fixed.** Abstention issues name only uses that end `abstained` | `test_r038_an_abstention_issue_names_only_uses_that_end_abstained` |
| H-1, H-2 | info | not reproduced on real data | No change. Hypotheses only: 0 role disagreements, and all 5,559 top-level templates matched in the corpus (reviewer A) | none |
| B-1 | medium | yes (reproduced) | **Fixed** by the A-01 change (generous support), together with S-1 (a number anchor needs at least 3 digits) | `test_r038_a_restyled_value_never_takes_another_values_marker` case B-1; `../evidence/REVIEWER_B_SIMULATION_after_fixes.txt` (seeds 1 to 8, 0 wrong; seed 1 was 10 wrong at `10bf0d2`) |
| B-2 | medium | yes | **Fixed.** The walk counts every child it iterates; one walk per block serves all its markers (cached per block and budget); markers are indexed by word and number | `test_r038_before_marker_budget_counts_every_child`, `test_r038_before_marker_texts_of_one_block_are_collected_once`; 6,705 real markers give the same before-text as the old walk; `../evidence/PERFORMANCE_after_fixes.txt` |
| B-3 | medium | yes | **Fixed in the campaign tooling** (Stage 00 stays unchanged). `confirmation-d036/scripts/secret_gate.py` adds the access-bearing URL and key shapes the Stage 00 list misses. The amendment requires the gate before every `git add` of campaign files | `tests/stage03/test_confirmation_d036_scripts.py` (every B-3 sample caught, ordinary citation URLs not) |
| B-4 | low | yes | **Documented.** `verify` rebuilds with the current engine. 23 of 203 recorded documents (15 more after these fixes) do not verify with engine 1.2.0, and every one verifies with the engine of its own campaign. SPECIFICATION.md D-036 section and RISK_ANALYSIS E17 now say so | `../evidence/VERIFY_HISTORICAL_DOCUMENTS.txt` |
| B-5 | low | yes | **Fixed.** The command in `security/PRESIGNED_URL_REVIEW.md` now searches the key-id pattern, and the words are said to occur only in documentation, the gate and its tests | the commands in that file |
| B-6 | low | yes | **Accepted as the protocol's limit.** The D-036 amendment keeps the capture driver unchanged and adopts its acquisition end (2026-11-14 23:59 UTC) as the campaign's time limit, before the 2026-11-21 deadline | amendment section 4 |
| B-7 | info | yes | **Mitigated in the procedure.** The confirmation MANIFEST records the Git tree digests of `src` and `schemas` at the candidate, and they are checked against the working tree before the prediction run | amendment section 6 |
| B-8 | info | yes | **Fixed.** SPECIFICATION.md, MATHEMATICAL_MODEL.md, RISK_ANALYSIS.md and SIMULATION_REPORT.md describe engine 1.2.0 | those files |

## Focused re-review

One focused re-review (`RE_REVIEW.md`) examined the fixes at `c144a09`. It found no critical or high defect, and
confirmed the fixes of A-01, A-02, A-03, A-05, A-06, A-07, B-1 and B-2. It also showed that the sentence this file
first ended with, "no known input yields a wrong render link", was false. It found:

| id | severity | disposition | evidence after |
|---|---|---|---|
| R-01 | medium | **Fixed.** A-04 was half fixed: a named use made by a template (`{{r|census}}`) was still paired by count with an anonymous marker the template emits itself. The text check now applies whenever the names are not equal on both sides | `test_r038_a_named_template_use_is_not_paired_by_count_with_a_disagreeing_marker` |
| R-02 | medium | **Fixed for every case it reproduced.** Silent swaps when a value is hidden, replaced, rounded or restyled beyond the folding, and another marker shows that value's source text: 21 wrong in 1,762 links in its simulation. Such a value leaves a marker that supports no use, so a role group is now paired by anchors or elimination only when every one of its markers supports some use. The cost on real data: 9 uses in 2 articles become abstained, no labelled correct link is lost, and the D-035 scores are byte-identical | `test_r038_a_marker_no_value_explains_blocks_the_whole_name` (3 cases); `../evidence/RE_REVIEWER_SIMULATION_after_fixes.txt` (21 → 0 wrong); DESIGN.md section 13 |
| R-03 | low | **Fixed.** The gate adds GCS V2 (`GoogleAccessId=`) and CloudFront (`Key-Pair-Id=`) signed URLs and matches parameter names in any case. It also scans each file's text once and twice percent-decoded, so a signed URL nested in a redirect is caught | `test_d036_secret_gate_catches_access_bearing_urls_stage00_misses` (5 new samples) |
| R-04 | low | **Fixed.** The word index uses runs of letters and digits, as the whole-word rule does, so it never drops a support | `test_r038_the_word_index_never_drops_a_support` |

All ten new tests fail on `c144a09` (`../evidence/FAIL_FIRST_re_review.txt`) and pass after.

**What remains.** No critical or high defect is open. No reproduction from the reviews, the re-review, the three
simulations (0 wrong in all), the 195 retained bundles or the 150 retained label files (0 false attachments)
yields a wrong render link after these fixes.

One boundary remains, by construction, in `MATHEMATICAL_MODEL.md` ("Safety"). A swap still needs (G) to fail with
every marker supporting some use: a use's own marker must show another use's text while its own text appears at
another marker. That takes two coincidences in one name's group, and no case of it is known. It is a scientific
limitation, not a known defect. The D-036 prospective confirmation measures G6a and G6b on unseen articles.
