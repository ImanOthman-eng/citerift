# Corrective cycle review D: source provenance

Reviewer D (fresh, independent; did not write the correction). Brief: `REVIEW_BRIEF.md`. Reviewed tree: commit
`9963908` on top of `f207bc0` (the only uncommitted changes are in `corrective/runner/s13_run_v2.py` and
`tests/stage04/test_corrective_runner.py`, outside this review; `git diff 9963908 --quiet -- src` is clean), 2026-11-18.
This replaces the draft of this file that was committed in `9963908`, which reviewed an earlier working tree.
**[V]** marks facts verified by a command or a file read in this review; **[I]** marks inference.

## Scope read

- Fixture: `tests/stage04/fixtures/corrective/rw_role_collision.csv` and `.json` (25 records, 43 queries, 21 classes),
  generator `corrective/scripts/role_collision_fixture.py`; compared with `docs/verification/stage-04/scripts/
  step8_rw_subset.py`, `tests/stage04/fixtures/step8|step9/rw_subset.json`, `tests/stage02/fixtures/real_cases.json`,
  `docs/sources-and-attribution.md`, and Stage 02 `SPECIFICATION.md` sections 3 and 14.
- Evidence chain: `src/citerift/investigation/dt1.py` (`attached_keys`, `notice_elsewhere`, `role_collided`,
  `discriminating`, `role_ambiguous`, `_d10`), `adapters/detector.py` (`_flags`, `_events`, `lookup_view`,
  `_Run.candidate`), `adapters/lookup.py` (`observe`), `adapters/verify.py` (observation re-validation),
  `retraction/query.py` (`render`, `public_event`), the lookup-observation and lookup-result schemas.
- Census: `corrective/census/role_collision_census.py`, `CENSUS.json`, `pair_census.py`, `PAIR_CENSUS.json`,
  `PAIR_CENSUS_LENIENT.json`, `corrective/frozen_dt1.py`, `ROOT_CAUSE.md` sections 1 to 4b.
- Oracle: `simulations/stage04/oracle-dt2/MANIFEST.json`, `decision_space_dt2.py` (`model_digest`), the frozen
  `simulations/stage04/oracle/`, `corrective/simulation/decision_space_dt2_summary.json`.
- Network and source reads: every `.py` under `corrective/` and `freeze-2/`, the dt-2 simulations and the corrective
  tests.

## Method

1. `uv run pytest tests/stage04/test_corrective_role_collision.py -q -p no:cacheprovider` on the reviewed tree:
   `59 passed in 4.02s` [V].
