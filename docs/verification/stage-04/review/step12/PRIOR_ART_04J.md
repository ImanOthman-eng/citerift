# Stage 04 Step 12: primary-source prior-art review (gate 04-J)

Owner authorization: Step 12 message `cmsg_018VCB51nDHP6HXmLU4ea5yPTS6uNNfzMEoiA4s4Jo33LV` (2026-11-17), section 16
and 17. Plan section 13 lists the systems to check: Retraction Tracker for Wikipedia, RetractionBot, Zotero's
Retraction Watch integration and Crossmark. This review adds the Crossref REST API and the Retraction Watch Database
(the data source of every system here), one peer-reviewed-track study (Shi et al.) and two further tools (scite,
Problematic Paper Screener).

## 1. Method and evidence rules

- Pages were fetched on **2026-11-17** over HTTPS from this session's network. Each fetch was done by a separate
  read-only web-fetch context that returned quotes (each under 125 characters) and an explicit "not stated" for
  every field the page did not cover. The fetch reports are kept in the Step 12 working notes; the quotes below are
  taken from them.
- **Only what a page states is recorded.** Where a page was truncated and the tail came back as a model-extracted
  summary rather than verbatim text, the item is marked **[summary]**. Where a page could not be read, the system is
  listed with the failure and no capability is inferred.
- **No "first", "unique" or "unprecedented" claim** is made anywhere in this document. Absence of a property from a
  reviewed page is not evidence that the system lacks it (plan section 13: "Absence from a reviewed page is not
  global uniqueness").
- Stage 01's earlier profile of Retraction Tracker for Wikipedia (`docs/verification/stage-01/CREATIVE_FEASIBILITY.md`)
  belongs to the Stage 01 agent. It is not repeated or extended here; the tracker's About page was read again
  independently.

## 2. Systems reviewed

Legend: "n/s" = not stated on the pages read.

### 2.1 Retraction Tracker for Wikipedia

| Field | Recorded |
|---|---|
| URL, accessed | https://retractions.thinkingpark.com/about (HTTP 200), 2026-11-17. About page has no last-updated date; it says "Updated each day". https://github.com/jcpark376/wikipedia-retraction-tracker returned **HTTP 404**; its relation to the site is not determinable. |
| Maintainer | "Built by Thinking Park" [summary]; states it is not affiliated with Wikipedia, the Wikimedia Foundation or Retraction Watch [summary]. |
| Input | English Wikipedia articles and revisions [summary]; the Retraction Watch Database, published by Crossref; Wikimedia page views; a monthly link dump; Cochrane withdrawal notices [summary]. Snapshot versions: n/s. |
| Output granularity | Passage level: each sentence, list item or table row resting on a retracted paper is one "finding"; cards group passages per article. Severities. |
| Retraction / EoC / correction / notice vs original | Retractions covered. Expressions of concern and corrections: n/s. Notice vs original paper: n/s. |
| Identity handling | DOI and PubMed ID. A "Check the citation" step flags footnotes whose PubMed ID and title name another paper. Conflict handling beyond that: n/s. |
| Provenance / auditability | Each finding cites a Wikipedia revision id, a finding id and a passage link [summary]; model quotes are checked "word for word" against the article. Content hashes: n/s. A findings data file exists [summary]. |
| Replay / determinism | Not stated as reproducible; the model "sometimes answers differently" on repeated comparisons [summary]. Uses AI language models to read articles and papers ("The models never write Wikipedia text"). |
| Multilingual scope | English Wikipedia [summary]; other languages n/s. |
| Edits Wikipedia | No: "It never edits Wikipedia itself. People do that." |

**Overlap with CITERIFT.** Both read Wikipedia citations against Retraction Watch data, match by DOI and PMID, anchor
findings to a revision, and do not edit Wikipedia. The tracker's footnote check (PMID and title naming another
paper) is an identity cross-check in the same spirit as CITERIFT's pair query. The tracker is far wider in reach:
daily over English Wikipedia, with sentence-level reading, page views and severities.

**Difference (as documented).** CITERIFT Stage 04 has no AI reading of claims: its verdict is a fixed first-match
table (dt-1) over Stage 02 lookups, with typed abstentions, and the same inputs replay to the same claim, evidence
and question ids. It covers Arabic as well as English (Stage 03 profiles). It separates notices from originals
(`NOTICE_CITED`, never positive) and expressions of concern, corrections and reinstatements from retractions. It is
not sentence-level and makes no statement about how a passage relies on a paper; it reports citation units only.

### 2.2 RetractionBot (English Wikipedia)

