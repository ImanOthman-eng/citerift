# Owner directive of 2026-11-02: Stage 03 final engineering recovery, correction, verification and handoff

Owner: EVE TELOS. Delivered in the CITERIFT project thread, message `cmsg_018VCB51nDHP6HXmLU4ea5yPAsujY49DkUw92HiR1mG4Ya`
(2026-11-02T12:25:19Z). Retained by the executor as an operative transcription of the owner's text (section headings
and rules kept, wording kept; formatting normalized to Markdown). Recorded as DECISIONS.md D-033. It is execution
authority for Stage 03 only, not acceptance, and it authorizes no new evaluation campaign and no later stage.

## Role and mandate

The executor acts as the accountable engineering and scientific lead for CITERIFT Stage 03. Independent specialist
agents may be used where they materially improve verification, without redundant parallel work. This is an
execution assignment: recover the existing Stage 03 work, complete the already-authorized adjudication, correct
independently established in-scope defects, conduct rigorous engineering verification, finish the deliverables
and prepare the existing PR for owner review. Only the owner may authorize a new scientific evaluation campaign,
change an acceptance requirement, accept a stage, or merge a PR. No claim of successful verification without
reproducible evidence.

## 1. Authoritative starting state

Repository ImanOthman-eng/citerift; PR #5; branch `claude/beautiful-planck-fm0pya`; last externally verified head
`d151507504bc1157ba92dc90541ccf4ec70868ab`; frozen production candidate `48cfeab2c093ea0e853fe2ccb2cd1d5ff87a528b`;
accepted main `94ac4f8df27383a03a810a4501ed1439bf8bcaea`; status IMPLEMENTED_NOT_VERIFIED; Stages 00-02
ACCEPTED_CLOSED; Stages 04-09 not authorized. These are recovery references: read the actual state first, identify
unpushed and newer work, compare with the retained evidence, check for active jobs, confirm tools and resources,
record a recovery checkpoint, preserve every valid result, reconcile non-destructively, never force push, and do
not repeat completed acquisition, evaluation or verification without a new technical requirement.

## 2. Non-negotiable scientific integrity

Read and enforce GOVERNANCE.md, DECISIONS.md, PROJECT_STATUS.md, the registry, the Stage 03 specification,
mathematical model, risk analysis, frozen protocol, amendment, annotation guide, adjudication brief, the final
evaluation directory and all applicable owner directives. Preserve the complete evaluation history. Prohibited:
changing frozen thresholds; changing annotations to match predictions without independent justification; treating
exposed articles as a new blind holdout; rerunning the final campaign and calling it independent; exceeding the
authorized sample ceiling; erasing or selectively excluding unfavorable evidence; reporting an underpowered
denominator as satisfied; changing earlier measurements to match repaired code; inventing verification, human
review or validation; modifying accepted Stage 00/01/02 contracts or artifacts; beginning Stage 04; automatically
merging or accepting Stage 03. Post-exposure repairs are labelled as such; regression tests on exposed data prove a
correction works but are not fresh acceptance evidence. The authorization covers bounded correction and completion
work, not a new blind campaign or relaxation of acceptance criteria.

## 3. Current scientific failures to resolve

- F-01 Arabic definition precision 0.913793 < 0.95; ten extra generated-note definitions in one article involving
  repeated `sfn` calls. Determine the cause (annotation error, engine overcounting, definition-versus-use
  interpretation, short-footnote semantics, unit identity or binding, support-profile limitation) without presuming
  either side is right.
- F-02 Arabic identifier denominator 33 < 50 with the 16-article limit exhausted: a sample-sufficiency failure.
  Report the actual denominator, narrow unsupported claims, never manufacture observations or a replacement sample.
- F-03 English normalized-key error rate about 1.923 % > 1 %; the Wiley URL
  `http://onlinelibrary.wiley.com/doi/10.1111/0004-5608.00043/abstract`. Investigate the boundary from the guide,
  DOI syntax, retained evidence and the Stage 02 contract; do not modify accepted Stage 02 behavior; repair a
  Stage 03 URL-interpretation or adapter defect there.
- F-04 Unfinished adjudication: finish it before any scientific conclusion; keep locked and adjudicated results
  separately inspectable.
- F-05 Incomplete delivery: final evidence, test documentation, owner handoff, PR readiness and verification.

## 4. Execution order

- Phase A, read-only recovery and evidence inventory (completed work, tests, frozen candidate, lock digests,
  predictions and scores, pending adjudication, failed gates, missing deliverables, local-only work, processes, CI),
  recorded in the Stage 03 evidence structure.
- Phase B, complete independent adjudication with separate non-implementing evaluator contexts that receive only
  the frozen guide, raw wikitext, retained Parsoid HTML, window metadata, original locked labels and the disputed
  prediction values; follow the committed protocol item by item; preserve original bytes and hashes; retain
  adjudicated annotations separately; validate, rescore with the unchanged scorer, report every gate per language,
  publish original versus adjudicated results; if isolation cannot be achieved, report that limitation.
- Phase C, root-cause analysis and targeted correction for each independently confirmed engine defect: unique id,
  preserved failure, earliest wrong assumption, trace through callers, schemas, accounting, verification and
  consumers, minimal reproduction, fail-first regression, at least one safer or simpler alternative considered,
  smallest supported correction, verified, related constructs checked; no change made solely to agree with
  unconfirmed annotations; protect reference/footnote and DOI semantics listed by the owner; no fabricated
  negatives, wrong attachments, false promotions or silent losses; no unnecessary refactoring.
