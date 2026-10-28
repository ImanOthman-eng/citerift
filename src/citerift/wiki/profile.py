"""The versioned bilingual support profile: which templates, parameters and tags the extractor recognizes.

The map is data (src/citerift/wiki/data/profile-v1.json), built from inspected Wikipedia evidence with its
provenance (docs/verification/stage-03/calibration/). A name that is not in the map is never guessed: a template
with identifier parameters that the map does not list is reported as unsupported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from citerift.wiki.canonical import digest, loads_strict

SUPPORTED_WIKIS = ("ar", "en")
_SPACES = re.compile(r"[ _\t\n\r ]+")


@dataclass(frozen=True)
class GeneratedRef:
    """A template that generates a reference (``refn``, ``efn``, ``sfn``) or reference uses (``r``)."""

    kind: str
    body_params: tuple[str, ...]
    name_params: tuple[str, ...]
    group_params: tuple[str, ...]
    default_group: str


@dataclass(frozen=True)
class ReflistSpec:
    """A reference-list template: its list-defined refs parameters and its group."""

    refs_params: frozenset[str]
    group_params: tuple[str, ...]
    default_group: str


TAG_REF = GeneratedRef("tag_ref", ("1",), ("name",), ("group",), "")


@dataclass(frozen=True)
class WikiProfile:
    wiki: str
    namespace_prefixes: tuple[str, ...]
    citation_templates: dict[str, str]
    external_data_templates: frozenset[str]
    identifier_params: dict[str, str]
    url_params: frozenset[str]
    wrappers: dict[str, str]
    markers: frozenset[str]
    marker_render_titles: frozenset[str]
    generated_refs: dict[str, GeneratedRef]
    reflists: dict[str, ReflistSpec]
    redirect_words: tuple[str, ...]
    doi_text_labels: tuple[str, ...]
    warning_terms: tuple[str, ...]
    ambiguous_terms: tuple[str, ...]

    def canonical_template(self, raw_name: str) -> str | None:
        """MediaWiki title rules for a template name: trimmed, underscores and runs of spaces as one space,
        an optional Template namespace prefix removed, first letter upper case (no case in Arabic).
        Returns None for parser functions and magic words (names with '#' or ':' after the prefix)."""
        name = _SPACES.sub(" ", raw_name).strip()
        if not name or name.startswith("#"):
            return None
        for prefix in self.namespace_prefixes:
            if name[: len(prefix)].casefold() == prefix.casefold():
                name = name[len(prefix) :].strip()
                break
        if not name or ":" in name:
            return None
        return name[0].upper() + name[1:]


@dataclass(frozen=True)
class Profile:
    version: str
    digest: str
    wikis: dict[str, WikiProfile]
    excluded_tags: frozenset[str]
    unsupported_tags: frozenset[str]
    raw: dict[str, Any]


def _wiki(wiki: str, d: dict[str, Any]) -> WikiProfile:
    def canon(names: list[str]) -> list[str]:
        return [n[0].upper() + n[1:] for n in names]

    generated = {}
    for g in d["generated_refs"]:
        spec = GeneratedRef(
            g["kind"], tuple(g["body_params"]), tuple(g["name_params"]), tuple(g["group_params"]), g["default_group"]
        )
        for name in canon(g["names"]):
            generated[name] = spec
    reflists = {}
    for r in d["reflists"]:
        spec_r = ReflistSpec(frozenset(r["refs_params"]), tuple(r["group_params"]), r["default_group"])
        for name in canon(r["names"]):
            reflists[name] = spec_r
    return WikiProfile(
        wiki=wiki,
        namespace_prefixes=tuple(d["namespace_prefixes"]),
        citation_templates={c: fam for fam, names in d["citation_templates"].items() for c in canon(names)},
        external_data_templates=frozenset(canon(d["external_data_templates"])),
        identifier_params={p: scheme for scheme, names in d["identifier_params"].items() for p in names},
        url_params=frozenset(d["url_params"]),
        wrappers={c: scheme for scheme, names in d["wrappers"].items() for c in canon(names)},
        markers=frozenset(canon(d["markers"])),
        marker_render_titles=frozenset(d["marker_render_titles"]),
        generated_refs=generated,
        reflists=reflists,
        redirect_words=tuple(d["redirect_words"]),
        doi_text_labels=tuple(d["doi_text_labels"]),
        warning_terms=tuple(d["warning_terms"]),
        ambiguous_terms=tuple(d["ambiguous_terms"]),
    )


@cache
def load_profile() -> Profile:
    text = resources.files("citerift.wiki").joinpath("data/profile-v1.json").read_bytes()
    raw = loads_strict(text)
    return Profile(
        version=raw["profile_version"],
        digest=digest(raw),
        wikis={w: _wiki(w, raw["wikis"][w]) for w in SUPPORTED_WIKIS},
        excluded_tags=frozenset(raw["excluded_tags"]),
        unsupported_tags=frozenset(raw["unsupported_tags"]),
        raw=raw,
    )