| Field | Recorded |
|---|---|
| URLs, accessed 2026-11-17 | BRFA https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/RetractionBot ; https://en.wikipedia.org/wiki/User:RetractionBot (last edited 2026-11-08) ; https://en.wikipedia.org/wiki/Template:Retracted/doc (last edited 2026-09-03) ; Signpost https://en.wikipedia.org/wiki/Wikipedia:Wikipedia_Signpost/2024-06-08/Special_report (article verbatim, comments [summary]) ; https://github.com/cookies52/RetractionBot (fork of Samwalton9/RetractionBot) |
| Maintainer | Operator Samwalton9 (BRFA, filed 2019-04-21, approved 2019-04-28); now "operated by Samwalton9 ... and mdann52" (User page). |
| Input | 2019: Crossref API, items flagged "retracted or withdrawn". Now: "downloads the Retraction Watch database (a CSV file)" (User page); README: "as reported by Crossref". |
| Output | An edit: appends {{Retracted}} (or the expression-of-concern template) to the citation, with the retraction DOI/PMID. Daily; README: flagged "within 24 hours". |
| Retraction / EoC / correction / notice | "The bot handles retractions and expressions of concern. {{Erratum}} is not handled by the bot." Notice vs original: the retraction notice's identifier is linked in the template; separate treatment of a citation that cites the notice itself: n/s. |
| Identity handling | "cross-checks the retracted DOIs and PMIDs ... against those cited in articles". Conflicts between a citation's DOI and PMID: n/s. |
| Provenance / audit | Edits visible in Special:Contributions; kill switch User:RetractionBot/run. "does not verify retractions independently"; "Coverage may be incomplete". |
| Replay / determinism | n/s. |
| Multilingual scope | README: "It currently runs only on the English Wikipedia". |
| Known problems | Signpost 2024: "several Cochrane Reviews were flagged as retracted for technical reasons, while they were never retracted in actuality. The bot was put on hiatus"; the 2019 bot "only ran for a few months". |

**Overlap.** Same data source (Retraction Watch), same identifiers (DOI, PMID), same unit (a cited reference), and
retraction vs expression of concern is separated.

**Difference.** RetractionBot writes to Wikipedia and acts in production on English Wikipedia; CITERIFT reads only
and has no production deployment. CITERIFT records why a verdict was or was not reached (rule, reasons, evidence
set, open questions) and replays it offline; the reviewed pages state no such record for the bot. The Cochrane
episode is the kind of source-side error that CITERIFT's `CONTRADICTION_IN_SOURCES` and abstention classes are meant
to surface rather than act on, but CITERIFT has not been measured on that case.

### 2.3 Zotero retracted-item notifications

| Field | Recorded |
|---|---|
| URL, accessed | https://www.zotero.org/blog/retracted-item-notifications/ (HTTP 200; dated 2019-06-14), 2026-11-17. https://www.zotero.org/support/retracted_items returned **HTTP 404**. |
| Maintainer | Zotero, "in partnership with Retraction Watch". |
| Input | Items in a user's library that carry a DOI or PMID (about three quarters of Retraction Watch data, per the post). |
| Output | Item flagged in the library list, warning in the item pane with retraction details and links, warning in the word-processor plugin when citing. |
| Retraction / EoC / correction / notice | n/s. |
| Identity handling | Partial identifiers are checked against the service (a privacy measure), then the full identifier is matched locally. Conflict handling: n/s. |
| Provenance / replay | n/s. Behaviour after version 5.0.67 (2019): n/s. |
| Multilingual / Wikipedia | Not about Wikipedia. |

**Overlap.** DOI/PMID match against Retraction Watch for cited works. **Difference.** Zotero works on a personal
library at citation-writing time; CITERIFT works on a pinned Wikipedia revision and keeps an auditable record.

### 2.4 Crossref REST API and Crossmark

| Field | Recorded |
|---|---|
| URLs, accessed 2026-11-17 | https://www.crossref.org/blog/retraction-watch-retractions-now-in-the-crossref-api/ (2025-01-29); https://www.crossref.org/documentation/crossmark/ (last updated 2020-04-08); https://www.crossref.org/documentation/register-maintain-records/maintaining-your-metadata/registering-updates/ (last updated 2024-05-27) |
| Maintainer | Crossref; Crossref acquired the Retraction Watch database in September 2023 (blog). |
| Input / output | Publisher deposits plus Retraction Watch data. REST API `update-to` entries with fields DOI, type, source, label, record-id. "The source field ... can have two values: publisher or retraction-watch"; "the same retraction may be included multiple times from different sources". Crossmark shows "the current status of an item of content, including any corrections, retractions, or updates". |
| Notice vs original | A notice "will have a different DOI from the document that it corrects"; "RN updates article A is only recorded in the RN's Crossmark deposit", and the API marks the original as updated by the notice. |
| Identity | DOIs. |
| Wikipedia | Not mentioned. |

**Overlap.** Crossref's model of a notice as a separate DOI linked to the original is the same distinction CITERIFT
enforces when a citation cites the notice. **Difference.** Crossref is a metadata registry and API, not a citation
checker; it does not read Wikipedia.

### 2.5 Retraction Watch Database (the data source)

