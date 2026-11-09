# Stage 03 Creative Differentiation Review: the verifiable citation ledger

This review is required by the owner's standing rule (DECISIONS.md D-021; directive section 12). It names the
problem, the mechanism, the nearest prior art, the measured difference, the cost, the failure modes and the test
result.

## 1. Problem

Later stages need to say: "this article, at this revision, cites this identifier, here, in this role, and readers
of that reference see this warning". The usual record behind such a statement is a DOI plus an article URL. That
record cannot be checked again by anyone, and it does not separate three things that a downstream match must not
confuse:

- **Where the identifier sits.** It may be the cited work's field, a notice inside a retraction template, a title,
  prose, or a URL on an External links line. Only the first is the cited work's identifier as the citation states
  it.
- **Which rendered footnote shows that reference, and from which in-text places.** A named reference is reused.
  Markers appear in the render's own order, and templates add or drop footnotes. Pairing by position attaches uses
  to the wrong footnote.
- **What was actually observed about a warning.** A rendered warning, a red link to a missing template, a word in
  the work's own title, hidden text, or nothing that was inspected at all. Collapsing these turns failures into "no
  warning".

## 2. Mechanism

For each captured revision the engine publishes an extraction document. Every claim in it is tied to retained
bytes and can be checked again offline by `citerift-wiki verify` and `replay`:

| Ledger part | What it records | How it is checked |
|---|---|---|
| Source witness | each container, definition, use, unit and identifier occurrence with its exact UTF-8 byte and code-point span, raw text and SHA-256; the role, and the rule that gave it | every span is re-sliced from the source artifact; roles must satisfy the role conditions; normalization is re-run through the Stage 02 normalizer |
| Render witness | for each matched use and container: the rendered element's id (and whether it is unique), its element path, a quote and a subtree digest, under the declared HTML parser profile | every locator is resolved again in the retained HTML |
| Use ledger | every in-article use, its binding (bound, missing, conflicting) and its render state (matched, abstained, unavailable), with the basis of each match | references between entities and the accounting identities are re-checked |
| Marker observations | per reference: source marker templates, and the rendered region's state (`recognized_warning_text`, `ambiguous_text`, `missing_template_link_only`, `no_recognized_warning_in_inspected_region`, `not_inspected`, `unavailable`) with its evidence, always with `browser_visibility: not_evaluated` | one observation per container; evidence quotes the shown text |
| Exception ledger | every unresolved, malformed, unsupported, abstained or failed item with a stable issue code | counts and codes are part of the digest |

The extraction digest covers the capture record and the configuration. Replay re-extracts in an isolated worker and
compares the whole document. No score, probability or model is involved.

## 3. Nearest prior art

- **Wikipedia citation extraction datasets and tools**, for example wikicite and wikiciteparser. They extract
  citation templates in bulk. The inspected wikicite multilingual tree has no Arabic locale. They do not bind
  rendered footnotes, do not anchor every occurrence to bytes, and do not separate roles. Stage 03 uses none of
  their code.
- **W3C Web Annotation selectors** (text quote, position, XPath). The ledger's anchors are in the same spirit: a
  byte span, a quote, an element path, a digest. Revision ids, hashes and selectors are not new.
- **Stage 01 known-identifier confirmation (B0)**: is a known DOI present in the wikitext?
- **A simple structural extractor (B1)**: regular expressions over `<ref>` tags, the k-th use linked to the k-th
  rendered marker, and a warning word in the ref body.

The claim is not novelty of any single element. The claim is the measured difference of the combined, checked
ledger on the guarded properties below.

## 4. Measured difference

The figures come from holdout run 1, scored on adjudicated labels. It used the engine before the repair round
(`d626c06`); the repaired engine's figures are in section 7. B1 and B0 were scored by the frozen scorer with the
same matcher.

**Render linking, holdout:**

| | arwiki engine | arwiki B1 | enwiki engine | enwiki B1 |
|---|---|---|---|---|
| uses correctly linked / linkable uses it matched | 104 / 104 | 79 / 104 | 189 / 189 | 88 / 172 |
| uses linked to a different footnote (false attachments) | **0** | **25** | **0** | **84** |

**Identifiers, holdout:**

| | arwiki engine | arwiki B1 | enwiki engine | enwiki B1 |
|---|---|---|---|---|
| precision / recall | 1.00 / 0.97 | 0.95 / 0.92 | 1.00 / 0.97 | 1.00 / 0.83 |
| definitions found (recall) | 1.00 | 0.99 | 1.00 | 0.75 (B1 does not see list-defined or short-footnote definitions) |

