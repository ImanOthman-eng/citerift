# Stage 03 Handoff: Wikipedia Extraction Engine

Project owner: EVE TELOS.

## Stage and status

**Stage.** 03, Wikipedia Extraction Engine. The executor role is `engineering-agent`, filled successively by:

- Claude Code, under the owner's directive of 2026-10-28 (`cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`)
  and the supplement of 2026-10-29 (D-031);
- ChatGPT/Codex, under the owner's handoff of 2026-10-30 (D-032);
- Claude Code, under the owner's instructions of 2026-11-02: recovery (`cmsg_018VCB51nDHP6HXmLU4ea5yPAsujY49DkUw92HiR1mG4Ya`,
  D-033) and corrective engineering with one prospective confirmation campaign
  (`cmsg_018VCB51nDHP6HXmLU4ea5yP8BNaHtTfgxhSrEp6pbWPHh`, D-034).

**Registry state.** `IMPLEMENTED_NOT_VERIFIED`, recorded at the confirmation freeze (`0d46ba4`, candidate `3e51792`).
**No technical verification is recorded.** The confirmation campaign passes every gate in Arabic and every gate but
one in English: **English G5c unit precision is 0.869 against 0.95** (RISKS.md R-036).

**Owner actions outstanding.**
- The scientific decision on G5c: `evaluation/confirmation-2026-11/DECISION_RECORD.md`.
- Acceptance, and the merge of pull request #5, which is open. The owner merges personally (D-019).
- No later stage is authorized or started.

## Verified completed work

**Engine and verification tools.** The bilingual (arwiki, enwiki) extraction engine `citerift.wiki`:

- capture with receipts;
- offline extract, verify and replay;
- the verifiable citation ledger: source anchors, containers, uses, units, identifiers with roles, render
  reconciliation, scoped marker observations and an exception ledger.

See SPECIFICATION.md and CREATIVE_DIFFERENTIATION_REVIEW.md.

**Corrective engineering under D-034, all before the freeze** (SPECIFICATION.md, last section;
`review/REVIEW_FINDINGS.md`):

- short-footnote identity per Module:Footnotes, with a formal definition/use decision;
- DOI boundary defects D-1 and D-2;
- Retry-After and network-gate defects G-1 and G-2, and a resumable, journalled campaign driver;
- MF-1 v2: a native tokenizer crash is classified without becoming an extraction;
- one adversarial review (R6, 13 findings) and one focused review (R7, 8 findings), all dispositioned.

**Confirmation campaign** (`evaluation/confirmation-2026-11/campaign/REPORT.md`):

- 24 Arabic and 20 English holdout articles and a 10-article English warning challenge, all captured complete.
- 263 HTTP attempts and 12.6 MB, against ceilings of 500 attempts and 300 MiB.
- Labels by 10 isolated AI evaluator instances, locked and committed before the single prediction run.
- 113 disputed items adjudicated by 6 AI adjudicator instances: 104 confirmed, 9 corrected.
- 54 / 54 extractions verify and replay (G8, G10).
- Locked and adjudicated scores, intervals and an evidence-integrity audit (27 / 27 checks pass, with scores
  reproduced byte for byte).

**Gate results under the adjudicated labels.**

| | ar | en |
|---|---|---|
| G1 identifier precision / recall | 0.980 / 0.951 | 1.000 / 0.960 |
| G2 key error rate | 0.000 | 0.000 |
| G3 promotions / role agreement | 0 / 1.000 | 0 / 0.958 |
| G4 uses: precision / recall / binding | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| G5 definitions (precision / recall), units (precision / recall) | 1.000 / 1.000, 0.988 / 0.988 | 1.000 / 0.987, **0.869 (fail)** / 0.969 |
| G6 render precision / false attachments / coverage | 1.000 / 0 / 1.000 | 1.000 / 0 / 1.000 |
| G7 fabricated negatives | 0 | 0 |
| Minimum denominators: identifiers / uses / definitions / linkable | 103 / 190 / 160 / 189 | 50 / 274 / 157 / 274 |
| Warning challenge | no candidates in the frame | 6 / 6 detected, 0 fabricated, 0 false |

The three failures of the earlier final campaign (candidate `48cfeab`) do not recur.

**Documents.** SPECIFICATION, MATHEMATICAL_MODEL, RISK_ANALYSIS, SIMULATION_REPORT, CREATIVE_DIFFERENTIATION_REVIEW,
TEST_RESULTS, COMPLETION_CHECKLIST, this handoff, the campaign report and decision record, RISKS.md R-036.

