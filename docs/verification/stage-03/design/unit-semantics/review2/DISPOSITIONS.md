# Dispositions of the second independent adversarial review of D-035

Review: `REVIEW.md` in this directory. An independent context that did not write the change reviewed
`git diff 4d44e6c 11bb5b2` (owner instruction D-035, section 6) and changed no repository file. Its scripts are kept
verbatim in `scripts/` as `.py.txt`, and its raw outputs in `out/`. The scripts import the test helpers and use the
reviewer's scratch directory; the paths are kept as run.

The implementer reproduced each confirmed finding with a test before changing production code.
`FAIL_FIRST_REVIEW2.txt` records the run of `tests/stage03/test_g5c_review2.py` against `11bb5b2`: 23 of its 28
tests fail there and the 5 controls pass. After the fix all 28 pass. Four existing tests encoded the behaviour that
RV2-4 corrects; they were changed as listed below, never deleted or skipped.

| Id | Severity | Disposition | Change | Tests (`tests/stage03/`) |
|---|---|---|---|---|
| RV2-1 | high | **Fixed** | Extraction, replay and the worker's marker reconstruction in `verify` now build the model through one function, `units.source_model`, which reads the render evidence first. Before, the reconstruction had no evidence, found no bibliography G unit, and contradicted the extraction's marker observation. All 146 retained bundles now verify with the new engine's documents (`../differential/VERIFY.txt`); at `11bb5b2`, `en-66266685-a1` did not. | `test_g5c_review2.py::test_a_bibliography_entry_with_a_g_unit_verifies` (en, ar), `::test_the_final_holdout_bundle_with_bibliography_g_units_verifies` |
| RV2-2 | medium | **Fixed: reported** | A located identifier of a reference that is in none of its units carries the new warning `IDENTIFIER_OUTSIDE_UNITS`. No unit is guessed: beside a C or G unit, whether hand-written text with its own DOI is a second work or part of the template's citation is not established, and the same holds for refs with C units since the frozen engine. In the retained data: three identifiers in two Arabic refs (`ar-3190666-a1`, `ar-4242367-a1`), each a hand-written citation beside a bot-added archive `{{استشهاد ويب}}`. | `::test_a_located_identifier_beside_a_g_unit_on_a_bibliography_line_is_reported` (en, ar), `::test_a_located_identifier_beside_a_citation_template_in_a_ref_is_reported`, control `::test_identifiers_inside_units_are_not_reported` |
| RV2-3 | medium | **Fixed** | A template that starts before a bibliography entry (a layout template around the whole list) is not part of it. An identifier that is not a template field is the entry's own when it is in no template of the entry but a wrapper, or when the entry has text of its own outside its templates and refs, as in a ref. This now matches the specification. | `::test_hand_written_entries_inside_a_list_layout_template_stay_unstructured` (en without and with render, ar), `::test_a_hand_written_entry_with_its_doi_in_a_formatting_template_stays_unstructured` (both), control `::test_an_entry_whose_only_text_is_a_template_field_stays_unresolved` |
| RV2-4 | medium | **Fixed** | A deciding template with no transclusion of its own at all (a ref in `refs=`, `{{refn}}`, an infobox parameter) is decided by the definition's rendered note, under the conditions in SPECIFICATION.md ("Note evidence"). A template whose transclusions conflict or were not expanded still has no evidence. Effect on the retained data: two Harvnb-only infobox refs go from H to no unit (E), Who's Who in `en-74446941-a1` goes from H to G (its DOI moves into the unit), NRDB species in `en-63163494-a1` stays H with the reason "render shows no citation markup". | `::test_a_list_defined_plain_citation_beside_a_helper_template_stays_unstructured` (en, ar), `::test_a_refn_plain_citation_beside_a_helper_template_stays_unstructured`, negatives `::test_the_rendered_note_decides_only_what_it_can_attribute` (4 cases). Changed: `test_g5c_unit_semantics.py::test_template_without_own_render_output_is_unresolved` became `::test_template_without_own_render_output_is_decided_by_its_note` (G, H, H without render); `::test_plain_text_beside_a_template_the_render_cannot_show_is_unresolved` now uses a note that shows a short-citation link (H) where it used a note showing nothing, which is evidence now. |
| RV2-5 | medium | **Fixed in part; residual documented** | A nested unclassified template does not make its holder H when it is a literal magic word (`{{!}}`, `{{=}}`), or when every transclusion of its own name elsewhere in the same render shows no citation markup. A nested template that is never rendered on its own still makes the holder H: nothing shows that it did not make the citation markup, and `{{small|{{Fishbase}}}}` must not become a G unit at `{{small}}` (RV-1). No retained bundle has this case. RISKS.md R-037. | `::test_a_g_template_holding_a_template_that_cannot_make_citation_markup_stays_g` (`{{!}}`, `{{lang}}` rendered elsewhere), negative `::test_a_g_template_holding_a_template_never_rendered_alone_stays_unresolved`; RV-1 test unchanged |
| RV2-6 | medium | **Fixed** (documents) | `../review/DISPOSITIONS.md`, "Effect on the retained data", corrected: `11bb5b2` added three G units and removed five `unstructured_text` units, and changed the final English holdout's G5c 0.9732 → 1.0 and G5d 0.9561 → 0.9825. | none |
| RV2-7 | low | **Fixed** | An identifier off a list line belongs to the list line on which the innermost template holding it starts. | `::test_a_multi_line_template_on_a_list_line_makes_an_entry`, control `::test_a_multi_line_template_off_a_list_line_makes_no_entry` |
| RV2-8 | low | **Fixed in part; residual documented** | `{{!}}` and `{{=}}` never decide a unit. Other magic words and parser functions stay unclassified templates; with a render, the note now decides when they have no transclusion of their own (RV2-4). Without a render a plain citation holding one stays H. | `::test_a_pipe_magic_word_in_a_plain_citation_is_not_an_unknown_template` (with and without render), `::test_a_magic_word_without_output_of_its_own_is_decided_by_the_note` |
| RV2-9 | low | **Documented; test renamed** | Accepted: VmPeak is the lifetime peak. A non-memory SystemError with exactly CPython's "error return without exception set" after a freed transient peak is improbable, as the reviewer states, and reading the state at the failure is not possible once the stack has unwound. The test that runs with an unlimited address space is renamed to say so; the case far below a set limit is the existing subprocess test. The test at the limit no longer provokes a real frame-allocation failure, which raised MemoryError on CI's runners (run 41647876812); it checks the exact exception after a peak that really reached the limit. RISKS.md R-037. | `test_wiki_mf1_tokenizer.py::test_other_errors_and_an_unlimited_address_space_are_not_memory_failures` (renamed) |
| RV2-10 | low | **Fixed** (tool) | `differential.py`: the bibliography form of `UNIT_CLASSIFICATION_UNRESOLVED` and the new `IDENTIFIER_OUTSIDE_UNITS` are checked for the right entity; a removed bibliography D unit with an H issue counts as H; an "explained" entry must be matched to the list item that holds its G unit's transclusion, read from the retained render, and its marker region must be that item. `verify_all.py` verifies every new document. | run over all 146 bundles (`../differential/`) |
| RV2-11 | info | **Documented** | The bibliography rule was designed on the exposed final holdout; `SEMANTIC_DECISION.md` section 4 and R-037 say its lift there is not evidence of generalisation. Only the prospective confirmation can be. | none |

## Effect on the retained data (exposed, regression only)

Compared with `11bb5b2`, over all 146 retained real bundles (`../differential/`):
- one `unsupported_citation_template` unit is added: Who's Who in `holdout/en-74446941-a1` (RV2-4), whose DOI moves
  into it;
- two infobox refs holding only `{{Harvnb}}` lose their H issue and have no unit (E): `challenge/en-71205055-a2` and
  `reserve1/en-186224-a1` (RV2-4);
- the H reason of NRDB species in `holdout/en-63163494-a1` now names the evidence read (RV2-4);
- three `IDENTIFIER_OUTSIDE_UNITS` warnings are added (RV2-2);
- no other output changes, and all 146 documents verify.

The frozen scorer gives exactly the same G5c and G5d as at `11bb5b2` on every exposed campaign
(`../differential/RESCORE_EXPOSED.txt`).

## Stopping

Every confirmed material finding is fixed or, for the two residuals of RV2-5 and RV2-8 and for RV2-9, documented
with its reason and kept conservative: no unit is claimed. No finding was critical. Owner instruction D-035 section 6
asks for no endless review cycles, so there is no third round; the prospective confirmation measures the result.
