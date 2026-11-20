# Review G: re-verification of the review C dispositions (C-01 to C-12) at `d5cd4ba`

Reviewer G, independent; I did not write the change, its fixes or the evidence. [V] = verified by reading the cited
file or line, or by command output; [I] = inference. The brief is `REVIEW_BRIEF.md`; the dispositions under review are
`LOW_DISPOSITION.md` section 5.

## Scope

- Head `d5cd4ba` on `claude/stage04-detection-engine`. Since review C (`e3d7952`), `src` and `simulations` changed only
  in `bb7a0cf` (`bibliographic.py`, `bib_reference.py`); nothing in `src` or `simulations` changed after `bb7a0cf` [V]
  (`git diff --stat e3d7952 HEAD -- src simulations`; `git diff bb7a0cf HEAD -- src simulations` is empty).
- Read: `review/REVIEW_C.md`; `LOW_DISPOSITION.md` (all sections); `BIBLIOGRAPHIC_SPEC.md` sections 2.1, 3 and 9; the
  `e3d7952..HEAD` diffs of `bibliographic.py`, `bib_reference.py`, `test_final_bib.py`, `test_final_provenance.py`,
  `test_p2_evaluation.py`, `fc_provenance.py`, `corpus/build_corpus.py`, `BIBLIOGRAPHIC_SPEC.md` and
  `freeze-3/build_freeze_manifest.py`; `ROLE_COLLISION_STUDY.md`, `REGRESSION.md` in full; `lows/corpus_probe.py`,
  `lows/review_c_fail_first.log`, `lows/review_f_fail_first.log`; `DECISIONS.md` D-083 and D-084.
- Checked against the committed JSON: `role-collision/ROLE_COLLISION_STUDY.json`, `regression/*_REGRESSION.json`,
  `regression/census/CENSUS.json`, `lows/survey_pairs.json`, `lows/description_sizes.json`,
  `fail-first/decided_by_*.json`, `corpus/BIB_CORPUS.json`, and the provenance block of every final-cycle result.
- Not read: `LOCK.json`, adjudications, packets, `SCORES.json` or any label (F-08). I read the owner's D-083 message
  and the D-084 decision card by id (read-only) to check two attributions.

## Method

I changed no file except this one. No network; no full suite; no long tool. Probe scripts are in the session
scratchpad `review-G/` and are not committed.

- `uv run pytest tests/stage04/test_final_bib.py -q -p no:cacheprovider`: `195 passed in 6.09s`.
- `uv run pytest tests/stage04/test_final_provenance.py -q -p no:cacheprovider`: `21 passed in 0.19s`.
- Fail-first reproduction: a temporary `git worktree` of `e3d7952` under the scratchpad (removed afterwards; the
  other worktrees were left as found), then `lows/corpus_probe.py` against its `src` and against HEAD's `src` with the
  six case ids of the log header.
- `probe_g.py`: 43 hand cases (surrogates in every field family, in links, inline tags, `vauthors`, script-title
  prefixes, surrogate pairs written as two entities, decimal forms; out-of-range, zero and non-character entities;
  `&shy;`, ZWSP, ZWJ, WJ, combining marks, full-width, ligature, homoglyph; encoded key and pipe), engine against
  reference.
- `fuzz_g.py`: 4,000 seeded templates over three records (Latin real-record variant, synthetic, Arabic), inserting 0
  to 3 tokens from {surrogate entities, U+FFFD, `&shy;`, ZWSP, `&nbsp;`, combining mark, `&#0;`, `&#x110000;`,
  `&#xFFFE;`, inline and block tags, `{{snd}}`} into author and title values; engine against reference, plus the
  invariant "a surrogate entity decides as a literal U+FFFD".
- `fffd.py`: U+FFFD through `fold`, `words`, `name_words`, the initials test and `\s`, in engine and reference; an
  exhaustive scan of all non-surrogate code points for a `fold` image containing U+FFFD.
- `rebuild_corpus.py`: runs `build_corpus.main()` with `write_text` captured in memory and compares the bytes with
  the committed `BIB_CORPUS.json`.
- `refs.py`: resolves every backticked test, corpus case and path reference of `LOW_DISPOSITION.md`, and checks that
  every finding id of reviews A to F has a row with the review's severity.
- `cf_scan.py`: an approximate scan (flat `{{cite …}}` templates only) of the Stage 03 bundle artifacts for cited
  title or author values holding a format character (category Cf).

## Verified without finding

