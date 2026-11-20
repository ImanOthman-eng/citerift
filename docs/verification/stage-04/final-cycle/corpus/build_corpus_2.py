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
    "punct-case": ex(CO, authors="AGREE", title="AGREE", title_relation="EQUAL"),
    "punct-markup": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "diacritics": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "author-inverted": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "author-initials-only": ex(CO, authors="INSUFFICIENT", title="AGREE"),
    "truncated-etal": ex(CO, authors="AGREE", title_relation="EQUAL"),
    "only-etal": ex(CO, authors="INSUFFICIENT", title="AGREE"),
    "subtitle-truncated": ex(CO, title_relation="SHORTER", designation=False),
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
    "chapter-in-book-dev": ex(CO, authors="AGREE", title_relation="SHORTER", designation=False),
    "malformed-title-markup-only": ex(IN, authors="INSUFFICIENT", title="INSUFFICIENT", title_relation="MISSING"),
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
    "markup-snd-boundary": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "markup-pipe-template-boundary": ex(MC, (RR,), authors="AGREE", title_relation="OVERLAP", designation=True),
    "markup-br-boundary": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
    "markup-ref-content-kept": ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True),
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
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        origin=DEV_GARRY,
        requirement=D086,
        note="exactly 4,096 code points over all values; the trans-title is DISJOINT and holds no designation",
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
            ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=2),
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
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=2),
        requirement=G04,
    ),
    new(
        "format-only-separator",
        "format_character",
        cite(last1="Lindqvist", title=T + ZWSP + "Comments"),
        REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=2),
        requirement=G04,
        note="split reading: LONGER with 'comments' (conflict); joined reading: OVERLAP with 'studycomments'",
    ),
    new(
        "format-in-record-title",
        "format_character",
        cite(last1="Lindqvist", title=T),
        {**REC, "title": "Thermal Drift of Syn" + SHY + "thetic Lattice Sensors: A Field Study"},
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=2),
        requirement=G04,
        note="split reading of the record title: 'syn' 'thetic' (OVERLAP); the worse reading decides",
    ),
    # D-087 G-04: genuine titles and surnames with format characters.
    new(
        "genuine-title-soft-hyphen",
        "format_character",
        cite(last1="Lindqvist", title="Ther" + SHY + "mal drift of synthetic lattice sensors: a field study"),
        REC,
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=2),
        requirement=G04,
        note="stated cost (spec 9): a format character inside a genuine word abstains",
    ),
    new(
        "genuine-title-format-between-words",
        "format_character",
        cite(last1="Lindqvist", title="Thermal drift" + ZWSP + " of synthetic lattice sensors: a field study"),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=2),
        requirement=G04,
        note="a format character next to a space changes no word under either reading",
    ),
    new(
        "genuine-surname-soft-hyphen",
        "format_character",
        cite(last1="Lind" + SHY + "qvist", title=T),
        REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL", readings=2),
        requirement=G04,
        note="stated cost (spec 9): the split reading sees 'lind' 'qvist', as bib-1 did; fail closed",
    ),
    new(
        "genuine-surname-trailing-format",
        "format_character",
        cite(last1="Lindqvist" + ZWSP, title=T),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=2),
        requirement=G04,
    ),
    new(
        "bom-at-value-start",
        "format_character",
        cite(last1=BOM + "Lindqvist", title=BOM + T),
        REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=2),
        requirement=G04,
    ),
    # D-087 G-04: Arabic.
    new(
        "arabic-designation-zwnj",
        "format_character_arabic",
        ar_cite(عنوان="تع" + ZWNJ + "ليق على " + AR_T, الأخير1="الخطيب"),
        AR_REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=2),
        wiki="ar",
        requirement=G04,
    ),
    new(
        "arabic-designation-alm",
        "format_character_arabic",
        ar_cite(عنوان=ALM + "رد على " + AR_T, الأخير1="الخطيب"),
        AR_REC,
        ex(MC, (RR,), authors="AGREE", title_relation="LONGER", designation=True, readings=2),
        wiki="ar",
        requirement=G04,
        note="U+061C ARABIC LETTER MARK before the designation",
    ),
    new(
        "arabic-genuine-rlm",
        "format_character_arabic",
        ar_cite(عنوان=RLM + AR_T + RLM, الأخير1="الخطيب"),
        AR_REC,
        ex(CO, authors="AGREE", title_relation="EQUAL", readings=2),
        wiki="ar",
        requirement=G04,
    ),
    new(
        "arabic-genuine-zwnj-in-word",
        "format_character_arabic",
        ar_cite(عنوان="الانجراف الحرا" + ZWNJ + "ري في المستشعرات الشبكية", الأخير1="الخطيب"),
        AR_REC,
        ex(NE, (PAR,), authors="AGREE", title_relation="OVERLAP", readings=2),
        wiki="ar",
        requirement=G04,
        note="stated cost: a format character inside a genuine word abstains",
    ),
    new(
        "arabic-surname-zwj",
        "format_character_arabic",
        ar_cite(عنوان=AR_T, الأخير1="الخط" + ZWJ + "يب"),
        AR_REC,
        ex(MC, (RA,), authors="CONFLICT", title_relation="EQUAL", readings=2),
        wiki="ar",
        requirement=G04,
        note="stated cost: the split reading conflicts, as under bib-1",
    ),
    new(
        "arabic-shortened-genuine",
        "arabic",
        ar_cite(عنوان="الانجراف الحراري", الأخير1="الخطيب"),
        AR_REC,
        ex(CO, authors="AGREE", title_relation="SHORTER"),
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
        ex(CO, authors="AGREE", title_relation="SHORTER", designation=False),
        requirement=A02,
        note="a shortened form whose omitted words name no other object stays compatible",
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
        ex(CO, authors="AGREE", title_relation="EQUAL"),
        requirement=A02,
        note="the best relation decides; the longer value holds no designation",
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
