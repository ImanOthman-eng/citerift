# Stage 04: evidence batches and the chunked report (D-053, D-054)

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPT7kaAY3dV5Ewo8KzF3bTe8` (2026-11-11T10:31:40Z): "Choose Evidence batches
+ chunked report." The baseline is `64e7acace6d13e61f3346b51cd045883236f9dca` (CI run 312 green; A-02-001
finalized). Step 8 is not started. No article-size cap is imposed. Decision records: DECISIONS.md D-053 and D-054.

Labels: **[verified]** means measured or tested here, with the file named. **[inference]** means derived, not
measured. **[condition]** is a requirement on a later step. **[owner]** needs an owner decision.

## 1. Result in one table

| Limit or requirement | Status |
|---|---|
| Record, 1 MiB | **PROVEN** [verified, `bounds.json`]: the largest record of any format-3 kind is 50,297 B (4.8 %). The batch record is at most 536 B whatever the batch holds. |
| Blob, 256 MiB | **PROVEN** for every blob kind [verified, `bounds.json`], with one Step 8 condition (the ACQUIRE observation, section 6) and one blob at exactly the limit (the Stage 03 extraction, by Stage 03's own cap). |
| Journal, 512 MiB, evidence batched (this change) | **NOT PROVEN** [verified, `bounds.json`]: with the per-candidate records (lookup observations, claims, decisions, questions) still one record each, a run at the Stage 03 caps writes about 184.5 MB of content per attempt; `A_max` = 3 attempts give 554.8 MB typical (103 % of the limit) and 15.8 GB at every field maximum. |
| Journal, 512 MiB, per-candidate records also batched | **PROVEN** [inference, same model, `bounds.json` "batched"]: 1.3 MB typical, 8.6 MB maximal (1.6 %, 62× headroom). Not implemented: it is the open owner question (section 7). |
| Scientific invariance | **PROVEN** on five scenarios [verified, `equivalence.py`, test `test_logical_content_equals_the_accepted_baseline`]. |
| Crash points (9) and corruption cases (25) | **PASS** [verified, `tests/stage04/test_d053_d054.py`]. |

## 2. Evidence batches (D-053)

### Format

- Journal format `v = 3` (`JOURNAL_FORMAT`). Format 1 is the original, format 2 is D-047/D-051, format 3 is this
  change. None was released; a format-1 or format-2 journal opens `CORRUPT` / `JOURNAL_VERSION_UNSUPPORTED` (tested in
  `test_memory_journal.py`). No migration.
- `evidence_recorded` is replaced by `evidence_batch_recorded` with the closed payload
  `{batch, batch_index, batch_total, evidence_count}` (`journal-record.schema.json` 3.0.0).
- Batch blob `evidence-batch.schema.json` 1.0.0: `{schema, schema_version, order, items}`, items the unchanged
  `common#/$defs/evidence` (D-051 ids). `order = "dependency-topological/evidence-id/1"`.
- Adapters still supply single evidence items (`ContentRecord("evidence", item)`); only the controller makes
  batches. An adapter never supplies a batch.

### Ordering algorithm (`batches.dependency_order`, SPEC 8.8 (c), MM 7.4)

Kahn's topological sort over the attempt's reference graph, with a min-heap on the evidence id as the ready set. A
reference to committed evidence is not an edge; a reference to anything else undefined is `DANGLING_REFERENCE`.
Duplicate id → `DUPLICATE_ID`; a cycle → `DEPENDENCY_CYCLE`. The result is the lexicographically least topological
order, so it depends only on the item set. Tests: input-order independence, references before items across batch
boundaries, evidence-id tie-break, refusal of cycle / missing ref / duplicate (controller: `ADAPTER_INCONSISTENT`).

### Boundaries and the derived ceiling

Greedy byte ceiling on the canonical encoding: a part closes before the next item would push it over
`MAX_PART_BYTES`; a part is never empty, so one legal item always fits (an oversize item is a part of its own, still
under `MAX_BLOB_BYTES`). Tests at N−1, N and N+1 against an independent greedy reference.

