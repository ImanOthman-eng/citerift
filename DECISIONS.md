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

## D-056 — Live ACQUIRE has no graceful-stop period
- Status: accepted
- Topic: stage-04-live-acquire-no-graceful-stop
- Date: 2026-11-12
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step8/STEP8_CLOSURE.md

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3QUKzTGVBuK7bcRu4jArpU`, 2026-11-12T14:58:09Z), approving
OD-S8-1 of the Step 8 closure; the same message accepted Step 8 technically at
`7e16bdefa6191de23948b54616636ba08f10c9c4`. At the exact `T_acq` deadline the Stage 04 parent (1) immediately
stops/freezes the supervised child tree, (2) kills the attributable child process tree, (3) reaps the direct child and
(4) performs the bounded cleanup and survivor check. There is no SIGTERM or graceful-stop interval before the hard
kill and no grace period after `T_acq`. Normative reason: `T_acq` is the maximum child execution budget; a grace
interval after it would extend that budget and one inside it would shorten the capture execution budget. The
Retry-After information that may affect retry safety is captured durably and independently as response headers
arrive, so no graceful shutdown is needed to preserve it. Kill, reap and cleanup overhead stays outside the child
execution budget and continues to be reported separately. SPEC 9.2 is corrected to this behaviour; the formula
`T_acq = deadline_s + op_timeout_s + 30 s` and the implementation are unchanged. The documented limitation stays: an
adversarial descendant that escapes both the process session and the parent relationship through an unsupported
double-fork/`setsid` pattern is outside the current attribution model; production Stage 03 capture starts no
subprocess. With that explicit platform and process-model limitation, F-11 is recorded as IMPLEMENTATION_VERIFIED.

## D-057 — The lookup evidence budget is investigation identity
- Status: accepted
- Topic: stage-04-lookup-budget-identity
- Date: 2026-11-12
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step8/STEP8_CLOSURE.md; tests/stage04/test_step8_resume_stale.py

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3QUKzTGVBuK7bcRu4jArpU`, 2026-11-12T14:58:09Z), approving
the D-048 behaviour reported in the Step 8 closure. `lookup_evidence_budget_bytes` is part of the effective request
configuration, therefore of `config_digest`, which is part of `investigation_key`; changing the budget creates a
different investigation and does not make the historical investigation STALE. STALE means that an already-created
investigation is resumed against an external or input identity that changed underneath the same investigation
identity (capture digest, Stage 03 extraction/profile identity, Stage 02 index snapshot, Stage 02 policy identity,
Stage 04 schema/engine identity where the investigation key is unchanged). A configuration change that participates
in `config_digest` defines a different requested computation; the original investigation stays valid under its
original configuration and is never recomputed in place. This applies to every configuration field S-4.7 already
defines as investigation identity, including `A_max`, `F_max`, the fetch-policy digest, the D-042 live-ACQUIRE bound,
`lookup_evidence_budget_bytes`, and the plan version included separately in the key. S-4.7 is not altered, the
budget is not removed from `config_digest`, and no special case forces STALE. With D-056 and D-057 recorded, Step 8 is
accepted and closed. Step 9 is not authorized; the D-051 evidence-pointer collision in multi-candidate units is a
mandatory Step 9 input (Step 8 closure, section 19).

## D-058 — A notice DOI with the original's PMID and no incompatibility witness
- Status: accepted
- Topic: stage-04-notice-doi-original-pmid-no-witness
- Date: 2026-11-16
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step9/STEP9_CLOSURE.md; tests/stage04/test_step9_detector.py

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWCTdWnihKu3hUi9BD1ZLbN`, 2026-11-16T13:41:40Z), approving
option (a) of OD-S9-1 of the Step 9 closure; the same message accepted Step 9 at
`4886546c4922291fd8289c03a86435299a3da897` and the production implementation at
`846cb81b90d71355daf2d466cd58e8e54cc1692b`. The current dt-1 semantics and the frozen Step 4 model are kept. For a
`PAIR` whose Q1(DOI) is `notice_only`, whose PMID independently resolves to the retracted original (Q1(PMID) and/or the
deciding Q2 support the original as retracted), and where Retraction Watch records no original DOI that would create an
explicit incompatibility witness, κ stays `UNDETERMINED`, not `INCOMPATIBLE`, and the result may be
`RETRACTED_WORK_CITED` under D-14 with the existing reasons `KEY_RESULTS_DIFFER` and `PAIR_UNCORROBORATED`. Rationale:
the positive finding is supported by the cited original's PMID; it does not treat the notice DOI itself as the original
work. `IDENTITY_CONFLICT` is not inferred merely from the absence of the original DOI in the checked source. If an
actual incompatibility witness exists (the definition in SPEC section 6.5; the owner message and the Step 9 closure cite
it as "S-6.10", a mislabel: S-6.10 is the unavailable-lookup rule), D-6 takes precedence and the result is
`IDENTITY_CONFLICT`; a DOI-only notice remains D-15 `NOTICE_CITED`. The inaccurate summary sentence of SPEC 7.4 (and the
same sentence in RISK_ANALYSIS R4) is corrected: this is a specification-summary correction, not a dt-1 change. dt-1,
the table version, the Step 4 model, the oracle manifest and the production detector are unchanged. A regression test
pins the distinction.

## D-059 — VS-5: PMID_ROLE_COLLISION is carried in the evidence
- Status: accepted
- Topic: stage-04-vs5-collision-carried-in-evidence
- Date: 2026-11-16
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step9/STEP9_CLOSURE.md; tests/stage04/test_step9_real.py

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWCTdWnihKu3hUi9BD1ZLbN`, 2026-11-16T13:41:40Z), approving
option (a) of OD-S9-2. For VS-5, "`PMID_ROLE_COLLISION` carried" is satisfied when the collision remains present and
resolvable in the committed claim evidence and provenance chain. It is not required to be a claim reason unless the
collision participates in the rule that actually determines the class. D-10 continues to use `PMID_ROLE_COLLISION`
when its exact guard applies; a D-14 claim may retain the collision in evidence without a non-deciding
`PMID_ROLE_COLLISION` reason; dt-1 reason semantics, the model and the oracle are unchanged. Rationale: evidence and
provenance answer what was observed; reason codes answer why this rule and class were selected; the two are not
conflated. At the Step 11 vertical-slice acceptance, VS-5 must be verified explicitly to expose the retained collision
in its evidence chain even when D-14 is the deciding rule. The VS-5 evidence note is clarified; its class-selection
rule is unchanged.

