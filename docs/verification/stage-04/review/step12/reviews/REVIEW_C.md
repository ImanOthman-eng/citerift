# Stage 04 pre-freeze review: Reviewer C (integration and reproducibility)

Repository `/home/user/citerift` at HEAD `65c30bd`. This review was read-only: no repository file was changed and no state-changing git command was run. All scratch work is under `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/review-C/`.

## 1. Scope and method

- **Code read:**
  - `src/citerift/investigation/adapters/{lookup,plan,acquire,validate,verify,assemble}.py`, `operations.py`, `ids.py`, `fold.py`, `memory.py`, `controller.py`, `workflow.py`, `canonical.py`
  - `src/citerift/retraction/{store,export,query}.py`
  - Stage 04 SPEC sections 4, 5, 10 and 14; Stage 02 SPEC 10.4 and RISK E8/E10; STEP11_CLOSURE A11-3 and A11-6; DECISIONS D-061 to D-063.
- **Experiments:** all used `.venv/bin/python` (3.12.3, SQLite 3.45.1, Unicode 15.0) and `venv313b` (3.13.18, SQLite 3.53.1, Unicode 15.1). `CITERIFT_WIKI_NETWORK_LOCK` pointed at a scratch file. There was no network use and no evaluation or holdout input.
  1. The fixture index (`tests/stage04/step8_support.build_index`) was built twice under 3.12 and twice under 3.13 (`build2.py`).
  2. Stage 02 verify was timed by component on an existing full pinned index: `scratchpad/rw/index/rw-2f116e9ffed718e6.sqlite`, 278,769,664 bytes. A second independent full build in `scratchpad/vs-final/index` was compared without modifying either file (`time_verify.py`, `time_parts.py`).
  3. A tamper matrix of 15 cases ran on copies of the fixture index (`tamper.py`, `forge.py`; results in `tamper_results.json`).
  4. Relocation experiments used the real CLI on bundle `tests/stage03/fixtures/observed/en-1372543632` with the fixture index (`reloc/`, `ops.sh`, `cmpj.py`).
  5. 3.12 and 3.13 were compared: same-path runs, cross-interpreter replay/verify, the Unicode database difference, and verify of a full 3.12-built index under 3.13.

## 2. Findings

