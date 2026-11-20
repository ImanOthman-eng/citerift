# Bibliographic-object consistency layer: specification (bib-1, decision table dt-3)

Owner decision D-083 (`cmsg_018VCB51nDHP6HXmLU4ea5yPYP4QxCiKQ1Hzx2XLj9zxep`), item 3. Normative for the production
module `citerift.investigation.bibliographic` and for the independent reference model
`simulations/stage04/bib_reference.py`, which is written from this document alone and imports no production code.

## 1. Purpose and principles

A citation names a publication object twice: by identifiers (DOI, PMID) and by its own description (authors, title,
periodical, date). dt-2 decides from identifiers only. bib-1 compares the description of a citation-template unit with
the bibliographic fields of every Stage 02 record its identifiers reach and classifies the pair as **COMPATIBLE**,
**INSUFFICIENT** or **MATERIAL_CONFLICT**. dt-3 never lets a candidate whose deciding lookup reaches a record in
material conflict become a positive finding; it abstains explicitly instead (`UNRESOLVED_IDENTITY`, section 6).

Principles: (P1) no rule names a DOI, PMID, person, journal, publisher or title; (P2) no similarity score and no
fitted threshold: every relation is equality, containment, a shared word or no shared word; (P3) the layer can only
remove a positive, never create or restore one; (P4) any field that cannot be compared is INSUFFICIENT, and
INSUFFICIENT never blocks or creates anything; (P5) a field whose variation among genuine citations of one object is
documented (year, periodical) is recorded and never decisive.

## 2. Inputs

### 2.1 Cited object C (NORMALIZE)

Only units of kind `citation_template` have a cited object; every other unit has none (`C = ⊥`).

1. `text` = the unit's committed source bytes `[byte_start, byte_end)`, decoded as UTF-8 (the span NORMALIZE already
   verifies). A decoding error gives `C = ⊥`. A `text` of more than 16,384 code points gives `C = ⊥` without being
   parsed (a resource bound: the parser's time grows faster than linearly on nested markup, reviewer finding E-02;
   over the 12,501 `citation_template` units Stage 03 extracts from the 411 development revisions with a source, the
   longest has 5,722 code points and none is above the bound; `lows/description_sizes.json`).
2. Parse `text` with mwparserfromhell 0.7.2 (`mwparserfromhell.parse`). If the parsed code, ignoring whitespace-only
   text nodes, is not exactly one Template node, `C = ⊥`. Any exception raised while parsing or reading the
   template's parameters gives `C = ⊥` (B8).
3. Effective named arguments: for each parameter of that template in source order with `showkey` true, `name =
   str(param.name).strip()`; a later parameter of the same name replaces an earlier one (MediaWiki semantics).
   Positional parameters are ignored.
4. Value cleaning, node by node over the top-level nodes of `param.value`: each node's text is
   `strip_code(normalize=True, collapse=True)` of that node alone (templates and comments give nothing, tags keep their
   contents, links keep their text, HTML entities are decoded). The text of a Text node, an HTML entity, a wikilink,
   an external link or an inline formatting tag (`i`, `b`, `sub`, `sup`, `span`, `small`, `big`, `u`, `s`, `em`,
   `strong`; the italic and bold wiki markup parses as `i` and `b`) is joined to its neighbours as written, as it is
   rendered (reviewer finding F-04: `CO<sub>2</sub>` is `CO2`); the text of every other node (template, other tag,
   comment, argument, heading) is surrounded by one space on each side, so a removed or replaced node is a word
   boundary (reviewer finding A-01: `Time{{snd}}Comments` and `Time<br/>Comments` are two words, not `TimeComments`). Then
   every run of characters matching Python's `re` class `\s` (str patterns) becomes one space and the result is
   stripped with `str.strip()`. An empty result is an absent value. In a non-empty cleaned value, every lone
   surrogate code point (U+D800 to U+DFFF, which a numeric entity such as `&#xD800;` decodes to) is replaced by
   U+FFFD. The value is then Unicode text and can be committed as evidence (reviewer finding E-01), and U+FFFD is no
   word character, so the value keeps its words: a surrogate never removes a compared value or the description
   (reviewer findings F-02 and C-01).
