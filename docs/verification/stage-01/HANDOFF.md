# Stage 01 Handoff: Independent Feasibility Investigation

## Stage and status

- Stage: 01, Independent Feasibility Investigation. Executor role:
  `external-agent`, filled by a Claude Code session in a separate project
  thread under the owner's directive of 2026-10-26
  (`cmsg_018VCB51nDHP6HXmLU4ea5yPHoNtmrTEksWGzn64yEgVJc`). Independence is
  procedural, not organizational (FEASIBILITY_REPORT.md §2).
- Research protocol fixed and pushed before any Wikipedia query
  (PROTOCOL.md, commit `c26d2d9`, which also recorded `IN_PROGRESS`).
- First evidence revision `562fe1a`, verified on 2026-10-27 and then
  returned to `IN_PROGRESS` the same day for the owner-requested corrective
  pass (directive `cmsg_018VCB51nDHP6HXmLU4ea5yPBWBK4PLfVSRHeA5DdXjWLz`;
  FEASIBILITY_REPORT.md §15).
- Second evidence revision `32712fa`, verified on 2026-10-27 and returned to
  `IN_PROGRESS` the same day, before acceptance, for the owner-approved
  strengthening pass (message
  `cmsg_018VCB51nDHP6HXmLU4ea5yPS6zrHggGn25MJPgeq5XsHC`; FEASIBILITY_REPORT.md
  §16).
