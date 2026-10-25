# Stage 00 Creative Differentiation Review (correction A-00-001)

Prompt 02 §15 asks Stage 00 to establish originality through measurable
engineering, without expanding scope. This review rechecks each contribution
of the accepted review (`superseded/741476c/CREATIVE_DIFFERENTIATION_REVIEW.md`)
against the corrected code.

The independent review (F-21) found that two claims there were false: 2.1
"cannot be represented" and 2.5 "patterns behave the same in Python and
JavaScript". It also found that one citation did not match its source, under
2.2. Each is corrected below, together with the test that now makes the claim
true. No visual interface, model, detection engine or Knowledge Ripple work is
part of Stage 00, and none was built.

The "existing approaches considered" table and the "alternatives rejected"
table of the accepted review are unchanged and still apply. They are not
repeated here. That landscape is a design comparison only: specific
Wikipedia or retraction tools belong to Stage 01 and are not predicted.

## 1. Contributions, rechecked

### 1.1 Epistemic status as a type in the data contract

Every factual value is an assertion with one of five statuses:

- `verified_fact`
- `model_inference`
- `uncertain`
- `unavailable`
- `conflicting`

The statuses are stored as machine codes, not display text. The accepted
retraction values are explicit: `retracted`, `expression_of_concern`,
`correction`, `reinstated`, `not_found_in_checked_sources`.

- **Corrected claim:** in contracts 1.0.1, a valid record cannot represent
  "not retracted", absence stated as fact, or a model's opinion stated as fact
  or as `uncertain`. That holds for the main value **and for every
  `conflicting` alternative**. In 1.0.0 the alternatives were untyped (F-08),
  so the earlier claim was false for them.
- **Verification now:** 47 single-mutation invalid cases are rejected, 12 more
  than before. They include `conflicting_retraction_alternative_not_retracted`,
  `..._boolean`, `retraction_status_from_model_labelled_uncertain` and
  `retraction_status_with_model_confidence_only`. Ten of the 12 were
  accepted by `ae2ce9e` (`fail-first/results-ae2ce9e.txt`). The other two (a
  control character and a next-line character in a DOI) were already
  rejected, and are kept as guards. Mutants M3 and M23 are killed.
- **Verification later:** in Stages 04 to 06, the share of produced records
  that state absence of retraction as anything other than `uncertain` must be
  0, checked by validating every record.

### 1.2 Evidence-bound, owner-separated stage governance

A stage is verified only against a specific commit. The record pins every
file in its verification directory, its own definition and the policy by
hash. The tests must be a complete run at that commit, and owned content must
be unchanged since then. Owner acceptance is a separate act and must cite a
new owner statement. The next stage needs a third, separate authorization.

- **Corrected claim:** hand edits are *detected*, not prevented. A consistent
  forgery is not detected (R-003). The accepted review did not say this.
  "Complete run" is judged from a report the test process writes about
  itself, so test code can forge it (R-004).
- **Verification now:** 12 mandatory scenarios, 19 hand edits, and 19 seeded
  mutation classes (120 cases) all pass. 54 rule-disabling mutants are run
  (TEST_RESULTS.md §5). On the live registry, the orchestrator refuses
  verification while CI evidence is missing. The accepted review cited
  TEST_RESULTS §8 for that, but §8 recorded other codes. The refusal is now
  shown directly by `test_05b_trivial_artifact_and_gates_block_verification`
  (`CI_EVIDENCE_MISSING`, `CI_NOT_SUCCESSFUL`) and by the dry run in HANDOFF.md.

### 1.3 Simulation before implementation, checked against the implementation

- **Corrected claim:** the differential test compared *proposals* only, so it
  missed F-11, where the model and the implementation disagreed on reopening
  after a dependent was accepted. It also missed the weakness of the history
  replay.
- **Verification now:** a fixed differential case for F-11. And an exhaustive
  conformance check of the replay against the model, which found 12,872
  disagreements at `ae2ce9e` and 0 after the correction (SIMULATION_REPORT.md
  §2). The model itself is unchanged, and its output is byte-identical to the
  accepted run.

### 1.4 Recovery from the repository alone

Unchanged. `test_recovery.py` runs `recover` on a fresh clone in a separate
isolated process. Failure simulations add interrupted writes, corruption,
lost commits and shallow clones (SIMULATION_REPORT.md §4). The handoff
simulation exercises recovery from a clean clone with a minimal environment
(§5).

### 1.5 Cross-language readiness in the foundation

- **Corrected claim:** schema patterns now accept the same strings in Python
  and ECMA-262. 1.0.0 did not (F-10): `$` matched before a trailing newline in
  Python, and `\S` differed on Unicode spaces. That earlier claim rested on a
  manual review only.
- **Verification now:**
  - `test_schema_patterns_use_the_portable_subset`, a lint.
  - `test_schema_patterns_agree_with_ecma262`, which runs every pattern in
    Node and Python on edge cases and on seeded random strings with 0
    differences. It is required in CI.
  - Multilingual positives (`test_multilingual_and_precise_values_accepted`):
    an Arabic title, a DOI with Arabic letters and Arabic-Indic digits, and the
    language code `zh-yue`. The valid fixtures keep their Arabic (`ar`) and
    English (`en`) citations.
  - Citations still carry the wiki edition and revision id.

## 2. New contribution of the correction (measurable)

**Conformance as evidence.** The stage now carries the measured number of
cases where the checker and the formal model disagree (12,872 → 0 over
205,632 cases). It also carries a fail-first record listing each test that
failed on the uncorrected revision. A reviewer can re-run both. This is an
engineering form of CITERIFT's "evidence-first, human-verifiable" identity,
and it adds no runtime component.

## 3. Identity and creative principles preserved

- The project identity standard is unchanged: "CITERIFT — Created and Directed
  by EVE TELOS · IM" (D-017, `docs/identity.md`, `OWNERSHIP.md`). No public
  file in this correction contains the founder's legal name. The AI-assistance
  disclosure stays truthful: commits carry
  `Assisted-by: Claude Code (AI coding agent)` (D-018).
- Evidence-first, uncertainty kept explicit, no clearance by absence, no model
  opinion as fact: all are strengthened, none relaxed.

## 4. Scope check

Every change is part of an existing Stage 00 deliverable: orchestrator,
memory, contracts, simulation, tests and documentation. None adds a runtime
service, a model, a dataset, a paid service, an MCP server or a user
interface.
