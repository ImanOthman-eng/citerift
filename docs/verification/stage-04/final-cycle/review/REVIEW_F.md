# Review F: re-verification of the fixes for reviews A, B, D and E (final corrective cycle, D-083 item 10)

Reviewer F, independent; I did not write the change or the fixes. [V] = verified by reading code at the cited line or
by command output; [I] = inference.

## Scope

- Assigned head: `14fe609` on `claude/stage04-detection-engine`. The fixes are in `79a0023`, `5ded53b`, `ce5c86b` and
  `14fe609` (`git log --oneline de7dcc2..14fe609`).
- The branch moved while I reviewed. `29be044` holds the result JSON files rerun with provenance from a clean checkout
  of `14fe609`. `e892cf2` adds `PERFORMANCE_AND_BOUNDS.md`, a reworded `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2 and
  `BUILD_VS_ADOPT.md`, `lows/c07_profile.json`, `role-collision/role_collision_study.py`, and one test in
  `test_final_bib.py`. Neither commit changes `src`, `schemas` or `simulations` [V] (`git diff --stat 14fe609 HEAD`).
  - Where a status depends on `29be044` or `e892cf2`, the table says so.
  - I did not review the content of `PERFORMANCE_AND_BOUNDS.md`, `c07_profile.json` or the role-collision tool. They
    belong to the pending items.
- Read:
  - `REVIEW_BRIEF.md` and `REVIEW_A/B/D/E.md`.
  - The diffs of the four fix commits: `bibliographic.py`, `bib_reference.py`, `BIBLIOGRAPHIC_SPEC.md`,
    `detector.py`, `cli.py`, `fsutil.py`, `fold.py`, `operations.py`, the schemas, `SPECIFICATION.md`,
    `RISK_ANALYSIS.md`, the exposure builder, `fc_provenance.py` and the final-cycle tools.
  - The tests: `test_final_bib.py`, `test_final_lows.py`, `test_corrective_compat.py`, `test_final_history.py`,
    `test_final_oracle.py`, `test_final_provenance.py`, `test_p2_evaluation.py` and `test_d055.py`.
  - The evidence: `bounds/bounds.json`, `oracle-dt3/MANIFEST.json`, `simulation/decision_space_dt3_summary.json`,
    `BIB_CORPUS.json`, `lows/review_fixes_fail_first.log`, and the provenance blocks of the result files.
- Not read: `LOCK.json`, adjudications, `SCORES.json`, or any label (F-08).

## Method

I changed no file except this one. I ran no full suite, used no network, and started no long tool.

- Targeted tests:
  - `uv run pytest tests/stage04/test_final_bib.py tests/stage04/test_final_lows.py
    tests/stage04/test_corrective_compat.py tests/stage04/test_final_history.py -q -p no:cacheprovider`:
    `188 passed in 5.30s`.
  - `uv run pytest tests/stage04/test_p2_evaluation.py -k "refuses or accepts or committed_engine_tree"`:
    `15 passed, 26 deselected in 10.47s`. The test removed its temporary worktree.
  - The three cheapest tests of `test_final_oracle.py` (pin, model imports, concrete bc pair): `3 passed in 0.11s`.
  - `tests/stage04/test_schemas_step5.py`: `134 passed`.
  - `tests/stage04/test_final_provenance.py` at `e892cf2`: `13 passed in 0.15s`.
  - `uv run ruff check` on the changed production modules and tests: `All checks passed!`.
- Probes, kept in the session scratchpad (`revF/`) and not committed:
  - `probe.py`: reviewer A's 50 probes plus 22 new ones. Each runs through the production `cited_object`/`compare`
    and through the reference model. Production and reference agree on all 72.
  - `oldprobe.py` and `sub.py`: `bibliographic.py` as of `de7dcc2` (copied with `git show`) against the current
    module, on the same inputs. This is how I detected regressions.
  - `cap.py`: CPU time of `cited_object` near the new 16,384 code-point source bound.

## Status of every finding

Statuses: FIXED [V], PARTLY FIXED, NOT FIXED, or OPEN BY DESIGN (awaiting a document or evidence not yet written). An
INFO finding with no recommended action is listed once at the end.

| Id | Orig. | Status | Evidence |
|---|---|---|---|
| A-01 | HIGH | FIXED [V] | `_clean` works node by node (`bibliographic.py:267-276`); the reference does the same (`bib_reference.py` R21). Probes `Time{{snd}}Comments`, `{{spaced ndash}}`, `<br/>`, `{{!}}`, `<!-- -->` and `<ref>` all give CONTAINED with designation and MATERIAL_CONFLICT, without an author parameter. Corpus cases `markup-snd-boundary`, `markup-pipe-template-boundary`, `markup-br-boundary` and `markup-ref-content-kept` are present. Side effects in F-04. |
| A-02 | HIGH | PARTLY FIXED | Fixed [V]: (b) the lexicon now has response(s), rebuttal(s), rejoinder(s), discussion(s), commentary, editorial(s), letter(s) and `re`, and the probes `Re:`, `Authors' response`, `Rebuttal`, `Discussion`, `Commentary`, `Responses`, `Clarifications` all designate. (c) initials, particles and record given names never count; the probes `vancouver-initials-collide`, `given-name-collide` and `al-particle` now give CONFLICT. (a) section 9 states the shared-surname path (3.3 %) and multi-name `vauthors`. Measured: `lows/author_coincidence.json` (157 / 665 / 2,151 of 20,000) matches spec 4.1 [V]. **Missing:** (a) section 9 and RISK R4-04a do not state the author-absent or non-comparable-author path. Example: a related note cited with no author parameter, whose title holds the record title plus words outside the lexicon (probe `other-paper-no-authors-funcword`, or "`<T>` - remarks"), stays COMPATIBLE. Section 9 still requires that the authors "agree", and neither document gives the measured DISJOINT reach (about 29 %). (d) no corpus case shows a residual COMPATIBLE for a related object. The fix also opened a new path of this kind (F-01). |
| A-03 | MEDIUM | FIXED [V] | `PROFILE_SHA256` and `PARSER_VERSION` are checked in `profile()` (`bibliographic.py:232-243`), and a mismatch raises `EnvironmentNotPinned`. `unidata_version` is stated as unpinned, and the CI matrix is `["3.12", "3.13"]` [V]. At `14fe609`, `BUILD_VS_ADOPT.md` still said "part of the engine identity" (PARTLY). `e892cf2` rewords it and adds `test_the_profile_and_parser_pins_belong_to_engine_0_4_0` [V]. The spec's "every code change of the engine changes its version" is a policy, not enforced [I]. |
| A-04 | LOW | FIXED [V] | Every CONTAINED or OVERLAP value is checked for designation (`bibliographic.py:408-432`). "Comments on `<T>`" with `trans-title=<T>` goes from COMPATIBLE (old) to MATERIAL_CONFLICT (new). `chapter=Erratum` (DISJOINT) is stated in section 9 with a corpus case. A-04's own probe (`Comentarios:`) stays COMPATIBLE only because `comentarios` is not a lexicon word. |
| A-05 | LOW | FIXED [V] | Singular and plural of every English word; `expressions of concern`; the Arabic plurals (`bibliographic.py:74-87`, spec 4.2). |
| A-06 | LOW | FIXED [V] | Section 9 "Recall costs" states inflection and synonym variants of a retracted comment, other-language titles, `{{lang}}`-wrapped titles, and the 1,767 records with a DW word in their own title, without the old "unaffected" claim. Spec 4.2 now states the CONTAINED-versus-OVERLAP difference. |
| A-07 | LOW | FIXED [V] | `cited_object` wraps `_parsed` in `try/except Exception: return None` (`bibliographic.py:294-297`); spec 2.1 step 2 states it. There is no test that forces an exception (minor). |
| A-08 | LOW | OPEN BY DESIGN | At `e892cf2`, `REGRESSION.md` and `ROLE_COLLISION_STUDY.md` are still absent and `PERFORMANCE_AND_BOUNDS.md` is present (not reviewed here). To close: (1) commit `REGRESSION.md`, giving the claim-level effect of dt-3 on development articles without joining labels (F-08); (2) commit `ROLE_COLLISION_STUDY.md` (see B-02); (3) `PERFORMANCE_AND_BOUNDS.md` holds the 766-code-point and 14-value survey cited by spec 2.1 step 6, and per-page parse time (E-02); (4) the "recall cost nil" sentence is withdrawn or qualified as in-sample (`e892cf2` says this was done; not verified here). Every cross-reference must resolve. |
| A-09 | LOW (optional) | FIXED [V] (declined with rationale) | Spec section 9, last paragraph: per-event verdicts are not stored, and VERIFY recomputes them. |
| A-10 | INFO (caveat) | FIXED [V] | The caveat that `oracle-dt3` was absent is closed by B-01. |
| B-01 | MEDIUM | FIXED [V] | `simulations/stage04/oracle-dt3/` exists: 50,529,792 cases, 387 distinct decisions. `final-cycle/simulation/decision_space_dt3_summary.json` lists 9 properties (including `EQUIVALENCE_BC_FALSE` and `BC_ONLY_REMOVES_POSITIVES`), all at 0 violations. `test_final_oracle.py` pins the manifest digest (the pin test passed) and runs production on one representative per distinct decision with `bc` and `rc` in {False, True}. I did not run that slow test. |
| B-02 | MEDIUM | OPEN BY DESIGN | `ROLE_COLLISION_STUDY.md` is absent; the study tool is committed in `e892cf2`. To close, the document must: measure the D-072 recall cost (abstentions due to `PMID_ROLE_COLLISION` / `IDENTIFIER_ROLE_COLLISION`) on development evidence only; state each candidate resolution and whether it is proven safe against D-083 item 5 (no JASIST regression, notice/original separation kept, no ambiguous object made positive); conclude, if so, that the strict rule is kept; and give the tool's provenance. The citations in `BIBLIOGRAPHIC_SPEC.md` and `SPECIFICATION.md` must then resolve. |
| B-03 | LOW | FIXED [V] | `test_a04_bridged_events_alone_never_give_a_positive` (`ce5c86b`) uses a real Stage 02 index, production `observe` and `lookup_view`, and dt-3 `decide`. In `29be044`, `lows/a04_invariant_census.json` carries provenance (`code_commit 14fe609`, `uncommitted []`). |
| B-04 | LOW | FIXED [V] | RISK R4-04 names rule 7f as the proof, the census as its confirmation, the two clauses implied by the table, and the PAIR argument (`ce5c86b`). |
| B-05 | LOW | FIXED [V] | Section 9 (last recall bullet) and RISK R4-04a item (7) state that bridged and co-keyed records are compared, with the 7-of-81,743 measurement. |
| B-06 | LOW | FIXED [V] | `_records` refuses `title`/`journal` differing from the event (`detector.py:77-78`). The test is parametrized over both fields, and the fail-first log shows it failing on `de7dcc2`. VERIFY covers it through the DETECT replay [I]. |
| D-01 | HIGH | FIXED [V] | `test_p2_evaluation.py:115-118` now reads "PENDING OWNER DECISION … no owner answer is recorded yet". No other file claims "Amend both" as decided (grep). The owner's decision must still be recorded (D-0xx with message id) before freeze-3. |
| D-02 | MEDIUM | FIXED [V] | Same evidence as A-03. The version-tying test is in `e892cf2`. |
| D-03 | MEDIUM | FIXED [V] | `fc_provenance.start` refuses a dirty dependency set and `finish` refuses a tree that changed. `review/` is excluded, and the campaign bundles, the dt-2 regression and the step 7 generators are in `CHECKED`. Every final-cycle tool calls `start`/`finish` (grep). At `29be044`/`e892cf2`, every result has `uncommitted: []`, and `test_final_provenance.py` passes 13/13. Remaining test gap in F-03. |
| D-04 | MEDIUM | FIXED [V] | The mutations run in the P2 worktree through `MUTATION_PROBE`. Each is accepted unmutated and refused mutated, with the expected reason. The `bad_tree` case exercises the "differing" branch (15 passed). |
| D-05 | MEDIUM | FIXED [V] | `bounds.json` (`5ded53b`, rerun `29be044`): `E_max` is 50,412 B; the census adds `cited_bibliography` and `lookup_event + lookup_record`. `test_d055.py` recomputes the census and the journal from HEAD modules and asserts `uncommitted == []`. Changed claim: the maximal journal is 434,316,192 B (headroom 1.2×, down from "≥ 20×"), and `test_d055.py` was relaxed accordingly. `e892cf2` says `PERFORMANCE_AND_BOUNDS.md` reports this. |
| D-06 | LOW | FIXED [V] | `_chain_intact` runs before the E-07 guard (`fold.py:186-197, 649`). The test covers digest, prev and garbage cases; fail-first is logged. |
| D-07 | LOW | FIXED [V] | `git diff 6663314 14fe609 -- docs/verification/stage-04/review/` is empty. The dt-3 copies live in `final-cycle/bounds/`. |
| D-08 | LOW | FIXED [V] | `test_final_history.py` pins `evaluation-p2-campaign` at `2b45931`, along with P, P2, both freezes and both oracles. |
| D-09 | LOW | FIXED [V] | `SPECIFICATION.md:1077` (dt-3), `common.schema.json` `claim_class` description, and `claim.schema.json` title. |
| D-10 | LOW | FIXED [V] | Tokens are restricted to article names and use a left boundary; the LOCK read is stated precisely. No right boundary was added, which can only over-include (the safe direction). |
| D-11 | LOW | FIXED [V] | `test_both_profiles_name_the_same_module_revisions`. The reference profile already recorded `revid` and `content_sha256` at `59f2ad0`, so D-11's premise was partly inaccurate [V]. |
| D-16 | INFO (action for P3) | OPEN BY DESIGN | P3 is not authorized. Its pre-registration must record the exclusion of drawn-but-not-acquired positions as an explicit choice. |
| E-01 | MEDIUM | FIXED [V] (as recommended) | A lone surrogate now gives `C = ⊥` for the unit (`bibliographic.py:321-322`), and NORMALIZE no longer fails. Test with three entities and a fail-first log. The chosen option weakens protection (F-02). |
| E-02 | LOW | PARTLY FIXED | A pre-parse bound of 16,384 code points (`bibliographic.py:292`) is in spec 2.1 step 1. At the bound, the quadratic shape still costs 4.74 s CPU per unit (`cap.py`, n = 1,300, 15,623 code points) [V]. **Missing:** the per-page NORMALIZE parse time in the D-064 evidence (`PERFORMANCE_AND_BOUNDS.md`, not reviewed). E-02 also said such a cap needs an owner decision, and none is recorded (`DECISIONS.md` ends at D-083). See F-02. |
| E-03 | MEDIUM | FIXED [V] | `_effective_root` reads the request's `memory_root` (`cli.py:270-283`), and `fsutil` messages no longer name an ancestor (`fsutil.py:110-120`). Tests for both, fail-first logged. |
| E-04 | MEDIUM | FIXED [V] | Only absolute spellings are replaced, and only at path boundaries (`cli.py:286-310`). The test covers a hex-letter relative root and digests. |
| E-06 | INFO (action) | FIXED [V] | Echo truncated to 200 / 80 characters (`fold.py:180-182`); "nothing is written" in `cli.py` and `operations.py`. |
| E-07 | MEDIUM | PARTLY FIXED | `bounds.json` `lookup_observation_v3`: ρ = 13.0664 measured over 40 shape × text combinations of production `observe`; worst observation 224,207,881 B (0.835 of the blob limit). **Missing:** (1) the bound is a measured maximum ("no analytic bound for v3"), yet `blob_limit_proven_except_ACQUIRE_observation` is `true`. Either derive ρ analytically (copies of each stored byte × 6) or label this row measured, not proven. (2) The `adapters/lookup.py:17-20` docstring was not amended as E-07 recommended. |
| E-08 | LOW | FIXED [V] | Same evidence as D-05. |
| E-09 | LOW | FIXED [V] | `bounds.json` row "candidate inputs: bibliography increment of schema 2.0.0 (E-09)", 27,745,824 B, with the Step 8 gap stated. |
| E-10 | LOW | OPEN BY DESIGN | `dt1.py` is unchanged, so the role scan is still O(n·N) and `comparisons` still runs twice. This is the "measure and retain" route. `lows/c07_profile.json` arrived in `e892cf2` (not reviewed; see F-03 on how it was produced). To close: the document states the measured synthetic curve, the pinned-index maximum (255 / 281 events), the extrapolated cost at the D-048 budget (about 16,000 to 26,000 events), and the owner-visible choice to retain rather than optimize. |
| E-11 | LOW | FIXED [V] | `cited_object` raises `EnvironmentNotPinned` without the C tokenizer (`bibliographic.py:290-291`), with a test. Stage 03 flips `use_c` only in its worker subprocess (`wiki/worker.py:94-98`). |
| — | — | OPEN BY DESIGN | The LOW disposition table that D-083 item 10 requires is not yet written. It must list every LOW above (and F-03 to F-05) with its fixing commit or classification and evidence. |

