# Stage 04 Step 12: triage of the independent review findings

Owner authorization `cmsg_018VCB51nDHP6HXmLU4ea5yPTS6uNNfzMEoiA4s4Jo33LV` (2026-11-17), section 3. Reports retained
verbatim in `reviews/` (commit `9499c49`) before any correction. Baseline `65c30bd`.

Classes (owner section 3): **1** confirmed Stage 04 correctness defect; **2** Stage 04 reliability/security defect;
**3** Stage 04 performance defect; **4** documentation/specification inconsistency; **5** accepted deliberate
limitation; **6** upstream Stage 02/03 issue; **7** non-issue; **8** post-freeze/future-stage concern.

Severity is the reviewer's unless the lead's triage changes it (stated). "Fixed" means changed in Step 12 and covered
by a test named in section 3; the commit is the Step 12 corrections commit unless stated.

## 1. Findings and dispositions

### Reviewer A (scientific semantics)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| A-01 D-12 explanation asserts "A record exists"; "quarantined" for invalid identifiers | MEDIUM | 1 + 4 | **Fixed.** D-12 (`no_record` deciding lookup with a coverage gap) has its own template stating that no record matched and that rows that may concern the identifier could not be checked; `COVERAGE_GAP_RELEVANT_ROWS` and the `UNRESOLVED_STATUS` limitation say "quarantined rows or invalid identifiers"; SPEC 7.2 and MM F-3 wording aligned. Wording only: class, rule, evidence and ids unchanged. |
| A-02 DETECT/replay compare only claim ids | MEDIUM | 2 | **Fixed.** VERIFY `DETECT_REPLAY` (and so `replay`) requires the re-run claim payloads and DETECT evidence items to equal the committed ones in full. Step 9 A-6 sentence corrected in the freeze record. |
| A-03 D-6 taint reasons without the tainting occurrences in evidence | LOW | 1 | **Fixed.** The unit's occurrences join the supporting set whenever a claim carries a taint reason (D-4, D-6, D-8), so every reason has its chain (S-12.1). Changes the evidence set, and so the claim id, of tainted D-6 claims only; dt-1 rules, order and classes unchanged. |
| A-04 CO_REPORTED_MULTIPLE text says "more than one work" | LOW | 1 | **Fixed** (wording): "the citation reports more than one identifier of one scheme; each is checked separately". |
| A-05 counts of claims worded as citations | LOW | 1 | **Fixed** (wording): counts say "candidate identifier(s)"; `UNRESOLVED_USE` named in the out-of-scope parenthetical. |
| A-06 finding template overstates the identified work when κ is UNDETERMINED | LOW | 1 | **Fixed** (wording): neutral base template "the work the checked sources reach through this citation's identifiers". |
| A-07 D-7 drops taint reasons that D-6 keeps | INFO | 5 | Accepted limitation: SPEC 7.3, the frozen Step 4 model and production agree; the class routes to resolution and strengthens nothing. Listed in the freeze limitations; a change would need a new table version and an owner decision. |
| A-08 MM EV-2 literally false | LOW | 4 | **Fixed**: MM 4.6 EV-2 replaced by Reviewer A's wording (section 3 of `REVIEW_A.md`), approved by the scientific reviewer as written. |

