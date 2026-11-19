# Review C: regression risk of dt-2 against the frozen dt-1

Reviewer C, independent, read-only. Branch head `cd26abf`. Rule reviewed: strict key-level dt-2 (SPEC 7.3a,
`corrective/ROOT_CAUSE.md`). Facts are marked **[fact]** (observed in a file or a command output of this review) and
inferences **[inference]**. No campaign label, adjudication, packet or score was read (F-08); all judgements below come
from Stage 02 evidence and the committed regression outputs.

## 1. Scope read

`REVIEW_BRIEF.md`; `corrective/regression/{README.md, regress.py, named_cases.py, DEV_REGRESSION.json,
CAMPAIGN_REGRESSION.json, NAMED_CASES.json}`; `corrective/frozen_dt1.py`; `corrective/ROOT_CAUSE.md` (all);
`corrective/census/{PAIR_CENSUS.json, PAIR_CENSUS_LENIENT.json, pair_census.py}`; `freeze-2/vertical-slice/vertical_slice.json`
(structure and `failed_checks`); `git diff f207bc0 -- src schemas` (all 8 files); SPEC 7.3 / 7.3a; the pinned index
(`mode=ro`); `operations.py` (show/verify/replay staleness), `fold.py`, `explanations.py`.

## 2. Method

- Compared the committed regression JSONs with the source of `regress.py` and `frozen_dt1.py` (blob pinned and hashed).
- `git diff --stat dfee881 cd26abf -- src schemas` and `git diff --stat 90bc60e cd26abf -- src schemas` are empty
  **[fact]**: the shards (`dfee881`, `90bc60e`) and `NAMED_CASES` (`db3b798`) ran on the same engine sources as the head.
- Looked up the five changed claims and their events in the pinned index with Python `sqlite3` (`mode=ro`); re-ran the
  two pair cases through the production `observe` / `lookup_view` / `dt1.decide` (small probe, no network).
- Classified all 1,570 changed pairs of `PAIR_CENSUS.json` by their role-ambiguous events, from the `event` table.
- Ran `test_step9_detector.py` (41 passed), `test_step9_real.py` (11 passed), `test_step9_b8.py` (6 passed), one at a
  time, `-p no:cacheprovider`. Probed decision cost on synthetic candidates; probed schema validation of a frozen journal.

## 3. Findings

### C-01 MEDIUM: key-level rule abstains on a probable true positive whose deciding event is itself clean (owner question, not covered by the existing "lenient" card)

**Fact.** `ar-3351802 un-00059` (DOI `10.1186/1741-7015-11-222`, PMID `24120035`). Index events for the pair:

| event | type | original DOI / PMID | notice DOI / PMID | flags |
|---|---|---|---|---|
| ev-0019152 | retracted | the cited pair | `10.1186/s12916-024-03504-x` / `38965520` | none |
| ev-0035654 | expression_of_concern | the same pair | null / null | `NOTICE_DOI_EQUALS_ORIGINAL`, `NOTICE_PMID_EQUALS_ORIGINAL` |

Probe: `role_collided(doi)` and `role_collided(pmid)` are both True (the flags of ev-0035654 are read key-level over all
events of all lookups), no key discriminates for ev-0019152, `roleamb = {ev-0019152, ev-0035654}`; dt-2 gives D-10
`IDENTIFIER_ROLE_COLLISION`, dt-1 gave D-14 `RETRACTED_WORK_CITED`. The abstention is correct under SPEC 7.3a as written;
it is exactly the B-01 key-level behaviour.

