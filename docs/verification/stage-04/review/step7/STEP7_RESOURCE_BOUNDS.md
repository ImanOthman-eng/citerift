# Stage 04 Step 7: resource-bound derivation (owner Step 7 item 17)

> **Closure note (2026-11-11).** This is the Step 7 derivation at `ab0ce66`, kept as written. Its owner decisions RB-1
> and RB-2 became D-047 and D-048. The re-derivation after them, and the current status of the three limits, are in
> `closure/STEP7_CLOSURE.md` section 3 (`closure/storage_bounds.py`).

Script: `resource_bounds.py` (this folder). Output: `resource_bounds.json`. Every number below is printed by that
script; the upstream caps are imported from the accepted Stage 02 and Stage 03 code, not copied by hand, and every
maximal record is validated against `urn:citerift:schema:investigation:v1:journal-record` before it is measured.

Limits under review (Step 6 Memory, unchanged): `MAX_RECORD_BYTES` = 1,048,576, `MAX_JOURNAL_BYTES` = 536,870,912,
`MAX_BLOB_BYTES` = 268,435,456.

## 1. Inputs

| Source | Constant | Value |
|---|---|---|
| Stage 03 `ExtractConfig` | `max_refs` | 20,000 |
| Stage 03 `ExtractConfig` | `max_candidates` | 50,000 |
| Stage 03 `extract.MAX_OUTPUT_BYTES` / `verify.MAX_EXTRACTION_BYTES` | extraction document, canonical bytes | 268,435,456 |
| Stage 02 `source.ROW_LIMIT` | rows in the pinned index | 2,000,000 |
| Stage 02 `source.FIELD_LIMIT` | bytes per field | 1,048,576 |
| Controller | `A_max`, `F_max` | 3, 6 |
| Controller | attempts, retained / live | 24 / 30 (7 × 3 + ACQUIRE 3 + 6 deferrals) |

One more digest in a canonical list costs 67 bytes (`"` + 64 hex + `"` + `,`). The smallest content record (an
`evidence_recorded` record at seq 1, empty pointer, no refs, null value) is **565 bytes**, measured.

### Count bounds of one run

Stage 03 counts every identifier occurrence that is not excluded against `max_candidates`, whatever its role
(`wiki/source.py`, `Scanner._add`). It counts units against `max_refs`.

| Quantity | Bound | Value |
|---|---|---:|
| Units | `max_refs` | 20,000 |
| Identifier occurrences (all roles) | `max_candidates` | 50,000 |
| Identifiers per unit | no per-unit cap, so the document cap applies | 50,000 |
| Distinct keys | at most one per occurrence | 50,000 |
| LOOKUP operations | Q1 per key + Q2 per PAIR (≤ min(units, occ/2)) + index identity | 70,001 |
| Work candidates | one per key + one NONE per keyless unit | 70,000 |
| Claims / decisions / open questions | one / one / at most one per candidate | 70,000 each |
| Stage 02 events per key | `ROW_LIMIT` only | 2,000,000 |
| Attempts | retained / live | 24 / 30 |
| Deferrals | `F_max` | 6 |
| Execution records | 1 + 2 × 30 + 1 | 62 |
| Report records | ASSEMBLE | 1 |
| `verification_recorded` | exactly one, written by VERIFY (W-7, `_guard_success`) | 1 |

Records written by each step in one attempt:

| Step | Records |
|---|---|
| VALIDATE | none |
| ACQUIRE | 1 bundle observation |
| EXTRACT | 1 extraction observation |
| NORMALIZE | evidence per unit and per occurrence, ≥ 70,000 |
| LOOKUP | 70,001 observations |
| DETECT | per candidate: claim, decision, question if routed, plus evidence |
| ASSEMBLE | 1 report |
| VERIFY | 1 `verification_recorded` |

Each attempt also writes its start and its close. Content from a failed or interrupted attempt stays in the journal.

## 2. Record limit (1 MiB)

