# Corrective cycle review B: identifier and publication-object roles

Reviewer B (fresh, independent; did not write the correction). Brief: `review/REVIEW_BRIEF.md`. Date 2026-11-18.

## Scope read

- `DECISIONS.md` D-071, D-058; `corrective/ROOT_CAUSE.md`; `corrective/census/role_collision_census.py`, `CENSUS.json`.
- `git diff f207bc0` of `src/citerift/investigation/dt1.py`, `adapters/detector.py`, `adapters/plan.py`,
  `adapters/detect.py`; `dt1.py` in full; `adapters/lookup.py` (`observe`).
- SPEC 7.3 (D-10) and 7.3a; MM D-10 / `rc(c)`; RISK_ANALYSIS R4-04 (diff); `simulations/stage04/dt2_reference.py`
  (header), `corrective/simulation/decision_space_dt2_summary.json`.
- Stage 02 (read only): `retraction/ingest.py` (`dispose`, `finalize_events`), `retraction/query.py` (`gather`,
  `_finish`, `render`, `public_event`), `retraction/identifiers.py` (`normalize_doi`, `normalize_pmid`),
  `retraction/policy.py` (bridged evidence), `schemas/retraction/v1/lookup-result.schema.json`,
  `schemas/investigation/v1/lookup-observation.schema.json`, `wiki/identifiers.py` (normalizer import).
- `tests/stage04/test_corrective_role_collision.py` and its fixture manifest.

## Method

- Pinned index `rw-2f116e9ffed718e6.sqlite` opened read-only (`mode=ro`); no network; nothing in the repository
  changed except this file.
- Probes (scratchpad `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/`, not committed): `probe1.py` decides one citation through the production path
  (`adapters.lookup.observe` with the default budget → `adapters.detector.lookup_view` → `dt1.decide`), shapes DOI,
  PMID, PAIR, built as in `test_corrective_role_collision.real_decide`. `probe2.py` sweeps every identifier the
  `ident` table gives in both roles (single-key citation) and every original (DOI, PMID) pair of an event where either
  key has a notice role anywhere (PAIR citation). `probe7.py` sweeps all 31,756 original pairs of the index with the
  current `role_collided` and with a key-level variant. `probe3.py` checks normalizer idempotence; `probe4.py`
  synthetic edges using the test module's builders; `probe6.py` re-runs the 17 fixture classes on the full index.
- Targeted test run: `uv run pytest tests/stage04/test_corrective_role_collision.py -q -p no:cacheprovider` →
  `49 passed in 2.46s`.

"Verified" below means reproduced by a command on the pinned index or the code; "inference" is marked.

## Findings

### B-01 — CRITICAL — A PAIR whose two keys are each a notice identifier (in two different records) is still positive

Verified. `role_collided` (`dt1.py:285-291`) reads the same-record flag only on the event being judged
(`SAME_RECORD_FLAG[scheme] in e.flags`, line 288), and the cross-record test reads `notice_hit_count` of the key's Q1
(`dt1.py:276-282`). Stage 02 nulls a same-record notice field (`ingest.py:99-104`), so another record's same-record
notice role of a key is counted by neither: not by `notice_hit_count` (`query.py:298`, built from `notice_doi` /
`notice_pmid`, which are null for that record) and not by the flag (it sits on the other event). In a PAIR, each event
can then be "resolved" by a key that the other event's record gives as its notice identifier.

Real rows (Diabetes & Metabolism, one work, two records):

| event | record | type | original DOI / PMID | flag |
|---|---|---|---|---|
| `ev-0054788` | 18792 | retracted | `10.1016/j.diabet.2013.06.003` / `24076359` | `NOTICE_DOI_EQUALS_ORIGINAL` (RetractionDOI = OriginalPaperDOI) |
| `ev-0054787` | 18793 | correction | `10.1016/j.diabet.2013.06.003` / `24076359` | `NOTICE_PMID_EQUALS_ORIGINAL` (RetractionPubMedID = OriginalPaperPubMedID) |

