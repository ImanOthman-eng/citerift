# Independent final review (second): Stage 00 correction A-00-001 at `9e025c9`

Reviewed commit: `9e025c984a49e7adb05b41cd6ab7f669841e8317` ("R"), branch `claude/project-thread-84z62e`, checked out
detached in my own clones. I wrote none of the code under review. Nothing in `/home/user/citerift` or on GitHub was
changed by me (`git -C /home/user/citerift status --porcelain` is empty). Note: while this review ran,
`/home/user/citerift` HEAD moved to `7138d6d` ("test the override and dropped-item rules on their own"); that commit was
**not** reviewed. Everything below refers to R.

Paths:

- `W=/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2`
- `$W/clone` (main clone at R, `uv sync --locked`), `$W/mut` (separate clone at R for the mutation, replay, model and
  handoff runs), `$W/exp/*` (one throwaway repository per experiment), `$W/scripts/*` (my reproduction scripts, all kept)
- `$W/exp/base`: sandbox built with R's own `tests/stage00/sandbox_repo.py` (`$W/scripts/mkbase.py`): Stage 00 and
  Stage 01 driven to `ACCEPTED_CLOSED` through `propose`/`apply`, root `.gitattributes` copied, plus a committed
  `NOTES.md`. `check`: `Consistency check: 0 errors, 0 warnings`.
- `$W/orig/*`: the first reviewer's scripts (`review/ee46423/scripts/`) copied and repointed to `$W/origws`; their base
  sandbox rebuilt with R's code (`check`: `0 errors, 0 warnings`). Logs: `$W/orig_run1.log`, `$W/orig_run2.log`.

Commands in this report use `GOV = $W/clone/.venv/bin/python -P -m citerift.governance.cli` with `PYTHONPATH=$W/clone/src`
(the CI form) unless stated otherwise.

All findings in §3 were reproduced. Speculation is only in §6.

## 1. Tool results (clean clone at R, actual output)

Every `uv` command also printed the environment warning `UV_NATIVE_TLS ... deprecated`; omitted below.

| Command | Output | Exit |
|---|---|---|
| `uv run pytest -q -p no:cacheprovider` | `308 passed in 113.70s (0:01:53)` | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `57 files already formatted` | 0 |
| `uv run mypy` | `Success: no issues found in 12 source files` | 0 |
| `uv run citerift-gov check` | `Consistency check: 0 errors, 0 warnings` | 0 |
| `uv run citerift-gov render-status --check` | `PROJECT_STATUS.md is up to date` | 0 |
| `uv run citerift-contracts check-schemas` | `2 schemas checked, 0 problems` | 0 |
| `uv lock --check` | `Resolved 45 packages in 4ms` | 0 |
| `uv run citerift-gov recover` | HEAD `9e025c98…`, 0 uncommitted; AUTHORIZED: 01, IN_PROGRESS: 00; 12 open risks; D-006, D-007 pending; `Consistency: 0 errors, 0 warnings` | 0 |

Stage 00 is `IN_PROGRESS` with no verification record, so `check` on the real registry runs no evidence, drift, gate
or acceptance check. Those were exercised in sandboxes (§2, §3).

## 2. Disposition of V-01 to V-16

"Original" means the first review's reproduction, re-run against R. "Variant" means my attempts to get around the fix.

