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

1. A stage is verified only with every required artifact, a passing test report
   produced at the verified revision from a clean tree, every acceptance gate
   passed with existing evidence, and (for engineering stages) a successful CI
   run on that revision.
2. A stage is accepted only from the verified state, by the owner, for the
   verified revision.
3. A stage can be authorized only when all of its dependencies are accepted.
4. At most one engineering-agent stage is active (AUTHORIZED, IN_PROGRESS,
   BLOCKED or IMPLEMENTED_NOT_VERIFIED) at a time.
5. The recorded status equals the status obtained by replaying the history.
6. Verified evidence is immutable: changing an evidence file, or committing a
   change to a stage-owned path without an amendment, makes the stage stale.
7. A verified or accepted stage has no open blocker and no open critical defect.

## Per-stage deliverables

Every engineering stage produces, in `docs/verification/stage-NN/`:
`SPECIFICATION.md`, `MATHEMATICAL_MODEL.md`, `RISK_ANALYSIS.md`,
`SIMULATION_REPORT.md`, `TEST_RESULTS.md`, `CREATIVE_DIFFERENTIATION_REVIEW.md`,
`HANDOFF.md` and `test-report.json`. The handoff must contain the sections
listed in the registry policy and cite the verified commit.

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

## Owner approval needed before

Starting another stage, destructive changes, deleting data, security changes,
paid services, publishing externally, editing Wikipedia, changing the research
objective or architecture, granting new permissions.

## What is enforced technically, and what is not

Enforced (by `citerift-gov check` and CI): everything in "Stage lifecycle"
above, registry schema, decision and risk record consistency, and that
`PROJECT_STATUS.md` matches the registry. Protection of `main` is defined in
`.github/rulesets/main-protection.json` (pull request required, `ci-gate` must
pass, merge commits only, no force-push, no deletion, no bypass). Whether it is
active on GitHub is recorded in the Stage 00 verification records; read it back
with `gh api repos/ImanOthman-eng/citerift/rulesets`.

Not enforceable by repository code: whether an `owner_ref` really contains the
owner's approval (R-002), whether an agent follows instructions at all, and
whether a hand-forged but fully consistent history is genuine (R-003). The
agent acts under the owner's GitHub account (R-001). These remain owner
judgment.

## Session start procedure

1. `uv sync --locked`
2. `uv run citerift-gov recover` (state, open items, next authorized action)
3. `uv run citerift-gov check` (must report 0 errors)
4. Read DECISIONS.md and RISKS.md entries relevant to the task.
5. Work only on what the owner authorized in the current instruction.
