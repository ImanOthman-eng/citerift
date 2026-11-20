# Stage 04 final corrective cycle: regression of dt-3 on the design-exposed articles (owner decision D-083, item 11)

**Development and regression evidence only.** The 232 development revisions of Step 13, the 80 articles of
evaluation 1 and the 100 articles of evaluation 2 are design-exposed (exposure manifest v3). They are never counted as
unseen data, never rescored, and no label, adjudication, packet or score of either campaign was read (reviewer finding
F-08). Nothing below is a recall or precision estimate. Both evaluations stay NOT PASSED and unchanged.

## 1. Method

Tool: `regression/regress.py`. Each revision runs one offline investigation through the production plan with engine
0.4.0 (table dt-3). Every socket is refused, and Investigation Memory lives in a temporary directory outside the
repository. For every work candidate, the recorded dt-3 claim is compared with the decision of the accepted dt-2 table
(`dt1.py` of the freeze-2 commit `28ba646`, read from git by blob id and checked) on the same committed inputs.

Outputs: `regression/DEV_REGRESSION.json`, `CAMPAIGN_REGRESSION.json` and `P2_REGRESSION.json`. Each was merged from
three shards that record one provenance: code commit `f83d20b`, an empty uncommitted list, and the Stage 02 index
identity. `tests/stage04/test_final_provenance.py` checks the provenance against HEAD.

Checks that hold on all three sets:

- The dt-2 decisions re-decided here equal the recorded dt-2 class counts of every revision. For the development and
  evaluation-1 sets, the reference is the corrective-cycle regression (`../corrective/regression/`). For P2, it is
  `../evaluation-p2-campaign/run/RUN.json` `claims_by_class`, claim counts only. There are 0 mismatches over 412
  revisions.
- Every recorded claim equals the dt-3 decision of the same inputs (`recorded_equals_dt3_everywhere`).
- No network attempt was made (0).
- Lifecycles are unchanged from dt-2:
  - development: 230 COMPLETED, 1 NEEDS_RESOLUTION (`ar-76190003`), 1 FAILED (`en-1380218630`, as before);
  - evaluation 1: 78 COMPLETED, 2 NEEDS_RESOLUTION;
  - evaluation 2: 99 COMPLETED, 1 NEEDS_RESOLUTION.
- VERIFY passed on 231, 80 and 100 revisions respectively, as under dt-2.

## 2. Effect, set by set

| | Development (232) | Evaluation 1 (80) | Evaluation 2 (100) |
|---|---|---|---|
| Work candidates | 4,614 | 4,920 | 5,190 |
| Candidates with a cited description | 3,859 | 4,116 | 4,551 |
| dt-2 D-14 candidate–event pairs by bib-1 object verdict | 24 COMPATIBLE, 1 MATERIAL_CONFLICT | 90 COMPATIBLE, 1 INSUFFICIENT, 3 MATERIAL_CONFLICT | 97 COMPATIBLE, 4 INSUFFICIENT, 4 MATERIAL_CONFLICT |
| Changed claims (dt-2 to dt-3) | 1 | 2 | 4 |
| New positives | 0 | 0 | 0 |
| Units with a positive claim, dt-2 to dt-3 | 19 to 18 | 78 to 76 | 86 to 82 |
| New NOTICE_CITED / NOT_FOUND | 0 / 0 | 0 / 0 | 0 / 0 |

Every changed claim has the same transition: D-14 `RETRACTED_WORK_CITED` becomes D-13a `UNRESOLVED_IDENTITY`
(`BIBLIOGRAPHIC_OBJECT_CONFLICT`). No claim moves between positive classes, and no positive is created. This matches
the oracle property that bib-1 can only remove a positive (`oracle-dt3`).

An INSUFFICIENT pair (5 in total) is a positive bib-1 could not check, because the description or the record lacks the
compared fields. It stays positive, exactly as under dt-2.

## 3. Every changed claim

