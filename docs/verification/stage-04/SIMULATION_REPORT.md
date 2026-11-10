# Stage 04 Simulation Report (Step 4)

Scope: Step 4 of the Stage 04 plan, authorized by the owner on 2026-11-10 (message
`cmsg_018VCB51nDHP6HXmLU4ea5yPFigUhaer7vUNd5ng3Rh6qw`, approved head `fb39ede`). This report covers executable
reference models of the dt-1 decision table and of the Investigation Workflow Controller, built before any Stage 04
production code exists. No production code, schema, adapter or CLI was written. "Exhaustive" in this report always
means exhaustive over the declared finite abstraction or the declared finite controller model, never over real inputs.

Reproduce: `uv run python simulations/stage04/run_step4.py` (about 15 minutes on 4 vCPU). Fast checks:
`uv run pytest tests/stage04/test_simulation_step4.py`. Retained evidence: `docs/verification/stage-04/simulation/`.
Frozen oracle: `simulations/stage04/oracle/`.

## 1. Result summary

| Item | Result |
|---|---|
| Decision space | 12,632,448 abstract cases enumerated; 244,884 valid, 12,387,564 invalid; 20 properties, 0 violations |
| D-1 to D-17 | D-1 to D-4 and D-6 to D-16 reached by valid cases; D-5 and D-17 reached only by invalid cases (P1) |
| P1 to P5 | hold on the abstract domain (section 5) |
| P6 | holds in the controller model for a retained bundle; a live capture does not converge to one content identity (F-09, as SPEC 10.1 states) |
| Controller | 25,120 states, 61,992 transitions over 4 scenarios; 20 properties, 0 violations; no record appended inside any cycle |
| F-11 | **BLOCKED ON F-11** for the live-capture path; retained-bundle path bounded under assumptions E-1 to E-5 |
| F-09 | retained bundle: 1 content identity per completed run; live capture: 9 distinct content identities (one per ACQUIRE attempt) |
| Mutants | 19 injected (11 decision, 8 controller), 19 detected |
| Stage 02 conformance | 192 synthetic worlds on the real Stage 02 engine: 0 problems, signatures equal; 44 Stage 02 cases probed, 0 outside the contract |
| Specification corrections | 8 (SC-1 to SC-8), each with executable evidence (`review/step4/STEP4_SPEC_CORRECTIONS.md`) |

## 2. Architecture and independence

| Module (`simulations/stage04/`) | Role | Imports from `citerift` |
|---|---|---|
| `dt1_reference.py` | reference dt-1: abstract lookups, `Case`, contract predicates, coherence, the 17 guards, `decide` | none |
| `stage02_abstraction.py` | which lookup combinations Stage 02 can produce: 192 worlds, 93 pair signatures, `valid`/`invalid_reasons` | none |
| `decision_space.py` | full enumeration, 20 properties, oracle writer and reader | none |
| `controller_model.py` | step and lifecycle machine, append guard, controller and environment moves, exploration, properties | none |
| `mutants.py` | 11 decision and 8 controller mutants | none |
| `stage02_conformance.py` | runs the real Stage 02 `gather` on all 192 worlds and on the frozen Stage 02 cases | `citerift.retraction` only |
| `bounds.py` | F-11: symbolic bounds and two experiments against Stage 03's transport | `citerift.wiki` only |
| `run_step4.py` | orchestration and evidence writing | none |

Why it is independent (R4-30):

- No module imports `citerift.investigation` (it does not exist yet) or any future `detect.py`. The test
  `test_reference_models_are_independent_of_production_code` parses every module and enforces the table above.
- The reference model was written from SPEC 7.3 and MM 4.5 and 5.2, not from code. Stage 02 facts were then checked
  against the real engine (`stage02_conformance.py`), not copied from it.
