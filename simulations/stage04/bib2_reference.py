"""Independent reference model of the bibliographic-object consistency layer bib-2 (owner decisions D-086, D-087).

Written from ``docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md`` as amended after this model's reviews
(items A1 to A15 and B1 to B7 of ``bib2_reference_NOTES.md``): sections 2 to 5 and 8, and, where that text says
"unchanged from bib-1", section 2.1 step 4 and section 3 of ``BIBLIOGRAPHIC_SPEC.md``. The parsing, value cleaning (with
B1) and word functions are copied from the earlier independent bib-1 reference ``bib_reference.py`` (which bib-2
declares unchanged), so this file stands alone. It imports no production code: nothing from ``citerift`` and nothing
from the other reference modules, only the standard library and ``mwparserfromhell`` (the parser the specification
names). Its alias profile is ``bib2-reference-profile.json`` next to this file (``PROFILE_PATH``): the bib-1 reference's
own profile ``bib-reference-profile.json`` (extracted separately from the raw ``Module:Citation/CS1/Configuration``
revisions the specification names, en 1384336575 and ar 76424085, content SHA-256 recorded in the file; left unchanged
for the bib-1 reference) with the keys TitleType and TitleNote added from the same raw revisions (downloaded with
``action=raw``, SHA-256 checked against the recorded values), not copied from the production profile. Simple code is
preferred to fast code.

Public API: ``load_profile`` (default: ``PROFILE_PATH``), ``describe`` (section 2.1 steps 1 to 8:
``{"state": "UNAVAILABLE", "reason": r}`` or ``{"state": "DESCRIBED", "fields": C}``; the caller handles ABSENT units)
and ``compare`` (sections 3, 4, 4.2a and 5 under the three readings of section 3.1).

Readings of the specification
-----------------------------

Where the text leaves a choice open, the most literal reading is taken; where two readings remain, the one that
blocks a positive more often. Each such point (ambiguities with a safety bearing are also in
``bib2_reference_NOTES.md``):

R1. (2.1 last paragraph, 2.2) Engine configuration is checked before any unit is read and raises (``ValueError`` or
    ``RuntimeError``), never gives UNAVAILABLE: an unknown wiki, a profile that lacks a needed alias list, a
    mwparserfromhell version other than 0.7.2, or an inactive C tokenizer (``mwparserfromhell.parser.use_c``).
R2. (2.1 step 1) ``data`` that is ``None`` (span unreadable) or not ``bytes``/``bytearray`` (B8) gives
    UNAVAILABLE(BIB_PARSE_FAILED); decoding is strict ``bytes.decode("utf-8")``, so a leading byte-order mark is kept
    as U+FEFF (and then, as a non-whitespace top-level Text node, gives BIB_PARSE_FAILED at step 3, as section 9 says).
R3. (2.1 step 2) The bound is ``len(text) > 16384`` on the decoded ``str``, checked before parsing.
R4. (2.1 step 3) "Ignoring top-level Text nodes whose value is empty after ``str.strip()``": every other top-level
    node (comment, tag, a second template, other text) gives BIB_PARSE_FAILED. Any template counts, whatever its name.
    Exceptions are caught over parsing, reading ``template.params`` and the names, the hidden-content check of step 5
    and cleaning; only the effective values of arguments in a family are cleaned (the others are not fields).
R5. (2.1 step 4) Applied to every parameter with ``showkey`` true, in source order, also to one that a later parameter
    replaces. The top-level nodes of ``param.name`` decide: Text only -> ``str(param.name).strip()``; Text and Comment
    nodes with at least one Comment -> the Text values concatenated and stripped; if that name belongs to no family
    (R8) the parameter is ignored (it neither enters nor replaces an effective argument), otherwise BIB_PARSE_FAILED;
    any other node type (Template, Argument, Wikilink, ExternalLink, HTMLEntity, Tag, ...) -> BIB_PARSE_FAILED. A dict
    keeps the first position of a name.
R6. (2.1 step 5) Checked on the effective (last) argument of every name in ``titles``, ``genres``, ``authors``,
    ``author_lists`` or ``vauthors``, whether or not its value cleans to an absent value: BIB_PARSE_FAILED when
    ``value.filter_templates(recursive=True)`` or ``value.filter_arguments(recursive=True)`` yields anything, or
    ``value.filter_tags(recursive=True)`` yields a tag whose ``str(tag.tag).strip().lower()`` is not one of the eleven
    inline formatting tags, ``nowiki`` or ``br``. The pinned parser's recursive traversal includes template parameters,
    tag contents and tag attributes; the content of ``<nowiki>`` is not parsed, so nothing inside it is a node.
    Comment, HTMLEntity, Wikilink and ExternalLink nodes are readable.
R7. (2.1 step 5, B1) Cleaning is bib-1's (copied from ``bib_reference.py``, its reading R21) with B1: each top-level
    node is ``Wikicode([node]).strip_code(normalize=True, collapse=True)``; Text, HTMLEntity, Wikilink, ExternalLink
    and the eleven inline tags (tag name compared after ``strip().lower()``) join as written; a top-level Comment node
    is one U+200B; a top-level ``nowiki`` tag (same name comparison) is its ``strip_code`` text between two U+200B
    (``<nowiki/>`` gives two U+200B); every other node (a ``br`` tag) gets one space on each side; runs of ``\\s``
    become one space (U+200B is not ``\\s``); ``str.strip()`` (which keeps U+200B); a result whose every character is
    invisible (R11), the empty string included, is absent; then lone surrogates become U+FFFD (a lone surrogate is not
    invisible, so a value of one is present). Comments and nowiki tags nested inside an inline tag are not top-level
    nodes: ``strip_code`` of the inline tag drops a comment and keeps the nowiki text, joined. Invisible characters are
    kept.
R8. (2.1 step 6) A name belongs to the first family, in the order titles, genres, authors, author_lists, vauthors,
    periodical, date, year, volume, issue, pages, then the first key in the listed order, that has an alias matching
    the whole name (``#`` = empty or ``[1-9][0-9]*``, ASCII, case-sensitive); the first alias in profile order does not
    change the family or key, so it is not tracked. ar ``host`` is in ``authors`` only. ``genres`` keys: TitleType,
    TitleNote.
R9. (2.1 step 6) The ScriptTitle/ScriptChapter prefix is removed once from the cleaned value (the name's key is the
    first key of R8), the rest stripped with ``str.strip()``; an empty rest is absent. ``pages`` is the first value over
    the Page and Pages aliases together.
R10. (2.1 step 7) "Values" are effective arguments with a non-absent value after step 6. The 64-value bounds count
    ``titles`` + ``genres`` and, separately, ``authors`` + ``author_lists`` + ``vauthors``. The 4,096 code-point total
    counts every value of every family (genres included), including the values after the first of the recorded
    families, after cleaning (the U+200B of B1 and the U+FFFD replacement included) and after script-prefix removal;
    ``len`` of the ``str``.
R11. (3.1) An invisible character is a code point of general category Cf, of category Cc for which ``str.isspace()`` is
    false, or one in the Default_Ignorable_Code_Point ranges the specification lists (hard-coded here as written,
    ``DEFAULT_IGNORABLE``); categories come from the running Python's Unicode database. The compared strings are the
    ones section 3.1 lists (B2): the cited title values (after step 6), the cited genre values, the cited author
    values of the three forms, the record's title and the record's authors; periodical, journal, date and year are
    not, so they are never edited and do not count for "some string holds one".
R12. (3.1) Three readings exactly when some compared string holds an invisible character (``readings`` = 3), else
    one (``readings`` = 1): as written; boundary (each invisible character replaced by one U+0020 space, no further
    collapse); joined (each removed). The object verdict is the worst in MATERIAL_CONFLICT > NOT_ESTABLISHED >
    INSUFFICIENT > COMPATIBLE; the reported field verdicts (authors, title, title_relation, designation) are those of
    the first reading, in the order as written, boundary, joined, that gives it; reasons are the union of the reasons
    of every reading that gives it.
R13. (3.2) Words, folding, scripts, name words, particles, initials and ``S_R`` are copied from ``bib_reference.py``
    (its readings R8 to R10 and R22): initials are tested on ``str.split()`` tokens of the raw string, before folding.
R14. (3.2, B6) A word (already folded: words come from ``words`` or the name-word functions) is mixed when the set of
    ``script(c)`` over its characters ``c`` of general category L other than Lm has two or more elements and is not
    a subset of {CJK, HIRAGANA, KATAKANA}, {CJK, HANGUL} or {CJK, BOPOMOFO}. ``script`` is the first word of the
    character's Unicode name (NFKD has already turned Hangul syllables into ``HANGUL CHOSEONG ...`` jamo and halfwidth
    forms into full ones). A letter of another script used in Japanese text (U+3006 ``IDEOGRAPHIC CLOSING MARK``, Lo)
    still makes the word mixed.
R15. (4.1) Splitting uses the characters ``;`` and U+061B (list separators) and additionally ``,`` and U+060C for
    ``vauthors``. For every form an empty piece (after ``str.strip()``) is dropped. A conjunction is the character
    ``&`` anywhere in the piece, or a ``str.split()`` token whose ``casefold()`` is ``and`` or that is exactly U+0648.
    An ``authors`` or ``author_lists`` piece is packed when it holds a conjunction or any comma character.
R16. (4.1) "Comparable when ``S_R`` is not empty and some word of ``N`` has a script that some word of ``S_R`` has, or
    some word of ``N`` is mixed" is read as (``S_R`` non-empty and a shared script) or (a mixed word), so a mixed word
    is comparable also against a record without authors (and then conflicts). The whole-value guard applies the same
    test to ``W``, the cited name words of the whole unsplit value, under the reading at hand. Author verdict:
    CONFLICT if the guard applies to some value or some comparable part has ``N ∩ S_R = ∅`` (person or packed alike);
    else AGREE if some comparable person part has ``N ∩ S_R ≠ ∅``; else INSUFFICIENT.
R17. (4.2) SHORTER and LONGER need a contiguous subsequence of strictly smaller length; OVERLAP uses word sets.
    "Leftmost occurrence" is the smallest start index. A value with empty ``words`` is skipped. Ties between values
    keep the first value of the ``titles`` list.
R18. (4.2) Designation is evaluated for every value whose own relation is not EQUAL; an extra word designates when it
    names a designation (R24) or is mixed; a DP phrase (as ``words(phrase)``) designates when it occurs (R24) in
    ``T`` but not in ``T_R``, or the reverse.
R19. (4.2, main title, B4) The separator pattern is searched in the record's title string under the reading at hand
    (``re.search``, first match); the main title is ``words`` of the text before the match; none without a match. A
    value (with non-empty ``T``) agrees when its relation is EQUAL, or SHORTER with words equal to the main title's.
    Title verdict, first that holds: a designating value or pair relation DISJOINT -> CONFLICT; pair relation MISSING
    -> INSUFFICIENT (checked before "every value agrees", which would hold vacuously with no compared value, R25);
    every compared value agrees -> AGREE; some agrees and another not -> NOT_ESTABLISHED ``BIB_TITLE_VALUES_DIFFER``;
    else NOT_ESTABLISHED with the pair relation's reason (SHORTER, LONGER, OVERLAP or INCOMPARABLE; EQUAL cannot occur
    here, since an EQUAL value agrees).
R20. (4.2a, B3) For each genre value ``G = words(g)``, both under the reading at hand: designates when a word of
    ``G`` names a designation (R24) or is mixed and is not (as itself, not as its skeleton) a word of
    ``words(R.title)``, or a DP phrase occurs (R24) in ``G`` and does not occur (R24) in ``words(R.title)``;
    otherwise unmatched when some word of ``G`` is not (as itself) a word of ``words(R.title)``. A genre value with no
    word (punctuation only) neither designates nor is unmatched. Checked whatever the title relation, also with no
    cited title or no record title (then every genre word is unmatched or designates).
R21. (5, B5) MATERIAL_CONFLICT when authors CONFLICT, the title verdict is CONFLICT or a genre value designates;
    reasons: ``BIB_AUTHORS_DISJOINT`` (authors CONFLICT), ``BIB_TITLE_DISJOINT`` (pair relation DISJOINT),
    ``BIB_TITLE_RELATED_OBJECT`` (a title or genre designation). Else NOT_ESTABLISHED when any of these holds, with
    every reason that holds: the title verdict's NOT_ESTABLISHED reason (R19), ``BIB_GENRE_UNMATCHED`` (some genre
    value unmatched, also with no title), ``BIB_TITLE_SHORTENED`` (B5: title AGREE with pair relation SHORTER and an
    author verdict other than AGREE). Else COMPATIBLE when the title verdict is AGREE, else INSUFFICIENT. The reported
    ``designation`` is true for either kind; the reported ``title`` stays the verdict of section 4.2 (AGREE under B5,
    unchanged by a genre). COMPATIBLE and INSUFFICIENT carry no reason.
R22. (4.3) Year and periodical are bib-1's (copied): ``R.original_year`` counts only as a non-bool ``int``; volume,
    issue and pages are always NOT_IN_RECORD.
R23. (B8) ``fields`` or ``record`` that is not a dict gives the INSUFFICIENT result with relation MISSING and one
    reading. A record field of the wrong type (title, authors, journal not ``str``; original_year not a non-bool
    ``int``) is absent. Non-string entries of the ``fields`` lists and non-string scalar fields are ignored.
R24. (3.2, B7) The skeleton is computed per character of an already folded word with ``unicodedata.name(c, "")`` and
    ``re.fullmatch`` of the stated pattern; the replaced letter is regex group 3 (the single letter just before an
    optional `` WITH ...`` part), casefolded. Names outside the pattern are kept, for example ``LATIN SMALL LETTER
    ALPHA`` (U+0251), ``LATIN LETTER DENTAL CLICK`` (U+01C0) and ``LATIN SMALL CAPITAL LETTER I WITH STROKE``
    (U+1D7B, "SMALL CAPITAL LETTER" is not the pattern's "SMALL LETTER" nor "LETTER SMALL CAPITAL"). A word names a
    designation when it or its skeleton is in DW; a DP phrase occurs in a sequence when it is contiguous in the
    sequence or in the list of the skeletons of its words (each word's skeleton, so the word boundaries are kept).
    The skeleton is used only for these two lookups: relations, extra words, genre-word membership in the record's
    title and author words compare the words themselves.
R25. (4.2, 5) With no compared title value (no value with non-empty ``T``, or empty ``T_R``) the title verdict is
    INSUFFICIENT, never a vacuous AGREE, as section 5 states ("INSUFFICIENT (no cited title or no record title ...)").
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import mwparserfromhell

MODEL_VERSION = "bib-2-reference/4"
PARSER_VERSION = "0.7.2"
PROFILE_PATH = Path(__file__).with_name("bib2-reference-profile.json")

TITLE_KEYS = ("Title", "ScriptTitle", "TransTitle", "Chapter", "ScriptChapter", "TransChapter")
SCRIPT_KEYS = ("ScriptTitle", "ScriptChapter")
# Section 2.1 step 6, in the listed order (R8): list families (all values) and recorded families (first value).
LIST_FAMILIES: dict[str, tuple[str, ...]] = {
    "titles": TITLE_KEYS,
    "genres": ("TitleType", "TitleNote"),
    "authors": ("AuthorList-Last",),
    "author_lists": ("Authors",),
    "vauthors": ("Vauthors",),
}
AUTHOR_FORMS = ("authors", "author_lists", "vauthors")
COMPARED_FAMILIES = ("titles", "genres", *AUTHOR_FORMS)
SINGLE_FAMILIES: dict[str, tuple[str, ...]] = {
    "periodical": ("Periodical",),
    "date": ("Date",),
    "year": ("Year",),
    "volume": ("Volume",),
    "issue": ("Issue",),
    "pages": ("Page", "Pages"),
}
ALL_FAMILIES = {**LIST_FAMILIES, **SINGLE_FAMILIES}

MAX_SOURCE = 16384
MAX_VALUES = 64
MAX_DESCRIPTION = 4096

PARSE_FAILED = "BIB_PARSE_FAILED"
SOURCE_LIMIT = "BIB_SOURCE_LIMIT_EXCEEDED"
VALUE_LIMIT = "BIB_VALUE_LIMIT_EXCEEDED"
DESCRIPTION_LIMIT = "BIB_DESCRIPTION_LIMIT_EXCEEDED"

WHITESPACE_RUN = re.compile(r"\s+")
SCRIPT_PREFIX = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:")
WORD = re.compile(r"[^\W_]+")
ET_AL = re.compile(r"\bet\.?\s*al\b\.?")
YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)")
MAIN_TITLE_SEPARATOR = re.compile(r"[:?!;\u061F\u061B]|\.\s|\s[-\u2013\u2014]\s|\s[(\[]")
LIST_SEPARATORS = re.compile(r"[;\u061B]")
VANCOUVER_SEPARATORS = re.compile(r"[;\u061B,\u060C]")
COMMAS = (",", chr(0x060C))
ARABIC_AND = chr(0x0648)
REPLACEMENT = chr(0xFFFD)
ZERO_WIDTH_SPACE = chr(0x200B)
# Section 3.2, B6: the scripts one writing system mixes by design (the augmented sets of UTS #39) count as one.
AUGMENTED_SCRIPTS = (
    frozenset({"CJK", "HIRAGANA", "KATAKANA"}),
    frozenset({"CJK", "HANGUL"}),
    frozenset({"CJK", "BOPOMOFO"}),
)
# Section 3.2, B7: the Unicode names of the Latin letters a skeleton replaces by their last single-letter group.
SKELETON_NAME = re.compile(r"LATIN (SMALL |CAPITAL )?LETTER ([A-Z]+ )*([A-Z])( WITH [A-Z ]+)?")

# Section 3.1: the Default_Ignorable_Code_Point ranges as the specification lists them (inclusive).
DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)

DW_TEXT = (
    "addendum addenda clarification clarifications correction corrections corrigendum corrigenda erratum errata "
    "retraction retractions withdrawal withdrawals removal removals "
    "comment comments commentary commentaries reply replies response responses rejoinder rejoinders rebuttal "
    "rebuttals discussion discussions editorial editorials letter letters re "
    "تعليق التعليق تعليقات التعليقات تعقيب التعقيب تعقيبات التعقيبات رد الرد ردود الردود تصحيح التصحيح تصحيحات "
    "التصحيحات استدراك الاستدراك سحب السحب افتتاحية الافتتاحية"
)
DW = frozenset(DW_TEXT.split(" "))
DP = ("expression of concern", "expressions of concern", "تعبير عن القلق")
NP_TEXT = "al el de del della der den di da du la le van von bin ibn abu ben dos das بن ابن ابو"
NP = frozenset(NP_TEXT.split(" "))

RELATION_RANK = ("EQUAL", "SHORTER", "LONGER", "OVERLAP", "DISJOINT", "INCOMPARABLE")
OBJECT_RANK = {"COMPATIBLE": 0, "INSUFFICIENT": 1, "NOT_ESTABLISHED": 2, "MATERIAL_CONFLICT": 3}
NOT_ESTABLISHED_REASON = {
    "SHORTER": "BIB_TITLE_SHORTENED",
    "LONGER": "BIB_TITLE_EXTENDED",
    "OVERLAP": "BIB_TITLE_PARTIAL",
    "INCOMPARABLE": "BIB_TITLE_INCOMPARABLE",
}
VALUES_DIFFER = "BIB_TITLE_VALUES_DIFFER"
GENRE_UNMATCHED = "BIB_GENRE_UNMATCHED"


# ---------------------------------------------------------------------------------------------------------------------
# Profile and engine configuration (R1, R8)


def load_profile(path: Path | str = PROFILE_PATH) -> dict[str, Any]:
    """Read the alias profile (by default bib2-reference-profile.json next to this file)."""
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def _alias_regex(alias: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in alias.split("#")]
    return re.compile("(?:[1-9][0-9]*)?".join(parts))


def _alias_table(profile: Any, wiki: Any) -> dict[str, list[re.Pattern[str]]]:
    """The compiled aliases of every CS1 key the families use; raises for an unknown wiki or a malformed profile."""
    if not isinstance(profile, dict) or not isinstance(profile.get("wikis"), dict):
        raise ValueError("malformed bibliographic profile")
    entry = profile["wikis"].get(wiki) if isinstance(wiki, str) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("aliases"), dict):
        raise ValueError(f"unknown wiki for the bibliographic profile: {wiki!r}")
    table: dict[str, list[re.Pattern[str]]] = {}
    for keys in ALL_FAMILIES.values():
        for key in keys:
            names = entry["aliases"].get(key)
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise ValueError(f"profile lacks the aliases of {key} for {wiki}")
            table[key] = [_alias_regex(n) for n in names]
    return table


def _check_parser() -> None:
    if mwparserfromhell.__version__ != PARSER_VERSION:
        raise RuntimeError(f"mwparserfromhell {PARSER_VERSION} required, found {mwparserfromhell.__version__}")
    if not mwparserfromhell.parser.use_c:
        raise RuntimeError("the C tokenizer of mwparserfromhell is not active")


def _family_of(name: str, table: dict[str, list[re.Pattern[str]]]) -> tuple[str, str] | None:
    """(family, key) of a name: the first family, then the first key, with an alias matching it whole (R8)."""
    for family, keys in ALL_FAMILIES.items():
        for key in keys:
            if any(p.fullmatch(name) is not None for p in table[key]):
                return family, key
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Section 2.1: cited object (describe)


class _Unreadable(Exception):
    """A parameter name or value that section 2.1 steps 4 and 5 cannot read (BIB_PARSE_FAILED)."""


JOINED = (
    mwparserfromhell.nodes.Text,
    mwparserfromhell.nodes.HTMLEntity,
    mwparserfromhell.nodes.Wikilink,
    mwparserfromhell.nodes.ExternalLink,
)
JOINED_TAGS = ("i", "b", "sub", "sup", "span", "small", "big", "u", "s", "em", "strong")
READABLE_TAGS = (*JOINED_TAGS, "nowiki", "br")


def _read_name(name: Any, table: dict[str, list[re.Pattern[str]]]) -> str | None:
    """Step 4 (R5): the name, None when the parameter is ignored; raises ``_Unreadable`` for BIB_PARSE_FAILED."""
    nodes = list(name.nodes)
    if all(isinstance(node, mwparserfromhell.nodes.Text) for node in nodes):
        return str(name).strip()
    if all(isinstance(node, (mwparserfromhell.nodes.Text, mwparserfromhell.nodes.Comment)) for node in nodes):
        bare = "".join(str(node.value) for node in nodes if isinstance(node, mwparserfromhell.nodes.Text)).strip()
        if _family_of(bare, table) is None:
            return None
        raise _Unreadable("comment in the name of a family parameter")
    raise _Unreadable("markup in a parameter name")


def _holds_hidden_content(value: Any) -> bool:
    """Step 5 (R6): a Template or Argument node, or a tag other than the readable ones, at any depth."""
    if value.filter_templates(recursive=True) or value.filter_arguments(recursive=True):
        return True
    return any(str(tag.tag).strip().lower() not in READABLE_TAGS for tag in value.filter_tags(recursive=True))


def _is_joined(node: Any) -> bool:
    if isinstance(node, JOINED):
        return True
    return isinstance(node, mwparserfromhell.nodes.Tag) and str(node.tag).strip().lower() in JOINED_TAGS


def _is_nowiki(node: Any) -> bool:
    return isinstance(node, mwparserfromhell.nodes.Tag) and str(node.tag).strip().lower() == "nowiki"


def _clean(value: Any) -> str | None:
    """Step 5 cleaning (R7): bib-1's, except that a Comment is one U+200B and a nowiki tag's text sits between two."""
    pieces = []
    for node in value.nodes:
        if isinstance(node, mwparserfromhell.nodes.Comment):
            pieces.append(ZERO_WIDTH_SPACE)
            continue
        piece = mwparserfromhell.wikicode.Wikicode([node]).strip_code(normalize=True, collapse=True)
        if _is_joined(node):
            pieces.append(piece)
        elif _is_nowiki(node):
            pieces.append(ZERO_WIDTH_SPACE + piece + ZERO_WIDTH_SPACE)
        else:
            pieces.append(" " + piece + " ")
    cleaned = WHITESPACE_RUN.sub(" ", "".join(pieces)).strip()
    if all(is_invisible(ch) for ch in cleaned):  # also the empty string
        return None
    return "".join(REPLACEMENT if 0xD800 <= ord(ch) <= 0xDFFF else ch for ch in cleaned)


def _unavailable(reason: str) -> dict[str, Any]:
    return {"state": "UNAVAILABLE", "reason": reason}


def describe(data: bytes | None, wiki: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Section 2.1 steps 1 to 8 for a ``citation_template`` unit (``data`` None: the span cannot be read)."""
    table = _alias_table(profile, wiki)  # R1: engine configuration raises
    _check_parser()

    # Step 1.
    if not isinstance(data, (bytes, bytearray)):
        return _unavailable(PARSE_FAILED)
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        return _unavailable(PARSE_FAILED)
    # Step 2.
    if len(text) > MAX_SOURCE:
        return _unavailable(SOURCE_LIMIT)
    # Steps 3 to 5.
    try:
        code = mwparserfromhell.parse(text)
        nodes = [
            node
            for node in code.nodes
            if not (isinstance(node, mwparserfromhell.nodes.Text) and str(node.value).strip() == "")
        ]
        if len(nodes) != 1 or not isinstance(nodes[0], mwparserfromhell.nodes.Template):
            return _unavailable(PARSE_FAILED)
        effective: dict[str, Any] = {}
        for param in nodes[0].params:
            if not param.showkey:
                continue
            name = _read_name(param.name, table)
            if name is not None:
                effective[name] = param.value  # a dict keeps the first position of a name
        cleaned: list[tuple[str, str, str | None]] = []  # (family, key, cleaned value)
        for name, raw in effective.items():
            belongs = _family_of(name, table)
            if belongs is None:
                continue
            family, key = belongs
            if family in COMPARED_FAMILIES and _holds_hidden_content(raw):
                raise _Unreadable("hidden content")
            cleaned.append((family, key, _clean(raw)))
    except Exception:
        return _unavailable(PARSE_FAILED)

    # Step 6.
    values: dict[str, list[str]] = {fam: [] for fam in ALL_FAMILIES}
    for family, key, value in cleaned:
        if value is None:
            continue
        kept = SCRIPT_PREFIX.sub("", value, count=1).strip() if key in SCRIPT_KEYS else value
        if kept != "":
            values[family].append(kept)

    # Step 7.
    if len(values["titles"]) + len(values["genres"]) > MAX_VALUES:
        return _unavailable(VALUE_LIMIT)
    if sum(len(values[f]) for f in AUTHOR_FORMS) > MAX_VALUES:
        return _unavailable(VALUE_LIMIT)
    if sum(len(v) for fam in ALL_FAMILIES for v in values[fam]) > MAX_DESCRIPTION:
        return _unavailable(DESCRIPTION_LIMIT)

    # Step 8.
    fields: dict[str, Any] = {fam: list(values[fam]) for fam in LIST_FAMILIES}
    for fam in SINGLE_FAMILIES:
        fields[fam] = values[fam][0] if values[fam] else None
    return {"state": "DESCRIBED", "fields": fields}


