# Stage 04 pre-freeze review, Reviewer A (scientific semantics)

Repository `/home/user/citerift` at `65c30bd`. This review was read-only: `git status --porcelain` printed nothing at the end. Scratch scripts are in `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/review-A/` (`exp1.py` to `exp4.py`).

## 1. Scope and method

**Code read:**
- `src/citerift/investigation/dt1.py`
- `adapters/detector.py`, `adapters/detect.py`, `adapters/normalize.py`, `adapters/assemble.py`
- `adapters/verify.py` (the claim, evidence and replay checks)
- `ids.py`, `explanations.py`, `projections.py`, `report.py`, `outputs.py`
- `workflow.py` (`DISPOSITION`, `detect_problem`)
- `fold.py` (the evidence-batch checks)
- `operations.py` (the `replay` command)
- Stage 02 `query.py` (`gather`, `relevance`) and `policy.py` (the `no_record` branch)

**Schema:** `schemas/investigation/v1/claim.schema.json`.

**Documents:**
- SPEC sections 6, 7, 11, 12 and 14
- MM sections 4.4 to 6
- RISK_ANALYSIS R4
- DECISIONS D-051 and D-058 to D-063
- STEP9_CLOSURE sections 13, 14 and 17, plus a grep of the Step 10 and Step 11 closures
- `simulations/stage04/dt1_reference.py` (read only)
- `tests/stage04/step9_support.py`, `test_step9_detector.py`, `test_step9_b8.py`, `test_step9_real.py` (VS-5)

**Commands run** (`.venv/bin/python`, from the repository root):
- `pytest -p no:cacheprovider -q tests/stage04/test_step9_detector.py -k "d058 or notice_is_never or not_found or identity_conflict or d10 or kappa or p2 or table_is or budget or reinstated or d17"` → `33 passed, 8 deselected`
- `pytest ... tests/stage04/test_step9_b8.py -k "true_duplicates or oracle"` → `2 passed`
- `pytest ... tests/stage04/test_step10_report.py -k summary_scoped` → `1 passed`
- `exp1.py`: decision outcomes and explanation text for D-12, a D-14 pair, CO_REPORTED_MULTIPLE, a D-15 pair, a D-1 pair and a tainted D-7, using the Step 9 `concretize` fixtures.
- `exp2.py`: whether the reason codes or the coherence value enter `claim_id` or the DETECT output.
- `exp3.py`: whether the tainting occurrence is in the evidence of D-6, D-7 and D-8 claims.
- `exp4.py`: real Stage 02 code over SYNTHETIC rows, giving a `no_record` lookup with a coverage gap → D-12 → explanation.

I did not run the full suite. I did not read any holdout sample or Stage 01 census frame.

## 2. Findings

