# A-00-002: Stage 00 maintenance transaction (model, safeguards, evidence)

Owner authorization: the owner's directive "CITERIFT — CORRECTED OPEN-SOURCE AI, BLOCKER RECOVERY AND
STAGE 02 COMPLETION", delivered in the project thread on 2026-10-28 as message
`cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT` (section 3). This file is not that authorization;
it records what was built under it. Decision record: DECISIONS.md D-024.

## 1. The cycle this resolves

| Step | Fact (verified in the repository) |
|---|---|
| 1 | Stage 00 is `ACCEPTED_CLOSED`, verified and accepted at `0c21182e5871f772c3a76c75a1217c7641a63bbb` (acceptance recorded 2026-10-26T11:28:47Z). |
| 2 | `ed8e442` changed `tests/stage00/test_corrections.py`, a Stage 00 owned path (the owner-authorized V-03 fixture fix). |
| 3 | With no amendment covering it, `check` reports `VERIFICATION_STALE` for Stage 00: correct behavior. |
| 4 | An enhancement amendment needs a passing complete test report at its revision. |
| 5 | The complete suite includes `test_real_repository_passes_governance_check`, which fails while step 3 holds. So no such report can exist before the amendment. |
| 6 | Reopening Stage 00 is refused while Stage 02 holds the active slot (single-active rule), and `propose` refuses any transition while `check` has an error. |
| 7 | `test_application_layers_not_created_prematurely` rejected `src/citerift/retraction/`, which the owner authorized for Stage 02. |

## 2. State model

One amendment record, `kind: enhancement`, with a `maintenance` object
(`schemas/governance/stage_registry.schema.json`, `$defs.maintenance`, all fields required):

| Field | Meaning |
|---|---|
| `purpose` | The bounded purpose. |
| `baseline_revision` | The stage's accepted (verified) revision. |
| `candidate_revision` | The commit that holds the patch. |
| `scope` | Each changed owned file with the SHA-256 of its bytes at the candidate (`null` = deleted). Regular non-executable files only. |
| `patch_sha256` | Canonical digest of `scope`. |
| `phase` | `pending_validation`, `finalized` or `superseded`. |
| `supersedes`, `superseded_by` | The mutual link when a candidate changes. |
| `reports` | Validation reports: path, SHA-256, Python minor version. |
| `opened_after_seq` | History length at prepare. It must equal the history length in the registry at the candidate revision. |
| `finalized_at`, `finalized_after_seq` | Time and history length at finalization. |

The amendment's own `owner_ref`, `reason`, `evidence` and `recorded_at` are used as for any amendment.
`revision` and `test_report` are `null` while pending. After finalization they hold the validated revision
and the Python 3.12 report.

Transitions (no new lifecycle state; the stage stays `ACCEPTED_CLOSED`):

```
(none) --prepare--> pending_validation --finalize--> finalized
                    pending_validation --prepare(supersedes)--> superseded   (new record: pending_validation)
```

## 3. Ordering (no self-reference)

1. **P**: commit the protected patch (candidate).
2. `citerift-gov maintenance prepare 00 --candidate P --path ... --owner-ref <directive>`. Needs no report.
3. **V**: commit the registry and status with the pending record. The patch is the only owned difference from
   the baseline, so `check` at V has no error (`MAINTENANCE_PENDING` warning).
4. Run the complete suite on a clean checkout of V, once with Python 3.12 and once with 3.13. Each run writes
   `test-report.json`, which binds V, `dirty: false`, the selection and the totals.
