# CITERIFT Engineering Governance

This file is the repository copy of the owner's standing rules (Master Plan
v1.0, Architecture v1.1, Engineering Governance Protocol v1.0, and the
Creative Differentiation rule), plus the mechanics that enforce them. Once
merged it is authoritative over conversation history.

## Authority

| Decision | Who | How it is recorded |
|---|---|---|
| Authorize a stage | Owner only | `NOT_STARTED -> AUTHORIZED`, actor `owner`, `owner_ref` to the owner's words |
| Withdraw an authorization | Owner only | `AUTHORIZED -> NOT_STARTED` |
| Start, block, implement, rework, verify | Stage executor (or owner) | transitions with evidence |
| Accept a verified stage | Owner only | `VERIFIED_AWAITING_OWNER_ACCEPTANCE -> ACCEPTED_CLOSED` |
| Reopen an accepted stage | Owner only | `ACCEPTED_CLOSED -> IN_PROGRESS` with a correction amendment |

Technical verification, owner acceptance and authorization of the next stage
are three separate decisions. Verifying a stage never unlocks its successor;
accepting a stage does not authorize the next one.

The engineering agent records owner decisions on the owner's behalf only after
the owner has stated them, and cites the statement in `owner_ref`. It never
infers approval from its own reports.

## Stage lifecycle

```
NOT_STARTED --owner--> AUTHORIZED --> IN_PROGRESS <--> BLOCKED
     ^                     |               |
     +------owner----------+               v
                                 IMPLEMENTED_NOT_VERIFIED --> (back to IN_PROGRESS)
                                           |
                                           v
                       VERIFIED_AWAITING_OWNER_ACCEPTANCE --> (back to IN_PROGRESS)
                                           |
                                         owner
                                           v
                                    ACCEPTED_CLOSED --owner + correction--> IN_PROGRESS
```

`citerift-gov transitions` prints the table. A transition is allowed only when
the edge exists, the actor may take it, and the resulting registry passes the
full consistency check (`citerift-gov check`). Main invariants:

1. A stage is verified only with every required artifact (always including the
   handoff), a passing test report produced at the verified revision from a
   clean tree, every acceptance gate passed, and (for engineering stages) a
   successful CI run on that revision. The report must record a complete run:
   every test file committed under `tests/` at the revision ran, with no
   narrowing option, ini override, other ini file or item dropped by a hook.
   Every file a gate cites must be hash-pinned (in the evidence manifest or
   under an owned path); a URL may be cited but does not count as pinned. The
   report is written by the test process itself, so code committed in a test
   or `conftest.py` file could still forge it (RISKS.md R-004).
2. A stage is accepted only from the verified state, by the owner, for the
   verified revision, citing an owner statement not already cited, by a history
   entry or an amendment, before the verification. One owner statement may
   cover several decisions made at the same time (for example accepting one
   stage and authorizing the next); that is allowed.
3. A stage can be authorized, verified or accepted only when all of its
   dependencies are accepted at that moment. A dependency that is reopened for
   a correction is reported (`DEPENDENCY_REOPENED`) until it is accepted again.
4. At most one engineering-agent stage is active (AUTHORIZED, IN_PROGRESS,
   BLOCKED or IMPLEMENTED_NOT_VERIFIED) at a time.
5. The recorded status equals the status obtained by replaying the history,
   each record matches the history entry that created it, and every history
   entry satisfies, at its own time, invariants 3 and 4, the blocker rules,
   and the reopening rule: a reopening cites a correction amendment recorded
   before it and not used by an earlier reopening. Amendment and blocker ids
   are unique.
6. Verified evidence is immutable: every file in the stage's verification
   directory (except files git ignores), the stage definition and the policy
   are pinned by hash at verification, and the content of the stage-owned
   paths must equal the verified revision unless an amendment covers the
   change. Only an enhancement amendment's test report may be added to the
   directory later, and it is hash-checked. Line endings are fixed by the root
   `.gitattributes`; a nested `.gitattributes` is an error.
7. A verified or accepted stage has no open blocker and no open critical defect
   (a critical defect with `Stage: project` blocks every stage). An entry
   heading that does not parse, or an entry field (`Status`, `Severity`,
   `Kind`, `Topic`) outside a recognized heading, is an error. An entry written
   in some other form entirely (for example as a table row) is not recognized
   and not reported.

## Per-stage deliverables

