# External Sources and Attribution Policy

Applies to every stage. A stage that adds a source or a dependency records it
here and in DECISIONS.md before using it.

## Data sources in use

| Source | Use | Terms status |
|---|---|---|
| Crossref Retraction Watch data, pinned commit `a987928a`, `retraction_watch.csv` (68,076,023 bytes, SHA-256 `2f116e9f…0a655`) | Retraction records (Stage 02) | Checked 2026-10-27: Crossref states it made the database publicly available and that REST API metadata may be used for any purpose; neither Crossref nor the data repository names a dataset licence (a third-party page calls it CC0; not relied on). Crossref asks for a citation. The full CSV and bulk extracts are not committed or redistributed; `tests/stage02/fixtures/rw_real_subset.csv` keeps selected fields of 69 records, with the attribution recorded in `tests/stage02/fixtures/real_cases.json` |
| Crossref REST API `/works/{doi}` | Bounded corroboration of 29 works (Stage 02), pinned as a replay bundle in `docs/verification/stage-02/evidence/crossref/` | REST API metadata reusable for any purpose (Crossref); GET only, 1 request per second, concurrency 1 |

## Planned data sources (not yet used)

| Source | Use | Terms status |
|---|---|---|
| Wikimedia APIs (Action API, REST API, dumps) | Articles, revisions, references (Stage 03) | Wikipedia text is CC BY-SA 4.0 (and GFDL for older text); API use must follow the Wikimedia User-Agent policy and rate limits |
| Wikidata | Cross-language article links (Stage 07, if used) | CC0 |
| PubMed / NCBI E-utilities | PMID resolution (Stage 03 or later, if used; Stage 02 did not use it) | NCBI usage policy; API key optional |

## Rules

1. **Provenance on every fact.** Each retrieved fact carries a `source_ref`
   with source id, locator, retrieval time and, where available, dataset version
   or revision id (see docs/data-contracts.md).
2. **Attribution for quoted text.** Citation context quoted from Wikipedia is
   attributed to the article, language edition and revision, with a link. Bulk
   Wikipedia text is not committed to this repository.
3. **No data committed before terms are checked.** Raw downloads go to ignored
   paths (`data/raw/`, `data/cache/`) and are reproducible from documented
   commands.
4. **Respect service limits.** Descriptive User-Agent with a contact, honor
   `Retry-After`, back off on HTTP 429, cache responses.
5. **No automatic Wikipedia edits.** CITERIFT reads Wikipedia; it never edits it.
6. **Third-party code.** Before reusing code from another project: check its
   license for compatibility, keep its notices, and record it in DECISIONS.md.
   Libraries are used as dependencies through `pyproject.toml`, not copied.
7. **AI tools.** The use of AI coding assistants and AI models is disclosed in
   the final report and Devpost submission (Stage 09). Model licenses are
   checked before a model is downloaded (Stage 06).
8. **Synthetic versus real.** Synthetic fixtures are labeled and never presented
   as findings.

## Current dependencies (Stage 00; Stage 02 added none)

Runtime: `jsonschema` (MIT) and its dependencies `attrs` (MIT),
`jsonschema-specifications` (MIT), `referencing` (MIT), `rpds-py` (MIT).
Development only: `pytest` (MIT), `ruff` (MIT), `mypy` (MIT), `pip-audit`
(Apache-2.0). Exact versions are pinned in `uv.lock`.
