# CITERIFT Ownership, Authority and Attribution

**CITERIFT — Created and Directed by EVE TELOS · IM**

This file records who owns and directs CITERIFT, who decides, and how the work
of people and AI tools is attributed. It is a project record, not a legal
instrument.

## Owner and research director

| Role | Identity |
|---|---|
| Creator, owner and research director | EVE TELOS (public identity) |
| Founder signature | EVE TELOS · IM |
| Repository owner account | GitHub `ImanOthman-eng` (owns `ImanOthman-eng/citerift`, administrator) |
| Project | CITERIFT |

EVE TELOS conceived CITERIFT, set its research question, and directs its
scope, architecture and acceptance decisions. The association between the
public identity EVE TELOS and the legitimate owner is the GitHub account
`ImanOthman-eng`, which owns the repository and holds its administrative
permissions. The standard for using these names is in
[docs/identity.md](docs/identity.md).

## Decision authority

Only the owner authorizes a stage, accepts a verified stage, reopens an
accepted stage, chooses the license, and approves publication, security
changes, paid services and merges to `main` (GOVERNANCE.md, "Authority").
Every owner decision recorded in `governance/stage_registry.json` cites the
owner's own words in `owner_ref`, so each one can be traced to its source.
These references are attested, not cryptographically verified (RISKS.md R-002,
DECISIONS.md D-005); signed owner acceptance is option D-006.

Code owner of every path: `.github/CODEOWNERS`.

## Original research contributions

The owner set the research question (*how consistently and how quickly do
different Wikipedia language editions respond to scientific paper
retractions?*), the project concept, the stage plan (Master Plan v1.0), the
architecture (Architecture v1.1), the engineering governance protocol, the
creative differentiation rule and the identity standard, in the owner's
messages that GOVERNANCE.md cites. Each later stage records which
results come from data, which from simulation, and which from models.

## AI-assisted engineering

CITERIFT is built with AI engineering assistance. AI coding agents (Claude Code)
write code, tests and documentation under the owner's direction. They are tools:
they are not owners, authors of the research direction, or decision-makers, and
they cannot accept their own work.

How this is recorded, truthfully:

- **Commit authorship.** A commit made by an AI agent carries the agent
  identity that its execution environment sets, and that environment signs it.
  It is never recorded as the owner's own work. Commits the owner makes carry
  the owner's identity.
- **Commit disclosure.** A commit an AI agent made or helped with ends with the
  trailer `Assisted-by: Claude Code (AI coding agent)`. Session links and
  promotional lines are not added (CLAUDE.md, DECISIONS.md D-018).
- **Pull requests.** Each pull request names who requested it and ends with
  the line `AI-assisted: prepared with Claude Code (AI coding agent) under the
  direction of EVE TELOS · IM.`
- **Final report and submission.** AI assistance is disclosed in the Stage 09
  research report and the Devpost submission (docs/sources-and-attribution.md,
  rule 7).
- **History.** Existing commits and their metadata are never rewritten.

Known limitation (RISKS.md R-001): the agent's GitHub actions (pushes, pull
requests, merges) run under the owner's GitHub account, so GitHub alone cannot
tell an agent action from an owner action. The commit author identity and the
recorded `owner_ref` are how the two are told apart.

## Copyright and license

No license has been chosen (DECISIONS.md D-007). Until one is added, no reuse
rights are granted. Nothing in this repository registers a copyright or a
trademark, and the founder signature and monogram are not legal proof of
authorship or ownership; they are a naming convention. Copyright questions
about AI-assisted work depend on jurisdiction and are for the owner to resolve
with qualified advice if needed.

## Release provenance

Not yet in place; planned for Stage 09 and subject to owner approval:
owner-signed release tags (see D-006 for the signing approach) and release
notes that list the verified revision of each stage.
