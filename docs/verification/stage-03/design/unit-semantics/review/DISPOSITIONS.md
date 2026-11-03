# Dispositions of the independent adversarial review of D-035

Review: `REVIEW.md` in this directory (an independent context that did not write the change; owner instruction D-035,
section 6). It reviewed `git diff 26398f5 4d44e6c` and fixed nothing. Its scripts are kept verbatim in `scripts/`
as `.py.txt`. `t13_hashseed.py.txt` writes to the reviewer's scratch directory; the path is kept as run.

The implementer reproduced each finding with the tests below before fixing it. `FAIL_FIRST_REVIEW.txt` records the
run of the new and changed tests against `4d44e6c`: 27 fail there, and every control passes. After the fix all of
them pass.

| Id | Severity | Disposition | Change | Tests (`tests/stage03/`) |
|---|---|---|---|---|
| RV-1 | high | **Fixed** | A template that holds a citation, external-data or unclassified template in its arguments within the same ref is not G. Its render output includes the nested template's. The nested citation is the one unit, with no parent. If only an unclassified template is nested, the definition is H ("citation markup holds nested templates"). | `test_a_wrapper_around_a_citation_template_is_not_a_second_unit` (en, ar), `test_a_wrapper_around_an_unclassified_template_with_citation_markup_is_unresolved` |
| RV-2 | medium | **Fixed**, with the same defect for containers | Issue entities are remapped at every renumbering of containers and units. The same cause also made container issues (`REF_DEFINITIONS_DUPLICATE`, `REF_DEFINITIONS_CONFLICT`, `LIST_DEFINED_UNUSED`) name the wrong container. This predates D-035. Under the frozen engine, 14 issues in the retained bundles named the wrong entity: 13 container issues, and one `DUPLICATE_TEMPLATE_PARAMETER` in `holdout/ar-9848536-a1` that named a unit without duplicate parameters. None do now (`differential/DIFFERENTIAL.json`, `issue_entities`). | `test_issues_name_the_renumbered_unit`, `test_container_issues_name_the_renumbered_container` |
| RV-3 | medium | **Measured, not adopted; documented** | Requiring citation markup for every RF-37 name-rule template inside refs was implemented. Over the 146 retained bundles it removed 21 genuine CS1 wrapper units: Cite iucn ×6 (taxobox parameters), Cite patent ×2, Cite simbad ×2, Cite DR3, Cite court, `استشهاد بويب/بسيط`, … . Parsoid gives these no output of their own. That is a recall loss on structured citations, so it was reverted. The annotation guide defines citation templates by purpose, with the names "Cite …" and "استشهاد …" as its examples, and RF-37 applies that name rule. A name-rule template is not a unit only on positive evidence (its own render is a short-citation link). SPECIFICATION wording corrected. Residual risk: RISKS.md R-037. | `test_a_name_rule_template_without_evidence_keeps_the_guide_name_rule` (pins the decision), `test_an_unclassified_template_without_evidence_is_not_a_citation_unit` |
| RV-4 | high | **Fixed** | Own text beside a template whose render is read as evidence, when that template has no evidence (no usable render, no output of its own, conflicting outputs), is H. Real effect: the two definitions of `challenge/en-906156-a1` (render failed) are now H, as in `-a2`. No other `unstructured_text` unit of the 146 bundles changed. | `test_short_link_and_comment_without_evidence_is_unresolved` (en, en infobox, ar), `test_the_same_revision_is_unresolved_with_or_without_its_render`, `test_plain_text_beside_a_template_the_render_cannot_show_is_unresolved`; controls `test_plain_text_beside_a_helper_template_stays_unstructured` |
| RV-5 | medium | **Not fixed; documented as residual** | No evidence in the markup or the render separates `{{NRDB species}} Retrieved …` (not a plain citation) from `{{ISBN}}` or `{{Webarchive}}` beside a hand-written citation (a plain citation) without a word list, which D-035 forbids. The controls that must stay D pass. Exposed instance: run 1, `ar-2700573-a1`. RISKS.md R-037. The Arabic run-1 row has been added to the regression table (`SEMANTIC_DECISION.md` section 7). | controls only |
| RV-6 | medium | **Fixed** | The text of an `efn`-family note without a locator is H, not F. The 4 adjudicated false positives stay without a unit, and a citation written in a note is reported, not dropped. | `test_explanatory_note_text_is_unresolved`, `test_a_citation_written_in_an_explanatory_note_is_reported` (en, ar), `test_campaign_false_positive` (4 cases now H) |
| RV-7 | low | **Documented** | Follows from rule 5 (template-only is H). The cost is now stated in `SEMANTIC_DECISION.md` section 5 and R-037. | none |
| RV-8 | low | **Fixed** | A ref whose letters or digits are only inside a tag the engine does not read (`<nowiki>`, `<pre>`, `<math>`, …) is H. A comment or punctuation alone is still empty. | `test_a_ref_whose_text_is_only_in_nowiki_is_reported`, control `test_a_ref_with_only_a_comment_or_punctuation_is_empty` |
| RV-9 | low | **Fixed** (schema); **documented** (capture) | `extraction.schema.json` `x-citerift-version` is 1.1.0. Capture records the package version (`citerift.wiki.__version__`) as its client version, so new captures say 1.1.0 although the capture code did not change. That is correct for the package and is stated in the SPECIFICATION. | schema validation in the suite |
| RV-10 | low | **Fixed** | H reasons now say what was read: "render shows no citation markup" only for templates whose render was read; "not citation templates in the profile" for markers, notes and reference lists; "no usable render" or "no output of their own in the render, or conflicting outputs" when there is no evidence. | `test_the_reason_does_not_claim_render_evidence_that_was_not_read`, updated ledger test |
| RV-11 | medium | **Documented** (design) | Adding a record for every E and empty definition was not done. It would add one issue per Harvard footnote (184 in one article) and change no unit. The limit for Stage 04 is stated in R-037 and the HANDOFF. RV-1 is fixed, so G now means a template whose own render is a citation. | none |
| RV-12 | info | **For the owner** | Deliberate and documented. A Harvard link beside a plain citation without a locator is H. This is reported in the final report as a trade-off against the directive's wording. | `test_short_citation_link_with_comment_is_unresolved` |