- The property checker does not reuse the model's coherence or guards: `decision_space.kappa_of` restates κ from MM
  5.3 and the monotone guards from SPEC 7.3. Mutant MD-8 (coherence ignores the pair witness) is caught only because
  of this (review item R4S-01).
- The oracle is written once and frozen: `MANIFEST.json` is pinned by SHA-256 in the test file, and its
  `model_digest` is the SHA-256 of `dt1_reference.py` and `stage02_abstraction.py`. Any change to the semantics fails
  `test_oracle_is_frozen` until the digest is changed in a visible commit.
- Residual shared assumption: the validity table of contract projection forms (`WELL_FORMED`) is used both by the
  model and by the abstraction. It is checked against the real engine: every one of the 12 contract values the real
  engine produced is in the table, and none outside it.

## 3. Decision space

### 3.1 Domain

A case is: use eligibility (`CITED`, `UNUSED`, `USE_NOT_ESTABLISHED`), shape (`NONE`, `DOI`, `PMID`, `PAIR`), taint
reasons (3 bits, 8 sets), the `multi` flag, one abstract lookup per query (32 values: 20 contract forms and 12
malformed ones), and for `PAIR` the witness bits `wd`, `wp`, `w2` and `coname`. The domain is a full product, with no
sampling.

| Shape | Cases | Valid | Invalid |
|---|---:|---:|---:|
| NONE | 384 | 12 | 372 |
| DOI | 24,576 | 864 | 23,712 |
| PMID | 24,576 | 912 | 23,664 |
| PAIR | 12,582,912 | 243,096 | 12,339,816 |
| **Total** | **12,632,448** | **244,884** | **12,387,564** |

Validity means "Stage 02 and Stage 03 can produce this case under their accepted contracts". States and witness bits
are exact (derived from the 192 worlds); projections are over-approximated (any contract form of a state is
admitted), so properties on the valid domain are checked on a superset of what Stage 02 produces.

Invalid reasons (a case can have several): `SIGNATURE_UNREACHABLE` 11,826,288; `PROJECTION_OUTSIDE_CONTRACT`
9,529,344; `INVALID_QUERY_FOR_VALID_KEY` 1,144,704; `WITNESS_WITHOUT_PAIR` 46,440; `STATE_UNREACHABLE` 4,608;
`UNCONFIRMED_WITHOUT_KEY` 192.

Each case is decided and its rule, class, kind, disposition and reasons are recorded. 363 distinct decisions occur.
The run took 588.2 s with 4 workers.

### 3.2 Rules reached

| Rule | Class | Valid cases | Invalid cases | Valid shapes |
|---|---|---:|---:|---|
| D-1 | UNUSED_DEFINITION | 81,628 | 4,129,188 | all |
| D-2 | UNRESOLVED_USE | 81,628 | 4,129,188 | all |
| D-3 | NO_IDENTIFIER | 1 | 15 | NONE |
| D-4 | UNRESOLVED_IDENTIFIER | 3 | 109 | NONE |
| D-5 | (DETECT fails, ADAPTER_INCONSISTENT) | 0 | 4,067,784 | none |
| D-6 | IDENTITY_CONFLICT | 16,040 | 31,008 | PAIR |
| D-7 | CONTRADICTION_IN_SOURCES | 21,584 | 6,464 | DOI, PMID, PAIR |
| D-8 | UNRESOLVED_IDENTIFIER | 38,500 | 20,832 | DOI, PMID, PAIR |
| D-9 | UNRESOLVED_IDENTITY | 2 | 0 | PMID |
| D-10 | UNRESOLVED_IDENTITY | 2,933 | 0 | DOI, PMID, PAIR |
| D-11 | UNRESOLVED_STATUS | 419 | 0 | DOI, PMID, PAIR |
| D-12 | UNRESOLVED_STATUS | 13 | 50 | DOI, PMID, PAIR |
| D-13 | LOOKUP_UNAVAILABLE | 660 | 703 | DOI, PMID, PAIR |
| D-14 | positive class of the value | 1,456 | 0 | DOI, PMID, PAIR |
| D-15 | NOTICE_CITED | 9 | 0 | DOI, PMID, PAIR |
| D-16 | NOT_FOUND_IN_CHECKED_SOURCES | 8 | 0 | DOI, PMID, PAIR |
| D-17 | (DETECT fails, DECISION_TABLE_GAP) | 0 | 2,223 | none |

