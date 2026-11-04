# Disagreements and adjudication of the D-035 confirmation campaign

- `disagreements.json`: `../scripts/disagreements_v2.py` (D-035 copy) on `../prediction/score_spec.json` as it was
  before adjudication (kept as `../scores/score_spec.locked-only.json`): 46 disputed items in 11 of the 48 gate
  articles (ar 7, en 4). There is no challenge split, so the 2026-11 recursion wrapper is not used.
- `items/`: made by the 2026-11 `make_adjudication_items.py`, unchanged, by path: per article the packet files, the
  locked label and the numbered disputed items; no extraction document. Committed in `86ef77a` with the filled briefs
  (`briefs/`, `ADJUDICATION_BRIEF_v1.1.md` unchanged) before any adjudicator started.

## Adjudication (2026-11-03)

- Three Claude Haiku instances (`d035-adj-ar-g1`, `ar-g2`, `en-g1`) decided all 46 items, started 16:40 UTC.
- The 2026-11 `validate_adjudication.py`, unchanged (format only: every item decided once with a reason; the
  adjudicated file passes the label check; the JSON paths changed from the locked label are listed), passed for all
  three at first submission (`ADJUDICATION_VALIDATION.json`). No submission was returned.
- Result (`decisions/`, `adjudicated/`): **45 confirmed, 1 corrected**. The correction (ar-g2, `ar-76752816`): the
  quote of a DOI in a `link.springer.com/chapter/10.…` URL moved from the whole URL to the identifier text, under
  guide 3.5 ("anything else: the identifier text"); role and key unchanged. The changed JSON paths
  (`.identifiers[0].at.cp`, `.identifiers[0].at.quote`) match the reported correction.
- Among the confirmed items are the two render links of `ar-76814232` (`Mallama2014`, an infobox whose rows render
  in another order than the source): the locked label assigns `cite_ref-Mallama2014_4-1` to the definition in the
  B−V row (source cp 1897) and `…_4-0` to the reuse in the U−B row (cp 2467); the render shows the U−B row first.
- `ADJUDICATOR_AUDIT.json` (the evaluator audit on the adjudicator transcripts): no tool call outside the instance's
  work directory, no git/uv/network command; the harness attached the repository `CLAUDE.md` to each context. The
  final report of ar-g2 ends with the governance line "VERIFIED COMPLETE" from that file, which has no meaning here.
  ar-g2 also observed that the self-reported `started_at`/`finished_at` of three locked labels are inconsistent;
  those fields are the evaluators' own statements (`../annotations/EVALUATOR_RUNS.md`, "Self-reported times").
- `adjudicator_tools/` keeps the instances' helper scripts with `.txt` appended.
- The specs were rebuilt with `run_confirmation.py spec` (no extraction repeated); `../scores/adjudicated.json` is
  the gate result. The locked-label section of the scores is unchanged.
