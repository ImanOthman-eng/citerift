# Stage 04 final corrective cycle: disposition of every finding (owner decision D-083, items 6, 7 and 10)

Every finding of the final-cycle reviews (`review/REVIEW_A.md`, `B`, `C`, `D`, `E`), the six LOW findings open at
the start of the cycle (`../HANDOFF.md` section 9) and the three accepted residuals of D-083 item 7 are listed below.
Each one is either fixed, with its evidence, or classified as an accepted residual with the reason.

- **Fixed** means the fix is committed and named by a test or a committed result.
- **Accepted residual** means the behaviour stays as it is, is stated in the named document, and fails closed or has
  no effect on a decision.

The independent re-verification of the fixes is `review/REVIEW_F.md`.

## 1. LOW findings open at the start of the cycle (`../HANDOFF.md` section 9)

| Id | Finding | Disposition | Evidence |
|---|---|---|---|
| A-04 | A non-cited bridge key could expose a positive | **Fixed (proof and tests, no semantic change)**. The proof is Stage 02 rule 7f: a bridged event never decides alone. On the whole snapshot, 96,803 keys are decided and every one of the 81,743 D-14 positives has a direct, non-ambiguous supporting event (0 violations). The test runs on a real Stage 02 index. | `lows/a04_invariant_census.json`; `tests/stage04/test_final_bib.py::test_a04_bridged_events_alone_never_give_a_positive`; RISK_ANALYSIS R4-04 |
| D-05 | The role-collision fixture manifest lacked the index's digests | **Fixed** (`artifact_digest` and `semantic_digest` recorded; fail-first log) | `test_final_lows.py::test_d05_…`; `lows/fail_first_d05_before.log` |
| E-05 | Absolute memory root in printed and durable output | **Fixed**. The CLI redacts whole absolute spellings, including the effective root of `run --request`; errors never print an ancestor path. Journals keep paths only as operational provenance outside every scientific digest (A11-6). | `test_final_lows.py::test_e05_…`, `test_e03_…`, `test_e04_…`; `lows/fail_first_e05_before.log` |
| E-07 | No dedicated error for a memory root of another engine | **Fixed**. The stable code is `ENGINE_IDENTITY_DIFFERS`. It is checked before schema validation and only on an intact first record (D-06). | `test_corrective_compat.py::test_e07_…` (4 tests) |
| C-07 | The role-collision scan is quadratic | **Accepted residual (measured)**: 2.5 s at 3,000 synthetic events; below 0.03 s on the snapshot's largest keys | `lows/c07_profile.json`; `PERFORMANCE_AND_BOUNDS.md` section 3 |
| N-01 | Provenance covered only `src` and `schemas` | **Fixed** together with D-03 (below) | `fc_provenance.py`; `tests/stage04/test_final_provenance.py` |

## 2. Accepted residuals re-reviewed (item 7)

| Residual | New evidence of a Stage 04 defect? | Disposition |
|---|---|---|
| `run` idempotency depends on path spelling (Step 12 C-07) | None. dt-3 does not touch the run key or the memory layout. | Accepted residual, reaffirmed; `resume --key` is the stable form |
| A different bundle at the recorded path is STALE (Step 12 C-08) | None. That is the intended fail-closed outcome. | Accepted residual, reaffirmed |
| Stage 02 `crossref_sources` has no ORDER BY (Step 12 C-12) | None. The RW-only index has 0 such rows, and Stage 02 is not changed (D-083 item 2). | Accepted residual, reaffirmed (upstream) |

## 3. Findings of the final-cycle reviews

