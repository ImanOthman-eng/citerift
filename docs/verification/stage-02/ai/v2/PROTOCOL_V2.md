# Evidence Ambiguity Investigator: AI Protocol v2 (preregistration)

The binding values are in `protocol-v2.json` (part 1, frozen before any model was screened) and
`protocol-v2-frozen.json` (part 2: the model, encoding and wrapper, frozen before the holdout was drawn).
Owner authorization: directive `cmsg_018VCB51nDHP6HXmLU4ea5yPWhxzhgqKQDanXYzuxvEBsT`, section 4. Decision:
DECISIONS.md D-025.

## 1. Why v1 is superseded (classification: admission design infeasible; no model evaluation executed)

v1 (`../protocol.json`) and its baseline score (`../baseline-heldout.json`) stay unchanged. The baseline
scores 110/120 on the v1 holdout, so the largest possible absolute gain is 100 · (1 − 110/120) = 8.33
points, below the required 10. With 60 positives and at most one false selection allowed, selection
coverage is at most 61/120 = 0.508, below the required 0.60. No model was ever run under v1. The
session-agent route pilot (`../route-pilot-2026-10-27.json`) used a synthetic bundle and is historical
only: it is not the product model route. This is not evidence that AI is ineffective. The v1 groups are
now exposed development data.

## 2. Task, unit and label repair

The task is controlled recovery of a masked source identifier. The bundle carries the query record's title,
authors, journal and year, with no identifier, and at most five deterministic candidates. The correct answer
is the candidate that carries the query's original DOI, or abstention when no other record carries it. This
is not natural missing-identifier resolution, and a source-established label is not human adjudication.

The unit is a lineage group (as v1): a connected component of records sharing an original or notice DOI or
PMID, or a Record ID. Each group gives one query (its smallest ordinal with a valid original DOI) and one
decision.

v1 had two label defects, repaired here. Both repairs were decided from record fields, before any model ran:

- **Identity collisions.** Some DOIs are carried by distinct works: 255 conference abstracts share
  `10.1016/s1873-9946(10)00006-1`, and two Brain Injury papers share `10.3109/02699052.2016.1162060`.
  These are excluded as unresolved (`doi_shared_by_distinct_titles`: a target record whose title-token
  Jaccard with the query is below 0.5). So are conflicting identifiers (`conflicting_original_pmid`,
  `pmid_shared_with_different_doi`). Metadata is used only to exclude a case, never to create a link.
- **Stratum versus scoring.** v1 assigned the "disagreement" stratum from the lowest-ordinal target record,
  but scored a selection of the target DOI correct whichever record carried it. v2 assigns the stratum
  from all target records: a positive is "disagreement" only if none of them agrees with the query.

Census (`dev-audit.json`). Of the 160 v1 groups, 4 are now excluded. Fresh eligible groups: 1,508
positives and 55,760 negatives; 10 negatives are excluded.

## 3. Strata, splits and separation

Strata are defined in `protocol-v2.json` from retrieval features only (candidate title cosine, year,
authors). They are never derived from a baseline or model decision.

Excluded from any holdout: the v1 groups, and every group with an event id or DOI named anywhere in the
Stage 02 documents before v2 (868 groups). The remaining fresh groups are split by
`sha256("20261028:<min ordinal>") mod 10`:
- below 3: development;
- otherwise: holdout pool.

The draw checks separation programmatically. No event id or identifier key of a holdout group may occur in
a development or prior group.

## 4. Attainability and power (before any prediction)

Development pool, baseline only (`dev-audit.json`):

| Stratum | n | Baseline errors | Rate (Wilson 95%) |
|---|---|---|---|
| negative / near-duplicate | 225 | 64 | 28.4% (22.9–34.7%) |
| negative / similar-title | 741 | 16 | 2.2% (1.3–3.5%) |
| negative / other | 15,762 | 0 | 0% |
| positive / competitor | 24 | 0 | 0% |
| positive / other | 432 | 0 | 0% |

There are no fresh disagreement positives: all 12 are v1 groups. A uniform 60/60 holdout would therefore
give about 1 baseline error, and no 25% relative reduction could be tested. That repeats v1's mistake.

The preregistered holdout is 300 groups (150 positives, 150 negatives), oversampled by stratum:

| Stratum | Groups |
|---|---|
| positive / other | 110 |
| positive / competitor | 40 |
| negative / near-duplicate | 100 |
| negative / similar-title | 30 |
| negative / other | 20 |

It gives about 29 expected baseline errors. Candidate recall@5 is 1.0 in every development stratum, so an
oracle could fix every baseline error.

Power of the full admission rule, from 29 baseline errors in 300 groups (exact calculation):

| Errors fixed (f) | No new errors (g = 0) | g = 1% | g = 2% | g = 4% |
|---|---|---|---|---|
| 30% | 0.68 | 0.30 | 0.10 | 0.00 |
| 40% | 0.94 | 0.67 | 0.33 | 0.03 |
| 50% | 1.00 | 0.90 | 0.61 | 0.10 |
| 60% | 1.00 | 0.98 | 0.83 | 0.25 |

f is the share of baseline errors the model fixes; g is the share of baseline-correct cases it breaks. So
the experiment is informative only for a model that fixes a large share of the near-duplicate errors
without adding errors elsewhere. A smaller effect will most likely not be admitted. n = 300 alone does not
guarantee adequate power.

At the draw, the attainability rule requires at least 15 baseline errors and a best-case one-sided
p < 0.001. If either fails, the experiment stops before any holdout prediction: no redraw and no quota
change.

## 5. Model screening and freezing (development data only)

- At most two candidates, each screened on the same 40 development cases. No fine-tuning and no sweep.
- The wrapper is "select the top candidate iff score ≥ τ_s and its margin over the second ≥ τ_m". It is
  calibrated on development cases only, by the rule in `protocol-v2.json`.
- One finalist: its artifact hashes, runtime, encoding, instruction and thresholds are frozen in
  `protocol-v2-frozen.json`, committed before the holdout is drawn.

## 6. Metrics, analysis and admission

As listed in `protocol-v2.json`:
- the primary test is an exact one-sided McNemar test on discordant groups;
- effect sizes are reported with bootstrap intervals;
- admission requires all of: at least 120 groups, a relative error reduction of at least 25%, p < 0.05,
  positive recall of at least 60%, no more negative false selections than the baseline, zero critical
  confusions, zero fact writes, and the CPU envelope met.

Each case is scored with independent forward passes, so the case-level paired test fits the unit. The
model runs once on the holdout; failures count as abstentions. Scores are reranker logit differences, not
probabilities.

## 7. Languages

Script of query titles: reported per case (`query_title_script`). The snapshot holds one Arabic-script
record, so there is no Arabic stratum and no Arabic accuracy claim. No translated or synthetic Arabic case
is used.