5. Fields by parameter family, using the alias profile of the unit's wiki (section 2.2). A family's value list keeps
   the effective arguments in source order of their first occurrence:
   - `titles`: Title, ScriptTitle, TransTitle, Chapter, ScriptChapter, TransChapter. For ScriptTitle and
     ScriptChapter a leading language prefix matching `^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:` is then removed (CS1
     syntax), the rest is stripped again, and an empty rest is an absent value.
   - `authors`: AuthorList-Last, Authors, Vauthors. (AuthorList-First, editors and Collaboration are not used.)
   - `periodical`: Periodical (first value); `date`: Date (first value); `year`: Year (first value);
     `volume`, `issue`, `pages` (first value over Page and Pages together, in source order): recorded only.
   A family's values are in source order of the effective arguments, not in the order of the CS1 keys.
6. Size bound: if `titles` or `authors` has more than 64 values, or the values of all family lists of step 5 (all
   values, not only the first) have more than 4,096 code points in total, `C = ⊥` (INSUFFICIENT, never truncated,
   since a truncated description could change a verdict). Over the same 12,501 development units the largest
   description has 1,804 code points and the largest family 56 values (`lows/description_sizes.json`, from
   `scripts/description_sizes.py`; `PERFORMANCE_AND_BOUNDS.md` section 5). The value bound is therefore close to the
   development maximum: a citation listing more than 64 authors has no description and decides as under dt-2
   (section 9). The bound keeps the committed value of one unit under about 25 KiB (at most 6 bytes of canonical
   JSON per code point).

### 2.2 Parameter-alias profile (bib-profile-1)

Taken from each wiki's own CS1 configuration module (`Module:Citation/CS1/Configuration`, table `aliases`):
en revision 1384336575 (2026-11-07T20:03:20Z), ar revision 76424085 (2026-09-03T19:50:04Z); the content SHA-256 of
each revision is recorded in the profile. A `#` in an alias matches the empty string or a positive decimal integer
without leading zero (`last`, `last1`, `last12`). Names are compared exactly (MediaWiki argument names are
case-sensitive). The profile file `src/citerift/investigation/data/bib-profile-1.json` and the parser version are
pinned by the engine code (`PROFILE_SHA256`, `PARSER_VERSION`): a profile with other bytes or another parser version
is refused (the engine raises and NORMALIZE fails closed), so neither can change a verdict without a code change, and
every code change of the engine changes its version (reviewer findings A-03, D-02). The parser's C tokenizer must be
active when a unit is described (the pure-Python tokenizer can parse differently, and Stage 03 switches it in its
worker processes); otherwise the engine refuses the same way (reviewer finding E-11). `unicodedata.unidata_version` is
not pinned: Python 3.12 has Unicode 15.0 and 3.13 has 15.1; the corpus and the differential set give the same verdicts
on both (the test suite runs on both versions).

### 2.3 Record object R (LOOKUP)

For every event of a lookup observation, from the same Stage 02 event (`Index.gather_bounded`): `title` (string or
null), `authors` (string or null; Retraction Watch `;`-separated full names), `journal` (string or null),
`original_year` (integer or null). Bound to the public event by `event_id` and `row_sha256`.

## 3. Normalization

- `fold(s)`: Unicode NFKD; remove every character of general category Mn, Mc or Me; `casefold()`.
- `words(s)`: the maximal runs matching the Python regular expression `[^\W_]+` in `fold(s)` (letters and digits of
  any script), in order.
- `script(w)`: the first word of `unicodedata.name(c)` for the first character `c` of `w` that is not a decimal
  digit (`str.isdecimal()`) (for example `LATIN`, `ARABIC`, `CYRILLIC`, `GREEK`, `CJK`); a word of digits only,
  or whose character has no Unicode name, has no script.
- Name particles `NP` (folded): `al el de del della der den di da du la le van von bin ibn abu ben dos das` and the
  Arabic `بن ابن ابو`. A particle says nothing about who the person is ("Al-Saud" and "Al Harbi" share only `al`).
- Name words of an author value: in `fold(value)` remove every match of `\bet\.?\s*al\b\.?`; then the words of length
  at least 2 code points that are not digits only (`str.isdecimal()`) and not in `NP`. (Single letters are initials,
  not names.)
- Cited author name words of one cited author value: first remove every whitespace-separated token of the value that,
  once its full stops are removed and trailing commas and semicolons stripped, is one to three letters all upper case
  (`str.isalpha()` and `str.isupper()`: initials such as `KL`, `J.J.`, `S.M.,`); then the name words of the rest.
  When every token of the value has that shape, its first token is kept, so the rule never empties a value
  (reviewer finding F-01: `|last=LI` or `|vauthors=WU H` name the surname Li or Wu, which `last=` and Vancouver put
  first).
