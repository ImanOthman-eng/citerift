# Owner directive: Stage 03 execution (retained evidence)

- Owner reference: `cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`
- Author: EVE TELOS (project owner), project chat of the CITERIFT project
- Sent: 2026-10-28T18:05:56Z (platform time)
- Delivered to the Stage 03 executor (a Claude Code session in a project thread)
  by the project coordinator, with the message attached by id.
- Retained here by the executor on 2026-10-28. The text below was transcribed
  from the platform's copy of the message. It is a copy for audit, not a
  signature: byte identity with the platform record is not machine-verified
  (RISKS.md R-002).

---

CITERIFT — STAGE 03 EXECUTION DIRECTIVE

Wikipedia Extraction Engine من — full implementation, verification, and unmerged PR

Owner: EVE TELOS · IM | Issued: 28 October 2026, UAE time

You are Claude Code, working in the existing CITERIFT cloud repository as the Stage 03 engineering executor.

CITERIFT — Created and Directed by EVE TELOS · IM.
Repository: https://github.com/ImanOthman-eng/citerift

This is an execution directive, not another planning-only request. The owner authorizes complete Stage 03 within the boundaries below: repository inspection, calibration, specification elaboration, permitted dependency qualification, simulations, implementation, specialist review, correction, real-data evaluation, documentation, commits, and an UNMERGED pull request.

Work autonomously inside this scope. Do not return a proposal instead of an implementation. Do not ask the owner to repeat this authorization at each routine checkpoint. The owner retains final acceptance and personally performs the merge. Never accept your own stage, merge the PR, or begin Stage 04.

The earlier Stage 03 draft was design-only. Delivery of THIS directive by the owner supplies the implementation authorization. It delegates routine engineering choices and pilot-informed numerical protocol refinement as specified below; it does not retroactively approve measurements, annotations, or results that have not happened.

1. Operate as a specialist engineering team

Exercise professional judgment, challenge weak assumptions, compare alternatives, and improve the design where there is demonstrable value. Do not follow this document mechanically when a simpler or more reliable implementation achieves the same contract.

If your cloud environment supports agents, use separate focused roles, with a coordinating architect and explicit write ownership:

• architecture/data contracts and integration;
• Arabic/English citation extraction and Wikimedia behavior;
• adversarial QA, security, and resource containment;
• performance/reproducibility;
• a NON-IMPLEMENTING evidence inspector/evaluator and product/scientific reviewer.

Roles may be combined when justified. Keep evaluation annotations separate from implementation. Parallelize independent work, not concurrent edits to the same files. Do not add an agent framework to the product. If separate agents are unavailable, perform distinct review passes and disclose that they were self-review; never invent independent reviewers.

As you work:

• review each meaningful change and its callers, schemas, tests, and error paths;
• test behavior before and after fixing a discovered defect;
• preserve fail-first evidence for material fixes;
• pause agent edits during clean-revision verification;
• continue fixing within-scope defects until the final checks pass;
• report short progress updates with findings and decisions, not repeated permission questions.

No finite test suite proves zero bugs. Do not promise or report “error-free.” The required standard is genuine verification, no concealed failure, no known unresolved material in-scope defect, and clearly disclosed limitations.

Cloud execution is allowed. It does not authorize paid APIs, purchased services, unbounded jobs, new credentials, access-control changes, or new infrastructure subscriptions.

2. Establish the live baseline and preserve accepted work

Confirmed baseline immediately before this directive:

• main: 94ac4f8df27383a03a810a4501ed1439bf8bcaea.
• PR #4 is merged.
• post-merge GitHub Actions run 40724667988: completed/success at that SHA.
• Stages 00, 01, 02: ACCEPTED_CLOSED and merged.
• Stage 03: NOT_STARTED, authorization=null, owned_paths=[].
• Stage 03 acceptance gate 03-A:
“Extraction results match an independently inspected sample, with failures and unsupported cases documented.”
• required suites: unit, integration, negative, regression.
• current registry depends_on for Stage 03 is [“00”, “01”]. Do not alter the fixed governance dependency graph or its schema. Stage 02 is additionally an accepted runtime provider of the identifier normalizer used below; document that bounded dependency without changing accepted stages.

Fetch/read live origin/main and record the exact implementation base. Inspect any divergence from the confirmed baseline. Preserve legitimate newer work; do not overwrite, reset, or assume an older summary is current. If Stage 03 already has matching authorized work, resume it rather than duplicating or rewriting history.

Read GOVERNANCE.md and CLAUDE.md first. Start with the repository-prescribed:
uv sync –locked
uv run citerift-gov recover
uv run citerift-gov check

Use a dedicated branch/worktree. Never write directly to main. Inspect uncommitted changes and existing PRs before modifying anything.

Read, at the actual base revision:

• governance/stage_registry.json, PROJECT_STATUS.md, GOVERNANCE.md;
• DECISIONS.md, especially D-026 through D-028, and RISKS.md;
• OWNERSHIP.md, docs/identity.md, docs/data-contracts.md;
• schemas/contracts/v1/ and their valid/invalid fixtures;
• docs/verification/stage-01/PROTOCOL.md, FEASIBILITY_REPORT.md, HANDOFF.md, CREATIVE_FEASIBILITY.md, relevant evidence and extraction scripts;
• docs/verification/stage-02/HANDOFF.md, SPECIFICATION.md, TEST_RESULTS.md;
• src/citerift/retraction/identifiers.py and the query/policy/CLI interfaces relevant to downstream boundaries;
• docs/architecture.md and current packaging/CI conventions.

