# Investigation MAESTRO — Design Brief (future requirements, not implemented)

Stage 01 deliverable. It records the orchestration vision of the owner's
Stage 01 directive (message `cmsg_018VCB51nDHP6HXmLU4ea5yPHoNtmrTEksWGzn64yEgVJc`,
2026-10-26) as testable requirements for later stages. **Nothing in this file exists as code.** The
Investigation MAESTRO is the owner's name for the **Investigation Workflow
Controller** of Architecture v1.1 (Stages 04 and 07); it is not a new
component and adds no stage. Requirements are numbered `MR-nn` so later
specifications can trace them. Facts from Stage 01 that shaped a requirement
are cited to FEASIBILITY_REPORT.md (FR §n).

## 1. Responsibilities and boundaries

The MAESTRO runs one investigation: given a subject, it plans a bounded set of
tasks, runs them through deterministic states, checks their evidence, and
emits one investigation record that follows `schemas/contracts/v1`.

It is **not**:

| Not this | Why it stays separate |
|---|---|
| Project Orchestrator (`src/citerift/governance`) | Governs how CITERIFT is built; development tooling (docs/architecture.md). |
| Persistent Project Memory (registry, DECISIONS.md, RISKS.md) | Engineering record, not investigation evidence. |
| GitHub governance (rulesets, CI) | Repository control. |
| An autonomous agent | No open-ended planning, no self-chosen web access, no Wikipedia writes. |

- **MR-01** Application code under `src/citerift/investigation/` never imports
  `citerift.governance`, and governance code never imports it (existing rule,
  docs/architecture.md).
- **MR-02** The MAESTRO only issues read requests (`GET`) to an allowlist:
  Wikimedia Action API `action=query` / `action=parse` on configured editions,
  Crossref REST `/works`, and the pinned Retraction Watch snapshot. It has no
  credential that could edit Wikipedia.
- **MR-03** The task plan for an investigation is a fixed function of the
  request and configuration. No model chooses which tasks run or which
  sources are queried.

## 2. Inputs and outputs

- **MR-04 Request:** `subject` (a DOI, or a PMID, or a Wikipedia article as
  `wiki` + `title`, optionally `revid`), `languages` (a configured subset,
  at most `L_max`, initially `en` and `ar`), `as_of` (latest revision, or a
  pinned revision/time), `history` (off, or a bounded revision budget), and a
  request budget (§7).
- **MR-05 Output:** one investigation record valid against
  `urn:citerift:schema:contracts:v1:investigation`, with `status` in
  `completed | partial | failed`, every factual value wrapped in the
  assertion type, and `limitations` listing each skipped or failed task.
  Fields that v1 cannot hold (for example several retraction events per
  paper, FR §4.3) are added in a Stage-04-owned schema that `$ref`s v1 by URN,
  not by editing v1.
- **MR-06** Each Wikipedia citation in the output names `language`, `title`,
  `revision_id` and the revision `sha1`, and its provenance names the
  discovery method (M1 external links, M2 search, or wikitext parse).

## 3. Tasks and workers

| Task | Worker (owning stage) | Depends on |
|---|---|---|
| T1 Resolve subject identifiers | Retraction data engine (02) | — |
| T2 Retraction events for the paper | Retraction data engine (02) | T1 |
| T3 Discover citing articles per language | Wikipedia extraction (03) | T1 |
| T4 Pin revision and confirm the citation in its wikitext | Wikipedia extraction (03) | T3 |
| T5 Match citations to events | Detection (04) | T2, T4 |
| T6 Citation context and existing retraction notices | Context (05) | T4 |
| T7 AI usage assessment (advisory) | AI investigation (06) | T6 |
| T8 Cross-language comparison | Cross-wiki (07) | T4 for ≥2 languages |
| T9 Retraction response timeline | Cross-wiki (07) | T2, T4 with history |
| T10 Assemble Evidence Passport | Detection (04), extended in 05/07 | all required tasks |

