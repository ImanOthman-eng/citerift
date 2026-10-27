"""Record dispositions, identifier occurrences and events (SPECIFICATION.md sections 5.4, 5.5, 6.3, 7)."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from citerift.retraction.dates import TemporalEvidence, definitely_before, parse_rw_date
from citerift.retraction.identifiers import Normalized, normalize_doi, normalize_pmid
from citerift.retraction.source import RawRecord

EVENT_TYPES = {
    "Retraction": "retracted",
    "Expression of concern": "expression_of_concern",
    "Correction": "correction",
    "Reinstatement": "reinstated",
}
IDENT_FIELDS = (
    ("original", "doi", "OriginalPaperDOI"),
    ("original", "pmid", "OriginalPaperPubMedID"),
    ("notice", "doi", "RetractionDOI"),
    ("notice", "pmid", "RetractionPubMedID"),
)


def event_id(ordinal: int) -> str:
    return f"ev-{ordinal:07d}"


@dataclass(frozen=True)
class IdentOccurrence:
    ordinal: int
    role: str
    scheme: str
    column: str
    norm: Normalized


@dataclass
class Event:
    event_id: str
    ordinal: int
    event_type: str
    source_label: str
    record_id: str
    original_doi: str | None
    original_pmid: str | None
    notice_doi: str | None  # notice-role DOI key, excluding a key equal to the original DOI
    notice_pmid: str | None
    anchor: str
    notice_key: str | None
    notice_date: TemporalEvidence
    original_date: TemporalEvidence
    title: str
    authors: str
    journal: str
    flags: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def original_year(self) -> int | None:
        rc = self.original_date.reported_calendar
        return int(rc[:4]) if rc else None


@dataclass
class Disposition:
    record: RawRecord
    record_id: str
    accepted: bool
    reasons: tuple[str, ...]
    idents: tuple[IdentOccurrence, ...]
    event: Event | None


def dispose(record: RawRecord, header: list[str]) -> Disposition:
    """Accept or quarantine one record and derive its identifier occurrences and event."""
    if len(record.fields) != len(header):
        return Disposition(record, "", False, ("FIELD_COUNT_MISMATCH",), (), None)
    row = dict(zip(header, record.fields, strict=True))
    record_id = row["Record ID"]
    idents = []
    for role, scheme, column in IDENT_FIELDS:
        norm = (normalize_doi if scheme == "doi" else normalize_pmid)(row[column], source_field=True)
        idents.append(IdentOccurrence(record.ordinal, role, scheme, column, norm))
    label = row["RetractionNature"]
    if label == "":
        return Disposition(record, record_id, False, ("EVENT_TYPE_MISSING",), tuple(idents), None)
    if label not in EVENT_TYPES:
        return Disposition(record, record_id, False, ("EVENT_TYPE_UNKNOWN",), tuple(idents), None)
    od, op, nd, np_ = (i.norm.normalized for i in idents)
    flags: list[str] = []
    issues: list[str] = []
    for occ in idents:
        if not occ.norm.valid and not occ.norm.missing:
            issues.append(f"{occ.role.upper()}_{occ.scheme.upper()}_INVALID")
        issues.extend(f"{occ.role.upper()}_{code}" for code in occ.norm.issues)
    if nd is not None and nd == od:
        flags.append("NOTICE_DOI_EQUALS_ORIGINAL")
        nd = None
    if np_ is not None and np_ == op:
        flags.append("NOTICE_PMID_EQUALS_ORIGINAL")
        np_ = None
    if od is not None:
        anchor = f"doi:{od}"
    elif op is not None:
        anchor = f"pmid:{op}"
        flags.append("ORIGINAL_ANCHOR_PMID_ONLY")
    else:
        anchor = f"rec:{record.ordinal}"
        flags.append("ORIGINAL_ANCHOR_SOURCE_RECORD_ONLY")
    notice_key = f"doi:{nd}" if nd is not None else (f"pmid:{np_}" if np_ is not None else None)
    if notice_key is None and "NOTICE_DOI_EQUALS_ORIGINAL" not in flags:
        flags.append("NO_NOTICE_IDENTIFIER")
    notice_date = parse_rw_date(row["RetractionDate"], "notice_date")
    original_date = parse_rw_date(row["OriginalPaperDate"], "original_publication_date")
    for ev in (notice_date, original_date):
        issues.extend(f"{ev.kind.upper()}_{code}" for code in ev.issues)
    if record_id == "":
        issues.append("RECORD_ID_MISSING")
    elif not (record_id.isascii() and record_id.isdigit()):
        issues.append("RECORD_ID_NONNUMERIC")
    if definitely_before(notice_date, original_date):
        issues.append("NOTICE_BEFORE_ORIGINAL_PUBLICATION")
    event = Event(
        event_id=event_id(record.ordinal),
        ordinal=record.ordinal,
        event_type=EVENT_TYPES[label],
        source_label=label,
        record_id=record_id,
        original_doi=od,
        original_pmid=op,
        notice_doi=nd,
        notice_pmid=np_,
        anchor=anchor,
        notice_key=notice_key,
        notice_date=notice_date,
        original_date=original_date,
        title=row.get("Title", ""),
        authors=row.get("Author", ""),
        journal=row.get("Journal", ""),
        flags=flags,
        issues=sorted(set(issues)),
    )
    return Disposition(record, record_id, True, (), tuple(idents), event)


@dataclass(frozen=True)
class DupMember:
    kind: str
    group_key: str
    ordinal: int


def finalize_events(events: list[Event]) -> None:
    """Flags that need the whole snapshot: shared notices and notices that are originals elsewhere."""
    notice_use = Counter(e.notice_key for e in events if e.notice_key)
    originals: dict[str, set[int]] = defaultdict(set)
    for e in events:
        if e.original_doi:
            originals[e.original_doi].add(e.ordinal)
    for e in events:
        if e.notice_key and notice_use[e.notice_key] > 1:
            e.flags.append("NOTICE_SHARED")
        if e.notice_doi and originals.get(e.notice_doi, set()) - {e.ordinal}:
            e.flags.append("NOTICE_ALSO_ORIGINAL_ELSEWHERE")
        e.flags.sort()


def duplicate_groups(
    records: Iterable[tuple[int, str, str]], events: list[Event], row_sha: dict[int, str]
) -> list[DupMember]:
    """Duplicate groups of SPECIFICATION.md 5.5. ``records`` yields (ordinal, record_id, row_sha256)."""
    by_sha: dict[str, list[int]] = defaultdict(list)
    by_id: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for ordinal, record_id, sha in records:
        by_sha[sha].append(ordinal)
        if record_id:
            by_id[record_id].append((ordinal, sha))
    out: list[DupMember] = []
    for sha, ords in by_sha.items():
        if len(ords) > 1:
            out += [DupMember("identical_record", sha, o) for o in ords]
    for rid, members in by_id.items():
        if len({sha for _, sha in members}) > 1:
            out += [DupMember("record_id_reused", rid, o) for o, _ in members]
    by_sig: dict[str, list[int]] = defaultdict(list)
    for e in events:
        sig = f"{e.anchor}|{e.event_type}|{e.notice_key or ''}|{e.notice_date.reported_calendar or ''}"
        by_sig[sig].append(e.ordinal)
    for sig, ords in by_sig.items():
        if len({row_sha[o] for o in ords}) > 1:
            out += [DupMember("same_event_signature", sig, o) for o in ords]
    return sorted(out, key=lambda m: (m.kind, m.group_key, m.ordinal))
