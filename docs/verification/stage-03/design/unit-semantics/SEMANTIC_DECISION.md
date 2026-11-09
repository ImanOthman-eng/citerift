# What a citation unit is: classes A-H (owner instruction D-035)

Status: implemented on the PR #5 branch after the fail-first commit `907d30d`, revised after the independent review
(`review/DISPOSITIONS.md`). Engine 1.1.0, extraction schema 1.1.0.
Supersedes the unit rule of SPECIFICATION.md 11.3 as frozen in `3e51792`. That text is kept as the record of the
candidate that the 2026-11 confirmation campaign measured.

## 1. The defect

`3e51792` made every reference definition without a template unit `unstructured_text`. The annotation guide v1.1
gives `unstructured` only to a definition that "cites something in plain text with no citation template". These two
predicates are not the same. The confirmation campaign measured the gap as English G5c 0.869 (126 true and 19 false
positives). All 19 false positives are `unstructured_text` units:

- 13 Harvard short-citation links;
- 4 explanatory notes;
- 2 citation-like templates the profile does not list.

The same predicate also produced the 2 Arabic false positives, IUCN and EI2 (Arabic G5c 0.9875). See
`evidence/campaign_false_positives.json` (frozen scorer matching on the adjudicated labels).

**Required invariant:** the absence of a recognized citation template is not sufficient evidence that an unstructured
bibliographic citation exists.

## 2. Classes

| Class | What it is | Engine output |
|---|---|---|
| A | a reference definition (a `<ref>` with content, a list-defined ref, a generated note) | a definition in a container (unchanged) |
| B | a citation unit: one cited work inside a definition or bibliography entry | a `units[]` entry |
| C | a structured citation template of the profile, or named "Cite …" / "استشهاد ب…" (RF-37) | `citation_template` / `external_data_template` (unchanged) |
| D | a genuine unstructured citation: the definition's own text cites a work | `unstructured_text` |
| E | a short-citation link (Harvard family) to an entry elsewhere, and nothing else | no unit |
| F | an empty definition (no own text, no template), including an `efn` with no own text | no unit |
| G | a template the profile does not list whose own render is a CS1/CS2 citation, in a ref or a bibliography entry | `unsupported_citation_template` (new kind), with the issue `CITATION_TEMPLATE_UNSUPPORTED` |
| H | a definition whose citation unit cannot be established safely | no unit; issue and ledger entry `UNIT_CLASSIFICATION_UNRESOLVED` naming the definition and the reason |

E and F have no unit of their own:
- an E link cites a work whose unit is the bibliography entry it points to;
- an F definition is empty;
- a ref nested in an E or F definition is a definition of its own and is classified by itself.

H is an abstention, not a classification. Since the review, the text of an explanatory note (`efn`) without a
locator is H, not F (RV-6): it may explain or cite, and it is reported, not dropped. It records that nothing in the markup or the render decides between a
citation and a non-citation. The definition keeps its anchors and the issue says why.

## 3. Evidence that decides

### 3.1 The definition's own content

From the source scan (`source.py`), recorded per ref:
- own text: a letter or a digit in a text run that is inside the ref and inside no template called within that ref;
- an own external link.

A template around the ref, such as the `{{efn}}` that generates it or an infobox whose parameter holds it, does not
count. Identifier candidates of the ref count as a locator when they are not template fields and every template
around them inside the ref is a profile identifier wrapper (`{{doi}}`, `{{PMID}}`). Letters and digits are Unicode
categories, the same for Arabic and English. No word list is used.

### 3.2 The template's render (`units.py`)

The engine reads the template's own Parsoid output, paired with the source call by canonical target and parameters
(the reconciliation key). Equal keys expand to the same output, so document order does not matter. Two marks are
used:

- **`citation_markup`**: a `<cite class="citation …">` element. Module:Citation/CS1 writes it around every CS1/CS2
  citation, in both wikis.
- **`short_citation_link`**: a link to a `#CITEREF…` anchor. These are the anchors that Module:Footnotes and the CS1
  module use for Harvard-style references (`design/sfn-semantics/sources/`).

Evidence is read only for templates that can decide a unit:
- inside a ref, outside any other template of that ref: kind `other`, and templates that are citation templates
  only by the RF-37 name rule (family `unlisted`);
- outside refs: kind `other` templates called at the top level that hold an identifier (they can make a bibliography
  entry).

Parsoid renders a template nested in another as part of the outer one. Citation markup in the output of a template
that holds a citation, external-data or unclassified template therefore cannot be attributed to the outer one
(RV-1). A nested unclassified template does not count when it cannot make citation markup (review 2, RV2-5):
- a literal magic word, `{{!}}` or `{{=}}`, which is MediaWiki syntax for one character;
- a template whose every transclusion of its own name elsewhere in the same render shows no citation markup.

A template gets no evidence of its own in these cases:
- its transclusion has several parts;
- MediaWiki stopped expanding it (a parser-limit warning);
- it has no transclusion of its own, as for a ref inside an infobox parameter, a reference list's `refs=` or
  `{{refn}}`;
