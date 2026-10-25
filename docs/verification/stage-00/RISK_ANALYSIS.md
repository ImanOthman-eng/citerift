# Stage 00 Risk Analysis and Adversarial Review (correction A-00-001)

The live register is `RISKS.md`. This document covers four things:

- how each Stage 00 control works: whether it **prevents** the action,
  only **detects** it, or **cannot** address it
- the adversarial review of the corrected code
- the residual exposure

The accepted analysis is kept in `superseded/741476c/RISK_ANALYSIS.md`. The
independent review in `docs/audits/stage-00-2026-10-25/` found that version
overstated enforcement (F-21). The tables below replace its claims.

## 1. Threat model

Asset: the integrity of the stage record. A stage is verified only with real
evidence, accepted only by the owner, and no later stage starts without the
owner's authorization.

Adversaries:

- **A1, careless or over-eager agent.** This is the likeliest case. It skips a
  step, reuses stale evidence, or treats its own report as approval.
- **A2, dishonest writer with write access.** It edits the registry, evidence
  or workflow by hand. That includes a writer able to rewrite everything
  consistently.
- **A3, external input.** Pull request content, workflow triggers,
  dependencies.

Verified fact that shapes the analysis: the agent's GitHub token acts as the
owner's account `ImanOthman-eng` (R-001). GitHub identity therefore cannot
separate the owner from the agent.

## 2. Prevent, detect, or not enforceable

"Prevents" means the tool refuses to write the change. That binds only writers
who use `citerift-gov`. "Detects" means `citerift-gov check` reports it. CI
runs `check` on every push and pull request, and so can anyone with an honest
copy of the code. Detection does not stop a commit.

| Threat | Prevented by | Detected by | Not enforceable by repository code |
|---|---|---|---|
| R-001 agent acts as the owner on GitHub | nothing in the repository | nothing: GitHub shows one account | separating the identities; needs D-006 (owner signature) or a bot identity |
| R-002 owner reference that does not contain approval | `OWNER_REF_REQUIRED` refuses owner edges without a reference; `OWNER_REF_REUSED` refuses an acceptance citing a reference used before the verification (F-17) | `HISTORY_OWNER_REF_MISSING`, `OWNER_REF_REUSED`, `RECORD_HISTORY_MISMATCH` on hand edits | whether the cited message says what is claimed; the owner reads it |
| Owner authorization skipped (agent authorizes, accepts, withdraws or reopens) | `OWNER_DECISION_REQUIRED`; owner edges require an `owner_ref`; reopening requires a correction amendment | replay of every history entry: `HISTORY_ACTOR`, `HISTORY_AMENDMENT_MISSING`, `HISTORY_DEPENDENCY`, `HISTORY_SINGLE_ACTIVE` (F-04, F-05) | `--actor owner` is a flag the agent can pass; the reference is the only control (R-002) |
| R-003 registry hand edit | none (any writer can edit the file) | schema, including fixed policy values and `ci_required`; per-entry replay; record/history match; definition hash; duplicate keys; future times (F-03 to F-05, F-16 to F-18) | a forgery that is consistent everywhere: history, records, evidence and hashes rewritten together |
| Forged or stale evidence | verification refuses missing, trivial, unpinned, stale or partial evidence (F-02, F-07) | `EVIDENCE_STALE`, `EVIDENCE_MISSING`, `EVIDENCE_UNLISTED` over every file in the verification directory; `GATE_EVIDENCE_UNPINNED`; owned-path content compared with the verified revision (F-01) | who produced a test report or CI record (R-004): they are self-reported files whose content and hashes are checked |
| CI trust (R-004, R-016) | ruleset 25824038 requires `ci-gate` and merge commits, and refuses force-push and deletion | a change to `.github/workflows`, `.github/rulesets` or `.gitattributes` makes Stage 00 `VERIFICATION_STALE` (F-20 detection) | CI independent of the change it gates: the gated pull request can edit the workflow, and 0 approvals are needed |
| Uncommitted local changes | none | `UNCOMMITTED_OWNED_CHANGE` (warning, F-19); the test report records a dirty tree | changes never committed are invisible to CI |

## 3. Adversarial review

Each attack was run against the corrected code in a sandbox repository by the
named test. The test passes only if the attack is refused or detected. The 20
attacks of the accepted review (`superseded/741476c/RISK_ANALYSIS.md` §2)
still pass. The new attacks below are the audit's bypasses and their variants.

