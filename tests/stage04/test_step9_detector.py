"""Step 9: the production detector dt-1 and kappa on LABELED SYNTHETIC contract-shaped inputs.

Every input here is built by ``step9_support.concretize`` from an abstract case of the Step 4 model and is labeled
synthetic (made-up keys, no Retraction Watch data). The production code reads it exactly as committed content:
``adapters.detector.dt1_detector`` parses the lookup observations, decides with ``dt1.RULES`` and builds the claim, its
evidence and its evidence set. Real-data regressions are in ``test_step9_real.py``.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import step9_support as S9

from citerift.investigation import dt1, sets
from citerift.investigation.adapters import Failed
from citerift.investigation.adapters.detect import DetectFailure, make_detect
from citerift.investigation.adapters.detector import dt1_detector
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import CLAIM, COMMON, problems, ref_problems
from citerift.investigation.workflow import CONFLICT, DISPOSITION

pytestmark = pytest.mark.unit

R = S9.R
C = "CITED"
NT: frozenset[str] = frozenset()


def lk(state: str, shape: str = "", collision: bool = False) -> R.Lookup:
    default = {
        "matched": "vf:retracted",
        "notice_only": "unc:notice",
        "ambiguous_identity": "unc:ambiguous",
        "no_record": "unc:not_found",
        "invalid_query": "none",
        "unavailable": "none",
    }
    return (state, shape or default.get(state, "none"), collision)


def pair(d: R.Lookup, p: R.Lookup, q2: R.Lookup, **bits: Any) -> R.Case:
    return R.Case(C, "PAIR", bits.pop("taint", NT), False, d, p, q2, **bits)


def single(shape: str, look: R.Lookup, **kw: Any) -> R.Case:
    d, p = (look, None) if shape == "DOI" else (None, look)
    return R.Case(kw.pop("use", C), shape, kw.pop("taint", NT), kw.pop("multi", False), d, p, None)


def detect(case: R.Case) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    inp, _ = S9.concretize(case)
    out = dt1_detector(inp)
    assert len(out.claims) == 1
    claim, value_set = out.claims[0]
    return dict(claim), dict(value_set), {e["evidence_id"]: dict(e) for e in out.evidence}


def check_claim(claim: dict[str, Any], value_set: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> None:
    """The claim validates, agrees with its set, and every id it names is an item of this run or of NORMALIZE."""
    assert problems(claim, CLAIM) == []
    assert sets.evidence_set_problem(value_set) == "" and sets.claim_set_problem(claim, value_set) == ""
    for e in evidence.values():
        assert ref_problems(e, COMMON + "#/$defs/evidence") == []


# All fifteen classes, and every distinct valid decision of the frozen model -------------------------------------


def _valid_representatives() -> dict[tuple[Any, ...], R.Case]:
    """One valid case per distinct decision of the frozen model: every valid NONE, DOI and PMID case, and every valid
    PAIR lookup triple (``stage02_abstraction.iter_valid_pair_lookups``) under each use and taint set."""
    import decision_space as DS
    import stage02_abstraction as A

    reps: dict[tuple[Any, ...], R.Case] = {}

    def keep(case: R.Case) -> None:
        assert A.valid(case)
        reps.setdefault((case.shape, *S9.model_key(S9.expected(case))), case)

    for shape, use, t in DS.chunks():
        if shape != "PAIR":
            for case in DS.iter_chunk(shape, use, t):
                if A.valid(case):
                    keep(case)
    triples = list(A.iter_valid_pair_lookups())
    for use in R.USES:
        for taint in A.taint_sets():
            for d, p, q2, sig in triples:
                keep(R.Case(use, "PAIR", taint, False, d, p, q2, *sig[3:]))
    return reps


@pytest.fixture(scope="module")
def representatives() -> dict[tuple[Any, ...], R.Case]:
    return _valid_representatives()


def test_every_class_is_executed_by_production_code(representatives: dict[tuple[Any, ...], R.Case]) -> None:
    seen: dict[str, int] = {}
    for case in representatives.values():
        claim, value_set, evidence = detect(case)
        check_claim(claim, value_set, evidence)
        exp = S9.expected(case)
        got = {"rule": claim["rule"], "class": claim["class"], "status": claim["status"], "value": claim["value"]}
        assert got == {k: exp[k] for k in got}, case
        assert DISPOSITION[claim["class"]] == exp["disposition"]
        assert sorted(claim["reasons"]) == exp["reasons"], case
        seen[claim["class"]] = seen.get(claim["class"], 0) + 1
    assert set(seen) == set(dt1.STATUS), sorted(set(dt1.STATUS) - set(seen))
    assert len(seen) == 15


# kappa variants (owner item 8) -----------------------------------------------------------------------------------

M, NR, UN, AMB, NO = lk("matched"), lk("no_record"), lk("unavailable"), lk("ambiguous_identity"), lk("notice_only")
KAPPA: dict[str, tuple[R.Case, str | None, str]] = {
    # name: (case, expected kappa or None for a DETECT failure, expected rule)
    "coherent pair": (pair(M, M, M, coname=True), "COHERENT", "D-14"),
    "DOI witness": (pair(M, NR, lk("ambiguous_identity"), wd=True, w2=True), "INCOMPATIBLE", "D-6"),
    "PMID witness": (pair(NR, M, AMB, wp=True, w2=True), "INCOMPATIBLE", "D-6"),
    "both witnesses": (pair(M, M, AMB, wd=True, wp=True, w2=True), "INCOMPATIBLE", "D-6"),
    "Q1 DOI unavailable, no witness": (pair(UN, M, M), "NOT_DETERMINED", "D-13"),
    "Q1 PMID unavailable, no witness": (pair(M, UN, M), "NOT_DETERMINED", "D-13"),
    "one unavailable, another holds a witness": (pair(UN, M, AMB, wp=True, w2=True), "INCOMPATIBLE", "D-6"),
    "no co-naming": (pair(M, NR, M), "UNDETERMINED", "D-14"),
    "bridged-only": (pair(M, NR, lk("matched", "unc:bridge_only")), "UNDETERMINED", "D-10"),
    "Q2 disagrees with kappa": (pair(M, NR, M, wd=True), None, "D-5"),
    "ambiguous DOI-only query": (single("DOI", AMB), None, "D-5"),
    "ambiguous PMID, no witness": (pair(NR, AMB, AMB, w2=True), None, "D-5"),
    "malformed non-contract projection": (pair(lk("matched", "vf:null"), M, M), None, "D-5"),
    "impossible state/event combination": (pair(NR, NR, NR, wd=True), None, "D-5"),
}


@pytest.mark.parametrize("name", sorted(KAPPA))
def test_kappa_variant(name: str) -> None:
    case, kappa, rule = KAPPA[name]
    assert S9.expected(case)["rule"] == rule  # the frozen model agrees with the expectation written here
    inp, _ = S9.concretize(case)
    if kappa is None:
        with pytest.raises(DetectFailure) as err:
            dt1_detector(inp)
        assert err.value.code == "ADAPTER_INCONSISTENT" and f"rule {rule}" in err.value.detail
        return
    claim, value_set, evidence = detect(case)
    check_claim(claim, value_set, evidence)
    assert claim["rule"] == rule and claim["candidate"]["coherence"] == kappa
    assert ("PAIR_UNCORROBORATED" in claim["reasons"]) == (kappa == "UNDETERMINED")
    coh = [e for e in evidence.values() if e["kind"] == "coherence"]
    assert [e["value"] for e in coh] == [kappa] and coh[0]["evidence_id"] in value_set["supporting"]


def test_p2_all_available_incompatible_iff_q2_ambiguous() -> None:
    """MM P2: with all three lookups available, a witness without an ambiguous Q2, or an ambiguous Q2 without a
    witness, is ADAPTER_INCONSISTENT; the agreeing forms decide normally."""
    for case, ok in (
        (pair(M, NR, AMB, wd=True, w2=True), True),
        (pair(M, NR, M, wd=True), False),
        (pair(M, NR, AMB, w2=False), False),
        (pair(M, M, M), True),
    ):
        inp, _ = S9.concretize(case)
        if ok:
            dt1_detector(inp)
        else:
            with pytest.raises(DetectFailure, match="ADAPTER_INCONSISTENT"):
                dt1_detector(inp)


# Identity conflict, contradiction, W-8 --------------------------------------------------------------------------


def test_identity_conflict_claim_shape() -> None:
    claim, value_set, evidence = detect(pair(M, NR, AMB, wd=True, w2=True))
    assert (claim["class"], claim["status"], claim["value"]) == ("IDENTITY_CONFLICT", "conflicting", None)
    assert DISPOSITION[claim["class"]] == "ROUTE_NEEDS_RESOLUTION" and CONFLICT[claim["class"]] == "identity_conflict"
    alts = claim["alternatives"]
    assert [a["value"]["reached_by"]["scheme"] for a in alts] == ["doi", "pmid"]
    assert alts[0]["value"]["work"] == {"doi": S9.D, "pmid": S9.OTHER_PMID}
    assert alts[1]["value"]["work"] == {"doi": None, "pmid": S9.P}
    assert all(a["supporting_count"] >= 1 for a in alts) and len(value_set["alternatives"]) == 2
    kinds = {evidence[i]["kind"] for i in value_set["supporting"] if i in evidence}
    assert {"coherence", "lookup_event", "lookup_result", "work_candidate", "index_identity"} <= kinds
    assert claim["upstream_reasons"] == []


def test_identity_conflict_with_an_unavailable_q1_uses_the_witness_field() -> None:
    """S-7.3: with Q1(DOI) and Q2 unavailable, the DOI side is supported by the witness event's identifier field."""
    case = pair(UN, M, UN, wp=True)
    assert S9.expected(case)["rule"] == "D-6"
    claim, value_set, evidence = detect(case)
    assert claim["class"] == "IDENTITY_CONFLICT" and "LOOKUP_PARTIAL" in claim["reasons"]
    assert claim["alternatives"][0]["value"]["work"] == {"doi": S9.D, "pmid": None}
    assert claim["alternatives"][1]["value"]["work"] == {"doi": S9.OTHER_DOI, "pmid": S9.P}
    doi_side = value_set["alternatives"][0]
    pointers = {evidence[i]["pointer"] for i in doi_side if i in evidence}
    assert any(p.endswith("/original_doi") for p in pointers)


