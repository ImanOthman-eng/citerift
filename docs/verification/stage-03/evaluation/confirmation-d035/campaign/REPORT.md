# Confirmation campaign report (owner instruction D-035, 2026-11-03)

Project owner: EVE TELOS. Executor: Claude Code (implementing agent, Claude Opus). Protocol:
`../../../protocol/AMENDMENT_2026-11-03_D035_CONFIRMATION.md` (committed in `1483024`, before the draw), with the
2026-11 confirmation amendment and annotation guide 1.1. Candidate: `fff0e5b` (`../MANIFEST.json`, frozen in
`b1e069e`). Every figure below is read from a committed file named next to it.

**Result in one line.** English passes every gate G1 to G7 and every minimum, including **G5c 0.994** and **G5d
0.994**. Arabic passes every gate and every minimum except **G6b: 2 wrong render attachments against a frozen limit
of 1**, both in one article (`ar-76814232`). The cause is a verified engine defect in the reconciliation of named
references inside one template's output (section 5). Under amendment section 9 and owner instruction section 10, the
campaign therefore does **not** verify Stage 03. Under amendment section 8, the defect is preserved and reported:
there is no repair, rerun or further campaign.

## 1. What was done, in order

Each step is a commit; `audit/EVIDENCE_AUDIT.json` re-checks the order from git history.

| Step | Commit | Record |
|---|---|---|
| Prospective amendment and copied campaign scripts | `1483024` | `../../../protocol/AMENDMENT_2026-11-03_D035_CONFIRMATION.md`, `../scripts/` |
| Candidate frozen; Stage 03 to `IMPLEMENTED_NOT_VERIFIED` | `b1e069e` | `../MANIFEST.json` |
| Exposure set committed before the draw | `fdc8b66` | `EXPOSURE_SET.json` |
| Draw: holdout frame (ar 70, en 59 eligible), initial plan ar 24 / en 16, reserve order | `41b2c9a` | `selection/`, `plan-initial.json` |
| Capture of the initial 40 articles | `4766a1f` | `capture/` |
| Evaluator packets and filled briefs, before any label | `763c1c4` (layout fix `b8d9834`) | `annotations/packets/`, `annotations/briefs/` |
| Locked labels of the initial 40 articles, before any extraction | `153efae` | `annotations/locked/initial-*` |
| Reserve decision 1 from locked counts: en needs block `reserve1` (identifiers 31 of 50); ar complete | `0ff6446` | `reserve/step-1.json` |
| Five captured files untracked (third-party AWS key id, section 6) | `eba17d7` | `WITHHELD_FILES.json` |
| Capture, packets and locked labels of en `reserve1` (4 articles) | `634e2e1`, `d9ad58a`, `4ed7120` | as above |
| Reserve decision 2: en needs block `reserve2` (identifiers 37 of 50) | `d9a0707` | `reserve/step-2.json` |
| Capture, packets and locked labels of en `reserve2` (4 articles) | `c39b6aa`, `f4e0162`, `dcd04c9` | as above |
| Reserve decision 3: both languages meet every minimum; sample closed | `446edeb` | `reserve/step-3.json` |
| The single prediction run (48 articles), verify and replay of each | `e2f7e0a` | `prediction/runs.json` |
| Scores on the locked labels | `2eeb8c8` | `scores/locked.json` |
| Disagreement listing, adjudicator inputs and filled briefs, before any decision | `86ef77a` | `adjudication/` |
| Adjudication, adjudicated scores, intervals | `e754cce` | `adjudication/`, `scores/adjudicated.json`, `scores/intervals.json` |
| Evidence-integrity audit | `6c499a7` | `audit/EVIDENCE_AUDIT.json` |