Old handoff wording predating owner acceptance and the stale architecture introduction do not reopen accepted stages. The live registry, accepted decisions, and code take precedence for current state.

Record this genuine owner directive using the existing governance workflow. Use the real owner-message reference available in your environment and retain the directive as evidence. If no platform message ID is exposed, use a transparent, stable document reference to the owner-delivered directive according to existing tool requirements; do not invent a cmsg ID, signature, or separately approved decision.

Record AUTHORIZED and IN_PROGRESS only through the existing lifecycle tooling, with registry/status committed together. Refine Stage 03 owned paths/gates before verification using allowed mechanisms. Do not patch governance enforcement to permit your work.

3. Scientific boundaries

These are non-negotiable:

1. Citing a retracted paper does not establish that a citing claim is false.
2. No retraction record does not establish that a work is sound or not retracted.
3. Retraction Watch redistributed through Crossref is not an independent second origin.
4. A DOI/PMID pair co-reported by Wikipedia is not independently established identity.
5. Distinguish original work, notice, source assertion, citation markup role, and later interpretation.
6. “verified_fact” means the cited artifact supports the particular scoped observation; it does not certify source truth, paper identity, or scientific validity.
7. An unresolved bridge, PMID_ROLE_COLLISION, or IDENTITY_SECONDARY_DIVERGENT must never be laundered into confirmed citation identity.
8. Preserve uncertain, unavailable, conflicting, and unsupported conditions. Do not turn them into negative findings.
9. No confidence score, probabilistic label, or semantic judgment is needed for this deterministic extractor.

Stage 02 residual restrictions remain intact, especially R-029 and R-031. Do not reopen Stage 02, add PubMed, resolve its identity cases, alter its policy, or enable its rejected model.

4. Stage 03 product outcome and scope

Build a usable, deterministic, ARTICLE-FIRST extractor:

language + article/page/revision request
    -> pinned source and separately identified render capture
    -> reference containers, citation units, all discovered use occurrences
    -> raw/normalized identifier occurrences and markup roles
    -> verifiable evidence anchors
    -> scoped marker observations, reconciliation, exception ledger
    -> explicit component states, limits, accounting, and offline replay

Support arwiki and enwiki, namespace 0, main-slot wikitext. Make unsupported languages/namespaces/content models explicit.

Include:

• capture, extract, verify, replay operations via Python and CLI;
• anonymous and named refs, reuse, groups, list-defined refs;
• supported citation templates and bounded bibliography extraction outside footnotes;
• DOI/PMID fields, supported identifier links and wrappers, invalid/missing/multiple identifiers;
• structural source/render reconciliation;
• bounded source-marker/render-text observations;
• real Arabic and English demonstrations and independent artifact inspection.

Excluded:

• global article discovery, exhaustive crawling, new dump-processing infrastructure;
• operational retraction matching or index queries;
• claim-truth, citation-reliance, intentionality, or full context analysis;
• semantic sentence extraction as a Stage 05 replacement;
• historical response-rate estimation, cross-wiki research comparisons;
• web frontend, backend API, Investigation MAESTRO;
• model inference, embeddings, rerankers, NER, model training, or inference endpoints;
• PubMed or any new identity/retraction data source;
• Wikipedia editing.

Stage 01 discovery/dump methods may inform sample selection and regression evidence. Do not silently promote that research code into production or expand Stage 03 into a paper-first discovery service.

5. Authorized design elaboration and creative freedom

The owner expects an expert implementation, not literal transcription.

You may autonomously:

• improve module boundaries, types, data structures, error codes, and CLI details;
• select the better qualified HTML parser;
• refine template/field maps from directly inspected evidence;
• refine provisional resource caps using calibration;
• add a small justified permissively licensed dependency within this scope;
• improve evidence navigation, reconciliation, accounting, and reproducibility;
• replace an overcomplicated mechanism with a simpler equivalent.

For significant choices record:
problem -> alternatives -> evidence -> decision -> resource cost -> tests -> limitations.

Do not claim that an executor-selected detail was individually approved by the owner. Record it as a delegated engineering decision under this directive. Do not change the research objective, scientific semantics, accepted contracts/code, or exclusions without new owner authorization.

Preserve the practical creative contribution: a machine-verifiable ledger linking source, rendered reference, and uses, with explicit exceptions. Compare it with a simpler baseline. Do not substitute new terminology, decorative output, or an unnecessary model for demonstrated value.

6. Calibrate and freeze the protocol BEFORE production behavior and final evaluation

This directive includes calibration and technical protocol refinement. Do not stop for a second routine approval merely to choose a parser, supported alias, or attainable measurement protocol.

Before implementing the full production pipeline:
A. Write the initial specification, failure model, evaluation design, and simulation plan.
B. Run bounded acquisition/parser/baseline experiments on DEVELOPMENT material.
C. Measure costs and inspect errors.
D. Commit a frozen protocol with support profile, data splits, metrics, sample-size rationale, numerical quality gates, and performance budgets.
E. Only then finish production implementation and expose final holdout predictions.

