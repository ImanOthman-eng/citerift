# Stage 01 Creative Differentiation Review — Prior Art, Signature Capabilities and Strategy

Required by the Creative Differentiation rule. It asks one question: what
would CITERIFT add that existing tools and research do not, and how could a
later stage prove it? Every capability below is a **proposal for a later
stage**, not a built feature, and no stage after 01 is authorized. Evidence
labels: **[V]** primary source opened by this stage's executor (or its
research subagent, FEASIBILITY_REPORT.md §10) on the date given; **[S]**
search snippet only; **[I]** inference or judgment.

First written 2026-10-26; revised 2026-10-27 in the corrective pass the owner
requested (FEASIBILITY_REPORT.md §15). The revision corrected the Shi et al.
figure, replaced an unopened prior-art entry with a verified one (the
Retraction Tracker for Wikipedia, a close English-language competitor), and
added §2 to §7.

## 1. Prior art found

| Work | Verified capabilities that overlap CITERIFT | Limits relevant to CITERIFT | Label |
|---|---|---|---|
| **RetractionBot** (English Wikipedia bot, operators Samwalton9 and mdann52, code `cookies52/RetractionBot`) | Downloads the Retraction Watch data, finds retracted DOIs and PMIDs cited on Wikipedia and inserts `{{Retracted}}` next to them. Still active: latest edits 2026-10-19 to 2026-10-23, edit summary "Flagging sources with dois highlighted by RetractionWatch". | Edits English Wikipedia only (global account: 1,673 edits, all on enwiki; none on arwiki). Flags; does not analyze context, history or other languages. | [V] 2026-10-26 |
| **Retraction Tracker for Wikipedia** (Thinking Park, <https://retractions.thinkingpark.com/about>, page dated 2026-10-27) | Daily: downloads the Retraction Watch data; finds English Wikipedia articles that cite retracted papers (monthly external-links dump plus daily queries); locates each citing sentence, list item or table row, following reused footnotes; an AI language model reads the article, judges whether the passage still states the paper's finding as fact, suggests an action and gives a confidence; quotes are checked word for word; locates retraction warnings in the article text and counts only those in the lead or the same section as "nearby"; ranks passages by square-rooted page views times three weights; never edits Wikipedia. Its data file (`findings.json`, generated 2026-10-27): 881 findings on 377 pages for 345 DOIs; statuses new 818, dropped 39, fixed 24, tracked since 2026-10-06; 573 findings list located warnings; one model identifier for all findings; 119 findings carry a `second_reading` value (90 "agreed", 29 "disagreed"). | English Wikipedia only in the reviewed evidence (its attribution names English Wikipedia; the data file has no language field). Its own stated limits: verdicts are machine-generated and only a few were checked by a person; the model changes about one verdict in twenty when asked twice; page views are per article, not per passage. (The 29 "disagreed" of 119 `second_reading` values do not measure that rate: which findings got a second reading, and how, is not stated in the reviewed evidence.) Its warning check reads article text; whether it checks how reference templates render was not established in the reviewed evidence. Relation to the GitHub repository `jcpark376/wikipedia-retraction-tracker` ([S] only, not opened) not established. | [V] 2026-10-27, `data/followups/prior_art_retraction_tracker_profile.json` |
| **`{{Retracted}}`** (enwiki) | Marks a citation as retracted; `intentional=yes` for deliberate citations. Category counts on 2026-10-26: 33 pages "citing retracted publications", 301 "intentionally citing". | Present only where someone or the bot added it. | [V] 2026-10-26 |
| **`قالب:مصدر مسحوب`** (arwiki "retracted source") | Arabic localization of `{{Retracted}}` (first revision 2021-11-06, `data/followups/ar_masdar_mashub_first_revision.json`), with an "intentional" parameter. | **0 transclusions in Arabic articles** on 2026-10-26. | [V] 2026-10-26 |
| **Shi, Yu, Romero, Horvát, "The Persistence of Retracted Papers on Wikipedia"**, Proc. ACM Hum.-Comput. Interact. (CSCW) 2026, doi:10.1145/3817014; preprint arXiv:2509.18403 | Revision-history study of 1,181 citations of retracted papers on **English** Wikipedia: 71.6% initially problematic (51.5% added before the retraction, 20.1% added after it without warning); survival analysis in which RetractionBot flagging is associated with faster correction. **Median persistence: the sources disagree.** The abstract in the paper's Crossref record (deposited by ACM, published 2026-09-23) says "a median of 5.8 years (2,106 days)"; arXiv v1 and v2 say "over 3.68 years (1,344 days)", arXiv v3 (2026-01-26) and the CSCW 2026 program page say "3.68 years (1,344 days)". The published full text could not be opened (ACM Digital Library: HTTP 403 to this environment), so which figure it reports is not established in the reviewed evidence. | English only. A research dataset and paper, not an interactive investigation tool. | [V] 2026-10-27, `data/followups/prior_art_shi_median_sources.json` |
| **Nicholson et al.**, FEBS J. 2021, doi:10.1111/febs.15608 | Citation-quality study; reported (per Shi et al.) 118 retracted articles cited across 297 Wikipedia pages. | English; general citation quality. | [V] via Shi et al. |
| **Wikipedia Citations** (Singh, West, Colavizza, QSS 2021, doi:10.1162/qss_a_00105) and **Kokash & Colavizza**, QSS 2026, doi:10.1162/qss.a.401 | Bulk citation extraction from dumps; the 2026 pipeline maps citation templates of **15 languages** to a common structure. | Dump-based snapshots; the abstract does not list the 15 languages, so whether Arabic is among them is not established in the reviewed evidence. No retraction analysis. | [V] |
| **Phabricator T120502** (2015 Community Wishlist) | Request for a tool that takes DOIs and lists every article citing them, highlighting the paragraphs, "hopefully … across multiple wikis and languages". | Open, needs triage, no assignee. | [V] 2026-10-26 |
| **Crossref REST API `updated-by` / `update-to`** | Since 2025 carries Retraction Watch events (`source: retraction-watch`) beside publisher deposits (`source: publisher`). | A delivery channel for the same Retraction Watch data, not an independent second source (FEASIBILITY_REPORT.md §4.2). | [V] |
| **Wikidata P5824** "retracted by" (Arabic label "سحبها"); **Scholia** | Structured retraction links between items. | Coverage not measured here; Scholia's Toolforge instance reports partial data after the Wikidata graph split. | [V] |
| Zotero retraction alerts; Problematic Paper Screener (incl. Feet of Clay); LibKey Nomad; scite Reference Check | Flag retracted references for authors and readers of papers. | Not about Wikipedia articles or language editions. | [V] (scite: [S]) |

### What this shows [I]

For **English** Wikipedia, the following already exist and are verified:
flagging of retracted references (RetractionBot), a published persistence
study (Shi et al.), and a daily, prioritized, sentence-level list with an AI
reading of whether a passage still relies on the paper and where the article
warns readers (Retraction Tracker). A CITERIFT that lists or ranks retracted
citations on English Wikipedia, or that offers an English sentence-level AI
verdict, would duplicate existing work and must not claim novelty for it.

Not established in the reviewed evidence (which is the list above, not an
exhaustive search):

- a tool or study that compares how **different language editions** cite and
  mark the same retracted paper;
- a check of whether a retraction **marker renders** as a warning, as
  distinct from being present in wikitext (Stage 01 found Arabic articles
  where it does not, §2.1);
- per finding, a **pinned retraction-data snapshot hash, a checked notice
  with its independence stated, the revision sha1, and a live re-verification
  of all of these** (EVIDENCE_MANIFEST.json, `verify`). Revision-pinned
  findings as such are not new: the Retraction Tracker publishes per-finding
  revision ids, model, prompt and input hashes.

These are the open parts. "Not established" is not "does not exist": a
later stage must repeat the search before any public novelty claim.

### Verified competitor capability versus proposed CITERIFT capability

| Capability | Verified in existing work | Proposed for CITERIFT (unbuilt) |
|---|---|---|
| Find retracted papers cited on English Wikipedia | RetractionBot, Retraction Tracker, Shi et al. | baseline only, no novelty claimed |
| Mark them in wikitext | RetractionBot (English) | none; CITERIFT never edits Wikipedia |
| Sentence-level context with an AI reliance verdict | Retraction Tracker (English) | advisory label, only if validated (§5) |
| Warning located in article text | Retraction Tracker (English; lead or same section) | rendered-marker check per language (§2.1) |
| Persistence statistics | Shi et al. (English) | none; per-paper timelines only (§2.3) |
| Compare language editions | not established | Cross-Wiki Divergence Lens (§2.2) |
| Provenance per finding | Retraction Tracker: revision ids, model, prompt and input hashes | Evidence Passport adds snapshot hash, notice check, sha1 and live re-verify (§2.4) |

## 2. Signature concept: Cross-Language Citation Forensics

One integrated idea: for a retracted paper, show **what each language
edition's readers are actually told**, at pinned revisions, with every value
traceable to its source. Six capabilities serve it. For each: value,
competition, what is new or unproven, required data, Stage 01 evidence,
limitations, owner stage, and a testable acceptance criterion. Stage numbers
follow the Master Plan; none of these stages is authorized.

### 2.1 Visible Warning Integrity

- **Value:** distinguishes a warning that exists in wikitext from one a
  reader can see. Stage 01 found that the Arabic `{{Retracted}}` marker
  points to a template that does not exist on Arabic Wikipedia.
- **States** (per citation, per pinned revision). Three cumulative
  evidence states, then exactly one render outcome:
  1. `event_verified`: a retraction event from the pinned snapshot with a
     resolving notice (FEASIBILITY_REPORT.md §4).
  2. `citation_observed`: the DOI is used as an identifier in the pinned
     revision (§5.3); requires 1.
  3. `marker_in_source`: a retraction template is at the reference in
     wikitext; recorded as yes or no, and not required for the render
     outcome (prose or other markup can warn too).
  Render outcome of the same revision, exactly one of:
  - `warning_visible_in_render`: every rendered reference citing the DOI
    contains warning text outside the citation itself and outside links to
    missing pages (probe: `warning_text_in_rendered_reference`);
  - `missing_template_link_only`: the only retraction wording is a link to a
    missing template page;
  - `warning_absent_in_inspected_render`: rendered references were found and
    none of the above applies (probe:
    `no_warning_text_in_inspected_rendered_reference`);
  - `mixed`: the references citing the DOI differ; reported per reference;
  - `reference_not_found_in_render`: no rendered reference contains the DOI
    (for example a template not expanded as expected); never read as
    absence of a warning;
  - `render_unavailable`: the render request failed or was malformed; never
    read as absence.
  A warning is called absent only from `warning_absent_in_inspected_render`
  or `missing_template_link_only` of an actual render, and the state names
  what was inspected (desktop parser HTML), not what every reader sees.
- **Competition:** Retraction Tracker locates warnings in English article
  text; a check of template rendering, or of other languages, was not
  established in the reviewed evidence.
- **New / unproven:** the per-language render check is new as a tool
  capability [I]; how common unrendered markers are beyond Stage 01's cases
  is unproven.
- **Required data:** pinned revision, wikitext marker check, `action=parse`
  of the same revision.
- **Stage 01 evidence:** rendered (parser HTML) check of four pinned
  revisions on 2026-10-27 (`data/followups/render_check_*.json`). English
  "Haruko Obokata" and "MMR vaccine": the citing reference ends with
  "(Retracted, see doi: …, PMID …, Retraction Watch)", `warning_visible_in_render`. Arabic
  "هاروكو أوبوكاتا" and "لقاح الحصبة والنكاف والحصبة الألمانية": the
  reference shows a link to the missing page "قالب:Retracted" and no
  retraction wording, `missing_template_link_only`. All four
  carry the marker in wikitext (state 3). Two pairs only; nothing about other
  articles.
- **Limitations:** parser HTML is not the mobile view, skins or gadgets; CSS
  could still hide text; one request per revision.
- **Owner stage:** 07 (check), 08 (display).
- **Acceptance criterion:** for every citing pair in the demo set, the state
  is computed from a stored render of the pinned revision; injected render
  failures yield `render_unavailable` and a reference missing from the
  render yields `reference_not_found_in_render`, never an absent warning; a
  manual inspection of 10 rendered references agrees with every state.

### 2.2 Cross-Wiki Divergence Lens

- **Value:** shows where linked articles in two languages differ in citing
  and marking the same retracted paper.
- **Competition:** not established in the reviewed evidence (§1).
- **New / unproven:** whether divergence is common beyond the purposive
  cases is unproven; Arabic citations are sparse.
- **Required data:** interlanguage links with explicit failure states
  (linked, no link, request failed, malformed answer), pinned revisions on
  both sides, identifier-level citation detection.
- **Stage 01 evidence:** of 33 English article–paper pairs (32 articles) for
  three retracted papers, 11 have no Arabic article, 11 have one without the
  citation, 11 have one with it; within those 11, the wikitext marker
  differs in 6 (FEASIBILITY_REPORT.md §7.2). The link lookup was rebuilt in
  this pass so that a failed request can no longer count as "no Arabic
  article"; the counts did not change (§15).
- **Limitations:** interlanguage links connect articles, not claims; an
  absent citation is not a missing correction.
- **Owner stage:** 07 (logic), 08 (presentation).
- **Acceptance criterion:** for every paper in a fixed evaluation list, each
  citing article is listed with its revision id, its link-lookup state
  (`linked`, `no_link`, `source_missing`, `request_failed`,
  `malformed_response`) and, when linked, the linked article's state
  (`doi_cited`, `doi_mention_only`, `doi_not_found`, `redirect`,
  `article_missing`, `fetch_failed`, `malformed_response`) with its revision
  id; a manual check of 20 random
  pairs agrees on all; injected 429 and 5xx responses never produce
  `no_link` or `doi_not_found` (the Stage 01 tests in
  `tests/test_crosswiki.py` are the model).

### 2.3 Retraction Timeline

- **Value:** shows, per language, how the citation and the warnings evolved
  relative to the retraction.
- **Intervals kept apart** (each with its revision ids, or `unknown`):
  first DOI-bearing citation; earliest retraction marker at the reference;
  earliest retraction wording in the article prose; earliest reader-visible
  warning (requires a render, §2.1); and any interval that was not measured,
  shown as unknown, not as zero or as the template delay.
- **Competition:** Shi et al. measure persistence statistically for English;
  no interactive per-paper, multi-language timeline was found.
- **Stage 01 evidence:** English "MMR vaccine": cited by DOI text in 2007;
  `{{Retracted paper}}` at the reference 778 days after the retraction, but
  the revision before already said in prose that the Lancet "fully retracted
  the original paper"; the first prose warning was not measured. Arabic:
  cited and marked in the same 2016 revision, with the marker pointing to a
  missing template (FEASIBILITY_REPORT.md §7.3, §7.4). Bisection costs about
  12–17 revision fetches per question.
- **Limitations:** bisection assumes a citation or marker, once added,
  stays; references without a DOI are invisible; no edit is explained.
- **Owner stage:** 07 (computation), 08 (display).
- **Acceptance criterion:** on at least 10 (paper, article) pairs, the
  first-citing and first-marking revisions equal those of a full linear
  scan; unmeasured intervals render as "unknown".

### 2.4 Evidence Passport

- **Value:** every statement carries its sources: snapshot hash, record id,
  notice check and its independence, revision id and sha1, retrieval time,
  method, epistemic status.
- **Competition:** the Retraction Tracker publishes per-finding revision
  ids, model, prompt and input hashes for its AI readings. A pinned
  retraction-data snapshot hash, a notice check with its independence, the
  revision sha1 and a live re-verification per finding were not established
  in the reviewed tools; only that combination is distinct.
- **Stage 01 evidence:** EVIDENCE_MANIFEST.json, generated from the data
  files and re-verified live by `verify` (FEASIBILITY_REPORT.md §9).
- **Limitations:** a passport is true for its retrieval time.
- **Owner stage:** 04 (record), 05 (context), 08 (display).
- **Acceptance criterion:** re-verification of every demo passport reports
  0 mismatches, and a passport with an injected wrong sha1 fails.

### 2.5 Citation Autopsy

- **Value:** shows the reference and the sentence it supports, so a person
  can judge reliance.
- **Competition:** **Retraction Tracker already does this for English**,
  including reused footnotes and an AI verdict. CITERIFT's version is only
  distinct as an input to the cross-language comparison (the same claim in
  two languages) and in Arabic, where it is unproven.
- **Stage 01 evidence:** only the reference markup was extracted;
  identifier-versus-mention classification prevents one real error class
  (notice cited as paper, NC-04).
- **Limitations:** reused references, templates, lists, tables, Arabic
  sentence segmentation.
- **Owner stage:** 05.
- **Acceptance criterion:** on a human-annotated set per language, the
  extracted supported passage matches the annotators' choice in at least a
  pre-registered share, reported with its interval.

### 2.6 Knowledge Ripple

- **Value:** a graph of a paper, its notices and the citing articles across
  languages.
- **Competition:** Scholia shows scholarly graphs from Wikidata, not
  Wikipedia citation states.
- **Stage 01 evidence:** data for a small graph exists (10 papers, 63
  article–paper pairs, 11 en/ar pairs); nothing was drawn.
- **Limitations:** small graphs; risk of decoration without insight.
- **Owner stage:** 08.
- **Acceptance criterion:** every node and edge links to a record in the
  investigation; a test fails on any unlinked element.

The **Investigation MAESTRO** (MAESTRO_DESIGN_BRIEF.md) is the deterministic
workflow under all six; it is infrastructure, not a user-facing feature.

## 3. Evaluation and classification [I]

Ratings are the executor's judgment from the Stage 01 evidence (H high, M
medium, L low); they are inputs to the owner's decision, not measurements.
"Judging" names the categories of the competition rules (§6) a capability
mainly serves.

