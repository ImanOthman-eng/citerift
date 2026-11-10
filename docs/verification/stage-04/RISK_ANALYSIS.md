# Stage 04 Risk Analysis: Detection Engine and Vertical Slice

Status: Step 3 of the retained plan (`planning/STAGE04_MASTER_EXECUTION_PACKAGE.md`, section 14), written before any
Stage 04 code. Owner authorization: `cmsg_018VCB51nDHP6HXmLU4ea5yPTg4B2mbvArm7ZsYe8DG6Ag` (2026-11-10). Companion
documents: `SPECIFICATION.md` (SPEC) and `MATHEMATICAL_MODEL.md` (MM).

## How to read this document

- Ids are `R4-nn` so that they are never confused with the project register `RISKS.md` (`R-0nn`), which this
  document cites where a risk is inherited.
- **Every risk below is open.** Nothing in Stage 04 is implemented yet, so every control is a design, not a tested
  fact. A risk is closed only by the evidence named in its "Detection" line, produced in a later step, and recorded in
  `TEST_RESULTS.md`; a planned mitigation never closes a risk.
- Each risk gives: cause; detection (how an occurrence would be found); prevention or mitigation (the designed
  control and where it is specified); residual risk (what remains if the control works as designed); the covering
  gate and invariant; and whether it **blocks verification**:
  - **blocks** = a detected occurrence makes the covering gate fail, so the stage cannot be reported VERIFIED;
  - **disclosed** = the residual cannot be removed inside Stage 04; it does not block by itself but must be stated in
    the handoff and in every result it affects, and the owner decides whether it is acceptable.
- Plan section 11 (F-01 to F-16) and plan section 17 are the earlier risk lists; the mapping is in section 4.

## 1. Detection risks

### R4-01 False attachment

- Cause: a positive claim (`RETRACTED_WORK_CITED`, `CONCERN_CITED`, `CORRECTION_CITED`, `REINSTATED_WORK_CITED`) for
  a work the citation does not cite: a wrong key from extraction, a key that names several works, support only through
  a co-occurrence bridge, a notice or marker taken as the cited work, or an unused reference definition.
- Detection: vertical slice expectations (SPEC 14); attachment precision on the pre-registered holdout with locked
  adjudicated labels (MM 11.2); hazard counts; differential test against the independent reference model (Step 4).
- Prevention: candidates only from `primary_citation_field` and `identifier_link` (SPEC 6.3); positive only through
  D-14 after every contradiction, unresolved and operational guard (SPEC 7.1, MM P4, P5); taint demotes any unit with
  an unconfirmed, malformed or unresolved-role identifier (D-8); ambiguous keys and bridged-only support abstain (D-9,
  D-10); use eligibility excludes unused and undetermined definitions (D-1, D-2).
- Residual: a citation whose identifier is itself wrong in Wikipedia (a typo that is a valid key of another retracted
  work) is attached to that work; Stage 04 can detect it only when the citation also carries a contradicting
  identifier (R4-03). Precision is measured, not proven.
- Gate and invariant: 04-A, 04-C, 04-I; M-7, M-12; MM P4, P5.
- Blocks verification: **blocks** (any false attachment above the pre-registered bound, or any in the vertical slice).

### R4-02 False reassurance

- Cause: absence, failure or abstention read as "not retracted" or as a clean article: a failed step, an unavailable
  lookup, a stale input, an unused definition, a missing identifier or an out-of-scope unit shown as a negative; an
  article summary that says "no retracted citations".
- Detection: property test over the decision table (no class or value means "not retracted"); failure-injection
  suite (gate 04-G: 0 negative findings and 0 successes from injected failures); schema test that the report and v1
  projections have no such value; summary wording test (SPEC S-7.7).
- Prevention: no negative class exists (SPEC 7.2); `NOT_FOUND_IN_CHECKED_SOURCES` only through D-16 with the
  conditions of MM P5; failures end the investigation without claims (O-2, O-3) or as `LOOKUP_UNAVAILABLE`; exports
  only after VERIFY (SPEC S-9.7); summary derived only from present claims.