**C-01 (surrogate) holds at HEAD [V].**

- Engine `bibliographic.py:72,278-288` and reference `bib_reference.py:195-207` replace every code point in
  U+D800..U+DFFF of a non-empty cleaned family value by U+FFFD, after the whitespace collapse and strip and before the
  script-prefix removal, in the same order in both. No value is dropped any more (`_encodable` is gone); the spec text
  (`BIBLIOGRAPHIC_SPEC.md:47-51`) matches the code.
- U+FFFD is never a word character [V] (`fffd.py`): category So; `fold` leaves it unchanged (NFKD, the Mn/Mc/Me
  removal and `casefold` do not touch it); `[^\W_]`, `\w`, `\s`, `isalpha`, `isupper` and `isspace` are all false; no
  other code point folds to a string containing U+FFFD. So it can only split a word, never join or create one, and in
  engine and reference alike (`words("a�b") == ["a", "b"]` in both).
- Adversarial probes (`probe_g.py`, 43 cases): 0 engine/reference disagreements, 0 exceptions, every cited object
  serializes as UTF-8. With a commenter's name, every surrogate placement (end or middle of the surname, `|last=` with
  a decimal entity, a surrogate pair written as two entities, inside a wikilink, `''…''`, `<sub>`, `vauthors`, an
  all-caps `LI&#xD800;`) still gives `BIB_AUTHORS_DISJOINT`; a surrogate in or after the designation, in `trans-title`
  or after a `script-title` prefix still gives `BIB_TITLE_RELATED_OBJECT`. A genuine `|last=Hon&#xD800;` stays
  COMPATIBLE. A value made only of surrogates is present but has no words, which decides exactly as the absent value
  did before. Out-of-range (`&#x110000;`, `&#99999999999;`) and zero entities stay literal text or NUL and neither
  crash nor drop the description.
- Fuzz (`fuzz_g.py`, 4,000 templates): `disagreements 0`, `exceptions 0`. The "entity equals literal U+FFFD" check
  differs on 8 templates, all with the entity inside tag syntax (`<b&#xDBFF;&#xDC00;r/>`), where my textual
  substitution changes how the tag parses; the object verdict is the same in all 8, so this is a probe artefact.
- `lows/review_c_fail_first.log` is reproducible [V]: `corpus_probe.py` on the `e3d7952` worktree gives the same five
  MISMATCH lines and exit 1, and on HEAD's `src` (equal to `bb7a0cf`) the same six MATCH lines and exit 0; a `diff` of
  the case lines against the committed log is empty. The "after" section of `lows/review_f_fail_first.log` also
  reproduces on HEAD (diff empty); I did not rebuild the `7d5b936` "before" section.
- At detector level (`fail-first/decided_by_dt3_engine.json`) all 48 MATERIAL_CONFLICT corpus cases are D-13a, and
  the four new surrogate cases are D-14 under the dt-2 engine `6663314` and D-13a (or D-14 for the genuine case) under
  dt-3 [V].
- No result changed with C-01 other than provenance and timing: every number of `REGRESSION.md` sections 2 and 3
  matches the f83d20b JSON (candidates 4,614 / 4,920 / 5,190; with a description 3,859 / 4,116 / 4,551; pairs 24+1 /
  90+1+3 / 97+4+4; changed 1 / 2 / 4; new positives 0; positive units 19→18, 78→76, 86→82; lifecycles; VERIFY 231 /
  80 / 100; the seven changed claims and their per-event verdicts) [V].

**C-03 [V].** Every finding of reviews A to F has a row with the review's severity (`refs.py`: A 12, B 10, C 12, D 16,
E 13, F 5; none missing, no severity mismatch). Every test reference resolves (including
`test_normalize_replaces_a_surrogate_and_keeps_the_value`), every corpus case named exists, and every path resolves;
`bounds.json`, `fold.py` and `adapters/lookup.py` are short forms that resolve by context. Ids are prefixed `corr-`
and `S12-` in sections 1 and 2.

**C-04 [V].** The owner's D-083 message (`cmsg_…YP4QxCiKQ1Hzx2XLj9zxep`), item 5, does say "13 role-collision
abstentions; all 13 were genuine work citations", so "partly incorrect" is right. `ROLE_COLLISION_STUDY.md:18-21`
now cites that message id, says the statement comes from the scored campaign, and no argument or count uses it.

