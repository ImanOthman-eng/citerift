# Stage 04 Step 6: focused re-review of the D-044 change

Status: Step 6 record. Date 2026-11-10. Owner instruction: message `cmsg_018VCB51nDHP6HXmLU4ea5yPWUXdMpviEn4TgnzgKGQCtK`
(the D-045 message), section "Focused D-044 re-review before Step 7".

## Scope and independence

The change reviewed is D-044 at `cf2e411` (`git diff 6fd799d cf2e411`): SPEC 8.6, 10.1, 10.2, `journal.parse_journal`,
torn-tail recovery in `memory.open`, the R6-2 fail-first evidence and the 13 D-044 tests. The reviewer was a fresh
agent context (a subagent), briefed only with the file list, D-044 and the owner's eight challenge points, told to
find defects and to change no repository file; it wrote its probes outside the repository. It then re-checked the
fixes twice.

Limits: the reviewer is the same model family as the author and was briefed by the author, who chose the fixes. This
is a focused re-review of one change. It is **not** the formal Stage 12 independent review, which remains required.

## The owner's eight questions

| # | Question | Verdict | Evidence |
|---|---|---|---|
| 1 | Is "no final newline" a precise enough physical definition of a candidate torn tail? | **No, it was too broad** (D44-R2, R2a, R2b); now narrowed to bytes an interrupted append can leave | reviewer probes A–C, b1–b9, `max_boundary.py`; tests below |
| 2 | Can a newline-terminated invalid record still be silently removed? | No defect: any problem with a complete line raises `CORRUPT` in both open modes; the fold applies every record | reviewer cases 1d, 1f, 1h, 1i, 2a; 13 D-044 tests |
| 3 | Does a corrupt prefix before an incomplete tail cause zero mutation? | Journal, blobs, listing, temporaries and torn copies unchanged. The lock file's informational content is rewritten by a writable open (D44-R3, documented) | reviewer case 3a, `lock_probe.py` |
| 4 | Is Copy → Verify → Preserve done only after prefix validity is established? | Yes (fold, including blob checks, before `repair_torn_tail`), but no test proved it (D44-R1, now tested) | mutant with repair before fold |
| 5 | Does a read-only open ever mutate? | No: sha256, `mtime_ns` and inode of every entry and of the directory unchanged in 15 cases | reviewer `edge_cases.py` |
| 6 | Can a writable open convert corruption into recovery? | Yes, only through D44-R2 (a committed final record whose newline byte is damaged was dropped as torn). Fixed | probe B |
| 7 | Does interrupted-append recovery still work? | Yes: 626 cuts (inside every record and at every byte of the final record) all recovered to the reference content digest, before and after the fixes | `cut_sweep.py`, `cut_sweep2.py` |
| 8 | Did D-044 regress M-1/M-2 or crash recovery? | No | Memory tests, fault-injection tests, cut sweep |

## Findings and dispositions

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| D44-R1 | MEDIUM (test coverage) | No test showed the recovery order when the prefix defect is visible only to the fold: both corrupt-prefix tests used a digest flip, which `parse_journal` rejects before any repair. A mutant that repairs before folding passed all 167 Memory tests | **Fixed.** New test `test_d044_fold_only_prefix_defect_before_an_incomplete_tail_is_not_mutated` (missing blob + incomplete tail + stale temporary). It fails on the mutant and passes on the code |
| D44-R2 | LOW (integrity) | "No final newline ⇒ torn" accepted bytes no append can leave: a committed, `fsync`ed final record whose newline byte was damaged (0x0A → 0x0B) was dropped as torn and the step went back to `running`; also a final record followed by a stray byte, and a tail longer than any record. This contradicted SPEC 10.2 ("bit flip … `CORRUPT`") | **Fixed** in `journal._tail_problem` (below) |
| D44-R2a | LOW (recovery) | Found in the first re-check: the size limit was off by one. An append of a line of exactly `MAX_RECORD_BYTES` writes `MAX_RECORD_BYTES + 1` bytes; a zero-filled crash of it was called `CORRUPT` | **Fixed:** the limit is `MAX_RECORD_BYTES + 1` |
| D44-R2b | LOW (integrity) | Found in the first re-check: tails no append can leave were still torn: garbage with a zero byte inside, a complete record + zero byte + junk, a complete value that is not a record, a complete record with a wrong digest, a copy of an earlier record | **Fixed:** first byte `{` or zero; a complete value must be followed only by zero bytes and must be the valid next record |
| D44-R3 | LOW (wording) | A writable open rewrites the lock file's informational content (pid, time) before validation, so "nothing changed" on `CORRUPT` was not literally true. Behaviour existed before D-044 (`lock.py` unchanged) | **Fixed in wording** (SPEC 10.1 step 3, `STEP6_D044_CLOSURE.md`): the journal, blobs and temporaries are unchanged; the lock content is the one write. Behaviour not changed |
| D44-R4 | INFO | `journal.py` docstring said the digest is checked by the fold; `parse_journal` checks it first | **Fixed** (docstring) |
| D44-R5 | — | A complete canonical record without its newline is torn: safe, it was never acknowledged (`append_line` writes line + newline in one write and `fsync`s before returning) | No defect (D-044 case 2) |
| D44-R6 | — | The repair sequence matches SPEC 10.1 step 4; the code `fsync`s the temporary before verifying it, which is harmless | No defect |

