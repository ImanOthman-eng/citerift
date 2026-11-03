# Stage 03 risk analysis

Risks of the extraction engine and of its evaluation, with the control in place and the residual risk. Severity
is the effect on Stage 04 and on the claims of this stage if the risk materializes and the control fails.

## 1. Output risks (what a wrong extraction would cause downstream)

| Id | Risk | Severity | Control | Residual |
|---|---|---|---|---|
| R1 | A notice, marker or title DOI is reported as the cited work, so Stage 04 would report "cites a retracted work" for the notice itself | critical | role decision list (SPECIFICATION 11.5), properties P1/P2; synthetic tests; observed regression (STAP notices are `marker_target` in both languages); gate G3a promotions = 0 | a citation template that is itself the notice (`{{cite journal |title=Retraction: …|doi=<notice>}}`) is `primary_citation_field` by markup; deciding that the cited work is a notice is Stage 04's job with the retraction data |
| R2 | An overridden or duplicated field value is taken as the DOI | high | RF-01: last value wins, the overridden value is `unresolved` | none known |
| R3 | A use or marker region is attached to the wrong rendered footnote | high | anchors-and-segments alignment never pairs across a length mismatch; duplicate DOM ids and shared notes are `note_ambiguous` (RF-03); gate G6 | abstentions lower coverage; Parsoid markup changes could make more segments unmatched (fail closed) |
| R4 | "No warning" reported where the reader saw one (fabricated negative) | critical | no path from failure, unavailable render, hidden text or unmatched region to `no_recognized_warning…` (RF-02, MATHEMATICAL_MODEL 6); gate G7 | wording outside the profile terms is not recognized; the state names the inspected region and never says "not retracted" |
| R5 | Wrong normalized key | high | the accepted Stage 02 normalizers unchanged; structural decoding steps recorded; gate G2 | publisher-URL DOI boundaries can be ambiguous (flagged `IDENTIFIER_BOUNDARY_AMBIGUOUS`) |
| R6 | Source and render of different revisions joined | high | header, document, page id, namespace and SHA-1 checks; render without revision statement refused | none known |
| R7 | Missed identifiers (recall) | medium | broad candidate scan (fields, wrappers, URLs, labels, free text); gate G1b | template-generated and Wikidata-generated identifiers exist only in the render (render-only list); `sfn` chains not followed |
| R8 | Language asymmetry: Arabic templates or terms missing from the profile | medium | profile built from inspected template pages in both wikis; Arabic tests; per-language gates | aliases created after the profile build are `TEMPLATE_UNSUPPORTED` / `unresolved`, never silently dropped |

## 2. Operational and security risks

| Id | Risk | Severity | Control | Residual |
|---|---|---|---|---|
| R9 | Load on Wikimedia, rate limiting, policy breach | high | one request in flight across processes (network gate), ≥ 10 s spacing, Retry-After never shortened, `maxlag`, ≤ 3 attempts, fixed User-Agent, no 403 bypass; simulation I1-I7 | Wikimedia answered 429 to a large share of first attempts; captures are slow (about one minute each) by design |
| R10 | Hostile or corrupted bundle or record (path traversal, symlinks, forged records, decompression bombs) | high | strict path and symlink checks, hashes, strict JSON, size limits, replay self-digest (RF-06), configuration validation (RF-04, RF-05) | a local attacker who can rewrite both a bundle and its recorded extraction consistently can forge evidence; bundles are integrity-checked, not signed |
| R11 | Resource exhaustion by a pathological article | medium | worker process with address-space, CPU and wall limits, structural limits; stable failure codes | very large articles fail closed (a 1.8 MB synthetic page with 20 000 references exceeds 30 s) |
| R12 | Executing retained HTML or fetching from it | high | lxml parse only; no script, no resource fetch; worker refuses sockets | none known |
| R13 | Installed wheel without schema files | low | `CITERIFT_SCHEMAS` override (same mechanism as Stage 02); fails closed with `SCHEMA_ROOT_UNAVAILABLE` (tested) | an installed wheel needs the repository's `schemas` directory |
| R14 | Platform without `fcntl`/`resource`/`setsid` | low | network gate and isolated extraction fail closed (`NETWORK_GATE_UNAVAILABLE`, `PLATFORM_UNSUPPORTED`) | Windows is not supported for live capture or isolated extraction |

## 3. Evaluation risks