Every engineering stage produces, in `docs/verification/stage-NN/`:
`SPECIFICATION.md`, `MATHEMATICAL_MODEL.md`, `RISK_ANALYSIS.md`,
`SIMULATION_REPORT.md`, `TEST_RESULTS.md`, `CREATIVE_DIFFERENTIATION_REVIEW.md`,
`HANDOFF.md` and `test-report.json`. The registry schema fixes this list for
engineering stages. The handoff must contain the sections listed in the
registry policy and cite the verified commit.

Acceptance gates for Stages 02 to 09 are the Master Plan v1.0 acceptance gates.
Each stage refines them into detailed gates when its specification is approved,
before implementation starts.

## Changing an accepted stage

- Correction (behavior or contract change): record a `correction` amendment
  with evidence, the owner reopens the stage, and it is verified and accepted
  again.
- Enhancement that preserves contracts: record an `enhancement` amendment with
  the new revision and a passing test report at that revision. The stage stays
  accepted.

## Engineering method

Specification, mathematical analysis, risk analysis, simulation, approval,
limited implementation, testing, regression, documentation, verified handoff.
Audit before modifying; make the smallest effective change; fix root causes;
preserve verified work and a recoverable revision; never weaken a test or a
gate to obtain a pass. Prefer minimum complexity; MCP stays optional.

## Honesty rules

- Never invent results, tests, commits, files, external states or findings.
- Keep simulated results separate from empirical results.
- A retracted citation is never automatically a false claim.
- Never claim full Wikipedia coverage without evidence.
- Separate verified fact, assumption and recommendation.
- Every final stage report ends with exactly one of: `VERIFIED COMPLETE`
  (Prompt 02 wording for a stage: `VERIFIED — AWAITING OWNER ACCEPTANCE`),
  `BLOCKED — EVIDENCE PROVIDED`, `NOT VERIFIED`.

## Project identity and attribution

CITERIFT is presented as "CITERIFT — Created and Directed by EVE TELOS · IM"
(owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPGk43kowXCxBqhPw9S7z5df`). Every
stage follows docs/identity.md and OWNERSHIP.md: EVE TELOS stays the prominent
creator identity, IM is a secondary signature, the founder's legal name is not
put in public materials, AI tools are disclosed as tools and never presented as
owner or creator, and historical attribution is never rewritten.

## Owner approval needed before

Starting another stage, destructive changes, deleting data, security changes,
paid services, publishing externally, editing Wikipedia, changing the research
objective or architecture, granting new permissions.

## What is enforced technically, and what is not

Prevented (the tool refuses to write it): a transition that is not in the
table, an owner decision taken by another actor or without an `owner_ref`, a
transition while the resulting registry has any consistency error, and a
blocker or amendment that would add an error. Errors that already exist do not
block a blocker or amendment, so that the problem can be recorded; they stay
reported. These controls bind only writers who use `citerift-gov`.

Detected (reported by `citerift-gov check`, run in CI on every push and pull
request): hand edits that break invariants 1 to 7, the registry schema (which
also fixes the policy values, the artifact list and the CI requirement of
engineering stages, and that only Stage 01 is external), decision and risk
record consistency, duplicate JSON keys, recorded times more than 5 minutes
ahead of the checking machine's clock, and a `PROJECT_STATUS.md` that does not
match the registry. Detection is not prevention: a hand edit can be committed,
and it is reported when `check` runs from an honest copy of the code. A stage's
own definition (gates, suites, owned paths, verification directory) can still
be changed before it is verified; that change shows only in the reviewed diff
of the registry.

Protection of `main` is defined in `.github/rulesets/main-protection.json`
(pull request required, `ci-gate` must pass, merge commits only, no
force-push, no deletion, no bypass) and is active on GitHub (read it back with
`gh api repos/ImanOthman-eng/citerift/rulesets`). It does not make CI
independent: `ci-gate` is defined by a workflow that the gated pull request can
change, and 0 approvals are required (RISKS.md R-016). The workflow and the
ruleset file are Stage 00 owned paths, so changing them makes Stage 00 stale
(detection only). CI runs the checked-out `src/` modules (`python -P` with
`PYTHONPATH=src`) and checks that the package is imported from the checkout,
so changing the entry points in `pyproject.toml` does not replace the checker.
The dependencies installed from `uv.lock` are not Stage 00 owned paths and run
in the same process; a change to them can still change what CI executes.

Not enforceable by repository code: whether an `owner_ref` really contains the
owner's approval (R-002), whether an agent follows instructions at all, and
whether a forgery that is consistent everywhere (history, records, evidence
and hashes rewritten together) is genuine (R-003). The agent acts under the
owner's GitHub account (R-001). Prevention of these needs a required review
from an identity the agent does not hold (D-006 or a bot account). These
remain owner judgment.