### Reviewer B (architecture and reliability)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| B-01 keyed index identity and observed index never cross-checked | MEDIUM | 1 | **Fixed.** The controller passes the identity values it keyed the step with (`StepRequest.identities`); LOOKUP fails closed (`INDEX_CORRUPT`) unless its verified identity equals the keyed one. VERIFY `STAGE02_INDEX_IDENTITY` also compares the observed identity's digest with the LOOKUP manifest's `identities.index`. |
| B-02 transiently unavailable index makes an investigation permanently STALE | MEDIUM | 1 | **Fixed** to MM 10.2: a changed identity whose current value cannot be established (missing, unreadable or unverifiable index) is `IdentityUnavailable`; nothing is written and the command is refused with the engine's code (exit 3). Restoring the input lets the investigation continue. |
| B-03 Retry-After side channel in volatile `/tmp`, not fsynced | MEDIUM | 2 | **Fixed** with SD-01/SD-02: the side channel is kept in `.acquire/<key>/` inside the memory root (durable like the journal, validated before use), and the kept `network.jsonl`, its directory and the parent directory are fsynced. Not done: a retry whose earlier attempt directory was deleted by someone is not detected (an attempt can also be counted without ever reaching the adapter, so refusing would turn a crash into a terminal failure); stated as a residual limitation. |
| B-04 unreadable Retry-After recorded as retryable, then ADAPTER_INCONSISTENT | LOW | 1 | **Fixed**: the normal-exit path passes the side channel's `known` flag, so the attempt is recorded as not retryable with `RETRY_AFTER_UNREADABLE` detail under the existing terminal code; no early request either way. |
| B-05 `run` on an existing investigation repairs a torn tail before the W-check | MEDIUM | 1 | **Fixed**: `run` on an existing investigation compares the request read-only and drives it through `open_controller` (D-044 order); `create` is used only for a new investigation. |
| B-06 damaged layout reported as not found | LOW | 2 | **Fixed** with SD-04: `PathUnsafe` after the investigation directory exists is `corrupt` (12); `not_found` only when the key directory is absent. |
| B-07 commands classify a forged step key differently | LOW | 1 | **Fixed**: one staleness rule (`controller.staleness`) with the checked step manifests (`controller.checked_manifest`) for `resume`, `show`, `verify` and `replay`; an invalid manifest or key is CORRUPT (12) everywhere. |
| B-08 report may list one committed claim twice | LOW | 1 | **Fixed**: the D-054 check refuses a duplicate `claim_id` and requires as many entries as committed claims. |
| B-09 `referenced_blobs()` ignores report chunks | LOW | 1 | **Fixed**: report-manifest chunks are referenced. |
| B-10 pid reuse on the normal-exit path of the supervisor | LOW (inference) | 2 | **Fixed** with SD-03: the supervisor observes the exit without reaping (a pidfd poll, else `waitid(WEXITED \| WNOHANG \| WNOWAIT)`), so the child's pid cannot be reused while it collects and kills the tree and the session; then it reaps. |
| B-11 SPEC S-10.2 vs post-commit bundle change | LOW | 4 | **Fixed** (SPEC/MM wording): S-10.2 applies at ACQUIRE; after the root is bound a different capture at the path is STALE. |
| B-12 repeated folds and double validation | LOW | 3 | Measured in the performance section; fixed only where measurement shows it material (owner section 13). |
| B-13 aggregate LOOKUP memory bound | LOW (inference) | 8 | Stated as a limitation (queries × per-query bound). |

### Reviewer C (integration and reproducibility)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| C-01 scientific identity bound to the SQLite file SHA-256 | HIGH | 1 | **Fixed: D-062** (section 2). |
| C-02 Stage 02 verify per process vs ≤ 5 s | HIGH | 3 → owner decision | **Resolved by the owner**: OD-S12-1 (D-064) chose the D-062 identity-verification profile `verify_index_identity`; the differential tamper proof found no discrepancy; see section 2.3. Not a correctness defect: no unverified identity is accepted. The ≤ 5 s target stays NOT_MET (D-061), reported as a frozen limitation. |
| C-03 `artifact_digest` alone does not prove what LOOKUP reads | HIGH (design requirement) | 4 | **Met by design**: the verification always runs `integrity_check`, structure, digests recomputed vs meta, the full derivation recompute and the manifest check; the tamper suite includes the reviewer's T3a, T7 and T8. |
| C-04 byte-identical index at another path is STALE; no override | MEDIUM | 1 | **Fixed**: identity no longer depends on the file; `resume`, `replay`, `verify`, `show` and `export` accept `--index` (and `--bundle`) as operational locators for the process. |
| C-05 mutation guard omits `ctime_ns` | LOW | 2 | **Fixed**: guard and reuse key use (dev, ino, size, mtime_ns, ctime_ns). |
| C-06 absolute paths reach step keys via the VALIDATE output | LOW | 5 → fixed | **Fixed**: the VALIDATE output names the logical request without paths. |
| C-07 `run` idempotency depends on path spelling | LOW | 5 | Accepted limitation (documented at Step 10); `run` compares the creation payload. Use `resume --key` for an existing investigation. |
| C-08 a different bundle at the recorded path makes it STALE | LOW | 5 | Accepted: consistent with S-4.4; with `--bundle` the operator can point elsewhere. |
| C-09 symlinked index FAILED at `run` but accepted by replay | LOW | 4 | **Fixed**: VALIDATE accepts a symlink to a regular file, as Stage 02 opens it. |
| C-10 verified identity does not prove CSV provenance | INFO | 8 | Limitation: the canonical digest of the accepted snapshot is pinned in the Stage 02 handoff and in the freeze manifest; a different `artifact_digest` is STALE. |
| C-11 build manifest is a mutable sibling | INFO | 4 | **Decided**: a missing or mismatched manifest refuses (D-062 "manifest checks"); relocation moves `*.manifest.json` with the index. |
| C-12 `crossref_sources` has no ORDER BY | LOW | 6 | Upstream Stage 02 item, returned through the maintenance mechanism; no effect on the accepted RW-only index (0 rows). Not changed here. |
| C-13 Stage 02 SPEC 10.4 export list incomplete | INFO | 6 | Upstream documentation item; not changed here. |
| C-14 index hashed for every step | MEDIUM | 3 | **Fixed** by D-062's process-local reuse. |

