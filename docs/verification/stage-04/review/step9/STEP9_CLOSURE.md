# Stage 04 Step 9: the production decision table dt-1 (closure record)

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yP5ifnawj9aWmi7tWi8poxsz` (2026-11-12T16:52:46Z), baseline
`8b623cd572480c88f9c4bfb619e7b863e996eab7` (Step 8 accepted and closed, D-056, D-057). Step 10 is not started: no
CLI, no report delivery, no new projection, no vertical-slice acceptance, no Step 12 freeze, no pre-registration, no
holdout, no annotation and no evaluation in this step. The frozen evaluation and holdout plan is unchanged.

Labels: **[verified]** measured or tested here, with the file named; **[inference]** derived, not measured;
**[limit]** a stated limitation; **[owner]** needs an owner decision.

Data. Synthetic inputs are labeled SYNTHETIC wherever they are used (`tests/stage04/step9_support.py`). Real inputs are
only previously exposed design data (owner decision D-5): the three design bundles of SPEC S-7.4 (VS-1 MMR, VS-2 ar
Obokata, VS-3 en Obokata), the Step 8 attributed Retraction Watch subset, the Step 8 B-8 unit (enwiki 1379214029,
a retained Stage 03 reserve bundle) and, for the development measurements only, the 232 retained Stage 03 revisions
of the planning join probe with the full pinned Retraction Watch index. Nothing in this record is precision, recall
or an evaluation.

## 1. Build-vs-Adopt (item 2)

`STEP9_BUILD_VS_ADOPT.md`: 15 candidates (rule engines, decision tables, expression evaluators, policy engines,
Datalog and CLIPS-style systems) plus the standard-library `match` and `singledispatch`, each with repository,
version, licence, declared dependencies, maintenance, 3.12/3.13 support, determinism, offline use, rule order,
auditability, complexity saved and added, and fit with the exhaustive differential. **Decision: no dependency.**
REFERENCE ONLY: the DMN `FIRST` hit policy and GoRules zen first-hit tables (the same model as `RULES`) and
`rule-engine` (how a typed expression language would look if the table ever became data). Rejected for: no
first-match guarantee, a second language or runtime, abandonment, copyleft (LGPL/GPL would need an owner decision),
or another problem domain. `pyproject.toml` and `uv.lock` are unchanged [verified, `git diff 8b623cd -- pyproject.toml
uv.lock` is empty]. [limit] Open issues and advisories of the candidates were not read (the GitHub API is limited to
this repository in this session); maintenance is release history only.

## 2. B-8: evidence identity of co-reported candidates (item 3) — RESOLVED, D-051 unchanged

**Fail-first** [verified, `tests/stage04/test_step9_b8.py::test_fail_first_the_unit_pointer_gives_two_facts_one_id`].
Real unit: enwiki revision 1379214029 (page 1898990, retained Stage 03 reserve bundle `en-1898990-a1`), unit
`un-00013`, an `identifier_link` DOI `10.10520/ejc123796` and a `primary_citation_field` DOI
`10.20940/jae/2012/v11i1a5`. NORMALIZE splits it into two single-key candidates, both flagged
`CO_REPORTED_MULTIPLE` (S-6.5). Under D-051, `evidence_id = H("citerift-evidence/1", obs, pointer, kind)`; a
`work_candidate` item placed at the unit's pointer gives both candidates **the same id** while their values (keys)
differ. A store keyed by id would either refuse the second item or keep one fact for two candidates: distinct facts
collide. The test reproduces the equal ids and different values on the real unit.

**Resolution (smallest semantically correct change): the pointer, not the identity function.** DETECT places
`work_candidate` at the first candidate-role occurrence of the candidate's keys in its unit (`/identifiers/j`, the
first of its key evidence), or at the unit (`/units/i`) for a `NONE` candidate, and `coherence` at `/query` of the Q2
observation. Candidates of one unit have disjoint key sets (S-6.5) and an occurrence belongs to one unit, so the
pointers of distinct candidates are distinct (proof: MM 4.6, "Candidate-scoped evidence"). A `coherence` item is a
function of the pair's lookups, so equal pointers carry equal values. In addition the production evidence store
(`adapters/detector.py`, `_Items.add`) refuses an id that would name two different items: DETECT fails closed with
`ADAPTER_INCONSISTENT` ("B-8 guard"), and true duplicates still deduplicate
(`test_true_duplicates_still_deduplicate`).

- Production on the real unit: each candidate has its own `work_candidate` item, at `/identifiers/…`, with its own
  keys; the investigation has exactly one `work_candidate` per candidate; replay gives the same claim ids and
  evidence batch digests [verified, `test_production_gives_each_candidate_its_own_work_candidate_evidence`,
  `test_replay_gives_the_same_ids`].
- **No id, schema or version change.** `ids.py`, `normalize.py`, the schemas, VERIFY and the evidence-set format are
  unchanged; D-051 (`H(observation, pointer, kind)`) is unchanged. SPEC 4.3 and MM 4.6 now state where DETECT puts the
  candidate-scoped kinds and why they are injective. Because the identity function is unchanged, no new owner-level
  design correction is recorded. [owner] The owner may still want to acknowledge this reading of D-051 (section 17).
- **Step 4 oracle manifest unchanged**: the oracle holds no evidence identity; MANIFEST SHA-256
  `411050772807cfbc5e2053431307516344984a759c489c746a490f1db3e27735`, 12,632,448 cases
  [verified, `test_the_step4_oracle_manifest_is_unchanged`; `git diff 8b623cd -- simulations/` is empty].

## 3. Architecture and the dt-1 mapping (items 1, 4, 5)

- `src/citerift/investigation/dt1.py` — pure core, no I/O, no dependency. Typed views `Event`, `Lookup`, `Candidate`;
  `kappa`; `violations` (the D-5 checks); `RULES`, a tuple of 17 `(rule id, guard)` pairs in SPEC order, first match
  wins (`first_rule`); `decide` returns an `Outcome` (rule, class or failure code, reasons, κ, violations, witnesses,
  conflict and upstream roles). Status and value follow from the class (SPEC 7.2).
- `src/citerift/investigation/adapters/detector.py` — the production detector `dt1_detector` (identity
  `citerift-dt1-detector/1 (dt-1)`): parses each Stage 02 lookup observation once (`lookup_view`), builds the
  candidate view, calls `decide`, and builds the evidence items, evidence sets (D-047), alternatives and claims. It
  is the default detector of `adapters.plan.Integration`; `Integration(detector=None)` still fails DETECT with
  `DECISION_TABLE_GAP`.
- `adapters/detect.py` — `DetectFailure(code, detail)`: D-5 → `ADAPTER_INCONSISTENT`, D-17 → `DECISION_TABLE_GAP`,
  a terminal DETECT failure with **no claim committed** (the controller commits DETECT's records only on success).
- Dispositions, routing and questions are the controller's (`workflow.DISPOSITION`, `CONFLICT`, Step 7); DETECT
  emits claims only. `IDENTITY_CONFLICT` and `CONTRADICTION_IN_SOURCES` route to `ROUTE_NEEDS_RESOLUTION` with an
  open question (W-8).

| Rule | Guard (production, `dt1.RULES`) | Class |
|---|---|---|
| D-1 | use `UNUSED` | `UNUSED_DEFINITION` |
| D-2 | use not established | `UNRESOLVED_USE` |
| D-3 | shape `NONE`, untainted | `NO_IDENTIFIER` |
| D-4 | shape `NONE`, tainted | `UNRESOLVED_IDENTIFIER` |
| D-5 | `violations(c)` non-empty | fail `ADAPTER_INCONSISTENT` |
| D-6 | `PAIR` and κ = `INCOMPATIBLE` | `IDENTITY_CONFLICT` |
| D-7 | some lookup (order L, Q1 DOI, Q1 PMID) matched with `conflicting`/null | `CONTRADICTION_IN_SOURCES` |
| D-8 | taint | `UNRESOLVED_IDENTIFIER` |
| D-9 | L `ambiguous_identity`, `uncertain`/null | `UNRESOLVED_IDENTITY` |
| D-10 | L matched in contract, and a `PMID_ROLE_COLLISION` naming a PMID-matched event or `BRIDGE_ONLY_SUPPORT` | `UNRESOLVED_IDENTITY` |
| D-11 | L matched, `uncertain`/null | `UNRESOLVED_STATUS` |
| D-12 | L `no_record`, `uncertain`/null | `UNRESOLVED_STATUS` |
| D-13 | some lookup unavailable | `LOOKUP_UNAVAILABLE` |
| D-14 | L matched, `verified_fact` with a value | positive class of the value |
| D-15 | L `notice_only`, `uncertain`/null | `NOTICE_CITED` |
| D-16 | L `no_record`, `uncertain`/`not_found_in_checked_sources` | `NOT_FOUND_IN_CHECKED_SOURCES` |
| D-17 | otherwise | fail `DECISION_TABLE_GAP` |

Precedence (item 5) is the tuple order and is tested directly [verified, `test_the_table_is_d1_to_d17_in_order`,
`test_identity_conflict_outranks_unavailable_and_contradiction`, the 14 κ variants]: D-6/D-7 precede D-8..D-16;
D-8..D-12 precede D-13; D-13 precedes D-14; D-14 precedes D-15/D-16. κ uses every available lookup's direct events, so
an available witness is never hidden by an unavailable lookup (`pair(UN, M, UN, wp=True)` →
`IDENTITY_CONFLICT`, `test_identity_conflict_with_an_unavailable_q1_uses_the_witness_field`).

## 4. κ and P2 (items 1, 6, 8)

`dt1.kappa` over direct events only (`matched_by` set, `linked_via` null): a witness → `INCOMPATIBLE`; otherwise an
unavailable Q1 → `NOT_DETERMINED`; otherwise co-naming → `COHERENT`; otherwise `UNDETERMINED`. P2 (S-6.12): with
Q1(DOI), Q1(PMID) and Q2 all available, κ = `INCOMPATIBLE` iff Q2 is `ambiguous_identity`; otherwise
`KAPPA_Q2_DISAGREE` → D-5 → `ADAPTER_INCONSISTENT` [verified, `test_p2_all_available_incompatible_iff_q2_ambiguous`;
on real data, `test_a_kappa_q2_disagreement_fails_detect_closed` flips the real Obokata Q2 to `matched`: DETECT
fails `ADAPTER_INCONSISTENT` naming D-5 and `KAPPA_Q2_DISAGREE`, no claim, lifecycle `FAILED`]. The 14 SYNTHETIC κ
variants of item 8 are `test_kappa_variant[...]`; every impossible combination among them fails closed.

## 5. Coverage of the 15 classes (item 9)

Every class is produced by the production code path (`lookup_view` → `candidate_view` → `decide`) on SYNTHETIC
representatives of the valid domain: one per (shape, model decision), 206 representatives
[verified, `test_every_class_is_executed_by_production_code`]. Real data reaches 8 of the 15 (section 9).
`REINSTATED_WORK_CITED` arises only from the contract form `matched`/`verified_fact`/`reinstated`
(`test_reinstated_only_from_the_contract_form`); [limit] it was **not observed in real data** and is unreachable from
real Stage 02 data today (SPEC 7.3 note, Step 4 finding S4-04).

## 6. Specific semantics (items 10–14)

- **D-10** keeps the upstream reason and its evidence: `PMID_ROLE_COLLISION` or `BRIDGE_ONLY_SUPPORT` is a claim
  reason and the projection basis and collision events are in the evidence set
  [verified, `test_d10_keeps_the_upstream_reason_and_evidence`].
- **Claims** carry the SPEC 7 fields; evidence is limited to the candidate's provenance (its unit, its keys'
  occurrences, its own lookups, the index identity) [verified on real data,
  `test_no_evidence_outside_the_candidates_provenance`]. No reason outside the SPEC vocabulary is emitted (the
  differential compares reason sets on every valid case).
- **Conflicts**: status `conflicting`, at least two alternatives each with evidence, routed with an open question
  (W-8) [verified, `test_identity_conflict_claim_shape`, `test_contradiction_in_sources_has_type_alternatives`, real
  Obokata].
- **NOT_FOUND** only from a valid `no_record` with checked sources; unavailable, coverage gap, unresolved identifier
  and identity conflict never become `NOT_FOUND_IN_CHECKED_SOURCES` or positive [verified, `test_never_not_found`,
  `test_not_found_needs_a_valid_no_record_lookup_with_checked_sources`, `test_a_notice_is_never_positive`].
- **D-13** adds `LOOKUP_EVIDENCE_LIMIT_EXCEEDED` only when an unavailable lookup was refused by the D-048 budget
  (`test_unavailable_carries_the_budget_reason_only_when_budget_refused`).

## 7. Differential against the frozen Step 4 model (item 15)

`differential.py` decides every case of the Step 4 domain through the production parser and table
(`concretize` → `lookup_view` → `candidate_view` → `dt1.decide`) and compares it with the frozen oracle table
(`simulations/stage04/oracle`, read only; every file checked against its MANIFEST, and the MANIFEST against the pinned
SHA-256 `411050772807…3e27735`). Compared fields: rule, class, status, value, disposition, question kind, reason codes
(model placeholders in production names, D-043) and failure code.

| Domain | Cases | Mismatches | Time |
|---|---|---|---|
| **valid** (Stage 02/03 can produce it; the owner's acceptance set) | **244,884** | **0** | 34.3 s (4 workers), after the review fixes (`differential.json`) |
| invalid (`--all`) | 12,387,564 | 26,384 | 1,253 s (`differential_all.json`) |

Valid rules covered: D-1 81,628, D-2 81,628, D-3 1, D-4 3, D-6 16,040, D-7 21,584, D-8 38,500, D-9 2, D-10 2,933,
D-11 419, D-12 13, D-13 660, D-14 1,456, D-15 9, D-16 8. D-5 and D-17 cannot occur on valid cases and are tested on
SYNTHETIC impossible inputs (section 4) and in the invalid domain (D-5 4,067,784, D-17 2,223 oracle decisions, all
matched except the classes below). [limit] The differential exercises the decision, not the detector's evidence and
alternative construction (that is where review finding F1 was); those are covered by the tests of sections 5–9.

**Every invalid-domain discrepancy is an abstraction mismatch** (none is a production defect, a reference-model
defect or a correction needing the owner; the oracle is unchanged):

| Kind (`mismatches_by_kind`) | Cases | Why |
|---|---|---|
| `WITNESS_WITHOUT_PAIR`: oracle D-5, production D-7 to D-17 or D-8 | 11,008 | The model's witness bits on a single-key shape. For a DOI-only or PMID-only candidate there is no other key, so an event naming another identifier is an ordinary record; `concretize` cannot express a "witness" there, and production decides the matching valid case. |
| `SIGNATURE_UNREACHABLE` (alone or with `INVALID_QUERY_FOR_VALID_KEY` / `PROJECTION_OUTSIDE_CONTRACT`): same rule D-1 or D-2, reasons differ by `PAIR_UNCORROBORATED` | 15,376 | An event bit (witness or co-naming) on an unavailable or invalid Q2. Stage 02 gives no events there, so the concrete observation carries none; production's κ is `UNDETERMINED` where the model's bit gives another κ. D-1 and D-2 precede D-5, so only the κ-derived reason differs. [verified on a random sample covering 5 of these 8 sub-kinds; `differential_all.json` lists all 22 kinds with counts] |

## 8. Mutation testing (item 16)

`mutants.py --differential` → `mutants.json`. Each mutant is a textual change to a copy of `src/` placed first on
`PYTHONPATH` (a probe checks the copy is the module under test); the three Step 9 suites and the valid differential
run against it. **Runner defect found and fixed in Step 9**: the first runner copied `src/` without the `schemas/`
directory the package resolves beside it, so every suite errored on every mutant and "caught" meant nothing; the copy
now mirrors the layout, and an unmutated **control** run must pass every suite and the differential before any mutant
counts (it passed).

| Mutant | Caught by |
|---|---|
| M01 D-14 before identity conflict | detector tests, real tests, differential |
| M02 D-13 after positive | detector tests, differential |
| M03 remove D-6 | detector tests, real tests, differential |
| M04 remove D-17 | detector tests |
| M05 notice becomes positive | detector tests, real tests, differential |
| M06 no-record becomes retracted | detector, B-8 and real tests, differential |
| M07 unavailable becomes no-record (adapter) | detector tests, differential |
| M08 ignore taint | detector tests, real tests, differential |
| M09 ignore bridge-only | detector tests, differential |
| M10 allow an ambiguous DOI-only query | detector tests |
| M11 ignore the κ/Q2 disagreement | detector tests, real tests |
| M12 NEEDS_RESOLUTION becomes normal completion | detector tests, real tests, differential |
| M13 collapse the two B-8 candidate evidence items | B-8 tests |
| X01 (extra) D-7 alternatives from conflict groups only (review F1) | detector tests |
| X02 (extra) NOT_FOUND without checked sources (review F4) | detector tests |

**13 of 13 owner mutants caught; 15 of 15 with the two extra.** The reviewer also ran 16 further mutants of its own
against the detector tests; all were caught by assertion failures, not errors.

## 9. Real regressions (items 7, 18)

CI tests, real Stage 03 bundles, real Stage 02 code, attributed Retraction Watch subsets, every socket refused
(`tests/stage04/test_step9_real.py`, `test_step9_b8.py`) [verified]:

| Case | Index | Result |
|---|---|---|
| VS-2 ar Obokata 76190003, `nature12969` + PMID `24476881` | Step 8 subset | `IDENTITY_CONFLICT`, rule D-6, status `conflicting`, coherence `INCOMPATIBLE`, reason `IDENTITY_WITNESSED`; alternatives: DOI side work `{doi: nature12969, pmid: 24476891}`, PMID side work `{doi: null, pmid: 24476881}`; both identifier occurrences, the unit span hash, both Q1 lookups, Q2 and the witness event (`original_pmid = 24476891`) in the evidence; decision `ROUTE_NEEDS_RESOLUTION`, one open `identity_conflict` question, lifecycle `NEEDS_RESOLUTION`; no other claim for the candidate |
| VS-2 ar Obokata, `nature12968` + `24476887` | Step 8 subset | `RETRACTED_WORK_CITED` (D-14), `COHERENT`, EV-2 value at the supporting pointer |
| VS-2 replay | Step 8 subset | a second investigation gives the same claim ids, evidence ids and question ids |
| VS-3 en Obokata 1372543632 | Step 8 subset | both works `RETRACTED_WORK_CITED`, `COHERENT`, lifecycle `COMPLETED` |
| VS-1 MMR 1381772671 | Step 8 subset | Wakefield `RETRACTED_WORK_CITED`; Lancet notice `NOTICE_CITED` (`uncertain`, null, `CITED_IDENTIFIER_IS_NOTICE`); the only verified fact is Wakefield |
| P2 on real data (Obokata Q2 flipped to `matched` by a defective adapter) | Step 8 subset | DETECT `ADAPTER_INCONSISTENT` (D-5, `KAPPA_Q2_DISAGREE`), no claim, `FAILED` |
| B-8 unit, en 1379214029 | Step 8 subset | section 2 |
| VS-5 BCAS3, ar 76488293 | Step 9 subset | both citing units `RETRACTED_WORK_CITED` (D-14), no reasons; `PMID_ROLE_COLLISION` is on all three lookups; in Q1(PMID) it names a PMID-matched event, in Q1(DOI) and Q2 a DOI-matched event, so D-10 does not hold on L = Q2 (section 13, A-2) |
| VS-4 expression of concern, en 1360148888 | Step 9 subset | one `CONCERN_CITED` (D-14, `expression_of_concern`), no `RETRACTED_WORK_CITED` |
| tainted unit, ar 74891699 | Step 9 subset | DOI `10.1002/14651858.cd000243.pub2` is a retracted record but its unit holds a malformed identifier: `UNRESOLVED_IDENTIFIER` (D-8, `IDENTIFIER_MALFORMED`); the clean pub3 + PMID unit is `RETRACTED_WORK_CITED` |

Step 9 subset (`tests/stage04/fixtures/step9/rw_subset.csv`, manifest beside it): 6 real records with selected
fields, selected from the pinned snapshot by the Step 8 selection script with the new `--bundle` option (the Step 8
default run reproduces the Step 8 fixture byte for byte; only the manifest's method text and a new `selection` field
differ) [verified]; all 277 queries of the three bundles give the same answer on it as on the full index
(`subset_equals_full_index: true`, 0 disagreements); 0 synthetic rows.

Real classes. Reached on real data (CI or the development measurements): `NO_IDENTIFIER`,
`NOT_FOUND_IN_CHECKED_SOURCES` (real no-record), `UNUSED_DEFINITION`, `UNRESOLVED_IDENTIFIER`,
`RETRACTED_WORK_CITED`, `CONCERN_CITED`, `NOTICE_CITED` (real notice-only), `IDENTITY_CONFLICT` (real identity
conflict): 8 of 15. **Absent from all real data available to Step 9**: `CORRECTION_CITED`,
`REINSTATED_WORK_CITED`, `CONTRADICTION_IN_SOURCES`, `UNRESOLVED_IDENTITY`, `UNRESOLVED_STATUS`,
`LOOKUP_UNAVAILABLE`, `UNRESOLVED_USE`. They are executed only on SYNTHETIC inputs (section 5);
`CONTRADICTION_IN_SOURCES` also on real Stage 02 code with SYNTHETIC rows (section 14, F1).

## 10. Development measurements on the 232 exposed revisions (item 17)

`dev_measurements.py` → `dev_measurements.json`. **DEVELOPMENT EVIDENCE ONLY** (design-exposed revisions, owner
decision D-5): no precision, no recall, no evaluation frame, no tuning; no rule, reason or threshold changed after
these numbers were seen. Full pinned index (`rw-2f116e9ffed718e6.sqlite`, SHA-256
`b3fa48caf8cd9ae75f2701a5a2f708c7696c169d16646a5a34f967dc125cbd21`, built from the verified pinned CSV); 257 bundle
directories, 232 distinct revisions (one bundle each, a complete capture first); 0 network attempts.

- Lifecycle: 230 `COMPLETED`, 1 `NEEDS_RESOLUTION` (ar Obokata), 1 `FAILED` (en 1380218630, ACQUIRE
  `BUNDLE_ARTIFACT_MISSING`: the retained holdout bundle `confirmation-d035/.../holdout/en-614753-a1` keeps only its
  failure artifact, not the source and render its manifest names; an inherited Stage 03 retention fact, section 13).
- 4,614 candidates, 4,614 claims (one per candidate). By class: `NO_IDENTIFIER` 3,452; `NOT_FOUND_IN_CHECKED_SOURCES`
  1,094; `UNUSED_DEFINITION` 25; `UNRESOLVED_IDENTIFIER` 17 (D-4 13, D-8 4); `RETRACTED_WORK_CITED` 15;
  `CONCERN_CITED` 5; `NOTICE_CITED` 5; `IDENTITY_CONFLICT` 1. No D-5, D-7, D-9 to D-13 or D-17.
- Lookups (distinct per revision): `no_record` 1,991, `matched` 49, `notice_only` 40, `ambiguous_identity` 1; none
  unavailable. `PAIR_UNCORROBORATED` 460 (pairs without co-naming events, almost all `no_record`).
- Revisions with a positive claim: 15. Multi-candidate units (`CO_REPORTED_MULTIPLE`): 3 (the B-8 unit, and two in
  ar 76436758).
- Identifier occurrences by role and Q1 state (the planning probe's unit of count): `notice_only` 43 (32
  `marker_target`, 10 `primary_citation_field`, 1 `identifier_link`); `matched` 41 (31 retracted, 10 expression of
  concern, one of them a `marker_target`). These reproduce the planning probe's figures (STAGE04_MASTER_EXECUTION_PACKAGE
  2.3) exactly [verified].

## 11. Naive baseline (item 19)

The plan's baseline: flag a unit if any key appears in any Retraction Watch identifier column (a Q1 answer other than
`no_record`). On the 232 revisions it flags 27 units; the engine's classes for them (development evidence, no
ground truth):

| Engine class of the flagged unit | Units | What the naive flag would say |
|---|---|---|
| `RETRACTED_WORK_CITED` | 15 | agrees (an attachment) |
| `CONCERN_CITED` | 5 | an attachment; it does not separate an expression of concern from a retraction |
| `NOTICE_CITED` | 5 | **a notice treated as an attachment** to the retracted work |
| `IDENTITY_CONFLICT` | 1 | **an attachment through a contradicted identity** (ar Obokata: the DOI's record names PMID 24476891, the citation PMID 24476881) |
| `UNRESOLVED_IDENTIFIER` | 1 | **an attachment where the engine abstains** (ar 74891699: a malformed identifier in the unit) |

Counting keys of observation roles as well changes nothing at unit level. At occurrence level (any role, the probe's
count) the naive lookup would also count the **32 `marker_target` notice occurrences and 1 marker matched to an
expression of concern**, which the engine never makes candidates (S-6.7). Abstentions of the engine: 17
`UNRESOLVED_IDENTIFIER` and 1 `IDENTITY_CONFLICT` route; `NOT_FOUND_IN_CHECKED_SOURCES` is never a negative.
[limit] Whether any of these is right or wrong is not measured here; only the holdout measures it (plan section 13).

## 12. Originality review: the Verifiable Citation Verdict (item 20)

Compared with a DOI-only lookup (query the cited DOI alone; report "retracted" when Retraction Watch has it):

| Property | DOI-only lookup | Verifiable Citation Verdict (Step 9, measured or tested) |
|---|---|---|
| Notice cited instead of the work | reported as a retracted citation (11 notice occurrences in citation roles, 32 in markers, on the dev set) | `NOTICE_CITED`, never positive (D-15; `test_a_notice_is_never_positive`; MMR and GFAJ-1 real) |
| Two identifiers of one citation disagree | invisible: the DOI alone is "retracted" | pair query and κ: `IDENTITY_CONFLICT` with both alternatives, routed with a question (ar Obokata real) |
| Type of the record | one flag | `RETRACTED_WORK_CITED` / `CONCERN_CITED` / `CORRECTION_CITED` / `REINSTATED_WORK_CITED`; source type conflicts are `CONTRADICTION_IN_SOURCES` |
| Unsafe identifier in the unit | ignored | abstention (`UNRESOLVED_IDENTIFIER`, real ar 74891699) |
| Absence | "not retracted" | `NOT_FOUND_IN_CHECKED_SOURCES`, scoped to the named checked sources, never a negative; unavailable, coverage gaps and conflicts never become it (`test_never_not_found`) |
| Why | none | the rule that fired, reasons, upstream Stage 02 reasons, an evidence set from the candidate's own provenance only (`test_no_evidence_outside_the_candidates_provenance`) |
| Reproducibility | live query | offline, deterministic; replay gives the same claim, evidence and question ids (`test_ar_obokata_replay_gives_the_same_ids`) |

**No global novelty claim.** The mechanism is a composition of known parts (first-match decision tables, Retraction
Watch matching, content addressing). The plan's prior-art list (Retraction Tracker for Wikipedia from Stage 01's
record, RetractionBot, Zotero's Retraction Watch integration, Crossmark) was **not re-read in Step 9**; the
primary-page prior-art check stays with the 04-J creative-differentiation review. All numbers above are development
evidence on design-exposed data, not evidence for the contribution; only the holdout measures it.

## 13. Inherited-baseline audit (item 21)

No Stage 00–03 file and no oracle file is changed [verified, `git diff 8b623cd -- src/citerift/wiki
src/citerift/retraction src/citerift/contracts src/citerift/governance schemas .github simulations pyproject.toml
uv.lock docs/verification/stage-00 … stage-03` is empty].

| # | Finding (verified) | Class | Handling |
|---|---|---|---|
| A-1 | Stage 02 `_finish` reports `PMID_ROLE_COLLISION` for any events flagged `NOTICE_PMID_EQUALS_ORIGINAL`, whatever the lookup's state and whichever key matched the event. | Stage 02 property, correct. | D-10 reads only L and only an event matched by PMID (SPEC D-10); the issue stays in the `/result` evidence of every lookup. |
| A-2 | Planning probe: "BCAS3: `PMID_ROLE_COLLISION` on the cited original". True of Q1(PMID); in Q2 the named event (a correction, ev-0056322) is matched by DOI. | Planning text, accurate but incomplete. | D-14 as specified; VS-5's "carried" is open (section 17, OD-S9-2). Real regression added. |
| A-3 | The retained Stage 03 holdout bundle `en-614753-a1` keeps 1 of the artifacts its `capture.json` names (only the failure artifact). | Inherited Stage 03 retention fact. | ACQUIRE fails `BUNDLE_ARTIFACT_MISSING`; nothing is decided; no Stage 03 change. |
| A-4 | SPEC 7.4 "a notice DOI paired with the original's PMID is a witness of incompatibility → D-6" holds only when Retraction Watch records the original's DOI (the witness definition S-6.10 needs `original_doi ≠ d`). Otherwise κ is `UNDETERMINED` and D-14 gives `RETRACTED_WORK_CITED` with `KEY_RESULTS_DIFFER` and `PAIR_UNCORROBORATED` (review F2). | Stage 04 SPEC inconsistency (summary row vs formal rule); the frozen model and production agree with the formal rule. | Not changed: a dt-1 semantics change is the owner's (section 17, OD-S9-1). Not observed in the dev data (`KEY_RESULTS_DIFFER` occurs once, on Obokata). |
| A-5 | MM EV-2 says the claimed value is "the value at the supporting pointer"; the supporting pointer is `/result/projection/retraction_status` (an object holding `value`), and the coherence item is at `/query` with κ as its derived value (review F7). | Stage 04 MM wording. | Items carry derived values, as NORMALIZE's do; the tests read `status["value"]`. Wording left for the Step 12 freeze review (section 17). |
| A-6 | `STAGE04_IDENTITY` names `engine_version` (package version) and `table_version: dt-1`; the detector identity is recorded in the DETECT output. A detector change without a version change shows as a DETECT replay mismatch at VERIFY, not as `STALE`. | Stage 04 design property. | Forward item for the Step 12 freeze (bump the engine version at freeze). |
| A-7 | Step 8 integration tests still run the SYNTHETIC test detector. | Step 8 design (they test the adapters). | Kept; the production detector runs on the same bundles in the Step 9 tests. |
| A-8 | Planning probe counted 255 bundle directories; the repository now holds 257 (same 232 revisions). | Count drift from later retained bundles. | Recorded; the measurement uses the measured set. |
| A-9 | The Step 4 model has no Crossref assertion in a conflict group (its abstraction has event types only); real Stage 02 can put one there. | Model abstraction, not a model defect for the decision (D-7 fires the same). | The defect it hid was in Step 9's evidence construction (review F1), fixed and tested on real Stage 02 code. |

## 14. Independent adversarial review (item 22)

A fresh-context reviewer (a separate agent with no prior context; read-only on the repository) reviewed precedence,
D-5, D-6, D-7, D-10, D-13 to D-17, evidence sufficiency, the B-8 fix, claim identity, the differential harness, the
mutation runner and the Obokata cases against SPEC, MM, the frozen model and real Stage 02 code. Findings and
handling:

| # | Finding | Verdict | Handling |
|---|---|---|---|
| F1 | HIGH. A D-7 conflict whose group holds a Crossref assertion (`cr-…`, real Stage 02 `policy`/`query`) made `type_alternatives` raise: DETECT failed the whole investigation on contract-valid input. | Confirmed (reproduced on real Stage 02 code). | **Fixed.** D-7 alternatives are Stage 02's own `retraction_status.alternatives` (one per type, sorted), each supported by its item at `/result/projection/retraction_status/alternatives/i` and the Retraction Watch events of its type. Fail-first: the new test fails on the previous detector with the reviewer's error. Test `test_a_crossref_assertion_in_a_conflict_is_an_alternative_not_a_failure`; mutant X01. |
| F2 | A PAIR of a notice DOI and the original's PMID, where Retraction Watch records no original DOI, gives `RETRACTED_WORK_CITED` (κ `UNDETERMINED`), while SPEC 7.4 says such a pair is a witness → D-6. | Confirmed; spec inconsistency, code follows the formal rule and the frozen model. | Not changed; owner decision OD-S9-1 (section 17); audit A-4. |
| F3 | BCAS3: D-14 is as specified; VS-5's "`PMID_ROLE_COLLISION` carried" is met only in the evidence (`/result` items), not in the claim's reasons. | Confirmed; spec ambiguity. | Real regression added; owner decision OD-S9-2. |
| F4 | `NOT_FOUND_IN_CHECKED_SOURCES` did not check that checked sources are named; a test name and the closure claimed more. | Confirmed. | **Fixed (narrow):** D-16 fails DETECT closed (`ADAPTER_INCONSISTENT`) unless the deciding lookup names at least one checked source; test extended; mutant X02. Real Stage 02 always names them. |
| F5 | With one Q1 unavailable and Q2 available, the side used Q2's events and not the witness field S-7.3 names. | Confirmed (deviation from the wording). | **Fixed:** the side always carries the witness field, with Q2's events beside it; test added. |
| F6 | Differential limits: no evidence construction, no D-5/D-17 in the valid domain, the MANIFEST digest printed but not pinned; invalid-domain mismatches need labels. | Confirmed. | Digest pinned in `differential.py`; mismatches classified by kind (section 7); limits stated. |
| F7 | EV-2 read literally (value at the pointer vs derived values). | Spec ambiguity. | Audit A-5; Step 12 freeze review. |
| F8 | Mutation runner: "caught" counted any non-zero exit. | Confirmed, and worse than stated: every suite errored (section 8). | **Fixed** with the layout mirror and the control run; mutants re-run. |

Checked and found correct by the reviewer: rule order and every guard's projection form; κ over available direct
events; every D-5 condition incl. P2; D-5/D-17 commit no claim; D-6 shape and W-8 routing; claim identity and one
claim per candidate; B-8 injectivity across every evidence kind the detector emits; replay with a reversed lookup plan;
no clock, randomness, network or model.

## 15. Runtime and CI (item 23)

- **Step 9 tests alone** (3 modules, 57 tests): **33.3 s** locally (Python 3.12.3, 4 vCPU). Slowest: the MMR module
  fixture 4.1 s, the 206-representative sweep fixture 3.4 s, the Obokata module fixture 1.6 s, the Obokata replay
  1.5 s. No exhaustive suite is duplicated in CI: the 244,884-case differential, the invalid domain, the mutation runner
  and the 232-revision measurements are scripts under `review/step9/`, not tests.
- **Full suite locally**, 3.12.3 and 3.13.18 run at the same time on one 4-vCPU machine (working tree before the final
  commit): **3,035 passed, 0 skipped** on each; 3.12: 12 min 8 s, 3.13: 11 min 21 s (Step 8: 2,978 tests, 15 min 7 s
  and 14 min 29 s on the same kind of machine). Slowest tests are all pre-existing:
  `test_d047_report_with_50000_projections` 37.3 s, the two Stage 00 differential simulations 24.4 s and 23.6 s,
  `test_d047_claim_over_50000_evidence_ids…` 23.2 s, `test_crash_at_every_occurrence_of_every_controller_boundary`
  17.3 s; the slowest Step 9 item is the MMR fixture, 4.2 s.
- **GitHub CI**: CI_PENDING
- Other runs: valid differential 34–45 s (4 workers); invalid domain 1,253 s; mutation runner with the differential
  885 s (control plus 15 mutants); development measurements 725–755 s.

## 16. Exit criteria (item 26)

| # | Criterion | Status and evidence |
|---|---|---|
| 1 | B-8 fail-first | PASS. Section 2, real unit, equal ids for different facts. |
| 2 | Evidence identity safe or corrected | PASS. Pointer placement, injectivity proof (MM 4.6), `_Items` guard; D-051 unchanged. |
| 3 | dt-1 detector | PASS. `dt1.py`, `adapters/detector.py`, default detector. |
| 4 | κ | PASS. Section 4. |
| 5 | Precedence | PASS. Section 3; mutants M01, M02. |
| 6 | All 15 classes | PASS. Section 5 (synthetic); 8 real (section 9). |
| 7 | D-5 fail-closed | PASS. κ variants, P2 tests, real P2; no claim committed. |
| 8 | D-17 gap | PASS. `test_d17_is_the_gap_for_a_malformed_deciding_lookup`; M04. |
| 9 | P2 | PASS. Section 4. |
| 10 | Obokata conflict | PASS. Section 9. |
| 11 | Obokata positive | PASS. Section 9. |
| 12 | MMR | PASS. Section 9. |
| 13 | Notice never positive | PASS. `test_a_notice_is_never_positive`; M05; MMR real. |
| 14 | Unavailable never NOT_FOUND or positive | PASS. `test_never_not_found`; M07. |
| 15 | NOT_FOUND semantics | PASS. Section 6, incl. the checked-source guard (F4). |
| 16 | W-8 | PASS. Conflicts route with a question; M12. |
| 17 | Differential matches | PASS. 244,884 valid, 0 mismatches; invalid domain classified (section 7). |
| 18 | All mutants caught | PASS. 13/13 (15/15 with extras), control passes. |
| 19 | Replay ids | PASS. Obokata and B-8 replay tests. |
| 20 | No network, randomness or model | PASS. Banned-import test; every socket refused in the real tests; 0 network attempts in the measurements. |
| 21 | 232 measurement retained | PASS. `dev_measurements.json` (section 10). |
| 22 | No evaluation/holdout exposure | PASS. Only design-exposed data (D-5); no evaluation frame drawn or read; the frozen evaluation and holdout plan unchanged. |
| 23 | Creative review | PASS with limit. Section 12; prior-art pages not re-read (04-J). |
| 24 | Audit | PASS. Section 13. |
| 25 | Reviewer findings resolved | PASS. F1, F4, F5, F6, F8 fixed; F2, F3 owner decisions; F7 forward. |
| 26 | Oracle frozen | PASS. `git diff 8b623cd -- simulations/` empty; MANIFEST digest pinned and checked. |
| 27 | 3.12 and 3.13 pass | PASS locally (3,035 each); CI: CI_PENDING |
| 28 | Zero skips | PASS locally (0 skipped); `check-report` on the committed tree: CI_PENDING |
| 29 | ruff | PASS. |
| 30 | format | PASS (521 files). |
| 31 | mypy | PASS (88 source files, no issues). |
| 32 | pip-audit | PASS. "No known vulnerabilities found" (locked export, `--require-hashes`); no dependency change. |
| 33 | Schemas | PASS. `check-schemas` 0 problems; no schema changed. |
| 34 | Step 3 checker | PASS (0 failed). |
| 35 | gov check 0/0 | PASS. 0 errors, 0 warnings. |
| 36 | render-status | PASS (`PROJECT_STATUS.md is up to date`). |
| 37 | CI green within the runtime boundary | CI_PENDING |

## 17. Owner decisions and carry-forward

**Open owner decisions (Step 9 did not decide them):**

- **OD-S9-1 (review F2, audit A-4).** A citation pairing a retraction notice's DOI with the original's PMID, when
  Retraction Watch records no DOI for the original: Q1(DOI) is `notice_only`, Q1(PMID) and Q2 are `matched`
  `retracted`, there is no witness (S-6.10 needs `original_doi ≠ d`), so dt-1 gives `RETRACTED_WORK_CITED` with
  `KEY_RESULTS_DIFFER` and `PAIR_UNCORROBORATED`. SPEC 7.4's summary row says such a pair is a witness → D-6.
  Options: (a) keep dt-1 and the frozen model, and correct the SPEC 7.4 row to "when Retraction Watch records the
  original's DOI; otherwise D-14 with `KEY_RESULTS_DIFFER`"; (b) make a `notice_only` Q1 in a PAIR an abstention
  (a dt-1 change: model, oracle and differential change, a new table version). **Recommendation: (a)**, because the
  PMID does name the retracted original and the claim already flags that the keys disagree; not observed in the 232
  revisions.
- **OD-S9-2 (review F3, VS-5).** "`PMID_ROLE_COLLISION` carried" for BCAS3: today it is carried in the claim's
  evidence (the `/result` items of all three lookups), not as a reason, because D-10 reads only L's PMID-matched
  events and no other rule names the code. Options: (a) evidence-level carrying satisfies VS-5; (b) add a
  non-deciding reason for a collision on any lookup of the candidate (a dt-1 reason change: model and oracle
  reasons). **Recommendation: (a)**, to be confirmed at the vertical-slice acceptance (not Step 9).
- **B-8 acknowledgement.** D-051 is unchanged; the resolution is where DETECT places the candidate-scoped evidence
  (section 2). No owner decision is recorded for it; the owner may want to acknowledge the reading.

**Carried forward (not Step 9 scope):** bump the engine version at the Step 12 freeze so a detector change is a
`STALE` input, not only a replay mismatch (A-6); state EV-2 for derived values in MM 4.6 (A-5); the absent real
classes (section 9) stay untested on real data until a source provides them; the prior-art primary-page check goes to
the 04-J creative review (section 12).

## 18. Changes to existing files (disclosed)

- `adapters/detect.py`: `DetectFailure`; the no-detector message names dt-1. `adapters/plan.py`: the production
  detector is the default.
- `tests/stage04/test_step8_integration.py`: the no-detector test passes `Integration(detector=None)` explicitly
  (the default is now dt-1) and checks the message names dt-1.
- `docs/verification/stage-04/scripts/step8_rw_subset.py`: a `--bundle` option (repeatable) and a `selection` field in
  the manifest; the default run reproduces the Step 8 fixture CSV byte for byte [verified]. The Step 8 fixture is
  unchanged.
- SPEC 4.3 and MM 4.6: the B-8 paragraphs (section 2). No other SPEC, MM or RA text changed.
No Stage 00–03 file, no schema, no `.github/` file and no governance code is changed.
