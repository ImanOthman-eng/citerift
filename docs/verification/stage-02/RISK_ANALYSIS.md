# Stage 02 Risk Analysis

Likelihood and impact are qualitative judgments (low / medium / high), not
measured probabilities. "Control" names the mechanism; "Check" names the test
or measurement that shows the control works. Project-level risks that outlive
the stage are also in RISKS.md (R-022 onward).

## 1. Scientific and semantic risks

| ID | Risk | L | I | Control | Check |
|---|---|---|---|---|---|
| S1 | A notice DOI is read as the retracted paper | M | H | separate roles in storage and queries; `notice_only` state with no projection | INV-L1 tests, oracle role comparison, real case NC-04 (NEJM notice) |
| S2 | Absence read as "not retracted" | M | H | no such value; `not_found_in_checked_sources` only as `uncertain` with provenance; relevant quarantine and invalid identifiers turn absence into a coverage gap | v1 schema rules, projection tests, absence controls |
| S3 | Latest-row-wins or greatest-date-wins hides a retraction or invents reinstatement | M | H | order-independent reducer; reinstatement needs supersession evidence | INV-P2 to P4 metamorphic tests (row permutation, added events) |
| S4 | PMID bridges two works into one | M | H | one-hop bridging only when the secondary identifier is unique; PMID with several DOIs is `ambiguous_identity`; two-ID compatibility check | INV-L2/L3 tests, 17 real divergent PMIDs |
| S5 | Day-1 dates presented as exact | H | M | RW guide convention: day 1 has no bounds; date shown as `uncertain`; chronology from bounds only | temporal tests, `require_temporal_bounds` demonstrations |
| S6 | Redistributed Crossref RW relations counted as independent corroboration | H | M | origin and dependency on every assertion; `collapse_shared_origin` | INV-P7 test, real Wakefield replay |
| S7 | Publisher-deposited relation types trusted as truth | M | M | publisher relations are a separate origin with unknown dependence; type disagreements are conflicts, never silent resolutions | conflict tests, real Lancet Surgisphere replay |
| S8 | Different events over time reported as a conflict | M | M | conflicts only within one proposition (same notice and original) | concern→retraction and correction-after-retraction tests |
| S9 | Model output promoted to a fact | L | H | advisory type without store access; forbidden keys abstain; read-only index | boundary tests, index hash before/after |
| S10 | Synthetic or masked-task results reported as natural accuracy | M | H | tasks labeled "controlled masking"; synthetic fixtures use 10.5555 and `synthetic: true` | report wording review, fixture checks |
| S11 | Arabic capability claimed without Arabic data | M | M | RW has 1 Arabic-script record; no Arabic stratum; no translations | protocol text, TEST_RESULTS statement |

## 2. Data integrity and engineering risks

| ID | Risk | L | I | Control | Check |
|---|---|---|---|---|---|
| E1 | Wrong or partial source bytes imported | L | H | size and SHA-256 against the receipt before parsing | wrong-hash and truncated-file tests |
| E2 | CSV quirks (BOM, embedded newlines, blank lines, bad quoting) lose or merge records | M | H | strict parser, physical line accounting, fatal failure when boundaries are unrecoverable | malformed-CSV tests, INV-A2 on the real file |
| E3 | `INSERT OR REPLACE` or `Record ID` primary key drops evidence | M | H | ordinals as keys; plain INSERT; duplicate groups kept | reused-ID and identical-duplicate tests |
| E4 | Failed rebuild destroys the last good index | L | H | temp file, validation, `os.replace`; other snapshots untouched | failure injection at each publication boundary |
| E5 | Normalizer bug hidden because test oracle shares the code | M | H | oracle written separately (separate author pass) and independent fixture table inspected by hand | oracle comparison, fixture review record |
| E6 | SQL injection or malicious source text | L | M | parameterized SQL only; text never interpreted; JSON output escaped by `json` | SQL-looking ID tests, malicious row test |
| E7 | Resource exhaustion from huge fields or rows | L | M | 1 MiB field limit, 2M row limit, page cap 100, payload cap 4 MiB | limit tests |
| E8 | Non-deterministic output (dict order, time, locale) | M | M | canonical JSON; run metadata outside digests | double build digest equality, permutation test |
| E9 | Offline operations open sockets | L | M | no network imports in query path; refusing socket stub in tests | offline tests |
| E10 | SQLite version differences change behavior | L | L | no extensions, standard SQL; byte-identical files not required | CI on 3.12/3.13 runners |

## 3. External-source risks

| ID | Risk | L | I | Control | Check |
|---|---|---|---|---|---|
| X1 | Crossref rate limits or outages | M | L | 1 req/s, concurrency 1, Retry-After, bounded retries, deferral | transport-double tests (429, 5xx, timeout) |
| X2 | HTTP 200 with an error or mismatched body read as "no relation" | M | H | strict status, message-type and DOI checks; failures recorded as failures | malformed-200 tests |
| X3 | Access restriction (403) evaded | L | H | 403 stops the run | 403 test |
| X4 | Licensing: redistribution of the RW dataset | M | M | never commit the CSV or bulk extracts; ≤ 120 fixture records with attribution | repository check of committed fixtures |

## 4. Schedule and process risks

| ID | Risk | L | I | Control |
|---|---|---|---|---|
| P1 | AI experiment cannot run (no authorized model access) | H (observed) | M | complete the boundary, baseline and frozen protocol; record the exact prerequisite as a blocker; no invented results |
| P2 | Hackathon deadline (R-010) | M | H | build the guaranteed engine first; keep the AI workstream isolated |
| P3 | Same-model reviews are not independent | H | M | three separate review passes with distinct scopes; limits stated |
| P4 | Ephemeral container loses data | M | M | everything committed and pushed; `EXECUTION_LEDGER.md`; raw data re-downloadable and hash-checked |

## 5. Residual risks proposed for the owner

- R-023 literal `%xx` in bare DOIs: lookups by the decoded form miss 24
  source values (deliberate; no silent repair).
- R-024 day-1 dates have no bounds, so many precise-date and ordering
  conclusions are withheld (deliberate conservatism).
- R-025 identity beyond exact identifiers (title/author matching) is advisory
  and not validated on natural cases.
- P1 above, if the owner does not supply model access.
