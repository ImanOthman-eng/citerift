# Bibliographic-object consistency layer, version 2: specification (bib-2, decision table dt-4)

Owner decisions D-086 and D-087 (`cmsg_018VCB51nDHP6HXmLU4ea5yP2PP7zzBVkR1qLdWfXovT83`, 2026-11-20), revising bib-1
(`BIBLIOGRAPHIC_SPEC.md`, kept unchanged as the specification of the candidate `c3854b8` that D-085 did not accept).
Normative for the production module `citerift.investigation.bibliographic` and for the independent reference model
`simulations/stage04/bib2_reference.py`, which is written from this document alone and imports no production code.

Changes from bib-1, each stated where it applies (amended after the independent reference's reviews, items A1 to A15
and M1 to M8 of `simulations/stage04/bib2_reference_NOTES.md`, before any regression was produced; the dt-4 oracle
abstracts the bib-2 detail reasons and is unchanged by them):

- **D-086**: a bibliographic check that cannot be performed (a resource bound, a parse or normalisation failure) is a
  state of its own, `UNAVAILABLE` with a reason, never the natural absence of a description; it blocks a positive
  (section 2.1, section 6, rule D-13b).
- **D-087, G-04**: invisible characters (Unicode general category Cf, non-whitespace controls, or
  Default_Ignorable_Code_Point) are read as written, as a word boundary and as nothing, and a pair must pass under all
  three readings (section 3.1); a word mixing scripts (look-alike letters) is never read as harmless (section 3.2).
- **D-087, A-02**: weak compatibility is not identity. A positive needs every cited title value to equal the
  record's title; a shorter (even the record's main title without its subtitle), longer or partially overlapping
  title, or one that cannot be compared, does not establish the object (`NOT_ESTABLISHED`, rule D-13c). A genre the
  citation states (`|type=`, `|department=`) must be named by the record's title (section 4.2a). Markup whose
  rendering cannot be read makes the check unavailable (section 2.1). Authors can only refute, never establish. An
  author value that packs several people agrees with nothing (section 4.1).

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
4. Effective named arguments: for each parameter of that template in source order with `showkey` true, its name is
   `str(param.name).strip()` when `param.name` consists of Text nodes only. A name of Text and Comment nodes is read
   with its comments removed (MediaWiki ignores them), stripped: when that name belongs to no family (step 6) the
   parameter is ignored, as bib-1 ignored it (bib-1 read the name with its comment, which no alias matches); when it
   belongs to a family the result is `UNAVAILABLE(BIB_PARSE_FAILED)` (MediaWiki reads the value under that name and
   bib-1 did not; reading it could replace an earlier argument of the same name and so remove a value bib-1 compared,
   against B4). A name holding any other node (a template, a link, an argument) cannot be read without expanding it
   and gives `UNAVAILABLE(BIB_PARSE_FAILED)`. A later parameter of the same name
   replaces an earlier one (its name keeps the position of its first occurrence). Positional parameters are ignored.
5. Hidden content: if an effective argument whose name falls in a compared family (`titles`, `genres`, `authors`,
   `author_lists`, `vauthors`; step 6) holds, at any depth of its value, a Template node (a template, a parser
   function or a magic word: `{{lang|en|Comments on}}`, `{{lc:Comments on}}`, `{{PAGENAME}}`, `{{snd}}`), an Argument
   node (`{{{x}}}`) or a Tag node whose tag, stripped and lower-cased, is not one of the readable tags (the inline
   formatting tags of the next paragraph, `nowiki` and `br`), the result is `UNAVAILABLE(BIB_PARSE_FAILED)`: what such
   a node renders cannot be known without expanding it (cleaning drops a template, and drops the content of `<math>`,
   `<score>` and similar tags), so the value cannot be read. Values of the recorded families are not checked.

   Value cleaning, unchanged from bib-1 (section 2.1 step 4 of `BIBLIOGRAPHIC_SPEC.md`): node by node over the
   top-level nodes of `param.value`, each node's text is `strip_code(normalize=True, collapse=True)` of that node alone;
   the text of a Text node, an HTML entity, a wikilink, an external link or an inline formatting tag (`i`, `b`, `sub`,
   `sup`, `span`, `small`, `big`, `u`, `s`, `em`, `strong`) is joined to its neighbours as written; a Comment node
   (it renders nothing) is written as one U+200B ZERO WIDTH SPACE, and the text of a `nowiki` tag (rendered as written,
   joined to its neighbours) is written between two U+200B (M1: MediaWiki renders `Err<!-- -->atum` and
   `Err<nowiki/>atum` as one word, bib-1 read a word boundary; as an invisible character U+200B gives both readings,
   section 3.1); the text of every other node is surrounded by one space on each side. Then every run of Python `re`
   `\s` (str patterns) becomes one space and the result is stripped with `str.strip()`. A result with no character
   that is not invisible (section 3.1) is an absent value. In a non-empty value every
   lone surrogate (U+D800 to U+DFFF) is replaced by U+FFFD. Invisible characters are kept here; section 3.1 reads them.