| Id | Title | Severity | Evidence | Proposed classification | Suggested fix |
|---|---|---|---|---|---|
| C-01 | Scientific identity is bound to the raw SQLite file SHA-256 (known A11-3) | HIGH | `lookup.py:56-62` puts `index_sha256` into the identity, which is embedded in every lookup observation (`lookup.py:102`) and the report (`assemble.py` `"index": index_identity`). Rebuilt fixture: same key and projection set `ca7c91e9…`; report `7470058e…` became `65004ee8…`; C(J) differs; 3 of 33 claim ids changed (2 RETRACTED, 1 NOT_FOUND; the 30 NO_IDENTIFIER claims are unchanged). Replay against a rebuild at the same path: `stale ["index"]`, exit 11 (R5). | 1 (known; owner-directed fix D-062) | Implement D-062 as in section 3. |
| C-02 | Running Stage 02 verification once per process, as D-062 says, conflicts with the D-061 ≤ 5 s target on the full index | HIGH | Measured on the full index (3.12): `verify` total **71.65 s**, RSS 544 MB. Under 3.13: 73.56 s. Components: structural 2.77 s (integrity_check 0.68, foreign_key_check 1.60); `compute_digests` 5.02 s; `derivation_problems` 12.26 s (ident part alone 5.29 s); `event_problems` 49.73 s. Today: 10 `file_sha256` calls per warm run, about 1.9 s in total (`perf_breakdown.json`). Fixture index: verify 0.009 s. | 3, needing an owner decision (4) | See section 3, options A, B and C. Even the minimal sufficient subset (option B, about 11 s) makes every run, replay and verify slower than today. Cross-process reuse keyed by a content hash (option C) needs explicit owner approval, because D-062 forbids caching across processes. |
| C-03 | `compute_digests` and `artifact_digest` alone do not prove what LOOKUP reads | HIGH (design requirement) | T3a: an edited `ident` row leaves `artifact_digest` unchanged, yet the lookup for `10.9999/zzz` changes; only `derivation_problems` (IDENT_INCONSISTENT) catches it. T7: the `event_original_doi` and `event_original_pmid` b-tree rootpages are swapped; digests and derivation both pass; DOI and PMID lookups change (false `no_record`); only `PRAGMA integrity_check` catches it. T8: the DDL affinity of `event.original_pmid` changes to INTEGER; the PMID lookup changes; only integrity_check catches it ("TEXT value in event.original_pmid"). | 4 | The Step 12 design must keep, at minimum, integrity_check, `compute_digests` compared both with meta and with the recorded identity, ident derivation (preferably all of `derivation_problems`) and `manifest_problems`. No cost cut may drop integrity_check or the ident derivation. |
| C-04 | A byte-identical index at another path reads as STALE; replay, verify and resume cannot be pointed at it | MEDIUM | `plan.py:98` derives the index identity from the absolute `request["index_path"]` recorded at creation. The CLI has no `--index` for replay, verify or resume (`cli.py:106-124`). R3 (index moved) and R4 (whole tree moved): replay and verify give `stale ["index"]`, exit 11. R6 (a symlink at the old path) gives `reproduced`. This survives D-062 unchanged. | 1 (reproducibility defect; spec 10.4 does not say which index) | Treat the index path as an operational locator. Add `--index` (and optionally `--bundle`) to replay, verify and resume, defaulting to the recorded path. Staleness is then decided by the canonical identity only. |
| C-05 | The mutation-guard stat tuple omits `ctime_ns` | LOW now; HIGH if the file hash is removed | `lookup.py:51` uses `(dev, ino, size, mtime_ns)`. T11: an in-place byte edit followed by `os.utime` restoring mtime leaves this tuple identical; only ctime and the file SHA differ. Today the second `file_sha256` (`lookup.py:143`) masks the gap. | 2 (latent) | Use `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` for the guard and for the reuse key. |
| C-06 | Absolute paths reach step keys and step outputs, not only the request (extends A11-6) | LOW | The VALIDATE output blob is `{"validated": request}` with all three paths (`validate.py:60`). It is a dependency of later steps, so every `step_key`, `outputs` and step manifest differs between two otherwise identical runs at different paths: 16 payloads differ, plus 8 path-dependent blobs. The investigation key, C(J) `10e4fd05…`, report `7470058e…` and claims are identical (fresh run in `reloc/X`). | 5 / 8 | Make the VALIDATE output path-free (for example the request without the three paths, or `request_key` plus config) so step keys are independent of paths and machines. |
| C-07 | `run` idempotency depends on how the path is spelled | LOW | Creation compares the whole payload (`memory.py:185`). The same inputs with `--memory-root …/A/../A/memory`, or `run` after moving the memory root, give `INVESTIGATION_REQUEST_DIFFERS`, exit 3. Documented in `STEP10_CLOSURE.md:223-225`. | 5 | Optionally normalise paths (`resolve()`) before building the request, or compare `request_key` plus config instead of the full payload. |
| C-08 | A different bundle placed at the recorded bundle path makes an existing investigation STALE `[root]` | LOW | `plan.py:106-118`. R7 gives `stale ["root"]`, while a missing bundle (R2) gives `reproduced`. The investigation already holds the retained bytes and is keyed by `capture_sha256`. Consistent with S-4.4 and the `plan.py` docstring. | 5 | Consider ignoring the path once the root is bound (the request key fixes the capture), or report it as `differs-input` rather than STALE. |
| C-09 | Index symlinks are handled inconsistently between `run` and replay/verify | LOW | `validate.py:51` (`follow_symlinks=False`) makes a fresh `run` with a symlinked index FAILED, exit 9 (`INDEX_PATH_INVALID`). That FAILED investigation then occupies the key: re-running with a correct path gives exit 3 (REQUEST_DIFFERS). Replay accepts a symlink at the recorded path (R6). | 4 | Either resolve the index path in the CLI or refuse at the request boundary (exit 3, as D-063 does) rather than creating a FAILED investigation. |
| C-10 | A verified canonical identity proves the index is internally consistent, not that it came from the pinned CSV | INFO | T12 / `forge.py`: an index built from a modified CSV, with meta `snapshot_id`, receipt and `source_*` patched back and digests recomputed, passes `verify` (no source) and claims `rw-1b7aa3769eb089af`. The lookup then says `correction` instead of `retracted`. It is caught only by: a different `artifact_digest` versus the recorded one; `verify(source=CSV)` (SOURCE_RECORD_MISMATCH); or a pinned expected digest. The accepted snapshot's digest is already pinned in `docs/verification/stage-02/HANDOFF.md:128` and `evidence/verify-rw.json`. The current file-SHA design has the same property. | 8 (owner option) | Optionally compare `(snapshot_id → artifact_digest, semantic_digest, export_lines)` with a pinned table for accepted snapshots. |
| C-11 | The build manifest is a mutable sibling file that Stage 04 currently ignores | INFO | T6 and T6b: a mismatched or missing manifest is caught only by `verify(manifest_path=…)`. The index content is unchanged. D-062 requires that a manifest mismatch does not pass. | 4 | Decide whether a missing manifest also refuses. If so, relocation must move `*.manifest.json` together with the index (`store.manifest_path_for`). |
| C-12 | `Index.crossref_sources` has no `ORDER BY` | LOW | `query.py:230-233`: row order comes from the query plan, which currently uses index `cr_attempt_work`. The result enters `checked_sources` and therefore lookup observations. `cr_attempt` has 0 rows in the accepted RW-only index. | 6 (upstream Stage 02) | Add `ORDER BY attempt_id` in Stage 02 maintenance, before any corroboration index is used. |
| C-13 | The Stage 02 SPEC 10.4 export description is incomplete | INFO | The SPEC lists snapshot, record, event, quarantine, dup_group and cr_assertion. The code also exports `cr_attempt` and semantic lines for quarantine, cr_attempt and cr_assertion (`export.py:153-174`). | 6 | Correct the documentation. |
| C-14 | Redundant identity work: the full identity vector, including the index hash, is recomputed for every step | MEDIUM | `controller.py:229-234` and `334`. VALIDATE, ACQUIRE, EXTRACT and NORMALIZE do not depend on `index` (`workflow.py:114-123`), yet each attempt hashes the file: 10 `file_sha256` calls per run. | 3 | With D-062, compute the index identity at most once per process through the reuse cache. Never run verification once per step. |