D-14 splits evenly over the four positive classes: `RETRACTED_WORK_CITED`, `CONCERN_CITED`, `CORRECTION_CITED` and
`REINSTATED_WORK_CITED`, 364 valid cases each.

Coverage notes:

- D-5 and D-17 are reached only by invalid cases. This is proposition P1: every valid case is decided by D-1 to D-16.
- D-9 is reachable only for a PMID-only candidate (2 valid cases). A DOI-only Stage 02 query is never ambiguous, and
  for a valid `PAIR` an ambiguous Q2 implies κ = INCOMPATIBLE, so D-6 fires first. SPEC 7.4 states both.
- `REINSTATED_WORK_CITED` is valid in the abstract domain (364 cases) but unreachable through Stage 04's calls.
  Stage 02 states `reinstated` only with supersession links, which `gather` takes as an argument Stage 04 never
  passes (SC-7). The real probes `X-reinstatement-alone` and `X-retraction-then-reinstatement` both return
  `matched` with an `uncertain` projection.
- O-1 to O-3 are investigation-level and are not inputs of the decision function. They are covered by the controller
  model through the `STALE` and `FAILED` lifecycle states.

### 3.3 Kinds

| Kind | Valid | Invalid |
|---|---:|---:|
| out_of_scope (D-1 to D-4) | 163,257 | 8,258,391 |
| abstain | 41,879 | 20,991 |
| needs_resolution (D-6, D-7) | 37,624 | 37,472 |
| positive (D-14) | 1,456 | 0 |
| abstain_unavailable (D-13) | 660 | 703 |
| not_found (D-16) | 8 | 0 |
| failure (D-5, D-17) | 0 | 4,070,007 |

No invalid case is positive or not-found. The per-dimension breakdown (DOI only, PMID only, each κ value of DOI+PMID,
taint, unavailability, notice, ambiguity) is in `decision_space_summary.json` under `dimensions`.

### 3.4 Properties

| Property | Statement (short) | Checked | Violations |
|---|---|---:|---:|
| TOTAL | exactly one rule of D-1 to D-17 decides every case | 12,632,448 | 0 |
| DETERMINISM | equal cases from fresh objects decide identically; first-true rule = minimum-index true guard | 12,632,448 | 0 |
| NO_NEGATIVE | no class, value or reason means "not retracted" | 12,632,448 | 0 |
| MONOTONE_GUARDS | a true monotone guard (D-5 invalid_query, D-6, D-7, D-8, D-13) gives no finding and no not-found | 12,495,312 | 0 |
| FAIL_CLOSED_INVALID | no invalid case yields a positive class or not-found | 12,387,564 | 0 |
| NO_FINDING_UNDER_CONFLICT | κ = INCOMPATIBLE never yields a positive class or not-found | 11,010,048 | 0 |
| UNKNOWN_PRESERVATION | an uncertain, ambiguous, gap, conflicting or malformed deciding lookup never yields a finding or not-found | 9,474,048 | 0 |
| STATUS_CONSISTENCY | status, value and disposition are functions of the class (SPEC 7.2, 7.6) | 8,562,441 | 0 |
| FAILURE_CONTAINMENT | an unavailable lookup never yields a finding or not-found; kind failure only from D-5 and D-17 | 5,214,711 | 0 |
| AB2_REASONS | every abstention, needs-resolution and failure carries a reason code | 4,209,336 | 0 |
| IDENTITY_DOMINANCE | a cited PAIR with κ = INCOMPATIBLE is IDENTITY_CONFLICT (or D-5 when invalid), whatever else holds | 3,670,016 | 0 |
| NOTICE_SEPARATION | notice_only never yields a finding; NOTICE_CITED has no value | 789,609 | 0 |
| P1_VALID_NO_FAILURE | no valid case reaches D-5 or D-17 | 244,884 | 0 |
| P2_VALID | valid PAIR, all lookups available: κ = INCOMPATIBLE iff Q2 is ambiguous_identity | 182,496 | 0 |
| POSITIVE_FROM_DECIDING | a positive class needs a matched deciding lookup with a verified_fact of the same value | 1,456 | 0 |
| P5_NOT_FOUND_CONDITIONS | NOT_FOUND_IN_CHECKED_SOURCES implies every condition of MM P5 | 8 | 0 |
| STRENGTHEN_UNAVAILABLE | making a lookup unavailable never creates a finding or not-found (pairs compared) | 36,616,704 | 0 |
| STRENGTHEN_TAINT | adding a taint reason never moves a case to a later tier or creates a finding (pairs compared) | 18,948,672 | 0 |
| STRENGTHEN_WITNESS | adding a witness bit never creates a finding; between valid cases never a later tier (pairs compared) | 18,874,368 | 0 |
| TAINT_CLASS_INDEPENDENCE | rule and class depend only on whether a taint reason is present (checked across chunks) | 12 | 0 |

