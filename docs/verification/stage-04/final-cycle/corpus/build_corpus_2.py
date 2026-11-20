"""Builds BIB2_CORPUS.json: the fail-first adversarial corpus of bib-2 (owner decisions D-086 and D-087).

Every case of the bib-1 corpus (``build_corpus.py``, unchanged) is kept with the same source and record and gets the
verdict BIBLIOGRAPHIC_SPEC_2.md requires (``BIB1_EXPECT_2``); ``bib1_expect`` keeps the bib-1 verdict beside it, so the
change of every case is visible. New cases cover D-086 (a check that is unavailable: source, value and description
bounds, parse failure, each on a Garry-style conflict and on genuine citations at the bound) and D-087 (G-04 format
characters, in English and Arabic, on designations and on genuine titles and surnames; A-02 weak compatibility: a
commenter sharing a surname, no comparable author, packed multi-person values, a non-lexicon designation, a strict
superset title). All verdicts were written down from the specification before the production and reference outputs
were compared with them. Every new case is SYNTHETIC or a constructed variant of a development record (``origin``);
no label, adjudication or score of any campaign is used. Run: ``python build_corpus_2.py`` (writes BIB2_CORPUS.json).

The free-form author list (CS1 Authors) is ``people=`` or ``credits=`` on en (en's configuration no longer has
``authors=``, which is an ar alias): the first draft of five A-02 cases used ``authors=`` on en, which is no field
there; that was an error of the cases, corrected before any production change, and is recorded in REGRESSION_DT4.md.

Expectation fields: ``object`` and ``reasons`` always; ``unavailable`` (the D-086 reason) for a case whose check is
UNAVAILABLE, in which case nothing is compared; otherwise any of ``authors``, ``title``, ``title_relation``,
``designation``, ``readings``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_corpus as B1  # noqa: E402

MC, CO, IN, NE, UN = "MATERIAL_CONFLICT", "COMPATIBLE", "INSUFFICIENT", "NOT_ESTABLISHED", "UNAVAILABLE"
RA, RT, RR = "BIB_AUTHORS_DISJOINT", "BIB_TITLE_DISJOINT", "BIB_TITLE_RELATED_OBJECT"
EXT, PAR, INC = "BIB_TITLE_EXTENDED", "BIB_TITLE_PARTIAL", "BIB_TITLE_INCOMPARABLE"
SHO = "BIB_TITLE_SHORTENED"
VAL, GEN = "BIB_TITLE_VALUES_DIFFER", "BIB_GENRE_UNMATCHED"
U_PARSE, U_SOURCE = "BIB_PARSE_FAILED", "BIB_SOURCE_LIMIT_EXCEEDED"
U_VALUES, U_DESC = "BIB_VALUE_LIMIT_EXCEEDED", "BIB_DESCRIPTION_LIMIT_EXCEEDED"


def ex(obj: str, reasons: tuple[str, ...] = (), **fields: Any) -> dict[str, Any]:
    return {"object": obj, "reasons": sorted(reasons), **fields}


def unavailable(reason: str) -> dict[str, Any]:
    return {"object": UN, "reasons": [reason], "unavailable": reason}


# bib-2 verdicts of the bib-1 cases (spec sections 2 to 5). CONTAINED splits into SHORTER and LONGER; a LONGER, OVERLAP
# or INCOMPARABLE title without designation is NOT_ESTABLISHED; authors never establish; a template that is not one
# template or is above a bound is UNAVAILABLE; a designation word in any non-EQUAL value conflicts.
BIB1_EXPECT_2: dict[str, dict[str, Any]] = {
    "garry-exact": ex(MC, (RA, RR), authors="CONFLICT", title_relation="LONGER", designation=True),
    "garry-authors-only": ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
    "garry-title-only": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "garry-true-original": ex(
        CO, authors="AGREE", title="AGREE", title_relation="EQUAL", year="SAME", periodical="SAME"
    ),
    "true-original-vauthors": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "punct-case": ex(CO, authors="INSUFFICIENT", title="AGREE", title_relation="EQUAL"),  # comma: packed
    "punct-markup": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "diacritics": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "author-inverted": ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),  # comma: packed (spec 4.1)
    "author-initials-only": ex(CO, authors="INSUFFICIENT", title="AGREE"),
    "truncated-etal": ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),  # comma: packed
    "only-etal": ex(CO, authors="INSUFFICIENT", title="AGREE"),
    # spec 4.2 (M8): a main title without its subtitle never agrees
    "subtitle-truncated": ex(NE, (SHO,), title_relation="SHORTER", designation=False),
    "subtitle-extended": ex(NE, (EXT,), title="NOT_ESTABLISHED", title_relation="LONGER", designation=False),
    "typo-overlap": ex(NE, (PAR,), title="NOT_ESTABLISHED", title_relation="OVERLAP", designation=False),
    "comment-other-authors": ex(MC, (RA, RR), authors="CONFLICT", title_relation="LONGER", designation=True),
    "comment-same-authors": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "reply": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "response-to": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "editorial-genre": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "erratum": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "correction-to": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "corrigendum": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "withdrawal-notice": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "withdrawn-status": ex(NE, (EXT,), title_relation="LONGER", designation=False),
    "retraction-notice": ex(MC, (RR,), authors="INSUFFICIENT", title_relation="LONGER", designation=True),
    "retracted-watermark": ex(NE, (EXT,), title_relation="LONGER", designation=False),
    "eoc-notice": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "retracted-comment-own-title": ex(CO, title="AGREE", title_relation="EQUAL", designation=False),
    "letter-genre-dev": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, year="SAME"),
    "jasist-withdrawal-dev": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "same-title-other-authors": ex(MC, (RA,), title="AGREE", title_relation="EQUAL"),
    "wrong-identifier-dev": ex(MC, (RA,), authors="CONFLICT", title_relation="OVERLAP"),
    "same-authors-disjoint-title": ex(MC, (RT,), authors="AGREE", title_relation="DISJOINT"),
    "disjoint-title-no-authors": ex(MC, (RT,), authors="INSUFFICIENT", title_relation="DISJOINT"),
    # spec 4.2 (M8): no title value is EQUAL (the chapter is a shortened form of the record's title)
    "chapter-in-book-dev": ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER", designation=False),
    "malformed-title-markup-only": unavailable(U_PARSE),  # spec 2.1 step 5: a template with parameters in a title
    "missing-title": ex(MC, (RA,), title_relation="MISSING", periodical="SAME"),
    "missing-title-agree": ex(IN, authors="AGREE", title="INSUFFICIENT", title_relation="MISSING"),
    "missing-author": ex(CO, authors="INSUFFICIENT", title="AGREE"),
    "no-fields": ex(IN, authors="INSUFFICIENT", title_relation="MISSING"),
    "not-a-template": unavailable(U_PARSE),
    "two-templates": unavailable(U_PARSE),
    "oversized-title": unavailable(U_DESC),
    "too-many-authors": unavailable(U_VALUES),
    "at-the-size-bound": ex(MC, (RA, RT), authors="CONFLICT", title_relation="DISJOINT"),
    "sixty-four-authors": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "sixty-four-authors-last-stranger": ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
    "record-malformed": ex(IN, authors="INSUFFICIENT", title_relation="MISSING", year="INSUFFICIENT"),
    "duplicate-param-last-wins": ex(MC, (RT,), title_relation="DISJOINT"),
    "duplicate-param-overrides": ex(CO, title="AGREE", title_relation="EQUAL"),
    "arabic-title-latin-record": ex(NE, (INC,), authors="INSUFFICIENT", title_relation="INCOMPARABLE"),
    "arabic-params-latin-values": ex(CO, authors="AGREE", title="AGREE", year="SAME", periodical="SAME"),
    "arabic-designation": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "arabic-clitic-designation": ex(NE, (EXT,), title_relation="LONGER", designation=False),
    "arabic-indic-year": ex(CO, year="INSUFFICIENT", title_relation="EQUAL"),
    "transliteration": ex(MC, (RA,), authors="CONFLICT"),
    "corporate-author": ex(MC, (RA,), authors="CONFLICT"),
    "markup-snd-boundary": unavailable(U_PARSE),  # spec 2.1 step 5: any template in a compared value
    "markup-pipe-template-boundary": unavailable(U_PARSE),
    "markup-br-boundary": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "markup-ref-content-kept": unavailable(U_PARSE),  # spec 2.1 step 5: a tag other than the readable ones
    "lone-surrogate-entity": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "lone-surrogate-garry-pages": ex(MC, (RA, RR), authors="CONFLICT", title_relation="LONGER", designation=True),
    "caps-surname-only": ex(MC, (RA,), authors="CONFLICT", title_relation="LONGER", designation=False),
    "caps-surname-with-first": ex(MC, (RA,), authors="CONFLICT", title_relation="LONGER"),
    "caps-vauthors": ex(MC, (RA,), authors="CONFLICT", title_relation="LONGER"),
    "caps-surname-genuine": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "inline-subscript": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "inline-italic-inside-a-word": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "re-hyphen-prefix": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "related-note-no-author-residual": ex(
        NE, (EXT,), authors="INSUFFICIENT", title_relation="LONGER", designation=False
    ),
    "oversized-source": unavailable(U_SOURCE),
    "given-name-collision": ex(MC, (RA,), authors="CONFLICT"),
    "vancouver-initials-never-count": ex(MC, (RA,), authors="CONFLICT"),
    "particle-collision": ex(MC, (RA,), authors="CONFLICT"),
    "coauthor-list-one-coincident-name": ex(MC, (RA,), authors="CONFLICT"),
    "re-prefix": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "authors-response": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "plural-corrigenda": ex(MC, (RR,), title_relation="LONGER", designation=True),
    "designation-in-second-title-value": ex(MC, (RR,), title_relation="EQUAL", designation=True),
    "chapter-erratum-disjoint": ex(MC, (RR,), title="CONFLICT", title_relation="EQUAL", designation=True),
    "surrogate-in-author-garry": ex(MC, (RA, RR), authors="CONFLICT", title_relation="LONGER", designation=True),
    "surrogate-in-title-garry": ex(MC, (RA, RR), authors="CONFLICT", title_relation="LONGER", designation=True),
    "surrogate-in-author-commenter": ex(MC, (RA,), authors="CONFLICT", title_relation="LONGER", designation=False),
    "surrogate-in-author-genuine": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "caps-surname-commenter": ex(MC, (RA,), authors="CONFLICT", title_relation="LONGER", designation=False),
    "inline-designation-joined": ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", designation=False),
    "collaboration-param-ignored": ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
}

GARRY, GT, REC, T = B1.GARRY_RECORD, B1.GT, B1.REC, B1.T
DEV_GARRY = "variant of development:en-27958530/un-00004 (real Stage 02 record, constructed citation)"


def cite(**params: str) -> str:
    return B1.cite(**params)


def garry(extra: str = "", title: str = GT + " – Comments", author: str = "Robert Garry") -> str:
    """The P2 Garry template (development evidence) with another title or author and extra parameters."""
    return (
        "{{cite journal\n |author=" + author + "\n |title=" + title + "\n |journal=Virology Journal\n"
        " |date=21 July 2010\n |volume=7\n |issue=1\n |page=169\n |doi=10.1186/1743-422X-7-169\n |pmid=20663162\n"
        " |pmc=2918564\n |s2cid=8124033\n |doi-access=free" + extra + "\n }}"
    )


def true_original(extra: str = "") -> str:
    return "{{cite journal |last1=Hon |last2=Ng |last3=Leung |title=" + GT + " |journal=Virology Journal" + extra + "}}"


def pad_to(source: str, total: int) -> str:
    """``source`` with a ``|quote=`` parameter of x's that makes it exactly ``total`` code points."""
    head = source[: source.rindex("}}")]
    fill = total - len(head) - len(" |quote=") - len("}}")
    if fill < 1:
        raise SystemExit("pad_to: source already too long")
    return head + " |quote=" + "x" * fill + "}}"


