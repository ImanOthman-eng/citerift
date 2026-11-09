"""DOI boundary audit of 2026-11-02 (D-1, D-2): cases where the key or the occurrence differed from the annotation
guide's definition and MediaWiki's behaviour. SYNTHETIC regressions, not evaluation evidence.

- D-1: an HTML character reference inside a bare URL in a template field stayed in the key (MediaWiki decodes it
  in the link target; the guide decodes entities).
- D-2: a publisher URL whose ``/doi/`` path separates prefix and suffix with ``%2F`` gave no occurrence at all (a
  silent loss); the guide percent-decodes a URL once.

D-5 (sentence punctuation after a DOI in text) is NOT changed: the specification keeps the punctuation and flags
the boundary ambiguous instead of trimming it (no suffix-stripping rule). These tests pin that, in both languages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract


def dois(tmp_path: Path, text: str, wiki: str = "en") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    return [i for i in doc["identifiers"] if i["scheme"] == "doi"], doc


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text", "key"),
    [
        ("en", "A<ref>Smith, J. doi:10.1002/abc.123.</ref>", "10.1002/abc.123."),
        ("en", "A<ref>Smith, J. 10.1002/abc.123, p. 4.</ref>", "10.1002/abc.123,"),
        ("ar", "أ<ref>سميث. دوي:10.1002/abc.123،</ref>", "10.1002/abc.123،"),
        ("ar", "أ<ref>سميث. doi:10.1002/abc.123.</ref>", "10.1002/abc.123."),
    ],
)
def test_trailing_sentence_punctuation_is_kept_and_flagged_not_stripped(
    tmp_path: Path, wiki: str, text: str, key: str
) -> None:
    (row,), doc = dois(tmp_path, text, wiki)
    assert row["normalization"]["normalized"] == key
    assert row["boundary"] == "ambiguous_trailing_punctuation"
    assert "IDENTIFIER_BOUNDARY_AMBIGUOUS" in codes(doc)


@pytest.mark.regression
@pytest.mark.parametrize(
    ("text", "key"),
    [
        # balanced parentheses belong to the DOI
        ("A<ref>doi:10.1002/(SICI)1097-4636(199703)</ref>", "10.1002/(sici)1097-4636(199703)"),
        # a field is the DOI as written, also with a final dot
        ("A<ref>{{cite journal|title=T|doi=10.1002/abc.123.}}</ref>", "10.1002/abc.123."),
        # resolver URLs keep MediaWiki's link boundary
        ("A<ref>[https://doi.org/10.1002/abc.123. x]</ref>", "10.1002/abc.123."),
    ],
)
def test_other_trailing_characters_are_kept(tmp_path: Path, text: str, key: str) -> None:
    (row,), _ = dois(tmp_path, text)
    assert row["normalization"]["normalized"] == key


@pytest.mark.regression
@pytest.mark.parametrize(
    "url",
    [
        "https://onlinelibrary.wiley.com/doi/10.1002/abc&amp;123",
        "https://doi.org/10.1002/abc&amp;123",
        "https://onlinelibrary.wiley.com/doi/10.1002/abc&#38;123",
    ],
)
def test_character_reference_in_a_url_field_is_decoded(tmp_path: Path, url: str) -> None:
    (row,), _ = dois(tmp_path, f"A<ref>{{{{cite journal|title=T|url={url}}}}}</ref>")
    assert row["normalization"]["normalized"] == "10.1002/abc&123"
    assert "HTML_ENTITY_DECODED" in row["decoding"]["structural_steps"]


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
@pytest.mark.parametrize(
    "url",
    [
        "https://onlinelibrary.wiley.com/doi/10.1002%2Fabc.123",
        "https://onlinelibrary.wiley.com/doi/abs/10.1002%2fabc.123",
    ],
)
def test_encoded_separator_in_a_publisher_doi_path(tmp_path: Path, wiki: str, url: str) -> None:
    (row,), _ = dois(tmp_path, f"A<ref>[{url} Paper]</ref>", wiki)
    assert row["normalization"]["normalized"] == "10.1002/abc.123"
    assert {"PUBLISHER_URL_DOI_PATH", "PERCENT_DECODED_ONCE"} <= set(row["decoding"]["structural_steps"])
    assert row["role"] == "identifier_link"


@pytest.mark.regression
def test_snapshot_urls_stay_excluded(tmp_path: Path) -> None:
    rows, _ = dois(tmp_path, "A<ref>[https://web.archive.org/web/2020/https://doi.org/10.1002%2Fabc.123 x]</ref>")
    assert rows == []
