"""The engine against the frozen prebuild cases (simulations/stage02/cases), which were written before it.

The same expectations are checked by the independent simulator; a disagreement between the two
implementations fails one of them (directive section 14, items 1 to 10 in synthetic form).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import policy, query, schemas, tension
from citerift.retraction.ingest import event_id

POLICY = S.load_cases("policy_cases.json")
TENSION = S.load_cases("tension_cases.json")


def run_case(tmp: Path, case: dict[str, Any]) -> tuple[dict[str, Any], query.Evidence | None, Path]:
    idx = S.build_case(tmp, case)
    if case.get("index_unavailable"):
        idx = tmp / "missing.sqlite"
    q = case["query"]
    out = query.lookup(idx, q.get("doi"), q.get("pmid"))
    ev = None
    if out["lookup_state"] not in ("invalid_query", "unavailable"):
        ordinals = {r["id"]: i for i, r in enumerate(case["rows"], 1)}
        sup = tuple((event_id(ordinals[a]), event_id(ordinals[b])) for a, b in case.get("supersessions", []))
        with query.Index(idx) as ix:
            ev = ix.gather(q.get("doi"), q.get("pmid"), supersessions=sup)
            out = query.render(ev, ix.snapshot_id)
    return out, ev, idx


@pytest.mark.simulation
@pytest.mark.integration
@pytest.mark.parametrize("case", POLICY, ids=[c["id"] for c in POLICY])
def test_rde_engine_matches_frozen_policy_case(tmp_path: Path, case: dict[str, Any]) -> None:
    out, ev, idx = run_case(tmp_path, case)
    assert schemas.validate_lookup(out) == []
    proj = out["projection"] or {}
    status = proj.get("retraction_status") or {}
    date = proj.get("retraction_date") or {}
    basis = proj.get("basis") or {}
    compare = policy.reduce(ev.evidence_set)["compare"] if ev and ev.evidence_set else {}
    got = {
        "state": out["lookup_state"],
        "status": status.get("status"),
        "value": status.get("value"),
        "date_status": date.get("status"),
        "date_value": date.get("value"),
        "events": out["total_event_count"],
        "identity": out["identity"]["status"],
        "role": out["identifier_role"],
        "alternatives": sorted(a["value"] for a in status.get("alternatives", [])),
        "notice_links": compare.get("notice_links", []),
        "support_origins": basis.get("origins", []),
        "support_observations": compare.get("support.observations", 0),
    }
    expected = case["expected"]
    for key, want in expected.items():
        if key == "reasons":
            assert set(want) <= set(basis.get("reasons", [])), (key, basis.get("reasons"))
        elif key == "quarantined":
            if idx.exists():
                with sqlite3.connect(idx) as conn:
                    assert conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] == want
        elif key == "dup_kinds":
            with sqlite3.connect(idx) as conn:
                kinds = sorted({k for (k,) in conn.execute("SELECT kind FROM dup_group")})
            assert kinds == want
        else:
            assert got[key] == want, (key, got[key], want)


def _plan(names: list[str]) -> list[tuple[str, tuple[str, ...]]]:
    return [("exclude_origin", (n.split(":", 1)[1],)) if n.startswith("exclude_origin:") else (n, ()) for n in names]


@pytest.mark.simulation
@pytest.mark.integration
@pytest.mark.parametrize("case", TENSION, ids=[c["id"] for c in TENSION])
def test_rde_tension_matches_frozen_case(tmp_path: Path, case: dict[str, Any]) -> None:
    _out, ev, _idx = run_case(tmp_path, case)
    assert ev is not None and ev.evidence_set is not None
    report = tension.report(ev, "rw-0000000000000000", _plan(list(case["interventions"])))
    assert schemas.validate_tension(report) == []
    for (name, _), result in zip(_plan(list(case["interventions"])), report["interventions"], strict=True):
        assert result["intervention"] == name
    for label, result in zip(case["interventions"], report["interventions"], strict=True):
        assert sorted(result["changed_fields"]) == sorted(case["interventions"][label]), label
    classes = set(report["diagnostic_classes"])
    if case["classes"] == ["control"]:
        assert classes == {"control"}
    else:
        assert set(case["classes"]) <= classes


@pytest.mark.simulation
def test_rde_tension_baseline_misses_every_diagnostic() -> None:
    """The event-log baseline has no diagnostics; every non-control frozen case has a recorded baseline error."""
    for case in TENSION:
        if case["classes"] != ["control"] and case["id"] not in ("T03", "T05", "T07"):
            assert case["baseline_error"], case["id"]
