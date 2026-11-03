# What a citation unit is: classes A-H (owner instruction D-035)

Status: implemented on the PR #5 branch after the fail-first commit `907d30d`. Engine 1.1.0, extraction schema 1.1.0.
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
| F | an explanatory note (the profile's `efn` family) whose own text gives no locator; or an empty definition | no unit |
| G | a template the profile does not list whose render is a CS1/CS2 citation | `unsupported_citation_template` (new kind), with the issue `CITATION_TEMPLATE_UNSUPPORTED` |
| H | a definition whose citation unit cannot be established safely | no unit; issue and ledger entry `UNIT_CLASSIFICATION_UNRESOLVED` naming the definition and the reason |

E and F have no unit of their own:
- an E link cites a work whose unit is the bibliography entry it points to;
- an F note cites nothing itself;
- a ref nested in an E or F definition is a definition of its own and is classified by itself.

H is an abstention, not a classification. It records that nothing in the markup or the render decides between a
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
- kind `other`;
- templates that are citation templates only by the RF-37 name rule (family `unlisted`).

A template gets no evidence in these cases:
- its transclusion has several parts;
- MediaWiki stopped expanding it (a parser-limit warning);
- it has no transclusion of its own, as for a ref inside an infobox parameter;
- its calls with one key disagree.

The survey of every retained bundle (`evidence/render_evidence_survey.txt`, 146 real bundles, before the fix)
separates the template families without exception:
- every profile citation template has `citation_markup`;
- every `Harvnb`, `Harvp`, `Harv` and `استشهاد بهارفارد دون أقواس` call has `short_citation_link` and no citation
  markup;
- identifier wrappers, archive, ISBN, maintenance and marker templates have neither.

The profile is not changed. Its digest is unchanged.

## 4. Rules (`model.py`, `_plain_definition`; first rule that applies)

**Template units.** A profile citation or external-data template is C, as before, except for one case:
- a template that is a citation template only by the RF-37 name rule;
- whose render is a short-citation link.

That template is a link (E), not a citation. In the retained data this is the Arabic Harvard template
`استشهاد بهارفارد دون أقواس`. A kind-`other` template whose render has citation markup, called inside a ref and
not inside another template of that ref, is G. A definition with a C or G unit gets no `unstructured_text` unit,
which is unchanged for C.

For any other definition of a `<ref>`, list-defined, `#tag` or generated note (short footnotes excluded, as before):
1. it gives a locator itself (an own external link, or a DOI/PMID in its text or in a profile wrapper): D;
2. it has own text:
   - beside a short-citation link: H (the text may be a comment, a quotation or a second citation);
   - in an explanatory footnote (`efn`): F;
   - otherwise: D (the `<ref>` mechanism is the evidence that its text is a citation);
3. no own text:
   - every template in it is a short-citation link: E;
   - some other template: H (its render shows no citation markup, or there is no usable render);
   - nothing at all: F (empty).

**Bibliography entries** are unchanged. An entry without a template was made from an identifier on its line.

**Identifiers** are unchanged in role, normalization and anchors:
- an identifier inside a G template moves to that unit, keeping the role `unresolved` and the issue
  `TEMPLATE_UNSUPPORTED`;
- an identifier in an H definition, which can only be a field of an unknown template, has no unit.

## 5. What is deliberately not done

- **Explanatory groups.** A `<ref group="note">` holding prose is still D. A group name is free text, and reading it
  would be a keyword rule. This is a residual risk (RISKS.md R-037), as is the `<ref>` that holds only a comment
  ("Originally: …", seen once in the exposed data).
- **Short link with text.** A Harvard link beside plain text without a locator is H, not D. A genuine second citation
  without a link or identifier there is therefore not claimed. It is reported, not lost silently.
- **No render.** Without a usable render, every template-only definition is H. The source alone cannot show what an
  unlisted template is, and the engine does not guess from names.
- **No profile change.** No template is added to the profile, and the frozen scorer and the guide are unchanged.

## 6. Compatibility

- **Extraction schema 1.1.0** adds the unit kind `unsupported_citation_template`. Documents of 1.0.0 validate
  unchanged. A consumer that switches on `kind` must accept the new value.
- **Issue codes.** `UNIT_CLASSIFICATION_UNRESOLVED` (warning) and `CITATION_TEMPLATE_UNSUPPORTED` (info) are new.
- **Engine `citerift-wiki` 1.1.0.** The replay of a document from engine 1.0.0 now stops at
  `REPLAY_IDENTITY_MISMATCH` instead of reporting a digest difference.
- **The frozen scorer is unchanged.** It maps every kind other than `unstructured_text` to "template", so a G unit is
  matched against an annotated template.

## 7. Verification

- **Fail-first:** `tests/stage03/test_g5c_unit_semantics.py`. Before the fix, 39 of 63 cases failed and every
  control passed (`FAIL_FIRST_BEFORE.txt`). After the fix and the review additions, every case passes.
- **Differential:** `differential/` covers every retained real bundle, comparing the old engine with the new one.

**Exposed regression.** Re-scoring the exposed data with the frozen scorer changes only G5c and G5d:

| Campaign | Language | G5c before → after | G5d before → after |
|---|---|---|---|
| 2026-11 confirmation | English | 0.869 → 1.000 | 0.969 → 0.977 |
| 2026-11 confirmation | Arabic | 0.988 → 1.000 | 0.988 → 0.994 |
| Final campaign | Arabic | 0.981 → 1.000 | — |
| Run 1 | English | 0.983 → 0.991 | — |

No labelled unstructured definition loses its unit. **These data are exposed: this is regression evidence only, not
a scientific pass.**
