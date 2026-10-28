"""R-026 correction: an unresolved identifier bridge does not by itself establish a status or a date.

SPECIFICATION.md 11.1 rule 7f and 16 item 25. A bridged assertion is one reached from the query only through
a link the sources do not resolve: a PMID or DOI that co-occurs with the query key on another record
(``pmid_cooccurrence``, ``doi_cooccurrence``), the pairing of a two-identifier query (``query_pair``), or a
Crossref relation about a DOI the query did not give. Sufficiency is decided from the supporting assertions,
not from the aggregate identity flag: a value or date is a verified fact only when the direct assertions
establish it and the bridged ones, if accepted, would not change it.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import policy, query, schemas, tension
from citerift.retraction.query import Index, lookup

D, P = "10.5555/w", "4242"  # the work's DOI and PMID
D2, P2 = "10.5555/other", "4343"


def _event(record_id: str, nature: str, notice: str, date: str = "3/12/2015 0:00", **values: str) -> dict[str, str]:
    return S.row(
        **{"Record ID": record_id, "RetractionNature": nature, "RetractionDOI": notice, "RetractionDate": date} | values
    )


def _paired(record_id: str, nature: str, notice: str, date: str = "3/12/2015 0:00") -> dict[str, str]:
    """A record that carries both identifiers of the work (the co-occurrence a bridge goes through)."""
    return _event(record_id, nature, notice, date, OriginalPaperDOI=D, OriginalPaperPubMedID=P)


def _only(scheme: str, record_id: str, nature: str, notice: str, date: str = "3/12/2015 0:00") -> dict[str, str]:
    """A record that carries only one identifier of the work."""
    field = "OriginalPaperDOI" if scheme == "doi" else "OriginalPaperPubMedID"
    return _event(record_id, nature, notice, date, **{field: D if scheme == "doi" else P})


# For a DOI query the bridge goes through the PMID (records carrying only the PMID are bridged); for a PMID
# query it goes through the DOI. Each scenario is built for both, so the two directions are tested alike.
DIRECTIONS = {"doi": ("doi", (D, None), "pmid"), "pmid": ("pmid", (None, P), "doi")}


def _run(tmp: Path, rows: list[dict[str, str]], key: tuple[str | None, str | None], crossref: Any = None) -> Any:
    idx = S.build_rows(tmp, rows, crossref)
    out = lookup(idx, key[0], key[1], page_size=100)
    assert schemas.validate_lookup(out) == []
    return idx, out


def _status(out: dict[str, Any]) -> tuple[Any, ...]:
    proj = out["projection"]
    date = proj["retraction_date"] or {}
    return (
        proj["retraction_status"]["status"],
        proj["retraction_status"]["value"],
        date.get("status"),
        date.get("value"),
    )


# 1. Bridge-only support ------------------------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_rde_bridge_only_retraction_is_not_a_verified_fact(tmp_path: Path, direction: str) -> None:
    """The only retraction is reached through the bridge: no verified status and no verified date (frozen
    P33, T05 and T06 amended). The bridged record, its link and its source assertions are kept."""
    _scheme, key, other = DIRECTIONS[direction]
    rows = [_paired("1", "Expression of concern", "10.5555/n-eoc"), _only(other, "2", "Retraction", "10.5555/n-r")]
    idx, out = _run(tmp_path, rows, key)
    assert out["identity"]["status"] == "bridged"
    assert _status(out) == ("uncertain", None, None, None)
    basis = out["projection"]["basis"]
    assert {"BRIDGE_ONLY_SUPPORT", "BRIDGED_EVIDENCE_MATERIAL"} <= set(basis["reasons"])
    assert "unverified identifier link" in out["projection"]["retraction_status"]["reason"]
    assert basis["supporting_assertions"] == []
    # Preserved: both records, the candidate link, and the bridged assertion named in the basis.
    assert out["total_event_count"] == 2
    links = {e["record_id"]: e["linked_via"] for e in out["events"]}
    assert links == {"1": None, "2": f"{other}_cooccurrence"}
    bridged = [e for e in out["events"] if e["linked_via"]]
    assert basis["bridged_assertions"] == [f"{bridged[0]['event_id']}/event_type"]
    with Index(idx) as ix:
        detail = query.event_detail(ix, bridged[0]["event_id"])
    assert detail is not None
    assert {a["proposition"]["predicate"] for a in detail["assertions"]} >= {"event_type", "notice_date"}


@pytest.mark.regression
def test_rde_query_pair_alone_does_not_establish_a_retraction(tmp_path: Path) -> None:
    """A two-identifier query links a PMID-only record through the query's own pairing; that pairing is not
    confirmed by any source, so a retraction recorded only there is not a verified fact for the DOI's work."""
    rows = [
        _only("doi", "1", "Expression of concern", "10.5555/n-eoc"),
        _only("pmid", "2", "Retraction", "10.5555/n-r"),
    ]
    _idx, out = _run(tmp_path, rows, (D, P))
    assert {e["record_id"]: e["linked_via"] for e in out["events"]} == {"1": None, "2": "query_pair"}
    assert _status(out) == ("uncertain", None, None, None)
    assert "BRIDGE_ONLY_SUPPORT" in out["projection"]["basis"]["reasons"]


