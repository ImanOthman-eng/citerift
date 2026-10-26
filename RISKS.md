# CITERIFT Risks, Known Defects and Limitations

Persistent Project Memory: risk register. Format (checked by
`citerift-gov check`): `## R-NNN — Title`, then `Status` (open, mitigated,
accepted, closed), `Severity` (critical, high, medium, low), `Kind` (risk,
defect, limitation) and `Stage` (two-digit ids, comma separated, or
`project`). An open critical defect on a stage blocks its verification.
Likelihoods are qualitative judgments, not measured probabilities.

## R-001 — The engineering agent acts under the owner's GitHub identity
- Status: open
- Severity: high
- Kind: risk
- Stage: project
- Owner: project owner

Verified 2026-10-25: GitHub reports the agent's session user as ImanOthman-eng.
Merges, approvals and commits made by the agent are indistinguishable on GitHub
from the owner's own. Mitigations: owner decisions require an `owner_ref` to
the owner's own words (D-005); the branch ruleset has no bypass actors and
requires the `ci-gate` check (D-011). That check does not stop the agent: the
workflow that defines `ci-gate` can be changed by the pull request it gates,
and the ruleset requires 0 approvals, so the same account can merge such a
change (R-016; independent review 2026-10-25, F-20). Full mitigation needs a
required review from an identity the agent does not hold: D-006 (owner-signed
acceptance) or a separate bot identity, both owner decisions.

## R-002 — Owner references are not machine-verified
- Status: open
- Severity: high
- Kind: limitation
- Stage: 00

The orchestrator checks that an owner decision cites a reference and that the
acceptance record matches the history, but it cannot read the reference. A
dishonest writer could cite a message that does not say what is claimed. An
acceptance must cite a reference not cited by history or an amendment before
the verification (OWNER_REF_REUSED); otherwise one reference may back several
decisions, because one owner message can accept a stage and authorize the next.
The owner should check the `owner_ref` of each acceptance in the history.

## R-003 — Registry files can be edited by hand
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

Detection, not prevention. `citerift-gov check` reports a hand edit that
breaks any rule a transition is checked against. Since correction A-00-001
(independent review 2026-10-25) that includes: each history entry checked at
its own time (single active stage, dependencies, a correction amendment
recorded before a reopening and used once, blockers); records that do not match
the history entry that created them; duplicate amendment or blocker ids; an
acceptance citing an owner reference used before the verification; every file
in the verification directory (except files git ignores), the stage definition
and the policy pinned by hash; policy values, the engineering artifact list and
the executor and dependencies of each stage fixed in the registry schema;
owned-path content compared with the verified revision; duplicate JSON keys
rejected; an amendment citing an owner reference cited before, or recorded
when its stage was not accepted (Y-06, Y-07); entry ids and stage numbers in
non-ASCII digits (Y-04).

What it cannot detect: a forgery that is consistent everywhere, that is,
history, records, evidence files and their recorded hashes rewritten together
by anyone with write access. Test reports and CI records are also
self-reported files: the checker verifies their content and hashes, not who
produced them (R-004). Detection happens when someone runs `check` from an
honest copy of the code; CI runs it on every push, but CI itself can be
changed by the gated change (R-016). Stage definitions (gates, suites, owned
paths, verification directory) can still be edited before a stage is verified;
that edit shows only in the reviewed diff of `governance/stage_registry.json`.
Executors, artifact lists and dependencies cannot (V-03, X-07).

## R-004 — CI evidence in the registry is entered by the agent
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