### Reviewer D (security and boundaries)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| SD-01 predictable `/tmp` live work root, unchecked | MEDIUM | 2 | **Fixed** (with B-03): the default work root is `.acquire` in the memory root (no longer in the shared temporary directory); it and the per-investigation directory are refused unless each is a real directory (not a symlink) owned by the user with no group or other access; a refusal is `ADAPTER_INCONSISTENT` before any child starts. |
| SD-02 side channel shared across memory roots and instances | LOW | 2 | **Fixed**: the side channel is scoped by the memory root and the investigation key (`<memory root>/.acquire/<key>/`); one key names one creation payload in a memory root (`run` refuses another payload, B-05), so it is per investigation instance. Two memory roots no longer share it. |
| SD-03 setsid descendant escapes on normal exit | LOW | 4 | **Fixed** with B-10 (scan before reap); the documented F-11 limit is restated. |
| SD-04 unsafe directories reported as not found | LOW | 1 | **Fixed** with B-06. |
| SD-05 S-15.1 static test not recursive | LOW | 4 | **Fixed**: `rglob` over the package and `from citerift import governance` flagged. |
| SD-06 hard links to `lock` / `journal.jsonl` | INFO | 8 | **Fixed** (cheap hardening): `st_nlink != 1` is refused as unsafe. |
| SD-07 export rename race with an empty directory | INFO | 8 | Documented: the docstring states the check-then-rename window; same as UF-11. |
| SD-08 journals record absolute host paths | INFO | 8 | Known A11-6; wording corrected; retained evidence is checked for local paths before commit. |
| SD-09 C1/bidi controls in text output | INFO | 7 | Non-issue today (no untrusted free text reaches output); text mode escapes non-printable characters anyway. |
| SD-10 user-named files opened with plain `open()` | INFO | 7 | Non-issue (self-supplied); unchanged. |

