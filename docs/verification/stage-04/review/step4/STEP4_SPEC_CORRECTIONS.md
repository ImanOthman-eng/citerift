# Stage 04 Step 4: corrections to the Step 3 documents

The owner allowed "minimal updates to Step 3 documents only if executable simulation exposes a real specification
defect, with the correction explicitly documented" (message `cmsg_018VCB51nDHP6HXmLU4ea5yPFigUhaer7vUNd5ng3Rh6qw`).
Each correction below names the defect, the executable evidence that exposed it and the exact change. Base revision of
the documents: `fb39ede`. Nothing else in `SPECIFICATION.md`, `MATHEMATICAL_MODEL.md` or `RISK_ANALYSIS.md` changed.
`review/step3/check_step3_docs.py` still passes on the corrected documents.

| Id | Defect at `fb39ede` | Evidence | Change |
|---|---|---|---|
| SC-1 | Guards D-7, D-9, D-11, D-12, D-14, D-15 and D-16 read only a state or a status. A projection outside the Stage 02 contract could satisfy a lenient guard, and D-14's `pos(v)` was undefined for a `verified_fact` whose value is not one of the four positive values. | Mutant MD-10 (positive guard reads the status only) yields positive findings from such projections and is caught by FAIL_CLOSED_INVALID, POSITIVE_FROM_DECIDING and UNKNOWN_PRESERVATION (`simulation/mutants.json`). | SPEC 7.3 and MM 5.2: each guard names the exact status and value it accepts; D-14 requires `v ∈ dom(pos)`; a sentence after SPEC 7.3 states that malformed projections fall to D-5 or D-17. |
| SC-2 | D-5 caught only `invalid_query` and the P2 disagreement. Lookup combinations that Stage 02 cannot produce passed D-5 and could be decided as findings; for example Q2 `matched` with a verified retraction while Q1(d) and Q1(p) are both `no_record` gave `RETRACTED_WORK_CITED`. | Mutant MD-11 (D-5 exactly as in Step 3) makes invalid inputs yield findings: FAIL_CLOSED_INVALID violations in `simulation/mutants.json`. | SPEC 7.3 D-5, S-6.12; MM 5.2 D-5 with the predicates `Contract` and `pairok`; new MM facts F-8 and F-9 (checked against the real `gather` on 192 worlds). |
| SC-3 | D-15 (`NOTICE_CITED`, an abstention) had no reason code, against AB-2 ("each abstention carries at least one reason code"). | Property AB2_REASONS on the reference model. | SPEC 7.3 D-15: reason `CITED_IDENTIFIER_IS_NOTICE`. |
| SC-4 | D-6 (`IDENTITY_CONFLICT`, status `conflicting`) had a reason only when a lookup was unavailable or the unit tainted. The v1 assertion form requires a `reason` for every `conflicting` status (`policy._assertion`, v1 rule). | Property AB2_REASONS (kinds abstain, needs-resolution and failure). | SPEC 7.3 D-6: reason `IDENTITY_WITNESSED` always, plus `LOOKUP_PARTIAL` and taint reasons when they apply. |
| SC-5 | SPEC 9.2, W-4 and MM TR-4 gave `A_max + F_max + 1` attempts per step. The exact maximum is lower. | Exhaustive controller model: ACQUIRE of a capture request reaches 9 = `A_max + F_max` attempts, every other step and ACQUIRE of a retained bundle 3 = `A_max`, never more (`simulation/controller_model_summary.json`). | SPEC 9.2, W-4, MM TR-4: the exact maxima. |
| SC-6 | S-4.4 did not say how pre-ACQUIRE records are attributed, nor that a capture made by a later ACQUIRE attempt (after one that committed nothing) is not a root replacement. Owner decision F-15 (D-041) states both. | Controller model: properties NO_CONTENT_BEFORE_ROOT and ROOT_IMMUTABLE; mutant MC-7. | SPEC S-4.4: `root_id = null` before the bind, attribution through `request_key`, `investigation_key` and the genesis value; no content record of any step before the bind. |
| SC-7 | SPEC 7.4 listed `REINSTATED_WORK_CITED` among reachable results. Stage 02 states the value `reinstated` only with supersession links, which `gather` takes as an argument that Stage 04 never passes. | Real Stage 02 probes X-reinstatement-alone and X-retraction-then-reinstatement give `matched` with `uncertain` (`simulation/stage02_conformance.json`); `policy._reduce`. | SPEC 7.4 note; MM F-8. The rule stays for a later versioned source. |
| SC-8 | MM P1 said the Step 4 model would check it; the result is now known. | Decision-space summary. | MM 5.6: one sentence with the Step 4 result. |

Not changed, on purpose:

- The tier order (owner decision F-01) and every class, status and disposition: the reference model reproduces them.
- The investigation-level budget: F-11 is reported in `SIMULATION_REPORT.md` with the result BLOCKED ON F-11 for the
  live-capture path; the owner's condition says to stop at the finding and recommend, not to add a timer in Step 4.
- `RISK_ANALYSIS.md`: all risks stay open; the Step 4 report maps its evidence to them.
