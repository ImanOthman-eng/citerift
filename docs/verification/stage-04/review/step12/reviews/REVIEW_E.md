# Stage 04 pre-freeze review: Reviewer E (evaluation, leakage and statistical readiness)

Repository `/home/user/citerift`, HEAD `65c30bd`. Read-only review. `git status --porcelain` was empty after all commands.

## 1. Scope and method

**Scope.** Five questions:
- Is the set of exposed articles kept apart from any future holdout?
- Has any evaluation leakage happened?
- Is the freeze ordered before the draw?
- Is any development measurement labelled as evaluation?
- Are the denominators, gates and failure criteria worded the same way in every document?

I did not design statistics, and I did not open or count any Stage 01 census or English dump-scan frame.

**What I read.**
- The planning package, `docs/verification/stage-04/planning/STAGE04_MASTER_EXECUTION_PACKAGE.md`: sections 2.3, 8.4, 8.7, 11, 12, 13, 14, 15 and 17.
- `SPECIFICATION.md` sections 1, 7.2, 14 and 17; `RISK_ANALYSIS.md` R4-01, R4-05 and R4-18 to R4-32; `MATHEMATICAL_MODEL.md` section 11.
- The Stage 04 gates in `governance/stage_registry.json` (lines 21212–21260).
- `DECISIONS.md` entries D-040, D-041 and D-058 to D-063.
- Step 9 closure, `dev_measurements.py`, `dev_measurements.json`, `differential*.json`; Step 11 closure; `run_vertical_slice.py`; the `tests/stage04` support files.
- Stage 03 `EXPOSURE_INVENTORY.md`, the D-036 `exposure_set.py` and `EXPOSURE_SET.json`, and the `capture_states*.json` files.
- Stage 01 `data/README.md`, `purposive_discovery.json`, `sample_S_discovery.json` and `EVIDENCE_MANIFEST.json`. These are exposure sources only, not the frame.

**Scripts I ran.** All small scripts used `.venv/bin/python -I`, with outputs in `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/review-E/`:
- `enum.py` → `bundles.json`: identity of every `capture.json`.
- `ids.py`: scans Stage 04 paths for revision-like integers.
- `states.py`: finds Stage 03 capture attempts that have no retained bundle.
- The Stage 03 exposure rule `docs/verification/stage-03/evaluation/confirmation-d036/scripts/exposure_set.py`, written to `.../review-E/s03_exposure_now.json`.

**Read-only git commands.** `git log`, `git ls-tree` and `git status`.

Labels used below: **[fact]** = file:line or command output; **[inference]** = derived.

## 2. Findings

