# CITERIFT Stage 04 — Master Execution Package (planning only)

Detection Engine and Vertical Slice, with Investigation Memory and the Investigation Workflow Controller.
Prepared 2026-11-09 for the owner, EVE TELOS, under the owner's instructions of 2026-11-09
(`cmsg_018VCB51nDHP6HXmLU4ea5yPPExKYg1WPyjb82BfbKrqGQ` and addendum `cmsg_018VCB51nDHP6HXmLU4ea5yP4tT61BM3491HRjgGX8wGKb`).
Nothing in Stage 04 is implemented. The only repository change is the authorization record (commit `59bc7ea`).

**Recommendation: PROCEED WITH CONDITIONS** (section 18). Five owner decisions are needed first (section 15).

Labels used: **[fact]** verified in this session with the command or file named; **[inference]** reasoned from facts,
not observed; **[proposal]** a design choice offered for approval.

---

## 0. Baseline and checks run

| Item | Value |
|---|---|
| Branch | `claude/stage04-detection-engine` |
| Base main | `741df40c408d9d68d9805f901ef0d82b523cdb2c` (after PR #6) |
| Authorization commit | `92312be529334e151182ceb2cff47be16f63434e` (registry seq 49 owner AUTHORIZED, seq 50 IN_PROGRESS) |
| Authorization record | `59bc7ea5991174bf4b51e7bbc664a1f29e8e0d9b`, `docs/verification/stage-04/authorization/OWNER_AUTHORIZATION_2026-11-09.md` (pushed) |
| Stages 00–03 | `ACCEPTED_CLOSED` at `0c21182`, `85da719`, `cf06083`, `b93314d`; unchanged |

Checks at `59bc7ea` [fact]: `citerift-gov check` 0 errors 0 warnings; `render-status --check` up to date; `ruff check .`
clean; `mypy` no issues in 52 files; `pytest` **2051 passed** (after the side branches were fetched, section 5).

Read-only reconstruction checks run outside the repository (scratchpad, nothing committed) [fact]:

1. Stage 02 index rebuilt from the pinned Retraction Watch snapshot (SHA-256 `2f116e9f…0a655`, verified): 88 s,
   artifact digest `adcf7b65…16d9` and semantic digest `7b2a2344…5f88`, **equal to the accepted Stage 02 handoff**.
2. A join probe: every retained Stage 03 capture bundle in the repository extracted offline with the accepted
   engine, every valid DOI/PMID key looked up in that index. Results in section 2.3.

---

## 1. Current-state reconstruction

### 1.1 Stage 00 — Engineering Foundation (accepted at `0c21182`)

- **Governance model.** Registry `governance/stage_registry.json` (schema-fixed dependencies, artifacts, policy),
  explicit transition table (`src/citerift/governance/model.py`), every write validated on a copy and written
  atomically; history replay must equal recorded status; owner decisions need `owner_ref`. `PROJECT_STATUS.md` is
  generated. Owner merges personally (D-019).
- **Contracts.** `schemas/contracts/v1` (JSON Schema 2020-12, URN ids, version 1.0.1): assertion wrapper with
  `verified_fact | model_inference | uncertain | unavailable | conflicting`; **no value means "not retracted"**;
  `not_found_in_checked_sources` must be `uncertain` with provenance; `model_inference` forbidden for
  `retraction_status`. The investigation record is **paper-centric**: one `subject_paper`, many `citations`.
- **Protected paths.** Stage 00 owns governance code, `schemas/governance`, `schemas/contracts/v1`,
  `src/citerift/contracts`, `.github/workflows`, `.github/rulesets`, `.gitattributes`, `tests/stage00`. Drift is an
  error (`VERIFICATION_STALE`) unless an amendment covers it.
- **CI.** Python 3.12 and 3.13, full-history checkout (`fetch-depth: 0`), governance check before any tool runs,
  lock check, ruff and mypy strict, schema validation, full pytest with a machine report, `check-report` (a skipped
  test makes the run partial and **fails CI**), clean-tree check, `pip-audit`. `ci-gate` required on `main`.
- **Accepted residuals relevant to Stage 04.** R-001 (agent uses owner's GitHub identity), R-002 (owner refs not
  machine-verified), R-003/R-004 (hand edits and agent-entered CI evidence are detected, not prevented), R-016 (the
  gate is defined by an editable workflow), R-005/R-006 (contract compatibility fixture-based; formats permissive).

### 1.2 Stage 01 — Independent Feasibility (accepted at `85da719`, D-020 limited RESCOPE)

Only what is in `docs/verification/stage-01/`:

- Positive chains: Wakefield 1998 (MMR vaccine), Obokata 2014, Wolfe-Simon 2011 (GFAJ-1); negative controls
  NC-01 (correction/concern), NC-02, NC-03 (absence → `not_found_in_checked_sources`), NC-04 (notice cited, not paper).
- Arabic census (2026-10-01 dumps, link-bearing citations only, lower bounds): at least 158 retracted papers cited in
  157 articles (198 citations); 170 of 198 show no warning. English dump scan: 745 articles.
- Owner constraints (D-020): edition findings only for the covered population with lower bounds; timing claims stay
  case-specific.
- `MAESTRO_DESIGN_BRIEF.md` assigns to Stage 04: MR-01 to MR-17b, MR-21, MR-23 to MR-25, CP-1 to CP-6 for one
  language, tasks T1–T5 and T10, Investigation Memory v0, budgets, error codes; acceptance tests AT-01 to AT-05,
  AT-07, AT-08, AT-12. It also says Stage 04 events live in a **Stage-04-owned schema that `$ref`s v1** (MR-05).

### 1.3 Stage 02 — Retraction Data Engine (accepted at `cf06083`)

- **Interface.** `citerift.retraction.query`: `Index(path)` (read-only, immutable), `Index.gather(doi, pmid)`,
  `render(evidence, snapshot_id)`, `lookup(index_path, doi, pmid)`, `event_detail`. CLI `citerift-rde`.
  Offline except `enrich`.
- **Data model.** One SQLite file per pinned snapshot (`rw-2f116e9ffed718e6`, 73,356 records, policy
  `citerift-rde-policy/1.3.0`, schemas 1.1.0); events, notices, duplicate groups, identifier occurrences with roles.
- **Query semantics.** `lookup_state` ∈ `matched | notice_only | ambiguous_identity | no_record | unavailable |
  invalid_query` (not epistemic statuses). Two-identifier queries check DOI/PMID compatibility and return
  `ambiguous_identity` on conflict. PMID bridging is one hop; bridged evidence never supports a value (R-026 fix).
- **Uncertainty.** `projection.retraction_status` is a v1 assertion with `basis` reason codes
  (`SOURCE_RECORDED_RETRACTION`, `NOTICE_ONLY`, `IDENTITY_AMBIGUOUS`, `BRIDGE_ONLY_SUPPORT`, `MIXED_CURRENT_EFFECT`,
  `REINSTATEMENT_UNLINKED`, `COVERAGE_GAP_RELEVANT_ROWS`, …). `verified_fact` means "established from the cited
  source record". Issues `IDENTITY_SECONDARY_DIVERGENT`, `PMID_ROLE_COLLISION` are reported, not resolved.
- **Provenance.** `snapshot_id`, `policy_version`, `evidence_digest`, per-event `row_sha256`.
- **Performance.** Budgets: build ≤ 120 s (measured 88 s here), warm lookup p95 ≤ 20 ms, fresh-process p95 ≤ 1 s.
  Probe: 1,576 distinct lookups in 0.14 s with one open `Index` [fact].
- **Limitations.** R-025 (identity beyond identifiers), R-029 (bridged evidence withheld), R-031 (PMID role
  collision), R-023/R-024, R-028 (local model excluded), one Arabic-script record, no Arabic claim. The CSV is not
  redistributable (MR-25); CI uses an attributed ≤ 120-row field subset (`tests/stage02/fixtures`).

### 1.4 Stage 03 — Wikipedia Extraction Engine (accepted at `b93314d`)

- **Interface.** `citerift.wiki`: `capture_revision` (the only network path; 2 hosts, 10 s spacing, Retry-After,
  cross-process lock), `extract_bundle` (offline, isolated worker), `verify_bundle`, `replay_bundle`. CLI
  `citerift-wiki`.
- **Outputs.** Content-addressed capture bundles; extraction documents (`schemas/wiki/v1/extraction`) with containers,
  uses (binding states), units (`citation_template | external_data_template | unsupported_citation_template |
  unstructured_text`), identifiers (scheme, **role** `primary_citation_field | identifier_link |
  labeled_reference_text | marker_target | textual_mention | unresolved`, boundary, byte-exact anchor, Stage 02
  normalization record), marker observations (`recognized_warning_text … not_inspected | unavailable`), exceptions,
  issues, accounting, `extraction_digest`.
- **Reconciliation.** Source/render joins never across revisions; abstains instead of guessing (R-038 fixed).
- **Verification/replay.** `verify` checks the document against the bundle; `replay` re-derives it (needed where
  identifier decoding must be trusted).
- **Limitations** (handoff "Requirements for the next stage"): `unstructured_text` not proof of a citation; abstained
  render links are unknown, not absent; `IDENTIFIER_BOUNDARY_AMBIGUOUS` and `unresolved` are unconfirmed; missing
  identifier or `not_inspected` is never "not retracted"; Arabic warning detection untested on real articles;
  co-reported identifiers never merged. R-035 (support boundaries, e.g. publisher URLs without `/doi/`), R-036
  (English unit precision interval reaches 0.929), R-037.

---

## 2. Stage 02 → Stage 03 → Stage 04 integration map

### 2.1 The exact boundary

```
Stage 03 extraction document                         Stage 02 index
identifiers[i]                                       Index.gather(doi=?, pmid=?)
  .scheme  ("doi"|"pmid")                ─────────▶    normalize_query() re-normalizes (idempotent, property-tested)
  .normalization.normalized  (Stage 02 key)            → lookup_state, identity, events(row_sha256),
  .role, .boundary, .unit_id, .container_id            projection.retraction_status (v1 assertion + basis),
  .source anchor (rev id, byte span, sha256)           issues, snapshot_id, policy_version, evidence_digest
units[u].identifier_ids  (co-reported keys) ─────────▶ pair query gather(doi=d, pmid=p) when a unit has one of each
containers[c].use_ids / uses[].binding                 (Stage 02 compatibility check, section 10.3 step 5)
markers[c].state  (observation only; Stage 05 interprets)
```

- No code path joins the two stages today: Stage 03 imports only `citerift.retraction.identifiers` (enforced by
  `test_runtime_imports_stay_inside_the_stage_boundary`). Stage 04 is the first consumer of both [fact].
- The Stage 03 key is the Stage 02 normalizer's output; passing it back through `normalize_query` is safe because
  normalization is idempotent (`test_rde_doi_normalization_is_idempotent`) [fact]. Stage 04 keeps Stage 03's own
  normalization record as provenance and asserts key equality.

### 2.2 What Stage 04 adds on top

Candidate building per citation unit, the pair query, a deterministic decision table, an article-centric report
schema that embeds v1 assertions, Investigation Memory, the Workflow Controller, replay.

### 2.3 Real-data join probe on the retained Stage 03 bundles [fact]

| Measure | Value |
|---|---|
| Bundle directories / distinct revisions | 255 / 232 (ar 113, en 119) |
| Extraction status | 196 complete, 35 partial (no usable render), 1 failed |
| Identifier occurrences / distinct keys | 1,726 / 1,576 |
| `no_record` occurrences | 1,637 |
| `matched` occurrences | 41 (31 retracted, 10 expression of concern) |
| `notice_only` occurrences | 43: 32 `marker_target`, 10 `primary_citation_field`, 1 `identifier_link` |
| Articles with any non-`no_record` key | 16 (en 12, ar 4) |
| Articles citing a retracted original in a primary field | 11 (en 7, ar 4) |
| Units with exactly one DOI and one PMID (primary) | 478: 454 no_record, 18 matched, 5 notice_only, **1 ambiguous_identity** |

Cases that matter for the design:

- **MMR vaccine** (en rev 1381772671): cites the Wakefield original (retracted) *and* the Lancet retraction notice
  `10.1016/s0140-6736(10)60175-4` as a primary citation. A DOI-lookup wrapper that matches any Retraction Watch DOI
  column would report the notice citation as a second retracted citation.
- **هاروكو أوبوكاتا** (ar rev 76190003, unit `un-00013`): DOI `10.1038/nature12969` with PMID `24476881`. The DOI
  alone is a direct `retracted` record (whose PMID is `24476891`); the PMID alone has no record; the pair is
  `ambiguous_identity`. A real **intra-citation contradiction**, invisible to per-identifier lookup.
- **BCAS3** (ar rev 76488293): `PMID_ROLE_COLLISION` on the cited original.
- Stage 01's three positive chains are already retained: MMR vaccine (en), Haruko Obokata (en 1372543632, ar
  76190003), GFAJ-1 (en 1374726997). **The vertical slice needs no new capture for its positive cases.**

