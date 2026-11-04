# Owner directive of 2026-11-02 (second): Stage 03 final scientific recovery, corrective engineering, Retry-After hardening, independent validation and release gate

Owner: EVE TELOS. Delivered in the CITERIFT project, message `cmsg_018VCB51nDHP6HXmLU4ea5yP8BNaHtTfgxhSrEp6pbWPHh`
(2026-11-02T15:37:19Z). It answers the decision left open by `../evaluation/final/DECISION_RECORD.md` (outcome C with
additional engineering). Recorded as DECISIONS.md D-034.

This file is an operative transcription by the executor. It keeps the section structure, every rule, number and
prohibition, and normalizes formatting to Markdown. The platform message is the authoritative text. The directive
gives execution authority for Stage 03 only. It is not acceptance, it authorizes exactly one new prospective
confirmation campaign, and it authorizes no later stage.

## 0. Mission and authority

The executor acts as accountable Principal Engineer, Scientific Evaluation Lead and Release Verification Coordinator,
and executes the work rather than only planning it. Specialist agents may be used for scientific methodology,
MediaWiki/Parsoid semantics, citation and DOI/PMID correctness, networking and fault tolerance, independent
evaluation and adjudication, adversarial review, and release verification, in isolated contexts for independent
reviews, without overlapping edits or redundant agents.

Requirements: no knowingly unresolved material defects; no regression to accepted components; no fabricated
scientific success; no hidden limitations; no unnecessary redesign; no repeated testing of verified work without
cause; no expansion beyond Stage 03; no merge without owner approval.

**One new prospective confirmation campaign is authorized** under the conditions below. The authorization does not
permit changing acceptance thresholds, erasing prior failures, using exposed articles as fresh evidence, or
automatically accepting the stage. All authorized work is completed before returning to the owner.

## 1. Reconstruct the exact current state

References: PR #5, branch `claude/beautiful-planck-fm0pya`, last verified head `eca4389`, last fully tested code
`8c6fe9f`, historical frozen candidate `48cfeab`, main `94ac4f8`, Stage 03 `IMPLEMENTED_NOT_VERIFIED`. Inspect the
actual local and remote state, reconcile local-only work, check governance and directives, review reports and risks,
identify the smallest necessary interventions, preserve accepted work and evidence, confirm tools and permissions. Do
not assume the SHAs are newest. Do not reset, force-push, erase or overwrite work. Stages 00-02 are protected and
accepted. Stage 04 is not authorized.

## 2. Scientific starting point

The previous final evaluation (16 + 16 articles, locked AI annotations, one prediction run on the frozen candidate,
37 disputed items adjudicated: 34 confirmed, 3 corrected) stays unchanged and is reported as a failed historical
result: Arabic G5a 106/116 = 0.913793 (< 0.95; ten repeated identical `{{sfn}}` calls); Arabic identifier denominator
33 (< 50; 16-article limit exhausted); English G2 1/52 = 0.0192308 (> 0.01; Wiley `/abstract`, corrected after
evaluation by RF-60). RF-60 and the five R5 fixes are implemented and tested: verify and preserve them, do not
reimplement. The new campaign establishes the performance of a prospectively frozen corrected candidate; it does not
rewrite historical outcomes.

## 3. First priority: short-footnote (sfn) semantics

Investigate the conflicting readings of ANNOTATION_GUIDE.md 3.1 and 3.2 against the frozen specification, retained
wikitext and Parsoid evidence, MediaWiki short-footnote behavior, the engine's container/definition/use model,
reuse and generated-note semantics, and the adjudication disagreement. The likely intended distinction (one
definition per identical effective short-footnote identity, multiple uses bound to it) must be verified against
actual MediaWiki semantics before adoption. Produce a formal semantic decision covering definition identity, repeated
identical calls, different effective arguments, named versus unnamed parameters, group identity, argument
normalization, source anchors, generated-note containers, rendered markers, and definition-versus-use accounting.
Then: create an explicitly versioned prospective clarification; keep the original guide unchanged; correct the engine
only if it is demonstrably inconsistent with the validated semantics; fail-first tests where code changes; test
Arabic and English; verify unchanged source/render binding; keep other constructs unaffected. Never manipulate
historical annotations.

## 4. Second priority: DOI/PMID hardening

Verify RF-60 and the R5 fixes. Investigate remaining boundary risks: publisher URLs ending in `/abstract`, `/full`
and similar routes; legitimate suffixes containing those words; percent encoding; mixed-case paths; HTML entities;
query parameters and fragments; embedded or nested URLs; trailing punctuation; multiple candidate interpretations;
co-reported identifiers; Stage 02 normalizer compatibility; ambiguous publisher URL structures. No universal
suffix-stripping rule from a few examples. Where a boundary cannot be established reliably, keep explicit ambiguity
or abstention. Any correction needs a documented root cause, fail-first tests, unchanged Stage 02 contracts, no false
cited-work identification, and bilingual and negative regressions. No general publisher-crawling system.