**Judgement.** **[inference]** This is very likely a true-positive loss caused by the key-level rule. The deciding
retraction record states a notice DOI and a notice PMID that both differ from the cited keys (it tells work from
notice in both schemes), and the colliding record is a second record with the same original DOI and PMID, i.e. the same
work (an expression of concern whose notice identifiers equal the article's). Nothing in the evidence suggests that
the cited identifiers name a different work or a notice of one. The B-01 counterexample the key-level rule was written for
(DOI collided by one record, PMID collided by a different record, so that no record resolves) is structurally different:
there the colliding records differ from each other.

**Frequency, from `PAIR_CENSUS.json` (31,756 pairs, 1,570 changed) and the index [fact for the counts, inference for the
reading].** In 74 of the 1,570 changed pairs (4.7 % of changes, 0.23 % of all pairs) some role-ambiguous event has
distinct notice identifiers in both schemes and no own flag, i.e. its own record is clean and only another record
collides the keys. Split by where the collision comes from (checked per key in the `event` table):

- 53: another event with the same original DOI and PMID and the `NOTICE_*_EQUALS_ORIGINAL` flags (the un-00059 type; same
  work). Likely true-positive losses.
- 21: another record gives the cited DOI and PMID as its notice identifiers while its original differs (genuine
  cross-record ambiguity; abstention is the intended behaviour).

For single DOI citations the analogous pattern (a clean-notice event plus a same-DOI flagged sibling) covers 197 of 13,681
DOI keys with a same-record collision (1.4 %); a single key cannot discriminate under any version of the rule, so this
is only a size note. In the real regression sets 1 of the 5 changed claims is of this type.

**Not covered by the owner's lenient card [fact].** All 74 pairs are also abstentions under `PAIR_CENSUS_LENIENT.json`
(checked: 74 of 74 appear in its changed list), because the lenient variant still requires a key with no notice role.
Putting only the lenient/strict question to the owner therefore leaves this loss unmentioned.

**Recommendation.** Put it to the owner as a separate item with the numbers above. A refinement that stays inside the
principle: a collision caused by a record whose original DOI and PMID both equal those of the event is not a different
work's notice (does not make the key role-collided for that event) when the event's own record gives a distinct notice
identifier. This needs a new oracle property and new adversarial tests (B-01 must stay closed), so it is an owner
decision and a re-freeze matter, not a quiet fix. If the owner declines, state in SPEC 7.3a and the regression README
that these cases abstain by design.

### C-02 LOW: frozen-engine investigations are refused by schema, not reported STALE (inference for the end status)

**Fact.** `common.schema.json` `stage04_identity` now has `table_version` const `dt-2` and `schema_version` const `4.0.0`;
`journal-record.schema.json` and `report.schema.json` reference it. Validating the first record of a frozen journal
(`freeze/vertical-slice/VS-6a/journal.jsonl`, record `investigation_created`) against `schemas.RECORD` gives
`/payload/stage04/schema_version: '4.0.0' was expected` and `/payload/stage04/table_version: 'dt-2' was expected`; the other
25 records validate. The claim schema's `table_version` is the same const, so a dt-1 claim is not valid either.

**Inference.** Memory validates every record on open (`journal.py` around line 262, "Validate everything before changing
anything"), so a Memory root created by engine 0.2.0 opens as `JOURNAL_CORRUPT` / CORRUPT, not as the STALE the engine
identity digest would give (`fold.py` 703, tests `test_controller_adversarial.py:381`, which change only `engine_version`).
Nothing is misread (no dt-1 claim is shown as a dt-2 claim, and `replay` and `verify` cannot reproduce it), so this is a
refusal. The schema description states that dt-1 claims "are not migrated". I found no test that pins the behaviour for a real
dt-1 journal.

**Recommendation.** Either add a test that opens a copy of a frozen journal and asserts the intended outcome, or record in
SPEC 10.3 / the closure that a pre-0.3.0 Memory root is CORRUPT by design and must be re-run under a new key. Any real
0.2.0 user investigation would otherwise see "corrupt" for a valid artifact.

### C-03 INFO: changes in the real regression sets are all explained by the rule; the dt-1 cross-checks are meaningful but unequal in strength

**Fact.** `DEV_REGRESSION.json`: 232 revisions, 4,614 candidates, 1 changed claim (D-14 CONCERN_CITED to D-10, reason
`IDENTIFIER_ROLE_COLLISION`); `CAMPAIGN_REGRESSION.json`: 80 articles, 4,920 candidates, 4 changed claims (D-14
RETRACTED_WORK_CITED to D-10). `changed_reasons_only` 0, `new_positive` 0, `new_notice_cited` 0, `new_not_found` 0,
`recorded_equals_dt2_everywhere` true, `network_attempts` 0, `engine_sources_uncommitted` false, index artifact digest
`adcf7b65...` in both. The four campaign claims and the dev claim have exactly one role-ambiguous event pair as listed
(`role_ambiguous_events`); the pair census transitions are only D-14 to D-10 (1,410 + 39 + 23) and D-11 to D-10 (98); D-6, all
other D-14 and D-11 pairs are unchanged. Precedence is intact by construction (D-10 is a guard of tier 5; nothing moves
to or from NOTICE_CITED, D-13 or D-16).

Cross-check strength **[fact]**: the campaign check compares cand_ref, class, rule and reasons of every one of 4,649 historical
claims with the frozen dt-1 re-decided on the committed inputs: strong, claim level, 0 mismatches. The dev check compares
per-revision unit class sets with `DEV_RUN.json` `engine_unit_classes`, present for 231 of 232 revisions (the 232nd is
checked on lifecycle only): coarser, not claim level, but not vacuous. `to_frozen` drops only dt-2-only fields, and the
frozen blob is verified by git blob id and SHA-1 before it is executed (`frozen_dt1.py`). Power is low: 5 changed claims
over 102 positive units (about 4.9 %), which matches the pair census (1,472 of 31,506 positive pairs, 4.7 %); the real
sets add no information about D-11 to D-10 (98 pairs in the census, 0 in the sets). The D-11 to D-10 change turns an
`UNRESOLVED_STATUS` into `UNRESOLVED_IDENTITY`: both abstain, but report counts and limitation sentences differ.

### C-04 INFO: each of the five changed claims is a correct abstention under SPEC 7.3a

All five are checked against the index (**[fact]**; probe output for the two pair cases):

| claim | evidence | verdict |
|---|---|---|
| `en-39868218 un-00011`, DOI `10.1002/asi.23238` | single event ev-0033558, `NOTICE_DOI_EQUALS_ORIGINAL`, notice DOI null; the failing case | correct |
| `en-1741558 un-00016`, DOI `10.1016/j.amc.2007.03.011` | single event ev-0001077, same flag | correct |
| `en-1382450117 un-00008`, DOI `10.4171/emss/4-2-3` (EoC) | single event ev-0056935, same flag | correct |
| `en-12228277 un-00110`, DOI `10.1016/j.giec.2006.03.005` + PMID `16644460` | ev-0032195 flagged for the DOI; the record states no notice PMID (zero sentinel), so the PMID is not a discriminating key under the strict reading | correct under the strict rule (the strict/lenient owner question: 1,570 versus 881 changes) |
| `ar-3351802 un-00059` | see C-01 | correct under the written rule; probable true-positive loss |

The giec case is the A-02/B-02 pattern: **[inference]** a retraction with an original PMID that no record gives as a
notice is probably a real retraction, so it is also a likely recall cost, already measured and put to the owner.

### C-05 INFO: named cases keep their classes; D-058, D-059, D-060 are pinned by passing tests

`NAMED_CASES.json` **[fact]**: `unchanged: true`, all eight cases `changed: []`, `recorded_equals_dt2` true, `verified` true,
`network_attempts` 0, class counts dt-1 equal dt-2: Wakefield/MMR (NOTICE_CITED 1, RETRACTED 1), Obokata ar (IDENTITY_CONFLICT 1,
RETRACTED 1) and en (RETRACTED 2), GFAJ-1 (NOTICE_CITED 2, RETRACTED 2), EoC (CONCERN_CITED 1), BCAS3 (RETRACTED 2), both
reserves (all NOT_FOUND). `vertical_slice.json` of freeze-2 has `failed_checks` empty and network attempts 0. Tests run
here: `test_step9_detector.py` 41 passed (D-058 pair test at line 325), `test_step9_real.py` 11 passed (D-059, VS-5),
`test_step9_b8.py` 6 passed (D-060). D-058 stays positive because its PMID is neither flagged nor a notice elsewhere.

### C-06 INFO: new reason code is handled by the consumers I could find

`IDENTIFIER_ROLE_COLLISION` is in `common.schema.json` `reason` (4.0.0), in the claim schema's D-10 `contains` list, and in
`explanations.REASON_TEXT` (a direct dict lookup, so omission would raise `KeyError`; it is present and the text passes the
wording test that iterates `REASON_TEXT.values()`, `test_step10_report.py:272`). The projections and the report only key on the
claim class (UNRESOLVED_IDENTITY already has template and limitation sentence), and no code branch tests for
`PMID_ROLE_COLLISION` outside the detector and Stage 02. I did not find a v1 contract mapping that lists reasons; I did not
run the export or projection tests. `PMID_ROLE_COLLISION` is unchanged and keeps priority when the Stage 02 issue names
the event (`set(role_ambiguous) - set(L.collision)`).

### C-07 LOW: role-collision scans are quadratic in the events of a candidate's lookups

`role_collided` iterates all events of all lookups for each (event, key, scheme), and `role_ambiguous` runs once as a
guard and again for reasons when D-10 is reached. Measured on synthetic candidates (3 lookups of n events each): n=100 0.005 s,
n=1,000 0.27 s, n=3,000 2.3 s per `decide` **[fact]**. In the pinned index the largest key has 281 events (original PMID
`35073579`; DOI 255), about 0.02 s, so real cost is negligible; the lookup evidence budget (16 MiB) would allow far more events
but Stage 02 caps by key in practice. **Recommendation:** none required; if a pathological index is ever expected, compute the
set of collided (scheme, key) pairs once per candidate.

### C-08 INFO: determinism

`role_ambiguous` returns a sorted tuple, reasons are a set rendered in a fixed order, no clock or randomness enters the new
code; `notice_hit_count` and the flags come from the committed observation. `recorded_equals_dt2` holds for every candidate
of both sets (recomputed from committed inputs). README claim that the `run` code of `regress.py` is unchanged since the
shards ran cannot be checked from git (the file has one commit after the shards' `dfee881`), so it is the author's
statement; the outputs are internally consistent either way.

## 4. Answers to the brief

1. Yes: every changed claim is a D-14 (or, in the census, D-11) to D-10 abstention explained by the rule; no new positive,
   NOTICE_CITED or NOT_FOUND; precedence intact; cross-checks meaningful (claim level on the campaign, class-set level on dev).
2. All five abstentions are correct under SPEC 7.3a. `un-00059` is, in my judgement, a probable true-positive loss caused by the
   key-level rule (C-01); about 74 of 1,570 changed pairs (4.7 %), 53 of them the same-work sibling type; I recommend putting
   it to the owner as an item separate from the lenient card.
3. Named cases keep their classes; D-058, D-059, D-060 tests pass.
4. Frozen-engine investigations are refused by schema (CORRUPT, inferred), not misread and not reported STALE (C-02);
   the new reason code is handled in the places I found (C-06).
5. Cost and determinism acceptable (C-07, C-08).

## 5. Verdict

No CRITICAL or HIGH finding. One MEDIUM (C-01, owner question about a probable recall loss of the key-level rule), one LOW
behavioural gap (C-02), one LOW cost note (C-07). dt-2 is regression-safe against dt-1 for the cases examined: ACCEPT WITH
C-01 PUT TO THE OWNER AND C-02 DOCUMENTED OR TESTED.
