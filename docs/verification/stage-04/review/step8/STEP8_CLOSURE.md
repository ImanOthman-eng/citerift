# Stage 04 Step 8: real Stage 02/03 integration adapters (closure record)

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yP3N7KPNwX5cW1HPdZKPNpQP` (2026-11-12T09:37:22Z), baseline
`b43fa036a97a00ef935c94cb9768bd8e2793403d` (D-055, accepted). Step 7, D-047 to D-055 and A-02-001 are not reopened.
Step 9 is not started: there is no decision table, no κ, no dt-1 change, no CLI, no report delivery, no holdout and no
evaluation in this step.

**Status (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3QUKzTGVBuK7bcRu4jArpU`, 2026-11-12T14:58:09Z): Step 8 accepted
technically at `7e16bdefa6191de23948b54616636ba08f10c9c4`; OD-S8-1 approved as D-056 and the lookup-budget identity
rule approved as D-057 (section 19). With both recorded, Step 8 is accepted and closed. Step 9 is not authorized.**

Labels: **[verified]** measured or tested here, with the file named; **[inference]** derived, not measured;
**[limit]** a stated limitation; **[owner]** needs an owner decision.

Real inputs only where real inputs are claimed: the previously exposed design bundles of SPEC S-7.4 (VS-1
`docs/verification/stage-03/demonstrations/bundles/en-1381772671`, VS-2 `tests/stage03/fixtures/observed/ar-76190003`,
VS-3 `tests/stage03/fixtures/observed/en-1372543632`; no Stage 03 evaluation or holdout bundle) and the attributed
Retraction Watch subset (section 9). DETECT in every integration test is the **SYNTHETIC test detector** of
`tests/stage04/step8_support.py` (identity `SYNTHETIC-test-detector/1 (not dt-1)`): it lets DETECT, ASSEMBLE and
VERIFY run end to end before Step 9 and decides nothing scientific.

## 1. Build-vs-Adopt (item 1)

`STEP8_BUILD_VS_ADOPT.md`. Candidates: psutil (REFERENCE ONLY), Pebble (REJECT, LGPL licence gate), sarge (REJECT),
plumbum (REJECT), and others recorded there. **Decision: no dependency.** The stdlib/POSIX baseline is the
implementation (`subprocess` with `start_new_session`, `os.killpg`, `Popen.wait` on the child only, a `/proc` read of
the session and of the descendants, `prctl(PR_SET_PDEATHSIG)` through `ctypes` in the child). No cloud worker.
`pyproject.toml` and `uv.lock` are unchanged since the baseline [verified, `git diff b43fa03 -- pyproject.toml uv.lock`
is empty].

## 2. IF-7: the ACQUIRE observation (item 2) — RESOLVED

**Architecture** (`src/citerift/investigation/retained.py`, `adapters/acquire.py`, schemas
`bundle-observation` 1.0.0 and `bundle-artifact-set` 1.0.0):

- The committed ACQUIRE observation (`obs_kind = bundle`) names a small, **closed** canonical manifest. The manifest
  has no list: engine, capture `{blob, bytes, schema_version}`, status, identity, display, source
  `{artifact, bytes, response_artifact}`, render `{state, artifact}`, `failure_artifact_count`, and artifact set
  `{blob, count, bytes}`.
- The **exact `capture.json` bytes** are a raw blob whose digest is the Stage 03 `capture_sha256`, so the root's
  capture identity (F-15) is the blob's name.
- A canonical **artifact-set** blob lists every artifact `capture.json` lists (`sha256`, `bytes`, roles), each
  retained as a raw blob.
- Memory checks the manifest, the set and every raw blob on append and on open (M-3; a missing or corrupt raw blob is
  `CORRUPT`) [verified, `test_a_deleted_raw_blob_is_corruption`].

**What is retained, what is digest-only, and why that suffices.**

- Retained as bytes: `capture.json` and every listed artifact (source text, the Action API response, the render
  HTML when there is one, every kept failure body). Stage 03 `verify_capture`, which VERIFY runs (SPEC 9.7), reads
  and hashes every listed artifact and refuses an unlisted one, so a byte-exact reconstruction needs exactly this set,
  no more and no less. The set Stage 04 derives (`retained.listed_artifacts`) is pinned to Stage 03's private
  `wiki.verify._listed_artifacts` and to the bundle's `artifacts/` directory on all three bundles [verified,
  `test_retained_artifacts_are_exactly_what_stage03_verification_reads`].
- Digest-only: nothing of the bundle. The manifest and the set name blobs by digest, but every named blob is in
  Memory. The capture's own attempt and issue lists are not copied into Stage 04 records; they stay inside the retained
  `capture.json` bytes.

**Proven bound** [verified, `if7_bound.py` → `if7_bound.json`; the largest instances the schemas allow, checked
against the schemas]:

| Object | Worst case | Limit |
|---|---|---|
| Manifest blob | 5,076 B (every string at its maximum in 4-byte UTF-8, every integer at its maximum) | 256 MiB blob |
| Artifact-set blob | 9,896,497 B at 65,539 entries (3.7 % of the limit) | 256 MiB blob |
| `observation_recorded` payload | 176 B (digest only; nothing grows with the bundle) | 1 MiB record |
| One raw artifact | 33,554,432 B (`MAX_ARTIFACT_BYTES`, Stage 03 read limit) | 256 MiB blob |

The 65,539 count: `capture.json` is at most 4 MiB and each listed failure digest takes at least 67 bytes, so at most
62,601 failure artifacts (under the schema's 65,536), plus source, response and render. The schema-only raw total
(2.2 TB) is theoretical; under Stage 03's own limits one capture retains at most **75,890,688 B** (capture 4 MiB,
source 4 MiB, response 32 MiB, render 32 MiB, six failure bodies of 64 KiB under the default policy) [verified,
`if7_bound.json`, `stage03_practical_*`]. The journal bound of D-055 is unaffected: the ACQUIRE record is a digest.

**Bundle removal** [verified, `test_removing_the_bundle_after_acquire_changes_nothing`]: the ar bundle is deleted
after ACQUIRE commits and before EXTRACT; the run ends `NEEDS_RESOLUTION` with the same claim ids and the same
candidate inputs as the run with the bundle in place, no `stale_detected` record, and a reopen without the bundle is
unchanged. EXTRACT and VERIFY rebuild the bundle from Memory (`retained.reconstruct`).

## 3. Retained ACQUIRE (item 3)

`retained_acquire` opens the bundle with Stage 03 `open_bundle`, runs `verify_bundle`, checks the capture against the
request key and the root rules (S-4.6, F-15), and returns the raw blobs, the set, the manifest, one content record
and the root. It writes nothing [verified, `test_adapter_returns_never_write_memory`: the memory root is unchanged]
and uses no network [verified, every integration module runs under `NoNetwork`, which refuses `connect`,
`connect_ex`, `create_connection` and `getaddrinfo` in-process and counts attempts: 0].

## 4. Live ACQUIRE under D-042 (item 4)

**Architecture** (`adapters/supervise.py`, `adapters/live_child.py`, `adapters/live.py`):

- One child process per attempt, `python -I -m citerift.investigation.adapters.live_child WORKDIR PARENT_PID`, in its
  own session; the parent takes the time immediately before `Popen`, so `T_acq` covers interpreter start-up, DNS,
  connection, transfer, Stage 03's own retries and bundle publication. Output goes to files, never pipes.
- `T_acq = deadline_s + op_timeout_s + 30 s` = **240 s** with the Stage 03 defaults (`bound_for(policy)`); the adapter
  refuses a request whose `fetch_policy_sha256` or `live_acquire_bound` is not this policy's before any child starts
  [verified, `test_wrong_policy_or_bound_is_refused_before_any_child`].
- At the deadline: `killpg(SIGSTOP)`; `/proc` read of every process of the session and every descendant by parent
  links; `SIGKILL` to each and `killpg(SIGKILL)` **before** the leader is reaped; the leader reaped with `wait()` only
  (never `waitpid(-1)`); a bounded sweep (5 s) until every killed process is gone. A survivor is a supervision
  failure (`ADAPTER_INCONSISTENT`), never a capture.
- The child sets `PR_SET_PDEATHSIG(SIGKILL)` and re-checks its parent, so it never outlives a dead controller
  [verified, `test_controller_death_during_the_live_child`].
- Stage 03 is unchanged: the child runs `capture_revision` with Stage 03's own transport, NetworkGate, throttling and
  retries (section 13, finding B-1).
- Past the bound: `step_failed(ACQUIRE_WALL_CLOCK_EXCEEDED)` with `wall_clock = {t_acq_ms, elapsed_ms}`, no root, no
  blob, no record; nothing the child wrote is read except the Retry-After side channel [verified,
  `test_a_killed_attempt_returns_nothing_authoritative`, `test_an_unknown_retry_after_at_the_kill_is_terminal`: root
  null, no logical record].

**Kill and reap, measured separately** [verified, `test_step8_live.py` supervisor tests; numbers from
`step8_perf.py` → `step8_perf.json`, section 15]. The tree test kills a child, a descendant in its session and a
descendant that left the session with `setsid`; all three are dead and the session is empty afterwards.

**What 240 s is not.** It bounds one attempt's child process. `9 × T_acq` (2,160 s) bounds live-ACQUIRE child time per
investigation; neither is the investigation's wall-clock bound, which also needs termination overhead and the other
steps' bounded work (SPEC 9.2).

**[limit]** A descendant that double-forks and calls `setsid` after its intermediate parent exited has neither the
session nor a parent link; only cgroups could attribute it. The child runs only Stage 03 capture code, which starts
no process. `/proc` and `PR_SET_PDEATHSIG` are Linux facilities; without them the child refuses to run.