No action was recommended for, or none is needed on: A-11, A-12, B-07 (optional, not adopted), B-08, B-09, B-10,
D-12, D-13, D-14, D-15, E-05, E-12 (optional, not adopted) and E-13.

## New findings

### F-01 HIGH: the initials rule erases an all-caps short surname, so a commenter the first draft blocked is now positive

- **Evidence [V]:**
  - Spec 3 and `_is_initials` (`bibliographic.py:125-134`) remove every whitespace token that is 1 to 3 upper-case
    letters. The author family is `AuthorList-Last` only, so `|last=LI`, `|last=WU`, `|last=NG`, `|last=LEE` or
    `|last=KIM` loses its only token. The value is then not comparable, and if every value is like that the authors
    are INSUFFICIENT.
  - `oldprobe.py`, against the Hon/Ng/Leung record (old = `de7dcc2`, new = `14fe609`):

    ```
    caps-LI              {{cite journal|last=LI|title=<T> - remarks}}                       old=MATERIAL_CONFLICT/CONFLICT  new=COMPATIBLE/INSUFFICIENT
    caps-LEE-first       {{cite journal|last=LEE|first=Min|title=<T>: a second look}}        old=MATERIAL_CONFLICT/CONFLICT  new=COMPATIBLE/INSUFFICIENT
    caps-two-commenters  |last1=WU|first1=H|last2=KIM|first2=J|title=<T>: a second look      old=MATERIAL_CONFLICT/CONFLICT  new=COMPATIBLE/INSUFFICIENT
    ```

    In the detector, the old result is D-13a (abstain) and the new one is D-14 `RETRACTED_WORK_CITED` when the
    identifiers are the original's.
  - The same commenter written `|last=Li` still gives CONFLICT (`F-caps-surname-mixed`).
  - The reference model has the same rule (R22), so the differential tests cannot see it.
  - Neither section 9 nor R4-04a states it. No corpus case has an all-caps surname. `author_coincidence.py` measures
    record pairs written in mixed case, so it does not measure this either.
