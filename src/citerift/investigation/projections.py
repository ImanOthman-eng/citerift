"""v1 projections of a Stage 04 report (SPEC 11.2, MR-05, MR-06; Step 10).

One record per distinct work with at least one positive claim, valid against the unchanged contract
``urn:citerift:schema:contracts:v1:investigation`` 1.0.1 (``schemas/contracts`` is never changed).

**Work identity.** A work is the Stage 02 identity anchor (``result.identity.anchor``, ``doi:…`` or ``pmid:…``) of the
deciding lookup of a positive claim. Claims are grouped by anchor only: two anchors are two works even when they
share an identifier, and one anchor is one work whichever keys its citations used. A positive claim whose deciding
lookup has no anchor fails ASSEMBLE closed.

**Stored form.** The blob a projection set names is the v1 record without ``created_at`` (the *body*). ``created_at``
comes from the journal (the ``at`` of ``investigation_created``) and is added only when the record is exported
(``v1_record``), because SPEC 11.2 excludes it from the content digest: ``C(J)``, the projection digests and the
projection-set digest are then functions of the committed content alone, equal for an interrupted-and-resumed run and
an uninterrupted one (MM P6). The v1 schema and semantic checks relate ``created_at`` to no other field
(``citerift.contracts.validate``), so a body is valid exactly when ``body + created_at`` is valid for every valid
timestamp; ``body_problems`` checks it with a fixed timestamp and ``record_problems`` checks an exported record.

**Mapping (lossy points are listed in ``LOSSY``).**

- ``subject_paper.identifiers``: the anchor key, plus the other scheme only when every direct event of the work
  states exactly one value for it;
- ``subject_paper.retraction_status``: Stage 02's projection assertion of the deciding lookup when every contributing
  claim's assertion is identical; when they agree on status and value but differ in provenance, that value with the
  union of their provenance; otherwise ``uncertain`` with value null and a reason (never ``conflicting``: different
  lookups of one work are not sources that disagree);
- ``subject_paper.retraction_date``: the deciding assertion when identical across contributing claims, else omitted;
- ``citations``: one per contributing claim (its unit), in report claim order (``report.claim_key``, whatever the
  order of ``entries``), with the revision's language, title,
  page id, revision id and timestamp; the cited keys as identifiers; provenance names the Stage 03 capture (API URL,
  completion time, ``revision_id=…;sha1=…`` as ``source_version``, the source artifact SHA-256);
- ``events``: every Stage 02 event of the deciding lookups (deduplicated by event id and row hash), one-to-one by
  event type (CP-2), dated by Stage 02's notice date when its effective precision is a day; ordered by time, then
  event id;
- ``status``: the report outcome (S-9.7): ``completed`` or ``partial``;
- ``limitations``: the report's limitation statements, then the work's own lossy points, as ``CODE: text``;
- ``assessments``: empty (Stage 06); ``synthetic``: true only when a checked source of the work says so.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from citerift.contracts.validate import INVESTIGATION_ID
from citerift.investigation import report
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import contracts

V1_VERSION = "1.0.1"
SOURCE_REF_KEYS = ("source_id", "locator", "retrieved_at", "source_version", "content_sha256")
WIKI_SOURCE_ID = "wikimedia-api"
RW_SOURCE_ID = "retraction-watch"
CHECK_TIMESTAMP = "2000-01-01T00:00:00Z"  # body_problems only; never written anywhere

LOSSY = {
    "V1_ONE_RECORD_PER_WORK": "v1 holds one paper per record: the article-revision investigation is split into one "
    "record per positive work, each with the Stage 04 investigation id.",
    "V1_EVENT_DATE_IS_A_DAY": "v1 events need an instant; Stage 02 notice dates are calendar days, so 00:00:00Z marks "
    "only the day (stated in each event's description).",
    "V1_EVENTS_WITHOUT_DAY_OMITTED": "{n} Stage 02 event(s) of this work have no day-precision notice date and are "
    "not v1 events; they stay in the Stage 04 report.",
    "V1_STATUS_NOT_UNIFORM": "the contributing claims of this work have different Stage 02 statuses; v1 states "
    "uncertain and the Stage 04 report keeps each claim.",
    "V1_DATE_NOT_UNIFORM": "the contributing claims of this work have different Stage 02 retraction dates; v1 states "
    "none and the Stage 04 report keeps each.",
    "V1_SECOND_IDENTIFIER_NOT_UNIQUE": "the Stage 02 events of this work state more than one {scheme}; v1 holds only "
    "the anchor identifier.",
    "V1_CLASSES_PER_WORK": "Stage 04 claim classes, rules, reasons and evidence chains of this work are in the "
    "Stage 04 report, not in v1.",
}


class ProjectionError(ValueError):
    """A projection cannot be formed or is invalid; ASSEMBLE fails closed with ``REPORT_INVALID``."""


def anchor_work(anchor: Any) -> dict[str, str]:
    """``doi:X`` → ``{"doi": X}``; ``pmid:P`` → ``{"pmid": P}``. Anything else is refused."""
    if not isinstance(anchor, str) or ":" not in anchor:
        raise ProjectionError(f"a positive claim's deciding lookup has no Stage 02 identity anchor ({anchor!r})")
    scheme, value = anchor.split(":", 1)
    if scheme not in ("doi", "pmid") or not value:
        raise ProjectionError(f"unknown Stage 02 identity anchor {anchor!r}")
    return {scheme: value}


def source_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(value[k]) for k in SOURCE_REF_KEYS if k in value and value[k] is not None}


def _union(refs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by = {canon(source_ref(r)): source_ref(r) for r in refs}
    return [by[k] for k in sorted(by)]


def _status(assertions: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], str | None]:
    first = assertions[0]
    if all(canon(a) == canon(first) for a in assertions):
        return copy.deepcopy(dict(first)), None
    same = all(a.get("status") == first.get("status") and a.get("value") == first.get("value") for a in assertions)
    if same and all(not a.get("alternatives") for a in assertions):
        merged = {k: copy.deepcopy(v) for k, v in first.items() if k != "provenance"}
        merged["provenance"] = _union(r for a in assertions for r in a.get("provenance") or ())
        return merged, None
    values = sorted({str(a.get("value")) for a in assertions})
    reason = "Stage 04 claims of this work have different Stage 02 statuses (" + ", ".join(values) + ")"
    return {"status": "uncertain", "value": None, "reason": reason}, "V1_STATUS_NOT_UNIFORM"


def _event(e: Mapping[str, Any], provenance: list[dict[str, Any]]) -> dict[str, Any] | None:
    nd = e.get("notice_date") or {}
    if nd.get("effective_precision") != "day" or not nd.get("earliest"):
        return None
    flags = ", ".join(nd.get("convention_flags") or []) or "none"
    label = e.get("source_label") or e["event_type"]
    desc = (
        f"Retraction Watch records {label} (event type {e['event_type']}; event {e['event_id']}; record "
        f"{e.get('record_id')}; row sha256 {e['row_sha256']}). Notice date as reported: {nd.get('reported_calendar')} "
        f"(raw {nd.get('raw')!r}; precision day; convention flags: {flags}). The source states a calendar day, not "
        f"an instant: 00:00:00Z marks the day only."
    )
    out: dict[str, Any] = {"at": f"{nd['earliest']}T00:00:00Z", "kind": e["event_type"], "description": desc}
    if provenance:
        out["provenance"] = provenance
    return out


def _lookup_rw(obs: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [source_ref(s) for s in obs["result"]["checked_sources"] if s.get("source_id") == RW_SOURCE_ID]


def build_bodies(
    entries: Sequence[Mapping[str, Any]],
    deciding: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    investigation_id: str,
    root: Mapping[str, Any],
    capture: Mapping[str, Any],
    source_artifact: str,
    outcome: str,
    limitations: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The positive works (report ``positive_work`` items) and the v1 bodies, both in canonical order of the work.

    ``entries`` are the report claim entries in report order; ``deciding(claim)`` returns the deciding lookup
    observation of a positive claim; ``capture`` is the committed Stage 03 ``capture.json``."""
    groups: dict[bytes, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    works: dict[bytes, dict[str, str]] = {}
    for e in entries:
        claim = e["claim"]
        if claim["class"] not in report.POSITIVE:
            continue
        obs = deciding(claim)
        work = anchor_work(obs["result"]["identity"]["anchor"])
        key = canon(work)
        works[key] = work
        groups.setdefault(key, []).append((e, obs))
    positive: list[dict[str, Any]] = []
    bodies: list[dict[str, Any]] = []
    ident = root["subject"]["identity"]
    display = root["subject"]["display"]
    page = capture["page"]
    title = display["title"] if display["title"] is not None else page.get("title")
    if not isinstance(title, str) or not title:
        raise ProjectionError("the revision has no title for the v1 citation")
    sha1 = display["revision_sha1"]
    wiki_ref = {
        "source_id": WIKI_SOURCE_ID,
        "locator": capture["source"]["url"],
        "retrieved_at": capture["finished_at"],
        "source_version": f"revision_id={ident['revision_id']}" + (f";sha1={sha1}" if sha1 else ""),
        "content_sha256": source_artifact,
    }
    article: dict[str, Any] = {"language": ident["wiki"], "title": title, "page_id": ident["page_id"]}
    article["revision_id"] = ident["revision_id"]
    if page.get("revision_timestamp"):
        article["revision_timestamp"] = page["revision_timestamp"]
    for key in sorted(groups):
        work = works[key]
        members = sorted(groups[key], key=lambda m: report.claim_key(m[0]))  # report claim order, whatever the input
        claim_ids = sorted(e["claim"]["claim_id"] for e, _ in members)
        classes = sorted({e["claim"]["class"] for e, _ in members})
        positive.append({"work": dict(work), "classes": classes, "claim_ids": claim_ids})
        lossy: list[str] = ["V1_ONE_RECORD_PER_WORK", "V1_CLASSES_PER_WORK"]
        scheme, value = next(iter(work.items()))
        other = "pmid" if scheme == "doi" else "doi"
        events: dict[tuple[str, str], tuple[Mapping[str, Any], list[dict[str, Any]]]] = {}
        for _, obs in members:
            rw = _lookup_rw(obs)
            for ev in obs["events"]:
                k = (ev["event_id"], ev["row_sha256"])
                if k in events:
                    if canon(_core(events[k][0])) != canon(_core(ev)):
                        raise ProjectionError(f"event {ev['event_id']} differs between lookups of one work")
                    continue
                events[k] = (ev, rw)
        if len({eid for eid, _ in events}) != len(events):
            raise ProjectionError("one event id with two row hashes in one snapshot")
        seconds: set[str] = {
            str(ev[f"original_{other}"])
            for ev, _ in events.values()
            if ev.get("anchor") == f"{scheme}:{value}" and ev.get(f"original_{other}")
        }
        identifiers = dict(work)
        if len(seconds) == 1:
            identifiers[other] = next(iter(seconds))
        elif len(seconds) > 1:
            lossy.append("V1_SECOND_IDENTIFIER_NOT_UNIQUE")
        status, status_lossy = _status([obs["result"]["projection"]["retraction_status"] for _, obs in members])
        paper: dict[str, Any] = {"identifiers": identifiers, "retraction_status": status}
        if status_lossy:
            lossy.append(status_lossy)
        dates = [obs["result"]["projection"].get("retraction_date") for _, obs in members]
        if all(d is not None and canon(d) == canon(dates[0]) for d in dates):
            paper["retraction_date"] = copy.deepcopy(dates[0])
        else:
            lossy.append("V1_DATE_NOT_UNIFORM")
        v1_events = []
        omitted = 0
        for ev, rw in sorted(events.values(), key=lambda x: x[0]["event_id"]):
            mapped = _event(ev, rw)
            if mapped is None:
                omitted += 1
            else:
                v1_events.append((mapped["at"], ev["event_id"], mapped))
        if v1_events:
            lossy.append("V1_EVENT_DATE_IS_A_DAY")
        if omitted:
            lossy.append("V1_EVENTS_WITHOUT_DAY_OMITTED")
        citations = []
        for e, _ in members:
            claim, unit = e["claim"], e["unit"]
            citations.append(
                {
                    "citation_id": f"{ident['wiki']}:{ident['revision_id']}:{unit['unit_id']}:{claim['cand_ref'][:16]}",
                    "article": copy.deepcopy(article),
                    "identifiers": {k["scheme"]: k["normalized"] for k in claim["candidate"]["keys"]},
                    "provenance": [copy.deepcopy(wiki_ref)],
                }
            )
        synthetic = any(s.get("synthetic") is True for _, obs in members for s in obs["result"]["checked_sources"])
        texts = [f"{lim['code']}: {lim['text']}" for lim in limitations]
        texts += [f"{code}: " + LOSSY[code].format(n=omitted, scheme=other.upper()) for code in lossy]
        body: dict[str, Any] = {
            "schema_version": V1_VERSION,
            "investigation_id": investigation_id,
            "status": outcome,
            "subject_paper": paper,
            "citations": citations,
            "assessments": [],
            "events": [m for _, _, m in sorted(v1_events, key=lambda t: (t[0], t[1]))],
            "limitations": texts,
        }
        if synthetic:
            body["synthetic"] = True
        bodies.append(body)
    return positive, bodies


def _core(ev: Mapping[str, Any]) -> dict[str, Any]:
    """An event without the per-lookup matching fields (``matched_by``, ``linked_via``)."""
    return {k: v for k, v in ev.items() if k not in ("matched_by", "linked_via")}


def v1_record(body: Mapping[str, Any], created_at: str) -> dict[str, Any]:
    """The exported v1 record of a stored body."""
    if "created_at" in body:
        raise ProjectionError("a stored projection body must not hold created_at")
    return {**copy.deepcopy(dict(body)), "created_at": created_at}


def record_problems(record: Any) -> list[str]:
    """Schema and semantic problems of a v1 record (``citerift.contracts.validate``); empty when valid."""
    return [str(p) for p in contracts().validate(record, INVESTIGATION_ID)]


def body_problems(body: Any) -> list[str]:
    if not isinstance(body, dict):
        return ["a projection body is not an object"]
    if "created_at" in body:
        return ["a stored projection body holds created_at"]
    return record_problems(v1_record(body, CHECK_TIMESTAMP))


def digest(value: Any) -> str:
    return sha256_hex(canon(value))