### 3.5 Frozen oracle

`simulations/stage04/oracle/`: `MANIFEST.json` (SHA-256 `411050772807cfbc5e2053431307516344984a759c489c746a490f1db3e27735`,
pinned in the test), `dt1_decisions.json` (363 distinct decisions) and `dt1_table.u16le.gz` (one little-endian
`uint16` index per case, in enumeration order, 12,632,448 entries). Versions: model `dt1-reference/1`, table `dt-1`.
Model digest `7cdf2e1cd1548892791895285797496b4631ce58f61e6f5aa8795b344ff07811`. Gate 04-C's "reference-model
differential" will compare the production DETECT against this oracle.

## 4. Stage 02 conformance of the abstraction

- 192 worlds, each built as a real Stage 02 index and queried with the real `gather` (DOI, PMID, pair). 0 worlds with
  problems. The 24 signatures the abstraction predicts when every lookup is available are exactly the 24 the real
  engine produced (`signatures_equal`). The other 69 of the 93 pair signatures add the adapter's `unavailable`, which
  Stage 02 never produces.
- P2 and Stage 02 fact F-7 were checked on every world against the real labels and witnesses.
- 44 probes ran on the real engine: 40 frozen Stage 02 policy and tension cases and 4 extra probes (a PMID role
  collision and two reinstatements). 13 frozen cases were skipped because they need a Crossref bundle, supersessions
  or an unavailable index. Every real result is a contract value: 12 distinct
  values, 0 outside the contract.
- Of the 20 contract lookup values, 8 were not produced by the real engine. They are admitted from the code (MM F-2 to
  F-4, F-8). `unavailable` is made only by the Stage 04 adapter. The others are `vf:reinstated` (see SC-7) and the
  PMID-collision variants. The properties are checked with all 20 admitted, so this is an over-approximation.

## 5. Propositions P1 to P6