**C-01.** This is the known A11-3 defect, confirmed again. The index identity flows into every lookup observation, so into evidence ids, claim ids, the report and C(J). Only the claims that depend on a lookup change. The projection-set digest and the investigation key do not.

**C-02.** This is the decisive design fact for D-062. D-061 expected D-062 to remove redundant identity work. A literal "Stage 02 `verify` once per process" instead raises warm-run identity cost from about 1.9 s to about 72 s on the full index. `event_problems` (JSON-Schema validation of about 73k events) accounts for 69% of that. Measured on 4 cores.

**C-03.** Coverage was established by experiment, not inference. `artifact_digest` covers the snapshot meta line, `raw_record`, `event`, `quarantine`, `dup_group`, `cr_attempt` and `cr_assertion` (`export.py:117-174`). It does not cover:
- `ident`, `notice`, `event_notice`, `title_token` and `token_df` (checked only by `derivation_problems`, `export.py:214-266`);
- SQLite secondary indexes and DDL (checked only by `PRAGMA integrity_check`, `store.py:529`);
- meta keys outside the snapshot line (T10: `run_built_at`) and `sqlite_stat1` (T9). Neither changes lookup results.

**C-04.** On another machine, replay or verify reproduces only if the index sits at the exact original absolute path. The bundle path and memory root do not matter (R1, R2).

**C-05 to C-09.** These are path and stat-sensitivity issues found while relocating. None changes scientific content. C-04 and C-09 are the only ones that give a wrong verdict.