- Residual: a reader can still misread `NOT_FOUND_IN_CHECKED_SOURCES` as "not retracted"; the wording and Stage 08
  presentation (AT-11) carry that, outside Stage 04. Coverage of the checked sources is limited (Retraction Watch
  snapshot, Crossref relations in the index); a retraction missing from them is not found.
- Gate and invariant: 04-A, 04-C, 04-G; M-12; MM P5.
- Blocks verification: **blocks** for any structural violation; the coverage limit is **disclosed**.

### R4-03 DOI/PMID collision

- Cause: one citation's DOI and PMID name different works (a copy error in Wikipedia, a PMID of the notice, a PMID of
  an unrelated record). Real case: arwiki revision 76190003, unit `un-00013` (`10.1038/nature12969` with
  `24476881`, while the DOI's record carries `24476891`).
- Detection: the 04-D regression set (SPEC S-7.4) with the real case and synthetic variants; D-5 agreement check
  against Stage 02's pair result; W-8 checked by VERIFY.
- Prevention: independent resolution of both keys and the coherence relation `κ` (SPEC 6.5, MM 5.3); D-6 before any
  positive rule; both alternatives kept with provenance; routed to needs-resolution; preserved by replay (MM P3).
- Residual: when the sources record neither identifier of the other scheme (`κ = UNDETERMINED`), a mismatched pair is
  not detectable from the checked sources; the claim carries `PAIR_UNCORROBORATED` and is evaluated. A conflict also
  hides a possibly true attachment by one key (a recall cost, measured by sensitivity variant (b), plan 8.4).
- Gate and invariant: 04-D; W-8; MM P2, P3.
- Blocks verification: **blocks** (any conflict case not ending `IDENTITY_CONFLICT`, or any positive or negative from
  an incompatible pair); the undetectable case is **disclosed**.

### R4-04 Notice/original confusion

- Cause: a citation of a retraction notice (or a notice DOI in a citation template, which Stage 03 marks as
  `primary_citation_field`, Stage 03 RISK_ANALYSIS R1) counted as a citation of the retracted work.
- Detection: VS-1 (Lancet notice), VS-3; NC-04 (AT-03); holdout hazard count.
- Prevention: Stage 02 matches originals and notices separately (`notice_only`); D-15 gives `NOTICE_CITED`, an
  abstention for the work, never a positive; a notice key paired with the original's key is a witness of
  incompatibility (D-6).
- Residual: a notice that Retraction Watch does not record as a notice (an unindexed notice DOI) gives `no_record`, so
  the citation is `NOT_FOUND_IN_CHECKED_SOURCES`, not a false positive. A Stage 02 record whose notice and original
  share one PMID is carried as `PMID_ROLE_COLLISION` (D-10).
- Gate and invariant: 04-A, 04-C; M-12.
- Blocks verification: **blocks**.

### R4-05 Identifier-role confusion

- Cause: an identifier in a marker, a textual mention, labeled reference text or an unsupported template treated as
  the cited work, or a cited identifier dropped because its role was not a candidate role.
- Detection: role tests per Stage 03 role; VS-1 markers; holdout sample of units without candidate keys (plan 12.3,
  annotation item set); sensitivity variants (a) and (c) (plan 8.4).
- Prevention: fixed candidate roles (SPEC 6.3); observation roles recorded, never deciding (S-6.7); `unresolved` role
  taints the unit (S-6.6) instead of being silently ignored.
- Residual: a work cited only in plain labeled text ("doi:10…" in prose) is out of detection scope (`NO_IDENTIFIER`)
  and therefore missed; this is a recall limit, measured on the sampled units without keys.
- Gate and invariant: 04-C; MM 4.3.
- Blocks verification: **disclosed** for the recall limit; **blocks** if an observation role ever decides a claim.

## 2. Data freshness and integrity risks

### R4-06 Stale Stage 02 index

- Cause: the index file is rebuilt, replaced or rebuilt under another policy after an investigation recorded it.
- Detection: index identity (snapshot id, policy version, schema version, file SHA-256) recorded per LOOKUP attempt
  and recomputed on resume and replay (SPEC S-3.2, 10.3); replay mutation tests (04-F: every mutation reported stale,
  no false stale).
- Prevention: staleness predicate over step keys (MM 10.2); a stale investigation is never resumed or reused
  (S-10.1).
- Residual: the pinned snapshot is itself dated; a retraction recorded after it is not known. Results always name the
  snapshot id.
- Gate and invariant: 04-F; MM ST-1.
- Blocks verification: **blocks** if a mutation is not reported; the snapshot date is **disclosed**.

### R4-07 Stale Stage 03 extraction

- Cause: the extraction engine, its profile, normalizer or configuration changes, or the bundle changes, after an
  investigation recorded its extraction.
- Detection: extractor version, profile digest, normalizer and `config_digest` in the input identity vector; bundle
  digest checked by `verify_bundle`; `replay_bundle` in replay.
- Prevention: as R4-06; a bundle whose bytes do not match its digest is corrupt input, not stale (S-10.2).
- Residual: a revision's live content can differ from a retained snapshot (two captures of one revision can differ in
  render); the root names the snapshot, so results are about that snapshot only.
