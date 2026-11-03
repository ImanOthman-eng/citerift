# Owner directive of 2026-11-03: Stage 03 final G5c corrective engineering and scientific acceptance

Owner: EVE TELOS. Delivered in the CITERIFT project, message `cmsg_018VCB51nDHP6HXmLU4ea5yPBxa7nEyAiE3VN5Lw442e8F`
(2026-11-03T05:53:24Z). It answers `../evaluation/confirmation-2026-11/DECISION_RECORD.md`: the owner rejects a
narrowed standard and orders a correction of the G5c defect and one more prospective confirmation. Recorded as
DECISIONS.md D-035.

This file is an operative transcription by the executor. It keeps the section structure, every rule, number and
prohibition, and normalizes formatting to Markdown. The platform message is the authoritative text. The directive
gives execution authority for Stage 03 only. It is not acceptance, it authorizes exactly one additional bounded
prospective confirmation of the corrected candidate, and it authorizes no later stage.

## Mission

Claude Code acts as Principal Software Engineer, Citation Semantics Specialist, Scientific Evaluation Lead,
Adversarial QA Lead and Release Verification Coordinator. Objective: eliminate the confirmed English G5c semantic
classification defect, preserve all previously validated engineering and scientific behaviour, and establish whether
the corrected Stage 03 meets the original scientific acceptance requirements.

- Do not propose a narrower acceptance standard. Do not waive G5c. Do not merely improve the documentation. Correct
  the underlying issue.
- Complete implementation, independent review, prospective verification, engineering checks, evidence preservation
  and GitHub handoff. Do not return after partial implementation. Do not ask for routine engineering approvals.
  Return only when the authorized work is complete or a genuine, evidence-backed scientific blocker prevents
  completion.

## 1. Recover the verified current state

Repository `ImanOthman-eng/citerift`; pull request #5; branch `claude/beautiful-planck-fm0pya`; last externally
reviewed head `f88bdd7ae4bc321863224bf95775ceeeba09591b`; frozen confirmation candidate `3e51792`; accepted main
baseline `94ac4f8`; expected status `IMPLEMENTED_NOT_VERIFIED`. Before modifying any file, verify the repository,
working tree, remote head, CI, governance records and artifacts; recover uncommitted or unpublished work; do not
repeat completed operations; no reset or force push; do not modify accepted Stages 00-02; do not begin Stage 04; do
not merge PR #5.

## 2. Exact failure to correct

Verified results of the latest campaign: 24 Arabic and 20 English holdout articles, 10 English warning-challenge
articles; 54 / 54 extractions verified and replayed; Arabic passed every applicable gate; English passed every gate
except G5c; 1,834 tests passed on both Python versions; CI passed; evidence audit 27 / 27.

English G5c, citation-unit precision: observed 126 / (126 + 19) = 0.8689655; required ≥ 0.95. All 19 false positives
involve `unstructured_text`. Adjudicated categories: (1) 13 Harvard short-citation links (`{{harvnb}}`, `{{harvp}}`)
without an independently qualifying plain-text citation; (2) 4 explanatory notes with no bibliographic citation;
(3) 2 unsupported but citation-like templates (`{{Fishbase}}`, `{{NRDB species}}`) that the evaluator recognized as
citation templates. Root cause: SPECIFICATION.md 11.3 treats a definition without a recognized template unit as
`unstructured_text`; the annotation guide requires text that actually constitutes an unstructured bibliographic
citation. These predicates are not equivalent. Correct it at the semantic-model level, not by hiding it from the
scorer.

## 3. Formal semantic correction

Reconstruct the citation-unit taxonomy from production code, schemas, tests, specification, mathematical model,
annotation guides, adjudication decisions and retained raw examples. Define a formal distinction between:
A. a reference definition; B. a citation unit inside it; C. a structured citation template; D. a genuine
unstructured bibliographic citation; E. a Harvard short-citation link referring to an entry elsewhere; F. an
explanatory note with no bibliographic citation; G. a citation-like template whose semantics are unsupported or
unresolved; H. a definition whose citation-unit classification cannot be established safely. These must not be
collapsed into `unstructured_text` because the template profile fails to recognize a construct.