Do not choose arbitrary numerical precision/recall targets before baseline measurement. Equally, do not choose lenient thresholds merely because they let the current implementation pass. Justify gates from task risk, baseline, actual inspectable sample, annotation uncertainty, and feasible sample size.

Requirements for any chosen gates:

• both languages have explicit requirements and denominators;
• precision and wrong-target attachment are protected, not traded away for coverage;
• abstention, unsupported cases, and acquisition failures remain visible;
• recall/coverage requirements prevent an “abstain on everything” pass;
• no required core behavior is reclassified as unsupported to rescue a score;
• all declared exact anchors and all published receipt hashes verify;
• mandatory safety/adversarial cases meet their exact expected outcomes;
• no known unexplained material mismatch is hidden in an aggregate score.

Start calibration with about 12 articles balanced across ar/en; this is a workload starting point, not a precision claim. Choose final holdout size using observed reference counts, article clustering, error rates, and review effort. Use a bounded corpus appropriate to the cloud host and document caps before collecting it. If a high population-level accuracy claim cannot be supported, narrow the claim rather than manufacture evidence.

Owner acceptance remains after execution. Your frozen evaluation protocol is an executor-defined protocol under delegated authority, not prior owner acceptance of its outcomes.

7. Tool and dependency qualification

Research checked on 28 October 2026 suggests:

• mwparserfromhell 0.7.2: MIT; initial source parser.
• lxml 6.1.3: BSD-3-Clause with bundled-component notices; initial HTML parser.
• selectolax/Lexbor 1.0.2: MIT binding, Lexbor Apache-2.0; challenger for HTML qualification.
• Hypothesis 6.170.13: MPL-2.0; optional justified dev-only property testing.
• HTTPX 0.28.1: BSD-3-Clause; optional transport alternative to stdlib.
• wikitextparser 3.0.0: GPLv3, NOT MIT; do not introduce it or copy its code under this authorization because CITERIFT’s own license is unresolved.
• Playwright: keep out of runtime 03; full browser-visibility research is outside this scope.

Verify release/package provenance, supported Python versions, exact licenses and transitive notices, wheel availability, and applicable audit findings at execution time. Do not blindly install latest main or alpha/beta releases. Newer stable patches may be selected for a documented reason within the same task boundary.

Qualify lxml versus Lexbor on identical retained HTML:

• reference targets, fragments, reused refs, duplicate IDs;
• text/attribute handling, Arabic/Unicode, malformed markup;
• anchor validity and data loss;
• wall time, CPU, peak RSS, distribution footprint.

Treat parser disagreements as diagnostic cases for direct artifact inspection. Agreement is not independent validation. Choose ONE production HTML parser; keep the comparator in an isolated evaluation environment if needed, not an unused core dependency.

Do not import a Spark/Lua/bulk stack from wikicite or wikiciteparser for this bounded task. The inspected wikicite multilingual tree at a16ff48b483c5cca1eab7afae5a15695a97be610 includes 15 locale directories but no ar; it is methodology/prior art, not ready-made Arabic support.

Do not copy code from repositories without a clear applicable license. Existing open-source library choice is not itself a novelty claim.

Use uv.lock for actual selected dependencies. Do not alter accepted CI/governance infrastructure to install them. Normal product operation must require no paid inference, model weights, subscription, or temporary model endpoint.

Useful official references:
https://www.mediawiki.org/wiki/API:Revisions
https://www.mediawiki.org/wiki/API:Parsing_wikitext
https://www.mediawiki.org/wiki/API:REST_API/Reference/en
https://www.mediawiki.org/wiki/Help:History
https://www.mediawiki.org/wiki/Specs/HTML/2.8.0/Extensions/Cite
https://www.mediawiki.org/wiki/API:Etiquette
https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits
https://github.com/earwig/mwparserfromhell
https://github.com/lxml/lxml
https://github.com/rushter/selectolax
https://github.com/albatros13/wikicite
https://www.w3.org/TR/annotation-model/

8. Revision acquisition and receipts

Use Action API revisions for pinned source. Initially compare parse(oldid) with Core REST revision-specific HTML on bounded development cases; choose and record the production acquisition profile.

Rules:

• Resolve title/page_id to a revision in one source request that also retrieves its content when possible.
• All subsequent requests use that revision ID, never a second latest lookup.
• A supplied revision ID must be used exactly; do not combine revids with incompatible listing options.
• Validate wiki, page ID when provided, namespace, revision, content model, and slot.
• Record page_id, observed title, revision_id, parent_id where available, revision timestamp, source endpoint/parameters, response status, retrieval time, and upstream hashes.
• Preserve source Unicode and line endings exactly as returned.
• Compute local SHA-256 over the explicitly defined retained bytes; distinguish raw response body, extracted UTF-8 slot text, and extracted HTML hashes.
• If checking upstream slot SHA-1, use the documented representation/hash domain; never compare unrelated JSON and slot hashes.
• For parse, request the pinned oldid and returned revid with HTML and parse warnings. Validate returned revision identity.
• Pin parser options/configuration and record content profile/version where actually available.
• Do not assume default means legacy forever, or assume data-parsoid/DSR is always available.
• A revision mismatch forbids joining source and render; preserve valid source extraction as partial if possible.
• Redirect resolution must be explicit, bounded, recorded, and never substitute current content for a requested historical revision.
• Preserve hidden/deleted/unavailable content states distinctly.

