"""Stage 04 Step 13: the annotation item set and the annotation packets (PREREGISTRATION.md section 6).

Engine-independent by construction: it reads the captured bundle, runs the accepted Stage 03 extractor on it
(``citerift.wiki.extract.extract_bundle`` with the default configuration, the same call Stage 04 EXTRACT makes) and
reads the pinned Stage 02 index with plain SQL. It never imports or runs the Stage 04 engine, so packets and labels
exist before any Stage 04 prediction does (owner decision D-3: labels locked before predictions are exposed).

**Candidate records of a unit** (a Stage 03 citation unit):

1. *identifier-reached*: every Retraction Watch event (accepted record) with an original or notice identifier equal
   to the Stage 02-normalized key (``normalization.normalized``) of any valid identifier occurrence of the unit, any
   role;
2. *title-reached*: every event whose title tokens ``T(r)`` (Stage 02 ``search.title_tokens``) satisfy
   ``|T(r)| >= 4`` and ``|T(r) & T(u)| / |T(r)| >= 0.8``, with ``T(u)`` the title tokens of the unit's wikitext span;
   at most 5 per unit, ranked by that ratio (descending), shared tokens (descending), event id.

**Item set**: every unit with at least one candidate record. A unit without one cannot be a true positive within the
retrieval scope (a declared boundary) and is not annotated.

Packet text is the unit's wikitext span (at most ``MAX_TEXT`` bytes, cut on a UTF-8 boundary and marked). Records
show only Retraction Watch fields; nothing of Stage 04 (class, rule, key, role, lookup state) is shown.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s13_common import digest, write_json

from citerift.retraction.search import title_tokens
from citerift.wiki.bundle import open_bundle
from citerift.wiki.extract import ExtractConfig, extract_bundle

FORMAT = "citerift-stage04-eval-packet/1"
MAX_TEXT = 6000
MIN_TITLE_TOKENS = 4
TITLE_COVERAGE = 0.8
MAX_TITLE_RECORDS = 5
NATURE = {
    "retracted": "Retraction",
    "expression_of_concern": "Expression of concern",
    "correction": "Correction",
    "reinstated": "Reinstatement",
}
RECORD_FIELDS = ("Journal", "Author", "OriginalPaperDate", "RetractionDate", "ArticleType")


def connect(index: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


class Records:
    """Read-only access to the accepted events of the pinned Stage 02 index."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.header = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'header'").fetchone()[0])

    def by_key(self, scheme: str, norm: str) -> list[tuple[str, str]]:
        """(event_id, side) of every event with this normalized identifier as an original or notice identifier."""
        rows = self.conn.execute(
            "SELECT e.event_id AS event_id, i.role AS role FROM ident i JOIN event e ON e.ordinal = i.ordinal "
            "WHERE i.scheme = ? AND i.norm = ? ORDER BY e.event_id, i.role",
            (scheme, norm),
        ).fetchall()
        return sorted({(r["event_id"], r["role"]) for r in rows})

    def by_title(self, tokens: Iterable[str]) -> list[tuple[str, float, int]]:
        toks = sorted(set(tokens))
        if not toks:
            return []
        shared: dict[str, int] = {}
        for i in range(0, len(toks), 500):
            chunk = toks[i : i + 500]
            marks = ",".join("?" * len(chunk))
            for r in self.conn.execute(
                f"SELECT event_id, COUNT(*) AS c FROM title_token WHERE token IN ({marks}) GROUP BY event_id",  # noqa: S608
                chunk,
            ):
                shared[r["event_id"]] = shared.get(r["event_id"], 0) + r["c"]
        out = []
        for eid, c in shared.items():
            if c < MIN_TITLE_TOKENS:
                continue
            title = self.conn.execute("SELECT title FROM event WHERE event_id = ?", (eid,)).fetchone()["title"]
            n = len(title_tokens(title))
            if n >= MIN_TITLE_TOKENS and c / n >= TITLE_COVERAGE:
                out.append((eid, c / n, c))
        out.sort(key=lambda t: (-t[1], -t[2], t[0]))
        return out[:MAX_TITLE_RECORDS]

    def record(self, event_id: str) -> dict[str, Any]:
        r = self.conn.execute(
            "SELECT e.*, raw.fields AS fields FROM event e JOIN raw_record raw ON raw.ordinal = e.ordinal "
            "WHERE e.event_id = ?",
            (event_id,),
        ).fetchone()
        fields = dict(zip(self.header, json.loads(r["fields"]), strict=True))
        return {
            "event_id": r["event_id"],
            "record_id": r["record_id"],
            "nature": NATURE[r["event_type"]],
            "title": r["title"],
            "original_doi": r["original_doi"],
            "original_pmid": r["original_pmid"],
            "notice_doi": r["notice_doi"],
            "notice_pmid": r["notice_pmid"],
            **{k.lower(): fields.get(k) for k in RECORD_FIELDS},
        }