**C-10 and C-11.** These are inputs for owner decisions on the trust anchor, not defects.

**C-12 to C-14.** C-12 and C-13 are minor upstream items. C-14 is the main current performance cost.

## 3. D-062 design analysis

### 3.1 Facts

- **Same content gives the same digest across builds and versions.**
  - Fixture, 3.12 build twice: file SHA `44de9dd1…` and `d62bb514…` differ by exactly 1 byte (`run_built_at`). `artifact_digest aa9dd886…`, `semantic_digest e0771f3f…` and `export_lines 13` are identical.
  - Fixture, 3.13 build twice: file SHA `505ba000…` and `9b659b67…` (10,868 bytes differ from the 3.12 build). The same `aa9dd886…` / `e0771f3f…`.
  - Full index, independent builds of 2026-11-12 and 2026-11-16: file SHA `b3fa48ca…` and `f6bd5e6e…`. Both `artifact_digest adcf7b65…`, `semantic_digest 7b2a2344…`, `export_lines 147152`. This equals the pinned value in `HANDOFF.md:128`.
  - Under 3.13, `verify` of the 3.12-built full index passes with the same digests.
- **What each digest covers:**
  - `artifact_digest`: the ordered canonical lines listed under C-03, ids and ordinals included. This is the correct scientific key.
  - `semantic_digest`: a sorted multiset that excludes ordinals, ids, line numbers and snapshot id (`export.py:97-114`, `186-187`). Permutation-invariant. Lookup observations, however, carry ordinal-derived ids and `#record=N` locators. So `semantic_digest` must not be the key; keep it only as metadata.
  - `export_lines`: a line count.
- **The function that proves current content matches a stored digest** is `export.verify(conn, source=None, manifest_path=None)` (`export.py:284-330`). It:
  - recomputes `compute_digests` and compares with meta (DIGEST_MISMATCH, `:292-295`);
  - runs `structural_problems` (integrity_check, foreign keys, accounting);
  - runs `manifest_problems` (`:296-301`) and `derivation_problems`;
  - runs `event_problems`.
  A meta digest string alone proves nothing: T4a shows a forged meta digest is detected only by recomputation.
- **Replay and VERIFY never re-run LOOKUP** (`verify.py` docstring; `operations._first_difference`). So once D-062 drops the file hash, the verified canonical identity is the only Stage 02 guard.

### 3.2 Tamper-coverage matrix (fixture copies)

In every case the file SHA and the Stage 04 stat tuple changed, except T6, T6b (sibling file only) and T11 (stat tuple unchanged).

| Case | `compute_digests` vs meta | Recomputed vs original digest | `derivation_problems` | integrity_check | `event_problems` | Manifest check | Lookup output changed? |
|---|---|---|---|---|---|---|---|
| T1 event row modified | caught | caught | caught (event) | – | – | – | yes |
| T2 raw_record modified | caught | caught | caught (raw, event) | – | – | – | no (the field changed is not queried) |
| T3a ident modified | – | – | **only this** | – | – | – | **yes** |
| T3b title_token / T3c notice | – | – | only this | – | – | – | no |
| T4a artifact_digest forged in meta, content unchanged | caught | – (content equal) | – | – | – | caught | no |
| T4b semantic_digest forged in meta | caught | – | – | – | – | caught | no |
| T5 event modified, meta digests recomputed | – | caught | caught | – | caught (EVENT_TYPE_MISMATCH) | caught | yes |
| T12 consistent forgery from another CSV | – | **only this**, or `verify(source=)` | – | – | – | – (manifest regenerable) | yes |
| T6 manifest mismatch / T6b missing | – | – | – | – | – | **only this** | no |
| T7 secondary index b-trees swapped | – | – | – | **only this** | – | – | **yes (false negatives)** |
| T8 column affinity changed in DDL | – | – | – | **only this** | – | – | **yes** |
| T9 `sqlite_stat1` / T10 `run_built_at` | – | – | – | – | – | – | no (benign) |
| T11 in-place edit with mtime restored | – | – | – | – | – | – | file SHA and ctime only |
| File replaced during LOOKUP | – | – | – | – | – | – | caught by the existing inode/stat guard (`lookup.py:132`, `143`) |