Keep two clocks:

1. revision_timestamp: when article source was saved;
2. retrieved_at/render_observed_at: when this artifact was obtained.

Old revisions can render using changed templates, modules, configuration, and time-dependent behavior. Do not claim that an HTML capture is what readers saw at the revision timestamp.

A changed HTML hash with unchanged source proves a difference between captures. It does NOT by itself prove a template update or another specific cause.

A receipt is an integrity/provenance record, not a Wikimedia signature or independent guarantee of authenticity.

9. Data model and contracts

Define Stage-03-owned schemas under schemas/wiki/v1/ with new URNs, using existing common v1 definitions by reference.

Do NOT edit schemas/contracts/v1/ or accepted contract validators. The existing wiki_citation requires valid identifiers and cannot represent all extraction outcomes; do not force identifierless or invalid cases into fake investigation records.

Implement typed equivalents of:

• ExtractionBundle: schema/engine/config versions, capture refs, result/component states, counts, issues, extraction digest.
• RevisionReceipt.
• RenderCapture.
• ReferenceContainer: note/bibliography container, raw name/group, definitions, binding state.
• CitationUnit: a structurally supported bibliographic source within a container.
• CitationUseOccurrence: each in-article use and its source/render anchors.
• IdentifierOccurrence: scheme, raw lexeme, decoded input, normalization record, origin, markup role, evidence anchor.
• EvidenceAnchor.
• MarkerObservation.
• ReconciliationRecord and exception ledger.
• Structured issues with stable code, severity, affected entities, retryability, and evidence refs.

Preserve one-to-many/many-to-many relationships:

• one named ref can have many uses;
• one ref can contain multiple sources;
• one source can contain multiple/repeated identifiers;
• source and rendered identifier observations are not additional independent works.

A list-defined ref definition is not automatically a use in article prose.
Two identical DOIs in separate containers do not merge those containers.
The same ref name in different groups does not merge.
Conflicting definitions or unresolved unit boundaries remain explicit; do not pick the first value silently.

Use scoped assertions/provenance for observations and decisions. Raw fields, identifiers, offsets, and operational counters must have precise types. No model confidence.

Load all schemas offline; reject duplicate JSON keys and invalid/non-finite data. Enforce semantic checks beyond JSON Schema:
referential integrity, valid offsets and units, accounting, role consistency, verified anchor equality, revision compatibility, and absence-observation preconditions.

Define stable, versioned IDs and canonical serialization. Avoid self-referential hashes. Separate receipt integrity digest from deterministic extraction digest. Specify which input artifacts, configuration, rule versions, and parser profiles enter each digest. Exclude wall times, process IDs, temporary paths, and host-specific noise from deterministic extraction output.

10. Identifier extraction and Stage 02 reuse

Use a thin adapter importing the accepted pure normalizers from:
citerift.retraction.identifiers.normalize_doi
citerift.retraction.identifiers.normalize_pmid

Do not modify, move, or duplicate them. Preserve their Normalized output and distinguish structural decoding before normalization:
raw source lexeme -> explicitly documented entity/wrapper extraction -> normalizer input -> normalization result.

Do not use the query relevance skeleton as identity normalization.
Do not import query, policy, advisory, or local_model into runtime 03.
Do not open the retraction SQLite index.

Preserve all:

• raw fields, duplicate template parameters, repeated identifiers;
• valid normalized keys and transformations;
• invalid candidates and normalizer issues;
• literal percent escapes in bare DOIs;
• uncertainty in free-text identifier boundaries.

No silent punctuation trimming, Unicode compatibility normalization, bidi removal, leading-zero repair, or Arabic-digit conversion to create an identity. DOI parentheses/full stops can be legitimate. URL percent decoding must not be accidentally applied twice.

Markup roles must distinguish at least:
primary_citation_field, identifier_link, marker_target, textual_mention, unresolved.

A DOI inside a notice title or a warning template is not automatically the cited paper’s identifier. Do not infer original-versus-notice identity in 03.

Do not assert that all identifiers within one ref belong to one work. Co-reported identifiers remain co-reported.

Document the Stage 04 consumption boundary: future matching must retain extraction IDs/digests plus RDE snapshot_id/policy_version/evidence_digest and preserve unresolved identity restrictions. Do not implement that matching now.

11. Arabic/English support profile

Implement and explicitly test:

• anonymous refs;
• named refs, reuse before/after definition, self-closing uses;
• list-defined refs and separate groups;
• missing definitions and conflicting definitions;
• nested citation templates, mixed Arabic/English parameter names;
• supported Cite journal/Citation and inspected Arabic equivalents;
• bounded DOI/PMID fields in supported web/book templates without assuming every cited source is a scientific paper;
• doi/دوي and supported URL aliases, plus actual inspected PMID aliases;
• doi.org, dx.doi.org, supported PubMed URL forms without visiting those URLs;
• a narrowly documented publisher-URL allowlist where structurally justified;
• supported DOI wrappers and DOI: text inside bounded reference contexts;
• encoded separators/entities and non-ASCII text;
• multiple/repeated identifiers;
• missing templates/red links;
• identifierless references;
• comments, nowiki, examples, and title-only mentions as negative controls;
• supported bibliography entries outside footnotes, without inventing a citing sentence.

