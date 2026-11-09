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
  D-035): G5c semantic correction and one further prospective confirmation;
- Claude Code, under the owner's instruction of 2026-11-04 (`cmsg_018VCB51nDHP6HXmLU4ea5yPJGcnAZCAku5nJRxTZzFaL7`,
  D-036): R-038 correction, readiness reviews and one final prospective confirmation;
- OpenAI Codex, under the owner's instruction of 2026-11-04 (D-037), while Claude was unavailable: preservation and
  audit of the D-036 checkpoint (`7646fe7`) and a contingent model-substitution record (`de66152`); no scientific
  output;
- Claude Code, under the owner's instruction of 2026-11-09 (`cmsg_018VCB51nDHP6HXmLU4ea5yPKQJiBv5w48TqZw8UJbfJvw`,
  D-038): completion of D-036 with its original model roles (D-037 not exercised), verification and delivery.

**Result (D-036 confirmation, `evaluation/confirmation-d036/campaign/REPORT.md`).** On 24 Arabic and 20 English
unexposed articles, the frozen candidate `8901a59` passes **every gate G1 to G11 and every minimum denominator in both
languages** on the adjudicated labels, including G5c (ar 1.000, en 0.977), G5d (0.966, 0.992), G6a (1.000, 1.000),
G6b (0 false attachments in each) and G6c (1.000, 1.000). R-038 does not recur. Arabic G2 is decided by one
adjudicated correction, and English G5c's interval reaches 0.929 (report section 4.1).