| Id | Title | Severity | Evidence | Proposed classification | Suggested fix (smallest) |
|---|---|---|---|---|---|
| A-01 | D-12 explanation says "A record exists" for a `no_record` lookup, and calls an invalid-identifier hit "quarantined" | MEDIUM | `explanations.py:74-77`, `:188-189`, `:102`; `dt1.py:407-408`; Stage 02 `query.py:270-281`, `:383-385`; `policy.py:240-242`; SPEC 7.2 line 381; MM F-3 line 163; `exp4.py` output below | 1 (claim wording), plus 4 for SPEC 7.2 and MM F-3 | Pick the template by rule: D-12 gets "No record matched, but rows of the checked sources that may concern this identifier could not be checked (quarantined or invalid identifiers); no finding is stated." Reword the `COVERAGE_GAP_RELEVANT_ROWS` reason text, the `UNRESOLVED_STATUS` limitation, SPEC 7.2 and MM F-3 to "quarantined rows or invalid identifiers". Add a test. |
| A-02 | Replay checks compare only claim ids, so reason codes, κ and alternative values are never re-verified | MEDIUM | `verify.py:291-302`; `detect.py:96-100` (the output holds only the detector identity and sorted claim ids); `ids.py:100-103`; `operations.py:601-608`; STEP9_CLOSURE A-6 (line 315); `exp2.py` output below | 2 | In `detect_replay`, require the re-run claim payloads and DETECT evidence items to equal the committed ones, as `normalize_replay` already does at `verify.py:282-289`. Correct the A-6 sentence. |
| A-03 | D-6 claims carry taint reasons without the tainting occurrences in their evidence | LOW | `dt1.py:388-389` (D-6 adds `*c.taint`); `detector.py:277-278` (occurrences added only for D-4 and D-8); `exp3.py` output below | 1 (evidence sufficiency) | `detector.py:277`: `if rule in ("D-4", "D-6", "D-8")`, or more generally whenever the reasons include a taint reason. This changes the evidence set, and so the claim id, of tainted D-6 claims only. |
| A-04 | CO_REPORTED_MULTIPLE is explained as "the citation names more than one work" | LOW | `explanations.py:109`; SPEC S-6.5 ("more than one key of a scheme … co-reported identifiers are never merged"); `exp1.py` | 1 (wording) | "the citation reports more than one identifier of one scheme; each is checked separately". |
| A-05 | Limitation and summary counts are counts of claims, worded as citations or units | LOW | `explanations.py:177`, `:181-193`, `:216-222`, `:271-273`; `normalize.py:266-269` (one candidate per key for co-reported keys); `report.py:95-97` | 1 (wording) | Say "candidate identifier(s)" or "claim(s)", or count distinct units. Add `UNRESOLVED_USE` to the `OUT_OF_SCOPE_UNITS` parenthetical. |
| A-06 | The finding template "for the work this citation identifies" says more than a pair with κ = UNDETERMINED supports (the D-058 case) | LOW | `explanations.py:60-63`; `exp1.py`: reasons `KEY_RESULTS_DIFFER, PAIR_UNCORROBORATED`, κ `UNDETERMINED`; D-058 rationale | 1 (wording), or 7 if the owner reads the template as the D-058 class decision | Use a neutral base template: "…record a retraction for the work the checked sources reach through this citation's identifiers." Or add a sentence when `PAIR_UNCORROBORATED` is present. |
| A-07 | D-7 drops the taint reasons that D-6 keeps | INFO | `dt1.py:392-394` against `:388-389`; SPEC 7.3 D-7 row; `dt1_reference.py` D-7 branch; `exp3.py`: tainted D-7 reasons `['RETRACTION_EVENT_TYPE_CONFLICT']` | 5 (the specification, the frozen model and production agree) | None now. Record it as a deliberate limitation, or as an owner question for a later table version. |
| A-08 | MM EV-2 is literally false for the tested implementation (Step 9 audit A-5, review F7) | LOW | MM:214-216; `detector.py:213-214`, `:267-274`, `:373-380`; `test_step9_real.py:150` | 4 | Replace it with the wording in section 3. |

**Output of `exp4.py` (A-01):**
```
state no_record issues ['RELEVANT_INVALID_IDENTIFIER'] basis ['COVERAGE_GAP_RELEVANT_ROWS']
D-12 UNRESOLVED_STATUS ['COVERAGE_GAP_RELEVANT_ROWS']
TEXT: A record exists in the checked sources, but its current effect is not established; no finding is stated for this citation.
REASONS: [{'code': 'COVERAGE_GAP_RELEVANT_ROWS', 'text': 'relevant rows of the checked sources are quarantined'}]
```

**Output of `exp2.py` (A-02):**
```
reasons A: ['KEY_RESULTS_DIFFER', 'PAIR_UNCORROBORATED']  reasons B: []
claim_id equal: True
identity equal: True
coherence value UNDETERMINED id independent of value: True
```

**Output of `exp3.py` (A-03):**
```
D-6 IDENTITY_CONFLICT ['IDENTIFIER_MALFORMED', 'IDENTITY_WITNESSED', 'KEY_RESULTS_DIFFER'] malformed occurrence in supporting: False
D-8 UNRESOLVED_IDENTIFIER ['IDENTIFIER_MALFORMED'] malformed occurrence in supporting: True
```

**A-01.** UNRESOLVED_STATUS has two sources: D-11 (the deciding lookup is `matched` with an uncertain projection) and D-12 (the deciding lookup is `no_record` with value null). Both get the one `unresolved_status` template, which states that a record exists and that its "current effect is not established". For D-12 both statements are false. The deciding lookup is `no_record`, and Stage 02 sets `relevant_gap` in the `no_record` branch for any relevance hit, including `RELEVANT_INVALID_IDENTIFIER` (`query.py:383-385`). That is not a quarantine. The exp4 run reproduces this on real Stage 02 code: a cited PMID with no record gets an explanation asserting that a record exists. It does not create a finding, because the class is an abstention, but it says more than the evidence supports. The same wording is in the `UNRESOLVED_STATUS` limitation and, for "quarantined", in SPEC 7.2 and MM F-3. Stage 02's own text is correct: "Quarantined rows or invalid identifiers that may concern this work exist." No test pins the D-12 text (a grep of `tests/` for "A record exists" finds nothing).