## Inputs and outputs

**Inputs:**
- pinned Wikipedia revisions captured through the Wikimedia Core REST API (source wikitext and Parsoid HTML, with
  receipts);
- the Stage 02 normalizers `normalize_doi` and `normalize_pmid`, used unchanged through `citerift.wiki.identifiers`.

**Outputs:**
- capture bundles;
- extraction documents (`schemas/wiki/v1/extraction.schema.json`);
- verify and replay reports, from the CLI `citerift-wiki {capture,extract,verify,replay}`.

Article content in retained bundles is attributed in ATTRIBUTION.md (CC BY-SA 4.0).

## Test evidence

TEST_RESULTS.md section 7 holds the complete verification matrix at the final head of this work: both Python
versions, static checks, governance, lock, dependency audit, protected paths, installed wheel, simulations. GitHub CI
on the final pull-request head is given in the pull request #5 description, because a commit cannot contain its own
CI run.

## Known limitations

- **English G5c is not met** (R-036). The engine's `unstructured_text` unit is wider than the guide's
  `unstructured`: a Harvard short-citation link, an explanatory note that cites nothing, or an unlisted citation-like
  template is `unstructured_text`.
- **No Arabic field evidence of warning detection:** no Arabic article in the frame transcludes a warning template.
- **Small positive sample:** 6 English warnings; sensitivity interval [0.541, 1.000].
- **Zero-tolerance gates at these sizes:** 0 key errors and 0 promotions bound the rates only at 3.0 % (ar) and 6.1 %
  (en).
- **AI labels, not human gold.** Evaluators on Claude Sonnet, adjudicators on a smaller model (Claude Haiku), one
  vendor. The harness attached the repository `CLAUDE.md` to their contexts; one evaluator wrote one scratch file
  outside its work directory (RISK_ANALYSIS.md E9, E13).
- **Declared support boundaries** (R-035):
  - DOIs in publisher URLs without `/doi/` are not extracted;
  - citation templates the profile does not list give unstructured units and `unresolved` roles;
  - list-defined refs are not uses;
  - `verify` does not re-derive identifier decoding (`replay` does);
  - `%20` and `;jsessionid` route forms keep the route.
- Only Linux was exercised. Browser visibility is `not_evaluated`. Results describe the sampled revisions, not the
  population.
- Fifteen public commits of 2026-10-30/31 carry a personal author name. Public history is not rewritten; this is an
  unresolved privacy concern for the owner.

## Open blockers

- None are recorded in the registry.
- English G5c is unmet. It is not a registry blocker, but it prevents a verification transition until the owner
  decides (`evaluation/confirmation-2026-11/DECISION_RECORD.md`).

## Dependency versions

- Runtime:
  - Python 3.12 / 3.13;
  - mwparserfromhell 0.7.2;
  - lxml 6.1.3;
  - jsonschema 4.26.0;
  - referencing 0.37.0.
- Lock: `uv.lock`, unchanged since `8c6fe9f`, checked with `uv lock --check`.
- Accepted Stage 02 normalizers, unchanged.

## Verified Git commit

- **Frozen evaluation candidate:** `3e51792`. `src/`, `schemas/`, `pyproject.toml` and `uv.lock` are unchanged from
  it to the final head.
- **Final head:** the commit named in TEST_RESULTS.md section 7, where the complete matrix ran.

Neither is a registry "verified revision". The stage is not verified, because G5c is unmet.

## Acceptance decision

**Pending the owner.** The executor recommends outcome A of the decision record: an owner-recorded narrowing that
excludes G5c from the verified claim and defines `unstructured_text` as "no recognised citation template unit",
followed by the verification transition at the then-current head, then owner acceptance and a personal merge. The
alternatives are a post-exposure specification correction (B) or keeping the stage unverified (C).

The executor records no acceptance and merges nothing.

## Requirements for the next stage

Stage 04 is not authorized. It depends on Stage 03 being accepted (GOVERNANCE.md invariant 3).

When it starts, it must:

- never read an `unstructured_text` unit as evidence that a definition cites a work;
- treat keys with `IDENTIFIER_BOUNDARY_AMBIGUOUS` or role `unresolved` as unconfirmed;
- never treat a missing identifier or a `not_inspected` marker as "not retracted";
- treat Arabic warning detection as untested on real articles;
- keep co-reported identifiers unmerged;
- use the replay check, not verify alone, where identifier decoding must be trusted.
