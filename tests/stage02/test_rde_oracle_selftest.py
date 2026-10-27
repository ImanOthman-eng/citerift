"""Self-tests of the independent Stage 02 streaming oracle (simulations/stage02/oracle_stream.py).

The oracle is derived only from docs/verification/stage-02/SPECIFICATION.md (sections 5, 6 and 10.3); these tests
check it against the specification text on tiny synthetic CSVs that use the 10.5555 test prefix only. No network.

Run: uv run pytest tests/stage02/test_rde_oracle_selftest.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.negative]

SCRIPT = Path(__file__).resolve().parents[2] / "simulations" / "stage02" / "oracle_stream.py"
_spec = importlib.util.spec_from_file_location("stage02_oracle_stream", SCRIPT)
assert _spec and _spec.loader
oracle = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = oracle
_spec.loader.exec_module(oracle)

HEADER = [
    "Record ID",
    "Title",
    "Subject",
    "Institution",
    "Journal",
    "Publisher",
    "Country",
    "Author",
    "URLS",
    "ArticleType",
    "RetractionDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDate",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
    "RetractionNature",
    "Reason",
    "Paywalled",
    "Notes",
]


def record(
    rid: str,
    odoi: str = "",
    ndoi: str = "",
    opmid: str = "",
    npmid: str = "",
    nature: str = "Retraction",
    title: str = "Synthetic title",
) -> list[str]:
    values = dict.fromkeys(HEADER, "")
    values.update(
        {
            "Record ID": rid,
            "Title": title,
            "RetractionDate": "1/2/2020 0:00",
            "OriginalPaperDate": "1/1/2019 0:00",
            "RetractionDOI": ndoi,
            "RetractionPubMedID": npmid,
            "OriginalPaperDOI": odoi,
            "OriginalPaperPubMedID": opmid,
            "RetractionNature": nature,
        }
    )
    return [values[name] for name in HEADER]


def write_csv(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    return path


def run_rows(tmp_path: Path, rows: list[list[str]]) -> dict[str, Any]:
    return oracle.run(write_csv(tmp_path / "rw.csv", rows))


def doi_key(raw: str) -> str | None:
    return oracle.normalize_doi(raw)[0]


def pmid_key(raw: str) -> str | None:
    return oracle.normalize_pmid(raw)[0]


# ---------------------------------------------------------------- roles


def test_roles_and_notice_equal_to_original_is_excluded(tmp_path: Path) -> None:
    result = run_rows(
        tmp_path,
        [
            record("1", odoi="10.5555/A1", ndoi="10.5555/N1", opmid="111", npmid="222"),
            record("2", odoi="10.5555/a1", ndoi="10.5555/a1", opmid="333", npmid="333"),  # notice == original
            record("3", odoi="10.5555/N1", ndoi="10.5555/N3"),  # an original elsewhere that is a notice in row 1
            record("4", ndoi="10.5555/N1", npmid="111"),  # notice only; notice PMID equals row 1's original
            record("5", odoi="https://doi.org/10.5555/A1", ndoi="doi:10.5555/a1"),  # equal after normalization
        ],
    )
    assert result["records"] == 5
    assert result["accepted"] == 5
    assert result["quarantined"] == []
    assert result["doi"]["10.5555/a1"] == {"original": [1, 2, 5], "notice": []}
    assert result["doi"]["10.5555/n1"] == {"original": [3], "notice": [1, 4]}
    assert result["doi"]["10.5555/n3"] == {"original": [], "notice": [3]}
    assert result["pmid"]["111"] == {"original": [1], "notice": [4]}
    assert result["pmid"]["222"] == {"original": [], "notice": [1]}
    assert result["pmid"]["333"] == {"original": [2], "notice": []}
    assert result["notice_equals_original"] == {"doi": 2, "pmid": 1}
    assert set(result["doi"]) == {"10.5555/a1", "10.5555/n1", "10.5555/n3"}


def test_notice_equal_to_original_only_within_the_same_scheme(tmp_path: Path) -> None:
    # The DOI and PMID schemes are separate key spaces; a record can be original for its DOI and notice for a PMID.
    result = run_rows(tmp_path, [record("1", odoi="10.5555/x", npmid="12345")])
    assert result["doi"] == {"10.5555/x": {"original": [1], "notice": []}}
    assert result["pmid"] == {"12345": {"original": [], "notice": [1]}}


# ---------------------------------------------------------------- DOI rules


@pytest.mark.parametrize("raw", ["", "   ", "unavailable", "Unavailable", " Unavailable\t"])
def test_doi_sentinels_are_missing_not_invalid(raw: str) -> None:
    assert oracle.normalize_doi(raw)[:2] == (None, oracle.MISSING)


@pytest.mark.parametrize("raw", ["UNAVAILABLE", "unAvailable", "n/a", "none"])
def test_other_doi_placeholders_are_invalid(raw: str) -> None:
    assert oracle.normalize_doi(raw)[:2] == (None, oracle.INVALID)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.5555/ABC", "10.5555/abc"),
        ("  10.5555/abc\n", "10.5555/abc"),
        ("doi:10.5555/abc", "10.5555/abc"),
        ("DOI:10.5555/ABC", "10.5555/abc"),
        ("Doi:10.5555/abc", "10.5555/abc"),
        ("https://doi.org/10.5555/abc", "10.5555/abc"),
        ("http://doi.org/10.5555/abc", "10.5555/abc"),
        ("HTTPS://DOI.ORG/10.5555/ABC", "10.5555/abc"),
        ("https://dx.doi.org/10.5555/abc", "10.5555/abc"),
        ("http://DX.DOI.org/10.5555/abc", "10.5555/abc"),
        ("https://doi.org/10.5555/a%2Fb", "10.5555/a/b"),
        ("https://doi.org/10.5555%2Fab", "10.5555/ab"),
        ("https://doi.org/10.5555/a%3Cb%3E", "10.5555/a<b>"),
        ("https://doi.org/10.5555/caf%C3%A9", "10.5555/caf\u00e9"),
        ("https://doi.org/10.5555/a+b", "10.5555/a+b"),
        ("https://doi.org/10.5555/a%2Bb", "10.5555/a+b"),
        ("https://doi.org/10.5555/a%2525", "10.5555/a%25"),  # decoded exactly once
        ("10.5555/a/b/c", "10.5555/a/b/c"),
        ("10.5555.1.22/x", "10.5555.1.22/x"),
        ("10.123456789/x", "10.123456789/x"),
        ("10.5555/x.", "10.5555/x."),
        ("10.5555/x)", "10.5555/x)"),
        ("10.5555/x;", "10.5555/x;"),
        ("10.5555/x+", "10.5555/x+"),
    ],
)
def test_doi_accepted_forms(raw: str, expected: str) -> None:
    assert oracle.normalize_doi(raw) == (expected, oracle.VALID, "")
    assert doi_key(expected) == expected  # idempotence


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("doi: 10.5555/abc", "DOI_PREFIX_INVALID"),
        ("doi:doi:10.5555/abc", "DOI_PREFIX_INVALID"),
        ("doi:https://doi.org/10.5555/abc", "DOI_PREFIX_INVALID"),
        ("https://www.doi.org/10.5555/abc", "DOI_URL_HOST_INVALID"),
        ("https://doi.org.example/10.5555/abc", "DOI_URL_HOST_INVALID"),
        ("https://example.org/10.5555/abc", "DOI_URL_HOST_INVALID"),
        ("https://doi.org:443/10.5555/abc", "DOI_URL_SHAPE_INVALID"),
        ("https://user@doi.org/10.5555/abc", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.5555/abc?x=1", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.5555/abc#frag", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org?10.5555/abc", "DOI_URL_SHAPE_INVALID"),
        ("https://doi.org/10.5555/a%zz", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.5555/a%2", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.5555/a%FF", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.5555/a%C3", "DOI_PERCENT_ENCODING_INVALID"),
        ("https://doi.org/10.5555/a%20b", "DOI_CONTAINS_WHITESPACE"),
        ("https://doi.org/", "DOI_SYNTAX_INVALID"),
        ("https://doi.org//10.5555/abc", "DOI_SYNTAX_INVALID"),
        ("ftp://doi.org/10.5555/abc", "DOI_SYNTAX_INVALID"),
        ("doi.org/10.5555/abc", "DOI_SYNTAX_INVALID"),
        ("10.555/abc", "DOI_SYNTAX_INVALID"),
        ("10.1234567890/abc", "DOI_SYNTAX_INVALID"),
        ("10.5555/", "DOI_SYNTAX_INVALID"),
        ("10.5555", "DOI_SYNTAX_INVALID"),
        ("10.5555./abc", "DOI_SYNTAX_INVALID"),
        ("11.5555/abc", "DOI_SYNTAX_INVALID"),
        ("x10.5555/abc", "DOI_SYNTAX_INVALID"),
        ("10.\u0665\u0665\u0665\u0665/abc", "DOI_SYNTAX_INVALID"),  # Arabic-Indic digits are not ASCII digits
        ("10.\uff15\uff15\uff15\uff15/abc", "DOI_SYNTAX_INVALID"),  # fullwidth digits
        ("10.5555/a b", "DOI_CONTAINS_WHITESPACE"),
        ("10.5555/a\u00a0b", "DOI_CONTAINS_WHITESPACE"),
        ("10.5555/a\u2028b", "DOI_CONTAINS_WHITESPACE"),
        ("10.5555/a\u2029b", "DOI_CONTAINS_WHITESPACE"),
        ("10.5555/a\tb", "DOI_CONTAINS_CONTROL"),
        ("10.5555/a\x7fb", "DOI_CONTAINS_CONTROL"),
        ("10.5555/a\u200bb", "DOI_CONTAINS_FORMAT_CHARACTER"),  # zero-width space
        ("10.5555/a\u200db", "DOI_CONTAINS_FORMAT_CHARACTER"),  # zero-width joiner
        ("10.5555/a\u202eb", "DOI_CONTAINS_FORMAT_CHARACTER"),  # right-to-left override
        ("10.5555/a\u2066b", "DOI_CONTAINS_FORMAT_CHARACTER"),  # left-to-right isolate
        ("10.5555/a\u200fb", "DOI_CONTAINS_FORMAT_CHARACTER"),  # right-to-left mark
        ("10.5555/a\ufeffb", "DOI_CONTAINS_FORMAT_CHARACTER"),  # BOM inside the value
        ("https://doi.org/10.5555/a%E2%80%8Bb", "DOI_CONTAINS_FORMAT_CHARACTER"),  # decoded zero-width space
        ("https://doi.org/10.5555/a%00b", "DOI_CONTAINS_CONTROL"),
    ],
)
def test_doi_invalid_forms(raw: str, reason: str) -> None:
    assert oracle.normalize_doi(raw) == (None, oracle.INVALID, reason)


def test_doi_length_limit() -> None:
    head = "10.5555/"
    at_limit = head + "a" * (512 - len(head))
    assert doi_key(at_limit) == at_limit
    assert oracle.normalize_doi(at_limit + "a") == (None, oracle.INVALID, "DOI_TOO_LONG")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.5555/a%3Cb", "10.5555/a%3cb"),  # bare percent is literal, never decoded
        ("10.5555/a%3cb", "10.5555/a%3cb"),
        ("10.5555/100%", "10.5555/100%"),
        ("10.5555/%zz", "10.5555/%zz"),
        ("doi:10.5555/a%2Fb", "10.5555/a%2fb"),  # the doi: form is not decoded either
    ],
)
def test_bare_percent_is_literal(raw: str, expected: str) -> None:
    assert doi_key(raw) == expected
    assert doi_key(expected) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.5555/\u00c9A", "10.5555/\u00c9a"),
        ("10.5555/\u00c4\u00d6\u00dc-X", "10.5555/\u00c4\u00d6\u00dc-x"),
        ("10.5555/STRASSE-\u00df", "10.5555/strasse-\u00df"),
        ("10.5555/\u212aelvin", "10.5555/\u212aelvin"),  # KELVIN SIGN is not folded to k
        ("10.5555/\u0130I", "10.5555/\u0130i"),  # LATIN CAPITAL I WITH DOT ABOVE is kept
        ("10.5555/\u03a3\u0391", "10.5555/\u03a3\u0391"),
        ("10.5555/e\u0301", "10.5555/e\u0301"),  # no NFC composition
        ("10.5555/\ufb01", "10.5555/\ufb01"),  # no NFKC ligature expansion
        ("10.5555/\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "10.5555/\u0627\u0644\u0639\u0631\u0628\u064a\u0629"),
    ],
)
def test_case_folding_is_ascii_only(raw: str, expected: str) -> None:
    assert doi_key(raw) == expected
    assert doi_key(expected) == expected


# ---------------------------------------------------------------- PMID rules


@pytest.mark.parametrize("raw", ["", "  ", "0", "00000000", " 0 "])
def test_pmid_missing(raw: str) -> None:
    assert oracle.normalize_pmid(raw)[:2] == (None, oracle.MISSING)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", "1"),
        ("12345678", "12345678"),
        ("123456789", "123456789"),
        (" 4321 ", "4321"),
        ("https://pubmed.ncbi.nlm.nih.gov/4321", "4321"),
        ("https://pubmed.ncbi.nlm.nih.gov/4321/", "4321"),
        ("http://PubMed.NCBI.nlm.nih.gov/4321", "4321"),
        ("HTTPS://www.ncbi.nlm.nih.gov/pubmed/4321", "4321"),
        ("http://WWW.NCBI.NLM.NIH.GOV/pubmed/4321", "4321"),
    ],
)
def test_pmid_valid(raw: str, expected: str) -> None:
    assert oracle.normalize_pmid(raw) == (expected, oracle.VALID, "")
    assert pmid_key(expected) == expected


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("0123", "PMID_LEADING_ZERO"),
        ("00069063", "PMID_LEADING_ZERO"),
        ("1234567890", "PMID_TOO_LONG"),
        ("\u0661\u0662\u0663", "PMID_NON_ASCII_DIGIT"),  # Arabic-Indic digits
        ("\uff11\uff12\uff13", "PMID_NON_ASCII_DIGIT"),  # fullwidth digits
        ("+123", "PMID_NOT_INTEGER"),
        ("-123", "PMID_NOT_INTEGER"),
        ("12.0", "PMID_NOT_INTEGER"),
        ("1e5", "PMID_NOT_INTEGER"),
        ("12 34", "PMID_NOT_INTEGER"),
        ("PMID:123", "PMID_NOT_INTEGER"),
        ("12\u200b3", "PMID_NOT_INTEGER"),
        ("https://pubmed.ncbi.nlm.nih.gov/", "PMID_URL_INVALID"),
        ("https://pubmed.ncbi.nlm.nih.gov/12a", "PMID_URL_INVALID"),
        ("https://pubmed.ncbi.nlm.nih.gov/123?x=1", "PMID_URL_INVALID"),
        ("https://pubmed.ncbi.nlm.nih.gov/123//", "PMID_URL_INVALID"),
        ("https://pubmed.ncbi.nlm.nih.gov:443/123", "PMID_URL_INVALID"),
        ("https://www.ncbi.nlm.nih.gov/123", "PMID_URL_INVALID"),
        ("https://www.ncbi.nlm.nih.gov/pmc/123", "PMID_URL_INVALID"),
        ("https://ncbi.nlm.nih.gov/pubmed/123", "PMID_URL_INVALID"),
        ("https://example.org/123", "PMID_URL_INVALID"),
        ("https://pubmed.ncbi.nlm.nih.gov", "PMID_URL_INVALID"),
        ("ftp://pubmed.ncbi.nlm.nih.gov/123", "PMID_NOT_INTEGER"),
    ],
)
def test_pmid_invalid(raw: str, reason: str) -> None:
    assert oracle.normalize_pmid(raw) == (None, oracle.INVALID, reason)


def test_invalid_identifiers_are_counted_and_never_quarantine(tmp_path: Path) -> None:
    result = run_rows(
        tmp_path,
        [
            record("1", odoi="10.5555/a\u202eb", ndoi="unavailable", opmid="0123", npmid="0"),
            record("2", odoi="Unavailable", ndoi="doi: 10.5555/x", opmid="00000000", npmid="1e5"),
        ],
    )
    assert result["accepted"] == 2
    assert result["quarantined"] == []
    assert result["invalid_identifiers"] == {
        "OriginalPaperDOI": 1,
        "RetractionDOI": 1,
        "OriginalPaperPubMedID": 1,
        "RetractionPubMedID": 1,
    }
    assert result["doi"] == {}
    assert result["pmid"] == {}


# ---------------------------------------------------------------- records, quarantine and CSV structure


def test_quarantine_unknown_nature_and_field_count(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "rw.csv",
        [
            record("1", odoi="10.5555/q1", nature="Retraction"),
            record("2", odoi="10.5555/q2", nature="retraction"),
            record("3", odoi="10.5555/q3", nature="Retraction "),
            record("4", odoi="10.5555/q4", nature=""),
            record("5", odoi="10.5555/q5", nature="Withdrawal"),
            record("6", odoi="10.5555/q6", nature="Expression of Concern"),
            record("7", odoi="10.5555/q7", nature="Expression of concern"),
            record("8", odoi="10.5555/q8", nature="Correction"),
            record("9", odoi="10.5555/q9", nature="Reinstatement"),
            [*record("10", odoi="10.5555/q10"), "extra"],
            record("11", odoi="10.5555/q11")[:-1],
        ],
    )
    result = oracle.run(path)
    assert result["records"] == 11
    assert result["quarantined"] == [2, 3, 4, 5, 6, 10, 11]
    assert result["accepted"] == 4
    assert result["quarantine_reasons"] == {
        "EVENT_TYPE_UNKNOWN": 4,
        "EVENT_TYPE_MISSING": 1,
        "FIELD_COUNT_MISMATCH": 2,
    }
    assert sorted(result["doi"]) == ["10.5555/q1", "10.5555/q7", "10.5555/q8", "10.5555/q9"]


def test_embedded_newline_and_blank_lines(tmp_path: Path) -> None:
    rows = [
        record("1", odoi="10.5555/e1", title="line one\nline two\n\nline four"),
        record("2", odoi="10.5555/e2", title='quote "inside", comma'),
        record("3", odoi="10.5555/e3"),
    ]
    path = write_csv(tmp_path / "rw.csv", rows)
    data = path.read_bytes()
    # Insert blank physical lines after the header, two after record 2, and one at the end of the file.
    header_end = data.index(b"\n") + 1
    record2_end = data.index(b"\n", data.index(b'comma"')) + 1
    patched = data[:header_end] + b"\n" + data[header_end:record2_end] + b"\n\n" + data[record2_end:] + b"\n"
    path.write_bytes(patched)
    result = oracle.run(path)
    assert result["records"] == 3
    assert result["blank_lines"] == 4
    assert result["quarantined"] == []
    assert result["doi"]["10.5555/e1"]["original"] == [1]
    assert result["doi"]["10.5555/e2"]["original"] == [2]
    assert result["doi"]["10.5555/e3"]["original"] == [3]
    # header + 4 lines of record 1 + 1 + 1 + 4 blank lines
    assert result["physical_lines"] == 1 + 4 + 1 + 1 + 4


def test_bom_is_removed_from_first_header_cell_and_counts_match(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "rw.csv", [record("1", odoi="10.5555/b")])
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    result = oracle.run(path)
    assert result["records"] == 1
    assert result["source"]["bytes"] == path.stat().st_size


HEADER_BYTES = ",".join(HEADER).encode() + b"\n"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (HEADER_BYTES + b"1,\xff\xfe\n", "ENCODING_INVALID"),
        (HEADER_BYTES + b"1,\xc3\n", "ENCODING_INVALID"),
        (HEADER_BYTES + b"1,\x00\n", "NUL_BYTE"),
        (b"", "HEADER_MISSING"),
        (b"\n\n", "HEADER_MISSING"),
        (b"Record ID,Record ID\n", "HEADER_DUPLICATE"),
        (b"Record ID,Title\n1,x\n", "HEADER_CRITICAL_MISSING"),
        (HEADER_BYTES + b'1,"unterminated\n', "CSV_STRUCTURE_INVALID"),
        (HEADER_BYTES + b'1,"a"b\n', "CSV_STRUCTURE_INVALID"),
        (HEADER_BYTES + b"1,a\r2,b\n", "CSV_STRUCTURE_INVALID"),
        (HEADER_BYTES + b"1,a\r", "CSV_STRUCTURE_INVALID"),
    ],
)
def test_fatal_import_failures(tmp_path: Path, payload: bytes, code: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(payload)
    with pytest.raises(oracle.FatalImportError) as caught:
        oracle.run(path)
    assert caught.value.code == code


def test_field_larger_than_limit_is_fatal(tmp_path: Path) -> None:
    big = "x" * (oracle.FIELD_LIMIT + 1)
    path = write_csv(tmp_path / "rw.csv", [record("1", title=big)])
    with pytest.raises(oracle.FatalImportError) as caught:
        oracle.run(path)
    assert caught.value.code == "FIELD_TOO_LARGE"


def test_field_over_one_mebibyte_in_utf8_bytes_is_fatal(tmp_path: Path) -> None:
    big = "\u00e9" * (oracle.FIELD_LIMIT // 2 + 1)  # under the character limit, over 1 MiB as UTF-8
    path = write_csv(tmp_path / "rw.csv", [record("1", title=big)])
    with pytest.raises(oracle.FatalImportError) as caught:
        oracle.run(path)
    assert caught.value.code == "FIELD_TOO_LARGE"


# ---------------------------------------------------------------- absent keys and CLI


def test_absent_keys_are_valid_and_truly_absent(tmp_path: Path) -> None:
    rows = [
        record(str(i), odoi=f"10.5555/oracle-absent-{i:06d}", ndoi=f"10.5555/N{i}", opmid=str(990_000_000 + 7_919 * i))
        for i in range(1, 40)
    ]
    rows.append(record("40", odoi="10.5555/realx", ndoi="10.5555/real", npmid="5"))
    result = run_rows(tmp_path, rows)
    absent = result["absent_keys"]
    assert len(absent["doi"]) >= 1200
    assert len(absent["pmid"]) == 300
    assert len(set(absent["doi"])) == len(absent["doi"])
    assert len(set(absent["pmid"])) == len(absent["pmid"])
    for key in absent["doi"]:
        assert key not in result["doi"]
        assert doi_key(key) == key
    for key in absent["pmid"]:
        assert key not in result["pmid"]
        assert pmid_key(key) == key
    # The keys planted in the file were skipped, and realistic mutations of present keys were produced.
    assert "10.5555/oracle-absent-000001" not in absent["doi"]
    assert "10.5555/realx" not in absent["doi"]
    assert any(not key.startswith("10.5555/oracle-absent") for key in absent["doi"])
    assert str(990_000_000 + 7_919) not in absent["pmid"]
    # Deterministic across runs.
    assert oracle.run(tmp_path / "rw.csv")["absent_keys"] == absent


def test_cli_writes_sorted_json_and_summary(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "rw.csv", [record("1", odoi="10.5555/B", ndoi="10.5555/a", npmid="7")])
    out = tmp_path / "out.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--csv", str(path), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.count("\n") == 1
    assert "records=1 accepted=1 quarantined=0" in completed.stdout
    text = out.read_text()
    data = json.loads(text)
    assert text.strip() == json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    assert data["doi"] == {
        "10.5555/a": {"original": [], "notice": [1]},
        "10.5555/b": {"original": [1], "notice": []},
    }
    assert data["pmid"] == {"7": {"original": [], "notice": [1]}}


def test_cli_fatal_exit_code_and_no_output(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(b"Record ID,X\n\xff\n")
    out = tmp_path / "out.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--csv", str(path), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "ENCODING_INVALID" in completed.stderr
    assert not out.exists()