| Id | Title | Severity | Evidence | Proposed classification | Suggested fix |
|---|---|---|---|---|---|
| E-01 | No committed canonical list of the exposure set. The "232 revisions" are defined by a run-time glob, and the planning count of 255 cannot be reproduced | MEDIUM | Plan:155 says "255 / 232". `dev_measurements.py:48` uses `REPO.glob("**/capture.json")`. Step 9 A-8 (`STEP9_CLOSURE.md` §13) blames "count drift from later retained bundles". But `git ls-tree` shows 257 `capture.json` at `b93314d` (the last commit to touch any `capture.json`), at plan commit `a152885` and at HEAD. No planning probe script is retained in `planning/` | 4 | Commit a canonical exposure manifest built by rule (section 3) in the Step 13 pre-registration, after the freeze. Correct A-8: 257 existed before planning, so the 255 figure has no recorded derivation |
| E-02 | "Stage 03 exposure set" (plan 12.3 Frame) is undefined. The last committed Stage 03 exposure set is out of date | MEDIUM | `confirmation-d036/campaign/EXPOSURE_SET.json` was computed before the D-036 draw and misses 47 retained bundle dirs = 44 articles (d036 holdout 42 dirs, reserve1 5 dirs) [fact, script]. Re-running the same rule at HEAD gives 7,038 page ids and 7,075 titles across 2,214 documents (`documents_sha256` `8fdee4b3…cef29`), covering all 257 bundles. The rule is wiki-agnostic and includes "listed only" ids | 8 | Recompute the Stage 03 tier at the manifest commit; never reuse the committed d036 file. Keep a wiki-qualified primary tier, and decide in pre-registration whether the wiki-agnostic "listed" tier is excluded too (Stage 03 excluded it) |
| E-03 | Some exposed Stage 03 articles have no retained bundle, and 10 have no page id | LOW | `confirmation-superseded/capture/capture_states.json` names ar 4823675 and ar 6468321 with no bundle [fact, script; also `EXPOSURE_INVENTORY.md` "capture failed, no bytes retained"]. `calibration/dev_selection.json` and `dev_selection_supplement.json` hold 15 entries; 10 have only `wiki` and `title`, no page id or revision [fact, script; `EXPOSURE_INVENTORY.md` "known only by title (including two redirect titles)"] | 5 | Manifest records keyed by (wiki, normalized title) for these entries; exclude by title and redirect title (the Stage 03 practice). Do not resolve page ids through the network before the draw unless pre-registered |
| E-04 | The documents name different exclusion sets, at different levels (revision vs article) | LOW | Registry 04-I (line 21251): "Stage 03 revisions examined during planning". D-040 / plan D-5 (plan:180, 511): "the 16 planning-exposed articles". Plan 12.3 Frame (plan:524): "Stage 03 exposure set, the 232 probe revisions, Stage 01 purposive pages". RA R4-19 (`RISK_ANALYSIS.md`:359–363): 232, the 16, Stage 01 purposive, Obokata, matched "by wiki and page id". Plan:177–178: "revisions outside them" | 4 | Pre-registration states one rule: article level (wiki, page_id), over the union of every source in section 3. The broadest wording, plan 12.3 + R4-19, already permits this. No gate change is needed |
| E-05 | Conflicting rules on whether a short identity-conflict denominator fails 04-I | MEDIUM | MM 11.2 (`MATHEMATICAL_MODEL.md`:636) applies the 200-attempt ceiling to all three denominators: positive, negative and identity conflict. Registry 04-I asks for minimum identity-conflict denominators, "expanded … never weakened". Plan:529 and RA:401 say conflicts are "reported descriptively when fewer than a pre-registered minimum". D-040 says "identity-conflict … where feasible" | 4 | The owner fixes one rule before Step 13. The pre-registration quotes it, and MM 11.2 is aligned at the freeze review |
| E-06 | Attachment precision covers 2 of the 4 positive classes | MEDIUM | SPEC 7.2 has four `verified_fact` positive classes, including `CORRECTION_CITED` and `REINSTATED_WORK_CITED`. RA R4-01 (lines 26–39) counts all four as false-attachment risk. Plan:530 and MM:629 define precision over `RETRACTED_WORK_CITED`/`CONCERN_CITED` only | 4 | Pre-registration states the treatment of the other two classes: in the denominator, a separate count, or a zero-tolerance hazard. The failure criterion then covers them explicitly |
| E-07 | Recall and the negative denominator have no stated measurement | LOW | Plan:530 lists "census-referenced recall", but plan:529 gives it no denominator or interval, and MM 11.2 omits recall. RA R4-05 (line 99) uses a different notion ("measured on the sampled units without keys"). Plan:529 defines the negative denominator as "units with candidate keys and no record, checked for false positives". Under D-16 such units are `NOT_FOUND_IN_CHECKED_SOURCES` and cannot be positive [inference: the intended check is missed attachments or structural wording] | 4 | Pre-registration defines each metric with its unit, denominator, label question and interval. Alternatively, recall is declared descriptive |
| E-08 | Holdout analyses named by the plan have no implementation yet, frozen or pre-registered | MEDIUM | Plan 8.4 (line 386): sensitivity variants (a) `identifier_link` excluded, (b) P-2 disabled, (c) `labeled_reference_text` included, "once on dev and once on holdout". `grep` finds no variant code in `src/citerift/investigation`, and no dev sensitivity run is recorded. The plan 13 naive baseline exists only as review script `review/step9/dev_measurements.py` | 8 | Commit and hash the variant and baseline computations, and the scorer, before the draw: in the freeze or the Step 13 pre-registration. Run the dev sensitivity analysis before the freeze so the holdout run is a replay of fixed code |
| E-09 | The freeze scope and the freeze → pre-registration → draw ordering exist only in the plan and RA | LOW | Plan:404–406 ("frozen (commit and hash)") and plan:587–589 do not say what is hashed. Registry 04-I and D-040 say "pre-registered before the draw" but do not mention the engine freeze. The open items (A-6 engine-version bump, D-062 index identity, I-2, I-3; D-061/D-063) all change identity before the freeze | 4 | The freeze record names: commit SHA; tree hashes of the owned paths; dt-1 table version and digest; `STAGE04_IDENTITY`/engine version after A-6; the D-062 canonical Stage 02 identity; the Stage 03 engine identity; the RW snapshot receipt. Step 14 checks the ancestry freeze ⊂ pre-registration ⊂ draw (R4-18 detection) |
| E-10 | The English frame source is not in the repository | MEDIUM | `docs/verification/stage-01/data/README.md`:42: "The full English dump scan is not committed (its summary is)." The plan's English frame is "Stage 01 English dump scan" (plan:524; AS_REVIEWED:462, "745 articles"). The Arabic frame files exist (`census/ar_*.json`) | 8 | Step 13 re-derives the English frame reproducibly (committed script, pinned dump), or obtains the scan, and commits the frame digest before the seed is used. The frame contents were not inspected in this review |
| E-11 | Docstrings understate Stage 03 evaluation reuse | LOW | `tests/stage04/step10_support.py`:5–6 says "no Stage 03 evaluation or holdout bundle". Yet Step 10 tests use `AR_BCAS3`, `AR_COCHRANE` and `EN_CONCERN` (lines 23, 31) from `docs/verification/stage-03/evaluation/…/challenge`. Two of these (ar 76488293, ar 74891699), VS-6a ar 73356164 and the B-8 unit en 1379214029 each have a file in `stage-03/evaluation/annotations/locked/`, so they were Stage 03 evaluation items. Step 9 dev measurements ran 160 revisions from Stage 03 holdout groups (development-labelled) | 4 | Reword as "no Stage 04 holdout; Stage 03 challenge, reserve and holdout bundles are reused as design-exposed development data". This is not leakage for Stage 04, and Stage 03 results are unaffected [inference] |
| E-12 | The id "F-15" means two different things | INFO | Plan §11 F-15 = "Evaluation leakage" (plan:470; RA:501). D-041 / Step 3 F-15 = root binding (`STEP4_OWNER_DECISIONS.md`:11; SPEC:145) | 4 | Qualify the id in the freeze review (e.g. "plan F-15", "Step 3 F-15") |
| E-13 | 04-C "on the development set" is not defined, and the differential evidence is synthetic | LOW | Registry 04-C (line 21227): "zero differences … on the development set"; plan 04-C: "all development units". Step 9 differential: 244,884 enumerated valid cases, 0 mismatches (`differential.json`). `dev_measurements.py` makes no oracle comparison on the 232 real revisions | 4 | Define "development set" at the freeze. Either name the enumerated domain, or add an oracle comparison over the manifest's real units |
| E-14 | Frame feasibility after exclusion, and pre-existing frame content | INFO | Plan:524 frame vs plan:537 ("unknown until the frame is profiled"). Stage 01 `census/ar_render.json` already holds reference excerpts for Arabic census pairs (README:37); no Stage 04 file references `ar_render`, `ar_confirm`, `ar_scan` or `purposive_discovery` [fact, grep]. The 60 Stage 01 purposive articles and the 16 matched articles are likely census-frame members [inference] | 8 | Limit pre-registration frame profiling to identity and stratum counts after exclusion. Forbid use of Stage 01 excerpts as labels or engine input |

