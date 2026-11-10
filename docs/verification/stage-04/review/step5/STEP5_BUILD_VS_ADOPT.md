# Stage 04 Step 5: open-source leverage review for schema tooling

Status: Step 5 record. Owner rule of 2026-11-10 (project chat, message
`cmsg_018VCB51nDHP6HXmLU4ea5yP2h9GM56jQT5F4jCEcUv9zu`): before building a non-trivial subsystem from scratch, review
mature open-source alternatives; licence compatibility is a hard gate; the review does not widen the authorized step.

Scope: Step 5 builds no subsystem. It adds five JSON Schema documents and their tests. The only tooling question is
how the schemas are validated and how they are tested. Later subsystems (state machine, workflow controller, file
locking, durable persistence, content-addressed storage, journal integrity, process supervision and the D-042 timer,
fault injection, stateful testing) are not reviewed here; the rule requires that review before each later step makes
them concrete.

Result: no dependency is added or changed. `jsonschema` (already adopted, DECISIONS.md D-008) stays the validator.

## 1. How the facts were gathered (2026-11-10)

- Release, upload date, declared licence, Python requirement and direct dependencies: the PyPI JSON API
  (`https://pypi.org/pypi/<name>/json`).
- Installed versions and licences of the existing chain: `importlib.metadata` in the project environment and
  `uv.lock`.
- Known vulnerabilities: the OSV API (`https://api.osv.dev/v1/query`, ecosystem PyPI), plus `pip-audit` on the
  locked environment in the Step 5 verification.
- Draft support: the project README or package text (fastjsonschema README and `fastjsonschema/__init__.py` at
  `master`; the hypothesis-jsonschema package description).
- Maintenance activity is judged only from the date of the latest release. Commit activity and issue response were
  not examined.

## 2. Candidates

| Field | jsonschema (in use) | hypothesis-jsonschema | fastjsonschema | check-jsonschema | pydantic |
|---|---|---|---|---|---|
| 1. Project | python-jsonschema/jsonschema | Zac-HD/hypothesis-jsonschema | horejsek/python-fastjsonschema | python-jsonschema/check-jsonschema | pydantic/pydantic |
| 2. Capability for CITERIFT | Draft 2020-12 validation with a `$id` registry (`referencing`), used by every accepted stage | generates instances from a schema for property-based tests | compiles a schema to Python code for fast validation | CLI and pre-commit hook that validates files against schemas | Python models that validate data and emit JSON Schema |
| 3. Release considered | 4.26.0 (locked; PyPI upload 2026-01-07) | 0.23.2 (2026-10-27) | 2.22.3 (2026-11-01) | 0.39.0 (2026-10-26) | 2.14.3 (2026-11-05) |
| 4. Licence | MIT | MPL-2.0 | BSD-3-Clause | Apache-2.0 (classifier) | MIT |
| 5. Transitive licences | attrs 26.1.0, referencing 0.37.0, rpds-py 2026.9.1, jsonschema-specifications 2025.9.1: all MIT | hypothesis (MPL-2.0), sortedcontainers; plus jsonschema | none | jsonschema, click, requests, ruamel.yaml, regress, tomli | pydantic-core (Rust extension), annotated-types, typing-extensions, typing-inspection |
| 6. Maintenance (latest release) | January 2026 | October 2026 | November 2026 | October 2026 | November 2026 |
| 7. Security history (OSV) | none recorded for jsonschema or its four dependencies | none recorded | none recorded | GHSA-q6mv-284r-mp36 / PYSEC-2026-1245 (remote schema caching), fixed in 0.30.0 | ReDoS GHSA-mr82-8j83-vxmv (fixed 2.4.0) and older 1.x advisories |
| 8. Python and platform | ≥ 3.10; 3.12 and 3.13 tested in CI | ≥ 3.11 | ≥ 3.10 | ≥ 3.11 | ≥ 3.10 |
| 9. Runtime cost | already installed | test-only | small, pure Python | CLI only | compiled core, large |
| 10. Reproducibility | locked; deterministic validation | randomized generation, needs a stored seed and database to replay a failure | deterministic | deterministic, but can fetch remote schemas | deterministic |
| 11. Network, cloud or API | none (URN ids, local registry) | none | none | can fetch remote `$ref`s and schema catalogs; can be disabled | none |
| 12. Complexity saved | — | hand-written negative cases (Step 5 has 132 tests) | none needed: validation time is not a constraint | the project's own `check-schemas` already does this | none: the contracts are schema-first by D-008 |
| 13. Complexity added | — | a copyleft test dependency and its engine; draft gap below | a second validator with different semantics | a second schema checker, YAML and HTTP dependencies | a second source of truth beside the schemas |
| 14. Testability | high | high in principle | high | n/a | high |
| 15. Against the internal approach | the internal approach is this library | its description says "JSONSchema drafts 04, 05, and 07 are fully tested and working"; the Stage 04 schemas use 2020-12 (`$defs`, `prefixItems`, `if`/`then`), so generated cases would not be trustworthy | implements drafts 04, 06 and 07 (README), with a 2019 generator on `master`; no 2020-12, so it cannot validate these schemas | duplicates `citerift-contracts check-schemas`; brings a remote-fetch feature the project must not use | would invert D-008 (schemas generated from code instead of contracts shared with the JavaScript frontend) |
| 16. Recommendation | **ADOPT** (keep; no change) | **REJECT** for Step 5 (draft gap); MPL-2.0 would also need an owner decision | **REJECT** (no 2020-12) | **REJECT** (duplicate; network feature) | **REJECT** (contradicts D-008) |

## 3. Notes for later steps

- Property-based and stateful testing will come up again for the Memory fold and the controller (Step 6 onward).
  The `hypothesis` engine is MPL-2.0. Using it, even as a test-only dependency, needs the licence analysis and owner
  decision that the rule requires. The review of that step should record this, together with the alternative of
  extending the exhaustive enumerations Step 4 already uses.
- No code was copied from any candidate.
- CITERIFT has no project licence yet (DECISIONS.md D-007 recommendation, Stage 09). Nothing here assumes one.
