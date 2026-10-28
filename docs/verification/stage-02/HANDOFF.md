# Stage 02 Handoff: Retraction Data Engine

## Stage and status

- Stage: 02, Retraction Data Engine. Executor role: `engineering-agent`,
  filled by a Claude Code session under the owner's Stage 02 Master Execution
  Directive (`cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`), with the
  owner's clarifications `cmsg_018VCB51nDHP6HXmLU4ea5yPSxAcT2gMtmN883uPhy43Ni`
  (model access) and `cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`
  (Stage 00 test-setup fix and CI), and the owner's directive
  `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT` of 2026-10-28
  (Stage 00 maintenance, AI Protocol v2 with a local open model).
- Registry state: see `governance/stage_registry.json` and
  `PROJECT_STATUS.md`. Both blockers (B-02-001, B-02-002) are resolved with
  recorded resolutions. The stage is offered for verification at the revision
  in "Verified Git commit"; it is **not accepted**. No later stage is
  authorized or started.
- Specification, model and risk analysis frozen at `36696b3`; the changes
  made after freezing are listed in SPECIFICATION.md 16 (items 1 to 24).
- Pull request: unmerged, to `main`; the owner merges (D-019).

## Verified completed work

Each item is covered by the Stage 02 tests, run locally on Python 3.12 and
3.13 and in CI on both versions, and, where it says so, checked on the real
pinned snapshot (TEST_RESULTS.md gives the numbers).

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
  baseline, AI Protocol v1 (kept; design infeasible, never run) and AI
  Protocol v2, executed: a local open model
  (mixedbread-ai/mxbai-rerank-base-v2, Apache-2.0, revision
  `3ea9d4dffa7d12a4f366be8e275c349de9fc9865`, float32, 4 CPU threads) behind
  `LocalAmbiguityModel.rank`, the opt-in `citerift-rde ambiguity
  --model-dir`, a fresh 300-group holdout, and one offline run. Result: 233/300
  against the baseline's 274/300; **not admitted**; exclusion from the default
  product recommended (TEST_RESULTS.md 7.2).
- **Stage 00 maintenance A-00-002** (owner-authorized; D-024): the two Stage
  00 tests corrected, no test skipped or weakened, CI green.
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
| Evidence | `evidence/`, `ai/`, `ai/v2/`, `test-report.json` |
| Local model adapter and its manifest | `src/citerift/retraction/local_model.py`, `src/citerift/retraction/model_manifests/` |
| Optional CPU inference requirements | `requirements/inference-cpu.txt` (hash-pinned) |
| Inference guide | `ai/v2/INFERENCE_GUIDE.md` |
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

| Evidence | Source | Result |
|---|---|---|
| Full test suite, Python 3.12 and 3.13 | local and CI | TEST_RESULTS.md 2 and 9 |
| `ruff check`, `ruff format --check`, `mypy`, `uv lock --check` | local and CI | clean |
| `citerift-gov check` | local and CI | 0 errors |
| Real build, double build, verify, oracle, demonstrations, benchmarks | real-data run at `a24dd46` | TEST_RESULTS.md 3 to 8; still applicable: the engine code they exercise is unchanged, and a rebuild at the final code gives the same artifact and semantic digests (`evidence/rebuild-check-2026-10-28.json`) |
| AI Protocol v2 screening, calibration, holdout | local, offline, at `2136943` to `4a0fc19` | TEST_RESULTS.md 7.2 |
| Clean-checkout inference and separate-process CLI | fresh clone at `4a0fc19`, no network, empty environment | `ai/v2/inference/` |
| Complete test report | local, clean tree, `test-report.json` | at the verified revision |

Stage 02 suites: unit 212, integration 115, negative 262, regression 36,
reproducibility 5, security 69, contracts 7, simulation 59 (561 tests). Full
suite: 1,123 passed on Python 3.12.3 and on 3.13.17. Fail-first evidence for
every review fix: `evidence/fail-first/`.

## Known limitations

- Retraction Watch and a 29-work Crossref replay are the only sources;
  publisher text was not read. `verified_fact` means "established from the
  cited source record", not independent truth.
- A single PMID-bridged event can give `verified_fact` (R-026, owner
  decision).
