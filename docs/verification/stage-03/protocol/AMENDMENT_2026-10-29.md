# Additive amendment to the Stage 03 evaluation protocol (2026-10-29)

Authority: the owner's supplemental directive of 2026-10-29
(`../authorization/OWNER_DIRECTIVE_2026-10-29_SUPPLEMENT.md`, DECISIONS.md D-031). Under it, one additional
correction batch (F1-F4 and other material in-scope defects) is followed by one fresh final confirmation campaign.
FROZEN_PROTOCOL.md section 9 says that further rounds go to the owner; this directive is that owner decision, for
this cycle only.

This amendment is written and committed after holdout run 1 and its adjudication, and before any final-campaign
article is chosen, captured, annotated or extracted. It does not change FROZEN_PROTOCOL.md, the annotation guide,
the scorer (`scripts/evaluate.py`), the old selection, locks, annotations, predictions, scores or adjudications. All
of them stay published. It adds the rules below for the final campaign only.

## 1. What stays exactly as frozen

- the metric definitions, units and matching rules (FROZEN_PROTOCOL.md sections 5 and 6);
- the per-language gates G1-G11 and their values (7.1);
- the minimum denominators per language (7.2): 50 target identifier occurrences, 80 uses, 60 definitions and 60
  linkable uses;
- uncertainty reporting: 2000 article-cluster bootstrap resamples, seed 20261028;
- failure accounting;
- the annotation guide and the evaluator brief text;
- the scorer, unchanged (`evaluate.py score`);
- the reserve rule;
- the adjudication procedure (section 4.5 and `../evaluation/ADJUDICATION_BRIEF.md`).

## 2. Eligible pool and order (fixed now, independent of the engine)

The pool is the unused candidates of the original draw in `../evaluation/selection/selection.json`
(`splits.<wiki>.unused`), in the order they are stored there. That is the frozen order of
`select_sample.py` (SHA-256 of `citerift-stage03-holdout-v1|<wiki>|<page id>`), continuing after position 22. The
exposure inventory (`../evaluation/EXPOSURE_INVENTORY.md`) found none of them exposed. The pool holds 15 arwiki and
36 enwiki candidates.

- **Final holdout:** pool positions 1-10 per wiki.
- **Final reserve:** pool positions 11-16 per wiki. arwiki has only 15 pool candidates, so its position 16 does not
  exist yet. It is drawn only if the reserve rule needs it (section 4).
- Every selected article counts in acquisition success. A failed capture is never replaced by another article.

## 3. Capture

The capture uses the production `citerift-wiki capture --page-id` through `../evaluation/scripts/capture_sample.py`
with a final-campaign selection file (`../evaluation/final/selection_final.json`). It is derived mechanically from
section 2 by `../evaluation/scripts/final_selection.py`. One bounded retry pass follows
(`../evaluation/scripts/retry_failed.py`, with its committed transient set). No other process uses the network gate
during the campaign.

Ceilings for all additional network work of this campaign together (selection draw, captures, retries):

- 500 HTTP attempts;
- 300 MiB of accepted bodies.

Old, additional and cumulative costs are reported separately.

## 4. Reserve rule for the final campaign

FROZEN_PROTOCOL.md 7.2 applies unchanged. The final holdout starts with 10 articles per wiki. Reserve articles are
added in order, two at a time, while the locked annotation counts fall short of any minimum, up to 16 articles per
wiki. The decision is computed by `../evaluation/scripts/reserve_decision.py` from locked labels only.

To save time, the reserve articles may be annotated before the decision. Those the rule does not need stay locked
and published but are not scored.

If arwiki needs a 16th article, one bounded new draw is made:

1. the procedure of `select_sample.py`, at most 2 batches of `list=random` with the `extlinks` filter;
2. every exposed group and every pool candidate is excluded;
3. eligible articles are ordered by the SHA-256 of `citerift-stage03-final-v1|ar|<page id>`;
4. the first one is taken;
5. every response is logged.

If 16 articles still do not reach a minimum, the affected gate is reported against the actual denominator and is
not met.

## 5. Annotation

- Separate evaluator instances receive the unchanged brief and guide. Each also receives one added line, recorded
  in `../evaluation/final/briefs/`: "Put any helper script only under `{OUT}/tools/`; do not create or use any other
  directory." Run 1 showed instances sharing a scratch helper folder; this line gives each instance its own.
- The packets contain the raw artifacts and the window only.
- The annotations and `ANNOTATION_LOCK.json` are committed, together with the reserve decision, before any
  final-campaign extraction. The lock also records the candidate engine revision and this amendment's revision.

## 6. One final prediction run

The production candidate is frozen at a committed revision, recorded in `../evaluation/final/MANIFEST.json`
before the final pool is captured. Predictions are produced once, by that revision, through
`../evaluation/scripts/run_holdout.py` (which refuses to run before the lock is committed). They are scored by the
frozen `evaluate.py`. Disagreements are listed by `disagreements.py` and adjudicated once by new adjudicator
instances. Gates use the adjudicated labels, and both label sets are published.

Supplementary, not gates:

- `relocation_in_window.py`, a correction of the frozen A/B/C use count, published beside the frozen figure;
- the costs measured by `measure_holdout.py`.

## 7. What decides the result

The final campaign's adjudicated per-language gates G1-G11 decide 03-G for the delivered engine. Holdout run 1 stays
published as a failed earlier result; it is not called fresh, and it is not overwritten.

If the final campaign exposes another material defect, the defect is preserved and reported to the owner with the
exact decision needed. There is no further repair-and-rerun on these articles, and no rerun is called fresh.
