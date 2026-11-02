# Post-exposure re-extraction after RF-60 (NOT evaluation evidence)

These articles were exposed by the final campaign's single prediction run. Nothing in this directory is a fresh
result, a gate result or a replacement for `../run/` and `../adjudication/`. It shows what the post-exposure repair
RF-60 changes on the same retained bundles, scored by the same frozen scorer against the same locked and adjudicated
labels.

- `extractions/`: `citerift-wiki extract` at `949cdc4` (RF-60) for the 32 final-campaign bundles. Every exit code
  equals the frozen run's (`extract_exits.json`: 31 × 0, 1 × 6 partial for en-1374633449).
- Byte comparison with `../run/extractions/`: 31 documents are byte-identical. Only `en-1377523963.json` differs,
  in the Wiley identifier key and its render witnesses, and in one warning that is no longer raised.
- `scores_post_exposure.json`: `evaluate.py score score_spec.json`, the frozen scorer, unchanged.

Gate rows under the adjudicated labels:

- **en:** G2 is now 0.000 (it was 0.0192 at the frozen candidate). Every en row passes.
- **ar:** unchanged. G5a is 0.914, and the identifier denominator is 33 against the minimum of 50.

Because the articles are exposed, these numbers are post-exposure regression figures on data the repair was
designed from. They do not show that the frozen evaluation passes, and they are not reported as gate results.

Verification and replay (`../adjudication/verify_replay_*.json`):

- **At the frozen candidate `48cfeab`:** all 32 recorded extractions verify (exit 0) and replay identically (exit 0).
  These are gates G8 and G10 for the delivered evaluation.
- **At `949cdc4`:** all 32 verify. Replay reproduces 31 and reports a difference (exit 5) for en-1377523963. That
  is expected: the code changed exactly that document, and it shows that replay detects the change.