- Record surname words `S_R`: for each `;`-separated part of `R.authors`, its name words in order; without the first of
  them when there are at least two (Retraction Watch writes the given name first: "Kam L E Hon" gives `hon`), the
  single word otherwise.

## 4. Field verdicts

### 4.1 Authors

For each value `a` of `C.authors`, `N(a)` = its cited author name words. A value is *comparable* when some word of
`N(a)` has a script that some word of `S_R` has. A value that is not comparable (no name word left, or another script
than every record surname) gives no evidence and is set aside.

- **INSUFFICIENT** if no value is comparable (no cited authors, no record authors, or no common script: for example
  Arabic-script cited names against a Latin-script record);
- else **AGREE** if every comparable value shares a word with `S_R` (`N(a) ∩ S_R ≠ ∅`);
- else **CONFLICT** (some comparable cited author names no record author).

Every comparable value must name a record author (reviewer finding A-02): a commenter who shares a common surname with
one author of the work, or a co-author list of which one name happens to match, does not make the object the same;
a given name, a particle or an initial never counts. On 20,000 seeded random pairs of snapshot records with
different author strings (the author list of one cited as full names against the other), the rule of the first draft
(`59f2ad0`) agrees by accident in 2,151 pairs (10.8 %), this rule in 157 (0.8 %), and a single cited full name (one
commenter) in 665 (3.3 %), through a shared surname (`scripts/author_coincidence.py`, output
`lows/author_coincidence.json`). The cost on genuine citations is stated in section 9.

### 4.2 Title

`T_R = words(R.title)`. For each value `t` of `C.titles` with `T = words(t)` non-empty, the relation of `T` to `T_R`:

1. **EQUAL**: `T = T_R`;
2. **CONTAINED**: one sequence is a contiguous subsequence of the other;
3. **OVERLAP**: they share at least one word;
4. **DISJOINT**: they share no word and some script has a word in both;
5. **INCOMPARABLE**: otherwise.

The title relation is the best over all values in the order EQUAL > CONTAINED > OVERLAP > DISJOINT > INCOMPARABLE;
with no value or an empty `T_R` it is **MISSING**. Ties between values keep the first value in field order.

**Designation of a related object.** Only a value whose own relation is CONTAINED or OVERLAP can designate; for
every other relation designation is false. The *extra words* are: for CONTAINED with `T_R` inside `T`, the words of
`T` outside the leftmost occurrence of `T_R`; for CONTAINED with `T` inside `T_R`, none; for OVERLAP, the words of
`T` that are not in `T_R`. Such a value *designates a related object* if an extra word is in the designation
lexicon `DW`, or a phrase of `DP` occurs as consecutive words of `T` but not of `T_R`:

- `DW` (folded words), singular and plural of each notion:
  - Crossmark update types: `addendum addenda clarification clarifications correction corrections corrigendum
    corrigenda erratum errata retraction retractions withdrawal withdrawals removal removals`;
  - notes on another publication and their answers: `comment comments commentary commentaries reply replies
    response responses rejoinder rejoinders rebuttal rebuttals discussion discussions editorial editorials letter
    letters re`;
  - Arabic: `تعليق التعليق تعليقات التعليقات تعقيب التعقيب تعقيبات التعقيبات رد الرد ردود الردود تصحيح التصحيح
    تصحيحات التصحيحات استدراك الاستدراك سحب السحب افتتاحية الافتتاحية`;
- `DP`: `expression of concern`, `expressions of concern`, `تعبير عن القلق`.