6. Fields by parameter family (alias profile, section 2.2). A name belongs to the first family, in the order listed
   below, then the first key, in the order listed, then the first alias, in profile order, whose alias pattern matches
   it whole (so ar `host`, which matches both `host#` of AuthorList-Last and `host` of Authors, is in `authors`).
   Each family's values are in source order of the effective arguments (first occurrence of the name):
   - `titles`: Title, ScriptTitle, TransTitle, Chapter, ScriptChapter, TransChapter. For ScriptTitle and
     ScriptChapter a leading language prefix matching `^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:` is removed, the rest stripped
     again, and an empty rest is an absent value.
   - `genres`: TitleType (`type`, `medium`; ar also `النوع`) and TitleNote (`department`, `title-note`), which CS1
     renders beside the title and which editors use to state an item's genre (`|type=Erratum`, `|department=Letters`).
   - Authors, now kept by form: `authors` (key AuthorList-Last: one person per parameter, as CS1 intends),
     `author_lists` (key Authors: a free-form list) and `vauthors` (key Vauthors: a Vancouver list).
   - `periodical`, `date`, `year`, `volume`, `issue`, `pages` (Page and Pages together): first value; recorded only.
7. Bounds (never truncated, since a truncated description could change a verdict): if `titles` and `genres`
   together have more than 64 values, or `authors`, `author_lists` and `vauthors` together have more than 64 values, the result is
   `UNAVAILABLE(BIB_VALUE_LIMIT_EXCEEDED)`; otherwise, if the values of step 6 together have more than 4,096 code
   points (every value of every family, the values of the recorded families after the first included, each counted
   after cleaning and after the removal of a script prefix), `UNAVAILABLE(BIB_DESCRIPTION_LIMIT_EXCEEDED)`. Development maxima over 12,501 units: 56 values in
   one family, 1,804 code points (`lows/description_sizes.json`).
8. Otherwise `DESCRIBED(C)`.

An unknown wiki (not in the profile) is not a property of the unit but of the engine's configuration: the engine
refuses to run (as for a profile with other bytes, section 2.2). Stage 03 supports `ar` and `en` only.

### 2.2 Parameter-alias profile (bib-profile-2)

`src/citerift/investigation/data/bib-profile-2.json` (SHA-256 `7420622e…`): bib-1's profile (`bib-profile-1.json`,
unchanged and still pinned by bib-1) with the keys TitleType and TitleNote added, all copied from each wiki's
`Module:Citation/CS1/Configuration` (en revision 1384336575, ar revision 76424085, content SHA-256 as recorded in the
profile); `#` matches the empty string or a
positive decimal integer without leading zero; names are compared exactly. The profile bytes, the parser version and
the parser's C tokenizer are pinned by the engine, which refuses otherwise.

### 2.3 Record object R (LOOKUP)

Unchanged: for every event of a lookup observation, from the same Stage 02 event: `title`, `authors`
(`;`-separated full names, given name first), `journal`, `original_year`; bound by `event_id` and `row_sha256`.

## 3. Normalization

### 3.1 Readings of invisible characters (G-04)