`probe1.py` output on the pinned index:

```
PAIR (10.1016/j.diabet.2013.06.003, 24076359): D-14 RETRACTED_WORK_CITED ()  kappa COHERENT  role_ambiguous: ()
DOI only:  D-10 UNRESOLVED_IDENTITY ('IDENTIFIER_ROLE_COLLISION',)   role_ambiguous: ('ev-0054788',)
PMID only: D-10 UNRESOLVED_IDENTITY ('PMID_ROLE_COLLISION',)         role_ambiguous: ('ev-0054787',)
```

`Q1_DOI`, `Q1_PMID`, `Q2` all report `notice_hit_count = 0`, `identifier_role = original`. The positive value
(`retracted`, provenance record 54788) rests on the record whose DOI is collided; its "clean second identifier"
`24076359` is the notice PMID of record 18793. The checked evidence gives both cited identifiers the notice role, no
independent evidence resolves the object, and dt-2 attaches `RETRACTED_WORK_CITED`. This breaks the D-071 §3 rule as
the correction itself states it (ROOT_CAUSE §4: "a key of the citation that is not collided … resolves"). Whether the
real-world attachment is false is not established (inference); the rule violation is verified.

Why the existing checks miss it: SPEC 7.3a (lines 445-447) and MM `rc(c)` (lines 290-294) define the same-record
collision per event, so code and specification agree with each other; the dt-2 oracle models `rc` as an abstract
input bit (`dt2_reference.py` header), so it checks the table but not how `rc` is derived from the evidence; the
adversarial suite's PAIR tests (`test_corrective_role_collision.py:231-255`) put both flags on one event only;
the census decides only single-key citations, where the flagged event is always in the lookup.

Scope (verified, `probe7.py`): over all 31,756 original (DOI, PMID) pairs of the index, a key-level definition changes
exactly one decision, this pair (`D-14 RETRACTED_WORK_CITED → D-10 UNRESOLVED_IDENTITY`); nothing else moves.

Recommendation: make the collision a property of the key, not of the event: `(s, k)` is role-collided when
`notice_hit_count(Q1(k)) ≠ 0` (unchanged) **or any event of an available lookup of the candidate with `original_s = k`
carries `NOTICE_S_EQUALS_ORIGINAL`** (every such event is in `Q1(k)`, which a PAIR always has). Update SPEC 7.3a, MM
`rc(c)` and the R4-04 residual; add this pair as a real-row class of the adversarial suite and a synthetic two-event
test; add an index-wide sweep (single keys and pairs) as committed evidence (see B-06).

### B-02 — MEDIUM — The "clean second identifier" assumption keeps 860 DOI-collided pairs positive, mostly on absence of evidence

Verified counts (`probe2.py`, PAIR citations of real original pairs where a key has a notice role in the `ident`
table): dt-2 positives with a notice-role DOI and a clean PMID: 860 (RETRACTED 813, CONCERN 39, CORRECTION 8); with a
clean DOI and a notice-role PMID (the dt-1 PMID treatment): 169. Of the 886 events flagged
`NOTICE_DOI_EQUALS_ORIGINAL` that have an original PMID without the PMID flag, 692 record **no notice PMID at all**;
only 194 record a distinct notice PMID. For the dt-1 mirror (PMID flag, DOI resolves), 455 of 462 record a distinct
notice DOI.

On the merits (inference): the rule is logically coherent when the source positively distinguishes the scheme (a
distinct notice identifier of that scheme exists, so the cited one is original-only). In the 692 cases the PMID is
"clean" only because Retraction Watch recorded no notice PMID; for the "page overwrite" pattern of the failure case
(same DOI for article and notice) the PMID may well index the same overwritten object. Also, Wikipedia citation tools
commonly fill the PMID from the DOI, so the second identifier is often derived from the first, not independent
evidence of which object the author meant. The asymmetry with dt-1 (455/462 with positive evidence) is material.

