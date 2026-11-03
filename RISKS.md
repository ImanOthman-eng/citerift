# CITERIFT Risks, Known Defects and Limitations

Persistent Project Memory: risk register. Format (checked by
`citerift-gov check`): `## R-NNN — Title`, then `Status` (open, mitigated,
accepted, closed), `Severity` (critical, high, medium, low), `Kind` (risk,
defect, limitation) and `Stage` (two-digit ids, comma separated, or
`project`). An open critical defect on a stage blocks its verification.
Likelihoods are qualitative judgments, not measured probabilities.

## R-001 — The engineering agent acts under the owner's GitHub identity
- Status: accepted
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

Owner-accepted on 2026-10-26 as a residual limitation, not fixed (DECISIONS.md
D-019, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`). The
safeguards are procedural (GOVERNANCE.md, "Procedural safeguards"); sharing one
GitHub account does not technically prevent the agent from exercising any
permission granted to that account.

## R-002 — Owner references are not machine-verified
- Status: accepted
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

Owner-accepted on 2026-10-26 as a residual limitation, not fixed (DECISIONS.md
D-019, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`). The
safeguards are procedural (GOVERNANCE.md, "Procedural safeguards"); sharing one
GitHub account does not technically prevent the agent from exercising any
permission granted to that account.

## R-003 — Registry files can be edited by hand
- Status: accepted
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

Owner-accepted on 2026-10-26 as a residual limitation, not fixed (DECISIONS.md
D-019, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`). The
safeguards are procedural (GOVERNANCE.md, "Procedural safeguards"); sharing one
GitHub account does not technically prevent the agent from exercising any
permission granted to that account.

## R-004 — CI evidence in the registry is entered by the agent
- Status: accepted
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

Owner-accepted on 2026-10-26 as a residual limitation, not fixed (DECISIONS.md
D-019, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`). The
safeguards are procedural (GOVERNANCE.md, "Procedural safeguards"); sharing one
GitHub account does not technically prevent the agent from exercising any
permission granted to that account.

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
- Status: closed
- Severity: high
- Kind: risk
- Stage: 01, 02, 03

Stages 02 and 03 depend on Stage 01 acceptance. The owner reports the external
investigation was reported, but no handoff is in this repository and no finding
is accepted. Nothing in Stage 00 assumes its results.

Closed 2026-10-27: the Stage 01 findings are delivered in
docs/verification/stage-01/ and the owner accepted Stage 01 at `85da719`
(owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP4bEH9RimJDhvHy8S2ABHcU`, D-020).
Stages 02 and 03 still need their own owner authorization.

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
- Status: accepted
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

Owner-accepted on 2026-10-26 as a residual limitation, not fixed (DECISIONS.md
D-019, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP83vKdFF4b7HZtJK8ZuJDsG`). The
safeguards are procedural (GOVERNANCE.md, "Procedural safeguards"); sharing one
GitHub account does not technically prevent the agent from exercising any
permission granted to that account.

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

## R-022 — Stage 02 review findings
- Status: closed
- Severity: high
- Kind: defect
- Stage: 02

Three review passes of the Retraction Data Engine at `3a6f1eb` (architecture
and data integrity, adversarial QA and security, scientific semantics; separate
passes of the same model, not human review) found 4 high, 15 medium and 12 low
issues. All high ones are fixed: a build could publish an index its own
`verify` rejected, a rebuild could delete a corroborated build, the relevance
check missed encoded identifier forms, an ordered concern and retraction on one
notice was reported as a conflict, and a reinstatement alone was a verified
fact. Each fix has a regression test that fails on `3a6f1eb`
(docs/verification/stage-02/evidence/fail-first/). Dispositions per finding:
docs/verification/stage-02/TEST_RESULTS.md section 10. What stays open is
R-026 and R-027.

## R-023 — Literal percent escapes in bare DOIs
- Status: accepted
- Severity: low
- Kind: limitation
- Stage: 02

A bare DOI is kept literally (no decoding, no silent repair). 24 source values
contain `%`; a lookup by the decoded form does not match them. The engine
reports such forms as possible coverage gaps, never as matches
(SPECIFICATION.md 15 A3, 16 item 17). Proposed to the owner as a residual risk.