- Phase D, preserve the evaluation boundary: publish the frozen evaluation's adjudicated outcome, label later fixes
  post-exposure, verify them on separate evidence, never claim they make the frozen evaluation pass; document the
  Arabic 33/50 result, the sampling ceiling and reserve history, quantify the limitation and produce a decision
  record. Possible outcomes: A all gates pass after legitimate adjudication; B implementation technically verified
  but the original scientific requirement unmet, a narrower claim supportable subject to owner and governance
  approval; C a new independent evaluation needed, requiring an owner-approved prospective amendment before any
  acquisition; D material defects or insufficient evidence prevent acceptance. Do not silently choose B or C.

## 5. Adversarial engineering review

After the corrections, an independent integration review by a specialist who did not implement them, covering DOI
association, reference binding, reuse/short-footnote collisions, false positives and fabricated negatives,
complete versus partial states, source anchors, DOM locators, forged or incomplete receipts, schema acceptance of
impossible states, nondeterminism, API failures, revision mismatch, network policy, resource exhaustion, large and
pathological input, path traversal and artifact integrity, installed-wheel and external-schema behavior,
multilingual equivalence and Stage 02 contract compatibility; integration paths, schemas, tests, verify, replay,
CLI and downstream meaning; adversarial and metamorphic tests. A self-review is required but is not independent
validation. No known material in-scope defect may be hidden or waived.

## 6. Full verification without wasteful repetition

Focused tests during correction; on the final committed revision: Python 3.12 and 3.13 complete suites, ruff check,
ruff format --check, mypy, citerift-gov check, contract and schema validation, security and negative tests,
reproducibility, deterministic replay, packaging and installed-wheel smoke tests, relevant dependency audit,
protected-path diff, successful GitHub CI on the exact final PR head. Inspect exit codes and reports; never
disable, skip, weaken or delete a test to pass; record and fix failures and rerun the final checks after the last
correction. No claims from old CI against newer code.

## 7. Deliverables

Complete and reconcile SPECIFICATION, MATHEMATICAL_MODEL, RISK_ANALYSIS, SIMULATION_REPORT,
CREATIVE_DIFFERENTIATION_REVIEW, TEST_RESULTS, HANDOFF, the final evaluation evidence and decision records, project
status and governance records where authorized, and the PR #5 description, in the established layout. The final
report states frozen original results, adjudication decisions, post-adjudication metrics, post-exposure
corrections, limitations, denominators and uncertainty, supported versus unsupported claims, failure and
abstention accounting, baseline comparison, reproducibility boundaries, costs, open risks, and exact implementation
and verification revisions. Update the differentiation review from evidence; keep the verifiable citation ledger
and multilingual evidence interpretation; no speculative AI, embeddings, platforms or features; preserve the
rejected optional AI model decision. Review public authorship metadata and attribution for accuracy and privacy; do
not rewrite public Git history; report any correction that needs an owner decision.

## 8. Durable evidence and GitHub delivery

Make the Stage 03 evidence durable and reproducible (receipts, locks, adjudication, original and adjudicated scores,
transcripts, revision ids, commands, checksums, environment, test results, CI links, handoff) through the
established export workflow, within size, license and budget limits; validate the manifest and checksums from a
separate location where possible. One existing PR; push in-scope commits to the existing branch and update PR #5;
no force push; no merge; do not mark Stage 03 ACCEPTED_CLOSED; do not start Stage 04. Record the technical
verification transition only if every applicable scientific and technical gate is genuinely satisfied; otherwise
keep the truthful status and state the blocker. Passing CI is never scientific acceptance.

## 9. Efficiency and deadline

Submission deadline 2026-11-21 23:59 EST (2026-11-22 08:59 UAE), a hard planning constraint. Avoid unbounded
research, endless reviews, redundant subagents, repeated whole-suite tests, repeated Wikimedia acquisition, new
dependencies, paid APIs, new infrastructure, reopening accepted stages and repeated work. No paid service or new
permission is authorized. No work outside Stage 03.

## 10. Final quality gate and self-audit

Sixteen self-audit questions (preservation of Stages 00-02; original results intact; independent and faithful
adjudication; confirmed defects corrected; regressions fail before and pass after; no new DOI, binding or warning
defect; artifacts verify and replay; nothing reported as fresh despite exposure; numbers from the right evidence;
Arabic denominator limitation preserved; scientific gates on the appropriate evidence; tests and CI green at the
final revision; documents consistent with the registry; evidence durable and checksum-verified; PR #5 accurate and
unmerged; no undisclosed defect or unsupported claim), each answered with evidence or turned into an owner decision.

## 11. Owner handoff

One concise final response: an executive verdict (READY_FOR_OWNER_ACCEPTANCE_AND_MERGE,
ENGINEERING_COMPLETE_SCIENTIFIC_DECISION_REQUIRED or BLOCKED_BY_VERIFIED_MATERIAL_DEFECT), verified delivery
(branch and head, frozen revision, evaluation status, adjudicated metrics, gate results, corrections, test counts,
static checks, CI links, export status, governance status, PR URL), remaining limitations, the required owner
decision with evidence, risk and a recommendation, ending with exactly:
"STAGE 03 HANDOFF COMPLETE — AWAITING OWNER DECISION. NO MERGE PERFORMED."