def test_contradiction_in_sources_has_type_alternatives() -> None:
    claim, value_set, evidence = detect(single("DOI", lk("matched", "conf")))
    assert claim["class"] == "CONTRADICTION_IN_SOURCES" and claim["rule"] == "D-7"
    # each alternative: Stage 02's alternative item and the event of its type
    assert [len(a) for a in value_set["alternatives"]] == [2, 2]
    for i, ids in enumerate(value_set["alternatives"]):
        pointers = sorted(evidence[e]["pointer"] for e in ids)
        assert pointers[0].startswith("/events/")
        assert pointers[1] == f"/result/projection/retraction_status/alternatives/{i}"
    assert [a["value"] for a in claim["alternatives"]] == ["expression_of_concern", "retracted"]
    assert CONFLICT[claim["class"]] == "source_conflict" and DISPOSITION[claim["class"]] == "ROUTE_NEEDS_RESOLUTION"
    assert [u["code"] for u in claim["upstream_reasons"]] == ["SOURCE_TYPE_CONFLICT"]


def test_a_crossref_assertion_in_a_conflict_is_an_alternative_not_a_failure(tmp_path: Path) -> None:
    """Independent review finding F1. Real Stage 02 code, SYNTHETIC rows: a Retraction Watch expression of concern and
    a publisher's Crossref deposit typing the same notice as a retraction give a conflicting status whose conflict
    group holds a Crossref assertion (``cr-...``), not an event. D-7 takes Stage 02's alternatives: the Crossref value
    is supported by its alternative item (whose provenance names the deposit), the Retraction Watch value by its item
    and its event. Before the fix DETECT failed the whole investigation with ADAPTER_INCONSISTENT."""
    import sys

    from citerift.investigation.adapters import lookup as LK
    from citerift.retraction.query import Index

    stage02 = str(Path(__file__).resolve().parents[1] / "stage02")
    sys.path.insert(0, stage02)
    try:
        import rde_support as RDE
    finally:
        sys.path.remove(stage02)
    rows = [
        RDE.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Expression of concern",
                "RetractionDate": "7/2/2019 0:00",
                "OriginalPaperDOI": S9.D,
                "RetractionDOI": "10.5555/n",
            }
        )
    ]
    deposit = [{"original": S9.D, "updated_by": [{"DOI": "10.5555/n", "type": "retraction", "source": "publisher"}]}]
    with Index(RDE.build_rows(tmp_path, rows, deposit)) as ix:
        obs = LK.observe(ix, LK.index_identity(ix, "0" * 64), S9.D, None, 16 * 1024 * 1024)
    groups = obs["result"]["projection"]["basis"]["conflict_groups"]
    assert any(str(a).startswith("cr-") for g in groups for a in g["assertions"])
    inp, blobs = S9.concretize(R.Case("CITED", "DOI", frozenset(), d=("matched", "conf", False)))
    digest = sha256_hex(canon(obs))
    blobs[digest] = obs
    inp.lookup_plan["lookups"][0]["observation"] = digest
    out = dt1_detector(inp)
    claim, value_set = out.claims[0]
    evidence = {e["evidence_id"]: e for e in out.evidence}
    assert (claim["class"], claim["rule"], claim["status"]) == ("CONTRADICTION_IN_SOURCES", "D-7", "conflicting")
    assert [a["value"] for a in claim["alternatives"]] == ["expression_of_concern", "retracted"]
    kinds = [sorted(evidence[e]["pointer"] for e in ids) for ids in value_set["alternatives"]]
    assert kinds == [
        ["/events/0", "/result/projection/retraction_status/alternatives/0"],
        ["/result/projection/retraction_status/alternatives/1"],
    ]
    assert obs["result"]["projection"]["retraction_status"]["alternatives"][1]["provenance"][0]["source_id"] == (
        "crossref"
    )