## Also found while fixing

- **Memory-limit test** (`test_wiki_bundle_verify.py::test_the_memory_limit_ends_in_a_stable_failure` and
  `test_wiki_mf1_tokenizer.py::test_the_memory_limit_is_reported_as_such_every_time`). These failed 3 of 3 times on
  `4d44e6c` with `EXTRACTION_WORKER_FAILED "SystemError: error return without exception set"`.
  - CPython 3.12.3 and 3.13.18 raise that error, not MemoryError, when a Python call cannot get a new frame-stack
    chunk under the address-space limit. A minimal reproduction independent of this project gives the same error.
  - The engine's new code moved the first failing allocation from the C tokenizer (a SIGSEGV, handled by MF-1 v2) to
    such a frame allocation.
  - The worker now classifies that exact message as a memory failure only when the process's peak address space
    reached the limit (SPECIFICATION.md "MF-1 v3").
  - Tests: three in `test_wiki_mf1_tokenizer.py` (a real allocation failure at the limit, and two negatives).
- **Observed-revision fixtures** (`fixtures/observed/expected.json`). The two pinned extraction digests changed. A
  field-by-field comparison with the frozen engine shows that only `schema_version` and the extractor version differ.
  Units, identifiers, issues and everything else are identical.

## Effect on the retained data (exposed, regression only)

Corrected after the second review (`../review2/REVIEW.md`, RV2-6). The first version of this section left out the
bibliography-entry rule, which was added in the same commit after the review, and said that no unit was added and
that G5c and G5d were unchanged. Measured against the reviewed commit `4d44e6c` over all 146 retained real bundles,
`11bb5b2` changed these:
- three `unsupported_citation_template` units are added: the `{{EI2}}`/`{{EI3}}` bibliography entries of the final
  English holdout `en-66266685-a1` (bibliography-entry rule);
- five `unstructured_text` units are removed: the three of those entries, and two RV-4 units in
  `challenge/en-906156-a1`;
- five definitions go from F to H (RV-6);
- 13 container issues and one `DUPLICATE_TEMPLATE_PARAMETER` issue change entity, each now naming the right entity
  (RV-2);
- the wording of the H reasons changes (RV-10).

With the frozen scorer (`differential/RESCORE_EXPOSED.txt`), every exposed campaign has the same G5c and G5d as at
`4d44e6c` except the final English holdout: G5c 0.9732 → 1.0 and G5d 0.9561 → 0.9825, from the bibliography-entry
rule. Those data shaped that rule, so this is regression evidence only (RV2-11).