- **MR-07** Required tasks are T1–T5 and T10; T6–T9 are optional and their
  failure yields `partial`, never `failed`.
- **MR-08** Workers are pure functions of their inputs plus the responses
  they fetched; every fetched response is stored with URL, status and
  retrieval time (§5), so a task can be re-run from memory without network.

## 4. States and transitions

Investigation: `created → planned → running → completed | partial | failed`,
plus `cancelled` from `planned` or `running` (an application state, recorded
as `failed` with a cancellation limitation in the v1 contract).

Task: `pending → running → succeeded | failed_retryable | failed_permanent |
timed_out | skipped | cancelled`; `failed_retryable → running` while the retry
budget lasts; `skipped` when a required input task did not succeed.

- **MR-09** The transition tables are data, checked by tests for
  completeness (every state reachable, every terminal state final), in the
  style of `citerift-gov transitions`.
- **MR-10** Final status rule: `completed` iff every required and requested
  optional task succeeded; `failed` iff T2 or every T3 failed; otherwise
  `partial`. A failed or skipped task never produces a negative finding:
  "no citation found" is reported only when T3 and T4 succeeded, and then as
  "not found by methods M… in revisions …", never as "not cited".

## 5. Evidence checkpoints

- **CP-1 Retraction source:** every event names the dataset snapshot (commit
  or version, file hash) and record id; a Crossref-only event names the
  Crossref DOI and retrieval time. Retraction Watch and Crossref
  `updated-by` with `source: retraction-watch` are one source, not two
  (FR §4.2).
- **CP-2 Event type:** `Retraction`, `Correction`, `Expression of concern`
  and `Reinstatement` map to contract values one-to-one; a paper with several
  events keeps all of them in date order (FR §4.3).
- **CP-3 Original vs notice DOI:** a citation matches only the original
  paper DOI; a record whose notice DOI equals its original DOI is flagged
  (FR §4.3).
- **CP-4 Revision pin:** a citation counts only after its DOI is found in
  the wikitext of the pinned revision (Stage 01 confirmation step, FR §5).
- **CP-5 Cross-language:** compared only between pinned revisions; an
  absent citation in one language is a difference observed in those two
  revisions, not a statement about the language edition.
- **CP-6 Absence:** a paper with no record yields
  `not_found_in_checked_sources` / `uncertain` with the sources checked.

## 6. Investigation Memory

- **MR-11** Append-only: tasks add records (request, response metadata,
  derived facts); nothing is overwritten. A re-run creates a new
  investigation that may reuse cached responses by key
  `(source, normalized request)`.
- **MR-12** Resumable: after a crash, an investigation restarts from its last
  recorded task states and produces the same record as an uninterrupted run
  given the same cached responses.
- **MR-13** Investigation Memory is separate from Persistent Project Memory
  and is not stored in the repository.

## 7. Errors, retries, timeouts, cancellation

Stage 01 observed HTTP 429 on Wikipedia requests from this environment, with
`Retry-After` values from 1 to 51 s, after runs of 1 to 6 successful requests;
whether Wikimedia or the environment's egress proxy applied the limit was not
determined (FR §8.2).

- **MR-14** One shared rate limiter for all Wikimedia editions; honor
  `Retry-After`; bounded attempts (≤ 6) and exponential backoff; per-request
  timeout; descriptive User-Agent.
- **MR-15** A per-investigation request budget and wall-clock budget; when
  exhausted, remaining tasks end `timed_out` and the investigation is
  `partial`, with each limitation stated.
- **MR-16** Cancellation stops new requests, lets in-flight requests finish or
  time out, and records the cancellation; the memory stays consistent.
- **MR-17** Errors are enumerable codes (`RATE_LIMITED`, `SOURCE_UNAVAILABLE`,
  `REVISION_MISSING`, `DOI_NOT_IN_REVISION`, ...), following the `Finding`
  convention of docs/architecture.md; no silent fallback.

## 8. AI advisory boundary

