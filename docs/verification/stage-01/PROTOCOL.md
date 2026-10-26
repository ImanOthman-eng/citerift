# Stage 01 Research Protocol (fixed before data collection)

Stage 01 — Independent Feasibility Investigation. Written on 2026-10-26 and
committed before any Wikipedia query was run and before any case was
interpreted, so that the conclusions are not tailored to the cases found. The
only data looked at before this file was written: the Retraction Watch
snapshot's README, its row counts per record type, and the presence in it of
five well-known retracted DOIs (to confirm the file was readable). Any later
deviation from this protocol is recorded in FEASIBILITY_REPORT.md §9 with its
reason.

Scope: a bounded feasibility investigation, not a prevalence study. It asks
whether CITERIFT's core method can work on real data, and where it breaks.

## 1. Research questions

| Gate | Question |
|---|---|
| 01-A | Can retraction events (original DOI, notice DOI, event type, date) be obtained reproducibly from authoritative open sources, and do two sources agree? |
| 01-B | Can a citation of a given DOI be found in a specific, pinned Wikipedia revision with documented MediaWiki APIs? |
| 01-C | Does at least one real chain exist: original paper → verified retraction → Wikipedia citation → exact revision? Can negative controls be established? |
| 01-D | Do English and Arabic Wikipedia both contain discoverable citations of retracted papers, and can the two be compared? |
| 01-E | What does the method miss, and how much of the observed result depends on the sample? |
| 01-F | Can every finding be reproduced from a machine-readable manifest? |
| 01-G | GO, RESCOPE or STOP? |

## 2. Sources and verification hierarchy

1. **Retraction events.** Crossref Retraction Watch dataset, pinned to one
   GitLab commit of `gitlab.com/crossref/retraction-watch-data` with the git
   blob id and SHA-256 of `retraction_watch.csv`.
2. **Second retraction source.** Crossref REST API `/works/{doi}` for the
   original DOI (`updated-by`, `relation`) and for the notice DOI (`type`,
   `update-to`). Used to confirm or contradict the Retraction Watch record.
3. **Wikipedia.** MediaWiki Action API of `en.wikipedia.org` and
   `ar.wikipedia.org`: `list=exturlusage`, `list=search` (CirrusSearch
   `insource:`), `prop=revisions` (ids, timestamp, sha1, content of the main
   slot), `prop=langlinks`. A revision is identified by its `revid` and its
   `sha1`.
