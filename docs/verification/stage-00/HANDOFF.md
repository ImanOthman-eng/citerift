# Stage 00 Handoff: Engineering Foundation (correction A-00-001)

## Stage and status

- Stage: 00, Engineering Foundation. Executor: engineering agent.
- Authorized by the owner on 2026-10-25 (`cmsg_018VCB51nDHP6HXmLU4ea5yPPJtDk4V58km8PBjZzdYKEV`),
  verified at `741476c` and accepted. Reopened by the owner for the
  corrective amendment A-00-001
  (`cmsg_018VCB51nDHP6HXmLU4ea5yPXk8eZcAUfir9fZgszrLxhk`, history entry 11).
- Corrected revision: `0c21182e5871f772c3a76c75a1217c7641a63bbb`, recorded as
  the implementation revision (`IMPLEMENTED_NOT_VERIFIED`).
- On 2026-10-26 the owner asked for a bounded independent review of the last
  three fixes (R5-01 to R5-03) and for the verification transition to be
  applied only if every requirement is demonstrated
  (`cmsg_018VCB51nDHP6HXmLU4ea5yP3BFvQvWtWFp37ndPPex2k9`). That review, at
  `0c21182`, returned **VERIFIED** with no new confirmed defect
  (`review/0c21182/report.md`). This package is the evidence for the
  verification transition `IMPLEMENTED_NOT_VERIFIED` →
  `VERIFIED_AWAITING_OWNER_ACCEPTANCE`, which the orchestrator records after
  this package is committed (see Verified Git commit).
- The stage is **not** accepted. Acceptance, and the risk decision in
  RISK_DECISION_PACKAGE.md, are the owner's. No later stage is authorized.

## Verified completed work

Gate status. "Pass" means the evidence named was produced and inspected; it
does not mean the owner accepted it. Every cited file is in this directory or
is a Stage 00 owned file committed at the revision.

