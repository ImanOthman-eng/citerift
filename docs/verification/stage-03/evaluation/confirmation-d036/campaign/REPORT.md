# Confirmation campaign report (owner instructions D-036 and D-038, 2026-11-04 to 2026-11-09)

Project owner: EVE TELOS. Executor: Claude Code (implementing agent, Claude Opus). Protocol:
`../../../protocol/AMENDMENT_2026-11-04_D036_CONFIRMATION.md` (committed with the freeze in `10db8cb`, before the draw),
which keeps the D-035 confirmation procedure and annotation guide 1.1. Candidate: `8901a59` (engine 1.2.0, the R-038
correction; `../MANIFEST.json`). The campaign ran from 2026-11-04 (D-036) to its interruption at `80000f2`, and was
resumed on 2026-11-09 under the owner's instruction D-038 with the original model roles. Every figure below is read
from a committed file named next to it.

**Result in one line.** On the adjudicated labels, **both languages pass every gate G1 to G11 and every minimum
denominator**: Arabic G5c 1.000, G5d 0.966, G6a 1.000, G6b 0 false attachments, G6c 1.000; English G5c 0.977, G5d
0.992, G6a 1.000, G6b 0 false attachments, G6c 1.000. The R-038 failure of D-035 does not recur, and the corrected
pairing path linked every one of its 8 uses correctly. Two results depend on adjudication or are close (section 4.1).

## 1. What was done, in order

Each step is a commit; `audit/EVIDENCE_AUDIT.json` re-checks the order from git history.

| Step | Commit | Record |
|---|---|---|
| Candidate frozen with the prospective amendment; Stage 03 to `IMPLEMENTED_NOT_VERIFIED` | `10db8cb` | `../MANIFEST.json`, amendment |
| Exposure set (6,038 ids) committed before the draw | `0dd921b` | `EXPOSURE_SET.json` |
| Draw: frame ar 48 / en 54 eligible (0 exposed), initial plan ar 24 / en 16, reserve order | `d75bff3` | `selection/`, `plan-initial.json` |
| Capture of the initial 40 articles | `86f8076` | `capture/` |
| Evaluator packets and filled briefs, before any label | `e5c1908` | `annotations/packets/`, `annotations/briefs/` |
| Locked labels of the initial 40 articles, before any extraction | `a37db94` | `annotations/locked/initial-*` |
| Reserve decision 1 from locked counts: en needs block `reserve1` (identifiers 49 of 50); ar complete | `5719e31` | `reserve/step-1.json` |
| Capture of en `reserve1` (4 articles) | `fd02b61` | `capture/` |
| Packets and filled brief of en `reserve1`, before any label | `80000f2` | `annotations/packets-reserve1/` |
| *Interruption (2026-11-04 to 2026-11-09): see section 3* | `7646fe7`, `de66152` | `../../../continuation/` |
| Owner instruction D-038 recorded; fresh brief for en `reserve1`, before launch | `bf7866a` | `../../../authorization/OWNER_DIRECTIVE_2026-11-09_RESUME_D036.md` |
| Locked labels of en `reserve1` (instance `en-r1-1b`) | `40a1aa4` | `annotations/locked/reserve1-en` |
| Blocker B-03-001 resolved with the governance tool | `7bab386` | `governance/stage_registry.json` |
| Reserve decision 2: both languages meet every minimum; sample closed | `6d2ceab` | `reserve/step-2.json` |
| The single prediction run (44 articles), verify and replay of each | `57c4c62` | `prediction/runs.json` |
| Scores on the locked labels | `b52b088` | `scores/locked.json` |
| Disagreement listing, adjudicator inputs and filled briefs, before any decision | `aee1c09` | `adjudication/` |
| Adjudication, adjudicated scores, intervals | `78cef7d` | `adjudication/`, `scores/adjudicated.json`, `scores/intervals.json` |
| Evidence-integrity audit | `1cd45a1` | `audit/EVIDENCE_AUDIT.json` |

**Resources.** 208 HTTP attempts and 7,394,021 accepted bytes for the whole campaign, including the draw (22
requests, 36 attempts, 14 answered HTTP 429 and resent after Retry-After), against ceilings of 500 attempts and 300 MiB
(`capture/captures.jsonl`, audit check 8). No network request was made after 2026-11-04: the sample closed with the
blocks already captured, well before the acquisition end (2026-11-14 23:59 UTC). All 44 articles ended `complete`:
40 at the first run and 4 at a second run after a first run that ended `partial` or `failed` on `ATTEMPTS_EXHAUSTED`,
a retryable code (`capture/capture_states.json`). The 44 extractions took 20.3 s in all (at most 0.73 s each,
`prediction/runs.json`).

