# Corrective cycle review D: source provenance

Reviewer D (fresh, independent; did not write the correction). Brief: `REVIEW_BRIEF.md`. Working tree on top of
`f207bc0`, reviewed 2026-11-18. Facts marked **[V]** were verified by a command or a file read in this review;
**[I]** marks inference.

## Scope read

- Fixture: `tests/stage04/fixtures/corrective/rw_role_collision.csv`, `.json`; generator
  `docs/verification/stage-04/corrective/scripts/role_collision_fixture.py`; compared with
  `docs/verification/stage-04/scripts/step8_rw_subset.py`, `tests/stage04/fixtures/step8|step9/rw_subset.json`,
  `tests/stage02/fixtures/real_cases.json`, `docs/sources-and-attribution.md`, Stage 02 `SPECIFICATION.md` sections 3
  and 14.
- Evidence chain: `src/citerift/investigation/dt1.py` (dt-2 diff), `adapters/detector.py` (`_events`, `lookup_view`,
  `_Run.candidate`), `adapters/lookup.py` (`observe`), `adapters/verify.py` (observation re-validation),
  `retraction/query.py` (`render`, `public_event`), `schemas/investigation/v1/lookup-observation.schema.json`,
  `schemas/retraction/v1/lookup-result.schema.json`.
- Census: `corrective/census/role_collision_census.py`, `CENSUS.json`, `ROOT_CAUSE.md` sections 1 to 3.
- Oracle: `simulations/stage04/oracle-dt2/MANIFEST.json`, `decision_space_dt2.py` (`model_digest`), frozen
  `simulations/stage04/oracle/`, `corrective/simulation/decision_space_dt2_summary.json`.
- Network and source reads: every `.py` under `corrective/`, `freeze-2/exposure/`, the dt-2 simulations and the
  corrective tests.

## Method