| Id | Risk | Control | Residual |
|---|---|---|---|
| E1 | Evaluator not independent of the implementation | separate agent instances with their own context, a committed brief that forbids reading engine code, tests or outputs, provenance with file hashes; annotations hash-locked and committed before any holdout extraction (the run driver refuses otherwise) | both are AI agents from the same model family; independence is procedural, not human gold |
| E2 | Thresholds tuned on holdout results | protocol, gates and scorer frozen at `afa0115` before selection; one repair round at most, evaluated on the confirmation split | none |
| E3 | Sample too small to support population claims | minimum denominators, reserve articles, bootstrap intervals and Clopper-Pearson bounds reported; claims limited to the sample | gates are sample checks |
| E4 | Annotation errors | adjudication by a new evaluator instance on disputed items only, with reasons; locked and adjudicated results published side by side | an error shared by evaluator and engine is not detected |
| E5 | Live-data drift (articles edited after selection) | revisions pinned at capture; bundles retained and exported with checksums | the sample describes revisions of 2026-10-28 |

## Risk addendum, 2026-10-30

RF-56/V1 and RF-57/V2 affected supplied result documents with recomputed accounting and
self-digests. Honest extraction was correct in the reported probes. A valid DOM locator
outside the bound reference and a supplied warning substring without its true context
formerly passed verify; full replay detected both. The bounded marker reconstruction
above closes those trust gaps for the tested constructs, including both languages,
repeated words, citation/hidden channels and forged regions. RF-58 prevents malformed
integer-valued float configuration from escaping verification as an uncaught exception.

The original frozen protocol and historical results remain unchanged. The 29 October
amendment authorizes one further fresh final campaign; it does not authorize unlimited
post-exposure tuning. A new session cannot prove what an earlier lost private workspace
read. At recovery the GitHub App omitted citerift and denied writes. On 31 October the owner
enabled access; checkpoint ec9453a was pushed to the existing branch and PR #5, with CI
started. This removes the access blocker but does not establish scientific gate success. Only Linux was exercised here.
Browser visibility remains not_evaluated; DOI/PMID co-reporting does not establish identity.


## Risk addendum, 2026-11-02 (final adjudication and RF-60)

| Id | Risk | Control | Residual |
|---|---|---|---|
| R-03-RF60 | The post-exposure route rule shortens a real DOI whose last suffix segment is exactly a route word (`…/full`, `…/abstract`). | The rule applies only to publisher `/doi/` URLs. The route must be written literally in ASCII, the remainder must still be a DOI, and only one segment is removed. The occurrence stays `IDENTIFIER_BOUNDARY_AMBIGUOUS`. A `doi=` field in the same unit that keeps the longer form is reported as `CO_REPORTED_IDENTIFIERS` (review RV-3). | Not observed in the 70 retained real bundles. Downstream stages must treat an ambiguous-boundary key as unconfirmed. |
| E6 | Adjudicators disagree across campaigns on the same guide wording: run 1 read guide 3.1, the final campaign read 3.2, for repeated identical short-footnote calls. | Both readings and both decisions are published. No label was edited by the executor. | The Arabic definition-precision gate depends on the reading. The guide needs an owner-approved clarification before any future evaluation. |
| E7 | The Arabic identifier sample is too small: 33 target occurrences, against a minimum of 50, with the sampling ceiling reached. | Reported as not met, with the actual denominator. No extra articles were acquired. | With 0 key errors in 32 matched Arabic identifiers, the one-sided 95 % upper bound on the key error rate is 8.9 %. With 1 miss in 33, the upper bound on the miss rate is 13.6 %. These are weaker than the frozen design (5.8 % at 50). |
| E8 | The final sample contains no retraction warning, so G7 is met without any warning present. | Stated in the differentiation review (7.2) and in the handoff. | Real-article warning detection rests on run 1's observed challenge set, the synthetic cases and the Obokata fixtures, not on the final campaign. |

## Risk addendum, 2026-11-02 (owner instruction D-034: semantics, boundaries, acquisition)