| # | Original reproduction at R | Variants | Disposition |
|---|---|---|---|
| V-01 | A: `-o "python_files=<5 files>"`: 137 tests, `override_ini` recorded, `complete: False`, `TEST_EVIDENCE_PARTIAL` x2. B: committed `tests/conftest.py` keeping 1 item per suite: 8 tests, `dropped: 300`, `complete: False`, `TEST_EVIDENCE_PARTIAL` x2 | One committed line in `pyproject.toml` (`python_functions = [20 names]`): **92 of 308 tests, `complete: True`, `check_test_report problems: []`** (X-02). Conftest that keeps 1 test per (file, suite) and pads the list back to its length with repeats: **21 distinct tests, `dropped: 0`, `complete: True`, `problems: []`**, while pytest prints `308 passed` (X-03). Same with the conftest uncommitted and hidden by `.git/info/exclude` (`dirty: False`), and as a `-p` plugin from outside the repository (X-03) | **Partly fixed** |
| V-02 | URL-only gates: verify `REFUSED` (`GATE_EVIDENCE_UNPINNED` x16). `HANDOFF.md` + `NOTES.md`: `REFUSED` (`... NOTES.md, which is neither in the evidence manifest nor an owned path`) | Gate citing `tests/stage00/../../NOTES.md`, or a committed symlink `tests/stage00/ev.md -> ../../NOTES.md`: **verify ALLOWED, `NOTES.md` rewritten and committed, `0 errors, 0 warnings`** (X-01) | **Partly fixed** |
| V-03 | `f03b`/`f03c` stop at the schema: `The registry does not match its schema`. Direct: Stage 00 `required_artifacts: []` or `["HANDOFF.md"]` → `REGISTRY_SCHEMA: stages/0/required_artifacts`; Stage 02 `executor: external-agent` → `REGISTRY_SCHEMA: stages/2/executor: 'engineering-agent' was expected`; `ci_required: false` → `True was expected` | `depends_on` is not fixed: Stage 02 edited to depend only on 00, then verified and accepted while Stage 01 is `NOT_STARTED`: `0 errors` (X-07; not in R-003's list of editable fields) | **Fixed** for the fields named; residual X-07 |
| V-04 | `pyproject.toml` entry point → shim: `uv run citerift-gov check` prints the shim's `0 errors`; the CI command `python -P -m citerift.governance.cli check` prints `2 errors` (`HISTORY_ACTOR`, `STATUS_DOC_OUT_OF_DATE`) | A non-owned `src/sitecustomize.py` (loaded through CI's `PYTHONPATH=src`): **every CI step passes** (lock, guard, ruff, format, mypy, schemas, `check` `0 errors`, `render-status` up to date, `308 passed`) on a registry where the agent took the owner's acceptance; no owned path changed (X-04). A non-owned `src/jsonschema/` also replaces the installed `jsonschema` | **Partly fixed** |
| V-05 | `f02b`: correction amendment naming a new file as `test_report` → `EVIDENCE_UNLISTED`; file rewritten → also `EVIDENCE_STALE` | Enhancement report path pointing at a non-report → `TEST_EVIDENCE_INVALID` (code path `check_test_report`) | **Fixed** |
| V-06 | All `f06` forms now errors: ASCII hyphen, en dash after id, level 3, bold heading → `MEMORY_MALFORMED` (heading + orphan fields); en dash / U+2011 / underscore / fullwidth id, setext, HTML heading → `MEMORY_MALFORMED` (orphan fields); `Stage: project` → `OPEN_CRITICAL_DEFECT` x2; topics `python_version`, `python version`, `Python‑version`, `ｐython-version` → `DECISION_CONTRADICTION` | Open critical defect under `### R–020` with `- **Status**: open` (bold field names), or lowercase field names, or an indented field block under a setext heading: `0 errors` (X-06). Topics `sand​box` / `sand­box` (invisible) next to accepted `sandbox`: no contradiction (X-06) | **Partly fixed** |
| V-07 | Case 3 (acceptance citing the amendment's `owner_ref`): `REFUSED ... OWNER_REF_REUSED ... already cited by A-00-001`; control with the reopening ref also refused | Cases 1 and 2 still `ALLOWED` (by design, GOVERNANCE invariant 2). An enhancement amendment may cite the acceptance's own `owner_ref` (X-13) | **Fixed** for the stated scope |
| V-08 | Second reopening with A-00-001: `REFUSED ... HISTORY_AMENDMENT_REUSED ... already justified entry 11` | — | **Fixed** |
| V-09 | Two `A-00-001`: `AMENDMENT_DUPLICATE_ID`; two `B-02-001`: `BLOCKER_DUPLICATE_ID` | — | **Fixed** |
| V-10 | Schema deleted → `REGISTRY_SCHEMA_UNREADABLE`, exit 1; schema truncated + `recover` → same; registry `{}` → `check` 5 errors, `recover`/`status` → `REGISTRY_SCHEMA`, exit 1; `0xff` in RISKS.md → `MEMORY_UNREADABLE` (1 error) | 16 other inputs still end in a traceback (X-05): non-UTF-8 `PROJECT_STATUS.md` (check, render-status, recover) or `HANDOFF.md`; unknown stage id for `deps`, `readiness`, `handoff`, `blocker add`, `amend`; a parseable but invalid schema (`{"type": 5}`, `[]`, dangling `$ref`); `amend --test-report <missing>`; `--record` that is a list or has list `gates`; a test report with a string or list count | **Fixed** for the named cases; residual X-05 |
| V-11 | `--at now+4min` then an immediate correct-clock `blocker add`: `Recorded blocker B-01-001` (was `HISTORY_BLOCKER`). Fast clock still blocks correct machines (`HISTORY_FUTURE_TIMESTAMP`), as R-012 now states | Honest `blocker add` → `BLOCKED` → `blocker resolve` within one second with default times: **resolve REJECTED** with `HISTORY_BLOCKER: ... (pre-existing) entry 13 blocks the stage with no open blocker` (X-08) | **Fixed**; residual X-08 |
| V-12 | Committed `docs/.gitattributes` (`*.md text eol=crlf`): same tree `ATTRIBUTES_NESTED` (1 error); fresh clone `17 errors` (`ATTRIBUTES_NESTED` + `EVIDENCE_STALE`) | — | **Fixed** (detected, named) |
| V-13 | `f01`: tamper + local `git replace <verified> <HEAD-tree commit>` → `VERIFICATION_STALE` (was `0 errors`) | `.git/info/grafts` is still honoured with `--no-replace-objects`: an orphan rewrite of history (`7 errors`, `REVISION_NOT_IN_HISTORY`) becomes `0 errors, 0 warnings` (X-09) | **Fixed** for replace refs; residual X-09 |
| V-14 | Duplicate `bypass_actors` in the ruleset → `test_branch_ruleset...` fails with `DuplicateKeyError: duplicate JSON key 'bypass_actors'`; fixtures read with `loads_strict` (`test_contracts.py:22,26`) | Remaining `json.loads` in tests read the real registry (`sandbox_repo.py:64`, `test_corrections.py:1004`), whose duplicates `check` already rejects | **Fixed** |
| V-15 | Tests added for H1..H12; mutation check at R | **M35 (dropped-item rule) and M37 (ini-override rule) survive** the suite (§5): the V-01 tests are also caught by the file-list rule, so neither rule is tested on its own (X-14) | **Partly fixed** |
| V-16 | `pytest ... --citerift-report $W/exp/nonexistent-dir/sub/report.json`: `3 passed`, report written (865 bytes) | — | **Fixed** |

Spot check of F-01 to F-23 at R (original scripts, `$W/orig_run1.log`, `$W/orig_run2.log`, and the audit's own scripts):

- F-01: TREESAME merge, octopus merge, mode-only change → `VERIFICATION_STALE`; change-then-restore → `0 errors`. Holds.
- F-02: edited artifact → `EVIDENCE_STALE` x2; rewritten report totals → `TEST_EVIDENCE_STALE`, `TESTS_FAILED` x2, `EVIDENCE_STALE`; gates `["."]` → 32 errors; new file → `EVIDENCE_UNLISTED`. Holds (bypass X-01).
- F-03: audit `policy_edit.py`: `drop_ci`, `shrink_gates` → `REGISTRY_SCHEMA`; `drop_owned_paths` + owned change → `DEFINITION_CHANGED`, `DEFINITION_WEAK`; `gate_dot` → 32 errors. Holds.
- F-04, F-05: `HISTORY_DEPENDENCY`, `HISTORY_SINGLE_ACTIVE`, `HISTORY_AMENDMENT_MISSING`, `HISTORY_BLOCKER`; amendment 10 minutes after the reopening → `HISTORY_AMENDMENT_MISSING`. Holds.
- F-06: see V-06. F-07: see V-01. F-08 to F-10: audit `contracts_probe.py`: A, B, B2, D, D2, D3, E, F `INVALID`; C `VALID`, C2 `EVENT_ORDER`. Holds.
- F-11: adapted `f11.py`: reopen 00 while 02 accepted → `ALLOWED` with `WARNING DEPENDENCY_REOPENED`; authorize 03 meanwhile → `REFUSED`. Holds.
- F-13: truncated registry → `REGISTRY_UNREADABLE` (handoff point 9). F-15: default actor → `ACTOR_NOT_PERMITTED`. F-16: `--at 2030` → `TIMESTAMP_IN_FUTURE`. F-17: authorization ref reused → `OWNER_REF_REUSED`; record time mismatch → `RECORD_HISTORY_MISMATCH` x2. F-18: duplicate key (also `\u` escaped) → `REGISTRY_UNREADABLE`; in report → `TEST_EVIDENCE_INVALID`. F-19: `UNCOMMITTED_OWNED_CHANGE`. F-12, F-14, F-20, F-22, F-23: covered by passing tests / files present. All hold.

## 3. Confirmed new findings

Severities are my judgment. None is critical. All "check" outputs are from R's code.

### X-01 Gate evidence outside the owned paths counts as pinned through `..` or a symlink (Low-Medium; bypass of V-02)

- Code: `src/citerift/governance/orchestrator.py:850-852` (`_owned` is a string-prefix test), used at `:825`;
  `evidence.inside` (`evidence.py:57-59`) only checks that the resolved path is inside the repository. The schema's
  `evidence_ref` pattern allows `..`.
- Reproduction: `$W/clone/.venv/bin/python -P $W/scripts/x_gate_owned_alias.py` (fresh sandboxes, Stage 00 verified
  through `propose` with every gate citing the given reference, then `NOTES.md` rewritten and committed):
  ```
  [dotdot] gate evidence 'tests/stage00/../../NOTES.md': verify ALLOWED []
  --- dotdot: after rewriting NOTES.md [exit 0]
  Consistency check: 0 errors, 0 warnings
  [symlink] gate evidence 'tests/stage00/ev.md': verify ALLOWED []      (ev.md -> ../../NOTES.md, committed)
  --- symlink: after rewriting NOTES.md [exit 0]
  Consistency check: 0 errors, 0 warnings
  diff of owned paths since verified revision: (none)
  [control] gate evidence 'NOTES.md': verify REJECTED ['GATE_EVIDENCE_UNPINNED']
  ```
- Contradicts GOVERNANCE.md invariant 1 ("Every file a gate cites must be hash-pinned"), SPECIFICATION §Verification 1,
  MATHEMATICAL_MODEL §6, CHANGELOG ("every file a gate cites must be pinned").
- Smallest fix: in `_gate_findings`, decide ownership on the resolved path:
  `rel_resolved = (root/ref).resolve().relative_to(root.resolve()).as_posix()`, require it to be owned or in the manifest,
  and reject references containing `..` or passing through a symlink (or require `ref` to be tracked and not a symlink:
  `git ls-files -s` mode `120000`).

### X-02 A one-line committed `pyproject.toml` change narrows the run and the report is still "complete" (Medium; bypass of V-01)

- Code: `src/citerift/governance/pytest_report.py:77-102` (`_selection` treats the repository `pyproject.toml` as
  trusted and inspects only CLI overrides); `evidence.py:178-189` compares files, not tests. `pyproject.toml` is not a
  Stage 00 owned path.
- Reproduction (clone `$W/exp/v01` at R; names picked by `$W/scripts/pick_names.py`, one test function per
  (file, suite); inserted by `$W/scripts/narrow_pyproject.py`):
  ```
  git diff --stat 9e025c9         ->  pyproject.toml | 1 +   (python_functions = ["test_01_valid_stage_authorization", ... 20 names])
  python -P -m pytest -q -p no:cacheprovider --citerift-report docs/verification/stage-00/test-report.json
                                  ->  92 passed in 26.30s
  python -P $W/scripts/rcheck.py . docs/verification/stage-00/test-report.json
     collected 92 totals {'passed': 92} dirty False exit 0
     selection {... 'override_ini': [], 'other_ini_file': '', ..., 'complete': True, 'deselected': 0, 'dropped': 0} files 11
     check_test_report problems: []
  owned-path files changed vs R: (none)
  ```
  The honest run of the same tree records 308 tests (`collected 308`, `problems: []`).
- Contradicts R-016 ("The test report check rejects the narrowing that such a configuration change could cause
  (V-01)"), GOVERNANCE invariant 1, SPECIFICATION §Verification 4, review/README V-01 "fixed".
- Smallest fix: record in the report the ini values that affect collection (`python_files`, `python_classes`,
  `python_functions`, `testpaths`, `norecursedirs`, `addopts`) and require them to equal fixed defaults, or make
  `pyproject.toml`'s `[tool.pytest.ini_options]` part of the verification definition (hash it into the record).
  Stronger: record the set of collected node ids and compare it with an independent `--collect-only` under fixed
  options.

### X-03 Padding defeats the "dropped item" rule; the forging code need not be committed (Low-Medium; bypass of V-01, R-004 understated)

- Code: `pytest_report.py:105-110, 162-173` (`dropped = itemcollected - final_items - deselected` counts items, not
  distinct node ids; `_suites_of` is keyed by node id).
- Reproduction (`$W/exp/v01` at R, `$W/scripts/pad_conftest.py`: keep one test per (file, suite), pad the list back
  to its original length by repeating kept items):
  ```
  A committed tests/conftest.py:         308 passed in 176.12s
     collected 21 totals {'passed': 21} dirty False exit 0
     selection {... 'complete': True, 'deselected': 0, 'dropped': 0} files 11
     check_test_report problems: []
  C nothing in the repository; PYTHONPATH=$W/scripts pytest -p pad_conftest --citerift-report ...:
     308 passed; collected 21 ... 'complete': True ... problems: []
  D tests/conftest.py uncommitted, listed in .git/info/exclude (git status: empty):
     308 passed; collected 21 dirty False ... 'complete': True ... problems: []
  ```
  21 distinct tests of 308 ran; the terminal shows `308 passed`.
- GOVERNANCE invariant 1 and R-004 say "code committed in a test or `conftest.py` file could still forge it". Cases C
  and D leave no committed trace and give `dirty: False`. CHANGELOG ("rejected when ... a hook narrowed the run") and
  SPECIFICATION ("nothing removed by a conftest hook") overstate.
- Smallest fix: compare distinct node ids: record the set at `pytest_itemcollected` and at the end of collection, and
  require equality and no duplicates (`len(items) == len({i.nodeid for i in items})`). Record `-p` plugins
  (`config.option.plugins`), `PYTEST_PLUGINS`/`PYTEST_ADDOPTS` and the loaded `conftest` paths in the report, and treat
  any extra plugin or untracked conftest as partial. State in R-004 that any code in the test process (including
  uncommitted files and command-line plugins) can forge the report.

### X-04 CI's governance check can still be neutralized without touching an owned path (Low-Medium; bypass of V-04)

- Code: `.github/workflows/ci.yml` (`PYTHONPATH: src`, `python -P -m ...`). `-P` stops the script directory being
  prepended; it does not stop `site` from importing `sitecustomize` found on `PYTHONPATH`, and `PYTHONPATH` precedes
  site-packages. Only `src/citerift/{__init__.py,governance,contracts,py.typed}` are owned.
- Reproduction (`$W/exp/v04`, branch from R; shim `$W/scripts/sitecustomize_shim.py` filters error findings only for
  `Orchestrator` instances rooted at the working directory):
  ```
  commits: registry history entry 10 (Stage 00 acceptance) actor -> engineering-agent; PROJECT_STATUS.md re-rendered;
           src/sitecustomize.py added (23 lines, ruff/mypy clean)
  git diff --stat 9e025c9: PROJECT_STATUS.md | 2, governance/stage_registry.json | 2, src/sitecustomize.py | 23
  owned-path files changed: (none)
  with PYTHONPATH=src, the ci.yml steps in order:
    uv lock --check                         Resolved 45 packages in 2ms        exit 0
    guard (citerift imported from src)                                          exit 0
    ruff check / format --check / mypy      All checks passed! / 58 files already formatted / Success: no issues found in 13 source files
    python -P -m citerift.contracts.validate check-schemas    2 schemas checked, 0 problems   exit 0
    python -P -m citerift.governance.cli check                Consistency check: 0 errors, 0 warnings   exit 0
    python -P -m citerift.governance.cli render-status --check  PROJECT_STATUS.md is up to date  exit 0
    python -P -m pytest --citerift-report ci-test-report.json  308 passed in 112.36s    exit 0
  honest code (R clone, --root $W/exp/v04): Consistency check: 1 errors
    ERROR HISTORY_ACTOR: [stage 00] entry 10: VERIFIED_AWAITING_OWNER_ACCEPTANCE -> ACCEPTED_CLOSED requires the owner, recorded actor is engineering-agent
  ```
  Same root cause: with `src/jsonschema/__init__.py` (`raise SystemExit("shadow jsonschema loaded from src/")`), the CI
  `check` command prints `shadow jsonschema loaded from src/`. `pip-audit` was not run (network). GitHub was not
  exercised.
- GOVERNANCE.md and R-016 state that CI "runs the checked-out `src/` modules" so the checker cannot be replaced except
  through `uv.lock` dependencies; any non-owned file directly under `src/` can do it as well. Detection from an honest
  copy still works, as GOVERNANCE says.
- Smallest fix: run the checks with `python -I` (or `-S`) and put `src` on the path explicitly inside the command
  (`python -I -c "import sys; sys.path.insert(0, 'src'); ..."`), or own all of `src/` (or fail `check` when `src/`
  contains anything outside `src/citerift`); list the residual in R-016.

### X-05 Remaining tracebacks (Low; residual of V-10)

- Code: `orchestrator.py:732` and `:1057` (`read_text` without `UnicodeDecodeError` handling), `cli.py:342-346`
  (only `OSError, ValueError` around schema use; `SchemaError`/`TypeError`/`AttributeError`/referencing errors escape),
  `Orchestrator.stage` `KeyError` reaching `cmd_deps`/`readiness`/`handoff`/`add_blocker`/`add_amendment`,
  `orchestrator.py:1327` (`sha256_file` on a missing `--test-report`), `cli.py:111-113` (`--record` not a dict),
  `evidence.py:136-164` (counts assumed numeric and dicts).
- Reproduction: `$W/clone/.venv/bin/python -P $W/scripts/x_tracebacks.py`; every case exits 1 (fail closed):
  ```
  [PROJECT_STATUS.md not UTF-8: check] TRACEBACK: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 4846
  [PROJECT_STATUS.md not UTF-8: render-status --check] TRACEBACK: UnicodeDecodeError ...
  [PROJECT_STATUS.md not UTF-8: recover] TRACEBACK: UnicodeDecodeError ...
  [deps 99 | readiness 99 | handoff 99 | blocker add 99 | amend 99] TRACEBACK: KeyError: 'unknown stage 99'
  [schema {"type": 5}: check] TRACEBACK: TypeError: 'int' object is not iterable
  [schema []: check] TRACEBACK: AttributeError: 'list' object has no attribute 'get'
  [schema {"$ref": "#/nope"}: check] TRACEBACK: jsonschema.exceptions._WrappedReferencingError: PointerToNowhere
  [HANDOFF.md not UTF-8 (verified stage): check] TRACEBACK: UnicodeDecodeError ...
  [amend --test-report missing file] TRACEBACK: FileNotFoundError ...
  [--record with gates as a list] TRACEBACK: AttributeError: 'list' object has no attribute 'update'
  [--record that is a JSON list] TRACEBACK: AttributeError: 'list' object has no attribute 'get'
  [test report totals.passed is a string: check] TRACEBACK: TypeError: '<=' not supported between instances of 'str' and 'int'
  [test report suite counts are a list: check] TRACEBACK: AttributeError: 'list' object has no attribute 'get'
  ```
  The test-report cases matter most: `check` on a verified stage crashes instead of naming the bad evidence.
- Smallest fix: catch `KeyError` in `main` (→ `STAGE_UNKNOWN`), `UnicodeDecodeError` for status/handoff
  (→ `STATUS_DOC_OUT_OF_DATE` / `HANDOFF_UNREADABLE`), validate the registry schema with
  `Draft202012Validator.check_schema` inside the existing `try`, validate the report against a small JSON schema before
  reading counts, and check `--record`/`--test-report` inputs.

### X-06 A heading that does not parse is still skipped when its fields are also written differently; invisible characters split topics (Low; residual of V-06)

- Code: `memory.py:23` (`_HEADING_LIKE` requires an ASCII `-` or nothing between the letter and the digits, ATX only),
  `:24` (`_FIELD` needs `- Name: value` exactly), `:81-83` (`normalize_topic` keeps format characters).
- Reproduction: `$W/scripts/x_memory.py` on the accepted sandbox (appended to RISKS.md / DECISIONS.md):
  ```
  [defect control]                               1 errors ['OPEN_CRITICAL_DEFECT']
  [defect "### R–020 — ..." + "- **Status**: open" ...]   0 errors, 0 warnings []
  [defect "## R–020 — ..." + "- status: open" ...]         0 errors, 0 warnings []
  [defect setext heading + indented "  - Status: open" ...] 0 errors, 0 warnings []
  [topic control 'Sandbox']                      DECISION_CONTRADICTION
  [topic 'sand​box'] / ['sand­box']    0 errors, 0 warnings
  ```
  Bold field names are a common Markdown style. (The table-row form is disclosed by GOVERNANCE invariant 7.)
- GOVERNANCE invariant 7 says "An entry heading that does not parse ... is an error"; the heading itself is never
  reported unless `_HEADING_LIKE` matches, and CHANGELOG says "Unparsed entry headings ... are errors".
- Smallest fix: make `_HEADING_LIKE` accept any dash-like character or none (`[\-‐-―−_]?`) after an NFKC
  pass and also setext/HTML forms; treat `- **Status**:`, lowercase or indented field names as fields (and so as
  orphans); in `normalize_topic` remove `unicodedata.category(c) == "Cf"` characters.

### X-07 Removing a dependency before authorization bypasses invariant 3 (Low-Medium; residual of V-03)

- Code: schema `stage.depends_on` is free (`stage_registry.schema.json`), the dependency guards use the current
  `depends_on` (`orchestrator.py:182-192, 457`); the definition hash binds it only from verification on.
- Reproduction (`$W/scripts/x_history.py`, part B; fresh sandbox, Stage 00 accepted, Stage 01 `NOT_STARTED`):
  ```
  02 depends_on before: ['00', '01']   -> edited to ['00'] (plus owned_paths ['impl/02.txt']), committed
  01 status: NOT_STARTED
  accept 02 while 01 NOT_STARTED: ALLOWED []
  --- B: Stage 02 verified and accepted without Stage 01 [exit 0]
  Consistency check: 0 errors, 0 warnings
  ```
  Stage 01 is the external feasibility investigation that Stages 02 and 03 depend on (R-007). Executors were fixed in
  the schema for exactly this kind of edit (V-03); dependencies were not. R-003 and GOVERNANCE list "gates, suites,
  owned paths, verification directory" as editable before verification; `depends_on` is not mentioned.
- Smallest fix: fix `depends_on` per stage id in the schema (as `executor`), or pin the Master Plan graph in an owned
  file and compare; at least list `depends_on` in R-003 and GOVERNANCE.

### X-08 Honest add → block → resolve within one second is refused, with a misleading "(pre-existing)" label (Low; V-11 area)

- Code: `orchestrator.py:126-140` (`_now` gives the blocker `last+1` but the resolution `max(now, recorded)`, i.e. the
  same second as the `BLOCKED` entry), `:497` (a blocker resolved at `t` is not open at `t`), `:1294-1304` (resolution
  proposes on an already-changed registry, so its own error is labelled "pre-existing").
- Reproduction: `$W/scripts/x_same_second.py` (accepted sandbox, all default times, in-process):
  ```
  attempt 0: resolve REJECTED at 2026-10-25T19:27:51Z: ['ERROR HISTORY_BLOCKER: [stage 02] (pre-existing) entry 13 blocks the stage with no open blocker']
     history times: ['2026-10-25T19:27:51Z', '2026-10-25T19:27:51Z', '2026-10-25T19:27:52Z'] blocker opened_at 2026-10-25T19:27:52Z
  ```
  Fail closed, and a retry one second later succeeds; the message tells the user the registry was already broken,
  which it was not.
- Smallest fix: default `resolve_blocker`'s time with `after_history=True` (strictly after the last entry and after
  the blocker's `opened_at`); compute `before` from `self.registry`, not from the changed copy.

### X-09 `.git/info/grafts` is still honoured (Low, local only; residual of V-13)

- Code: `gitutil.py:17-27` (`_git`); the comment at line 22 says "Replace refs and grafts ... never honour them", but
  `--no-replace-objects` does not disable grafts (git 2.43.0).
- Reproduction: `$W/scripts/x_graft.py` (accepted sandbox; HEAD rewritten as an orphan commit with the same tree):
  ```
  orphan HEAD: Consistency check: 7 errors, 0 warnings ['REVISION_NOT_IN_HISTORY']
  orphan HEAD + .git/info/grafts: Consistency check: 0 errors, 0 warnings
  ```
  Drift is unaffected (tree diffs). Grafts are not cloned, so CI is not affected.
- Smallest fix: set `GIT_GRAFT_FILE=/dev/null` (and `GIT_NO_REPLACE_OBJECTS=1`) in `_git`'s environment, or report an
  existing `.git/info/grafts`; correct the comment.

### X-10 Acceptance with an open blocker passes the history replay; the model has no such guard (Low)

- Code: `orchestrator.py:497-515` (blocker rules checked at block, start, unblock and verify, not at accept);
  `simulations/stage00/state_machine_model.py` `guard`: `accept` ignores `blockers_open`;
  `replay_conformance.py:129-131` compares the model only with `_history_findings`, so both agree.
- Reproduction: `$W/scripts/x_history_a2.py` (hand edit on the accepted sandbox: blocker on Stage 01 opened at the
  acceptance second, resolved later):
  ```
  --- A2: acceptance while a blocker was open [exit 0]
  Consistency check: 0 errors, 0 warnings
  --- A2 control: blocker still open [exit 1]
  ERROR BLOCKER_OPEN: [stage 01] unresolved blocker B-01-001: external handoff missing a section
  ```
  GOVERNANCE invariant 7 ("A verified or accepted stage has no open blocker") holds only for the current state.
  `citerift-gov` itself cannot produce this (adding a blocker to a verified stage is refused), so it is a hand-edit
  detection gap.
- Smallest fix: add `(VA, AC)` to the "no open blocker" list in `_replay_step_findings` and `not inp.blockers_open` to
  the model's `accept` guard; re-run the conformance.

### X-11 The language-code pattern rejects an open Wikipedia edition (Low; contract)

- Code: `schemas/contracts/v1/common.schema.json` `wiki_language`: `^[a-z][a-z0-9]{1,11}(-[a-z0-9]{1,8})*$`.
- Reproduction: `$W/scripts/x_contracts.py .` (valid full fixture with the citation language replaced):
  `wiki language 'zh-classical': INVALID -> ... does not match '^[a-z][a-z0-9]{1,11}(-[a-z0-9]{1,8})*$(?!\n)'`
  (`zh-yue`, `zh-min-nan`, `be-tarask`, `be-x-old`, `roa-tara`, `nds-nl`, `map-bms`, `cbk-zam`, `fiu-vro`, `bat-smg`,
  `roa-rup` are `VALID`). Checked against the live Wikimedia site matrix (`$W/sitematrix.json`, fetched with
  `action=sitematrix`): 348 open and 16 closed Wikipedia editions; the pattern rejects exactly one,
  `('zh-classical', 'zh_classicalwiki', 'open')`.
- The schema describes the field as "Wikipedia language edition code (subdomain)" and docs/data-contracts.md and R-006
  call language codes "deliberately permissive".
- Smallest fix: allow longer subtags (`-[a-z0-9]{1,12}`), as a backward-compatible minor version (amendment needed,
  `schemas/contracts/v1` is owned).

### X-12 A Stage 00 regression test fails once Stage 01 is accepted or Stage 02 authorized (Low; liveness, fail closed on an honest repository)

- Code: `tests/stage00/test_repository.py:43-49`
  (`assert s["status"] == "NOT_STARTED"` for every stage other than 00 and 01; `assert orc.stage("01")["acceptance"] is None`).
- Reproduction: scratch clone at R, Stage 01 given a synthetic placeholder acceptance record (status fields only, no
  Stage 01 content); `pytest tests/stage00/test_repository.py::test_no_stage_beyond_00_is_authorized_for_the_engineering_agent`:
  `E AssertionError: Stage 01 findings are not accepted` / `1 failed`.
- The planned next owner decisions (accept Stage 01, authorize Stage 02) make the required CI test step fail. The test
  is under a Stage 00 owned path, so fixing it makes Stage 00 `VERIFICATION_STALE` and needs an amendment.
- Smallest fix: assert the rule, not today's state: no stage beyond 01 is active without an owner authorization entry
  in the history, and Stage 01 has no acceptance unless an owner history entry records one.

### X-13 An enhancement amendment changes accepted contracts with no CI, no compatibility check and a reused owner reference (Low-Medium)

- Code: `orchestrator.py:1002-1017` (an enhancement needs only a revision and a passing complete report),
  `:916-921` (it then covers owned-path drift); no check of contract compatibility, `x-citerift-version` or owner
  reference reuse for amendments; `cli.py` `amend` accepts any `--owner-ref`.
- Reproduction: `$W/scripts/x_enhancement.py` (accepted sandbox):
  ```
  investigation.schema.json: retraction_status value enum gains "not_retracted" (x-citerift-version still 1.0.1)
  --- owned contract changed, no amendment [exit 1]   ERROR VERIFICATION_STALE ...
  amend 00 --kind enhancement --owner-ref cmsg_TESTACCEPTREF0005 (the acceptance's own ref) --revision <rev> --test-report ...
     -> Recorded amendment A-00-001
  --- after the enhancement amendment [exit 0]   Consistency check: 0 errors, 0 warnings
  Stage 00 status: ACCEPTED_CLOSED | ci in amendment record: False
  record stating 'not_retracted' as verified fact under the accepted contract: VALID
  ```
  The sandbox report is synthetic, like the project's own sandbox tests. In the real repository the same change also
  needs the matching invalid-case fixture under `tests/stage00` (owned, so the same enhancement covers it) for the real
  suite to pass.
- GOVERNANCE ("Enhancement that preserves contracts") and docs/data-contracts.md ("a minor version needs an
  owner-approved `enhancement` amendment"; "Breaking changes need a new major directory") state rules the tool does not
  check. This is the one path by which accepted Stage 00 content changes without a new verification.
- Smallest fix: require for an enhancement a CI record at its revision and an `owner_ref` not cited before; run
  `check_backward_compatible` against the fixtures of the accepted revision for changes under `schemas/contracts/`;
  require an `x-citerift-version` increase when a contract schema changes.

### X-14 Two of the 54 mutants survive at R (Low; test adequacy, V-15)

- `M35 V-01 items dropped by a conftest ignored: SURVIVED ['308 passed in 108.79s (0:01:48)']`
- `M37 V-01 ini overrides allowed: SURVIVED ['308 passed in 112.07s (0:01:52)']`
- Cause: the V-01 test cases (`test_v01_narrowing_by_configuration_or_conftest_is_partial`) each also omit a whole
  file, so `_files_not_run` already fails them; the dropped-item and override rules are not tested where they alone
  decide (narrowing inside files). The documents at R claim only that 54 mutants are run (RISK_ANALYSIS §3,
  CREATIVE_DIFFERENTIATION_REVIEW §1.2), with results deferred to TEST_RESULTS.md §5, so there is no false count in the
  written documents. (The unreviewed `7138d6d` appears to address this.)
- Smallest fix: add tests that narrow within a file (`-o python_functions=test_alpha`, a conftest dropping one of two
  items in the same file) and assert `TEST_EVIDENCE_PARTIAL`.

## 4. Documentation accuracy

Accurate (checked against behaviour): GOVERNANCE.md "Authority", lifecycle, invariants 2, 4, 6 and the "Prevented"
paragraph (pre-existing errors do not block a blocker or amendment: `mutate_pre.py` → `Recorded blocker B-02-001`,
`Recorded amendment A-00-001`, error still reported); R-001, R-002, R-012 (now states that a fast clock blocks, fail
closed); R-018 counts (1 medium, 3 low-medium, 12 low); review/README dispositions for V-05, V-08, V-09, V-12, V-14,
V-16; fail-first counts (`results-135e4ac.txt`: 36 `FAILED` lines, `36 failed, 269 passed`; `results-ae2ce9e.txt`: 82,
`82 failed, 178 passed`; per-finding table sums to 36); `uv.lock` sha256 `52980fe6…fe50` and unchanged since `741476c`;
model output sha256 `55ed9851…2ff0` equals the accepted `final-results.json`; 47 invalid contract cases; all test
names cited in SPECIFICATION, SIMULATION_REPORT, RISK_ANALYSIS and CREATIVE_DIFFERENTIATION_REVIEW exist; the Node
test fails rather than skips when `CI` is set (`test_contracts.py:267-268, 299-300`).

Overstated or inaccurate:

| File:line | Text | Evidence |
|---|---|---|
| GOVERNANCE.md:46-56 (invariant 1) | "every test file ... ran, with no narrowing option, ini override, other ini file or item dropped by a hook. Every file a gate cites must be hash-pinned ... code committed in a test or `conftest.py` file could still forge it" | X-02 (ini file itself edited), X-03 (padding; uncommitted conftest and `-p` plugin forge with no committed code), X-01 |
| GOVERNANCE.md:61-63 (invariant 3) | "A stage can be authorized, verified or accepted only when all of its dependencies are accepted" | X-07 (dependency list editable before verification, not disclosed) |
| GOVERNANCE.md:66-71 (invariant 5) | every entry satisfies "the blocker rules" | X-10 (acceptance not checked) |
| GOVERNANCE.md:79-84 (invariant 7) | "An entry heading that does not parse ... is an error" | X-06 |
| GOVERNANCE.md:158-161 | "(gates, suites, owned paths, verification directory) can still be changed before it is verified" | omits `depends_on` (X-07) |
| GOVERNANCE.md:170-175 | "CI runs the checked-out `src/` modules ... so changing the entry points ... does not replace the checker. The dependencies ... can still change what CI executes" | X-04: any non-owned file under `src/` also can |
| GOVERNANCE.md:104-106 ("Changing an accepted stage") | "Enhancement that preserves contracts" | not checked (X-13) |
| RISKS.md:66-68 (R-003) | editable fields "gates, suites, owned paths, verification directory" | X-07 |
| RISKS.md:80-83 (R-004) | "code committed in a test or `conftest.py` file ... could write a false report" | X-03 C/D: uncommitted or command-line code too |
| RISKS.md:226-232 (R-016) | "CI runs the checked-out `src/` modules directly, so the entry points ... cannot replace the checker (V-04). ... The test report check rejects the narrowing that such a configuration change could cause (V-01)." | X-04; X-02 contradicts the last sentence directly |
| CHANGELOG.md:23-27 | "every file a gate cites must be pinned" | X-01 |
| CHANGELOG.md:28-31 | "a report is rejected when a narrowing option, an ini override, another ini file or a hook narrowed the run" | X-02, X-03 |
| CHANGELOG.md:40-41 | "Unparsed entry headings and entry fields outside a recognized heading are errors" | X-06 |
| CHANGELOG.md:53-54 | "unreadable schemas, schema-invalid registries and non-UTF-8 memory files are reported without a traceback" | literally true; other inputs still crash (X-05) |
| SPECIFICATION.md:60-67 | gate evidence "must be a pinned file ... or a file under the stage's owned paths" | X-01 |
| SPECIFICATION.md:79-86 | "nothing removed by a conftest hook" | X-03 |
| SPECIFICATION.md:117-118, MATHEMATICAL_MODEL.md:161 | "A heading that looks like an entry but is malformed is an error"; "`|C| − |F| − |D| = 0` (no item dropped silently)" | X-06; X-03 (counts, not sets) |
| SIMULATION_REPORT.md:35-37 | "`replay_conformance.py` checks that `check` accepts exactly the histories the model permits" | it compares `_history_findings` only (`replay_conformance.py:129-131`); full `check` refuses some model-permitted histories (accept with an open blocker → `BLOCKER_OPEN`), and the model itself lacks that guard (X-10). MATHEMATICAL_MODEL §5 ("no history error") is the accurate wording |
| RISK_ANALYSIS.md:47 | "Prevented: verification refuses ... a run narrowed by ini override, other ini file or conftest" | X-02, X-03 |
| docs/verification/stage-00/review/README.md:27, 30, 41 | V-01 "fixed"; V-04 "fixed"; V-15 "tests added" | §2 (partly fixed; M35/M37 survive) |
| docs/data-contracts.md:97-106 | minor version "needs an owner-approved `enhancement` amendment"; breaking changes need `v2/`; language codes "deliberately permissive" | X-13 (not enforced), X-11 |
| `src/citerift/governance/gitutil.py:22` (comment) | "Replace refs and grafts ... never honour them" | X-09 |

Placeholders `{{RVER7}}`/`{{HANDOFF_PASSED}}` in SIMULATION_REPORT and the absence of TEST_RESULTS.md/HANDOFF.md were
not counted, as instructed.

Identity (docs/identity.md): `git grep -i -E "<name terms, redacted>"` at R, excluding the login `ImanOthman-eng`, finds
nothing in any file. The login appears only in ownership-type records (CODEOWNERS, OWNERSHIP.md, registry
`github_login`, DECISIONS.md, RISKS.md R-001, GOVERNANCE.md, docs, archived evidence), which rule 2 allows. Registry
`display_name` is `EVE TELOS`; `pyproject.toml` authors `EVE TELOS · IM`; README carries the identity line. No file
presents an AI tool as creator or owner (searched "created/built/authored/developed/directed by" Claude/AI: none;
OWNERSHIP.md "AI-assisted engineering" calls agents tools). Commits `5749e9c`, `950e005`, `9e025c9` carry
`Assisted-by: Claude Code (AI coding agent)` and no `Co-Authored-By`/`Claude-Session`, with the environment's identity
`Claude <noreply@anthropic.com>`. Observation, not a file: the GitHub merge commit of PR #1 has author metadata with
the owner's name and email (set by GitHub; rule 5, historical records are not rewritten).

## 5. Evidence scripts

| Script | Command (clone) | Result |
|---|---|---|
| mutation check | `uv run --no-sync python docs/verification/stage-00/mutation/mutation_check.py` (`$W/mut`, at R) | **`54 mutants, 52 killed, 2 survived`**, exit 1, `real 21m52.671s`. Survivors: `M35 V-01 items dropped by a conftest ignored: SURVIVED ['308 passed in 108.79s']`, `M37 V-01 ini overrides allowed: SURVIVED ['308 passed in 112.07s']`. All patterns found exactly once; tree clean afterwards. Log `$W/mutation.log` |
| replay conformance, full | `uv run --no-sync python simulations/stage00/replay_conformance.py --config full --output $W/replay-full.json` | 205,632 cases, 205,632 agreements, **0 disagreements**, 459 vectors, 15,640 model-permitted, max history 28; `real 0m33.063s`; output byte-identical to `docs/verification/stage-00/simulation/replay-conformance-full.json` (`cmp`). Scope caveat: compares `_history_findings` only (X-10) |
| abstract model | `uv run --no-sync python simulations/stage00/state_machine_model.py --output $W/model-results.json` | sha256 `55ed9851ea007d4fb10253aad1a6cfe733c474dbc876097d6923e2985dcb2ff0`, identical to the committed and accepted files; `real 0m15.276s` |
| handoff simulation | `uv run --no-sync python docs/verification/stage-00/handoff/handoff_simulation.py 9e025c98… $W/handoff-result.json` | **12/12 PASS** (points 1, 8, 2, 3, 10, 4, 7, 7b, 5, 6, 9, 10b); `real 0m3.058s`. Caveat as before: Stage 00 is not verified at R, so 7b and the self-acceptance part of 6 run without drift or acceptance checks |

Mutation-script observation: `killed = r.returncode != 0` with no baseline run, so a suite that fails for an unrelated
reason would report every mutant killed. At R the baseline passes (308 passed), so the result above stands.

## 6. Not reproduced or speculative

- GitHub was not exercised: whether a pull request with X-04's `src/sitecustomize.py` gets a green `ci-gate` there
  (inferred from running the ci.yml steps locally with `PYTHONPATH=src`; `pip-audit` not run, no network for it).
- Other process-level forgeries of the report (running the suite with `PYTHONPATH` pointing at a different `citerift`,
  `PYTEST_PLUGINS`) follow from X-03's mechanism; only `-p` and an ignored conftest were run.
- A committed test file under `tests/` that pytest does not collect (for example a helper named `test_*.py` with no
  tests, or under a `norecursedirs` directory) would make every honest report partial (`_files_not_run`); none exists
  at R, so this is a future false-positive risk only.
- `--recorded-by owner` is accepted for transitions recorded by the agent (self-declared, like F-15's variant); covered
  by R-001/R-002, not tested further.
- A `.DS_Store` in a verified evidence directory gave `EVIDENCE_UNLISTED` in the sandbox, but only because the sandbox
  has no `.gitignore`; the real `.gitignore` ignores it. Not a finding.
- DOI prefixes with dotted registrant codes (`10.1000.10/...`) are rejected by the `doi` pattern; not checked against
  real data.
- Severity ratings are judgments.

## 7. Verdict

Most of the first review's findings are fixed at R. The original reproductions of V-02 (URL-only and mixed gates),
V-03, V-05, V-07 (case 3), V-08, V-09, V-10, V-12, V-13, V-14 and V-16 are now refused or named, and the F-01 to F-23
spot checks still hold. The tools are clean (308 passed, ruff, format, mypy, `check`, schemas, lock), the replay
conformance (0 disagreements, identical output), the model output and the handoff simulation (12/12) reproduce.

The central claims still do not hold in full:

- A partial test run can be recorded as complete by one committed `pyproject.toml` line (X-02: 92 of 308 tests), or by
  padding with no committed trace (X-03: 21 of 308).
- Gate evidence outside the owned paths counts as pinned (X-01).
- CI's governance check can be neutralized by a non-owned file under `src/` (X-04).
- Accepted contracts can be changed through an enhancement amendment with no CI and a reused owner reference (X-13).
- Removing a dependency lets Stage 02 be accepted without Stage 01 (X-07).
- The mutation check itself reports 2 survivors (X-14).

GOVERNANCE.md, RISKS.md (R-003, R-004, R-016), CHANGELOG.md, SPECIFICATION.md and SIMULATION_REPORT.md overstate
several of these controls (§4). This review records no stage state and makes no owner decision.

NOT VERIFIED
