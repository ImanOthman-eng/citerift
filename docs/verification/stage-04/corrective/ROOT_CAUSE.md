# Stage 04 corrective cycle: root cause, role-collision census, placement and proposed rule

Owner decision D-071 (`cmsg_018VCB51nDHP6HXmLU4ea5yPTDrESsDr75RoYgLhdymUyn`, 2026-11-18T20:07:29Z), items 1 to 2 of
the immediate action. The failed campaign (`evaluation-campaign/`, commit `1064113`) is not altered; nothing here
reads its labels to choose a rule or a threshold. The 80 campaign articles are design-exposed development evidence
from this point on.

## 1. Reconstruction of `en-39868218` / `un-00011`

Unit (packet `en-39868218`, item `un-00011`): `{{cite journal … doi=10.1002/asi.23238 |title=''Withdrawal:'' 'A new
type of misconduct …' by L. Iorio|year=2014}}` — one DOI, no PMID, so the candidate's shape is `DOI` and its deciding
lookup is Q1(DOI).

Stage 02 (index `rw-2f116e9ffed718e6`, artifact digest `adcf7b65…16d9`), read-only:

| What | Value |
|---|---|
| Source record | ordinal 33558, Record ID 40120, `RetractionNature = Retraction` |
| `OriginalPaperDOI` / `RetractionDOI` | `10.1002/asi.23238` / `10.1002/asi.23238` (identical) |
| `OriginalPaperDate` / `RetractionDate` | `4/28/2014 0:00` / `4/28/2014 0:00`; notes "date of retraction unknown, html page overwrite" |
| `ident` rows | two occurrences of `10.1002/asi.23238`: role `original` (`OriginalPaperDOI`) and role `notice` (`RetractionDOI`) |
| Event `ev-0033558` | `retracted`, `original_doi = 10.1002/asi.23238`, `notice_doi = null`, `notice_key = null`, flag `NOTICE_DOI_EQUALS_ORIGINAL` |

Stage 02 therefore preserves both roles faithfully: the `ident` table keeps the notice occurrence, the event carries
the import flag `NOTICE_DOI_EQUALS_ORIGINAL`, and SPEC 6.3 states that such a record "is not an independent notice
witness". It deliberately nulls the event's notice field (so the DOI is not counted twice as a notice key), and the
lookup is `matched`, `identifier_role = original`, projection `verified_fact` / `retracted`.

The run's lookup observation (`1f1774a3…` in the export of `en-39868218`) holds exactly that: one event,
`matched_by = doi`, flags `["NOTICE_DOI_EQUALS_ORIGINAL"]`, no lookup issue.

Frozen dt-1 path (reproduced with the census tool on the same index): D-1 … D-9 do not hold; D-10 holds only for a
`PMID_ROLE_COLLISION` issue naming a PMID-matched event or for `BRIDGE_ONLY_SUPPORT` — neither is present; D-11
needs an uncertain projection; D-13 needs an unavailable lookup; **D-14** holds → `RETRACTED_WORK_CITED`.

**Root cause.** dt-1 reads a role collision only through the Stage 02 *lookup issue* `PMID_ROLE_COLLISION`. Stage 02
raises that issue for the PMID case only (Stage 02 SPEC 10.3 step 9, added after audit F3, which counted 1,341 PMID
events). The DOI case is exposed by the *event flag* `NOTICE_DOI_EQUALS_ORIGINAL`, and a key that is the notice
identifier of another record is exposed by `identifier_role = original_and_notice` and `notice_hits`. dt-1 reads
neither, so an identifier the checked evidence gives as both the work and its notice reaches D-14 as an original.
This is a gap in Stage 04 semantics (the evidence was committed and in hand), not a one-off data error: the census
below shows it is the common case, not the rare one.

## 2. Role-collision census of the pinned Stage 02 snapshot

Tool: `census/role_collision_census.py` (read-only, `mode=ro`, no network, no clock, no label). Output:
`census/CENSUS.json` (SHA-256 `292007d1…c71f`). Snapshot: 73,356 records, 73,356 events, 0 quarantined.

