# Stage 01 Creative Differentiation Review — Prior Art and Originality Hypotheses

Required by the Creative Differentiation rule. It asks one question: what
would CITERIFT add that existing tools and research do not, and how could a
later stage prove it? Every contribution below is a **proposal for a later
stage**, not a built feature. Evidence labels: **[V]** primary source opened
on 2026-10-26 (by this stage's executor or its research subagent, see
FEASIBILITY_REPORT.md §10); **[S]** search snippet only; **[I]** inference.

## 1. Prior art found

| Work | What it does that overlaps CITERIFT | Limits relevant to CITERIFT | Label |
|---|---|---|---|
| **RetractionBot** (English Wikipedia bot, operators Samwalton9 and mdann52, code `cookies52/RetractionBot`) | Downloads the Retraction Watch data, finds retracted DOIs and PMIDs cited on Wikipedia and inserts `{{Retracted}}` next to them. Still active: latest edits 2026-10-19 to 2026-10-23, edit summary "Flagging sources with dois highlighted by RetractionWatch". | Edits English Wikipedia only (global account: 1,673 edits, all on enwiki; none on arwiki). Flags; does not analyze context, history or other languages. | [V] |
| **`{{Retracted}}`** (enwiki) | Marks a citation as retracted; `intentional=yes` for deliberate citations. Category counts on 2026-10-26: 33 pages "citing retracted publications", 301 "intentionally citing". | Present only where someone or the bot added it. | [V] |
| **`قالب:مصدر مسحوب`** (arwiki "retracted source") | Arabic localization of `{{Retracted}}` (first revision 2021-11-06, `data/followups/ar_masdar_mashub_first_revision.json`), with an "intentional" parameter. | **0 transclusions in Arabic articles** on 2026-10-26. | [V] |
| **Shi, Yu, Romero, Horvát, "The Persistence of Retracted Papers on Wikipedia"**, PACM HCI (CSCW) 2026, doi:10.1145/3817014 | Revision-history study: 1,181 citations of retracted papers on **English** Wikipedia; 71.6% initially problematic (51.5% added before retraction, 20.1% added after without warning); median persistence 5.8 years (2,106 days) in the published abstract; RetractionBot flagging associated with faster correction. | English only. A research dataset and paper, not an interactive investigation tool. (arXiv v3 states a different median, 3.68 years; the published version is cited.) | [V] |
| **Nicholson et al.**, FEBS J. 2021, doi:10.1111/febs.15608 | Citation-quality study; reported (per Shi et al.) 118 retracted articles cited across 297 Wikipedia pages. | English; general citation quality. | [V] via Shi et al. |
| **Wikipedia Citations** (Singh, West, Colavizza, QSS 2021, doi:10.1162/qss_a_00105) and **Kokash & Colavizza**, QSS 2026, doi:10.1162/qss.a.401 | Bulk citation extraction from dumps; the 2026 pipeline maps citation templates of **15 languages** to a common structure. | Dump-based snapshots; whether Arabic is among the 15 languages was not checked. No retraction analysis. | [V] (Arabic: not checked) |
| **Phabricator T120502** (2015 Community Wishlist) | Request for a tool that takes DOIs and lists every article citing them, highlighting the paragraphs, "hopefully … across multiple wikis and languages". | Open, needs triage, no assignee: the need is documented and unmet. | [V] |
| **"wikipedia-retraction-tracker"** (GitHub `jcpark376`) — the closest match to "Retraction Tracker for Wikipedia" | Described as "Trawls, checks, and marks claims in Wikipedia based on retracted articles". | Repository could not be opened from this environment (GitHub access is limited to the project repository); languages, data, license and status unknown. | [S] |
| **Crossref REST API `updated-by` / `update-to`** | Since 2025 carries Retraction Watch events (`source: retraction-watch`) beside publisher deposits (`source: publisher`). | A delivery channel for the same Retraction Watch data, not an independent second source (FEASIBILITY_REPORT.md §4.2). | [V] |
| **Wikidata P5824** "retracted by" (Arabic label "سحبها"); **Scholia** | Structured retraction links between items. | Coverage not measured here; Scholia's Toolforge instance reports partial data after the Wikidata graph split. | [V] |
| Zotero retraction alerts; Problematic Paper Screener (incl. Feet of Clay); LibKey Nomad; scite Reference Check | Flag retracted references for authors and readers of papers. | Not about Wikipedia articles or language editions. | [V] (scite: [S]) |

