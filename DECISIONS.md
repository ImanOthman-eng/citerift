# CITERIFT Engineering Decisions

Persistent Project Memory: architectural and engineering decisions, with the
alternatives considered and why they were accepted or rejected.

Format (checked by `citerift-gov check`): each entry is a `## D-NNN — Title`
heading followed by `- Field: value` lines. `Status` is one of `proposed`,
`pending-owner`, `accepted`, `rejected`, `superseded`. A topic may have at most
one `accepted` decision. A superseded decision names its successor in
`Superseded-by`, and the successor names it in `Supersedes`. Never delete an
entry; supersede it.

## D-001 — Python baseline 3.12, supported range 3.12 to 3.13
- Status: accepted
- Topic: python-version
- Date: 2026-10-25
- Stage: 00
- Supersedes: none
- Evidence: PyPI JSON metadata queried 2026-10-25 (see docs/verification/stage-00/superseded/741476c/SPECIFICATION.md, section "Environment")

`requires-python = ">=3.12,<3.14"`, `.python-version` is 3.12, and CI tests both
3.12 and 3.13.

PyPI metadata on 2026-10-25: numpy 2.5.4 and scipy 1.18.1 require Python 3.12 or
newer; torch 2.14.1 and spacy 3.8.16 ship wheels for cp310 to cp314;
mwparserfromhell 0.7.2 (a likely Stage 03 wikitext parser) ships wheels up to
cp313 only; transformers, sentence-transformers, fastapi and pydantic are pure
Python and require 3.10 or newer.

Alternatives:
- 3.11: rejected. Current numpy and scipy no longer support it, so later stages
  would be pinned to older scientific releases.
- 3.13 only (the container default): rejected as the sole baseline. It works
  today, but 3.12 has the longest track record across ML wheels. 3.13 stays in
  the CI matrix, so moving to it later is a recorded, tested option.
- 3.14: rejected. mwparserfromhell has no cp314 wheel, which would force a
  source build in Stage 03.

Revisit when Stage 06 selects its models.

## D-002 — uv with pyproject.toml and a committed uv.lock
- Status: accepted
- Topic: dependency-management
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

uv was already installed in the CITERIFT environment, resolves a universal lock
across platforms and Python versions, and installs fast in CI. The lock pins
every transitive dependency with hashes, which also feeds `pip-audit
--require-hashes`.

Alternatives: Poetry (installed, but slower, and adds nothing here);
pip with requirements files (no transitive lock without extra tools); conda
(heavier, not needed until a stage proves a binary dependency requires it).

## D-003 — One canonical JSON stage registry; PROJECT_STATUS.md is generated
- Status: accepted
- Topic: canonical-state
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

`governance/stage_registry.json` holds stage definitions, current state,
records and the transition history. It is validated by
`schemas/governance/stage_registry.schema.json`. `PROJECT_STATUS.md` is
rendered from it, and CI fails if the rendered file is stale, so the two can
never disagree.

Alternatives: YAML (needs a parser dependency and has ambiguous typing);
SQLite (binary, not reviewable in a diff); Markdown only (not machine
checkable); separate files per stage (more places for facts to disagree).

## D-004 — Project Orchestrator is a library, a CLI and a CI check
- Status: accepted
- Topic: orchestrator-form
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

No daemon, service, database, agent framework or MCP server. A transition is
allowed only if the edge exists, the actor may take it, and the resulting
registry passes the full consistency check. CI runs the same check on every
push and pull request.

Alternatives: a hosted workflow service (cost, failure points, no benefit at
this scale); GitHub Issues or Projects as state (not versioned with the code,
not testable offline); an agent framework (Prompt 02 section 4 forbids adding
one to simulate teamwork).

## D-005 — Owner decisions are attested, not cryptographically verified
- Status: accepted
- Topic: owner-acceptance-method
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Owner-only transitions (authorize, withdraw, accept, reopen) must be recorded
with actor `owner` and an `owner_ref` that points to the owner's own words (a
project-thread message id or an https URL). The record's `method` is
`attested`. The orchestrator rejects owner transitions that lack a reference
and detects acceptance records that do not match the history, but it cannot
verify what the reference says.

Verified fact (2026-10-25): the engineering agent's GitHub actions run under
the owner's GitHub account (`get_me` returns ImanOthman-eng). GitHub identity
therefore cannot distinguish the owner from the agent. See R-001 and D-006.

## D-006 — Optional cryptographic owner signatures for acceptance
- Status: pending-owner
- Topic: owner-signatures
- Date: 2026-10-25
- Stage: 00

Option: the owner creates an SSH-signed git tag for each acceptance, and the
orchestrator verifies it against an `allowed_signers` file. The agent never
holds the owner's private key, so it could not forge an acceptance.

