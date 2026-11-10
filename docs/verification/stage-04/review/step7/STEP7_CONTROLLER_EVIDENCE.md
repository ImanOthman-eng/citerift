# Stage 04 Step 7: Investigation Workflow Controller, evidence

Baseline is `7ad1e14` (Step 6 accepted). This step covers the Workflow Controller over deterministic fake adapters
only. There is no real Stage 02 or Stage 03 adapter, no Detection Engine, no report assembly and no CLI. The frozen
Step 4 model (`simulations/stage04/`) and Investigation Memory (`memory.py`, `fold.py`, `journal`/`blobs`) are not
changed.

Companion evidence in this folder:

- `STEP7_BUILD_VS_ADOPT.md`: owner item 1.
- `STEP7_RESOURCE_BOUNDS.md`, `resource_bounds.py`, `resource_bounds.json`: item 17.
- `STEP7_INHERITED_AUDIT.md`: items 18 and 19.
- `run_mutants.py`, `mutation_results.json`: item 22.
- `STEP7_REVIEW.md`: item 23.

## 1. Architecture

```
journal + blobs ──fold (Step 6)──> Folder ──workflow.derive──> WorkflowState / NextAction / explanation
                                     │
WorkflowController.step():  guard(proposal, Folder) ──> Memory.append  (every record, one path)
                            adapter(StepRequest) ──> closed StepResult ──> controller validates ──> records
```

| Module | Owns |
|---|---|
| `workflow.py` (pure, no I/O) | The fixed plan `STEPS`, `A_MAX` = 3, `F_MAX` = 6, and the retryable code sets. The step view (state, `phi`, `f`, attempts, `not_before`). The lifecycle, the next legal action, the outcome, `explain`. The guard (MM 8 with W-3 to W-8). `check_journal` (W-2 to W-8 over a whole journal). Step keys and their manifest. The controller identity. |
| `controller.py` | `WorkflowController`: recovery (W-6), staleness (S-10.1), one attempt through an adapter, and validating the result into records. `open_controller` (read-only `check_journal` first, keeping the D-044 order, then writable). `run_investigation`. |
| `adapters.py` | The closed adapter protocol (section 2). |
| `ids.py` | Step keys `K(s)` and child ids. All are SHA-256 over canonical JSON with a domain tag. None is random, and none depends on display text. |

There is one authoritative state: `fold(journal + blobs)`. The controller keeps exactly two in-process fields:

- `_own`, the attempts this process opened, used to tell its own open attempt from a dead process's (W-6);
- `_broken`, which makes the controller unusable after an unrecorded defect.

Neither is persisted, and neither affects what a later process derives. There is no controller-state file, no
checkpoint database and no global variable. The clock is injected and shared with Memory (`CLOCK_NOT_SHARED`
refused). `MonotoneClock` never goes back.

## 2. Adapter protocol

```
StepRequest(step, attempt, step_key, live, request, inputs, committed, content_digest, read_blob)   (deep copies)
StepResult = Succeeded(records, blobs, outputs, root) | Failed(code, reason, detail, not_before, wall_clock,
             retry_after_known) | Deferred(not_before)
ContentRecord(kind, payload)
```

An adapter never touches Memory. The controller does all of the following:

- publishes the result's blobs;
- checks each content kind against the step (`CONTENT_KINDS`);
- for DETECT, derives decisions and questions from the claims (SPEC 7.6, 7.7);
- applies CH-1 (`evidence_problem`) and W-8 (`detect_problem`);
- binds the root only in ACQUIRE;
- adds the step manifest as the last output;
- appends every record through the guard and then Memory.

Any other result type, a mutated or non-serialisable payload, a code that belongs to the controller, a `not_before`
outside live ACQUIRE, a naive datetime, a wall clock on the wrong code, or a root on the wrong step is a defect:

- where the step has a schema-legal defect code (`DEFECT_CODE`), it ends the step as a terminal failure;
- where it has none (VALIDATE, EXTRACT, LOOKUP), it raises `AdapterDefect` and the attempt stays open for W-6. This is
  owner decision point IA-11.

Memory's size refusals become `STORAGE_ERROR` with the limit as reason. If even the closing record cannot be written,
the controller raises `StorageExhausted` (resource-bound review).

