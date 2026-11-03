# Stage 03 Handoff: Wikipedia Extraction Engine

Project owner: EVE TELOS.

## Stage and status

**Stage.** 03, Wikipedia Extraction Engine. The executor role is `engineering-agent`, filled successively by:

- Claude Code, under the owner's directive of 2026-10-28 (`cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`)
  and the supplement of 2026-10-29 (D-031);
- ChatGPT/Codex, under the owner's handoff of 2026-10-30 (D-032);
- Claude Code, under the owner's instructions of 2026-11-02: recovery (`cmsg_018VCB51nDHP6HXmLU4ea5yPAsujY49DkUw92HiR1mG4Ya`,
  D-033) and corrective engineering with one prospective confirmation campaign
  (`cmsg_018VCB51nDHP6HXmLU4ea5yP8BNaHtTfgxhSrEp6pbWPHh`, D-034);
- Claude Code, under the owner's instruction of 2026-11-03 (`cmsg_018VCB51nDHP6HXmLU4ea5yPBxa7nEyAiE3VN5Lw442e8F`,
  D-035): G5c semantic correction and one further prospective confirmation.

**Registry state.** `IMPLEMENTED_NOT_VERIFIED`, recorded at the D-035 candidate freeze (`b1e069e`, candidate
`fff0e5b`). **No technical verification is recorded.**

**Current result (D-035 confirmation, `evaluation/confirmation-d035/campaign/REPORT.md`).** The G5c correction holds
prospectively: English G5c 0.994 and G5d 0.994, Arabic 1.000 and 0.992. Every gate passes in English. In Arabic every
gate passes except **G6b: 2 false render attachments against a frozen limit of 1**, caused by a verified engine defect
in the reconciliation of repeated names inside an infobox (RISKS.md R-038). The amendment forbids repair after the run.

**Owner actions outstanding.**
- The decision on R-038: `evaluation/confirmation-d035/DECISION_RECORD.md`.
- Acceptance, and the merge of pull request #5, which is open. The owner merges personally (D-019).
- No later stage is authorized or started.

The D-034 sections below are kept as the historical record of that campaign. The owner rejected outcome A of its
decision record (D-035); the D-035 results are in the section "D-035 correction and confirmation".

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

## D-035 correction and confirmation

**Correction, before the freeze** (SPECIFICATION.md, "Changes under owner instruction D-035";
`design/unit-semantics/`):
- fail-first reproduction of the 19 English false positives;
- citation-unit classes A-H: `unstructured_text` only on positive evidence; new kind `unsupported_citation_template`;
  engine and schema 1.1.0;
- differential checks on all 146 retained bundles;
- one independent adversarial review and a second independent review, every confirmed finding fixed; MF-1 v3.

**Confirmation campaign** (`evaluation/confirmation-d035/campaign/REPORT.md`): candidate `fff0e5b`; 24 Arabic and 24
English unexposed articles (two English reserve blocks); 280 HTTP attempts and 9.2 MB of 500 / 300 MiB; labels by 9
isolated AI evaluator instances, locked before the single prediction run; 46 disputed items adjudicated by 3 AI
adjudicator instances (45 confirmed, 1 corrected); 48 / 48 extractions verify and replay; evidence audit 28 / 28.

| Adjudicated labels | ar | en |
|---|---|---|
| G1 identifier precision / recall | 1.000 / 0.967 | 1.000 / 1.000 |
| G2 key error rate; G3 promotions / role agreement | 0.000; 0 / 1.000 | 0.000; 0 / 1.000 |
| G4 uses: precision / recall / binding | 1.000 / 0.995 / 1.000 | 1.000 / 0.986 / 1.000 |
| G5 definitions (precision / recall), units (precision / recall) | 1.000 / 1.000, 1.000 / 0.992 | 1.000 / 1.000, **0.994 / 0.994** |
| G6 render precision / false attachments (limit) / coverage | 0.989 / **2 (1): fail** / 0.924 | 1.000 / 0 (2) / 0.981 |
| G7 fabricated negatives | 0 (no labelled warning) | 0 (no labelled warning) |
| G8 verify / G9 acquisition / G10 replay | 24 / 24; 23 / 24 with render; 24 / 24 | 24 / 24; 24 / 24; 24 / 24 |
| Minimum denominators: identifiers / uses / definitions / linkable | 61 / 207 / 153 / 197 | 60 / 210 / 195 / 207 |

