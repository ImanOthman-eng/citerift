# Owner directive of 2026-11-04: Stage 03 definitive engineering resolution, scientific validation and final owner acceptance

Owner: EVE TELOS. Delivered in the CITERIFT project, message `cmsg_018VCB51nDHP6HXmLU4ea5yPJGcnAZCAku5nJRxTZzFaL7`
(2026-11-04T02:20:42Z). It answers `../evaluation/confirmation-d035/DECISION_RECORD.md`. Recorded as DECISIONS.md
D-036.

This file is an operative transcription by the executor. It keeps the section structure, every rule, number and
prohibition, and normalizes formatting to Markdown. The platform message is the authoritative text. The directive
gives execution authority for Stage 03 only. It is not acceptance. It authorizes exactly one additional bounded
prospective bilingual confirmation of a corrected candidate, and no later stage.

## Executive mandate

Claude Code acts as the accountable Principal Engineering Lead and Scientific Validation Director. This is a final
execution mandate, not a planning assignment: perform the entire authorized lifecycle autonomously; do not return
with a plan, after one fix, after unit tests or after documentation; do not delegate unresolved engineering decisions
back to the owner; do not stop because a reviewer finds another correctable defect. Desired outcome
`VERIFIED_AWAITING_OWNER_ACCEPTANCE`, claimed only if every applicable mandatory requirement is actually met. Never
manufacture passing evidence or conceal a failed gate.

## 1. Current verified state

Repository `ImanOthman-eng/citerift`, pull request #5, branch `claude/beautiful-planck-fm0pya`, last externally
verified head `11fb5b87711e74a8c9ec7203f462a42678dd977f`, accepted main `94ac4f8`, Stage 03 `IMPLEMENTED_NOT_VERIFIED`;
Stages 00-02 accepted; Stages 04-09 not authorized. Reconstruct the actual state first (head and PR, uncommitted
changes, evidence, frozen candidates, test matrices, directives, local artifacts, outstanding findings, security and
attribution). Latest verified evidence is authoritative; never redo verified work without a new reproducible reason;
preserve all historical evaluations, including failures. No reset, force push, destructive cleanup or unapproved
history rewrite.

## 2. Engineering accountability

Cover Python architecture, MediaWiki/Wikitext/Parsoid, reconciliation and citation semantics, multilingual
extraction, DOI/PMID identity, scientific evaluation, adversarial QA, security and evidence integrity, reproducible
release engineering. Use independent specialist contexts when genuinely useful; separate implementation from
adversarial verification; avoid overlapping edits, redundant subagents, unnecessary MCP integrations, paid services
and repetitive work. Keep a durable checkpoint after every material milestone; commit and push complete verified
checkpoints without modifying frozen evaluation artifacts; on recovery continue from the latest checkpoint.

## 3. Root cause R-038 / Arabic G6b

R-038 (`src/citerift/wiki/reconcile.py`, `_align_unordered`) is a confirmed defect requiring a production correction.
Do not simply reorder two markers. Redesign only the affected decision so that matching relies on valid evidence:
investigate and use, when reliable, Parsoid `data-mw` body metadata, definition versus reuse markers, group and name
identity, source and render container boundaries, template transclusion identity, exact source anchors, rendered DOM
evidence and reuse semantics. If a mapping cannot be established unambiguously, abstain, keeping explicit
`RECONCILIATION_ABSTAINED` accounting. Excessive abstention is not an acceptable way to bypass G6b while failing G6c:
maintain both precision and coverage.

Mandatory test cases: reordered infobox parameters; repeated named references; definition followed by reuse; reuse
rendered before definition; multiple reuses; multiple groups; anonymous references; nested templates; transclusions
producing multiple markers; missing `data-mw`; contradictory `data-mw`; duplicate or malformed DOM identifiers;
source/render revision mismatch; mixed Arabic and English; ambiguous mappings; large and pathological templates. Do
not hardcode the failing article, template or reference name.

## 4. Mandatory fail-first correction

Before changing production code: reproduce both false attachments on the faulty revision; preserve the evidence and
expected behaviour; add minimal failing regression tests and related synthetic and real-fixture cases; implement the
smallest correct fix; show the tests fail before and pass after; recheck affected integration paths; verify no valid
attachment is lost and no incorrect attachment is created elsewhere; document root cause and correction. Do not
modify the historical D-035 candidate or its scores. Label post-exposure regression results as such.

## 5. Full pre-validation defect elimination

Mandatory before any further campaign. A systematic adversarial investigation of the whole flow: capture, source
parsing, definitions, uses, units, identifiers, render reconciliation, marker observations, ledger, verification,
replay. Per subsystem: invariants, boundaries, interface assumptions, nondeterminism, malformed inputs, ambiguous and
unsupported states, failure containment, cross-language consistency, downstream consequences, counterexamples.
Prioritize failures that could invalidate G1-G11; in particular, whether other reconciliation paths assume an order
the renderer may legally change. Classify known limitations as genuine defects, supported boundaries, scientific
limitations or noncritical enhancements. Correct every independently confirmed material defect within Stage 03 with
fail-first and after-fix evidence; no unrelated enhancements.

## 6. Full regression protection

Preserve Stage 02 DOI/PMID contracts, RF-60, the G5c unit taxonomy, `unsupported_citation_template`, genuine
`unstructured_text`, Arabic short-footnote semantics, named-reference and definition/use identity, reconciliation
safeguards, explicit uncertainty and abstention, warning-marker correctness, Retry-After, durable resume and
journaling, rate limiting and maxlag, worker containment, receipts and checksums, installed-wheel compatibility,
offline verify and replay. Differential analysis over every retained real bundle; investigate every unexpected
change. Do not weaken tests, schemas, validation or CI.