| Proposition | Result | Evidence |
|---|---|---|
| P1 totality, D-17 unreachable | holds on the abstract domain: 244,884 valid cases, none reach D-5 or D-17; all 12,632,448 cases decided | TOTAL, P1_VALID_NO_FAILURE |
| P2 coherence = Stage 02 pair rule | holds: 182,496 valid cases on the model; 192 worlds on the real engine | P2_VALID, `stage02_conformance.json` |
| P3 identity conflict preserved | (a) holds: 3,670,016 cases; (b) holds through CD-1, which the abstraction enforces (`MULTI_ON_PAIR` is invalid); (c) replay of claim ids is not checked here, because claim ids do not exist before production code; `decide` is a pure function (DETERMINISM) | IDENTITY_DOMINANCE, NO_FINDING_UNDER_CONFLICT |
| P4 monotone precedence | holds: 12,495,312 cases with a monotone guard; strengthening pairs compared 74,439,744 times in total | MONOTONE_GUARDS, STRENGTHEN_* |
| P5 no negative | holds: no value means "not retracted"; all 8 not-found cases satisfy every condition | NO_NEGATIVE, P5_NOT_FOUND_CONDITIONS |
| P6 resume equivalence | holds in the controller model for a retained bundle (1 content identity in every completed run); for a live capture, completed runs carry 9 distinct content identities, as SPEC 10.1 and owner decision F-09 require | RETAINED_RESUME_CONVERGES, `completed_content_identities` |

P6 is checked at the level of the model: content identity is abstracted as the identity of the capture that a run's
ACQUIRE committed. Byte-level digest equality after injected crashes is gate 04-E's fault-injection test and needs
production code.

Two Step 3 statements did not survive the executable model and were corrected before the final run
(`review/step4/STEP4_SPEC_CORRECTIONS.md`): D-5 let invalid pair combinations through as findings (SC-2), and
several guards accepted projections outside the contract (SC-1). After the corrections, P1 to P6 hold as stated
above.

## 6. Controller model

### 6.1 Model

- Eight steps in plan order (VALIDATE, ACQUIRE, EXTRACT, NORMALIZE, LOOKUP, DETECT, ASSEMBLE, VERIFY).
- Step states: pending, running, succeeded, failed_retryable, failed_terminal, deferred.
- Lifecycle states: CREATED, RUNNING, BLOCKED, COMPLETED, NEEDS_RESOLUTION, FAILED, STALE, CORRUPT.
- Counters: attempts and failures per step, deferrals for ACQUIRE, an open attempt, the root binding and the
  capture id.
- Budgets: `A_max = 3`, `F_max = 6`.
- The append guard (`legal`, MM section 8) is kept separate from the moves (`successors`): controller moves and
  environment moves (crash, interruption, failure, deferral, staleness, corruption, duplicate invocation). Every
  record proposed in every state is offered to the guard, and every refused proposal is categorized.
- Scenarios: request (retained bundle, live capture) × DETECT outcome (no question, a question).

Reduction R-1 (history quotient) forgets the counters of steps that have succeeded. It was checked against the full
space for budgets (2, 1) and (2, 2) in all four scenarios. In every one, the full space projected by R-1 equals the
quotient, the attempt maxima are equal and all property verdicts are equal (for example live, (2, 2): 76,714 full
states, 2,860 quotient states). The full space for (3, 6) was not built; R-1 at (3, 6) rests on that check plus the
argument in `normalize`.

### 6.2 Counts

| Scenario | States | Transitions | Terminal states | Proposals checked | Refused | Max records on a path |
|---|---:|---:|---:|---:|---:|---:|
| retained, no question | 2,894 | 7,063 | 1,426 | 283,612 | 279,618 | 70 |
| retained, question | 2,894 | 7,063 | 1,426 | 283,612 | 279,618 | 70 |
| live, no question | 9,666 | 23,933 | 4,726 | 947,268 | 933,734 | 88 |
| live, question | 9,666 | 23,933 | 4,726 | 947,268 | 933,734 | 88 |
| **Total** | **25,120** | **61,992** | | **2,461,760** | **2,426,704** | |

Every lifecycle state and every step state is reached in at least one scenario. Attempt maxima: ACQUIRE of a live
capture 9 (= `A_max + F_max`), every other step and ACQUIRE of a retained bundle 3 (= `A_max`). This is the exact
bound now in SPEC 9.2 and W-4 (SC-5); the Step 3 bound `A_max + F_max + 1` is never reached.

### 6.3 Properties (0 violations in every scenario)