# ---------------------------------------------------------------------------------------------------------------------
# Section 3: normalization (3.2 copied from bib_reference.py; 3.1 readings; mixed words)


def fold(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s)
    kept = "".join(c for c in decomposed if unicodedata.category(c) not in ("Mn", "Mc", "Me"))
    return kept.casefold()


def words(s: str | None) -> list[str]:
    if s is None:
        return []
    return WORD.findall(fold(s))


def script(w: str) -> str | None:
    for c in w:
        if c.isdecimal():
            continue
        try:
            return unicodedata.name(c).split()[0]
        except ValueError:
            return None
    return None


def mixed(w: str) -> bool:
    """Section 3.2 (R14): the letters (category L except Lm) of ``w`` belong to two or more scripts, and not all to one
    augmented set (B6: Japanese, Korean, or CJK with Bopomofo)."""
    scripts = set()
    for c in w:
        category = unicodedata.category(c)
        if category.startswith("L") and category != "Lm":
            scripts.add(script(c))
    if len(scripts) < 2:
        return False
    return not any(scripts <= augmented for augmented in AUGMENTED_SCRIPTS)


def skeleton(w: str) -> str:
    """Section 3.2, B7 (R24): every character whose Unicode name fully matches ``SKELETON_NAME`` becomes the
    casefolded letter of its last single-letter group; other characters are kept."""
    out = []
    for c in w:
        match = SKELETON_NAME.fullmatch(unicodedata.name(c, ""))
        out.append(match.group(3).casefold() if match is not None else c)
    return "".join(out)


