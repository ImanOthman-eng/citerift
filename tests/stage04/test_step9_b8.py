"""Step 9, B-8 (Step 8 carry-forward): evidence identity of two co-reported candidates of one unit.

The real unit is enwiki revision 1379214029 (page 1898990), unit ``un-00013``: an ``identifier_link`` DOI
``10.10520/ejc123796`` and a ``primary_citation_field`` DOI ``10.20940/jae/2012/v11i1a5``. It is one of the 232
design-exposed Stage 03 revisions (Stage 04 planning probe, owner decision D-5): design and regression data only.
NORMALIZE splits it into two single-key candidates flagged CO_REPORTED_MULTIPLE (S-6.5).

Fail-first: under D-051 (``H(observation, pointer, kind)``) a ``work_candidate`` item placed at the unit's pointer
gives both candidates one evidence id although their facts (keys) differ, so a detector would either refuse the
second item (duplicate id) or silently keep one fact for two candidates. The production detector places it at the
first occurrence of the candidate's keys (``adapters.detector`` module docstring), which names one candidate only;
D-051 itself is unchanged, and an id that would name two different items fails DETECT closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation import ids
from citerift.investigation.adapters.detect import DetectFailure
from citerift.investigation.adapters.detector import _Items
from citerift.investigation.adapters.plan import Integration

pytestmark = pytest.mark.integration

EN_MULTI = S8.REPO / "docs/verification/stage-03/evaluation/capture/bundles/reserve/en-1898990-a1"
UNIT = "un-00013"
KEYS = {"10.10520/ejc123796", "10.20940/jae/2012/v11i1a5"}
ORACLE_MANIFEST_SHA256 = "411050772807cfbc5e2053431307516344984a759c489c746a490f1db3e27735"


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory, index: Path) -> dict[str, Any]:
    with pytest.MonkeyPatch.context() as mp:
        offline = S8.NoNetwork(mp)
        root = S8.memory_root(tmp_path_factory.mktemp("b8"))
        payload = S8.create(root, S8.request(EN_MULTI, index, root))
        result = S8.run(root, payload, Integration())
        recs, blobs = S8.committed(root, payload)
        assert offline.attempts == []
    inputs = next(v for v in blobs.values() if isinstance(v, dict) and v.get("schema", "").endswith("candidate-inputs"))
    return {"result": result, "recs": recs, "blobs": blobs, "inputs": inputs, "root": root, "payload": payload}


def committed_evidence(recs: list[dict[str, Any]], blobs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every committed evidence item, from the evidence batches (D-053)."""
    return {
        i["evidence_id"]: i
        for r in recs
        if r["kind"] == "evidence_batch_recorded"
        for i in blobs[r["payload"]["batch"]]["items"]
    }


def _multi(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in inputs["candidates"] if c["unit_id"] == UNIT]


def test_the_real_unit_holds_two_co_reported_candidates(run: dict[str, Any]) -> None:
    cands = _multi(run["inputs"])
    assert len(cands) == 2 and len({c["cand_ref"] for c in cands}) == 2
    assert {c["keys"][0]["normalized"] for c in cands} == KEYS
    assert all(c["flags"] == ["CO_REPORTED_MULTIPLE"] and c["shape"] == "DOI" for c in cands)


def test_fail_first_the_unit_pointer_gives_two_facts_one_id(run: dict[str, Any]) -> None:
    """The B-8 collision reproduced: same observation, pointer and kind; different facts; equal D-051 ids."""
    inputs = run["inputs"]
    unit = next(u for u in inputs["units"] if u["unit_id"] == UNIT)
    a, b = _multi(inputs)
    id_a = ids.evidence_id(inputs["extraction"], unit["pointer"], "work_candidate")
    id_b = ids.evidence_id(inputs["extraction"], unit["pointer"], "work_candidate")
    value_a = {"shape": a["shape"], "keys": a["keys"], "coherence": None}
    value_b = {"shape": b["shape"], "keys": b["keys"], "coherence": None}
    assert id_a == id_b and value_a != value_b and a["cand_ref"] != b["cand_ref"]
    # A detector that kept items by id would hold one fact for two candidates; the production store refuses it.
    items = _Items()
    items.add("work_candidate", inputs["extraction"], unit["pointer"], [], value_a)
    with pytest.raises(DetectFailure) as err:
        items.add("work_candidate", inputs["extraction"], unit["pointer"], [], value_b)
    assert err.value.code == "ADAPTER_INCONSISTENT" and "B-8" in err.value.detail


def test_true_duplicates_still_deduplicate() -> None:
    items = _Items()
    first = items.add(
        "work_candidate", "a" * 64, "/identifiers/3", ["b" * 64], {"shape": "NONE", "keys": [], "coherence": None}
    )
    again = items.add(
        "work_candidate", "a" * 64, "/identifiers/3", ["b" * 64], {"shape": "NONE", "keys": [], "coherence": None}
    )
    assert first == again and len(items.items) == 1


def test_production_gives_each_candidate_its_own_work_candidate_evidence(run: dict[str, Any]) -> None:
    recs, blobs = run["recs"], run["blobs"]
    assert run["result"].status in ("COMPLETED", "NEEDS_RESOLUTION")
    evidence = committed_evidence(recs, blobs)
    claims = {r["payload"]["cand_ref"]: r["payload"] for r in recs if r["kind"] == "claim_recorded"}
    seen = {}
    for cand in _multi(run["inputs"]):
        claim = claims[cand["cand_ref"]]
        assert "CO_REPORTED_MULTIPLE" in claim["reasons"]
        es = blobs[claim["evidence_set"]]
        wc = [evidence[i] for i in es["supporting"] if evidence[i]["kind"] == "work_candidate"]
        assert len(wc) == 1 and wc[0]["value"]["keys"] == cand["keys"]
        assert wc[0]["pointer"].startswith("/identifiers/")
        seen[cand["cand_ref"]] = wc[0]["evidence_id"]
    assert len(set(seen.values())) == 2
    # Every work_candidate item of the investigation names one candidate (no id holds two facts).
    items = [e for e in evidence.values() if e["kind"] == "work_candidate"]
    assert len(items) == len(run["inputs"]["candidates"])


def test_replay_gives_the_same_ids(run: dict[str, Any], tmp_path: Path, index: Path) -> None:
    with pytest.MonkeyPatch.context() as mp:
        S8.NoNetwork(mp)
        root = S8.memory_root(tmp_path)
        payload = S8.create(root, S8.request(EN_MULTI, index, root))
        S8.run(root, payload, Integration())
        recs, _ = S8.committed(root, payload)

    def content(rs: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
        return (
            {r["payload"]["claim_id"] for r in rs if r["kind"] == "claim_recorded"},
            {r["payload"]["batch"] for r in rs if r["kind"] == "evidence_batch_recorded"},
        )

    assert content(recs) == content(run["recs"])
    checks = [r["payload"] for r in run["recs"] if r["kind"] == "verification_recorded"]
    assert checks and all(c["passed"] for c in checks[0]["checks"])


def test_the_step4_oracle_manifest_is_unchanged() -> None:
    """D-051 is unchanged by the B-8 resolution, and the oracle holds no evidence identity: its manifest is the frozen
    one."""
    manifest = S8.REPO / "simulations/stage04/oracle/MANIFEST.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == ORACLE_MANIFEST_SHA256
    assert json.loads(manifest.read_text(encoding="utf-8"))["cases"] == 12632448
