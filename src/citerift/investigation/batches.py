"""Deterministic ordering and chunking of bulk Stage 04 collections (owner decisions D-053 and D-054; SPEC 8.8).

The journal is the audit log, commit log and state-machine history; it is not the bulk store. Evidence items are
committed in content-addressed **evidence batches** (one ``evidence_batch_recorded`` record per batch), and the large
collections of a report are content-addressed **report chunks** named by a small report manifest (``report.py``).

Two rules make the representation a function of the content alone, so that equal content always gives equal blobs:

- **Order of evidence** (``dependency_order``). The items of one attempt form a graph by their ``refs``. A reference to
  an item outside the attempt must name evidence already defined (``known``); a reference inside it is an edge. The
  order is Kahn's topological order in which, at every point, the ready item with the smallest evidence id comes next.
  It does not depend on the order the items were supplied in. Every reference precedes the item that names it, also
  across batch boundaries. A duplicate id, a dangling reference or a cycle is refused (``BatchError``).
- **Boundaries** (``boundaries``). Items are taken in that order and a part closes before the next item would make its
  canonical encoding exceed ``MAX_PART_BYTES``. A part always holds at least one item, so an item larger than the
  ceiling forms a part of its own; it still has to fit ``MAX_BLOB_BYTES``. The ceiling is derived in
  ``docs/verification/stage-04/review/step7/d053/`` (``part_ceiling.py``); it is a constant of journal format 3.

Investigation Memory checks both rules when a batch or a report is committed and when the journal is opened
(``fold.py``), so a journal can only hold the one canonical representation of its content.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from citerift.investigation.canonical import canon
from citerift.investigation.schemas import EVIDENCE_BATCH

BATCH_VERSION = "1.0.0"
ORDER = "dependency-topological/evidence-id/1"
# Derived in docs/verification/stage-04/review/step7/d053/part_ceiling.py (part_ceiling.json): the smallest power of two
# that holds the largest legal item, keeps the batch records of the worst legal investigation within 1 % of the journal
# limit, and costs no measurable commit or open time over larger ceilings. A test pins it to that record.
MAX_PART_BYTES = 8 * 1024 * 1024


class BatchError(ValueError):
    """The evidence of an attempt cannot be ordered: ``DUPLICATE_ID``, ``DANGLING_REFERENCE`` or
    ``DEPENDENCY_CYCLE``."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def item_bytes(item: Any) -> int:
    """The length of an item's canonical encoding, as it appears inside a part (blobs allow finite floats)."""
    return len(canon(item, allow_float=True))


def dependency_order(items: Iterable[Mapping[str, Any]], known: Callable[[str], bool]) -> list[Mapping[str, Any]]:
    """The deterministic dependency order of one attempt's evidence (module docstring)."""
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in items:
        eid = item["evidence_id"]
        if eid in by_id:
            raise BatchError("DUPLICATE_ID", f"evidence {eid} is supplied twice")
        by_id[eid] = item
    waiting: dict[str, int] = {}
    children: dict[str, list[str]] = {}
    for eid, item in by_id.items():
        inside = 0
        for ref in item["refs"]:
            if ref in by_id:
                inside += 1
                children.setdefault(ref, []).append(eid)
            elif not known(ref):
                raise BatchError("DANGLING_REFERENCE", f"evidence {eid} refers to {ref}, which is not defined")
        waiting[eid] = inside
    ready = [eid for eid, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    out: list[Mapping[str, Any]] = []
    while ready:
        eid = heapq.heappop(ready)
        out.append(by_id[eid])
        for child in children.get(eid, ()):
            waiting[child] -= 1
            if waiting[child] == 0:
                heapq.heappush(ready, child)
    if len(out) != len(by_id):
        stuck = sorted(eid for eid, n in waiting.items() if n > 0)
        raise BatchError("DEPENDENCY_CYCLE", f"{len(stuck)} evidence items are on or behind a cycle, first {stuck[0]}")
    return out


def boundaries(sizes: list[int], envelope: int, limit: int | None = None) -> list[int]:
    """The number of items in each part when items of canonical sizes ``sizes`` are cut by the byte ceiling.

    ``envelope`` is the canonical size of the part with an empty item list; ``n`` items add their sizes and ``n - 1``
    commas. A part closes before an item would push it over ``limit`` (default ``MAX_PART_BYTES``, read at the call);
    a part is never empty."""
    if limit is None:
        limit = MAX_PART_BYTES
    counts: list[int] = []
    size, count = envelope, 0
    for s in sizes:
        added = s + (1 if count else 0)
        if count and size + added > limit:
            counts.append(count)
            size, count = envelope, 0
            added = s
        size += added
        count += 1
    if count:
        counts.append(count)
    return counts


def evidence_batch(items: list[Any]) -> dict[str, Any]:
    return {"schema": EVIDENCE_BATCH, "schema_version": BATCH_VERSION, "order": ORDER, "items": items}


BATCH_ENVELOPE = len(canon(evidence_batch([])))


def evidence_batches(
    items: Iterable[Mapping[str, Any]], known: Callable[[str], bool], limit: int | None = None
) -> list[dict[str, Any]]:
    """The canonical evidence batches of one attempt's items: dependency order, then the byte ceiling."""
    ordered = [dict(i) for i in dependency_order(items, known)]
    counts = boundaries([item_bytes(i) for i in ordered], BATCH_ENVELOPE, limit)
    out, at = [], 0
    for n in counts:
        out.append(evidence_batch(ordered[at : at + n]))
        at += n
    return out


def batch_records(digests: list[str], batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ``evidence_batch_recorded`` payloads of an attempt's batches, in order."""
    total = len(batches)
    return [
        {"batch": d, "batch_index": i, "batch_total": total, "evidence_count": len(b["items"])}
        for i, (d, b) in enumerate(zip(digests, batches, strict=True))
    ]
