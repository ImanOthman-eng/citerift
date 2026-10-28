# Stage 02 Handoff: Retraction Data Engine

## Stage and status

- Stage: 02, Retraction Data Engine. Executor role: `engineering-agent`,
  filled by a Claude Code session under the owner's Stage 02 Master Execution
  Directive (`cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`), with the
  owner's clarifications `cmsg_018VCB51nDHP6HXmLU4ea5yPSxAcT2gMtmN883uPhy43Ni`
  (model access) and `cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`
  (Stage 00 test-setup fix and CI), and the owner's directive
  `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT` of 2026-10-28
  (Stage 00 maintenance, AI Protocol v2 with a local open model), and the
  owner's instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPR1ZTbdzz21fL4gMeJzfxyy`
  of 2026-10-28 (scientific correction of R-026; D-026).
- Registry state: see `governance/stage_registry.json` and
  `PROJECT_STATUS.md`. Both blockers (B-02-001, B-02-002) are resolved with
  recorded resolutions. The stage was verified at `15925c9`, returned to
  IN_PROGRESS for the R-026 correction (that verification stays in the
  registry history and in `evidence/*-at-15925c9.json`), and is offered for
  verification again at the revision in "Verified Git commit"; it is **not
  accepted**. No later stage is authorized or started.
- Specification, model and risk analysis frozen at `36696b3`; the changes
  made after freezing are listed in SPECIFICATION.md 16 (items 1 to 26).
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
  settles nothing; since policy 1.2.0, rule 7f, a record reached only through
  an unresolved identifier link supports no value and no date, and a stated
  value must hold whether such links are accepted or rejected).
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
| Retraction Watch only | `22bf1f30482b71ef45c61940d835649bb449892319d21a7e0adc7b53d1ded339` | `7b2a2344a7f9546d2c684dfef84aa01db9e010fd9c9bf7f9343c93b5b88a5f88` | 147,152 |
| With the pinned Crossref replay | `ebb1f873269dbff949673d77f9096e8fcbafb35b9a9ef2ae9c03bc965c136b31` | `d3daab8ff9697c0a0072a15a4f640728f3fc10dd09acba0d54d8f8987f687e5a` | 147,229 |

Snapshot `rw-2f116e9ffed718e6`, policy `citerift-rde-policy/1.2.0`, Evidence
Tension `citerift-evidence-tension/0.3.0`, schemas `1.1.0`. The semantic
digests equal those of policy 1.1.0; the artifact digests differ because they
include the versions. A build with another policy version is refused by
readers (`INDEX_FORMAT_MISMATCH`), so a 1.1.0 index must be rebuilt.

## Test evidence

| Evidence | Source | Result |
|---|---|---|
| Full test suite, Python 3.12 and 3.13 | local and CI | TEST_RESULTS.md 2 and 9 |
| `ruff check`, `ruff format --check`, `mypy`, `uv lock --check` | local and CI | clean |
| `citerift-gov check` | local and CI | 0 errors |
| Real build, double build, verify, oracle, real cases, demonstrations, benchmarks | real-data run at `a0666b3` (engine code of the R-026 correction) | TEST_RESULTS.md 3 to 8 and 12; the earlier runs (`a24dd46`) are kept as `evidence/*-at-15925c9.json` |
| R-026 before/after and real-data impact | `720a049` against `a0666b3`, all 96,803 original keys on both indexes | TEST_RESULTS.md 12 |
| AI Protocol v2 screening, calibration, holdout | local, offline, at `2136943` to `4a0fc19` | TEST_RESULTS.md 7.2 |
| Clean-checkout inference and separate-process CLI | fresh clone at `4a0fc19`, no network, empty environment | `ai/v2/inference/` |
| Complete test report | local, clean tree, `test-report.json` | at the verified revision |

Stage 02 suites: unit 213, integration 115, negative 263, regression 60,
reproducibility 5, security 69, contracts 7, simulation 59 (587 tests). Full
suite: 1,149 passed on Python 3.12.3 and on 3.13.17. Fail-first evidence for
every review fix and for the R-026 correction: `evidence/fail-first/`.

## Known limitations

- Retraction Watch and a 29-work Crossref replay are the only sources;
  publisher text was not read. `verified_fact` means "established from the
  cited source record", not independent truth.