**C-05 [V].** `ROLE_COLLISION_STUDY.md:35-46` matches `CENSUS.json` (`same_record` DOI 13,681 keys / 13,700 records,
PMID 1,053 / 1,341; 13,681 / 13,724 = 99.7 %, 1,053 / 1,079 = 97.6 %; 13,724 + 1,079 = 14,803). The "4 of 18
candidates with 2 to 4 events" is exact (`ar-3351802 un-00059` 2, `ar-8312431 un-00001` 4, `en-73261569 un-00028` 3,
`un-00038` 4). The cross-record table (DOI 42/14, PMID 18/9; 13 DOIs and 1 PMID also same-record) and section 4
(1 / 4 / 13 candidates, all same-record; 17 COMPATIBLE; JASIST MATERIAL_CONFLICT with `BIB_TITLE_RELATED_OBJECT` and
authors AGREE, so "its 'Withdrawal:' title word alone" is accurate) match the JSON.

**C-06, C-09, C-11 [V].** `REGRESSION.md:96-104` states that the censuses carry no description and that the equality
holds by construction; the census provenance test checks `SAME_AS_HEAD` from the census commit (`f83d20b`) to HEAD.
The engineering-reading qualifier is in `REGRESSION.md:64-68` and in the freeze limitation
(`build_freeze_manifest.py:130-131`); "6 pairs (5 citations)" and "243 pairs" match `survey_pairs.json` (243 pairs, 9
MATERIAL_CONFLICT, less JASIST, less the two different-object claims). "6.5 s … one crafted shape, not a bound" matches
`description_sizes.json` (`cpu_s` 6.542 at 15,623 code points). The C-01 sibling case is named in section 6
(`ar-3351802 un-00059` stays D-10 in `CAMPAIGN_REGRESSION.json`). Shard times give "about 34 / 13 / 16 min" (max 2,060 s,
808 s, 990 s).

**C-07 [V].** `fc_provenance.CHECKED` and `test_final_provenance.SAME_AS_HEAD` contain `docs/verification/stage-03`;
every final-cycle result's recorded `checked_paths` contains it, with `uncommitted: []` and code commit `f83d20b`
(`19e6af0` for the study). `READS` covers the study's regression inputs and the fail-first files' corpus and detector
inputs. The other tools' file inputs (`evaluation/dev/DEV_RUN.json`, `evaluation-p2-campaign/run/RUN.json`,
`review/step7/…`, the bundles) all lie in `SAME_AS_HEAD`.

**C-08 [V].** `build_corpus.main()` relabels every case whose record is `GARRY_RECORD` (11 cases, all those built on
the real P2 record or its title) as "variant of development:en-27958530/un-00004 (real Stage 02 record, constructed
citation)", and the committed `BIB_CORPUS.json` is byte-identical to a fresh build (`rebuild_corpus.py`: `True`). The
F-01 and C-01 author paths have synthetic-record cases (`caps-surname-commenter`, `surrogate-in-author-commenter`).

**C-10 [V].** `lows/corpus_probe.py` is committed, loads the engine from the named `src`, refuses a mismatched import
and reproduces both logs (above).

## Findings

### G-01 LOW: at HEAD the disposition table still shows D-01 and D-04 as awaiting the owner, although D-084 settled them in the same commit

- **Evidence [V]:**
  - `DECISIONS.md` D-084 ("This settles final-cycle reviewer findings D-01 and D-04") and the D-084 comment in
    `tests/stage04/test_p2_evaluation.py:115-120` were committed in `19e6af0`, together with the table.
  - In the same commit `LOW_DISPOSITION.md` (blob at HEAD) gives D-01 "**Awaiting owner decision.** The test comment
    says "PENDING OWNER DECISION"…" and D-04 "**Awaiting owner decision** (with D-01)…". No "PENDING" remains in either
    test file (`grep -n PENDING tests/stage04/test_p2_evaluation.py tests/stage04/test_step13_evaluation.py`: no hit),
    so the D-01 evidence sentence is false at HEAD.
  - Row C-02 at HEAD says D-01 and D-04 "are marked 'Awaiting owner decision' … and the final report lists them". A
    final report built from it would put an answered question to the owner again.
  - At review time the working tree held an **uncommitted** edit of `LOW_DISPOSITION.md` (`git status`: ` M`) that
    changes D-01 and D-04 to "Fixed by owner decision D-084" and rewords C-02. It is not part of `d5cd4ba` and I did
    not review it as committed evidence.
  - D-084 says the files were "amended in `1b0670a`". The D-04 mutation tests of `test_p2_evaluation.py`
    (`MUTATION_PROBE`, `test_engine_check_refuses_a_different_committed_engine_tree`, 78 changed lines) came in
    `79a0023` (2026-11-20 04:29Z), before the owner's answer (07:20Z per D-084), and the D-04 row cites one of them. [I]
    The answer covers them in substance, but the record names only the first commit.
  - [I] The decision card exists (`cmsg_…MLNjt7WVEnsz4KbEmUGNxB`, question and two options as quoted); the chosen
    option is not in the card message, so I could not check the tap itself.
