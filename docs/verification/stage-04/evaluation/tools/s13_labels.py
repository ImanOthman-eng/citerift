"""Stage 04 Step 13: label format, validation, disagreements, final labels and the lock (PREREGISTRATION.md 6, 7).

A label file holds one annotator's labels for the items of some packets. Two independent Claude Sonnet annotators
(``A``, ``B``) label every item; an item on which they differ in any labelled field (``note`` excepted) goes to a third
Claude Sonnet instance (``ADJ``), whose label is final for that item; an agreed label is final as it is. The final
labels and every file they come from are hashed into ``LOCK.json``, which is committed before the prediction run.

Label of one item (all fields required; values are the enumerations below):

- ``kind``: what the unit is;
- ``same_work``: whether the unit's DOI(s) and PMID(s) identify one and the same work;
- ``records``: for every record ref of the item, how the record relates to what the unit cites;
- ``single_identifier_attachable``: whether the citation is unambiguous and attachable to the cited work by one of
  its identifiers alone (D-067);
- ``note``: free text, at most 500 characters, never scored.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s13_common import file_sha256, read_json, write_json

FORMAT = "citerift-stage04-eval-labels/1"
LOCK_FORMAT = "citerift-stage04-eval-lock/1"
ROLES = ("A", "B", "ADJ")
KIND = ("work_citation", "notice_citation", "retraction_marker", "other_mention", "not_a_reference", "cannot_tell")
SAME_WORK = ("yes", "no", "single_identifier", "no_identifier", "cannot_tell")
RECORD = ("cited_work", "cited_notice", "unrelated", "cannot_tell")
ATTACHABLE = ("yes", "no", "cannot_tell")
SCORED = ("kind", "same_work", "records", "single_identifier_attachable")


def label_problems(label: Any, item: dict[str, Any]) -> list[str]:
    """Format problems of one label against its item (the executor checks format only, never content)."""
    out = []
    if not isinstance(label, dict):
        return ["label is not an object"]
    want = {"item_id", "kind", "same_work", "records", "single_identifier_attachable", "note"}
    if set(label) != want:
        out.append(f"fields {sorted(set(label) ^ want)}")
        return out
    for field, allowed in (("kind", KIND), ("same_work", SAME_WORK), ("single_identifier_attachable", ATTACHABLE)):
        if label[field] not in allowed:
            out.append(f"{field} {label[field]!r}")
    refs = {r["ref"] for r in item["records"]}
    recs = label["records"]
    if not isinstance(recs, dict) or set(recs) != refs:
        out.append(f"records must name exactly {sorted(refs)}")
    elif any(v not in RECORD for v in recs.values()):
        out.append("record judgment outside the enumeration")
    if not isinstance(label["note"], str) or len(label["note"]) > 500:
        out.append("note")
    return out


def file_problems(doc: Any, items: dict[str, dict[str, Any]], expected: set[str] | None = None) -> list[str]:
    if not isinstance(doc, dict) or doc.get("format") != FORMAT or doc.get("annotator") not in ROLES:
        return ["not a label file of this format"]
    out = []
    seen = set()
    for label in doc.get("labels") or []:
        iid = label.get("item_id") if isinstance(label, dict) else None
        if iid not in items:
            out.append(f"unknown item {iid!r}")
            continue
        if iid in seen:
            out.append(f"item {iid} labelled twice")
        seen.add(iid)
        out += [f"{iid}: {p}" for p in label_problems(label, items[iid])]
    if expected is not None and seen != expected:
        out.append(f"items missing {sorted(expected - seen)[:5]} or extra {sorted(seen - expected)[:5]}")
    return out


def scored(label: dict[str, Any]) -> dict[str, Any]:
    return {k: label[k] for k in SCORED}


def disagreements(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]) -> list[str]:
    """Item ids on which A and B differ in any scored field."""
    return sorted(i for i in a if scored(a[i]) != scored(b[i]))


def final_labels(
    a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]], adj: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Agreed items keep the agreed label; every disagreed item takes the adjudicator's label (required)."""
    if set(a) != set(b):
        raise ValueError("annotators A and B labelled different items")
    out = {}
    for iid in sorted(a):
        notes = {"A": a[iid]["note"], "B": b[iid]["note"]}
        if scored(a[iid]) == scored(b[iid]):
            out[iid] = {**scored(a[iid]), "source": "agreed", "notes": notes}
        else:
            if iid not in adj:
                raise ValueError(f"disagreed item {iid} has no adjudicated label")
            out[iid] = {**scored(adj[iid]), "source": "adjudicated", "notes": {**notes, "ADJ": adj[iid]["note"]}}
    extra = set(adj) - set(disagreements(a, b))
    if extra:
        raise ValueError(f"adjudicated labels for agreed items: {sorted(extra)[:5]}")
    return out


