"""NORMALIZE: the committed Stage 03 extraction as typed Stage 04 evidence and candidate inputs (Step 8).

Production transform of SPEC 6.1 to 6.6 and MM 4.1 to 4.4, with no decision-table semantics (no coherence, class,
rule or disposition: those are DETECT, Step 9). It reads only committed content: the ACQUIRE manifest, the extraction
blob and the retained source artifact (raw blob, D-043). It never re-parses wikitext, never normalizes an identifier
itself (keys are exactly Stage 03's ``normalization.normalized``, produced by Stage 02's normalizer), never merges
co-reported identifiers and never infers a negative from a missing identifier.

Evidence (D-051 ids ``H(observation, pointer, kind)``), returned as individual records; the controller batches them
(D-053):

- ``bundle_identity`` at ``/identity`` of the bundle manifest;
- ``extraction_identity`` at ``/extraction_digest`` of the extraction (ref: the bundle identity);
- per unit ``i``: ``unit`` at ``/units/i`` with the D-043 span hash (ref: the extraction identity) and
  ``use_eligibility`` at ``/units/i`` (ref: the unit);
- per identifier ``j``: ``identifier_occurrence`` at ``/identifiers/j`` with its status and key (ref: its unit, or the
  extraction identity when it has none).

The output blob (``candidate-inputs``) lists units, work candidates, observation keys and the lookups to make.
A failure is ``NORMALIZE_INVALID`` (a defect of the committed input: a dangling container or unit, a schema-invalid
document, an anchor that does not verify, a key the Stage 04 key schema refuses); nothing is guessed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from citerift.investigation import ids
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.adapters.acquire import RetentionError, committed_manifest
from citerift.investigation.anchors import SourceArtifact, unit_span_sha256
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.errors import SpanError
from citerift.investigation.schemas import CANDIDATE_INPUTS, COMMON, problems, ref_problems

EXTRACTION_SCHEMA = "urn:citerift:schema:wiki:v1:extraction"
INVALID = "NORMALIZE_INVALID"
CANDIDATE_ROLES = frozenset({"primary_citation_field", "identifier_link"})
CONFIRMED_BOUNDARIES = frozenset({"field", "delimited", "url"})
AMBIGUOUS_STEP = "DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS"
CO_REPORTED = "CO_REPORTED_IDENTIFIERS"
SCHEMA_VERSION = "1.0.0"


class NormalizeInvalid(Exception):
    def __init__(self, detail: str, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail[:1000]
        self.reason = reason


def evidence(kind: str, obs: str, pointer: str, refs: list[str], value: Any) -> dict[str, Any]:
    return {
        "evidence_id": ids.evidence_id(obs, pointer, kind),
        "observation": obs,
        "pointer": pointer,
        "kind": kind,
        "refs": sorted(refs),
        "value": value,
    }


def committed_extraction(req: StepRequest) -> tuple[str, dict[str, Any]]:
    """The committed extraction blob (the EXTRACT output that is a Stage 03 extraction document)."""
    for digest in req.inputs.get("EXTRACT") or ():
        value = req.read_blob(digest)
        if isinstance(value, dict) and value.get("schema") == EXTRACTION_SCHEMA:
            return digest, value
    raise NormalizeInvalid("no committed extraction document")


def eligibility(container: Mapping[str, Any], uses: Mapping[str, Mapping[str, Any]]) -> tuple[str, str | None]:
    """``U(u)`` of SPEC 6.2 / MM 4.2: the first row that holds."""
    if container["binding_state"] == "conflicting_definitions":
        return "USE_NOT_ESTABLISHED", "CONFLICTING_DEFINITIONS"
    if container["kind"] == "bibliography_entry":
        return "CITED", None
    for uid in container["use_ids"]:
        use = uses.get(uid)
        if use is None:
            raise NormalizeInvalid(f"container {container['id']} names a use {uid} the document does not hold")
        if use["binding"] in ("bound", "anonymous"):
            return "CITED", None
    if container["kind"] == "list_defined_note":
        return "UNUSED", "LIST_DEFINED_UNUSED"
    return "USE_NOT_ESTABLISHED", "NO_BOUND_USE"


def named_identifiers(doc: Mapping[str, Any]) -> set[str]:
    """Identifier ids named by an extraction exception, or by an ``IDENTIFIER_*`` issue other than
    ``CO_REPORTED_IDENTIFIERS`` (SPEC 6.3)."""
    named = {e["entity"] for e in doc["exceptions"]}
    for issue in doc["issues"]:
        if issue["code"].startswith("IDENTIFIER_") and issue["code"] != CO_REPORTED:
            named.update(issue.get("entities") or ())
    return named


def status_of(ident: Mapping[str, Any], named: set[str]) -> str:
    """Occurrence status of SPEC 6.3 / MM 4.3 (``OBSERVATION_ROLE`` for the roles that are not candidate roles)."""
    if ident["role"] not in CANDIDATE_ROLES:
        return "OBSERVATION_ROLE"
    norm = ident["normalization"]
    if norm is None or not norm["valid"]:
        return "MALFORMED"
    steps = (ident["decoding"] or {}).get("structural_steps") or []
    if ident["boundary"] in CONFIRMED_BOUNDARIES and AMBIGUOUS_STEP not in steps and ident["id"] not in named:
        return "CONFIRMED"
    return "UNCONFIRMED"


def key_of(ident: Mapping[str, Any]) -> dict[str, str] | None:
    """The key Stage 03 recorded (Stage 02's normalizer), or None when it gives none. Never re-normalized."""
    norm = ident["normalization"]
    if norm is None or not norm["valid"] or not isinstance(norm.get("normalized"), str):
        return None
    if norm["scheme"] != ident["scheme"]:
        raise NormalizeInvalid(f"identifier {ident['id']} has a normalization of another scheme")
    key = {"scheme": ident["scheme"], "normalized": norm["normalized"]}
    found = ref_problems(key, COMMON + "#/$defs/key")
    if found:
        raise NormalizeInvalid(f"identifier {ident['id']} gives a key the Stage 04 key schema refuses: {found[0]}")
    return key


def _key_tuple(k: Mapping[str, str]) -> tuple[str, str]:
    return (k["scheme"], k["normalized"])


def normalize(req: StepRequest) -> StepResult:
    """The NORMALIZE adapter."""
    try:
        return _normalize(req)
    except NormalizeInvalid as exc:
        return Failed(INVALID, reason=exc.reason, detail=exc.detail)
    except SpanError as exc:  # D-043 fails closed: no new identity is created
        return Failed(INVALID, reason=exc.code, detail=f"D-043: {exc.detail}"[:1000])
    except RetentionError as exc:
        return Failed(INVALID, detail=exc.detail)


def _normalize(req: StepRequest) -> StepResult:
    if req.root is None:
        raise NormalizeInvalid("no bound root")
    root_identity = req.root["subject"]["identity"]
    manifest = committed_manifest(req)
    manifest_digest = sha256_hex(canon(manifest))
    ext_digest, doc = committed_extraction(req)
    found = problems(doc, EXTRACTION_SCHEMA)
    if found:
        raise NormalizeInvalid("the committed extraction is not schema-valid: " + "; ".join(found[:3]))
    if doc["status"] not in ("complete", "partial"):
        raise NormalizeInvalid(f"the committed extraction has status {doc['status']!r}")
    cap = doc["capture"]
    for name in ("wiki", "page_id", "revision_id", "capture_sha256"):
        if cap[name] != root_identity[name] or manifest["identity"][name] != root_identity[name]:
            raise NormalizeInvalid(f"the extraction's {name} is not the bound root's", "ROOT_IDENTITY_MISMATCH")
    if cap["source_artifact"] != manifest["source"]["artifact"]:
        raise NormalizeInvalid("the extraction names another source artifact than the bundle", "SOURCE_DIGEST_MISMATCH")
    source = SourceArtifact(req.read_bytes(cap["source_artifact"]), cap["source_artifact"])

    items: list[dict[str, Any]] = []
    ev_bundle = evidence("bundle_identity", manifest_digest, "/identity", [], None)
    ev_ext = evidence("extraction_identity", ext_digest, "/extraction_digest", [ev_bundle["evidence_id"]], None)
    items += [ev_bundle, ev_ext]

    containers = {c["id"]: c for c in doc["containers"]}
    uses = {u["id"]: u for u in doc["uses"]}
    by_span: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for ident in doc["identifiers"]:
        anchor = ident.get("source")
        if isinstance(anchor, Mapping):
            by_span.setdefault((anchor.get("byte_start"), anchor.get("byte_end")), []).append(ident)  # type: ignore[arg-type]

    units: list[dict[str, Any]] = []
    unit_index: dict[str, dict[str, Any]] = {}
    for i, unit in enumerate(doc["units"]):
        container = containers.get(unit["container_id"])
        if container is None:
            raise NormalizeInvalid(f"unit {unit['id']} names a container the document does not hold")
        if unit["id"] in unit_index:
            raise NormalizeInvalid(f"unit id {unit['id']} occurs twice")
        span = unit["source"]
        same = by_span.get((span.get("byte_start"), span.get("byte_end")), [])
        span_hash = unit_span_sha256(
            source, span, extraction_capture=cap, root_capture_sha256=root_identity["capture_sha256"], identifiers=same
        )
        pointer = f"/units/{i}"
        ev_unit = evidence(
            "unit",
            ext_digest,
            pointer,
            [ev_ext["evidence_id"]],
            {"source_artifact": source.sha256, "unit_span_sha256": span_hash},
        )
        elig, reason = eligibility(container, uses)
        ev_elig = evidence(
            "use_eligibility", ext_digest, pointer, [ev_unit["evidence_id"]], {"eligibility": elig, "reason": reason}
        )
        items += [ev_unit, ev_elig]
        entry = {
            "unit_id": unit["id"],
            "pointer": pointer,
            "unit_ref": ids.unit_ref(req.root["root_id"], unit["id"], span["byte_start"], span["byte_end"], span_hash),
            "eligibility": elig,
            "reason": reason,
            "taint": [],
            "evidence": {"unit": ev_unit["evidence_id"], "use_eligibility": ev_elig["evidence_id"]},
            "occurrences": [],
        }
        units.append(entry)
        unit_index[unit["id"]] = entry

    named = named_identifiers(doc)
    # per unit: (key, status, evidence id) of every candidate-role occurrence that is not MALFORMED
    keyed: dict[str, list[tuple[dict[str, str], str, str]]] = {u["unit_id"]: [] for u in units}
    taint: dict[str, set[str]] = {u["unit_id"]: set() for u in units}
    observation: dict[tuple[str, str], list[str]] = {}
    for j, ident in enumerate(doc["identifiers"]):
        unit = unit_index.get(ident["unit_id"]) if ident["unit_id"] is not None else None
        if ident["unit_id"] is not None and unit is None:
            raise NormalizeInvalid(f"identifier {ident['id']} names a unit the document does not hold")
        status = status_of(ident, named)
        key = key_of(ident) if status != "MALFORMED" else None
        if status in ("CONFIRMED", "UNCONFIRMED") and key is None:
            raise NormalizeInvalid(f"identifier {ident['id']} is valid but gives no key")
        parent = unit["evidence"]["unit"] if unit is not None else ev_ext["evidence_id"]
        ev_occ = evidence(
            "identifier_occurrence", ext_digest, f"/identifiers/{j}", [parent], {"status": status, "key": key}
        )
        items.append(ev_occ)
        eid = ev_occ["evidence_id"]
        if unit is not None:
            unit["occurrences"].append(eid)
            uid = unit["unit_id"]
            if ident["role"] == "unresolved":
                taint[uid].add("IDENTIFIER_ROLE_UNRESOLVED")
            if status == "UNCONFIRMED":
                taint[uid].add("IDENTIFIER_UNCONFIRMED")
            if status == "MALFORMED":
                taint[uid].add("IDENTIFIER_MALFORMED")
            if status in ("CONFIRMED", "UNCONFIRMED") and key is not None:
                keyed[uid].append((key, status, eid))
        if key is not None and (unit is None or status == "OBSERVATION_ROLE"):
            observation.setdefault(_key_tuple(key), []).append(eid)  # S-6.7: looked up, never deciding

    candidates: list[dict[str, Any]] = []
    for u in units:
        u["taint"] = sorted(taint[u["unit_id"]])
        occ = keyed[u["unit_id"]]
        dois = sorted({k["normalized"] for k, _, _ in occ if k["scheme"] == "doi"})
        pmids = sorted({k["normalized"] for k, _, _ in occ if k["scheme"] == "pmid"})
        groups: list[tuple[list[dict[str, str]], list[str]]]
        if not dois and not pmids:
            groups, flags = [([], [])], list[str]()
        elif len(dois) <= 1 and len(pmids) <= 1:
            groups = [
                (
                    [{"scheme": "doi", "normalized": d} for d in dois]
                    + [{"scheme": "pmid", "normalized": p} for p in pmids],
                    [],
                )
            ]
            flags = []
        else:
            groups = [([{"scheme": "doi", "normalized": d}], []) for d in dois]
            groups += [([{"scheme": "pmid", "normalized": p}], []) for p in pmids]
            flags = ["CO_REPORTED_MULTIPLE"] + (["PAIRING_NOT_DETERMINED"] if dois and pmids else [])
        for keys, _ in groups:
            wanted = {_key_tuple(k) for k in keys}
            shape = "NONE" if not keys else ("PAIR" if len(keys) == 2 else keys[0]["scheme"].upper())
            candidates.append(
                {
                    "cand_ref": ids.cand_ref(u["unit_ref"], keys),
                    "unit_id": u["unit_id"],
                    "unit_ref": u["unit_ref"],
                    "shape": shape,
                    "keys": keys,
                    "flags": flags,
                    "taint": u["taint"],
                    "key_evidence": [eid for k, _, eid in occ if _key_tuple(k) in wanted],
                }
            )

    queries: set[tuple[str | None, str | None]] = set()
    for c in candidates:
        for k in c["keys"]:
            queries.add((k["normalized"], None) if k["scheme"] == "doi" else (None, k["normalized"]))
        if c["shape"] == "PAIR":
            queries.add((c["keys"][0]["normalized"], c["keys"][1]["normalized"]))
    for scheme, value in observation:
        queries.add((value, None) if scheme == "doi" else (None, value))
    output = {
        "schema": CANDIDATE_INPUTS,
        "schema_version": SCHEMA_VERSION,
        "root_id": req.root["root_id"],
        "bundle": manifest_digest,
        "extraction": ext_digest,
        "identity_evidence": {
            "bundle_identity": ev_bundle["evidence_id"],
            "extraction_identity": ev_ext["evidence_id"],
        },
        "units": units,
        "candidates": candidates,
        "observation_keys": [
            {"key": {"scheme": s, "normalized": v}, "evidence": eids} for (s, v), eids in sorted(observation.items())
        ],
        "queries": [{"doi": d, "pmid": p} for d, p in sorted(queries, key=lambda q: (q[0] or "", q[1] or ""))],
    }
    found = problems(output, CANDIDATE_INPUTS)
    if found:
        raise NormalizeInvalid("the candidate inputs do not validate: " + "; ".join(found[:3]))
    digest = sha256_hex(canon(output))
    return Succeeded(records=tuple(ContentRecord("evidence", e) for e in items), blobs=(output,), outputs=(digest,))