- **Classification:** the brief's literal reading is CRITICAL ("can still produce a false positive attachment of the
  failure's kind"). I classify it HIGH for the reason reviewer A gave for A-02: it needs two coincident conditions
  (all-caps surnames of at most three letters, and a title designation outside the lexicon). It differs from A-02 in
  one way that matters: a fix introduced it, and the first draft blocked it. The owner should confirm the reading.
- **Recommendation:**
  - Never let the initials rule empty a value. For example, when every token of a value has the initials shape, keep
    its first token, which Vancouver and `last=` both put first. "LI" then gives `li`, "WU H" gives `wu`, and
    "HON KL" gives `hon`.
  - Or apply the rule only to the `Vauthors` and `Authors` keys, never to `last`/`author`.
  - Amend the spec and the reference alike. Add corpus cases (`last=LI`, `last=LEE|first=…`, `vauthors=WU H`) with a
    fail-first run against `14fe609`.

### F-02 MEDIUM: the E-01 and E-02 fixes turn two blocked inputs into identifier-only positives

- **Evidence [V]:** in `oldprobe.py`, the Garry item (`author=Robert Garry`, title "`<T>` – Comments") changes:

  ```
  surrogate-pages  … |pages=&#xD800;                  old=MATERIAL_CONFLICT (bib) / NORMALIZE failed closed   new=INSUFFICIENT (C = ⊥)
  long-quote       … |quote=<16,600 code points>      old=MATERIAL_CONFLICT                                   new=INSUFFICIENT (C = ⊥)
  ```

  - With `C = ⊥` the unit decides as under dt-2, so D-14 `RETRACTED_WORK_CITED`.
  - **Surrogate path.** Before the fix, the page's NORMALIZE failed and nothing was attached. Now a lone surrogate in
    any family field, even `pages`, which is never compared, discards the whole description.
  - **Size path.** Before the fix, the template parsed and the 4,096-code-point bound counted family values only, so
    a long `|quote=` or `|url=` did not matter. Now any template longer than 16,384 code points has no description.