## 5. Third priority: Retry-After reliability audit

Retry-After is implemented; do not rebuild it. Read `src/citerift/wiki/fetch.py`, `capture.py`,
`tests/stage03/test_wiki_fetch_capture.py`, `simulations/stage03/fetch_policy_sim.py`, the networking and capture
sections of SPECIFICATION.md, and the network evidence. Verify the documented behavior (429; retryable 5xx;
HTTP-date and delta-seconds Retry-After; 10 s minimum spacing; at most three attempts; per-attempt and global
deadlines; shared cross-process gate; deferred status and `not_before`; maxlag and API `ratelimited`; fixed
Wikimedia hosts; no 403 bypass) before proposing changes.

Mandatory audit:

- **R1** 429: no request before the valid Retry-After deadline.
- **R2** 503 and maxlag: a valid Retry-After is respected; JSON API errors with HTTP 200, including maxlag, are
  handled correctly.
- **R3** header parsing: integer delta seconds, valid HTTP dates, past dates, missing, malformed, very large values,
  invalid encodings, clock and timezone edges; fail safely when uninterpretable.
- **R4** operation deadline: a long requested wait yields a truthful deferred outcome, never indefinite sleep or an
  early request.
- **R5** cross-process coordination: separate capture processes share the restrictions and never shorten another's
  cooldown; interrupted-process and stale-lock cases.
- **R6** retry budgets: maximum attempts, deadlines, response-size limits, cumulative ceilings; no hidden infinite
  loops.
- **R7** network failures: connection refusal, timeout, incomplete response, invalid JSON, unexpected status, 403,
  redirect refusal, decompression failure, interrupted requests.
- **R8** resume after deferral: distinguish computing and recording `not_before` from actually resuming unfinished
  acquisition after it. If resumption exists and is correct, keep it; if missing or defective, implement the smallest
  bounded durable mechanism: persist unfinished work and status; respect `not_before` after restart; resume only
  eligible unfinished requests; never repeat successful immutable captures; never request early; preserve revision
  identity and provenance; never silently replace failed selected articles; respect global budgets; idempotent after
  interruption; no duplicate concurrent workers; independent of an AI session staying alive; no unbounded background
  service or new infrastructure. If automatic resumption is unnecessary, keep an explicit deterministic manual resume.
- **R9** policy: follow current Wikimedia API usage, user-agent, rate and maxlag guidance; never rotate identities,
  hosts, IPs, proxies or credentials to evade limits.
- **R10** evidence: deterministic simulations and real-case regressions from retained logs, with injectable clocks
  and scripted transports; no live 429 traffic to test what can be simulated.

Acceptance: correct waiting, deferral, persistence and bounded resumption for every supported case; unsupported
resume behavior disclosed; no request intentionally violates a valid server cooldown.

## 6. One new prospective confirmation study

Begins only after: engineering corrections complete; definition/use ambiguity resolved prospectively; implementation
stable; independent engineering review finds no unresolved material defect in the candidate; prospective protocol
written, internally reviewed and committed; this authorization recorded truthfully in governance (no fabricated
message id, signature or separate approval).

Keep G1-G11 and the original thresholds, and the per-language minimums: 50 target identifier occurrences, 80 uses, 60
definitions, 60 linkable uses. No change after seeing outcomes.

Sample design: address the underpowered Arabic sample with a larger pre-registered design; deterministic random
frame independent of engine predictions; keep the original sampling population where possible. Suggested bounds:
Arabic initial 24, English initial 16, ordered reserve blocks of 4, maxima 48 Arabic and 32 English (caps, not
guarantees), validated for statistical and operational feasibility against previous evidence and the deadline before
acquisition. Freeze: frame and eligibility; randomization method and seed; exclusions; article-group non-overlap;
exposure inventory; initial and reserve order; window selection; minimum denominators; capture failure policy;
annotation instructions; adjudication protocol; estimands; bootstrap; stopping rules; request, body and time limits;
budget exhaustion behavior; acceptance procedure. Reserve additions use committed locked annotation counts only. If
minimums stay unmet at the ceiling, record the failure. No selection change after predictions, no enrichment by
engine success or failure; any alternate design is pre-registered with its own inferential population.

Network: hard cumulative ceiling of 500 HTTP attempts and 300 MiB of accepted bodies for the campaign (maxima, not
targets); no concurrent process bypasses the shared capture policy; use the existing compliant client and controls;
never silently exceed the ceilings.

## 7. Independent annotation and blind evaluation

Before any holdout prediction: commit the candidate, the protocol, and the selection and reserve order; capture
pinned revisions; produce raw-only evaluator packets; annotate independently; lock with hashes and commit the lock;
resolve reserve decisions from locked counts alone. The implementing agent does not create gold labels. Independent
evaluator contexts with restricted inputs and separate output directories; reviewers from different available model
families where possible without paid APIs; AI evaluations are never presented as human gold.

