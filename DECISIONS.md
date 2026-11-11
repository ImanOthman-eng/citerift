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


## D-019 — Owner acceptance of the Stage 00 trust-boundary residuals
- Status: accepted
- Topic: stage-00-residual-risk-acceptance
- Date: 2026-10-26
- Stage: 00
- Supersedes: none

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`,
2026-10-26, section 2): option A of
docs/verification/stage-00/RISK_DECISION_PACKAGE.md, with additional
safeguards, for R-001, R-002, R-003, R-004 and R-016. In the owner's words,
this is "a conscious, bounded acceptance of documented residual limitations
during active development", and "NOT a declaration that these risks have been
technically eliminated".

Recorded as: the five entries in RISKS.md have `Status: accepted` (a status the
memory schema defines), with their severity unchanged. None of them is fixed.
**Sharing one GitHub account does not technically prevent the agent from
exercising any permission granted to that account**, including merging,
changing the ruleset or editing the workflow; the safeguards below are
procedural.

Safeguards set by the owner (GOVERNANCE.md, "Procedural safeguards"):

1. The agent may develop, test, commit and prepare pull requests.
2. The owner keeps final acceptance and merge authority.
3. The owner personally performs merges to the protected `main` branch.
4. Acceptance references and the actual GitHub CI evidence are reviewed
   before merging.
5. Security-sensitive changes, especially CI workflows and governance
   controls, receive explicit owner review.
6. Independent evidence is retained outside the editable project working tree
   wherever supported.
7. Agent access is reviewed, and revoked when no longer needed after the
   project.
8. Owner-signed acceptance (D-006) and a separate agent identity remain
   documented future enhancements. They are not implemented and are not
   protections in place.

Recommendation carried forward: decide on D-006 before Stage 09. Accepting
these residuals authorizes no stage.


## D-020 — Stage 01 accepted; revised, limited RESCOPE approved
- Status: accepted
- Topic: stage-01-feasibility-scope
- Date: 2026-10-27
- Stage: 01
- Supersedes: none
- Evidence: docs/verification/stage-01/FEASIBILITY_REPORT.md §12 and §16.8; docs/verification/stage-01/HANDOFF.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4bEH9RimJDhvHy8S2ABHcU`,
2026-10-27): Stage 01 is accepted at evidence revision
`85da719ac43fc46170310b225c9190b63a046df8`, and "the revised, limited RESCOPE
recommendation documented in FEASIBILITY_REPORT.md §12 and §16.8" is approved.

In the owner's words, this decision "preserves the full planned CITERIFT
architecture, including Investigation MAESTRO, Investigation Memory, meaningful
evaluated AI, cross-language investigation, Evidence Passport, Citation
Autopsy, Timeline, and Knowledge Ripple."

Constraints set by the owner for later stages:

1. "Edition-level findings must be restricted to the demonstrably covered
   citation population and its documented lower bounds."
2. "Response-timing claims must remain case-specific unless independently
   validated broader historical evidence becomes available."

Recorded as: Stage 01 `ACCEPTED_CLOSED` through `citerift-gov` with this owner
reference. Merging pull request #3 and authorizing Stage 02 remain separate
owner decisions; this decision authorizes no stage.

## D-021 — Standing rule: every stage ships a measured creative contribution
- Status: accepted
- Topic: creative-differentiation-per-stage
- Date: 2026-10-27
- Stage: project
- Supersedes: none
- Evidence: owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ` (Stage 02 Master Execution Directive, section 12)

Owner's standing requirement: every stage contains a practical,
evidence-supported creative contribution that strengthens CITERIFT's own
identity and usefulness. Branding, a renamed standard feature, an unsupported
"first-ever" claim, extra dependencies or decorative documentation do not
count. Each stage's `CREATIVE_DIFFERENTIATION_REVIEW.md` names the user or
scientific problem, the concrete mechanism, the nearest prior art (checked in
primary materials; absence from a reviewed page is not global uniqueness),
the measurable difference, cost and complexity, failure modes, and the test
result that supports or rejects the improvement. Recording this rule
authorizes no stage and changes no governance code. Stage 02 applies it with
Evidence Tension v0 (docs/verification/stage-02/CREATIVE_DIFFERENTIATION_REVIEW.md).

## D-022 — Stage 02 engine stack: standard library csv, hashlib, sqlite3
- Status: accepted
- Topic: retraction-engine-stack
- Date: 2026-10-27
- Stage: 02
- Supersedes: none
- Evidence: docs/verification/stage-02/SPECIFICATION.md §2, §10; docs/verification/stage-02/TEST_RESULTS.md (benchmarks)

The Retraction Data Engine uses the Python standard library (`csv` in strict
mode, `hashlib`, `sqlite3`, `urllib.request`) and the existing `jsonschema`;
no runtime dependency is added. The index is one SQLite file per snapshot,
built into a temporary file and published with `os.replace` after
validation, and opened read-only and immutable by readers.

Alternatives:
- Polars or pandas for parsing: rejected; 73,356 records parse in seconds
  with `csv`, and their CSV readers are lenient about malformed quoting,
  which the engine must reject.
- Pydantic for records: rejected; JSON Schema is already the contract
  language (D-008) and dataclasses cover the internal types.
- RapidFuzz for title matching: rejected for now; the baseline uses an
  inverted token index with IDF cosine, which is bounded and deterministic.
- httpx: rejected; enrichment is at most 80 sequential GET requests.
- DuckDB: rejected; adds a binary dependency for no measured need.

## D-023 — Model access for the Evidence Ambiguity Investigator experiment
- Status: superseded
- Topic: stage-02-ai-model-access
- Date: 2026-10-27
- Stage: 02
- Supersedes: none
- Superseded-by: D-025
- Evidence: docs/verification/stage-02/ai/protocol.json; docs/verification/stage-02/ai/route-pilot-2026-10-27.json; docs/verification/stage-02/HANDOFF.md ("Open blockers")

The directive requires a real model experiment with verified, authorized
access. This environment has no model API key. The owner then ruled
(`cmsg_018VCB51nDHP6HXmLU4ea5yPSxAcT2gMtmN883uPhy43Ni`): no API keys and no
additional paid services; existing session-provided model or agent
facilities may be used where technically supported and permitted. One
synthetic pilot outside the frozen splits showed that the session's agent
facility can run the task and that each call is auditable, but that one call
carries about 45,000 tokens of fixed context against the frozen limit of
4,500 input tokens per call, and that it has no temperature or seed control.
The owner was asked to choose a route (thread message
`cmsg_018VCB51nDHP6HXmLU4ea5yPEBsMCiKEj6WcSf8w6VEepd`): one group per call
with only the token limit amended, ten groups per call, or no run. No choice
has been recorded. Independently of the route, the frozen admission gate
cannot be met on the frozen held-out split: the baseline scores 110/120, so
the largest possible gain is 8.3 points (gate: 10), and with 60 positives and
at most one false selection allowed, coverage is at most 61/120 = 0.508
(gate: 0.60). The gate is not lowered. Until the owner decides, the
boundary, the deterministic baseline and the frozen protocol are delivered
and the experiment is a recorded blocker, not an evaluated negative result.

## D-024 — Stage 00 maintenance transaction for the amendment/report cycle
- Status: accepted
- Topic: stage-00-maintenance-transaction
- Date: 2026-10-28
- Stage: 00
- Supersedes: none
- Evidence: docs/verification/maintenance/A-00-002/MAINTENANCE_MODEL.md; docs/verification/maintenance/A-00-002/review-round-1.md; docs/verification/maintenance/A-00-002/review-round-2.md; governance/stage_registry.json (amendment A-00-002)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT`,
2026-10-28, sections 1 and 3): the owner approved "a narrowly scoped,
two-phase governance maintenance mechanism that resolves the Stage 00
amendment/report circular dependency and the two affected test assumptions,
without redoing Stage 00 or Stage 01", and authorized the limited
protected-path changes it needs. Implemented as an enhancement amendment with
a `maintenance` record (prepare → validate → finalize), anchored to registry
history positions, with no new lifecycle state and no change to the
single-active rule. Executed as A-00-002: candidate `8b1db57`, validated
`627cc9d` (Python 3.12.3 and 3.13.17, 1,093 passed each, clean), finalized
`4bf0255`. The owner's approval covers the mechanism; it is not an acceptance
of Stage 02, and the agent's shared repository authority (R-002, R-016)
remains a documented limitation.

