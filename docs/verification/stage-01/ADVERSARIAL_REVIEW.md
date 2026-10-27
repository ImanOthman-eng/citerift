# Stage 01 Internal Adversarial Review — Findings and Dispositions

A subagent of the same model as the executor was asked to falsify the Stage 01
conclusions, re-run the counts and test the code (2026-10-26). It downloaded
the pinned Retraction Watch CSV (SHA-256 matched), made 14 Wikipedia and 4
Crossref requests, and changed nothing in the repository. **It is not an
independent review**: same model, same session, same tools. Findings are
paraphrased from its report; dispositions are the executor's and were
re-checked against the regenerated data.

| Id | Severity | Finding (paraphrased) | Disposition |
|---|---|---|---|
| RV-01 | high | The Crossref `update-to` back-link counted as a second source is usually the Retraction Watch-sourced link itself, so "two sources agree" rested on one source for most events, including the POS-01 retraction. | Fixed. Each event now states its `independent_confirmation`; only publisher-sourced links count. 4 of 19 events have a publisher link of the same type (FEASIBILITY_REPORT.md §4.2). |
| RV-02 | high | "Marked 778 days after the retraction" is misleading: the revision before the first `{{Retracted}}` already reported the retraction in its text. | Fixed. 778 days is described as the delay of the reference template; a substring check of the two revisions is committed (`data/followups/en_mmr_retraction_text_check.json`; report §7.4; creative review B). |
| RV-03 | high | Gate 01-F was marked PASS while the manifest did not exist and `verify` had never run. | Fixed. The manifest is generated and the live re-verification result is committed (`data/verify_result.json`, report §9). |
| RV-04 | medium | The marker check missed `{{Retracted}}` placed right after a citation template outside `<ref>` (en "Andrew Wakefield", "John Walker-Smith"). | Fixed in `marked()`. English marked pairs 47 → 49; cross-wiki marker split corrected to 4 / 6 / 1 / 0. |
| RV-05 | medium | With no enclosing `<ref>` or template, the reference span fell back to the first template of the page (Halomonadaceae recorded a short-description template). | Fixed: the span falls back to the line. |
| RV-06 | medium | No DOI boundary check: `10.1109/fitme.2009.11` matched inside `10.1109/FITME.2009.112`. Two sample DOIs are prefixes of other DOIs. | Fixed with a tail lookahead; re-derived. |
| RV-07 | medium | Notice citations could be counted as paper citations: `{{Retracted|doi=X}}`, a wikilink pipe in a title, or a bare-text notice reference. | Partly fixed: `{{Retracted|doi=}}` is its own non-identifier role; `{{!}}` and wikilink pipes are neutralized. Bare-text notice references remain a documented limitation (report §8.3 item 18). |
| RV-08 | medium | NC-03 used the NEJM notice DOI, which is in Retraction Watch as a notice, so "not found in checked sources" misdescribed it; "the 4 articles that cite it" was unsupported. | Fixed. NC-03 is now Watson & Crick 1953 (in neither Retraction Watch column, no Crossref update); the notice case is NC-04 and claims only the articles found by searches for the original DOI. |
| RV-09 | medium | NC-02 used the tested function as its own ground truth; "in any form" overclaimed; the Arabic negative is trivial. | Fixed. A separate plain-substring check (DOI suffix, PMID, PII, author name in two scripts) is committed; wording narrowed; the English revision that names Wakefield without a DOI was added; the trivial Arabic negative is labelled as such. |
| RV-10 | medium | Under PROTOCOL.md §7 the outcome is GO; the RESCOPE recommendation used reasons outside the pre-registered criteria without saying so. | Addressed. Report §12 now applies each criterion of PROTOCOL.md §7 explicitly. The later QA pass (below) showed that the reviewer's GO reading overlooked the third RESCOPE trigger (a method limitation forcing a narrower claim than the research question), which is met. GO's conditions and that trigger hold together; the protocol does not rank them; the recommendation is RESCOPE with this reasoning stated, and the reasons outside the criteria (prior art, rate limits) are labelled as such. |
| RV-11 | medium | Date disagreements other than Obokata were not marked `conflicting`. | Fixed. All original and event dates are compared at the coarser precision; disagreements are `conflicting` (case U-02). |
| RV-12 | medium | Undisclosed deviations: no cross-language follow-up for S, verifier renamed, wrong section pointer, added "marked" bisection, scripts modified after the data were produced. | Fixed. Report §11 items 5–9; S cross-language follow-up run; all data re-derived from cache with the final scripts (`scripts/reproduce.sh`). |
| RV-13 | medium (latent) | A failed fetch would count as "does not cite" in the cross-wiki counts and as absent in bisection. | Fixed. Bisection stops with an error on a failed fetch; cross-wiki counts failures separately (`linked_article_fetch_failed`). |
| RV-14 | low | Prior-art figures from the research subagent (RetractionBot edits, category sizes, Arabic template use) had no committed evidence. | Fixed. The API responses are committed in `data/followups/` and the figures re-read from them. |
| RV-15 | low | Small errors: Retry-After range, the one record with a different date format, number of negative controls, a section reference, interval rounding. | Fixed. Record 18930 is a genuine 1756 Philosophical Transactions retraction, not an impossible year, so the report says only that its format differs. |
| RV-16 | low | Cross-wiki compared marking differently on the two sides. | Fixed: both sides use the same `observe()` result. |
| RV-17 | low | The project's GitHub handle appears in the User-Agent strings; the MAESTRO brief attributed a vision to the owner without citing a message. | Brief now cites the owner's directive. The handle in the User-Agent is left for the owner to decide (raised in the pull request); the protocol requires a descriptive User-Agent with a project URL. |
| RV-18 | low | "Arabic cites far fewer of the sampled papers" was supported only by the purposive set, which the AI chose from English-centric knowledge. | Fixed. The random sample found no cited DOI in either language, so it does not support a language difference. The claim is now limited to the purposive set and labelled as not representative (report §1, §7.1, §12). |

