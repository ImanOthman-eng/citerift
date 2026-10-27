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
| 2026-10-27 21:10 | this commit | Specification, mathematical model and risk analysis frozen; prebuild simulator and frozen cases (37 policy, 16 tension) pass in the simulator; registry Stage 02 definition refined (owned paths, 8 suites, gates 02-A to 02-I) |

## Remaining work

Engine implementation, tension, corroboration, ambiguity baseline and
protocol, tests, real-data evidence, reviews, documents, PR and CI.

## Blockers

- Model experiment (gate 02-G): no authorized model access in this
  environment (D-023). Needs an owner-provided key and spending approval.
