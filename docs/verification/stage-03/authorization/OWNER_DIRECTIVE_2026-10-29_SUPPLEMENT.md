# Owner directive: Stage 03 final correction and completion (retained evidence)

- Owner reference: no platform message id is exposed to this session. Reference used: "owner message in the
  Stage 03 cloud session `claude/beautiful-planck-fm0pya`, received 2026-10-29 about 14:40 UTC, retained at
  `docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-29_SUPPLEMENT.md`". This is a transparent
  document reference, not a platform id or a signature (RISKS.md R-002).
- Author: EVE TELOS (project owner). It was delivered as a user message to the Stage 03 executor session.
- Retained by the executor on 2026-10-29 as the text received. It is a copy for audit; byte identity with any
  platform record is not machine-verified.
- It supplements `OWNER_DIRECTIVE_2026-10-28.md`, which remains binding. It authorizes one additional correction
  batch and one fresh final confirmation campaign for Stage 03 only.

---

CITERIFT — Stage 03 final correction and completion directive

[Executor handoff — authorized Stage 03 corrective implementation]
Owner: EVE TELOS · IM
Issued: 29 October 2026, UAE time
Repository: https://github.com/ImanOthman-eng/citerift

You are Claude Code, the cloud engineering executor for CITERIFT. Act as an autonomous, accountable engineering lead with specialist support. Resume the existing Stage 03 implementation, repair the independently reproduced defects below, complete the remaining evaluation and delivery, and stop for my acceptance with one unmerged PR.

This is an execution authorization for Stage 03 only. Do the work, not another planning-only response. The original full directive remains binding:

docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-28.md

This supplemental directive authorizes the additional bounded correction/evaluation cycle specified below. It takes precedence over the old protocol’s one-repair-round limit for this explicitly authorized cycle only. It does not accept the stage, authorize Stage 04, authorize merging, or permit unlimited cycles of tuning on evaluation data.

1. Recover the actual state and preserve existing work

Last independently reviewed published state:

• main: 94ac4f8df27383a03a810a4501ed1439bf8bcaea.
• Current Stage 03 branch: claude/beautiful-planck-fm0pya.
• Reviewed head: 0355c1737c0f37edce8ced855bba10ddb008928d.
• Previous implementation branch, retained: claude/project-thread-5bfmq7.
• Stages 00, 01, 02: accepted, closed, merged. Stage 03: authorized and IN_PROGRESS.
• At review time there was no Stage 03 PR, and no published final confirmation result or final handoff. Your private workspace may now contain more work: inspect before deciding anything is missing.
• The previous cloud Project’s automatic continuation was disabled by the owner. Do not restart it or create competing writers.

Inspect current HEAD, working tree, remotes, existing PRs, background processes, evaluator outputs and pending captures. Fetch the current branch. Preserve legitimate newer commits and uncommitted work; do not reset or force-push to the reviewed SHA. Continue on the existing session branch where possible. If session restrictions require another branch, preserve ancestry and keep a single coherent Stage 03 PR.

Read GOVERNANCE.md and CLAUDE.md. Follow the repository’s normal locked environment, recover and consistency-check procedure. Record this owner-delivered directive and its amendment using existing governance mechanisms. Use the actual message reference if exposed, otherwise a transparent stable reference to the retained owner directive. Do not invent a platform message ID or a separately signed approval. Preserve the original authorization and history.

The independent review is named CITERIFT_STAGE03_INDEPENDENT_REVIEW_2026-10-29.md. If attached, read it and retain it as an external AI review, not your own inspection or human gold. Its essential findings are self-contained below, so lack of access to a ChatGPT file link is not a blocker.

2. Scope, authority and completion standard

I authorize:

• F1–F4 corrections and their directly related failure paths;
• review and repair of other material Stage 03 defects discovered while completing this work;
• bounded improvements to evidence correctness, usability, API/CLI consistency, reproducibility, performance and documentation;
• the additional evaluation protocol amendment and one fresh final confirmation campaign in section 6;
• specialist review, tests, simulations, appropriate in-scope commits and one unmerged Stage 03 PR.

