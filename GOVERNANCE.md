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
   successful CI run of the project's repository on that revision (the run
   URL must be exactly `https://github.com/<repository>/actions/runs/<id>`). A
   clean tree has no change that `git status` shows, no tracked file flagged
   `--skip-worktree` or `--assume-unchanged`, and no tracked file whose bytes
   differ from its index entry (read from disk, not from git's stat cache);
   the report is left out of that check only when it is written to an
   untracked path. These are checks of the working tree by the test process;
   code in that process can still forge the report (RISKS.md R-004). The report must record
   a complete run: every test file committed under `tests/` at the revision
   ran; every test passed (none skipped or expected to fail); no narrowing
   option, ini override or other ini file was used; the collection settings
   (`python_files`, `python_classes`, `python_functions`, `testpaths`) had
   their fixed values; no collected test was dropped or repeated by a hook; no
   extra plugin was loaded with `-p` or `PYTEST_PLUGINS`; and every conftest
   the run loaded is committed at the revision. Every file a gate cites must be
   hash-pinned: in the evidence manifest, or under an owned path and committed
   at the verified revision. It must be named by a plain path with no `..`,
   `.` or symbolic link; a URL may be cited but does not count as pinned.
   These rules make an honest narrowing visible. They do not bind code that
   runs inside the test process: committed test or conftest code, an
   untracked or ignored file the run imports (inside the tree or outside it),
   or an installed dependency can write a false report (RISKS.md R-004).
2. A stage is accepted only from the verified state, by the owner, for the
   verified revision, citing an owner statement not already cited, by a history
   entry or an amendment, before the verification. One owner statement may
   cover several decisions made at the same time (for example accepting one
   stage and authorizing the next); that is allowed.
3. A stage can be authorized, verified or accepted only when all of its
   dependencies are accepted at that moment. Each stage's dependency list is
   fixed by the registry schema (D-010), so it cannot be shortened first. A dependency that is reopened for
   a correction is reported (`DEPENDENCY_REOPENED`) until it is accepted again.
4. At most one engineering-agent stage is active (AUTHORIZED, IN_PROGRESS,
   BLOCKED or IMPLEMENTED_NOT_VERIFIED) at a time.
5. The recorded status equals the status obtained by replaying the history,
   each record matches the history entry that created it, and every history
   entry satisfies, at its own time, invariants 3 and 4, the blocker rules (an
   open blocker for a block, none for start, unblock, verification or
   acceptance), and the reopening rule: a reopening cites a correction amendment recorded
   before it and not used by an earlier reopening. Amendment and blocker ids
   are unique.
6. Verified evidence is immutable: every file in the stage's verification
   directory (except files git ignores), the stage definition and the policy
   are pinned by hash at verification, and the content of the stage-owned
   paths must equal the verified revision unless an amendment covers the
   change. Only an enhancement amendment's test report may be added to the
   directory later, and it is hash-checked. Line endings are fixed by the root
   `.gitattributes`; a nested `.gitattributes` is an error. Git is run with
   replace refs and grafts disabled.
7. A verified or accepted stage has no open blocker and no open critical defect
   (a critical defect with `Stage: project` blocks every stage). Entry ids and
   `Stage` values use ASCII digits; other digits (Arabic-Indic, fullwidth) are
   errors, because they would never match a stage id. A heading that
   looks like an entry heading but does not parse, an entry field (`Status`,
   `Severity`, `Kind`, `Topic`) outside a recognized heading, and an entry
   field written in any form other than `- Name: value` (bold, another case,
   indented, another bullet) are errors. Topics are compared without case,
   separators, invisible characters, or Arabic tatweel and short-vowel marks. An entry written in some other form
   entirely (for example as a table row, or with neither a recognizable
   heading nor recognizable fields) is not recognized and not reported.

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

- Every amendment is recorded while its stage is accepted; `check` reports one
  dated when the stage was not (`AMENDMENT_NOT_APPLICABLE`). Only enhancements
  of the current acceptance can cover changes to the stage's owned paths.
- Correction (behavior or contract change): record a `correction` amendment
  with evidence, the owner reopens the stage, and it is verified and accepted
  again.
- Enhancement that preserves contracts: record an `enhancement` amendment with
  the new revision, a passing test report at that revision and an owner
  statement not cited before (not even in the same second). The stage stays
  accepted. If it changes a
  contract schema under the stage's owned paths, the schema's
  `x-citerift-version` must increase and every valid contract fixture of the
  accepted revision must stay valid. Whether the change preserves the
  contracts' meaning (for example, that no value means "not retracted") is
  decided by the owner's approval and by the tests at the new revision; an
  enhancement has no CI record of its own.

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
table, an owner decision recorded with another actor or without an `owner_ref`
(the actor is a command-line flag that any writer can pass, so the reference
is the real control, R-002), a
transition while the resulting registry has any consistency error, and a
blocker or amendment that would add an error. Errors that already exist do not
block a blocker or amendment, so that the problem can be recorded; they stay
reported. These controls bind only writers who use `citerift-gov`.

Detected (reported by `citerift-gov check`, run in CI on every push and pull
request): hand edits that break invariants 1 to 7, the registry schema (which
also fixes the policy values, the artifact list and the CI requirement of
engineering stages, that only Stage 01 is external, and every stage's
dependencies), decision and risk
record consistency, duplicate JSON keys, recorded times more than 5 minutes
ahead of the checking machine's clock, and a `PROJECT_STATUS.md` that does not
match the registry, and amendments dated when their stage was not accepted.
Detection is not prevention: a hand edit can be committed,
and it is reported when `check` runs from an honest copy of the code. A stage's
own definition (gates, suites, owned paths, verification directory) can still
be changed before it is verified; that change shows only in the reviewed diff
of the registry. Its executor, artifact list and dependencies cannot.

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
Before any Python runs, a shell step refuses anything in `src/` beside the
`citerift` package (such as a `sitecustomize.py` or a package that shadows a
dependency), and `check` reports one as `SRC_FOREIGN_MODULE`. Before the
governance check, CI installs only the locked dependencies, as wheels and
without the project (`uv sync --frozen --no-install-project --no-build`), so
no build backend named in `pyproject.toml` runs yet. The check then runs
before the lock check, the project install, ruff, mypy and pytest, because a
build backend or a tool setting in `pyproject.toml` can run code (a mypy
plugin, for example), and such code could rewrite the checker on disk before a
later step. After the tests, CI checks its own test report
(`citerift-gov check-report`) and fails if `git status` shows any change: an
unstaged or staged change to a tracked file, or a new file other than the
test report. The dependencies installed from `uv.lock` and everything in
`pyproject.toml` are not Stage 00 owned paths. Code in the locked wheels (a
`.pth` file, for example) already runs during the governance check; code from
the build backend and tool settings runs after it and can still change what
the test, report and tree-check steps do (including restoring the files it
changed). Later stages must be able to add dependencies. Such code must be
committed or locked, so it is visible in the reviewed diff.

Not enforceable by repository code: whether an `owner_ref` really contains the
owner's approval (R-002), whether an agent follows instructions at all, and
whether a forgery that is consistent everywhere (history, records, evidence
and hashes rewritten together) is genuine (R-003). The agent acts under the
owner's GitHub account (R-001). Prevention of these needs a required review
from an identity the agent does not hold (D-006 or a bot account). These
remain owner judgment.
