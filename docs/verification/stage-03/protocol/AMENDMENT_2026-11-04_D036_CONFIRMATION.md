# Prospective amendment: the D-036 final confirmation campaign

*CITERIFT — Created and Directed by EVE TELOS · IM*

**Authority.** The owner's instruction of 2026-11-04, section 8 (`../authorization/OWNER_DIRECTIVE_2026-11-04_R038.md`,
DECISIONS.md D-036). It authorizes exactly one additional bounded, prospectively registered, bilingual confirmation of
the corrected candidate after the engineering readiness gate, and no other campaign. This amendment is that
campaign's protocol.

**When it was written.** It was written and committed before any article of the campaign was drawn, captured,
annotated or extracted, and after the readiness gate (section 2). No outcome of the campaign existed when any rule
below was set. The candidate revision is recorded in `../evaluation/confirmation-d036/MANIFEST.json`, committed with
this amendment and before the draw.

**What stays.** It does not change any of these:
- FROZEN_PROTOCOL.md, AMENDMENT_2026-10-29.md, AMENDMENT_2026-11-02_CONFIRMATION.md or
  AMENDMENT_2026-11-03_D035_CONFIRMATION.md;
- annotation guide 1.1;
- `scripts/evaluate.py` or `scripts/evaluate_v2.py`;
- any earlier selection, capture, label, lock, prediction, score, adjudication or report.

The D-035 campaign stays a published result: candidate `fff0e5b`, English all gates passed, Arabic G6b failed
(2 false render attachments against a limit of 1), verdict `BLOCKED_BY_VERIFIED_MATERIAL_DEFECT`. It is not rerun.
Its articles are exposed: they shaped the correction (`ar-76814232`) and were scored again post-exposure
(`../design/r038-reconciliation/post-exposure-d035/`), which is regression evidence and not part of this campaign.

## 1. What stays exactly as in the D-035 confirmation

Everything in AMENDMENT_2026-11-03_D035_CONFIRMATION.md sections 1 and 3 to 8 applies unchanged, except what section
2 below lists. In particular these stay:
- the claim under test and the support profile (FROZEN_PROTOCOL.md 1, 2). The profile file is unchanged; its digest
  is in the MANIFEST;