- Gate and invariant: 04-F; M-9; MM RT-2.
- Blocks verification: **blocks** if a mutation is not reported.

### R4-08 Provenance loss

- Cause: a claim whose evidence chain cannot be followed back to a Stage 02 row hash and a Stage 03 anchor (values
  copied without pointers, events dropped by paging, observations not stored).
- Detection: VERIFY checks a complete evidence chain for every claim (SPEC S-12.2); 04-A criterion "every claim
  traces to a Stage 02 row hash and a Stage 03 anchor".
- Prevention: observations stored byte-for-byte; evidence only by pointer (S-8.5, MM EV-1, EV-2); full events
  recorded without paging (S-3.1); explanation text generated from rule id and chain only (S-12.2).
- Residual: provenance ends at the Retraction Watch row and the Wikipedia snapshot; whether the row itself is correct is
  outside Stage 04 (Stage 02 limitations).
- Gate and invariant: 04-A, 04-B; M-3, M-4, M-7.
- Blocks verification: **blocks**.

### R4-09 Journal corruption

- Cause: a bit flip, a manual edit, a bug that writes a wrong record, a truncated file.
- Detection: hash chain and digests verified on every open (M-1, M-2); blob hashes checked on read (M-3);
  bit-flip injection tests (plan 23).
- Prevention: `CORRUPT` is read-only; nothing is repaired or guessed (SPEC 8.6); only a torn final record is cut, after
  a verified copy is preserved (SPEC 10.1).
- Residual: corruption is detected, not prevented; a corrupt investigation must be re-run from its inputs.
- Gate and invariant: 04-E; M-1, M-2, M-3.
- Blocks verification: **blocks** if an injected corruption is not detected.

### R4-10 Partial writes

- Cause: a crash during a blob write, between a blob and its record, or between content records and `step_succeeded`.
- Detection: fault injection at every write, `fsync` and step boundary (plan 23; SPEC 10.2 table).
- Prevention: write order blob → record (M-3); temporary file, `fsync`, rename, directory `fsync` (S-8.2); commit
  discipline: content counts only with `step_succeeded` (M-6); torn-tail handling (SPEC 10.1).
- Residual: the guarantees rely on POSIX `fsync` and `rename` semantics on a local file system (assumption A-3); a
  file system that lies about `fsync` can lose a committed record.
- Gate and invariant: 04-E; M-3, M-5, M-6.
- Blocks verification: **blocks** if any injected crash changes `C(J)` or repeats a committed step.

### R4-11 Replay divergence

- Cause: hidden nondeterminism (dictionary order, time, environment, locale, floating point), a pure step that reads
  something outside its inputs, or a capture repeated before ACQUIRE committed.
