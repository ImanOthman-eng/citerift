"""Stage 04 Step 8: the real Stage 02/03 adapters end to end on real bundles (owner Step 8 items 2, 3, 6 to 16).

Real inputs: the previously exposed design bundles of SPEC S-7.4 (VS-1, VS-2, VS-3) and the attributed Retraction
Watch subset index (``step8_support``). DETECT runs the SYNTHETIC test detector of ``step8_support`` (not dt-1), so
the claims here test the Step 8 boundary, ASSEMBLE and VERIFY, never the decision table. Every run here is offline:
the in-process network is refused and the refusals are counted.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation.adapters import Failed, StepRequest
from citerift.investigation.adapters.acquire import retained_acquire
from citerift.investigation.adapters.plan import Integration
from citerift.investigation.anchors import SourceArtifact, unit_span_sha256
from citerift.investigation.controller import run_investigation
from citerift.investigation.schemas import (
    BUNDLE_OBSERVATION,
    CANDIDATE_INPUTS,
    LOOKUP_OBSERVATION,
    LOOKUP_PLAN,
    problems,
)
from citerift.retraction.query import Index
from citerift.wiki.extract import ExtractConfig

pytestmark = pytest.mark.integration


class Case:
    def __init__(self, root: Path, payload: dict[str, Any], result: Any) -> None:
        self.root, self.payload, self.result = root, payload, result
        self.records, self.blobs = S8.committed(root, payload)

    def kind(self, kind: str) -> list[dict[str, Any]]:
        return [r["payload"] for r in self.records if r["kind"] == kind]

    def blob(self, schema: str) -> dict[str, Any]:
        [value] = [v for v in self.blobs.values() if isinstance(v, dict) and v.get("schema") == schema]
        return value

    def lookup(self, doi: str | None, pmid: str | None) -> dict[str, Any]:
        plan = self.blob(LOOKUP_PLAN)
        [obs] = [e["observation"] for e in plan["lookups"] if e["query"] == {"doi": doi, "pmid": pmid}]
        return dict(self.blobs[obs])

    def claims(self) -> dict[tuple[str, ...], dict[str, Any]]:
        return {tuple(k["normalized"] for k in c["candidate"]["keys"]): c for c in self.kind("claim_recorded")}


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


def _run(tmp: Path, bundle: Path, index: Path, integration: Integration = S8.TEST_INTEGRATION, **kw: Any) -> Case:
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(bundle, index, root, **kw))
    return Case(root, payload, S8.run(root, payload, integration))


@pytest.fixture(scope="module")
def offline() -> Any:
    with pytest.MonkeyPatch.context() as mp:
        yield S8.NoNetwork(mp)


@pytest.fixture(scope="module")
def ar(tmp_path_factory: pytest.TempPathFactory, index: Path, offline: Any) -> Case:
    return _run(tmp_path_factory.mktemp("ar"), S8.AR_OBOKATA, index)


@pytest.fixture(scope="module")
def mmr(tmp_path_factory: pytest.TempPathFactory, index: Path, offline: Any) -> Case:
    return _run(tmp_path_factory.mktemp("mmr"), S8.EN_MMR, index)


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path, offline: Any) -> Case:
    return _run(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


# The vertical-slice cases ------------------------------------------------------------------------------------------


def test_obokata_ar_keeps_the_identity_conflict_open(ar: Case, offline: Any) -> None:
    """VS-2 shape: the coherent pair is a positive finding, the nature12969 / PMID 24476881 pair is a conflict whose
    question stays open, and the investigation ends NEEDS_RESOLUTION after VERIFY passes on real content."""
    assert ar.result.status == "NEEDS_RESOLUTION"
    assert ar.result.explanation["outcome"] == "partial"
    claims = ar.claims()
    assert claims[("10.1038/nature12968", "24476887")]["class"] == "RETRACTED_WORK_CITED"
    conflict = claims[("10.1038/nature12969", "24476881")]
    assert conflict["class"] == "IDENTITY_CONFLICT"
    assert [q["claim_id"] for q in ar.kind("question_opened")] == [conflict["claim_id"]]
    [verification] = ar.kind("verification_recorded")
    assert verification["result"] == "passed" and len(verification["checks"]) == 14
    assert offline.attempts == []


def test_obokata_doi_pmid_evidence_is_intact_to_the_step9_boundary(ar: Case) -> None:
    """Owner item 11: the DOI and the PMID of the conflicting citation reach DETECT as separate, typed, anchored
    occurrences of one unit, with Stage 02's own answers for each key and for the pair."""
    inputs = ar.blob(CANDIDATE_INPUTS)
    [cand] = [
        c for c in inputs["candidates"] if [k["normalized"] for k in c["keys"]] == ["10.1038/nature12969", "24476881"]
    ]
    assert cand["shape"] == "PAIR" and cand["taint"] == [] and len(cand["key_evidence"]) >= 2
    evidence = {i["evidence_id"]: i for b in ar.kind("evidence_batch_recorded") for i in ar.blobs[b["batch"]]["items"]}
    keys = {
        (evidence[e]["value"]["key"]["scheme"], evidence[e]["value"]["key"]["normalized"]) for e in cand["key_evidence"]
    }
    assert keys == {("doi", "10.1038/nature12969"), ("pmid", "24476881")}
    expected = {(q["doi"], q["pmid"]): q for q in S8.RW_MANIFEST["q1_with_records"]}
    doi = ar.lookup("10.1038/nature12969", None)["result"]
    assert (doi["lookup_state"], doi["identity"]["status"]) == ("matched", "exact")
    assert sorted(e["record_id"] for e in doi["events"]) == expected[("10.1038/nature12969", None)]["record_ids"]
    assert ar.lookup(None, "24476881")["result"]["lookup_state"] == "no_record"
    pair = ar.lookup("10.1038/nature12969", "24476881")["result"]
    assert ["10.1038/nature12969", "24476881", "ambiguous_identity", "ambiguous"] in S8.RW_MANIFEST["q2_with_records"]
    assert (pair["lookup_state"], pair["identity"]["status"]) == ("ambiguous_identity", "ambiguous")