`MAX_PART_BYTES` = 8 MiB, derived by `part_ceiling.py` → `part_ceiling.json` [verified]. It is not a count; the
item count per batch follows from the item sizes (about 21,400 typical items or 305 maximal items per batch, `part_ceiling.json` rule 4).

| Rule | Input | Result |
|---|---|---|
| 1. largest item | every evidence kind built at its schema maxima | `E_max` = 27,477 B; with the 147 B envelope a part must allow ≥ 27,624 B |
| 2. blob limit | `MAX_BLOB_BYTES` | ≤ 256 MiB |
| 3. measured time | 20,000 items per attempt, ceilings 32 KiB to 16 MiB, 3 runs each | commit 20.2 to 21.3 s, open 9.6 to 10.2 s: no ceiling ≥ 1 MiB is measurably slower (all within 10 % of the best) |
| 4. parse and validation memory | one batch read and validated | peak 4.4× (typical items) to 5.0× (maximal items) the batch size: 42 MB for an 8 MiB batch |
| 5. record count | 510,000 items per run at the Stage 03 caps, every item maximal, `A_max` = 3 | batch records ≤ 1 % of the journal limit needs a ceiling ≥ 5.37 MB; the smallest power of two is 8 MiB (2.7 MB of batch records in that worst case) |

Selected: the smallest power of two that satisfies all five rules. A test pins `MAX_PART_BYTES` to
`part_ceiling.json`.

### Memory checks (fold, on append and on open)

Per batch record: `batch_index` continues the series and `batch_total` is constant (`BATCH_SEQUENCE`); the batch
digest is new (`DUPLICATE_ID`); the blob exists and is intact (`BLOB_MISSING` / `BLOB_CORRUPT`); it is schema-valid
and `evidence_count` matches (`EVIDENCE_BATCH_INVALID`); per item, the D-051 id (`EVIDENCE_ID_INVALID`), a recorded
observation (M-10), references to earlier evidence only (M-4), and a new id (M-14). At `step_succeeded`: the series
is complete, and the order and boundaries recomputed from the items' `(id, refs, size)` are the canonical ones
(`BATCH_NOT_CANONICAL`). A journal can therefore hold only one representation of given content.

### Fold and index

`Folder` keeps, per committed evidence id, its batch and position (`evidence_batch`, `evidence_item`). Evidence sets
(D-047) resolve through it, M-7 checks that every claim's evidence exists, and replay reads the same batches. The
index is rebuilt from the journal and blobs on every open; there is no second store. Uncommitted batches (an attempt
that did not reach `step_succeeded`) are not in the index: tested by
`test_batches_of_an_attempt_that_did_not_succeed_are_not_authoritative`.

## 3. The report manifest graph (D-054)

`report.schema.json` 3.0.0 (manifest) and `report-chunk.schema.json` 1.0.0 (chunk); `src/citerift/investigation/report.py`
builds and checks them; SPEC 11.1 states the format.

- Manifest: identities, root, terminal state, outcome, `article_summary` (claims by class, open questions, snapshot
  id), limitations, identities/config, and `components` with `order`, `count` and ordered `chunks` per part.
- Parts in chunks: `claims` (order: unit byte offset, candidate keys, claim id), `observations` (commit order),
  `positive_works` (canonical work). The cut is the same byte-ceiling rule as batches.
- Evidence: the manifest lists the committed evidence batches `{batch, count}` in commit order.

**Reuse analysis.** The report needs every committed evidence item, each exactly once, in a fixed order, with
integrity. The committed batches already give exactly that: content-addressed, immutable, schema-checked, in the
canonical commit order, and their union is the committed evidence (no loss, no duplicate, by the D-053 checks). A
copy would add up to 14 GB per run at the maxima (`bounds.json`, `evidence_per_run.max_bytes`) and a second
representation to keep equal. No semantic need for a copy was found: the report adds no per-evidence field. So the
report names the batches; `test_report_reuses_the_committed_batches_and_copies_no_evidence` proves the listed
batches are exactly the committed ones and no chunk holds an evidence item.