## D-060 — The B-8 resolution preserves D-051
- Status: accepted
- Topic: stage-04-b8-pointer-placement-preserves-d051
- Date: 2026-11-16
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step9/STEP9_CLOSURE.md; tests/stage04/test_step9_b8.py

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWCTdWnihKu3hUi9BD1ZLbN`, 2026-11-16T13:41:40Z),
acknowledging and accepting the Step 9 B-8 resolution. D-051 remains `evidence_id = H(observation, pointer,
evidence_kind)`; no candidate id is added to the hash. The normative correction is the semantic placement of
candidate-scoped evidence: distinct candidate-specific facts must be assigned distinct canonical pointers; the Step 9
injectivity proof (MM 4.6) establishes that the selected `work_candidate` pointer is distinct across distinct
candidates; equivalent replay produces the same pointer and evidence id; truly identical evidence may still
deduplicate. The production `_Items` collision guard is mandatory defence in depth: if one evidence id would represent
two different logical evidence objects, DETECT fails closed with `ADAPTER_INCONSISTENT`. This is an accepted
refinement of pointer-selection semantics, not a change to the D-051 identity function; no schema or version
migration is required. With D-058, D-059 and D-060 recorded, Stage 04 Step 9 is accepted and closed. Carried forward
unchanged: the MM EV-2 wording refinement (audit A-5) to the Step 12 freeze review; the engine-version bump (A-6) to
the Step 12 freeze; the absent real-data classes stay disclosed as coverage limitations; the prior-art primary-source
review to gate 04-J; the VS-5 evidence-level collision assertion to Step 11. Step 10 is not started (owner: "Do not
start Step 10 yet").

## D-061 — Step 11 performance: accepted, the ≤ 5 s p95 target NOT_MET
- Status: accepted
- Topic: stage-04-step11-performance-target-not-met
- Date: 2026-11-17
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step11/STEP11_CLOSURE.md; docs/verification/stage-04/evidence/vertical-slice/results/perf_breakdown.json

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3qrWZMdMRxJ3hF99iSrL1H`, 2026-11-17T02:07:18Z); the same
message accepts Step 11 at `099dc1988b5131093e0aa884e3263fb4dbfa1978`, the production vertical slice VS-1 to VS-10 and
CI run 329 as the current green evidence. The Step 11 vertical slice is accepted although VS-1 (6.57 s p95) and VS-3b
(5.39 s p95) exceed the planning benchmark "warm retained investigation ≤ 5 s p95". The benchmark is part of the
retained performance verification strategy but is not a Step 11 vertical-slice exit criterion. The target is recorded
as NOT_MET at Step 11: it is not marked PASS, not weakened or redefined, the measurements are not deleted and the excess
is not called runner noise. The scientific and functional vertical-slice results remain accepted. Carried to Step 12,
which must investigate safe performance improvements before freeze, in this order: (1) eliminate redundant Stage 02
index-identity work as part of D-062; (2) then profile JSON Schema validation; (3) cache compiled validators only if
measured construction or initialization overhead is material. No validation check may be removed; no scientific result
may depend on caching; any cache must be disposable and reconstructible. After the Step 12 fixes the retained warm
benchmark is rerun; if the target is still not met after safe improvements, the residual limitation is reported
honestly at freeze rather than weakening correctness.

