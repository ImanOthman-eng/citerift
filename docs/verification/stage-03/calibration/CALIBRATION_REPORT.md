# Stage 03 calibration report (directive section 6, steps B and C)

Status: written on 2026-10-28, after the development experiments and before the
evaluation protocol was frozen (`../protocol/FROZEN_PROTOCOL.md`). Every number
below comes from the development split only. No holdout article had been
selected, captured or seen when this report was written.

## 1. Development corpus

Selection: `dev_selection.json` (fixed before collection) and
`dev_selection_supplement.json` (fixed after the first acquisition run, before
any extractor output was inspected; it records why). Collected by
`scripts/acquire_dev.py` (one request in flight, at least 10 s between
requests, Retry-After honoured, descriptive User-Agent).

| Wiki | Article | Revision | Why it is in the corpus |
|---|---|---|---|
| en | Haruko Obokata | 1372543632 | Stage 01 positive chain; `{{Retracted}}` renders |
| en | MMR vaccine | 1381772671 | Stage 01 positive chain |
| en | GFAJ-1 | 1374726997 | Stage 01 positive paper |
| en | Wakefield MMR-autism fraud | 1379489342 | notice and original cited together |
| en | Aspirin | 1380653302 | ordinary medical citations |
| en | Tardigrade | 1382117018 | ordinary biology citations |
| en | Lancet MMR autism fraud | 1372484806 | redirect page (kept as a redirect case) |
| ar | هاروكو أوبوكاتا | 76190003 | Stage 01 rendered check: red link to missing `قالب:Retracted` |
| ar | لقاح الحصبة والنكاف والحصبة الألمانية | 72523566 | Stage 01 rendered check |
| ar | فضيحة شون | 75286968 | Stage 01 census: visible retraction wording |
| ar | 2020 في العلوم | 76077251 | Stage 01 census: citation not found in the render |
| ar | أسبرين | 76203761 | ordinary medical citations |
| ar | بطيء الخطو | 76386528 | ordinary biology citations |
| ar | بطيئات المشية | 17146468 | redirect page (kept as a redirect case) |

Stage 01's findings are not repeated or extended here: these revisions were
chosen because Stage 01 named them, and only this stage's own measurements are
reported.

The development bundles were built by `scripts/build_dev_bundles.py`, which
replays the recorded answer bytes through the production `capture_revision`
with a scripted transport and clock. Rebuilding them gives byte-identical
`capture.json` files (checked on 2026-10-28). Their timestamps and attempt lists
are those of the replay; the real requests, including every HTTP 429, are in
`acquisition.json` of the evidence export. The two redirect pages fail capture
with `REDIRECT_NOT_FOLLOWED`, as specified.

## 2. Decisions taken from the development evidence

| Decision | Evidence | Alternative rejected |
|---|---|---|
| Render = Core REST `/w/rest.php/v1/revision/{id}/html` (Parsoid HTML 2.8.0) | On the five revisions fetched both ways, the Action API `parse` HTML carried 10-23 `data-mw` attributes and no `about` groups; the REST HTML carried 149-411 `data-mw`, 182-541 `about` attributes, the revision id in a header and in the document, the page id, namespace and the revision SHA-1 | `action=parse`: no reference attributes, no template grouping, so source/render reconciliation would rest on text similarity |
| HTML parser = lxml 6.1.3 (libxml2 2.14.6) | `parser_qualification.json`: lxml and selectolax 1.0.2 (Lexbor) gave identical reference facts on all 15 captures and 3 malformed variants; lxml 0.20 s / 58 MB against Lexbor 0.11 s / 61 MB on the 4 MB page | selectolax: faster, but no gain in correctness, and lxml gives element paths (`getpath`) for locators directly |
| Wikitext parser = mwparserfromhell 0.7.2 | lossless round trip and offset validation on all 12 sources; known divergences from MediaWiki (unclosed `<ref>`, unclosed comment) are detected and reported (`REF_UNCLOSED`, comment cut) | none qualified (wikitextparser is GPL, excluded by the directive) |
| Profile v1 built from fetched template evidence | `profile_evidence.json` and `scripts/build_profile.py`; provenance with page revisions and the profile's SHA-256 in `profile-v1.provenance.json` | a hand-written template list |
| Worker address-space limit 1024 MiB (initial ceiling 512 MiB) | a synthetic page at the size limits (3.7 MB source, 16.0 MB HTML) peaked at 455 MiB address space (414 MiB resident) (section 3), leaving 11 % margin under 512 MiB | 512 MiB: a page at the declared size limits could fail on memory alone |
| Worker wall deadline kept at 30 s | the same synthetic page took 18.2-19.1 s (three runs) after the fixes in section 4 | |
| Network policy kept as the initial ceilings (10 s interval, 3 attempts, 30 s per operation, 180 s per capture) | section 3: Retry-After values 19-49 s fit two retries inside 180 s | shorter deadlines would turn ordinary 429s into deferred captures |

