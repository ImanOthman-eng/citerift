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
