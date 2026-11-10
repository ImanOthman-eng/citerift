# Stage 04 Step 6: Investigation Memory — design and evidence

Status: Step 6 record (owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPHFkw4RSkx4W14idXWvzLNy`, 2026-11-10). Scope:
Investigation Memory only, in `src/citerift/investigation/`. No Workflow Controller, Detection Engine, CLI or adapter
was written; Stage 02 and Stage 03 code and schemas are unchanged.

Companion records: `STEP6_BUILD_VS_ADOPT.md` (item 1), `STEP6_TRACEABILITY.md` (item 13),
`STEP6_FAULT_INJECTION.md` (item 10), `STEP6_INDEPENDENT_REVIEW.md` (item 14).

## 1. Modules

| Module | Responsibility |
|---|---|
| `canonical.py` | the one canonical serialization `canon`, the strict readers `loads_record` and `loads_blob`, `H`, the derived UUID |
| `ids.py` | genesis value, `config_digest`, `investigation_key`, `investigation_id`, `root_id`, record digest, live request key, the D-042 bound arithmetic |
| `fsutil.py` | directory-descriptor-relative opens with `O_NOFOLLOW`, non-blocking type checks, `fsync` of files and directories, memory root safety |
| `blobs.py` | the content-addressed blob store `blobs/<sha256>` |
| `journal.py` | journal parsing (records versus torn tail versus corruption), append, torn-tail repair |
| `lock.py` | the single-writer `flock` |
| `schemas.py` | the Step 5 record schema, loaded from `schemas/` |
| `fold.py` | validate-then-apply fold of every Memory invariant; derived views (step state, lifecycle, committed content, `C(J)`) |
| `memory.py` | the public API: `create`, `open`, `put_blob`, `append`, inspection |
| `anchors.py` | the D-043 unit anchor over retained Stage 03 bytes |
| `faults.py` | named persistence boundaries for fault injection (no effect unless a test installs a handler) |
| `errors.py` | stable error codes |

No module imports `citerift.governance` (S-15.1; `test_investigation_memory_does_not_import_governance`).

## 2. The authoritative store (item 2)

One directory per investigation, `<memory_root>/<investigation_key>/`, holding exactly `journal.jsonl`, `blobs/` and
`lock`. Everything else is derived by folding the journal: there is no index, cache, status file or other mutable
state. Two kinds of leftover can appear and are never authoritative: `journal.jsonl.torn-<k>` (a preserved torn
journal, kept) and orphan blobs (published, never named by a committed record; kept and reported, SPEC 10.2).

- The memory root must be absolute, a real directory (not a symbolic link), not writable by group or others, and
  outside any git working tree (S-15.3, MR-13). Every file is opened relative to a directory descriptor with
  `O_NOFOLLOW`; names are fixed constants or SHA-256 hex digests, never request text.
- New directories are `0700`, new files `0600`.
- Creation writes `journal.jsonl` (record 0), `blobs/` and `lock` in `.creating-<random>`, `fsync`s them, then
  renames the directory into place and `fsync`s the memory root. A crash before the rename leaves only the inert
  `.creating-*` directory (not removed automatically; see section 9).

## 3. Strict JSON and canonical serialization (items 3 and 4)

`canon(x)` = `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` in UTF-8, the
encoding Stages 02 and 03 already use. It is the only serializer for records, blobs and hashes.

Readers never coerce. `loads_record` (journal records) refuses any non-integer number token (`1.0`, `1e0`, `1E2`,
`-0.0`, `1e400`), `NaN`, `Infinity`, duplicate keys at any depth, invalid UTF-8, UTF-8-encoded surrogates, lone
surrogate escapes, a byte-order mark, nesting deeper than 64, and any bytes that are not exactly the canonical
encoding of the parsed value (spaces, key order, `é`-style escapes, `-0`, trailing newline). `loads_blob` is
the same except that finite floats are allowed (MM 2.1 allows them in engine outputs). An unsupported journal format
version is refused as `JOURNAL_VERSION_UNSUPPORTED` (S-8.7); the schema fixes `schema_version`.

Determinism: `test_canonical_output_is_identical_across_processes_hash_seeds_and_locales` runs the encoder in four
processes with different `PYTHONHASHSEED` and locale values and compares the bytes, `H` and the record digest.

## 4. Blob publication (item 5)

1. create `blobs/.tmp-<pid>-<random>` with `O_CREAT | O_EXCL | O_NOFOLLOW`, mode `0600`;
2. write all bytes; `fsync` the file;
3. read the temporary file back and verify its SHA-256;
4. publish with `link(tmp, <sha256>)`;
5. unlink the temporary name; `fsync` the `blobs` directory;
6. return the digest. Only then may a record name the blob; `append` re-verifies every blob a record names (M-3, M-5).

An existing name is verified (regular file, hashes to its name, canonical JSON) and the put succeeds without writing.
An existing name whose bytes do not hash to it is `BLOB_CORRUPT`: reported, never overwritten, never replaced.

Deviation from the owner's wording, stricter: the owner listed "atomic rename/replace". Step 6 uses `link`, which is
equally atomic but **fails** when the name exists, where `rename` would silently replace it. A replacing primitive
would break "incompatible existing bytes are never overwritten" under a race between two publishers; with `link` the
loser gets `FileExistsError` and verifies the winner's file instead. `test_concurrent_blob_publication_is_safe` runs
eight processes publishing the same 200 kB blob and 20 own blobs each at once: one complete file per name, all
verified, no temporaries.

## 5. Journal (item 6)

Each line is `canon(record)` + `\n`. A record has `v`, `seq`, `at`, `kind`, `step`, `attempt`, `root_id`, `payload`,
`prev` and `digest`. `prev` of record 0 is the genesis value `H("citerift-journal-genesis/1", key)`; every other
`prev` is the previous record's `digest`; `digest` is the record digest over every other field. Memory sets `seq`,
`prev`, `at` (clamped so it never decreases, M-1), `root_id` (null before the bind, the bound root after it) and
`digest`; the caller supplies `kind`, `step`, `attempt` and `payload`.

`append` builds the record, refuses one over 1 MiB (`RECORD_TOO_LARGE`), runs every check of the fold on it without
changing state (`Folder.check`), then writes the whole line with one `write` on an `O_APPEND` descriptor and `fsync`s
it. Only after the `fsync` does the in-memory fold advance. If anything fails before the `fsync` returns (an
`OSError`, or any other exception such as an interrupt), the journal is truncated back to its length before the
append and `fsync`ed, so a failed append commits nothing (SPEC 10.2); `OSError` becomes `STORAGE_ERROR`. Any failure
after the record was built poisons the instance (no further writes; reopen to recover), so a later append can never
reuse a sequence number. Before writing, `append` also checks that the lock file still designates the held lock
(`LOCK_LOST` otherwise) and that the journal stays within its bound (`JOURNAL_TOO_LARGE`). Records and payloads are
deep-copied in and out, so no caller object aliases the view. A record refused by a check is never written
(`AppendRefused` names the invariant).

Committed versus uncommitted: content records of an attempt count only when that attempt ends in `step_succeeded`
(M-6). Until then they are pending; a later attempt cannot see or refer to them, and may define the same ids again.

History is never repaired in place: the only change Memory ever makes to existing journal bytes is the removal of a
torn final line, after the whole journal has been preserved (section 6).

## 6. Torn tail versus CORRUPT (item 7)

`parse_journal` splits the bytes into lines. Since owner decision D-044 (corrective closure, see
`STEP6_D044_CLOSURE.md`), only final bytes **without the terminating newline** are a torn tail (an incomplete
physical record). Every newline-terminated line is a complete record, and any defect in it, last line or not, is
`CORRUPT` (M-2). Before D-044 (commit 6fd799d) a newline-terminated final line that did not parse or had a wrong
digest was also treated as torn (review finding R6-2). Every
record of the prefix is then folded with every invariant and every named blob verified **before anything is
changed**. Only when the prefix is valid, and only on a writable open, is a torn tail removed:

1. copy the whole journal to `journal.jsonl.torn-<k>` (new file, `O_EXCL`), read it back, compare byte for byte,
   `fsync` the directory;
2. write the valid prefix to `.journal.tmp-<random>`, read it back and compare;
3. rename it over `journal.jsonl`, `fsync` the directory; re-read and require exactly the validated prefix.

A read-only open reports the torn tail (`torn_tail`) and changes nothing. A `CORRUPT` investigation raises
`CorruptInvestigation` (stable code `CORRUPT`, `cause` names the violated invariant) and nothing is written, copied
or removed, not even its torn tail or leftover temporaries (`test_corrupt_history_with_a_torn_tail_is_not_repaired`).

Order: validate the whole prefix first, repair only a valid prefix, so a corrupt journal is never modified. D-044
approved this order and SPEC 10.1 now states it.

Evidence for the owner's list (all in `tests/stage04/test_memory_journal.py`):

| Case | Classified as | Test |
|---|---|---|
| truncated final line | torn; preserved, removed, resumable | `test_torn_tail_is_preserved_and_removed[truncated final line]` |
| invalid final JSON without its newline | torn | `…[invalid final JSON without its newline]`, `…[final line zero-filled, no newline]` |
| invalid final JSON, newline-terminated | CORRUPT M-2 (D-044) | `test_d044_complete_defective_records_are_corrupt` |
| final record with a wrong digest, newline-terminated | CORRUPT M-2 (D-044) | `test_d044_r6_2_complete_final_record_with_wrong_digest_is_corrupt` |
| modified historical record | CORRUPT M-2, journal unchanged | `test_corruption_is_distinct_from_a_torn_tail[modified historical record]`, `test_corrupt_investigation_is_never_repaired` |
| broken prev | CORRUPT M-2 | `…[broken prev]` |
| wrong digest | CORRUPT M-2 | `…[wrong digest in history]` |
| torn line before the end | CORRUPT M-2 | `…[torn line before the end]` |
| missing blob | CORRUPT (`BLOB_MISSING`) | `test_missing_or_corrupted_blob_is_corrupt` |
| corrupted blob | CORRUPT (`BLOB_CORRUPT`) | `test_missing_or_corrupted_blob_is_corrupt`, `test_blob_under_its_name_that_is_not_canonical_is_corrupt` |

## 7. Locking (item 9)

`flock(LOCK_EX | LOCK_NB)` on `lock`, taken by every open, read-only included (SPEC 10.1); a held lock gives
`INVESTIGATION_BUSY` and nothing is written. Ownership is the kernel lock alone: the file's content (`pid … since …`)
is informational and never read. The lock file is created once, with the investigation; an open never recreates it
and refuses an investigation whose lock file is missing (`PATH_UNSAFE`), because recreating it could admit a second
writer while a process still holds a lock on the unlinked file. After `flock` the descriptor's inode is compared with
the name's, and every append re-checks it (`LOCK_LOST`). A read-only open uses `O_RDONLY` and writes nothing. The
descriptor is `O_CLOEXEC`. There is no lease, timeout or heartbeat. `read_journal` is the lockless reader: it sees a consistent prefix (a partially written final
line is at most a torn tail, never a record), and blob names appear only by an atomic `link` of a verified file.

| Owner case | Result | Test |
|---|---|---|
| second writer refused | `INVESTIGATION_BUSY` for writable open, read-only open and `create` | `test_second_writer_is_refused_and_lock_released_after_close` |
| released after normal exit | yes: `close`, and process exit without `close` | `test_lock_is_released_when_the_holder_ends[close]`, `[exit]` |
| released after a killed process | yes: child killed with `SIGKILL` | `test_lock_is_released_when_the_holder_ends[SIGKILL]` |
| stale lock contents do not imply ownership | forged pid of this process, pid 1, garbage, empty: all open; an absent file is refused, never recreated | `test_lock_file_contents_do_not_imply_ownership`, `test_an_unlinked_lock_file_does_not_admit_a_second_writer` |
| concurrent blob publication safe | 8 processes, 161 names, all verified, no temporaries | `test_concurrent_blob_publication_is_safe` |
| readers never see partial data | lockless reader loops while a writer publishes 300 kB blobs and appends 20 records | `test_lockless_readers_never_see_partial_data` |

Limitation: `flock` is local to one kernel; network file systems are not supported (RA R4-26).

## 8. D-043 unit anchor (owner decision; SR-03 option A)

`unit_span_sha256 = SHA-256(source_artifact_bytes[byte_start:byte_end])`, half-open, over the exact retained Stage 03
source artifact. It is a Stage 04 derived value, not a Stage 03 field; Stage 03 is unchanged and is read only through
its accepted functions `open_bundle` and `read_artifact`. In order: the source artifact's digest is verified; the
extraction's `capture_sha256` must equal the bound root's, and its `source_artifact` must name this artifact;
`0 <= byte_start <= byte_end <= len(source)` and `0 <= cp_start <= cp_end <= len(text)`; the byte offsets must be the
UTF-8 offsets of the code-point offsets (so a span cannot split a character); then the hash is taken. Every Stage 03
identifier whose exact anchor (`source`, `$defs/anchor`) covers the same byte span must have `raw_sha256` equal to
the derived hash. Any mismatch raises `SpanError` (`SOURCE_DIGEST_MISMATCH`, `ROOT_IDENTITY_MISMATCH`,
`SPAN_INVALID`, `ANCHOR_MISMATCH`); nothing falls back to another identity. `verify_unit_span` recomputes it for
VERIFY.

Tests (`test_memory_anchors.py`) use the observed Stage 03 fixtures `ar-76190003` (26 of 32 unit spans multibyte)
and `en-1372543632`: ASCII spans, Arabic multibyte spans (the byte slice equals the UTF-8 encoding of the code-point
slice), the empty span, out-of-range and reversed spans, spans ending inside a two-byte letter, code-point and byte
spans that disagree, booleans and floats as offsets, a modified source (in memory and in a copied bundle), another
root's capture, another extraction's source artifact, identifier parity on all 20 observed identifier anchors, a
forced parity mismatch, and replay: the hash is recorded in a unit evidence record, the investigation is reopened,
and `verify_unit_span` recomputes it from the retained bundle (and refuses a tampered value).

Defect found and fixed while writing these tests: the first version of `anchors.py` looked for the identifier anchor
under a field named `anchor`; in Stage 03 output the anchor is the identifier's `source` (`anchor` is only the
schema `$defs` name). The parity check therefore never fired on real data. Fixed before commit; the observed-fixture
parity test would have caught it.

## 9. Decisions, limits and findings for the owner

- **F-1 (review finding R6-2): resolved by owner decision D-044.** A complete (newline-terminated) final record
  that fails validation is now `CORRUPT`; only final bytes without the newline are a torn tail.
- **F-2 (SPEC 10.1 order): approved by D-044.** Validation precedes repair; SPEC 10.1 updated.
- **Provisional ceilings (D-044):** record 1 MiB (`RECORD_TOO_LARGE`) and journal 512 MiB are defensive
  implementation ceilings, not justified final values. A resource-bound argument from the Stage 04 model is owed
  before the Stage 04 freeze (at the latest in Step 7). The blob bound, 256 MiB, is the Stage 03 extraction bound.
- **Not checked by Memory, left to Step 7 (controller, DETECT, VERIFY):** derivation of evidence, claim, decision and
  question ids (the SPEC gives no tags), transition legality and budgets (W-*, T-*), `not_before`, staleness
  (S-10.1), closing an open attempt on resume (W-6), and `step_failed(STORAGE_ERROR)` after a failed write.
- **Leftover `.creating-*` directories** from a crash before the creation rename are inert (never opened as an
  investigation). They are reported by `InvestigationMemory.creation_leftovers` and not removed automatically,
  because removing them safely would need a lock on the memory root, which SPEC 10.1 does not define.
- **Memory root and directory checks** run on the opened descriptors (owner is this user, no group or other write),
  and a writable open `fsync`s the blobs directory, the investigation directory and the memory root before the first
  append, so a rename or link left undurable by a crash is made durable.
- **Fault injection is process death**, not power loss: the page cache survives, so it cannot show what a power
  failure between `write` and `fsync` would lose. That case rests on the `fsync` order above (file before link,
  directory after link, journal line before the in-memory commit).
- **No dependency adopted** (`STEP6_BUILD_VS_ADOPT.md`).