- Current evidence revision: `85da719ac43fc46170310b225c9190b63a046df8`, recorded as the implementation
  revision (`IMPLEMENTED_NOT_VERIFIED`). This package is the evidence for
  the transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE`.
- The stage is **not** accepted. Acceptance is the owner's. No later stage is
  authorized or started.
- The registry notes that an earlier external Stage 01 investigation was
  reported to the owner but never supplied to the repository. This package
  does not use, predict or replace it; if it exists, reconciling the two is
  the owner's decision.

## Verified completed work

"Pass" means the evidence named was produced and inspected by the executor;
it does not mean the owner accepted it.

| Gate | Requirement | Result | Evidence |
|---|---|---|---|
| 01-A | Retraction data accessibility evidenced | pass | FEASIBILITY_REPORT.md §4; `data/rw_profile.json`; `data/purposive_lookup.json`; EVIDENCE_MANIFEST.json (events with `independent_confirmation`) |
| 01-B | Wikipedia citation discoverability evidenced | pass | FEASIBILITY_REPORT.md §5; `data/purposive_discovery.json`; `data/rate-limit/`; `tests/stage01/test_discovery_errors.py`, `data/run-logs/stage01_tests_pinned_85da719.json` (pins `tests/stage01/` by sha256) |
| 01-C | Verified positive and negative examples | pass | FEASIBILITY_REPORT.md §6; EVIDENCE_MANIFEST.json cases POS-01–03, NC-01, NC-01b, NC-02–04, U-01–03; `data/followups/nc2_absence_check_*.json`, `nc3_lookup.json` |
| 01-D | Initial cross-language feasibility evidenced | pass | FEASIBILITY_REPORT.md §7; `data/followups/crosswiki_*.json`, `render_check_*.json`, `timeline_*.json`, `ar_*.json`; `data/census/` (§16); `tests/stage01/test_crosswiki.py`, `test_render_check.py`, `test_census.py`, `data/run-logs/stage01_tests_pinned_85da719.json` (pins `tests/stage01/` by sha256) |
| 01-E | Coverage limitations documented | pass | FEASIBILITY_REPORT.md §8; `data/sample_S.json`; `data/sample_S_discovery.json`; `data/run-logs/sample_S_search_*.json`; `data/census/dump_vs_api_crosscheck.json` |
| 01-F | Source references and reproducible findings | pass | EVIDENCE_MANIFEST.json; `scripts/`; `tests/stage01/` and `data/run-logs/stage01_tests_pinned_85da719.json` (pins `tests/stage01/` by sha256); `data/verify_result.json`; `data/clean_reproduction.json`; FEASIBILITY_REPORT.md §9, §14 |
| 01-G | Critical blockers and recommendations stated | pass | FEASIBILITY_REPORT.md §12, §15; CREATIVE_FEASIBILITY.md; MAESTRO_DESIGN_BRIEF.md; ADVERSARIAL_REVIEW.md; `data/followups/prior_art_*.json` |

Main results (details and labels in FEASIBILITY_REPORT.md):

- **01-A:** pinned Retraction Watch snapshot (73,356 records) with original
  DOI, notice DOI, event type and date; 17 of 19 purposive events have a
  separate, resolving Crossref notice, but only 4 have a publisher link that
  confirms link and type (Crossref's Retraction Watch-sourced links are the
  same data, not a second source). Dates conflict between the sources for 5
  of 10 original papers and 4 of 17 events. Access, metadata reuse and
  redistribution are kept apart; the full CSV is not redistributed.
- **01-B:** 63 confirmed citations at pinned revisions for the 10 purposive
  papers (52 en, 11 ar). M1 finds template citations only with the `%2F`
  form; M2 cannot be batched; occurrences are classified as identifier use
  or mention (4 English pages cite only the NEJM retraction notice). All 86
  M1 (external-links) and M2 (search) responses for the purposive set were
  complete answers.
- **01-C:** 3 positive chains in both languages (Wakefield 1998, Obokata
  2014, Wolfe-Simon 2011); 5 negative controls (event type ×2, extraction,
  absence, notice citation); 3 unresolved cases kept apart.
- **01-D (census, §16):** Arabic Wikipedia cites at least **158 retracted
  papers in 157 articles (198 citations)**, confirmed at the current revision
  on 2026-10-27 from a scan of every DOI and PMID in the 2026-10-01 dumps;
  **170 of the 198 show readers no retraction warning** (148 no wording, 22
  only a red link to the missing `قالب:Retracted`); none of the 23 Arabic
  wikitext markers renders as warning text. Of 249 English article–paper
  pairs with an Arabic counterpart, 175 are not carried; of the 46 carried
  citations English marks as retracted, none shows warning wording in
  Arabic. In 20 pairs (16 papers) the English article once cited the paper
  and no longer does while the Arabic article still cites it. Lower bounds:
  link-bearing citations only.
- **01-D (purposive):** Arabic cites 3 of 10 purposive papers. Of 11 en/ar pairs that
  both cite, marking differs in 6. Every interlanguage lookup was a complete
  answer (en→ar 32 linked, 20 without a link). On Arabic Wikipedia
  `قالب:Retracted` does not exist; in the two Arabic articles whose renders
  were inspected, the marker shows as a link to the missing template with no
  warning text, while the English counterparts show "(Retracted, see …)".
  English MMR vaccine: template 778 days after the retraction, prose warning
  earlier (date not measured).
- **01-E:** random sample of 200 retracted DOIs: 0 discoverable as cited in
  either language. English: 200 complete searches; upper end of the exact
  two-sided 95% interval 0.0183. Arabic: the first run had 193 complete and
  7 unavailable searches (0.0189, n = 193); after re-sending the 7 on
  2026-10-27, 200 complete (0.0183). The estimand is a rate discoverable by this method, not a
  prevalence, and the editions are not compared with it. 21 limitations;
  requests limited to about 6.5 per minute from this environment.
- **01-F:** manifest with epistemic status per value; every data file
  re-derived by `scripts/reproduce.sh`; 101 deterministic tests in
  `tests/stage01/`, run in CI with the whole suite since 2026-10-27; live re-verification
  35 checks of 20 revisions and 9 Crossref works, 0 mismatches; clean-cache reproduction of POS-02 end-to-end and of the
  NC-03 lookups with 0 mismatches; a table of what reproduces from a
  clean checkout and what needs the (unpreserved) response cache.
- **01-G:** no critical blocker. Recommendation (advisory) **RESCOPE**: GO's
  conditions are met, but the protocol's narrower-claim trigger applies too.
  After the census it applies to timing only: edition-level counts of
  citation, marking, carrying and visible warnings are now possible for
  English and Arabic (lower bounds); how quickly editions respond stays per
  paper (FEASIBILITY_REPORT.md §16.8). Prior art now includes
  the Retraction Tracker for Wikipedia (English, daily, sentence-level, AI
  readings); novelty claims are bounded to the reviewed evidence.

## Corrective pass of 2026-10-27

Defects found and fixed (FEASIBILITY_REPORT.md §15): HTTP 200 MediaWiki
error bodies read as "0 hits" (changed the recorded Arabic sample result:
7 searches); failed link lookups readable as "no linked article" (latent,
counts unchanged); M1 continuation not followed (latent); the Shi et al.
median misattributed; a competitor listed from a snippet; an inferred
rendering claim; terms and reproducibility statements too coarse. The
User-Agent was reviewed and kept (§15.3).

## Strengthening pass of 2026-10-27

Owner-approved before acceptance (FEASIBILITY_REPORT.md §16): a census of
every Retraction Watch DOI and PMID in Arabic Wikipedia from sha1-checked
Wikimedia dumps (2026-10-01) with live confirmation; cross-wiki divergence
over every linked English–Arabic pair, with first-revision history for
papers not carried; the Arabic warning gap from rendered HTML; the Stage 01
tests moved to `tests/stage01/` so CI runs them (no Stage 00 file changed);
the disputed Shi et al. median dropped after reading the arXiv v3 full text.
633 answered Wikipedia requests plus 298 retries after 429; one failed
render re-sent once.

## Inputs and outputs

Inputs: Retraction Watch data at GitLab commit
`a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` (`retraction_watch.csv`, SHA-256
`2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`, not
committed); Wikimedia SQL dumps of 2026-10-01 (`arwiki`, `enwiki`:
externallinks, page, langlinks; sha1 as published; not committed); Crossref
REST API; MediaWiki Action API of English and Arabic
Wikipedia, Meta-Wiki and the Foundation wiki (read-only `action=query` and
`action=parse`). Retrieved 2026-10-26, with the corrective-pass requests on
2026-10-27. Public pages read for prior art: CREATIVE_FEASIBILITY.md §1.

Outputs, all in this directory:

| File | Purpose |
|---|---|
| PROTOCOL.md | Pre-registered method and decision criteria (unchanged) |
| FEASIBILITY_REPORT.md | Gate-by-gate findings, limitations, deviations, recommendation, corrective pass |
| EVIDENCE_MANIFEST.json | Machine-readable cases and aggregates with provenance and epistemic status |
| CREATIVE_FEASIBILITY.md | Prior art, signature capabilities, evaluation and classification, demo narrative, AI evaluation plan, competition strategy |
| MAESTRO_DESIGN_BRIEF.md | Future requirements for the Investigation MAESTRO (not implemented) |
| ADVERSARIAL_REVIEW.md | Same-model reviews and their dispositions |
| `scripts/` | `stage01_probe.py`, `stage01_census.py`, `build_manifest.py`, `reproduce.sh`, `clean_reproduction.sh`, `compare_clean.py` (standard library and bash only) |
| `../../../tests/stage01/` | Deterministic tests (pytest, no network), run in CI |
| `data/` | Derived records; see `data/README.md` |
| verification-record.json | Gate record for the verification transition |

Outside this directory, only `tests/stage01/` (the moved and new tests) and,
through `citerift-gov`, the registry and PROJECT_STATUS.md changed. No
dependency was added, and no Stage 00 owned path, `pyproject.toml` or
`uv.lock` changed.

## Test evidence

Stage 01 has no required test suites (`required_test_suites: []`,
`ci_required: false`). The evidence checks:

| Check | Result (2026-10-27, at `85da719`) |
|---|---|
| `uv run pytest` | 505 passed in 276.03s |
| `uv run pytest tests/stage01` | 101 passed in 0.33s |
| `uv run ruff check .` | All checks passed! |
| `uv run ruff format --check .` | 76 files already formatted |
| `uv run mypy` | Success: no issues found in 12 source files |
| `uv run citerift-gov check` | Consistency check: 0 errors, 0 warnings |
| census re-derivation from the cache and dumps | all nine `data/census/` files re-derived identical (except run times) |
| `scripts/reproduce.sh` render checks (cache) | the four `render_check_*.json` files re-derived identical (except run time) |
| `stage01_probe.py --refresh verify` | 35 checks of 20 revisions and 9 Crossref works, 0 mismatches (`data/verify_result.json`, manifest sha256 `e2e9fd48…`) |
| `scripts/clean_reproduction.sh` | 15 requests, 14 checks, 0 mismatches (`data/clean_reproduction.json`, earlier pass; not re-run) |

Reviews: a same-model adversarial review (18 findings) and a same-model QA
pass (11 issues) on 2026-10-26/27, and in the corrective pass a same-model
review covering technical, scientific, creative and integration aspects
(18 findings, 3 medium and 15 low), all dispositioned in ADVERSARIAL_REVIEW.md. The
strengthening pass was self-reviewed by the executor (10 checks, same
section). None is independent.

## Known limitations

The limitations of FEASIBILITY_REPORT.md §8.3, §15.4 and §16.7 apply. The
most important:

- The census counts link-bearing citations only (on the purposive set it
  missed 1 of 63 confirmed citations), from dumps of 2026-10-01, against
  Retraction Watch only: lower bounds, not prevalence.
- The rendered check reads the desktop parser HTML; prose warnings away
  from the citation and intentional citations are not separated.
- The divergence history reads two revisions per pair, not whole histories.
- The purposive set was chosen by the AI executor and is not representative.
- The full response cache is not preserved; a full rerun observes newer
  revisions (§9.1).
- All reviews were by the same model and are not independent.

## Open blockers

None. Questions for the owner, none blocking: whether to adopt the narrower
scope of FEASIBILITY_REPORT.md §12, and whether to keep the User-Agent as
reviewed in §15.3 (kept; the repository URL is the contact, as the Wikimedia
policy asks).

## Dependency versions

No new dependency. Scripts use the Python standard library (run with
Python 3.13.17) and bash; the tests use the project's locked pytest.
Repository quality checks ran with the locked project environment
(`uv sync --locked`).

## Verified Git commit

`85da719ac43fc46170310b225c9190b63a046df8` on branch `claude/project-thread-70xjkv` in
<https://github.com/ImanOthman-eng/citerift>: the commit containing every
evidence file above except this handoff, verification-record.json and
`data/run-logs/stage01_tests_pinned_85da719.json`, which were added afterwards
and are pinned by hash in the verification record. The governance check accepts
as gate evidence only files in this directory, so that file pins the four test
files under `tests/stage01/` by their sha256 at this revision.
The pull request must be merged with a merge commit so the cited commits stay
in `main`'s history.

`IMPLEMENTED_NOT_VERIFIED` was recorded at this revision on 2026-10-27 (commit `22264be`).
Dry run of the verification transition with `verification-record.json`
(gates 01-A to 01-G with their evidence files; Stage 01 needs no CI record):

```
$ uv run citerift-gov transition 01 VERIFIED_AWAITING_OWNER_ACCEPTANCE --actor external-agent \
    --recorded-by external-agent --revision 85da719ac43fc46170310b225c9190b63a046df8 \
    --record docs/verification/stage-01/verification-record.json --reason "..."