**A-02.** `claim_id = H(cand_ref, class, rule, table_version, ES)`, and evidence ids are `H(observation, pointer, kind)`. Neither binds the reason codes, `candidate.coherence`, the `upstream_reasons`, the alternative values, or the `value` field of DETECT evidence items such as κ or the `work_candidate` record. Two VERIFY checks are affected:
- DETECT_REPLAY compares only the set of claim ids and the output digest, which is a digest of the detector identity string and the sorted claim ids.
- ASSEMBLE_REPLAY rebuilds the report from the committed claims, not from the re-run.

The `replay` command uses the same two methods. exp2 changes the detector so that it drops `KEY_RESULTS_DIFFER` and `PAIR_UNCORROBORATED`. The claim id and the detector identity stay the same, so VERIFY and `replay` would report the result as reproduced. Step 9 audit A-6 says that "a detector change without a version change shows as a DETECT replay mismatch at VERIFY"; that holds only for changes that alter class, rule or evidence set. This matters at freeze because A-6, the engine-version bump, relies on that sentence. Reason and κ semantics are themselves a deterministic function of the evidence set's content, so this is a gap in verification, not in identity.

**A-03.** D-6 attaches `IDENTIFIER_MALFORMED`, `IDENTIFIER_UNCONFIRMED` or `IDENTIFIER_ROLE_UNRESOLVED` to IDENTITY_CONFLICT claims, as SPEC 7.3 requires. Only D-4 and D-8 put the unit's occurrences into the supporting set. A malformed or unresolved-role occurrence is not a key occurrence, so nothing in the claim's evidence set names it. The reason can still be derived from the extraction, which the claim reaches through the unit item's observation. But the claim's own evidence does not justify it, while D-8 for the same unit does. This is inconsistent with S-12.1, under which every reason has its chain.

**A-04.** Two DOIs in one citation (S-6.5) can be one work, for example a preprint and the published version, or a DOI alias. Stage 04 deliberately never decides that, so the reason text asserts something no evidence states.

**A-05.** `_counts` counts claims. A unit whose keys are co-reported yields one claim per key. "For N citation(s)…", "N extracted unit(s) are outside detection scope" and the summary sentence "For the N identified citation(s) listed…" therefore overcount. These are wording precision issues, not semantic ones.

**A-06.** In the D-058 case the citation's DOI is a notice and its PMID is the original. The class is correct by D-058. The base template, however, presents "the work this citation identifies" as settled, while the claim's own reasons say the sources do not name the DOI and the PMID together. The reasons are shown in the chain, so this is minor.

**A-07.** A tainted unit decided by D-7 loses the information that an identifier is unconfirmed or malformed. D-6 keeps it. The behaviour is consistent across the specification, the frozen reference model and production, and the class is a contradiction routed to resolution, so nothing is strengthened. It is reported only so the owner can see the asymmetry. I found no defect in the reference model.

**A-08.** Covered in section 3.

## 3. EV-2 proposed wording

**Proposed text for MM 4.6:**

