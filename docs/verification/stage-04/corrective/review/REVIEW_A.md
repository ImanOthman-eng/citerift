# Corrective cycle review A: scientific semantics of dt-1 → dt-2

Reviewer A (scientific semantics), written under `REVIEW_BRIEF.md`. I did not write the correction. Working tree on
top of `f207bc0`; I modified nothing except this file.

## Scope read

- Owner instruction: `DECISIONS.md` D-071 (lines 1612-1641); D-058 (lines 1286-1309) for the earlier owner decision on
  the mirror case.
- Production: `src/citerift/investigation/dt1.py` (full file, diff against `f207bc0`), `adapters/detector.py` (diff
  and claim support construction, lines 270-312), `explanations.py`, `__init__.py`, `adapters/plan.py`.
- Stage 02 semantics the rule depends on: `src/citerift/retraction/ingest.py` (`dispose`, `finalize_events`),
  `src/citerift/retraction/query.py` (`gather`, `_finish`, `render`).
- Written rule: `SPECIFICATION.md` 7.3 (D-10) and 7.3a; `MATHEMATICAL_MODEL.md` D-10 and `rc(c)`;
  `RISK_ANALYSIS.md` R4-04 diff; `corrective/ROOT_CAUSE.md`; `corrective/census/CENSUS.json` (summarised in ROOT_CAUSE).
- Reference model and oracle: `simulations/stage04/dt2_reference.py`, `decision_space_dt2.py`, `oracle-dt2/MANIFEST.json`,
  `corrective/simulation/decision_space_dt2_summary.json`, the frozen `simulation/decision_space_summary.json`.
- Tests: `tests/stage04/test_corrective_role_collision.py`, `test_corrective_oracle.py`, the `step9_support.py` diff
  (concretization of `rc`).

## Method

1. Read the diff line by line against D-071 §3-5 and SPEC 7.3a / MM `rc(c)`.
2. Traced every way Stage 02 builds a matched lookup (direct, `query_pair`, `pmid_cooccurrence`, `doi_cooccurrence`) to
   see which keys can attach an event, so as to find inputs where a collided key can still reach D-14 or D-15.
3. Ran the two corrective test files (allowed targeted commands):
   `uv run pytest tests/stage04/test_corrective_role_collision.py -q -p no:cacheprovider` → `49 passed in 2.81s`;
   `uv run pytest tests/stage04/test_corrective_oracle.py -q -p no:cacheprovider` → `20 passed in 14.66s`.
4. Small read-only probes (scripts in my scratchpad, not in the repository): SQL on the pinned index
   (`mode=ro`), and the production `dt1.decide` on hand-built `Candidate`s and on real observations from
   `adapters.lookup.observe` against the pinned index.

Where I say "verified" it comes from code I read or a command I ran. Where I say "inference", it is reasoning that I
did not test on data.

## Verified facts (no finding)

- **The failure is closed.** The production path on the pinned index:
  `DOI 10.1002/asi.23238 -> D-10 UNRESOLVED_IDENTITY ('IDENTIFIER_ROLE_COLLISION',)`, deciding lookup `matched/vf`,
  `role_ambiguous = ('ev-0033558',)`. The record has no PMIDs (`original_pmid`/`notice_pmid` null), so no second key
  could resolve it.
- **dt-2 equals dt-1 where nothing is role-ambiguous, in production.** The only semantic edits are the extra disjunct
  `bool(role_ambiguous(x.c))` in `_d10` (dt1.py:387-394) and the reason added under `set(role_ambiguous(c)) -
  set(L.collision)` (dt1.py:465-466). With `role_ambiguous(c) == ()`, both are no-ops. The new `Event.flags` and
  `Lookup.notice_hits` fields are read nowhere else.
- **Precedence is kept.** D-10 is still tier 5, after D-5 to D-9 and before D-11 to D-16. In the abstract domain, the
  valid `rc` cases that change are exactly 5,028 (= `RC_EFFECT` checked): 2,933 D-10 (reason added), 1,456 D-14,
  419 D-11 and 220 D-13 (PAIR with a Q1 unavailable). All of them become D-10 (summary `rules`: `no_rc|valid|D-13`
  660 vs `rc|valid|D-13` 440, and no `rc|valid|D-14` or `rc|valid|D-11`). Moving cases from D-13 to D-10 follows the
  order "unresolved before operational failure". `RC_PRECEDENCE` holds on all 12,632,448 `rc=True` cases with 0
  violations, so no D-1 to D-9 outcome changes.
