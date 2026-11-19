# Stage 04 scientific evaluation: pre-registration P2 (gate 04-I, corrected dt-2 engine)

Status: **SUBMITTED FOR OWNER ACCEPTANCE. Not in force.** Until the owner accepts P2 by its manifest digest, no seed
is fixed, no sample is drawn, no article is captured, nothing is annotated and no prediction is run. After acceptance,
nothing in this directory (`evaluation-p2/`) or in the external files the manifest lists may change; a change needs an
explicit owner decision recorded before the draw, and no metric definition may change after the draw (D-068).

Scope: Stage 04 Step 13, new pre-registration P2 only (owner message
`cmsg_018VCB51nDHP6HXmLU4ea5yP9UYHLzpXxFTSu95UPqEi99`, 2026-11-19, recorded as D-076). Step 14 is not authorized by
this document.

**The historical evaluation is untouched.** The first pre-registration P (`4eded723…1098a`, commit `827ac1a`, files
in `../evaluation/`), its seed, draw, labels, `RUN.json`, `SCORES.json`, the failed campaign report and the 80
evaluated articles (`../evaluation-campaign/`, commit `1064113`) are immutable historical evidence (D-071, D-074,
D-076). P2 lives only in `evaluation-p2/`; it reads three of P's committed inputs (the English dump scan, the listed
tier and P's manifest, as a reference) without changing them. Those 80 articles are development-exposed and excluded
(section 3).

Every file of `evaluation-p2/` and every external input P2 reads is listed with its SHA-256 in
`PREREGISTRATION_MANIFEST.json`; its canonical digest is the identity of P2 (section 4.1).

## 1. What is evaluated, against what

| Item | Value |
|---|---|
| Engine | the accepted freeze-2 (D-076): content commit `28ba6467c7005eec7bf51869974719a402059ca7`, tree `45c52da459b09597f105d6e4abd8ab00332c6799`, freeze manifest digest `d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13`, attestation `6dab7f8ea1b97982dca978c38ca0fc8eea6e1a7f` (CI runs 365 and 366) |
| Engine identity | engine 0.3.0, decision table dt-2, Stage 04 common schema 4.0.0, claim schema 3.0.0, plan `plan-1`, detector `citerift-dt1-detector/3 (dt-2)` |
| Exposure | exposure manifest v2, `freeze-2/exposure/EXPOSURE_MANIFEST.json`, SHA-256 `b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b` (378 articles) |
| Checked source | the Stage 02 index of the pinned Retraction Watch snapshot `rw-2f116e9ffed718e6` (CSV SHA-256 `2f116e9f…0a655`), identity per D-062/D-064 |
| Extraction, capture | the accepted Stage 03 extractor and capture inside the frozen tree, as in P |
| Unit of analysis | a Stage 03 citation unit of a captured article revision |

**Engine identity is enforced, not assumed.** `tools/p2_common.engine_check` (called by the runner, the scorer and the
development run) refuses with `EngineMismatch` unless: the freeze manifest at the content commit has the pinned
canonical digest; that commit has the pinned tree; the running package reports exactly the identity above (engine and
package version, `dt1.TABLE_VERSION`, schema version, claim-schema version, plan and detector); and the trees of `src`,
`schemas`, `pyproject.toml` and `uv.lock` at `HEAD` equal the content commit's, with no uncommitted change.
`exposure_check` refuses any exposure manifest but the pinned one. The runner also probes the engine its article
subprocesses import (`python -I`) and refuses another version or location (tests: section 16).

## 2. Owner decisions applied