**Notice and marker identifiers given a cited-work role, observed challenge set:**

| | engine | B1 |
|---|---|---|
| arwiki | 0 | 4 |
| enwiki | 1 (before repair RF-36) | 5 |

**Fabricated negative warnings:** engine 0 in every set.

On B0's valid task, every DOI key the evaluator labelled was found in the wikitext (arwiki 34 of 34, enwiki 44 of
44). In the observed challenge set, 4 (ar) and 3 (en) of those found keys were never a cited-work identifier, so a
"key present" answer would wrongly count them as cited works.

**Relocating an annotated cited-work DOI** (FROZEN_PROTOCOL.md section 8), holdout:

- **A:** the DOI plus the revision URL.
  - arwiki: unique in the source for 28 of 39 occurrences (11 ambiguous); the rendered note found for 39 of 39.
  - enwiki: unique in the source for 38 of 50 (12 ambiguous); the note found for 40 of 50, not found for 10.
- **B:** the exact source anchor alone.
  - Relocates the source occurrence for 37 of 39 (ar) and 48 of 50 (en), each correct. The 2 + 2 misses are the
    identifiers the engine did not extract (DOIs in publisher URLs without `/doi/`).
  - Says nothing about the rendered note or the uses.
- **C:** the full ledger.
  - The same source relocation as B.
  - The rendered note: correct for 37 (ar) and 39 (en), with 0 wrong and the rest abstained or unverifiable.
  - Every in-window use of the citing reference (`../evaluation/run-1/relocation_in_window.json`): 45 of 47 (ar)
    and 43 of 50 (en) correct.
  - 0 (ar) and 4 (en) extra links. The 4 come from one article with six identical definitions of the same named
    reference. The metric takes the nearest preceding definition as the DOI's "home", and no uses are bound to
    that duplicate, so the expected set is empty. The links themselves are correct (gate G6: 189 of 189).
  - The frozen relocation figure counts every correct link outside the annotated window as wrong (en: 40). It is
    published unchanged in `scores_adjudicated.json`.
- **Review effort** was not measured; there is no independent way to measure it here.

## 5. Cost

**Record size, holdout:**

