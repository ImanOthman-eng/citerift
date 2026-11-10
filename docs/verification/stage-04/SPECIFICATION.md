# Stage 04 Specification: Detection Engine and Vertical Slice

Status: Step 3 of the retained plan (`planning/STAGE04_MASTER_EXECUTION_PACKAGE.md`, section 14), written before any
Stage 04 code. Owner authorization for this step: `cmsg_018VCB51nDHP6HXmLU4ea5yPTg4B2mbvArm7ZsYe8DG6Ag`
(2026-11-10). Authoritative inputs: the retained plan, DECISIONS.md D-039 and D-040, registry gates 04-A to 04-J, and
the accepted Stage 00 to 03 baseline. Companion documents: `MATHEMATICAL_MODEL.md` (formal model, referred to as MM)
and `RISK_ANALYSIS.md` (risks, referred to as RA). The adversarial review of these three documents is in
`review/step3/STEP3_ADVERSARIAL_REVIEW.md`.

Words: **must** is a requirement that a test or check will verify; **never** is a requirement whose violation is a
defect. A requirement id (`S-…`) is cited by tests later. Statements about the accepted engines are verified against
their code and schemas at `a152885` and name the file; everything else is the Stage 04 design.

## 1. Purpose and boundary

Stage 04 answers one question for one pinned Wikipedia article revision: **which of its citations name a work for
which the pinned Retraction Watch snapshot records a retraction, an expression of concern, a correction or a
reinstatement, and with what certainty and provenance**. It composes the accepted Stage 03 extraction engine and the
accepted Stage 02 retraction data engine, records every step in an append-only Investigation Memory, and runs the
steps through a small deterministic Investigation Workflow Controller.

- S-1.1 A detection never says that a citing claim is false, and never says that a work is "not retracted". Absence
  of a record is reported only as `not_found_in_checked_sources` with status `uncertain` (v1 contract rule).
- S-1.2 Stage 04 is a deterministic rule engine. It has no learned component, no score and no numeric threshold in
  any decision (MM section 11 gives the reason).
- S-1.3 Stage 04 is not an autonomous agent. Its plan is a fixed function of the request (MR-03); no component
  chooses which sources to query or which steps to run.
- S-1.4 Stage 04 never edits Wikipedia and never writes to Stage 02 or Stage 03 data.

### 1.1 Scope

1. Detection Engine: candidates, lookups, the decision table (section 7), claims with provenance.
2. Investigation Memory v0: journal, content-addressed blobs, fold, replay (section 8).
3. Investigation Workflow Controller v0: fixed plan, step and lifecycle state machines, retries, deferral, resume
   (section 9).
4. Article-revision investigations in `en` and `ar`, one revision at a time, from a retained Stage 03 bundle or a new
   read-only capture through Stage 03.
5. A Stage 04 report and v1 projections (section 11), CLI `citerift-investigate` (section 13).
6. The vertical slice (section 14), the scientific evaluation under the pre-registered protocol (gate 04-I), the
   stage documents and a measured creative contribution (gate 04-J).

### 1.2 Non-scope

Citation context and interpretation of existing on-page warnings (Stage 05; Stage 04 only records Stage 03 marker
observations); AI (Stage 06); cross-language comparison, timelines, revision history, an API, explicit cancellation,
edition snapshots, DOI- or PMID-subject discovery of citing articles (Stage 07); user interface (Stage 08); fuzzy or
title-based matching; live Crossref queries; any change to Stages 00 to 03. Stage 04 does not depend on any behavior
of Stages 05 to 07: the only forward-looking element is the extensible subject type (section 4.1), which Stage 04
defines and later stages may extend.

### 1.3 Ownership

Owned paths (registry, D-1): `src/citerift/investigation`, `schemas/investigation`, `tests/stage04`,
`simulations/stage04`. Verification directory: `docs/verification/stage-04`. Stage 04 reads but never modifies Stage
02 and Stage 03 owned paths or `schemas/contracts/v1`.

## 2. Terms

| Term | Meaning |
|---|---|
| Revision | One immutable revision of one Wikipedia article: `(wiki, page_id, revision_id)`. |
| Snapshot | One Stage 03 capture bundle of a revision, identified by its `capture_sha256`. Two captures of one revision can differ in their render. |
| Root | The investigation subject: one revision plus the snapshot it was read from (section 4.1). |
| Unit | A Stage 03 extraction unit (`units[]`): one citation template, external-data template, unsupported citation template or unstructured text citation inside a container. |
| Identifier occurrence | A Stage 03 identifier record (`identifiers[]`): scheme, role, boundary, source anchor and the Stage 02 normalization record. |
| Key | A valid normalized identifier: `(scheme, normalized)` with `scheme ∈ {doi, pmid}`. |
| Work candidate | The set of keys of one unit that Stage 04 treats as naming one work (section 6.3). |
| Lookup | One Stage 02 query (`Index.gather`) and its rendered result. |
| Observation | Raw data recorded from an engine: bundle identity, extraction document, lookup result. |
| Evidence | A normalized fact pointing into an observation (JSON pointer). |
| Claim | A Stage 04 conclusion about one work candidate: a claim class (section 7.2), an epistemic status, its evidence. |
| Decision | The disposition of one claim (section 7.6). |
| Question | An open item that needs resolution outside Stage 04 (section 7.7). |
| Journal | The append-only record list of one investigation (section 8). |
| Fold | The function that computes the current investigation state from the journal (MM section 7). |

## 3. Interfaces with the accepted engines

Stage 04 calls only the public functions below and never imports private names of Stage 02 or Stage 03. The adapters
live in `src/citerift/investigation/adapters/`.

### 3.1 Stage 03 (`citerift.wiki`)

| Function | Use | Facts relied on (verified at `a152885`) |
|---|---|---|
| `capture_revision(CaptureRequest(wiki, revision_id=…), policy, out=…)` | ACQUIRE of a new snapshot (the only network path) | `CaptureRequest` takes exactly one of title, page id, revision id; status `complete`, `partial` (render failed), `failed` or `deferred` with `not_before` (`capture.py`); retries and Retry-After are handled inside `fetch.py` |
| `open_bundle` / `verify_bundle(bundle, extraction)` | ACQUIRE of a retained snapshot; VERIFY | bundle content addressing and issue codes `BUNDLE_*` (`issues.py`) |
| `extract_bundle(bundle, isolated=True)` | EXTRACT | offline, isolated worker with wall and memory limits; failure document with a stable code (`EXTRACTION_DEADLINE_EXCEEDED`, `EXTRACTION_MEMORY_EXCEEDED`, `EXTRACTION_WORKER_FAILED`); document `status ∈ {complete, partial, failed}` (`schemas/wiki/v1/extraction.schema.json`) |
| `replay_bundle(bundle, pinned_config, recorded)` | replay check (section 10) | re-derives the extraction offline and compares |

Extraction document fields used: `capture` (`capture_sha256`, `wiki`, `page_id`, `revision_id`, `sha1`, `title`),
`extractor` (version, profile digest, normalizer), `config_digest`, `status`, `containers` (`kind`,
`binding_state`, `use_ids`, `unit_ids`), `uses` (`binding`), `units` (`id`, `container_id`, `kind`, `source`,
`identifier_ids`), `identifiers` (`id`, `scheme`, `role`, `origin`, `boundary`, `unit_id`, `container_id`, `source`,
`decoding`, `normalization`), `markers`, `exceptions`, `issues`, `extraction_digest`.

Stage 03 handoff requirements that bind Stage 04 (HANDOFF.md, "Requirements for the next stage"), and where they are
met: `unstructured_text` is read only as Stage 03 defines it (S-6.2); an abstained render link is unknown, not absent
(Stage 04 does not use render links for detection, S-6.1); `IDENTIFIER_BOUNDARY_AMBIGUOUS` and role `unresolved` are
unconfirmed (S-6.4, S-6.2); a missing identifier or a `not_inspected` marker is never "not retracted" (S-1.1, S-7.5);
Arabic warning detection is untested (markers are recorded, not interpreted); co-reported identifiers are never
merged (S-6.3); replay, not verify alone, where decoding must be trusted (EXTRACT always re-derives, S-9.3).

### 3.2 Stage 02 (`citerift.retraction.query`)

| Function | Use | Facts relied on (verified at `a152885`, `query.py`, `policy.py`) |
|---|---|---|
| `Index(path: Path)` | open once per LOOKUP attempt | read-only, immutable; raises `IndexUnavailable` with a code; must be given a `Path` (a `str` raises `AttributeError`, plan G-08) |
| `Index.gather(doi, pmid)` | every query | returns all events, unpaged; `state ∈ {matched, notice_only, ambiguous_identity, no_record, invalid_query}` (`unavailable` only from `lookup()`/`unavailable_result`) |
| `render(evidence, snapshot_id, page_size=MAX_PAGE)` | the recorded result | projection (`retraction_status` v1 assertion with `basis`), `issues`, `identity`, `evidence_digest` |
| `projection_of(evidence)` | the value used by detection | `retraction_status.status ∈ {verified_fact, uncertain, conflicting, unavailable}`; values `retracted`, `expression_of_concern`, `correction`, `reinstated`, `not_found_in_checked_sources` or null |

Facts of the pair query used by section 6.5 (`Index.gather`, branch `d and p`): the pair is **incompatible** when an
event whose `original_doi` is the DOI carries an `original_pmid` other than the PMID or null, or an event whose
`original_pmid` is the PMID carries an `original_doi` other than the DOI or null; Stage 02 then returns
`ambiguous_identity`. A single PMID whose events carry more than one DOI is also `ambiguous_identity`. A compatible
pair may add PMID events linked by `query_pair`, which the projection policy treats as bridged and never counts as
support (`policy.reduce`, rule 7f).

- S-3.1 The Stage 02 adapter records, for every query, the full `Evidence` events (event id, `row_sha256`,
  `matched_by`, `linked_via`, `original_doi`, `original_pmid`, `event_type`, `flags`), the rendered result, the
  projection and the `evidence_digest`. Paging is never relied on.
