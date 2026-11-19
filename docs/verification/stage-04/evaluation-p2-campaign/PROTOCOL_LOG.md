# Stage 04 Step 14 under P2: protocol log

Append-only record of how the campaign is executed under the accepted pre-registration P2
(`5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a`, commit `10cc9d8`, D-077), including every
deviation, however small. Nothing here changes a pre-registered rule. The historical campaign
(`../evaluation-campaign/`) is a separate, immutable record; nothing of it is read, reused or combined here.

## Campaign location and executor glue

- Campaign directory `docs/verification/stage-04/evaluation-p2-campaign/`, a sibling of `evaluation-p2/`, so the P2
  manifest (every file under `evaluation-p2/`) is unaffected.
- `executor/p2c_batches.py` (not pre-registered) is the historical `s14_batches.py` with the P2 paths and tool names
  (`p2_labels`, `p2_common`, the P2 guide and parameters) and nothing else changed. It only builds work directories,
  copies label files and records instance metadata; it never reads, decides or changes a label's content.
- Index: the Stage 02 index of snapshot `rw-2f116e9ffed718e6` used by P2's development run (file SHA-256
  `abedb94e…`), outside the repository; the prediction run verifies it per process (D-064).

## Seed

- Owner acceptance of P2: message `cmsg_018VCB51nDHP6HXmLU4ea5yP6Ugyq1ZbRyyuDXEcx5N7Bh`, sent 12:16:15Z, stored
  12:16:16Z. The two timestamps select different rounds under the registered rule; the owner fixed round 34096937
  (13:16:15Z) at 12:18:57Z, before either round existed (D-078). `p2_draw.py seed --acceptance-time
  2026-11-19T12:16:15Z` computes the same round.
- Fetched at 13:16:50Z with the registered tool: `api.drand.sh`, `api2.drand.sh` and `api3.drand.sh` agreed
  (randomness `8402f166…3772` = SHA-256 of the signature, checked by the tool); `drand.cloudflare.com` answered HTTP
  403 (as in the historical campaign). All four answers are in `SEED.json`. Seed
  `b45666399e691ab6a1301086d33eb5f6b776748e6e0504a5399a407aaaba4e6c`.

## Round `primary`

- Acquisition 13:19Z to 14:23Z (`p2_acquire.py acquire --round primary`): 60 of 60 positions acquired (ar 22 S1 + 8 S2,
  en 22 S1 + 8 S2), 0 failures, 0 replacements, 0 `EXPOSED_AT_CAPTURE`; 60 attempts of 200. 103 items; 1 article
  without items.
- Annotation: 10 batches per role (ar 5, en 5; at most six articles of one language each), one new Claude Code agent
  per instance, model `sonnet` (platform model `claude-sonnet-5-5` for every instance), started 14:25Z with the P2
  brief text filled in (`rounds/primary/briefs/`). Work directories are outside the repository (scratchpad). A and B:
  103 labels each, every file format-valid on the first submission (`p2_labels.py check`).
- Disagreements: 8 items (ar 5, en 3), adjudicated by 2 ADJ instances (`ADJ-ar-p01`, `ADJ-en-p01`); their labels are
  final as written (the executor never edits a label).
- Every tool call of every primary instance was checked for paths: none read or wrote outside its work directory (the
  only path-like strings outside it were JSON field lists inside helper snippets, such as `/journal/year`).
- Instance `B-ar-p05` ended without a final reply through the platform's hand-back channel; its label file was complete
  and format-valid, and its transcript is recorded like every other.
- Lock: 103 items, 8 adjudicated (`rounds/primary/LOCK.json`).
- Expansion decision (`p2_acquire.py status`, engine-independent, after the lock): ar identifier-reached
  truth-positive units 27 (< 40), negative-proxy units 427; en 27 (< 40) and 1208. Both languages expand:
  `ar-expansion-1`, `en-expansion-1`.
