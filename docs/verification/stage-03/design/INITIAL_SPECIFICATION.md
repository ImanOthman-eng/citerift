# Stage 03 initial specification (pre-calibration)

Status: **initial**, written on 2026-10-28 before any calibration request, under
the owner's Stage 03 Execution Directive
(`cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`, retained in
`../authorization/`). It is step A of directive section 6. It is kept unchanged
after calibration as the record of what was decided before measurement; the
calibrated and frozen version is `../SPECIFICATION.md` with
`../protocol/FROZEN_PROTOCOL.md`.

Before writing this file the executor sent three exploratory requests to check
the response shapes only (one Action API revision query and one Action API
parse for enwiki revision 1372543632, one Core REST revision HTML for the same
revision; the REST call received two HTTP 429 answers first). They are not
calibration data and are not used as evidence.

## 1. Product

An article-first, deterministic extractor. Input: a language edition (`ar` or
`en`), and exactly one of a title, a page id or a revision id. Output:

1. a **capture bundle**: the pinned source revision (raw API response and the
   extracted main-slot text), a separately identified render capture of the
   same revision, receipts with hashes, and every failed attempt;
2. an **extraction bundle**: reference containers, citation units, every use
   occurrence found in the saved source, identifier occurrences with raw
   lexeme, decoding steps, Stage 02 normalization record and markup role,
   exact source anchors (UTF-8 byte intervals), render anchors (DOM locators
   under a declared parser profile), scoped marker observations, a
   source/render reconciliation, an exception ledger, explicit component
   states, accounting and a deterministic extraction digest.

Operations: `capture` (the only network path), `extract`, `verify`,
`replay`, as Python functions and as the `citerift-wiki` command.

Supported: `arwiki` and `enwiki`, namespace 0, main slot, content model
`wikitext`. Anything else is reported as unsupported, never silently skipped.

## 2. Out of scope

Exactly the exclusions of the directive (section 4): no discovery or
crawling, no retraction matching or index access, no claim, reliance or
context analysis, no API or frontend, no model of any kind, no PubMed or other
identity source, no Wikipedia editing.

## 3. Initial design choices (to be qualified in calibration)

| Concern | Initial choice | Challenger / question for calibration |
|---|---|---|
| Source acquisition | Action API `query&prop=revisions|info`, `rvslots=main`, `formatversion=2`, content in the same request as the title/page/revision resolution | none |
| Render acquisition | undecided | Action API `parse&oldid=` (legacy parser HTML) vs Core REST `/v1/revision/{id}/html` (Parsoid HTML with versioned profile, revision headers and `data-mw`) |
| Source parser | mwparserfromhell 0.7.2 (MIT) | lossless traversal and offset validation to be tested; deep-nesting behavior to be measured |
| HTML parser | lxml 6.1.3 | selectolax 1.0.2 (Lexbor), in an isolated environment only |
| Transport | standard library `urllib` with own streaming limits | HTTPX not needed unless calibration shows a gap |
| Property testing | seeded standard-library generators (as Stage 02) | Hypothesis not added (latest release is from the day of the directive; no demonstrated need) |
| Isolation | extraction in a child process with CPU, address-space and wall limits | measure RSS and address space of a real parse first |

## 4. Entities (typed, versioned; full field list in the frozen specification)

- `RevisionReceipt`: wiki, request, page id, observed title, namespace,
  revision id, parent id, revision timestamp, content model, slot, endpoint
  and parameters, HTTP status, retrieval time, hashes of the raw response
  body, the extracted UTF-8 slot text and the upstream slot SHA-1 (domain:
  SHA-1 of the UTF-8 slot text, to be confirmed in calibration).
- `RenderCapture`: render id, renderer and profile, request, status, headers
  that identify the revision, observation time, hash of the retained HTML
  bytes, revision check result.
- `ReferenceContainer`: kind (`note`, `list_defined_note`, `bibliography_entry`),
  raw name and group, definitions, binding state.
