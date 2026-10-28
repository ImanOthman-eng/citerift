# Stage 02 Test Results

Results for the Retraction Data Engine at the code revision named in
HANDOFF.md ("Verified Git commit"). Section 1 is the summary; the later
sections give the evidence. "CI" means the GitHub Actions workflow on the
pull request; "real-data run" means the full-source commands run in the cloud
container on the same code revision with the ignored local data
(`data/raw/rw/retraction_watch.csv`, receipt-checked).

## 1. Gate summary

| Gate | Result | Evidence |
|---|---|---|
| 02-A tests (directive 14 items 1 to 17) | pass | section 2; `tests/stage02/` |
| 02-B pinned real build | pass | section 3; `evidence/benchmark.json` |
| 02-C oracle and real cases | pass, with the reviewer limit of section 4 | `evidence/oracle-comparison.json`; `tests/stage02/fixtures/real_cases.json` |
| 02-D schemas | pass | `test_rde_schemas.py`; section 2 |
| 02-E Evidence Tension | pass | section 5; `evidence/tension-demonstrations.json` |
| 02-F bounded corroboration | pass | section 6; `evidence/crossref/` |
| 02-G Evidence Ambiguity Investigator | **not met: the model experiment was not executed** | section 7; blocker B-1 in HANDOFF.md |
| 02-H budgets | pass | section 8; `evidence/benchmark.json` |
| 02-I CI, reviews, documents | **not met: CI is red on two Stage 00 tests** | section 9; blocker B-2 in HANDOFF.md |

Stage 02 is therefore not verified. Every other gate is met with the
evidence below.

## 2. Test suites

`uv run pytest` at the cited revision (local, Python 3.12.3):
**2 failed, 1034 passed** (1,036 tests, 198.8 s); Python 3.13.17 gives the same result (section 9). The two failures are the Stage 00 tests of section 9.

Stage 02 tests, `tests/stage02/` (531 collected; a test can carry more than
one suite marker):

| Suite | Tests |
|---|---|
| unit | 206 |
| integration | 114 |
| negative | 250 |
| regression | 36 |
| reproducibility | 5 |
| security | 58 |
| contracts | 7 |
| simulation | 59 |

Coverage of directive section 14:

| Item | Tests |
|---|---|
| 1 exact retraction and each other type | `test_rde_policy_cases.py` (P01 to P04), real cases R01 to R09 |
| 2 concern then retraction; correction after retraction | P-cases, `test_rde_policy_regressions.py`, `test_rde_policy_properties.py` (INV-P2), real R10 to R13, R46, R47 |
| 3 reinstatement with and without supersession | P-cases, `test_rde_sole_reinstatement_is_unlinked`, INV-P3, real R07 to R09 |
| 4 equal original/notice DOI; shared notice; notice-only | P-cases, `test_rde_lookup.py`, real R16 to R23 |
| 5 missing IDs, malformed ID, contradictory bridge, incompatible dual query | `test_rde_lookup.py`, real R24 to R35, R41 to R43 |
| 6 identical duplicate, reused ID, duplicate accounting | `test_rde_import.py`, real R44, R45 |
| 7 RW plus Crossref-RW; publisher dependence unknown; resolving notice | `test_rde_corroboration.py` |
| 8 day-1, volume/season, historical, impossible dates, date kinds | `test_rde_dates.py`, real R36, R37, R40 |
| 9 unknown/overlapping bounds and conflicts | `test_rde_dates.py`, `test_rde_policy_regressions.py` |
| 10 healthy absence, relevant quarantine, corrupt index | `test_rde_lookup.py`, `test_rde_review_findings.py` (S1, S2), real R43, R48 to R50 |
| 11 hash, partial file, headers, quoting, encoding, newlines, blanks | `test_rde_import.py` |
| 12 failure at publication boundaries | `test_rde_import.py`, `test_rde_review_findings.py` (A1, A2) |
| 13 disappearance without false reinstatement | `test_rde_export_diff.py` |
| 14 Unicode, ASCII folding, lookalikes, bidi, `%`, encoded separators, `+` | `test_rde_identifiers.py`, S6 |
| 15 SQL-looking IDs, malicious text, exhaustion, cycles, duplicate keys | `test_rde_schemas.py`, `test_rde_import.py`, S4, S7, S9 |
| 16 timeout, 429, 403, 5xx, invalid JSON, mismatched 200 | `test_rde_corroboration.py`, S3, S5, S8 |
| 17 AI abstention and forbidden promotion | `test_rde_advisory.py` |