| Capability | User value | Scientific validity | Distinct from existing tools | Complexity | Required data | Testability | Critical-path impact | Judging | Class |
|---|---|---|---|---|---|---|---|---|---|
| Evidence Passport | H | H (demonstrated) | M | L | already produced by the pipeline | H | on path (04) | Functionality, Problem and Impact | **CORE** |
| Cross-Wiki Divergence Lens | H | M (case-level only) | H (not established elsewhere) | M | langlinks + pinned revisions | H | on path (07) | Problem and Impact, Presentation | **CORE** |
| Visible Warning Integrity | H | H for inspected renders | H (not established elsewhere) | L–M | one parse per revision | H | small addition to 07 | Problem and Impact, Presentation | **CORE** |
| Retraction Timeline | M–H | M (bisection assumptions) | M | M | revision history, 12–17 fetches per question | H | 07; precompute 1–2 cases | Presentation, Learning and Growth | **HIGH-VALUE** |
| AI advisory label (Stage 06) | M | unproven; held-out evaluation required (§5) | L for English (Retraction Tracker) | M–H | annotated held-out sets per language | M | 06; must not block 07/08 | Use of AI | **HIGH-VALUE**, shipped only if it passes §5 |
| Citation Autopsy | M | M | L for English, M for Arabic | M–H | rendered or parsed article text | M | 05; feeds AI | Use of AI, Functionality | **HIGH-VALUE**, minimal form |
| Knowledge Ripple | L–M | H if every element is linked | M | M | the records above | H | none (presentation only) | Presentation | **OPTIONAL** |

