"""Pinned real reviewed cases on the attributed fixture (gate 02-C in CI form).

``fixtures/rw_real_subset.csv`` holds selected fields of the related records of every case (at most 120 records,
attributed to Retraction Watch via Crossref; docs/sources-and-attribution.md). ``fixtures/real_cases.json``
records, per case, the outcome the independent prebuild simulator derived from the same records and the engine's
answer on the full pinned index. This test rebuilds an index from the fixture alone and requires both."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction.query import Index, lookup
from citerift.retraction.store import build

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "real_cases.json").read_text(encoding="utf-8"))
DATA = (FIXTURES / MANIFEST["fixture"]).read_bytes()
COMPARED = ("state", "status", "value", "date_status", "date_value", "events", "identity", "record_ids")


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("real")
    path = tmp / MANIFEST["fixture"]
    path.write_bytes(DATA)
    receipt = S.receipt_for(
        DATA,
        repository="https://gitlab.com/crossref/retraction-watch-data",
        commit="a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4",
        path=MANIFEST["fixture"],
        url="https://gitlab.com/crossref/retraction-watch-data/-/raw/a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4/retraction_watch.csv",
        attribution=MANIFEST["attribution"],
    )
    return build(path, receipt, tmp / "index").index_path


@pytest.mark.contracts
def test_rde_real_fixture_respects_the_distribution_boundary() -> None:
    assert hashlib.sha256(DATA).hexdigest() == MANIFEST["fixture_sha256"]
    rows = list(csv.DictReader(DATA.decode("utf-8-sig").splitlines()))
    assert len(rows) == MANIFEST["fixture_records"] <= 120
    allowed = set(MANIFEST["fixture_fields"])
    for row in rows:
        assert all(value == "" for column, value in row.items() if column not in allowed)
    assert "Retraction Watch" in MANIFEST["attribution"]


@pytest.mark.integration
def test_rde_real_cases_cover_the_required_classes() -> None:
    cases = MANIFEST["cases"]
    assert len(cases) >= 40 and MANIFEST["agree"] == MANIFEST["total"] == len(cases)
    natures = {r["RetractionNature"] for r in csv.DictReader(DATA.decode("utf-8-sig").splitlines())}
    assert natures == {"Retraction", "Correction", "Expression of concern", "Reinstatement"}
    states = {c["expected_simulator"]["state"] for c in cases}
    assert states == {"matched", "notice_only", "ambiguous_identity", "no_record"}
    assert len({json.dumps(c["query"], sort_keys=True) for c in cases}) == len(cases)


@pytest.mark.integration
@pytest.mark.parametrize("case", MANIFEST["cases"], ids=[c["id"] for c in MANIFEST["cases"]])
def test_rde_real_case_on_fixture(index: Path, case: dict[str, Any]) -> None:
    q = case["query"]
    out = lookup(index, q.get("doi"), q.get("pmid"), page_size=100)
    proj = out["projection"] or {}
    status = proj.get("retraction_status") or {}
    date = proj.get("retraction_date") or {}
    got = {
        "state": out["lookup_state"],
        "status": status.get("status"),
        "value": status.get("value"),
        "date_status": date.get("status"),
        "date_value": date.get("value"),
        "events": out["total_event_count"],
        "identity": out["identity"]["status"],
        "record_ids": sorted(e["record_id"] for e in out["events"]),
        "role": out["identifier_role"],
    }
    full = case["engine_full_index"]
    expected = case["expected_simulator"]
    for key in COMPARED:
        assert got[key] == expected[key] == full[key], key
    assert got["role"] == full["role"]
    assert set(expected["reasons"]) <= set((proj.get("basis") or {}).get("reasons", []))


@pytest.mark.regression
def test_rde_historical_dates_are_kept(index: Path) -> None:
    [case] = [c for c in MANIFEST["cases"] if c["class"] == "historical_date_event_via_notice_query"]
    with Index(index) as ix:
        [event] = ix.gather(case["query"]["doi"]).events
    assert event["notice_date"]["reported_calendar"] == "1756-06-24"
    assert event["notice_date"]["earliest"] == "1756-06-24"  # no year cutoff, and day 24 is not a convention
    assert event["anchor"].startswith("rec:")
