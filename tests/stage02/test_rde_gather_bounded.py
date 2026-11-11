"""Maintenance A-02-001 (owner decision D-048): ``Index.gather_bounded``, the byte-bounded lookup Stage 04 needs.

The facility is backward compatible: ``gather`` is unchanged (proved structurally against the accepted Stage 02
module and behaviourally on every Stage 02 simulation case), within the budget the result is that of ``gather``, and
over the budget the lookup raises ``EvidenceBudgetExceeded`` before the rows that would exceed it are read, never
returning a truncated result.
"""

from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import query
from citerift.retraction.query import EvidenceBudgetExceeded, Index, QueryError

QUERY_PY = Path(query.__file__)

# ast.unparse of src/citerift/retraction/query.py at the accepted Stage 02 baseline cf06083 (file sha256
# 0b1b74ed7b070555e3b89f2d687c267d89e5b72b9bd5f7bd108ff9ddbfacd9e3). ast.unparse differs between Python versions,
# so each supported version has its digest.
ACCEPTED_UNPARSE_SHA256 = {
    (3, 12): "5e1f67b9d591ab4ff6827390b0bc84eac322d001cfd4b4d8bec7932d4439852d",
    (3, 13): "003045b81007bbd7c84c18e52f7ec316d366376d414d320538261be1b340b7dd",
}
# Everything A-02-001 adds; removing exactly this from the current module must give the accepted module.
ADDED_TOP_LEVEL = {
    "EvidenceBudgetExceeded",
    "_stored_bytes",
    "_listed_bytes",
    "_EVENT_BYTES",
    "_CR_BYTES",
    "_ATTEMPT_BYTES",
    "_Budget",
}
ADDED_IN_INDEX = {"_budget", "gather_bounded"}
GUARD = "self._budget is not None"


def _name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.ClassDef | ast.FunctionDef):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


class _StripGuards(ast.NodeTransformer):
    """Drop every ``if self._budget is not None: ...`` statement (the only change inside existing methods)."""

    removed = 0

    def visit_If(self, node: ast.If) -> ast.AST | None:
        if ast.unparse(node.test) == GUARD and not node.orelse:
            self.removed += 1
            return None
        return self.generic_visit(node)


def _without_maintenance(source: str) -> tuple[ast.Module, int, set[str]]:
    tree = ast.parse(source)
    dropped: set[str] = set()
    body = []
    for node in tree.body:
        name = _name(node)
        if name in ADDED_TOP_LEVEL:
            dropped.add(name)
            continue
        if isinstance(node, ast.ClassDef) and node.name == "Index":
            kept = []
            for item in node.body:
                if _name(item) in ADDED_IN_INDEX:
                    dropped.add(f"Index.{_name(item)}")
                    continue
                kept.append(item)
            node.body = kept
        body.append(node)
    tree.body = body
    strip = _StripGuards()
    tree = strip.visit(tree)
    return tree, strip.removed, dropped


# gather() is unchanged ------------------------------------------------------------------------------------------------


@pytest.mark.regression
def test_module_without_the_maintenance_is_the_accepted_module() -> None:
    """Removing the added names and the five ``if self._budget is not None`` guards gives, node for node, the
    accepted module: ``gather`` and every function it calls run the accepted code when no budget is set."""
    expected = ACCEPTED_UNPARSE_SHA256.get(sys.version_info[:2])
    if expected is None:
        pytest.fail(f"no accepted digest for Python {sys.version_info[:2]}")
    tree, guards, dropped = _without_maintenance(QUERY_PY.read_text(encoding="utf-8"))
    assert guards == 5  # _events, crossref_relations, crossref_sources, and the two relevance hit kinds
    assert dropped == ADDED_TOP_LEVEL | {f"Index.{n}" for n in ADDED_IN_INDEX}
    assert hashlib.sha256(ast.unparse(tree).encode()).hexdigest() == expected


@pytest.mark.regression
def test_no_budget_is_set_outside_gather_bounded(tmp_path: Path) -> None:
    idx = _one(tmp_path)
    with Index(idx) as ix:
        assert ix._budget is None
        ix.gather("10.5555/a")
        assert ix._budget is None
        with pytest.raises(EvidenceBudgetExceeded):
            ix.gather_bounded("10.5555/a", budget_bytes=0)
        assert ix._budget is None  # reset after an exceeded lookup too


