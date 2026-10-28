"""DOI and PMID normalization (SPECIFICATION.md section 6).

Normalization returns what was done, not only the result: the raw value, the input form, the key, the
transformations applied and the issues found. Nothing is repaired silently: an identifier that is not
valid keeps its raw value and has no key.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# Categories that never appear in a DOI or PMID key: controls, format characters (bidi controls,
# zero-width characters, the BOM), surrogates and every kind of space.
_FORBIDDEN_CATEGORIES = {"Cc": "CONTROL", "Cf": "FORMAT_CHARACTER", "Cs": "CONTROL"}
_SPACE_CATEGORIES = {"Zs", "Zl", "Zp"}
_DOI_SYNTAX = re.compile(r"10\.[0-9]{4,9}(?:\.[0-9]+)*/.+", re.ASCII | re.DOTALL)
_HEX2 = re.compile(r"%[0-9A-Fa-f]{2}")
_ASCII_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
_DOI_HOSTS = ("doi.org", "dx.doi.org")
_PUBMED_URL = (
    re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/([^/?#]*)/?", re.ASCII | re.IGNORECASE),
    re.compile(r"www\.ncbi\.nlm\.nih\.gov/pubmed/([^/?#]*)", re.ASCII | re.IGNORECASE),
)
DOI_MAX_LENGTH = 512
PMID_MAX_DIGITS = 9
DOI_SOURCE_SENTINELS = ("unavailable", "Unavailable")
# Outer whitespace that is trimmed: Unicode whitespace except control characters, with tab, LF and CR allowed.
# Other controls Python treats as whitespace (U+000B, U+000C, U+001C to U+001F, U+0085) stay in the value and are
# then rejected as controls, never silently removed (SPECIFICATION.md 16, C-18).
TRIM_WHITESPACE = (
    "\t\n\r\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)


@dataclass(frozen=True)
class Normalized:
    raw: str
    scheme: str
    input_form: str
    normalized: str | None
    transformations: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    missing: bool = field(default=False)

    @property
    def valid(self) -> bool:
        return self.normalized is not None

    def to_json(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "scheme": self.scheme,
            "input_form": self.input_form,
            "normalized": self.normalized,
            "transformations": list(self.transformations),
            "issues": list(self.issues),
            "missing": self.missing,
            "valid": self.valid,
        }


def ascii_fold(value: str) -> str:
    """Lower-case ASCII A-Z only; every other code point is kept."""
    return value.translate(_ASCII_FOLD)


def _character_issues(value: str) -> list[str]:
    issues = []
    for ch in value:
        cat = unicodedata.category(ch)
        if cat in _SPACE_CATEGORIES or (cat == "Cc" and ch in "\t\n\r\x0b\x0c"):
            issues.append("DOI_CONTAINS_WHITESPACE")
        elif cat in _FORBIDDEN_CATEGORIES:
            issues.append("DOI_CONTAINS_" + _FORBIDDEN_CATEGORIES[cat])
    return sorted(set(issues))


def _decode_url_path(path: str) -> tuple[str | None, str | None]:
    """Percent-decode once as strict UTF-8. Returns (decoded, issue)."""
    if "%" in _HEX2.sub("", path):
        return None, "DOI_PERCENT_ENCODING_INVALID"
    out = bytearray()
    i = 0
    while i < len(path):
        if path[i] == "%":
            out.append(int(path[i + 1 : i + 3], 16))
            i += 3
        else:
            out += path[i].encode("utf-8", "surrogatepass")
            i += 1
    try:
        return out.decode("utf-8", "strict"), None
    except UnicodeDecodeError:
        return None, "DOI_PERCENT_ENCODING_INVALID"


def _split_url(value: str) -> tuple[str | None, str | None, str | None]:
    """Return (host, path, issue) for an http(s) URL without using a lenient parser."""
    scheme_end = value.index("://")
    rest = value[scheme_end + 3 :]
    slash = rest.find("/")
    if slash < 0:
        return None, None, "DOI_URL_SHAPE_INVALID"
    authority, path = rest[:slash], rest[slash + 1 :]
    if "@" in authority or ":" in authority:
        return None, None, "DOI_URL_SHAPE_INVALID"
    if "?" in path or "#" in path:
        return None, None, "DOI_URL_SHAPE_INVALID"
    return authority, path, None


def normalize_doi(raw: str, *, source_field: bool = False) -> Normalized:
    """Normalize one DOI value (SPECIFICATION.md 6.1). ``source_field`` accepts the RW missing sentinels."""
    transformations: list[str] = []
    value = raw.strip(TRIM_WHITESPACE)
    if value != raw:
        transformations.append("TRIM_OUTER_WHITESPACE")
    if value == "":
        return Normalized(raw, "doi", "empty", None, tuple(transformations), ("DOI_EMPTY",), missing=True)
    if source_field and value in DOI_SOURCE_SENTINELS:
        return Normalized(
            raw, "doi", "sentinel", None, tuple(transformations), ("DOI_SENTINEL_UNAVAILABLE",), missing=True
        )
    form = "bare"
    lowered = ascii_fold(value[:8])
    if lowered.startswith("doi:"):
        form = "doi_prefix"
        value = value[4:]
        transformations.append("STRIP_DOI_PREFIX")
        if not value.startswith("10."):
            return Normalized(raw, "doi", form, None, tuple(transformations), ("DOI_PREFIX_INVALID",))
    elif lowered.startswith(("http://", "https://")):
        form = "doi_url"
        host, path, issue = _split_url(value)
        if issue or host is None or path is None:
            return Normalized(raw, "doi", form, None, tuple(transformations), (issue or "DOI_URL_SHAPE_INVALID",))
        if ascii_fold(host) not in _DOI_HOSTS:
            return Normalized(raw, "doi", form, None, tuple(transformations), ("DOI_URL_HOST_INVALID",))
        transformations.append("STRIP_RESOLVER_URL")
        decoded, issue = _decode_url_path(path)
        if decoded is None:
            return Normalized(
                raw, "doi", form, None, tuple(transformations), (issue or "DOI_PERCENT_ENCODING_INVALID",)
            )
        if decoded != path:
            transformations.append("PERCENT_DECODE_URL_PATH")
        value = decoded
    issues = _character_issues(value)
    if not _DOI_SYNTAX.fullmatch(value):
        issues.append("DOI_SYNTAX_INVALID")
    if len(value) > DOI_MAX_LENGTH:
        issues.append("DOI_TOO_LONG")
    if issues:
        return Normalized(raw, "doi", form, None, tuple(transformations), tuple(sorted(set(issues))))
    info = []
    if form == "bare" and "%" in value:
        info.append("DOI_LITERAL_PERCENT")
    if not value.isascii():
        info.append("DOI_NON_ASCII_SUFFIX")
    key = ascii_fold(value)
    if key != value:
        transformations.append("ASCII_CASE_FOLD")
    return Normalized(raw, "doi", form, key, tuple(transformations), tuple(info))


def normalize_pmid(raw: str, *, source_field: bool = False) -> Normalized:
    """Normalize one PMID value (SPECIFICATION.md 6.2). All-zero values are the RW missing sentinel."""
    del source_field  # the rules are the same for source fields and queries
    transformations: list[str] = []
    value = raw.strip(TRIM_WHITESPACE)
    if value != raw:
        transformations.append("TRIM_OUTER_WHITESPACE")
    if value == "":
        return Normalized(raw, "pmid", "empty", None, tuple(transformations), ("PMID_EMPTY",), missing=True)
    form = "bare"
    lowered = ascii_fold(value)
    if lowered.startswith(("http://", "https://")):
        form = "pmid_url"
        rest = value[value.index("://") + 3 :]
        for pattern in _PUBMED_URL:
            m = pattern.fullmatch(rest)
            if m:
                value = m.group(1)
                transformations.append("STRIP_PUBMED_URL")
                break
        else:
            return Normalized(raw, "pmid", form, None, tuple(transformations), ("PMID_URL_INVALID",))
    if value and all("0" <= ch <= "9" for ch in value):
        if set(value) == {"0"}:
            return Normalized(raw, "pmid", "sentinel", None, tuple(transformations), ("PMID_ZERO_SENTINEL",), True)
        if value[0] == "0":
            return Normalized(raw, "pmid", form, None, tuple(transformations), ("PMID_LEADING_ZERO",))
        if len(value) > PMID_MAX_DIGITS:
            return Normalized(raw, "pmid", form, None, tuple(transformations), ("PMID_TOO_LONG",))
        return Normalized(raw, "pmid", form, value, tuple(transformations), ())
    if value and all(ch.isdigit() for ch in value):
        return Normalized(raw, "pmid", form, None, tuple(transformations), ("PMID_NON_ASCII_DIGIT",))
    return Normalized(raw, "pmid", form, None, tuple(transformations), ("PMID_NOT_INTEGER",))


def normalize(scheme: str, raw: str, *, source_field: bool = False) -> Normalized:
    if scheme == "doi":
        return normalize_doi(raw, source_field=source_field)
    if scheme == "pmid":
        return normalize_pmid(raw, source_field=source_field)
    raise ValueError(f"unknown identifier scheme {scheme!r}")
