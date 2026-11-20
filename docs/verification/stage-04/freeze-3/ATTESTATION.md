# Stage 04 freeze-3 candidate attestation (final corrective cycle)

Second record of the two-record mechanism: it names the freeze-content commit, which cannot name itself.

| Record | Value |
|---|---|
| Freeze-content commit (candidate SHA) | `c3854b8f386d507ad129ebfb81cf96be7202549e` |
| Its tree | `a039e67c7a9e6e54f56b8d8f5357962822f01581` |
| Its parent (evidence commit) | `1a6231ca02886cae6171b5dda4481a290a9a498c` |
| Freeze manifest digest | `5fa2e0884c653418041504d023da9c997a38161e0868aece0d2a751ce9936ad4` (reproduced twice at `1a6231c`) |
| Exposure manifest v3 SHA-256 | `f3556be865ed051f4a9144172f09965ec767737379e3cd87e251b69ac0eeedc9` (478 articles) |
| Code revision of the test runs | `208a8de2533acd7a31b4580f791bd548a645b4c7`, CI run 390 (`44725151080`): success |
| CI run on the content commit | run 391, id `44728240942`: **success** |

CI run 391: `verify (python 3.12)` 3,681 passed (test step 14 min 33 s, pytest 871.99 s); `verify (python 3.13)`
3,681 passed (13 min 39 s, 818.17 s); in both jobs the governance check, lock check, ruff, format, mypy strict, schema
validation, the test-report check (0 problems), the unchanged-files check and `pip-audit --strict` (no known
vulnerabilities) passed; `ci-gate` success. No required job reached 30 minutes (OD-S12-2).

The frozen engine of the earlier freezes is unchanged: `b5bf8ed` (dt-1, `SUPERSEDED_AFTER_FAILED_04_I`) and
`28ba646` (dt-2, D-076; gate 04-I NOT PASSED under P2) keep every file of `../freeze/` and `../freeze-2/`.

This is a freeze **candidate**. It is not a freeze until the owner accepts it. No P3, seed, draw, frame, annotation or
prospective run starts without the owner's explicit authorization.
