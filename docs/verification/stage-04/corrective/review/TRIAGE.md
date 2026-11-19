# Corrective cycle: triage of the independent reviews (owner decision D-071, section 10)

Reviews: A scientific semantics (`REVIEW_A.md`, with a re-review), B identifiers and roles (`REVIEW_B.md`, with a
re-review), C regression risk (`REVIEW_C.md`), D source provenance (`REVIEW_D.md`), E security (`REVIEW_E.md`),
F evaluation leakage (`REVIEW_F.md`). The fixes for D, E and F were re-verified by a separate reviewer
(`REVERIFY_DEF.md`). Each review ran in a fresh context and was committed verbatim; the author changed none of them.

Status values: **fixed** (the reviewer or the re-verifier confirmed the fix), **decided** (put to the owner on a
decision card and decided by the owner; the decision is cited), **open** (accepted as a known limit, with the reason), **info** (no action).

## Tally

| Review | CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|---|
| A | 0 | 0 | 4 (A-01, A-02, A-03, A-10) | 4 (A-04, A-05, A-06, A-11) | 4 (A-07, A-08, A-09, A-12) |
| B | 1 (B-01) | 0 | 2 (B-02, B-03) | 3 (B-04, B-05, B-06) | 3 (B-07, B-08, B-09) |
| C | 0 | 0 | 1 (C-01) | 2 (C-02, C-07) | 5 (C-03 to C-06, C-08) |
| D | 0 | 0 | 2 (D-01, D-02) | 3 (D-03, D-04, D-05) | 5 (D-06 to D-10) |
| E | 0 | 0 | 4 (E-01 to E-04) | 6 (E-05 to E-08, E-10) | 4 (E-09, E-11 to E-13) |
| F | 0 | 0 | 3 (F-03, F-04, F-06) | 2 (F-05, F-07) | 4 (F-01, F-02, F-08, F-09) |
| Re-verification | 0 | 0 | 0 | 2 (N-01, N-03) | 2 (N-02, N-04) |

The one CRITICAL finding (B-01) is fixed and re-verified by reviewer B. No reviewer raised a HIGH finding. No CRITICAL
or HIGH finding is open. The MEDIUM findings put to the owner (A-02, A-10, B-02, B-03, C-01) were decided by the owner
on 2026-11-19 (D-072, D-073, D-075; `cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`); no MEDIUM or higher
finding is open.

The freeze-2 candidate's one test failure (`test_step13_evaluation.py::test_frozen_check_passes_on_the_frozen_engine`,
a P-listed test that asserted the running engine is the superseded `b5bf8ed`) is resolved by owner decision D-074: the
test now proves, from git objects, that P resolves to the files at `827ac1a`, the frozen engine is exactly `b5bf8ed`,
the historical frozen check passes on the historical tree, the Step 14 campaign used that engine, and the current dt-2
engine fails the old assertion; `test_corrective_compat.py::test_freeze2_names_the_dt2_engine_identity` checks the
freeze-2 identity. P and every other P-listed file are unchanged.

## Dispositions

