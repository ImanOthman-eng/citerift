# Prospective amendment: the D-035 confirmation campaign

**Authority.** The owner's instruction of 2026-11-03, section 7 (`../authorization/OWNER_DIRECTIVE_2026-11-03_G5C.md`,
DECISIONS.md D-035). It authorizes exactly one additional bounded prospective confirmation of the corrected
candidate and no other campaign. This amendment is that campaign's protocol.

**When it was written.** It was written and committed before any article of the campaign was drawn, captured,
annotated or extracted. No outcome of the campaign existed when any rule below was set.

**What stays.** It does not change any of these:
- FROZEN_PROTOCOL.md, AMENDMENT_2026-10-29.md or AMENDMENT_2026-11-02_CONFIRMATION.md;
- annotation guide 1.1;
- `scripts/evaluate.py` or `scripts/evaluate_v2.py`;
- any earlier selection, capture, label, lock, prediction, score or adjudication.

The 2026-11 confirmation campaign stays a published result: English G5c 0.869, not verified. It is not rerun, and its
articles are not evidence here. They are exposed, and they shaped the correction.

## 1. What stays exactly as in the 2026-11 confirmation

Everything in AMENDMENT_2026-11-02_CONFIRMATION.md sections 1, 3 to 8 and 10 to 12 applies unchanged, except what
section 2 below lists. In particular these stay:
- the claim under test and the support profile (FROZEN_PROTOCOL.md 1, 2). The profile file is unchanged; its digest
  is in the MANIFEST;
- the matching rules and metrics, through the unchanged `scripts/evaluate_v2.py`;
- **the gates G1 to G11 and every threshold**. English and Arabic **G5c ≥ 0.95** and **G5d ≥ 0.95** are not lowered,
  exempted or reinterpreted;
- the per-language minimum denominators: 50 target identifier occurrences, 80 uses, 60 definitions, 60 linkable
  uses;
- the frozen window (8000 code points from the line of a seeded-random `<ref` opening);
- the bootstrap: 2000 article-cluster resamples, seed 20261028;
- the Clopper-Pearson bounds for the zero-tolerance gates;
- failure accounting: every selected article counts, and none is ever replaced;
- the population: arwiki and enwiki namespace-0 non-redirect articles whose render links to `doi.org`;
- the draw procedure, the sizes, the block-wise ordered reserve and the reserve rule (locked annotation counts
  only);
- the capture driver `../evaluation/scripts/campaign_capture.py`, unchanged, with its run, wait, retry and
  Retry-After rules;
- the annotation, lock, prediction, scoring and adjudication procedure, and the three-model rule:
  - evaluators: Claude Sonnet, at most 6 articles per instance, isolated work directories, raw packets only;
  - adjudicators: Claude Haiku;
  - implementing agent: Claude Opus;
- the briefs `../evaluation/confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md` and `ADJUDICATION_BRIEF_v1.1.md`, used
  unchanged by path.

## 2. What is prospectively different, and why

| Change | Why | Where |
|---|---|---|
| The candidate | the corrected engine (citation-unit classes, engine 1.1.0), after both independent reviews | `../evaluation/confirmation-d035/MANIFEST.json` |
| A new salt | a new, independent random order | section 4 |
| A new exposure set | it now also covers both earlier confirmation campaigns and every file added since | section 4 |
| No warning challenge | section 3 | section 3 |
| A new campaign directory, journal and ceilings | this campaign's network use is counted from zero against its own ceiling (owner instruction section 7) | `../evaluation/confirmation-d035/campaign/` |
| Copied campaign scripts | the 2026-11 scripts stay byte-identical as that campaign's record | `../evaluation/confirmation-d035/scripts/` |

The copied scripts differ from `../evaluation/confirmation-2026-11/scripts/` only in these ways:
- each docstring says it is a copy;
- `select_confirmation.py` has the new salt, empty challenge strata and the campaign name `confirmation-d035`.

`disagreements_challenge_fix.py` is not copied, because without a challenge split it is not needed.

## 3. Strategy: why bilingual, and why without a warning challenge

**Bilingual.** English-only confirmation would not be sufficient. The correction is language-general and changes
Arabic outputs on the exposed data:
- 8 Arabic Harvard calls are no longer citation-template units;
- the Arabic IUCN and EI2 false positives become H and G;
- the new rules for `{{ملا}}` notes and for bibliography entries apply to Arabic exactly as to English.

The Arabic pass of the 2026-11 campaign was a pass of a different engine (`3e51792`). Owner instruction section 10
requires Arabic validity "retained or prospectively re-established where required". The Arabic sample is therefore
drawn fresh, under the same frame, sizes and minimums as in 2026-11. The differential regression on the existing
Arabic data (all retained Arabic bundles, `../design/unit-semantics/differential/`) is reported as well. It is
regression evidence, not fresh validation.

**No warning challenge.**
- The challenge of 2026-11 was added by that campaign's own instruction (D-034 section 8). It is not one of the
  frozen gates, and its sensitivity has no threshold.
- The marker detection code is unchanged by D-035.
- The one marker-related effect of the correction is that a bibliography entry with a new G unit is now matched to
  its rendered list item, so its marker region is inspected.
- G7 (no fabricated negative warning states) is a gate on the holdout. The holdout measures exactly that effect.
- The 2026-11 challenge listed the transclusions of every marker template up to its paging bound, and those page ids
  are now exposed, so an unexposed challenge frame could not be guaranteed.