2. Fixture regeneration from the pinned snapshot into the scratchpad (never into the repository). The scratch copy of
   `retraction_watch.csv` has SHA-256 `2f116e9f…0a655`, the receipt's value [V]. `role_collision_fixture.py --csv <it>
   --index <pinned rw-2f116e9ffed718e6.sqlite> --out-dir <scratch>` printed `{"fixture_records": 25, "queries": 43,
   "subset_equals_full_index": true}`. The output CSV (`339744e0…5c4c`) and JSON (`9dab82cc…d245`) are byte-identical
   to the committed files [V]. The generator was run from a copy that differs from the committed one only in
   formatting (`diff` shows reflowed comprehensions and a `noqa` comment). An earlier version (22 records) also
   reproduced byte for byte.
3. Census reproduction on the pinned index with the reviewed tree. `role_collision_census.py` gives an output
   byte-identical to `CENSUS.json` (`f7df2fa1…eccb`). `pair_census.py` (strict) is byte-identical to
   `PAIR_CENSUS.json` (`7331939c…4a74`; 31,756 pairs, 1,570 changed). `pair_census.py --variant lenient` is
   byte-identical to `PAIR_CENSUS_LENIENT.json` (`a5ebc2c7…9b37c`; 881 changed) [V].
4. Probe (a pytest file in the scratchpad) covering the 21 class queries and the 8 single keys of `en-39868218`. It
   compared the complete dt-2 lookup views of each query (state, projection form, basis reasons, budget refusal,
   `notice_hits`, and for every event the type, `matched_by`, `linked_via`, original keys and flags, plus the PMID
   collision count) and the dt-2 decisions. The full pinned index and an index built from the fixture alone agree:
   `QUERIES 29 DIFFS []` [V].
5. Probe: ran `en-39868218` end to end on the fixture index (`test_step9_real.Run`) and listed the evidence set of the
   `10.1002/asi.23238` claim [V]. Also decided the historical committed observation `1f1774a3ae64b681…` with the
   current `lookup_view` and `dt1.decide`. I extracted that observation from `evaluation-campaign/run/
   run-archive.tar.gz` into the scratchpad; its canonical content hash starts `1f1774a3ae64b681` [V].
6. Hashes and `git diff --quiet f207bc0 HEAD` over the frozen oracle, `dt1_reference.py`, `decision_space.py`,
   `stage02_abstraction.py`, `src/citerift/retraction`, `tests/stage02`, the Step 8 and Step 9 fixtures, `evaluation/`
   and `evaluation-campaign/` [V]. Ran `git rev-parse b5bf8ed:src/citerift/investigation/dt1.py` [V].
7. Text search of the correction's code for network clients and subprocess calls [V].

No repository file was modified except this one. The full index was only opened read-only.

## Findings

### D-01 — MEDIUM — Fixture record cap and attribution say 200, against the accepted 120-record boundary

Evidence [V]: Stage 02 `SPECIFICATION.md:92-94` (accepted, design decision [D]) says "committed fixtures contain at most
120 records' selected fields with attribution", and `:747` repeats "at most 120 attributed real records". Every earlier
fixture follows that limit: `step8_rw_subset.py` has `MAX_RECORDS = 120`, and the Stage 02, Step 8 and Step 9
attributions say "at most 120 records". The corrective generator sets `MAX_RECORDS = 200`
(`role_collision_fixture.py:43`). Its attribution, which is copied into the committed manifest, says "selected fields of
at most 200 records" (`:47`). D-071 sets no record limit. The fixture actually holds 25 records, and the four committed
Retraction Watch fixtures together hold 100 distinct Record IDs [V], so no limit is exceeded today.
Impact: the public attribution text contradicts an accepted distribution boundary. The guard would also let a later
regeneration (more classes were added in this cycle already) pass 120 without an owner decision.
Recommendation: set `MAX_RECORDS = 120` and the attribution to "at most 120 records", then regenerate (the CSV bytes do
not change, only the manifest). Alternatively, get an explicit owner decision for a different limit. Consider
also guarding the total across all committed fixtures (100 today, close to 120).

### D-02 — MEDIUM — The pair census does not name the index it was computed on, and neither census names its code

Evidence [V]: the strict and lenient `PAIR_CENSUS*.json` files hold only `census`, `shard`, `variant`, `pairs`,
`transitions` and `changed`. Neither file names the snapshot, the artifact, semantic or source digests, the dt-2 table
or engine version, or the frozen blob (`pair_census.py`, output dict). `CENSUS.json` does record the index identity
(see D-08), but it does not name the table, engine or frozen blob either. These files are the evidence behind
`ROOT_CAUSE.md` section 4b and the strict/lenient alternative put to the owner. Today they reproduce byte for byte on
the pinned index with the reviewed code (Method 3). [I] A reader of the file alone still cannot tell which snapshot
and which table produced it, and the lenient file comes from a run in which `dt1.discriminating` was monkeypatched.
Recommendation: add an `index` block to both pair-census outputs (same fields as `CENSUS.json`). Add `table_version`,
`engine_version`, the frozen commit and blob (`frozen_dt1.FROZEN_COMMIT`, `FROZEN_BLOB`) and the code commit to all
three census outputs. Mark the lenient output `"production_semantics": false` or similar.

Resolved since the draft (earlier draft D-02, the census "frozen dt-1" column computed with the working-tree table):
`role_collision_census.py` and `pair_census.py` now decide the frozen column with `frozen_dt1.decide`. That module loads
`b5bf8ed:src/citerift/investigation/dt1.py` by blob `27409702a03f…` (`git rev-parse` confirms [V]), re-hashes the bytes
before executing them, and checks `TABLE_VERSION == "dt-1"`. The frozen column now reproduces (Method 3), and its DOI
same-record values (D-14 positives: 13,489 RETRACTED, 53 CONCERN, 18 CORRECTION; 108 D-11) equal those of the earlier
census file that I read in the first pass.

### D-03 — LOW — docs/sources-and-attribution.md lists only the Stage 02 extract

Evidence [V]: `docs/sources-and-attribution.md:10` names only `tests/stage02/fixtures/rw_real_subset.csv` ("69
records") as a committed extract. A search for `rw_subset`, `rw_role_collision` or `stage04/fixtures` finds nothing,
although the file's own rule (line 3) is that a stage adding a source "records it here". The Step 8 and Step 9
omissions predate this cycle; the correction adds a third undeclared extract.
Recommendation: extend the row to list every committed Retraction Watch extract with its manifest: Stage 02 69, Step 8
6, Step 9 6, corrective 25; 100 distinct records in total.

### D-04 — LOW — The method says "first in sorted order", but 11 of 21 classes use snapshot order

Evidence [V]: the docstring (`role_collision_fixture.py:4`) and the manifest's `method` say each key is "the **first in
sorted order** among the keys of its class". Seven classes do use `_first`, which takes the smallest key (the four
`same_doi_*`, `same_pmid` and both `cross_record_*`). `doi_and_pmid_collided_in_two_records_pair` takes the first
sorted pair. Eleven classes use `pick()`, which is `min(rows, key=event_id)` (`:143-144`); event ids are
`ev-<ordinal>`, so `pick()` takes the first event in snapshot file order, not the smallest key.
`contradictory_source_rows` takes the first sorted DOI whose Stage 02 projection is `conflicting`; that filters on a
Stage 02 outcome, not a Stage 04 engine outcome, so the "never … an outcome of the engine" claim holds. The JASIST key
is chosen by name, as the method states. All choices are deterministic and rule-based, none uses a title, journal or
label, and regeneration is byte-identical (Method 2).
Recommendation: state the rule exactly: "first in sorted key order, or, for the event-defined classes, the event with
the lowest snapshot ordinal". Name the classes that use each rule.

### D-05 — LOW — The fixture manifest records less than the Step 8/9 convention

Evidence [V]: in the Step 8 and Step 9 manifests, `source` carries `bytes`, `commit`, `path`, `repository`, `sha256`
and `url`, and the manifest also has `outcomes_sha256`. The corrective manifest's `source` has only `commit`, `sha256`
and `url`. No fixture manifest, including Step 8/9, names the full index used for selection. The pinned commit
`a987928a816e…` and SHA-256 `2f116e9f…0a655` match the receipt and `docs/sources-and-attribution.md` [V].
Recommendation: emit the receipt's full `source` block as Step 8 does, and add the selection index's
`artifact_digest` and `semantic_digest` (`adcf7b65…`, `7b2a2344…`).

### D-06 — INFO — "subset_equals_full_index" holds for its queries but is narrower than its name

Evidence [V]: the generator compares the 43 listed queries only. It compares state, role, identity, status, value,
dates, event count and types, record ids, notice-hit record ids (from the rendered list, which is capped at 100),
issues, and the two same-record collision flags. It does not compare `notice_hit_count` itself, other event flags,
`matched_by`, `linked_via`, the notice identifiers that `dt1.discriminating` now reads, or basis reasons. My probe
(Method 4) covers the dt-2 inputs for 29 queries and finds the views and decisions identical. [I] The claim does not
cover queries outside the list.
Recommendation: name the field `subset_equals_full_index_for_listed_queries`, or document that scope. Add
`notice_hit_count`, each event's full flag list and its `notice_doi`/`notice_pmid` to the compared fields, so that the
manifest itself vouches for every dt-2 input.

### D-07 — INFO — The IDENTIFIER_ROLE_COLLISION abstention can be re-derived from committed inputs

Evidence [V]:
- `lookup_view` reads event flags, `notice_doi` and `notice_pmid` from the observation's top-level `events`
  (`detector.py:63` and following) and `notice_hit_count` from `result` (`detector.py:106-107`). The observation schema
  requires `flags`, the notice fields and `notice_hit_count`. LOOKUP validates each observation when it writes it
  (`adapters/lookup.py:308`), and VERIFY validates it again (`adapters/verify.py:269`). A missing or malformed `flags`
  value is now read as both same-record flags (`_flags`, `detector.py:44-50`), and a missing count is read as "may be a
  notice". Both fail closed.
- D-10 sets `upstream_role` to the deciding lookup. The claim's evidence set therefore holds `/result` of every lookup
  of the candidate (which carries `notice_hit_count` and `notice_hits`) and `/events/k` of every event of the deciding
  lookup (which carries the flags and notice identifiers). For the JASIST claim on the reviewed tree, the set holds
  `/result` (query `10.1002/asi.23238`, `notice_hit_count` 0) and `/events/0` (record 40120, flags
  `["NOTICE_DOI_EQUALS_ORIGINAL"]`, `matched_by` doi). The supporting count is 8, and VERIFY passes in the end-to-end
  test.
- The historical committed observation `1f1774a3…` from the failed run, decided by the reviewed code, gives
  `dt-2 D-10 UNRESOLVED_IDENTITY ('IDENTIFIER_ROLE_COLLISION',)`. In the pinned index, record 40120 is raw-record
  ordinal 33558 and event `ev-0033558`, as `ROOT_CAUSE.md` states.
Residual points:
- Evidence items point at whole events and results, not at `/events/k/flags` or `/result/notice_hit_count`, so the
  claim does not say which key or flag triggered the collision. A reader has to re-run dt-2.
- `role_collided` now scans the events of every lookup of the candidate, but only the deciding lookup's events are
  cited at `/events/k`; the other lookups are cited at `/result` only. [I] For a PAIR, Q2 normally returns the events of
  both single-key lookups, so the triggering flag is still among the cited events, but no check enforces this.
Recommendation (optional): add field-level items at `/events/k/flags` of each role-ambiguous event, and at
`/result/notice_hit_count` of each collided cited key's lookup, including the events of a non-deciding lookup whose
flag set `role_collided`.

### D-08 — INFO — The single-key census records the index identity and is read-only

Evidence [V]: the `index` block of `CENSUS.json` records `snapshot_id` `rw-2f116e9ffed718e6`, `artifact_digest`
`adcf7b65…`, `semantic_digest` `7b2a2344…`, `source_sha256` `2f116e9f…0a655` and `policy_version`
`citerift-rde-policy/1.3.0`. These equal the `meta` table of the pinned index and the values in
`freeze/d062/two_build_equivalence.json` and the vertical-slice report manifests. Both census scripts open SQLite with
`mode=ro` and query through `Index` (`mode=ro&immutable=1`), and they write only their output file. The digests are
copied from the stored `meta` table, not recomputed. That is acceptable given the match with the freeze records.
Recommendation (optional): run the Stage 04 index identity verifier first and record that it passed.

### D-09 — INFO — Oracle dt-2 pins the frozen oracle and its model; the frozen material is untouched

Evidence [V]: in `oracle-dt2/MANIFEST.json`, `frozen_dt1_oracle_manifest_sha256` `4110507728…7735` equals the
`sha256sum` of `simulations/stage04/oracle/MANIFEST.json`. `model_digest` `d01f3438…56ca` equals
`decision_space_dt2.model_digest()` recomputed on the reviewed tree (over `dt2_reference.py` and
`stage02_abstraction.py`, as in dt-1). The hashes of the decisions file and the table file match the manifest, and the
summary JSON carries the same two digests. `git diff --quiet f207bc0 HEAD` is clean for the frozen oracle,
`dt1_reference.py`, `decision_space.py`, `stage02_abstraction.py`, `src/citerift/retraction`, `tests/stage02`, the
Step 8/9 fixtures, `evaluation/` and `evaluation-campaign/`.
Two points for the semantics reviewers:
- As in dt-1, `decision_space_dt2.py` (the enumeration) is outside `model_digest`; only the table digest covers it.
- The oracle treats the role collision as an abstract input `rc`. The revisions after reviews A, B and E changed how
  production computes it (`role_collided` across lookups, `discriminating`), but the model digest is unchanged. [I] The
  oracle therefore checks the D-10 placement, not the derivation of `rc`, which only the suites and the censuses check.

### D-10 — INFO — No network access and no unpinned source

Evidence [V]: the correction's code contains no HTTP or socket client. The only matches for the search pattern are the
URL and the word "requests" in the attribution text. `subprocess` runs only local `git` (`frozen_dt1.py`,
`regress.py`, the freeze-2 builders, `logical_view_diff.py`), the local investigation CLI (`s13_run_v2.py`) and local
`python -I` scripts. The fixture generator refuses a CSV whose SHA-256 differs from the receipt's (`check_bytes`). The
censuses and the tests read only the pinned index or the committed fixture. The end-to-end test runs under
`NoNetwork` and records zero network attempts. One minor point: the generator's conflicting-key scan is quadratic in
events, so a regeneration takes about 10 minutes on one core (duration [V], cause [I]).

## Verdict

There is no CRITICAL or HIGH provenance finding. The fixture is attributed, pinned and selected by rule. It stays
within the record limit in practice and reproduces byte for byte, as do both censuses. The dt-2 abstention can be
re-derived from committed inputs. Two MEDIUM findings should be fixed before the refreeze: the cap and attribution say
200 against the accepted limit of 120 (D-01), and the census outputs do not name their snapshot (pair census) or code
identity (D-02).
