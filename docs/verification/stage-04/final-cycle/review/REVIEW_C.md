# Review C: regression evidence, evaluation leakage, role-collision study, review F fixes, LOW table, provenance

Reviewer C, independent; I did not write the change, its fixes or the evidence. [V] = verified by reading the cited
file or line, or by command output; [I] = inference. The brief is `REVIEW_BRIEF.md`.

## Scope

- Assigned head: `e3d7952` on `claude/stage04-detection-engine`. Since review F (`14fe609`), `src` and `simulations`
  changed only in `acc92d9` (`bibliographic.py`, `bib_reference.py`, the `adapters/lookup.py` docstring) [V]
  (`git diff --stat 14fe609 HEAD -- src simulations schemas`).
- Read in full:
  - `REGRESSION.md`, `regression/regress.py`, and the three `regression/*_REGRESSION.json` files (totals, every
    changed claim, every role-collision candidate, provenance);
  - `regression/census/*.json` against `../corrective/census/*.json`;
  - `ROLE_COLLISION_STUDY.md`, `role-collision/role_collision_study.py` and `ROLE_COLLISION_STUDY.json`;
  - `LOW_DISPOSITION.md`, and `REVIEW_F.md` (`REVIEW_A`, `B`, `D`, `E` for their finding ids);
  - `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2, `BIBLIOGRAPHIC_SPEC.md` sections 2.1 and 9, and
    `PERFORMANCE_AND_BOUNDS.md`;
  - `freeze-3/build_freeze_manifest.py` `LIMITATIONS`, and `freeze-3/exposure/build_exposure_manifest.py` (where it
    reads the lock);
  - `corpus/build_corpus.py` and `BIB_CORPUS.json`, `tests/stage04/test_final_provenance.py`, `fc_provenance.py`;
  - the `acc92d9` diff of `bibliographic.py` and `bib_reference.py`;
  - `DECISIONS.md` D-083.
- Not read: `LOCK.json`, adjudications, packets, `SCORES.json` or any label (F-08). I read campaign **bundles**
  (inputs) to check two engineering readings, and the Stage 02 index read-only.

## Method

I changed no file except this one. I used no network and ran no full suite or long tool.

- `uv run pytest tests/stage04/test_final_bib.py tests/stage04/test_final_provenance.py -q -p no:cacheprovider`:
  `204 passed in 4.86s`.
- Numbers: short `python3 -c` reads of each committed JSON, compared cell by cell with `REGRESSION.md`,
  `ROLE_COLLISION_STUDY.md`, ROOT_CAUSE section 2, spec section 9 and the freeze-3 `LIMITATIONS`.
- Pin check: `git rev-parse` of `dt1.py` at `28ba646`, `dfee881`, `90bc60e` and `6663314`; imports of the dt-2 blob.
- Leakage: grep of every final-cycle, freeze-3 and test tool for `LOCK`, adjudication, `SCORES`, packet, label,
  gold and truth; grep of `src` and the reference for item-specific tokens (Garry, the DOI, Virology, JASIST,
  `asi.23238`, "Biblical").
- Probes, kept in the session scratchpad `review-C/` and not committed:
  - `probe.py`: 27 hand cases on F-01, F-02, F-04 and F-05 through production `cited_object`/`compare` and through
    the reference.
  - `fuzz.py`: 4,000 seeded random templates over all-caps short tokens, surrogate entities, inline and block tags,
    designation words and hyphenated `re-`, against three records, production against reference.

## Verified without finding

- **The regression numbers match the JSON [V].** Every cell of `REGRESSION.md` section 2 matches `totals` of the
  three files:
  - candidates 4,614 / 4,920 / 5,190 and with a description 3,859 / 4,116 / 4,551;
  - D-14 pairs by object 24+1 / 90+1+3 / 97+4+4;
  - changed claims 1 / 2 / 4, `new_positive` 0, positive units 19→18, 78→76, 86→82;
  - new NOTICE_CITED and NOT_FOUND 0 / 0.
  - Every row of section 3 matches the `bib` entries, keys and units of `totals.changed`; `title_relation` gives
    the EQUAL / OVERLAP / CONTAINED wording.
  - The lifecycles (including `ar-76190003`, `en-1380218630`, `ar-8414305`, `en-60575`, `ar-7378444`) and the VERIFY
    counts equal the corrective-cycle regression and the P2 `RUN.json` revision by revision.
  - The 1 + 4 + 13 role-collision candidates and the 1,472 = 1,410 + 39 + 23 split (`PAIR_CENSUS.json`
    `transitions`) match.
  - Shard times are 2,005 s, 796 s and 972 s.
- **The method compares dt-3 against the pinned dt-2 table on the same inputs [V].**
  - `regress.py:81-97` checks the blob id twice (`rev-parse` and a SHA-1 recomputation) and `TABLE_VERSION == "dt-2"`.
  - The dt-2 blob imports only `collections.abc`, `dataclasses` and `typing`, so no HEAD helper leaks into it.
  - `to_dt2` drops only the dt-3 fields and would raise on a renamed field.
  - The cross-check is meaningful. The corrective-cycle regressions ran at `dfee881` and `90bc60e`, whose `dt1.py`
    is blob `815f0dd`, the same as `28ba646` [V]. The P2 reference is the historical run's per-article
    `claims_by_class`. Both are per revision, at class-count level. 0 mismatches over 412 revisions.
- **No rescoring, and no label in the tools [V].**
  - `regress.py` reads only `RUN.json` `claims_by_class` and the corrective `dt2_classes`. `RUN.json` also holds a
    lock digest, which is not read.
  - The only lock reader is the exposure builder (`build_exposure_manifest.py:199-205`), for item counts per article.
    It is known since D-10 and not joined with any regression output.
- **No rule comes from the P2 item [V].**
  - `src` and the reference contain no item-specific token.
  - The lexicon (`bibliographic.py:74-87`) is general: the NLM Comment type and its answering forms.
- **The review F fixes hold at HEAD [V].**
  - F-01: `|last=LI`, `|last=LEE|first=Min` and `|last1=WU|last2=KIM` give CONFLICT and MATERIAL_CONFLICT;
    `|last=NG|first=PC` and `|author=HON` agree with the record. Under the "every comparable value" rule a kept token
    can only add a comparable value, so the F-01 fix removes no block.
  - F-04: `CO<sub>2</sub>` and `''Bio''logy` are EQUAL.
  - F-05: `Re-examined:` designates, as stated.
  - F-03: `SAME_AS_HEAD` now holds `final-cycle/*.py`. The git pathspec matches subdirectories: `git ls-files` lists
    the 16 tools.
  - The engine and the reference agree on all 27 probes and on 4,000 fuzz templates (`disagreements 0`).

## Findings

### C-01 MEDIUM: F-02 is closed only for a surrogate in an uncompared field; inside a compared value it still turns a material conflict into a positive

- **Evidence [V]** (`probe.py`, engine and reference agree):

  ```
  F02 surrogate in author, Garry   |author=Robert Garry&#xD800;|title=<T>                      obj=COMPATIBLE  auth=INSUFFICIENT title=AGREE/EQUAL
  (same without the entity)        |author=Robert Garry|title=<T>                              obj=MATERIAL_CONFLICT auth=CONFLICT
  F02 surrogate in title           |title=<T> – Comments&#xD800;                               obj=INSUFFICIENT (titles=())
  (same without the entity)        |title=<T> – Comments                                       obj=MATERIAL_CONFLICT des=True
  F02 surrogate in trans-title     |title=<T>|trans-title=Comments on <T>&#xDFFF;              obj=COMPATIBLE des=False
  F02 decimal surrogate            |title=Comments on <T> &#55296;                             obj=INSUFFICIENT
  ```

  - With the Garry identifiers each of these is D-14 `RETRACTED_WORK_CITED`.
  - `bibliographic.py:330-333` (and `bib_reference.py:195-210`) drop the whole value that holds the surrogate, so
    every word of it is lost, including the commenter's surname and the designation.
  - At `de7dcc2` such a page failed NORMALIZE (fail closed). At `14fe609` it had no description. Now only the
    damaged value is dropped. This is narrower, but a single entity in the author or title still gives an
    identifier-only positive.
  - Spec 2.1 step 4 (`BIBLIOGRAPHIC_SPEC.md:47-50`) states that the value is absent. The residual list of section 9
    (`:287-293`) names the step 1, step 6 and parser-exception paths but not this one, as F-02 asked.
  - `LOW_DISPOSITION.md:85` says "Fixed for the surrogate path".
  - The corpus case `lone-surrogate-entity` has a surrogate in a non-designating title, so it does not show the loss
    of a block.
- **Classification:** under the brief's literal wording, "a false positive attachment of the failure's kind" is
  CRITICAL. I classify it MEDIUM, because:
  - bib-1 never observes the conflict: the value is absent by spec, which is P4's non-blocking INSUFFICIENT;
  - the input is an invalid numeric character reference. MediaWiki does not render it as a character [I]; it shows
    it as U+FFFD or as literal text, so the words around it stay visible to a reader.
  - The owner should confirm the reading.
- **Recommendation:**
  - In both the engine and the reference, replace each lone surrogate code point of a cleaned value by U+FFFD (or
    remove only that code point) instead of discarding the value. The words around it then survive and the value is
    valid UTF-8 for evidence.
  - Add corpus cases `surrogate-in-author-garry-like` and `surrogate-in-designating-title` (synthetic record) that
    expect MATERIAL_CONFLICT, with a fail-first run at `e3d7952`.
  - If the owner prefers the current rule, state the path in section 9 and in the freeze `LIMITATIONS`, and change
    the F-02 row to "accepted residual, owner decision".

### C-02 MEDIUM: the disposition table calls "Fixed" findings that still await an owner decision

- **Evidence [V]:**
  - `LOW_DISPOSITION.md:53` (D-01, HIGH) and `:56` (D-04, MEDIUM) say "Fixed", and in the same cell "The amendment
    itself awaits the owner".
  - `:65` (E-02) and `:85` (F-02, MEDIUM, size path) say "put to the owner" or "listed among the owner decisions of
    the final report".
  - `:38` (A-02, HIGH) says "Fixed as far as a threshold-free rule allows … Residual false compatibility is stated,
    never removed". That is an accepted residual of a HIGH finding.
  - `DECISIONS.md` ends at D-083, so no owner answer is recorded for any of them.
  - D-083 item 10 requires "no unresolved CRITICAL/HIGH/MEDIUM finding". A reader of the table would conclude that
    this is met.
- **Recommendation:**
  - Add a status "Awaiting owner decision" (or "Accepted residual, pending owner acceptance") for D-01, D-04, E-02,
    the F-02 size path and A-02's residual, and list them where the final report asks the owner.
  - Call none of them "Fixed" until a D-0xx entry with the owner's message id exists.

### C-03 LOW: disposition table, stale evidence, missing rows and colliding ids

- **Evidence [V]:**
  - Row E-01 (`LOW_DISPOSITION.md:64`) cites `test_final_bib.py::test_normalize_gives_no_cited_object_for_a_surrogate_entity`.
    That test no longer exists; it was renamed `test_normalize_makes_only_a_surrogate_value_absent`. The row also
    describes the superseded behaviour ("a surrogate entity gives no cited object").
  - The header (`:3`) says every finding is listed, but A-11, A-12, B-08, B-09, B-10, D-12, D-13, D-14 and D-15 (all
    INFO) are absent. Other INFO findings (B-07, E-05, E-12, E-13, A-10, D-16) are listed.
  - Ids collide:
    - section 1 uses the corrective-cycle A-04, D-05, E-05, E-07 and C-07, which section 3 reuses for different
      final-cycle findings;
    - section 1's C-07 (quadratic scan) and section 2's "Step 12 C-07" (path spelling) are different findings;
    - this review's C-NN ids add a third collision.
  - Every other cited test, corpus case and `lows/` file exists. I checked them by script: 14 corpus case names and
    16 test references.
- **Recommendation:**
  - Fix row E-01.
  - Add the nine INFO rows ("No action"), or reword the header.
  - Prefix the ids by cycle: `corr-A-04`, `S12-C-07`, `final-A-04`.

### C-04 LOW: the role-collision study uses a label-derived fact and attributes it to an unnamed "owner's note"

- **Evidence [V]:**
  - `ROLE_COLLISION_STUDY.md:19` and `:83` say "the 13 units of the P2 campaign that the owner's note calls genuine
    work citations".
  - The only sources in the repository are `evaluation-p2-campaign/REPORT.md:179` ("13 truth positives, all
    genuine work citations") and `HANDOFF.md` section 10 item 3. Both are outcomes of the scored campaign's labels.
    No owner message id is cited, and D-083 does not contain the statement.
  - Line 9 of the same document says that no label was read.
  - Section 4 matches the 13 regression candidates to that label-derived truth in prose. This is the join that F-08
    forbids, although nothing in the argument depends on it [I].
- **Recommendation:** delete the two clauses, or cite the exact source and mark it as label-derived context that the
  study does not use. Never present it as an owner statement without the owner's message id (CLAUDE.md).

### C-05 LOW: the "by construction" argument of the role-collision study is stated too strongly

- **Evidence [V]:**
  - `ROLE_COLLISION_STUDY.md:36` says "The lookup of such a key holds one record". This is false in general:
    - `regression/census/CENSUS.json` `same_record` has 13,681 DOI keys but 13,700 records, and 1,053 PMID keys but
      1,341 records;
    - 4 of the 18 development candidates have deciding lookups of 2 to 4 events: `ar-3351802 un-00059` (the C-01
      sibling), `ar-8312431 un-00001`, and `en-73261569 un-00028` and `un-00038`.
  - `:42-45` says "Condition 1 fails too". Under a resolve-on-COMPATIBLE rule, JASIST itself would still abstain,
    because bib-1 gives MATERIAL_CONFLICT. The argument is about fragility, which is condition 3.
  - The conclusion survives [I]. No Retraction Watch record describes the notice's own object, so any number of
    same-record events still gives bib-1 nothing that depends on the role.
  - In section 3, "bib-1 could tell the roles apart" means only that two records' works differ. The notice-role
    record describes its own retracted work, not the notice.
- **Recommendation:**
  - Reword: "the lookup holds only records that name the key in the original role and describe works, never a notice".
  - Move the JASIST sentence under condition 3.
  - Qualify the section 3 header.
  - D-072 staying strict is justified either way. The constraint puts the burden of proof on a resolution, and the
    study shows that none can be proven.

### C-06 LOW: the census reruns lack the final-cycle provenance, and their equality holds by construction

- **Evidence [V]:**
  - `regression/census/*.json` carry the corrective-cycle provenance: `engine_sources_uncommitted` over `src` and
    `schemas` only. They have no `tool`, no `tool_sha256`, no `uncommitted` list and no index `file_sha256`.
  - `test_final_provenance.py:_results` excludes them, and their own test checks only that flag and the
    `SAME_AS_HEAD` diff. So the commit message's "rerun from a clean checkout" cannot be shown from the artifacts.
  - The three census tools build `dt1.Candidate("CITED", None, …)` with no cited description
    (`corrective/census/pair_census.py:78`, `role_collision_census.py:56`, `b03_census.py:66`). With `bc` False,
    dt-3 equals dt-2 (oracle-dt3), so "each equals its dt-2 counterpart" (`REGRESSION.md:92-96`) cannot fail.
  - The test docstring says so. `REGRESSION.md` section 6 and `ROLE_COLLISION_STUDY.md` section 5 do not.
- **Recommendation:**
  - Run the census tools through `fc_provenance.start`/`finish` (for example a thin wrapper), or record their tool
    hash and the dirty-tree check.
  - In `REGRESSION.md` section 6, state that the censuses carry no description, so the equality confirms that D-10
    and the other rules are unchanged, not bib-1.

### C-07 LOW: the provenance dependency set omits the Stage 03 bundles and the result-to-result inputs

- **Evidence [V]:**
  - All 232 development bundles are under `docs/verification/stage-03/…`
    (`evaluation/dev/DEV_RUN.json`: `Counter({'docs/verification/stage-03': 232})`).
  - `fc_provenance.CHECKED` (`:24-39`) and `SAME_AS_HEAD` include no Stage 03 path. So `DEV_REGRESSION.json`,
    `survey_pairs.json` and `description_sizes.json` are not protected against a dirty or later-changed input.
  - `ROLE_COLLISION_STUDY.json` (code commit `947e4a2`) reads `regression/*_REGRESSION.json`, and
    `fail-first/*.json` reads `corpus/BIB_CORPUS.json`. `SAME_AS_HEAD` holds only `*.py` of the final cycle, so a
    later change to those JSON inputs would not be caught.
  - Mitigation: `git diff 6663314 HEAD -- docs/verification/stage-03` is empty, and the corpus and regression JSON
    files are unchanged since their consumers ran [V]. Bundle artifacts are content-addressed [I].
- **Recommendation:**
  - Add `docs/verification/stage-03/evaluation` to `CHECKED` and `SAME_AS_HEAD`.
  - Add the consumed JSON results (`regression/*_REGRESSION.json`, `corpus/BIB_CORPUS.json`), or record each input
    file's SHA-256 in the consumer's provenance and test it.

### C-08 LOW: corpus cases from the P2 item are labelled synthetic, and the F-01 and F-02 evidence rests on that one record

- **Evidence [V]:**
  - `build_corpus.py:4-8` says that every non-`development:` case is "SYNTHETIC (made-up names, titles and records,
    not Retraction Watch data)".
  - Nine cases with `origin: synthetic` use the real Retraction Watch record `GARRY_RECORD` (Hon, Ng, Leung) and the
    P2 citation's title: `garry-authors-only`, `garry-title-only`, `garry-true-original`, `true-original-vauthors`,
    `lone-surrogate-garry-pages`, and `caps-surname-only`, `-with-first`, `caps-vauthors`, `caps-surname-genuine`.
  - The corpus cases for the F-01 and F-02 fixes all sit on that single P2 record.
  - No rule is derived from the item: grep of `src` and the reference is clean, and the fixes are general rules
    [V]. But the adversarial evidence for both fixes is one record of the failing item.
- **Recommendation:**
  - Label these cases `derived:en-27958530/un-00004`.
  - Add F-01 and F-02 cases on the synthetic `REC` (for example `|last=LI` on a "Wei Li" record, and a surrogate in
    the Lindqvist author value) to show the rules are not tuned to that record.

### C-09 LOW: the engineering readings are stated as facts downstream

- **Evidence [V]:**
  - `REGRESSION.md` section 3 qualifies the reading column correctly: "not a label … not an estimate".
  - The next sentence (`:64`) states "So 2 of the 7 … block a different publication object, and 5 are abstentions on
    the retracted work itself" as a count.
  - `build_freeze_manifest.py:130` puts "6 pairs (5 citations) of the retracted work itself abstain" into the
    freeze `LIMITATIONS` without "by engineering reading".
  - Most of these items are campaign items whose adjudications the authors had already seen, so the readings'
    independence from labels cannot be shown [I].
  - I checked two readings against the bundles and the index, and both hold:
    - `ar-10305362`: the citation is Pang et al., "Induction of human neuronal cells by defined transcription
      factors", while the record of `10.1016/j.cell.2011.07.007` is Qiang et al., "Directed Conversion of
      Alzheimer's Disease Patient Skin Fibroblasts…";
    - `en-83484354`: `last4 = Gromovа` ends in U+0430.
  - Separately, `build_freeze_manifest.py:138` "up to about 5.7 s" presents one measured shape as a bound.
    Review F measured 4.74 s for another shape.
- **Recommendation:**
  - Add "(engineering reading of the citation and record; not a label; in-sample)" to the manifest limitation and
    to the count sentence.
  - Write "measured 5.7 s for one crafted shape".

### C-10 LOW: the fail-first evidence for the review F fixes is not reproducible from the repository

- **Evidence [V]:**
  - `lows/review_f_fail_first.log` line 1 names its generator as
    `/tmp/claude-0/-home-user/6e897802-…/scratchpad/fprobe.py`. That file is not committed.
  - The log is not covered by the provenance test.
- **Recommendation:** commit the probe under `final-cycle/scripts/` (it can run the corpus cases against
  `git show 7d5b936:src/citerift/investigation/bibliographic.py`), or regenerate the log with a committed tool.

### C-11 INFO: C-01 of D-083 item 11 is covered but not named

D-083 item 11 lists "C-01" among the regressions. `REGRESSION.md` names only the role-collision, B-03 and pair
censuses. C-01 is covered implicitly [V]:

- the 53 sibling pairs lie inside the unchanged pair census;
- the sibling campaign claim `ar-3351802 un-00059` stays D-10 in `CAMPAIGN_REGRESSION.json`.

A sentence in section 6 would close the item visibly.

### C-12 INFO: the F-04 fix turns some unspaced designation tags from conflict to compatible

`|title=<T><i>Comments</i>` and `|title=<small>Reply</small><T>` now join to `timeComments` and `ReplyInfluenza`,
which gives OVERLAP and COMPATIBLE. At `14fe609` they gave MATERIAL_CONFLICT [V] (`probe.py`). This follows the
rendered text, as the spec intends, and needs a malformed citation. Stating it in section 9 next to F-04 would
complete the residual list.

## Verdict

The regression evidence is accurate: it matches its JSON, compares dt-3 with the pinned dt-2 table on the same
inputs, and joins no label. D-072 staying strict is justified. **The change is not ready for freeze-3** until C-01 (a
surrogate entity inside a compared value still gives an identifier-only positive) and C-02 (findings that await the
owner are shown as "Fixed") are settled by a fix or an owner decision.