def _one(tmp: Path) -> Path:
    return S.build_rows(
        tmp, [S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/a"})]
    )


def _fields(ev: query.Evidence) -> dict[str, Any]:
    return {k: getattr(ev, k) for k in vars(ev)}


@pytest.mark.regression
@pytest.mark.parametrize("name", ["policy_cases.json", "tension_cases.json"])
def test_bounded_lookup_within_budget_equals_gather_on_every_case(tmp_path: Path, name: str) -> None:
    """On every Stage 02 simulation case, ``gather_bounded`` with the exact budget the lookup
    needs, and with a large one, gives the same Evidence (and the same rendered result) as ``gather``."""
    cases = S.load_cases(name)
    checked = 0
    for i, case in enumerate(cases):
        idx = S.build_case(tmp_path / str(i), case)
        q = case.get("query", {})
        doi, pmid = q.get("doi"), q.get("pmid")
        with Index(idx) as ix:
            plain = ix.gather(doi, pmid)
            need = needed(ix, doi, pmid)
            for budget in (need, need + 1, 1 << 40):
                assert _fields(ix.gather_bounded(doi, pmid, budget_bytes=budget)) == _fields(plain)
            if need > 0:
                with pytest.raises(EvidenceBudgetExceeded):
                    ix.gather_bounded(doi, pmid, budget_bytes=need - 1)
        checked += 1
    assert checked == len(cases) > 0


# The bound: N - 1, N, N + 1 -----------------------------------------------------------------------------------------


def needed(ix: Index, doi: str | None, pmid: str | None) -> int:
    """The smallest budget the lookup fits: each refusal names the running total at the query that exceeded it."""
    budget = 0
    while True:
        try:
            ix.gather_bounded(doi, pmid, budget_bytes=budget)
            return budget
        except EvidenceBudgetExceeded as exc:
            assert exc.needed > budget
            budget = exc.needed


def _fanout(tmp: Path, n: int) -> Path:
    rows = [
        S.row(
            **{
                "Record ID": str(i + 1),
                "RetractionNature": "Correction",
                "OriginalPaperDOI": "10.5555/many",
                "OriginalPaperPubMedID": "123456",
                "RetractionDOI": f"10.5555/n{i}",
            }
        )
        for i in range(n)
    ]
    crossref = [
        {
            "original": "10.5555/many",
            "updated_by": [{"DOI": "10.5555/n0", "type": "retraction", "source": "retraction-watch"}],
        }
    ]
    return S.build_rows(tmp, rows, crossref)


def _stored_event_bytes(idx: Path, key: str) -> int:
    """Independent count: the UTF-8 bytes of every stored value of the key's event rows and their row digests."""
    import sqlite3

    conn = sqlite3.connect(f"file:{idx}?mode=ro", uri=True)
    try:
        cols = ", ".join(f"e.{c}" for c in query.EVENT_COLUMNS)
        total = 0
        sql = f"SELECT {cols}, r.row_sha256 FROM event e JOIN raw_record r ON r.ordinal = e.ordinal WHERE e.original_doi = ?"  # noqa: S608, E501
        for row in conn.execute(sql, (key,)):
            total += sum(len(v if isinstance(v, bytes) else str(v).encode()) for v in row if v is not None)
        return total
    finally:
        conn.close()


@pytest.mark.negative
@pytest.mark.parametrize("pmid", [None, "123456"])
def test_below_at_and_one_over_the_bound(tmp_path: Path, pmid: str | None) -> None:
    idx = _fanout(tmp_path, 40)
    with Index(idx) as ix:
        plain = ix.gather("10.5555/many", pmid)
        n = needed(ix, "10.5555/many", pmid)
        assert n >= _stored_event_bytes(idx, "10.5555/many") > 0
        assert _fields(ix.gather_bounded("10.5555/many", pmid, budget_bytes=n + 1)) == _fields(plain)
        assert _fields(ix.gather_bounded("10.5555/many", pmid, budget_bytes=n)) == _fields(plain)
        with pytest.raises(EvidenceBudgetExceeded) as exc:
            ix.gather_bounded("10.5555/many", pmid, budget_bytes=n - 1)
        assert (exc.value.code, exc.value.budget) == ("EVIDENCE_BUDGET_EXCEEDED", n - 1)
        assert exc.value.needed == n  # the last charged query is the one that crosses N - 1


@pytest.mark.negative
def test_one_event_more_than_the_budget_allows_is_refused_whole(tmp_path: Path) -> None:
    """With the budget fixed at what k events need, the index with k + 1 events is refused, not cut to k."""
    with Index(_fanout(tmp_path / "k", 30)) as ix:
        budget = needed(ix, "10.5555/many", None)
        assert len(ix.gather_bounded("10.5555/many", budget_bytes=budget).events) == 30
    with Index(_fanout(tmp_path / "k1", 31)) as ix, pytest.raises(EvidenceBudgetExceeded):
        ix.gather_bounded("10.5555/many", budget_bytes=budget)


def _row_bytes(idx: Path) -> dict[str, int]:
    """Stored bytes of each event row as the budget counts them, by event id (computed here, not by the module)."""
    import sqlite3

    conn = sqlite3.connect(f"file:{idx}?mode=ro", uri=True)
    try:
        cols = [f"e.{c}" for c in query.EVENT_COLUMNS] + ["r.row_sha256"]
        sql = f"SELECT e.event_id, {', '.join(cols)} FROM event e JOIN raw_record r ON r.ordinal = e.ordinal"  # noqa: S608
        return {
            row[0]: sum(len(v if isinstance(v, bytes) else str(v).encode()) for v in row[1:] if v is not None)
            for row in conn.execute(sql)
        }
    finally:
        conn.close()


@pytest.mark.negative
@pytest.mark.parametrize("fraction", [0.0, 0.25, 0.5, 0.75, 0.999])
def test_over_the_budget_nothing_beyond_it_is_materialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fraction: float
) -> None:
    """SQLite sums the size of a query's rows before they are read: an exceeded lookup converts only rows of the
    queries that fitted, whose stored bytes are within the budget, and never the rows of the query that crossed it
    (fail-first: gather materialized every row and a cap was applied afterwards, fail_first_before.log)."""
    made: list[str] = []
    real = query.event_from_row

    def counting(row: Any) -> Any:
        made.append(row[0])
        return real(row)

    monkeypatch.setattr(query, "event_from_row", counting)
    idx = _fanout(tmp_path, 2000)
    size = _row_bytes(idx)
    with Index(idx) as ix:
        n = needed(ix, "10.5555/many", None)
        made.clear()
        ix.gather_bounded("10.5555/many", budget_bytes=n)
        unbounded = len(made)
        assert unbounded >= 2000
        budget = int(n * fraction)
        made.clear()
        with pytest.raises(EvidenceBudgetExceeded):
            ix.gather_bounded("10.5555/many", budget_bytes=budget)
        assert sum(size[e] for e in made) <= budget
        assert len(made) < unbounded
        if fraction < 0.5:  # below the first query's share (the DOI query reads all 2000 rows): nothing is read
            assert made == []


