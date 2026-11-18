# Corrective cycle review F: evaluation leakage and exposure accounting

Reviewer F, independent; I did not write the correction. Owner decision D-071; brief `REVIEW_BRIEF.md`. Review date
2026-11-18. Markers: **[V]** verified fact (command output or code read), **[I]** inference.

## Scope read

- `REVIEW_BRIEF.md`; `DECISIONS.md` D-071; `corrective/ROOT_CAUSE.md`; `SPECIFICATION.md` section 7.3 and 7.3a,
  `MATHEMATICAL_MODEL.md` and `RISK_ANALYSIS.md` (diff against `f207bc0`).
- Production and schema diff against `f207bc0`: `src/citerift/investigation/{dt1.py, adapters/detector.py,
  adapters/plan.py, adapters/detect.py, explanations.py, __init__.py}`, `schemas/investigation/v1/{common,claim}.schema.json`.
- Corrective tooling: `corrective/regression/regress.py`, `corrective/runner/s13_run_v2.py`, `fail_first_runner.py`,
  `corrective/census/{role_collision_census.py, pair_census.py}`, `corrective/scripts/role_collision_fixture.py`,
  `corrective/identity/logical_view_diff.py`; fixture `tests/stage04/fixtures/corrective/rw_role_collision.json`;
  tests `test_corrective_*.py` (campaign references only).
- Freeze-2: `exposure/build_exposure_manifest.py` (in full), `build_freeze_manifest.py` (limitations),
  `build_validation.py` (header and TESTS block), `d062/two_build_equivalence.py` (bundle references).
- Campaign and P (read-only): `evaluation/PREREGISTRATION_MANIFEST.json`, `evaluation/frame/FRAME.json`,
  `evaluation/dev/DEV_RUN.json`, `evaluation-campaign/{REPORT.md, DRAW.json, ACQUISITION.json, LOCK.json}`.

The working tree was moving during the review (the implementer was still editing `dt1.py`, the fixture manifest,
`build_validation.py`, and had added untracked `freeze-2/d062/` and `freeze-2/performance/`). Findings refer to the tree
as read at about 22:30Z on top of `9963908`.

## Method

1. `git diff --stat 1064113 -- docs/verification/stage-04/evaluation docs/verification/stage-04/evaluation-campaign
   tests/stage04/test_step13_evaluation.py`, `git diff --quiet 1064113 -- …` (includes the working tree),
   `git log 1064113..HEAD -- …`, `git ls-files -d`, `git status --ignored` on those paths; re-hashed the 26 files of
   `PREREGISTRATION_MANIFEST.json` and the 80 packets named in `LOCK.json`.
2. Grepped the **added** lines of `src/`, `schemas/` and `simulations/` (`git diff f207bc0 -U0 | grep '^+'`) for
   `10.1002`, `asi.23238`, `33558`, `39868218`, `un-00011`, `withdraw`, `Wiley`, `JASIST`, campaign article ids;
   grepped `src/citerift/investigation`, `schemas/investigation` and the dt-2 reference model for any DOI literal; read
   the dt-2 functions (`attached_keys`, `notice_elsewhere`, `role_collided`, `discriminating`, `role_ambiguous`).
3. Grepped every corrective script, test and freeze-2 file for reads of labels, adjudications, transcripts, scores,
   the frame and the draw (`LOCK|SCORES|labels/|ADJ|A.json|B.json|INSTANCES|frame/|en_scan|listed_tier|DRAW|SEED`);
   listed every campaign article id that appears in the corrective work.
4. Ran the exposure builder once to a scratch path, never into the repository:
   `uv run --offline python -I docs/verification/stage-04/freeze-2/exposure/build_exposure_manifest.py >
   /tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/reviewF/EXPOSURE_MANIFEST.json` (exit 0,
   55 s). Compared it with the superseded v1 manifest; checked every `en-NNNN` / `ar-NNNN` token in tracked Stage 04
   docs, tests, simulations, `src`, `DECISIONS.md` and `PROJECT_STATUS.md` (and untracked files) against its page and
   revision ids; checked every DOI written in the corrective documents, reviews, tests and census outputs against its
   `identifiers` block; applied its frame rule to the P frame (`FRAME.json`).
