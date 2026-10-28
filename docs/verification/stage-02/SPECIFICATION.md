# Stage 02 Specification: Retraction Data Engine

Project owner: EVE TELOS. Stage authorized by the owner's Stage 02 Master
Execution Directive (message `cmsg_018VCB51nDHP6HXmLU4ea5yPWSJKXxdz5fLqXyjZEAfWDJ`,
recorded in the registry at commit `1d2c0ba`). This file was frozen before
production code was written (commit of this file, see EXECUTION_LEDGER.md).
Later changes are listed in §16 with their reason; none lowers a criterion.

Labels: **[V]** verified by the executor against a primary source or the
pinned bytes on 2026-10-27; **[D]** design decision of this stage; **[I]**
inference.

## 1. Purpose and boundary

The Retraction Data Engine (RDE) turns one pinned Retraction Watch (RW)
snapshot into an offline, indexed, provenance-preserving event ledger, and
answers identifier lookups with role-aware event evidence and a conservative
projection into the v1 contract vocabulary.

In scope: snapshot receipt and verification; lossless row accounting;
quarantine; DOI/PMID normalization; events, notices and source assertions;
temporal evidence; SQLite index; lookup, event, export, verify, diff and
tension operations; bounded, replayable Crossref corroboration; the Evidence
Ambiguity Investigator boundary, baseline and experiment protocol;
Stage-02-owned schemas and semantic validation.

Out of scope (not built here): Wikipedia extraction and citation context
(Stages 03, 05), an HTTP service, cross-wiki analytics, frontend, the
runtime Investigation MAESTRO / Workflow Controller (Stages 04, 07), vector
stores, queues, any edit of Wikipedia. Application code never imports
`citerift.governance`.

Scientific invariants (from the directive; each has tests, §14):

1. A citation of a retracted paper does not prove its citing claim false (no
   claim-truth field exists).
2. No record found is `uncertain / not_found_in_checked_sources`, never "not
   retracted".
3. A notice DOI is not the DOI of the affected original; roles are stored and
   queried separately.
4. Events over time are not contradictions; only incompatible assertions about
   the same proposition are conflicts.
5. A second distribution channel of the same origin is not corroboration.
6. An exact identifier match is a source-record match, not proof of truth.
7. Model output never writes facts, statuses or dates.
8. Observed evidence, derived conclusions, model suggestions and unknowns are
   distinct objects.

## 2. Ownership

Stage-owned paths (registry `owned_paths`): `src/citerift/retraction`,
`schemas/retraction`, `tests/stage02`, `simulations/stage02`. Verification
directory: `docs/verification/stage-02` (real-data scripts live in its
`scripts/`). Narrow shared changes: registry and PROJECT_STATUS.md through
`citerift-gov`; DECISIONS.md (D-021 to D-024), RISKS.md (R-022 onward),
CHANGELOG.md, `.gitignore` (`data/index/`, `data/runs/`), `pyproject.toml`
(console script `citerift-rde`), `docs/architecture.md`,
`docs/data-contracts.md`, `docs/sources-and-attribution.md`. No Stage 00 or
Stage 01 owned or evidence path changes. No new runtime dependency is planned
(standard library `csv`, `hashlib`, `sqlite3`, `urllib`, plus the existing
`jsonschema`).

## 3. Pinned source

| Field | Value |
|---|---|
| Repository | `https://gitlab.com/crossref/retraction-watch-data` |
| Commit | `a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` |
| Path | `retraction_watch.csv` |
| Bytes | 68,076,023 [V] |
| SHA-256 | `2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655` [V] |
| Git blob | `2a466638299c351ae50ae8e5736c410b96b99045` [V] (equals the tree listing) |
| Logical data rows | 73,356 [V] |
| Acquisition | `https://gitlab.com/crossref/retraction-watch-data/-/raw/a987928.../retraction_watch.csv`, HTTP 200, 2026-10-27T20:20:13Z [V] |

The receipt is committed as `src/citerift/retraction/receipts/rw-a987928.json`
(source facts only, no data). Raw bytes stay in ignored `data/raw/`. The
build refuses bytes whose size or SHA-256 differ from the receipt. The full
CSV, the database and caches are never committed; tests use small attributed
fixtures (§14).

Format facts [V]: UTF-8 with BOM; LF line ends; 20 columns; 40,775 records
contain embedded newlines; no duplicate `Record ID`; README: DOI missing is
blank, `unavailable` or `Unavailable`; PMID missing is blank or 0; list
fields are `;`-separated (authors, reasons, subjects). DOI fields are
single-valued (README); the engine never splits them.

Licensing [V]: Crossref states that it made the RW database publicly
available and that REST API metadata is reusable for any purpose; no
dataset licence name is stated by Crossref or the repository (a third party
calls it CC0; not relied on). Crossref asks for a citation of the source.
Distribution boundary [D]: the engine and repository never redistribute the
full CSV or a bulk extract; committed fixtures contain at most 120 records'
selected fields with attribution (docs/sources-and-attribution.md).

## 4. Versions

| Constant | Value |
|---|---|
| `POLICY_VERSION` | `citerift-rde-policy/1.0.0` |
| `PARSER_VERSION` | `citerift-rw-csv/1.0.0` |
| `SCHEMA_VERSION` (schemas/retraction/v1) | `1.0.0` |
| `INDEX_FORMAT` (SQLite `user_version`) | `2001` |
| `TENSION_VERSION` | `citerift-evidence-tension/0.1.0` |
| `BASELINE_VERSION` (ambiguity baseline) | `citerift-ambiguity-baseline/1.0.0` |

A change to any rule in §5 to §11 increments the matching version.

## 5. Import, accounting and quarantine

### 5.1 Fatal import failures (no artifact published)

