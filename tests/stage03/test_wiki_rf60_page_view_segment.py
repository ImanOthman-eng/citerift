"""RF-60: a publisher DOI URL ending in a page-view route kept that route in the normalized key. SYNTHETIC.

Found after exposure, by the final-campaign adjudication (enwiki 1377523963: the Wiley URL
``/doi/10.1111/0004-5608.00043/abstract`` gave the key ``10.1111/0004-5608.00043/abstract``). These cases are
synthetic; they are regressions, not evaluation evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract

from citerift.wiki.identifiers import decode


def doi_rows(tmp_path: Path, text: str, wiki: str = "en") -> list[dict[str, Any]]:
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    return [i for i in doc["identifiers"] if i["scheme"] == "doi"]


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
@pytest.mark.parametrize(
    ("url", "key"),
    [
        ("http://onlinelibrary.wiley.com/doi/10.1111/0004-5608.00043/abstract", "10.1111/0004-5608.00043"),
        ("https://onlinelibrary.wiley.com/doi/10.1002/abc.123/full", "10.1002/abc.123"),
        ("https://onlinelibrary.wiley.com/doi/10.1002/abc.123/PDF", "10.1002/abc.123"),
        ("https://pubs.acs.org/doi/abs/10.1021/xy.5/suppinfo", "10.1021/xy.5"),
        ("https://www.tandfonline.com/doi/10.1080/1/2/references", "10.1080/1/2"),
    ],
)
def test_page_view_route_is_not_part_of_the_key(tmp_path: Path, wiki: str, url: str, key: str) -> None:
    (row,) = doi_rows(tmp_path, f"A<ref>{url}</ref>", wiki)
    assert row["normalization"]["normalized"] == key
    steps = row["decoding"]["structural_steps"]
    assert "DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS" in steps
    assert "PAGE_VIEW_SEGMENT_REMOVED" in steps
    assert row["role"] == "identifier_link"


@pytest.mark.regression
def test_removed_route_stays_reported_as_ambiguous(tmp_path: Path) -> None:
    doc = extract(bundle(tmp_path, "A<ref>https://onlinelibrary.wiley.com/doi/10.1002/abc.123/abstract</ref>"))
    assert "IDENTIFIER_BOUNDARY_AMBIGUOUS" in codes(doc)


@pytest.mark.regression
@pytest.mark.parametrize(
    "url",
    [
        # nothing but the route after the prefix: removing it would leave no DOI, so the text stays as written
        "https://onlinelibrary.wiley.com/doi/10.1111/abstract",
        # a route word inside the suffix, not at its end
        "https://onlinelibrary.wiley.com/doi/10.1002/abstract.123",
        "https://onlinelibrary.wiley.com/doi/10.1002/full/x",
        # a longer last segment that only starts with a route word
        "https://onlinelibrary.wiley.com/doi/10.1002/abc/abstracts",
    ],
)
def test_route_words_inside_the_doi_are_kept(url: str) -> None:
    got = decode("doi", "url", url, ())
    assert got is not None
    assert "PAGE_VIEW_SEGMENT_REMOVED" not in got.steps
    assert got.normalizer_input == url.split("/doi/", 1)[1]


@pytest.mark.regression
def test_only_one_route_segment_is_removed() -> None:
    got = decode("doi", "url", "https://onlinelibrary.wiley.com/doi/10.1002/abc.123/full/pdf", ())
    assert got is not None
    assert got.normalizer_input == "10.1002/abc.123/full"
    assert got.normalized.normalized == "10.1002/abc.123/full"
    assert "DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS" in got.steps


@pytest.mark.regression
def test_resolver_urls_and_fields_are_unchanged(tmp_path: Path) -> None:
    """doi.org URLs and template fields never pass the publisher path rule; their text is kept as written."""
    rows = doi_rows(tmp_path, "A<ref>https://doi.org/10.1000/x/abstract {{cite journal|doi=10.1000/y/full}}</ref>")
    assert [r["normalization"]["normalized"] for r in rows] == ["10.1000/x/abstract", "10.1000/y/full"]
    assert all("PAGE_VIEW_SEGMENT_REMOVED" not in r["decoding"]["structural_steps"] for r in rows)