### 3.3 Costs (full index, 3.12, seconds)

| Component | Seconds |
|---|---|
| `file_sha256` | 0.38 warm / 2.8 cold |
| `quick_check` | 0.21 |
| `integrity_check` | 0.68 |
| `foreign_key_check` | 1.60 |
| `compute_digests` | 5.02 |
| ident-only derivation | 5.29 |
| full `derivation_problems` | 12.26 |
| `event_problems` | 49.73 |
| full `verify` | 71.65 |

- **Option A**, full `verify` per process: about 72 s.
- **Option B**, the minimal set that covers everything LOOKUP reads (integrity_check + `compute_digests` + ident derivation + manifest): about 11 s. With full derivation instead of ident-only: about 18 s. `event_problems` adds nothing to identity: event content is fixed by `artifact_digest`, and derivation regenerates events from the raw records. This is inference, consistent with T5.
- **Option C**, cross-process memoisation keyed by the SHA-256 of the file bytes (about 0.4 s), with full verification only when the hash is new. This contradicts the D-062 sentence "validation results are not cached across processes", so it needs an explicit owner decision.

None of the options meets ≤ 5 s on the full index except C.

### 3.4 Smallest Stage 04 design (not implemented)

- **Scientific identity**, in `lookup.index_identity` (`lookup.py:56-62`):
  `{snapshot_id, policy_version, lookup_schema_version, artifact_digest, semantic_digest, export_lines}`.
  - `artifact_digest`, `semantic_digest` and `export_lines` are the recomputed values, required to equal meta.
  - `index_sha256` is dropped.
  - The same object is returned by `environment_identity` (`lookup.py:66-76`), which plan.py uses at `plan.py:98`.
- **Verification:** a new `verified_identity(index)` in `adapters/lookup.py`. It runs on the same `Index.conn` that serves the queries, so verification and lookups read the same open file. It applies the option chosen in 3.3, refuses on any problem (code `INDEX_CORRUPT` with detail) and never trusts meta strings alone.
- **Operational guard:** in LOOKUP, `before = stat5(path)` before the open and `after = stat5(path)` after the lookups, where stat5 = `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)`. A mismatch fails. The two full-file hashes may be removed, or one kept as belt-and-braces (0.4 s). Nothing from this guard enters any content or key.
- **Process-local cache:** an object created per `Integration` (a field with `default_factory`, passed to `make_lookup` and `environment`). Not module-global, so tests and invocations never share it.
  - Key: `(str(Path(path).resolve()), stat5)`. Value: the verified identity.
  - Re-stat on every use; any change invalidates the entry. Failures are not cached.
  - Gives one verification per process instead of 10 hashes.
- **Schemas and versions:**
  - `schemas/investigation/v1/common.schema.json:334-357` (`index_identity`).
  - `INTEGRATION_SCHEMAS["lookup-observation"]` and the Stage 04 `schema_version` (`plan.py:40-53`), so Step 8–11 journals become STALE `[stage04]`, never mis-read.
- **Documentation:** SPEC S-3.2 (line 123), the CP-1 row (line 1169), and the `plan.py:11-12` and `lookup.py:3-5` docstrings.
- **Tests referencing `index_sha256`:** `controller_support.py:66,348`, `step9_support.py:52`, `test_controller_resolution_stale.py:231,285`, `test_schemas_step5.py:342,1168`.
- **Equivalence and tamper tests:** the T-cases above, plus the two-build equivalence. The fixture builds already differ in bytes and agree in digests, so they suffice for CI.
- **Recommended additionally:** C-04 (`--index` override) and C-06 (path-free VALIDATE output).

## 4. Relocation experiment

Baseline: `run` in `reloc/A` gave exit 0, key `ef90ada3…`, C(J) `10e4fd05…`, report `7470058e…`, projection set `ca7c91e9…`. Replay and verify on the baseline were reproduced/passed, exit 0.