Finish all ordinary in-scope repairs autonomously. Do not repeatedly ask me to authorize the same stage, choose routine implementation details, or approve each test run. Compare alternatives and simplify weak mechanisms. Challenge a review finding if evidence contradicts it, preserving the reproduction and explaining the result rather than silently discarding it.

Do not modify accepted Stage 00/01/02 code, tests, contracts or frozen evidence. Do not change CI workflows, protection rules, governance enforcement, the research objective or stage graph. No PubMed integration, retraction-policy changes, rejected model activation, runtime AI, embeddings, frontend, backend API, Investigation MAESTRO, Wikipedia editing, paid service, new subscription or new permission. Do not merge or accept a stage.

The completion standard is concrete: no known unresolved material in-scope defect; every required gate genuinely satisfied; real retained verification; actual successful CI at the cited candidate; complete evidence and an unmerged PR. Do not call scaffolding, a green unit suite, successful capture, or a drafted report stage completion.

3. Work as a coordinated specialist team

Use available agents where they provide independent work:

1. Coordinating architect: scope, contracts, integration, evidence inventory and final accountability.
2. Source extraction specialist: F4 and related binding/parameter semantics.
3. Render/observation specialist: F1–F3, multilingual text channels and evidence.
4. Adversarial reviewer: wrong attachments, fabricated negatives, malformed artifacts, isolation and resources.
5. Non-implementing evaluator: raw-artifact annotation under the locked protocol, separate from implementation and predictions.

Combine roles when sensible; do not launch a large idle team. Give every writer non-overlapping files. Source and render fixes may proceed in parallel; integration and final clean-revision verification must be coordinated. Evaluators write only to their assigned output directories and do not share disposable helper directories. Identify actual agents and access restrictions. Self-review is self-review, not independent evaluation.

Review each meaningful change while building: callers, output schemas, failure paths, downstream meaning, tests and documentation. Then conduct a separate complete integration review. The architect remains responsible for resolving findings, not merely collecting agent reports.

4. Mandatory defect reproductions and corrections

At reviewed head, a separate ChatGPT/Codex session reproduced these issues through synthetic capture bundles and the public isolated extraction API. Ten warning cases, including controls, produced status: complete and passed verify; integrity verification did not independently validate the marker decision. These are synthetic failures, not claimed live-Wikipedia occurrences.

Preserve before outputs and add targeted bilingual regressions. Give new findings unique IDs without overwriting RF-01 through RF-38. Keep external review IDs F1–F4 mapped to your IDs.

F1 — Warning words broken by inline elements or comments

Location at reviewed head: src/citerift/wiki/render.py, region_text, around lines 425–478.

Controls:

• English Retracted -> recognized_warning_text.
• Arabic مسحوب -> recognized_warning_text.

Failures:

• <span>Re</span>tracted and Re<!--x-->tracted -> no_recognized_warning_in_inspected_region.
• <span>مس</span>حوب and مس<!--x-->حوب -> the same fabricated negative.

The locator quote still contains the complete word. Marker scanning adds spaces between adjacent fragments, changing the text before matching.

Correct text reconstruction at the root. Preserve real inline adjacency and actual whitespace, while separating block boundaries and hidden/citation/backlink channels correctly. Do not blindly replace every space-join with an empty-join: that can manufacture a warning across blocks or excluded regions.

Verify at least: span/strong/em/anchor boundaries; comments; entity-decoded characters; actual spaces; br and block boundaries; multiple inline fragments; negation, quotations, title-prefix exclusions and English word boundaries; Arabic folding, attached-letter rules and original evidence text. Formatting-only changes must preserve an otherwise identical observation. Uncertain reconstruction must not become a confident negative.

F2 — Ordinary red-link labels are discarded