def names_designation(w: str) -> bool:
    """B7: the word or its skeleton is in DW."""
    return w in DW or skeleton(w) in DW


def phrase_occurs(phrase: list[str], seq: list[str]) -> bool:
    """B7: the phrase occurs as consecutive words of the sequence or of the sequence of its words' skeletons."""
    return _contains(phrase, seq) or _contains(phrase, [skeleton(w) for w in seq])


def name_words(value: str) -> list[str]:
    edited = ET_AL.sub("", fold(value))
    return [w for w in WORD.findall(edited) if len(w) >= 2 and not w.isdecimal() and w not in NP]


def _initials(token: str) -> bool:
    core = token.replace(".", "").rstrip(",;")
    return 1 <= len(core) <= 3 and core.isalpha() and core.isupper()


def cited_author_words(value: str) -> set[str]:
    tokens = value.split()
    kept = [tok for tok in tokens if not _initials(tok)]
    if not kept:
        kept = tokens[:1]
    return set(name_words(" ".join(kept)))


def record_surnames(authors: str | None) -> set[str]:
    if authors is None:
        return set()
    result: set[str] = set()
    for part in authors.split(";"):
        ws = name_words(part)
        result.update(ws[1:] if len(ws) >= 2 else ws)
    return result


def _scripts(ws: set[str] | list[str]) -> set[str]:
    return {s for s in (script(w) for w in ws) if s is not None}