## 3. Measured costs

Extraction, measured by `scripts/measure_costs.py` (the production worker code
in a fresh interpreter; one cold run and the median of five warm runs per
bundle; Python 3.12.3; peak resident set VmHWM and peak address space VmPeak):

| Bundle | Source bytes | HTML bytes | Output bytes | Status | Warm wall s | Peak RSS MiB | Peak address space MiB |
|---|---|---|---|---|---|---|---|
| en Obokata | 20,444 | 116,074 | 85,029 | complete | 0.18 | 29 | 52 |
| en GFAJ-1 | 43,137 | 292,011 | 217,503 | complete | 0.25 | 33 | 53 |
| en MMR vaccine | 56,971 | 422,679 | 304,115 | complete | 0.28 | 36 | 54 |
| en Wakefield fraud | 69,896 | 509,313 | 299,879 | complete | 0.30 | 37 | 54 |
| en Tardigrade | 73,851 | 606,913 | 343,728 | complete | 0.34 | 39 | 55 |
| en Aspirin | 177,851 | 1,347,700 | 1,093,513 | partial | 0.72 | 55 | 66 |
| ar أوبوكاتا | 28,115 | 171,603 | 84,791 | partial | 0.21 | 30 | 53 |
| ar لقاح | 48,529 | 330,222 | 174,057 | complete | 0.27 | 33 | 54 |
| ar فضيحة شون | 48,709 | 311,159 | 221,853 | complete | 0.28 | 33 | 54 |
| ar بطيء الخطو | 58,385 | 425,174 | 198,588 | complete | 0.28 | 35 | 54 |
| ar أسبرين | 153,134 | 775,258 | 473,991 | complete | 0.48 | 45 | 60 |
| ar 2020 في العلوم | 922,993 | 4,006,778 | 3,269,426 | partial | 2.93 | 128 | 143 |

Summary over the 12 bundles: wall p50 0.28 s, p95 0.72 s, max 2.93 s; cold
runs p50 0.29 s, max 3.24 s; peak RSS p50 36 MiB, max 129 MiB. Every run of
every bundle gave the same extraction digest. Importing the extractor takes
0.11 s. Bundles take 1.3-1.5 times their source plus HTML on disk.

Synthetic stress bundles (`scripts/stress_bundle.py`, labelled synthetic: the
largest development page repeated, with a consistent fake revision): twice the
size (1.8 MB source, 8.0 MB HTML) took 6.8-7.1 s and 260 MiB address space; four
times (3.7 MB source, 16.0 MB HTML, the declared limits) took 18.2-19.1 s and
455 MiB address space (414 MiB resident) in each of three runs. Before the performance fixes of section 4 the four-times bundle
took 28.9 s, within 4 % of the 30 s deadline.

Network (from the acquisition logs, 72 requests): 44 answered 200, 27 answered
HTTP 429 (37.5 %), one Parsoid render answered 504 after 15.4 s. Retry-After
p50 39 s, max 49 s. Accepted bodies: 3.1 MB on the wire, 17.0 MB decompressed.
Most of a capture's wall time is waiting imposed by the server, not computation.

## 4. Errors found on the development split and what was changed

Each row is a defect or gap found by inspecting extraction output against the
raw source and HTML. "Before" outputs are kept in the evidence export
(`failfirst/`) where they were retained; rows marked "described" were fixed
before the outputs were kept, and only the description is evidence.