| Gate | Requirement | Result | Evidence |
|---|---|---|---|
| 00-A | Repository initialized safely with verified Git revision | pass | no history rewritten, no force push; every change on `claude/project-thread-84z62e` (PR #2), merge commits only; `0c21182` in the branch history (this file) |
| 00-B | Reproducible engineering environment | pass | `uv.lock` unchanged since `741476c`; both CI test reports (404 of 404 on 3.12.3 and 3.13.14); the handoff simulation's clean-clone install (`handoff/results-0c21182.json`) |
| 00-C | Operational Project Orchestrator | pass | TEST_RESULTS.md §1, §3; SPECIFICATION.md |
| 00-D | Persistent Project Memory | pass | TEST_RESULTS.md §1 to §3; handoff simulation points 3 and 10 |
| 00-E | Orchestrator-Memory integration | pass | TEST_RESULTS.md §2 |
| 00-F | Validated stage-transition rules | pass | SIMULATION_REPORT.md; MATHEMATICAL_MODEL.md; `simulation/replay-conformance-full.json` (0 disagreements); TEST_RESULTS.md §5 |
| 00-G | Versioned data contracts with positive and negative tests | pass | contracts 1.0.1, `schemas/contracts/v1/`; 3 valid fixtures, 52 invalid cases; TEST_RESULTS.md §1 |
| 00-H | Completed relevant pre-implementation simulations | pass | SIMULATION_REPORT.md; `simulation/model-results.json` |
| 00-I | Successful unit and integration tests | pass | `test-report.json`: unit 29, integration 141 |
| 00-J | Successful regression and consistency tests | pass | `test-report.json`: regression 214; fail-first runs (`fail-first/README.md`); `check` 0 errors |
| 00-K | Successful GitHub Actions verification | pass | push run 40273320614 and pull_request run 40273323339 at `0c21182`, all jobs and steps green (TEST_RESULTS.md §7) |
| 00-L | Effective branch protection verified | pass | ruleset 25824038 read back active and equal to the file (TEST_RESULTS.md §8) |
| 00-M | Security and adversarial review completed | pass | RISK_ANALYSIS.md; six independent reviews (`review/README.md`, TEST_RESULTS.md §9); the last, bounded to the R5 fixes, VERIFIED (`review/0c21182/report.md`); trust-boundary items put to the owner in RISK_DECISION_PACKAGE.md |
| 00-N | Creative Differentiation Review completed | pass | CREATIVE_DIFFERENTIATION_REVIEW.md |
| 00-O | Reproducible Stage 00 documentation and handoff | pass | this package; handoff simulation 12 of 12; requirements traceability in TRACEABILITY.md |
| 00-P | No known unresolved critical foundational defect | pass | no review found a critical defect; every reproduced finding is fixed; no open critical defect in RISKS.md |

## Inputs and outputs

Inputs: the accepted Stage 00 at `741476c`; the owner's correction
instruction (`cmsg_018VCB51nDHP6HXmLU4ea5yPXk8eZcAUfir9fZgszrLxhk`); the
independent audit of 2026-10-25 (`docs/audits/stage-00-2026-10-25/`); the
six review reports in `review/`; the owner's final verification instruction
(`cmsg_018VCB51nDHP6HXmLU4ea5yP3BFvQvWtWFp37ndPPex2k9`). No external data was read or written. No
Stage 01 finding was used.

Outputs, all in the repository: the corrected orchestrator, memory and
contracts (`src/citerift/`, `schemas/`), data contracts 1.0.1
(`docs/data-contracts.md`), the replay-conformance simulation
(`simulations/stage00/replay_conformance.py`), 404 tests (`tests/stage00/`),
the CI workflow (`.github/workflows/ci.yml`), this package, and the updated
GOVERNANCE.md, RISKS.md (R-016 to R-021), DECISIONS.md and CHANGELOG.md. The
project identity work (OWNERSHIP.md, `docs/identity.md`, CODEOWNERS) is on the
same pull request and does not touch a Stage 00 owned path.

## Test evidence

- `test-report.json` (3.12.3) and `test-report-python3.13.json` (3.13.14):
  from CI run 40273320614 at `0c21182`, clean tree, complete selection, 404
  collected, 404 passed; copied unchanged (TEST_RESULTS.md §1).
- Fail-first: each review's findings fail on the revision reported against
  (82, 36, 46, 27, 7 and 4 failing tests; TEST_RESULTS.md §3).
- Mutation: TEST_RESULTS.md §5.
- Simulation: model and conformance outputs byte-identical at `0c21182`;
  handoff simulation 12 of 12 (TEST_RESULTS.md §6).
- Static checks and dependency audit clean in CI (TEST_RESULTS.md §4).

## Known limitations

From RISKS.md and RISK_ANALYSIS.md §4, stated plainly:

- The agent acts under the owner's GitHub account (R-001), and owner
  references are not machine-read (R-002). Hand edits are detected, not
  prevented; a consistent forgery is not detected (R-003).
- The test report and CI record are written by the agent's own processes.
  Code inside the test process can forge the report; the CI record is
  checked offline for form, not fetched (R-004).
- CI is not independent of the change it gates, and code reaching uv through
  unowned inputs (locked wheels, `.python-version`, uv settings) runs during
  the governance check (R-016).
- Each open-ended review round found new low-severity variants of earlier
  findings; the bounded review of the last fixes found none (R-021). A
  further open-ended round may find more.
- These trust-boundary items (R-001 to R-004, R-016) cannot be closed by
  repository code. They are not accepted by this package or by the
  verification transition; RISK_DECISION_PACKAGE.md puts them to the owner
  as one decision, with alternatives and a recommendation.
- Contract compatibility is checked against fixtures (R-005); identifier
  formats stay permissive until real data (R-006). No license is chosen
  (D-007).

## Open blockers

None. B-00-001 and B-00-002 were resolved on 2026-10-25.

## Dependency versions

`uv.lock` sha256 `52980fe6641ddd859ea3f93750e4bf348df47eccf4695adc610cb24bd164fe50`,
unchanged since `741476c`:

| Package | Version | Role |
|---|---|---|
| Python | 3.12.3 and 3.13.14 (CI), 3.12.3 (local) | `requires-python >=3.12,<3.14` (D-001) |
| jsonschema | 4.26.0 | runtime |
| referencing | 0.37.0 | runtime |
| jsonschema-specifications | 2025.9.1 | runtime |
| rpds-py | 2026.9.1 | runtime |
| attrs | 26.1.0 | runtime |
| pytest | 9.1.1 | development |
| ruff | 0.17.2 | development |
| mypy | 2.4.0 | development |
| pip-audit | 2.10.1 | development |
| uv | 0.11.32 | tooling (pinned in CI) |

CI actions are pinned to commit SHAs.

## Verified Git commit

`0c21182e5871f772c3a76c75a1217c7641a63bbb` on branch
`claude/project-thread-84z62e` in <https://github.com/ImanOthman-eng/citerift>
(PR #2): the commit both green CI runs tested. The commits after it change
only this directory, the registry and PROJECT_STATUS.md, none under a Stage 00
owned path. PR #2 must be merged with a merge commit so the cited commits stay
in `main`'s history.

Dry run of the verification transition with `verification-record.json` (all
sixteen gates and the CI record of push run 40273320614):

```
$ uv run citerift-gov transition 00 VERIFIED_AWAITING_OWNER_ACCEPTANCE --actor engineering-agent \
    --revision 0c21182e5871f772c3a76c75a1217c7641a63bbb \
    --record docs/verification/stage-00/verification-record.json --reason "..."
Transition stage 00 -> VERIFIED_AWAITING_OWNER_ACCEPTANCE: ALLOWED
Dry run: nothing written. Re-run with --apply to record it.
```

Run on 2026-10-26 after the implementation revision was recorded, and again
after each change to this package. The orchestrator checked the seven
artifacts, the handoff sections, the cited revision, both test reports, every
gate and its pinned evidence, and the CI record, and raised nothing. After
the bounded review returned VERIFIED and this package was committed, the same
command was run with `--apply`; the registry and PROJECT_STATUS.md record it.

## Acceptance decision

Requested from the owner, as one decision on the whole correction set and on
RISK_DECISION_PACKAGE.md. The orchestrator refuses acceptance from any actor
but the owner. The owner can:

- accept Stage 00 at revision `0c21182` together with option A of the risk
  package: the agent then records the acceptance with
  `--actor owner --owner-ref <that message>`;
- choose another option of the risk package; or
- reject or ask for rework.

Merging PR #2 is a separate owner approval, with a merge commit only.

Also pending, not blocking: license (D-007) and owner-signed acceptance
(D-006).

## Requirements for the next stage

- **No stage after 00 is authorized.** Accepting Stage 00 authorizes nothing;
  Stages 02 and 03 each need their own owner authorization, refused until
  Stages 00 and 01 are accepted.
- Stage 01 belongs to the external feasibility agent; nothing here assumes its
  findings.
- A later stage that needs a contract change follows `docs/data-contracts.md`:
  new schemas outside `v1/` that `$ref` the v1 definitions, or an
  owner-approved enhancement amendment.
- Session start for any later work: `uv sync --locked`,
  `uv run citerift-gov recover`, `uv run citerift-gov check`.
