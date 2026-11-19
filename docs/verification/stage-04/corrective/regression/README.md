# Corrective-cycle regression (owner decision D-071, section 8)

DEVELOPMENT AND REGRESSION EVIDENCE ONLY. Every set here is design-exposed. None of it is an evaluation, and none of it
is ever counted as unseen data.

| File | Set | Code revision (shards) | Result |
|---|---|---|---|
| `DEV_REGRESSION.json` | the 232 development revisions of Step 13 | `dfee881` | 4,614 candidates; 1 changed claim; dt-1 cross-check 0 mismatches |
| `CAMPAIGN_REGRESSION.json` | the 80 articles of the failed campaign | `90bc60e` (same `src` and `schemas` as `dfee881`) | 4,920 candidates; 4 changed claims; 4,649 historical claims re-decided, 0 mismatches |
| `NAMED_CASES.json` | the named vertical-slice cases (Wakefield/MMR, Obokata ar/en, GFAJ-1, EoC, BCAS3, reserves) | see its `provenance` | see the file |

Every changed claim is a positive that becomes `UNRESOLVED_IDENTITY` with `IDENTIFIER_ROLE_COLLISION`. No new
positive, no new `NOTICE_CITED` and no new `NOT_FOUND_IN_CHECKED_SOURCES` appears anywhere. Every recorded dt-2 claim
equals the dt-2 decision recomputed from the committed inputs, and no network request was attempted.

How the shards were made: `regress.py run` records `provenance` at its start (the index, both tables, the code
commit, and whether `src` or `schemas` had uncommitted changes); `regress.py merge` refuses shards that disagree or ran
on uncommitted engine code. After the shards ran, one defect in `merge` was fixed: `positive_units` was computed after
the per-candidate rows were dropped and read 0. The merge now computes the totals first. `tool_sha256` is the hash of
`regress.py` at merge time; its `run` code is unchanged from the code that made the shards.

One campaign claim (`ar-3351802 un-00059`) abstains because a second record of the same work (an expression of
concern) gives both cited keys both roles while the deciding retraction record itself states distinct notice
identifiers (reviewer finding C-01). Owner decision D-073 keeps it `UNRESOLVED_IDENTITY`: no same-work-sibling
exemption. "Probable true positive" describes it; it is not a reason to resolve it.

The changed claims here are the recall cost of the strict rule approved by owner decision D-072 (snapshot: 1,472 of
31,506 dt-1 positive pairs abstain; 800 under the declined lenient alternative). Any later evaluation states this cost
as a limitation of the engine; it is not reported as a performance result. Owner decision D-075 leaves an original DOI
cited with the same record's notice PMID positive when the DOI is clean (`../census/B03_CENSUS.json`: of 31,279 such
pairs, 628 positive under dt-2 and 794 under dt-1; the 166 that change are D-14 to D-10 because the DOI itself is
role-collided; 30,482 are `IDENTITY_CONFLICT` under both tables because the record also states the work's own, different
PMID, an incompatibility witness of SPEC 6.5, not because the cited PMID is a notice identifier).

These outputs were never joined with the campaign's labels, adjudications or scorer, and must not be (reviewer finding
F-08). The rule was designed from the one authorized failure only (D-071 section 2).