5. Compared the builder's stated provenance with the bytes it read (`git show 9963908:<fixture> | sha256sum` versus
   the working-tree file and the manifest's `identifiers.source_sha256`).

I did not run the test suite. Nothing was written except this file.

## Answers to the five questions (summary)

1. **Campaign and P untouched.** [V] No diff, no commit, no deletion, no new tracked or untracked file in
   `evaluation/`, `evaluation-campaign/` or `test_step13_evaluation.py` since `1064113`; P manifest and lock hashes all
   match (F-01).
2. **No item-specific knowledge in production, schemas or the reference model; the rule is general.** [V] (F-02).
3. **Exposure manifest v2** lists every Wikipedia article the design has seen that I could find (378 articles: v1's
   298 plus the 80 campaign articles; all 232 development revisions; every vertical-slice and fixture bundle), and
   applied to the P frame it removes exactly the 80 campaign articles (F-09). Its provenance stamp is wrong on a dirty
   tree (F-03, MEDIUM), its Retraction Watch `identifiers` block is incomplete and framed so that P2 could use it in
   a way that biases the evaluation (F-04, MEDIUM), and its reference scan skips `freeze-2/` (F-05, LOW).
4. **No label-driven tuning found.** [V] No corrective tool reads campaign labels, adjudications, transcripts, scores,
   the frame or the draw. The only campaign facts that fed the design are the authorized failure (`en-39868218` /
   `un-00011`, via REPORT.md and its export) and, for the runner fix, the two operational deviations of REPORT
   section 6, reproduced on a vertical-slice article, not on the campaign (F-08).
5. **No document claims evaluation evidence or precision for dt-2.** Two freeze-2 builders are not yet consistent with
   the corrected state: `build_validation.py` would attach the superseded engine's test runs to the freeze-2 candidate
   (F-06, MEDIUM), and the freeze-2 limitations describe a lenient resolution the code does not implement; RISK_ANALYSIS
   cites regression results that do not exist yet (F-07, LOW).

## Findings

### F-01 INFO: the failed campaign and the P files are unchanged

Evidence [V]:

```
$ git diff --quiet 1064113 -- docs/verification/stage-04/evaluation docs/verification/stage-04/evaluation-campaign \
    tests/stage04/test_step13_evaluation.py && echo "no diff vs 1064113 (incl. working tree)"
no diff vs 1064113 (incl. working tree)
$ git log --oneline 1064113..HEAD -- <same paths>          # (empty)
$ git ls-files -d -- <campaign and evaluation paths> | wc -l
0
re-hash: 26 files of PREREGISTRATION_MANIFEST.json; changed: []
re-hash: 80 packets of LOCK.json; changed: []
```

The only non-tracked content under these paths is the ignored `evaluation/tools/__pycache__/`, whose newest file is
17:08Z, before the D-071 record (`f207bc0`, 20:09Z), so nothing in the corrective cycle wrote there [V]. Rerun protection: `s13_run_v2.main` refuses when `run/RUN.json` exists
(`s13_run_v2.py:238`) and the historical guard refuses the corrected engine
(`test_corrective_runner.py::test_the_historical_guard_refuses_the_corrected_engine`) [V, by reading]. The campaign
regression (`regress.py`) and the end-to-end test of `en-39868218` read the bundle and run in temporary memory
outside the campaign [V, by reading `regress.py:64-110,128` and `test_corrective_role_collision.py:507-528`].

Recommendation: none. Keep the `git diff --quiet 1064113 -- …` check in the freeze-2 validation evidence.

### F-02 INFO: the correction encodes no evaluation-item knowledge; the rule is general