- Detection: VERIFY re-runs the pure steps (SPEC 9.7); `replay` reports `differs` with the first differing record
  (S-10.3); VS-9 and VS-10; byte-identical replay on both Python versions.
- Prevention: canonical encoding (MM 2.1); `δ` and the fold are functions of recorded data only (MM 5.2, FD-1); `at`
  excluded from content (MM 7.3); network only in ACQUIRE.
- Residual: a crash before ACQUIRE commits on a capture request can lead to a different snapshot on resume, hence
  another root and another `C(J)`; MM P6 is stated with that condition, and fault injection for those points uses a
  deterministic transport (review finding F-09).
- Gate and invariant: 04-A, 04-F; M-13; MM P6, RP-1 to RP-3.
- Blocks verification: **blocks**.

### R4-12 Duplicate execution

- Cause: two processes on one investigation, a repeated `run`, a retry of a step that had committed.
- Detection: concurrency test (`INVESTIGATION_BUSY`); duplicate-run test; M-14 checked on open and by VERIFY.
- Prevention: exclusive `flock` (SPEC 10.1); step keys and "never re-run a committed key" (S-9.3, M-14); `run` on an
  existing investigation is `resume` (S-9.4); content-addressed blobs make a repeated write a no-op (S-8.2).
- Residual: none known on a local file system (see R4-26 for others).
- Gate and invariant: 04-E; M-11, M-14; W-3.
- Blocks verification: **blocks**.

### R4-13 Infinite retry and unbounded waiting

- Cause: a step that keeps failing, a deferral that keeps coming back, a process that keeps crashing in one step, or
  a controller that sleeps until `not_before`.
- Detection: state-space enumeration of the controller (Step 4, plan 12.2); budget tests; MM TR-4, TR-5.
- Prevention: `A_max = 3` failed or interrupted attempts and `F_max = 6` deferrals per step (SPEC 9.2); a crash loop
  ends `RETRY_BUDGET_EXHAUSTED`; a deferral ends the run in `BLOCKED` without sleeping; Stage 03 keeps its own bounded
  network retries (MR-14).
- Residual: an operator can resume a `BLOCKED` investigation repeatedly; each resume before `not_before` writes
  nothing.
- Gate and invariant: 04-E, 04-G; W-4; MM TR-4, TR-5.
- Blocks verification: **blocks** if any reachable state has no bound.

## 3. Security, boundary and engineering risks

### R4-14 Path traversal

- Cause: a title, request field or record value used to build a path; a symbolic link planted in a store.
- Detection: path-safety tests (titles with `../`, absolute paths, symlinked `blobs/` and `journal.jsonl`).
- Prevention: directories named by hashes, blobs by digests, no path from request text (S-8.1); `O_NOFOLLOW` and
  symlink refusal; memory root outside the repository (S-15.3).
- Residual: a local user with write access to the memory root can still delete or replace files (see R4-15).
- Gate and invariant: 04-H; S-15.3.
- Blocks verification: **blocks**.

### R4-15 Evidence tampering

- Cause: a person or process with write access rewrites a journal, its blobs or a bundle consistently (recomputing the
  chain).
- Detection: accidental changes are detected by the chain and hashes (R4-09); retained evidence in the repository is
  pinned by git commits and by digests cited in `TEST_RESULTS.md`.
- Prevention: the chain makes edits evident to anyone who holds an earlier digest (the report and the retained
  evidence record `C(J)` and the last record digest).
- Residual: records are integrity-checked, not signed; a consistent rewrite by someone with write access is not
  detectable without an external copy of a digest. Stage 03 has the same limit (Stage 03 RISK_ANALYSIS R10).
- Gate and invariant: 04-H; M-2, M-3.
- Blocks verification: **disclosed**.

### R4-16 Schema drift

- Cause: Stage 04 schemas, the Stage 02 lookup-result schema, the Stage 03 extraction schema or contracts v1 change
  under Stage 04, or a Stage 04 record is read by a reader of another version.
