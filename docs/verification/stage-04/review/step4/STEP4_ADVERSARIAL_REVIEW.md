# Stage 04 Step 4: adversarial review of the simulation

Scope: the Step 4 deliverables (`simulations/stage04/`, `tests/stage04/test_simulation_step4.py`,
`docs/verification/stage-04/simulation/`, `SIMULATION_REPORT.md`) and the Step 3 corrections they caused. The review
was done after the first complete run and before the final one. It looks for the ten failure modes the owner listed
(message `cmsg_018VCB51nDHP6HXmLU4ea5yPFigUhaer7vUNd5ng3Rh6qw`, item 13). Each item states what was checked, how,
what was found and what was done. "Confirmed" findings were corrected before the final run; "open" ones are reported
to the owner.

## R4S-01 Oracle circularity

- Question: can the oracle agree with production because both are derived from the same code?
- Checked: the reference modules import nothing from `citerift` (AST test
  `test_reference_models_are_independent_of_production_code`); no Stage 04 production code exists; the oracle is
  written once by `run_step4.py`, pinned by digest in the test (`ORACLE_MANIFEST_SHA256`) and tied to the SHA-256 of
  the two semantic modules (`model_digest`).
- Found (confirmed, corrected): the first version of the property checker read the model's own `coherence` and
  `guards`, so a defect in those functions would also have blinded the check. The checker now restates kappa
  (`decision_space.kappa_of`) and the monotone guards from SPEC 6.5 and 7.3; mutant MD-8 (coherence ignores the pair
  witness) is caught by IDENTITY_DOMINANCE and NO_FINDING_UNDER_CONFLICT only because of this change.
- Residual (open, accepted): the abstraction (`stage02_abstraction.valid`) reuses the model's table of contract
  projection forms (`WELL_FORMED`). An error there would be shared. Mitigation: the real Stage 02 engine is run on
  192 worlds and 44 cases and every real result falls inside the table (`stage02_conformance.json`); a form the real
  engine produced outside the table would be reported as `outside_contract`.

## R4S-02 Missing input dimensions

- Checked: every input `δ` reads in MM 5.1 (`E`, `σ`, `τ` with its three reasons, `Λ(c)` per slot, `κ` through four
  witness bits, `L`) and every reason source (CO_REPORTED_MULTIPLE).
- Found (open, documented): four reason codes depend on inputs the abstraction does not carry and are placeholders:
  `DEFINITION_UNUSED` and `USE_NOT_ESTABLISHED` stand for the SPEC 6.2 reason, `STAGE02_BASIS_REASONS` for the
  Stage 02 basis reasons, `LOOKUP_UNAVAILABLE` for the failed query's code. The oracle compares them as placeholders.
  The investigation-level rows O-1 to O-3 are not inputs of `δ`; they are covered by the controller model (FAILED,
  STALE). Observation-role identifiers and marker targets are not candidates by construction (S-6.7) and are not in
  the domain.

## R4S-03 Unreachable combinations treated as valid

- Found (open, by design): validity over-approximates projections: any contract form of a state is admitted, and
  cross-lookup constraints between projections are not modelled. Properties are therefore checked on a superset of
  what Stage 02 produces. Of the 20 contract lookup values, the real engine produced 12 (one of them, `invalid_query`,
  only for an invalid query key, which Stage 04 never sends). Not produced: `unavailable` (made by the Stage 04
  adapter, never by `gather`), `vf:reinstated` with and without a PMID role collision, and the collision variants of
  `conf`, `unc`, `unc:bridge_only`, `vf:correction` and `vf:expression_of_concern`; they are admitted from the code
  (F-2 to F-4, F-8).
- Found (confirmed, documented as SC-7): `vf:reinstated` is admitted by the contract but unreachable through Stage
  04's calls (Stage 02 states it only with supersession links that Stage 04 never passes). It stays valid in the
  domain, so the table is shown safe if a later source provides it.

## R4S-04 Invalid combinations silently ignored

- Checked: every invalid case is enumerated, decided and counted by rule and kind; FAIL_CLOSED_INVALID requires that
  none yields a finding.
- Found (confirmed, corrected as SC-2): with D-5 as written in Step 3, invalid pair combinations were decided as
  findings (mutant MD-11 reproduces it). D-5 now covers every contract inconsistency visible to Stage 04.
