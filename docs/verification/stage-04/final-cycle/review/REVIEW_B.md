# Review B: identifier semantics, role collisions, notice/original separation (final corrective cycle, D-083)

Reviewer B, independent. Scope as assigned: table dt-3 (rule D-13a) against D-6 to D-16, the separation of notices
from originals, reviewer finding A-04 and its census, the PAIR shape and the claim schema, D-072, and how the
detector adapter binds records. [V] = verified fact (code read, command output or probe output); [I] = inference.

## Scope read

- `src/citerift/investigation/dt1.py` (whole file), `bibliographic.py` (whole file), `adapters/detector.py` (lines
  1-200 and 300-380), `adapters/lookup.py` (`observe`, validation at line 319), `adapters/verify.py` (lookup checks),
  `adapters/normalize.py` (cited object entry points).
- Stage 02 (read only): `src/citerift/retraction/query.py` (`gather` lines 296-390, `public_event` 528-549) and
  `policy.py` (`reduce`, rule 7f, lines 117-180).
- `simulations/stage04/dt3_reference.py`, `decision_space_dt3.py`; `tests/stage04/test_final_bib.py`,
  `test_final_lows.py`, `test_corrective_oracle.py`, `step9_support.py` (`concretize`, `records_of`).
- `schemas/investigation/v1/claim.schema.json` (allOf constraints), `common.schema.json` (`reason`),
  `lookup-observation.schema.json` (`records`).
- `final-cycle/BIBLIOGRAPHIC_SPEC.md` sections 2.1, 6, 7 and 9; `SPECIFICATION.md` 7.3b; `MATHEMATICAL_MODEL.md` (`bc`);
  `RISK_ANALYSIS.md` R4-04; `final-cycle/scripts/a04_invariant.py`, `final-cycle/lows/a04_invariant_census.json`;
  corrective `review/REVIEW_A.md` A-04 and `DECISIONS.md` D-083.

## Method

No full test suite, no network, no file changed except this one. Probe scripts are in the session scratchpad
(`.../scratchpad/revB/`); none is committed.

1. `uv run pytest tests/stage04/test_final_bib.py tests/stage04/test_final_lows.py -q -p no:cacheprovider` gave
   `127 passed in 4.29s` [V].
2. **Production against the dt-3 model** (`probe_dt3.py`). One valid abstract case per distinct dt-3 decision and
   shape was built the way `test_corrective_oracle._representatives` builds them, but over dt-3 cases with
   `bc` in {False, True}. That gave 455 representatives. Each was concretized with `step9_support.concretize` and run
   through the production `dt1_detector`. Rule, class, status, value and reasons were compared with
   `dt3_reference.decide`, with `BIB_AUTHORS_DISJOINT` added on D-13a because the concrete `bc` record conflicts on
   authors. Each claim was also validated against `CLAIM`. Result: `bad 0` [V]. With `bc = True` the rules
   reached were D-1 to D-4, D-6 to D-13, **D-13a (7)**, D-15 and D-16; D-14 was never reached [V].
3. **dt-3 model against the dt-2 model** (`probe_bcprops.py`). The probe ran over every non-PAIR case of
   `decision_space_dt2` and every 211th PAIR case, 218,352 cases in all. For each it checked that
   `R3(bc=False) == R2`, that `R3(bc=True)` differs only where R2 is D-14, and that every R2 D-14 becomes D-13a. Result:
   `{'n': 218352, 'changed': 24} 0` violations [V]. This is a sample, not the exhaustive oracle (see B-01).
4. **Adapter binding** (`probe_bind.py`). A `bc` PAIR case had its committed observations mutated, and the result was
   recorded for each mutation (outputs are quoted in B-06, B-07 and B-10).
5. **Whole pinned snapshot, read only** (`probe_bridge_all.py`, 55 s). Every distinct original DOI and PMID was
   decided as in `a04_invariant.py`, which reproduced D-14 = 81,743 [V]. The probe then decided each positive again
   with a synthetic "perfect" description taken from its first direct event's own record (title, and authors split on
   `;`).