| Id | Severity | Disposition | Evidence |
|---|---|---|---|
| A-01 | HIGH | Fixed: values are cleaned at node boundaries, so no designation word is lost | `test_final_bib.py` corpus cases; spec 2.1 |
| A-02 | HIGH | Fixed as far as a threshold-free rule allows. Surnames only (no given names, initials or particles), every comparable cited value must name a record surname, and a uniform lexicon with note genres. Residual false compatibility is stated with measured rates. | spec 4.1 and 9; `lows/author_coincidence.json`; corpus |
| A-03 | MEDIUM | Fixed: the profile bytes and the parser version are pinned in the engine code (another profile is refused), and a test pins both with the engine version | `test_final_bib.py::test_the_profile_and_parser_pins_belong_to_engine_0_4_0`; spec 2.2 |
| A-04 | LOW | Fixed: designation is checked over every CONTAINED/OVERLAP title value | corpus; spec 4.2 |
| A-05 | LOW | Fixed: singular and plural forms of every term, phrase forms included | spec 4.2; corpus |
| A-06 | LOW | Fixed: the recall costs are stated in spec section 9 | spec 9 |
| A-07 | LOW | Fixed: a parser exception gives no cited object | `bibliographic.cited_object`; spec 2.1 |
| A-08 | LOW | Fixed: `REGRESSION.md` and `PERFORMANCE_AND_BOUNDS.md` exist, and the survey claim is qualified as in-sample development evidence (the "recall cost nil" claim is withdrawn) | `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2 |
| A-09 | LOW | Accepted residual. Per-event verdicts are a pure function of the committed description and records. VERIFY recomputes them, and the claim names every compared record. | spec 7 |
| B-01 | MEDIUM | Fixed: the dt-3 oracle (50,529,792 cases) and the production test exist. With `bc` False dt-3 equals dt-2 case for case, and `bc` changes only D-14 to D-13a (1,456 cases). | `simulations/stage04/oracle-dt3/`; `test_final_oracle.py` |
| B-02 | MEDIUM | Fixed: the role-collision study is committed, and D-072 is kept strict | `ROLE_COLLISION_STUDY.md`; `role-collision/ROLE_COLLISION_STUDY.json` |
| B-03 | LOW | Fixed: the A-04 census was rerun with provenance from a clean checkout, and a detector-level A-04 test runs on a real Stage 02 index | `lows/a04_invariant_census.json`; `test_final_bib.py::test_a04_…` |
| B-04 | LOW | Fixed: R4-04 names Stage 02 rule 7f as the proof and states the PAIR scope | `RISK_ANALYSIS.md` R4-04 |
| B-05 | LOW | Accepted residual (fail closed, stated). Every event of the deciding lookup is compared, bridged and co-keyed events included. On the snapshot, 7 of 81,743 single-key positives abstain; the regression gives the development count. | spec 9; RISK R4-04a; `REGRESSION.md` |
| B-06 | LOW | Fixed: a lookup record whose title or journal contradicts its event fails with `ADAPTER_INCONSISTENT` | `test_final_bib.py::test_a_record_contradicting_its_public_event_fails_closed`; `lows/review_fixes_fail_first.log` |
| B-07 | INFO | No action (mistyped record fields are treated as absent, which is the spec) | spec 2.3 |
| D-01 | HIGH | Fixed: the comment says "PENDING OWNER DECISION" and cites the card. The amendment itself awaits the owner. | `tests/stage04/test_p2_evaluation.py:115` |
| D-02 | MEDIUM | Fixed with A-03 | as A-03; `BUILD_VS_ADOPT.md` |
| D-03 | MEDIUM | Fixed. Every final-cycle tool refuses to start from a tree with uncommitted changes in its dependency set and refuses to write when the tree changed during the run. Every committed result was rerun from a clean checkout. A test checks each result's tool hash at its commit and that the engine and inputs are unchanged at HEAD. | `fc_provenance.py`; `test_final_provenance.py`; `lows/d03_fail_first.log` |
| D-04 | MEDIUM | Fixed: the P2 identity-guard mutations run in the P2 worktree. The amendment awaits the owner, as for D-01. | `test_p2_evaluation.py::test_engine_check_refuses_a_different_committed_engine_tree` |
| D-05 | MEDIUM | Fixed: the dt-3 evidence census uses the new kinds and their sizes, and `bounds.json` is regenerated | `bounds/dt3_bounds.py`; `bounds/bounds.json`; `test_d055.py::test_format_4_bounds_are_recomputed_and_proven` |
| D-06 | LOW | Fixed: the E-07 guard runs only on an intact first record; a damaged one is `RECORD_INVALID` or `CHAIN_BROKEN` | `test_corrective_compat.py::test_e07_a_damaged_first_record_is_corrupt_not_another_engines` |
| D-07 | LOW | Fixed: the historical generators are restored to `6663314`, and the dt-3 copies are in `bounds/` | `test_final_history.py`; `bounds/` |
| D-08 | LOW | Fixed: a git-object test pins the evaluations, campaigns, freezes and oracles to their commits | `test_final_history.py` |
| D-09 | LOW | Fixed: the stale identity sentences are corrected (common schema description, claim schema title) | `schemas/investigation/v1/` |
| D-10 | LOW | Fixed: the exposure v3 builder uses word boundaries and the article-name pattern | `freeze-3/exposure/build_exposure_manifest.py` |
| D-11 | LOW | Partly incorrect finding. Both profiles name the same module revisions, and a test checks it. | `test_final_bib.py::test_both_profiles_name_the_same_module_revisions` |
| E-01 | MEDIUM | Fixed: a surrogate entity gives no cited object instead of failing NORMALIZE | `test_final_bib.py::test_normalize_gives_no_cited_object_for_a_surrogate_entity` |
| E-02 | LOW | Fixed: a source over 16,384 code points gives no cited object before parsing | `bibliographic.cited_object`; spec 2.1 |
| E-03 | MEDIUM | Fixed: the redaction covers the effective root of `run --request` and ancestor paths | `test_final_lows.py::test_e03_…` |
| E-04 | MEDIUM | Fixed: only whole absolute spellings are replaced | `test_final_lows.py::test_e04_…` |
| E-05 | INFO | No action | |
| E-06 | INFO | No action (the echoed strings are shortened) | `fold.py` |
| E-07 | MEDIUM | Fixed: LOOKUP v3 rho is measured (13.07), with no analytic claim, and the worst observation is within the blob limit | `bounds/bounds.json`; `PERFORMANCE_AND_BOUNDS.md` section 2 |
| E-08 | LOW | Fixed with D-05 | as D-05 |
| E-09 | LOW | Fixed for the bibliography increment (bounded by the source). The Step 8 terms have no derived bound, a pre-existing gap now stated (overflow fails closed). | `bounds/dt3_bounds.py` docstring item 4; `PERFORMANCE_AND_BOUNDS.md` |
| E-10 | LOW | Accepted residual (measured; as C-07) | `lows/c07_profile.json` |
| E-11 | LOW | Fixed: the engine refuses without the C tokenizer | `test_final_bib.py::test_the_engine_refuses_without_the_c_tokenizer` |
| E-12 | INFO | No action (the size bound is stated) | spec 2.1 |
| E-13 | INFO | No action (the scans are clean) | |
