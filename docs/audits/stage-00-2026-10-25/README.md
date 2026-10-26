# Stage 00 independent audit, 2026-10-25

Evidence for correction amendment A-00-001 (governance/stage_registry.json).

- `independent-review.md`: the independent reviewer's report on Stage 00 as
  accepted at `741476c` (main `c8618a3`), with the reproduction command and
  observed output for every finding F-01 to F-23. Paths such as `$S/exp/...`
  refer to throwaway clones in the reviewer's session and are not in this
  repository.
- `scripts/`: the reviewer's probe scripts, kept as they were run.

The engineering agent re-ran F-01, F-02, F-03, F-05, F-06, F-08, F-09 and F-10
in separate clones before the correction started. The owner authorized the
correction in project message `cmsg_018VCB51nDHP6HXmLU4ea5yPXk8eZcAUfir9fZgszrLxhk`.
Each finding's disposition is recorded in
`docs/verification/stage-00/TEST_RESULTS.md` of the corrected verification.
