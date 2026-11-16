"""Step 10: a corrupted or forged report fails closed through the operations (owner Step 10 items 7, 15, 27, 28).

Each case changes a verified investigation's stored report as an adversary with write access to the memory root could:
blob bytes, or a forged report whose hash chain is recomputed and whose verified content digest is re-sealed to
``C(J)`` whenever Memory still opens it (``step10_support.forge_report``). Every case must end in ``corrupt`` (the
journal or the D-054 graph does not open) or ``verify_failed`` (it opens, and a named VERIFY check fails), never in
``passed``; ``export`` writes nothing; ``replay`` does not report ``reproduced``.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import projections, report, sets

pytestmark = pytest.mark.integration

Put = Callable[[Any], str]


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def pristine(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    inv = T.Inv(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)
    assert inv.code == 0 and inv.out["report"]["positive_works"] == 2
    return inv


@pytest.fixture
def inv(pristine: T.Inv, tmp_path: Path) -> T.Inv:
    return pristine.copy(tmp_path)


def _args(inv: T.Inv) -> list[str | Path]:
    return ["--memory-root", inv.root, "--key", inv.key]


def _manifest(inv: T.Inv) -> dict[str, Any]:
    return dict(inv.blob(inv.report_record()["report"]))


def _fails_closed(inv: T.Inv, tmp_path: Path, expected: str, check: str | None = None) -> dict[str, Any]:
    """verify, export and replay of the damaged investigation; returns the verify result."""
    code, value = T.run_json("verify", *_args(inv))
    result = value["result"]
    assert result["result"] != "passed"
    if expected == "corrupt":
        assert code == 12 and result["result"] == "corrupt", result
    else:
        assert code == 5 and result["result"] == "failed", result
        failed = [c["check"] for c in result["checks"] if not c["passed"]]
        assert check in failed, failed
    out = tmp_path / "export"
    code, value = T.run_json("export", *_args(inv), "--out", out)
    assert code in (5, 12) and value["error"]["code"] == "EXPORT_REFUSED" and not out.exists()
    code, value = T.run_json("replay", *_args(inv))
    assert code in (5, 12)
    assert "result" not in value or value["result"]["result"] != "reproduced"
    return result


# Blob damage: Memory refuses the journal on open -----------------------------------------------------------------


def _chunk(inv: T.Inv, part: str) -> Path:
    return inv.dir / "blobs" / _manifest(inv)["components"][part]["chunks"][0]["chunk"]


@pytest.mark.parametrize(
    "target",
    ["claims chunk", "positive works chunk", "observations chunk", "report manifest", "projection set",
     "projection body", "evidence batch"],
)  # fmt: skip
@pytest.mark.parametrize("how", ["missing", "changed"])
def test_damaged_blob_is_corrupt(inv: T.Inv, tmp_path: Path, target: str, how: str) -> None:
    rec = inv.report_record()
    path = {
        "claims chunk": lambda: _chunk(inv, "claims"),
        "positive works chunk": lambda: _chunk(inv, "positive_works"),
        "observations chunk": lambda: _chunk(inv, "observations"),
        "report manifest": lambda: inv.dir / "blobs" / rec["report"],
        "projection set": lambda: inv.dir / "blobs" / rec["projection_set"],
        "projection body": lambda: inv.dir / "blobs" / inv.blob(rec["projection_set"])["projections"][0],
        "evidence batch": lambda: inv.dir / "blobs" / _manifest(inv)["components"]["evidence"]["batches"][0]["batch"],
    }[target]()
    if how == "missing":
        path.chmod(0o644)
        path.unlink()
    else:
        T.flip(path)
    _fails_closed(inv, tmp_path, "corrupt")


# Forged graphs that D-054 refuses on open ------------------------------------------------------------------------


def _items(inv: T.Inv, m: dict[str, Any], part: str) -> list[Any]:
    return [i for ref in m["components"][part]["chunks"] for i in inv.blob(ref["chunk"])["items"]]


def _set_items(m: dict[str, Any], part: str, items: list[Any], put: Put) -> None:
    m["components"][part]["chunks"] = [{"chunk": put(report.chunk(part, items)), "count": len(items)}]
    m["components"][part]["count"] = len(items)


def _graph_forgeries(inv: T.Inv) -> dict[str, Callable[[dict[str, Any], Put], None]]:
    def reorder(m: dict[str, Any], put: Put) -> None:
        _set_items(m, "claims", list(reversed(_items(inv, m, "claims"))), put)

    def drop_claim(m: dict[str, Any], put: Put) -> None:
        items = _items(inv, m, "claims")
        gone = next(e for e in items if e["claim"]["class"] == "NOT_FOUND_IN_CHECKED_SOURCES")
        items.remove(gone)
        _set_items(m, "claims", items, put)
        cls = m["article_summary"]["claims_by_class"]
        cls["NOT_FOUND_IN_CHECKED_SOURCES"] -= 1
        if not cls["NOT_FOUND_IN_CHECKED_SOURCES"]:
            del cls["NOT_FOUND_IN_CHECKED_SOURCES"]

    def duplicate_chunk(m: dict[str, Any], put: Put) -> None:
        c = m["components"]["claims"]
        c["chunks"] = [c["chunks"][0], dict(c["chunks"][0])]
        c["count"] *= 2

    def wrong_chunk_digest(m: dict[str, Any], put: Put) -> None:
        m["components"]["claims"]["chunks"][0]["chunk"] = m["components"]["observations"]["chunks"][0]["chunk"]

    def changed_claim(m: dict[str, Any], put: Put) -> None:
        items = _items(inv, m, "claims")
        e = next(e for e in items if e["claim"]["class"] == "NOT_FOUND_IN_CHECKED_SOURCES")
        e["claim"]["reasons"] = []
        _set_items(m, "claims", items, put)

    def changed_decision(m: dict[str, Any], put: Put) -> None:
        items = _items(inv, m, "claims")
        items[0]["decision"]["disposition"] = "REPORT_FINDING"
        _set_items(m, "claims", items, put)

    def chunk_count(m: dict[str, Any], put: Put) -> None:
        m["components"]["claims"]["chunks"][0]["count"] += 1

    def total_count(m: dict[str, Any], put: Put) -> None:
        m["components"]["observations"]["count"] += 1

    def summary_counts(m: dict[str, Any], put: Put) -> None:
        m["article_summary"]["claims_by_class"]["RETRACTED_WORK_CITED"] += 1

    def missing_batch(m: dict[str, Any], put: Put) -> None:
        ev = m["components"]["evidence"]
        ev["batches"].pop()
        ev["count"] = sum(b["count"] for b in ev["batches"])

    def batch_count(m: dict[str, Any], put: Put) -> None:
        ev = m["components"]["evidence"]
        ev["batches"][0]["count"] += 1
        ev["count"] += 1

    def reordered_observations(m: dict[str, Any], put: Put) -> None:
        _set_items(m, "observations", list(reversed(_items(inv, m, "observations"))), put)

    def positive_claim_dropped(m: dict[str, Any], put: Put) -> None:
        works = _items(inv, m, "positive_works")
        _set_items(m, "positive_works", works[1:], put)

    def positive_works_duplicated(m: dict[str, Any], put: Put) -> None:
        works = _items(inv, m, "positive_works")
        _set_items(m, "positive_works", [works[0], works[0], *works[1:]], put)

    def wrong_class(m: dict[str, Any], put: Put) -> None:
        works = _items(inv, m, "positive_works")
        works[0]["classes"] = ["CONCERN_CITED"]
        _set_items(m, "positive_works", works, put)

    return {
        "claims reordered": reorder,
        "claim missing": drop_claim,
        "claims chunk duplicated": duplicate_chunk,
        "wrong chunk digest": wrong_chunk_digest,
        "claim changed": changed_claim,
        "decision changed": changed_decision,
        "wrong chunk count": chunk_count,
        "wrong total count": total_count,
        "summary does not count the claims": summary_counts,
        "evidence batch missing": missing_batch,
        "wrong batch count": batch_count,
        "observations reordered": reordered_observations,
        "positive claim in no work": positive_claim_dropped,
        "positive work listed twice": positive_works_duplicated,
        "positive work with a wrong class": wrong_class,
        "another investigation key": lambda m, put: m.__setitem__("investigation_key", "e" * 64),
        "another investigation id": lambda m, put: m.__setitem__("investigation_id", "00000000-0000-8000-8000-0000"),
        "another root": lambda m, put: m["root"]["subject"]["identity"].__setitem__("revision_id", 1),
    }


GRAPH = [
    "claims reordered", "claim missing", "claims chunk duplicated", "wrong chunk digest", "claim changed",
    "decision changed", "wrong chunk count", "wrong total count", "summary does not count the claims",
    "evidence batch missing", "wrong batch count", "observations reordered", "positive claim in no work",
    "positive work listed twice", "positive work with a wrong class", "another investigation key",
    "another investigation id", "another root",
]  # fmt: skip


@pytest.mark.parametrize("name", GRAPH)
def test_forged_report_graph_is_corrupt(inv: T.Inv, tmp_path: Path, name: str) -> None:
    resealed = T.forge_report(inv.root, inv.key, manifest=_graph_forgeries(inv)[name])
    assert not resealed  # Memory refuses the forged report before anything else
    _fails_closed(inv, tmp_path, "corrupt")


# Forged reports that open: a named VERIFY check fails -------------------------------------------------------------


def _split_work(inv: T.Inv) -> Callable[[dict[str, Any], Put], None]:
    """Both positive claims under one work (a graph-valid list that is not the Stage 02 identity grouping)."""

    def change(m: dict[str, Any], put: Put) -> None:
        works = _items(inv, m, "positive_works")
        merged = {
            "work": works[0]["work"],
            "classes": sorted({c for w in works for c in w["classes"]}),
            "claim_ids": sorted(c for w in works for c in w["claim_ids"]),
        }
        _set_items(m, "positive_works", [merged], put)

    return change


def _other_identity(inv: T.Inv) -> Callable[[dict[str, Any], Put], None]:
    def change(m: dict[str, Any], put: Put) -> None:
        works = _items(inv, m, "positive_works")
        works[0]["work"] = {"doi": "10.9999/not-the-stage02-work"}
        _set_items(m, "positive_works", sorted(works, key=report.work_key), put)

    return change


SUMMARY = {
    "limitations dropped": lambda m, put: m.__setitem__("limitations", ["CHECKED_SOURCES_ONLY"]),
    "snapshot": lambda m, put: m["article_summary"].__setitem__("snapshot_id", "rw-0000000000000000"),
    "identities": lambda m, put: m["identities"]["config"].__setitem__("lookup_evidence_budget_bytes", 1),
}


def test_schema_invalid_summary_is_corrupt(inv: T.Inv, tmp_path: Path) -> None:
    """A summary the report schema refuses (a partial outcome without its cause, S-9.7; a snapshot id of another form)
    never opens."""
    for change in (
        lambda m, put: m.__setitem__("outcome", "partial"),
        lambda m, put: m["article_summary"].__setitem__("snapshot_id", "another-snapshot"),
    ):
        copy_ = inv.copy(tmp_path / str(id(change)))
        assert not T.forge_report(copy_.root, copy_.key, manifest=change)
        _fails_closed(copy_, tmp_path / str(id(change)), "corrupt")


@pytest.mark.parametrize("name", ["works merged", "work identity replaced", *SUMMARY])
def test_forged_report_that_opens_fails_assemble_replay(inv: T.Inv, tmp_path: Path, name: str) -> None:
    change = {"works merged": _split_work(inv), "work identity replaced": _other_identity(inv), **SUMMARY}[name]
    resealed = T.forge_report(inv.root, inv.key, manifest=change)
    assert resealed, "Memory opens the forged report; VERIFY must refuse it"
    result = _fails_closed(inv, tmp_path, "verify_failed", "ASSEMBLE_REPLAY")
    assert next(c for c in result["checks"] if c["check"] == "COMMITTED_VERIFICATION")["passed"]


def _projection_forgeries(inv: T.Inv) -> dict[str, Callable[[dict[str, Any], Put], None]]:
    def drop_one(p: dict[str, Any], put: Put) -> None:
        bodies = inv.blob(p["projection_set"])["projections"]
        p["projection_set"] = put(sets.projection_set(bodies[1:]))
        p["projection_count"] = 1

    def other_body(p: dict[str, Any], put: Put) -> None:
        bodies = inv.blob(p["projection_set"])["projections"]
        body = copy.deepcopy(inv.blob(bodies[0]))
        body["subject_paper"]["retraction_status"] = {"status": "uncertain", "value": None, "reason": "forged"}
        assert not projections.body_problems(body)  # a valid v1 body, just not the one the fold gives
        p["projection_set"] = put(sets.projection_set([put(body), *bodies[1:]]))

    def invalid_body(p: dict[str, Any], put: Put) -> None:
        bodies = inv.blob(p["projection_set"])["projections"]
        body = copy.deepcopy(inv.blob(bodies[0]))
        body["schema_version"] = "9.9.9"
        p["projection_set"] = put(sets.projection_set([put(body), *bodies[1:]]))

    def body_with_created_at(p: dict[str, Any], put: Put) -> None:
        bodies = inv.blob(p["projection_set"])["projections"]
        body = {**inv.blob(bodies[0]), "created_at": "2026-11-16T00:00:00Z"}
        p["projection_set"] = put(sets.projection_set([put(body), *bodies[1:]]))

    return {
        "projection missing from the set": drop_one,
        "projection replaced by another valid body": other_body,
        "projection body invalid against v1": invalid_body,
        "projection body holds created_at": body_with_created_at,
    }


@pytest.mark.parametrize(
    "name",
    ["projection missing from the set", "projection replaced by another valid body",
     "projection body invalid against v1", "projection body holds created_at"],
)  # fmt: skip
def test_forged_projection_set_fails_v1_projections(inv: T.Inv, tmp_path: Path, name: str) -> None:
    resealed = T.forge_report(inv.root, inv.key, payload=_projection_forgeries(inv)[name])
    assert resealed
    _fails_closed(inv, tmp_path, "verify_failed", "V1_PROJECTIONS")


def test_projection_count_that_is_not_the_set_is_corrupt(inv: T.Inv, tmp_path: Path) -> None:
    resealed = T.forge_report(inv.root, inv.key, payload=lambda p, put: p.__setitem__("projection_count", 3))
    assert not resealed
    _fails_closed(inv, tmp_path, "corrupt")


def test_the_pristine_copy_passes(inv: T.Inv, tmp_path: Path) -> None:
    """Control: the copy itself verifies, exports and replays (the damage above is what fails)."""
    code, value = T.run_json("verify", *_args(inv))
    assert code == 0 and value["result"]["result"] == "passed"
    assert T.run_json("export", *_args(inv), "--out", tmp_path / "export")[0] == 0
    code, value = T.run_json("replay", *_args(inv))
    assert code == 0 and value["result"]["result"] == "reproduced"


def test_a_resealed_forgery_without_changes_still_passes(inv: T.Inv) -> None:
    """Control for the forging helper: re-sealing an unchanged report gives a journal that verifies."""
    assert T.forge_report(inv.root, inv.key)
    code, value = T.run_json("verify", *_args(inv))
    assert code == 0 and value["result"]["result"] == "passed"
