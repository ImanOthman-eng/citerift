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

## Corrective pass of 2026-10-27

The owner asked for one bounded correction cycle (FEASIBILITY_REPORT.md §15).
The executor's own audit against the owner's list found defects D1 to D8 of
report §15.1, including the one that changed a result (7 Arabic sample
searches recorded as complete). Consequential counts were then re-derived
from the raw cached responses by separate code, not by the probe's
classifiers.

A same-model subagent then reviewed the uncommitted changes read-only and
without network access, from four angles (technical, scientific, creative,
integration). It re-derived the sample results per wiki and date, both
Clopper–Pearson bounds, the cross-wiki states, the render states, the
clean-reproduction result and the Retraction Tracker counts with its own
code, all consistent, and found the manifest byte-identical on regeneration.
It is **not an independent review**: same model, same session. It raised 18
findings (0 high, 3 medium, 15 low), all handled before the evidence commit:

| # | Severity | Finding (paraphrased) | Disposition |
|---|---|---|---|
| 1 | medium | "40 of 46 tests fail against the old probe, which shows they detect the defects" overstates: most link-lookup failures are missing output fields, not caught defects. | Reworded (report §15.1): behavioural failures named for the discovery and client tests; D2 shown directly on the old code. |
| 2 | low | An HTTP 200 body that is not JSON was cached. | Fixed; test added (D9). |
| 3 | low | Attempts did not record API error codes, so retried error bodies looked like repeated 200s in logs. | Fixed; test added (D9). |
| 4 | low | The render check matched DOI prefixes and could read "RETRACTED" in a cited title, or the Arabic stem سحب in an unrelated word, as a warning. | Boundary rule and `<cite>` exclusion added with tests; the stem limitation is stated. Render states unchanged. |
| 5 | low | The Stage 01 tests are not collected by CI or by plain `uv run pytest`. | Stated in report §9 and the handoff; changing repository test configuration is outside Stage 01. |
| 6 | low | The sample is a simple random sample, not systematic. | Corrected in the report and `data/README.md`; PROTOCOL.md left unchanged, noted in §8.1. |
| 7 | low | "95% upper bound" is the upper end of the two-sided 95% interval (a 97.5% one-sided bound). | Reworded; one-sided 95% values given. |
| 8 | low | "Such citations are rare" read as prevalence. | Bounded to the rate discoverable by M2 (§12). |
| 9 | low | The committed sample file does not itself show the 7 re-sends. | Provenance stated in §8.1 and `data/README.md`. |
| 10 | low | The Tracker's "one verdict in twenty" sits beside 29 of 119 disagreements, and the about-page claims had no committed quotation. | Tension noted; quotations and the page hash added to the profile. |
| 11 | low | "No personal name" in the User-Agent conflicted with RV-17's point about the login. | Reworded (§15.3): no legal name; the login appears in the repository URL. |
| 12 | low | "One positive and one negative case" overstated NC-03's reproduction, and the request count was wrong. | NC-03 described as a lookup control; 15 requests stated. |
| 13 | medium | Revision-pinned provenance per finding was claimed as not established, but the Tracker publishes revision ids and hashes. | Narrowed to the distinct combination (snapshot hash, notice check, sha1, live re-verify). |
| 14 | medium | The Visible Warning Integrity states were called cumulative, though the render outcomes exclude each other, and the probe's `reference_not_found_in_render` and `mixed` were missing. | States restructured; MAESTRO CP-7 aligned. |
| 15 | low | The §2.2 acceptance categories did not match the probe's lookup states. | Aligned with the full state lists. |
| 16 | low | Sample sizes count answered items, and the gate is a paired comparison. | Both stated in CREATIVE_FEASIBILITY.md §5. |
| 17 | low | `data/README.md` glob and producer statements were inaccurate. | Corrected. |
| 18 | low | The MAESTRO ownership table omitted MR-17a/b, MR-24, MR-25 and CP-7. | Assigned. |

Also handled: the handoff's "86 purposive search responses" now says they
are M1 and M2 responses; a cosmetic strict-typing issue in the probe was
fixed.

## Strengthening pass of 2026-10-27 (census)

No reviewer agent was used in this pass. The executor checked its own work;
**this is a self-review by the same model, not independent verification.**
What was checked, and what it changed:

| # | Check | Result | Action |
|---|---|---|---|
| 1 | Does the dump scan find what live discovery found? | 19 of 20 purposive paper–language pairs identical; the exception is a citation with no external link (`data/census/dump_vs_api_crosscheck.json`). | Reported as the method's blind spot (FEASIBILITY_REPORT.md §16.2, §16.7 item 1). |
| 2 | Are the dumps the published files? | All six sha1 values equal those in the run's `dumpstatus.json`; the script refuses any other file. | None needed; a test covers the refusal. |
| 3 | First render run: 59 of 198 Arabic pairs were "not found in render". | Inspection of the cached HTML showed the citations sit in bibliography lists outside the footnotes, visible to readers. | The render check now also reads list items, paragraphs and definition items outside the footnotes, labelled as such; re-run from the cache: 2 remain not found. Tests added. |
| 4 | Is any failed request counted as absence? | Confirmation, divergence and history code keep `request_failed`, `missing`, `absent_from_response`, redirects and failed renders apart; one failed parse is logged and was re-sent. No attempt in this pass carried a MediaWiki error body. | Tests inject error bodies, missing pages and failed renders. |
| 5 | Do the counts in §16 match the data? | The counts were computed twice: by ad-hoc scripts during the run and by `stage01_census.py summarize`; they agree. | `census_summary.json` is the source quoted. |
| 6 | Wording that claims more than the data shows. | "lost in translation" (implies translation, not observed); "a reference list that was later replaced" (not checked); "never carried" for pairs where only the first revision was read. | Reworded to what was observed; the history category was renamed. |
| 7 | One test expectation was wrong (the position of a PMID match). | The code was right; the expected value was corrected, not the code or the check. | — |
| 8 | Could the census be read as prevalence? | Link-bearing citations only, dump of 2026-10-01, Retraction Watch only. | Stated as lower bounds wherever a count is quoted. |
| 9 | Disputed Shi et al. median. | The arXiv v3 full text says 3.68 years throughout; the published abstract says 5.8; the published text was refused (HTTP 403) and no workaround was attempted. | The median is no longer used as a fact. |
| 10 | Do Stage 00 files change? | `git diff ac779a7 -- <Stage 00 owned paths> pyproject.toml` is empty; the tests moved into `tests/stage01/`, inside the existing `testpaths`. | — |