**OD-S8-1, graceful stop — resolved by owner decision D-056.** SPEC 9.2 said the child "is asked to stop gracefully
within `T_acq` and is then killed and reaped". The implementation sends no SIGTERM: at `T_acq` it freezes and kills
the tree. Reasons: nothing
the child produces after the deadline may count (G-4); the only state that must survive a kill, the Retry-After
side channel, is fsynced as each response's headers arrive, so a graceful flush has nothing to save; a grace period
inside `T_acq` would shorten the capture budget, and one after it would extend the bound. The owner's Step 8 item 4
("kill the whole tree, reap, and measure kill/reap separately") is met. D-056 approved this and SPEC 9.2 now reads:
"At `T_acq` the parent immediately freezes (stops) the attributable child process tree, kills it and reaps the direct
child. No graceful-stop interval is used, neither inside `T_acq` (which would shorten the capture execution budget)
nor after it (which would extend it) (owner decision D-056). Kill, reap and cleanup latency are measured or bounded
separately and are not part of the child execution budget." The formula and the implementation are unchanged.

## 5. Retry-After proof and F-11 (item 5)

- **Durability before the kill.** `live_child` wraps the module-level Stage 03 transport: a `request` line before each
  request and, as soon as the headers are in and before Stage 03 reads the body, a `response` line with the status,
  the raw `Retry-After` and the wall-clock instant, appended and fsynced to `network.jsonl`.
- **Parse.** Stage 03's own `parse_retry_after` (delta-seconds and HTTP-date). A value it refuses, a value beyond its
  range, a request with no response line (killed in flight) and a torn last line are all **unknown**.
- **Decision.** Known → retryable with `not_before` = the **latest** instant any response named (never shortened);
  unknown → terminal (or a deferral to a known earlier instant, below).
- **Earlier attempts.** The side channel stays in a per-investigation directory until a capture succeeds. A new
  attempt first reads every earlier attempt's side channel: a future Retry-After → `Deferred` without starting a
  child; an unknown one → `ADAPTER_INCONSISTENT`, terminal.

| Case (item 5) | Result | Test |
|---|---|---|
| Retry-After in seconds, killed after the headers persisted | known; `not_before` = arrival + 600 s | `test_a_retry_after_seen_before_the_kill_is_the_retry_instant[seconds]` |
| Retry-After as an HTTP-date | known; `not_before` = the date exactly | `…[date]` |
| Invalid ("soon"), huge number, date beyond range (2120) | unknown, terminal | `test_an_unreadable_or_out_of_range_retry_after_is_unknown` ×3 |
| Kill immediately before persistence (request in flight) | unknown, `FAILED` terminal, no root | `test_an_unknown_retry_after_at_the_kill_is_terminal`, `test_a_killed_attempt_returns_nothing_authoritative` |
| Kill during persistence (torn line) | unknown | `test_side_channel_never_shortens_and_treats_a_torn_line_as_unknown` |
| Two responses (300 s, then 60 s) | the later instant wins | same test |
| Resume 1 ms before / at / 1 h after `not_before` | `wait` / `start` / `start`; a run 1 s early starts nothing; a run at the instant completes with 2 attempts | `test_retry_after_resume_waits_before_the_instant_and_starts_at_it` |
| Controller killed with the child, headers persisted | child dies (PDEATHSIG); resume: attempt interrupted, next attempt **defers** to the dead child's instant, `BLOCKED`, no request sent | `test_controller_death_during_the_live_child[retry_after:600]` |
| Controller killed with the child, request in flight | child dies; next attempt fails terminally, no request sent | `test_controller_death_during_the_live_child[in_flight]` |

Stage 04 never shortens an observed Retry-After: the only instants it uses are the ones the server sent, maximised.

**F-11 status: IMPLEMENTATION_VERIFIED** (recorded by owner decision D-056) for the bound, the kill and reap, their
measurement, the non-authoritative timeout and the Retry-After retryability, on the synthetic-network child
(`tests/stage04/live_fake_child.py`, which runs the production `live_child.main` with only the transport replaced).
Explicit platform and process-model limitation: an adversarial descendant that escapes both the process session and
the parent relationship (a double fork with `setsid` after its parent exited) is outside the attribution model;
production Stage 03 capture starts no subprocess; `/proc` and `PR_SET_PDEATHSIG` are Linux facilities. No real
network request was made by any test.

## 6. EXTRACT and D-050 (item 6)

EXTRACT rebuilds the bundle from Memory in a private temporary directory and runs Stage 03
`extract_bundle(path, config, isolated=True)`. A `complete` or `partial` document is committed exactly as Stage 03
returned it after schema, self-digest, extractor/configuration and root-identity checks. A `failed` document is
mapped by D-050 (`extraction.extraction_failure`) [verified, `test_extraction_failure_maps_by_d050`: a real Stage 03
reference-limit failure on VS-2 is `EXTRACTION_FAILED` with the Stage 03 code as the reason; nothing downstream runs;
no claim].

## 7. D-043 on real bytes (item 7)

