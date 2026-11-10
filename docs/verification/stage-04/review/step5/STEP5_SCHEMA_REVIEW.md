# Stage 04 Step 5: adversarial review of the investigation schemas

Status: Step 5 record, retained as the owner instructed. Reviewed: `schemas/investigation/v1/` (`common`, `request`,
`journal-record`, `claim`, `report`, schema version 1.0.0) against SPECIFICATION.md, MATHEMATICAL_MODEL.md,
DECISIONS.md D-041 and D-042, and the Step 4 reference model. Tests: `tests/stage04/test_schemas_step5.py`.

The reviewer is the author. That is a limit of this review: an independent review has not been done.

## 1. Schema set

| `$id` | Purpose |
|---|---|
| `urn:citerift:schema:investigation:v1:common` | Shared definitions: hashes, ids, wiki, paths, steps, subject and root, request key, configuration (with the D-042 live-ACQUIRE bound), identity records, the 15 claim classes, rules, dispositions, reasons, keys, work candidates and typed evidence. |
| `urn:citerift:schema:investigation:v1:request` | The investigation request: pinned live capture or retained bundle (S-4.3, SPEC 5.1). |
| `urn:citerift:schema:investigation:v1:journal-record` | One journal line: the envelope of SPEC 8.2 and a payload constrained per kind (SPEC 8.3), with the root-binding, step and retryability rules. |
| `urn:citerift:schema:investigation:v1:claim` | One claim of `dt-1`: class, rule, status, value, reasons, Stage 02 upstream reasons and evidence, with a rule set per class. |
| `urn:citerift:schema:investigation:v1:report` | The Stage 04 report (SPEC 11.1): terminal state, outcome, claims with their decisions, questions and unit anchors, evidence, limitations and the identities needed for replay. |

Accepted upstream definitions are reused by `$ref` and never copied: `contracts:v1:common` (hash, timestamp),
`contracts:v1:investigation` (the v1 `investigation_id`), `wiki:v1:common` (wiki), `wiki:v1:extraction` (extractor
identity, element id), `retraction:v1:common` (snapshot id, code, DOI and PMID keys, policy version) and
`retraction:v1:lookup-result` (schema version, checked sources). `test_accepted_schemas_untouched` checks with git
that `schemas/contracts`, `schemas/wiki` and `schemas/retraction` are unchanged since `fb39ede`.

## 2. Findings

Each finding states what was checked, what was found, and the outcome. "Deferred" means the property cannot be stated
in JSON Schema and is assigned to Investigation Memory or VERIFY (section 3).

### SR-01 Root binding: which record carries the new root

- Question: SPEC 8.2 said "null before the root is bound; afterwards the bound root". It did not say which record
  is the first to carry it, so the `step_succeeded` record of ACQUIRE could validate with either null or the root.
- Outcome: fixed. The ACQUIRE `step_succeeded` record must carry a non-null `root_id` and its payload must hold the
  root object. Every other ACQUIRE record, including a failed, deferred, interrupted or killed attempt, must carry
  null, and so must `investigation_created` and every VALIDATE record. Every record of EXTRACT to VERIFY must carry a
  root. ACQUIRE's bundle observation is written before the bind and carries null. M-9 allows this ("no content record
  of *another* step precedes the bind"). SPEC 8.2 was reworded to state it. This matches F-15 (D-041): only the
  committed ACQUIRE binds. Deferred: equality of `root_id` with `payload.root.root_id` and with `H(type, identity)`,
  and equality across records (M-9).

### SR-02 The report and the lifecycle state

- Question: the owner requires the report to distinguish `COMPLETED` from `NEEDS_RESOLUTION`. SPEC 11.1 said the
  report "holds neither the lifecycle state".
- Outcome: terminology and structure change, recorded. The report has `terminal_state ∈ {COMPLETED,
  NEEDS_RESOLUTION}`: the state the investigation enters if VERIFY passes. It is a function of the fold, since a
  question is open exactly when a claim routes to resolution. A report is exported only after VERIFY passed, so an
  exported report never names a state that was not reached. `FAILED`, `STALE` and `CORRUPT` have no report
  representation, because they export none (S-9.7). The schema enforces both directions. Any question requires
  `NEEDS_RESOLUTION`, outcome `partial` and limitation `OPEN_QUESTIONS`. No question requires `COMPLETED`. Decisions
  and questions are embedded in each claim entry instead of in separate arrays, so a decision cannot be detached from
  its claim. SPEC 11.1 was updated. No lifecycle transition changed.

### SR-03 Unit anchor hash: Stage 03 units carry no `raw_sha256` (decision point for the owner)