5. Copy the reports to this directory (outside any stage's owned paths and its old evidence sets).
6. `citerift-gov maintenance finalize 00 A-00-002 --revision V --report ... --report ...`.
7. **F**: commit the finalization. This is a bookkeeping commit: its owned content must equal V's.

The tested code revision is V. P has the same owned bytes. F and later commits change only bookkeeping and
evidence outside the owned paths, and `check` enforces that the owned content stays equal.

## 4. Guarantees and where they are enforced

| Guarantee | Enforcement (`src/citerift/governance/orchestrator.py`) | Test (`tests/stage00/test_maintenance.py`) |
|---|---|---|
| Only the declared patch is exempt | `_patch_problems` at the candidate and at HEAD: an undeclared changed file, a declared unchanged file, changed bytes, a wrong mode or type, or a present "deleted" file is `MAINTENANCE_PATCH_MISMATCH` | `unrelated_drift`, `patch_changed_after_prepare`, `executable_bit`, `forged_patch_digest` |
| Exempt only while pending | `_drift_findings` gives `MAINTENANCE_PENDING` only for a pending record that matches HEAD | `after_finalization_ordinary_drift_is_detected_again` |
| Owner reference, baseline, scope, candidate | the schema; `OWNER_REF_REUSED`; `MAINTENANCE_BASELINE`, `MAINTENANCE_SCOPE`, `MAINTENANCE_PATCH_MISMATCH`; prepare only on an accepted stage | the `prepare_refuses_*` tests |
| No verification or acceptance while pending | `MAINTENANCE_BARRIER` on any entry to a verified or accepted status after `opened_after_seq` (and up to `finalized_after_seq`), and on any entry dated on the wrong side of the window. `propose` runs `check` on the result. | `no_stage_can_be_verified_*`, `hand_written_acceptance_*`, `dated_before_*`, `raised_window_opening` |
| Historical acceptance stays valid | the barrier covers only entries inside the window; Stage 01's acceptance comes before it | `no_stage_can_be_verified_*` (Stage 01 acceptance unchanged) |
| No back door through an ordinary enhancement | `add_amendment` refuses an enhancement while one is pending; `check` flags an enhancement tested at a revision whose registry holds a pending maintenance | `ordinary_enhancement_cannot_cover_a_pending_patch` |
| Finalize only on genuine complete reports | `check_test_report` (revision, clean tree, complete selection, no failures or skips counted as passes, suites, hash) for each report; Python 3.12 and 3.13; each report finished after the prepare and before the finalization | `report_that_does_not_prove_the_patch` (failed, partial, dirty, stale, skipped, deselected, wrong suite, wrong revision, future), `needs_every_python_version`, `report_from_before_the_prepare` |
| No code smuggled after validation | the owned content at V must equal the candidate (`MAINTENANCE_CODE_CHANGED`); the registry at V must hold the same record pending, compared field by field except for the finalization fields (`MAINTENANCE_NOT_VALIDATED`) | `patch_changed_after_validation`, `rewriting_the_prepare_time`, `revision_without_the_pending_record` |
| A finalization cannot shorten the window | `finalized_after_seq` is at least V's history length, and `finalized_at` is not before V's last entry | `cannot_end_the_window_before_the_validated_history` |
| A changed candidate is a new transaction | `supersedes` / `superseded_by` must be mutual; the old record stays | `patch_changed_after_prepare_*_superseded`, `superseded_record_needs_its_successor`, `superseding_in_the_same_second` |
| Contract rules unchanged | `_enhancement_contract_findings` runs on maintenance records | `contract_change_in_the_patch` |
| Single-active rule unchanged | not touched; a reopening of Stage 00 while Stage 02 is active is still refused | `two_active_engineering_stages_still_fail_while_pending` |
| Crash and restart | atomic writes; every rule is re-derived from the registry and git | `restart_between_phases`, `crash_while_writing`, `finalizing_twice_is_refused` |
| Writes need a clean result | `_mutate_maintenance` writes only if the whole resulting `check` has no error, including errors that existed before | the prepare and finalize refusals |

Historical amendments without `maintenance` follow the old path unchanged, and `maintenance: null` is
rejected by the schema (`test_an_ordinary_enhancement_keeps_its_rules`).

## 5. Test corrections inside the patch

- `tests/stage00/test_corrections.py` (V-03): the empty definition is now created inside the sandbox, for
  each missing field separately (`owned_paths`, `acceptance_gates`). `required_test_suites` is tested
  separately, because an empty list is refused earlier with `TEST_SUITES_UNDEFINED`. A complete definition
  is a control. The rejection and `DEFINITION_WEAK` assertions are kept.
- `tests/stage00/test_repository.py` (layout guard): `src/citerift/` may hold a layer only if it is in the
  architecture's component-to-stage mapping, its stage has an owner authorization (status after
  `NOT_STARTED`), and that stage owns the path. A test checks the mapping against `docs/architecture.md`.
  Negative fixtures: an unknown package, a layer of a `NOT_STARTED` stage (wiki), a layer the authorized
  stage does not own, and frontend content before Stage 08. The real-repository check stays.

## 6. Adversarial review (same model, separate pass; not human review)

Round 1 found 7 problems in the first implementation. All were reproduced and fixed, each with a
regression test:

1. backdating a transition with `--at`;
2. rewriting `recorded_at` after validation;
3. the contract checks skipped;
4. an ordinary enhancement covering the patch;
5. gitlinks and file modes outside the digest;
6. superseding in the same second (failed closed);
7. a directory path that crashed the tool.

Round 2 re-reviewed the fixes and found 3 more, all fixed:

1. `finalized_after_seq` set back by hand;
2. `opened_after_seq` raised by hand while pending;
3. a same-second transition after finalization refused (failed closed).

Reports: `review-round-1.md` and `review-round-2.md` in this directory.

## 7. Limitation that remains (not solved here)

The agent and the owner share repository authority: the session's GitHub token acts as the owner's
account, and anyone who can write the registry can write a consistent forgery. That includes a fabricated
owner reference, or reports and registry edits made consistent with each other. This mechanism does not
prove an owner reference authentic and adds no cryptographic trust. What it does is keep every existing
control, make the maintenance window explicit and position-anchored in the registry, and make any
inconsistent edit an error that CI reports. Owner-signed acceptance remains a documented future
enhancement (GOVERNANCE.md, D-006; RISKS.md R-002, R-016).

## 8. Live execution record

Filled in after the live transaction: P, V, F, the report paths and hashes, and the CI runs.
