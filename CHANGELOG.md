# Changelog

All notable changes to CITERIFT. Format based on Keep a Changelog. Stage state
and its history live in `governance/stage_registry.json`; this file records
what changed in the repository.

## [Unreleased]

### Fixed (Stage 00 correction A-00-001, owner-authorized reopening)

Findings of the independent review of 2026-10-25
(docs/audits/stage-00-2026-10-25/); each has a regression test that fails on
the reopened revision `ae2ce9e`.

- Contracts 1.0.1: retraction-status alternatives restricted to the accepted
  values and free of model fields; typed title and context alternatives;
  patterns that Python and ECMA-262 read the same way; `date-time` format
  enforced with a standard-library checker; events ordered by instant;
  calendar check for retraction dates; duplicate JSON keys rejected (F-08,
  F-09, F-10, F-18).
- Drift is decided by owned-path content, so a merge restoring old content is
  detected; uncommitted owned-path changes are reported (F-01, F-19).
- Every file in a verification directory, the stage definition and the policy
  are pinned by hash; gate evidence must be a pinned file; policy values and
  the CI requirement are fixed in the registry schema (F-02, F-03).
- Test reports record how tests were selected; partial runs are rejected
  (F-07); a report path outside the repository no longer crashes the plugin
  (F-14); `.gitattributes` keeps LF so CRLF checkouts do not change evidence
  hashes (F-12).
- History replay checks each entry against the transition rules (single
  active stage, dependencies, correction amendment, blockers); a reopened
  dependency is a warning, so a foundation stage can be corrected after a
  dependent was accepted (F-04, F-05, F-11).
- Malformed memory entries are errors; topic comparison ignores case; a
  project-wide critical defect blocks every stage (F-06).
- Unreadable registry reported without a traceback; blocker resolution
  records the real actor; future timestamps refused; records must match their
  history entries and an acceptance must cite a new owner statement (F-13,
  F-15, F-16, F-17).
- `.github/workflows`, `.github/rulesets`, `.gitattributes` and
  `src/citerift/py.typed` (new) are Stage 00 owned paths (F-20 detection,
  F-23).
- GOVERNANCE.md, RISKS.md (R-001, R-003, R-004, R-012, new R-016, R-017),
  DECISIONS.md D-006 and docs/data-contracts.md state what is prevented, what
  is only detected, and what is not enforceable (F-21, F-22).

### Added (project identity and ownership, no Stage 00 change)

- OWNERSHIP.md: owner, decision authority, original contributions,
  AI-assisted engineering disclosure, copyright and license status.
- docs/identity.md: identity standard "CITERIFT — Created and Directed by
  EVE TELOS · IM" and usage rules for later stages (D-017).
- `.github/CODEOWNERS` naming the owner account for every path.
- AI-assistance attribution rule for commits and pull requests in CLAUDE.md
  and `.claude/settings.json` (D-018).
- README founder line and "Ownership and attribution" section; GOVERNANCE.md
  "Project identity and attribution" section; package author
  `EVE TELOS · IM`.

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