| Code | Condition |
|---|---|
| `SOURCE_UNREADABLE` | file cannot be opened |
| `SOURCE_SIZE_MISMATCH` | byte count differs from the receipt (covers partial downloads) |
| `SOURCE_HASH_MISMATCH` | SHA-256 differs from the receipt |
| `RECEIPT_INVALID` | receipt fails its schema |
| `ENCODING_INVALID` | bytes are not strict UTF-8 |
| `NUL_BYTE` | a NUL byte occurs |
| `CR_UNSUPPORTED` | a CR byte occurs anywhere (parser 1.0.0 reads LF-terminated files only; the pinned source has none [V]) |
| `HEADER_MISSING` | no header record |
| `HEADER_DUPLICATE` | a column name repeats |
| `HEADER_CRITICAL_MISSING` | a critical column is absent: `Record ID`, `RetractionNature`, `RetractionDate`, `RetractionDOI`, `RetractionPubMedID`, `OriginalPaperDate`, `OriginalPaperDOI`, `OriginalPaperPubMedID` |
| `CSV_STRUCTURE_INVALID` | the strict CSV parser fails (unterminated quote, text after a closing quote, bare CR): logical record boundaries cannot be recovered |
| `FIELD_TOO_LARGE` | a field exceeds 1 MiB |
| `ROW_LIMIT_EXCEEDED` | more than 2,000,000 logical records |
| `ACCOUNTING_MISMATCH` | an internal check of §5.3 fails (defect guard) |

No row count is reported for a failed import; the failure report gives the
code, a byte or line position where known, and the receipt.

### 5.2 Records

The parser reads with `csv.reader(strict=True)` after strict UTF-8 decoding,
with a leading BOM removed (`utf-8-sig`). A *physical line* is a
`\n`-terminated byte line; a *logical record* is one CSV record (it may span
lines). Physical lines that contain nothing (zero bytes before `\n`) outside a
quoted field are *blank lines*: counted, never records. Each logical record
gets a 1-based ordinal (`row:N`), its first and last physical line, the raw
field list, and `row_sha256` = SHA-256 of the canonical JSON of the list of
raw field strings (§10.4).

### 5.3 Accounting equations

`N_records = N_accepted + N_quarantined`, and
`N_physical_lines = N_header_lines + Σ record line spans + N_blank_lines`.
Both are checked before publication (`ACCOUNTING_MISMATCH` otherwise) and by
`verify`. Duplicate grouping (§5.5) never changes these counts.

### 5.4 Dispositions

A record is **quarantined** (kept in full, with reasons) when:

| Reason | Condition |
|---|---|
| `FIELD_COUNT_MISMATCH` | field count differs from the header |
| `EVENT_TYPE_MISSING` | `RetractionNature` is empty |
| `EVENT_TYPE_UNKNOWN` | `RetractionNature` is not exactly one of the four known labels |

Every other record is **accepted** and yields exactly one event. Missing or
invalid identifiers, invalid dates and other field problems never quarantine:
they are row issues with null normalized values.

### 5.5 Duplicate groups (separate from accounting)

| Kind | Members |
|---|---|
| `identical_record` | records with equal `row_sha256` |
| `record_id_reused` | records with the same non-empty `Record ID` and different `row_sha256` |
| `same_event_signature` | accepted records with the same anchor, event type, notice key and reported event date, different `row_sha256` |

All members are kept as separate rows and events. A group never replaces or
removes a member.

## 6. Identifiers

`normalize_doi(raw)` and `normalize_pmid(raw)` return
`{raw, scheme, input_form, normalized | null, transformations[], issues[], valid}`.

### 6.1 DOI

1. Trim outer whitespace (Unicode `str.strip()`): `TRIM_OUTER_WHITESPACE`.
2. Empty → `DOI_EMPTY`. In source fields only, `unavailable` and
   `Unavailable` → `DOI_SENTINEL_UNAVAILABLE` (missing, not invalid).
3. Form detection (ASCII-case-insensitive scheme and prefix):
   - `doi:` followed directly by `10.` → strip once (`STRIP_DOI_PREFIX`).
     Anything else after `doi:` is `DOI_PREFIX_INVALID`.
   - `http://` or `https://` → URL form. Host must be exactly `doi.org` or
     `dx.doi.org` (ASCII case-insensitive); no userinfo, no port, no query,
     no fragment; path `/` + DOI. Otherwise `DOI_URL_HOST_INVALID` or
     `DOI_URL_SHAPE_INVALID`. The path is percent-decoded exactly once as
     strict UTF-8 (`PERCENT_DECODE_URL_PATH`); a `%` not followed by two hex
     digits, or bytes that are not UTF-8, is `DOI_PERCENT_ENCODING_INVALID`.
     `+` is kept (no `unquote_plus`).
   - otherwise bare. Percent signs in a bare DOI are literal
     (`DOI_LITERAL_PERCENT`, informational); bare DOIs are never decoded.
4. Validation of the resulting string: `10.` + ASCII digits `[0-9]{4,9}`
   + optional `.digits` groups + `/` + non-empty suffix
   (`DOI_SYNTAX_INVALID` otherwise); no character of Unicode category Cc, Cf,
   Cs, Zs, Zl or Zp anywhere (`DOI_CONTAINS_CONTROL`,
   `DOI_CONTAINS_FORMAT_CHARACTER` (bidi, zero-width, BOM),
   `DOI_CONTAINS_WHITESPACE`); at most 512 characters (`DOI_TOO_LONG`).
5. Key: ASCII `A`–`Z` → `a`–`z` only (`ASCII_CASE_FOLD`). No Unicode
   case folding, NFC/NFKC, mark stripping, or punctuation repair: final
   `.`, `)`, `;` and `+` are kept. Non-ASCII suffix characters are kept
   (`DOI_NON_ASCII_SUFFIX`, informational).

Idempotence: for every valid key `k`, `normalize_doi(k).normalized == k`.

### 6.2 PMID

Trim outer whitespace; then exactly ASCII `[0-9]+`. Empty →
`PMID_EMPTY`; all zeros → `PMID_ZERO_SENTINEL` (missing, per README); other
leading zero → `PMID_LEADING_ZERO` (invalid, not repaired); non-ASCII digits
→ `PMID_NON_ASCII_DIGIT`; sign, decimal point, exponent or other characters
→ `PMID_NOT_INTEGER`; more than 9 digits → `PMID_TOO_LONG` (the v1 `pmid`
pattern allows 9). URL forms (http or https, ASCII-case-insensitive host):
`pubmed.ncbi.nlm.nih.gov/<digits>` with optional trailing `/`, and
`www.ncbi.nlm.nih.gov/pubmed/<digits>`; anything else is
`PMID_URL_INVALID`. Invalid PMIDs keep the raw value and export no v1 `pmid`.

### 6.3 Roles and anchors