## 2. Sample and denominators

| | ar | en | Minimum |
|---|---|---|---|
| Articles (gate split) | 24 (initial) | 20 (16 initial + reserve block 1) | — |
| Target identifier occurrences | 56 | 64 | 50 |
| Uses | 187 | 282 | 80 |
| Definitions | 147 | 143 | 60 |
| Linkable uses | 187 | 282 | 60 |

Both languages reach every minimum (`reserve/step-2.json`; `scores/adjudicated.json`,
`splits.gate.<lang>.adjudicated.gates`, "minimum denominators"). There is no warning challenge in this campaign.

## 3. Annotation and adjudication provenance

- **Evaluators.** Eight Claude Sonnet instances (Claude Code subagents): ar-h1 to ar-h4 (6 articles each), en-h1 to
  en-h3 (6, 5, 5) on 2026-11-04, and en-r1-1b (4) on 2026-11-09. Each worked in its own directory outside the
  repository with raw packets, guide 1.1 and the unchanged brief template, and was told nothing about the engine, its
  predictions, the R-038 correction or any earlier result. All 44 label files passed format validation at first
  submission; none was returned, edited or chosen by the executor (`annotations/EVALUATOR_RUNS.md`,
  `annotations/VALIDATION.json`).
- **The interruption and the lost instance.** On 2026-11-04 at about 14:01 UTC an instance `d036-eval-en-r1-1` was
  launched for the four reserve articles; the executing session ended before its output was committed, and its
  container no longer exists. The owner continued meanwhile with OpenAI Codex, which preserved and audited the
  checkpoint (`7646fe7`), recorded a contingent model substitution D-037 and blocker B-03-001 (`de66152`), and
  produced no label, prediction or score. On 2026-11-09 the owner ordered the campaign resumed with its original
  model roles (D-038); **D-037 was not exercised**. A fresh Sonnet instance `en-r1-1b` labelled the same four packets
  under the same brief template with only the work path and instance name rebound, committed before its launch. No
  output of the lost instance was ever observed by anyone, so no label was chosen between two runs.
- **Adjudicators.** Two Claude Haiku instances decided the 19 disputed items (9 articles: ar 6, en 3) under the
  unchanged adjudication brief: **16 confirmed, 3 corrected** (`adjudication/README.md`).
- **These are AI labels.** They are not human-reviewed gold data, and all models are from one vendor
  (RISK_ANALYSIS.md E9).
- **Isolation audits** (`annotations/EVALUATOR_AUDIT.json`, `adjudication/ADJUDICATOR_AUDIT.json`): no instance read
  the repository, the project files or another instance's directory, or ran git, uv, a network tool or a CITERIFT
  command. One deviation: en-r1-1b wrote two scratch files of its own snippet output to `/tmp/claude-0/` and read
  them back (section 6).

## 4. Gate results

Values on the **adjudicated** labels, the gate basis of the protocol. Thresholds are those frozen in
`../../../protocol/FROZEN_PROTOCOL.md`, copied unchanged into each score file. Intervals: section 7.

| Gate | Threshold | ar | en |
|---|---|---|---|
| G1a identifier precision | ≥ 0.97 | 1.000 | 1.000 |
| G1b identifier recall | ≥ 0.90 | 0.929 (52 / 56) | 0.984 (63 / 64) |
| G2 key error rate | ≤ 0.01 | 0.000 (0 / 52) | 0.000 (0 / 63) |
| G3a promotions to a cited-work role | 0 | 0 | 0 |
| G3b role agreement | ≥ 0.90 | 0.942 | 1.000 |
| G4a / G4b / G4c uses: precision / recall / binding | ≥ 0.97 / 0.95 / 0.97 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| G5a / G5b definitions: precision / recall | ≥ 0.95 / 0.95 | 1.000 / 1.000 | 1.000 / 1.000 |
| **G5c unit precision** | ≥ 0.95 | **1.000** (144 tp, 0 fp) | **0.977** (129 tp, 3 fp) |
| **G5d unit recall** | ≥ 0.95 | **0.966** (5 fn) | **0.992** (1 fn) |
| **G6a render precision** | ≥ 0.98 | **1.000** (187 / 187) | **1.000** (282 / 282) |
| **G6b false attachments − max(1, ⌊1 % of engine links⌋)** | ≤ 0 | **0 − 1 = −1** | **0 − 2 = −2** |
| **G6c render coverage** | ≥ 0.85 | **1.000** | **1.000** |
| G7 fabricated negative markers | 0 | 0 (0 labelled warnings) | 0 (0 labelled warnings) |
| G8 verify / G10 replay | all exit 0 | 24 / 24, 24 / 24 | 20 / 20, 20 / 20 |
| G9 acquisition: recorded state; ≥ 80 % with source and render | | 24 recorded; 24 / 24 | 20 recorded; 20 / 20 |
| G11 synthetic challenge | suite passes | TEST_RESULTS.md section 9 | TEST_RESULTS.md section 9 |