- `CitationUnit`: one supported citation template, or the unstructured text
  of a container, inside a container; boundary state.
- `CitationUseOccurrence`: every use in the saved source, with its binding to
  a container and its render anchor if reconciled.
- `IdentifierOccurrence`: scheme, raw lexeme, decoding steps, normalizer input,
  normalization record (Stage 02 `Normalized`), origin, markup role, anchor.
- `EvidenceAnchor`: `source_bytes` (artifact hash and `[start, end)` byte
  interval, exactness) or `dom` (render id, artifact hash, parser profile,
  element id, path, text quote, subtree digest, uniqueness).
- `MarkerObservation`: source marker or render text observation, with rule
  version, scope, matched text, exclusions and state.
- `ReconciliationRecord`: `matched`, `source_only`, `render_only`, `ambiguous`,
  `unavailable`, with reasons.
- `Issue`: stable code, severity, affected entities, retryable flag, evidence.

Roles for identifier occurrences: `primary_citation_field`, `identifier_link`,
`marker_target`, `textual_mention`, `unresolved` (extensions only if
calibration shows a structurally distinct case).

## 5. Failure model (initial)

| Class | Examples | Required behavior |
|---|---|---|
| Acquisition | timeout, 429/503 with Retry-After, maxlag or ratelimited in HTTP 200, 403, 5xx, invalid JSON, wrong content type, oversize or compressed growth | bounded retries within a global deadline; `deferred` with `not_before` when Retry-After passes the deadline; failures recorded apart from answers; never a negative finding |
| Identity | missing page, bad revision, hidden text, redirect, wrong namespace or model, revision mismatch between source and render | explicit unsupported/unavailable states; no source/render join on mismatch; source kept when valid |
| Parsing | malformed wikitext, unparsed deep nesting, template-generated references, malformed HTML, duplicate DOM ids | explicit issues; abstain from links that cannot be verified |
| Resource | huge or deep input, stuck parser | child process killed at the wall or memory limit; extraction `failed` with the limit named |
| Storage | interrupted write, corrupted or partial bundle, duplicate JSON keys, symlinks, path traversal | atomic publish; verify rejects; existing bundles untouched |
| Semantic | DOI only in a notice title or marker, co-reported DOI and PMID, same name in two groups, conflicting definitions | roles and states keep them apart; nothing merged or promoted |

## 6. Evaluation design (initial)

- Three disjoint resources: development (calibration, including Stage 01
  known examples), a fresh article-grouped holdout drawn by a recorded
  procedure from a population that does not depend on retraction data, and a
  challenge corpus (observed and synthetic parts kept apart).
- A separate non-implementing evaluator agent annotates the holdout from the
  raw source and HTML before any holdout prediction is shown to anyone;
  annotations are locked by hash first.
- Units of measurement: container, unit, use, identifier occurrence, render
  link, marker observation; matched by exact source byte interval (or by
  rule stated in the protocol). Raw TP/FP/FN, per language, micro and
  per-article, with clustering accounted for.
- Gates are not chosen here. They are chosen after the development
  measurements and frozen before the holdout predictions exist.

## 7. Simulation plan (initial)

Before the acquisition client is integrated: a deterministic discrete-event
simulation of the fetch policy (attempts, Retry-After in seconds and as an
HTTP date, maxlag bodies, global deadline, deferred results) over scripted
fault sequences, checking that no schedule retries earlier than allowed,
exceeds the attempt or deadline budget, or turns a failure into an answer.
Fault injection for interrupted bundle writes and killed workers.

## 8. Caps for collecting the development corpus

At most 16 articles (8 per language), at most 3 render captures per
revision, at most one in-flight request, at least 10 s between requests,
Retry-After honored, 4 MiB source text, 16 MiB HTML, 32 MiB response body
per request. Total development download expected below 100 MiB.