## The narrowed torn-tail rule (refines the literal v1 criterion of D-044)

D-044 states the v1 criterion as "the final bytes lack the terminating newline". The re-review showed that, read
literally, it lets a writable open drop a committed record (D44-R2), which D-044 itself forbids ("a complete record is
never dropped as crash recovery"). The fix keeps D-044's intent and only moves cases from "torn" to `CORRUPT`; it adds
no recovery. **This is a refinement of the owner's stated criterion and needs the owner's confirmation.** If the owner
prefers the literal criterion, reverting is the `_tail_problem` call in `parse_journal` and its tests.

Final bytes without a newline are `CORRUPT` when (SPEC 8.6, `journal._tail_problem`):

- they are longer than one append (`MAX_RECORD_BYTES + 1`);
- their first byte is neither `{` nor zero;
- the bytes before the first zero byte hold a complete JSON value followed by anything other than zero bytes;
- that complete value is not the valid next record (strict canonical JSON, correct digest, `seq` equal to the number of
  records, `prev` equal to the last record's digest).

They remain a torn tail (preserved, never read as authority) when they are all zero, start with zero bytes, are an
incomplete JSON fragment starting with `{`, or are the valid next record, possibly followed by zero bytes.

Residual, accepted as uncheckable and stated plainly: an incomplete fragment that starts with `{` (for example
`{garbage`, or invalid UTF-8 inside an unfinished string) and bytes after a leading zero-filled block are still
classified torn, because a prefix of a record cannot be validated. Nothing is lost: the whole journal is preserved in
`journal.jsonl.torn-<k>` before the tail is removed, and only after the entire prefix has validated.

## Fail-first evidence

Each new test was run before its fix.

- D44-R1, against the reviewer's mutant (repair moved before the fold):
  `FAILED …test_d044_fold_only_prefix_defect_before_an_incomplete_tail_is_not_mutated` — `1 failed, 2 passed`
  (the two older corrupt-prefix tests pass on the mutant, which is the gap).
- D44-R2, against `cf2e411`: `test_d044_final_bytes_no_append_can_produce_are_corrupt` 5 of 5 cases failed
  (`DID NOT RAISE CorruptInvestigation`): newline damaged, extra byte, newline replaced plus fragment, oversize, `\r`.
  The zero-filled torn cases passed already.
- D44-R2a and D44-R2b, against the first fix: 6 failed, 9 passed — the five new R2b cases and "a whole maximal
  append zero-filled".
- After the fixes: all D-044 tests pass; Memory tests 183 passed (167 before the re-review).

## Re-checks by the reviewer context

1. First re-check: R1, R3 and R4 fixed. R2 partly fixed, with R2a (a new defect) and R2b (remaining gaps) found. The
   SPEC 8.6 wording then disagreed with the code on three cases; it was rewritten.
2. Second re-check: R2a and R2b fixed; no crash-producible tail found that is now called `CORRUPT` (the first record
   with no records yet, a next record of exactly `MAX_RECORD_BYTES` with its newline missing or zeroed, every cut of a
   record with multibyte UTF-8 characters, 626 cut-sweep trials all recovered); SPEC 8.6 consistent with the code.
   Remaining, INFO: a hand-forged next record with a correct digest, `seq` and `prev` that would fail the fold (schema
   or invariant) is still classified torn, and `seq` compares equal when written as `true`. An append cannot produce
   such a record (the fold checks every record before it is written); producing one needs deliberate forgery with a
   recomputed digest, which the hash chain does not defend against without an external anchor (Step 6 limit R6-12).
   Not changed: a schema and invariant check on the tail would duplicate the fold for a case outside the crash model.

Reviewer probe scripts were kept outside the repository (session scratch), as in the Step 6 review.