- **Context [I]:**
  - Both inputs are unlikely in real citations (the development maximum is 5,722 code points), but both are trivially
    constructible.
  - E-01 offered "or makes that value absent" as the alternative.
  - E-02 said a pre-parse cap "is a spec change and needs an owner decision". No decision is recorded.
  - Section 9 names only the step 6 bound, not the step 1 bound, the surrogate rule or the exception rule.
  - P4 makes INSUFFICIENT non-blocking by design, so this is not an invariant break. It is a loss of protection
    introduced by the fixes.
- **Recommendation:**
  - For E-01, make only the non-encodable value absent, as E-01 offered, and keep the rest of the description. Amend
    the spec and the reference alike.
  - For E-02, put the cap and its consequence to the owner explicitly, or bound something that does not depend on
    non-family arguments.
  - In either case, state the step 1, surrogate and exception paths in section 9 as residual false-compatibility
    paths, and add corpus cases with a Garry-like item.

### F-03 LOW: `test_final_provenance.py` does not tie a result to its tool at HEAD

- **Evidence [V]:**
  - The test checks the recorded `tool_sha256` against the tool at the result's own `code_commit`.
  - `SAME_AS_HEAD` holds `src`, `schemas`, `simulations/stage04`, the support modules and the input trees. It holds
    neither the final-cycle tools nor the final-cycle modules they load. For example, `dt3_bounds.py` loads
    `final-cycle/bounds/storage_bounds.py` and `part_ceiling.py` (`dt3_bounds.py:73-78`), and every tool loads
    `fc_provenance.py`.
  - A result made stale by a later edit of its own tool therefore still passes.
  - Concrete instance: `lows/c07_profile.json` (`e892cf2`) records `code_commit ce5c86b`, with the tool SHA-256 of
    `c07_profile.py` at `ce5c86b` (`72ce7041…`). That is the version before `14fe609`, which had no `start`/`finish`
    guard. HEAD's tool hashes to `34895329…`. The test passes.
  - Here the change is only the guard, so the numbers are not affected [I]. But the result was not produced under the
    guarantee that D-03's fix states ("every tool refuses … a tree that changed during the run").
  - `bounds.json` is mitigated, because `test_d055.py` recomputes it from HEAD modules.
