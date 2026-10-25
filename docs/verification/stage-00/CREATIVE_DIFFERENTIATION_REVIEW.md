# Stage 00 Creative Differentiation Review

Prompt 02 section 15 asks Stage 00 to establish originality through
foundational, measurable engineering that supports CITERIFT's scientific
identity, without expanding scope. No visual interface, AI model, detection
engine or Knowledge Ripple work is part of Stage 00, and none was built.

## 1. Existing approaches considered

| Approach | What it offers | Why it is not enough for CITERIFT |
|---|---|---|
| Issue trackers and project boards (for example GitHub Projects) | task status | status is not tied to commits, evidence hashes or test results; anyone can drag a card to "done" |
| Architecture Decision Records (Nygard-style ADRs) | decision history | free text; nothing detects two accepted decisions that contradict each other |
| CI status checks alone | proof that tests ran on a commit | no notion of stage, owner acceptance, or evidence that must stay unchanged |
| W3C PROV / PROV-O provenance model | a full standard vocabulary for provenance | heavyweight for a hackathon timeline; CITERIFT needs a small subset (source, retrieval time, identifier) that both Python and JavaScript can validate |
| A boolean "retracted: true/false" field, common in simple citation checkers | easy to display | `false` silently turns "not found in the sources we checked" into "not retracted", which is a false claim of clearance |

These are general categories, compared on their design. Stage 00 did not
survey specific Wikipedia or retraction tools; that landscape belongs to the
Stage 01 feasibility investigation and is not predicted here.

## 2. Original contributions accepted

### 2.1 Epistemic status as a type in the data contract

Every factual value is an assertion with one of five statuses
(`verified_fact`, `model_inference`, `uncertain`, `unavailable`,
`conflicting`), each with structural rules enforced by the schema
(DECISIONS.md D-009). There is no value meaning "not retracted". Absence of a
retraction record can only be `not_found_in_checked_sources` with status
`uncertain` and the list of sources checked. A model output can never carry
`verified_fact`, and an AI assessment may abstain.

- **Value:** the two integrity errors CITERIFT exists to avoid (treating
  absence as clearance, and treating a model's opinion as a fact) cannot be
  represented in a valid record, so Stages 02 to 08 cannot produce them by
  accident.
- **Verification now:** 35 single-mutation invalid fixtures are rejected,
  including "not retracted", absence claimed as fact, and retraction status
  from a model; mutant M3 (relaxing the absence rule) is killed.
- **Verification later:** in Stages 04 to 06, the share of records whose
  absence-of-retraction is stored as anything other than `uncertain` must be
  0, checked by validating every produced record.

### 2.2 Evidence-bound, owner-separated stage governance

A stage is verified only against a specific commit, with sha256-pinned
artifacts, a clean-tree test report at that commit, gate evidence and a CI run;
owner acceptance is a separate, attested act; the next stage needs a third,
separate authorization. Hand edits are detected by history replay and record
coherence.

- **Value:** a reviewer, judge or later session can check any claim in the
  project history against the repository instead of trusting a narrative.
  This is the engineering form of CITERIFT's "evidence-first, human-verifiable"
  identity.
- **Verification:** 12 mandatory scenarios, 19 single hand edits each detected
  by a specific code, 9 of 9 rule-disabling mutants killed; on the live
  registry, the orchestrator refuses to mark Stage 00 verified while CI
  evidence is missing (TEST_RESULTS.md section 8).

### 2.3 Simulation before implementation, checked against the implementation

The governance rules were model-checked exhaustively on a reduced model before
the orchestrator was written, then compared move by move with the
implementation (differential test).

- **Value:** found a real design defect (VA→IP re-entering the active set)
  that random testing missed, before any code depended on it (D-016).
- **Verification:** iteration-1 and final results are committed; the defect
  is re-introduced in a test that requires the search to find it.

### 2.4 Recovery from the repository alone

`citerift-gov recover` reconstructs completed, verified and open work,
limitations, authoritative revisions and the next authorized action, without
conversation history.

- **Value:** the ephemeral cloud container and context resets cannot erase
  project state; this also makes the project reproducible for judges.
- **Verification:** `test_recovery.py` runs it on a fresh clone in a separate,
  isolated Python process.

### 2.5 Cross-language readiness in the foundation

Contracts carry the wiki language edition and revision id on every citation,
store statuses as machine codes rather than display text (so the frontend can
localize labels), and use
regular expressions that behave the same in Python and JavaScript (the final
review replaced a Unicode-sensitive `\d`).

- **Value:** Stage 07 cross-wiki comparison and the Stage 08 frontend can rely
  on identical validation of the same records.
- **Verification:** every schema pattern was listed and checked
  (RISK_ANALYSIS.md section 4); the valid fixtures include citations from the
  Arabic (`ar`) and English (`en`) editions.

## 3. Alternatives rejected

| Alternative | Reason for rejection |
|---|---|
| Append-only signed ledger or blockchain for stage history | large complexity and tooling cost; git history plus consistency checks gives detection at a fraction of the cost |
| Cryptographic owner signatures now | real benefit (R-001), but needs owner key setup; offered as pending decision D-006 rather than imposed |
| Full W3C PROV-O | heavier than needed; the provenance subset in `common.schema.json` can map to PROV later |
| Graph database or service for project state | not reviewable in a diff, adds an always-on component (D-003, D-004) |
| MCP server or agent framework for orchestration | optional per Architecture v1.1; no Stage 00 requirement needs it (D-015); Prompt 02 forbids frameworks that only simulate teamwork |
| Calibrated confidence in the contract now | calibration needs Stage 06 models and data; the contract documents confidence as uncalibrated until then |
| Strict DOI, PMID and language-code formats now | real formats are verified in Stages 02 and 03; premature strictness would reject valid data (R-006) |

## 4. Scope check

Every contribution above is part of an existing Stage 00 deliverable
(orchestrator, memory, contracts, simulation, tests). None adds a runtime
service, a model, a dataset or a user interface.
