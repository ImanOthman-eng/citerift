"""bib-2: the bibliographic-object consistency layer, version 2 (owner decisions D-083, D-086, D-087; normative
text docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC_2.md, which revises bib-1, BIBLIOGRAPHIC_SPEC.md).

A citation names a publication object twice: by its identifiers and by its own description. This module describes one
citation-template unit (``cited_object``: a ``CitedObject``, or ``Unavailable`` with a reason when the description
cannot be produced, D-086) and compares the description with the bibliographic fields of one Stage 02 record
(``RecordObject``): COMPATIBLE, INSUFFICIENT, NOT_ESTABLISHED or MATERIAL_CONFLICT. It is pure: no clock, no
randomness, no network, no I/O beyond reading its packaged alias profile.

Every relation is threshold-free (spec P2). Only the title can establish the object (EQUAL, or a shortened form whose
omitted words name no related object); a longer, partial or incomparable title does not (D-087, A-02). Authors can
only refute it; an author value that packs several people agrees with nothing. Invisible characters (Unicode general
category Cf and the Default_Ignorable_Code_Point property) are read as written, as a word boundary and as nothing, and
a pair must pass every reading (D-087, G-04). Year and
periodical are recorded and never decide. The independent reference model is
``simulations/stage04/bib2_reference.py``; this module imports nothing from it and it imports nothing from here.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

import mwparserfromhell
from mwparserfromhell.nodes import Comment, ExternalLink, HTMLEntity, Tag, Template, Text, Wikilink
from mwparserfromhell.wikicode import Wikicode

BIB_VERSION = "bib-2"
MAX_VALUES = 64  # spec 2.1 step 7: at most this many title and genre values, and as many author values (all forms)
MAX_TOTAL_CODE_POINTS = 4096  # spec 2.1 step 7: all values of all families together
MAX_SOURCE_CODE_POINTS = 16384  # spec 2.1 step 2: a longer unit source is not parsed (resource bound; dev max 5,722)
PROFILE_FILE = "data/bib-profile-2.json"
# Spec 2.2: the alias profile and the parser are part of the engine: a profile with other bytes or another parser
# version is refused (the engine fails closed) rather than silently changing verdicts under the same identity.
PROFILE_SHA256 = "7420622ecaf0047158f023b3ae81b93e55749998f199c57353f41d2d3d1cbece"
PARSER_VERSION = "0.7.2"

AGREE, CONFLICT, INSUFFICIENT, NOT_ESTABLISHED = "AGREE", "CONFLICT", "INSUFFICIENT", "NOT_ESTABLISHED"
SAME, DIFFERENT, NOT_IN_RECORD = "SAME", "DIFFERENT", "NOT_IN_RECORD"
EQUAL, SHORTER, LONGER, OVERLAP, DISJOINT, INCOMPARABLE, MISSING = (
    "EQUAL",
    "SHORTER",
    "LONGER",
    "OVERLAP",
    "DISJOINT",
    "INCOMPARABLE",
    "MISSING",
)
OBJ_COMPATIBLE, OBJ_INSUFFICIENT, OBJ_NOT_ESTABLISHED, MATERIAL_CONFLICT = (
    "COMPATIBLE",
    "INSUFFICIENT",
    "NOT_ESTABLISHED",
    "MATERIAL_CONFLICT",
)
# Spec 5: conflict reasons (bib-1) and the reasons of a title that does not establish the object (bib-2, D-087).
R_AUTHORS, R_TITLE_DISJOINT, R_RELATED = "BIB_AUTHORS_DISJOINT", "BIB_TITLE_DISJOINT", "BIB_TITLE_RELATED_OBJECT"
R_EXTENDED, R_PARTIAL, R_INCOMPARABLE = "BIB_TITLE_EXTENDED", "BIB_TITLE_PARTIAL", "BIB_TITLE_INCOMPARABLE"
R_SHORTENED = "BIB_TITLE_SHORTENED"
R_VALUES, R_GENRE = "BIB_TITLE_VALUES_DIFFER", "BIB_GENRE_UNMATCHED"  # spec 4.2 (M4) and 4.2a (M3)
CONFLICT_REASONS = (R_AUTHORS, R_TITLE_DISJOINT, R_RELATED)
NOT_ESTABLISHED_REASONS = (R_SHORTENED, R_EXTENDED, R_PARTIAL, R_INCOMPARABLE, R_VALUES, R_GENRE)
# Spec 2.1 (D-086): why a citation template's description could not be produced.
U_PARSE, U_SOURCE, U_VALUES, U_DESCRIPTION = (
    "BIB_PARSE_FAILED",
    "BIB_SOURCE_LIMIT_EXCEEDED",
    "BIB_VALUE_LIMIT_EXCEEDED",
    "BIB_DESCRIPTION_LIMIT_EXCEEDED",
)
UNAVAILABLE_REASONS = (U_PARSE, U_SOURCE, U_VALUES, U_DESCRIPTION)
REASONS = (*CONFLICT_REASONS, *NOT_ESTABLISHED_REASONS, *UNAVAILABLE_REASONS)

# Spec 2.1 step 6: parameter families and the CS1 keys of the profile that form them. The three author forms are kept
# apart (spec 4.1): one person per parameter, a free-form list, a Vancouver list.
FAMILIES: dict[str, tuple[str, ...]] = {
    "titles": ("Title", "ScriptTitle", "TransTitle", "Chapter", "ScriptChapter", "TransChapter"),
    "genres": ("TitleType", "TitleNote"),
    "authors": ("AuthorList-Last",),
    "author_lists": ("Authors",),
    "vauthors": ("Vauthors",),
    "periodical": ("Periodical",),
    "date": ("Date",),
    "year": ("Year",),
    "volume": ("Volume",),
    "issue": ("Issue",),
    "pages": ("Page", "Pages"),
}
AUTHOR_FAMILIES = ("authors", "author_lists", "vauthors")
COMPARED_FAMILIES = frozenset({"titles", "genres", *AUTHOR_FAMILIES})
SCRIPT_KEYS = frozenset({"ScriptTitle", "ScriptChapter"})
_SCRIPT_PREFIX = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:")
_WORD = re.compile(r"[^\W_]+")
_ETAL = re.compile(r"\bet\.?\s*al\b\.?")
_YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)")
_SPACE = re.compile(r"\s+")
_SURROGATE = re.compile("[\ud800-\udfff]")
# Spec 4.1: list separators (";" and the Arabic semicolon) and commas ("," and the Arabic comma).
_LIST_SEP = re.compile("[;؛]")
_LIST_OR_COMMA = re.compile("[;؛,،]")
_COMMA = re.compile("[,،]")

# Spec 4.2: designations of a related object (folded words and phrases); bib-1's lexicon, not extended.
_DESIGNATION_TEXT = (
    # Crossmark update types (singular and plural of each)
    "addendum addenda clarification clarifications correction corrections corrigendum corrigenda erratum errata "
    "retraction retractions withdrawal withdrawals removal removals "
    # the NLM Comment publication type, its answering forms and the related-note genres named by the owner
    "comment comments commentary commentaries reply replies response responses rejoinder rejoinders rebuttal "
    "rebuttals discussion discussions editorial editorials letter letters re "
    # Arabic translations of the same notions (indefinite and definite, singular and plural)
    "تعليق التعليق تعليقات التعليقات تعقيب التعقيب تعقيبات التعقيبات رد الرد ردود الردود تصحيح التصحيح تصحيحات "
    "التصحيحات استدراك الاستدراك سحب السحب افتتاحية الافتتاحية"
)
DESIGNATION_WORDS = frozenset(_DESIGNATION_TEXT.split())
DESIGNATION_PHRASES: tuple[tuple[str, ...], ...] = (
    ("expression", "of", "concern"),
    ("expressions", "of", "concern"),
    ("تعبير", "عن", "القلق"),
)
# Spec 3.2: name particles, which say nothing about who the person is (folded forms).
_PARTICLES_TEXT = "al el de del della der den di da du la le van von bin ibn abu ben dos das بن ابن ابو"
NAME_PARTICLES = frozenset(_PARTICLES_TEXT.split())


# Normalization (spec 3) -----------------------------------------------------------------------------------------------


def fold(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if unicodedata.category(c) not in ("Mn", "Mc", "Me")).casefold()


def words(s: str) -> list[str]:
    return _WORD.findall(fold(s))


def script(word: str) -> str | None:
    """The script of a word: the first word of the Unicode name of its first non-digit character."""
    for c in word:
        if c.isdecimal():
            continue
        name = unicodedata.name(c, "")
        return name.split(" ", 1)[0] if name else None
    return None


# Spec 3.1: the code points of the Unicode property Default_Ignorable_Code_Point (DerivedCoreProperties.txt; the
# property is stable). Together with general category Cf they are the invisible characters.
_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F),
    (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
)  # fmt: skip


def invisible(c: str) -> bool:
    """Spec 3.1: a character of general category Cf, a control character (Cc) that is not whitespace, or a character
    with the property Default_Ignorable_Code_Point."""
    cat = unicodedata.category(c)
    return cat == "Cf" or (cat == "Cc" and not c.isspace()) or any(a <= ord(c) <= b for a, b in _DEFAULT_IGNORABLE)


def has_invisible(s: str) -> bool:
    """Spec 3.1: the string holds an invisible character."""
    return any(invisible(c) for c in s)


def boundary(s: str) -> str:
    """Spec 3.1: the boundary reading of a string: every invisible character replaced by a space."""
    return "".join(" " if invisible(c) else c for c in s)


def joined(s: str) -> str:
    """Spec 3.1: the joined reading of a string: every invisible character removed."""
    return "".join(c for c in s if not invisible(c))


READINGS = {"boundary": boundary, "joined": joined}


def mixed(word: str) -> bool:
    """Spec 3.2: a word whose letters (general category L other than Lm) belong to two or more scripts; it cannot be
    read (a designation written with look-alike letters of another script would not match the lexicon)."""
    found = {script(c) for c in word if unicodedata.category(c).startswith("L") and unicodedata.category(c) != "Lm"}
    return len(found) > 1 and not any(found <= one for one in _ONE_WRITING_SYSTEM)


# Spec 3.2 (M6): the scripts one writing system mixes by design (the augmented script sets of Unicode UTS #39 5.1).
_ONE_WRITING_SYSTEM = (
    frozenset({"CJK", "HIRAGANA", "KATAKANA"}),
    frozenset({"CJK", "HANGUL"}),
    frozenset({"CJK", "BOPOMOFO"}),
)
# Spec 3.2 (M7): a Latin letter whose name ends in a single-letter group (small capitals, dotless, script, turned and
# long letters) is read as that letter when a word is looked up in the designation lexicon.
_LATIN_LOOKALIKE = re.compile(r"LATIN (?:SMALL |CAPITAL )?LETTER (?:[A-Z]+ )*([A-Z])(?: WITH [A-Z ]+)?")


def skeleton(word: str) -> str:
    """Spec 3.2 (M7): the word with every Latin look-alike letter read as its base letter (lexicon lookups only)."""
    out = []
    for c in word:
        m = _LATIN_LOOKALIKE.fullmatch(unicodedata.name(c, ""))
        out.append(m.group(1).casefold() if m else c)
    return "".join(out)


def names_designation(word: str) -> bool:
    """Spec 3.2 (M7): the word or its skeleton is in the designation lexicon."""
    return word in DESIGNATION_WORDS or skeleton(word) in DESIGNATION_WORDS


def phrase_in(ws: Sequence[str], phrase: Sequence[str]) -> bool:
    """Spec 3.2 (M7): a lexicon phrase occurs in the words or in their skeletons."""
    return _contains(ws, phrase) >= 0 or _contains([skeleton(w) for w in ws], phrase) >= 0


def name_words(value: str) -> set[str]:
    """Spec 3.2: the name words of a string (``et al`` removed; single letters, numbers and name particles are not
    names)."""
    text = _ETAL.sub(" ", fold(value))
    return {w for w in _WORD.findall(text) if len(w) >= 2 and not w.isdecimal() and w not in NAME_PARTICLES}


def _is_initials(token: str) -> bool:
    """Spec 3.2: a whitespace token that is one to three upper-case letters once its full stops and trailing commas and
    semicolons are removed ("KL", "J.J.", "S.M.,") is a set of initials, not a name."""
    t = token.replace(".", "").rstrip(",;")
    return 1 <= len(t) <= 3 and t.isalpha() and t.isupper()


def cited_name_words(value: str) -> set[str]:
    """Spec 3.2: the name words of one cited author part, initials removed first. A part made only of initials keeps
    its first token, so the rule never empties it (bib-1 reviewer finding F-01: ``|last=LI`` is the surname Li)."""
    tokens = value.split()
    kept = [t for t in tokens if not _is_initials(t)] or tokens[:1]
    return name_words(" ".join(kept))


def record_surname_words(authors: str) -> set[str]:
    """Spec 3.2: for each ``;``-separated record author, its name words without the first (the given name); a single
    name word is kept. Retraction Watch writes authors given name first ("Kam L E Hon")."""
    out: set[str] = set()
    for part in authors.split(";"):
        ws = [w for w in _WORD.findall(_ETAL.sub(" ", fold(part))) if len(w) >= 2 and not w.isdecimal()]
        ws = [w for w in ws if w not in NAME_PARTICLES]
        out.update(ws[1:] if len(ws) >= 2 else ws)
    return out


def _scripts(ws: set[str] | Sequence[str]) -> set[str]:
    return {s for w in ws if (s := script(w)) is not None}


# Inputs (spec 2) ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CitedObject:
    """The cleaned bibliographic fields of one citation-template unit (spec 2.1, DESCRIBED)."""

    titles: tuple[str, ...] = ()
    genres: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    author_lists: tuple[str, ...] = ()
    vauthors: tuple[str, ...] = ()
    periodical: str | None = None
    date: str | None = None
    year: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "titles": list(self.titles),
            "genres": list(self.genres),
            "authors": list(self.authors),
            "author_lists": list(self.author_lists),
            "vauthors": list(self.vauthors),
            "periodical": self.periodical,
            "date": self.date,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
        }

    @classmethod
    def from_json(cls, raw: Any) -> CitedObject | None:
        """The object a committed ``cited_bibliography`` value describes; None for a value that is not one."""
        if not isinstance(raw, Mapping):
            return None

        def strs(v: Any) -> tuple[str, ...]:
            return tuple(x for x in v if isinstance(x, str)) if isinstance(v, list) else ()

        def one(v: Any) -> str | None:
            return v if isinstance(v, str) else None

        return cls(
            titles=strs(raw.get("titles")),
            genres=strs(raw.get("genres")),
            authors=strs(raw.get("authors")),
            author_lists=strs(raw.get("author_lists")),
            vauthors=strs(raw.get("vauthors")),
            periodical=one(raw.get("periodical")),
            date=one(raw.get("date")),
            year=one(raw.get("year")),
            volume=one(raw.get("volume")),
            issue=one(raw.get("issue")),
            pages=one(raw.get("pages")),
        )

    def strings(self) -> tuple[str, ...]:
        """The compared cited strings (spec 3.1): every title, genre and author value."""
        return (*self.titles, *self.genres, *self.authors, *self.author_lists, *self.vauthors)

    def reading(self, mode: str) -> CitedObject:
        """Spec 3.1: the boundary or joined reading of every compared value."""
        f = READINGS[mode]
        return CitedObject(
            titles=tuple(f(v) for v in self.titles),
            genres=tuple(f(v) for v in self.genres),
            authors=tuple(f(v) for v in self.authors),
            author_lists=tuple(f(v) for v in self.author_lists),
            vauthors=tuple(f(v) for v in self.vauthors),
            periodical=self.periodical,
            date=self.date,
            year=self.year,
            volume=self.volume,
            issue=self.issue,
            pages=self.pages,
        )


@dataclass(frozen=True)
class Unavailable:
    """Spec 2.1 (D-086): a citation template whose description could not be produced, and why."""

    reason: str


@dataclass(frozen=True)
class RecordObject:
    """The bibliographic fields of one Stage 02 event (spec 2.3). Values of another type are treated as absent."""

    title: str | None = None
    authors: str | None = None
    journal: str | None = None
    original_year: int | None = None

    @classmethod
    def from_json(cls, raw: Any) -> RecordObject | None:
        if not isinstance(raw, Mapping):
            return None
        year = raw.get("original_year")
        return cls(
            title=raw.get("title") if isinstance(raw.get("title"), str) else None,
            authors=raw.get("authors") if isinstance(raw.get("authors"), str) else None,
            journal=raw.get("journal") if isinstance(raw.get("journal"), str) else None,
            original_year=year if isinstance(year, int) and not isinstance(year, bool) else None,
        )

    def strings(self) -> tuple[str, ...]:
        return tuple(v for v in (self.title, self.authors) if v is not None)

    def reading(self, mode: str) -> RecordObject:
        f = READINGS[mode]
        return RecordObject(
            title=f(self.title) if self.title is not None else None,
            authors=f(self.authors) if self.authors is not None else None,
            journal=self.journal,
            original_year=self.original_year,
        )


class EnvironmentNotPinned(RuntimeError):
    """The alias profile, the parser or the wiki is not one this engine pins (spec 2.1, 2.2): the engine refuses."""


@cache
def profile() -> dict[str, Any]:
    raw = resources.files("citerift.investigation").joinpath(PROFILE_FILE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise EnvironmentNotPinned("the bib alias profile is not the pinned one")
    if mwparserfromhell.__version__ != PARSER_VERSION:
        raise EnvironmentNotPinned(
            f"mwparserfromhell {mwparserfromhell.__version__} is not the pinned {PARSER_VERSION}"
        )
    data: dict[str, Any] = json.loads(raw.decode("utf-8"))
    return data


@cache
def _matchers(wiki: str) -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    """(family, CS1 key, compiled alias pattern) for one wiki, in family order then profile order."""
    aliases = profile()["wikis"][wiki]["aliases"]
    out = []
    for family, keys in FAMILIES.items():
        for key in keys:
            for alias in aliases[key]:
                pattern = "".join("(?:[1-9][0-9]*)?" if ch == "#" else re.escape(ch) for ch in alias)
                out.append((family, key, re.compile(pattern)))
    return tuple(out)


def _family_of(wiki: str, name: str) -> tuple[str, str] | None:
    for family, key, pattern in _matchers(wiki):
        if pattern.fullmatch(name):
            return family, key
    return None


_INLINE = (Text, HTMLEntity, Wikilink, ExternalLink)
# Spec 2.1 step 5: inline formatting renders joined to its neighbours ("CO<sub>2</sub>", italic or bold wiki markup
# inside a word), so these tags (the wiki markup parses as tags i and b) join as written.
INLINE_TAGS = frozenset({"i", "b", "sub", "sup", "span", "small", "big", "u", "s", "em", "strong"})


def _joined(node: Any) -> bool:
    return isinstance(node, _INLINE) or (isinstance(node, Tag) and str(node.tag).strip().lower() in INLINE_TAGS)


# Spec 2.1 step 5 (M1): a comment, and each side of a nowiki tag's text, render nothing yet may sit inside a word
# (``Err<!-- -->atum``); written as an invisible character, section 3.1 reads them both as a boundary and as nothing.
_RENDERS_NOTHING = "\u200b"


def _clean(value: Any) -> str | None:
    """Spec 2.1 step 5: node by node, a removed or replaced node (template, other tag, comment, argument, heading) is a
    word boundary; text, entities, links and inline formatting tags join their neighbours as written. A lone surrogate
    (from a numeric entity such as ``&#xD800;``) becomes U+FFFD, which is no word character, so the value stays Unicode
    text and keeps its words."""
    parts = []
    for node in value.nodes:
        text = Wikicode([node]).strip_code(normalize=True, collapse=True)
        if isinstance(node, Comment):
            parts.append(_RENDERS_NOTHING)
        elif isinstance(node, Tag) and str(node.tag).strip().lower() == "nowiki":
            parts.append(f"{_RENDERS_NOTHING}{text}{_RENDERS_NOTHING}")
        else:
            parts.append(text if _joined(node) else f" {text} ")
    cleaned = _SURROGATE.sub("�", _SPACE.sub(" ", "".join(parts)).strip())
    return cleaned if joined(cleaned).strip() else None


def describe(data: bytes | None, wiki: str) -> CitedObject | Unavailable:
    """Spec 2.1 steps 1 to 8 for the committed source bytes of one ``citation_template`` unit (None: the span could not
    be read): its description, or why there is none (D-086). An unknown wiki makes the engine refuse."""
    if data is None:
        return Unavailable(U_PARSE)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return Unavailable(U_PARSE)
    return cited_object(text, wiki)


def cited_object(text: str, wiki: str) -> CitedObject | Unavailable:
    """Spec 2.1 steps 2 to 8 for the decoded source of one citation-template unit. The pinned parser's C tokenizer
    must be active (spec 2.2; the pure-Python tokenizer can parse differently, and Stage 03 switches it in its worker
    processes) and the wiki must be one of the profile's: otherwise the engine refuses."""
    if not mwparserfromhell.parser.use_c:
        raise EnvironmentNotPinned("the C tokenizer of mwparserfromhell is not active")
    if wiki not in profile()["wikis"]:
        raise EnvironmentNotPinned(f"the bib alias profile has no wiki {wiki!r}")
    if len(text) > MAX_SOURCE_CODE_POINTS:
        return Unavailable(U_SOURCE)
    try:
        fields = _parsed(text, wiki)
    except Exception:
        return Unavailable(U_PARSE)
    if fields is None:
        return Unavailable(U_PARSE)
    # Spec 2.1 step 7: above the bounds of the committed value there is no description (never truncated).
    titles = len(fields["titles"]) + len(fields["genres"])
    if titles > MAX_VALUES or sum(len(fields[f]) for f in AUTHOR_FAMILIES) > MAX_VALUES:
        return Unavailable(U_VALUES)
    if sum(len(v) for vs in fields.values() for v in vs) > MAX_TOTAL_CODE_POINTS:
        return Unavailable(U_DESCRIPTION)

    def first(family: str) -> str | None:
        return fields[family][0] if fields[family] else None

    return CitedObject(
        titles=tuple(fields["titles"]),
        genres=tuple(fields["genres"]),
        authors=tuple(fields["authors"]),
        author_lists=tuple(fields["author_lists"]),
        vauthors=tuple(fields["vauthors"]),
        periodical=first("periodical"),
        date=first("date"),
        year=first("year"),
        volume=first("volume"),
        issue=first("issue"),
        pages=first("pages"),
    )


_IGNORED = ""  # spec 2.1 step 4: a parameter that is ignored (a commented name that names no family)


def _name(param: Any, wiki: str) -> str | None:
    """Spec 2.1 step 4: the parameter's name, stripped; ``_IGNORED`` for a name holding comments that, once they are
    removed, names no family (MediaWiki reads such a parameter under a name no family uses, and bib-1 read it under one
    no alias matches: either way it is not read); None when the name holds any other markup (a template, a link: it
    cannot be read without expanding it) or comments around a name of a family (MediaWiki reads it under that name,
    bib-1 did not; reading it could replace a value bib-1 compared, against B4)."""
    nodes = param.name.nodes
    if all(isinstance(n, Text) for n in nodes):
        return str(param.name).strip()
    if not all(isinstance(n, (Text, Comment)) for n in nodes):
        return None
    bare = "".join(str(n) for n in nodes if isinstance(n, Text)).strip()
    return None if _family_of(wiki, bare) is not None else _IGNORED


# Spec 2.1 step 5: tags whose content cleaning keeps as the text it renders (inline formatting, nowiki) or that render
# no text (a line break). Any other tag in a compared value may hide what it renders (``<math>``, ``<score>``).
READABLE_TAGS = frozenset({*INLINE_TAGS, "nowiki", "br"})


def _hides_content(raw: Any) -> bool:
    """Spec 2.1 step 5: the value holds, at any depth, a template or parser function (``{{lang|en|Comments on}}``,
    ``{{lc:Comments on}}``, ``{{PAGENAME}}``: what it renders cannot be known without expanding it), a template
    parameter (``{{{x}}}``) or a tag other than the readable ones."""
    if raw.filter_templates(recursive=True) or raw.filter_arguments(recursive=True):
        return True
    return any(str(t.tag).strip().lower() not in READABLE_TAGS for t in raw.filter_tags(recursive=True))


def _parsed(text: str, wiki: str) -> dict[str, list[str]] | None:
    """Spec 2.1 steps 3 to 6: the family values, or None when the source is not exactly one template, a named
    parameter's name cannot be read, or a compared value hides content."""
    code = mwparserfromhell.parse(text)
    nodes = [n for n in code.nodes if not (isinstance(n, Text) and not str(n).strip())]
    if len(nodes) != 1 or not isinstance(nodes[0], Template):
        return None
    effective: dict[str, Any] = {}
    for param in nodes[0].params:
        if not param.showkey:
            continue
        name = _name(param, wiki)
        if name is None:
            return None
        if name == _IGNORED:
            continue
        # A later duplicate replaces the earlier value; the name keeps the position of its first occurrence.
        effective[name] = param.value
    fields: dict[str, list[str]] = {f: [] for f in FAMILIES}
    for name, raw in effective.items():
        found = _family_of(wiki, name)
        if found is None:
            continue
        family, key = found
        if family in COMPARED_FAMILIES and _hides_content(raw):
            return None
        value = _clean(raw)
        if value is not None and key in SCRIPT_KEYS:
            value = _SCRIPT_PREFIX.sub("", value, count=1).strip() or None
        if value is not None:
            fields[family].append(value)
    return fields


# Field verdicts (spec 4) ---------------------------------------------------------------------------------------------


# Spec 4.1: a conjunction is "&" or a whitespace token that casefolds to "and" or is the Arabic "\u0648".
_CONJUNCTION_TOKENS = frozenset({"and", "\u0648"})


def _conjunction(piece: str) -> bool:
    return "&" in piece or any(t.casefold() in _CONJUNCTION_TOKENS for t in piece.split())


def author_parts(cited: CitedObject) -> list[tuple[str, bool]]:
    """Spec 4.1: the cited author parts, each ``(text, packed)``: a Vancouver list splits into persons at list
    separators and commas; a one-person parameter or a free-form list splits at list separators, and a piece that may
    still hold several names (a conjunction or a comma: "Smith, John" and "Smith J, Jones K" cannot be told apart) is
    packed."""
    out: list[tuple[str, bool]] = []
    for value in cited.vauthors:
        out += [(p.strip(), False) for p in _LIST_OR_COMMA.split(value) if p.strip()]
    for value in (*cited.authors, *cited.author_lists):
        for p in (p.strip() for p in _LIST_SEP.split(value)):
            if p:
                out.append((p, _conjunction(p) or bool(_COMMA.search(p))))
    return out


def authors_verdict(cited: CitedObject, record: str | None) -> str:
    """Spec 4.1: CONFLICT if a comparable part names no record author (a packed part: none of its names), or if a
    comparable whole author value does (bib-1's test, kept so that splitting a value never hides a conflict, B4);
    AGREE if a comparable person part names one and none conflicts; INSUFFICIENT otherwise. A packed part never
    agrees."""
    s_r = record_surname_words(record) if record else set()
    scripts_r = _scripts(s_r)

    def comparable(ws: set[str]) -> bool:
        # A word that mixes scripts cannot be read and is compared (spec 4.1), so a look-alike name still conflicts.
        return bool(s_r) and (bool(_scripts(ws) & scripts_r) or any(mixed(w) for w in ws))

    for value in (*cited.authors, *cited.author_lists, *cited.vauthors):
        ws = cited_name_words(value)
        if comparable(ws) and not ws & s_r:
            return CONFLICT
    agree = False
    for text, packed in author_parts(cited):
        ws = cited_name_words(text)
        if not comparable(ws):
            continue  # not comparable
        if not ws & s_r:
            return CONFLICT
        agree = agree or not packed
    return AGREE if agree else INSUFFICIENT


def _contains(outer: Sequence[str], inner: Sequence[str]) -> int:
    """The first index of ``inner`` as consecutive words of ``outer``, or -1."""
    n = len(inner)
    if n == 0 or n > len(outer):
        return -1
    for i in range(len(outer) - n + 1):
        if list(outer[i : i + n]) == list(inner):
            return i
    return -1


def relation(t: Sequence[str], r: Sequence[str]) -> str:
    """Spec 4.2: the relation of a cited title's words to the record title's words (both non-empty)."""
    if list(t) == list(r):
        return EQUAL
    if _contains(r, t) >= 0:
        return SHORTER
    if _contains(t, r) >= 0:
        return LONGER
    if set(t) & set(r):
        return OVERLAP
    if _scripts(t) & _scripts(r):
        return DISJOINT
    return INCOMPARABLE


_RANK = {EQUAL: 0, SHORTER: 1, LONGER: 2, OVERLAP: 3, DISJOINT: 4, INCOMPARABLE: 5}


def _outside(outer: Sequence[str], inner: Sequence[str]) -> list[str]:
    at = _contains(outer, inner)
    return list(outer[:at]) + list(outer[at + len(inner) :]) if at >= 0 else list(outer)


def designates(t: Sequence[str], r: Sequence[str], rel: str) -> bool:
    """Spec 4.2: one side names an object related to the other's (a word of the designation lexicon among the words
    that side has beyond the other, or a lexicon phrase that only one side holds)."""
    if rel == SHORTER:
        cited_extra, record_extra = [], _outside(r, t)
    elif rel == LONGER:
        cited_extra, record_extra = _outside(t, r), []
    elif rel in (OVERLAP, DISJOINT, INCOMPARABLE):
        cited_extra, record_extra = [w for w in t if w not in set(r)], [w for w in r if w not in set(t)]
    else:
        return False
    extra = [*cited_extra, *record_extra]
    if any(names_designation(w) or mixed(w) for w in extra):
        return True
    return any(phrase_in(t, p) != phrase_in(r, p) for p in DESIGNATION_PHRASES)


def genre_designates(genres: Sequence[str], record: str | None) -> bool:
    """Spec 4.2a: a genre value (CS1 ``type``, ``medium``, ``department``, ``title-note``) names a related object when
    it holds a lexicon word or phrase, or a word that mixes scripts, that the record's title does not hold."""
    r = words(record) if record else []
    for value in genres:
        g = words(value)
        if any((names_designation(w) or mixed(w)) and w not in r for w in g):
            return True
        if any(phrase_in(g, p) and not phrase_in(r, p) for p in DESIGNATION_PHRASES):
            return True
    return False


def genre_unmatched(genres: Sequence[str], record: str | None) -> bool:
    """Spec 4.2a (M3): some genre value has a word the record's title does not hold (the lexicon is not extended, so a
    genre it does not know cannot be told from a harmless one)."""
    r = set(words(record)) if record else set()
    return any(w not in r for value in genres for w in words(value))


@dataclass(frozen=True)
class TitleResult:
    verdict: str
    relation: str
    designation: bool
    values_differ: bool = False  # spec 4.2 (M4): some value agrees and another does not


_NOT_ESTABLISHED_BY = {SHORTER: R_SHORTENED, LONGER: R_EXTENDED, OVERLAP: R_PARTIAL, INCOMPARABLE: R_INCOMPARABLE}


def title_verdict(cited: Sequence[str], record: str | None) -> TitleResult:
    """Spec 4.2: the best relation over the values; designation over every value that is not EQUAL (one designating
    value suffices, fail closed)."""
    r = words(record) if record else []
    best: str | None = None
    designation = False
    agreeing = differing = 0
    for value in cited:
        t = words(value)
        if not t or not r:
            continue
        rel = relation(t, r)
        designation = designation or designates(t, r, rel)
        if rel == EQUAL:  # spec 4.2 (M8): only an equal title agrees
            agreeing += 1
        else:
            differing += 1
        if best is None or _RANK[rel] < _RANK[best]:
            best = rel
    if best is None:
        return TitleResult(INSUFFICIENT, MISSING, False)
    if designation or best == DISJOINT:
        return TitleResult(CONFLICT, best, designation)
    if agreeing and not differing:
        return TitleResult(AGREE, best, False)
    return TitleResult(NOT_ESTABLISHED, best, False, values_differ=bool(agreeing))


def year_verdict(date: str | None, year: str | None, record_year: int | None) -> str:
    found = None
    for text in (date, year):
        if text:
            m = _YEAR.search(text)
            if m:
                found = int(m.group(1))
                break
    if found is None or record_year is None:
        return INSUFFICIENT
    return SAME if found == record_year else DIFFERENT


def periodical_verdict(cited: str | None, journal: str | None) -> str:
    c, j = words(cited) if cited else [], words(journal) if journal else []
    if not c or not j:
        return INSUFFICIENT
    return SAME if c == j else DIFFERENT


# Object verdict (spec 5) ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Comparison:
    authors: str
    title: str
    title_relation: str
    designation: bool
    year: str
    periodical: str
    object: str
    reasons: tuple[str, ...]
    readings: int = 1  # spec 3.1: 3 when a compared string held an invisible character

    def to_json(self) -> dict[str, Any]:
        return {
            "version": BIB_VERSION,
            "authors": self.authors,
            "title": self.title,
            "title_relation": self.title_relation,
            "designation": self.designation,
            "year": self.year,
            "periodical": self.periodical,
            "volume": NOT_IN_RECORD,
            "issue": NOT_IN_RECORD,
            "pages": NOT_IN_RECORD,
            "object": self.object,
            "reasons": list(self.reasons),
            "readings": self.readings,
        }


NO_COMPARISON = Comparison(INSUFFICIENT, INSUFFICIENT, MISSING, False, INSUFFICIENT, INSUFFICIENT, OBJ_INSUFFICIENT, ())
# Spec 3.1: the order in which the worse of two readings is taken.
_SEVERITY = {MATERIAL_CONFLICT: 3, OBJ_NOT_ESTABLISHED: 2, OBJ_INSUFFICIENT: 1, OBJ_COMPATIBLE: 0}


def _compare_one(cited: CitedObject, record: RecordObject) -> Comparison:
    """Spec 4 and 5 under one reading."""
    a = authors_verdict(cited, record.authors)
    t = title_verdict(cited.titles, record.title)
    designation = t.designation or genre_designates(cited.genres, record.title)
    reasons = []
    if a == CONFLICT:
        reasons.append(R_AUTHORS)
    if t.verdict == CONFLICT and t.relation == DISJOINT:
        reasons.append(R_TITLE_DISJOINT)
    if designation:
        reasons.append(R_RELATED)
    conflict = bool(
        reasons
    )  # spec 5: authors CONFLICT, title CONFLICT (designation or DISJOINT) or a genre designation
    if not conflict:
        if t.verdict == NOT_ESTABLISHED:
            reasons.append(R_VALUES if t.values_differ else _NOT_ESTABLISHED_BY[t.relation])
        if genre_unmatched(cited.genres, record.title):
            reasons.append(R_GENRE)
    if conflict:
        obj = MATERIAL_CONFLICT
    elif reasons:
        obj = OBJ_NOT_ESTABLISHED
    elif t.verdict == AGREE:
        obj = OBJ_COMPATIBLE
    else:
        obj = OBJ_INSUFFICIENT
    return Comparison(
        authors=a,
        title=t.verdict,
        title_relation=t.relation,
        designation=designation,
        year=year_verdict(cited.date, cited.year, record.original_year),
        periodical=periodical_verdict(cited.periodical, record.journal),
        object=obj,
        reasons=tuple(sorted(reasons)),
    )


def compare(cited: CitedObject | None, record: RecordObject | None) -> Comparison:
    """The bib-2 verdict of one (described unit, record) pair: the worst of the three readings (as written, boundary,
    joined) when a compared string holds an invisible character (spec 3.1), the single reading otherwise."""
    if cited is None or record is None:
        return NO_COMPARISON
    written = _compare_one(cited, record)
    if not any(has_invisible(s) for s in (*cited.strings(), *record.strings())):
        return written
    results = [written, *(_compare_one(cited.reading(m), record.reading(m)) for m in READINGS)]
    worst = max(_SEVERITY[c.object] for c in results)
    chosen = next(c for c in results if _SEVERITY[c.object] == worst)
    reasons = sorted({r for c in results if _SEVERITY[c.object] == worst for r in c.reasons})
    return Comparison(
        authors=chosen.authors,
        title=chosen.title,
        title_relation=chosen.title_relation,
        designation=chosen.designation,
        year=chosen.year,
        periodical=chosen.periodical,
        object=chosen.object,
        reasons=tuple(reasons),
        readings=len(results),
    )