**What this shows [I]:** detecting and flagging retracted citations on English
Wikipedia is solved and running (RetractionBot), and the English-language
"how long do retracted citations persist" question has a published answer
(Shi et al. 2026). A CITERIFT that only lists retracted citations on English
Wikipedia would duplicate both. No tool or study found compares language
editions, and the Arabic retraction template exists but is unused in articles.
The cross-language question in the Master Plan is therefore the open part.

## 2. Proposed contributions

For each: value, competing functionality, what is new or unproven, required
evidence, Stage 01 feasibility evidence, limitations, owner stage, and a
testable acceptance criterion. Stage 01 results are summarized from
FEASIBILITY_REPORT.md.

### A. Cross-Wiki Evidence Divergence

- **Value:** shows readers and editors where language editions disagree in
  how they cite and mark the same retracted paper.
- **Competition:** none found that compares editions (§1). RetractionBot and
  Shi et al. cover English only.
- **New / unproven:** new as a tool; whether divergence is common beyond the
  purposive cases is unproven (Arabic citations are sparse).
- **Required evidence:** pinned revisions of interlanguage-linked articles,
  identifier-level citation detection, marker detection that also checks
  rendering.
- **Stage 01 feasibility:** demonstrated on the purposive set. Of 33
  English article–paper pairs (32 articles) for three retracted papers, 11
  have no Arabic article, 11 have one without the citation, 11 have one with
  it; within those 11 pairs, the wikitext marker `{{Retracted}}` differs in 6 (English only), and
  the Arabic markers do not render (FEASIBILITY_REPORT.md §7.2, §7.3).
- **Limitations:** articles, not claims, are linked; absence in one edition
  is not a missing correction; small Arabic counts.
- **Owner stage:** 07 (logic), 08 (presentation).
- **Acceptance criterion:** for every paper in a fixed evaluation list, the
  report lists each linked article pair with both revision ids and one of
  {both cite, one cites, linked article missing}, and an independent manual
  check of a random 20 pairs agrees on all of them.

### B. Retraction Response Timeline

- **Value:** shows when a citation was added and when a warning appeared,
  relative to the retraction date, per language.
- **Competition:** Shi et al. 2026 measure persistence on English Wikipedia
  in a research dataset; no interactive, per-paper, multi-language timeline
  was found.
- **New / unproven:** the per-paper bilingual view is new; reliability on
  articles where citations are removed and re-added is unproven.
- **Required evidence:** event history (Retraction Watch), revision history
  with first-citing and first-marking revisions, explicit assumptions.
- **Stage 01 feasibility:** demonstrated for one paper in two languages:
  English first cited by DOI in 2007; `{{Retracted paper}}` first at the
  reference on 2012-03-25, 778 days after the retraction, although the
  article prose already said the Lancet "fully retracted the original paper"
  in the revision before (when that sentence first appeared was not
  measured); Arabic cited and marked in the
  same 2016 revision, but the marker does not render (FEASIBILITY_REPORT.md
  §7.3, §7.4). Bisection costs about 12–17 revision fetches per question.
  The template date measures the reference marker, not the first warning to
  readers.
- **Limitations:** bisection assumes monotonic presence; references without
  a DOI are invisible; warnings in article prose are not detected by a
  template check; no causal explanation of edits.
- **Owner stage:** 07 (computation), 08 (display).
- **Acceptance criterion:** on a set of at least 10 (paper, article) pairs,
  first-citing and first-marking revisions found by the tool equal those
  found by a full linear scan of the history.

### C. Citation Autopsy

- **Value:** shows the exact reference and the sentence it supports, so a
  human can judge whether the claim relies on the retracted paper.
- **Competition:** RetractionBot marks the reference but gives no analysis;
  the reference checkers in §1 work on manuscripts, not Wikipedia.
- **New / unproven:** context extraction across Arabic and English wikitext
  is unproven; Stage 01 extracted only the reference markup.
