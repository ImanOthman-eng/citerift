# Changelog

All notable changes to CITERIFT. Format based on Keep a Changelog. Stage state
and its history live in `governance/stage_registry.json`; this file records
what changed in the repository.

## [Unreleased]

### Added (Stage 00, Engineering Foundation)

- Project Orchestrator (`src/citerift/governance/`): stage state model with an
  explicit transition table, owner-only decisions, single-active-stage rule,
  dependency checks, evidence checks (artifact hashes, test reports, handoff
  sections, gates, CI record), drift detection on stage-owned paths, blockers,
  amendments, handoff summaries and a `citerift-gov` CLI.
- Persistent Project Memory: canonical `governance/stage_registry.json` with a
  JSON Schema, generated `PROJECT_STATUS.md`, structured `DECISIONS.md` and
  `RISKS.md` with contradiction checks, and `citerift-gov recover`.
- Versioned data contracts v1 (`schemas/contracts/v1/`) with an epistemic
  assertion model, synthetic valid fixtures, 35 mutation-based invalid cases,
  semantic checks and a fixture-based compatibility check.
- Pre-implementation simulation of the governance state machine
  (`simulations/stage00/`).
- Test suite with suite markers and a machine-readable test report plugin.
- GitHub Actions CI (lint, types, schemas, governance check, tests on Python
  3.12 and 3.13, dependency audit) with a single `ci-gate` required check.
- Documentation: README, GOVERNANCE.md, architecture, data contracts, sources
  and attribution policy, development setup, Stage 00 verification package.
- Branch ruleset for `main` (`.github/rulesets/main-protection.json`), created
  on GitHub by the owner on 2026-10-25 as ruleset 25824038 (active, read back).

### Stage 00 closed

- 2026-10-25: Stage 00 verified at `741476c` (all 16 gates) and accepted by
  the owner (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP68JgEArkKAaUCqqYkVsnti`,
  method attested, no signature). The acceptance covers Stage 00 only; it does
  not authorize any later stage, merging PR #1, a license or publication.

### Fixed (Stage 00 final review)

- `registry_version` pattern used `\d`, which Python and JavaScript validators
  interpret differently; now `[0-9]`.
- Every governance and contract finding code is now asserted by at least one
  test (26 codes had none, including `ACCEPTANCE_STALE`, `DEPENDENCY_CYCLE` and
  the history ordering checks).