### 2.1 Same-record collisions (one record gives the key in both roles)

| | DOI | PMID |
|---|---|---|
| records | **13,700** (18.7 % of events) | 1,341 |
| distinct keys | 13,681 | 1,053 |
| by event type | retracted 13,396 · EoC 163 · correction 38 · reinstated 103 | retracted 794 · EoC 335 · correction 132 · reinstated 80 |
| record also has no independent notice identifier | 13,340 | 884 |
| record has a distinct notice identifier of the other scheme | 360 (notice PMID) | 457 (notice DOI) |
| both schemes equal in the same record | 860 | 860 |
| exposed by Stage 02 as | event flag only | event flag **and** lookup issue `PMID_ROLE_COLLISION` |

### 2.2 Cross-record collisions (the key is the original of one record and the notice of another)

| | DOI | PMID |
|---|---|---|
| distinct keys | 56 (43 cross-record only, 13 also same-record) | 27 (26 cross-record only, 1 also same-record) |
| events with the key as original / as notice | 328 / 681 | 307 / 61 |
| exposed by Stage 02 as | `identifier_role = original_and_notice`, `notice_hits`; notice event flagged `NOTICE_ALSO_ORIGINAL_ELSEWHERE` | `identifier_role = original_and_notice`, `notice_hits`; **no** PMID flag (Stage 02 sets `NOTICE_ALSO_ORIGINAL_ELSEWHERE` for notice DOIs only; the census metric of 56 flagged notice events counts that DOI flag, reviewer finding B-05) |

Event-type pairs (original role / notice role, counted per key) include retracted/correction (DOI 21, PMID 10),
correction/retracted (11, 11), retracted/retracted (13, 1), retracted/reinstated (3, 2) and EoC/EoC (4, 1); the full
table is in `CENSUS.json`.

### 2.3 Frozen-engine class of a citation that carries only the colliding key

Each colliding key decided by the frozen dt-1 code on the observation the production LOOKUP adapter builds (default
evidence budget), as a cited single-key candidate with no taint:

| Group | keys | frozen outcome | dt-2 outcome |
|---|---|---|---|
| DOI, same-record only | 13,668 | **D-14 positive 13,560** (RETRACTED 13,489 · CONCERN 53 · CORRECTION 18); D-11 108 | D-10 13,668 |
| DOI, cross-record only | 43 | **D-14 positive 43** | D-10 43 |
| DOI, same and cross | 13 | **D-14 positive 13** | D-10 13 |
| PMID, same-record only | 1,052 | D-10 1,051 (`PMID_ROLE_COLLISION`); D-9 1 | unchanged |
| PMID, cross-record only | 26 | **D-14 positive 25**; D-10 1 | D-10 26 |
| PMID, same and cross | 1 | D-9 1 | D-9 1 |

The frozen column is decided by the frozen `dt1.py` loaded by its pinned git blob (`frozen_dt1.py`; reviewer finding
E-04: an earlier version of the census script used the working-tree table, which is now dt-2; the frozen column
reproduces the first census byte for byte). Cited **pairs** are in `census/PAIR_CENSUS.json` (section 4b).

So 13,641 colliding identifiers can produce a positive attachment under the frozen engine; the PMID same-record case
is the only one dt-1 already withholds.

### 2.4 Context (not collisions)

`NO_NOTICE_IDENTIFIER` 3,864 events (no notice identifier stated: normally not a collision, but 24 of them also carry
`NOTICE_PMID_EQUALS_ORIGINAL`, a third Stage 02 asymmetry found by reviewer B (B-05); dt-2 reads the flag itself, so
those 24 are handled as collisions); `NOTICE_SHARED` 7,573 (one notice for several works: compatible roles); original anchored by PMID only 758;
by source record only 5,194 (no original identifier: such a record can be reached only through its notice key, which
gives `notice_only` → `NOTICE_CITED`).

## 3. Placement: Stage 02 or Stage 04