- **Record legality:** EMITTED_RECORD_LEGAL, FORBIDDEN_REFUSED.
- **Terminal behavior:** NO_ESCAPE_FROM_TERMINAL_STEP, NO_ESCAPE_FROM_TERMINAL_LIFECYCLE, TERMINAL_REFUSES_ALL.
- **Budgets:** COUNTERS_MONOTONE, RETRY_BUDGET, DEFERRAL_BUDGET, BLOCKED_ONLY_WHEN_DEFERRED.
- **Recovery and idempotency:** RECOVERY_FIRST, DUPLICATE_INVOCATION_IDEMPOTENT.
- **Root and content:** NO_CONTENT_BEFORE_ROOT, ROOT_IMMUTABLE, RETAINED_RESUME_CONVERGES.
- **Completion:** COMPLETED_ALL_SUCCEEDED, CONFLICT_NEVER_COMPLETED, NEEDS_RESOLUTION_PARTIAL.
- **Cycles and termination:** NO_RECORD_IN_ANY_CYCLE, TERMINAL_REACHABLE_FROM_EVERY_STATE, STATE_SPACE_FINITE.

Cycles exist (368 non-trivial SCCs per retained scenario, 1,236 per live one). They are waiting in BLOCKED (an
invocation that exits) and a second invocation answered BUSY. Tarjan's algorithm over every reachable transition finds
no SCC containing a transition that appends a record. From every non-terminal state a terminal state is reachable.
No state space reached the exploration limit of 400,000 states.

## 7. F-11: boundedness

**Result: BLOCKED ON F-11 for the live-capture path.**

| Quantity | Retained bundle | Live capture |
|---|---:|---:|
| attempts, all steps | 24 (`8 × A_max`) | 30 (`7 × A_max + A_max + F_max`) |
| execution records | 50 | 62 |
| isolated-worker wall time (2 × 30 s per call) | 720 s (ACQUIRE bundle check 180, EXTRACT 180, VERIFY 360) | EXTRACT and VERIFY 540 s; ACQUIRE in the next row |
| live ACQUIRE as designed | — | 1,620 s (9 × 180 s), only if the response head arrives within the timeout |

The live-capture path has no upper bound that follows from the configured limits. Two experiments ran on the real
Stage 03 transport, `citerift.wiki.fetch.urllib_transport`, against a local server (`f11_bounds.json`):

- a response head dripped one byte every 0.5 s held a 1.0 s timeout for 6.01 s and then returned status 200;
- an endless stream of `100 Continue` interim responses, one every 0.5 s, held a 1.0 s timeout for 6.0 s.

Python's socket timeout bounds each receive, not the whole response head, and `http.client` skips any number of
`100 Continue` responses. Name resolution (`getaddrinfo`) takes no timeout argument in Python, so its duration is set
by the resolver configuration. This one is stated from the API, not measured. The test
`test_f11_characterization_response_head_is_not_bounded_by_the_timeout` keeps the first experiment as a
characterization: it fails if Stage 03 ever bounds the head, so the conclusion can be revisited.

The retained-bundle path is bounded under assumptions E-1 to E-5 (`f11_bounds.json`, `symbolic.assumptions`):

- **E-1:** local reads of regular files complete.
- **E-2:** write, fsync and rename on a local file system complete.
- **E-3:** the isolated worker creates no process outside its session.
- **E-4:** the process is not suspended.
- **E-5:** BLOCKED is an exit, not a wait.

With these, every local step has a stated size bound from Stage 03 caps. The bound is 720 s of isolated-worker time
plus that finite local work. No local step is called "deterministic" in place of a bound; the table in
`f11_bounds.json` (`symbolic.local_work`) names the work and its bound per step.

Recommendation (owner decision; not implemented in Step 4):

