# Stage 04 freeze candidate attestation (corrective cycle, freeze-2)

Second record of the two-record mechanism: it names the freeze-content commit, which cannot name itself.

This attestation replaces the one for the first candidate (content `d8a059d`, CI run 362 red on one P-listed test),
which the owner did not accept (`cmsg_018VCB51nDHP6HXmLU4ea5yPC9MGHitF1TN4me2xbMsFkj`). The candidate below was
regenerated after owner decisions D-072 to D-075.

| Record | Value |
|---|---|
| Freeze-content commit (candidate SHA) | `28ba6467c7005eec7bf51869974719a402059ca7` |
| Its tree | `45c52da459b09597f105d6e4abd8ab00332c6799` |
| Its parent (evidence commit) | `90282408193bf05cd49a4c9df7c90e853ff0ee9d` |
| Freeze manifest digest | `d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13` (reproduced byte for byte at `9028240`) |
| Exposure manifest v2 SHA-256 | `b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b` |
| CI run on the content commit | run 365, id `44486733733`: **success** |

CI run 365: `verify (python 3.12)` 3,382 passed (test step 20 min 57 s, pytest 1256.13 s); `verify (python 3.13)`
3,382 passed (12 min 9 s, 727.42 s); in both jobs governance check and `render-status --check`, lock check, ruff,
format, mypy strict, schema validation, the test-report check (0 problems), the unchanged-files check and
`pip-audit --strict` (no known vulnerabilities) passed; `ci-gate` success. No required job reached 30 minutes
(OD-S12-2).

This is a freeze **candidate**. It is not a freeze until the owner accepts it, and no new Step 13 starts without the
owner's explicit authorization.
