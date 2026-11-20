# bib2_reference.py and dt4_reference.py: notes

Fourth review, against `docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md` as amended after the third
review (items B1 to B7: comments and `nowiki` in values, genres under the three readings, unmatched genres, every title
value must agree, a main title alone needs an agreeing author, augmented script sets, Latin look-alike skeleton). Inputs
used, as before: that file, `BIBLIOGRAPHIC_SPEC.md` section 2.1 step 4 and section 3 (declared unchanged), the earlier
independent `bib_reference.py` (parsing, cleaning and word code copied), `bib-reference-profile.json` (copied and
extended into `bib2-reference-profile.json`, below) and `dt3_reference.py`. No production code, production test,
production profile, production diff, corpus expectation or other final-cycle document was opened. The readings taken
where the text leaves a choice are R1 to R25 of the module docstring of `bib2_reference.py`, now
`MODEL_VERSION = "bib-2-reference/4"` (bumped from /3: the behaviour changed). Nothing below is fixed in the model: the
model implements the text as read.

Severity of a remaining path (a positive that could be wrong, or a check that cannot be made but is read as natural
absence): **CRITICAL** = a likely input reports a different publication positive; **HIGH** = a plausible editor practice
does; **MEDIUM** = a rare or unusual input does, or a class the specification set out to close stays open;
**LOW** = contrived or adversarial input, a residual the specification states, or reporting only. **COST** = fail closed
(an abstention), for the regression.

## Profile (section 2.2): `bib2-reference-profile.json`

Unchanged since the third review. `bib2_reference.py` loads `simulations/stage04/bib2-reference-profile.json`
(`PROFILE_PATH`, the default of `load_profile()`). It is the bib-1 reference's profile `bib-reference-profile.json`
(left unchanged: it is the input of `bib_reference.py` and its oracle) with the keys TitleType and TitleNote added for
both wikis, extracted from the pinned raw modules, downloaded with `curl` from
`https://en.wikipedia.org/w/index.php?oldid=1384336575&action=raw` and
`https://ar.wikipedia.org/w/index.php?oldid=76424085&action=raw`. SHA-256 of the downloads: en
`3bf19c2ad5cacfd87122a6d9b763469f1bcc34fd10db176b9d2d714bc9fcdbf4`, ar
`32ffe2c261413bc443aa27ece9a1a7a92c6d752e7f5d9a2b669ba77dec985f07`, equal to the `content_sha256` recorded in both
files. The entries, inside the `local aliases = {` table:

- en line 383 `['TitleNote'] = {'title-note', 'department'},`, line 384 `['TitleType'] = {'type', 'medium'},`
- ar line 413 `['TitleNote'] = {'title-note', 'department'},`, line 414 `['TitleType'] = {'النوع', 'type', 'medium'},`

SHA-256: `bib-reference-profile.json` `71ed58e047373246d5c60ff2c0fa549d10231a2f0d2eb01dadf80f307a423ac1` (as
committed), `bib2-reference-profile.json` `ddbf2372c400c2bb173aa11af4b7d01193137d330e78455afa3512cd2f7e18b3`.

## (a) Status of the third-review items

| Third review | Amendment | Model now (log) |
|---|---|---|
| 1 MEDIUM comment or `<nowiki/>` inside a word read as a boundary | B1: a Comment is one U+200B, a `nowiki` tag's text sits between two; all-invisible value absent | `\|chapter=Err<!-- -->atum` and `Err<nowiki/>atum` beside an EQUAL title, the same in `\|type=`: MATERIAL_CONFLICT, 3 readings (B1a, B1c, B1j, B1k; earlier P1, P2, P3b); a comment-only, `<nowiki/>`-only or `&#8203;&shy;` title is absent (B1g to B1i) |
| 2 MEDIUM genres not under the readings | B2: genre values are compared strings | `\|type=Err` U+200B `atum`: MATERIAL_CONFLICT (B2a, earlier P3); an invisible character only in a genre gives 3 readings (B2c) |
| 3 MEDIUM Arabic lexicon gaps and spellings | B3: an unmatched genre value gives NOT_ESTABLISHED, `BIB_GENRE_UNMATCHED` (no lexicon growth) | ar `رسالة`, `مقال افتتاحي`, Persian-yeh `تعلیق`, `Research article`, `Conference abstract`, `Preprint`, `Print`: NOT_ESTABLISHED (B3a to B3e, B3k; earlier P4, P5, P5b, P8); a genre word the record's title holds stays COMPATIBLE (B3f); a genre of punctuation only has no word (B3h) |
| 4 LOW same-script look-alikes | B7: skeleton for lexicon lookups | small capitals, dotless i, small-capital DP word: MATERIAL_CONFLICT (B7a to B7d, B7f; earlier P6, P6b); names outside the pattern remain, (b) 1 |
| 5 LOW generic main title of another work | B5: a main title alone needs authors AGREE | NOT_ESTABLISHED without an author or with a packed one (B5b, B5c, B5f; earlier M2, M4, M6, P7); COMPATIBLE with an agreeing person part (B5a, B5e, B5g); residual (b) 2 |
| 6 LOW genre words outside the lexicon | B3 | NOT_ESTABLISHED (B3b, earlier P8) |
| 9 COST Japanese words mixed | B6: augmented sets | Japanese and Korean titles EQUAL to their records are COMPATIBLE (B6a to B6c); Cyrillic still mixed (B6d); Latin with kanji in one word still mixed (B6f) |
| (new) a second title value that is not the record's | B4: every value must agree, else `BIB_TITLE_VALUES_DIFFER` | `\|title=T \|chapter=Remarks`, `\|trans-title=T: remarks`, Arabic or Japanese title beside an EQUAL trans-title: NOT_ESTABLISHED (B4a to B4c, B4g; earlier 3b, P9); two EQUAL values, or an EQUAL value with the main title, COMPATIBLE (B4d, B4e) |