Recommendation: put these numbers in front of the owner with the assumption. A stricter variant: a second identifier
resolves only when it is not collided (B-01, key-level) **and** the event records a distinct notice identifier of that
scheme (positive evidence of the scheme's role split); otherwise abstain. At minimum, disclose the 860 / 692 figures in
the R4-04 residual and the regression report.

### B-03 — MEDIUM — Original DOI + the same record's notice PMID stays positive (D-058 mirror, not owner-decided)

Verified. Fixture class `doi_original_pmid_notice_pair` (real row `ev-0000196`, record 73681: original DOI
`10.3389/fpsyg.2025.1544589`, no original PMID, notice PMID `41993809`) → `D-14 RETRACTED_WORK_CITED`
(`KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED`), also on the full index (`probe6.py`); synthetic
`test_doi_original_with_the_notice_pmid_is_unchanged` (line 175) pins it. 852 events have this exposure shape
(original DOI, no original PMID, a notice PMID). Not introduced by dt-2 (dt-1 decides the same), and it is not a
per-identifier collision, so D-071 §3 does not literally cover it; but the citation's two identifiers name two
different objects, one of them the notice, which is the failure's kind (a notice citation reported as the work). D-058
decided the mirror (notice DOI + original PMID); this direction rests on symmetry only.

Recommendation: record it for an explicit owner decision (extend D-058 by name, or abstain under "prefer abstention
over false attachment"); until then do not describe it as "unchanged by owner decision".

### B-04 — LOW — An unavailable Q1 of the resolving key resolves the collision for classification purposes

Verified (`probe4.py`): PAIR, event flagged `NOTICE_DOI_EQUALS_ORIGINAL`, `Q1(PMID)` unavailable →
`D-13 LOOKUP_UNAVAILABLE`; the same with `Q1(PMID)` available but without `notice_hit_count` → `D-10
UNRESOLVED_IDENTITY`. `notice_elsewhere` returns False for an unavailable lookup (`dt1.py:280-281`), so the unknown key
counts as clean. No positive is reachable (D-13 precedes D-14), so this is not a false attachment, but the brief asks
for `UNRESOLVED_IDENTITY` on an unresolved collision, and the two "unknown" cases are treated oppositely.
Recommendation: treat an unavailable Q1 as "may be a notice" inside `role_collided` (then D-10, which precedes D-13,
gives `UNRESOLVED_IDENTITY`), or document why `LOOKUP_UNAVAILABLE` is preferred.

### B-05 — LOW — Two census statements are inaccurate (engine unaffected)

Verified.
- ROOT_CAUSE §2.4: "`NO_NOTICE_IDENTIFIER` 3,864 events (… the cited key can only be the original — not a
  collision)". 24 of them carry `NOTICE_PMID_EQUALS_ORIGINAL` (17 with no original DOI): Stage 02 sets
  `NO_NOTICE_IDENTIFIER` whenever the DOI flag is absent (`ingest.py:114`), even when the PMID notice equals the
  original. This is a third Stage 02 asymmetry worth recording beside the two in §3. dt-2 does not read this flag, so
  no decision changes.
- `CENSUS.json` `cross_record.pmid.notice_events_flagged_NOTICE_ALSO_ORIGINAL_ELSEWHERE = 56` while ROOT_CAUSE §2.2
  says the PMID case has "no event flag". The 56 are flagged because their **notice DOI** is an original elsewhere
  (all 56 have that property, verified by SQL); the metric name invites the wrong reading.

Recommendation: correct §2.4, add the asymmetry, rename or annotate the PMID metric.

### B-06 — LOW — No committed dt-2 evidence over the index; the census omits PAIR citations

Verified. The census decides colliding keys with the frozen dt-1 only, and only as single-key citations; the
"expected effect" of ROOT_CAUSE §4 is not shown over the index by committed evidence (the regression covers the 232
development revisions and 80 campaign articles). My sweep confirms it for single keys: dt-2 on all 13,724 DOI keys in
both roles → `D-10` 13,724; on all 1,079 PMID keys → `D-10` 1,077, `D-9` 2; zero positives. The PAIR population, where
B-01 and B-02 live, is not censused at all.
Recommendation: add a dt-2 column and a PAIR section (original pairs where a key has a notice role, plus the mixed
original/notice pairs of B-03) to the census, and pin "no PAIR positive in which every cited key has a notice role in
the `ident` table" as a test over the fixture and as committed evidence over the pinned index.

### B-07 — INFO — Bridged attaching keys: flag counts, cross-record role does not; harmless for positives

Verified. A same-record flag on a bridged event forces D-10 (`test_a_bridged_event_attached_through_a_collided_doi_abstains`,
line 263), while a bridged key's cross-record notice role is ignored (`role_collided` checks cross-record only for
cited keys). Real case: PMID `3507357` → `D-14 CONCERN_CITED` with 254 `doi_cooccurrence` events attached through
`10.1016/s1873-9946(10)00006-1`, which 18 other records give as their notice DOI. Harmless for positives: Stage 02
never lets bridged records support a verified value (`policy.py:131-156`: bridged evidence is "not counted", or makes
the value uncertain / `BRIDGE_ONLY_SUPPORT`), and here the direct event `ev-0038168` is attached through a clean PMID.
The flag side is a small recall cost only. No action required; a sentence in SPEC 7.3a would make the asymmetry
explicit.