## 7. Independent engineering readiness gate

Before freezing: genuine adversarial review in independent contexts; one reviewer covers the entire corrected
reconciliation subsystem, another the complete Stage 03 integration boundary; reproducible evidence, severity and
impact per finding; fix every confirmed critical or high defect; a focused independent re-review; no endless loop.
The next evaluation is forbidden until: known material reconciliation defects corrected; fail-first tests pass; all
retained bilingual regressions pass; no incorrect source/render link known; affected reference groups audited;
findings dispositioned; complete engineering verification passes; no unresolved critical or high defect. The gate
must not use future holdout results.

## 8. One final prospective scientific confirmation

Authorized: one additional prospectively registered, bounded, bilingual campaign after readiness. Before acquisition:
freeze the production revision; commit the protocol; keep G1-G11 thresholds and the minimum denominators; define
population, method, randomization, reserve order, exclusions, stopping rules; exclude previously exposed groups;
freeze annotation and adjudication rules; define the network budget; validate feasibility; record this authorization.
Fresh unexposed articles; no selection on engine performance, no tuning on holdout results, no threshold or metric
change after prediction, no exclusion of difficult cases after outcomes. Independent blind evaluators with isolated
inputs; annotations locked and committed before predictions; one prediction run; independent adjudication; locked
and adjudicated outcomes retained; every result published. Ceilings: 500 HTTP attempts and 300 MiB accepted bodies;
respect Retry-After, maxlag, cooldowns, global limits and resumable acquisition; no proxy rotation or rate-limit
bypass. Every applicable gate G1-G11 must pass; G5c is not excluded; G6b is not exempted. If a mandatory requirement
fails, do not change frozen evidence or start another unapproved campaign.

## 9. Security and public Git history

Resolve the historical AWS presigned-URL exposure as far as safely possible. Separate security review of the five
withheld files: key id only or access-bearing presigned URL; whether a secret value is present; whether the resource
may remain accessible; whether the repository or export redistributes sensitive material; whether merges would
propagate the historical blobs into main; whether a clean sanitized delivery branch would avoid that; whether public
history requires owner or third-party remediation. Do not execute or follow presigned URLs; do not disclose
credentials, signatures or sensitive values; do not rely on `.gitignore`; do not blindly delete evidence; do not
rewrite public history or force-push without explicit authorization. Where possible implement nondestructive
sanitization and prepare a clean merge path with audit provenance. Do not present sensitive history as safe to merge.
Document the minimal owner-side action only where it cannot be done under the granted permissions. Do not confuse an
AWS key identifier with a secret access key.

## 10. Complete final engineering verification

At the exact final revision: Python 3.12 and 3.13 suites; ruff lint and format; mypy; governance; schema and
contract validation; lock; dependency audit; negative and security tests; bilingual integration; reconciliation
metamorphic tests; worker memory and timeout; Retry-After and network-gate simulations; reproducibility; offline
verify and replay; installed-wheel smoke; protected paths; clean worktree; GitHub Actions on the final head. Do not
reuse older results for newer code; rerun after the last code change.

## 11. Documentation

Specification, mathematical model, risk analysis, simulation report, test results, creative differentiation review,
protocol, locked annotations, adjudicated scores, review records, evidence-integrity reports, security findings,
durable export, handoff, governance state, decision records, PR description; exact commits, revisions, checksums and
commands; an independently verifiable archive. Do not claim owner preservation before it happens.

## 12. Final scientific acceptance standard

Ready for owner acceptance only if: candidate frozen before evaluation; every mandatory G1-G11 gate passes; minimum
denominators met; no unapproved threshold change; no known critical or high defect; all evidence verifies and
replays; annotation independence documented; limitations disclosed; complete engineering verification; final-head CI
passes; durable evidence complete and checksum-verified; documentation consistent; Git-history security concern
resolved or the required owner-side remediation identified; governance permits verification. Only then record
`VERIFIED_AWAITING_OWNER_ACCEPTANCE`. Never record acceptance, never merge, never start Stage 04.

## 13. Autonomous execution

Complete ordinary in-scope implementation, testing, analysis, documentation and validation without routine approval
(no return for a plan, for permission to fix a confirmed defect, add tests, review, repair a regression, run
authorized verification, document or update the PR). The bounded campaign above is authorized. Checkpoint; leave a
recovery note on interruption; do not repeat completed acquisition, annotation or scoring; no agent overwrites
another's work.

## 14. Mandatory final self-audit

Before any final response: every R-038 failure corrected; no new incorrect attachment known; G6c preserved; G5c/G5d
valid; accepted contracts intact; no locked evidence changed; no failed result removed; samples independent; gates
passed legitimately; engineering checks passed; no serious defect hidden; security correctly classified; no unsafe
history unknowingly introduced into main; PR describes the final implementation; tested SHA matches; governance
status correct; the owner alone retains acceptance and merge.

## 15. Final owner handoff

Only after all authorized work. If all requirements pass: `READY_FOR_OWNER_ACCEPTANCE_AND_MERGE`, with final SHA, PR
link, root-cause corrections, review evidence, Arabic and English G1-G11 results, test counts, CI URLs, evidence
integrity, security disposition, governance status and confirmation that no merge occurred; then request only
acceptance and manual merge. If verification genuinely fails after the campaign, or an action needs permissions not
granted, report the exact blocker and the minimum owner action. Do not classify engineering completion as scientific
acceptance.
