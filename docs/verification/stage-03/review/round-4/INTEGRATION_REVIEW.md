# Independent Stage 03 V1/V2 integration review

Reviewer: separate read-only ChatGPT/Codex agent, 2026-10-30. One reviewer, no delegation.
Authority: `GOVERNANCE.md` and `docs/verification/stage-03/authorization/OWNER_DIRECTIVE_2026-10-30_HANDOFF.md`.

## Review identity and scope

- Baseline and checkout HEAD: `d1b64499ab7b53d5e486f3cc6db6d86f51bf3399`.
- Reviewed uncommitted product diff SHA-256: `4b6746a51d6ff432e3271b53eda4875bbf7ee99ea5bfc0c819a3f893e973c166`.
- Product diff: `reviewed-product.patch`. Per-file hashes, including the untracked V1/V2 test file, are in `reviewed-manifest.json`.
- Scope: changes to `src/citerift/wiki/{verify,extract,worker}.py`, `tests/stage03/test_wiki_v1_v2.py`, and narrowly related marker/render/reconciliation, configuration, schema, and test helpers needed to assess those changes.
- No final cohort content, evaluator annotations, or predictions were read. All captures used here are SYNTHETIC. No product, test, or checkout file was edited. Review output is confined to `/workspace/stage03-work/reviewer`.

## Finding R3-V12-01 — schema-valid numeric configuration raises an uncaught exception

**Priority: P2. Status: open in the reviewed candidate.**

Location: `src/citerift/wiki/verify.py:523`, new `_bound_markers` call to `ExtractConfig.from_json(doc["config"])`.

An ordinary genuine marker-bearing extraction with only `config.max_nodes` serialized as `400000.0` instead of `400000`, followed by recomputation of the config and extraction digests, passes the extraction JSON Schema. JSON Schema treats integer-valued floats as integers. `ExtractConfig.__post_init__` instead requires a Python `int` object. The new call is not caught, so `verify_bundle` raises `ValueError: configuration value max_nodes=400000.0 is not allowed` rather than returning a structured verification result.

This is an introduced verifier availability/API consistency regression. The baseline verifier returns `verified: true` for the same retained capture and document. Current `replay_bundle` already catches this conversion error and returns `replay.state: failed`; verification should likewise handle it. A legitimate JSON reserializer can produce the triggering numeric representation; no capture-byte alteration is needed.

Suggested narrow correction: catch `ValueError`/`TypeError` when constructing the recorded configuration and report `BUNDLE_SCHEMA_INVALID`, matching the established replay path. Alternatively normalize accepted numeric representations consistently, if that is the intended configuration contract. Add a regression asserting a structured report rather than an exception.

Reproduce, without changing retained inputs:

```sh
/workspace/citerift/.venv/bin/python -B /workspace/stage03-work/reviewer/reproduce_config.py
```

Retained evidence: `config-float/` (synthetic capture), `config-float.extraction.json`, `probe-results.json` record `config-float`, and `baseline_verify.py` (exact baseline verifier read with `git show`; it imports the current unchanged extraction semantics). Observed schema errors: `[]`. Observed current exception: `ValueError`. Observed baseline verification: `true`. Observed current replay state: `failed`.

## V1/V2 repair result and focused evidence

No additional material marker-authentication defect was found in the reviewed candidate. Marker reconstruction uses retained source bytes, source-model bindings and the retained DOM, then exact-compares the complete marker witness rather than accepting document-edited region authorization. Equality preserves occurrence multiplicity, context exclusions, region metadata, snippets, source marker templates, and abstention claims. The full extraction replay comparison remains intact.

`probes.py` completed with exit code 0 and 81 recorded scenarios (some record both genuine and forged results):

- 39 genuine outputs verified; none failed. These cover nested/common-ancestor text, quotation, citation-spanning text, inherited hiding, multi-element template output, empty and parser-limited regions, unmatched regions, source-only captures, render element-limit abstention, marker links, repeated contexts, and the original bilingual controls.
- 63 forged variants were rejected. 56 reached and failed `marker context reproduces`; seven evidence-removal cases were already rejected by the schema. Mutations include the original 22 bilingual cases plus reason, hidden-element count, source-marker-template, and evidence-list changes.
- 34 genuine replay checks reproduced. All 22 original forged replay checks differed. The original five reported modifications are included in this matrix.
- Independent additional layout/context probes were authored in `probes.py`; the existing V1/V2 matrix and synthetic capture helpers were also reused. This is focused independent execution and review, not a claim that the existing tests were authored independently.

Performance smoke check on one region: 200 evidence items verified in 0.665 seconds and 2,000 evidence items in 1.115 seconds on this environment. These are actual end-to-end verification wall times, including worker startup. The patch retains the prior local reconstruction/quotation caches, performs one marker reconstruction worker call per nonempty document, and applies existing address-space/CPU/wall limits to that worker. This bounded check does not prove asymptotic behavior or worst-case memory use.

For read-only operation, the probe launcher added Python `-B` to the worker interpreter invocation to prevent bytecode writes in the checkout. It did not alter isolation, limits, marker code, or capture bytes.

## Limits

This is a focused review of the identified uncommitted diff, not final-stage verification or owner acceptance. It does not validate a later edit, the full regression suite, final campaign results, installed-wheel behavior, CI, or large real-world resource limits. Reconstruction shares deterministic marker code with extraction, as expressly allowed by the directive, so this review principally validates binding and resistance to document forgery rather than providing an independent semantic implementation. Existing local locator checks remain in place and the honest cases above passed them.

The open configuration exception must be addressed or explicitly dispositioned before treating this review as clean.

NOT VERIFIED
