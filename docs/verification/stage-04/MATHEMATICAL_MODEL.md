# Stage 04 Mathematical Model: Detection Engine and Vertical Slice

Status: Step 3 of the retained plan (`planning/STAGE04_MASTER_EXECUTION_PACKAGE.md`, section 14), written before any
Stage 04 code. Owner authorization: `cmsg_018VCB51nDHP6HXmLU4ea5yPTg4B2mbvArm7ZsYe8DG6Ag` (2026-11-10). This document
gives the formal objects behind `SPECIFICATION.md` (SPEC) and is checked against it by the Step 3 consistency check
(`review/step3/check_step3_docs.py`). Facts about the accepted engines name the file they were read from at
`a152885`; they are labelled **F-n** and are the only assumptions about Stages 02 and 03 that the propositions use.

Every definition below states its **domain**, **codomain**, **rule**, **invariants**, **precedence** (where more than
one case can apply) and **failure behavior**. A failure is never a value of a function: it is a step failure with a
stable code (SPEC section 9.3), written `fail(CODE)`.

## 1. Notation

| Symbol | Meaning |
|---|---|
| `Str`, `ℕ`, `ℕ⁺`, `Hex64` | strings, natural numbers, positive integers, 64-character lowercase hexadecimal strings |
| `X?` | `X ∪ {null}` |
| `⟨a, b, …⟩` | a tuple; encoded as a JSON array |
| `first(r₁, …, rₙ)` | the first rule whose guard holds, in the order given |
| `J = ⟨j₀, …, jₙ₋₁⟩` | a journal: a finite sequence of records |
| `W = {en, ar}` | the supported wikis |
| `KS = {doi, pmid}` | identifier schemes |

## 2. Canonical encoding, hashing and derived ids

### 2.1 Canonical encoding `canon`

- Domain: JSON values whose object keys are strings, whose numbers are integers or finite floats, with no duplicate
  keys and no lone surrogates.
- Codomain: byte strings.
- Rule: `canon(x) = UTF-8(json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))`.
  This is the encoding already used by Stage 02 (`src/citerift/retraction/canonical.py`, `canonical`) and Stage 03
  (`src/citerift/wiki/canonical.py`, `canonical_bytes`), so engine outputs and Stage 04 records share one encoding.
  Stage 04's own record fields hold integers, never floats. Reading uses a strict parser that rejects duplicate keys,
  NaN or infinity and invalid UTF-8 (the Stage 03 `loads_strict` rules, reimplemented in Stage 04 without importing
  private names).
- Invariants: `canon` is a function (equal values give equal bytes); `parse(canon(x)) = x`.
- Failure: a value outside the domain is `fail(CANON_INVALID)` in the step that tried to write it; it is never coerced.

### 2.2 Tagged hash `H`

- Domain: a tag string and a finite sequence of JSON values.
- Codomain: `Hex64`.
- Rule: `H(tag, x₁, …, xₙ) = hex(SHA-256(canon(⟨tag, x₁, …, xₙ⟩)))`.
- Invariants: the tag separates purposes (a root id can never equal a claim id computed from the same values).
  Collision resistance of SHA-256 is assumed (assumption **A-H**); every "equal ids imply equal content" statement
  below holds under A-H.
- Failure: inherits `canon`.

### 2.3 Derived UUID

- Domain: `Hex64` (an investigation key).
- Codomain: lowercase UUID strings matching the v1 pattern (`schemas/contracts/v1/investigation.schema.json`,
  `investigation_id`).
- Rule: `uuid(k)` takes the first 16 bytes of `SHA-256(canon(⟨"citerift-investigation-uuid/1", k⟩))`, sets the
  version nibble to 8 and the variant bits to `10` (RFC 9562, UUIDv8), and formats it in lowercase 8-4-4-4-12 form.
- Invariants: deterministic; distinct keys give distinct UUIDs except with probability `2⁻¹²²` per pair.
- Failure: none (total on its domain).

## 3. Investigation root and identities

### 3.1 Investigation root

- Domain: subject records `s = {type, identity, display}`.
- Codomain: `root_id ∈ Hex64`, or `fail`.
- Rule: for `type = "wikipedia_article_revision"`, `identity = ι = ⟨wiki, page_id, revision_id, capture_sha256⟩` with
  `wiki ∈ W`, `page_id, revision_id ∈ ℕ⁺`, `capture_sha256 ∈ Hex64` (the SHA-256 of the bundle's `capture.json`
  bytes, which record the capture request and every artifact digest; `src/citerift/wiki/bundle.py`, `open_bundle`).
  `root_id = H("citerift-investigation-root/1", type, ι)`. `display = ⟨title, revision_sha1⟩` is outside the hash.
- Invariants:
  - **RT-1** The title never enters `root_id`; two titles of one revision give one root.
  - **RT-2** Two snapshots of one revision with different bytes have different roots (they can differ in render).
  - **RT-3** The root is bound once (SPEC S-4.4): there is at most one committed `step_succeeded(ACQUIRE)` (M-14), and
    `root_id` of every later record equals it (M-9).
- Precedence: none.
- Failure: another `type` is `fail(SUBJECT_TYPE_UNSUPPORTED)`; bundle and extraction identities that differ
  (SPEC S-4.6) are `fail(ROOT_IDENTITY_MISMATCH)`; a request without a pinned revision is `fail(INPUT_INVALID)` with
  reason `REVISION_NOT_PINNED`.

### 3.2 Investigation key

- Domain: request keys `ρ ∈ {⟨wiki, revision_id⟩, ⟨capture_sha256⟩}`, plan version `π`, configuration digest `γ`.
- Codomain: `Hex64`.
- Rule: `key(ρ, π, γ) = H("citerift-investigation/1", ρ, π, γ)`; the directory name is `key`, the v1 id is
  `uuid(key)` (2.3).