## D-062 — Stage 04 index identity uses the Stage 02 canonical content identity
- Status: accepted
- Topic: stage-04-index-identity-canonical-stage02
- Date: 2026-11-17
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step11/STEP11_CLOSURE.md (A11-3)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3qrWZMdMRxJ3hF99iSrL1H`, 2026-11-17T02:07:18Z), resolving
Step 11 finding A11-3 directionally now, for implementation in Step 12. The exact SQLite file is not required as a
permanent release artifact merely to reproduce Stage 04 claim and report digests: Stage 02 explicitly allows
non-byte-identical SQLite builds and already defines canonical reproducible digests (`artifact_digest`,
`semantic_digest`, `export_lines`), which its build replacement rule treats, not raw SQLite bytes, as the equality test
for an equivalent build; Stage 04 currently binds scientific identity at the wrong layer by using the raw file SHA-256.
Required Step 12 design: the authoritative Stage 04 Stage 02 identity is based on the canonical Stage 02 artifact,
including at minimum `snapshot_id`, `policy_version`, the lookup-result/schema version and the Stage 02 canonical
`artifact_digest`, with `semantic_digest` and `export_lines` retained as consistency/provenance metadata where
appropriate (the exact field shape is a Step 12 detail). The raw SQLite byte hash must not determine scientific claim or
report identity. Scientific/content identity (which evidence/queryable Stage 02 artifact this is; it must survive a
byte-different but canonically identical rebuild) is separated from the operational file-integrity guard (whether the
concrete file changed while Stage 04 used it; a raw file SHA-256 and/or stat tuple may still be used transiently for
it), which must not make scientifically equivalent rebuilt indexes produce different lookup-observation identities,
evidence ids, claim ids, report digests or C(J). Integrity: an `artifact_digest` string read from mutable SQLite
metadata is not simply trusted; before Stage 04 accepts a canonical identity, Stage 02's existing verification and
digest machinery (`verify`, `compute_digests`, derivation and manifest checks) proves the current index content
corresponds to it. The verified result may be reused once per process/invocation while a strong filesystem fingerprint
is unchanged; the reuse key must detect ordinary replacement or modification and is invalidated if the file identity
or stat changes; validation results are not cached across processes; the before/after LOOKUP mutation guard is not
weakened. Equivalent-rebuild requirement: the accepted snapshot is built independently at least twice; with identical
canonical artifact identity, Stage 04 must show the same Stage 02 scientific identity, no STALE solely from differing
SQLite bytes, and the same lookup observations, evidence ids, claim ids, report digest, projection-set digest and C(J);
a genuinely different canonical `artifact_digest` still makes an existing investigation STALE. Tamper tests at least:
queryable row modified, event modified, derived table modified, stored canonical digest forged with content unchanged or
mismatched, manifest mismatch, file replaced during LOOKUP; none may pass as the recorded canonical artifact. This
changes Stage 04 pre-freeze identity semantics; the Stage 04 schema/engine identity is handled consistently in Step 12.
No migration is required for the development-only Step 8 to 11 journals, which remain retained historical engineering
evidence; fresh post-freeze investigations become authoritative for evaluation. No code is changed for D-062 in the
Step 11 closure.

## D-063 — Invalid requests are refused before an investigation exists
- Status: accepted
- Topic: stage-04-invalid-request-refused-not-failed
- Date: 2026-11-17
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step11/STEP11_CLOSURE.md (VS-7); docs/verification/stage-04/SPECIFICATION.md (S-4.3, section 14)

Owner decision (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP3qrWZMdMRxJ3hF99iSrL1H`, 2026-11-17T02:07:18Z). The current
VS-7 behaviour is accepted. A request that fails the Stage 04 request boundary, including an unpinned or invalid
revision request, is refused by the command line with exit status 3 (invalid): no Investigation Memory, no journal, no
lifecycle. This is consistent with SPEC S-4.3 (an invalid or unpinned subject request is refused before an
investigation is created). No FAILED investigation is manufactured for an input that was never a valid investigation
request. A syntactically valid, pinned request that creates an investigation and later discovers an input defect may
end FAILED with its stable failure code: for example a corrupt bundle, a requested revision that differs from the
captured or bundle revision discovered during ACQUIRE, or a schema-invalid Stage 03 result. The SPEC section 14 VS-7 row
is clarified to distinguish the two (a vertical-slice wording correction, not a controller semantic change). With
D-061, D-062 and D-063 recorded, Stage 04 Step 11 is accepted and closed. Mandatory Step 12 inputs: I-2 (internal
`workflow.outcome()` disagrees on partial extraction); I-3 with A-6 (engine identity/version freeze); I-4
(projection-set schema wording); A11-3 (implement D-062); A11-4 (safe performance optimization and benchmark rerun,
D-061); A11-5 (two user-visible not_before representations); A11-6 (absolute scratch paths in development journals);
the MM EV-2 wording; the primary-source prior-art review for gate 04-J. Step 12 is not started (owner: "Do not start
Step 12 yet").

## D-064 — The D-062 identity-verification profile (OD-S12-1)
- Status: accepted
- Topic: stage-04-d062-identity-verification-profile
- Date: 2026-11-17
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step12/STEP12_TRIAGE.md (C-02, section 2.3); docs/verification/stage-04/freeze/d062/tamper_differential.json

Owner decision OD-S12-1 (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPX6tov3HkhvFC2ppixAiwyL`, 2026-11-17T16:57:39Z),
resolving Step 12 finding C-02 (the verification scope of D-062). Approved: each Stage 04 process verifies the Stage 02
index with the profile that covers everything LOOKUP reads, not Stage 02's complete `verify()`; the approximately
18-second profile is the baseline; the cross-process trust-by-file-hash option is rejected. Stage 02's complete
`verify()` remains the authoritative certification of the artifact, and its semantics are not changed. The profile
carries an explicit Stage 04 name, `verify_index_identity`, and is never described as "full Stage 02 verify". It
includes: SQLite integrity and structural checks; Stage 02 format and policy compatibility; recomputation of
`artifact_digest`, `semantic_digest` and `export_lines` and comparison with the stored metadata and with the published
build manifest; full re-derivation of the derived tables with equality to the stored tables; construction of the
canonical identity; and the before/after LOOKUP mutation guard. It may omit only the full per-event JSON-Schema
re-validation pass. Mandatory before acceptance of the profile: a differential tamper proof running both complete
`verify()` and the profile on the tamper corpus (queryable event, raw record and derived-table mutation, malformed event
JSON, schema-invalid event type or value, forged `artifact_digest` and `semantic_digest`, manifest mismatch, metadata
and content mismatch, inode replacement, size-preserving mutation, replacement during LOOKUP); for every corruption
that can affect LOOKUP or the canonical identity the profile must fail closed, and a case that only complete `verify()`
rejects and that can affect LOOKUP, provenance or the canonical identity stops the work before freeze. Complete
`verify()` is run on both rebuilt indexes, on the final freeze artifact and on tamper controls where needed. The
performance target is not marked PASS. After D-062 correctness is closed, Step 12 profiles the verification by
component, identifies redundant passes over the index, determines whether digests, derivation and structural
verification can share one read pass without weakening any check, and then profiles JSON-Schema validation; the
event-validator cost must not be attributed to validator construction without measurement. Optimize passes, not checks:
no validation may be removed solely to reach the 5-second target.

## D-065 — CI verify job timeout 30 minutes; 18 minutes is diagnostic (OD-S12-2)
- Status: accepted
- Topic: ci-verify-job-timeout-30-minutes
- Date: 2026-11-17
- Stage: 00
- Supersedes: none
- Evidence: docs/verification/maintenance/A-00-003/MAINTENANCE_RECORD.md

Owner decision OD-S12-2 (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPQBMQAvkyRYvCrNmrZM88n8`, 2026-11-17T18:45:34Z),
answering the Stage 04 Step 12 runtime stop after two consecutive Python 3.12 CI jobs (runs 333 and 334) were cancelled
at the 20-minute limit. Approved: the `timeout-minutes` of the existing `verify` matrix job in
`.github/workflows/ci.yml` changes from 20 to 30; no other `.github/` change is authorized. Not changed: the tests,
their assertions, coverage, the Python 3.12 + 3.13 matrix (no version skipped), the suite (not sharded), and product
code (not optimized for runner variance). The owner's reading of the evidence: the 3.12 slowdown is spread across
untouched Stage 00 to 03 tests, Python 3.13 is essentially unchanged from the pre-Step-12 baseline and the new Step 12
tests add about 21 s on 3.13, so it is GitHub-hosted runner-speed variance, not a Step 12 regression. Runtime policy
from now on: 18 minutes is a diagnostic threshold, not a correctness gate (a job over it is recorded and investigated,
and is not blocking solely for that when a runner-wide slowdown is demonstrated); 30 minutes is the hard infrastructure
timeout, and a required job that reaches it stops the work for an owner decision before further CI changes. The work
also stops on evidence of a code-induced runtime regression (both Python versions regress materially after a change,
the slowdown localizes to new or modified tests or code, or comparable runners show sustained growth attributable to
Step 12); slow runs are not classified as runner noise automatically. This decision does not change D-061, the
retained ≤ 5 s p95 target (still rerun and reported honestly before freeze), the Step 12 performance work, the
D-062/D-064 verification semantics, test completeness, the zero-skip requirement or the full Python matrix. The change
is committed as a narrow Stage 00 maintenance (A-00-003) before Step 12 continues, and a green complete CI run (both
Python versions, check-report, clean tree, pip-audit --strict, ci-gate) is required before Step 12 proceeds to freeze.
The same message keeps the D-064 work unchanged and accepts the 21-case differential proof with zero discrepancies as
evidence for `verify_index_identity`.

## D-066 — Stage 04 freeze accepted with the ≤ 5 s p95 target NOT_MET
- Status: accepted
- Topic: stage-04-freeze-performance-target-not-met
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/freeze/FREEZE_REPORT.md (section 7); docs/verification/stage-04/freeze/ATTESTATION.md; docs/verification/stage-04/review/step12/STEP12_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6` (2026-11-18T08:19:10Z) accepts the Stage 04 freeze:
frozen scientific-content commit `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0`, tree
`86152ad543971d321059f16f93c3aff671f467c4`, freeze manifest digest
`609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc`, attestation commit
`15ef3c302e3d0a5406150e523b144174ed69f433`, and CI run 338 on the exact frozen commit. The freeze is accepted with the
performance target "warm retained investigation ≤ 5 s p95" recorded as NOT_MET. The frozen measured behaviour is an
explicit engineering limitation: about 25.5–30.5 s p95 across the measured cases, of which about 24–25 s is the
per-process D-064 Stage 02 canonical identity verification. Rationale (owner): the target is an engineering-performance
objective, not a scientific correctness gate; meeting it now would require changing a deliberately accepted
integrity/reuse rule after freeze; correctness and provenance integrity take precedence. D-064 is not weakened; no
cross-process trust and no reduced verification profile may be introduced merely to hit the target; the target must
never be claimed as met. The freeze report keeps the limitation (it is section 7 and the first entry of the manifest's
limitations; the freeze is not regenerated to add this decision). Future optimization of the verification architecture
only in a post-Stage-04 version or through an explicit freeze-breaking owner decision.

## D-067 — E-05: identity-conflict evaluation is exhaustive-descriptive, no hard minimum denominator
- Status: accepted
- Topic: stage-04-e05-identity-conflict-exhaustive-descriptive
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step12/STEP12_TRIAGE.md (E-05); docs/verification/stage-04/review/step12/STEP12_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6` (2026-11-18), for the Step 13 pre-registration.
Every IDENTITY_CONFLICT case that occurs in the final evaluation sample is independently annotated and adjudicated.
There is no hard minimum identity-conflict denominator: sampling is not expanded solely to obtain a number of identity
conflicts, and the gate does not fail merely because identity conflicts are rare or absent. Reported at minimum: the
count per language; the pooled count; the adjudicated interpretation of each occurring case; whether the engine's
abstention was justified; whether an annotator judged the citation unambiguous and attachable by one identifier; and
whether any identity-conflict case was incorrectly converted into a positive attachment. If n = 0, the report states
that no identity-conflict case occurred in the pre-registered evaluation sample; if n > 0, all cases are reported
descriptively. No population-rate claim is made from this denominator unless Step 13 independently pre-registers a
valid inferential design for it. The structural hazard requirement stays strict: an unresolved identity conflict must
never be silently counted as a positive attachment.

## D-068 — E-06: attachment precision covers all four positive Stage 04 classes
- Status: accepted
- Topic: stage-04-e06-four-class-attachment-precision
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step12/STEP12_TRIAGE.md (E-06); docs/verification/stage-04/review/step12/STEP12_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6` (2026-11-18). The primary attachment-precision
denominator includes every unit classified into any positive Stage 04 work-status class: RETRACTED_WORK_CITED,
CONCERN_CITED, CORRECTION_CITED and REINSTATED_WORK_CITED, since all four make an affirmative attachment/status
assertion about a work and carry false-attachment risk. Primary metric, per language: positive_attachment_precision =
correct positive attachments / all four-class positive attachments, with the pre-registered exact confidence-interval
method. The existing proposed positive denominator applies to this pooled four-class metric unless Step 13 feasibility
analysis, performed before the draw and without prediction exposure, demonstrates that the denominator rule itself must
be clarified. Also reported, for every positive class with n > 0: count, correct and incorrect attachments, and an exact
interval where statistically interpretable. No hard per-class minimum for rare CORRECTION_CITED or
REINSTATED_WORK_CITED cases; a class with zero cases is reported as n = 0. Step 13 may additionally pre-register a
secondary subset metric over RETRACTED_WORK_CITED + CONCERN_CITED for continuity with the original planning question,
but it must not replace or hide the all-four-class primary precision. No metric definition may change after the sample
is drawn.

## D-069 — E-08: sensitivity analysis and naive baseline are pre-registered evaluation tooling, not engine code
- Status: accepted
- Topic: stage-04-e08-evaluation-tooling-outside-frozen-engine
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/review/step12/STEP12_TRIAGE.md (E-08); docs/verification/stage-04/review/step12/STEP12_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6` (2026-11-18). The freeze is not broken to add the
sensitivity variants or the baseline scorer to the production engine; they belong to the Step 13
pre-registration/evaluation layer and are specified and hashed before the final sample is drawn. Naive baseline: the
baseline described in the planning package, flag a unit when any eligible cited identifier appears in the relevant
Retraction Watch identifier fields, with every eligibility and matching rule defined precisely before the draw; it must
not call the production detector. Sensitivity variants (descriptive only, never used to tune or alter the frozen
engine): (1) identifier_link excluded; (2) P-2 / identity-conflict protection disabled; (3) labeled_reference_text
included. Executable tooling, if useful, is added in Step 13 as separate evaluation-only tooling under the
verification/evaluation area; it must not modify `src/citerift/investigation`, alter the frozen engine, frozen schemas
or dt-1, or be imported by production code; it is committed and hashed before the final draw and has deterministic tests
on already exposed development fixtures. Deriving sensitivity results from frozen retained intermediate evidence is
preferred. A variant that cannot be computed faithfully without changing the frozen production engine is not
approximated: its limitation is pre-registered and it is omitted from final execution. The pre-registration states
exactly which variants are executable before the draw.

## D-070 — Step 13 pre-registration accepted; the Stage 03 listed tier stays in the frame
- Status: accepted
- Topic: stage-04-step13-preregistration-accepted-listed-tier-kept
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/evaluation/PREREGISTRATION.md; docs/verification/stage-04/evaluation/PREREGISTRATION_MANIFEST.json; docs/verification/stage-04/review/step13/STEP13_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP2Hk5yHet3jmkhGoVf9yZD5` (2026-11-18T12:04:37Z). The owner accepts the
Stage 04 Step 13 pre-registration exactly as committed at `827ac1aa1d9d16d444d4860e4119f8633d8e802e`, canonical
pre-registration digest `P = 4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a`, with CI run 341 as its
green verification. Listed tier: KEEP IT IN, exactly as registered; the frame is not rebuilt and P does not change; the
Stage 03 listed tier is not treated as design exposure for exclusion purposes (listed-only pages were never captured,
read, annotated or used for Stage 04 design; excluding them would reduce English S1 from 380 to 105 and thin the
marker/notice hazard test). Registered frame: Arabic S1 143, S2 37 (180); English S1 380, S2 307 (687); the exposure
rules of PREREGISTRATION section 3.3 remain binding. Accepted with P: G1 ≥ 30, G2 one-sided 95 % upper bound ≤ 0.10,
G5 ≥ 60 per language; expansion targets 40 and 75; allocation 22 S1 + 8 S2 primary and 7 + 3 reserve per language;
expansion blocks and the 200-attempt ceiling; the section 14 deviations; D-067, D-068, D-069 as registered; registry
04-I and MATHEMATICAL_MODEL 11.2 read as superseded by D-067 and D-068. No denominator, gate, allocation, exposure rule,
metric or replacement rule may change after this acceptance without an explicit pre-registration-breaking owner
decision. Seed: exactly the registered rule (drand quicknet, the first round at least one hour after this message, no
alternate round, at least two mirrors agreeing, all mirror answers kept in SEED.json, randomness = SHA-256(signature)
checked; no two-mirror agreement within 24 hours → STOP for owner decision); the absence of local BLS public-key
verification is accepted as the registered limitation. Step 13 is ACCEPTED AND CLOSED; Step 14 only is authorized,
strictly under P; Step 15 does not start until the Step 14 campaign is complete and presented for owner review.

## D-071 — Gate 04-I failed evaluation accepted; one corrective cycle within Stage 04
- Status: accepted
- Topic: stage-04-04i-failed-corrective-cycle
- Date: 2026-11-18
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/evaluation-campaign/REPORT.md; docs/verification/stage-04/evaluation-campaign/SCORES.json; docs/verification/stage-04/review/step14/STEP14_CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPTDrESsDr75RoYgLhdymUyn` (2026-11-18T20:07:29Z). Gate 04-I at evaluation
commit `1064113902c674f1c61dcb7eda33afe40350ca71` is accepted as a valid, faithfully reported failed evaluation
(English G2 FAIL, English G3 FAIL, Arabic G4 FAIL, overall NOT PASSED). The frozen engine `b5bf8ed` is not accepted as
the final Stage 04 engine. One evidence-supported corrective cycle within Stage 04 is authorized; Stage 04 remains
IN_PROGRESS; Step 15 does not start. The completed campaign is never altered, deleted, rescored, redrawn or rerun (P,
seed, draw, locked labels, RUN.json, SCORES.json unchanged; no samples added; no Arabic export created in it; no rerun
on the 80 articles); it is design-exposed development evidence from now on, and its 80 articles, revisions, packets and
locked items join the future exposure manifest. The cycle: root-cause audit of `en-39868218` / `un-00011` and a
read-only role-collision census of the pinned Stage 02 snapshot; the general rule "an identifier whose checked evidence
gives incompatible publication-object roles must never produce a positive work attachment solely because one of those
roles is original" (source/evidence based; no DOI, publisher or "Withdrawal" special case; abstain, preferably
UNRESOLVED_IDENTITY, unless independent production evidence resolves the object; a new reason code only if no existing
one fits); the protection runs before D-14 without weakening contradiction → unresolved → operational failure →
positive → notice/no-finding; a new post-failure reference-model version, the old oracle kept; Stage 04 correction
preferred, and any Stage 02 maintenance only after a separate owner decision; the role-collision adversarial suite and
full regression on the vertical slice, the 232 development revisions and the 80 exposed campaign articles; evaluation
runner fixes (memory outside the repository from the start, export parent created before the first article, fail-first
tested); fresh independent reviews (scientific semantics, identity/publication-object roles, regression, source
provenance, security, evaluation leakage) with no unresolved HIGH/CRITICAL; a new engine identity (not 0.2.0; at least a
new minor version); a complete new Step-12-style freeze, the old freeze marked SUPERSEDED_AFTER_FAILED_04_I and kept; an
updated exposure manifest hashed and committed. For this instruction the work stops at the new freeze candidate; the new
Step 13 pre-registration (P2, new drand seed, G2 ≤ 0.10, G3 = 0, G4 = 0 by default) waits for explicit authorization.