## Findings

### B-01: MEDIUM. The exhaustive dt-3 oracle and its production test are cited as evidence but do not exist

- [V] `simulations/stage04/oracle-dt3/` and `tests/stage04/test_final_oracle.py` are absent (`find` finds neither).
  No `decision_space_dt3_summary.json` exists anywhere.
- [V] Three places cite them as completed evidence:
  - `SPECIFICATION.md:514-515`: "checked over the whole abstract domain: `simulations/stage04/oracle-dt3`, property
    `EQUIVALENCE_BC_FALSE`".
  - `MATHEMATICAL_MODEL.md:304`: "The dt-3 oracle (... `oracle-dt3/`) ... with `bc = false` it equals the dt-2 oracle
    case for case".
  - `tests/stage04/test_corrective_oracle.py:10-11`: "on which dt-3 equals dt-2 (`test_final_oracle.py`)".
- [V] The invariant itself holds wherever I could check it: the 455-representative production run (method 2) and the
  218,352-case model sample (method 3) both gave 0 violations. The brief's own wording ("when present") shows the
  oracle is known to be pending.
- [I] The brief's CRITICAL invariant is "dt-3 differs from dt-2 without a material conflict". The normative
  documents currently rest it on an artifact that has not been produced.
- Recommendation:
  - Run `decision_space_dt3.py --oracle simulations/stage04/oracle-dt3` and commit the oracle and its summary with
    every property at 0 violations.
  - Add `test_final_oracle.py`. It should pin the manifest digest and run production on one representative per
    distinct decision with `bc` in {False, True}; method 2 is a ready template.
  - Until both exist, word the three sentences as pending.
  - This is a precondition of any freeze-3 candidate. If a freeze is proposed without it, this finding becomes HIGH.

### B-02: MEDIUM. The D-072 study required by D-083 item 5 is cited but absent

- [V] `BIBLIOGRAPHIC_SPEC.md:172` ("study in `ROLE_COLLISION_STUDY.md`") and `SPECIFICATION.md:519`
  (`final-cycle/ROLE_COLLISION_STUDY.md`) cite a file that does not exist.
- [V] D-083 item (5) requires "a study of the D-072 role-collision recall cost, keeping the strict rule unless a
  resolution is proven safe".
- [V] The code-level claim is true; see B-09.
- [V] `BIBLIOGRAPHIC_SPEC.md:51` also cites a missing `PERFORMANCE_AND_BOUNDS.md`. Reviewer A noted this too.
- Recommendation: commit the study, or record that it is deferred and why. Keeping D-072 unchanged is safe as it
  stands; what is missing is the evidence that item 5 asks for, not a code change. Until then, remove or qualify the
  citations.

### B-03: LOW. The committed A-04 census was produced by an earlier script and carries no provenance

- [V] `a04_invariant.py` (HEAD, after commit `49e7187`) writes a `provenance` key, which records the tool's SHA-256
  and the index identity. The committed `lows/a04_invariant_census.json` has no such key. Its keys are only
  `exposure_*`, `invariant`, `keys_decided`, `positives_by_class`, `rules`, `table_version` and `violations`. So it
  was written by the `59f2ad0` version of the script.
- [V] The figures are internally consistent:
  - `rules` sums to `keys_decided`: 14,801 + 240 + 81,743 + 2 + 17 = 96,803.
  - D-14 = 81,743 = 77,914 + 2,741 + 1,088 (`positives_by_class`).
  - `violations` is `[]`.
  - The exposure holds 254 entries and one key (`pmid 3507357`).
- [V] My independent pass over the pinned index (method 5) reproduced D-14 = 81,743.
- Recommendation: re-run the HEAD script and commit its output with provenance, so that the census is bound to the
  pinned index and to the engine commit. Add one detector-level regression test for the A-04 shape: a matched lookup
  whose only events of the claim's type are bridged through a non-cited key must not give D-14. Today only the census
  checks it.

### B-04: LOW. I-A04 is an adequate empirical check, but the proof is Stage 02 rule 7f, and the PAIR scope is unstated

