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
- Every file in a verification directory (except files git ignores), the
  stage definition and the policy are pinned by hash; every file a gate cites
  must be pinned and named by a plain path (no `..`, `.` or symbolic link),
  and a URL alone is not pinned; policy values, the CI requirement and
  artifact list of engineering stages, and each stage's executor and
  dependencies are fixed in the registry schema (F-02, F-03, V-02, V-03, S-01,
  X-01, X-07).
- Test reports record how tests were selected, which test files ran and which
  conftest files were loaded; a report is partial when a narrowing option, an
  ini override, another ini file, changed collection settings, a `-p` or
  `PYTEST_PLUGINS` plugin, or a hook that dropped or repeated tests changed the
  run, when a loaded conftest is not committed, or when a test file committed
  under `tests/` did not run (F-07, V-01, X-02, X-03). This makes an honest
  narrowing visible; code running inside the test process can still write a
  false report (R-004). A report path outside the repository or in a new directory
  no longer crashes the plugin (F-14, V-16). `.gitattributes` keeps LF so CRLF
  checkouts do not change evidence hashes, and a nested `.gitattributes` is an
  error (F-12, V-12).
- History replay checks each entry against the transition rules (single
  active stage, dependencies, correction amendment, blockers, including at
  acceptance); a reopened
  dependency is a warning, so a foundation stage can be corrected after a
  dependent was accepted (F-04, F-05, F-11).
- Entry headings that look like entries but do not parse, entry fields outside
  a recognized heading, and entry fields not written as `- Name: value` are
  errors; topics are compared after Unicode, separator and invisible-character
  normalization; a project-wide critical defect blocks every stage (F-06,
  V-06, X-06). An entry written in neither form (for example a table row) is
  still not recognized.
- Unreadable registry reported without a traceback; blocker resolution
  records the real actor; future timestamps refused; records must match their
  history entries and an acceptance must cite a new owner statement (F-13,
  F-15, F-16, F-17).
- `.github/workflows`, `.github/rulesets`, `.gitattributes` and
  `src/citerift/py.typed` (new) are Stage 00 owned paths (F-20 detection,
  F-23).
- Final independent review (V-01 to V-16): besides the items above, an
  acceptance cannot cite an amendment's owner reference (V-07); a correction
  amendment justifies one reopening (V-08); duplicate amendment and blocker
  ids are errors (V-09); unreadable schemas, schema-invalid registries and
  non-UTF-8 memory files are reported without a traceback (V-10); default
  record times never precede recorded times (V-11); git queries ignore replace
  refs (V-13); CI runs the checked-out `src/` modules, not the entry points
  (V-04).
- Second final independent review (X-01 to X-14): besides the items above, CI
  refuses anything in `src/` beside the package before any Python runs, and
  `check` reports it (X-04); unknown stage ids, invalid schemas, non-UTF-8
  status or handoff files, malformed `--record` files, a missing amendment
  test report and wrongly typed report counts give named errors (X-05); a
  blocker resolution defaults to a time after the last entry (X-08); git
  ignores grafts (X-09); `wiki_language` accepts subtags of up to 12
  characters, so `zh-classical` is valid, as part of the unreleased 1.0.1
  (X-11); the repository test checks the authorization rule rather than
  today's state (X-12); an amendment must cite an owner statement not cited
  before, and an enhancement that changes a contract must raise its version
  and keep the accepted valid fixtures valid (X-13); the mutation check runs
  a baseline first and covers the new rules (X-14).
- Third final independent review (Y-01 to Y-13): a report written over a
  tracked file, and tracked files flagged `--skip-worktree` or
  `--assume-unchanged`, make the tree dirty (Y-01, Y-02); skipped and
  expected-to-fail tests make a run partial (Y-03); entry ids and `Stage`
  values need ASCII digits, and Arabic tatweel and short-vowel marks are
  folded in topics (Y-04); in the unreleased 1.0.1, an absence of record is
  never a conflicting alternative, conflicting alternatives must differ, no
  retraction date may stand next to `not_found_in_checked_sources`, and a
  subdivided DOI registrant code is valid (Y-05, Y-12, Y-13); an amendment
  must be recorded while its stage is accepted, only enhancements of the
  current acceptance cover owned changes, and an owner reference cited in the
  same second counts as cited before (Y-06, Y-07); CI runs the governance
  check before ruff, mypy and pytest, checks its own test report with the new
  `check-report` command and fails if a step changed an unstaged tracked file
  (Y-08; see the confirmation review below for the rest); an
  owned file is pinned gate evidence only if committed at the verified
  revision (Y-09); the CI run must belong to the project's repository (Y-10);
  non-UTF-8 evidence names, a damaged index, an absolute `verification_dir`
  and deeply nested JSON give named errors (Y-11). Tests were added for four
  rules the 73-mutant check found untested (M52, M57, M58, M59).
- Confirmation review (Z-01 to Z-05): a tracked file whose bytes differ from
  its index entry makes the tree dirty even when git's stat cache hides the
  edit (Z-01); the CI run URL must match the project's run URL as a whole, so
  `..` segments cannot lead to another repository (Z-02); `recover` says
  uncommitted changes are unknown when git cannot list them (Z-03); CI
  installs only the locked dependencies as wheels before the governance
  check, and builds the project after it (Z-04); a tracked file whose name
  starts with `:` is recognised as tracked (Z-05); the last CI step also fails
  on staged changes and new files. Overstated statements in GOVERNANCE.md,
  RISKS.md and the verification documents were corrected.
- GOVERNANCE.md, RISKS.md (R-001, R-003, R-004, R-012, new R-016, R-017, R-018, R-019, R-020, R-021),
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