## D-072 — Strict role-collision resolution rule (dt-2) approved
- Status: accepted
- Topic: stage-04-dt2-strict-resolution
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/corrective/census/PAIR_CENSUS.json; docs/verification/stage-04/corrective/census/PAIR_CENSUS_LENIENT.json; docs/verification/stage-04/corrective/review/TRIAGE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj` (2026-11-19T07:45:19Z). The strict interpretation
implemented in dt-2 is approved; the lenient alternative is not adopted. A second cited identifier resolves a
role-collided identifier only when the checked evidence positively distinguishes the work from the notice: the resolving
cited key is free of a notice role, directly identifies the same work, and its record gives a distinct notice identifier
in that scheme where SPEC 7.3a requires the discrimination. Absence of a notice role is not by itself evidence that the
key cannot identify the notice. The correction is precision-first and fail-closed; its recall cost is accepted and stays
visible as an explicit recall/abstention trade-off, never as a performance result: dt-1 positive pairs 31,506; strict
dt-2 loses 1,472; the lenient alternative would lose 800. The strict alternative stays documented in SPEC,
RISK_ANALYSIS, the freeze report, the regression evidence and future P2 limitations. No threshold or holdout-derived
special case is authorized.

## D-073 — No same-work-sibling exemption (reviewer finding C-01)
- Status: accepted
- Topic: stage-04-dt2-no-sibling-exemption
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/corrective/review/REVIEW_C.md; docs/verification/stage-04/corrective/regression/CAMPAIGN_REGRESSION.json

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`. No exemption is added for the 53 same-work
sibling-record pairs of C-01; their strict dt-2 behaviour (UNRESOLVED_IDENTITY when the D-10 role-collision guard
applies) is kept. A sibling record of the same work does not resolve publication-object identity when the checked
source reuses the cited identifier in both the original-work role and a notice role (notice, EoC, correction or other
notice object), even when another sibling record provides a clean retraction event: the Stage 04 evidence model lacks
the publication-object context to prove the citation refers to the clean original. Same-work equality, a shared
original DOI/PMID, event type preference, title similarity and record ordering are not used to override the collision.
`ar-3351802` / `un-00059` and the other 52 measured pairs are a documented recall cost of dt-2; calling them "probable
true positives" is descriptive only and does not restore D-14. A future engine may revisit them only with independently
verified publication-object disambiguation evidence.