**Verification.** `report.graph_problem` proves the graph alone; `report.fold_problem` adds equality with the
committed fold (claims with decisions and open questions, observations, evidence batches, investigation key and id,
root). Investigation Memory runs it when `report_recorded` is appended and on every open (`REPORT_INVALID`, M-3).
The graph is therefore proven before VERIFY can start (the append is part of ASSEMBLE's commit) and again on every
later open; nothing is silently omitted. [condition] The real VERIFY adapter (Step 8) must also report this check in
its verification record; the synthetic VERIFY of Step 7 records a fixed result. The D-047 projection set
is unchanged.

## 4. Crash tests [verified, `test_process_death_at_every_listed_point`]

The process is killed (`os._exit` through the fault hooks) at each point, then the investigation is resumed. At
every point: no false committed evidence (only the batches of succeeded steps are committed, and none is missing);
the journal before the crash is a prefix of the journal after; no succeeded step runs again; every step succeeds
exactly once; after the resume the committed evidence equals an uninterrupted run and the content digest `C(J)` is
the same; leftover blobs are harmless extras.

| Point | Fault hook |
|---|---|
| before batch blob creation | `controller.after_adapter` (NORMALIZE) |
| during the batch blob write | `blob.during_write` (a batch) |
| after fsync, before publication | `blob.after_fsync` (a batch) |
| after publication, before the record | `controller.after_blobs` (NORMALIZE) |
| between batch records | `controller.after_batch` (NORMALIZE, after batch 0) |
| after all batch records, before success | `controller.after_batch` (DETECT, last batch) |
| during the batch record append (torn tail) | `journal.during_append` |
| during claim-chunk creation | `blob.during_write` (a claim chunk) |
| during manifest creation | `blob.during_write` (the manifest) |

## 5. Corruption tests [verified, `tests/stage04/test_d053_d054.py`]

Each case opens `CORRUPT` with the cause shown (fail closed; nothing repaired, dropped or guessed).

| Case | Cause |
|---|---|
| missing batch | M-3 `BLOB_MISSING` |
| changed batch bytes | M-3 `BLOB_CORRUPT` |
| wrong batch digest in the record: another existing batch; a digest naming no blob | M-4 or M-3 (its items refer to undefined evidence); M-3 `BLOB_MISSING` |
| invalid item | M-3 `EVIDENCE_BATCH_INVALID` |
| duplicate id | M-14 `DUPLICATE_ID` |
| cycle | M-4 `DANGLING_REFERENCE` (a cycle has a reference to a later item) |
| dangling reference | M-4 `DANGLING_REFERENCE` |
| id not derived by D-051 | CH-1 `EVIDENCE_ID_INVALID` |
| unknown batch version, wrong order label | M-3 `EVIDENCE_BATCH_INVALID` |
| wrong `evidence_count`; incomplete or broken series | M-3 `EVIDENCE_BATCH_INVALID`; S-8.8 `BATCH_SEQUENCE` |
| non-canonical order or cut | S-8.8 `BATCH_NOT_CANONICAL` (on append and on open) |
| missing claim chunk; corrupt claim chunk | M-3 `REPORT_INVALID` |
| duplicated chunk reference | M-3 `REPORT_INVALID` |
| wrong chunk count; wrong total count | M-3 `REPORT_INVALID` |
| wrong ordering metadata (label; chunks out of order); non-canonical chunk cut | M-3 `REPORT_INVALID` |
| claim missing; evidence batch omitted; summary disagrees; another investigation | M-3 `REPORT_INVALID` |

## 6. Bounds [verified, `bounds.py` → `bounds.json`]

`bounds.py` reuses the Step 7 closure's maximal record builders (`../closure/storage_bounds.py`, kept unchanged as
the format-2 record) and replaces the evidence record by the batch record.

### Journal (512 MiB, not raised)