Build a versioned bilingual map from inspected sources and calibration. Keep raw names and map provenance. Do not guess an Arabic alias or call a generic stem matcher language support.

For template-generated refs, short-footnote chains, subreferences, Lua, or unsupported syntax:
preserve available source/render observations, state exactly what is unsupported, and abstain from unverifiable links. Support simple cases where justified; do not fabricate a source span for transcluded content absent from the saved article source.

Publish a matrix of fully supported, partially supported, and explicitly unsupported behaviors for each language. No blanket Arabic coverage claim.

12. Evidence anchors and the creative deliverable

Deliver a practical machine-verifiable evidence ledger, not just a list of identifiers.

For every resolved unit/container provide:

• source witness: original fragment, source artifact hash, exact location, role evidence;
• render witness: captured HTML hash, target DOM locator, observed region;
• use ledger: every discovered in-article use with target/binding state;
• reconciliation: matched/source_only/render_only/ambiguous/unavailable with reasons;
• exception ledger: unresolved/malformed/unsupported/failed observations and affected scopes.

Source anchors:

• define UTF-8 byte intervals [start,end);
• if a parser uses Unicode code-point positions, convert explicitly and test Arabic/combining characters;
• verify each claimed exact slice against original bytes;
• use lossless traversal and locally validated boundaries, not a global text.find that selects a repeated fragment incorrectly;
• never claim exactness for an inferred or ambiguous offset.

HTML anchors:

• bind to render_id and captured HTML bytes;
• prefer validated unique IDs plus structural target/backlink evidence;
• provide deterministic DOM selectors/quotes/subtree digests under a declared parser profile;
• derived DOM serialization is not raw HTML byte content;
• duplicate IDs or multiple quote matches require ambiguity handling, not a lucky first match.

A hash proves consistency with retained bytes, not correctness or independence.

Compare:
A. DOI + article/revision URL only;
B. source anchors only;
C. full source/render/use/exception ledger.

Measure successful evidence relocation, wrong-target attachment, abstention/coverage, review effort where independently measurable, and extra bytes/time/RSS. Disclose self-audit when applicable. Do not claim global novelty for revision IDs, hashes, W3C selectors, or reused-footnote tracking.

Required demonstrations:

1. source marker and missing-template rendering;
2. one reference reused at multiple locations;
3. notice title mentioning an original DOI;
4. multiple works in one ref, resolved or honestly unresolved;
5. source-only/render failure or differing render captures at the same revision.

Use real retained ar/en examples where available; synthetic cases may cover unavailable rare conditions but must be labelled. Do not fabricate a newly observed live difference or conflate old Stage 01 evidence with a new run.

13. Scoped warning observations

Keep source marker, rendered text match, missing-page link, and browser visibility separate.

Suggested states, refine names consistently:
recognized_warning_text;
no_recognized_warning_in_inspected_region;
missing_template_link_only;
ambiguous_text;
not_inspected;
unavailable.

A negative observation means only no recognized match under the stated rule/version in a fully inspected region. It is not no warning anywhere, no retraction, or a scientific claim.

Inspect a structurally linked reference/bibliographic region. Store exact matched text, term/context, rule, language, exclusions, and scope.

Do not treat:

• a missing template’s red-link label;
• a paper title beginning “RETRACTED”;
• script/style/comment text;
• an unrelated broad Arabic word stem
as a confirmed adjacent warning.

Preserve title prefixes and other excluded matches separately where useful. Ambiguous wording remains ambiguous.

Do not issue a verified negative region observation when capture, revision check, linking, parser coverage, or relevant visibility constraints failed. Capture flags such as hidden attributes without pretending that HTML analysis proves perception.

browser_visibility stays not_evaluated in runtime03. No claim about mobile, skins, gadgets, full CSS, or what every reader saw.

14. Network, cache, publication, and resource policies

Use descriptive User-Agent/contact, fixed allowed Wikipedia hosts, anonymous read-only requests, and maxlag for noninteractive batches. No arbitrary outbound publisher/identifier fetching.

Handle:

• connection/read/global deadline timeouts;
• HTTP 429/503 and Retry-After seconds or HTTP-date;
• MediaWiki maxlag/ratelimited and other errors inside HTTP 200;
• 403, 5xx, invalid JSON, wrong content type;
• missing pages, bad revisions, hidden slots;
• redirects/loops, revision mismatch;
• incomplete/oversize/compressed responses;
• cancellation, interruption, cache corruption.

Honor Retry-After without clipping it into an earlier retry. If the next allowed attempt exceeds the capture deadline, return deferred/not_before. No IP rotation, identity spoofing, or bypassing 403.

Store failed attempts as failures, separately from successful-answer cache. Source cache key is wiki+revision+slot; render captures also identify renderer/options and observation. Refresh creates a new immutable capture, not silent replacement.