After the lock: one planned prediction run; verify and replay every evaluated extraction; score with the
prospectively frozen procedure; identify disagreements; adjudicate independently; publish locked and adjudicated
outcomes; confidence intervals; compare with the unchanged thresholds; report all failures. No tuning, repair or
reclassification followed by a rerun called fresh. A failed study is preserved truthfully; no further campaign is
launched automatically.

## 8. Positive retraction-warning challenge

Separate, independently specified positive challenge with genuine, previously unexposed examples of retraction,
correction or concern warnings, where obtainable within the budget, distinct from the random holdout. Test explicit
retraction warnings, expressions of concern, corrections, Arabic and English variants, missing-template links,
rendered versus source-only, uninspected versus inspected regions, warning absence versus extraction failure,
unsupported or ambiguous language. Keep provenance and independent labels; report detection performance and
denominator; no invented positives; synthetic tests are not field evidence; state an insufficient sample as a
limitation.

## 9. Independent adversarial review

After all code repairs and before the study: one independent adversarial integration review (citation identity and
grouping, short-footnote reuse, DOI/PMID roles, false promotions, source/render revision matching, anchors and
locators, rendered binding, warning regions, no fabricated negatives, receipts and hashes, strict schemas, offline
verify, replay, Retry-After and concurrency, size and decompression limits, worker memory and time, resource
exhaustion, installed wheel, stage boundaries, cross-language consistency, failure accounting). Confirmed findings:
record severity, reproduce before change, smallest repair, pass after, integrations checked, residual risk.
Speculative findings are not confirmed defects without reproduction. One second focused review only for changes from
the first. After the study, an evidence-integrity audit, with no change to the frozen candidate based on results.

## 10. Full release verification

At the exact final code revision: Python 3.12 and 3.13 full suites, ruff check, ruff format check, mypy, governance,
lockfile, dependency audit, schema and contract, security and negative, cross-language, Retry-After simulations,
worker containment, reproducibility, offline verify/replay, installed wheel, external schemas, protected paths,
clean worktree, GitHub Actions on the final PR head. No change, skip or weakening of tests. Engineering verification
and scientific validation are distinct; both are needed for unconditional acceptance; green CI alone is not
scientific success. Do not reopen Stages 00-02.

## 11. Deliverables

Update consistently: specification, mathematical model, risk analysis, simulation report, scientific protocol and
prospective amendment, annotation provenance, adjudication reports, evaluation and confidence intervals, baseline
comparison, creative differentiation review, test results, handoff, governance status, decision records, PR #5
description, in the existing structure. Durable checksum-verifiable evidence archive, checked from an independent
extraction location, not dependent on ephemeral paths. Keep attribution and license obligations. Do not rewrite
public history for authorship metadata; document unresolved privacy concerns. No paid APIs, unnecessary dependencies
or speculative features.

## 12. Scientific pass/fail rule

Unconditional verification only when: (1) the frozen candidate is exactly the one evaluated; (2) denominators reached
in both languages; (3) every applicable G1-G11 passes under the new protocol; (4) annotation independence and
provenance met; (5) warning claims within positive evidence; (6) every evaluated bundle verifies and replays; (7) no
known critical or high unresolved engineering defect; (8) full regression and static verification pass; (9) network
policy and Retry-After controls pass; (10) export and documentation complete; (11) governance permits the
transition; (12) final PR-head CI succeeds. Then record `VERIFIED_AWAITING_OWNER_ACCEPTANCE`, never acceptance, never
merge. Otherwise report the exact failure; never weaken the standard.

## 13. Execution discipline

Work autonomously; no routine questions; no pause after a plan; no stopping after one fix; no reopening completed
work; no full suites after every small change; no network requests for what can be simulated. Keep the branch and PR;
commit evidence at freeze points; push without force; keep an auditable record. Deadline 2026-11-22 08:59 UAE
(2026-11-21 23:59 EST) is a hard constraint.

## 14. Final self-audit

No uncommitted material work; no accepted-stage change; no original evaluation data overwritten; no new sample
contaminated; no annotation changed to match predictions; no threshold relaxed; no known DOI or binding regression;
Retry-After deadlines enforced; deferred acquisitions resume safely or have a supported manual path; no unauthorized
network access or bypass; no paid service; final tests tied to the final revision; measurements reproduce; archive
digests verify; documentation exists; PR reflects the results; no concealed high finding; governance agrees with the
evidence.

## 15. Final handoff

One final handoff, sections A (verdict: READY_FOR_OWNER_ACCEPTANCE_AND_MERGE, ENGINEERING_COMPLETE_SCIENTIFIC_DECISION_REQUIRED
or BLOCKED_BY_VERIFIED_MATERIAL_DEFECT), B (engineering delivery), C (scientific validation), D (scientific
conclusion), E (owner action), ending with: "STAGE 03 EXECUTION COMPLETE — OWNER ACCEPTANCE OR SCIENTIFIC DECISION
REQUIRED. NO MERGE PERFORMED."
