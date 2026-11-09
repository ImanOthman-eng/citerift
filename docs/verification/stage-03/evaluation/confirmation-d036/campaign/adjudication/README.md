# Disagreements and adjudication of the D-036 confirmation campaign

- `disagreements.json`: `../../scripts/disagreements_v2.py` (D-036 copy) on `../prediction/score_spec.json` as it was
  before adjudication (kept as `../scores/score_spec.locked-only.json`): 19 disputed items in 9 of the 44 gate
  articles (ar 6, en 3): identifier_missed 5, template_unit_missed 6, unstructured_unit_extra 4, identifier_role 3,
  identifier_key 1. There is no challenge split.
- `items/`: made by the 2026-11 `make_adjudication_items.py`, unchanged, by path: per article the packet files, the
  locked label and the numbered disputed items; no extraction document. Two Claude Haiku instances: `ar-g1`
  (6 articles) and `en-g1` (3 articles).
- `briefs/`: `../../../confirmation-2026-11/ADJUDICATION_BRIEF_v1.1.md` unchanged, with `{LANG}`, `{WORK}` and
  `{INSTANCE}` (`d036-adj-<instance>`) filled in. Each work directory, outside the repository, holds a byte copy of
  guide 1.1, a byte copy of its `items/` (compared with `diff -r`) and an empty `out/`. Items and briefs were committed
  before any adjudicator started.
