"""DOI and PMID normalization (SPECIFICATION.md 6; directive section 14 item 14 and idempotence)."""

from __future__ import annotations

import pytest

from citerift.retraction.identifiers import ascii_fold, normalize_doi, normalize_pmid
from citerift.retraction.search import search_normalize, title_tokens


def key(raw: str, **kw: bool) -> str | None:
    return normalize_doi(raw, **kw).normalized


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected", "form"),
    [
        ("10.1000/ABC", "10.1000/abc", "bare"),
        ("  10.1000/abc  ", "10.1000/abc", "bare"),
        ("doi:10.1000/abc", "10.1000/abc", "doi_prefix"),
        ("DOI:10.1000/abc", "10.1000/abc", "doi_prefix"),
        ("https://doi.org/10.1000/abc", "10.1000/abc", "doi_url"),
        ("http://dx.doi.org/10.1000/ABC", "10.1000/abc", "doi_url"),
        ("HTTPS://DOI.ORG/10.1000/x", "10.1000/x", "doi_url"),
        ("https://doi.org/10.1000/a%2Fb", "10.1000/a/b", "doi_url"),
        ("https://doi.org/10.1000/a%252Fb", "10.1000/a%2fb", "doi_url"),  # decoded once only
        ("10.1000/a%2Fb", "10.1000/a%2fb", "bare"),  # bare percent stays literal
        ("10.1000/a+b", "10.1000/a+b", "bare"),
        ("https://doi.org/10.1000/a+b", "10.1000/a+b", "doi_url"),  # no unquote_plus
        ("10.1000/abc.", "10.1000/abc.", "bare"),  # final punctuation kept
        ("10.1000/(abc);", "10.1000/(abc);", "bare"),
        ("10.1000.10/abc", "10.1000.10/abc", "bare"),
        ("10.1000/ÄBC", "10.1000/Äbc", "bare"),  # non-ASCII is not case folded
        ("10.1000/café", "10.1000/café", "bare"),
        ("10.1000/دراسة", "10.1000/دراسة", "bare"),
    ],
)
def test_rde_doi_valid_forms(raw: str, expected: str, form: str) -> None:
    n = normalize_doi(raw)
    assert n.normalized == expected
    assert n.input_form == form
    assert n.valid and not n.missing


@pytest.mark.negative
@pytest.mark.parametrize(
    ("raw", "issue"),
    [
        ("", "DOI_EMPTY"),
        ("unavailable", "DOI_SYNTAX_INVALID"),  # a sentinel only in source fields
        ("10.1000/a\u202eb", "DOI_CONTAINS_FORMAT_CHARACTER"),
        ("10.1000/a\u200bb", "DOI_CONTAINS_FORMAT_CHARACTER"),
        ("10.1000/a\ufeffb", "DOI_CONTAINS_FORMAT_CHARACTER"),
        ("10.1000/a b", "DOI_CONTAINS_WHITESPACE"),
        ("10.1000/a\xa0b", "DOI_CONTAINS_WHITESPACE"),
        ("10.1000/a\u2028b", "DOI_CONTAINS_WHITESPACE"),
        ("10.1000/a\x07b", "DOI_CONTAINS_CONTROL"),
        ("10.1000/a\x85b", "DOI_CONTAINS_CONTROL"),
        ("x10.1007/978-3-030-00524-5_9", "DOI_SYNTAX_INVALID"),
        ("10.12/abc", "DOI_SYNTAX_INVALID"),
        ("10.1000/", "DOI_SYNTAX_INVALID"),
        ("１0.1000/abc", "DOI_SYNTAX_INVALID"),  # fullwidth digit lookalike
        ("10.1000/" + "a" * 600, "DOI_TOO_LONG"),
        ("doi: 10.1000/abc", "DOI_PREFIX_INVALID"),
        ("doi:doi:10.1000/abc", "DOI_PREFIX_INVALID"),
        ("https://example.org/10.1000/abc", "DOI_URL_HOST_INVALID"),
        ("https://doi.org.evil.example/10.1000/abc", "DOI_URL_HOST_INVALID"),
        ("https://user@doi.org/10.1000/abc", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org:443/10.1000/abc", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.1000/abc?x=1", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.1000/abc#frag", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.1000/a%zzb", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.1000/a%ffb", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.1000/a%20b", "DOI_CONTAINS_WHITESPACE"),
        ("10.1000/abc' OR '1'='1", "DOI_CONTAINS_WHITESPACE"),
    ],
)
def test_rde_doi_invalid_forms(raw: str, issue: str) -> None:
    n = normalize_doi(raw)
    assert n.normalized is None
    assert issue in n.issues


@pytest.mark.unit
def test_rde_doi_sentinels_only_in_source_fields() -> None:
    for raw in ("unavailable", "Unavailable"):
        source = normalize_doi(raw, source_field=True)
        assert source.missing and source.normalized is None and source.issues == ("DOI_SENTINEL_UNAVAILABLE",)
        assert not normalize_doi(raw).missing
    assert not normalize_doi("UNAVAILABLE", source_field=True).missing  # exact labels only


@pytest.mark.unit
def test_rde_doi_informational_issues_keep_the_key() -> None:
    n = normalize_doi("10.1002/(SICI)1097-4636%3C247::AID")
    assert n.valid and "DOI_LITERAL_PERCENT" in n.issues
    assert normalize_doi("10.1000/é").issues == ("DOI_NON_ASCII_SUFFIX",)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12345", "12345"),
        (" 123 ", "123"),
        ("123456789", "123456789"),
        ("https://pubmed.ncbi.nlm.nih.gov/123/", "123"),
        ("https://pubmed.ncbi.nlm.nih.gov/123", "123"),
        ("http://www.ncbi.nlm.nih.gov/pubmed/123", "123"),
    ],
)
def test_rde_pmid_valid(raw: str, expected: str) -> None:
    assert normalize_pmid(raw).normalized == expected


