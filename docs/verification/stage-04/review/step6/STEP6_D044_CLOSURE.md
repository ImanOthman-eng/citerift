# Stage 04 Step 6: corrective closure (owner decision D-044)

Status: record of the corrective closure the owner authorized when conditionally accepting Step 6 at
`6fd799db0234fb9fcef42b7a9618eafe409833f1` (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPEUWjPwtyadJ3r35wXrmJrf`,
2026-11-10T17:30:22Z). Step 7 is not started.

## 1. R6-2 fail-first evidence (before any implementation change)

Script `r6_2_fail_first.py` (this directory) builds the synthetic investigation, changes one hex digit of the stored
digest of the complete, newline-terminated final record, and opens it read-only and then writable.

Output at `6fd799d` (unchanged implementation):

```
records stored: 21; final record ends with newline: True
journal sha256 before open: c7e83b77d1abb5de7c92275406b79a924edd6b703cf187335302ef226e082ca6
read-only open: ACCEPTED, records folded: 20, torn tail: 'digest does not match the record'
writable open: ACCEPTED, records folded: 20, torn tail: 'digest does not match the record'
journal unchanged after opens: False; records now stored: 20
preserved copies: ['journal.jsonl.torn-0']
```

Both opens accepted the journal: the defective record was classified as a torn tail, and the writable open removed
it (20 records remained; the original was kept only as `journal.jsonl.torn-0`). The new regression tests, run against
the unchanged implementation, gave 4 failed and 9 passed:

```
FAILED tests/stage04/test_memory_journal.py::test_d044_r6_2_complete_final_record_with_wrong_digest_is_corrupt
FAILED tests/stage04/test_memory_journal.py::test_d044_complete_defective_records_are_corrupt[malformed JSON, newline-terminated]
FAILED tests/stage04/test_memory_journal.py::test_d044_complete_defective_records_are_corrupt[non-canonical JSON, newline-terminated]
FAILED tests/stage04/test_memory_journal.py::test_d044_complete_defective_records_are_corrupt[zero bytes, newline-terminated]
4 failed, 9 passed, 47 deselected in 10.25s
```

(The `prev`, schema and invariant cases already failed closed at `6fd799d`, because the fold checks them; the parse,
canonical-form and digest checks of a newline-terminated final line were the ones that fell through to "torn".)

Output after the correction:

```
records stored: 21; final record ends with newline: True
journal sha256 before open: 29fec8abcf27ea9d1f6c7999d5bffdf2c049433b522a5203dc5c7755978a5714
read-only open: CORRUPT (JOURNAL_CORRUPT: M-2 at seq 20: line 20: digest does not match the record)
writable open: CORRUPT (JOURNAL_CORRUPT: M-2 at seq 20: line 20: digest does not match the record)
journal unchanged after opens: True; records now stored: 21
preserved copies: []
```

(The journal digest differs between runs because each run uses a new temporary memory root, which the creation
record names.)

## 2. Corrected classification

| Final bytes | Classification |
|---|---|
| no terminating newline (truncated JSON, one byte, zero bytes, or a complete canonical record whose newline is missing) | torn tail: an interrupted append, never committed. Removed by Copy → Verify → Preserve only on a writable open and only after the whole prefix validated |
| newline-terminated and not strict canonical JSON (malformed, non-canonical, zero bytes) | `CORRUPT` (M-2) |
| newline-terminated canonical record with a wrong digest | `CORRUPT` (M-2) |
| newline-terminated record with a wrong `prev`, a schema violation or an invariant violation, or naming a missing or invalid blob | `CORRUPT` (M-2, `SCHEMA`, the invariant, or `BLOB_*`) |
| any defect in a non-final record | `CORRUPT` |
| valid complete final record | valid |

Implementation: `journal.parse_journal` now returns a torn tail only when the final bytes have no newline; a problem
in any newline-terminated line raises M-2 `JOURNAL_CORRUPT`. `memory.open` already validated the whole prefix before
any change; that order is unchanged and now specified.

## 3. SPEC changes

- 8.6 Validity: only an incomplete physical record (no terminating newline) is a torn tail; a complete record that
  fails validation is `CORRUPT`, final or not.
- 10.1: steps renumbered so the order reads: take the lock; read and identify a candidate incomplete tail; validate the
  entire prefix (any failure: `CORRUPT`, nothing changed); only then, on a writable open, Copy → Verify → Preserve,
  `fsync`, re-read; fold; recompute step keys; continue.
- 10.2: the "Torn final record" row names "final bytes without a newline" and "prefix validated, then …".
- `DECISIONS.md`: D-044.

## 4. Tests added or changed (`tests/stage04/test_memory_journal.py`)

| Owner case | Test |
|---|---|
| 1 truncated final JSON, no newline → torn | `test_d044_incomplete_final_line_is_a_torn_tail[truncated final JSON, no newline]` |
| 2 complete canonical JSON, newline missing → torn | `…[complete canonical record, newline missing]` |
| 3 newline-terminated record, wrong digest → CORRUPT | `test_d044_r6_2_complete_final_record_with_wrong_digest_is_corrupt` (the fail-first regression) |
| 4 newline-terminated malformed or non-canonical JSON → CORRUPT | `test_d044_complete_defective_records_are_corrupt[malformed JSON, …]`, `[non-canonical JSON, …]`, `[zero bytes, …]` |
| 5 valid final record with incorrect `prev` → CORRUPT | `…[valid digest over a wrong prev]` |
| 6 corruption in a middle record → CORRUPT | `…[middle record corrupt]` |
| 7 legitimate complete final record → valid | `test_d044_legitimate_complete_final_record_is_valid` |
| 8 interrupted append recovery still works | `test_d044_incomplete_final_line_is_a_torn_tail` (writable reopen, preserved copy, resume to DETECT), `test_torn_tail_is_preserved_and_removed`, and every `journal.during_append` run of `test_memory_faults.py` |
| order: corrupt prefix before an incomplete tail → no mutation | `test_d044_corrupt_prefix_before_an_incomplete_tail_is_not_mutated` |

Also covered: schema and invariant violations in a newline-terminated final record. Changed:
`test_torn_tail_is_preserved_and_removed` no longer lists the two cases that D-044 reclassifies (newline-terminated
invalid JSON, wrong final digest); its remaining cases lack the newline.

## 5. Resource ceilings: provisional

`MAX_RECORD_BYTES` (1 MiB) and `MAX_JOURNAL_BYTES` (512 MiB) stay as defensive implementation ceilings. They are not
justified final values. The resource-bound argument (Stage 03 `max_refs` and `max_candidates`, lookup count, evidence,
claims, decisions and questions, attempts and deferrals, records per step, the encoded size of each record family,
report and blob separation) has not been made yet; it needs the full controller record bound and is owed before the
Stage 04 freeze, at the latest in Step 7, with one of the four conclusions the owner listed. No number was changed.

## 6. Accepted residual limitations (unchanged)

Process-death, not power-loss, fault injection; `flock` on local POSIX file systems only; `.creating-*` leftovers
reported, not deleted; a deleted lock file causes fail-closed refusal; the Step 6 reviewer was a separate context,
not an independent one (the later independent review remains mandatory). None was "improved" by adding recovery.

## 7. Inherited Stage 01 governance defect: analysis, stopped at the decision boundary

Fact. `governance/stage_registry.json`, stage `01`: `status` `ACCEPTED_CLOSED`; `implementation` and `verification`
revision `85da719ac43fc46170310b225c9190b63a046df8`; `HANDOFF.md` retained and in the evidence manifest; acceptance
recorded (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yP4bEH9RimJDhvHy8S2ABHcU`, 2026-10-27T18:44:05Z, history entry 24).
Its `notes` field still reads: "Executed by a separate external agent. The owner reports the investigation was
reported externally; its handoff has not been supplied to this repository and none of its findings are accepted. The
exact evidence file set is fixed when the owner delivers the handoff." The note was written with the Stage 00
foundation (commit `b13f910`, 2026-10-25), before the handoff existed, and `render-status` copies it into
`PROJECT_STATUS.md` under "Stage notes". It is the only stage with a note.

