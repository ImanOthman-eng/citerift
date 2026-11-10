# Stage 04 Step 3: internal adversarial review

Scope: `SPECIFICATION.md` (SPEC), `MATHEMATICAL_MODEL.md` (MM) and `RISK_ANALYSIS.md` (RA), against the retained plan
(`planning/STAGE04_MASTER_EXECUTION_PACKAGE.md`), DECISIONS.md D-039 and D-040, the registry gates 04-A to 04-J and
the accepted Stage 02 and Stage 03 code at `a152885`. Requested by the owner on 2026-11-10
(`cmsg_018VCB51nDHP6HXmLU4ea5yPTg4B2mbvArm7ZsYe8DG6Ag`).

Method. The review was done by the same agent that wrote the documents, after a first complete draft of the
specification and before the three documents were committed. It is therefore a self-review, not an independent one.
For each question the owner listed (undefined or unreachable states, non-total rules, negative/unknown ambiguity,
memory/controller divergence, non-idempotent transitions, replay ambiguity, missing provenance, hidden dependence on
Stages 05 to 07, untestable requirements), the draft was read against the plan and against the Stage 02 and Stage 03
source it relies on. Every confirmed defect was corrected in the committed documents; the draft itself was not kept,
so each finding states what the draft said. A structural consistency check (`check_step3_docs.py`, output in
`check_step3_docs.log`) verifies the cross-references after the corrections; it does not evaluate the decision table or
the state machines on inputs, which is the reference model and state-space enumeration of Step 4.

Classification: **defect** (corrected), **deviation** (a recorded difference from the retained plan, with the reason;
listed for the owner), **observation** (checked, no change needed).

## Findings

### F-01 Precedence differs from the plan's draft table (deviation)

- Draft and plan: plan 8.3 orders P-0 unavailable (extraction or index) > P-1 unresolved identifier > P-2 identity
  conflict > P-3 contradiction in sources > P-4 unresolved identity > P-5/P-6 positive > P-7 unresolved status > P-8
  notice > P-9 not found > P-10 no identifier. The first draft of SPEC put the lookup-unavailable rule before the
  identity conflict as the plan did.
- Owner instruction of 2026-11-10: default ordering "identity contradiction / unresolved evidence / operational
  failure > positive finding > no finding".
- Correction: SPEC 7.1 and 7.3 follow the owner's order (tiers 4 to 9); eligibility and the adapter consistency check
  stay first because they decide whether there is a shown citation or a trustworthy input at all and cannot produce a
  finding. Both orders put every abstention before any positive finding, so neither can turn an abstention into a
  finding; they differ only in which abstention or contradiction class is reported when two apply.
- Mapping of the plan's rules:

| Plan rule | SPEC rule |
|---|---|
| P-0 extraction failed | O-2 (an investigation-level failure; Stage 03 has no per-unit extraction failure, its status is per document) |
| P-0 index unavailable | O-3 (index cannot be opened) and D-13 (a query fails) |
| P-1 unresolved identifier | D-4 (no key), D-8 (beside a key) |
| P-2 identity conflict | D-6 |
| P-3 contradiction in sources | D-7 |
| P-4 unresolved identity | D-9 (ambiguous), D-10 (PMID role collision, bridged-only support) |
| P-5, P-6 positive | D-14 |
| P-7 unresolved status | D-11, D-12 |
| P-8 notice | D-15 |
| P-9 not found | D-16 |
| P-10 no identifier | D-3 |
| (new) | D-1, D-2 use eligibility (plan 8.1 named unused definitions in prose), D-5 adapter consistency, D-17 gap |

- Owner decision point: confirm that the 2026-11-10 order replaces the plan's draft order. No gate names an order.

### F-02 The plan's table was not total (defect, corrected)

- Case: a `PAIR` citation whose DOI is a notice (`notice_only`) and whose PMID has no record (`no_record`). P-8
  requires "every Q-1 is `notice_only`", P-9 "every Q-1 is `no_record`", P-10 "no candidate key"; none holds, so the
  plan's table gave no class.
