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

## Adjudication (2026-11-03)

- Five Claude Haiku instances (`cf11-adj-ar-g1`, `ar-g2`, `en-g1`, `en-g2`, `en-c1`) decided the 113 disputed items
  under the filled briefs in `briefs/` (inputs `items/`, committed in `6c2b544` before they started).
- `validate_adjudication.py` (format only: every item decided once with a reason; the adjudicated file passes the
  label check; the JSON paths changed from the locked label are listed) passed for four instances. For
  `en-1329904848` the first submission (`en-c1`) gave no reason for items 1 to 20. Under section 7 it was returned to
  a new instance of the same role, `cf11-adj-en-c1b`, with the validation message (`briefs/en-c1b.txt`); its result
  is used. The returned submission is kept in `returned/en-c1/`. Both instances made the same single correction.
- Result (`decisions/`, `adjudicated/`, `ADJUDICATION_VALIDATION.json`): 104 items confirmed, 9 corrected
  (ar: 2 identifier keys lower-cased under guide 3.5, 1 marker `none` to `cannot_tell` for an unrendered footnote,
  1 template location moved to its own reference; en gate: 2 `[[doi:…]]` interwiki links from
  `labeled_reference_text` to `identifier_link`; en challenge: 2 Gaia EDR3 erratum notes from `none` to
  `ambiguous`). The changed JSON paths match the corrections the instances reported.
- `ADJUDICATOR_AUDIT.json` (same audit as for the evaluators): no tool call outside the instance's work directory,
  no git/uv/network command; the harness again attached the repository `CLAUDE.md` to each context.
- `adjudicator_tools/` keeps the instances' helper scripts with `.txt` appended.