Metamorphic properties (directive 14): idempotence (`test_rde_identifiers.py`),
no event loss when adding events and row-permutation invariance
(`test_rde_export_diff.py`), redistributed duplication and evidence removal
(`test_rde_tension_properties.py`), page size (`test_rde_lookup.py`), same
inputs give the same semantic content (`test_rde_export_diff.py`, and the
real double build of section 3).

## 3. Real build and reproducibility (real-data run)

Five full builds of the pinned CSV at the cited code revision, each in a fresh
process (`scripts/benchmark.py`, `evidence/benchmark.json`):

| Measure | Result |
|---|---|
| Records, accepted, quarantined | 73,356, 73,356, 0 |
| Physical lines (header, record lines, blank) | 173,491 (1, 173,490, 0) |
| Events by type | 67,916 retracted, 3,733 expression of concern, 1,544 correction, 163 reinstated |
| Records in duplicate groups (all kept) | 439 |
| Artifact digest, every build | `1ee679b5e5c2e89f06139f43ffd27818b9259dc15693c743ef7bd2ea45e809dc` |
| Semantic digest, every build | `7b2a2344a7f9546d2c684dfef84aa01db9e010fd9c9bf7f9343c93b5b88a5f88` |
| Export lines | 147,152 |
| Double build | one digest set over five builds; query outputs equal |

The counts equal the accepted Stage 01 profile. The semantic digest is the
same as at `e4de42b`; the artifact digest changed with the policy version
(SPECIFICATION.md 16 item 23), which is what it is meant to record.

`verify --source` on the first build re-reads the CSV and compares it with the
index: ok, 0 problems, 73,356 events schema-checked, 73,356 source records
checked (`evidence/verify-rw.json`). The index built with the pinned Crossref
replay (48 Crossref assertions) is also clean: artifact digest
`ea4c1678e1f4fd0a65e56e9202f129f53dd2e3fa2607a9c5002e16782430147d`, semantic
digest `d3daab8ff9697c0a0072a15a4f640728f3fc10dd09acba0d54d8f8987f687e5a`,
147,229 export lines (`evidence/verify-cr.json`).

## 4. Oracle and real cases (real-data run, gate 02-C)

The independent streaming oracle agrees with the index on every key: 112,481
DOI and 63,010 PMID keys of the snapshot in both roles and 1,600 absent
synthetic keys, 350,982 key-role comparisons, **0 mismatches**; record and
line accounting are equal (SIMULATION_REPORT.md 2).

Real cases: 50 cases in 27 classes from 69 attributed records
(`tests/stage02/fixtures/real_cases.json`, `rw_real_subset.csv`), covering all
four event types. Expected outcomes come from the prebuild simulator; the
engine agrees on all 50, both on the full index and on an index rebuilt from
the fixture alone by the test suite (`test_rde_real_cases.py`). Classes with no instance in
the snapshot are listed in the fixture (`classes_absent_in_snapshot`).

Reviewer and method, stated accurately: cases were selected by a deterministic
script (`scripts/real_cases.py`) by class, not by outcome. After the last
regeneration the agent read all 50 cases (rows, query and expected outcome)
against the specification as amended and found no disagreement. The agent is
an AI model; there was **no human review or adjudication**. Gate 02-C says
"reviewed cases"; it is met only in this sense.

## 5. Evidence Tension (gate 02-E)