def unit_text(source: bytes, unit: dict[str, Any]) -> tuple[str, bool]:
    span = source[unit["source"]["byte_start"] : unit["source"]["byte_end"]]
    if len(span) <= MAX_TEXT:
        return span.decode("utf-8", "replace"), False
    return span[:MAX_TEXT].decode("utf-8", "ignore") + " [...TRUNCATED]", True


def items_of(extraction: dict[str, Any], source: bytes, records: Records) -> list[dict[str, Any]]:
    """The annotation items of one extraction, in unit order (engine-independent)."""
    idents: dict[str, list[dict[str, Any]]] = {}
    for ident in extraction["identifiers"]:
        if ident.get("unit_id"):
            idents.setdefault(ident["unit_id"], []).append(ident)
    cap = extraction["capture"]
    items = []
    for unit in extraction["units"]:
        text, cut = unit_text(source, unit)
        reached: dict[str, set[str]] = {}
        shown = []
        for ident in idents.get(unit["id"], []):
            norm = ident.get("normalization") or {}
            entry = {"scheme": ident["scheme"], "as_written": (ident.get("source") or {}).get("raw")}
            if norm.get("valid") and isinstance(norm.get("normalized"), str):
                entry["normalized"] = norm["normalized"]
                for eid, side in records.by_key(ident["scheme"], norm["normalized"]):
                    reached.setdefault(eid, set()).add(f"{ident['scheme']}:{norm['normalized']} as {side}")
            shown.append(entry)
        for eid, ratio, _ in records.by_title(title_tokens(text)):
            reached.setdefault(eid, set()).add(f"title tokens ({ratio:.2f} of the record title)")
        if not reached:
            continue
        recs = []
        for n, eid in enumerate(sorted(reached), start=1):
            recs.append({"ref": f"R{n}", **records.record(eid), "reached_by": sorted(reached[eid])})
        shown.sort(key=lambda e: (e["scheme"], e.get("normalized") or "", e["as_written"] or ""))
        items.append(
            {
                "item_id": f"{cap['wiki']}-{cap['revision_id']}-{unit['id']}",
                "unit_id": unit["id"],
                "byte_start": unit["source"]["byte_start"],
                "byte_end": unit["source"]["byte_end"],
                "text": text,
                "text_truncated": cut,
                "identifiers": shown,
                "records": recs,
            }
        )
    return items


def packet(bundle: Path, index: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract the bundle (Stage 03, isolated worker) and build its packet; return (packet, extraction). A failed
    extraction gives a packet without items (an acquisition failure)."""
    extraction = extract_bundle(bundle, ExtractConfig(), isolated=True)
    if extraction["status"] not in ("complete", "partial"):
        return {"format": FORMAT, "extraction_status": extraction["status"], "items": None}, extraction
    cap = open_bundle(bundle).capture
    source = (bundle / "artifacts" / cap["source"]["artifact"]).read_bytes()
    with connect(index) as conn:
        items = items_of(extraction, source, Records(conn))
    doc = {
        "format": FORMAT,
        "article": {
            "wiki": cap["page"]["wiki"],
            "page_id": cap["page"]["page_id"],
            "revision_id": cap["page"]["revision_id"],
            "title": cap["page"]["title"],
        },
        "extraction_status": extraction["status"],
        "extraction_digest": extraction["extraction_digest"],
        "units": len(extraction["units"]),
        "items": items,
        "items_digest": digest(items),
    }
    return doc, extraction


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 annotation packet of one bundle")
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extraction-out", type=Path, required=True, help="where the Stage 03 extraction is retained")
    a = ap.parse_args(argv)
    p, extraction = packet(a.bundle, a.index)
    write_json(a.out, p)
    write_json(a.extraction_out, extraction)
    print(p["extraction_status"], None if p["items"] is None else len(p["items"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