| Field | Recorded |
|---|---|
| URLs, accessed 2026-11-17 | https://retractionwatch.com/retraction-watch-database-user-guide/ ("updated October 23, 2024"); https://gitlab.com/crossref/retraction-watch-data (created 2024-09-02; "Daily updates to Retraction Watch data"; 592 commits, 0 tags; licence n/s on the landing page) |
| Maintainer | The Center for Scientific Integrity; distributed by Crossref. |
| Types | "Retraction or Other Notices" covers retractions, corrections, expressions of concern and reinstatements; "we do not aim for comprehensiveness in expressions of concern (EOCs) or corrections (CNs)". |
| Identity | DOI and PMID searchable "for either original paper, notice, or both". |
| Versioning | Entries are "added or amended"; changes appendix (not fetched). The Crossref blog says the CSV is updated "on working days"; the GitLab page says "Daily". |
| Citation | "The Retraction Watch Database [Internet]. New York: The Center for Scientific Integrity. 2018. ISSN: 2692-4579." |

CITERIFT pins one snapshot (receipt and SHA-256, Stage 02) because the database changes; this follows from the
user guide's own statement that entries are amended.

### 2.6 Shi, Yu, Romero, Horvát: "The Persistence of Retracted Papers on Wikipedia"

| Field | Recorded |
|---|---|
| URL, accessed | https://arxiv.org/abs/2509.18403 (v1 2025-09-22, v3 2026-01-26; "Preprint. Under review at a peer-reviewed conference"), 2026-11-17. Sections 3.3 to 5.2 were read only as a [summary]. A journal DOI was not found on the pages read and is not cited. |
| Kind | A measurement study, not a tool. English Wikipedia only. Data collected October 2024. |
| Input | Retraction Watch, Crossref Events, Altmetric, OpenAlex, Wikipedia revisions and page views. "we excluded the ones with expressions of concern or corrections." |
| Unit / method | "retracted paper–Wikipedia page citation pairs"; 1,181 pairs; DOI-based discovery (Crossref Event API "only indexes papers with valid DOIs"); manual check of the citing revisions. |
| Findings (abstract) | 71.6% of citations "initially problematic"; median persistence "3.68 years (1,344 days)". Table A4: a RetractionBot flag has hazard ratio 2.34 (1.91–2.86) for correction. |
| Code / data | No repository found in the parts read verbatim. |

**Relevance.** Independent evidence that the problem CITERIFT addresses exists and persists on English Wikipedia,
and that automated flags are associated with faster human correction. It is not a competing tool.

### 2.7 Tools that could not be assessed

- **scite** (https://scite.ai, https://scite.ai/extension-install, https://scite.ai/llms.txt read; help centre
  HTTP 403). The pages state alerts "about retractions and editorial notices" and a Reference Check for
  "retractions, editorial notices, and contrasting evidence". Data source, type distinctions, identity matching and
  Wikipedia: n/s. **Not compared.**
- **Problematic Paper Screener / Feet of Clay detector** (https://www.irit.fr/~Guillaume.Cabanac/problematic-paper-screener/):
  the page returned only "Redirecting..."; nothing was read. **Not compared.**

## 3. Differentiation statement (section 17)

**Existing ideas, documented above.** Matching cited DOIs and PMIDs against Retraction Watch (RetractionBot, Zotero,
Retraction Tracker); separating expressions of concern from retractions (RetractionBot, Retraction Watch, Crossref
types); treating a notice as a separate DOI from the original (Crossref); anchoring findings to a Wikipedia revision
(Retraction Tracker); a cross-check of one citation's identifiers (Retraction Tracker's PMID-and-title check); daily
English Wikipedia coverage (Retraction Tracker, RetractionBot). None of these is claimed for CITERIFT as new.

**CITERIFT's combination, as built and tested in Stage 04 (development evidence only).**
1. A typed, abstention-first verdict per citation unit from a fixed, versioned first-match table (dt-1, 17 rules),
   with fifteen classes that keep notice, concern, correction, reinstatement, contradiction, identity conflict,
   unavailability and "not found in the checked sources" apart; absence is never reported as "not retracted".
2. A pair query that cross-examines a citation's DOI and PMID through the source's own records (κ), routing a
   witnessed conflict to an open question rather than a finding.
3. Content-addressed evidence chains and an append-only journal, so a verdict replays offline to identical ids from
   a pinned Wikipedia revision and a pinned Retraction Watch snapshot.
4. Arabic and English Wikipedia through the Stage 03 extraction profiles.

Whether this combination reduces false attachments relative to a naive lookup is **not yet measured**: the Step 9
preview (43 notice or marker occurrences, 1 concern marker, 1 identity conflict on design-exposed data) is not
evidence for the contribution. Only the frozen engine on the pre-registered holdout (Step 13 onwards) can measure
it. Coverage is far smaller than Retraction Tracker's or RetractionBot's, and CITERIFT reads no sentence context.

**No claim** that CITERIFT is the first, the only or an unprecedented system of any kind is made or supported by
this review.

## 4. Limits of this review

- Pages read on one day; tools change. Behaviour not documented on a page was not inferred.
- Parts of three pages (Retraction Tracker About tail, the Signpost comments, the middle of Shi et al.) were read only
  as summaries and are marked.
- scite and Problematic Paper Screener were not assessable; the Retraction Tracker GitHub repository was 404.
- No system was run or tested; this compares documentation, not measured behaviour.