| Id | Found | Change | Before | After |
|---|---|---|---|---|
| CAL-01 | infobox templates render their reference parameters in their own order, so in-order alignment failed | uses inside one template's output pair by name, or as the single remaining anonymous use, regardless of order | described | all uses of Infobox drug/Ubl except two paired |
| CAL-02 | anonymous refs inside templates could not be paired | content pairing: a source ref and a rendered note pair when they share a unique URL and no other candidate does | described | |
| CAL-03 | `{{sfn}}` uses were not located (the generated `sup` carries the template's `about` itself) | the element's own `about` counts | described | |
| CAL-04 | notes inside `{{reflist}}` took the reflist's `about` and looked template-generated | the transclusion lookup stops at the `cite_note` list item | described | |
| CAL-05 | unstructured bibliography entries had no render counterpart | matched by a unique URL `href` in the list item | described | |
| CAL-06 | `pubmedhealth/` paths were read as PubMed ids | the PubMed path must be `/pubmed` followed by `/` or the end | described | |
| CAL-07 | units in refs written inside infobox parameters were reported "unmatched", although the render marks no template output inside such notes | `region_only`: the note is the region | described | |
| CAL-08 | ar 2020 في العلوم: MediaWiki stopped expanding templates (post-expand include size limit) and left `<!-- WARNING: template omitted ... -->`; the extractor's worker failed on an issue code missing from the catalog | the warning comments are read; affected identifiers are `render_template_omitted`, affected marker regions `not_inspected`, the render component `partial` | worker failure, described | 225 identifiers and 351 regions explicitly not inspected |
| CAL-09 | quadratic lookups (transclusion by `about`, element by path, container by id, unit by definition) made the four-times stress bundle take 28.9 s | dictionary indexes; no output change (all 12 development extractions replayed to the same digests) | 28.9 s | 18.2-19.1 s (final code, three runs) |
| CAL-10 | the 512 MiB initial memory ceiling left 11 % margin at the declared size limits | 1024 MiB | 455 MiB of 512 | 455 MiB of 1024 |
| CAL-11 | en Aspirin: cite templates wrapped in `{{citation-attribution|1=...}}` were "unmatched" because only the outer template has a transclusion | a unit is matched through its outermost enclosing template inside the ref (`within_matched_template`) | 5 units unmatched | 5 within_matched_template |
| CAL-12 | ar أوبوكاتا: a ref inside an infobox parameter that the Wikidata-driven infobox does not display was "abstained" | an unpaired use is `source_only` when no unpaired rendered use could be its counterpart; `abstained` stays for ambiguous pairings | abstained | source_only (checked: the ref text appears only inside the infobox's `data-mw`) |
| CAL-13 | bare URLs in citation URL parameters were reported twice (once as the parameter value, once as the free link node inside it), the second copy without normalization | a free external link without brackets counts as text in a parameter value; new accounting check "no source span reported twice for one scheme" | `failfirst/CAL-16_before`: ar لقاح id-00009/id-00010 share bytes 13258-13298; 20 duplicates over 6 articles | no duplicates |
| CAL-14 | `biorxiv=` (and `medrxiv=`) DOIs were textual mentions | the CS1 BIORXIV and MEDRXIV identifier handlers are read from the CS1 configuration into the profile as DOI fields; with `doi=` in the same template the two DOIs are co-reported, neither chosen | `failfirst/CAL-17_before`: 6 textual_mention | 6 primary_citation_field, 2 CO_REPORTED_IDENTIFIERS |
| CAL-15 | URLs with a `/doi/` path on publisher hosts outside the first five (ahajournals.org, bioone.org, royalsocietypublishing.org) were not identifier links | the `/doi/` path rule applies on any host; a path ending in a page-view segment (`/abstract`, `/full`, ...) keeps the whole DOI and is marked `IDENTIFIER_BOUNDARY_AMBIGUOUS` | `failfirst/CAL-18_before` | 3 more identifier links |
| CAL-16 | en Aspirin: an infobox ref with `pmid=` could not be paired (no URL in the ref) | content pairing also uses normalized DOIs and PMIDs shown as links in the note (`unique_identifier_in_reference_text`) | `failfirst/CAL-19_before` | paired; the remaining `{{PubChem}}` ref stays abstained |

Checked and left as they are (correct behaviour, recorded here):

- ar 2020 في العلوم: an unclosed `<ref>` makes MediaWiki merge the following
  reference; 9 source uses and 8 rendered uses cannot be paired one to one, and
  the extractor abstains on them instead of guessing.
- arwiki infoboxes built from Wikidata render references and identifiers that
  the article's wikitext does not contain (88 rendered uses and 8 identifier
  links in ar أسبرين); they are reported as render-only, never attached to a
  source reference.
- DOIs inside archive URLs (`web.archive.org/web/.../doi/...`) and DOIs used as
  ref names (`<ref name="10.1093/mnras/staa1635">`) are not identifier
  occurrences.
- Missing marker templates on arwiki (`قالب:Retracted`, `قالب:Erratum`) render
  as red links: `missing_template_link_only`, never a recognized warning.
- Cited titles that contain "Retraction" are `ambiguous_text`, never a
  recognized warning.

## 5. What calibration does not show

- No precision or recall: the development corpus was chosen on purpose, and the
  inspection above is the implementer's own. The evaluation numbers come only
  from the frozen protocol's holdout, annotated by a separate evaluator.
- The costs are from one 4-vCPU Linux container; Windows and macOS are not
  measured (the worker's process limits are POSIX-only and report
  `PLATFORM_UNSUPPORTED` elsewhere).
