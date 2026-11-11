# Stage 04: per-candidate batches, journal format 4 (D-055)

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP7cfPWf5UN6kmKGbSHoPG1n` (2026-11-11T16:48:14Z), answering OD-J2:
"APPROVED — batch the remaining per-candidate journal records. Do not keep one journal record per candidate. Do not
raise the 512 MiB journal limit. Do not impose an article-size cap." Baseline `0097a9329d728e8260d48dc79a53a6be5f9c4fa9`
(CI run 313 accepted as green). Decision record: DECISIONS.md D-055. Step 8 is not started.

Labels: **[verified]** means measured or tested here, with the file named. **[inference]** means derived, not
measured. **[condition]** is a requirement on a later step.

## 1. Result in one table

| Limit or requirement | Status |
|---|---|
| Journal, 512 MiB | **PROVEN** [verified, `bounds.py` → `bounds.json`, test `test_format_4_bounds_are_recomputed_and_proven`]: format 4 as implemented, every attempt, deferral, interruption and failure counted: 1,345,917 B typical (0.25 %), **8,640,021 B maximal (1.61 %, 62.1× headroom)**. |
| Record, 1 MiB | **PROVEN** [verified, `bounds.json`]: largest record 50,297 B (`investigation_created`); a LOOKUP or DETECT batch record is at most 531 / 541 B whatever the batch holds. |
| Blob, 256 MiB | **PROVEN** for every blob kind, the two new batch kinds at 8 MiB (3.1 %), with the unchanged ACQUIRE condition (IF-7, section 10). |
| Part ceiling | **UNCHANGED, 8 MiB** [verified, `part_ceiling.json`, `changed_from_d053: false`]: re-derived by the D-053 method with LOOKUP and DETECT entries; one legal entry always fits. |
| Scientific invariance | **PROVEN** on eight scenarios: every logical digest equals the format-3 baseline `0097a93` [verified, `equivalence.py`, test `test_logical_content_equals_the_format_3_baseline`]. |
| Crash points (5) and corruption / forgery cases | **PASS** [verified, `tests/stage04/test_d055.py`]. |
| Performance | **Better on every measure except blob bytes** [verified, `perf_0097a93.json`, `perf_after.json`]: at 70,000 candidates, journal records 218,773 → 33, journal bytes 149.6 MB → 17 kB, DETECT commit 615 → 259 s, open 490 → 283 s, open peak memory 1.21 GB → 570 MB; blob bytes 84.6 → 160.7 MB (total storage 234.2 → 160.7 MB). |

## 2. Format

- Journal format `v = 4` (`JOURNAL_FORMAT`). Formats 1 to 3 were development formats, never released; a journal in
  any of them opens `CORRUPT` / `JOURNAL_VERSION_UNSUPPORTED` (tested for 1, 2, 3). No migration.
- `journal-record.schema.json` 4.0.0. Two new record kinds with the closed payload
  `{batch, batch_index, batch_total, entry_count}`:
  - `lookup_batch_recorded` (LOOKUP only);
  - `candidate_result_batch_recorded` (DETECT only).
- `claim_recorded`, `decision_recorded` and `question_opened` are no longer record kinds; an `observation_recorded`
  record may no longer carry `obs_kind: lookup`. `question_closed` and `claim_superseded` (resolution) are unchanged.
- Adapters are unchanged: they still return single `observation_recorded` (lookup) and `claim_recorded` content
  records. Only the controller builds batches; an adapter never supplies one.

### LOOKUP batch (`lookup-batch.schema.json` 1.0.0)

`{schema, schema_version, order: "observation-blob/entry/1", entries}`. Each entry is one compact lookup observation
reference `{obs_kind: "lookup", blob, source_ref}`, exactly the payload the format-3 record carried. The lookup
observation blob itself is never inlined; the entry names it by digest and the fold requires it to exist and be
intact (`BLOB_MISSING` / `BLOB_CORRUPT`). Two candidates that share one lookup give two equal entries; duplicates are
allowed, so the batch is a multiset, exactly as format 3 allowed two equal records.

### DETECT candidate-result batch (`candidate-result-batch.schema.json` 1.0.0)

`{schema, schema_version, order: "candidate-ref/claim-id/1", entries}`. Each entry is one candidate's result
`{claim, decision, question}`: the unchanged `claim` (D-047 evidence set bound into `claim_id`), its `decision`
(same `claim_id`) and the identity or contradiction `question`, or `null`. This is storage only: an entry never
merges candidates, dt-1 identity and W-8 are unchanged, and a candidate with two claims is still two entries (and
still refused by W-8, section 7).

## 3. Ordering and boundary rule (SPEC 8.9, MM 7.5)

- **Order.** LOOKUP entries by `(blob digest, canonical encoding of the entry)`, non-decreasing; DETECT entries by
  `(cand_ref, claim_id)`, strictly increasing (a repeat is `DUPLICATE_ID`). Both keys are functions of the entry, so
  the same set in any adapter order gives the same order. [verified: `test_*_order_and_boundaries_do_not_depend_on_the_input_order`,
  5 shuffles each; `test_adapter_order_does_not_change_the_batches_or_the_digest` end to end.]
- **Boundaries.** The D-053 primitive `batches.boundaries` unchanged: a part closes before the next entry would push
  its canonical encoding over `MAX_PART_BYTES` (8 MiB); a part is never empty, so one legal entry always fits.
  [verified: N−1/N/N+1 tests for both kinds; `test_one_legal_entry_always_fits_and_the_ceiling_is_the_d053_one`.]
- **Scope.** Batches are step-local and attempt-local: a series starts at index 0 in its attempt, keeps one
  `batch_total`, and must be complete at `step_succeeded` (S-8.9 `BATCH_SEQUENCE`); a batch digest is never recorded
  twice (M-14). [verified: `test_no_batch_crosses_a_step_or_an_attempt`.]
- **Canonical check.** At `step_succeeded` the order and cut are recomputed from the entries and must be the
  canonical ones (`BATCH_NOT_CANONICAL`), on append and on every open.
- **No conflict with the report or dt-1.** The report (D-054) consumes the logical fold and orders its claim chunks
  by its own key (unit byte offset, candidate keys, claim id) and its observations by digest; the batch order is
  never read by it. dt-1 identity (`cand_ref`, `claim_id`) is the input of the key, not changed by it.

### Commit discipline

Write order per attempt: blobs (evidence batches, lookup and candidate batches, evidence sets), then evidence batch
records, then lookup / candidate batch records, then the remaining records, then `step_succeeded`. A batch is
authoritative only once its attempt's `step_succeeded` is in the journal. The batches of a failed or interrupted
attempt may stay as blobs and records but never enter the committed content; no batch is shared across attempts.
[verified: `test_a_batch_of_an_attempt_that_did_not_succeed_is_not_authoritative`, crash tests section 6.]

## 4. Fold: logical records

`Folder` expands each batch, once, into the logical records it stands for: one `observation_recorded` (lookup) per
LOOKUP entry; one `claim_recorded`, one `decision_recorded` and, when present, one `question_opened` per DETECT entry,
each carrying the batch record's `seq`, step and attempt. `committed_content()` returns the logical records (what
W-8, M-7, the report and replay consume); `committed_records()` returns the storage records; the content digest
`C(J)` is computed over the storage records. There is no second mutable index: the expansion is rebuilt from the
journal and blobs on every open. A fold that has not read the batch blobs (no blob store and no validated source)
marks itself `unexpanded`, and the workflow guard refuses to judge such a fold (M-3, fail closed) instead of seeing
empty content.

Checks per entry: M-3 `LOOKUP_BATCH_INVALID` / `CANDIDATE_BATCH_INVALID` (schema, version, order label,
`entry_count`, empty batch), M-3 `BLOB_MISSING` / `BLOB_CORRUPT` (lookup blob, evidence set), M-7
`CANDIDATE_ENTRY_INVALID` (decision or question for another claim), M-14 `DUPLICATE_ID` (claim id, batch digest),
M-4 / M-7 as before for evidence. W-8 runs unchanged on the logical content of the attempt.

## 5. Record counts before and after

| | Format 3 (`0097a93`) | Format 4 (this change) |
|---|---|---|
| Per-candidate journal records, one attempt at the Stage 03 caps (70,000 candidates) | up to 280,000 (70,000 lookup observations, claims, decisions, and up to 70,000 questions) | typical 5 LOOKUP + 17 DETECT batch records; maximal 416 + 824 |
| Journal at the caps, `A_max` = 3, typical | 554.8 MB (103 %, `../d053/bounds.json`) | 1,345,917 B (0.25 %) |
| Journal at the caps, every field at its maximum | 15.8 GB (2,940 %) | 8,640,021 B (1.61 %) |
| Measured, 70,000 candidates, one attempt each (section 10) | 218,773 records (218,750 per candidate), 149,558,851 B | 33 records (0 per candidate; 218,750 logical records), 17,061 B |

## 6. Crash tests [verified, `test_process_death_at_every_listed_point`]

The process is killed (`os._exit` through the fault hooks) at each point and the investigation is resumed. At every
point: committed content comes only from succeeded steps (no claim or decision before DETECT succeeds); the journal
before the crash is a prefix of the journal after; no succeeded step runs again; every step succeeds exactly once;
after the resume the logical content, its digest and the lifecycle equal those of an uninterrupted run (deterministic
replay); leftover blobs are harmless extras.

| Point (owner's list) | Fault hook |
|---|---|
| during the candidate batch blob write | `blob.during_write` (a candidate batch) |
| after blob publication, before the batch record | `controller.after_blobs` (DETECT) |
| between candidate batch records | `controller.after_entry_batch` (DETECT, after batch 0) |
| after all batch records, before success | `controller.after_entry_batch` (DETECT, after the last batch) |
| between LOOKUP batch records | `controller.after_entry_batch` (LOOKUP, after batch 0) |

The D-053 points (torn tail during a record append, evidence batches, report chunks) still pass unchanged in
`test_d053_d054.py`, now over format-4 journals.

## 7. Corruption and forgery tests [verified, `tests/stage04/test_d055.py`]

Each case opens `CORRUPT` with the cause shown (fail closed; nothing repaired, dropped or guessed).

| Case (owner's list first) | Cause |
|---|---|
| missing candidate batch / missing LOOKUP batch | M-3 `BLOB_MISSING` |
| corrupt (changed bytes) candidate or LOOKUP batch | M-3 `BLOB_CORRUPT` |
| wrong batch digest: another existing candidate batch; a digest naming no blob; a candidate batch named as a LOOKUP batch | M-14 `DUPLICATE_ID`; M-3 `BLOB_MISSING`; M-3 `LOOKUP_BATCH_INVALID` |
| duplicate candidate entry | M-14 `DUPLICATE_ID` |
| duplicate claim id | M-14 `DUPLICATE_ID` |
| duplicate candidate across two batches | M-14 `DUPLICATE_ID` |
| incorrect ordering (batches swapped); non-canonical cut (two batches merged) | S-8.9 `BATCH_NOT_CANONICAL` |
| incorrect count (`entry_count`) / index (`batch_index`, `batch_total` short or long) | M-3 `CANDIDATE_BATCH_INVALID`; S-8.9 `BATCH_SEQUENCE` |
| claim without decision; decision without claim | M-3 `CANDIDATE_BATCH_INVALID` |
| decision for another claim; question for another claim | M-7 `CANDIDATE_ENTRY_INVALID` |
| claim naming a missing evidence set | M-3 `BLOB_MISSING` |
| unknown batch version; wrong order label; empty batch | M-3 `CANDIDATE_BATCH_INVALID` |
| LOOKUP entry naming a missing observation blob | M-3 `BLOB_MISSING` |
| failed-attempt batch | never authoritative (section 3) |

W-8 refusals (unchanged rule, now over batch entries), each tested both in a stored journal (the run ends `CORRUPT`,
cause W-8) and when appended (`WorkflowRefused`, W-8): two claims for one candidate; wrong disposition; conflict plus
a positive result; conflict plus a negative result; missing required conflict question; unexpected question. The
Step 7 W-8 guard tests also cover a dropped decision (M-3) and a decision or question for another claim (M-7).

## 8. Bounds [verified, `bounds.py` → `bounds.json`]

`bounds.py` builds every format-4 record kind at its maxima (the measured set must equal the schema's kind enum) and
reuses the D-053 builders. Counted for the journal: `investigation_created`; every execution record of every attempt
(`A_max` = 3 per step, `A_max + F_max` = 9 for ACQUIRE, an interruption before each terminal record, deferrals
included); `stale_detected`; the bundle, extraction and index-identity observations of every attempt; report and
verification records of every attempt; and the batch records of every attempt of every step, also of attempts that
failed after writing them (`A_max` copies). A closed part holds at least `(c − E − envelope) / 2` entry bytes (MM 7.5,
CB-4), which bounds the batch record count from the entry bytes.

| | Entries per run | Entry bytes typical / maximal | Batch records per attempt, typical / maximal |
|---|---|---|---|
| evidence item (D-053) | 510,000 | 380 / 27,477 | 49 / 3,355 |
| lookup reference | 70,000 | 227 / 24,751 | 5 / 416 |
| candidate result | 70,000 | 936 / 48,987 | 17 / 824 |

The maximal candidate entry (48,987 B) is the sum of every field at its maximum and is not itself a valid entry; the
largest validated entry is 42,432 B (`UNRESOLVED_STATUS`). Using the larger figure only over-approximates.

**Final journal bound:** fixed records 1,231,356 B + `A_max` × batch records → **1,345,917 B typical (0.25 %, 399×
headroom); 8,640,021 B maximal (1.61 %, 62.1× headroom)** of 536,870,912 B.

Blobs: the LOOKUP batch and the candidate-result batch are each at most 8,388,608 B (3.1 %): cut at the ceiling, and
the largest legal entry (≤ 48,987 B) is far below it. The other rows are the D-053 rows, unchanged.

## 9. Part ceiling [verified, `part_ceiling.py` → `part_ceiling.json`]

The D-053 method, applied with the LOOKUP and DETECT entries added (`part_ceiling.py`, Python 3.12.3, 4 vCPU):

| Rule | Input | Result |
|---|---|---|
| 1. largest entry | every entry kind at its schema maxima | evidence 27,477 B; lookup reference 24,751 B; candidate result 42,432 B validated (`UNRESOLVED_STATUS`), 48,987 B as sum of field maxima; with the 145 B envelope a part must allow ≥ 49,132 B |
| 2. blob limit | `MAX_BLOB_BYTES` | ≤ 256 MiB |
| 3. measured time | 20,000 typical candidate results per attempt (1 in 8 `IDENTITY_CONFLICT`), ceilings 32 KiB to 16 MiB, 3 runs each; the D-053 evidence rows unchanged | DETECT commit 72.7 to 80.6 s, open 35.3 to 38.3 s; every ceiling ≥ 128 KiB within 10 % of the best (32 KiB: commit +10.8 %) |
| 4. parse and validation memory | one batch read and validated | peak 4.0× (typical) to 6.16× (maximal valid entries) the batch size: about 52 MB for an 8 MiB batch |
| 5. record count | 510,000 evidence items + 70,000 lookup references + 70,000 candidate results per run at the caps, every entry maximal, `A_max` = 3 | batch records ≤ 1 % of the journal limit needs a ceiling ≥ 5.37 MB; smallest power of two 8 MiB (3,687,387 B of batch records in that worst case) |

Admissible ceilings: 8 MiB and 16 MiB; selected the smallest, **8,388,608 B, the same as D-053** (`changed_from_d053:
false`). `test_ceiling_still_holds_with_lookup_and_candidate_entries` pins `MAX_PART_BYTES` to this file. The
commit cost per candidate (about 3.6 ms) is dominated by jsonschema validation, not by the batch size (rule 3).

## 10. Performance [verified, `perf.py` → `perf_0097a93.json`, `perf_after.json`]

One investigation runs end to end on the synthetic adapters of the tree measured, except that LOOKUP commits `N`
lookup observations (`N` distinct lookup blobs) and DETECT commits `N` candidate results over them (one in eight an
`IDENTITY_CONFLICT` with its question, the rest `NOT_FOUND_IN_CHECKED_SOURCES`). `N = 70,000` is the Stage 03 cap
(`max_candidates + max_refs`). Same machine (4 vCPU, Python 3.12.3), one process, no other long job running (a minute of lint and type checks overlapped the start of the
baseline run; an earlier baseline run, stopped by a time limit, measured 15.9 s and 164.4 s for the first two rows). "Before" is
the clean `0097a93` worktree (format 3), "after" the clean committed tree `bdee8d5` (format 4). Commit time runs from
the adapter's return to the step's terminal record; open time is a read-only open that reads and checks every record
and every blob it names; peak memory is the Python heap peak of a second open (`tracemalloc`).

| N | | Journal records | Per-candidate records | Journal bytes | Blob bytes | LOOKUP commit, s | DETECT commit, s (ms per candidate) | Open, s (ms per candidate) | Open peak memory | Whole run, s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1,000 | before | 3,148 | 3,125 | 2,140,930 | 1,215,855 | 3.28 | 9.46 (9.46) | 6.90 (6.90) | 21.6 MB | 17.1 |
| 1,000 | after | 25 | 0 | 13,181 | 2,301,273 | 1.01 | 3.88 (3.88) | 4.12 (4.12) | 12.6 MB | 9.6 |
| 10,000 | before | 31,273 | 31,250 | 21,340,078 | 12,067,815 | 33.1 | 85.0 (8.50) | 71.1 (7.11) | 198.6 MB | 164.2 |
| 10,000 | after | 26 | 0 | 13,667 | 22,929,627 | 11.2 | 38.2 (3.82) | 39.7 (3.97) | 107.1 MB | 90.7 |
| 70,000 | before | 218,773 | 218,750 | 149,558,851 | 84,594,237 | 241.7 | 615.2 (8.79) | 490.4 (7.01) | 1,209.9 MB | 1,184.1 |
| 70,000 | after | 33 | 0 | 17,061 | 160,692,047 | 71.1 | 258.6 (3.69) | 283.5 (4.05) | 569.6 MB | 630.9 |

The logical per-candidate records are the same in both trees (3,125 / 31,250 / 218,750: one lookup observation, one
claim and one decision per candidate, and a question for one in eight). At 70,000 candidates batching cuts DETECT
commit time by 2.4×, LOOKUP commit by 3.4×, open time by 1.7× and open peak memory by 2.1×. The per-candidate content
moved from the journal into batch blobs: blob bytes grow by 76.1 MB while the journal shrinks by 149.5 MB, so the
investigation's total storage falls from 234.2 MB to 160.7 MB.

The remaining cost is jsonschema validation of every entry, on commit and on open (IF-1): about 3.7 ms per candidate
to commit and 4.0 ms to open, so a read-only open at the caps takes about 4.7 minutes for the candidates alone. It
was not optimized and no duplicate validation was removed, per the owner. Whether that is a material bottleneck for
the vertical slice is an owner question for later steps; it is not a correctness issue.

## 11. Scientific invariance [verified]

`equivalence.py` runs eight scenarios with the same synthetic adapters on the baseline tree (`0097a93`, format 3)
and on this tree (format 4), and reduces each journal to its logical view: every committed evidence item, every
claim, decision and question payload, the bundle and extraction observations in commit order, the lookup
observations as a sorted multiset (format 3 kept the adapter's order, format 4 the canonical order; the order of
content-addressed lookup references carries no meaning, and the report orders observations by digest), the
lifecycle, the outcome, and the failing step's code. The LOOKUP adapter supplies its references in reverse order, so
the canonical reordering is exercised. Each scenario name says exactly which classes DETECT commits.

| Scenario | Lifecycle, outcome | Logical digest (before = after) |
|---|---|---|
| positive finding (`RETRACTED_WORK_CITED`) | COMPLETED, completed | `c68d75b9e5ece0ba9ef51c5105ec549f0082dbd2752e2c9ce8d2f1377f68bebe` |
| not found in checked sources | COMPLETED, completed | `9012bf0734f9b2886f7c4be34c2e457d0e784050320e27f6e76f3580eab0aff8` |
| lookup unavailable | COMPLETED, partial | `efeb45c3b435750d26194fe8217d466362cb09b30704d0d0ff743ff6e2b67c0c` |
| identity conflict (with its question) | NEEDS_RESOLUTION, partial | `6019247fe5ba6c3d02f40a7e9de0fdaf8238d9dd2c4cc237c4c2b70d898c9429` |
| contradiction in sources (with its question) | NEEDS_RESOLUTION, partial | `fd048a42d5a95d38e55c10977cdd0906a96c34964f17c645d791ffc36c293097` |
| terminal DETECT failure: decision-table gap (a claim of an unknown class) | FAILED, `DECISION_TABLE_GAP` | `7ee3754fbcf5377a74a62ce4a9fe36cbfbb5827e71510558cf3a6c8d7b18ec6d` |
| terminal DETECT failure: adapter exception (the synthetic DETECT has no `CONCERN_CITED` claim) | FAILED, `ADAPTER_INCONSISTENT` | `e9a59bbf458db0cd2c6152fc02c9a51c87c23beef046f37d425e097dd25269ad` |
| mixed article: the five classes above, 4 distinct lookups + 1 shared (5 references) | NEEDS_RESOLUTION, partial | `f8ce64ef7a1f9dba83ccc2483714d2bf8fb3ea03aaacba7d740275f2322548c9` |

`CONCERN_CITED` and `UNRESOLVED_STATUS` are not executed by any scenario: the synthetic DETECT does not produce them
(the seventh scenario shows the refusal path, not the class). They are covered by schema and fold tests only.

The baseline run is retained as `equivalence_0097a93.json` (tree `0097a93`, format 3, clean), the format-4 run as
`equivalence_after.json`; `test_logical_content_equals_the_format_3_baseline` pins the eight baseline digests and
`test_the_baseline_run_is_the_accepted_format_3_tree` checks the baseline file's provenance. dt-1, precedence,
dispositions, `NEEDS_RESOLUTION`, claim identity, the D-048 lookup, the Stage 03 extraction and the frozen Step 4
oracle are not changed; the Step 4 differential tests run unchanged against the frozen model (one new classified
category entry: a LOOKUP probe after its batch series is closed is S-8.9 `BATCH_SEQUENCE`, proven in
`test_batch_series_closed_is_the_batch_sequence_rule`).

## 12. Schema and format versions

| Item | Before (`0097a93`) | After |
|---|---|---|
| journal record field `v` | 3 | 4; formats 1 to 3 refused, no migration |
| `journal-record` | 3.0.0 | 4.0.0 |
| `lookup-batch`, `candidate-result-batch` | absent | 1.0.0 |
| `claim`, `common`, `request`, `evidence-batch`, `evidence-set`, `projection-set`, `report`, `report-chunk` | | unchanged |
| Stage 00 (`schemas/governance`), `schemas/contracts`, Stage 02 and Stage 03 schemas and code, `.github/` | | unchanged |

## 13. Inherited baseline audit

No accepted-stage file was changed (`git diff 0097a93` touches no file under `src/citerift/wiki`,
`src/citerift/retraction`, `src/citerift/governance`, `schemas/wiki`, `schemas/retraction`, `schemas/governance`,
`schemas/contracts` or `.github/`), so no maintenance transaction was needed.

| Id | Finding | Disposition |
|---|---|---|
| IF-7 | The Stage 03 capture schema leaves `attempts`, `issues`, `failure_artifacts` without `maxItems`, so the ACQUIRE observation has no schema bound. | Unchanged: **Step 8 condition** (owner D-055). An over-limit blob fails closed (`BLOB_TOO_LARGE`). |
| IF-8 | The Stage 03 extraction can be exactly `MAX_BLOB_BYTES`. | Not a defect; recorded. |
| IF-1 | jsonschema dominates append and open time. | Still true (section 10); not optimized, per the owner. |
| D-052, R6-12 | External checkpoint is design only. | Unchanged. |

## 14. Tests

- **New `tests/stage04/test_d055.py`** (69 tests): order and boundaries independent of the input order (both kinds,
  5 shuffles each), boundaries at N−1/N/N+1, one legal entry fits, batch-backed LOOKUP and DETECT with the logical
  counts, adapter order does not change batches or `C(J)`, a failed or interrupted attempt is not authoritative, no
  batch crosses a step or attempt, six W-8 forgeries stored and appended, every corruption case of section 7, the five
  crash points of section 6, the ceiling pinned to `part_ceiling.json`, the eight baseline digests and their
  provenance, and the bounds recomputed against `bounds.json`.
- **Updated for format 4:** `controller_support.py`, `memory_support.py` (`append_lookups`, `append_candidates`),
  `test_controller_adversarial.py` (record-size and journal-limit tests moved to ACQUIRE, whose records still grow
  with content), `test_controller_crash.py` (new hook `controller.after_entry_batch`), `test_controller_differential.py`
  (the LOOKUP probe; `BATCH_SERIES_CLOSED` now proven to be S-8.8 or S-8.9 `BATCH_SEQUENCE`),
  `test_controller_guard.py`, `test_controller_resolution_stale.py` (W-8 guard over forged entries, plus M-3 and M-7
  cases), `test_memory_journal.py`, `test_schemas_step5.py`, `test_step7_closure.py` (formats 1 to 3 refused).
- The frozen Step 4 oracle and its tests are unchanged (`git diff 0097a93` is empty for `simulations/`,
  `docs/verification/stage-04/simulation` and `tests/stage04/test_simulation_step4.py`).
- Full suite at `bdee8d5`: **2,912 passed, 0 skipped**, on Python 3.12.3 (12 min 39 s) and 3.13.18 (11 min 48 s), the
  two run at the same time on one 4-vCPU machine; `check-report` 0 problems for both (clean tree). The baseline
  `0097a93` has 2,835 tests.
- Also run: `ruff check`, `ruff format --check`, `mypy` (73 source files), `check-schemas`, the Step 3 checker
  (PASS, 0 failed), `citerift-gov check` (0 errors, 0 warnings), `render-status --check`, `pip-audit --strict`
  (no known vulnerabilities).

## 15. Remaining Step 8 conditions

- IF-7: bound the ACQUIRE observation representation (capture document arrays) before real ACQUIRE adapters write it.
- The real VERIFY adapter must report the D-054 report-graph check in its verification record (D-054 condition).
- Real LOOKUP and DETECT adapters keep returning single content records; only the controller batches (no adapter
  batch interface exists).
- Step 12 independent review must revisit the Memory/controller boundary, D-044, D-046 (Step 6 condition), now
  including the logical expansion of batches.
