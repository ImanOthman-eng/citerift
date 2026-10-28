# Stage 02 Execution Ledger

Recovery notes for this cloud session (directive §16). Newest entries last.
State is authoritative only in `governance/stage_registry.json`
(`uv run citerift-gov recover`).

## How to resume

```bash
uv sync --locked && uv run citerift-gov recover && uv run citerift-gov check
mkdir -p data/raw/rw && curl -o data/raw/rw/retraction_watch.csv \
  https://gitlab.com/crossref/retraction-watch-data/-/raw/a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4/retraction_watch.csv
sha256sum data/raw/rw/retraction_watch.csv   # 2f116e9f...0a655
```

## Entries

Times are git commit times (UTC). Rows without a commit give the commit
they preceded; their times were not recorded.

| When (UTC) | Commit | State and evidence |
|---|---|---|
| 2026-10-27 20:25 | `1d2c0ba` | AUTHORIZED (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`) and IN_PROGRESS recorded |
| before `36696b3` | — | Snapshot downloaded: 68,076,023 bytes, sha256 and git blob match the receipt |
| before `36696b3` | — | Capability inventory: Python 3.13.17 / 3.12.3 (uv), SQLite 3.45.1, 4 vCPU, 15 GiB, no GPU; GitHub push works; Crossref reachable (rate headers 5/s, concurrency 1); no model API key (owner asked) |
| 2026-10-27 20:40 | `36696b3` | Specification, mathematical model and risk analysis frozen; prebuild simulator and frozen cases (37 policy, 16 tension) pass in the simulator; registry Stage 02 definition refined (owned paths, 8 suites, gates 02-A to 02-I) |
| 2026-10-27 21:04 | `ed8e442` | Owner-authorized V-03 test-setup fix (`cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`): the sandbox sets the empty Stage 02 definition itself. Verified locally (186 passed; mutant check fails the test). Amendment not yet recordable: see Blockers |
| 2026-10-27 21:17 | `e4de42b` | Engine work in progress: ingest, identifiers, dates, store, query, policy, export/verify/diff, tension, corroboration, schemas, CLI. Real build 23.5 s; artifact digest `0eca50b5...`, semantic digest `7b2a2344...`, 147,152 export lines |
| 2026-10-27 21:31 | `fe187b1` | AI evaluation protocol frozen before any prediction (`docs/verification/stage-02/ai/protocol.json`): seed 20261027, 40 tuning / 120 held-out groups, thresholds tau_s 0.85, tau_m 0.10 chosen on tuning only (38/40) |
| 2026-10-27 21:31 | `fea7fa7` | Baseline scored on held-out: 110/120 (0.917, Wilson 0.853 to 0.954); coverage 0.433; maximum attainable gain 8.3 points, below the 10-point gate |
| 2026-10-27 21:35 | `00bb159` | Engine-vs-frozen-case tests and identifier tests (280 pass). PubMed `www` URL form follows SPECIFICATION.md 6.2 (no trailing slash) |
| 2026-10-27 21:38 | `d649f59` | Miss lookups 17 ms → 0.05 ms (quarantine join order); relevance hits capped at 100 with an explicit total |
| 2026-10-27 21:45 | `0f07823` | Import, dates, lookup, export/diff, corroboration-double, advisory-boundary and schema tests |
| 2026-10-27 21:46 | `ec090e2` | Evidence Tension invariants and metamorphic properties over 300 seeded evidence sets |
| 2026-10-27 21:53 | `d99f893` | Independent oracle comparison on the full snapshot: 0 mismatches (112,481 DOI and 63,010 PMID keys, 1,600 absent keys). 49 real cases on a 68-record attributed fixture (selected by script; expected outcomes from the simulator, not human review), 49 agree |
| 2026-10-27 22:01 | `7a7d6b6` | C-9 fixed (SPECIFICATION.md 16 item 9); bounded live Crossref run (29 works, 30 requests, 27 ok, 2 recorded 404s) pinned as a replay bundle |
| 2026-10-27 22:03 | `0dd1c86` | Eight real Evidence Tension demonstrations, four diagnostic classes; CLI ambiguity defaults are the frozen thresholds |
| 2026-10-27 22:08 | `3a6f1eb` | C-10 fixed (item 10); SPECIFICATION.md 16 written; benchmark follows the frozen query mix of SPECIFICATION.md 13 (a provisional run before this commit used a different mix and is discarded) and adds the tension and ambiguity budgets |
| 2026-10-27 22:47 | `aa7c23c` | Three review passes (architecture, security, science; separate passes of the same model, not human review). Fixed with fail-first evidence (`evidence/fail-first/`): items 11 to 22 of SPECIFICATION.md 16. Real policy impact on 96,803 original keys: 313 change (275 reinstated → uncertain, 34 conflicting → retracted, 4 conflicting → uncertain); `evidence/policy-impact-*.json`. Real cases regenerated: 50 cases, 27 classes, 50 agree. Stage 02 tests: 525 + 5 property tests pass |
| 2026-10-28 02:25 | `66e39ed` | Benchmark at `aa7c23c` failed the build memory budget (peak RSS 740 MiB against 512; kept as `evidence/benchmark-at-aa7c23c-failed-rss.json`). Cause: every event held in memory for parallel validation. Fix: serial streaming validation, no worker processes. Re-run: every budget met, digests unchanged (`evidence/benchmark-at-66e39ed.json`) |
| 2026-10-28 02:33 | `cb28ee2` | Policy version 1.1.0 and tension version 0.2.0 for the post-freeze rule changes (SPECIFICATION.md 16 item 23); an index of another policy version is refused. Artifact digest changes, semantic digest unchanged |
| 2026-10-28 02:33 | `a24dd46` | Tension demonstrations report `base_unresolved` and `dependence_unknown`. Final real-data runs at this code revision: five builds (median 71.7 s, peak RSS 405 MiB), oracle 0 mismatches, `verify --source` clean on the RW and Crossref indexes, eight demonstrations regenerated, full suite 1034 passed and the two known Stage 00 failures. CI: red at the governance check (VERIFICATION_STALE, B-2) |
| 2026-10-28 02:58 | `f62a280` | Documents and remaining evidence; local full suite on Python 3.12 and 3.13 (1034 passed, 2 Stage 00 failures). `test-report.json` produced on this commit, clean tree |
| 2026-10-28 03:05 | the commit after `f62a280` | Test report committed; blockers B-02-001 (gate 02-G) and B-02-002 (gate 02-I) recorded with `citerift-gov blocker add`. `transition 02 BLOCKED` refused (pre-existing VERIFICATION_STALE error), so the status stays IN_PROGRESS |
| 2026-10-28 04:25 | — | Owner directive "Corrected open-source AI, blocker recovery and Stage 02 completion" (`cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT`): approves a bounded Stage 00 maintenance mechanism and AI Protocol v2 with a local open model |
| 2026-10-28 05:14 | `8b1db57` | Maintenance mechanism and test corrections (protected patch, 8 Stage 00 owned files); two adversarial review rounds, 10 findings fixed with regressions (`docs/verification/maintenance/A-00-002/`) |
| 2026-10-28 05:14 | `627cc9d` | A-00-002 prepared (`pending_validation`); complete suite on a clean checkout of this revision: Python 3.12.3 and 3.13.17, 1,093 passed each |
| 2026-10-28 05:20 | `4bf0255` | A-00-002 finalized; `check` 0 errors. CI green for the first time with Stage 02 tests: runs 40637490981 (push) and 40637496253 (pull request) |
| 2026-10-28 05:21 | `6d3de07` | AI Protocol v2 part 1 frozen before any model ran: label repair, development audit, holdout quotas, attainability rule, admission rule (`ai/v2/protocol-v2.json`) |
| 2026-10-28 05:25 | `27e3249` | `LocalAmbiguityModel` adapter, hash-pinned CPU inference requirements, development set (296), screening ids (40), manifests for the two candidates |
| 2026-10-28 05:32 | `e591af1` | B-02-002 resolved. CI at this commit red on two Stage 02 checks introduced at `27e3249` (an `eval(` call in `local_model.py` and its import of the advisory boundary module) |
| 2026-10-28 07:25 | `2136943` | Both CI defects fixed. Screening (offline, 40 cases each): mxbai-rerank-base-v2 33/40, Qwen3-Reranker-0.6B 29/40, baseline 34/40; finalist mxbai. Calibration on the other 256: τ_s 9.75, τ_m 2; model 222/256 against baseline 241/256 (recorded before the draw). CLI `--model-dir`. Part 2 frozen (`ai/v2/protocol-v2-frozen.json`) |
| 2026-10-28 07:27 | `9e23c76` | Holdout drawn: 300 groups, separation proven (0 shared events or keys), attainable (26 baseline errors, best-case p 1.5e-8) |
| 2026-10-28 07:39 | `4a0fc19` | One offline holdout run (network namespace without interfaces, index SHA-256 unchanged): 233/300 against 274/300, relative error reduction -1.58, p 1.0; not admitted; every resource limit met (cold init 63.4 s, warm p95 2.67 s, peak RSS 3,266 MiB, 11.5 min) |
| 2026-10-28 07:40 | — | Fresh clone at `4a0fc19`: INFERENCE_GUIDE.md followed (hash-pinned installs, anonymous pinned download, 15 files verified); separate-process CLI runs with an empty environment and no network: three real unresolved events, baseline output unchanged, missing weights give `MODEL_UNAVAILABLE`, index and lookup unchanged. Real index rebuilt at current code: artifact and semantic digests equal to those of `a24dd46` |
| 2026-10-28 | the documents commit | B-02-001 resolved with the v2 disposition; D-024, D-025 (D-023 superseded), R-027 closed, R-028; Stage 02 documents updated |
| 2026-10-28 08:06 | `720a049` | Verified at `15925c9` (registry record and CI runs 40653182012, 40653188197); awaiting owner acceptance |
| 2026-10-28 10:04 | `d1a6ce1` | Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPR1ZTbdzz21fL4gMeJzfxyy` (R-026 correction): stage returned to IN_PROGRESS; the earlier verification stays in the registry history |
| 2026-10-28 10:05 | `a0666b3` | Rule 7f (policy 1.2.0): bridged assertions never support a value or date; Crossref relations reached through a co-occurring DOI are bridged; P33, T05, T06 amended; simulator changed; 17 of 24 new regressions fail on `720a049` (`evidence/fail-first/`) |
| 2026-10-28 10:05 to 10:30 | `a0666b3` | Real data: indexes rebuilt under 1.2.0 (semantic digests unchanged), verify clean, oracle 0 mismatches, 50/50 real cases, tension demonstrations; impact on 96,803 keys: 0 changed on RW only, 22 on the Crossref index (2 verified retractions become uncertain); benchmark of five builds |
| 2026-10-28 | the documents commit | D-026, R-026 closed, R-029; SPECIFICATION.md 16 items 25 and 26; MATHEMATICAL_MODEL.md 9.8; TEST_RESULTS.md 12; earlier verified evidence kept as `evidence/*-at-15925c9.json` |

## Specification changes

Recorded in SPECIFICATION.md 16 (items 1 to 26).

## Remaining work

Owner decisions only: Stage 02 acceptance, the merge of the pull request,
and whether to keep the local model out of the default product (R-028).

## Blockers and open owner decisions

None open. B-02-001 and B-02-002 are resolved in the registry, with their
resolutions. The earlier route questions (decision cards
`cmsg_018VCB51nDHP6HXmLU4ea5yPEBsMCiKEj6WcSf8w6VEepd` and
`cmsg_018VCB51nDHP6HXmLU4ea5yPHaUBWgBzT9es75PZZMJv73`) were answered by the
owner's directive of 2026-10-28.