The offline check verifies that the recorded CI record names a run of this
repository (the URL must be exactly the project's run URL pattern, ASCII
letters compared without case, so dot
segments cannot lead elsewhere; Y-10, Z-02), the verified revision as its
tested commit, and success. It
cannot fetch the run, so it cannot tell whether the record is true; the run
URL is public for this repository and can be checked by anyone. A
`pull_request` run tests the merge commit, not the head commit it reports, so
the CI record should cite the `push` run. The required
`ci-gate` check on `main` is a control on the honest workflow only; it is not
independent of the change it gates (R-016). The test report is written by the
test process. The checker rejects the narrowing an honest run can show:
narrowing options, ini overrides, another ini file, changed collection
settings, dropped or repeated tests, skipped or expected-to-fail tests, extra
`-p` or `PYTEST_PLUGINS` plugins, conftest files not committed at the
revision, and committed test files that did not run (V-01, X-02, X-03, Y-03).
A tree is dirty when `git status` shows a change, when a tracked file is
flagged `--skip-worktree` or `--assume-unchanged`, when a tracked file's bytes
differ from its index entry although git's stat cache says they do not, or
when the report itself is written over a tracked file, whatever its name;
local settings that tell `git status` to ignore submodule changes are
overridden (Y-01, Y-02, Z-01, Z-05, R5-02). Local git state outside these checks, such as
`.git/info/exclude` hiding a new file, an index rewritten together with
the files, or index flags and settings inside a submodule's own repository
(found by the review of the R5 fixes; the repository has no submodule), is not
bound. It cannot bind code that runs
inside the test process: committed test or conftest code, an untracked or
ignored module the run imports (inside the tree or outside it), or an
installed dependency can rewrite the report or the plugin's state, and a
writer can edit a report after the run. In CI the checkout is fresh, so such code must be committed
or come from `uv.lock`, and a reviewer can see it in the diff.

## R-005 — Contract compatibility is checked against fixtures, not proven
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

`check_backward_compatible` shows that every valid fixture of the old version
validates under the new one. It does not prove the new schema accepts every
record the old one did. More fixtures from real data (Stages 02 to 05) make the
check stronger.

## R-006 — Contract field formats are not yet validated against real data
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00, 02, 03

DOI, PMID, wiki language codes and revision ids are deliberately permissive
until Stages 02 and 03 verify real formats. Tightening them is expected as a
backward-compatible minor version where possible.

## R-007 — Stage 01 findings are not delivered or accepted
- Status: open
- Severity: high
- Kind: risk
- Stage: 01, 02, 03

Stages 02 and 03 depend on Stage 01 acceptance. The owner reports the external
investigation was reported, but no handoff is in this repository and no finding
is accepted. Nothing in Stage 00 assumes its results.

## R-008 — Wikimedia API rate limiting
- Status: open
- Severity: medium
- Kind: risk
- Stage: 03, 05, 07

Observed 2026-10-25 from this environment: HTTP 429 from Wikimedia's edge even
on first requests, succeeding after honoring Retry-After. Data stages need
throttling, retry with backoff, caching and a descriptive User-Agent.

## R-009 — No license chosen
- Status: open
- Severity: high
- Kind: risk
- Stage: 09

The public repository has no license (D-007). Others cannot legally reuse it,
and the competition submission may need one. Owner decision pending.

## R-010 — Hackathon deadline
- Status: open
- Severity: high
- Kind: risk
- Stage: project

Devpost must be Submitted (not Draft) by 2026-11-21 23:59 EST. Ten stage gates
with owner acceptance between them leave little slack; the owner's acceptance
turnaround is on the critical path.

## R-011 — Ephemeral cloud container
- Status: mitigated
- Severity: medium
- Kind: risk
- Stage: project

The development container is reclaimed after inactivity. Mitigation: all
deliverables are committed and pushed; `citerift-gov recover` rebuilds the
project state from the repository alone (tested in tests/stage00/test_recovery.py).

## R-012 — Clock-dependent history ordering
- Status: accepted
- Severity: low
- Kind: limitation
- Stage: 00

History entries must be in non-decreasing time order. A machine with a slow
clock has its transitions rejected (fail-closed), never silently reordered.
Since correction A-00-001 (F-16) a time more than 5 minutes ahead of the
writer's own clock is refused, and `check` reports recorded times more than 5
minutes ahead of the checking machine's clock. The bound is relative to the
writer's clock: a writer whose clock is fast can still record a future time,
which `check` then reports and which blocks correct-clock transitions until
real time catches up or the entry is corrected (detected, fail-closed). Default
times never precede times already recorded (V-11). Pass `--at` to record an
explicit time.

## R-013 — Future ML libraries may drop Python 3.12
- Status: open
- Severity: low
- Kind: risk
- Stage: 06

Mitigated in advance by testing 3.13 in CI (D-001).

