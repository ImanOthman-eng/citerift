# Differential: corrected engine against the frozen candidate, every retained real bundle

The baseline is the engine at `26398f5`, whose `src`, `schemas`, `pyproject.toml` and `uv.lock` are identical to the
frozen candidate `3e51792`. Its 54 confirmation extractions are byte-identical to the committed predictions
(`campaign/prediction/extractions/`). The corrected engine is the D-035 fix after both independent reviews
(`../review/DISPOSITIONS.md`, `../review2/DISPOSITIONS.md`).

Scope: all 146 real bundles retained under `docs/verification/stage-03/` (synthetic ones excluded):
- the 54 of the 2026-11 confirmation campaign;
- the final, run-1 and superseded campaigns;
- the demonstrations.

Each bundle is extracted in process with the default configuration (`extract_all.py`), then compared by
`differential.py`. Unit references are compared by kind and span, because unit ids are renumbered. Issues that name
a container or a unit are checked to name an entity that fits them.

Files:
- `DIFFERENTIAL.json`: the raw report, frozen engine against this engine (`differential.py base new <root>`).
- `DIFFERENTIAL_REVIEW2.json`: the same tool, `11bb5b2` (the second review's subject) against this engine.
- `OUTPUTS.sha256`: output digests for four engines:
  - `base/`: the frozen engine;
  - `reviewed-4d44e6c/`: the commit the first reviewer examined;
  - `reviewed-11bb5b2/`: the commit the second reviewer examined;
  - `new/`: this engine.
- `VERIFY.txt`: `verify_all.py`, offline verification of every document of this engine against its bundle (review 2,
  RV2-1: the differential compares documents, it does not verify them).
- `RESCORE_EXPOSED.txt`: the frozen scorer on the exposed campaigns (`rescore_exposed.py`).

## Result

- **120 bundles are unchanged; 26 change.**
- **No unexpected difference** (`unexpected` is empty). One bundle has an *explained* difference, verified field by
  field by `differential.py`, and against the retained render (see "Bibliography entries reconciled through G
  units" below).
- **All 146 documents verify** offline (`VERIFY.txt`). Containers, definitions, uses, bindings and identifiers are
  identical, apart from the identifier-to-unit links listed below. Identifier roles, normalization and anchors,
  render links, markers and the excluded identifiers are identical too. So are every non-unit issue apart from its
  entity, the accounting apart from unit counts, and every accounting check.
- **Issue entities.** Under the frozen engine, 14 issues named the wrong entity (review RV-2, a defect that predates
  D-035). 13 were container issues (`LIST_DEFINED_UNUSED` ×10, `REF_DEFINITIONS_DUPLICATE` ×3), and one was a
  `DUPLICATE_TEMPLATE_PARAMETER` in `holdout/ar-9848536-a1`. Under the corrected engine none do.
- Only the following change:
  - units;
  - container unit lists;
  - identifier unit links;
  - unit issues;
  - ledger entries for unresolved definitions;
  - issue entities (RV-2);
  - the engine and schema versions.

## Totals

| Change | Count |
|---|---|
| `unstructured_text` unit removed: short-citation link only, or empty (E) | 226 |
| `unstructured_text` unit removed, classification unresolved (H, issue and ledger entry) | 125 |
| `unstructured_text` unit replaced by an `unsupported_citation_template` unit (G): 10 in refs, 3 bibliography entries | 13 |
| `citation_template` unit removed: Arabic Harvard template `استشهاد بهارفارد دون أقواس` (E, or H with text) | 8 |
| identifiers moving to another unit (all into G units, role `unresolved` kept) | 10 |
| identifiers losing their unit | 0 |
| container issues naming the corrected container (RV-2) | 13 |
| `IDENTIFIER_OUTSIDE_UNITS` added (review 2, RV2-2) | 3 |

No `unstructured_text` unit is added, and no profile `citation_template` unit is removed or added. The 125 H
include the five `efn` notes that the first reviewed commit classed F (review RV-6) and the two definitions of
`challenge/en-906156-a1`, whose render failed (review RV-4).

## Per bundle

| Bundle | Units | Identifiers losing a unit | Identifiers moving | Issue entities corrected |
|---|---|---|---|---|
| `evaluation/capture/bundles/challenge/en-41925151-a1` | none | 0 | 0 | 10 |
| `evaluation/capture/bundles/holdout/en-63163494-a1` | H 1 | 0 | 0 | 0 |
| `evaluation/capture/bundles/holdout/en-74446941-a1` | G 1 (note evidence) | 0 | 1 | 0 |
| `evaluation/capture/bundles/reserve/ar-9617858-a1` | H 2 | 0 | 0 | 0 |
| `evaluation/capture/bundles/reserve/en-1505283-a1` | H 1 | 0 | 0 | 1 |
| `evaluation/capture/bundles/reserve/en-1898990-a1` | H 1 (efn) | 0 | 0 | 0 |
| `evaluation/capture/bundles/reserve/en-55111438-a1` | G 6 | 0 | 6 | 1 |
| `evaluation/confirmation-2026-11/…/challenge/en-3202774-a1` | H 1 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-71205055-a2` | E 33 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-72994622-a1` | E 1, H 85 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-906156-a1` | H 2 (render failed) | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-906156-a2` | H 2 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-1325389-a1` | H 1 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-4242367-a1` | template unit removed: استشهاد بهارفارد دون أقواس 8 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-8446039-a1` | G 1 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-25916990-a1` | G 1 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-28279091-a1` | H 1 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-38148109-a1` | H 3 (efn) | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-67651016-a1` | H 2 (1 efn) | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/reserve1/en-186224-a1` | E 185, H 17 | 0 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/reserve1/en-9778156-a1` | E 7 | 0 | 0 | 0 |
| `evaluation/confirmation-superseded/capture/bundles/confirmation/en-23645349-a1` | G 1 | 0 | 0 | 0 |
| `evaluation/confirmation-superseded/capture/bundles/confirmation/en-31718-a1` | H 4 | 0 | 0 | 0 |
| `evaluation/final/capture/bundles/holdout/ar-8362097-a1` | H 2 | 0 | 0 | 0 |
| `evaluation/final/capture/bundles/holdout/en-2275-a1` | none | 0 | 0 | 1 |
| `evaluation/final/capture/bundles/holdout/en-66266685-a1` | G 3 (bibliography entries) | 0 | 3 | 0 |

The `DUPLICATE_TEMPLATE_PARAMETER` correction in `holdout/ar-9848536-a1` is a unit issue. It counts in
`issue_entities`, not in this table.

## Why each change happens

**Class E (Harvard links only).** The changes are:
- `reserve1/en-186224-a1`: 184 definitions;
- `challenge/en-71205055-a2`: 32;
- `reserve1/en-9778156-a1`: 7.

Each body is one `{{harvnb}}` or `{{harvp}}` call, which renders a `#CITEREF` link. The 11 adjudicated false
positives of `en-186224` and the one of `en-9778156` are among them.

**Class H.**
- **Plain text beside Harvard links:**
  - `challenge/en-72994622-a1`: 85 ("Petitioners: {{Harvnb|…}}, …");
  - `reserve1/en-186224-a1`: 17 ("{{harvnb|…}}, reprinted in {{harvnb|…}}");
  - `challenge/en-906156-a1` and `-a2`: 2 each, a link followed by a quotation. In `-a1` the render failed, so the
    link has no evidence;
  - `holdout/en-67651016-a1`: 1, the adjudicated false positive "…, treats these as two separate volumes.";
  - `holdout/ar-4242367-a1`: 1, an Arabic Harvard call followed by a quotation.
- **Templates whose render shows no citation markup:**
  - NRDB species in `en-28279091`, the adjudicated false positive;
  - MedlinePlusEncyclopedia, EMedicine, ITIS and FishBase species;
  - Bibleverse (3) and Bibleref2-nb;
  - قاموس دورلاند and من سمى هذا.
- **Templates without render output of their own.** These are refs inside infobox parameters, which Parsoid renders
  as part of the infobox. The rendered note decides where the ref's container is matched to one note (review 2,
  RV2-4):
  - IUCN in `ar-1325389`, the Arabic false positive: its container is not matched to a note, so it stays H;
  - NRDB species in `en-63163494`: the note shows no citation markup, H ("render shows no citation markup").
- **Explanatory-note text without a locator** (review RV-6): five `{{efn}}` notes. Four are adjudicated false
  positives: three in `en-38148109` and one in `en-67651016`.

**Class G.** These templates render CS1 citation markup of their own:
- Fishbase, the adjudicated false positive;
- EI2, the Arabic false positive;
- LepIndex;
- Who's Who, six identical definitions in `reserve/en-55111438-a1`. Their DOIs, role `unresolved`, move into the G
  units;
- Who's Who in the infobox ref of `en-74446941`, by its note's citation markup (review 2, RV2-4). Its DOI, role
  `unresolved`, moves into the unit.

**Class E by note evidence.** One infobox ref holding only `{{Harvnb}}` in each of `en-71205055-a2` and
`en-186224-a1`: the note shows only a short-citation link (review 2, RV2-4).

**`IDENTIFIER_OUTSIDE_UNITS`** (review 2, RV2-2). Three identifiers in `holdout/ar-3190666-a1` (a PMID) and
`holdout/ar-4242367-a1` (a DOI link and `{{دوي}}`). Each is in a hand-written citation beside a bot-added archive
`{{استشهاد ويب}}`, the definition's one unit. That was so under the frozen engine too; the identifiers are now
reported.

- EI2 and EI3, three bibliography list entries (`* {{EI2|…|doi=…}}`) in the final English holdout
  `en-66266685-a1`. These are its three adjudicated false positives. The entries were made from the DOI field of a
  template the profile does not list. Before this rule they were `unstructured_text` for that reason alone.

No G template holds a nested citation-like template (review RV-1).

**Bibliography entries reconciled through G units** (`en-66266685-a1`, the one *explained* bundle). Reconciliation
matches a bibliography entry to the render through its template unit (`reconcile.py`), the same path as for a listed
citation template. Once the three entries have G units, their rendered list items are found. The following changes
follow, and `differential.py` checks that nothing else differs:
- the three entries' render state goes from `unmatched` to `matched`, at the list item of the template's own
  transclusion;
- their three DOIs go from `region_not_reconciled` to `render_link_found`;
- their marker regions are inspected (`no_recognized_warning_in_inspected_region`) instead of `not_inspected`;
- the six render links of those items are no longer render-only identifiers, and their exceptions disappear;
- status and components go from `partial` to `complete`.

Since review 2 (RV2-10) the tool also reads the retained render and requires each such entry to be matched to the
list item that holds its G unit's transclusion, with its marker region that same item. The new document of this
bundle verifies; at `11bb5b2` it did not (RV2-1).

**Arabic Harvard template.** In `holdout/ar-4242367-a1`, 8 calls of `استشهاد بهارفارد دون أقواس` were
`citation_template` units only by the RF-37 name rule. They render `#CITEREF` links: 7 are now E and 1 is H. All 8
lie outside that article's evaluation window (code points 22784-30784), so no label covers them.

## Exposed regression (frozen scorer)

| Campaign | Language | G5c before → after | G5d before → after |
|---|---|---|---|
| 2026-11 confirmation (adjudicated) | English | 0.869 → 1.000 | 0.969 → 0.977 |
| 2026-11 confirmation (adjudicated) | Arabic | 0.988 → 1.000 | 0.988 → 0.994 |
| Final holdout (adjudicated) | Arabic | 0.981 → 1.000 | 0.981 → 0.981 |
| Final holdout (adjudicated) | English | 0.973 → 1.000 | 0.956 → 0.983 |
| Run 1 holdout (adjudicated) | English | 0.983 → 0.991 | 0.974 → 0.974 |
| Run 1 holdout (adjudicated) | Arabic | 0.988 → 0.988 | 0.988 → 0.988 |

These data shaped the fix. **This is regression evidence only, not a scientific pass.** The remaining false
positives are residual risks listed in RISKS.md R-037:
- run 1, Arabic, bundle `holdout/ar-2700573-a1` (revision 75137993): `{{IUCN2008|…}}` followed by commentary
  (review RV-5);
- run 1, English, bundle `reserve/en-55111438-a1` (revision 1372414197): a `<ref>` holding only "Originally:
  ‘Judicial Review of Administrative Action’.".
