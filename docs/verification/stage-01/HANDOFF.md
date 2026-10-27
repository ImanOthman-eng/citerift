# Stage 01 Handoff: Independent Feasibility Investigation

## Stage and status

- Stage: 01, Independent Feasibility Investigation. Executor role:
  `external-agent`, filled by a Claude Code session in a separate project
  thread under the owner's directive of 2026-10-26
  (`cmsg_018VCB51nDHP6HXmLU4ea5yPHoNtmrTEksWGzn64yEgVJc`). Independence is
  procedural, not organizational (FEASIBILITY_REPORT.md §2).
- Research protocol fixed and pushed before any Wikipedia query
  (PROTOCOL.md, commit `c26d2d9`, which also recorded `IN_PROGRESS`).
- Evidence revision: `562fe1a9d0498612c61f63c820bbd1c54aa38545`, recorded as the implementation revision
  (`IMPLEMENTED_NOT_VERIFIED`). This package is the evidence for the
  transition to `VERIFIED_AWAITING_OWNER_ACCEPTANCE`.
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
| 01-B | Wikipedia citation discoverability evidenced | pass | FEASIBILITY_REPORT.md §5; `data/purposive_discovery.json`; `data/rate-limit/` |
| 01-C | Verified positive and negative examples | pass | FEASIBILITY_REPORT.md §6; EVIDENCE_MANIFEST.json cases POS-01–03, NC-01, NC-01b, NC-02–04, U-01–03; `data/followups/nc2_absence_check_*.json`, `nc3_lookup.json` |
| 01-D | Initial cross-language feasibility evidenced | pass | FEASIBILITY_REPORT.md §7; `data/followups/crosswiki_*.json`, `timeline_*.json`, `ar_*.json`, `en_mmr_retraction_text_check.json` |
| 01-E | Coverage limitations documented | pass | FEASIBILITY_REPORT.md §8; `data/sample_S.json`; `data/sample_S_discovery.json` |
| 01-F | Source references and reproducible findings | pass | EVIDENCE_MANIFEST.json; `scripts/`; `data/verify_result.json`; FEASIBILITY_REPORT.md §9, §14 |
| 01-G | Critical blockers and recommendations stated | pass | FEASIBILITY_REPORT.md §12; CREATIVE_FEASIBILITY.md; MAESTRO_DESIGN_BRIEF.md; ADVERSARIAL_REVIEW.md |

Main results (details and labels in FEASIBILITY_REPORT.md):

- **01-A:** pinned Retraction Watch snapshot (73,356 records) with original
  DOI, notice DOI, event type and date; 17 of 19 purposive events have a
  separate, resolving Crossref notice, but only 4 have a publisher link that
  confirms link and type (Crossref's Retraction Watch-sourced links are the
  same data, not a second source). Dates conflict between the sources for 5
  of 10 original papers and 4 of 17 events.
- **01-B:** 63 confirmed citations at pinned revisions for the 10 purposive
  papers (52 en, 11 ar). M1 finds template citations only with the `%2F`
  form; M2 cannot be batched; occurrences are classified as identifier use
  or mention (4 English pages cite only the NEJM retraction notice).
- **01-C:** 3 positive chains in both languages (Wakefield 1998, Obokata
  2014, Wolfe-Simon 2011); 5 negative controls (event type ×2, extraction,
  absence, notice citation); 3 unresolved cases kept apart.
- **01-D:** Arabic cites 3 of 10 purposive papers. Of 11 en/ar pairs that
  both cite, marking differs in 6. On Arabic Wikipedia `قالب:Retracted` does
  not exist, so 14 articles carry a marker that does not render; the
  Arabic template has 0 article uses. English MMR vaccine: template 778 days
  after the retraction, prose warning earlier (date not measured).
- **01-E:** random sample of 200 retracted DOIs: 0 cited in either language
  (95% upper bound 0.0183 each); 19 limitations; requests limited to about
  6.5 per minute from this environment.
- **01-F:** manifest with epistemic status per value; every data file
  re-derived by `scripts/reproduce.sh`; live re-verification 35 checks of 20
  revisions and 9 Crossref works, 0 mismatches.
- **01-G:** no critical blocker. Recommendation (advisory) **RESCOPE**: GO's
  conditions are met, but the protocol's narrower-claim trigger applies too;
  the narrower scope is a revision-pinned English–Arabic comparison of named
  papers and article pairs, not edition-level rates.

## Inputs and outputs

Inputs: Retraction Watch data at GitLab commit
`a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` (`retraction_watch.csv`, SHA-256
`2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`, not
committed); Crossref REST API; MediaWiki Action API of English and Arabic
Wikipedia and Meta-Wiki (read-only `action=query`). All retrieved 2026-10-26.

Outputs, all in this directory:

