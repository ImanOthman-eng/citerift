"""Read-only lookups over a built index (SPECIFICATION.md sections 8, 10.3 and 11.1).

Nothing here writes: the index is opened ``mode=ro&immutable=1`` and every query is parameterized.
"""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from citerift.retraction import policy
from citerift.retraction.canonical import canonical, digest
from citerift.retraction.dates import TemporalEvidence
from citerift.retraction.export import CR_COLUMNS, EVENT_COLUMNS, cr_from_row, event_from_row
from citerift.retraction.identifiers import Normalized, ascii_fold, normalize_doi, normalize_pmid
from citerift.retraction.ingest import IDENT_FIELDS
from citerift.retraction.source import Receipt, parse_receipt
from citerift.retraction.store import SCHEMA_VERSION, IndexUnavailable, open_index, read_meta

RW_CHANNEL = "rw-gitlab-csv"
CR_SOURCE_ID = "crossref"
DEFAULT_PAGE = 20
MAX_PAGE = 100
MAX_RELEVANCE_LISTED = 100  # relevance hits listed in issues; the full count is always reported


class QueryError(ValueError):
    """A usage problem that is not an identifier problem (for example a cursor from another query)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass
class Evidence:
    """Everything a lookup gathered, before projection and paging."""

    query: dict[str, Any]
    keys: dict[str, str | None]
    state: str
    identity: str = "none"
    role: str = "none"
    anchor: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    candidate_groups: list[dict[str, Any]] = field(default_factory=list)
    notice_hits: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    crossref: list[dict[str, Any]] = field(default_factory=list)
    checked_sources: list[dict[str, Any]] = field(default_factory=list)
    relevant_gap: bool = False
    evidence_set: policy.EvidenceSet | None = None


def _norm_record(n: Normalized | None) -> dict[str, Any] | None:
    return None if n is None else n.to_json()


def normalize_query(doi: str | None, pmid: str | None) -> tuple[dict[str, Any], dict[str, str | None], bool]:
    """Return (query record, keys, valid). Query identifiers are not source fields: no sentinels."""
    nd = normalize_doi(doi) if doi is not None else None
    np_ = normalize_pmid(pmid) if pmid is not None else None
    query = {"doi": _norm_record(nd), "pmid": _norm_record(np_)}
    keys = {"doi": nd.normalized if nd else None, "pmid": np_.normalized if np_ else None}
    valid = (doi is not None or pmid is not None) and (nd is None or nd.valid) and (np_ is None or np_.valid)
    return query, keys, valid


class Index:
    """An opened, read-only index with its snapshot metadata."""

    def __init__(self, path: Path):
        self.path = path
        self.conn: sqlite3.Connection = open_index(path)
        self.meta = read_meta(self.conn)
        self.snapshot_id: str = self.meta["snapshot_id"]
        self.receipt: Receipt = parse_receipt(json.loads(self.meta["receipt"]))
        self.header: list[str] = json.loads(self.meta["header"])

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Index:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # Sources and assertions ------------------------------------------------------------------------

    def rw_source(self) -> dict[str, Any]:
        return {
            "source_id": self.receipt.source_id,
            "locator": self.receipt.url,
            "retrieved_at": self.receipt.acquired_at,
            "source_version": self.receipt.commit,
            "content_sha256": self.meta["source_sha256"],
        }

    def rw_record_ref(self, ordinal: int, row_sha256: str) -> dict[str, Any]:
        return {
            "source_id": self.receipt.source_id,
            "locator": f"{self.receipt.locator_base}#record={ordinal}",
            "retrieved_at": self.receipt.acquired_at,
            "source_version": self.receipt.commit,
            "content_sha256": row_sha256,
        }

    def _events(self, where: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        columns = ", ".join(f"e.{c}" for c in EVENT_COLUMNS)
        sql = f"SELECT {columns}, r.row_sha256 FROM event e JOIN raw_record r ON r.ordinal = e.ordinal WHERE {where}"  # noqa: S608
        out = []
        for row in self.conn.execute(sql, params):
            ev = event_from_row(row[:-1])
            ev["row_sha256"] = row[-1]
            out.append(ev)
        return out

    def events_by(self, column: str, key: str) -> list[dict[str, Any]]:
        if column not in ("original_doi", "original_pmid", "notice_doi", "notice_pmid"):
            raise ValueError(column)
        return self._events(f"e.{column} = ?", (key,))

    def event_by_id(self, event_id: str) -> dict[str, Any] | None:
        found = self._events("e.event_id = ?", (event_id,))
        return found[0] if found else None

    def crossref_relations(self, original_dois: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for d in sorted(set(original_dois)):
            rows = self.conn.execute(
                f"SELECT {', '.join(CR_COLUMNS)} FROM cr_assertion "  # noqa: S608
                "WHERE predicate = 'update_relation' AND original_doi = ? ORDER BY assertion_id",
                (d,),
            )
            out += [cr_from_row(r) for r in rows]
        return out

    def crossref_sources(self, dois: list[str]) -> list[dict[str, Any]]:
        out = []
        for d in sorted(set(dois)):
            for url, retrieved_at, sha in self.conn.execute(
                "SELECT url, retrieved_at, payload_sha256 FROM cr_attempt WHERE work_doi = ? AND outcome = 'ok'",
                (d,),
            ):
                out.append(
                    {"source_id": CR_SOURCE_ID, "locator": url, "retrieved_at": retrieved_at, "content_sha256": sha}
                )
        return out

    def relevance(self, keys: list[str]) -> list[dict[str, Any]]:
        """Quarantined records and invalid identifier occurrences that contain a query key."""
        hits: list[dict[str, Any]] = []
        id_columns = [self.header.index(col) for _, _, col in IDENT_FIELDS if col in self.header]
        for ordinal, fields_json in self.conn.execute(
            # CROSS JOIN keeps the (small) quarantine table outermost; the planner otherwise scans every record.
            "SELECT q.ordinal, r.fields FROM quarantine q CROSS JOIN raw_record r ON r.ordinal = q.ordinal "
            "ORDER BY q.ordinal"
        ):
            fields = json.loads(fields_json)
            candidates = [fields[i] for i in id_columns] if len(fields) == len(self.header) else fields
            if any(k in ascii_fold(f) for k in keys for f in candidates):
                hits.append({"code": "RELEVANT_QUARANTINE", "ordinal": ordinal})
        for ordinal, column, raw in self.conn.execute(
            "SELECT ordinal, column_name, raw FROM ident WHERE norm IS NULL AND missing = 0 ORDER BY ordinal, id"
        ):
            if any(k in ascii_fold(raw) for k in keys):
                hits.append({"code": "RELEVANT_INVALID_IDENTIFIER", "ordinal": ordinal, "column": column, "raw": raw})
        return hits

    # Lookup ----------------------------------------------------------------------------------------

    def gather(
        self, doi: str | None = None, pmid: str | None = None, *, supersessions: tuple[tuple[str, str], ...] = ()
    ) -> Evidence:
        """Steps 1 to 7 of SPECIFICATION.md 10.3. ``supersessions`` has no source in Stage 02 data; it lets
        tests and later stages pass explicit (reinstatement, target) event-id links."""
        query, keys, valid = normalize_query(doi, pmid)
        if not valid:
            return Evidence(query, keys, "invalid_query")
        d, p = keys["doi"], keys["pmid"]
        ev = Evidence(query, keys, "no_record", checked_sources=[self.rw_source()])
        o_d = self.events_by("original_doi", d) if d else []
        o_p = self.events_by("original_pmid", p) if p else []
        notices = (self.events_by("notice_doi", d) if d else []) + (self.events_by("notice_pmid", p) if p else [])
        notices = sorted({e["event_id"]: e for e in notices}.values(), key=lambda e: e["event_id"])
        matched: list[tuple[dict[str, Any], str, str | None]] = []  # (event, matched_by, linked_via)
        if d and p:
            compatible = all(e["original_pmid"] in (p, None) for e in o_d) and all(
                e["original_doi"] in (d, None) for e in o_p
            )
            if not compatible:
                ev.state, ev.identity = "ambiguous_identity", "ambiguous"
                for e in o_p:
                    e["matched_by"], e["linked_via"] = "pmid", None
                for e in o_d:
                    e["matched_by"], e["linked_via"] = "doi", None
                ev.events = sorted({e["event_id"]: e for e in o_p + o_d}.values(), key=lambda e: e["event_id"])
                ev.candidate_groups = [
                    {"anchor": f"doi:{d}", "event_ids": sorted(e["event_id"] for e in o_d)},
                    {"anchor": f"pmid:{p}", "event_ids": sorted(e["event_id"] for e in o_p)},
                ]
                self._finish(ev, supersessions)
                return ev
            in_d = {e["event_id"] for e in o_d}
            matched = [(e, "doi", None) for e in o_d]
            # PMID-only events are linked through the query's own pairing only when DOI events exist.
            link = "query_pair" if o_d else None
            matched += [(e, "pmid", link) for e in o_p if e["event_id"] not in in_d]
            ev.anchor = f"doi:{d}"
        elif d:
            matched = [(e, "doi", None) for e in o_d]
            secondary = sorted({e["original_pmid"] for e in o_d} - {None})
            if len(secondary) > 1:
                ev.issues.append({"code": "IDENTITY_SECONDARY_DIVERGENT", "pmids": secondary})
            elif len(secondary) == 1:
                q = secondary[0]
                matched += [
                    (e, "pmid", "pmid_cooccurrence")
                    for e in self.events_by("original_pmid", q)
                    if not e["original_doi"]
                ]
            ev.anchor = f"doi:{d}"
        elif p:
            dois = sorted({e["original_doi"] for e in o_p} - {None})
            if len(dois) > 1:
                ev.state, ev.identity = "ambiguous_identity", "ambiguous"
                for e in o_p:
                    e["matched_by"], e["linked_via"] = "pmid", None
                ev.events = sorted(o_p, key=lambda e: e["event_id"])
                groups: dict[str, list[str]] = {}
                for e in o_p:
                    groups.setdefault(e["anchor"], []).append(e["event_id"])
                ev.candidate_groups = [{"anchor": a, "event_ids": sorted(ids)} for a, ids in sorted(groups.items())]
                self._finish(ev, supersessions)
                return ev
            matched = [(e, "pmid", None) for e in o_p]
            if dois:
                e2 = dois[0]
                matched += [
                    (e, "doi", "doi_cooccurrence") for e in self.events_by("original_doi", e2) if not e["original_pmid"]
                ]
                ev.anchor = f"doi:{e2}"
            else:
                ev.anchor = f"pmid:{p}"
        if matched:
            ev.state = "matched"
            ev.identity = "bridged" if any(link for _, _, link in matched) else "exact"
            ev.role = "original_and_notice" if notices else "original"
            for e, by, link in matched:
                e["matched_by"], e["linked_via"] = by, link
            ev.events = sorted((e for e, _, _ in matched), key=lambda e: e["event_id"])
            ev.notice_hits = [self._notice_hit(e) for e in notices]
            dois = [e["original_doi"] for e in ev.events if e["original_doi"]]
            ev.crossref = self.crossref_relations(dois)
            ev.checked_sources += self.crossref_sources(dois)
            gap = [h for h in self.relevance([k for k in (d, p) if k]) if h["code"] == "RELEVANT_QUARANTINE"]
            ev.issues += _capped(gap)
            ev.relevant_gap = bool(gap)
        elif notices:
            ev.state, ev.role = "notice_only", "notice"
            for e in notices:
                e["matched_by"], e["linked_via"] = "notice", None
            ev.events = notices
            ev.notice_hits = [self._notice_hit(e) for e in notices]
        else:
            hits = self.relevance([k for k in (d, p) if k])
            ev.issues += _capped(hits)
            ev.relevant_gap = bool(hits)
            ev.checked_sources += self.crossref_sources([d] if d else [])
        self._finish(ev, supersessions)
        return ev

    def _notice_hit(self, e: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": e["event_id"],
            "event_type": e["event_type"],
            "notice_key": e["notice_key"],
            "original_anchor": e["anchor"],
            "original_doi": e["original_doi"],
            "original_pmid": e["original_pmid"],
        }

    def _finish(self, ev: Evidence, supersessions: tuple[tuple[str, str], ...]) -> None:
        assertions: list[policy.TypedAssertion] = []
        for e in ev.events:
            assertions.append(
                policy.TypedAssertion(
                    assertion_id=f"{e['event_id']}/event_type",
                    origin=policy.RW_ORIGIN,
                    channel=RW_CHANNEL,
                    type=e["event_type"],
                    notice_key=e["notice_key"],
                    anchor=e["anchor"],
                    source_ref=self.rw_record_ref(e["ordinal"], e["row_sha256"]),
                    event_id=e["event_id"],
                    notice_date=TemporalEvidence.from_json(e["notice_date"]),
                    bridged=bool(e.get("linked_via")),
                    notice_ambiguous="NOTICE_ALSO_ORIGINAL_ELSEWHERE" in e["flags"],
                )
            )
        for c in ev.crossref:
            ref = {
                "source_id": CR_SOURCE_ID,
                "locator": c["locator"],
                "retrieved_at": c["retrieved_at"],
                "content_sha256": c["payload_sha256"],
            }
            assertions.append(
                policy.TypedAssertion(
                    assertion_id=c["assertion_id"],
                    origin=c["origin"],
                    channel=c["channel"],
                    type=c["mapped_type"],
                    notice_key=c["notice_key"],
                    anchor=f"doi:{c['original_doi']}",
                    source_ref=ref,
                    depends_on=tuple(c["depends_on"]),
                )
            )
        ev.evidence_set = policy.EvidenceSet(
            state=ev.state,
            identity=ev.identity,
            anchor=ev.anchor,
            assertions=tuple(assertions),
            checked_sources=tuple(ev.checked_sources),
            supersessions=supersessions,
            relevant_gap=ev.relevant_gap,
        )


def _capped(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """At most MAX_RELEVANCE_LISTED hits, plus an explicit count when more exist (never a silent cut)."""
    if len(hits) <= MAX_RELEVANCE_LISTED:
        return hits
    capped = {"code": "RELEVANT_LIST_CAPPED", "total": len(hits), "listed": MAX_RELEVANCE_LISTED}
    return [*hits[:MAX_RELEVANCE_LISTED], capped]


def _cursor_token(snapshot_id: str, keys: dict[str, str | None], offset: int) -> str:
    raw = canonical({"o": offset, "q": digest(keys), "s": snapshot_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _cursor_offset(token: str, snapshot_id: str, keys: dict[str, str | None]) -> int:
    try:
        data = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise QueryError("CURSOR_INVALID", "cursor is not readable") from None
    if not isinstance(data, dict) or data.get("s") != snapshot_id or data.get("q") != digest(keys):
        raise QueryError("CURSOR_INVALID", "cursor belongs to another snapshot or query")
    offset = data.get("o")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise QueryError("CURSOR_INVALID", "cursor offset is not a non-negative integer")
    return offset


def public_event(e: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "event_id",
        "event_type",
        "source_label",
        "record_id",
        "anchor",
        "original_doi",
        "original_pmid",
        "notice_doi",
        "notice_pmid",
        "notice_key",
        "notice_date",
        "title",
        "journal",
        "flags",
        "issues",
        "row_sha256",
        "matched_by",
        "linked_via",
    )
    return {k: e.get(k) for k in keep}


def evidence_digest(ev: Evidence, projection: dict[str, Any] | None) -> str:
    return digest(
        {
            "keys": ev.keys,
            "state": ev.state,
            "events": sorted([e["event_id"], e["row_sha256"]] for e in ev.events),
            "identity": ev.identity,
            "projection": projection,
        }
    )


def projection_of(ev: Evidence) -> dict[str, Any] | None:
    if ev.state == "invalid_query" or ev.evidence_set is None:
        return None
    reduced = policy.reduce(ev.evidence_set)
    return {
        "retraction_status": reduced["retraction_status"],
        "retraction_date": reduced["retraction_date"],
        "basis": reduced["basis"],
    }


def render(
    ev: Evidence, snapshot_id: str | None, *, page_size: int = DEFAULT_PAGE, cursor: str | None = None
) -> dict[str, Any]:
    if not 1 <= page_size <= MAX_PAGE:
        raise QueryError("PAGE_SIZE_INVALID", f"page size must be 1 to {MAX_PAGE}")
    offset = _cursor_offset(cursor, snapshot_id or "", ev.keys) if cursor else 0
    projection = projection_of(ev)
    page = ev.events[offset : offset + page_size]
    nxt = offset + page_size
    return {
        "schema_version": SCHEMA_VERSION,
        "policy_version": policy.POLICY_VERSION,
        "snapshot_id": snapshot_id,
        "query": ev.query,
        "lookup_state": ev.state,
        "identifier_role": ev.role,
        "identity": {"status": ev.identity, "anchor": ev.anchor, "candidate_groups": ev.candidate_groups},
        "total_event_count": len(ev.events),
        "events": [public_event(e) for e in page],
        "page": {
            "size": page_size,
            "cursor": cursor,
            "next_cursor": _cursor_token(snapshot_id or "", ev.keys, nxt) if nxt < len(ev.events) else None,
        },
        "notice_hits": ev.notice_hits,
        "checked_sources": ev.checked_sources,
        "issues": ev.issues,
        "projection": projection,
        "evidence_digest": evidence_digest(ev, projection),
    }


def unavailable_result(doi: str | None, pmid: str | None, reason: str) -> dict[str, Any]:
    query, keys, valid = normalize_query(doi, pmid)
    ev = Evidence(query, keys, "invalid_query" if not valid else "unavailable")
    if valid:
        ev.evidence_set = policy.EvidenceSet("unavailable", "none", None, (), ())
        ev.issues.append({"code": "INDEX_UNAVAILABLE", "detail": reason})
    return render(ev, None)


def lookup(
    index_path: Path,
    doi: str | None = None,
    pmid: str | None = None,
    *,
    page_size: int = DEFAULT_PAGE,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Lookup of SPECIFICATION.md 10.3. An index that cannot be opened gives ``unavailable``, never absence."""
    _query, _keys, valid = normalize_query(doi, pmid)
    if not valid:
        return render(Evidence(_query, _keys, "invalid_query"), None, page_size=page_size)
    try:
        index = Index(index_path)
    except IndexUnavailable as exc:
        return unavailable_result(doi, pmid, exc.code)
    with index:
        return render(index.gather(doi, pmid), index.snapshot_id, page_size=page_size, cursor=cursor)