Each record has up to four identifier occurrences: original DOI, original
PMID, notice DOI, notice PMID, each with `role ∈ {original, notice}`.
Work anchor of an event: `doi:<key>` if the original DOI is valid, else
`pmid:<key>` if the original PMID is valid, else `rec:<ordinal>`
(source-record-local; never merged with anything). Notice key: `doi:<key>`
of a valid notice DOI, else `pmid:<key>` of a valid notice PMID, else none.
When the notice DOI key equals the original DOI key the record is flagged
`NOTICE_DOI_EQUALS_ORIGINAL` and has **no notice key** (it is not an
independent notice witness); likewise for PMIDs
(`NOTICE_PMID_EQUALS_ORIGINAL`). A notice key shared by several records is
`NOTICE_SHARED` (allowed). A notice DOI that is also an original DOI of
another record is `NOTICE_ALSO_ORIGINAL_ELSEWHERE`.

## 7. Events and temporal evidence

### 7.1 Event types

`Retraction` → `retracted`; `Expression of concern` →
`expression_of_concern`; `Correction` → `correction`; `Reinstatement` →
`reinstated`. Exact, case-sensitive labels. No default.

### 7.2 Temporal evidence

Each date field becomes
`{raw, kind, reported_calendar, stated_precision, effective_precision, earliest, latest, convention_flags[], issues[], provenance}`.

- Kinds: `notice_date` (`RetractionDate`, the date of the published notice),
  `original_publication_date` (`OriginalPaperDate`). Source update,
  acquisition and build times are separate metadata and are never mixed
  with these.
- Accepted shapes [V]: `M/D/YYYY H:MM` and `M/D/YYYY HH:MM:SS AM|PM`,
  1-2 digit month and day, 4-digit year. Any other shape →
  `DATE_UNPARSEABLE`; an impossible calendar date (for example 2/30) →
  `DATE_CALENDAR_INVALID`. Both keep the raw value with null bounds. No year
  cutoff: 1756 is valid.
- The time part is never an observed instant (`MIDNIGHT_NOT_INSTANT`
  convention flag when it is midnight); bounds are calendar days.
- RW user guide [V]: an unknown day is entered as 1; a month range uses its
  first month; seasons are entered as months 3, 6, 9, 12; volume numbers
  1–11 replace the month and larger volumes use 12. So a reported day of 1
  does not justify day, month or even season precision:
  `DAY_ONE_CONVENTION_POSSIBLE`, `effective_precision = unknown`,
  `earliest = latest = null`.