| File | Purpose |
|---|---|
| PROTOCOL.md | Pre-registered method and decision criteria |
| FEASIBILITY_REPORT.md | Gate-by-gate findings, limitations, deviations, recommendation |
| EVIDENCE_MANIFEST.json | Machine-readable cases and aggregates with provenance and epistemic status |
| CREATIVE_FEASIBILITY.md | Creative differentiation review: prior art, contributions A–F, hypotheses |
| MAESTRO_DESIGN_BRIEF.md | Future requirements for the Investigation MAESTRO (not implemented) |
| ADVERSARIAL_REVIEW.md | Same-model adversarial review findings and dispositions |
| `scripts/` | `stage01_probe.py`, `build_manifest.py`, `reproduce.sh` (standard library and bash only) |
| `data/` | Derived records; see `data/README.md` |
| verification-record.json | Gate record for the verification transition |

No file outside this directory was changed except the registry and
PROJECT_STATUS.md through `citerift-gov`. No dependency was added.

## Test evidence

Stage 01 has no required test suites (`required_test_suites: []`,
`ci_required: false`). The evidence checks are:

| Check | Result (2026-10-27, at `562fe1a`) |
|---|---|
| `uv run pytest` | 404 passed |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 70 files already formatted |
| `uv run mypy` | Success: no issues found in 12 source files |
| `uv run citerift-gov check` | 0 errors, 0 warnings |
| `scripts/reproduce.sh` (cache) | all data files re-derived, exit 0 |
| `stage01_probe.py --refresh verify` | 35 checks, 20 revisions, 9 Crossref works, 0 problems (`data/verify_result.json`) |

Reviews: a same-model adversarial review (18 findings) and a same-model QA
pass (11 issues), all dispositioned in ADVERSARIAL_REVIEW.md. Neither is
independent.

## Known limitations

The 19 limitations of FEASIBILITY_REPORT.md §8.3 apply. The most important:

- Neither discovery method is a census; references without a DOI are not
  found; nothing here is a prevalence of retracted citations in Wikipedia.
- Arabic counts are small; Arabic findings are case-level.
- The purposive set was chosen by the AI executor and is not representative.
- The adversarial review was by the same model and is not independent.
- Wikipedia observations are of 2026-10-26 revisions; the pinned revisions
  do not change, the articles do.

## Open blockers

None. Questions for the owner, none blocking: whether the project's GitHub
handle may stay in the User-Agent string of the probe (`docs/identity.md`
limits where it appears; ADVERSARIAL_REVIEW.md RV-17), and whether to adopt
the narrower scope of FEASIBILITY_REPORT.md §12.

## Dependency versions

No new dependency. Scripts use the Python standard library (run with
Python 3.13.17) and bash. Repository quality checks ran with the locked project
environment (`uv sync --locked`).

## Verified Git commit

`562fe1a9d0498612c61f63c820bbd1c54aa38545` on branch `claude/project-thread-70xjkv` in
<https://github.com/ImanOthman-eng/citerift>: the commit containing every
evidence file above except this handoff and verification-record.json, which
were added afterwards and are pinned by hash in the verification record.
The pull request must be merged with a merge commit so the cited commits stay
in `main`'s history.

`IMPLEMENTED_NOT_VERIFIED` was recorded at this revision on 2026-10-27.
Dry run of the verification transition with `verification-record.json`
(gates 01-A to 01-G with their evidence files; Stage 01 needs no CI record):

```
$ uv run citerift-gov transition 01 VERIFIED_AWAITING_OWNER_ACCEPTANCE --actor external-agent \
    --recorded-by external-agent --revision 562fe1a9d0498612c61f63c820bbd1c54aa38545 \
    --record docs/verification/stage-01/verification-record.json --reason "..."
Transition stage 01 -> VERIFIED_AWAITING_OWNER_ACCEPTANCE: ALLOWED
Dry run: nothing written. Re-run with --apply to record it.
```

After this package was final, the same command was run with `--apply`; the
registry and PROJECT_STATUS.md record it.

## Acceptance decision

Requested from the owner. The orchestrator refuses acceptance from any actor
but the owner. The owner can accept Stage 01 at revision `562fe1a` (the agent
then records it with `--actor owner --owner-ref <that message>`), ask for
rework, or reject it. Adopting the RESCOPE recommendation and its narrower
scope (FEASIBILITY_REPORT.md §12) is a separate owner decision, as is
merging the pull request.

## Requirements for the next stage

- **No later stage is authorized.** Stage 02 needs its own owner
  authorization after Stage 01 is accepted.
- If the owner adopts the recommendation, later stages should take from this
  package: event history per paper and notice-versus-original DOI handling
  (Stage 02); encoded-URL M1, single-DOI M2 and identifier-versus-mention
  classification including Arabic aliases (Stage 03); events stored in a
  Stage-04-owned schema referencing contract v1, and the MAESTRO
  requirements (Stage 04); cross-wiki comparison and timelines at pinned
  revisions (Stage 07); "marked in wikitext" kept distinct from "visible
  warning" (Stage 08). FEASIBILITY_REPORT.md §13 lists them.
- Rate limits: throttle, honor `Retry-After`, and precompute the demo
  investigations.