def event_detail(index: Index, event_id: str) -> dict[str, Any] | None:
    """Full event: raw row, identifier occurrences, materialized source assertions, duplicates, Crossref."""
    e = index.event_by_id(event_id)
    if e is None:
        return None
    row = index.conn.execute(
        "SELECT line_start, line_end, fields FROM raw_record WHERE ordinal = ?", (e["ordinal"],)
    ).fetchone()
    fields = json.loads(row[2])
    ref = index.rw_record_ref(e["ordinal"], e["row_sha256"])

    def assertion(predicate: str, subject: str, value: Any, columns: list[str]) -> dict[str, Any]:
        return {
            "assertion_id": f"{event_id}/{predicate}",
            "proposition": {"subject": subject, "predicate": predicate, "value": value},
            "source_ref": ref,
            "lineage": {
                "origin": policy.RW_ORIGIN,
                "channel": RW_CHANNEL,
                "method": "csv-field",
                "payload_sha256": e["row_sha256"],
                "pointer": [f"/fields/{c}" for c in columns],
                "depends_on": [],
            },
        }

    assertions = [
        assertion("event_type", event_id, e["event_type"], ["RetractionNature"]),
        assertion("affects_original", event_id, e["anchor"], ["OriginalPaperDOI", "OriginalPaperPubMedID"]),
        assertion("notice_date", event_id, e["notice_date"], ["RetractionDate"]),
        assertion("original_publication_date", event_id, e["original_date"], ["OriginalPaperDate"]),
    ]
    if e["notice_key"]:
        assertions.append(assertion("has_notice", event_id, e["notice_key"], ["RetractionDOI", "RetractionPubMedID"]))
    if e["original_doi"] and e["original_pmid"]:
        assertions.append(
            assertion(
                "identifier_cooccurs",
                f"row:{e['ordinal']}",
                {"doi": e["original_doi"], "pmid": e["original_pmid"]},
                ["OriginalPaperDOI", "OriginalPaperPubMedID"],
            )
        )
    idents = [
        {
            "role": r[0],
            "scheme": r[1],
            "column": r[2],
            "raw": r[3],
            "input_form": r[4],
            "normalized": r[5],
            "missing": bool(r[6]),
            "transformations": json.loads(r[7]),
            "issues": json.loads(r[8]),
        }
        for r in index.conn.execute(
            "SELECT role, scheme, column_name, raw, input_form, norm, missing, transformations, issues "
            "FROM ident WHERE ordinal = ? ORDER BY id",
            (e["ordinal"],),
        )
    ]
    dups = [
        {
            "kind": k,
            "group_key": g,
            "members": [
                f"row:{o}"
                for (o,) in index.conn.execute(
                    "SELECT ordinal FROM dup_group WHERE kind = ? AND group_key = ? ORDER BY ordinal", (k, g)
                )
            ],
        }
        for k, g in index.conn.execute(
            "SELECT kind, group_key FROM dup_group WHERE ordinal = ? ORDER BY kind, group_key", (e["ordinal"],)
        )
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": index.snapshot_id,
        "event": {k: v for k, v in e.items() if k not in ("matched_by", "linked_via")},
        "raw_record": {
            "ordinal": e["ordinal"],
            "row": f"row:{e['ordinal']}",
            "line_start": row[0],
            "line_end": row[1],
            "fields": dict(zip(index.header, fields, strict=True)),
        },
        "identifiers": idents,
        "assertions": assertions,
        "duplicate_groups": dups,
        "crossref": index.crossref_relations([e["original_doi"]]) if e["original_doi"] else [],
    }