| Decision | How it is applied |
|---|---|
| D-3 (D-040) | two independent blinded Claude Sonnet annotators, a third Sonnet adjudicator, labels locked before predictions, AI-generated single-vendor disclosure (section 7) |
| D-5 (D-040) | 30 primary and 10 reserve articles per language, expansion within 200 attempts, denominators never weakened, no prevalence claim (sections 5, 10) |
| D-064, D-066 | each engine process verifies the index by `verify_index_identity`; the ≤ 5 s p95 target is NOT_MET and nothing here measures or claims it |
| D-067 | identity conflicts exhaustive and descriptive, no minimum (8.7) |
| D-068 | primary precision over the four positive classes, per language, exact interval; per-class results; optional secondary subset (8.2 to 8.4) |
| D-069 | baseline and sensitivity variants as evaluation-only tooling, committed and hashed here, self-checked on exposed data (section 11) |
| D-070 | the Stage 03 listed-only tier stays in the frame (3.3) |
| D-071 to D-075 | the dt-2 limitations are declared before the draw (section 13) |
| D-076 | this P2: frozen identity (1), exposure v2 (3), gates unchanged (10), new metrics (8.8, 8.9), corrected runner (9), new seed commitment (4.2) |

As in P (section 2 there, accepted by D-070), registry gate 04-I's "identity-conflict denominator" wording and
MATHEMATICAL_MODEL.md 11.2's two-class precision are read as superseded by D-067 and D-068.

## 3. Frames

### 3.1 Source and members

Unchanged from P (3.1, 3.2): per language, the Stage 01 `dump-scan` of the 2026-10-01 Wikimedia dumps against the
pinned Retraction Watch CSV (`stage-01/data/census/ar_scan.json`; `evaluation/frame/en_scan.json`, both read only).
A member is a namespace-0 non-redirect page of the scan. **S1**: a linked record of nature `Retraction` reached through
the original paper's identifier; **S2**: every other member. Only identities, strata and counts are computed; no
article content is read.

### 3.2 Exposure exclusion (exposure manifest v2)

A member is excluded when its (wiki, page id) is a record of exposure manifest v2, its (wiki, normalized title) is one
of a record's titles, or its normalized title is an exposed title of the other wiki. Manifest v2 holds every article
of the Step 12 manifest (all Stage 03 bundles, attempts and development titles, the 232 Stage 04 development
revisions, Stage 01 purposive pages and evidence) plus the 80 articles of the failed campaign (`S04-CAMPAIGN-80`) and
every bundle the corrective cycle's code, tests and evidence name (root cause, regression, adversarial and vertical-
slice cases; `S04-REF`). Exclusion is by article identity, never by revision: **no article of the first campaign can
re-enter through another revision.**

The rule is applied again at capture time to each captured page's current page id and title
(`p2_acquire.exposure_check`, reading the pinned v2): a match is the acquisition failure `EXPOSED_AT_CAPTURE` (5.3).
A page moved after 2026-10-01 to an exposed title, or an exposed page reached under a new title, is caught by one of
the two keys.

### 3.3 Stage 03 listed-only tier (D-070 kept)

Pages only present in Stage 03 selection lists, never captured, read, annotated or used for design, stay in the frame
and are marked `listed_only` (`PARAMETERS.json` `frame.exclude_listed_tier` false). The listed tier is P's committed
file, checked against the `listed.output_sha256` that exposure manifest v2 records (`84653870…beff35`, unchanged from
v1). No new evidence shows a listed-only page was exposed: the corrective cycle inspected only articles that manifest
v2 lists, and the 80 campaign articles are excluded by their own identities.

### 3.4 Counts after exclusion

`frame/FRAME.json` (format `citerift-stage04-eval-frame/2`, `tools/p2_frame.py`) holds every member with its stratum,
every excluded page with its reasons **and the sources of the manifest records it matched** (the exclusion audit),
the digest of each frame, and the no-overlap proof.

| | ar | en |
|---|---|---|
| namespace-0 non-redirect pages | 195 | 745 |
| before exclusion, S1 / S2 | 158 / 37 | 432 / 313 |
| excluded (first reason: page id / title / other-wiki title) | **56** (53 / 2 / 1) | **100** (96 / 1 / 3) |
| **P2 frame, S1 / S2 (total)** | **110 / 29 (139)** | **346 / 299 (645)** |
| of which `listed_only` (S1 / S2) | 7 (7 / 0) | 412 (253 / 159) |
| historical P frame, S1 / S2 | 143 / 37 (180) | 380 / 307 (687) |

