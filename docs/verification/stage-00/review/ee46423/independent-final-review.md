# Independent final review: Stage 00 correction A-00-001

Reviewed commit: `ee464237da3ed33b0ccc63d82e5b242925ac9ee7` (branch `claude/project-thread-84z62e`), checked out detached in
my own clones. The pre-correction code is `ae2ce9e`. Nothing in `/home/user/citerift` or on GitHub was changed by me
(`git -C /home/user/citerift status --porcelain` is empty). Note: while this review ran, `/home/user/citerift` HEAD moved
to `135e4ac`; that commit was not reviewed.

Paths used below:

- `W=/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review`
- `$W/clone` (main review clone, `uv sync --locked`), `GOV=$W/clone/.venv/bin/citerift-gov`, `PY=$W/clone/.venv/bin/python`
- `$W/mut`, `$W/sim`, `$W/hand` (separate clones for the evidence scripts), `$W/old` (clone at `ae2ce9e`)
- `$W/exp/*` (one throwaway repository per experiment), `$W/scripts/*.py` (my reproduction scripts; all are kept)
- `$W/exp/base`: a sandbox repository built with the project's own `tests/stage00/sandbox_repo.py`
  (`$PY $W/scripts/mkbase.py $W/clone $W/exp/base`): Stage 00 and Stage 01 driven to `ACCEPTED_CLOSED` through
  `citerift-gov`'s own `propose`/`apply`, root `.gitattributes` included. `check` on it: `0 errors, 0 warnings`.

Why a sandbox: at `ee46423` Stage 00 is `IN_PROGRESS` (reopened for A-00-001, no verification record), so `check` on the
real registry runs no evidence, drift, gate or acceptance checks. Every audit reproduction that needs a verified or
accepted stage was therefore run against sandboxes in which the stage was verified by the tool itself.

All findings below were reproduced unless they are listed in section 7 (not reproduced / speculative).

## 1. Tool results (clean clone at ee46423, actual output)