Consequence [inference]: these 232 revisions are now Stage 04 design-exposed. They are the development set only;
the final evaluation must use revisions outside them and outside every Stage 03 exposure set (section 12).

---

## 3–4. Inherited-gap / upgrade audit and classification

Classes: **INT** integration improvement within Stage 04 · **MNT** maintenance defect · **SCI** scientific defect ·
**GOV** governance/contract defect · **DOC** documentation/evidence gap · **RES** accepted residual, unchanged.

| # | Finding | Evidence | Class | Action |
|---|---|---|---|---|
| G-01 | `test_accepted_contract_schemas_are_untouched` depends on commit `c3346d1`, reachable only through unmerged side branches | section 5 | MNT (Stage 03-owned file) | Owner decision D-2; maintenance transaction; do not touch now |
| G-02 | v1 investigation is paper-centric; an article investigation spans many papers | `investigation.schema.json` | INT | Stage-04-owned schema `$ref`ing v1 (MR-05); no v1 change |
| G-03 | v1 holds one status per paper; Stage 02 returns several events per paper | MR-05, FR §4.3 | INT | Events kept in Stage 04 schema |
| G-04 | No end-to-end contract from Stage 03 identifier to Stage 02 query | no importer of both [fact] | INT | Adapter + key-equality test |
| G-05 | DOI/PMID contradictions inside one citation are checked by neither stage | Obokata ar case | INT | Pair query rule P-2 (section 8) |
| G-06 | Notice citations and marker templates match RW notice columns | 43 `notice_only` | INT | Never attachments; separate classes |
| G-07 | `lookup()` opens SQLite per call | `query.py` | INT | One `Index` per investigation |
| G-08 | `Index(str)` raises `AttributeError`, not `IndexUnavailable` | probe traceback [fact] | RES (typed `Path` API, mypy-checked) | Adapter passes `Path`; no Stage 02 change |
| G-09 | Full RW snapshot cannot be committed; CI has no full index | MR-25, Stage 02 fixtures | DOC | Stage 04 attributed ≤ 120-row subset fixture, same boundary test |
| G-10 | Index format binds policy version; a rebuilt index can differ | `INDEX_FORMAT_MISMATCH` | INT | Memory records snapshot, policy, artifact digest; replay flags STALE |
| G-11 | Extraction depends on engine, profile and config digests | extraction doc | INT | Recorded; replay flags STALE |
| G-12 | No structured observability in either engine beyond issues | code | INT | The investigation journal is the audit/observability log |
| G-13 | `verified_fact` scope is the source record, not truth | Stage 02 rule 9 | RES | Carry `basis.scope`; never say "false claim" |
| G-14 | Bridged evidence withheld (R-029), PMID role collision (R-031) | RISKS.md | RES | Become `unresolved` claims |
| G-15 | English unit-kind precision interval to 0.929 (R-036) | Stage 03 | RES | Detection keys on identifier role, not unit kind |
| G-16 | Support boundaries (R-035): e.g. publisher URLs without `/doi/` not extracted | Stage 03 | RES | Counted as declared false-negative sources |
| G-17 | Arabic warning detection untested; one Arabic RW record | Stage 02/03 | RES | Stage 04 does not interpret markers (Stage 05) |
| G-18 | Census frame is link-bearing only; conditioning on link detectability | Stage 01 | RES | Used as recall reference with that caveat |
| G-19 | Stage 04 registry definition has no owned paths, one gate, four suites | registry [fact] | GOV | Refine before implementation (D-1) |
| G-20 | No CLI command edits a stage definition; prior stages hand-edited it (`36696b3`, `b93314d`) | `cli.py` [fact] | GOV | Owner decision D-1 |
| G-21 | Unused list-defined references are not uses (R-035) | Stage 03 | INT | Claim `UNUSED_DEFINITION`, not an attachment |
| G-22 | Retained Stage 03 bundles now exposed to Stage 04 design | this probe | DOC | Dev-only; fresh holdout |
| G-23 | Creation time and investigation id are non-deterministic | v1 contract | INT | Excluded from content digest (MR-21) |
| G-24 | Other skips: ECMA tests need Node (fail in CI if absent), `/proc` tests skip off Linux | tests | RES | Correct behaviour; none silently skipped in CI |

