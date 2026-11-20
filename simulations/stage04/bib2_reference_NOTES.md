# bib2_reference.py and dt4_reference.py: notes

Written from `docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md` (as amended on 2026-11-20: designation
is checked for every title value whose relation is not EQUAL, DISJOINT included), `BIBLIOGRAPHIC_SPEC.md` section 2.1
step 4 and section 3 (which bib-2 declares unchanged), the earlier independent `bib_reference.py` (parsing, cleaning and
word code copied), `bib-reference-profile.json` (the independently extracted alias profile, reused) and
`dt3_reference.py`. No production code, production test or other final-cycle document was opened. The readings taken
where the text leaves a choice are listed in the module docstring of `bib2_reference.py` (R1 to R20); this file lists
the points where the specification is ambiguous, contradictory or unsafe. Nothing below is fixed in the model: the
model implements the text as read.

Rating used: **POSITIVE+** = the point can make a positive more likely (a genuine-looking but different publication
reported positive, or an unavailable check read as natural absence); **NEUTRAL** = changes reports or fail-closed
costs only; **COST** = fail-closed recall cost not (or not fully) stated in section 9.

## (a) Ambiguities and defects

### A1. Section 8, B4 does not hold as stated for author values (POSITIVE+ relative to dt-3; low realism)

B4 claims: for every pair, if bib-2's result is COMPATIBLE or INSUFFICIENT under both readings, bib-1's result is not
MATERIAL_CONFLICT. It fails. The initials test of section 3.2 strips only trailing ASCII `,` and `;`, and the bib-1
value is one token string, whereas bib-2 splits the value at `;`, `؛` (and `,`, `،` for `vauthors`) first. A token of
one to three capitals glued to an Arabic separator (`KL،`, `KL؛`) or followed by a separator inside the token
(`KL;y`) is a name word `kl` for bib-1 (not initials) but becomes initials, and is removed, once bib-2 has split there.
When that word was bib-1's only conflicting word and the rest of the bib-2 part has no name word, bib-1 gives
MATERIAL_CONFLICT and bib-2 gives COMPATIBLE: dt-3 abstains (D-13a) and dt-4 reports a positive (D-14).

- `{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=& KL،}}` (ar) against record title "Gene therapy
  for cystic fibrosis", authors "John Smith": bib-1 MATERIAL_CONFLICT (`BIB_AUTHORS_DISJOINT`), bib-2 COMPATIBLE.
- `|author=x KL؛` (ar) and `|author=x KL;y` (en), same record: same result (log N8, N8b).

A randomized differential of the two reference models (random author, title and record strings over a small
vocabulary with separators, initials and format characters) found 6 violations in 100,000 pairs (seed 7) and 16 in
300,000 (seed 11), all of this author kind; none on the title side. bib-1's conflict here is itself spurious (it reads
initials as a surname), so the practical risk is small, but a B4 test over such inputs fails against any
implementation that follows section 3.2 and 4.1 literally. Fix options for the owner: state B4 with this exception, or
strip `؛` and `،` in the initials test as well (that changes bib-2 and still leaves the inner-separator case).

### A2. Section 2.1 steps 5 and 6 against P4: a description the cleaning cannot read is natural absence (POSITIVE+)

P4 says "a description that exists but cannot be checked does block", but step 5 makes an empty cleaned value an absent
value, and the cleaning removes templates. A title wrapped in a template is therefore MISSING, not UNAVAILABLE, and the
unit decides by identifiers alone:

- `{{cite journal |title={{lang|en|Comments on gene therapy for cystic fibrosis}}}}`: fields `titles: []`, compare
  INSUFFICIENT (log N2), so dt-4 can report a positive although the citation names a comment.