## D-074 — The historical P test verifies the historical freeze, not the current HEAD
- Status: accepted
- Topic: stage-04-historical-p-test
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: tests/stage04/test_step13_evaluation.py; tests/stage04/test_corrective_compat.py

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`. `test_frozen_check_passes_on_the_frozen_engine`
is obsolete in its applicability after D-071 superseded the first frozen engine. P
(`4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a`), commit `827ac1a`, the historical
PREREGISTRATION manifest, the Step 14 campaign, the frozen engine `b5bf8ed` and the failed campaign scores are not
changed. The repository HEAD is no longer required to equal the historical frozen engine. The Step 13 test code is
corrected to prove, from the historical git objects: P resolves to the exact accepted pre-registration files at
`827ac1a`; the manifest digest is unchanged; the frozen engine named by P is exactly `b5bf8ed`; the historical frozen
check succeeds on that historical frozen tree; the Step 14 campaign names and used that engine; the current dt-2 engine
has a different identity and does not satisfy the old assertion. No skip, xfail, deletion of the historical invariant,
change of P or weakening to "commit exists". P is identified by its historical commit and digest, not by requiring
every future HEAD to keep those files byte-identical. A new explicit test proves that freeze-2 uses the dt-2 engine
identity.

## D-075 — B-03: a clean original DOI keeps D-14 beside the same record's notice PMID
- Status: accepted
- Topic: stage-04-b03-original-doi-notice-pmid
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/corrective/census/B03_CENSUS.json; tests/stage04/test_corrective_role_collision.py

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`. The current B-03 behaviour is approved, the
mirror of D-058: for a citation with a clean, directly supported original-work DOI and a PMID that the same checked
record identifies as the notice PMID, the notice PMID does not invalidate the independently supported DOI attachment,
which may remain D-14 when the DOI is direct contract-valid support, has no unresolved role collision of its own, and
no D-6 identity-conflict witness, D-7 contradiction or earlier unresolved rule applies to the deciding evidence. The
notice PMID never counts as positive support, stays visible in evidence and provenance, and keeps the key-disagreement
and uncorroborated-pair warnings where they apply. No IDENTITY_CONFLICT is manufactured merely because one key is a
notice identifier of the same work. If the clean original-work identifier is absent, unavailable or itself
role-collided, D-14 is never recovered from the notice key. Explicit regression tests cover the boundary; the measured
snapshot pairs remain positive.

