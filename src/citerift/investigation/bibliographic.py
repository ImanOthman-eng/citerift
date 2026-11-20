"""bib-1: the bibliographic-object consistency layer (owner decision D-083; normative text
docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC.md).

A citation names a publication object twice: by its identifiers and by its own description. This module compares the
description of one citation-template unit (``CitedObject``, parsed from the unit's committed source span) with the
bibliographic fields of one Stage 02 record (``RecordObject``) and classifies the pair as COMPATIBLE, INSUFFICIENT or
MATERIAL_CONFLICT. It is pure: no clock, no randomness, no network, no I/O beyond reading its packaged alias profile.

Every relation is threshold-free (spec P2): equality, contiguous containment, a shared word, or no shared word. Only
authors and title are decisive; year and periodical are recorded and never decide (spec 4.3). A field that cannot be
compared is INSUFFICIENT and never blocks anything. The independent reference model is
``simulations/stage04/bib_reference.py``; this module imports nothing from it and it imports nothing from here.
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
from mwparserfromhell.nodes import ExternalLink, HTMLEntity, Tag, Template, Text, Wikilink
from mwparserfromhell.wikicode import Wikicode

BIB_VERSION = "bib-1"
MAX_VALUES = 64  # spec 2.1 step 6: at most this many titles and at most this many authors
MAX_TOTAL_CODE_POINTS = 4096  # spec 2.1 step 6: all values of all families together
MAX_SOURCE_CODE_POINTS = 16384  # spec 2.1 step 1: a longer unit source is not parsed (resource bound; dev max 5,722)
PROFILE_FILE = "data/bib-profile-1.json"
# Spec 2.2: the alias profile and the parser are part of the engine: a profile with other bytes or another parser
# version is refused (the engine fails closed) rather than silently changing verdicts under the same identity.
PROFILE_SHA256 = "450f17a2ec492f9066825e0ec9de3f2f480398345d4593759bfb9ace45e9808f"
PARSER_VERSION = "0.7.2"

AGREE, COMPATIBLE, CONFLICT, INSUFFICIENT = "AGREE", "COMPATIBLE", "CONFLICT", "INSUFFICIENT"
SAME, DIFFERENT, NOT_IN_RECORD = "SAME", "DIFFERENT", "NOT_IN_RECORD"
EQUAL, CONTAINED, OVERLAP, DISJOINT, INCOMPARABLE, MISSING = (
    "EQUAL",
    "CONTAINED",
    "OVERLAP",
    "DISJOINT",
    "INCOMPARABLE",
    "MISSING",
)
OBJ_COMPATIBLE, OBJ_INSUFFICIENT, MATERIAL_CONFLICT = "COMPATIBLE", "INSUFFICIENT", "MATERIAL_CONFLICT"
R_AUTHORS, R_TITLE_DISJOINT, R_RELATED = "BIB_AUTHORS_DISJOINT", "BIB_TITLE_DISJOINT", "BIB_TITLE_RELATED_OBJECT"
REASONS = (R_AUTHORS, R_TITLE_DISJOINT, R_RELATED)

# Spec 2.1 step 5: parameter families and the CS1 keys of the profile that form them.
FAMILIES: dict[str, tuple[str, ...]] = {
    "titles": ("Title", "ScriptTitle", "TransTitle", "Chapter", "ScriptChapter", "TransChapter"),
    "authors": ("AuthorList-Last", "Authors", "Vauthors"),
    "periodical": ("Periodical",),
    "date": ("Date",),
    "year": ("Year",),
    "volume": ("Volume",),
    "issue": ("Issue",),
    "pages": ("Page", "Pages"),
}
SCRIPT_KEYS = frozenset({"ScriptTitle", "ScriptChapter"})
_SCRIPT_PREFIX = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]+)?:")
_WORD = re.compile(r"[^\W_]+")
_ETAL = re.compile(r"\bet\.?\s*al\b\.?")
_YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)")
_SPACE = re.compile(r"\s+")

# Spec 4.2: designations of a related object (folded words and phrases), counted only outside the record's title.
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
# Spec 4.1: name particles, which say nothing about who the person is (folded forms).
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


def name_words(value: str) -> set[str]:
    """Spec 3: the name words of one author value (``et al`` removed; single letters, numbers and name particles are
    not names)."""
    text = _ETAL.sub(" ", fold(value))
    return {w for w in _WORD.findall(text) if len(w) >= 2 and not w.isdecimal() and w not in NAME_PARTICLES}


def _is_initials(token: str) -> bool:
    """Spec 4.1: a whitespace token of a cited author value that is one to three upper-case letters once its full stops
    and trailing commas and semicolons are removed ("KL", "J.J.", "S.M.,") is a set of initials, not a name."""
    t = token.replace(".", "").rstrip(",;")
    return 1 <= len(t) <= 3 and t.isalpha() and t.isupper()


def cited_name_words(value: str) -> set[str]:
    """Spec 4.1: the name words of one cited author value, initials removed first. A value made only of initials keeps
    its first token, so the rule never empties a value (reviewer finding F-01: ``|last=LI`` is the surname Li)."""
    tokens = value.split()
    kept = [t for t in tokens if not _is_initials(t)] or tokens[:1]
    return name_words(" ".join(kept))


def record_surname_words(authors: str) -> set[str]:
    """Spec 4.1: for each ``;``-separated record author, its name words without the first (the given name); a single
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
    """The cleaned bibliographic fields of one citation-template unit (spec 2.1)."""

    titles: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    periodical: str | None = None
    date: str | None = None
    year: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "titles": list(self.titles),
            "authors": list(self.authors),
            "periodical": self.periodical,
            "date": self.date,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
        }

    @classmethod
    def from_json(cls, raw: Any) -> CitedObject | None:
        """The object a committed ``cited_bibliography`` value describes; None for a value that is not one (fail
        closed to INSUFFICIENT, spec B8)."""
        if not isinstance(raw, Mapping):
            return None

        def strs(v: Any) -> tuple[str, ...]:
            return tuple(x for x in v if isinstance(x, str)) if isinstance(v, list) else ()

        def one(v: Any) -> str | None:
            return v if isinstance(v, str) else None

        return cls(
            titles=strs(raw.get("titles")),
            authors=strs(raw.get("authors")),
            periodical=one(raw.get("periodical")),
            date=one(raw.get("date")),
            year=one(raw.get("year")),
            volume=one(raw.get("volume")),
            issue=one(raw.get("issue")),
            pages=one(raw.get("pages")),
        )


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