def is_invisible(c: str) -> bool:
    """Section 3.1 (R11): category Cf, a control (Cc) that is not whitespace, or a listed default-ignorable."""
    category = unicodedata.category(c)
    if category == "Cf" or (category == "Cc" and not c.isspace()):
        return True
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in DEFAULT_IGNORABLE)


def has_invisible(s: str | None) -> bool:
    return s is not None and any(is_invisible(c) for c in s)


def _as_written(s: str) -> str:
    return s


def _boundary(s: str) -> str:
    return "".join(" " if is_invisible(c) else c for c in s)


def _joined(s: str) -> str:
    return "".join(c for c in s if not is_invisible(c))


READINGS = (_as_written, _boundary, _joined)  # the order of section 3.1


# ---------------------------------------------------------------------------------------------------------------------
# Section 4.1: authors


def author_parts(form: str, value: str) -> list[tuple[bool, set[str]]]:
    """(packed, N) for every non-empty part of one cited author value of the given form (R15)."""
    splitter = VANCOUVER_SEPARATORS if form == "vauthors" else LIST_SEPARATORS
    parts = []
    for piece in splitter.split(value):
        if piece.strip() == "":
            continue
        if form == "vauthors":
            packed = False
        else:  # authors and author_lists
            comma = any(c in piece for c in COMMAS)
            conjunction = "&" in piece or any(tok.casefold() == "and" or tok == ARABIC_AND for tok in piece.split())
            packed = conjunction or comma
        parts.append((packed, cited_author_words(piece)))
    return parts


