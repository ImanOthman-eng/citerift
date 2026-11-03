# Differential: corrected engine against the frozen candidate, every retained real bundle

The baseline is the engine at `26398f5`, whose `src`, `schemas`, `pyproject.toml` and `uv.lock` are identical to the
frozen candidate `3e51792`. Its 54 confirmation extractions are byte-identical to the committed predictions
(`campaign/prediction/extractions/`). The corrected engine is the working tree of the D-035 fix.

Scope: all 146 real bundles retained under `docs/verification/stage-03/` (synthetic ones excluded):
- the 54 of the 2026-11 confirmation campaign;
- the final, run-1 and superseded campaigns;
- the demonstrations.

Each bundle is extracted in process with the default configuration (`extract_all.py`), then compared by
`differential.py`. Unit references are compared by kind and span, because unit ids are renumbered.

Raw report: `DIFFERENTIAL.json`. Output digests: `OUTPUTS.sha256`.

## Result

- **124 bundles are unchanged; 22 change.**
- **No unexpected difference** (`unexpected` is empty). Containers, definitions, uses, bindings and identifiers are
  identical, apart from the identifier-to-unit links listed below. Identifier roles, normalization and anchors,
  render links, markers, the excluded identifiers and every non-unit issue are identical too. So are the accounting
  apart from unit counts, and every accounting check.
- Only the following change: units, container unit lists, identifier unit links, unit issues, ledger entries for
  unresolved definitions, and the engine and schema versions.

## Totals

| Change | Count |
|---|---|
| `unstructured_text` unit removed, short-citation link only or empty (E/F-empty) | 224 |
| `unstructured_text` unit removed, classification unresolved (H, issue and ledger entry) | 121 |
| `unstructured_text` unit removed, explanatory note (F) | 5 |
| `unstructured_text` unit replaced by an `unsupported_citation_template` unit (G) | 9 |
| `citation_template` unit removed: Arabic Harvard template `استشهاد بهارفارد دون أقواس` (now E or H) | 8 |
| identifiers moving to another unit (all into G units, role `unresolved` kept) | 6 |
| identifiers losing their unit (a field of a template with no render output of its own, role `unresolved` kept) | 1 |

No `unstructured_text` unit is added. No profile `citation_template` unit is removed or added.

## Per bundle

| Bundle | Units | Identifiers losing a unit | Identifiers moving |
|---|---|---|---|
| `evaluation/capture/bundles/holdout/en-63163494-a1` | H 1 | 0 | 0 |
| `evaluation/capture/bundles/holdout/en-74446941-a1` | H 1 | 1 | 0 |
| `evaluation/capture/bundles/reserve/ar-9617858-a1` | H 2 | 0 | 0 |
| `evaluation/capture/bundles/reserve/en-1505283-a1` | H 1 | 0 | 0 |
| `evaluation/capture/bundles/reserve/en-1898990-a1` | F 1 | 0 | 0 |
| `evaluation/capture/bundles/reserve/en-55111438-a1` | G 6, added unsupported_citation_template 6 | 0 | 6 |
| `evaluation/confirmation-2026-11/…/challenge/en-3202774-a1` | H 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-71205055-a2` | E-or-empty 32, H 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-72994622-a1` | E-or-empty 1, H 85 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/challenge/en-906156-a2` | H 2 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-1325389-a1` | H 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-4242367-a1` | template unit removed: استشهاد بهارفارد دون أقواس 8 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/ar-8446039-a1` | G 1, added unsupported_citation_template 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-25916990-a1` | G 1, added unsupported_citation_template 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-28279091-a1` | H 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-38148109-a1` | F 3 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/holdout/en-67651016-a1` | F 1, H 1 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/reserve1/en-186224-a1` | E-or-empty 184, H 18 | 0 | 0 |
| `evaluation/confirmation-2026-11/…/reserve1/en-9778156-a1` | E-or-empty 7 | 0 | 0 |
| `evaluation/confirmation-superseded/capture/bundles/confirmation/en-23645349-a1` | G 1, added unsupported_citation_template 1 | 0 | 0 |
| `evaluation/confirmation-superseded/capture/bundles/confirmation/en-31718-a1` | H 4 | 0 | 0 |
| `evaluation/final/capture/bundles/holdout/ar-8362097-a1` | H 2 | 0 | 0 |

## Why each change happens

**Class E (Harvard links only).** The changes are:
- `reserve1/en-186224-a1`: 184 definitions;
- `challenge/en-71205055-a2`: 32;
- `reserve1/en-9778156-a1`: 7.

Each body is one `{{harvnb}}` or `{{harvp}}` call, which renders a `#CITEREF` link. The 11 adjudicated false
positives of `en-186224` and the one of `en-9778156` are among them.

**Class H.**
- **Plain text beside Harvard links.** These are in `challenge/en-72994622-a1` (85: "Petitioners: {{Harvnb|…}}, …"),
  `reserve1/en-186224-a1` (17: "{{harvnb|…}}, reprinted in {{harvnb|…}}"), `challenge/en-906156-a2` (2: a link
  followed by a quotation), `holdout/en-67651016-a1` (1: the adjudicated false positive "…, treats these as two
  separate volumes.") and `holdout/ar-4242367-a1` (1: an Arabic Harvard call followed by a quotation).
- **Templates whose render shows no citation markup.** NRDB species in `en-28279091` (the adjudicated false
  positive), MedlinePlusEncyclopedia, EMedicine, ITIS, FishBase species, Bibleverse (3), Bibleref2-nb, قاموس دورلاند
  and من سمى هذا.
- **Templates without render output of their own.** These are refs inside infobox parameters, which Parsoid renders
  as part of the infobox: IUCN in `ar-1325389` (the Arabic false positive), NRDB species in `en-63163494`, Who's Who
  in `en-74446941` (its DOI, role `unresolved`, loses its unit), and one Harvnb each in `en-71205055` and
  `en-186224`.

**Class F.** Five `{{efn}}` notes whose own text gives no locator. Four are the adjudicated false positives (3 in
`en-38148109`, 1 in `en-67651016`).

**Class G.** These templates render CS1 citation markup:
- Fishbase, the adjudicated false positive;
- EI2, the Arabic false positive;
- LepIndex;
- Who's Who, six identical definitions in `reserve/en-55111438-a1`. Their DOIs, role `unresolved`, move into the G
  units.

**Arabic Harvard template.** In `holdout/ar-4242367-a1`, 8 calls of `استشهاد بهارفارد دون أقواس` were
`citation_template` units only by the RF-37 name rule. They render `#CITEREF` links: 7 are now E and 1 is H. All 8 lie outside
that article's evaluation window (code points 22784-30784), so no label covers them.