**E-01.** Today the development set exists only as "whatever `capture.json` files the glob finds". The Step 9 output does record the 232 chosen bundle paths, keyed `wiki-revision`. The planning figure of 255 directories has no retained derivation. Step 9 A-8 explains it as drift from later retained bundles, but git shows 257 bundle directories at every commit since `b93314d`, which is before planning. A frame-exclusion check (R4-19) needs a fixed, hashed list. A glob that silently grows or shrinks is not enough.

**E-02.** Stage 03's last committed exposure set was computed before its own D-036 draw, so it misses the 44 articles that draw captured. Plan 12.3 excludes "Stage 03 exposure set" without saying which version; taking the committed file would leave 44 exposed articles in the Stage 04 frame. Stage 03's rule, rerun now, covers every retained bundle. It is over-inclusive and wiki-agnostic (integers and titles from any committed JSON).

**E-03.** Two Arabic articles selected and attempted by Stage 03 left no bundle. Ten Stage 03 development articles survive only as (wiki, title). Neither group is in the 232. Title-only identity is weak because pages can be moved, so exclusion must also match redirect titles.

**E-04.** The documents differ in which set is excluded:

| Document | Set excluded |
|---|---|
| Registry gate | Stage 03 planning revisions |
| D-5 | 16 articles |
| Plan 12.3 | Stage 03 exposure + 232 + Stage 01 purposive |
| R4-19 | Adds Obokata; article-level match |

