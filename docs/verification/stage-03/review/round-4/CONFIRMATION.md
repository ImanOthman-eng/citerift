# Addendum: RF-58 correction confirmed

Read-only reviewer: separate ChatGPT/Codex agent, 2026-10-30. This addendum preserves `INTEGRATION_REVIEW.md` unchanged and updates only the disposition of its finding R3-V12-01, allocated the project identifier **RF-58** by the implementer.

**RF-58 is closed for the code hashes below. No unresolved material findings remain from this focused V1/V2 review.**

The correction catches `ValueError` and `TypeError` from `ExtractConfig.from_json` in `_bound_markers`, records `BUNDLE_SCHEMA_INVALID`, and returns from marker reconstruction. The added regression asserts that the integer-valued-float configuration returns a failed verification report rather than raising an exception.

The retained before result is in `probe-results.json`, scenario `config-float`: schema validation returned `[]`, the initial candidate raised `ValueError: configuration value max_nodes=400000.0 is not allowed`, and the baseline verifier returned `verified: true`. `INTEGRATION_REVIEW.md` records that finding and remains historical evidence of the initially reviewed candidate.

The focused correction run completed **nine checks**, retained in `rf58-confirmation.json` and `rf58-confirmation.log`:

- A genuine integer-configuration control still verified.
- Each of the seven integer configuration fields, independently serialized as an integer-valued float, passed JSON Schema validation and returned `verified: false` with `BUNDLE_SCHEMA_INVALID`, without an uncaught exception.
- The implementer's new `test_schema_integer_float_returns_report_not_exception` regression passed when invoked directly using a synthetic temporary directory. This was a direct test-function execution, not a full pytest run.

On this resumption, current file contents and the product diff were hashed again and matched the exact manifest embedded in those nine results. No broad test rerun was performed. The fresh hash comparison is retained in `confirmation-current-hashes.json`.

Baseline and current HEAD: `d1b64499ab7b53d5e486f3cc6db6d86f51bf3399`; these are reviewed uncommitted changes. Confirmed product-diff SHA-256: `af936ed3467cdc3d0c7b53f791c564a9be1b711b330306f9fb39e37d52a325a7`.

| File | Confirmed current SHA-256 |
| --- | --- |
| `src/citerift/wiki/verify.py` | `8241f032b0b2f3935ef9f95cde86c505f0b8e3219493eb5674c35a8eac8a106c` |
| `src/citerift/wiki/extract.py` | `b1ce483a3954c21a0fd798c121676418356ffdb12ef17bd747b78c909608353e` |
| `src/citerift/wiki/worker.py` | `dc981b77ed3dc2d87aa3ee674dfa597c70a8754dfd796550d7cc0081181a75db` |
| `tests/stage03/test_wiki_v1_v2.py` | `b5af0871bfc9f2fe2157d4747333a2239d244572c6b0abbd9f86a8b39d343374` |

The first confirmation harness invocation failed at the added test because the reviewer had not created the directory normally supplied by pytest's `tmp_path`. The synthetic capture correctly returned `BUNDLE_PATH_UNSAFE`. This was a reviewer harness setup error, retained in `rf58-confirmation-harness-path-error.log`. Creating that directory fixed the harness; the subsequent run produced the nine successful checks above. No product change was made for this harness error.

The initial review's 39 genuine verification controls, 63 forged rejections, replay checks, and bounded performance observations remain scoped to its earlier diff. The only subsequent product change reviewed here is the configuration-error handling; the new regression is separately identified above. These results are focused repair evidence, not a full-suite, CI, campaign, installed-wheel, worst-case resource, final-stage verification, or owner-acceptance claim. No final cohort content, evaluator annotations, or predictions were read. No product/test edits or delegation were performed by the reviewer.

Preserved original report SHA-256: `b3ad76f97080b1c56c627c4c5770c91ca7d6af8fe58751388fa72cf1532ff7a0`.

Stage 03 verification remains outside this review's scope.

NOT VERIFIED