Frozen 16-case set (`cases/tension_cases.json`, engine and simulator): every
case's changed fields match exactly; every expected diagnostic class is
detected on the 12 non-control cases; the 4 controls show no change. The
event-log baseline has no diagnostics (recall 0 by construction) and gives a
wrong or misleading answer on 10 of the 16 cases (recorded per case as
`baseline_error`).

Real pinned demonstrations (real-data run on the Crossref-replay index,
`scripts/tension_demos.py`, `evidence/tension-demonstrations.json`; every report
validates against its schema):

| Demo | Query | Classes shown | Base settled | What the baseline gets wrong |
|---|---|---|---|---|
| D1 | DOI `10.1016/s0140-6736(97)11096-0` | redistributed support | yes | counts 4 confirming sources from 1 origin |
| D2 | DOI `10.2217/nnm.14.183` | redistributed support, origin dependence | yes | counts 8 sources from 2 origins; cannot show the date and notice rest on one origin |
| D3 | DOI `10.1007/s13277-014-2995-5` | redistributed support | yes | counts 6 sources from 2 origins; states 2015-07-24 as given while the dates conflict |
| D4 | PMID `26700683` | uncertain identity or notice | yes | cannot show the answer rests on a one-hop bridge |
| D6 | DOI `10.1001/archneur.1985.04060020080021` | unsupported temporal precision | yes | states 1989-10-01, a day-1 value, as a date |
| D5 | PMID `11430323` | none (control label) | **no** (`ambiguous_identity`) | answers "retracted" for a PMID that names several works |
| D7 | DOI `10.1159/000443123` | none (control label) | **no** (`REINSTATEMENT_UNLINKED`) | answers "retracted" and a date |
| D8 | DOI with `%3c` in the source form | none (true control) | yes | nothing |

Five demonstrations (D1, D2, D3, D4, D6) show the three required classes and
origin dependence; gate 02-E asks for four covering the three. D5 and D7 carry
`base_unresolved`: Evidence Tension reports no change because the base answer
was never settled, and that is not robustness (Sci-7). D5 was chosen as an
identity case; the identity problem is caught by lookup itself, not by a
tension view, so it is not counted toward the gate.

## 6. Bounded corroboration (gate 02-F)

Every failure mode of SPECIFICATION.md 9 is tested with transport doubles and
none becomes a negative finding (`test_rde_corroboration.py`, plus S3, S5,
S7, S8 on a loopback server). The real bounded run on 2026-10-27 requested
29 works with 30 requests (limits 40 and 80): 27 ok, 2 recorded as 404
failures, not as absence (`evidence/crossref/manifest.json`). Building with the
pinned replay reproduces the same assertions and keeps the original retrieval
time (`test_rde_replay_reproduces_assertions_and_keeps_retrieval_time`); the
Crossref index is verified clean (section 3).

## 7. Evidence Ambiguity Investigator (gate 02-G): blocked

Delivered and tested:

- The advisory boundary: a bounded bundle of at most five candidates, a
  response schema, abstention on schema-invalid output, injection, timeout,
  unsupported candidate and budget exhaustion; no module of the engine
  imports the advisory code or accepts its output, so a suggestion cannot
  become a fact (`test_rde_advisory.py`).
- The deterministic baseline (inverted title-token index, IDF cosine, author
  and year features, abstention thresholds), frozen on the tuning split.
- The protocol, frozen before any prediction at `fe187b1`
  (`ai/protocol.json`): seed 20261027, 40 tuning and 120 held-out groups
  (60 positive, 60 negative), thresholds tau_s 0.85 and tau_m 0.10, gate as
  in the directive.
- The baseline on the held-out split (`ai/baseline-heldout.json`): 110/120
  correct (0.917, Wilson 0.853 to 0.954), coverage 0.433, selection precision
  0.981, 1 false selection on negatives, candidate recall@5 1.0.

Not done: no model prediction was made, so there is no model result, positive
or negative. Two facts are independent of any model and are reported, not
used to lower the gate:

1. The largest possible gain is 100 × (1 − 110/120) = 8.3 points; the gate
   asks for 10.
2. Coverage is selections / 120. With 60 positives and false selections on
   negatives not allowed above the baseline's 1, coverage is at most
   61/120 = 0.508; the gate asks for 0.60.

So no model can pass the frozen gate on this frozen split. The route for
running the experiment on the session's agent facility, and whether to run
it at all, is the owner's decision (D-023; HANDOFF.md blocker B-1). The
pilot that established the route used a synthetic bundle outside the splits
(`ai/route-pilot-2026-10-27.json`).

Known label limits (science review 9, kept because the protocol is frozen):
some positives are supplement-DOI collisions, valid for the controlled
"recover the masked DOI" task but not for "same work"; the disagreement
stratum is assigned from the target's lowest-ordinal record while scoring
uses the best-matching record. The snapshot has one Arabic-script record, so
there is no Arabic stratum and no Arabic claim.

## 8. Resource budgets (real-data run, gate 02-H)

Real-data run at the cited code revision, protocol declared before measurement
in `evidence/benchmark.json` (SPECIFICATION.md 13 query mix):

| Budget | Limit | Measured | Met |
|---|---|---|---|
| Build wall time | 120 s | median 71.7 s, max 73.7 s (5 builds) | yes |
| Build peak RSS | 512 MiB | 405.3 MiB | yes |
| Index size | 512 MiB | 265.9 MiB | yes |
| Warm lookup p95 (2,000 queries) | 20 ms | 0.239 ms (max 41.6 ms) | yes |
| Fresh-process lookup p95 (200) | 1,000 ms | 141.3 ms | yes |
| Evidence Tension p95 (200) | 50 ms | 0.398 ms | yes |
| Ambiguity candidates p95 (200) | 100 ms | 16.4 ms | yes |
| Double build | equal | equal | yes |

An earlier run at `aa7c23c` failed the memory budget (740 MiB) because every
event was held in memory for parallel validation; it is kept as
`evidence/benchmark-at-aa7c23c-failed-rss.json`. Validation was made serial
and streaming at `66e39ed` and the budget was not changed. The run at `66e39ed`
(`evidence/benchmark-at-66e39ed.json`) met every budget before the version
increment; the run above is the one at the cited revision. Host: 4 vCPU,
15 GiB, Python 3.12.3, SQLite 3.45.1.

## 9. CI and the Stage 00 tests (gate 02-I)