**Resources.** 280 HTTP attempts and 9,178,225 accepted bytes for the whole campaign, including the draw (39
requests, 80 attempts, 47 answered HTTP 429), against ceilings of 500 attempts and 300 MiB (`capture/captures.jsonl`,
audit check 8). Of 48 articles, 47 ended `complete` (41 on the first run; 6 on a second run after a first run that
ended `failed` or `partial`) and 1 ended `partial`: `holdout/ar-9335702` (revision 70571172) has its source but no
render (`ATTEMPTS_EXHAUSTED` on HTTP 429 in both runs; under the driver's rules its first, partial run is final).
It stays in the sample and was labelled and scored (section 6).

## 2. Sample and denominators

| | ar | en | Minimum |
|---|---|---|---|
| Articles (gate split) | 24 (initial) | 24 (16 initial + reserve blocks 1 and 2) | — |
| Target identifier occurrences | 61 | 60 | 50 |
| Uses | 207 | 210 | 80 |
| Definitions | 153 | 195 | 60 |
| Linkable uses | 197 | 207 | 60 |

Both languages reach every minimum. Source: `scores/adjudicated.json`, `splits.gate.<lang>.adjudicated.gates`
("minimum denominators"). There is no warning challenge in this campaign (amendment section 3).

## 3. Annotation and adjudication provenance

- **Evaluators.** Nine new Claude Sonnet instances (Claude Code subagents): ar-h1 to ar-h4 (6 articles each), en-h1
  to en-h3 (6, 5, 5), en-r1-1 and en-r2-1 (4 each). Each worked in its own directory outside the repository with raw
  packets, guide 1.1 and the unchanged brief, and was told nothing about the engine, its predictions, the D-035
  correction or any earlier result. All 48 label files passed format validation at first submission; none was
  returned, edited or chosen by the executor (`annotations/EVALUATOR_RUNS.md`, `annotations/VALIDATION.json`).
- **Adjudicators.** Three new Claude Haiku instances decided the 46 disputed items (11 articles: ar 7, en 4) under the
  unchanged adjudication brief: **45 confirmed, 1 corrected** (`adjudication/README.md`). The correction
  (`ar-76752816`) moves the quote of a DOI in a `link.springer.com/chapter/…` URL from the whole URL to the identifier
  text (guide 3.5); role and key are unchanged, and no gate value changes.
- The adjudicators **confirmed the locked labels of both G6b items** (section 5).
- **These are AI labels.** They are not human-reviewed gold data. The models are from one vendor (RISK_ANALYSIS.md
  E9).
- **Isolation audits** (`annotations/EVALUATOR_AUDIT.json`, `adjudication/ADJUDICATOR_AUDIT.json`): no instance named
  a path outside its own work directory or ran git, uv, a network tool or a CITERIFT command. Deviations are in
  section 6.

## 4. Gate results

Values on the **adjudicated** labels (the gate basis). The locked values are identical for every gate in both
languages (`scores/locked.json`). Thresholds are those frozen in `../../../protocol/FROZEN_PROTOCOL.md`, copied
unchanged into each score file. Intervals: section 7.

| Gate | Threshold | ar | en |
|---|---|---|---|
| G1a identifier precision | ≥ 0.97 | 1.000 | 1.000 |
| G1b identifier recall | ≥ 0.90 | 0.967 (59 / 61) | 1.000 |
| G2 key error rate | ≤ 0.01 | 0.000 | 0.000 |
| G3a promotions to a cited-work role | 0 | 0 | 0 |
| G3b role agreement | ≥ 0.90 | 1.000 | 1.000 |
| G4a / G4b / G4c uses: precision / recall / binding | ≥ 0.97 / 0.95 / 0.97 | 1.000 / 0.995 / 1.000 | 1.000 / 0.986 / 1.000 |
| G5a / G5b definitions: precision / recall | ≥ 0.95 / 0.95 | 1.000 / 1.000 | 1.000 / 1.000 |
| **G5c unit precision** | ≥ 0.95 | **1.000** (130 tp, 0 fp) | **0.994** (179 tp, 1 fp) |
| **G5d unit recall** | ≥ 0.95 | **0.992** (1 fn) | **0.994** (1 fn) |
| G6a render precision | ≥ 0.98 | 0.989 (182 / 184) | 1.000 (203 / 203) |
| **G6b false attachments − max(1, ⌊1 % of engine links⌋)** | ≤ 0 | **2 − 1 = 1: fail** | 0 − 2 = −2 |
| G6c render coverage | ≥ 0.85 | 0.924 | 0.981 |
| G7 fabricated negative markers | 0 | 0 (0 labelled warnings) | 0 (0 labelled warnings) |
| G8 verify / G10 replay | all exit 0 | 24 / 24, 24 / 24 | 24 / 24, 24 / 24 |
| G9 acquisition: recorded state; ≥ 80 % with source and render | | 24 recorded; 23 / 24 = 95.8 % | 24 recorded; 24 / 24 |
| G11 synthetic challenge | suite passes | TEST_RESULTS.md section 8 | TEST_RESULTS.md section 8 |

Eight extractions exited 6 (`partial`, an exception-ledger outcome the engine reports, not a crash); all 48 verify and
replay with exit 0 (`prediction/runs.json`).

**English G5c and G5d.** The D-034 failure (0.869) does not recur: 179 true and 1 false unit in 180 engine units.
**Arabic G5c and G5d** are re-established prospectively on the corrected engine (owner instruction section 10).

## 5. The Arabic G6b failure: a verified engine defect

**Where.** `ar-76814232` (page 10469946, «دلتا الثمن»), an infobox (`معلومات نجم/رصد نجم`) whose rows hold
references. The named reference `Mallama2014` is defined in the B−V row (source codepoint 1897) and reused in the U−B
row (cp 2467). The infobox renders the U−B row before the B−V row, so the first rendered marker
`cite_ref-Mallama2014_4-0` belongs to the reuse and the second, `…_4-1`, to the definition.

**Labels.** The locked label (evaluator ar-h2) assigns `…_4-1` to the definition and `…_4-0` to the reuse, with the
note "Infobox template renders its rows in a different order than the source". The adjudicator confirmed both items.
The executor checked the render independently (`…_4-0` precedes `…_4-1` in the U−B row of the retained render). The
labels are correct.

**Engine.** It paired the definition with `…_4-0` and the reuse with `…_4-1` (`prediction/extractions/ar-76814232.json`,
basis `name_in_template_output`). The scorer lists exactly these two rows as false attachments, and no other row in
either language (`scores/adjudicated.json`, `per_article`).

**Cause.** `src/citerift/wiki/reconcile.py`, `_align_unordered` (lines 282-337). Its docstring states that inside one
template's output "the template decides the order … so names pair regardless of position". For a name with more
than one use, the code nevertheless pairs the k-th source use with the k-th rendered marker (`zip(uses, rs)`, line
309), which assumes the template keeps source order. An infobox that reorders its rows breaks that assumption. Both
rendered markers point to the same note and show the same text. They differ in one place: the Parsoid `data-mw` of
`…_4-1` (B−V row) has a `body` (`mw-reference-text-cite_note-Mallama2014-4`), which marks the definition, while that of
`…_4-0` (U−B row) has none, which marks a reuse (independent integration audit, `../INTEGRATION_AUDIT.md`). The
engine's render-use record does not keep that field, so it cannot use it. The code dates from `a29bb4e` (2026-10-29) and is unchanged by D-035
(`git diff 3e51792 fff0e5b -- src/citerift/wiki/reconcile.py` is empty).

**Scope in the retained data (diagnostic, read-only).** Across the 204 retained extraction documents, 15 groups (one
name with two or more uses paired this way in one template's output) occur in 12 articles. Five of those articles
have scored render labels: this one, and four with 0 false attachments (`en-1371940951` in the D-034 gate split;
`en-1375552426`, `en-1380218630`, `en-1382843355` here). The other seven were not scored for render links (the
D-034 warning challenge scored markers only), so their pairing is unknown.

**What it affects.** Both swapped markers belong to the same reference and cite the same work, with the same
identifiers. What is wrong is the source position (which infobox row) each rendered marker is attributed to. G6b
counts exactly this, as frozen, and the gate fails.

**Classification.** A material engine defect: the code contradicts its own specification, it produces a wrong render
link silently instead of abstaining, and it decides a frozen gate. It is recorded as RISKS.md R-038 (severity high).
The two independent reviews did not report it. The reconciliation perturbation simulation had shown the class:
when a marker is moved, 107 of 1823 uses are linked to another marker of the same reference, which G6b counts as a
false attachment, and it left the real frequency to the holdout (SIMULATION_REPORT.md section 3). This is its first
observation on a real article (SIMULATION_REPORT.md, D-035 addendum).

**What may not be done.** Under amendment section 8 there is no repair, retuning, reselection or rerun after the
prediction run, and no further campaign starts. G6b is not exempted, and no label is changed to match the engine.
A correction would need a new owner authorization and a new prospective confirmation (`../DECISION_RECORD.md`).

## 6. Deviations found during the campaign

| Item | What happened | Effect |
|---|---|---|
| Partial capture `ar-9335702` | The frozen `make_packets.py` refuses a plan with a capture that is not `complete`. The failure policy and `run_confirmation.py` (RR-8) require the article to be labelled. `../scripts/make_packets_partial.py` runs the frozen file with exactly one guard changed (a capture with a bundle is accepted) | The packet has no `render.html`, as the unchanged brief allows; every other packet is as the frozen tool makes it. The article counts in G9 and in every source-side gate |
| Five captured files with a third-party AWS access key id | The wikitext and render of enwiki revision 1380218630 (`holdout/en-614753`) contain a public academia.edu presigned URL. CI on `b8d9834` failed the accepted Stage 00 secret scan | The files are untracked from `eba17d7` and ignored; their sha256 and the commits holding them (`4766a1f`, `763c1c4`) are in `WITHHELD_FILES.json`. They stay on disk unchanged; audit check 10 verifies them. The Stage 00 test is not changed. The pattern remains in git history at `4766a1f`, `763c1c4`, `153efae` and `0ff6446`, which a merge commit publishes to `main` (`../INTEGRATION_AUDIT.md` F-3) The checksum-verified export includes them |
| `CLAUDE.md` in subagent contexts | The harness attached the repository's governance instructions to every evaluator and adjudicator context | It holds no label, output or result. Two reports end with a governance line from it (en-r2-1 "NOT VERIFIED", ar-g2 "VERIFIED COMPLETE"), which has no meaning for labels |
| Self-reported times | ar-h1's `started_at`/`finished_at` (09:00-10:00) are not real; the transcript times are authoritative | None; these fields are not validated (`annotations/EVALUATOR_RUNS.md`) |
| Adjudication tools | The 2026-11 `make_adjudication_items.py` and `validate_adjudication.py` (`../../confirmation-2026-11/campaign/adjudication/`) were run unchanged, by path; they are not listed among the MANIFEST's copied tools | None; neither file has changed since the 2026-11 campaign |

## 7. Confidence intervals (`scores/intervals.json`)

95 % article-cluster bootstrap (seed 20261028, 2000 resamples) and exact Clopper-Pearson bounds. Adjudicated labels;
the locked intervals are identical.

| Measure | ar | en |
|---|---|---|
| Identifier precision | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Identifier recall | 0.967 [0.895, 1.000] | 1.000 [1.000, 1.000] |
| Role agreement | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Use precision / recall | 1.000 [1.000, 1.000] / 0.995 [0.986, 1.000] | 1.000 [1.000, 1.000] / 0.986 [0.949, 1.000] |
| Binding accuracy | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Definition precision / recall | 1.000 / 1.000 | 1.000 / 1.000 |
| **Unit precision (G5c)** | 1.000 [1.000, 1.000] | **0.994 [0.978, 1.000]** |
| **Unit recall (G5d)** | 0.992 [0.977, 1.000] | **0.994 [0.980, 1.000]** |
| Render precision | 0.989 [0.962, 1.000] | 1.000 [1.000, 1.000] |
| Render coverage | 0.924 [0.780, 1.000] | 0.981 [0.938, 1.000] |
| G2 key errors, one-sided 95 % upper bound | 0 / 59 → 4.95 % | 0 / 60 → 4.87 % |
| G3a promotions, one-sided 95 % upper bound | 0 / 59 → 4.95 % | 0 / 60 → 4.87 % |
| G7 fabricated negatives | 0 / 0 labelled warnings: no bound | 0 / 0: no bound |
| False-attachment rate (G6b; exact, computed for this report) | 2 / 184 = 1.1 %, two-sided [0.13 %, 3.9 %] | 0 / 203, one-sided upper 1.5 % |

The lower G5c and G5d bounds in English (0.978, 0.980) are above 0.95. The zero-tolerance gates G2 and G3a are met
on their point values, but at these sizes the data cannot exclude rates up to about 5 %. G7 is met vacuously: no
drawn article has a labelled warning, and there is no warning challenge in this campaign (amendment section 3), so
sensitivity to genuine warnings rests on the D-034 challenge (earlier engine, marker code unchanged).

## 8. Comparison with the baseline and the earlier campaigns

**Baseline B1** (regular expressions over `<ref>` tags; adjudicated labels; reported, not gated):

| Measure | ar: engine / B1 | en: engine / B1 |
|---|---|---|
| Identifier recall | 0.967 / 0.639 | 1.000 / 0.700 |
| Definition recall | 1.000 / 0.765 | 1.000 / 0.815 |
| Unit precision | 1.000 / 1.000 | 0.994 / 0.969 |
| Use recall | 0.995 / 0.725 | 0.986 / 0.919 |
| Render precision (false attachments) | 0.989 (2) / 0.579 (59) | 1.000 (0) / 0.753 (47) |

**Earlier campaigns** (adjudicated; preserved unchanged):

| Gate | final, `48cfeab` | D-034, `3e51792` | D-035, `fff0e5b` (this campaign) |
|---|---|---|---|
| en G5c unit precision | 0.973 | **0.869, fail** | 0.994 |
| ar G5a definition precision | **0.914, fail** | 1.000 | 1.000 |
| en G2 key error rate | **0.0192, fail** | 0.000 | 0.000 |
| ar G6b false attachments | 0 | 0 | **2 (limit 1), fail** |

No failure of an earlier campaign recurs. The new failure is in a gate both earlier samples passed; its code path
predates both earlier candidates.

## 9. Evidence integrity (`audit/EVIDENCE_AUDIT.json`)

`audit/evidence_audit.py` (the 2026-11 audit, copied, with check 10 for the withheld files) recomputes 28 checks from
the committed files and git history: commit order; the frozen candidate and MANIFEST hashes at the prediction commit
and now; lock integrity of all four batches; labels against packets; packets against the capture bundles; 48
extractions present, unchanged, verified and replayed; adjudicated files only where items were disputed and changes
only where a decision says `correct`; the resource ceilings; byte-for-byte reproduction of `scores/locked.json` and
`scores/adjudicated.json`; and the withheld files. **All 28 pass** at `e754cce`. A deliberately altered label (not
committed) made check 3 fail, as intended.
