# Stage 04 Step 6: fault-injection matrix and results

Status: Step 6 record (owner item 10). Produced by `tests/stage04/test_memory_faults.py` with
`CITERIFT_FAULT_MATRIX=<file>`; the table below is generated from that file.

## Method

The workload is the synthetic plan of `tests/stage04/memory_support.py`: create the investigation, then VALIDATE,
ACQUIRE (binding the root), EXTRACT, NORMALIZE (two evidence records), LOOKUP, DETECT (evidence, claim, decision):
21 records and 6 distinct blobs (other puts of the same bytes are idempotent and reach no write boundary). It is not
the Workflow Controller.

Production code calls `faults.point(name)` at 14 named boundaries. A reference run counts how often each is reached.
Then, for every boundary and every occurrence (and, at the two `during` boundaries, for each partial-write size), a
forked child runs the workload and dies there with `os._exit` (after writing the stated prefix of the pending bytes
through the production descriptor). The parent then checks, for that crash:

1. a writable reopen succeeds (no `CORRUPT`);
2. the stored journal is a byte-equal prefix of the reference journal (no history rewrite);
3. the number of records equals 1 + the number of appends whose line was completely written before the crash (no
   false committed success, no lost record);
4. a torn tail is preserved in `journal.jsonl.torn-0` and removed exactly when a partial line was written;
5. every blob a record names verifies; every blob present is one the reference run wrote (orphans are kept);
6. no temporary file (`blobs/.tmp-*`, `.journal.tmp-*`) remains;
7. resuming with `drive` gives the reference content digest `C(J)`, the same root, the reference blob set with no
   orphan left, exactly one succeeded attempt per step, and keeps the pre-resume journal as its prefix.

The owner's boundary list maps to the points as follows: before / during / after blob write → `blob.before_write`,
`blob.during_write`, `blob.after_fsync`; before rename → `blob.before_link` (publication is `link`, see
`STEP6_MEMORY_EVIDENCE.md` section 4); after rename before directory fsync → `blob.after_link`; after publication
before append → `blob.published` and `journal.before_append`; during append → `journal.during_append`; after append
before fsync → `journal.after_write`; after fsync → `journal.after_fsync`; between content and `step_succeeded` →
the `journal.*` occurrences whose record is a `step_succeeded` (every occurrence is enumerated). Creation and
torn-tail repair have their own boundaries.

## Results

| Boundary | Partial write | Crash runs | Records after reopen (min..max) | Runs with a torn tail preserved | Runs with orphan blobs | Result |
|---|---|---|---|---|---|---|
| `create.prepared` | — | 1 | 1..1 | 0 | 0 | all checks pass |
| `create.renamed` | — | 1 | 1..1 | 0 | 0 | all checks pass |
| `blob.before_write` | — | 6 | 2..20 | 0 | 0 | all checks pass |
| `blob.during_write` | half | 6 | 2..20 | 0 | 0 | all checks pass |
| `blob.after_fsync` | — | 6 | 2..20 | 0 | 0 | all checks pass |
| `blob.before_link` | — | 6 | 2..20 | 0 | 0 | all checks pass |
| `blob.after_link` | — | 6 | 2..20 | 0 | 6 | all checks pass |
| `blob.published` | — | 6 | 2..20 | 0 | 6 | all checks pass |
| `journal.before_append` | — | 20 | 1..20 | 0 | 6 | all checks pass |
| `journal.during_append` | one byte | 20 | 1..20 | 20 | 6 | all checks pass |
| `journal.during_append` | half | 20 | 1..20 | 20 | 6 | all checks pass |
| `journal.during_append` | all but the newline | 20 | 1..20 | 20 | 6 | all checks pass |
| `journal.after_write` | — | 20 | 2..21 | 0 | 0 | all checks pass |
| `journal.after_fsync` | — | 20 | 2..21 | 0 | 0 | all checks pass |
| `torn.copied` | — | 1 | n/a (repair) | 1 | 0 | all checks pass |
| `torn.prefix_written` | — | 1 | n/a (repair) | 1 | 0 | all checks pass |

Total crash runs recorded: 160

In addition, `test_crash_during_creation_leaves_no_half_investigation` crashes at `create.prepared` (no investigation
exists, only an inert `.creating-*` directory) and at `create.renamed` (the investigation exists and is complete);
both then create or open, run to completion and reach the reference `C(J)`. `test_every_boundary_is_exercised`
fails if the workload stops reaching any boundary.

Two deliberate mutations were run to check that the harness detects defects (not committed): skipping the removal of
blob temporaries on reopen (failed at `blob.during_write` and `blob.after_fsync`), and keeping one byte of the torn
line in the repaired prefix (failed at `journal.during_append`).

## Limits

- Process death only. The page cache survives a killed process, so a crash at `journal.after_write` (line written,
  not yet `fsync`ed) still finds the line; a power loss there could lose it. That case is covered by argument, not by
  test: the record is not reported committed to the caller before `fsync` returns, and resume handles either outcome.
- No kernel or file-system fault injection (ALICE/CrashMonkey style), see `STEP6_BUILD_VS_ADOPT.md`.
- `ENOSPC` and other write errors are covered by the `STORAGE_ERROR` path (the instance refuses further writes); no
  test fills a disk.