Two extractions exited 6 (`partial`, an exception-ledger outcome the engine reports, not a crash): `ar-10531419` and
`en-32105383`. All 44 verify and replay with exit 0 (`prediction/runs.json`).

### 4.1 Results that depend on adjudication or are close

- **Arabic G2 is decided by one adjudicated correction.** On the locked labels, Arabic G2 is 1 key error in 52
  matched identifiers (0.0192 > 0.01, `scores/locked.json`). The disputed item (`ar-73440513`, a DOI written across
  several display links, `10.2305/IUCN.` …) was adjudicated under the frozen procedure: the adjudicator kept the final
  `.` as part of the DOI, which continues in the following link displays, so the locked key was corrected and the
  engine's key matches it. With the adjudicated label G2 is 0 / 52. The protocol decides gates on adjudicated labels
  (AMENDMENT_2026-11-02_CONFIRMATION.md section 8, kept by D-035 and D-036); the executor neither chose nor edited the decision. Every other gate value is identical
  on locked and adjudicated labels except English G5c (0.970 locked, 0.977 adjudicated) and G5d (0.992 both); both
  pass either way.
- **English G5c's interval reaches below the threshold.** The point value 0.977 (3 false units, all in
  `en-1377880902`) passes; its 95 % article-cluster bootstrap interval is [0.929, 1.000]. The frozen gate is on the
  point value. Two of the three false units are explanatory notes with a link that the adjudicator called borderline
  pointers rather than citations.
- **Arabic G5d is 0.966** (5 missed units, all in `ar-77132099`: Harvard-style templates inside one composite note,
  confirmed by the adjudicator as citation templates); interval [0.897, 1.000].

## 5. The R-038 correction on unseen articles

The D-035 failure was two swapped render links of one repeated reference name inside an infobox (RISKS.md R-038).
Engine 1.2.0 pairs such a group only on evidence and abstains otherwise. On the 44 unexposed articles:

- G6b: **0 false attachments** in either language, and **0 abstained** linkable uses (G6c 1.000 in both).
- The corrected path itself (`basis: reference_role_in_template_output` in `prediction/extractions/`) linked **8 uses
  in 3 articles** (`ar-73694006` 4, `en-1343268522` 2, `en-1374321138` 2); since no render link in the sample is
  false, all 8 are correct. Other template-output bases: `single_use_in_template_output` 62,
  `name_in_template_output` 5, `anchor_in_template_output` 5, `single_anonymous_in_template_output` 1 (diagnostic
  counts, read-only).

This is one prospective sample: 8 uses on the corrected path in 3 articles is a small field test of that path.

## 6. Deviations found during the campaign

| Item | What happened | Effect |
|---|---|---|
| Interruption and lost instance | Section 3. The lost instance's output, transcript and isolation audit were never committed and are unavailable; a fresh instance replaced it under D-038 | No label of the reserve block existed before `en-r1-1b`; the brief was committed before launch; the replacement is recorded in `LOCK_RECORD.json` |
| Original transcripts | The seven 2026-11-04 evaluator transcripts lived in that session's container and are no longer available. Their isolation audit was committed then (`a37db94`) and is kept byte-identical | Those audits cannot be recomputed from transcripts now; the 2026-11-09 transcripts are in the private evidence export |
| en-r1-1b scratch files | In one Bash call the instance redirected its own snippet output (from its own packet) to `/tmp/claude-0/h1.txt` and `h1s.txt`, outside its work directory, and read them back (2 of 16 calls flagged) | It broke the letter of brief rule 1; no other input reached it, so the independence condition holds. Labels kept as submitted; both files are in the private export |
| `CLAUDE.md` in subagent contexts | The harness attached the repository's governance instructions to every evaluator and adjudicator context, as in earlier campaigns | It holds no label, output or result |
| Adjudication tools | The 2026-11 `make_adjudication_items.py`, `validate_adjudication.py` and `audit_evaluators.py` were run unchanged, by path | None; none has changed since the 2026-11 campaign |
| Audit of one instance | `audit_evaluators.py` was run on a map holding only en-r1-1b and its entry added to `EVALUATOR_AUDIT.json` | Running it on the full map would have replaced the seven committed entries with "missing" |

