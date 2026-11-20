# Final corrective cycle: independent review D (provenance, versioning, evaluation leakage, exposure)

Reviewer D. Branch head `de7dcc2` (`git log --oneline -6`: `de7dcc2`, `49e7187`, `1b0670a`, `59f2ad0`, `6663314`,
`ab7aa9c`). The only change in the working tree is the untracked `final-cycle/review/` folder. [V]

## Scope read

- `REVIEW_BRIEF.md`; `DECISIONS.md` D-074 and D-083; `CLAUDE.md`.
- Versioning: `src/citerift/investigation/__init__.py`, `adapters/plan.py`, `adapters/detector.py`,
  `adapters/detect.py`, `adapters/normalize.py`, `adapters/lookup.py`, `bibliographic.py` (profile loading),
  `data/bib-profile-1.json`, `explanations.py`, `dt1.py` (header and identity), and every schema diff since `6663314`.
- E-07: `fold.py`, `errors.py`, `operations.py`, `controller.py`, `memory.py` (`InvestigationMemory.open`),
  `tests/stage04/test_corrective_compat.py`.
- D-05 / N-01: `tests/stage04/test_final_lows.py`, `fixtures/corrective/rw_role_collision.json`,
  `corrective/scripts/role_collision_fixture.py`, `final-cycle/fc_provenance.py`, `regression/regress.py`,
  `scripts/a04_invariant.py`, `scripts/c07_profile.py`, `fail-first/fail_first.py`, `identity/logical_view_diff.py`,
  and the committed final-cycle outputs.