@pytest.mark.negative
@pytest.mark.parametrize("budget", [-1, 1.5, True, "1000", None])
def test_budget_must_be_a_non_negative_int(tmp_path: Path, budget: Any) -> None:
    idx = _one(tmp_path)
    with Index(idx) as ix, pytest.raises(QueryError) as exc:
        ix.gather_bounded("10.5555/a", budget_bytes=budget)
    assert exc.value.code == "BUDGET_INVALID"


@pytest.mark.negative
def test_invalid_query_needs_no_budget(tmp_path: Path) -> None:
    idx = _one(tmp_path)
    with Index(idx) as ix:
        assert ix.gather_bounded("not a doi", budget_bytes=0).state == ix.gather("not a doi").state == "invalid_query"


@pytest.mark.negative
def test_relevance_hits_are_charged_before_they_are_kept(tmp_path: Path) -> None:
    """A no-record lookup lists the quarantined records and invalid identifiers that may concern the key; each hit is
    charged its canonical size before it is kept, so a large raw value cannot pass the budget (D-048 bound)."""
    raw = "see 10.5555/zzz " + "x" * 5000
    rows = [
        S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": raw}),
        S.row(**{"Record ID": "2", "RetractionNature": "Bogus", "OriginalPaperDOI": "10.5555/zzz"}),
    ]
    with Index(S.build_rows(tmp_path, rows)) as ix:
        plain = ix.gather("10.5555/zzz")
        assert plain.state == "no_record"
        assert [i["code"] for i in plain.issues] == ["RELEVANT_QUARANTINE", "RELEVANT_INVALID_IDENTIFIER"]
        n = needed(ix, "10.5555/zzz", None)
        assert n > len(raw)
        assert _fields(ix.gather_bounded("10.5555/zzz", budget_bytes=n)) == _fields(plain)
        with pytest.raises(EvidenceBudgetExceeded) as exc:
            ix.gather_bounded("10.5555/zzz", budget_bytes=n - 1)
        assert exc.value.needed == n
