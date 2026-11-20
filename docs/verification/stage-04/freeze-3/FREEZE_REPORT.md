# Stage 04 freeze-3 candidate report (final corrective cycle)

Owner decision D-083 (`cmsg_018VCB51nDHP6HXmLU4ea5yPYP4QxCiKQ1Hzx2XLj9zxep`, 2026-11-19T20:37:57Z) authorizes one final
corrective cycle: a general bibliographic-object consistency layer, a new decision-table version (dt-3), a new minor
engine version and a freeze-3 candidate, then STOP before P3, any seed, draw, frame, annotation or prospective run.
Gate 04-I is unchanged. P / dt-1 and P2 / dt-2 stay NOT PASSED and immutable. Stage 05 is not authorized.

Everything below is development evidence on design-exposed inputs. It is not an evaluation. Nothing was drawn,
annotated or rescored, and no label, adjudication, packet or score of either campaign was read to choose a rule. This
is a **candidate**: it is not a freeze until the owner accepts it.

## 1. Freeze records

| Record | Value |
|---|---|
| Earlier freezes | `b5bf8ed` (engine 0.2.0, dt-1): `SUPERSEDED_AFTER_FAILED_04_I`. `28ba646` (engine 0.3.0, dt-2): accepted as D-076, gate 04-I NOT PASSED under P2 (D-080); historical and immutable. Every file of `../freeze/` and `../freeze-2/` is unchanged |
| Baseline of the cycle | `66633148c8226ef5bbd20b32d15a3c8c0bb7abf7` (D-083 recorded; B-04-001 resolved; `src` identical to `28ba646`) |
| Last change to `src` and `schemas` | `bb7a0cf361ce0829f9671f4fc1b05fa2ffa57043` (review C fixes) |
| Code revision of the test runs | `208a8de2533acd7a31b4580f791bd548a645b4c7` (`src`, `schemas`, `pyproject.toml` and `uv.lock` equal those of `bb7a0cf`); CI run 390 (`44725151080`) |
| Evidence commit (parent of the freeze-content commit) | `1a6231ca02886cae6171b5dda4481a290a9a498c` |
| Freeze manifest | `FREEZE_MANIFEST.json`, format `citerift-stage04-freeze/3` |
| Manifest digest (SHA-256 of the canonical encoding) | `5fa2e0884c653418041504d023da9c997a38161e0868aece0d2a751ce9936ad4` |
| Exposure manifest v3 | `exposure/EXPOSURE_MANIFEST.json`, SHA-256 `f3556be865ed051f4a9144172f09965ec767737379e3cd87e251b69ac0eeedc9`, built at `bdc6e32`: **478 articles** (222 ar, 256 en; 9 without a page id); v2 had 378. The 100 P2 articles are added as `S04-P2-CAMPAIGN-100`; 4 + 4 drawn-not-acquired positions of the two campaigns are recorded separately |
| Frozen SHA (freeze-content commit), its tree, its CI run | named by the attestation commit that follows (two-record mechanism) |

The digest is reproduced by `uv run python docs/verification/stage-04/freeze-3/build_freeze_manifest.py` at the
evidence commit, which prints it. The manifest pins the 45 Stage 04 source files, the 16 Stage 04 schemas, the decision
semantics files (the bib-1 module and profile included), the dt-1, dt-2 and dt-3 oracle manifests, `pyproject.toml`,
`uv.lock`, the exposure manifest and 42 evidence files.

## 2. Root cause, architecture and correction

