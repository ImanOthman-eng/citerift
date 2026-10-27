"""Compare a clean-cache reproduction (clean_reproduction.sh) with the committed Stage 01 data.

Retrieval timestamps are expected to differ. Wikipedia observations are of each article's latest revision, so a
different revision id is reported as such, and the citation and marking are compared at both revisions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data"
POS = "10.1038/nature12968"
NEG = "10.1038/171737a0"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def by_doi(path: Path, doi: str) -> dict[str, Any]:
    return next(r for r in load(path)["results"] if r["doi"] == doi)


def lookup_view(r: dict[str, Any]) -> dict[str, Any]:
    cr = r["crossref_original"] or {}
    return {
        "retraction_watch": r["retraction_watch"],
        "retraction_watch_records_naming_it_as_notice": r["retraction_watch_records_naming_it_as_notice"],
        "crossref_status": cr.get("status"),
        "crossref_title": cr.get("title"),
        "crossref_updated_by": sorted(
            (u["DOI"].lower(), u["type"], u.get("source", "")) for u in cr.get("updated_by") or []
        ),
        "crossref_notice_dois": sorted(n["doi"].lower() for n in r["crossref_notices"]),
    }


def discovery_view(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "complete": r["complete"],
        "observations": {
            o["title"]: {"confirmed": o["confirmed"], "marked": o.get("marked"), "revid": o.get("revid")}
            for o in r["observations"]
        },
    }


def compare(name: str, committed: Any, clean: Any, checks: list[dict[str, Any]]) -> None:
    checks.append({"check": name, "match": committed == clean, "committed": committed, "clean": clean})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    checks: list[dict[str, Any]] = []
    for case, doi, committed_file, clean_file in (
        ("POS-02", POS, DATA / "purposive_lookup.json", a.work / "pos_lookup.json"),
        ("NC-03", NEG, DATA / "followups/nc3_lookup.json", a.work / "neg_lookup.json"),
    ):
        compare(
            f"{case} lookup", lookup_view(by_doi(committed_file, doi)), lookup_view(by_doi(clean_file, doi)), checks
        )
    clean_disc = load(a.work / "pos_discovery.json")
    for wiki in ("en", "ar"):
        committed = discovery_view(
            next(r for r in load(DATA / "purposive_discovery.json")["results"] if r["doi"] == POS and r["wiki"] == wiki)
        )
        clean = discovery_view(next(r for r in clean_disc["results"] if r["wiki"] == wiki))
        compare(f"POS-02 discovery {wiki}: complete", committed["complete"], clean["complete"], checks)
        compare(
            f"POS-02 discovery {wiki}: citing titles",
            sorted(committed["observations"]),
            sorted(clean["observations"]),
            checks,
        )
        for title in sorted(set(committed["observations"]) & set(clean["observations"])):
            c, n = committed["observations"][title], clean["observations"][title]
            compare(
                f"POS-02 {wiki} {title}: confirmed and marked",
                [c["confirmed"], c["marked"]],
                [n["confirmed"], n["marked"]],
                checks,
            )
            checks.append(
                {
                    "check": f"POS-02 {wiki} {title}: revision",
                    "same_revision": c["revid"] == n["revid"],
                    "committed": c["revid"],
                    "clean": n["revid"],
                }
            )
    requests = clean_disc["request_log"]
    result = {
        "run_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": {"positive": f"POS-02 ({POS})", "negative": f"NC-03 ({NEG})"},
        "cache": "empty at start (clean_reproduction.sh refuses a non-empty work directory)",
        "discovery_requests": len(requests),
        "discovery_requests_from_cache": sum(1 for r in requests if r["cached"]),
        "checks": checks,
        "mismatches": [c["check"] for c in checks if c.get("match") is False],
        "revisions_changed": [c["check"] for c in checks if c.get("same_revision") is False],
    }
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: result[k] for k in ("discovery_requests", "mismatches", "revisions_changed")}, ensure_ascii=False
        )
    )
    return 1 if result["mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