| Id | Sev. | Status | Disposition and evidence |
|---|---|---|---|
| A-01 | MEDIUM | fixed | Only a cited key can discriminate (`dt1.discriminating`); test `test_a_non_cited_bridge_key_never_resolves_a_collided_cited_key`; confirmed in A's re-review. |
| A-02 | MEDIUM | decided (D-072) | Strict reading implemented, lenient measured (`PAIR_CENSUS_LENIENT.json`); owner approved the strict rule and declined the lenient one (D-072). Recall cost stated in SPEC 7.3a, RISK R4-04, the regression README and the freeze limitations: 1,472 of 31,506 dt-1 positive pairs abstain (800 under lenient). |
| A-03 | MEDIUM | fixed | `test_corrective_role_property.py` checks the computation of `rc` on 23,328 combinations; ROOT_CAUSE credits the oracle only given `rc`. |
| A-04 | LOW | open | Documented residual in RISK_ANALYSIS R4-04 (non-cited bridge keys, small exposure, cannot create a positive the cited keys do not support). |
| A-05 | LOW | fixed | Recall cost measured on the full pair set and on the exposed sets (`corrective/regression/`); RISK R4-04 states that every dual role is treated as incompatible. |
| A-06 | LOW | fixed | `explanations.py` text for `IDENTIFIER_ROLE_COLLISION` names "an identifier that links the citation to the work", including the fail-closed case. |
| A-07 | INFO | fixed | `_flags` fails closed (E-08). |
| A-08 | INFO | info | Limits by design or of Stage 02. |
| A-09 | INFO | fixed | `valid_per_shape_note` in the oracle summary. |
| A-10 | MEDIUM | decided (D-072) | The strict rule also drops 5 PMID-side pairs that dt-1 resolved by a clean DOI; kept under D-072. |
| A-11 | LOW | fixed | Stale descriptions rewritten in `dt1.py`, `dt2_reference.py` (oracle re-pinned, decisions unchanged), tests, RISK R4-04. |
| A-12 | INFO | fixed | The property test is described as a restatement of SPEC 7.3a, not as independent semantics. |
| B-01 | CRITICAL | fixed | Key-level collision over every record of every lookup (`dt1.role_collided`); the real pair `10.1016/j.diabet.2013.06.003` + `24076359` is D-10; confirmed in B's re-review. |
| B-02 | MEDIUM | decided (D-072) | As A-02. |
| B-03 | MEDIUM | decided (D-075) | Original DOI cited with the same record's notice PMID stays positive when the DOI is clean, the mirror of D-058. Boundary tests `test_d075_*` in `test_corrective_role_collision.py` (notice PMID alone never positive; no IDENTITY_CONFLICT made from the notice role; a role-collided, unavailable or absent DOI never reaches D-14 through the notice PMID). `census/B03_CENSUS.json`: 31,279 pairs, 628 positive under dt-2 (794 under dt-1; the 166 changes are D-14 to D-10 because the DOI is itself role-collided). |
| B-04 | LOW | fixed | ROOT_CAUSE states that an unavailable Q1 of the resolving key gives D-13 `LOOKUP_UNAVAILABLE` or D-10, never a positive. |
| B-05 | LOW | fixed | Census statements annotated (B's re-review). |
| B-06 | LOW | fixed | dt-2 column in `CENSUS.json`; `PAIR_CENSUS.json` over every original pair. |
| B-07 to B-09 | INFO | info | Verified sound. |
| D-01 | MEDIUM | fixed | Cap and attribution 120 records (re-verified). |
| D-02 | MEDIUM | fixed | Census and regression outputs record index, tables and code revision (re-verified). |
| D-03 | LOW | fixed | `docs/sources-and-attribution.md` lists the Stage 04 fixtures. |
| D-04 | LOW | fixed | Method text matches the selection order. |
| D-05 | LOW | open | The fixture manifest still lacks the selection index's `artifact_digest` and `semantic_digest` (it has its `source_sha256`); regenerating the fixture for a provenance field only was not worth a new fixture digest before the freeze. |
| D-06 to D-10 | INFO | info | Verified sound. |
| E-01, E-02, E-03, E-06 | MEDIUM/LOW | fixed | Runner hardening (no chmod, refusal of shared or symlinked roots, `python -I` engine identity probe); re-verified with probes. |
| E-04 | MEDIUM | fixed | Frozen column decided by the frozen table loaded from its git blob. |
| E-05 | LOW | open | `RUN.json` records the absolute memory root as an operational locator, which D-071 section 9 asks for; it is outside every scientific digest. |
| E-07 | LOW | open | No dedicated engine-version error; a reused private memory root is accepted. The corrected runner refuses to run where a `RUN.json` exists, so a campaign cannot be rerun into an old root. |
| E-08 | LOW | fixed | `_flags` fails closed. |
| E-09, E-11 to E-13 | INFO | info | No action. |
| E-10 | LOW | fixed | Frozen table loaded and re-hashed by blob id. |
| F-01, F-02 | INFO | info | Campaign and P files unchanged; no item-specific knowledge in the engine. |
| F-03 | MEDIUM | fixed | Exposure builder refuses a working tree that differs from HEAD (re-verified). |
| F-04 | MEDIUM | fixed | Identifiers block marked information only, with the census scope; frame exclusion is by article. |
| F-05 | LOW | fixed | freeze-2 scanned; v1 coverage checked before writing. |
| F-06 | MEDIUM | fixed | `freeze-2/build_validation.py` carries the freeze-2 code revision and test runs (filled in from the freeze-2 runs). |
| F-07 | LOW | fixed | Freeze limitation states the strict rule; regression results now exist in `corrective/regression/`. |
| F-08 | INFO | fixed | `corrective/regression/README.md` states the regression is never joined with campaign labels or scorer. |
| F-09 | INFO | info | For a future P2: drawn-but-unacquired positions stay eligible; the Arabic frame after exclusion (140) must be checked against G2. |
| N-01 | LOW | open | `provenance()` checks `src` and `schemas` only; tools under `docs/` are identified by their commit (`code_commit`) and, for the regression, by `tool_sha256`. |
| N-02 | INFO | info | `--memory-root /` passes the engine check; no permission change is made. |
| N-03 | LOW | fixed | Identifiers note says other named keys are inside the census scope. |
| N-04 | INFO | fixed | The two "B-03" references in the freeze limitations are disambiguated. |

## C: regression risk

| Id | Sev. | Status | Disposition and evidence |
|---|---|---|---|
| C-01 | MEDIUM | decided (D-073) | A same-work sibling record (same original DOI and PMID, e.g. an EoC with notice ids equal to the article's) collides both keys of a clean retraction (53 snapshot pairs, 1 campaign claim, `ar-3351802 un-00059`). Owner decision D-073: no same-work-sibling exemption; all 53 stay `UNRESOLVED_IDENTITY`; "probable true positive" is descriptive only. SPEC 7.3a, RISK R4-04 and the regression README say so. |
| C-02 | LOW | fixed | `tests/stage04/test_corrective_compat.py`: a frozen-engine (dt-1) journal is refused at its first record (`RECORD_INVALID`, names dt-2 and 4.0.0), the freeze-2 journal of the same case folds. |
| C-03 to C-06 | INFO | info | Every changed claim is D-14 to D-10 with `IDENTIFIER_ROLE_COLLISION`; named cases unchanged; D-058, D-059, D-060 tests pass; the reason code is handled by schemas and explanations. |
| C-07 | LOW | open | The scans are quadratic in the events of a candidate's lookups (2.3 s at 3,000 events); the largest real key has 281 events. Stage 02 bounds the evidence per lookup (`DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES`). |
| C-08 | INFO | info | Deterministic. |