Counted: `investigation_created`; every execution record of every attempt (`A_max` = 3 per step, `A_max + F_max` = 9
for ACQUIRE, an interruption before each terminal record, deferrals included); `stale_detected`; the ACQUIRE and
EXTRACT observations of every attempt; report and verification records of every attempt; and the content of every
attempt of every step, also of attempts that failed after writing it (`A_max` copies). Batch records are bounded
rigorously: a closed part holds at least `(c − E − envelope) / 2` item bytes (MM 7.4, EB-4).

| | Content per attempt | Journal | Share of 512 MiB |
|---|---|---|---|
| Format 2 (`64e7aca`), typical, one run | 720,001 records | 478 MB | 89 % |
| Format 2, `A_max` attempts, typical / maximal | | 1.43 GB / 58.3 GB | 267 % / 10,851 % |
| Format 3 as implemented, typical | about 280,050 records, 184.5 MB | 554.8 MB | 103 % |
| Format 3 as implemented, maximal | 5.26 GB | 15.8 GB | 2,940 % |
| Format 3 with per-candidate records batched, typical | 55.8 kB | 1.3 MB | 0.25 % |
| Format 3 with per-candidate records batched, maximal | 2.49 MB | 8.6 MB | 1.6 % |

Evidence alone is now about 49 batch records (typical) and at most 3,364 (maximal) per run, instead of 510,000. The
remaining records are one per candidate: about 70,000 lookup observations, 70,000 claims, 70,000 decisions and up to
70,000 questions per run (the format-2 row above did not count questions). One attempt per step fits (186 MB, 35 %),
but the three attempts the plan allows do not, so the limit is **not proven**. Under the owner's rule this is
returned as an owner decision (section 7), not solved by raising the limit or capping the article.

### Per-file blobs (256 MiB)

| Blob | Bound | Share | Basis |
|---|---|---|---|
| Stage 03 extraction | 268,435,456 B | 100 % | Stored byte for byte (no wrapper). Stage 03 refuses a worker output over `MAX_OUTPUT_BYTES` = 256 MiB, and its `canonical_bytes` is the same encoding as Stage 04 `canon`, so it never exceeds the limit. Zero headroom by Stage 03's own cap. |
| ACQUIRE observation | 125,894,656 B | 47 % | **[condition]** Step 8 representation: capture document plus at most the 4 MiB source and 16 MiB render, each embedded as a JSON string (≤ 6 bytes per byte). The Stage 03 capture schema has no `maxItems` on `attempts`, `issues`, `failure_artifacts` (verified); measured documents are 3.8 to 5.2 kB, 64 KiB allowed. Over the limit is `BLOB_TOO_LARGE` (`STORAGE_ERROR`, fail closed). |
| LOOKUP observation | 102,311,086 B | 38 % | D-048 budget (`../closure/lookup_budget.json`) |
| evidence batch | 8,388,608 B | 3.1 % | ceiling; the largest legal item fits |
| evidence set (one claim) | 34,170,256 B | 12.7 % | at most every evidence id of the run |
| projection set | 4,690,256 B | 1.7 % | one per candidate |
| report claim chunk | 102,364,105 B | 38 % | ceiling, or one entry of its own: a maximal claim, decision, question, anchor and the checked sources of one lookup observation |
| report observations / positive-works chunk | 8,388,608 B | 3.1 % | ceiling |
| report manifest | 21,445,115 B | 8.0 % | fixed fields (< 64 KiB) plus one reference per chunk and per batch at the maxima |
| step output manifests, VALIDATE output | 65,536 B | 0.02 % | fixed shape |

### Total storage of one investigation

- **Mathematical worst case**: 50.2 TB (`5.02 × 10¹³` B): every attempt at every cap with every blob at its bound
  (every lookup at the D-048 budget, every claim naming every evidence id, every claim entry carrying a maximal
  lookup). Not reachable by a real article and index.
- **Operational bound**: 3.71 GB: one committed run at the Stage 03 caps with typical item sizes, lookups of the
  common shape (no record or one event), evidence sets of tens of ids, claim entries of about 1.5 kB, plus the full
  journal and the two largest blobs at their bounds. Equal content re-written by a retry adds nothing
  (content-addressed blobs).