def _comparable(n: set[str], s_r: set[str]) -> bool:
    """R16: (S_R non-empty and a shared script) or a mixed word."""
    return (bool(s_r) and bool(_scripts(n) & _scripts(s_r))) or any(mixed(w) for w in n)


def author_verdict(cited: dict[str, list[str]], record_authors: str | None) -> str:
    s_r = record_surnames(record_authors)
    conflict = False
    agree = False
    for form in AUTHOR_FORMS:
        for value in cited.get(form, []):
            w = cited_author_words(value)  # whole-value guard
            if _comparable(w, s_r) and not (w & s_r):
                conflict = True
            for packed, n in author_parts(form, value):
                if not _comparable(n, s_r):
                    continue  # set aside
                if not (n & s_r):
                    conflict = True
                elif not packed:
                    agree = True
    if conflict:
        return "CONFLICT"
    return "AGREE" if agree else "INSUFFICIENT"


# ---------------------------------------------------------------------------------------------------------------------
# Section 4.2: title, and 4.2a: genre


def _first_occurrence(inner: list[str], outer: list[str]) -> int | None:
    n = len(inner)
    for i in range(len(outer) - n + 1):
        if outer[i : i + n] == inner:
            return i
    return None


def _contains(inner: list[str], outer: list[str]) -> bool:
    return _first_occurrence(inner, outer) is not None


