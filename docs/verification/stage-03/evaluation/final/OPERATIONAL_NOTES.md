# Final campaign operational record — 2026-10-30

This is the single final campaign authorized by the 29 October amendment.
Production candidate and effective frozen protocol are pinned in MANIFEST.json
before fresh content acquisition. GitHub App write access is unavailable; local
commits preserve the protocol checkpoints, but remote delivery and CI remain
unmet. No new campaign is implied by the executor change.

`selection_final.json` is the unmodified deterministic final_selection.py output.
`capture_initial.json` restricts execution to the first 10 articles per language.
The retained final_capture.py enforces the shared ceilings. Its cumulative log
is seeded with the four capability preflight requests on already-exposed
article groups, conservatively debiting them from this campaign's ceiling.
One fixed host-wide network lock is used throughout. No alternate access route
or 403 bypass is permitted. Failed captures remain selected.

`tools/reserve_step.py` uses the existing reserve_decision.py count functions,
checks committed annotation hashes, and authorizes only the next ordered pair
when counts require it. It pauses for the amendment's bounded Arabic 16th draw
only if the locked first-14 counts need that pair. This changes no metric or
threshold. Annotation helpers and packets are copied to separate external
output directories during the runs, then retained here with hashes.

Evaluator briefs preserve the frozen task text and guide. Only actual paths and
assignment names are substituted; the amendment's helper-directory sentence
and the owner's truthful ChatGPT/Codex attribution requirement are appended.
No engine code, predictions, tests or repair findings are sent to annotators.
The frozen scorer/guide and all earlier cohorts/results remain untouched.