def test_an_unavailable_q1_side_carries_the_witness_field_even_beside_q2_events() -> None:
    """S-7.3 read literally (review finding F5): with Q1(DOI) unavailable and Q2 available, the DOI side holds Q2's
    DOI-reached events and the witness event's identifier field."""
    claim, value_set, evidence = detect(pair(UN, M, AMB, wp=True, w2=True))
    assert claim["class"] == "IDENTITY_CONFLICT" and "LOOKUP_PARTIAL" in claim["reasons"]
    pointers = {evidence[i]["pointer"] for i in value_set["alternatives"][0] if i in evidence}
    assert any(p.endswith("/original_doi") for p in pointers) and any(p.count("/") == 2 for p in pointers)


def test_identity_conflict_outranks_unavailable_and_contradiction() -> None:
    """Owner item 5: an available witness is never hidden by an unavailable lookup or a contradiction."""
    for case in (
        pair(UN, M, AMB, wp=True, w2=True),
        pair(lk("matched", "conf"), NR, AMB, wd=True, w2=True),
        pair(M, NR, AMB, wd=True, w2=True, taint=frozenset({"IDENTIFIER_UNCONFIRMED"})),
    ):
        claim, _, _ = detect(case)
        assert claim["class"] == "IDENTITY_CONFLICT", case


