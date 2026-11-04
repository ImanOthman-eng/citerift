# D-035 labels scored again with the corrected engine (post-exposure regression)

*CITERIFT — Created and Directed by EVE TELOS · IM*

**This is not a gate result and not a confirmation.** The D-035 articles and labels were exposed before the R-038
correction was designed (the Arabic G6b failure is what the correction answers). The published D-035 result stays
as it is: candidate `fff0e5b`, Arabic G6b failed, verdict `BLOCKED_BY_VERIFIED_MATERIAL_DEFECT`
(`../../../evaluation/confirmation-d035/campaign/REPORT.md`). Nothing under `evaluation/confirmation-d035/` was
written by this check.

## Method

`rescore_d035.py` extracts the 48 D-035 bundles again with the corrected engine (isolated workers, default
configuration; the five withheld files of `en-1380218630` present on disk) and runs the frozen scorer
`protocol/scripts/evaluate_v2.py` on the campaign's own two score specifications (locked-only and adjudicated)
with only the extraction paths replaced. Two runs gave byte-identical extractions and scores.
`EXTRACTIONS.sha256` lists the 48 extraction documents; they differ from the D-035 prediction documents in their
version strings for every article and in render pairings for the articles listed in `../DESIGN.md` section 6.

```
uv run python docs/verification/stage-03/design/r038-reconciliation/post-exposure-d035/rescore_d035.py . <out>
```

## Result (adjudicated labels; the locked labels give the same render numbers)

| Language | Render links correct | False attachments | Abstained | G6a | G6b | G6c | Other gates |
|---|---|---|---|---|---|---|---|
| ar, D-035 candidate (published) | 182 / 197 | 2 (allowed 1) | 13 | 0.989 | **fail** | 0.924 | all pass |
| ar, corrected engine | 184 / 197 | 0 | 13 | 1.000 | pass | 0.934 | all pass |
| en, D-035 candidate (published) | 203 / 207 | 0 | 4 | 1.000 | pass | 0.981 | all pass |
| en, corrected engine | 203 / 207 | 0 | 4 | 1.000 | pass | 0.981 | all pass |

Every metric other than the render metrics is identical to the published D-035 scores (identifiers, uses,
definitions, units, markers, in both languages and both label sets). The two corrected Arabic links are the two
false attachments of `ar-76814232` (`Mallama2014`), now attached to their own markers; no abstention was added.

What this shows: the correction removes the observed failure without costing coverage on the data where it was
observed. What it cannot show: performance on unseen articles. That is the purpose of the single D-036 prospective
confirmation.