**Registry state and delivery.** On this branch (the scientific record, continuing PR #5's history) Stage 03 stays
`IMPLEMENTED_NOT_VERIFIED` at candidate `8901a59`. The verification transition is recorded on the clean delivery
branch, whose history holds `main` and the final tree only (section "Verified Git commit"), so that a merge does not
publish the restricted historical blobs (`security/PRESIGNED_URL_REVIEW.md`).

**Owner actions outstanding.**
- Acceptance of Stage 03, and the choice and execution of the merge. The owner merges personally (D-019).
- No later stage is authorized or started.

The D-034 and D-035 sections below are kept as the historical record of those campaigns.

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
A final independent integration audit (`evaluation/confirmation-d035/INTEGRATION_AUDIT.md`) confirmed the change set,
the G6b diagnosis and the deviations; it found no critical issue and no defect introduced by D-035.

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

## D-036 correction and final confirmation

**Correction, before the freeze** (SPECIFICATION.md, "Changes under owner instruction D-036";
`design/r038-reconciliation/`): repeated names inside one template's output are paired only on evidence and
abstained otherwise (engine and schema 1.2.0); fail-first reproduction; differential on every retained bundle; two
independent readiness reviews and a focused re-review, every confirmed finding fixed
(`design/r038-reconciliation/review/DISPOSITIONS.md`).

**Confirmation campaign** (`evaluation/confirmation-d036/campaign/REPORT.md`): candidate `8901a59`; 24 Arabic and 20
English unexposed articles (one English reserve block); 208 HTTP attempts and 7.4 MB of 500 / 300 MiB; labels by 8
isolated Claude Sonnet instances, locked before the single prediction run; 19 disputed items adjudicated by 2 Claude
Haiku instances (16 confirmed, 3 corrected); 44 / 44 extractions verify and replay; evidence audit 25 / 25. The
campaign was interrupted on 2026-11-04 after its reserve packets (`80000f2`) and resumed on 2026-11-09 (D-038); one
reserve evaluator instance whose output was never observed was replaced by a fresh one (report sections 3 and 6).

| Adjudicated labels | ar | en |
|---|---|---|
| G1 identifier precision / recall | 1.000 / 0.929 | 1.000 / 0.984 |
| G2 key error rate; G3 promotions / role agreement | 0.000; 0 / 0.942 | 0.000; 0 / 1.000 |
| G4 uses: precision / recall / binding | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| G5 definitions (precision / recall), units (precision / recall) | 1.000 / 1.000, **1.000 / 0.966** | 1.000 / 1.000, **0.977 / 0.992** |
| G6 render precision / false attachments (limit) / coverage | **1.000 / 0 (1) / 1.000** | **1.000 / 0 (2) / 1.000** |
| G7 fabricated negatives | 0 (no labelled warning) | 0 (no labelled warning) |
| G8 verify / G9 acquisition / G10 replay | 24 / 24; 24 / 24 with render; 24 / 24 | 20 / 20; 20 / 20; 20 / 20 |
| Minimum denominators: identifiers / uses / definitions / linkable | 56 / 187 / 147 / 187 | 64 / 282 / 143 / 282 |

Intervals: report section 7 (English G5c [0.929, 1.000], Arabic G5d [0.897, 1.000]).

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

TEST_RESULTS.md section 9 holds the complete verification matrix of the final delivery revision (both Python versions,
static checks, governance, lock, dependency audit, protected paths, installed wheel, simulations), with the GitHub CI
run of that revision. Sections 7 and 8 hold the D-034 and D-035 matrices. Earlier matrices, including the Codex
checkpoint's, describe their own revisions only.

## Known limitations

- **R-038 is corrected and confirmed on one sample** (0 false attachments in 469 engine links); the corrected path
  was exercised on 8 uses in 3 articles only. Where evidence does not decide a pairing, the use is abstained.
- **Arabic G2 depends on one adjudicated correction** (0.0192 on the locked labels), and **English G5c's interval**
  is [0.929, 1.000] (R-036; residual limits of the citation-unit classes are R-037).
- **G7 is vacuous in the D-035 and D-036 samples** (no labelled warning, no warning challenge); field sensitivity rests on the
  D-034 challenge (6 / 6).
- **Five captured files are withheld from git** (a third-party AWS key id in one enwiki article); they are in the
  checksum-verified export (`evaluation/confirmation-d035/campaign/WITHHELD_FILES.json`).
- **No Arabic field evidence of warning detection:** no Arabic article in the frame transcludes a warning template.
- **Small positive sample:** 6 English warnings; sensitivity interval [0.541, 1.000].
- **Zero-tolerance gates at these sizes:** 0 key errors and 0 promotions bound the rates only at about 5 % in the
  D-035 sample (3.0 % / 6.1 % in D-034).
- **AI labels, not human gold.** Evaluators on Claude Sonnet, adjudicators on a smaller model (Claude Haiku), one
  vendor. The harness attached the repository `CLAUDE.md` to their contexts; one evaluator in 2026-11 and one in
  D-036 wrote scratch files outside their work directories (RISK_ANALYSIS.md E9, E13; D-036 report section 6).
- **D-036 transcripts.** The seven evaluator transcripts of 2026-11-04 are no longer available; their isolation audit
  was committed at the time (RISK_ANALYSIS.md E30).
- **Declared support boundaries** (R-035):
  - DOIs in publisher URLs without `/doi/` are not extracted;
  - citation templates the profile does not list give unstructured units and `unresolved` roles;
  - list-defined refs are not uses;
  - `verify` does not re-derive identifier decoding (`replay` does);
  - `%20` and `;jsessionid` route forms keep the route.
- Only Linux was exercised. Browser visibility is `not_evaluated`. Results describe the sampled revisions, not the
  population.
- Fifteen public commits of 2026-10-30/31 and the two Codex commits of 2026-11-04 (`7646fe7`, `de66152`) carry a
  personal author name and e-mail address. Public history is not rewritten. None of these commits is in the clean
  delivery branch's history; they stay on the public PR #5 and continuation branches.

## Open blockers

- None. B-03-001 (D-037 evaluator runtime) was resolved with `citerift-gov` on 2026-11-09 (`7bab386`) after a Claude
  Sonnet evaluator ran with a retained transcript; D-037 was not exercised.

## Dependency versions

- Runtime:
  - Python 3.12 / 3.13;
  - mwparserfromhell 0.7.2;
  - lxml 6.1.3;
  - jsonschema 4.26.0;
  - referencing 0.37.0.
- Lock: `uv.lock`, unchanged since `8c6fe9f`, checked with `uv lock --check` (TEST_RESULTS.md section 9).
- Accepted Stage 02 normalizers, unchanged.

## Verified Git commit

- **Frozen evaluation candidate:** `8901a59` (D-036; `src` tree `cda4a4b6`, `schemas` tree `360501fc`). `src/`,
  `schemas/`, `pyproject.toml` and `uv.lock` are unchanged from it to the final head of this branch and in the
  delivery branch.
- **Scientific record:** this branch, from `80000f2` (PR #5's head) through the campaign commits `bf7866a` to
  `1cd45a1` and the documents. The evidence audit re-checks commit order on this history.
- **Verified revision:** recorded on the clean delivery branch, whose first commit has `main` as its only parent and
  whose tree equals this branch's final tree except the registry; see TEST_RESULTS.md section 9 there.

## Acceptance decision

**Pending the owner.** Every gate passes; the executor recommends acceptance through the clean delivery branch.
The executor records no acceptance and merges nothing.

## Requirements for the next stage

Stage 04 is not authorized. It depends on Stage 03 being accepted (GOVERNANCE.md invariant 3).

When it starts, it must:

- read `unstructured_text` only as the D-035 classes define it, and never as proof of a citation where a class is
  unresolved;
- treat an abstained render link (a repeated name inside a template's output without deciding evidence) as unknown,
  not as absent (R-038);
- treat keys with `IDENTIFIER_BOUNDARY_AMBIGUOUS` or role `unresolved` as unconfirmed;
- never treat a missing identifier or a `not_inspected` marker as "not retracted";
- treat Arabic warning detection as untested on real articles;
- keep co-reported identifiers unmerged;
- use the replay check, not verify alone, where identifier decoding must be trusted.