- its calls with one key disagree.

**The rendered note** (review 2, RV2-4). In the third case only (no transclusion at all, which is structural), the
definition's rendered note decides, when its container is matched to exactly one note with agreeing backlinks and no
unexpanded template, and its definitions do not conflict. A note with neither mark shows that none of those templates
is a citation or a link. A note with a mark gives it to the definition's one template without evidence, when every
other deciding template of it has no citation markup; with two or more without evidence nothing is attributed.
Without this, every hand-written citation with an `{{ISBN}}` or `{{Webarchive}}` in a list-defined ref was H.

The survey of every retained bundle (`evidence/render_evidence_survey.txt`, 146 real bundles, before the fix)
separates the template families without exception:
- every profile citation template has `citation_markup`;
- every `Harvnb`, `Harvp`, `Harv` and `استشهاد بهارفارد دون أقواس` call has `short_citation_link` and no citation
  markup;
- identifier wrappers, archive, ISBN, maintenance and marker templates have neither.

The profile is not changed. Its digest is unchanged.

## 4. Rules (`model.py`, `_plain_definition` and `_bibliography_entry`; first rule that applies)

**Template units.** A profile citation or external-data template is C, as before, except for one case:
- a template that is a citation template only by the RF-37 name rule;
- whose own render is a short-citation link.

That template is a link (E), not a citation. In the retained data this is the Arabic Harvard template
`استشهاد بهارفارد دون أقواس`. Without that evidence the guide's name rule stands (RV-3, measured in
`review/DISPOSITIONS.md`). A kind-`other` template whose own render has citation markup, and that holds no
citation-like template, is G when it is called inside a ref outside any other template of that ref, or at the top
level of a bibliography entry. A definition or entry with a C or G unit gets no `unstructured_text` unit, which is
unchanged for C.

For any other definition of a `<ref>`, list-defined, `#tag` or generated note (short footnotes excluded, as before):
1. it gives a locator itself (an own external link, or a DOI/PMID in its text or in a profile wrapper): D;
2. it has own text:
   - beside a template whose render is read as evidence and shows a short-citation link, citation markup it cannot
     own (a holder), or no evidence at all (no usable render, no output of its own, conflicting outputs): H. The
     text may be a comment, a quotation or a second citation (RV-4);
   - in an explanatory footnote (`efn`): H (RV-6);
   - otherwise: D (the `<ref>` mechanism is the evidence that its text is a citation);
3. its letters or digits are only inside a tag the engine does not read (`<nowiki>`, `<pre>`, `<math>`, …): H
   (RV-8);
4. no own text:
   - every template in it is a short-citation link: E;
   - some other template: H, with the reason (its render shows no citation markup; no usable render; no output of
     its own; markup it cannot own; or not a citation template in the profile, RV-10);
   - nothing at all: F (empty).

**Bibliography entries.** An entry is made from a citation template or an identifier on a list line, as before. An
identifier off a list line belongs to the list line on which the innermost template holding it starts, so a call over
several lines makes an entry too (review 2, RV2-7). Without a C or G unit:
- an identifier that is not a template field, and is in no template of the entry but a profile identifier wrapper
  (its own text, a resolver link), or in an entry that has text of its own outside its templates and refs: D. A
  template that starts before the entry, such as `{{Columns-list}}` around the whole list, is not part of it
  (review 2, RV2-3);
- identifiers only as fields of other templates: H, "bibliography entry: …" with the reason.

This rule was added after the first review. The exposed regression showed three `* {{EI2|…|doi=…}}` entries in the
final English holdout that were `unstructured_text` only because the profile does not list EI2. It was therefore
designed on exposed data, and the lift of that split's G5c to 1.000 is not evidence that it generalizes (RV2-11).

**A located identifier outside every unit** (review 2, RV2-2). A hand-written citation with its own DOI beside a C or
G unit gets no `unstructured_text` unit, as before for C: whether it is a second work or part of the template's
citation is not established. Its identifier now carries `IDENTIFIER_OUTSIDE_UNITS`, so it is never silent. In the
retained data this is three identifiers in two Arabic refs where a bot added an archive `{{استشهاد ويب}}` beside a
hand-written citation.

**Identifiers** are unchanged in role, normalization and anchors:
- an identifier inside a G template moves to that unit, keeping the role `unresolved` and the issue
  `TEMPLATE_UNSUPPORTED`;
- an identifier in an H definition or entry, which can only be a field of an unknown template, has no unit.

**Issues** name the renumbered containers and units (RV-2). Before, an issue made before renumbering kept the former
id. That defect predates D-035 and also affected container issues.

## 5. What is deliberately not done

- **Explanatory groups.** A `<ref group="note">` holding prose is still D. A group name is free text, and reading it
  would be a keyword rule. This is a residual risk (RISKS.md R-037), as is the `<ref>` that holds only a comment
  ("Originally: …", seen once in the exposed data).
- **Short link with text.** A Harvard link beside plain text without a locator is H, not D. A genuine second citation
  without a link or identifier there is therefore not claimed. It is reported, not lost silently (RV-12; the owner
  decides this trade-off).
