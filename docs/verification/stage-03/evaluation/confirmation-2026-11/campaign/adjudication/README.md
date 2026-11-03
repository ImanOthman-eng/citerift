# Disagreements and adjudication of the confirmation campaign

- `disagreement_spec.json`: `../prediction/score_spec.json` (split `gate`, 44 articles) plus the challenge articles
  of `../prediction/challenge_spec.json` as split `challenge` (10 articles), as `disagreements_v2.py` expects.
- **Tool defect found here (2026-11-03, after the prediction run).** The frozen `disagreements_v2.py` ends in a
  RecursionError on a `challenge` split (`disagreements_v2-challenge-recursion.stderr.txt`, empty stdout): its
  replacement of `evaluate.load_bundle` is called again by `warning_challenge.load`. The gate split is not affected.
  The frozen files were left byte-identical. `../../scripts/disagreements_challenge_fix.py` runs the frozen
  `items` with a `warning_challenge.load` bound to the original loader; its tests are
  `tests/stage03/test_disagreements_challenge_fix.py` (the frozen function recurses; the wrapper lists a challenge
  split with the challenge window; on a gate split it equals the frozen result).
- `disagreements_v2-gate-only.json` (frozen tool, gate split only) and the gate part of `disagreements.json`
  (wrapper, both splits) are identical.
- `disagreements.json`: 56 disputed items in 44 gate articles and 57 in 10 challenge articles. These go to the
  adjudicators (Claude Haiku) under `../../ADJUDICATION_BRIEF_v1.1.md`.