`unit_span_sha256 = SHA256(source_bytes[byte_start:byte_end])`, computed by `anchors.unit_span_sha256` after, in
order: the source digest, the extraction/root capture binding, the byte bounds, the UTF-8 code-point boundaries and
identifier-anchor parity. [verified, `test_d043_unit_anchors_on_real_arabic_and_english_bytes[ar|en]`: every unit of
VS-2 and VS-3 — the source digest is checked first, the committed hash equals both the production function and an
independent `hashlib.sha256` of the slice, every span decodes as UTF-8, and Arabic spans contain non-ASCII bytes.]
A mismatch fails closed [verified, `test_verify_fails_on_an_unanchored_unit` (shifted span → `D043_UNIT_ANCHORS`);
the Step 6 anchor tests now run over the IF-7 retained source].

## 8. NORMALIZE (item 8)

Production transform of SPEC 6.1–6.6 / MM 4.1–4.4 into `candidate-inputs` 1.0.0: units, identifier occurrences with
status, roles and eligibility, anchors with D-043 hashes, work candidates, observation keys and the lookups to make,
with D-051 evidence ids `H(observation, pointer, kind)` and provenance refs (bundle identity → extraction identity →
unit → identifier). Keys are exactly Stage 03's `normalization.normalized`; nothing is re-parsed, re-normalized,
merged or inferred. No coherence, class, rule or disposition (Step 9). VERIFY replays it (`NORMALIZE_REPLAY`).

## 9. Fixture: attributed Retraction Watch subset (item 10)

`docs/verification/stage-04/scripts/step8_rw_subset.py` → `tests/stage04/fixtures/step8/rw_subset.csv` (6 real
records, 1,708 B, SHA-256 `1b7aa376…f18`) and `rw_subset.json` (attribution, source receipt, query states, outcome
digest). The script checks the pinned Retraction Watch CSV against receipt `rw-a987928`, extracts every key of the
four design bundles, runs all 2,405 queries (Q1 per key and every DOI×PMID pair) through `bounded_gather` (16 MiB) on
the **full** index, keeps every record any query touches (record ids 2081, 2086, 4036, 17269, 66335, 66337), builds
a subset index and checks that every query's outcome is identical on the subset and on the full index
(`subset_equals_full_index: true`, 0 disagreements; states: 144 ambiguous_identity, 12 matched, 2,054 no_record,
195 notice_only). No synthetic row. It is a test fixture, not evaluation data.

## 10. LOOKUP, bounded (item 9)

One `Index(Path)` per attempt; its identity (snapshot, policy version, lookup-result schema version, file SHA-256)
recorded once and compared before and after the attempt. Every query runs through `bounded_gather`
(`Index.gather_bounded`, budget `lookup_evidence_budget_bytes`, default 16 MiB); the unbounded `gather` is never
called. Over budget: `unavailable`, no events, `LOOKUP_EVIDENCE_LIMIT_EXCEEDED`, all or nothing [verified,
`test_lookup_overflow_is_unavailable_all_or_nothing`]. A raising query is `unavailable` with its code, never
`no_record` [verified, `test_a_failing_query_is_unavailable_never_no_record`]; an index that cannot open fails with
the Stage 02 code [verified, `test_corrupt_index_fails_lookup_with_the_stage02_code`]. Source-ref operations use the
schema's enum values (`index_identity`, `gather`); no schema change.

## 11. DETECT, ASSEMBLE, VERIFY (items 12–14)

- DETECT is a thin boundary (`adapters/detect.py`): committed NORMALIZE and LOOKUP outputs to a `Detector`, the
  detector's evidence, claims and evidence sets back as individual logical records. The controller derives
  decisions and questions and owns all batching (D-053, D-055). With no detector it fails `DECISION_TABLE_GAP`
  [verified, `test_no_detector_fails_detect_with_decision_table_gap`].
- ASSEMBLE uses `report.build` (D-054) unchanged, with real anchors, checked sources, extraction and index
  identities. Projections are empty (Step 10).
- VERIFY runs 14 named checks and fails closed with `VERIFY_FAILED` and the first failing check's code:
  `STAGE03_CAPTURE_VERIFIED`, `EXTRACTION_ROOT_IDENTITY`, `D043_UNIT_ANCHORS`, `EVIDENCE_POINTERS_RESOLVE`,
  `EVIDENCE_SETS_RESOLVE`, `D053_EVIDENCE_BATCHES`, `D055_ENTRY_BATCHES`, `STAGE02_INDEX_IDENTITY`,
  `BOUNDED_LOOKUP_PROVENANCE`, `NORMALIZE_REPLAY`, `DETECT_REPLAY`, `ASSEMBLE_REPLAY`, `COMPLETION_INVARIANTS`,
  **`D054_REPORT_GRAPH`**. [verified, `test_verify_passes_all_fourteen_checks_on_real_content`; each failure case:
  changed source byte, lookup missing an event, detector that drops a claim, report of another engine identity,
  shifted unit span.] The tamper tests change content at the reader, because Memory refuses bytes that do not hash
  to their name; they exercise each check's own logic.

## 12. Integration cases (item 16)