- Invariants: one request under one plan and configuration addresses one investigation (idempotency, SPEC S-9.4).
- Failure: none beyond request validation.

### 3.3 Child identities

The child ids of SPEC section 4.3 are values of `H` with distinct tags over the parent id and the child's anchor or
content. Invariant **CH-1**: a child id is a function of committed content only (never of `seq`, attempt or time), so
an interrupted-and-resumed run and an uninterrupted run assign equal ids to equal content.

## 4. Inputs to detection

### 4.1 Stage 03 extracted unit

- Domain: an extraction document `X` valid against `schemas/wiki/v1/extraction.schema.json` with `X.status ≠ failed`.
- Codomain: the set `Units(X)` of tuples `u = ⟨id, container, kind, anchor, I(u)⟩`, where `anchor = ⟨b₀, b₁, h⟩` is the
  source byte span and raw SHA-256, and `I(u)` is the set of identifier occurrences with `unit_id = id`.
- Rule: read as given; Stage 04 never re-parses wikitext.
- Invariants: every unit names one container of `X`; anchors are as Stage 03 reports them (its accepted G-gates).
- Failure: a unit whose container is missing is `fail(NORMALIZE_INVALID)`; a document that is not schema-valid is
  `fail(EXTRACTION_FAILED)` in EXTRACT.

### 4.2 Citation unit and use eligibility

- Domain: `Units(X)`.
- Codomain: `E(u) ∈ {CITED, UNUSED, USE_NOT_ESTABLISHED}` with a reason.
- Rule: `E(u) = first(` (1) `binding_state = conflicting_definitions` → `USE_NOT_ESTABLISHED`; (2) container kind
  `bibliography_entry` → `CITED`; (3) a use of the container has binding `bound` or `anonymous` → `CITED`; (4) kind
  `list_defined_note` → `UNUSED`; (5) otherwise → `USE_NOT_ESTABLISHED` `)`. A **citation unit** is a unit with
  `E(u) = CITED`.
- Invariants: `E` is total (case 5 is the default) and never maps an undetermined case to `UNUSED`.
- Precedence: as listed; (1) comes first because a conflicting definition makes the shown body unknown even when it
  is used.
- Failure: none (total).

### 4.3 Normalized identifier set

- Domain: identifier occurrences `o ∈ I(u)` with fields `scheme ∈ KS`, `role`, `boundary`, `normalization`.
- Codomain: occurrence status `st(o) ∈ {CONFIRMED, UNCONFIRMED, MALFORMED}` for candidate roles
  `CR = {primary_citation_field, identifier_link}`; the **normalized identifier set** of `u`:
  `K(u) = {⟨o.scheme, o.normalization.normalized⟩ : o ∈ I(u), o.role ∈ CR, st(o) ≠ MALFORMED}`.
- Rule: `st(o) = MALFORMED` if `normalization` is null or `valid = false`; else `CONFIRMED` if the boundary is
  `field`, `delimited` or `url`, no ambiguous DOI-path step was applied, and no extraction exception or `IDENTIFIER_*`
  issue other than `CO_REPORTED_IDENTIFIERS` names `o`; else `UNCONFIRMED`.
- Taint: `τ(u) = ∃o ∈ I(u): (o.role ∈ CR ∧ st(o) ≠ CONFIRMED) ∨ o.role = unresolved`, with the reasons
  `IDENTIFIER_UNCONFIRMED`, `IDENTIFIER_MALFORMED`, `IDENTIFIER_ROLE_UNRESOLVED`.
- Invariants: `K(u)` holds only keys produced by Stage 02's normalizer as recorded by Stage 03 (no Stage 04
  normalization); observation-role keys are never in `K(u)`.
- Precedence: `MALFORMED` before the boundary test.
- Failure: none (total on schema-valid input).

### 4.4 Work candidates

- Domain: `K(u)`, split into `D(u)` (DOI keys) and `P(u)` (PMID keys).
- Codomain: a non-empty finite set `Cand(u)` of candidates `c = ⟨u, keys(c), σ(c), flags(c)⟩`.
- Rule: if `|D| ≤ 1 ∧ |P| ≤ 1 ∧ D ∪ P ≠ ∅`: one candidate with all keys, `σ ∈ {DOI, PMID, PAIR}`; if `D ∪ P = ∅`: one
  candidate with `σ = NONE`; otherwise one candidate per key with `σ ∈ {DOI, PMID}` and flag `CO_REPORTED_MULTIPLE`.
- Invariants: **CD-1** a `PAIR` candidate is the only candidate of its unit; **CD-2** keys are never merged across
  co-reported identifiers.
- Failure: none (total).

### 4.5 Stage 02 lookup result

- Domain: a query `q = ⟨d?, p?⟩` of valid keys, and one opened index `ix` with identity
  `id(ix) = ⟨snapshot_id, policy_version, lookup schema version, file SHA-256⟩`.
- Codomain: lookup results `ℓ = ⟨state, events, issues, projection, evidence_digest⟩` with
  `state ∈ S₂ = {matched, notice_only, ambiguous_identity, no_record, invalid_query, unavailable}`.
- Rule: `ℓ = render(gather(d, p))` with all events recorded (SPEC S-3.1); a raised database error gives
  `state = unavailable` with the error code and no events (SPEC S-6.10).