def by_item(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {lab["item_id"]: lab for lab in doc["labels"]}


def lock(packets: list[Path], a: Path, b: Path, adj: Path, out: Path) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    for p in packets:
        for it in read_json(p)["items"] or []:
            items[it["item_id"]] = it
    docs = {"A": read_json(a), "B": read_json(b), "ADJ": read_json(adj)}
    for role, doc in docs.items():
        if doc.get("annotator") != role:
            raise ValueError(f"{role} file names annotator {doc.get('annotator')!r}")
        expected = set(items) if role != "ADJ" else None
        found = file_problems(doc, items, expected)
        if found:
            raise ValueError(f"{role}: " + "; ".join(found[:5]))
    la, lb, ladj = by_item(docs["A"]), by_item(docs["B"]), by_item(docs["ADJ"])
    dis = disagreements(la, lb)
    if set(ladj) != set(dis):
        raise ValueError("the adjudicated items are not exactly the disagreed items")
    final = final_labels(la, lb, ladj)
    result = {
        "format": LOCK_FORMAT,
        "packets": {p.name: file_sha256(p) for p in packets},
        "label_files": {"A": file_sha256(a), "B": file_sha256(b), "ADJ": file_sha256(adj)},
        "items": len(items),
        "disagreed": len(dis),
        "final": final,
    }
    write_json(out, result)
    return result


def combine(role: str, files: list[Path], out: Path) -> dict[str, Any]:
    """One role file from the label files of that role's instances (each instance labels at most six articles)."""
    labels: list[dict[str, Any]] = []
    instances = []
    for path in files:
        doc = read_json(path)
        if doc.get("format") != FORMAT or doc.get("annotator") != role:
            raise ValueError(f"{path} is not a {role} label file")
        instances.append(
            {
                "file": path.name,
                "sha256": file_sha256(path),
                "instance": doc.get("instance"),
                "model": doc.get("model"),
                "items": len(doc["labels"]),
            }
        )
        labels += doc["labels"]
    ids = [lab["item_id"] for lab in labels]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{role}: an item is labelled by two instances")
    result = {
        "format": FORMAT,
        "annotator": role,
        "instances": instances,
        "labels": sorted(labels, key=lambda lab: lab["item_id"]),
    }
    write_json(out, result)
    return result


def merge(locks: list[Path], out: Path) -> dict[str, Any]:
    """The campaign ``LOCK.json``: the union of the round locks (no item or packet may appear in two rounds)."""
    result: dict[str, Any] = {
        "format": LOCK_FORMAT,
        "rounds": {},
        "packets": {},
        "items": 0,
        "disagreed": 0,
        "final": {},
    }
    for path in locks:
        doc = read_json(path)
        if doc.get("format") != LOCK_FORMAT or "rounds" in doc:
            raise ValueError(f"{path} is not a round lock")
        if set(doc["packets"]) & set(result["packets"]) or set(doc["final"]) & set(result["final"]):
            raise ValueError(f"{path} repeats a packet or an item of another round")
        result["rounds"][path.parent.name] = file_sha256(path)
        result["packets"].update(doc["packets"])
        result["final"].update(doc["final"])
        result["items"] += doc["items"]
        result["disagreed"] += doc["disagreed"]
    write_json(out, result)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 labels")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--packets", type=Path, nargs="+", required=True)
    c.add_argument("--labels", type=Path, required=True)
    d = sub.add_parser("disagreements")
    d.add_argument("--a", type=Path, required=True)
    d.add_argument("--b", type=Path, required=True)
    k = sub.add_parser("lock")
    k.add_argument("--packets", type=Path, nargs="+", required=True)
    k.add_argument("--a", type=Path, required=True)
    k.add_argument("--b", type=Path, required=True)
    k.add_argument("--adj", type=Path, required=True)
    k.add_argument("--out", type=Path, required=True)
    cb = sub.add_parser("combine")
    cb.add_argument("--role", choices=ROLES, required=True)
    cb.add_argument("--files", type=Path, nargs="+", required=True)
    cb.add_argument("--out", type=Path, required=True)
    m = sub.add_parser("merge")
    m.add_argument("--locks", type=Path, nargs="+", required=True)
    m.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "combine":
        res = combine(args.role, args.files, args.out)
        print(len(res["labels"]), "labels from", len(res["instances"]), "instances")
        return 0
    if args.cmd == "merge":
        res = merge(args.locks, args.out)
        print(res["items"], "items in", len(res["rounds"]), "rounds")
        return 0
    if args.cmd == "check":
        items = {it["item_id"]: it for p in args.packets for it in (read_json(p)["items"] or [])}
        found = file_problems(read_json(args.labels), items)
        print("\n".join(found) or "format ok")
        return 1 if found else 0
    if args.cmd == "disagreements":
        for iid in disagreements(by_item(read_json(args.a)), by_item(read_json(args.b))):
            print(iid)
        return 0
    res = lock(args.packets, args.a, args.b, args.adj, args.out)
    print(res["items"], "items,", res["disagreed"], "adjudicated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
