# Stage 04 Step 6: independent review of Investigation Memory

Status: Step 6 record (owner item 14). Date 2026-11-10.

## Independence: what it was and was not

The reviewer was a separate agent context (a subagent). It started without the author's conversation and was given
only the file list, the SPEC sections and the attack list of item 14. It changed no repository file and wrote its
proof scripts outside the repository. It was told to find defects, not to confirm the design.

Limits, stated plainly: the reviewer is the same model family as the author, it was briefed by the author, and the
author chose what to fix. This is a separate context, not an independent organisation or person. It does not replace
the formal Stage 12 independent review, which remains required.

## First pass: findings

The reviewer also found that the Memory tests failed when run in one order (24 failures in `test_memory_storage.py`
after `test_memory_journal.py`). The cause was finding R6-4: a test mutated a payload that aliased a shared constant.

| Id | Severity | Finding | How shown | Disposition |
|---|---|---|---|---|
| R6-1 | MEDIUM | `append` was not exception-safe: an interrupt between `write` and `fsync`, or a failure in the fold after the write, left a written line, an unpoisoned instance and a stale view, so the next append reused `seq` and the journal became CORRUPT | script | **Fixed.** Any failure before `fsync` returns truncates the journal back and `fsync`s; any failure after the record is built poisons the instance. Test `test_an_exception_of_any_type_during_append_commits_nothing` |
| R6-2 | MEDIUM | A complete, newline-terminated final record with a wrong digest is classified as a torn tail (SPEC 8.6) and silently removed on a writable open; a crash cannot produce such a line, so this catches only bit flips or tampering, which SPEC 10.2 calls CORRUPT | script | **Open: owner decision needed.** Implemented as SPEC 8.6 states; the SPEC is internally inconsistent (8.6 versus 10.2 "bit flip → CORRUPT" and S-8.3). Recommendation: a torn tail is only a final line without a newline; a complete final line with a parse or digest problem is CORRUPT. The original journal is always preserved in `journal.jsonl.torn-<k>`, so nothing is lost on disk today |
| R6-3 | MEDIUM | `put` of an already-published name returned without `fsync`, so a name from a failed earlier put could be named by a record before it was durable (power loss) | script (code path) | **Fixed.** The existing file and the blobs directory are `fsync`ed again. Test `test_an_existing_blob_is_made_durable_again_before_it_is_named` |
| R6-4 | MEDIUM | Caller objects were stored by reference (payloads, `created_payload` inputs): mutating them changed the view and `C(J)` but not the journal | script | **Fixed** for inputs and returned records (deep copies). Residual INFO: `mem.view` is the live fold; code that mutates it changes the in-memory view only, never the journal, and the next open rebuilds it. Test `test_records_never_alias_the_callers_objects` |
| R6-5 | MEDIUM | After a crash between the creation rename and the memory root `fsync`, recovery never `fsync`ed the memory root; `.creating-*` leftovers were not reported | reasoning; missing `fsync` shown | **Fixed.** A writable open `fsync`s blobs, the investigation directory and the memory root; `creation_leftovers()` lists leftovers. Test `test_writable_open_makes_directory_entries_durable_and_reports_leftovers` |
| R6-6 | LOW | A failed `fsync` raised `STORAGE_ERROR` but the record stayed and folded as committed, contrary to SPEC 10.2 | script | **Fixed** by the truncation of R6-1. Test `test_failed_write_poisons_the_instance_until_reopen` |
| R6-7 | LOW | If `lock` was unlinked while held, a second open created a new file and its own lock: two writers, a forked chain | script | **Fixed.** An open never creates the lock file (missing → `PATH_UNSAFE`); the inode is checked after `flock`; every append re-checks it (`LOCK_LOST`, instance poisoned). Test `test_an_unlinked_lock_file_does_not_admit_a_second_writer` |
| R6-8 | LOW | A read-only open (even of a CORRUPT investigation) created and rewrote the lock file | script | **Fixed.** Read-only opens use `O_RDONLY` and write nothing. Test `test_read_only_open_neither_creates_nor_rewrites_the_lock` |
| R6-9 | LOW | The journal bound was enforced on read but not on append, so a valid journal could grow into one that opens as CORRUPT | reasoning | **Fixed.** `JOURNAL_TOO_LARGE` before the write. Test `test_journal_size_bound_is_enforced_on_append` |
| R6-10 | LOW | Memory root owner not checked; mode checked on the path, not on the opened descriptor; investigation and blobs directory modes not checked | reasoning | **Fixed.** `uid == euid` on the root; owner and mode re-checked on the descriptors of the root, investigation and blobs directories. Test `test_directories_owned_by_another_user_are_refused` |
| R6-11 | LOW | A directory named like a journal temporary made the writable open raise a raw `OSError` | reasoning | **Fixed.** Only regular files and links are removed; others are left. Test `test_a_directory_named_like_a_temporary_is_left_and_does_not_break_open` |
| R6-12 | INFO | `MAX_DEPTH = 64` accepted 65 levels; non-mapping identifiers were skipped in the anchor parity check; the chain has no keyed or external head anchor; integers above 2^53 accepted; `fork` without `exec` shares the lock's file description | script / reasoning | Depth fixed (exactly 64 levels, leaves counted; test `test_nesting_bound_is_exactly_max_depth_levels`); malformed identifiers now fail closed (test `test_malformed_identifier_records_fail_closed`). The rest is recorded as a limit: a truncation at a record boundary or a rewritten suffix with recomputed digests is undetectable without an external anchor (by design of SPEC 8); large integers are within JSON and the record bound; Memory is not used across `fork` without `exec` |

## Areas where the reviewer found no defect

Canonical form and strict parsing (46 crafted byte inputs, including escaped duplicate keys, `1e16`, overflow,
underflow, 5 000-deep nesting); chain splice, reorder and replacement; corruption detection and the rule that a
corrupt journal is never repaired; the order of torn-tail repair and blob publication (apart from R6-3 and R6-5);
root binding (no forged or second bind found); the D-043 anchor (bounds, code-point and byte agreement at the
4 096-code-point checkpoints, digest before decoding, root before span, parity, the bundle chain); idempotency and
M-14; path handling.

## Second pass: re-check of the fixes

The same reviewer context re-ran its proof scripts against the fixed code. Its result: R6-1, R6-3, R6-5, R6-6, R6-7,
R6-8 and R6-12 fixed (by script); R6-9, R6-10 and R6-11 fixed (by reading the code); R6-4 fixed except the live
`mem.view` residual; R6-2 open as intended. Memory tests: 155 passed. New residuals it named:

- LOW: a short window remains between the lock identity check and the write, reachable only by someone deliberately
  replacing the lock file inside the private investigation directory.
- INFO: an investigation whose lock file was deleted cannot be opened, not even read-only, until the operator
  recreates an empty `lock` file in it. This fails closed; the procedure is: confirm no process uses the
  investigation, then create an empty file `lock` with mode `0600`.
- INFO: the depth rule counts leaves as levels; the docstring now says so.

Its verdict on the re-check: VERIFIED, with R6-2 open pending the owner's decision.
