# Stage 04 Step 14: protocol log

Append-only record of how the campaign was executed under the accepted pre-registration
(P = `4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a`, D-070), including every deviation, however
small. Nothing here changes a pre-registered rule.

## Seed and draw

- Owner acceptance message 2026-11-18T12:04:37Z; seed round 34067905 (13:04:39Z). Fetched at 13:05Z:
  `api.drand.sh`, `api2.drand.sh`, `api3.drand.sh` agreed (randomness = SHA-256 of the signature checked by the tool);
  `drand.cloudflare.com` answered HTTP 403. All four answers are in `SEED.json`.

## Executor glue

- `executor/s14_batches.py` (not pre-registered) only builds work directories, copies label files and records
  instance metadata. Batching: per language, articles with at least one item in name order, at most six per instance.
- Instances were started with the Claude Code agent tool, model `sonnet`, one new agent per instance, with the brief
  text of `ANNOTATOR_BRIEF.md` / `ADJUDICATOR_BRIEF.md` filled in (`rounds/<round>/briefs/`). Platform model per
  transcript: `claude-sonnet-5-5` for every instance.
- Transcripts: the committed copy keeps every user and assistant record and the platform `model` attachment; platform
  context attachments (system prompt snapshots, tool listings, environment, organization and session identifiers) are
  left out of the public repository, with the original file's SHA-256 and line count in `INSTANCES.json`.
- The platform gives each instance some context of its own, outside the brief: the repository `CLAUDE.md`, a tool
  listing (including the project thread tools), and a queued copy of the owner's acceptance message. No Stage 04
  output existed for any sampled article at any point, so none could be seen.
- Several instances wrote placeholder `started_at` / `finished_at` values (they said so); the platform timestamps are
  `first_timestamp` / `last_timestamp` in `INSTANCES.json`.

## Round `primary`

- 60 of 60 positions acquired, 0 failures, 0 replacements; 59 articles with items (127 items), 1 without items.
- A and B: 10 instances each, every file format-valid on the first submission; 11 items disagreed.
- Adjudication: 2 instances. `ADJ-ar-p01` once tried to write the clock time to `/tmp/x` (outside its work directory);
  the platform denied it, and it then wrote only its label file. No read outside a work directory was found in any
  primary transcript (every tool call's paths checked).
- `A-en-p01` called the project thread's "no reply needed" tool once at its end (it posts nothing).
- Lock: 127 items, 11 adjudicated (`rounds/primary/LOCK.json`).
- Expansion decision (`s13_acquire.py status`, engine-independent): ar identifier-reached truth-positive units 33
  (< 40), negative-proxy units 1110; en 31 (< 40) and 807. Both languages expand: `ar-expansion-1`, `en-expansion-1`.