Stream with wire/decompressed/retained size limits where applicable. Reject unsafe paths/symlinks, never derive filesystem paths directly from article titles, and never execute retained HTML or its scripts.

Publish bundles atomically only after required integrity checks. Failed operations preserve existing valid bundles. Cache/replay never makes a network request. An optional explicit online capture operation is the only network path.

Initial calibration ceilings, NOT measured claims:

• one in-flight Wikimedia request, about 10s minimum interval;
• up to 3 attempts per operation within a global budget;
• 4 MiB extracted source; 16 MiB extracted HTML; 32 MiB retained response-body limit;
• 64 MiB per capture bundle before dedup/retention policy;
• one article parsing worker; initial 512 MiB memory cap;
• initial 30s extraction worker wall deadline;
• initial 30s per HTTP operation timeout; 180s capture global deadline.
Refine from pilot evidence before freezing. Enforce nesting/node/occurrence and global job limits too; byte limits alone do not bound DOM memory.

Use an actually interruptible worker for untrusted expensive parsing. Clock checks only before/after a call do not interrupt a stuck call. Document platform limits; Linux cloud tests do not establish Windows support.

Measure requests/retries, source/HTML/fixture bytes, CPU/wall p50/p95/max with sample sizes, cold/warm behavior, RSS, package/import footprint, and failures. Separate network waiting from extraction computation.

No model tokens or weights. Report compute/storage/network use rather than calling operation cost-free.

15. Evaluation independence and sampling integrity

Create an annotation protocol before predictions. A NON-IMPLEMENTING inspector should examine retained raw source and HTML directly, not label extractor output or call extractor helpers as the oracle.

When agents are available, assign inspection to a separate evaluator with separate workspace/context and explicit restrictions:

• no production code edits;
• no copying production parsing/normalization logic into expected labels;
• no predictions before annotations are locked;
• record who/what inspected which artifact hashes, and what was unresolved.

Separate AI-agent inspection is procedural independence, not human gold, institutional independence, or owner review. Disclose model/agent and access history. Agreement among agents does not independently establish truth. If genuine separate inspection cannot be obtained, complete useful implementation work but do not falsely mark 03-A independently inspected.

Use three disjoint resources:

1. development/calibration corpus, including Stage 01 known examples;
2. fresh article-grouped holdout, both languages, not selected only because RDE has a hit;
3. challenge/adversarial corpus, with synthetic and observed cases separated.

All revisions of the same article belong to one split. Check duplicate/near-duplicate citation leakage where feasible. Record selection procedure, population, date, IDs, hashes, selection failures, and exclusions. Freeze manifests.

Inspect ALL reference/use/identifier targets within the annotated scope, not just extractor matches. Unsupported and failed cases remain in overall coverage reporting.

Metrics:

• container/unit precision and recall;
• use-occurrence extraction and binding precision/recall;
• identifier occurrence precision/recall, normalized-key and role errors;
• source/render linking precision, false attachment, abstention, coverage;
• per-language/per-class marker confusion matrices and not_inspected counts;
• exact-anchor verification;
• acquisition and replay success/failure.

Define matching rules and units. Report raw TP/FP/FN, zero-denominator N/A, micro and article-level results as appropriate. Account for article clustering; do not treat thousands of references in a few articles as independent trials.

Freeze final gates before exposing holdout predictions. Never tune on disclosed holdout or rewrite labels to fit the engine. Preserve any failed evaluation. After a material repair following exposure, use a predeclared fresh confirmation set; do not relabel the old set “fresh.” Avoid an unlimited model-selection-style retry loop.

Baseline Stage 01 searched for a known identifier; do not invent general-extractor recall for it. Report B0 on its valid task, a simple structural B1, and the new system on comparable scopes.

16. Required negative, adversarial, and metamorphic verification

Cover at least:

• missing ref definition, forward definition, same name/different groups;
• conflicting definitions, duplicate template keys, nested templates;
• multiple works in a ref and repeated same DOI;
• DOI only in notice title, warning template, comment, or nowiki;
• PMID role-neutral extraction, mixed identifiers, non-ASCII digits;
• DOI longer-prefix false matches, valid punctuation, percent/double encoding;
• Arabic, combining characters, bidi/control issues, non-ASCII DOI suffixes;
• bibliography-only entries and identifierless refs;
• redlinks, title prefix, ambiguous warning words;
• generated references and unsupported citation chains;
• malformed HTML, duplicate DOM IDs, missing targets/backlinks;
• HTTP 200 API errors, 429 HTTP-date, 403, 5xx, timeout;
• missing/hidden revisions, redirects, revision mismatch;
• corrupted/partial bundles, duplicate JSON keys, path traversal/symlinks;
• resource exhaustion, decompression growth, excessive depth, stuck workers;
• replay attempting sockets.

Metamorphic properties:

• adding one named-ref reuse increases uses without duplicating the source;
• independent groups stay separate;
• adding a title-only DOI mention does not create a primary citation target;
• repeated identifiers preserve occurrences without inventing extra works;
• removing HTML makes render observations unavailable, never absent;
• changing only a render capture cannot overwrite source revision identity;
• original source bytes and exact anchors roundtrip;
• same retained artifacts/config/profile yield identical deterministic extraction;
• serialization/ordering and host paths do not create semantic nondeterminism.