- Worse, a partial removal: `|title={{lang|en|Comments on}} gene therapy for cystic fibrosis` is cleaned to the record
  title, EQUAL, COMPATIBLE (log N2b). (bib-1 behaved the same; bib-2's section 9 lists only the template-free cases.)

### A3. Section 2.1 step 4: a parameter name with a comment matches no alias (POSITIVE+)

`name = str(param.name).strip()` keeps an HTML comment (and any template) inside the name; MediaWiki removes comments
before it reads template arguments, so CS1 renders `|title<!-- x -->=Comments on …` as the title. The engine sees no
title: `{{cite journal |title<!-- x -->=Comments on gene therapy for cystic fibrosis}}` is DESCRIBED with no title,
INSUFFICIENT (log N1), natural absence.

### A4. Section 3.1: invisible characters outside category Cf are not read (POSITIVE+, adversarial)

G-04 is limited to general category Cf. Default-ignorable (invisible) code points of other categories are not covered:
unassigned default-ignorables such as U+2065 (Cn: a separator under both readings) and the Hangul fillers U+115F,
U+1160, U+3164, U+FFA0 (Lo: a word character, glued into the word under both readings). Each hides a designation word
in both readings. Since a LONGER, OVERLAP or INCOMPARABLE chosen value abstains anyway, the effect is on a second title
value beside an EQUAL one (and on a SHORTER value's record side): `{{cite book |title=Gene therapy for cystic fibrosis
|chapter=Err<U+2065>atum}}` (U+2065) and `|chapter=Err<U+3164>atum` (U+3164) are COMPATIBLE, while `|chapter=Erratum` and the ZWSP
form `|chapter=Err<U+200B>atum` are MATERIAL_CONFLICT (log N3, N3b, 10, 2). I checked over the Unicode 15.0 database of the
venv's Python 3.12.3: no Cf code point is a word character, and no non-Cf code point folds (NFKD + casefold) to a Cf
one, so the Cf readings themselves are consistent.

### A5. Section 4.2: SHORTER has no minimum, so one shared word establishes the object (POSITIVE+)

P6 asks for strong evidence of identity, but SHORTER is any contiguous shorter subsequence, a single word included:
`|title=Gene` against "Gene therapy for cystic fibrosis" is SHORTER, AGREE, COMPATIBLE (log N4). A different
publication whose (short) title is a contiguous part of the record's title ("Diabetes mellitus" against a retracted
"Diabetes mellitus in children: a review" reached through a wrong DOI) is reported positive unless an author conflicts.
This is the text's explicit rule, so it is a design choice, but it is the weakest relation that still establishes.

### A6. Section 4.1: the person/packed distinction never changes the object verdict; packed lists still hide non-authors (POSITIVE+, inherited from bib-1)

A person part and a packed part conflict under the same condition (`N ∩ S_R = ∅`); they differ only in AGREE versus
undetermined, and section 5 never uses AGREE. So A-02's "a packed value agrees with nothing" has no effect on dt-4
decisions. What remains is bib-1's residual: a value holding one record author and one non-author never conflicts,
whatever its form. `|authors=Smith J, Jones K` (ar, `author_lists`, packed) and `|author=Smith J, Jones K` (one comma,
read as "Surname, Given", a person part with N = {smith, jones}) against authors "John Smith" are both COMPATIBLE (log
4a, N9); only the `vauthors` form splits at the comma and conflicts (log 5). A note by Jones and Smith with the record's
title (EQUAL) is therefore positive when its authors are written in one `|author=` or `|authors=` value.

### A7. Profile: en has no `authors` alias, and unknown names are silently ignored (POSITIVE+, removes refutation only)

The en CS1 configuration lists only `credits` and `people` under Authors, so `|authors=Smith J, Jones K` on en is not a
field at all (log 4b); likewise any misspelled or unknown author parameter. Authors can only refute, so a dropped
author value can only remove a conflict. (CS1 itself does not render an unknown parameter, so this follows the wiki;
it is a lost refutation, not a lost description.)

### A8. Section 3.2 against 4.1: record authors are split at ASCII `;` only (POSITIVE+, slight)

The cited side splits at `;` and `؛`, `S_R` only at `;`. A record author list written with Arabic semicolons is one part
whose first name word only is dropped, so the other given names enter `S_R` and can agree by accident. Stage 02 records
(Retraction Watch) use ASCII `;`, so this is theoretical.

### A9. Section 4.2 (amended) and section 9: a second title value blocks whenever the record title holds a lexicon word (COST)

With DISJOINT and INCOMPARABLE values checked, their record extra words are all words of `T_R` not in `T`. Any second
title value (a chapter, a series, an Arabic original beside an English `trans-title`) beside an EQUAL value makes the
pair MATERIAL_CONFLICT when the record title holds any of `DW`, including common biomedical words such as "response",
"discussion", "correction", "removal", "letter" or "re": `{{cite book |title=Immune response to vaccine
|chapter=Introduction}}` against "Immune response to vaccine" is MATERIAL_CONFLICT (log 10b). Section 9 states the
case for "a retracted work whose own title holds a lexicon word"; the size of the cost on Arabic-wiki citations with an
Arabic `title` and an English `trans-title` should be measured in `REGRESSION_DT4.md`.

### A10. Section 2.1 step 7: what the 4,096 code-point total counts (NEUTRAL near the bound, but it decides blocking)

"All values of all families of step 6" can be read as every value of every family, or as the fields recorded (titles,
author values and the first value of each single family). It also leaves open whether ScriptTitle/ScriptChapter values
count before or after the prefix removal. The model counts every value of every family (bib-1 said "all values, not
only the first") and titles after prefix removal (R9). Near the bound one reading gives UNAVAILABLE (blocks, D-13b) and
the other DESCRIBED (may be positive), so production and model must agree on one reading.

### A11. Section 2.1 step 6: a name in two families (NEUTRAL)

In the ar profile `host` matches AuthorList-Last (`host#` with empty `#`) and Authors (`host`). The text does not say
which form it takes. The model puts it in both `authors` and `author_lists` and counts it twice for the 64-value bound
(R7; log N5). Conflict detection is the same in both forms, so only AGREE reporting and the bound are affected.