Evidence [V]: no added line of `src/`, `schemas/` or `simulations/` matches `10.1002`, `asi.23238`, `33558`,
`39868218`, `un-00011`, `withdraw`, `Wiley`, `JASIST` or any `en-`/`ar-` article id; `src/citerift/investigation`,
`schemas/investigation` and `dt2_reference.py` / `decision_space_dt2.py` contain no DOI literal at all. The new guard
reads only Stage 02 structure: the same-record flags `NOTICE_DOI_EQUALS_ORIGINAL` / `NOTICE_PMID_EQUALS_ORIGINAL`
(`dt1.py`, `SAME_RECORD_FLAG`), `notice_hit_count` (`detector.py`, `lookup_view`), the event's original and notice
identifiers, and which keys the candidate cites (`dt1.py`, `attached_keys` … `role_ambiguous`). It applies to both
schemes and to same- and cross-record collisions; by the census it changes the outcome of 13,724 DOI keys and 26 PMID
keys of the snapshot, not one record (`ROOT_CAUSE.md` 2.3). The campaign label of `un-00011` (`kind =
notice_citation`) would have favoured `NOTICE_CITED`; dt-2 abstains instead (`UNRESOLVED_IDENTITY`), as D-071 orders,
so the outcome is not fitted to the label. The JASIST DOI and the keys of `en-39868218` appear only in tests and the
test fixture, which is the authorized use.

Recommendation: none.

### F-03 MEDIUM: the exposure manifest v2 states a commit it was not built from when the tree is dirty

Evidence [V]: `build_exposure_manifest.py` lists files with `git ls-files` but reads their **working-tree** bytes
(`load()` reads `ROOT / path`), while it stamps `source_commit = git rev-parse HEAD` and `inputs_sha256` over
`git ls-files -s` (staged blob ids, blind to unstaged edits). Untracked files are not read at all. My scratch run:

```
manifest source_commit          996390888cffc5a5896a2ed8debe37138f297684
manifest identifiers.source_sha256  b418fe84b107…afc8
git show 9963908:tests/stage04/fixtures/corrective/rw_role_collision.json | sha256sum   9dab82cc…d245
sha256sum tests/stage04/fixtures/corrective/rw_role_collision.json (working tree)       b418fe84…afc8
```

So the manifest claims commit `9963908` but carries the hash of a fixture that is not in `9963908`. D-071 requires the
exposure manifest to be "hashed and committed"; a manifest that cannot be regenerated from the commit it names is
weak evidence for the P2 frame exclusion. The same applies to any other tracked input edited but not committed
(capture bundles, `dev_measurements.json`, campaign files, the S03 rule).

Recommendation: make the builder refuse when `git status --porcelain --untracked-files=all` is not empty for the
repository (or at least for every path it reads and the reference roots), or read every input with
`git show HEAD:<path>`; record `clean_tree: true` in the output. Regenerate the committed manifest from the freeze
commit and check that a second run is byte-identical.

### F-04 MEDIUM: the Retraction Watch `identifiers` block is incomplete, and P2 must not use it to exclude articles

Evidence [V]: `fixture_identifiers()` lists only the 21 DOIs and 12 PMIDs of the role-collision fixture and calls them
"Retraction Watch works inspected in the corrective cycle". Keys examined by name in the cycle but absent from the
block: `10.1016/j.diabet.2013.06.003` + `24076359` (ROOT_CAUSE 4a, REVIEW_A, REVIEW_B), `10.1074/jbc.274.11.7196`
(ROOT_CAUSE 4b, REVIEW_A), `10.1002/14651858.cd000018` and `10.1016/s1873-9946(10…` (REVIEW_A/B); the census outputs
name 29 (`CENSUS.json`), 1,548 (`PAIR_CENSUS.json`) and 878 (`PAIR_CENSUS_LENIENT.json`) DOIs not in the block; and the
census tools read **every** record of the snapshot (73,356 events; all 31,756 original DOI+PMID pairs). The block's
docstring leaves "whether a future frame also excludes articles citing them" to the pre-registration.

Analysis. Article-level exposure (a Wikipedia article or revision whose content the design has seen) is what can
leak into a revision-level draw: the article itself could be redrawn and scored. Record-level exposure (a Retraction
Watch record whose content the design has seen) is different [I]:

- The reference database is the same for every article; the whole snapshot was scanned in aggregate by the census, so
  "records the design has seen" is the entire snapshot. A record list cannot be made complete in any useful sense.
- Overfitting to records would matter only if the rule special-cased them; it does not (F-02): it reads the same
  structural flags for every record.
- Excluding P2 articles that cite fixture or census keys would remove exactly the role-collision citations that G3
  must test. That is a selection bias in favour of the corrected engine, the opposite of the protection exposure
  accounting is for.

So record-level exposure does not matter for a revision-level draw, except through the articles that are already
listed (the only article whose citations drove the rule, `en-39868218`, is in `S04-CAMPAIGN-80`).

Recommendation: rename the block (e.g. `rw_identifiers_examined_informational`), state in it that the census read the
whole pinned snapshot, that the list is illustrative and not complete, and that it is **not** a frame-exclusion input;
P2 should pre-commit to article-level exclusion only and give the reason above. If the block is kept as a list, add
the keys named in ROOT_CAUSE and the reviews. Consider instead a P2 reporting stratum for units that cite a
role-collided key, so that the correction's effect is measured, not hidden.

### F-05 LOW: the reference scan skips `freeze-2/`, and the superset claim over v1 is not checked by the builder

Evidence [V]: `SELF_DIR = ("docs/verification/stage-04/freeze/", "docs/verification/stage-04/freeze-2/")` excludes the
whole freeze-2 tree from the `S04-REF` scan, although `freeze-2/d062/two_build_equivalence.py:47-53` names seven
bundles (VS-1 … VS-6a) and `freeze-2/performance/` runs investigations. Today every one of them is already listed (via
`S03-BUNDLE`, `S04-DEV-232`, `S04-REF`), and every `en-`/`ar-` token in the Stage 04 docs, tests, simulations, `src`,
`DECISIONS.md` and `PROJECT_STATUS.md` resolves to a manifest page or revision id (0 unresolved) [V]. The `supersedes`
note says "every article it lists is listed here"; I checked it holds (0 v1 keys, titles or revision ids missing from
v2) [V], but the builder does not assert it.

Recommendation: exclude only `freeze-2/exposure/` (and `freeze/exposure/`) from the scan; add an assertion that every
v1 key, title and revision id is in v2.

### F-06 MEDIUM: `build_validation.py` would record the superseded engine's test runs as freeze-2 evidence

Evidence [V]: the header now reads "``VALIDATION.json`` of the freeze-2 candidate" and the output label "Stage 04
corrective cycle validation summary (freeze-2 candidate)", but `CODE_REVISION = "3eec84f6…"` is "Stage 04 Step 12:
L-04 …" (pre-correction engine 0.2.0), and `TESTS` is unchanged from Step 12 (3,249 passed, CI run 44179654515, run
number 337). `build_freeze_manifest.py:194,197` copies `code_revision`, `tests` and `performance` from that file into
the freeze manifest. [I] This is work in progress, but run as it stands it would present dt-1's test evidence as the
validation of the dt-2 freeze candidate.

Recommendation: fill `CODE_REVISION` and `TESTS` from runs of the freeze-2 code revision, or make the builder refuse
when `CODE_REVISION` is not an ancestor of HEAD that contains engine 0.3.0 / dt-2 (e.g. check
`git show <rev>:src/citerift/investigation/dt1.py` for `TABLE_VERSION = "dt-2"`).

### F-07 LOW: two freeze-2 statements do not match the corrected state

Evidence [V]:
- `build_freeze_manifest.py:86-89` (LIMITATIONS): "a clean second cited identifier naming the same event resolves a
  role collision (as dt-1 did for PMID_ROLE_COLLISION)". The implemented rule is the strict one: the second key must
  have no notice role **and** its record must give a different notice identifier in that scheme (SPEC 7.3a,
  `dt1.py` `discriminating`). The limitation describes the lenient alternative.
- `RISK_ANALYSIS.md` R4-04 residual: "the cost on exposed articles is in `corrective/regression/`"; that directory holds
  only `regress.py` (no results yet; the dev shards were still running at review time).