- **Root cause** (`../final-cycle/ROOT_CAUSE_AND_ARCHITECTURE.md` section 1). P2's false attachment, `en-27958530`
  unit `un-00004`, cites a commentary (author Robert Garry, title = the record's title plus "– Comments") with the
  DOI and PMID of the retracted paper (Hon, Ng, Leung). dt-2 decides from identifiers only: **no part of it compares
  the citation's own bibliographic description with the record its identifiers reach.** The defect is general:
  evaluation 1's `ar-10305362` cites another paper with a retracted record's DOI.
- **Architecture** (section 3). **No Stage 02 or Stage 03 maintenance.** Citation fields are parsed by NORMALIZE
  from each citation-template unit's committed source span with mwparserfromhell 0.7.2 (already pinned by Stage 03);
  record fields (authors, title, journal, dates) come through Stage 02's accepted `Index` interface, bound to each
  public event by `event_id` and `row_sha256`. No Stage 02/03 code, schema, policy, index or document changed.
- **Correction** (`../final-cycle/BIBLIOGRAPHIC_SPEC.md`, bib-1). Each event of the deciding lookup is compared with
  the cited description: surnames only, normalised titles with a fixed designation lexicon (comment, reply, erratum,
  retraction and the like, singular and plural). The object verdict is COMPATIBLE, INSUFFICIENT or
  MATERIAL_CONFLICT. **No threshold, no similarity score, no DOI, author, journal, publisher or word exception.**
- **dt-3** = dt-2 plus rule **D-13a**, between D-13 and D-14: a MATERIAL_CONFLICT on any compared event makes the
  candidate `UNRESOLVED_IDENTITY` with reason `BIBLIOGRAPHIC_OBJECT_CONFLICT` and the `BIB_` detail reasons. bib-1
  can only remove a positive: it never creates, restores or moves one (dt-3 oracle, section 4). INSUFFICIENT stays as
  under dt-2. The order contradiction → unresolved → operational failure → positive → notice/no-finding is unchanged.

## 3. Versions and identities

| Item | freeze-2 | freeze-3 candidate |
|---|---|---|
| Engine (`citerift.investigation.__version__`) | 0.3.0 | 0.4.0 |
| Decision table | dt-2 | dt-3 |
| Stage 04 schema set (`common.schema.json`) | 4.0.0 | 5.0.0 |
| `claim.schema.json` | 3.0.0 | 4.0.0 |
| `candidate-inputs` / `lookup-observation` | 1.0.0 / 2.0.0 | 2.0.0 / 3.0.0 |
| Detector | `citerift-dt1-detector/3 (dt-2)` | `citerift-dt1-detector/4 (dt-3)` |
| bib-1 profile (`bib-profile-1.json`) | none | SHA-256 `450f17a2ec492f9066825e0ec9de3f2f480398345d4593759bfb9ace45e9808f`, parser mwparserfromhell 0.7.2 (pinned in the engine) |
| Reference model / oracle | `dt2_reference.py`, `oracle-dt2/` | kept unchanged; new `dt3_reference.py`, `bib_reference.py`, `oracle-dt3/` (manifest `1c302c78…`) |
| Stage 02 index identity | `rw-2f116e9ffed718e6`, `artifact_digest adcf7b65…`, `semantic_digest 7b2a2344…` | unchanged |

An investigation made by an earlier engine is refused at its first record with `ENGINE_IDENTITY_DIFFERS` (corr-E-07).

## 4. Tests and fail-first evidence

- **New suites:** `test_final_bib.py` (195 collected; the 89-case adversarial corpus, normalisation, record binding,
  the A-04 shape test on a real Stage 02 index), `test_final_oracle.py` (21; dt-3 oracle: 50,529,792 cases, 387
  distinct decisions, 0 violations; with no conflict dt-3 equals dt-2 case for case, and a conflict changes only D-14
  to D-13a), `test_final_provenance.py` (21), `test_final_history.py` (9), `test_final_lows.py` (6).
- **Fail-first:** the corpus decided by the dt-2 engine (`6663314`): 89 of 89 `RETRACTED_WORK_CITED`. By the dt-3
  engine: the 48 MATERIAL_CONFLICT cases become D-13a `UNRESOLVED_IDENTITY`; the 32 COMPATIBLE and 9 INSUFFICIENT
  cases stay D-14 (`../final-cycle/fail-first/`). Review fixes failed first with `lows/corpus_probe.py`: review F,
  8 mismatches before (`7d5b936`), 0 after; review C, 5 before (`e3d7952`), 0 after.
- **Historical pre-registrations (owner decision D-084, card `cmsg_018VCB51nDHP6HXmLU4ea5yPMLNjt7WVEnsz4KbEmUGNxB`).**
  `test_step13_evaluation.py` and `test_p2_evaluation.py` verify the historical engines (`b5bf8ed`, `28ba646`) from git,
  D-074 style. P and P2 and their campaigns are unchanged.
- **Full suite on `208a8de`:** local Python 3.12.3: 3,681 passed, 0 failed, 0 skipped (22 min 29 s); local Python 3.13.18: 3,681
  passed, 0 failed, 0 skipped (21 min 18 s); both test reports 0 problems on a clean tree. (A first local pair at
  `d5cd4ba` is not counted for 3.13: its environment ran Python 3.12.3, which its test report records.)
- **CI run 390 (`44725151080`)** on the same commit: `verify (python 3.12)` 3,681 passed (16 min 48 s), `verify (python 3.13)` 3,681 passed
  (13 min 13 s), test report check 0 problems on both, `pip-audit --strict` no known vulnerabilities, `ci-gate`
  success. No required job reached 30 minutes (OD-S12-2).
- `ruff check` (all passed), `ruff format --check` (698 files), `mypy` (96 source files, no issues), schema
  validation, the Step 3 document checker (PASS, 0 failed; amended in `8409baa` to admit D-13a and the letter-suffixed
  risk R4-04a), `citerift-gov check` (0 errors, 0 warnings), `render-status --check` (up to date), `pip-audit --strict`
  (no known vulnerabilities).
- **Secret scan.** The project's secret gate (D-036 patterns, `../final-closure/secret_scan.py`) over the freeze
  surface (`docs/verification/stage-04`, `src`, `schemas`, `simulations`, `tests/stage04`, governance, `.github`,
  lock files): 2,274 files, 0 matches (`SECRET_SCAN_GATE.json`). Over the whole repository it matches 5 files, all
  Stage 03 files unchanged since Stage 03's acceptance that define, test or review those patterns. A second scan of
  fixed credential formats over every tracked file (`secret_scan.py`, `SECRET_SCAN.json`, 7,409 files) has 1 hit: the
  placeholder `https://user:pw@…` URL that `tests/stage03/test_wiki_fetch_capture.py` asserts is refused; not a
  secret.

## 5. Regression (development evidence only; `../final-cycle/REGRESSION.md`)

| | Development (232) | Evaluation 1 (80) | Evaluation 2 / P2 (100) |
|---|---|---|---|
| Work candidates | 4,614 | 4,920 | 5,190 |
| Changed claims (dt-2 → dt-3) | 1 | 2 | 4 |
| New positives / NOTICE_CITED / NOT_FOUND | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Units with a positive claim | 19 → 18 | 78 → 76 | 86 → 82 |

Every changed claim is D-14 `RETRACTED_WORK_CITED` → D-13a `UNRESOLVED_IDENTITY`. By an engineering reading of
citation and record (not a label, in-sample, not shown independent of earlier adjudications), 2 of the 7 block a
different publication object (Garry; `ar-10305362`) and 5 are abstentions on the retracted work itself, the recall
cost of the threshold-free rules (a record listing one of nine authors, a misspelled co-author, a Cyrillic final
letter, a citation that adds "Letter:" twice). dt-2 re-decided on the committed inputs equals the recorded dt-2 class
counts on all 412 revisions; lifecycles and VERIFY are unchanged; 0 network attempts.

- **Garry** (`en-27958530 un-00004`): dt-2 D-14 → dt-3 D-13a with `BIB_AUTHORS_DISJOINT`, `BIB_TITLE_RELATED_OBJECT`.
  No rule names the DOI, the author, the journal or "Comments".
- **JASIST** (`en-39868218 un-00011`): D-10 `UNRESOLVED_IDENTITY` (`IDENTIFIER_ROLE_COLLISION`) under dt-2 and dt-3;
  the false attachment of evaluation 1 is not restored.
- **Role-collision recall study** (`../final-cycle/ROLE_COLLISION_STUDY.md`): 18 role-collision candidates on the three
  sets (1 / 4 / 13), all same-record collisions, none changed by dt-3. In a same-record collision the events describe
  the retracted work under both roles, so bib-1 cannot tell work from notice. **D-072 stays strict**: 1,472 of 31,506
  dt-1 positive DOI+PMID pairs stay `UNRESOLVED_IDENTITY`. The censuses rerun on dt-3 equal dt-2 by construction.

## 6. Reviews and findings (`../final-cycle/LOW_DISPOSITION.md`)

Seven independent reviews: A (semantics), B (identifiers, roles, oracle), D (provenance), E (security and bounds),
F (re-verification of A, B, D, E fixes), C (regression, recall, leakage, F fixes), G (re-verification of C fixes).

| Review | CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|---|
| A | 0 | 2 | 1 | 6 | 3 |
| B | 0 | 0 | 2 | 4 | 4 |
| D | 0 | 1 | 4 | 6 | 5 |
| E | 0 | 0 | 4 | 5 | 4 |
| F | 0 | 1 | 1 | 3 | 0 |
| C | 0 | 0 | 2 | 8 | 2 |
| G | 0 | 0 | 0 | 5 | 2 |

Every finding is fixed with evidence, an accepted residual with its reason, or awaiting an owner decision. The six LOW
findings open at the start of the cycle are dispositioned (corr-A-04, D-05, E-05, E-07, N-01 fixed; C-07 accepted
residual, measured). The three residuals of D-083 item 7 are reaffirmed with no new evidence of a defect. Two items
need the owner (section 9): the **A-02** residual (HIGH; the fix is committed, the stated residual false
compatibility needs acceptance, with G-04), and the **E-02 / F-02** size bound (16,384 code points, 64 values; above
it a unit decides as under dt-2). No other CRITICAL, HIGH or MEDIUM finding is open.

## 7. Vertical slice, D-062 and performance

- **Vertical slice** (`vertical-slice/`, run at `18acf6f`, engine of `bb7a0cf`; 149 calls in `unshare -rn`, 0 network
  attempts): `failed_checks` empty; VS-1 to VS-10, checkpoint and I-2 included.
- **D-062 two builds** (`d062/two_build_equivalence.json`, at `f83d20b`): equal canonical identity
  (`artifact_digest adcf7b65…`, `semantic_digest 7b2a2344…`, 147,152 export lines); 0 failed checks.
- **D-062 tamper differential** (`d062/tamper_differential.json`): 21 cases, 0 discrepancies, none rejected by the
  profile alone; operational tests 5 passed.
- **Performance** (D-061 target ≤ 5 s p95): **NOT_MET**, as accepted in D-066; D-064 is not weakened.

| Case | n | Run median (s) | Run p95 (s) | freeze-2 run p95 (s) | Replay p95 (s) |
|---|---|---|---|---|---|
| VS-1 | 5 | 32.611 | 33.756 | 30.548 | 28.479 |
| VS-2 | 5 | 29.32 | 31.708 | 26.547 | 28.494 |
| VS-3a | 5 | 26.844 | 27.909 | 25.96 | 26.854 |
| VS-3b | 5 | 29.988 | 32.984 | 27.865 | 27.954 |
| VS-4 | 5 | 28.358 | 28.564 | 25.318 | 28.571 |
| VS-5 | 5 | 29.618 | 31.539 | 26.958 | 28.141 |
| VS-6a | 5 | 26.145 | 27.814 | 25.151 | 26.936 |
| VS-6b | 5 | 26.618 | 29.47 | 25.447 | 26.82 |

  The vertical-slice run p95 is 1.9 to 5.2 s above freeze-2's. The single-process breakdown (`performance/`) does not
  show that rise: process wall 32.94 s median (freeze-2 33.03 s), of which `verify_index_identity` 25.51 s (26.05 s).
  bib-1's own parse time is 0.0035 s median, 0.038 s p95 and 0.172 s maximum per development page
  (`../final-cycle/lows/description_sizes.json`). The cause of the vertical-slice difference is **not isolated**: both
  runs used the same 4-vCPU container type, and the load on the container during either run was not recorded. It is
  reported as measured, not explained away.
- **Storage** (`../final-cycle/PERFORMANCE_AND_BOUNDS.md`): maximal journal 434,316,192 B at the Stage 03 caps, 1.2x
  headroom (the D-055 "at least 20x" no longer holds); above 32,030 events per deciding lookup a run is refused.

## 8. Limitations

The manifest's `limitations` list is authoritative. In short: the bib-1 recall costs (5 of 7 changed claims in the
regression are on the retracted work itself); the A-02 / G-04 residual false compatibility; the size bound of E-02;
the D-071 / D-072 role-collision recall cost (1,472 pairs) and D-073 abstentions; the D-075 rule; performance NOT_MET;
1.2x storage headroom; the C-07 quadratic scan (2.6 s at 3,000 synthetic events); all regression sets are
design-exposed, so nothing here is a recall or precision estimate.

## 9. Owner decisions and what remains

Recorded during the cycle: D-083 (authorization) and D-084 (the P and P2 tests verify their historical engines from
git). **Still required from the owner:**

1. Acceptance (or not) of this freeze-3 candidate.
2. **E-02 / F-02**: the bib-1 size bound (a citation source above 16,384 code points, a family above 64 values or a
   description above 4,096 code points has no description, so the unit decides as under dt-2; development maximum
   5,722 code points and 56 values).
3. **A-02** (with **G-04**): acceptance of the stated residual false compatibility (BIBLIOGRAPHIC_SPEC section 9).

Not started and not authorized: P3, any seed, draw, frame, annotation or prospective run; Step 15; Stage 05.