- Detection: schema identities in the input identity vector (stale); contract test that `schemas/contracts` is
  unchanged from `0c21182` (the fail-closed test of A-03-001); journal version check (S-8.7); v1 projection
  validation.
- Prevention: Stage 04 schemas `$ref` v1 by URN without editing it (SPEC 11.2); readers refuse unknown journal
  versions and subject types (S-8.7, S-4.5).
- Residual: none known inside Stage 04; a later contract version needs a migration that writes new investigations.
- Gate and invariant: 04-B, 04-F; M-13.
- Blocks verification: **blocks**.

### R4-17 Dependency drift

- Cause: a library version change that alters parsing, JSON encoding or hashing (for example `mwparserfromhell`,
  `jsonschema`, Python itself), or a new dependency added under time pressure.
- Detection: `uv lock --check` and `uv sync --locked` in CI; engine identities in the staleness vector; the matrix on
  Python 3.12 and 3.13; `pip-audit` (plan 12.1).
- Prevention: no new runtime dependency (gate 04-J requires a recorded reason for any); standard library plus the
  existing `jsonschema`; locked environment.
- Residual: Python minor versions are both supported; a difference between them in canonical output would appear as
  replay `differs` and block (R4-11).
- Gate and invariant: 04-F, 04-J.
- Blocks verification: **blocks** for an unrecorded dependency or a replay difference.

### R4-25 Memory and controller divergence

- Cause: the controller keeps state in variables (attempt counters, a "current step" flag, a cache) that can disagree
  with the journal after a crash.
- Detection: invariant W-1 tested by killing the process at every boundary and comparing the resumed state with
  `fold(J)`; code review rule: the controller reads state only through `fold`.
- Prevention: no independent mutable controller state (SPEC W-1, MM FD-1); every append checked by `legal` against
  `fold(J)` (S-9.1).
- Residual: none known by design; it depends on implementation discipline, which the fault-injection tests check.
- Gate and invariant: 04-E; W-1, W-2.
- Blocks verification: **blocks**.

### R4-26 Concurrent writers and unsupported file systems

- Cause: a memory root on a network file system where `flock` or `rename` is not reliable; two hosts writing one
  store.
- Detection: not detectable in general from inside the process.
- Prevention: the memory root must be a local POSIX file system (assumption A-3); documented as unsupported otherwise
  (SPEC 10.1).
- Residual: on an unsupported file system the single-writer and atomicity guarantees do not hold.
- Gate and invariant: 04-E, 04-H; M-11.
- Blocks verification: **disclosed** (operating constraint).

### R4-27 Secret exposure in retained evidence

- Cause: captured pages contain third-party secrets (Stage 03 found a key id in a captured page); retained journals or
  bundles copied into the repository publish them.
- Detection: secret scan of every file before it is committed (S-15.5).
- Prevention: scan, then the Stage 03 withheld-file procedure for any hit.
- Residual: a scanner misses unknown secret formats.
- Gate and invariant: 04-H.
- Blocks verification: **blocks** if a known secret format is committed.

### R4-28 Boundary breach

- Cause: Stage 04 code imports `citerift.governance`; a network call outside Stage 03's capture path; untrusted
  wikitext or HTML evaluated outside Stage 03's isolated worker.
- Detection: static import test (AT-07); socket-blocking test for every step but ACQUIRE of a capture request, and
  for replay (AT-08); no `eval`, `exec` or `shell=True` test.
- Prevention: SPEC S-15.1, S-15.2, S-15.4; adapters call only public Stage 02 and Stage 03 functions (SPEC 3).
- Residual: none known.
- Gate and invariant: 04-H.
- Blocks verification: **blocks**.

### R4-29 Upstream defect or semantic mismatch exposed by Stage 04

- Cause: Stage 02's pair result and Stage 04's coherence relation disagree (a Stage 02 change or an adapter bug); a
  Stage 02 or Stage 03 output outside the facts F-1 to F-7; pressure to patch an accepted engine to make a case pass.
