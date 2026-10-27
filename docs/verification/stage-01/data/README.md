# Stage 01 data files

Derived, minimal records produced by `../scripts/stage01_probe.py` on
2026-10-26, corrected and extended on 2026-10-27 (FEASIBILITY_REPORT.md §15).
Raw API responses were cached outside the repository and are not committed.
Every file was re-derived from that cache with the committed scripts by
`../scripts/reproduce.sh`, which lists the exact commands in order (except
the inputs `purposive_dois.json` and `rate-limit/`, `run-logs/`,
`clean_reproduction.json`, and the two prior-art profiles; how each of those
was produced is stated below). What reproduces without the cache:
FEASIBILITY_REPORT.md §9.1.

| File | Content |
|---|---|
| `rw_profile.json` | Data-quality profile of the pinned Retraction Watch snapshot (counts only). |
| `sample_S.json` | The sample S: 200 Retraction Watch records drawn at random without replacement (seed 20261026), selected fields. |
| `purposive_dois.json` | The purposive set P: 10 DOIs chosen by the agent (AI-assisted prioritization, PROTOCOL.md §4). |
| `purposive_lookup.json` | Retraction Watch records and Crossref REST metadata for the 10 DOIs of P, for the NEJM retraction notice `10.1056/NEJMc2021225`, and for every notice DOI. |
| `purposive_discovery.json` | M1 (exturlusage) and M2 (insource search) discovery with confirmation, P, en + ar. |
| `sample_S_discovery.json` | M2 discovery with confirmation, S, en + ar. 7 Arabic searches are from 2026-10-27 (see `run-logs/`). |
| `verify_result.json` | Live re-verification of every pinned revision and notice in `../EVIDENCE_MANIFEST.json`. |
| `clean_reproduction.json` | Comparison of a clean-cache rerun of POS-02 and NC-03 with the committed data (`../scripts/clean_reproduction.sh`, `compare_clean.py`). |
| `followups/crosswiki_*.json` | Interlanguage-link follow-up of every citing article, P and S (`_S_`), both directions. |
| `followups/timeline_*.json` | First citing and first marked revision of the MMR vaccine articles (bisection). |
| `followups/nc2_absence_check_*.json`, `en_mmr_retraction_text_check.json` | Plain substring counts in pinned revisions (NC-02; retraction wording, report §7.4). |
| `followups/nc3_lookup.json` | Retraction Watch and Crossref lookup of the NC-03 paper (Watson & Crick 1953). |
| `followups/render_check_*.json` | Rendered (parser HTML) check of the citing reference in four pinned revisions: warning text, links to missing pages, a 300-character excerpt. |
| `followups/prior_art_retractionbot_*.json`, `prior_art_en_categories.json`, `ar_*.json` | Read-only Action API responses: RetractionBot accounts and edits, English retraction categories, Arabic retraction templates and their use. |
| `followups/prior_art_shi_median_sources.json`, `prior_art_retraction_tracker_profile.json` | Short quotations and derived counts from public pages read on 2026-10-27 (Crossref, arXiv, CSCW program; Retraction Tracker about page and data file); the pages are not committed. Produced by one-off commands in the executor's session (not committed); summarized in CREATIVE_FEASIBILITY.md §1. |
| `run-logs/sample_S_discovery_first_run_log.json` | Request log (statuses, attempts) of the first, network-bound sample run. |
| `run-logs/sample_S_search_errors_first_run.json` | The 7 Arabic search responses of the first run that were HTTP 200 with `cirrussearch-too-busy-error` (unavailable, first recorded as "0 hits"). |
| `run-logs/sample_S_search_retry_2026-10-27.json` | The answers to those 7 searches, sent again once on 2026-10-27, with their attempts. Both search logs were extracted from the session's response cache by one-off commands (not committed). |
| `run-logs/census_render_first_run_failure.json` | The one rendered check of the first census render run (2026-10-27) that got no HTTP answer after the client's retries; it was re-sent once and answered (`census/ar_render.json` holds that answer). |
| `run-logs/stage01_tests_pinned_85da719.json` | The sha256 of each Stage 01 test file under `tests/stage01/` at revision 85da719, with its result, so the gate record pins the tests. |
| `rate-limit/` | The 40-request Wikimedia rate-limit measurement (log and the exact script, stored as text). |
| `census/ar_scan.json` | Every Arabic Wikipedia page whose external links (dump of 2026-10-01) point to the DOI or PMID of a Retraction Watch record, original paper or notice; page ids, titles and matched identifiers only (FEASIBILITY_REPORT.md §16). |
| `census/ar_confirm.json` | Live check (2026-10-27) of the current revision of each Arabic article in `ar_scan.json`: cited by identifier or not, marked by a {{Retracted}}-family template or not. No article text. |
| `census/ar_render.json` | Rendered (parser HTML) check of every Arabic article–paper pair whose record is a Retraction or an Expression of concern: warning text, link to a missing template, or no warning text; a 300-character excerpt per reference. |
| `census/en_ar_langmap.json`, `ar_en_langmap.json` | Interlanguage links from the 2026-10-01 langlinks dumps for the citing articles, and the linked articles' page ids in the other wiki's page dump. |
| `census/crosswiki_en_to_ar.json`, `crosswiki_ar_to_en.json` | For every article citing a retracted paper (Retraction records) with a linked article in the other language: whether the linked article cites the same paper now (by any of its RW identifiers), each side's marking, and, for papers not carried, the linked article's first revision and the source article at that time. |
| `census/dump_vs_api_crosscheck.json` | The dump scan compared with the live M1/M2 results for the 10 purposive papers in both languages. |
| `census/census_summary.json` | All counts quoted in FEASIBILITY_REPORT.md §16, computed by `stage01_census.py summarize`. The full English dump scan is not committed (its summary is). |