An *invisible character* is a code point of Unicode general category Cf, a control character (category Cc) that is
not whitespace for `str.isspace()`, or a code point with the Unicode property Default_Ignorable_Code_Point (a stable property; its code points are U+00AD, U+034F, U+061C, U+115F to U+1160, U+17B4 to
U+17B5, U+180B to U+180F, U+200B to U+200F, U+202A to U+202E, U+2060 to U+206F, U+3164, U+FE00 to U+FE0F, U+FEFF,
U+FFA0, U+FFF0 to U+FFF8, U+1BCA0 to U+1BCA3, U+1D173 to U+1D17A and U+E0000 to U+E0FFF). This is a general Unicode rule,
not a list of observed characters: soft hyphen, zero-width space, zero-width non-joiner and joiner, word joiner,
byte-order mark, the bidirectional controls, variation selectors and the Hangul fillers are all included. An invisible
character renders as nothing ("Com&shy;ments" renders as "Comments"), and it is ambiguous whether it separates two
words or sits inside one; some of these characters are word characters for section 3.2 (U+3164 is a letter), others
are not. So every comparison of sections 4 and 5 is made under three readings of the compared strings (the cited title
values, the cited genre values, the cited author values of all three forms, the record's title and authors):

- **as written**: every string as it is (exactly bib-1's reading);
- **boundary**: every invisible character replaced by one space;
- **joined**: every invisible character removed.

When no compared string holds an invisible character the three readings are identical and the comparison is made once
(`readings` = 1). When some string holds one (`readings` = 3), the pair's result is the worst of the three in the order
MATERIAL_CONFLICT > NOT_ESTABLISHED > INSUFFICIENT > COMPATIBLE; the reported field verdicts (and year and periodical,
which no reading changes) are those of the first reading, in the order as written, boundary, joined, that gives it, and
the reasons are the union of the reasons of every reading that gives it. So a designation hidden by an invisible
character is found (boundary or joined reading), and an invisible character can never make a pair pass that bib-1
would have refused (as-written reading).

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

New in bib-2: a word is *mixed* when its letters (general category L, except Lm) belong to two or more scripts
(`script` of each letter). A mixed word cannot be read: a designation or a name written with look-alike letters of
another script ("Errаtum" with a Cyrillic а) would match neither the lexicon nor a record word. A mixed word counts as
a designation (section 4.2) and makes an author part comparable (section 4.1), so it can only block. M6: as in the
augmented script sets of Unicode UTS #39 (section 5.1), the scripts that one writing system mixes by design count as
one: a word whose letters' scripts all lie in {`CJK`, `HIRAGANA`, `KATAKANA`} (Japanese), in {`CJK`, `HANGUL`}
(Korean) or in {`CJK`, `BOPOMOFO`} is not mixed.

M7: the *skeleton* of a word, used only to look a word up in the designation lexicon (sections 4.2 and 4.2a): every
character whose Unicode name fully matches `LATIN (SMALL |CAPITAL )?LETTER ([A-Z]+ )*([A-Z])( WITH [A-Z ]+)?` is
replaced by the casefolded letter of the last single-letter group (small capitals, dotless i, script, turned and long
letters: "ᴇʀʀᴀᴛᴜᴍ" and "Errıtum" are read as "erratum" and "erritum"); other characters are kept. A word *names a
designation* when it or its skeleton is in `DW`; a phrase of `DP` *occurs* in a word sequence when it occurs in the
sequence or in the sequence of the words' skeletons. Look-alikes within one script then cannot hide a lexicon word.

## 4. Field verdicts

### 4.1 Authors (A-02: a packed value agrees with nothing)

The cited author values are split into **parts**, each either a *person* (one name) or a *packed* part (possibly
several names that cannot be told apart). A *list separator* is `;` or the Arabic semicolon `؛`; a *comma* is `,` or
the Arabic comma `،`; a *conjunction* is `&`, or a whitespace token that casefolds to `and` or is the Arabic `و`.

- `vauthors` value: split at every list separator and comma (the Vancouver format separates people by commas); every
  non-empty (after `str.strip()`) piece is a person.
- `authors` value (one person per parameter) and `author_lists` value (a free-form list): split at list separators; a
  piece holding a conjunction or a comma is packed, otherwise a person ("Smith, John" and "Smith J, Jones K" cannot be
  told apart, so neither ever agrees; a conflict is found in both, as for a person).

For each part, `N` = its cited name words. A part is *comparable* when `S_R` is not empty and some word of `N` has a
script that some word of `S_R` has, or some word of `N` is mixed; a part that is not comparable is set aside. A comparable person part *agrees* if `N ∩ S_R ≠ ∅`, else it
*conflicts*. A comparable packed part *conflicts* if `N ∩ S_R = ∅` (none of the names it holds is an author), and is
otherwise *undetermined* (it may hold an author and a non-author: it never counts as agreement).

Whole-value guard (bib-1's test, kept so that splitting a value can never hide a conflict bib-1 found, B4): for each
cited author value of the three forms, `W` = its cited name words; if `W` is comparable (as a part) and
`W ∩ S_R = ∅`, the author verdict is CONFLICT.

Author verdict: **CONFLICT** if the whole-value guard applies or some comparable part conflicts; else **AGREE** if some comparable person part agrees;
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

The value designates when a cited or a record extra word names a designation or is mixed (section 3.2), or a phrase of
`DP` occurs as consecutive words of `T` but not of `T_R`, or of `T_R` but not of `T`. The lexicon is bib-1's, unchanged (Crossmark
update types, the NLM comment genre and its answers, the note genres D-083 names, their Arabic translations, singular
and plural; `DP`: `expression of concern`, `expressions of concern`, `تعبير عن القلق`). A designation word on the
record's side means the record is itself a note on the object the citation names (a retracted comment cited by the
title of the paper it comments on); on the cited side, that the citation names a note on the record's work.

A value *agrees* when its relation is EQUAL. M8: a SHORTER value never agrees, not even the record's main title (the
words before a subtitle separator): whether the omitted words name another object (a notice subtitle in another
language, "Berichtigung", "訂正"; a part number, "Part II"; a citation-index correction title, "X (vol 5, pg 3,
2001)"; a look-alike the skeleton does not read) cannot be decided without extending the lexicon, which D-087
forbids, and a part of a title may be the whole title of another work. (M8 supersedes M5 and the main-title rule of
the previous amendment.)