No scientific defect (SCI) in an accepted stage was found. Nothing above requires reopening a stage. Only G-01 touches
accepted-stage-owned material; its correction path is section 5.

---

## 5. The skipped accepted-contract test

**Facts.**

- `tests/stage03/test_wiki_properties.py:246` (the test) runs `git diff --name-only c3346d1 -- schemas/contracts` and skips
  when git fails.
- `c3346d1` = "Stage 03: record owner authorization and start work" (2026-10-28, parent `94ac4f8`), on the PR #5
  lineage (`claude/beautiful-planck-fm0pya`, `claude/project-thread-o4amfd`, `codex/stage03-d036-safe-continuation`).
  The test came from `73da40a` on that lineage and reached `main` through the clean-tree commit `b93314d`, whose
  history does not contain `c3346d1`.
- `schemas/contracts` has the same tree (`9b4c3a00`) at Stage 00's accepted `0c21182`, at `c3346d1` and at HEAD:
  no contract changed.
- Fresh clone of the Stage 04 branch: **2050 passed, 1 skipped**. After fetching the side branches: **2051 passed**.
- CI checks out with `fetch-depth: 0`, which fetches every branch, so `c3346d1` is reachable there while those
  branches exist. A skip makes the report partial (`TEST_EVIDENCE_PARTIAL`), and CI fails on that.
- `citerift-gov check` separately compares Stage 00-owned `schemas/contracts/v1` with `0c21182`
  (`VERIFICATION_STALE`), so v1 is protected independently.

**Assessment.** Both. The reference is stale for the clean-history lineage (1), and the protection is not exercised in
any clone without those side branches (2). Its scope beyond v1 (`schemas/contracts/` outside `v1/`, such as a future
`v2/`) is protected only by this test.

**Hidden dependency** [inference, not observed]: deleting PR #5's branch, `claude/project-thread-o4amfd` and the Codex
branch would make CI red on `main` and on every pull request, and a Stage 04 verification report made in a clone
without them would be rejected.

**Governance path.** The file is a Stage 03 owned path; Stage 03 is accepted. A change makes Stage 03
`VERIFICATION_STALE` unless covered by an enhancement amendment. Because the change repairs a test that the
recording report must pass in a fresh clone, the route is a **maintenance transaction** (D-024, as A-00-002):
`citerift-gov maintenance prepare 03 --candidate <sha> --path tests/stage03/test_wiki_properties.py --owner-ref <owner
message> …`, validate the complete suite on Python 3.12 and 3.13 at the candidate, then `maintenance finalize`.
Proposed patch [proposal]: replace the short `c3346d1` with Stage 00's accepted revision
`0c21182e5871f772c3a76c75a1217c7641a63bbb` (an ancestor of main with the identical tree). Interim measure needing no
change: keep the three side branches on GitHub, and fetch them before producing any verification report.

---

## 6. Stage 04 scope and non-scope

**Sources of scope.** Master Plan v1.0 Stage 04; registry gate 04-A; Architecture v1.1 (Workflow Controller and
Investigation Memory, Stage 04 initial); `MAESTRO_DESIGN_BRIEF.md` section 11; the owner's addendum; Stage 02/03
handoff requirements.

**In scope.**

1. Detection Engine: match extracted citations against verified retraction records, with uncertainty and provenance.
2. Investigation Workflow Controller v0: fixed plan, explicit states, retries, resume (MR-01–MR-17b).
3. Investigation Memory v0: durable, append-only, replayable (MR-11–MR-13, addendum).
4. Article-subject investigations for one edition at a time, `en` and `ar`, at a pinned revision (from a retained
   bundle or a new read-only capture through Stage 03).