| Case | Result [verified, `test_step8_integration.py`] |
|---|---|
| Obokata ar (VS-2) | `NEEDS_RESOLUTION`. nature12968 + PMID 24476887: `RETRACTED_WORK_CITED`. nature12969 + PMID 24476881: Stage 02 pair `ambiguous_identity` → `IDENTITY_CONFLICT` with an open question. VERIFY passed, 14 checks. |
| Obokata evidence to the Step 9 boundary (item 11) | DOI and PMID arrive as separate typed, anchored occurrences of one unit; DOI alone `matched/exact` with the expected record ids; PMID 24476881 alone `no_record` (the page's PMID is not the record's 24476891: real data); the pair `ambiguous_identity`. |
| Obokata en (VS-3) | `COMPLETED`, two `RETRACTED_WORK_CITED`. |
| English MMR / Wakefield (VS-1) | `COMPLETED`. 10.1016/s0140-6736(97)11096-0 + 9500320 `RETRACTED_WORK_CITED`; the Lancet notice pair `notice_only` → no claim (Step 9); `NOT_FOUND_IN_CHECKED_SOURCES` claims carry the checked source of their deciding lookup. |
| No record | the `NOT_FOUND_IN_CHECKED_SOURCES` claims above. |
| Stage 02 unavailable | corrupt index → LOOKUP fails `INDEX_CORRUPT`/`INDEX_FORMAT_MISMATCH`; a non-Stage-02 SQLite file → `INDEX_FORMAT_MISMATCH`; a missing index → VALIDATE `INPUT_INVALID`, or LOOKUP `INDEX_MISSING` when it disappears after NORMALIZE; a raising query → `unavailable` with `INDEX_QUERY_FAILED`, never `no_record`. No claim in any of them. |
| Stage 03 failed extraction | Real reference-limit document → `EXTRACTION_FAILED`, reason `LIMIT_OCCURRENCES`, terminal. Real worker deadline (1 ms wall) → `EXTRACTION_DEADLINE_EXCEEDED` retryable twice, then `RETRY_BUDGET_EXHAUSTED` with that reason (D-050). |
| Lookup overflow | VS-1 with a 1-byte budget: every lookup that has records is `unavailable` with `LOOKUP_EVIDENCE_LIMIT_EXCEEDED` and no events; Wakefield becomes `LOOKUP_UNAVAILABLE`, no `RETRACTED_WORK_CITED`; outcome `partial`. |

## 13. Crash, resume, replay and STALE (items 17, 18)

