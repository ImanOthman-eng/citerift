# Stage 03 scientific decision record (2026-11-02)

Prepared by the executor under the owner's instruction of 2026-11-02 (DECISIONS.md D-033). This file records
evidence and a recommendation. **It records no owner decision.** Only the owner can change an acceptance
requirement, accept the stage or authorize a new campaign.

## 1. What the frozen evaluation shows

There was one final campaign:

- 16 articles per language, the protocol's ceiling;
- labels locked before predictions;
- one prediction run at the frozen candidate `48cfeab`;
- adjudication of all 37 disputed items (`adjudication/README.md`).

Gate results under the adjudicated labels (`run/scores_adjudicated.json`):

| Requirement | ar | en |
|---|---|---|
| G1-G4, G5b-d, G6, G7 | all pass | all pass |
| G5a definition precision ≥ 0.95 | **0.914, fail** | 0.984 pass |
| G2 normalized-key error rate ≤ 0.01 | 0.000 pass | **0.0192, fail** |
| Minimum denominators: identifiers ≥ 50 | **33, not met** | 54, met |
| Minimum denominators: uses, definitions, linkable | met | met |
| G8 verify, G10 replay (32 / 32 at `48cfeab`) | pass | pass |
| G9 acquisition (32 / 32 complete) | pass | pass |
| G11 synthetic challenge cases | pass in the complete suite (TEST_RESULTS.md) | pass |

**Gate 03-G** requires G1-G6 and G8-G11 per language with the minimum denominators. It is **not met**, so the
registry cannot record a technical verification for Stage 03 (GOVERNANCE.md invariant 1).

## 2. Cause of each unmet requirement

1. **Arabic G5a.** All 10 false positives are repeated identical `{{sfn}}` calls in one article, ar-75574746. The
   engine lists every call as a definition of one container (SPECIFICATION 11.2). The final adjudicator ruled
   (guide 3.2) that the later calls are uses only.
   - The run-1 adjudicator ruled the opposite on the same wording (guide 3.1).
   - Uses, bindings and render links of these calls are all correct.
   - Under the run-1 reading, the same 116 predictions would all be true positives. This is arithmetic, not a
     gate result, because no label was changed.
   - The failure is a definitional disagreement in the frozen guide, not a wrong citation, binding or identifier.
2. **Arabic identifier denominator.** 16 randomly drawn Arabic DOI-citing articles hold 33 in-window target
   identifier occurrences. The engine found 32 of them, with 0 key errors and 0 promotions. Adjudication did not
   change the count. Nothing can legitimately raise it inside the authorized campaign.
3. **English G2.** One Wiley URL kept its `/abstract` page route in the key (RF-60). It was repaired after exposure
   and confirmed by fail-first tests and an independent integration review. The frozen result is not changed. The
   post-exposure re-extraction gives 0 / 52 key errors on exposed data, which is not a gate result.

## 3. Possible outcomes (the owner's directive, section 4 D)

- **A. All applicable gates pass after legitimate adjudication.** Not available: three requirements are unmet.
- **B. Technically verified, scientific requirement unmet, narrower claim.** Supportable, but only with an owner
  decision. The decision would amend gate 03-G to accept the narrowed claim below, recorded before any verification
  transition. The executor cannot make it.
- **C. New independent evaluation.** It needs an owner-approved, prospectively written amendment *before* any
  acquisition. That amendment would set:
  - unexposed article groups only;
  - a guide clarification of the short-footnote rule, decided before any labelling;
  - a sample design able to reach 50 Arabic identifiers, which the 16-article ceiling did not;
  - the fixed RF-60 candidate.
  Cost and risk: about one working day of capture, annotation and adjudication under the Wikimedia rate limits, with
  no guarantee that Arabic articles reach 50 identifiers within a bounded draw.
- **D. Material defects or insufficient evidence prevent acceptance.** No unresolved material defect is known. The
  evidence is insufficient only for the Arabic identifier claim.

## 4. Supported and unsupported claims (if B is chosen)

**Supported, on this sample:**
- English extraction meets every frozen gate except G2, which failed by one key. That failure has a post-exposure
  repair that has not been freshly evaluated.
- Arabic uses, bindings, render links (119 / 119, zero false attachments), units and definition recall meet their
  gates.
- No promotions and no fabricated negatives in either language.
- Every result verifies and replays.

**Not supported:**
- Arabic identifier extraction at the frozen 50-item strength. The evidence is 32 of 33 found, with 0 key errors in
  32; the 95 % upper bound on the key error rate is 8.9 %, not 5.8 %.
- Any claim about warning detection from the final campaign, which contains no warnings.
- Population-level accuracy.
- Any freshly evaluated accuracy for RF-60.

## 5. Executor recommendation

The executor recommends **B, with an explicit owner-recorded narrowing of 03-G** to the claims in section 4, and with
the guide's short-footnote ambiguity recorded as a known definitional limitation. The reasons:

1. No wrong citation, binding, attachment, promotion or warning was found in either language.
2. The Arabic shortfall is sample size, which more of the same procedure inside the ceiling cannot fix.
3. Stage 04 depends on Stage 03 being accepted (GOVERNANCE.md invariant 3). A new campaign (C) would consume about a
   day of the remaining 19 and could still miss 50 Arabic identifiers.

Stage 04 should treat Arabic identifier results as lower-confidence and must keep treating
`IDENTIFIER_BOUNDARY_AMBIGUOUS` keys as unconfirmed.

If the owner prefers C, the executor will draft the prospective amendment for approval before any network request.