1. `uv run pytest tests/stage04/test_corrective_role_collision.py -q -p no:cacheprovider` → `49 passed in 33.06s` [V].
2. Regenerated the fixture from the pinned snapshot into the scratchpad (not the repository): the CSV in the
   scratchpad has SHA-256 `2f116e9f…0a655` (the receipt's) [V]; `role_collision_fixture.py --csv <pinned CSV> --index
   <pinned index rw-2f116e9ffed718e6.sqlite> --out-dir <scratch>` printed `{"fixture_records": 22, "queries": 39,
   "subset_equals_full_index": true}`, and `cmp` reported both the regenerated `rw_role_collision.csv` (SHA-256
   `c710ff1d…f0e6`) and `rw_role_collision.json` (SHA-256 `5a7d40f9…3ce6`) byte-identical to the committed files [V].
3. Probe (scratch pytest file): for the 17 class queries and the 8 single keys of `en-39868218`, the complete dt-2
   lookup views (state, projection form, basis reasons, budget refusal, `notice_hits`, every event's type,
   `matched_by`, `linked_via`, original keys and flags, PMID-collision count) and the dt-2 decisions are equal on
   the full pinned index and on an index built from the fixture alone: `QUERIES 25 DIFFS []` [V].
4. Probe: ran `en-39868218` end to end on the fixture index (`test_step9_real.Run`) and listed the evidence set of
   the `10.1002/asi.23238` claim [V]; decided the **historical committed** observation
   `1f1774a3ae64b681…` (extracted from `evaluation-campaign/run/run-archive.tar.gz` into the scratchpad; its canonical
   content hash starts `1f1774a3ae64b681`) with the current `lookup_view` + `dt1.decide` [V].
5. Probe: called the committed census function `frozen_class(index, "doi", "10.1002/asi.23238")` on the pinned index
   with the current tree [V].
6. Hashes and `git diff --quiet f207bc0` on the frozen oracle, `dt1_reference.py`, `decision_space.py`,
   `stage02_abstraction.py`, Stage 02 code and fixtures, Step 8/9 fixtures and the campaign directories [V].
7. Text search for network clients and subprocess use in the correction's code [V].

No repository file was modified except this one. The full index was opened read-only only.

## Findings

### D-01 — MEDIUM — Fixture record cap raised to 200 against the accepted 120-record distribution boundary

Evidence [V]: Stage 02 `SPECIFICATION.md:92-94` (accepted, design decision [D]): "committed fixtures contain at most
120 records' selected fields with attribution"; `:747` repeats "at most 120 attributed real records". All earlier
fixtures follow it (`step8_rw_subset.py` `MAX_RECORDS = 120`; Stage 02, Step 8 and Step 9 attributions say "at most
120 records"). The corrective generator sets `MAX_RECORDS = 200` (`role_collision_fixture.py:43`) and its attribution,
copied into the committed manifest, says "selected fields of at most 200 records" (`:47`). D-071 does not mention a
record limit. Actual use is 22 records; the union of all four committed Retraction Watch fixtures is 97 distinct
Record IDs [V], so no boundary is actually exceeded today.
Impact: the public attribution text states a limit that contradicts an accepted distribution boundary, and the guard
would let a later regeneration exceed it without an owner decision.
Recommendation: set `MAX_RECORDS = 120` and the attribution to "at most 120 records" (regenerate; the CSV bytes do not
change, only the manifest), or obtain an explicit owner decision for a different limit. Consider also asserting the
aggregate across all committed fixtures (currently 97).

### D-02 — MEDIUM — The census's "frozen dt-1" column is not reproducible from the committed tree

Evidence [V]: `role_collision_census.py:30` imports the working-tree `citerift.investigation.dt1` and labels its result
`frozen_dt1_outcome` (`:179`); the docstring says "with the frozen dt-1 code". In the corrected tree that module is
dt-2. Running the committed function now on the pinned index gives
`dt-2 {'rule': 'D-10', 'class': 'UNRESOLVED_IDENTITY', 'reasons': ['IDENTIFIER_ROLE_COLLISION'], …}` for the JASIST
key, whereas `CENSUS.json` reports D-14 positives for that class. `CENSUS.json` records no table version, engine
version or code commit. [I] The committed `CENSUS.json` is nevertheless a genuine dt-1 result: its mtime (20:19:28)
precedes the dt-2 edit of `dt1.py` (20:33:10), and its content (13,560 D-14 positives among same-record DOI keys) is
only possible under dt-1. `ROOT_CAUSE.md:32` ("reproduced with the census tool on the same index") is true only at
`f207bc0`. By contrast `corrective/regression/regress.py:58-71` loads the frozen `dt1.py` from git (`b5bf8ed`) and
checks `TABLE_VERSION == "dt-1"`, which is the right pattern.
Recommendation: load the frozen table from git in the census as `regress.py` does (or refuse unless
`dt1.TABLE_VERSION == "dt-1"`), write `table_version`, engine version and the code commit into `CENSUS.json`, rerun,
and confirm the output equals the committed file (SHA-256 `292007d1…c71f`, verified [V]) apart from the added fields.

### D-03 — LOW — docs/sources-and-attribution.md does not list the corrective fixture (nor the Step 8/9 ones)

Evidence [V]: `docs/sources-and-attribution.md:10` names only `tests/stage02/fixtures/rw_real_subset.csv` ("69
records") as the committed extract; a search for `rw_subset`, `rw_role_collision` or `stage04/fixtures` finds nothing.
The file's own rule (line 3): "A stage that adds a source … records it here". The Step 8 and Step 9 omission predates
this cycle; the correction adds a third undeclared extract.
Recommendation: extend the row to list all committed Retraction Watch extracts (Stage 02: 69; Step 8: 6; Step 9: 6;
corrective: 22; union 97), each with its manifest path.

### D-04 — LOW — Selection description says "first in sorted order"; 8 of 17 classes use snapshot order

Evidence [V]: docstring `role_collision_fixture.py:4` (and the manifest's `method`) says each key is "the **first in
sorted order** among the keys of its class". `_first` sorts keys for 7 classes (the four `same_doi_*`, `same_pmid`,
both `cross_record_*`), but 8 classes use `pick()` = `min(rows, key=event_id)` (`:143-144`); event ids are
`ev-<ordinal>`, i.e. the first event in snapshot file order, not the smallest key. `contradictory_source_rows` is the
first sorted DOI whose Stage 02 projection is `conflicting` (`:136-141`), a filter on a Stage 02 outcome (not a Stage
04 engine outcome, so the "never … an outcome of the engine" claim holds). All choices are deterministic and
rule-based; reproduction is byte-identical (Method 2). No class is defined by a title, journal or label [V].
Recommendation: say "first in sorted key order, or the first event in snapshot order (lowest event ordinal) for the
event-defined classes", naming which classes use which.

### D-05 — LOW — Fixture manifest is thinner than the Step 8/9 convention

Evidence [V]: the Step 8/9 manifests' `source` carries `bytes`, `commit`, `path`, `repository`, `sha256`, `url`, plus
`outcomes_sha256`; the corrective manifest's `source` has only `commit`, `sha256`, `url` (`role_collision_fixture.py`
manifest block), no `bytes`, and no record of the full index identity used for selection (also absent in Step 8/9).
Pinned commit `a987928a816e…` and SHA-256 `2f116e9f…0a655` match the receipt and `docs/sources-and-attribution.md` [V].
Recommendation: emit the receipt's full `source` block (as Step 8 does) and the full index's `artifact_digest` /
`semantic_digest` (`adcf7b65…`, `7b2a2344…`) so the selection index is named, not only the CSV.

### D-06 — INFO — "subset_equals_full_index" is sound for its queries but narrower than its name

Evidence [V]: the generator compares, for the 39 listed queries only, state, role, identity, status, value, dates,
event count and types, record ids, notice-hit record ids (from the rendered list, capped at 100), issues and the two
same-record collision flags. It does not compare `notice_hit_count` itself, other event flags, `matched_by`,
`linked_via` or basis reasons. My probe (Method 3) closes that gap for the dt-2 inputs: on 25 queries the complete
dt-2 views and decisions are identical on the subset and the full index. The claim does not extend to queries outside
the list (e.g. lookups of the notice-hit records' own keys) [I].
Recommendation: rename or document as "subset_equals_full_index_for_listed_queries", and add `notice_hit_count` and
the full flag list of each event to the compared fields so the manifest itself carries the dt-2 inputs.

### D-07 — INFO — The IDENTIFIER_ROLE_COLLISION abstention is fully re-derivable from committed inputs

Evidence [V]:
- `lookup_view` reads event flags from the observation's top-level `events` (`detector.py:54`) and
  `notice_hit_count` from `result` (`detector.py:106-107`); both are required by the committed observation schema
  (`flags` in the event `required` list of `lookup-result.schema.json`; `notice_hit_count` required), validated when
  LOOKUP writes (`adapters/lookup.py:308`) and again by VERIFY (`adapters/verify.py:269`).
- D-10 sets `upstream_role` to the deciding lookup, so the claim's evidence set contains `/result` of every lookup of
  the candidate (holding `notice_hit_count` and `notice_hits`) and `/events/k` of every event of the deciding lookup
  (holding `flags`). For the JASIST claim: `/result` (query `10.1002/asi.23238`, `notice_hit_count` 0) and `/events/0`
  (record 40120, `flags ["NOTICE_DOI_EQUALS_ORIGINAL"]`, `matched_by doi`), supporting count 8; VERIFY passed (the
  end-to-end test).
- The historical committed observation `1f1774a3…` from the failed run, decided by the current code, gives
  `dt-2 D-10 UNRESOLVED_IDENTITY ('IDENTIFIER_ROLE_COLLISION',)`; record 40120 is raw-record ordinal 33558 /
  event `ev-0033558` in the pinned index, as `ROOT_CAUSE.md` states.
Residual observations: evidence items point at whole events and results, not at `/events/k/flags` or
`/result/notice_hit_count`, so the claim does not say which key or which flag triggered the collision (a reader must
re-run dt-2) [V]; and a missing `flags` field would read as "no flags" (`e.get("flags") or ()`) while a missing
`notice_hit_count` fails closed. Schema validation at write and VERIFY makes the first unreachable in practice [I].
Recommendation (optional): add a field-level `lookup_event` item at `/events/k/flags` for each role-ambiguous event
and a `lookup_result` item at `/result/notice_hit_count` for each collided cited key; treat a missing `flags` key as
an adapter inconsistency rather than as an empty list.

### D-08 — INFO — Census index identity and read-only access

Evidence [V]: `CENSUS.json` `index` records `snapshot_id rw-2f116e9ffed718e6`, `artifact_digest adcf7b65…`,
`semantic_digest 7b2a2344…`, `source_sha256 2f116e9f…0a655`, `policy_version citerift-rde-policy/1.3.0`, equal to the
pinned index's `meta` table and to the values in `freeze/d062/two_build_equivalence.json` and the vertical-slice
report manifests. The census opens the index with `mode=ro` (`_ro`) and through `Index` (`mode=ro&immutable=1`) and
writes only its output file. The digests are copied from the index's stored `meta`, not recomputed (no
`verify_index_identity`) [V]; acceptable given the match with the freeze records.
Recommendation (optional): call the Stage 04 identity verifier before the census and record that it passed.

### D-09 — INFO — Oracle dt-2 pins the frozen oracle and the model; frozen material untouched

Evidence [V]: `oracle-dt2/MANIFEST.json` `frozen_dt1_oracle_manifest_sha256 4110507728…7735` = `sha256sum
simulations/stage04/oracle/MANIFEST.json`; `model_digest d01f3438…56ca` = `decision_space_dt2.model_digest()`
recomputed now (over `dt2_reference.py` and `stage02_abstraction.py`, the dt-1 convention); the decisions and table
file hashes match the manifest; the summary JSON carries the same two digests. `git diff --quiet f207bc0` is clean for
`simulations/stage04/oracle`, `dt1_reference.py`, `decision_space.py`, `stage02_abstraction.py`,
`src/citerift/retraction`, `tests/stage02`, the Step 8/9 fixtures, `evaluation/` and `evaluation-campaign/`.
As in dt-1, the enumeration module (`decision_space_dt2.py`) is outside `model_digest` and is covered only by the
table digest.

### D-10 — INFO — No network or unpinned source

Evidence [V]: no HTTP or socket client in the correction's code; the only URL is the attribution text. `subprocess`
appears only for local `git` (`regress.py`, `build_exposure_manifest.py`), the local investigation CLI
(`s13_run_v2.py`) and a local `python -I` rule script. The fixture generator refuses a CSV whose SHA-256 is not the
receipt's (`check_bytes`); the census and the tests read only the pinned index or the committed fixture. The end-to-end
test runs under `NoNetwork` with zero attempts. Minor: the generator's conflicting-key scan (`:136-140`) is quadratic
in events, so a regeneration takes about 10 minutes on one core [V for duration, I for cause].

## Verdict

No CRITICAL or HIGH finding: the fixture is attributed, pinned, rule-selected, within the record limit in fact and
reproducible byte for byte; the dt-2 abstention is re-derivable from committed inputs. Two MEDIUM provenance defects
(D-01 cap and attribution at 200 against the accepted 120; D-02 census not reproducible as "frozen dt-1" from the
corrected tree) should be fixed before the refreeze.