| Command | Output |
|---|---|
| `uv run pytest -q` | `260 passed in 79.87s (0:01:19)` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy` | `Success: no issues found in 12 source files` |
| `uv run citerift-gov check` | `Consistency check: 0 errors, 0 warnings` (exit 0) |
| `uv run citerift-contracts check-schemas` | `2 schemas checked, 0 problems` (exit 0) |
| extra: `uv run ruff format --check .` | `50 files already formatted` |
| extra: `uv run citerift-gov render-status --check` | `PROJECT_STATUS.md is up to date` |
| extra: `uv lock --check` (offline) | `Resolved 45 packages in 1ms` |
| extra: `uv run mypy simulations tests` (F-23) | `Found 13 errors in 5 files (checked 15 source files)` |

(Every command printed the environment warning `UV_NATIVE_TLS ... deprecated`; omitted above.)

## 2. Disposition of F-01 to F-23

"Variant" is my attempt to get around the fix. N-xx refers to section 3.

| # | Original reproduction against ee46423 | Variant(s) | Disposition |
|---|---|---|---|
| F-01 | Merge that takes owned paths from an older branch (`$W/scripts/f01.py`, sandbox `f01base` where owned content changed before verification): `ERROR VERIFICATION_STALE ... (schemas/contracts/v1/common.schema.json; last change seen in history: 5381c2d9a4e4)` | Octopus merge: `VERIFICATION_STALE`. Mode-only change (`update-index --chmod=+x`): `VERIFICATION_STALE`. Change then restore: `0 errors` (correct). Local `git replace <verified> <commit with HEAD tree>` after tampering: `0 errors` (N-13) | **Fixed** (local replace-ref residual, N-13) |
| F-02 | Edit + commit `TEST_RESULTS.md`: 2 x `EVIDENCE_STALE`. Rewrite report totals: `TEST_EVIDENCE_STALE`, `TESTS_FAILED` x2, `EVIDENCE_STALE`. All gates `["."]`: `GATE_EVIDENCE_MISSING` + `GATE_EVIDENCE_UNPINNED` per gate (32 errors). New file in verification dir: `EVIDENCE_UNLISTED` | Gate evidence only `https://example.invalid/anything-at-all`: verification ALLOWED, `0 errors`. Gate citing `HANDOFF.md` + `NOTES.md`, then `NOTES.md` rewritten and committed: `0 errors` (N-02). File named as a correction amendment's `test_report` is exempt and mutable (N-05) | **Partly fixed** |
| F-03 | `policy_edit.py drop_ci`: `REGISTRY_SCHEMA: stages/0/ci_required: True was expected`. `shrink_gates`: `REGISTRY_SCHEMA: policy/handoff_required_sections ...`. `drop_owned_paths` + owned change: `DEFINITION_CHANGED`, `DEFINITION_WEAK`. `single_active_flip.py`: `authorize 03 -> False`, `REGISTRY_SCHEMA: policy/single_active_engineering_stage: True was expected` | Before verification: stage-level `required_artifacts: []` on engineering Stage 00 -> verified with only `test-report.json`, `0 errors`; Stage 02 reclassified `external-agent` + 1 gate + 1 suite + no owned paths -> verified without CI, `0 errors` (N-03) | **Fixed for edits after verification and for the policy block; pre-verification weakening remains** (partly disclosed in R-003) -> partly fixed |
| F-04 | 02 authorized and withdrawn while 00 active and 01 unaccepted: `HISTORY_DEPENDENCY`, `HISTORY_SINGLE_ACTIVE` | 03 authorized in the past while 02 IN_PROGRESS, later withdrawn: `HISTORY_SINGLE_ACTIVE` | **Fixed** |
| F-05 | `mutate.py reopen_without_amendment`: `HISTORY_AMENDMENT_MISSING`. IN_PROGRESS with open blocker: `HISTORY_BLOCKER` | Amendment recorded 10 min after the reopening (hand edit, `$W/scripts/h1.py`): `HISTORY_AMENDMENT_MISSING` (correct, but untested: N-15). One correction amendment used for a second reopening: ALLOWED (N-08) | **Fixed** (new rule gap N-08) |
| F-06 | All 8 audit variants now fail: ASCII hyphen, en dash after id, `###`: `MEMORY_MALFORMED`; `Stage: project`: `OPEN_CRITICAL_DEFECT` for 00 and 01; duplicate Status: `MEMORY_MALFORMED`; topic `Sandbox`/`SANDBOX `: `DECISION_CONTRADICTION` | `## R–016 — ...` (en dash inside the id), `## R‑016` (U+2011), `## R_016`, fullwidth `Ｒ-016`, setext heading, `<h2>` heading, each with an open critical Stage 00 defect: `0 errors` (N-06). Topics `python-version` vs `python version`: no contradiction | **Partly fixed** |
| F-07 | 3 explicit test files: `TEST_EVIDENCE_PARTIAL` (`complete: False`). `--deselect`: `TEST_EVIDENCE_PARTIAL` x2 | `-o "python_files=<5 of 12 files>"`: 137 of 260 tests, `selection.complete: True`, `check_test_report problems: []`. `-o testpaths=...` and `-o python_functions=...`: `complete: True`. Committed `tests/conftest.py` (outside owned paths) keeping 1 test per suite: **8 tests**, `complete: True`, `problems: []` (N-01) | **Partly fixed** (the original outcome, 8 tests accepted, is reproducible) |
| F-08 | `contracts_probe.py`: A, B, B2 all `INVALID` | (see section 3 contracts) no bypass found | **Fixed** |
| F-09 | C chronological fractional: `VALID`; C2 reversed: `EVENT_ORDER` | — | **Fixed** |
| F-10 | D, D2, D3 trailing newline: `INVALID`; E `2026-02-31`: `is not a 'date-time'`; F U+001C: `INVALID`; registry `bad_calendar`, `trailing_newline_ref`: `REGISTRY_SCHEMA` | Differential of all 22 schema patterns, Python `re.search` vs Node 22 `RegExp(p,'u')`, 1,469,403 strings (BMP 0..0x30FF and notable whitespace inserted at start, middle, end of matching seeds): **0 disagreements** (`$W/scripts/patterns_diff.py`) | **Fixed** |
| F-11 | Audit script now stops earlier (`DEFINITION_WEAK: [stage 02] ... empty owned_paths`; the real Stage 02 definition has no owned paths yet). Adapted (`$W/scripts/f11.py`, 02 given an owned path): reopen 00 while 02 ACCEPTED_CLOSED -> ALLOWED with `WARNING DEPENDENCY_REOPENED`; authorize 03 while 00 reopened -> REFUSED (`HISTORY_DEPENDENCY`, ...) | Reopen 00 while dependent 02 IN_PROGRESS: REFUSED (`HISTORY_SINGLE_ACTIVE`, `MULTIPLE_ACTIVE_STAGES`) — consistent with invariant 4 and the model (observation, not a defect) | **Fixed** |
| F-12 | `git -c core.autocrlf=true clone`: `0 errors`; `core.eol=crlf`: `0 errors` | Committed `docs/.gitattributes` (`*.md text eol=crlf`, outside owned paths): fresh clone gives 16 x `EVIDENCE_STALE` (N-12) | **Fixed** (fail-closed residual N-12) |
| F-13 | Truncated registry: `ERROR REGISTRY_UNREADABLE ...`, exit 1; `recover` prints HEAD, branch, dirty paths, exit 1 | Registry schema deleted: `FileNotFoundError` traceback (the audit named this case); schema truncated + `recover`: `JSONDecodeError` traceback; registry `{}`: `check` fine, `recover`/`status`: `KeyError: 'stages'` traceback; non-UTF-8 byte in RISKS.md: `UnicodeDecodeError` traceback (all exit 1) (N-10) | **Partly fixed** |
| F-14 | Report outside repo: `29 passed`, report written | Report in a non-existent directory: `FileNotFoundError` after the run (N-16) | **Fixed** |
| F-15 | Default `blocker resolve 01` by engineering agent: `REJECTED ACTOR_NOT_PERMITTED` (no misattribution) | `--actor external-agent --recorded-by external-agent`: accepted, recorded as external-agent (self-declared actor; covered by R-001/R-002) | **Fixed** |
| F-16 | `--at 2030-01-01T00:00:00Z`: `REJECTED TIMESTAMP_IN_FUTURE` | Writer with a clock 2 h fast (no `--at`): ALLOWED; on a correct clock `check` gives `HISTORY_FUTURE_TIMESTAMP` and the next transition is REJECTED (`HISTORY_TIME_ORDER`). `--at now+4min` ALLOWED, then an immediate correct-clock `blocker add` is REJECTED (`HISTORY_BLOCKER`) (N-11) | **Partly fixed** (R-012 overstates) |
| F-17 | Acceptance reusing the authorization ref: `OWNER_REF_REUSED`; `acceptance_before_history`: 2 x `RECORD_HISTORY_MISMATCH` | One owner ref for the acceptances of 00 and 01: both ALLOWED, `0 errors`. Authorization of 02 citing 00's acceptance ref: ALLOWED. Acceptance citing the correction amendment's owner ref (cited before the verification): ALLOWED (N-07) | **Partly fixed** |
| F-18 | Duplicate `status` key: `REGISTRY_UNREADABLE: ... duplicate JSON key 'status'` | `a`-escaped duplicate: rejected. Duplicate key in test report: `TEST_EVIDENCE_INVALID`. Two amendments both `A-00-001` (one correction, one enhancement) and two blockers `B-02-001`: `0 errors` (N-09). Ruleset file with duplicate `bypass_actors` passes its test (N-14) | **Fixed for JSON keys** (array-level duplicates N-09, test loader N-14) |
| F-19 | Uncommitted change in owned file: `WARNING UNCOMMITTED_OWNED_CHANGE` | Untracked file in owned dir: same warning | **Fixed** |
| F-20 | `.github/workflows`, `.github/rulesets`, `.gitattributes` are owned paths (registry); R-016 records the limitation | `pyproject.toml` entry point `citerift-gov` pointed at a new module under `src/citerift/` (not owned): `uv lock --check` passes, the CI command `uv run --no-sync citerift-gov check` prints `0 errors`, the honest `python -m citerift.governance.cli check` prints 2 errors; no owned-path file changed (N-04) | **Addressed by documentation; compensating detection incomplete** (GitHub side not exercised) |
| F-21 | R-001, R-003, GOVERNANCE "What is enforced" rewritten; RISK_ANALYSIS and CREATIVE review archived under `superseded/` | New overstatements, section 4 | **Partly fixed** |
| F-22 | docs/data-contracts.md:97-101 states the amendment requirement and the out-of-`v1/` alternative | handoff point 7 (synthetic consumer) PASS | **Fixed (documentation)** |
| F-23 | `src/citerift/py.typed` exists (0 bytes) and is an owned path | `mypy` still `files = ["src"]`; `mypy simulations tests`: 13 errors (was 20) | **Fixed** (py.typed); scope unchanged, optional |