| Set | Revision / unit | Keys | bib-1 (every event of the deciding lookup) | Reading (by hand, `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2) |
|---|---|---|---|---|
| development | `en-1383058278` (bundle `en-3202774-a1`) / `un-00047` | `10.1016/s1701-2163(15)30444-8`, PMID 25375307 | 1 event: authors CONFLICT, title EQUAL | the retracted work; the record lists one author of a nine-author guideline (recall cost) |
| evaluation 1 | `ar-10305362` / `un-00259` | `10.1016/j.cell.2011.07.007` | 1 event: authors CONFLICT, title OVERLAP | another paper cited with this DOI |
| evaluation 1 | `en-41008786` / `un-00005` | `10.1038/nature17620`, PMID 27075097 | 2 events: authors CONFLICT, title EQUAL (both) | the retracted work; the record misspells a co-author (recall cost) |
| evaluation 2 | `en-27958530` / `un-00004` | `10.1186/1743-422x-7-169`, PMID 20663162 | 1 event: authors CONFLICT, title CONTAINED with designation | the P2 failure (Garry, "Comments"): a different publication object |
| evaluation 2 | `en-83484354` / `un-00012` | `10.17116/jnevro20161162199-108`, PMID 27166488 | 1 event: authors CONFLICT, title OVERLAP | the retracted work; a cited surname ends in a Cyrillic letter (recall cost) |
| evaluation 2 | `ar-1651067` / `un-00023` | `10.1136/bmj.2.5914.335-a`, PMID 4827125 | 1 event: authors AGREE, title CONTAINED with designation | the retracted letter itself; the citation adds "Letter:" (recall cost) |
| evaluation 2 | `en-21293835` / `un-00003` | `10.1136/bmj.2.5914.335-a`, PMID 4827125 | 1 event: authors AGREE, title CONTAINED with designation | as `ar-1651067` (recall cost) |

By this engineering reading of the citation and the record (not a label; in-sample; reviewer finding C-09), 2 of the
7 changed claims block a different publication object, and 5 are abstentions on the retracted work itself. Those 5
are the recall cost of the threshold-free rules (spec section 9). Most of these articles belong to campaigns whose
adjudications had been seen before this cycle, so the reading cannot be shown to be independent of them. The reading is an engineering
inspection of the citation and the record, not a label. It is in-sample on design-exposed articles and is not an
estimate. The 7 claims are the 9 MATERIAL_CONFLICT pairs of the development survey (`lows/survey_pairs.json`) less
the JASIST pair, which dt-2 already decides at D-10, with `en-41008786` counted once for its two events.

**Bridged and co-keyed events (reviewer finding B-05).** In every changed claim, every compared event of the deciding
lookup is a MATERIAL_CONFLICT. No positive on these sets is lost because a bridged or co-keyed event conflicts while
the direct event agrees: the development count is 0. The snapshot count is 7 of 81,743 single-key positives (spec 9).

## 4. The two named regressions

- **JASIST** (`en-39868218` / `un-00011`, DOI `10.1002/asi.23238`, "Withdrawal:"). dt-2: D-10
  `UNRESOLVED_IDENTITY` (`IDENTIFIER_ROLE_COLLISION`). dt-3: D-10 `UNRESOLVED_IDENTITY`, unchanged. bib-1 also gives
  MATERIAL_CONFLICT (`BIB_TITLE_RELATED_OBJECT`), but D-10 decides first. The false attachment of evaluation 1 is not
  restored (D-083 item 5, condition 1).
- **Garry** (`en-27958530` / `un-00004`). dt-2: D-14 `RETRACTED_WORK_CITED`, the false attachment of P2. dt-3: D-13a
  `UNRESOLVED_IDENTITY` with `BIB_AUTHORS_DISJOINT` and `BIB_TITLE_RELATED_OBJECT`. No rule names the DOI, the author,
  the journal or the "Comments" suffix. The general rule decides it (fail-first: `fail-first/`).

## 5. Role-collision candidates

On the three sets, 18 candidates abstain under the role-collision rule (dt-2 D-10 with `IDENTIFIER_ROLE_COLLISION`):
1 development, 4 evaluation 1 (JASIST included) and 13 evaluation 2. All 18 are same-record collisions, and dt-3
changes none of them. The analysis is in `ROLE_COLLISION_STUDY.md`. D-072 stays strict.

## 6. Censuses on dt-3

The corrective-cycle census tools were rerun on dt-3 (`regression/census/`): the role-collision census, the B-03
census and the pair census. Each equals its dt-2 counterpart (`../corrective/census/`; checked by
`test_final_provenance.py::test_the_role_collision_censuses_are_unchanged_under_dt3`). The census candidates carry no cited
description, so bib-1 cannot act in them and the equality holds by construction (with `bc` False, dt-3 equals dt-2;
reviewer finding C-06). It confirms that D-10 and the other rules are unchanged, not bib-1. The census results keep the
corrective-cycle provenance of those tools (code commit, a clean engine tree, the index); the provenance test checks
that the census tools and the engine are unchanged from that commit to HEAD. In particular, 1,472 of the 31,506 dt-1
positive DOI+PMID pairs stay `UNRESOLVED_IDENTITY` (D-072: 1,410 retracted-work, 39 concern and 23
correction pairs). dt-3 adds no same-work-sibling exemption (D-073), so the C-01 sibling cases are unchanged:
one of them, `ar-3351802` / `un-00059`, is among the role-collision candidates of section 5 and stays
`UNRESOLVED_IDENTITY` (reviewer finding C-11).

## 7. Changed claims of earlier documents

- "Recall cost nil" on the development survey (an early draft) is withdrawn. The survey and this regression show 5
  abstentions on the retracted work itself (section 3).
- The D-055 "at least 20x headroom" claim no longer holds for dt-3: 1.2x at the theoretical maximum
  (`PERFORMANCE_AND_BOUNDS.md` section 2).
- The figures of spec 2.1 for the description sizes are replaced by the committed measurement
  (`lows/description_sizes.json`): a largest description of 1,804 code points and a largest family of 56 values, not
  766 and 14.

Run time: three shards per set on the 4-vCPU container, about 34 min (development), 13 min (evaluation 1) and 16 min
(evaluation 2).