- The separate commit `1b0670a` (`test_p2_evaluation.py`, `test_step13_evaluation.py`) and `p2_common.engine_check`.
- Leakage and exposure: `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2, `BIBLIOGRAPHIC_SPEC.md` 2.2 and 4.2,
  `corpus/build_corpus.py`, the v2 and v3 exposure builders.
- Historical immutability: the `git diff` checks in item 6; `review/step7/d053`, `d055`, `closure`; and
  `final-cycle/bounds/bounds.json`.

## Method

I read the code and evidence and ran these targeted commands only. None used the network, none ran the full suite,
and no tracked file was changed:

- `uv run pytest tests/stage04/test_corrective_compat.py tests/stage04/test_final_lows.py -q`: `9 passed in 0.73s`.
- `uv run pytest tests/stage04/test_p2_evaluation.py -k "engine or manifest or runner_refuses or current_engine"`:
  `19 passed, 21 deselected in 5.08s`. The test's temporary worktree was removed afterwards (`git worktree list`).
- Probes of the E-07 guard on modified copies of the freeze-2 VS-6a first record, held in memory.
- A rerun of `fail_first.py` on this tree and on a clean `6663314` worktree, written to the scratchpad.
- An in-memory run of the v3 exposure `build()` and `covers_superseded()`, written to the scratchpad. The builder's
  `main()` refuses the tree because of the untracked review folder.
- A computation of the maximal evidence-item and candidate-entry sizes with the cycle's own `storage_bounds` and
  `d055/part_ceiling` modules.
- Reads of the key names in `LOCK.json`, `DRAW.json` and the packets. No label values were read.

## Findings

### D-01 HIGH: a committed P2 pre-registered file states as decided an owner decision that is still pending

- [V] `tests/stage04/test_p2_evaluation.py:115` reads: "Owner decision on the final corrective cycle (D-083 card,
  "Amend both, D-074 style"): ...". The message of commit `1b0670a` says "(pending owner decision card)" and "revert it
  if the owner keeps both files byte-identical". The brief says the amendment is pending an owner decision.
- [V] `DECISIONS.md` ends at D-083, and D-083 says nothing about amending these tests. `grep -rn "Amend both"` finds
  only this comment. No owner message id is cited.
- [V] This file is one of the 28 files of the P2 pre-registration manifest. The amended test itself asserts that it is
  the only listed file that differs, and my hash comparison confirms it: `changed in tree:
  ['tests/stage04/test_p2_evaluation.py']`.
- Why it matters: CLAUDE.md forbids recording an owner decision without a reference to the owner's own words. D-083
  says "neither historical evaluation is modified", so whether a P2 pre-registered file may change is exactly what
  the owner has to decide.
- Recommendation: until the owner decides, reword the comment to "pending owner decision (card <id>); proposed: amend
  in the D-074 style". After the decision, record it as D-0xx with the owner's message id and cite that id in the
  comment. Freeze-3 must not be cut while the comment claims a decision that does not exist.

### D-02 MEDIUM: the alias profile is not part of the engine identity, although two documents say it is

- [V] `BIBLIOGRAPHIC_SPEC.md:60` says: "The profile file `src/citerift/investigation/data/bib-profile-1.json` is part
  of the engine identity." `BUILD_VS_ADOPT.md` section 4 says: "(the profile digest, part of the engine identity, would
  change)". Its table row says "a profile file in the engine identity".
- [V] `bibliographic.profile_identity()` (`bibliographic.py:222`) is not called anywhere in `src/` or `tests/`.
  `STAGE04_IDENTITY` (`adapters/plan.py:49-54`) holds only `engine_version`, `table_version`, `plan_version` and
  `schema_version`, and `common.schema.json` `stage04_identity` has `additionalProperties: false`. No test pins the
  file's SHA-256 (`450f17a2…808f`).
- [V] `test_final_bib.py:63` compares the production profile with `simulations/stage04/bib-reference-profile.json`
  as sorted alias sets. Changing both files together passes.
- [I] An edit to the profile without an engine version bump would not make an investigation STALE. It would surface
  only as a `NORMALIZE_REPLAY` failure in VERIFY (`adapters/verify.py:286`), which is the "replay mismatch only"
  outcome that `plan.py:44-47` says the identity exists to prevent. Stage 03 records a profile digest in its
  extraction identity (SPEC 10.3), so the analogy the documents draw does not hold for Stage 04.
- Recommendation: either pin the profile, for example with a test asserting `sha256(bib-profile-1.json)` together
  with `__version__ == "0.4.0"` so that any profile change forces a version bump, and delete or use
  `profile_identity()`; or correct both documents. Adding a profile digest to `stage04_identity` would be a schema
  change that needs its own version.

### D-03 MEDIUM: N-01 is only partly closed, so a result can still be recorded from uncommitted code without a flag

- [V] `fc_provenance.provenance()` is used by three tools only: `regress.py`, `a04_invariant.py` and `c07_profile.py`.
  Only the `regress.py merge` step refuses a result whose `uncommitted` list is not empty (`regress.py:294`).
  `a04_invariant.py:105` and `c07_profile.py:139` record the list and write the result anyway.
- [V] None of the committed final-cycle results carries provenance:
  - `lows/a04_invariant_census.json` has no `provenance` key (keys: `exposure_*`, `invariant`, `keys_decided`,
    `positives_by_class`, `rules`, `table_version`, `violations`). It was committed in `59f2ad0`, before provenance
    was added in `49e7187`.
  - `fail-first/decided_by_dt3_engine.json` records only `engine: "0.4.0"`, with no commit and no dirty check.
  - `identity/LOGICAL_VIEW_DIFF.json` records only `old_root_head`; the new side has no commit.
  - `bounds/bounds.json` and `survey_pairs.py` have no provenance.
- [V] Nothing checks that a recorded `code_commit` still has the same `CHECKED` trees as the head the result is
  frozen with. `regress merge` checks only that the shard commit equals HEAD at merge time.
- [V] `CHECKED` (`fc_provenance.py:22-31`) leaves out inputs a result depends on: the bundles under
  `evaluation*/`, `corrective/regression/*.json` (which `regress.py` cross-checks against), and
  `review/step7/{closure,d053,d055}` (the generators behind `final-cycle/bounds/bounds.json`). Gitignored files
  (`*.py[cod]`) are invisible to `git status`. That last point is theoretical.
- Mitigation:
  - [V] My rerun of `fail_first.py` reproduces both fail-first outputs byte for byte (`cmp`: IDENTICAL for dt-3 at
    this tree and for dt-2 at `6663314`).
  - [V] `LOGICAL_VIEW_DIFF.json` and `bounds.json` are compared with recomputations by `test_d053_d054.py` and
    `test_d055.py`.
  - [I] The A-04 census has not been re-verified by anyone since `59f2ad0`. `src` has not changed since then
    (`git diff --stat 59f2ad0 HEAD -- src schemas simulations`: only three test files).
- Recommendation:
  - Make `a04_invariant.py` and `c07_profile.py` exit non-zero when `uncommitted` is not empty.
  - Add `fc_provenance` to `fail_first.py`, to the new side of `logical_view_diff.py`, to `survey_pairs.py` and to the
    bounds generator.
  - Regenerate the A-04 census at the freeze-3 candidate.
  - Add a test that every committed final-cycle JSON result has an empty `uncommitted` list and a `code_commit` whose
    `CHECKED` trees equal HEAD's, or record bundle and input digests.
  - Put the `review/` folder outside `CHECKED`, so that review files do not make every result "uncommitted".

### D-04 MEDIUM: the amendment leaves part of P2's identity-guard proof vacuous at HEAD

- [V] The parametrized test `test_engine_check_refuses_any_scientific_engine_mismatch` (`test_p2_evaluation.py:185-207`)
  was not moved into the historical worktree. Its five identity mutations (`table_version`, `engine_version`,
  `schema_version`, `claim_schema_version`, `detector_identity`) now raise whether or not anything is mutated. The
  amended `test_the_current_engine_is_not_the_freeze2_engine` itself asserts that `C.engine_check(PARAMS)` raises on
  the unmutated identity in this tree.
- [V] The same holds in `test_runner_refuses_another_engine_before_any_article`: the
  `table_version="dt-1"` mutation is vacuous, because the amended test also asserts that `RN.frozen_check(PARAMS)`
  raises.
- [V] The `content_commit`, `tree` and `freeze_manifest_digest` mutations stay meaningful, because those checks run
  before the identity check (`p2_common.py:50-59`).
- [V] The pre-amendment `test_engine_check_refuses_a_changed_engine_tree` exercised the "committed tree differs"
  branch (`bad`, `p2_common.py:80`) through a faked `rev-parse HEAD:src`. Its replacement exercises only the
  "uncommitted change" branch (`dirty`). The `bad` branch is now untested.
- [V] Everything else in the amendment holds against the pre-amendment tests:
  - P2 resolves to the exact manifest text at `10cc9d8`, with digest `5d323a67…`.
  - Every listed file hashes, at `10cc9d8`, to its recorded SHA-256.
  - Only this test file differs in the tree.
  - P2's own `engine_check`, `frozen_check` and `MF.build()` pass at `10cc9d8`. The probe proves that `citerift` was
    imported from the worktree. `uv.lock` and `pyproject.toml` are unchanged since `10cc9d8`.
  - A tampered `dt1.py` is refused there.
  - The `test_step13_evaluation.py` change is a docstring and `dt-2`→`dt-3` only, already under D-074's
    "P identified by its historical commit".
- Recommendation: run the eight mutation cases, and one `bad`-branch case (the probe can monkeypatch `C.git` inside the
  subprocess), through `HISTORICAL_PROBE` in the P2 worktree. That gives each case its own reason for failing.

### D-05 MEDIUM: the "D-055 bounds re-proved" evidence still uses the dt-2 evidence-item maximum and count

- [V] `final-cycle/bounds/bounds.json` gives `journal.entry_bytes.maximal["evidence item"] = 27477` and
  `entries_per_run["evidence item"] = 510000`. Both come from the historical `d053/part_ceiling.json`
  (`d055/bounds.py:101,117,155-158`).
- [V] The cycle's own updated `storage_bounds._evidence("cited_bibliography")` measures **50,412 bytes**, and
  `lookup_record` measures 25,328 bytes. The D-053 count of 510,000 per run counts neither the new `cited_bibliography`
  items (up to one per unit, 20,000) nor the `lookup_record` items (one per event of the deciding lookup).
- [V] The largest D-13a candidate entry is 42,697 bytes and the sum of field maxima is 49,114 bytes, which is
  covered.
- [I] The conclusion still holds. About 810,000 items × 50,412 B ≈ 40.8 GB of entries gives about 4,900 batch
  records of about 540 B, roughly 2.7 MB of journal, against a 512 MiB limit. The evidence part ceiling
  (`MAX_PART_BYTES` = 8 MiB ≥ 50,559 B) also holds. But the retained file states numbers that are not the dt-3
  maxima, and `test_d055.py` only compares the file with the same stale computation.
- Recommendation: derive the maximal evidence item and the count per run from the dt-3 kinds (a final-cycle
  `part_ceiling` record), regenerate `bounds.json` with provenance, and assert the new maximum in `test_d055.py`.

### D-06 LOW: the E-07 guard classifies a tampered first record as another engine's (STALE) before any integrity check

- [V] `engine_identity_differs` runs at `fold.py:634-637`, before the schema and before the M-2 `prev`/`digest`
  checks (`fold.py:655-658`). My probes on the freeze-2 VS-6a first record gave:

  | Change to the first record | Code |
  |---|---|
  | Garbage version strings (`"garbage"`, `"x"`) | `ENGINE_IDENTITY_DIFFERS` |
  | Broken `digest` and `prev` | `ENGINE_IDENTITY_DIFFERS` |
  | `schema_version` set to null | `RECORD_INVALID` |
  | `stage04` block removed | `RECORD_INVALID` |
  | dt-3 and 5.0.0 with engine 0.3.0 | `CHAIN_BROKEN` |

- This is not a bypass. [V] Every case is refused. Non-string or missing identity fails closed as CORRUPT. A later
  foreign record fails the schema and is CORRUPT. `test_e07_a_reused_memory_root…` proves exit 11 and an unchanged
  tree, and `Memory.open` validates before any repair (`memory.py:262-279`). [I] But corruption of the first record
  is reported as "stale, created by another engine" (exit 11) instead of CORRUPT (exit 12).
- Recommendation: verify the first record's schema-independent integrity (`prev` equals the genesis value and
  `digest` recomputes) before the guard, or restrict the guard to the known historical pairs (`dt-1`/`3.0.0`,
  `dt-2`/`4.0.0`).

### D-07 LOW: historical bound generators were edited in place

- [V] `review/step7/closure/storage_bounds.py`, `d053/perf.py` and `d055/part_ceiling.py` changed in `59f2ad0` (`dt-2`
  becomes `dt-3`, D-13a claims, new evidence kinds). The historical `d053/bounds.json`, `d053/part_ceiling.json`,
  `d055/bounds.json` and `d055/part_ceiling.json` are unchanged.
- [V] `test_d055.py:908` now compares the recomputation with `final-cycle/bounds/bounds.json`. The D-055 file can
  therefore be reproduced only from `6663314`, not from HEAD's tools.
- Recommendation: either copy the generators into `final-cycle/bounds/` and restore the historical ones, or add a note
  in `d055/` that names `6663314` as the reproduction commit of the dt-2 record.

### D-08 LOW: no test pins the P2 campaign's run and scores to their commit

- [V] For P, `test_historical_p_and_campaign_are_unchanged` runs `git diff` between `CAMPAIGN_COMMIT` and HEAD on
  `evaluation-campaign`. No test anywhere names `evaluation-p2-campaign` (`grep -rln` on `tests/`: none). The
  amendment did not weaken anything here: neither the pre- nor the post-amendment file had such a check.
- [V] Immutability holds today. `evaluation-p2-campaign` was last changed in `2b45931` and `evaluation-p2` in
  `10cc9d8` (see D-16).
- Recommendation: add a git-object test for `evaluation-p2-campaign` (RUN.json, SCORES.json, LOCK.json, report) at
  `2b45931`, mirroring the P test.

### D-09 LOW: stale identity sentences in normative text

- [V] `SPECIFICATION.md:1072` (10.3 Staleness) still lists "decision table version `dt-1`". This was already stale
  since D-071.
- [V] The `claim_class` description in `common.schema.json:408` still says "The fifteen classes of dt-1 and dt-2"
  (dt-3 has the same fifteen classes).
- [V] The `claim.schema.json` title still says "version 2", while `x-citerift-version` is 4.0.0. This was already
  the case before the cycle.
- Recommendation: correct the wording. No version change is needed for a description.

### D-10 LOW: exposure v3 builder imprecisions

- [V] The `S04-REF` token scan inherits a v2 defect. The Stage 03 bundles named `ar` and `en` (in
  `stage-03/current-checks/wheel-smoke-final/`) become tokens. The pattern has no left word boundary, so every
  scanned file "names" `ar:10487829` and `en:41787575`. In my build these two records carry 19 and 20 final-cycle
  evidence paths, including `bounds.json` and `fc_provenance.py`. This is over-inclusion (the safe direction), but it
  makes the evidence paths of those records meaningless.
- [V] The docstring claims "only the item count of the lock is read". In fact `campaign_articles` loads the whole
  `LOCK.json`, whose `final` values hold labels (`same_work`, `single_identifier_attachable`, …), and uses its item ids
  for a revision cross-check. The label values are not used.
- Recommendation: add `(?<![\w-])` and `\b` boundaries and skip generic bundle names. Count items from a label-free
  source (packets `items`, or the ids only), or state the actual read precisely.

### D-11 LOW: the "independently extracted" reference profile carries no source metadata

- [V] `bib-reference-profile.json` has only `wikis.*.aliases`: no `source`, revision or content SHA-256. The raw
  `Module:Citation/CS1/Configuration` revisions are not in the repository.
- [I] The independence claim in `bib_reference.py:5-7` and BUILD_VS_ADOPT ("checked equal to an independently
  extracted one") therefore cannot be re-verified offline.
- Recommendation: record the revision id and content SHA-256 in the reference profile, or commit the two raw module
  texts (an attribution note may be needed) so that both profiles can be re-extracted.

### D-12 INFO: versioning is consistent and there is no migration

- [V] The identities are updated consistently:
  - `__version__` is `"0.4.0"`, `dt1.TABLE_VERSION` is `"dt-3"`, `DETECTOR_IDENTITY` is
    `"citerift-dt1-detector/4 (dt-3)"`, and `STAGE04_IDENTITY.schema_version` is `"5.0.0"`.
  - `INTEGRATION_SCHEMAS` names `candidate-inputs` 2.0.0 and `lookup-observation` 3.0.0, matching
    `normalize.SCHEMA_VERSION` and `lookup.SCHEMA_VERSION_OBS`.
  - The schemas declare common 5.0.0 (`table_version` const `dt-3`, `stage04_identity.schema_version` const `5.0.0`),
    claim 4.0.0, candidate-inputs 2.0.0 and lookup-observation 3.0.0.
  - `test_schemas_step5.py` pins all four versions.
  - Every reason in the enum has explanation text: my probe found no missing `REASON_TEXT` entry.
- [V] The diff contains no migration code. Its only mention is the schema description "Claims of dt-1 and dt-2
  belong to the frozen engines and are not migrated".
- [V] `report.schema.json` and `journal-record.schema.json` keep their versions although referenced definitions
  changed. This follows the D-071 precedent.

### D-13 INFO: the E-07 guard behaves as specified

- [V] The guard checks the first record only, before `problems(rec, RECORD)`, with its own code and invariant `E-07`.
- [V] `_corrupt()` maps it to `stale` / `ENGINE_IDENTITY_DIFFERS` (exit 11) on every path that opens a journal:
  `opened`, `run`, `_drive`, `verify` and `export`. Memory validates every record before any repair or removal, and
  the test proves the tree is unchanged.
- [V] The test's corrected sentence "the investigation key does not include the engine identity" matches
  `ids.investigation_key`. The pre-cycle docstring said the opposite.

### D-14 INFO: D-05 is closed

- [V] The fixture now names `artifact_digest`, `semantic_digest` and `snapshot_id` of `rw-2f116e9ffed718e6`. These
  equal the pinned index's `meta` and appear in `freeze-2/d062/two_build_equivalence.json`. The fail-first log shows
  the test failing on `None` values before the fix.
- [I] The script copies the digests from `meta` without Stage 02's verification. They were added in the final cycle,
  not at the original selection. Because the D-062 identity is the same for every build of that source, this is
  acceptable.

### D-15 INFO: no evaluation leakage found

- [V] No label file is read for any result. `LOCK.json`, `SCORES.json` and adjudication files appear in final-cycle
  code, `simulations/stage04` and `test_final_*` only in disclaimers. The single exception is the exposure builder's
  `LOCK.json` read described in D-10.
- [V] `regress.py` cross-checks only engine class counts (`evaluation-p2-campaign/run/RUN.json`
  `claims_by_class`, `corrective/regression/*`).
- [V] Neither the engine nor the reference models contain a Garry, Virology Journal, DOI or PMID constant, and they
  give no special treatment to "–" or "Comments" (grep). The designation lexicon has external sources (Crossmark
  update types, NLM *Comment*; `BIBLIOGRAPHIC_SPEC.md` 4.2) and deliberately leaves out status and genre words.
- [I] The survey of `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2 covers 243 pairs from development, evaluation 1 and
  evaluation 2 data, all design-exposed under D-071 and D-083. It informed design choices: year is never decisive,
  the whole title family is compared, and only relational designations count. It sets no threshold. The
  `MAX_TOTAL_CODE_POINTS` bound (4,096 against a measured 766) is a size bound, not a decision rule.
- [V] The corpus labels its five development-origin cases. Its Garry variants are tests, not rules.

### D-16 INFO: historical immutability and the exposure v3 coverage verified

- [V] `git diff --stat 6663314 HEAD -- docs/verification/stage-04/{evaluation,evaluation-campaign,evaluation-p2,`
  `evaluation-p2-campaign,freeze,freeze-2}/ simulations/stage04/{oracle,oracle-dt2}/` is empty. These paths hold 22,
  698, 20, 878, 59, 58, 3 and 3 tracked files, and none has uncommitted changes.
- [V] `d053/bounds.json`, `d053/part_ceiling.json`, `d055/bounds.json` and `d055/part_ceiling.json` are unchanged
  (the diff under `review/` lists only the three `.py` files of D-07).
- [V] In-memory v3 build (about 170 s):
  - 478 articles. `S04-CAMPAIGN-80` has 80 and `S04-P2-CAMPAIGN-100` has 100.
  - `covers_superseded` passes for both the v1 and the v2 manifest.
  - All six article tokens in the final-cycle evidence are listed: `en-27958530`, `en-21293835`, `en-39868218`,
    `ar-10305362`, `ar-311750-a1` and `en-614753-a1`.
  - `drawn_not_acquired`: 173 of 320 positions (P) and 199 of 299 (P2) are not otherwise listed. Every position has a
    page id.
- [I] Keeping the drawn-but-not-acquired block for information only matches the Stage 03 `listed` precedent: only
  titles were seen. The P3 pre-registration should nonetheless make its exclusion an explicit, recorded choice.

## Verdict

No CRITICAL finding. The change is not ready for freeze-3 until the false owner-decision statement (D-01, HIGH) is
corrected and the four MEDIUM findings (D-02 to D-05) are fixed or settled by the owner. The versioning, E-07, the
D-05 fix, historical immutability, label isolation and exposure coverage are sound.
