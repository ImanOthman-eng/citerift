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

