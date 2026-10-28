# Stage 02 Handoff: Retraction Data Engine

## Stage and status

- Stage: 02, Retraction Data Engine. Executor role: `engineering-agent`,
  filled by a Claude Code session under the owner's Stage 02 Master Execution
  Directive (`cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`), with the
  owner's clarifications `cmsg_018VCB51nDHP6HXmLU4ea5yPSxAcT2gMtmN883uPhy43Ni`
  (model access) and `cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`
  (Stage 00 test-setup fix and CI).
- Registry state: `BLOCKED`, with blockers B-1 and B-2 below. The stage is
  **not verified and not accepted**. No later stage is authorized or started.
- Specification, model and risk analysis frozen at `36696b3`; the changes
  made after freezing are listed in SPECIFICATION.md 16 (items 1 to 23).
- Pull request: unmerged, to `main`; the owner merges (D-019).

## Verified completed work

Each item is covered by the Stage 02 tests, run locally on Python 3.12 and
3.13, and, where it says so, checked on the real pinned snapshot
(TEST_RESULTS.md gives the numbers). The tests have **not** run in CI: CI
stops at the governance check before the test step (B-2).

- **Import and accounting.** Receipt check (size, SHA-256, git blob SHA-1),
  strict CSV, exact line accounting; 73,356 records, all accepted, 0
  quarantined, 173,491 physical lines; types 67,916 retraction, 3,733
  expression of concern, 1,544 correction, 163 reinstatement (equal to the
  accepted Stage 01 profile); 439 records in duplicate groups, all kept.
- **Identity.** Role-aware DOI and PMID normalization with raw value, form,
  transformations and issues; no Unicode folding, single percent decoding of
  URL forms, controls rejected; one-hop PMID bridging only for a unique
  partner; incompatible two-identifier queries are `ambiguous_identity`.
- **Events, dates, projection.** Every event kept; day-1 dates have no
  bounds; chronology is a partial order; the v1 projection follows
  SPECIFICATION.md 11.1 as amended (an ordered concern then retraction is a
  sequence; a reinstatement needs a supersession link; unknown origin alone
  settles nothing).
- **Index and operations.** One SQLite file per snapshot, validated before an
  atomic publish, never replacing a different build; read-only immutable
  readers; `build`, `lookup`, `event`, `tension`, `verify`, `export`, `diff`,
  `enrich`, `ambiguity` in Python and the `citerift-rde` CLI; offline except
  `enrich`.
- **Schemas.** Eight Stage 02 schemas in `schemas/retraction/v1/`, local,
  referencing the accepted v1 definitions by URN, with semantic checks; the
  v1 subject projection validates against the v1 investigation contract.
- **Evidence Tension v0** (CREATIVE_DIFFERENTIATION_REVIEW.md).
- **Bounded corroboration.** Crossref client within the directive's limits,
  pinned replay bundle of 29 works, lineage with origin, channel and known or
  unknown dependence.
- **Evidence Ambiguity Investigator.** Advisory boundary, deterministic
  baseline, frozen protocol and held-out baseline score. The model
  experiment has **not** run (B-1).
- **Reviews.** Three review passes with dispositions (TEST_RESULTS.md 10).
- **Real-data checks** at the cited code revision: independent oracle (0
  mismatches), 50 real cases, eight tension demonstrations, five measured
  builds, double build, benchmarks.

## Inputs and outputs

Inputs:

- Retraction Watch data, `https://gitlab.com/crossref/retraction-watch-data`,
  commit `a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4`, `retraction_watch.csv`,
  68,076,023 bytes, SHA-256
  `2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`
  (packaged receipt `src/citerift/retraction/receipts/`). Not committed.
- Crossref REST API `/works/{doi}`, 29 works on 2026-10-27, pinned in
  `evidence/crossref/`.
- Accepted Stage 01 profile (`docs/verification/stage-01/data/rw_profile.json`),
  used only as a comparison.