**Two of the three clauses of I-A04 are vacuous on a D-14 positive [V].**

- A role-ambiguous event, or `BRIDGE_ONLY_SUPPORT`, already makes D-10 hold, and D-10 precedes D-14
  (`dt1.py:451-458, 473, 478`).
- What the census really checks is therefore "some direct event's type gives the claim's class". That is weaker than
  the counterfactual "the decision without the bridged events is the same".

**The counterfactual holds by construction [V].**

- Stage 02 `policy.reduce` (rule 7f, `policy.py:117-160`) computes the projection from the direct assertions alone.
- It keeps `verified_fact` only when accepting the bridges would not change the value.
- Otherwise the result is `uncertain`, with `BRIDGED_EVIDENCE_MATERIAL` or `BRIDGE_ONLY_SUPPORT`.
- A bridged record can therefore only demote a positive, never create one. RISK R4-04 states the principle in words
  ("Stage 02 never counts bridged records toward a verified value"). Rule 7f, plus the D-10 guard on
  `BRIDGE_ONLY_SUPPORT`, is the proof; the census confirms it on data.

**The census method is sound for single keys.**

- [V] The method uses the production `observe` and `lookup_view` and dt-3 `decide`.
- [I] Leaving out the description is the worst case: D-13a only removes positives (method 3), so a description can
  only lower the count of positives under test.

**What the census does not cover:**

- PAIR, which is structurally outside A-04 [V]. For a pair query, `gather` (`query.py:300-322`) does no co-occurrence
  bridging. Its only linked events are PMID events marked `linked_via = "query_pair"`, attached through the cited
  PMID. A direct event naming a different key of the other scheme makes the query `ambiguous_identity`, and Stage 04
  turns that into a witness and D-6.
- Keys that are not original identifiers. These cannot be `matched`, so they cannot reach D-14.

**Recommendation:** in RISK R4-04 and wherever the census is cited:

- name rule 7f as the proof and the census as its confirmation;
- state that two clauses of I-A04 are implied by the table;
- state the PAIR argument above, so that "single-key" is not read as a gap.

### B-05: LOW. Comparing every event of L, bridged events included, has a recall cost that section 9 does not state

**No safety problem [V].** D-13a can only replace D-14, so comparing more events can never yield a positive,
`NOTICE_CITED` or `NOT_FOUND` (`dt1.py:477-478`; methods 2 and 3).

**The cost [V, method 5].** For 7 of the 81,743 single-key positives, a description copied from the first direct
event's own record already gives D-13a:

- **PMID `3507357`, through bridged events only.** Its direct event `ev-0038168` is "Mucosal healing predicts
  quality-of-life benefits for adalim…" (P Rutgeerts et al.). The other 254 events are conference abstracts by other
  authors, reached through the supplement DOI `10.1016/s1873-9946(10)00006-1`. Stage 02 does not count them
  (`BRIDGED_EVIDENCE_NOT_COUNTED`), yet they give `BIB_AUTHORS_DISJOINT`. A correct citation of the Rutgeerts paper
  therefore abstains under dt-3, where dt-2 gave `CONCERN_CITED`.
- **6 keys through direct events.** Each key is shared by several records, for example DOI
  `10.1080/02699052.2023.2194723` with 145 events. One further key, PMID `17381062`, gives `BIB_TITLE_RELATED_OBJECT`
  between two records of the same key.

**Assessment.** [I] Abstaining here is consistent with "prefer abstention": a key that names several objects does not
establish which object the citation means. Still, the cost is real and it is not among the known limits of section 9.
The synthetic description is my approximation of a real citation [I].

**Recommendation.** Keep the rule, which is fail closed. In section 9 and in RISK R4-04a, state that bridged and
co-keyed records are compared and can block a correct positive. Give this measurement, or the regression's own, as the
exposure.

### B-06: LOW. A record's content is not cross-checked with its own public event