- **Required evidence:** pinned revision, reference markup, the text the
  reference is attached to (including reused named references).
- **Stage 01 feasibility:** partly shown: the enclosing reference was
  extracted for every observation; identifier-versus-mention classification
  already prevents one real error class (notice cited as paper, FEASIBILITY_REPORT.md §5.3).
- **Limitations:** reused references, templates, lists and tables.
- **Owner stage:** 05.
- **Acceptance criterion:** on an annotated set, the extracted supported
  sentence matches the annotators' choice in at least a pre-registered share
  of cases, reported with its interval.

### D. Evidence Passport

- **Value:** every finding carries its sources: snapshot hash, record id,
  notice check, revision id and sha1, retrieval time, method, epistemic
  status.
- **Competition:** none of the tools found exposes provenance at this level.
- **New / unproven:** the format exists as the Stage 01 manifest; user value
  is unproven.
- **Required evidence:** as in EVIDENCE_MANIFEST.json.
- **Stage 01 feasibility:** demonstrated: the manifest is generated from
  data files and re-verified against live sources by `verify`.
- **Limitations:** sources change (new snapshots, new revisions); a passport
  is true for its retrieval time.
- **Owner stage:** 04 (record), 05 (context), 08 (display).
- **Acceptance criterion:** for every passport produced in the demo,
  re-verification of its pinned revisions and notices reports 0 mismatches.

### E. Knowledge Ripple

- **Value:** a graph of papers, notices and citing articles across
  languages.
- **Competition:** Scholia shows scholarly graphs from Wikidata, not
  Wikipedia citation states.
- **New / unproven:** as a view over CITERIFT's own verified records it is
  new; whether it helps users more than a table is unproven.
- **Required evidence:** the cross-language rows and events above; nothing
  beyond observed edges.
- **Stage 01 feasibility:** the data for a small graph exists (10 papers,
  63 article–paper citation pairs, 11 en/ar pairs); no visualization was
  built.
- **Limitations:** small graphs per paper; risk of decoration without
  insight.
- **Owner stage:** 08.
- **Acceptance criterion:** every node and edge in the rendered graph links
  to a record in the investigation; a test fails on any unlinked element.

### F. Investigation MAESTRO

- **Value:** a bounded, deterministic workflow that makes every investigation
  reproducible, resumable and honest about failures.
- **Competition:** RetractionBot is a batch editor; no investigation workflow
  of this kind was found.
- **New / unproven:** the design is a proposal (MAESTRO_DESIGN_BRIEF.md);
  nothing is implemented.
- **Required evidence:** the acceptance tests AT-01 to AT-11 of the brief.
- **Stage 01 feasibility:** the Stage 01 probe already shows the needed
  mechanics in miniature (cached, throttled, retried requests; confirmation
  checkpoints; failure as `unavailable`).
- **Limitations:** rate limits make cold investigations slow (FEASIBILITY_REPORT.md §8.2).
- **Owner stage:** 04, 07; presentation 08.
- **Acceptance criterion:** AT-01 (deterministic replay) and AT-04 (injected
  failures give `partial`, never a negative finding) pass.

## 3. Proposals beyond the listed contributions

Classified as proposals; none is approved or built.

- **Rendered-warning check:** compare the wikitext marker with what the
  rendered page shows (Stage 01 found Arabic markers that do not render).
  Owner stage 07 or 08.
- **Notice-versus-paper guard:** report citations of retraction notices
  separately; Stage 01 found articles whose only occurrence of the paper's
  DOI is inside a citation of its notice (FEASIBILITY_REPORT.md §5.3, NC-04). Owner stage 03/04.

## 4. Originality hypotheses to test later

| Id | Hypothesis | Test | Stage |
|---|---|---|---|
| H-1 | Linked English and Arabic articles differ in citing or marking the same retracted paper in a substantial share of pairs. | Count over a fixed paper list, with numerator and denominator. | 07 |
| H-2 | Arabic markers of retraction are less often visible to readers than English ones. | Rendered-page check over all citing pairs. | 07/08 |
| H-3 | A citation-context view helps reviewers decide reliance faster or more accurately than the reference alone. | Small user test with a baseline. | 05/08 |

None of these is a finding yet.