| Record | arwiki (39 DOIs) | enwiki (50 DOIs) |
|---|---|---|
| A | 4.0 kB | 5.4 kB |
| B | 10.3 kB | 13.8 kB |
| C (the ledger slice of each DOI's reference) | 131 kB | 182 kB |

The whole extraction document is 0.06 to 1.96 times the size of source plus HTML (median 0.34; 38 articles).

**Extraction time, 38 evaluated articles:**

- warm wall time p50 0.19 s, p95 0.28 s, max 0.32 s;
- cold maximum 0.37 s;
- peak resident set 34 MiB.

Capture costs two HTTP requests per revision, plus retries. During the evaluation, half of all requests were
answered 429, with Retry-After 38 s at the median (`../evaluation/run-1/costs.json`). No model, token or paid
service is used.

## 6. Failure modes

- **The ledger can be wrong where the engine is wrong.** Run 1 had two failures of this kind:
  - PubMed links outside references were given a cited-work role (RF-36, repaired);
  - citation templates missing from the profile were counted as unstructured text (RF-37, partly repaired).

  Verification proves consistency with the retained bytes, not correctness.
- **Abstention costs coverage.** In one observed Arabic article, an unbalanced wrapping template made the engine
  abstain on all 12 render links.
- **Partial support.** Unsupported constructs (subreferences, short-footnote chains, generated references) are
  reported, not resolved.
- **Hashes and anchors bind to captured bytes, not to what readers saw.** Old revisions render with today's
  templates. Two captures of one revision may differ; demonstration 5 shows a render-id-only difference.

## 7. Test result

On the 30 October repaired production code (3d91429, runtime-identical to frozen
candidate 48cfeab), 46 distinct retained real bundles verified and replayed. The
unchanged scorer and historical adjudicated labels give Arabic identifier precision /
recall 59/59 and 59/61, English 56/56 and 56/58; rendered attachments remain 104/104
and 189/189 correct, zero observed false attachments. The structural B1 baseline on
these same exposed holdouts has 25 Arabic and 84 English false attachments. English
unit precision/recall is 114/118 and 114/117. These are exposed-data regression
results, not fresh final acceptance evidence. Locked English definition precision
128/135 is below the gate; the historical adjudicated labels count 135/135. Both
label sets and scores remain published.

The current frozen A/B/C source relocation counts are A:28/39 Arabic,38/50 English;
B and C:37/39 Arabic,48/50 English. Full-ledger rendered-note relocation is 37/39 and
39/50. The declared supplemental in-window C use count is 45/47 and43/50, with zero
and four extra links respectively; the four relate to duplicate-definition homes.
Frozen counts are preserved beside the supplement. Review effort was not measured.

Current resource observations on the 46 retained bundles: extraction p50 0.279 s,
p95 0.499 s; verification p50 0.379 s,p95 0.818 s; maximum worker peak RSS39128KiB.
OS caches were not flushed and the full suite could be running concurrently. The
historical warm/cold figures in section5 are not relabelled as these observations.

The paragraph written on 30 October said the final campaign was still in progress. Its result is reported below.

### 7.1 Final campaign result (frozen candidate `48cfeab`, adjudicated labels, 2026-11-02)

Source: `evaluation/final/run/scores_adjudicated.json`, the frozen scorer, and `evaluation/final/adjudication/README.md`.
There are 16 articles per language. The engine was run once, after the labels were locked.

**What the ledger adds over the structural baseline B1** (same matcher, same labels):

| Measure | ar engine | ar B1 | en engine | en B1 |
|---|---|---|---|---|
| Rendered-footnote attachments, correct / wrong | 119 / 0 | 77 / 30 | 117 / 0 | 99 / 8 |
| Use recall | 1.000 | 0.899 | 0.992 | 0.915 |
| Definition recall | 1.000 | 0.792 | 0.984 | 0.811 |
| Identifier recall | 0.970 (32/33) | 0.848 | 0.963 (52/54) | 0.722 |
| Identifier precision | 1.000 | 1.000 | 1.000 | 0.975 |
| Promotions of notice/marker/title identifiers | 0 | 0 | 0 | 0 |

**A/B/C relocation** of the annotated DOI occurrences (26 Arabic and 43 English, counted per occurrence):

| Approach | Source relocated, ar | Source relocated, en | Rendered note relocated, ar | Rendered note relocated, en |
|---|---|---|---|---|
| (A) DOI plus revision URL | 24 unique and correct; 2 ambiguous | 33 unique and correct; 10 ambiguous | 22 | 32 (11 failed) |
| (C) full ledger | 25 correct | 41 correct | 22 correct; 3 unverifiable; 1 abstained | 31 correct; 7 unverifiable; 5 abstained |

- **Uses:** the ledger relocated 28 of 29 Arabic and 38 of 40 English uses, with 0 and 2 wrong targets.
- **Record size:** the ledger record is about 30 times larger than (A), at 85.6 kB against 2.6 kB in Arabic and
  124.7 kB against 4.4 kB in English.
- **Review effort:** not measured.

### 7.2 What the final campaign did not show

- **No retraction warnings in the sample.** No final-campaign article showed a retraction warning: every marker
  label is `none`. Three English entries were `not_inspected`. G7 (zero fabricated negatives) is therefore met
  trivially and gives no evidence about warning detection on real articles. The warning evidence comes from the
  observed challenge set of run 1, the synthetic F1-F4 and V1/V2 cases, and the retained Obokata fixtures.
- **Frozen gates not met.** The scientific gates are not all met at the frozen candidate:
  - Arabic definition precision is 0.914. The cause is the repeated short-footnote reading, an ambiguity in the
    annotation guide.
  - The Arabic identifier denominator is 33, against a minimum of 50.
  - The English key error rate is 0.0192, from one Wiley page-view URL, since repaired after exposure as RF-60.
- **Consequence for the claim.** The ledger's advantage over B1 is measured. The protocol's full extraction claim is
  not established for Arabic identifiers (`evaluation/final/DECISION_RECORD.md`).

### 7.3 Confirmation campaign result (candidate `3e51792`, adjudicated labels, 2026-11-03)

Source: `evaluation/confirmation-2026-11/campaign/REPORT.md` and `scores/adjudicated.json` there. 24 Arabic and 20
English articles, one prediction run after the labels were locked.

| Measure | ar engine | ar B1 | en engine | en B1 |
|---|---|---|---|---|
| Rendered-footnote attachments, correct / wrong | 189 / 0 | 113 / 76 | 274 / 0 | 168 / 76 |
| Use recall | 1.000 | 1.000 | 1.000 | 0.891 |
| Definition recall | 1.000 | 0.850 | 0.987 | 0.828 |
| Identifier recall | 0.951 (98/103) | 0.466 | 0.960 (48/50) | 0.800 |
| Unit precision | 0.988 | 0.985 | **0.869** | 0.885 |

**A/B/C relocation** of the annotated DOI occurrences (62 Arabic, 42 English):

| Approach | Source relocated, ar | Source relocated, en | Rendered note, ar | Rendered note, en |
|---|---|---|---|---|
| (A) DOI plus revision URL | 44 correct; 18 ambiguous | 34 correct; 8 ambiguous | 35 correct; 25 failed; 2 ambiguous | 40 correct; 2 failed |
| (C) full ledger | 58 correct; 4 failed | 40 correct; 2 failed | 35 correct; 12 unverifiable; 15 abstained | 38 correct; 2 unverifiable; 2 abstained |

- **Uses:** the ledger relocated 45 of 55 Arabic and 48 of 50 English uses, with 1 wrong target in each language.
- **Record size:** 177.0 kB against 6.4 kB (A) in Arabic, 132.9 kB against 4.5 kB in English.
- **What the ledger adds:** no wrong rendered attachment where B1 makes 76 in each language, and higher identifier
  and definition recall. It does not improve unit precision in English, where B1 is slightly higher.
- **Warnings:** on enwiki, 6 of 6 labelled retraction and concern warnings were recognised, with no fabricated
  negative and no false warning. No Arabic positive exists in the frame.
- **Gate not met:** English G5c (R-036). The ledger's `unstructured_text` kind is wider than the guide's
  `unstructured`; see SPECIFICATION 11.3.


### 7.4 D-035 confirmation result (candidate `fff0e5b`, engine 1.1.0, adjudicated labels, 2026-11-03)

Source: `evaluation/confirmation-d035/campaign/REPORT.md` and `scores/adjudicated.json` there. 24 Arabic and 24
English unexposed articles, one prediction run after the labels were locked.

| Measure | ar engine | ar B1 | en engine | en B1 |
|---|---|---|---|---|
| Rendered-footnote attachments, correct / wrong | 182 / **2** | 81 / 59 | 203 / 0 | 143 / 47 |
| Use recall | 0.995 | 0.725 | 0.986 | 0.919 |
| Definition recall | 1.000 | 0.765 | 1.000 | 0.815 |
| Identifier recall | 0.967 (59/61) | 0.639 | 1.000 (60/60) | 0.700 |
| Unit precision | 1.000 | 1.000 | **0.994** | 0.969 |

**A/B/C relocation** of the annotated DOI occurrences (45 Arabic, 39 English):

| Approach | Source relocated, ar | Source relocated, en | Rendered note, ar | Rendered note, en |
|---|---|---|---|---|
| (A) DOI plus revision URL | 39 correct; 6 ambiguous | 36 correct; 3 ambiguous | 30 correct; 14 failed; 1 ambiguous | 32 correct; 7 failed |
| (C) full ledger | 43 correct; 2 failed | 39 correct | 27 correct; 1 unverifiable; 17 abstained | 32 correct; 7 unverifiable |

- **Uses:** the ledger relocated 30 of 45 Arabic uses with none wrong, and 35 of 35 English uses with 3 wrong targets.
- **Record size:** 131.3 kB against 4.6 kB (A) in Arabic, 123.0 kB against 4.2 kB in English.
- **What the D-035 correction adds:** the citation-unit classes remove the English unit-precision gap of 7.3 (0.869
  → 0.994 on fresh articles; B1 0.969), so in English the ledger now equals or exceeds B1 on every measure in the first table.
- **What it does not establish:** Arabic G6b fails. Two of 184 Arabic render links are a same-reference swap inside
  an infobox (RISKS.md R-038), against 59 wrong links for B1. The ledger's claim "no wrong rendered attachment" does
  not hold on this sample; it holds in English (0 of 203).

### 7.5 D-036 confirmation result (candidate `8901a59`, engine 1.2.0, adjudicated labels, 2026-11-09)

- **Render attachment:** 0 wrong render links in 187 Arabic and 282 English engine links, against 35 and 17 wrong for
  B1 (`evaluation/confirmation-d036/campaign/REPORT.md` section 8). The ledger's claim "no wrong rendered attachment" holds on this sample in both languages; it
  failed in Arabic on the D-035 sample (2 of 184) and was corrected under D-036 (RISKS.md R-038).
- **Units and recall:** English unit precision 0.977 against B1 0.960; identifier recall 0.929 / 0.984 against B1
  0.839 / 0.828; use recall 1.000 in both languages against 0.968 / 0.848.
- **What it does not establish:** one sample of 44 articles; the corrected same-name path was exercised on 8 uses
  only; G7 is vacuous (no labelled warning); the labels are AI labels from one vendor.