- Found (open, documented): an invalid input in a unit that is not cited, or with no key, is decided by tier 2
  (out of scope) before D-5 can see it. This produces no finding and follows the accepted tier order, but the
  inconsistency is not reported as `ADAPTER_INCONSISTENT`. The counts are in the report (invalid cases by rule).

## R4S-05 State-space truncation

- Decision space: a full product; no sampling. Counted cases equal the product of the dimension sizes (checked by the
  test against `chunk_size`).
- Controller: reduction R-1 forgets the counters of succeeded steps. Checked by `quotient_check`: for budgets
  (A, F) = (2, 1) and (2, 2), in all four scenarios, the full space projected by R-1 equals the quotient space, the
  per-step attempt maxima are equal and every property gives the same verdict. The full space for (3, 6) exceeds
  400,000 states and was not built; R-1's soundness for (3, 6) rests on the argument in `normalize` plus these checks.
  The exploration limit of 400,000 states was not reached by the declared machine (STATE_SPACE_FINITE).

## R4S-06 Hidden cycles

- Checked: Tarjan SCCs over every reachable transition, including environment moves. NO_RECORD_IN_ANY_CYCLE: no
  strongly connected component contains a transition that appends a record. Cycles exist (waiting in BLOCKED:
  invocation, exit; a second invocation answered BUSY) and append nothing.
- Checked: every non-terminal state reaches a terminal state (TERMINAL_REACHABLE_FROM_EVERY_STATE).

## R4S-07 Off-by-one budgets

- Found (confirmed, corrected as SC-5): the Step 3 bound `A_max + F_max + 1` is not reached; the exact maxima are 9
  for ACQUIRE of a capture and 3 elsewhere. Mutants MC-5 (retry budget plus one) and MC-6 (a seventh deferral) are
  detected.

## R4S-08 Precedence errors

- Checked: mutants MD-1 (positive before identity conflict) and MD-5 (the plan draft's order, unavailability before
  identity conflict, which owner decision F-01 forbids) are detected by IDENTITY_DOMINANCE. STRENGTHEN_TAINT and
  STRENGTHEN_WITNESS check that stronger evidence never moves a case to a later tier between valid cases.
- Found (not a defect, recorded): adding a witness bit to an invalid case can remove a D-5 violation and move it from
  tier 3 to tier 4 (identity conflict). Monotonicity is therefore stated between valid cases only.

## R4S-09 Boundedness proof

- Found (confirmed, reported as the F-11 result): the live-capture path has no operational bound from the configured
  limits. Two experiments on the real Stage 03 transport (`f11_bounds.json`): a response head dripped one byte every
  0.5 s and an endless sequence of `100 Continue` interim responses each held a 1 s timeout for 6 s. Python's socket
  timeout bounds each receive, not the response head, and `http.client` skips any number of `100 Continue`
  responses. DNS resolution (`getaddrinfo`) has no timeout in Python. The bound for that path cannot be derived, so
  the result is BLOCKED ON F-11 with a recommended minimum timer, as the owner's condition requires.
- Checked: the retained-bundle path is bounded under assumptions E-1 to E-5, which are written out (no hidden
  "deterministic" step; each local step has its size bound from Stage 03 caps).

## R4S-10 False claims of exhaustive coverage

- Wording checked in `SIMULATION_REPORT.md`: "exhaustive" is used only for the declared finite abstraction and the
  declared controller model, never for real inputs; reduction R-1, the over-approximation of projections and the
  placeholder reasons are stated next to the counts.
- Rule coverage: D-5 and D-17 are reached only by invalid inputs (as P1 states); D-9 is unreachable for DOI-only
  candidates and the reinstated row of D-14 is unreachable through Stage 04's calls; both facts are in the report.

## Result

Confirmed defects corrected before the final run: R4S-01 (checker independence), R4S-04 (D-5, SC-2), R4S-07 (attempt
bound, SC-5), and SC-1, SC-3, SC-4, SC-6 found by the properties. Open and reported: R4S-01 residual, R4S-02
placeholders, R4S-03 over-approximation, R4S-04 tier-2 absorption, R4S-05 (3, 6) quotient argument, and R4S-09
(F-11: BLOCKED ON F-11 for live capture).
