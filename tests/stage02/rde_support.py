"""Shared helpers for the Stage 02 tests: synthetic CSV sources, receipts, Crossref replay bundles."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from citerift.retraction.corroboration import MANIFEST_VERSION, work_url
from citerift.retraction.identifiers import normalize_doi
from citerift.retraction.source import Receipt, parse_receipt
from citerift.retraction.store import build

REPO = Path(__file__).resolve().parents[2]
CASES = REPO / "simulations" / "stage02" / "cases"
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
CASE_FIELDS = {
    "id": "Record ID",
    "nature": "RetractionNature",
    "od": "OriginalPaperDOI",
    "op": "OriginalPaperPubMedID",
    "nd": "RetractionDOI",
    "np": "RetractionPubMedID",
    "rd": "RetractionDate",
    "pd": "OriginalPaperDate",
}
CASE_DEFAULTS = {"op": "", "np": "", "nd": "", "od": "", "rd": "3/12/2015 0:00", "pd": "6/15/2010 0:00"}


def load_cases(name: str) -> list[dict[str, Any]]:
    """Frozen cases with the post-freeze amendments of ``cases/post_freeze_amendments.json`` applied."""
    cases: list[dict[str, Any]] = json.loads((CASES / name).read_text(encoding="utf-8"))["cases"]
    amendments = json.loads((CASES / "post_freeze_amendments.json").read_text(encoding="utf-8"))["amendments"]
    by_id = {c["id"]: c for c in cases}
    for a in amendments:
        if a["file"] == name:
            case = by_id[a["case"]]
            assert all(case["expected"][k] == v for k, v in a["frozen_expected"].items()), a["case"]
            case["expected"] = {**case["expected"], **a["expected"]}
    return cases


def row(**values: str) -> dict[str, str]:
    """A full synthetic row; unspecified columns get neutral synthetic values."""
    out = {h: "" for h in HEADER}
    out.update({"Title": "Synthetic record", "Journal": "Synthetic Journal", "Author": "A Tester"})
    out.update({"RetractionDate": "3/12/2015 0:00", "OriginalPaperDate": "6/15/2010 0:00"})
    out.update(values)
    return out


def case_row(r: dict[str, str]) -> dict[str, str]:
    merged = {**CASE_DEFAULTS, **r}
    return row(**{CASE_FIELDS[k]: v for k, v in merged.items()}, Title=f"Synthetic title {merged['id']}")


def csv_bytes(rows: list[dict[str, str]] | list[list[str]], header: list[str] | None = None, bom: bool = True) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header or HEADER)
    for r in rows:
        writer.writerow([r[h] for h in (header or HEADER)] if isinstance(r, dict) else r)
    return ("﻿" if bom else "").encode("utf-8") + buf.getvalue().encode("utf-8")


def receipt_for(data: bytes, **overrides: Any) -> Receipt:
    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    fields: dict[str, Any] = {
        "receipt_version": "1.0.0",
        "source_id": "retraction-watch",
        "repository": "https://example.invalid/synthetic/rw",
        "commit": "0" * 40,
        "path": "retraction_watch.csv",
        "url": "https://example.invalid/synthetic/rw/retraction_watch.csv",
        "expected_bytes": len(data),
        "expected_sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": blob,
        "readme_generated_on": "2026-01-01",
        "acquired_at": "2026-01-01T00:00:00Z",
        "attribution": "Synthetic test data (10.5555 test prefix); not Retraction Watch records",
    }
    fields.update(overrides)
    return parse_receipt(fields)


def write_source(tmp: Path, data: bytes, name: str = "source.csv") -> tuple[Path, Receipt]:
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / name
    path.write_bytes(data)
    return path, receipt_for(data)


def crossref_bundle(tmp: Path, entries: list[dict[str, Any]], retrieved_at: str = "2026-01-02T00:00:00Z") -> Path:
    """Replay bundle from case-style entries {"original": DOI, "updated_by": [...]}"""
    bundle = tmp / "crossref"
    (bundle / "payloads").mkdir(parents=True, exist_ok=True)
    works = []
    for entry in entries:
        key = normalize_doi(entry["original"]).normalized
        assert key is not None
        payload = {
            "status": "ok",
            "message-type": "work",
            "message-version": "1.0.0",
            "message": {"DOI": entry["original"], "type": "journal-article", "updated-by": entry["updated_by"]},
        }
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        sha = hashlib.sha256(body).hexdigest()
        (bundle / "payloads" / f"{sha}.json").write_bytes(body)
        works.append(
            {
                "doi": key,
                "url": work_url(key),
                "outcome": "ok",
                "failure": None,
                "http_status": 200,
                "attempts": 1,
                "retrieved_at": retrieved_at,
                "payload_sha256": sha,
                "bytes": len(body),
                "waits": [],
            }
        )
    manifest = {"manifest_version": MANIFEST_VERSION, "client_version": "synthetic", "works": works}
    path = bundle / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_rows(tmp: Path, rows: list[dict[str, str]], crossref: list[dict[str, Any]] | None = None) -> Path:
    source, receipt = write_source(tmp, csv_bytes(rows))
    manifest = crossref_bundle(tmp, crossref) if crossref else None
    return build(source, receipt, tmp / "index", corroboration=manifest).index_path


def build_case(tmp: Path, case: dict[str, Any]) -> Path:
    return build_rows(tmp, [case_row(r) for r in case["rows"]], case.get("crossref"))