## D-076 — Freeze-2 accepted; corrective cycle closed; Step 13 (new pre-registration P2 only) authorized
- Status: accepted
- Topic: stage-04-freeze2-accepted
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/freeze-2/FREEZE_MANIFEST.json; docs/verification/stage-04/freeze-2/FREEZE_REPORT.md; docs/verification/stage-04/freeze-2/ATTESTATION.md; docs/verification/stage-04/corrective/CLOSURE.md

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP9UYHLzpXxFTSu95UPqEi99` (2026-11-19T09:28:37Z). The owner accepts Stage 04
freeze-2. The authoritative corrected Stage 04 frozen scientific engine is the content commit
`28ba6467c7005eec7bf51869974719a402059ca7`, tree `45c52da459b09597f105d6e4abd8ab00332c6799`, attestation
`6dab7f8ea1b97982dca978c38ca0fc8eea6e1a7f`, freeze manifest digest
`d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13`, exposure manifest v2 SHA-256
`b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b`. CI run 365 on the exact frozen-content commit and
CI run 366 on the attestation commit are accepted. Engine identity: engine 0.3.0, decision table dt-2, Stage 04 common
schema 4.0.0, claim schema 3.0.0, detector `citerift-dt1-detector/3 (dt-2)`. The superseded freeze
`b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` remains historical evidence only, marked SUPERSEDED_AFTER_FAILED_04_I. The
first pre-registration P and the failed Step 14 campaign remain immutable historical evidence and are not altered or
deleted. The performance target remains NOT_MET under D-066. The strict recall and abstention costs of D-072 and D-073
remain declared limitations. The corrective freeze cycle (D-071) is accepted and closed; Stage 04 remains IN_PROGRESS.

The same message authorizes Step 13 for a completely new pre-registration P2 for the corrected dt-2 engine only, in a
new versioned area, without overwriting the historical Step 13 files: no drand seed, no draw, no acquisition, no
annotation, no adjudication, no predictions and no Step 14. P2 pins the frozen identity above, excludes every article of
exposure manifest v2 (at article identity and again at capture), keeps D-070's listed-only tier unless new evidence
invalidates it, keeps gates G1 to G5 and the exact interval method, keeps D-067 and D-068, adds descriptive dt-2
role-collision and recall-withholding metrics, uses the corrected runner, updates baseline and sensitivity tooling to
dt-2, and commits to the first drand quicknet round at least one hour after the owner's future acceptance of P2. The
deliverable stops at P2, ready for owner acceptance.

## D-077 — Pre-registration P2 accepted; Step 14 under P2 authorized
- Status: accepted
- Topic: stage-04-p2-accepted
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/evaluation-p2/PREREGISTRATION.md; docs/verification/stage-04/evaluation-p2/PREREGISTRATION_MANIFEST.json

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP6Ugyq1ZbRyyuDXEcx5N7Bh` (2026-11-19, sent 12:16:15Z, stored 12:16:16Z).
The owner accepts the corrected-engine pre-registration P2 exactly as committed at
`10cc9d8267942d625d0d32a4b4b72101155c0d06`, canonical digest
`P2 = 5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a`; P2 is immutable. CI run 368 on that commit is
accepted as green. The frozen engine stays the freeze-2 content commit `28ba6467c7005eec7bf51869974719a402059ca7`
(tree `45c52da459b09597f105d6e4abd8ab00332c6799`, freeze manifest
`d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13`, exposure manifest v2
`b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b`; engine 0.3.0, dt-2, common schema 4.0.0, claim
schema 3.0.0, detector `citerift-dt1-detector/3 (dt-2)`).

