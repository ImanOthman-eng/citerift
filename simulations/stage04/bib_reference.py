"""Independent reference model of the bibliographic-object consistency layer bib-1 (owner decision D-083, item 3).

Written from ``docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC.md`` only (sections 2 to 5 and 8). It imports
no production code: nothing from ``citerift``, only the standard library and ``mwparserfromhell`` (the parser the
specification names). Its alias profile, ``bib-reference-profile.json`` next to this file, was extracted separately
from the raw ``Module:Citation/CS1/Configuration`` revisions the specification names (en 1384336575, ar 76424085), not
copied from the production profile. Simple code is preferred to fast code throughout.

Public API: ``load_profile``, ``cited_object`` (section 2.1 steps 2 to 5; ``None`` stands for the absent object
``C = ⊥``) and ``compare`` (sections 3, 4 and 5).

Readings of the specification
-----------------------------

Where the text leaves a choice open, the most literal reading is taken. Each such point:

R1. (2.1 step 2) "whitespace-only text nodes": a top-level ``Text`` node whose value is empty after ``str.strip()``
    (so an empty Text node is also ignored). Every other top-level node (comment, tag, link, a second template, any
    other text) makes ``C = ⊥``. Any template counts, whatever its name. An exception raised by the parser gives
    ``C = ⊥`` (B8).
R2. (2.1 step 3) A later parameter of the same name replaces the earlier one even when its value is empty (the
    effective value is then absent); the effective argument keeps the source position of the first occurrence of
    its name. The name is ``str(param.name).strip()`` exactly (Python ``str.strip``); a comment or inner whitespace
    inside a name is kept, so such a name matches no alias.
R3. (2.1 step 4, amended) Whitespace runs are runs of Python ``re`` ``\\s`` on ``str`` (Unicode; includes
    U+001C..U+001F) and the final strip is ``str.strip()``, as the amended text states.
R4. (2.1 step 5) A family's value list is in source order of the effective arguments (by first occurrence of the
    name), not in the order of the CS1 keys inside the family. A name contributes to every family one of whose
    aliases it matches (in bib-reference-profile.json no name matches aliases of two families).
R5. (2.1 step 5, amended) The ScriptTitle/ScriptChapter language prefix (one match of the regex at the start,
    ASCII letters/digits as written) is removed from the cleaned value of step 4, the rest is stripped again with
    ``str.strip()`` and an empty rest is absent: ``script-title=ja: X`` gives ``"X"``, ``script-title=ja:`` gives no
    value.
R6. (2.1 step 5) ``pages`` is the first value, in source order, of the effective arguments whose name matches an
    alias of Page or of Pages (one combined family). ``periodical``, ``date``, ``year``, ``volume``, ``issue``: first
    value in source order of their family. Values are the cleaned (step 4) strings.
R7. (2.2) ``#`` in an alias matches the empty string or ``[1-9][0-9]*`` with ASCII digits only; matching is of the
    whole name, case-sensitive; several ``#`` in one alias would each match independently. An unknown wiki or a
    malformed profile gives ``C = ⊥``.
R8. (3) ``fold`` is applied in the stated order: NFKD, then removal of Mn/Mc/Me, then ``casefold()``. Results depend
    on the Unicode database of the running Python (``unicodedata.unidata_version``).
R9. (3) Name words: the regex ``[^\\W_]+`` is applied directly to ``fold(value)`` after the et-al removal; fold is
    not applied a second time. Length in code points and "digits only" by ``str.isdecimal()`` (amended text);
    ``script(w)`` uses ``str.isdecimal()`` and is ``None`` when the character has no Unicode name (amended text).
R10. (3) Record author words: name words of each ``;``-separated part of ``R.authors`` (the et-al removal therefore
    acts per part).
R11. (4.2) A value ``t`` whose ``words(t)`` is empty is skipped; if no value remains, or ``T_R`` is empty, the
    relation is MISSING. "Ties between values keep the first value in field order": field order is the order of the
    ``titles`` value list (source order, R4).
R12. (4.2) CONTAINED uses contiguous subsequences of the word sequences; OVERLAP and the extra words of OVERLAP use
    word membership (sets). For CONTAINED with ``T`` inside ``T_R`` there are no extra words; "leftmost occurrence
    of ``T_R``" is the smallest start index.
R13. (4.2, amended) Designation is false unless the chosen value's relation is CONTAINED or OVERLAP; for those two,
    both the DW extra-word clause and the DP phrase clause apply. DP phrases are compared as ``words(phrase)``; DW
    entries are taken as given (stated to be folded; ``_self_check`` confirms ``fold`` leaves each unchanged).
R14. (4.2) Title verdict: EQUAL → AGREE; CONTAINED/OVERLAP → CONFLICT with designation, else COMPATIBLE; DISJOINT →
    CONFLICT; INCOMPARABLE, MISSING → INSUFFICIENT. (With R13 no relation is covered by two rules.)
R15. (4.3) Year: Python ``re`` as written (``\\d`` is any Unicode decimal digit, now stated). The alternatives start
    with a literal ASCII ``1`` or ``2``, so ``19`` followed by two Arabic-Indic digits matches (``int`` converts it)
    but a year written wholly in Arabic-Indic digits does not match; section 9 states the opposite (see the report).
    If ``C.date`` has no match, ``C.year`` is searched. ``R.original_year`` counts only as a non-bool ``int``.
R16. (4.3, amended) Periodical: SAME needs both word lists non-empty and equal (now stated in the text).
R17. (4.3, 5) ``volume``, ``issue`` and ``pages`` are always NOT_IN_RECORD, also when ``C = ⊥`` or the record is
    absent (they are not comparable fields).
R18. (5) Reasons are given only with MATERIAL_CONFLICT: BIB_AUTHORS_DISJOINT if authors CONFLICT,
    BIB_TITLE_DISJOINT if the relation is DISJOINT, BIB_TITLE_RELATED_OBJECT if the chosen value designates;
    sorted. Designation always implies a title CONFLICT, so the list is never empty for a conflict.
R19. (B8) A record that is not a dict is absent; a record field of the wrong type (title/authors/journal not ``str``,
    original_year not a non-bool ``int``) is absent. A record whose four fields are all absent is "a record with no
    bibliographic fields" and gives INSUFFICIENT through the ordinary rules. ``cited`` that is not a dict is absent;
    non-string entries of its lists and non-string scalar fields are ignored. Absent ``authors``/``title`` strings
    behave like empty word sets.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import mwparserfromhell

MODEL_VERSION = "bib-1-reference/2"

TITLE_KEYS = ("Title", "ScriptTitle", "TransTitle", "Chapter", "ScriptChapter", "TransChapter")
SCRIPT_KEYS = ("ScriptTitle", "ScriptChapter")
AUTHOR_KEYS = ("AuthorList-Last", "Authors", "Vauthors")
SINGLE_FAMILIES = {
    "periodical": ("Periodical",),
    "date": ("Date",),
    "year": ("Year",),
    "volume": ("Volume",),
    "issue": ("Issue",),
    "pages": ("Page", "Pages"),
}

WHITESPACE_RUN = re.compile(r"\s+")
SCRIPT_PREFIX = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:")
WORD = re.compile(r"[^\W_]+")
ET_AL = re.compile(r"\bet\.?\s*al\b\.?")
YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)")

DW_TEXT = (
    "addendum addenda clarification correction corrections corrigendum corrigenda erratum errata retraction "
    "retractions withdrawal removal comment comments reply replies "
    "تعليق التعليق تعقيب التعقيب رد الرد تصحيح التصحيح استدراك الاستدراك سحب السحب"
)
DW = frozenset(DW_TEXT.split(" "))
DP = ("expression of concern", "response to", "تعبير عن القلق")

RELATION_RANK = ("EQUAL", "CONTAINED", "OVERLAP", "DISJOINT", "INCOMPARABLE")


# ---------------------------------------------------------------------------------------------------------------------
# Profile


def load_profile(path: Path) -> dict[str, Any]:
    """Read the alias profile (bib-reference-profile.json)."""
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def _alias_regex(alias: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in alias.split("#")]
    return re.compile("(?:[1-9][0-9]*)?".join(parts))


def _name_matches(name: str, aliases: list[str]) -> bool:
    return any(_alias_regex(alias).fullmatch(name) is not None for alias in aliases)


def _aliases_of(profile: Any, wiki: Any, key: str) -> list[str] | None:
    """The alias list of one CS1 key for one wiki, or None when the profile does not provide it."""
    if not isinstance(profile, dict) or not isinstance(wiki, str):
        return None
    wikis = profile.get("wikis")
    if not isinstance(wikis, dict):
        return None
    entry = wikis.get(wiki)
    if not isinstance(entry, dict):
        return None
    aliases = entry.get("aliases")
    if not isinstance(aliases, dict):
        return None
    names = aliases.get(key)
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return None
    return names


# ---------------------------------------------------------------------------------------------------------------------
# Section 2.1: cited object


def _clean(value: Any) -> str | None:
    """Step 4: strip_code, each run of ``\\s`` becomes one space, ``str.strip()``; empty is absent."""
    text = value.strip_code(normalize=True, collapse=True)
    cleaned = WHITESPACE_RUN.sub(" ", text).strip()
    return cleaned if cleaned != "" else None


def cited_object(text: str, wiki: str, profile: dict[str, Any]) -> dict[str, Any] | None:
    """Section 2.1 steps 2 to 5. Returns None for C = ⊥."""
    if not isinstance(text, str):
        return None
    keys = TITLE_KEYS + AUTHOR_KEYS + tuple(k for keys in SINGLE_FAMILIES.values() for k in keys)
    alias_table: dict[str, list[str]] = {}
    for key in keys:
        names = _aliases_of(profile, wiki, key)
        if names is None:
            return None
        alias_table[key] = names

    # Step 2.
    try:
        code = mwparserfromhell.parse(text)
        nodes = [
            node
            for node in code.nodes
            if not (isinstance(node, mwparserfromhell.nodes.Text) and str(node.value).strip() == "")
        ]
    except Exception:
        return None
    if len(nodes) != 1 or not isinstance(nodes[0], mwparserfromhell.nodes.Template):
        return None
    template = nodes[0]

    # Step 3 and 4. A dict keeps the position of the first insertion of a key when the value is replaced.
    effective: dict[str, str | None] = {}
    try:
        for param in template.params:
            if not param.showkey:
                continue
            name = str(param.name).strip()
            effective[name] = _clean(param.value)
    except Exception:
        return None

    def family_values(family_keys: tuple[str, ...]) -> list[tuple[str, str]]:
        """(name, value) of the effective arguments of a family, in source order, absent values left out."""
        result = []
        for name, value in effective.items():
            if value is None:
                continue
            if any(_name_matches(name, alias_table[key]) for key in family_keys):
                result.append((name, value))
        return result

    titles: list[str] = []
    for name, value in family_values(TITLE_KEYS):
        if any(_name_matches(name, alias_table[key]) for key in SCRIPT_KEYS):
            rest = SCRIPT_PREFIX.sub("", value, count=1).strip()
            if rest == "":
                continue  # an empty rest is an absent value
            titles.append(rest)
        else:
            titles.append(value)

    result: dict[str, Any] = {
        "titles": titles,
        "authors": [value for _, value in family_values(AUTHOR_KEYS)],
    }
    # Section 2.1 step 6 (size bound): checked over every value of every family, before taking first values.
    others = [value for keys in SINGLE_FAMILIES.values() for _, value in family_values(keys)]
    every = [*titles, *result["authors"], *others]
    if len(titles) > 64 or len(result["authors"]) > 64 or sum(len(v) for v in every) > 4096:
        return None
    for field, family_keys in SINGLE_FAMILIES.items():
        values = family_values(family_keys)
        result[field] = values[0][1] if values else None
    return result


# ---------------------------------------------------------------------------------------------------------------------
# Section 3: normalization


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
    return [w for w in WORD.findall(edited) if len(w) >= 2 and not w.isdecimal()]


def record_author_words(authors: str | None) -> set[str]:
    if authors is None:
        return set()
    result: set[str] = set()
    for part in authors.split(";"):
        result.update(name_words(part))
    return result


def _scripts(ws: set[str] | list[str]) -> set[str]:
    return {s for s in (script(w) for w in ws) if s is not None}


# ---------------------------------------------------------------------------------------------------------------------
# Section 4: field verdicts


def author_verdict(cited_authors: list[str], record_authors: str | None) -> str:
    a_c: set[str] = set()
    for value in cited_authors:
        a_c.update(name_words(value))
    a_r = record_author_words(record_authors)
    if a_c & a_r:
        return "AGREE"
    if _scripts(a_c) & _scripts(a_r):
        return "CONFLICT"
    return "INSUFFICIENT"


def _is_contiguous(inner: list[str], outer: list[str]) -> bool:
    return _first_occurrence(inner, outer) is not None


def _first_occurrence(inner: list[str], outer: list[str]) -> int | None:
    n = len(inner)
    for i in range(len(outer) - n + 1):
        if outer[i : i + n] == inner:
            return i
    return None


def relation(t: list[str], t_r: list[str]) -> str:
    """Relation of two non-empty word sequences (4.2 items 1 to 5)."""
    if t == t_r:
        return "EQUAL"
    if _is_contiguous(t, t_r) or _is_contiguous(t_r, t):
        return "CONTAINED"
    if set(t) & set(t_r):
        return "OVERLAP"
    if _scripts(t) & _scripts(t_r):
        return "DISJOINT"
    return "INCOMPARABLE"


def extra_words(rel: str, t: list[str], t_r: list[str]) -> list[str]:
    if rel == "CONTAINED":
        start = _first_occurrence(t_r, t)
        if start is None:  # T inside T_R
            return []
        return t[:start] + t[start + len(t_r) :]
    if rel == "OVERLAP":
        record = set(t_r)
        return [w for w in t if w not in record]
    return []


def designates(rel: str, t: list[str], t_r: list[str]) -> bool:
    if rel not in ("CONTAINED", "OVERLAP"):
        return False
    if any(w in DW for w in extra_words(rel, t, t_r)):
        return True
    for phrase in DP:
        p = words(phrase)
        if _is_contiguous(p, t) and not _is_contiguous(p, t_r):
            return True
    return False


def title_relation(cited_titles: list[str], record_title: str | None) -> tuple[str, bool]:
    """(relation, designation) of the chosen value."""
    t_r = words(record_title)
    if not t_r:
        return "MISSING", False
    best: tuple[int, str, list[str]] | None = None
    for value in cited_titles:
        t = words(value)
        if not t:
            continue
        rel = relation(t, t_r)
        rank = RELATION_RANK.index(rel)
        if best is None or rank < best[0]:  # strict: ties keep the first value
            best = (rank, rel, t)
    if best is None:
        return "MISSING", False
    _, rel, t = best
    return rel, designates(rel, t, t_r)


def title_verdict(rel: str, designation: bool) -> str:
    if rel == "EQUAL":
        return "AGREE"
    if rel in ("CONTAINED", "OVERLAP"):
        return "CONFLICT" if designation else "COMPATIBLE"
    if rel == "DISJOINT":
        return "CONFLICT"
    return "INSUFFICIENT"


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
    }


def compare(cited: dict[str, Any] | None, record: dict[str, Any] | None) -> dict[str, Any]:
    """Sections 3, 4 and 5 for one cited object and one record."""
    if not isinstance(cited, dict) or not isinstance(record, dict):
        return _insufficient()

    r_title = _str_or_none(record.get("title"))
    r_authors = _str_or_none(record.get("authors"))
    r_journal = _str_or_none(record.get("journal"))
    r_year_raw = record.get("original_year")
    r_year = r_year_raw if isinstance(r_year_raw, int) and not isinstance(r_year_raw, bool) else None

    authors = author_verdict(_str_list(cited.get("authors")), r_authors)
    rel, designation = title_relation(_str_list(cited.get("titles")), r_title)
    title = title_verdict(rel, designation)
    year = year_verdict(cited_year(_str_or_none(cited.get("date")), _str_or_none(cited.get("year"))), r_year)
    periodical = periodical_verdict(_str_or_none(cited.get("periodical")), r_journal)

    reasons: list[str] = []
    if authors == "CONFLICT" or title == "CONFLICT":
        obj = "MATERIAL_CONFLICT"
        if authors == "CONFLICT":
            reasons.append("BIB_AUTHORS_DISJOINT")
        if rel == "DISJOINT":
            reasons.append("BIB_TITLE_DISJOINT")
        if designation:
            reasons.append("BIB_TITLE_RELATED_OBJECT")
    elif authors == "AGREE" or title in ("AGREE", "COMPATIBLE"):
        obj = "COMPATIBLE"
    else:
        obj = "INSUFFICIENT"

    return {
        "authors": authors,
        "title": title,
        "title_relation": rel,
        "designation": designation,
        "year": year,
        "periodical": periodical,
        "volume": "NOT_IN_RECORD",
        "issue": "NOT_IN_RECORD",
        "pages": "NOT_IN_RECORD",
        "object": obj,
        "reasons": sorted(reasons),
    }


def _self_check() -> None:
    """The lexicon is stated as folded: fold leaves every DW entry unchanged and each DP phrase has words."""
    for w in DW:
        if fold(w) != w or words(w) != [w]:
            raise AssertionError(w)
    for phrase in DP:
        if not words(phrase):
            raise AssertionError(phrase)


_self_check()