- **No render.** Without a usable render, every template-only definition is H, and so is plain text beside an
  unclassified template. The source alone cannot show what an unlisted template is, and the engine does not guess
  from names. In the retained data this affects one capture whose render failed (`en-906156-a1`, two definitions).
- **Wrapped plain citations.** A whole plain citation inside `{{lang}}`, `{{nowrap}}`, `{{ISBN}}` or `{{URL}}`, with
  no text outside, is H (RV-7).
- **Other magic words without a render.** `{{PAGENAME}}`, `{{#if:}}` and the like are unclassified templates. With a
  render, the note decides; without one, a plain citation holding one is H (RV2-8).
- **A G template holding a template never rendered on its own** (RV2-5). `{{Fishbase|title={{lang|la|…}}}}` is H
  when `{{lang}}` has no transclusion of its own anywhere in the render: nothing shows that it did not make the
  citation markup.
- **Unclassified template without citation markup beside text** (RV-5). `{{NRDB species}} Retrieved …` stays D,
  because nothing separates it from `{{ISBN}}` beside a hand-written citation without a word list.
- **Name-rule templates without evidence** (RV-3). The Arabic Harvard template with no render, or nested, stays C.
  Requiring evidence removed 21 genuine CS1 wrappers from the retained data.
- **No record for E and F** (RV-11). Only H definitions are reported.
- **No profile change.** No template is added to the profile, and the frozen scorer and the guide are unchanged.

## 6. Compatibility

- **Extraction schema 1.1.0** (`x-citerift-version` 1.1.0) adds the unit kind `unsupported_citation_template`.
  Documents of 1.0.0 validate unchanged. A consumer that switches on `kind` must accept the new value.
- **Capture** code is unchanged. A capture records the package version (`citerift.wiki.__version__`) as its client,
  so new captures say 1.1.0 (RV-9).
- **Issue entities** now name the renumbered container or unit (RV-2). A consumer that joined issues to containers
  by id under 1.0.0 could have attached them to the wrong container.
- **Reconciliation** is unchanged. It now also matches a bibliography entry with a G unit to its rendered list item,
  through the template's transclusion, exactly as for a listed citation template. That entry's markers are then
  inspected (`differential/DIFFERENTIAL.md`).
- **Issue codes.** `UNIT_CLASSIFICATION_UNRESOLVED` (warning), `CITATION_TEMPLATE_UNSUPPORTED` (info) and
  `IDENTIFIER_OUTSIDE_UNITS` (warning, review 2) are new.
- **Verification** rebuilds the model through the same function as extraction (`units.source_model`, review 2,
  RV2-1).
- **Engine `citerift-wiki` 1.1.0.** The replay of a document from engine 1.0.0 now stops at
  `REPLAY_IDENTITY_MISMATCH` instead of reporting a digest difference.
- **The frozen scorer is unchanged.** It maps every kind other than `unstructured_text` to "template", so a G unit is
  matched against an annotated template.

## 7. Verification

- **Fail-first:** `tests/stage03/test_g5c_unit_semantics.py`.
  - Before the fix, 39 of 63 cases failed and every control passed (`FAIL_FIRST_BEFORE.txt`).
  - The review fixes and the bibliography rule have their own fail-first record: 27 + 5 new or changed tests fail
    on the reviewed commit `4d44e6c`, and every control passes there (`review/FAIL_FIRST_REVIEW.txt`).
  - After the fix every case passes.
- **Independent review:** `review/REVIEW.md` and `review/DISPOSITIONS.md`; second round `review2/REVIEW.md` and
  `review2/DISPOSITIONS.md`, with its fail-first record `review2/FAIL_FIRST_REVIEW2.txt` (23 of 28 new tests fail
  on `11bb5b2`, every control passes).
- **Differential:** `differential/` covers every retained real bundle, comparing the frozen engine with this one.
  There is no unexpected difference.

**Exposed regression.** Re-scoring the exposed data with the frozen scorer changes only G5c and G5d
(`differential/RESCORE_EXPOSED.txt`, adjudicated labels):

| Campaign | Language | G5c before → after | G5d before → after |
|---|---|---|---|
| 2026-11 confirmation | English | 0.869 → 1.000 | 0.969 → 0.977 |
| 2026-11 confirmation | Arabic | 0.988 → 1.000 | 0.988 → 0.994 |
| Final holdout | English | 0.973 → 1.000 | 0.956 → 0.983 |
| Final holdout | Arabic | 0.981 → 1.000 | 0.981 → 0.981 |
| Run 1 holdout | English | 0.983 → 0.991 | 0.974 → 0.974 |
| Run 1 holdout | Arabic | 0.988 → 0.988 | 0.988 → 0.988 |

G5d falls in no exposed campaign, and in the 44 gate articles of the 2026-11 campaign no labelled unstructured
definition loses its unit (`test_campaign_labelled_unstructured_definitions_keep_their_unit`). The two remaining false positives are residual risks
(`differential/DIFFERENTIAL.md`). **These data are exposed: this is regression evidence only, not a scientific
pass.**