4. **Not sources of fact:** AI output (including the agent's own memory),
   search snippets, secondary web pages. They may suggest candidates or
   critique methods only.

Epistemic status of every manifest entry uses the contract vocabulary:
`verified_fact` (established from the cited primary source in this run),
`model_inference`, `uncertain`, `unavailable`, `conflicting`.

Rules carried from the data contracts:

- A retraction status is `verified_fact` only when the Retraction Watch record
  names the event type and the original DOI, and the notice DOI (when one is
  given) resolves in Crossref. If Crossref and Retraction Watch disagree on a
  stated field, that field is `conflicting`, with both values.
- No record found in the checked sources is recorded as
  `not_found_in_checked_sources`, status `uncertain`. It never means "not
  retracted".
- The original paper DOI and the retraction notice DOI are separate fields and
  are never substituted for each other. A record whose two DOIs are identical
  is reported, not corrected.

## 3. Wikipedia citation discovery method

For a DOI `d` and a wiki `w` (namespace 0, articles only):

1. **M1 — external links table:** `list=exturlusage`, `euquery=doi.org/<d>`,
   protocols `https` and `http`. Finds pages whose rendered output links to
   `doi.org/<d>` (as `{{cite journal |doi=}}` does).
2. **M2 — search index:** `list=search`, `srsearch=insource:"<d>"`.
3. **Confirmation (required):** for each page found by M1 or M2, fetch the
   latest revision (revid, timestamp, sha1, wikitext) and test whether the
   wikitext contains `d` (case-insensitive; also its URL-encoded form). Only a
   confirmed page is a citation observation. Unconfirmed hits are reported as
   method disagreements.

A citation observation is: wiki, title, page id, revid, revision timestamp,
revision sha1, retrieval time, method(s) that found it, and the reference
markup around the DOI (the enclosing `<ref>` or citation template, at most
one reference per observation, attributed under CC BY-SA 4.0).

## 4. Samples and bounds

- **P — purposive set (at most 12 DOIs).** High-profile retracted papers
  likely to be cited in Wikipedia, proposed by the agent from its own
  background knowledge (an AI-assisted prioritization, stated as such) and
  then checked against the sources. Its purpose is to find real positive
  cases. It is not representative and no rate is computed from it.
- **S — systematic random sample.** 200 records drawn without replacement,
  with Python `random.Random(20261026).sample`, from the Retraction Watch
  records of the pinned snapshot with `RetractionNature == "Retraction"` and
  a non-missing `OriginalPaperDOI`, after de-duplicating by lower-cased
  original DOI (first record in file order kept). Every sampled DOI is
  searched with M1 and M2 on both wikis. The estimated quantity is the share
  of such DOIs with at least one confirmed citation in the latest revision
  of an article on that wiki, as found by M1 ∪ M2, on the retrieval date.
  A 95% Clopper–Pearson interval is reported for that quantity only; it
  describes this population and method, not Wikipedia as a whole.
- **Cross-language follow-up.** For each confirmed English article in P or
  S, its Arabic interlanguage link (if any) is fetched and its latest
  revision is checked for the same DOI; and the reverse for each confirmed
  Arabic article.
- **Timeline probe (at most 2 cases).** For one confirmed case per wiki where
  feasible, bisect the article's revision history to find the first revision
  containing the DOI, and check whether a retraction marker appears near the
  citation in the latest revision. Assumes the DOI, once added, stays; any
  violation found while bisecting is reported.
- **Request bounds.** Descriptive User-Agent with a project URL; at most one
  request per second per host; `maxlag=5`; honor `Retry-After` on 429 and
  503; at most 6 attempts per request with exponential backoff, 30 s timeout.
  A request that still fails is recorded as `unavailable`, never as "no
  citation".

## 5. Positive and negative controls

- **Positive case:** a DOI with a `verified_fact` retraction (§2) and a
  confirmed citation observation (§3) in a pinned revision.
- **NC-1, event-type discrimination:** a Retraction Watch record whose type
  is Correction or Expression of concern, which a correct system must not
  report as a retraction. Preferably on a DOI that is also cited in
  Wikipedia.
- **NC-2, extraction negative:** a specific pinned revision verified not to
  contain a target DOI (for example the revision just before the citation was
  added, or a language-linked article). Tests that extraction does not
  report a citation that is not there. It says nothing about other
  revisions.
- **NC-3, absence semantics:** a DOI with no record in the checked sources,
  recorded as `not_found_in_checked_sources` / `uncertain`. It demonstrates
  the representation; it does not show that the paper was never retracted.
- **Unresolved cases** (conflicting sources, unconfirmed hits, failed
  requests) are listed separately and are not counted as positives or
  negatives.

## 6. English and Arabic feasibility criteria

- **Arabic feasible for detection:** at least one confirmed Arabic citation
  of a Retraction Watch retracted DOI (from P, S or cross-language
  follow-up).
- **Arabic feasible for comparison:** at least one paper for which the
  English and Arabic articles linked by interlanguage links can both be
  inspected at pinned revisions and their citation of the DOI compared.
- Arabic-specific problems (template and parameter names, digits, direction,
  encoding) are recorded as observed, not assumed.
- Linked articles are not assumed to share citations.

## 7. Decision criteria (fixed in advance)

- **GO:** 01-A to 01-F pass; at least one verified positive case on English
  Wikipedia; Arabic feasible for detection and for comparison; no data-terms
  blocker.
- **RESCOPE:** the core English chain is verified, but Arabic is not feasible
  for detection or comparison within these bounds, or data terms restrict the
  planned use, or a method limitation forces a narrower claim than the Master
  Plan research question. The recommendation then states the narrower scope.
- **STOP:** no verified positive chain on English Wikipedia within these
  bounds, or retraction data cannot be accessed or used.

The recommendation is advisory; scope decisions belong to the owner.

## 8. Reproducibility

- Scripts in `scripts/` use the Python standard library only (no new
  dependency). The run writes raw API responses to an ignored cache outside
  the repository and commits only derived, minimal records.
- The Retraction Watch CSV is not committed. Its source commit, blob id and
  SHA-256 are recorded so the exact file can be re-downloaded and checked.
- Wikipedia text is not committed in bulk: only revision identifiers, sha1
  and the single reference markup of each observation.
- `scripts/verify_manifest.py` re-fetches every pinned revision and Crossref
  record named in `EVIDENCE_MANIFEST.json` and reports any mismatch.

## 9. AI use

The agent executing Stage 01 is an AI coding agent. It may prioritize
candidates, suggest hypotheses, look for missing evidence and critique the
method. It is never the source of a retraction fact or of a citation
observation. A same-model adversarial review is labelled as such and is not
an independent review.