Classification rule used: CORE = needed for the signature claim and already
supported by Stage 01 evidence; HIGH-VALUE = strengthens a judging category
but can be cut without losing the claim; OPTIONAL = presentation only.

## 4. Demo narrative mapped to stages and tests

Proposed for the Stage 08/09 demo, precomputed and cached (FEASIBILITY_REPORT.md
§8.2), each step showing its retrieval time. Candidate papers: Obokata 2014
(POS-02) or Wakefield 1998 (POS-01).

| Step | What is shown | Owner stage | Acceptance test |
|---|---|---|---|
| 1 Paper | Retraction events from the pinned snapshot, notice check and its independence | 02 | NC-01/NC-01b event types never reported as retractions; CP-1 to CP-3 of the MAESTRO brief |
| 2 English citation | Pinned revision, reference markup, identifier use | 03 | AT-02 (positive case end-to-end); NC-04 notice citations not counted |
| 3 Arabic counterpart | Interlanguage link with explicit lookup state; Arabic pinned revision | 07 | §2.2 criterion; injected failures never give "missing" |
| 4 Warning states | Visible Warning Integrity per side | 07, 08 | §2.1 criterion |
| 5 History | Retraction Timeline with unknown intervals marked | 07 | §2.3 criterion |
| 6 Evidence Passport | Every value with its source and a re-verify result | 04, 08 | §2.4 criterion; AT-01 deterministic replay |
| 7 AI advisory (only if validated) | Advisory usage label with abstention and "needs human review" | 06, 08 | §5 gate; AT-09, AT-11 |