Regression-test claim (CHANGELOG.md:11-13, R-017): copying `tests/stage00/test_corrections.py` from ee46423 into the
`ae2ce9e` clone and running it: `51 failed, 1 passed`; the passing one is the control case
`test_f12_crlf_checkout_does_not_change_evidence_hashes[False]`. The claim holds.

## 3. Confirmed findings (new defects and bypasses of the fixes)

### N-01 Partial test run recorded and accepted as complete (Security weakness, Medium; bypass of F-07)

- Code: `src/citerift/governance/pytest_report.py:325-347` (`_selection`), `:354-362` (`pytest_collection_modifyitems`),
  `src/citerift/governance/evidence.py:139-148`.
- Reproduction A (no commit; `$W/clone`, `$W/scripts/rcheck.py` calls `evidence.check_test_report` on the report):
  ```
  .venv/bin/python -m pytest -q -p no:cacheprovider \
    -o "python_files=test_unit_model_evidence_memory.py test_recovery.py test_contracts.py test_simulation.py test_registry_tampering.py" \
    --citerift-report $W/reports/e6.json
  .venv/bin/python $W/scripts/rcheck.py $W/reports/e6.json $(git rev-parse HEAD)
  ```
  Observed: `137 passed`; `collected 137 ... dirty False exit 0`; `selection {'args': ['tests'], ..., 'complete': True, 'deselected': 0}`;
  `check_test_report problems: []`. The full suite has 260 tests; `test_corrections.py` (the A-00-001 regression tests) did not run.
  `-o testpaths=...` and `-o python_functions=...` also give `complete: True`.