**CI evidence.** GitHub Actions, workflow `CI`, run 83 on the cited code
revision `a24dd46` (https://github.com/ImanOthman-eng/citerift/actions/runs/40621662275):
both `verify` jobs (Python 3.12 and 3.13) stop at the step "Governance state
and memory consistency" with

```
ERROR VERIFICATION_STALE: [stage 00] owned content differs from the verified revision
(tests/stage00/test_corrections.py; last change seen in history: ed8e44200567), with no
recorded amendment covering the change
```

and `ci-gate` fails. The later steps (lockfile, ruff, mypy, schema check,
pytest, report check, audit) do not run in CI. Every run on this branch since
`ed8e442` stops at the same step, so **no Stage 02 test has run in CI**; the
test results in this document come from local runs in the cloud container.
The pull request's own CI run is reported in the pull request.

**Local evidence.** At the cited revision, Python 3.12.3: `uv run pytest` 2
failed, 1034 passed; `ruff check`, `ruff format --check` and `mypy` clean;
`citerift-gov check` gives only the error above. Python 3.13.17 (a scratch
environment from the same lockfile): 2 failed (the same two), 1034 passed
(207.7 s).

The two failing Stage 00 tests:

- `test_real_repository_passes_governance_check` fails with the error above.
  The change at `ed8e442` is the owner-authorized V-03 test-setup fix
  (`cmsg_018VCB51nDHP6HXmLU4ea5yPJN5cHhUJ8f8AM5hyKq3tCu`): the sandbox sets the
  empty Stage 02 definition itself, keeps the rejection assertion and the
  DEFINITION_WEAK check, and leaves the real definition and production
  governance unchanged. It fixes the V-03 failure of run 77 in local runs;
  CI has not reached that test since. The authorization
  says the fix is to be "recorded through the required existing governance
  amendment process"; that process cannot complete here (HANDOFF.md B-2).
- `test_application_layers_not_created_prematurely` allows only `contracts/`
  and `governance/` under `src/citerift/`; Stage 02 adds `retraction/`, which
  the directive requires. Changing the test is a Stage 00 change the owner has
  not authorized.

Neither test was skipped, deleted or weakened, and no governance code was
changed.

## 10. Review passes and dispositions

Three review passes were run on `3a6f1eb`, each a separate session of the same
model with a non-overlapping scope and read-only access: architecture and
data integrity (2 high, 4 medium, 2 low), adversarial QA and security (1 high,
5 medium, 4 low) and scientific and statistical semantics (2 high, 6 medium,
1 low group). They are not human or organizational review; each reported its
own limits (it reviewed files that were changing, did not run the full suite,
and did not cover the other scopes). Every regression test below failed, or
could not run, on the code of `3a6f1eb`, except the controls named in
`evidence/fail-first/review-findings-at-3a6f1eb.txt` (46 failed, 9 controls
passed) and `policy-properties-at-3a6f1eb.txt`.

| Finding | Severity | Requirement | Evidence (reviewer) | Fix or disposition | Regression check |
|---|---|---|---|---|---|
| A1 | high | SPECIFICATION.md 10.1, validate before publishing | a 201-character date built an index its own `verify` rejected | fixed: events and manifest validated in the build (`ARTIFACT_INVALID`); the 200-character limit removed (16 items 15, 21); validation streamed after the benchmark (section 8) | `test_rde_a1_*` |
| A2 | high | "rebuilding never deletes earlier evidence" | a plain rebuild replaced a corroborated build; a crash between renames left a mismatched pair | fixed: a build replaces only an equal build (`ARTIFACT_EXISTS`); `verify` compares the manifest. Names still depend only on the source hash, so another build needs another directory | `test_rde_a2_*` |
| A3 | medium | 10.4 digests cover what lookups read | tampered `ident`, `notice`, `title_token` passed `verify`; an extra Crossref work changed no digest | fixed: `verify` recomputes derived tables; `cr_attempt` exported | `test_rde_a3_*` |
| A4 | medium | 9, replay integrity | NaN, wrong types and foreign URLs accepted or crashed | fixed with S4 | `test_rde_s4_*` |
| A5 | medium | 10.5 semantic diff | reordered columns reported as three changed records | fixed: semantic-line and header comparison | `test_rde_a5_*` |
| A6 | low-medium | 7.2, acquisition time is not content | retrieval time changed the semantic digest | fixed | `test_rde_a6_*` |
| A7 | low | page cap bounds a response | one notice-only lookup listed 659 notice hits (159 KB) | fixed: 100 listed plus a count | `test_rde_a7_*` |
| A8 | low | robustness | source read three times; schema directory resolved from the repository layout; temp files after a kill; §16 item 1 text | §16 text fixed. The others are limitations: the reads are of a local ignored file and `verify --source` re-hashes it; an installed wheel needs the schema-root environment override; a killed build leaves a temp file and never a published one | none |
| S1 | high | no error becomes a negative finding | `%2F`, zero-width and broken-escape forms gave "not found" | fixed (16 item 17) | `test_rde_s1_*` (3) |
| S2 | medium | readers open read-only, immutable | `#`, `?`, `%` in the path created files or dropped `mode=ro` | fixed (item 16) | `test_rde_s2_*` (4) |
| S3 | medium | GET to approved `/works` only | redirects followed off host | fixed: redirects refused | `test_rde_s3_*` |
| S4 | medium | replay manifest schema | forged URL, bad time, `404` with `ok` accepted | fixed (item 22) | `test_rde_s4_*` (8) |
| S5 | medium | honour Retry-After | HTTP-date and 503 ignored | fixed; unreadable value recorded as failure | `test_rde_s5_*` (3) |
| S6 | medium-low | reject or flag controls | `str.strip()` removed controls, giving an exact match | fixed (item 18) | `test_rde_s6_*` (6) |
| S7 | low | payload cap | symlink to `/dev/zero` ran out of memory | fixed | `test_rde_s7_*` |
| S8 | low | run deadline | slow drip read for 11.7 s against 3 s | fixed: total deadline | `test_rde_s8_*` |
| S9 | low | invalid input is a typed error | deep cursor raised `RecursionError` | fixed: `CURSOR_INVALID` | `test_rde_s9_*` |
| S10 | low | identifier hygiene | U+3164 and U+2800 kept in keys; short PMIDs match many relevance rows | accepted as specified: both characters are allowed by SPECIFICATION.md 6.1; extra relevance hits make an answer uncertain, never a match | none |
| Sci-1 | high | directive 9, INV-P2 | ordered concern then retraction on one notice was `conflicting`; 25 real groups | fixed (item 12); 34 real keys now `retracted`, 4 `uncertain` | regressions, INV-P2 property, R46, R47 |
| Sci-2 | high | directive 9, unlinked reinstatement | a reinstatement alone was `verified_fact` | fixed (item 11; P04 amended); 275 real keys now `uncertain` | regression, INV-P3, R08, R09 |
| Sci-3 | medium | directive 8, co-occurrence is not proof of identity | a PMID-bridged event alone gives `verified_fact`, `retracted` with identity `bridged` | **kept as frozen** (cases P33, T05, T06 expect it; 0 real instances found by the reviewer); identity `bridged` and `exclude_ambiguous_links` expose it; proposed to the owner as R-026 | P33, T05, T06 |
| Sci-4 | medium | directive 11, unknown dependence | publisher dependence stored as none | fixed: `dependence` field (item 14) | `test_rde_replay_lineage_and_dependence` |
| Sci-5 | medium | INV-P1 | unknown-origin support alone verified | fixed (item 14) | regression, INV-P8 |
| Sci-6 | medium | gate 02-G coverage | coverage ≤ 0.508 for any model | recorded, gate not lowered; owner decision (section 7) | arithmetic in section 7 |
| Sci-7 | medium | 11.2 controls | unresolved bases labelled `control` | partly fixed: reports state `base_unresolved`; the label is kept because frozen cases use it, and the demonstrations report the flag | `test_rde_c7_*` |
| Sci-8 | medium | disclosure | four in-place spec edits and a simulator change not listed | fixed: SPECIFICATION.md 16 lists them | review of §16 |
| Sci-9 | low | various | proposition without anchor; substring relevance noise; baseline counting; two misnamed real-case classes; AI label and stratum notes; day-1 nulls the year | proposition fixed (item 13); real-case classes fixed (R40 renamed, R43 now a true relevance case); the others documented here and in section 7 | regression, real cases |

## 11. Evidence locations

| Evidence | Path |
|---|---|
| Environment and permissions | `evidence/environment.json` |
| Simulator run | `evidence/simulator.json` |
| Oracle comparison | `evidence/oracle-comparison.json` |
| Benchmarks, double build | `evidence/benchmark.json`; failed run kept as `evidence/benchmark-at-aa7c23c-failed-rss.json` |
| Policy impact | `evidence/policy-impact-rw.json`, `evidence/policy-impact-cr.json` |
| Tension demonstrations | `evidence/tension-demonstrations.json` |
| Crossref replay bundle | `evidence/crossref/` |
| Fail-first runs | `evidence/fail-first/` |
| AI protocol, baseline, route pilot | `ai/` |
| Local full-suite runs, Python 3.12 and 3.13 | `evidence/local-test-runs.txt` |
| Complete test report | `test-report.json` |
