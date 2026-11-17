# Stage 04 freeze report (Step 12)

Owner authorization `cmsg_018VCB51nDHP6HXmLU4ea5yPTS6uNNfzMEoiA4s4Jo33LV` (2026-11-17T08:25Z): Step 12, independent
review, pre-freeze corrective closure and formal freeze, from baseline `65c30bde697dced5f1698fb3db46707b939cc0c7`.
Owner decisions during the step: OD-S12-1 (`cmsg_018VCB51nDHP6HXmLU4ea5yPX6tov3HkhvFC2ppixAiwyL`, recorded as D-064)
and OD-S12-2 (`cmsg_018VCB51nDHP6HXmLU4ea5yPQBMQAvkyRYvCrNmrZM88n8`, recorded as D-065).

Everything below is development evidence on design-exposed inputs (D-5). It is not an evaluation. Step 13 has not
started: no holdout sample was drawn, enumerated, inspected or profiled, nothing was annotated, and no final
prediction was run.

## 1. Freeze records

| Record | Value |
|---|---|
| Baseline | `65c30bde697dced5f1698fb3db46707b939cc0c7` |
| Code revision of the freeze evidence | `3eec84f63467192407934dda2de544338a5d9140` (CI run 337, green) |
| Evidence commit (parent of the freeze-content commit) | `bdeeac10135043fec65734e47c78c4437a1da4c6` |
| Freeze manifest | `FREEZE_MANIFEST.json`, format `citerift-stage04-freeze/1` |
| Manifest digest (SHA-256 of the canonical encoding) | `609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc` |
| Frozen SHA (freeze-content commit), its tree, its CI run | named by the attestation commit that follows (two-record mechanism, owner section 22) |

The freeze-content commit holds this report and the manifest, so neither can name that commit. The manifest names its
parent, the code revision of the evidence and the SHA-256 of every frozen file: 43 Stage 04 source files, 16 Stage 04
schemas, the decision-semantics files, the Step 4 oracle manifest (`41105077…`), `pyproject.toml` and `uv.lock`, the
exposure manifest and the eight evidence files. The digest is reproduced by
`uv run python -P docs/verification/stage-04/freeze/build_freeze_manifest.py`, which prints it.

After the freeze only the Step 13 pre-registration may be added. Any change to frozen scientific code or semantics
needs an explicit, freeze-breaking owner decision.

## 2. Files changed since the baseline

124 files at `bdeeac1` (23,812 insertions, 377 deletions), plus the files of the freeze-content commit.

- **Stage 04 code**: 22 files in `src/citerift/investigation/` (857 insertions, 259 deletions).
- **Schemas**: three files in `schemas/investigation/v1/` (`common`, `lookup-observation`, `projection-set`).
- **Tests**: 21 files in `tests/stage04/`, three of them new (`test_step12_d062.py`, `test_step12_fixes.py`,
  `test_step12_semantics.py`).
- **Documents**: SPEC and MM sections, the Step 11 evidence README and scripts, the six review reports and the
  triage (`review/step12/`), the prior-art review, and the freeze evidence (`freeze/`).
- **Governance**: `DECISIONS.md` (D-064, D-065), `governance/stage_registry.json` and the maintenance record
  `docs/verification/maintenance/A-00-003/`.
- **Stage 00 CI**: `.github/workflows/ci.yml`, one line (`timeout-minutes: 20` to `30`, verify job, OD-S12-2). It was
  made through the Stage 00 maintenance transaction A-00-003 (candidate `0c643e6`, pending record `47bdbe2`, finalized
  `91c70af`). No other `.github/` change.
- **Unchanged** between the baseline and `bdeeac1`: accepted Stage 01–03 code (`src/citerift/retraction`,
  `src/citerift/wiki`, `src/citerift/contracts`, `schemas/contracts`), governance code and schemas, and the Step 4
  oracle (`simulations/`).

## 3. Independent review and findings