## D-025 — AI Protocol v2: local open model, repaired task, fresh holdout
- Status: accepted
- Topic: stage-02-ai-model-access
- Date: 2026-10-28
- Stage: 02
- Supersedes: D-023
- Evidence: docs/verification/stage-02/ai/v2/PROTOCOL_V2.md; docs/verification/stage-02/ai/v2/protocol-v2.json; docs/verification/stage-02/ai/v2/protocol-v2-frozen.json; docs/verification/stage-02/ai/v2/MODEL_SELECTION.md; docs/verification/stage-02/ai/v2/holdout-result.json; docs/verification/stage-02/ai/v2/holdout-disposition.json

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT`,
2026-10-28, sections 1, 4 and 5): the product AI must be a freely
obtainable, permissively licensed, self-hosted model run by open-source
software, with no paid provider, API key, subscription or hosted endpoint;
the session-agent route of D-023 is superseded. Protocol v1 is kept unchanged
and classified "admission design infeasible; no model evaluation executed
under it". Protocol v2 repairs the labels, uses a fresh lineage-separated
holdout of 300 groups (oversampled by a retrieval-feature rule, preregistered
for feasibility), and the owner's relative-error admission rule.

Executed: two open rerankers screened on the same 40 development cases;
finalist mixedbread-ai/mxbai-rerank-base-v2 (Apache-2.0, revision
`3ea9d4dffa7d12a4f366be8e275c349de9fc9865`, float32 on 4 CPU threads),
wrapper calibrated on 256 other development cases and frozen at `2136943`;
holdout drawn at `9e23c76` (separated, attainable: 26 baseline errors); one
offline run (`4a0fc19`). Result: 233/300 correct against the baseline's
274/300; relative error reduction -1.58 (bootstrap 95% -2.95 to -0.79),
b = 54, c = 13, one-sided p = 1.0; negative false selections 36 against 26;
positive recall 0.79; zero critical confusions and zero fact writes; every
resource limit met. Not admitted. Recommendation for the owner: keep the
adapter and the opt-in CLI option, exclude the model from the default product;
the deterministic baseline stays the ambiguity decision. The owner approved
the route and the protocol; the admission recommendation and Stage 02
acceptance are still the owner's decisions.

Owner decision of 2026-10-28 on the admission recommendation: the evaluated
model is excluded from the default product (D-028).

## D-026 — Bridged identifiers do not by themselves establish a status or a date
- Status: accepted
- Topic: stage-02-bridge-sufficiency
- Date: 2026-10-28
- Stage: 02
- Supersedes: none
- Evidence: docs/verification/stage-02/SPECIFICATION.md (11.1 rule 7f; 16 items 25 and 26); docs/verification/stage-02/MATHEMATICAL_MODEL.md (9.8); simulations/stage02/cases/post_freeze_amendments.json (P33, T05, T06); docs/verification/stage-02/evidence/fail-first/r026-bridge-sufficiency-at-720a049.txt; docs/verification/stage-02/evidence/policy-impact-r026-rw.json; docs/verification/stage-02/evidence/policy-impact-r026-cr.json

Owner instruction (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPR1ZTbdzz21fL4gMeJzfxyy`,
2026-10-28): perform a narrowly scoped Stage 02 scientific correction for
R-026. Unresolved identifier bridges must not, by themselves, establish a
verified retraction status or date for the queried subject; sufficiency is
determined from the supporting evidence, not from the aggregate identity
flag, and adequate direct evidence keeps its conclusion beside bridged
events. Source assertions, provenance, candidate relationships and
uncertainty reasons are preserved. The AI Protocol v2 experiment and its
negative result are kept; the rejected model stays disabled by default.

Implemented as policy 1.2.0, rule 7f. The projection is that of the direct
assertions, stated as a verified fact only when accepting the bridges would
not change it (the stated value holds whether the bridges are rejected or
accepted). Frozen cases P33, T05 and T06 are amended with their frozen values
kept. Interpretation chosen by the engineering agent, open to the owner's
review: a bridged record may withhold a conclusion (when it would change the
value or the verified date) but never supports one. Stage 02 acceptance stays
the owner's decision.

Status corrected on 2026-10-28 from "accepted" to "pending-owner": the owner
gave the instruction, but has not yet confirmed the decision as implemented
and the interpretation above; the owner will decide after seeing the result
of D-027. No owner approval is recorded here.

Approved by the owner on 2026-10-28 (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`, item 2, recorded in
D-028): "unresolved bridged assertions cannot support a verified
subject-level status or date. Material bridged evidence may withhold the
affected conclusion. Source records and provenance remain preserved." The
interpretation above is confirmed as implemented (policy 1.3.0, which keeps
rule 7f). The status history of this entry is kept above.

## D-027 — Fix the independent audit's Stage 02 findings F1 and F3 before acceptance
- Status: accepted
- Topic: stage-02-audit-fixes
- Date: 2026-10-28
- Stage: 02
- Supersedes: none
- Evidence: docs/verification/stage-02/SPECIFICATION.md (10.3 steps 4 and 9; 16 items 27 to 29); docs/verification/stage-02/MATHEMATICAL_MODEL.md (9.9); docs/verification/stage-02/evidence/fail-first/audit-f1-f3-at-ac959c6.txt; docs/verification/stage-02/evidence/policy-impact-audit-rw.json; docs/verification/stage-02/evidence/policy-impact-audit-cr.json; docs/verification/stage-02/evidence/pubmed-esummary-audit-2026-10-28.json

Owner authorization (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPTuLwB5wxxfxy8sGptetSkX`, 2026-10-28, in
Arabic: "اوك نفذ التحسينات فقط ورد عليا عشان اعطي الموافقه", "OK, carry out
the improvements only and reply to me so that I give my approval"). The
improvements are those the independent Stage 02 audit of 2026-10-28 assigns to
Stage 02: F1, a PMID-only lookup that ignored records of its DOI under a
different PMID (R-030), and F3, the PMID role collision, reported as an issue
only (R-031). The audit's other recommendations (a PubMed identity source,
Stage 03 scope, the license decision, the documentation format) are not in
this scope and were not started.