Title verdict, with the pair relation MISSING first: MISSING → **INSUFFICIENT**; else designation or a pair relation
DISJOINT → **CONFLICT** (reason `BIB_TITLE_RELATED_OBJECT` for a designation and `BIB_TITLE_DISJOINT` for the
relation DISJOINT; both when both hold); else, when every compared value (non-empty `T`; at least one exists, since
the relation is not MISSING) agrees → **AGREE**; else, when some value agrees and another does not → **NOT_ESTABLISHED**
(`BIB_TITLE_VALUES_DIFFER`, M4: a `chapter`, `trans-title` or `script-title` that is not the record's title names
something the record does not, whatever its words: `|title=T |chapter=Remarks` or `|trans-title=T: remarks` beside the
record's own title); else by the pair relation: SHORTER → **NOT_ESTABLISHED** (`BIB_TITLE_SHORTENED`, M8); LONGER →
**NOT_ESTABLISHED** (`BIB_TITLE_EXTENDED`); OVERLAP → **NOT_ESTABLISHED** (`BIB_TITLE_PARTIAL`); INCOMPARABLE →
**NOT_ESTABLISHED** (`BIB_TITLE_INCOMPARABLE`). The designation lexicon is not extended: a
title value that is not the record's title is not established whatever its extra words are, so the lexicon only names
the conflict.

### 4.2a Genre (A-02: a stated genre is a designation, and must be the record's)

For each `genres` value `g` with `G = words(g)`: the value designates when some word of `G` names a designation or is
mixed and is not a word of `words(R.title)`, or a phrase of `DP` occurs in `G` and not in `words(R.title)` (an absent
record title has no words). A designating genre value is a designation of the pair (section 5,
`BIB_TITLE_RELATED_OBJECT`), whatever the title relation, including MISSING: `|type=Erratum` beside the record's own
title names the erratum. A genre word the record's title also holds (a retracted letter cited with `|type=Letter`)
does not designate.

M3: a genre value that does not designate but has a word that is not a word of `words(R.title)` is *unmatched*: the
lexicon is not extended (D-087), so a genre it does not know (`|type=Conference abstract`, `|type=Preprint`, ar
`|النوع=رسالة`, a spelling variant of a lexicon word) cannot be told from a harmless one (`|type=Research article`);
the pair is not established (section 5, `BIB_GENRE_UNMATCHED`).

### 4.3 Recorded, never decisive

Unchanged: year (first match of `(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)` in `C.date`, else `C.year`; SAME,
DIFFERENT or INSUFFICIENT against `R.original_year`), periodical (both word lists non-empty and equal → SAME; both
non-empty and unequal → DIFFERENT; else INSUFFICIENT), volume, issue, pages (NOT_IN_RECORD).

## 5. Object verdict

Under one reading (section 3.1):

- **MATERIAL_CONFLICT** if the author verdict is CONFLICT, the title verdict is CONFLICT or a genre value designates;
  reasons, every one that holds: `BIB_AUTHORS_DISJOINT` (authors CONFLICT), `BIB_TITLE_DISJOINT` (relation DISJOINT),
  `BIB_TITLE_RELATED_OBJECT` (a designation of a title value or of a genre value; the reported `designation` is true).
- else **NOT_ESTABLISHED** if the title verdict is NOT_ESTABLISHED or some genre value is unmatched (section 4.2a);
  reasons, every one that holds: the title's (`BIB_TITLE_SHORTENED`, `BIB_TITLE_EXTENDED`, `BIB_TITLE_PARTIAL`,
  `BIB_TITLE_INCOMPARABLE` or `BIB_TITLE_VALUES_DIFFER`) and `BIB_GENRE_UNMATCHED`.
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
result is COMPATIBLE or INSUFFICIENT then bib-1's result is not MATERIAL_CONFLICT; an UNAVAILABLE
unit never yields a positive. B5 equivalence: with an ABSENT unit, or with every compared event COMPATIBLE or
INSUFFICIENT, dt-4 = dt-2. B6 every D-13a, D-13b and D-13c claim carries its general reason and at least one bib-2
detail reason. B7 a role-collided or notice-only candidate is never changed by bib-2. B8 no input of section 2 outside
its type raises; the cited side gives UNAVAILABLE(BIB_PARSE_FAILED), the record side INSUFFICIENT fields. B9 the three
readings agree whenever no compared string holds an invisible character.