- Facts used (read in `src/citerift/retraction/query.py` and `policy.py` at `a152885`):
  - **F-1** `gather` returns one of the first five states; `unavailable` is never returned by `gather`.
  - **F-2** For `matched` from `gather`, the projection status is `verified_fact`, `uncertain` or `conflicting`
    (`policy.reduce`; `checked_sources` is never empty for a `gather` result, so the `NO_SOURCE_IN_VIEW` branch is
    not reached).
  - **F-3** For `no_record`, the projection is `uncertain` with value `not_found_in_checked_sources`, or with value
    null when relevant quarantined rows exist (`COVERAGE_GAP_RELEVANT_ROWS`).
  - **F-4** A `verified_fact` value is one of `retracted`, `expression_of_concern`, `correction`, `reinstated` (the
    store's `event_type` CHECK constraint in `store.py` and the Crossref `TYPE_MAP` in `corroboration.py`).
  - **F-5** The direct events of the result (`linked_via` null) with `matched_by = doi` are exactly the index events
    `O_d = {e : e.original_doi = d}` for a DOI-only query; those with `matched_by = pmid` are exactly
    `O_p = {e : e.original_pmid = p}` for a PMID-only query (both the `ambiguous_identity` and the `matched` branch
    label `O_p` direct). Events reached by co-occurrence carry `linked_via ∈ {pmid_cooccurrence, doi_cooccurrence}`.
  - **F-6** For a pair query, `gather` returns `ambiguous_identity` if and only if
    `¬compat(d, p) := ∃e ∈ O_d: e.original_pmid ∉ {p, null} ∨ ∃e ∈ O_p: e.original_doi ∉ {d, null}`; it then returns
    `O_d ∪ O_p` as direct events. When `compat(d, p)`, its direct events are `O_d` (labelled `doi`) and, only when
    `O_d = ∅`, `O_p` (labelled `pmid`).
  - **F-7** `_events` builds new event objects for every query, so labels set by one query never reach another.
  - **F-8** A `notice_only` or `ambiguous_identity` result has the projection `uncertain` with value null; a `matched`
    result may carry a `PMID_ROLE_COLLISION` issue (`_finish`) and, with status `uncertain` or `conflicting`, the
    basis reason `BRIDGE_ONLY_SUPPORT` (`policy.reduce`); `conflicting` has value null. A `verified_fact` value
    `reinstated` needs supersession links (`policy._reduce`), which `gather` receives only as an argument that Stage
    04 never passes.
  - **F-9** For a pair query of valid keys, `st(Q2)` is a function of `st(Q1(d))`, `st(Q1(p))` and `compat(d, p)`:
    `ambiguous_identity` iff `¬compat`; otherwise `matched` iff `st(Q1(d)) = matched` or
    `st(Q1(p)) ∈ {matched, ambiguous_identity}`; otherwise `notice_only` iff one of them is `notice_only`; otherwise
    `no_record`. A DOI-only query is never `ambiguous_identity`; a PMID-only query is `ambiguous_identity` only when
    `O_p` names two or more DOIs, and then `O_p` holds a witness.
  - F-1 to F-9 were checked in Step 4 against the real `gather` on all 192 abstract index worlds of
    `simulations/stage04/stage02_abstraction.py` and on the frozen Stage 02 cases (`SIMULATION_REPORT.md`).
- Invariants: `ℓ` is a function of `(q, ix)` (MR-21); the index is read-only.
- Failure: an index that cannot be opened is `fail(c)` for the LOOKUP step with Stage 02's code
  `c ∈ {INDEX_MISSING, INDEX_CORRUPT, INDEX_FORMAT_MISMATCH}` (SPEC 9.3), never a lookup result.

The **lookups of a candidate** are `Λ(c) = {Q1(k) : k ∈ keys(c)} ∪ ({Q2(c)} if σ(c) = PAIR)`, and the **deciding lookup**
is `L(c) = Q2(c)` for `PAIR`, `Q1(k)` for the single key otherwise, undefined for `NONE`. A lookup is **available** when
its state is not `unavailable`.

### 4.6 Evidence relation

- Domain: committed observations `Obs` (blobs) and JSON pointers into them.
- Codomain: evidence items `ev = ⟨evidence_id, obs, pointer, kind, refs⟩` with
  `evidence_id = H("citerift-evidence/1", obs, pointer)`.
- Rule: the evidence relation `supports ⊆ Evidence × Claims` holds when the claim lists the evidence id in
  `supporting` or in an alternative; `contradicts` likewise for `contradicting`.
- Invariants: **EV-1** every evidence item resolves: `pointer` names a value inside the blob `obs`; **EV-2** a claim
  never carries a value that is not the value at the pointer of one of its supporting evidence items, or a constant of
  the decision table (class, rule id, reason code).
- Failure: an unresolvable pointer is `fail(NORMALIZE_INVALID)` or `fail(VERIFY_FAILED)`, depending on the step that
  finds it.

## 5. Detection

### 5.1 Inputs of the detection function

For a candidate `c` of unit `u`: `ξ(c) = ⟨E(u), σ(c), τ(u), Λ(c), κ(c), L(c)⟩`. The investigation-level preconditions
(rows O-1 to O-3 of SPEC 7.3) are not inputs of `δ`: when one holds, DETECT does not run.

### 5.2 Decision table as a function

- Domain: `ξ(c)` for every candidate of every unit of a committed NORMALIZE output, given committed LOOKUP output.
- Codomain: `Class ∪ {fail(ADAPTER_INCONSISTENT), fail(DECISION_TABLE_GAP)}` where
  `Class` is the fifteen classes of SPEC 7.2.
- Rule: `δ(c) = first(D-1, …, D-17)` with the guards of SPEC 7.3. Formally, writing `st(ℓ)`, `ps(ℓ)` (projection
  status), `pv(ℓ)` (projection value) and `br(ℓ)` (basis reasons):

| Rule | Guard `g_i(ξ)` | Value |
|---|---|---|
| D-1 | `E = UNUSED` | `UNUSED_DEFINITION` |
| D-2 | `E = USE_NOT_ESTABLISHED` | `UNRESOLVED_USE` |
| D-3 | `σ = NONE ∧ ¬τ` | `NO_IDENTIFIER` |
| D-4 | `σ = NONE ∧ τ` | `UNRESOLVED_IDENTIFIER` |
| D-5 | `∃ℓ ∈ Λ: st(ℓ) = invalid_query` ∨ `∃ℓ ∈ Λ ∖ {L}: ℓ ∉ Contract` ∨ `st(Q1(DOI)) = ambiguous_identity` ∨ `(σ = PAIR ∧ ¬pairok(Λ))` | `fail(ADAPTER_INCONSISTENT)` |
| D-6 | `σ = PAIR ∧ κ = INCOMPATIBLE` | `IDENTITY_CONFLICT` |
| D-7 | `∃ℓ ∈ Λ: st(ℓ) = matched ∧ ps(ℓ) = conflicting ∧ pv(ℓ) = null` | `CONTRADICTION_IN_SOURCES` |
| D-8 | `τ` | `UNRESOLVED_IDENTIFIER` |
| D-9 | `st(L) = ambiguous_identity ∧ ps(L) = uncertain ∧ pv(L) = null` | `UNRESOLVED_IDENTITY` |
| D-10 | `st(L) = matched ∧ L ∈ Contract ∧ (collision(L) ∨ BRIDGE_ONLY_SUPPORT ∈ br(L))` | `UNRESOLVED_IDENTITY` |
| D-11 | `st(L) = matched ∧ ps(L) = uncertain ∧ pv(L) = null` | `UNRESOLVED_STATUS` |
| D-12 | `st(L) = no_record ∧ ps(L) = uncertain ∧ pv(L) = null` | `UNRESOLVED_STATUS` |
| D-13 | `∃ℓ ∈ Λ: st(ℓ) = unavailable` | `LOOKUP_UNAVAILABLE` |
| D-14 | `st(L) = matched ∧ ps(L) = verified_fact ∧ pv(L) ∈ dom(pos)` | `pos(pv(L))` |
| D-15 | `st(L) = notice_only ∧ ps(L) = uncertain ∧ pv(L) = null` | `NOTICE_CITED` |
| D-16 | `st(L) = no_record ∧ ps(L) = uncertain ∧ pv(L) = not_found_in_checked_sources` | `NOT_FOUND_IN_CHECKED_SOURCES` |
| D-17 | true | `fail(DECISION_TABLE_GAP)` |

  where `collision(L)` holds when `L` has a `PMID_ROLE_COLLISION` issue naming an event with `matched_by = pmid`, and
  `pos(retracted) = RETRACTED_WORK_CITED`, `pos(expression_of_concern) = CONCERN_CITED`,
  `pos(correction) = CORRECTION_CITED`, `pos(reinstated) = REINSTATED_WORK_CITED` (so `dom(pos)` is the four values
  of F-4). `Contract` is the set of lookup results whose state and projection are among the forms of F-1 to F-4 and
  F-8 (`unavailable` included). `pairok(Λ)` holds when every witness and co-naming event sits in a lookup whose state
  can hold it (a witness of `Q1(d)` needs `matched`, of `Q1(p)` needs `matched` or `ambiguous_identity`, of `Q2`
  needs `ambiguous_identity`, and a co-naming event needs an available `Q1` that is `matched` or
  `ambiguous_identity`), `Q1(p)` is `ambiguous_identity` only with a witness, `Q2` is `ambiguous_identity` exactly when
  it holds a witness, and, when all three are available, `st(Q2)` is the state F-9 implies (which includes P2). The
  exact forms in D-7 to D-16 make every malformed projection fall through: to D-5 for a lookup other than `L`, to
  D-17 for `L` (Step 4 corrections SC-1 and SC-2, `review/step4/STEP4_SPEC_CORRECTIONS.md`).
- Invariants: `δ` is a function of `ξ(c)` only (no hidden input, no randomness, no clock); the set of reason codes
  attached to a claim is a function of `ξ(c)` (SPEC 7.3).
- Precedence: the row order; the tiers of SPEC 7.1.
- Failure: D-5 and D-17 end DETECT terminally; no claim of the investigation is committed.

Epistemic status and disposition are functions of the class (SPEC tables 7.2 and 7.6): `status(class)` and
`disp(class)`.

### 5.3 Work-identity coherence relation

- Domain: `PAIR` candidates `c` with keys `d`, `p` and their lookups `Λ(c) = {Q1(d), Q1(p), Q2(c)}`.
- Codomain: `κ(c) ∈ {INCOMPATIBLE, COHERENT, UNDETERMINED, NOT_DETERMINED}`.
- Rule: let `Dir(ℓ)` be the direct events of `ℓ` (`linked_via` null), and
  `wit(ℓ) = {e ∈ Dir(ℓ) : (e.matched_by = doi ∧ e.original_doi = d ∧ e.original_pmid ∉ {p, null}) ∨
  (e.matched_by = pmid ∧ e.original_pmid = p ∧ e.original_doi ∉ {d, null})}`. Then

  `κ = first(` `∃ℓ ∈ Λ available: wit(ℓ) ≠ ∅` → `INCOMPATIBLE`; `Q1(d)` or `Q1(p)` unavailable → `NOT_DETERMINED`;
  `∃e ∈ Dir(Q1(d)) ∪ Dir(Q1(p)): e.original_doi = d ∧ e.original_pmid = p` → `COHERENT`; true → `UNDETERMINED` `)`.

- Relation: the **work-identity coherence relation** `d ≈ p` ("the checked sources do not state that `d` and `p`
  name different works") is `κ ≠ INCOMPATIBLE`; `d ≡ p` ("they state that `d` and `p` name the same work") is
  `κ = COHERENT`. Only `INCOMPATIBLE` changes the class; `UNDETERMINED` adds `PAIR_UNCORROBORATED`.
- Invariants: `κ` uses only direct events, so a link that Stage 02 made by co-occurrence never decides it.
- Precedence: a witness decides `INCOMPATIBLE` even when another lookup is unavailable (the owner's order: identity
  contradiction before operational failure); the claim then carries `LOOKUP_PARTIAL`.
- Failure: none (total); disagreement with Stage 02 is caught by D-5.

**Proposition P2 (coherence agrees with Stage 02's pair rule).** If `d` and `p` are valid and `Q1(d)`, `Q1(p)`,
`Q2(c)` are all available on one index, then `κ = INCOMPATIBLE ⟺ st(Q2) = ambiguous_identity`.

*Proof.* By F-5, the direct `doi`-labelled events of `Q1(d)` are `O_d` and the direct `pmid`-labelled events of
`Q1(p)` are `O_p`; by definition every `e ∈ O_d` has `original_doi = d` and every `e ∈ O_p` has `original_pmid = p`.
So `wit(Q1(d)) ∪ wit(Q1(p)) = ∅ ⟺ compat(d, p)`. By F-6 the direct events of `Q2` are subsets of `O_d ∪ O_p` with the
same labels, so `wit(Q2) ⊆ wit(Q1(d)) ∪ wit(Q1(p))` up to event identity (an event in `O_d ∩ O_p` has
`original_doi = d` and `original_pmid = p` and is never a witness, whichever label it carries). Hence
`κ = INCOMPATIBLE ⟺ ¬compat(d, p) ⟺ st(Q2) = ambiguous_identity` (F-6). F-7 guarantees that the labels read are the
ones each query set. ∎

D-5 turns any violation of P2 (a changed Stage 02 or a defective adapter) into a terminal failure instead of a silent
choice. P2 is also tested on the synthetic variants of SPEC S-7.4 and by the reference model of Step 4.

### 5.4 Contradiction predicate

- Domain: claims.
- Codomain: booleans.
- Rule: `contra(claim) ⟺ status(claim.class) = conflicting ⟺ claim.class ∈ {IDENTITY_CONFLICT, CONTRADICTION_IN_SOURCES}`.
- Invariants: **CO-1** a contradicting claim has at least two alternatives, each with at least one supporting
  evidence item (v1 rule; M-7); **CO-2** `contra(claim) ⇒ disp = ROUTE_NEEDS_RESOLUTION` and an open question (W-8);
  **CO-3** no other claim exists for the same candidate (`δ` is a function).
- Failure: a contradicting claim that cannot be given two alternatives with evidence is `fail(VERIFY_FAILED)`.

### 5.5 Abstention predicate

- Rule: `abst(claim) ⟺ status(claim.class) ∈ {uncertain, unavailable} ∧ claim.class ≠ NOT_FOUND_IN_CHECKED_SOURCES`,
  that is `UNRESOLVED_IDENTITY`, `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`, `LOOKUP_UNAVAILABLE` and `NOTICE_CITED`.
- Invariants: **AB-1** an abstention is never counted as a finding or a negative (it has no value, SPEC 7.2); **AB-2**
  each abstention carries at least one reason code.
- Failure: an abstention without a reason is `fail(VERIFY_FAILED)`.

### 5.6 Propositions on detection

**Proposition P1 (totality; D-17 is unreachable).** Under F-1 to F-4, for every candidate whose inputs are committed,
some rule D-1 to D-16 holds.

*Proof.* If `E ≠ CITED`, D-1 or D-2 holds (4.2 is total). If `σ = NONE`, D-3 or D-4 holds (`τ` is boolean). Otherwise
`L` is defined (4.5) and `st(L) ∈ S₂` (F-1 plus the adapter's `unavailable`). Case `invalid_query`: D-5. Case
`unavailable`: D-13, since `L ∈ Λ`. Case `ambiguous_identity`: D-9. Case `notice_only`: D-15. Case `no_record`: by F-3
`pv(L)` is null (D-12) or `not_found_in_checked_sources` (D-16). Case `matched`: by F-2 `ps(L)` is `conflicting`
(D-7), `uncertain` (D-11) or `verified_fact` (D-14, and `pos(pv(L))` is defined by F-4). Each case reaches a rule
before D-17 unless an earlier rule fired. ∎

P1 depends on F-1 to F-4. If Stage 02 ever violates them, D-17 fails closed; the reference model of Step 4 enumerates
the abstract input domain to check that the implementation matches the table. Step 4 result: over the 12,632,448
abstract inputs of `simulations/stage04/decision_space.py`, no input that Stage 02 and Stage 03 can produce reaches
D-5 or D-17, and no input they cannot produce yields a positive class or `NOT_FOUND_IN_CHECKED_SOURCES`
(`SIMULATION_REPORT.md`).

**Proposition P3 (identity conflict is preserved).** If `σ(c) = PAIR`, `E(u) = CITED`, D-5 does not hold and
`κ(c) = INCOMPATIBLE`, then (a) `δ(c) = IDENTITY_CONFLICT` whatever the projections of `Λ(c)` are; (b) no claim of
the unit `u` is positive or `NOT_FOUND_IN_CHECKED_SOURCES`; (c) replay of DETECT on the same committed observations
gives the same `claim_id`.

*Proof.* (a) D-1 to D-4 do not hold (`E = CITED`, `σ ≠ NONE`), D-5 does not hold by assumption, and D-6 holds. (b) By
CD-1 `c` is the only candidate of `u`, and `δ` gives it exactly one class. (c) `claim_id = H(cand_ref, class, rule id,
table version, sorted evidence ids)`; all arguments are functions of committed observations (CH-1) and `δ` is a pure
function of `ξ(c)`. ∎

**Proposition P4 (monotone abstention-first precedence).** Call a guard *monotone* when it stays true if identifier
occurrences or lookups are added to the unit and no existing one is removed or changed. The guards of D-5 (first
disjunct), D-6 (for a fixed pair), D-7, D-8 and D-13 are monotone (each is an existential statement over occurrences,
witnesses or lookups). If one of them holds for `ξ`, then `δ(ξ')` is not a positive class and not
`NOT_FOUND_IN_CHECKED_SOURCES` for any extension `ξ'` of `ξ` that keeps `σ`.

*Proof.* The guard still holds in `ξ'`, it precedes D-14 and D-16, and `first` returns a rule no later than it. ∎

Adding a key of the other scheme changes `σ` (for example `DOI → PAIR`) and therefore `L`; P4 does not claim
monotonicity across such a change. The property test of plan section 12.1 ("adding a contradicting key never upgrades
a claim") is the instance where the added key creates a witness: then D-6 holds and the result is
`IDENTITY_CONFLICT`, never a positive class.

**Proposition P5 (no negative).** No value of `δ` means "not retracted", and `δ(c) = NOT_FOUND_IN_CHECKED_SOURCES`
implies: `E(u) = CITED`, `σ ≠ NONE`, `¬τ`, every lookup of `c` is available and none is `invalid_query`, and
`st(L(c)) = no_record` with value `not_found_in_checked_sources` in a committed LOOKUP.

*Proof.* The codomain lists no such value (SPEC 7.2). D-16 is reached only when D-1, D-2, D-3, D-4, D-5, D-8 and D-13
do not hold, which are the listed conditions; its own guard gives the last one; DETECT runs only after LOOKUP
committed (O-3). ∎

## 6. Claims, decisions and questions

- Claim: `claim(c) = ⟨claim_id, cand_ref, class, status(class), value, alternatives, rule, reasons, supporting,
  contradicting⟩` with `value = pv(L(c))` for positive classes and `NOT_FOUND_IN_CHECKED_SOURCES`, null otherwise.
- Decision: exactly one per claim, `decision_id = H(claim_id, disp(class))`.
- Question: exactly one per claim with `disp = ROUTE_NEEDS_RESOLUTION`, `question_id = H(claim_id, "question", kind)`.
- Invariants: **CL-1** one claim per candidate; **CL-2** one decision per claim; **CL-3** questions exactly for routed
  claims; **CL-4** every supporting evidence id of a claim resolves (EV-1).
- Failure: violation of CL-1 to CL-4 is `fail(VERIFY_FAILED)`.

## 7. Journal, fold and state reconstruction

### 7.1 Records and validity

A record is `j = ⟨v, seq, prev, kind, step, attempt, at, root_id, payload, digest⟩` (SPEC 8.2). The genesis value is
`g = H("citerift-journal-genesis/1", key)`. A journal `J` is **chain-valid** when for all `i`:
`jᵢ.seq = i`, `jᵢ.digest = SHA-256(canon(jᵢ without digest))`, `j₀.prev = g` and `jᵢ.prev = jᵢ₋₁.digest` for
`i > 0` (M-1, M-2). It is **valid** when it is chain-valid and M-3 to M-14 hold.

### 7.2 Fold

- Domain: valid journals.
- Codomain: states `Σ = ⟨λ, stepstate: Steps → StepStates, attempts, deferrals, open attempt, root_id, committed content
  view, open questions⟩`.
- Rule: `fold(J) = foldl(apply, Σ₀, J)` with `Σ₀` = all steps `pending`, `λ = ⊥` (none). `apply` is the transition
  function of section 8 restricted to legal records, so `fold` of a valid journal never meets an illegal record.
- Step state of step `s`: `pending` if no attempt was started or the last attempt ended `step_interrupted`; `running`
  if the last attempt has no terminal record; `succeeded`, `failed_retryable`, `failed_terminal` or `deferred` from the
  last attempt's terminal record. Counters: `φ(s)` = attempts of `s` closed by `step_failed(retryable = true)` or
  `step_interrupted`; `f(s)` = attempts closed by `step_deferred`.
- Lifecycle `λ(Σ)` = `first(` journal invalid other than a torn tail → `CORRUPT`; a `stale_detected` record →
  `STALE`; some step `failed_terminal` → `FAILED`; all steps `succeeded` and an open question → `NEEDS_RESOLUTION`;
  all steps `succeeded` → `COMPLETED`; some step `deferred` → `BLOCKED`; some `step_started` record exists →
  `RUNNING`; `investigation_created` exists → `CREATED` `)`.
- Committed content view: the content records of attempts whose terminal record is `step_succeeded`, in journal order.
- Invariants: **FD-1** `fold` is total on valid journals and depends on nothing but `J` and the blobs it names (W-1);
  **FD-2** the sequence of `λ` values over the prefixes of `J` is a path of the lifecycle table (SPEC 9.4), and each
  step's sequence of states is a path of the step table (SPEC 9.2) (W-2).
- Precedence: as written for `λ`; `STALE` and `FAILED` are mutually exclusive in practice (W-5), the order only makes
  `λ` total.
- Failure: an invalid journal gives `λ = CORRUPT` and no other component is computed.

### 7.3 Content digest `C(J)`

- Domain: valid journals.
- Codomain: `Hex64`.
- Rule: `C(J) = H("citerift-investigation-content/1", key, root_id, ⟨content(j) : j ∈ committed content view of
  layers observation, evidence, claim, decision, question, report⟩)` where `content(j) = ⟨kind, step, payload⟩`
  (no `seq`, `prev`, `attempt`, `at` or `digest`).
- Invariants: **CD-C1** `C` ignores execution records, attempt numbers and times, so a run with retries or
  interruptions has the same `C` as one without them when the committed content is equal (M-13); **CD-C2** `C` is
  recorded by VERIFY (it covers the report, so the report cannot contain it).
- Failure: none on valid journals.

**Proposition P6 (resume equivalence).** Let `J₁` be an uninterrupted run and `J₂` a run of the same request that was
interrupted at any record boundary or inside any write and then resumed, with equal input identities (section 10)
and an equal committed ACQUIRE output. Then `C(J₁) = C(J₂)`.

*Proof sketch.* Uncommitted content is excluded from `C` (M-6). Each committed step output is a function of the
committed outputs it reads and the input identities: VALIDATE, NORMALIZE, DETECT, ASSEMBLE and VERIFY are pure;
EXTRACT is the deterministic Stage 03 engine (its accepted replay property); LOOKUP is a function of keys and the
pinned index (4.5). A torn tail is removed before resuming (SPEC 10.1) and was not committed. Ids are content-derived
(CH-1). By induction over the plan, the committed content views are equal. ∎

The ACQUIRE condition matters for a capture request: if the process dies before ACQUIRE commits, a new capture can
produce different bytes (its `capture.json` records fetch times), hence another root and another `C`. The fault
injection of gate 04-E therefore uses a retained bundle or a deterministic transport and clock for crash points
before the ACQUIRE commit (review finding F-09).

## 8. Workflow transition function

- Domain: pairs `(Σ, j)` of a fold state and a proposed record.
- Codomain: `Σ` or `refuse(rule)`.
- Rule: `legal(j, Σ)` holds for exactly one transition rule below; `apply(Σ, j)` updates `Σ` as the rule says. Any
  other record is refused before it is written (SPEC S-9.1).

| Rule | Record `j` | Requires in `Σ` | Effect |
|---|---|---|---|
| T-CREATE | `investigation_created` | empty journal | `λ = CREATED` |
| T-START | `step_started(s, 1)` | `λ ∈ {CREATED, RUNNING}`; `s` `pending` with no previous attempt; every earlier step `succeeded`; no open attempt | `s` `running` |
| T-RESTART | `step_started(s, a + 1)` | `s` `failed_retryable`, or `s` `deferred` and `j.at ≥ not_before`, or `s` `pending` after `step_interrupted`; no open attempt | `s` `running` |
| T-CONTENT | content record of `s`, attempt `a` | `s` `running` in attempt `a`; layer order (M-10) and references resolve (M-4) | content added, uncommitted |
| T-SUCCEED | `step_succeeded(s, a)` | `s` `running` in `a`; output blobs durable; step checks pass | `s` `succeeded`; content of `a` committed |
| T-FAIL-R | `step_failed(s, a, retryable)` | `s` `running`; code retryable for `s`; `φ(s) + 1 < A_max` | `s` `failed_retryable` |
| T-FAIL-T | `step_failed(s, a, terminal)` | `s` `running`; code not retryable; or a retryable code, or an interruption found on resume, with `φ(s) + 1 = A_max` (`RETRY_BUDGET_EXHAUSTED`); or a Stage 03 deferral with `f(s) = F_max` (`DEFERRAL_BUDGET_EXHAUSTED`) | `s` `failed_terminal`; `λ = FAILED` |
| T-DEFER | `step_deferred(s, a, not_before)` | `s` `running`; Stage 03 returned `deferred`; `f(s) < F_max` | `s` `deferred`; `λ = BLOCKED` |
| T-INTERRUPT | `step_interrupted(s, a)` | first record appended by a resume; `s` `running` in `a`; `φ(s) + 1 < A_max` | `s` `pending`; content of `a` stays uncommitted |
| T-STALE | `stale_detected` | `λ ∈ {RUNNING, BLOCKED}`; a recomputed step key differs (section 10) | `λ = STALE` |

- Invariants: **TR-1** for each `(Σ, j)` at most one rule applies (the requires-columns are disjoint on `kind`, and for
  `step_started` on the attempt number and prior state); **TR-2** no rule leaves `succeeded` or `failed_terminal`;
  **TR-3** no rule applies when `λ` is terminal (W-5); **TR-4** the number of records is bounded: each step has at
  most `A_max` attempts, ACQUIRE of a capture request `A_max + F_max` (Step 4 correction SC-5) (T-FAIL-R,
  T-INTERRUPT and T-DEFER each raise `φ` or `f`, and each is refused at its budget), each attempt has a bounded number of content records (bounded by the units, keys and candidates of one
  extraction), so every investigation reaches a terminal state or stops in `BLOCKED` waiting for `not_before` after
  finitely many records (no infinite retry); **TR-5** no non-terminal state is a dead end: in every reachable
  non-terminal `Σ` some rule applies (in `BLOCKED` for a record whose `at ≥ not_before`; after an interruption through
  T-INTERRUPT or T-FAIL-T).
- Precedence: none needed (TR-1).
- Failure: `refuse(rule)` is a defect, raised and never written.

The lifecycle transitions `RUNNING → COMPLETED` and `RUNNING → NEEDS_RESOLUTION` are the effect of T-SUCCEED on
VERIFY; `CREATED → RUNNING` is the effect of T-START on VALIDATE; `BLOCKED → RUNNING` of T-RESTART on the deferred step.
`CORRUPT` is computed on open and never recorded.

## 9. Completion predicate

- Domain: fold states.
- Codomain: booleans.
- Rule: `complete(Σ) ⟺ ∀s ∈ plan: stepstate(s) = succeeded ∧ the report validates ∧ verification_recorded.result =
  passed ∧ every claim has a complete evidence chain (SPEC S-12.1)`.
- Invariants: **W-7** `λ ∈ {COMPLETED, NEEDS_RESOLUTION} ⇒ complete(Σ)`; the outcome is `partial` exactly in the
  cases of SPEC S-9.7.
- Failure: a VERIFY attempt whose checks fail ends `step_failed(VERIFY_FAILED, terminal)`, so `complete` is false and
  `λ = FAILED`.

## 10. Staleness and replay

### 10.1 Input identity vector and step keys

`id⃗ = ⟨request key, bound root, extraction engine identity, index identity, Stage 04 identity⟩` (SPEC 10.3). Each step
`s` reads a sub-vector `id⃗_s` and the outputs of the steps it depends on. Its key is
`K(s) = H("citerift-step/1", s, π, out(dep(s)), id⃗_s, γ)` (SPEC S-9.3).

### 10.2 Staleness predicate

- Domain: a valid journal and the current environment.
- Codomain: booleans, plus the names of the changed identities.
- Rule: `stale(J, env) ⟺ ∃s committed in J: K_env(s) ≠ K_J(s)`.
- Invariants: **ST-1** stale input is never reused (SPEC S-10.1); **ST-2** a stale investigation keeps every record,
  so the earlier evidence stays readable as history.
- Precedence: a bundle whose bytes do not hash to its recorded digest is `CORRUPT` input (`BUNDLE_DIGEST_MISMATCH`),
  checked before `stale`.
- Failure: an identity that cannot be computed (for example an unreadable index) is a failure with the engine's code
  (for the index, `INDEX_MISSING`, `INDEX_CORRUPT` or `INDEX_FORMAT_MISMATCH`), not `stale` and not "unchanged".

### 10.3 Replay equivalence

- Domain: a valid journal of a `COMPLETED` or `NEEDS_RESOLUTION` investigation and the current environment.
- Codomain: `{reproduced, differs(first record), stale(identities)}`.
- Rule: `replay = first(` `stale(J, env)` → `stale`; recomputed outputs of NORMALIZE, DETECT and ASSEMBLE from the
  committed observation blobs, Stage 03 `verify_bundle` and `replay_bundle` all equal the committed ones →
  `reproduced`; true → `differs` `)`.
- Relation: two journals are **replay-equivalent**, `J ~ J'`, when `C(J) = C(J')`. `replay = reproduced` implies that
  a fresh run with the same inputs yields a journal `~ J` (P6 applied to a run with no interruption).
- Invariants: **RP-1** replay writes nothing; **RP-2** replay never calls `capture_revision` (offline); **RP-3**
  replay reproduces contradictions with equal claim ids (P3 c).
- Failure: an unreadable blob is `CORRUPT`; it is never treated as `differs` or `stale`.

## 11. Why there is no score or threshold

### 11.1 Deterministic rule engine

Stage 04 is a deterministic rule engine: every output is `δ` applied to categorical inputs, and every input is a
recorded fact (a Stage 03 field, a Stage 02 state, projection status, value, issue or reason). No decision compares a
number with a threshold, and none is needed:

1. The inputs are categorical. Stage 02 already reduces several events into a v1 status with explicit reasons, and
   Stage 03 already reports confirmation as categorical states. A score would re-encode these categories as numbers
   and then cut them again with a threshold that nothing has calibrated.
2. The output vocabulary is categorical by contract: v1 epistemic statuses (`verified_fact`, `uncertain`,
   `conflicting`, `unavailable`) and values. A numeric confidence would have to be mapped back to these, adding a free
   parameter without adding information.
3. Uncertainty is carried by abstention with reasons (5.5), not by a probability. A citation is either supported by a
   recorded event of the same work or it is not; when that cannot be established the engine says why.
4. No labelled data exists before the evaluation that could fit a threshold, and fitting one on the evaluation set
   would leak it (RA R4-18).

The operational budgets `A_max = 3` and `F_max = 6` bound work (TR-4); they never change a class. The only numbers in
gate decisions are the pre-registered evaluation bounds (11.2), which test the engine and never feed it.

### 11.2 Evaluation quantities

Under the pre-registration of gate 04-I (plan 12.3; fixed in Step 13, after the freeze):

- Attachment precision per language: `prec = TP / (TP + FP)` over units the engine classifies
  `RETRACTED_WORK_CITED` or `CONCERN_CITED`, where truth is the locked adjudicated label (D-3).
- Interval: Clopper–Pearson 95 % per language; with `x` errors in `n`, the exact upper bound `u` solves
  `P(Bin(n, u) ≤ x) = 0.025` (two-sided) and the one-sided bound uses `0.05`; for `x = 0`, `u = 1 − 0.05^{1/n}`
  (`n = 30` gives `0.0950`; `n = 59` gives `0.0495`).
- Hazard counts (notice, marker or identity-conflict counted as an attachment) and structural counts (any "not
  retracted" value, any claim without a complete evidence chain) must be 0.
- Denominators (positive, negative, identity-conflict) are pre-registered minima at the event level; a short
  denominator after the 200-attempt ceiling means the gate is not passed (D-5).

These are measurements of the engine, not parameters of it.

## 12. Summary of invariant families

| Family | Ids (this document) | SPEC ids |
|---|---|---|
| Root and identity | RT-1 to RT-3, CH-1 | S-4.1 to S-4.9, M-9 |
| Candidates | CD-1, CD-2 | S-6.4 to S-6.6 |
| Evidence | EV-1, EV-2 | S-8.5, S-12.1, M-3, M-4 |
| Detection | P1 to P5, CO-1 to CO-3, AB-1, AB-2, CL-1 to CL-4 | S-7.1 to S-7.5, M-7, M-12, W-8 |
| Journal and fold | FD-1, FD-2, CD-C1, CD-C2, P6 | M-1, M-2, M-5, M-6, M-13, M-14, W-1, W-2 |
| Transitions | TR-1 to TR-4 | S-9.1, W-3 to W-6 |
| Completion | W-7 | S-9.6, S-9.7 |
| Staleness and replay | ST-1, ST-2, RP-1 to RP-3 | S-10.1 to S-10.5, S-16.1 to S-16.3 |
