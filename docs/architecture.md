# CITERIFT Architecture

Source: Master Plan v1.0 and Architecture Update v1.1 (owner-approved). This
document records how the repository implements that architecture and where
future components will live. Only Stage 00 components exist today.

## Layers

| Layer | Components | Stage | Exists |
|---|---|---|---|
| Project governance | Project Orchestrator, Persistent Project Memory | 00 | yes |
| External integration | Crossref Retraction Watch, Wikimedia APIs, optional MCP | 02, 03, 07 | no |
| Application runtime | Retraction Detection, Wikipedia Extraction, Citation Context, AI Investigation, Cross-Wiki Intelligence, Investigation Workflow Controller | 02 to 07 | no |
| Persistent data | Investigation Memory, evidence records, source provenance, history | 04, 07 | no |
| Presentation | Web app, Knowledge Ripple, Citation Autopsy, Evidence Passport, Timeline | 08 | no |

## Two orchestrators, kept apart

- The **Project Orchestrator** (`src/citerift/governance/`) governs how
  CITERIFT is built: stage states, evidence, owner decisions. It is development
  tooling, run by people, agents and CI.
- The **Investigation Workflow Controller** (Stages 04 and 07) will govern how
  an investigation runs inside the application.

Likewise, **Persistent Project Memory** (registry, DECISIONS.md, RISKS.md,
CHANGELOG.md, verification packages) is separate from **Investigation Memory**
(the application's evidence store). Application code must not import
`citerift.governance`, and governance code must not depend on application
code. The shared vocabulary between application components is the data
contract in `schemas/contracts/`.

## Component boundaries and planned locations

| Component | Planned location | Owner stage | Depends on |
|---|---|---|---|
| Governance | `src/citerift/governance/` | 00 | jsonschema |
| Contracts | `schemas/contracts/`, `src/citerift/contracts/` | 00 (v1), later minor versions | jsonschema |
| Retraction data engine | `src/citerift/retraction/`, `schemas/retraction/v1/` | 02 (built) | contracts |
| Wikipedia extraction | `src/citerift/wiki/` | 03 | contracts |
| Detection and workflow controller | `src/citerift/investigation/` | 04, 07 | retraction, wiki, contracts |
| Citation context | `src/citerift/context/` | 05 | investigation |
| AI investigation | `src/citerift/ai/` | 06 | context |
| Backend API | `src/citerift/api/` | 07 | investigation, ai |
| Frontend | `frontend/` | 08 | API contracts |
| Release and report | `docs/report/` | 09 | everything |

These directories are not created until their stage is authorized, so the
repository holds no placeholder code. Each stage adds its own tests under
`tests/stageNN/` and declares its `owned_paths` in the registry.

Dependency direction is one-way, top to bottom in the table above, which
prevents circular imports. Each stage's new runtime dependencies are added to
`pyproject.toml` in that stage, with the reason recorded in DECISIONS.md.

## Retraction Data Engine (Stage 02)

One SQLite file per pinned snapshot, built into a temporary file, validated
(accounting, integrity, every event against its schema, digests) and
published with `os.replace`; readers open it read-only and immutable. The
modules, in dependency order:

- `source.py`: receipts and strict CSV reading with line accounting.
- `identifiers.py`, `dates.py`: DOI and PMID normalization; temporal evidence
  with justified bounds and a partial order.
- `ingest.py`, `store.py`: dispositions, events, notices, duplicate groups;
  the build.
- `query.py`, `policy.py`: role-aware lookup and the conservative v1
  projection.
- `tension.py`: Evidence Tension interventions on copies of the evidence.
- `corroboration.py`: the bounded Crossref client and the replay bundle.
- `canonical.py`, `schemas.py`: canonical JSON and digests; local schema
  loading and semantic validation.
- `export.py`: canonical export, `verify`, `diff`.
- `search.py`, `ambiguity.py`, `stats.py`, `advisory.py`: title search
  normalization, the deterministic ambiguity baseline, the exact statistics of
  the evaluation protocol, and the advisory boundary; nothing in the engine
  imports `advisory.py`.
- `cli.py`: the `citerift-rde` command.

Lookup, verify, export and tension make no network connection. The
specification is docs/verification/stage-02/SPECIFICATION.md.

## Project Orchestrator

- `model.py`: states, actors, transition table.
- `orchestrator.py`: registry access, consistency check, transition proposal and
  application, blockers, amendments, status rendering, handoff summary,
  recovery report.
- `evidence.py`: artifact hashes, test report checks, handoff completeness.
- `memory.py`: structured DECISIONS.md and RISKS.md parsing and checks.
- `gitutil.py`: read-only git queries (revision existence, ancestry, path history).
- `pytest_report.py`: pytest plugin producing `citerift.test-report/1`.
- `cli.py`: the `citerift-gov` command.

Default operations are read-only. Writes happen only through
`transition --apply`, `blocker` and `amend`, and each write is validated before
it is made and written atomically (temporary file plus rename).

## Error handling conventions

Governance code reports problems as `Finding(code, severity, stage, message)`
with stable upper-case codes, instead of raising, so that every problem in a
registry is reported at once. Contract validation reports
`ContractProblem(code, path, message, keyword)`. Later stages should follow the
same pattern: explicit, enumerable problem codes, never silent fallbacks.

## Environment constraints

- Development containers are ephemeral; everything persistent is committed.
- No GPU and no Docker daemon in the current cloud environment
  (4 vCPU, 15 GiB RAM, verified 2026-10-25).
- Wikimedia returns HTTP 429 to this environment's shared egress; clients must
  honor Retry-After (R-008).