- Found: SPEC 4.3 (`unit_ref = H(root_id, "unit", unit.id, unit.source.byte_start, unit.source.byte_end,
  unit.source.raw_sha256)`) and S-12.1 ("the unit id and source anchor (byte span, `raw_sha256`)") read a field that
  the accepted Stage 03 schema does not have. A unit's `source` is a `span` (`wiki:v1:common#/$defs/span`: code-point
  and byte offsets only). Only identifier occurrences have an `anchor` with `raw` and `raw_sha256`.
- Schema now: the report's unit anchor requires `raw_sha256`, described as the SHA-256 of the retained source bytes
  in `[byte_start, byte_end)`. Stage 04 would compute it with the definition Stage 03 uses for identifier anchors.
- Options: (A, recommended) keep that definition. It needs no Stage 03 change, it keeps `unit_ref` and S-12.1 as
  written, and VERIFY can recompute it from the bundle. (B) Drop the per-unit hash and anchor a unit by
  `extraction_digest`, unit id and span. This needs an edit to SPEC 4.3 and S-12.1 and a schema change.
- Not decided here. This changes the meaning of a child identity, so it is a new decision point (owner instruction:
  "Any required semantic change beyond D-042 must be reported as a new decision point"). SPEC 4.3 and S-12.1 were not
  edited.

### SR-04 Retry-After after a failed ACQUIRE attempt (D-042)

- Question: the step machine let `failed_retryable → running` start at once. D-042: "Under no circumstance may the
  new wall-clock bound cause CITERIFT to retry earlier than a Retry-After value it has observed." Its option 2 is that
  Stage 04 preserves `not_before`.
- Outcome: represented. Every ACQUIRE `step_failed` payload must carry `not_before`: a UTC instant or null. It is
  forbidden on other steps. SPEC 9.2 (the `failed_retryable` row) and MM 8 (T-RESTART) now require the new
  attempt's `at ≥ not_before` when one was recorded. This precondition comes directly from D-042. No other state,
  edge or budget changed, and the Step 4 controller model was not edited. Whether Stage 03 can hand over a Retry-After
  observed by a killed child is a Step 8 test (D-042, slow body plus Retry-After). Deferred: the `at ≥ not_before`
  check is a cross-record comparison, made by the append guard.

### SR-05 `ACQUIRE_WALL_CLOCK_EXCEEDED`: form fixed, retryability open

