"""Deterministic extraction from a capture bundle (SPECIFICATION.md 10-14).

``extract_bundle`` runs the extraction in a separate worker process with an address-space limit and a wall-clock
deadline (``worker.py``); the worker calls ``extract_document``, which reads only the bundle: no network, no clock,
no environment. The same bundle, configuration, profile and parser versions give byte-identical output, and the
document carries the SHA-256 of its own canonical form (``extraction_digest``).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from citerift.wiki import __version__
from citerift.wiki.bundle import Bundle, BundleError, open_bundle
from citerift.wiki.canonical import StrictJSONError, canonical_bytes, digest, loads_strict, sha256_hex
from citerift.wiki.issues import Issue, sort_issues
from citerift.wiki.markers import observe
from citerift.wiki.model import SourceModel, build
from citerift.wiki.profile import Profile, load_profile
from citerift.wiki.reconcile import reconcile
from citerift.wiki.render import HTML_PARSER, HTML_PARSER_VERSION, LIBXML_VERSION, RenderLimitExceeded, read_render
from citerift.wiki.source import PARSER_NAME, PARSER_VERSION, LimitExceeded, Limits, SourceScan, scan_source
from citerift.wiki.textmap import ByteMap

EXTRACTION_SCHEMA = "urn:citerift:schema:wiki:v1:extraction"
SCHEMA_VERSION = "1.0.0"
MAX_OUTPUT_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class ExtractConfig:
    max_nodes: int = 400_000
    max_depth: int = 60
    max_refs: int = 20_000
    max_templates: int = 50_000
    max_candidates: int = 50_000
    max_render_elements: int = 2_000_000
    worker_memory_mib: int = 512
    worker_wall_s: float = 30.0

    def limits(self) -> Limits:
        return Limits(self.max_nodes, self.max_depth, self.max_refs, self.max_templates, self.max_candidates)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ExtractConfig:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        if set(data) - set(known):
            raise ValueError(f"unknown configuration keys {sorted(set(data) - set(known))}")
        return cls(**known)


def extractor_identity(profile: Profile) -> dict[str, Any]:
    return {
        "name": "citerift-wiki",
        "version": __version__,
        "profile": {"version": profile.version, "digest": profile.digest},
        "parsers": {
            "wikitext": f"{PARSER_NAME} {PARSER_VERSION}",
            "html": f"{HTML_PARSER} {HTML_PARSER_VERSION} (libxml2 {LIBXML_VERSION})",
        },
        "normalizer": "citerift.retraction.identifiers (Stage 02)",
    }


# Assembly ---------------------------------------------------------------------------------------------------


def _span(bmap: ByteMap, start: int, end: int) -> dict[str, int]:
    b0, b1 = bmap.interval(start, end)
    return {"cp_start": start, "cp_end": end, "byte_start": b0, "byte_end": b1}


def _anchor(bmap: ByteMap, text: str, start: int, end: int) -> dict[str, Any]:
    raw = text[start:end]
    return {**_span(bmap, start, end), "raw": raw, "raw_sha256": sha256_hex(raw.encode("utf-8")), "exact": True}


def _template_ref(model: SourceModel, index: int | None) -> dict[str, Any] | None:
    if index is None or index not in model.templates:
        return None
    t = model.templates[index]
    return {"name": t.raw_name.strip(), "canonical": t.canonical, "kind": t.kind, "family": t.family}


@dataclass
class _Doc:
    issues: list[Issue] = field(default_factory=list)
    exceptions: list[dict[str, Any]] = field(default_factory=list)

    def ledger(self, entity: str, entity_type: str, code: str, detail: str = "") -> None:
        self.exceptions.append({"entity": entity, "entity_type": entity_type, "code": code, "detail": detail})


def _source_component(scan: SourceScan, doc: _Doc, bmap: ByteMap) -> str:
    state = "complete"
    for start, end, kind in scan.inexact:
        doc.issues.append(Issue("ANCHOR_NOT_EXACT", (), f"{kind} at code points {start}-{end}"))
        doc.ledger(f"source:{start}-{end}", "source_region", "ANCHOR_NOT_EXACT", kind)
        state = "partial"
    for start, end, kind in scan.unparsed:
        doc.issues.append(Issue("UNPARSED_MARKUP", (), f"{kind} at code points {start}-{end}"))
        doc.ledger(f"source:{start}-{end}", "source_region", "UNPARSED_MARKUP", kind)
        state = "partial"
    for start, end in scan.unclosed_refs:
        doc.issues.append(Issue("REF_UNCLOSED", (), f"code points {start}-{end}"))
        doc.ledger(f"source:{start}-{end}", "source_region", "REF_UNCLOSED", "")
        state = "partial"
    for start, end, kind in scan.unsupported:
        doc.issues.append(Issue("UNPARSED_MARKUP", (), f"{kind} at code points {start}-{end}"))
        doc.ledger(f"source:{start}-{end}", "source_region", "UNPARSED_MARKUP", kind)
    del bmap
    return state


def extract_document(bundle: Bundle, config: ExtractConfig) -> dict[str, Any]:
    """The extraction document for one bundle (in this process; ``extract_bundle`` isolates it)."""
    profile = load_profile()
    cap = bundle.capture
    page = cap.get("page") or {}
    wiki = page.get("wiki")
    doc = _Doc()
    out: dict[str, Any] = {
        "schema": EXTRACTION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "extractor": extractor_identity(profile),
        "config": config.to_json(),
        "config_digest": digest(config.to_json()),
        "capture": {
            "capture_sha256": bundle.capture_sha256,
            "wiki": wiki,
            "page_id": page.get("page_id"),
            "title": page.get("title"),
            "revision_id": page.get("revision_id"),
            "sha1": page.get("sha1"),
            "source_artifact": (cap.get("source") or {}).get("artifact"),
            "render_artifact": (cap.get("render") or {}).get("artifact"),
            "render_state": (cap.get("render") or {}).get("state"),
        },
    }
    if wiki not in profile.wikis or not cap.get("source"):
        doc.issues.append(Issue("BUNDLE_SEMANTIC_INVALID", (), "the capture holds no supported source"))
        return _finalize(out, doc, "failed", {"source": {"state": "failed"}}, {})
    w = profile.wikis[wiki]
    text_bytes = bundle.artifact(cap["source"]["artifact"], limit=4 * 1024 * 1024)
    text = text_bytes.decode("utf-8", "strict")
    bmap = ByteMap(text)
    components: dict[str, Any] = {}
    try:
        scan = scan_source(text, w, profile, config.limits())
        model = build(scan, w, profile, bmap)
    except LimitExceeded as exc:
        doc.issues.append(Issue(exc.code, (), exc.detail))
        components["source"] = {"state": "failed", "code": exc.code}
        return _finalize(out, doc, "failed", components, {})
    except RecursionError:
        doc.issues.append(Issue("LIMIT_DEPTH", (), "the parser's recursion limit"))
        components["source"] = {"state": "failed", "code": "LIMIT_DEPTH"}
        return _finalize(out, doc, "failed", components, {})
    components["source"] = {"state": _source_component(scan, doc, bmap)}
    doc.issues.extend(model.issues)

    # Render ---------------------------------------------------------------------------------------------
    render = reader = rec = None
    render_state = cap.get("render", {}).get("state", "not_requested")
    if render_state == "captured":
        try:
            html = bundle.artifact(cap["render"]["artifact"], limit=16 * 1024 * 1024)
            render, reader = read_render(html, config.max_render_elements)
        except RenderLimitExceeded as exc:
            doc.issues.append(Issue("LIMIT_OCCURRENCES", (), f"render: {exc}"))
            render_state = "failed"
        except (ValueError, SyntaxError) as exc:
            doc.issues.append(Issue("RENDER_PARSE_FAILED", (), type(exc).__name__))
            render_state = "failed"
        else:
            if render.revision_about not in (None, page.get("revision_id")):
                doc.issues.append(Issue("RENDER_REVISION_MISMATCH", (), f"document states {render.revision_about}"))
                render = reader = None
                render_state = "rejected"
            else:
                rec = reconcile(model, render, w, profile, text)
                doc.issues.extend(rec.issues)
                for dup in render.duplicate_ids:
                    doc.issues.append(Issue("DOM_ID_DUPLICATE", (), dup))
                if render.data_mw_errors:
                    doc.issues.append(Issue("RENDER_DATA_MW_INVALID", (), f"{render.data_mw_errors} attributes"))
                for warning, count in sorted(Counter(w["warning"] for w in render.limit_warnings).items()):
                    doc.issues.append(Issue("RENDER_TEMPLATE_OMITTED", (), f"{count} x {warning}"))
    else:
        doc.issues.append(Issue("RECONCILIATION_UNAVAILABLE", (), f"render {render_state}"))
    components["render"] = {"state": "complete" if render is not None else render_state}
    if render is not None and render.limit_warnings:
        components["render"] = {"state": "partial", "reason": "MediaWiki omitted templates (parser limits)"}

    observations = observe(model, rec, render, reader, w, render_state)
    body = _assemble(model, scan, rec, render, reader, observations, text, bmap, doc)
    out.update(body)
    if rec is None:
        components["reconciliation"] = {"state": "not_run"}
    else:
        partial = any(s != "matched" for s in rec.use_state.values()) or any(
            s != "matched" for c, s in rec.container_state.items()
        )
        components["reconciliation"] = {"state": "partial" if partial else "complete"}
    marker_states = Counter(o.state for o in observations)
    if render is None:
        components["markers"] = {"state": "not_run"}
    elif marker_states.get("not_inspected", 0):
        components["markers"] = {"state": "partial"}
    else:
        components["markers"] = {"state": "complete"}
    states = [c["state"] for c in components.values()]
    status = "complete" if all(s == "complete" for s in states) else "partial"
    return _finalize(out, doc, status, components, body.get("accounting", {}))


def _assemble(
    model: SourceModel,
    scan: SourceScan,
    rec: Any,
    render: Any,
    reader: Any,
    observations: list[Any],
    text: str,
    bmap: ByteMap,
    doc: _Doc,
) -> dict[str, Any]:
    has_render = rec is not None
    defs_by_container: dict[str, list[dict[str, Any]]] = {}
    containers = []
    for c in model.containers:
        defs = []
        for i, d in enumerate(c.definitions):
            defs.append(
                {
                    "id": f"{c.id}/d{i + 1}",
                    "origin": d["origin"],
                    "zone": d["zone"],
                    "source": _span(bmap, *d["_span"]),
                    "body": _span(bmap, *d["_body"]),
                }
            )
        defs_by_container[c.id] = defs
        render_part: dict[str, Any] = {"state": "not_reconciled"}
        if has_render:
            render_part = {
                "state": rec.container_state.get(c.id, "unmatched"),
                "region_id": rec.container_note.get(c.id),
            }
            if render_part["state"] != "matched" and c.kind != "bibliography_entry":
                doc.ledger(c.id, "container", "SOURCE_ONLY", f"render state {render_part['state']}")
        containers.append(
            {
                "id": c.id,
                "kind": c.kind,
                "layout": c.layout,
                "group": c.group,
                "name": c.name,
                "name_raw": c.name_raw,
                "group_raw": c.group_raw,
                "binding_state": c.binding_state,
                "source": _span(bmap, c.start, c.end),
                "definitions": defs,
                "use_ids": sorted(c.use_ids),
                "unit_ids": sorted(c.unit_ids),
                "render": render_part,
            }
        )
    uses = []
    for u in model.uses:
        r = model.refs[u.ref]
        render_part = {"state": "not_reconciled"}
        if has_render:
            state = rec.use_state.get(u.id, "abstained")
            render_part = {"state": state, "basis": rec.use_basis.get(u.id)}
            if u.id in rec.use_match:
                ru = render.uses[rec.use_match[u.id]]
                render_part.update({"locator": ru.locator.to_json(), "target_note": ru.target_note})
            else:
                doc.ledger(u.id, "use", "RECONCILIATION_ABSTAINED", "no render use paired")
        if u.binding in ("definition_missing", "unbindable_name"):
            doc.ledger(
                u.id,
                "use",
                "REF_DEFINITION_MISSING" if u.binding == "definition_missing" else "REF_NAME_HAS_MARKUP",
                u.binding,
            )
        uses.append(
            {
                "id": u.id,
                "container_id": u.container_id,
                "origin": u.origin,
                "zone": u.zone,
                "group": u.group,
                "name": u.name,
                "binding": u.binding,
                "position": u.position,
                "source": _span(bmap, r.start, r.end),
                "template": _template_ref(model, u.template),
                "render": render_part,
            }
        )
    units = []
    for un in model.units:
        render_part = {"state": "not_reconciled"}
        if has_render:
            about = rec.unit_transclusion.get(un.id)
            omitted = None
            if about is not None:
                omitted = next((t.omitted for t in render.transclusions if t.about == about), None)
            render_part = {
                "state": rec.unit_state.get(un.id, "unmatched"),
                "transclusion": about,
                "template_omitted": omitted,
            }
        units.append(
            {
                "id": un.id,
                "container_id": un.container_id,
                "definition_id": un.definition_id,
                "kind": un.kind,
                "template": _template_ref(model, un.template),
                "source": _span(bmap, un.start, un.end),
                "parent_unit": un.parent_unit,
                "duplicate_params": un.duplicate_params,
                "identifier_ids": sorted(un.identifier_ids),
                "render": render_part,
            }
        )
    identifiers = []
    for o in model.occurrences:
        cand = o.cand
        render_part = {"state": "not_reconciled", "witnesses": []}
        if has_render:
            render_part = {
                "state": rec.witness_state.get(o.id, "not_comparable"),
                "witnesses": [render.links[i].locator.to_json() for i in rec.witnesses.get(o.id, [])],
            }
        normalization = o.decoded.normalized.to_json() if o.decoded is not None else None
        if o.role == "unresolved":
            doc.ledger(o.id, "identifier", "TEMPLATE_UNSUPPORTED", o.role_reason)
        if o.decoded is None:
            doc.ledger(o.id, "identifier", "IDENTIFIER_VALUE_HAS_MARKUP", "not normalized")
        elif not o.decoded.normalized.valid and not o.decoded.normalized.missing:
            doc.ledger(o.id, "identifier", "IDENTIFIER_INVALID", ",".join(o.decoded.normalized.issues))
        if cand.boundary == "ambiguous_trailing_punctuation":
            doc.ledger(o.id, "identifier", "IDENTIFIER_BOUNDARY_AMBIGUOUS", cand.raw[-1:])
        identifiers.append(
            {
                "id": o.id,
                "scheme": cand.scheme,
                "role": o.role,
                "role_reason": o.role_reason,
                "origin": cand.origin,
                "container_id": o.container_id,
                "unit_id": o.unit_id,
                "boundary": cand.boundary,
                "context": {
                    "template": _template_ref(model, cand.template),
                    "param": cand.param,
                    "in_link_text": cand.link_display,
                },
                "source": _anchor(bmap, text, cand.start, cand.end),
                "decoding": None
                if o.decoded is None
                else {
                    "input_steps": list(cand.steps),
                    "structural_steps": list(o.decoded.steps),
                    "normalizer_input": o.decoded.normalizer_input,
                },
                "normalization": normalization,
                "render": render_part,
            }
        )
    excluded = [
        {"scheme": c.scheme, "reason": c.excluded, "source": _anchor(bmap, text, c.start, c.end)}
        for c in sorted(scan.excluded_candidates, key=lambda c: (c.start, c.end, c.scheme))
    ]
    markers = [o.to_json() for o in observations]
    render_only: dict[str, Any] = {"uses": [], "identifiers": [], "limit_warnings": []}
    if has_render:
        for idx in rec.unmatched_render_uses:
            ru = render.uses[idx]
            tr = next((t for t in render.transclusions if t.about == ru.in_transclusion), None)
            render_only["uses"].append(
                {
                    "locator": ru.locator.to_json(),
                    "name": ru.name,
                    "group": ru.group,
                    "target_note": ru.target_note,
                    "in_template": tr.templates[0][0].strip() if tr is not None and tr.templates else None,
                    "in_note": ru.in_note,
                }
            )
            doc.ledger(
                f"render-use:{ru.locator.path}",
                "render_use",
                "RENDER_USE_UNMATCHED",
                f"in template output {render_only['uses'][-1]['in_template']}",
            )
        for item in rec.render_only_links:
            link = render.links[item["render_link"]]
            render_only["identifiers"].append(
                {
                    "scheme": item["scheme"],
                    "normalized": item["normalized"],
                    "href": link.href,
                    "locator": link.locator.to_json(),
                    "note": item["note"],
                    "list_item": item["list_item"],
                    "hidden": item["hidden"],
                    "region_reconciled": item["region_reconciled"],
                }
            )
            doc.ledger(
                f"render-link:{link.locator.path}",
                "render_identifier",
                "RENDER_ONLY_IDENTIFIER",
                f"{item['scheme']} {item['normalized']}",
            )
        render_only["limit_warnings"] = render.limit_warnings
    for o in observations:
        if o.state in ("not_inspected", "unavailable") and has_render:
            doc.ledger(o.container_id, "marker", "MARKER_REGION_NOT_INSPECTED", o.reason)
    accounting = _accounting(model, scan, rec, render, observations, identifiers, excluded)
    return {
        "containers": containers,
        "uses": uses,
        "units": units,
        "identifiers": identifiers,
        "excluded_identifiers": excluded,
        "markers": markers,
        "render_only": render_only,
        "accounting": accounting,
    }


def _accounting(
    model: SourceModel,
    scan: SourceScan,
    rec: Any,
    render: Any,
    observations: list[Any],
    identifiers: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
) -> dict[str, Any]:
    acc: dict[str, Any] = {
        "source_bytes": len(scan.text.encode("utf-8")),
        "parse_nodes": scan.nodes,
        "containers": dict(Counter(c.kind for c in model.containers)),
        "uses": dict(Counter(u.binding for u in model.uses)),
        "units": dict(Counter(u.kind for u in model.units)),
        "identifiers_by_role": dict(Counter(i["role"] for i in identifiers)),
        "identifiers_by_scheme": dict(Counter(i["scheme"] for i in identifiers)),
        "excluded_identifiers": dict(Counter(e["reason"] for e in excluded)),
        "markers": dict(Counter(o.state for o in observations)),
    }
    checks = [
        (
            "candidates = identifiers + excluded",
            len(scan.candidates) + len(scan.excluded_candidates),
            len(identifiers) + len(excluded),
        ),
        ("identifiers by role sum", len(identifiers), sum(acc["identifiers_by_role"].values())),
        ("one marker observation per container", len(model.containers), len(observations)),
        ("every unit in exactly one container", len(model.units), sum(len(c.unit_ids) for c in model.containers)),
    ]
    if rec is not None:
        acc["uses_render"] = dict(Counter(rec.use_state.get(u.id, "abstained") for u in model.uses))
        acc["render_uses"] = {
            "total": len(render.uses),
            "matched": len(rec.render_use_matched),
            "unmatched": len(rec.unmatched_render_uses),
        }
        acc["identifiers_render"] = dict(Counter(i["render"]["state"] for i in identifiers))
        acc["render_only_identifiers"] = len(rec.render_only_links)
        checks += [
            ("source uses = matched + abstained", len(model.uses), sum(acc["uses_render"].values())),
            (
                "render uses = matched + unmatched",
                len(render.uses),
                acc["render_uses"]["matched"] + acc["render_uses"]["unmatched"],
            ),
            ("matched pairs are one-to-one", len(rec.use_match), len(set(rec.use_match.values()))),
        ]
    acc["checks"] = [{"name": n, "left": a, "right": b, "ok": a == b} for n, a, b in checks]
    return acc


def _finalize(
    out: dict[str, Any], doc: _Doc, status: str, components: dict[str, Any], accounting: dict[str, Any]
) -> dict[str, Any]:
    if accounting.get("checks") and not all(c["ok"] for c in accounting["checks"]):
        doc.issues.append(Issue("BUNDLE_SEMANTIC_INVALID", (), "an accounting check failed"))
        status = "failed"
    out["status"] = status
    out["components"] = components
    out.setdefault("accounting", accounting)
    for key in ("containers", "uses", "units", "identifiers", "excluded_identifiers", "markers"):
        out.setdefault(key, [])
    out.setdefault("render_only", {"uses": [], "identifiers": [], "limit_warnings": []})
    out["exceptions"] = sorted(doc.exceptions, key=lambda e: (e["entity_type"], e["entity"], e["code"], e["detail"]))
    out["issues"] = [i.to_json() for i in sort_issues(_dedupe(doc.issues))]
    out["extraction_digest"] = digest({k: v for k, v in out.items() if k != "extraction_digest"})
    return out


def _dedupe(issues: list[Issue]) -> list[Issue]:
    seen = set()
    out = []
    for i in issues:
        key = (i.code, i.entities, i.detail, i.evidence)
        if key not in seen:
            seen.add(key)
            out.append(i)
    return out


def failure_document(bundle_sha: str | None, config: ExtractConfig, code: str, detail: str) -> dict[str, Any]:
    profile = load_profile()
    out: dict[str, Any] = {
        "schema": EXTRACTION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "extractor": extractor_identity(profile),
        "config": config.to_json(),
        "config_digest": digest(config.to_json()),
        "capture": {"capture_sha256": bundle_sha},
    }
    doc = _Doc(issues=[Issue(code, (), detail)])
    return _finalize(out, doc, "failed", {"worker": {"state": "failed", "code": code}}, {})


# Isolation --------------------------------------------------------------------------------------------------


def _limits(memory_mib: int, cpu_s: int) -> Any:
    def apply() -> None:
        import resource  # noqa: PLC0415 - POSIX only; other platforms get PLATFORM_UNSUPPORTED

        limit = memory_mib * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        os.setsid()

    return apply


def extract_bundle(
    capture: Bundle | Path | str, config: ExtractConfig | None = None, *, isolated: bool = True
) -> dict[str, Any]:
    """Extract one bundle. With ``isolated`` (the default) the work runs in a child process limited to
    ``worker_memory_mib`` of address space and ``worker_wall_s`` of wall time; the child is killed at the
    deadline and the result is a failure document with a stable code."""
    config = config or ExtractConfig()
    path = capture.path if isinstance(capture, Bundle) else Path(capture)
    try:
        bundle = capture if isinstance(capture, Bundle) else open_bundle(path)
    except BundleError as exc:
        return failure_document(None, config, exc.issue.code, exc.issue.detail)
    from citerift.wiki.verify import verify_capture  # noqa: PLC0415 - verify imports this module

    checked, _ = verify_capture(bundle)
    if not checked.ok:
        first = next(i for i in sort_issues(checked.issues) if i.severity == "error")
        return failure_document(bundle.capture_sha256, config, first.code, f"capture not verified: {first.detail}")
    if not isolated:
        try:
            return extract_document(bundle, config)
        except BundleError as exc:
            return failure_document(bundle.capture_sha256, config, exc.issue.code, exc.issue.detail)
    if not hasattr(os, "setsid"):
        return failure_document(bundle.capture_sha256, config, "PLATFORM_UNSUPPORTED", "POSIX process limits")
    src_root = str(Path(__file__).resolve().parents[2])
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from citerift.wiki.worker import main; sys.exit(main(sys.argv[2:]))"
    )
    cmd = [sys.executable, "-I", "-c", code, src_root, str(path), json.dumps(config.to_json())]
    proc = subprocess.Popen(  # noqa: S603 - fixed interpreter and arguments, no shell
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": os.environ.get("PATH", "")},
        preexec_fn=_limits(config.worker_memory_mib, int(config.worker_wall_s) + 1),  # noqa: PLW1509
    )
    try:
        stdout, stderr = proc.communicate(timeout=config.worker_wall_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return failure_document(
            bundle.capture_sha256, config, "EXTRACTION_DEADLINE_EXCEEDED", f"killed after {config.worker_wall_s} s"
        )
    if proc.returncode == 0 and len(stdout) <= MAX_OUTPUT_BYTES:
        try:
            result: dict[str, Any] = loads_strict(stdout)
        except StrictJSONError:
            pass
        else:
            if result.get("capture", {}).get("capture_sha256") != bundle.capture_sha256:
                return failure_document(
                    bundle.capture_sha256,
                    config,
                    "BUNDLE_DIGEST_MISMATCH",
                    "capture.json changed after it was verified",
                )
            return result
    tail = stderr[-2000:].decode("utf-8", "replace")
    if proc.returncode == 3 or "MemoryError" in tail:
        return failure_document(
            bundle.capture_sha256,
            config,
            "EXTRACTION_MEMORY_EXCEEDED",
            f"address space limit {config.worker_memory_mib} MiB",
        )
    if proc.returncode == -signal.SIGXCPU:
        return failure_document(bundle.capture_sha256, config, "EXTRACTION_DEADLINE_EXCEEDED", "CPU limit")
    last = tail.strip().splitlines()[-1] if tail.strip() else ""
    return failure_document(
        bundle.capture_sha256, config, "EXTRACTION_WORKER_FAILED", f"exit {proc.returncode}: {last[:300]}"
    )


def write_canonical(doc: dict[str, Any]) -> bytes:
    return canonical_bytes(doc)