- S-3.2 Index identity is recorded once per LOOKUP attempt: `snapshot_id`, `policy_version`, lookup-result schema
  version, and the SHA-256 of the index file.

## 4. Root and child identities (owner decision D-4)

### 4.1 Root

- S-4.1 The root of every investigation is one immutable subject snapshot:
  `subject = {type, identity, display}` with, in Stage 04, `type = "wikipedia_article_revision"` and
  `identity = {wiki, page_id, revision_id, capture_sha256}`; `display = {title, revision_sha1}`.
- S-4.2 `root_id = H("citerift-investigation-root/1", type, identity)` where `H` is SHA-256 over canonical JSON
  (MM section 2). The title is never part of the identity.
- S-4.3 A request names a revision by `wiki` and `revision_id`, or gives a retained bundle. A request that names only
  a title or only a page id is refused (`INPUT_INVALID`, reason `REVISION_NOT_PINNED`). Title-to-revision resolution
  is done with Stage 03 (`citerift-wiki capture`) before an investigation is created.
- S-4.4 The root is bound exactly once, by the successful ACQUIRE commit (section 9.2). After binding it never
  changes; every later content record carries `root_id`. A resume or replay that would bind a different root is
  `STALE` (section 10.3). Before the bind, records carry `root_id = null` and are attributable to the request key:
  `investigation_created` holds `request_key`, the investigation directory and the journal genesis derive from
  `investigation_key` (S-4.7, S-8.1, 8.2), and no evidence, claim, decision or question record of any step may precede
  the bind (M-9). A capture made by a later ACQUIRE attempt of the same investigation (after a failed or interrupted
  attempt that committed nothing) binds the root once; a different capture after the bind is never bound in place
  (owner decision F-15, DECISIONS.md D-041).
- S-4.5 `type` is an open, versioned enumeration. Stage 04 readers accept only `wikipedia_article_revision` and
  refuse any other type with `SUBJECT_TYPE_UNSUPPORTED` instead of guessing. A later stage may add a type; the meaning
  of Stage 04 records does not change.
- S-4.6 The page identity is verified: the bundle's `page_id`, `revision_id` and `wiki` must equal the extraction
  document's `capture` fields and, for a new capture, the requested `revision_id`. A mismatch is a terminal ACQUIRE or
  EXTRACT failure (`ROOT_IDENTITY_MISMATCH`).

### 4.2 Investigation key

- S-4.7 `investigation_key = H("citerift-investigation/1", request_key, plan_version, config_digest)`, where
  `request_key` is `{wiki, revision_id}` for a capture request or `{capture_sha256}` for a bundle request.
  `config_digest` is the SHA-256 of the canonical effective configuration
  (`urn:citerift:schema:investigation:v1:common#/$defs/config`): plan version, the budgets `A_max` and `F_max`, the
  Stage 03 fetch policy digest and the live-ACQUIRE bound (`deadline_s`, `op_timeout_s`, the 30 s allowance and
  `T_acq`), both null for a bundle request (owner decision D-042). A change of any of them is a different
  investigation key and a different step key (S-9.3); a historical investigation is never recomputed under another
  bound.
- S-4.8 The investigation directory is named by the hexadecimal `investigation_key`. The v1 `investigation_id` is a
  UUID derived deterministically from it (MM section 2.3). Running the same request twice addresses the same
  investigation (idempotency, section 9.6).

### 4.3 Children

| Child | Identity | Parent |
|---|---|---|
| Unit | `unit_ref = H(root_id, "unit", unit.id, unit.source.byte_start, unit.source.byte_end, unit_span_sha256)` | root |
| Identifier occurrence | `ident_ref = H(root_id, "identifier", identifier.id, source byte span, source raw_sha256)` | unit, or root when `unit_id` is null |
| Work candidate | `cand_ref = H(unit_ref, sorted keys)` | unit |
| Observation | SHA-256 of its canonical content (the blob digest) | root |
| Evidence | `evidence_id = H(observation digest, JSON pointer)` | observation |
| Claim | `claim_id = H(cand_ref, class, rule id, table version, sorted evidence ids)` | work candidate |
| Decision | `decision_id = H(claim_id, disposition)` | claim |
| Question | `question_id = H(claim_id, "question", kind)` | claim |