- A record reached only through an unresolved identifier link is withheld,
  not resolved (R-029): a true retraction reachable only that way reads as
  `uncertain` (`BRIDGE_ONLY_SUPPORT`). R-026 itself is closed (D-026).
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
maintenance tests), and GOVERNANCE.md, all from A-00-002. The R-026
correction changed none of them: it touches only Stage 02's owned paths,
its documents, DECISIONS.md, RISKS.md, CHANGELOG.md and the registry
transitions. Nothing in `src/citerift/contracts`, `schemas/contracts/v1`,
`.github/` or Stage 01 evidence changed.

## Dependency versions

No runtime dependency was added to the engine (D-022). The local model uses
a separate, optional, hash-pinned environment (`requirements/inference-cpu.txt`:
torch 2.14.1+cpu, transformers 5.19.0, no CUDA), audited separately. Real-data runs: Python 3.12.3, SQLite
3.45.1, jsonschema 4.26.0, uv 0.11.32, on 4 vCPU and 15 GiB without GPU
(`evidence/environment.json`). Locked versions: `uv.lock`. CI: Python 3.12 and
3.13.

## Verified Git commit

- R-026 correction (owner instruction
  `cmsg_018VCB51nDHP6HXmLU4ea5yPR1ZTbdzz21fL4gMeJzfxyy`, D-026): return to
  IN_PROGRESS at `d1a6ce1`; engine code (rule 7f, policy 1.2.0, tension 0.3.0,
  schema 1.1.0) and tests at `a0666b3`; documents, decision and regenerated
  real-data evidence at the verified revision below. The fail-first run of the
  new regressions against the code of `720a049` is
  `evidence/fail-first/r026-bridge-sufficiency-at-720a049.txt` (17 failed, 7
  passed, the seeded invariant failing at seed 2).
- Verified revision: `21d9f378b19cc01b948767472618a85ae47b1093`. Complete
  test report on a clean checkout of it: `test-report.json` (Python 3.12.3,
  1,149 collected, 1,149 passed, exit 0) and `evidence/test-report-py3.13.json` (Python 3.13.17, the same);
  run logs `evidence/test-run-py3.12-at-21d9f37.log` and
  `evidence/test-run-py3.13-at-21d9f37.log`. CI at this revision: push run
  https://github.com/ImanOthman-eng/citerift/actions/runs/40672514661 and pull
  request run https://github.com/ImanOthman-eng/citerift/actions/runs/40672521827,
  both successful on Python 3.12 and 3.13.
- The next commit records the verification in the registry, with this
  handoff and the reports; it changes no code.
- Earlier verification, kept in the registry history (entries 27 and 28) and
  in `evidence/registry-verification-at-15925c9.json`: verified revision
  `15925c9aa3d5aa4f51209e5953e02a7c6b15c226` (registry commit `720a049`),
  reports `evidence/test-report-py3.12-at-15925c9.json` and
  `evidence/test-report-py3.13-at-15925c9.json` (1,123 passed each), CI push
  run https://github.com/ImanOthman-eng/citerift/actions/runs/40653182012 and
  pull request run https://github.com/ImanOthman-eng/citerift/actions/runs/40653188197.
  Its record is `evidence/verification-record-at-15925c9.json`. Engine code
  and real-data evidence of that verification: `a24dd46`; Stage 00
  maintenance: candidate `8b1db57`, validated `627cc9d`, finalized `4bf0255`;
  local model code and frozen model `2136943`, holdout drawn at `9e23c76`, run
  and evaluated at `4a0fc19`. The earlier failing report of `f62a280` is kept
  as `evidence/test-report-at-f62a280.json`.
- Branch `claude/project-thread-ddufmg`; the pull request to `main` is
  unmerged.

## Acceptance decision

Requested from the owner: accept Stage 02 (or not), merge the pull request
(or not), decide whether the local model stays out of the default product
(recommended: yes, R-028), and confirm or change the reading of "adequate
direct evidence" in D-026 (a bridged record may withhold a conclusion that
it would change, never support one). The agent has done none of these.

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
  claim about a Wikipedia citation. A result with `BRIDGE_ONLY_SUPPORT` or
  `BRIDGED_EVIDENCE_MATERIAL` is unresolved, never "not retracted"; the
  candidate records are in `events` (`linked_via`) and
  `basis.bridged_assertions`.
- Advisory suggestions have no path into facts; keep it that way.
- Do not enable the local model by default and do not show its ranking as a
  suggestion unless a new protocol with a new fresh holdout admits it (R-028).
  Missing weights must stay an abstention, never a negative finding.