- **NOTICE_CITED.** D-15 needs `L.state = notice_only`, and Stage 02 gives `notice_only` only when no event has the
  key as original (query.py `elif notices:` branch). A same-record collision nulls the notice field (ingest.py
  `nd = None`), so the key is matched. A cross-record collision has an original event, so it is matched too. A
  collision therefore cannot produce `NOTICE_CITED` (also `RC_NO_NOTICE_FROM_COLLISION`, 0 violations).
- **"rc = False equals dt-1" is checked over the whole table.** `EQUIVALENCE_RC_FALSE` was checked on 12,632,448 cases
  (the full frozen domain), with 0 violations. `test_rc_false_equals_the_frozen_dt1_oracle_case_for_case` compares the
  two oracle tables chunk by chunk over every chunk, after mapping decisions by full JSON equality, and it passed.
- **The abstraction is sound as a superset.** `rc` is a free bit crossed with every other abstract input. Production
  can set `role_ambiguous` only for a matched deciding lookup (dt1.py:299-301). The model treats `rc` with any other
  state as inert (`RC_INERT_UNLESS_MATCHED`, 4,737,408 checks, 0 violations). The production condition "guard
  `collision ∨ roleamb`, reason only for `roleamb \ collision`" equals the model's "guard `col ∨ rc`, `rc` = not
  covered by col". I found no production state where `rc` holds but the model treats it as impossible.
- **A new reason code was needed.** `PMID_ROLE_COLLISION` names a Stage 02 PMID-only issue, and its text says "the
  PMID". `IDENTIFIER_ROLE_UNRESOLVED` is a Stage 03 taint, so reusing it would wrongly route the claim through the
  taint chain (detector.py:285). `KEY_NAMES_SEVERAL_WORKS` and `CITED_IDENTIFIER_IS_NOTICE` assert different facts. No
  existing code fits.
- **Evidence chain.** A D-10 claim supports itself with every lookup's result evidence (which carries
  `notice_hit_count`) and every event of the deciding lookup (which carries `flags`) (detector.py:289-302). The new
  reason therefore has its chain.

## Findings

### A-01 — MEDIUM — A non-cited bridge key can resolve a collision of a cited key; SPEC 7.3a contradicts itself on this

Evidence (verified):
- `attached_keys` counts a key as attaching when it is cited **or** when it is the event's `matched_by` scheme
  (dt1.py:266-273). `role_collided` checks cross-record notices only for cited keys (dt1.py:285-291). So an event that
  carries a collided cited DOI, and that Stage 02 reached through a clean, non-cited PMID, is not role-ambiguous.
- Probe (production `dt1.decide`): DOI-only candidate `10.5555/x`. Lookup Q1(DOI) is matched/vf with a clean direct
  event e1 (original DOI `10.5555/x`) and an event e2 (`matched_by=pmid`, `linked_via=pmid_cooccurrence`, original
  DOI `10.5555/x`, original PMID `9999`, flag `NOTICE_DOI_EQUALS_ORIGINAL`):
  `bridged by non-cited pmid: D-14 RETRACTED_WORK_CITED ()`, with `attached_keys(e2) = (('doi','10.5555/x'),
  ('pmid','9999'))`. The same two events, both attached directly by DOI, give
  `D-10 UNRESOLVED_IDENTITY ('e2',)`.
- SPEC 7.3a defines attaching keys to include the `matched_by` key (line 443-444). Its next bullet says "A second,
  non-collided identifier **of the citation** naming the same event resolves the ambiguity … nothing else does"
  (lines 449-451). The code and MM `rc(c)` follow the definition; the prose says otherwise.
- Reachability (verified from Stage 02 code): `pmid_cooccurrence` admits only events with an empty `original_doi`
  (query.py:332-336). `doi_cooccurrence` admits only events whose `original_pmid != p` (query.py:357). So the current
  Stage 02 never emits this configuration, and the defect cannot fire on the pinned snapshot. Stage 04 does not check
  those Stage 02 invariants, though: `events_fit_state` checks only `matched_by ∈ {doi, pmid}` and one direct event.

Recommendation: make only cited keys able to resolve. For example, `e` is role-ambiguous when it has a cited attaching
key and all its cited attaching keys are collided, or when it has no cited attaching key and all its attaching keys
are collided. Then align SPEC 7.3a and MM `rc(c)` and add the probe above as a test. This is fail-closed and changes
nothing on Stage 02-producible input.

