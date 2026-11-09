# Holdout and challenge prediction run 1 (2026-10-29)

The only prediction run of the frozen protocol on these articles (FROZEN_PROTOCOL.md section 9). It ran at commit
`66d323a` (`prediction_revision.txt`), after the annotations were locked and committed in that same commit, via
`../scripts/run_holdout.py ../capture ../annotations/locked <out>` from 09:16:59 to 09:18:08 UTC.

| File | Content |
|---|---|
| `extractions/<wiki>-<revision>.json` | the engine's extraction document per captured article (38) |
| `runs.json` | per article: capture state and the `extract`, `verify --extraction`, `replay --extraction` commands, exit codes, wall times and outputs |
| `score_spec.json` | the driver's spec (all splits) |
| `score_spec_gates.json` | the spec actually scored: holdout = holdout positions plus the reserve articles of `../annotations/RESERVE_DECISION.json`, observed challenge separately; the four arwiki reserve articles the rule did not need are excluded |
| `scores.json` | `../../protocol/scripts/evaluate.py score score_spec_gates.json` on the locked labels (before adjudication) |
| `disagreements.json` | `../scripts/disagreements.py score_spec_gates.json`: every item counted as an error, for adjudication |

Paths inside the JSON files point to the session scratchpad where the run was made; the same files are here and in
`../capture/bundles/` and `../annotations/locked/`.