> **EV-2** (claim values are justified by the claim's own evidence). Let `S(claim) = ⟨sup, con, alt_1, …, alt_k⟩`. Every field of a claim is exactly one of:
> (a) a constant of dt-1: class, rule id, table version, reason codes, upstream-reason `source`; or a function of the class alone: `status`, and `value` for every class whose value is null;
> (b) a derived identity or count: `cand_ref` (SPEC 4.3), `evidence_set = H_blob(canon(S))`, `claim_id`, `supporting_count = |sup|`, `contradicting_count = |con|`, `alternatives[i].supporting_count = |alt_i|`;
> (c) a value read from committed evidence. There is an item `ev` in `sup` (in `alt_i` for alternative `i`) such that the claimed value is either
>   (c1) a component, at a fixed relative path, of the value that `ev.pointer` selects in `ev.obs`, or
>   (c2) the value recorded by `ev`, where that value is a fixed pure function of the observations named by `ev` and by the items in its `refs` closure (all of them earlier committed evidence).
>
> In particular:
> - `value` (positive classes and `NOT_FOUND_IN_CHECKED_SOURCES`) is `/value` under the `lookup_result` item at `/result/projection/retraction_status` of `L(c)`.
> - Each `upstream_reasons[j].code` is an element of `/projection/basis/reasons` under its `evidence`, the `lookup_result` item at `/result` of that lookup.
> - A D-7 alternative's value is `/value` under its `lookup_result` item at `/result/projection/retraction_status/alternatives/i`.
> - `candidate` is the value of the `work_candidate` item. Its keys are the `(scheme, normalization.normalized)` of its `identifier_occurrence` refs. Its `coherence` is the value of the `coherence` item (κ of MM 5.3 over the three lookup observations its refs name), or null for shapes other than PAIR.
> - A D-6 alternative's `reached_by` and `work[scheme]` are the key of an `identifier_occurrence` item in `alt_i`. `work[other]` is the single non-null `original_<other>` of the `lookup_event` items `/events/k` in `alt_i`, and null when there are none or several.
>
> No non-constant claim value is taken from content outside `S(claim)` and the refs closure of its items. No value is inferred from the absence of evidence except κ ∈ {UNDETERMINED, NOT_DETERMINED} (MM 5.3, a predicate over the whole lookup observations named by the coherence item's refs) and the null of `work[other]`. Supporting items that hold no claimed value (for example witness fields or index identity) are allowed; they justify the class, not a value.

**Justification against the code:**
- **Value.** `dt1.py:416` sets `cls = POSITIVE[L.value]`, and `dt1.py:195,198` sets `value = _VALUE[cls] = L.value`. `detector.py:289-291` (D-14 and D-16, through the deciding lookup) adds `projection_ev`, whose pointer is `/result/projection/retraction_status` (`detector.py:213-214`). That pointer selects an object holding `status` and `value`, so the claimed value sits at `/value` below it: case (c1). `test_step9_real.py:150` asserts exactly `status["value"] == claim["value"]`.
- **Coherence.** `detector.py:267-271`: the `coherence` item is at `/query` of Q2, with value `out.kappa` and refs to the `/result` items of the three lookups. κ reads `/events` of those observations (`dt1.py:204-245`), not the pointed-to value: case (c2).
- **Candidate.** `detector.py:272-274`: the `work_candidate` value `{shape, keys, coherence}` equals `claim["candidate"]` (`detector.py:306`). Its refs are the unit item, the first occurrence of each key, and the coherence item. `detector.py:253-262` checks that the keys equal the occurrence keys.
- **Upstream reasons.** `detector.py:294-301`: each code comes from `views[o].basis_reasons` (`/result/projection/basis/reasons`), and its `evidence` is `result_ev(o)` (`/result`). `sets.claim_set_problem` (`sets.py:99`) requires that evidence to be in the set.
- **D-7 alternatives.** `detector.py:368-380`: the value is `conflict_groups[i][0]`, which `lookup_view` (`detector.py:71-79`) takes, in order, from `stated[i]["value"]`. The item is at `…/alternatives/i`.
- **D-6 alternatives.** `detector.py:340-354`: `mine` holds the direct events of the side's scheme. `work[other]` is the unique `original_<other>` of `mine`, or None. The alternative's support includes `event_ev` for every event in `mine`, plus the key occurrence.
- **Identities and counts.** `detector.py:302-319`.

The wording does not broaden what a claim may assert: every non-constant value is tied to a named item and a fixed function. The present phrase "a constant of the decision table" is kept and made explicit.

## 4. Checked, no finding

- **Rule order and guards.** `RULES` (`dt1.py:337-355`) is D-1 to D-17 in SPEC 7.3 order, first match wins (`dt1.py:359-360`). Each guard names the exact contract form it accepts (`Lookup.form`, `dt1.py:111-126`; `CONTRACT`, `:45-52`). A malformed deciding lookup reaches D-17 and a malformed non-deciding one reaches D-5 (`dt1.py:268`). `test_the_table_is_d1_to_d17_in_order` and `test_d17_is_the_gap_for_a_malformed_deciding_lookup` pass.
- **D-5 and P2.** Every condition of SPEC S-6.12 and MM `pairok` is in `violations` (`dt1.py:262-294`), including `KAPPA_Q2_DISAGREE` when all three lookups are available. Production adds `EVENTS_OUTSIDE_STATE`, which is stricter than the specification. `test_p2_all_available_incompatible_iff_q2_ambiguous` passes.
- **κ.** κ uses only direct events of available lookups (`dt1.py:204-245`), as SPEC 6.5 requires. INCOMPATIBLE is decided before NOT_DETERMINED, NOT_DETERMINED before COHERENT, and COHERENT before UNDETERMINED. κ is None for shapes other than PAIR.
- **D-058.** Stage 02 `gather` (`query.py:301-321`) gives a matched Q2 from the original PMID's events when the notice DOI has no original-DOI events. The only possible witness is the PMID event's `original_doi`, so κ is UNDETERMINED when Retraction Watch records no original DOI, and D-6 applies when it does. `test_d058_notice_doi_with_the_original_pmid` passes and pins all three outcomes. SPEC 7.4 and RISK_ANALYSIS R4 (lines 80-83) are corrected.
- **D-059.** `PMID_ROLE_COLLISION` becomes a reason only inside D-10 (`dt1.py:397-404`). The `/result` item of every lookup, which holds the issue, is supporting evidence for every class other than D-1 to D-4 (`detector.py:279-281`). The BCAS3 test (`test_step9_real.py:297-327`) checks this per lookup.
- **D-060.** The `work_candidate` pointer is the first key occurrence, or `/units/i` for a NONE candidate (`detector.py:272`). The `_Items` collision guard is in place (`detector.py:158-163`). Memory additionally refuses any duplicate evidence id across steps (`fold.py:344-345`, M-14). The D-051 function is unchanged (`ids.py:83-86`). The B-8 tests pass.
- **NOTICE_CITED.** Status `uncertain`, value None (`dt1.py:63`, `:417-418`). It is not in `report.POSITIVE` (`report.py:38`) and is skipped by projections (`projections.py:153`). Its template attaches no status to the work. `test_a_notice_is_never_positive` passes.
- **IDENTITY_CONFLICT.** The claim is `conflicting` with value null and two alternatives (the schema's `prefixItems` require doi, then pmid). `workflow.detect_problem` enforces exactly one `identity_conflict` question, `ROUTE_NEEDS_RESOLUTION`, and no positive or NOT_FOUND claim for the same candidate (`workflow.py:354-372`). ASSEMBLE gives terminal state NEEDS_RESOLUTION (`assemble.py:140`). With one Q1 unavailable, the alternative carries the witness field and the claim carries `LOOKUP_PARTIAL`; the tests pass.
- **NOT_FOUND_IN_CHECKED_SOURCES.** It comes only from D-16. D-8 (taint) and D-13 (any unavailable lookup) precede it, and DETECT fails closed if the deciding `no_record` lookup names no checked source (`detector.py:239-251`). The schema pins rule D-16 and the reason. The checked sources are read from the deciding observation (`assemble.py:93-96`), the template is scoped, the `FORBIDDEN` list covers "clean/safe/not retracted", and the summary sentence appears only when every in-scope claim is NOT_FOUND.
  - *Inference, not verified:* across Q1 and Q2, consistency of the coverage gap relies on Stage 02's `relevance` taking the union over keys (`query.py:239-252`); Stage 04 itself does not guard it.
- **Claim identity.** `claim_id` inputs match MM P3(c) (`ids.py:100-103`; recomputed in `workflow.py:350-351`). Distinct candidates of one unit have distinct `cand_ref` (`ids.py:95-97`).
- **Epistemic status.** `dt1.STATUS` equals SPEC table 7.2. v1 projections copy the Stage 02 assertion, or downgrade it to `uncertain` when it is not uniform, never to `conflicting` (`projections.py:98-109`).
- **Reference model.** `simulations/stage04/dt1_reference.py` and production agree on every rule I inspected, including how D-6 and D-7 handle taint. I found no defect in the reference model and propose no change to it.

NOT VERIFIED: this is a review record. It found two MEDIUM defects (A-01, A-02) and three LOW claim-correctness defects (A-03 to A-05) that are open, and it does not certify Stage 04 as complete.