- Day-1 dates and literal `%` in bare DOIs are handled conservatively (R-023,
  R-024).
- Identity beyond exact identifiers is advisory and not validated on natural
  cases (R-025). The local open model was not admitted (R-028): its output must
  not be shown or used by default.
- The local model was tested on Linux x86_64 CPU only. Its scores are ranking
  logits, not probabilities. The model's training code and data are not
  published in full ("open-weight", not a fully open model).
- The simulator, oracle, frozen cases and engine have one author (an AI
  agent); the real cases had no human review (SIMULATION_REPORT.md 5).
- The three reviews are separate passes of the same model, not human or
  organizational review.
- The snapshot has one Arabic-script record; there is no Arabic evaluation
  and no Arabic claim.
- An installed wheel needs the schema-root environment override; a killed
  build can leave a temporary file (never a published one).

## Open blockers

None. History of the two blockers:

- **B-02-001 (gate 02-G), resolved.** The model experiment had not run, and
  v1's gate was infeasible. Resolved by executing AI Protocol v2 with a local
  open model and recording the disposition (evaluated, not admitted).
- **B-02-002 (gate 02-I), resolved.** CI was red on two Stage 00 tests that
  could not be fixed without a governance route. Resolved by the
  owner-authorized maintenance A-00-002 (`8b1db57`, `627cc9d`, `4bf0255`) and
  green CI (TEST_RESULTS.md 9.1).

Protected changes, for the owner's review: `src/citerift/governance/`
(maintenance transaction), `schemas/governance/stage_registry.schema.json`
(`$defs.maintenance`), `tests/stage00/` (the two corrected tests and the
maintenance tests), and GOVERNANCE.md. Nothing in `src/citerift/contracts`,
`schemas/contracts/v1`, `.github/` or Stage 01 evidence changed.

## Dependency versions

No runtime dependency was added to the engine (D-022). The local model uses
a separate, optional, hash-pinned environment (`requirements/inference-cpu.txt`:
torch 2.14.1+cpu, transformers 5.19.0, no CUDA), audited separately. Real-data runs: Python 3.12.3, SQLite
3.45.1, jsonschema 4.26.0, uv 0.11.32, on 4 vCPU and 15 GiB without GPU
(`evidence/environment.json`). Locked versions: `uv.lock`. CI: Python 3.12 and
3.13.

## Verified Git commit

- Engine code and real-data evidence: `a24dd46c36b74d2a7ba5efd6b48f4606f1d9901e`
  (unchanged engine since; rebuild check above).
- Stage 00 maintenance: candidate `8b1db57`, validated
  `627cc9dc73621eff3aebffba3ed340ba94fa61eb`, finalized `4bf0255`.
- Local model code and frozen model: `21369431d3274c9b94e2db1b416232a75f10f4d9`;
  holdout drawn at `9e23c76`; holdout run and evaluation at `4a0fc19`.
- Verified revision: `15925c9aa3d5aa4f51209e5953e02a7c6b15c226` (documents,
  evidence, the B-02-001 resolution and two added tests in
  `tests/stage02/test_rde_local_model.py`; no engine code). Complete test
  report on a clean checkout of it: `test-report.json` (Python 3.12.3, 1,123
  collected, 1,123 passed, exit 0) and
  `evidence/test-report-py3.13-at-15925c9.json` (Python 3.13.17, the same).
  CI at this revision: push run
  https://github.com/ImanOthman-eng/citerift/actions/runs/40653182012 and pull
  request run https://github.com/ImanOthman-eng/citerift/actions/runs/40653188197,
  both successful on Python 3.12 and 3.13.
- The next commit records the verification in the registry, with this
  handoff and the reports; it changes no code. The earlier failing report of
  `f62a280` is kept as `evidence/test-report-at-f62a280.json`.
- Branch `claude/project-thread-ddufmg`; the pull request to `main` is
  unmerged.

## Acceptance decision

Requested from the owner: accept Stage 02 (or not), merge the pull request
(or not), and decide whether the local model stays out of the default
product (recommended: yes, R-028). The agent has done none of these.

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
- Do not enable the local model by default and do not show its ranking as a
  suggestion unless a new protocol with a new fresh holdout admits it (R-028).
  Missing weights must stay an abstention, never a negative finding.