Implemented as policy 1.3.0: a single-PMID query bridges every other record
of its co-occurring DOI and reports `IDENTITY_SECONDARY_DIVERGENT`, and rule
7f decides; listed events whose original PMID equals their notice PMID give
`PMID_ROLE_COLLISION`. D-026 stays pending the owner, and Stage 02 acceptance
stays the owner's decision.

## D-028 — Stage 02 accepted; local model excluded from the default product
- Status: accepted
- Topic: stage-02-acceptance
- Date: 2026-10-28
- Stage: 02
- Supersedes: none
- Evidence: docs/verification/stage-02/HANDOFF.md; docs/verification/stage-02/verification-record.json; docs/verification/stage-02/ai/v2/holdout-result.json; docs/verification/stage-02/ai/v2/holdout-disposition.json

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`,
2026-10-28): Stage 02 (Retraction Data Engine) is accepted, verified at
`cf060834afedfa4a82712ca247ad2fc2b2fa9665`. The acceptance covers the
reviewed implementation recorded at pull request #4 head
`f9592b171e6faf6c6eef4e015ef20ee9e9762a6c`, and "does not cover subsequent
unreviewed implementation changes". The owner confirms:

1. "Acceptance of the completed engine, Evidence Tension, and the R-026, F1
   and F3 corrections."
2. "Approval of D-026: unresolved bridged assertions cannot support a
   verified subject-level status or date. Material bridged evidence may
   withhold the affected conclusion. Source records and provenance remain
   preserved." (D-026 is now accepted.)
3. "Exclusion of the evaluated local model from the default product. Preserve
   its negative evaluation and experimental evidence." The model is
   mixedbread-ai/mxbai-rerank-base-v2 under AI Protocol v2 (D-025; 233/300
   against the baseline's 274/300). The adapter and the opt-in
   `citerift-rde ambiguity --model-dir` option stay as they are, off by
   default; the deterministic baseline stays the ambiguity decision. The
   protocol, holdout, run outputs and disposition under
   `docs/verification/stage-02/ai/` are kept unchanged (R-028 accepted).
4. "Acknowledgement of the documented residual limitations, including R-029
   and R-031. These remain unresolved limitations, not completed identity
   resolution. Downstream stages must preserve uncertainty and
   PMID_ROLE_COLLISION restrictions." (R-029 and R-031 record the
   acknowledgment and stay open, since they are not resolved.)

The owner also asked that the review's complexity-documentation and
experimental inference-timeout observations be recorded as follow-up items
without expanding the implementation during closure: R-032 and R-033.

Recorded as: Stage 02 `ACCEPTED_CLOSED` through `citerift-gov` with this
owner reference. Merging pull request #4 is the owner's ("I will merge it").
This decision authorizes no stage; Stage 03 is not authorized or started.

## D-029 — Stage 03 extraction stack and render source
- Status: accepted
- Topic: stage-03-extraction-stack
- Date: 2026-10-28
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/calibration/CALIBRATION_REPORT.md; docs/verification/stage-03/calibration/parser_qualification.json; docs/verification/stage-03/calibration/profile-v1.provenance.json

Delegated engineering decision under the owner's Stage 03 directive
(`cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`, sections 6 and 7), taken
from development measurements; it is not an owner approval of any outcome.
Source wikitext is parsed with mwparserfromhell 0.7.2 and rendered HTML with
lxml 6.1.3 (selectolax 1.0.2 was qualified as a challenger and not adopted;
wikitextparser and Playwright are not used). The render is the Core REST
Parsoid HTML of the pinned revision (HTML 2.8.0, with `data-mw`, revision and
page identity checked), not the Action API parse output, which lacks most of
the structure the reconciliation needs. Extraction runs in a child process
with a 30 s wall limit and a 1024 MiB address-space limit (raised from the
initial 512 MiB after a synthetic page at the declared size limits peaked at
455 MiB). Live requests pass a host-wide lock so that one request is in
flight across processes, with at least 10 s between requests.

## D-030 — Stage 03 frozen evaluation protocol and refined gates
- Status: accepted
- Topic: stage-03-evaluation-protocol
- Date: 2026-10-28
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/protocol/FROZEN_PROTOCOL.md; docs/verification/stage-03/protocol/ANNOTATION_GUIDE.md; docs/verification/stage-03/protocol/scripts/evaluate.py; governance/stage_registry.json (Stage 03 gates 03-A to 03-K)

Delegated engineering decision under the owner's Stage 03 directive (section
6, step D): the support matrix, splits, annotation protocol, matching rules,
metrics, per-language gates, minimum denominators, baselines and budgets are
frozen before any holdout article is selected or any holdout prediction
exists. Gate 03-A keeps the Master Plan wording; 03-B to 03-K refine it
(directive section 20). The protocol is the executor's; its outcomes remain
for the owner to accept or reject.

## D-031 — Stage 03 supplemental correction batch and one fresh final confirmation campaign
- Status: accepted
- Topic: stage-03-supplemental-correction-and-final-confirmation
- Date: 2026-10-29
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-29_SUPPLEMENT.md; docs/verification/stage-03/protocol/AMENDMENT_2026-10-29.md

Owner instruction (owner directive delivered in the Stage 03 cloud session on
2026-10-29; no platform message id is exposed to that session, so the
reference is the retained text at
docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-29_SUPPLEMENT.md):
Stage 03 only. The executor repairs the independently reproduced defects F1-F4
(warning words broken by inline markup or comments, discarded ordinary
red-link labels, hidden ancestors ignored, explicitly numbered reuse arguments
dropped) and other material in-scope defects, then runs one additional
correction batch followed by one fresh final confirmation campaign. This
satisfies FROZEN_PROTOCOL.md section 9's requirement to bring further rounds
to the owner, for this cycle only. Metric definitions, per-language
thresholds, minimum denominators and failure accounting stay as frozen; old
selections, locks, annotations, predictions, scores and adjudications stay
published; the additive amendment is dated and recorded before use. Network
ceilings for the added campaign: 500 HTTP attempts and 300 MiB accepted
bodies; export at most 1 GiB. The directive does not accept the stage,
authorize Stage 04 or merging, or permit unlimited tuning cycles.

## D-032 — Stage 03 executor handoff and verifier corrections
- Status: accepted
- Topic: stage-03-executor-handoff-verifier-corrections
- Date: 2026-10-30
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-30_HANDOFF.md

Owner-delivered authorization in the current ChatGPT/Codex conversation, retained by document reference because
no platform message ID is exposed. Continue the existing branch and PR #5; correct V1/RF-56 and V2/RF-57 before
freezing the final candidate, preserve D-031 and the one-campaign amendment, and complete verification/delivery.
This is execution authority, not acceptance. The actual new assistant is ChatGPT/Codex; new attribution uses
`Assisted-by: ChatGPT/Codex (AI coding agent)` rather than falsely naming Claude. Historical attribution stays.
The owner retains acceptance and personal merge authority; no later stage or additional campaign is authorized.

## D-033 — Stage 03 final recovery, adjudication, correction and handoff
- Status: accepted
- Topic: stage-03-final-recovery-adjudication-handoff
- Date: 2026-11-02
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-02_RECOVERY.md; docs/verification/stage-03/evaluation/final/adjudication/README.md

Owner instruction in the CITERIFT project thread (`cmsg_018VCB51nDHP6HXmLU4ea5yPAsujY49DkUw92HiR1mG4Ya`,
2026-11-02T12:25:19Z): recover PR #5, complete the already-authorized adjudication of the final campaign, correct
independently confirmed in-scope defects as labelled post-exposure repairs, verify, complete the deliverables and
update PR #5 for owner review. The executor for this work is Claude Code; new commits carry
`Assisted-by: Claude Code (AI coding agent)`, and earlier ChatGPT/Codex attribution stays. The instruction keeps
every frozen threshold, denominator and the one-campaign limit; it authorizes no new evaluation campaign, no
acceptance, no merge and no later stage, and it reserves to the owner any decision about an unmet scientific gate.

## D-034 — Stage 03 corrective engineering and one prospective confirmation campaign
- Status: accepted
- Topic: stage-03-prospective-confirmation-campaign
- Date: 2026-11-02
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-02_CONFIRMATION.md; docs/verification/stage-03/evaluation/final/DECISION_RECORD.md

Owner instruction in the CITERIFT project (`cmsg_018VCB51nDHP6HXmLU4ea5yP8BNaHtTfgxhSrEp6pbWPHh`,
2026-11-02T15:37:19Z), answering the decision record of D-033 with outcome C plus engineering work: resolve the
short-footnote definition/use semantics prospectively (original guide kept unchanged), verify RF-60 and audit the
remaining DOI/PMID boundaries, audit Retry-After and resumption after deferral, run one independent adversarial
review (and one focused follow-up), and then run exactly one pre-registered prospective confirmation campaign on
unexposed articles with a frozen candidate, within 500 HTTP attempts and 300 MiB of accepted bodies, plus a separate
positive retraction-warning challenge. G1-G11, their thresholds and the per-language minimum denominators (50
identifiers, 80 uses, 60 definitions, 60 linkable uses) stay unchanged. The final campaign of D-031 stays published
as a failed historical result. The instruction authorizes no acceptance, no merge and no later stage, and no
further campaign after this one.

## D-035 — Stage 03 G5c semantic correction and one further prospective confirmation
- Status: accepted
- Topic: stage-03-g5c-correction-and-confirmation
- Date: 2026-11-03
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-03_G5C.md; docs/verification/stage-03/evaluation/confirmation-2026-11/DECISION_RECORD.md

Owner instruction in the CITERIFT project (`cmsg_018VCB51nDHP6HXmLU4ea5yPBxa7nEyAiE3VN5Lw442e8F`,
2026-11-03T05:53:24Z), answering the decision record of the D-034 campaign. The owner rejects outcome A (no narrowing,
no waiver of G5c) and orders a correction of the citation-unit semantics at the model level: the absence of a
recognized citation template is not evidence of an unstructured bibliographic citation. The work comprises
fail-first reproduction of the 19 English false positives, the smallest correct semantic fix, differential checks on
the retained bundles, an independent adversarial review, and exactly one further bounded, pre-registered prospective
confirmation of the corrected candidate on unexposed articles (500 HTTP attempts and 300 MiB of accepted bodies,
G1-G11 thresholds and minimum denominators unchanged), followed by full release verification. The D-031 and D-034
campaigns stay published unchanged as historical results. The instruction authorizes no acceptance, no merge, no
later stage and no further campaign after this one.

## D-036 — Stage 03 R-038 correction, pre-validation review and one final prospective confirmation
- Status: accepted
- Topic: stage-03-r038-correction-and-final-confirmation
- Date: 2026-11-04
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-04_R038.md; docs/verification/stage-03/evaluation/confirmation-d035/DECISION_RECORD.md

Owner instruction in the CITERIFT project (`cmsg_018VCB51nDHP6HXmLU4ea5yPJGcnAZCAku5nJRxTZzFaL7`,
2026-11-04T02:20:42Z), answering the decision record of the D-035 campaign. The owner orders a fail-first, evidence-based
correction of R-038 (repeated reference names inside one template's output), a full adversarial pre-validation
review of the Stage 03 flow with correction of every confirmed material defect, differential regression on every
retained bundle, an independent engineering readiness gate with a focused re-review, and then exactly one further
bounded, pre-registered prospective bilingual confirmation of the frozen corrected candidate on unexposed articles
(500 HTTP attempts and 300 MiB of accepted bodies; G1-G11 thresholds and minimum denominators unchanged; G5c not
excluded, G6b not exempted). It also orders a security review of the withheld presigned-URL files and a
nondestructive clean merge path where possible. The D-031, D-034 and D-035 campaigns stay published unchanged. The
instruction authorizes no acceptance, no merge, no force push or history rewrite, no later stage and no further
campaign after this one.

## D-037 — Prospective OpenAI-model substitution for unfinished D-036 work
- Status: accepted
- Topic: stage-03-d036-prospective-model-substitution
- Date: 2026-11-04
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-04_D037.md; docs/verification/stage-03/protocol/AMENDMENT_2026-11-04_D037_MODELS.md; docs/verification/stage-03/continuation/d037-2026-11-04/CAPABILITY_REPORT.md

The owner's current instruction, titled "CITERIFT — STAGE 03 FINAL COMPLETION UNDER OWNER-AUTHORIZED D-037",
explicitly authorizes isolated OpenAI-model evaluators/adjudicators for unfinished D-036 work while Claude is
unavailable. No platform message identifier was exposed; the retained exact instruction is the authority reference.
It was received after checkpoint 7646fe7, not before the original freeze. This changes only the evaluator/adjudicator
model requirement and minimum necessary provenance procedures; the candidate, source/schema trees, initial 40 locked
labels, sample/order, all G1–G11 thresholds, minimum denominators, ceilings and stopping rules remain unchanged.
This is an amended mixed-model D-036 campaign, not an unchanged replication or another campaign. Exact requested
identifiers and the lack of attested serving snapshots are disclosed in the amendment. No scientific replacement
was launched: hosted subagents lack enforceable per-instance access controls/native transcript export, while the
native CLI authentication probe failed before completion. The authorization is accepted; experimental execution
remains blocked until genuine isolation, model metadata and durable raw provenance can be established. No labels,
locks, predictions or scores are invented. No acceptance, merge, history rewrite or Stage 04 is authorized.

## D-038 — Stage 03 D-036 resumed under its original model roles (D-037 not exercised)
- Status: accepted
- Topic: stage-03-d036-resumption-original-models
- Date: 2026-11-09
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-11-09_RESUME_D036.md

Owner instruction in the CITERIFT project (`cmsg_018VCB51nDHP6HXmLU4ea5yPKQJiBv5w48TqZw8UJbfJvw`,
2026-11-09T12:57:41Z), after the executor's read-only audit of the state left on 2026-11-04. The owner orders the
D-036 campaign to resume from its reserve1 evaluator checkpoint under the original, prospectively registered model
roles (Claude Sonnet evaluators, Claude Haiku adjudicators, Claude Opus executor) and states that D-037 is not
exercised for this continuation. D-037 and the Codex continuation records (`7646fe7`, `de66152`) stay in the history
unchanged; no OpenAI-model label, adjudication, prediction or score exists. Blocker B-03-001 is resolved through
`citerift-gov blocker resolve` only after a Claude Sonnet evaluator has actually run with a retained transcript. All
G1-G11 thresholds, minimum denominators, ceilings (500 HTTP attempts, 300 MiB), the acquisition end
(2026-11-14 23:59 UTC) and stopping rules stay as frozen. The instruction authorizes completion of D-036 to
`VERIFIED_AWAITING_OWNER_ACCEPTANCE` if every requirement passes; it authorizes no acceptance, no merge, no force
push or history rewrite, no post-prediction repair or further campaign, and no Stage 04.

## D-039 — Stage 03 maintenance A-03-001: fail-closed accepted-contract test
- Status: accepted
- Topic: stage-03-maintenance-contract-test-baseline
- Date: 2026-11-09
- Stage: 03
- Supersedes: none
- Evidence: docs/verification/maintenance/A-03-001/MAINTENANCE_RECORD.md; docs/verification/maintenance/A-03-001/fail_first_demo.sh; docs/verification/maintenance/A-03-001/fail_first_demo.log

Owner decision D-2 on the Stage 04 Master Execution Package (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPRpb2tWYwbQwCYA5ps9aLth`, 2026-11-09T21:25:03Z): the owner authorizes a Stage 03
maintenance transaction (D-024 mechanism) for
`tests/stage03/test_wiki_properties.py::test_accepted_contract_schemas_are_untouched`. The test compared the
contract schemas with `c3346d1`, reachable only through unmerged side branches, and skipped when that commit could
not be resolved (fail-open). The owner requires the full Stage 00 accepted SHA
`0c21182e5871f772c3a76c75a1217c7641a63bbb` as baseline, failure (not a skip) when the baseline cannot be resolved,
drift still a failure, success in a clean clone holding only the main/Stage 04 history, a fail-first demonstration,
the minimum Stage 03 owned change, complete maintenance validation, no change to the contract schemas and no branch
deletion. Recorded as amendment A-03-001. Stage 03 stays `ACCEPTED_CLOSED`; its acceptance is not rewritten. Branch
cleanup of PR #5 and the Codex branch is a separate owner decision.