If step 7 fails its gate, the demo shows the deterministic baseline and says
that the AI label was evaluated and not shipped (this still documents the use
of AI honestly).

## 5. Stage 06 AI evaluation plan (proposal)

- **Role:** label how a pinned citation is used (supports a claim; is about
  the paper or its retraction; discusses the retraction; abstain). AI never
  sets a retraction status, date, citation presence, warning state or
  cross-language difference (MAESTRO brief MR-18 to MR-20).
- **Deterministic baseline first:** rules from markup (`intentional=yes`,
  citation inside a section or article about the paper, notice cited
  alongside) give a baseline label or abstain. The AI is compared with it,
  not with nothing.
- **Held-out evaluation, independent of the model:** labels from people (the
  owner or recruited annotators), written before any model output is seen;
  the evaluation set is frozen and never used for prompt tuning. Another
  model's agreement is not independent evaluation (Retraction Tracker's own
  caveat illustrates the point).
- **Per-language sample sizes:** for a 95% interval of about ±10 percentage
  points on accuracy at worst case (p = 0.5, normal approximation), about 96
  labelled items per language; ±14 points needs about 50. Stage 01 found 11
  Arabic citing pairs for 10 purposive papers, so an Arabic set of 50–96
  needs a larger paper list; if fewer than 50 Arabic items can be labelled,
  the Arabic label is not shown.
