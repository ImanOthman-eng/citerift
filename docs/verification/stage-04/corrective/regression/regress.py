"""Corrective cycle (owner decision D-071 section 8): every changed claim of dt-2 against the frozen dt-1 engine.

DEVELOPMENT AND REGRESSION EVIDENCE ONLY. Two design-exposed sets:

- ``dev``: the 232 development revisions of Step 13 (``evaluation/dev/DEV_RUN.json``, its bundles);
- ``campaign``: the 80 articles of the failed campaign (``evaluation-campaign/bundles``), development evidence after
  D-071; never counted as unseen again. Nothing in the campaign directory is written or changed.

Each revision runs one investigation offline through the production plan with the corrected engine (in this process,
every socket refused; Investigation Memory in a temporary directory outside the repository). For every work candidate
the recorded dt-2 claim is compared with the frozen dt-1 decision of the **same committed inputs** (the committed
candidate inputs and lookup observations, decided by the frozen ``dt1.py`` of ``b5bf8ed``, read from git and loaded
as an isolated module). LOOKUP, NORMALIZE and EXTRACT are unchanged by the correction, so the inputs are those the
frozen engine saw; the cross-checks below confirm it:

- ``dev``: the per-revision class counts of dt-1 re-decided here equal those of ``DEV_RUN.json`` (frozen run);
- ``campaign``: every claim of the 79 historical exports (cand_ref, class, rule, reasons) equals the dt-1 decision
  re-decided here, and the article without an export matches its ``RUN.json`` class counts.

Run (three shards in parallel, then merge)::

    uv run python -P R/regress.py run --set dev --index I --shard 0/3 --out part0.json   # 1/3, 2/3
    uv run python -P R/regress.py merge --set dev --parts part*.json --out DEV_REGRESSION.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
TOOLS = REPO / "docs/verification/stage-04/evaluation/tools"
CAMPAIGN = REPO / "docs/verification/stage-04/evaluation-campaign"
FROZEN = "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "tests" / "stage04"))
sys.path.insert(0, str(REPO / "docs/verification/stage-04/corrective"))

import frozen_dt1 as F1  # noqa: E402
import pytest  # noqa: E402
import s13_score as SC  # noqa: E402
import step8_support as S8  # noqa: E402
from s13_common import file_sha256, read_json, write_json  # noqa: E402

from citerift.investigation import __version__ as ENGINE_VERSION  # noqa: E402
from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.detector import candidate_view, lookup_roles, lookup_view  # noqa: E402
from citerift.investigation.adapters.plan import Integration  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402

POSITIVE = ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")


def decision(out: Any) -> dict[str, Any]:
    return {"rule": out.rule, "class": out.cls or out.failure, "reasons": list(out.reasons)}


def one(tmp: Path, bundle: Path, index: Path) -> dict[str, Any]:
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(bundle, index, root))
    result = S8.run(root, payload, Integration())
    row: dict[str, Any] = {"lifecycle": result.status}
    recs, blobs = S8.committed(root, payload)
    checks = [r["payload"] for r in recs if r["kind"] == "verification_recorded"]
    row["verified"] = bool(checks) and all(c["passed"] for c in checks[-1]["checks"])
    claims = {r["payload"]["cand_ref"]: r["payload"] for r in recs if r["kind"] == "claim_recorded"}
    inputs = next(
        (b for b in blobs.values() if isinstance(b, dict) and str(b.get("schema", "")).endswith(":candidate-inputs")),
        None,
    )
    plan = next(
        (b for b in blobs.values() if isinstance(b, dict) and str(b.get("schema", "")).endswith(":lookup-plan")), None
    )
    if inputs is None or plan is None:
        row["candidates"] = 0
        return row
    obs_of = {canon(e["query"]).decode(): e["observation"] for e in plan["lookups"]}
    units = {u["unit_id"]: u for u in inputs["units"]}
    cands: list[dict[str, Any]] = []
    for cand in inputs["candidates"]:
        views = {q: lookup_view(blobs[obs_of[q]]) for _, q in lookup_roles(cand)}
        view = candidate_view(cand, units[cand["unit_id"]], views)
        new, old = decision(dt1.decide(view)), decision(F1.decide(view))
        claim = claims.get(cand["cand_ref"])
        recorded = {"rule": claim["rule"], "class": claim["class"], "reasons": claim["reasons"]} if claim else None
        cands.append(
            {
                "cand_ref": cand["cand_ref"],
                "unit_id": cand["unit_id"],
                "keys": [k["normalized"] for k in cand["keys"]],
                "dt2": new,
                "dt1": old,
                "recorded_equals_dt2": recorded == new,
                "role_ambiguous_events": list(dt1.role_ambiguous(view)),
            }
        )
    row["candidates"] = len(cands)
    row["recorded_equals_dt2"] = all(c["recorded_equals_dt2"] for c in cands)
    row["dt1_classes"] = dict(Counter(c["dt1"]["class"] for c in cands))
    row["dt2_classes"] = dict(Counter(c["dt2"]["class"] for c in cands))
    row["changed"] = [c for c in cands if c["dt1"] != c["dt2"]]
    row["all_candidates"] = cands
    return row


def dev_bundles() -> list[tuple[str, Path]]:
    dev = read_json(REPO / "docs/verification/stage-04/evaluation/dev/DEV_RUN.json")["revisions"]
    return [(name, REPO / r["bundle"]) for name, r in sorted(dev.items())]


def campaign_bundles() -> list[tuple[str, Path]]:
    return [(p.name, p) for p in sorted((CAMPAIGN / "bundles").iterdir()) if p.is_dir()]


def bundles_of(which: str) -> list[tuple[str, Path]]:
    return dev_bundles() if which == "dev" else campaign_bundles()


def run_shard(which: str, index: Path, shard: int, shards: int) -> dict[str, Any]:
    out: dict[str, Any] = {"set": which, "shard": [shard, shards], "revisions": {}}
    rows = [r for i, r in enumerate(bundles_of(which)) if i % shards == shard]
    with tempfile.TemporaryDirectory() as d, pytest.MonkeyPatch.context() as mp:
        offline = S8.NoNetwork(mp)
        for i, (name, bundle) in enumerate(rows):
            t0 = time.perf_counter()
            row = {"bundle": str(bundle.relative_to(REPO))}
            row.update(one(Path(d) / str(i), bundle, index))
            row["seconds"] = round(time.perf_counter() - t0, 2)
            out["revisions"][name] = row
            print(shard, i, name, row["lifecycle"], len(row.get("changed", [])), flush=True)
        out["network_attempts"] = len(offline.attempts)
    return out


def cross_check_dev(revisions: dict[str, Any]) -> dict[str, Any]:
    """dt-1 re-decided here against the frozen DEV_RUN.json, per revision (class counts of unit class sets)."""
    dev = read_json(REPO / "docs/verification/stage-04/evaluation/dev/DEV_RUN.json")["revisions"]
    mismatched = []
    for name, row in revisions.items():
        units: dict[str, set[str]] = {}
        for c in row.get("all_candidates", []):
            units.setdefault(c["unit_id"], set()).add(c["dt1"]["class"])
        mine = dict(Counter("+".join(sorted(v)) for v in units.values()))
        theirs = dev[name].get("engine_unit_classes")
        if theirs is not None and mine != theirs:
            mismatched.append({"revision": name, "redecided_dt1": mine, "DEV_RUN": theirs})
        if dev[name]["lifecycle"] != row["lifecycle"]:
            mismatched.append({"revision": name, "lifecycle": [dev[name]["lifecycle"], row["lifecycle"]]})
    return {"revisions": len(revisions), "mismatched": mismatched}


def cross_check_campaign(revisions: dict[str, Any], exports: Path) -> dict[str, Any]:
    """dt-1 re-decided here against the historical run: every claim of each historical export; RUN.json counts for an
    article without an export. ``exports`` is the historical ``run/exports`` (read-only)."""
    run = {a["article"]: a for a in read_json(CAMPAIGN / "run" / "RUN.json")["articles"]}
    mismatched, claims_checked = [], 0
    for name, row in revisions.items():
        mine = {c["cand_ref"]: c["dt1"] for c in row.get("all_candidates", [])}
        ex = exports / name
        if (ex / "export.json").is_file():
            _, items, _ = SC.export_claims(ex)
            for it in items:
                cl = it["claim"]
                claims_checked += 1
                want = {"rule": cl["rule"], "class": cl["class"], "reasons": cl["reasons"]}
                if mine.get(cl["cand_ref"]) != want:
                    mismatched.append(
                        {
                            "article": name,
                            "cand_ref": cl["cand_ref"],
                            "historical": want,
                            "redecided": mine.get(cl["cand_ref"]),
                        }
                    )
            if len(items) != len(mine):
                mismatched.append({"article": name, "historical_claims": len(items), "redecided": len(mine)})
        else:
            counts = dict(Counter(c["class"] for c in mine.values()))
            if counts != run[name]["claims_by_class"]:
                mismatched.append({"article": name, "RUN.json": run[name]["claims_by_class"], "redecided": counts})
    return {"articles": len(revisions), "claims_checked": claims_checked, "mismatched": mismatched}


def totals(revisions: dict[str, Any]) -> dict[str, Any]:
    changed = [dict(c, revision=n) for n, r in revisions.items() for c in r.get("changed", [])]
    unit_pos = {"dt1": 0, "dt2": 0}
    for r in revisions.values():
        for k in ("dt1", "dt2"):
            units: dict[str, set[str]] = {}
            for c in r.get("all_candidates", []):
                units.setdefault(c["unit_id"], set()).add(c[k]["class"])
            unit_pos[k] += sum(1 for v in units.values() if v & set(POSITIVE))
    return {
        "revisions": len(revisions),
        "lifecycle": dict(Counter(r["lifecycle"] for r in revisions.values())),
        "verified": sum(1 for r in revisions.values() if r.get("verified")),
        "candidates": sum(r.get("candidates", 0) for r in revisions.values()),
        "recorded_equals_dt2_everywhere": all(r.get("recorded_equals_dt2", True) for r in revisions.values()),
        "changed_claims": len(changed),
        "changed_by_transition": dict(
            Counter(
                f"{c['dt1']['rule']} {c['dt1']['class']} -> {c['dt2']['rule']} {c['dt2']['class']}" for c in changed
            )
        ),
        "changed_reasons_only": sum(1 for c in changed if c["dt1"]["class"] == c["dt2"]["class"]),
        "new_not_found": sum(1 for c in changed if c["dt2"]["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"),
        "new_positive": sum(1 for c in changed if c["dt2"]["class"] in POSITIVE),
        "lost_positive": sum(1 for c in changed if c["dt1"]["class"] in POSITIVE and c["dt2"]["class"] not in POSITIVE),
        "new_notice_cited": sum(1 for c in changed if c["dt2"]["class"] == "NOTICE_CITED"),
        "positive_units": unit_pos,
        "changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="corrective-cycle regression: dt-2 against the frozen dt-1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", choices=("dev", "campaign"), required=True)
    r.add_argument("--index", type=Path, required=True)
    r.add_argument("--shard", required=True)
    r.add_argument("--out", type=Path, required=True)
    m = sub.add_parser("merge")
    m.add_argument("--set", choices=("dev", "campaign"), required=True)
    m.add_argument("--index", type=Path, required=True)
    m.add_argument("--parts", type=Path, nargs="+", required=True)
    m.add_argument("--historical-exports", type=Path, help="campaign: the historical run/exports (read-only)")
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        k, n = (int(x) for x in a.shard.split("/"))
        t0 = time.perf_counter()
        part = run_shard(a.set, a.index.resolve(), k, n)
        part["seconds"] = round(time.perf_counter() - t0, 1)
        write_json(a.out, part)
        return 0
    parts = [read_json(p) for p in a.parts]
    revisions = {k: v for p in parts for k, v in p["revisions"].items()}
    if sorted(revisions) != sorted(n for n, _ in bundles_of(a.set)):
        sys.exit("the shards do not cover the set")
    cross = (
        cross_check_dev(revisions)
        if a.set == "dev"
        else cross_check_campaign(revisions, a.historical_exports or (CAMPAIGN / "run" / "exports"))
    )
    for row in revisions.values():
        row.pop("all_candidates", None)
    out = {
        "label": "DEVELOPMENT AND REGRESSION EVIDENCE ONLY (design-exposed; owner decisions D-5, D-071); no labels, "
        "not an evaluation",
        "set": a.set,
        "engine_version": ENGINE_VERSION,
        "table_version": dt1.TABLE_VERSION,
        "frozen_reference": FROZEN,
        "index_sha256": file_sha256(a.index),
        "tool_sha256": file_sha256(Path(__file__)),
        "network_attempts": sum(p["network_attempts"] for p in parts),
        "seconds_per_shard": [p["seconds"] for p in sorted(parts, key=lambda p: p["shard"][0])],
        "cross_check_dt1": cross,
        "totals": totals(revisions),
        "revisions": dict(sorted(revisions.items())),
    }
    write_json(a.out, out)
    t = out["totals"]
    print(json.dumps({k: v for k, v in t.items() if k != "changed"}, indent=1))
    print(json.dumps(cross if not cross["mismatched"] else {"MISMATCHED": cross["mismatched"][:5]}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