## R-014 — GitHub Actions jobs do not start (owner account billing lock)
- Status: closed
- Severity: high
- Kind: risk
- Stage: 00

Verified 2026-10-25: every job of CI runs 1 to 4 on PR #1 (commits `b13f910`
and `ecaa845`) failed before a runner was assigned, with the annotation "The job was not started because your
account is locked due to a billing issue." No CI evidence can exist until the
owner resolves it in GitHub billing settings. Recorded as Stage 00 blocker
B-00-001.

Closed 2026-10-25: after the owner updated billing, re-runs of CI runs
40188172695 and 40188175045 at `741476c` ran on GitHub-hosted runners and
succeeded. Blocker B-00-001 resolved.

## R-015 — Branch protection is defined but not active
- Status: closed
- Severity: high
- Kind: risk
- Stage: 00

The ruleset in `.github/rulesets/main-protection.json` cannot be created from
this session (proxy refuses ruleset writes; classic protection API returns
403). Until the owner imports it, `main` accepts direct pushes and force
pushes. Recorded as Stage 00 blocker B-00-002.

Closed 2026-10-25: the owner created ruleset `main-protection` (id 25824038,
enforcement active). Read back from the GitHub API, it matches the file, no
bypass actors, and `GET /rules/branches/main` lists all four rules in effect
(docs/verification/stage-00/superseded/741476c/TEST_RESULTS.md section 7). Blocker B-00-002
resolved.

## R-016 — The CI gate is defined by a file the gated change can edit
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

Independent review 2026-10-25, F-20 (verified by inspection; the GitHub side
was not exercised). The ruleset requires the `ci-gate` status from GitHub
Actions with 0 approvals. `ci-gate` is a job in `.github/workflows/ci.yml`,
which a same-repository pull request can change; the agent acts as the owner's
account (R-001). Prevention is not in place. Compensating detection since
correction A-00-001: `.github/workflows`, `.github/rulesets` and
`.gitattributes` are Stage 00 owned paths, so a change to them makes Stage 00
`VERIFICATION_STALE` at the next `check` run from an honest copy. CI runs the
checked-out `src/` modules directly, so the entry points in `pyproject.toml`
cannot replace the checker (V-04), and a shell step refuses anything in `src/`
beside the `citerift` package before any Python runs, because a
`sitecustomize.py` or a package shadowing a dependency there would run inside
every check (X-04). Before the governance check, CI installs only the locked
dependencies as wheels, without building the project (Z-04: the build backend
named in `pyproject.toml` rewrote the checker during `uv sync --locked`, which
then ran first). The governance check runs before the lock check, the project
install, ruff, mypy and pytest, and CI fails at the end if `git status` shows
any unstaged or staged change or a new file that git does not ignore, other
than the test report (Y-08:
a mypy plugin named in `pyproject.toml` rewrote the checker on disk before the
check; D4 of the confirmation review: `git diff` alone missed staged changes
and new files). A committed `.venv` is refused before uv runs (R5-01 of the
fix check: uv ran a committed interpreter wrapper, which rewrote the checker).
Not covered: `pyproject.toml` (build backend and every tool setting),
`uv.lock` (dependencies) and uv's other inputs (`.python-version`, uv
settings) are not Stage 00 owned paths. Code that reaches uv through them,
such as code in a locked wheel (a `.pth` file), already runs during the
governance check; code that the build backend or a tool setting runs executes after it,
so it can change what the test, report and tree-check steps do without making
Stage 00 stale, and it can restore the files it changed before the last step. The test report
records collection settings that differ from the fixed values (X-02), but a
dependency or committed test code can still write a false report (R-004). Prevention
needs a required code-owner review from an identity the agent does not hold
(D-006 or a bot account), an owner decision.

## R-017 — Stage 00 independent review findings (A-00-001)
- Status: closed
- Severity: medium
- Kind: defect
- Stage: 00

The independent review of 2026-10-25
(docs/audits/stage-00-2026-10-25/independent-review.md) found 14 engineering
defects and 5 security weaknesses in accepted Stage 00 (F-01 to F-19). The
owner reopened Stage 00 for correction A-00-001. Each finding has a regression
test in tests/stage00/test_corrections.py or tests/stage00/test_contracts.py
that fails on the reopened revision `ae2ce9e` and passes with the correction.
Closed when the corrections were committed; the verification of the corrected
stage is recorded in the registry. Residual limitations stay open as R-001 to
R-004 and R-016.

