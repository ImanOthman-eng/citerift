# Confirmation campaign report (owner instruction D-034, 2026-11-02 to 2026-11-03)

Project owner: EVE TELOS. Executor: Claude Code (implementing agent, Claude Opus). Protocol:
`../../../protocol/AMENDMENT_2026-11-02_CONFIRMATION.md` with annotation guide 1.1. Candidate: `3e51792`
(`../MANIFEST.json`, frozen in `0d46ba4`). Every figure below is read from a committed file named next to it.

**Result in one line.** Arabic passes every gate G1 to G7 and every minimum. English passes every gate except
**G5c, unit precision: 0.869 against 0.95**, on both the locked and the adjudicated labels. Under the amendment's
acceptance rule (section 10) and owner instruction section 12, the campaign therefore does **not** verify Stage 03.

## 1. What was done, in order

Each step is a commit; `audit/EVIDENCE_AUDIT.json` re-checks the order from git history.

| Step | Commit | Record |
|---|---|---|
| Candidate frozen; Stage 03 to `IMPLEMENTED_NOT_VERIFIED` | `0d46ba4` | `../MANIFEST.json` |
| Exposure set committed before the draw | `127af68` | `EXPOSURE_SET.json` |
| Draw: holdout frame (ar 24, en 16 initial, reserve order) and warning challenge (en 10, ar 0 candidates) | `d19f3f2` | `selection/SELECTION.json` |
| Capture of the initial 50 articles | `d27747b` | `capture/` |
| Evaluator packets and filled briefs, before any label | `5e2ec1d` | `annotations/packets/`, `annotations/briefs/` |
| Locked labels of the initial 50 articles, before any extraction | `8dd6d2c` | `annotations/locked/` |
| Reserve decision 1 from locked counts: en needs block `reserve1`; ar complete | `24bf009` | `reserve/step-1.json` |
| Capture, packets and locked labels of en `reserve1` (4 articles) | `10689b0`, `6f39025`, `992748f` | as above |
| Reserve decision 2: both languages meet every minimum; sample closed | `aa6e1d4` | `reserve/step-2.json` |
| The single prediction run (54 articles), verify and replay of each | `668e87c` | `prediction/runs.json` |
| Scores on the locked labels | `05e269e` | `scores/locked.json` |
| Disagreement listing (with the wrapper of section 6) | `d5ac091` | `adjudication/disagreements.json` |
| Adjudicator inputs, before any decision | `6c2b544` | `adjudication/items/`, `adjudication/briefs/` |
| Adjudication and adjudicated scores | `81d75d0` | `adjudication/`, `scores/adjudicated.json`, `scores/challenge.json` |
| Interval estimates | `0c6b662` | `scores/intervals.json` |
| Evidence-integrity audit (owner instruction section 9) | `cfd10b2` | `audit/EVIDENCE_AUDIT.json` |

**Resources.** 263 HTTP attempts and 12,593,218 accepted bytes for the whole campaign, including the draw, against
ceilings of 500 attempts and 300 MiB (recomputed from `capture/captures.jsonl` by the audit, check 8). All 54
articles were captured `complete` (49 on the first run; 5 on a second run, after a first run that ended with `ATTEMPTS_EXHAUSTED`: 3 failed, 2 partial).

## 2. Sample and denominators

| | ar | en | Minimum |
|---|---|---|---|
| Articles (gate split) | 24 (initial) | 20 (16 initial + reserve block 1) | — |
| Target identifier occurrences | 103 | 50 | 50 |
| Uses | 190 | 274 | 80 |
| Definitions | 160 | 157 | 60 |
| Linkable uses | 189 | 274 | 60 |

Both languages reach every minimum. The en identifier count is exactly the minimum. Source:
`scores/adjudicated.json`, `splits.gate.<lang>.adjudicated.engine.denominators`.

## 3. Annotation and adjudication provenance

- **Evaluators.** Ten Claude Sonnet instances (Claude Code subagents), each in its own work directory outside the
  repository, with raw packets only, under `../EVALUATOR_BRIEF_v1.1.md`. All 54 label files passed format validation
  at first submission; none was returned, edited or chosen by the executor (`annotations/EVALUATOR_RUNS.md`,
  `annotations/VALIDATION.json`).
- **Adjudicators.** Six Claude Haiku instances decided the 113 disputed items (56 in the gate split, 57 in the
  challenge) under `../ADJUDICATION_BRIEF_v1.1.md`: **104 confirmed, 9 corrected** (`adjudication/README.md`).
  - ar: 2 DOI keys lower-cased (guide 3.5), 1 marker `none` → `cannot_tell` for a footnote that does not render,
    1 template location moved to its own reference (2 decisions).
  - en gate: 2 `[[doi:…]]` interwiki links from `labeled_reference_text` to `identifier_link`.
  - en challenge: 2 Gaia EDR3 erratum notes `none` → `ambiguous`.
- **These are AI labels.** They are not human-reviewed gold data, and are not presented as such. The three models
  are from one vendor (RISK_ANALYSIS.md E9).