- **Pinned index**: every lookup observation is within the D-048 budget by construction; the largest the pinned
  index gives for any key is recorded in `../closure/lookup_budget.json`.
- No global article cap is imposed. Disk exhaustion is `STORAGE_ERROR`, never a silent truncation (tested since
  Step 7).

## 7. Owner decision returned

**OD-J2: the per-candidate records.** Evidence batching alone does not bring the journal under 512 MiB with the three
attempts the plan allows (section 6). The remaining growth is one record per candidate: lookup observation, claim,
decision and question. The owner card of 2026-11-11 asks whether to batch those records the same way (recommended:
the journal is then proven at 1.6 % in the worst case) or to keep evidence-only batching with the journal NOT
PROVEN. Nothing here implements per-candidate batching. Step 8 should not start while this is open.

## 8. Performance [verified, `perf.py` → `perf_before.json`, `perf_after.json`]

One investigation runs end to end on synthetic adapters; DETECT commits `N` lookup-result evidence items and one
claim naming all of them. Same machine (4 vCPU, Python 3.12.3), one process. "Before" is the `64e7aca` worktree
(format 2, one record per item); "after" is this change (format 3) measured on the working tree before the commit
(only lint edits followed). Open time and memory are a read-only open that reads and checks every record and every
blob it names; memory is the Python heap peak (`tracemalloc`).

| N items | | Journal records | Journal bytes | Commit, ms per item | Open, s | Open, ms per item | Open peak memory | Whole run, s |
|---|---|---|---|---|---|---|---|---|
| 3,000 | before | 3,026 | 1,758,533 | 2.67 | 3.31 | 1.10 | 11.6 MB | 8.2 |
| 3,000 | after | 26 | 14,182 | 0.72 | 1.10 | 0.37 | 4.9 MB | 2.2 |
| 20,000 | before | 20,026 | 11,672,560 | 2.85 | 23.2 | 1.16 | 75.3 MB | 58.0 |
| 20,000 | after | 26 | 14,184 | 0.79 | 7.02 | 0.35 | 32.2 MB | 16.0 |
| 510,000 (all evidence of a run at the caps) | after | 40 | 20,953 | 0.73 | 173.1 | 0.34 | 300.5 MB | 371.8 |
| 510,000 | before [inference] | about 510,026 | about 298 MB | about 2.85 | about 590 | about 1.16 | about 1.9 GB | about 1,500 |

The 510,000 "before" row is extrapolated linearly from the measured 3,000 and 20,000 rows (cost per item, 3,766 B of
memory per item); it was not run. Append time per record: before 2.67 to 2.85 ms per record (one record per item);
after, one batch record commits about 21,000 items, so the per-record figure (19.6 s per record at 510,000) is not
comparable and the per-item cost is the measure. Batching cuts commit time per item by about 3.6×, open time per
item by about 3.3× and open memory per item by about 2.3× (20,000) to 6× (510,000, against the extrapolation). The
remaining cost is the jsonschema validation of every item, on commit and on open.

jsonschema was not optimized and no duplicate validation was removed.

## 9. Scientific invariance [verified]

`equivalence.py` runs five scenarios with the same synthetic adapters on the baseline tree (`64e7aca`, format 2)
and on this tree (format 3), and reduces each journal to its logical view: every committed evidence item (from its
record before, from its batch after), every claim, decision, question and observation, the lifecycle and the
outcome. The report blob is excluded: at `64e7aca` the fake ASSEMBLE wrote a placeholder; its structure is checked
by the D-054 tests. All five digests are equal (`equivalence_64e7aca.json`, `equivalence_after.json`), and the test
`test_logical_content_equals_the_accepted_baseline` pins the baseline digests. Candidates, evidence, dt-1,
precedence, dispositions, `NEEDS_RESOLUTION`, claim identity, the D-048 lookup and the Stage 03 extraction are not
changed; the Step 4 oracle is untouched (its tests pass unchanged).