Neither overstates dt-2 as evaluated, but both are claims a reader of the freeze would rely on.

Recommendation: restate the limitation in the strict form (or in whatever form the owner chooses on the pending card);
commit the regression reports before the freeze, with the "development evidence only, not an evaluation" label that
`regress.py:260` already writes.

### F-08 INFO: what fed the design from the campaign

Evidence [V]: no corrective script, test or freeze-2 file reads `rounds/*/labels`, `A.json`, `B.json`, `ADJ.json`,
transcripts, `INSTANCES.json`, `SCORES.json`, `DRAW.json` or the frame (`evaluation/frame/*`). Campaign reads are:
`s13_run_v2.py` (`SEED.json` digest, `LOCK.json` packet hashes, `ARTICLES.json`) for its integrity guards;
`regress.py` (bundles, `RUN.json` class counts, historical exports via `s13_score.export_claims`, which reads engine
output only, `s13_score.py:57-68`); the exposure builder (`ACQUISITION.json`, `LOCK.json` item ids for counting,
packets and bundles for identity). The only campaign article named in corrective documents, code, tests or fixtures
is `en-39868218`; the Arabic G4 article `ar-10305362` is not named anywhere in the corrective work; the runner fix is
fail-first on the vertical-slice article `en-1381772671`, a copy in a temporary directory
(`fail_first_runner.py`). The strict/lenient change (ROOT_CAUSE 4a) came from the label-free census (692 of 886
events) and reviewer findings on Retraction Watch rows, not from campaign outcomes. ROOT_CAUSE 4b states the expected
effect "before any regression is run", and at review time no campaign regression output existed (scratch logs show
only the dev shards started at 22:27Z) [V]. ROOT_CAUSE's sentence "nothing here reads its labels" is accurate for the
tooling; the root-cause audit itself necessarily relies on the adjudicated label of `un-00011` through REPORT.md,
which is the one failure D-071 authorized [V].

[I] After D-071 the 80 articles are development data, so even label-informed changes on them would not contaminate a
fresh P2 sample; they would only make any statement about dt-2 on the campaign non-evaluative. The real P2 leakage
paths are (a) overlap of the P2 sample with exposed articles (covered by F-09), (b) inspecting the P2 frame or sample
before the freeze, and (c) choosing P2 parameters after seeing the corrected engine's output on the P2 frame. None of
the corrective tooling touches the frame.

Recommendation: state in the regression report that its campaign section must never be joined with the campaign
labels or scorer (no "post-correction G2/G3 on the campaign" figure in any document); keep the frame unread until P2
is authorized, and have P2 rebuild the frame against the v2 manifest hash.

### F-09 INFO: v2 applied to the P frame, and what P2 can exclude

Evidence [V]: v2 has 378 articles (v1's 298 plus 80; sources `S04-CAMPAIGN-80` 80, `S04-DEV-232` 232, `S04-REF` 312,
`S03-BUNDLE` 232, others as v1); all 80 campaign records carry their revision ids and extraction and packet paths,
and the `campaign` block pins `LOCK.json` (161 items) and `ACQUISITION.json`. Applying its frame rule ((wiki, page_id)
or (wiki, normalised title)) to the P frame removes exactly the 80 campaign articles: `ar` 180 → 140, `en` 687 → 647.
The 240 positions of `DRAW.json` that were drawn but never acquired (80 attempts, all acquired) were seen only as
titles in a seeded order; their content was not examined, so they are correctly not listed. Locked items are counted,
not listed; article-level exclusion subsumes them.

Recommendation: P2 should say explicitly that the 240 unacquired positions of the failed draw remain eligible, and
should check that the Arabic frame (140 after exclusion, if the frame is reused) supports the planned sample size
for G2 ≤ 0.10 before the seed is drawn.

## Verdict

No CRITICAL or HIGH leakage finding: the campaign and P are untouched, the rule carries no item-specific knowledge and
was designed from the one authorized failure plus label-free census evidence; three MEDIUM findings (F-03 manifest
provenance, F-04 identifier block and its frame use, F-06 stale validation evidence) must be fixed before the refreeze.
