# Stage 03 Handoff: Wikipedia Extraction Engine

Project owner: EVE TELOS.

## Stage and status

**Stage.** 03, Wikipedia Extraction Engine. The executor role is `engineering-agent`, filled successively by:

- Claude Code, under the owner's directive of 2026-10-28 (`cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS`)
  and the supplement of 2026-10-29 (D-031);
- ChatGPT/Codex, under the owner's handoff of 2026-10-30 (D-032);
- Claude Code again, under the owner's instruction of 2026-11-02
  (`cmsg_018VCB51nDHP6HXmLU4ea5yPAsujY49DkUw92HiR1mG4Ya`, D-033).

**Registry state.** `IMPLEMENTED_NOT_VERIFIED`, with the implementation recorded at the frozen candidate `48cfeab`.
**No technical verification is recorded, and none can be.** Gate 03-G is unmet: Arabic definition precision, the
Arabic identifier denominator and English key error rate fail at the frozen candidate.

**Owner actions outstanding.** The stage is not accepted. No later stage is authorized or started. Pull request #5
is open and unmerged; the owner merges personally (D-019).

The owner decision this stage needs is in `evaluation/final/DECISION_RECORD.md`.

## Verified completed work

**Engine and verification tools.** The bilingual (arwiki, enwiki) extraction engine `citerift.wiki`:

- capture with receipts;
- offline extract, verify and replay;
- the verifiable citation ledger: source anchors, containers, uses, units, identifiers with roles, render
  reconciliation, scoped marker observations and an exception ledger.

See SPECIFICATION.md and CREATIVE_DIFFERENTIATION_REVIEW.md.

**Final campaign (frozen candidate `48cfeab`).**

- 32 articles, 16 per language, all captured complete.
- Labels were locked before the single prediction run.
- All 37 disputed items were adjudicated independently: 34 confirmed, 3 corrected.
- Locked and adjudicated scores are both published. The locked scores reproduce exactly.
- 32 / 32 extractions verify and replay at `48cfeab` (G8, G10).

**Gate results under the adjudicated labels.**

| | ar | en |
|---|---|---|
| G1 identifier precision / recall | 1.000 / 0.970 | 1.000 / 0.963 |
| G2 key error rate | 0.000 | **0.0192 (fail)** |
| G3 promotions / role agreement | 0 / 1.000 | 0 / 0.942 |
| G4 uses: precision / recall / binding | 1.000 / 1.000 / 1.000 | 1.000 / 0.992 / 1.000 |
| G5 definitions (precision / recall), units (precision / recall) | **0.914 (fail)** / 1.000, 0.981 / 0.981 | 0.984 / 0.984, 0.973 / 0.956 |
| G6 render precision / false attachments / coverage | 1.000 / 0 / 1.000 | 1.000 / 0 / 1.000 |
| G7 fabricated negatives | 0 | 0 |
| Minimum denominators: identifiers / uses / definitions / linkable | **33 (min 50)** / 119 / 106 / 119 | 54 / 118 / 122 / 117 |

**Post-exposure repair RF-60.** A publisher DOI URL that ended in a page-view route (Wiley `…/abstract`) kept the
route in its key. The repair includes fail-first tests, an independent integration review (R5) and five hardening
fixes. RF-60 is labelled post-exposure, and the frozen results are unchanged.

**Documents.** All required documents are complete, including this handoff, TEST_RESULTS.md and the decision
record.

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

See TEST_RESULTS.md. The complete verification matrix was run at the final code `8c6fe9f`:

- the complete suite on Python 3.12 and 3.13;
- ruff check and format, mypy, citerift-gov check, the lock check, a dependency audit, protected paths;
- the installed-wheel smoke test with external schemas;
- the simulations.

The reports are in `final-checks/8c6fe9f/`. GitHub CI on the final pull-request head is listed in TEST_RESULTS.md
section 3. There is no `test-report.json` at a verified revision, because no verification is recorded.

## Known limitations

- **Frozen gate 03-G is not met** (RISKS.md R-034; `evaluation/final/DECISION_RECORD.md`):
  - Arabic G5a is 0.914. The cause is a guide ambiguity about repeated identical short footnotes, and the run-1 and
    final adjudications disagree on it.
  - The Arabic identifier denominator is 33 against a minimum of 50, at the sample ceiling.
  - English G2 is 1 / 52, repaired after exposure as RF-60 and not freshly evaluated.
- **No retraction warning in the final sample.** G7 is met trivially there, so warning detection rests on the run-1
  observed challenge, the synthetic and the fixture evidence.
- **Declared support boundaries** (R-035):
  - DOIs in publisher URLs without `/doi/` are not extracted;
  - citation templates the profile does not list give unstructured units and `unresolved` roles;
  - list-defined refs are not uses;
  - `verify` does not re-derive identifier decoding (`replay` does);
  - `%20` and `;jsessionid` route forms keep the route.
- **RF-60 residual risk:** a real DOI ending in a route word loses that segment. Its boundary stays flagged
  ambiguous.
- **Evaluator independence is procedural.** Evaluators and adjudicators are AI agents from two model families.
  This is not human gold.
- Only Linux was exercised. Browser visibility is `not_evaluated`. Results describe the sampled revisions, not the
  population.

## Open blockers

- None are recorded in the registry.
- The scientific gate 03-G is unmet. It is not a registry blocker, but it prevents a verification transition until
  the owner decides (DECISION_RECORD.md).

## Dependency versions

- Runtime:
  - Python 3.12 / 3.13 (tested 3.12.3 and 3.13.18);
  - mwparserfromhell 0.7.2;
  - lxml 6.1.3;
  - jsonschema 4.26.0;
  - referencing 0.37.0.
- Lock: `uv.lock`, checked with `uv lock --check`.
- Accepted Stage 02 normalizers, unchanged.

## Verified Git commit

- **Final code:** `8c6fe9f80bc6557bb48ca36e9d7003b3f897c142`, where the complete matrix ran.
- **Frozen evaluation candidate:** `48cfeab2c093ea0e853fe2ccb2cd1d5ff87a528b`.

Neither is a registry "verified revision". The stage is not verified, because 03-G is unmet.

## Acceptance decision

**Pending the owner.** The executor recommends outcome B: an owner-recorded narrowing of 03-G to the claims in
DECISION_RECORD.md section 4, followed by verification at the then-current head, then owner acceptance and a
personal merge. The alternative is a prospective new evaluation (C), authorized before any acquisition.

The executor records no acceptance and merges nothing.

## Requirements for the next stage

Stage 04 is not authorized. It depends on Stage 03 being accepted (GOVERNANCE.md invariant 3).

When it starts, it must:

- treat keys with `IDENTIFIER_BOUNDARY_AMBIGUOUS` or role `unresolved` as unconfirmed;
- treat Arabic identifier results as lower-confidence (33-item evidence);
- never treat a missing identifier or a `not_inspected` marker as "not retracted";
- keep co-reported identifiers unmerged;
- use the replay check, not verify alone, where identifier decoding must be trusted.
