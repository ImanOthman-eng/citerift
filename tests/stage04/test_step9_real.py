"""Step 9: the production detector on the real, design-exposed bundles (owner Step 9 items 7, 12, 13, 18, 19).

Bundles: VS-2 arwiki 76190003 (Haruko Obokata), VS-3 enwiki 1372543632 (Haruko Obokata), VS-1 enwiki 1381772671
(MMR vaccine, Wakefield), previously exposed design cases (SPEC S-7.4, owner decision D-5). The index is Stage 02's,
built from the attributed Retraction Watch subset of Step 8 (6 real records). Every socket is refused.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation.adapters import detector as detector_module
from citerift.investigation.adapters.plan import Integration

pytestmark = pytest.mark.integration

CONFLICT_KEYS = ["10.1038/nature12969", "24476881"]
POSITIVE_KEYS = ["10.1038/nature12968", "24476887"]
WAKEFIELD = ["10.1016/s0140-6736(97)11096-0", "9500320"]
LANCET_NOTICE = ["10.1016/s0140-6736(10)60175-4", "20137807"]


class Run:
    def __init__(self, tmp: Path, bundle: Path, index: Path, integration: Integration | None = None) -> None:
        with pytest.MonkeyPatch.context() as mp:
            offline = S8.NoNetwork(mp)
            self.root = S8.memory_root(tmp)
            self.payload = S8.create(self.root, S8.request(bundle, index, self.root))
            self.result = S8.run(self.root, self.payload, integration or Integration())
            self.recs, self.blobs = S8.committed(self.root, self.payload)
            assert offline.attempts == []
        self.evidence = {
            i["evidence_id"]: i
            for r in self.kind("evidence_batch_recorded")
            for i in self.blobs[r["payload"]["batch"]]["items"]
        }

    def kind(self, k: str) -> list[dict[str, Any]]:
        return [r for r in self.recs if r["kind"] == k]

    def claims(self) -> list[dict[str, Any]]:
        return [r["payload"] for r in self.kind("claim_recorded")]

    def claim(self, keys: list[str]) -> dict[str, Any]:
        found = [c for c in self.claims() if [k["normalized"] for k in c["candidate"]["keys"]] == keys]
        assert len(found) == 1, keys
        return found[0]

    def set_items(self, claim: dict[str, Any], where: str = "supporting") -> list[dict[str, Any]]:
        es = self.blobs[claim["evidence_set"]]
        ids = es[where] if where != "alternatives" else [i for a in es["alternatives"] for i in a]
        return [self.evidence[i] for i in ids]


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def ar(tmp_path_factory: pytest.TempPathFactory, index: Path) -> Run:
    return Run(tmp_path_factory.mktemp("ar"), S8.AR_OBOKATA, index)


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path) -> Run:
    return Run(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


@pytest.fixture(scope="module")
def mmr(tmp_path_factory: pytest.TempPathFactory, index: Path) -> Run:
    return Run(tmp_path_factory.mktemp("mmr"), S8.EN_MMR, index)


def _verified(run: Run) -> None:
    checks = [r["payload"] for r in run.kind("verification_recorded")]
    assert len(checks) == 1 and all(c["passed"] for c in checks[0]["checks"])


def test_ar_obokata_identity_conflict(ar: Run) -> None:
    assert ar.result.status == "NEEDS_RESOLUTION"
    _verified(ar)
    claim = ar.claim(CONFLICT_KEYS)
    assert (claim["class"], claim["rule"], claim["status"], claim["value"]) == (
        "IDENTITY_CONFLICT",
        "D-6",
        "conflicting",
        None,
    )
    assert claim["candidate"]["coherence"] == "INCOMPATIBLE" and "IDENTITY_WITNESSED" in claim["reasons"]
    alts = [a["value"] for a in claim["alternatives"]]
    assert alts == [
        {
            "reached_by": {"scheme": "doi", "normalized": "10.1038/nature12969"},
            "work": {"doi": "10.1038/nature12969", "pmid": "24476891"},
        },
        {"reached_by": {"scheme": "pmid", "normalized": "24476881"}, "work": {"doi": None, "pmid": "24476881"}},
    ]
    items = ar.set_items(claim) + ar.set_items(claim, "alternatives")
    kinds = {e["kind"] for e in items}
    assert {
        "unit",
        "use_eligibility",
        "identifier_occurrence",
        "work_candidate",
        "coherence",
        "lookup_result",
        "lookup_event",
        "index_identity",
    } <= kinds
    # both identifiers with their anchors (unit span hash, both identifier occurrences)
    occ = [e for e in items if e["kind"] == "identifier_occurrence"]
    assert {e["value"]["key"]["normalized"] for e in occ} == set(CONFLICT_KEYS)
    assert any(e["kind"] == "unit" and e["value"]["unit_span_sha256"] for e in items)
    # both Q1 lookups and Q2
    queries = {
        (ar.blobs[e["observation"]]["query"]["doi"], ar.blobs[e["observation"]]["query"]["pmid"])
        for e in items
        if e["kind"] == "lookup_result"
    }
    assert queries == {("10.1038/nature12969", None), (None, "24476881"), ("10.1038/nature12969", "24476881")}
    # the witness: the DOI's record carries another PMID
    witness = [e for e in items if e["kind"] == "lookup_event"]
    assert any(
        ar.blobs[e["observation"]]["events"][int(e["pointer"].split("/")[2])]["original_pmid"] == "24476891"
        for e in witness
    )
    # routed with an open question (W-8); no other claim for the candidate
    decisions = [r["payload"] for r in ar.kind("decision_recorded") if r["payload"]["claim_id"] == claim["claim_id"]]
    questions = [r["payload"] for r in ar.kind("question_opened") if r["payload"]["claim_id"] == claim["claim_id"]]
    assert [d["disposition"] for d in decisions] == ["ROUTE_NEEDS_RESOLUTION"]
    assert [q["kind"] for q in questions] == ["identity_conflict"]
    assert [c["class"] for c in ar.claims() if c["cand_ref"] == claim["cand_ref"]] == ["IDENTITY_CONFLICT"]


def test_ar_obokata_positive_stays_positive(ar: Run) -> None:
    claim = ar.claim(POSITIVE_KEYS)
    assert (claim["class"], claim["rule"], claim["value"]) == ("RETRACTED_WORK_CITED", "D-14", "retracted")
    assert claim["candidate"]["coherence"] == "COHERENT" and claim["reasons"] == []
    proj = [e for e in ar.set_items(claim) if e["pointer"] == "/result/projection/retraction_status"]
    assert len(proj) == 1
    status = ar.blobs[proj[0]["observation"]]["result"]["projection"]["retraction_status"]
    assert status["value"] == claim["value"]  # EV-2: the value is the value at the supporting pointer


def test_ar_obokata_replay_gives_the_same_ids(ar: Run, tmp_path: Path, index: Path) -> None:
    again = Run(tmp_path, S8.AR_OBOKATA, index)
    assert sorted(c["claim_id"] for c in again.claims()) == sorted(c["claim_id"] for c in ar.claims())
    assert set(again.evidence) == set(ar.evidence)
    qa = sorted(r["payload"]["question_id"] for r in again.kind("question_opened"))
    assert qa == sorted(r["payload"]["question_id"] for r in ar.kind("question_opened"))


def test_en_obokata_both_works_retracted(en: Run) -> None:
    assert en.result.status == "COMPLETED"
    _verified(en)
    for keys in (["10.1038/nature12969", "24476891"], POSITIVE_KEYS):
        claim = en.claim(keys)
        assert (claim["class"], claim["candidate"]["coherence"]) == ("RETRACTED_WORK_CITED", "COHERENT")


def test_mmr_wakefield_and_the_notice(mmr: Run) -> None:
    assert mmr.result.status == "COMPLETED"
    _verified(mmr)
    wakefield = mmr.claim(WAKEFIELD)
    assert (wakefield["class"], wakefield["value"]) == ("RETRACTED_WORK_CITED", "retracted")
    notice = mmr.claim(LANCET_NOTICE)
    assert (notice["class"], notice["value"], notice["status"]) == ("NOTICE_CITED", None, "uncertain")
    assert "CITED_IDENTIFIER_IS_NOTICE" in notice["reasons"]
    positives = [c for c in mmr.claims() if c["status"] == "verified_fact"]
    assert [[k["normalized"] for k in c["candidate"]["keys"]] for c in positives] == [WAKEFIELD]


def test_every_candidate_has_exactly_one_claim(ar: Run, en: Run, mmr: Run) -> None:
    for run in (ar, en, mmr):
        inputs = next(
            v
            for v in run.blobs.values()
            if isinstance(v, dict) and str(v.get("schema", "")).endswith("candidate-inputs")
        )
        refs = sorted(c["cand_ref"] for c in run.claims())
        assert refs == sorted(c["cand_ref"] for c in inputs["candidates"])


def test_no_evidence_outside_the_candidates_provenance(ar: Run) -> None:
    """Every supporting item of a claim derives from the candidate's unit, its keys' occurrences, its lookups, or the
    index identity: no evidence of another unit or another query."""
    inputs = next(
        v for v in ar.blobs.values() if isinstance(v, dict) and str(v.get("schema", "")).endswith("candidate-inputs")
    )
    units = {u["unit_id"]: u for u in inputs["units"]}
    plan = next(
        v for v in ar.blobs.values() if isinstance(v, dict) and str(v.get("schema", "")).endswith("lookup-plan")
    )
    by_obs = {e["observation"]: e["query"] for e in plan["lookups"]}
    for claim in ar.claims():
        cand = next(c for c in inputs["candidates"] if c["cand_ref"] == claim["cand_ref"])
        unit = units[cand["unit_id"]]
        keys = {k["normalized"] for k in cand["keys"]}
        own = {unit["evidence"]["unit"], unit["evidence"]["use_eligibility"], *unit["occurrences"]}
        for e in ar.set_items(claim) + ar.set_items(claim, "alternatives"):
            if e["kind"] in ("unit", "use_eligibility", "identifier_occurrence"):
                assert e["evidence_id"] in own
            elif e["observation"] in by_obs:
                q = by_obs[e["observation"]]
                assert {v for v in (q["doi"], q["pmid"]) if v} <= keys
            elif e["kind"] == "work_candidate":
                assert e["value"]["keys"] == cand["keys"]
            else:
                assert e["kind"] == "index_identity" and e["observation"] == plan["index_identity"]


@pytest.fixture
def q2_flipped(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A defective adapter: the Obokata pair query reported as matched (Stage 02 says ambiguous_identity)."""
    real = detector_module.lookup_view

    def flipped(obs: Any) -> Any:
        view = real(obs)
        if obs["query"] == {"doi": CONFLICT_KEYS[0], "pmid": CONFLICT_KEYS[1]}:
            from dataclasses import replace

            return replace(view, state="matched")
        return view

    monkeypatch.setattr(detector_module, "lookup_view", flipped)
    yield


def test_a_kappa_q2_disagreement_fails_detect_closed(tmp_path: Path, index: Path, q2_flipped: None) -> None:
    """P2 on real data: kappa is INCOMPATIBLE (the DOI's record names PMID 24476891) but Q2 claims matched: D-5,
    DETECT failed terminally with ADAPTER_INCONSISTENT, and no claim of the investigation is committed."""
    run = Run(tmp_path, S8.AR_OBOKATA, index)
    t = run.result.explanation["terminated_by"]
    assert (t["step"], t["code"]) == ("DETECT", "ADAPTER_INCONSISTENT")
    assert "rule D-5" in t["detail"] and "KAPPA_Q2_DISAGREE" in t["detail"]
    assert run.claims() == [] and run.result.status == "FAILED"