| Id | Risk | Control | Residual |
|---|---|---|---|
| R-03-D5 | A labelled or free-text DOI followed by sentence punctuation keeps the punctuation in its key, while the guide's key excludes it. | The boundary is flagged `ambiguous_trailing_punctuation` and `IDENTIFIER_BOUNDARY_AMBIGUOUS`. No suffix-stripping rule is used (`design/doi-boundaries/AUDIT.md`). | Such an occurrence counts as a key error (G2) when the annotator drops the punctuation. One instance is in the retained exposed data. Downstream stages must treat an ambiguous-boundary key as unconfirmed. |
| R-03-D3 | A publisher `/doi/` path with two DOI-shaped segments becomes one key, without an ambiguity flag. | None in the engine. | Not observed in the 70 retained bundles. |
| R-03-D4 | Publisher URLs without a `/doi/` segment (Springer, PLOS, JSTOR) give no identifier. | Outside the guide's definition, so engine and guide agree. | A coverage limit for retraction matching, when the reference gives no `doi=` field. |
| R-03-SFN | Short-footnote calls whose module names collide across fields (`p=5` and `pp=5`), URL-stripped or hyphen-converted page values, more than five positional arguments, or `sfn`-family templates outside Module:Footnotes split where MediaWiki may merge. | The shared rendered note is withdrawn from both containers, which is an abstention and never a false attachment (`design/sfn-semantics/SEMANTIC_DECISION.md`, section 4). | Render-link recall can fall on such articles. The 5 retained bundles with short footnotes are unaffected. |
| R-03-CEIL | Interrupted or unreported runs are charged their worst case (6 attempts, 64 MiB each), so about four of them stop the campaign at the 300 MiB ceiling with no real use (review R7, RF7-7). | Published bundles are adopted with their real cost; gate deferrals cost zero; the driver holds one lock and journals every run (`review/REVIEW_FINDINGS.md`, R6 and R7). | A campaign stopped this way ends with fewer articles; uncaptured articles keep their states and the minimums may stay unmet. |
| R-03-MF1 | A native tokenizer crash is classified by a second run with the pure-Python tokenizer; a page that crashes for a reason other than memory takes up to two worker runs and is reported `EXTRACTION_WORKER_FAILED`. | The second run's output is never an extraction; every extraction uses the C tokenizer (`review/failfirst/mf-1/BEFORE_AND_AFTER.md`). | Such pages give no extraction; they count as failures in G9. |
| E9 | Labels come from AI evaluators (Claude Sonnet) and adjudication from a smaller model (Claude Haiku), all from one vendor. No human gold. | Separate contexts working outside the repository, raw packets only, locks committed before predictions; three distinct models (amendment section 7). | Shared-vendor blind spots cannot be ruled out; adjudication quality is limited by the smaller model. Reported with the results. |

## Risk addendum, 2026-11-03 (confirmation campaign results)

| Id | Risk | Control | Residual |
|---|---|---|---|
| E10 | The engine's `unstructured_text` unit is wider than the guide's `unstructured` (Harvard short-citation links, notes that cite nothing, unlisted citation-like templates); English G5c is 0.869. | Reported as measured, with no repair after the run (RISKS.md R-036). | A downstream stage that reads `unstructured_text` as "cites a work in plain text" would over-count citations. Stage 04 must not. |
| E11 | No Arabic article in the frame transcludes a warning template, so Arabic warning detection has no field evidence. | Stated as a limitation; never counted as a pass. | Arabic warning detection rests on synthetic and fixture tests only. |
| E12 | Six English positives give a wide sensitivity interval ([0.541, 1.000]). | Denominator and interval reported. | Real-article sensitivity below 0.9 cannot be excluded. |
| E13 | The harness attached the repository `CLAUDE.md` to every evaluator and adjudicator context; one evaluator wrote one scratch file outside its work directory. | Both are recorded with the transcripts' audit (`campaign/annotations/EVALUATOR_AUDIT.json`). The file holds no label, output or result. | Independence is procedural and AI-only (E9). |


## Risk addendum, 2026-11-03 (owner instruction D-035: citation-unit classes)

