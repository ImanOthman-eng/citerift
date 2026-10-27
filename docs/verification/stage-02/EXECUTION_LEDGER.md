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
| 2026-10-27 22:40 (approx., before commit) | review batch, the commit after `3a6f1eb` | Three review passes (architecture, security, science; separate passes of the same model, not human review). Fixed with fail-first evidence (`evidence/fail-first/`): items 11 to 22 of SPECIFICATION.md 16. Real policy impact on 96,803 original keys: 313 change (275 reinstated → uncertain, 34 conflicting → retracted, 4 conflicting → uncertain); `evidence/policy-impact-*.json`. Real cases regenerated: 50 cases, 27 classes, 50 agree. Stage 02 tests: 525 + 5 property tests pass |

## Specification changes

Recorded in SPECIFICATION.md 16 (items 1 to 22).

## Remaining work

Re-run the oracle, tension demonstrations, benchmark and double build at the
final revision; SIMULATION_REPORT, TEST_RESULTS, CREATIVE_DIFFERENTIATION_REVIEW,
HANDOFF and test report; pull request and CI on Python 3.12 and 3.13.

## Blockers and open owner decisions

- Model experiment (gate 02-G): the owner authorized existing session
  facilities (`cmsg_018VCB51nDHP6HXmLU4ea5yPSxAcT2gMtmN883uPhy43Ni`). The
  session Agent route works and is auditable (`ai/route-pilot-2026-10-27.json`),
  but one call costs about 45k tokens against a 4,500-token envelope. The
  owner's choice of route is pending. The frozen baseline leaves at most
  8.3 points of gain, so the 10-point gate cannot be met by any model.
- Stage 00 amendment for the V-03 fix: an enhancement amendment needs a
  passing complete test report at its revision, and the real-repository
  governance test fails until the amendment exists. A reopen is rejected
  while Stage 02 is active. The owner's choice is pending.
