"""The Stage 04 report as a manifest graph (owner decision D-054; SPEC 11.1).

The report blob named by ``report_recorded`` is a small versioned **manifest** (``report`` schema 3.0.0): the
identities, terminal state, outcome, article summary, limitations and, for each large collection, the ordered list of
content-addressed **report chunks** (``report-chunk`` schema) that hold it, with their item counts. The evidence of
the report is not copied: the manifest names the committed evidence batches (D-053) in commit order. The durable
report is the whole graph.

Determinism: the order of every collection is a function of its content (``ORDERS``) and the chunk boundaries are the
byte-ceiling cut of SPEC 8.8 (``batches.boundaries``), so equal reports always give equal blobs.

Checks: ``graph_problem`` proves the graph on its own (every chunk present, intact, schema-valid, of its part, listed
once, counted correctly, cut canonically, in canonical order; the summary counts and positive works agree with the
claims), and ``fold_problem`` proves it equals the committed fold (claims, decisions, questions, observations,
evidence batches, investigation and root). Investigation Memory runs both when the report is recorded and when the
journal is opened (``fold.py``); a missing or corrupt chunk is corruption, never an empty part.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from citerift.investigation import batches
from citerift.investigation.canonical import canon
from citerift.investigation.errors import InvestigationMemoryError
from citerift.investigation.schemas import REPORT, REPORT_CHUNK, problems

REPORT_VERSION = "3.0.0"
CHUNK_VERSION = "1.0.0"
PARTS = ("claims", "observations", "positive_works")
ORDERS = {
    "claims": "unit-byte-start/candidate-keys/claim-id/1",
    "observations": "commit/1",
    "positive_works": "work/1",
}
EVIDENCE_ORDER = "commit/evidence-batch/1"
POSITIVE = frozenset({"RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED"})

Read = Callable[[str], Any]  # the parsed value of a blob; raises on a missing or corrupt blob


def chunk(part: str, items: list[Any]) -> dict[str, Any]:
    return {"schema": REPORT_CHUNK, "schema_version": CHUNK_VERSION, "part": part, "items": items}


ENVELOPE = {part: len(canon(chunk(part, []))) for part in PARTS}


def claim_key(entry: Mapping[str, Any]) -> tuple[int, bytes, str]:
    """SPEC 11.1: unit source byte offset, then candidate key order (the canonical encoding of the candidate's keys),
    then the claim id, which makes the order total."""
    return (entry["unit"]["byte_start"], canon(entry["claim"]["candidate"]["keys"]), entry["claim"]["claim_id"])


def work_key(work: Mapping[str, Any]) -> bytes:
    return canon(work["work"])


def chunks(part: str, items: list[Any]) -> list[dict[str, Any]]:
    """The canonical chunks of one collection, its items already in canonical order."""
    counts = batches.boundaries([batches.item_bytes(i) for i in items], ENVELOPE[part])
    out, at = [], 0
    for n in counts:
        out.append(chunk(part, items[at : at + n]))
        at += n
    return out


def build(
    header: Mapping[str, Any],
    claims: Iterable[Mapping[str, Any]],
    observations: Iterable[Mapping[str, Any]],
    positive_works: Iterable[Mapping[str, Any]],
    evidence: Iterable[tuple[str, int]],
    publish: Callable[[Any], str],
) -> dict[str, Any]:
    """The manifest of a report, after publishing its chunks with ``publish`` (which returns a blob digest).

    ``header`` holds ``investigation_key``, ``investigation_id``, ``root``, ``terminal_state``, ``outcome``,
    ``limitations``, ``identities`` and ``snapshot_id``; ``evidence`` is the committed batches as (digest, item count)
    in commit order. Claims and positive works are put in canonical order; observations keep the order given (commit
    order)."""
    collections = {
        "claims": sorted((dict(c) for c in claims), key=claim_key),
        "observations": [dict(o) for o in observations],
        "positive_works": sorted((dict(w) for w in positive_works), key=work_key),
    }
    components: dict[str, Any] = {}
    for part, items in collections.items():
        listed = [{"chunk": publish(c), "count": len(c["items"])} for c in chunks(part, items)]
        components[part] = {"order": ORDERS[part], "count": len(items), "chunks": listed}
    ev = [{"batch": d, "count": n} for d, n in evidence]
    components["evidence"] = {"order": EVIDENCE_ORDER, "count": sum(e["count"] for e in ev), "batches": ev}
    by_class: dict[str, int] = {}
    for e in collections["claims"]:
        by_class[e["claim"]["class"]] = by_class.get(e["claim"]["class"], 0) + 1
    return {
        "schema": REPORT,
        "schema_version": REPORT_VERSION,
        "investigation_key": header["investigation_key"],
        "investigation_id": header["investigation_id"],
        "root": header["root"],
        "terminal_state": header["terminal_state"],
        "outcome": header["outcome"],
        "article_summary": {
            "claims_by_class": dict(sorted(by_class.items())),
            "open_questions": sum(1 for e in collections["claims"] if e["question"] is not None),
            "snapshot_id": header["snapshot_id"],
        },
        "limitations": list(header["limitations"]),
        "identities": header["identities"],
        "components": components,
    }


class _Bad(Exception):
    pass


def _read_part(manifest: Mapping[str, Any], part: str, read: Read) -> Iterable[Any]:
    """The items of one collection, chunk by chunk, with every structural check of that collection."""
    comp = manifest["components"][part]
    listed = [c["chunk"] for c in comp["chunks"]]
    if len(set(listed)) != len(listed):
        raise _Bad(f"{part}: a chunk is listed twice")
    if sum(c["count"] for c in comp["chunks"]) != comp["count"]:
        raise _Bad(f"{part}: count {comp['count']} is not the sum of the chunk counts")
    sizes: list[int] = []
    for i, ref in enumerate(comp["chunks"]):
        try:
            value = read(ref["chunk"])
        except (InvestigationMemoryError, OSError, ValueError) as exc:  # BlobError, CanonError, JSONDecodeError
            raise _Bad(f"{part} chunk {i} ({ref['chunk']}) is missing or corrupt: {exc}") from exc
        found = problems(value, REPORT_CHUNK)
        if found:
            raise _Bad(f"{part} chunk {i}: " + "; ".join(found[:3]))
        if value["part"] != part:
            raise _Bad(f"{part} chunk {i} is a chunk of {value['part']}")
        if len(value["items"]) != ref["count"]:
            raise _Bad(f"{part} chunk {i} holds {len(value['items'])} items, the manifest says {ref['count']}")
        for item in value["items"]:
            sizes.append(batches.item_bytes(item))
            yield item
    if batches.boundaries(sizes, ENVELOPE[part]) != [c["count"] for c in comp["chunks"]]:
        raise _Bad(f"{part}: the chunk boundaries are not the canonical ones (SPEC 8.8)")


def _walk(manifest: Mapping[str, Any], read: Read) -> dict[str, Any]:
    """Every check of the graph on its own; returns what ``fold_problem`` compares (no item is kept beyond that)."""
    found = problems(manifest, REPORT)
    if found:
        raise _Bad("manifest: " + "; ".join(found[:3]))
    claims: dict[str, dict[str, Any]] = {}
    by_class: dict[str, int] = {}
    questions = 0
    last: tuple[int, bytes, str] | None = None
    for e in _read_part(manifest, "claims", read):
        key = claim_key(e)
        if last is not None and key <= last:
            raise _Bad("claims are not in the canonical order (unit offset, candidate keys, claim id)")
        last = key
        c = e["claim"]
        claims[c["claim_id"]] = {"claim": c, "decision": e["decision"], "question": e["question"]}
        by_class[c["class"]] = by_class.get(c["class"], 0) + 1
        questions += e["question"] is not None
    summary = manifest["article_summary"]
    if summary["claims_by_class"] != by_class:
        raise _Bad("article_summary.claims_by_class does not count the claims")
    if summary["open_questions"] != questions:
        raise _Bad("article_summary.open_questions does not count the questions of the claims")
    observations = list(_read_part(manifest, "observations", read))
    placed: set[str] = set()
    last_work: bytes | None = None
    for w in _read_part(manifest, "positive_works", read):
        wkey = work_key(w)
        if last_work is not None and wkey <= last_work:
            raise _Bad("positive works are not in the canonical order or a work is listed twice")
        last_work = wkey
        for cid in w["claim_ids"]:
            c = claims.get(cid)
            if c is None or c["claim"]["class"] not in POSITIVE or c["claim"]["class"] not in w["classes"]:
                raise _Bad(f"positive work names {cid}, which is not a positive claim of one of its classes")
            if cid in placed:
                raise _Bad(f"claim {cid} is in two positive works")
            placed.add(cid)
        if {claims[cid]["claim"]["class"] for cid in w["claim_ids"]} != set(w["classes"]):
            raise _Bad("a positive work lists a class none of its claims has")
    if placed != {cid for cid, c in claims.items() if c["claim"]["class"] in POSITIVE}:
        raise _Bad("a positive claim is in no positive work")
    ev = manifest["components"]["evidence"]
    listed = [b["batch"] for b in ev["batches"]]
    if len(set(listed)) != len(listed):
        raise _Bad("evidence: a batch is listed twice")
    if sum(b["count"] for b in ev["batches"]) != ev["count"]:
        raise _Bad("evidence: count is not the sum of the batch counts")
    return {"claims": claims, "observations": observations}


def graph_problem(manifest: Any, read: Read) -> str:
    """D-054: every node of the report graph, on its own; ``""`` when it holds."""
    try:
        _walk(manifest, read)
    except _Bad as exc:
        return str(exc)
    return ""


def fold_problem(
    manifest: Any,
    read: Read,
    *,
    investigation: Mapping[str, Any],
    root: Mapping[str, Any] | None,
    claims: Mapping[str, Mapping[str, Any]],
    decisions: Mapping[str, Mapping[str, Any]],
    questions: Mapping[str, Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    evidence: Sequence[tuple[str, int]],
) -> str:
    """``graph_problem``, then D-054 against the committed fold: the report holds exactly the current committed claims,
    each with its committed decision and its open question; the committed observations in commit order; the committed
    evidence batches in commit order; and the investigation and root it was made for. ``""`` when it holds.

    ``claims`` maps the current claim ids to their payloads, ``decisions`` decision ids to ``{claim_id,
    disposition}``, ``questions`` question ids to ``{claim_id, kind, open}``."""
    try:
        got = _walk(manifest, read)
    except _Bad as exc:
        return str(exc)
    if manifest["investigation_key"] != investigation["investigation_key"]:
        return "the report is for another investigation key"
    if manifest["investigation_id"] != investigation["investigation_id"]:
        return "the report is for another investigation id"
    if root is None or manifest["root"] != root:
        return "the report root is not the bound root"
    if set(got["claims"]) != set(claims):
        return "the report claims are not the current committed claims"
    decision_of = {d["claim_id"]: {"decision_id": i, "disposition": d["disposition"]} for i, d in decisions.items()}
    question_of = {
        q["claim_id"]: {"question_id": i, "kind": q["kind"]} for i, q in questions.items() if q.get("open", True)
    }
    for cid, e in got["claims"].items():
        if e["claim"] != claims[cid]:
            return f"claim {cid} in the report is not the committed claim"
        if e["decision"] != decision_of.get(cid):
            return f"the decision of claim {cid} in the report is not the committed decision"
        if e["question"] != question_of.get(cid):
            return f"the question of claim {cid} in the report is not its open question"
    if got["observations"] != [dict(o) for o in observations]:
        return "the report observations are not the committed observations in commit order"
    if [(b["batch"], b["count"]) for b in manifest["components"]["evidence"]["batches"]] != list(evidence):
        return "the report evidence is not the committed evidence batches in commit order"
    return ""