## What the reviewer could not falsify

The §4.3 data-quality counts, the sample frame (61,868) and the 200 sampled
record ids, the purposive discovery and cross-wiki counts other than the
marker counts above, the 778- and 2,181-day gaps, the identifier-versus-
mention classification of every purposive observation, the sha1 of six
pinned revisions checked live, the missing Arabic `قالب:Retracted`, the
Clopper–Pearson implementation, and the absence of prevalence, causal or
"retracted means false" claims.

One reviewer statement is not relied on: that the 429 responses came from
Wikimedia's edge. Its evidence was not saved; report §8.2 states what the
committed log shows.

## QA pass after the fixes

A second same-model subagent checked every number and cross-reference in the
report set against the regenerated data files, read-only and without network
access (2026-10-27). It confirmed the counts listed in the review above and
the regenerated sample, verification and prior-art figures, and raised 11
issues, all handled before the evidence commit:

| # | Issue | Disposition |
|---|---|---|
| 1 | The GO recommendation ignored the third RESCOPE trigger. | Recommendation changed to RESCOPE with the overlap stated (report §1, §12; RV-10). |
| 2 | The MAESTRO brief attributed the 429 responses to Wikimedia. | Reworded: source not determined. |
| 3 | "When they do, their marking differs" overgeneralized. | Now "in 6 of the 11 pairs". |
| 4 | Article–paper pairs were called articles. | Pairs and distinct articles both given (33 pairs, 32 articles; 52 pairs, 46 articles). |
| 5 | The "fully retracted" prose claim rested on a bare count. | The check now stores quoted context with offsets; the sentence is in article prose. |
| 6 | The English template is `{{Retracted paper}}`, not `{{Retracted}}`. | Named; the marker check covers the `{{Retracted…` family. |
| 7 | Verification counts included duplicates and missed the NC-04 notice and the NC-03 Crossref record. | `verify` now fetches each item once, covers both, and reports distinct counts: 35 checks of 20 revisions and 9 Crossref works, 0 mismatches. |
| 8 | Retry counts, the 18930 date format, the CSV byte size and the Arabic template's creation date had no committed evidence. | Committed: the first-run request log, `file_bytes` and non-standard dates in the profile, and the template's first revision. |
| 9 | "Bursts of about 6 requests" overstated the log. | Now "runs of 1 to 6 successful requests; the first request was already refused". |
| 10 | The M1 cost estimate for S was too high. | Now about 3–4 hours (about 5 with M2). |
| 11 | Two generalizations beyond the data (publisher inconsistency, rarity of cited papers). | Limited to "3 of the 10 purposive papers" and "in this frame and by this method". |