def relation(t: list[str], t_r: list[str]) -> str:
    """Relation of two non-empty word sequences (4.2 items 1 to 6)."""
    if t == t_r:
        return "EQUAL"
    if len(t) < len(t_r) and _contains(t, t_r):
        return "SHORTER"
    if len(t_r) < len(t) and _contains(t_r, t):
        return "LONGER"
    if set(t) & set(t_r):
        return "OVERLAP"
    if _scripts(t) & _scripts(t_r):
        return "DISJOINT"
    return "INCOMPARABLE"


def extra_words(rel: str, t: list[str], t_r: list[str]) -> tuple[list[str], list[str]]:
    """(cited extra words, record extra words) of a value whose relation is not EQUAL."""
    if rel == "SHORTER":
        start = _first_occurrence(t, t_r)
        if start is None:
            raise AssertionError("model invariant")
        return [], t_r[:start] + t_r[start + len(t) :]
    if rel == "LONGER":
        start = _first_occurrence(t_r, t)
        if start is None:
            raise AssertionError("model invariant")
        return t[:start] + t[start + len(t_r) :], []
    record, cited = set(t_r), set(t)
    return [w for w in t if w not in record], [w for w in t_r if w not in cited]


def designates(rel: str, t: list[str], t_r: list[str]) -> bool:
    """R18: every relation but EQUAL is checked; an extra word that names a designation or is mixed, or a DP phrase
    that occurs (B7) on one side only."""
    if rel == "EQUAL":
        return False
    cited_extra, record_extra = extra_words(rel, t, t_r)
    if any(names_designation(w) or mixed(w) for w in cited_extra + record_extra):
        return True
    for phrase in DP:
        p = words(phrase)
        if phrase_occurs(p, t) != phrase_occurs(p, t_r):
            return True
    return False


