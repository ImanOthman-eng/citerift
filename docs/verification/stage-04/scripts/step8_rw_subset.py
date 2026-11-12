"""Write the attributed Retraction Watch subset fixture of Stage 04 Step 8 (owner Step 8 item 10).

Method. The pinned snapshot (receipt ``rw-a987928``) is checked byte for byte. Each vertical-slice bundle named in
SPECIFICATION.md S-7.4 / VS-1..VS-3 (all previously exposed design cases, none a Stage 03 evaluation or holdout
bundle) is extracted offline with the accepted Stage 03 extractor, and its valid DOI and PMID keys are collected.
Every key is queried alone (Q1), and every DOI x PMID pair of one bundle is queried together (Q2, a superset of the
pairs NORMALIZE forms), on an index built from the full snapshot, through the Stage 04 bounded lookup
(``Index.gather_bounded``, 16 MiB). The fixture keeps the Record IDs of every event any of those queries returns
(the bridge closure is the engine's own), with the same selected fields as the Stage 02 fixture; other columns are
left empty. The script then builds an index from the fixture alone and checks that every query gives the same
state, status, value, dates, event identities and record ids as on the full index. Disagreements are written to the
manifest and fail the run. No synthetic row is added.

Run (the CSV is the pinned snapshot; the index is built from it by ``citerift.retraction.store.build``):

    python docs/verification/stage-04/scripts/step8_rw_subset.py --csv retraction_watch.csv --index FULL.sqlite \
      --out-csv tests/stage04/fixtures/step8/rw_subset.csv --out-manifest tests/stage04/fixtures/step8/rw_subset.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from citerift.investigation.lookup import bounded_gather
from citerift.retraction.query import MAX_PAGE, Index, render
from citerift.retraction.source import check_bytes, load_receipt, parse_receipt
from citerift.retraction.store import build
from citerift.wiki.extract import ExtractConfig, extract_bundle

REPO = Path(__file__).resolve().parents[4]
BUNDLES = (
    "tests/stage03/fixtures/observed/ar-76190003",  # VS-2 Obokata ar
    "tests/stage03/fixtures/observed/en-1372543632",  # VS-3 Obokata en
    "docs/verification/stage-03/demonstrations/bundles/en-1381772671",  # VS-1 MMR vaccine (Wakefield)
    "docs/verification/stage-03/demonstrations/bundles/en-1374726997",  # VS-3 GFAJ-1
)
FIXTURE_FIELDS = (
    "Record ID",
    "Title",
    "Journal",
    "Publisher",
    "RetractionDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDate",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
    "RetractionNature",
)
MAX_RECORDS = 120
BUDGET = 16 * 1024 * 1024
ATTRIBUTION = (
    "Retraction Watch data via Crossref (https://gitlab.com/crossref/retraction-watch-data), commit "
    "a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4; selected fields of at most 120 records; other columns left empty. "
    "Cited as the source requests; not a redistribution of the dataset."
)


def bundle_keys(rel: str) -> dict[str, list[str]]:
    doc = extract_bundle(REPO / rel, ExtractConfig(), isolated=True)
    keys: dict[str, set[str]] = {"doi": set(), "pmid": set()}
    for ident in doc["identifiers"]:
        norm = ident["normalization"]
        if norm and norm["valid"] and ident["scheme"] in keys and isinstance(norm.get("normalized"), str):
            keys[ident["scheme"]].add(norm["normalized"])
    return {k: sorted(v) for k, v in keys.items()}


def queries(keys: dict[str, list[str]]) -> list[tuple[str | None, str | None]]:
    out: list[tuple[str | None, str | None]] = [(d, None) for d in keys["doi"]]
    out += [(None, p) for p in keys["pmid"]]
    out += [(d, p) for d in keys["doi"] for p in keys["pmid"]]
    return out


def outcome(index: Index, doi: str | None, pmid: str | None) -> dict[str, Any]:
    """The Stage 02 answer, in the fields the Stage 02 real-case fixture compares, plus the notice hits."""
    out = render(bounded_gather(index, doi, pmid, BUDGET), index.snapshot_id, page_size=MAX_PAGE)
    proj = out["projection"] or {}
    status = proj.get("retraction_status") or {}
    date = proj.get("retraction_date") or {}
    return {
        "state": out["lookup_state"],
        "role": out["identifier_role"],
        "identity": out["identity"]["status"],
        "status": status.get("status"),
        "value": status.get("value"),
        "date_status": date.get("status"),
        "date_value": date.get("value"),
        "events": out["total_event_count"],
        "event_types": sorted(e["event_type"] for e in out["events"]),
        "record_ids": sorted(e["record_id"] for e in out["events"]),
        "notice_hit_record_ids": sorted(_record(index, "event", "event_id", h["event_id"]) for h in out["notice_hits"]),
        "issues": sorted(i["code"] for i in out["issues"]),
        "issue_record_ids": sorted(
            _record(index, "raw_record", "ordinal", i["ordinal"]) for i in out["issues"] if "ordinal" in i
        ),
    }


def _record(index: Index, table: str, column: str, value: Any) -> str:
    """The Record ID of an event or raw record (event ids and ordinals are positions, so they differ in a subset)."""
    row = index.conn.execute(f"SELECT record_id FROM {table} WHERE {column} = ?", (value,)).fetchone()  # noqa: S608
    return str(row[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-manifest", type=Path, required=True)
    args = ap.parse_args()
    receipt = load_receipt()
    check = check_bytes(args.csv, receipt)
    if check.sha256 != receipt.expected_sha256:
        sys.stderr.write("the CSV is not the pinned snapshot\n")
        return 1

    per_bundle = {rel: bundle_keys(rel) for rel in BUNDLES}
    all_queries = sorted(
        {q for keys in per_bundle.values() for q in queries(keys)}, key=lambda q: (str(q[0]), str(q[1]))
    )
    with Index(args.index) as full:
        full_out = {q: outcome(full, *q) for q in all_queries}
    used = sorted(
        {
            int(r)
            for o in full_out.values()
            for r in (*o["record_ids"], *o["notice_hit_record_ids"], *o["issue_record_ids"])
        }
    )
    if len(used) > MAX_RECORDS:
        sys.stderr.write(f"{len(used)} records exceed the {MAX_RECORDS}-record fixture limit\n")
        return 1

    with args.csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader)
        rid = header.index("Record ID")
        rows = {int(r[rid]): r for r in reader if r[rid].isdigit() and int(r[rid]) in set(used)}
    missing = sorted(set(used) - set(rows))
    if missing:
        sys.stderr.write(f"record ids not found in the CSV: {missing[:10]}\n")
        return 1
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for r in used:
        writer.writerow([v if h in FIXTURE_FIELDS else "" for h, v in zip(header, rows[r], strict=True)])
    data = ("﻿" + buf.getvalue()).encode("utf-8")

    fields = receipt.to_json()
    fields.update(
        {
            "path": args.out_csv.name,
            "expected_bytes": len(data),
            "expected_sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest(),
            "attribution": ATTRIBUTION,
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / args.out_csv.name
        sub.write_bytes(data)
        built = build(sub, parse_receipt(fields), Path(tmp) / "index")
        with Index(built.index_path) as small:
            sub_out = {q: outcome(small, *q) for q in all_queries}
    disagree = [
        {"doi": q[0], "pmid": q[1], "full": full_out[q], "subset": sub_out[q]}
        for q in all_queries
        if full_out[q] != sub_out[q]
    ]

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_csv.write_bytes(data)
    found = [q for q in all_queries if full_out[q]["state"] != "no_record"]
    single = [{"doi": q[0], "pmid": q[1], **full_out[q]} for q in found if q[0] is None or q[1] is None]
    pairs = [[q[0], q[1], full_out[q]["state"], full_out[q]["identity"]] for q in found if None not in q]
    states: dict[str, int] = {}
    for q in all_queries:
        states[full_out[q]["state"]] = states.get(full_out[q]["state"], 0) + 1
    manifest = {
        "fixture": args.out_csv.name,
        "fixture_sha256": hashlib.sha256(data).hexdigest(),
        "fixture_bytes": len(data),
        "fixture_records": len(used),
        "fixture_fields": list(FIXTURE_FIELDS),
        "attribution": ATTRIBUTION,
        "source": {
            "repository": receipt.repository,
            "commit": receipt.commit,
            "path": receipt.path,
            "url": receipt.url,
            "sha256": receipt.expected_sha256,
            "bytes": receipt.expected_bytes,
        },
        "synthetic_rows": 0,
        "method": __doc__.split("Run (")[0].strip().replace("\n", " "),
        "bundles": {rel: per_bundle[rel] for rel in BUNDLES},
        "queries": len(all_queries),
        "query_states": dict(sorted(states.items())),
        "q1_with_records": single,
        "q2_with_records": pairs,
        "outcomes_sha256": hashlib.sha256(
            json.dumps([[q, full_out[q]] for q in all_queries], sort_keys=True).encode()
        ).hexdigest(),
        "subset_equals_full_index": not disagree,
        "disagreements": disagree,
    }
    args.out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "utf-8")
    print(
        json.dumps(
            {"records": len(used), "queries": len(all_queries), "with_events": len(found), "disagree": len(disagree)}
        )
    )
    return 1 if disagree else 0


if __name__ == "__main__":
    raise SystemExit(main())