## 9. Known limits and costs

Costs on genuine citations (fail closed; measured on development evidence in `REGRESSION_DT4.md`, never an estimate):

- Every bib-1 cost remains (section 9 of `BIBLIOGRAPHIC_SPEC.md`: records listing fewer authors, misspelled or
  mixed-script record names, a genre word added by the citation, a title in another language, a conflicting bridged or
  co-keyed event, a hyphenated `re-` prefix).
- A cited title that adds words to the record's (a subtitle the record lacks, an editor's note such as "(retracted)"
  or "[Retracted article]", a series name) is NOT_ESTABLISHED; a title that differs from the record's by spelling,
  punctuation that splits a word, a number written differently or a translated word is OVERLAP and NOT_ESTABLISHED.
- A title in another script than the record's (an Arabic title of an English paper) is INCOMPARABLE and
  NOT_ESTABLISHED, also when another title value of the unit (for example `trans-title`) is EQUAL (M4,
  `BIB_TITLE_VALUES_DIFFER`); so is a book chapter cited with the book's title as `title` when the record holds the
  chapter's title, and a citation with a translated title beside the original.
- A genre value with a word the record's title lacks and the lexicon does not hold (`|type=Research article`,
  `|type=Review`, `|medium=Print`) abstains (M3, `BIB_GENRE_UNMATCHED`).
- A citation that gives the record's main title without its subtitle abstains (M8, `BIB_TITLE_SHORTENED`), and so does
  one that gives the main title beside the full title in another value (`BIB_TITLE_VALUES_DIFFER`).