- **Recommendation:** commit the corrected rows (D-01, D-04: "Settled by owner decision D-084", evidence `DECISIONS.md`
  D-084, `1b0670a` and `79a0023`; drop the "PENDING OWNER DECISION" sentence) and the reworded C-02 row. Name `79a0023`
  in D-084's evidence or text only if the owner's record may be annotated; otherwise state it in the table row.

### G-02 LOW: row A-02 (HIGH) is still headed "Fixed" while its residual awaits the owner, which contradicts the C-02 disposition

- **Evidence [V]:** `LOW_DISPOSITION.md` row A-02: "**Fixed; the stated residual awaits owner acceptance.** … whether to
  accept it is the owner's call". Row C-02 at HEAD says "none is called fixed". The header defines a separate
  "Awaiting owner decision" status for exactly this case, and review C (C-02) asked that none of these be called
  "Fixed" until a D-0xx entry exists. `DECISIONS.md` has no entry accepting the A-02 residual.
- **Recommendation:** give A-02 the status "Awaiting owner acceptance (residual)", keeping the engineering description,
  and list it with E-02 and the F-02 size path among the owner decisions of the final report. D-083 item 10 ("no
  unresolved CRITICAL/HIGH/MEDIUM") is then met only after those answers, and the final report should say so.

### G-03 LOW: two freeze-3 limitations do not carry the corrected wording

- **Evidence [V]:**
  - `freeze-3/build_freeze_manifest.py:142-144`: "In a same-record collision bib-1 compares the citation with one record
    for both roles". This is the claim C-05 corrected in the study (`ROLE_COLLISION_STUDY.md:39-46`: 13,681 DOI keys
    cover 13,700 records, 1,053 PMID keys cover 1,341; 4 of the 18 development candidates have 2 to 4 events). The C-05
    disposition names only the study. It is the only remaining "one record" sentence in the final-cycle and freeze-3
    texts (grep).
  - `build_freeze_manifest.py:132-134` (A-02 residual) states only the surname-coincidence path. Spec section 9 also
    states the author-absent path ("A related note cited with no author parameter, or only with author values that
    are not comparable …, stays positive"), which review F asked for and which the A-02 row puts to the owner. The
    freeze limitations omit it.
- **Recommendation:** reword the D-072 limitation as in the study ("the lookup holds only records that describe works,
  never the notice, so the same fields stand for both roles"), and add the author-absent residual to the A-02
  limitation, before the manifest is built (no `FREEZE_MANIFEST.json` is committed yet [V]).

### G-04 LOW: an invisible format character inside a designation word hides it; with no comparable author the note stays positive

- **Evidence [V]** (`probe_g.py`, engine and reference agree; Garry record, title only):

  ```
  |title=<T> – Com&shy;ments        obj=COMPATIBLE  authors=INSUFFICIENT  title CONTAINED, designation False
  |title=<T> – Com&#x200B;ments     obj=COMPATIBLE  (ZWSP)
  |title=<T> – Comm&zwj;ents        obj=COMPATIBLE  (ZWJ)
  |title=<T> – Comm&#x2060;ents     obj=COMPATIBLE  (word joiner)
  |title=<T> – Com<U+00AD>ments     obj=COMPATIBLE  (raw soft hyphen)
  |title=<T> – Comme&#x301;nts      obj=MATERIAL_CONFLICT (a combining mark is removed by fold)
  |author=Robert Gar&shy;ry |title=<T>  obj=MATERIAL_CONFLICT (BIB_AUTHORS_DISJOINT)
  ```

  - Spec 3 `fold` removes only Mn, Mc and Me. A Cf character (soft hyphen, ZWSP, ZWJ, ZWNJ, WJ, BOM) is not a word
    character, so it splits `Comments` into `com` and `ments`, neither in the lexicon. The page renders "Comments".
  - With identifiers of a retracted work, each COMPATIBLE line is D-14 `RETRACTED_WORK_CITED`. With a commenter's name
    present the author conflict still blocks, so the P2 failure with its author is not reopened by this path.
  - The same split happens for a surrogate inside a word (`Com&#xD800;ments` gives `com`, `ments`; U+FFFD is no word
    character by design). That is malformed input in the same class.
  - Not introduced by C-01: the code path is the unchanged `fold`/`words` of spec 3, and the outcome is the same at
    `e3d7952` [I] (the title value has no surrogate).
  - It falls within the letter of the stated author-absent residual (spec 9: extra words outside the lexicon), but
    not its example ("Remarks on X" is a visible non-lexicon word; here the visible word is in the lexicon).
  - In-sample exposure: the approximate scan (`cf_scan.py`) found 0 cited title or author values with a Cf character
    in the Stage 03 bundle artifacts [V, approximate: flat templates only].
  - A Cf character in a genuine surname (`|last=Ho&shy;n`) gives CONFLICT, an abstention (recall cost, fail closed).
- **Recommendation:** either (a) remove default-ignorable code points (at least category Cf) in `fold` in both the
  engine and the reference, add corpus cases (`designation-soft-hyphen`, `designation-zero-width`,
  `surname-soft-hyphen-genuine`) with a fail-first run, and rerun the results; or (b) name the path in spec section 9
  under the author-absent residual and in the freeze A-02 limitation, so the owner's acceptance of the A-02 residual
  covers it explicitly. (a) only joins words and only ever adds a lexicon match or a surname match, but it changes
  bib-1 outputs and needs the reruns.

### G-05 LOW: C-08 left the corpus builder's docstring stale, and the C-01 title path has no synthetic-record case

- **Evidence [V]:**
  - `corpus/build_corpus.py:4-8` still says that `development:<article>/<unit>` cases copy development evidence and
    "every other case is SYNTHETIC (made-up names, titles and records, not Retraction Watch data)". The 11
    `variant of development:…` cases use the real Retraction Watch record. The JSON `label` ("SYNTHETIC unless origin
    names development evidence") is accurate.
  - Review C recommended `surrogate-in-designating-title` on a synthetic record. The corpus has the surrogate title
    case only on the Garry record (`surrogate-in-title-garry`). The C-08 row says "the F-01 and C-01 paths also have
    cases on the synthetic record", which holds for the author path only. My probe shows the synthetic title path
    works (`|title=<RT>: a re&#xD800;ply` designates, through `re` after the split).
- **Recommendation:** name the third origin class in the docstring, and add one synthetic case with a surrogate after
  a designation word in the title (for example `<RT> – Comments&#xD800;` on `REC`, expecting `BIB_TITLE_RELATED_OBJECT`).

### G-06 INFO: one engine identity covers three surrogate behaviours of the cycle

- **Evidence [V]:** engine `0.4.0`, `BIB_VERSION = "bib-1"` and `DETECTOR_IDENTITY = "citerift-dt1-detector/4 (dt-3)"`
  are unchanged from before E-01 (NORMALIZE failed), through F-02 (the value was dropped), to C-01 (U+FFFD). Every
  committed final-cycle result was rerun at `f83d20b` or later (all provenance blocks), so no committed evidence mixes
  them, and the candidate is not frozen. A memory root written by an intermediate `0.4.0` build would pass the E-07
  guard [I].
- **Recommendation:** none beyond pinning freeze-3 by commit, as planned. Do not reuse memory roots written before
  `bb7a0cf`.

### G-07 INFO: the provenance input sets are maintained by hand

- **Evidence [V]:** `READS` and `SAME_AS_HEAD` are static lists. I checked each current tool's file inputs against
  them and found none missing (section "Verified", C-07). The fail-first `.log` files are not covered by the provenance
  test, which checks JSON results only. They are reproducible with the committed probe.
- **Recommendation:** none required. A future tool that reads a new input must extend `READS`. Optionally, a test could
  require each tool to declare its inputs.

## Verdict

The C-01 fix is correct and complete for surrogates: engine and reference agree, U+FFFD never forms or joins a word,
no surrogate removes a compared value or the description, and the fail-first log reproduces. No CRITICAL, HIGH or
MEDIUM finding. The dispositions of C-03 to C-11 are accurate against the committed JSON. At `d5cd4ba` the table is
stale on D-01 and D-04 relative to D-084 (G-01; an uncommitted fix was present in the working tree) and still headed
"Fixed" for A-02 (G-02), and two freeze limitations need the corrected wording (G-03).
