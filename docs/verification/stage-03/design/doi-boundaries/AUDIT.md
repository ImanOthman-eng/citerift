# DOI/PMID boundary audit (2026-11-02)

Authority: the owner's instruction of 2026-11-02, section 4 (DECISIONS.md D-034). The question was whether keys and
occurrences follow the annotation guide (3.5 "Key") and MediaWiki's link behaviour at every boundary the instruction
lists, without a general suffix-stripping rule and without changing the Stage 02 contract.

Method: the probes `probe.py` (decoder on 32 URL forms) and `probe2.py` (full extraction of 14 reference texts),
with outputs retained in `probe.out.txt` and `probe2.out.txt`, plus a survey of the publisher URLs in the 70 retained
(exposed) real bundles. Every fix has a fail-first test and a real-data impact check.

## RF-60 and its review R5: verified, not reimplemented

- `tests/stage03/test_wiki_rf60_page_view_segment.py` passes at this revision. The fail-first evidence in
  `../../review/failfirst/rf-60/` is unchanged.
- The probes confirm the behaviour: one literal route at the end of a `/doi/` path is removed, with or without a
  trailing `/`, and after a query or fragment has been removed. The boundary stays flagged. A route word inside the
  suffix (`…/doi/10.1080/1234/full`) is treated as a route, which is the declared residual risk R-03-RF60.
- RV-1 (ASCII-only matching) and RV-2 (`\Z` anchoring) are in place.

## Matrix

| Boundary | Behaviour at this revision | Verdict |
|---|---|---|
| Page-view route after the DOI | removed once (RF-60) and flagged | as specified |
| Route word inside the suffix | removed and flagged (R-03-RF60) | residual, declared |
| Prefix route `/doi/abs/`, `full/`, `pdf/`, `epdf/`, `book/`, `reader/` | skipped | as specified |
| Mixed case `/DOI/`, `ABC` | path matched case-insensitively (ASCII); ASCII letters lower-cased by the Stage 02 normalizer | as specified |
| Percent-encoding in a resolver URL | decoded once by Stage 02 | as specified |
| Percent-encoding in a publisher path, `%2F` between prefix and suffix | **no occurrence at all** | **defect D-2, fixed** |
| HTML character reference in a bare URL inside a template field (`url=…&amp;…`) | **entity kept in the key** | **defect D-1, fixed** |
| Query and fragment | removed (step `URL_QUERY_FRAGMENT_REMOVED`) | as specified |
| Nested URL (archive snapshot of a DOI URL) | excluded, reason `other_site_url` | as specified |
| Trailing punctuation after a free URL | MediaWiki's free-link boundary (a final `.` is outside the link; a final `)` is outside unless the URL has `(`) | as MediaWiki |
| Trailing punctuation after a labelled or free-text DOI | **kept in the key and flagged `ambiguous_trailing_punctuation`** | **D-5: guide divergence, not changed** (below) |
| Trailing punctuation inside a field value or link target | kept as written | as specified |
| Two DOI-shaped segments in one `/doi/` path (`/doi/10.1002/abc/10.1003/def`) | one key, the whole path; not flagged | residual D-3 (below) |
| Publisher URLs without `/doi/` (Springer `/article/10.…`, PLOS `?id=10.…`, JSTOR `/stable/10.…`) | no occurrence | outside the guide's definition; residual D-4 |
| Co-reported identifiers in one unit | every occurrence kept, never merged; `CO_REPORTED_IDENTIFIERS` when keys differ | as specified |
| PMID leading zeros, PMC URLs | null key (Stage 02 rule); PMC is not a PMID | as specified |
| Stage 02 contract | `normalize_doi` / `normalize_pmid` are called unchanged; `src/citerift/retraction` is not modified | unchanged |

## Fixes

**D-1. Character reference in a bare URL inside a field.**

- Root cause: `_plain` in `source.py` decoded entities in plain text nodes of a field value, but returned a bare
  `ExternalLink` node verbatim.
- MediaWiki decodes character references in a link target, and the guide decodes HTML entities.
- Fix: a bare URL in a value is flattened with the same decoding, and the steps are recorded.

**D-2. `%2F` separator in a publisher DOI path.**

- Root cause: `_DOI_PATH` required a literal `/` after the prefix, so the URL matched nothing and the identifier was
  silently lost.
- The guide percent-decodes a URL once.
- Fix: the pattern also accepts `%2F`/`%2f`, and the existing single percent-decoding resolves it.

**Fail-first evidence:** `tests/stage03/test_wiki_doi_boundaries_d1_d2.py` and `../../review/failfirst/doi-d1-d2/`.
Against the source of cb305bf, 7 failed and 8 controls passed. After the fix, 15 passed.

**Real-data impact:** none of the 70 retained bundles changes (`real_bundles_impact.json`).

## Not changed

**D-5. Sentence punctuation after a labelled or free-text DOI.**

- The guide says that trailing sentence punctuation which is not part of the DOI is not part of the key.
- The specification (11.4) keeps it and flags `IDENTIFIER_BOUNDARY_AMBIGUOUS`, "never trimmed silently".
- The existing test `test_wiki_links_wrappers_labels_and_pubmed_urls` pins that behaviour.

A trimming rule was drafted and withdrawn, for three reasons:

1. It contradicted that existing test.
2. The instruction forbids a general suffix-stripping rule based on a few examples.
3. A final `.` is legal DOI syntax, so trimming invents a key in the rare case where it belongs to the DOI.

The engine keeps the boundary undecided and flags it. Consequences:

- An annotator key without the punctuation counts as a key error (G2), and this is reported, not hidden.
- One instance exists in the retained exposed data: `run__holdout__ar-1812799-a1`, `10.2307/2408747.`.
- This is risk R-03-D5 in RISK_ANALYSIS.md.

**D-3. Two DOI-shaped segments in one publisher path.** The whole path becomes the key, with no ambiguity flag. No
instance appears in the retained data. Recorded as a residual risk.

**D-4. Publisher URLs without a `/doi/` segment.** These are outside the guide's key definition, so the engine and
the guide agree. It is a coverage limit for retraction matching (8 `link.springer.com/10.1007/…` URLs appear in the
retained data). Recorded as a residual risk.