- Reproduction B (committed file outside Stage 00 owned paths, `$W/exp/f07conf`): commit `tests/conftest.py` whose
  `pytest_collection_modifyitems` keeps one item per suite marker (`items[:] = keep`), run
  `python -m pytest -q -p no:cacheprovider --citerift-report $W/reports/e8.json`.
  Observed: `8 passed`, `selection ... 'complete': True, 'deselected': 0`, all 8 suites present, `problems: []`.
  `git diff --stat ee46423 HEAD`: only `tests/conftest.py`. This is the exact outcome of the original F-07 (8 tests accepted).
- Root cause: `complete` is derived from the CLI arguments and a fixed list of narrowing options. Ini overrides
  (`-o`/`--override-ini`, also `-c`) change what "the configured test tree" means, and conftest hooks run before the plugin's
  `pytest_collection_modifyitems`, so items removed there are never seen. `tests/conftest.py`, `conftest.py` and
  `pyproject.toml` are not owned paths.
- Smallest fix: in `_selection`, set `complete` false when `config.option.override_ini` is non-empty or the ini file is not
  the repository `pyproject.toml`; add `pyproject.toml` and any `conftest.py` outside `tests/stage00` to Stage 00 owned
  paths (or fail `check` when one exists); for robustness record a hash of the collected node-id set and compare it with an
  independent `pytest --collect-only` in CI.

### N-02 Gate evidence counts as "hash-pinned" when it is a URL, or when any one of its references is pinned (Confirmed defect, Low-Medium; bypass of F-02)

- Code: `src/citerift/governance/orchestrator.py:745-764` (`pinned = True` for `evidence.is_url(ref)`; one pinned reference
  sets `pinned` for the whole gate).
- Reproduction (`$PY $W/scripts/f02.py`, sandboxes `f02_url`, `f02_mixed`):
  - every gate's evidence `["https://example.invalid/anything-at-all"]`: `verify 00 ...: ALLOWED`, `check`: `0 errors, 0 warnings`.
  - every gate's evidence `["docs/verification/stage-00/HANDOFF.md", "NOTES.md"]`, then `NOTES.md` rewritten and committed
    after verification: `0 errors, 0 warnings`.