- Detection: D-5 (`ADAPTER_INCONSISTENT`) and D-17 (`DECISION_TABLE_GAP`) fail closed; reference-model differential.
- Prevention: Stage 02 and Stage 03 are not changed by Stage 04 (SPEC S-6.13); a genuinely required upstream change
  is put to the owner as a decision through a maintenance transaction, as A-03-001 was.
- Residual: an upstream defect that stays inside the facts F-1 to F-7 is not detected by these checks.
- Gate and invariant: 04-D; MM P1, P2.
- Blocks verification: **blocks** while an unexplained `ADAPTER_INCONSISTENT` or `DECISION_TABLE_GAP` exists.

### R4-30 Reference model not independent

- Cause: the reference model of the decision table (Step 4) is written from the same misunderstanding as the engine,
  so the zero-difference criterion of 04-C passes on a shared error.
- Detection: the reference model is written before the engine from this specification and the mathematical model
  only, in a separate module under `simulations/stage04/`, enumerating the abstract input domain of MM 5.1; the
  vertical slice and the holdout are independent of both.
- Prevention: the table is data in the specification; the reference model is a direct transcription of MM 5.2 with
  no shared code.
- Residual: both are written by the same agent; independence is procedural, not personal. This is stated in the
  simulation report.
- Gate and invariant: 04-C.
- Blocks verification: **disclosed**.

### R4-31 Storage exhaustion and I/O errors

- Cause: the disk fills, a write fails, a blob cannot be read.
- Detection: `ENOSPC` injection on blob and record writes (plan 23).
- Prevention: the failing write is not committed; the attempt ends `step_failed(STORAGE_ERROR)` when a record can be
  written, otherwise resume treats it as a crash (SPEC 10.2).
- Residual: a full disk stops progress until space is freed.
- Gate and invariant: 04-E, 04-G; M-5, M-6.
- Blocks verification: **blocks** if an injected I/O error leaves an inconsistent journal.

## 4. Evaluation and process risks

### R4-18 Evaluation leakage

- Cause: decision rules, thresholds or code tuned after seeing holdout data; predictions exposed to annotators; more
  than one prediction run.
- Detection: commit history audit: the freeze commit (plan step 12) precedes the pre-registration commit (step 13),
  which precedes the draw; one prediction run recorded; annotator transcripts show no prediction.
- Prevention: freeze before draw; seeded draw with committed seed and frame digests; labels locked before predictions
  are exposed (D-3); no score or threshold to tune (MM 11.1).
- Residual: the agent that wrote the engine also runs the campaign; separation is by commits and locks, not by people.
- Gate and invariant: 04-I.
- Blocks verification: **blocks** for any change after the freeze or any second prediction run.

### R4-19 Exposed development cases leaking into the holdout

- Cause: the 232 probe revisions, the 16 matched articles, the Stage 01 purposive cases or the Obokata conflict case
  appear in the holdout.
- Detection: exclusion check of the drawn set against the committed exposure list (by wiki and page id, not only
  revision id).
- Prevention: the frame excludes the exposure set before the draw (plan 12.3); VS cases and the 04-D regression
  case are labelled design data (SPEC 14, S-7.4).
- Residual: an article closely related to an exposed one (same retracted work, other article) can still be drawn; it
  is allowed and reported.
- Gate and invariant: 04-I.
- Blocks verification: **blocks** if an excluded article is in the holdout.

### R4-20 AI-label dependency

- Cause: all reference labels come from Claude Sonnet instances of one vendor (D-3); shared model errors are not
  caught by agreement.
- Detection: disagreement rate between the two annotators; adjudication record; spot checks by Claude Haiku
  (auxiliary only).
- Prevention: two blinded independent annotators, a blinded third adjudicator, labels locked before predictions,
  retained transcripts and model metadata.
- Residual: labels are AI-generated from one vendor and are not human gold labels; correlated errors remain. This is
  the same class of limit as Stage 03's AI-only labels.