**No change was made.** Reasons the existing commands cannot perform it:

1. No `citerift-gov` command writes `notes`. The field is read only by `render-status` (`orchestrator.py`, "Stage
   notes"); `transition`, `blocker`, `amend` and `maintenance` never touch it.
2. `amend --kind correction` is a behaviour or contract change that leads to reopening and re-acceptance (GOVERNANCE.md,
   "Changing an accepted stage"); using it would reopen Stage 01, which the owner excluded.
3. `amend --kind enhancement` records a new revision of the stage's owned content with a passing test report; Stage 01
   owns no paths, and an amendment record would not change `notes` either, so the stale text would remain.
4. `maintenance` is a transaction over a stage's owned files; same limits.
5. A hand edit of the registry is possible, and `check` would not report it (`notes` is a free string in the schema,
   not covered by invariants 1–7). GOVERNANCE.md calls hand edits "detected, not prevented"; here it would not even be
   detected. That is why the owner's instruction not to edit it by hand without a governance path matters.

Exact minimal proposed diff (not applied):

```diff
--- governance/stage_registry.json (stage "01")
-      "notes": "Executed by a separate external agent. The owner reports the investigation was reported externally; its handoff has not been supplied to this repository and none of its findings are accepted. The exact evidence file set is fixed when the owner delivers the handoff."
+      "notes": "Executed by a separate external agent. Its handoff (docs/verification/stage-01/HANDOFF.md) and evidence were supplied, verified at 85da719ac43f and accepted by the owner on 2026-10-27 (acceptance; history entry 24). This replaces a note of 2026-10-25 written before the handoff existed (owner decision D-0xx)."
```

plus the matching re-rendered line of `PROJECT_STATUS.md` (`citerift-gov render-status`) and a `DECISIONS.md` entry
citing the owner's authorization. Nothing else changes: not the authorization scope (its "no Stage 01 findings are
accepted" was true when recorded on 2026-10-25 and stays as history), not the revisions, gates, acceptance or history.
A smaller alternative is to delete the `notes` key (it is optional), which also removes the "Stage notes" section.

Recommendation: a **one-time, owner-authorized metadata correction** is safer now than a new capability. A new
`citerift-gov` command would change `src/citerift/governance` and `schemas/governance`, which are Stage 00 owned paths:
Stage 00 would need an enhancement amendment or a maintenance transaction, a larger and riskier change than one string,
for a field used once. The one-time correction is a reviewed registry diff, cites the owner's words in `DECISIONS.md`,
and keeps `check` and `render-status --check` at 0 errors.

Tests to prevent a recurrence (a Stage 00 enhancement, so only if the owner authorizes it): structural rather than
phrase matching, which would be fragile.
- Give a note a recording time (`notes: {text, recorded_at}`), and have `check` warn (`NOTE_PREDATES_STATE`) when a
  stage's note was recorded before its latest history entry, so every later transition forces a review of the note.
- `render-status` prints a note with its recording date, so a reader sees how old it is.
- Tests: a note older than the last transition produces the warning; a note re-recorded after it does not; a
  transition through `citerift-gov` does not silently keep a predating note without the warning; rendering shows the
  date.

Owner decision needed: (a) apply the one-time correction above (replace or delete the note), (b) authorize the Stage
00 capability and tests instead, or (c) both.