All round-3 remaining paths P1 to P9 now block (the log shows each; P9, earlier MATERIAL_CONFLICT through mixed
Japanese extra words, is now NOT_ESTABLISHED `BIB_TITLE_VALUES_DIFFER`).

## B4 against bib-1, both levels

Rerun with the independent bib-1 model (`bib_reference.py` with `bib-reference-profile.json`; bib-2 with
`bib2-reference-profile.json`; scripts in a scratch directory, not kept). A violation is "bib-2 COMPATIBLE or
INSUFFICIENT and bib-1 MATERIAL_CONFLICT". Evidence on generated inputs, not a proof.

- source level, random (`describe` + `compare` against bib-1's `cited_object` + `compare`, 15,000 sources x 9 records
  per seed; the third-review vocabulary plus comments and `<nowiki/>` inside and around surnames, initials and title
  words, `|last1=`, `|author1=`, and records with surnames "AB", "Sm", "Ith" and a soft hyphen): seed 5 `pairs 135000
  violations 0`, seed 9 `pairs 135000 violations 0`, seed 13 `pairs 135000 violations 0` (bib-2 COMPATIBLE 210, 202,
  236; INSUFFICIENT 13,932, 12,782, 13,731).
- source level, aimed at bib-2 positives (new: every source built from one of 10 records, its full title or main title
  and its surnames, perturbed with invisible characters, comments, `<nowiki/>`, entities, `<br>`, separators, lexicon
  words, look-alikes, initials, conjunctions and Arabic separators, with genre values from the record's title words;
  30,000 sources per seed): seeds 2, 3, 4 `pairs 30000 violations 0` each, bib-2 COMPATIBLE 7,184, 7,434 and 7,465.
- comparison level (random fields and records, 200,000 pairs per seed, now with random genre values in 30 per cent of
  the fields): seeds 7, 11 and 23 `violations 0` each (bib-2 COMPATIBLE 29, 28, 31; INSUFFICIENT 23,653, 23,072,
  23,179).