Accepted as registered: the frames (ar S1 110 / S2 29, total 139; en S1 346 / S2 299, total 645) with the exposure-v2
exclusion, the 80 first-campaign articles permanently design-exposed and excluded, and the Stage 03 listed-only tier
eligible under D-070, no frame definition changing after acceptance; the sampling (per language 22 S1 + 8 S2 primary,
7 S1 + 3 S2 reserve, deterministic expansion blocks of 10, S1 then S2, targets of 40 identifier-reached truth-positive
and 75 negative-proxy units, at most 200 acquisition attempts), never altered after labels or predictions and never
enlarged because the historical evaluation failed G2; the gates G1 to G5 per language, all five required in both
languages, no threshold relaxed or reinterpreted; the annotation guide and label format, with `ambiguous_object` a
distinct record judgment that is never a correct attachment, annotators and adjudicator blinded to Stage 04 and every
label locked before the prediction run; metrics 8.8 and 8.9 as descriptive only (they never turn an abstention into a
positive, rescue G2 or G3, replace attachment precision or modify a gate), the "independently clean cited identifier"
definition for that descriptive analysis only, not weakening D-072; and the dt-2 limitations as declared (1,472 of
31,506; 800 lenient; 53 C-01 cases; 628 B-03 pairs under D-075; no notice-PMID rescue), not revisable in response to
the P2 result. The historical P (`4eded723…1098a`), its seed, draw, packets, labels, `RUN.json`, `SCORES.json`, report and
failed gate result stay immutable; the first campaign remains 04-I NOT PASSED for engine 0.2.0 / dt-1 and its
denominator is never combined with P2.

