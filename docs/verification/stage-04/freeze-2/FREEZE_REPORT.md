# Stage 04 freeze candidate report (corrective cycle, freeze-2)

Owner instruction D-071 (`cmsg_018VCB51nDHP6HXmLU4ea5yPTDrESsDr75RoYgLhdymUyn`, 2026-11-18T20:07:29Z): gate 04-I
failed at evaluation commit `1064113`; the frozen engine `b5bf8ed` is not final; one corrective cycle, ending with a
complete freeze candidate, then STOP before a new Step 13.

Everything below is development evidence on design-exposed inputs (D-5). It is not an evaluation. No new sample was
drawn, nothing was annotated, the failed campaign was not rerun, and no new pre-registration exists. This is a
**candidate**: it is not a freeze until the owner accepts it.

## 1. Freeze records

| Record | Value |
|---|---|
| Superseded freeze | `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` (engine 0.2.0, dt-1), marked `SUPERSEDED_AFTER_FAILED_04_I` in `../freeze/SUPERSEDED.md`; every file of `../freeze/` unchanged |
| Baseline of the cycle | `f207bc025c992d24b409e5869e3f380bc986e821` (D-071 recorded; `src` identical to `b5bf8ed`) |
| Code revision of the test runs | `99c4194622498b2343584f08b4f6e52cd2f077e3` (`src` and `schemas` equal those of every evidence run, `dfee881` onwards) |
| Evidence commit (parent of the freeze-content commit) | `80e414b0d2d399637a63152f778335ea01e0b44f` |
| Freeze manifest | `FREEZE_MANIFEST.json`, format `citerift-stage04-freeze/2` |
| Manifest digest (SHA-256 of the canonical encoding) | `6be3d310c88ad01ccdb5f9e7987cad6716c7f469399ad5d6d9e41d363b5ab77a` |
| Exposure manifest v2 | `exposure/EXPOSURE_MANIFEST.json`, SHA-256 `932cd65f79d7d72b508923bdfc0892422ee25eeea653b0941370649a595343b5` (built at `7215aa0`) |
| Frozen SHA (freeze-content commit), its tree, its CI run | named by the attestation commit that follows (two-record mechanism) |

The digest is reproduced by `uv run python docs/verification/stage-04/freeze-2/build_freeze_manifest.py` at the
evidence commit, which prints it. The manifest pins 43 Stage 04 source files, 16 Stage 04 schemas, the decision
semantics files, both oracle manifests (frozen dt-1 `41105077…`, kept; dt-2 `60a21534…`), `pyproject.toml`, `uv.lock`,
the exposure manifest and 20 evidence files.

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

- **New suites:** `test_corrective_role_collision.py` (59, adversarial, on an attributed 25-record Retraction Watch
  fixture), `test_corrective_role_property.py` (2; 23,328 combinations against a restatement of SPEC 7.3a),
  `test_corrective_oracle.py` (dt-2 oracle: 25,264,896 cases, 383 distinct decisions, 0 violations),
  `test_corrective_runner.py` (12), `test_corrective_compat.py` (2).
- **Fail-first:** the final role-collision and property suites against the frozen engine's `src` and `schemas`:
  37 failed, 24 passed (`../corrective/evidence/fail_first_final.txt`); the runner fixes fail first on the historical
  tool (`runner_fail_first.txt`).
- **Full suite on `99c4194`:** local (Python 3.12.3) 3,371 passed, 1 failed; CI run 360 (Python 3.12.3 and 3.13.14)
  3,371 passed, 1 failed each, so `ci-gate` is red. The one failure is
  `test_step13_evaluation.py::test_frozen_check_passes_on_the_frozen_engine`, a P-listed test that asserts the
  running engine is the superseded `b5bf8ed`. It is not skipped, marked or edited: P files are untouchable without
  the owner, and the owner's decision is pending.
- `ruff check`, `ruff format --check`, `mypy` (95 files) and `citerift-gov check` (0 errors, 0 warnings) pass.
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
raised. **No CRITICAL or HIGH finding is open.** Open items: owner decisions A-02/B-02/A-10 (strict versus lenient),
B-03 (original DOI with the same record's notice PMID, the mirror of D-058) and C-01 (a same-work sibling record
collides a clean retraction); LOW items D-05, E-05, E-07, C-07, N-01 with stated reasons.

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

## 9. Open owner decisions

1. Strict versus lenient resolution by a second identifier (card `cmsg_018VCB51nDHP6HXmLU4ea5yPHj8evfLAf6BjmudsykjrGy`).
2. Same-work sibling records (C-01; card `cmsg_018VCB51nDHP6HXmLU4ea5yP3kTt3KcXyqmhT7HXKdfzb4`).
3. The P-listed test that pins the superseded engine (card `cmsg_018VCB51nDHP6HXmLU4ea5yPKGg9QN82npdYdMmf5LXJez`); CI
   stays red on it until then.
4. B-03 (original DOI with the same record's notice PMID stays positive, as in dt-1).
5. Acceptance of this candidate, and any new Step 13 (P2, new seed, the 80 campaign articles excluded).