## R-024 — Day-1 dates have no bounds
- Status: accepted
- Severity: low
- Kind: limitation
- Stage: 02

Retraction Watch writes day 1 for an unknown day, month range, season or volume
number. Such dates get no justified bounds, so the date is `uncertain` and
orderings that need it are withheld, including across years. Deliberately
conservative (SPECIFICATION.md 7.2). Proposed to the owner as a residual risk.

## R-025 — Identity beyond exact identifiers is not validated
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 02

Title, author and year matching exists only as the deterministic ambiguity
baseline, evaluated on a controlled masking task, not on natural cases. The
local open model was evaluated under AI Protocol v2 and not admitted (R-028).
Later stages must not treat a baseline candidate or a model ranking as an
identity.

## R-026 — A single PMID-bridged event can give a verified retraction
- Status: closed
- Severity: medium
- Kind: risk
- Stage: 02

The frozen policy treats a one-hop PMID bridge as evidence (cases P33, T05,
T06): when the only retraction is a bridged event, the result is
`verified_fact`, `retracted` with identity `bridged`. The directive says
co-occurrence is a source assertion, not proof of identity. The identity status
and Evidence Tension's `exclude_ambiguous_links` expose it; the review found no
real instance. Changing it means amending three frozen cases; that is the
owner's decision.

Closed on 2026-10-28 by the owner's correction (D-026; policy 1.2.0, rule 7f):
bridged assertions no longer support a value or a date, and P33, T05 and T06
are amended. The audit found that the review's "no real instance" was
incomplete: a PMID query also counted Crossref relations about the
co-occurring DOI as direct. On the pinned snapshot with the Crossref replay,
2 PMID queries had a verified retraction resting only on such relations
(PMIDs 23649173 and 25996123, each recorded in Retraction Watch only as a
correction while the DOI's retraction is recorded under another PMID); both
are now `uncertain` (`evidence/policy-impact-r026-cr.json`). The RW-only
index has no changed key. What remains is R-029.

## R-027 — Stage 02 model experiment not executed; frozen gate unattainable
- Status: closed
- Severity: medium
- Kind: risk
- Stage: 02

Historical (2026-10-27): no model prediction was made, and the frozen v1
admission gate could not be met on the v1 held-out split (largest gain 8.3
points against 10; coverage at most 61/120 = 0.508 against 0.60). Closed on
2026-10-28: v1 is kept unchanged and classified "admission design
infeasible; no model evaluation executed under it", and the experiment was
executed under AI Protocol v2 (DECISIONS.md D-025; R-028).

## R-028 — The local open model is not admitted
- Status: accepted
- Severity: medium
- Kind: limitation
- Stage: 02

Under AI Protocol v2 the frozen mxbai-rerank-base-v2 pipeline was worse than
the deterministic baseline on the fresh holdout (67 errors against 26;
negative false selections 36 against 26). The adapter and the opt-in
`citerift-rde ambiguity --model-dir` option exist and run offline, but their
output must not be shown as a suggestion by default or used for any decision.
A later stage that wants it needs a new model or task design, a new
development phase and a new fresh holdout; reusing this holdout for tuning is
not allowed. Reranker scores are ranking logits, not probabilities.

Owner-accepted on 2026-10-28 (DECISIONS.md D-028, owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`): the evaluated model is excluded from the default product, and its
negative evaluation and experimental evidence are preserved.

## R-029 — Bridged evidence is withheld, not resolved
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 02

Since policy 1.2.0 (D-026) a record reached only through an unresolved
identifier link (a co-occurring PMID or DOI, the pairing of a two-identifier
query, or a Crossref relation about a DOI the query did not give) neither
supports nor, when it would change nothing, affects a result. Identity is not
resolved: a retraction that truly concerns the work but is reachable only
through such a link is reported as `uncertain` with `BRIDGE_ONLY_SUPPORT`,
not as retracted, and a bridged retraction with another date makes a
verified date `uncertain`. Later stages must show these as unresolved, not as
"not retracted". Two related behaviors are kept as specified and are pinned
by tests: a PMID whose records carry two DOIs is `ambiguous_identity`, while
a DOI whose records carry two PMIDs stays matched with
`IDENTITY_SECONDARY_DIVERGENT` and bridges nothing (the anchor is DOI-first);
and a two-identifier query whose DOI names no record answers for the PMID
alone, anchored at `pmid:p`.

Owner-acknowledged on 2026-10-28 as a residual limitation, not resolved
(DECISIONS.md D-028, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`): "These remain unresolved
limitations, not completed identity resolution. Downstream stages must
preserve uncertainty and PMID_ROLE_COLLISION restrictions."
The status stays open because the limitation is not resolved, so that
`citerift-gov recover` keeps listing it for later stages.


## R-030 — A PMID lookup ignores records of its DOI under another PMID
- Status: closed
- Severity: medium
- Kind: defect
- Stage: 02

Found by the independent Stage 02 audit of 2026-10-28 (finding F1). A
single-PMID query reached the records of its co-occurring DOI only when they
carried no PMID; a record of that DOI under a different PMID was dropped
without an issue, although the DOI query reported the divergence
(`IDENTITY_SECONDARY_DIVERGENT`). On the pinned RW snapshot two PMID queries
were stated as `verified_fact` correction while their DOI is recorded as
retracted under another PMID: 23649173 (PubMed lists it as a retracted
publication with that DOI, so the work is in fact retracted) and 25996123
(PubMed lists it as a corrigendum, `10.2217/nnm.15.54`: Retraction Watch
gives it as that corrigendum's notice PMID on one record and as the original's
PMID on another) (`evidence/pubmed-esummary-audit-2026-10-28.json`).

Closed on 2026-10-28 under the owner's authorization (D-027; policy 1.3.0,
SPECIFICATION.md 16 item 27): such records are bridged candidates under rule
7f and the divergence is reported. Both keys are now `uncertain`, null with
`BRIDGED_EVIDENCE_MATERIAL`; no key changed toward a stated value
(`evidence/policy-impact-audit-rw.json`). For 23649173 this withholds a true
retraction, as R-029 describes; it no longer states a wrong one.