Sources of the lexicon: the Crossref Crossmark update types (addendum, clarification, correction, corrigendum,
erratum, expression of concern, retraction, withdrawal, removal) name notices that update another work; the NLM
publication type *Comment* is by definition a note on another publication, and *reply*, *response*, *rejoinder* and
*rebuttal* are its answering forms (`re` is the "Re:" of an answer); *editorial*, *letter*, *commentary* and
*discussion* are the genres of note that D-083 names (a comment, reply, editorial or erratum must not be taken for the
retracted work). The Arabic words are the plain translations of the same notions. Every English word is listed in the
singular and the plural (reviewer finding A-05); Arabic words in the indefinite and the definite form and, where the
plural is a distinct word, its plural. Status words stay absent: `retracted`, `withdrawn`, `removed` describe the work
itself (publisher watermarks). A genre word of the lexicon designates only as an extra word, so a retracted editorial
or letter cited with its own title (EQUAL) is unaffected; one cited with a genre word its record title lacks
("Editorial: X" against "X") abstains (a recall cost in the safe direction, section 9). For OVERLAP a word counts only
when the record's title lacks it; for CONTAINED it counts when it lies outside the leftmost occurrence of the record's
title (so a word that the record's title also holds can still count there).

Every value of `C.titles` whose own relation is CONTAINED or OVERLAP is checked for designation, not only the chosen
value: one designating value makes the title designate (a single decisive conflict suffices, fail closed; reviewer
finding A-04). Title verdict: designation → **CONFLICT**; otherwise by the chosen relation: EQUAL → **AGREE**;
CONTAINED or OVERLAP → **COMPATIBLE**; DISJOINT → **CONFLICT**; INCOMPARABLE or MISSING → **INSUFFICIENT**.

### 4.3 Recorded, never decisive

- Year (Python `re`, so `\d` is any Unicode decimal digit): the first match of `(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)` in `C.date`, else in `C.year`; verdict
  **SAME**, **DIFFERENT** (from `R.original_year`) or **INSUFFICIENT**.
- Periodical: both word lists non-empty and equal → **SAME**; both non-empty and unequal → **DIFFERENT**; else
  **INSUFFICIENT** (abbreviated journal titles are common, so a difference proves nothing).
- Volume, issue, pages: **NOT_IN_RECORD** (Stage 02 records have none).

## 5. Object verdict

- **MATERIAL_CONFLICT** if the author verdict is CONFLICT or the title verdict is CONFLICT. Reasons:
  `BIB_AUTHORS_DISJOINT` (authors CONFLICT), `BIB_TITLE_DISJOINT` (relation DISJOINT), `BIB_TITLE_RELATED_OBJECT`
  (designation).
- **COMPATIBLE** if no conflict and (authors AGREE or title AGREE or COMPATIBLE).
- **INSUFFICIENT** otherwise, and whenever `C = ⊥` or the record has no bibliographic fields.

A single decisive conflict suffices (fail closed): for example a matching title with disjoint authors (a comment by
other authors, or a wrong identifier), or agreeing authors with a disjoint title (another paper of the same authors,
or a field holding something else).

## 6. Decision table dt-3

dt-3 is dt-2 with one rule inserted between D-13 and D-14:

- **D-13a**: the deciding lookup L is `matched` with a `verified_fact` projection (the D-14 guard) **and** some event
  of L (direct or bridged, any position) is in MATERIAL_CONFLICT with the candidate's unit → class
  **UNRESOLVED_IDENTITY** (status `uncertain`, value null), reasons `BIBLIOGRAPHIC_OBJECT_CONFLICT` plus the bib-1
  reasons of the conflicting events plus the common tail of dt-2 (`KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED`,
  `CO_REPORTED_MULTIPLE` where they hold); upstream role L (its Stage 02 basis reasons are kept as for D-10).

Precedence and its reasons:

- D-1 … D-13 keep their place: an unused or unresolved use, a missing or tainted identifier, a Stage 02 contract
  violation (D-5), an identifier incompatibility (D-6, kappa), a source contradiction (D-7), an ambiguous key (D-9),
  an unresolved identity including role collisions (D-10), an unresolved status (D-11, D-12) and an unavailable
  lookup (D-13) all decide first and keep their classes and reasons; D-13a only replaces what would otherwise be D-14.
- D-14 (positive), D-15 (notice cited), D-16 (not found) are unchanged. D-15 and D-16 are not positives and their
  lookups hold no original-role event to compare (notice/original separation: a notice is never compared with the
  work's description).
- dt-3 with no event in MATERIAL_CONFLICT decides exactly as dt-2 (equivalence property, section 8).
- UNRESOLVED_IDENTITY means "the publication object the citation names is not established"; dt-2 already uses it
  for the same situation reached through identifiers (D-10, `IDENTIFIER_ROLE_COLLISION`), and its disposition is the
  existing one. IDENTITY_CONFLICT is not used: it is defined by gate 04-D as an incompatibility between two cited
  identifiers (D-6, kappa, two identity alternatives), which a bibliographic conflict is not.
- The D-072 role-collision rule is unchanged: bib-1 never resolves a role collision (study in `ROLE_COLLISION_STUDY.md`).

## 7. Evidence

- NORMALIZE: one `cited_bibliography` item per citation-template unit with a cited object (observation: the
  extraction; pointer `/units/i`; refs: the unit item; value: `{version: "bib-1", fields}`), the same fields also in
  the unit's entry of the candidate inputs (`bibliography`, null when none).
- LOOKUP: the observation records `records`, one entry per event, `{event_id, row_sha256, title, authors, journal,
  original_year}`. DETECT refuses (`ADAPTER_INCONSISTENT`) a `records` list that is missing, not aligned with the
  events, not bound to them by `event_id` and `row_sha256`, or whose `title` or `journal` differs from its own public
  event's (reviewer finding B-06); `authors` and `original_year`, which the public event does not carry, are bound
  through `row_sha256` to the Stage 02 row.
- DETECT: for every candidate decided by D-13a or D-14, one `lookup_record` item per event of L (observation: L's
  lookup observation; pointer `/records/k`; ref: the event item; value null) and the unit's `cited_bibliography` item
  support the claim. The verdict is a pure function of these two and is recomputed by VERIFY's replay; it is not
  stored as an item value, because one record item serves every unit that reaches it while the verdict depends on
  the unit (evidence ids are `H(observation, pointer, kind)`, D-051). D-13a claims carry the bib-1 reasons.

## 8. Required properties (tested against the reference model and the oracle)

- B1 determinism: equal inputs, equal verdicts. B2 symmetry of the relation classes (EQUAL, OVERLAP, DISJOINT) under
  exchange of the two titles. B3 monotonicity: adding an author word shared with the record never turns AGREE into
  anything else. B4 P3: dt-3 never yields a positive dt-2 would not yield. B5 equivalence: with no MATERIAL_CONFLICT
  dt-3 = dt-2. B6 every D-13a claim carries `BIBLIOGRAPHIC_OBJECT_CONFLICT` and at least one bib-1 reason. B7 a
  role-collided or notice-only candidate is never changed by bib-1. B8 no input of section 2 outside its type raises;
  it yields INSUFFICIENT.

## 9. Known limits (stated, not fixed)

Free-text references and identifier-only units have no cited object (INSUFFICIENT). Abbreviated or transliterated
names that share no word with the record's names (for example "Alharbi" against "Al Harbi") give an author CONFLICT
and therefore an abstention (recall cost, fail closed). Corporate authors in an author parameter likewise. A related
object whose title contains the record's title, whose authors agree and whose extra words are outside the lexicon is
not recognized (it stays positive). Arabic-script titles are compared only with Arabic-script record titles, of which
the snapshot has none. A shared function word ("in", "of") makes two Latin titles OVERLAP, so DISJOINT is reached
only by titles with no word in common (a deliberate consequence of P2: no stop list). Arabic designation words are
matched as whole words, so a word with an attached clitic (`والرد`, `بالتصحيح`) is not recognized. A year written
wholly in Arabic-Indic digits does not match the year pattern (its first digit must be an ASCII 1 or 2), so its year
verdict is INSUFFICIENT; year is recorded only. A template above the size bound of section 2.1 step 6 has no cited
object (INSUFFICIENT, as under dt-2).

Residual false compatibility (reviewer finding A-02; the layer lowers it, it does not remove it):

- A commenter whose surname is also a surname of the work's record (a single cited full name agrees by accident in
  3.3 % of random record pairs, section 4.1), writing a note whose title holds the record's title and no word of the
  lexicon, stays positive.
- A `vauthors` value or an `authors` value lists several people in one value; the value agrees when any of its names
  is a record surname, so such lists are weaker evidence than one name per parameter. Values are not split at commas
  (splitting would also split "Surname, Given" values and cost recall on genuine citations).
- Status words (`retracted`, `withdrawn`, `removed`) are not in the lexicon, because publisher watermarks put them
  on the retracted work itself; a notice titled "Withdrawn: X" by the work's own authors is not recognized by bib-1
  (dt-2's notice/original role separation and D-15 still apply when its identifiers are the notice's).
- A value whose relation to the record title is DISJOINT never designates (section 4.2): `chapter=Erratum` beside an
  EQUAL title is COMPATIBLE (corpus case `chapter-erratum-disjoint`).
- The text inside a tag is kept by the pinned parser's `strip_code` (for example a `<ref>` inside a title), so it is
  part of the cited title (corpus case `markup-ref-content-kept`; it can only add conflicts).
- Inline formatting joins as rendered (section 2.1 step 4), so a designation word written in an inline tag with no
  space before it (`<T><i>Comments</i>`) fuses with the preceding word and is not recognized (corpus case
  `inline-designation-joined`; reviewer finding C-12).
- An invisible format character (soft hyphen `&shy;`, zero-width space, zero-width joiner, word joiner) inside a
  designation word splits it into two non-lexicon words ("Com&shy;ments"), so the designation is not recognized. A
  related note cited this way with no comparable author stays positive; with a commenter's name, the author conflict
  still blocks it (reviewer finding G-04; no such cited value was found in the development bundles).
- A related note cited with no author parameter, or only with author values that are not comparable (another
  script, initials only of no record surname), whose title holds the record's title and a designation outside the
  lexicon ("Remarks on X"), stays positive (corpus case `related-note-no-author-residual`). Title DISJOINT is reached
  only by titles with no word in common: about 29 % of the pairs of different snapshot records (reviewer finding
  A-02's measurement), so the title verdict alone rarely tells two Latin-script objects apart.
- A unit without a description is decided by its identifiers exactly as under dt-2: a template above the step 1
  bound (16,384 code points, for example with a long `quote`), above the step 6 bounds, or one the parser raises on
  (corpus case `oversized-source`; reviewer finding F-02). These are resource and well-formedness bounds; the
  development maximum is 5,722 code points, and the development maximum of one family is 56 values, against the
  bound of 64. A crafted unit just under the step 1 bound can still cost seconds of parser time (6.5 s CPU for a
  15,623-code-point nested unit, `lows/description_sizes.json`); the performance limitation is stated in
  `PERFORMANCE_AND_BOUNDS.md`.

Recall costs on genuine citations (fail closed; development evidence, never evaluation scoring):

- A title word written with a hyphenated `re-` prefix ("Re-examined", "re-analysis") gives the lexicon word `re`
  (words split at hyphens), so a citation that adds such a word to the record's title abstains (corpus case
  `re-hyphen-prefix`; reviewer finding F-05).
- A record that lists fewer authors than the citation (11,741 of 73,356 snapshot events list one author;
  `lows/author_coincidence.json`): every cited co-author absent from the record gives CONFLICT (development case
  `en-3202774`).
- A misspelled record name (Retraction Watch "Perdersen", development `en-41008786`) or a name mixing scripts (a
  Cyrillic letter inside a Latin name, development `en-83484354`) shares no surname word.
- A genre word of the lexicon added by the citation to a record title that lacks it ("Letter: X" against "X",
  development `en-21293835`), a plural or synonym in the citation's own title of a retracted comment or reply, and
  a title wrapped in a template the cleaning removes (`{{lang|…}}` gives an empty or partial title).
- A title in another language than the record's (INCOMPARABLE when the scripts differ, OVERLAP or DISJOINT when they
  share a script).
- 1,767 snapshot records hold a word of `DW` or a phrase of `DP` in their own title (the retracted work is itself a
  comment, reply, correction or letter). Cited with its own or a shortened title it is unaffected (the word is not an
  extra word); cited with words added around the title it can abstain.
- Every event of the deciding lookup is compared, bridged (`linked_via`) and co-keyed ones included: a key that
  names several objects does not establish which one the citation means, so a conflicting bridged or co-keyed record
  makes the candidate abstain even when the record of the work actually cited agrees (reviewer finding B-05). With a
  description copied from the first direct event's own record, 7 of the 81,743 single-key D-14 positives of the
  snapshot abstain: PMID `3507357` through its 254 bridged conference abstracts (which Stage 02 already does not
  count, `BRIDGED_EVIDENCE_NOT_COUNTED`), six keys through several direct records, and PMID `17381062` through a
  related-object title between two records of the same key (reviewer B's probe; the regression gives the measured
  effect on development citations, `REGRESSION.md`).

Per-event verdicts are not stored as evidence values: the verdict is a pure function of the committed description
and the committed records, and VERIFY recomputes it (section 7; reviewer finding A-09).