| Scenario | Logical digest (before = after) |
|---|---|
| not found and retracted | `77916a7ebfa74c9e4cf43a5ccd049319997c3488cb7c1a7bd2095545da78d718` |
| identity conflict | `ac2f0e1643f2b29d107490a4b2ec66764bcc287a736ba1e305f7d8a24457c37b` |
| source contradiction beside a finding | `64bf58a5f910cb8943fda8390bc78504a85517fb89e6fa14e9110f738a187e0b` |
| lookup unavailable | `b0df2b0193c46c06c78e712d0323b231f1ab632685b28295f5bb0368f61afff7` |
| every positive class | `3bd6e925d55854e2ce4a3e457bd6219a300986d0e39bbf201811bc12e02519f0` |

## 10. Schema and format versions

| Item | Before (`64e7aca`) | After |
|---|---|---|
| journal record field `v` | 2 | 3; formats 1 and 2 refused, no migration |
| `journal-record` | 2.0.0 | 3.0.0 (`evidence_batch_recorded` replaces `evidence_recorded`) |
| `report` | 2.0.0 | 3.0.0 (manifest) |
| `evidence-batch`, `report-chunk` | absent | 1.0.0 |
| `claim`, `common`, `request`, `evidence-set`, `projection-set` | | unchanged |
| Stage 00 (`schemas/governance`), `schemas/contracts`, Stage 02 and Stage 03 schemas and code | | unchanged |

`StepRequest` gained `investigation` (key and id) so that ASSEMBLE can write them into the manifest.

## 11. Inherited baseline audit

Done through the maintenance path: no accepted-stage file was changed (`git diff 64e7aca` touches no file under
`src/citerift/wiki`, `src/citerift/retraction`, `src/citerift/governance`, `schemas/wiki`, `schemas/retraction`,
`schemas/governance`, `schemas/contracts` or `.github/`), so no maintenance transaction was needed.

| Id | Finding | Disposition |
|---|---|---|
| IF-7 | The Stage 03 capture schema leaves `attempts`, `issues` and `failure_artifacts` without `maxItems`, so the ACQUIRE observation has no schema bound. | Accepted residual; Step 8 design condition (section 6). An over-limit blob fails closed. A Stage 03 change would go through maintenance and is not proposed. |
| IF-8 | The Stage 03 extraction can be exactly `MAX_BLOB_BYTES`, with zero headroom. | Not a defect: Stage 03 refuses anything larger. Recorded. |
| IF-1 (Step 7) | jsonschema dominates append and open time. | Still true (section 8); not optimized, per the owner. |
| D-052, R6-12 | External checkpoint is design only; tamper evidence without an external anchor is not provided. | Unchanged. |

## 12. Tests

- **New `tests/stage04/test_d053_d054.py`** (55 tests): ordering, boundaries at N−1/N/N+1, the derived ceiling,
  commit and reopen across boundaries, refusal of non-canonical batches, non-authoritative batches of failed
  attempts, the nine crash points, every corruption case of section 5, the report build and graph checks, report
  reuse of the batches, and the five baseline equivalence digests.
- **Updated** for format 3 and the manifest: `controller_support.py` (the synthetic ASSEMBLE writes a true manifest
  and chunks; the synthetic adapters supply single evidence items), `memory_support.py`,
  `test_controller_adversarial.py`, `test_controller_crash.py`, `test_controller_differential.py` (a new classified
  category `BATCH_SERIES_CLOSED`, proven to be exactly S-8.8 `BATCH_SEQUENCE`; the frozen Step 4 model is
  unchanged), `test_controller_guard.py`, `test_controller_resolution_stale.py`, `test_memory_anchors.py`,
  `test_memory_journal.py`, `test_schemas_step5.py`, `test_step7_closure.py`. Record-size tests that relied on large
  evidence records now use the DETECT claim, and a regression test shows that item size no longer reaches the
  journal.
- Full suite before the commit: 2,835 passed, 0 skipped, on Python 3.12.3 (12 min 3 s) and 3.13.18 (11 min 8 s);
  the baseline had 2,775. `check-report` refused both reports only as `TEST_EVIDENCE_DIRTY` (uncommitted tree); the
  clean-tree run is CI.