Outputs (paths under `docs/verification/stage-02/` unless absolute):

| Output | Path |
|---|---|
| Engine | `src/citerift/retraction/` |
| Schemas | `schemas/retraction/v1/` |
| Tests and fixtures | `tests/stage02/` |
| Prebuild simulator, oracle, frozen cases | `simulations/stage02/` |
| The seven documents | this directory |
| Evidence | `evidence/`, `ai/`, `test-report.json` |
| Recovery ledger | `EXECUTION_LEDGER.md` |

Rebuild from a clean checkout:

```bash
uv sync --locked
mkdir -p data/raw/rw && curl -o data/raw/rw/retraction_watch.csv \
  https://gitlab.com/crossref/retraction-watch-data/-/raw/a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4/retraction_watch.csv
uv run citerift-rde build --source data/raw/rw/retraction_watch.csv --out-dir data/index/rw
uv run citerift-rde build --source data/raw/rw/retraction_watch.csv --out-dir data/index/cr \
  --corroboration docs/verification/stage-02/evidence/crossref/manifest.json
uv run citerift-rde verify --index data/index/rw/rw-2f116e9ffed718e6.sqlite --source data/raw/rw/retraction_watch.csv
uv run citerift-rde lookup --index data/index/rw/rw-2f116e9ffed718e6.sqlite --doi 10.1038/nature16193
```

Digests of the real-data run at the code revision below (equal over five
builds; TEST_RESULTS.md 3):

| Index | Artifact digest | Semantic digest | Export lines |
|---|---|---|---|
| Retraction Watch only | `1ee679b5e5c2e89f06139f43ffd27818b9259dc15693c743ef7bd2ea45e809dc` | `7b2a2344a7f9546d2c684dfef84aa01db9e010fd9c9bf7f9343c93b5b88a5f88` | 147,152 |
| With the pinned Crossref replay | `ea4c1678e1f4fd0a65e56e9202f129f53dd2e3fa2607a9c5002e16782430147d` | `d3daab8ff9697c0a0072a15a4f640728f3fc10dd09acba0d54d8f8987f687e5a` | 147,229 |

Snapshot `rw-2f116e9ffed718e6`, policy `citerift-rde-policy/1.1.0`, Evidence
Tension `citerift-evidence-tension/0.2.0`. A build with another policy version
is refused by readers (`INDEX_FORMAT_MISMATCH`).

## Test evidence

Which evidence came from where:

| Evidence | Source | Result |
|---|---|---|
| Full test suite, Python 3.12.3 | local, cloud container | 2 failed (the Stage 00 tests of B-2), 1034 passed |
| Full test suite, Python 3.13.17 | local, scratch environment from `uv.lock` | 2 failed (the same two), 1034 passed |
| `ruff check`, `ruff format --check`, `mypy`, `uv lock --check` | local | clean |
| `citerift-gov check` | local and CI | 1 error, VERIFICATION_STALE for Stage 00 (B-2) |
| CI workflow, Python 3.12 and 3.13 | GitHub Actions run 83 at `a24dd46` | failed at the governance check; later steps did not run |
| Build, double build, verify, oracle, demonstrations, benchmarks | real-data run, local | as in TEST_RESULTS.md 3 to 8 |
| Complete test report | local, `test-report.json` | written at the documents commit below |

Stage 02 suites: unit 206, integration 114, negative 250, regression 36,
reproducibility 5, security 58, contracts 7, simulation 59 (531 tests).
Fail-first evidence for every review fix: `evidence/fail-first/`.

## Known limitations

- Retraction Watch and a 29-work Crossref replay are the only sources;
  publisher text was not read. `verified_fact` means "established from the
  cited source record", not independent truth.
- A single PMID-bridged event can give `verified_fact` (R-026, owner
  decision).
- Day-1 dates and literal `%` in bare DOIs are handled conservatively (R-023,
  R-024).
