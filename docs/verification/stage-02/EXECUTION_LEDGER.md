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

| When (UTC) | Commit | State and evidence |
|---|---|---|
| 2026-10-27 20:19 | `1d2c0ba` | AUTHORIZED (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`) and IN_PROGRESS recorded |
| 2026-10-27 20:20 | — | Snapshot downloaded: 68,076,023 bytes, sha256 and git blob match the receipt |
| 2026-10-27 20:30 | — | Capability inventory: Python 3.13.17 / 3.12.3 (uv), SQLite 3.45.1, 4 vCPU, 15 GiB, no GPU; GitHub push works; Crossref reachable (rate headers 5/s, concurrency 1); no model API key (owner asked) |
| 2026-10-27 21:10 | `36696b3` | Specification, mathematical model and risk analysis frozen; prebuild simulator and frozen cases (37 policy, 16 tension) pass in the simulator; registry Stage 02 definition refined (owned paths, 8 suites, gates 02-A to 02-I) |
| 2026-10-27 21:20 | `ed8e442` | Owner-authorized V-03 test-setup fix (`cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`): the sandbox sets the empty Stage 02 definition itself. Verified locally (186 passed; mutant check fails the test). Amendment not yet recordable: see Blockers |
| 2026-10-27 22:00 | `e4de42b` | Engine work in progress: ingest, identifiers, dates, store, query, policy, export/verify/diff, tension, corroboration, schemas, CLI. Real build 23.5 s; index `data/index/tmp1/rw-2f116e9ffed718e6.sqlite` (ignored), artifact digest `0eca50b5...`, semantic digest `7b2a2344...`, 147,152 export lines |
| 2026-10-27 22:40 | `fe187b1` | AI evaluation protocol frozen before any prediction (`docs/verification/stage-02/ai/protocol.json`): seed 20261027, 40 tuning / 120 held-out groups, thresholds tau_s 0.85, tau_m 0.10 chosen on tuning only (38/40) |
| 2026-10-27 22:50 | `fea7fa7` | Baseline scored on held-out: 110/120 (0.917, Wilson 0.853 to 0.954); coverage 0.433; maximum attainable gain 8.3 points, below the 10-point gate |
| 2026-10-27 23:30 | `00bb159` | Engine-vs-frozen-case tests and identifier tests (280 pass). PubMed `www` URL form follows SPECIFICATION.md 6.2 (no trailing slash) |
| 2026-10-27 23:45 | next commit | Miss lookups 17 ms → 0.05 ms (quarantine join order); relevance hits capped at 100 with an explicit total |

## Specification changes to record in SPECIFICATION.md section 16

1. §10.1 tables: `title_token` and `token_df` (ambiguity baseline), no `issue_index`.
2. §11.1 rule 8: `no_record` has no `retraction_date` assertion.
3. §9: fatal replay code `CORROBORATION_INVALID`; works not attempted after a stop are listed.
4. §10.3 step 5: `query_pair` bridging only when `O_d` is non-empty.
5. §11.2: default plan runs `exclude_origin` only with at least two origins (`single_origin` otherwise).
6. §3: the git blob SHA-1 is checked against the receipt.
7. §12.3: draw quotas and strata (16 hard positives exist in the snapshot).
8. §10.3 step 7: at most 100 relevance hits listed, then `RELEVANT_LIST_CAPPED` with the total.

## Remaining work

Remaining §14 tests; real-data evidence (oracle, five builds and
benchmarks, double build, 40 reviewed cases, tension demonstrations, live
Crossref run); documents; three reviews; PR and CI.

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
