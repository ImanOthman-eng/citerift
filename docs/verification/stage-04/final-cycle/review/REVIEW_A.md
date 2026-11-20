# Review A: scientific semantics and bibliographic identity (final corrective cycle, D-083 item 10)

Reviewer A (independent; did not write the change). Focus: the bib-1 specification, its implementation, the reference
model, adversarial behaviour, the dt-3 invariants and the evidence model.

## Scope read

- `docs/verification/stage-04/final-cycle/review/REVIEW_BRIEF.md`, `BIBLIOGRAPHIC_SPEC.md` (all sections),
  `ROOT_CAUSE_AND_ARCHITECTURE.md` sections 1 and 2, `BUILD_VS_ADOPT.md` (profile row and line 59).
- `src/citerift/investigation/bibliographic.py` (all), `data/bib-profile-1.json`, `dt1.py` (rule table, `decide`,
  `comparisons`, `bib_conflicts`), `adapters/normalize.py`, `adapters/lookup.py`, `adapters/detector.py`,
  `adapters/plan.py` (engine identity), `adapters/verify.py` (replays), `fold.py` (E-07 guard),
  `schemas/investigation/v1/lookup-observation.schema.json` (`records`).
- `simulations/stage04/bib_reference.py` (all), `bib-reference-profile.json`, `dt3_reference.py` (guards).
- `tests/stage04/test_final_bib.py`, `final-cycle/corpus/BIB_CORPUS.json`, `final-cycle/fail-first/*.json`,
  `final-cycle/scripts/survey_pairs.py`, `final-cycle/regression/regress.py` (header only).
- Not read: any label, adjudication, `LOCK.json` or `SCORES.json` (F-08).

## Method

- Line-by-line comparison of production against the spec and the reference.
- Commands (no network, no full suite):
  - `uv run pytest tests/stage04/test_final_bib.py -q -p no:cacheprovider` → `124 passed in 3.84s`.
  - Alias profiles compared as sets and as ordered lists, per wiki and CS1 key: identical.
  - A differential fuzz of `cited_object` (3,003 random templates with markup, `{{!}}`, comments, combining marks,
    Arabic, script prefixes): `divergences 0 raised 0 of 3003`.
  - 50 hand-built adversarial probes run through both production and reference
    (scratch script `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/revA/probe.py`).
    Production and reference agree on every probe. The verdicts are quoted below.
  - Pinned Stage 02 index (read-only): 20,000 random pairs of *different* records, each pair compared with bib-1's own
    relations, to measure how discriminating the title and author rules are.
  - Stage 03 extraction of the P2 bundle `en-27958530` (source artifact only; no label), with `cited_object` run on
    every `citation_template` unit span.
- [V] marks a fact verified by reading code or by command output. [I] marks an inference.

## Answers to the five questions (summary)

1. **Spec soundness.** P1, P2 and P4 hold [V]. P3 holds [V] (finding A-10). P5 holds for year and periodical [V]. The
   relations are threshold-free, but the rule is general mainly through the author relation. The title side rests on
   a closed lexicon, and DISJOINT is rarely reached (A-02). The known-limits section leaves out the most likely
   residual paths, on both the safety side and the recall side (A-02, A-06).
2. **Implementation equals the spec and the reference.** It does, with one robustness gap (A-07) [V]. No semantic
   divergence was found (A-11).
3. **Adversarial.** The Garry item and its single-field variants are blocked [V]. Variants that still give COMPATIBLE,
   and therefore a positive, exist: A-01 (markup merges words) and A-02 (no or spuriously agreeing authors with a
   designation outside the lexicon). The coverage table is below.
4. **"bib-1 can only remove a positive", and dt-2 equivalence.** Both are true at the level of decisions [V] (A-10).
5. **Evidence model.** The verdict can be reproduced from committed evidence plus the engine code, and VERIFY's
   replays recompute it [V]. The per-event verdict is never committed, and the alias profile is not part of the engine
   identity despite the claims that it is (A-03, A-09).

## Findings

### A-01 HIGH: value cleaning merges words across removed markup, so a designation word is lost