- Gate and invariant: 04-I.
- Blocks verification: **disclosed** (must be stated with every evaluation result).

### R4-21 Bilingual asymmetry

- Cause: Arabic and English differ in templates, profile coverage and data volume; Stage 03 Arabic warning detection
  is untested and its Arabic G2 rests on one adjudicated correction; a pooled metric can hide one language failing.
- Detection: every metric and gate criterion per language (plan 12.3); per-language denominators.
- Prevention: no pooled pass criterion; Arabic cases in the vertical slice (VS-2, VS-5).
- Residual: Arabic data are scarcer; intervals are wider; markers are recorded, not interpreted, in both languages.
- Gate and invariant: 04-I.
- Blocks verification: **blocks** if either language fails its own criterion.

### R4-22 Insufficient event denominators

- Cause: 30 + 10 articles per language may not contain enough flagged units, no-record units or identity conflicts to
  meet the pre-registered minima.
- Detection: denominator counts after each block of the pre-registered expansion.
- Prevention: frame profiling before pre-registration; positive-enriched strata; pre-registered expansion within 200
  acquisition attempts (D-5); identity conflicts reported descriptively below their minimum (plan 12.3).
- Residual: the ceiling can be reached with a short denominator.
- Gate and invariant: 04-I.
- Blocks verification: **blocks** (a short denominator after the ceiling means 04-I is not passed; it is never
  weakened).

### R4-23 Rate limiting

- Cause: Wikimedia answers 429 or `maxlag` (R-008: frequent from this environment); captures are slow.
- Detection: Stage 03 issue codes recorded per attempt; `BLOCKED` lifecycle with `not_before`.
- Prevention: Stage 03's shared network gate, Retry-After honored, bounded attempts (MR-14); Stage 04 defers instead of
  retrying itself (T-DEFER); retained bundles for development and CI; capture only for the holdout.
- Residual: the campaign can take hours; a long block delays 04-I but never changes a result.
- Gate and invariant: 04-G; W-4.
- Blocks verification: **disclosed** as schedule risk; **blocks** if a rate-limit failure ever yields a claim.

### R4-24 Deadline pressure causing gate weakening

- Cause: the Devpost deadline (2026-11-21, R-010) and the remaining Stages 05 to 09 create pressure to relax a
  denominator, skip a suite, accept a red check or merge an unverified state.
- Detection: gates are fixed in the registry (D-040) and checked by `citerift-gov check`; any change to a gate needs a
  recorded owner decision; the final report must quote each gate's evidence.
- Prevention: no gate, denominator or criterion is changed without the owner's words; if a gate cannot be met, the
  report says NOT VERIFIED or BLOCKED — EVIDENCE PROVIDED instead of weakening it (D-5: "expand never weaken").
- Residual: time may run out before 04-I completes; the stage then stays unverified, which is a schedule loss, not a
  validity loss.
- Gate and invariant: 04-J (and every gate).
- Blocks verification: **blocks** (any weakening without an owner decision).

### R4-32 Inherited upstream limitations

- Cause: limits accepted in earlier stages bound what Stage 04 can claim: Stage 03 declared support boundaries
  (R-035), English unit precision interval below G5c (R-036), render reconciliation of repeated names (R-038),
  AI-only labels in Stage 03, Retraction Watch and Crossref coverage in Stage 02.
- Detection: the vertical slice and holdout misses are attributed to a declared upstream boundary or counted as Stage
  04 defects (plan 8.6).
- Prevention: Stage 04 reads only the source side of the extraction (S-6.1), so R-038 (render) does not reach
  detection; identifiers that Stage 03 could not confirm are tainted (S-6.6); no Stage 04 result claims more
  coverage than its inputs.
- Residual: an upstream extraction miss is a Stage 04 miss; recall is conditional on Stage 03 and Stage 02 coverage.
- Gate and invariant: 04-A, 04-I.
- Blocks verification: **disclosed**.

## 5. Summary