## R-031 — The role of a PMID given for both an original and its notice is not resolved
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 02

Retraction Watch gives the same PMID as the original's and the notice's on
1,341 events (finding F3 of the independent audit); on 455 of them the notice
has its own DOI, different from the original's, a strong sign that the PMID
names the notice. Since policy 1.3.0 a lookup listing such an event reports
`PMID_ROLE_COLLISION` (`event_ids`, `distinct_notice_doi`); 2,097 keys of the
snapshot carry it (1,043 DOI and 1,054 PMID keys). Values are unchanged: the PMID is still read as the
original's. Resolving the role needs an identity source such as PubMed, which
is a new source and needs the owner's approval; later stages must show the
issue and must not treat such a PMID as proof of identity.

Owner-acknowledged on 2026-10-28 as a residual limitation, not resolved
(DECISIONS.md D-028, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`); the downstream restrictions above
stay in force. The status stays open because the limitation is not
resolved, so that `citerift-gov recover` keeps listing it for later stages.

## R-032 — Follow-up: computational complexity of the Stage 02 engine is not documented
- Status: open
- Severity: low
- Kind: limitation
- Stage: 02

Follow-up item recorded at the owner's request on 2026-10-28 (DECISIONS.md
D-028, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`): "the review's complexity-documentation ...
observation". Recorded without implementation during closure. The
engineering agent's reading, not the review's text: MATHEMATICAL_MODEL.md
(§7) and SPECIFICATION.md state a cost bound only for Evidence Tension
(linear in `|E|` per intervention); the
build, lookup and reducer have measured budgets (TEST_RESULTS.md, benchmark)
but no stated time or space complexity. Any change needs the owner's
authorization.

## R-033 — Follow-up: the experimental model's inference deadline is checked between candidates
- Status: open
- Severity: low
- Kind: limitation
- Stage: 02

