# Bibliographic-object consistency layer, version 2: specification (bib-2, decision table dt-4)

Owner decisions D-086 and D-087 (`cmsg_018VCB51nDHP6HXmLU4ea5yP2PP7zzBVkR1qLdWfXovT83`, 2026-11-20), revising bib-1
(`BIBLIOGRAPHIC_SPEC.md`, kept unchanged as the specification of the candidate `c3854b8` that D-085 did not accept).
Normative for the production module `citerift.investigation.bibliographic` and for the independent reference model
`simulations/stage04/bib2_reference.py`, which is written from this document alone and imports no production code.

Changes from bib-1, each stated where it applies:

- **D-086**: a bibliographic check that cannot be performed (a resource bound, a parse or normalisation failure) is a
  state of its own, `UNAVAILABLE` with a reason, never the natural absence of a description; it blocks a positive
  (section 2.1, section 6, rule D-13b).
- **D-087, G-04**: invisible format characters (Unicode general category Cf) are read both as nothing and as a word
  boundary, and a pair must pass under both readings (section 3.1).
- **D-087, A-02**: weak compatibility is not identity. A positive needs the cited title to equal the record's title or
  to be a shortened form of it whose omitted words name no related object; a longer title, a partial overlap or a title
  that cannot be compared does not establish the object (`NOT_ESTABLISHED`, rule D-13c). Authors can only refute,
  never establish. An author value that packs several people agrees with nothing (section 4.1).

## 1. Purpose and principles

A citation names a publication object twice: by identifiers (DOI, PMID) and by its own description (authors, title,
periodical, date). bib-2 compares the description of a citation-template unit with the bibliographic fields of every
Stage 02 record its identifiers reach and classifies the pair as **COMPATIBLE**, **INSUFFICIENT**, **NOT_ESTABLISHED**
or **MATERIAL_CONFLICT**. dt-4 lets a candidate become a positive finding only if no compared pair is
NOT_ESTABLISHED or MATERIAL_CONFLICT and the unit's check was not UNAVAILABLE; otherwise it abstains explicitly
(`UNRESOLVED_IDENTITY`, section 6).

Principles: (P1) no rule names a DOI, PMID, person, journal, publisher or title; (P2) no similarity score and no
fitted threshold: every relation is equality, contiguous containment, a shared word or no shared word; (P3) the layer
can only remove a positive, never create or restore one, and dt-4 never yields a positive that dt-3 (bib-1) would not
yield (section 8, B4); (P4) a field that is naturally absent from the description or the record is INSUFFICIENT and
does not block; a description that exists but cannot be checked does block; (P5) a field whose variation among genuine
citations of one object is documented (year, periodical) is recorded and never decisive; (P6) evidence of identity
must be strong: a weaker relation, or a value that cannot be attributed to one person, never counts as agreement.

## 2. Inputs

### 2.1 Cited object C (NORMALIZE)

The result for a unit is exactly one of:

- **ABSENT**: the unit is not of kind `citation_template` (a free-text reference, an identifier-only unit). Nothing is
  described; nothing is checked.
- **UNAVAILABLE(r)**: the unit is a `citation_template` whose description could not be produced, with exactly one
  reason `r` of: `BIB_PARSE_FAILED`, `BIB_SOURCE_LIMIT_EXCEEDED`, `BIB_VALUE_LIMIT_EXCEEDED`,
  `BIB_DESCRIPTION_LIMIT_EXCEEDED`.
- **DESCRIBED(C)**: the unit's description `C`, whose fields may all be empty (a template with no title and no author
  parameter describes nothing: natural absence, not a failure).

Steps, for a `citation_template` unit, in this order (the first that applies decides):

1. `text` = the unit's committed source bytes `[byte_start, byte_end)`, decoded as UTF-8. A decoding error, or a span
   that cannot be read, gives `UNAVAILABLE(BIB_PARSE_FAILED)`.
2. A `text` of more than 16,384 code points gives `UNAVAILABLE(BIB_SOURCE_LIMIT_EXCEEDED)` without being parsed (the
   parser's time grows faster than linearly on nested markup; development maximum 5,722 code points,
   `lows/description_sizes.json`).
3. Parse `text` with mwparserfromhell 0.7.2 (`mwparserfromhell.parse`). If the parsed code, ignoring top-level Text
   nodes whose value is empty after `str.strip()`, is not exactly one Template node, or if any exception is raised while
   parsing, reading the template's parameters or cleaning a value (step 5), the result is
   `UNAVAILABLE(BIB_PARSE_FAILED)`.