- Before Step 7, bound each live ACQUIRE attempt at the Stage 04 boundary, without changing Stage 03.
- Run the capture in a child process in its own session, and kill the session after
  `T_acq = deadline_s + op_timeout_s + 30 s` = 240 s with the configured values.
- Record the kill as a retryable ACQUIRE failure `ACQUIRE_WALL_CLOCK_EXCEEDED`, counted in φ.
- Then live ACQUIRE ≤ 9 × 240 s = 2,160 s. The investigation-level bound becomes a derived constant (that plus the
  retained-path terms) rather than a separate timer.

## 8. F-09: same digest

- **Retained bundle:** every completed run in the model carries one content identity, capture id 0, whatever the
  crashes and retries (RETAINED_RESUME_CONVERGES). Mutant MC-8, which re-acquires a retained bundle as a new capture
  on each attempt, is detected.
- **Live capture:** completed runs carry 9 distinct content identities, capture ids 1 to 9, one per ACQUIRE attempt
  that may commit. A live capture interrupted before ACQUIRE commits therefore does not claim the same digest.
- Gate 04-E is not weakened. Its "identical content digest after every injected crash" applies with the condition of
  P6, an equal committed ACQUIRE output.

## 9. Mutants

Each mutant changes one function of a reference model. Decision mutants run on the mutant domain of
`mutants.mutant_domain`: every NONE, DOI and PMID case and every cited, untainted PAIR case with contract or unavailable
lookups (197,712 cases). Controller mutants run on all four scenarios, with the exploration limit lowered to 60,000
states because some mutants make the space infinite (STATE_SPACE_FINITE then reports the truncation, and the edge
properties still run). For each mutant, `simulation/mutants.json` retains the properties that caught it and the number
of violating cases or transitions; the tests re-check every mutant on a reduced domain (13,744 cases).

| Id | Mutation | Required by the owner |
|---|---|---|
| MD-1 | swap identity-conflict (D-6) and positive (D-14) precedence | yes |
| MD-2 | remove the catch-all D-17 | yes |
| MD-3 | hide lookup-unavailable as no-record | yes |
| MD-4 | treat no-record as "not retracted" | yes |
| MD-5 | plan draft order: D-13 before D-6 (owner decision F-01 forbids it) | |
| MD-6 | remove D-5 | |
| MD-7 | count a notice as the retracted work | |
| MD-8 | coherence ignores the pair query's witness | |
| MD-9 | ignore identifier taint | |
| MD-10 | positive guard reads only the status | |
| MD-11 | D-5 as written in Step 3 | |
| MC-1 | append guard permits an edge out of succeeded | yes |
| MC-2 | a committed step is rerun | yes |
| MC-3 | retry counter reset when an attempt starts | yes |
| MC-4 | NEEDS_RESOLUTION reported as COMPLETED | yes |
| MC-5 | retry budget off by one | |
| MC-6 | a seventh deferral allowed | |
| MC-7 | root-binding rule M-9 removed from the guard | |
| MC-8 | retained bundle re-acquired as a new capture (F-09) | |

Result: 19 injected, 19 detected. The unmutated baseline has 0 decision and 0 controller violations on the same
domains. Examples from `mutants.json`: MD-1 is caught by IDENTITY_DOMINANCE (928 cases) and five other properties;
MD-2 by TOTAL (46 cases fall through); MD-4 by NO_NEGATIVE (8); MD-11 by FAIL_CLOSED_INVALID (1,416); MC-4 by
CONFLICT_NEVER_COMPLETED (96 states); MC-8 by RETAINED_RESUME_CONVERGES (2 violations).

## 10. Traceability