Follow-up item recorded at the owner's request on 2026-10-28 (DECISIONS.md
D-028, owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPXLtGyHjV52VwjSnTKz35e6`): "the review's ... experimental inference-timeout
observation". Recorded without implementation during closure. The
engineering agent's reading of the code, not the review's text:
`LocalAmbiguityModel.rank` (`src/citerift/retraction/local_model.py`) checks
the case deadline before each candidate and after scoring, so one slow
`score` call is not interrupted and a case can run past the deadline before
it abstains with `TIMEOUT`; one-time model initialization is outside the
deadline. The model is excluded from the default product (R-028), so this
affects only the opt-in experimental path. Any change needs the owner's
authorization.

## R-034 — Stage 03 frozen evaluation does not meet gate 03-G
- Status: open
- Severity: high
- Kind: limitation
- Stage: 03

The single final campaign (frozen candidate `48cfeab`, adjudicated 2026-11-02) leaves three requirements of gate
03-G unmet:

- Arabic definition precision is 0.914 against 0.95. All ten false positives are repeated identical `{{sfn}}`
  calls. The annotation guide is ambiguous here, and the run-1 and final adjudications read it in opposite ways.
- Arabic target identifiers number 33 against a minimum of 50. The sample ceiling was reached.
- English normalized-key error rate is 1 / 52 = 0.0192 against 0.01. The cause was a Wiley page-view route, since
  repaired after exposure as RF-60; that repair has not been freshly evaluated.

No unresolved wrong citation, binding, render attachment, promotion or fabricated negative is known. Evidence:
`docs/verification/stage-03/evaluation/final/DECISION_RECORD.md`. The owner decides between a narrowed claim, a new
prospective evaluation, or non-acceptance. The executor cannot record a technical verification while 03-G is unmet.

Update 2026-11-03: the owner chose a new prospective evaluation (D-034). In that campaign, at candidate `3e51792`, none
of the three failures above recurs (Arabic G5a 1.000, Arabic identifiers 103, English G2 0.000), but a different gate
fails (R-036). This entry stays open until the owner decides on R-036.

## R-035 — Stage 03 declared support boundaries observed in the final campaign
- Status: open
- Severity: low
- Kind: limitation
- Stage: 03

Observed in the adjudicated final campaign and dispositioned without code changes
(`docs/verification/stage-03/review/REVIEW_FINDINGS.md`, sections "final-campaign adjudication" and "R5"):

- **Publisher URLs without a `/doi/` path** (Springer `/10.…`, iopscience `/article/10.…`): the DOI inside them is
  not extracted. In all three observed cases, the same DOI is extracted from the template's `doi=` field.
- **Citation templates the profile does not list** (for example EI2, EI3, `قاموس دورلاند`): they are reported as
  unstructured, and their DOIs get role `unresolved`. Superseded by D-035 at engine 1.1.0:
  - a template whose render is a CS1/CS2 citation (EI2) is an `unsupported_citation_template` unit;
  - one whose render shows no citation markup (`قاموس دورلاند`) leaves its definition unresolved
    (`UNIT_CLASSIFICATION_UNRESOLVED`), with no unit;
  - DOIs keep the role `unresolved`.
- **List-defined `<ref>` tags** are not counted as uses.
- **`verify` does not re-derive identifier decoding;** only `replay` does.
- **URL forms the page-view rule does not cover:** `%20` and `;jsessionid` after a route keep the route.

## R-036 — Stage 03 confirmation campaign: English unit precision does not meet G5c
- Status: open
- Severity: high
- Kind: limitation
- Stage: 03

In the prospective confirmation campaign of D-034 (candidate `3e51792`, adjudicated 2026-11-03), English unit
precision is 126 / 145 = 0.869 against 0.95 (95 % article-cluster interval 0.718 to 0.971). Every other gate passes
in both languages, and both languages reach every minimum denominator.

All 19 false positives are `unstructured_text` units. SPECIFICATION 11.3 gives that kind to every definition with no
template unit; the annotation guide gives `unstructured` only to a plain-text citation. The definitions concerned are
Harvard short-citation links (13), explanatory notes that cite nothing (4) and two unlisted citation-like templates;
11 are in one article. None of the 19 involves an identifier, binding, render link or marker. No repair is allowed after the
prediction run. Evidence: `docs/verification/stage-03/evaluation/confirmation-2026-11/campaign/REPORT.md` and
`DECISION_RECORD.md` there. The owner decides; the executor records no verification while G5c is unmet.

Update 2026-11-03 (D-035): the owner rejected a narrowed claim and ordered a semantic correction and one more
prospective confirmation. The engine now separates citation-unit classes A-H. A definition is `unstructured_text`
only on positive evidence. Harvard links, explanatory notes, unlisted citation-like templates and unresolved
definitions are distinguished (`docs/verification/stage-03/design/unit-semantics/SEMANTIC_DECISION.md`). On the
exposed confirmation data, the frozen scorer gives English G5c 1.000 and Arabic G5c 1.000. This is regression only,
not a pass. This entry stays open until the prospective confirmation of D-035 is scored.

Update 2026-11-03 (D-035 confirmation scored): on 24 unexposed English articles, unit precision is 179 / 180 = 0.994
(95 % article-cluster interval 0.978 to 1.000) and unit recall 0.994; Arabic 1.000 and 0.992. G5c and G5d pass in
both languages (`docs/verification/stage-03/evaluation/confirmation-d035/campaign/REPORT.md`). The stage is still
not verified, because of R-038. This entry stays open until the owner accepts the stage.

## R-037 — Stage 03 citation-unit classification (D-035): residual limits
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 03

The D-035 rule recognizes a plain-text citation only on positive evidence: a locator, or the text of a citation
reference (`docs/verification/stage-03/design/unit-semantics/SEMANTIC_DECISION.md` section 5). Known limits:

- **Explanatory text in an ordinary reference.** A `<ref>` (including one in a `group="note"`) that holds only
  explanatory prose is still `unstructured_text`. A group name is free text, and reading it would be a keyword rule.
- **Short link with text.** A Harvard link beside plain text without a link or identifier is unresolved. A genuine
  second citation written there without a locator is reported, not claimed as a unit.
- **Render dependence.** Without a usable render, every template-only definition is unresolved, and so is plain
  text beside an unclassified template (review RV-4). In the 146 retained bundles this changed two definitions, both
  in one capture whose render failed (`en-906156-a1`). For refs inside template arguments (a reference list's
  `refs=`, `{{refn}}`, an infobox parameter), whose templates have no output of their own, the rendered note decides
  (review 2, RV2-4); where the ref's container is not matched to exactly one note, they stay unresolved (IUCN in
  the exposed `ar-1325389-a1`). The reviewer measured that 36 of 476 `unstructured_text` units in refs of the
  retained bundles depend on render evidence.
- **A located identifier beside a template unit** (review 2, RV2-2). A hand-written citation with its own DOI or
  PMID beside a C or G unit is not a unit of its own; its identifier carries `IDENTIFIER_OUTSIDE_UNITS`. If the
  annotation guide counts it as a second, unstructured unit, that is a recall loss, as under the frozen engine.
  Three such identifiers in the retained data, all Arabic refs where a bot added an archive `{{استشهاد ويب}}`.
- **Magic words and nested templates** (review 2, RV2-5 and RV2-8). Only `{{!}}` and `{{=}}` are known to be syntax.
  Other magic words and parser functions are unclassified templates: without a render, a plain citation holding one
  is unresolved. A G template holding an unclassified template that has no transclusion of its own anywhere in the
  render (`{{Fishbase|title={{lang|la|…}}}}`) is unresolved, because nothing shows that the nested template did not
  make the citation markup. No retained bundle has either case.
- **MF-1 v3 reads the lifetime peak** (review 2, RV2-9). A non-memory SystemError with exactly CPython's message
  "error return without exception set", after a transient peak at the limit that was freed, would be reported as
  `EXTRACTION_MEMORY_EXCEEDED`. That message comes only from CPython's own error paths, so this is improbable.
- **Rules shaped by exposed data** (review 2, RV2-11). The bibliography-entry rule was designed after inspecting the
  final English holdout's false positives and lifts that split's G5c to 1.000. Only the prospective D-035
  confirmation is evidence that the rules generalize.
- **Plain citation inside a formatting or identifier template** (`{{lang}}`, `{{nowrap}}`, `{{ISBN}}`, `{{URL}}` with
  no text outside) is unresolved, not `unstructured_text` (review RV-7). It is reported, not lost.
- **Unclassified template without citation markup beside text** (review RV-5). `{{NRDB species}} Retrieved …` or
  `{{IUCN2008|…}}` followed by commentary stays `unstructured_text`, while `{{ISBN}}`, `{{Webarchive}}` or
  `{{US patent}}` beside a hand-written citation must stay `unstructured_text`. Nothing in the markup or the render
  separates the two without a word list. Exposed instance: run 1, Arabic holdout `ar-2700573-a1` (adjudicated
  `unstructured: false`). The reviewer counted about 1 such case among about 170 D units with an unclassified
  template beside text.
- **Arabic Harvard template without evidence** (review RV-3). `استشهاد بهارفارد دون أقواس` matches the guide's name
  rule ("استشهاد …", RF-37). It is not a unit only when its own render shows a short-citation link. With no render,
  nested in another template or in a template parameter it stays a `citation_template` unit, while `{{harvnb}}` in
  the same place is unresolved. Requiring render evidence for every name-rule template was implemented and measured:
  it removed 21 genuine CS1 wrappers (Cite iucn in taxobox parameters, Cite patent, Cite simbad, …) from the retained
  bundles, a recall loss, so it was not adopted.
- **No record for E and empty definitions** (review RV-11). A definition that is only a short-citation link, or
  empty, gets no unit and no issue. Stage 04 cannot tell these apart from each other from the extraction alone.
  Unresolved definitions are named by container, with the definition number in the issue detail ("definition N").
- **Evidence marks.** Two render marks decide unlisted templates: CS1/CS2 `<cite class="citation">` and `#CITEREF`
  links. A citation module that writes neither, or a non-citation template that writes `<cite class="citation">`,
  would be misclassified. Neither was observed in the 146 retained bundles.
