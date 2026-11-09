# Stage 04 owner authorization (retained record)

This is a short summary record. It is not a transcription of the owner's message. The owner asked for a minimal
record and not a copy of the conversation (owner instruction of 2026-11-09,
`cmsg_018VCB51nDHP6HXmLU4ea5yPPExKYg1WPyjb82BfbKrqGQ`). The platform message is the authoritative text. This file
copies the facts below for audit; it is not a signature (RISKS.md R-002).

| Field | Value |
|---|---|
| Stage | 04 — Detection Engine and Vertical Slice |
| Owner | EVE TELOS |
| Owner authorization reference | `cmsg_018VCB51nDHP6HXmLU4ea5yPFrh5szvKs3Wf6aVj3k31gR` (sent 2026-11-09T20:30:09Z, platform time) |
| Registry entry | history seq 49, `NOT_STARTED -> AUTHORIZED`, actor `owner`, recorded by the engineering agent, at 2026-11-09T20:38:17Z |
| Start entry | history seq 50, `AUTHORIZED -> IN_PROGRESS`, actor `engineering-agent`, at 2026-11-09T20:38:32Z |
| Base main revision | `741df40c408d9d68d9805f901ef0d82b523cdb2c` (main after PR #6) |
| Authorization commit | `92312be529334e151182ceb2cff47be16f63434e` on branch `claude/stage04-detection-engine` |

## Authorized scope

- Stage 04 only: Detection Engine and Vertical Slice, as defined by the stage registry
  (`governance/stage_registry.json`, gate 04-A) and the project's architecture.
- Record of the authorization and start state through `citerift-gov` (done in the authorization commit).
- The owner's follow-up instruction of 2026-11-09 (`cmsg_018VCB51nDHP6HXmLU4ea5yPPExKYg1WPyjb82BfbKrqGQ`) limits
  the current step to reconstruction, an integration and inherited-gap audit, and a Master Execution Plan, plus
  this record. It does not authorize implementation of the Detection Engine yet.

## Not authorized

- Stages 00, 01, 02 and 03 remain `ACCEPTED_CLOSED` at their accepted revisions. They are not reopened or
  modified. A correction to material they own needs its own owner-authorized amendment or maintenance under
  GOVERNANCE.md.
- Stage 05 and every later stage are not authorized.
- No merge to `main`: the owner merges personally (D-019).