# D-10 (owner item 10) ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("look", "reason"),
    [
        (lk("matched", "vf:retracted", True), "PMID_ROLE_COLLISION"),
        (lk("matched", "unc:bridge_only"), "BRIDGE_ONLY_SUPPORT"),
    ],
)
def test_d10_keeps_the_upstream_reason_and_evidence(look: R.Lookup, reason: str) -> None:
    claim, value_set, evidence = detect(single("PMID", look))
    assert (claim["class"], claim["rule"]) == ("UNRESOLVED_IDENTITY", "D-10") and reason in claim["reasons"]
    assert claim["value"] is None and claim["status"] == "uncertain"
    assert claim["upstream_reasons"] and all(
        u["evidence"] in value_set["supporting"] for u in claim["upstream_reasons"]
    )
    events = [
        e for e in evidence.values() if e["kind"] == "lookup_event" and e["evidence_id"] in value_set["supporting"]
    ]
    assert events  # the events the collision or the bridge names are in the claim's evidence


# Guards that must never yield a finding or NOT_FOUND (owner items 13, 14) ----------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        single("DOI", lk("unavailable")),  # unavailable
        single("DOI", lk("no_record", "unc:gap")),  # coverage gap
        single("DOI", NR, taint=frozenset({"IDENTIFIER_UNCONFIRMED"})),  # unresolved identifier
        pair(M, NR, AMB, wd=True, w2=True),  # identity conflict
        pair(NR, NR, NR, taint=frozenset({"IDENTIFIER_MALFORMED"})),
        pair(NR, UN, NR),
    ],
)
def test_never_not_found(case: R.Case) -> None:
    claim, _, _ = detect(case)
    assert claim["class"] != "NOT_FOUND_IN_CHECKED_SOURCES" and claim["status"] != "verified_fact"


