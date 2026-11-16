"""Step 10: the production report, positive works, v1 projections, explanations and export (owner Step 10 items 3 to
14, 29 to 32).

Real cases are the previously exposed design bundles of SPEC S-7.4 (VS-1 MMR/Wakefield, VS-2/VS-3 Obokata, VS-4 an
expression of concern, VS-5 BCAS3), run through the production operations with every socket refused. The SYNTHETIC
cases (labeled) change copies of real deciding lookups to reach v1 mapping branches that no exposed bundle reaches (a
correction, distinct works sharing an identifier, non-uniform statuses and dates); they are inputs of the projection
function only and never pass through Stage 02.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import explanations, projections, report
from citerift.investigation import operations as ops
from citerift.investigation.adapters.assemble import make_assemble
from citerift.investigation.adapters.plan import STAGE04_IDENTITY
from citerift.investigation.canonical import canon, sha256_hex

pytestmark = pytest.mark.integration

WAKEFIELD = "doi:10.1016/s0140-6736(97)11096-0"
BCAS3_DOI = "10.1210/me.2006-0514"


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def index9(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return T.build_index9(tmp_path_factory.mktemp("rw9"))


@pytest.fixture(scope="module")
def ar(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("ar"), S8.AR_OBOKATA, index)


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


@pytest.fixture(scope="module")
def mmr(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("mmr"), S8.EN_MMR, index)


@pytest.fixture(scope="module")
def eoc(tmp_path_factory: pytest.TempPathFactory, index9: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("eoc"), T.EN_CONCERN, index9)


@pytest.fixture(scope="module")
def bcas3(tmp_path_factory: pytest.TempPathFactory, index9: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("bcas3"), T.AR_BCAS3, index9)


def _works(inv: T.Inv) -> list[dict[str, Any]]:
    m = inv.blob(inv.report_record()["report"])
    return [w for ref in m["components"]["positive_works"]["chunks"] for w in inv.blob(ref["chunk"])["items"]]


def _claims(inv: T.Inv) -> list[dict[str, Any]]:
    entries, _, _ = T.projection_inputs(inv)
    return [e["claim"] for e in entries]


def _anchor(body: dict[str, Any]) -> str:
    ids = body["subject_paper"]["identifiers"]
    return f"doi:{ids['doi']}" if "doi" in ids else f"pmid:{ids['pmid']}"


def _codes(body: dict[str, Any]) -> list[str]:
    return [t.split(":", 1)[0] for t in body["limitations"]]


# Positive works and v1 projections on real data --------------------------------------------------------------------


def test_every_body_is_valid_v1_and_the_store_names_one_per_positive_work(
    ar: T.Inv, en: T.Inv, mmr: T.Inv, eoc: T.Inv, bcas3: T.Inv
) -> None:
    for inv in (ar, en, mmr, eoc, bcas3):
        bodies = T.stored_bodies(inv)
        assert len(bodies) == len(_works(inv)) == inv.report_record()["projection_count"]
        for body in bodies:
            assert projections.body_problems(body) == []
            assert "created_at" not in body and body["schema_version"] == "1.0.1"
            assert body["status"] == inv.out["report"]["outcome"]
            record = projections.v1_record(body, "2026-11-16T00:00:00Z")
            assert projections.record_problems(record) == []
        # The stored bodies are exactly what the projection function gives for the committed content.
        entries, deciding, ctx = T.projection_inputs(inv)
        works, again = projections.build_bodies(entries, lambda c, d=deciding: d[c["claim_id"]], **ctx)
        assert works == _works(inv)
        assert (
            sorted(projections.digest(b) for b in again)
            == inv.blob(inv.report_record()["projection_set"])["projections"]
        )  # the set lists the digests in order; the bodies follow the works' order


def test_retracted_work_with_two_events_and_no_projection_for_the_notice(mmr: T.Inv) -> None:
    """VS-1: the Wakefield paper is one retracted work; the cited Lancet notice is NOTICE_CITED and never a work."""
    classes = {c["class"] for c in _claims(mmr)}
    assert "NOTICE_CITED" in classes
    works = _works(mmr)
    assert [w["classes"] for w in works] == [["RETRACTED_WORK_CITED"]]
    (body,) = T.stored_bodies(mmr)
    assert _anchor(body) == WAKEFIELD
    assert body["subject_paper"]["retraction_status"]["value"] == "retracted"
    assert body["subject_paper"]["identifiers"] == {"doi": WAKEFIELD[4:], "pmid": "9500320"}
    assert len(body["events"]) == 2 and [e["at"] for e in body["events"]] == sorted(e["at"] for e in body["events"])
    for e in body["events"]:
        assert e["at"].endswith("T00:00:00Z") and "00:00:00Z marks the day only" in e["description"]
    assert "V1_EVENT_DATE_IS_A_DAY" in _codes(body)
    notice = next(c for c in _claims(mmr) if c["class"] == "NOTICE_CITED")
    assert notice["claim_id"] not in {cid for w in works for cid in w["claim_ids"]}


def test_identity_conflict_and_not_found_have_no_projection(ar: T.Inv) -> None:
    """VS-2: the conflicting pair (D-6) and the not-found citation never form a work."""
    claims = _claims(ar)
    conflict = [c for c in claims if c["class"] == "IDENTITY_CONFLICT"]
    not_found = [c for c in claims if c["class"] == "NOT_FOUND_IN_CHECKED_SOURCES"]
    assert conflict and not_found
    placed = {cid for w in _works(ar) for cid in w["claim_ids"]}
    assert not placed & {c["claim_id"] for c in conflict + not_found}
    (body,) = T.stored_bodies(ar)
    assert body["subject_paper"]["retraction_status"]["value"] == "retracted"
    assert body["status"] == "partial" and any(t.startswith("OPEN_QUESTIONS:") for t in body["limitations"])


def test_two_distinct_works(en: T.Inv) -> None:
    """VS-3: two positive claims of two Stage 02 works are two works and two records."""
    works = _works(en)
    assert len(works) == 2 and len({canon(w["work"]) for w in works}) == 2
    bodies = T.stored_bodies(en)
    assert {_anchor(b) for b in bodies} == {f"{k}:{v}" for w in works for k, v in w["work"].items()}
    assert all(len(b["citations"]) == 1 for b in bodies)


def test_expression_of_concern_is_a_concern_record(eoc: T.Inv) -> None:
    """VS-4: one CONCERN_CITED work; its v1 status is expression_of_concern, never retracted."""
    assert [w["classes"] for w in _works(eoc)] == [["CONCERN_CITED"]]
    (body,) = T.stored_bodies(eoc)
    assert body["subject_paper"]["retraction_status"]["value"] == "expression_of_concern"
    assert "retracted" not in json.dumps(body["subject_paper"]["retraction_status"])


def test_one_work_cited_by_two_units_is_one_record_with_two_citations(bcas3: T.Inv) -> None:
    """VS-5: the BCAS3 paper is cited by two units; one work, both claim ids, one record with two citations."""
    (work,) = _works(bcas3)
    assert work["work"] == {"doi": BCAS3_DOI} and len(work["claim_ids"]) == 2
    (body,) = T.stored_bodies(bcas3)
    assert len(body["citations"]) == 2 and len({c["citation_id"] for c in body["citations"]}) == 2
    assert body["events"] == [] and "V1_EVENTS_WITHOUT_DAY_OMITTED" in _codes(body)
    assert any("2 Stage 02 event(s)" in t for t in body["limitations"])


def test_no_title_or_article_text_in_citation_ids(ar: T.Inv, en: T.Inv, bcas3: T.Inv) -> None:
    for inv in (ar, en, bcas3):
        for body in T.stored_bodies(inv):
            for c in body["citations"]:
                assert re.fullmatch(r"(ar|en):\d+:un-\d{5}:[0-9a-f]{16}", c["citation_id"]), c["citation_id"]


def test_lookup_unavailable_has_no_projection(tmp_path: Path, index: Path) -> None:
    """A lookup evidence budget too small for the lookups: LOOKUP_UNAVAILABLE claims, no projection for them."""
    inv = T.Inv(tmp_path, S8.EN_OBOKATA, index, budget=1024)
    claims = _claims(inv)
    unavailable = [c for c in claims if c["class"] == "LOOKUP_UNAVAILABLE"]
    assert unavailable, sorted({c["class"] for c in claims})
    assert inv.code == 6 and inv.out["report"]["outcome"] == "partial"
    placed = {cid for w in _works(inv) for cid in w["claim_ids"]}
    assert not placed & {c["claim_id"] for c in unavailable}
    assert len(T.stored_bodies(inv)) == len(_works(inv))


# Determinism (owner items 13, 30) ----------------------------------------------------------------------------------


def _digests(inv: T.Inv) -> tuple[str, str, str]:
    _code, value = T.run_json("verify", "--memory-root", inv.root, "--key", inv.key)
    rec = inv.report_record()
    return rec["report"], rec["projection_set"], value["result"]["content_digest"]


def test_two_independent_runs_give_the_same_digests(ar: T.Inv, tmp_path: Path) -> None:
    again = T.Inv(tmp_path, S8.AR_OBOKATA, Path(ar.request["index_path"]))
    assert again.key == ar.key
    assert _digests(again) == _digests(ar)
    assert canon(T.stored_bodies(again)) == canon(T.stored_bodies(ar))


def _reorder(committed: tuple[dict[str, Any], ...], kinds: set[str]) -> tuple[dict[str, Any], ...]:
    """For each kind in ``kinds``, its records in reversed order, put back at the positions that kind held."""
    out = list(committed)
    for kind in kinds:
        at = [i for i, r in enumerate(committed) if r["kind"] == kind]
        for i, j in zip(at, reversed(at), strict=True):
            out[i] = committed[j]
    return tuple(out)


@pytest.mark.parametrize("inv_name", ["ar", "mmr", "bcas3"])
def test_assemble_does_not_depend_on_in_memory_record_order(inv_name: str, request: pytest.FixtureRequest) -> None:
    inv: T.Inv = request.getfixturevalue(inv_name)
    assemble = make_assemble(STAGE04_IDENTITY)
    with ops.opened(inv.root, inv.key) as mem:
        req = ops.readonly_request(mem, "ASSEMBLE")
        base = tuple(r for r in req.committed if r["kind"] != "report_recorded")
        kinds = {"claim_recorded", "decision_recorded", "question_opened"}
        reordered = _reorder(base, kinds)
        assert [r["kind"] for r in reordered] == [r["kind"] for r in base] and reordered != base
        results = []
        for committed in (base, reordered):
            out = assemble(replace(req, committed=committed))
            results.append((out.records[0].payload, sorted(sha256_hex(canon(b)) for b in out.blobs)))
    assert results[0] == results[1]
    assert results[0][0] == inv.report_record()


def test_projection_function_ignores_input_order(bcas3: T.Inv, mmr: T.Inv) -> None:
    for inv in (bcas3, mmr):
        entries, deciding, ctx = T.projection_inputs(inv)
        flipped = {k: {**copy.deepcopy(v), "events": list(reversed(v["events"]))} for k, v in deciding.items()}
        a = projections.build_bodies(entries, lambda c, d=deciding: d[c["claim_id"]], **ctx)
        b = projections.build_bodies(list(reversed(entries)), lambda c, d=flipped: d[c["claim_id"]], **ctx)
        assert canon(a) == canon(b)


# Explanations, summary and limitations (owner items 9 to 11, 32) ---------------------------------------------------

FORBIDDEN = re.compile(r"\b(clean|safe|not retracted|no retracted citations|never retracted)\b", re.IGNORECASE)


def _texts(inv: T.Inv) -> tuple[list[dict[str, Any]], str, list[dict[str, str]]]:
    _code, value = T.run_json("show", "--memory-root", inv.root, "--key", inv.key, "--claims")
    rep = value["result"]["report"]
    return rep["claims"], rep["summary"], rep["limitations"]


def test_mandatory_wording_and_no_forbidden_words(ar: T.Inv, mmr: T.Inv, en: T.Inv, eoc: T.Inv) -> None:
    seen: dict[str, list[str]] = {}
    for inv in (ar, mmr, en, eoc):
        claims, summary, limits = _texts(inv)
        for c in claims:
            seen.setdefault(c["class"], []).append(c["text"])
            assert not FORBIDDEN.search(c["text"] + " " + c["chain"]), c
        assert not FORBIDDEN.search(summary)
        assert not any(FORBIDDEN.search(lim["text"]) for lim in limits)
    assert all(explanations.NOT_FOUND_SENTENCE in t for t in seen["NOT_FOUND_IN_CHECKED_SOURCES"])
    assert all(explanations.NOTICE_SENTENCE in t for t in seen["NOTICE_CITED"])
    assert all(explanations.IDENTITY_CONFLICT_SENTENCE in t for t in seen["IDENTITY_CONFLICT"])
    assert explanations.NOT_FOUND_SENTENCE == "No matching record was found in the checked sources."
    # Templates: no forbidden phrase anywhere, in any template or reason text.
    for text in [*explanations.CLAIM_TEMPLATES.values(), *explanations.REASON_TEXT.values(),
                 *explanations.LIMITATION_TEMPLATES.values(), *projections.LOSSY.values()]:  # fmt: skip
        assert not FORBIDDEN.search(str(text)), text


def test_lookup_unavailable_wording(tmp_path: Path, index: Path) -> None:
    inv = T.Inv(tmp_path, S8.EN_OBOKATA, index, budget=1024)
    claims, _, limits = _texts(inv)
    texts = [c["text"] for c in claims if c["class"] == "LOOKUP_UNAVAILABLE"]
    assert texts and all(explanations.UNAVAILABLE_SENTENCE in t for t in texts)
    assert "LOOKUP_EVIDENCE_BUDGET_REFUSED" in [lim["code"] for lim in limits]
    assert "LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES" in [lim["code"] for lim in limits]


def test_explanations_name_the_rule_and_the_evidence(ar: T.Inv) -> None:
    claims, _, _ = _texts(ar)
    entries, _, _ = T.projection_inputs(ar)
    by_id = {e["claim"]["claim_id"]: e for e in entries}
    for c in claims:
        e = by_id[c["claim_id"]]
        assert c["rule"] == e["claim"]["rule"] and e["claim"]["evidence_set"] in c["chain"]
        assert e["unit"]["unit_span_sha256"] in c["chain"]
    kinds = {c["class"]: c["kind"] for c in claims}
    assert kinds["RETRACTED_WORK_CITED"] == "finding" and kinds["NOT_FOUND_IN_CHECKED_SOURCES"] == "not_found"
    assert kinds["IDENTITY_CONFLICT"] == "identity_conflict" and kinds["NO_IDENTIFIER"] == "out_of_scope"


def test_explanations_are_byte_identical_across_runs(ar: T.Inv, tmp_path: Path) -> None:
    again = T.Inv(tmp_path, S8.AR_OBOKATA, Path(ar.request["index_path"]))
    assert canon(_texts(again)) == canon(_texts(ar))


def _manifest(classes: dict[str, int], **extra: Any) -> dict[str, Any]:
    return {
        "outcome": "completed",
        "terminal_state": "COMPLETED",
        "limitations": ["CHECKED_SOURCES_ONLY"],
        "article_summary": {"claims_by_class": classes, "open_questions": 0, "snapshot_id": "rw-0123456789abcdef"},
        "identities": {"config": {"lookup_evidence_budget_bytes": 1 << 24}},
        **extra,
    }


def test_summary_scoped_statement_only_when_everything_is_not_found() -> None:
    only = explanations.summary_statement(_manifest({"NOT_FOUND_IN_CHECKED_SOURCES": 3, "NO_IDENTIFIER": 9}), 0)
    assert "no matching record was found in the checked sources (snapshot rw-0123456789abcdef)" in only
    assert not FORBIDDEN.search(only)
    mixed = explanations.summary_statement(_manifest({"NOT_FOUND_IN_CHECKED_SOURCES": 3, "RETRACTED_WORK_CITED": 1}), 1)
    assert "no matching record was found in the checked sources (snapshot" not in mixed
    none = explanations.summary_statement(_manifest({"NO_IDENTIFIER": 4}), 0)
    assert "no matching record was found in the checked sources (snapshot" not in none
    for text in (only, mixed, none):
        assert not FORBIDDEN.search(text)


# Export (owner items 14, 15) ---------------------------------------------------------------------------------------


def test_export_is_a_bounded_directory_derived_from_the_graph(mmr: T.Inv, tmp_path: Path) -> None:
    out = tmp_path / "export"
    with T.offline():
        code, _value = T.run_json("export", "--memory-root", mmr.root, "--key", mmr.key, "--out", out)
    assert code == 6
    manifest = json.loads((out / "export.json").read_bytes())
    files = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert files == {f["path"] for f in manifest["files"]} | {"export.json"}
    for f in manifest["files"]:
        data = (out / f["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == f["sha256"] and len(data) == f["bytes"]
        assert re.fullmatch(r"(report|evidence|observations|explanations|v1)/[0-9a-f]{64}\.json|projection_set\.json",
                            f["path"]), f["path"]  # fmt: skip
    rec = mmr.report_record()
    assert manifest["report"] == rec["report"] and manifest["projection_set"] == rec["projection_set"]
    assert (out / "report" / f"{rec['report']}.json").read_bytes() == (mmr.dir / "blobs" / rec["report"]).read_bytes()
    created = mmr.records()[0]["at"]
    for path in sorted((out / "v1").iterdir()):
        record = json.loads(path.read_bytes())
        assert record["created_at"] == created and projections.record_problems(record) == []
        body = {k: v for k, v in record.items() if k != "created_at"}
        assert projections.digest(body) == path.stem
    assert manifest["summary"] and manifest["limitations"] and "authoritative" in manifest
    assert not [p for p in out.rglob("*") if p.suffix in (".html", ".wikitext", ".txt")]


# SYNTHETIC: projection mapping branches (labeled; copies of real lookups changed in memory) ------------------------


Change = Callable[[list[dict[str, Any]], dict[str, dict[str, Any]]], None]


def _synthetic(inv: T.Inv, change: Change) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries, deciding, ctx = T.projection_inputs(inv)
    entries, deciding = copy.deepcopy(entries), copy.deepcopy(deciding)
    change(entries, deciding)
    return projections.build_bodies(entries, lambda c: deciding[c["claim_id"]], **ctx)


def _positive(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in entries if e["claim"]["class"] in report.POSITIVE]


def _day(obs: dict[str, Any], day: str = "2014-07-01") -> None:
    for ev in obs["events"]:
        ev["notice_date"] = {**ev["notice_date"], "effective_precision": "day", "earliest": day, "latest": day}


def test_synthetic_correction_record(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        for e in _positive(entries):
            e["claim"]["class"] = "CORRECTION_CITED"
            deciding[e["claim"]["claim_id"]]["result"]["projection"]["retraction_status"]["value"] = "correction"

    works, bodies = _synthetic(bcas3, change)
    assert [w["classes"] for w in works] == [["CORRECTION_CITED"]]
    assert bodies[0]["subject_paper"]["retraction_status"]["value"] == "correction"
    assert projections.body_problems(bodies[0]) == []


def test_synthetic_distinct_anchors_sharing_an_identifier_are_two_works(bcas3: T.Inv) -> None:
    """Two Stage 02 anchors are two works even when one's events name the other's identifier (never merged)."""

    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        second = _positive(entries)[1]["claim"]["claim_id"]
        deciding[second]["result"]["identity"]["anchor"] = "pmid:17505058"

    works, bodies = _synthetic(bcas3, change)
    assert [w["work"] for w in works] == [{"doi": BCAS3_DOI}, {"pmid": "17505058"}]
    assert [len(w["claim_ids"]) for w in works] == [1, 1]
    assert [b["subject_paper"]["identifiers"] for b in bodies] == [{"doi": BCAS3_DOI, "pmid": "17505058"},
                                                                   {"pmid": "17505058"}]  # fmt: skip
    assert all(projections.body_problems(b) == [] for b in bodies)


def test_synthetic_events_are_deduplicated_and_dated_by_day(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        for obs in deciding.values():
            _day(obs)

    _, (body,) = _synthetic(bcas3, change)
    assert len(body["events"]) == 2  # two lookups, the same two events: not four
    assert [e["kind"] for e in body["events"]] == ["retracted", "correction"]  # by time, then event id
    assert all(e["at"] == "2014-07-01T00:00:00Z" for e in body["events"])
    assert "V1_EVENT_DATE_IS_A_DAY" in _codes(body) and "V1_EVENTS_WITHOUT_DAY_OMITTED" not in _codes(body)
    assert projections.body_problems(body) == []


def test_synthetic_status_not_uniform_is_uncertain_never_conflicting(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        second = _positive(entries)[1]["claim"]["claim_id"]
        deciding[second]["result"]["projection"]["retraction_status"]["value"] = "expression_of_concern"

    _, (body,) = _synthetic(bcas3, change)
    status = body["subject_paper"]["retraction_status"]
    assert status["status"] == "uncertain" and status["value"] is None and "reason" in status
    assert "V1_STATUS_NOT_UNIFORM" in _codes(body) and projections.body_problems(body) == []


def test_synthetic_same_status_other_provenance_is_merged(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        second = _positive(entries)[1]["claim"]["claim_id"]
        prov = deciding[second]["result"]["projection"]["retraction_status"]["provenance"]
        prov[0] = {**prov[0], "locator": prov[0]["locator"] + "-synthetic"}

    _, (body,) = _synthetic(bcas3, change)
    status = body["subject_paper"]["retraction_status"]
    assert status["value"] == "retracted" and len(status["provenance"]) == 2
    assert "V1_STATUS_NOT_UNIFORM" not in _codes(body)


def test_synthetic_date_not_uniform_is_omitted(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        second = _positive(entries)[1]["claim"]["claim_id"]
        date = deciding[second]["result"]["projection"]["retraction_date"]
        deciding[second]["result"]["projection"]["retraction_date"] = {**date, "value": "2014-07-02"}

    _, (body,) = _synthetic(bcas3, change)
    assert "retraction_date" not in body["subject_paper"] and "V1_DATE_NOT_UNIFORM" in _codes(body)


def test_synthetic_second_identifier_not_unique_keeps_the_anchor_only(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        for obs in deciding.values():
            obs["events"][1]["original_pmid"] = "1"

    _, (body,) = _synthetic(bcas3, change)
    assert body["subject_paper"]["identifiers"] == {"doi": BCAS3_DOI}
    assert "V1_SECOND_IDENTIFIER_NOT_UNIQUE" in _codes(body)


def test_synthetic_source_marks_the_record_synthetic(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        for obs in deciding.values():
            obs["result"]["checked_sources"][0]["synthetic"] = True

    _, (body,) = _synthetic(bcas3, change)
    assert body["synthetic"] is True
    assert "synthetic" not in T.stored_bodies(bcas3)[0]


@pytest.mark.parametrize("anchor", [None, "", "isbn:123", "doi:", "doi"])
def test_synthetic_positive_claim_without_a_stage02_anchor_fails_closed(bcas3: T.Inv, anchor: Any) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        for obs in deciding.values():
            obs["result"]["identity"]["anchor"] = anchor

    with pytest.raises(projections.ProjectionError):
        _synthetic(bcas3, change)


def test_synthetic_one_event_two_contents_fails_closed(bcas3: T.Inv) -> None:
    def change(entries: list[dict[str, Any]], deciding: dict[str, dict[str, Any]]) -> None:
        second = _positive(entries)[1]["claim"]["claim_id"]
        deciding[second]["events"][0]["journal"] = "Another Journal"

    with pytest.raises(projections.ProjectionError, match="differs between lookups"):
        _synthetic(bcas3, change)


def test_created_at_never_enters_a_stored_body(bcas3: T.Inv) -> None:
    body = T.stored_bodies(bcas3)[0]
    with pytest.raises(projections.ProjectionError):
        projections.v1_record({**body, "created_at": "2026-11-16T00:00:00Z"}, "2026-11-16T00:00:00Z")
    assert projections.body_problems({**body, "created_at": "2026-11-16T00:00:00Z"})
    record = projections.v1_record(body, "2026-11-16T00:00:00Z")
    assert record["created_at"] == "2026-11-16T00:00:00Z" and "created_at" not in body


def test_claim_chunking_does_not_change_projection_identity(
    ar: T.Inv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a lowered part ceiling the claims fall into several chunks and batches; the projections and the
    projection set are the same (they depend on the claims, not on how the report is cut)."""
    from citerift.investigation import batches

    monkeypatch.setattr(batches, "MAX_PART_BYTES", 2000)
    small = T.Inv(tmp_path, S8.AR_OBOKATA, Path(ar.request["index_path"]))
    m = small.blob(small.report_record()["report"])
    assert len(m["components"]["claims"]["chunks"]) > 1
    assert small.report_record()["report"] != ar.report_record()["report"]
    assert small.report_record()["projection_set"] == ar.report_record()["projection_set"]
    assert canon(T.stored_bodies(small)) == canon(T.stored_bodies(ar))
