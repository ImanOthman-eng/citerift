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