Six read-only reviews (A scientific semantics, B architecture and reliability, C integration and reproducibility,
D security, E evaluation readiness, F CLI and user semantics) ran in fresh contexts on the baseline. Their reports were
committed verbatim (`9499c49`) before any correction. The triage, with every disposition and the test that covers it,
is in `../review/step12/STEP12_TRIAGE.md`.

**Tally**: 76 rows, including 4 findings of the Step 12 lead (L-01 to L-04). By severity: 4 HIGH, 20 MEDIUM, 39 LOW,
12 INFO and 1 n/a. No CRITICAL finding.

**HIGH findings**, none left open:
- C-01 (scientific identity bound to the SQLite file hash): fixed by D-062.
- C-02 (Stage 02 verify per process against ≤ 5 s): resolved by the owner (OD-S12-1, D-064). The target stays NOT_MET.
- C-03 (`artifact_digest` alone does not prove what LOOKUP read): met by design, because the verification recomputes
  the digests from the content it reads.
- L-01 (D-062 reuse could store an identity under a replaced file's fingerprint): fixed, test
  `test_a_file_replaced_during_the_lookup_fails_closed`.

**Step 4 oracle**: no oracle defect was found. The oracle (`simulations/`) is unchanged.

**L-04** was found by the freeze vertical-slice run, before any freeze commit. A resume before `not_before` took
24.9 s against 0.49 s at Step 11, because every command verified the index. It was fixed in `3eec84f`: the index
identity is established only by LOOKUP and the steps that depend on it (`STEP_IDENTITIES`). The evidence from the
earlier revision was discarded and the whole freeze evidence was produced again from `3eec84f`.

## 4. D-062: canonical Stage 02 index identity

**Design.** The Stage 04 index identity is the canonical Stage 02 identity: `snapshot_id`, `policy_version`,
`lookup_schema_version` and `artifact_digest` (scientific), plus `semantic_digest` and `export_lines` (consistency).
The SQLite file bytes are never part of it.

A process accepts the identity only after `adapters/lookup.verify_index_identity` has recomputed it from the index
content, in this order:
1. Stage 02 format and policy checks (`application_id`, `user_version`, `meta.policy_version`).
2. `structural_problems`: `integrity_check`, `foreign_key_check` and the Stage 02 invariants.
3. `compute_digests`, compared with the stored metadata.
4. `manifest_problems` (the build manifest).
5. `derivation_problems` (full re-derivation of every record and derived table, compared with the stored ones).

This is the D-062 identity-verification profile chosen by the owner (OD-S12-1, D-064). It omits only Stage 02's
per-event JSON-Schema pass. Stage 02's complete `verify` stays the certification, is unchanged, and is never called
"the profile".

Reuse inside a process is keyed by the file fingerprint (dev, inode, size, mtime_ns, ctime_ns) taken before the open.
An entry is stored only if the fingerprint is unchanged after the verification. Failures are never cached, and nothing
is reused across processes. The file SHA-256 is only the operational guard around LOOKUP (before and after). The keyed
identity must equal the verified one (B-01). The policy and lookup-schema versions come from the running code on every
use (L-02). A tampered index is refused (`INDEX_CORRUPT`, exit 3), never reported as stale. An index whose identity
cannot be established is `IdentityUnavailable` (MM 10.2).

**Equivalent-rebuild proof** (`d062/two_build_equivalence.json`, from `3eec84f`). Two independent builds of the pinned
snapshot (`csv_sha256 2f116e9f…`) gave:

| Property | Build A | Build B |
|---|---|---|
| File SHA-256 | `cd9d1256…` | `2ffec44f…` (different) |
| Bytes | 278,769,664 | 278,769,664 |
| `artifact_digest` | `adcf7b65…16d9` | equal |
| `semantic_digest` | `7b2a2344…5f88` | equal |
| `export_lines` | 147,152 | equal |
| Identity verification (profile) | 23.6 s | 24.4 s |
| Stage 02 complete `verify` | 80.1 s, no problem | 81.1 s, no problem |

For each of the seven design-exposed cases, both builds gave the same investigation key and identical scientific
content, and a replay against the other build was reproduced and never stale. Failed checks: none.

**Tamper results** (`d062/tamper_differential.json`, mandatory under OD-S12-1). There were 21 cases on a real Stage 02
index with its manifest, each checked by Stage 02's complete `verify` and by the profile:
- Both accept 3 cases: the untampered control; a different but consistent artifact (another canonical identity, so
  STALE); and a size-preserving byte flip at the file midpoint, which `dbstat` places in unallocated space of a
  `notice` leaf page, so the identity is unchanged.
- Both reject the other 18. These include forged stored digests, mutated raw records, events and derived tables, a
  missing or mismatched manifest, schema-invalid event fields with the metadata and manifest recomputed, and two
  direct byte edits of stored row content.
- Discrepancies: none. No case is rejected by complete `verify` alone, and none by the profile alone.

The five operational cases pass as named tests in `test_step12_d062.py` (`5 passed`):
- inode replacement with the same size and times;
- a size-preserving in-place change with the mtime restored, after reuse;
- a change after reuse;
- a replacement during LOOKUP;
- failures are never reused.

## 5. Named corrections and version changes

- **I-2** (UF-12): one pure outcome rule, `report.outcome()` (S-9.7), used by ASSEMBLE. The fold-only
  `workflow.outcome` was removed, and `status_of` fails closed for COMPLETED without an outcome. The VS run checks it
  (VS-1 `partial`, exit 6; VS-2 `needs_resolution`, exit 10).
- **I-4**: the projection-set schema now describes what is stored: the SHA-256 of each stored v1 projection body
  (without `created_at`), one per distinct work with a positive claim. Exported records add `created_at` and are named
  by the body digest.
- **A11-5** (UF-02): the user-facing status is `blocked` (exit 8) whenever no step may start before `not_before`. This
  covers lifecycle BLOCKED and also RUNNING after a retryable failure. The JSON output keeps `lifecycle` and `next`, and
  the lifecycle and journal are unchanged.
- **A11-6** (C-04, C-06): paths are operational locators. `resume`, `replay`, `verify`, `show` and `export` accept
  `--index` and `--bundle`, a relocation test was added, and the VALIDATE output names no path. Journals keep the
  creating host's paths as provenance outside every scientific digest.
- **MM EV-2** (A-08): MM 4.6 EV-2 replaced by Reviewer A's wording.
- **Versions** (A-6 / I-3), so a changed engine is a changed input (STALE):

  | Item | Before | After |
  |---|---|---|
  | Stage 04 engine (`citerift.investigation.__version__`, now `engine_version`) | 0.1.0 | 0.2.0 |
  | Stage 04 schema set | 2.0.0 | 3.0.0 |
  | `lookup-observation` | 1.0.0 | 2.0.0 |
  | Detector | `citerift-dt1-detector/1` | `citerift-dt1-detector/2` |

  Unchanged: `lookup-plan` 1.0.0, `plan-1`, table `dt-1`, and the v1 contracts.

## 6. Vertical slice (VS-1 to VS-10)

The run used `freeze/vertical-slice/` from `3eec84f`, with Python 3.12.3 on x86_64 with 4 CPUs. The pinned index is
`rw-2f116e9ffed718e6`, 278,769,664 bytes. There were 5 repeats per case, and every call ran in `unshare -rn` (149 calls,
0 network attempts).

All 220 named checks passed (`failed_checks` is empty):
- VS-1 to VS-6b: classes, wording, VERIFY, v1 contracts and export.
- VS-7a to VS-7e: corrupt or invalid inputs FAILED, or refused with exit 3 before any investigation exists.
- VS-8a to VS-8c: missing index, wrong format, and Retry-After BLOCKED with exit 8. The resume before `not_before` took
  0.29 s.
- VS-9: SIGKILL inside DETECT at three points. ACQUIRE to LOOKUP was not repeated and the result was the same.
- VS-10: STALE naming the changed input. Another index build was reproduced. Forged index metadata was refused.
- Also passed: the external checkpoint match and the I-2 outcomes.

## 7. Performance (D-061 target: warm retained investigation ≤ 5 s p95)

**Status: NOT_MET.** The target is not redefined.

| Case | n | Run median | Run p95 | Step 11 run p95 | Replay p95 | ≤ 5 s |
|---|---|---|---|---|---|---|
| VS-1 | 5 | 30.230 s | 30.464 s | 6.572 s | 27.160 s | no |
| VS-2 | 5 | 26.437 s | 27.633 s | 3.746 s | 26.300 s | no |
| VS-3a | 5 | 26.132 s | 26.370 s | 3.775 s | 25.034 s | no |
| VS-3b | 5 | 28.193 s | 29.268 s | 5.390 s | 26.830 s | no |
| VS-4 | 5 | 26.171 s | 26.297 s | 3.338 s | 25.651 s | no |
| VS-5 | 5 | 25.598 s | 26.310 s | 3.717 s | 25.242 s | no |
| VS-6a | 5 | 24.812 s | 25.522 s | 2.940 s | 25.241 s | no |
| VS-6b | 5 | 24.899 s | 25.977 s | 3.020 s | 27.158 s | no |

With 5 samples, p95 is close to the maximum.

**Cause, measured.** For VS-1 (`performance/perf_breakdown.json`, medians), the run takes 30.1 s:

| Part | Time |
|---|---|
| D-062 identity verification | 24.2 s |
| Schema validation | 3.5 s |
| File hash guard | 0.45 s |
| Unaccounted | 1.9 s |

The identity verification (D-064) runs in every process that reaches LOOKUP, because nothing is trusted across
processes. By component, it takes 25.3 s (`performance/verification_components.json`):

| Component | Time |
|---|---|
| Derivation recompute | 15.4 s |
| Digests | 6.2 s |
| Structural checks (`foreign_key_check` 2.6 s, `integrity_check` 0.9 s) | 3.5 s |

The repeated read passes cost under 1 s in total, so the work is CPU-bound. A single shared pass would save at most
about 1 to 1.5 s, would still leave about 23 to 24 s, and would need a change to accepted Stage 02 functions, so it was
not made. No validator cache was added: construction takes 0.008 s of the 3.5 s (`schema_validation_profile.json`).

Under D-064 and the rule against caching across processes, the identity verification alone is about five times the
target. No check was removed or weakened.

## 8. Prior art, differentiation and exposure

The primary-source review (gate 04-J) is in `../review/step12/PRIOR_ART_04J.md`. It covers:
- Retraction Tracker for Wikipedia;
- RetractionBot;
- Zotero retracted-item notifications;
- Crossref REST and Crossmark;
- the Retraction Watch Database;
- Shi et al., "The Persistence of Retracted Papers on Wikipedia".

scite and Problematic Paper Screener could not be assessed.

DOI and PMID matching against Retraction Watch, separating concerns from retractions, notice DOIs, revision anchoring
and daily English coverage all exist already, and none of them is claimed as new.

CITERIFT's combination, as built in Stage 04, is:
- a typed, abstention-first verdict from a versioned first-match table (dt-1);
- DOI/PMID cross-examination that routes a witnessed conflict to an open question;
- content-addressed evidence chains with offline replay;
- Arabic and English through the Stage 03 profiles.

Whether this reduces false attachments is not yet measured: only the frozen engine on the pre-registered holdout can
measure it. No "first", "only" or "unprecedented" claim is made.

**Exposure manifest**: `exposure/EXPOSURE_MANIFEST.json`, SHA-256
`5a6d466f0cccb671afac9bcd9ad9660374a017df434d419f33aa94c20abeb83b`, from `bdeeac1`. It lists 298 design-exposed
articles (en 166, ar 132; 9 keyed by title because no page id is recorded), identified by (wiki, page_id), from eight
listed sources. Its frame-exclusion rule is recorded for the pre-registration.

## 9. Limitations

These are the `limitations` list of `FREEZE_MANIFEST.json`, in summary:
- D-061 NOT_MET (section 7).
- The D-062 profile omits the per-event JSON-Schema pass, which is in complete `verify` only; no tamper case depends on
  that pass.
- The F-11 descendant scan bound.
- The checkpoint detects divergence and is not a signature.
- Memory needs a local POSIX filesystem.
- AI-generated labels are planned for Step 14.
- Snapshot coverage stops at the snapshot date.
- Some dt-1 classes are covered only synthetically.
- The Step 4 model's independence is procedural.
- A-07, B-03 residual, B-13 and C-12 (upstream).
- A11-5 and A11-6 as described.
- E-05, E-06 and E-08 are left to the pre-registration.

## 10. Tests and CI

The suite has 3,249 tests, 1,177 of them in `tests/stage04`, with zero skipped.

**Local run** on `3eec84f`: 3,249 passed (Python 3.12.3, 18 min 48 s, 4 vCPU).

**CI run 337** on `3eec84f` (id 44179654515) was green:

| Job | Tests | Test step | Job | check-report |
|---|---|---|---|---|
| Python 3.12.3 | 3,249 passed | 19 min 34 s | 19 min 56 s | 0 problems |
| Python 3.13.14 | 3,249 passed | 11 min 30 s | 11 min 53 s | 0 problems |

The clean-tree check passed, `pip-audit --strict` found no known vulnerability, and `ci-gate` was green.

**CI runtime under OD-S12-2.** The verify job timeout is 30 minutes. 18 minutes is diagnostic only.

| Run | Commit | 3.12 tests | 3.13 tests | Result |
|---|---|---|---|---|
| 332 | `9499c49` | 10m16s | 11m29s | success |
| 333 | `75e7b26` | 19m53s | 17m07s | cancelled at the old 20-minute limit |
| 334 | `00c2d6c` | 19m40s | 11m28s | cancelled at the old 20-minute limit |
| 335 | `91c70af` | 13m59s | 10m06s | success |
| 336 | `c23e5dc` | 12m32s | 18m03s | success |
| 337 | `3eec84f` | 19m34s | 11m30s | success |

Runs over 18 minutes alternate between the Python versions on the same code. In run 337, untouched Stage 00–03 test
files ran a median 1.46× slower on 3.12 than in run 335, and Stage 04 files 1.44× slower, while per-file times on 3.13
equal run 334 (1.00×). This is recorded as GitHub-hosted runner variance under OD-S12-2: the slowdown is not localized
to Step 12 tests or code, and no required job reached 30 minutes. The CI run on the freeze-content commit itself is
named, with its timings, by the attestation commit.

## 11. Governance

- Stage 04 stays `IN_PROGRESS`. No stage transition was made, and Step 13 is not authorized.
- D-064 (OD-S12-1) and D-065 (OD-S12-2) were recorded with the owner's message ids.
- Stage 00 maintenance A-00-003 was finalized; `citerift-gov check` reports 0 errors.
- The A-00-003 declared scope is cumulative from the accepted Stage 00 baseline `0c21182`, as the maintenance mechanism
  requires: the eight A-00-002 files, unchanged, plus `ci.yml`. It is documented in the maintenance record.
- No pull request was opened and nothing was merged.

## 12. Owner decisions still open

1. **Performance.** Accept NOT_MET (D-061) at freeze, or decide otherwise. Under D-064 and the rule against caching
   across processes, the per-process identity verification alone (about 24 s) exceeds the 5 s target. Any route to
   the target changes either the verification scope or the reuse rule, and both are owner decisions.
2. **E-05 and E-06**: the identity-conflict denominator and the precision coverage, for the Step 13 pre-registration.
3. **E-08**: the sensitivity variants and baseline scorer are not in the frozen code. Adding them after the freeze
   needs a freeze-breaking decision; otherwise they belong to the pre-registration.
4. **A-00-003 scope**: owner awareness of the cumulative declared scope (no action needed unless the owner objects).
