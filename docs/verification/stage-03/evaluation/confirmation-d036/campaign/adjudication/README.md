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

## Adjudication (2026-11-09)

- Two Claude Haiku instances (`d036-adj-ar-g1`, `d036-adj-en-g1`; the model is recorded in each transcript) decided
  all 19 items; transcripts 13:09:09 to 13:11:40 UTC (ar-g1) and 13:09:09 to 13:10:56 UTC (en-g1). Each first
  message equals its brief file exactly.
- The 2026-11 `validate_adjudication.py`, unchanged, passed for both at first submission
  (`ADJUDICATION_VALIDATION.json`). No submission was returned or edited.
- Result (`decisions/`, `adjudicated/`, byte copies of the instances' `out/`): **16 confirmed, 3 corrected**.
  - `ar-73440513` item 1 (`identifier_key`): key `10.2305/iucn` corrected to `10.2305/iucn.`; the adjudicator read
    the final `.` of the display text as part of the DOI, which continues in the next link displays, not as
    sentence punctuation. Changed path `.identifiers[4].key`. This correction decides Arabic G2: with the locked
    label G2 is 1 key error in 52 (0.0192 > 0.01); with the adjudicated label it is 0.
  - `en-1377158630` item 0 (`identifier_missed`): the quote of a DOI in a `microbiologyresearch.org/content/…/10.…`
    URL moved from the whole URL to the identifier text (guide 3.5: the whole URL only for a `/doi/10.` path); role
    and key unchanged. Changed paths `.identifiers[3].at.cp`, `.identifiers[3].at.quote`.
  - `en-1377880902` item 1 (`unstructured_unit_extra`): note `d3`, which gives figures with a labelled link to their
    source, corrected to an unstructured citation unit (`.definitions[2].unstructured` false to true); the
    adjudicator called it borderline. Items 2 and 3 of the same article (links that explain a term) were confirmed
    as not citations, also called borderline.
  - Every changed path matches the reported correction.
- `ADJUDICATOR_AUDIT.json` (the evaluator audit on the two transcripts): 15 and 16 tool calls, none flagged (no path
  outside the work directory, no git/uv/network/CITERIFT command); the harness attached the repository `CLAUDE.md`
  to each context.
- `adjudicator_tools/` keeps the instances' helper scripts with `.txt` appended.
- The specs were rebuilt with `run_confirmation.py spec` (no extraction repeated); `../scores/adjudicated.json` is the
  gate result. The locked-label section of the scores is unchanged.