def test_not_found_needs_a_valid_no_record_lookup_with_checked_sources() -> None:
    claim, value_set, evidence = detect(single("DOI", NR))
    assert (claim["class"], claim["value"], claim["rule"]) == (
        "NOT_FOUND_IN_CHECKED_SOURCES",
        "not_found_in_checked_sources",
        "D-16",
    )
    pointers = {evidence[i]["pointer"] for i in value_set["supporting"] if i in evidence}
    assert {"/result", "/result/projection/retraction_status"} <= pointers
    assert DISPOSITION[claim["class"]] == "REPORT_NOT_FOUND"
    # the same answer naming no checked source is outside the contract: DETECT fails closed (review finding F4)
    for checked in (None, []):
        inp, blobs = S9.concretize(single("DOI", NR))
        obs = blobs[inp.lookup_plan["lookups"][0]["observation"]]
        obs["result"]["checked_sources"] = checked
        digest = sha256_hex(canon(obs))
        blobs[digest] = obs
        inp.lookup_plan["lookups"][0]["observation"] = digest
        with pytest.raises(DetectFailure, match="NOT_FOUND names no checked source"):
            dt1_detector(inp)


def test_a_notice_is_never_positive() -> None:
    for case in (single("DOI", NO), single("PMID", NO), pair(NO, NR, NO), pair(NO, NO, NO, coname=False)):
        claim, _, _ = detect(case)
        assert claim["class"] == "NOTICE_CITED" and claim["value"] is None and claim["status"] == "uncertain"


def test_unavailable_carries_the_budget_reason_only_when_budget_refused() -> None:
    case = single("DOI", lk("unavailable"))
    inp, blobs = S9.concretize(case)
    claim = dict(dt1_detector(inp).claims[0][0])
    assert claim["reasons"] == ["LOOKUP_QUERY_FAILED"]
    for b in blobs.values():
        if isinstance(b, dict) and "result" in b:
            b["result"]["issues"] = [{"code": "LOOKUP_EVIDENCE_LIMIT_EXCEEDED", "budget_bytes": 1, "needed_bytes": 2}]
    claim = dict(dt1_detector(inp).claims[0][0])
    assert claim["reasons"] == ["LOOKUP_EVIDENCE_LIMIT_EXCEEDED", "LOOKUP_QUERY_FAILED"]
    assert problems(claim, CLAIM) == []