The fake adapters (`tests/stage04/controller_support.py`, `Plan`) script, per (step, attempt):

- success;
- retryable failure;
- terminal failure;
- deferral with `not_before`;
- an exception;
- real process death (`os._exit`);
- a callable;
- `IDENTITY_CONFLICT`, `CONTRADICTION_IN_SOURCES`, not-found, lookup-unavailable and retracted DETECT claims.

Stale identity comes from the `Env` identity source.

## 3. W-1 to W-8 traceability

All tests are in `tests/stage04/`.

| W | Implementation | Positive test | Negative / adversarial test |
|---|---|---|---|
| W-1 state is a function of the journal | `workflow.derive` and `explain` read only the `Folder`; no persisted controller state | `test_controller_guard.py::test_w1_state_is_a_function_of_the_journal`; `test_controller_resolution_stale.py::test_two_independent_runs_write_identical_journals` | `test_controller_crash.py` (every resume re-derives from the journal alone) |
| W-2 only legal paths | `workflow.guard` before every append; `check_journal` replays it over the whole journal on open | `test_controller_guard.py::test_transition_matrix` (14 legal) | `test_w2_illegal_path_in_a_memory_valid_journal_is_corrupt`; `test_corrupt_journal_with_a_torn_tail_is_not_repaired` |
| W-3 plan order, one open attempt | `guard`: `T-START`, `T-RESTART` branches | `test_controller_run.py::test_happy_path_runs_the_fixed_plan_in_order` | `test_w3_plan_order_violation_is_corrupt`; `test_w3_overlapping_attempt_is_refused_before_it_is_written`; matrix (9 early EXTRACT starts) |
| W-4 exact budgets | `guard` failure and deferral branches; `controller._fail` and `_defer` | `test_extract_retries_below_the_budget_then_succeeds[0,1,2]`; `test_deferrals_up_to_the_budget_then_success[1,5,6]`; `test_nine_attempts_can_still_succeed` | `test_third_retryable_failure_is_retry_budget_exhausted`; `test_seventh_deferral_is_deferral_budget_exhausted`; `test_acquire_reaches_nine_attempts_and_no_more`; `test_w4_budget_exhaustion_before_the_budget_is_corrupt`; `test_w4_retryable_failure_past_the_budget_is_corrupt` |
| W-5 terminal admits nothing | `guard` first branch; `next_action` returns `terminal` | `test_run_on_a_terminal_investigation_reports_it_and_appends_nothing` | `test_w5_record_after_terminal_is_corrupt_and_refused[...]`; `test_stale_investigation_is_terminal_for_every_later_run` |
| W-6 resume closes the open attempt first | `controller.recover`; `guard` (`orphan`) | `test_w6_resume_closes_the_open_attempt_first`; `test_controller_crash.py` (all) | `test_w6_an_orphan_attempt_cannot_be_continued`; `test_repeated_death_of_a_step_without_retryable_codes_ends_it` |
| W-7 completion predicate | `_guard_success` (ASSEMBLE report, VERIFY passed over C(J)); `workflow.outcome` | `test_w7_positive_completed_has_a_passed_verification_of_cj` | `test_w7_completion_without_the_predicate_is_corrupt[...]` |
| W-8 needs-resolution content | `detect_problem` in `_guard_success` and `check_journal`; `controller._content` derives the decision and the question | `test_conflict_routes_to_needs_resolution[IDENTITY_CONFLICT, CONTRADICTION_IN_SOURCES]` | `test_conflict_and_finding_for_one_candidate_is_refused`; `test_guard_refuses_detect_content_that_breaks_w8[4 forgeries]`; `test_w8_conflict_claim_without_its_question_is_corrupt` |

## 4. Transitions

`test_transition_matrix` puts 11 proposals to each of 10 step states:

- the 6 SPEC states;
- running with content;
- running orphan;
- pending after interrupt;
- deferred, both not ready and ready.

It also tries an early EXTRACT start in the 9 states other than succeeded. The result is **14 legal and 105
refused**, each with the expected rule (MM 8, W-3 to W-6, M-6, TR-2).

The forbidden transitions the owner listed are all among the refused:

- pending → succeeded or failed without a start;
- succeeded → anything;
- failed_terminal → anything;
- overlapping attempts;
- restarting a succeeded step;
- k+1 before k;
- a wrong attempt number;
- a retry-counter reset (mutant MS-2).

`test_every_transition_rule_is_used_by_controller_runs` shows that real controller runs reach every legal rule.

## 5. Budgets, not_before and the D-042 wall clock (`test_controller_run.py`, 42 tests)

**Retries.**

- EXTRACT with 0, 1 or 2 retryable failures succeeds.
- The 3rd failure is `RETRY_BUDGET_EXHAUSTED`, with the original code as reason.
- A restart after exhaustion appends nothing.
- Counts carry across processes.
- A non-retryable code is terminal at once.
- Network codes are retryable only for a live capture.

**Deferrals.**

- 1, 5 and 6 deferrals followed by success all complete.
- The 7th deferral is `DEFERRAL_BUDGET_EXHAUSTED`.
- 6 deferrals and 2 failures followed by a third failure ends at exactly **9 attempts**, and a 9th attempt can still
  succeed.
- Deferral is refused outside live ACQUIRE.

**not_before.**

- No `not_before`: restart at once.
- A future one: the run returns `wait`, with no sleep.
- Boundaries: just before (−1 µs) refuses; exactly at the instant and just after (+1 µs) start. This holds for both
  deferral and failure.
- After process death, `not_before` is still honoured.
- A forged early restart record is refused by the guard.

**D-042 wall clock.**

- `ACQUIRE_WALL_CLOCK_EXCEEDED` with a known Retry-After status is retryable and honours `not_before`.
- With an unknown status it is terminal: retry safety is unknown, so the fallback is terminal.
- The third one exhausts the budget.
- On a retained bundle it is a defect.
- Malformed wall-clock failures are defects.

## 6. Crash and resume (`test_controller_crash.py`, real process death)

A forked child runs the controller and dies with `os._exit` at a boundary: no `finally` runs and nothing is flushed.
The reference run (NEEDS_RESOLUTION, two candidates) reaches the six boundaries this many times:

| Boundary | Times reached |
|---|---:|
| `before_start` | 8 |
| `after_start` | 8 |
| `after_adapter` | 8 |
| `after_blobs` | 8 |
| `after_content` | 16 |
| `after_terminal` | 8 |

That gives **56 deaths**, one at every occurrence. On top of these:

- 8 deaths inside each step's adapter;
- 1 death after the final VERIFY;
- crash mixed with failure (EXTRACT: death, retryable failure, death → `RETRY_BUDGET_EXHAUSTED`);
- repeated death of DETECT (→ `RETRY_BUDGET_EXHAUSTED`, reason `STEP_INTERRUPTED`).

After every death the parent resumes in a new process and checks:

- the journal reopens and `check_journal` passes;
- the open attempt is closed first by `step_interrupted` (W-6) and `phi` goes up by exactly 1;
- no succeeded step's adapter is called again, and every step has exactly one `step_succeeded`;
- the interrupted attempt's content is not in the committed view;
- the committed content equals the uninterrupted run's;
- a terminal investigation appends nothing;
- history is never rewritten (the old journal is a prefix of the new one).

The owner's boundaries map as follows:

| Owner boundary | Controller boundary |
|---|---|
| before step_started | `before_start` |
| after step_started | `after_start` |
| during the adapter | adapter death |
| after the adapter, before content | `after_adapter` / `after_blobs` |
| after content, before the terminal record | `after_content` |
| after step_succeeded / before the next start | `after_terminal` and the next `before_start` |

Limitation, as in Step 6: process death keeps the page cache. Power loss is argued from the fsync order, not tested.

## 7. Needs-resolution and staleness (`test_controller_resolution_stale.py`, 30 tests)

**Needs-resolution.** `IDENTITY_CONFLICT` and `CONTRADICTION_IN_SOURCES` each produce:

- retained evidence;
- the claim;
- a `ROUTE_NEEDS_RESOLUTION` decision;
- an open question of the matching kind;
- no other claim for the candidate;
- lifecycle `NEEDS_RESOLUTION` with outcome `partial`.

A rerun appends nothing, and replay from the journal gives the same state. Further checks:

