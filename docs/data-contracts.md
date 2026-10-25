# CITERIFT Data Contracts

Contracts are JSON Schema 2020-12 files in `schemas/contracts/v<major>/`.
Version 1.0.0 was the Stage 00 foundation; version 1.0.1 is the corrected
foundation (correction A-00-001, below). Validate with
`uv run citerift-contracts validate FILE...`.

## Files

| Schema `$id` | File | Purpose |
|---|---|---|
| `urn:citerift:schema:contracts:v1:common` | `v1/common.schema.json` | identifiers, timestamps, provenance, model references, the assertion wrapper |
| `urn:citerift:schema:contracts:v1:investigation` | `v1/investigation.schema.json` | one investigation: subject paper, Wikipedia citations, AI assessments, events, limitations |

## The assertion wrapper

Every factual value is stored as `{"status": ..., "value": ..., ...}`:

| Status | Meaning | Structural rule |
|---|---|---|
| `verified_fact` | Established from cited sources | `provenance` has at least one source; no `model` or `confidence`; value not null |
| `model_inference` | Produced by a model; never a fact | `model` and `confidence` required |
| `uncertain` | Evidence is insufficient | `reason` required |
| `unavailable` | Could not be obtained | `value` is null; `reason` required |
| `conflicting` | Sources disagree | `value` is null; at least two `alternatives`, each with provenance |

`confidence` is a model-reported score in [0, 1]. It is not a probability of
correctness unless Stage 06 calibrates it and documents that.

## Rules that protect scientific integrity

- **Missing records are not evidence.** There is no value meaning "not
  retracted". When checked sources hold no retraction record, the value is
  `not_found_in_checked_sources`, the status must be `uncertain`, and the
  provenance must list what was checked.
- **Accepted and rejected retraction values are explicit.** `retraction_status`
  accepts `retracted`, `expression_of_concern`, `correction`, `reinstated` and
  `not_found_in_checked_sources` (and null where the status requires it). The
  same list applies to every `alternatives[].value` of a `conflicting` status,
  so "not retracted" (or `false`, or any other value) cannot enter through a
  conflicting alternative.
- **Unknown, unavailable and negative stay distinct.** `unavailable` (could not
  be obtained, null value), `uncertain` (insufficient evidence, with a reason)
  and `not_found_in_checked_sources` (a search of named sources found nothing,
  always `uncertain` with provenance) are different records; none of them is a
  verified negative.
- **A retraction status cannot come from a model.** `model_inference` is
  rejected for `retraction_status`, and so are `model` and `confidence` fields
  under any status.
- **No claim-truth field.** AI assessments describe how a citation is used, as
  model inferences with an abstention option (an abstained assessment has null
  label and confidence). Human review is recorded beside the assessment and does
  not change its epistemic status.
- **Revisions are explicit.** A Wikipedia citation records the language edition,
  title and the exact revision id it was observed in, plus provenance.
- **Synthetic data is labeled.** Fixtures and simulations set `"synthetic": true`
  and use the `10.5555` DOI test prefix and invented titles.

## Semantic checks beyond JSON Schema

`citerift.contracts.validate.semantic_problems`: unique citation and
assessment ids, assessments must target an existing citation, events in
chronological order (compared as instants, so fractional seconds order
correctly), a `retraction_date` (year, year-month or full date, including in
alternatives) must be a real calendar date, and `partial` or `failed`
investigations must state their limitations.

## Portability and parsing

- Validators must enable the `date-time` format check: CITERIFT validators use
  `citerift.contracts.formats.FORMAT_CHECKER` (standard library only), which
  rejects impossible instants such as `2026-02-31T12:00:00Z`.
- Patterns are written so that Python `re.search` and ECMA-262 `RegExp` (with
  the `u` flag) accept the same strings: every pattern ends with `$(?!\n)` (in
  Python `$` also matches before a final newline) and uses the explicit class
  `[^\s\x00-\x1f\x7f-\x9f\ufeff]` instead of `\S`. `\d`, `\w` and `\b` are not
  used. A test lints every pattern and compares both engines on edge strings
  (tests/stage00/test_contracts.py; Node is required for it in CI).
- Records and schemas are parsed with duplicate-key rejection
  (`citerift.contracts.formats.loads_strict`): the standard library silently
  keeps the last value, so a reviewer could be shown a different one.
- Multilingual values (Arabic titles, non-ASCII DOI suffixes, language codes
  such as `zh-yue`) are accepted; tests cover them.

## Versioning

- `schema_version` in a record must match `1.x.y`.
- Minor versions (1.1, 1.2, ...) may only add optional fields or relax
  constraints. `check_backward_compatible` verifies that every valid fixture of
  the previous version still validates (fixture-based; see R-005).
- Patch versions (1.0.1) correct a contract so that it enforces what this
  document already stated. 1.0.1 rejects records that 1.0.0 accepted in
  violation of the rules above (trailing newlines and control characters in
  identifiers, impossible dates, untyped or forbidden alternatives, model
  fields in `retraction_status`); every valid fixture of 1.0.0 is still valid.
  Corrections need an owner-authorized `correction` amendment to Stage 00.
- Adding a schema or a field under `schemas/contracts/v1/` changes a Stage 00
  owned path and makes Stage 00 stale: a minor version needs an owner-approved
  `enhancement` amendment to Stage 00 (independent review 2026-10-25, F-22).
  A later stage can instead define its own schemas outside `v1/` that `$ref`
  the v1 definitions by URN, with no Stage 00 change.
- Breaking changes need a new major directory (`v2/`), a migration note in
  DECISIONS.md, and, because `schemas/contracts/v1` is a Stage 00 owned path,
  a recorded amendment.
- Field formats that real data has not yet confirmed (DOI, PMID, language
  codes) are deliberately permissive (R-006).

## Fixtures

`tests/stage00/fixtures/contracts/v1/valid/` holds three valid synthetic
records. `invalid_cases.json` holds 47 single-mutation negative cases; each
names the base fixture, the JSON pointer, the change and the expected failing
keyword or semantic code, and the test asserts the record fails for exactly
that reason.