The same message authorizes Step 14 under P2 only: the seed round is the first drand quicknet round whose round time is
at least one hour after the timestamp of the acceptance message, fetched only under the registered mirror and
agreement protocol (a failure stops for an owner decision); then SEED.json committed, DRAW.json, acquisition with the
capture-time exposure recheck, packets, blinded A/B annotation, adjudication, label lock and its verification, the
single prediction run on frozen dt-2 with the corrected runner, scoring, baseline and sensitivity exactly under P2, and
the Step 14 report. After the draw nothing in the engine, P2, gates, draw or scoring changes; only the registered
replacement and expansion rules operate; a tooling or protocol defect not governed by P2 stops the campaign for an
owner decision. Step 15 is not authorized.

## D-078 — P2 seed round fixed at quicknet round 34096937
- Status: accepted
- Topic: stage-04-p2-seed-round
- Date: 2026-11-19
- Stage: 04
- Supersedes: none
- Evidence: docs/verification/stage-04/evaluation-p2/tools/p2_draw.py

Owner answer on decision card `cmsg_018VCB51nDHP6HXmLU4ea5yPMKB8XbkvvvLVJsfoATf2Nf` (tapped 2026-11-19T12:18:57Z, option
"Round 34096937 (13:16:15Z)"). The P2 acceptance message (D-077) carries two platform timestamps, sent 12:16:15Z and
stored 12:16:16Z, and the registered rule ("the first quicknet round at least one hour after the acceptance message")
selects round 34096937 (13:16:15Z) from the first and 34096938 (13:16:18Z) from the second. The owner fixes the seed
round at **34096937**, the round that the registered tool `p2_draw.py seed --acceptance-time 2026-11-19T12:16:15Z`
computes from the sent-at timestamp (round time exactly 3600 s after it). The decision was made at 12:18:57Z, before
either round existed, so it could not depend on the randomness. No other round is used; the mirror and agreement
protocol of P2 4.2 applies unchanged.