Intervals: `evaluation/confirmation-d035/campaign/REPORT.md` section 7 (English G5c [0.978, 1.000], G5d
[0.980, 1.000]).

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

TEST_RESULTS.md section 8 holds the complete verification matrix of the D-035 work at `6c499a7` (section 7: D-034
at `e6b3d7b`): both Python
versions, static checks, governance, lock, dependency audit, protected paths, installed wheel, simulations. GitHub CI
on the final pull-request head is given in the pull request #5 description, because a commit cannot contain its own
CI run.

## Known limitations

- **Arabic G6b is not met** (R-038). Inside one template's output, repeated uses of one reference name are paired
  with their rendered markers in source order; an infobox that reorders its rows swaps them.
- **English G5c** was not met at `3e51792` (R-036); at `fff0e5b` it is 0.994 on fresh articles. The residual limits
  of the citation-unit classes are R-037.
- **G7 is vacuous in the D-035 sample** (no labelled warning, no warning challenge); field sensitivity rests on the
  D-034 challenge (6 / 6).
- **Five captured files are withheld from git** (a third-party AWS key id in one enwiki article); they are in the
  checksum-verified export (`evaluation/confirmation-d035/campaign/WITHHELD_FILES.json`).
- **No Arabic field evidence of warning detection:** no Arabic article in the frame transcludes a warning template.
- **Small positive sample:** 6 English warnings; sensitivity interval [0.541, 1.000].
- **Zero-tolerance gates at these sizes:** 0 key errors and 0 promotions bound the rates only at about 5 % in the
  D-035 sample (3.0 % / 6.1 % in D-034).
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
- Arabic G6b is unmet because of R-038. It is not a registry blocker, but it prevents a verification transition
  until the owner decides (`evaluation/confirmation-d035/DECISION_RECORD.md`).

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

- **Frozen evaluation candidate:** `fff0e5b` (D-035). `src/`, `schemas/`, `pyproject.toml` and `uv.lock` are
  unchanged from it to the final head. The D-034 candidate was `3e51792`.
- **Matrix revision:** `6c499a7`, named in TEST_RESULTS.md section 8. Later commits add documents only.

Neither is a registry "verified revision". The stage is not verified, because Arabic G6b is unmet (R-038).

## Acceptance decision

**Pending the owner.** The D-034 recommendation (outcome A) was rejected by the owner in D-035 and is withdrawn.
For the D-035 result, `evaluation/confirmation-d035/DECISION_RECORD.md` section 4 sets out the minimum legitimate
path: an owner-authorized narrow correction of R-038 (abstain instead of guessing), then one more bounded prospective
bilingual confirmation under the unchanged gates. The alternative is to keep the stage unverified.

The executor records no acceptance and merges nothing.

## Requirements for the next stage

Stage 04 is not authorized. It depends on Stage 03 being accepted (GOVERNANCE.md invariant 3).

When it starts, it must:

- read `unstructured_text` only as the D-035 classes define it, and never as proof of a citation where a class is
  unresolved;
- not rely on which source use a rendered marker of a repeated name inside a template's output belongs to (R-038);
- treat keys with `IDENTIFIER_BOUNDARY_AMBIGUOUS` or role `unresolved` as unconfirmed;
- never treat a missing identifier or a `not_inspected` marker as "not retracted";
- treat Arabic warning detection as untested on real articles;
- keep co-reported identifiers unmerged;
- use the replay check, not verify alone, where identifier decoding must be trusted.