### B-08 — INFO — Normalization, notice-hit count and Stage 02 asymmetries: verified sound

- Both sides use the Stage 02 normalizers: candidate keys (`wiki/identifiers.py:22`), the query
  (`query.py:122-129`), source fields and the same-record flags (`ingest.py:85-104`). `normalize_doi` /
  `normalize_pmid` are idempotent on all 203,940 normalized values of the index (`probe3.py`: 0 differences), so
  `own == cited` in `attached_keys` compares like with like. Upper case, `doi:` prefix, `https://doi.org/`,
  `dx.doi.org` with `%2F` and outer whitespace all give `10.1002/asi.23238`; leading-zero and `pmid:`-prefixed PMIDs
  are invalid on both sides (taint, D-8). 13 same-record DOI collisions differ only in raw form and are flagged.
- `notice_hit_count` is the full count (`query.py:600`, `len(ev.notice_hits)`); only the listed hits are capped at
  100. A missing count fails closed (`detector.py:95-96`); `flags` and `notice_hit_count` are required by the Stage 02
  result schema the observation embeds.
- `ambiguous_identity` results always report `notice_hit_count = 0` (`query.py:306`, `341` return before notices are
  gathered). Not reachable as a resolving lookup: Q2 cannot be `matched` when Q1(PMID) is ambiguous, and an ambiguous
  Q1(DOI) is a D-5 violation.
- The Stage 02 asymmetries named in ROOT_CAUSE §3 (no DOI lookup issue; `NOTICE_ALSO_ORIGINAL_ELSEWHERE` for notice
  DOIs only) do not matter to dt-2, which reads the `NOTICE_*_EQUALS_ORIGINAL` flags and per-key Q1 counts; verified by
  the single-key sweep (all 27 cross-record PMID keys abstain). No Stage 02 maintenance is needed for B-01: the
  evidence is already in the observations.
- Crossref notice roles are invisible to both Stage 02's notice hits and dt-2, but `cr_assertion` has 0 rows in the
  pinned snapshot: latent only.

### B-09 — INFO — Census counts spot-checked: correct

Verified by direct SQL on the pinned index: same-record DOI 13,700 events / 13,681 keys; PMID 1,341 / 1,053; both
schemes 860; cross-record keys DOI 56, PMID 27; PMID notice events 61; context 3,864 / 7,573 / 758 / 5,194 of 73,356;
`ev-0033558` = record 40120, `retracted`, `notice_doi` null, flag `NOTICE_DOI_EQUALS_ORIGINAL`. The census definitions
(flag for same-record, post-nulling notice fields for cross-record) are what the engine reads. All 17 fixture classes
give the expected dt-2 outcome on the full index (`probe6.py`), confirming `subset_equals_full_index` for those queries.

