"""Final corrective cycle (owner decision D-083, item 11): every changed claim of the current table against the
accepted dt-2 engine. Written for dt-3 (candidate c3854b8); rerun for the revised freeze-3 (owner decisions D-086,
D-087) with dt-4, where the per-candidate fields are named after the current table (``dt4``) and the unit's bib-2
unavailability is recorded; ``delta_c3854b8.py`` then compares every claim with the committed dt-3 regression of
c3854b8.

DEVELOPMENT AND REGRESSION EVIDENCE ONLY. Three design-exposed sets, never counted as unseen data:

- ``dev``: the 232 development revisions of Step 13 (``evaluation/dev/DEV_RUN.json``, its bundles);
- ``campaign``: the 80 articles of evaluation 1 (``evaluation-campaign/bundles``; development evidence since D-071);
- ``p2``: the 100 articles of evaluation 2 (``evaluation-p2-campaign/bundles``; development evidence since D-083).

Nothing in an evaluation or campaign directory is written. No label, adjudication, packet or score is read (reviewer
finding F-08): the cross-checks below read only engine claims and class counts.

Each revision runs one investigation offline through the production plan with the current engine (in this process, every
socket refused; Investigation Memory in a temporary directory outside the repository). For every work candidate the
recorded claim is compared with the dt-2 decision of the **same committed inputs**, decided by the accepted dt-2
table (``src/citerift/investigation/dt1.py`` of the freeze-2 commit ``28ba646``, read from git by blob id, checked,
and loaded as an isolated module). The dt-3 and dt-4 inputs add the cited description or its unavailability
(NORMALIZE) and the records (LOOKUP) and nothing else; the dt-2 table never reads them. Cross-checks of the dt-2
decisions re-decided here:

- ``dev`` and ``campaign``: per revision, the dt-2 class counts equal those recorded by the corrective-cycle
  regression (``corrective/regression/DEV_REGRESSION.json`` and ``CAMPAIGN_REGRESSION.json``);
- ``p2``: per article, the dt-2 class counts equal ``evaluation-p2-campaign/run/RUN.json`` ``claims_by_class`` (the
  historical dt-2 run; claim counts only).

For every candidate of the role-collision rule (dt-2 D-10 with ``IDENTIFIER_ROLE_COLLISION``) the bib-1 verdicts of
its unit against the deciding lookup's events are recorded, for the role-collision recall study (item 5).

Run (shards in parallel, then merge)::

    uv run python -P R/regress.py run --set dev --index I --shard 0/3 --out part0.json   # 1/3, 2/3
    uv run python -P R/regress.py merge --set dev --index I --parts part*.json --out DEV_REGRESSION.json
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import types
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[6]
S04 = REPO / "docs/verification/stage-04"
TOOLS = S04 / "evaluation/tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "tests" / "stage04"))
sys.path.insert(0, str(S04 / "final-cycle"))

import pytest  # noqa: E402
import step8_support as S8  # noqa: E402
from fc_provenance import finish as fc_finish  # noqa: E402
from fc_provenance import start as fc_start  # noqa: E402
from s13_common import file_sha256, read_json, write_json  # noqa: E402

from citerift.investigation import __version__ as ENGINE_VERSION  # noqa: E402
from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.detector import candidate_view, lookup_roles, lookup_view  # noqa: E402
from citerift.investigation.adapters.plan import Integration  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402

CUR = dt1.TABLE_VERSION.replace("-", "")  # the current table's field name: "dt4"
POSITIVE = ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")
DT2_COMMIT = "28ba6467c7005eec7bf51869974719a402059ca7"
DT2_BLOB = "815f0dde0392415fd97c9c4c58e43026d3162bf8"  # git rev-parse 28ba646:src/citerift/investigation/dt1.py
SETS = {
    "dev": None,
    "campaign": S04 / "evaluation-campaign" / "bundles",
    "p2": S04 / "evaluation-p2-campaign" / "bundles",
}


def _git(*args: str, text: bool = True) -> Any:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=text, check=True).stdout  # noqa: S603, S607


def load_dt2() -> types.ModuleType:
    name = "dt1_dt2_28ba646"
    if name in sys.modules:
        return sys.modules[name]
    blob = _git("rev-parse", f"{DT2_COMMIT}:src/citerift/investigation/dt1.py").strip()
    if blob != DT2_BLOB:
        raise SystemExit(f"the freeze-2 commit names blob {blob}, not {DT2_BLOB}")
    data = _git("cat-file", "blob", DT2_BLOB, text=False)
    got = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    if got != DT2_BLOB:
        raise SystemExit(f"the dt-2 bytes hash to {got}, not {DT2_BLOB}")
    mod = types.ModuleType(name)
    sys.modules[name] = mod  # dataclasses resolve annotations through sys.modules
    exec(compile(data.decode("utf-8"), f"{name}.py", "exec"), mod.__dict__)  # noqa: S102 - pinned repository blob
    if mod.TABLE_VERSION != "dt-2":
        raise SystemExit("the freeze-2 table is not dt-2")
    return mod


def _same_fields(cls: Any, obj: Any, **override: Any) -> Any:
    """``cls`` built from the fields of ``obj`` that ``cls`` declares (dt-3 and dt-4 add only defaulted fields)."""
    return cls(**{f.name: override.get(f.name, getattr(obj, f.name)) for f in dataclasses.fields(cls)})


def to_dt2(c: Any) -> Any:
    """A current ``Candidate`` as the dt-2 ``Candidate`` (the fields ``cited``, ``cited_unavailable`` and
    ``Event.record`` are dropped)."""
    D2 = load_dt2()

    def lk(x: Any) -> Any:
        return _same_fields(D2.Lookup, x, events=tuple(_same_fields(D2.Event, e) for e in x.events))

    return _same_fields(D2.Candidate, c, lookups=tuple((r, lk(x)) for r, x in c.lookups))


def decision(out: Any) -> dict[str, Any]:
    return {"rule": out.rule, "class": out.cls or out.failure, "reasons": list(out.reasons)}


def with_tables(out: dict[str, Any]) -> dict[str, Any]:
    """The committed code and index of a shard (reviewer finding N-01: the whole scientific dependency set is checked
    for uncommitted changes and the running tool's SHA-256 is recorded; see ``fc_provenance``; D-03: a shard refuses
    to start from, or to finish in, a changed tree) with the two decision tables."""
    out["tables"] = {
        "reference": {"table_version": "dt-2", "commit": DT2_COMMIT, "blob": DT2_BLOB},
        "current": {"table_version": dt1.TABLE_VERSION, "engine_version": ENGINE_VERSION},
    }
    return out


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
    row["units_with_description"] = sum(1 for u in inputs["units"] if u.get("bibliography") is not None)
    row["units_unavailable"] = dict(
        Counter(u["bibliography_unavailable"] for u in inputs["units"] if u.get("bibliography_unavailable"))
    )
    D2 = load_dt2()
    cands: list[dict[str, Any]] = []
    for cand in inputs["candidates"]:
        views = {q: lookup_view(blobs[obs_of[q]]) for _, q in lookup_roles(cand)}
        view = candidate_view(cand, units[cand["unit_id"]], views)
        new, old = decision(dt1.decide(view)), decision(D2.decide(to_dt2(view)))
        claim = claims.get(cand["cand_ref"])
        recorded = {"rule": claim["rule"], "class": claim["class"], "reasons": claim["reasons"]} if claim else None
        entry: dict[str, Any] = {
            "cand_ref": cand["cand_ref"],
            "unit_id": cand["unit_id"],
            "keys": [k["normalized"] for k in cand["keys"]],
            CUR: new,
            "dt2": old,
            f"recorded_equals_{CUR}": recorded == new,
            "has_description": view.cited is not None,
            "unavailable": view.cited_unavailable,
        }
        if old["rule"] in ("D-10", "D-14") or new["rule"] in ("D-13a", "D-13b", "D-13c", "D-14"):
            entry["bib"] = [{"position": k, **cmp.to_json()} for k, cmp in dt1.comparisons(view)]
        cands.append(entry)
    row["candidates"] = len(cands)
    row[f"recorded_equals_{CUR}"] = all(c[f"recorded_equals_{CUR}"] for c in cands)
    row["dt2_classes"] = dict(Counter(c["dt2"]["class"] for c in cands))
    row[f"{CUR}_classes"] = dict(Counter(c[CUR]["class"] for c in cands))
    row["changed"] = [c for c in cands if c["dt2"] != c[CUR]]
    row["role_collision"] = [
        c for c in cands if c["dt2"]["rule"] == "D-10" and "IDENTIFIER_ROLE_COLLISION" in c["dt2"]["reasons"]
    ]
    row["all_candidates"] = cands
    return row


def bundles_of(which: str) -> list[tuple[str, Path]]:
    if which == "dev":
        dev = read_json(S04 / "evaluation/dev/DEV_RUN.json")["revisions"]
        return [(name, REPO / r["bundle"]) for name, r in sorted(dev.items())]
    folder = SETS[which]
    if folder is None:
        raise SystemExit(f"no bundle folder for {which}")
    return [(p.name, p) for p in sorted(folder.iterdir()) if p.is_dir()]


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


def cross_check(which: str, revisions: dict[str, Any]) -> dict[str, Any]:
    """The dt-2 class counts re-decided here against the recorded dt-2 class counts of each revision."""
    if which == "p2":
        recorded = {
            a["article"]: a["claims_by_class"]
            for a in read_json(S04 / "evaluation-p2-campaign/run/RUN.json")["articles"]
        }
        source = "evaluation-p2-campaign/run/RUN.json claims_by_class"
    else:
        name = "DEV_REGRESSION.json" if which == "dev" else "CAMPAIGN_REGRESSION.json"
        rows = read_json(S04 / "corrective/regression" / name)["revisions"]
        recorded = {k: v.get("dt2_classes", {}) for k, v in rows.items()}
        source = f"corrective/regression/{name} dt2_classes"
    mismatched = [
        {"revision": n, "redecided_dt2": row.get("dt2_classes", {}), "recorded": recorded.get(n)}
        for n, row in revisions.items()
        if row.get("dt2_classes", {}) != (recorded.get(n) or {})
    ]
    return {"source": source, "revisions": len(revisions), "mismatched": mismatched}


def totals(revisions: dict[str, Any]) -> dict[str, Any]:
    changed = [dict(c, revision=n) for n, r in revisions.items() for c in r.get("changed", [])]
    unit_pos = {"dt2": 0, CUR: 0}
    for r in revisions.values():
        for k in ("dt2", CUR):
            units: dict[str, set[str]] = {}
            for c in r.get("all_candidates", []):
                units.setdefault(c["unit_id"], set()).add(c[k]["class"])
            unit_pos[k] += sum(1 for v in units.values() if v & set(POSITIVE))
    every = [c for r in revisions.values() for c in r.get("all_candidates", [])]
    objects = Counter(b["object"] for c in every for b in c.get("bib", []) if c["dt2"]["rule"] == "D-14")
    rc = [dict(c, revision=n) for n, r in revisions.items() for c in r.get("role_collision", [])]
    return {
        "revisions": len(revisions),
        "lifecycle": dict(Counter(r["lifecycle"] for r in revisions.values())),
        "verified": sum(1 for r in revisions.values() if r.get("verified")),
        "candidates": len(every),
        "candidates_with_description": sum(1 for c in every if c["has_description"]),
        "candidates_unavailable": dict(Counter(c["unavailable"] for c in every if c.get("unavailable"))),
        f"recorded_equals_{CUR}_everywhere": all(r.get(f"recorded_equals_{CUR}", True) for r in revisions.values()),
        "dt2_positive_pairs_by_bib_object": dict(objects),
        "changed_claims": len(changed),
        "changed_by_transition": dict(
            Counter(f"{c['dt2']['rule']} {c['dt2']['class']} -> {c[CUR]['rule']} {c[CUR]['class']}" for c in changed)
        ),
        "new_positive": sum(1 for c in changed if c[CUR]["class"] in POSITIVE),
        "lost_positive": sum(1 for c in changed if c["dt2"]["class"] in POSITIVE and c[CUR]["class"] not in POSITIVE),
        "new_notice_cited": sum(1 for c in changed if c[CUR]["class"] == "NOTICE_CITED"),
        "new_not_found": sum(1 for c in changed if c[CUR]["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"),
        "positive_units": unit_pos,
        "changed": changed,
        "role_collision_candidates": rc,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="final-cycle regression: the current table against the accepted dt-2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", choices=tuple(SETS), required=True)
    r.add_argument("--index", type=Path, required=True)
    r.add_argument("--shard", required=True)
    r.add_argument("--out", type=Path, required=True)
    m = sub.add_parser("merge")
    m.add_argument("--set", choices=tuple(SETS), required=True)
    m.add_argument("--index", type=Path, required=True)
    m.add_argument("--parts", type=Path, nargs="+", required=True)
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        k, n = (int(x) for x in a.shard.split("/"))
        t0 = time.perf_counter()
        prov = with_tables(fc_start(Path(__file__), a.index))
        part = run_shard(a.set, a.index.resolve(), k, n)
        fc_finish({x: y for x, y in prov.items() if x != "tables"}, Path(__file__), a.index)
        part["seconds"] = round(time.perf_counter() - t0, 1)
        part["provenance"] = prov
        write_json(a.out, part)
        return 0
    parts = [read_json(p) for p in a.parts]
    revisions = {k: v for p in parts for k, v in p["revisions"].items()}
    if sorted(revisions) != sorted(n for n, _ in bundles_of(a.set)):
        sys.exit("the shards do not cover the set")
    provs = [p.get("provenance") for p in parts]
    if provs[0] is None or any(x != provs[0] for x in provs) or provs[0]["uncommitted"]:
        sys.exit("the shards do not record one committed code revision")
    if (
        provs[0]["tool_sha256"] != file_sha256(Path(__file__))
        or provs[0]["code_commit"] != _git("rev-parse", "HEAD").strip()
    ):
        sys.exit("the shards ran another tool or commit than this merge")
    cross = cross_check(a.set, revisions)
    tot = totals(revisions)  # before the per-candidate rows are dropped
    for row in revisions.values():
        row.pop("all_candidates", None)
    out = {
        "label": "DEVELOPMENT AND REGRESSION EVIDENCE ONLY (design-exposed; owner decisions D-071, D-083); no labels, "
        "not an evaluation",
        "set": a.set,
        "engine_version": ENGINE_VERSION,
        "table_version": dt1.TABLE_VERSION,
        "reference_table": {"table_version": "dt-2", "commit": DT2_COMMIT, "blob": DT2_BLOB},
        "provenance": provs[0],
        "index_sha256": file_sha256(a.index),
        "tool_sha256": file_sha256(Path(__file__)),
        "network_attempts": sum(p["network_attempts"] for p in parts),
        "seconds_per_shard": [p["seconds"] for p in sorted(parts, key=lambda p: p["shard"][0])],
        "cross_check_dt2": cross,
        "totals": tot,
        "revisions": dict(sorted(revisions.items())),
    }
    write_json(a.out, out)
    t = out["totals"]
    print(json.dumps({k: v for k, v in t.items() if k not in ("changed", "role_collision_candidates")}, indent=1))
    print(json.dumps(cross if not cross["mismatched"] else {"MISMATCHED": cross["mismatched"][:5]}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
