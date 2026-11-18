"""Write the attributed Retraction Watch subset fixture of the role-collision suite (corrective cycle, D-071 item 7).

Method. The pinned snapshot is checked byte for byte. Keys are selected from an index built from the full snapshot,
one or two per class of the adversarial list of D-071 section 7, each the **first** of its class in a fixed order
(the smallest key, or, for a class defined on events, the event with the smallest event id; reviewer finding D-04). A
class is defined by Stage 02 flags, roles and states only; never by a label, a title, a journal or an outcome of the
engine. Also selected: the failed-campaign key ``10.1002/asi.23238`` by name and every key of the exposed
campaign bundle ``en-39868218`` (both design-exposed after D-071). Every key is queried alone (Q1) and the listed pairs
together (Q2) through the Stage 04 bounded lookup; the fixture keeps the Record IDs of every event and notice hit those
queries return, with the selected fields of the Step 8 fixture. An index built from the fixture alone must give the
same state, status, value, dates, record ids, notice hits and same-record collision flags for every query;
disagreements fail the run. No synthetic row is added.

Run:

    python docs/verification/stage-04/corrective/scripts/role_collision_fixture.py --csv retraction_watch.csv \
      --index FULL.sqlite --out-dir tests/stage04/fixtures/corrective
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "docs/verification/stage-04/scripts"))

import step8_rw_subset as S8  # noqa: E402

from citerift.retraction.query import Index  # noqa: E402
from citerift.retraction.source import check_bytes, load_receipt, parse_receipt  # noqa: E402
from citerift.retraction.store import build  # noqa: E402

JASIST = "10.1002/asi.23238"
CAMPAIGN_BUNDLE = "docs/verification/stage-04/evaluation-campaign/bundles/en-39868218"
MAX_RECORDS = 120  # the Stage 02 limit for committed fixtures (Stage 02 SPECIFICATION; reviewer finding D-01)
SAME = {"doi": "NOTICE_DOI_EQUALS_ORIGINAL", "pmid": "NOTICE_PMID_EQUALS_ORIGINAL"}
ATTRIBUTION = (
    "Retraction Watch data via Crossref (https://gitlab.com/crossref/retraction-watch-data), commit "
    "a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4; selected fields of at most 120 records; other columns left empty. "
    "Cited as the source requests; not a redistribution of the dataset."
)


def _events(path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out = []
    for r in con.execute("SELECT * FROM event ORDER BY event_id"):
        e = dict(r)
        e["flags"] = json.loads(e["flags"])
        out.append(e)
    con.close()
    return out


def _first(keys: Any) -> str:
    vals = sorted(k for k in keys if k)
    if not vals:
        raise SystemExit("an adversarial class has no key in the snapshot")
    return vals[0]


def select(events: list[dict[str, Any]], index: Index) -> dict[str, dict[str, Any]]:
    """One query per class: {class: {"doi": ..., "pmid": ...}} (first in sorted order within the class)."""
    notice_of: dict[str, set[str]] = {"doi": set(), "pmid": set()}
    original_of: dict[str, set[str]] = {"doi": set(), "pmid": set()}
    for e in events:
        for s in ("doi", "pmid"):
            if e[f"notice_{s}"]:
                notice_of[s].add(e[f"notice_{s}"])
            if e[f"original_{s}"]:
                original_of[s].add(e[f"original_{s}"])
    same = {s: {e[f"original_{s}"] for e in events if SAME[s] in e["flags"]} for s in ("doi", "pmid")}
    cross = {s: original_of[s] & notice_of[s] for s in ("doi", "pmid")}

    def same_doi(etype: str) -> str:
        return _first(
            e["original_doi"]
            for e in events
            if SAME["doi"] in e["flags"] and e["event_type"] == etype and e["original_doi"] not in cross["doi"]
        )

    def second_clean(e: dict[str, Any], collided: str, second: str) -> bool:
        """``e`` collides in scheme ``collided``; its original identifier of scheme ``second`` is cited cleanly."""
        return (
            SAME[collided] in e["flags"]
            and SAME[second] not in e["flags"]
            and bool(e[f"original_{second}"])
            and e[f"original_{second}"] not in notice_of[second]
            and e[f"original_{second}"] not in same[second]
            and e[f"original_{collided}"] not in cross[collided]
        )

    clean_pmid_same_doi = [e for e in events if second_clean(e, "doi", "pmid") and not e["notice_pmid"]]
    discr_pmid_same_doi = [e for e in events if second_clean(e, "doi", "pmid") and e["notice_pmid"]]
    clean_doi_same_pmid = [e for e in events if second_clean(e, "pmid", "doi") and not e["notice_doi"]]
    discr_doi_same_pmid = [e for e in events if second_clean(e, "pmid", "doi") and e["notice_doi"]]
    # A cited DOI+PMID pair naming one work whose DOI one record gives both roles and whose PMID another record gives
    # both roles (no single event carries both flags): reviewer finding B-01.
    split_pairs = sorted(
        (e["original_doi"], e["original_pmid"])
        for e in events
        if e["original_doi"] in same["doi"]
        and e["original_pmid"] in same["pmid"]
        and not (SAME["doi"] in e["flags"] and SAME["pmid"] in e["flags"])
    )
    both_equal = [e for e in events if SAME["doi"] in e["flags"] and SAME["pmid"] in e["flags"]]
    no_notice = [e for e in events if "NO_NOTICE_IDENTIFIER" in e["flags"] and e["original_doi"]]
    no_original = [e for e in events if "ORIGINAL_ANCHOR_SOURCE_RECORD_ONLY" in e["flags"] and e["notice_doi"]]
    plain = [
        e
        for e in events
        if e["event_type"] == "retracted"
        and e["original_doi"]
        and e["notice_doi"]
        and not e["flags"]
        and e["original_doi"] not in cross["doi"]
    ]
    doi_notice_pmid = [
        e
        for e in events
        if e["original_doi"]
        and e["notice_pmid"]
        and not e["original_pmid"]
        and not e["flags"]
        and e["original_doi"] not in cross["doi"]
    ]
    conflicting = sorted(
        d
        for d in {e["original_doi"] for e in events if e["original_doi"]}
        if len({x["event_type"] for x in events if x["original_doi"] == d}) > 1
    )
    conf_key = next(d for d in conflicting if S8.outcome(index, d, None)["status"] == "conflicting")

    def pick(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return min(rows, key=lambda e: e["event_id"])

    cp = pick(clean_pmid_same_doi)
    dp = pick(discr_pmid_same_doi)
    cd = pick(clean_doi_same_pmid)
    dd = pick(discr_doi_same_pmid)
    be = pick(both_equal)
    dn = pick(doi_notice_pmid)
    return {
        "jasist_failure": {"doi": JASIST, "pmid": None},
        "same_doi_retracted": {"doi": same_doi("retracted"), "pmid": None},
        "same_doi_correction": {"doi": same_doi("correction"), "pmid": None},
        "same_doi_expression_of_concern": {"doi": same_doi("expression_of_concern"), "pmid": None},
        "same_doi_reinstated": {"doi": same_doi("reinstated"), "pmid": None},
        "same_pmid": {"doi": None, "pmid": _first(same["pmid"] - cross["pmid"])},
        "cross_record_doi": {"doi": _first(cross["doi"] - same["doi"]), "pmid": None},
        "cross_record_pmid": {"doi": None, "pmid": _first(cross["pmid"] - same["pmid"])},
        "same_doi_with_clean_pmid_pair": {"doi": cp["original_doi"], "pmid": cp["original_pmid"]},
        "same_doi_with_clean_pmid_doi_only": {"doi": cp["original_doi"], "pmid": None},
        "same_doi_with_discriminating_pmid_pair": {"doi": dp["original_doi"], "pmid": dp["original_pmid"]},
        "same_pmid_with_clean_doi_pair": {"doi": cd["original_doi"], "pmid": cd["original_pmid"]},
        "same_pmid_with_discriminating_doi_pair": {"doi": dd["original_doi"], "pmid": dd["original_pmid"]},
        "doi_and_pmid_collided_in_two_records_pair": {"doi": split_pairs[0][0], "pmid": split_pairs[0][1]},
        "both_schemes_equal_pair": {"doi": be["original_doi"], "pmid": be["original_pmid"]},
        "no_notice_identifier": {"doi": pick(no_notice)["original_doi"], "pmid": None},
        "no_original_identifier_notice_doi": {"doi": pick(no_original)["notice_doi"], "pmid": None},
        "original_with_distinct_notice_doi": {"doi": pick(plain)["original_doi"], "pmid": None},
        "original_with_distinct_notice_doi_notice_side": {"doi": pick(plain)["notice_doi"], "pmid": None},
        "doi_original_pmid_notice_pair": {"doi": dn["original_doi"], "pmid": dn["notice_pmid"]},
        "contradictory_source_rows": {"doi": conf_key, "pmid": None},
    }


def outcome(index: Index, doi: str | None, pmid: str | None) -> dict[str, Any]:
    out = S8.outcome(index, doi, pmid)
    from citerift.investigation.lookup import bounded_gather  # noqa: PLC0415 - as in the Step 8 fixture tool

    ev = bounded_gather(index, doi, pmid, S8.BUDGET)
    out["collision_flags"] = sorted(
        {
            f"{S8._record(index, 'event', 'event_id', e['event_id'])}:{f}"
            for e in ev.events
            for f in e["flags"]
            if f in SAME.values()
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    receipt = load_receipt()
    if check_bytes(args.csv, receipt).sha256 != receipt.expected_sha256:
        sys.stderr.write("the CSV is not the pinned snapshot\n")
        return 1
    con = sqlite3.connect(f"file:{args.index}?mode=ro", uri=True)
    source = dict(con.execute("SELECT key, value FROM meta").fetchall()).get("source_sha256")
    con.close()
    if source != receipt.expected_sha256:  # reviewer finding E-11: the index must be built from the pinned snapshot
        sys.stderr.write("the index was not built from the pinned snapshot\n")
        return 1
    with Index(args.index) as full:
        classes = select(_events(args.index), full)
        bundle = S8.bundle_keys(CAMPAIGN_BUNDLE)
        qs = {(q["doi"], q["pmid"]) for q in classes.values()} | set(S8.queries(bundle))
        all_queries = sorted(qs, key=lambda q: (str(q[0]), str(q[1])))
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
        wanted = set(used)
        rows = {int(r[rid]): r for r in reader if r[rid].isdigit() and int(r[rid]) in wanted}
    if set(used) - set(rows):
        sys.stderr.write("record ids not found in the CSV\n")
        return 1
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for r in used:
        writer.writerow([v if h in S8.FIXTURE_FIELDS else "" for h, v in zip(header, rows[r], strict=True)])
    data = ("﻿" + buf.getvalue()).encode("utf-8")
    fields = receipt.to_json()
    fields.update(
        {
            "path": "rw_role_collision.csv",
            "expected_bytes": len(data),
            "expected_sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest(),
            "attribution": ATTRIBUTION,
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / "rw_role_collision.csv"
        sub.write_bytes(data)
        built = build(sub, parse_receipt(fields), Path(tmp) / "index")
        with Index(built.index_path) as small:
            sub_out = {q: outcome(small, *q) for q in all_queries}
    disagree = [{"doi": q[0], "pmid": q[1]} for q in all_queries if full_out[q] != sub_out[q]]
    if disagree:
        sys.stderr.write(f"the subset index disagrees with the full index on {disagree[:3]}; nothing written\n")
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "rw_role_collision.csv").write_bytes(data)
    manifest = {
        "fixture": "rw_role_collision.csv",
        "fixture_sha256": hashlib.sha256(data).hexdigest(),
        "fixture_bytes": len(data),
        "fixture_records": len(used),
        "fixture_fields": list(S8.FIXTURE_FIELDS),
        "attribution": ATTRIBUTION,
        "source": {
            "bytes": receipt.expected_bytes,
            "commit": receipt.commit,
            "path": receipt.path,
            "repository": receipt.repository,
            "sha256": receipt.expected_sha256,
            "url": receipt.url,
        },
        "selection_index": {"source_sha256": source, "note": "an index built by Stage 02 from the pinned snapshot"},
        "outcomes_sha256": hashlib.sha256(
            json.dumps([[q[0], q[1], full_out[q]] for q in all_queries], sort_keys=True).encode()
        ).hexdigest(),
        "synthetic_rows": 0,
        "method": __doc__.split("Run:")[0].strip().replace("\n", " "),
        "classes": classes,
        "campaign_bundle": {CAMPAIGN_BUNDLE: bundle},
        "queries": len(all_queries),
        "outcomes": [
            {"doi": q[0], "pmid": q[1], **full_out[q]} for q in all_queries if full_out[q]["state"] != "no_record"
        ],
        "subset_equals_full_index": not disagree,
        "disagreements": disagree,
    }
    (args.out_dir / "rw_role_collision.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: manifest[k] for k in ("fixture_records", "queries", "subset_equals_full_index")}))
    print(json.dumps(classes, indent=1))
    return 0 if not disagree else 1


if __name__ == "__main__":
    sys.exit(main())