| Id | Risk | Mitigation and evidence |
|---|---|---|
| E14 | **A genuine plain-text citation loses its unit** (false negative of the new rule) | Recognition needs own text or a locator; Harvard-with-text, template-only and explanatory cases are reported (`UNIT_CLASSIFICATION_UNRESOLVED`), not silent. On the three exposed campaigns no labelled unstructured definition loses its unit (`design/unit-semantics/SEMANTIC_DECISION.md` 7). `RISKS.md` (repository root) R-037. |
| E15 | **Explanatory prose in an ordinary `<ref>` stays `unstructured_text`** | Deliberate: a group name or wording would be a keyword rule. Residual false positives remain possible; measured by the D-035 confirmation. R-037. |
| E16 | **Render evidence is attached to the wrong template** | Pairing by the reconciliation key (canonical target and trimmed parameters) gives equal keys equal expansion. Conflicting outputs, multi-part, unexpanded and missing outputs give no evidence (tests `test_conflicting_render_evidence_is_unresolved`, `test_omitted_template_is_unresolved`). A template with no transclusion at all is decided by its definition's matched note only under the conditions of SPECIFICATION.md "Note evidence"; with two such templates and a mark in the note nothing is attributed (`test_template_without_own_render_output_is_decided_by_its_note`, `test_g5c_review2.py::test_the_rendered_note_decides_only_what_it_can_attribute`). |
| E17 | **Consumers of extraction documents meet a new unit kind** | Additive enum value; schema and engine 1.1.0. Old documents validate. Replay of 1.0.0 documents reports `REPLAY_IDENTITY_MISMATCH`. |
| E18 | **The corrected candidate is confirmed on data that shaped the fix** | Forbidden: the 2026-11 data are exposed and used only as regression. One prospective bilingual confirmation excludes both earlier confirmation campaigns (amendment of D-035). |
| E19 | **A memory failure at the worker limit is reported as a worker failure** (CPython raises `SystemError: error return without exception set` when a frame-stack chunk cannot be allocated) | Classified as `EXTRACTION_MEMORY_EXCEEDED` only for that exact message and a peak address space at the limit (SPECIFICATION.md, "MF-1 v3"); otherwise `EXTRACTION_WORKER_FAILED`. A C-extension bug with the same message while the process is at the limit would be reported as memory: both stop the extraction with an error, and no output is used. |
| E20 | **A formatting wrapper is taken for a citation because its render holds a nested citation's markup** (review RV-1) | A template that holds a citation-like template is never G; the nested citation is the unit (`test_a_wrapper_around_a_citation_template_is_not_a_second_unit`). |
| E21 | **An issue names the wrong container or unit** (review RV-2; 14 cases under the frozen engine in the retained data) | Issues are remapped at every renumbering. The differential checks that every container- or unit-naming issue fits its entity (`design/unit-semantics/differential/DIFFERENTIAL.json`, `issue_entities`: 14 → 0). |
| E22 | **Changes after the independent review are not reviewed** | The review fixes, the bibliography-entry rule and MF-1 v3 got a second independent review before the candidate is frozen (`design/unit-semantics/review2/`: 1 high, 5 medium, 4 low, 1 info; dispositions in `review2/DISPOSITIONS.md`). Its fixes are small, fail-first, differential-checked and verified on all 146 retained bundles; per D-035 section 6 there is no third round, and the prospective confirmation measures the result. |
| E23 | **A correct extraction fails offline verification** (review 2, RV2-1: the marker reconstruction built the model without render evidence) | Extraction, replay and verification share `units.source_model`. All 146 retained bundles verify (`design/unit-semantics/differential/VERIFY.txt`); tests `test_a_bibliography_entry_with_a_g_unit_verifies`, `test_the_final_holdout_bundle_with_bibliography_g_units_verifies`. |
| E24 | **A hand-written citation beside a template unit is lost silently** (review 2, RV2-2) | Its located identifier carries `IDENTIFIER_OUTSIDE_UNITS`; no unit is guessed. R-037. |
| E25 | **List-defined, `{{refn}}` and infobox refs are unresolved although their render is complete** (review 2, RV2-4) | Decided by the matched note (E16). Remaining: refs whose container matches no single note. R-037. |


## Risk addendum, 2026-11-03 (D-035 confirmation campaign results)

| Id | Risk | Control and evidence | Residual |
|---|---|---|---|
| E26 | **A rendered marker is attached to the wrong use of the same reference** when a template (an infobox) renders its rows in another order than the source: `_align_unordered` pairs repeated names in source order. Observed in `ar-76814232`; Arabic G6b fails (2 against a limit of 1). | Preserved and reported, not repaired (amendment section 8). RISKS.md R-038; `evaluation/confirmation-d035/campaign/REPORT.md` section 5. | Until corrected, a downstream stage may show a warning in the wrong infobox row. The cited work and its identifiers are the same for both markers. |
| E27 | **Captured third-party content holds a secret-shaped string** (a public academia.edu presigned URL with an AWS access key id in one enwiki article). | The Stage 00 secret scan failed in CI; the five files are untracked, ignored, listed with sha256 in `campaign/WITHHELD_FILES.json`, checked by audit check 10, and exported with checksums outside git. The accepted Stage 00 test is unchanged. | Anyone re-running the campaign from git alone lacks those five files; the export holds them. Later captures can meet the same pattern; run the secret scan before committing captured content. |
| E28 | **G7 is met vacuously.** No drawn article has a labelled warning, and this campaign has no warning challenge (amendment section 3). | Stated in the report (section 7). Marker code is unchanged since the D-034 challenge (6 / 6 detected). | Field sensitivity rests on the D-034 challenge on the earlier engine. |
| E29 | **A partial capture would have been left out by the frozen packet tool.** | `scripts/make_packets_partial.py` changes exactly one guard; recorded as a deviation (`campaign/REPORT.md` section 6). | None on labels: the article was labelled and scored on its source. |