@pytest.mark.regression
def test_rde_crossref_relation_reached_through_a_bridge_is_bridged(tmp_path: Path) -> None:
    """Symmetry fix: for a PMID query, a Crossref relation about the DOI that co-occurs with the PMID is
    reached through the same bridge as a DOI-only record. It cannot establish the retraction alone. For a DOI
    query the same relation is about the queried DOI and is direct."""
    rows = [_paired("1", "Expression of concern", "10.5555/n-eoc")]
    deposit = [{"original": D, "updated_by": [{"DOI": "10.5555/n-pub", "type": "retraction", "source": "publisher"}]}]
    idx = S.build_rows(tmp_path, rows, deposit)
    by_pmid = lookup(idx, None, P)
    assert by_pmid["identity"]["status"] == "bridged"
    assert by_pmid["projection"]["retraction_status"]["status"] == "uncertain"
    assert "BRIDGE_ONLY_SUPPORT" in by_pmid["projection"]["basis"]["reasons"]
    by_doi = lookup(idx, D, None)
    assert by_doi["identity"]["status"] == "exact"
    status = by_doi["projection"]["retraction_status"]
    assert (status["status"], status["value"]) == ("verified_fact", "retracted")
    assert by_doi["projection"]["basis"]["origins"] == ["publisher"]


# 2. Sufficient direct support plus bridged events --------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
@pytest.mark.parametrize(
    ("bridged_nature", "bridged_notice"),
    [("Retraction", "10.5555/n-r"), ("Retraction", "10.5555/n-r2"), ("Correction", "10.5555/n-c")],
)
def test_rde_direct_retraction_keeps_its_conclusion_beside_bridged_events(
    tmp_path: Path, direction: str, bridged_nature: str, bridged_notice: str
) -> None:
    """Adequate direct evidence keeps its conclusion: the bridged record agrees or cannot change it."""
    _scheme, key, other = DIRECTIONS[direction]
    rows = [_paired("1", "Retraction", "10.5555/n-r"), _only(other, "2", bridged_nature, bridged_notice)]
    _idx, out = _run(tmp_path, rows, key)
    assert out["identity"]["status"] == "bridged"
    assert _status(out) == ("verified_fact", "retracted", "verified_fact", "2015-03-12")
    basis = out["projection"]["basis"]
    direct = [e["event_id"] for e in out["events"] if not e["linked_via"]]
    assert basis["supporting_assertions"] == [f"{direct[0]}/event_type"]  # support is the direct record only
    assert "BRIDGED_EVIDENCE_NOT_COUNTED" in basis["reasons"]
    assert len(basis["bridged_assertions"]) == 1


