# Stage 03 scientific decision record: D-035 confirmation campaign (2026-11-03)

Prepared by the executor under the owner's instruction of 2026-11-03 (DECISIONS.md D-035). This file records evidence
and the decision the owner would have to take. **It records no owner decision.** Only the owner can accept the
stage, authorize further work or change a requirement.

## 1. Requirements of owner instruction section 10

Full results: `campaign/REPORT.md`. One prospective bilingual campaign was run at the frozen candidate `fff0e5b`,
with every label locked before the single prediction run and all 46 disputed items adjudicated (45 confirmed, 1
corrected).

| Requirement | Status | Evidence |
|---|---|---|
| English G5c ≥ 0.95 and G5d ≥ 0.95 | **met**: 0.994 [0.978, 1.000] and 0.994 [0.980, 1.000] | `campaign/REPORT.md` sections 4 and 7 |
| Arabic validity prospectively re-established | **met for G5c (1.000) and G5d (0.992)**; not for G6b (next row) | same |
| All other applicable G1-G11 thresholds | **not met: Arabic G6b**, 2 false render attachments against the frozen limit max(1, 1 % of 184) = 1. Every other gate passes in both languages | `campaign/scores/adjudicated.json` |
| Denominators | met (ar 61 / 207 / 153 / 197, en 60 / 210 / 195 / 207) | same |
| No false cited-work promotions (G3a) | met (0 / 59, 0 / 60) | same |
| No fabricated negative warning states (G7) | met, vacuously: no labelled warning in the sample | `campaign/REPORT.md` section 7 |
| **No wrong rendered attachments beyond the frozen limit** | **not met** (Arabic G6b) | `campaign/REPORT.md` section 5 |
| Full verify and replay | met (48 / 48 and 48 / 48) | `campaign/prediction/runs.json` |
| Valid independent annotation provenance | met, with the recorded deviations (AI labels, not human gold) | `campaign/REPORT.md` sections 3 and 6 |
| Complete engineering checks | see TEST_RESULTS.md section 8 | |
| Green final-head CI | see the pull request #5 description | |
| No unresolved critical or high material defect | **not met**: the defect behind G6b (RISKS.md R-038, high) | `campaign/REPORT.md` section 5 |
| All evidence preserved | met; five files withheld from git are exported with checksums | `campaign/WITHHELD_FILES.json`, `campaign/audit/EVIDENCE_AUDIT.json` |

Because two requirements are not met, the executor records **no** transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE`.
Stage 03 stays `IMPLEMENTED_NOT_VERIFIED`.

## 2. The exact blocker

`src/citerift/wiki/reconcile.py`, `_align_unordered`, line 309: inside one template's output, the uses of one
reference name are paired with its rendered markers in source order, although the template decides the rendered
order (its own docstring says so). In `ar-76814232` an infobox renders the U−B row before the B−V row, so the two
markers of `Mallama2014` are attached to the wrong source positions. The locked label is correct and was confirmed by
the adjudicator. The code predates D-035 and both earlier candidates. Details: `campaign/REPORT.md` section 5.

The corrected G5c semantics are not involved: no unit, definition, identifier or marker gate fails.

## 3. What the amendment allows now

Nothing more inside this campaign: "After the run. There is no repair, retuning, reselection or rerun. A material
defect is preserved and reported. No further campaign starts" (amendment section 8). G6b may not be exempted, G5c may
not be excluded, and no label may be changed to match the engine.

## 4. The minimum scientifically legitimate decision

The owner decides. The executor's assessment of the smallest legitimate path to verification:

1. **Authorize a narrow engine correction** of `_align_unordered`: when one name has more than one use inside one
   template's output, pair those uses only when the render proves the order, and otherwise abstain (state
   `abstained`, issue `RECONCILIATION_ABSTAINED`) instead of guessing. In this case the render carries the evidence (not
   yet implemented or tested): only the definition's marker has a Parsoid `data-mw` `body`, so a definition plus one reuse can be paired by that
   evidence; with two or more reuses, the reuses stay unordered and abstain. Abstaining can lower G6c coverage slightly; it
   cannot add a wrong attachment. Fail-first test on this case, a differential check on all retained bundles, and the
   full verification matrix. The scope: in the 204 retained extraction documents, 15 such groups in 12 articles are paired
   this way today; those are the pairings such a correction could change.
2. **Authorize one more bounded prospective confirmation** of that candidate, with a new exposure set, under the same
   gates, thresholds, minimums and ceilings. The change is language-general, so the same reasoning as D-035 section 3
   applies: both languages. This campaign's articles are then exposed and may serve only as regression evidence.
3. Only if that confirmation meets every requirement of section 1 would the executor record
   `VERIFIED_AWAITING_OWNER_ACCEPTANCE`.

The alternative is to **keep Stage 03 unverified**, which keeps Stage 04 blocked (GOVERNANCE.md invariant 3).

Measured cost of this campaign, for planning: 280 HTTP attempts, 9.2 MB, about 1.5 hours from the draw (15:04 UTC) to the locked scores (16:39 UTC). The
deadline is 2026-11-21 23:59 EST.

## 5. What this campaign does establish

These hold whatever the owner decides, and are not claimed as a verification:

- The D-035 semantic correction works prospectively: English G5c 0.994 and G5d 0.994 on 24 unexposed articles,
  Arabic 1.000 and 0.992 on 24.
- Every other frozen gate passes in both languages, on adjudicated labels that equal the locked labels in every gate
  value.
- Every extraction verifies and replays; the evidence audit passes 28 / 28.
