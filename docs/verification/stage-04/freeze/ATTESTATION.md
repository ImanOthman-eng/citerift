# Stage 04 freeze attestation (Step 12)

The second freeze record (owner Step 12 message, section 22). The commit that adds this file only names the freeze;
it changes no frozen file.

| Item | Value |
|---|---|
| Freeze-content commit (frozen SHA) | `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` |
| Its tree | `86152ad543971d321059f16f93c3aff671f467c4` |
| Its parent (evidence commit) | `bdeeac10135043fec65734e47c78c4437a1da4c6` |
| Code revision of the freeze evidence | `3eec84f63467192407934dda2de544338a5d9140` |
| Freeze manifest | `docs/verification/stage-04/freeze/FREEZE_MANIFEST.json` |
| Manifest digest (canonical encoding) | `609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc` |
| Freeze report | `docs/verification/stage-04/freeze/FREEZE_REPORT.md` |

## CI on the exact freeze-content tree

GitHub Actions run 338, id 44194411028 (push of `b5bf8ed`), conclusion **success**:

| Job | Python | Tests | Test step (pytest) | Job | check-report |
|---|---|---|---|---|---|
| verify (python 3.12) | 3.12.3 | 3249 passed | 12 min 25 s (744.14 s) | 12 min 51 s | 0 problems at `b5bf8edfcb6f` |
| verify (python 3.13) | 3.13.14 | 3249 passed | 12 min 20 s (739.08 s) | 12 min 42 s | 0 problems at `b5bf8edfcb6f` |
| ci-gate | | | | | success |

Ruff, format and mypy strict passed; the schemas were checked (0 problems); the tree was clean before and after the
steps; `pip-audit --strict` found no known vulnerabilities. Both jobs ran under the 18-minute diagnostic threshold
(OD-S12-2).

Local check of the same commit, on a clean clone in the 4-vCPU container: 3249 passed in 17 min 57 s (Python
3.12.3), with the tree still clean afterwards.

To check the freeze:
- `git rev-parse b5bf8ed^{tree}` gives the tree above.
- At `b5bf8ed`, the SHA-256 of the canonical encoding of the committed `FREEZE_MANIFEST.json` (`canon(...,
  allow_float=True)`) gives the digest above.
- The SHA-256 of each of the 84 files the manifest lists equals its recorded value. This was checked on the clean
  clone: no mismatch.

The builder records `HEAD` at build time as `parent_sha`. It wrote the manifest with `HEAD` at `bdeeac1`, so running
it again at a later commit changes only that field.