def new(cid: str, category: str, source: str, record: Any, expect: dict[str, Any], wiki: str = "en", **kw: str) -> Any:
    return {
        "id": cid,
        "category": category,
        "wiki": wiki,
        "source": source,
        "record": record,
        "expect": expect,
        "origin": kw.get("origin", "synthetic"),
        "note": kw.get("note", ""),
        "requirement": kw.get("requirement", ""),
    }


SHY, ZWSP, ZWNJ, ZWJ, WJ, BOM, RLM, ALM = "\u00ad", "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u200f", "\u061c"
AR_REC = {"title": "الانجراف الحراري في المستشعرات الشبكية", "authors": "سارة أحمد الخطيب;عمر يوسف", "journal": None,
          "original_year": 2015}  # fmt: skip
AR_T = "الانجراف الحراري في المستشعرات الشبكية"


AR_TITLE, AR_TYPE = "\u0639\u0646\u0648\u0627\u0646", "\u0627\u0644\u0646\u0648\u0639"


def ar_cite(**params: str) -> str:
    return "{{استشهاد بدورية محكمة " + " ".join(f"|{k}={v}" for k, v in params.items()) + "}}"


D086 = "D-086"
G04 = "D-087 G-04"
A02 = "D-087 A-02"

NEW_CASES = [
    # D-086: a Garry-style conflict above a bound, or unparsable, never reaches D-14.
    new(
        "garry-oversized-source",
        "unavailable",
        pad_to(garry(), 16385),
        GARRY,
        unavailable(U_SOURCE),
        origin=DEV_GARRY,
        requirement=D086,
        note="c3854b8 read the unit as having no description (C = ⊥) and reached D-14",
    ),
    new(
        "garry-oversized-description",
        "unavailable",
        garry("\n |trans-title=" + "x" * 4000),
        GARRY,
        unavailable(U_DESC),
        origin=DEV_GARRY,
        requirement=D086,
    ),
    new(
        "garry-too-many-values",
        "unavailable",
        garry("".join(f"\n |last{i}=Garry{i}" for i in range(2, 66))),
        GARRY,
        unavailable(U_VALUES),
        origin=DEV_GARRY,
        requirement=D086,
        note="65 author values (author plus last2..last65)",
    ),
    new(
        "garry-unbalanced",
        "unavailable",
        garry()[:-2] + "}",
        GARRY,
        unavailable(U_PARSE),
        origin=DEV_GARRY,
        requirement=D086,
        note="the template is not closed: the parser gives text, not one template",
    ),
    new(
        "garry-trailing-text",
        "unavailable",
        garry() + " Comments.",
        GARRY,
        unavailable(U_PARSE),
        origin=DEV_GARRY,
        requirement=D086,
    ),
    new(
        "garry-not-utf8",
        "unavailable",
        "",
        GARRY,
        unavailable(U_PARSE),
        origin=DEV_GARRY,
        requirement=D086,
        note="source bytes b'\\xff' + the Garry template: not UTF-8 (the case's source_bytes_hex replaces source)",
    ),
    # D-086: genuine citations at each bound: below or at it they are checked, above it they abstain (never positive).
    new(
        "genuine-at-source-bound",
        "unavailable_boundary",
        pad_to(true_original(), 16384),
        GARRY,
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        origin=DEV_GARRY,
        requirement=D086,
    ),
    new(
        "genuine-above-source-bound",
        "unavailable_boundary",
        pad_to(true_original(), 16385),
        GARRY,
        unavailable(U_SOURCE),
        origin=DEV_GARRY,
        requirement=D086,
    ),
    new(
        "genuine-at-value-bound",
        "unavailable_boundary",
        true_original("".join(f" |last{i}=Leung" for i in range(4, 65))),
        GARRY,
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        origin=DEV_GARRY,
        requirement=D086,
        note="64 author values",
    ),
    new(
        "genuine-above-value-bound",
        "unavailable_boundary",
        true_original("".join(f" |last{i}=Leung" for i in range(4, 66))),
        GARRY,
        unavailable(U_VALUES),
        origin=DEV_GARRY,
        requirement=D086,
        note="65 author values",
    ),
    new(
        "genuine-at-description-bound",
        "unavailable_boundary",
        true_original(" |trans-title=" + "y" * (4096 - len(GT) - len("HonNgLeung") - len("Virology Journal"))),
        GARRY,
        ex(NE, (VAL,), authors="AGREE", title_relation="EQUAL"),
        origin=DEV_GARRY,
        requirement=D086,
        note="exactly 4,096 code points over all values: described and compared; the trans-title is DISJOINT, holds no "
        "designation and does not agree (M4), so the pair abstains as NOT_ESTABLISHED, never UNAVAILABLE",
    ),
    new(
        "genuine-above-description-bound",
        "unavailable_boundary",
        true_original(" |trans-title=" + "y" * (4097 - len(GT) - len("HonNgLeung") - len("Virology Journal"))),
        GARRY,
        unavailable(U_DESC),
        origin=DEV_GARRY,
        requirement=D086,
    ),
    new(
        "empty-template-is-natural-absence",
        "natural_absence",
        "{{cite journal |doi=10.5555/x}}",
        REC,
        ex(IN, authors="INSUFFICIENT", title_relation="MISSING"),
        requirement=D086,
        note="a template with no title and no author describes nothing: natural absence, not a failure",
    ),
    # D-087 G-04: designations split by format characters (English).
    *(
        new(
            f"garry-title-{name}",
            "format_character",
            garry(title=GT + " – Com" + ch + "ments", author="Hon"),
            GARRY,
            ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
            origin=DEV_GARRY,
            requirement=G04,
            note=f"{name} inside 'Comments'; the commenter's surname replaced by a record author's",
        )
        for name, ch in (
            ("soft-hyphen", SHY),
            ("zwsp", ZWSP),
            ("zwnj", ZWNJ),
            ("zwj", ZWJ),
            ("word-joiner", WJ),
            ("bom", BOM),
        )
    ),
    new(
        "designation-prefix-word-joiner",
        "format_character",
        cite(last1="Lindqvist", title="Re" + WJ + "ply to " + T),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        requirement=G04,
    ),
    new(
        "format-only-separator",
        "format_character",
        cite(last1="Lindqvist", title=T + ZWSP + "Comments"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        requirement=G04,
        note="split reading: LONGER with 'comments' (conflict); joined reading: OVERLAP with 'studycomments'",
    ),
    new(
        "format-in-record-title",
        "format_character",
        cite(last1="Lindqvist", title=T),
        {**REC, "title": "Thermal Drift of Syn" + SHY + "thetic Lattice Sensors: A Field Study"},
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=3),
        requirement=G04,
        note="split reading of the record title: 'syn' 'thetic' (OVERLAP); the worse reading decides",
    ),
    # D-087 G-04: genuine titles and surnames with format characters.
    new(
        "genuine-title-soft-hyphen",
        "format_character",
        cite(last1="Lindqvist", title="Ther" + SHY + "mal drift of synthetic lattice sensors: a field study"),
        REC,
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=3),
        requirement=G04,
        note="stated cost (spec 9): a format character inside a genuine word abstains",
    ),
    new(
        "genuine-title-format-between-words",
        "format_character",
        cite(last1="Lindqvist", title="Thermal drift" + ZWSP + " of synthetic lattice sensors: a field study"),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        requirement=G04,
        note="a format character next to a space changes no word under either reading",
    ),
    new(
        "genuine-surname-soft-hyphen",
        "format_character",
        cite(last1="Lind" + SHY + "qvist", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL", readings=3),
        requirement=G04,
        note="stated cost (spec 9): the split reading sees 'lind' 'qvist', as bib-1 did; fail closed",
    ),
    new(
        "genuine-surname-trailing-format",
        "format_character",
        cite(last1="Lindqvist" + ZWSP, title=T),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        requirement=G04,
    ),
    new(
        "bom-at-value-start",
        "format_character",
        cite(last1=BOM + "Lindqvist", title=BOM + T),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        requirement=G04,
    ),
    # D-087 G-04: Arabic.
    new(
        "arabic-designation-zwnj",
        "format_character_arabic",
        ar_cite(عنوان="تع" + ZWNJ + "ليق على " + AR_T, الأخير1="الخطيب"),
        AR_REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        wiki="ar",
        requirement=G04,
    ),
    new(
        "arabic-designation-alm",
        "format_character_arabic",
        ar_cite(عنوان=ALM + "رد على " + AR_T, الأخير1="الخطيب"),
        AR_REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        wiki="ar",
        requirement=G04,
        note="U+061C ARABIC LETTER MARK before the designation",
    ),
    new(
        "arabic-genuine-rlm",
        "format_character_arabic",
        ar_cite(عنوان=RLM + AR_T + RLM, الأخير1="الخطيب"),
        AR_REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        wiki="ar",
        requirement=G04,
    ),
    new(
        "arabic-genuine-zwnj-in-word",
        "format_character_arabic",
        ar_cite(عنوان="الانجراف الحرا" + ZWNJ + "ري في المستشعرات الشبكية", الأخير1="الخطيب"),
        AR_REC,
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=3),
        wiki="ar",
        requirement=G04,
        note="stated cost: a format character inside a genuine word abstains",
    ),
    new(
        "arabic-surname-zwj",
        "format_character_arabic",
        ar_cite(عنوان=AR_T, الأخير1="الخط" + ZWJ + "يب"),
        AR_REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL", readings=3),
        wiki="ar",
        requirement=G04,
        note="stated cost: the split reading conflicts, as under bib-1",
    ),
    new(
        "arabic-shortened-genuine",
        "arabic",
        ar_cite(عنوان="الانجراف الحراري", الأخير1="الخطيب"),
        AR_REC,
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER"),
        wiki="ar",
        requirement=A02,
    ),
    new(
        "arabic-extended-title",
        "arabic",
        ar_cite(عنوان=AR_T + ": ملاحظات", الأخير1="الخطيب"),
        AR_REC,
        ex(NE, (EXT,), authors="AGREE", title_relation="LONGER"),
        wiki="ar",
        requirement=A02,
        note="'ملاحظات' (remarks) is not in the lexicon: a longer title is not established",
    ),
    # D-087 A-02: weak compatibility is not identity.
    new(
        "commenter-shares-surname-remarks",
        "weak_compatibility",
        garry(title="Remarks on: " + GT, author="Ng"),
        GARRY,
        ex(NE, (EXT,), authors="AGREE", title_relation="LONGER", designation=False),
        origin=DEV_GARRY,
        requirement=A02,
        note="bib-1: CONTAINED + AGREE → COMPATIBLE (positive); one shared surname proves nothing",
    ),
    new(
        "commenter-shares-surname-overlap",
        "weak_compatibility",
        garry(title="Fever in Biblical time: influenza revisited", author="Leung"),
        GARRY,
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", designation=False),
        origin=DEV_GARRY,
        requirement=A02,
    ),
    new(
        "no-comparable-author-superset",
        "weak_compatibility",
        cite(title=T + ": a second look"),
        REC,
        ex(NE, (EXT,), authors="INSUFFICIENT", title_relation="LONGER"),
        requirement=A02,
    ),
    new(
        "non-latin-author-superset",
        "weak_compatibility",
        cite(last1="ليندكفيست", title=T + ": remarks"),
        REC,
        ex(NE, (EXT,), authors="INSUFFICIENT", title_relation="LONGER"),
        requirement=A02,
        note="an author in another script is not comparable",
    ),
    new(
        "remarks-prefix",
        "weak_compatibility",
        cite(last1="Lindqvist", title="Remarks on " + T),
        REC,
        ex(NE, (EXT,), authors="AGREE", title_relation="LONGER", designation=False),
        requirement=A02,
        note="'remarks' is not in the lexicon and is not added: a strict superset never keeps D-14",
    ),
    new(
        "superset-shared-author",
        "weak_compatibility",
        cite(last1="Lindqvist", last2="Oyelaran", title=T + ": a reappraisal"),
        REC,
        ex(NE, (EXT,), authors="AGREE", title_relation="LONGER"),
        requirement=A02,
    ),
    new(
        "packed-author-value-overlap",
        "packed_authors",
        cite(author="Lindqvist M, Quill P, Vargas I", title="Thermal drift revisited"),
        REC,
        ex(NE, (PAR,), authors="INSUFFICIENT", title_relation="OVERLAP"),
        requirement=A02,
        note="one author parameter holding three people: packed, never AGREE (bib-1: AGREE)",
    ),
    new(
        "packed-author-value-equal-title",
        "packed_authors",
        cite(author="Lindqvist M, Quill P, Vargas I", title=T),
        REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        requirement=A02,
        note="the EQUAL title establishes the object; the packed value neither agrees nor conflicts",
    ),
    new(
        "packed-authors-list",
        "packed_authors",
        cite(people="Lindqvist M, Quill P", title=T + ": comments"),
        REC,
        ex(MC, (RR,), authors="INSUFFICIENT", title_relation="LONGER", designation=True),
        requirement=A02,
    ),
    new(
        "packed-authors-list-strangers",
        "packed_authors",
        cite(people="Quill P, Vargas I", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        requirement=A02,
        note="a packed part none of whose names is an author conflicts",
    ),
    new(
        "packed-conjunction",
        "packed_authors",
        cite(author="Lindqvist and Quill", title=T + " (extended)"),
        REC,
        ex(NE, (EXT,), authors="INSUFFICIENT", title_relation="LONGER"),
        requirement=A02,
    ),
    new(
        "packed-ampersand",
        "packed_authors",
        cite(author="Lindqvist & Quill", title=T),
        REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        requirement=A02,
    ),
    new(
        "vauthors-one-stranger",
        "packed_authors",
        cite(vauthors="Lindqvist MQ, Quill P", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        requirement=A02,
        note="a Vancouver list is split into persons; one non-author conflicts (bib-1: AGREE)",
    ),
    new(
        "authors-list-semicolon-persons",
        "packed_authors",
        cite(people="Lindqvist; Oyelaran; Brezinova", title=T),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        requirement=A02,
    ),
    new(
        "authors-list-semicolon-stranger",
        "packed_authors",
        cite(people="Lindqvist; Quill", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        requirement=A02,
    ),
    new(
        "arabic-comma-packed",
        "packed_authors",
        cite(people="Lindqvist، Quill", title=T),
        REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        requirement=A02,
    ),
    new(
        "arabic-authors-list-packed",
        "packed_authors",
        ar_cite(المؤلفون="الخطيب، يوسف، القاسم", عنوان=AR_T + " مراجعة"),
        AR_REC,
        ex(NE, (EXT,), authors="INSUFFICIENT", title_relation="LONGER"),
        wiki="ar",
        requirement=A02,
        note="ar free-form list (Authors family) packed by Arabic commas; a longer title is not established",
    ),
    new(
        "shortened-title-genuine",
        "weak_compatibility",
        cite(last1="Lindqvist", title="Thermal drift"),
        REC,
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER", designation=False),
        requirement=A02,
        note="a shortened form other than the main title does not establish the object (spec 4.2, D-087 A-02)",
    ),
    new(
        "shortened-title-record-designation",
        "weak_compatibility",
        cite(last1="Lindqvist", title="the lattice debate"),
        {**REC, "title": "Comment on the lattice debate"},
        ex(MC, (RR,), authors="AGREE", title_relation="SHORTER", designation=True),
        requirement=A02,
        note="the record is a comment; the citation names the debate",
    ),
    new(
        "equal-title-second-value-disjoint-designation",
        "weak_compatibility",
        cite(last1="Lindqvist", title=T, chapter="Reply"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=A02,
        note="spec 4.2: a designation in any non-EQUAL value conflicts",
    ),
    new(
        "equal-title-and-longer-value",
        "weak_compatibility",
        cite(last1="Lindqvist", title=T, **{"trans-title": T + ": remarks"}),
        REC,
        ex(NE, (VAL,), authors="AGREE", title_relation="EQUAL"),
        requirement=A02,
        note="M4: every title value must agree; 'remarks' is not in the lexicon: the longer value is not established",
    ),
    # Amendments after the independent reference's review (spec 2.1 steps 4 to 7, 3.1, 4.1; items A1 to A15 of
    # simulations/stage04/bib2_reference_NOTES.md), written from the amended specification before the outputs were seen.
    new(
        "vauthors-whole-value-conflict",
        "packed_authors",
        cite(vauthors="& KL\u060c", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        requirement=A02,
        note="A1: the parts hold no comparable word, the whole value does and names no author (bib-1's test, kept)",
    ),
    new(
        "title-lang-template-hides-designation",
        "hidden_content",
        cite(last1="Lindqvist", title="{{lang|en|Comments on}} " + T),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="A2: cleaning would drop the template's words; the value cannot be read, so the check is unavailable",
    ),
    new(
        "title-template-argument",
        "hidden_content",
        cite(last1="Lindqvist", title="{{{1}}} " + T),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="A2: a template argument in a compared value",
    ),
    new(
        "periodical-template-is-not-compared",
        "hidden_content",
        cite(last1="Lindqvist", title=T, journal="{{lang|fr|Revue}}"),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        requirement=D086,
        note="a template in a recorded family is cleaned as in bib-1; nothing compared is hidden",
    ),
    new(
        "parameterless-template-is-boundary",
        "hidden_content",
        cite(last1="Lindqvist", title="Thermal drift {{snd}} synthetic lattice sensors"),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="a template without parameters may render anything ({{Erratum}}); its value cannot be read",
    ),
    new(
        "commented-parameter-name",
        "hidden_content",
        "{{cite journal |last1=Lindqvist |title<!-- as published -->=Comments on " + T + "}}",
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="A3: MediaWiki reads this parameter as the title, which bib-1 did not (no title: INSUFFICIENT); a name"
        " with markup cannot be read either way without changing what bib-1 compared, so the check is unavailable",
    ),
    new(
        "templated-parameter-name",
        "hidden_content",
        "{{cite journal |last1=Lindqvist |{{echo|title}}=Comments on " + T + "}}",
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="A3: a name holding a template cannot be read without expanding it",
    ),
    new(
        "hangul-filler-hides-erratum",
        "format_character",
        cite(last1="Lindqvist", title="Err\u3164atum: " + T),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        requirement=G04,
        note="A4: U+3164 is a letter (not Cf) but Default_Ignorable; the joined reading finds the designation",
    ),
    new(
        "unassigned-ignorable-hides-comment",
        "format_character",
        cite(last1="Lindqvist", title="Com\u2065ment on " + T),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=3),
        requirement=G04,
        note="A4: U+2065 is unassigned (Cn) and Default_Ignorable; the joined reading finds the designation",
    ),
    new(
        "variation-selector-in-genuine-title",
        "format_character",
        cite(last1="Lindqvist", title="Thermal\ufe0f drift of synthetic lattice sensors: a field study"),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        requirement=G04,
        note="a variation selector (a mark, removed by folding) leaves a genuine title equal under every reading",
    ),
    new(
        "arabic-waw-packed",
        "packed_authors",
        ar_cite(
            **{"\u0645\u0624\u0644\u0641": "\u0623\u062d\u0645\u062f \u0648 \u0627\u0644\u0642\u0627\u0633\u0645"},
            **{"\u0639\u0646\u0648\u0627\u0646": AR_T},
        ),
        AR_REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        wiki="ar",
        requirement=A02,
        note="A15: the Arabic conjunction packs two people in one author value; packed never agrees",
    ),
    new(
        "arabic-host-is-one-person",
        "packed_authors",
        ar_cite(host="\u0627\u0644\u0642\u0627\u0633\u0645", **{"\u0639\u0646\u0648\u0627\u0646": AR_T}),
        AR_REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        wiki="ar",
        requirement=A02,
        note="A11: ar host is in the one-person family; a non-author conflicts",
    ),
    new(
        "surname-given-comma-is-packed",
        "packed_authors",
        cite(author="Lindqvist, Mara", title=T),
        REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        requirement=A02,
        note="A6: 'Surname, Given' cannot be told from two people, so it never agrees; it can still conflict",
    ),
    new(
        "two-people-one-comma-is-packed",
        "packed_authors",
        cite(author="Lindqvist M, Quill P", title=T),
        REC,
        ex(CO, authors="INSUFFICIENT", title_relation="EQUAL"),
        requirement=A02,
        note="A6: one author and one non-author in one value: undetermined, never a conflict, never an agreement",
    ),
    # Second review of the independent reference (bib2_reference_NOTES.md, B1 to B9): written from the amended spec
    # (2.1 steps 4 and 5, 3.1, 3.2, 4.2, 4.2a) before the outputs were seen.
    new(
        "genre-type-erratum",
        "genre",
        cite(last1="Lindqvist", title=T, type="Erratum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=A02,
        note="CS1 type states the genre; the record's title does not hold it (bib-1: COMPATIBLE)",
    ),
    new(
        "genre-department-letters",
        "genre",
        cite(last1="Lindqvist", title=T, department="Letters"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=A02,
    ),
    new(
        "genre-type-without-title",
        "genre",
        cite(last1="Lindqvist", type="Retraction notice"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="MISSING", designation=True),
        requirement=A02,
        note="a stated genre designates even when the citation has no title",
    ),
    new(
        "genre-word-in-record-title",
        "genre",
        cite(last1="Lindqvist", title="Letter: " + T, type="Letter"),
        {**REC, "title": "Letter: " + REC["title"]},
        ex(CO, authors="AGREE", title_relation="EQUAL", designation=False),
        requirement=A02,
        note="a retracted letter cited as a letter: the record's title holds the word",
    ),
    new(
        "genre-neutral-type",
        "genre",
        cite(last1="Lindqvist", title=T, type="Research article"),
        REC,
        ex(NE, (GEN,), authors="AGREE", title_relation="EQUAL", designation=False),
        requirement=A02,
        note="M3: a genre the lexicon does not hold and the record's title does not name is not established (a cost)",
    ),
    new(
        "arabic-genre-type",
        "genre",
        ar_cite(
            **{
                "\u0639\u0646\u0648\u0627\u0646": AR_T,
                "\u0627\u0644\u0646\u0648\u0639": "\u062a\u0635\u062d\u064a\u062d",
            }
        ),
        AR_REC,
        ex(MC, (RR,), authors="INSUFFICIENT", title_relation="EQUAL", designation=True),
        wiki="ar",
        requirement=A02,
        note="ar type (\u0627\u0644\u0646\u0648\u0639) = correction",
    ),
    new(
        "title-parser-function",
        "hidden_content",
        cite(last1="Lindqvist", title="{{lc:Comments on}} " + T),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="a parser function has no parameters for the parser but renders words",
    ),
    new(
        "title-magic-word",
        "hidden_content",
        cite(last1="Lindqvist", title=T + " {{PAGENAME}}"),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
    ),
    new(
        "title-math-hides-designation",
        "hidden_content",
        cite(last1="Lindqvist", title="<math>\\text{Comments on}</math> " + T),
        REC,
        unavailable(U_PARSE),
        requirement=D086,
        note="cleaning drops a math tag's content, which renders",
    ),
    new(
        "title-nowiki-is-read",
        "hidden_content",
        cite(last1="Lindqvist", title="<nowiki>Comments on</nowiki> " + T),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
        requirement=D086,
        note="nowiki content is kept by cleaning: it is read",
    ),
    new(
        "commented-name-of-no-family",
        "hidden_content",
        "{{cite journal |last1=Lindqvist |title=" + T + " |url<!-- dead -->=https://example.org/x}}",
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        requirement=D086,
        note="a commented name of no family is ignored, as by bib-1",
    ),
    new(
        "commented-name-of-recorded-family",
        "hidden_content",
        "{{cite journal |last1=Lindqvist |title=" + T + " |journal<!-- x -->=Letters}}",
        REC,
        unavailable(U_PARSE),
        requirement=D086,
    ),
    new(
        "cyrillic-lookalike-second-title",
        "lookalike",
        cite(last1="Lindqvist", title=T, chapter="Err\u0430tum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=G04,
        note="a Cyrillic a inside 'Erratum': a mixed word counts as a designation",
    ),
    new(
        "cyrillic-lookalike-genre",
        "lookalike",
        cite(last1="Lindqvist", title=T, type="L\u0435tter"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=G04,
    ),
    new(
        "cyrillic-lookalike-author",
        "lookalike",
        garry(title=GT, author="R\u043ebert G\u0430rry"),
        GARRY,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL"),
        origin=DEV_GARRY,
        requirement=G04,
        note="a look-alike name is compared and names no record author",
    ),
    new(
        "c1-control-hides-erratum",
        "format_character",
        cite(last1="Lindqvist", title=T, chapter="Err\u0080atum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True, readings=3),
        requirement=G04,
        note="a C1 control character is read as invisible; the joined reading finds the designation",
    ),
    new(
        "shortened-suffix-of-title",
        "weak_compatibility",
        cite(last1="Lindqvist", title="a field study"),
        REC,
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER"),
        requirement=A02,
        note="the subtitle alone may be the title of another work",
    ),
    new(
        "shortened-other-work-title",
        "weak_compatibility",
        cite(last1="Quill", title="Cystic fibrosis"),
        {"title": "Gene therapy for cystic fibrosis", "authors": "Ann Quill", "journal": None, "original_year": 2001},
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER"),
        requirement=A02,
        note="a shortened title that is the full title of another work does not establish the object",
    ),
    new(
        "greek-letter-in-equal-title",
        "lookalike",
        cite(last1="Lindqvist", title="Integrin \u03b1v\u03b23 in lattice sensors"),
        {**REC, "title": "Integrin \u03b1v\u03b23 in lattice sensors"},
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        requirement=G04,
        note="a mixed word both titles hold is no extra word: an equal title is unaffected",
    ),
    # Amendments M1 to M8 after the independent reference's second review (simulations/stage04/bib2_reference_NOTES.md),
    # written from the amended specification before the outputs were seen.
    new(
        "comment-inside-chapter-erratum",
        "hidden_content",
        cite(last1="Lindqvist", title=T, chapter="Err<!-- -->atum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True, readings=3),
        requirement=G04,
        note="M1: MediaWiki renders the comment as nothing, so the chapter reads Erratum (joined reading)",
    ),
    new(
        "nowiki-inside-type-erratum",
        "hidden_content",
        cite(last1="Lindqvist", title=T, type="Err<nowiki/>atum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True, readings=3),
        requirement=G04,
        note="M1: an empty nowiki tag renders nothing inside the genre word",
    ),
    new(
        "comment-beside-genuine-title",
        "hidden_content",
        cite(last1="Lindqvist", title=T + " <!-- checked 2024 -->"),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=3),
        requirement=G04,
        note="M1: a comment after the title is a boundary in every reading; the title stays EQUAL",
    ),
    new(
        "comment-only-title",
        "hidden_content",
        cite(last1="Lindqvist", title="<!-- title -->"),
        REC,
        ex(IN, authors="AGREE", title_relation="MISSING"),
        requirement=D086,
        note="M1: a value with no visible character is absent (natural absence, not a failure)",
    ),
    new(
        "zwsp-inside-type-erratum",
        "invisible",
        cite(last1="Lindqvist", title=T, type="Err" + ZWSP + "atum"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True, readings=3),
        requirement=G04,
        note="M2: genre values are compared strings of section 3.1",
    ),
    new(
        "genre-conference-abstract",
        "genre",
        cite(last1="Lindqvist", title=T, type="Conference abstract"),
        REC,
        ex(NE, (GEN,), authors="AGREE", title_relation="EQUAL", designation=False),
        requirement=A02,
        note="M3: a genre outside the lexicon (an abstract shares the paper's title) is not established",
    ),
    new(
        "arabic-genre-letter-outside-lexicon",
        "genre",
        ar_cite(**{AR_TITLE: AR_T, AR_TYPE: "\u0631\u0633\u0627\u0644\u0629"}),
        AR_REC,
        ex(NE, (GEN,), authors="INSUFFICIENT", title_relation="EQUAL", designation=False),
        wiki="ar",
        requirement=A02,
        note="M3: 'رسالة' (letter) is not in the Arabic lexicon, which is not extended; the pair is not established",
    ),
    new(
        "arabic-genre-persian-yeh-variant",
        "genre",
        ar_cite(**{AR_TITLE: AR_T, AR_TYPE: "\u062a\u0639\u0644\u06cc\u0642"}),
        AR_REC,
        ex(NE, (GEN,), authors="INSUFFICIENT", title_relation="EQUAL", designation=False),
        wiki="ar",
        requirement=A02,
        note="M3: 'تعلیق' with a Persian yeh is no lexicon word, so it is unmatched, never harmless",
    ),
    new(
        "small-capitals-chapter-erratum",
        "lookalike",
        cite(last1="Lindqvist", title=T, chapter="\u1d07\u0280\u0280\u1d00\u1d1b\u1d1c\u1d0d"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=G04,
        note="M7: small capitals are Latin look-alikes; the skeleton of the chapter is 'erratum'",
    ),
    new(
        "dotless-i-genre-correction",
        "lookalike",
        cite(last1="Lindqvist", title=T, type="Correct\u0131on"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="EQUAL", designation=True),
        requirement=G04,
        note="M7: a dotless i inside 'Correction' is read as i for the lexicon lookup",
    ),
    new(
        "main-title-without-author",
        "weak_compatibility",
        cite(title="Thermal drift of synthetic lattice sensors"),
        REC,
        ex(NE, (SHO,), authors="INSUFFICIENT", title_relation="SHORTER"),
        requirement=A02,
        note="M8: the main title alone may be another work's whole title; it never agrees",
    ),
    new(
        "main-title-with-author",
        "weak_compatibility",
        cite(last1="Lindqvist", title="Thermal drift of synthetic lattice sensors"),
        REC,
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER"),
        requirement=A02,
        note="M8: the main title never agrees, even with an agreeing author (M5 superseded)",
    ),
    new(
        "main-title-of-a-notice-in-another-language",
        "weak_compatibility",
        cite(last1="Lindqvist", title="Thermal drift of synthetic lattice sensors"),
        {**REC, "title": "Thermal drift of synthetic lattice sensors: Berichtigung"},
        ex(NE, (SHO,), authors="AGREE", title_relation="SHORTER"),
        requirement=A02,
        note="M8: the omitted subtitle names a notice in a word outside the lexicon; the main title cannot show it",
    ),
    new(
        "title-and-chapter-remarks",
        "weak_compatibility",
        cite(last1="Lindqvist", title=T, chapter="Remarks"),
        REC,
        ex(NE, (VAL,), authors="AGREE", title_relation="EQUAL"),
        requirement=A02,
        note="M4: 'Remarks' is outside the lexicon; a title value that does not agree is never ignored",
    ),
    new(
        "japanese-title-beside-equal-trans-title",
        "weak_compatibility",
        cite(last1="Lindqvist", title="\u71b1\u30c9\u30ea\u30d5\u30c8\u306e\u7814\u7a76", **{"trans-title": T}),
        REC,
        ex(NE, (VAL,), authors="AGREE", title_relation="EQUAL", designation=False),
        requirement=A02,
        note="M6: kanji with kana is one writing system, not mixed (no conflict); M4: the original title differs",
    ),
    new(
        "greek-lookalike-whole-chapter",
        "lookalike",
        cite(last1="Lindqvist", title=T, chapter="\u03f9\u039f\u039c\u039c\u0395\u039d\u03a4"),
        REC,
        ex(NE, (VAL,), authors="AGREE", title_relation="EQUAL"),
        requirement=G04,
        note="a chapter written wholly in Greek look-alikes ('COMMENT') is no lexicon word and never agrees (M4)",
    ),
]

for c in NEW_CASES:
    if c["id"] == "garry-not-utf8":
        c["source_bytes_hex"] = (b"\xff" + garry().encode("utf-8")).hex()
        c["source"] = None


def main() -> None:
    old = json.loads((HERE / "BIB_CORPUS.json").read_text(encoding="utf-8"))["cases"]
    if {c["id"] for c in old} != set(BIB1_EXPECT_2):
        raise SystemExit("every bib-1 case needs exactly one bib-2 verdict")
    cases: list[dict[str, Any]] = []
    for c in old:
        cases.append({**c, "expect": BIB1_EXPECT_2[c["id"]], "bib1_expect": c["expect"], "requirement": "bib-1"})
    cases += NEW_CASES
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate case id")
    doc = {
        "format": "citerift-bib-corpus/2",
        "specification": "docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md (bib-2)",
        "label": "SYNTHETIC unless origin names development evidence; never evaluation data",
        "cases": cases,
    }
    (HERE / "BIB2_CORPUS.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
