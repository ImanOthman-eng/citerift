# Stage 00 Specification: Engineering Foundation (correction A-00-001)

Stage 00 was authorized by the owner on 2026-10-25 (Prompt 02,
`cmsg_018VCB51nDHP6HXmLU4ea5yPPJtDk4V58km8PBjZzdYKEV`), verified at `741476c`
and accepted. The owner then reopened it for a controlled corrective amendment
(`cmsg_018VCB51nDHP6HXmLU4ea5yPXk8eZcAUfir9fZgszrLxhk`, amendment A-00-001,
history entry 11). This package is the result of the corrected stage. The
accepted package is kept unchanged in `superseded/741476c/`.

Scope of the correction: the confirmed findings F-01 to F-23 of the
independent review in `docs/audits/stage-00-2026-10-25/`, inside Stage 00's
original scope. No later stage is touched or authorized. Stage 01 belongs to
the external agent and nothing here assumes any of its findings.

## Purpose (unchanged)

Give CITERIFT a foundation in which stage state, owner decisions, evidence and
data contracts are recorded in the repository, checked by code, and recoverable
by a new session from a clone alone. Stage 00 reads no external data.

## Components

| Component | Location | Change in A-00-001 |
|---|---|---|
| Project Orchestrator | `src/citerift/governance/` (`model.py`, `orchestrator.py`, `evidence.py`, `gitutil.py`, `cli.py`), CLI `citerift-gov` | replay checks every rule per entry; content-based drift; manifest and definition hashes; future times refused; strict JSON; unreadable registry reported, not crashed |
| Persistent Project Memory | `governance/stage_registry.json`, `schemas/governance/stage_registry.schema.json`, `PROJECT_STATUS.md`, `DECISIONS.md`, `RISKS.md`, `CHANGELOG.md`, `memory.py` | policy fixed by the schema; malformed entries are errors; project-wide defects count |
| Data contracts v1, version 1.0.1 | `schemas/contracts/v1/`, `src/citerift/contracts/` (`validate.py`, new `formats.py`), CLI `citerift-contracts` | explicit accepted values for all alternatives; date-time and calendar checks; portable patterns; duplicate keys rejected |
| Test evidence plugin | `src/citerift/governance/pytest_report.py` | records how tests were selected; partial runs are not evidence |
| Simulations | `simulations/stage00/state_machine_model.py` (unchanged), new `replay_conformance.py` | exhaustive check of the history replay against the model |
| CI and protection definition | `.github/workflows/ci.yml`, `.github/rulesets/main-protection.json` | now Stage 00 owned paths (detection for F-20) |
| Repository foundation | `.gitattributes` (new, LF), `src/citerift/py.typed` (new) | owned paths |

## State machine (unchanged edges)

States `NOT_STARTED`, `AUTHORIZED`, `IN_PROGRESS`, `BLOCKED`,
`IMPLEMENTED_NOT_VERIFIED`, `VERIFIED_AWAITING_OWNER_ACCEPTANCE`,
`ACCEPTED_CLOSED`; eleven edges; four owner-only (authorize, withdraw, accept,
reopen). The edge table did not change. What changed is where the guards are
checked: before A-00-001 the guards ran only in `propose()`. Now every history
entry is checked against them at its own position in `check`:

- single active engineering stage after the entry
- dependencies accepted at authorize, verify and accept
- a correction amendment recorded before a reopening
- a blocker open for a block, and none open for start, unblock or verify

A hand-written history must pass the same rules as one written by the tool.

Reopening a foundation stage after a dependent was accepted is allowed again
(F-11). The model always allowed it. The dependent is then reported with the
warning `DEPENDENCY_REOPENED`, not an error. The single-active rule still
prevents two engineering stages from being active together.

## Verification requirements (IN→VA)

All of the requirements of `741476c`, plus:

1. The verification record pins **every file** under the verification
   directory (`evidence_manifest`), not only the seven artifacts. Each gate
   evidence path must be a pinned file inside that directory, or a file under
   the stage's owned paths (whose content the drift check compares with the
   verified revision), or an https URL (F-02).
2. The record pins `definition_sha256` over the stage definition and the
   policy. The definition covers the owned paths, gates, suites, artifacts,
   dependencies, executor and `ci_required`. Weakening them after
   verification is `DEFINITION_CHANGED`. An engineering stage with no owned
   paths, gates or suites cannot be verified (`DEFINITION_WEAK`, F-03).
3. The registry schema fixes the policy values (`single_active`, artifacts,
   handoff file and sections, report file) and `ci_required: true` for
   engineering stages (F-03).
4. The test report must record a complete selection. That means the whole
   `tests` tree, with no `-k`, `-m`, `--deselect`, `--ignore`, `--lf` or
   stepwise run, and nothing deselected or not run (F-07).
5. The handoff, report and record are read with duplicate-key rejection
   (F-18).

## Persistent memory integrity rules

Rules 1 to 10 of `741476c` still hold. They are strengthened as follows:

- Rule 2, replay. Each entry is also checked against the transition guards at
  its own time (F-04, F-05).
- Rule 3, ordering. A time more than 5 minutes ahead of the local clock is
  refused when written and reported by `check` (F-16).
- Rule 5, records. Authorization, verification and acceptance records must
  equal their history entry (time, owner reference). An acceptance must cite
  an owner reference not used before the verification (F-17).
- Rule 7, hashes. They cover every file in the verification directory, and
  the line-ending policy is fixed by `.gitattributes` (F-02, F-12).
- Rule 8, drift. It is decided by comparing owned-path *content* at the
  verified revision and at `HEAD` (`git diff --no-renames`). A merge that
  restores old content is therefore detected. Uncommitted owned changes give
  the warning `UNCOMMITTED_OWNED_CHANGE` (F-01, F-19).
- Rule 9, records. A heading that looks like an entry but is malformed is an
  error, a topic is compared case- and space-insensitively, and a critical
  defect with `Stage: project` blocks every stage (F-06).

## Data contracts 1.0.1

The full table is in `docs/data-contracts.md`.

- The accepted retraction values are `retracted`, `expression_of_concern`,
  `correction`, `reinstated` and `not_found_in_checked_sources`. They are
  explicit for the main value and for every `conflicting` alternative.
  "Not retracted" is not representable.
- Absence of a record is `uncertain` with checked sources. It is never
  `verified_fact`, never model output, and never carries model or confidence
  fields.
- `unavailable` (source not reachable) keeps a null value and a reason. It
  stays distinct from a checked negative.
- Identifiers keep their 1.0.0 patterns. They are now written so that Python
  and ECMA-262 accept the same strings: no trailing-newline match, and a
  `[^\s…]` class with explicit control and format characters.
- Multilingual values stay valid: an Arabic title, a DOI with Arabic letters
  and Arabic-Indic digits, and the language code `zh-yue`
  (`test_multilingual_and_precise_values_accepted`), plus the Arabic and
  English citations in the valid fixtures.

Versioning: 1.0.0 → 1.0.1 is a patch. Every valid 1.0.0 fixture still
validates (`check_backward_compatible` returns no problem). What 1.0.1 now
rejects was never valid under the documented 1.0.0 semantics.

## Environment (unchanged)

Python `>=3.12,<3.14` (D-001). `uv.lock` is unchanged since `741476c` (sha256
`52980fe6641ddd859ea3f93750e4bf348df47eccf4695adc610cb24bd164fe50`). No new
dependency was added: the date-time checker uses the standard library. Node
22 is used only by a test that compares patterns with ECMA-262. That test is
required in CI and skipped locally if `node` is absent.

## Out of scope

Data acquisition, NLP, the UI, any external source, Stage 01 and every later
stage. A cryptographic owner signature (D-006) and a separate bot identity
would close R-001/R-016. Both are owner decisions and are not implemented.