- Otherwise `stated_precision = effective_precision = day` and
  `earliest = latest = reported_calendar` (the source's own day).

### 7.3 Chronology

`definitely_before(A, B)` iff both bounds exist and `A.latest < B.earliest`.
Equal or overlapping intervals and missing bounds are `unresolved`. A stable
display order (reported value, then event id) is never presented as
chronology. Differences use `[C.earliest − E.latest, C.latest − E.earliest]`
(days), null when any bound is null.

## 8. Source assertions and lineage

Each fact is a source assertion with a proposition
`(subject, predicate, value)`, a v1 `source_ref` and, beside it, a `lineage`
object: `{origin, channel, method, payload_sha256, pointer, depends_on[]}`.

| Predicate | Subject | Value |
|---|---|---|
| `event_type` | event | v1 status value of §7.1 |
| `affects_original` | event | anchor key |
| `has_notice` | event | notice key |
| `notice_date` / `original_publication_date` | event | temporal evidence |
| `identifier_cooccurs` | record | `{doi, pmid}` of the original |
| `update_relation` (Crossref) | `(notice DOI, original DOI)` | Crossref `type` mapped by §9 |
| `notice_record_exists` (Crossref) | notice DOI | Crossref work type |

RW CSV assertions: origin `retraction-watch`, channel `rw-gitlab-csv`,
locator `<repository>/-/blob/<commit>/retraction_watch.csv#record=<N>`,
`source_version` = commit, `content_sha256` = `row_sha256`, `pointer` =
`/fields/<column>`. They are a deterministic function of the stored raw row
and are materialized on read and in exports. Crossref assertions are stored
(§9). Unknown origin or dependence stays `unknown`.

## 9. Bounded corroboration (explicit preparation step)

- Endpoint: `GET https://api.crossref.org/works/{doi}` only. The response must
  be HTTP 200 JSON with `status = ok`, `message-type = work` and
  `message.DOI` equal (ASCII case-insensitive) to the requested DOI; else the
  attempt fails with a typed reason.
- `updated-by` entries of an original [V] (`DOI`, `type`, `label`, `source`,
  `updated`, `record-id`) become `update_relation` assertions on
  `(entry.DOI, original)`. `source = retraction-watch` → origin
  `retraction-watch`, depends on the RW origin (redistributed channel);
  `source = publisher` → origin `publisher`, dependence on the RW notice
  `unknown`; other or missing → origin `unknown`.
- Type map: `retraction` → `retracted`; `correction`, `corrigendum`,
  `erratum` → `correction`; `expression_of_concern` →
  `expression_of_concern`; `reinstatement` → `reinstated`; every other
  Crossmark type (addendum, clarification, new_edition, new_version,
  partial_retraction, removal, withdrawal) → `untyped` (a relation without a
  comparable event type).
- A notice payload yields only `notice_record_exists`; a resolving notice is
  not typed corroboration.
- Limits (defaults, all enforced): 40 distinct works, 80 attempts including
  retries, concurrency 1, ≥1.0 s between request starts, 10 s request
  timeout, 30 s per work, 10 min per run, 4 MiB payload. `Retry-After` and
  `x-rate-limit-*`/`x-concurrency-limit` headers are honored; a wait longer
  than the remaining budget defers the work (`DEFERRED_BUDGET`). Transient
  errors (timeout, 429, 5xx, connection) retry at most twice with backoff
  2 s, 4 s. 403 stops the run (`ACCESS_DENIED`), never evaded.
- Failure reasons: `TIMEOUT`, `RATE_LIMITED`, `ACCESS_DENIED`,
  `SERVER_ERROR`, `HTTP_ERROR`, `CONNECTION_ERROR`, `PAYLOAD_TOO_LARGE`,
  `INVALID_JSON`, `SCHEMA_INVALID`, `DOI_MISMATCH`, `DEFERRED_BUDGET`. A
  failure is recorded as a failure and never as absence of a relation; failed
  payloads are not cached as results.
- Replay bundle: `manifest.json` (request URL, attempts, status, original
  `retrieved_at`, sha256, byte size, failure reason) plus payload files named
  by sha256. `build --corroboration <manifest>` verifies every hash and
  ingests successful payloads. A replay is not a new live verification; the
  original retrieval time is kept.
- Stage 01 pinned extracts (`docs/verification/stage-01/data/purposive_lookup.json`,
  hash-pinned in the Stage 01 verification) may be read as a second replay
  source, channel `stage01-extract`, without editing them.

## 10. Index, operations and interfaces

### 10.1 SQLite artifact

Tables: `meta`, `raw_record`, `event`, `ident`, `notice`, `event_notice`,
`quarantine`, `dup_group`, `cr_attempt`, `cr_assertion`, `title_token`,
`issue_index`. Primary keys are ordinals or engine ids, never `Record ID`.
Foreign keys enforced. `PRAGMA user_version = 2001`;
`application_id = 0x43525244` ("CRRD").

Build: write `<name>.tmp-<pid>-<nonce>` in the output directory, validate
(`integrity_check`, `foreign_key_check`, accounting, schema of the manifest,
semantic invariants, recomputed digests), `fsync`, then `os.replace` to
`rw-<sha256[:16]>.sqlite` and write the manifest the same way. Any failure
removes the temporary file and leaves every existing artifact unchanged.
Artifacts of other snapshots are never touched. Readers open
`file:<path>?mode=ro&immutable=1`, check `application_id`, `user_version`,
`meta.policy_version` and the stored digests, never migrate and
never enable extension loading. SQL is parameterized; inserts use batches of
5,000.

### 10.2 Operations (Python and CLI `citerift-rde`)

| Operation | CLI | Network | Behavior |
|---|---|---|---|
| build | `build --source CSV --receipt R --out-dir D [--corroboration M]` | none | §5, §10.1 |
| lookup | `lookup --index I (--doi X \| --pmid Y \| both) [--page-size N] [--cursor C]` | none | §10.3 |
| event | `event --index I EVENT_ID` | none | full event with raw row, assertions, issues |
| tension | `tension --index I (--doi \| --pmid) [--intervention K ...] [--origin O ...]` | none | §11 |
| verify | `verify --index I [--source CSV]` | none | integrity, schema, semantic, accounting and digest report |
| export | `export --index I --out FILE` | none | §10.4 |
| diff | `diff --old I1 --new I2` | none | §10.5 |
| enrich | `enrich --index I --dois-file F --out-dir D` | Crossref, bounded | §9 |
| ambiguity | `ambiguity --index I --event EVENT_ID` | none (baseline) | §12 |

JSON goes to stdout, diagnostics to stderr. Exit codes: 0 result produced
(including `no_record`); 2 usage; 3 `invalid_query`; 4 `unavailable`
(index missing, corrupt or wrong format); 5 verification failed; 6 import
failed; 7 enrichment stopped by a failure that is not per-work; 1 internal
error. Query, event, tension, verify, export and diff open no socket; a test
replaces `socket.socket` with a refusing stub and runs each.

### 10.3 Lookup contract

Output: `schema_version`, `policy_version`, `snapshot_id`, `query`
(raw values, normalization records), `lookup_state`, `identifier_role`,
`identity`, `total_event_count`, `events` (page), `page`
(`size`, `cursor`, `next_cursor`), `notice_hits`, `checked_sources`,
`issues`, `projection` (`retraction_status`, `retraction_date` as v1
assertions plus `basis`), `evidence_digest`.

Lookup states: `matched`, `notice_only`, `ambiguous_identity`, `no_record`,
`unavailable`, `invalid_query`. They are not epistemic statuses.

Algorithm (DOI `d`, PMID `p`, either or both):

1. Invalid identifier → `invalid_query`. Index cannot be opened or fails its
   format check → `unavailable`.
2. `O_d` = events whose original DOI key is `d`; `O_p` likewise for PMID.
   `N_d`, `N_p` = events with a notice-role occurrence of the query key
   (notice DOI key `d`, or notice PMID key `p`), excluding occurrences equal
   to the same record's original key of that scheme (those records are in
   `O`, not `N`). The notice key of §6.3 is used for grouping, not here.
3. Single DOI: if `O_d` ≠ ∅ → `matched`. Secondary PMIDs of `O_d`: if more
   than one distinct valid PMID → issue `IDENTITY_SECONDARY_DIVERGENT`, no
   bridging. If exactly one PMID `q`, events with original PMID `q` and no
   valid original DOI are **bridged** (`linked_via = pmid_cooccurrence`,
   one hop only).
4. Single PMID: if the valid original DOIs of `O_p` are more than one →
   `ambiguous_identity` with candidate groups by DOI (no union). If exactly
   one DOI `e`, events with DOI `e` and no valid PMID are bridged
   (`linked_via = doi_cooccurrence`). Otherwise `matched`.
5. Both: compatible iff every event of `O_d` has PMID ∈ {p, null} and every
   event of `O_p` has DOI ∈ {d, null}. Compatible with `O_d ∪ O_p` ≠ ∅ →
   `matched` (events matched only by `p` are marked `matched_by = pmid`).
   Incompatible → `ambiguous_identity` with both groups, never a union.
6. `O` = ∅ and `N` ≠ ∅ → `notice_only`: the events for which the query is the
   notice are listed with their originals; no projection value.
7. Nothing → `no_record`. Relevance check: quarantined records whose raw
   identifier fields contain the key (ASCII case-insensitive substring), and
   invalid identifier occurrences that contain it, are listed under
   `issues` as `RELEVANT_QUARANTINE` / `RELEVANT_INVALID_IDENTIFIER`.
8. `total_event_count` counts all matched and bridged events; pages hold at
   most 100 (default 20) in event-id order; the cursor is opaque and bound
   to the snapshot and query. Page size never changes counts, projection or
   `evidence_digest` (SHA-256 of the canonical JSON of query keys, state,
   sorted event ids with row hashes, identity and projection).

### 10.4 Canonical export and digests

Canonical JSON: UTF-8, sorted keys, separators `,` `:`, no NaN, integers
only. `export` streams JSONL: one `snapshot` record, then `record`,
`event`, `quarantine`, `dup_group`, `cr_assertion` records ordered by kind
then id, then a `digest` record. Two digests:

- `artifact_digest`: SHA-256 over every exported line (ids included).
- `semantic_digest`: SHA-256 over the sorted multiset of per-event semantic
  lines that exclude ordinals, line numbers, event ids and snapshot ids
  (raw fields, normalized identifiers, event type, temporal evidence, issue
  codes). Permuting records changes the snapshot and ids but not this digest.

Build duration, build time and host are in `meta` under `run_*` keys and in
no digest.

### 10.5 Diff

`diff` compares two indexes by `row_sha256` multisets and by semantic event
lines: `added`, `absent_in_new`, `unchanged`, and `changed` (same
`Record ID`, different content). Absence from a newer snapshot is reported as
`absent_in_new` with reason `SOURCE_VERSION_DIFFERENCE`; it never becomes a
reinstatement, a retraction removal or any assertion about a paper.

## 11. Projection policy and Evidence Tension

### 11.1 Conservative v1 projection (reducer)

Input: the events of the lookup (exact and bridged), the identity status,
Crossref assertions of the index for those originals, relevant
quarantine/invalid hits, and index health. Output: v1 `retraction_status`
and `retraction_date` assertions, a `basis` with reason codes and
supporting assertion ids. Rules in order:

1. Index unavailable → `unavailable`, value null.
2. `invalid_query` → no projection object.
3. `ambiguous_identity` → `uncertain`, null (`IDENTITY_AMBIGUOUS`).
4. `notice_only` → `uncertain`, null (`NOTICE_ONLY`).
5. `no_record` with relevant quarantine or invalid identifiers →
   `uncertain`, null (`COVERAGE_GAP_RELEVANT_ROWS`).
6. `no_record` otherwise → `uncertain`, `not_found_in_checked_sources`, with
   the checked sources as provenance (`NOT_FOUND_IN_CHECKED_SOURCES`).
7. `matched`: typed assertions are the RW events and the typed Crossref
   relations about the matched anchor. Group them by proposition
   *(notice key, original anchor)*; assertions without a notice key are
   their own propositions. A proposition with two or more different types is
   a **conflict group**. Clear assertions are those outside conflict groups;
   rules a to e use them (a clear retraction from any origin counts, and its
   origin is in `basis`). If an intervention view leaves no checked source,
   the result is `unavailable`, null (`NO_SOURCE_IN_VIEW`).
   a. Any reinstatement together with any other type: if every reinstatement
      carries a `supersedes` assertion naming an event of the set, and
      `definitely_before(target, reinstatement)`, and no other retraction
      remains unsuperseded → `reinstated`; else `uncertain`, null
      (`REINSTATEMENT_UNLINKED`).
   b. Else if a clear retraction exists → `verified_fact`, `retracted`
      (`SOURCE_RECORDED_RETRACTION`); conflicts elsewhere add
      `CONFLICT_NOT_MATERIAL`.
   c. Else if a conflict group exists → `conflicting`, null, with one
      alternative per distinct type and its provenance
      (`SOURCE_TYPE_CONFLICT`).
   d. Else only reinstatements → `verified_fact`, `reinstated`; only
      expressions of concern → `expression_of_concern`; only corrections →
      `correction`.
   e. Else (expression of concern and correction, no retraction) →
      `uncertain`, null (`MIXED_CURRENT_EFFECT`).
   Relevant quarantine with a matched state downgrades a b/d result to
   `uncertain`, null (`COVERAGE_GAP_RELEVANT_ROWS`).
8. `retraction_date` only when the value is `retracted`, from the RW notice
   dates of the clear retraction events: if they all report the same
   calendar value, that value with `verified_fact` when its bounds are
   justified, or `uncertain` with the reported value and
   `DATE_PRECISION_UNJUSTIFIED` when they are not; an unparseable or invalid
   date gives `uncertain`, null (`DATE_UNKNOWN`); different reported values
   give `uncertain`, null (`MULTIPLE_RETRACTION_DATES`). Crossref dates are
   not used. Otherwise absent; for `not_found_in_checked_sources` it is null
   with no alternatives (v1 rule).
9. `verified_fact` here means "established from the cited source record"
   (`basis.scope = checked_sources`), not independent truth.

Never: latest-row-wins, greatest-date-wins, notice retraction applied to the
original, unknown label defaulting to retraction, `not_retracted`.

### 11.2 Evidence Tension v0

`R(q, E)` is the fixed-policy result with these comparison fields:
`lookup_state`, `retraction_status.status`, `retraction_status.value`,
`retraction_date.status`, `retraction_date.value`,
`support.observations` (count of assertions supporting the projected value),
`support.origins` (sorted origin families), `identity.status`,
`notice_links` (sorted notice keys used), `definite_orderings` (sorted pairs).

Interventions operate on a copy of `E` (no mutation, no database write):

| Intervention | View |
|---|---|
| `collapse_shared_origin` | supporting observations of one origin count once (channels kept for display) |
| `exclude_origin(o)` | assertions with origin `o` and assertions that depend on `o` are removed; at most two origins per call |
| `exclude_ambiguous_links` | bridged events, notice links flagged `NOTICE_ALSO_ORIGINAL_ELSEWHERE`, and Crossref relations whose subject does not resolve to the query anchor are withheld; exact original-role events stay |
| `require_temporal_bounds` | every date value and ordering without justified bounds is withheld; events stay |

Output per intervention: `applicable` (false with a reason when the view
equals `E`), `result`, `changed_fields` (paths whose values differ),
`affected_assertions` (removed or collapsed ids), `reason_codes`, plus
`policy_version`, `tension_version`, `snapshot_id`, `evidence_digest` of the
base and of each view, and source pointers. No score, no probability, no
all-subsets search; cost is O(|E|) per intervention.

Baseline for comparison (`event_log_baseline`): the conventional design that
lists every row for the original DOI, answers "retracted" if any row is a
retraction, takes that row's date, and counts each source row or relation as
one confirming source. Diagnostic classes: `redistributed_support`,
`uncertain_identity_or_notice`, `unsupported_temporal_precision`,
`origin_dependence`, and `control` (no change expected).

## 12. Evidence Ambiguity Investigator

### 12.1 Boundary