@pytest.mark.negative
@pytest.mark.parametrize(
    ("raw", "issue", "missing"),
    [
        ("", "PMID_EMPTY", True),
        ("0", "PMID_ZERO_SENTINEL", True),
        ("0000000000", "PMID_ZERO_SENTINEL", True),
        ("00069063", "PMID_LEADING_ZERO", False),
        ("1234567890", "PMID_TOO_LONG", False),
        ("١٢٣", "PMID_NON_ASCII_DIGIT", False),
        ("１２３", "PMID_NON_ASCII_DIGIT", False),
        ("-123", "PMID_NOT_INTEGER", False),
        ("123.0", "PMID_NOT_INTEGER", False),
        ("1e5", "PMID_NOT_INTEGER", False),
        ("+123", "PMID_NOT_INTEGER", False),
        ("123; DROP TABLE event", "PMID_NOT_INTEGER", False),
        ("https://example.org/pubmed/123", "PMID_URL_INVALID", False),
        ("https://www.ncbi.nlm.nih.gov/pubmed/123/", "PMID_URL_INVALID", False),
    ],
)
def test_rde_pmid_invalid(raw: str, issue: str, missing: bool) -> None:
    n = normalize_pmid(raw)
    assert n.normalized is None
    assert n.issues == (issue,)
    assert n.missing is missing


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "10.1000/ABC",
        "https://doi.org/10.1000/a%252Fb",
        "doi:10.1000/X%3C1",
        "10.1000/Äé+;.",
        "https://doi.org/10.1000/%E2%80%93dash",
    ],
)
def test_rde_doi_normalization_is_idempotent(raw: str) -> None:
    k = key(raw)
    assert k is not None
    assert key(k) == k
    assert key(k, source_field=True) == k


@pytest.mark.unit
def test_rde_ascii_fold_touches_ascii_only() -> None:
    assert ascii_fold("ABCxyzÄİΣ") == "abcxyzÄİΣ"


@pytest.mark.unit
def test_rde_search_normalization_is_separate_from_identifiers() -> None:
    assert search_normalize("دِرَاسَـة") == "دراسة"  # marks and tatweel removed for search only
    assert key("10.1000/دِرَاسَة") == "10.1000/دِرَاسَة"  # never for identifiers
    assert title_tokens("A Study of ÄBC, an ab") == ["study", "äbc"]