- **Evidence [V]:** spec 2.1 step 4 uses `strip_code(normalize=True, collapse=True)`, which removes templates and some
  tags without leaving a word boundary (`bibliographic.py:251-254`; reference `bib_reference.py:158-162`, same).
  Probe: record = the Hon/Ng/Leung record, no author parameter, title = record title followed by a separator and
  "Comments":

  ```
  …Biblical Time{{snd}}Comments            → '…Biblical TimeComments'  OVERLAP False COMPATIBLE
  …Biblical Time{{spaced ndash}}Comments   → '…Biblical TimeComments'  OVERLAP False COMPATIBLE
  …Biblical Time<br/>Comments              → '…Biblical TimeComments'  OVERLAP False COMPATIBLE
  …Biblical Time{{!}}Comments              → '…Biblical TimeComments'  OVERLAP False COMPATIBLE
  …Biblical Time&ndash;Comments            → CONTAINED True MATERIAL_CONFLICT   (an entity is decoded, so this works)
  'Comments on Y<ref>z</ref>'              → 'Comments on Yz'
  ```

  With `|author=Robert Garry` the author rule still blocks these. Without an author parameter, or with an agreeing
  one, the P2 item written with `{{snd}}` instead of a literal " – " is decided D-14 `RETRACTED_WORK_CITED`. That is
  a false attachment of the failure's kind, caused by cleaning rather than by the lexicon. `{{snd}}`, `{{spaced
  ndash}}` and `{{!}}` are common en-wiki separators.
- **Coverage [V]:** none of `{{!}}`, `{{snd}}`, `<br>` or `<ref>` occurs in a title in `BIB_CORPUS.json`.
- **Recommendation:** amend spec 2.1 step 4 so that each removed node (template, tag, comment) leaves one space
  (replace the nodes with " " before `strip_code`, or join node strips with a space). Apply the same change to the
  reference. Add corpus cases for `{{snd}}`, `{{!}}`, `<br/>` and `{{lang|..|title}}`, with and without an author
  parameter.

### A-02 HIGH: false compatibility of the failure's kind is still reachable, and section 9 understates it

- **Evidence [V], probes (production = reference):**

  ```
  authors-response-same   last1=Hon, "Authors' response: <T>"            a=AGREE        CONTAINED d=False COMPATIBLE
  re-colon-no-author      "Re: <T>"                                       a=INSUFFICIENT CONTAINED d=False COMPATIBLE
  letter-no-author        "Letter to the editor regarding <T>"            a=INSUFFICIENT CONTAINED d=False COMPATIBLE
  rebuttal / discussion / commentary-on / responses-plural / clarifications-plural          … COMPATIBLE
  vancouver-initials-collide  vauthors=Smith NG  ("ng" = record surname Ng) a=AGREE  COMPATIBLE
  given-name-collide      author=Robert Kam  ("kam" = given name of Kam L E Hon)  a=AGREE  COMPATIBLE
  al-particle             Ahmed Al-Saud vs Fahad Al Harbi                 a=AGREE  COMPATIBLE
  other-paper-no-authors-funcword  a different paper sharing only "of"    OVERLAP  COMPATIBLE
  ```

- **Measurement on the pinned index [V]** (20,000 random pairs of different records; scratch command, not committed):
  - title relation: DISJOINT 5,746 and OVERLAP 14,254. A wrong-object title is DISJOINT in only about 29 % of pairs.
  - author verdict with full author lists: AGREE 2,112 (10.6 %).
  - one full-name commenter against a random record: AGREE 813 (4.1 %). The most common shared words are li, wang,
    zhang, liu, chen, yang, yu and wei.
  - 571 records have a lexicon word in their own title.
- **Inference [I]:** the general protection is the author relation. The title lexicon is a second line, and DISJOINT
  rarely fires on Latin titles. A comment, reply, letter or editorial that carries the original's DOI is still
  attached in two cases:
  - when its citation has no author parameter (2 of 243 development pairs had authors INSUFFICIENT), or when one of
    its author words occurs anywhere in the record's author list (given names, particles al/de/van, 2-letter
    Vancouver initials, common surnames);
  - **and** its title designation is outside DW ("Re:", "Authors' response", "Response:", "Responses to", "Rebuttal",
    "Rejoinder", "Discussion", "Commentary", "Letter", "Editorial", "Withdrawn:"), or is lost by A-01.
- Section 9 states only one of these paths ("whose authors agree and whose extra words are outside the lexicon"). It
  does not state author-absent citations, spurious agreement through given names, particles or initials, or the
  low reach of DISJOINT. The owner's constraint names "editorial" explicitly, yet by design no editorial is
  recognized by title.
- **Classification note:** read literally, the brief puts "can still produce a false positive attachment of the
  failure's kind" at CRITICAL. I classify this HIGH for three reasons: the exact P2 item and both of its single-field
  variants are blocked; the residual needs two coincident conditions; and any closed, threshold-free lexicon leaves
  some residual, which the fixed constraints accept. The owner should confirm this reading.
- **Recommendation:**
  - (a) Rewrite section 9 to state each path above, with the measured rates.
  - (b) Inflect the lexicon uniformly (A-05). Consider "response", "rejoinder" and "rebuttal", which come from the
    same NLM Comment/reply source and are not genres.
  - (c) Consider not counting cited author words of length 2 that come from a Vancouver initials token, and not
    counting record given names as matches for a cited surname-only value. Both are threshold-free.
  - (d) Add corpus cases for the author-absent related object and the spurious-AGREE related object, with expected
    verdicts that show the residual openly.

### A-03 MEDIUM: the alias profile is not part of the engine identity, contrary to the spec and BUILD_VS_ADOPT

- **Evidence [V]:**
  - `bibliographic.profile_identity()` (`bibliographic.py:222-228`) is not called anywhere in `src/`. A grep for
    `profile_identity` finds only its definition.
  - `STAGE04_IDENTITY` (`adapters/plan.py:49-54`) holds engine, table, plan and schema versions only.
  - Spec 2.2 says "The profile file … is part of the engine identity". `BUILD_VS_ADOPT.md:59` says "the profile
    digest, part of the engine identity, would change".
  - Two other inputs that can change verdicts are not in the identity either: the parser version (pinned only by
    `pyproject.toml:10` / `uv.lock`) and `unicodedata.unidata_version`. `requires-python = ">=3.12,<3.14"` allows
    Unicode 15.0 or 15.1, and `fold`/`words` depend on it (reference R8 notes this).
- **Effect [I]:** a profile edit without a version bump changes verdicts with an unchanged identity. The result is a
  replay mismatch instead of STALE.
- **Recommendation:** put `profile_identity()` together with the profile's SHA-256 (and the parser version and
  `unidata_version`) into the Stage 04 identity, or correct both sentences.

### A-04 LOW: designation is evaluated only on the best-ranked title value

- **Evidence [V]:** `bibliographic.py:366-386`; spec 4.2 ("Only a chosen value … can designate").
  - Probe `trans-title-equal-masks` (`title=Comentarios: <T> |trans-title=<T>`) gives EQUAL and COMPATIBLE.
  - Probe `title-equal-chapter-erratum` (`title=<T> |chapter=Erratum`) gives EQUAL and COMPATIBLE.

  This is unlike section 5's "a single decisive conflict suffices (fail closed)" [I].
- **Recommendation:** state it in section 9, or let any CONTAINED/OVERLAP value that designates give the conflict.
  Either way, add a corpus case for it.

### A-05 LOW: the lexicon's inflections are inconsistent

- **Evidence [V]:** DW (`bibliographic.py:67-99`, spec 4.2) has both numbers for comment(s), reply/replies,
  correction(s), retraction(s), addendum/addenda, corrigendum/corrigenda and erratum/errata. It has no plural for
  clarification, withdrawal or removal, nor "responses to" or "expressions of concern". Probes `responses-plural` and
  `clarifications-plural` give COMPATIBLE.
- **Inference [I]:** the plural "comments" is exactly the P2 literal, so the uneven choice reads as partly fitted to
  that item. This is not a constraint violation, because each word has a stated general source.
- **Recommendation:** state one inflection rule (singular and plural of every Crossmark and NLM term, and their
  phrase forms) and apply it uniformly.

### A-06 LOW: recall costs missing from the known limits (fail closed, but unstated)

- **Evidence [V], probes:**
  - A genuine citation of a retracted comment, reply or erratum with an inflection or synonym variant gives
    MATERIAL_CONFLICT `BIB_TITLE_RELATED_OBJECT`: record "Comment on …" cited as "Comments on …"; "Response to: …"
    cited as "Reply: …"; "Erratum: …" cited as "Errata: …". 571 snapshot records have a DW word in their own title,
    so the spec sentence "a record whose own title contains such a word … is unaffected" is too strong.
  - A Latin-script foreign-language original title without a trans-title, against an English record title, gives
    DISJOINT and an abstention (`foreign-title-genuine`), even with agreeing authors. Section 9 mentions only Arabic.
  - A title wholly wrapped in `{{lang|…}}` is removed and gives MISSING (`nested-lang-whole-noauthor`).
  - For CONTAINED, the extra words include a DW word that also occurs in T_R but outside the leftmost occurrence. The
    sentence "A word counts only outside the record's own title" is exact only for OVERLAP.
- **Recommendation:** add these to section 9 and tighten the wording of the sentence.

### A-07 LOW: production lacks the reference's exception guard on parsing

- **Evidence [V]:**
  - The reference returns `None` when `mwparserfromhell.parse` or the parameter walk raises
    (`bib_reference.py:178-200`, R1 and R2).
  - Production does not catch either (`bibliographic.py:261-281`).
  - `normalize()` catches only `NormalizeInvalid`, `SpanError` and `RetentionError` (`adapters/normalize.py`,
    `def normalize`).

  An exception would fail the whole NORMALIZE step instead of giving one unit INSUFFICIENT. No such input was found:
  the 3,003-input fuzz (deep nesting, unbalanced braces, NUL) raised nothing. Spec step 2 says nothing about it.
- **Recommendation:** wrap the parse and the parameter walk in `try/except Exception: return None`, and state it in
  spec 2.1 step 2 (B8).

### A-08 LOW: dangling references and an in-sample claim

- **Evidence [V]:**
  - Spec 2.1 step 6 cites `PERFORMANCE_AND_BOUNDS.md`, and `ROOT_CAUSE_AND_ARCHITECTURE.md` section 2 cites
    `REGRESSION.md`. Neither file exists in the repository (`find` over the repository found nothing), and
    `final-cycle/regression/` holds only `regress.py`.
  - "The recall cost of bib-1 on this development evidence is nil" rests on 243 design-exposed pairs that include P2.
  - `survey_pairs.py` parses with `str(t)` from `filter_templates(recursive=True)` and a naive `events_by`. It does not
    go through the NORMALIZE unit span or the LOOKUP path.
- **Mitigation [V]:** Stage 03 extraction of `en-27958530` gives `un-00004` span 3331–3672, and `cited_object` on
  that span gives the expected `CitedObject` (title "… – Comments", authors ("Robert Garry",)). All 6 citation-template
  units of that revision have a cited object.
- **Recommendation:** commit the two documents or remove the references. Qualify the recall claim as in-sample.

### A-09 LOW: the per-event verdict is never committed

- **Evidence [V]:**
  - `Comparison.to_json()` is never serialized (grep). A D-13a claim carries only the union of reasons
    (`dt1.py:543-546`), not which event or which field conflicted. `lookup_record` items have value null
    (`detector.py:344-353`).
  - Reproduction from committed evidence is possible with the engine code. `cited_bibliography` holds the cleaned
    fields. `records[k]` holds the record side. VERIFY's `normalize_replay` re-derives the description from source
    bytes and `detect_replay` re-derives the claims (`adapters/verify.py:286-316`).
  - `records` are trusted like `events`: VERIFY checks alignment only, and `row_sha256` cannot be checked against the
    row offline.
- **Recommendation (optional):** put the per-event comparisons in the claim itself (the claim is per unit, so there
  is no B-8 id collision). An auditor could then read the verdict without re-running code.

### A-10 INFO: the P3, B4, B5 and B7 invariants hold at the decision level

- **Evidence [V]:**
  - The D-13a guard is the D-14 guard plus `bib_conflicts`: `RULES` at `dt1.py:477-478`,
    `x.L_is("matched", VF) and bool(bib_conflicts(x.c))`. It is placed after D-1…D-13, and its only outcome is
    `UNRESOLVED_IDENTITY` with `BIBLIOGRAPHIC_OBJECT_CONFLICT` (`dt1.py:543-546`).
  - It therefore cannot create, restore or move a decision. Without a conflict the rule sequence is dt-2's.
  - `test_d13a_never_overrides_an_earlier_rule` passes. `dt3_reference.py:270-271` mirrors the guard.
- **Caveats:**
  - Equivalence holds for decisions, not artifacts. D-14 claims now also cite `lookup_record` and `cited_bibliography`
    items (`detector.py:344-353`).
  - New `ADAPTER_INCONSISTENT` paths exist for misaligned records (`detector.py:60-77`, `:348`). These are integrity
    checks.
  - `oracle-dt3/` and `test_final_oracle.py` are not present yet, so B4 and B5 are not yet shown over the whole
    decision space.

### A-11 INFO: production equals the spec and the reference

- **Evidence [V]**, each item matching the spec:
  - fold order (NFKD, then removal of Mn/Mc/Me, then casefold) and the word regex `[^\W_]+`;
  - script by the first non-decimal character, with no name giving none;
  - name words of length ≥ 2 and not decimal;
  - CONTAINED leftmost occurrence (`_contains` returns the first index);
  - OVERLAP extra words by set membership;
  - the DP phrase "in T and not in T_R";
  - a strict `<` for ties;
  - the 64 / 4,096 bounds over every value of every family;
  - a later duplicate wins, keeping the first position, with an empty later value making the field absent;
  - `showkey`;
  - the script-prefix removal.

  The et-al removal differs textually (`" "` in production, `""` in the reference). It is equivalent, because `\b`
  forces a non-word character before the match. The profiles are identical. The reference imports only the standard
  library and `mwparserfromhell` (`bib_reference.py:77-83`).
- **Limit on independence [I]:** the reference was written in the same cycle, and the spec was amended from it (R3,
  R5, R9, R15 "amended text"). It therefore checks transcription, not the choice of rule.

### A-12 INFO: Arabic

- **Evidence [V]:** Arabic-script descriptions against the all-Latin snapshot give INSUFFICIENT for both authors and
  title (`arabic-title-latin-record`), so bib-1 offers no protection there; this is stated. The Arabic DW words act
  only on mixed titles ("تعليق على <Latin title>"; corpus `arabic-designation`). The shadda is removed by fold.
  Tatweel (U+0640) and clitics are not normalized; clitics are stated.

## Adversarial coverage (item 3)

The "Corpus" column says whether `BIB_CORPUS.json` has a case for the input. "Probe" is the result of my probe and
"Effect" says what it means.

| Input | Corpus | Probe | Effect |
|---|---|---|---|
| Subtitle truncated or extended | yes | COMPATIBLE | correct |
| "et al." truncation; et al. only | yes | COMPATIBLE | correct |
| Initials only | yes | INSUFFICIENT authors | correct |
| Corporate author | yes | MATERIAL_CONFLICT | recall cost, stated |
| Transliterated name | yes | MATERIAL_CONFLICT | recall cost, stated |
| Vancouver "Hon KL, Ng PC" | yes | COMPATIBLE | correct |
| Vancouver initials colliding with a record name | no | AGREE | spurious (A-02) |
| Latin foreign-language title, no trans-title | no | MATERIAL_CONFLICT | unstated recall cost (A-06) |
| Arabic title vs Latin record | yes | INSUFFICIENT | stated |
| HTML entities | partly (`&nbsp;`) | correct | correct |
| `{{!}}`, `{{snd}}`, `<br>` inside a title | no | words merge | **A-01** |
| Nested `{{lang}}` wrapping a whole title | no | MISSING | A-06 |
| Trailing period | yes | correct | correct |
| "Retraction notice to:", "Erratum to", "Correction:" | yes | MATERIAL_CONFLICT | correct |
| "Withdrawn:" | yes | COMPATIBLE | by design (status word) |
| Reply, "response to" | yes | MATERIAL_CONFLICT | correct |
| "Re:", "Authors' response", "Responses", "Rebuttal", "Discussion", "Commentary" | no | COMPATIBLE | **A-02** |
| Related object with no author parameter and outside DW | no | COMPATIBLE | **A-02** |
| Designation masked by an EQUAL second value | no | COMPATIBLE | A-04 |
| Retracted comment cited with an inflection variant | no | MATERIAL_CONFLICT | A-06 |

## Verdict

bib-1 is implemented exactly as specified, cannot create, restore or move a positive, and blocks the P2 item and its
single-field variants. It is **not ready for a freeze**: A-01 (markup merges words), A-02 (understated residual false
compatibility of the failure's kind) and A-03 (profile missing from the engine identity) must be fixed or explicitly
accepted by the owner first.