- Contradicts GOVERNANCE.md:48 ("every acceptance gate passed with hash-pinned evidence") and CHANGELOG.md:24 ("gate
  evidence must be a pinned file"). No test covers either case (hand mutant H10 survives).
- Smallest fix: require every non-URL reference of a gate to be in the recorded manifest or an owned path; either reject
  URL-only gates or document that a URL is not pinned.

### N-03 Stage-level overrides bypass the schema-fixed policy before verification; `DEFINITION_WEAK` is incomplete and untested (Confirmed defect, Low-Medium; partly disclosed in R-003)

- Code: `orchestrator.py:144-146` (`stage.get("required_artifacts", policy[...])`), `:660-661` (handoff checks skipped when
  `HANDOFF.md` is absent), `:809-819` (`DEFINITION_WEAK` covers `owned_paths`, `required_test_suites`, `acceptance_gates`
  only, engineering stages only); schema allows `required_artifacts: []` and any `executor`.
- Reproduction (`$PY $W/scripts/f03c.py`): engineering Stage 00 with `required_artifacts: []`, CI recorded, gates citing
  `test-report.json`: `verify ... ALLOWED []`, verification dir contains only `['test-report.json']`, `check`: `0 errors`.
  (`$PY $W/scripts/f03b.py`): Stage 02 set to `executor: external-agent`, `ci_required: false`, `required_artifacts: []`,
  1 gate, 1 suite, no owned paths, then authorized and verified with no CI and a URL-only gate: ALLOWED, `0 errors`.
- R-003 (RISKS.md:61-63) discloses that "Stage definitions (gates, suites, owned paths) can still be edited before a stage
  is verified"; it does not mention `required_artifacts`, `executor` or `verification_dir`, and GOVERNANCE.md:133-134 says
  the schema "fixes the policy values and the CI requirement of engineering stages". Hand mutant H12 (remove the whole
  `DEFINITION_WEAK` block) survives the suite.
- Smallest fix: in the schema, for engineering stages forbid `required_artifacts` or make it `const` to the policy list;
  extend `DEFINITION_WEAK` to `required_artifacts`; add a test; list the remaining editable fields in R-003.

### N-04 The CI governance step can be neutralized without touching a Stage 00 owned path (Security weakness, Low-Medium; extends F-20)

- Reproduction (`$W/exp/f20pyproject`, clone of ee46423): change `pyproject.toml` `[project.scripts] citerift-gov` to
  `citerift.gov_shim:main`, add `src/citerift/gov_shim.py` printing `Consistency check: 0 errors, 0 warnings`, and hand-edit
  the registry (last history actor). Commit. Then:
  - `uv lock --check` -> `Resolved 45 packages in 1ms` (passes); `uv sync --locked` succeeds.
  - `uv run --no-sync citerift-gov check` (the CI command, ci.yml "Governance state and memory consistency") ->
    `Consistency check: 0 errors, 0 warnings`, exit 0.
  - honest `.venv/bin/python -m citerift.governance.cli check` -> `2 errors` (`HISTORY_ACTOR`, `STATUS_DOC_OUT_OF_DATE`).
  - changed files: `governance/stage_registry.json`, `pyproject.toml`, `src/citerift/gov_shim.py`; changed owned-path files: `[]`.
- So R-016's compensating detection (owned `.github/workflows`, `.github/rulesets`, `.gitattributes`) does not cover
  `pyproject.toml`, `uv.lock` or new modules under `src/citerift/`, which change what CI executes; the same applies to the
  test step (N-01 B). The honest copy still detects the registry edit, as GOVERNANCE.md says. GitHub was not exercised.
- Smallest fix: add `pyproject.toml` and `uv.lock` to Stage 00 owned paths (or own `src/citerift` as a whole) and run the
  CI governance check as `python -I -m citerift.governance.cli` rather than through the entry point; state the residual in R-016.

### N-05 Amendment test reports exempt arbitrary files from the evidence manifest (Confirmed defect, Low; new code)

- Code: `orchestrator.py:779` (`later` = every amendment's `test_report.path`, any kind), `:788`; `_amendment_findings`
  re-checks the hash only for `enhancement` (`:915-930`).
- Reproduction (`$PY $W/scripts/f02b.py`): on accepted Stage 00, `citerift-gov amend 00 --kind correction ... --test-report
  docs/verification/stage-00/late-evidence.md` (a new file) -> `Recorded amendment A-00-001`; `check`: `0 errors, 1 warnings`
  (`CORRECTION_PENDING`); rewrite and commit the file again -> still `0 errors, 1 warnings`.
- Contradicts GOVERNANCE.md:62-64 ("every file in the stage's verification directory ... pinned by hash").
- Smallest fix: exempt only `enhancement` test reports and compare the recorded hash of every amendment test report.

### N-06 Memory parser still skips some heading forms (Confirmed defect, Low; bypass of F-06)

- Code: `src/citerift/governance/memory.py:22` (`_HEADING_LIKE` accepts only an ASCII `-` or nothing between the letter and
  the digits, only ATX headings), `:72-73` (`normalize_topic`).
- Reproduction (`$PY $W/scripts/f06.py`, open critical Stage 00 defect appended to RISKS.md of the accepted sandbox):
  `## R–016 — Critical defect` (U+2013 inside the id), `## R‑016` (U+2011), `## R_016`, `## Ｒ-016`, a setext heading
  (`R-016 — Critical defect` over `-----`), and `<h2>R-016 — ...</h2>`: each `Consistency check: 0 errors, 0 warnings`
  (control with the exact form: `OPEN_CRITICAL_DEFECT`). Topics (`f06b.py`): `python-version` + `python version`,
  `+ Python‑version`, `+ ｐython-version`: no `DECISION_CONTRADICTION` (`python_version` is detected).
- Contradicts GOVERNANCE.md:67-68 ("A malformed decision or risk entry is an error, never skipped"); hand mutant H8
  survives (no test of a heading without a hyphen).
- Smallest fix: report as `MEMORY_MALFORMED` any `- Status:`/`- Severity:`/`- Kind:` field block that is not attached to a
  parsed entry (catches every heading variant); NFKC-normalize, map dash-like characters to `-` in ids and spaces to `-` in topics.

### N-07 Owner-reference reuse is checked only for acceptance against history before the verification (Security weakness, Low; bypass of F-17)

- Code: `orchestrator.py:489-506`.
- Reproduction (`$PY $W/scripts/f11_17.py`):
  - 00 and 01 both verified; `accept 00 with cmsg_ONESTATEMENT001: ALLOWED`, `accept 01 with the same ...: ALLOWED`, `check`: `0 errors`.
  - `authorize 02 citing 00's acceptance ref cmsg_TESTACCEPTREF0005: ALLOWED` (an acceptance message used as an authorization).
  - correction amendment with `owner_ref cmsg_AMENDMENTREF01`, reopen with another ref, re-verify, then accept citing
    `cmsg_AMENDMENTREF01`: ALLOWED (control: citing the reopening ref -> `OWNER_REF_REUSED`).
- The third case contradicts GOVERNANCE.md:50-52 (acceptance "citing an owner statement not already cited before the
  verification"): amendments are not searched. In the real registry A-00-001 and the reopening cite the same ref, so the
  real case is covered.
- Smallest fix: treat every owner-only history entry and every amendment as a citation; require an acceptance (and an
  authorization) ref not cited by any earlier owner decision, except a reopening paired with its own amendment.

### N-08 One correction amendment can justify any number of reopenings (Confirmed defect, Low; new rule)

- Code: `orchestrator.py:423-434`, `:1093-1098`.
- Reproduction (`f11_17.py`): A-00-001 recorded, 00 reopened with it, re-verified, re-accepted; second reopening citing
  A-00-001 again: `ALLOWED`. The second reopening carries no new recorded reason or evidence.
- Smallest fix: a reopening must cite a correction amendment not cited by an earlier reopening (replay and `_edge_problems`).

### N-09 Duplicate amendment and blocker ids are accepted (Confirmed defect, Low; array-level analog of F-18)

- Reproduction (`$PY $W/scripts/f18.py`): Stage 00 with two amendments both `A-00-001` (correction and enhancement):
  `0 errors, 1 warnings`; Stage 02 with two blockers `B-02-001`: `0 errors`.
- `_replay_step_findings` takes the first record with the id (`:425`, `next(...)`), `_edge_problems` the last
  (`:1094`, dict), so replay and `propose` can read different records for the same history entry.
- Smallest fix: `AMENDMENT_DUPLICATE_ID` and `BLOCKER_DUPLICATE_ID` errors in `_amendment_findings`/`_record_findings`.

### N-10 Remaining tracebacks (Confirmed defect, Low; residual of F-13)

- Reproduction (`$W/exp/f13_*`): schema file deleted, `check`: `FileNotFoundError: ... stage_registry.schema.json`
  traceback; schema truncated, `recover`: `json.decoder.JSONDecodeError` traceback; registry `{}`, `recover` and `status`:
  `KeyError: 'stages'` traceback (`check` reports `REGISTRY_SCHEMA` correctly); byte `0xff` appended to RISKS.md, `check`:
  `UnicodeDecodeError` traceback. All exit 1 (fail closed). The audit named the deleted-schema case explicitly; the new
  F-13 test (`test_corrections.py:509-527`) covers only the registry file.
- Code: `orchestrator.py:128-131` (schema loaded lazily, outside `cli.main`'s `try`), `cli.py:205-245`, `memory.py:106,162`.
- Smallest fix: load the schema in `Orchestrator.__init__` (inside the existing `try`), stop `recover`/`status` when schema
  errors exist, and report undecodable memory files as `MEMORY_UNREADABLE`.

### N-11 Clock skew handling (Confirmed defect, Low; residual of F-16)

- Reproduction (`$PY $W/scripts/f15_16.py`):
  - writer whose clock is 2 h fast (simulated by replacing `orchestrator.utc_now`), no `--at`: `authorizes 01: ALLOWED`;
    on the correct clock `check`: `ERROR HISTORY_FUTURE_TIMESTAMP ... 2026-10-25T20:07:21Z is later than now (2026-10-25T18:07:21Z)`;
    next correct-clock transition: `REJECTED ... HISTORY_FUTURE_TIMESTAMP (pre-existing) ... HISTORY_TIME_ORDER`.
  - `--at now+4min` (inside the 5-minute allowance): `ALLOWED`; an immediate correct-clock `blocker add`:
    `REJECTED ERROR HISTORY_BLOCKER: entry 2: AUTHORIZED -> IN_PROGRESS while blockers ['B-01-001'] were open`
    (the new blocker's real time precedes the forward-dated entry, so replay places it before the transition).
- The limit is relative to the writer's own clock, so a fast clock still blocks every correct machine until real time
  catches up (detected, fail closed). R-012 (RISKS.md:155-157) says "so a fast clock cannot block later correct transitions".
- Smallest fix: correct R-012; make `add_blocker`/`resolve_blocker` default `at` to `max(now, last history at)`.

### N-12 Evidence hashes still depend on checkout attributes outside owned paths (Confirmed defect, Low; residual of F-12)

- Reproduction: in a clone of `$W/exp/base` commit `docs/.gitattributes` = `*.md text eol=crlf`; the existing tree checks
  `0 errors`; a fresh plain clone gives `Consistency check: 16 errors` (`EVIDENCE_STALE` for every `.md` artifact of 00 and 01).
- Fail closed (false positive), but a non-owned file changes the outcome. Root cause unchanged: `sha256_file` hashes
  working-tree bytes. Smallest fix: hash the committed blob (`git hash-object`/`git cat-file`) or forbid nested `.gitattributes`.

### N-13 `git replace` hides owned-path drift locally (Security weakness, Low; F-01 variant)

- Reproduction (`f01.py`, `$W/exp/f01_replace`): tamper an owned file and commit -> `VERIFICATION_STALE`; then
  `git replace <verified> $(git commit-tree <HEAD tree> -p <verified>^ -m fake)` -> `Consistency check: 0 errors, 0 warnings`.
- `git diff` (`gitutil.changed_paths`) honors `refs/replace/*`. Local only: a fresh CI checkout does not fetch replace refs
  by default (inference, not exercised). Smallest fix: run every git query with `--no-replace-objects` (or
  `GIT_NO_REPLACE_OBJECTS=1`) in `gitutil._git`.

### N-14 The ruleset test reads JSON with last-key-wins (Confirmed defect, Low; F-18 residual)

- `tests/stage00/test_repository.py:189` uses `json.loads`. With a duplicate `"bypass_actors": [{"actor_id": 5, ...}],`
  before `"bypass_actors": []` in `.github/rulesets/main-protection.json`: `test_branch_ruleset_definition` -> `1 passed`;
  `loads_strict` on the same file -> `DuplicateKeyError: duplicate JSON key 'bypass_actors'`. (What GitHub does with such a
  file was not tested.) Contract fixtures are also read with `json.loads` (`test_contracts.py:21,25`).
- Smallest fix: use `loads_strict` in these tests.

### N-15 Test gaps in the new checks (Low; test adequacy, not behavior)

Hand mutants (`$W/scripts/hand_mutants.py`, `pytest -q -x tests/stage00` per mutant, in `$W/mut`; tree clean afterwards):

| Mutant | Result |
|---|---|
| H1 reopening amendment time comparison removed | SURVIVED (260 passed) — behavior correct when exercised by hand (`h1.py`) |
| H2 `--ignore` not narrowing | KILLED |
| H3 deselected count ignored | SURVIVED — redundant with `not_run` (deselected items are counted as not run); equivalent in practice |
| H4 owned-path gate evidence not accepted as pinned | SURVIVED (allowance untested) |
| H5 topic normalization removed | KILLED |
| H6 skew widened to 10 years | SURVIVED (only 2030 is tested) |
| H7 reuse window uses the first verification | SURVIVED |
| H8 heading detector requires an ASCII hyphen | SURVIVED |
| H9 `not_run` check removed from `check_test_report` | SURVIVED — redundant with `complete` for plugin-written reports |
| H10 URL evidence not pinned | SURVIVED (see N-02) |
| H11 blocker actor forced to executor | KILLED |
| H12 `DEFINITION_WEAK` block removed | SURVIVED (see N-03) |

### N-16 Report into a missing directory crashes the plugin (Confirmed defect, Low; F-14 residual)

`pytest ... --citerift-report $W/exp/nonexistent-dir/report.json` -> tests run, then `FileNotFoundError` traceback at
session finish, no report. Fix: `Path(path).parent.mkdir(parents=True, exist_ok=True)`.

### Observations checked with nothing wrong

- Content drift: change-then-restore is clean; shallow-clone behaviour not re-tested.
- Duplicate-key strict loader is used for the registry, its schema, test reports, `--record`, contract schemas and records
  (grep of `src/`); only tests use `json.loads` (N-14).
- `const true` policy vs `1`: rejected (`True was expected`); `ci_required: 1`: rejected.
- Contracts 1.0.1: the three 1.0.0 valid fixtures (from `ae2ce9e`) validate under 1.0.1 (`broken under 1.0.1: []`), and
  the 1.0.1 fixtures validate under 1.0.0; the tightenings are the ones docs/data-contracts.md:91-95 lists.
- Reopening a foundation stage while an engineering dependent is active is refused by invariant 4; the model agrees
  (conformance 0 disagreements). This is a liveness constraint worth stating in GOVERNANCE.md, not a defect.

## 4. Documentation accuracy

Accurate (checked against behavior): GOVERNANCE.md "Protection of `main`" paragraph (each literal statement holds) and
"Not enforceable" paragraph; R-001, R-002, R-004; R-016 statement that prevention is not in place; docs/data-contracts.md
(assertion table, retraction rules, `$(?!\n)` and explicit-class claims confirmed by the 0-disagreement differential, 47
invalid cases, 1.0.0 fixture compatibility, F-22 versioning text).

Overstated or inaccurate:

| File:line | Text | Evidence |
|---|---|---|
| GOVERNANCE.md:46-48 | "a passing test report of the complete test suite ... every acceptance gate passed with hash-pinned evidence" | N-01 (8 of 260 tests accepted), N-02 (URL-only and partly pinned gates) |
| GOVERNANCE.md:50-52 | "citing an owner statement not already cited before the verification" | N-07 (amendment ref) |
| GOVERNANCE.md:62-64 | "every file in the stage's verification directory ... pinned by hash" | N-05 |
| GOVERNANCE.md:67-68 | "A malformed decision or risk entry is an error, never skipped." | N-06 |
| GOVERNANCE.md:127-131 | "Prevented ...: any transition, blocker or amendment whose resulting registry fails the full consistency check" | With a pre-existing `HISTORY_ACTOR` error, `blocker add 02` and `amend 00` both wrote (`Recorded blocker B-02-001`, `Recorded amendment A-00-001`; `check` still 1 error) — `_mutate` refuses only newly introduced errors (`$W/scripts/mutate_pre.py`) |
| GOVERNANCE.md:132-134 | "Detected: hand edits that break invariants 1 to 7, the registry schema (which also fixes the policy values and the CI requirement of engineering stages)" | N-02, N-03 (stage override of `required_artifacts`, executor reclassification), N-05, N-06, N-07 |
| GOVERNANCE.md:72-74 ("Per-stage deliverables") | "Every engineering stage produces ... SPECIFICATION.md, ... HANDOFF.md" | N-03 (verified with none of them) |
| RISKS.md:51-52 (R-003) | "every file in the verification directory, the stage definition and the policy pinned by hash" | N-05; R-003:61-63 lists only "gates, suites, owned paths" as editable before verification (N-03) |
| RISKS.md:155-157 (R-012) | "so a fast clock cannot block later correct transitions" | N-11 |
| RISKS.md:211-214 (R-016) | "Compensating detection ... a change to them makes Stage 00 VERIFICATION_STALE" | Literally true, but CI is equally neutralized through non-owned `pyproject.toml` + a new module (N-04) |
| CHANGELOG.md:24 | "gate evidence must be a pinned file" | URL-only accepted (N-02) |
| CHANGELOG.md:26 | "partial runs are rejected (F-07)" | N-01 |
| CHANGELOG.md:34 | "Malformed memory entries are errors" | N-06 |
| governance/stage_registry.json, A-00-001 `reason` | "14 Stage 00 defects and 5 security weaknesses (F-01 to F-20 ...)" | 14 + 5 = 19 = F-01..F-19; F-20 is a sixth weakness. Trivial, and the record is history |

Also: docs/audits/stage-00-2026-10-25/README.md says dispositions are recorded in `docs/verification/stage-00/TEST_RESULTS.md`
"of the corrected verification"; that file does not exist at ee46423 (Stage 00 is `IN_PROGRESS`), which is consistent
with the state but means no disposition record is in the commit yet.

## 5. Evidence scripts

| Script | Command | Result |
|---|---|---|
| replay conformance, small | `uv run --no-sync python simulations/stage00/replay_conformance.py --config small` (in `$W/sim`) | 45,024 cases, 45,024 agreements, 0 disagreements, 134 status vectors; `real 0m5.009s` |
| replay conformance, full | `... --config full --output $W/replay-full.json` | 205,632 cases, 0 disagreements, 459 vectors, max history 28; `real 0m31.736s` (about half a minute on this 4-CPU machine, not several minutes). JSON identical to `docs/verification/stage-00/simulation/replay-conformance-full.json` |
| replay conformance on ae2ce9e | same script and model run with the `ae2ce9e` orchestrator (`$W/old`) | 12,872 disagreements; JSON identical to `replay-conformance-full-ae2ce9e.json` |
| mutation check | `uv run --no-sync python docs/verification/stage-00/mutation/mutation_check.py` (in `$W/mut`) | `33 mutants, 33 killed, 0 survived`; `real 6m40.542s`; working tree clean afterwards |
| hand mutants | `$W/scripts/hand_mutants.py` | 12 mutants: 3 killed, 2 survive because of redundant checks, 7 survive (test gaps, N-15) |
| handoff simulation | `uv run --no-sync python docs/verification/stage-00/handoff/handoff_simulation.py ee4642... $W/handoff-result.json` (in `$W/hand`) | 12/12 PASS, `real 0m2.649s` |

Caveat on the handoff simulation: at ee46423 Stage 00 is not verified, so point 7b ("consumer files outside owned paths do
not disturb Stage 00") and the self-acceptance branch of point 6 pass without exercising drift or acceptance checks; the
mutation check runs with `-x` on `tests/stage00` and does not use the report plugin's completeness logic.

## 6. Severity summary of confirmed findings

| Severity | Findings |
|---|---|
| Medium | N-01 |
| Low-Medium | N-02, N-03, N-04 |
| Low | N-05, N-06, N-07, N-08, N-09, N-10, N-11, N-12, N-13, N-14, N-15, N-16 |

No critical or high finding. N-03 and N-04 are partly disclosed (R-003, R-016); the rest are not disclosed.

## 7. Not reproduced or speculative (kept apart from the findings above)

- GitHub behavior for F-20/N-04 (a PR-modified workflow or entry point satisfying the required `ci-gate`) was not exercised.
- How GitHub treats a ruleset file with duplicate keys (N-14) was not tested.
- Skipped tests are accepted in a "complete" report (code reading of `evidence.check_test_report`; the two Node tests skip
  when Node is absent outside CI). Not reproduced because Node is installed here.
- A `conftest.py` using `collect_ignore`/`pytest_ignore_collect` would also hide files from the plugin (inferred from N-01 B;
  not run separately).
- Tampered `.pyc` files in git-ignored `__pycache__` under owned paths are invisible to `UNCOMMITTED_OWNED_CHANGE`; not tested.
- Severity ratings are judgments.

## 8. Verdict

The correction is real and substantial: all original reproductions of F-01, F-04, F-05, F-08 to F-12, F-14, F-15, F-18 and
F-19 now fail closed, the tools pass, the mutation check reproduces (33/33), the conformance results reproduce exactly, and
51 of the 52 new regression tests fail on `ae2ce9e`. The claim that F-01 to F-19 are fixed does not fully hold: F-07 can
still be reproduced with its original outcome by an ini override or a committed `tests/conftest.py` (N-01), and F-02, F-03,
F-06, F-13, F-16 and F-17 are only partly fixed (N-02, N-03, N-06, N-10, N-11, N-07). GOVERNANCE.md, RISKS.md (R-012, R-003)
and CHANGELOG.md overstate several of these controls (section 4). This review records no stage state and makes no owner
decision; whether these residuals block re-verification of Stage 00 is the owner's decision.

NOT VERIFIED