def test_mmr_wakefield_positive_and_not_found_claims(mmr: Case) -> None:
    """VS-1 shape: the Wakefield original is a positive finding; keys with no record are NOT_FOUND claims whose report
    entries carry the checked sources of their deciding lookup; the Lancet notice pair is left to Step 9."""
    assert mmr.result.status == "COMPLETED"
    claims = mmr.claims()
    assert claims[("10.1016/s0140-6736(97)11096-0", "9500320")]["class"] == "RETRACTED_WORK_CITED"
    assert ("10.1016/s0140-6736(10)60175-4", "20137807") not in claims
    assert mmr.lookup("10.1016/s0140-6736(10)60175-4", "20137807")["result"]["lookup_state"] == "notice_only"
    found = [c for c in claims.values() if c["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"]
    assert found
    for c in found:
        key = c["candidate"]["keys"][0]
        q = (key["normalized"], None) if key["scheme"] == "doi" else (None, key["normalized"])
        checked = mmr.lookup(*q)["result"]["checked_sources"]
        assert checked and checked[0]["source_version"] == S8.RW_MANIFEST["source"]["commit"]


def test_obokata_en_two_positive_findings(en: Case) -> None:
    assert en.result.status == "COMPLETED"
    classes = {k: c["class"] for k, c in en.claims().items()}
    assert classes == {
        ("10.1038/nature12968", "24476887"): "RETRACTED_WORK_CITED",
        ("10.1038/nature12969", "24476891"): "RETRACTED_WORK_CITED",
    }


# IF-7, D-043, EXTRACT, LOOKUP ------------------------------------------------------------------------------------


def test_if7_retains_the_exact_capture_and_every_listed_artifact(ar: Case) -> None:
    manifest = ar.blob(BUNDLE_OBSERVATION)
    capture = (S8.AR_OBOKATA / "capture.json").read_bytes()
    assert ar.blobs["bytes:" + manifest["capture"]["blob"]] == capture
    artifact_set = ar.blobs[manifest["artifact_set"]["blob"]]
    on_disk = {p.name: p.read_bytes() for p in (S8.AR_OBOKATA / "artifacts").iterdir()}
    assert {a["sha256"] for a in artifact_set["artifacts"]} == set(on_disk)
    for a in artifact_set["artifacts"]:
        assert ar.blobs["bytes:" + a["sha256"]] == on_disk[a["sha256"]] and a["bytes"] == len(on_disk[a["sha256"]])
    assert len(json.dumps(manifest)) < 4096  # a closed manifest: no list grows with the bundle


@pytest.mark.parametrize("name", ["ar", "en"])
def test_d043_unit_anchors_on_real_arabic_and_english_bytes(name: str, request: pytest.FixtureRequest) -> None:
    case: Case = request.getfixturevalue(name)
    manifest = case.blob(BUNDLE_OBSERVATION)
    source = SourceArtifact(case.blobs["bytes:" + manifest["source"]["artifact"]], manifest["source"]["artifact"])
    [ext] = [case.blobs[o["blob"]] for o in case.kind("observation_recorded") if o["obs_kind"] == "extraction"]
    units = [
        i for b in case.kind("evidence_batch_recorded") for i in case.blobs[b["batch"]]["items"] if i["kind"] == "unit"
    ]
    assert len(units) == len(ext["units"])
    non_ascii = 0
    for u in units:
        span = ext["units"][int(u["pointer"].rsplit("/", 1)[1])]["source"]
        same = [
            i
            for i in ext["identifiers"]
            if ((i.get("source") or {}).get("byte_start"), (i.get("source") or {}).get("byte_end"))
            == (span["byte_start"], span["byte_end"])
        ]
        again = unit_span_sha256(
            source,
            span,
            extraction_capture=ext["capture"],
            root_capture_sha256=manifest["identity"]["capture_sha256"],
            identifiers=same,
        )
        assert u["value"]["unit_span_sha256"] == again
        source.data[span["byte_start"] : span["byte_end"]].decode("utf-8")  # a real UTF-8 span of the retained bytes
        non_ascii += any(b > 127 for b in source.data[span["byte_start"] : span["byte_end"]])
    assert non_ascii > 0 if name == "ar" else True


def test_extraction_failure_maps_by_d050(tmp_path: Path, index: Path, offline: Any) -> None:
    """A real Stage 03 ``failed`` document (a reference limit) is EXTRACTION_FAILED with the Stage 03 code as the
    reason; nothing downstream runs and no claim exists."""
    case = _run(
        tmp_path,
        S8.AR_OBOKATA,
        index,
        Integration(extract_config=ExtractConfig(max_refs=1), detector=S8.synthetic_detector),
    )
    assert case.result.status == "FAILED"
    t = case.result.explanation["terminated_by"]
    assert (t["step"], t["code"], t["reason"]) == ("EXTRACT", "EXTRACTION_FAILED", "LIMIT_OCCURRENCES")
    assert case.kind("claim_recorded") == []


def test_lookup_overflow_is_unavailable_all_or_nothing(tmp_path: Path, index: Path, offline: Any) -> None:
    """Owner item 9: with a 1-byte budget every lookup with records is unavailable with LOOKUP_EVIDENCE_LIMIT_EXCEEDED
    and no events (never a partial or a negative), VERIFY still passes, and the report says the lookup was limited."""
    case = _run(tmp_path, S8.EN_MMR, index, budget=1)
    wake = case.lookup("10.1016/s0140-6736(97)11096-0", "9500320")
    assert wake["budget_bytes"] == 1 and wake["events"] == [] and wake["event_count"] == 0
    assert wake["result"]["lookup_state"] == "unavailable"
    assert [i["code"] for i in wake["result"]["issues"]] == ["LOOKUP_EVIDENCE_LIMIT_EXCEEDED"]
    claims = case.claims()
    assert claims[("10.1016/s0140-6736(97)11096-0", "9500320")]["class"] == "LOOKUP_UNAVAILABLE"
    assert "RETRACTED_WORK_CITED" not in {c["class"] for c in claims.values()}
    assert case.result.status == "COMPLETED" and case.result.explanation["outcome"] == "partial"


def test_corrupt_index_fails_lookup_with_the_stage02_code(tmp_path: Path, index: Path, offline: Any) -> None:
    bad = tmp_path / "corrupt.sqlite"
    bad.write_bytes(b"not an index" * 100)
    case = _run(tmp_path / "run", S8.AR_OBOKATA, bad)
    t = case.result.explanation["terminated_by"]
    assert t["step"] == "LOOKUP" and t["code"] in {"INDEX_CORRUPT", "INDEX_FORMAT_MISMATCH"}
    assert case.kind("claim_recorded") == []


def test_a_failing_query_is_unavailable_never_no_record(tmp_path: Path, index: Path, offline: Any) -> None:
    """S-6.10: a query that raises becomes an unavailable lookup with the error code; the others are unaffected."""

    class Faulty(Index):
        def gather_bounded(self, doi: str | None = None, pmid: str | None = None, **kw: Any) -> Any:
            if pmid == "24476881" and doi is None:
                raise sqlite3.OperationalError("disk I/O error (injected)")
            return super().gather_bounded(doi, pmid, **kw)

    case = _run(tmp_path, S8.AR_OBOKATA, index, Integration(detector=S8.synthetic_detector, index_opener=Faulty))
    res = case.lookup(None, "24476881")["result"]
    assert res["lookup_state"] == "unavailable"
    assert [i["code"] for i in res["issues"]] == ["INDEX_QUERY_FAILED"]
    assert case.lookup("10.1038/nature12969", None)["result"]["lookup_state"] == "matched"


def test_lookup_observations_are_schema_valid_and_complete(mmr: Case) -> None:
    plan = mmr.blob(LOOKUP_PLAN)
    assert len(plan["lookups"]) == len(mmr.blob(CANDIDATE_INPUTS)["queries"])
    for entry in plan["lookups"]:
        obs = mmr.blobs[entry["observation"]]
        assert problems(obs, LOOKUP_OBSERVATION) == []
        assert obs["event_count"] == len(obs["events"]) == obs["result"]["total_event_count"]


# DETECT boundary, bundle removal, network --------------------------------------------------------------------------


def test_no_detector_fails_detect_with_decision_table_gap(tmp_path: Path, index: Path, offline: Any) -> None:
    case = _run(tmp_path, S8.AR_OBOKATA, index, Integration())
    t = case.result.explanation["terminated_by"]
    assert (t["step"], t["code"]) == ("DETECT", "DECISION_TABLE_GAP")
    assert "Step 9" in t["detail"] and case.kind("claim_recorded") == []


def test_removing_the_bundle_after_acquire_changes_nothing(tmp_path: Path, index: Path, ar: Case, offline: Any) -> None:
    """IF-7: once ACQUIRE committed, the investigation never reads the bundle path again. The bundle is deleted
    before EXTRACT runs; the result equals the run with the bundle in place (same claims, evidence and report
    content), and the vanished path is not a changed input (no STALE)."""
    copy = tmp_path / "bundle"
    shutil.copytree(S8.AR_OBOKATA, copy)
    adapters = S8.TEST_INTEGRATION.adapters()
    extract = adapters["EXTRACT"]

    def remove_then_extract(req: Any) -> Any:
        if copy.exists():
            shutil.rmtree(copy)
        return extract(req)

    root = S8.memory_root(tmp_path / "m")
    payload = S8.create(root, S8.request(copy, index, root))
    result = run_investigation(
        root,
        payload["investigation_key"],
        {**adapters, "EXTRACT": remove_then_extract},
        S8.TEST_INTEGRATION.environment(payload),
    )
    assert not copy.exists()
    gone = Case(root, payload, result)
    assert result.status == ar.result.status == "NEEDS_RESOLUTION"
    assert [r["kind"] for r in gone.records].count("stale_detected") == 0
    assert set(gone.claims()) == set(ar.claims())
    assert {c["claim_id"] for c in gone.kind("claim_recorded")} == {c["claim_id"] for c in ar.kind("claim_recorded")}
    assert gone.blob(CANDIDATE_INPUTS) == ar.blob(CANDIDATE_INPUTS)
    again = S8.run(root, payload, S8.TEST_INTEGRATION)  # reopening without the bundle: terminal, unchanged
    assert again.status == "NEEDS_RESOLUTION"


def test_retained_acquire_needs_no_network(ar: Case, mmr: Case, offline: Any) -> None:
    """Owner items 3 and 15: every retained-bundle run in this module ran with the network refused in-process, and
    nothing tried to connect. (The Stage 03 extraction worker is a separate offline process of Stage 03.)"""
    assert offline.attempts == []
    assert ar.result.status != "FAILED" and mmr.result.status != "FAILED"


def test_adapter_returns_never_write_memory(tmp_path: Path, index: Path) -> None:
    """Owner item 3: an adapter returns values; only the controller writes. ACQUIRE on a read-only memory root
    returns its result without touching it."""
    root = S8.memory_root(tmp_path)
    req = S8.request(S8.AR_OBOKATA, index, root)
    before = sorted(p.name for p in root.iterdir())
    fields = {f: None for f in StepRequest.__dataclass_fields__}
    fields.update(
        step="ACQUIRE", request=req, request_key={"capture_sha256": S8.open_bundle_capture(S8.AR_OBOKATA)}, live=False
    )
    result = retained_acquire(StepRequest(**fields))  # type: ignore[arg-type]
    assert not isinstance(result, Failed)
    assert sorted(p.name for p in root.iterdir()) == before
