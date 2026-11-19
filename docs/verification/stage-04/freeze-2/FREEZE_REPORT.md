# Stage 04 freeze candidate report (corrective cycle, freeze-2)

Owner instruction D-071 (`cmsg_018VCB51nDHP6HXmLU4ea5yPTDrESsDr75RoYgLhdymUyn`, 2026-11-18T20:07:29Z): gate 04-I
failed at evaluation commit `1064113`; the frozen engine `b5bf8ed` is not final; one corrective cycle, ending with a
complete freeze candidate, then STOP before a new Step 13. Owner instruction of 2026-11-19
(`cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`, decisions D-072 to D-075): the first candidate (`d8a059d`,
CI run 362 red on one P-listed test) was not accepted; the decisions below were recorded and the candidate was
regenerated from the resulting tree. This report describes the regenerated candidate.

Everything below is development evidence on design-exposed inputs (D-5). It is not an evaluation. No new sample was
drawn, nothing was annotated, the failed campaign was not rerun, and no new pre-registration exists. This is a
**candidate**: it is not a freeze until the owner accepts it.

## 1. Freeze records

| Record | Value |
|---|---|
| Superseded freeze | `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` (engine 0.2.0, dt-1), marked `SUPERSEDED_AFTER_FAILED_04_I` in `../freeze/SUPERSEDED.md`; every file of `../freeze/` unchanged |
| Baseline of the cycle | `f207bc025c992d24b409e5869e3f380bc986e821` (D-071 recorded; `src` identical to `b5bf8ed`) |
| First candidate (not accepted) | content `d8a059d`, manifest digest `6be3d310…`, attestation `2aeb6b5`, CI run 362 red (1 P-listed test) |
| Code revision of the test runs | `032bbaf434291126976c06ad10d6cddeb90408c6` (`src` and `schemas` equal those of every evidence run, `dfee881` onwards); CI run 364 green |
| Evidence commit (parent of the freeze-content commit) | `90282408193bf05cd49a4c9df7c90e853ff0ee9d` |
| Freeze manifest | `FREEZE_MANIFEST.json`, format `citerift-stage04-freeze/2` |
| Manifest digest (SHA-256 of the canonical encoding) | `d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13` |
| Exposure manifest v2 | `exposure/EXPOSURE_MANIFEST.json`, SHA-256 `b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b` (rebuilt at `3ef1e56`; 378 articles, as before; only evidence paths changed) |
| Frozen SHA (freeze-content commit), its tree, its CI run | named by the attestation commit that follows (two-record mechanism) |

The digest is reproduced by `uv run python docs/verification/stage-04/freeze-2/build_freeze_manifest.py` at the
evidence commit, which prints it. The manifest pins 43 Stage 04 source files, 16 Stage 04 schemas, the decision
semantics files, both oracle manifests (frozen dt-1 `41105077…`, kept; dt-2 `60a21534…`), `pyproject.toml`, `uv.lock`,
the exposure manifest and 21 evidence files (the B-03 census added).

## 2. Root cause and correction

- **Failure.** `en-39868218` unit `un-00011` cites DOI `10.1002/asi.23238`. Its Retraction Watch record gives that DOI
  as both the original and the notice DOI (Stage 02 flag `NOTICE_DOI_EQUALS_ORIGINAL`). dt-1 read only
  `PMID_ROLE_COLLISION`, so D-14 attached `RETRACTED_WORK_CITED` (`../corrective/ROOT_CAUSE.md`).
- **Census** of the pinned snapshot `rw-2f116e9ffed718e6` (read-only, `../corrective/census/`): 13,681 DOIs and 1,053
  PMIDs given both roles in one record; 56 DOIs and 27 PMIDs across records. The frozen engine made nearly every such
  DOI positive. Stage 02 already records the evidence; **no Stage 02 maintenance is needed**.
