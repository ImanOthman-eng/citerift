# Stage 04 Step 7: open-source leverage review for the Workflow Controller

Status: Step 7 record, written before any controller code. It follows the owner's permanent rule of 2026-11-10
(message `cmsg_018VCB51nDHP6HXmLU4ea5yP2h9GM56jQT5F4jCEcUv9zu`) and the Step 7 instruction, item 1
(`cmsg_018VCB51nDHP6HXmLU4ea5yPDQM4CSrgtLVKEZ4HCN1Yto`).

**Baseline to beat.** A small controller owned by CITERIFT, built on what already exists in Stage 04:

- SPEC 9 and MM 7 to 10 specify its legal behaviour. The fold (`Folder`, Step 6) already derives step states,
  attempts and the lifecycle from the journal.
- The Step 4 controller model (`simulations/stage04/controller_model.py`) explored it exhaustively: 25,120 states and
  0 violations.

Step 7 adds the transition guard, the budgets, `not_before`, staleness and the adapter boundary on top of the fold.

**Result: no dependency is adopted.**
- Each finite-state-machine library would hold a second, in-memory state next to the fold, which W-1 forbids.
- Each workflow engine would bring its own state store and a server or database.
- Each retry library would put sleeping retry loops inside the process, where SPEC 9.2 needs retries to be journal
  records under budgets.

The details are below.

## 1. Method (2026-11-10)

- **Version, upload date, declared licence, Python classifiers and direct dependencies:** from the PyPI JSON API.
- **Known vulnerabilities:** from the OSV API (ecosystem PyPI), queried per package.
- **Maintenance:** judged only by the date of the latest release and the number of releases. Commit history and issue
  response were not examined.
- No candidate was installed, and no code was copied.

## 2. What the controller must do that a library would have to support

Each requirement comes from SPEC 9, 10 and MM 8.

1. **R-1, state is a function of the journal (W-1).** After a crash, `fold(J)` is the whole state, so a library state
   object would have to be rebuilt from the journal on every open and never be authoritative.
2. **R-2, guards depend on the journal.** They read the counters `φ` and `f`, the attempt numbers, `not_before`
   compared with the record's time, root binding and committed content (T-START … T-STALE).
3. **R-3, the transition is a record.** It is appended, `fsync`ed and checked by Memory before it counts. A transition
   that exists only in memory is not a transition.
4. **R-4, deterministic replay.** There are no timers, threads, background tasks or randomness. The controller never
   sleeps (SPEC 9.2: a `BLOCKED` run exits and is resumed later).
5. **R-5, process death at any boundary.** The design must survive it, with recovery by W-6.
6. **R-6, offline and auditable.** No network, no telemetry, small code that a reviewer can read against SPEC 9.2.

## 3. Candidates

Common to every candidate: none needs network access to run, and all are pure Python unless noted. "POSIX" is yes for
all of them.

### 3.1 State-machine libraries

**transitions:**
- Release 0.9.3 (2025-07-02, 50 releases), github.com/pytransitions/transitions.
- MIT; one dependency, `six` (MIT). Python 3.10–3.13 declared. OSV: none recorded.
- Gives states, triggers, conditions and callbacks on a model object, plus hierarchical and diagram extensions.
- Replay: deterministic, but the state lives in the model object (R-1).
- Saves the declaration of 6 step states and 11 transitions.
- Adds a second state representation, callbacks that hide the order of effects, and a mapping from fold to model
  object on every open. Conditions would still be our own code reading the fold (R-2), and records would still be
  appended by us (R-3).
- Auditability and testability: worse than a table of explicit guard functions. Transitions spread across callback
  names are harder to check line by line against SPEC 9.2.
- **REFERENCE ONLY** (its condition and transition vocabulary).

**python-statemachine:**
- Release 3.2.2 (2026-10-14, 42 releases), github.com/fgmacedo/python-statemachine.
- MIT; no dependencies. Python 3.10–3.15 declared.
- OSV: GHSA-v4jc-pm6r-3vj8 / CVE-2026-47103, eval injection in its SCXML `<data expr>` support, affecting 3.0.0 to
  below 3.2.0 and fixed in 3.2.0.
- Gives declarative states and transitions, guards, validators, SCXML import and diagrams.
- Replay: deterministic, but stateful (R-1). Its async engine and SCXML evaluation are surface CITERIFT would not use,
  and the advisory shows that surface has carried a code-execution defect.
- Saves about the same as transitions. It adds the same second representation, plus an SCXML and expression-evaluation
  surface.
- **REJECT** (the security surface is unnecessary; no correctness gain over the fold-based guard).

**Automat:**
- Release 25.4.16 (2025-04-16, 14 releases), github.com/glyph/automat.
- MIT; depends on `typing_extensions`. Python 3.10–3.13 declared. OSV: none recorded.
- Gives input/output state machines whose state is private by design and cannot be set from outside. That is the
  opposite of R-1, where the state must be derived from the journal on every open. Its serialization hooks exist but
  restore a state; they do not derive one.