**Required invariant:** the absence of a recognized citation template is not sufficient evidence that an
unstructured bibliographic citation exists.

- Establish a precise, conservative recognition rule for genuine unstructured citations. No fragile keyword
  heuristics, English-only assumptions, or hardcoded exclusion list covering only the 19 examples.
- Handle plain-text references, Harvard author-year links, mixed structured and unstructured content, nested
  templates, unsupported citation-like templates, empty or explanatory references, reused and list-defined
  references, Arabic and English templates, ambiguous bibliographic content, render-only reference structures.
- A Harvard link must not automatically become a standalone unstructured unit; a genuine plain-text citation in the
  same definition must be retained.
- An unsupported citation-like template must not be silently reclassified as plain text: keep its exact source
  anchors and an explicit unsupported or unresolved classification.
- Do not expand the supported template profile merely to improve the score unless authoritative semantics justify it
  and complete regression coverage exists.
- Keep definitions, uses, bindings, identifiers, render links and marker observations intact.
- Any schema or taxonomy change is the smallest version-compatible change the Stage 03 contracts allow; document any
  compatibility effect.

## 4. Fail-first reproduction

Before production changes: reconstruct the 19 cases; keep their source coordinates and evidence; isolated
reproducible tests for all three categories; show the tests expose the current behaviour; positive controls where
`unstructured_text` is legitimately required; negative controls (unsupported, empty, explanatory, short-citation
only); bilingual and mixed-content variants; keep the frozen prediction files and historical scores unchanged.
Record the failures, then implement the smallest defensible correction; run focused tests; no valid unit may
disappear incorrectly; do not modify the frozen scorer or historical annotations to manufacture a pass.

## 5. Protect the entire extraction pipeline

No compromise of: DOI/PMID detection and normalization; cited-work versus notice roles; source-span precision;
definition identity; use counting; short-footnote binding; named and grouped references; rendered marker attachment;
retraction-warning detection; explicit ambiguity and abstention; offline verification; deterministic replay; schema
compatibility; multilingual equivalence; Stage 02 contracts. Keep RF-60, Retry-After, network-gate, memory-safety and
R6/R7 fixes; do not reopen them without a demonstrated regression. Differential checks on all 54 retained real
bundles, reporting exactly which outputs change and why. The previous campaign's data are exposed: regression use
only, never a new independent scientific pass.

## 6. Independent adversarial engineering review

After implementation, an independent specialist context (not the implementer) reviews: the new unit definition;
false negatives from conservative recognition; false positives in unsupported templates; Harvard-link interaction;
mixed constructs; Arabic/English differences; source and render integrity; schema evolution; replay; complexity and
resource limits; downstream interpretability for Stage 04; leakage into identifiers, bindings or warning states. The
reviewer must try to falsify the implementation with challenging examples. Each confirmed defect: reproduce,
document, correct, add regression coverage, verify. Stop when all confirmed material in-scope findings are resolved;
no endless review cycles.

## 7. One authorized prospective confirmation

One additional bounded prospective confirmation of the corrected candidate is authorized; no other campaign. Before
selecting or capturing: finish corrections; complete the review; freeze the corrected production commit; write and
commit a prospective protocol amendment; freeze the guide and scoring rules; freeze frame, randomization,
exclusions, reserve order and stopping rules; verify every evaluation article group is unexposed to calibration,
testing, development and both earlier confirmation campaigns; record the authorization truthfully in governance.

- Keep the original G1-G11 thresholds; English G5c not below 0.95; keep the minimum denominators. The study must be
  sufficient to verify the corrected candidate under the existing framework.
- Assess whether English-only confirmation is legitimately sufficient; if protocol or governance require fresh
  bilingual validation, use a prospectively defined bilingual study. A differential regression on the existing Arabic
  sample is required regardless and is not fresh holdout validation. Justify the strategy before acquisition.
- Deterministic pre-registered random sampling; no cherry-picking; no use of engine predictions or historical failure
  membership to select primary holdout articles; keep the population and task claim or state a changed estimand;
  reserve decisions from annotation counts only.
- Cumulative ceiling of 500 HTTP attempts and 300 MiB of accepted bodies, hard ceilings not targets; no bypass of
  Wikimedia rate limits; keep Retry-After, maxlag, request spacing and resume protections; no duplicate captures. If
  the design cannot meet the statistical requirements within the limits, report the exact obstacle.