- **Isolation audits** (`annotations/EVALUATOR_AUDIT.json`, `adjudication/ADJUDICATOR_AUDIT.json`): no instance ran
  git, uv, a network tool or a CITERIFT command. Deviations are listed in section 6.

## 4. Gate results

Values on the **adjudicated** labels (the gate basis). Where the locked value differs, it is given in brackets.
Thresholds are those frozen in `../../../protocol/FROZEN_PROTOCOL.md` and copied unchanged into each score file.

| Gate | Threshold | ar | en |
|---|---|---|---|
| G1a identifier precision | ≥ 0.97 | 0.980 | 1.000 |
| G1b identifier recall | ≥ 0.90 | 0.951 | 0.960 |
| G2 key error rate | ≤ 0.01 | 0.000 (locked 0.0204, fail) | 0.000 |
| G3a promotions to a cited-work role | 0 | 0 | 0 |
| G3b role agreement | ≥ 0.90 | 1.000 | 0.958 |
| G4a / G4b / G4c uses: precision / recall / binding | ≥ 0.97 / 0.95 / 0.97 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| G5a / G5b definitions: precision / recall | ≥ 0.95 / 0.95 | 1.000 / 1.000 | 1.000 / 0.987 |
| **G5c unit precision** | ≥ 0.95 | 0.988 (locked 0.981) | **0.869 — fail** (126 tp, 19 fp) |
| G5d unit recall | ≥ 0.95 | 0.988 (locked 0.981) | 0.969 |
| G6a render precision / G6b false attachments / G6c coverage | ≥ 0.98 / ≤ max(1, 1 %) / ≥ 0.85 | 1.000 / 0 / 1.000 | 1.000 / 0 / 1.000 |
| G7 fabricated negative markers | 0 | 0 | 0 |
| G8 verify / G10 replay | all exit 0 | 24 / 24, 24 / 24 | 20 / 20, 20 / 20 (and the 10 challenge articles) |
| G9 acquisition | complete | 24 / 24 | 20 / 20 (and 10 / 10 challenge) |
| G11 synthetic challenge | suite passes | see TEST_RESULTS.md | see TEST_RESULTS.md |

Four extractions exited 6 (`partial`, an exception-ledger outcome the engine reports, not a crash): ar-76336375,
ar-76524679, en-1378959744, en-1329904848. All 54 extractions verify and replay with exit 0 (`prediction/runs.json`).

**The Arabic locked G2 failure** came from 2 locked keys that kept upper-case letters, against guide 3.5; the
adjudicator corrected both labels, and the engine's keys did not change.

## 5. The English G5c failure: what it is

All 19 English unit false positives are engine `unstructured_text` units in definitions where the locked label has
no unit, and the adjudicator confirmed all 19 locked labels (`adjudication/decisions/`):

| Definition body | Count | Articles |
|---|---|---|
| A `{{harvnb}}` or `{{harvp}}` Harvard short-citation link, with no citation template (one is followed by a sentence) | 13 | en-1371940951 (11), en-1361411235 (1), en-1373847247 (1) |
| An explanatory note in plain text that cites no work | 4 | en-1377237744 (3), en-1361411235 (1) |
| A citation-like template the profile does not list (`{{Fishbase}}`, `{{NRDB species}}`). The evaluator labelled it a citation template, so each also counts as one missed template unit (G5d) | 2 | en-1296237338, en-1355030157 |

**Cause.** The engine follows its own specification, SPECIFICATION.md 11.3: "a definition with no template unit is
`unstructured_text`". The annotation guide (both the frozen guide and 1.1, section 3.2) defines `unstructured` more
narrowly: "the definition cites something in plain text with no citation template". So a definition whose body is a
short-citation link, an explanatory note, or an unlisted citation-like template is `unstructured_text` for the
engine and no unit for the guide. This is a divergence between two frozen texts, not a crash, a regression or a
departure of the engine from its specification. It existed at the earlier frozen candidate too (en G5c 0.973 in the
final campaign); this sample contains one Harvard-referenced article (en-1371940951) that accounts for 11 of the 19.

**What it does not affect.** Identifiers, roles, keys, uses, bindings, definitions, render links and markers are
scored separately and pass. A unit is the classification of what a definition contains.

**What may not be done.** Under amendment section 8 there is no repair, retuning or rerun after the prediction run.
The result stands as measured. Any change to SPECIFICATION 11.3 would be post-exposure and could not be called a
fresh confirmation (`DECISION_RECORD.md`).

## 6. Deviations and defects found during the campaign