## Verdict

NOT READY FOR REFREEZE: one CRITICAL (B-01, a real PAIR whose both identifiers carry the notice role is still
`RETRACTED_WORK_CITED`; a small key-level change of `role_collided` moves exactly that one of 31,756 pairs), plus two MEDIUM items for the
owner (B-02, B-03).

## Re-review of 9963908

Scope: commit `9963908` (`dt1.role_collided(c, scheme, key)` over all lookups of the candidate, `dt1.discriminating`,
`role_ambiguous` revised; `adapters/detector.py` `_flags` fail-closed; `census/PAIR_CENSUS.json`,
`PAIR_CENSUS_LENIENT.json`, `pair_census.py`; `CENSUS.json` with a dt-2 column; ROOT_CAUSE §2.4, §3, §4a, §4b;
`tests/stage04/test_corrective_role_property.py`). `src/citerift/investigation/dt1.py` and `adapters/detector.py` in the
working tree are identical to the commit (`git diff 9963908 --stat` lists only REVIEW_D, the runner, the fixture
script and the runner test). Same constraints as before; pinned index read-only; probes in
`/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/` (`probe8.py`, `probe9.py`, `probe10.py`
new; `probe1.py`, `probe6.py` re-run).

`uv run pytest tests/stage04/test_corrective_role_collision.py tests/stage04/test_corrective_role_property.py -q -p
no:cacheprovider` → `61 passed in 4.09s`.

### (1) B-01 and its variants now abstain — verified

Real pair `10.1016/j.diabet.2013.06.003` + `24076359` (production path, pinned index): `D-10 UNRESOLVED_IDENTITY
('IDENTIFIER_ROLE_COLLISION',)` (was D-14). Synthetic variants built with the suite's own observation builders
(`probe9.py`), all through `lookup_view` and `dt1.decide`:

| variant | result |
|---|---|
| V1 DOI flag on one record, PMID flag on another (B-01 shape) | D-10 `IDENTIFIER_ROLE_COLLISION` |
| V2 three records of one pair; the PMID flag on the third, the second clean with distinct notices | D-10 |
| V3 PMID same-record flag on an event present only in Q1(PMID), not in Q2 | D-10 |
| V4 DOI same-record flag on an event present only in Q1(DOI), not in Q2 | D-10 |
| V5 resolving PMID is another record's notice (`notice_hit_count` 1 in Q1(PMID)) | D-10 |
| V5b Q1(PMID) without `notice_hit_count` | D-10 |
| V7 resolving PMID "clean" only by absence (record states no notice PMID) | D-10 |
| V10 malformed (`null`) flags on an event only in Q1(PMID) | D-10 (read as both flags) |
| V6 DOI collided, PMID uncollided and the record states a different notice PMID | D-14 (the designed resolution) |
| V8 DOI cross-record notice, PMID discriminating | D-14 (designed) |

Index-wide (`probe8.py`, 129 s): all 175,491 distinct DOI and PMID keys of the snapshot (every original and every
notice key) as single-key citations → no D-14 on any key that the `ident` table gives a notice role (D-14 81,743, all
on keys with no notice role; D-15 78,688; D-10 14,801; D-11 240; D-9 17; D-7 2). All 31,756 original pairs → D-14
30,034, D-10 1,570, D-11 105, D-6 47: identical to `PAIR_CENSUS.json` (transitions sum to the same totals).

### (2) No dt-2 positive rests on a key with a notice role — verified, with one owner-level exception (B-03)