## 7. Confidence intervals (`scores/intervals.json`)

95 % article-cluster bootstrap (the frozen scorer's seed and resample count) and exact Clopper-Pearson bounds.
Adjudicated labels.

| Measure | ar | en |
|---|---|---|
| Identifier precision | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Identifier recall | 0.929 [0.850, 0.981] | 0.984 [0.947, 1.000] |
| Role agreement | 0.942 [0.827, 1.000] | 1.000 [1.000, 1.000] |
| Use precision / recall | 1.000 / 1.000 | 1.000 / 1.000 |
| Binding accuracy | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| Definition precision / recall | 1.000 / 1.000 | 1.000 / 1.000 |
| **Unit precision (G5c)** | 1.000 [1.000, 1.000] | **0.977 [0.929, 1.000]** |
| **Unit recall (G5d)** | 0.966 [0.897, 1.000] | 0.992 [0.972, 1.000] |
| Render precision / coverage | 1.000 / 1.000 | 1.000 / 1.000 |
| G2 key errors, one-sided 95 % upper bound | 0 / 52 → 5.6 % | 0 / 63 → 4.6 % |
| G3a promotions, one-sided 95 % upper bound | 0 / 52 → 5.6 % | 0 / 63 → 4.6 % |
| G7 fabricated negatives | 0 / 0 labelled warnings: no bound | 0 / 0: no bound |

The zero-tolerance gates G2 and G3a are met on their point values, but at these sizes the data cannot exclude rates
up to about 5 %. G7 is met vacuously: no drawn article has a labelled warning and there is no warning challenge, so
sensitivity to genuine warnings rests on the D-034 challenge (6 / 6; earlier engine, marker code unchanged since).

## 8. Comparison with the baseline and the earlier campaigns

**Baseline B1** (regular expressions over `<ref>` tags; adjudicated labels; reported, not gated):

| Measure | ar: engine / B1 | en: engine / B1 |
|---|---|---|
| Identifier recall | 0.929 / 0.839 | 0.984 / 0.828 |
| Definition recall | 1.000 / 0.980 | 1.000 / 0.867 |
| Unit precision | 1.000 / 1.000 | 0.977 / 0.960 |
| Use recall | 1.000 / 0.968 | 1.000 / 0.848 |
| Render precision (false attachments) | 1.000 (0) / 0.806 (35) | 1.000 (0) / 0.929 (17) |

**Earlier campaigns** (adjudicated; preserved unchanged):

| Gate | final, `48cfeab` | D-034, `3e51792` | D-035, `fff0e5b` | D-036, `8901a59` (this campaign) |
|---|---|---|---|---|
| en G5c unit precision | 0.973 | **0.869, fail** | 0.994 | 0.977 |
| ar G5a definition precision | **0.914, fail** | 1.000 | 1.000 | 1.000 |
| en G2 key error rate | **0.0192, fail** | 0.000 | 0.000 | 0.000 |
| ar G6b false attachments | 0 | 0 | **2 (limit 1), fail** | 0 |

No failure of an earlier campaign recurs. This is the first prospective campaign in which every gate passes in both
languages.

## 9. Evidence integrity (`audit/EVIDENCE_AUDIT.json`)

`audit/evidence_audit.py` (the D-035 audit, copied, with check 10 changed to "nothing withheld") recomputes 25
checks from the committed files and git history: commit order; the frozen candidate and MANIFEST hashes at the
prediction commit and now; lock integrity of all three batches; labels against packets; packets against the capture
bundles; 44 extractions present, unchanged, verified and replayed; adjudicated files only where items were disputed
and changes only where a decision says `correct`; the resource ceilings; byte-for-byte reproduction of
`scores/locked.json` and `scores/adjudicated.json`; and no withheld or secret-pattern file among the 697 tracked
campaign files. **All 25 pass** at `1cd45a1`. A deliberately altered label (not committed) made check 3 fail, as
intended.
