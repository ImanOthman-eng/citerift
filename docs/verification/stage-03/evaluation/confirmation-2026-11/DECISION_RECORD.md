# Stage 03 scientific decision record: confirmation campaign (2026-11-03)

Prepared by the executor under the owner's instruction of 2026-11-02 (DECISIONS.md D-034). This file records
evidence and a recommendation. **It records no owner decision.** Only the owner can change an acceptance
requirement, accept the stage, or authorize further work.

## 1. What the confirmation campaign shows

Full results: `campaign/REPORT.md`. One prospective campaign was run at the frozen candidate `3e51792`, with labels
locked before the single prediction run, and all 113 disputed items adjudicated (104 confirmed, 9 corrected).

| Requirement (owner instruction section 12) | Status | Evidence |
|---|---|---|
| (1) The frozen candidate is the one evaluated | met | `campaign/audit/EVIDENCE_AUDIT.json`, check 2 |
| (2) Denominators in both languages | met (ar 103 / 190 / 160 / 189, en 50 / 274 / 157 / 274) | `campaign/scores/adjudicated.json` |
| (3) Every applicable G1-G11 passes | **not met: en G5c unit precision 0.869 < 0.95**; all others pass | `campaign/REPORT.md` section 4 |
| (4) Annotation independence and provenance | met, with the recorded deviations (AI labels, not human gold) | `campaign/REPORT.md` sections 3 and 6 |
| (5) Warning claims within positive evidence | met for enwiki (6 / 6); **no Arabic positives exist** in the frame | `campaign/REPORT.md` section 8 |
| (6) Every evaluated bundle verifies and replays | met (54 / 54) | `campaign/prediction/runs.json` |
| (7) No known critical or high unresolved engineering defect | met; see section 2 for why G5c is classed as a specification divergence | `review/REVIEW_FINDINGS.md` |
| (8) Full regression and static verification | see TEST_RESULTS.md section 7 | |
| (9) Network policy and Retry-After controls | met (263 attempts, 12.6 MB of 500 / 300 MiB) | `campaign/audit/EVIDENCE_AUDIT.json`, check 8 |
| (10) Export and documentation | see HANDOFF.md | |
| (11) Governance permits the transition | it would, but (3) is not met, so no transition is recorded | `governance/stage_registry.json` |
| (12) Final PR-head CI | see the pull request #5 description | |

Because (3) is not met, the executor records **no** transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE`. Stage 03
stays `IMPLEMENTED_NOT_VERIFIED`.

## 2. Cause of the unmet requirement

SPECIFICATION.md 11.3 says that a definition with no template unit is `unstructured_text`. The annotation guide
(3.2, frozen and 1.1) gives `unstructured` only to a definition that "cites something in plain text with no citation
template". The two texts disagree on definitions whose body is a Harvard short-citation link (`{{harvnb}}`,
`{{harvp}}`: 13 cases), an explanatory note that cites nothing (4), or a citation-like template the profile does not
list (2). The engine does what its specification says; the gate measures agreement with the guide. Eleven of the 19
false positives are in one Harvard-referenced article. Both frozen texts predate the campaign, and neither may be
changed after it.

Classed as a **specification divergence, not an engineering defect**: none of the 19 cases involves a crash, a
regression, an identifier, a binding, a render link or a marker, and the engine output is reproducible and verified. The executor's judgement
is that this is not a critical or high defect; the owner may judge otherwise.

## 3. Possible outcomes

- **A. Narrow the unit claim and proceed to verification.** The owner records, in their own words, that gate G5c is
  not met and is excluded from the verified claim, and that `unstructured_text` means "a definition with no
  recognised citation template unit", not "a plain-text citation". The executor would then record
  `VERIFIED_AWAITING_OWNER_ACCEPTANCE` at the then-current head, with green CI, citing that owner decision. The owner
  accepts and merges personally.
- **B. Authorize a post-exposure correction of SPECIFICATION 11.3** (for example, a separate unit kind for
  short-citation links and for notes that cite nothing), with fail-first tests. It would be measured only on the
  exposed campaign data, so it could not be called a fresh confirmation; it would still need outcome A, or a new
  prospective campaign, for verification.
- **C. Keep Stage 03 unverified.** Stage 04 stays blocked (GOVERNANCE.md invariant 3).

A new campaign is not started automatically (owner instruction section 7). The deadline is 2026-11-21 23:59 EST.

## 4. Supported and unsupported claims (if A is chosen)

**Supported by this campaign**, for random DOI-citing arwiki and enwiki articles at selection time, window level,
with the intervals of `campaign/scores/intervals.json`:

- identifier detection, keys and roles (G1-G3) in both languages;
- uses, bindings, definitions and render links (G4-G6) in both languages, with no false attachment;
- no fabricated negative marker (G7), and, on enwiki, detection of 6 / 6 labelled retraction and concern warnings;
- every extraction verifies and replays offline.

**Not supported:**

- the classification of a definition as `unstructured_text` as meaning a plain-text citation (en G5c);
- any statement about Arabic warning detection in real articles (no Arabic positive exists in the frame);
- a key-error or promotion rate below 1 % (the one-sided 95 % upper bounds are 3.0 % for ar and 6.1 % for en);
- human-reviewed gold labels (all labels are AI evaluations).

## 5. Executor recommendation

**Outcome A.** Every other gate passes in both languages, the three failures of the earlier campaign do not recur,
and the one failure is fully explained by a divergence between two frozen texts in a classification that is not an
identifier, binding or marker. B is useful engineering, but it cannot produce fresh evidence before the deadline
without a new campaign. Stage 04 should then treat `unstructured_text` units as "no recognised citation template",
never as evidence that a definition cites a work.

This is a recommendation. The decision is the owner's.