- Single keys: 0 positives on a notice-role key (above).
- Original pairs: 357 positives have one cited key with a notice role (193 DOI, 164 PMID); **none has both**. An
  independent check from the raw `ident` table (`probe10.py`, not using `dt1`) confirms that in every one of the 357,
  every direct event attached through the notice-role key is resolved by the other cited key, which is that event's
  original identifier, has no notice role anywhere in the snapshot, and whose record states a different notice
  identifier in its scheme: 0 violations.
- Notice DOI + original PMID (D-058 shape): 31,390 real combinations → 158 positives, each attached through the
  original PMID (owner decision D-058). Notice DOI + notice PMID: 29,532 → no positive (D-15 29,495).
- Original DOI + notice PMID (B-03 shape): 31,279 real combinations → **628 positives**
  (`RETRACTED/…_CITED` with `KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED`), e.g. `10.1002/14651858.cd000018` +
  `21563126`. The attaching key (the DOI) has no notice role, so no positive rests on a notice-role *attaching* key,
  but the citation itself carries a notice identifier. Unchanged by 9963908; see B-03.

### (3) Status of the original findings

| id | severity | status after 9963908 | evidence |
|---|---|---|---|
| B-01 | CRITICAL | **Resolved** | real pair now D-10; V1–V5, V10 abstain; key-level rule over all lookups (`dt1.role_collided`); index sweeps above |
| B-02 | MEDIUM | **Resolved in code (strict); owner decision pending on strict vs lenient** | `discriminating` requires a different notice identifier in the resolving scheme (V7 abstains); `PAIR_CENSUS.json` 1,570 changes vs `PAIR_CENSUS_LENIENT.json` 881 put to the owner (ROOT_CAUSE §4a, §4b). I support the strict reading. |
| B-03 | MEDIUM | **Open — owner decision** | 628 real original-DOI + notice-PMID combinations positive; `test_doi_original_with_the_notice_pmid_is_unchanged` still pins D-14; no owner decision, and ROOT_CAUSE / SPEC do not mention the D-058 mirror. Recommendation unchanged. |
| B-04 | LOW | **Open** | V9: DOI collided, resolving PMID's Q1 unavailable → `D-13 LOOKUP_UNAVAILABLE` (no positive possible: D-13 precedes D-14). SPEC 7.3a now states "an unavailable lookup states nothing and is handled by D-13", so the behaviour is documented, but ROOT_CAUSE §4 ("A collided candidate whose lookup is also unavailable is `UNRESOLVED_IDENTITY`") overstates it for this case. Fix the sentence or read an unavailable Q1 as "may be a notice". |
| B-05 | LOW | **Resolved** | ROOT_CAUSE §2.2 annotates the PMID metric (counts the DOI flag), §2.4 records the 24 `NO_NOTICE_IDENTIFIER` + `NOTICE_PMID_EQUALS_ORIGINAL` events and §3 the third asymmetry. (The JSON key name is unchanged; acceptable with the annotation.) |
| B-06 | LOW | **Resolved** | `CENSUS.json` now has a dt-2 column (all single colliding keys D-10 or D-9, 0 positives, matching my sweep); `PAIR_CENSUS.json` covers all original pairs; the property test checks `roleamb` against an independent formulation. The mixed original/notice pair shapes (B-03) are still not in the committed census. |
| B-07 | INFO | Unchanged | bridged non-cited flagged event still forces D-10 (now also because only cited keys resolve); bridged clean event stays D-14; harmless for positives |
| B-08 | INFO | Unchanged | normalization and count findings still hold |
| B-09 | INFO | Unchanged | census counts still correct; PAIR census totals verified against my independent sweep |

New in 9963908: no new defect found. The `_flags` fail-closed reading (V10) and the "any attaching key collided"
semantics with resolution only by a discriminating cited key are consistent with D-071 §3 and §4 on every probe.

### Re-review verdict

No open CRITICAL or HIGH in identity / publication-object roles. Open: B-03 (MEDIUM, owner decision on the D-058
mirror, 628 real combinations), B-02 strict-vs-lenient choice (owner decision; strict is implemented), B-04 (LOW,
one overstated sentence).