### A12. Section 2.1 step 7: the 64-title bound cannot be reached (NEUTRAL)

A later parameter of the same name replaces the earlier one and the title aliases have no `#`, so the number of title
values is at most the number of distinct title aliases: 18 on en, 26 on ar (log 9a, 9b). Only the author bound can
fire (log 9c, 9e).

### A13. Section 3.1: "Periodical and year are read from the reported reading" (NEUTRAL)

The joined reading edits only the cited titles, cited authors, record title and record authors, so periodical and year
are the same under both readings; the sentence suggests otherwise. A format character in a periodical or date does not
make two readings.

### A14. Sections 4.2 and 5: reasons when the chosen relation is DISJOINT and some value designates (NEUTRAL)

Section 4.2 is an else-chain (designation, else DISJOINT); section 5 attaches each reason to its own condition. With
the amendment a DISJOINT value can itself designate (`|title=Erratum` against "Gene therapy"), so both conditions hold
often. The model gives both `BIB_TITLE_DISJOINT` and `BIB_TITLE_RELATED_OBJECT` (R17).

### A15. Section 2.1 steps 1 and 3: smaller points (NEUTRAL or fail closed)

- Strict UTF-8 decoding keeps a leading byte-order mark as U+FEFF, a non-whitespace top-level Text node: BIB_PARSE_FAILED
  (log N6). Fail closed.
- "Any exception raised while … cleaning a value": which values are cleaned is not said. The model cleans only the
  effective values of family arguments (R4). No input that makes `strip_code` raise is known.
- A conjunction is "`&` or a whitespace token that casefolds to `and`": the model takes `&` anywhere in the piece (R13).
  The Arabic conjunction `و` is not a conjunction (log N7). Reporting only (A6).
- Engine configuration (unknown wiki, malformed profile, parser version other than 0.7.2, inactive C tokenizer) raises
  in the model rather than giving UNAVAILABLE (R1), following the last paragraph of 2.1 and 2.2.
- A record with no title (natural absence, P4) lets a cited "Erratum: X" decide by identifiers unless an author
  conflicts; this is stated in section 9 and kept.

### dt-4 model

`dt4_reference.py` is `dt3_reference.py` with: the docstring rewritten for dt-4; `MODEL_VERSION = "dt4-reference/1"`,
`TABLE_VERSION = "dt-4"`; a new constant `BIB_STATES = ("NONE", "CONFLICT", "UNAVAILABLE", "NOT_ESTABLISHED")`;
`Case.bc: bool = False` replaced by `Case.bib: str = "NONE"` (same position, also in `key()`); `RULES` with D-13a,
D-13b, D-13c between D-13 and D-14; `TIER` with D-13b and D-13c at 7 (the tier of D-13a and D-14, same guard); guards
D-13a/b/c = the D-14 guard and `bib == "CONFLICT"` / `"UNAVAILABLE"` / `"NOT_ESTABLISHED"`; decide branches giving
UNRESOLVED_IDENTITY with `BIBLIOGRAPHIC_OBJECT_CONFLICT` / `BIBLIOGRAPHIC_CHECK_UNAVAILABLE` /
`BIBLIOGRAPHIC_OBJECT_NOT_ESTABLISHED`, then the unchanged common tail, status and value. Like `bc`, `bib` is not
validated: a value outside `BIB_STATES` behaves as NONE. The `oracle-dt3` directory and `decision_space_dt3.py` were not
copied or changed. A differential run over 200,000 random cases (seed 1, every lookup value, positives favoured)
compared dt-4 with dt-3: `bib` NONE/CONFLICT equal to `bc` False/True in every case; `bib` UNAVAILABLE/NOT_ESTABLISHED
equal to dt-3 with `bc` False except where dt-3 gives D-14, where dt-4 gives D-13b (394 cases) / D-13c (469 cases),
UNRESOLVED_IDENTITY, status uncertain, value null, and D-13a's reasons with the general reason replaced. Output:
`cases 200000 diffs 0 {'D-13c': 469, 'D-13b': 394}`.

