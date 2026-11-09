# A-03-001: Stage 03 maintenance transaction (fail-closed accepted-contract test)

Owner authorization: owner decision D-2 in the Stage 04 thread, 2026-11-09
(`cmsg_018VCB51nDHP6HXmLU4ea5yPRpb2tWYwbQwCYA5ps9aLth`). That message is the authorization; this file records what
was done under it. Mechanism: the maintenance transaction of D-024 (model in
`docs/verification/maintenance/A-00-002/MAINTENANCE_MODEL.md`), unchanged. Stage 03 is not reopened and its
acceptance is not rewritten. Decision record: DECISIONS.md D-039.

## 1. Defect [verified]

| Item | Fact |
|---|---|
| Test | `tests/stage03/test_wiki_properties.py::test_accepted_contract_schemas_are_untouched` (Stage 03 owned path) |
| Accepted form | `git diff --name-only c3346d1 -- schemas/contracts`; `pytest.skip(...)` when git fails |
| `c3346d1` | "Stage 03: record owner authorization and start work" (2026-10-28), on the PR #5 lineage only; not an ancestor of `main` |
| Effect | In a clone holding only the `main`/Stage 04 history the protection is skipped, **also when contract drift is present** (section 3). It passed in CI only because `fetch-depth: 0` fetched the side branches that still exist |
| Second gap | `git diff` does not list untracked files, so a new file under `schemas/contracts/` was not reported |
| Contracts | `schemas/contracts` tree `9b4c3a00…` is identical at `0c21182`, at `c3346d1` and at `59bc7ea`: no contract has changed |

## 2. Patch (candidate `d24ea4da15c1dbd3d804904d72e3a8200657f47b`)

One owned file changed: `tests/stage03/test_wiki_properties.py`. No contract schema, no engine code, no other
owned file.

- The baseline is Stage 00's accepted revision `0c21182e5871f772c3a76c75a1217c7641a63bbb` (registry, Stage 00
  verification), written as the full SHA. It is an ancestor of `main`.
- `contract_schema_drift(root, baseline)` requires `git rev-parse --verify <baseline>^{commit}` to return exactly
  that SHA. Otherwise the test **fails** (`pytest.fail`), never skips. A git error during comparison also fails.
- Drift = changed or deleted tracked files (`git diff --name-only -z --no-renames <baseline> -- schemas/contracts`)
  plus untracked, non-ignored files (`git ls-files --others --exclude-standard`). Git runs with replace objects and
  grafts disabled, as the governance check does.
- Two regression tests on a scratch repository: an unresolvable baseline (all-zero SHA, a short SHA, `HEAD`, and a
  directory that is not a repository) fails; a modified, a deleted and an untracked contract file are each reported,
  and a change outside `schemas/contracts` is not.

Consequence, stated plainly: a shallow clone, or any checkout without the `main` history, now fails this test. That
is intended (fail-closed). CI checks out with `fetch-depth: 0`.

## 3. Fail-first demonstration [verified]

`fail_first_demo.sh` clones only the Stage 04 branch (`git clone --no-local --single-branch`, so none of the PR #5
or Codex side branches), plus a depth-1 clone that lacks the baseline, and runs the test from the old revision
`59bc7ea` and the candidate `d24ea4d`. Drift = one byte appended to `v1/common.schema.json` and a new untracked
`v1/injected.schema.json`. Output: `fail_first_demo.log`.

| Revision | Single-branch clone, no drift | Same, drift injected | Shallow clone (baseline missing) |
|---|---|---|---|
| `59bc7ea` (accepted test) | skipped | **skipped (defect)** | skipped |
| `d24ea4d` (candidate) | passed | failed | failed |

## 4. Transaction record

| Step | Record |
|---|---|
| Baseline | `b93314dfde749a7cf977744a44b70a3a0d900ef2` (Stage 03 accepted revision; unchanged) |
| P (candidate) | `d24ea4da15c1dbd3d804904d72e3a8200657f47b` |
| prepare | `citerift-gov maintenance prepare 03 --candidate d24ea4d… --path tests/stage03/test_wiki_properties.py --owner-ref cmsg_018VCB51nDHP6HXmLU4ea5yPRpb2tWYwbQwCYA5ps9aLth` gave A-03-001, `pending_validation`, recorded 2026-11-09T21:29:29Z, `opened_after_seq` 50, file SHA-256 `ef0eca92…67dc8`, patch digest `05428f89…4ebf3`; check: 0 errors, 1 warning (`MAINTENANCE_PENDING`) |
| V (validated) | see section 5 |
| Validation | complete suite on a clean single-branch clone of V, Python 3.12 and 3.13 |
| finalize | see section 5 |

## 5. Live execution

Filled in as each step completes.