None contradicts excluding the full union, but a pre-registration that quoted only the gate would under-exclude.

**E-05.** One set of wording makes the identity-conflict denominator a hard minimum that fails 04-I (MM 11.2, registry). The other makes it a descriptive count below its minimum (plan, RA, D-040 "where feasible"). Only the owner can reconcile them, and they must be reconciled before Step 13.

**E-06.** Correction and reinstatement findings are positive `verified_fact` claims, but no metric denominator covers them. They are reachable only through the vague "any false attachment above the pre-registered bound" (R4-01).

**E-07.** "Census-referenced recall" is listed as a metric but has no denominator. The "negative" denominator's measurement is described as checking for false positives on units that cannot be positive.

**E-08.** Plan 8.4 promises a sensitivity analysis on both dev and holdout. Plan 13 promises a naive-baseline comparison on the holdout. Neither is implemented in code that will be frozen, and the dev sensitivity run has not happened. If they are written after the draw, they are analyses written with the holdout in view.

**E-09.** "Freeze commit and hash" has no defined content, and the gate text does not state the freeze-before-draw ordering. Several identity changes are still pending for Step 12. The freeze is therefore only well defined if its record enumerates the identities it pins.

**E-10.** The English frame cannot be digested from the repository as it stands. This is a Step 13 prerequisite.

**E-11.** Several Stage 04 inputs were Stage 03 evaluation items: challenge and reserve bundles, with locked Stage 03 labels. The Step 9 development run also included 160 Stage 03 holdout revisions. All of this is correctly labelled development data, and it is all Stage 04 exposure. One docstring wrongly says no Stage 03 evaluation bundle is used.

**E-12.** The same identifier "F-15" names two unrelated items. A freeze review could misread it.

**E-13.** The registry's "development set" for 04-C has no definition. The only differential (0 mismatches) is over the Step 4 enumerated domain, not over the real development units.

**E-14.** Inference only. Excluding the Stage 01 purposive pages and the matched articles may thin the Arabic census-positive stratum. The plan already plans for this with profiling first and pre-registered expansion. Profiling must stay at identity and count level.

## 3. Exposure sources and proposed manifest rule

### 3.1 Sources (counted at HEAD 65c30bd, by script)

