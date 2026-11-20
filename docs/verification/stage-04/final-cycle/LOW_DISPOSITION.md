# Stage 04 final corrective cycle: disposition of every finding (owner decision D-083, items 6, 7 and 10)

Every finding of the final-cycle reviews (`review/REVIEW_A.md`, `B`, `C`, `D`, `E`, `F`), the six LOW findings open at
the start of the cycle (`../HANDOFF.md` section 9) and the three accepted residuals of D-083 item 7 are listed below.
Each one is fixed with its evidence, classified as an accepted residual with the reason, or marked as awaiting an
owner decision.

- **Fixed** means the fix is committed and named by a test or a committed result.
- **Accepted residual** means the behaviour stays as it is, is stated in the named document, and fails closed or has
  no effect on a decision.
- **Awaiting owner decision** means the engineering work is done but the outcome needs the owner's answer, which is
  not yet recorded in `DECISIONS.md` (reviewer finding C-02). These rows are listed again in the final report.
- **No action** (INFO) means the finding confirms a property and asks for nothing.

Ids are prefixed by cycle where they would collide (reviewer finding C-03): `corr-` for the corrective-cycle LOW
findings of section 1, `S12-` for the Step 12 residuals of section 2. The ids of sections 3 to 5 are those of the
final-cycle reviews (`A-01` is finding 01 of `review/REVIEW_A.md`).

The independent re-verification of the fixes of reviews A, B, D and E is `review/REVIEW_F.md`; its own findings
(F-01 to F-05) are in section 4. Review C (regression, recall, evaluation leakage, and the fixes of review F) is
section 5.

## 1. LOW findings open at the start of the cycle (`../HANDOFF.md` section 9)

| Id | Finding | Disposition | Evidence |
|---|---|---|---|
| corr-A-04 | A non-cited bridge key could expose a positive | **Fixed (proof and tests, no semantic change)**. The proof is Stage 02 rule 7f: a bridged event never decides alone. On the whole snapshot, 96,803 keys are decided and every one of the 81,743 D-14 positives has a direct, non-ambiguous supporting event (0 violations). The test runs on a real Stage 02 index. | `lows/a04_invariant_census.json`; `tests/stage04/test_final_bib.py::test_a04_bridged_events_alone_never_give_a_positive`; RISK_ANALYSIS R4-04 |
| corr-D-05 | The role-collision fixture manifest lacked the index's digests | **Fixed** (`artifact_digest` and `semantic_digest` recorded; fail-first log) | `test_final_lows.py::test_d05_…`; `lows/fail_first_d05_before.log` |
| corr-E-05 | Absolute memory root in printed and durable output | **Fixed**. The CLI redacts whole absolute spellings, including the effective root of `run --request`; errors never print an ancestor path. Journals keep paths only as operational provenance outside every scientific digest (A11-6). | `test_final_lows.py::test_e05_…`, `test_e03_…`, `test_e04_…`; `lows/fail_first_e05_before.log` |
| corr-E-07 | No dedicated error for a memory root of another engine | **Fixed**. The stable code is `ENGINE_IDENTITY_DIFFERS`. It is checked before schema validation and only on an intact first record (final-cycle D-06). | `test_corrective_compat.py::test_e07_…` (4 tests) |
| corr-C-07 | The role-collision scan is quadratic | **Accepted residual (measured)**: 2.6 s at 3,000 synthetic events; below 0.03 s on the snapshot's largest keys (281 events at most); the extrapolation to the storage bound is stated | `lows/c07_profile.json`; `PERFORMANCE_AND_BOUNDS.md` section 3 |
| corr-N-01 | Provenance covered only `src` and `schemas` | **Fixed** together with D-03 (section 3) | `fc_provenance.py`; `tests/stage04/test_final_provenance.py` |

## 2. Accepted residuals re-reviewed (item 7)

| Residual | New evidence of a Stage 04 defect? | Disposition |
|---|---|---|
| `run` idempotency depends on path spelling (S12-C-07) | None. dt-3 does not touch the run key or the memory layout. | Accepted residual, reaffirmed; `resume --key` is the stable form |
| A different bundle at the recorded path is STALE (S12-C-08) | None. That is the intended fail-closed outcome. | Accepted residual, reaffirmed |
| Stage 02 `crossref_sources` has no ORDER BY (S12-C-12) | None. The RW-only index has 0 such rows, and Stage 02 is not changed (D-083 item 2). | Accepted residual, reaffirmed (upstream) |