## D-040 — Stage 04 plan accepted with conditions: owner decisions D-1 to D-5 and the identity-conflict requirement
- Status: accepted
- Topic: stage-04-master-execution-plan-decisions
- Date: 2026-11-09
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/planning/STAGE04_MASTER_EXECUTION_PACKAGE.md; docs/verification/stage-04/planning/STAGE04_MASTER_EXECUTION_PACKAGE_AS_REVIEWED.md; docs/verification/stage-04/planning/PLANNING_RECORD.md; docs/verification/stage-04/planning/registry-definition/REGISTRY_DEFINITION_RECORD.md

Owner decision on the Stage 04 Master Execution Package (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPRpb2tWYwbQwCYA5ps9aLth`, 2026-11-09T21:25:03Z): PROCEED WITH CONDITIONS; no
functional Stage 04 implementation before the conditions are recorded and the package is retained in the repository.
D-1: one controlled manual edit of the Stage 04 registry definition only (owned paths, test suites, gates 04-B to
04-J), because citerift-gov has no command for it; authorization, status, history, accepted revisions, Stage 00-03
definitions and Stage 05+ are not touched; diff, collision proof, schema validation, check, renderer and full matrix
before committing. D-2: Stage 03 maintenance with a fail-closed test (D-039, A-03-001). D-3: two independent blinded
Claude Sonnet annotators per item, labels locked before predictions, a third blinded Sonnet adjudicator, retained
evidence and model metadata; Haiku auxiliary only; disclosed as AI-generated single-vendor labels, not human gold.
D-4: the investigation root is an immutable article revision (wiki, page, revision, capture identity where
applicable), never title text alone; units are children; the subject model stays extensible. D-5: 30 primary and 10
predetermined reserve articles per language within 200 acquisition attempts as the minimum acquisition plan, with a
pre-registered sampling procedure, strata, replacement rules, positive, negative and identity-conflict denominators,
metrics, interval method and failure criteria; expansion instead of weaker denominators; no prevalence claim; the 16
planning-exposed articles are design, regression, adversarial and integration data only. Inherited requirement: when
the DOI and PMID of one citation resolve to incompatible works, Stage 04 enters an explicit identity-conflict state,
emits no positive or negative detection from the pair, keeps both identities with provenance, routes the case to
needs-resolution and preserves it on replay, at the Stage 04 boundary without changing Stages 02 or 03 to hide it.
No Stage 05 work and no claim that Stage 04 is implemented or verified.

## D-041 — Stage 04 Step 3 findings decided by the owner: F-01, F-11 (with condition), F-15, F-16
- Status: accepted
- Topic: stage-04-step3-findings-decisions
- Date: 2026-11-10
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step4/STEP4_OWNER_DECISIONS.md; docs/verification/stage-04/review/step3/STEP3_ADVERSARIAL_REVIEW.md

Owner decisions on the open Step 3 decision points (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPFigUhaer7vUNd5ng3Rh6qw`, 2026-11-10T09:48:45Z, which also accepted Step 3 at
`fb39ede` and authorized Step 4 only). F-01 APPROVED: the 2026-11-10 per-citation precedence (identity contradiction >
unresolved evidence > operational lookup failure > positive finding > notice / not-found outcome) replaces the plan's
draft; investigation-level preconditions may end or block an investigation before a citation-level decision exists;
an operational lookup failure must never hide an already-witnessed identity contradiction. F-11 APPROVED WITH
CONDITION: no separate investigation-level wall-clock timer for now, provided Step 4 formally demonstrates a finite
operational bound on every reachable execution path and derives the worst case symbolically; if Step 4 finds an
unbounded cycle, a path without a derivable bound or a local operation that can wait indefinitely, it stops at that
finding and recommends a wall-clock budget before Step 7; no timer for appearance only. F-15 APPROVED: the request
key and investigation identity are fixed at creation; the article-revision root is bound only when ACQUIRE succeeds;
pre-ACQUIRE records may carry a null root and stay attributable to the request key; no citation evidence, scientific
claim or final decision before the root is bound; the bound root is immutable; a later different capture means
staleness or a new investigation, never silent replacement. F-16 APPROVED: the lifecycle is CREATED, RUNNING,
BLOCKED, NEEDS_RESOLUTION, COMPLETED, FAILED, STALE, CORRUPT, with no duplicated derived states; NEEDS_RESOLUTION is
terminal for Stage 04 with outcome partial, keeps its open questions and conflicting evidence, is never shown as
COMPLETED and never yields a false positive or false negative from the conflict; later stages may extend resolution
through versioned evolution. No Stage 05 work and no claim that Stage 04 is implemented or verified.