Stage 02 preserves both roles (the `ident` rows), marks the collision on the event (`NOTICE_DOI_EQUALS_ORIGINAL`,
`NOTICE_PMID_EQUALS_ORIGINAL`) and reports cross-record roles in every matched lookup (`identifier_role`,
`notice_hits`, `notice_hit_count`), and every one of these is already in each committed lookup observation (the
observation keeps every event with its flags and Stage 02's full rendered result). Stage 04 can therefore decide the
case from evidence it already commits.

**Decision: the correction belongs in Stage 04 semantics only. No Stage 02 maintenance is required.** Three Stage 02
asymmetries are recorded as observations, not changed: the lookup issue exists for PMID collisions but not for DOI
collisions, `NOTICE_ALSO_ORIGINAL_ELSEWHERE` is set for DOIs but not for PMIDs, and `NO_NOTICE_IDENTIFIER` can stand
beside `NOTICE_PMID_EQUALS_ORIGINAL` (24 events). Neither is needed by the
correction, because Stage 04 reads the event flags and the per-key notice hits directly.

Build-vs-Adopt (permanent rule of 2026-11-10): not applicable — the correction is a guard extension of one existing
rule of the existing dt-1 module and its adapter view, not a new subsystem; no external component offers Retraction
Watch role semantics over this index.

## 4. Proposed general rule (dt-2)

**Principle (owner, D-071 §3).** An identifier whose checked evidence gives incompatible publication-object roles must
never produce a positive work attachment solely because one of those roles is original.

Definitions, for a cited candidate `c` with cited keys `K(c)` (its DOI and/or PMID), its lookups `Λ(c)` and deciding
lookup `L` (as implemented after the independent reviews; section 4a gives the first draft and why it changed):

1. An event `e` of `L` is **attached through** the key `(s, k)` when `e.original_s = k` and either `k ∈ K(c)` (a cited
   key) or `s = e.matched_by` (the key through which Stage 02 matched or bridged it).
2. The key `(s, k)` has a **notice role** when
   - (same-record) some event of any lookup in `Λ(c)` has `k` as its original `s` identifier and carries
     `NOTICE_S_EQUALS_ORIGINAL`: a source record gives `k` as both its original and its notice identifier; or
   - (cross-record) `k ∈ K(c)` and the single-key lookup of `k` (`L` itself for a DOI or PMID candidate, Q1 of that
     key for a PAIR) has `notice_hit_count > 0` (absent: read as > 0): another record gives `k` as its notice.
   It is a property of the key, not of one event.
3. A cited key `(s, k)` **discriminates** for `e` when `e.original_s = k`, `k` has no notice role, and `e.notice_s` is
   present and differs from `k`: the record itself tells the work (identifier `k`) from its notice.
4. `e` is **role-ambiguous** when it is attached through a key with a notice role (or through no key; fail closed)
   and no cited key discriminates for it. Nothing else resolves it (no non-cited bridge key, title, journal,
   publisher, DOI prefix, language or text test). `roleamb(L)` is the set of role-ambiguous events of `L`.

**Rule D-10 (dt-2).** `L.state = matched`, its projection within the contract, and (`roleamb(L) ≠ ∅` or the basis
reasons include `BRIDGE_ONLY_SUPPORT`) → `UNRESOLVED_IDENTITY`, reasons: `PMID_ROLE_COLLISION` when `L` has a
`PMID_ROLE_COLLISION` issue naming a PMID-matched event (unchanged from dt-1), **`IDENTIFIER_ROLE_COLLISION`** when
`roleamb(L)` holds an event not covered by that issue, `BRIDGE_ONLY_SUPPORT` as before.

Properties:

- **Extension of dt-1.** The guard keeps dt-1's `collision(L)` unchanged, so every dt-1 PMID collision still
  reaches D-10; dt-2 only adds `roleamb(L)`. Where `roleamb(L)` is empty dt-2 decides exactly as dt-1: proved over the
  whole abstract domain of the dt-2 oracle given the abstract input `rc` (`EQUIVALENCE_RC_FALSE`). How `roleamb` is
  computed is outside that oracle; it is checked exhaustively on a synthetic domain against an independent
  formulation (`tests/stage04/test_corrective_role_property.py`) and on all real DOI+PMID pairs (section 4b).
- **Precedence unchanged.** The protection is a guard of D-10 (tier 5, "unresolved"): after D-5 (contract), D-6
  (identity conflict) and D-7 (contradiction), before D-13 (operational failure) and D-14 (positive), and before
  D-15/D-16 (notice / not found). The order contradiction → unresolved → operational failure → positive →
  notice/no-finding is not changed. A collided candidate whose deciding lookup is matched and another lookup
  unavailable is `UNRESOLVED_IDENTITY`, exactly as a PMID collision already is under dt-1. When the lookup of a key
  that would otherwise discriminate is unavailable, that key states nothing and the result is D-13
  `LOOKUP_UNAVAILABLE` or D-10, never a positive (reviewer finding B-04).
- **Abstention, not a notice claim.** `NOTICE_CITED` stays reachable only through D-15 (a `notice_only` deciding
  lookup). A collision never produces `NOTICE_CITED` and never a negative.
- **New reason code justified.** `PMID_ROLE_COLLISION` names a PMID-specific Stage 02 issue; no existing code
  represents a DOI or cross-record collision, so one code, `IDENTIFIER_ROLE_COLLISION`, is added.

### 4a. Revision after the independent reviews

The first draft (fail-first evidence and the first oracle run) defined collision **per event** (the same-record flag
of `e` itself) and let **any** non-collided key resolve. Reviewers found:

- B-01 (CRITICAL, confirmed): a cited pair `10.1016/j.diabet.2013.06.003` + `24076359` whose DOI one record gives both
  roles and whose PMID another record gives both roles was `RETRACTED_WORK_CITED`: each event looked resolved by the
  other key. Fixed by making the notice role a property of the key over all lookups of the candidate.
- A-01 (MEDIUM): a non-cited bridge key could resolve a collided cited key. Fixed: only cited keys resolve.
- A-02 / B-02 (MEDIUM): in 692 of 886 events with a same-record DOI collision and a clean original PMID, the record
  states no notice PMID, so the PMID is "clean" only because evidence is missing. The rule now requires the record to
  give a different notice identifier in the resolving scheme (strict reading of "independent evidence"); the lenient
  alternative was measured and put to the owner, who approved the strict rule (D-072).

### 4b. Pair census

All 31,756 distinct original DOI+PMID pairs of the snapshot, cited together and decided by both tables
(`census/PAIR_CENSUS.json`; `PAIR_CENSUS_LENIENT.json` for the alternative): dt-2 changes 1,570 decisions (D-14 →
D-10: RETRACTED 1,410, CONCERN 39, CORRECTION 23; D-11 → D-10: 98). That no dt-2 positive rests on a role-ambiguous event holds by construction (the D-10 guard); reviewer B
checked independently, from the raw `ident` table, that every one of the 357 pair positives with one cited key in a
notice role rests on the other cited key, which has no notice role and whose record gives a different notice
identifier. Strict versus lenient also differs on the PMID side (reviewer finding A-10): dt-1 let a clean DOI
resolve a PMID collision; the strict rule requires the record to give a different notice DOI, which drops 5 positive
pairs (for example `10.1074/jbc.274.11.7196` + `10066780`; the DOI alone is positive). Original DOI cited with the
same record's notice PMID stays positive when the DOI is clean (628 pairs under dt-2, `census/B03_CENSUS.json`; the
mirror of owner decision D-058, reviewer finding B-03, kept by owner decision D-075).
Under the lenient alternative 881 change (800 positives). Positives: dt-1 31,506, dt-2 30,034.

Expected effect, stated before any regression is run: the JASIST unit becomes `UNRESOLVED_IDENTITY`
(`IDENTIFIER_ROLE_COLLISION`); every cited identifier in §2.3 that the frozen engine made positive becomes an
abstention unless the citation carries a second identifier that discriminates (section 4, item 3). That is a recall cost on
real retractions (most same-DOI records describe a genuine retraction communicated on the article itself), accepted by
D-071 §4 ("prefer abstention over false attachment") and reported in full in the regression.