# Reinstated (owner item 11) --------------------------------------------------------------------------------------


def test_reinstated_only_from_the_contract_form() -> None:
    """SYNTHETIC: Stage 02 states ``reinstated`` only with supersession links that Stage 04 never passes (S4-04), so
    the class was not observed in real data. From the contract form (matched, verified_fact, reinstated) D-14 gives
    REINSTATED_WORK_CITED; any other form never does."""
    claim, _, _ = detect(single("DOI", lk("matched", "vf:reinstated")))
    assert (claim["class"], claim["value"]) == ("REINSTATED_WORK_CITED", "reinstated")
    for shape in ("unc", "unc:bridge_only"):
        assert detect(single("DOI", lk("matched", shape)))[0]["class"] != "REINSTATED_WORK_CITED"


# D-5, D-17 fail closed (owner items 4, 7, 8) ---------------------------------------------------------------------


def test_d17_is_the_gap_for_a_malformed_deciding_lookup() -> None:
    for look in (lk("matched", "vf:null"), lk("no_record", "vf:retracted"), lk("unknown_state", "none")):
        inp, _ = S9.concretize(single("DOI", look))
        with pytest.raises(DetectFailure) as err:
            dt1_detector(inp)
        assert err.value.code == "DECISION_TABLE_GAP" and "rule D-17" in err.value.detail


def test_a_failing_candidate_stops_detect_with_no_claim() -> None:
    inp, blobs = S9.concretize(single("DOI", lk("matched", "vf:null")))
    blobs = dict(blobs)
    inputs_digest = sha256_hex(canon(inp.candidate_inputs))
    blobs[inputs_digest] = inp.candidate_inputs
    plan_digest = sha256_hex(canon(inp.lookup_plan))
    blobs[plan_digest] = inp.lookup_plan
    req = SimpleNamespace(
        root=inp.root, inputs={"NORMALIZE": (inputs_digest,), "LOOKUP": (plan_digest,)}, read_blob=blobs.__getitem__
    )
    result = make_detect(dt1_detector)(req)  # type: ignore[arg-type]
    assert isinstance(result, Failed) and result.code == "DECISION_TABLE_GAP" and "D-17" in str(result.detail)


# Determinism, no clock, no network, no randomness, no model (owner items 1, 24) ---------------------------------


def test_deciding_twice_gives_identical_claims() -> None:
    case = pair(M, NR, AMB, wd=True, w2=True)
    a, b = S9.concretize(case)[0], S9.concretize(case)[0]
    assert dt1_detector(a) == dt1_detector(b)


def test_the_detector_imports_no_clock_randomness_network_or_model() -> None:
    root = Path(dt1.__file__).parent
    banned = {
        "random",
        "secrets",
        "time",
        "datetime",
        "socket",
        "urllib",
        "http",
        "requests",
        "subprocess",
        "os",
        "threading",
        "multiprocessing",
        "uuid",
        "citerift.governance",
    }
    for path in (root / "dt1.py", root / "adapters" / "detector.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not {m for m in names if m.split(".")[0] in banned or m in banned}, (path, names)


def test_the_table_is_d1_to_d17_in_order() -> None:
    assert tuple(f"D-{i}" for i in range(1, 18)) == dt1.RULE_IDS
    assert [r for r, _ in dt1.RULES] == list(R.RULES)


def test_outcome_is_a_function_of_the_view() -> None:
    inp, _ = S9.concretize(pair(M, NR, M))
    from citerift.investigation.adapters.detector import candidate_view, lookup_roles, lookup_view

    cand, unit = inp.candidate_inputs["candidates"][0], inp.candidate_inputs["units"][0]
    obs = {canon(e["query"]).decode(): inp.read_blob(e["observation"]) for e in inp.lookup_plan["lookups"]}
    view = candidate_view(cand, unit, {q: lookup_view(obs[q]) for _, q in lookup_roles(cand)})
    assert dt1.decide(view) == dt1.decide(replace(view))