Recommendation: not required for the hackathon timeline; adopt it only if the
owner wants a technical guarantee rather than a procedural one. Cost: a
one-time key setup on the owner's machine and one signed tag per stage.

Limit found by the independent review of 2026-10-25: an `allowed_signers` file
kept in the repository can be edited by the agent, which could add its own key.
The file must be protected by a required review from an identity the agent does
not hold, or kept outside the repository (RISKS.md R-016).

## D-007 — License for code, documentation and data
- Status: pending-owner
- Topic: license
- Date: 2026-10-25
- Stage: 00

No license file is committed. Until one is, the public repository is "all
rights reserved" by default, and Stage 09 cannot complete.

Recommendation: Apache-2.0 for code (permissive, explicit patent grant,
compatible with the planned stack: jsonschema MIT, FastAPI MIT, React MIT,
Cytoscape.js MIT, Hugging Face transformers Apache-2.0, spaCy MIT, PyTorch
BSD-3-Clause). Alternatives: MIT (simpler, no patent grant), GPL-3.0 (copyleft,
limits reuse by others). Data is a separate question: Wikipedia text is
CC BY-SA 4.0 and needs attribution when quoted; the terms for redistributing
Retraction Watch data must be verified in Stage 02 before any data is
committed. See docs/sources-and-attribution.md.

## D-008 — Contracts in JSON Schema 2020-12 with URN identifiers
- Status: accepted
- Topic: contract-format
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

JSON Schema works from both Python (backend) and JavaScript (frontend), so the
same contract serves Stages 02 to 08. Schema `$id`s are URNs
(`urn:citerift:schema:...`) so no web domain is implied. Timestamps and URLs
are checked with `pattern`, not `format`, because the `jsonschema` library
silently skips `date-time` and `uri` format checks unless optional packages
are installed. Major version is in the path (`schemas/contracts/v1/`); minor
versions must stay backward compatible.

Alternatives: Pydantic models as the source of truth (Python-only, frontend
would need a generated copy); Protocol Buffers or Avro (tooling overhead, poor
fit for evidence documents).

## D-009 — Epistemic status on every factual field
- Status: accepted
- Topic: epistemic-model
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Every factual value is wrapped in an assertion with status `verified_fact`,
`model_inference`, `uncertain`, `unavailable` or `conflicting`, each with
structural rules (facts need provenance and may not carry model confidence;
inferences need a model and a confidence; unavailable has a null value and a
reason; conflicting lists at least two sourced alternatives). There is no
value meaning "not retracted" and no field for "claim is false": absence of a
retraction record is `not_found_in_checked_sources` and must be `uncertain`.

## D-010 — Stage dependency graph encodes technical dependencies only
- Status: accepted
- Topic: stage-dependencies
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

01 depends on nothing (external, independent). 02 and 03 depend on 00 and 01.
04 depends on 02 and 03; then 05, 06, 07, 08, 09 in sequence. The Master Plan's
sequential order beyond that is enforced by the single-active-stage rule and by
the owner's explicit authorization of each stage, not by extra graph edges.
The engineering agent's stages may not overlap; the external Stage 01 is
exempt because it is not executed by the engineering agent.

## D-011 — Branch protection through a repository ruleset
- Status: accepted
- Topic: branch-protection
- Date: 2026-10-25
- Stage: 00