Simulate acquisition and failure interleavings before integrating them. Use fault injection for interrupted writes and workers. Property tests and parser comparisons complement direct inspected examples; none replaces them.

17. Review while building, then review the complete system

Maintain findings with severity, evidence, affected behavior, fix, regression, and disposition.

Conduct these review perspectives throughout and after integration:

1. architecture/contracts/scientific semantics;
2. Arabic/English extraction and product/evidence usability;
3. adversarial/security/failure handling;
4. performance/complexity/reproducibility.

Review every changed production module and public interface. Focus on cross-module bugs, failure transitions, source/render misjoins, false certainty, evidence loss, identifier roles, and excessive complexity—not only style.

For each material defect, demonstrate failure before correction where feasible and a passing regression afterward. Keep original failed outputs and explain non-reproducible findings honestly.

Do not game test counts, silence warnings indiscriminately, weaken tests, skip required cases, add expected failures, or alter governance/report generation to get green CI.

Before final verification:

• no known unresolved critical/high in-scope defect;
• no known material incorrect attachment or fabricated negative observation;
• remaining unsupported behavior and low-severity limitations fully documented;
• final data/model/CLI/schema behavior consistent with documentation.

If review finds a defect in accepted protected code, document the evidence separately. Do not reopen, patch, or bypass it under this directive. Prefer an in-scope solution if sound; a genuinely necessary protected change is a blocker needing a separate owner decision.

18. Files and ownership

Expected owned paths:

• src/citerift/wiki/
• schemas/wiki/v1/
• tests/stage03/
• simulations/stage03/ if used
• the existing Stage 03 verification directory per governance.

Possible modules: models, client/capture, source, rendered, anchors, identifiers adapter, markers, extraction, schemas, CLI. Use fewer files if clearer; avoid placeholder abstraction.

Shared permitted edits:

• pyproject.toml: justified dependencies, dev dependencies, CLI entry point only;
• uv.lock: resulting dependency lock;
• docs/architecture.md and suitable usage docs for completed Stage 03;
• DECISIONS.md, RISKS.md, CHANGELOG.md;
• Stage 03 definition/records through allowed governance mechanisms.

Do not make the whole shared pyproject/lock a permanently Stage-03-owned path that prevents later dependency additions.

Do not modify Stage 00/01/02 owned paths, their frozen evidence, accepted schemas, CI workflows, protection rules, or governance code/schema. No broad refactor or formatting churn.

Use unique test_wiki_* names and committed deterministic fixtures. Separate synthetic/observed data and include attribution/license/source/revision information.

19. Python API, CLI, packaging, and reproducibility

Provide coherent APIs equivalent to:
capture_revision(request, fetch_policy);
extract_bundle(capture, config);
verify_bundle(bundle);
replay_bundle(bundle, pinned_config).

Provide a usable citerift-wiki CLI:

• capture –wiki ar|en with title/page-id/revision options;
• extract –bundle … –out …;
• verify –bundle …;
• replay –bundle ….

Use structured JSON stdout and diagnostics stderr; document stable exit semantics for complete/partial/unsupported/unavailable/invalid/verification failure. Do not use exit 0 plus an empty array to mask a failed operation.

Validate all CLI combinations and public API errors. Public callers must not need to know SQLite internals or development paths.

Test clean clone use and installed-wheel behavior for Stage 03 schema resources and references to accepted common schemas. Use a documented supported schema-root mechanism if necessary; do not modify accepted Stage 00/02 packaging to fix unrelated limitations. A local editable install is not proof of wheel correctness.

CI tests run without live network and without model weights. Real network evaluation is a separately retained evidence run. Keep all bytes required for declared offline demonstrations; hashes without files do not establish replayability.

Deduplicate large source artifacts by hash. Keep a bounded attributed observed fixture set in Git and retain the rest in a durable downloadable evidence export if appropriate. Do not create broken links to ephemeral /tmp or another agent’s private /mnt paths. Verify export availability and checksums before claiming handoff completeness.

20. Acceptance gates to implement and report

Preserve 03-A, refining it with explicit measurable subgates before production completion:

• Source/revision receipts and integrity: no mismatched revision join; all published hashes/anchors validate.
• Core bilingual extraction: required supported constructs work and every discovered candidate has a disposition.
• Identifier semantics: normalization reuse, no title/marker promotion, no fabricated cross-ID identity.
• Source/render/use ledger: reuse and multi-source accounting, explicit unresolved links, five demonstrations.
• Scoped marker observations: source/render/missing-template/unknown separated; no failure-to-absence path.
• Independent evaluation: frozen protocol, fresh splits, raw predictions/annotations, per-language metrics meet pilot-informed preregistered gates.
• Resource/failure containment: enforced limits and observed costs meet the frozen scope/budgets.
• Reproducibility/packaging: no-network replay and clean environments reproduce the declared content.
• Reviews/regressions: findings dispositioned with meaningful evidence; no protected drift.
• Engineering verification: complete required test suites, static checks, both Python versions, actual successful GitHub CI at cited revision.
• Delivery: full documents, durable evidence, usable CLI demonstrations, and unmerged PR.

Do not silently reduce subgates after seeing holdout or change a core requirement into an optional feature. Scope improvements are permitted; scope erosion to manufacture success is not.

