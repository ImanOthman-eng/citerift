"""Offline verification and replay of capture bundles and extraction documents (SPECIFICATION.md 14).

``verify_bundle`` re-checks everything a capture bundle and, when given, an extraction document claim, from the
retained bytes only: schemas, artifact hashes, the source SHA-1 and size, the source answer against the recorded
page identity, the render's revision checks, every exact source anchor against the source bytes, every render
locator against the retained HTML, references between entities, accounting and the digests. ``replay_bundle``
re-extracts the bundle in the isolated worker (which refuses every network connection) and compares the result
with a recorded extraction. Neither function makes a network request.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from citerift.wiki import schemas
from citerift.wiki.bundle import ARTIFACTS, CAPTURE_FILE, Bundle, BundleError, open_bundle
from citerift.wiki.canonical import StrictJSONError, digest, loads_strict, sha256_hex
from citerift.wiki.capture import (
    MAX_RENDER_BYTES,
    MAX_SOURCE_BYTES,
    CaptureRequest,
    _check_render,
    _check_source,
    render_url,
    source_url,
)
from citerift.wiki.extract import ExtractConfig, extract_bundle, extractor_identity
from citerift.wiki.fetch import HOSTS
from citerift.wiki.issues import CATALOG, Issue, sort_issues
from citerift.wiki.profile import load_profile
from citerift.wiki.render import RenderLimitExceeded, RenderReader
from citerift.wiki.textmap import ByteMap

VERIFICATION_SCHEMA = "urn:citerift:schema:wiki:v1:verification"
SCHEMA_VERSION = "1.0.0"
MAX_EXTRACTION_BYTES = 256 * 1024 * 1024


class _Report:
    def __init__(self) -> None:
        self.checks: dict[str, dict[str, Any]] = {}
        self.issues: list[Issue] = []

    def check(self, name: str, ok: bool, code: str = "BUNDLE_SEMANTIC_INVALID", detail: str = "") -> bool:
        entry = self.checks.setdefault(name, {"name": name, "checked": 0, "failed": 0, "first_failure": None})
        entry["checked"] += 1
        if not ok:
            entry["failed"] += 1
            if entry["first_failure"] is None:
                entry["first_failure"] = detail[:300]
            if entry["failed"] <= 20:
                self.issues.append(Issue(code, (), f"{name}: {detail}"[:400]))
        return ok

    def fail(self, issue: Issue) -> None:
        self.issues.append(issue)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def to_json(self) -> dict[str, Any]:
        return {
            "checks": [self.checks[k] for k in sorted(self.checks)],
            "issues": [i.to_json() for i in sort_issues(self.issues)],
        }


def _schema_problems(instance: Any, schema_id: str, report: _Report) -> bool:
    try:
        problems = schemas.validate(instance, schema_id)
    except schemas.SchemaRootUnavailable as exc:
        report.fail(Issue("SCHEMA_ROOT_UNAVAILABLE", (), str(exc)[:300]))
        return False
    name = f"schema {schema_id.rsplit(':', 1)[-1]}"
    for p in problems:
        report.check(name, False, "BUNDLE_SCHEMA_INVALID", p)
    if not problems:
        report.check(name, True)
    return not problems


# Capture bundles --------------------------------------------------------------------------------------------


def _listed_artifacts(cap: dict[str, Any]) -> set[str]:
    names = set(cap.get("failure_artifacts") or [])
    for part in (cap.get("source") or {}, cap.get("render") or {}):
        for key in ("artifact", "response_artifact"):
            if isinstance(part.get(key), str):
                names.add(part[key])
    return names


def _directory_entries(bundle: Bundle, report: _Report) -> None:
    """Only capture.json and artifacts/ at the top; only listed, regular files in artifacts/."""
    for entry in sorted(os.listdir(bundle.path)):
        if entry not in (CAPTURE_FILE, ARTIFACTS):
            report.fail(Issue("BUNDLE_UNLISTED_FILE", (), entry[:120]))
    adir = bundle.path / ARTIFACTS
    st = os.lstat(adir) if os.path.lexists(adir) else None
    if st is None or not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        report.fail(Issue("BUNDLE_MALFORMED", (), "artifacts is not a directory"))
        return
    listed = _listed_artifacts(bundle.capture)
    for entry in sorted(os.listdir(adir)):
        if entry not in listed:
            report.fail(Issue("BUNDLE_UNLISTED_FILE", (), f"artifacts/{entry[:100]}"))


def verify_capture(bundle: Bundle) -> tuple[_Report, dict[str, bytes]]:
    """Checks of one capture bundle; returns the report and the verified artifacts by SHA-256."""
    report = _Report()
    cap = bundle.capture
    if not _schema_problems(cap, "urn:citerift:schema:wiki:v1:capture", report):
        return report, {}
    _directory_entries(bundle, report)
    artifacts: dict[str, bytes] = {}
    for sha in sorted(_listed_artifacts(cap)):
        try:
            artifacts[sha] = bundle.artifact(sha, limit=max(MAX_RENDER_BYTES, 32 * 1024 * 1024))
            report.check("artifact hashes", True)
        except BundleError as exc:
            report.check("artifact hashes", False, exc.issue.code, exc.issue.detail)
    for issue in cap["issues"]:
        report.check("issue codes in catalog", issue["code"] in CATALOG, detail=issue["code"])
    req_json = cap["request"]
    request = CaptureRequest(**req_json)
    report.check("request is valid", not request.problems(), "BUNDLE_SEMANTIC_INVALID", str(req_json)[:200])
    page, source, render = cap["page"], cap["source"], cap["render"]
    host = HOSTS.get(req_json["wiki"])
    for a in cap["attempts"]:
        report.check("attempt hosts", a["url"].startswith(f"https://{host}/"), "HOST_NOT_ALLOWED", a["url"][:200])
    for sha in cap["failure_artifacts"]:
        report.check(
            "failure artifacts belong to failed attempts",
            any(a["body_sha256"] == sha and a["code"] is not None for a in cap["attempts"]),
            detail=sha,
        )
    if page is None or source is None:
        report.check("a published bundle holds a source", False, detail=f"status {cap['status']}")
        return report, artifacts
    report.check("page wiki is the requested wiki", page["wiki"] == req_json["wiki"] and page["host"] == host)
    report.check(
        "source URL",
        source["url"] == source_url(request, cap["client"]["policy"]["maxlag_s"]),
        detail=source["url"][:200],
    )
    accepted = [a for a in cap["attempts"] if a["operation"] == "source" and a["code"] is None]
    report.check(
        "source answer is the accepted attempt",
        len(accepted) == 1 and accepted[0]["body_sha256"] == source["response_artifact"],
    )
    text_bytes = artifacts.get(source["artifact"])
    if text_bytes is not None:
        report.check(
            "source size",
            len(text_bytes) == source["bytes"] == page["size"] <= MAX_SOURCE_BYTES,
            detail=f"{len(text_bytes)} bytes",
        )
        sha1 = hashlib.sha1(text_bytes, usedforsecurity=False).hexdigest()
        report.check("source SHA-1", sha1 == page["sha1"], "BUNDLE_ARTIFACT_CORRUPT", f"{sha1} vs {page['sha1']}")
        response = artifacts.get(source["response_artifact"])
        try:
            data = loads_strict(response) if response is not None else None
        except StrictJSONError as exc:
            data = None
            report.check("source answer is JSON", False, "BUNDLE_ARTIFACT_CORRUPT", str(exc))
        if data is not None:
            found: list[Issue] = []
            checked = _check_source(request, data, found)
            same = checked is not None and checked["content"].encode("utf-8") == text_bytes
            if checked is not None:
                p, r = checked["page"], checked["rev"]
                same = same and (
                    p.get("pageid"),
                    p.get("title"),
                    r.get("revid"),
                    r.get("parentid"),
                    r.get("timestamp"),
                    r.get("sha1"),
                    r.get("size"),
                ) == (
                    page["page_id"],
                    page["title"],
                    page["revision_id"],
                    page["parent_revision_id"],
                    page["revision_timestamp"],
                    page["sha1"],
                    page["size"],
                )
                same = same and (p.get("lastrevid") == r.get("revid")) == page["is_latest"]
            report.check(
                "source answer states the recorded revision",
                same,
                "BUNDLE_SEMANTIC_INVALID",
                ",".join(i.code for i in found),
            )
    if req_json["revision_id"] is not None:
        report.check("pinned revision", page["revision_id"] == req_json["revision_id"])
    if req_json["page_id"] is not None:
        report.check("requested page", page["page_id"] == req_json["page_id"])
    state = render["state"]
    if not req_json["render"]:
        report.check("render not requested", state == "not_requested")
    else:
        report.check("render requested", state != "not_requested")
    expected_status = {"not_requested": "complete", "captured": "complete"}.get(state, "partial")
    report.check("capture status", cap["status"] == expected_status, detail=f"{cap['status']} with render {state}")
    if state in ("captured", "rejected", "failed"):
        report.check("render URL", render["url"] == render_url(page["wiki"], page["revision_id"]))
    if state in ("captured", "rejected"):
        html = artifacts.get(render["artifact"])
        if html is not None:
            report.check("render size", len(html) == render["bytes"])
            checks, issues = _check_render(html, render["headers"], page)
            report.check("render checks reproduce", checks == render["checks"], detail=str(checks)[:200])
            accepted_render = not any(i.severity == "error" for i in issues)
            report.check(
                "render state follows its checks",
                accepted_render == (state == "captured"),
                "RENDER_REVISION_MISMATCH",
                ",".join(i.code for i in issues),
            )
            ok_attempts = [a for a in cap["attempts"] if a["operation"] == "render" and a["code"] is None]
            report.check(
                "render body is the accepted attempt",
                len(ok_attempts) == 1 and ok_attempts[0]["body_sha256"] == render["artifact"],
            )
    return report, artifacts


# Extraction documents ---------------------------------------------------------------------------------------


def _locators(doc: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for u in doc["uses"]:
        if "locator" in u["render"]:
            yield f"use {u['id']}", u["render"]["locator"]
    for i in doc["identifiers"]:
        for w in i["render"]["witnesses"]:
            yield f"identifier {i['id']} witness", w
    for m in doc["markers"]:
        if m["region"] is not None:
            yield f"marker {m['container_id']}", m["region"]["locator"]
    for ru in doc["render_only"]["uses"]:
        yield "render-only use", ru["locator"]
    for ri in doc["render_only"]["identifiers"]:
        yield "render-only identifier", ri["locator"]


def _spans(doc: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for c in doc["containers"]:
        yield f"container {c['id']}", c["source"]
        for d in c["definitions"]:
            yield f"definition {d['id']}", d["source"]
            yield f"definition {d['id']} body", d["body"]
    for u in doc["uses"]:
        yield f"use {u['id']}", u["source"]
    for un in doc["units"]:
        yield f"unit {un['id']}", un["source"]


def _references(doc: dict[str, Any], report: _Report) -> None:
    containers = {c["id"]: c for c in doc["containers"]}
    uses = {u["id"]: u for u in doc["uses"]}
    units = {u["id"]: u for u in doc["units"]}
    idents = {i["id"]: i for i in doc["identifiers"]}
    for name, items in (
        ("containers", doc["containers"]),
        ("uses", doc["uses"]),
        ("units", doc["units"]),
        ("identifiers", doc["identifiers"]),
    ):
        ids = [x["id"] for x in items]
        report.check(f"unique {name} ids", len(ids) == len(set(ids)), detail=name)
    for u in doc["uses"]:
        c = containers.get(u["container_id"]) if u["container_id"] is not None else None
        if u["container_id"] is not None:
            report.check(
                "use container exists and lists the use", c is not None and u["id"] in c["use_ids"], detail=u["id"]
            )
    for c in doc["containers"]:
        for uid in c["use_ids"]:
            report.check("container uses exist", uid in uses and uses[uid]["container_id"] == c["id"], detail=uid)
        for nid in c["unit_ids"]:
            report.check("container units exist", nid in units and units[nid]["container_id"] == c["id"], detail=nid)
    for un in doc["units"]:
        for iid in un["identifier_ids"]:
            report.check("unit identifiers exist", iid in idents and idents[iid]["unit_id"] == un["id"], detail=iid)
        if un["parent_unit"] is not None:
            report.check("parent unit exists", un["parent_unit"] in units, detail=un["id"])
    for i in doc["identifiers"]:
        if i["container_id"] is not None:
            report.check("identifier container exists", i["container_id"] in containers, detail=i["id"])
        if i["unit_id"] is not None:
            report.check(
                "identifier unit lists it",
                i["unit_id"] in units and i["id"] in units[i["unit_id"]]["identifier_ids"],
                detail=i["id"],
            )
    marked = Counter(m["container_id"] for m in doc["markers"])
    report.check(
        "one marker observation per container", set(marked) == set(containers) and all(n == 1 for n in marked.values())
    )
    for m in doc["markers"]:
        report.check("marker browser visibility not evaluated", m["browser_visibility"] == "not_evaluated")


def _accounting(doc: dict[str, Any], report: _Report) -> None:
    acc = doc["accounting"]
    for c in acc.get("checks", []):
        report.check("recorded accounting checks hold", c["ok"] and c["left"] == c["right"], detail=c["name"])
    if doc["status"] == "failed":
        return
    report.check(
        "identifiers by role", acc["identifiers_by_role"] == dict(Counter(i["role"] for i in doc["identifiers"]))
    )
    report.check(
        "identifiers by scheme", acc["identifiers_by_scheme"] == dict(Counter(i["scheme"] for i in doc["identifiers"]))
    )
    report.check("markers by state", acc["markers"] == dict(Counter(m["state"] for m in doc["markers"])))
    report.check("containers by kind", acc["containers"] == dict(Counter(c["kind"] for c in doc["containers"])))
    report.check("uses by binding", acc["uses"] == dict(Counter(u["binding"] for u in doc["uses"])))


def verify_extraction(bundle: Bundle, doc: Any, artifacts: dict[str, bytes], report: _Report) -> None:
    if not _schema_problems(doc, "urn:citerift:schema:wiki:v1:extraction", report):
        return
    report.check(
        "extraction digest",
        doc["extraction_digest"] == digest({k: v for k, v in doc.items() if k != "extraction_digest"}),
        "BUNDLE_DIGEST_MISMATCH",
    )
    report.check("config digest", doc["config_digest"] == digest(doc["config"]), "BUNDLE_DIGEST_MISMATCH")
    cap, page = bundle.capture, bundle.capture.get("page") or {}
    report.check(
        "extraction names this capture",
        doc["capture"]["capture_sha256"] == bundle.capture_sha256,
        "BUNDLE_DIGEST_MISMATCH",
    )
    if doc["status"] == "failed" and "source_artifact" not in doc["capture"]:
        return
    expected = {
        "wiki": page.get("wiki"),
        "page_id": page.get("page_id"),
        "title": page.get("title"),
        "revision_id": page.get("revision_id"),
        "sha1": page.get("sha1"),
        "source_artifact": (cap.get("source") or {}).get("artifact"),
        "render_artifact": (cap.get("render") or {}).get("artifact"),
        "render_state": (cap.get("render") or {}).get("state"),
    }
    stated = {k: doc["capture"].get(k) for k in expected}
    report.check("extraction capture fields", stated == expected, "BUNDLE_DIGEST_MISMATCH", str(stated)[:200])
    text_bytes = artifacts.get(expected["source_artifact"] or "")
    if text_bytes is None:
        report.check("source available for anchors", False, "BUNDLE_ARTIFACT_MISSING")
        return
    text = text_bytes.decode("utf-8")
    bmap = ByteMap(text)
    for where, span in _spans(doc):
        ok = 0 <= span["cp_start"] <= span["cp_end"] <= len(text) and bmap.interval(
            span["cp_start"], span["cp_end"]
        ) == (span["byte_start"], span["byte_end"])
        report.check("source spans", ok, "ANCHOR_MISMATCH", where)
    anchors = [(f"identifier {i['id']}", i["source"]) for i in doc["identifiers"]]
    anchors += [(f"excluded {e['scheme']}", e["source"]) for e in doc["excluded_identifiers"]]
    for where, a in anchors:
        ok = (
            0 <= a["byte_start"] <= a["byte_end"] <= len(text_bytes)
            and text_bytes[a["byte_start"] : a["byte_end"]] == a["raw"].encode("utf-8")
            and 0 <= a["cp_start"] <= a["cp_end"] <= len(text)
            and text[a["cp_start"] : a["cp_end"]] == a["raw"]
            and bmap.interval(a["cp_start"], a["cp_end"]) == (a["byte_start"], a["byte_end"])
            and sha256_hex(a["raw"].encode("utf-8")) == a["raw_sha256"]
        )
        report.check("exact source anchors", ok, "ANCHOR_MISMATCH", where)
    _references(doc, report)
    _accounting(doc, report)
    locators = list(_locators(doc))
    html = artifacts.get(expected["render_artifact"] or "")
    if not locators:
        return
    if html is None or expected["render_state"] != "captured":
        report.check("render available for locators", False, "BUNDLE_ARTIFACT_MISSING")
        return
    try:
        reader = RenderReader(html, doc["config"]["max_render_elements"])
    except (RenderLimitExceeded, ValueError, SyntaxError) as exc:
        report.check("render parses", False, "RENDER_PARSE_FAILED", type(exc).__name__)
        return
    for where, loc in locators:
        el = reader.element_by_path(loc["path"])
        ok = el is not None and reader.locator(el).to_json() == loc
        report.check("render locators", ok, "LOCATOR_MISMATCH", f"{where} {loc['path'][:120]}")


def _read_extraction(path: Path, report: _Report) -> Any:
    try:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            report.fail(Issue("BUNDLE_PATH_UNSAFE", (), f"{path.name} is not a regular file"))
            return None
        if st.st_size > MAX_EXTRACTION_BYTES:
            report.fail(Issue("BUNDLE_MALFORMED", (), "the extraction document is too large"))
            return None
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as f:
            return loads_strict(f.read(MAX_EXTRACTION_BYTES + 1))
    except OSError as exc:
        report.fail(Issue("BUNDLE_MALFORMED", (), f"{path.name}: {exc.strerror}"))
    except StrictJSONError as exc:
        report.fail(Issue("BUNDLE_MALFORMED", (), str(exc)))
    return None


def _result(operation: str, bundle: Bundle | None, report: _Report, extra: dict[str, Any]) -> dict[str, Any]:
    out = {
        "schema": VERIFICATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "operation": operation,
        "capture_sha256": bundle.capture_sha256 if bundle is not None else None,
        "verified": report.ok,
        **extra,
        **report.to_json(),
    }
    return out


def verify_bundle(bundle: Bundle | Path | str, extraction: Path | str | dict[str, Any] | None = None) -> dict[str, Any]:
    """Verify a capture bundle and, when given, an extraction document of it (a path or the parsed document)."""
    report = _Report()
    try:
        b = bundle if isinstance(bundle, Bundle) else open_bundle(Path(bundle))
    except BundleError as exc:
        report.fail(exc.issue)
        return _result("verify", None, report, {"extraction_digest": None})
    cap_report, artifacts = verify_capture(b)
    report.checks.update(cap_report.checks)
    report.issues += cap_report.issues
    doc = None
    if extraction is not None:
        doc = extraction if isinstance(extraction, dict) else _read_extraction(Path(extraction), report)
        if doc is not None and cap_report.ok:
            verify_extraction(b, doc, artifacts, report)
    digest_value = doc.get("extraction_digest") if isinstance(doc, dict) else None
    return _result("verify", b, report, {"extraction_digest": digest_value if isinstance(digest_value, str) else None})


def replay_bundle(
    bundle: Bundle | Path | str,
    pinned_config: ExtractConfig | None = None,
    recorded: Path | str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-extract ``bundle`` offline and compare with ``recorded`` (a path or document) when given.

    The configuration is ``pinned_config`` or, when absent, the recorded document's configuration. A replay is
    ``reproduced`` only when the new extraction digest equals the recorded one; an extractor, profile or parser
    identity that differs from the recorded one is reported before any comparison is made."""
    report = _Report()
    try:
        b = bundle if isinstance(bundle, Bundle) else open_bundle(Path(bundle))
    except BundleError as exc:
        report.fail(exc.issue)
        return _result("replay", None, report, {"replay": {"state": "failed"}, "extraction_digest": None})
    doc = None
    if recorded is not None:
        doc = recorded if isinstance(recorded, dict) else _read_extraction(Path(recorded), report)
        if doc is None:
            return _result("replay", b, report, {"replay": {"state": "failed"}, "extraction_digest": None})
        if not isinstance(doc, dict) or not _schema_problems(doc, "urn:citerift:schema:wiki:v1:extraction", report):
            return _result("replay", b, report, {"replay": {"state": "failed"}, "extraction_digest": None})
    config = pinned_config
    if doc is not None:
        recorded_config = ExtractConfig.from_json(doc["config"])
        if config is not None and config != recorded_config:
            report.fail(Issue("REPLAY_CONFIG_MISMATCH", (), "the pinned configuration is not the recorded one"))
            return _result("replay", b, report, {"replay": {"state": "not_compared"}, "extraction_digest": None})
        config = recorded_config
        identity = extractor_identity(load_profile())
        if doc["extractor"] != identity:
            changed = sorted(k for k in identity if doc["extractor"].get(k) != identity[k])
            report.fail(Issue("REPLAY_IDENTITY_MISMATCH", (), f"differs in {', '.join(changed)}"))
            return _result("replay", b, report, {"replay": {"state": "not_compared"}, "extraction_digest": None})
    config = config or ExtractConfig()
    new = extract_bundle(b, config)
    new_digest = new["extraction_digest"]
    state = "not_compared"
    replay: dict[str, Any] = {"new_status": new["status"], "new_digest": new_digest}
    if new["status"] == "failed":
        state = "failed"
        for i in new["issues"]:
            if i["severity"] == "error":
                report.fail(Issue(i["code"], (), i["detail"]))
    if doc is not None:
        replay["recorded_digest"] = doc["extraction_digest"]
        if state != "failed":
            same = new_digest == doc["extraction_digest"]
            state = "reproduced" if same else "differs"
            if not same:
                keys = sorted(k for k in set(new) | set(doc) if new.get(k) != doc.get(k) and k != "extraction_digest")
                replay["differing_keys"] = keys
                report.fail(Issue("REPLAY_DIFFERS", (), f"differs in {', '.join(keys)}"[:300]))
    replay["state"] = state
    return _result("replay", b, report, {"replay": replay, "extraction_digest": new_digest})