Transition stage 01 -> VERIFIED_AWAITING_OWNER_ACCEPTANCE: ALLOWED
Dry run: nothing written. Re-run with --apply to record it.
```

After this package was final, the same command was run with `--apply`; the
registry and PROJECT_STATUS.md record it.

## Acceptance decision

Requested from the owner. The orchestrator refuses acceptance from any actor
but the owner. The owner can accept Stage 01 at revision `85da719` (the agent
then records it with `--actor owner --owner-ref <that message>`), ask for
rework, or reject it. Adopting the RESCOPE recommendation and its narrower
scope (FEASIBILITY_REPORT.md §12) is a separate owner decision, as is
merging the pull request.

## Requirements for the next stage

- **No later stage is authorized.** Stage 02 needs its own owner
  authorization after Stage 01 is accepted.
- If the owner adopts the recommendation, later stages should take from this
  package: event history per paper and notice-versus-original DOI handling
  (Stage 02); encoded-URL M1, single-DOI M2, identifier-versus-mention
  classification including Arabic aliases, and error bodies treated as
  failures (Stage 03); events stored in a Stage-04-owned schema referencing
  contract v1, and the MAESTRO requirements (Stage 04); the AI evaluation
  plan of CREATIVE_FEASIBILITY.md §5 (Stage 06); cross-wiki comparison with
  explicit lookup states, timelines and rendered-warning states at pinned
  revisions (Stage 07); "marked in wikitext" kept distinct from "visible
  warning" (Stage 08). FEASIBILITY_REPORT.md §13 lists them.
- Rate limits: throttle, honor `Retry-After`, and precompute the demo
  investigations.