- [V] The public Stage 02 event already carries `title` and `journal` (`query.py:541-542`). `_records`
  (`detector.py:60-77`) binds a record only by position, `event_id` and `row_sha256`, and never compares the record's
  `title` and `journal` with the event's. VERIFY checks the record schema only (`verify.py:265-281`).
- [V] Probe: setting every record's title to "Totally different words here" while leaving the events unchanged gave
  `D-13a … ['BIBLIOGRAPHIC_OBJECT_CONFLICT', 'BIB_AUTHORS_DISJOINT', 'BIB_TITLE_DISJOINT']`. The decision changed and
  there was no `ADAPTER_INCONSISTENT`.
- [I] Production cannot reach this:
  - LOOKUP builds `events` and `records` from the same `ev.events` list (`lookup.py:250-255`).
  - Observations are content-addressed and schema-validated at commit (`lookup.py:319`).
  - The gap matters only for corrupted or hand-made committed content.
- Recommendation: in `_records`, and in VERIFY's lookup check, require `record.title == event.title` and
  `record.journal == event.journal`, failing with `ADAPTER_INCONSISTENT` otherwise. The check is cheap and closes the
  last misbinding path.

### B-07: INFO. Mistyped record fields and null row hashes fall back to dt-2 instead of failing

- [V] Probe results:
  - `authors` given as a list gave `D-14 RETRACTED_WORK_CITED`.
  - `title`/`authors` set to null gave D-14.
  - Both `row_sha256` values set to null passed binding (`None == None`, `detector.py:72-73`).
- `RecordObject.from_json` treats a wrong type as absent, which is INSUFFICIENT. This is the spec's B8 choice.
  It differs from `_flags` (`detector.py:51-57`), which fails closed on malformed input.
- [V] Production cannot reach it: the record schema requires string or null types and a `sha256`, and LOOKUP
  (`lookup.py:319`) and VERIFY (`verify.py:269`) both validate.
- Recommendation: none required. Optionally, raise `ADAPTER_INCONSISTENT` when a record field is present with a wrong
  type or `row_sha256` is not a string, for symmetry with `_flags`.

### B-08: INFO. D-13a placement, its guard, the PAIR tail and the claim schema are correct

D-13a placement and guard:

- [V] D-13a is the 14th entry of `RULES` (`dt1.py:477`): after D-13 (`476`) and before D-14 (`478`).
- [V] Its guard is the D-14 guard (`L_is("matched", VF)`) conjoined with `bib_conflicts`. Python's `and`
  short-circuits, so bib-1 is evaluated only when D-1 to D-13 have all failed and D-14 would hold.
- [V] No earlier guard reads `Event.record` or `Candidate.cited` (grep of `dt1.py`: only lines 117, 195, 225 and
  360-371 touch them).
- [V] D-15 and D-16 require L to be `notice_only` or `no_record`. D-13a requires `matched`, so the guards are
  disjoint.

Comparisons and reasons:

- [V] `comparisons` (`dt1.py:360-366`) iterates `lk.events`, the complete event list: VERIFY checks
  `event_count == len(events) == total_event_count`. It is empty unless L is matched.
- [V] bib-1 reasons are non-empty exactly when the result is MATERIAL_CONFLICT (`bibliographic.py:450-457`). So the
  D-13a reasons (`dt1.py:546`) are exactly `BIBLIOGRAPHIC_OBJECT_CONFLICT` plus the reasons of the conflicting events.

PAIR tail (method 2):

- [V] DOI and PMID D-13a claims carry `[BIBLIOGRAPHIC_OBJECT_CONFLICT, BIB_*]`, with or without
  `CO_REPORTED_MULTIPLE`.
- [V] PAIR D-13a claims carry it alone, with `PAIR_UNCORROBORATED`, or with `KEY_RESULTS_DIFFER` and
  `PAIR_UNCORROBORATED`.
- [V] These are exactly the dt-3 model's tails (`BC_EFFECT`), and every claim validates against `CLAIM`.

Claim schema against `dt1.py`:

- [V] `UNRESOLVED_IDENTITY` allows rule D-13a with status `uncertain`, value null and a keyed shape.
- [V] D-13a must carry `BIBLIOGRAPHIC_OBJECT_CONFLICT` and at least one `BIB_*`. This is guaranteed because a
  conflict implies a non-empty reason.
- [V] `BIB_*` reasons are allowed only on D-13a, and production adds them nowhere else.
- [V] D-13a is not in the "no upstream reasons" list, which matches `upstream_role = L` (`dt1.py:545`).
- [V] `KEY_RESULTS_DIFFER` is PAIR-only, `CO_REPORTED_MULTIPLE` is single-key only, and `PAIR_UNCORROBORATED` holds
  exactly when kappa is UNDETERMINED. All three hold in production.

A schema gap:

- [I] The schema cannot express that a D-13a claim is supported by a `lookup_record` item for each event of L. Only
  the detector (`detector.py:344-353`) and the corpus test assert it.

### B-09: INFO. Notice/original separation holds, and bib-1 never resolves a role collision (D-072 unchanged)

Separation:

- [V] A notice record is never compared with the citation:
  - Comparisons exist only for a matched L (`dt1.py:363-365`).
  - Every event of a matched lookup is `matched_by` doi or pmid. Otherwise `events_fit_state` fails, and D-5
    (`EVENTS_OUTSIDE_STATE`, `dt1.py:177-178, 396`) precedes everything.
  - Stage 02 keeps notice hits out of `events` for a matched query: they go to `notice_hits` (`query.py:362-366`).
- [V] The section 6 sentence "D-15 and D-16 … hold no original-role event to compare" is true for Stage 02 data.
  - A `notice_only` L holds only direct `matched_by = "notice"` events.
  - A `no_record` L holds no event.
  - For a PAIR, F-9 (`implied_pair_state`, `dt1.py:374-382`, enforced by D-5) makes Q2 `notice_only` or `no_record`
    only when neither Q1 lookup is matched.
  - Precision note: a `notice_only` lookup does carry `records`, which describe the works whose notices are cited.
    They are not compared, because `comparisons` returns `()`.
- [I] A key that is both original and notice reaches D-13a or D-14 only through a discriminating second key (D-10
  otherwise). Even then the record compared describes the original work.

D-072:

- [V] `role_collided`, `discriminating`, `role_ambiguous`, `notice_elsewhere` and `_d10` (`dt1.py:299-354, 451-458`)
  read only identifiers, flags, notice identifiers, `notice_hits`, `collision` and `basis_reasons`. None reads a
  record, the cited object or a comparison.
- [V] `test_d13a_never_overrides_an_earlier_rule` and method 2 show that `bc = True` leaves every D-10 decision
  (56 representatives) unchanged.
- [V] Stage 02 is unchanged: `git diff 6663314 HEAD --stat -- src/citerift/retraction` is empty.

### B-10: INFO. Detector record binding fails closed on structural defects

[V] Probe outputs on a `bc` PAIR case:

| Mutation | Result |
|---|---|
| `records` removed | `ADAPTER_INCONSISTENT: a lookup observation's records do not match its events` |
| One extra record | the same |
| Records reversed | `ADAPTER_INCONSISTENT: a lookup record is not bound to its event` |
| Record 1 replaced by a copy of record 0 | the same |
| `row_sha256` of record 0 changed | the same |

- [V] Unmutated, the case gives `D-13a UNRESOLVED_IDENTITY`.
- [V] `DetectFailure` produces no claim.
- [V] Every lookup of the candidate is checked, not only L, so an unavailable lookup must also carry `records: []`.
- Content mismatches are covered in B-06 and type defects in B-07.

## Verdict

Within my scope, dt-3 is correct. D-13a is correctly placed and guarded, can only turn a D-14 positive into an
abstention, never yields `NOTICE_CITED`, leaves D-072 and the separation of notices from originals intact, and
production matches the dt-3 model with 0 differences. No CRITICAL or HIGH finding. **B-01 (missing oracle-dt3) and
B-02 (missing D-072 study) must be closed before any freeze-3 candidate**; B-03 to B-06 are LOW.