### A-02 — MEDIUM — The "clean second identifier" assumption is weaker than "independent evidence" claims; the owner should decide it knowing this

Evidence:
- Verified (pinned index): of 13,700 events flagged `NOTICE_DOI_EQUALS_ORIGINAL`, 1,746 carry an original PMID. 860 of
  those are also PMID-collided (both keys collided, so dt-2 abstains). That leaves **886 events where a PAIR citation
  (DOI, original PMID) is "resolved" to a positive**. Of these, **692 have no notice identifier in any scheme**
  (`notice_key` null) and 194 have a distinct notice PMID.
- Verified: the resolving PMID comes from the same Retraction Watch record that is already internally inconsistent
  (it gave one DOI in both roles). The JASIST record shows the kind of entry involved (notes "html page overwrite",
  identical dates).
- Inference (not tested on data): the DOI and PMID of a Wikipedia `{{cite journal}}` are often filled by tools that
  derive one from the other. When a notice replaced the article at the same DOI and has no PMID of its own (the 692
  case), a PMID attached to a citation of that DOI is most likely the article's PMID whichever object the editor meant.
  It then adds no information on which object is cited. In the 194 case the source does tell the two objects apart in
  the PMID scheme, so a match to the original PMID is real discriminating evidence (a notice PMID would give a witness
  and D-6).
- ROOT_CAUSE.md:129 calls the clean second key "the independent evidence that resolves which object is cited", and
  D-071 asks for "independent production evidence". The mirror of dt-1's PMID rule is a fair argument for
  consistency, but it does not show independence.

Recommendation: put the numbers above to the owner with the assumption, and offer a stricter variant. In that variant
a second key resolves only when the same record gives a distinct notice identifier in that key's scheme (the 194
case); otherwise the result is to abstain. Whatever is chosen, reword "independent" to "a second key the source
records as the original's". In the regression, report how many PAIR citations each variant resolves to a positive.

### A-03 — MEDIUM — The oracle verifies the table given `rc`, not the computation of `rc`; one claim overstates this

Evidence (verified):
- `rc` is a free input bit of `dt2_reference.Case`. All the semantic content of the correction is in
  `role_ambiguous` (attaching keys, same-record flags, cross-record hits, resolution by a second key), and the model
  does not represent any of it. The 25,264,896-case run shows only that the table handles a given `rc` correctly.
- The conformance test concretizes `rc` one way per shape (step9_support.py `role_collision_event`: a same-record DOI
  flag for DOI and PAIR, a cross-record PMID hit for PMID) and checks one representative per distinct decision.
- The computation of `rc` is tested only by `test_corrective_role_collision.py` (49 cases, 17 real-row classes).
  That suite missed A-01.
- ROOT_CAUSE.md:139-143 says "`roleamb(L)` equals the dt-1 set and dt-2 decides exactly as dt-1 (to be proved over the
  full abstract domain by the new oracle)". The oracle cannot prove the first half. SPEC 7.3a's equivalent sentence
  is accurate.

Recommendation: reword ROOT_CAUSE §4 so the oracle is credited only with the table property. Add a property or
exhaustive test of `role_ambiguous` against an independently written predicate, run over small generated Stage
02-shaped event sets: 1 to 3 events, each `matched_by`/`linked_via` combination, flags, hit counts, cited and
non-cited keys. That test would have caught A-01.

### A-04 — LOW — The cross-record check does not cover non-cited bridge keys (documented residual, small exposure)