- A conflict together with a finding for the same candidate is refused (W-8).
- A conflict next to a finding for another candidate is still `NEEDS_RESOLUTION`.
- Lookup-unavailable completes with outcome `partial`.
- An unknown class is `DECISION_TABLE_GAP`.
- Forged DETECT content (a dropped question, a dropped decision, a wrong disposition, a question on not-found) is
  refused.

**Staleness.** Changing any of these gives `STALE`:

- the 10 environment identities: request, capture/root, extractor, profile, config, index, schema version, table
  version, effective configuration, D-042 bound;
- the 3 controller identities: plan version, `A_max`, `F_max`.

In every case nothing committed is reused and no step is rerun in place. An unchanged identity resumes without
rerunning. A change in the middle of a run stops it. An identity that cannot be computed is a failure, not
staleness. An inconsistent `stale_detected` is refused.

## 8. Step keys and child ids

The step key is `K(s) = H("citerift-step/1", s, plan version, out(dep(s)), id_s, config digest)`. Here `id_s` is the
digests of the identities the step depends on, and the controller identity is part of `id_s`.

- Two independent runs write byte-identical journals.
- Keys ignore the display title and change with each input.
- The domain tags of child ids (evidence, claim, decision, question, identity) are distinct.

## 9. Differential against the frozen Step 4 model (`test_controller_differential.py`)

`MODEL_SHA256` pins `controller_model.py`; `test_reference_model_is_the_frozen_one` passes.

The walks are seeded and follow the model's own `successors`. Each event is performed on real Memory with the
production primitives. In every state, every record of the model's alphabet is proposed to both sides. 10 walks per
scenario:

| Scenario | States compared | Proposals | Agree | Classified | Next actions compared | End lifecycles |
|---|---:|---:|---:|---:|---:|---|
| retained | 204 | 17,934 | 17,877 | 57 (SUCCESS_FLAG 42, W6_STRICTER 15) | 61 | COMPLETED 2, FAILED 2, STALE 3, CORRUPT 3 |
| retained, conflict | 234 | 21,168 | 21,094 | 74 (47, 27) | 69 | NEEDS_RESOLUTION 2, FAILED 4, STALE 2, CORRUPT 2 |
| live | 168 | 14,994 | 14,958 | 36 (27, 9) | 60 | FAILED 7, STALE 2, CORRUPT 1 |
| live, conflict | 224 | 18,914 | 18,872 | 42 (28, 14) | 75 | NEEDS_RESOLUTION 1, FAILED 7, STALE 1, CORRUPT 1 |
| **Total** | **830** | **73,010** | **72,801** | **209** | **265** | all terminal lifecycles reached; BLOCKED reached (live) |
| live, directed at the budgets (review F6) | 293 | 24,304 | 24,286 | 18 (SUCCESS_FLAG 18) | 117 | FAILED 9, CORRUPT 1; reaches f = 6, phi = 2, 9 attempts |

Every discrepancy is classified, and the test fails on any unclassified one.

| Class | Category | Meaning |
|---|---|---|
| `W6_STRICTER` | specification, neither side defective | The model's `legal` encodes MM 8 alone and allows continuing a dead process's attempt. Production refuses by W-6 (SPEC 9.9), which the model enforces only through `successors`. `test_w6_stricter_is_the_only_orphan_discrepancy`: 4 records. |
| `SUCCESS_FLAG` | abstraction | The model's `step_succeeded` carries an "opens a question" flag. In production that is a property of the content, so only the matching flag is compared. |
| Input change before any commit | reference-model over-approximation | The model's `env_changed` flag is sticky, so a change before the first commit makes it STALE. SPEC S-10.1 defines staleness over committed keys, so production is not STALE. Checked separately (`test_input_change_before_any_commit`). The oracle is not changed, and the evidence is here. |
| Production defect found and fixed | production defect | `stale_payload` raised `WorkflowCorrupt` when committed steps' manifests recorded different identity digests. That is reachable when an identity changes between steps of one process. Production now reports `STALE` with the first differing digest per component. |

No discrepancy needed the oracle to change.

## 10. Adversarial (`test_controller_adversarial.py`, 61 tests) and guard (`test_controller_guard.py`, 20 tests)

The adversarial tests cover:

- an exception in each step;
- a controller left unusable after an unrecorded defect;
- `BaseException` passed through;
- 21 malformed results;
- a live root of another revision, and a retained root of another capture;
- a naive datetime;
- an adapter that mutates its request;
- idempotent blobs;
- a duplicate invocation while one is running (`INVESTIGATION_BUSY`, nothing written);
- corrupt record or blob reported `CORRUPT` and not changed;
- stale is terminal for every later run;
- explanations;
- request isolation;
- record, blob and journal limits (`STORAGE_ERROR` / `StorageExhausted`);
- the review findings F1 to F4 (`STEP7_REVIEW.md`):
  - non-canonical content is a step defect;
  - a `not_before` outside the schema range is refused;
  - a full disk during a blob write is `STORAGE_ERROR`;
  - an adapter output equal to the manifest is refused;
  - corruption found while running is reported `CORRUPT`;
  - two claims for one candidate are refused.

The guard tests add forged Memory-valid journals for each W, which are reported `CORRUPT` with the files unchanged.

## 11. Observability

`WorkflowController.explain()` (from `workflow.explain`) is computed from the fold alone. It returns:

- `lifecycle` and `outcome`;
- `next`: action (`start`, `wait`, `recover`, `terminal`), step, attempt, the deciding rule, a reason, and
  `not_before`. This answers why this step is next, why the run is blocked (`wait`, `T-RESTART`, the instant), and
  why a retry is permitted (`T-RESTART`) or refused (`TR-2`, W-4, W-5);
- `steps`: per step the state, attempts, `phi`, `f`, `a_max`, `f_max`;
- `open_questions`, which says why the investigation needs resolution;
- `terminated_by` for every terminal lifecycle other than CORRUPT:
  - the `stale_detected` record with its `changed` names (the record itself also holds `recorded` and `current`);
  - or the terminal `step_failed` with code, reason and detail;
  - or the final VERIFY success with its open questions.

No second log exists. Tested by `test_explanation_names_rule_and_reason` and `test_explanations_say_why`.

## 12. Mutation testing (`run_mutants.py`, `mutation_results.json`)

Each mutant is one deliberate defect, applied to a temporary copy of `src` and never to the repository. A probe checks
that the copy is the code under test. The 173 controller tests then run against it with `-x`. The unmutated copy runs
first as a control: **173 passed**. Final run, after the review fixes: **10 mutants, 10 detected, 0 survived**.

| ID | Owner's mutant | First detecting test |
|---|---|---|
| MS-1 | permit a succeeded step to restart | `test_controller_guard.py::test_transition_matrix` |
| MS-2 | reset the retry count (only the last attempt counts) | `test_controller_adversarial.py::test_adapter_exception_fails_closed[VALIDATE]` |
| MS-3 | ignore `not_before` (schedule and guard) | `test_controller_adversarial.py::test_explanations_say_why` |
| MS-4 | allow step k+1 before k | `test_controller_differential.py::test_differential_random_walks[retained]` |
| MS-5 | allow continuing after a terminal lifecycle | `test_controller_adversarial.py::test_stale_investigation_is_terminal_for_every_later_run` |
| MS-6 | turn NEEDS_RESOLUTION into COMPLETED | `test_controller_crash.py` reference fixture (error: its run must end NEEDS_RESOLUTION) |
| MS-7 | drop the open question (neither derived nor required) | `test_controller_crash.py` reference fixture (error) |
| MS-8 | repeat a committed step (DETECT offered again) | `test_controller_adversarial.py::test_adapter_exception_fails_closed[ASSEMBLE]` |
| MS-9 | ignore a changed step key (no staleness) | `test_controller_adversarial.py::test_stale_investigation_is_terminal_for_every_later_run` |
| MS-10 | treat an adapter exception as success | `test_controller_adversarial.py::test_adapter_exception_fails_closed[VALIDATE]` |

`-x` stops at the first failure, so the table names only the first test to detect each mutant; others may detect it
too. MS-6 and MS-7 are detected as fixture errors: the module's reference run asserts its own lifecycle before any
crash. In a separate run without `-x`, `test_conflict_routes_to_needs_resolution` (both classes) was checked against the
same two mutants: **2 failed** for MS-6 and **2 failed** for MS-7.