| Id | Risk | Gates | Blocks verification |
|---|---|---|---|
| R4-01 | False attachment | 04-A, 04-C, 04-I | blocks |
| R4-02 | False reassurance | 04-A, 04-C, 04-G | blocks; coverage disclosed |
| R4-03 | DOI/PMID collision | 04-D | blocks; undetectable case disclosed |
| R4-04 | Notice/original confusion | 04-A, 04-C | blocks |
| R4-05 | Identifier-role confusion | 04-C | blocks; recall limit disclosed |
| R4-06 | Stale Stage 02 index | 04-F | blocks; snapshot date disclosed |
| R4-07 | Stale Stage 03 extraction | 04-F | blocks |
| R4-08 | Provenance loss | 04-A, 04-B | blocks |
| R4-09 | Journal corruption | 04-E | blocks |
| R4-10 | Partial writes | 04-E | blocks |
| R4-11 | Replay divergence | 04-A, 04-F | blocks |
| R4-12 | Duplicate execution | 04-E | blocks |
| R4-13 | Infinite retry and unbounded waiting | 04-E, 04-G | blocks |
| R4-14 | Path traversal | 04-H | blocks |
| R4-15 | Evidence tampering | 04-H | disclosed |
| R4-16 | Schema drift | 04-B, 04-F | blocks |
| R4-17 | Dependency drift | 04-F, 04-J | blocks |
| R4-18 | Evaluation leakage | 04-I | blocks |
| R4-19 | Exposed development cases in the holdout | 04-I | blocks |
| R4-20 | AI-label dependency | 04-I | disclosed |
| R4-21 | Bilingual asymmetry | 04-I | blocks |
| R4-22 | Insufficient event denominators | 04-I | blocks |
| R4-23 | Rate limiting | 04-G | disclosed; blocks if it yields a claim |
| R4-24 | Deadline pressure causing gate weakening | 04-J | blocks |
| R4-25 | Memory and controller divergence | 04-E | blocks |
| R4-26 | Concurrent writers and unsupported file systems | 04-E, 04-H | disclosed |
| R4-27 | Secret exposure in retained evidence | 04-H | blocks |
| R4-28 | Boundary breach | 04-H | blocks |
| R4-29 | Upstream defect or semantic mismatch | 04-D | blocks |
| R4-30 | Reference model not independent | 04-C | disclosed |
| R4-31 | Storage exhaustion and I/O errors | 04-E, 04-G | blocks |
| R4-32 | Inherited upstream limitations | 04-A, 04-I | disclosed |

All 32 risks are open. None is resolved by this document.

## 6. Mapping from the plan's lists

| Plan id | Plan risk | This document |
|---|---|---|
| F-01 | notice or marker counted | R4-04, R4-05 |
| F-02 | DOI and PMID name different works | R4-03 |
| F-03 | missing record read as "not retracted" | R4-02 |
| F-04 | failed step read as success | R4-02, R4-25 |
| F-05 | crash between blob and record | R4-10 |
| F-06 | torn final line | R4-09, R4-10 |
| F-07 | two runners | R4-12, R4-26 |
| F-08 | index rebuilt with another policy | R4-06 |
| F-09 | rate limiting | R4-23 |
| F-10 | path traversal | R4-14 |
| F-11 | untrusted wikitext or HTML | R4-28 |
| F-12 | governance import | R4-28 |
| F-13 | hidden network use | R4-28 |
| F-14 | secrets in captured pages | R4-27 |
| F-15 | evaluation leakage | R4-18, R4-19 |
| F-16 | contradiction hidden by aggregation | R4-02 (summary), R4-03 |
| plan 17 | deadline | R4-24 |
| plan 17 | too few flagged units; denominators | R4-22 |
| plan 17 | AI-only labels | R4-20 |
| plan 17 | census frame bias | R4-32 (recall conditional on the frame; stated with every result) |
| plan 17 | rate limits | R4-23 |
| plan 17 | contradiction rule removes true attachments | R4-03 (residual) |
| plan 17 | scope creep into 05/07 | R4-24 (process), SPEC 1.2 |
