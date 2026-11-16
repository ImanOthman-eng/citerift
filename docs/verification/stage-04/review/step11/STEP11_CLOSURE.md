# Stage 04 Step 11: full production vertical slice VS-1 to VS-10 (closure record)

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPLPtkdbcpueYbnRk1ixuLdX` (2026-11-16T19:19:28Z): Step 10 accepted at
`c74a937487d83d793029858c6a671df628bae6f5`; "Proceed with Stage 04 — Step 11 only"; "Do not start Step 12". The
Step 10 acceptance and CI run 327 are recorded in `../step10/STEP10_CLOSURE.md` at commit `e409a74` (the baseline of
this step). Step 12 is not started: no freeze, no engine-version change, no evaluation, holdout, pre-registration,
annotation or scoring, no Stage 05+ work, no dt-1 change, no change to the frozen Step 4 oracle.

**Status: VERIFIED — AWAITING OWNER ACCEPTANCE** (section 15). Two items need an owner decision and do not block the
vertical-slice contract: the warm-investigation performance target is not met for two of eight cases (section 9) and
the investigation digests are bound to the exact Stage 02 index file (section 11, A11-3).

Labels: **[verified]** measured or tested here, with the file named; **[inference]** derived, not measured;
**[limit]** a stated limitation; **[owner]** needs an owner decision.

Data. Design-exposed inputs only (owner decision D-5): the SPEC S-7.4 bundles, the challenge bundles already used at
Steps 9 and 10, and two reserve bundles for VS-6. No holdout bundle, no Step 14 evaluation frame and no evaluation
data is read; dt-1 is not tuned. Nothing here is precision, recall or an evaluation (section 13).

## 1. What runs, and where the evidence is

`docs/verification/stage-04/evidence/vertical-slice/`:

- `run_vertical_slice.py`: the reproducible runner. It builds the Stage 02 index with Stage 02 `build` from the pinned
  Retraction Watch CSV (receipt `a987928`, CSV SHA-256 checked against the receipt), then runs every case through the
  production command line `citerift-investigate` (`cli.main`, the console-script function), each call a child process
  in a network namespace with no interface (`unshare -rn`). It retains the minimal evidence and writes
  `results/vertical_slice.json` (every case, check, digest, exit code, timing and network count).
- `vs_entry.py`: the instrumented entry. It calls `cli.main` after optional instrumentation chosen by environment
  variables, as the instruction allows (item 3): a socket counter that records and refuses every connect and DNS call;
  SIGKILL at a named controller fault point (VS-9); one extra property in the extraction document (VS-7c); another
  Stage 03 profile digest or Stage 04 identity (VS-10); the live ACQUIRE adapter with the SYNTHETIC-network child of
  the Step 8 tests (VS-8c). No instrumentation changes a scientific decision.
- `perf_breakdown.py`: where the time of one production investigation goes (section 9).
- `results/<case>/`: per successful case, the authoritative `journal.jsonl`, `report_manifest.json`,
  `projection_set.json`, the exported `v1/` records and `export.json` (export manifest); `VS-1/checkpoint.json`
  (D-052). Investigation Memory directories (blobs) are not committed: they are rebuilt from the bundle and the
  pinned snapshot (about 0.2 to 1.7 MB per case).

The full run: 146 command-line calls, 596 s including a real 200 s Retry-After wait; **all checks passed**
(`failed_checks: {}`) [verified, `results/vertical_slice.json`]. The scientific results come only through the
production controller, adapters, dt-1 detector, ASSEMBLE, VERIFY and report graph.

Inputs (exact):

| Case | Wiki, revision | Bundle (repository path) |
|---|---|---|
| VS-1 | en 1381772671 (MMR vaccine) | `docs/verification/stage-03/demonstrations/bundles/en-1381772671` |
| VS-2 | ar 76190003 (Obokata) | `tests/stage03/fixtures/observed/ar-76190003` |
| VS-3a | en 1372543632 (Obokata) | `tests/stage03/fixtures/observed/en-1372543632` |
| VS-3b | en 1374726997 (GFAJ-1) | `docs/verification/stage-03/demonstrations/bundles/en-1374726997` |
| VS-4 | en 1360148888 (Culturomics, expression of concern) | `docs/verification/stage-03/evaluation/confirmation-2026-11/campaign/capture/bundles/challenge/en-65547507-a1` |
| VS-5 | ar 76488293 (BCAS3) | `docs/verification/stage-03/evaluation/capture/bundles/challenge/ar-4541237-a1` |
| VS-6a | ar 73356164 | `docs/verification/stage-03/evaluation/capture/bundles/reserve/ar-9617858-a1` |
| VS-6b | en 1345535167 | `docs/verification/stage-03/evaluation/confirmation-2026-11/campaign/capture/bundles/reserve1/en-44351447-a1` |

Stage 02 index: snapshot `rw-2f116e9ffed718e6`, CSV SHA-256 `2f116e9f…a655`, built here in 75.5 s, file
278,769,664 bytes, file SHA-256 `011a0284cf58824cc1541caff6ca2daedb6d3e18235a9be628db1ac629fba896` (section 11,
A11-3). Engine identity: Stage 04 engine 0.1.0, schema 2.0.0, plan-1, dt-1; Stage 03 extractor 1.2.0, profile 1.0.0.

## 2. Result table (VS-1 to VS-10)

| Case | Result | Lifecycle | Report outcome (S-9.7) | Exit (run/show/verify/replay/export) | Claims by class |
|---|---|---|---|---|---|
| VS-1 | PASS (19 checks) | COMPLETED | partial | 6/6/6/6/6 | RETRACTED 1, NOTICE 1, NOT_FOUND 41, NO_IDENTIFIER 52 |
| VS-2 | PASS (19) | NEEDS_RESOLUTION | partial | 10/10/10/10/10 | RETRACTED 1, IDENTITY_CONFLICT 1, NOT_FOUND 1, NO_IDENTIFIER 29 |
| VS-3a | PASS (14) | COMPLETED | completed | 0/0/0/0/0 | RETRACTED 2, NOT_FOUND 1, NO_IDENTIFIER 30 |
| VS-3b | PASS (14) | COMPLETED | completed | 0/0/0/0/0 | RETRACTED 2, NOTICE 2, NOT_FOUND 28, NO_IDENTIFIER 30 |
| VS-4 | PASS (16) | COMPLETED | completed | 0/0/0/0/0 | CONCERN 1, NOT_FOUND 7 |
| VS-5 | PASS (16) | COMPLETED | completed | 0/0/0/0/0 | RETRACTED 2, NOT_FOUND 11, NO_IDENTIFIER 1 |
| VS-6a | PASS (17) | COMPLETED | completed | 0/0/0/0/0 | NOT_FOUND 1 |
| VS-6b | PASS (16) | COMPLETED | completed | 0/0/0/0/0 | NOT_FOUND 4 |
| VS-7a–c | PASS (7 each) | FAILED | none | run 9, export 9 (refused) | none |
| VS-7d–e | PASS (3 each) | none (nothing created) | none | 3 | none |
| VS-8a–b | PASS (7 each) | FAILED | none | run 9, export 9 (refused) | none |
| VS-8c | PASS (7) | BLOCKED, then NEEDS_RESOLUTION after not_before | none while BLOCKED | 8, resume early 8, export 8; resume after 10 | none while BLOCKED |
| VS-9 | PASS (8 per kill point, 3 points) | COMPLETED after resume | partial | kill −9, show 14, resume 6 | = VS-1 |
| VS-10 | PASS (15) | unchanged | — | replay/verify 11 per mutation | — |

Digests (full values in `results/vertical_slice.json`):

| Case | Investigation key | C(J) | Report | Projection set | Projections | Journal (seq 25) |
|---|---|---|---|---|---|---|
| VS-1 | `466f12f4…` | `5ebecbd4…` | `20a3b122…` | `1497abf8…` | 1 | `a6f61030…` |
| VS-2 | `6fb93733…` | `896471ae…` | `d8988973…` | `dec6bc16…` | 1 | see JSON |
| VS-3a | `ef90ada3…` | `164e4c48…` | `7e059e08…` | `19cbe5dc…` | 2 | see JSON |
| VS-3b | `3aa4b256…` | `4ffe411e…` | `c8148e7d…` | `8c6a7702…` | 1 | see JSON |
| VS-4 | `88242345…` | `31139722…` | `35898b2e…` | `5f43c2f1…` | 1 | see JSON |
| VS-5 | `8f72ab93…` | `ef8564b5…` | `899a9bcd…` | `2274f889…` | 1 | see JSON |
| VS-6a | `329c2822…` | `72b35e71…` | `613ab70e…` | `474f0155…` (empty set) | 0 | see JSON |
| VS-6b | `68db59fa…` | `f3974c69…` | `238c180f…` | `474f0155…` (empty set) | 0 | see JSON |

Every successful case [verified, per-case checks]: VERIFY passed every named check; the report graph re-proved
(Memory open and `D054_REPORT_GRAPH`); every v1 record valid against contracts v1 1.0.1
(`projections.record_problems`); projection count = distinct positive works; no projection without a positive
claim; export succeeded only after VERIFY and its report and projection-set digests equal the committed ones;
replay `reproduced` (first difference: none); five repeated runs of each case gave the same C(J); the S-7.7
forbidden-phrase scan of the summary, explanations and limitations found nothing; exit code matches the status; zero
network attempts.

## 3. Case findings

**VS-1 (MMR).** Wakefield (`10.1016/s0140-6736(97)11096-0`, PMID 9500320): `RETRACTED_WORK_CITED`, D-14,
REPORT_FINDING. Lancet notice (`10.1016/s0140-6736(10)60175-4`, PMID 20137807): `NOTICE_CITED`, D-15, reasons
`CITED_IDENTIFIER_IS_NOTICE`, `PAIR_UNCORROBORATED` (D-058); it is not a positive work and no work is keyed by it.
Markers are observed (marker_target identifiers and marker states retained by Stage 03) and no marker target is a
candidate key. The summary states each class separately ("Claims by class: NOTICE_CITED: 1, … RETRACTED_WORK_CITED:
1 …"). One v1 projection, for the Wakefield work only. Lifecycle COMPLETED; report outcome `partial` (Stage 03
extraction partial).

**VS-2 (ar Obokata).** `nature12968` (PMID 24476887): `RETRACTED_WORK_CITED`. `nature12969` + PMID 24476881:
`IDENTITY_CONFLICT`, D-6, `conflicting`, coherence INCOMPATIBLE, reasons `IDENTITY_WITNESSED`, `KEY_RESULTS_DIFFER`,
two alternatives, 12 supporting evidence items [verified, read from the investigation's evidence set `f687e7e0…`]:
both identifier occurrences (each with its Stage 03 anchor), the citation unit, three lookup results (Q1 for the DOI,
Q1 for the PMID, Q2 for the pair), two lookup events, the index identity, the work candidate, the coherence evidence
(INCOMPATIBLE) and the use eligibility; deciding lookup state `ambiguous_identity`, disposition ROUTE_NEEDS_RESOLUTION, one open
question (`identity_conflict`, question `5f29fa3d…`); no positive and no NOT_FOUND claim for that candidate.
Lifecycle NEEDS_RESOLUTION; replay `reproduced` names the same conflict claim id `a0d520f7…`; replay recomputes the
DETECT and ASSEMBLE outputs and finds every digest equal to the committed one (S-10.3), so the claim, evidence and
question records, and their ids, are preserved. Export after VERIFY is allowed and succeeded.

**VS-3 (en Obokata, GFAJ-1), guards I-1.** en Obokata: two distinct works (nature12968, nature12969), two
projections. GFAJ-1: the work `10.1126/science.1197258` is cited twice and gives **one** positive work holding both
claim ids and **one** v1 record listing both citations; the two notice citations (`science.1208877`,
`science.adu5488`) are `NOTICE_CITED` and are not works. Positive works are keyed by Stage 02 identity anchors.

**VS-4 (expression of concern).** `10.1371/journal.pone.0223543`: `CONCERN_CITED`, D-14, never
`RETRACTED_WORK_CITED`. v1 record: event `expression_of_concern`, status not `retracted`. Explanation (fixed
template): "The checked sources record an expression of concern for the work this citation identifies. …"; no
explanation mentioning the concern contains "retract". Provenance walk complete (section 6).

**VS-5 (BCAS3, D-059).** Both citations of `10.1210/me.2006-0514` / PMID 17505058 are `RETRACTED_WORK_CITED` under
**D-14**, as dt-1 decided. `PMID_ROLE_COLLISION` is present in the three committed lookups (pair, DOI-only,
PMID-only) and is resolvable in each deciding claim's committed evidence set (three evidence items, pointer
`/result`). It is **not** a claim reason: D-14 does not use it (reasons `[]`); it would be a reason only under D-10.
One positive work, one projection. The v1 record has no event because the Retraction Watch dates of this work have no
day (the documented Step 10 lossy mapping `V1_EVENTS_WITHOUT_DAY_OMITTED`) [limit]. Replay reproduced. This closes
the D-059 carry-forward.

**VS-6 (NOT_FOUND).** ar 73356164 (1 identifier) and en 1345535167 (4): only `NOT_FOUND_IN_CHECKED_SOURCES` among
keyed claims, every deciding lookup `no_record`, checked-source identity retained, no positive work, no projection.
Summary: "For the 1 identified citation(s) listed, no matching record was found in the checked sources (snapshot
rw-2f116e9ffed718e6)." Explanation: "No matching record was found in the checked sources. Checked sources:
retraction-watch (a987928…)." None of "clean", "safe", "not retracted", "no retracted citations" appears.

**VS-7 (failures).** (a) one retained artifact byte changed → ACQUIRE `BUNDLE_ARTIFACT_CORRUPT`; (b) the capture's
revision id changed so it no longer matches its content → ACQUIRE `BUNDLE_SEMANTIC_INVALID`; (c) a schema-invalid
extraction document → EXTRACT `ADAPTER_INCONSISTENT`. Each: lifecycle FAILED, exit 9, JSON `status: failed` with the
step, code and reason, no claim (so no NOT_FOUND), no report, export refused (exit 9, nothing written). (d) An invalid
revision request (revision id 0) and (e) a schema-invalid request (unknown property): exit 3 `REQUEST_INVALID`
(machine-readable error), refused **before any investigation exists**, so there is no lifecycle, no journal and
nothing to export. [owner, interpretation] The instruction asks for "lifecycle FAILED" for an invalid revision
request; the accepted Step 10 CLI refuses such a request at the boundary (exit 3, nothing created), which is
stronger than a FAILED investigation. A revision that does not match its bundle (VS-7b) is the case that reaches
FAILED. Not changed.

**VS-8 (unavailable, blocked).** Missing index → VALIDATE `INPUT_INVALID` / `INDEX_PATH_INVALID`; a SQLite file of
another format → LOOKUP `INDEX_FORMAT_MISMATCH`. Both FAILED (exit 9), no claim, no negative statement, export
refused. Retry-After (SYNTHETIC network; `live_fake_child.py` mode `throttled:200`, a complete 429 so Stage 03
itself defers): `run` → BLOCKED, exit 8, ACQUIRE `deferred` with `not_before`, next action `wait` (T-RESTART), no
claim and no report; `resume` before `not_before` → exit 8, ACQUIRE not started, journal byte-identical, returned in
0.5 s (no sleep); `export` while BLOCKED → exit 8, nothing written. The runner then waited until `not_before`
(the command never sleeps) and `resume` started the second ACQUIRE attempt at 19:57:58.76Z, after `not_before`
19:57:57.07Z, and completed (NEEDS_RESOLUTION, the VS-2 content), as D-042/F-11 require. Each live attempt runs in
the D-042-bounded child; the CI test of the restart instant is the accepted Step 8 test
`test_retry_after_resume_waits_before_the_instant_and_starts_at_it`.

## 4. VS-9: interrupted and resumed VS-1

Three kill points inside DETECT (SIGKILL, no clean-up): `controller.after_start`, `controller.after_adapter`,
`controller.after_entry_batch` (after one D-055 entry batch was written). In each, LOOKUP had committed and DETECT was
open. `show` after the kill: exit 14 (`incomplete`). `resume` through the command line: exit 6 (partial, = VS-1).

- ACQUIRE, EXTRACT, NORMALIZE and LOOKUP: not repeated (one `step_started` each); only DETECT was retried
  (`step_interrupted` then attempt 2), then ASSEMBLE and VERIFY ran.
- Same claims; same report digest `20a3b122…`; same projection-set digest `1497abf8…`; same C(J) `5ebecbd4…` as the
  uninterrupted VS-1 run, for all three kill points [verified, `vs9[*]` in the JSON].
- The transition comparison (seq, kind, step, attempt) of the interrupted and the reference journals is retained in
  `vs9[*].transitions_interrupted` / `transitions_reference`; timestamps are not compared (excluded from C(J)).

## 5. VS-10: replay and STALE; D-057

Every completed and needs-resolution case replays `reproduced` (section 2). On VS-2, one identity changed at a time,
then restored [verified, `vs10`]:

| Mutation | replay | verify |
|---|---|---|
| another capture at the bundle path (root) | 11 `stale` [`root`] | 11 `stale` [`root`] |
| Stage 03 profile digest (extraction identity) | 11 `stale` [`extraction`] | 11 `stale` [`extraction`] |
| Stage 02 index bytes | 11 `stale` [`index`] | 11 `stale` [`index`] |
| Stage 04 schema version | 11 `stale` [`stage04`] | 11 `stale` [`stage04`] |
| Stage 04 engine version | 11 `stale` [`stage04`] | 11 `stale` [`stage04`] |

Replay never wrote the journal; restored inputs replay `reproduced` again. D-057: a run with another lookup evidence
budget (8 MiB) gets another investigation key (`d6643d07…`); the first investigation has no `stale_detected` record,
its journal is unchanged, and it still replays `reproduced`.

**Fault found and fixed (category 2, Step 10 delivery defect).** Before the fix, `verify` returned 5
(`verify_failed`) for a Stage 04 identity change while `replay` returned 11 (`stale`): the re-derivation checks
(`NORMALIZE_REPLAY`, `DETECT_REPLAY`, `ASSEMBLE_REPLAY`, `V1_PROJECTIONS`) re-run Stage 04 code and fail when that
code's identity changed. `operations._verify` now classifies those failures as `stale` when `stage04` is among the
changed identities; every other failed check of a verified lifecycle stays `verify_failed`. SPEC note after S-10.5.
Compact CI test: `test_vs10_verify_and_replay_name_each_changed_identity`.

## 6. Provenance walks (item 20)

An independent walk (in the runner, using only the journal, blobs, the retained Stage 03 artifacts and the pinned
CSV) for a positive (VS-1 Wakefield, VS-5), a notice (VS-1 Lancet), a conflict (VS-2), a concern (VS-4) and a
NOT_FOUND (VS-6a) claim; 11 links each, **all verified**:

1. journal hash chain (every `prev` and record digest recomputed);
2. Wikipedia revision → Stage 03 capture (wiki, revision id, capture SHA-256);
3. evidence set → evidence items (every evidence id recomputed with `ids.evidence_id`, every pointer resolved);
4. Stage 03 extraction → source byte anchor (artifact SHA-256 and the D-043 span SHA-256 re-hashed from the retained
   artifact; e.g. VS-1 bytes 32667–33428 of unit `un-00048` contain "9500320" and "10.1016/S0140-6736(97)11096-0");
5. source anchor → normalized identifiers;
6. Stage 02 lookup → event row hash (each `row_sha256` recomputed from the pinned CSV row);
7. Stage 02 lookup → pinned index identity;
8. dt-1 rule → claim id (recomputed with `ids.claim_id`);
9. claim → decision (decision id recomputed);
10. decision → report claims component (the claim is in the committed report);
11. report → v1 projection: exported record = stored body + the approved `created_at` (positive), or no projection
    (non-positive).

## 7. I-2, I-3, I-4

**I-2** (cases with Stage 03 extraction `partial`) [verified, `i2`]:

| Case | workflow.outcome() | report outcome | v1 status | CLI status | export status | lifecycle |
|---|---|---|---|---|---|---|
| VS-1 | **completed** | partial | partial | partial (exit 6) | partial (exit 6) | COMPLETED |
| VS-2 | partial | partial | partial | needs_resolution (exit 10) | exit 10 | NEEDS_RESOLUTION |

The discrepancy exists only in the internal `workflow.outcome()` helper; the report, the v1 projections, the CLI and
the export all say `partial`. Per the instruction, **I-2 stays a Step 12 freeze-review item**; it is not a Step 11
blocker. Compact CI test: `test_i2_partial_extraction_is_partial_in_every_user_visible_output`.

**I-3.** Not changed: no engine-version change. Every vertical-slice investigation was created fresh from this code
(new memory roots). Older development journals (assembled before Step 10) are not freeze artifacts. Carried to Step
12 with A-6.

**I-4.** No validation or interpretation defect appeared: every projection set and v1 record validates and every
export equals the stored body plus `created_at`. The schema description wording stays a Step 12 review item;
schemas unchanged.

## 8. Offline guarantee and network isolation (item 19)

Every call ran in `unshare -rn` (no network interface) with the `vs_entry.py` socket counter: **0 network attempts in
146 calls** [verified, `network`]. The only live-capture request (VS-8c) used the SYNTHETIC child (no request leaves
the machine; the namespace has no interface). [limit] The counter is installed in the command's own process; the
live-capture child of VS-8c and the Stage 03 worker are covered by the namespace, not by the counter. The Stage 03
network gate file was isolated per run (A11-2).

## 9. Performance (item 22)

Per case, 5 repeated fresh runs on the full index (4 vCPU, Python 3.12.3), seconds, p95 [verified,
`cases[*].perf`]:

| Case | total wall | journal span | VALIDATE | ACQUIRE | EXTRACT | NORMALIZE | LOOKUP | DETECT | ASSEMBLE | VERIFY | replay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VS-1 | **6.57** | 5.67 | 0.01 | 0.02 | 0.49 | 0.44 | 0.89 | 0.69 | 0.32 | 1.25 | 2.34 |
| VS-2 | 3.75 | 3.31 | 0.01 | 0.03 | 0.26 | 0.13 | 0.48 | 0.17 | 0.11 | 0.51 | 1.25 |
| VS-3a | 3.77 | 3.30 | 0.01 | 0.02 | 0.25 | 0.14 | 0.49 | 0.18 | 0.11 | 0.50 | 1.30 |
| VS-3b | **5.39** | 4.74 | 0.01 | 0.02 | 0.41 | 0.31 | 0.72 | 0.47 | 0.25 | 0.98 | 1.91 |
| VS-4 | 3.34 | 2.96 | 0.01 | 0.02 | 0.22 | 0.07 | 0.53 | 0.10 | 0.06 | 0.39 | 1.07 |
| VS-5 | 3.72 | 3.28 | 0.01 | 0.03 | 0.23 | 0.12 | 0.55 | 0.16 | 0.11 | 0.48 | 1.21 |
| VS-6a | 2.94 | 2.62 | 0.01 | 0.03 | 0.14 | 0.02 | 0.43 | 0.02 | 0.02 | 0.26 | 0.91 |
| VS-6b | 3.02 | 2.68 | 0.01 | 0.02 | 0.15 | 0.03 | 0.45 | 0.05 | 0.03 | 0.31 | 0.92 |

**Target "warm investigation of a retained bundle ≤ 5 s p95" (master package): met for 6 of 8 cases, not met for
VS-1 (6.57 s) and VS-3b (5.39 s).** The gate is not claimed as passed.

Diagnosis (`perf_breakdown.py`, VS-1, 5 samples, medians) [verified, `results/perf_breakdown.json`]: the command's
`run` takes 6.11 s, of which

- **1.92 s: whole-file SHA-256 of the 278 MB Stage 02 index, 10 times** (the S-10.1 identity check before each of
  the 8 steps, and twice in LOOKUP). This is the gap between the sum of the step spans (4.1 s) and the journal span
  (5.7 s), plus the LOOKUP part;
- **2.74 s: JSON Schema validation, 939 validator calls** (contract checks of every stored and re-read document,
  including Memory's re-proof on open, 0.57 s for 4 opens, and the `show` the command prints, 0.59 s);
- 1.45 s: everything else (Stage 03 worker, Stage 02 queries, dt-1, canonical encoding, writes, fsync);
- import 0.17 s.

Cost grows with the number of citations (VS-1 95 claims, VS-3b 62; the 2.9 to 3.8 s cases have 1 to 33). Both
large costs are integrity checks, and no validation was weakened. [owner] Options, none applied: (a) accept the
measured times as the Step 11 result and revisit the target at Step 12; (b) a narrow change that keeps every check
but hashes the index once per process while its `stat` (size, mtime_ns, ctime_ns, inode) is unchanged; (c) both
(b) and a cache of compiled schema validators if profiling shows compilation in the 2.7 s. Each of (b) and (c) is a
Stage 04 change that would need its own evidence.

Replay p95 0.9 to 2.3 s. Journal and memory size per article: 14.7 KB journal, at most 1.73 MB in total (target
≤ 10 MiB) [verified].

## 10. Runtime of the tests and CI (item 23)

New CI tests: one module, `tests/stage04/test_step11_vertical_slice.py`, **7 tests, about 24 s locally**, on the
attributed Retraction Watch subset of Step 8 (no full index in CI). They cover the VS semantic contracts that no
earlier test covers: VS-3 one work cited twice (I-1), VS-6 scoped NOT_FOUND, VS-7 schema-invalid extraction, VS-8
Retry-After BLOCKED with no early start and no export, VS-9 a real SIGKILL and command-line resume to the same
content, VS-10 verify and replay naming each identity, and I-2. VS-1, VS-2, VS-4, VS-5 and the remaining failures
are already covered by the Step 8, 9 and 10 tests on the same bundles. The full vertical slice stays an explicit
script (about 10 minutes). No test removed or weakened; no timeout and no `.github/` change.

- **Full suite locally at `d4e819e`, clean tree**: **3,187 passed, 0 skipped on Python 3.12.3** (14 min 18 s) and
  **3,187 passed, 0 skipped on Python 3.13.18** (13 min 30 s); `check-report` 0 problems for both reports (revision
  `d4e819e`, `dirty: false`) [verified]. Step 10 had 3,180; the 7 new tests are this step's module.
- **Correction to the Step 10 record [verified]:** the local environment used for "3.13" in Step 10 had been
  recreated with Python 3.12.3 (`pyvenv.cfg` `version_info = 3.12.3`, created 16:33 on 2026-11-16), so the Step 10
  local "3.13" run of 3,180 tests was almost certainly a second 3.12 run [inference: no report file of that run
  survives]. Python 3.13 was nonetheless verified for Step 10 by GitHub CI (runs 326 and 327, 3.13 jobs green). The
  Step 11 3.13 run above used a fresh environment synced from the lock with `--python 3.13`, and its test report
  records 3.13.18.
- **GitHub CI run 329 at `d4e819e`: green** (`ci-gate` success). 3.12: job 20:14:24Z to 20:29:53Z, **15 min 29 s**;
  test step 15 min 08 s. 3.13: job 13 min 14 s; test step 12 min 52 s. **Slowest job 15 min 29 s, about 2 min 31 s
  under the 18-min decision boundary.** For comparison, run 328 at `e409a74` (closure record only): 3.12 job 12 min
  12 s, 3.13 job 16 min 04 s; run 327: 16 min 47 s. [inference] Runner variance between runs (up to about 4.5 min for
  the same code) is much larger than the about 0.5 min this step adds; the margin should keep being watched.

## 11. Inherited-baseline audit (item 27)

| Id | Finding | Classification | Action |
|---|---|---|---|
| A11-1 | `verify` gave `verify_failed` (5) for a Stage 04 identity change while `replay` gave `stale` (11) | Step 10 delivery defect (category 2), stale semantics mismatch | Fixed narrowly in `operations._verify`; SPEC note; CI test (section 5) |
| A11-2 | The Stage 03 network gate keeps its state in one host-wide file by default (`~/.cache/citerift/wiki-network.lock`). A SYNTHETIC 429 with Retry-After in one test run is persisted there and made a later run defer to the earlier instant | Test-fixture defect in the new Step 11 test and runner (category 1); the host-wide gate is accepted Stage 03 design (one request in flight per host) | The Step 11 test and the runner set `CITERIFT_WIKI_NETWORK_LOCK` to their own file, as the Step 8 tests already do. Stage 03 not changed |
| A11-3 | Two builds of the Stage 02 index from the same pinned CSV are not byte-identical (the file SHA-256 differs; Stage 02 RISK E10 accepts this). Stage 04 binds the index identity to the file SHA-256 (S-10.1, A-1), and that identity enters evidence, claim ids, the report and C(J). A rebuild therefore gives other claim ids, report digests and C(J), and `replay` of an existing investigation against a rebuilt index says `stale` [`index`] [verified: two builds, `f6bd5e6e…` and `011a0284…`; replay 11 stale `index`]. Classes, claims by class, projection-set digests and investigation keys are the same across builds | Specification interaction (category 7), not a contradiction: both rules hold as written | Not changed. The recorded digests reproduce only with the index file whose SHA-256 is recorded (not committed: 279 MB). [owner] for Step 12: keep the exact index file as a release artifact, or define the Stage 04 index identity by a reproducible Stage 02 content digest (an architecture change) |
| A11-4 | Warm investigation above 5 s p95 for VS-1 and VS-3b | Performance, not a defect | Diagnosed (section 9); [owner] |
| A11-5 | Two user-visible forms of "wait until not_before": a Stage 03 deferral gives BLOCKED (exit 8); a D-042 kill after Retry-After headers were seen gives a retryable `step_failed` with `not_before`, lifecycle RUNNING with next action `wait` (exit 14) (`test_step8_live.py`) | Accepted Step 7/8 semantics (deferred vs retryable failure) | Not changed; both refuse to start early and export nothing. Step 12 review item |
| A11-6 | The retained journals record the request with absolute local paths (bundle, index, memory root) | Accepted request schema; the journal bytes are authoritative and are not rewritten | Not changed; the paths name scratch directories only |

Watched and not found [verified by the runs]: no incomplete or unreconstructible Stage 03 bundle among the inputs
(every ACQUIRE verified its bundle and every replay re-derived its extraction); no Stage 02 anchor split or collapse
(VS-3); no report/projection mismatch; no CLI lifecycle mismatch; no evidence or reference loss (every walk link and
pointer resolves); no hidden network use; no wording that contradicts D-058, D-059 or D-060. Stages 00–03 are not
changed.

## 12. Originality and differentiation checkpoint (item 26)

Practical properties shown end to end by this vertical slice only; no novelty is claimed and no prior-art search was
made here (primary-source prior-art review remains gate 04-J, Steps 12 to 15).

- **Notice ≠ original.** VS-1 and VS-3b: the notice citations are `NOTICE_CITED` and never become works or
  projections; the retracted originals are separate positive works.
- **Contradiction before positive.** VS-2: a DOI and PMID that the checked sources assign to different works stay
  `IDENTITY_CONFLICT` with both alternatives and an open question; no positive and no NOT_FOUND claim is made for
  them, and the investigation ends NEEDS_RESOLUTION.
- **No false negative from no-record.** VS-6: absence gives only the scoped sentence; VS-7/VS-8 failures give no
  claim at all, so a failure never reads as "not found".
- **Byte-exact citation provenance.** Every walk re-hashes the D-043 source span from the retained Wikipedia artifact
  and recomputes the Retraction Watch row hash from the pinned CSV.
- **Deterministic replay.** Every case replays `reproduced`; five repeated runs give the same C(J); a SIGKILL in
  DETECT resumes to the same C(J), report and projection set.
- **Verifiable report and checkpoint.** VERIFY re-proves the report graph; the export equals the committed report;
  a D-052 checkpoint written outside Memory for VS-1 (seq 25, journal digest `a6f61030…`, the final record) verifies
  `CHECKPOINT_MATCH`.

## 13. Design-only evidence (item 25)

Inputs are the S-7.4 bundles, challenge bundles already exposed at Steps 9 and 10, and two reserve bundles; the
runner reads no holdout directory and no evaluation frame. No result here is used to tune dt-1 (no dt-1, table,
detector or D-051 identity file changed: `git diff e409a74 -- src/citerift/investigation/dt1.py
src/citerift/investigation/adapters/detector.py src/citerift/investigation/ids.py` is empty).

## 14. Secret scan (item 24)

Before `git add`, the D-036 secret gate (`docs/verification/stage-03/evaluation/confirmation-d036/scripts/secret_gate.py`,
the Stage 00 `SECRET_PATTERNS` plus the access-URL and key shapes) scanned all 48 new files of the evidence directory:
**no match, nothing withheld** [verified]. The Stage 00 repository secret test passes in the full suite. The retained
files hold identifiers, digests and Stage 04 records, not captured page text.

## 15. Exit criteria (item 28)

| # | Criterion | Result |
|---|---|---|
| 1 | Step 10 acceptance / run-327 closure recorded | PASS. `e409a74` (`STEP10_CLOSURE.md`). |
| 2 | VS-1 passes | PASS. 19 checks (section 3). |
| 3 | VS-2 passes | PASS. 19 checks. |
| 4 | VS-3 passes | PASS. 14 checks each for en Obokata and GFAJ-1; I-1 guarded. |
| 5 | VS-4 passes | PASS. 16 checks; CONCERN_CITED, never RETRACTED, no retraction wording. |
| 6 | VS-5 passes incl. D-059 evidence-level collision proof | PASS. Collision in 3 committed lookups and in each deciding evidence set; D-14; not a reason. |
| 7 | VS-6 passes with scoped NOT_FOUND wording only | PASS. Two articles; forbidden phrases absent. |
| 8 | VS-7 failure cases pass | PASS. 7a–c FAILED (exit 9) with stable codes; 7d–e refused (exit 3, nothing created) [owner, interpretation, section 3]. |
| 9 | VS-8 unavailable/blocked cases pass | PASS. Missing and foreign index FAILED; Retry-After BLOCKED, no early start, no sleep, no export, restart after not_before. |
| 10 | VS-9 identical C(J) | PASS. Three kill points; same C(J), report, projection set, claims. |
| 11 | VS-10 reproduced/stale | PASS. Five mutations name their identity in replay and verify; D-057 holds. |
| 12 | every successful real case validates the report graph | PASS. VERIFY and Memory re-proof for all 8 cases. |
| 13 | every positive-work projection validates v1.0.1 | PASS. |
| 14 | no non-positive case emits a positive projection | PASS. VS-6 0 projections; conflict and notice none. |
| 15 | identity conflicts remain NEEDS_RESOLUTION | PASS. VS-2, VS-10 and VS-8c resume. |
| 16 | report/export gating correct | PASS. Export only after VERIFY; refused for FAILED (9) and BLOCKED (8); STALE and CORRUPT refusals are Step 10 tests. |
| 17 | at least one external checkpoint verified | PASS. VS-1: seq 25, journal digest = final record, CHECKPOINT_MATCH. |
| 18 | network isolation passes | PASS. 0 attempts in 146 calls, no network interface. |
| 19 | full provenance walk succeeds | PASS. 6 walks, 11 links each (section 6). |
| 20 | I-2 practical effect recorded | PASS. Section 7; Step 12 item, not a blocker. |
| 21 | I-3 deferred to Step 12 | PASS. No engine-version change. |
| 22 | I-4 deferred unless substantive | PASS. Not substantive; schemas unchanged. |
| 23 | no final evaluation/holdout data touched | PASS. Section 13. |
| 24 | originality checkpoint retained | PASS. Section 12. |
| 25 | inherited audit retained | PASS. Section 11 (A11-1 to A11-6). |
| 26 | full tests pass on 3.12 and 3.13 | PASS. 3,187 each (section 10). |
| 27 | zero required skips | PASS. 0 skipped; check-report 0 problems. |
| 28 | ruff passes | PASS. `ruff check .`: all checks passed. |
| 29 | format check passes | PASS. `ruff format --check .`: 539 files formatted. |
| 30 | mypy passes | PASS. No issues in 95 source files. |
| 31 | pip-audit --strict clean | PASS. Locked export, all groups: no known vulnerabilities. |
| 32 | schemas pass | PASS. `check-schemas`: 2 schemas, 0 problems. |
| 33 | Step 3 checker passes | PASS. 0 failed. |
| 34 | frozen Step 4 oracle unchanged | PASS. `git diff 7ed2148 -- simulations/` empty. |
| 35 | citerift-gov check 0/0 | PASS. 0 errors, 0 warnings. |
| 36 | render-status --check passes | PASS. PROJECT_STATUS.md up to date. |
| 37 | CI green and below 18 min | PASS. Run 329: slowest job 15 min 29 s. |

The performance target (section 9) is not an exit criterion of this instruction; it is reported as not met for two cases and left to the owner.

## 16. Files

New: `docs/verification/stage-04/evidence/vertical-slice/{run_vertical_slice,vs_entry,perf_breakdown}.py` and
`results/`; `tests/stage04/test_step11_vertical_slice.py`; this record. Changed:
`src/citerift/investigation/operations.py` (A11-1), `tests/stage04/live_fake_child.py` (SYNTHETIC `throttled` mode),
`docs/verification/stage-04/SPECIFICATION.md` (Step 11 note after S-10.5). Not changed: `.github/`,
`src/citerift/governance`, `schemas/`, Stages 00–03 code, dt-1, the Step 4 oracle.

## 17. Owner decisions

None was taken in this step. Open:

1. [owner] Performance target (section 9, A11-4): accept the measured times for Step 11, or authorize a narrow
   optimization (options b, c).
2. [owner] Index identity and reproducibility (A11-3), for Step 12.
3. [owner, interpretation] VS-7 "invalid revision request": refused at the boundary (exit 3, nothing created) rather
   than a FAILED investigation (section 3).
4. Carried, not blocking: I-2 (Step 12), I-3 with A-6 (Step 12), I-4 (Step 12), A11-5 (Step 12).
