# Stage 04 Step 9: Build-vs-Adopt review of rule and decision engines

Status: Step 9 record (owner instruction of 2026-11-12, item 2; permanent Open-Source Leverage rule of 2026-11-10).
Subject: how to implement the decision table dt-1 (17 ordered rules, SPEC 7.3), the coherence function κ (SPEC 6.5)
and the D-5 contract checks.

## 1. Baseline

The baseline is a small explicit CITERIFT-owned ordered table with an independent reference model:

- `src/citerift/investigation/dt1.py`: `RULES`, a tuple of 17 `(rule id, guard)` pairs evaluated in order, first
  match wins; `kappa`, `violations` (D-5) and `decide`. Pure Python, no dependency, no I/O.
- `simulations/stage04/dt1_reference.py`: the frozen Step 4 model, written separately and importing nothing from
  `citerift`, with its exhaustive oracle (12,632,448 cases; 244,884 valid). The differential harness compares the two.

What a candidate would have to beat: rule order that is the code order and is visible in one place; exact guards over
typed projections; no runtime besides CPython 3.12/3.13; deterministic and offline; exhaustively checkable by the
existing oracle at about 5,000 cases per second per process.

## 2. Method

Facts were read on 2026-11-12 from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`: version, release dates,
license metadata, `requires_python`, classifiers, declared dependencies) and, where PyPI states no license, from the
project's LICENSE file at `raw.githubusercontent.com` (GoRules zen, cel-python, Open Policy Agent). The GitHub API was
not reachable for repositories outside this session's scope, so open-issue counts and security advisories were not
read; "maintenance" below is release history only. Nothing was installed. Transitive licenses were checked only from
the declared dependency list; no candidate reached the point where a full transitive audit (pip-licenses on an
install) was needed, because each fails an earlier criterion. Where a fact was not verified it says so.

## 3. Candidates

| # | Candidate (PyPI) | Repository | Version, last release | License (source) | Declared runtime deps | 3.12 / 3.13 |
|---|---|---|---|---|---|---|
| 1 | durable-rules | github.com/jruizgit/rules | 2.0.28, 2020-06-07 | MIT (PyPI) | none (C extension) | classifiers end at 3.7; not verified |
| 2 | business-rules | github.com/venmo/business-rules | 1.1.1, 2022-03-18 | MIT (PyPI) | six | classifiers end at 3.7; not verified |
| 3 | rule-engine | github.com/zeroSteiner/rule-engine | 5.2.0, 2026-10-28 | BSD-3-Clause (PyPI) | python-dateutil | yes (classifiers 3.10 to 3.13) |
| 4 | json-logic | github.com/nadirizr/json-logic-py | 0.6.3 (0.7.0a0 2017-03-31) | MIT (PyPI) | none | classifiers end at 3.4 |
| 5 | json-logic-qubit | github.com/qubitproducts/json-logic-py | 0.9.1, 2018-08-15 | MIT (PyPI) | none | classifiers end at 3.7 |
| 6 | panzi-json-logic | github.com/panzi/panzi-json-logic | 1.0.1, 2021-09-12 | MIT (classifier) | none | `>=3.6`; not verified |
| 7 | zen-engine (GoRules JDM decision tables) | github.com/gorules/zen | 2.1.7, 2026-11-10 | MIT (repository LICENSE; PyPI states none) | none declared; native Rust wheels (cp38 ABI) | wheels exist; not run |
| 8 | pyDatalog | pydatalog.readthedocs.io | 0.22.4, 2026-06-13 | LGPL (classifier) | none (extras: sqlalchemy, pymongo) | `>=3.8`; not verified |
| 9 | experta (CLIPS-like, Rete) | github.com/nilp0inter/experta | 1.9.4, 2019-11-16 | LGPLv3 (PyPI) | frozendict ==1.2, schema ==0.6.7 (exact pins) | classifiers end at 3.8 |
| 10 | clipspy (CLIPS binding) | github.com/noxdafox/clipspy | 1.0.6, 2025-10-26 | BSD (classifier) | cffi; bundles the CLIPS C engine | not verified |
| 11 | cel-python (Common Expression Language) | github.com/cloud-custodian/cel-python | 0.5.0, 2026-01-31 | Apache-2.0 (repository LICENSE) | google-re2, jmespath, lark, pendulum, pyyaml | `>=3.10`; 3.13 pin for google-re2 |
| 12 | casbin (policy engine) | github.com/casbin/pycasbin | 1.43.0, 2025-05-10 | Apache 2.0 (PyPI) | simpleeval | classifiers end at 3.12 |
| 13 | pyDMNrules (DMN decision tables) | github.com/russellmcdonell/pyDMNrules | 1.4.5, 2026-08-22 | GPLv3 (classifier) | pandas, openpyxl, pySFeel, datetime | not verified |
| 14 | Open Policy Agent / Rego (with opa-python-client 3.0.0, 2026-09-30, MIT) | github.com/open-policy-agent/opa | server binary | Apache-2.0 (repository LICENSE) | client: aiohttp, requests, aiofiles, urllib3 | client `>=3.10` |
| 15 | pyknow | (former CLIPS-like package) | not on PyPI (404) | not verified | n/a | n/a |

Built-in alternatives considered as well: Python's `match` statement and `functools.singledispatch` (standard
library, PSF license). Neither expresses an ordered list of overlapping guards better than a tuple of guards.

## 4. Assessment per candidate

All fields of the owner's list. "Order" means a guarantee that rules are tried in a fixed order and the first match
wins with nothing else firing.

| # | Maintenance | Determinism / offline | Order | Auditability / testability | Complexity saved | Complexity added | Fits exhaustive differential? | Decision |
|---|---|---|---|---|---|---|---|---|
| 1 durable-rules | no release since 2020 | offline; asynchronous forward chaining, results depend on assertion order | salience, not a first-match table | rules in a DSL; state in an engine | none: 17 guards are already one line each | C extension, engine state, event model | poor: per-case engine setup | REJECT (abandoned) |
| 2 business-rules | no release since 2022 | offline; deterministic | runs every matching rule unless stopped | JSON rules + Python variables | none | variable/action classes, `six` | possible but slower | REJECT (abandoned; not first-match) |
| 3 rule-engine | active | offline; deterministic expressions | none (evaluates one expression; order is the caller's loop) | readable expressions, but guards over typed lookups need custom resolvers | none: the caller still writes the ordered loop | an expression language and its type coercions | possible, slower | REFERENCE ONLY |
| 4-6 json-logic ports | stale (2017-2021) | offline; deterministic | none (single expression) | rules as JSON data | none | three competing unmaintained ports | possible | REJECT |
| 7 zen-engine | active | offline in-process; determinism not verified | decision tables with a first-hit policy | tables as JSON (JDM); native Rust code not auditable from Python | the table layout | native wheel, JDM format, a second representation of the projection forms | needs JSON marshalling per case | REFERENCE ONLY (first-hit table idea) |
| 8 pyDatalog | released 2026 | offline; logic evaluation | no rule order (Datalog is declarative) | logic program | none | a logic language | poor | REJECT (copyleft LGPL needs an owner decision; no order guarantee) |
| 9 experta | no release since 2019 | offline; Rete | salience | Python classes | none | exact old pins | poor | REJECT (abandoned; LGPLv3) |
| 10 clipspy | active | offline; CLIPS | salience and conflict strategies | CLIPS language in a C engine | none | a C engine and a second language | poor | REJECT |
| 11 cel-python | active, beta | offline; deterministic | none (expressions) | CEL expressions | none | five runtime deps incl. native google-re2 | possible | REJECT |
| 12 casbin | active | offline; deterministic | policy effect (allow/deny), not a table | access-control model | none | a model file and simpleeval | not designed for it | REJECT (wrong problem: authorization) |
| 13 pyDMNrules | active | offline; deterministic | DMN hit policies incl. FIRST | DMN in Excel/XML | the table layout | pandas, openpyxl; GPLv3 | possible, slow | REJECT (GPLv3 copyleft; heavy) |
| 14 OPA / Rego | active | needs an OPA server process (client speaks HTTP) | Rego rules are unordered; `else` chains give order | policy language | none | a separate Go service and network calls | no (network per case) | REJECT (not in process; network) |
| 15 pyknow | gone from PyPI | n/a | n/a | n/a | n/a | n/a | n/a | REJECT |

## 5. Decision

**No dependency is adopted.** dt-1 is 17 guards over typed values; each guard is one line, the order is the tuple's
order, and the frozen oracle checks the whole valid domain in 45 seconds. Every engine above either gives no
first-match guarantee (rule-engine, json-logic, Datalog, Rego, CEL), adds a second language and runtime (CLIPS,
experta, zen-engine, OPA), is unmaintained (durable-rules, business-rules, json-logic ports, experta), is copyleft and
would need an owner decision (pyDatalog, experta, pyDMNrules), or solves another problem (casbin). None reduces the
code that matters: the guards' exact projection forms, κ and the D-5 checks must be written for any engine, and the
engine would sit between them and the oracle.

Reference only: the DMN "FIRST" hit policy and GoRules' first-hit decision tables are the same model as `RULES`;
`rule-engine` shows how a typed expression language would look if the table ever became data. No code was copied.

Owner rules checked: no dependency, so no pin, attribution, DECISIONS entry or pip-audit change; no copyleft, hosted
service, API key or telemetry.