- **Crash inside a step** (a child process dies with `os._exit` after the adapter's work, before commit) in ACQUIRE,
  EXTRACT, LOOKUP, DETECT and VERIFY: on resume that step has 2 attempts and every other step 1 (nothing committed is
  repeated), the claim ids **and the committed content digest `C(J)` (MM 7.3)** equal the uncrashed reference
  [verified, `test_process_death_inside_a_step_resumes_without_repeating_committed_steps` ×5].
- **Crash during the live child**: section 5.
- **STALE** [verified, `test_step8_resume_stale.py`]:

| Changed input (item 18) | Recorded `changed` |
|---|---|
| Capture digest: another bundle at the same path | `["root"]` |
| Capture digest: an unreadable bundle at the path | `["root"]` |
| Stage 03 extraction configuration (`max_refs`) | `["extraction"]` |
| Stage 03 profile (profile digest) | `["extraction"]` |
| Stage 02 index snapshot (index file bytes) | `["index"]` |
| Stage 02 lookup policy version | `["index"]` |
| Stage 04 schema version / decision-table version | `["stage04"]` |
| Stage 04 integration schema versions | `["stage04"]` |
| Lookup evidence budget | Not a STALE transition (owner decision D-057): a changed lookup evidence budget resolves to a different investigation key; the original investigation remains unchanged. [verified, `test_a_changed_lookup_budget_is_another_investigation`: same request and budget → same `config_digest` and key; another budget → another `config_digest` and key; the first journal's bytes are unchanged after the second investigation runs and the first is resumed; neither has a `stale_detected` record.] |

## 14. Only ACQUIRE uses the network (items 15, 17 criteria)

Every retained-mode and integration test runs under `NoNetwork` with 0 attempts. The live tests use a synthetic
transport and make no request. **[limit]** The in-process block does not reach the Stage 03 extraction worker, a
separate offline process of Stage 03 started by `extract_bundle(isolated=True)`; it is Stage 03's accepted offline
path and does no I/O beyond the bundle.

## 15. Performance and CI runtime (items 20, 21)

`step8_perf.py` → `step8_perf.json` (warm median of 5 fresh investigations per bundle, network refused):

Python 3.12.3, x86_64, 4 CPUs. Milliseconds; per step = adapter plus commit. DETECT is the SYNTHETIC detector.

| Bundle | ACQUIRE | EXTRACT | NORMALIZE | LOOKUP | DETECT | ASSEMBLE | VERIFY | Total run | Reopen / replay |
|---|---|---|---|---|---|---|---|---|---|
| VS-1 en MMR (warm median) | 31.3 | 632.2 | 589.7 | 580.1 | 164.2 | 86.2 | 1,530.3 | 3,653.0 | 308.3 |
| VS-2 ar Obokata (warm median) | 26.4 | 326.7 | 178.4 | 108.9 | 59.5 | 39.5 | 571.7 | 1,330.0 | 97.1 |
| VS-3 en Obokata (warm median) | 28.1 | 375.5 | 179.8 | 136.3 | 60.6 | 43.6 | 598.3 | 1,376.8 | 114.6 |

- Cold first runs: 3,577 / 1,317 / 1,437 ms total (EXTRACT 780 / 299 / 338 ms); cold and warm are close because
  EXTRACT starts the Stage 03 isolated worker process every time, and VERIFY re-runs Stage 03 `verify_bundle` and the
  NORMALIZE, DETECT and ASSEMBLE replays.
- Subset index build (Stage 02 `build`): 22 ms. Network attempts during the whole run: 0.
- **Supervisor kill/reap** (5 runs, child plus two descendants, one setsid; bound 1 s): `kill_ms` ≤ 3.1, `reap_ms`
  ≤ 1.2, `sweep_ms` ≤ 13.0; elapsed at the kill = the bound (1,000 ms, 0 ms overrun at ms resolution). The kill
  starts at `T_acq`; its cost does not depend on `T_acq`.
- These are the realistic retained-article numbers. The Stage 03-cap stress tests (`test_step7_closure.py` 50,000
  projections and evidence ids) are separate and unchanged; jsonschema was not optimized and no validation removed.

**CI runtime**, measured, not projected from one number.

- **Step 8 tests alone** (3 modules, 66 tests): **64.4 s** locally (Python 3.12.3, 4 vCPU). Slowest: the MMR module
  fixture 4.0 s, lookup overflow 3.9 s, the Retry-After resume test 3.2 s, the five crash/resume subprocess tests
  2.3–2.9 s each; every supervised-kill test about 1.5 s (a 1.5 s bound).
- **Full suite locally**, first timing run on 3.12.3 (tree before the last seven Step 8 tests): **2,971 passed, 0
  skipped, 15 min 16 s** (`--durations=25`); it shared the 4 vCPUs with ruff, mypy and the checkers for part of the
  time. Final runs on 3.12 and 3.13: section 18, criterion 27.
- **Slowest tests** (all pre-existing, none Step 8): `test_d047_report_with_50000_projections` 48.3 s, two Stage 00
  differential simulations 31.5 s and 31.2 s, `test_d047_claim_over_50000_evidence_ids…` 25.0 s,
  `test_crash_at_every_occurrence_of_every_controller_boundary` 22.9 s, `test_controller_reaches_every_declared_state`
  11.8 s.
- **GitHub CI baseline** (run 315, `b43fa03`): test step 13 min 29 s on 3.12 (job 13 min 52 s), 8 min 45 s on 3.13
  (job 9 min 14 s); limit 20 min. **[inference]** Step 8 adds about 1 min of test time, so 3.12 is projected near
  14.5–15 min, under the 18-min stop line. The pushed CI run is the measurement: **run 316 at `165c224`, green**:
  3.12 test step 8 min 37 s (job 8 min 52 s), 3.13 test step 13 min 17 s (job 13 min 41 s), `ci-gate` success. The
  baseline's slow job was 3.12 and this run's is 3.13: runner speed differs between jobs by about 5 minutes, so the
  budget is judged on the slower job. **Run 317 at `7dd1772`** (same code, closure text only), green: 3.12 test step
  14 min 57 s (job 15 min 17 s), 3.13 test step 12 min 43 s (job 13 min 7 s). Slowest job over both runs: **15 min
  17 s of 20**, under the 18-min line; against the baseline's slow job (13 min 52 s) Step 8 costs about 1.4 min on a
  slow runner. **[inference]** The remaining margin to 18 min is about 2.7 min, so Step 9 should not add more than
  about 2 min of CI test time without a runtime review.
- **Final local runs at `165c224`**, 3.12 and 3.13 at the same time on one 4-vCPU machine: **2,978 passed, 0 skipped**
  on each (3.12.3: 15 min 7 s; 3.13.18: 14 min 29 s); `check-report` 0 problems for both on the clean tree.

## 16. Inherited-baseline audit (item 19)

No Stage 00–03 file is changed [verified, `git diff b43fa03 -- src/citerift/wiki src/citerift/retraction
src/citerift/contracts src/citerift/governance schemas/governance schemas/wiki schemas/retraction .github` is empty].
Each verified finding:

| # | Finding (verified in code) | Class | Handling |
|---|---|---|---|
| B-1 | `capture_revision(transport=…)` disables Stage 03's NetworkGate: `Fetcher` sets `gate = None` when a transport is given (`wiki/fetch.py:437`). | Stage 03 design property; not a defect for Stage 03's own callers. | Live child never passes `transport=`; it wraps the module transport so the gate, throttling and retries stay as accepted. |
| B-2 | The NetworkGate records a Retry-After only after the body is read (`gate.release(...)` after the attempt, `fetch.py:498`). A kill during the body loses it. | Stage 03 limit relevant only to Stage 04's kill (F-11). | Stage 04 side channel (section 5). No Stage 03 change. |
| B-3 | `anchors.read_retained_source` (Step 6) reads from the bundle path. | Stage 04 Step 6 design that IF-7 supersedes. | Step 8 reads the source from Memory raw blobs; the function stays for its Step 6 tests. |
| B-4 | Stage 03 `verify._listed_artifacts` is private; Stage 04 re-derives the listed set. | Coupling risk. | Pinned by a drift test on three bundles. |
| B-5 | The Stage 03 capture schema leaves `failure_artifacts`, `attempts`, `issues` without `maxItems` (IF-7). | Inherited, bounded indirectly. | Bounded by the 4 MiB `capture.json` limit (section 2); IF-7 resolved. |
| B-6 | `verify_capture` reads every artifact with a 32 MiB limit. | Stage 03 limit. | Used as `MAX_ARTIFACT_BYTES` in the IF-7 bound. |
| B-7 | The investigation claim schema requires `PAIR_UNCORROBORATED` when pair coherence is `UNDETERMINED`. | Stage 04 schema rule (Step 5), correct. | The synthetic detector uses `NOT_DETERMINED` for unavailable pairs. Noted for Step 9. |
| B-8 | D-051 `work_candidate` pointer: two `CO_REPORTED_MULTIPLE` candidates in one unit can share a pointer. | **Forward finding for Step 9** (not reachable without dt-1 candidate splitting). | Not changed here; recorded for Step 9. |
| B-9 | Stage 02 `render` pages its event list (`page_size`). | Stage 02 property. | LOOKUP renders with `page_size=MAX_PAGE` and stores every event of the bounded gather separately, unpaged, under the byte budget (D-048). |
| B-10 | VS-2 page PMID 24476881 differs from the record's 24476891. | Real data, not a defect. | Kept: it is what makes the VS-2 identity conflict. |
| B-11 | D-050 coverage: every issue code the Stage 03 source emits is in its `CATALOG` (the one other upper-case token, `HTML_ENTITY_DECODED`, is a normalization step name, not a code). | No gap. | D-050 maps the three worker codes to themselves and every other catalog code to `EXTRACTION_FAILED`; an unknown code is `ADAPTER_INCONSISTENT`. |
| B-12 | A failed Stage 03 extraction document is committed as an observation on every failed attempt (Step 7 `Failed(evidence=…)`), so three worker deadlines commit the same blob three times by reference. | Stage 04 Step 7 behaviour, bounded (`A_max`). | Unchanged; noted. |
| B-13 | Stale Stage 04 text: SPEC MR-15 and RA R4-13 said F-11 was not implementation-verified and the live bound "not implemented yet"; D-055 records left IF-7 as a Step 8 condition. | Stale documentation (Stage 04, in progress). | SPEC MR-15 and RA R4-13 updated in this step; the D-055 closure records are historical and left as written. |
| B-14 | Notice relationships: the fixture holds the MMR Lancet notice (`notice_only`, 195 query states). No other Stage 02 relationship kind occurs in the three design bundles. | Coverage limit of the exposed bundles. | Stated; Step 9 and later evaluation need wider coverage. |
| B-15 | A missing index after VALIDATE and before LOOKUP is not STALE (no committed output depends on it yet); LOOKUP fails `INDEX_MISSING`. After LOOKUP committed, a changed index is STALE. | Correct by SPEC 10.3 (stale is about reused outputs). | Tested both ways. |

## 17. Changes to existing tests (disclosed)

- `memory_support.py`, `controller_support.py`: the SYNTHETIC bundle observation is now an IF-7 manifest over
  SYNTHETIC raw blobs; `verify_blob` checks raw blobs by digest.
- `test_d053_d054.py`, `test_d055.py`: the logical-view equivalence tests compare against the recorded baselines
  after renaming the one bundle observation back to its pre-Step-8 SYNTHETIC digest (`with_legacy_bundle`, which
  asserts there is exactly one and that it is the new manifest). Everything else must still equal the baselines.
- `test_controller_*`: forged `Succeeded` results carry `raw_blobs`.
- `test_memory_anchors.py`: the ACQUIRE record names the real IF-7 manifest.
- `test_memory_faults.py`, `test_memory_storage.py`: `verify_blob`.
- `test_schemas_step5.py`: the 5 new schema ids.
No assertion was removed or loosened beyond these substitutions.

## 18. Exit criteria (item 24)

| # | Criterion | Status and evidence |
|---|---|---|
| 1 | IF-7 resolved by a bounded representation | PASS. Section 2, `if7_bound.json`. |
| 2 | Retained Stage 03 bundle integration real | PASS. Sections 3, 12. |
| 3 | Bundle-path removal does not break replay | PASS. `test_removing_the_bundle_after_acquire_changes_nothing`. |
| 4 | Live ACQUIRE isolated under D-042 | PASS; no graceful-stop interval (D-056). Section 4. |
| 5 | Kill/reap measured and tested | PASS. Supervisor tests; `step8_perf.json`. |
| 6 | Retry-After safety proven | PASS. Section 5 table. |
| 7 | F-11 implementation-verified | PASS: IMPLEMENTATION_VERIFIED (D-056), with the double-fork/`setsid` attribution limit. |
| 8 | Real EXTRACT works | PASS. All three design bundles. |
| 9 | D-050 on real Stage 03 documents | PASS. Real `LIMIT_OCCURRENCES` → `EXTRACTION_FAILED`; real worker `EXTRACTION_DEADLINE_EXCEEDED` → retryable, same code. Every Stage 03 catalog code is mapped (B-11). |
| 10 | D-043 on real source bytes | PASS. Section 7. |
| 11 | NORMALIZE typed with D-051 ids | PASS. Section 8; `NORMALIZE_REPLAY`. |
| 12 | LOOKUP bounded path only | PASS. Section 10. |
| 13 | D-048 overflow all-or-nothing | PASS. `test_lookup_overflow_is_unavailable_all_or_nothing`. |
| 14 | Stage 02 index identity/provenance retained | PASS. Index identity observation; `STAGE02_INDEX_IDENTITY`; checked sources in NOT_FOUND claims. |
| 15 | Fixture provenance retained | PASS. Section 9. |
| 16 | Obokata conflict evidence intact | PASS. `test_obokata_doi_pmid_evidence_is_intact_to_the_step9_boundary`. |
| 17 | Only ACQUIRE can use the network | PASS, with the Stage 03 worker limit (section 14). |
| 18 | Retained mode works with sockets blocked | PASS. 0 network attempts. |
| 19 | Crash/resume repeats no completed work | PASS. Section 13. |
| 20 | Upstream identity changes give STALE | PASS for capture, extraction config, profile, index, policy, Stage 04 schema/plan. A changed lookup evidence budget resolves to a different investigation key; the original investigation remains unchanged, so it is not a STALE transition (D-057). |
| 21 | VERIFY records the D-054 check | PASS. `D054_REPORT_GRAPH` among 14 named checks. |
| 22 | Batching controller-owned | PASS. Adapters return individual records; `D053_EVIDENCE_BATCHES`, `D055_ENTRY_BATCHES`. |
| 23 | Record/journal/blob bounds valid | PASS. ACQUIRE record 176 B; blobs ≤ 32 MiB artifacts and 9.9 MB set under 256 MiB; D-055 bound tests pass. |
| 24 | Step 4 oracle unchanged | PASS. `git diff b43fa03 -- simulations/ docs/verification/stage-04/simulation tests/stage04/test_simulation_step4.py` empty; MANIFEST SHA-256 `411050772807cfbc…3e27735`. |
| 25 | Inherited-baseline audit retained | PASS. Section 16. |
| 26 | No Step 9 semantics | PASS. No dt-1, κ or precedence; the SYNTHETIC detector is test-only and labeled. |
| 27 | Full tests on 3.12 and 3.13 | PASS. 2,978 passed on 3.12.3 and on 3.13.18, locally and in CI run 316. |
| 28 | Zero required skips | PASS. 0 skipped; `check-report` 0 problems (local, both versions; CI step 14). |
| 29 | ruff / format / mypy | PASS (mypy: 86 source files, no issues). |
| 30 | pip-audit --strict | PASS. "No known vulnerabilities found" (locked export, `--require-hashes`); no dependency change. |
| 31 | Schema checks | PASS. `check-schemas` 0 problems; the 5 new schemas are tested in `test_schemas_step5.py`. |
| 32 | Step 3 consistency checker | PASS (0 failed). |
| 33 | citerift-gov check | PASS, 0 errors, 0 warnings. |
| 34 | render-status --check | PASS. |
| 35 | GitHub CI green within budget | PASS. Runs 316 and 317 green; slowest job 15 min 17 s of 20 (under 18). |

## 19. Owner decisions and carry-forward

- **D-056** (OD-S8-1): no graceful-stop interval; SPEC 9.2 corrected (section 4); F-11 IMPLEMENTATION_VERIFIED with
  the stated limitation (section 5).
- **D-057**: the lookup evidence budget is investigation identity; a changed budget is a different investigation,
  never STALE (section 13). SPEC S-10.1 states this; S-4.7 is unchanged.
- **Mandatory Step 9 input (owner, same message): B-8, the D-051 evidence-pointer collision in multi-candidate
  units.** Before the production decision table is frozen, Step 9 must determine whether `H(observation, pointer,
  evidence_kind)` is sufficient when one observation pointer can legitimately support more than one
  candidate-specific semantic fact; it must not silently merge distinct candidate evidence. Required: reproduce the
  collision fail-first; decide whether candidate identity, a sub-pointer or context must take part in evidence
  identity; keep replay deterministic; document any identity change before the Stage 04 freeze; test real
  multi-candidate units. This is a forward item; D-051 is not changed in Step 8.