- **Correction (table dt-2, SPEC 7.3a).** D-10 also fires on a role-ambiguous event: an event attached through a key
  that the checked evidence also gives as a notice identifier (any record of the candidate's lookups with the
  same-record flag, or the cited key's own notice hits), unless another cited key with no notice role, whose record
  states a different notice identifier in its scheme, tells the work from the notice. Class `UNRESOLVED_IDENTITY`,
  reason `IDENTIFIER_ROLE_COLLISION` (new; no existing code fit). Never `NOTICE_CITED`. Missing or malformed evidence
  fails closed. The guard sits in D-10, before D-14; the order contradiction → unresolved → operational failure →
  positive → notice/no-finding is unchanged. No DOI, publisher, word or language is special-cased.
- **Resolution by a second identifier (owner decision D-072).** The strict rule is approved: a resolving cited key has
  no notice role, directly identifies the same work, and its record gives a distinct notice identifier in its scheme.
  The lenient alternative is not adopted. Recall cost, stated as a limitation and never as a performance result: of
  31,506 dt-1 positive DOI+PMID pairs of the snapshot, 1,472 abstain under the strict rule (800 would under the
  lenient one). No threshold or holdout-derived special case.
- **Same-work sibling records (owner decision D-073, reviewer finding C-01).** No exemption. The 53 snapshot pairs,
  including `ar-3351802 un-00059`, stay `UNRESOLVED_IDENTITY`; "probable true positive" is descriptive only.
- **Original DOI with the same record's notice PMID (owner decision D-075, reviewer finding B-03).** Positive when the
  clean original DOI independently supports the work; the notice PMID is never positive support and stays visible
  (`KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED` kept); no `IDENTITY_CONFLICT` is made from the notice role; an absent,
  unavailable or role-collided DOI never reaches D-14 through the notice PMID. B-03 census
  (`../corrective/census/B03_CENSUS.json`, 31,279 pairs): 628 positive under dt-2 (794 under dt-1; the 166 that change
  are D-14 to D-10 because the DOI is itself role-collided). 30,482 pairs are `IDENTITY_CONFLICT` under both tables:
  the record also states the work's own, different PMID, an incompatibility witness (SPEC 6.5), unchanged from dt-1.
- **Corrected JASIST result:** `D-10 UNRESOLVED_IDENTITY (IDENTIFIER_ROLE_COLLISION)`, in the regression of the
  campaign article and in `test_historical_jasist_unit_end_to_end`.

## 3. Versions

| Item | Superseded | Candidate |
|---|---|---|
| Engine (`citerift.investigation.__version__`) | 0.2.0 | 0.3.0 |
| Decision table | dt-1 | dt-2 |
| Stage 04 schema set (`common.schema.json`) | 3.0.0 | 4.0.0 |
| `claim.schema.json` | 2.0.0 | 3.0.0 |
| Detector | `citerift-dt1-detector/2` | `citerift-dt1-detector/3 (dt-2)` |
| Reference model / oracle | `dt1_reference.py`, `oracle/` | kept unchanged; new `dt2_reference.py`, `oracle-dt2/` |

An investigation made by the frozen engine is refused by the dt-2 schemas at its first record, never read as dt-2
(`test_corrective_compat.py`).

## 4. Tests and fail-first evidence

- **New suites:** `test_corrective_role_collision.py` (64, adversarial, 5 of them the D-075 boundary tests, on an attributed 25-record Retraction Watch
  fixture), `test_corrective_role_property.py` (2; 23,328 combinations against a restatement of SPEC 7.3a),
  `test_corrective_oracle.py` (dt-2 oracle: 25,264,896 cases, 383 distinct decisions, 0 violations),
  `test_corrective_runner.py` (12), `test_corrective_compat.py` (3, including the freeze-2 dt-2 identity test).
- **Fail-first:** the final role-collision and property suites against the frozen engine's `src` and `schemas`:
  37 failed, 24 passed (`../corrective/evidence/fail_first_final.txt`); the runner fixes fail first on the historical
  tool (`runner_fail_first.txt`).
- **Historical pre-registration (owner decision D-074).** `test_step13_evaluation.py` no longer asserts that the
  running engine is `b5bf8ed`; it verifies the historical freeze from git objects: P
  (`4eded723…1098a`) resolves to the files at `827ac1a`, every listed file's blob there matches its recorded hash, and
  the manifest digest is unchanged; P names the frozen engine `b5bf8ed` (tree and freeze-manifest digest); the
  historical frozen check, run on a detached checkout of `b5bf8ed`, succeeds; the Step 14 campaign `RUN.json` at
  `1064113` equals the tree's copy and records that engine and P; the current dt-2 engine fails the old assertion. The
  only P-listed file that differs from `827ac1a` is that test file, which D-074 authorizes; P, the manifest, the
  campaign, `b5bf8ed` and the scores are unchanged.
- **Full suite on `032bbaf`:** local Python 3.12.3: 3,382 passed, 0 failed, 0 skipped; local Python 3.13.18: 3,382
  passed, 0 failed, 0 skipped. CI run 364 (`44483392722`): `verify (python 3.12)` 3,382 passed, `verify (python
  3.13)` 3,382 passed, test report check 0 problems on both, `pip-audit --strict` no known vulnerabilities, `ci-gate`
  success.
- `ruff check`, `ruff format --check` (623 files), `mypy` (95 files), schema validation (0 problems), the Step 3
  document checker (0 failed), `citerift-gov check` (0 errors, 0 warnings) and `render-status --check` pass. The frozen
  dt-1 oracle (`41105077…`) and `dt1_reference.py` are unchanged since `b5bf8ed`; the dt-2 oracle (`60a21534…`) tests
  pass.
- One existing test was narrowed in meaning-preserving form: `test_oracle_and_model_unchanged_by_step5` now refuses
  any modification, deletion or rename of a `simulations/stage04` file that existed at `244c4b6`, and allows the files
  D-071's new oracle version adds.

## 5. Regression (development evidence only)

| Set | Candidates | Changed claims | Detail |
|---|---|---|---|
| 232 development revisions | 4,614 | 1 | `en-1382450117 un-00008` `CONCERN_CITED` → `UNRESOLVED_IDENTITY` |
| 80 campaign articles | 4,920 | 4 | `RETRACTED_WORK_CITED` → `UNRESOLVED_IDENTITY`: `en-39868218 un-00011` (JASIST), `en-1741558 un-00016`, `en-12228277 un-00110`, `ar-3351802 un-00059` |
| Named cases (Wakefield/MMR, Obokata ar/en, GFAJ-1, EoC, BCAS3, reserves) | 8 cases | 0 | classes unchanged |
| Snapshot DOI+PMID pairs | 31,756 | 1,570 | 1,472 positives lost under the strict rule (800 under the measured lenient alternative) |

No new positive, no new `NOTICE_CITED` and no new not-found anywhere. dt-1 re-decided on the committed inputs equals the
frozen runs (dev: 0 mismatches; campaign: 4,649 historical claims, 0 mismatches). D-058, D-059 and D-060 stay pinned by
their tests. The regression was never joined with the campaign's labels (reviewer finding F-08).

## 6. Runner fixes

`../corrective/runner/s13_run_v2.py` (the historical `s13_run.py` is unchanged): the Memory root is outside the
repository, at a configured path recorded only as an operational locator, created private or refused when shared or
symlinked; the export parent is created before the first article; every article runs the engine with `python -I`
after an engine-identity probe; it refuses to run where a `RUN.json` exists.

## 7. Reviews

Six fresh reviews (A semantics, B identifiers and roles, C regression risk, D provenance, E security, F evaluation
leakage) plus a re-verification of the D, E and F fixes; dispositions in `../corrective/review/TRIAGE.md`. One CRITICAL
(B-01, a pair whose two keys are each a notice identifier in different records) was fixed and re-verified. No HIGH was
raised. The MEDIUM items put to the owner are decided: A-02, B-02 and A-10 by D-072, C-01 by D-073, B-03 by D-075.
**No finding of MEDIUM or higher is open.** Open LOW items D-05, E-05, E-07, C-07 and N-01 keep their stated reasons.

## 8. Vertical slice, D-062 and performance

- **Vertical slice** (`vertical-slice/`, 149 calls in `unshare -rn`, 0 network attempts): all 220 named checks pass
  (`failed_checks` empty), VS-1 to VS-10, checkpoint and I-2 included.
- **D-062 two builds** (`d062/two_build_equivalence.json`): different file hashes, equal canonical identity
  (`artifact_digest adcf7b65…`, `semantic_digest 7b2a2344…`, 147,152 export lines); the seven cases give equal keys and
  content across builds; 0 failed checks.
- **D-062 tamper differential** (`d062/tamper_differential.json`): 21 cases, 0 discrepancies, none rejected by the
  profile alone; the 5 operational tests pass.
- **Performance** (D-061 target ≤ 5 s p95): **NOT_MET**, as accepted in D-066. Run p95 25.2 to 30.5 s (superseded
  freeze 25.5 to 30.5 s); the D-062 identity verification takes 26.1 s of the 32.7 s VS-1 breakdown run
  (`performance/`). The correction adds no measurable cost.

## 9. Owner decisions and what remains

Recorded in `DECISIONS.md`: D-072 (strict rule), D-073 (no same-work-sibling exemption), D-074 (the historical P test
verifies the historical freeze), D-075 (B-03 stays positive on a clean original DOI). Open: acceptance of this
candidate by the owner, and any new Step 13 (P2, new seed, the 80 campaign articles excluded), which is not started.
Any future P2 states the D-072 recall cost and the D-073 abstentions as limitations.

**Validation of the vertical slice, D-062 and performance (section 8)** comes from runs on `src` and `schemas` that are
byte-identical to those of `032bbaf` (unchanged since `dfee881`); these runs were not repeated.