| Evidence | SPEC | MM | Gate | Risks |
|---|---|---|---|---|
| TOTAL, DETERMINISM, P1_VALID_NO_FAILURE, oracle | 7.1, 7.3 | 5.2, P1 | 04-C | R4-30 |
| NO_NEGATIVE, P5_NOT_FOUND_CONDITIONS, MD-4 | 7.2, 7.5, S-7.5 | P5, M-12 | 04-C, 04-G | R4-02 |
| FAIL_CLOSED_INVALID, UNKNOWN_PRESERVATION, MD-6, MD-10, MD-11 | 7.3 D-5, D-17, S-6.12 | 4.5 F-1 to F-9, 5.2 | 04-C | R4-01, R4-29 |
| IDENTITY_DOMINANCE, NO_FINDING_UNDER_CONFLICT, P2_VALID, Obokata test, MD-1, MD-5, MD-8 | 6.5, 7.3 D-6, S-7.3 | 5.3, P2, P3 | 04-D | R4-03, R4-29 |
| NOTICE_SEPARATION, MD-7 | 7.3 D-15, 7.4 | 4.5 | 04-C | R4-04 |
| STRENGTHEN_TAINT, TAINT_CLASS_INDEPENDENCE, MD-9 | 6.6, D-4, D-8, S-6.6 | 4.3, P4 | 04-C | R4-05 |
| FAILURE_CONTAINMENT, STRENGTHEN_UNAVAILABLE, MD-3 | 7.3 D-13, 9.3 | 4.5, P4 | 04-G | R4-02, R4-23 |
| Stage 02 conformance | 3.2, 7.4 | 4.5 | 04-C, 04-D | R4-29, R4-30 |
| Controller legality and terminal properties, MC-1, MC-2, MC-4 | 9.2, 9.4, W-2, W-5, W-7 | 7.2, 8, 9 | 04-E | R4-09, R4-25 |
| RECOVERY_FIRST, DUPLICATE_INVOCATION_IDEMPOTENT | 9.6, 10.1, W-6 | 8 | 04-E | R4-10, R4-12 |
| RETRY_BUDGET, DEFERRAL_BUDGET, NO_RECORD_IN_ANY_CYCLE, MC-3, MC-5, MC-6 | 9.2, W-4 | TR-4 | 04-E, 04-G | R4-13, R4-31 |
| STALE reached, O-1 | 10.3 | 10.2 | 04-F | R4-11 |
| NO_CONTENT_BEFORE_ROOT, ROOT_IMMUTABLE, MC-7 | 4.1, S-4.4, M-9 | 3.1 | 04-E | R4-25 |
| RETAINED_RESUME_CONVERGES, MC-8 (F-09) | 10.1 | P6 | 04-E | R4-11 |
| F-11 symbolic bounds and experiments | 9.2, MR-15 | TR-4 | 04-E, 04-G | R4-13 |

All risks stay open in `RISK_ANALYSIS.md`. This evidence is about the models; the gates are passed by production code
in later steps.

## 11. Limits of this evidence

- The decision domain is an abstraction. Reason codes `DEFINITION_UNUSED`, `USE_NOT_ESTABLISHED`,
  `STAGE02_BASIS_REASONS` and `LOOKUP_UNAVAILABLE` are placeholders for inputs the abstraction does not carry, and the
  oracle compares them as placeholders.
- Projections are over-approximated, and cross-lookup constraints between projections are not modelled.
- An invalid input in a unit that is not cited, or that has no key, is decided by tier 2 (out of scope) before D-5
  can see it. This yields no finding, but it is not reported as `ADAPTER_INCONSISTENT`. It concerns 8,258,391
  invalid cases of kind `out_of_scope`.
- The controller model uses reduction R-1. It was checked at (2, 1) and (2, 2), not at (3, 6).
- The F-11 experiments characterize the transport against a local server; they are not measurements of real
  Wikimedia behavior.
- Nothing here verifies Stage 04 production code, which does not exist yet.

Adversarial review: `review/step4/STEP4_ADVERSARIAL_REVIEW.md`. Specification corrections:
`review/step4/STEP4_SPEC_CORRECTIONS.md`. Owner decisions recorded: `review/step4/STEP4_OWNER_DECISIONS.md` (D-041).