5. A Stage-04-owned report schema embedding v1 assertions, plus a v1 investigation record per detected paper.
6. CLI `citerift-investigate` (`run`, `resume`, `replay`, `verify`, `show`).
7. The vertical slice, a fresh evaluation, the seven stage documents, a measured creative contribution.

**Out of scope.** Citation context and existing-notice interpretation (05); AI (06); cross-language comparison,
timelines, history, API, cancellation, edition snapshots MR-26 (07); UI (08); DOI-subject discovery of citing
articles (needs search clients Stage 03 does not have; proposed for 07, decision D-4); fuzzy title matching; live
Crossref; any Wikipedia edit; any change to Stages 00–03.

---

## 7. Gate-by-gate requirements and evidence matrix [proposal]

Gate 04-A stays as the Master Plan wording. 04-B to 04-J refine it (GOVERNANCE.md: refined when the specification is
approved, before implementation). Suites: `unit, integration, negative, regression, reproducibility, security,
contracts, simulation`.

| Gate | Requirement | Input → output | Invariants | Failure behaviour | Tests | Acceptance criterion | Evidence artifact |
|---|---|---|---|---|---|---|---|
| 04-A | A real documented investigation succeeds end-to-end, with negative and failure-case tests | pinned article → final report + journal | report validates; every claim traces to a Stage 02 row hash and a Stage 03 anchor | never a negative from a failure | vertical slice VS-1…VS-9 | all VS cases pass on real retained data | `evidence/vertical-slice/` journals, reports, replay logs |
| 04-B | Contracts | report, claims, journal records | Stage 04 schemas `$ref` v1 by URN; v1 unchanged | schema-invalid output is a terminal step failure | schema + semantic tests; v1 projections validate | 0 invalid outputs; `schemas/contracts` diff empty | schema test report |
| 04-C | Detection semantics | candidates + lookups → claims | decision table total and deterministic; no "not retracted" value anywhere | ambiguity → `unresolved`, never positive | table tests, property tests, reference-model differential, NC-01…NC-04 | 0 differences against the independent reference model on all dev units | differential report |
| 04-D | Memory and controller correctness | journal ↔ state | I-1…I-12 (section 21) | crash/partial write fails safe | fault injection at every step boundary and mid-write | identical final content digest after every injected crash | fault-injection report |
| 04-E | Replay and staleness | journal + inputs → replay verdict | same inputs → byte-identical content | changed bundle/index/engine/schema → `STALE` | replay tests with each input mutated | 100 % mutations detected; 0 false STALE on unchanged | replay report |
| 04-F | Scientific evaluation on a fresh holdout | annotated sample → metrics | no tuning after freeze | insufficient denominator = not passed | single locked prediction run | section 12.3 | `evaluation/` campaign record |
| 04-G | Failure containment | injected 429/503/timeouts, missing index, failed extraction | failures never become negatives or success | `partial`/`failed` with limitations | AT-04, AT-12 analogues | 0 negative findings from failures | failure-case report |
| 04-H | Security and boundaries | code, runtime | no `citerift.governance` import; no network outside Stage 03 fetch; path safety | refuse, never fall back | import, network-allowlist, path tests; secret scan | all pass | test report, scan log |
| 04-I | Reproducibility and packaging | clean checkout | lock unchanged (no new dependency); complete reports 3.12/3.13; CI | — | full matrix | all pass, CI success | `test-report.json`, CI run |
| 04-J | Creative contribution measured | holdout | — | reported honestly if it fails | baseline comparison | section 13 | `CREATIVE_DIFFERENTIATION_REVIEW.md` |

---

## 8. Detection Engine scientific design

**Principle.** Detection is deterministic composition of two accepted engines. It contains **no numeric threshold and
no learned or probabilistic component**. Uncertainty is categorical (v1 statuses plus reason codes); there is no
confidence score, because nothing is calibrated to give one meaning.

### 8.1 Candidate generation

For each citation unit `u` in a container with at least one bound use, the **candidate keys** are the valid keys of
identifiers in `u` whose role is `primary_citation_field` or `identifier_link`. Identifiers with other roles are
recorded as observations: `marker_target` (existing wikitext marker), `textual_mention`, `labeled_reference_text`,
`unresolved`. Units in containers with no bound use become `UNUSED_DEFINITION` observations.

### 8.2 Queries

- Q-1: each candidate key alone (`gather(doi=k)` or `gather(pmid=k)`).
- Q-2: the pair `(d, p)` when the unit has exactly one candidate DOI and one candidate PMID.
- More than one candidate key of one scheme in a unit: no pair query; flag `CO_REPORTED_MULTIPLE` (never merged).

### 8.3 Decision table (first rule that applies, per unit) [proposal]

| Rule | Condition | Claim class | Epistemic status |
|---|---|---|---|
| P-0 | extraction for the unit's region failed, or index unavailable | `UNAVAILABLE` | `unavailable` |
| P-1 | any candidate boundary ambiguous, or role `unresolved` on a would-be candidate | `UNRESOLVED_IDENTIFIER` | `uncertain` |
| P-2 | Q-2 is `ambiguous_identity` | `CONTRADICTION_IN_CITATION` (both keys and both results kept) | `conflicting` (alternatives) or `uncertain` |
| P-3 | any Q-1 projection is `conflicting` | `CONTRADICTION_IN_SOURCES` | `conflicting` |
| P-4 | any Q-1 is `ambiguous_identity`, bridged-only support, or `PMID_ROLE_COLLISION` on a PMID-only unit | `UNRESOLVED_IDENTITY` | `uncertain` |
| P-5 | a Q-1 is `matched` with `verified_fact retracted` from direct support, and no rule above applied | `RETRACTED_WORK_CITED` | `verified_fact` (scope: checked sources) |
| P-6 | as P-5 with `expression_of_concern`, `correction` or `reinstated` | `CONCERN_CITED`, `CORRECTION_CITED`, `REINSTATED_WORK_CITED` | `verified_fact` |
| P-7 | Q-1 `matched` but projection `uncertain` (mixed effect, unlinked reinstatement, coverage gap) | `UNRESOLVED_STATUS` | `uncertain` |
| P-8 | every Q-1 is `notice_only` | `NOTICE_CITED` (not an attachment to the retracted work) | observation |
| P-9 | every Q-1 is `no_record` | `NOT_FOUND_IN_CHECKED_SOURCES` | `uncertain`, value `not_found_in_checked_sources` |
| P-10 | unit has no candidate key | `NO_IDENTIFIER` (out of detection scope) | no claim |

Where keys of one unit disagree (one `matched`, another `no_record`) without an `ambiguous_identity` pair result,
P-5 applies and the disagreement is listed in the claim (`KEY_RESULTS_DIFFER`). Article-level summaries count claims
by class and never derive a negative from absent claims.

### 8.4 Thresholds and decision rules