4. Effective named arguments: for each parameter of that template in source order with `showkey` true, `name =
   str(param.name).strip()`; a later parameter of the same name replaces an earlier one (its name keeps the position of
   its first occurrence). Positional parameters are ignored.
5. Value cleaning, unchanged from bib-1 (section 2.1 step 4 of `BIBLIOGRAPHIC_SPEC.md`): node by node over the
   top-level nodes of `param.value`, each node's text is `strip_code(normalize=True, collapse=True)` of that node alone;
   the text of a Text node, an HTML entity, a wikilink, an external link or an inline formatting tag (`i`, `b`, `sub`,
   `sup`, `span`, `small`, `big`, `u`, `s`, `em`, `strong`) is joined to its neighbours as written; the text of every
   other node is surrounded by one space on each side. Then every run of Python `re` `\s` (str patterns) becomes one
   space and the result is stripped with `str.strip()`. An empty result is an absent value. In a non-empty value every
   lone surrogate (U+D800 to U+DFFF) is replaced by U+FFFD. Format characters (category Cf) are kept here; section 3.1
   reads them.
6. Fields by parameter family (alias profile, section 2.2). Each family's values are in source order of the effective
   arguments (first occurrence of the name):
   - `titles`: Title, ScriptTitle, TransTitle, Chapter, ScriptChapter, TransChapter. For ScriptTitle and
     ScriptChapter a leading language prefix matching `^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:` is removed, the rest stripped
     again, and an empty rest is an absent value.
   - Authors, now kept by form: `authors` (key AuthorList-Last: one person per parameter, as CS1 intends),
     `author_lists` (key Authors: a free-form list) and `vauthors` (key Vauthors: a Vancouver list).
   - `periodical`, `date`, `year`, `volume`, `issue`, `pages` (Page and Pages together): first value; recorded only.
7. Bounds (never truncated, since a truncated description could change a verdict): if `titles` has more than 64
   values, or `authors`, `author_lists` and `vauthors` together have more than 64 values, the result is
   `UNAVAILABLE(BIB_VALUE_LIMIT_EXCEEDED)`; otherwise, if all values of all families of step 6 together have more than
   4,096 code points, `UNAVAILABLE(BIB_DESCRIPTION_LIMIT_EXCEEDED)`. Development maxima over 12,501 units: 56 values in
   one family, 1,804 code points (`lows/description_sizes.json`).
8. Otherwise `DESCRIBED(C)`.

An unknown wiki (not in the profile) is not a property of the unit but of the engine's configuration: the engine
refuses to run (as for a profile with other bytes, section 2.2). Stage 03 supports `ar` and `en` only.

### 2.2 Parameter-alias profile (bib-profile-1)

Unchanged from bib-1: `src/citerift/investigation/data/bib-profile-1.json` (SHA-256 `450f17a2…`), from each wiki's
`Module:Citation/CS1/Configuration` (en revision 1384336575, ar revision 76424085); `#` matches the empty string or a
positive decimal integer without leading zero; names are compared exactly. The profile bytes, the parser version and
the parser's C tokenizer are pinned by the engine, which refuses otherwise.

### 2.3 Record object R (LOOKUP)

Unchanged: for every event of a lookup observation, from the same Stage 02 event: `title`, `authors`
(`;`-separated full names, given name first), `journal`, `original_year`; bound by `event_id` and `row_sha256`.

## 3. Normalization

### 3.1 Readings of format characters (G-04)

A *format character* is a code point of Unicode general category Cf (for example U+00AD soft hyphen, U+200B zero-width
space, U+200C zero-width non-joiner, U+200D zero-width joiner, U+2060 word joiner, U+FEFF byte-order mark, the
bidirectional controls). A format character is invisible: "Com&shy;ments" renders as "Comments". It is ambiguous
whether it separates two words or sits inside one, so every comparison of section 4 and 5 is made under two readings:

- the **split reading** uses every string as it is (a format character is no word character, so it separates words;
  this is exactly bib-1's reading);
- the **joined reading** first removes every format character from every compared string (the cited title values, the
  cited author values of all three forms, the record's title and authors).

When no compared string holds a format character the two readings are identical and the comparison is made once. When
some string holds one, the pair's result is the worse of the two readings in the order MATERIAL_CONFLICT >
NOT_ESTABLISHED > INSUFFICIENT > COMPATIBLE; the reported field verdicts are those of the reading that gives it (the
split reading when both give it), and the reasons are the union of the reasons of every reading that gives it. So a
designation hidden by a format character is found (joined reading), and a format character can never make a pair pass
that bib-1 would have refused (split reading). Periodical and year are read from the reported reading.

### 3.2 Words

Unchanged from bib-1: `fold(s)` = Unicode NFKD, removal of categories Mn, Mc, Me, then `casefold()`; `words(s)` = the
maximal runs of `[^\W_]+` in `fold(s)`; `script(w)` = the first word of the Unicode name of the first non-decimal
character of `w` (none for digits only or an unnamed character); name particles `NP` (`al el de del della der den di da
du la le van von bin ibn abu ben dos das` and `بن ابن ابو`); name words of a string = in `fold(s)` remove every match of
`\bet\.?\s*al\b\.?`, then the words of at least 2 code points that are not digits only and not in `NP`; cited name
words of a string = remove the whitespace tokens that are initials (one to three upper-case letters once full stops are
removed and trailing commas and semicolons stripped; when every token is initials the first is kept), then name words;
record surname words `S_R` = for each `;`-separated part of `R.authors`, its name words without the first when there
are at least two.

## 4. Field verdicts

### 4.1 Authors (A-02: a packed value agrees with nothing)

The cited author values are split into **parts**, each either a *person* (one name) or a *packed* part (possibly
several names that cannot be told apart). A *list separator* is `;` or the Arabic semicolon `؛`; a *comma* is `,` or
the Arabic comma `،`; a *conjunction* is `&` or a whitespace token that casefolds to `and`.

- `vauthors` value: split at every list separator and comma (the Vancouver format separates people by commas); every
  non-empty (after `str.strip()`) piece is a person.
- `authors` value (one person per parameter): split at list separators; a piece holding a conjunction or two or more
  commas is packed, otherwise a person (a single comma is the "Surname, Given" form).
- `author_lists` value (a free-form list): split at list separators; a piece holding a conjunction or a comma is
  packed, otherwise a person.

For each part, `N` = its cited name words. A part is *comparable* when some word of `N` has a script that some word of
`S_R` has; a part that is not comparable is set aside. A comparable person part *agrees* if `N ∩ S_R ≠ ∅`, else it
*conflicts*. A comparable packed part *conflicts* if `N ∩ S_R = ∅` (none of the names it holds is an author), and is
otherwise *undetermined* (it may hold an author and a non-author: it never counts as agreement).

Author verdict: **CONFLICT** if some comparable part conflicts; else **AGREE** if some comparable person part agrees;
else **INSUFFICIENT**. Authors never establish the object (section 5): an AGREE only reports that no comparable cited
author is a non-author.

### 4.2 Title (A-02: weak compatibility is not identity)

`T_R = words(R.title)`. For each value `t` of `C.titles` with `T = words(t)` non-empty, and `T_R` non-empty, the
relation of `T` to `T_R`:

1. **EQUAL**: `T = T_R`;
2. **SHORTER**: `T` is a contiguous subsequence of `T_R` and shorter (the cited title is a shortened form);
3. **LONGER**: `T_R` is a contiguous subsequence of `T` and shorter (the cited title adds words to the record's);
4. **OVERLAP**: they share at least one word;
5. **DISJOINT**: they share no word and some script has a word in both;
6. **INCOMPARABLE**: otherwise.

The pair's title relation is the best over the values in the order EQUAL > SHORTER > LONGER > OVERLAP > DISJOINT >
INCOMPARABLE (ties keep the first value in field order); with no value or an empty `T_R` it is **MISSING**.

**Designation of a related object**, checked for every value whose relation is not EQUAL (SHORTER, LONGER, OVERLAP,
DISJOINT or INCOMPARABLE; one designating value suffices, fail closed, even when another value is EQUAL: a citation
whose `title` equals the record's but whose `chapter` is "Erratum" may name the erratum). The *cited extra words* and
the *record extra words* are:

- SHORTER: none; the words of `T_R` outside the leftmost occurrence of `T`;
- LONGER: the words of `T` outside the leftmost occurrence of `T_R`; none;
- OVERLAP, DISJOINT and INCOMPARABLE: the words of `T` not in `T_R`; the words of `T_R` not in `T`.

The value designates when a cited or a record extra word is in the designation lexicon `DW`, or a phrase of `DP` occurs
as consecutive words of `T` but not of `T_R`, or of `T_R` but not of `T`. The lexicon is bib-1's, unchanged (Crossmark
update types, the NLM comment genre and its answers, the note genres D-083 names, their Arabic translations, singular
and plural; `DP`: `expression of concern`, `expressions of concern`, `تعبير عن القلق`). A designation word on the
record's side means the record is itself a note on the object the citation names (a retracted comment cited by the
title of the paper it comments on); on the cited side, that the citation names a note on the record's work.

Title verdict: designation → **CONFLICT** (reason `BIB_TITLE_RELATED_OBJECT`); else DISJOINT → **CONFLICT**
(`BIB_TITLE_DISJOINT`); EQUAL or SHORTER → **AGREE**; LONGER → **NOT_ESTABLISHED** (`BIB_TITLE_EXTENDED`); OVERLAP →
**NOT_ESTABLISHED** (`BIB_TITLE_PARTIAL`); INCOMPARABLE → **NOT_ESTABLISHED** (`BIB_TITLE_INCOMPARABLE`); MISSING →
**INSUFFICIENT**. The designation lexicon is not extended: a longer title is not established whatever its extra words
are, so the lexicon only names the conflict.

### 4.3 Recorded, never decisive

Unchanged: year (first match of `(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)` in `C.date`, else `C.year`; SAME,
DIFFERENT or INSUFFICIENT against `R.original_year`), periodical (both word lists non-empty and equal → SAME; both
non-empty and unequal → DIFFERENT; else INSUFFICIENT), volume, issue, pages (NOT_IN_RECORD).

## 5. Object verdict

Under one reading (section 3.1):

- **MATERIAL_CONFLICT** if the author verdict is CONFLICT or the title verdict is CONFLICT; reasons
  `BIB_AUTHORS_DISJOINT` (authors CONFLICT), `BIB_TITLE_DISJOINT` (relation DISJOINT), `BIB_TITLE_RELATED_OBJECT`
  (designation).
- else **NOT_ESTABLISHED** if the title verdict is NOT_ESTABLISHED; reason the title's (`BIB_TITLE_EXTENDED`,
  `BIB_TITLE_PARTIAL` or `BIB_TITLE_INCOMPARABLE`).
- else **COMPATIBLE** if the title verdict is AGREE;
- else **INSUFFICIENT** (no cited title or no record title; also whenever the record has no bibliographic fields).

The pair's result combines the readings (section 3.1). A unit that is ABSENT or UNAVAILABLE is not compared.

## 6. Decision table dt-4

dt-4 is dt-2 with three rules inserted between D-13 and D-14, all guarded like D-14 (the deciding lookup L is
`matched` with a `verified_fact` projection), so each replaces only what would otherwise be a positive:

- **D-13a** (dt-3, unchanged): some event of L (direct or bridged) is in MATERIAL_CONFLICT with the unit's description
  → `UNRESOLVED_IDENTITY`, reasons `BIBLIOGRAPHIC_OBJECT_CONFLICT` plus the bib-2 reasons of every conflicting event.
- **D-13b** (D-086): the unit's check is UNAVAILABLE(r) → `UNRESOLVED_IDENTITY`, reasons
  `BIBLIOGRAPHIC_CHECK_UNAVAILABLE` and `r`.
- **D-13c** (D-087): some event of L is NOT_ESTABLISHED (and none is in MATERIAL_CONFLICT) →
  `UNRESOLVED_IDENTITY`, reasons `BIBLIOGRAPHIC_OBJECT_NOT_ESTABLISHED` plus the bib-2 reasons of every such event.

Each also carries the common tail of dt-2 (`KEY_RESULTS_DIFFER`, `PAIR_UNCORROBORATED`, `CO_REPORTED_MULTIPLE` where
they hold) and keeps L's Stage 02 basis reasons (upstream role L), as D-10 and D-13a do. Status `uncertain`, value null.

An UNAVAILABLE unit has no comparisons, so D-13a and D-13c cannot hold for it; D-13a and D-13c are exclusive by their
guards. D-1 to D-13 keep their place, classes and reasons; D-14, D-15, D-16 and D-17 are unchanged. dt-4 with an
ABSENT unit, or a DESCRIBED unit whose every compared event is COMPATIBLE or INSUFFICIENT, decides exactly as dt-2
(section 8, B5). The D-072 role-collision rule is unchanged (bib-2 never resolves a role collision).

## 7. Evidence

- NORMALIZE: per `citation_template` unit one `cited_bibliography` item (observation: the extraction; pointer
  `/units/i`; ref: the unit item) whose value is `{version: "bib-2", fields}` for DESCRIBED or `{version: "bib-2",
  unavailable: r}` for UNAVAILABLE; an ABSENT unit has none. The unit's entry in the candidate inputs carries
  `bibliography` (the fields, or null) and `bibliography_unavailable` (`r`, or null); exactly one of them is non-null
  for a `citation_template` unit, both are null otherwise.
- LOOKUP: unchanged (`records`, bound to the events by `event_id` and `row_sha256`; DETECT refuses a misaligned,
  unbound or contradicting list with `ADAPTER_INCONSISTENT`).
- DETECT: a D-13a, D-13c or D-14 claim is supported by one `lookup_record` item per event of L and by the unit's
  `cited_bibliography` item when it has one; a D-13b claim by the unit's `cited_bibliography` item, which records why
  the check was unavailable. Verdicts are recomputed by VERIFY's replay from the committed source, extraction and
  records (UNAVAILABLE included), never stored as item values.

## 8. Required properties

B1 determinism. B2 symmetry of EQUAL, OVERLAP and DISJOINT under exchange of the two titles, and SHORTER ↔ LONGER.
B3 adding an author word shared with the record to a person part never turns AGREE into anything else.
**B4 (P3)**: dt-4 never yields a positive that dt-3 would not yield for the same inputs: for every pair, if bib-2's
result is COMPATIBLE or INSUFFICIENT under both readings then bib-1's result is not MATERIAL_CONFLICT; an UNAVAILABLE
unit never yields a positive. B5 equivalence: with an ABSENT unit, or with every compared event COMPATIBLE or
INSUFFICIENT, dt-4 = dt-2. B6 every D-13a, D-13b and D-13c claim carries its general reason and at least one bib-2
detail reason. B7 a role-collided or notice-only candidate is never changed by bib-2. B8 no input of section 2 outside
its type raises; the cited side gives UNAVAILABLE(BIB_PARSE_FAILED), the record side INSUFFICIENT fields. B9 the two
readings agree whenever no compared string holds a format character.

## 9. Known limits and costs

Costs on genuine citations (fail closed; measured on development evidence in `REGRESSION_DT4.md`, never an estimate):

- Every bib-1 cost remains (section 9 of `BIBLIOGRAPHIC_SPEC.md`: records listing fewer authors, misspelled or
  mixed-script record names, a genre word added by the citation, a title in another language, a conflicting bridged or
  co-keyed event, a hyphenated `re-` prefix).
- A cited title that adds words to the record's (a subtitle the record lacks, an editor's note such as "(retracted)"
  or "[Retracted article]", a series name) is NOT_ESTABLISHED; a title that differs from the record's by spelling,
  punctuation that splits a word, a number written differently or a translated word is OVERLAP and NOT_ESTABLISHED.