## Sources and attribution

- **Retraction Watch data**, via Crossref: `gitlab.com/crossref/retraction-watch-data`,
  commit `a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` (data generated
  2026-10-23), file `retraction_watch.csv`, git blob
  `2a466638299c351ae50ae8e5736c410b96b99045`, SHA-256
  `2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`.
  Crossref states that its metadata is free to reuse without a license and
  asks that published uses of the Retraction Watch metadata cite the source
  (https://www.crossref.org/blog/retraction-watch-retractions-now-in-the-crossref-api/,
  read 2026-10-26). Access, reuse and redistribution are kept apart
  (FEASIBILITY_REPORT.md §4.4): the CSV was downloaded and pinned, selected
  fields of the inspected records are reused here with this citation, and the
  full CSV is not committed or redistributed.
- **Crossref REST API** (`api.crossref.org/works/{doi}`): metadata, free to
  reuse.
- **Wikipedia** (English and Arabic): each `reference_markup` value is a
  single reference copied from the named article revision (see its
  `revision_url`) and is available under CC BY-SA 4.0 (older text also
  GFDL); authors are listed in that article's history. The `text_excerpt`
  and `context` values in `followups/render_check_*.json` are short excerpts
  of the rendered reference of the named revision, under the same terms. No
  article text beyond one reference per observation is committed.
- **Wikimedia dumps** of 2026-10-01 (`arwiki` and `enwiki` externallinks, page and
  langlinks tables), from https://dumps.wikimedia.org/, each checked against
  the sha1 published in the run's `dumpstatus.json`. Only page ids, titles,
  revision ids and matched identifiers derived from them are committed; the
  dumps are not.
- **Requests** were sent with the User-Agent
  `CITERIFT-Stage01-feasibility/0.1 (https://github.com/ImanOthman-eng/citerift; read-only research; contact via GitHub issues)`,
  following the Wikimedia Foundation User-Agent Policy (FEASIBILITY_REPORT.md §15.3).
