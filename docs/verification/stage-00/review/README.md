# Independent reviews of correction A-00-001

Each subdirectory holds one review by a separate reviewer agent that took no
part in writing the correction. The reviewer worked in its own clones and
changed nothing in the repository or on GitHub. Its report and reproduction
scripts are kept byte-for-byte as it wrote them. The scripts refer to the
reviewer's scratch paths (`$W/...`), so they show method and are not meant to
run unchanged. Ruff skips this directory (`pyproject.toml`).

## `ee46423/`: first final review

Verdict: NOT VERIFIED. 260 tests passed, ruff, mypy and `check` were clean.
F-01 to F-23 were partly confirmed fixed (§2 of the report), and 16 new
findings were raised.

The report numbers them N-01 to N-16. The repository calls them **V-01 to
V-16**, because "N-01" was already used in the message of commit `373045d`
for the defect now called S-01. V-*n* is the report's N-*n*.

All sixteen were reproduced. Their regression tests failed on `135e4ac`, with
the corrected tests run against the old code
(`../fail-first/results-135e4ac.txt`: 36 failed, 269 passed). The fixes are in
`5749e9c`.

| Id | Finding | Disposition |
|---|---|---|
| V-01 | partial test run (ini override, other ini file, conftest drop, `collect_ignore`) recorded as complete | fixed: those runs are partial, and every committed test file must have run |
| V-02 | a URL, or one pinned file among unpinned ones, counted as pinned gate evidence | fixed: URLs are not pinned, and each unpinned file is an error |
| V-03 | stage overrides could weaken the schema-fixed policy; handoff not always required | fixed in the schema (artifact list, executor per stage) and in `_artifacts_for` |
| V-04 | CI check run through an entry point that `pyproject.toml` can redirect | fixed: CI runs `python -P -m` from `src`, with a guard step. Residual: `pyproject.toml` and `uv.lock` are not owned (R-016) |
| V-05 | an amendment test report exempted arbitrary files from the manifest | fixed: only enhancement reports are exempt, and others are hash-checked |
| V-06 | memory parser skipped some heading forms | fixed: fields outside a recognised heading are `MEMORY_MALFORMED`; topics are compared after NFKC, separator and case folding |
| V-07 | owner-reference reuse checked only against history | fixed for amendments (case 3). Cases 1 and 2, one message covering several decisions, are allowed by design (GOVERNANCE.md invariant 2, R-002) |
| V-08 | one correction amendment justified several reopenings | fixed: `HISTORY_AMENDMENT_REUSED` |
| V-09 | duplicate amendment and blocker ids accepted | fixed: `AMENDMENT_DUPLICATE_ID`, `BLOCKER_DUPLICATE_ID` |
| V-10 | remaining tracebacks (schema missing or damaged, `{}` registry, undecodable memory) | fixed: named errors, exit 1 |
| V-11 | default times could precede the last history entry | fixed; R-012 now states that a fast clock still blocks (detected, fail closed) |
| V-12 | a nested `.gitattributes` changed evidence hashes | fixed: `ATTRIBUTES_NESTED` error for a tracked nested file |
| V-13 | `git replace` hid owned-path drift | fixed: every git call uses `--no-replace-objects` |
| V-14 | ruleset and fixture tests read JSON last-key-wins | fixed: `loads_strict`. No fail-first run is possible, because the defect is in the test itself; reproduced by hand |
| V-15 | test gaps in the new checks | tests added. They pass on the old code by design, because they kill mutants rather than reproduce a defect |
| V-16 | a report into a missing directory crashed the plugin | fixed: the directory is created |

The report's §7 items that it did not reproduce are not counted as findings.
`collect_ignore` is now covered by V-01's file enumeration.
