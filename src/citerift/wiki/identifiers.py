"""Thin adapter to the accepted Stage 02 normalizers (SPECIFICATION.md 11.4).

``normalize_doi`` and ``normalize_pmid`` are imported from ``citerift.retraction.identifiers`` and used unchanged.
This module only performs the documented structural decoding that comes before them, and records it:

    raw source lexeme -> structural decoding (steps listed) -> normalizer input -> Stage 02 ``Normalized``

Structural steps never repair an identifier: no punctuation trimming, no Unicode normalization, no digit
conversion, no bidi removal. Percent-decoding is applied at most once, and only by the Stage 02 normalizer for
resolver URLs, or once here for the DOI path of a publisher URL (recorded as a step).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from citerift.retraction.identifiers import Normalized, normalize_doi, normalize_pmid

NORMALIZER = "citerift.retraction.identifiers"
_DOI_PATH = r"/doi/(?:(?:abs|full|pdf|epdf|book|reader)/)?(10\.[0-9]{4,9}/.+)"
_PUBLISHER_DOI_PATH = re.compile(r"(?i)^https?://[^/]+" + _DOI_PATH + "$")
# A path segment that names a page view of the article rather than part of the DOI. DOIs may contain "/", so the
# boundary is not decided: the DOI is kept whole and marked ambiguous.
_VIEW_SEGMENT = re.compile(r"(?i)/(?:abstract|full|pdf|epdf|references|suppinfo|citedby|figures|summary|meta)$")
DOI_RESOLVER_HOSTS = frozenset({"doi.org", "dx.doi.org", "www.doi.org"})
_HEX2 = re.compile(r"%[0-9A-Fa-f]{2}")


@dataclass(frozen=True)
class Decoded:
    normalizer_input: str
    steps: tuple[str, ...]
    normalized: Normalized

    def to_json(self) -> dict[str, Any]:
        return {
            "normalizer_input": self.normalizer_input,
            "structural_steps": list(self.steps),
            "normalization": self.normalized.to_json(),
        }


def _decode_percent_once(path: str) -> str | None:
    if "%" in _HEX2.sub("", path):
        return None
    raw = bytearray()
    i = 0
    while i < len(path):
        if path[i] == "%":
            raw.append(int(path[i + 1 : i + 3], 16))
            i += 3
        else:
            raw += path[i].encode("utf-8", "surrogatepass")
            i += 1
    try:
        return raw.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None


def decode(scheme: str, origin: str, decoded: str, steps: tuple[str, ...]) -> Decoded:
    """Structural decoding for one candidate. ``decoded`` already has comments removed and entities decoded
    (``steps`` names what was done)."""
    out_steps = list(steps)
    value = decoded
    if origin == "url":
        value = value.strip()
        if value.startswith("//"):
            value = "https:" + value
            out_steps.append("PROTOCOL_RELATIVE_URL_COMPLETED")
        cut = min((i for i in (value.find("?"), value.find("#")) if i >= 0), default=-1)
        if cut >= 0:
            value = value[:cut]
            out_steps.append("URL_QUERY_FRAGMENT_REMOVED")
        host = re.match(r"(?i)^https?://([^/]+)", value)
        host_name = host.group(1).casefold() if host else ""
        if scheme == "doi" and host_name not in DOI_RESOLVER_HOSTS:
            m = _PUBLISHER_DOI_PATH.match(value)
            if m:
                path = m.group(1)
                once = _decode_percent_once(path)
                value = once if once is not None else path
                out_steps.append("PUBLISHER_URL_DOI_PATH")
                if once is not None and once != path:
                    out_steps.append("PERCENT_DECODED_ONCE")
                if _VIEW_SEGMENT.search(value):
                    out_steps.append("DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS")
    normalized = normalize_doi(value) if scheme == "doi" else normalize_pmid(value)
    return Decoded(value, tuple(out_steps), normalized)


_URL = re.compile(r"(?i)^(?:https?:)?//([^/?#\s]+)(/[^?#\s]*)?(?:[?#]\S*)?$")


def url_scheme(url: str) -> str | None:
    """The identifier scheme a URL denotes, from its host and path shape only (no request is ever made)."""
    m = _URL.match(url)
    if not m:
        return None
    host = m.group(1).casefold()
    path = m.group(2) or ""
    if host in DOI_RESOLVER_HOSTS:
        return "doi"
    if host == "pubmed.ncbi.nlm.nih.gov" or (host == "www.ncbi.nlm.nih.gov" and re.match(r"/pubmed(?:/|$)", path)):
        return "pmid"
    if re.match("(?i)" + _DOI_PATH, path):
        return "doi"
    return None


def decode_render_href(href: str) -> tuple[str, Decoded] | None:
    """An identifier link in the rendered HTML (href already entity-decoded by the HTML parser)."""
    scheme = url_scheme(href)
    if scheme is None:
        return None
    return scheme, decode(scheme, "url", href, ())