| Source id | Where the list lives | Identity recoverable | Count |
|---|---|---|---|
| S03-BUNDLE | Every tracked `capture.json` (`git ls-files`; same 257 at `a152885` and HEAD). Fields `page.wiki`, `page.page_id`, `page.revision_id`, `page.title` are present in all 257. Request wiki equals page wiki in all 257 | yes, all | 257 dirs; 232 distinct revisions = 232 distinct articles (ar 113, en 119); 1 revision per article |
| ↳ by group | `docs/verification/stage-03/evaluation/{capture,final,confirmation-2026-11,confirmation-d035,confirmation-d036}/…/holdout` | yes | 23 + 20 + 41 + 41 + 42 dirs. 160 articles appear in a holdout group; 160 of the 232 bundles used in Step 9 are holdout bundles |
| ↳ | reserve, reserve1, reserve2, challenge, confirmation-superseded, demonstrations (3), current-checks (12), review/failfirst (5), `tests/stage03/fixtures/observed` (2) | yes | see `bundles.json`; 2 articles occur in more than one group kind |
| S04-DEV-232 | `docs/verification/stage-04/review/step9/dev_measurements.json` `revisions` (keys `wiki-revision`, field `bundle`) | yes, via `bundle/capture.json` | 232 (ar 113, en 119); label "DEVELOPMENT EVIDENCE ONLY" |
| S04-VS | `docs/verification/stage-04/evidence/vertical-slice/run_vertical_slice.py`:54–64 | yes | 8 cases (VS-1, 2, 3a, 3b, 4, 5, 6a, 6b), all within S03-BUNDLE |
| S04-TESTS | `tests/stage04/step8_support.py`:43–45; `test_step9_real.py`:255–263; `test_step9_b8.py`:32; `test_step11_vertical_slice.py`:51–52 | yes | all within S03-BUNDLE. Scan of Stage 04 paths: 24 revision-like integers, 13 match bundles, 11 are byte counts, hash prefixes or synthetic mutations (1372543633, 1381772672) |
| S03-NOBUNDLE | `stage-03/evaluation/confirmation-superseded/capture/capture_states.json` | (wiki, page_id) | 2 (ar 4823675, ar 6468321) |
| S03-DEV-TITLE | `stage-03/calibration/dev_selection.json` (12) and `dev_selection_supplement.json` (3) | title and wiki only for 10; revision ids for 5 | 15 entries (ar 8, en 7) |
| S03-LISTED | Stage 03 rule `confirmation-d036/scripts/exposure_set.py` rerun at HEAD | page_id without wiki; titles | 7,038 page ids, 7,075 titles (over-inclusive) |
| S01-PURPOSIVE | `docs/verification/stage-01/data/purposive_discovery.json` (`wiki`, `pageid`, `revid`) | yes | 60 articles (en 48, ar 12), 57 confirmed; 5 overlap S03-BUNDLE |
| S01-EVIDENCE | `docs/verification/stage-01/EVIDENCE_MANIFEST.json` (11 cases) | yes | 13 articles (en 8, ar 5), all within S01-PURPOSIVE |
| S01-SAMPLE-S | `docs/verification/stage-01/data/sample_S_discovery.json` | n/a | 0 article identities (no hit titles) |
| Planning probe | Plan:155. Script not retained; the set equals S03-BUNDLE [inference from equal revision counts] | via S03-BUNDLE | 255 stated, 257 found |

**Flagged identities:**
- Every exposed bundle has wiki, page_id and revision_id.
- The 10 S03-DEV-TITLE entries and the S03-LISTED tier cannot be keyed by (wiki, page_id) offline.

### 3.2 Proposed construction rule (for the Step 13 pre-registration, generated after the freeze commit)

1. **Inputs.** Only tracked files at a named commit (`git ls-files`), no network. The generator script is committed, and its SHA-256 is recorded.
2. **One record per article:**
   ```
   {"wiki": "ar"|"en", "page_id": int|null, "title_norm": str|null,
    "titles": [sorted known titles incl. redirect titles], "revision_ids": [sorted ints],
    "sources": [sorted source ids from 3.1], "evidence_paths": [sorted repo paths]}
   ```
   - Key: (wiki, page_id) when page_id is known. Otherwise (wiki, "title:" + `title_norm`).
   - `title_norm`: NFC, `_` → space, trimmed; first character upper-cased for enwiki only.
   - Records with the same key are merged by set union.
