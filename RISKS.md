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
the owner's own words (D-005); the branch ruleset has no bypass actors, so the
agent cannot skip CI either (D-011). Full mitigation needs D-006 (owner-signed
acceptance) or a separate bot identity.

## R-002 — Owner references are not machine-verified
- Status: open
- Severity: high
- Kind: limitation
- Stage: 00

The orchestrator checks that an owner decision cites a reference and that the
acceptance record matches the history, but it cannot read the reference. A
dishonest writer could cite a message that does not say what is claimed. The
owner should check the `owner_ref` of each acceptance in the history.

## R-003 — Registry files can be edited by hand
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

The orchestrator detects inconsistent hand edits (history replay, record
coherence, evidence hashes, revisions) and CI blocks them from `main`, but it
cannot prevent edits, and a fully consistent forgery of history plus records
is possible for anyone with write access. Detection, not prevention.

## R-004 — CI evidence in the registry is entered by the agent
- Status: open
- Severity: medium
- Kind: limitation
- Stage: 00

The offline check verifies that the recorded CI run tested the verified
revision and succeeded as recorded, but it cannot fetch the run. The run URL is
public for this repository and can be checked by anyone. The required
`ci-gate` check on `main` is the independent control.

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

History entries must be in non-decreasing time order. A machine with a wrong
clock would have its transitions rejected (fail-closed), never silently
reordered. Pass `--at` to record an explicit time.

## R-013 — Future ML libraries may drop Python 3.12
- Status: open
- Severity: low
- Kind: risk
- Stage: 06

Mitigated in advance by testing 3.13 in CI (D-001).