- **Recommendation:**
  - Assert `sha256(HEAD:<tool>) == tool_sha256`.
  - Add the final-cycle `*.py` files (excluding `review/`) to `SAME_AS_HEAD`, or record a digest of each loaded
    final-cycle module in the provenance.
  - Rerun `c07_profile.py` under the guard.
  - Optional: `index_identity` reads only the index's own `meta` rows. Record the index file's SHA-256 as well.

### F-04 LOW: the A-01 fix splits words that render joined (`<sub>`, `<sup>`, italic and bold markup)

- **Evidence [V]** (`sub.py`, old against new):

  ```
  title=Atmospheric CO<sub>2</sub>          vs "Atmospheric CO2"           old=COMPATIBLE/EQUAL  new=COMPATIBLE/OVERLAP
  title=H<sub>2</sub>O<sub>2</sub> toxicity vs "H2O2 toxicity"             old=COMPATIBLE/EQUAL  new=COMPATIBLE/OVERLAP
  title=Ca<sup>2+</sup> signalling in yeast vs "Ca2+ signalling in yeast"  old=COMPATIBLE/EQUAL  new=COMPATIBLE/OVERLAP
  title=''Bio''logy                         vs "Biology"                   old=COMPATIBLE/EQUAL  new=MATERIAL_CONFLICT/DISJOINT
  ```

  - Every Tag node is a boundary (`_INLINE` excludes `Tag`; spec 2.1 step 4). MediaWiki renders inline formatting with
    no space.
  - Chemical and mathematical titles therefore lose EQUAL. A title made only of split words becomes DISJOINT and
    abstains.
  - This is fail closed, but it is not stated, and the corpus has no `<sub>`/`<sup>` case.
