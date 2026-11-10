# D-045: one-time owner-authorized correction of the Stage 01 current-state note

Evidence record for `DECISIONS.md` D-045 (2026-11-10). This is a **one-time, owner-authorized correction of current
metadata**. It is not a reopening of Stage 01, not a scientific re-evaluation, not a new acceptance, not an amendment
to Stage 01 findings and not a change to any historical record.

## Owner authorization

Owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPWUXdMpviEn4TgnzgKGQCtK` (2026-11-10T18:25:11Z): "Owner decision: choose
One-time authorized correction for the stale Stage 01 registry note. Do not create a new Stage 00 notes capability at
this time." The owner gave the replacement text verbatim and limited the change to the Stage 01 `notes` field, the
re-rendered `PROJECT_STATUS.md` line and this documentation.

## Reason

The registry already records Stage 01 as `ACCEPTED_CLOSED`, with implementation, verification and accepted revision
`85da719ac43fc46170310b225c9190b63a046df8`, `HANDOFF.md` and the evidence manifest retained under
`docs/verification/stage-01/`, gates 01-A to 01-G passed, and the owner's acceptance of 2026-10-27 (owner ref
`cmsg_018VCB51nDHP6HXmLU4ea5yP4bEH9RimJDhvHy8S2ABHcU`, history entry 24). The `notes` value was written on 2026-10-25
(commit `b13f910`), before the handoff existed, and still said the handoff had not been supplied. `render-status`
copies it into `PROJECT_STATUS.md` under "Stage notes", so the current status page contradicted the registry state.

No `citerift-gov` command writes `notes`; the analysis is in
`docs/verification/stage-04/review/step6/STEP6_D044_CLOSURE.md` §7. The owner chose this correction over a new
Stage 00 capability.

## Old and new value

Old (stage `01`, `notes`):

> Executed by a separate external agent. The owner reports the investigation was reported externally; its handoff
> has not been supplied to this repository and none of its findings are accepted. The exact evidence file set is
> fixed when the owner delivers the handoff.

New (owner's text, verbatim):

> Executed by a separate external agent. The Stage 01 handoff and supporting evidence are retained under
> docs/verification/stage-01/, verified at revision 85da719ac43fc46170310b225c9190b63a046df8 and accepted by the
> owner on 2026-10-27. This current-state note supersedes the earlier pre-handoff note recorded before Stage 01
> evidence and acceptance were available.

## Exact registry diff

```diff
--- a/governance/stage_registry.json
+++ b/governance/stage_registry.json
@@ -1793,7 +1793,7 @@
         "HANDOFF.md"
       ],
       "ci_required": false,
-      "notes": "Executed by a separate external agent. The owner reports the investigation was reported externally; its handoff has not been supplied to this repository and none of its findings are accepted. The exact evidence file set is fixed when the owner delivers the handoff."
+      "notes": "Executed by a separate external agent. The Stage 01 handoff and supporting evidence are retained under docs/verification/stage-01/, verified at revision 85da719ac43fc46170310b225c9190b63a046df8 and accepted by the owner on 2026-10-27. This current-state note supersedes the earlier pre-handoff note recorded before Stage 01 evidence and acceptance were available."
     },
     {
       "id": "02",
```

The edit was a single exact string replacement of the `"notes": "<old>"` member, checked to occur exactly once; the
old text occurs nowhere else in the registry. `PROJECT_STATUS.md` was regenerated with
`uv run citerift-gov render-status --write`; its only change is the matching "Stage notes" line.

## Proof that no other registry field changed

`verify_d045_registry_diff.py` parses the registry before (`cf2e411`) and after, compares every JSON value, prints
each differing path and exits 0 only if the single difference is `$.stages[01].notes` with exactly the old and new
values above. Observed output:

```
CHANGED $.stages[01].notes
  old: 'Executed by a separate external agent. The owner reports the investigation was reported externally; its handoff has not been supplied to this repository and none of its findings are accepted. The exact evidence file set is fixed when the owner delivers the handoff.'
  new: 'Executed by a separate external agent. The Stage 01 handoff and supporting evidence are retained under docs/verification/stage-01/, verified at revision 85da719ac43fc46170310b225c9190b63a046df8 and accepted by the owner on 2026-10-27. This current-state note supersedes the earlier pre-handoff note recorded before Stage 01 evidence and acceptance were available.'
paths changed: 1; only Stage 01 notes with the D-045 values: True
```

Control: comparing `cf2e411` with itself reports `paths changed: 0` and exits 1, so the script does not pass vacuously.

Unchanged by construction and by the proof: Stage 01 authorization and its historical scope text (including "none of
its findings are accepted", true when recorded on 2026-10-25), implementation, verification and accepted revisions,
gate results, acceptance record, evidence manifest, history, blockers, and all Stage 00–03 artifacts. No file under
`src/citerift/governance`, `schemas/governance` or `tests/stage00` was changed.

## Not done (owner decision)

The dated-notes capability (`notes: {text, recorded_at}`, a `NOTE_PREDATES_STATE` warning, dated rendering) is kept
as a non-blocking governance-hardening candidate, not implemented. Reconsider it only if more stale-note cases appear,
several stages start using mutable current-state notes, or the final release review finds automated stale-note
detection materially useful.