Advisory only. Input: a bounded bundle (one unresolved event's fields with
JSON pointers, at most 5 deterministic candidates with their fields). The
model may return only `{"decision": "select" | "abstain", "candidate_id",
"cited_pointers": [...], "rationale"}` (schema
`urn:citerift:schema:retraction:v1:advisory-response`,
`additionalProperties: false`, ≤ 2,000 characters of rationale). Any
schema-invalid output, unknown candidate, citation of an unsupplied pointer,
timeout, transport failure, budget exhaustion or output containing a
forbidden key (`verified_fact`, `retraction_status`, `status`, `value`,
`provenance`) becomes `abstain` with a reason code. The result type
`AdvisorySuggestion` has no path into the store: the advisory module does
not import the build or write modules, the index is opened read-only, and a
test checks the index bytes are unchanged after a run.

### 12.2 Deterministic baseline (`BASELINE_VERSION`)

1. Exact compatible original DOI or PMID present → that anchor (decision
   `exact`).
2. Otherwise candidates from an inverted index of title tokens (title-search
   normalization: NFKC, `casefold`, Unicode letters and digits, tokens of
   length ≥ 3, Arabic marks U+064B–U+065F and tatweel removed; separate from
   identifier normalization). Tokens with document frequency > 2,000 are
   skipped. Candidate anchors: DOI anchors only, at most 200 per query by
   summed IDF, then ranked by
   `score = 0.6·cos_title + 0.2·year + 0.2·author`, where `cos_title` is
   IDF-weighted cosine of token sets; `year` is 1 for equal reported
   original-publication year, 0.5 for ±1 or missing, 0 otherwise; `author`
   is the Jaccard index of author surname tokens (last token of each
   `;`-separated name, title-search normalized), 0.5 when either side is
   missing. Ties: higher score, then smaller anchor key. Top 5 kept.
3. Select the top candidate iff `score ≥ τ_s` and
   `score − second ≥ τ_m`; else abstain. `τ_s`, `τ_m` are chosen once on the
   tuning split from the grid `τ_s ∈ {0.70, 0.75, …, 0.95}`,
   `τ_m ∈ {0.00, 0.05, 0.10}` by the primary metric (ties: larger `τ_s`,
   then larger `τ_m`) and frozen in the protocol before any held-out scoring.

### 12.3 Evaluation protocol (frozen before any prediction)

- Task (controlled, source-established masking, labeled as such): an
  accepted record with a valid original DOI has its original DOI and PMID
  masked (and its notice identifiers when equal to the original). Label
  `positive` with target `doi:<key>` when another record carries the same
  original DOI; `negative` (correct answer: abstain) when no other record
  does. This measures linking under masking, not natural missing-ID accuracy.
- Groups: connected components of records sharing an original or notice
  key or a `Record ID`. One query record per group (smallest ordinal with a
  valid original DOI); candidates never include the query record itself.
- Splits: 40 tuning and 120 held-out groups, disjoint by group, drawn with a
  fixed seed; held-out = 60 positives and 60 negatives; strata quotas
  (similar-title negatives, year/author disagreement positives,
  notice-also-original, mixed-event, shared-notice) are recorded with the
  draw. Languages are reported from the title script; RW holds 1 record with
  Arabic script [V], so no Arabic stratum exists.
- Primary score per group: correct when a positive selects the target or a
  negative abstains. Reported: primary accuracy, selection precision,
  coverage, false selections on negatives, positive recall, abstention,
  candidate recall@5 (separately), Wilson 95% intervals, discordant counts
  `b` (baseline right, model wrong) and `c`, exact one-sided binomial
  McNemar p.
- Admission gate (model vs baseline on held-out): ≥ 120 eligible groups;
  accuracy gain ≥ 10 percentage points; p < 0.05; selection coverage ≥ 60%;
  false selections on negatives not above baseline; zero notice/original
  confusions; zero prohibited fact writes; resource limits met.
- Envelope: ≤ 200 calls, ≤ 4,500 input and 450 output tokens per call
  (provider-counted, all billable categories), ≤ 900,000 / 90,000 total,
  ≤ 60 min, 30 s per call, at most two tuning passes, no held-out-driven
  revision or retry. Cost estimate `≤ 0.90·p_in + 0.09·p_out` USD only where
  the rates cover the invocation; USD 5 is a planning ceiling, not an
  authorization.
- Model: chosen only with authorized access, after a check of the provider's
  current specification and prices. Access status on 2026-10-27: none in
  this environment (no key; the coding session's own access is not
  authorized for experiments). The experiment is a **blocked prerequisite**
  until the owner supplies a key and spending approval; nothing about model
  performance is reported until then.
- Natural unresolved links (records with neither original DOI nor PMID):
  candidates are produced by the baseline and written to a blinded review
  sheet for human adjudication; no labels are invented.

## 13. Resource budgets (reference host: 4 vCPU, 15 GiB, CPU-only)

| Measure | Budget |
|---|---|
| Full pinned build | ≤ 120 s wall, peak RSS ≤ 512 MiB, index ≤ 512 MiB |
| Warm lookup (2,000 declared mixed queries, ≤ 20 events per page) | p95 ≤ 20 ms |
| Fresh-process lookup (CLI, same mix, sample of 200) | p95 ≤ 1 s |
| Tension, one query, all interventions | p95 ≤ 50 ms warm |
| Baseline ambiguity candidate retrieval | p95 ≤ 100 ms warm |

The query mix is declared in `docs/verification/stage-02/scripts/benchmark.py`
before measurement: 40% matched DOI, 10% matched PMID, 10% notice-only,
5% ambiguous PMID, 5% two-ID, 25% absent synthetic, 5% invalid. Five measured
builds; median and maximum reported. "Fresh process" means a new interpreter
per query; OS page-cache eviction is not claimed.

## 14. Tests and acceptance gates

Test files live in `tests/stage02/` with unique `test_rde_*` names; every
test carries a suite marker. CI uses only committed fixtures (synthetic
`10.5555` records and at most 120 attributed real records), transport and
model doubles, and no network. The full-source checks run outside CI with
`docs/verification/stage-02/scripts/`, on the same code revision.

Gates (02-A is the Master Plan gate; 02-B to 02-I refine it):

