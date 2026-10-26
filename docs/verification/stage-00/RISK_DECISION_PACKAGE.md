# Stage 00 Risk Decision Package (correction A-00-001)

Prepared on 2026-10-26 at the owner's request
(`cmsg_018VCB51nDHP6HXmLU4ea5yP3BFvQvWtWFp37ndPPex2k9`, section 4) for the
five open Stage 00 trust-boundary items. It is a proposal for one owner
decision. **None of these risks is accepted by this package, by the
verification transition, or by the agent.** Accepting them, or choosing
another option, is the owner's decision at Stage 00 acceptance.

Source of each description: RISKS.md at `0c21182`. Severity is the one
recorded there.

## 1. Assessment

The six questions of the owner's instruction, answered for each item.
"Stage 00 requirement" means the sixteen acceptance gates in
`governance/stage_registry.json`.

| Question | R-001 shared GitHub identity (high, risk) | R-002 owner references not machine-read (high, limitation) | R-003 consistent forgery not detected (medium, limitation) | R-004 self-reported test and CI evidence (medium, limitation) | R-016 CI gate editable by the gated change (medium, limitation) |
|---|---|---|---|---|---|
| 1. Fails a Stage 00 gate? | No gate requires a separate agent identity. It limits what 00-L means: the ruleset stops direct pushes, force pushes, deletion and merges without `ci-gate`, but not an actor holding the owner's account | No gate requires machine-verified references. 00-C/00-D require the reference to exist, to be unique per acceptance and to match the history, which is enforced | No. 00-D/00-J require detection of hand edits that break a rule, which is enforced and tested (`test_registry_tampering.py`, `test_properties.py`) | No. 00-I/00-K require passing tests and CI; the evidence is checked for form, completeness and revision, and the cited run is public | It limits 00-K and 00-L: `ci-gate` passing means the workflow in the pull request passed, not that an unchanged workflow passed |
| 2. Existing effective control | Ruleset with no bypass and required `ci-gate`; owner references required (D-005); agent commits carry their own git author (`Claude <noreply@anthropic.com>`) and the `Assisted-by` trailer; owner merges only on explicit approval | Reference required; reuse refused (`OWNER_REF_REUSED`); acceptance only from the actor `owner` | `check` replays the whole history, pins every evidence file and the stage definition, and compares owned-path content with git | Completeness, revision and clean-tree checks of the report; CI record must name a run URL of this repository, the revision and success; anyone can open the run | Workflow and ruleset are Stage 00 owned paths, so a change makes Stage 00 stale; CI step order and tree checks (Y-08, Z-04, R5-01) |
| 3. Minimal code correction needed now? | No: no repository code can tell two holders of one account apart | No: repository code cannot read the owner's chat | No: any single-writer repository record can be rewritten consistently | No: a check inside the repository cannot prove who produced a file | No: CI cannot be made independent of a change that can edit it |
| 4. Independent external control required to remove it? | Yes: an identity the agent does not hold (owner-held signing key, or a separate agent account plus a required owner review) | Yes: the same owner-held key (D-006) | Yes: the same | Partly: fetching the run from GitHub at acceptance time | Yes: a required code-owner review from an identity the agent does not hold |
| 5. Needs an owner-only configuration or authorization? | Yes | Yes | Yes | No for the manual check; yes for an automated one | Yes |
| 6. Documented architectural limitation, not an unfinished defect? | Yes | Yes | Yes | Yes | Yes |

No item is an unfinished Stage 00 defect, and no minimal correction inside
the authorized scope would remove one. All five come from one cause: the
agent and the owner share one GitHub account, and the repository holds the
only record. They are therefore decided together.

## 2. Exposure

What can go wrong while these stay open: an agent session that does not
follow its instructions, or a compromised session token, can (a) merge a
pull request that changes the CI workflow so that `ci-gate` passes without
the real checks, (b) record an acceptance that cites a message that does not
say "accept", or (c) rewrite the registry, evidence and hashes together. On
GitHub, (a) looks like the owner's own merge. Each of these leaves a commit
in the history; (a) also makes Stage 00 stale at the next honest `check`. No
data, money or credential beyond the repository is exposed by Stage 00 itself.

## 3. Alternatives

| Option | What it takes | Effect | Cost |
|---|---|---|---|
| A. Accept the five as documented limitations, with three owner habits (recommended) | Owner merges pull requests to `main` personally; at each acceptance the owner reads the cited `owner_ref` (`citerift-gov handoff <stage>`) and opens the cited CI run URL | Exposure stays as in section 2, detected by history and `check`, not prevented | none now |
| B. Owner-signed acceptance (D-006) | Owner creates an SSH signing key on their own machine; a later amendment adds a check of signed acceptance tags against an `allowed_signers` file | Removes forged acceptance (R-002, part of R-001 and R-003) | one key setup; an engineering change with its own review, so not before this acceptance |
| C. Separate agent identity and required owner review | Agent sessions use another GitHub identity with write access only; the ruleset requires one approving code-owner review | Removes R-016 and most of R-001 | depends on whether the agent platform can use a separate identity, which has not been tested |
| D. Do not accept Stage 00 until B or C is in place | as B or C | as B or C | delays Stage 00 acceptance and every later stage |

## 4. Recommendation

Option A for Stage 00 now, and decide on B before Stage 09, when the project
publishes results and a forged acceptance would matter most. Reason: the
hackathon deadline (R-010), Stage 00 reads no external data and publishes
nothing, and every exposure in section 2 leaves a visible trace.

## 5. Downstream implications

- Every later stage inherits the same trust boundary: its acceptance is only
  as strong as this decision.
- If B is chosen later, past acceptances stay unsigned; only acceptances after
  the change are signed.
- If C is chosen, the ruleset change is an owner action on GitHub, and the
  file `.github/rulesets/main-protection.json` must be updated to match in a
  pull request, which makes Stage 00 stale and needs an enhancement amendment.
- Under A, a merge of a workflow change by anyone other than the owner is a
  breach of process that the owner can see in the pull request history.