@pytest.mark.regression
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_rde_bridged_retraction_with_another_date_makes_the_date_uncertain(tmp_path: Path, direction: str) -> None:
    """The status stays a verified retraction; the date does not, because the bridged retraction, if it
    concerns this work, reports another date (the C-9 rule for conflicted events, applied to bridges)."""
    _scheme, key, other = DIRECTIONS[direction]
    rows = [
        _paired("1", "Retraction", "10.5555/n-r", "3/12/2015 0:00"),
        _only(other, "2", "Retraction", "10.5555/n-r2", "5/10/2016 0:00"),
    ]
    _idx, out = _run(tmp_path, rows, key)
    assert _status(out) == ("verified_fact", "retracted", "uncertain", None)
    assert "BRIDGED_EVIDENCE_MATERIAL" in out["projection"]["basis"]["reasons"]


@pytest.mark.regression
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_rde_direct_non_retraction_is_not_stated_beside_a_bridged_retraction(tmp_path: Path, direction: str) -> None:
    """A directly recorded correction is not stated as the current effect while a retraction that may concern
    the work is reached through the bridge; the reverse (bridged correction) leaves it a fact."""
    _scheme, key, other = DIRECTIONS[direction]
    rows = [_paired("1", "Correction", "10.5555/n-c"), _only(other, "2", "Retraction", "10.5555/n-r")]
    _idx, out = _run(tmp_path, rows, key)
    assert _status(out)[:2] == ("uncertain", None)
    rows = [_paired("1", "Correction", "10.5555/n-c"), _only(other, "2", "Correction", "10.5555/n-c2")]
    _idx, out = _run(tmp_path / "agree", rows, key)
    assert _status(out)[:2] == ("verified_fact", "correction")


# 3. Contradictory identifiers -----------------------------------------------------------------------------------


@pytest.mark.regression
def test_rde_contradictory_identifiers_never_give_a_verified_fact(tmp_path: Path) -> None:
    rows = [
        _event("1", "Retraction", "10.5555/n1", OriginalPaperDOI=D, OriginalPaperPubMedID=P2),
        _event("2", "Retraction", "10.5555/n2", OriginalPaperDOI=D2, OriginalPaperPubMedID=P),
    ]
    idx = S.build_rows(tmp_path, rows)
    # The query pairs D with P, but the sources pair D with P2 and P with D2: no union, no value.
    pair = lookup(idx, D, P)
    assert pair["lookup_state"] == "ambiguous_identity"
    assert pair["projection"]["retraction_status"]["status"] == "uncertain"
    assert len(pair["identity"]["candidate_groups"]) == 2


@pytest.mark.regression
def test_rde_pmid_with_two_dois_is_ambiguous_and_doi_with_two_pmids_does_not_bridge(tmp_path: Path) -> None:
    """The pinned asymmetry of SPECIFICATION.md 10.3 steps 3 and 4 (the anchor is DOI-first): a PMID naming
    two DOIs names two originals (ambiguous); a DOI naming two PMIDs is one original whose secondary
    identifier diverges, so nothing is bridged through either PMID."""
    rows = [
        _event("1", "Expression of concern", "10.5555/n1", OriginalPaperDOI=D, OriginalPaperPubMedID=P),
        _event("2", "Expression of concern", "10.5555/n2", OriginalPaperDOI=D, OriginalPaperPubMedID=P2),
        _event("3", "Retraction", "10.5555/n3", OriginalPaperPubMedID=P),
        _event("4", "Correction", "10.5555/n4", OriginalPaperDOI=D2, OriginalPaperPubMedID=P2),
    ]
    idx = S.build_rows(tmp_path, rows)
    by_doi = lookup(idx, D, None, page_size=100)
    assert by_doi["identity"]["status"] == "exact"
    assert {i["code"] for i in by_doi["issues"]} >= {"IDENTITY_SECONDARY_DIVERGENT"}
    assert sorted(e["record_id"] for e in by_doi["events"]) == ["1", "2"]
    assert _status(by_doi)[:2] == ("verified_fact", "expression_of_concern")
    by_pmid = lookup(idx, None, P2)
    assert by_pmid["lookup_state"] == "ambiguous_identity"
    assert by_pmid["projection"]["retraction_status"]["status"] == "uncertain"