- A comment or a `nowiki` tag inside a genuine title is read both as a word boundary and as nothing (M1); the title
  is EQUAL under every reading only when both give the record's words.
- A citation template above a bound, or one the pinned parser cannot read as exactly one template, abstains.
- An invisible character inside a genuine word makes the as-written or boundary reading see two words (or a different
  word), so such a title is not EQUAL under every reading and abstains; an invisible character inside a genuine
  surname leaves the author part conflicting under one reading, as under bib-1.
- A source with a leading byte-order mark or any other text beside the one template (the mark is no whitespace for
  `str.strip()`) is not exactly one template and abstains (`BIB_PARSE_FAILED`). So does a compared value that holds any
  template, parser function or magic word (`{{lang|…}}`, `{{nowrap|…}}`, `{{snd}}`, `{{-}}`), a template argument or a
  tag other than inline formatting, `nowiki` and `br` (`<math>`, `<ref>`), whatever it renders, and a parameter whose
  name holds markup other than a comment, or a comment around a name of a compared or recorded family.
- Any shortened cited title (the main title, the first words of a long title, the subtitle alone) is NOT_ESTABLISHED
  (`BIB_TITLE_SHORTENED`).
- A genre value with a lexicon word the record's title lacks (`|type=Letter` for a research article recorded without
  that word, `|department=Correspondence` is not one: "correspondence" is not in the lexicon) abstains.
- A mixed word (section 3.2) among a value's extra words, or in a genre value, abstains (a Greek letter written inside
  a Latin word, "αvβ3", when the record's title lacks that word); a mixed word in a cited author name makes the part
  comparable, so it conflicts unless it shares a record surname word. Japanese and Korean words mixing their own
  scripts are not mixed (M6).
- A second title value (a chapter, a journal name given as a title) beside an EQUAL value is checked for designation:
  when the record's title holds a lexicon word that the second value lacks ("Immune response to …" beside the chapter
  "Introduction"), the pair is MATERIAL_CONFLICT and abstains.
- A retracted work whose own title holds a lexicon word, cited by a shortened title that leaves that word out, abstains
  (SHORTER with a record extra word in `DW`); so does any citation of it with a second title value (a chapter, a
  journal name given as the title) that does not hold that word.
- A citation with a second title value that holds a lexicon word not in the record's title (for example a journal name
  "Letters in …" given as `title` beside the article as `chapter`) abstains, even when another value is EQUAL.

Properties that are not costs but are stated so that no one reads more into the layer than it gives:

- Only an EQUAL title establishes the object (M8). The residual this leaves is a distinct object registered under
  exactly the record's title (a notice titled as the article it concerns), which the identifiers and the equal title
  together cannot tell apart; the owner's decision D-087 names EQUAL as strong.
- Parameters outside the families of section 2.1 step 6 are not read: CS1's `series` (alias `version`), `book-title`,
  `at`, `edition`, `journal`-like containers. They name a container, an edition or a location, not the cited object,
  and are rendered apart from the title; like `periodical` they never decide. Their use on development evidence is
  measured in `dt4/lows/description_sizes.json`.
- Authors only refute. A value naming one record author and one non-author in a form that cannot be split ("Smith J,
  Jones K" in `author`) is packed and undetermined, never a conflict; it never makes a pair stronger either. The en
  profile has no `authors` alias (the wiki's own CS1 configuration), so `|authors=` on en is not read and a conflict it
  might show is not found. The record's authors are split at `;` only, the Stage 02 separator.
- The value bound of 64 titles cannot be reached (at most 18 en and 26 ar title names); it is kept as a stated bound.

What still decides by identifiers alone (natural absence, P4): a unit that is ABSENT, or DESCRIBED with no cited title
(or a record with no title), and no genre value. An author agreement never makes such a unit stronger, and an author
conflict still blocks it. A unit whose only title is EQUAL and whose comparable authors are all undetermined (packed)
is COMPATIBLE: the title establishes the object and no cited author is shown to be a non-author.