## 3. Findings of the final-cycle reviews

| Id | Severity | Disposition | Evidence |
|---|---|---|---|
| A-01 | HIGH | Fixed: values are cleaned at node boundaries, so no designation word is lost | `test_final_bib.py` corpus cases; spec 2.1 |
| A-02 | HIGH | **Awaiting owner acceptance of the stated residual** (the fix itself is committed). Threshold-free rule: surnames only (no given names, initials or particles), every comparable cited value must name a record surname, and a uniform lexicon with note genres. Review F found the author-absent path unstated: section 9 now states it (a related note cited with no comparable author whose extra title words are outside the lexicon stays positive), with a corpus case, and that title DISJOINT is rare between Latin titles. The residual false compatibility is stated, never removed; whether to accept it is the owner's call. | spec 4.1 and 9; `lows/author_coincidence.json`; corpus case `related-note-no-author-residual` |
| A-03 | MEDIUM | Fixed: the profile bytes and the parser version are pinned in the engine code (another profile is refused), and a test pins both with the engine version | `test_final_bib.py::test_the_profile_and_parser_pins_belong_to_engine_0_4_0`; spec 2.2 |
| A-04 | LOW | Fixed: designation is checked over every CONTAINED/OVERLAP title value | corpus; spec 4.2 |
| A-05 | LOW | Fixed: singular and plural forms of every term, phrase forms included | spec 4.2; corpus |
| A-06 | LOW | Fixed: the recall costs are stated in spec section 9 | spec 9 |
| A-07 | LOW | Fixed: a parser exception gives no cited object | `bibliographic.cited_object`; spec 2.1 |
| A-08 | LOW | Fixed: `REGRESSION.md`, `ROLE_COLLISION_STUDY.md` and `PERFORMANCE_AND_BOUNDS.md` exist; the size figures of spec 2.1 come from a committed measurement; the survey claim is qualified as in-sample development evidence (the "recall cost nil" claim is withdrawn) | `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2; `lows/description_sizes.json` |
| A-09 | LOW | Accepted residual. Per-event verdicts are a pure function of the committed description and records. VERIFY recomputes them, and the claim names every compared record. | spec 7 |
| B-01 | MEDIUM | Fixed: the dt-3 oracle (50,529,792 cases) and the production test exist. With `bc` False dt-3 equals dt-2 case for case, and `bc` changes only D-14 to D-13a (1,456 cases). | `simulations/stage04/oracle-dt3/`; `test_final_oracle.py` |
| B-02 | MEDIUM | Fixed: the role-collision study is committed, and D-072 is kept strict | `ROLE_COLLISION_STUDY.md`; `role-collision/ROLE_COLLISION_STUDY.json` |
| B-03 | LOW | Fixed: the A-04 census was rerun with provenance from a clean checkout, and a detector-level A-04 test runs on a real Stage 02 index | `lows/a04_invariant_census.json`; `test_final_bib.py::test_a04_…` |
| B-04 | LOW | Fixed: R4-04 names Stage 02 rule 7f as the proof and states the PAIR scope | `RISK_ANALYSIS.md` R4-04 |
| B-05 | LOW | Accepted residual (fail closed, stated). Every event of the deciding lookup is compared, bridged and co-keyed events included. On the snapshot, 7 of 81,743 single-key positives abstain; the regression gives the development count. | spec 9; RISK R4-04a; `REGRESSION.md` |
| B-06 | LOW | Fixed: a lookup record whose title or journal contradicts its event fails with `ADAPTER_INCONSISTENT` | `test_final_bib.py::test_a_record_contradicting_its_public_event_fails_closed`; `lows/review_fixes_fail_first.log` |
| B-07 | INFO | No action (mistyped record fields are treated as absent, which is the spec) | spec 2.3 |
| D-01 | HIGH | **Fixed by owner decision D-084** (2026-11-20, option "Amend both, D-074 style"): the two pre-registered test files verify the historical engines from git; the test comment cites D-084. P and P2 are unchanged and still proved from git. | `DECISIONS.md` D-084; `tests/stage04/test_p2_evaluation.py:115` |
| D-02 | MEDIUM | Fixed with A-03 | as A-03; `BUILD_VS_ADOPT.md` |
| D-03 | MEDIUM | Fixed. Every final-cycle tool refuses to start from a tree with uncommitted changes in its dependency set and refuses to write when the tree changed during the run. Every committed result was rerun from a clean checkout. A test checks each result's tool hash at its commit and that the engine and inputs are unchanged at HEAD. | `fc_provenance.py`; `test_final_provenance.py`; `lows/d03_fail_first.log` |
| D-04 | MEDIUM | **Fixed by owner decision D-084** (with D-01): the P2 identity-guard mutations run in the P2 worktree. | `DECISIONS.md` D-084; `test_p2_evaluation.py::test_engine_check_refuses_a_different_committed_engine_tree` |
| D-05 | MEDIUM | Fixed: the dt-3 evidence census uses the new kinds and their sizes, and `bounds.json` is regenerated | `bounds/dt3_bounds.py`; `bounds/bounds.json`; `test_d055.py::test_format_4_bounds_are_recomputed_and_proven` |
| D-06 | LOW | Fixed: the E-07 guard runs only on an intact first record; a damaged one is `RECORD_INVALID` or `CHAIN_BROKEN` | `test_corrective_compat.py::test_e07_a_damaged_first_record_is_corrupt_not_another_engines` |
| D-07 | LOW | Fixed: the historical generators are restored to `6663314`, and the dt-3 copies are in `bounds/` | `test_final_history.py`; `bounds/` |
| D-08 | LOW | Fixed: a git-object test pins the evaluations, campaigns, freezes and oracles to their commits | `test_final_history.py` |
| D-09 | LOW | Fixed: the stale identity sentences are corrected (common schema description, claim schema title) | `schemas/investigation/v1/` |
| D-10 | LOW | Fixed: the exposure v3 builder uses word boundaries and the article-name pattern | `freeze-3/exposure/build_exposure_manifest.py` |
| D-11 | LOW | Partly incorrect finding. Both profiles name the same module revisions, and a test checks it. | `test_final_bib.py::test_both_profiles_name_the_same_module_revisions` |
| E-01 | MEDIUM | **Fixed** (behaviour changed twice; final form by C-01): a lone surrogate becomes U+FFFD in the cleaned value, so NORMALIZE no longer fails and the value keeps its words | `test_final_bib.py::test_normalize_replaces_a_surrogate_and_keeps_the_value`; corpus cases `lone-surrogate-entity`, `surrogate-in-author-commenter`; spec 2.1 step 4 |
| E-02 | LOW | **Awaiting owner decision** (the bound and its consequence; reviewer findings E-02, F-02 and C-02). A source over 16,384 code points is not parsed and has no cited object, so the unit decides as under dt-2 (section 9). The development maximum is 5,722 code points; the per-page bib-1 time and a crafted unit just under the bound (6.5 s CPU in the committed run) are measured. | `bibliographic.cited_object`; spec 2.1 and 9; `lows/description_sizes.json`; `PERFORMANCE_AND_BOUNDS.md` section 5 |
| E-03 | MEDIUM | Fixed: the redaction covers the effective root of `run --request` and ancestor paths | `test_final_lows.py::test_e03_…` |
| E-04 | MEDIUM | Fixed: only whole absolute spellings are replaced | `test_final_lows.py::test_e04_…` |
| E-05 | INFO | No action | |
| E-06 | INFO | No action (the echoed strings are shortened) | `fold.py` |
| E-07 | MEDIUM | Fixed: LOOKUP v3 rho is measured (13.07), with no analytic claim; `bounds.json` labels the LOOKUP row measured, not proven, and the `adapters/lookup.py` docstring says so. The worst observation is within the blob limit; above it the write fails (`BLOB_TOO_LARGE`). | `bounds/bounds.json`; `adapters/lookup.py`; `PERFORMANCE_AND_BOUNDS.md` section 2 |
| E-08 | LOW | Fixed with D-05 | as D-05 |
| E-09 | LOW | Fixed for the bibliography increment (bounded by the source). The Step 8 terms have no derived bound, a pre-existing gap now stated (overflow fails closed). | `bounds/dt3_bounds.py` docstring item 4; `PERFORMANCE_AND_BOUNDS.md` |
| E-10 | LOW | Accepted residual (measured and retained; as C-07). The measured synthetic curve, the snapshot maximum and the extrapolated cost at the storage bound are stated, with the choice to retain rather than restructure the normative scan. | `lows/c07_profile.json`; `PERFORMANCE_AND_BOUNDS.md` section 3 |
| E-11 | LOW | Fixed: the engine refuses without the C tokenizer | `test_final_bib.py::test_the_engine_refuses_without_the_c_tokenizer` |
| E-12 | INFO | No action (the size bound is stated) | spec 2.1 |
| E-13 | INFO | No action (the scans are clean) | |
| A-11 | INFO | No action (production equals the spec and the reference) | |
| A-12 | INFO | No action (Arabic handling as specified) | |
| B-08 | INFO | No action (D-13a placement, guard, PAIR tail and claim schema are correct) | |
| B-09 | INFO | No action (notice/original separation holds; bib-1 never resolves a role collision) | `ROLE_COLLISION_STUDY.md` |
| B-10 | INFO | No action (detector record binding fails closed) | |
| D-12 | INFO | No action (versioning consistent, no migration) | |
| D-13 | INFO | No action (the E-07 guard behaves as specified) | |
| D-14 | INFO | No action (D-05 closed) | |
| D-15 | INFO | No action (no evaluation leakage found) | |
| D-16 | INFO | Open by design, for a future P3 (not authorized): its pre-registration must record the exclusion of drawn-but-not-acquired positions as an explicit choice | `review/REVIEW_D.md` |
| A-10 | INFO | Closed by B-01 | |

## 4. Findings of the re-verification (`review/REVIEW_F.md`)

| Id | Severity | Disposition | Evidence |
|---|---|---|---|
| F-01 | HIGH | Fixed: the initials rule keeps the first cited token when every token looks like initials, so a value made only of a short all-caps surname (`|last=LI`, `|last=WU`) still names that surname and a commenter with such a name is a CONFLICT again. Engine and reference alike. | corpus cases `caps-surname-only`, `caps-surname-with-first`, `caps-vauthors`, `caps-surname-genuine`; spec 3; `lows/review_f_fail_first.log` |
| F-02 | MEDIUM | Surrogate path **fixed** (final form by C-01: the surrogate becomes U+FFFD and no value is dropped). Size path: **awaiting owner decision**, as E-02. | `test_final_bib.py::test_normalize_replaces_a_surrogate_and_keeps_the_value`; corpus cases `lone-surrogate-garry-pages`, `surrogate-in-author-garry`, `surrogate-in-title-garry`, `oversized-source`; `lows/review_f_fail_first.log`, `lows/review_c_fail_first.log` |
| F-03 | LOW | Fixed: the test checks the recorded tool hash against the tool at HEAD, and the final-cycle tools, the census tools and (C-07) the Stage 03 development bundles and the files one result reads from another are checked from the result's commit to HEAD; the index file's SHA-256 is recorded; every result was rerun under the guard from a clean checkout | `test_final_provenance.py`; `fc_provenance.py` |
| F-04 | LOW | Fixed: the content of inline formatting tags (`i`, `b`, `sub`, `sup`, `span`, `small`, `big`, `u`, `s`, `em`, `strong`) is joined as rendered; templates, comments, `br`, `ref` and block tags stay boundaries | corpus cases `inline-subscript`, `inline-italic-inside-a-word`; spec 2.1 step 4 |
| F-05 | LOW | Accepted residual (fail closed, stated): a hyphenated `re-` word gives the lexicon word `re`, so a genuine citation that adds it abstains. Counting `re` only as a first word would be a new positional rule for one word. | spec 9; corpus case `re-hyphen-prefix` |


## 5. Findings of review C (`review/REVIEW_C.md`: regression, recall, evaluation leakage, review F fixes)

| Id | Severity | Disposition | Evidence |
|---|---|---|---|
| C-01 | MEDIUM | **Fixed** in engine and reference: a lone surrogate becomes U+FFFD (no word character), so it never removes a compared value. Fail-first: `surrogate-in-author-commenter` was COMPATIBLE (a positive) before the fix and is MATERIAL_CONFLICT after. All results were rerun. | spec 2.1 step 4; corpus cases `surrogate-in-author-garry`, `surrogate-in-title-garry`, `surrogate-in-author-commenter`, `surrogate-in-author-genuine`; `lows/review_c_fail_first.log`; `test_final_bib.py::test_normalize_replaces_a_surrogate_and_keeps_the_value` |
| C-02 | MEDIUM | **Fixed**: items awaiting the owner are marked so and listed in the final report (E-02 with the F-02 size path; A-02's residual). D-01 and D-04 were marked so until the owner decided them (D-084). | this table, section 3 |
| C-03 | LOW | **Fixed**: row E-01 updated, the nine INFO rows added, ids prefixed by cycle | this table |
| C-04 | LOW | **Fixed** (partly incorrect: the statement is in the owner's D-083 message, item 5). The study now cites that message id, says the statement comes from the scored campaign, and uses it in no argument or count. | `ROLE_COLLISION_STUDY.md` sections 1 and 4 |
| C-05 | LOW | **Fixed**: the same-record argument no longer says "one record" (13,700 and 1,341 records; up to 4 events per development lookup), the JASIST sentence is a condition 3 argument, and section 3 says that a conflict means two works, not work versus notice. The conclusion is unchanged. | `ROLE_COLLISION_STUDY.md` sections 2 and 3 |
| C-06 | LOW | **Fixed (statement)** and **accepted residual (format)**: `REGRESSION.md` section 6 says the census equality holds by construction (no description) and confirms only the unchanged rules. The census results keep the corrective-cycle provenance of the unchanged census tools; the test checks the tools and the engine from that commit to HEAD. | `REGRESSION.md` section 6; `test_final_provenance.py::test_the_role_collision_censuses_are_unchanged_under_dt3` |
| C-07 | LOW | **Fixed**: the Stage 03 bundles are in the checked set, and the files one result reads from another (`READS`) must be unchanged from its commit to HEAD | `fc_provenance.py`; `test_final_provenance.py` |
| C-08 | LOW | **Fixed**: variants built on the real P2 record are labelled as such in each corpus case's `origin` field, and the F-01 path and the surrogate-in-author path also have cases on the synthetic record (the surrogate-in-title path has a case on the P2-record variant only; G-05) | corpus `origin` field; cases `caps-surname-commenter`, `surrogate-in-author-commenter` |
| C-09 | LOW | **Fixed**: the reading of the changed claims is labelled an engineering reading (not a label, in-sample, not shown independent of earlier adjudications) in `REGRESSION.md` and the freeze limitations; the parser-time figure is one measured shape, not a bound | `REGRESSION.md` section 3; `../freeze-3/build_freeze_manifest.py` |
| C-10 | LOW | **Fixed**: `lows/corpus_probe.py` decides corpus cases with any engine checkout; both fail-first logs were regenerated with it (review F: before at `7d5b936`; review C: before at `e3d7952`; after at `bb7a0cf`) | `lows/corpus_probe.py`; `lows/review_f_fail_first.log`; `lows/review_c_fail_first.log` |
| C-11 | INFO | **Fixed**: the C-01 sibling case of D-083 item 11 is named in `REGRESSION.md` section 6 | `REGRESSION.md` |
| C-12 | INFO | **Accepted residual (stated)**: an unspaced designation word in an inline tag fuses with the word before it | spec 9; corpus case `inline-designation-joined` |

## 6. Findings of review G (`review/REVIEW_G.md`: re-verification of the review C fixes)

Review G found no CRITICAL, HIGH or MEDIUM finding and confirmed that C-01 is fixed and complete (0 disagreements
between engine and reference over 4,000 fuzzed templates; the C-01 fail-first log reproduces).

| Id | Severity | Disposition | Evidence |
|---|---|---|---|
| G-01 | LOW | **Fixed**: rows D-01 and D-04 cite D-084; D-084 names both amending commits (`1b0670a`, `79a0023`) | this table; `DECISIONS.md` D-084 |
| G-02 | LOW | **Fixed**: row A-02 is headed "Awaiting owner acceptance of the stated residual" | this table |
| G-03 | LOW | **Fixed**: the freeze-3 limitations use the corrected same-record wording (C-05) and name the no-author residual | `../freeze-3/build_freeze_manifest.py` |
| G-04 | LOW | **Accepted residual, stated, awaiting owner acceptance with A-02**: an invisible format character (soft hyphen, zero-width space or joiner, word joiner) inside a designation word splits it, so a related note cited with no comparable author stays compatible; with a commenter's name the author conflict still blocks. Review G's scan found no such cited value in the Stage 03 bundles. Removing format characters in `fold()` would be an engine change for a path no development citation shows; it is left to the owner with A-02. | spec section 9 |
| G-05 | LOW | **Accepted residual**: the corpus builder's docstring predates the `origin` labels of C-08; each case's `origin` field is authoritative. The surrogate-in-title path is covered on the P2-record variant only. Changing the builder now would invalidate every committed result for a wording fix. | `corpus/BIB_CORPUS.json` `origin` |
| G-06 | INFO | No action: every committed result was rerun at `f83d20b`, so no evidence mixes the three surrogate behaviours of the cycle | `test_final_provenance.py` |
| G-07 | INFO | No action: the provenance input lists are maintained by hand and cover each tool's current inputs; the fail-first logs are reproducible with `lows/corpus_probe.py` | |
