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
| S3 | Latest-row-wins or greatest-date-wins hides a retraction or invents reinstatement | M | H | order-independent reducer; reinstatement needs supersession evidence | row-permutation test (`test_rde_export_diff.py`); INV-P1 to P3 and P8 property tests (`test_rde_policy_properties.py`, added after freezing; see §6) |
| S4 | PMID bridges two works into one | M | H | one-hop bridging only when the secondary identifier is unique; PMID with several DOIs is `ambiguous_identity`; two-ID compatibility check | INV-L2/L3 tests, 17 real divergent PMIDs |
| S5 | Day-1 dates presented as exact | H | M | RW guide convention: day 1 has no bounds; date shown as `uncertain`; chronology from bounds only | temporal tests, `require_temporal_bounds` demonstrations |
| S6 | Redistributed Crossref RW relations counted as independent corroboration | H | M | origin and dependency on every assertion; `collapse_shared_origin` | INV-P7 test, real Wakefield replay |
| S7 | Publisher-deposited relation types trusted as truth | M | M | publisher relations are a separate origin with unknown dependence; type disagreements are conflicts, never silent resolutions | conflict tests, real Lancet Surgisphere replay |
| S8 | Different events over time reported as a conflict | M | M | conflicts only within one proposition (same notice and original); RW events of different types on one notice that are definitely ordered are a sequence (§6) | concern→retraction and correction-after-retraction tests; sequence, unordered and publisher-disagreement regressions |
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

## 6. Changes after freezing

The review passes of `3a6f1eb` (TEST_RESULTS.md, review dispositions) found
risks the frozen table did not list, or controls that did not work. The table
above is kept as frozen except the two Check/Control cells marked §6.
The residual risks of §5 are now RISKS.md R-023 to R-025, and P1 is R-027:
the owner later ruled out API keys, so the experiment waits on a route
decision instead (DECISIONS.md D-023).

| ID | Risk | L | I | Control | Check |
|---|---|---|---|---|---|
| S12 | Support of unknown origin or dependence presented as established | M | H | `dependence` on every Crossref assertion; support only of origin `unknown` gives `uncertain` (SPECIFICATION.md 16 item 14) | `test_rde_policy_regressions.py`, INV-P8 property test |
| S13 | A reinstatement with nothing it supersedes shown as the current effect | M | H | rule 7d gives `uncertain` (item 11); 275 real originals affected | P04 (amended), INV-P3 property test, `evidence/policy-impact-rw.json` |
| S14 | A PMID-bridged event alone yields `verified_fact` | M | M | kept as frozen (cases P33, T05, T06): identity status `bridged` and `exclude_ambiguous_links` show it; not hidden | proposed to the owner as R-026 |
| E11 | A rebuild with other evidence deletes an earlier artifact of the same snapshot | M | H | `ARTIFACT_EXISTS`; equal builds only are replaced (item 15) | A2 tests |
| E12 | A derived table is altered and `verify` still passes | L | H | `verify` recomputes derived tables from the raw records and checks the manifest (item 15) | A3 tests |
| E13 | Characters in the index path change which file SQLite opens or its mode | L | H | percent-encoded URI and `PRAGMA database_list` check (item 16) | S2 tests |
| E14 | Controls removed as whitespace make an exact match | M | H | explicit trim set (item 18) | S6 tests |
| E15 | Hidden or encoded identifier forms turn a coverage gap into "not found" | M | H | relevance by normalized value and skeleton (item 17) | S1 tests |
| X5 | Redirect, slow drip or bad `Retry-After` from the API host | L | M | no redirects, total deadline, `Retry-After` parsed or recorded as failure (item 22) | loopback-server tests S3, S5, S8 |
| P5 | The AI admission criterion "selection coverage ≥ 60%" cannot be met on this snapshot | H (observed) | M | not lowered; reported to the owner with the arithmetic (TEST_RESULTS.md) | protocol arithmetic in TEST_RESULTS.md |

Residual risk proposed for the owner: R-026, a single PMID-bridged event can
give `verified_fact` with identity `bridged` (S14).

## 7. AI Protocol v2 and the local open model (2026-10-28)

v1's P5 is confirmed and closed by superseding the protocol, not by lowering
it (DECISIONS.md D-025; RISKS.md R-027 closed, R-028 open).

| ID | Risk | L | I | Control | Check |
|---|---|---|---|---|---|
| AI1 | A model suggestion is read as a fact or an identity | M | H | `AdvisoryAssessment` has no path into the store; `local_model.py` imports neither the build, the store nor the advisory boundary; CLI output keeps the baseline unchanged and labels the model result advisory | `test_rde_local_model.py` (invariance, import and CLI tests); real-index demonstration (`ai/v2/inference/separate-process-demo/`): index SHA-256 and lookup output unchanged |
| AI2 | Missing or tampered weights produce a confident wrong answer | M | H | size and SHA-256 of every manifest file checked before loading; safetensors only; `trust_remote_code=False`; failure is `abstain` with a reason code | artifact-mismatch and missing-weights tests; CLI no-weights demonstration |
| AI3 | The model or the evaluation reaches the network | L | H | offline environment variables and `local_files_only`; runs in a network namespace with no interfaces plus a socket guard | run logs (`curl` fails in the namespace; summaries record `network_denied`) |
| AI4 | Tuning on the holdout, or a second try after seeing it | M | H | part 1 and part 2 committed before the draw; one run; no change after any prediction | commit order `6d3de07`, `2136943`, `9e23c76`, `4a0fc19` |
| AI5 | The holdout is too easy for the baseline to test any gain (v1's failure) | H (v1) | H | stratum oversampling by a retrieval-feature rule; attainability rule at the draw | `holdout-attainability.json` (26 baseline errors, `p_best = 1.5e-8`) |
| AI6 | The model is enabled in the product despite not being admitted | M | H | opt-in only (`--model-dir`); exclusion recommended; R-028 records the constraint for later stages | owner decision; HANDOFF.md |
| AI7 | A heavy inference stack enters the core engine or CI | L | M | separate hash-pinned `requirements/inference-cpu.txt`, `.venv-infer/` ignored; lazy import | `test_rde_local_model_import_does_not_load_an_inference_stack`; core `uv.lock` unchanged |

Residual risk proposed for the owner: R-028 (the model is not admitted; keep
it out of the default product).