## R-018 — Stage 00 final independent review findings (A-00-001)
- Status: closed
- Severity: medium
- Kind: defect
- Stage: 00

The final independent review of the corrected revision `ee46423`
(docs/verification/stage-00/review/) reproduced 16 further findings, V-01 to
V-16 (1 medium, 3 low-medium, 12 low; none critical). The most serious was
V-01: a partial test run could still be recorded as complete through an ini
override or a committed `conftest.py`. Each finding has a regression test in
tests/stage00/; the tests that reproduce a behavior fail on `135e4ac`
(docs/verification/stage-00/fail-first/results-135e4ac.txt). Closed when the
fixes were committed in `5749e9c`. Residual limitations stay open as R-002,
R-003, R-004, R-012 and R-016.

## R-019 — Stage 00 second final independent review findings (A-00-001)
- Status: closed
- Severity: medium
- Kind: defect
- Stage: 00

The second final independent review, of `9e025c9`
(docs/verification/stage-00/review/), reproduced 14 further findings, X-01
to X-14 (1 medium, 5 low-medium, 8 low; none critical). The most serious was
X-02: one committed `python_functions` line in `pyproject.toml` ran 92 of 308
tests, and the report was still complete. X-14 (two surviving mutants) was
fixed in `7138d6d`. X-01 to X-13 were fixed in `564030b`; their regression
tests fail on `7138d6d`
(docs/verification/stage-00/fail-first/results-7138d6d.txt), except X-12,
which is a defect in a test. Residual limitations stay open as R-002, R-003,
R-004 and R-016.

## R-020 — Stage 00 third final independent review findings (A-00-001)
- Status: closed
- Severity: medium
- Kind: defect
- Stage: 00

The third final independent review, of `4a396fb`
(docs/verification/stage-00/review/), reproduced 13 findings, Y-01 to Y-13
(2 medium, 4 low-medium, 7 low; none critical). The two medium ones: a test
report written over a tracked test file hid that file's change (Y-01), and an
open critical defect whose `Stage` was written in Arabic-Indic or fullwidth
digits passed validation but did not block Stage 00 (Y-04). Fixed in
`aa06a40`; their regression tests fail on `4a396fb`
(docs/verification/stage-00/fail-first/results-4a396fb.txt). The 73-mutant
check at `564030b` found four rules without a test of their own (M52, M57,
M58, M59); tests and a corrected M52 were added in `aa06a40` and `a93c64f`.
Residual limitations stay open as R-002, R-003, R-004 and R-016.

## R-021 — Stage 00 confirmation review findings (A-00-001)
- Status: closed
- Severity: low
- Kind: defect
- Stage: 00

The confirmation review of `97b2051` (docs/verification/stage-00/review/)
found every earlier finding's original attack stopped and no regression, and
reproduced five close variants, Z-01 to Z-05 (1 low-medium, 4 low; none
critical), plus six overstated statements in the documents (D1 to D6). The
low-medium one: an edit that kept the file's size and mtime, with a local
`core.trustctime=false`, was hidden from `git status`, so a run of 44 of 393
tests reported a clean tree (Z-01). Fixed in `6d1fa00`; their regression
tests fail on `97b2051`
(docs/verification/stage-00/fail-first/results-97b2051.txt), and the
documents were corrected. A bounded independent fix check of `b8bb5ac`
confirmed that all five original attacks are stopped and found no
regression, but reproduced three low variants, R5-01 to R5-03 (a committed
`.venv` run by uv before the governance check, local submodule ignore
settings, Unicode case folding in the CI URL), and a few overstated words.
They were fixed in `cbb4659`; their regression tests fail on `b8bb5ac`
(docs/verification/stage-00/fail-first/results-b8bb5ac.txt). At the owner's
request, a bounded independent review of the R5 fixes at `0c21182` returned
VERIFIED: all three fixed, no new confirmed defect, no regression
(docs/verification/stage-00/review/0c21182/). Residual limitations stay open as
R-002, R-003, R-004 and R-016.