- **Abstention reduces n:** the sizes above count answered items, so the
  labelled set must be larger by the expected abstention rate.
- **The gate is a paired comparison:** AI and baseline are scored on the same
  items, so the "beats the baseline" margin is tested with a paired test
  (McNemar) and needs its own sample-size calculation from the expected
  disagreement rate; the ±10-point figure sizes only a single accuracy.
- **Abstention:** reported as coverage; accuracy is reported on answered
  items, together with the share abstained. A schema-invalid or failed answer
  counts as abstention.
- **Pre-registered gate:** the AI label ships for a language only if, on the
  frozen set, its accuracy on answered items exceeds the baseline's by a
  margin fixed before evaluation, with coverage above a fixed floor;
  otherwise it is cut and the baseline remains.
- **Reporting:** model identifier and version, prompt hash, per-language n,
  accuracy with interval, abstention rate, confusion matrix; no claim beyond
  the evaluated languages.

## 6. Competition strategy

Judging (Devpost rules, read 2026-10-26,
<https://stem2connect-online-hackathon.devpost.com/rules>): five categories,
each 20%: Problem and Impact, Use of AI, Functionality, Learning and Growth,
Presentation; ties go to the higher Problem and Impact score. Projects must
work as shown, credit open data and APIs, disclose AI coding assistance, and
must not contain misleading content. No score is expected or claimed here.

How the proposals map [I]:

- **Problem and Impact:** the divergence and warning-visibility findings in
  Arabic are concrete and verifiable (§2.1, §2.2); the claim must stay at
  named cases (FEASIBILITY_REPORT.md §12).
- **Use of AI:** the AI label only counts if it passes §5; an honest
  evaluation that cuts it, plus the disclosed AI-assisted engineering, is the
  fallback. Avoid presenting an English AI verdict as new (Retraction
  Tracker).
- **Functionality:** a precomputed, re-verifiable investigation for 1–2
  papers that works every time beats a live, rate-limited search.
- **Learning and Growth:** the Stage 01 corrections (method pitfalls, error
  bodies, failure states) are documented material.
- **Presentation:** the §4 narrative in under 6 minutes, one paper, two
  languages.

Deadline risk: submission 2026-11-21 23:59 EST; on 2026-10-27, 25 days remain
and Stages 02–09 each need owner acceptance. Keep CORE small; cut OPTIONAL
first, then the AI label if its gate fails, then the timeline (precomputed
for one case only).

## 7. Originality hypotheses to test later

| Id | Hypothesis | Test | Stage |
|---|---|---|---|
| H-1 | Linked English and Arabic articles differ in citing or marking the same retracted paper in a substantial share of pairs. | Count over a fixed paper list, with numerator and denominator. | 07 |
| H-2 | Arabic retraction markers are less often rendered as warnings than English ones. | Rendered-reference check (§2.1) over all citing pairs of a fixed list. | 07/08 |
| H-3 | A citation-context view helps reviewers decide reliance faster or more accurately than the reference alone. | Small user test with a baseline. | 05/08 |
| H-4 | An AI usage label beats the deterministic baseline per language on a held-out human-labelled set. | §5. | 06 |

None of these is a finding yet.

## 8. Further proposal

- **Notice-versus-paper guard:** report citations of retraction notices
  separately; Stage 01 found articles whose only occurrence of the paper's
  DOI is inside a citation of its notice (FEASIBILITY_REPORT.md §5.3, NC-04).
  Owner stage 03/04.