Location: the tag == "a" and "new" in cls branch of region_text, around lines 457–462.

<a class="new" title="Missing page">Retracted</a> is reported as no recognized warning. So is an ordinary red link labelled مسحوب. The link label is discarded, and the unrelated target is not in the marker-template title list.

Distinguish an identified missing marker-template link from an ordinary red link. Preserve ordinary link-label text in the right observation channel. Retain the special treatment of missing Template:Retracted / قالب:Retracted: the template-name red link alone is not a reader warning.

Test equivalent ordinary blue/red links, known missing marker templates, unknown targets, different title and label, quotation/title contexts, surrounding inline fragments and hidden links in both languages. Keep the link’s label, target, locator and classification basis inspectable.

F3 — A hidden ancestor is ignored

Location: region_text starts at the note with walk(el, False, False), around line 471.

Wrap the whole reference list in <div style="display:none">…</div>. A note containing Retracted or مسحوب still becomes recognized_warning_text, with hidden_elements: 0.

Inherit the existing supported hiding rules from ancestors before inspecting a region. Apply consistent reasoning to reference-list notes and bibliography/template-output regions. An explicitly hidden warning belongs in hidden/ambiguous or not-inspected evidence, not shown-warning evidence and not a fabricated negative.

Cover ancestor/self/descendant combinations of inline display:none, visibility:hidden, hidden and the already-supported hidden classes; contrast with visible controls. This is a correction of the declared limited HTML inspection, not authorization for Playwright or a full CSS/browser visibility engine. Keep browser_visibility: not_evaluated.

F4 — Explicitly numbered reuse arguments disappear

Location: src/citerift/wiki/source.py, _generated_ref, around lines 435–445; it keeps only parameters with not p.showkey.

For these source-only controls, there must be two uses: the definition use and the reuse:

A.<ref name="a">Paper</ref> B.{{r|a}}
A.<ref name="a">Paper</ref> B.{{r|1=a}}

At reviewed head the first gives two uses and the second only one. The supported Arabic alias {{استشهاد متعدد|1=a}} fails the same way, without an unsupported-reuse issue accounting for the dropped call.

Implement numeric positional-parameter resolution, distinguishing it from non-positional options. Preserve raw arguments and effective semantics, actual numeric ordering, explicit/implicit mixtures, whitespace, duplicate-key precedence, empty arguments, multiple names and groups. Confirm against the actual supported template implementation and MediaWiki rules. Check related short-footnote key logic for the same assumption, without treating that check as an already-established additional defect.

Required properties: implicit and explicitly numbered equivalent calls produce equivalent use/binding facts; an overridden argument does not create a phantom use; invalid/unsupported forms have an explicit disposition. Test source-only and structurally faithful rendered cases in both languages.

5. Strengthen the product within Stage 03

Keep the verifiable source/render/use ledger as the practical creative contribution. Improve its reliability and legibility through the repairs:

• each warning observation has its exact inspected region, appropriate text channel, matched wording, exclusion/hidden basis and evidence locator;
• each reference definition/use and identifier has a disposition; silent loss is unacceptable;
• missing templates, unsupported constructs, uncertain identity, absent render and inspected-with-no-profile-term remain distinguishable;
• grouped/reused references and multiple works in one note remain separate; DOI/PMID co-reporting does not establish identity;
• role-neutral extraction does not turn a title/marker/notice identifier into the original work;
• exact anchors, hashes, atomic publication, deterministic output and offline replay survive the changes.

Keep raw source bytes unchanged. Reuse Stage 02 normalization through the existing adapter. Do not normalize away Arabic digits, controls or punctuation to manufacture a valid identifier. Do not add another parser/model simply to cover a failing example.

Re-run the five actual CLI demonstration themes, including Arabic missing-template versus English rendered-warning observations, reused named refs, notice identifiers, multiple works, different captures of one revision and source-only failure. Add focused F1–F4 before/after demonstrations labelled SYNTHETIC. Re-run B0/B1/ledger comparisons on the appropriate frozen scopes. Explain concrete benefit and cost; do not claim worldwide novelty or measured human review-time savings.