@pytest.mark.regression
def test_rde_bridge_through_a_contradicted_key_cannot_establish_a_retraction(tmp_path: Path) -> None:
    """The PMID that co-occurs with the DOI also co-occurs with another DOI elsewhere: a PMID-only retraction
    may belong to either work. It is listed as a bridged candidate and establishes nothing."""
    rows = [
        _paired("1", "Expression of concern", "10.5555/n-eoc"),
        _event("2", "Correction", "10.5555/n-c", OriginalPaperDOI=D2, OriginalPaperPubMedID=P),
        _only("pmid", "3", "Retraction", "10.5555/n-r"),
    ]
    _idx, out = _run(tmp_path, rows, (D, None))
    assert {e["record_id"]: e["linked_via"] for e in out["events"]} == {"1": None, "3": "pmid_cooccurrence"}
    assert _status(out)[:2] == ("uncertain", None)


# 4. DOI/PMID query symmetry -------------------------------------------------------------------------------------

SCENARIOS = {
    "bridge_only": lambda o: [
        _paired("1", "Expression of concern", "10.5555/a"),
        _only(o, "2", "Retraction", "10.5555/b"),
    ],
    "direct_and_bridged_agree": lambda o: [
        _paired("1", "Retraction", "10.5555/a"),
        _only(o, "2", "Retraction", "10.5555/a"),
    ],
    "bridged_date_differs": lambda o: [
        _paired("1", "Retraction", "10.5555/a", "3/12/2015 0:00"),
        _only(o, "2", "Retraction", "10.5555/b", "5/10/2016 0:00"),
    ],
    "bridged_correction": lambda o: [_paired("1", "Retraction", "10.5555/a"), _only(o, "2", "Correction", "10.5555/b")],
    "bridged_eoc_beside_eoc": lambda o: [
        _paired("1", "Expression of concern", "10.5555/a"),
        _only(o, "2", "Expression of concern", "10.5555/b"),
    ],
}


@pytest.mark.regression
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_rde_doi_and_pmid_queries_bridge_symmetrically(tmp_path: Path, scenario: str) -> None:
    """The same evidence seen from the DOI (bridge through the PMID) and from the PMID (bridge through the
    DOI) gives the same projection, reasons and support counts."""
    results = []
    for direction in ("doi", "pmid"):
        _scheme, key, other = DIRECTIONS[direction]
        _idx, out = _run(tmp_path / direction, SCENARIOS[scenario](other), key)
        basis = out["projection"]["basis"]
        results.append(
            (
                out["identity"]["status"],
                _status(out),
                sorted(basis["reasons"]),
                len(basis["supporting_assertions"]),
                len(basis.get("bridged_assertions", [])),
            )
        )
    assert results[0] == results[1], results


# Evidence Tension and the reducer ------------------------------------------------------------------------------


@pytest.mark.regression
def test_rde_tension_shows_what_the_direct_evidence_alone_gives(tmp_path: Path) -> None:
    """exclude_ambiguous_links withholds the bridged record: the view is the direct projection, which here is
    a settled expression of concern, so the report shows that the unsettled base rests on the bridge."""
    rows = [_paired("1", "Expression of concern", "10.5555/n-eoc"), _only("doi", "2", "Retraction", "10.5555/n-r")]
    idx = S.build_rows(tmp_path, rows)
    with Index(idx) as ix:
        ev = ix.gather(None, P)
        rep = tension.report(ev, ix.snapshot_id, [("exclude_ambiguous_links", ())])
    assert schemas.validate_tension(rep) == []
    assert rep["base"]["result"]["retraction_status.status"] == "uncertain"
    [view] = rep["interventions"]
    assert view["result"]["retraction_status.value"] == "expression_of_concern"
    assert "retraction_status.status" in view["changed_fields"]
    assert rep["base_unresolved"] is True


