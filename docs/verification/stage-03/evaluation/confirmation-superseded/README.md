# Confirmation capture of 2026-10-29 (superseded before annotation)

These are the captures of the confirmation articles (selection positions 17-22 per wiki) taken for the single
repair round of FROZEN_PROTOCOL.md section 9, after holdout run 1 and repair RF-36/RF-37. The run began at
09:22 UTC on 2026-10-29. It was stopped once for RF-38 (a client read-loop defect) and then resumed. At the end
of the main pass, 9 of the 12 articles were captured completely. The details are in `capture/capture_notes.txt`
and `capture/orphan_attempts.json`.

The owner's supplemental directive of 2026-10-29 (`../../authorization/OWNER_DIRECTIVE_2026-10-29_SUPPLEMENT.md`)
arrived before this set was annotated. It authorized a further correction batch (F1-F4) and one fresh final
confirmation campaign. This set was therefore never annotated, never extracted for evaluation and never scored. No
bounded retry pass was run on it. It is kept under its actual provenance:

- these articles are **exposed**: they were captured and their source and HTML were stored in this session;
- they are excluded from the final campaign (`../../protocol/AMENDMENT_2026-10-29.md`);
- they are not relabelled as the final campaign.

The capture states include two failures caused by this session's own operations, recorded as such: a concurrent
development re-acquisition held the network gate, and the RF-38 client defect occurred.
