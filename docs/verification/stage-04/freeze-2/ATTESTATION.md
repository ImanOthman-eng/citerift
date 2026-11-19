# Stage 04 freeze candidate attestation (corrective cycle, freeze-2)

Second record of the two-record mechanism: it names the freeze-content commit, which cannot name itself.

| Record | Value |
|---|---|
| Freeze-content commit (candidate SHA) | `d8a059dccd9b7782f8a9ee0b19a2ec39370b14da` |
| Its tree | `973703020f8d0d09c0e4552e3fc616bf02e23c28` |
| Its parent (evidence commit) | `80e414b0d2d399637a63152f778335ea01e0b44f` |
| Freeze manifest digest | `6be3d310c88ad01ccdb5f9e7987cad6716c7f469399ad5d6d9e41d363b5ab77a` (reproduced byte for byte at `80e414b`) |
| Exposure manifest v2 SHA-256 | `932cd65f79d7d72b508923bdfc0892422ee25eeea653b0941370649a595343b5` |
| CI run on the content commit | run 362, id `44451825018`: **failure** |

CI run 362, both verify jobs: `1 failed, 3371 passed` (Python 3.12: test step 17 min 43 s, pytest 1061.85 s; Python
3.13: 12 min 4 s, 723.83 s); lint, format, mypy strict, schema validation and the governance check passed; the
clean-tree, unchanged-files and pip-audit steps were skipped because the test step failed; `ci-gate` failed on the
matrix result. No required job reached 30 minutes (OD-S12-2).

The one failure is `tests/stage04/test_step13_evaluation.py::test_frozen_check_passes_on_the_frozen_engine`: a
P-listed check that the running engine is the superseded frozen engine `b5bf8ed`. It fails because the candidate's
`src` and `schemas` are dt-2, as D-071 requires. It is not skipped, marked or edited; how it is handled is an owner
decision (card `cmsg_018VCB51nDHP6HXmLU4ea5yPKGg9QN82npdYdMmf5LXJez`). Until then the candidate has no green CI run.

This is a freeze **candidate**. It is not a freeze until the owner accepts it, and no new Step 13 starts without the
owner's explicit authorization.