The only "thresholds" are the evaluation gates (section 12.3). Each decision rule has a rationale, an evaluation and a
failure criterion:

| Rule | Rationale | Evaluation | Failure criterion |
|---|---|---|---|
| Roles limited to primary and link | notices, markers and mentions are not citations of the work (CP-3, Stage 03 G3 role agreement) | annotators label attachment truth per flagged unit | any false `RETRACTED_WORK_CITED` caused by role choice |
| Pair contradiction P-2 | a citation naming two works cannot be attached to either without a source | dev case Obokata ar; holdout count | a P-2 case that annotators judge unambiguous and correctly attached by a single key is reported as a cost, not hidden |
| Precedence contradiction > unresolved > positive | an unresolved contradiction must not look resolved (addendum) | property test: adding a contradicting key never upgrades a claim | any upgrade |
| Notice ≠ original (P-8) | NC-04; MMR vaccine case | holdout | any notice counted as an attachment |

**Sensitivity analysis** (descriptive, run once on dev and once on holdout, never used to tune): counts under variants
(a) `identifier_link` excluded, (b) P-2 disabled, (c) `labeled_reference_text` included.

### 8.5 Provenance and explainability

Every claim stores: Stage 03 bundle digest, extraction digest, revision id and SHA-1, unit id, identifier byte anchors
and their raw text hash; Stage 02 snapshot id, policy version, artifact digest, query keys, `evidence_digest`, event
ids with `row_sha256`; the rule id that fired and every reason code. Explanation is the rule id plus the evidence
chain, rendered as text by a template, not generated.

### 8.6 False-positive and false-negative controls

- FP: roles, pair query, notice separation, boundary and identity abstention, bound-use requirement, direct-support
  requirement.
- FN: every occurrence is looked up (no sampling); `no_record` is never "not retracted"; misses are attributed to a
  declared upstream boundary (R-035, Stage 03 abstentions) or counted as Stage 04 defects.

### 8.7 Leakage control

Design and development: the 232 retained revisions and the Stage 01 purposive cases. The decision table is frozen
(commit and hash) before the holdout is drawn; the holdout is drawn by a committed seed after the freeze; one
prediction run; no change after it.

---

## 9. Vertical-slice design

Each case runs through the real Stage 03 extraction and the real Stage 02 index, with Investigation Memory and the
controller. CI runs them on retained bundles and an attributed Retraction Watch field subset; the full-index run is
retained as real-data evidence.

| Case | Input (retained unless noted) | Expected |
|---|---|---|
| VS-1 positive | MMR vaccine, en 1381772671 | Wakefield original `RETRACTED_WORK_CITED`; Lancet notice `NOTICE_CITED`; marker observed |
| VS-2 positive, Arabic | Obokata, ar 76190003 | nature12968 `RETRACTED_WORK_CITED`; nature12969 + PMID 24476881 `CONTRADICTION_IN_CITATION` |
| VS-3 positive, English | Obokata en 1372543632; GFAJ-1 en 1374726997 | retracted originals attached; notice citations separate |
| VS-4 concern ≠ retraction | Culturomics or Supriyo v. Union of India (EoC) | `CONCERN_CITED`, never retracted (NC-01) |
| VS-5 identity issue | BCAS3, ar 76488293 | `PMID_ROLE_COLLISION` carried; claim per P-4/P-5 as specified |
| VS-6 negative | a retained article with only `no_record` keys | `NOT_FOUND_IN_CHECKED_SOURCES`, never negative |
| VS-7 malformed | corrupted bundle, invalid revision request, schema-invalid input | `FAILED` with code; no claim |
| VS-8 upstream unavailable | index missing / format mismatch; injected 429 then deferral | `BLOCKED` or `partial` with limitations; no negative |
| VS-9 interrupted | VS-1 killed after LOOKUP succeeded, then `resume` | EXTRACT and LOOKUP not repeated (journal shows no new step_started for them); identical content digest |
| VS-10 replay | each completed VS case | byte-identical content; STALE when bundle, index, engine or schema changes |

---

## 10. Architecture and data flow

```
request ──▶ Controller (src/citerift/investigation/controller.py)
              │ fixed plan: VALIDATE → ACQUIRE → EXTRACT → NORMALIZE → LOOKUP → DETECT → ASSEMBLE → VERIFY
              ▼
           Journal (Investigation Memory) ◀── every step writes observations/evidence/claims, then its terminal record
              │
   ACQUIRE/EXTRACT ─▶ adapters/wiki.py ─▶ citerift.wiki (capture_revision, extract_bundle, verify_bundle)
   LOOKUP          ─▶ adapters/retraction.py ─▶ citerift.retraction.query (Index, gather, render)
   DETECT          ─▶ detect.py (pure decision table)
   ASSEMBLE        ─▶ report.py (Stage 04 report + v1 projections)
   VERIFY          ─▶ verify.py (schemas, invariants, replay of DETECT from journal, Stage 03 verify)
```

One process, standard library plus the existing `jsonschema`; **no new dependency**, no service, no queue, no agent
framework. The only network path stays Stage 03's `fetch.py`, used only in ACQUIRE for a new capture.

---

## 11. Failure-mode and threat analysis

| Id | Failure or threat | Effect if unhandled | Control | Test |
|---|---|---|---|---|
| F-01 | Notice DOI or marker counted as a retracted citation | false attachment | P-8, role filter | VS-1, NC-04 |
| F-02 | DOI and PMID of one citation name different works | false attachment | P-2 | VS-2 |
| F-03 | Missing record read as "not retracted" | false negative claim | P-9 only `uncertain`; schema forbids value | property test |
| F-04 | Failed step read as success | silent gap | completion invariants | fault injection |
| F-05 | Crash between blob write and journal record | orphan or lost work | write order; orphans ignored | crash tests |
| F-06 | Torn final journal line | corrupt state | tail quarantine with copy; mid-chain mismatch → `CORRUPT` | corruption tests |
| F-07 | Two runners on one investigation | duplicated or interleaved records | `flock` lock, `INVESTIGATION_BUSY` | concurrency test |
| F-08 | Index rebuilt with another policy | stale evidence | snapshot/policy/digest recorded; STALE | replay mutation |
| F-09 | Rate limiting (R-008) | long stalls | Stage 03 policy; `BLOCKED` with `not_before` | injected 429 |
| F-10 | Path traversal from titles | file overwrite | ids are hashes/UUIDs; no title paths; `O_NOFOLLOW` | path tests |
| F-11 | Untrusted wikitext/HTML | code execution | Stage 03 isolated worker; no eval | existing + import tests |
| F-12 | Product code importing governance | coupling | static import test (AT-07) | import test |
| F-13 | Hidden network use in detection | non-replayable results | network allowlist test (AT-08) | socket-block test |
| F-14 | Secrets in captured pages (Stage 03 found an AWS key id) | publication of a secret | secret scan before commit; withheld-file procedure | scan step |
| F-15 | Evaluation leakage | inflated metrics | freeze before draw; exposure exclusion | audit check |
| F-16 | Contradiction hidden by aggregation | false confidence | article summary counts classes; no roll-up to "clean" | property test |

