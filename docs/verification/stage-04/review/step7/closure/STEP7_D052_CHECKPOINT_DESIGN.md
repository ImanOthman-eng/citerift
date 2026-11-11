# D-052: external journal checkpoint (design only)

Owner decision D-052 (TA-1), owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`,
2026-11-11. This file records the design. **Nothing in it is implemented in Step 7.** The implementation belongs to
the CLI and report work of a later step. R6-12 (an actor who can rewrite the journal and recompute the unkeyed hash
chain is not detected) stays a recorded limitation until then, and partly after it (section 5).

## 1. What already exists [verified, `journal.py`, `ids.py`]

Every journal record carries `seq`, `prev` (the `digest` of the record before it, or the genesis value for `seq` 0)
and `digest = record_digest(record)`, which covers every other field, `prev` included. The `digest` of the record at
`seq = n` therefore commits to the whole prefix `0..n`: changing, removing or reordering any earlier record changes it,
unless SHA-256 collides. The chain is unkeyed. Anyone who rewrites the journal can recompute every `digest`, so the
chain alone detects accidental damage, not deliberate rewriting.

## 2. The checkpoint

One canonical JSON object (Stage 04 `canon`, the same encoding as journal records), with exactly these fields:

| Field | Value |
|---|---|
| `format` | `"citerift-investigation-checkpoint"` |
| `format_version` | `"1"` |
| `investigation_key` | the investigation key (directory name, SPEC 4.3) |
| `seq` | the `seq` of the last record the checkpoint covers |
| `journal_digest` | that record's `digest` (64 lowercase hex) |

No timestamp, path, host name, user name or content excerpt is included. A checkpoint therefore discloses only that an
investigation with that key had at least `seq + 1` committed records ending in that digest.

## 3. Where it lives

- It is written to **stdout**, or to a file the user names, by an explicit command (for example
  `citerift investigate checkpoint <key>` and `--out <path>`; the CLI names are for the CLI step to fix).
- It is **never** written into the investigation's journal, its directory or any directory under the memory root. The
  command refuses an `--out` path that resolves (after symlinks) inside the memory root.
- It is **not** part of the ASSEMBLE report or any blob, so that the report stays a function of the journal and a
  checkpoint never certifies itself.
- Keeping the checkpoint somewhere the journal's writer cannot change is the user's job (another machine, a commit, a
  ticket, a printed copy). The design states that plainly to the user.

## 4. Verification

`verify-checkpoint <key> <checkpoint>` opens the investigation read-only (the ordinary `open`, D-044/D-046 rules) and
answers exactly one of:

| Result | Condition |
|---|---|
| `CHECKPOINT_MATCH` | the journal holds a record at `seq` and its `digest` equals `journal_digest` |
| `CHECKPOINT_PREFIX_REWRITTEN` | a record at `seq` exists with another `digest` |
| `CHECKPOINT_TRUNCATED` | the journal holds fewer than `seq + 1` complete records |
| `CHECKPOINT_KEY_MISMATCH` | `investigation_key` is not the investigation opened |
| `CHECKPOINT_INVALID` | the checkpoint is not the canonical object of section 2 or names an unknown `format_version` |
| `JOURNAL_CORRUPT` | the journal itself fails `open` (reported as today, before any checkpoint comparison) |

Records after `seq` are neither confirmed nor questioned: a later, larger checkpoint covers them.

## 5. The only claim, and what it does not claim

**Claim.** Given a checkpoint that was kept outside the investigation memory since it was produced, a verifier detects
any rewriting or truncation of the journal prefix `0..seq` that the checkpoint covers (up to a SHA-256 collision).

**Not claimed.**

- It is **not a signature**, authentication or non-repudiation. It says nothing about who wrote the journal or the
  checkpoint. Anyone can produce a checkpoint of any journal.
- It does not protect records after `seq`, a journal for which no checkpoint was kept, or a checkpoint stored where
  the same actor can replace it together with the journal.
- It does not make the report trustworthy beyond the journal it was derived from.

## 6. Dependencies and limits

- No new dependency: SHA-256 (`hashlib`) and the existing canonical encoder suffice. No cryptographic library, no key
  material, no network.
- Size: about 250 bytes; reading a checkpoint is bounded by a fixed 4 KiB limit.
- R6-12 (recorded in `review/step6/STEP6_INDEPENDENT_REVIEW.md`) stays a limitation; the checkpoint narrows it to
  "rewriting not covered by a retained checkpoint".

## 7. Tests the implementation will need

1. A checkpoint taken at `seq = n` matches the unchanged journal and still matches after further appends.
2. Changing one byte of any record `<= n` (with the whole chain recomputed, the R6-12 attacker) gives
   `CHECKPOINT_PREFIX_REWRITTEN`; removing records to below `n + 1` gives `CHECKPOINT_TRUNCATED`.
3. A checkpoint of another investigation gives `CHECKPOINT_KEY_MISMATCH`; non-canonical, extra-field, unknown-version
   or oversized input gives `CHECKPOINT_INVALID`.
4. The command never creates a file under the memory root (including through a symlinked `--out`), and the report and
   journal bytes are identical with and without taking a checkpoint.