Definition: `.github/rulesets/main-protection.json`. Rules for the default
branch: required status check `ci-gate` pinned to the GitHub Actions app
(integration id 15368, read from this repository's check runs) with
up-to-date branches, pull requests with zero required approvals and merge
commits only, block force pushes, block deletion, no bypass actors.

Zero approvals because a single-owner repository cannot approve its own pull
requests (GitHub returned "Review cannot be requested from pull request author"
on PR #1). Merge commits only because squash or rebase merges would remove the
commits that the registry cites as verified revisions. No bypass because the
agent acts with the owner's account (D-005), so an admin bypass would also let
the agent skip CI. Tradeoff: if CI is broken for reasons outside the code, the
owner cannot merge until it is fixed, but can edit or disable the ruleset as
repository admin at any time.

Status `proposed` until it is active on GitHub. On 2026-10-25 this session's
GitHub proxy refused ruleset writes ("Write access to this GitHub API path is
not permitted through this proxy") and the classic branch protection API
returned 403 "Resource not accessible by integration", so the owner has to
import the file. See docs/verification/stage-00/superseded/741476c/TEST_RESULTS.md.

Accepted 2026-10-25: the owner created the ruleset on GitHub (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPBsct46wZA6iBixZ1ZLXboz`: "The `main-protection`
ruleset has been created and activated successfully on GitHub"). Read back:
ruleset id 25824038, enforcement active, rules and parameters equal to the
file (TEST_RESULTS.md section 7).

## D-012 — Stage-owned paths and drift detection
- Status: accepted
- Topic: owned-paths
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Each stage lists the paths it owns. After verification, any later commit that
touches those paths makes the verification stale unless an amendment records
it: an `enhancement` amendment with a passing test report at its revision
(the stage stays accepted), or a `correction` amendment followed by an owner
reopen. Shared infrastructure (pyproject.toml, uv.lock, CI workflow) is not
owned by any stage; it is protected by CI, which re-runs every stage's tests on
every change.

## D-013 — CI design
- Status: accepted
- Topic: ci
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

One workflow, least-privilege `contents: read`, third-party actions pinned to
full commit SHAs, `persist-credentials: false`, full history checkout (revision
checks need it), uv pinned to 0.11.32, Python 3.12 and 3.13 matrix, and an
aggregating `ci-gate` job used as the single required check. Steps: lockfile
check, locked install, ruff, mypy strict, schema meta-validation, governance
check, status-doc check, pytest with a machine-readable report, pip-audit on
the hashed lock export.

## D-014 — Test suites as markers with a machine-readable report
- Status: accepted
- Topic: test-evidence
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Every test carries at least one suite marker (unit, integration, negative,
regression, reproducibility, security, contracts, simulation); collection fails
otherwise. The plugin `citerift.governance.pytest_report` writes
`citerift.test-report/1` JSON with the git revision, a dirty-tree flag, totals
and per-suite counts. A stage cannot be verified unless the report is at the
verified revision, clean, has no failures, and every required suite passed.

## D-015 — MCP integration not adopted in Stage 00
- Status: accepted
- Topic: mcp
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

Architecture v1.1 makes MCP optional and conditional (Stage 07). No Stage 00
requirement needs it.

## D-016 — Pre-implementation simulation corrected the single-active rule
- Status: accepted
- Topic: single-active-rule
- Date: 2026-10-25
- Stage: 00
- Supersedes: none

The first design applied the one-active-engineering-stage check only to
authorize and reopen. Exhaustive search found a 12-step counterexample in which
VERIFIED -> IN_PROGRESS (rework) re-entered the active set while another stage
was active. The rule now applies to every edge that enters the active set, and
the implementation enforces it as a state invariant. See
docs/verification/stage-00/superseded/741476c/SIMULATION_REPORT.md.

## D-017 — Project identity and founder signature
- Status: accepted
- Topic: project-identity
- Date: 2026-10-25
- Stage: project
- Supersedes: none

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPGk43kowXCxBqhPw9S7z5df`):
the public creator identity is EVE TELOS, IM is a secondary founder monogram,
the professional signature is "EVE TELOS · IM", and the identity standard is
"CITERIFT — Created and Directed by EVE TELOS · IM". The owner's legal name is
not used in public materials; the association with the legitimate owner is the
repository owner account `ImanOthman-eng` (OWNERSHIP.md). The monogram is not
presented as proof of authorship, copyright or trademark. Usage rules:
docs/identity.md.

## D-018 — AI-assistance attribution in commits and pull requests
- Status: accepted
- Topic: ai-attribution
- Date: 2026-10-25
- Stage: project
- Supersedes: none

Owner instruction (same message as D-017): avoid unnecessary AI promotional
signatures and session links, keep truthful authorship and AI-assistance
disclosure, never rewrite history.

Verified facts (2026-10-25, cloud project thread): the environment's git
configuration sets author and committer to the AI agent identity and SSH-signs
each commit (GitHub shows it as verified, account `claude`). Git adds no
trailers by itself: a test commit in a scratch repository carried only the
message given. The `Co-Authored-By` and `Claude-Session` lines and the PR
"Generated with Claude Code" line come from the agent's instructions, which
let the owner's CLAUDE.md or project-memory rules take precedence.

Decision: agent commits keep the environment identity and signature and end
with `Assisted-by: Claude Code (AI coding agent)`; pull requests keep the
environment's requester block and end with a neutral AI-assistance line; no
session links or promotional lines. Mechanisms: CLAUDE.md (read in sessions on
a branch that contains it), project memory (all project threads), and
`.claude/settings.json` `attribution` (read, per the Claude Code
documentation, by single-repository cloud sessions and local CLI sessions, not
by project threads; not verified in a live session of those kinds).

Rejected: rewriting commit authors or trailers (falsifies history); committing
agent work under the owner's identity (misattributes who did the work);
removing disclosure entirely (AI assistance must stay disclosed).