**No-overlap proof** (`FRAME.json` `overlap_check`, recomputed independently by the tests): 0 frame members share a
(wiki, page id), a (wiki, normalized title) or a normalized title in any wiki with exposure manifest v2; 0 of the 80
campaign articles is in either frame.

**Stability (E-14).** Exclusion removes 48 of 158 Arabic S1 members (30 %) and 86 of 432 English S1 members (20 %);
S2 loses 8 and 14. Per language 40 positions are planned before expansion (29 in S1, 11 in S2); Arabic keeps 110 S1
and 29 S2 members, English 346 and 299. No stratum is exhausted before the 200-attempt ceiling can be reached by the
planned positions, so the frame definition is kept (the STOP condition of D-076 section 4 is not met). In Arabic the
expansion blocks reach S2 after 81 S1 positions beyond the primary and reserve ones, as in P.

## 4. Seed and draw order

### 4.1 Identity of P2

`PREREGISTRATION_MANIFEST.json` (format `citerift-stage04-eval-preregistration-manifest/2`, `tools/p2_manifest.py`)
lists every file of `evaluation-p2/` (this document, `PARAMETERS.json`, the guide, the briefs, `FRAME.json`, every
tool, the development run) and the external inputs P2 reads (the Stage 01 Arabic scan and script, the English scan and
listed tier of P, the Stage 03 exposure rule, P's manifest, the freeze-2 manifest, exposure manifest v2, the test file
`tests/stage04/test_p2_evaluation.py`), each with its SHA-256, plus the frozen-engine identity, the exposure pin and
the historical P it does not change. Its canonical digest (sorted keys, no whitespace, UTF-8, SHA-256) is **P2**. The
owner accepts P2 by that digest. Rebuilding the manifest from the committed files reproduces it (tests, section 16).

### 4.2 Seed (new commitment)

As in P, with a new commitment that cannot reuse P's round or randomness:

- beacon: drand `quicknet` (chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`, period 3 s); a
  round's randomness is the SHA-256 of its BLS signature, checked by the tool; the signature is kept in `SEED.json`;
- round `R`: the **first registered quicknet round at least one hour after the owner's future acceptance message of
  P2**, fixed by that message's timestamp alone; P's round 34067905 is long past and can never be selected;
- read from `api.drand.sh`, `api2.drand.sh`, `api3.drand.sh` and `drand.cloudflare.com`; at least two must agree; if
  no two agree within 24 hours of the round time, the draw stops for an owner decision; no other round is used;
- seed = SHA-256(`citerift-stage04-eval-seed/2|P2|R|randomness`) (new tag `/2`; P2 differs from P).

### 4.3 Order

Within each (wiki, stratum), members are ranked by SHA-256(`citerift-stage04-eval-order/2|seed|wiki|stratum|page_id`),
ascending (`tools/p2_draw.py plan`, written to `DRAW.json`). No seed or draw exists now.

## 5. Sampling, acquisition, replacement, expansion

Unchanged from P (sections 5.1 to 5.5; `PARAMETERS.json` `sampling` and `acquisition` are identical to P's, checked
by the tests).

| Per language | historical P | P2 |
|---|---|---|
| primary S1 / S2 | 22 / 8 | 22 / 8 |
| reserve S1 / S2 (replacements only) | 7 / 3 | 7 / 3 |
| expansion block | 10 from S1 in order, S2 when S1 is used up; at most 12 blocks | same |
| expansion targets (engine-independent) | ≥ 40 identifier-reached truth-positive units, ≥ 75 negative-proxy units | same |
| ceiling | 200 acquisition attempts, both languages together | same |

**Denominator analysis (why nothing changes).** G2 uses the exact one-sided 95 % Clopper–Pearson upper bound: with 0
false attachments it passes from n = 30 (0.0950), with 1 from n = 46 (0.0990), with 2 from n = 61. G1 already requires
n ≥ 30. The expansion targets keep a margin over G1 and G5 because they are counted before any prediction. Nothing in
the frame, the gates or the method has changed in a way that would justify another allocation: the strata, their
roles (S1 for positives, S2 for notices, concerns and corrections) and the attempt ceiling are as accepted. The first
campaign's result (one false attachment in 42 English positive units) is development evidence and was **not** used to
choose a sample size; no allocation was chosen so that one error would pass G2.

Acquisition (5.3), replacement (5.4: only a failed primary position, only by the next reserve of the same language and
stratum in draw order; never because of content, labels or predictions) and expansion (5.5) are word for word P's.
`EXPOSED_AT_CAPTURE` uses exposure manifest v2 (3.2).

## 6. Item set and packets

As in P (section 6): candidate records are reached by identifier (any role) or by title tokens (|T(r)| ≥ 4, coverage
≥ 0.8, at most 5); the item set is every unit with a candidate record; packets (`tools/p2_packets.py`) never import or
run the Stage 04 engine and show nothing of Stage 04 (no class, rule, reason, key choice or lookup state).

**P2 addition (publication-object evidence).** Packet format `citerift-stage04-eval-packet/2`: each record also states
`same_identifier_for_work_and_notice`, the schemes in which the Retraction Watch record itself gives one identifier as
both the original paper's and the notice's, computed from the record's own fields. With the unit text, the record's
title, nature, original and notice identifiers, journal, authors, dates and the search reason ("as original", "as
notice", "title tokens"), it lets the annotator tell a cited work from a cited notice or withdrawal, a same-work
citation whose publication object is ambiguous, and an unrelated record.

## 7. Annotation and adjudication (D-3)

Unchanged protocol: two Claude Sonnet annotators per item (A, B), each a new agent with its own context, at most six
articles of one language per instance, blinded to each other and to Stage 04 (no prediction exists until every round
is locked); disagreements in any scored field go to a third Sonnet instance (ADJ), whose label is final; model
metadata and transcripts kept (a missing transcript is recorded as missing); `tools/p2_labels.py lock` validates and
locks each round before the next is decided; the executor never edits a label. Labels are AI-generated by one
vendor's models, not human gold labels.

**Guide changes, made and hashed before the draw** (`ANNOTATION_GUIDE.md`, otherwise P's text):

1. Section 1 explains `same_identifier_for_work_and_notice` (section 6).
2. A record judgment **`ambiguous_object`**: the unit concerns the record's paper, but the item does not show whether
   it cites the paper or its notice; `cannot_tell` stays for a unit whose paper itself is in doubt. Example 5 shows
   the failed campaign's pattern synthetically (a "Withdrawal:" reference whose record gives one DOI for work and
   notice).

Justification: D-076 section 10 requires the packet to distinguish the cited work, the cited notice or withdrawal, the
same work with an ambiguous publication object, and an unrelated record; P's judgments had no value for the third.
The change is stricter for the engine, never more lenient (8.2). Label format `citerift-stage04-eval-labels/2`.
The briefs are P's, with the P2 tool names.

## 8. Metrics (per language unless stated)

Sections 8.1 to 8.7 are P's definitions, with one P2 change in 8.2.

### 8.1 Engine units

Positive unit: a unit with a claim of `RETRACTED_WORK_CITED`, `CONCERN_CITED`, `CORRECTION_CITED` or
`REINSTATED_WORK_CITED` (D-068). Negative unit: a `NOT_FOUND_IN_CHECKED_SOURCES` claim and no positive claim.

### 8.2 Primary metric: attachment precision (D-068)

A positive claim is correct when `kind = work_citation`, `same_work ≠ no`, and among the records its keys reach as
original at least one is judged `cited_work` and none `unrelated`, `cited_notice` or (**P2**) `ambiguous_object`. A
positive unit is correct when every positive claim is. Unannotated, unverifiable (`cannot_tell` only) and
ambiguous-object positives count as incorrect and are reported separately. Precision with the exact two-sided 95 %
Clopper–Pearson interval; false-attachment rate with its exact one-sided 95 % upper bound `u`,
`P(Bin(n, u) ≤ x) = 0.05` (unchanged method).

### 8.3, 8.4 Per class and secondary

Per class with n > 0: n, correct, incorrect, exact interval; n = 0 reported; no per-class minimum. Secondary
(optional, never replacing 8.2): RETRACTED + CONCERN units.

### 8.5 Negatives and recall (descriptive)

Negative denominator, truth positives among negatives, exact misses (H4), **retrieval-scoped recall** and
**identifier-reached recall**, each with its interval. Recall is descriptive, never pass/fail.

### 8.6 Hazards and structural violations (must be 0)

H1 notice as attachment, H2 marker as attachment, H3 identity conflict as attachment, H4 exact miss; S1 investigation
not completed/verified/exported, S2 forbidden phrase (frozen S-7.7 list), S3 positive without evidence. As in P.

### 8.7 Identity conflicts (D-067)

Exhaustive and descriptive, as in P: every `IDENTITY_CONFLICT` unit and every `same_work = no` unit, with its label,
abstention, justification, `single_identifier_attachable` and conversion to a positive; no population rate.

### 8.8 dt-2 role-collision abstentions (new; descriptive only)

Every unit with no positive claim and an `UNRESOLVED_IDENTITY` claim giving reason `IDENTIFIER_ROLE_COLLISION`, per
language: the number of such units; how many are annotated; among the annotated, the fractions (exact intervals) whose
final `kind` is `work_citation`, `notice_citation`, `cannot_tell` or another kind, the fraction that is a truth
positive, and the fraction with a record judged `ambiguous_object`; and the number with an **independently clean cited
identifier**: a key of the unit that is the original-paper identifier of at least one record and the notice
identifier of none (plain SQL on the index). Each case is listed. These abstentions are never converted into positives
during scoring and have no pass/fail.

### 8.9 Recall withheld (new; descriptive)

Every truth-positive unit without a correct engine attachment, by cause: `role_collision` (the unit's claims include
the 8.8 abstention), `other_abstention` (another `UNRESOLVED_*`, `IDENTITY_CONFLICT`, `CONTRADICTION_IN_SOURCES` or
`LOOKUP_UNAVAILABLE` claim), `other_class` (for example `NOT_FOUND_IN_CHECKED_SOURCES`, `NOTICE_CITED`),
`positive_but_incorrect`, `no_claim`. A withheld true positive is never counted as a correct attachment.

## 9. The one prediction run (corrected runner)

`tools/p2_run.py`, derived from the corrective cycle's corrected runner, after every round is locked and committed:

- refuses when `run/RUN.json` exists (one prediction run; nothing is re-run after it, whatever the scores);
- checks the pinned engine identity (`engine_check`, section 1), the P2 manifest file hashes, the seed's `P2`, and the
  locked packet hashes;
- probes the engine its article subprocesses import (`python -I`): this repository's `src`, version 0.3.0;
- takes the Investigation Memory root as `--memory-root`: absolute, **outside the repository and any working tree from
  the start**, accepted by the engine's own `check_memory_root`, created `0700` when absent and never `chmod`-ed;
  recorded only under `operational` in `RUN.json` (a locator, outside every scientific record, score and digest);
- creates and validates the export parent `run/exports` (a real directory, not a symbolic link) **before the first
  article**;
- runs per article the production command line only (`run`, `resume` at most three times, `verify`, `export` after a
  passed verify) and writes `RUN.json` once.

The two defects of the historical tool (memory root inside the repository; no export parent, so the first article had
no export) are each proven unable to recur by `tests/stage04/test_p2_evaluation.py` (section 16). The scorer takes the
memory root as an operational argument too.

## 10. Failure criteria (gate 04-I, per language; unchanged)

| Gate | Criterion |
|---|---|
| G1 | positive units ≥ **30** |
| G2 | one-sided 95 % upper bound of the false-attachment rate ≤ **0.10** |
| G3 | hazards H1 to H4 = 0 |
| G4 | structural violations S1 to S3 = 0 |
| G5 | negative units ≥ **60** |

The evaluation passes only when all five hold in both languages. A short G1 or G5 after the ceiling or the end of the
planned positions is a failed gate, never a weakened one. No gate, threshold or interval method differs from P.

## 11. Baseline and sensitivity variants (D-069)

Evaluation-only tooling outside `src/`, never imported by production code. Naive baseline (`tools/p2_baseline.py`):
unchanged from P (an eligible cited identifier equal to any original or notice identifier of a record). Sensitivity
variants (`tools/p2_sensitivity.py`), from the retained Investigation Memory, read-only, with the frozen dt-2 functions
called as they are and no new lookup: (a) `identifier_link` excluded; (b) rule D-6 removed from the frozen dt-2 table
(the dt-2 role-collision guard in D-10 stays); (c) `labeled_reference_text` included, with `NOT_COMPUTABLE` for a
DOI–PMID pair query the investigation did not retain (counted, never approximated). Faithfulness self-checks first: dt-2
`decide` on the retained inputs must reproduce every committed claim class, and NORMALIZE on the committed extraction
must reproduce the committed candidate inputs byte for byte; otherwise the article's variants are not computed. No
variant disables or approximates the role-collision guard; P2 adds no variant.

**Development self-check on dt-2** (`tools/p2_dev.py`, result `dev/DEV_RUN.json`; development evidence only, no
labels read, offline with every socket refused: 0 network attempts). The set is P's rule applied at the current
commit: one bundle per (wiki, revision) of every capture bundle tracked in git. That gives **312 revisions**: P's 232
development revisions plus the 80 articles of the failed campaign, which D-071 and D-076 made design-exposed (manifest
v2) and which are excluded from the P2 frame. Their labels and scores are not read.

| | 312 revisions |
|---|---|
| lifecycle | 308 `COMPLETED`, 3 `NEEDS_RESOLUTION`, 1 `FAILED` (`en-1380218630`, failed the same way in P's run) |
| faithfulness self-checks passed / unfaithful | **311 / 0** (the failed run has no retained evidence) |
| engine positive units (frozen dt-2) | 97 (19 on P's 232, 78 on the 80 campaign articles) |
| baseline flagged units | 131 (by engine class: 81 `RETRACTED_WORK_CITED`, 22 `NOTICE_CITED`, 11 `CORRECTION_CITED`, 5 `CONCERN_CITED`, 5 `UNRESOLVED_IDENTITY`, 3 `IDENTITY_CONFLICT`, 3 `UNRESOLVED_IDENTIFIER`, 1 `UNRESOLVED_STATUS`) |
| variant (a), `identifier_link` excluded | 9,514 candidates, 0 `NOT_COMPUTABLE`, 96 positive units; 76 units change (71 `NOT_FOUND` → no identifier, 1 `RETRACTED_WORK_CITED` → no identifier, 4 `UNRESOLVED_IDENTIFIER` changes) |
| variant (b), D-6 removed (guard kept) | 9,534 candidates, 0 `NOT_COMPUTABLE`, 97 positive units; 3 units `IDENTITY_CONFLICT` → `UNRESOLVED_IDENTITY` |
| variant (c), `labeled_reference_text` included | 9,534 candidates, **4 `NOT_COMPUTABLE`** (all on campaign articles; counted, never approximated), 97 positive units; 14 units gain a candidate |

All three variants are faithfully computable on dt-2 and stay in P2; none is declared `NOT_COMPUTABLE` as a whole. On
P's 232 revisions dt-2 differs from P's dt-1 run (`evaluation/dev/DEV_RUN.json`, 20 positive units) in one revision
only (`en-1382450117`, one positive unit fewer). These numbers are not precision, recall or a performance result.

The new holdout is never used to tune a variant.

## 12. Reporting

`SCORES.json` (format `citerift-stage04-eval-scores/2`, with the engine identity) and a Step 14 report: every number
of section 8 per language (and pooled where stated) with its interval, the gates, the baseline and variants scored
the same way with `NOT_COMPUTABLE` counts, the D-067 case list, the 8.8 role-collision cases, the 8.9 withheld counts,
the acquisition log, annotation agreement and every protocol deviation, whatever the results.

## 13. Limitations (declared before the draw)

**dt-2 design choices (D-071 to D-075).** dt-2 deliberately prefers abstention where an identifier's roles collide.
These are limitations and design choices of the engine, not results of P2:

1. On the pinned snapshot, 1,472 of the 31,506 DOI+PMID pairs that dt-1 made positive become `UNRESOLVED_IDENTITY`
   under the strict rule (D-072); the declined lenient alternative would have made 800 unresolved. Their recall cost
   is a limitation, never a performance result.
2. All 53 same-work sibling cases of reviewer finding C-01 (including `ar-3351802 un-00059`) remain
   `UNRESOLVED_IDENTITY`; no sibling exemption exists (D-073).
3. A clean original DOI can still support D-14 beside the same record's notice PMID (D-075); 628 measured B-03 pairs of
   the snapshot remain positive under dt-2.
4. A role-collided, unavailable or absent original DOI is never rescued by a notice PMID (D-075).
5. A citation whose only identifier is given by the checked sources as both an original and a notice is
   `UNRESOLVED_IDENTITY`, even when the work is truly retracted (D-071).

**Carried from P.** Truth is retrieval-scoped (recall is an upper bound within the routes of section 6); labels are
AI-generated single-vendor labels; the sample is stratified and unbalanced, so no prevalence is estimated; articles are
captured at their current revision; exposure is article-level (manifest v2) and listed-only pages stay (D-070); the
snapshot is pinned; variant (c) can leave units `NOT_COMPUTABLE`. Performance (D-061) is NOT_MET (D-066).

## 14. Deviations from the historical P

1. Engine: freeze-2 (`28ba646`, dt-2, 0.3.0) instead of `b5bf8ed` (dt-1, 0.2.0), with a full identity check
   (`engine_check`) instead of a tree comparison only.
2. Exposure: manifest v2 (378 articles) instead of the Step 12 manifest (298); frames 139 and 645 instead of 180 and
   687; exclusion audit and no-overlap proof added to `FRAME.json` (format `/2`).
3. Runner: the corrected runner (memory outside the repository, export parent first, subprocess engine probe with the
   pinned version, `RUN.json` refused) instead of the historical tool; the scorer takes the memory root as an
   argument.
4. Packets: `same_identifier_for_work_and_notice` (format `/2`).
5. Guide and labels: record judgment `ambiguous_object` (labels format `/2`); scoring treats it as not correct (8.2).
6. Metrics: 8.8 (role-collision abstentions) and 8.9 (recall withheld) added, descriptive.
7. Seed and order tags `/2`; a new drand round after the owner's acceptance of P2.
8. Sensitivity variants run on dt-2 (variant (b) keeps the dt-2 role-collision guard).
9. Limitations: the dt-2 section of 13.

Unchanged: frame source and strata, listed-tier treatment, allocation, reserves, expansion rule and targets, attempt
ceiling, acquisition outcomes, replacement, item set, annotation protocol, adjudication, lock, gates, interval method,
hazards, structural violations, D-067 and D-068 metrics, baseline.

## 15. Owner decisions required by accepting P2

Accepting P2 by its digest accepts, in particular:

1. the frame of 3.4 (exposure v2, listed-only tier kept): ar 110 / 29, en 346 / 299;
2. the unchanged allocation, expansion targets and gates (sections 5, 10);
3. the guide change of section 7 and its scoring in 8.2 (`ambiguous_object` never correct);
4. the descriptive metrics 8.8 and 8.9 and their definitions (including "independently clean cited identifier");
5. the deviations of section 14;
6. that the owner's acceptance message fixes the seed round (4.2). Nothing is drawn before it.

## 16. Files and checks

`PREREGISTRATION_MANIFEST.json` lists every file with its SHA-256. Tools (`tools/`): `p2_common.py`, `p2_frame.py`,
`p2_draw.py`, `p2_acquire.py`, `p2_packets.py`, `p2_labels.py`, `p2_run.py`, `p2_score.py`, `p2_baseline.py`,
`p2_sensitivity.py`, `p2_dev.py`, `p2_manifest.py`. Tests: `tests/stage04/test_p2_evaluation.py` (engine identity and
every mismatch, exposure pin, historical P and campaign unchanged, frame rebuild and independent no-overlap proof,
counts and audit, capture-time recheck, new tags, packets and labels, scorer and gates, role-collision and withheld
metrics, the corrected runner and both historical defects, the dt-2 development run, the manifest rebuild).
