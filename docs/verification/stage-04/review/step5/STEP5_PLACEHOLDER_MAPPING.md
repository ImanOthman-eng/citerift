# Stage 04 Step 5: simulation placeholders and their production codes

Status: Step 5 record, updated at the start of Step 6 for owner decision D-043 (final v1 reason vocabulary). Applies
to `schemas/investigation/v1` (schema version 1.0.0) and decision table `dt-1`.

The Step 4 reference model (`simulations/stage04/dt1_reference.py`) decides on an abstraction of the inputs. Four of
its reason codes are placeholders for inputs that the abstraction does not carry (SIMULATION_REPORT.md section 11).
The owner's Step 5 instruction says: "Do not accidentally freeze simulation-only placeholder semantics into the
production schemas." This record states, for each placeholder, what the production schemas hold instead and where
the specification already defines it. No placeholder is a value of any production enumeration; the test
`test_simulation_placeholders_are_not_reason_codes` checks this, and
`test_every_valid_reference_decision_is_a_valid_claim` checks that every decision the reference model makes on its
valid domain (244,884 cases, 225 distinct decision signatures, all 15 classes) maps, through this table and nothing
else, to a claim that validates.

## 1. The four placeholders

| Placeholder (model only) | Rule | Classification | Production representation | Source in the specification |
|---|---|---|---|---|
| `DEFINITION_UNUSED` | D-1 | abstraction label for the use-eligibility reason | reason `LIST_DEFINED_UNUSED` | SPEC 6.2, row 4 |
| `USE_NOT_ESTABLISHED` | D-2 | abstraction label for two distinct reasons | reason `CONFLICTING_DEFINITIONS` or `NO_BOUND_USE`, whichever row of SPEC 6.2 decided `U` | SPEC 6.2, rows 1 and 5 |
| `STAGE02_BASIS_REASONS` | D-11 | namespace of Stage 02 codes, not a code | Stage 04 reason `CURRENT_EFFECT_NOT_ESTABLISHED` (D-043), plus the Stage 02 basis reasons themselves in `upstream_reasons`, each as `{source: "stage02_projection_basis", code, evidence}` | SPEC 7.3 D-11 ("Stage 02 basis reasons kept") |
| `LOOKUP_UNAVAILABLE` | D-13 | the class name reused as a reason | Stage 04 reason `LOOKUP_QUERY_FAILED` (new name); the failed query's own code stays in the lookup observation, reached through the claim's supporting evidence | SPEC 7.3 D-13 ("code of the failed query"), S-6.10 |

Notes:

- `USE_NOT_ESTABLISHED` is also a value of the use-eligibility codomain `E(u)` (MM 4.2). That value is kept, as the
  `eligibility` of `use_eligibility` evidence. Only its use as a claim reason is a placeholder.
- The test maps `USE_NOT_ESTABLISHED` to `NO_BOUND_USE`. Both production reasons are valid for D-2; which one applies
  depends on an input (the container's binding state) that the abstraction does not carry.
- For D-11 the reference model's Stage 02 basis reasons are an abstraction. The test supplies one real Stage 02 code
  (`MIXED_CURRENT_EFFECT`) as an upstream reason.

## 2. Stage 02 basis reasons keep their provenance

Stage 02 projection basis reasons are an open set owned by Stage 02 and versioned by its policy version
(`src/citerift/retraction/policy.py`). Examples are `SOURCE_TYPE_CONFLICT`, `NOT_FOUND_IN_CHECKED_SOURCES`,
`COVERAGE_GAP_RELEVANT_ROWS`, `MIXED_CURRENT_EFFECT` and `BRIDGE_ONLY_SUPPORT`. The schemas therefore:

- do not enumerate Stage 02 codes as Stage 04 reasons. `upstream_reasons[].code` is a Stage 02 `code`
  (`urn:citerift:schema:retraction:v1:common#/$defs/code`), so a new Stage 02 code needs no Stage 04 schema change;
- tie each upstream reason to the evidence id of the lookup result whose basis carries it, so the code is never
  detached from its source;
- forbid upstream reasons on rules that read no projection basis: D-1, D-2, D-3, D-4, D-6, D-8 and D-13.

## 3. Stage 04 reason codes that share or replace a Stage 02 name

The specification already names these Stage 04 reasons, and they are spelled like Stage 02 basis reasons. They are
Stage 04 reasons with a fixed meaning in `dt-1`. They are not copies of whatever Stage 02 reported.

| Stage 04 reason | Rule | Meaning in `dt-1` | Note |
|---|---|---|---|
| `COVERAGE_GAP_RELEVANT_ROWS` | D-12 | `L` is `no_record` and its projection is `uncertain` with value null | named in SPEC 7.3 |
| `BRIDGE_ONLY_SUPPORT` | D-10 | the projection's basis reasons include `BRIDGE_ONLY_SUPPORT` | named in SPEC 7.3 |
| `RETRACTION_EVENT_TYPE_CONFLICT` | D-7 | a lookup is `matched` with projection `conflicting` and value null | SPEC 7.3 named no reason for D-7. Step 5 used the Stage 02 name `SOURCE_TYPE_CONFLICT`; D-043 renamed it, because D-7 is a conflict of retraction-event types or effects, not of data-source type |
| `NOT_FOUND_IN_CHECKED_SOURCES` | D-16 | `L` is `no_record` with value `not_found_in_checked_sources` | SPEC 7.3 named no reason for D-16 ("provenance = checked sources"); approved by D-043 |

## 4. Names fixed by Step 5 and finalized by owner decision D-043

These names do not exist in the Step 3 documents. They change no class, rule, guard or precedence of `dt-1`. They
only name a reason that the specification described in words. The owner decided them in D-043 (DECISIONS.md).

| v1 name | Rule | Step 5 name | D-043 |
|---|---|---|---|
| `CURRENT_EFFECT_NOT_ESTABLISHED` | D-11 | `STATUS_NOT_ESTABLISHED` (replacing placeholder `STAGE02_BASIS_REASONS`) | renamed: the current scholarly or retraction effect cannot be established from the checked evidence |
| `LOOKUP_QUERY_FAILED` | D-13 | same (replacing placeholder `LOOKUP_UNAVAILABLE` used as a reason) | approved |
| `RETRACTION_EVENT_TYPE_CONFLICT` | D-7 | `SOURCE_TYPE_CONFLICT` | renamed: conflicting Stage 02 retraction-event types or effects |
| `NOT_FOUND_IN_CHECKED_SOURCES` | D-16 | same | approved |

`SOURCE_TYPE_CONFLICT` remains a Stage 02 projection basis code (`src/citerift/retraction/policy.py`); it may appear in
`upstream_reasons` with its evidence, never as a Stage 04 reason. The frozen Step 4 reference model and oracle still
emit `SOURCE_TYPE_CONFLICT` for D-7; they are not changed, and the test that validates every reference decision maps
that name to `RETRACTION_EVENT_TYPE_CONFLICT` the same way it maps the placeholders.