## (b) Self-test log

Produced by a scratch script (not kept in the repository) that calls `describe(source.encode("utf-8"), wiki, profile)`
with `bib-reference-profile.json` and, for DESCRIBED units with a record, `compare(fields, record)`; output printed with
`json.dumps(..., ensure_ascii=True)` (describe output cut at 600 characters). Run with `uv run python` (Python 3.12.3,
mwparserfromhell 0.7.2, C tokenizer active, Unicode 15.0.0). Wiki is en unless the label says ar.

```text
### 1 soft hyphen (entity) in designation word
source: '{{cite journal |title=Com&shy;ments on X |author=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Com\u00adments on X"], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 2}

### 1b soft hyphen (literal U+00AD) in designation word
source: '{{cite journal |title=Com\xadments on X |author=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Com\u00adments on X"], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 2}

### 2 ZWSP inside designation word, in a chapter beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u200batum |last1=Smith}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u200batum"], "authors": ["Smith"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "AGREE", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 2}

### 2b ZWSP inside designation word of the only title
source: '{{cite journal |title=Err\u200batum: Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Err\u200batum: Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "LONGER", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 2}

### 2c ZWSP inside a genuine title word (EQUAL under joined, not under split)
source: '{{cite journal |title=Gene ther\u200bapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene ther\u200bapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "OVERLAP", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_PARTIAL"], "readings": 2}

### 3 Arabic title vs English record
source: '{{cite journal |title=\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a \u0644\u0644\u062a\u0644\u064a\u0641 \u0627\u0644\u0643\u064a\u0633\u064a"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "INCOMPARABLE", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_INCOMPARABLE"], "readings": 1}

### 3b Arabic title plus EQUAL trans-title
source: '{{cite journal |title=\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a |trans-title=Gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["\u0627\u0644\u0639\u0644\u0627\u062c \u0627\u0644\u062c\u064a\u0646\u064a", "Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 4a |authors=Smith J, Jones K (ar: Authors alias)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |authors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": ["Smith J, Jones K"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 4b |authors=Smith J, Jones K (en: no such alias in the profile)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |authors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 4c |people=Smith J, Jones K (en Authors alias)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |people=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": ["Smith J, Jones K"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 5 |vauthors=Smith J, Jones K
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": ["Smith J, Jones K"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### 5b |vauthors=Smith J (agrees)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=Smith J}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": ["Smith J"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### 6 longer title X: Remarks vs X
source: '{{cite journal |title=X: Remarks}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["X: Remarks"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "X", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "NOT_ESTABLISHED", "title_relation": "LONGER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "NOT_ESTABLISHED", "reasons": ["BIB_TITLE_EXTENDED"], "readings": 1}

### 6b shorter title
source: '{{cite journal |title=Gene therapy}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

len(source 7) = 16385
### 7 source of 16,385 code points
describe: {"state": "UNAVAILABLE", "reason": "BIB_SOURCE_LIMIT_EXCEEDED"}

len(source 7b) = 16384
### 7b source of 16,384 code points
describe: {"state": "DESCRIBED", "fields": {"titles": ["A"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 8 two templates
source: '{{cite journal |title=X}}{{cite journal |title=Y}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 8b unit span unreadable (data None)
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 8c invalid UTF-8
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### 9a every distinct en title alias (18 names): the 64-title bound cannot be reached
describe: {"state": "DESCRIBED", "fields": {"titles": ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12", "T13", "T14", "T15", "T16", "T17"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 9b 66 |title= parameters (same name: later replaces earlier)
describe: {"state": "DESCRIBED", "fields": {"titles": ["T64"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}

### 9c 65 |last#= values
describe: {"state": "UNAVAILABLE", "reason": "BIB_VALUE_LIMIT_EXCEEDED"}

### 9d 64 author values (last1..32, author33..64)
describe: {"state": "DESCRIBED", "fields": {"titles": ["X"], "authors": ["Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith", "Smith

### 9e 64 |last#= plus one |vauthors= (65 together)
describe: {"state": "UNAVAILABLE", "reason": "BIB_VALUE_LIMIT_EXCEEDED"}

### 9f description over 4,096 code points
describe: {"state": "UNAVAILABLE", "reason": "BIB_DESCRIPTION_LIMIT_EXCEEDED"}

### 10 amended 4.2: chapter=Erratum beside an EQUAL title
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Erratum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Erratum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### 10b chapter=Introduction beside EQUAL title, record title holds a DW word
source: '{{cite book |title=Immune response to vaccine |chapter=Introduction}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Immune response to vaccine", "Introduction"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Immune response to vaccine", "authors": null, "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "CONFLICT", "title_relation": "EQUAL", "designation": true, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_TITLE_RELATED_OBJECT"], "readings": 1}

### N1 comment in a parameter name (MediaWiki strips comments; the spec keeps them)
source: '{{cite journal |title<!-- x -->=Comments on gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### N2 title wrapped in a template the cleaning removes
source: '{{cite journal |title={{lang|en|Comments on gene therapy for cystic fibrosis}}}}'
describe: {"state": "DESCRIBED", "fields": {"titles": [], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}

### N2b designation inside a template the cleaning removes, rest equals the record title
source: '{{cite journal |title={{lang|en|Comments on}} gene therapy for cystic fibrosis}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N3 unassigned default-ignorable U+2065 inside a designation word of a second value
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u2065atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u2065atum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N3b Hangul filler U+3164 (category Lo) inside a designation word of a second value
source: '{{cite book |title=Gene therapy for cystic fibrosis |chapter=Err\u3164atum}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis", "Err\u3164atum"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N4 one-word SHORTER title establishes the object
source: '{{cite journal |title=Gene}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene"], "authors": [], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith; Kate Jones", "journal": "Nature", "original_year": 2001}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "SHORTER", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N5 ar host matches two author families
source: '{{cite journal |title=Gene therapy for cystic fibrosis |host=Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": ["Jones K"], "author_lists": ["Jones K"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "CONFLICT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "MATERIAL_CONFLICT", "reasons": ["BIB_AUTHORS_DISJOINT"], "readings": 1}

### N6 BOM before the template
source: '\ufeff{{cite journal |title=X}}'
describe: {"state": "UNAVAILABLE", "reason": "BIB_PARSE_FAILED"}

### N7 Arabic standalone conjunction و is not a conjunction
source: '{{cite journal |title=Gene therapy for cystic fibrosis |\u0627\u0644\u0645\u0624\u0644\u0641\u0648\u0646=Smith \u0648 Jones}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": ["Smith \u0648 Jones"], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N8 B4 counterexample (bib-1 conflicts on KL followed by an Arabic comma)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |vauthors=& KL\u060c}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": [], "author_lists": [], "vauthors": ["& KL\u060c"], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N8b B4 counterexample (ASCII separator inside a token)
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=x KL;y}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": ["x KL;y"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "INSUFFICIENT", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### N9 single-comma author value packing two people reads as a person
source: '{{cite journal |title=Gene therapy for cystic fibrosis |author=Smith J, Jones K}}'
describe: {"state": "DESCRIBED", "fields": {"titles": ["Gene therapy for cystic fibrosis"], "authors": ["Smith J, Jones K"], "author_lists": [], "vauthors": [], "periodical": null, "date": null, "year": null, "volume": null, "issue": null, "pages": null}}
record: {"title": "Gene therapy for cystic fibrosis", "authors": "John Smith", "journal": null, "original_year": null}
compare: {"authors": "AGREE", "title": "AGREE", "title_relation": "EQUAL", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "COMPATIBLE", "reasons": [], "readings": 1}

### non-dict inputs
{"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1} {"authors": "INSUFFICIENT", "title": "INSUFFICIENT", "title_relation": "MISSING", "designation": false, "year": "INSUFFICIENT", "periodical": "INSUFFICIENT", "volume": "NOT_IN_RECORD", "issue": "NOT_IN_RECORD", "pages": "NOT_IN_RECORD", "object": "INSUFFICIENT", "reasons": [], "readings": 1}
### unknown wiki
ValueError unknown wiki for the bibliographic profile: 'fr'
```