class EnvironmentNotPinned(RuntimeError):
    """The alias profile or the parser is not the one this engine pins (spec 2.2): the engine refuses to run."""


@cache
def profile() -> dict[str, Any]:
    raw = resources.files("citerift.investigation").joinpath(PROFILE_FILE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise EnvironmentNotPinned("the bib-1 alias profile is not the pinned one")
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
# Spec 2.1 step 4 (reviewer finding F-04): inline formatting renders joined to its neighbours ("CO<sub>2</sub>",
# italic or bold wiki markup inside a word), so these tags (the wiki markup parses as tags i and b) join as written.
INLINE_TAGS = frozenset({"i", "b", "sub", "sup", "span", "small", "big", "u", "s", "em", "strong"})


def _joined(node: Any) -> bool:
    return isinstance(node, _INLINE) or (isinstance(node, Tag) and str(node.tag).strip().lower() in INLINE_TAGS)


def _clean(value: Any) -> str | None:
    """Spec 2.1 step 4: node by node, a removed or replaced node (template, other tag, comment, argument, heading) is a
    word boundary; text, entities, links and inline formatting tags join their neighbours as written."""
    parts = []
    for node in value.nodes:
        text = Wikicode([node]).strip_code(normalize=True, collapse=True)
        parts.append(text if _joined(node) else f" {text} ")
    cleaned = _SPACE.sub(" ", "".join(parts)).strip()
    return cleaned or None


def _encodable(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:  # a lone surrogate, for example from the entity &#xD800;
        return False
    return True


def cited_object(text: str, wiki: str) -> CitedObject | None:
    """Spec 2.1 steps 2 to 5 for the decoded source of one citation-template unit; None for no cited object. The
    pinned parser's C tokenizer must be active (spec 2.2; the pure-Python tokenizer can parse differently, and Stage 03
    switches it in its worker processes): otherwise the engine refuses (reviewer finding E-11)."""
    if not mwparserfromhell.parser.use_c:
        raise EnvironmentNotPinned("the C tokenizer of mwparserfromhell is not active")
    if wiki not in profile()["wikis"] or len(text) > MAX_SOURCE_CODE_POINTS:
        return None
    try:
        return _parsed(text, wiki)
    except Exception:
        return None


def _parsed(text: str, wiki: str) -> CitedObject | None:
    code = mwparserfromhell.parse(text)
    nodes = [n for n in code.nodes if not (isinstance(n, Text) and not str(n).strip())]
    if len(nodes) != 1 or not isinstance(nodes[0], Template):
        return None
    effective: dict[str, Any] = {}
    for param in nodes[0].params:
        if not param.showkey:
            continue
        # A later duplicate replaces the earlier value; the name keeps the position of its first occurrence.
        effective[str(param.name).strip()] = param.value
    fields: dict[str, list[str]] = {f: [] for f in FAMILIES}
    for name, raw in effective.items():
        found = _family_of(wiki, name)
        if found is None:
            continue
        family, key = found
        value = _clean(raw)
        if value is not None and key in SCRIPT_KEYS:
            value = _SCRIPT_PREFIX.sub("", value, count=1).strip() or None
        # Spec 2.1 step 4: a value that is not Unicode text (a lone surrogate) is absent; the rest of the description
        # stays (reviewer finding F-02).
        if value is not None and _encodable(value):
            fields[family].append(value)

    # Spec 2.1 step 6: above the bounds of the committed value there is no cited object (never truncated).
    if any(len(fields[f]) > MAX_VALUES for f in ("titles", "authors")) or (
        sum(len(v) for vs in fields.values() for v in vs) > MAX_TOTAL_CODE_POINTS
    ):
        return None

    def first(family: str) -> str | None:
        return fields[family][0] if fields[family] else None

    return CitedObject(
        titles=tuple(fields["titles"]),
        authors=tuple(fields["authors"]),
        periodical=first("periodical"),
        date=first("date"),
        year=first("year"),
        volume=first("volume"),
        issue=first("issue"),
        pages=first("pages"),
    )


# Field verdicts (spec 4) ---------------------------------------------------------------------------------------------


def authors_verdict(cited: Sequence[str], record: str | None) -> str:
    """Spec 4.1: every comparable cited author value must name a record author by a surname word."""
    s_r = record_surname_words(record) if record else set()
    scripts_r = _scripts(s_r)
    comparable = [ws for ws in (cited_name_words(v) for v in cited) if _scripts(ws) & scripts_r]
    if not comparable:
        return INSUFFICIENT
    return AGREE if all(ws & s_r for ws in comparable) else CONFLICT


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
    if _contains(t, r) >= 0 or _contains(r, t) >= 0:
        return CONTAINED
    if set(t) & set(r):
        return OVERLAP
    if _scripts(t) & _scripts(r):
        return DISJOINT
    return INCOMPARABLE


_RANK = {EQUAL: 0, CONTAINED: 1, OVERLAP: 2, DISJOINT: 3, INCOMPARABLE: 4}


def designates(t: Sequence[str], r: Sequence[str], rel: str) -> bool:
    """Spec 4.2: the cited title names an object related to the record's work (a word or phrase of the designation
    lexicon outside the record's own title)."""
    if rel == CONTAINED:
        at = _contains(t, r)
        extra = list(t[:at]) + list(t[at + len(r) :]) if at >= 0 else []
    elif rel == OVERLAP:
        extra = [w for w in t if w not in set(r)]
    else:
        return False
    if DESIGNATION_WORDS.intersection(extra):
        return True
    return any(_contains(t, p) >= 0 and _contains(r, p) < 0 for p in DESIGNATION_PHRASES)


@dataclass(frozen=True)
class TitleResult:
    verdict: str
    relation: str
    designation: bool


def title_verdict(cited: Sequence[str], record: str | None) -> TitleResult:
    """Spec 4.2: the best relation over the values; designation over every CONTAINED or OVERLAP value (one designating
    value suffices, fail closed)."""
    r = words(record) if record else []
    best: str | None = None
    designation = False
    for value in cited:
        t = words(value)
        if not t or not r:
            continue
        rel = relation(t, r)
        designation = designation or designates(t, r, rel)
        if best is None or _RANK[rel] < _RANK[best]:
            best = rel
    if best is None:
        return TitleResult(INSUFFICIENT, MISSING, False)
    if designation:
        return TitleResult(CONFLICT, best, True)
    if best == EQUAL:
        return TitleResult(AGREE, best, False)
    if best in (CONTAINED, OVERLAP):
        return TitleResult(COMPATIBLE, best, False)
    if best == DISJOINT:
        return TitleResult(CONFLICT, best, False)
    return TitleResult(INSUFFICIENT, best, False)


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
        }


NO_COMPARISON = Comparison(INSUFFICIENT, INSUFFICIENT, MISSING, False, INSUFFICIENT, INSUFFICIENT, OBJ_INSUFFICIENT, ())


def compare(cited: CitedObject | None, record: RecordObject | None) -> Comparison:
    """The bib-1 verdict of one (cited object, record) pair."""
    if cited is None or record is None:
        return NO_COMPARISON
    a = authors_verdict(cited.authors, record.authors)
    t = title_verdict(cited.titles, record.title)
    reasons = []
    if a == CONFLICT:
        reasons.append(R_AUTHORS)
    if t.relation == DISJOINT:
        reasons.append(R_TITLE_DISJOINT)
    if t.designation:
        reasons.append(R_RELATED)
    if reasons:
        obj = MATERIAL_CONFLICT
    elif a == AGREE or t.verdict in (AGREE, COMPATIBLE):
        obj = OBJ_COMPATIBLE
    else:
        obj = OBJ_INSUFFICIENT
    return Comparison(
        authors=a,
        title=t.verdict,
        title_relation=t.relation,
        designation=t.designation,
        year=year_verdict(cited.date, cited.year, record.original_year),
        periodical=periodical_verdict(cited.periodical, record.journal),
        object=obj,
        reasons=tuple(sorted(reasons)),
    )
