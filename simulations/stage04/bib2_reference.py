"""Independent reference model of the bibliographic-object consistency layer bib-2 (owner decisions D-086, D-087).

Written from ``docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md`` (sections 2 to 5 and 8, including the
amendment of section 4.2 that checks designation for every title value whose relation is not EQUAL) and, where that
text says "unchanged from bib-1", from section 2.1 step 4 and section 3 of ``BIBLIOGRAPHIC_SPEC.md``. The parsing,
value cleaning and word functions are copied from the earlier independent bib-1 reference ``bib_reference.py`` (which
bib-2 declares unchanged), so this file stands alone. It imports no production code: nothing from ``citerift`` and
nothing from the other reference modules, only the standard library and ``mwparserfromhell`` (the parser the
specification names). Its alias profile is ``bib-reference-profile.json`` next to this file, the profile extracted
separately for ``bib_reference.py`` from the raw ``Module:Citation/CS1/Configuration`` revisions the specification
names (en 1384336575, ar 76424085), not copied from the production profile. Simple code is preferred to fast code.

Public API: ``load_profile``, ``describe`` (section 2.1 steps 1 to 8: ``{"state": "UNAVAILABLE", "reason": r}`` or
``{"state": "DESCRIBED", "fields": C}``; the caller handles ABSENT units) and ``compare`` (sections 3, 4 and 5, both
readings of section 3.1).

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
    as U+FEFF (and then, as a non-whitespace top-level Text node, gives BIB_PARSE_FAILED at step 3).
R3. (2.1 step 2) The bound is ``len(text) > 16384`` on the decoded ``str``, checked before parsing.
R4. (2.1 step 3) "Ignoring top-level Text nodes whose value is empty after ``str.strip()``": every other top-level
    node (comment, tag, a second template, other text) gives BIB_PARSE_FAILED. Any template counts, whatever its name.
    Exceptions are caught over parsing, reading ``template.params`` (``showkey``, ``name``, ``value``) and cleaning;
    only the effective values of arguments whose name belongs to a family are cleaned (the others are not fields), so
    an exception while cleaning a replaced or a non-family value cannot occur.
R5. (2.1 step 4) A later parameter of the same name replaces the earlier one even when its value is empty (the
    effective value is then absent); a Python ``dict`` keeps the first insertion position. The name is exactly
    ``str(param.name).strip()``: a comment or a template inside a name is kept, so such a name matches no alias.
R6. (2.1 step 5) Cleaning is bib-1's, copied unchanged from ``bib_reference.py`` (its reading R21): each top-level
    node is ``Wikicode([node]).strip_code(normalize=True, collapse=True)``; Text, HTMLEntity, Wikilink, ExternalLink
    and the eleven inline tags (tag name compared after ``strip().lower()``) join as written; every other node gets one
    space on each side; runs of ``\\s`` become one space; ``str.strip()``; empty is absent; lone surrogates become
    U+FFFD. Format characters are kept.
R7. (2.1 step 6) A name contributes to every family one of whose aliases it matches. In bib-reference-profile.json the
    only such name is ar ``host`` (AuthorList-Last ``host#`` with an empty ``#``, and Authors ``host``): its value is in
    both ``authors`` and ``author_lists`` and counts twice for the bound of step 7. ``#`` matches the empty string or
    ``[1-9][0-9]*`` (ASCII), whole name, case-sensitive.
R8. (2.1 step 6) The ScriptTitle/ScriptChapter prefix is removed once from the cleaned value, the rest stripped with
    ``str.strip()``; an empty rest is absent. ``pages`` is the first value over the Page and Pages aliases together.
R9. (2.1 step 7) "Values" are effective arguments with a non-absent value after step 6. The 64-value bounds count
    ``titles`` and, separately, ``authors`` + ``author_lists`` + ``vauthors``. The 4,096 code-point bound counts every
    value of every family of step 6, including the values after the first of ``periodical``, ``date``, ``year``,
    ``volume``, ``issue`` and ``pages`` (bib-1 states "all values, not only the first"; bib-2 says "all values of all
    families"), and titles after the prefix removal of step 6. Code points are ``len`` of the ``str`` after U+FFFD
    replacement.
R10. (3.1) A format character is a code point with ``unicodedata.category(c) == "Cf"`` in the running Python's Unicode
    database. The compared strings are the cited title values (after step 6), the cited author values of the three
    forms, the record's title and the record's authors; periodical, journal, date and year are never edited and do not
    count for "some string holds one", so periodical and year are equal in both readings.
R11. (3.1) Two readings are made exactly when some compared string holds a format character (``readings`` = 2), else
    one (``readings`` = 1). The pair's object verdict is the worse in MATERIAL_CONFLICT > NOT_ESTABLISHED >
    INSUFFICIENT > COMPATIBLE; the reported field verdicts (authors, title, title_relation, designation) are the
    split reading's when it gives that object verdict, else the joined reading's; reasons are the union of the reasons
    of every reading that gives it.
R12. (3.2) Words, folding, scripts, name words, particles, initials and ``S_R`` are copied from ``bib_reference.py``
    (its readings R8 to R10 and R22): initials are tested on ``str.split()`` tokens of the raw string, before folding.
R13. (4.1) Splitting uses the characters ``;`` ``؛`` (list separators) and additionally ``,`` ``،`` for ``vauthors``.
    For every form an empty piece (after ``str.strip()``) is dropped. A conjunction is the character ``&`` anywhere in
    the piece, or a ``str.split()`` token whose ``casefold()`` is ``and`` (``and,`` is not one). Commas are counted as
    characters ``,`` and ``،``. Packed or person, ``N`` is the piece's cited name words.
R14. (4.1) Author verdict: CONFLICT if some comparable part has ``N ∩ S_R = ∅`` (person or packed alike); else AGREE
    if some comparable person part has ``N ∩ S_R ≠ ∅``; else INSUFFICIENT. AGREE has no effect on the object verdict.
R15. (4.2) SHORTER and LONGER need a contiguous subsequence of strictly smaller length; OVERLAP uses word sets.
    "Leftmost occurrence" is the smallest start index. A value with empty ``words`` is skipped. Ties between values
    keep the first value of the ``titles`` list.
R16. (4.2, amended) Designation is evaluated for every value whose own relation is not EQUAL (SHORTER, LONGER,
    OVERLAP, DISJOINT, INCOMPARABLE), whichever value is chosen; one designating value makes the pair designate.
    DW words are matched against the extra words (lists of folded words); DP phrases as ``words(phrase)``
    contiguous in ``T`` but not in ``T_R``, or in ``T_R`` but not in ``T``. The DP clause is evaluated only for a
    value whose relation is not EQUAL (an EQUAL value cannot satisfy it anyway).
R17. (4.2, 5) When the chosen relation is DISJOINT and some value also designates, the title verdict is CONFLICT
    and both ``BIB_TITLE_DISJOINT`` and ``BIB_TITLE_RELATED_OBJECT`` are given: section 5 lists the reasons by their
    own conditions ("relation DISJOINT", "designation"), which the else-chain of section 4.2 does not restrict.
R18. (5) A NOT_ESTABLISHED reason is given only when the object is NOT_ESTABLISHED; a MATERIAL_CONFLICT pair whose
    title is also NOT_ESTABLISHED (authors CONFLICT) carries only the conflict reasons. COMPATIBLE and INSUFFICIENT
    carry none.
R19. (4.3) Year and periodical are bib-1's (copied): ``R.original_year`` counts only as a non-bool ``int``;
    volume, issue and pages are always NOT_IN_RECORD.
R20. (B8) ``fields`` or ``record`` that is not a dict gives the INSUFFICIENT result with relation MISSING and one
    reading. A record field of the wrong type (title, authors, journal not ``str``; original_year not a non-bool
    ``int``) is absent. Non-string entries of the ``fields`` lists and non-string scalar fields are ignored.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import mwparserfromhell

MODEL_VERSION = "bib-2-reference/1"
PARSER_VERSION = "0.7.2"

TITLE_KEYS = ("Title", "ScriptTitle", "TransTitle", "Chapter", "ScriptChapter", "TransChapter")
SCRIPT_KEYS = ("ScriptTitle", "ScriptChapter")
# Section 2.1 step 6: list families (all values) and single-value families (first value, recorded only).
LIST_FAMILIES: dict[str, tuple[str, ...]] = {
    "titles": TITLE_KEYS,
    "authors": ("AuthorList-Last",),
    "author_lists": ("Authors",),
    "vauthors": ("Vauthors",),
}
AUTHOR_FORMS = ("authors", "author_lists", "vauthors")
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
LIST_SEPARATORS = re.compile("[;\u061b]")  # ; and the Arabic semicolon
VANCOUVER_SEPARATORS = re.compile("[;\u061b,\u060c]")  # list separators and commas (, and the Arabic comma)
COMMAS = (",", "\u060c")

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
    "LONGER": "BIB_TITLE_EXTENDED",
    "OVERLAP": "BIB_TITLE_PARTIAL",
    "INCOMPARABLE": "BIB_TITLE_INCOMPARABLE",
}


# ---------------------------------------------------------------------------------------------------------------------
# Profile and engine configuration (R1, R7)


def load_profile(path: Path | str) -> dict[str, Any]:
    """Read the alias profile (bib-reference-profile.json)."""
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


def _matches(name: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.fullmatch(name) is not None for p in patterns)


def _families_of(name: str, table: dict[str, list[re.Pattern[str]]]) -> list[str]:
    """Every family (R7) one of whose CS1 keys has an alias matching ``name``."""
    return [fam for fam, keys in ALL_FAMILIES.items() if any(_matches(name, table[key]) for key in keys)]


# ---------------------------------------------------------------------------------------------------------------------
# Section 2.1: cited object (describe)


JOINED = (
    mwparserfromhell.nodes.Text,
    mwparserfromhell.nodes.HTMLEntity,
    mwparserfromhell.nodes.Wikilink,
    mwparserfromhell.nodes.ExternalLink,
)
JOINED_TAGS = ("i", "b", "sub", "sup", "span", "small", "big", "u", "s", "em", "strong")


def _is_joined(node: Any) -> bool:
    if isinstance(node, JOINED):
        return True
    return isinstance(node, mwparserfromhell.nodes.Tag) and str(node.tag).strip().lower() in JOINED_TAGS


def _clean(value: Any) -> str | None:
    """Step 5 (bib-1 step 4, unchanged; copied from bib_reference.py)."""
    pieces = []
    for node in value.nodes:
        piece = mwparserfromhell.wikicode.Wikicode([node]).strip_code(normalize=True, collapse=True)
        pieces.append(piece if _is_joined(node) else " " + piece + " ")
    cleaned = WHITESPACE_RUN.sub(" ", "".join(pieces)).strip()
    if cleaned == "":
        return None
    return "".join("\ufffd" if 0xD800 <= ord(ch) <= 0xDFFF else ch for ch in cleaned)


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
            effective[str(param.name).strip()] = param.value  # a dict keeps the first position of a name
        cleaned: list[tuple[str, str | None, list[str]]] = []
        for name, raw in effective.items():
            families = _families_of(name, table)
            if families:
                cleaned.append((name, _clean(raw), families))
    except Exception:
        return _unavailable(PARSE_FAILED)

    # Step 6.
    values: dict[str, list[str]] = {fam: [] for fam in ALL_FAMILIES}
    for name, value, families in cleaned:
        if value is None:
            continue
        for fam in families:
            if fam == "titles" and any(_matches(name, table[key]) for key in SCRIPT_KEYS):
                rest = SCRIPT_PREFIX.sub("", value, count=1).strip()
                if rest != "":
                    values[fam].append(rest)
            else:
                values[fam].append(value)

    # Step 7.
    if len(values["titles"]) > MAX_VALUES or sum(len(values[f]) for f in AUTHOR_FORMS) > MAX_VALUES:
        return _unavailable(VALUE_LIMIT)
    if sum(len(v) for fam in ALL_FAMILIES for v in values[fam]) > MAX_DESCRIPTION:
        return _unavailable(DESCRIPTION_LIMIT)

    # Step 8.
    fields: dict[str, Any] = {fam: list(values[fam]) for fam in LIST_FAMILIES}
    for fam in SINGLE_FAMILIES:
        fields[fam] = values[fam][0] if values[fam] else None
    return {"state": "DESCRIBED", "fields": fields}


# ---------------------------------------------------------------------------------------------------------------------
# Section 3: normalization (3.2 copied from bib_reference.py; 3.1 readings)


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


def has_format(s: str | None) -> bool:
    return s is not None and any(unicodedata.category(c) == "Cf" for c in s)


def remove_format(s: str | None) -> str | None:
    if s is None:
        return None
    return "".join(c for c in s if unicodedata.category(c) != "Cf")


# ---------------------------------------------------------------------------------------------------------------------
# Section 4.1: authors


def author_parts(form: str, value: str) -> list[tuple[bool, set[str]]]:
    """(packed, N) for every non-empty part of one cited author value of the given form."""
    splitter = VANCOUVER_SEPARATORS if form == "vauthors" else LIST_SEPARATORS
    parts = []
    for piece in splitter.split(value):
        if piece.strip() == "":
            continue
        commas = sum(piece.count(c) for c in COMMAS)
        conjunction = "&" in piece or any(tok.casefold() == "and" for tok in piece.split())
        if form == "vauthors":
            packed = False
        elif form == "authors":
            packed = conjunction or commas >= 2
        else:  # author_lists
            packed = conjunction or commas >= 1
        parts.append((packed, cited_author_words(piece)))
    return parts


def author_verdict(cited: dict[str, list[str]], record_authors: str | None) -> str:
    s_r = record_surnames(record_authors)
    record_scripts = _scripts(s_r)
    conflict = False
    agree = False
    for form in AUTHOR_FORMS:
        for value in cited.get(form, []):
            for packed, n in author_parts(form, value):
                if not (_scripts(n) & record_scripts):
                    continue  # not comparable: set aside
                if not (n & s_r):
                    conflict = True
                elif not packed:
                    agree = True
    if conflict:
        return "CONFLICT"
    return "AGREE" if agree else "INSUFFICIENT"


# ---------------------------------------------------------------------------------------------------------------------
# Section 4.2: title


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
    """R16 (amended 4.2): every relation but EQUAL is checked."""
    if rel == "EQUAL":
        return False
    cited_extra, record_extra = extra_words(rel, t, t_r)
    if any(w in DW for w in cited_extra) or any(w in DW for w in record_extra):
        return True
    for phrase in DP:
        p = words(phrase)
        if _contains(p, t) != _contains(p, t_r):
            return True
    return False


def title_relation(cited_titles: list[str], record_title: str | None) -> tuple[str, bool]:
    """(relation of the chosen value, whether any value designates)."""
    t_r = words(record_title)
    if not t_r:
        return "MISSING", False
    best: int | None = None
    any_designates = False
    for value in cited_titles:
        t = words(value)
        if not t:
            continue
        rel = relation(t, t_r)
        if designates(rel, t, t_r):
            any_designates = True
        rank = RELATION_RANK.index(rel)
        if best is None or rank < best:
            best = rank
    if best is None:
        return "MISSING", False
    return RELATION_RANK[best], any_designates


def title_verdict(rel: str, designation: bool) -> str:
    if designation or rel == "DISJOINT":
        return "CONFLICT"
    if rel in ("EQUAL", "SHORTER"):
        return "AGREE"
    if rel in NOT_ESTABLISHED_REASON:
        return "NOT_ESTABLISHED"
    return "INSUFFICIENT"  # MISSING


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
    titles: list[str], cited_authors: dict[str, list[str]], r_title: str | None, r_authors: str | None
) -> dict[str, Any]:
    """Sections 4.1, 4.2 and 5 under one reading."""
    authors = author_verdict(cited_authors, r_authors)
    rel, designation = title_relation(titles, r_title)
    title = title_verdict(rel, designation)
    reasons: list[str] = []
    if authors == "CONFLICT" or title == "CONFLICT":
        obj = "MATERIAL_CONFLICT"
        if authors == "CONFLICT":
            reasons.append("BIB_AUTHORS_DISJOINT")
        if rel == "DISJOINT":
            reasons.append("BIB_TITLE_DISJOINT")
        if designation:
            reasons.append("BIB_TITLE_RELATED_OBJECT")
    elif title == "NOT_ESTABLISHED":
        obj = "NOT_ESTABLISHED"
        reasons.append(NOT_ESTABLISHED_REASON[rel])
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
    cited_authors = {form: _str_list(fields.get(form)) for form in AUTHOR_FORMS}
    compared = [*titles, *(v for form in AUTHOR_FORMS for v in cited_authors[form]), r_title, r_authors]

    split = _one_reading(titles, cited_authors, r_title, r_authors)
    results = [split]
    if any(has_format(s) for s in compared):
        joined = _one_reading(
            [remove_format(t) or "" for t in titles],
            {form: [remove_format(v) or "" for v in cited_authors[form]] for form in AUTHOR_FORMS},
            remove_format(r_title),
            remove_format(r_authors),
        )
        results.append(joined)
    worst = max(OBJECT_RANK[r["object"]] for r in results)
    giving = [r for r in results if OBJECT_RANK[r["object"]] == worst]
    reported = giving[0]  # the split reading when both give it
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
    """The lexicon is stated as folded: fold leaves every DW and NP entry unchanged and each DP phrase has words. The
    format characters 3.1 names are of category Cf and no word character (so the split reading separates words)."""
    for w in DW | NP:
        if fold(w) != w or words(w) != [w]:
            raise AssertionError(w)
    for phrase in DP:
        if not words(phrase):
            raise AssertionError(phrase)
    for c in "\u00ad\u200b\u200c\u200d\u2060\ufeff\u200e\u200f\u202a\u202e\u2066\u2069":
        if unicodedata.category(c) != "Cf" or WORD.fullmatch(fold(c)) is not None:
            raise AssertionError(hex(ord(c)))
    if relation(["a"], ["a", "b"]) != "SHORTER" or relation(["a", "b"], ["a"]) != "LONGER":
        raise AssertionError("relation")


_self_check()