Evidence (verified): a bridged event that is attached only through a non-cited key is checked for same-record flags
but never for cross-record notice hits (dt1.py:285-291), because Stage 04 has no lookup for that key. On the pinned
snapshot, exactly 2 PMID queries bridge (`doi_cooccurrence`) through a DOI that is another record's notice:
`3507357` and `35073579`, both through `10.1016/s1873-9946(10)00006-1` (a conference supplement DOI, original of 255
records and notice of 18). Production gives `PMID 3507357 -> D-14 CONCERN_CITED`, 255 events, `role_ambiguous = ()`.
The direct event `ev-0038168` is attached through the clean cited PMID and has the same type, so the outcome does not
rest on the bridged support. (`3507357` looks like a truncation of `35073579` in the source. That is a data error
outside this rule's scope.)

Recommendation: add this residual to SPEC 7.3a and RISK_ANALYSIS R4-04, with these two keys as the measured exposure.

### A-05 — LOW — The rule abstains on every dual role, which is stricter than "incompatible roles", and the recall cost is not yet measured

Evidence:
- Verified: 198 DOIs have one record flagged `NOTICE_DOI_EQUALS_ORIGINAL` and another record of the same DOI that
  gives it as original with a distinct notice DOI. dt-2 abstains on all of them because a single ambiguous event
  triggers D-10.
- Inference: a cross-record dual role can be compatible. A notice that is itself retracted, or a retracted item that
  is also another record's notice, is one publication object with both roles, and RETRACTED_WORK_CITED would be true
  for it. The census pairs retracted/retracted (13) and retracted/reinstated (3) suggest such cases next to data
  errors.
- ROOT_CAUSE §4 already admits the recall cost for same-record cases. RISK_ANALYSIS.md:96 says the cost is "measured
  in `corrective/regression/`", but that directory holds only `regress.py` and no results yet.

Recommendation: state in SPEC 7.3a that the implementation treats any original-and-notice dual role as incompatible
(deliberately stricter than the principle). Have the regression report the positives lost on the development
revisions, split by same-record, cross-record and "other record gives a distinct notice". Do not cite
`corrective/regression/` as a measurement until its output is committed.

### A-06 — LOW — The `IDENTIFIER_ROLE_COLLISION` explanation text is inaccurate in two reachable or fail-closed cases

Evidence (verified): explanations.py:107 says "the checked sources give **the cited identifier** both as the work and
as a notice". The reason is also attached (1) when the collided key is a non-cited bridge key
(`test_a_bridged_event_attached_through_a_collided_doi_abstains`: PMID query, collided bridged DOI) and (2) when
`notice_hit_count` is missing (`test_a_matched_deciding_lookup_without_notice_hit_evidence_fails_closed`), where the
sources state nothing.

Recommendation: change the text to something like "an identifier through which the work is attached is given by the
checked sources as both the work and a notice, or its notice role could not be excluded, and no other identifier of
the citation settles which object is cited".

### A-07 — INFO — Fail-closed treatment differs between the two inputs

`notice_hit_count` missing is read as "may be a notice" (detector.py:95-96), but a missing `flags` is read as no flags
(detector.py:54). The dataclass defaults `Lookup.notice_hits = 0` and `Event.flags = ()` are both "clean"
(dt1.py:98,120). Stage 02's lookup-result schema requires `flags`, and production builds `Lookup` only in
`lookup_view`, so neither default is reached in production. Recommendation: read a missing `flags` as unknown
(ambiguous), or document why it is safe.

### A-08 — INFO — Limits that are by design and fall outside dt-2

- A D-7 contradiction (which by design precedes D-10) can list alternatives supported by role-ambiguous events.
  Annotating that would change D-7 outcomes, which the owner's constraint forbids. Recording it is enough.
- `NOTICE_CITED` also arises where Retraction Watch left the original identifier blank (5,194 records anchored by
  source record only), and Stage 02's `notice_only` branch runs no quarantine relevance scan (0 quarantined in the
  pinned snapshot). Any change belongs to Stage 02 and needs a separate owner decision.
- Crossref assertions are 0 in the pinned index, so Crossref-side role collisions are not exercised. The rule reads
  only Retraction Watch flags and hits.

### A-09 — INFO — Reporting details of the dt-2 summary

`valid_per_shape` doubles the frozen counts (DOI 1,728 vs 864) because `rc = True` beside a non-matched deciding
lookup counts as valid, although production cannot produce it (it is inert). Five frozen properties are listed under
`not_rechecked_here`. For `rc = False` they hold through `EQUIVALENCE_RC_FALSE`. For `rc = True` they follow from
`RC_EFFECT` and `RC_INERT_UNLESS_MATCHED` (inference). Recommendation: say both in the corrective simulation note.

## Verdict

No CRITICAL or HIGH finding. On every Stage 02-producible input I traced, dt-2 implements D-071 faithfully: no
positive and no `NOTICE_CITED` from a role-collided key without a second cited key, precedence intact, and dt-1
unchanged elsewhere. Before a refreeze, fix A-01 (only cited keys may resolve) and correct the A-03 claim, and the
owner should decide the A-02 assumption with the 886/692/194 figures.