- **Recommendation:**
  - Join the content of inline formatting tags (`i`, `b`, `sub`, `sup`, `span`, `small`, and the `''`/`'''` wiki
    markup) as written. Keep templates, comments, `br`, `ref` and block tags as boundaries; A-01's cases do not depend
    on the inline tags.
  - Or state the recall cost in section 9 with a corpus case.

### F-05 LOW: the lexicon word `re` also matches the prefix of every hyphenated "re-" word

- **Evidence [V]:**
  - `_WORD` splits at hyphens, so "Re-examined", "re-analysis" and "re-evaluation" yield the word `re`, which is in DW
    (spec 4.2: "`re` is the 'Re:' of an answer").
  - Probe `F-caps-surname-last` (title "Re-examined: `<T>`") gives `designation=True` from `re`.
  - A genuine citation whose title adds such a word outside the record's title abstains. This is fail closed, but it
    is not among the stated recall costs.
- **Recommendation:** state it in section 9, or count `re` only as the first word of a value. The latter is a spec
  amendment and needs a corpus case.

## Verdict

The fixes close 31 findings with verified evidence. A-02, E-02 and E-07 are only partly closed. A-08, B-02, E-10,
D-16 and the LOW disposition table remain open by design. One of the fixes opens a new path of the failure's kind
(F-01, HIGH), and two others trade a fail-closed outcome for an identifier-only positive (F-02, MEDIUM). The change is
**not ready for a freeze** until F-01 and F-02 are fixed or explicitly accepted by the owner and the open-by-design
documents are written.
