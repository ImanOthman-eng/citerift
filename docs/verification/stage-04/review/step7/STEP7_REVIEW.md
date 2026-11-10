# Stage 04 Step 7: fresh-context adversarial review (owner Step 7 item 23)

**This is not the formal Step 12 independent review.** It is a Step 7 review by a separate reviewer context (a
subagent started with no conversation history). That context was given:

- the repository;
- the specification, the mathematical model and the frozen Step 4 model;
- the owner's thirteen review areas.

It changed no repository file. It wrote its probe scripts outside the repository and ran them. The Step 12 review
must still cover the Memory/controller boundary, D-044 and D-046, as the owner directed.

The reviewer ran targeted tests and probe scripts. It did not run the full suite, ruff, mypy or `citerift-gov
check`; those are run at the exit criteria.

## Findings and dispositions

Fail-first evidence is the reviewer's probe output before the fix, reproduced by the implementer on the unfixed tree.
After the fix, the same probes and the new regression tests give the fixed behaviour.

| ID | Severity | Finding | Before the fix (probe output) | Fix | Regression test (`test_controller_adversarial.py`) |
|---|---|---|---|---|---|
| F1 | MEDIUM | A non-canonical content payload (a float) raised Memory's raw `CanonError` out of the controller. The attempt stayed open, so a deterministic defect was re-run by W-6 and ended `RETRY_BUDGET_EXHAUSTED / STEP_INTERRUPTED` (wrong cause). Separately, `_defer` mapped no Memory refusal: a `not_before` in year 5 (written `5-01-01…`, schema-invalid) raised raw `AppendRefused`, and `datetime.min` at +01:00 raised raw `OverflowError`. | `NORMALIZE run1: ('EXC', 'CanonError', 'CANON_INVALID: float 1.5 …')`, last record `step_started`. `defer y5 ('EXC', 'AppendRefused', …)`. `defer min+1h ('EXC', 'OverflowError', …)` | `_content_append` maps `CanonError` to a defect. `_defer` maps refusals of its two appends as `_fail` does. `_aware` also requires a UTC instant with a four-digit year and no overflow. | `test_non_canonical_content_is_a_defect_of_the_step_not_a_crash[ACQUIRE,NORMALIZE,DETECT]`; `test_not_before_outside_the_schema_range_is_a_defect[4 cases]` |
| F2 | MEDIUM/LOW | A full disk during a blob write (`StorageError`) escaped. SPEC 10.2 requires `step_failed(STORAGE_ERROR, retryable = false)` when a record can still be written. | `run1: ('EXC', 'StorageError', '… No space left on device')`, attempt left open; `run2` re-ran NORMALIZE | `StorageError` from `put_blob` (step blobs and manifest) becomes `STORAGE_ERROR`. A `StorageError` from a journal append marks the controller unusable and is re-raised, leaving the attempt for W-6, as SPEC 10.2 says for when no record can be written. That last path is read from the code, not separately tested. | `test_disk_full_while_publishing_a_blob_is_storage_error` |
| F3 | LOW | An adapter could list the step-manifest digest among its outputs. The manifest was then not the last output, and every later staleness check raised raw `WorkflowCorrupt`: `check_journal` does not read manifests, and `run_investigation` did not map the error. | `evil run2 after config change: ('EXC', 'WorkflowCorrupt', '… S-9.3: VALIDATE has no valid step manifest')`, and the same on run 3 | An output equal to the manifest is a defect. Outputs are de-duplicated and the manifest is appended last. `run_investigation` reports `CORRUPT` for a `WorkflowCorrupt` found while running. | `test_adapter_output_equal_to_the_step_manifest_is_refused`; `test_workflow_corruption_found_while_running_is_reported_corrupt` |
| F4 | LOW | The guard allowed two claims for one candidate. SPEC 7.1 says one class per candidate. | `['RETRACTED_WORK_CITED', 'NOT_FOUND_IN_CHECKED_SOURCES'] -> ('OK', 'COMPLETED')` with both claims committed | `detect_problem` refuses more than one claim per `cand_ref`. The W-8 conflict/finding message is still checked first. | `test_two_claims_for_one_candidate_are_refused[2 cases]` |
| F5 | LOW (evidence) | `STEP7_RESOURCE_BOUNDS.md` said `verification_recorded` is never written. VERIFY writes exactly one (W-7). Its `checks` list was not measured, and one percentage was wrong (52 %, correct 49.9 %). | as stated | The row was corrected. A maximal `verification_recorded` is measured (567 bytes + 91 per check) and its constraint is recorded (one check per SPEC 9.7 kind, not per claim). The percentage was fixed. The reviewer recomputed every other figure and found them correct. | `resource_bounds.py` (validated maximal record) |
| F6 | LOW (evidence) | The differential walks never reached the budget boundaries (maximum f = 4, maximum 7 attempts). `_proposal` swallowed exceptions from `stale_payload`. | coverage probe: maximum f 0/0/3/4, maximum attempts 2/3/6/7 | A walk scenario directed at the budgets, `test_differential_at_the_budget_boundaries`, reaches f = 6, phi = 2 and 9 attempts, with every proposal compared. The blanket `except` was removed. Two harness gaps it exposed were fixed: a comparison before creation, and opening before creation. Remaining limitations, not fixed: the harness builds failure payloads itself rather than calling `_fail`/`_defer`, and only the `config` identity is changed in walks. Production's budget-code choice and per-component staleness are covered by the unit tests (`test_third_retryable_failure_is_retry_budget_exhausted`, `test_seventh_deferral_is_deferral_budget_exhausted`, `test_changed_identity_is_stale_and_nothing_is_rerun[10]`). | `test_controller_differential.py` |
| F7 | INFO | (1) `_own` and `_broken` are in-process fields. They are documented in the evidence (section 1) and neither is persisted or affects what a later process derives. (2) `read_blob` reaches the blob store in process. The adapter boundary is a correctness boundary, not a security boundary, and the store accepts only content-addressed writes. (3) `next_action` compares the raw clock while the guard uses `max(clock, last_at)`. After a backwards clock jump this can only lengthen a wait, never start early. (4) A wall-clock failure converted to `RETRY_BUDGET_EXHAUSTED` drops `wall_clock`, which the schema permits. | n/a | Accepted as stated. No change. | n/a |

Areas the reviewer checked and found no defect in:

- state derivation;
- transitions, including every forbidden transition the owner listed;
- `A_max`/`F_max` off-by-one and the 9-attempt cap;
- the `not_before` boundary (`at ≥ not_before` in both schedule and guard);
- W-6 recovery and no repeated success;
- staleness (`changed` exactly the differing components, terminal, nothing reused);
- needs-resolution routing and outcome `partial`;
- adapter result validation;
- the mutation runner (copy plus control);
- the reference model digest (matches the pin);
- the narrow scope of the `W6_STRICTER` and `SUCCESS_FLAG` classifications.

## Defects found by the implementer during Step 7 (before this review)

- `stale_payload` raised `WorkflowCorrupt` when committed steps had recorded different identity digests. The
  differential test found this. It now reports `STALE`.
- A full journal let Memory's raw `AppendRefused` escape when even the closing record was refused. The resource-bound
  derivation found this. The fix is `StorageExhausted`, with tests.