---

## 12. Test and evaluation strategy

### 12.1 Fail-first verification matrix

| Layer | What | Fail-first evidence |
|---|---|---|
| Unit | decision table rows, adapters, journal codec, state machine | each test committed failing against a stub before the code |
| Property | determinism, monotonic precedence, no negative value, fold(journal) legal | seeded generators with the standard library `random` (Hypothesis is not a project dependency; none added) |
| Adversarial | malformed bundles, poisoned journals, duplicate keys, NaN, symlinks, huge inputs | negative suite |
| Integration | real Stage 03 extraction + real Stage 02 subset index | integration suite |
| End-to-end | VS-1 … VS-10 | vertical-slice suite |
| Regression | G-05 Obokata contradiction, G-06 notice, each defect found later | regression suite |
| Schema | Stage 04 schemas, v1 projections, journal records | contracts suite |
| Static | ruff, mypy strict | CI |
| Dependency | `uv lock --check`, `pip-audit` | CI |
| Replay | same inputs → byte-identical; mutations → STALE | reproducibility suite |
| Performance | warm investigation of a retained bundle ≤ 5 s p95; journal ≤ 10 MiB per article (measured extraction 0.19 s mean, lookups < 1 ms) | benchmark script |
| Scientific | fresh holdout, section 12.3 | campaign record |
| Security | import boundary, network allowlist, path safety, secret scan | security suite |
| Clean tree | complete report from a clean tree, CI `check-report` | CI |

### 12.2 Simulation

An independent reference model (`simulations/stage04/`) of the decision table and an exhaustive enumeration of the
controller's state space (every step × every outcome × crash points), written before the engine, compared
differentially.

### 12.3 Scientific evaluation [proposal]

- **Frame.** Arabic: Stage 01 census confirmed articles (157). English: Stage 01 English dump scan (745 articles).
  Excluded: Stage 03 exposure set (6,038 page ids), the 232 probe revisions, Stage 01 purposive pages.
- **Draw.** After the freeze, seeded and committed; 30 articles per language plus a reserve block of 10.
- **Capture.** Read-only through Stage 03, within ≤ 200 attempts and ≤ 100 MiB (Stage 03 used 208 attempts for 44).
- **Labels.** Independent annotators who never saw the engine output: for each unit with a candidate key, "does this
  reference cite the original work of the matched record, its notice, another work, or is it unclear". Locked before
  the prediction run, adjudicated on disagreement (Stage 03 procedure). Annotator type is decision D-3.
- **Metrics and gates.**
  - Attachment precision of `RETRACTED_WORK_CITED` and `CONCERN_CITED`: **0 false attachments** among at least
    **30 flagged units per language**. Rationale: with 0 errors in 30, the exact one-sided 95 % upper bound on the
    false-attachment rate is 9.5 % (rule of three ≈ 10 %); 59 units would be needed for 5 %. Fewer than 30 flagged
    units = not passed (reserve used first).
  - Census-referenced recall: every census pair present at the captured revision is either detected or explained
    by a declared upstream boundary; **0 misses attributable to Stage 04 logic**. No numeric target, because
    Stage 04 cannot exceed Stage 03 identifier recall.
  - Hazards: 0 notice citations, 0 marker targets and 0 contradiction cases counted as attachments.
  - Structural: 0 "not retracted" values; 0 claims without a complete evidence chain (exhaustive, not sampled).
- **Interval reporting.** Clopper–Pearson 95 % per language for every rate.

---

## 13. Creative differentiation review [proposal]

**Problem.** A DOI-lookup wrapper over Retraction Watch confuses notices with papers, hides contradictions inside a
citation and turns absence into reassurance.

**Mechanism.** The *Verifiable Citation Verdict*: each verdict is a typed claim with (1) a byte-exact anchor in a
pinned revision, (2) the Retraction Watch row hashes and snapshot digest behind it, (3) the decision rule that fired,
and (4) an abstention-first precedence (contradiction > unresolved > positive). It is replayable offline, and the pair
query cross-examines the identifiers of one citation against each other.

**Prior art to check (primary pages, before claims).** Retraction Tracker for Wikipedia (English, daily,
sentence-level, AI readings; Stage 01), RetractionBot on English Wikipedia, Zotero's Retraction Watch integration,
Crossmark. Absence from a reviewed page is not global uniqueness.

**Measured difference.** On the holdout, false attachments of a naive baseline (flag a unit if any key appears in any
Retraction Watch identifier column) versus the engine, with intervals. Development preview [fact]: in the 232 retained
revisions the baseline would count 43 notice or marker occurrences, 1 marker matched to an expression of concern and
1 intra-citation contradiction as attachments.

**Cost.** One pair query per unit; no dependency.

**Failure modes.** If the holdout has no contradiction or notice cases, the contribution is reported as untested there.

---

## 14. Proposed implementation sequence

| Step | Work | Depends on | Exit evidence |
|---|---|---|---|
| 0 | Owner decisions D-1 … D-5 | — | owner references |
| 1 | Registry definition of Stage 04 (owned paths, gates 04-B…04-J, suites); SPECIFICATION, MATHEMATICAL_MODEL, RISK_ANALYSIS frozen | 0 | commit, `citerift-gov check` 0 errors |
| 2 | Simulation: reference decision model, exhaustive state enumeration | 1 | SIMULATION_REPORT |
| 3 | Schemas `schemas/investigation/v1/` | 1 | contract tests |
| 4 | Journal (memory) with fault injection | 3 | fail-first + pass |
| 5 | State machine and controller over fake adapters (unit only) | 4 | invariant tests |
| 6 | Real adapters to Stage 02/03; attributed RW subset fixture | 5 | integration tests |
| 7 | Detection table; dev measurements on 232 revisions | 6 | dev report |
| 8 | Report assembly, v1 projections, CLI | 7 | schema tests |
| 9 | Vertical slice VS-1 … VS-10 incl. interrupted run | 8 | evidence/vertical-slice |
| 10 | Review (independent pass), fixes, **freeze** | 9 | freeze commit |
| 11 | Holdout draw, capture, labels locked, one prediction run, scoring, adjudication | 10 | campaign record |
| 12 | Full matrix both Pythons, CI, handoff, verification record; PR unmerged | 11 | VERIFIED — AWAITING OWNER ACCEPTANCE |

---

## 15. Decision points requiring the owner