@pytest.mark.unit
def test_rde_reducer_never_lets_bridged_support_alone_give_a_fact() -> None:
    """INV-P5: for every value, a verified fact needs at least one direct supporting assertion."""
    from citerift.retraction.dates import TemporalEvidence

    date = TemporalEvidence(
        "3/12/2015 0:00", "notice_date", "2015-03-12", "day", "day", "2015-03-12", "2015-03-12", (), ()
    )
    for kind in ("retracted", "correction", "expression_of_concern"):
        assertion = policy.TypedAssertion(
            assertion_id="ev-1/event_type",
            origin=policy.RW_ORIGIN,
            channel="rw-gitlab-csv",
            type=kind,
            notice_key="doi:10.5555/n",
            anchor="doi:10.5555/w",
            source_ref={"source_id": "retraction-watch"},
            event_id="ev-1",
            notice_date=date,
            bridged=True,
        )
        es = policy.EvidenceSet("matched", "bridged", "doi:10.5555/w", (assertion,), ({"source_id": "x"},))
        out = policy.reduce(es)
        assert out["retraction_status"]["status"] == "uncertain", kind
        assert out["retraction_date"] is None


def _random_set(seed: int) -> policy.EvidenceSet:
    import random

    from citerift.retraction.dates import parse_rw_date

    rng = random.Random(seed)  # a fixed, reproducible draw
    kinds = ("retracted", "correction", "expression_of_concern", "reinstated")
    assertions = []
    for i in range(rng.randint(1, 6)):
        rw = i == 0 or rng.random() < 0.6
        assertions.append(
            policy.TypedAssertion(
                assertion_id=f"a{i}",
                origin=policy.RW_ORIGIN if rw else rng.choice(("publisher", "unknown")),
                channel="rw-gitlab-csv" if rw else "crossref-rest-api",
                type=rng.choice(kinds),
                notice_key=rng.choice([None, "doi:10.5555/n1", "doi:10.5555/n2"]),
                anchor=rng.choice(["doi:10.5555/o", "pmid:77"]),
                source_ref={"source_id": "retraction-watch" if rw else "crossref", "locator": f"loc-{i}"},
                event_id=f"ev-{i + 1:07d}" if rw else None,
                notice_date=parse_rw_date(f"{rng.randint(1, 12)}/{rng.choice([2, 15])}/2015 0:00", "notice_date")
                if rw
                else None,
                bridged=rng.random() < 0.4,
            )
        )
    identity = "bridged" if any(a.bridged for a in assertions) else "exact"
    sources = ({"source_id": "retraction-watch"}, {"source_id": "crossref"})
    return policy.EvidenceSet("matched", identity, "doi:10.5555/o", tuple(assertions), sources)


@pytest.mark.regression
def test_rde_bridge_sufficiency_invariants_over_seeded_sets() -> None:
    """INV-P9, INV-P10 and INV-P11 (MATHEMATICAL_MODEL.md 9.8) on 600 seeded sets, with a non-vacuity floor."""
    seen = {"bridged_verified": 0, "demoted": 0, "kept": 0}
    for seed in range(600):
        es = _random_set(seed)
        out = policy.reduce(es)
        bridged = {a.assertion_id for a in es.assertions if a.bridged}
        direct = policy._reduce(replace(es, assertions=tuple(a for a in es.assertions if not a.bridged)))
        full = policy._reduce(es)
        status = out["retraction_status"]
        if status["status"] == "verified_fact":
            support = set(out["basis"]["supporting_assertions"])
            assert support and not support & bridged, seed  # INV-P9
            for r in (direct, full):  # INV-P10
                assert (r["retraction_status"]["status"], r["retraction_status"]["value"]) == (
                    "verified_fact",
                    status["value"],
                ), seed
            date = out["retraction_date"]
            if date is not None and date["status"] == "verified_fact":
                assert full["retraction_date"]["value"] == direct["retraction_date"]["value"] == date["value"], seed
            seen["bridged_verified" if bridged else "kept"] += 1
        elif direct["retraction_status"]["status"] == "verified_fact":
            seen["demoted"] += 1
            assert bridged, seed
        if bridged and direct["retraction_status"] == full["retraction_status"]:
            assert status["status"] == direct["retraction_status"]["status"], seed  # INV-P11
    assert min(seen.values()) >= 20, seen
