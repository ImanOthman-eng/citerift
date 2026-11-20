"""Role-collision recall study (owner decision D-083, item 5; reviewer finding B-02): can bibliographic agreement safely
resolve an identifier role collision (D-072, strict)? Written for bib-1 (dt-3); rerun with bib-2 (dt-4, owner
decisions D-086 and D-087), whose verdicts are the ones measured below wherever bib-1 is named.

Read-only and descriptive; it uses no campaign label, adjudication or score (reviewer finding F-08 of the corrective
cycle). Two measurements:

1. ``snapshot``: every key (DOI, PMID) that the pinned Stage 02 snapshot gives in both roles, by kind:

   - ``same_record``: one record gives the key as its original and its notice identifier (Stage 02 flag
     ``NOTICE_<SCHEME>_EQUALS_ORIGINAL``). The lookup of the key holds that one record, and bib-1 compares a citation
     with that record only (spec 2.3), so the verdict is the same whether the citation names the work or its notice:
     bib-1 cannot tell the two roles apart, by construction.
   - ``cross_record``: the key is the original identifier of some records and the notice identifier of others. Each
     (original-role record, notice-role record) pair is compared by bib-1, with the original-role record standing for a
     citation that reproduces it exactly (titles, ``;``-separated authors, journal, year). A pair in MATERIAL_CONFLICT
     is one bib-1 could in principle tell apart; a COMPATIBLE or INSUFFICIENT pair it cannot.

2. ``development``: every candidate of the role-collision rule (dt-2 D-10 with ``IDENTIFIER_ROLE_COLLISION``) in the
   three final-cycle regression files (``../regression/*_REGRESSION.json``: 232 development revisions, 80 and 100
   campaign articles, all design-exposed), with the kind of each of its role-colliding keys and the bib-1 object
   verdicts the regression recorded for its deciding lookup.

Usage: ``uv run python role_collision_study.py INDEX.sqlite OUT.json``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fc_provenance import finish, start

from citerift.investigation import bibliographic as B
from citerift.investigation import dt1
from citerift.retraction.query import Index

HERE = Path(__file__).resolve().parent
REGRESSION = {s: HERE.parent / "regression" / f"{s.upper()}_REGRESSION.json" for s in ("dev", "campaign", "p2")}
SCHEMES = ("doi", "pmid")
CUR = dt1.TABLE_VERSION.replace("-", "")  # the regression's field of the current table
FLAG = {"doi": "NOTICE_DOI_EQUALS_ORIGINAL", "pmid": "NOTICE_PMID_EQUALS_ORIGINAL"}


def as_citation(e: dict[str, Any]) -> B.CitedObject:
    """A citation that reproduces the record exactly."""
    year = e.get("original_year")
    return B.CitedObject.from_json(
        {
            "titles": [e["title"]] if e.get("title") else [],
            "authors": [a.strip() for a in (e.get("authors") or "").split(";") if a.strip()],
            "author_lists": [],
            "vauthors": [],
            "periodical": e.get("journal"),
            "date": None,
            "year": str(year) if isinstance(year, int) else None,
            "volume": None,
            "issue": None,
            "pages": None,
        }
    )  # type: ignore[return-value]


def snapshot(index: Index) -> tuple[dict[str, Any], dict[tuple[str, str], str]]:
    events = [index.event_by_id(r[0]) for r in index.conn.execute("SELECT event_id FROM event ORDER BY event_id")]
    kinds: dict[tuple[str, str], str] = {}
    out: dict[str, Any] = {}
    for scheme in SCHEMES:
        same = {e[f"original_{scheme}"] for e in events if e and FLAG[scheme] in (e.get("flags") or ())}
        orig: dict[str, list[dict[str, Any]]] = defaultdict(list)
        note: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in events:
            if e and e.get(f"original_{scheme}"):
                orig[e[f"original_{scheme}"]].append(e)
            if e and e.get(f"notice_{scheme}"):
                note[e[f"notice_{scheme}"]].append(e)
        cross = set(orig) & set(note)
        pair_verdicts: Counter[str] = Counter()
        key_verdicts: Counter[str] = Counter()
        for k in sorted(cross):
            verdicts = {
                B.compare(as_citation(o), B.RecordObject.from_json(n)).object  # type: ignore[arg-type]
                for o in orig[k]
                for n in note[k]
                if o["event_id"] != n["event_id"]
            }
            pair_verdicts.update(verdicts)
            key_verdicts["every pair MATERIAL_CONFLICT" if verdicts == {B.MATERIAL_CONFLICT} else "some pair not"] += 1
        for k in same:
            kinds[(scheme, k)] = "same_record"
        for k in cross:
            kinds[(scheme, k)] = "same_and_cross_record" if k in same else "cross_record"
        out[scheme] = {
            "same_record_keys": len(same),
            "cross_record_keys": len(cross),
            "cross_record_keys_also_same_record": len(cross & same),
            "cross_record_keys_with_a_pair_of_verdict": dict(sorted(pair_verdicts.items())),
            "cross_record_keys_by_discrimination": dict(sorted(key_verdicts.items())),
        }
    return out, kinds


def development(kinds: dict[tuple[str, str], str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, path in REGRESSION.items():
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc["totals"]["role_collision_candidates"]
        by_kind: Counter[str] = Counter()
        by_verdicts: Counter[str] = Counter()
        dt3: Counter[str] = Counter()
        for c in rows:
            ks = {kinds[(s, k)] for k in c["keys"] for s in SCHEMES if (s, k) in kinds}
            by_kind["+".join(sorted(ks)) or "no key in both roles"] += 1
            verdicts = sorted({b["object"] for b in c.get("bib", [])}) if c["has_description"] else ["NO_DESCRIPTION"]
            by_verdicts["+".join(verdicts) or "NONE"] += 1
            dt3[f"{c[CUR]['rule']} {c[CUR]['class']}"] += 1
        out[name] = {
            "regression_code_commit": doc["provenance"]["code_commit"],
            "role_collision_candidates": len(rows),
            "by_collision_kind": dict(sorted(by_kind.items())),
            "by_bib_object_verdicts": dict(sorted(by_verdicts.items())),
            f"{CUR}_decision": dict(sorted(dt3.items())),
        }
    return out


def main() -> int:
    path, target = Path(sys.argv[1]), Path(sys.argv[2])
    prov = start(Path(__file__), path)
    with Index(path) as index:
        snap, kinds = snapshot(index)
    report: dict[str, Any] = {
        "label": "DEVELOPMENT EVIDENCE ONLY (design-exposed; owner decisions D-071, D-083); no labels",
        "snapshot": snap,
        "development": development(kinds),
        "provenance": prov,
    }
    finish(prov, Path(__file__), path)
    target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "provenance"}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