Unit anchor (owner decision D-043, review finding SR-03 of Step 5). Stage 03 is authoritative for a unit's source span
(`cp_start`, `cp_end`, `byte_start`, `byte_end`) and emits no hash for it. Stage 04 derives
`unit_span_sha256 = SHA-256(source_artifact_bytes[byte_start:byte_end])` over the half-open byte interval of the exact
retained Stage 03 source artifact (the extraction's `capture.source_artifact`), never over normalized or reformatted
text. Before deriving it, Stage 04 verifies the source artifact's digest, that `0 ≤ byte_start ≤ byte_end ≤
len(source)`, that the span lies on code-point boundaries matching `cp_start` and `cp_end`, and that the extraction
belongs to the bound root (its `capture.capture_sha256` equals the root's). Where a Stage 03 identifier anchor covers
exactly the same byte span, its `raw_sha256` must equal the derived hash. Any mismatch fails closed and never creates a
new identity. VERIFY recomputes the hash from the retained bytes. Unit evidence records the hash with the source
artifact digest.

- S-4.9 Stage 03 element ids (`un-00013`) are stable for a given extraction digest; the source anchors make every
  child identity independent of them across engines, so a re-extraction that renumbers units changes child ids only
  through the anchors, never silently.

## 5. Inputs and outputs (semantic contracts)

### 5.1 Request

`{subject: {wiki, revision_id} | {bundle: path}, index: path, memory_root: path, config}` where `config` holds
the Stage 03 fetch policy reference and no detection parameter (there is none to set). Validation (VALIDATE step):
`wiki ∈ {en, ar}`; `revision_id` a positive integer; bundle path a directory that `open_bundle` accepts; index path an
existing regular file; memory root an existing directory outside the repository working tree (MR-13). Each failure
has a code: `INPUT_INVALID` with reasons `WIKI_UNSUPPORTED`, `REVISION_NOT_PINNED`, `BUNDLE_UNREADABLE`,
`INDEX_PATH_INVALID`, `MEMORY_ROOT_UNSAFE`.

The request schema is `urn:citerift:schema:investigation:v1:request` (Step 5). It has two forms, discriminated by
`mode`: `live_capture` (`subject = {type, wiki, revision_id}`, with the fetch policy digest and the live-ACQUIRE bound
in `config`) and `retained_bundle` (`subject = {type, bundle_path}`, with both null). A title or page id is not a
field of either form, so a request that names only a title or only a page id does not validate (S-4.3). The request
and its `request_key` are the input identity fixed at creation; the root is bound later by ACQUIRE (S-4.4).

### 5.2 Outputs

1. The journal and blobs (section 8): the authoritative record.
2. The Stage 04 report (section 11): a deterministic function of the fold.
3. v1 projections: one v1 investigation record per distinct work with a positive claim (section 11.2).
4. The CLI exit status and a short text summary derived from the report.

## 6. Candidates

### 6.1 Units considered

- S-6.1 Detection reads the **source** side of the extraction only: units, identifiers and their source anchors.
  Render reconciliation states are recorded as observations and never decide a claim. A render that is missing,
  abstained or unmatched therefore never removes or adds a candidate.
- S-6.2 Every unit of every container is considered, whatever its `kind` (`citation_template`,
  `external_data_template`, `unsupported_citation_template`, `unstructured_text`). Identifiers inside an unsupported
  template carry role `unresolved` in Stage 03 and are never candidate keys (S-6.4).

### 6.2 Use eligibility

Each unit gets a use eligibility `U(u)` from its container `c` (the first row that holds):

| # | Condition (Stage 03 fields, `schemas/wiki/v1/extraction.schema.json`) | `U(u)` | Reason |
|---|---|---|---|
| 1 | `c.binding_state = conflicting_definitions` | `USE_NOT_ESTABLISHED` | `CONFLICTING_DEFINITIONS` (which body is shown is not established) |
| 2 | `c.kind = bibliography_entry` | `CITED` | shown as a list item or standalone citation |
| 3 | some use of `c` has `binding ∈ {bound, anonymous}` | `CITED` | shown where it is used |
| 4 | `c.kind = list_defined_note` | `UNUSED` | defined in a reference list and never used (Stage 03 issue `LIST_DEFINED_UNUSED`) |
| 5 | otherwise | `USE_NOT_ESTABLISHED` | `NO_BOUND_USE` (a note with no bound use; not expected from Stage 03, never treated as unused) |

A unit whose `container_id` does not name a container of the document is a NORMALIZE failure (`NORMALIZE_INVALID`).

- S-6.3 `UNUSED` and `USE_NOT_ESTABLISHED` units are looked up and recorded like any other, but their claim class is
  decided by rules D-1 and D-2 (section 7.3): no finding is reported for them.

### 6.3 Identifier status and work candidates

Candidate roles: `primary_citation_field` and `identifier_link`. All other roles (`labeled_reference_text`,
`marker_target`, `textual_mention`, `unresolved`) are observation roles.

Each candidate-role identifier occurrence of a unit gets a status:

| Status | Condition |
|---|---|
| `CONFIRMED` | normalization present and `valid`, boundary `field`, `delimited` or `url`, no `DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS` step, and the identifier is not named by an extraction exception or an `IDENTIFIER_*` issue other than `CO_REPORTED_IDENTIFIERS` |
| `UNCONFIRMED` | normalization `valid` but any of the other conditions fails (boundary `ambiguous_trailing_punctuation` or `ambiguous_markup_or_entity`, the ambiguous DOI path step, or a named exception or issue) |
| `MALFORMED` | normalization null (structural decoding failed) or `valid: false` |

- S-6.4 Keys are taken from `CONFIRMED` and `UNCONFIRMED` occurrences. `MALFORMED` occurrences have no key.
- S-6.5 Work candidates of a unit `u` with distinct DOI keys `D` and distinct PMID keys `P`:
  - `|D| ≤ 1` and `|P| ≤ 1`, not both empty: one candidate with those keys (shape `DOI`, `PMID` or `PAIR`);
  - otherwise (more than one key of a scheme): one single-key candidate per key, each flagged
    `CO_REPORTED_MULTIPLE`; keys of different schemes are not paired, and the pair check is recorded as
    `PAIRING_NOT_DETERMINED` (co-reported identifiers are never merged);
  - no key: one candidate of shape `NONE`.
- S-6.6 A candidate is **tainted** (`τ`) when its unit has any `UNCONFIRMED` key (reason `IDENTIFIER_UNCONFIRMED`),
  any `MALFORMED` candidate-role occurrence (reason `IDENTIFIER_MALFORMED`), or any identifier occurrence with role
  `unresolved` (reason `IDENTIFIER_ROLE_UNRESOLVED`: Stage 03 could not decide whether it is a would-be candidate, and
  its handoff requires such identifiers to be treated as unconfirmed). Taint is a property of the unit and applies to
  every candidate of that unit.
- S-6.7 Observation-role identifiers with a valid key are looked up too and recorded as observations
  (`MARKER_TARGET_OBSERVED`, `MENTION_OBSERVED`, `LABELED_TEXT_OBSERVED`, `UNRESOLVED_ROLE_OBSERVED`), linked to their
  unit when they have one. They never decide a claim. Identifiers outside every unit (`unit_id` null) are recorded
  the same way, linked to the root.

### 6.4 Lookups

- S-6.8 Q1: every distinct key is queried alone, once per investigation (`gather(doi=k)` or `gather(pmid=k)`).
- S-6.9 Q2: every `PAIR` candidate `(d, p)` is also queried as a pair (`gather(doi=d, pmid=p)`).
- S-6.10 A query that raises (database error) records a lookup observation with state `unavailable` and the error
  code; the LOOKUP step still commits (section 9.2). An index that cannot be opened fails the step with Stage 02's
  code (`INDEX_MISSING`, `INDEX_CORRUPT` or `INDEX_FORMAT_MISMATCH`).
- S-6.11 The **deciding lookup** `L(c)` of a candidate is Q2 for `PAIR` and Q1 of its key otherwise.

### 6.5 Cross-identifier coherence (gate 04-D, owner requirement)

Both identifiers of a `PAIR` candidate `(d, p)` are resolved independently (Q1(d), Q1(p)) and the work identities are
compared by Stage 04 itself, using only **direct** events (`linked_via` null) of the lookups of the candidate that are
available (state other than `unavailable`):

- A **witness of incompatibility** is a direct event with `matched_by = doi`, `original_doi = d` and
  `original_pmid ∉ {p, null}`, or a direct event with `matched_by = pmid`, `original_pmid = p` and
  `original_doi ∉ {d, null}`: a checked source states that one identifier belongs to a work that carries a different
  identifier of the other scheme.
- `κ = INCOMPATIBLE` if a witness exists in any available lookup of the candidate (Q1(d), Q1(p) or Q2);
- otherwise `κ = NOT_DETERMINED` if Q1(d) or Q1(p) is `unavailable` (the relation cannot be decided);
- otherwise `κ = COHERENT` if some direct event of Q1(d) or Q1(p) has `original_doi = d` and `original_pmid = p`;
- otherwise `κ = UNDETERMINED` (the checked sources say nothing about whether the two name the same work).

`κ` is defined only for `PAIR` candidates; for the other shapes it is `n/a`.

- S-6.12 Agreement: when Q1(d), Q1(p) and Q2 are all available, `κ = INCOMPATIBLE` if and only if Q2 is
  `ambiguous_identity`. A disagreement is a terminal DETECT failure `ADAPTER_INCONSISTENT`, never a silent choice (MM
  proposition P2 proves the two definitions equal on Stage 02's data model, so a disagreement means a defect). The
  same failure covers every other inconsistency between the lookups of one candidate that Stage 02 cannot produce
  (rule D-5, MM F-8 and F-9): a non-deciding lookup outside the contract, an ambiguous DOI-only query, a witness or a
  co-naming event in a lookup whose state cannot hold one, an ambiguous Q1(PMID) without a witness, and a Q2 state
  other than the one implied by the two single-key states (Step 4 correction SC-2).
- S-6.13 Stage 02 and Stage 03 are not changed to hide an identity conflict. If evidence shows that an upstream
  correction is genuinely required, it is reported to the owner as a decision; Stage 04 does not work around it.

## 7. Detection

### 7.1 Principle and precedence

Detection is the function `δ` of MM section 5: for each work candidate, the first rule of the decision table whose
guard holds decides the claim class. The tiers, in order, are:

1. investigation preconditions (O-1 to O-3): stale input, failed extraction, unusable index (no claims at all);
2. eligibility (D-1 to D-4): the reference is not shown, its shown body is not established, or it has no key;
3. adapter consistency (D-5): a defect check, fail-closed;
4. **contradiction** (D-6 identity conflict, D-7 contradiction in the sources);
5. **unresolved evidence** (D-8 to D-12);
6. **operational failure** (D-13 lookup unavailable);
7. **positive finding** (D-14);
8. observation that the cited identifier is a notice (D-15);
9. **no finding** (D-16 not found in the checked sources);
10. fail-closed gap (D-17).

Tiers 4 to 9 follow the owner's default ordering of 2026-11-10: identity contradiction > unresolved evidence >
operational failure > positive finding > no finding. Tiers 1 to 3 come first because they decide whether a candidate
is a citation of a shown reference at all, or whether the inputs can be trusted; none of them can produce a finding.
No rule can produce a positive finding when an earlier rule's guard holds, and adding evidence that satisfies an
earlier guard can only move a candidate to an earlier tier (monotonicity, MM proposition P4).

This order differs from the retained plan's draft table (plan 8.3, rules P-0 to P-10), where unavailability (P-0) and
an unresolved identifier (P-1) came before the identity conflict (P-2). The owner's instruction of 2026-11-10 sets the
order used here; the mapping of every plan rule is in `review/step3/STEP3_ADVERSARIAL_REVIEW.md`, finding F-01.

### 7.2 Claim classes

| Class | Kind of result | Epistemic status (v1) | Value |
|---|---|---|---|
| `RETRACTED_WORK_CITED` | positive finding | `verified_fact` (scope: checked sources) | `retracted` |
| `CONCERN_CITED` | positive finding | `verified_fact` | `expression_of_concern` |
| `CORRECTION_CITED` | positive finding | `verified_fact` | `correction` |
| `REINSTATED_WORK_CITED` | positive finding | `verified_fact` | `reinstated` |
| `NOT_FOUND_IN_CHECKED_SOURCES` | missing evidence | `uncertain` | `not_found_in_checked_sources` |
| `NOTICE_CITED` | observation: the cited identifier is a notice | `uncertain` | null |
| `IDENTITY_CONFLICT` | contradiction: the citation's identifiers name incompatible works | `conflicting` | null, both alternatives |
| `UNRESOLVED_IDENTITY` | abstention: one key names several works, the supporting PMID may name the notice, or the only support is bridged | `uncertain` | null |
| `UNRESOLVED_IDENTIFIER` | abstention: an identifier of the unit is unconfirmed, malformed or of unresolved role | `uncertain` | null |
| `CONTRADICTION_IN_SOURCES` | contradiction in the checked sources | `conflicting` | null, alternatives from Stage 02 |
| `UNRESOLVED_STATUS` | abstention: a record exists but its current effect is not established, or relevant rows are quarantined | `uncertain` | null |
| `LOOKUP_UNAVAILABLE` | operational failure for this candidate | `unavailable` | null |
| `UNUSED_DEFINITION` | out of detection scope: not shown in the revision | none (observation) | — |
| `UNRESOLVED_USE` | out of detection scope: which definition is shown is not established | none (observation) | — |
| `NO_IDENTIFIER` | out of detection scope: no DOI or PMID in a candidate role | none (observation) | — |

The six semantic kinds the owner named stay distinct (S-7.5): **missing evidence** = `NOT_FOUND_IN_CHECKED_SOURCES`;
**negative evidence** = a source stating that the work is not retracted, which no accepted source provides, so Stage 04
has no class for it and the report schema forbids such a value; **conflicting evidence** = `IDENTITY_CONFLICT`,
`CONTRADICTION_IN_SOURCES`; **failed lookup** = `LOOKUP_UNAVAILABLE` (and step failures, which produce no claims);
**stale evidence** = the lifecycle state `STALE` (section 10.3), never a claim; **unresolved evidence** =
`UNRESOLVED_IDENTITY`, `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`.

### 7.3 Decision table (version `dt-1`)

Inputs per work candidate `c` of unit `u` (MM section 4): use eligibility `U`; shape `σ ∈ {NONE, DOI, PMID, PAIR}`;
taint `τ` and its reasons; the lookups of `c` (`Λ(c)`: Q1 of each key, and Q2 for `PAIR`); coherence `κ`; the deciding
lookup `L = L(c)` with its state, projection status and value, basis reasons and issues. Investigation-level
preconditions (rows O-1 to O-3) are checked before any candidate is decided.

| Rule | Tier | Guard (first that holds) | Class | Notes |
|---|---|---|---|---|
| O-1 | 1 | an input identity changed since it was recorded (section 10.3) | — (lifecycle `STALE`) | DETECT does not run; no claim |
| O-2 | 1 | the extraction status is `failed`, or EXTRACT did not commit | — (lifecycle `FAILED`) | no claim, no negative |
| O-3 | 1 | the index cannot be opened, or LOOKUP did not commit | — (lifecycle `FAILED`) | no claim, no negative |
| D-1 | 2 | `U = UNUSED` | `UNUSED_DEFINITION` | lookups kept as observations; reason `LIST_DEFINED_UNUSED` |
| D-2 | 2 | `U = USE_NOT_ESTABLISHED` | `UNRESOLVED_USE` | lookups kept; reason from section 6.2 (`CONFLICTING_DEFINITIONS` or `NO_BOUND_USE`) |
| D-3 | 2 | `σ = NONE` and `τ` false | `NO_IDENTIFIER` | |
| D-4 | 2 | `σ = NONE` and `τ` true | `UNRESOLVED_IDENTIFIER` | reasons `IDENTIFIER_MALFORMED` and/or `IDENTIFIER_ROLE_UNRESOLVED` |
| D-5 | 3 | the lookups of `c` break a Stage 02 contract visible to Stage 04 (S-6.12): some lookup in `Λ(c)` has state `invalid_query`; a lookup other than `L` has a state or projection outside F-1 to F-4, F-8 (MM 4.5); Q1(DOI) is `ambiguous_identity`; or, for `σ = PAIR`, a witness or co-naming event without matching lookup states, (`κ = INCOMPATIBLE`) ≠ (Q2 state `ambiguous_identity`), Q1(PMID) `ambiguous_identity` without a witness, or (all three available) a Q2 state other than the one F-9 implies | — (DETECT `failed_terminal`, `ADAPTER_INCONSISTENT`) | impossible for valid keys (P2, F-9); fail-closed; corrected in Step 4 (`review/step4/STEP4_SPEC_CORRECTIONS.md`, SC-2) |
| D-6 | 4 | `σ = PAIR` and `κ = INCOMPATIBLE` | `IDENTITY_CONFLICT` | section 7.5, S-7.3; reason `IDENTITY_WITNESSED`, plus `LOOKUP_PARTIAL` when a lookup of `c` is unavailable and taint reasons when `τ` |
| D-7 | 4 | some lookup in `Λ(c)` has state `matched` and projection status `conflicting` with value null | `CONTRADICTION_IN_SOURCES` | alternatives from the first such lookup in the order L, Q1(DOI), Q1(PMID); reason `RETRACTION_EVENT_TYPE_CONFLICT` |
| D-8 | 5 | `τ` | `UNRESOLVED_IDENTIFIER` | taint reasons (S-6.6) |
| D-9 | 5 | `L.state = ambiguous_identity` and projection `uncertain` with value null | `UNRESOLVED_IDENTITY` | reason `KEY_NAMES_SEVERAL_WORKS` |
| D-10 | 5 | `L.state = matched`, its projection within F-2 and F-4, and (`L` has a `PMID_ROLE_COLLISION` issue naming an event with `matched_by = pmid`, or the projection's basis reasons include `BRIDGE_ONLY_SUPPORT`) | `UNRESOLVED_IDENTITY` | reason `PMID_ROLE_COLLISION` or `BRIDGE_ONLY_SUPPORT` |
| D-11 | 5 | `L.state = matched` and projection status `uncertain` with value null | `UNRESOLVED_STATUS` | reason `CURRENT_EFFECT_NOT_ESTABLISHED`; Stage 02 basis reasons kept as upstream reasons with their evidence |
| D-12 | 5 | `L.state = no_record` and projection `uncertain` with value null | `UNRESOLVED_STATUS` | reason `COVERAGE_GAP_RELEVANT_ROWS` |
| D-13 | 6 | some lookup in `Λ(c)` has state `unavailable` | `LOOKUP_UNAVAILABLE` | reason `LOOKUP_QUERY_FAILED`; the code of the failed query stays in its lookup observation |
| D-14 | 7 | `L.state = matched` and projection status `verified_fact` with value `v ∈ {retracted, expression_of_concern, correction, reinstated}` | positive class of `v` (table 7.2) | reasons `KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED`, `CO_REPORTED_MULTIPLE` attached when they apply |
| D-15 | 8 | `L.state = notice_only` and projection `uncertain` with value null | `NOTICE_CITED` | reason `CITED_IDENTIFIER_IS_NOTICE`; never an attachment to the retracted work |
| D-16 | 9 | `L.state = no_record` and projection `uncertain` with value `not_found_in_checked_sources` | `NOT_FOUND_IN_CHECKED_SOURCES` | reason `NOT_FOUND_IN_CHECKED_SOURCES`; provenance = checked sources |
| D-17 | 10 | otherwise | — (DETECT `failed_terminal`, `DECISION_TABLE_GAP`) | unreachable on Stage 02's model (MM proposition P1); fail-closed; reached by a deciding lookup outside the Stage 02 contract |

Reason names for D-1, D-2, D-7, D-11, D-13 and D-16 were fixed in Step 5 and finalized by owner decision D-043; they
replace the Step 4 model's placeholders and change no class, guard or precedence
(`review/step5/STEP5_PLACEHOLDER_MAPPING.md`).

Reason codes attached by D-14 (and kept on any class when they apply): `KEY_RESULTS_DIFFER` when the lookups of the keys
of a `PAIR` candidate have different states (for example `matched` and `no_record`); `PAIR_UNCORROBORATED` when
`κ = UNDETERMINED`; `CO_REPORTED_MULTIPLE` from S-6.5. These reasons never change the class; they are reported and
evaluated (gate 04-I).

Every guard that reads a projection names the exact contract form (status and value) it accepts; a projection outside
the forms of MM 4.5 (F-2 to F-4, F-8) never satisfies such a guard and therefore reaches D-5 (a lookup other than `L`)
or D-17 (the deciding lookup `L`), never a finding (Step 4 correction SC-1).

A rule that ends DETECT (`D-5`, `D-17`) stops the whole step: no claim of the investigation is committed, because a
defect in one candidate means the table or an adapter cannot be trusted for any (S-9.3).

### 7.4 Input combinations named by the owner

| Input class | Rule(s) |
|---|---|
| DOI only | D-7 to D-16 with `σ = DOI` (D-9 cannot fire: a DOI-only Stage 02 query never returns `ambiguous_identity`) |
| PMID only | D-7 to D-16 with `σ = PMID`; D-9 when the PMID's records carry more than one DOI; D-10 for a PMID role collision |
| DOI + PMID coherent | `κ ∈ {COHERENT, UNDETERMINED}`: D-7 to D-16 on `L = Q2`; `PAIR_UNCORROBORATED` when `UNDETERMINED` |
| DOI + PMID incompatible | D-6 `IDENTITY_CONFLICT` |
| DOI + PMID, a lookup unavailable | D-6 when a witness exists in the available lookups; otherwise `κ = NOT_DETERMINED` and D-13 (or an earlier tier) |
| identifier absent | D-3 |
| identifier malformed | D-4 (no key), D-8 (beside a key) |
| lookup unavailable | O-3 (index), D-13 (query) |
| lookup ambiguous | D-6 (pair), D-9 (single key) |
| retracted work | D-14 → `RETRACTED_WORK_CITED` |
| retraction notice | D-15 → `NOTICE_CITED`; a notice DOI paired with the original's PMID is a witness of incompatibility → D-6 |
| expression of concern / flagged record | D-14 → `CONCERN_CITED`, `CORRECTION_CITED`, `REINSTATED_WORK_CITED`; D-11 when the effect is mixed or unlinked; flags are carried as reasons. `REINSTATED_WORK_CITED` is unreachable through S-6.8 and S-6.9: Stage 02 states the value `reinstated` only with supersession links, which have no source in Stage 02 data and which Stage 04 never passes (`policy.py`, Step 4 finding S4-04); the rule stays for a later versioned source |
| marker target | S-6.7: observation only, never a candidate |
| multiple candidate records | several events of one work: Stage 02 reduces them (D-7, D-11, D-14); several works for one key: D-9; several keys in one unit: S-6.5 |
| conflicting source evidence | D-7 |
| stale source/index | O-1 |
| extraction failure | O-2 (document `failed`); a `partial` document continues with outcome `partial` (section 9.8) |

### 7.5 Absence, abstention and contradiction

- S-7.1 **Abstention** is a claim whose status is `uncertain` or `unavailable` (`UNRESOLVED_IDENTITY`,
  `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`, `LOOKUP_UNAVAILABLE`, and `NOTICE_CITED` for the work). An abstention
  states what is missing; it is reported with its reasons and is never counted as a finding or as a negative.
- S-7.2 **Contradiction** is a claim whose status is `conflicting` (`IDENTITY_CONFLICT`, `CONTRADICTION_IN_SOURCES`). It holds
  at least two alternatives, each with evidence (v1 rule), and opens a question (section 7.7).
- S-7.3 **Identity conflict** (gate 04-D). For a `PAIR` candidate with `κ = INCOMPATIBLE`: no positive or negative
  detection is emitted for the candidate; the claim's alternatives are the work identity reached by the DOI and the
  work identity reached by the PMID, each with its Q1 lookup, its events and provenance (when one Q1 is unavailable,
  that alternative is supported by the witness event's identifier field and the claim carries `LOOKUP_PARTIAL`); Q2
  is attached as corroborating evidence; Investigation Memory keeps all
  three lookups, both identifier occurrences with their Stage 03 anchors and normalization records, and the coherence
  computation; the controller opens a `needs_resolution` question; replay must reproduce the same claim id.
- S-7.4 Regression cases for 04-D: the real, already exposed design case arwiki revision 76190003, unit `un-00013`
  (DOI `10.1038/nature12969`, whose record has PMID `24476891`, with PMID `24476881`), expected `IDENTITY_CONFLICT`;
  synthetic variants on the attributed Retraction Watch subset fixture: the same pair in the other parameter order,
  a PMID of the work's retraction notice, a PMID of an unrelated retracted record, a DOI and PMID of one record
  (expected `COHERENT`, not a conflict), and DOI-only and PMID-only controls of each. The real case is design and
  regression data only; it is never prospective evaluation evidence (D-5).
- S-7.5 **No negative.** No class, report field or v1 projection holds a value meaning "not retracted". A failed
  step, an unavailable lookup, a stale input, an unused definition or an absent identifier never produces
  `NOT_FOUND_IN_CHECKED_SOURCES`; that class requires a committed `no_record` lookup of a confirmed key of a cited unit.

### 7.6 Decisions (dispositions)

Each claim gets exactly one decision:

| Claim class | Disposition |
|---|---|
| positive classes | `REPORT_FINDING` |
| `NOT_FOUND_IN_CHECKED_SOURCES` | `REPORT_NOT_FOUND` |
| `IDENTITY_CONFLICT`, `CONTRADICTION_IN_SOURCES` | `ROUTE_NEEDS_RESOLUTION` |
| `UNRESOLVED_IDENTITY`, `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`, `NOTICE_CITED` | `ABSTAIN` |
| `LOOKUP_UNAVAILABLE` | `ABSTAIN_UNAVAILABLE` |
| `UNUSED_DEFINITION`, `UNRESOLVED_USE`, `NO_IDENTIFIER` | `OUT_OF_SCOPE` |

### 7.7 Questions

- S-7.6 Every `ROUTE_NEEDS_RESOLUTION` decision opens one question (`question_opened`, kind `identity_conflict` or
  `source_conflict`). Stage 04 has no action that closes a question; closing requires new evidence through a later
  mechanism and is recorded as `question_closed` with that evidence (defined for the journal format; Stage 04 never
  writes it).

### 7.8 Article summary

- S-7.7 The article summary counts claims by class and lists the distinct works with positive claims. It never
  derives a statement about the article from absent claims (no "clean", "no retracted citations", or similar). When
  every candidate is `NOT_FOUND_IN_CHECKED_SOURCES`, the summary says that no record was found in the checked sources
  for the listed identifiers, with the snapshot id.

## 8. Investigation Memory

### 8.1 Store

- S-8.1 One directory per investigation under the memory root, named by `investigation_key` (hex):
  `journal.jsonl`, `blobs/<sha256>`, `lock`. No path component comes from request text (titles never appear in
  paths). The memory root is outside the repository (MR-13); retained evidence for the stage is a verified copy.
- S-8.2 Blobs are canonical JSON (MM section 2) addressed by their SHA-256. A blob is written to a temporary file in
  the same directory, flushed and `fsync`ed, renamed into place, and the directory is `fsync`ed. Writing a blob that
  exists is a no-op after its content hash is checked.
- S-8.3 The journal is a sequence of records, one canonical JSON object per line, appended and `fsync`ed one record
  at a time. No record is ever rewritten or removed in place.

### 8.2 Record

`{v, seq, prev, kind, step, attempt, at, root_id, payload, digest}`:

| Field | Rule |
|---|---|
| `v` | journal format version, `1` |
| `seq` | 0, 1, 2, … without gaps |
| `prev` | `digest` of record `seq − 1`; for `seq = 0` the constant `H("citerift-journal-genesis/1", investigation_key)` |
| `kind` | one of section 8.3 |
| `step`, `attempt` | the step and attempt number for execution and content records; null otherwise |
| `at` | UTC timestamp; excluded from every content digest |
| `root_id` | null before the root is bound; the `step_succeeded` record of ACQUIRE carries the root it binds, and every later record the bound root; every other ACQUIRE record (including a failed or killed attempt) and every VALIDATE record carries null |
| `payload` | kind-specific; references blobs by digest |
| `digest` | SHA-256 of the canonical record without `digest` |

### 8.3 Record kinds and layers

| Layer | Kinds | Payload |
|---|---|---|
| Lifecycle | `investigation_created` | request, `request_key`, plan version, config digest, engine identities |
| Execution | `step_started`, `step_succeeded`, `step_failed`, `step_deferred`, `step_interrupted`, `stale_detected` | step key; for `step_succeeded` the output digests (and for ACQUIRE the bound root); for `step_failed` `{code, retryable, reason, detail, wall_clock}` and, for ACQUIRE, `not_before` (the Retry-After instant the attempt observed, or null; `wall_clock` is non-null only for `ACQUIRE_WALL_CLOCK_EXCEEDED`, owner decision D-042); for `step_deferred` `{code, not_before}`; for `stale_detected` `{changed, recorded, current}` (section 10.3) |
| Observation | `observation_recorded` | `{obs_kind ∈ {bundle, extraction, index_identity, lookup}, blob, source_ref}` |
| Evidence | `evidence_recorded` | `{evidence_id, observation, pointer, kind, refs}` (keys, identifier statuses, coherence results) |
| Claim | `claim_recorded` | `{claim_id, cand_ref, class, status, value, alternatives, rule, reasons, supporting, contradicting}` |
| Decision | `decision_recorded` | `{decision_id, claim_id, disposition}` |
| Question | `question_opened`, `question_closed` | `{question_id, claim_id, kind}`; close adds `{evidence}` |
| Report | `report_recorded` | `{report blob, v1 projection blobs}` |
| History | `claim_superseded` | `{old_claim_id, new_claim_id, reason, new_evidence}` |
| Verification | `verification_recorded` | `{result, checks}` |

The exact payload of each kind is fixed by `urn:citerift:schema:investigation:v1:journal-record` (Step 5). The schema
spells out what this table states in words: `investigation_created` adds `investigation_id` and `migrated_from`
(S-8.7); evidence adds the typed `value` read at its pointer; a claim adds its `candidate`, `table_version` and
`upstream_reasons` (Stage 02 basis reasons with their evidence); `verification_recorded` adds the content digest
`C(J)` (section 11.1). Invariants the schema cannot express (M-1 to M-8, M-10, M-11, M-13, M-14, the transition rules
and the derivation of every id) are checked by Investigation Memory and VERIFY
(`review/step5/STEP5_SCHEMA_REVIEW.md`).

Content records (observation, evidence, claim, decision, question, report, verification) are written only between
`step_started` and `step_succeeded` of their step and attempt. They are **committed** if and only if that attempt has a
`step_succeeded` record; uncommitted content is ignored by the fold (MM section 7).

### 8.4 Separation of layers

- S-8.4 References point only downward: evidence → observation; claim → evidence; decision → claim; question →
  claim; report → claims and decisions. A record never refers to a record of a later `seq`.
- S-8.5 Observations hold engine output byte-for-byte as canonical JSON; evidence never copies a value without its
  pointer into an observation.

### 8.5 Supersession

- S-8.6 A claim is never edited or deleted. `claim_superseded` links an old claim to a new one; it requires at least
  one evidence id in the new claim that the old claim did not have, and a reason code. The current view excludes
  superseded claims; the history view keeps them and the link. In Stage 04 no step writes `claim_superseded`
  (committed steps never re-run); the kind is defined so that later stages can, and the fold and its invariants are
  tested on synthetic journals.

### 8.6 Validity

A journal is **valid** when every invariant of section 8.7 holds. On open (owner decision D-044): a final line without
the terminating newline is an incomplete physical record, a **torn tail** (section 10.1); it is the only defect
treated as an interrupted append. A newline-terminated line is a complete physical record: if it is not valid strict
canonical JSON, has a wrong digest or `prev`, violates the schema or an invariant, or references invalid or missing
committed data, the investigation is `CORRUPT` (read-only; nothing is repaired, dropped or guessed), whether that line
is the last one or not. Incomplete append ≠ integrity failure.

- S-8.7 Versioning: journal format `v = 1` is the first version. A reader refuses a version it does not know
  (`JOURNAL_VERSION_UNSUPPORTED`). A later version that needs migration writes a new investigation whose
  `investigation_created` cites the source journal's last digest; no journal is rewritten in place.

### 8.7 Memory invariants

| Id | Family | Statement |
|---|---|---|
| M-1 | chronology | `seq` starts at 0 and increases by 1; `at` never decreases |
| M-2 | chain integrity | each `digest` is correct and each `prev` equals the previous record's `digest` (genesis for `seq = 0`) |
| M-3 | evidence provenance and write order | every observation names a blob that exists, whose SHA-256 equals its name, and a `source_ref`; a blob is durable (written, `fsync`ed, renamed) before the record that names it is appended |
| M-4 | no dangling references | every id a record refers to is defined by an earlier committed record of the same investigation |
| M-5 | no completed step without durable success | a step counts as succeeded only with a `step_succeeded` record whose output blobs exist (M-3) |
| M-6 | commit discipline | content records of an attempt lie between its `step_started` and its terminal execution record, and are counted only when that terminal record is `step_succeeded` |
| M-7 | no decision without support | every decision names a committed claim; every claim names committed evidence; a `conflicting` claim has at least two alternatives with evidence |
| M-8 | no silent supersession | a superseded claim is reachable from its successor through `claim_superseded`; the successor has new evidence |
| M-9 | root binding | `root_id` is null before the ACQUIRE commit and equal to the bound root in every record after it; no content record of another step precedes the bind |
| M-10 | layer order | references point only downward (S-8.4) |
| M-11 | single writer | records are appended only while the investigation lock is held |
| M-12 | no negative value | no claim, decision or report value means "not retracted"; `uncertain`, `unavailable` and `not_found_in_checked_sources` never become a finding |
| M-13 | determinism | equal committed inputs (section 10.2) give an equal content digest `C(J)` (MM section 7.3) |
| M-14 | duplicate suppression | at most one committed `step_succeeded` per step; a step whose key is committed is not started again |

## 9. Investigation Workflow Controller

### 9.1 Plan

The plan (version `plan-1`) is the fixed sequence of required steps:

| # | Step | Input | Output | Network | Pure |
|---|---|---|---|---|---|
| 1 | VALIDATE | request | validated request | no | yes |
| 2 | ACQUIRE | validated request | verified bundle; bound root | only for a capture request | no |
| 3 | EXTRACT | bundle | extraction document | no | deterministic (Stage 03 engine) |
| 4 | NORMALIZE | extraction | eligibility, identifier statuses, work candidates, observation keys | no | yes |
| 5 | LOOKUP | candidates | Q1 and Q2 lookups, index identity | no | deterministic (pinned index) |
| 6 | DETECT | candidates, lookups | coherence, claims, decisions, questions | no | yes |
| 7 | ASSEMBLE | fold | report, v1 projections | no | yes |
| 8 | VERIFY | journal, bundle, extraction | verification result | no | yes |

There are no optional steps in Stage 04. Steps run in order; step `k + 1` never starts before step `k` succeeded.

### 9.2 Step state machine

States: `pending`, `running`, `succeeded`, `failed_retryable`, `failed_terminal`, `deferred`. The step state is a
function of the journal (MM section 7.2); there is no other step state.

| From | Event (record) | To | Precondition | Postcondition |
|---|---|---|---|---|
| `pending` | `step_started(a = 1)` | `running` | lifecycle `CREATED` (VALIDATE) or `RUNNING`; previous step `succeeded`; lock held; step key computed | attempt 1 open |
| `running` | `step_succeeded` | `succeeded` | outputs written as blobs; content records appended; step-specific checks pass | outputs committed |
| `running` | `step_failed(retryable = true)` | `failed_retryable` | code in the step's retryable set (9.3) and `φ + 1 < A_max` | attempt closed |
| `running` | `step_failed(retryable = false)` | `failed_terminal` | code not retryable, or `φ + 1 = A_max` (code `RETRY_BUDGET_EXHAUSTED`) | step closed |
| `running` | `step_deferred(not_before)` | `deferred` | Stage 03 returned `deferred`; `f < F_max` | attempt closed |
| `running` | `step_failed(retryable = false)` | `failed_terminal` | Stage 03 returned `deferred` and `f = F_max` (code `DEFERRAL_BUDGET_EXHAUSTED`) | step closed |
| `running` | `step_interrupted` | `pending` | written on resume for an attempt with no terminal record (process died) and `φ + 1 < A_max` | attempt closed, uncommitted content ignored |
| `running` | `step_failed(retryable = false)` | `failed_terminal` | written on resume for an attempt with no terminal record and `φ + 1 = A_max` (code `RETRY_BUDGET_EXHAUSTED`) | step closed; a step that keeps killing the process ends |
| `failed_retryable` | `step_started(a + 1)` | `running` | lifecycle `RUNNING`; for ACQUIRE, the record's `at` ≥ the failed attempt's `not_before` when it recorded one (owner decision D-042) | new attempt |
| `pending` (after `step_interrupted`) | `step_started(a + 1)` | `running` | lifecycle `RUNNING` | new attempt |
| `deferred` | `step_started(a + 1)` | `running` | the record's `at` ≥ `not_before` (checkable from the journal alone) | new attempt |

Forbidden (refused by the append guard, MM section 8): any transition out of `succeeded` or `failed_terminal`;
`pending → succeeded`, `pending → failed_*`; two open attempts of one step; a `step_started` of step `k + 1` before step
`k` succeeded; a `step_started` while another step is `running`; content records outside an open attempt; a second
`step_succeeded` for a step.

`φ` is the number of attempts of the step that ended in `step_failed(retryable = true)` or `step_interrupted`, and `f`
the number that ended in `step_deferred`. `A_max = 3`: a step is abandoned at its third failed or interrupted
attempt, so a transient failure gets two retries. `F_max = 6`: a step is abandoned when Stage 03 defers it a seventh
time; 6 is the Stage 01 brief's bound on attempts per request (MR-14). A step therefore has at most `A_max` attempts,
except ACQUIRE of a capture request, which has at most `A_max + F_max` (= 9: two failed or interrupted, six deferred and
one final); the exhaustive controller model of Step 4 reaches these maxima and no more (correction SC-5). These are operational budgets, not decision thresholds: they bound work (no infinite
retry, RA R4-13) and never change a claim. Both are fixed in `plan-1`; changing them is a plan version change.

Live-ACQUIRE wall-clock bound (owner decision D-042, review finding F-11). Each ACQUIRE attempt of a capture request
runs as a dedicated child process (its own session) whose deadline the parent owns. The parent starts the timer
immediately before it launches the child, so the bound covers process start-up, DNS, connection, transfer, Stage 03's
own retries, bundle publication and the local completion path. `T_acq = deadline_s + op_timeout_s + 30 s` (240 s with
the Stage 03 defaults); it is a controller safety bound, not a scientific threshold. The child is asked to stop
gracefully within `T_acq` and is then killed and reaped; kill and reap latency are measured or bounded separately. An
attempt that exceeds `T_acq` ends `step_failed(ACQUIRE_WALL_CLOCK_EXCEEDED)` with `root_id = null` and
`wall_clock = {t_acq_ms, elapsed_ms}`; none of its output is authoritative: it binds no root, commits no bundle as
evidence, commits no evidence, claim, decision or question, and leaves no `step_succeeded` record. It is retryable
and counted in `φ` only if a retry can never start before a Retry-After instant the attempt observed (Stage 03
persists it before the kill, or Stage 04 records it as `not_before`); otherwise it is terminal or deferred. This is
proven in step 8 of the plan; the schema leaves the code's retryability open. The bound never weakens Stage 03's
throttling and the Stage 03 transport is not changed. A retained-bundle ACQUIRE uses no network and no timer.
`9 × T_acq` (2,160 s with the defaults) is the maximum live-ACQUIRE child execution budget of one investigation; it
is not the investigation's wall-clock upper bound, which also needs the termination and reap overhead and the other
steps' bounded work.

### 9.3 Step outcomes by step

| Step | Succeeds when | Retryable codes | Deferral | Terminal codes |
|---|---|---|---|---|
| VALIDATE | request valid | none | no | `INPUT_INVALID` |
| ACQUIRE | bundle opens and `verify_bundle` passes; identity checks S-4.6 pass; capture status `complete` or `partial` | Stage 03 network codes after its own retries: `HTTP_TIMEOUT`, `HTTP_CONNECTION_FAILED`, `HTTP_SERVER_ERROR`, `HTTP_UNAVAILABLE`, `HTTP_RATE_LIMITED`, `API_RATELIMITED`, `API_MAXLAG`, `ATTEMPTS_EXHAUSTED`, `NETWORK_GATE_BUSY`; `ACQUIRE_WALL_CLOCK_EXCEEDED` only under the Retry-After condition of D-042 (section 9.2), otherwise terminal | `DEFERRED_RETRY_AFTER` | `REVISION_NOT_FOUND`, `PAGE_MISSING`, `REVISION_TEXT_HIDDEN`, `BUNDLE_*`, `ROOT_IDENTITY_MISMATCH`, other Stage 03 codes |
| EXTRACT | document `status ∈ {complete, partial}` and schema-valid; capture fields equal the root | `EXTRACTION_DEADLINE_EXCEEDED`, `EXTRACTION_MEMORY_EXCEEDED`, `EXTRACTION_WORKER_FAILED` | no | `EXTRACTION_FAILED` (document `failed`), `ROOT_IDENTITY_MISMATCH` |
| NORMALIZE | always for a valid document | none | no | `NORMALIZE_INVALID` (a defect) |
| LOOKUP | index opens and its identity is recorded; every key queried (a raising query records `unavailable`, S-6.10) | none | no | Stage 02 `IndexUnavailable` codes: `INDEX_MISSING`, `INDEX_CORRUPT`, `INDEX_FORMAT_MISMATCH` (`store.py`, `query.py`) |
| DETECT | every candidate decided by D-1 to D-4 or D-6 to D-16 | none | no | `ADAPTER_INCONSISTENT`, `DECISION_TABLE_GAP` |
| ASSEMBLE | report and projections validate against their schemas | none | no | `REPORT_INVALID` |
| VERIFY | all checks of section 9.7 pass | none | no | `VERIFY_FAILED` with the failing check |

A deterministic step that fails because of its inputs would fail again on the same inputs, so it has no retryable
codes (a retry would repeat the result). The only retryable codes are network failures in ACQUIRE and resource limits
of the isolated Stage 03 worker in EXTRACT, which depend on the machine and not on the inputs.

### 9.4 Lifecycle

The lifecycle state is a function `λ` of the fold (MM section 7.2):

| State | Holds when | Terminal |
|---|---|---|
| `CREATED` | `investigation_created` only | no |
| `RUNNING` | some step not `succeeded`, none `failed_terminal`, no step `deferred`, inputs not stale | no |
| `BLOCKED` | a step is `deferred` (`not_before` in the payload) | no |
| `NEEDS_RESOLUTION` | all eight steps `succeeded`, verification passed, at least one open question | yes for Stage 04 |
| `COMPLETED` | all eight steps `succeeded`, verification passed, no open question | yes |
| `FAILED` | some step `failed_terminal` | yes |
| `STALE` | a resume found a changed input identity and recorded `stale_detected` (section 10.3); replay is read-only and only reports `stale` | yes |
| `CORRUPT` | the journal is invalid other than by a torn tail | yes |

Lifecycle transitions (each is caused by the record named; there is no lifecycle record of its own):

| From | Cause | To |
|---|---|---|
| — | `investigation_created` | `CREATED` |
| `CREATED` | `step_started(VALIDATE)` | `RUNNING` |
| `RUNNING` | `step_deferred` | `BLOCKED` |
| `BLOCKED` | `step_started` of the deferred step at or after `not_before` | `RUNNING` |
| `RUNNING` | `step_failed(retryable = false)` (including budget exhaustion) | `FAILED` |
| `RUNNING` | `verification_recorded(passed)` and `step_succeeded(VERIFY)`, no open question | `COMPLETED` |
| `RUNNING` | same, with an open question | `NEEDS_RESOLUTION` |
| `RUNNING`, `BLOCKED` | `stale_detected` (section 10.3) | `STALE` |
| any | invalid journal on open | `CORRUPT` (not recorded; computed) |

`STALE` is recorded by a `stale_detected` execution record `{changed: [identity names], recorded, current}` so that
a later reader sees why the investigation stopped. `NEEDS_RESOLUTION` is terminal for Stage 04 because Stage 04 has no
resolution action (S-7.6). `ABSTAIN` is a claim disposition, not a lifecycle state.

### 9.5 Explanation of transitions

- S-9.1 Every append is checked by `legal(record, fold(J))` (MM section 8) before it is written. A refused append is
  a defect, raised as an exception with the rule that refused it; it is never written.
- S-9.2 `citerift-investigate show` prints, for the current state, the next legal transition and the rule that
  permits it (for example: "step LOOKUP pending; previous step NORMALIZE succeeded at seq 41; rule T-START").

### 9.6 Idempotency

- S-9.3 The step key is `K(step) = H(step, plan version, the output digests of the steps it reads, the engine and
  schema identities it depends on, config digest)`. A committed step with the same key is never run again.
- S-9.4 `run` of a request whose investigation exists behaves as `resume`. `run` on a terminal investigation reports
  it and does nothing.
- S-9.5 Blob writes are idempotent (S-8.2); a repeated attempt of a pure step writes the same blobs.

### 9.7 Verification step

VERIFY checks, on the committed journal: invariants M-1…M-14 and W-1…W-8; `verify_bundle(bundle, extraction)`
passes; NORMALIZE, DETECT and ASSEMBLE re-run in memory from the committed observation blobs give the same output
digests (replay of the pure steps); every claim has a complete evidence chain (section 12); the report and v1
projections validate; the content digest `C(J)` is recorded.

### 9.8 Completion

- S-9.6 Completion predicate (MM section 9): `COMPLETED` or `NEEDS_RESOLUTION` only when every required step
  succeeded in a committed attempt, the report validates, verification passed and every claim has a complete evidence
  chain.
- S-9.7 Outcome (computed by ASSEMBLE from the committed claims, recorded in the report and used as the v1 status):
  `partial` when the extraction status is `partial`, or any claim is `LOOKUP_UNAVAILABLE`, or any question is open;
  otherwise `completed`. The report and v1 projections are exported only when the lifecycle is `COMPLETED` or
  `NEEDS_RESOLUTION`, that is after VERIFY committed. A `FAILED`, `STALE` or `CORRUPT` investigation exports no report
  and no v1 record; `show` and the exit status state why. (v1 records exist only for works with a positive claim, so
  the v1 status `failed` is never needed.)

### 9.9 Workflow invariants

| Id | Statement |
|---|---|
| W-1 | The controller holds no state that is not a function of the journal; after any crash, `fold(J)` is the whole controller state |
| W-2 | The step and lifecycle states of `fold(J)` form a legal path of the tables of sections 9.2 and 9.4 |
| W-3 | Steps start in plan order; at most one attempt is open at a time |
| W-4 | Per step, attempts ending in failure or interruption `≤ A_max` and deferrals `≤ F_max`, so at most `A_max` attempts, and `A_max + F_max` for ACQUIRE of a capture request |
| W-5 | A terminal lifecycle state is final: no record is appended after the record that made the lifecycle terminal |
| W-6 | A `step_started` without a terminal record is closed on resume, before anything else is appended, by `step_interrupted` (or by `step_failed(RETRY_BUDGET_EXHAUSTED)` when the budget is spent) |
| W-7 | `COMPLETED` and `NEEDS_RESOLUTION` imply the completion predicate (S-9.6) |
| W-8 | Each `IDENTITY_CONFLICT` and `CONTRADICTION_IN_SOURCES` claim has a committed decision `ROUTE_NEEDS_RESOLUTION` and an open question; no positive or negative claim exists for the same work candidate |

## 10. Consistency, recovery, replay and staleness

### 10.1 Authoritative state and recovery

The journal plus its blobs is the only authoritative state. On every open (run, resume, replay, show):

1. Take the lock (`flock`, exclusive, non-blocking). If held: `INVESTIGATION_BUSY`, nothing written. The kernel
   releases the lock when the holder dies, so a stale lock cannot exist on a local file system; the lock file's
   content (process id, start time) is informational only. Network file systems are not supported (RA R4-26).
2. Read the journal and identify a candidate incomplete tail: final bytes without the terminating newline (section
   8.6). Only the final record can be torn.
3. Validate the entire prefix (every complete record: strict canonical JSON, digest, `prev`, schema, M-1…M-14, the
   blobs it names) before changing anything. Any failure: `CORRUPT`, read-only, and the journal, its torn tail and
   any temporary file are left exactly as found.
4. Only if the prefix is valid and the open is writable, remove the torn tail (Copy → Verify → Preserve): copy the
   original journal to `journal.jsonl.torn-<k>`, verify the copy byte for byte and `fsync` the directory; write the
   validated prefix to a temporary file, verify it, `fsync` it and rename it over `journal.jsonl`; `fsync` the
   directory; re-read and require exactly the validated prefix. A read-only open reports the tail and changes
   nothing. (Owner decision D-044 approved this order: never repair first and discover corruption afterwards.)
5. Fold. An attempt with `step_started` and no terminal record is closed by `step_interrupted`, or by
   `step_failed(RETRY_BUDGET_EXHAUSTED)` when `φ + 1 = A_max` (W-6).
6. Recompute the step keys of committed steps from the current environment (section 10.3).
7. Continue from the first step that is not `succeeded`.

### 10.2 Crash and fault cases

| Case | What the journal holds | Recovery | Result |
|---|---|---|---|
| Crash before a blob is complete | a temporary file, no rename | temporary files are ignored and removed only after the fold shows no record names them | step re-run; same blobs |
| Crash after blob rename, before its record | an orphan blob | ignored by the fold (reported as orphan); kept | step re-run writes the same blob (no-op) |
| Crash after content records, before `step_succeeded` | uncommitted content | `step_interrupted`; content ignored (M-6) | step re-run; same committed content |
| Crash after `step_succeeded`, before the next `step_started` | a committed step | nothing to repair | next step starts |
| Torn final record | final bytes without a newline | prefix validated, then preserved copy and valid prefix (10.1) | resume from the prefix |
| Bit flip inside a record or blob | digest or hash mismatch | none | `CORRUPT`; no repair |
| Duplicate retry of a committed step | a committed step key | not run (M-14) | no duplicate |
| Repeated invocation (`run` twice) | same `investigation_key` | resume (S-9.4) | no duplicate investigation |
| Two processes at once | lock held by the first | second gets `INVESTIGATION_BUSY` | no interleaving |
| Stale lock | impossible on a local file system (kernel releases `flock`) | — | — |
| Changed input after interruption | a recorded identity differs | `stale_detected` | `STALE`; nothing reused |
| Changed engine, schema or index after interruption | a recomputed step key differs | `stale_detected` | `STALE` |
| Disk full | write fails | the failing blob or record is not committed; the attempt ends `step_failed(STORAGE_ERROR, retryable = false)` if a record can be written, otherwise the process exits and resume treats it as a crash | journal consistent |

### 10.3 Staleness

The **input identity vector** of an investigation: the request key; the bound root (`capture_sha256` and the
revision identity); the extraction engine identity (extractor version, profile digest, normalizer, `config_digest`);
the index identity (S-3.2); the Stage 04 identities (engine version, decision table version `dt-1`, plan version
`plan-1`, Stage 04 schema versions); the configuration and its digest (S-4.7), including the live-ACQUIRE bound
(owner decision D-042). The report records every component (`identities`), and `stale_detected` names the changed
ones.

- S-10.1 On resume, each committed step's key is recomputed from the current identities. If any differs from the
  recorded key, the investigation is `STALE`: no committed output is reused, nothing is re-run in it, and a new
  investigation (new key when the config or plan changes; otherwise the operator moves the stale directory aside)
  must be created. Stale evidence is never mixed with fresh evidence.
- S-10.2 A retained bundle whose content no longer hashes to its recorded `capture_sha256` is `CORRUPT` input
  (ACQUIRE terminal `BUNDLE_DIGEST_MISMATCH`), not `STALE`.

### 10.4 Replay

- S-10.3 `replay` opens the journal read-only, re-runs NORMALIZE, DETECT and ASSEMBLE from the committed observation
  blobs, re-verifies the bundle with Stage 03 `verify_bundle` and re-derives the extraction with `replay_bundle`,
  re-opens the index and checks its identity, and reports one of:
  - `reproduced`: identities equal and every recomputed output digest equals the committed one;
  - `differs`: identities equal but an output differs (a defect; the first differing record is named);
  - `stale`: an identity differs (which one is named).
- S-10.4 Replay is offline: it never calls `capture_revision`.
- S-10.5 Replay preserves contradictions: an `IDENTITY_CONFLICT` claim is reproduced with the same claim id; replay
  never resolves, upgrades or drops a claim.

## 11. Report and projections

### 11.1 Stage 04 report (`urn:citerift:schema:investigation:v1:report`, written in step 5 of the plan)

`{schema, schema_version, investigation_key, investigation_id, root, terminal_state, outcome, claims[],
observations[], evidence[], article_summary, limitations[], identities}`. Each entry of `claims[]` holds the claim, its
decision, its question (or null), its unit anchor and, for a not-found claim, the checked sources; decisions and
questions are therefore embedded per claim instead of in separate arrays. Claims are ordered by unit source byte
offset, then candidate key order. Each claim carries its rule id, reasons and evidence chain (section 12). The report
is a pure function of the committed fold at ASSEMBLE. `terminal_state` is the lifecycle state that the investigation
enters if VERIFY passes (`NEEDS_RESOLUTION` when a question is open, otherwise `COMPLETED`, S-9.7); it is computed from
the fold, and a report is exported only after VERIFY passed, so an exported report never states a state the
investigation did not reach. `FAILED`, `STALE` and `CORRUPT` investigations export no report. The report does not
hold the content digest `C(J)`, which covers the report and is recorded by VERIFY in `verification_recorded` (MM
section 7.3).

### 11.2 v1 projections

For each distinct work (by Stage 02 identity anchor) with at least one positive claim, one record valid against
`urn:citerift:schema:contracts:v1:investigation` 1.0.1: `subject_paper` from the record's identifiers;
`citations` = the units with that positive claim (language, title, revision id, revision sha1); `events` from the
Stage 02 events; `status` from S-9.7; `limitations` from the report; `created_at` from the journal (excluded from the
content digest); `investigation_id` from S-4.8. Several retraction events per paper (which v1 cannot hold in one
status) stay in the Stage 04 report, which `$ref`s v1 assertions by URN (MR-05). `schemas/contracts` is not changed.

## 12. Provenance

- S-12.1 Every claim's evidence chain contains: the root (`wiki`, `page_id`, `revision_id`, `capture_sha256`); the
  extraction digest and engine identity; the unit id and source anchor (byte span and the Stage-04-derived
  `unit_span_sha256`, section 4.3); each identifier
  occurrence's anchor, raw text hash, decoding steps and normalization record; the index identity (S-3.2); each
  lookup's keys, state, `evidence_digest` and event ids with `row_sha256`; the coherence result for a pair; the rule id
  and table version; the reasons.
- S-12.2 A claim without a complete chain is a VERIFY failure. Explanation text is generated from the rule id and the
  chain by a fixed template, never written freely.

## 13. Command-line interface (semantic)

`citerift-investigate run | resume | replay | verify | show`. Exit codes distinguish completed, needs-resolution,
partial, blocked, failed, stale, corrupt and busy. `run` and `resume` never print a negative statement; `show` prints
the lifecycle, step states and the next legal transition (S-9.2).

## 14. Vertical-slice contract (gate 04-A)

Each case runs through the real Stage 03 extraction and the real Stage 02 code. CI uses retained bundles and the
attributed Retraction Watch field subset; the full pinned index run is retained as real-data evidence.

| Case | Input | Expected |
|---|---|---|
| VS-1 | MMR vaccine, en 1381772671 | Wakefield original `RETRACTED_WORK_CITED`; Lancet notice citation `NOTICE_CITED`; markers observed |
| VS-2 | Haruko Obokata, ar 76190003 | `nature12968` `RETRACTED_WORK_CITED`; `nature12969` + PMID 24476881 `IDENTITY_CONFLICT`, question open, lifecycle `NEEDS_RESOLUTION`, preserved by replay |
| VS-3 | Obokata en 1372543632; GFAJ-1 en 1374726997 | retracted originals found; notice citations separate |
| VS-4 | an expression-of-concern case from the retained set | `CONCERN_CITED`, never retracted |
| VS-5 | BCAS3, ar 76488293 | `PMID_ROLE_COLLISION` carried; class by D-10 or D-14 as the evidence decides |
| VS-6 | a retained article with only `no_record` keys | `NOT_FOUND_IN_CHECKED_SOURCES` only; summary per S-7.7 |
| VS-7 | corrupted bundle; invalid request; schema-invalid extraction input | `FAILED` with the code; no claim |
| VS-8 | index missing; index of another format; injected 429 then deferral | `FAILED` or `BLOCKED` with the code; no claim, no negative |
| VS-9 | VS-1 killed after LOOKUP committed, then `resume` | ACQUIRE…LOOKUP not re-run (no new `step_started` for them); same `C(J)` as an uninterrupted run |
| VS-10 | replay of each completed case | `reproduced`; `stale` when the bundle, index, engine or schema identity is changed |

All VS inputs are design-exposed data (D-5) and are never final-evaluation evidence.

## 15. Security and boundaries

- S-15.1 No module under `src/citerift/investigation` imports `citerift.governance` (MR-01, AT-07); a static test
  enforces it.
- S-15.2 The only network path is Stage 03 `capture_revision` in ACQUIRE for a capture request, with Stage 03's host
  allowlist (MR-02, AT-08). A socket-blocking test runs every other step and replay.
- S-15.3 Paths: investigation directories are named by hashes; blobs by digests; files are opened with `O_NOFOLLOW`
  and refused when they are symbolic links; the memory root must not be inside the repository working tree.
- S-15.4 Untrusted content (wikitext, HTML) is parsed only by Stage 03 in its isolated worker; Stage 04 never
  evaluates content.
- S-15.5 Retained evidence copied into the repository is scanned for secrets before commit (Stage 03 found a
  third-party key id in captured pages).

## 16. Offline and replay guarantees

- S-16.1 Every step except ACQUIRE of a capture request runs without network.
- S-16.2 Given the journal, its blobs, the bundle and the same pinned index, replay is offline and deterministic.
- S-16.3 `C(J)` of a completed investigation is equal for an interrupted-and-resumed run and an uninterrupted run with
  the same inputs and the same committed ACQUIRE output (M-13, MM P6, VS-9). For a capture request interrupted before
  ACQUIRE committed, the resumed run captures again and may bind another snapshot.

## 17. Traceability

### 17.1 Gates

| Gate | Specification | Mathematical model | Risks (RA) |
|---|---|---|---|
| 04-A | 14, 9, 12 | 9, P6 | R4-01, R4-02, R4-04, R4-08, R4-11, R4-32 |
| 04-B | 4, 5, 11 | 2, 3 | R4-08, R4-16 |
| 04-C | 6, 7 | 4, 5, 6, 11, P1, P4, P5 | R4-01, R4-02, R4-04, R4-05, R4-30 |
| 04-D | 6.5, 7.5 (S-7.3, S-7.4), 9.9 W-8 | 5.3, P2, P3 | R4-03, R4-29 |
| 04-E | 8, 9, 10.1, 10.2 | 7, 8, P6 | R4-09, R4-10, R4-12, R4-13, R4-25, R4-26, R4-31 |
| 04-F | 10.3, 10.4, 16 | 10 | R4-06, R4-07, R4-11, R4-16, R4-17 |
| 04-G | 9.3, 7.5, 10.2 | 8, 9 | R4-02, R4-13, R4-23, R4-31 |
| 04-H | 15 | 2.1 | R4-14, R4-15, R4-26, R4-27, R4-28 |
| 04-I | plan section 12.3 (pre-registration, plan step 13) | 11.2 | R4-01, R4-18, R4-19, R4-20, R4-21, R4-22, R4-32 |
| 04-J | 1.1, 13 | 11.1 | R4-17, R4-24 |

### 17.2 Stage 01 MAESTRO requirements assigned to Stage 04

The Stage 01 brief (`docs/verification/stage-01/MAESTRO_DESIGN_BRIEF.md`) assigns these requirements to Stage 04.
The retained plan and owner decision D-4 changed the subject from a paper to an article revision; the table says where
each requirement is met, or where it moved.

| Requirement | Where | Note |
|---|---|---|
| MR-01 | S-15.1 | static import test (AT-07) |
| MR-02 | S-15.2 | network only through Stage 03 capture (AT-08) |
| MR-03 | S-1.3, 9.1 | fixed plan `plan-1` |
| MR-04 | S-4.3, 5.1 | request is a pinned revision (D-4); DOI or PMID subjects and `history` move to Stage 07 (plan 6) |
| MR-05 | 11.2 | v1 record per positive work; several events per paper in the Stage 04 report, which `$ref`s v1 |
| MR-06 | 11.2, S-12.1 | language, title, revision id and sha1; discovery method is the wikitext parse |
| MR-07 | 9.1 | all eight steps are required; there are no optional tasks in Stage 04 |
| MR-08 | 9.1, S-3.1 | pure steps; engine outputs stored as observations |
| MR-09 | 9.2, 9.4; MM 8 | tables are data; completeness checked by the Step 4 enumeration |
| MR-10 | S-9.7, S-7.5 | outcome rule; a failed step never produces a negative |
| MR-11 to MR-13 | 8, 10 | append-only journal, resume, memory outside the repository |
| MR-14 | 3.1, 9.2 | Stage 03 rate limiter and Retry-After; `F_max` |
| MR-15 | 9.2 | bounded by `A_max`, `F_max`, Stage 03 timeouts and the live-ACQUIRE wall-clock bound `T_acq` of owner decision D-042 (review finding F-11, design-unblocked, not yet implementation-verified); `BLOCKED` ends the run without waiting. There is no per-investigation wall-clock timer and no `timed_out` step state |
| MR-16 | — | cancellation is Stage 07 (plan 6) |
| MR-17 | 9.3 | stable codes |
| MR-17a, MR-17b | 3.1, 7.3 | HTTP 200 error bodies are Stage 03's (`fetch.py`); only a committed `no_record` gives `NOT_FOUND_IN_CHECKED_SOURCES` |
| MR-21 | 10.4, 16 | determinism and replay |
| MR-23 | 12 | provenance chain |
| MR-24 | 15 | Stage 04 stores no user data; Stage 03 captures do not request the editor (`rvprop` has no `user`, `capture.py`) |
| MR-25 | 14 | CI uses the attributed field subset; the full Retraction Watch file is never committed |
| CP-1 | S-3.1, S-3.2 | snapshot id, file hash, event id and row hash per event |
| CP-2 | 7.2, 11.2 | four event types map one-to-one; all events kept |
| CP-3 | D-6, D-15 | notices never counted as the work |
| CP-4 | S-4.1, S-6.1 | candidates only from the pinned revision's wikitext |
| CP-5 | — | cross-language comparison is Stage 07 |
| CP-6 | D-16, S-7.5 | `not_found_in_checked_sources` / `uncertain` with checked sources |

## 18. Assumptions

- A-1 The Stage 02 index and the Stage 03 engine are used at their accepted versions; any change is a staleness event.
- A-2 Revision ids are immutable and unique within a wiki (MediaWiki guarantee); page id is verified, not assumed.
- A-3 The memory root is on a local POSIX file system with `flock`, `fsync` and atomic `rename`.
- A-4 Stage 04 runs one investigation per process; concurrent investigations use different directories.
