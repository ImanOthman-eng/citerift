# Stage 03 session recovery note (2026-10-29)

The Stage 03 work was started in a cloud project session that reached its usage
limit on 2026-10-28. The owner disabled that session's automatic continuation
and asked a new cloud session to resume the existing authorized work (owner
message in this session, 2026-10-29: "Resume the EXISTING authorized CITERIFT
Stage 03 implementation"). This note records what the new session found, what
it could not recover, and what it redid. It is written by the executor; it is
not an owner decision.

## 1. Recovered revision

| Item | Value |
|---|---|
| Previous implementation branch | `claude/project-thread-5bfmq7` |
| Its head on the remote at recovery (fetched 2026-10-29) | `40aaebadd659dbf668b2ad93c708647bef6b1454`, equal to the owner-confirmed SHA; no newer commit |
| New working branch | `claude/beautiful-planck-fm0pya`, fast-forwarded from `main` `94ac4f8` to `40aaeba` (no rebase, reset or force-push); the old branch is left as it was |
| Registry at recovery | Stage 03 `IN_PROGRESS` since 2026-10-28T18:10:34Z; `citerift-gov check`: 0 errors, 0 warnings |
| Full suite at `40aaeba` (Python 3.12, this host) | 1402 passed |

## 2. Material that was never committed and is not available

The previous session kept some material in its own workspace. A new session
cannot reach that workspace, and none of it is in Git:

| Missing material | Consequence | What this session does |
|---|---|---|
| Holdout, reserve and challenge capture bundles, `captures.jsonl`, `capture_states.json` of the first capture pass (`capture_sample.py`, `retry_failed.py`, committed 2026-10-28 23:27 and 23:45 UTC) | the revisions that pass pinned are unknown | the frozen selection (`selection/selection.json`, unchanged) is captured again with the same committed driver; the revisions pinned now (2026-10-29) are the evaluated ones |
| The development capture bundles, the raw development answers (`acquisition.json`) and the calibration "before" outputs, described in `../calibration/CALIBRATION_REPORT.md` as part of an evidence export | the calibration measurements cannot be re-derived from retained bytes | the calibration report stays as written (its numbers are not changed or re-claimed); the 12 development revisions are re-acquired by revision id for the leakage check and the scorer self-test, and labelled as a 2026-10-29 re-acquisition |
| Any evaluator packets, annotations or provenance | none had been locked (no `ANNOTATION_LOCK.json` in Git) | annotation starts from scratch under the unchanged frozen protocol and brief |

## 3. Evaluation independence after the interruption

- Git records no annotation lock, no holdout or challenge extraction, no
  predictions and no scores. `scripts/run_holdout.py` (committed at `6c22258`)
  refuses to extract before the lock is committed.
- This session cannot verify what the previous session's private workspace
  held or ran beyond what Git records. In particular it cannot exclude that a
  holdout capture of 2026-10-28 was opened or extracted by hand there. The last
  engine change (`40aaeba`, RF-07) states that its defect was found by the
  synthetic reconciliation simulation and that the development regression
  digests were unchanged; nothing in Git connects it to holdout data. This is
  disclosed as a residual limitation, not resolved.
- In this session: the holdout captures are taken by the committed driver; the
  executor does not open their source or HTML and runs no extractor on them
  before the annotations are locked and committed. Code reviewers working in
  this session are told not to read the evaluation directory or the captures.
- The frozen protocol, the gates, the annotation guide and the evaluator brief
  are not changed.

## 4. Pinned-revision drift

The frozen protocol pins "the latest revision at capture time". Articles edited
between 2026-10-28 and the recapture are evaluated at their 2026-10-29
revision. The selection (page ids, order, splits) is unchanged; no article is
replaced.