### Reviewer E (evaluation, leakage and statistical readiness)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| E-01 no committed canonical exposure list | MEDIUM | 4 | **Fixed**: committed, hashed article-level exposure manifest (`freeze/exposure/`), built by E's rule from every tracked file at the freeze (all 257 tracked Stage 03 capture bundles, 232 distinct articles; 298 articles in all, 9 known only by title). The plan's figure of 255 bundles has no retained derivation; the Step 9 A-8 statement is corrected in the freeze report. |
| E-02 Stage 03 exposure set undefined / committed file outdated | MEDIUM | 8 | The manifest recomputes the Stage 03 rule at the freeze commit (separate `listed` block, digest recorded); adoption of the wiki-agnostic tier is a Step 13 pre-registration choice. |
| E-03 exposed articles without bundle / without page id | LOW | 5 | Included in the manifest (`S03-ATTEMPTED`, title-keyed records). |
| E-04 documents name different exclusion sets | LOW | 4 | The manifest is the union; the freeze report states the one rule. |
| E-05 identity-conflict denominator: hard minimum vs descriptive | MEDIUM | 4 → owner | **Owner decision for Step 13** (pre-registration); not an engine change. |
| E-06 precision covers 2 of 4 positive classes | MEDIUM | 4 → owner | **Owner decision for Step 13** (pre-registration). |
| E-07 recall and negative denominator undefined | LOW | 4 | Step 13 pre-registration item. |
| E-08 sensitivity variants and baseline scorer not implemented | MEDIUM | 8 → owner | **Owner decision**: whether they belong to the frozen code or to the pre-registration (owner section 23 allows only pre-registration after the freeze). |
| E-09 freeze content undefined | LOW | 4 | **Fixed** by the freeze manifest. |
| E-10 English frame source not in the repository | MEDIUM | 8 | Step 13 prerequisite; recorded in the freeze limitations. |
| E-11 docstring understates Stage 03 evaluation reuse | LOW | 4 | **Fixed** (wording). |
| E-12 "F-15" means two things | INFO | 4 | Qualified in the freeze report. |
| E-13 04-C "development set" undefined | LOW | 4 | Defined in the freeze report: the Step 4 enumerated domain (244,884 valid cases) is the differential; the 232 revisions are development measurements. |
| E-14 frame thinning after exclusion | INFO | 8 | Step 13 item. |

### Reviewer F (CLI, report and user semantics)