## D-042 — F-11 resolved: hard wall-clock bound around each live ACQUIRE attempt
- Status: accepted
- Topic: stage-04-f11-live-acquire-bound
- Date: 2026-11-10
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step5/STEP5_OWNER_DECISION_D042.md; docs/verification/stage-04/SIMULATION_REPORT.md

Owner decision on the Step 4 result BLOCKED ON F-11 (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPAewpJuzMjqkzvVZfNQHxDy`, 2026-11-10T11:28:37Z, which also accepted Step 4 at `244c4b6`
and authorized Step 5 only). APPROVED WITH CONDITIONS: Stage 04 imposes a hard wall-clock bound around the entire live
ACQUIRE invocation at the Stage 04 boundary, without modifying the accepted Stage 03 transport;
`T_acq = FetchPolicy.deadline_s + FetchPolicy.op_timeout_s + 30 s` (240 s with the accepted defaults), a
controller/integration safety bound, not a scientific threshold. The timer covers the whole child-process live ACQUIRE
operation and starts immediately before the child is launched; a retained-bundle ACQUIRE does not use it. Live ACQUIRE
runs in a dedicated child process session owned by the parent, which ensures at the deadline that it cannot continue
network work; kill and reap latency outside the budget is measured or separately bounded, so 9 × 240 = 2160 s is the
maximum live-ACQUIRE child execution budget, not the investigation's whole wall-clock bound. A hard timeout is the
stable failure code `ACQUIRE_WALL_CLOCK_EXCEEDED`; nothing from a killed attempt is authoritative (no root binding,
successful bundle, scientific evidence, claim, decision or `step_succeeded`). The code may be retryable and counted in
φ only if that cannot shorten an observed Retry-After; Step 8 must prove that Stage 03 persists Retry-After before a
kill or that Stage 04 preserves `not_before`, otherwise the failure is terminal or deferred; CITERIFT never retries
earlier than an observed Retry-After, and Stage 03 throttling is not weakened. The effective bound, the fetch timeouts,
the 30 s allowance and the retry budgets are part of the configuration identity, so a change is detectable by
replay and staleness checks and historical investigations are never recomputed with other bounds. F-11 is
design-unblocked, not implementation-verified until the later production and fault-injection tests pass.

## D-043 — SR-03 unit anchor derived by Stage 04; final v1 reason vocabulary
- Status: accepted
- Topic: stage-04-sr03-unit-anchor-and-reason-vocabulary
- Date: 2026-11-10
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step5/STEP5_SCHEMA_REVIEW.md (SR-03); docs/verification/stage-04/review/step5/STEP5_PLACEHOLDER_MAPPING.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPHFkw4RSkx4W14idXWvzLNy`, 2026-11-10T15:59:11Z, which also
accepted Step 5 at `6111b279780825aab08953fd02b3711e7cbabd99` subject to this decision and authorized Step 6 only).