- the matching rules and metrics, through the unchanged `scripts/evaluate_v2.py`;
- **the gates G1 to G11 and every threshold**, in both languages. G5c and G5d ≥ 0.95 are not lowered or excluded;
  **G6b is not exempted**: false render attachments ≤ max(1, 1 % of the engine's render links), computed by the
  unchanged scorer; G6a ≥ 0.98 and G6c ≥ 0.85 stay;
- the per-language minimum denominators: 50 target identifier occurrences, 80 uses, 60 definitions, 60 linkable
  uses;
- the frozen window, the bootstrap (2000 article-cluster resamples, seed 20261028) and the Clopper-Pearson bounds
  for the zero-tolerance gates;
- failure accounting: every selected article counts, none is ever replaced, a partial capture stays in the sample;
- the population: arwiki and enwiki namespace-0 non-redirect articles whose render links to `doi.org`;
- the draw procedure, sizes, block-wise ordered reserve and reserve rule (locked annotation counts only);
- the capture driver `../evaluation/scripts/campaign_capture.py`, unchanged, with its run, wait, retry, Retry-After
  and time-limit rules;
- the annotation, lock, prediction, scoring and adjudication procedure, and the three-model rule (evaluators Claude
  Sonnet, at most 6 articles per instance, isolated work directories, raw packets only; adjudicators Claude Haiku;
  implementing agent Claude Opus);
- the briefs `../evaluation/confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md` and `ADJUDICATION_BRIEF_v1.1.md`, used
  unchanged by path;
- no warning challenge, for the reasons of AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 3. The D-036 correction
  changes only which rendered marker a use is attached to inside one template's output; marker detection,
  marker regions and container-to-note matching are unchanged (DESIGN.md section 3), and G7 is measured on the
  holdout.

## 2. What is prospectively different, and why

| Change | Why | Where |
|---|---|---|
| The candidate | the R-038 correction (engine 1.2.0, extraction schema 1.2.0) after the D-036 readiness gate: two independent reviews, dispositions, a focused re-review | `../evaluation/confirmation-d036/MANIFEST.json`; `../design/r038-reconciliation/review/` |
| A new salt | a new, independent random order | section 3 |
| A new exposure set | it now also covers the D-035 campaign and every file added since | section 3 |
| A new campaign directory, journal and ceilings | this campaign's network use is counted from zero against its own ceilings (owner instruction section 8) | `../evaluation/confirmation-d036/campaign/` |
| Copied campaign scripts | the earlier scripts stay byte-identical as their campaigns' record | `../evaluation/confirmation-d036/scripts/` |
| `make_packets_partial.py` from the start | in D-035 it was introduced during the campaign for a partial capture (a recorded deviation); here it is the packet tool before any capture | section 6 |
| The secret gate | in D-035 five captured files with a third-party AWS key id were committed and later withheld; here no such file is ever committed | section 5 |

The copied scripts differ from `../evaluation/confirmation-2026-11/scripts/` only in their docstrings and, in
`select_confirmation.py`, in the salt, the unused challenge salt, the empty challenge strata and the campaign name
`confirmation-d036`. `make_packets_partial.py` is the D-035 wrapper with one docstring paragraph added.
`secret_gate.py` is new. `tests/stage03/test_confirmation_d036_scripts.py` pins all of this.

## 3. Frame, exclusions and order

**Exposure.** Before the draw, `confirmation-d036/scripts/exposure_set.py` (copied unchanged) is run on the
repository at the amendment commit. It collects every page id and title in any JSON document committed under
`docs/verification/stage-03/` or `tests/stage03/`, including every selection, capture, label, extraction and fixture
of every earlier campaign (D-035 among them). The output, `confirmation-d036/campaign/EXPOSURE_SET.json`, is
committed before the draw. An exposed page id or title is excluded in both wikis. An article group is the page id.

**Random draw.** The frozen procedure (`list=random` in batches of 500; `prop=extlinks` with `elquery=doi.org`; at
most 6 batches for arwiki and 4 for enwiki; per wiki the draw stops at that wiki's maximum), made once by
`confirmation-d036/scripts/select_confirmation.py`. Every answer is kept.

**Order.** Eligible articles are ordered by the SHA-256 of
`citerift-stage03-confirmation-d036-2026-11-04-v1|<wiki>|<page id>`. The order depends only on the page id and the
salt, never on the engine, its predictions, any label or any earlier failure.

## 4. Sample design, reserve and feasibility

As in D-035: arwiki positions 1-24 initial, 25-48 reserve in blocks of 4 (maximum 48); enwiki positions 1-16
initial, 17-32 reserve in blocks of 4 (maximum 32). Reserve decisions use `confirmation-d036/scripts/reserve_step.py`
on committed locked counts only, per language. A minimum unmet at the maximum, at a ceiling or at the time limit is
reported against the actual denominator as **not met**.

**Statistical feasibility.** The population, sizes and minimums are those of D-035, which realized Arabic 24 articles
(initial only) and English 24 articles (two reserve blocks) with every minimum met. The resampling estimates of
AMENDMENT_2026-11-02_CONFIRMATION.md section 5 (P(all minimums met) ≈ 0.92 at the initial sizes) apply. G6b has a
fixed allowance of 1 false attachment up to 199 engine links; the corrected engine had 0 false attachments on every
retained label (1,387 correct, post-exposure), which is not a prediction for unseen articles.

**Network feasibility.** D-035 used 280 HTTP attempts and 9,178,225 accepted bytes for its draw and 48 articles; 47 of its 80 draw attempts were answered HTTP 429.
A draw plus 40 to 56 articles is expected to need about 160 to 300 attempts. **500 HTTP attempts and 300 MiB
(314,572,800 bytes) of accepted bodies** are hard ceilings for this campaign, not targets. The worst case of an
unreported run is 6 attempts and 64 MiB.

**Time.** Acquisition ends at **2026-11-14 23:59 UTC**, the constant of the unchanged capture driver, before the
deadline of 2026-11-21. It is adopted as this campaign's limit (readiness review B-6); the driver is not changed.

## 5. Capture, network and the secret gate

As in AMENDMENT_2026-11-02_CONFIRMATION.md section 6, with this campaign's own journal
(`confirmation-d036/campaign/capture/captures.jsonl`) and ceilings: the production `citerift-wiki capture --page-id`,
pinned to the latest revision at capture time; `maxlag`, Retry-After and at least 10 s between requests; the project
network gate, used by no other process during the campaign; no duplicate captures; no proxy rotation, no other route,
identity or host; no rate-limit bypass.

**Secret gate.** Before every `git add` of campaign files, `confirmation-d036/scripts/secret_gate.py` scans every
untracked file of the campaign directory with the accepted Stage 00 secret patterns (read from the unchanged
`tests/stage00/test_repository.py`) and with the access-bearing URL and key shapes that list misses (readiness review
B-3: S3 SigV2 and SigV4 presigned URLs, temporary STS key ids and session tokens, Google Cloud Storage signed URLs,
Azure shared access signatures, Google API keys, Slack webhooks; `EXTRA_PATTERNS` in the script). A matching file is never committed: it is listed in the campaign's `.gitignore`
and in `campaign/WITHHELD_FILES.json` (path, SHA-256, size, number of matches; never the matched text), kept on disk
unchanged for the prediction run, verify and replay, and included in the checksummed export. The executor never
requests or follows a URL found in such a file. An article whose files are withheld stays in the sample. If a file
that must be committed for the procedure (a label or a lock) matched, the procedure would stop and the case would be
reported as a deviation; it is not expected, because labels hold identifiers and positions, not URLs with query
strings.

## 6. Annotation, prediction, scoring, adjudication

As in AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 8, with these specifics.

**Packets.** `confirmation-d036/scripts/make_packets_partial.py` runs the frozen packet tool for every batch, so a
partial capture (source without render) gets a packet as the unchanged brief allows; an article without a bundle is
still refused. Packets of withheld captures are withheld by the secret gate in the same way.

**Labels.** Only from new Claude Sonnet evaluator instances, each seeing its raw packets, guide 1.1 and the unchanged
brief, never the engine, its predictions, the R-038 correction or any earlier failure classification. The executor
validates format only. Evaluator work directories are outside the repository; transcripts are kept.

**Lock.** `evaluate.py lock` per batch, recording the candidate revision of the MANIFEST and this amendment's commit,
committed before any extraction of those articles.

**Prediction.** One run, by `confirmation-d036/scripts/run_confirmation.py`, after every lock is committed, at the
candidate revision recorded in the MANIFEST before the draw, through the installed CLI. Every extraction is verified
and replayed. The engine's version string does not bind its code (readiness review B-7), so the MANIFEST records the
Git tree ids of `src` and `schemas` at the candidate, and immediately before the run the executor records, in the
run log, that `git rev-parse HEAD:src` and `HEAD:schemas` equal them and that `git status --porcelain -- src schemas`
is empty. A mismatch stops the run before any extraction.

**Scores.** `scripts/evaluate_v2.py score` on the locked and on the adjudicated labels. Gates use the adjudicated
labels. Both sets are published.

**Adjudication.** Disagreements by `confirmation-d036/scripts/disagreements_v2.py`; new Claude Haiku instances
adjudicate them once, under the frozen procedure and the unchanged brief.

**Intervals.** `confirmation-d036/scripts/intervals.py`, with an empty challenge input.

**Evidence audit.** As in D-035 (the D-035 audit copied, with its withheld-file check reading this campaign's
`WITHHELD_FILES.json`).

**After the run.** There is no repair, retuning, reselection, threshold change or rerun. A material defect found
after the prediction run is preserved and reported. No further campaign starts (owner instruction section 8).

## 7. Acceptance

Stage 03 moves to `VERIFIED_AWAITING_OWNER_ACCEPTANCE` only when every condition of owner instruction section 12
holds: the candidate frozen before evaluation; every mandatory gate G1 to G11 passed in **both** languages, including
G5c, G5d and G6b; the minimum denominators met; no threshold changed; no known critical or high defect; every
extraction verifies and replays; annotation independence documented; complete engineering verification at the final
revision; green CI on the final head; durable, checksum-verified evidence; the Git-history security concern resolved
or the owner-side remediation identified; governance permitting the transition. Otherwise Stage 03 stays
`IMPLEMENTED_NOT_VERIFIED` and the exact blocker is named. The executor never records acceptance and never merges.