- **`efn` only.** Only the profile's `efn` family is treated as possibly explanatory: its text without a locator is
  unresolved, not dropped (review RV-6). `{{refn}}` is treated like `<ref>`, and no retained bundle contains it.
- **Harvard link beside a plain citation without a locator** (review RV-12) is unresolved. The owner's directive asks
  that "a genuine plain-text citation in the same definition must be retained". It is retained as a unit only when
  it carries a link, DOI or PMID; otherwise it is reported. This trade-off is for the owner.

## R-038 — Stage 03 reconciliation pairs repeated names inside a template's output in source order
- Status: open
- Severity: high
- Kind: defect
- Stage: 03

In the prospective confirmation campaign of D-035 (candidate `fff0e5b`, adjudicated 2026-11-03), Arabic gate G6b
fails: 2 false render attachments against the frozen limit max(1, 1 % of 184 engine links) = 1. Every other gate
passes in both languages, including English G5c 0.994 and G5d 0.994.

Both false attachments are in `ar-76814232`, an infobox that renders its U−B row before its B−V row. The named
reference `Mallama2014` is defined in the B−V row and reused in the U−B row; the engine attached the first rendered
marker to the definition and the second to the reuse, the reverse of the render. The locked label is correct and the
adjudicator confirmed it. Cause: `src/citerift/wiki/reconcile.py` `_align_unordered` pairs the k-th source use of a
name with its k-th rendered marker inside one template's output, although the template decides the rendered order
(the function's own docstring). The pairing is a guess that is not reported as one: the engine's render-use record
drops the Parsoid `data-mw` `body` that marks which marker carries the definition. Both markers cite the same work; what is wrong is the source position each
is attributed to. The code dates from `a29bb4e` (2026-10-29) and is unchanged by D-035. In the 204 retained extraction
documents, 15 groups in 12 articles are paired this way; this is the only one known to be wrong (5 of the 12
articles have scored render labels).

The amendment of D-035 (section 8) forbids repair or rerun after the prediction run, so the defect is preserved and
Stage 03 stays `IMPLEMENTED_NOT_VERIFIED`. A correction (abstain unless the render proves the order) needs a new owner
authorization and a new prospective confirmation. Evidence:
`docs/verification/stage-03/evaluation/confirmation-d035/campaign/REPORT.md` section 5 and `DECISION_RECORD.md`
there.