6. Owner-authorized evaluation amendment and final confirmation

I explicitly authorize one additional correction batch followed by one fresh final confirmation campaign for this review. This satisfies the old protocol section 9 requirement to bring further rounds to the owner. Record this as a dated additive amendment before using it. Keep FROZEN_PROTOCOL.md, old selections, locks, annotations, predictions, scores, failures and adjudications intact. Do not rewrite the original protocol or imply this amendment existed before the review.

6.1 Exposure inventory and consolidated repair

Inventory every old holdout/reserve/challenge/confirmation article and revision, capture, annotation, prediction, evaluator and known access history, including uncommitted background results. Treat uncertain exposure conservatively. Missing private material is missing, not proof it never existed.

Old data may be retained for regression and diagnosis; label its use honestly. Complete F1–F4, related QA and all ordinary repairs before drawing the final campaign. Freeze the production candidate and effective protocol at committed revisions before final-cohort selection/annotation. No final-cohort prediction or implementation tuning before the annotation lock.

6.2 Effective protocol

Preserve existing metric definitions, per-language quality thresholds, minimum denominators, uncertainty reporting and failure accounting. Do not weaken gates to pass. Retain original locked and adjudicated results side by side.

Use the previous observed counts to justify workload and denominator attainability, not to tune final labels or thresholds. For this final campaign, start with 10 articles per language and add ordered reserve articles in pairs only if locked annotation counts require them, up to 16 per language. Keep the existing per-language minimums: 50 target identifier occurrences, 80 uses, 60 definitions and 60 linkable uses. Count failed captures in acquisition success; never substitute a successful article for a failed one. If denominators cannot be reached, report the affected gate as unmet.

Select article groups not previously used/exposed in development, demonstrations, holdout, reserve, observed challenge or earlier confirmation. A newer revision of an old article is not a fresh article group. Deduplicate page IDs and resolved titles, and report overlapping cited works separately from article leakage.

The retained selection has unused metadata-only candidates (at review: 15 ar and 36 en). Use them only if the exposure inventory supports that they remain unused; exclude any affected group. Order a fixed eligible pool by a declared deterministic rule independent of engine performance. If the eligible pool is insufficient, make a bounded new draw using the existing selection method, logging every response and exclusion. Do not hand-pick easy articles.

Keep the sample’s DOI-link eligibility and bounded annotation-window limitations explicit. Do not expand its conclusions to PMID-only articles or all Wikipedia. Explain how the existing reserve rule applies to this newly authorized campaign.

6.3 Independent annotation and one final run

Provide a non-implementing evaluator only the raw retained artifacts, annotation guide, assigned window and output location. No engine code, tests, predictions or implementation findings that disclose expected labels. Use isolated helper directories, truthful provenance and artifact hashes. A same-family AI evaluator is procedural separation, not human gold.

Lock and commit annotations and reserve inclusion decisions before predictions. Confirm the lock matches retained bytes and the declared candidate/protocol. Produce final predictions once. Use the frozen scorer with its declared metric definitions; maintain any known flawed historical A/B/C statistic and publish corrected supplements separately. A changed scorer requires an explicit versioned methodological explanation and preserved old results, never a silent score improvement.

Freeze any essential, explicitly justified scoring correction before final annotation/prediction; do not change scoring rules after seeing final results. Keep adjudication governed by the existing independent, reasoned, item-level procedure, with both label sets published. The implementer does not edit labels. Newly observed failures stay failures. Do not tune on this final cohort and call a rerun fresh. If the final campaign exposes another material defect, preserve it, complete independent deliverables, and report the exact further decision needed rather than manufacture acceptance or launch endless campaigns.

Earlier confirmation work already underway remains published under its actual provenance. It is not silently relabelled as the fresh final campaign.