def main_title_words(record_title: str | None) -> list[str] | None:
    """R19: words of the record's title before the first separator; None when there is no separator."""
    if record_title is None:
        return None
    match = MAIN_TITLE_SEPARATOR.search(record_title)
    if match is None:
        return None
    return words(record_title[: match.start()])


def title_relation(cited_titles: list[str], record_title: str | None) -> tuple[str, bool, int, int]:
    """(pair relation, whether any value designates, number of values that agree, number of values compared)."""
    t_r = words(record_title)
    if not t_r:
        return "MISSING", False, 0, 0
    main = main_title_words(record_title)
    best: int | None = None
    any_designates = False
    agreeing = 0
    compared = 0
    for value in cited_titles:
        t = words(value)
        if not t:
            continue
        compared += 1
        rel = relation(t, t_r)
        if designates(rel, t, t_r):
            any_designates = True
        if rel == "EQUAL" or (rel == "SHORTER" and main is not None and t == main):
            agreeing += 1
        rank = RELATION_RANK.index(rel)
        if best is None or rank < best:
            best = rank
    if best is None:
        return "MISSING", False, 0, 0
    return RELATION_RANK[best], any_designates, agreeing, compared


def title_verdict(rel: str, designation: bool, agreeing: int, compared: int) -> tuple[str, str | None]:
    """R19: (title verdict, its NOT_ESTABLISHED reason or None)."""
    if designation or rel == "DISJOINT":
        return "CONFLICT", None
    if rel == "MISSING":
        return "INSUFFICIENT", None  # no compared value: never a vacuous agreement
    if agreeing == compared:
        return "AGREE", None
    if agreeing > 0:
        return "NOT_ESTABLISHED", VALUES_DIFFER
    return "NOT_ESTABLISHED", NOT_ESTABLISHED_REASON[rel]


def genre_check(genres: list[str], record_title: str | None) -> tuple[bool, bool]:
    """Section 4.2a (R20): (some genre value designates, some genre value is unmatched)."""
    t_r = words(record_title)
    record = set(t_r)
    any_designates = False
    any_unmatched = False
    for g in genres:
        gw = words(g)
        designating = any((names_designation(w) or mixed(w)) and w not in record for w in gw) or any(
            phrase_occurs(words(phrase), gw) and not phrase_occurs(words(phrase), t_r) for phrase in DP
        )
        if designating:
            any_designates = True
        elif any(w not in record for w in gw):
            any_unmatched = True
    return any_designates, any_unmatched


# ---------------------------------------------------------------------------------------------------------------------
# Section 4.3: recorded, never decisive (copied from bib_reference.py)


def cited_year(date: str | None, year: str | None) -> int | None:
    for source in (date, year):
        if source is None:
            continue
        match = YEAR.search(source)
        if match is not None:
            return int(match.group(1))
    return None


def year_verdict(c_year: int | None, r_year: int | None) -> str:
    if c_year is None or r_year is None:
        return "INSUFFICIENT"
    return "SAME" if c_year == r_year else "DIFFERENT"


def periodical_verdict(c_periodical: str | None, r_journal: str | None) -> str:
    a = words(c_periodical)
    b = words(r_journal)
    if not a or not b:
        return "INSUFFICIENT"
    return "SAME" if a == b else "DIFFERENT"


# ---------------------------------------------------------------------------------------------------------------------
# Section 5 and the public comparison


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def _insufficient() -> dict[str, Any]:
    return {
        "authors": "INSUFFICIENT",
        "title": "INSUFFICIENT",
        "title_relation": "MISSING",
        "designation": False,
        "year": "INSUFFICIENT",
        "periodical": "INSUFFICIENT",
        "volume": "NOT_IN_RECORD",
        "issue": "NOT_IN_RECORD",
        "pages": "NOT_IN_RECORD",
        "object": "INSUFFICIENT",
        "reasons": [],
        "readings": 1,
    }