- Identity beyond exact identifiers is advisory and not validated on natural
  cases (R-025).
- The simulator, oracle, frozen cases and engine have one author (an AI
  agent); the real cases had no human review (SIMULATION_REPORT.md 5).
- The three reviews are separate passes of the same model, not human or
  organizational review.
- The snapshot has one Arabic-script record; there is no Arabic evaluation
  and no Arabic claim.
- An installed wheel needs the schema-root environment override; a killed
  build can leave a temporary file (never a published one).

## Open blockers

**B-1 (registry `B-02-001`): model experiment (gate 02-G).** No model prediction was made. The
route on the session's agent facility (one group per call with the per-call
token limit amended, ten groups per call, or no run) is the owner's choice
(decision card `cmsg_018VCB51nDHP6HXmLU4ea5yPEBsMCiKEj6WcSf8w6VEepd`; D-023).
Whatever the route, the frozen gate cannot be met on the frozen split (gain at
most 8.3 points, coverage at most 0.508); the gate is not lowered. Smallest
owner action: pick a route, or rule that the experiment is not run, in which
case gate 02-G stays unmet and the result is recorded as a blocker, not as a
negative finding.

**B-2 (registry `B-02-002`): Stage 00 tests and CI (gate 02-I).** CI fails on two Stage 00 tests.
`test_real_repository_passes_governance_check` fails because the
owner-authorized V-03 test-setup fix (`ed8e442`) changes a Stage 00 owned file
with no recorded amendment, and an enhancement amendment needs a passing
complete report at its own revision, which this test prevents; a correction
reopening is refused while Stage 02 is active. `test_application_layers_not_
created_prematurely` fails because it allows only `contracts/` and
`governance/` under `src/citerift/`, and Stage 02 adds `retraction/`. Both
need a Stage 00 route the owner has not chosen (decision card
`cmsg_018VCB51nDHP6HXmLU4ea5yPHaUBWgBzT9es75PZZMJv73`). Nothing in Stage 00 or
in governance code was changed beyond the authorized V-03 fix. Smallest owner
action: pick the route.

## Dependency versions

No runtime dependency was added (D-022). Real-data runs: Python 3.12.3, SQLite
3.45.1, jsonschema 4.26.0, uv 0.11.32, on 4 vCPU and 15 GiB without GPU
(`evidence/environment.json`). Locked versions: `uv.lock`. CI: Python 3.12 and
3.13.

## Verified Git commit

- Code and real-data evidence: `a24dd46c36b74d2a7ba5efd6b48f4606f1d9901e`.
  Every real-data number in these documents was measured with this code.
- Documents, remaining evidence and test report: {{DOCS_COMMIT}}. It changes
  documents and evidence only, no code.
- Branch `claude/project-thread-ddufmg`; the pull request to `main` is
  unmerged.

## Acceptance decision

Not requested. The stage is `BLOCKED`, so it cannot be offered for
acceptance. After B-1 and B-2 are resolved and CI is green on Python 3.12 and
3.13 at a cited revision, the stage can move to `IMPLEMENTED_NOT_VERIFIED`
and then `VERIFIED_AWAITING_OWNER_ACCEPTANCE`. Acceptance and the merge are
the owner's.

## Requirements for the next stage

Interface requirements only; no later stage is authorized.

- Read the index only through `citerift.retraction.query` (`Index`, `lookup`,
  `event`) or the CLI; never open the SQLite file for writing.
- Cite `snapshot_id`, `policy_version` and `evidence_digest` with every
  retraction finding, and keep `lookup_state` separate from the assertion
  status.
- Never turn `no_record` or `notice_only` into "not retracted"; carry
  `uncertain` and its reasons through.
- Treat identity `bridged` and `ambiguous_identity` as unresolved for any
  claim about a Wikipedia citation.
- Advisory suggestions have no path into facts; keep it that way.