| # | Attack | Outcome now | At `ae2ce9e` | Test |
|---|---|---|---|---|
| 21 | Merge an old branch that restores pre-verification owned content (TREESAME merge) | `VERIFICATION_STALE` | not detected | `test_f01_*` |
| 22 | Edit a gate evidence file, cite `.` as evidence, or add a file to the evidence directory after verification | `EVIDENCE_STALE`, `GATE_EVIDENCE_MISSING` or `GATE_EVIDENCE_UNPINNED`, `EVIDENCE_UNLISTED` | not detected | `test_f02_*` |
| 23 | Turn off `single_active`, drop artifacts or handoff sections, set `ci_required: false`, remove gates, suites or owned paths | `REGISTRY_SCHEMA` before verification, `DEFINITION_CHANGED` after, `DEFINITION_WEAK` at verify | 0 errors | `test_f03_*` |
| 24 | History in which two stages were active, or a stage was authorized before its dependency was accepted, later repaired | `HISTORY_SINGLE_ACTIVE`, `HISTORY_DEPENDENCY` | not detected | `test_f04_*`, replay conformance |
| 25 | Reopen without a correction amendment; start or verify with an open blocker; block with no blocker | `HISTORY_AMENDMENT_MISSING`, `HISTORY_BLOCKER` | not detected | `test_f05_*` |
| 26 | Malformed `RISKS.md` heading on a critical defect; `Stage: project` critical defect; topic differing only in case | `MEMORY_MALFORMED`, `OPEN_CRITICAL_DEFECT`, `DECISION_CONTRADICTION` | ignored | `test_f06_*` |
| 27 | Verify with a report from `-k`, `-m`, a node id, `--deselect`, `--lf`, or a subset path | `TEST_EVIDENCE_PARTIAL` | accepted (8 of 161 tests sufficed) | `test_f07_*` |
| 28 | Store "not retracted" or a boolean as a conflicting alternative; store model output as `uncertain` | `SCHEMA_VIOLATION` | accepted | `test_contracts.py` invalid cases |
| 29 | Strings that Python and JavaScript validators read differently (trailing newline, `\S` versus Unicode spaces) | rejected by both; 0 differences against Node on all patterns and on seeded random strings | 2 engines disagreed | `test_schema_patterns_agree_with_ecma262*` |
| 30 | Accepted dependent blocks the correction of its foundation | allowed, with `DEPENDENCY_REOPENED` as a warning | permanent error | `test_f11_*`, `test_differential_fixed_case_*` |
| 31 | CRLF checkout | hashes stable (`.gitattributes`) | 8 false `EVIDENCE_STALE` | `test_f12_*` |
| 32 | Truncated, empty or BOM-prefixed registry | `REGISTRY_UNREADABLE`, exit 1, no traceback | traceback | `test_f13_*`, `test_failure_simulation.py` |
| 33 | Future timestamp to block correct clocks | refused at write; `HISTORY_FUTURE_TIMESTAMP` at check | accepted | `test_f16_*` |
| 34 | Reuse the authorization reference for the acceptance; record time not equal to its history entry | `OWNER_REF_REUSED`, `RECORD_HISTORY_MISMATCH` | accepted | `test_f17_*` |
| 35 | Duplicate JSON key showing a reviewer one value and the checker another | `REGISTRY_UNREADABLE` / `UNREADABLE` | last value silently won | `test_f18_*`, `test_duplicate_json_keys_rejected` |
| 36 | Weaken the workflow, the ruleset file or `.gitattributes` after verification | `VERIFICATION_STALE` (detection only) | not detected | `test_f20_*` |
| 37 | Byte-code cache in the evidence directory pinned at verification, so every clone reports missing evidence (found during this correction, N-01) | ignored files left out of the manifest; a non-ignored added file is still `EVIDENCE_UNLISTED` | false errors | `test_n01_*` |

Seeded property tests apply 19 classes of single mutation to an accepted
registry, 60 cases for each of 2 seeds. Every mutation is detected
(`test_properties.py`). Random byte damage never produces an exception.

Mutation testing: 34 mutants each disable one rule. Results are in
TEST_RESULTS.md §5.

## 4. Residual exposure, stated plainly

| Risk | Severity | Status | What remains |
|---|---|---|---|
| R-001 shared GitHub identity | high | open | the agent can do on GitHub whatever the owner can, including merging and editing the ruleset; nothing in the repository changes that |
| R-002 owner references not read | high | open | a reference that does not contain approval is accepted if it is present, well-formed and not reused |
| R-003 hand edits | medium | open | detection only; a consistent forgery is not detectable; stage definitions can be edited *before* verification, visible only in the reviewed diff |
| R-004 CI record entered by the agent | medium | open | the offline check cannot fetch the run; the run URL is public |
| R-016 CI gate editable by the gated change | medium | open | a pull request can change `ci.yml` so that `ci-gate` passes; Stage 00 then becomes stale, but only someone running `check` from an honest copy sees it |
| Structural evidence checks | medium | disclosed | document *content* is not judged; the owner's reading of the handoff is the control |
| R-012 clock dependence | low | accepted | a slow clock is refused (fail-closed); a clock more than 5 minutes fast is refused |

Prevention of R-001, R-002 and R-016 needs a required review from an identity
the agent does not hold: owner-signed acceptance (D-006) or a separate bot
account with code-owner review. Both are owner decisions, and neither is
implemented. They add no paid infrastructure, but they do add process.

## 5. Security review of the correction itself

- No new runtime dependency. The date-time checker uses the standard library.
  `uv.lock` is unchanged.
- No shell: new git calls (`diff --no-renames`, `check-ignore --stdin`) use
  argument lists (`test_governance_code_runs_no_shell`).
- The workflow is unchanged in this correction except where it gained owned
  status. Permissions stay `contents: read` and actions stay SHA-pinned.
- New failure modes fail closed. An unreadable registry or report is an error,
  a shallow clone reports `REVISION_NOT_FOUND` without a false staleness
  report, and an interrupted write leaves the old registry
  (`test_failure_simulation.py`).

## 6. Independent review

A separate reviewer agent with no part in writing the correction reviewed the
integrated revision. Its report and the disposition of each finding are in
TEST_RESULTS.md §9 and `review/`.