The aimed generator exists because the random ones reach few bib-2 positives; it was written for B1 (U+200B in place of
bib-1's space), whose only B4 bearing is a reading where bib-1's space and another invisible character meet: the
boundary reading reproduces bib-1's space, and the worst of three readings is taken.

## (b) Remaining paths and ambiguities in the amended specification

No CRITICAL, HIGH or MEDIUM path found. With B4 every title value must agree and with B3 every genre word must be a
word of the record's title, so a cited value can no longer carry an unread designation into a positive: a cited value
that is not the record's title or main title, and a genre word the record's title lacks, block whatever their words.
The lexicon and the mixed-word rule now matter for a positive only on the record's side, in the subtitle that a
main-title citation leaves out (items 1 and 2), and in the choice between MATERIAL_CONFLICT and NOT_ESTABLISHED, which
dt-4 treats alike for a positive (D-13a, D-13c).

### 1. LOW: a record subtitle that names a related object without a lexicon word

A cited main title agrees (with an agreeing author, B5) when the record's omitted subtitle names no designation. The
subtitle is the record's own text (Stage 02), so this needs a record whose title marks a notice without a lexicon word
or its skeleton:

- Latin look-alikes outside the B7 name pattern: `LATIN SMALL CAPITAL LETTER I WITH STROKE` (U+1D7B; "SMALL CAPITAL
  LETTER" is neither "SMALL LETTER" nor "LETTER SMALL CAPITAL"), `LATIN LETTER DENTAL CLICK` (U+01C0, looks like l),
  `LATIN SMALL LETTER ALPHA` (U+0251), a digit for a letter (`c0rrection`): COMPATIBLE (log B7e is the genre form, which
  blocks as unmatched; B7g, B7h, B7i are the record-subtitle form, COMPATIBLE).
- A notice title in a language other than English and Arabic (`Berichtigung`, `Rectificatif`, `訂正`), or an English
  notice word not in the lexicon (`update`, `supplement`, `addendum` is in it): COMPATIBLE (R2).
- Citation-index style titles of a correction, the original title followed by "(vol 5, pg 3, 2001)": the annotation is
  the subtitle and holds no lexicon word. Not tried on real records; it is LOW if Stage 02 titles come from Crossref or
  PubMed, which name such notices ("Correction to:", "Erratum:", "[Erratum]"), and should be measured if any Stage 02
  source uses that style.

In every case the citation must give only the main title and an author that agrees with the notice's authors (a notice
by the original authors agrees). Fix, if wanted: none within the lexicon rule; a record genre from Stage 02 (publication
type) would close it.

### 2. LOW (stated residual): a main title with an author that agrees through one shared word

B5 asks for an author verdict AGREE, which one comparable person part sharing one word with `S_R` gives. `S_R` holds
every name word of a record author except the first, so a middle name or an Arabic patronymic counts as a surname
(record "John Paul Smith", cited `|last1=Paul`: AGREE, log B5h), as does a common surname. The specification states the
residual ("a different work with that title and a shared author surname"). Parts of a series with one main title ("X:
Part I", "X: Part II") are the same case: a citation of "X" by the shared authors agrees with either part's record.

### 3. LOW (stated, by design): an EQUAL title of a distinct object

A record whose title equals the cited title is the same object for bib-2 unless an author refutes it. A correspondence
item or a notice registered under the original article's title, cited without authors or by authors it shares, is
COMPATIBLE (log R1). Identifiers decide; no rule of form can separate two objects with one title.

### 4. LOW: parameters bib-2 does not read

Only the families of section 2.1 step 6 are read. CS1 parameters outside them are not checked for a designation:
`|series=Retraction notices`, `|version=Erratum`, `|at=Erratum`, `|book-title=Letters` beside the record's own title
are COMPATIBLE (log R3 to R6), and the recorded families are not checked for hidden content (`|journal={{lc:Comments}}`,
R7). Editors state an item's genre in `|type=` and `|department=`, which are read; the others are unusual places for it.

### 5. LOW (stated, by design)

Natural absence (no cited title and no genre, or a record without title: identifiers decide, log R8), authors only
refute, a packed value with one record author never conflicts, en `|authors=` is not read, record authors split at `;`
only (section 9).

### 6. Ambiguities (the model's reading in brackets; none lets a positive through under the other reading unless said)

- **4.2 title verdict with no compared value.** "When every value (with non-empty `T`) agrees → AGREE" holds vacuously
  when no value is compared; the list then reaches MISSING → INSUFFICIENT only if the vacuous case is excluded. Read
  with section 5 ("INSUFFICIENT (no cited title or no record title ...)"): MISSING is checked first (R25). The literal
  order would make a unit with no cited title COMPATIBLE (fail open); suggest "every value agrees (at least one value)".
- **3.2 B7 pattern.** "The last single-letter group" is read as regex group 3 of a `fullmatch` (the single letter just
  before an optional " WITH ..." part). The pattern does not cover `LATIN SMALL CAPITAL LETTER ...` names (U+1D7B,
  U+1D7E) or letters named by a word (ALPHA, SCHWA, EZH, DENTAL CLICK); see (b) 1.
- **4.2a with B7.** "names a designation ... and is not a word of `words(R.title)`" and "unmatched: a word that is not a
  word of `words(R.title)`" compare the genre word itself, not its skeleton (R20); "a phrase of `DP` occurs in `G` and
  not in `words(R.title)`" uses "occurs" (with skeletons) on both sides. A skeleton reading of the word comparisons
  would turn some MATERIAL_CONFLICT into NOT_ESTABLISHED and back, never into a positive: a genre word the record's
  title does not hold as written is unmatched either way.
- **2.1 step 5, B1.** The comment and `nowiki` rules apply to top-level nodes of the value (cleaning is "node by node over
  the top-level nodes"). A comment or `nowiki` inside an inline tag (`''Err<!-- -->atum''`) is dropped or kept by
  `strip_code` of the tag, so it is read joined only (log B1l), as bib-1 read it and as MediaWiki renders it. No
  positive bearing: a non-agreeing title value or an unmatched genre word blocks either way. "The text of a `nowiki`
  tag" is read as `strip_code` of the tag (its literal content). A value of two comments with whitespace between them
  is "U+200B U+0020 U+200B", which has a character that is not invisible (the space) and so is present, with no word.
- **3.2 B6.** A letter whose name starts with a word other than the script's (U+3006 IDEOGRAPHIC CLOSING MARK, Lo, used
  in Japanese) still makes a Japanese word mixed (R14). Cost only.
- **5, B5.** The reported `title` is AGREE when B5 makes the object NOT_ESTABLISHED (log B5b); reporting only.
- Still standing from earlier reviews: 4.1 comparability grouping (R16, the literal reading blocks more); a name with an
  HTML entity is "any other node" and gives BIB_PARSE_FAILED (R5, cost); a genre designation leaves the reported title
  verdict as 4.2 gives it (R21).

### 7. COST (fail closed, for `REGRESSION_DT4.md`)

- B1: a comment or `<nowiki/>` inside a genuine title word or surname (`Gene ther<!-- -->apy`, `Sm<!-- -->ith`) is read
  as a boundary in one reading and abstains (B1d, B1m); `Smith<!-- -->J` is read as "SmithJ" in the joined reading and
  conflicts (B1n), as MediaWiki renders it.
- B2: an invisible character inside a genuine genre word (`Let` U+00AD `ter` against a record title with "letter") is
  unmatched in the as-written reading (B2b).
- B3: every genre word the record's title lacks abstains (`Research article`, `Review`, `Print`, `Journal article`),
  also in a unit with no cited title (B3i).
- B4: a translated or original-script title beside the EQUAL one, a chapter or book title beside the record's title.
- B5: every main-title citation without an agreeing person author.
- Unchanged: templates and non-readable tags in compared values, markup in parameter names, mixed words other than the
  B6 sets (Latin letters with kanji in one word, `DNA解析`, log B6f).

### dt-4 model

Section 6 is unchanged by the amendments, so `dt4_reference.py` is unchanged since the first review (`dt4-reference/1`,
`dt-4`; `bib` field with NONE, CONFLICT, UNAVAILABLE, NOT_ESTABLISHED; D-13a, D-13b, D-13c between D-13 and D-14 with the
D-14 guard, tier 7). Differential at the first review against `dt3_reference.py`, 200,000 random cases (seed 1):
`cases 200000 diffs 0 {'D-13c': 469, 'D-13b': 394}`. `BIB_TITLE_VALUES_DIFFER` and `BIB_GENRE_UNMATCHED` are bib-2
detail reasons, which the dt-4 model abstracts.

## (c) Self-test log

Produced by a scratch script (not kept) that calls `describe(source.encode("utf-8"), wiki, profile)` with
`bib2-reference-profile.json` and, for DESCRIBED units with a record, `compare(fields, record)`; output printed with
`json.dumps(..., ensure_ascii=True)` (describe output cut at 600 characters). Run with `uv run python` (Python 3.12.3,
mwparserfromhell 0.7.2, C tokenizer active, Unicode 15.0.0). Wiki is en unless the label says `[ar]`. Blocks: every input
of the earlier reviews rerun (labels unchanged; their expectations may have changed with the amendments), the probes of
the amendments B1 to B7, and the remaining paths of section (b) (R). Compared with the third-review log, exactly these
results changed: 3b, G6, H5 (now 3 readings), M2, M4, M6, P1 to P9; every other earlier input gives the same output.

```text
MODEL_VERSION bib-2-reference/4
======== Original inputs (rerun) ========

### 1 soft hyphen (entity) in designation word
source: '{{cite journal |title=Com&shy;ments on X |author=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Com\u00adments on X"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### 1b soft hyphen (literal U+00AD) in designation word
source: '{{cite journal |title=Com\xadments on X |author=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Com\u00adments on X"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### 2 ZWSP inside designation word, in a chapter beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u200batum |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200batum"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### 2b ZWSP inside designation word of the only title
source: '{{cite journal |title=Err\u200batum: Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Err\u200batum: Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### 2c ZWSP inside a genuine title word
source: '{{cite journal |title=Gene ther\u200bapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene ther\u200bapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "OVERLAP", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_PARTIAL"], "readings": 3}

### 3 Arabic title vs English record [ar]
source: '{{cite journal |title=\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "INCOMPARABLE", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_INCOMPARABLE"], "readings": 1}

### 3b Arabic title plus EQUAL trans-title [ar]
source: '{{cite journal |title=\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a", "Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### 4a |authors=Smith J, Jones K (ar: Authors alias) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |authors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": ["Smith J, Jones K"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 4b |authors=Smith J, Jones K (en: no such alias)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |authors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 4c |people=Smith J, Jones K (en Authors alias)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |people=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": ["Smith J, Jones K"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 5 |vauthors=Smith J, Jones K
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": ["Smith J, Jones K"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### 5b |vauthors=Smith J
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=Smith J}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": ["Smith J"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 6 longer title X: Remarks vs X
source: '{{cite journal |title=X: Remarks}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["X: Remarks"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "LONGER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_EXTENDED"], "readings": 1}

### 6b shorter title
source: '{{cite journal |title=Gene therapy}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

len(source 7) = 16385
### 7 source of 16,385 code points
describe: {"state": "UNAVAILABLE", "reason": "BIB_SOURCE_LIMIT_EXCEEDED"}

len(source 7b) = 16384
### 7b source of 16,384 code points
describe: {"state": "DESCRIBED", "fields": {"titles": ["A"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 8 two templates
source: '{{cite journal |title=X}}{{cite journal |title=Y}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 8b unit span unreadable (data None)
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 8c invalid UTF-8
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 9a every distinct en title alias (18 names)
describe: {"state": "DESCRIBED", "fields": {"titles": ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12", "T13", "T14", "T15", "T16", "T17"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 9b 66 |title= parameters (later replaces earlier)
describe: {"state": "DESCRIBED", "fields": {"titles": ["T64"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 9c 65 |last#= values
describe: {"state": "UNAVAILABLE", "reason": "BIB_VALUE_LIMIT_EXCEEDED"}

### 9d 64 author values (last1..32, author33..64)
describe: {"state": "DESCRIBED", "fields": {"titles": ["X"], "genres": [], "authors": ["Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "

### 9e 64 |last#= plus one |vauthors= (65 together)
describe: {"state": "UNAVAILABLE", "reason": "BIB_VALUE_LIMIT_EXCEEDED"}

### 9f description over 4,096 code points
describe: {"state": "UNAVAILABLE", "reason": "BIB_DESCRIPTION_LIMIT_EXCEEDED"}

### 9g 4,097 code points only through a second Periodical value (work=): 1 + 1 + 4095
describe: {"state": "UNAVAILABLE", "reason": "BIB_DESCRIPTION_LIMIT_EXCEEDED"}

### 10 chapter=Erratum beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Erratum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### 10b chapter=Introduction beside EQUAL title, record title holds a DW word
source: '{{cite book |title=Immune response to vaccine |chapter=Introduction}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Immune response to vaccine", "Introduction"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Immune response to vaccine", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### N4 one-word SHORTER title
source: '{{cite journal |title=Gene}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### N6 BOM before the template
source: '\ufeff{{cite journal |title=X}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

======== Probes of the amended items ========

### A1 vauthors whole-value guard (bib-1 conflict on 'KL' + Arabic comma) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=& KL\u060c}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": ["& KL\u060c"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### A1b author whole-value guard, ASCII separator inside a token
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=x KL;y}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["x KL;y"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### A2 {{lang|en|Comments on X}} as the whole title
source: '{{cite journal |title={{lang|en|Comments on gene therapy for cystic fibrosis}}}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A2b {{lang|en|Comments on}} before the record title
source: '{{cite journal |title={{lang|en|Comments on}} gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A2c template argument in a title
source: '{{cite journal |title={{{1|Comments}}} on X}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A2d parameterless template (now hidden content)
source: '{{cite journal |title=Time{{snd}}Comments}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A2e template with parameters in a recorded family is not checked
source: '{{cite journal |title=X |journal={{lang|en|Nature}}}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["X"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A2f template with parameters in an author value
source: '{{cite journal |title=X |last1={{lang|en|Smith}}}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A3 commented parameter name
source: '{{cite journal |title<!-- x -->=Comments on gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A3b templated parameter name
source: '{{cite journal |{{x}}title=Comments on gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A3c commented name of a parameter of no family
source: '{{cite journal |title=X |url<!-- dead -->=http://example.org}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["X"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A3d entity in a parameter name
source: '{{cite journal |title=X |ti&amp;tle=Y}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### A4 U+3164 (Hangul filler) hiding Erratum beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u3164atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u3164atum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### A4b U+2065 (unassigned default-ignorable) hiding Erratum beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u2065atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u2065atum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### A4c U+3164 inside a genuine title word (boundary reading splits it)
source: '{{cite journal |title=Gene ther\u3164apy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene ther\u3164apy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "OVERLAP", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### A4d variation selector U+FE0F after a title word
source: '{{cite journal |title=Gene\ufe0f therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene\ufe0f therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 3}

### A11 ar host is in authors only [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |host=Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Jones K"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### A15 author with the Arabic conjunction U+0648, Latin-script record [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A15b author 'سميث و جونز' against Arabic record authors 'جون سميث' [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "\u062c\u0648\u0646 \u0633\u0645\u064a\u062b", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A15c same value, Arabic record authors without either name [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["\u0633\u0645\u064a\u062b \u0648 \u062c\u0648\u0646\u0632"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "\u0639\u0644\u064a \u062d\u0633\u0646", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### A6 author 'Smith, John' against record 'John Smith'
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=Smith, John}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Smith, John"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A6b author 'Smith J, Jones K' in one author value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Smith J, Jones K"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### A6c author 'Brown, Ann' against record 'John Smith' (packed part conflicts)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=Brown, Ann}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Brown, Ann"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### A14 DISJOINT title that also designates (both reasons)
source: '{{cite journal |title=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Erratum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "DISJOINT", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_DISJOINT", "BIB_TITLE_RELATED_OBJECT"], "readings": 1}

======== Probes of the second amendment ========

### G1 |type=Erratum beside the record's own title
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Erratum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### G2 |department=Letters beside the record's own title
source: '{{cite journal |title=Gene therapy for cystic fibrosis |department=Letters}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Letters"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### G3 |type=Erratum with no title
source: '{{cite journal |type=Erratum |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": ["Erratum"], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### G4 |type=Letter when the record title holds Letter
source: '{{cite journal |title=Letter to the editor on gene therapy |type=Letter}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Letter to the editor on gene therapy"], "genres": ["Letter"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Letter to the editor on gene therapy", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### G5 ar النوع=تصحيح (type=Correction) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u062a\u0635\u062d\u064a\u062d}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u062a\u0635\u062d\u064a\u062d"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### G6 |type=Research article (no lexicon word)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Research article}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Research article"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### G7 |type=Expression of concern (DP phrase)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |medium=Expression of concern}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Expression of concern"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### H1 {{lc:Comments on}} in a title
source: '{{cite journal |title={{lc:Comments on}} gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H2 {{PAGENAME}} in a title
source: '{{cite journal |title={{PAGENAME}}}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H3 {{snd}} in a title
source: '{{cite journal |title=Time{{snd}}Comments}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H4 <math> in a title
source: '{{cite journal |title=<math>\\text{Comments on}</math> gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H5 <nowiki> in a title (readable, content kept)
source: '{{cite journal |title=<nowiki>[Comments on]</nowiki> gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u200b[Comments on]\u200b gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### H6 <br> in a title (readable)
source: '{{cite journal |title=Gene therapy<br>for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### H7 <ref> in a title
source: '{{cite journal |title=Gene therapy for cystic fibrosis<ref>x</ref>}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H8 template in a genre value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type={{lang|en|Letter}}}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### H9 template in a recorded family (not checked)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |journal={{lang|en|Nature}}}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N1 |url<!-- dead -->= (no family: ignored)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |url<!-- dead -->=http://example.org}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N2 |journal<!-- x -->= (recorded family)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |journal<!-- x -->=Nature}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### N3 |title<!-- x -->= (compared family)
source: '{{cite journal |title<!-- x -->=Comments on gene therapy for cystic fibrosis}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### N4 templated name of no family
source: '{{cite journal |title=Gene therapy for cystic fibrosis |{{x}}url=http://example.org}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### L1 Cyrillic a in a chapter 'Erratum' beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u0430tum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u0430tum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### L2 Cyrillic E in a genre 'Erratum'
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=\u0415rratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u0415rratum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### L3 Cyrillic o in an author name 'Jones' (record Smith; Jones)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |last1=J\u043enes}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["J\u043enes"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### L3b Cyrillic o in an author name, record without authors
source: '{{cite journal |title=Gene therapy for cystic fibrosis |last1=J\u043enes}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["J\u043enes"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### C1 U+0080 inside Erratum beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\x80atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u0080atum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### M1 |title=Cystic fibrosis vs 'Gene therapy for cystic fibrosis'
source: '{{cite journal |title=Cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### M2 the main title alone (record 'Cystic fibrosis: gene therapy outcomes')
source: '{{cite journal |title=Cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### M3 the subtitle alone
source: '{{cite journal |title=Gene therapy outcomes}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy outcomes"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### M4 record 'X (Pub 2)' with cited X
source: '{{cite journal |title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis (Pub 2)", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### M5 first words of a title without separator
source: '{{cite journal |title=Gene therapy}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### M6 main title before a question mark
source: '{{cite journal |title=Is gene therapy safe}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Is gene therapy safe"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Is gene therapy safe? A randomised trial", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

======== Remaining paths (see the notes) ========

### P1 comment inside a designation word of a second title value
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err<!-- -->atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200batum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### P2 <nowiki/> inside a designation word of a second title value
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err<nowiki/>atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200b\u200batum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### P3 ZWSP inside a genre value (genres are not read under the three readings)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err\u200batum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u200batum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### P3b comment inside a genre value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err<!-- -->atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u200batum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### P4 Persian yeh in an Arabic genre word (تعلیق) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u062a\u0639\u0644\u06cc\u0642}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u062a\u0639\u0644\u06cc\u0642"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### P5 Arabic genre 'letter' (رسالة) is not in the lexicon [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u0631\u0633\u0627\u0644\u0629}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u0631\u0633\u0627\u0644\u0629"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### P5b Arabic genre 'editorial article' (مقال افتتاحي) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u0645\u0642\u0627\u0644 \u0627\u0641\u062a\u062a\u0627\u062d\u064a}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u0645\u0642\u0627\u0644 \u0627\u0641\u062a\u062a\u0627\u062d\u064a"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### P6 same-script look-alike (small capital A, U+1D00) in a chapter
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u1d00tum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u1d00tum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### P6b same-script look-alike (dotless i, U+0131) in a genre
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Correct\u0131on}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Correct\u0131on"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### P7 generic main title of another work (record 'Cystic fibrosis: gene therapy outcomes')
source: '{{cite journal |title=Cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### P8 genre word naming a distinct same-titled object (|type=Conference abstract)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Conference abstract}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Conference abstract"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### P9 Japanese title (kanji + kana is mixed)
source: '{{cite journal |title=\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76 |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76", "Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

======== Probes of amendments B1 to B7 ========

-- B1: comments and nowiki --

### B1a comment inside Erratum in a chapter beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err<!-- -->atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200batum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B1b comment inside Erratum in the only title (record has no such word)
source: '{{cite journal |title=Err<!-- -->atum: Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Err\u200batum: Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B1c <nowiki/> inside Erratum in a chapter
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err<nowiki/>atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200b\u200batum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B1d comment inside a genuine title word
source: '{{cite journal |title=Gene ther<!-- -->apy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene ther\u200bapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "OVERLAP", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_PARTIAL"], "readings": 3}

### B1e trailing comment after an EQUAL title
source: '{{cite journal |title=Gene therapy for cystic fibrosis<!-- dead link -->}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis\u200b"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 3}

### B1f title wrapped in nowiki
source: '{{cite journal |title=<nowiki>Gene therapy for cystic fibrosis</nowiki>}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u200bGene therapy for cystic fibrosis\u200b"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 3}

### B1g title of a comment only (absent)
source: '{{cite journal |title=<!-- x --> |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### B1h title of <nowiki/> only (absent)
source: '{{cite journal |title=<nowiki/>}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### B1i title of an invisible entity only (absent)
source: '{{cite journal |title=&#8203;&shy;}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### B1j comment inside Erratum in a genre value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err<!-- -->atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u200batum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B1k <nowiki/> inside Erratum in a genre value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err<nowiki/>atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u200b\u200batum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B1l comment nested in an inline tag (joined only)
source: "{{cite book |title=Gene therapy for cystic fibrosis |chapter=''Err<!-- -->atum''}}"
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Erratum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B1m comment inside a genuine surname
source: '{{cite journal |title=Gene therapy for cystic fibrosis |last1=Sm<!-- -->ith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Sm\u200bith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 3}

### B1n comment between surname and initials
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=Smith<!-- -->J}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Smith\u200bJ"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 3}

### B1o <br> inside a title word (space, as bib-1)
source: '{{cite journal |title=Gene ther<br>apy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene ther apy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "OVERLAP", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_PARTIAL"], "readings": 1}

-- B2: genre values under the three readings --

### B2a ZWSP inside Erratum in a genre value
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err\u200batum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u200batum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 3}

### B2b soft hyphen inside Letter, record title holds 'letter'
source: '{{cite journal |title=Gene therapy for cystic fibrosis: a letter |type=Let\xadter}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis: a letter"], "genres": ["Let\u00adter"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis: a letter", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 3}

### B2c ZWSP only in a genre value: readings = 3
source: '{{cite journal |title=Gene therapy for cystic fibrosis: a letter |type=Letter\u200b}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis: a letter"], "genres": ["Letter\u200b"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis: a letter", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 3}

-- B3: unmatched genre values --

### B3a |type=Research article
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Research article}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Research article"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3b |type=Conference abstract
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Conference abstract}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Conference abstract"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3c |type=Preprint
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Preprint}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Preprint"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3d ar genre 'letter' (رسالة) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u0631\u0633\u0627\u0644\u0629}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u0631\u0633\u0627\u0644\u0629"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3e Persian yeh in an Arabic lexicon word (تعلیق) [ar]
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0646\u0648\u0639=\u062a\u0639\u0644\u06cc\u0642}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u062a\u0639\u0644\u06cc\u0642"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3f |type=Letter, record title holds 'letter'
source: '{{cite journal |title=Gene therapy for cystic fibrosis: a letter |type=Letter}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis: a letter"], "genres": ["Letter"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis: a letter", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B3g |department=Letters, record title lacks it
source: '{{cite journal |title=Gene therapy for cystic fibrosis |department=Letters}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Letters"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B3h genre of punctuation only (no word)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=\u2014}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u2014"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B3i genre without a cited title
source: '{{cite journal |type=Journal article |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": ["Journal article"], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B3j genre without a record title
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Letter}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Letter"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": null, "authors": "John Smith"}
compare: {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B3k |medium=Print
source: '{{cite journal |title=Gene therapy for cystic fibrosis |medium=Print}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Print"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

-- B4: every title value must agree --

### B4a |title=T |chapter=Remarks
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Remarks}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Remarks"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### B4b |title=T |trans-title=T: remarks
source: '{{cite journal |title=Gene therapy for cystic fibrosis |trans-title=Gene therapy for cystic fibrosis: remarks}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Gene therapy for cystic fibrosis: remarks"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### B4c Arabic title plus EQUAL trans-title [ar]
source: '{{cite journal |title=\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a", "Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### B4d two EQUAL values
source: '{{cite journal |title=Gene therapy for cystic fibrosis |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B4e main title plus full title (pair EQUAL, no B5)
source: '{{cite journal |title=Cystic fibrosis |trans-title=Cystic fibrosis: gene therapy outcomes}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis", "Cystic fibrosis: gene therapy outcomes"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B4f main title plus subtitle as chapter
source: '{{cite book |title=Cystic fibrosis |chapter=Gene therapy outcomes}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis", "Gene therapy outcomes"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### B4g Japanese title plus EQUAL trans-title
source: '{{cite journal |title=\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76 |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76", "Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_VALUES_DIFFER"], "readings": 1}

### B4h EQUAL title plus a value of punctuation only (skipped)
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=\u2014}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "\u2014"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

-- B5: a main title alone needs an agreeing author --

### B5a main title, agreeing author
source: '{{cite journal |title=Cystic fibrosis |last1=Smith |first1=John}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B5b main title, no author
source: '{{cite journal |title=Cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### B5c main title, packed author value
source: '{{cite journal |title=Cystic fibrosis |author=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith J, Jones K"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### B5d main title, conflicting author
source: '{{cite journal |title=Cystic fibrosis |last1=Jones}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Jones"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### B5e main title, Vancouver author
source: '{{cite journal |title=Cystic fibrosis |vauthors=Smith J}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": ["Smith J"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B5f X (Pub 2), no author
source: '{{cite journal |title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis (Pub 2)", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_SHORTENED"], "readings": 1}

### B5g X (Pub 2), agreeing author
source: '{{cite journal |title=Gene therapy for cystic fibrosis |last=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis (Pub 2)", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B5h main title, author agreeing only through a middle name
source: '{{cite journal |title=Cystic fibrosis |last1=Paul}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Paul"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Paul Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B5i main title, author agreeing under one reading only (ZWSP in surname)
source: '{{cite journal |title=Cystic fibrosis |last1=Sm\u200bith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Sm\u200bith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: gene therapy outcomes", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 3}

-- B6: augmented script sets --

### B6a Japanese title EQUAL to a Japanese record
source: '{{cite journal |title=\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76", "authors": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B6b Japanese main title of a Japanese record, Japanese author agreeing
source: '{{cite journal |title=\u907a\u4f1d\u5b50\u6cbb\u7642 |last1=\u5c71\u7530}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u907a\u4f1d\u5b50\u6cbb\u7642"], "genres": [], "authors": ["\u5c71\u7530"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "\u907a\u4f1d\u5b50\u6cbb\u7642: \u56a2\u80de\u6027\u7dda\u7dad\u75c7", "authors": "\u592a\u90ce \u5c71\u7530"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B6c Korean title EQUAL
source: '{{cite journal |title=\uc720\uc804\uc790 \uce58\ub8cc \uc5f0\uad6c}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\uc720\uc804\uc790 \uce58\ub8cc \uc5f0\uad6c"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "\uc720\uc804\uc790 \uce58\ub8cc \uc5f0\uad6c", "authors": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B6d Cyrillic a in Erratum (chapter)
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u0430tum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u0430tum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B6e Japanese genre word not in record title
source: '{{cite journal |title=\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76 |type=\u8ad6\u6587}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76"], "genres": ["\u8ad6\u6587"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "\u907a\u4f1d\u5b50\u6cbb\u7642\u306e\u7814\u7a76", "authors": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B6f Latin plus kanji word in an extra word (mixed)
source: '{{cite journal |title=DNA\u89e3\u6790 gene therapy}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["DNA\u89e3\u6790 gene therapy"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "gene therapy", "authors": null}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

-- B7: Latin look-alike skeleton --

### B7a small capital A in Erratum (chapter)
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u1d00tum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u1d00tum"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B7b dotless i in Correction (genre)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Correct\u0131on}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Correct\u0131on"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B7c ERRATUM in small capitals (genre)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=\u1d07\u0280\u0280\u1d00\u1d1b\u1d1c\u1d0d}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["\u1d07\u0280\u0280\u1d00\u1d1b\u1d1c\u1d0d"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B7d DP with a small capital C (genre)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Expression of \u1d04oncern}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Expression of \u1d04oncern"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B7e Latin alpha (U+0251) in Erratum (genre): not skeletonised
source: '{{cite journal |title=Gene therapy for cystic fibrosis |type=Err\u0251tum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": ["Err\u0251tum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_GENRE_UNMATCHED"], "readings": 1}

### B7f record subtitle ERRATUM in small capitals, main title cited with agreeing author
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: \u1d07\u0280\u0280\u1d00\u1d1b\u1d1c\u1d0d", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "SHORTER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### B7g record subtitle with small capital I with stroke (U+1D7B) in correction
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: correct\u1d7bon", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B7h record subtitle with dental click (U+01C0) for l in letter
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: \u01c0etter", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B7i record subtitle with digit zero in correction
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: c0rrection", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### B7j record subtitle 'retracted article' (no lexicon word)
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis (Retracted article)", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

-- remaining paths --

### R1 identically titled letter recorded under the article's title, no cited author
source: '{{cite journal |title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "Ann Wu"}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R2 record subtitle naming another version (an update), agreeing author
source: '{{cite journal |title=Cystic fibrosis |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Cystic fibrosis"], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Cystic fibrosis: an update", "authors": "John Smith"}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R3 |series=Retraction notices (not read)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |series=Retraction notices}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R4 |version=Erratum (not read)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |version=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R5 |at=Erratum (not read)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |at=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R6 |book-title=Letters (not read)
source: '{{cite book |title=Gene therapy for cystic fibrosis |book-title=Letters}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R7 |journal={{lc:Comments}} (recorded family, not checked)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |journal={{lc:Comments}}}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "genres": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### R8 no title, no genre, agreeing author (identifiers decide)
source: '{{cite journal |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "genres": [], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### non-dict inputs
{"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1} {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}
### unknown wiki
ValueError unknown wiki for the bibliographic profile: 'fr'
```