- The code is accepted only on ACQUIRE. It is valid both with `retryable = true` (it is in the ACQUIRE retryable set)
  and with `retryable = false`, so the schema does not fix its retryability (owner: "without fixing its retryability
  at schema level").
- `wall_clock = {t_acq_ms, elapsed_ms}` is required exactly for this code and must be null for every other code.
- The record carries `root_id = null`, because a non-success ACQUIRE record cannot carry a root. A killed attempt
  therefore cannot bind the root through this record.
- Deferred to Memory: that a killed attempt leaves no `step_succeeded` record and that its content is never
  committed (M-6, M-14). This includes a bundle observation written before the kill. Also deferred: `elapsed_ms ≥
  t_acq_ms`, and that `t_acq_ms` equals the bound in the configuration.

### SR-06 Live bound and configuration identity (D-042)

- The configuration has these parts: plan version; budgets (`a_max = 3`, `f_max = 6`, fixed by `plan-1`); the Stage 03
  fetch policy digest; and `live_acquire_bound = {deadline_ms, op_timeout_ms, safety_allowance_ms = 30000, t_acq_ms}`.
- For a live capture both the fetch policy digest and the bound are required. For a retained bundle both are null.
  The pairing is a `oneOf` of null against non-null, so exactly one branch can match.
- The configuration and its digest are recorded in `investigation_created` and in the report's `identities`, and
  `config` is a name that `stale_detected` can report. SPEC S-4.7 and MM 3.2 now define `config_digest` over this
  object, so a different bound gives a different investigation key and step keys, and is never silently applied to a
  historical investigation.
- Deferred: `t_acq_ms = deadline_ms + op_timeout_ms + safety_allowance_ms`, because JSON Schema has no arithmetic.
  That check belongs to the configuration builder and VERIFY. Milliseconds are used so every value is an integer
  (MM 2.1: no floats).

### SR-07 Request key: no added discriminator

- The first draft added a `kind` field to `request_key`. That would have changed the hashed input of
  `investigation_key` relative to S-4.7, which defines `request_key` as `{wiki, revision_id}` or `{capture_sha256}`.
- Outcome: removed. The two forms have disjoint required fields and `additionalProperties: false`, so the `oneOf` is
  unambiguous without a discriminator.
- A key with both forms, part of a form, a title, or a form that does not match the request mode is rejected
  (`test_request_key_has_exactly_the_specified_form`).

### SR-08 Outcome rule as an equivalence

- S-9.7 is an "exactly when" rule. The first draft enforced only one direction: a cause required `partial`. So
  `outcome = partial` with no cause validated, and so did the limitations `OPEN_QUESTIONS`,
  `LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES` or `EXTRACTION_PARTIAL` with no matching condition. Tests found this.
- Outcome: fixed. `partial` now requires at least one cause, and each of those limitations requires its condition.

### SR-09 Title and page id cannot identify anything

- A request has no `title` or `page_id` field in either form. A title-only, page-id-only or title-beside-revision
  request is rejected (S-4.3).
- In the root, the title lives only in `display`, which is outside `identity`. `page_id` is part of the root
  identity, as S-4.1 requires, but it never addresses a request.

### SR-10 Simulation placeholders not promoted

- None of the four Step 4 placeholders is a value of a production enumeration.
- The mapping and the new reason names are in `STEP5_PLACEHOLDER_MAPPING.md`. `STATUS_NOT_ESTABLISHED`,
  `LOOKUP_QUERY_FAILED`, and the D-7 and D-16 reason names are terminology choices for owner review.
- Stage 02 basis reasons are kept in `upstream_reasons` with the lookup evidence that carries them, never as Stage 04
  reasons, and the set stays open to Stage 02's policy versions.

### SR-11 Accidental global negatives

- Checked: every enumeration, every free-text field, and every place where a value could mean "not retracted",
  "clean", "safe" or "no retracted citations".
- Outcome: none is representable.
  - There is no such class, claim value, status, disposition or limitation (`test_no_global_negative_is_representable`
    tries each spelling).
  - The report has no summary text field.
  - `limitations` is a closed enumeration that must contain `CHECKED_SOURCES_ONLY`.
  - The only absence value, `not_found_in_checked_sources`, is tied to D-16, status `uncertain`, and a non-empty list
    of checked sources in the report entry (NOT_FOUND requires source and index identity: the report's `identities`
    also carry the index snapshot and digest).
  - The article summary counts claims by class and lists positive works only.
- Residual: two free-text fields remain: `step_failed.detail` (at most 4,096 characters) and an observation's
  `source_ref.locator`. They are operational and never enter the report. Their wording is a Step 6 implementation
  concern (RA R4-07).

### SR-12 Numbers: integers and the `1.0` token

- Every number is declared `integer` with bounds. No `number` type is used. NaN and infinity have no JSON token, and
  the strict reader of MM 2.1 rejects the non-standard ones.
- Draft 2020-12 counts `1.0` as an integer, so no schema can tell `1.0` from `1`. A record with `"seq": 1.0` validates
  (the test records this).
- Deferred to Investigation Memory. MM 2.1 states that Stage 04's own record fields hold integers, never floats. A
  digest check alone would not catch a `1.0` token, because `canon` of the float `1.0` is `1.0` and the digest would
  agree, so Memory's strict reader must refuse float tokens in journal records (`CANON_INVALID`). This is a Step 6
  implementation requirement.

### SR-13 Ambiguous unions

- Every `oneOf` in the five schemas was listed by a script. Each one is either null against a non-null type, or two
  objects with disjoint required fields and no additional properties, so at most one branch can match any instance.
- Class-specific rules use `if`/`then` on a `const` discriminator (`class`, `rule`, `kind`, `step`, `mode`,
  `obs_kind`), not `oneOf`.
- Validation is deterministic. Format checks use the project's `FORMAT_CHECKER`, and patterns use `$(?!\n)` so a
  trailing newline is refused.

### SR-14 Over-permissive payloads

- The envelope's `payload` is constrained per kind by a `$ref`, and every payload object has
  `additionalProperties: false`. A payload of another kind is rejected (`test_payload_must_match_kind`).
- Content kinds are tied to their step: observations to ACQUIRE, EXTRACT and LOOKUP with a matching `obs_kind`;
  evidence to NORMALIZE and DETECT; claims, decisions and questions to DETECT; reports to ASSEMBLE; verification to
  VERIFY.
- Failure codes are restricted per step. Only ACQUIRE and EXTRACT may be retryable, with their SPEC 9.3 sets. ACQUIRE
  also passes through other Stage 03 terminal codes (SPEC 9.3, "other Stage 03 codes"), which is deliberately open.
- Evidence values are typed per evidence kind. An identifier occurrence's key is null exactly when it is `MALFORMED`.

### SR-15 Valid states that cannot validate

- `test_every_valid_reference_decision_is_a_valid_claim` runs the frozen Step 4 reference model on its whole valid
  domain: 244,884 cases, giving 225 distinct decision signatures and covering all 15 classes. It maps each decision
  through the placeholder table only and validates it as a claim. No decision is rejected.
- A valid claim per class and a valid report containing each class also validate. Valid live and bundle requests,
  and one valid record of each of the 16 journal kinds (`test_one_valid_record_of_every_kind`), validate too.

### SR-16 Forward compatibility against fail-closed

- `schema_version` is the constant `1.0.0`, the journal `v` is the constant `1`, `subject_type` is a closed enumeration
  (`wikipedia_article_revision`), `table_version` is `dt-1` and `plan_version` is `plan-1`. Every object rejects
  unknown fields.
- An unknown version, subject type, field or code therefore fails. This is tested for request, report and journal.
- The cost is that any extension needs a new schema version, and S-4.5 and S-8.7 already require that. No `x-`
  extension slot or open object was left, because such a slot would let unreviewed content through.

### SR-17 Coupling to Stages 05 to 07

- No field names a later stage's concept: no DOI or PMID subject, no history, no cross-language comparison, no
  cancellation, no user field.
- The subject type is closed in v1. A later stage adds a type through a new schema version, as S-4.5 says. Nothing
  in Stage 04 depends on Stage 05 to 07 schemas.

### SR-18 Schema against model

- The 15 classes, rules D-1 to D-4 and D-6 to D-16, dispositions and questions follow SPEC 7.2, 7.3, 7.6 and 7.7.
  Disposition and question kind are enforced per class in the report entry.
- The schema adds fields that SPEC 8.3 described in words: claim `candidate`, `table_version` and `upstream_reasons`;
  evidence `value`; `investigation_created` `investigation_id` and `migrated_from`; verification `content_digest`.
  SPEC 8.3 now points to the schema.
- In the journal, a `decision_recorded` record does not carry the claim's class. Its disposition is checked against
  the class only in the report. Deferred to Memory (M-7): the journal check of disposition against class.
- dt-1 itself is unchanged. The reason names added to SPEC 7.3 change no class, guard or tier, and the Step 3
  consistency check passes.

### SR-19 Coverage of the schemas in CI

- The CI step `check-schemas` meta-validates `schemas/contracts` only, as for the Stage 02 and 03 schemas.
- The investigation schemas are meta-validated and fully exercised by `tests/stage04/test_schemas_step5.py`, which CI
  runs. `python -m citerift.contracts.validate --schemas schemas/investigation check-schemas` also reports
  `5 schemas checked, 0 problems`.
- `.github/` was not changed.

## 3. Invariants deferred to Investigation Memory, the controller or VERIFY

JSON Schema validates one document at a time, with no arithmetic and no value equality across fields. The following
are therefore not schema properties; each is assigned to the component that checks it.

| Property | Owner |
|---|---|
| M-1 `seq` without gaps, `at` non-decreasing | Memory, on open and on append |
| M-2 `prev` chain and record `digest` | Memory |
| float tokens such as `1.0` refused in journal records (SR-12, MM 2.1) | Memory strict reader |
| M-3 blob exists, hashes to its name, written before its record | Memory |
| M-4 every referenced id defined by an earlier committed record | Memory |
| M-5 succeeded step has its output blobs | Memory |
| M-6 content of an attempt counts only with its `step_succeeded`; a killed ACQUIRE attempt commits nothing (SR-05) | Memory fold |
| M-7 claim to evidence and decision to claim resolution; disposition against class in the journal (SR-18); two alternatives with evidence | Memory, VERIFY |
| M-8 supersession reachability and new evidence | Memory |
| M-9 equality of `root_id` across records and with the root's hash (SR-01) | Memory |
| M-10 references point only downward across records | Memory |
| M-11 single writer (lock) | Memory |
| M-13 determinism of `C(J)` | VERIFY, replay |
| M-14 at most one `step_succeeded` per step | Memory, append guard |
| W-1 to W-8 and T-* transition legality, including `at ≥ not_before` after a failed or deferred ACQUIRE (SR-04) | controller append guard (MM 8) |
| derivation of `root_id`, `investigation_key`, `investigation_id`, `config_digest`, step keys and child ids (SPEC 4.3) | Memory, VERIFY |
| `t_acq_ms` sum and its equality with the configuration; `elapsed_ms ≥ t_acq_ms` (SR-05, SR-06) | configuration builder, VERIFY |
| `request_key` equal to the request's own fields | Memory at creation, VERIFY |
| report identities equal to the journal's recorded identities; report root equal to the bound root | ASSEMBLE, VERIFY |
| claim rule guards on actual lookup content (which lookup decided, EV-1, EV-2) | DETECT, VERIFY |

## 4. What this review does not cover

- No production code exists, so the schemas have not been exercised by an implementation. Step 6 and later steps may
  find fields that need a new schema version.
- SR-03 is open for the owner.
- The Retry-After hand-over (SR-04) and the kill and reap behaviour (SR-05) are Step 8 tests.
