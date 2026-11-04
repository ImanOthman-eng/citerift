# Evaluation captures (2026-10-29)

Captured by `../scripts/capture_sample.py` (selection `../selection/selection.json`, splits holdout, challenge,
reserve) and one bounded retry pass `../scripts/retry_failed.py`, through the production `citerift-wiki capture`
CLI and its network policy. See `../RECOVERY_NOTE.md` for why the 2026-10-28 captures are not available.

| File | Content |
|---|---|
| `bundles/<split>/<wiki>-<page id>-a<attempt>/` | every published capture bundle (also superseded attempts); `citerift-wiki verify --bundle` checks each |
| `captures.jsonl` | every capture attempt: argv, exit code, the CLI's stdout JSON, stderr |
| `capture_states.json` | per selected article: all attempts and the final state (FROZEN_PROTOCOL.md G9) |
| `capture_states.snapshot*.json` | the states file as read when evaluator packets were built (before and after the retry pass) |
| `capture_code_revision.txt`, `capture_started_at.txt`, `capture_finished_at.txt`, `capture_notes.txt`, `capture_driver.stderr` | code revision at the start of the run, times, notes and the driver's progress log |

The JSON files record the bundles under the session scratchpad path
(`/tmp/claude-0/…/scratchpad/eval/bundles/…`); that prefix corresponds to `bundles/` here. The capture code was
`e9b7cfa` for the main pass (the fetch, capture and bundle modules are unchanged between `40aaeba` and `e9b7cfa`)
and `d626c06` for the retry pass (after the RF-24 to RF-29 network fixes).

The source wikitext and rendered HTML are Wikipedia content under CC BY-SA 4.0 (and GFDL where applicable); the
page and revision of each bundle are in its `capture.json`.
