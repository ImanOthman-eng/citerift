# CITERIFT Data Contracts

Contracts are JSON Schema 2020-12 files in `schemas/contracts/v<major>/`.
Version 1.0.0 is the Stage 00 foundation. Validate with
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
- **A retraction status cannot come from a model.** `model_inference` is
  rejected for `retraction_status`.
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
chronological order, and `partial` or `failed` investigations must state their
limitations.

## Versioning

- `schema_version` in a record must match `1.x.y`.
- Minor versions (1.1, 1.2, ...) may only add optional fields or relax
  constraints. `check_backward_compatible` verifies that every valid fixture of
  the previous version still validates (fixture-based; see R-005).
- Breaking changes need a new major directory (`v2/`), a migration note in
  DECISIONS.md, and, because `schemas/contracts/v1` is a Stage 00 owned path,
  a recorded amendment.
- Field formats that real data has not yet confirmed (DOI, PMID, language
  codes) are deliberately permissive (R-006).

## Fixtures

`tests/stage00/fixtures/contracts/v1/valid/` holds three valid synthetic
records. `invalid_cases.json` holds 35 single-mutation negative cases; each
names the base fixture, the JSON pointer, the change and the expected failing
keyword or semantic code, and the test asserts the record fails for exactly
that reason.
