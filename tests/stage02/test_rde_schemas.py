"""Stage 02 schemas and semantic validation (gate 02-D; directive section 14 item 15: dangling references,
dependency cycles and duplicate JSON keys)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.contracts.formats import loads_strict
from citerift.contracts.validate import load_contracts
from citerift.retraction import policy, schemas, tension
from citerift.retraction.dates import parse_rw_date
from citerift.retraction.export import EVENT_COLUMNS, event_from_row
from citerift.retraction.query import Index, lookup

RETRACTION_SCHEMAS = S.REPO / "schemas" / "retraction" / "v1"


def codes(problems: list[Any]) -> set[str]:
    return {p.code for p in problems}


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    rows = [
        S.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/r",
                "OriginalPaperPubMedID": "11",
                "RetractionDOI": "10.5555/r.n",
            }
        ),
        S.row(**{"Record ID": "2", "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/c"}),
        S.row(
            **{
                "Record ID": "3",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/a",
                "OriginalPaperPubMedID": "77",
            }
        ),
        S.row(
            **{
                "Record ID": "4",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/b",
                "OriginalPaperPubMedID": "77",
            }
        ),
    ]
    return S.build_rows(
        tmp_path_factory.mktemp("schemas"),
        rows,
        [
            {
                "original": "10.5555/r",
                "updated_by": [{"DOI": "10.5555/r.n", "type": "retraction", "source": "publisher"}],
            }
        ],
    )


@pytest.mark.contracts
def test_rde_schemas_are_meta_valid_versioned_and_local() -> None:
    cs = load_contracts(S.REPO / "schemas" / "retraction")
    assert cs.meta_problems() == []
    files = sorted(RETRACTION_SCHEMAS.glob("*.schema.json"))
    assert len(files) == 8
    for path in files:
        schema = loads_strict(path.read_text(encoding="utf-8"))
        assert schema["$id"] == schemas.PREFIX + path.name.removesuffix(".schema.json")
        assert schema["x-citerift-version"] == "1.0.0"
        for ref in _refs(schema):
            assert ref.startswith(("#", "urn:citerift:schema:")), ref  # no remote resolution
    merged = schemas.contracts()
    assert "urn:citerift:schema:contracts:v1:investigation" in merged.schemas


def _refs(node: Any) -> list[str]:
    if isinstance(node, dict):
        return [v for k, v in node.items() if k == "$ref"] + [r for v in node.values() for r in _refs(v)]
    if isinstance(node, list):
        return [r for v in node for r in _refs(v)]
    return []


@pytest.mark.contracts
def test_rde_projection_reuses_v1_definitions() -> None:
    text = (RETRACTION_SCHEMAS / "common.schema.json").read_text(encoding="utf-8")
    assert "urn:citerift:schema:contracts:v1:investigation#/$defs/paper/properties/retraction_status" in text
    assert "urn:citerift:schema:contracts:v1:investigation#/$defs/paper/properties/retraction_date" in text


@pytest.mark.contracts
def test_rde_lookup_results_validate_and_project_into_v1(index: Path) -> None:
    for doi, pmid in [
        ("10.5555/r", None),
        ("10.5555/c", None),
        (None, "77"),
        ("10.5555/none", None),
        ("10.5555/r.n", None),
        ("bad", None),
    ]:
        out = lookup(index, doi, pmid)
        assert schemas.validate_lookup(out) == [], (doi, pmid)
        record = schemas.subject_projection(out, "2026-10-27T00:00:00Z")
        if out["lookup_state"] == "invalid_query":
            assert record is None
            continue
        assert record is not None
        assert schemas.validate(record, schemas.INVESTIGATION) == [], (doi, pmid)


@pytest.mark.contracts
def test_rde_events_validate_and_semantic_negatives(index: Path) -> None:
    with Index(index) as ix:
        rows = ix.conn.execute(f"SELECT {', '.join(EVENT_COLUMNS)} FROM event ORDER BY ordinal").fetchall()  # noqa: S608
    events = [event_from_row(r) for r in rows]
    for ev in events:
        assert schemas.validate_event_record(ev) == []
    ev = events[0]
    cases = {
        "EVENT_ID_MISMATCH": {"event_id": "ev-0000002"},
        "EVENT_TYPE_MISMATCH": {"event_type": "correction"},
        "ANCHOR_INCONSISTENT": {"anchor": "pmid:11"},
        "NOTICE_KEY_INCONSISTENT": {"notice_key": None},
        "ORIGINAL_YEAR_INCONSISTENT": {"original_year": 1999},
    }
    for code, change in cases.items():
        assert code in codes(schemas.validate_event_record({**ev, **change})), code
    swapped = copy.deepcopy(ev)
    swapped["notice_date"]["earliest"], swapped["notice_date"]["latest"] = "2016-01-02", "2015-01-02"
    assert "BOUNDS_DISORDERED" in codes(schemas.validate_event_record(swapped))
    same = {**ev, "notice_doi": ev["original_doi"], "notice_key": f"doi:{ev['original_doi']}"}
    assert "NOTICE_EQUALS_ORIGINAL" in codes(schemas.validate_event_record(same))
    assert schemas.validate_event_record({**ev, "extra": 1})  # closed shape


@pytest.mark.contracts
def test_rde_lookup_semantic_negatives(index: Path) -> None:
    good = lookup(index, "10.5555/r")
    matched_status = good["projection"]["retraction_status"]

    def mutate(fn: Any) -> set[str]:
        out = copy.deepcopy(good)
        fn(out)
        return codes(schemas.validate_lookup(out))

    assert mutate(lambda o: o["projection"]["basis"].update(model="x"))  # the schema closes the basis
    modelled = copy.deepcopy(good)
    modelled["projection"]["retraction_status"]["status"] = "model_inference"
    assert "MODEL_IN_FACT_PATH" in codes(schemas.lookup_semantics(modelled))  # and the semantic layer agrees
    assert "PAGE_ORDER" in mutate(lambda o: o["events"].insert(0, {**o["events"][0], "event_id": "ev-0000009"}))
    assert "DUPLICATE_ID" in mutate(lambda o: o["events"].append(o["events"][0]))
    assert "COUNT_INCONSISTENT" in mutate(lambda o: o.update(total_event_count=0))
    assert mutate(lambda o: o.update(lookup_state="notice_only"))
    notice_fact = copy.deepcopy(good)
    notice_fact["lookup_state"] = "notice_only"
    assert "FACT_WITHOUT_MATCH" in codes(schemas.lookup_semantics(notice_fact))
    none = lookup(index, "10.5555/none")
    bad = copy.deepcopy(none)
    bad["projection"]["retraction_date"] = {"status": "uncertain", "value": None, "reason": "x"}
    assert "DATE_WITHOUT_RETRACTION" in codes(schemas.validate_lookup(bad))
    absent = copy.deepcopy(good)
    absent["projection"]["retraction_status"] = {
        **matched_status,
        "status": "uncertain",
        "value": "not_found_in_checked_sources",
        "reason": "x",
    }
    absent["projection"]["retraction_status"].pop("provenance", None)
    absent["projection"]["retraction_date"] = None
    assert "ABSENCE_WITH_RECORDS" in codes(schemas.lookup_semantics(absent))
    amb = lookup(index, None, "77")
    assert amb["lookup_state"] == "ambiguous_identity"
    one = copy.deepcopy(amb)
    one["identity"]["candidate_groups"] = one["identity"]["candidate_groups"][:1]
    assert "AMBIGUITY_WITHOUT_GROUPS" in codes(schemas.validate_lookup(one))
    same_alt = copy.deepcopy(none)
    same_alt["projection"]["retraction_status"] = {
        "status": "conflicting",
        "value": None,
        "reason": "x",
        "alternatives": [{"value": "retracted", "provenance": []}, {"value": "retracted", "provenance": []}],
    }
    assert codes(schemas.validate_lookup(same_alt))  # alternatives must genuinely differ (schema or semantics)


@pytest.mark.contracts
def test_rde_tension_semantic_negatives(index: Path) -> None:
    with Index(index) as ix:
        rep = tension.report(ix.gather("10.5555/r"), ix.snapshot_id)
    assert schemas.validate_tension(rep) == []

    def mutate(fn: Any) -> set[str]:
        out = copy.deepcopy(rep)
        fn(out)
        return codes(schemas.validate_tension(out))

    assert mutate(lambda o: o["interventions"][0].update(changed_fields=["lookup_state"]))
    lying = copy.deepcopy(rep)
    lying["interventions"][0]["changed_fields"] = ["lookup_state"]
    assert "CHANGED_FIELDS_INCONSISTENT" in codes(schemas.tension_semantics(lying))
    assert "DANGLING_REFERENCE" in mutate(lambda o: o["source_pointers"].pop(0))
    assert "CONTROL_WITH_DIAGNOSTIC" in mutate(
        lambda o: o.update(diagnostic_classes=["control", "redistributed_support"])
    )
    assert mutate(lambda o: o["base"]["basis"].update(score=1))  # rejected by the schema
    scored = copy.deepcopy(rep)
    scored["note"] = {"score": 0.5}
    assert "SCORE_FORBIDDEN" in codes(schemas.tension_semantics(scored))  # and by the semantic layer
    excl = next(i for i, r in enumerate(rep["interventions"]) if r["intervention"] == "exclude_origin")
    assert mutate(lambda o: o["interventions"][excl].update(origins=["a", "b", "c"]))


@pytest.mark.negative
def test_rde_supersession_cycles_and_dangling_links_never_reinstate() -> None:
    def event(eid: str, typ: str, date: str) -> policy.TypedAssertion:
        return policy.TypedAssertion(
            assertion_id=f"{eid}/event_type",
            origin=policy.RW_ORIGIN,
            channel="rw-gitlab-csv",
            type=typ,
            notice_key=f"doi:10.5555/{eid}",
            anchor="doi:10.5555/o",
            source_ref={"source_id": "retraction-watch", "locator": eid},
            event_id=eid,
            notice_date=parse_rw_date(date, "notice_date"),
        )

    t = event("ev-0000001", "retracted", "3/12/2015 0:00")
    r = event("ev-0000002", "reinstated", "4/20/2016 0:00")

    def status(sup: tuple[tuple[str, str], ...]) -> tuple[str, Any]:
        es = policy.EvidenceSet("matched", "exact", "doi:10.5555/o", (t, r), ({"source_id": "retraction-watch"},), sup)
        s = policy.reduce(es)["retraction_status"]
        return s["status"], s["value"]

    assert status((("ev-0000002", "ev-0000001"),)) == ("verified_fact", "reinstated")
    assert status(()) == ("uncertain", None)
    assert status((("ev-0000002", "ev-0000404"),)) == ("uncertain", None)  # dangling target
    assert status((("ev-0000404", "ev-0000001"),)) == ("uncertain", None)  # dangling reinstatement
    assert status((("ev-0000001", "ev-0000002"), ("ev-0000002", "ev-0000001"))) == ("verified_fact", "reinstated")
    assert status((("ev-0000001", "ev-0000002"),)) == ("uncertain", None)  # backwards in time: not a supersession


@pytest.mark.security
def test_rde_duplicate_json_keys_rejected_everywhere(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        loads_strict('{"a": 1, "a": 2}')
    broken = tmp_path / "schemas" / "retraction" / "v1"
    broken.mkdir(parents=True)
    (broken / "x.schema.json").write_text('{"$id": "urn:x", "$id": "urn:y"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_contracts(tmp_path / "schemas" / "retraction")
    assert json.loads('{"a": 1, "a": 2}') == {"a": 2}  # why the strict loader is required