| Item | What happened | Effect |
|---|---|---|
| Evaluator first launch | All nine instances stopped on the account's usage limit at 2026-11-02 19:41Z before writing any file; relaunched unchanged at 2026-11-03 01:56Z | None on labels (`annotations/EVALUATOR_RUNS.md`) |
| `CLAUDE.md` in subagent contexts | The harness attached the repository's governance instructions to every evaluator and adjudicator context | It holds no label, output or result; recorded as a deviation from "receives only" |
| Evaluator en-r1-1 | Wrote one scan listing of its own packet to a path outside its work directory and read it back | The file holds packet text only; a copy is kept (`annotations/evaluator_tools/en-r1-1/`) |
| Adjudicator en-c1 | No reason for 20 items of en-1329904848; returned under section 7 to a new instance (en-c1b), whose result is used | Same single correction in both; the returned submission is kept |
| `disagreements_v2.py` (frozen tool) | RecursionError on the challenge split | Frozen file unchanged; a wrapper and 3 tests were added (`../scripts/disagreements_challenge_fix.py`); on the gate split the wrapper equals the frozen tool |
| `make_packets.py` (campaign tool) | Wrong repository root, and reserve blocks would have been given the challenge window; both fixed before the packets were built | The reserve windows were checked to equal the frozen window |
| Prediction runner | `run_confirmation.py` was used, as amendment section 11 (after review R6) requires, instead of the `run_holdout.py` named in section 8 | None; recorded in the amendment |

## 7. Confidence intervals (`scores/intervals.json`)

95 % article-cluster bootstrap (seed 20261028, 2000 resamples) and exact Clopper-Pearson bounds.

| Measure | ar (adjudicated) | en (adjudicated) |
|---|---|---|
| Identifier precision | [0.922, 1.000] | [1.000, 1.000] |
| Identifier recall | [0.857, 0.992] | [0.898, 1.000] |
| Role agreement | [1.000, 1.000] | [0.870, 1.000] |
| Unit precision | [0.969, 1.000] | **[0.718, 0.971]** |
| Unit recall | [0.969, 1.000] | [0.910, 1.000] |
| Definition recall | [1.000, 1.000] | [0.956, 1.000] |
| G2 key errors, one-sided 95 % upper bound | 0 / 98 → 3.0 % | 0 / 48 → 6.1 % |
| G3a promotions, one-sided 95 % upper bound | 0 / 98 → 3.0 % | 0 / 48 → 6.1 % |

The G2 and G3a point values meet their zero-tolerance gates, but at these sample sizes the data cannot exclude rates
above 1 %. The en unit-precision interval is wide because 11 of the 19 false positives are in one article; the gate
is decided on the point value, as frozen.

## 8. Positive retraction-warning challenge (`scores/challenge.json`)

- **arwiki:** no article transcludes any of the three marker templates outside the exposure set (0 candidates in
  each stratum). No Arabic field evidence of warning detection exists; this is a limitation, not a pass.
- **enwiki:** 10 articles (2 retraction of 2 candidates, 4 concern of 84, 4 correction of 585).

| Stratum | Labelled warnings | Detected | Fabricated negatives | False warnings | Other |
|---|---|---|---|---|---|
| retraction | 2 | 2 | 0 | 0 | 24 none → none |
| concern | 4 | 4 | 0 | 0 | 47 none → none |
| correction | 0 | 0 | 0 | 0 | 4 ambiguous → ambiguous, 42 none → none |
| **all** | **6** | **6** | **0** | **0** | 0 `not_inspected` |

Sensitivity 6 / 6, exact 95 % interval [0.541, 1.000]. Six positives are too few to estimate sensitivity tightly.
Not observed in the drawn articles: unsupported or ambiguous wording of a warning, red-linked templates,
source-only markers, uninspected regions, and any Arabic variant. Synthetic tests cover those cases; they are not
field evidence.

## 9. Comparison with the baseline and the earlier campaign

**Baseline B1** (regular expressions over `<ref>` tags; adjudicated labels; reported, not gated):

| Measure | ar: engine / B1 | en: engine / B1 |
|---|---|---|
| Identifier recall | 0.951 / 0.466 | 0.960 / 0.800 |
| Definition recall | 1.000 / 0.850 | 0.987 / 0.828 |
| Unit precision | 0.988 / 0.985 | **0.869 / 0.885** |
| Use recall | 1.000 / 1.000 | 1.000 / 0.891 |
| Render precision (false attachments) | 1.000 (0) / 0.598 (76) | 1.000 (0) / 0.689 (76) |

B1 also fails G5c in English, at a slightly higher value than the engine (15 false positives against 19).

**Earlier final campaign** (candidate `48cfeab`, adjudicated, `../../final/adjudication/README.md`):

| Gate | 48cfeab | 3e51792 (this campaign) |
|---|---|---|
| ar G5a definition precision | 0.914, fail | 1.000 |
| ar identifier denominator | 33, below 50 | 103 |
| en G2 key error rate | 0.0192, fail | 0.000 |
| en G5c unit precision | 0.973 | 0.869, fail |

The three failures of the earlier campaign do not recur. The new failure is in a gate the earlier sample passed.

## 10. Evidence integrity (`audit/EVIDENCE_AUDIT.json`)

`audit/evidence_audit.py` recomputes 27 checks from the committed files and git history: commit order; the frozen
candidate and MANIFEST hashes at the prediction commit and now; lock integrity; labels against packets; packets
against the capture bundles; extractions present, unchanged, verified and replayed; adjudicated files only where
items were disputed and changes only where a decision says `correct`; the resource ceilings; and byte-for-byte
reproduction of `scores/locked.json`, `scores/adjudicated.json` and `scores/challenge.json`. **All 27 pass** at
`cfd10b2`. A deliberately altered label (not committed) made check 3 fail, as intended.