## 8. Blind evaluation and adjudication

Evaluator contexts independent of implementation, with only the frozen rules and raw packets, no engine predictions
and no prior failure classifications; isolated workspaces; exact input manifests and provenance. Before predictions:
lock annotations by checksum, commit locks, commit the evaluated cohort, record the frozen candidate SHA, validate
non-exposure. Then exactly one planned prediction run, scored with the frozen scorer. Record G5c, G5d, all other gates,
denominators, per-article error distributions, confidence intervals, failure and abstention accounting,
disagreements and ambiguity. Independent adjudication under the frozen guide; keep locked and adjudicated labels and
scores; keep historical failed campaigns unchanged. No tuning after seeing new holdout outcomes. A failed evaluation
is recorded and scientific acceptance stops; no automatic further campaign.

## 9. Final engineering verification

At a clean committed revision after the final code correction: Python 3.12 and 3.13 suites; ruff check and format;
mypy; governance; schema and contract tests; lock and dependency audit; security tests; citation-model regressions;
retained bilingual bundles; DOI and short-footnote regressions; Retry-After and resumable capture; worker resource
containment; offline verification; deterministic replay; installed-wheel smoke tests; protected-path diff; GitHub CI on
the final PR head. No disabled, deleted, skipped or weakened tests. Review the complete change set. Final independent
integration audit.

## 10. Scientific acceptance gate

`VERIFIED_AWAITING_OWNER_ACCEPTANCE` only when the prospective evidence satisfies every mandatory requirement:
English G5c ≥ 0.95 and G5d ≥ 0.95; Arabic validity retained or prospectively re-established where required; all
other applicable G1-G11 thresholds; denominators; no false cited-work promotions; no fabricated negative warning
states; no wrong rendered attachments beyond the frozen limit; full verify and replay; valid independent annotation
provenance; complete engineering checks; green final-head CI; no unresolved critical or high material defect; all
evidence preserved. No changing, removing or exempting G5c; no claim that regressions on exposed data are a fresh
pass. Otherwise keep `IMPLEMENTED_NOT_VERIFIED` and name the exact blocker.

## 11. Final handoff and GitHub delivery

Update SPECIFICATION, MATHEMATICAL_MODEL, RISK_ANALYSIS, SIMULATION_REPORT, CREATIVE_DIFFERENTIATION_REVIEW,
TEST_RESULTS, HANDOFF, the protocol amendment, the confirmation report, the independent review report, governance and
decision records, and the PR #5 description. Preserve original results and audit histories; checksum-verified
evidence export with exact commit identifiers, inspectable without the session. Push to the PR #5 branch; never force
push; never merge; never mark `ACCEPTED_CLOSED`; never start Stage 04.

**Final owner response:** one concise but complete report: A. Verdict (READY_FOR_OWNER_ACCEPTANCE_AND_MERGE,
ENGINEERING_COMPLETE_SCIENTIFIC_DECISION_REQUIRED or BLOCKED_BY_VERIFIED_MATERIAL_DEFECT); B. Corrective implementation
(root cause, files changed, classification model changes, fail-first results, review findings, regression
assessment); C. New scientific evidence (candidate SHA, sampling design and article count, annotation provenance,
G5c and G5d, other gates, intervals, new failures, historical evaluations preserved); D. Engineering verification
(3.12/3.13 tests, static and security checks, verify/replay, CI links, export, governance state, final PR head);
E. Required owner action (if all requirements are met, only owner acceptance and manual merge; otherwise the precise
blocker and the minimum scientifically legitimate decision). Do not propose excluding G5c. Do not reopen completed
engineering work without evidence.

## Final execution order

Recover; diagnose; reproduce; implement the smallest correct semantic fix; protect genuine unstructured citations and
multilingual behaviour; focused regressions; independent adversarial review; freeze candidate and prospective study;
one blind confirmation; independent adjudication; verify gates; full engineering checks; preserve evidence; update
governance and documents; push to PR #5; self-audit; return only at the final owner gate. Do not optimize for the
metric at the expense of correct behaviour. Do not merge. Do not start Stage 04.