| Id | Severity | Class | Disposition |
|---|---|---|---|
| UF-01 false `V1_DATE_NOT_UNIFORM` for every non-retraction record | MEDIUM | 1 | **Fixed**: when every contributing claim states the same date it is carried; when none states one the date is omitted with no lossy code (a work that is not retracted has none); when they state different dates, or only some state one, it is omitted with `V1_DATE_NOT_UNIFORM`. Changes the projection bodies of works with no date. |
| UF-02 A11-5: RUNNING-and-wait gives exit 14 | MEDIUM | 1 | **Fixed (A11-5, reviewer's option b)**: the user-facing status is `blocked` (exit 8) whenever no step may start before `not_before`, for lifecycle BLOCKED and for RUNNING after a retryable failure with a `not_before`; JSON keeps `lifecycle` and `next`. Lifecycle and journal unchanged. |
| UF-03 `show` predicts the wrong next transition after an input change | MEDIUM | 1 | **Fixed**: `show` applies the staleness rule read-only and reports `next: stale` (T-STALE) with the changed identities. |
| UF-04 "failed" for not-yet-verified | LOW | 4 | **Fixed**: result `not_verified`, export detail names the lifecycle. Exit codes unchanged. |
| UF-05 JSON shape exceptions | LOW | 4 | **Fixed**: usage and internal errors emit the JSON error envelope when `--format json` is given; `checkpoint` to stdout and `verify` busy/corrupt documented as the two exceptions. |
| UF-06 text output omits diagnostics | LOW | 1 | **Fixed**: `changed`, `code`, `detail` printed. |
| UF-07 two timestamp formats | LOW | 4 | **Fixed**: one format (`…Z`). |
| UF-08 article-level statements copied into every v1 record | LOW | 4 | **Fixed**: lossy code `V1_ARTICLE_LEVEL_STATEMENTS`. |
| UF-09 v1 events drop `matched_by`/`linked_via` | LOW | 4 | **Fixed**: lossy code `V1_EVENT_LINKS_NOT_STATED`. |
| UF-10 exit codes not in `--help`; I-5 undocumented | LOW | 4 | **Fixed**: the exit-code table is the parser epilog; the I-5 sentence added; row 11 qualified. |
| UF-11 export rename race; ENOSPC → exit 3 | LOW | 2 | Documented (as SD-07); unchanged. |
| UF-12 I-2 `workflow.outcome()` ignores extraction partial | LOW | 1 | **Fixed (I-2)**: one pure helper `report.outcome()` (S-9.7) used by ASSEMBLE; the fold-only `workflow.outcome` removed; `status_of` fails closed for COMPLETED without an outcome. |
| UF-13 cosmetic text | INFO | 4 | **Fixed**. |

### Findings of the Step 12 lead during the corrections

| Id | Severity | Class | Disposition |
|---|---|---|---|
| L-01 D-062 reuse could store a verified identity under a replaced file's fingerprint | HIGH (found by the new D-062 test before any commit) | 1 | **Fixed**: the reuse key is the fingerprint taken before the index was opened, and the entry is stored only if the path still has that fingerprint after the verification; otherwise `INDEX_CORRUPT`. Test `test_a_file_replaced_during_the_lookup_fails_closed`. |
| L-02 a reused identity carried the policy and lookup-schema versions of the code that verified it | MEDIUM (found by the suite) | 1 | **Fixed**: those two values are not properties of the file and are taken from the running code on every use (`_current_versions`); a changed lookup policy is again STALE (`test_a_changed_lookup_policy_is_stale`). |
| L-03 triage claims checked against the code before freeze | n/a | 4 | Four dispositions drafted before the code was final were corrected (B-03, SD-01, SD-02, UF-01) and tests were added for every "Fixed" row that had none (A-01, A-02, A-03, B-01, B-04, C-09, SD-01, UF-06). |
| L-04 every command verified the index (about 25 s) even when no step it ran or checked depends on the index | MEDIUM (found by the VS-8c check of the freeze vertical-slice run before any freeze commit: a resume before `not_before` took 24.9 s, Step 11 0.49 s) | 1 | **Fixed**: the index identity is established only when read (`workflow.LazyIdentities`, `IdentityDigests`): by a step key or staleness check of LOOKUP or a later step (`STEP_IDENTITIES`), or by LOOKUP itself; a step request carries only the identities its key depends on. Step keys, digests and the D-062 checks are unchanged. Test `test_step8_live.py::test_l04_a_run_that_waits_before_lookup_does_not_verify_the_index` (fails without the change: 1 verification on the first run). |

## 2. D-062

See `../../freeze/FREEZE_REPORT.md` section "D-062" for the design, the equivalent-rebuild proof and the tamper
results.

### 2.3 Verification scope (C-02)

Measured on the accepted full index (278,769,664 bytes): Stage 02 `verify` 72–83 s per process, of which the
JSON-Schema re-check of every stored event (`event_problems`) is about 50 s; the checks that cover everything LOOKUP
reads (integrity and structure, digests recomputed, full derivation recompute, build manifest) about 18 s. The
choice was put to the owner, who chose the second as the D-062 identity-verification profile (OD-S12-1, recorded as
D-064): `adapters/lookup.verify_index_identity`, which also checks the Stage 02 format and policy. Stage 02's complete
`verify` stays the certification and is unchanged.

Differential tamper proof required by OD-S12-1 (`../../freeze/d062/tamper_differential.py` and `.json`): 21 cases on a
real Stage 02 index with its manifest, each checked by complete `verify` and by the profile. Both accept the untampered
control, a genuinely different consistent artifact (another canonical identity, so STALE) and a byte flip that lands in
unallocated page space (recorded from `dbstat`; identity unchanged). Both reject the other 18. No case is rejected by
complete `verify` alone: every schema-invalid event also breaks the derivation equality (the event table must equal the
events derived from the raw records), so the per-event JSON-Schema re-check found no tampering the profile missed. The
operational cases (inode replacement, size-preserving change after reuse, change after reuse, replacement during
LOOKUP, failures not reused) run as the named `test_step12_d062.py` tests and pass.

Component profile required by OD-S12-1 (`../../freeze/performance/verification_components.py` and `.json`; accepted
full index, 278,769,664 bytes, 73,356 records; warm single process, 5 repeats, medians). The "about 18 s" above was
the first estimate; the measured profile is **25.3 s**, the same as the `index_verify` median of the post-D-062
`perf_breakdown` (25.4 s):

| Component | Median |
|---|---|
| `derivation_problems` (re-derive every record and derived table, compare) | 15.4 s |
| `compute_digests` (canonical export lines, SHA-256, semantic digest) | 6.2 s |
| `structural_problems` (of which `PRAGMA foreign_key_check` 2.6 s, `integrity_check` 0.9 s) | 3.5 s |
| format, policy, manifest | < 0.01 s |

Read passes over the file: `raw_record` is read three times (digest record lines, the digest event join, the
derivation) and the file once more by `integrity_check`. Measured bare scans: one full file read with SHA-256 0.24 s;
`raw_record` scan 0.13 s; the event join 0.38 s; `ident` 0.41 s; `event` 0.22 s; `title_token` 0.30 s. The repeated
reads therefore cost well under 1 s in total: the profile is CPU-bound in Python, not I/O-bound. `cProfile` attributes
the time to work each check needs on its own: re-deriving records (`ingest.dispose`, identifier and date
normalization), building the derived tables (`derive_tables`, title tokenization), and canonical JSON encoding (1.32
million `canonical` calls: the export lines that are hashed and the derived rows that are compared). The overlap that a
single shared pass could remove is the duplicate scans and the repeated `json.loads` of each record's stored fields
(about 1–1.5 s together, an upper bound from the scans and the profile); hashing the export and re-deriving the tables
are different computations and would both remain, so a shared pass would still leave about 23–24 s, far above 5 s. It
would also require changing accepted Stage 02 functions (`compute_digests`, `derivation_problems`; a Stage 02
maintenance needing an owner decision) or re-implementing them in Stage 04, which would stop the profile being Stage
02's own checks. No such change is made; no check is removed. `foreign_key_check` (2.6 s) is a SQLite algorithmic
cost of the accepted Stage 02 schema and is also left unchanged. The ≤ 5 s p95 target stays NOT_MET (D-061), with this
profile as the measured cause.

## 3. Tests

Each "Fixed" row is covered by a test in `tests/stage04/` (all run in CI):

| Findings | Tests |
|---|---|
| A-01, A-03, A-04 | `test_step12_semantics.py` (A-03 fails without the change: a malformed occurrence of a tainted D-6 unit) |
| A-02 | `test_step12_fixes.py::test_a02_*` (claim and evidence variants) |
| B-01, C-01, C-03, C-05, C-14, L-01 (D-062) | `test_step12_d062.py` |
| B-02, MM 10.2 | `test_step12_fixes.py::test_mm10_2_*`, `test_step12_d062.py::test_a_tampered_index_is_refused_not_stale`, `test_step12_fixes.py::test_a11_6_moved_inputs_are_named_with_locators` |
| B-04 | `test_step8_live.py::test_b04_*` (fails without the change) |
| B-05, B-06/SD-04, B-08, B-09, SD-06 | `test_step12_fixes.py::test_b05_*`, `test_b06_*`, `test_b08_*` (fails without the change), `test_b09_*`, `test_sd06_*` |
| B-07 | `test_controller_adversarial.py`, `test_step10_corruption.py` (one staleness rule; forged manifests are CORRUPT) |
| B-10/SD-03 | `test_step8_live.py` supervisor tests (normal-exit tree kill) |
| C-04, C-06, A11-6 | `test_step12_fixes.py::test_a11_6_*`, `test_c06_*` |
| C-09 | `test_step12_fixes.py::test_c09_*` |
| I-2 (UF-12) | `test_step12_fixes.py::test_i2_*` |
| A11-5 (UF-02), UF-07 | `test_step12_fixes.py::test_a11_5_*` |
| L-02 | `test_step8_resume_stale.py::test_a_changed_lookup_policy_is_stale` |
| SD-01 | `test_step8_live.py::test_sd01_*` |
| SD-05 | `test_memory_storage.py` (recursive S-15.1 scan) |
| UF-01, UF-08, UF-09 | `test_step12_fixes.py::test_uf01_*`, `test_uf08_uf09_*` |
| UF-03 | `test_step12_fixes.py::test_uf03_*` |
| UF-04 | `test_step10_cli.py` (`not_verified`) |
| UF-05, UF-06, UF-10 | `test_step12_fixes.py::test_uf05_*`, `test_uf06_*`, `test_uf10_*` |