SR-03, option A approved. Stage 03 is not modified and stays authoritative for a unit's source span (`cp_start`,
`cp_end`, `byte_start`, `byte_end`). Stage 04 derives the unit anchor hash from the retained Stage 03 source artifact:
`unit_span_sha256 = SHA256(source_artifact_bytes[byte_start:byte_end])`, a half-open interval over the exact retained
bytes, never over normalized or reformatted text. Stage 04 verifies `0 <= byte_start <= byte_end <= len(source)`,
that the span belongs to the same bound root and Stage 03 extraction, and the source artifact digest before deriving
the hash; where a Stage 03 identifier anchor covers exactly the same span, its `raw_sha256` must equal the derived
hash. A mismatch fails closed and never creates a new identity. VERIFY recomputes the hash from the retained bytes.
The value is derived by Stage 04 and is never described as a Stage 03 field.

Reason vocabulary: `LOOKUP_QUERY_FAILED` (D-13) and `NOT_FOUND_IN_CHECKED_SOURCES` (D-16) approved;
`STATUS_NOT_ESTABLISHED` renamed `CURRENT_EFFECT_NOT_ESTABLISHED` (D-11: the current scholarly or retraction effect
cannot be established from the checked evidence); `SOURCE_TYPE_CONFLICT` renamed `RETRACTION_EVENT_TYPE_CONFLICT`
(D-7: conflicting Stage 02 retraction-event types or effects, not a conflict of data-source type). dt-1 guards,
precedence, classes and the frozen Step 4 oracle are unchanged by these names.

## D-044 — Journal-tail integrity semantics (Step 6 review finding R6-2)
- Status: accepted
- Topic: stage-04-journal-tail-integrity
- Date: 2026-11-10
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step6/STEP6_INDEPENDENT_REVIEW.md (R6-2); docs/verification/stage-04/review/step6/STEP6_D044_CLOSURE.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPEUWjPwtyadJ3r35wXrmJrf`, 2026-11-10T17:30:22Z, which
conditionally accepted Step 6 at `6fd799db0234fb9fcef42b7a9618eafe409833f1` and authorized this corrective closure
only). The owner accepts the R6-2 recommendation.

A final journal tail is an interrupted append (a **torn tail**) only when the physical record is incomplete; in v1 the
criterion is that the final bytes lack the terminating newline. Such a tail may be preserved and removed by Copy →
Verify → Preserve, and only after the whole preceding prefix has independently validated. A newline-terminated final
record is a complete physical record: if it is not valid strict canonical JSON, has a wrong digest, violates the
schema or M-1…M-14, has an invalid `prev`, references invalid or missing committed data, or otherwise fails
validation, the investigation is `CORRUPT` and the record is never dropped as crash recovery. Any defect in a
non-final record is `CORRUPT`. Incomplete append ≠ integrity failure; SPEC 8.6 is made consistent with SPEC 10.2.

Recovery order (the implementation's stronger behaviour, approved): read → identify a candidate incomplete tail →
validate the entire prefix → only if it is valid, preserve the original journal → verify the preserved copy →
publish the validated prefix → `fsync` → reopen and fold. If the prefix is corrupt, the journal is not mutated.

The Step 6 resource ceilings (`MAX_RECORD_BYTES` 1 MiB, `MAX_JOURNAL_BYTES` 512 MiB) remain provisional defensive
implementation ceilings, not justified final values, until a resource-bound argument from the Stage 04 model is
made (at the latest in Step 7). Accepted residual limitations of Step 6: process-death (not power-loss) fault
injection; `flock` on local POSIX file systems only; `.creating-*` leftovers reported, not deleted; a deleted lock
file causes fail-closed refusal; the Step 6 reviewer was a separate context, not an independent reviewer.

## D-045 — Stage 01 stale current-state note correction (one-time, owner-authorized)
- Status: accepted
- Topic: governance-stage01-note-correction
- Date: 2026-11-10
- Stage: 01 (metadata only)
- Supersedes: none
- Evidence: docs/audits/governance-2026-11-10-d045/README.md; docs/audits/governance-2026-11-10-d045/verify_d045_registry_diff.py; docs/verification/stage-04/review/step6/STEP6_D044_CLOSURE.md §7

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWUXdMpviEn4TgnzgKGQCtK`, 2026-11-10T18:25:11Z): a one-time
owner-authorized correction of current metadata. The registry already records Stage 01 as `ACCEPTED_CLOSED` at
`85da719ac43fc46170310b225c9190b63a046df8`, with `HANDOFF.md` and the evidence manifest retained, gates 01-A to 01-G
passed and the owner's acceptance of 2026-10-27. The Stage 01 `notes` value, written on 2026-10-25 before the handoff
existed, said the handoff had not been supplied; it was stale.