- Correction: every rule after D-5 reads the deciding lookup `L(c)` (Q2 for a pair) or an existential over `Λ(c)`;
  D-17 makes any remaining case fail closed, and MM P1 proves D-17 unreachable under facts F-1 to F-4. In the example,
  Q2 is `notice_only` (`gather` with both keys and no original events), so the class is `NOTICE_CITED` with
  `KEY_RESULTS_DIFFER`.

### F-03 Identifiers of unresolved role were out of scope (defect, corrected)

- Draft: role `unresolved` was an observation role only, so a unit whose only identifier had role `unresolved` (for
  example inside an unsupported citation template) became `NO_IDENTIFIER`, out of scope. Plan P-1 abstains for
  "role `unresolved` on a would-be candidate", and the Stage 03 handoff requires `unresolved` to be treated as
  unconfirmed.
- Correction: any `unresolved` occurrence taints the unit (SPEC S-6.6, reason `IDENTIFIER_ROLE_UNRESOLVED`); with no
  key the unit is `UNRESOLVED_IDENTIFIER` (D-4), never out of scope.

### F-04 Use eligibility was not total (defect, corrected)

- Draft: rows for notes with a bound or anonymous use, unused list-defined notes and conflicting definitions; a
  `note` or `generated_note` container without such a use matched no row.
- Correction: a first-match table over the Stage 03 enumerations with the default `USE_NOT_ESTABLISHED`
  (reason `NO_BOUND_USE`), which leads to `UNRESOLVED_USE`, never to `UNUSED` (SPEC 6.2, MM 4.2). A unit whose
  container is missing fails NORMALIZE.

### F-05 Bridged-only support was classed as unresolved status (defect, corrected)

- Draft: a `matched` result whose only support is bridged has projection `uncertain` (`BRIDGE_ONLY_SUPPORT`,
  `policy.reduce`) and went to `UNRESOLVED_STATUS`. Plan P-4 classes it as an identity question.
- Correction: D-10 includes `BRIDGE_ONLY_SUPPORT` and gives `UNRESOLVED_IDENTITY`.

### F-06 A witnessed identity conflict could be hidden by an unavailable lookup (defect, corrected)

- Draft: coherence needed all three lookups, and the unavailable rule came first, so an incompatibility that one
  available lookup already shows was reported as `LOOKUP_UNAVAILABLE`.
- Correction: `κ` is witness-based over the available lookups, with `NOT_DETERMINED` when no witness exists and a Q1
  is unavailable (SPEC 6.5, MM 5.3); D-6 precedes D-13; the claim carries `LOOKUP_PARTIAL`. The agreement check D-5
  and P2 apply only when all three lookups are available.

### F-07 Retry budgets had a dead state and an unreachable budget (defect, corrected)

- Draft: `step_interrupted` had no budget, so a step that kills the process every time was retried forever; once a
  step had used `A_max` attempts, an interrupted attempt returned to `pending` with no legal transition (a non-terminal
  dead state). Deferrals also counted as attempts, so `F_max = 6` could never be reached with `A_max = 3`.
- Correction: separate counters `φ` (failures and interruptions) and `f` (deferrals); at the budget, resume closes the
  open attempt with `step_failed(RETRY_BUDGET_EXHAUSTED)` (SPEC 9.2, W-4, W-6; MM T-INTERRUPT, T-FAIL-T, TR-4, TR-5).

### F-08 Report and lifecycle were circular (defect, corrected)

- Draft: the report (written by ASSEMBLE, step 7) held the lifecycle and the content digest, but the lifecycle is
  decided only after VERIFY (step 8) and `C(J)` covers the report. The draft also mapped `FAILED` to a v1 `failed`
  record, while v1 records exist only for works with a positive claim.
- Correction: the report holds the outcome only; VERIFY records `C(J)`; the report and v1 records are exported only in
  `COMPLETED` or `NEEDS_RESOLUTION` (SPEC 11.1, S-9.7; MM 7.3).

### F-09 Resume equivalence needs a condition on ACQUIRE (observation, made explicit)