- **MR-18** AI (Stage 06) may only label how a pinned citation is used in its
  context, from a fixed label set that includes `abstain`. Output is
  `model_inference` with a model reference and confidence; it never sets
  `retraction_status`, a date, a citation's presence, or a cross-language
  difference.
- **MR-19** AI failure, timeout or schema-invalid output becomes an abstention;
  the investigation still completes.
- **MR-20** No AI output states that a citing claim is false because the cited
  paper is retracted.

## 9. Human review checkpoints

- **HR-1** AI labels are shown as advisory, with "needs human review" until a
  `human_review` entry exists (contract field).
- **HR-2** Timeline statements about why an edit happened are never
  generated; only observed revisions with ids are shown (FR §7.4).
- **HR-3** `conflicting` and `uncertain` values are shown as such, with their
  sources.

## 10. Non-functional requirements

- **MR-21 Determinism:** same request + same cached responses → byte-identical
  record (except the record's own creation time).
- **MR-22 Bounded cost:** with a warm cache, a single-DOI, two-language
  investigation without history makes no network request. Cold-run latency
  is dominated by the rate limits observed from this environment (FR §8.2),
  so the demo must use
  precomputed, cached investigations, labelled with their retrieval time.
- **MR-23 Traceability:** every value in the Evidence Passport links to a
  stored response (URL, retrieval time, revision id or dataset hash).
- **MR-24 Privacy:** no personal data about users is stored; Wikipedia editor
  names are not needed and not stored.

## 11. Stage ownership

| Stage | Owns |
|---|---|
| 04 | MR-01–MR-17, MR-21, MR-23 for one language: state machine, T1–T5, T10, Investigation Memory v0, budgets, error codes. |
| 05 | T6 and the context part of the Evidence Passport. |
| 06 | T7 and MR-18–MR-20 (empirical evaluation of the AI role). |
| 07 | Multi-language plans, T8, T9, resumption and cancellation through the API, MR-22, HR-2. |
| 08 | Presentation of task states, uncertainty, AI advisory status (HR-1, HR-3), timeline and Evidence Passport. |

## 12. Proposed acceptance tests

| Id | Test | Stage |
|---|---|---|
| AT-01 | Replaying an investigation from cached responses reproduces the same record (MR-21). | 04 |
| AT-02 | The Stage 01 positive case (EVIDENCE_MANIFEST.json) is found end-to-end at its pinned revision. | 04 |
| AT-03 | NC-01 (correction or concern) is never reported as a retraction; NC-02 revisions yield no citation; NC-03 yields `not_found_in_checked_sources` / `uncertain`; NC-04 notice citations are not counted as citations of the paper. | 04 |
| AT-04 | Injected 429, 503 and timeouts produce `partial` with limitations and no negative finding (MR-10, MR-15). | 04 |
| AT-05 | Crash at each task boundary, then resume: identical record (MR-12). | 04 |
| AT-06 | Cancellation mid-run leaves memory consistent and the record `failed` with a cancellation limitation (MR-16). | 07 |
| AT-07 | Static check: no import of `citerift.governance` from application code (MR-01). | 04 |
| AT-08 | Network allowlist test: only read endpoints are called (MR-02). | 04 |
| AT-09 | AI stub returning garbage, timing out or raising yields abstention and a completed investigation (MR-19). | 06 |
| AT-10 | Cross-language comparison of a Stage 01 case lists both pinned revisions and states differences only between them (CP-5). | 07 |
| AT-11 | The UI never shows an AI label without its advisory marker and never shows `uncertain` as negative (HR-1, HR-3). | 08 |

## 13. Realism for the schedule

The MAESTRO is a state machine over at most ten task types, run in one
process with a local store; no queue, scheduler service or agent framework is
needed. Given the 2026-11-21 deadline (R-010), Stage 04 should build only the
single-language core; T8 and T9 belong to Stage 07 and may be reduced to the
cases Stage 01 shows to be feasible.
