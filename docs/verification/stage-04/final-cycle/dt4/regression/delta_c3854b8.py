"""Revised freeze-3 (owner decisions D-086 and D-087): every claim the dt-4 engine decides differently from the
freeze-3 candidate c3854b8 (dt-3), over the three regression sets (232 development revisions, the 80 articles of the
failed historical campaign and the 100 P2 campaign articles).

Inputs: the committed regressions of c3854b8 (``../../regression/{DEV,CAMPAIGN,P2}_REGRESSION.json``, the record of
that candidate) and of this engine (``{DEV,CAMPAIGN,P2}_REGRESSION.json`` here). Each lists only the claims that differ
from the accepted dt-2 engine, so a claim not listed in a file decides as dt-2 there. A claim is keyed by its revision,
unit and candidate keys; its dt-3 decision is the old file's ``dt3`` when listed, else its ``dt2``; its dt-4 decision is
the new file's ``dt4`` when listed, else its ``dt2``. Reported: every key whose dt-3 and dt-4 decisions differ, by
transition, and the owner's required outcomes (D-087): no new positive (a dt-4 positive where dt-3 had none) and so no
restored false attachment (a dt-3 D-13a block that dt-4 lifts), and no silent D-14 (a dt-4 positive on a pair bib-2
judges MATERIAL_CONFLICT, NOT_ESTABLISHED or UNAVAILABLE).

The regressions never join campaign labels (F-08); neither does this script.

Usage: ``uv run python delta_c3854b8.py [--out DELTA_C3854B8.json]`` (provenance of ``fc_provenance``).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / "regression"
sys.path.insert(0, str(HERE.parents[1]))

from fc_provenance import finish, start  # noqa: E402

SETS = {"dev": "DEV_REGRESSION.json", "campaign": "CAMPAIGN_REGRESSION.json", "p2": "P2_REGRESSION.json"}
POSITIVE = {"D-14"}
BLOCKING_BIB = {"MATERIAL_CONFLICT", "NOT_ESTABLISHED", "UNAVAILABLE"}


def _changed(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for rev, r in sorted(doc["revisions"].items()):
        for c in r.get("changed", []):
            out.append({**c, "revision": c.get("revision", rev)})
    return out


def _key(c: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    return (c["revision"], c["unit_id"], tuple(c["keys"]))


def _decision(d: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    return (d["rule"], d["class"], tuple(d["reasons"]))


def delta(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if old["index_sha256"] != new["index_sha256"]:
        raise SystemExit("the two regressions read different Stage 02 indexes")
    if set(old["revisions"]) != set(new["revisions"]):
        raise SystemExit("the two regressions cover different revisions")
    o = {_key(c): c for c in _changed(old)}
    n = {_key(c): c for c in _changed(new)}
    rows, transitions = [], Counter()
    for k in sorted(set(o) | set(n)):
        dt2 = (o.get(k) or n[k])["dt2"]
        if k in o and k in n and _decision(o[k]["dt2"]) != _decision(n[k]["dt2"]):
            raise SystemExit(f"{k}: the dt-2 decisions of the two regressions differ")
        dt3 = o[k]["dt3"] if k in o else dt2
        dt4 = n[k]["dt4"] if k in n else dt2
        if _decision(dt3) == _decision(dt4):
            continue
        bib = n[k].get("bib", []) if k in n else []
        unavailable = n[k].get("unavailable") if k in n else None
        row = {
            "revision": k[0],
            "unit_id": k[1],
            "keys": list(k[2]),
            "dt2": dt2,
            "dt3": dt3,
            "dt4": dt4,
            "dt3_bib": o[k].get("bib", []) if k in o else [],
            "dt4_bib": bib,
            "dt4_unavailable": unavailable,
        }
        rows.append(row)
        transitions[f"{dt3['rule']} {dt3['class']} -> {dt4['rule']} {dt4['class']}"] += 1
    new_positive = [r for r in rows if r["dt4"]["rule"] in POSITIVE and r["dt3"]["rule"] not in POSITIVE]
    lifted = [r for r in rows if r["dt3"]["rule"] == "D-13a" and r["dt4"]["rule"] in POSITIVE]
    silent = [
        r
        for r in rows
        if r["dt4"]["rule"] in POSITIVE
        and (r["dt4_unavailable"] or any(b.get("object") in BLOCKING_BIB for b in r["dt4_bib"]))
    ]
    return {
        "rows": rows,
        "changed": len(rows),
        "by_transition": dict(sorted(transitions.items())),
        "new_positive_vs_c3854b8": len(new_positive),
        "restored_false_attachment": len(lifted),
        "silent_d14": len(silent),
        "positive_units": {
            "dt3": old["totals"]["positive_units"].get("dt3"),
            "dt4": new["totals"]["positive_units"].get("dt4"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "DELTA_C3854B8.json")
    args = ap.parse_args()
    prov = start(Path(__file__))
    result: dict[str, Any] = {"decision": "D-086 and D-087 (revised freeze-3): dt-4 against the c3854b8 candidate"}
    for name, file in SETS.items():
        old = json.loads((OLD / file).read_text(encoding="utf-8"))
        new = json.loads((HERE / file).read_text(encoding="utf-8"))
        if old.get("table_version") != "dt-3" or new.get("table_version") != "dt-4":
            raise SystemExit(f"{name}: expected dt-3 and dt-4 regressions")
        result[name] = delta(old, new)
    result["required"] = {
        "no_new_positive": all(result[s]["new_positive_vs_c3854b8"] == 0 for s in SETS),
        "no_restored_false_attachment": all(result[s]["restored_false_attachment"] == 0 for s in SETS),
        "no_silent_d14": all(result[s]["silent_d14"] == 0 for s in SETS),
    }
    finish(prov, Path(__file__))
    result["provenance"] = prov
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({s: {k: result[s][k] for k in result[s] if k != "rows"} for s in SETS}, indent=1))
    print(json.dumps(result["required"]))


if __name__ == "__main__":
    main()