- A crash before ACQUIRE commits on a capture request leads to a new capture on resume; `capture.json` records fetch
  times, so the snapshot, the root and `C(J)` can differ from an uninterrupted run. Gate 04-E ("reaches the same
  content digest") is still testable: MM P6 states the condition, SPEC S-16.3 says so, and fault injection for crash
  points before the ACQUIRE commit must use a retained bundle or a deterministic transport and clock (RA R4-11).

### F-10 An index code that Stage 02 does not have (defect, corrected)

- Draft: LOOKUP had a retryable code `INDEX_BUSY` and O-3 could end `BLOCKED`. Stage 02 raises `IndexUnavailable` only
  with `INDEX_MISSING`, `INDEX_CORRUPT` and `INDEX_FORMAT_MISMATCH` (`store.py`, `query.py`).
- Correction: LOOKUP has no retryable codes and uses Stage 02's codes; O-3 ends `FAILED`; the VALIDATE reason is
  `INDEX_PATH_INVALID` so that it is not confused with Stage 02's projection reason `INDEX_UNAVAILABLE`.

### F-11 MR-15 is met only in part (deviation)

- The Stage 01 brief's MR-15 asks for a per-investigation request budget and wall-clock budget with `timed_out` tasks.
  Stage 04 bounds work by `A_max`, `F_max`, Stage 03's per-request timeouts and extraction deadline, and ends a
  deferral in `BLOCKED` without waiting. It has no investigation-level timer and no `timed_out` state.
- Reason: one article investigation has one network step, already bounded by Stage 03; a timer would add a
  nondeterministic input to an otherwise replayable run.
- Owner decision point: accept this deviation, or ask for a wall-clock budget in the controller step (plan step 7).
  It is recorded in SPEC 17.2. No gate depends on it.

### F-12 `stale_detected` was not a listed record kind (defect, corrected)

- Draft: SPEC 9.4 used `stale_detected`, but the kind table 8.3 did not list it. Added to the execution layer.

### F-13 Replay was said to make an investigation `STALE` (defect, corrected)

- Draft: "a resume or replay found a changed input". Replay is read-only and writes nothing. Correction: only resume
  records `stale_detected`; replay reports `stale` (SPEC 9.4, 10.4; MM RP-1).

### F-14 Defined but unreachable record kinds (observation)

- `claim_superseded` and `question_closed` are never written in Stage 04: committed steps never re-run, and Stage 04
  has no resolution action. They are defined so that later stages can use them without a format change, and the fold
  and invariants M-8 and M-4 are tested on synthetic journals. `NEEDS_RESOLUTION` is therefore terminal in Stage 04.

### F-15 Root bound at ACQUIRE, not at creation (deviation)

- Plan 21 (I-14) fixes the root "at creation". For a capture request, `page_id` and `capture_sha256` are unknown until
  ACQUIRE commits, and D-4 requires the bundle identity in the root. Correction: the request key is fixed at creation
  (it names the investigation), the root is bound by the ACQUIRE commit, and records before it carry `root_id = null`
  (SPEC S-4.4, M-9). This refines the plan; gate 04-B is met.

### F-16 Lifecycle reduced to the smallest machine (deviation)

- Plan 20 has `INPUT_VALIDATED`, `DETECTED`, `VERIFIED` and `COMPLETE`; these are functions of the step states, so
  keeping them as lifecycle states would duplicate state. SPEC 9.4 has `CREATED`, `RUNNING`, `BLOCKED`,
  `NEEDS_RESOLUTION`, `COMPLETED`, `FAILED`, `STALE`, `CORRUPT`. The plan's "an identity conflict … can still complete
  with outcome `partial` and the open question listed" is `NEEDS_RESOLUTION` with outcome `partial`. The plan's record
  kinds `input_validated`, `investigation_finalized`, `blocker_opened` and `blocker_resolved` are likewise derivable
  (VALIDATE and VERIFY step records; `step_deferred` and the restart).

### F-17 Names realigned with the plan (defect, corrected)

- Draft: several plan class names and the step name NORMALIZE had been renamed without need. Restored:
  `CONTRADICTION_IN_SOURCES`, `UNRESOLVED_IDENTITY`, `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`, `CORRECTION_CITED`,
  `NO_IDENTIFIER`, NORMALIZE. Kept as new or narrowed, with reason: `LOOKUP_UNAVAILABLE` (the plan's `UNAVAILABLE`
  without extraction and index failures, which are now step failures), `UNRESOLVED_USE` (F-04).

### F-18 Plan invariants I-1 to I-14 (observation; mapping)

| Plan | SPEC | Plan | SPEC |
|---|---|---|---|
| I-1 output blobs exist | M-5, M-3 | I-8 interrupted attempt reported | W-6 |
| I-2 write order | M-3 | I-9 superseded claims reachable | M-8 |
| I-3 legal path of both machines | W-2 | I-10 step keys recomputed, STALE | S-10.1 |
| I-4 chain and `seq` | M-1, M-2 | I-11 single writer | M-11 |
| I-5 references exist | M-4, M-7 | I-12 COMPLETE implies completion | W-7 |
| I-6 no stronger status without new evidence | M-8 | I-13 identity conflict kept and routed | W-8 |
| I-7 no negative value | M-12 | I-14 root identity | M-9 (F-15) |

Plan step 6 names "I-1…I-12 tests"; they become tests of M-1 to M-14 and W-1 to W-8.

### F-19 Non-idempotent transitions (observation)

- A retried attempt writes the same content records as the failed one (ids are content-derived, MM CH-1); only the
  attempt that ends `step_succeeded` is committed (M-6), and a committed step is never started again (M-14). Blob
  writes are idempotent. No transition was found whose repetition changes the committed view.

### F-20 Memory and controller divergence (defect, corrected; otherwise observation)

- Draft: restarting a deferred step required "now ≥ `not_before`", a condition that cannot be checked from the journal
  afterwards. Correction: the condition is on the restart record's own `at` (SPEC 9.2, MM T-RESTART), so the fold and
  its legality check use the journal only. Otherwise the controller has no state outside `fold(J)` (W-1, MM FD-1).

### F-21 Negative versus unknown (observation)

- `NOT_FOUND_IN_CHECKED_SOURCES` and `UNRESOLVED_STATUS` (coverage gap) are separated by Stage 02's own value
  (F-3); no class or field means "not retracted" (MM P5); a failed step, a stale input, an unused definition and an
  absent identifier each have their own outcome. No ambiguity found.

### F-22 Replay ambiguity (observation)

- Replay has three exclusive results with a fixed precedence (`stale` before `reproduced` before `differs`), runs
  offline and writes nothing (MM 10.3). A corrupt blob is `CORRUPT`, never `differs`.

### F-23 Provenance (observation)

- The chain of SPEC S-12.1 was checked against the data each step records: index identity per LOOKUP attempt, full
  events with row hashes, Stage 03 anchors, coherence as evidence, rule id and table version. No missing link found.

### F-24 Hidden dependence on Stages 05 to 07 (observation)

- Markers are recorded and not interpreted (Stage 05); render reconciliation is not used for detection (S-6.1);
  cancellation, DOI or PMID subjects, history and cross-language comparison are excluded (SPEC 1.2, 17.2). The only
  forward-looking element is the extensible subject type, which Stage 04 defines. No dependence found.

### F-25 Requirements that are hard to test (observation)

- W-1 (no controller state outside the journal) is tested indirectly, by killing the process at every boundary and
  comparing the resumed state with `fold(J)`. R4-30 (independence of the reference model) and A-3 (local POSIX file
  system) are procedural or environmental and are disclosed in RA, not claimed as tested. Every other requirement
  names a test or a check in SPEC, MM or the plan's section 12.

## Contradictions with the retained plan or the gates

None found that changes an approved decision or a gate. F-01, F-11, F-15 and F-16 are deviations from the plan's
design text, each recorded with its reason; F-01 follows the owner's own instruction of 2026-11-10. They are listed for
the owner in the Step 3 report.