def _one_reading(
    titles: list[str],
    genres: list[str],
    cited_authors: dict[str, list[str]],
    r_title: str | None,
    r_authors: str | None,
) -> dict[str, Any]:
    """Sections 4.1, 4.2, 4.2a and 5 under one reading (R21)."""
    authors = author_verdict(cited_authors, r_authors)
    rel, title_designation, agreeing, compared = title_relation(titles, r_title)
    title, title_reason = title_verdict(rel, title_designation, agreeing, compared)
    genre_designation, genre_unmatched = genre_check(genres, r_title)
    designation = title_designation or genre_designation
    reasons: list[str] = []
    if authors == "CONFLICT" or title == "CONFLICT" or designation:
        obj = "MATERIAL_CONFLICT"
        if authors == "CONFLICT":
            reasons.append("BIB_AUTHORS_DISJOINT")
        if rel == "DISJOINT":
            reasons.append("BIB_TITLE_DISJOINT")
        if designation:
            reasons.append("BIB_TITLE_RELATED_OBJECT")
    else:
        if title_reason is not None:
            reasons.append(title_reason)
        if genre_unmatched:
            reasons.append(GENRE_UNMATCHED)
        if title == "AGREE" and rel == "SHORTER" and authors != "AGREE":
            reasons.append("BIB_TITLE_SHORTENED")  # B5: a main title alone needs an agreeing author
        if reasons:
            obj = "NOT_ESTABLISHED"
        elif title == "AGREE":
            obj = "COMPATIBLE"
        else:
            obj = "INSUFFICIENT"
    return {
        "authors": authors,
        "title": title,
        "title_relation": rel,
        "designation": designation,
        "object": obj,
        "reasons": reasons,
    }


def compare(fields: dict[str, Any] | None, record: dict[str, Any] | None) -> dict[str, Any]:
    """Sections 3, 4 and 5 for one DESCRIBED unit's fields and one record."""
    if not isinstance(fields, dict) or not isinstance(record, dict):
        return _insufficient()

    r_title = _str_or_none(record.get("title"))
    r_authors = _str_or_none(record.get("authors"))
    r_journal = _str_or_none(record.get("journal"))
    r_year_raw = record.get("original_year")
    r_year = r_year_raw if isinstance(r_year_raw, int) and not isinstance(r_year_raw, bool) else None

    titles = _str_list(fields.get("titles"))
    genres = _str_list(fields.get("genres"))
    cited_authors = {form: _str_list(fields.get(form)) for form in AUTHOR_FORMS}
    compared = [*titles, *genres, *(v for form in AUTHOR_FORMS for v in cited_authors[form]), r_title, r_authors]
    readings = READINGS if any(has_invisible(s) for s in compared) else READINGS[:1]

    results = []
    for read in readings:
        results.append(
            _one_reading(
                [read(t) for t in titles],
                [read(g) for g in genres],
                {form: [read(v) for v in cited_authors[form]] for form in AUTHOR_FORMS},
                None if r_title is None else read(r_title),
                None if r_authors is None else read(r_authors),
            )
        )
    worst = max(OBJECT_RANK[r["object"]] for r in results)
    giving = [r for r in results if OBJECT_RANK[r["object"]] == worst]
    reported = giving[0]  # the first reading, in the order of section 3.1, that gives the worst result
    reasons = sorted({reason for r in giving for reason in r["reasons"]})

    year = year_verdict(cited_year(_str_or_none(fields.get("date")), _str_or_none(fields.get("year"))), r_year)
    periodical = periodical_verdict(_str_or_none(fields.get("periodical")), r_journal)
    return {
        "authors": reported["authors"],
        "title": reported["title"],
        "title_relation": reported["title_relation"],
        "designation": reported["designation"],
        "year": year,
        "periodical": periodical,
        "volume": "NOT_IN_RECORD",
        "issue": "NOT_IN_RECORD",
        "pages": "NOT_IN_RECORD",
        "object": reported["object"],
        "reasons": reasons,
        "readings": len(results),
    }


def _self_check() -> None:
    """The lexicon is stated as folded: fold and the skeleton leave every DW and NP entry unchanged, no entry is mixed,
    and each DP phrase has words. The characters section 3.1 names are invisible. The examples of section 3.2 hold."""
    for w in DW | NP:
        if fold(w) != w or words(w) != [w] or mixed(w) or skeleton(w) != w:
            raise AssertionError(w)
    small_capitals = "".join(chr(cp) for cp in (0x1D07, 0x0280, 0x0280, 0x1D00, 0x1D1B, 0x1D1C, 0x1D0D))
    if skeleton(small_capitals) != "erratum" or skeleton("err" + chr(0x0131) + "tum") != "erritum":
        raise AssertionError("skeleton")
    japanese = "".join(chr(cp) for cp in (0x65E5, 0x672C, 0x3054, 0x30AB, 0x30CA))
    korean = "".join(chr(cp) for cp in (0x97D3, 0xD55C, 0xAD6D))
    if mixed(japanese) or mixed(korean) or not mixed("err" + chr(0x0430) + "tum"):
        raise AssertionError("mixed")
    for phrase in DP:
        if not words(phrase):
            raise AssertionError(phrase)
    for cp in (0x00AD, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x202E, 0x2066, 0xFE0F, 0x3164, 0x115F, 0x2065, 0x0080):
        if not is_invisible(chr(cp)):
            raise AssertionError(hex(cp))
    if is_invisible("\t") or is_invisible(" "):
        raise AssertionError("whitespace")
    if relation(["a"], ["a", "b"]) != "SHORTER" or relation(["a", "b"], ["a"]) != "LONGER":
        raise AssertionError("relation")
    if main_title_words("Gene therapy (Pub 2)") != ["gene", "therapy"] or main_title_words("A-B c") is not None:
        raise AssertionError("main title")


_self_check()