Sensitivity to genuine warnings therefore stays as measured in 2026-11 on the earlier engine and is not re-measured.
This is stated as a limitation.

## 4. Frame, exclusions and order

**Exposure.** Before the draw, `exposure_set.py` (copied unchanged) is run on the repository at the amendment commit.
It collects every page id and title in any JSON document committed under `docs/verification/stage-03/` or
`tests/stage03/`. That includes the selections, random batches, challenge listings, captures, labels, extractions and
fixtures of every earlier campaign, both confirmation campaigns among them. The output,
`confirmation-d035/campaign/EXPOSURE_SET.json`, is committed before the draw. An exposed page id or title is excluded
in both wikis. An article group is the page id.

**Random draw.** The frozen procedure:
- `list=random` in batches of 500;
- `prop=extlinks` with `elquery=doi.org`;
- at most 6 batches for arwiki and 4 for enwiki;
- per wiki, the draw stops at that wiki's maximum.

It is made once by `confirmation-d035/scripts/select_confirmation.py`, and every answer is kept.

**Order.** Eligible articles are ordered by the SHA-256 of `citerift-stage03-confirmation-d035-2026-11-03-v1|<wiki>|<page
id>`. The order depends only on the page id and the salt, never on the engine, its predictions, any label or any
earlier failure.

## 5. Sample design and reserve

As in 2026-11:

| | arwiki | enwiki |
|---|---|---|
| initial holdout | positions 1-24 | positions 1-16 |
| reserve | positions 25-48, blocks of 4 | positions 17-32, blocks of 4 |
| maximum | 48 | 32 |

- Reserve decisions use `confirmation-d035/scripts/reserve_step.py` on committed locked counts only. Each language
  is decided independently.
- A minimum unmet at the maximum, at a ceiling or at the time limit is reported against the actual denominator as
  **not met**.

## 6. Feasibility, checked before acquisition

**Statistical.** The population, sizes and minimums are those of 2026-11, whose resampling estimates (section 5 of
that amendment) apply: P(all minimums met) is 0.92 at 24 Arabic articles and 0.92 at 20 English articles. The
2026-11 campaign realized:
- Arabic: 24 articles, 103 identifiers;
- English: 20 articles (one reserve block), 50 identifiers.

The English identifier minimum may again need reserve blocks. The maximum of 32 allows four.

**Network.** The 2026-11 campaign used 263 HTTP attempts and 12.6 MB for 54 articles. That count includes its draw
and a 10-article challenge. Without the challenge, a draw plus 40 to 56 articles is expected to need about 160 to
260 attempts. Rate limiting may add about 100. All of this is inside **500 HTTP attempts and 300 MiB of accepted
bodies**, which are hard ceilings for this campaign and not targets. The worst case of an unreported run is
6 attempts and 64 MiB.

**Time.** Acquisition ends at **2026-11-14 23:59 UTC**, the constant of the unchanged capture driver. That is
before the deadline of 2026-11-21.

## 7. Capture and network

As in AMENDMENT_2026-11-02_CONFIRMATION.md section 6, with this campaign's own journal
(`confirmation-d035/campaign/capture/captures.jsonl`) and ceilings:
- the production `citerift-wiki capture --page-id`, pinned to the latest revision at capture time;
- `maxlag`, Retry-After and at least 10 s between requests;
- the project network gate. No other process uses it during the campaign;
- no duplicate captures;
- no other route, identity or host.

## 8. Annotation, prediction, scoring, adjudication

As in AMENDMENT_2026-11-02_CONFIRMATION.md sections 7 and 8, with these specifics.

**Labels.**
- Labels come only from new Claude Sonnet evaluator instances. Each sees its raw packets, guide 1.1 and the
  unchanged brief.
- Evaluators are never told about the engine, its predictions, the D-035 correction or any earlier failure
  classification.
- The executor validates format only.

**Lock.** `evaluate.py lock` per batch. The locks record the candidate revision of the MANIFEST and this amendment's
commit. They are committed before any extraction of those articles.

**Prediction.** One run, by `confirmation-d035/scripts/run_confirmation.py`, after every lock is committed. It uses
the candidate revision recorded in the MANIFEST before the draw. Every extraction is verified and replayed.

**Scores.** `scripts/evaluate_v2.py score` is run on the locked labels and on the adjudicated labels. Gates use the
adjudicated labels. Both sets are published.

**Adjudication.** Disagreements are listed by `confirmation-d035/scripts/disagreements_v2.py`. New Claude Haiku
instances adjudicate them once, under the frozen procedure and the unchanged brief.

**Intervals.** `confirmation-d035/scripts/intervals.py`, with an empty challenge input.

**Evidence audit.** It runs as in 2026-11.

**After the run.** There is no repair, retuning, reselection or rerun. A material defect is preserved and
reported. No further campaign starts.

## 9. Acceptance

Stage 03 moves to `VERIFIED_AWAITING_OWNER_ACCEPTANCE` only when every condition of owner instruction section 10
holds:
- English **and** Arabic G5c ≥ 0.95 and G5d ≥ 0.95;
- every other applicable gate G1 to G11;
- the minimums;
- G2, G3a and G7 at zero;
- full verify and replay;
- valid annotation provenance;
- complete engineering checks;
- green CI on the final head;
- no unresolved critical or high material defect.

Otherwise Stage 03 stays `IMPLEMENTED_NOT_VERIFIED`, and the exact blocker is named. The executor never records
acceptance and never merges.