- Saves little and adds an object whose state the journal cannot set directly.
- **REJECT** (design conflict with W-1).

**sismic:**
- Release 1.6.14 (2026-10-05, 97 releases), github.com/AlexandreDecan/sismic.
- **LGPL-3.0**; depends on `behave`, `ruamel-yaml` and `schema`. Python 3.10–3.14 declared. OSV: none recorded.
- Gives statechart interpretation with contracts (pre/post conditions, invariants) and YAML statecharts.
- Its contract checking is interesting, but statecharts with YAML and an interpreter clock are a large surface.
- **REJECT** (licence gate: copyleft needs an owner decision, and nothing here justifies asking; dependency footprint).
- REFERENCE ONLY for the idea of checking invariants after every step. Step 7 already does that by checking
  W-1 to W-8 over the fold on every open.

### 3.2 Workflow engines and durable execution

**Temporal (temporalio 1.35.0, 2026-10-28):**
- MIT; depends on protobuf and nexus-rpc. Needs a Temporal server.
- **REJECT**: a server and its own event history as authority, which is a second state store against W-1, and network.

**Prefect 3.9.2 (2026-11-06):**
- Apache-2.0. Its direct dependencies include `amplitude-analytics` (telemetry), `asyncpg`, `alembic` and an API server.
- **REJECT**: telemetry, a database-backed state store and a large footprint.

**DBOS 3.5.0 (2026-11-10):**
- MIT; needs PostgreSQL through `psycopg` and SQLAlchemy.
- **REJECT**: its durable state lives in a database, not in the journal.

**Luigi 3.8.1 (2026-05-07):**
- Apache-2.0; depends on `tornado` and `python-daemon`. It is a task scheduler with a central server.
- **REJECT**: the wrong model (dependency scheduling of file targets), plus a daemon.

None of these is needed for a fixed eight-step plan run by one process under a lock.

### 3.3 Retry and backoff primitives

**tenacity 9.2.1 (2026-10-07):**
- Apache-2.0; no dependencies. OSV: none recorded.
- **REJECT**. It retries by calling the function again inside the process, after sleeping. SPEC 9.2 needs each attempt
  to be a journal record (`step_started(a + 1)` after `step_failed(retryable)`), counted by `φ` across process
  restarts. Budgets are spent by the journal, not by a decorator, and the controller never sleeps (R-4).

**backoff 2.2.1 (2022-10-05):**
- MIT. Only Python 3.10 is declared, and there has been no release since 2022.
- **REJECT**: same reasons as tenacity, and maintenance is uncertain.

**stamina 26.1.0 (2026-04-13):**
- MIT; depends on tenacity.
- **REJECT**: an opinionated wrapper of tenacity, with the same model conflict.

**The Stage 03 network retries** (`src/citerift/wiki`, accepted) already happen inside Stage 03, under its own policy.
Stage 04 only classifies their final outcome (SPEC 9.3).

### 3.4 Testing primitives

**hypothesis 6.170.15 (2026-11-06):**
- MPL-2.0; depends on `sortedcontainers`.
- **REJECT for Step 7**, unchanged from the Step 6 decision (licence gate, copyleft). Its stateful testing would suit
  the controller. Instead, Step 7 uses the method of Step 4: exhaustive enumeration of the abstract event alphabet up to
  bounded depth, plus a differential comparison of production against the frozen Step 4 model, plus seeded random event
  sequences from the standard library. This can be revisited if the owner decides on the licence.

**Model-based testing:** the reference model is the frozen Step 4 `controller_model.py`. It is CITERIFT's own, written
independently of `citerift`, and the differential harness drives both.

### 3.5 Process supervision

**psutil 7.2.2 (2026-01-28):**
- BSD-3-Clause. A C extension.
- OSV lists GHSA-qfc5-mcwq-26q8 and PYSEC-2019-41, a 2019 double free in old releases.
- **REFERENCE ONLY, deferred to Step 8.** Step 7 needs no child process: the D-042 kill wrapper is Step 8 (owner
  item 13). Process death in Step 7 tests uses `subprocess` and `os._exit` from the standard library. Step 8 will repeat
  this review for the wrapper itself, where `subprocess` with `start_new_session`, `os.killpg` and `waitpid` are the
  standard-library baseline.

## 4. Decision and what it costs

Every candidate is REJECT or REFERENCE ONLY, and no dependency is added. `pyproject.toml` and `uv.lock` are unchanged.

What CITERIFT writes instead:
- the guard as explicit functions, one per rule of MM 8, each naming its rule;
- a workflow checker for W-1 to W-8 over the fold;
- a closed adapter result type.

The cost is our own code, about the size of the Step 4 model's `legal`. That code is checked three ways:
- against the model by the differential harness;
- by every-transition and forbidden-transition tests;
- by mutation tests.

Limits stated plainly:
- Maintenance was judged by release dates only.
- The comparison is with this project's requirements R-1 to R-6, not a general ranking of the libraries.