Only Stage 01's current `notes` value is replaced, with the owner's text verbatim, and `PROJECT_STATUS.md` is
regenerated with `citerift-gov render-status --write`. The note is kept, not deleted. Because no `citerift-gov` command
writes `notes`, the registry was edited by one exact string replacement, and a field-by-field comparison proves that
no other registry value changed.

This is not a reopening of Stage 01, not a scientific re-evaluation, not a new acceptance, not an amendment to Stage 01
findings and not authorization to change historical records. The Stage 01 authorization text (which correctly said on
2026-10-25 that no findings were accepted), revisions, gates, acceptance record, evidence manifest, history and
blockers are unchanged.

No Stage 00 notes capability is added now (`src/citerift/governance`, `schemas/governance` and `tests/stage00` are
unchanged). Dated notes with a `NOTE_PREDATES_STATE` warning remain a non-blocking governance-hardening candidate, to
be reconsidered only if more stale-note cases appear, several stages begin using mutable current-state notes, or the
final release review finds automated stale-note detection materially useful.

## D-046 — A complete unterminated journal record must pass full next-record validation
- Status: accepted
- Topic: stage-04-complete-tail-record-validation
- Date: 2026-11-10
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step6/STEP6_D044_REREVIEW.md (sections "The narrowed torn-tail rule" and "D-046")

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP6hByFwsEfpUhzKebsUsPBb`, 2026-11-10T19:23:48Z). The owner
confirms the D44-R2, D44-R2a and D44-R2b narrowing of the torn-tail rule at
`9c72852a2193e972f5a73b6b09a2c8a4c7a93855` and directs that it not be reverted.

A final fragment without its terminating newline that holds one complete JSON value is a recoverable torn tail only if
that value would be a fully valid next journal record under the same authoritative validation an append passes,
apart from the missing newline: strict canonical JSON, exact record schema with JSON token types (a boolean never
satisfies an integer field), digest, next `seq`, `prev`, journal version, record kind, step and attempt legality, root
binding, reference and layer legality, the existence and integrity of named blobs, and the M-invariants and state
rules Memory enforces. Otherwise the investigation is `CORRUPT` and the record is not removed. Incomplete or
uncheckable fragments compatible with one interrupted append (a prefix of the next record, possibly with zero-filled
blocks) remain candidate torn tails and are preserved before removal.

One source of truth: the complete tail record is validated by `Folder.check`, the fold check every append passes
before it is written; no second, hand-written approximation is kept. D-046 refines D-044 and D44-R2 toward fail-closed
behaviour only and does not broaden recovery. It is not cryptographic tamper protection: an actor able to rewrite the
journal and recompute the unkeyed hash chain is not detected without an external anchor. D-045 is accepted and
complete. The record and journal ceilings remain provisional; their derivation is owed in Step 7.

## D-047 — RB-1: high-cardinality collections leave the journal record as content-addressed blobs
- Status: accepted
- Topic: stage-04-record-collections-as-blobs
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md (sections D-047 and the bound tables)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z), which
also accepts Step 7 at `ab0ce66edafab7a7720649892386aa58795b9b91` for its Workflow Controller and orders this narrow
corrective closure before Step 8. RB-1 is approved. The 1 MiB record defect is not solved by raising
`MAX_RECORD_BYTES`: the journal is an audit and commit log, not a bulk-data container. A claim's evidence (supporting
ids, contradicting ids and the evidence supporting each conflict alternative) becomes a versioned, schema-validated,
content-addressed evidence-set blob with deterministic order, unique ids and no truncation. Its digest is part of the
claim identity, so `claim_id` binds the exact set content and no inline copy is kept. VERIFY must prove that every
referenced evidence id exists and is valid; a missing or corrupt set is corruption or failure, never an empty set.
`report_recorded.projections` becomes a content-addressed projection set with a digest, a count and a deterministic
order; the report stays a blob. Every Stage 04 journal payload is reviewed so that no collection scaling with Stage 03
units or candidates, Stage 02 events, or article-wide claims or projections makes one record grow without a
defensible bound. The existing blob architecture is used; no generic database layer is added.

## D-048 — RB-2: lookup evidence budget enforced before Stage 02 materializes a result
- Status: accepted
- Topic: stage-04-bounded-lookup-before-materialization
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md (section D-048); docs/verification/maintenance/A-02-001/MAINTENANCE_RECORD.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z). RB-2 is
approved in principle with a stronger requirement: the budget is enforced before Stage 02 materializes an unbounded
result; a cap applied after the current `Index.gather()` is rejected. The smallest backward-compatible bounded query
facility is added to Stage 02: `Index.gather()` is unchanged; within the budget the bounded result is identical to
`gather()`; over it, the query stops before materializing beyond the bound and never returns a truncated result as
complete. The Stage 02 change goes through the accepted-stage governance mechanism with fail-first evidence, the exact
owned-file patch, proof that `gather()` is unchanged, this authorization and the full accepted-stage validation. Over
budget is all-or-nothing: no positive finding and no `NOT_FOUND_IN_CHECKED_SOURCES` from it; the affected candidate
is unavailable (candidate-level `LOOKUP_UNAVAILABLE`), with the reason `LOOKUP_EVIDENCE_LIMIT_EXCEEDED`. The bound is
derived from the Stage 02 event representation, serialized size, the post-D-047 storage model and the query's memory
needs, with the pinned index as a sanity check only; it is part of the Stage 04 configuration and so of
`config_digest`. If no defensible default can be derived, the evidence is returned instead.

## D-049 — IA-11: ADAPTER_INCONSISTENT is a terminal code of every step
- Status: accepted
- Topic: stage-04-adapter-inconsistent-every-step
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md (section D-049)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z).
`ADAPTER_INCONSISTENT` is a stable, terminal, non-retryable code available to every step. It records an adapter that
raises an ordinary exception, returns the wrong result type, supplies illegal content, violates the protocol or
returns structurally contradictory metadata. It is not used for genuine domain failures, which keep their codes, and
it stays distinct from scientific uncertainty. Such a defect is recorded terminally and is never left open for W-6
recovery or retry exhaustion.

## D-050 — IA-4: mapping of a failed Stage 03 extraction document
- Status: accepted
- Topic: stage-04-stage03-failed-document-mapping
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md (section D-050)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z). For a
Stage 03 extraction document with `status = "failed"`: a worker code `EXTRACTION_DEADLINE_EXCEEDED`,
`EXTRACTION_MEMORY_EXCEEDED` or `EXTRACTION_WORKER_FAILED` maps to the same Stage 04 code with the approved
retryability; any other valid Stage 03 code maps to `EXTRACTION_FAILED`, non-retryable, with the Stage 03 code as the
reason and the failed document kept as evidence where safe; a missing or malformed code, or a document that
contradicts the Stage 03 schema, is `ADAPTER_INCONSISTENT`. A worker failure is never guessed. Every accepted Stage 03
failure family is tested.

## D-051 — IA-6: the evidence id binds the evidence kind
- Status: accepted
- Topic: stage-04-evidence-id-binds-kind
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md (section D-051)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z).
`evidence_id = H(observation, pointer, evidence_kind)` with the existing evidence domain tag. The same observation,
pointer and kind give the same id; a different kind gives a different id. Pointer text stays canonical; there is no
random component, and replay gives the same id. SPEC, the mathematical model, `ids.py`, the workflow evidence checks,
schemas and descriptions, tests, traceability and the Step 7 fixtures are updated. The frozen Step 4 oracle is not
altered unless it encodes the derivation; otherwise its digest is shown unchanged. No released records exist, so no
migration is needed; the identity change is documented.

## D-052 — TA-1: external journal checkpoint, design recorded now, implemented later
- Status: accepted
- Topic: stage-04-external-journal-checkpoint
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/closure/STEP7_D052_CHECKPOINT_DESIGN.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`, 2026-11-11T07:04:33Z). The design
is recorded now and implemented later with the CLI and report work. An optional external checkpoint holds the
investigation key, the final journal `seq`, the final journal digest and a format version. The only claim it supports:
given a checkpoint retained outside the investigation memory, a verifier can detect rewriting or truncation of the
journal prefix that the checkpoint covers. It is not called a signature, authentication or non-repudiation. It is
never written into the same journal or memory directory and is not added to the ASSEMBLE report; it is delivered on
stdout or to a user-selected file outside the memory root, and the verifier compares a supplied checkpoint with the
journal. No cryptographic dependency is added. R6-12 stays a recorded limitation.

