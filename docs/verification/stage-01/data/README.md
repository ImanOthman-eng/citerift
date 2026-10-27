# Stage 01 data files

Derived, minimal records produced by `../scripts/stage01_probe.py` on
2026-10-26. Raw API responses were cached outside the repository and are not
committed. Every file was re-derived from that cache with the committed
scripts by `../scripts/reproduce.sh`, which lists the exact commands in order
(except `run-logs/`).

| File | Content |
|---|---|
| `rw_profile.json` | Data-quality profile of the pinned Retraction Watch snapshot (counts only). |
| `sample_S.json` | The systematic sample S: 200 Retraction Watch records (seed 20261026), selected fields. |
| `purposive_dois.json` | The purposive set P: 10 DOIs chosen by the agent (AI-assisted prioritization, PROTOCOL.md §4). |
| `purposive_lookup.json` | Retraction Watch records and Crossref REST metadata for the 10 DOIs of P, for the NEJM retraction notice `10.1056/NEJMc2021225`, and for every notice DOI. |
| `purposive_discovery.json` | M1 (exturlusage) and M2 (insource search) discovery with confirmation, P, en + ar. |
| `sample_S_discovery.json` | M2 discovery with confirmation, S, en + ar. |
| `verify_result.json` | Live re-verification of every pinned revision and notice in `../EVIDENCE_MANIFEST.json`. |
| `followups/crosswiki_*.json` | Interlanguage-link follow-up of every citing article, P and S (`_S_`), both directions. |
| `followups/timeline_*.json` | First citing and first marked revision of the MMR vaccine articles (bisection). |
| `followups/nc2_absence_check_*.json`, `en_mmr_retraction_text_check.json` | Plain substring counts in pinned revisions (NC-02; retraction wording, report §7.4). |
| `followups/nc3_lookup.json` | Retraction Watch and Crossref lookup of the NC-03 paper (Watson & Crick 1953). |
| `followups/prior_art_*.json`, `ar_*.json` | Read-only Action API responses: RetractionBot accounts and edits, English retraction categories, Arabic retraction templates and their use. |
| `run-logs/sample_S_discovery_first_run_log.json` | Request log (statuses, attempts) of the first, network-bound sample run; the only file here not produced by `reproduce.sh`. |
| `rate-limit/` | The 40-request Wikimedia rate-limit measurement (log and the exact script, stored as text). |

## Sources and attribution

- **Retraction Watch data**, via Crossref: `gitlab.com/crossref/retraction-watch-data`,
  commit `a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` (data generated
  2026-10-23), file `retraction_watch.csv`, git blob
  `2a466638299c351ae50ae8e5736c410b96b99045`, SHA-256
  `2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`.
  Crossref states that its metadata is free to reuse without a license and
  asks that published uses of the Retraction Watch metadata cite the source
  (https://www.crossref.org/blog/retraction-watch-retractions-now-in-the-crossref-api/,
  read 2026-10-26). The CSV itself is not committed; only selected fields of
  the inspected records.
- **Crossref REST API** (`api.crossref.org/works/{doi}`): metadata, free to
  reuse.
- **Wikipedia** (English and Arabic): each `reference_markup` value is a
  single reference copied from the named article revision (see its
  `revision_url`) and is available under CC BY-SA 4.0 (older text also
  GFDL); authors are listed in that article's history. No article text
  beyond one reference per observation is committed.