| Gate | Requirement |
|---|---|
| 02-A | Successful positive, negative, malformed-data, duplicate and conflict-resolution tests (directive §14 items 1–17) |
| 02-B | Pinned real build: receipt verified, `N_records = N_accepted + N_quarantined` = 73,356, line accounting exact, verify clean, two builds give equal semantic and artifact digests and equal query output |
| 02-C | Independent streaming oracle agrees with the index for every valid original/notice DOI/PMID key of the real snapshot and ≥ 1,000 absent synthetic keys (0 mismatches); ≥ 40 real reviewed cases covering all four event types and the ambiguity classes pass |
| 02-D | Stage-02 schemas meta-valid and versioned; schema and semantic validation positive and negative tests; v1 subject projection validates against the v1 investigation contract |
| 02-E | Evidence Tension: on the frozen 16-case adversarial set, every expected diagnostic class detected, zero changes on controls, baseline comparison reported; ≥ 4 real pinned demonstrations covering redistributed support, uncertain identity/notice relation and unsupported temporal precision |
| 02-F | Bounded corroboration: all failure modes of §9 tested with doubles and none becomes a negative finding; a real bounded run within limits; replay reproduces the same assertions |
| 02-G | Evidence Ambiguity Investigator: boundary and forbidden-promotion tests, baseline frozen on tuning, protocol frozen before predictions, and the model experiment executed under the protocol with its disposition (admitted, or exclusion proposed) — or the exact missing prerequisite recorded as a blocker |
| 02-H | Budgets of §13 met on the reference host, five builds measured |
| 02-I | Complete CI green on Python 3.12 and 3.13 at the cited revision; three review perspectives completed with findings dispositioned; required documents and handoff complete |

## 15. Assumptions

- A1 [I]: RW `RetractionDate` is the notice's publication date as RW
  recorded it; RW states dates may contain errors.
- A2 [D]: equal DOIs differing only in ASCII case are the same DOI (DOI
  system case-insensitivity for ASCII; RetractionBot folds A–Z the same way
  [V]). Non-ASCII case is not folded.
- A3 [D]: bare DOIs containing `%xx` are kept literally; the decoded form is
  a different key. 24 source values contain `%` [V]; a query with `<`
  instead of `%3C` does not match them (R-023).

## 16. Changes after freezing

The specification was frozen at `36696b3`. The changes below were made while
implementing it; each is recorded with its reason and the test that holds it.
None lowers a gate or a budget. Items 2, 4, 5, 9 to 14 and 17 change a
result; all of them except item 5 are stricter than the frozen text, and item 5
removes an intervention whose outcome is fixed in advance. Items 11 to 22 come
from the three review passes of `3a6f1eb` (TEST_RESULTS.md, review
dispositions); their fail-first run is
`evidence/fail-first/review-findings-at-3a6f1eb.txt`.