3. **Order.** By `wiki`, then `page_id` ascending with nulls last, then `title_norm`.
4. **Canonical JSON.** `citerift.investigation.canonical.canon` (sort_keys, `(",",":")` separators, `ensure_ascii=False`, no floats), over:
   ```
   {"schema": "stage04-exposure-manifest/1", "commit": <sha>,
    "generator_sha256": …, "inputs_sha256": <sha256 of the sorted input path list>,
    "counts": {source: n}, "articles": [...]}
   ```
   The digest is the SHA-256 of these bytes. The S03-LISTED tier is kept as a separate sorted `listed_page_ids` / `listed_titles` block with its own digest, if the pre-registration adopts it.
5. **Frame exclusion, before the seeded draw.** Drop a frame article if any of the following holds:
   - its (wiki, page_id) is in the manifest;
   - its (wiki, `title_norm`) equals any `titles` entry of a manifest record;
   - (if adopted) it matches the listed tier.

   Record excluded counts per source and stratum (counts only), then the frame digest after exclusion. Commit manifest digest, frame digest and seed before the draw.
6. **Audit after the draw (R4-19).** The drawn primary, reserve and expansion blocks must not intersect the manifest by (wiki, page_id) or by title. The check runs again on capture identities, since a page can move between frame build and capture.

## 4. Leakage audit result

No evaluation leakage found.

- **No Stage 04 draw or evaluation artifact exists.** There is no `docs/verification/stage-04/evaluation/`, no seed, frame digest, pre-registration, exposure manifest, annotation or label file. No commit message mentions a Stage 04 freeze, pre-registration, draw or holdout. The only `random` and seed uses in `tests/stage04` are property-test shuffles and walks (`test_d055.py`, `test_d053_d054.py`, `test_controller_differential.py`).
- **Every real Wikipedia identity used by Stage 04 is a retained Stage 03 bundle.** This covers code, tests, evidence and docs. The live-capture paths are synthetic replays (`test_step8_live.py`:3–6; VS-8).
- **Stage 04 reads no Stage 03 labels, selections or exposure files** (`grep` for `annotations/`, `locked/`, `adjudicated`, `SELECTION.json`, `EXPOSURE_SET`: none in Stage 04 code, tests or evidence). It also reads no Stage 01 census content.
- **Development measurements are labelled correctly.** Step 9 (`STEP9_CLOSURE.md`:18–22, 241–243; `dev_measurements.json` `label`) and Step 11 (`STEP11_CLOSURE.md`:20–22, 362–366) both state that nothing is precision, recall or evaluation. The naive-baseline and originality numbers are explicitly design-exposed and "not evidence for the contribution" (`STEP9_CLOSURE.md`:280, 299–300; plan:556–559). No mislabelled measurement was found.
- **Stage 03 holdout bundles were used only as development data** (Step 9: 160 of 232). This is correct use of exposed data. It makes them Stage 04 exposure; it does not leak a Stage 04 holdout.

## 5. Checked, no finding

- The plan's 232 (ar 113, en 119) equals the measured distinct revisions and articles.
- Step 9 occurrence counts reproduce plan 2.3 (`STEP9_CLOSURE.md` §10).
- Clopper–Pearson wording agrees between plan:531 and MM 11.2. The zero-error bounds 0.0950 (n = 30) and 0.0495 (n = 59) match plan:535–536.
- The "30 primary + 10 reserve, ≤ 200 attempts, expand never weaken" wording is consistent across plan:506–512, D-040, registry 04-I and RA R4-22.
- The hazard and structural counts (notice, marker, conflict as attachment; no "not retracted"; complete evidence chains) are consistent between plan:530–532 and MM 11.2.
- The freeze → pre-registration → draw order is consistent across plan:404–406 and 587–589, plan:650, and RA R4-18.
- SPEC 14:1101 labels all VS inputs design-exposed.
- `dev_measurements.json` and the final dt-1 code were committed together (`846cb81`). Commit order therefore cannot show whether dt-1 changed after the dev numbers. This is not a leakage issue: D-5 allows design use of development data.
- D-062 says the Step 8–11 journals are development-only, and that fresh post-freeze investigations become authoritative for evaluation. This is consistent with freeze-before-draw.

Review status: VERIFIED COMPLETE (read-only review; no file in the repository was changed; pytest, ruff, mypy and citerift-gov were not run because no code was changed)