| Id | Decision | Options | Recommendation |
|---|---|---|---|
| D-1 | Stage 04 definition in the registry (owned paths, refined gates, suites) needs a hand edit: no `citerift-gov` command exists, and the authorization instruction said not to edit the registry by hand | (a) approve one reviewed hand edit of Stage 04's definition only, checked by `citerift-gov check`; (b) first add a CLI command (Stage 00 change, needs an amendment) | (a), as Stages 02 and 03 did |
| D-2 | Skipped contract test (section 5) | (a) maintenance transaction on Stage 03 now; (b) keep the side branches and defer | (a) before Stage 04 verification; meanwhile do not delete the branches |
| D-3 | Holdout annotators | (a) isolated Claude Sonnet instances + Haiku adjudication (Stage 03 procedure); (b) owner or human annotators | (a) for the deadline, labelled "AI labels, not human gold" |
| D-4 | Subject type | article-first only in Stage 04; DOI-subject discovery in Stage 07 | article-first |
| D-5 | Evaluation scale and live capture | 30 + 10 reserve articles per language, read-only capture ≤ 200 attempts | as proposed; smaller only with a stated weaker bound |

---

## 16. Files and modules expected

New (Stage 04 owned paths, proposed): `src/citerift/investigation/` (`__init__`, `model`, `journal`, `controller`,
`steps`, `adapters/wiki`, `adapters/retraction`, `detect`, `report`, `verify`, `schemas`, `cli`),
`schemas/investigation/v1/` (`request`, `journal-record`, `claim`, `report`), `tests/stage04/` (+ attributed fixture
subset), `simulations/stage04/`, `docs/verification/stage-04/` (seven documents, evidence, evaluation).

Changed (not owned by any stage): `pyproject.toml` (script `citerift-investigate`), `DECISIONS.md` (D-039 Stage 04
design), `RISKS.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/data-contracts.md` (pointer to Stage 04 schemas),
registry and `PROJECT_STATUS.md` via `citerift-gov` (and D-1). **Not changed:** anything owned by Stages 00–03
(except D-2 through its transaction), `uv.lock`.

---

## 17. Risks to deadline, validity and reliability

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Deadline (R-010): 12 days remain for Stages 04–09 | high | high | Stage 04 timeboxed to about 3 days; no new dependency; reuse retained bundles; evaluation in one pass |
| Too few flagged units in the holdout | medium | gate not passed | positive-enriched frames; reserve block |
| AI-only labels | high | weaker independence | lock before prediction; adjudication; disclose |
| Census frame bias (link-bearing) | certain | recall is conditional | stated in every result |
| Rate limits during capture | medium | delay | Stage 03 policy, small sample |
| Contradiction rule removes true attachments | low | recall cost | reported as a cost, sensitivity variant (b) |
| Side branches deleted before D-2 | low | CI red, verification blocked | keep branches; D-2 |
| Scope creep into 05/07 | medium | delay | non-scope list; markers recorded, not interpreted |

---

## 18. Recommendation

**PROCEED WITH CONDITIONS.** Conditions: owner decisions D-1 to D-5; the side branches stay until D-2 is done; the
detection table and gates are frozen before any holdout is drawn. No blocker prevents the plan; the accepted engines
reproduce (index digests match) and already connect on real data.

---

## 19. Investigation Memory: data model and invariants [proposal]

**Store.** One directory per investigation under a configurable root outside the repository (MR-13), named by the
investigation UUID: `journal.jsonl` (append-only, hash-chained), `blobs/<sha256>` (content-addressed canonical JSON),
`lock`. Retained evidence for the stage is a verified copy in `docs/verification/stage-04/evidence/`.

**Record envelope.** `schema` (URN), `schema_version`, `seq`, `prev` (SHA-256 of the previous record), `kind`, `step`,
`attempt`, `at` (UTC, excluded from the content digest), `payload`, `digest`.

**Layers and record kinds** (references point only downward):

| Layer | Kinds | Key fields |
|---|---|---|
| Lifecycle | `investigation_created`, `input_validated`, `investigation_finalized`, `verification_recorded` | request, config and engine digests; outcome; report digest |
| Execution | `step_started`, `step_succeeded`, `step_failed` (`retryable`/`terminal`, code), `step_deferred` (`not_before`), `step_interrupted` | step key, input and output digests |
| Raw observation | `observation_recorded` | kind (`bundle`, `extraction`, `lookup`), blob digest, source ref |
| Normalized evidence | `evidence_recorded` | evidence id, observation id + JSON pointer, normalized key, role |
| Claim/hypothesis | `claim_recorded` | claim id, class, epistemic status, supporting and contradicting evidence ids, rule id, reason codes |
| Decision | `decision_recorded` | claim id, decision, rationale codes |
| Unresolved | `question_opened`/`question_closed`, `blocker_opened`/`blocker_resolved` | what is missing and why |
| History | `claim_superseded` | old id, new id, reason |

**Stable ids.** Observation = SHA-256 of canonical content; evidence = hash(observation, pointer); claim =
hash(class, revision id, unit anchor, work key, engine versions). Dedup follows from content addressing.

**Contradiction.** A claim with status `conflicting` holds at least two alternatives, each with evidence (v1 rule); a
contradiction between keys of one citation lists both evidence ids.

**Supersession.** Nothing is deleted; the current state is the fold of the journal, with superseded claims excluded
from the current view but kept and linked.

**Migration.** A reader accepts the current and previous journal version; migration writes a new investigation whose
`investigation_created` cites the source journal digest. No in-place rewrite.

**Corruption.** On open the hash chain is verified. A torn final line is copied to `journal.torn.<seq>` and dropped
(Copy → Verify → Preserve); any mid-chain mismatch makes the investigation `CORRUPT` (read-only).

**Answers on resume.** Complete = steps with `step_succeeded` for the current step key; unresolved = open questions,
blockers, `uncertain`/`conflicting` claims; changed = step keys that differ from recorded ones; support = the evidence
chain of each current claim; not to repeat = succeeded steps with unchanged keys.

---

## 20. Investigation Workflow Controller: state machine [proposal]

**Two machines, deliberately separate.** The owner's list mixes lifecycle (CREATED, BLOCKED, FAILED…) with epistemic
outcomes (CONTRADICTION_DETECTED, ABSTAINED, NEEDS_MORE_EVIDENCE). One article yields many claims with different
outcomes, so outcomes belong to claims, not to the investigation. The lifecycle stays small:

| From | To | Precondition | Postcondition |
|---|---|---|---|
| — | CREATED | request recorded | journal exists, lock held |
| CREATED | INPUT_VALIDATED | request valid (wiki ∈ {en, ar}, revision or bundle, index present) | `input_validated` |
| CREATED | FAILED | request invalid | `INPUT_INVALID` |
| INPUT_VALIDATED | RUNNING | — | first step pending |
| RUNNING | BLOCKED | a step deferred (Retry-After, index busy) | `not_before` recorded |
| BLOCKED | RUNNING | time reached or blocker resolved | — |
| RUNNING | DETECTED | ACQUIRE…DETECT succeeded | claims recorded |
| RUNNING | FAILED | a required step `failed_terminal` or retries exhausted | limitations recorded |
| DETECTED | VERIFIED | ASSEMBLE and VERIFY succeeded | report digest recorded |
| DETECTED | FAILED | verification failed | — |
| VERIFIED | COMPLETE | completion invariants hold | outcome `completed` or `partial` |