| # | Section | Change | Reason | Held by |
|---|---|---|---|---|
| 1 | 10.1 | Tables `title_token` and `token_df` replace `issue_index` | The ambiguity baseline (12.2) needs title-token postings and document frequencies; issue lookups use the `quarantine` table and the `ident` table, whose invalid occurrences have a partial index | `test_rde_import.py`, `test_rde_advisory.py` |
| 2 | 11.1 rule 8 | `no_record` carries no `retraction_date` assertion | A date of something not found is not a fact or an uncertainty about a date | `test_rde_policy_cases.py` |
| 3 | 9 | Fatal replay code `CORROBORATION_INVALID`; the works not attempted after a stop are listed by DOI | A tampered or malformed replay bundle must fail the build, not load partially; an unattempted work must not read as "nothing found" | `test_rde_corroboration.py` |
| 4 | 10.3 step 5 | `query_pair` bridging only when the DOI's own set `O_d` is non-empty | Without it a PMID-only partner could stand in for a DOI that names no work | `test_rde_lookup.py`, `test_rde_policy_cases.py` |
| 5 | 11.2 | The default plan runs `exclude_origin` only when there are at least two origins; otherwise the report says `single_origin` | Excluding the only origin always empties the evidence and would report every field as changed | `test_rde_tension_properties.py` |
| 6 | 3 | The git blob SHA-1 of the CSV is checked against the receipt, as well as SHA-256 and size | It ties the file to the pinned commit without trusting the download URL | `test_rde_import.py` |
| 7 | 12.3 | Draw quotas and strata for the 160 evaluation groups are fixed in `ai/protocol.json` | The snapshot holds only 16 hard positives; quotas keep each stratum in both splits | `ai/protocol.json` (frozen at `fe187b1` before any prediction) |
| 8 | 10.3 step 7 | At most 100 relevance hits are listed, followed by `RELEVANT_LIST_CAPPED` with the total | A short common key could otherwise return thousands of quarantine hits in one response | `test_rde_lookup.py` |
| 9 | 11.1 rule 8 (C-9) | RW retraction events inside a type conflict also count for the date: if their dates differ from the clear ones the date is `uncertain` (`MULTIPLE_RETRACTION_DATES`) | Found on the real demonstration `10.1007/s13277-014-2995-5`: a publisher deposit that typed the 2015 notice as a correction had made the 2017 date a verified fact. The prebuild simulator was changed the same way. On the RW-only index no result changes (61,844 retracted originals); with the pinned Crossref replay one does | `test_rde_policy_regressions.py` (fails without the fix) |
| 10 | 10.3 step 5 (C-10) | With both identifiers, the anchor is `doi:d` only when `O_d` is non-empty; otherwise `pmid:p` | Found while writing the test for item 4: a query pairing an unknown DOI with a known PMID reported an exact identity anchored at the unknown DOI, which no record carries. The simulator was changed the same way | `test_rde_spec_changes.py` (fails without the fix) |
| 11 | 11.1 rule 7d (C-11) | Reinstatements alone, with no `supersedes` link to an event of the set, give `uncertain`, null (`REINSTATEMENT_UNLINKED`) instead of `verified_fact`, `reinstated`. Frozen case P04 is amended in `simulations/stage02/cases/post_freeze_amendments.json` (the frozen file is unchanged; both loaders check the frozen value before applying the amendment) | Directive 9: "Reinstatement requires adequate original/target/supersession evidence before it can change a current-effect projection"; "unlinked reinstatement: uncertain/null". On the RW-only index 275 originals change from `reinstated` to `uncertain` | `test_rde_policy_regressions.py`, `test_rde_policy_cases.py` (P04) |
| 12 | 11.1 rule 7 (C-12) | Retraction Watch events of different types on one notice key are a sequence, not a conflict group, when every member is from RW and every pair of different types is definitely ordered; the reducer then reads them as separate propositions and adds `SEQUENTIAL_EVENTS_SHARE_NOTICE`. Undated RW copies join a sequence only if their type is already in it. Crossref relations and unordered pairs still form conflict groups | Directive 9: "A concern followed by retraction is not a conflict". Found on `10.1038/nature16193` (an expression of concern and a later retraction share one notice). On the RW-only index 34 originals change from `conflicting` to `retracted` and 4 to `uncertain` (`MIXED_CURRENT_EFFECT`) | `test_rde_policy_regressions.py` (sequence, unordered and publisher-disagreement cases); real cases R46, R47 |
| 13 | 11.1 rule 7 (C-13) | The proposition key is the notice key together with the original anchor, as the frozen text says; the code had grouped by notice key alone | A notice shared by two originals is two propositions | `test_rde_policy_regressions.py` |
| 14 | 8, 11.1 (C-14) | Each Crossref assertion records `dependence` (`known` or `unknown`); support that comes only from origin `unknown` gives `uncertain`, null (`SUPPORT_ORIGIN_UNKNOWN`); `exclude_origin` reports `dependence_unknown` | Directive 11: "Unknown origin/dependence remains unknown." No pinned replay assertion has origin `unknown`, so no real result changes | `test_rde_policy_regressions.py`, `test_rde_corroboration.py` |
| 15 | 10.1, 10.4 (C-15) | A build never replaces an artifact of the same snapshot with different digests (`ARTIFACT_EXISTS`); every event is validated against the event schema and the manifest against its schema before publishing (`ARTIFACT_INVALID`); `verify` recomputes the derived tables (`ident`, `notice`, `event_notice`, `title_token`, `token_df`, duplicate groups) from the stored raw records and compares the manifest; `cr_attempt` rows are in the export, and the canonical lines of `cr_attempt` and `cr_assertion` leave out `retrieved_at` and `attempt_id` | A rebuild with another replay bundle had deleted earlier evidence; tampering with a derived table passed `verify`; two acquisitions of the same evidence must have the same semantic digest | `test_rde_review_findings.py` (A1 to A3) |
| 16 | 10.1 (C-16) | The read-only URI percent-encodes the path, and the open checks that SQLite opened that file (`PRAGMA database_list`), else `INDEX_CORRUPT`; stored digests must be 64 hexadecimal characters | A `#`, `?` or `%` in the path could end the URI early, open another file or add URI parameters such as `mode=rwc` | `test_rde_review_findings.py` (S2) |
| 17 | 10.3 step 7 (C-17) | Relevance hits also match a quarantined or invalid value that normalizes to the key, or that contains the key once percent escapes and invisible characters are removed | A value with `%2F`, an embedded zero-width space or a broken percent escape was not reported as a possible coverage gap, so the lookup said "not found". A hit is never a match | `test_rde_review_findings.py` (S1); real case R43 |
| 18 | 6.1, 6.2 (C-18) | The outer trim set is Unicode whitespace that is not a control character, plus tab, LF and CR; U+000B, U+000C, U+001C to U+001F and U+0085 stay in the value and are rejected | Directive: "Reject/flag controls ... without silent repaired exact matches"; Python's `str.strip()` had removed these controls silently | `test_rde_review_findings.py` (S6) |
| 19 | 10.3 output | `notice_hits` lists at most 100 entries and `notice_hit_count` gives the total | Same bound as item 8, for notice-role hits | `test_rde_review_findings.py` (A7) |
| 20 | 11.2 | The tension report states `base_unresolved` when the base result has no settled value (uncertain, conflicting or unavailable) | A change in a view of an unresolved base is not evidence of fragility of a settled answer | `test_rde_review_findings.py` (Sci-7) |
| 21 | schemas | The 200-character limit on a temporal `raw` value is removed; a successful corroboration attempt must have HTTP status 200 | A real date cell longer than 200 characters produced an event that failed its own schema | `test_rde_review_findings.py` (A1, S4) |
| 22 | 9 | The Crossref client follows no redirect, enforces a total read deadline, honours `Retry-After` (seconds or HTTP date) on 429 and 5xx and records an unreadable one as a failure; replay payloads must be regular files within the size cap, strict JSON (no duplicate keys, NaN or Infinity) and with a hexadecimal hash | Security review findings S3, S4, S5, S7 and S8 | `test_rde_review_findings.py` |
| 23 | 4 | `POLICY_VERSION` is `citerift-rde-policy/1.1.0` and `TENSION_VERSION` is `citerift-evidence-tension/0.2.0`. `PARSER_VERSION`, `INDEX_FORMAT` and `BASELINE_VERSION` are unchanged. `SCHEMA_VERSION` stays `1.0.0`: the schemas were first written with the engine (`e4de42b`) and are first delivered with this stage, so no other 1.0.0 exists | Section 4: "A change to any rule in §5 to §11 increments the matching version"; items 2, 4, 9 to 14 change §10 and §11 rules, and item 20 the tension report. Readers refuse an index built under another policy version (`INDEX_FORMAT_MISMATCH`) | `test_rde_spec_changes.py` |

Four sentences of the frozen text were also edited in place in `e4de42b`,
together with the first engine code, instead of being listed here: the
`CR_UNSUPPORTED` row of the issue table (5.1), the BOM rule (`utf-8-sig`,
5.2), the reader check of the stored digests (10.1), and the definition of
`N_d` and `N_p` by notice-role occurrence (10.3 step 2). `git diff 36696b3 --
docs/verification/stage-02/SPECIFICATION.md` shows them.

The prebuild simulator was changed after the freeze in four commits:
`e4de42b`, together with the first engine code, for notice-role matching by
the raw notice key (10.3 step 2), the reinstatement rule of any origin
(11.1 rule 7a) and item 4; `7a7d6b6` for item 9; `3a6f1eb` for item 10; and
the review batch for items 11 to 14 and 18. The frozen expected outputs
(`simulations/stage02/cases/`) were not changed; the one amended expectation
(P04, item 11) is applied from `post_freeze_amendments.json`. The real-case
outcomes in `tests/stage02/fixtures/real_cases.json` were derived with the
changed simulator, so on those points the simulator is not independent of the
engine (SIMULATION_REPORT.md 5). The effect of items 11 to 14 on every
original key of the snapshot is in `evidence/policy-impact-rw.json` and
`evidence/policy-impact-cr.json`.