21. Final verification sequence and evidence

Run targeted checks continuously. Once the implementation/reviews are complete, freeze edits and verify from clean committed revisions.

Run the whole repository suite, not just Stage 03, on Python 3.12 and 3.13 with the normal repository report plugin. Preserve exact interpreter/environment versions, command lines, timestamps, exit codes, collection/pass/fail/skip counts, and clean-tree evidence.

Also run the existing required checks, including:
uv run pytest
uv run ruff check .
uv run ruff format –check .
uv run mypy
uv run citerift-gov check

Use actual current CLI help for check-report and transition flags; do not invent commands. Audit changed dependencies with the project’s established method, including relevant dev/evaluation environments.

Obtain real successful GitHub Actions for the exact code revision cited, including Python matrix and ci-gate. “Pushed” is not “CI succeeded.” Inspect statuses and meaningful failure logs.

Do not rerun expensive accepted snapshot builds merely because Stage 03 planning mentioned them. The full regression test suite is required; reopening previous acceptance is not.

Use the existing revision/evidence-recording procedure. Avoid circular “this commit contains its own SHA” evidence and fabricated report revisions. Code or required evidence changes after verification invalidate the corresponding claim; re-verify through the normal lifecycle.

Only mark IMPLEMENTED_NOT_VERIFIED and then VERIFIED_AWAITING_OWNER_ACCEPTANCE when their actual conditions hold. Never mark ACCEPTED_CLOSED.

22. Required deliverables

Under docs/verification/stage-03/, provide the repository-required:
SPECIFICATION.md
MATHEMATICAL_MODEL.md
RISK_ANALYSIS.md
SIMULATION_REPORT.md
TEST_RESULTS.md
CREATIVE_DIFFERENTIATION_REVIEW.md
HANDOFF.md
test-report.json

Also provide compact inspectable evidence for:

• owner-delivered authorization reference and actual base/head revisions;
• tool qualification, exact package versions/licenses, and decisions;
• frozen evaluation protocol and support matrix;
• sample/split/annotation manifests and reviewer provenance;
• raw predictions, metric calculations, confusion/error tables;
• synthetic and observed fixtures, receipts, artifacts, hashes;
• five source/render/use-ledger demonstrations with actual CLI commands/output;
• resource results and failure injections;
• review findings/fail-first regressions/dispositions;
• full-suite reports for both Python versions and exact CI URLs;
• manifest and durable export instructions.

HANDOFF must contain all current registry-required section titles, including:
Stage and status; Verified completed work; Inputs and outputs; Test evidence;
Known limitations; Open blockers; Dependency versions; Verified Git commit;
Acceptance decision; Requirements for the next stage.

Write technical repository material in clear English consistent with the project. Give the owner the final explanatory report in Arabic.

23. PR and attribution

Open/update one clearly titled Stage 03 PR against main after implementation. A draft while work continues is fine. Leave it UNMERGED. The owner merges personally.

PR description must lead with concrete product behavior, then scope, design choices, real verification, unsupported cases, resource costs, and limits. Link actual evidence and CI. No success claims based only on a test count.

Keep environment-provided git identity/signing. Never impersonate the owner.

Follow CLAUDE.md attribution exactly:
commit trailer:
Assisted-by: Claude Code (AI coding agent)

PR final attribution line:
AI-assisted: prepared with Claude Code (AI coding agent) under the direction of EVE TELOS · IM.

Preserve any environment-required top attribution block. Do not add conflicting Co-Authored-By or invented human approvals. Use EVE TELOS · IM as the prominent public creator identity.

24. Completion, blockers, and stopping point

Continue through the whole authorized stage. Do not stop after scaffolding, a specification, a small demo, initial green unit tests, or a list of suggested next steps.

Ordinary parser issues, broken in-scope tests, dependency qualification, supported aliases, and review findings are your work to resolve autonomously.

A real blocker is something you cannot resolve within the authorization: unavailable indispensable external access/evidence, an essential protected-stage change, no genuine required independent inspection, irreconcilable governance conflict, or another evidenced constraint. Do all independent useful work first, preserve evidence, and report the exact minimum owner action. Do not bypass restrictions or falsely declare completion.

The final Arabic report must start with what NOW works and why it matters:

• actual Arabic and English article/revision -> extracted reference/use -> source/render evidence examples;
• what the engine catches that the simpler baseline misses;
• measured costs and evaluation results;
• unsupported/uncertain cases and reviewer-independence limits;
• exact code/evidence revisions, CI links, PR URL;
• an explicit statement that the PR is unmerged and acceptance is the owner’s.

Do not state that Stage 03 matches retractions end to end; that is Stage 04. Do not announce the full product finished.

If all gates are met, stop at VERIFIED_AWAITING_OWNER_ACCEPTANCE, leave the PR unmerged, and end with:
VERIFIED — AWAITING OWNER ACCEPTANCE

Otherwise use the honest repository-required status:
BLOCKED — EVIDENCE PROVIDED
or:
NOT VERIFIED

Do not accept the stage, merge, begin Stage 04, or take another project action after the handoff until the owner decides.

BEGIN THE AUTHORIZED STAGE 03 WORK NOW.