Step machine (per step): `pending → running → succeeded | failed_retryable | failed_terminal | deferred`;
`failed_retryable → running` while attempts ≤ 3; `deferred → running` after `not_before`; `skipped` only for an
optional component (render-dependent observations) and never for a required step.

Mapping of the owner's names: NEEDS_MORE_EVIDENCE, CONTRADICTION_DETECTED and ABSTAINED are claim classes
(`UNRESOLVED_*`, `CONTRADICTION_*`, `uncertain`) and open questions; EVIDENCE_DISCOVERY and EVIDENCE_NORMALIZED are
the ACQUIRE/EXTRACT and NORMALIZE steps; FAILED_RETRYABLE is a step state; FAILED_TERMINAL is FAILED.

**Retry.** Network retries stay inside Stage 03's policy; controller retries only `retryable` codes (Stage 03 issue
catalog, index busy), at most 3 attempts. Deterministic steps failing are terminal (a retry would repeat the result).

**Idempotency.** Step key = hash(step, input digests, engine and schema versions). A succeeded step with the same key
is never re-run.

**Observability.** The journal is the log: every transition, attempt, code and digest. `show` prints it.

**Completion invariants.** COMPLETE only if every required step succeeded, the report validates, verification passed
and every claim has a complete evidence chain; outcome `partial` iff an optional component was skipped or any claim is
`unavailable`.

---

## 21. Memory/workflow consistency model

The controller keeps **no state of its own**: its state is the fold of the journal. Divergence is therefore
impossible by construction, and each invariant is checked on every open and in tests.

| Inv | Statement |
|---|---|
| I-1 | Every `step_succeeded` names output digests whose blobs exist and hash correctly |
| I-2 | Write order: blob (temp, fsync, rename) → record (append, fsync); a record never precedes its data |
| I-3 | The fold of the journal is a legal path of both state machines (like Stage 00 invariant 5) |
| I-4 | Hash chain intact; `seq` contiguous |
| I-5 | Claims reference existing evidence; evidence references existing observations |
| I-6 | No claim moves to a stronger status without new evidence (no silent resolution) |
| I-7 | `uncertain`, `unavailable` and `not_found_in_checked_sources` never become a negative value |
| I-8 | A `step_started` without a terminal record is reported as interrupted on resume |
| I-9 | Superseded claims stay reachable from their successor |
| I-10 | Replay recomputes step keys; a difference is STALE, never silently reused |
| I-11 | At most one writer (lock); a second gets `INVESTIGATION_BUSY` |
| I-12 | COMPLETE implies the completion invariants of section 20 |

---

## 22. Resume, replay, idempotency and crash recovery

- **Resume.** Take the lock, verify the chain, fold, record `step_interrupted` for any open attempt, recompute step
  keys, skip succeeded steps with equal keys, run the rest.
- **Replay.** Re-run every pure step (NORMALIZE, DETECT, ASSEMBLE) from recorded observations and compare digests;
  re-verify the bundle with Stage 03 `verify`/`replay` and the index digest; report `reproduced`, `differs` (with
  the first differing record) or `stale` (input, engine or schema changed).
- **Crash recovery.** Orphan blobs without a record are ignored (and reported); a torn tail is quarantined; nothing
  is guessed.
- **Duplicate execution.** `flock` on the lock file, released by the kernel when a process dies.

---

## 23. Failure-injection verification plan

| Injection | Points | Expected |
|---|---|---|
| Process kill | before and after each blob write, each record append, each fsync, at every step boundary (8 steps) | resume gives the same content digest; no step with an unchanged key re-run |
| Torn write | last record truncated at every byte offset of one record | tail quarantined, run resumes |
| Bit flip | one byte in a middle record, in a blob | `CORRUPT` / blob mismatch reported; no repair |
| Duplicate runner | second process on the same investigation | `INVESTIGATION_BUSY` |
| Upstream faults | 429 with Retry-After, 503, timeout, HTTP 200 error body, malformed JSON (through the Stage 03 transport hook) | `BLOCKED`/`partial`, limitations, no negative |
| Index faults | missing, wrong policy version, unreadable | `unavailable` claims or `FAILED`, never `not_found` |
| Extraction faults | failed status, worker timeout | step failure with Stage 03 code |
| Disk full | `ENOSPC` on blob and on record | step failure, journal consistent |
| Schema change | journal of the previous version | read or migrate; never misread |

---

## 24. Interfaces among the components [proposal]

```python
# adapters/wiki.py  (Stage 03, unchanged API)
def acquire(req: AcquireRequest, policy: FetchPolicy | None) -> BundleRef      # capture_revision or retained bundle + verify_bundle
def extract(bundle: BundleRef) -> ExtractionDoc                                 # extract_bundle(isolated=True)

# adapters/retraction.py  (Stage 02, unchanged API)
class RetractionSource:                                                        # wraps one Index(Path)
    def identity(self) -> IndexIdentity                                         # snapshot_id, policy_version, artifact digest
    def query(self, doi: str | None, pmid: str | None) -> LookupResult         # render(gather(...)) dict

# detect.py  (pure)
def candidates(doc: ExtractionDoc) -> list[UnitCandidates]
def decide(units: list[UnitCandidates], results: Mapping[QueryKey, LookupResult], policy: DetectionPolicy) -> list[Claim]

# journal.py  (Investigation Memory)
class Journal:
    @classmethod
    def create(cls, root: Path, request: Request) -> "Journal"; @classmethod
    def open(cls, root: Path, inv_id: UUID) -> "Journal"
    def put_blob(self, obj: JSON) -> Digest; def get_blob(self, d: Digest) -> JSON
    def append(self, kind: RecordKind, **payload) -> Record                    # validated against the state machine first
    def fold(self) -> InvestigationState

# controller.py
def run(req: Request, *, memory_root: Path, index: Path) -> Outcome
def resume(inv_id: UUID, *, memory_root: Path, index: Path) -> Outcome
def replay(inv_id: UUID, *, memory_root: Path, index: Path) -> ReplayReport
```

Detection never touches the journal; the controller is the only writer. Adapters never write memory.

---

## 25. Reusing Stage 00 governance concepts

**Reuse the patterns, not the code.** Safe and useful: an explicit enum of states with an edge table as data; every
write applied to a copy and checked before it is made; history replay must equal recorded state; canonical JSON and
atomic writes; stable upper-case problem codes (`Finding` convention).

**Do not import or share `citerift.governance`.** Reasons: `docs/architecture.md` and MR-01 forbid it; governance is a
Stage 00 owned path (sharing would need an amendment); its semantics (owner actor, `owner_ref`, single active stage)
do not apply to investigations; coupling would let product runs affect, or be blocked by, project governance state.
The cost is about a hundred lines of similar code in Stage 04, accepted. A static test enforces the boundary (AT-07).

---

*Report status line for the owner:* this is a plan, not a stage result. Final verdict of this planning task: see the
thread reply.