6.4 Bounded resources

Use the existing network and parser safety limits. For this explicitly added final campaign, cap additional selection/acquisition work at the existing scale: 500 HTTP attempts and 300 MiB accepted bodies, counted globally across selection, captures, retries and agents; evidence export at most 1 GiB. Report old, additional and cumulative costs separately. These are operational ceilings, not accuracy thresholds or targets to consume.

One request in flight across the host; shared network gate; at least 10-second spacing; no shortened Retry-After; no 403 bypass or alternate identities. Do not create separate lock files to evade the shared gate. Count higher-level retries as well as retries inside one CLI operation. Persist progress so an interruption does not cause blind recapture.

Retain the 30-second extraction worker wall deadline, 1,024 MiB address-space limit and existing byte/structural limits unless a tighter equivalent is justified. Measure real RSS/CPU/wall time and distinguish it from network waiting. No product-model tokens or weights; report annotation-agent effort separately where available.

7. Adversarial and integrated verification

Run meaningful checks while implementing. In addition to all existing required suites, verify:

• F1–F4 exact outcomes and bilingual metamorphic twins;
• visible/hidden/title/quote/negation/redlink transitions do not fabricate a negative or a shown warning;
• reused references, forward/list-defined refs, groups, conflicting definitions and duplicate DOM IDs do not gain wrong attachments;
• duplicate/aliased fields, multiple works and notice/marker identifiers keep their roles and uncertainty;
• same retained bytes/config/runtime yield identical extraction; source/DOM anchors re-check;
• missing render, revision mismatch, parser omission, limits, malformed data and network failure retain explicit states;
• timeout/memory containment interrupts expensive work; replay/extraction make no network calls;
• malicious paths, symlinks, duplicate JSON keys, corrupt artifacts and modified outputs fail appropriately;
• API, CLI, schemas, documentation, exported evidence and the observed behavior agree.

Review every changed production module and its consumers. Maintain findings with severity, root cause, affected output, before evidence, fix, regression and disposition. Include a cross-module review after integration. Do not silence warnings indiscriminately, weaken tests, add skips/xfails, change fixtures to match incorrect behavior or game test counts.

For repairs changing output, record exact code/config/profile/parser identities and version Stage 03 behavior appropriately. Preserve replay instructions for older frozen outputs using their original code revision. Do not claim old and new extraction digests should match when behavior intentionally changed.

8. Recoverable evidence and distribution

Keep required artifacts durable as work proceeds. Commit/push small coherent checkpoints after substantial progress, including locked annotations and completed background captures. Do not leave indispensable evidence only under /tmp, private scratchpads or another session’s /mnt directory.

Inventory the calibration evidence lost with the previous session. Preserve the loss disclosure. Reacquisition is a new observation with a new retrieval time; it does not recreate missing original bytes or validate the old timing numbers. Repeat bounded measurements where required for a currently reproducible gate, with new provenance, keeping the original report.

Use content-addressed artifacts and checksum manifests. Export must include bytes required for declared demonstrations/evaluation, raw annotations/predictions, commands, revisions, versions, outcomes, license/attribution and limitations. Verify a documented durable download path or host-supported downloadable attachment. If durable export cannot be provided, identify that exact delivery blocker; do not invent a URL.

Use relocatable paths or a verified path-remapping procedure in evaluation specs and scripts. Test from a fresh directory without the original session layout.

Build and install the wheel in a separate environment outside the checkout. Test capture where supported, verify, extract and replay with the documented schema-root configuration. State explicitly that the current wheel needs external schema files via CITERIFT_SCHEMAS; no unrelated accepted-stage packaging refactor. Linux tests do not establish Windows support.

9. Final engineering verification and PR

Once fixes, independent review, evaluation and required documents are complete, freeze the candidate and run final verification on clean committed revisions using normal repository tooling.

Required:

• full repository tests on Python 3.12 and 3.13, with the established report plugin and genuine complete-run reports;
• ruff lint and formatting, strict mypy, lock consistency, schema validation, governance consistency and the established dependency audit;
• actual successful GitHub Actions for the cited candidate, Python matrix and ci-gate, checking meaningful logs rather than only a pushed status;
• unchanged accepted/protected paths and a final clean-tree check;
• final CLI demonstrations, artifact checksums, offline replay and installed-wheel results.

Do not recreate the accepted 68 MB Retraction Watch builds merely to repeat Stage 02 acceptance; the complete regression suite remains required. Do not reuse the independent review’s 1,517-test success as proof for later edits. Correctly bind code and evidence revisions using the established lifecycle; avoid circular self-SHA records. Any behavior/evidence change after verification requires the affected checks to be renewed.

Provide the required Stage 03 documents:

SPECIFICATION.md, MATHEMATICAL_MODEL.md, RISK_ANALYSIS.md, SIMULATION_REPORT.md, TEST_RESULTS.md, CREATIVE_DIFFERENTIATION_REVIEW.md, HANDOFF.md, and test-report.json.

Also provide the retained supplemental owner directive, additive evaluation amendment, exposure inventory, F1–F4 before/after evidence, complete review dispositions, frozen final-campaign manifest, evaluator/annotation locks, raw predictions, scores and uncertainty, resource results, five real demonstrations, synthetic repair demonstrations, export manifest and exact CI links. Remove completion placeholders and reconcile stale wording with actual dates and results without altering historical evidence.

Update one Stage 03 PR against main; create it if none exists. A draft while work continues is allowed. Leave it unmerged. Explain concrete product behavior, repairs, evaluation history and final result, resource costs, limitations, source attribution and protected-path checks. Follow CLAUDE.md’s commit and PR attribution rules; never impersonate the owner. Public creator identity: EVE TELOS · IM.

Use existing transitions only when their real conditions hold. Stage 03 may reach VERIFIED_AWAITING_OWNER_ACCEPTANCE; it must never be accepted by the executor. Do not force a verified transition if a scientific gate, denominator, evidence requirement or delivery requirement is unmet.

10. Owner-facing completion report and stop

Write the final explanatory report in Arabic, starting with what now works and its practical value. Include:

1. Real Arabic/English article and pinned-revision examples through extracted reference/use/identifier to inspectable evidence; no Stage 04 retraction-matching claim.
2. F1–F4 and any additional findings: original failure, root correction, meaningful regression, final disposition.
3. Historical first-run failures, earlier confirmation state, newly authorized final confirmation, locked/adjudicated results, per-language denominators and scope limitations. Distinguish reported agent work, actual CI and independent review.
4. What the ledger improves over the baseline and what the comparison does not measure.
5. Measured parsing versus acquisition latency, requests, bytes, memory, storage and annotation effort where available.
6. Exact code/evidence revisions, test counts and versions, successful CI URLs, durable evidence download and the unmerged PR URL.
7. Remaining unsupported behavior and scientific uncertainty; no concealed failure or invented human approval.

Complete all authorized independent work before reporting a genuine blocker. Resolve ordinary Stage 03 issues without repeated permission requests. If an indispensable external requirement, protected-stage change, missing genuine evaluator or a further post-confirmation repair is necessary, preserve the evidence and state the exact minimal decision required.

On successful completion, stop with:

VERIFIED — AWAITING OWNER ACCEPTANCE

Otherwise use the truthful repository-required status, BLOCKED — EVIDENCE PROVIDED or NOT VERIFIED, with exact unmet requirements. Never treat either as successful closure.

The owner alone accepts the stage and personally merges the PR. Do not begin Stage 04 or any other project action after the handoff until the owner decides.

Begin by recovering the current state, inventorying exposure/background work and recording this directive. Then reproduce and correct F1–F4, consolidate review, freeze the final candidate/protocol and carry the authorized Stage 03 completion through to its genuine stopping point.