- A title in another script than the record's (an Arabic title of an English paper) is INCOMPARABLE and
  NOT_ESTABLISHED, unless another title value of the unit (for example `trans-title`) is EQUAL or SHORTER.
- A citation template above a bound, or one the pinned parser cannot read as exactly one template, abstains.
- A format character inside a genuine word makes the split reading see two words, so such a title is not EQUAL under
  both readings and abstains; a format character inside a genuine surname leaves the author part conflicting under the
  split reading, as under bib-1.
- A retracted work whose own title holds a lexicon word, cited by a shortened title that leaves that word out, abstains
  (SHORTER with a record extra word in `DW`); so does any citation of it with a second title value (a chapter, a
  journal name given as the title) that does not hold that word.
- A citation with a second title value that holds a lexicon word not in the record's title (for example a journal name
  "Letters in …" given as `title` beside the article as `chapter`) abstains, even when another value is EQUAL.

What still decides by identifiers alone (natural absence, P4): a unit that is ABSENT, or DESCRIBED with no cited title
(or a record with no title). An author agreement never makes such a unit stronger, and an author conflict still blocks
it. A unit whose only title is EQUAL or SHORTER and whose comparable authors are all undetermined (packed) is
COMPATIBLE: the title establishes the object and no cited author is shown to be a non-author.
