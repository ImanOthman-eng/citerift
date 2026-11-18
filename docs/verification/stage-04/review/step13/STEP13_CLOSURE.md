# Stage 04 Step 13: evaluation pre-registration (closure record)

Owner authorization `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6` (2026-11-18T08:19:10Z).

**Status (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP2Hk5yHet3jmkhGoVf9yZD5`, 2026-11-18T12:04:37Z, recorded as
D-070): the pre-registration is accepted exactly as committed, and Step 13 is ACCEPTED AND CLOSED.**

| Accepted record | Value |
|---|---|
| Pre-registration commit | `827ac1aa1d9d16d444d4860e4119f8633d8e802e` |
| Pre-registration digest P | `4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a` |
| CI on the exact commit | run 341 (id 44279592605), accepted |
| Frozen engine (unchanged) | `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` |
| Stage 03 listed tier | kept in the frame, exactly as registered (owner choice of PREREGISTRATION section 15.1) |

The pre-registration files are not edited to record the acceptance: any edit would change P. Its status line
("SUBMITTED FOR OWNER ACCEPTANCE") is superseded by this record and D-070.

## Seed round fixed by the acceptance message

The acceptance message's timestamp is 2026-11-18T12:04:37Z. By the registered rule (`s13_draw.round_for`), the seed
round is the first drand quicknet round whose time is at least 13:04:37Z: round **34067905** (13:04:39Z). The previous
round, 34067904, is at 13:04:36Z, so a sub-second part of the timestamp cannot change the round.

## Next

Step 14 only, strictly under P: seed, draw, acquisition, packets, A/B annotation, adjudication, locks committed and
hashed, then the one frozen-engine prediction run, scoring, baseline and sensitivity variants. Step 15 does not start
until the Step 14 campaign is presented for owner review.