## D-053 — Evidence batches: the journal commits evidence in content-addressed batches
- Status: accepted
- Topic: stage-04-evidence-batches
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/d053/D053_D054_CLOSURE.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPT7kaAY3dV5Ewo8KzF3bTe8`, 2026-11-11T10:31:40Z), choosing
the evidence-batch answer to OD-J of the Step 7 closure. No article-size cap is imposed to make the journal fit, and
Step 8 is not started. The journal stays the audit, commit and state log. Evidence is committed in deterministic,
content-addressed, immutable evidence-batch blobs, each named by one `evidence_batch_recorded` record with a compact
closed payload. A batch holds complete, schema-valid items with D-051 ids and valid references, with no loss and no
duplicate; a missing or corrupt batch fails closed. Items are in topological order over their dependency graph with
the evidence id as tie-break; a cycle or a missing reference fails. The batch size is not guessed: a byte ceiling is
derived from the maximum item size, `MAX_BLOB_BYTES`, encoding overhead, parse and validation memory, the record
count and measured write and open performance; one legal item always fits; boundaries are deterministic and tested
at N−1, N and N+1. The fold supports id existence, id to batch, M-3, M-4, M-7, evidence sets, replay, corruption
detection and commit discipline, with no second mutable database (any index is rebuildable). Batches of a failed
attempt are not authoritative; only `step_succeeded` commits them. D-047 evidence sets stay. Versions advance without
migration: journal format 1 is the original, 2 is D-047/D-051, 3 is batches; none was released. Stage 00 contracts
and Stage 03 schemas are unchanged. The 512 MiB journal limit is proven from first principles with headroom or
returned as a new owner decision; it is not raised. Scientific behavior is unchanged and proven equal before and
after on a fixture; the Step 4 oracle stays frozen.

## D-054 — The report is a manifest graph of content-addressed chunks
- Status: accepted
- Topic: stage-04-report-manifest-chunks
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/d053/D053_D054_CLOSURE.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPT7kaAY3dV5Ewo8KzF3bTe8`, 2026-11-11T10:31:40Z), choosing
the chunked-report answer to OD-R of the Step 7 closure. The report blob is a small versioned manifest: schema and
version, investigation and root identity, terminal state, outcome, article summary, limitations, identities and
configuration, counts, and ordered references to its components. Claims are stored in deterministic
content-addressed chunks whose ordered digests and total count are in the manifest. The evidence of the report reuses
the committed evidence batches by digest; it is duplicated only with a proven and documented semantic need. The
D-047 projection set stays. The durable report is the whole manifest graph: VERIFY proves every node, and nothing is
silently omitted.

## D-055 — Per-candidate journal records are committed in step-local batches
- Status: accepted
- Topic: stage-04-candidate-batches
- Date: 2026-11-11
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step7/d055/D055_CLOSURE.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP7cfPWf5UN6kmKGbSHoPG1n`, 2026-11-11T16:48:14Z), answering
OD-J2 of the D-053/D-054 closure: the remaining per-candidate journal records are batched. The journal no longer
keeps one record per candidate; the 512 MiB journal limit is not raised and no article-size cap is imposed. Baseline
`0097a9329d728e8260d48dc79a53a6be5f9c4fa9` with CI run 313 as the green baseline. Batching is step-local: a batch
never crosses a workflow step or an attempt, and LOOKUP and DETECT stay independently authoritative. LOOKUP commits
its lookup observation references in deterministic LOOKUP batches of compact references and metadata (the lookup
observation blobs stay separate blobs, never inlined). DETECT commits each candidate's claim, decision and optional
question as one entry of a DETECT candidate-result batch; this is storage only (candidates are never merged; dt-1 and
W-8 are unchanged). A batch belongs to one step and one attempt and is authoritative only at `step_succeeded`; blobs
of a failed or interrupted attempt may remain but are never committed. The order is the canonical candidate order,
independent of adapter order and in conflict with neither the report order nor dt-1 identity. The D-053 primitive and
ceiling are reused; the ceiling is re-derived only if the candidate entry maximum requires it, by the same method, and
one legal entry always fits. The fold exposes the same logical objects (lookup observations, claims, decisions,
questions, relationships, committed order) and callers consume the logical fold; any index is disposable. W-8 stays
fully enforced; the dt-1 and Step 4 differential checks run unchanged and the oracle stays frozen. The D-054 report
consumes the logical fold with no duplicate store. The journal bound is recomputed from the actual format-4 records as
an executable, retained bound. The version advances (journal format 4) without migration; formats 1 to 3 are
development-only. IF-7 (the Stage 03 capture schema has unbounded attempts, issues and failure_artifacts) stays a
Step 8 condition. Step 8 is not authorized.