Records whose payload has no unbounded list, built at every schema maximum (strings at `maxLength` with the
character whose canonical encoding is longest under the field's pattern; integers at 2^53 − 1):

| Kind | Max bytes | Share of limit |
|---|---:|---:|
| investigation_created | 50,257 | 4.79 % |
| step_failed | 25,221 | 2.41 % |
| observation_recorded | 25,112 | 2.39 % |
| step_succeeded (1 output) | 7,041 (+67 per output) | 0.67 % |
| verification_recorded (1 check) | 567 (+91 per check) | 0.05 % |
| stale_detected | 1,379 | 0.13 % |
| decision_recorded | 557 | 0.05 % |
| question_opened | 543 | 0.05 % |
| step_deferred | 445 | 0.04 % |
| step_interrupted / step_started | 375 / 371 | 0.04 % |

`step_succeeded` grows with its outputs. The controller writes the step's blobs plus one manifest, so the count is
set by the adapter; at 67 bytes per output the limit admits about 15,500 outputs.

`verification_recorded` grows with its checks. The schema sets no `maxItems`. At 91 bytes per check (codes at their
64-character maximum) the limit admits about 11,500 checks. SPEC 9.7 names a fixed set of check kinds: M-1…M-14,
W-1…W-8, `verify_bundle`, the three replays, the evidence chains, report and projection validation, and the content
digest. That is about 30 kinds, so the record fits **provided the VERIFY step records one check per kind, not one per
claim**. With 70,000 claims, one check each would need about 6.4 MB. This is a design constraint on the VERIFY
adapter (a later step), recorded here.

Records with lists bounded only by upstream counts:

- **claim_recorded.** A claim's evidence list holds its unit, every candidate-role occurrence of its key in the unit,
  its Q1/Q2 lookups and the coherence result (SPEC 6.3, 6.4). Stage 03 allows up to 50,000 candidate occurrences in
  one document, so the list holds at least 50,005 ids, which is **3,350,335 bytes** before the claim's other fields.
  That is 3.2 × the limit. With one evidence id per Stage 02 event of the key (no Stage 02 constant bounds the events
  of one key below `ROW_LIMIT`), it is 137,350,335 bytes.
- **report_recorded.** At most one projection per distinct work key, at most 50,000 keys, so the list is
  **3,350,000 bytes**, 3.2 × the limit.

**Conclusion: STRUCTURAL REDESIGN REQUIRED.** The bounded kinds are proven sufficient, with at least 20 × headroom.
The claim and report lists are not. An investigation that the Stage 03 caps accept can produce a claim or report
record the limit refuses. Raising the limit would not fix this: the claim bound reaches 137 MB once lookup events
are counted, and no fixed record size covers it. The lists have to move out of the record, into a blob the record
names by digest, or the record has to be split. That changes the accepted Step 5 claim and report schemas and the
Step 6 record layout (Step 6 is not to be reopened), so it is an **owner decision** (section 6).

Interim behaviour (Step 7, tested): a record over the limit is refused by Memory, and the controller ends the
attempt with `STORAGE_ERROR`, reason `RECORD_TOO_LARGE`. Nothing is truncated and nothing is reported as complete
(`test_controller_adversarial.py::test_record_over_the_size_limit_fails_the_step_with_storage_error`).

## 3. Journal limit (512 MiB)

- Execution records: at most 62 (1 creation + 2 per attempt × 30 + 1 stale), at most **1,564,896 bytes** with every
  close at the largest `step_failed`.
- Content records that grow with the Stage 03 caps, one run, lookup events excluded (a lower bound):
  - NORMALIZE: at least one per unit and one per candidate-role occurrence (refs + cands);
  - LOOKUP: one per distinct key, plus the index identity (cands + 1);
  - DETECT: one claim and one decision per candidate (2 × cands).

  That is 220,001 records.
- Failed or interrupted attempts keep their content in the journal, as non-authoritative records (SPEC 10.2). A
  valid investigation that commits on its third attempt therefore holds 3 copies. Lower bound:
  1,564,896 + 3 × 220,001 × 565 = **374,466,591 bytes**, 70 % of the limit, with lookup events still excluded.
- Counting the lookup evidence of a single key at `ROW_LIMIT` events: **3,764,466,591 bytes**, 7.0 × the limit.

**Conclusion: SHOULD BE CONFIGURATION-BOUND.** The limit cannot be proven sufficient, because the events per key are
bounded by the pinned index, not by any Stage 02 or Stage 03 constant below `ROW_LIMIT`. Even the lower bound
without events uses 70 % of the limit, so any further per-unit evidence approaches it. A fixed 512 MiB is arbitrary
with respect to the inputs.

The limit should be derived from caps the investigation is configured with, all recorded in `config_digest`:

- the Stage 03 caps;
- `A_max`;
- a per-key event cap at LOOKUP, which does not exist today.

Without that per-key cap, a pathological index makes the journal bound unbounded, which is a structural property of
the evidence design (one record per event). The per-key event cap and the derived limit are an **owner decision**,
because they add a configuration field and a LOOKUP refusal code.

Interim (Step 7, tested), fail-closed:

- If the record that ends the attempt still fits, the step fails with `STORAGE_ERROR`, reason `JOURNAL_TOO_LARGE`
  (`test_journal_limit_with_room_for_the_failure_fails_the_step_with_storage_error`).
- If even that record is refused, the controller raises `StorageExhausted` and writes nothing more. The attempt stays
  open, and every later run stops at recovery with the same error. Once the limit allows it, the resume closes the
  attempt by W-6 and continues (`test_journal_limit_without_room_for_the_failure_stops_and_writes_nothing`).
- This is found by the Step 7 review. Before the review, Memory's raw `AppendRefused` escaped the controller.

## 4. Blob limit (256 MiB)

| Blob | Bound | Status |
|---|---|---|
| Extraction observation (EXTRACT) | Stage 03 refuses an extraction document over 268,435,456 canonical bytes (`MAX_OUTPUT_BYTES`, `MAX_EXTRACTION_BYTES`). `citerift.wiki.canonical.canonical_bytes` and `citerift.investigation.canonical.canon` use the same encoding (`sort_keys`, `(",", ":")`, `ensure_ascii=False`), and blobs accept floats (`put_blob` uses `allow_float=True`; the document's `worker_wall_s` is a number). | **PROVEN SUFFICIENT**, on one condition: the Step 8 EXTRACT adapter stores the Stage 03 document byte for byte, with no wrapper. A wrapper would exceed the limit by its own size. |
| Bundle observation (ACQUIRE) | Capture JSON ≤ 4 MiB; artifacts ≤ 64 MiB each, carried by digest, not inline. | PROVEN SUFFICIENT if the Step 8 adapter records digests and the capture JSON, not artifact bytes. |
| Lookup observation (LOOKUP) | Per key, up to `ROW_LIMIT` events of up to `FIELD_LIMIT` per field. One digest per event alone is 134,000,000 bytes (49.9 % of the limit); real events are larger. | **SHOULD BE CONFIGURATION-BOUND**: the same per-key event cap as the journal. |
| Report (ASSEMBLE) | Grows with claims and projections, at least 3.35 MB of projection ids alone. Each claim's list can reach 137 MB with events (section 2), so the report is not bounded below the limit. | **SHOULD BE CONFIGURATION-BOUND**, following the claim redesign. |

Interim: `STORAGE_ERROR`, reason `BLOB_TOO_LARGE`, fail-closed (`test_blob_over_the_size_limit_fails_the_step_with_storage_error`).

## 5. Summary

| Limit | Conclusion |
|---|---|
| Record, 1 MiB | Bounded kinds PROVEN SUFFICIENT. Claim and report lists: **STRUCTURAL REDESIGN REQUIRED**. |
| Journal, 512 MiB | **SHOULD BE CONFIGURATION-BOUND**. Needs a per-key event cap at LOOKUP. Without one the bound is structural. |
| Blob, 256 MiB | Extraction and bundle: PROVEN SUFFICIENT under the Step 8 storage conditions above. Lookup and report: **SHOULD BE CONFIGURATION-BOUND**. |

None of the three limits was changed in Step 7.

- All three are Step 6 Memory constants, and the owner said not to reopen Step 6.
- The fixes change accepted Step 5 schemas and add configuration.
- Every refusal is fail-closed: `STORAGE_ERROR` with the limit as reason.
- The owner's rule ("a limit that rejects a valid investigation is a defect to fix within Stage 04") makes these
  Stage 04 defects. They are listed as open, to be fixed inside Stage 04 once the owner chooses the design.

## 6. Owner decisions

- **RB-1 (record).** Move the claim's evidence lists and the report's projection list into blobs named by digest,
  or split them across records. Recommendation: blobs named by digest. They keep one claim per record (W-8 and the
  fold unchanged) and reuse M-5 output validation. This changes the Step 5 claim and report schemas, Memory's blob
  reference check and the Step 4 differential invariants on claims.
- **RB-2 (journal, lookup and report blobs).** Add a configured per-key event cap at LOOKUP, with a refusal code,
  and derive the journal and blob limits from the configured caps. Alternatively keep fixed limits and accept that
  pathological indexes fail closed. Recommendation: the configured cap, because a fixed limit is arbitrary under
  owner item 17.
- **Timing.** Both are Stage 04 work. They belong with the real adapters (Step 8/9), where the evidence layout is
  built, or in a dedicated step. Either way, before any real investigation runs.
