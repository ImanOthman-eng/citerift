# Stage 00 Specification: Engineering Foundation

Authorized by the owner on 2026-10-25 (Prompt 02, project thread message
`cmsg_018VCB51nDHP6HXmLU4ea5yPPJtDk4V58km8PBjZzdYKEV`). Scope: Stage 00 only.
No later stage is authorized by this document or by any Stage 00 result.

## Purpose

Give CITERIFT a foundation in which stage state, owner decisions, evidence and
data contracts are recorded in the repository, checked by code, and recoverable
by a new session that has nothing but a clone. Nothing in Stage 00 touches
Wikipedia, Retraction Watch, Crossref or any model; it builds the controls that
later stages must pass through.

## Components

| Component | Location | Requirement it meets |
|---|---|---|
| Project Orchestrator | `src/citerift/governance/` (`model.py`, `orchestrator.py`, `evidence.py`, `gitutil.py`), CLI `citerift-gov` | 7 states, explicit transitions, owner-only decisions, verification separate from acceptance and from next-stage authorization |
| Persistent Project Memory | `governance/stage_registry.json` (canonical), `schemas/governance/stage_registry.schema.json`, generated `PROJECT_STATUS.md`, `DECISIONS.md`, `RISKS.md`, `CHANGELOG.md`, `src/citerift/governance/memory.py` | one machine-readable state record, structured decision and risk logs, integrity rules, recovery |
| Data contracts v1 | `schemas/contracts/v1/`, `src/citerift/contracts/validate.py`, CLI `citerift-contracts`, fixtures in `tests/stage00/fixtures/contracts/v1/` | versioned contracts with valid and invalid synthetic fixtures |
| Test evidence plugin | `src/citerift/governance/pytest_report.py` | machine-readable test report bound to a git revision |
| Simulation | `simulations/stage00/state_machine_model.py` | pre-implementation model of the governance rules |
| CI | `.github/workflows/ci.yml` | lockfile, lint, types, schemas, governance check, tests on 3.12 and 3.13, dependency audit, `ci-gate` |
| Branch protection definition | `.github/rulesets/main-protection.json` | protection of `main` (active on GitHub as ruleset 25824038) |
| Repository foundation | `README.md`, `.gitignore`, `GOVERNANCE.md`, `CLAUDE.md`, `docs/` | onboarding, standing rules, sources and attribution policy |

## State machine

States: `NOT_STARTED`, `AUTHORIZED`, `IN_PROGRESS`, `BLOCKED`,
`IMPLEMENTED_NOT_VERIFIED`, `VERIFIED_AWAITING_OWNER_ACCEPTANCE`,
`ACCEPTED_CLOSED`. Eleven edges (`citerift-gov transitions`). Four are
owner-only: authorize (NS→AU), withdraw (AU→NS), accept (VA→AC), reopen
(AC→IP, needs a `correction` amendment). Owner transitions require an
`owner_ref` that cites the owner's own words.

A transition is accepted only if (1) the edge exists, (2) the actor may take
it, and (3) the registry that would result passes the full consistency check.
The check is the same one CI runs, so a hand edit and a CLI transition are held
to the same rules.

Verification (IN→VA) requires: every required artifact present and non-trivial
(at least 300 bytes) with its sha256 pinned; a handoff with all required
sections that cites the verified revision; a `citerift.test-report/1` report
at that revision from a clean tree, with no failures and every required suite
passing; every acceptance gate recorded as passed with existing evidence; for
engineering stages a successful CI run on that revision; no open blocker; no
open critical defect in `RISKS.md`.

Acceptance (VA→AC) is owner-only and must cite the verified revision.
Accepting a stage does not authorize its successor: authorization is a
separate owner transition, refused until every dependency is accepted.

## Persistent memory integrity rules

1. The registry validates against its JSON Schema.
2. Replaying `history` from `NOT_STARTED` reproduces every stage's `status`.
3. History sequence numbers are contiguous and timestamps non-decreasing.
4. At most one engineering-agent stage is active (the external Stage 01 is
   exempt, D-010).
5. Stage records (authorization, implementation, verification, acceptance,
   blockers) match the status; a record for a state not reached is an error.
6. Cited revisions exist and are in the history of `HEAD`; a shallow clone is
   reported, not trusted.
7. Pinned evidence hashes match the files; evidence paths must stay inside the
   repository.
8. A commit touching a verified stage's owned paths without an amendment makes
   the verification stale.
9. `DECISIONS.md` has at most one accepted decision per topic and consistent
   supersession links; `RISKS.md` entries have valid fields.
10. `PROJECT_STATUS.md` equals the rendering of the registry.

Recovery: `citerift-gov recover` rebuilds the full state, open items and the
next authorized action from a fresh clone (tested in a separate process).

## Environment

Python baseline 3.12, range `>=3.12,<3.14` (D-001). PyPI JSON metadata queried
2026-10-25: numpy 2.5.4 and scipy 1.18.1 require 3.12 or newer; torch 2.14.1
and spacy 3.8.16 ship cp310 to cp314 wheels; mwparserfromhell 0.7.2 ships wheels
up to cp313; transformers, sentence-transformers, fastapi and pydantic are pure
Python requiring 3.10 or newer. uv 0.11.32 with a committed `uv.lock` (D-002);
`uv sync --locked` refuses to re-resolve. Runtime dependency: jsonschema 4.26.0
(with referencing 0.37.0). Development: pytest 9.1.1, ruff 0.17.2, mypy 2.4.0,
pip-audit 2.10.1.

Container verified 2026-10-25: 4 vCPU, 15 GiB RAM, no GPU, no Docker daemon,
Python 3.12.3 and 3.13.17 available to uv.

## Out of scope

Data acquisition, parsing, NLP models, the web UI, any Wikipedia or Retraction
Watch access, and everything assigned to Stage 01 (external agent). Stage 00
does not predict or assume any Stage 01 finding.

## Open items requiring the owner

- ~~Resolve the GitHub account billing lock (B-00-001).~~ Resolved by the owner
  on 2026-10-25; CI passed at `741476c`.
- ~~Import `.github/rulesets/main-protection.json` (B-00-002, D-011).~~ Done by
  the owner on 2026-10-25; ruleset 25824038 is active and read back.
- License decision (D-007) and optional signed acceptance (D-006).