| Scenario | replay | verify | resume |
|---|---|---|---|
| R1 memory root moved | reproduced 0 | passed 0 | 0 |
| R2 bundle path removed | reproduced 0 | passed 0 | 0 |
| R3 index (and manifest) moved | **stale ["index"] 11** | **stale 11** | 0 (terminal; no stale check) |
| R4 whole tree moved | **stale ["index"] 11** | **stale 11** | 0 |
| R5 byte-different, canonically equal rebuild at the same path | **stale ["index"] 11** | **stale 11** | – |
| R6 index moved, symlink left at old path | reproduced 0 | passed 0 | – |
| R7 another bundle (ar-76190003) at the bundle path | stale ["root"] 11 | stale 11 | – |
| Fresh run at entirely different paths (`reloc/X`) | same key, C(J), report; replay reproduced 0 | – | – |
| `run` after moving the memory root / `..` spelling | – | – | `run` refused: INVESTIGATION_REQUEST_DIFFERS, exit 3 |

- **Paths inside digests:** paths are stored in journal seq 0 (`request`) and in the VALIDATE output blob. They therefore reach every step key and every step-succeeded output, and the journal and D-052 checkpoint digests (as do the `at` timestamps).
- **Paths outside digests:** they do not reach the investigation key, root, claims, evidence, report, projection set or C(J). This was verified by the identical C(J), report and claim ids across paths.
- **Retained artifacts:** the Stage 03 bundle is reconstructed from Memory into a private temp directory for replay and verify (`acquire.reconstruct`), so the bundle path never matters once retained, except in the R7 case.

## 5. Python 3.12 vs 3.13

- **Same-path runs** (`reloc/Q312`, `reloc/Q313`): 26 journal records each, all payloads identical, only the `at` field differs, identical blob sets (77 blobs).
- **Cross-interpreter:** 3.13 replay/verify of the journal written under 3.12 gave `reproduced` / `passed`, exit 0. No interpreter version is part of any identity.
- **Stage 02:** `artifact_digest` and `semantic_digest` are identical across 3.12/SQLite 3.45.1 and 3.13/SQLite 3.53.1 builds; the file bytes differ. Verify of the full 3.12-built index under 3.13 passes, 73.56 s.
- **Unicode:** 3.13 (Unicode 15.1) assigns 627 code points (U+2FFC to U+2EE5D) that are unassigned in 3.12 (Unicode 15.0). These affect `isalnum`, `category` and NFKC in `search.py`, `query.py:41`, `identifiers.py:74` and `wiki/reconcile.py`. 0 of the full index's raw records contain any of them. Theoretical only.
- **Code inspection:** canonical JSON is `sort_keys` with code-point order and `ensure_ascii=False`. Python's `json` is not locale-dependent. dt-1 reasons are sorted (`dt1.py:430`). There is no `locale`, `random` or `hash()` use in content paths; the times recorded (`at`, `now`) stay outside content.

## 6. Checked, no finding

- The investigation key, `root_id`, unit, candidate, evidence and claim ids, the report and C(J) contain no path or time (`ids.py`, `memory.py:83-109`, `fold.py:731-739`, `assemble.py` header). Verified across paths and interpreters.
- Existing LOOKUP guard: stat before the hash and open, stat and hash after. File replacement and in-place edits are caught today (`lookup.py:132-144`).
- `open_index` is read-only and immutable, checks `policy_version` and the shape of the meta digests, and requires the opened path to be the resolved one (`store.py:558-588`).
- Stage 02 lookup queries other than `crossref_sources` have deterministic order: `ORDER BY` in SQL, or sorted in Python.
- The Stage 02 build replacement rule compares `DIGEST_KEYS`, not bytes (`store.py:268-302`).
- Repeated runs give the same C(J): every run here had a fresh hash seed and gave the same C(J).
- `verify` of an untouched copy and of a canonically equal rebuild passes. Neither `run_*` meta nor `sqlite_stat1` affects lookup results.

NOT VERIFIED. This was a read-only review. The `pytest`, `ruff`, `mypy` and `citerift-gov check` suites were not run, and no change was made to verify.
