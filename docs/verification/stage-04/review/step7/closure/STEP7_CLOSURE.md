# Stage 04 Step 7 corrective closure (D-047 to D-052)

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3` (2026-11-11T07:04:33Z). Step 7 is
accepted at `ab0ce66edafab7a7720649892386aa58795b9b91`. This closure changes only what that message orders; Step 8
is not started. Decision records: DECISIONS.md D-047 to D-052. Stage 02 change: maintenance transaction A-02-001
(`docs/verification/maintenance/A-02-001/MAINTENANCE_RECORD.md`).

Labels: **[verified]** means measured or tested here, with the file named. **[inference]** means derived, not
measured. **[condition]** is a requirement on later steps.

## 1. D-047 (RB-1): collections leave the record

### Fail-first [verified, `fail_first_before.log`, run at `ab0ce66`]

| Case at `ab0ce66` | Result |
|---|---|
| claim with 16,000 supporting ids | DETECT `STORAGE_ERROR` / `RECORD_TOO_LARGE`, 1,072,796 bytes |
| claim with 50,000 supporting ids | DETECT `STORAGE_ERROR` / `RECORD_TOO_LARGE`, 3,350,796 bytes |
| report with 50,000 projections | ASSEMBLE `STORAGE_ERROR` / `RECORD_TOO_LARGE`, 3,350,437 bytes |

### Architecture

`MAX_RECORD_BYTES` is unchanged (1 MiB). The journal stays an audit and commit log. Two collections that grow with
the article become content-addressed blobs (`src/citerift/investigation/sets.py`), stored with the existing blob
store (`put_blob`, `blob_read`). No database layer was added.

- **Evidence set** (`urn:citerift:schema:investigation:v1:evidence-set`, 1.0.0):
  `{schema, schema_version, supporting[], contradicting[], alternatives[][]}`. Each list is sorted ascending, holds
  unique evidence ids and is never truncated. `alternatives[i]` belongs to the claim's `alternatives[i]`. A duplicate
  id within a list is refused when the set is built (`ValueError`), never merged silently.
- **Claim record** (`claim.schema.json` 2.0.0) keeps `evidence_set` (the set's digest), `supporting_count`,
  `contradicting_count` and per alternative `supporting_count`. It holds **no inline copy** of the ids.
  `upstream_reasons` (at most 192 = 3 lookups × 64 codes) must cite ids in the set.
- **Projection set** (`urn:citerift:schema:investigation:v1:projection-set`, 1.0.0):
  `{schema, schema_version, projections[]}`, sorted, unique. `report_recorded` now carries `report`,
  `projection_set` (digest) and `projection_count` instead of the `projections` list.

**Claim-id semantics (changed).** Before: `claim_id = H(cand_ref, class, rule, table_version, sorted(set(evidence)))`,
a flat union that did not distinguish supporting, contradicting and alternative evidence. Now:
`claim_id = H(cand_ref, class, rule, table_version, evidence_set_digest)` (`ids.claim_id`). The digest covers the
canonical set, so the claim id binds the exact supporting, contradicting and per-alternative lists. The same ids in
another role give another claim id. Replay gives the same id, because the set has exactly one canonical form.

**Enforcement (Memory, on every append and on every open)** [verified, `fold.py`]:

- the set blob must exist and be intact (M-3; a missing blob is `BLOB_MISSING`, never an empty set);
- it must validate against its schema and be in canonical order (`EVIDENCE_SET_INVALID`, `PROJECTION_SET_INVALID`);
- the counts must equal the list lengths, and the upstream reasons must cite ids in the set;
- every id the set names must resolve to evidence committed earlier or written earlier in the same attempt (M-7);
- every projection digest in a projection set must be an existing blob (M-3).

When the controller writes, a refused set ends the attempt as `ADAPTER_INCONSISTENT` (D-049). When a set is damaged
after commit, opening the investigation gives `CORRUPT`. The VERIFY replay opens Memory, so it runs the same checks.
**[condition]** The Step 8+ VERIFY adapter must list this resolution among its checks.

### Payload review (every record kind of `journal-record.schema.json` 2.0.0)

| Collection | Before | After |
|---|---|---|
| `claim_recorded` evidence lists | unbounded | evidence-set blob |
| `report_recorded.projections` | unbounded | projection-set blob + count |
| `claim.upstream_reasons` | unbounded | `maxItems` 192 |
| `question_closed.evidence`, `claim_superseded.new_evidence` | unbounded | `maxItems` 64 (a resolution names a few ids) |
| `verification_recorded.checks` | unbounded | `maxItems` 64 (one check per kind, SPEC 9.7, about 30 kinds) |
| `step_succeeded.outputs` | unbounded | `maxItems` 16 |
| `stale_detected.changed`, `claim.reasons` | `uniqueItems` over enums of 6 and 20 values | unchanged, bounded |

## 2. D-048 (RB-2): the lookup budget is enforced before Stage 02 materializes

### Fail-first [verified]

- `fail_first_before.log`: the accepted `Index.gather()` returned all 200 or 2,000 events of one key (traced peaks
  1.06 MB and 10.4 MB) before any cap could apply. A cap applied after it bounds nothing.
- `docs/verification/maintenance/A-02-001/fail_first.log`: the new Stage 02 tests against the accepted code at
  `cf06083`. Collection fails: `EvidenceBudgetExceeded` does not exist.

### Stage 02 facility (A-02-001)

These are additions to `src/citerift/retraction/query.py`; no existing line changed.

- `Index.gather_bounded(doi, pmid, *, budget_bytes, supersessions=())`. It sets a per-call `_Budget` and calls the
  **unchanged** `gather()`.
- Five guards (`if self._budget is not None:`) charge each row before it is read into Python. They sit in `_events`,
  `crossref_relations` and `crossref_sources`, which use the SQL length of the stored fields, and at the two
  relevance-hit sites, which use the canonical bytes of the hit before it is appended.
- Once the charge exceeds the budget, `EvidenceBudgetExceeded(budget, needed)` is raised and nothing is returned. A
  result is never truncated.
- A non-int, bool or negative budget is `BUDGET_INVALID`. A nested call is `BUDGET_ACTIVE`.

How `gather()` is shown unchanged [verified, `tests/stage02/test_rde_gather_bounded.py`]:

- the module with the maintenance additions removed (by AST) unparses to the same SHA-256 as the accepted module, on
  3.12 and on 3.13;
- no budget is set outside `gather_bounded`;
- within budget, the bounded result equals `gather()` on every policy and tension case.

Further tests in that file:

- N−1, N and N+1;
- k events against k+1;
- at 2,000 events, the rows materialized stay within the budget at the fractions 0, 0.25, 0.5, 0.75 and 0.999;
- relevance hits are charged.

### Stage 04 use

`src/citerift/investigation/lookup.py`:

- `bounded_gather` returns `gather()`'s result, or, over budget, an `unavailable` lookup with no events, no projection
  value and the issue `LOOKUP_EVIDENCE_LIMIT_EXCEEDED`;
- the issue carries `budget_bytes` and `needed_at_least_bytes`;
- the result is all-or-nothing, and under dt-1 the candidate is decided `LOOKUP_UNAVAILABLE` (D-13) [verified,
  `test_d048_*`];
- such a claim carries the reason `LOOKUP_EVIDENCE_LIMIT_EXCEEDED` besides `LOOKUP_QUERY_FAILED` (SPEC S-6.10a). The
  latter stays required by the Step 5 placeholder mapping. The new reason code (common 2.0.0) is allowed with class
  `LOOKUP_UNAVAILABLE` only [verified,
  `test_schemas_step5.py::test_d048_lookup_evidence_limit_reason_belongs_to_lookup_unavailable_only`]. Which claims
  carry it is decided by the Step 8 DETECT adapter, from the lookup observation's issue.

The bound is `config.lookup_evidence_budget_bytes`:

- it is required, an integer from 1 to 16,777,216 (`common.schema.json`);
- it is part of `config_digest`, so changing it changes the investigation key [verified,
  `test_d048_budget_is_configuration_and_changes_config_digest`].

### Bound derivation [verified, `lookup_budget.py` → `lookup_budget.json`]

`N` is the stored bytes a lookup charges. `O` is the canonical observation size. **[condition]** The Step 8
observation is the canonical gathered `Evidence` without its derived `evidence_set`, plus the projection.

`O` was measured on eight shapes × three text types at 50 and 200 events. The shapes are DOI match, PMID match,
notice-only, ambiguous pair, PMID role collision, two maximal-length-DOI shapes and a no-record lookup with relevance
hits. The three text types
are empty, all-escaped and maximal-length escaped DOIs. On every shape `O` is affine in `N`.

| Quantity | Value |
|---|---:|
| `rho_max = max dO/dN` (notice-only, escaped long DOI) | 5.7792 |
| `rho_bound` (6 bytes is the largest canonical expansion of one stored byte; ≥ `rho_max`) | 6.0 |
| `F_max` (largest intercept) | 1,647,790 bytes |
| `B_max = (MAX_BLOB_BYTES − F_max) / rho_bound` | 44,464,611 bytes (42.4 MiB) |
| **Selected default `B`** | **16,777,216 bytes (16 MiB)** |
| Worst observation at `B` (`rho_bound·B + F_max`) | 102,311,086 bytes; blob margin 2.62× |
| Query memory at `B`: `gather` peak (7.597 B per needed byte) | 127,456,510 bytes |
| Query memory at `B`: encode peak (11.56 B per needed byte) | 193,944,617 bytes |
| Pinned index `rw-2f116e9ffed718e6`: 207,247 lookups in 41.8 s | largest `N` = 656,378 bytes (281 events) |
| Headroom of `B` over the pinned maximum | 25.56× |
| A synthetic lookup of 16,966 rows (`N` = 16,941,574 bytes) | over `B`: refused; its observation would be 20.6 MB |

16 MiB is chosen below `B_max` so that the query's own Python memory stays under 200 MB on the 15 GiB container while
the blob keeps a margin of 2.6×. The pinned index is a sanity check only: its largest lookup uses 3.9 % of `B`.

**N−1 / N / N+1** [verified]:

- `test_below_at_and_one_over_the_bound`, with `pmid` None and `"123456"`: `B = N` and `B = N + 1` equal `gather()`;
  `B = N − 1` raises;
- `test_d048_over_the_budget_the_lookup_is_unavailable_whole`: the same at the Stage 04 boundary.

## 3. Storage limits after the closure [verified, `storage_bounds.py` → `storage_bounds.json`]

`storage_bounds.py` extends the Step 7 `../resource_bounds.py`. The original builds format-1 records, does not run on
format 2, and is kept unchanged as evidence. Each record kind is built at its schema maximum, validated against the
format-2 schema, and measured.

### Before / after

| Item | Before (`ab0ce66`, `STEP7_RESOURCE_BOUNDS.md`) | After the closure |
|---|---|---|
| claim record | ≥ 3,350,335 B at the Stage 03 caps (3.2× the record limit); 137 MB with events | ≤ 42,565 B valid maximum; ids in an evidence set ≤ 34.17 MB |
| report record | 3,350,000 B of projection ids (3.2×) | 555 B; projection set ≤ 4.69 MB |
| largest record of any kind | over the limit (claim, report) | 50,297 B (`investigation_created`, 4.8 %) |
| events read by one lookup | up to `ROW_LIMIT` = 2,000,000, all materialized | ≤ 16 MiB of stored row bytes, checked before each row |
| lookup observation blob | not bounded below the blob limit | ≤ 102.3 MB |
| query memory, one lookup | unbounded (10.4 MB already at 2,000 events) | ≤ 194 MB peak |
| journal, one committed run, typical | ≥ 374 MB (3 runs, without events) | 478 MB (720,001 records) |
| journal, `A_max` = 3 runs | 3.76 GB with one key at `ROW_LIMIT` | 1.43 GB typical, 58.3 GB at every field maximum |
| journal reader | not measured | 6.58 B of memory per journal byte; 5.11 ms per record to open |

### Status of the three limits

| Limit | Status |
|---|---|
| **Record, 1 MiB** | **PROVEN SUFFICIENT.** Every record kind at its schema maximum is ≤ 50,297 B. A further sum-of-field-maxima claim bound is 48,922 B. |
| **Blob, 256 MiB** | **PROVEN SUFFICIENT** for every blob Step 7 writes, with two Step 8 conditions: the Stage 03 extraction is stored byte for byte (Stage 03 caps it at exactly 256 MiB), and the bundle observation records artifacts by digest. Also proven: the lookup observation (≤ 102 MB, D-048), the evidence set (≤ 34.2 MB) and the projection set (≤ 4.7 MB). **NOT PROVEN for the ASSEMBLE report** of SPEC 11.1, which carries `claims[]` and `evidence[]` inline: about 510,000 evidence items, 204 MB typical, 13.1 GB at every field maximum. **Owner decision OD-R** (section 7). |
| **Journal, 512 MiB** | **NOT PROVEN.** One committed run at the Stage 03 caps is 478 MB typical. Three attempts are 1.43 GB typical and 58 GB maximal (2.7× and 108× the limit). Raising the limit is rejected: opening a 512 MiB journal already needs about 3.5 GB of Python memory and about 79 min (4,718 s, estimated from the measured per-record cost). **Owner decision OD-J** (section 7). |

No limit constant was changed. Every refusal stays fail-closed: `STORAGE_ERROR` with `RECORD_TOO_LARGE`,
`JOURNAL_TOO_LARGE` or `BLOB_TOO_LARGE` as the reason, tested since Step 7.

## 4. D-049 (IA-11): `ADAPTER_INCONSISTENT` in every step

Fail-first [verified, `fail_first_before.log`]: at `ab0ce66`, an adapter raising in VALIDATE, EXTRACT or LOOKUP left
the attempt open (`AdapterDefect`) three times, and the step ended as `RETRY_BUDGET_EXHAUSTED` / `STEP_INTERRUPTED`.

Implementation:

- `ADAPTER_INCONSISTENT` is a terminal, non-retryable code of every step in the record schema;
- `controller.DEFECT_CODE` maps every step to it, and `AdapterDefect` is removed;
- these all end the attempt at once with `step_failed` / `ADAPTER_INCONSISTENT` / `retryable: false`:
  - an ordinary exception;
  - a wrong result type;
  - content the guard or Memory refuses;
  - a protocol violation;
  - an engine or controller code used as a failure code;
  - evidence attached by a step other than EXTRACT;
- domain failures keep their own codes: `NORMALIZE_INVALID`, `REPORT_INVALID`, `VERIFY_FAILED` and the others are
  now only the adapter's domain failures;
- size limits keep `STORAGE_ERROR`;
- only a process death or a `BaseException` leaves an attempt open for W-6.

**Finding found during the closure (fixed):** ACQUIRE accepted any string as a failure code. Evidence:
`fail_first_acquire_code.py` / `.log`, where `NOT_A_CODE_OF_ANY_STEP` and `STEP_INTERRUPTED` were recorded as
terminal codes. ACQUIRE now accepts a Stage 03 issue code (`citerift.wiki.issues.CATALOG`) or one of its five Stage 04
codes. Anything else is `ADAPTER_INCONSISTENT`.

Tests:

- `test_d049_defect_is_terminal_in_every_step`: 5 defect kinds × 8 steps;
- `test_d049_domain_failures_keep_their_codes`: 8 steps;
- `test_controller_adversarial.py::test_adapter_exception_fails_closed`: every step;
- `test_base_exception_in_an_adapter_leaves_the_attempt_open`.

## 5. D-050 (IA-4): failed Stage 03 documents

`src/citerift/investigation/extraction.py::extraction_failure` maps a failed document as follows:

- `EXTRACTION_DEADLINE_EXCEEDED`, `EXTRACTION_MEMORY_EXCEEDED` or `EXTRACTION_WORKER_FAILED` in a failed worker
  component, carried by an issue, keeps its code. It is retryable under SPEC 9.3: three attempts, then
  `RETRY_BUDGET_EXHAUSTED` with the code as reason.
- Any other valid Stage 03 code becomes `EXTRACTION_FAILED`, non-retryable, with the Stage 03 code as the reason.
- Anything else becomes `ADAPTER_INCONSISTENT`. That covers:
  - a schema-invalid document;
  - no determinable code;
  - a code Stage 03 does not define;
  - a worker code outside a failed worker component;
  - a worker code that no issue carries.

The failed document is kept as an `extraction` observation of the failing attempt (`_keep_failed_document`). If it
cannot be stored, the failure is still recorded and its detail says why.

Families tested:

- the three worker codes, each run end to end, with the kept blob equal to the document;
- `BUNDLE_MALFORMED`, `PLATFORM_UNSUPPORTED` and `BUNDLE_DIGEST_MISMATCH`;
- real Stage 03 extractions failing with `LIMIT_NODES`, `LIMIT_DEPTH`, `LIMIT_OCCURRENCES` and `SOURCE_PARSE_LOSSY`;
- a capture with no supported source;
- an accounting failure;
- seven malformed or contradictory documents, which give `ADAPTER_INCONSISTENT`.

## 6. D-051 (IA-6): evidence id binds the kind

`evidence_id = H(EVIDENCE_TAG, observation, pointer, kind)` (`ids.evidence_id`). SPEC 4.3, MM 4.6/5/6, the
workflow's evidence check (CH-1), the schema descriptions and every fixture were updated.

Fail-first [verified, `fail_first_before.log`]: two kinds at one pointer had the same id, and the second was refused
as `DUPLICATE_ID` (NORMALIZE `NORMALIZE_INVALID`).

Tests:

- two kinds at one pointer coexist;
- the same kind repeated is refused;
- the id is deterministic and binds each part.

The Step 4 oracle does not encode the derivation. Its manifest digest is unchanged (`411050772807cfbc…3e27735`,
`test_simulation_step4.py`). No released records exist, so there is no migration.

## 7. Owner decisions returned (not implemented)

**OD-J: the journal.** The journal grows with one record per evidence item: about 510,000 evidence records per run
at the Stage 03 caps.

- **Recommended: evidence batches.** NORMALIZE, LOOKUP and DETECT write evidence in content-addressed blobs of a
  fixed maximum count (for example 4,096 items), chunked deterministically in sorted-id order. Each blob gets one
  `evidence_batch_recorded` record carrying its digest, count and first and last id. At the caps this is about 125
  records per run instead of 510,000, and the journal stays compact by design. The cost is a change to the Step 5
  record schema, to the fold's evidence index (ids resolve through batch manifests) and to CH-1.
- **Alternative: an explicit configured article-size cap**, recorded in `config_digest`, with a refusal code at
  EXTRACT. It is honest, but it rejects articles that Stage 03 accepts.
- **Not recommended:** raising `MAX_JOURNAL_BYTES` (reader memory, section 3).

**OD-R: the report.** Following the owner's chunking rule, the recommendation is a report manifest:

- the report keeps its fixed fields and the claim and evidence counts;
- `claims[]` and `evidence[]` move into deterministic chunks, sorted by id with a fixed maximum per chunk, each a blob;
- the report names the chunks by digest, in order.

This changes the Step 5 report schema and SPEC 11.1.

Under the owner's instruction, real Stage 02/03 integration (Step 8) should not start while OD-J and OD-R are open.

## 8. Step 8 design conditions [condition]

1. The LOOKUP observation is the representation used in section 2. Any other representation re-runs `lookup_budget.py`.
2. `lookup_event` evidence exists only for the events a claim cites as witnesses, at most 4 per claim (assumed by the
   journal model).
3. VERIFY records one check per kind (≤ 64; the schema enforces this) and reports evidence-set resolution.
4. EXTRACT stores the Stage 03 document byte for byte. ACQUIRE records artifacts by digest.
5. A step has at most 16 outputs (the schema enforces this).

## 9. Schema versions

| Schema | Before | After |
|---|---|---|
| `claim`, `common`, `journal-record`, `report`, `request` (investigation v1) | 1.0.0 | 2.0.0 |
| journal record field `v` (`JOURNAL_FORMAT`) | 1 | 2; a format-1 journal opens as `CORRUPT` / `JOURNAL_VERSION_UNSUPPORTED` (tested), no migration |
| `evidence-set`, `projection-set` | absent | 1.0.0 |
| Stage 00 (`schemas/governance`), contracts (`schemas/contracts`), Stage 02 (`schemas/retraction`), Stage 03 | unchanged | unchanged |

## 10. Inherited findings

| Id | Finding | Disposition |
|---|---|---|
| IF-1 | Appending costs about 3.5 ms per record and opening about 5.1 ms per record, dominated by jsonschema. The fold validates each record twice (check and apply). At 720,001 records per run this is about 42 min to write and 61 min to open [inference from the measured rates]. | Performance only. OD-J removes most of it; otherwise a later step should validate once. |
| IF-2 | The accepted Stage 02 `gather()` did not bound relevance hits by size. | Unchanged in `gather()`; charged in `gather_bounded`. |
| IF-3 | `../resource_bounds.py` (Step 7) does not run on format 2. | Kept as evidence; replaced by `storage_bounds.py`. |
| IF-4 | ACQUIRE accepted any failure code (section 4). | Fixed under D-049. |
| IF-5 | Stage 03 `normalize_doi` accepts `"` and `\`, and Stage 02 keeps control characters in text. Both expand in canonical JSON. | Accounted for in `rho`; not a defect. |
| IF-6 | Pinned index sanity data: 3 invalid identifiers, 0 quarantine rows, empty Crossref tables. | Sanity check only; no conclusion rests on it. |

## 11. Tests added or changed

- **New `tests/stage04/test_step7_closure.py`:** D-047, D-048, D-049, D-050 and D-051, including a 50,000-id claim
  that commits and replays.
- **New `tests/stage02/test_rde_gather_bounded.py`** (A-02-001).
- **Updated** for the new identities, the format and D-049: `test_controller_adversarial.py`,
  `test_controller_differential.py`, `test_controller_guard.py`, `test_controller_resolution_stale.py`,
  `test_memory_journal.py`, `test_schemas_step5.py`, `controller_support.py` and `memory_support.py`.

D-052 (TA-1) is a design only, recorded in `STEP7_D052_CHECKPOINT_DESIGN.md`.
