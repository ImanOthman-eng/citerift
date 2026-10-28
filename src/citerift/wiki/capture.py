"""Capture one pinned revision of an arwiki or enwiki article, with a separately identified render (SPEC 8).

Two operations, one request in flight, under one ``FetchPolicy`` and one global deadline:

1. source: the Action API ``query`` for one title, page id or revision id, returning the revision's ids, SHA-1, size,
   content model and main-slot wikitext in one answer;
2. render: the Core REST ``/v1/revision/{id}/html`` endpoint (Parsoid HTML) of exactly that revision id.

The source is accepted only when the answer names the requested page or revision, the namespace is 0, the content
model is wikitext and the SHA-1 and byte size match the text. The render is accepted only when it states the same
revision (header and document), page id, namespace and SHA-1, and a supported HTML profile; otherwise the capture
keeps the source and records why the render was rejected. Nothing is followed implicitly: a redirect page is an
error unless ``follow_redirect`` was requested, and then exactly one hop is followed.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from citerift.wiki import __version__
from citerift.wiki.bundle import BundleError, publish_bundle
from citerift.wiki.canonical import sha256_hex
from citerift.wiki.fetch import HOSTS, Answer, Clock, Fetcher, FetchPolicy, SystemClock, Transport, utc_text
from citerift.wiki.issues import Issue, sort_issues
from citerift.wiki.profile import SUPPORTED_WIKIS, load_profile

CAPTURE_SCHEMA = "urn:citerift:schema:wiki:v1:capture"
SCHEMA_VERSION = "1.0.0"
MIB = 1024 * 1024
MAX_SOURCE_BYTES = 4 * MIB
MAX_RENDER_BYTES = 16 * MIB
SUPPORTED_HTML = ("2.",)  # Parsoid HTML major version 2 (minor versions are compatible by the spec's versioning)
_PROFILE = re.compile(r'profile="https://www\.mediawiki\.org/wiki/Specs/HTML/([0-9]+\.[0-9]+\.[0-9]+)"')
_HEAD_END = re.compile(rb"</head\s*>", re.IGNORECASE)
_META = re.compile(r'<meta\s+(?:property|http-equiv)="([^"]+)"\s+content="([^"]*)"')
_ABOUT = re.compile(r'<html[^>]*\sabout="[^"]*/revision/([0-9]+)"')
_MAX_TITLE = 255  # bytes, MediaWiki's title limit


@dataclass(frozen=True)
class CaptureRequest:
    wiki: str
    title: str | None = None
    page_id: int | None = None
    revision_id: int | None = None
    follow_redirect: bool = False
    render: bool = True

    def problems(self) -> list[Issue]:
        out = []
        if self.wiki not in SUPPORTED_WIKIS:
            out.append(Issue("WIKI_UNSUPPORTED", (), repr(self.wiki)[:40]))
        given = [x for x in (self.title, self.page_id, self.revision_id) if x is not None]
        if len(given) != 1:
            out.append(Issue("REQUEST_INVALID", (), "give exactly one of title, page id, revision id"))
        if self.title is not None and (
            not self.title.strip()
            or len(self.title.encode("utf-8", "surrogatepass")) > _MAX_TITLE
            or any(ch in self.title for ch in "\x00\n\r\t|{}[]<>#")
        ):
            out.append(
                Issue("REQUEST_INVALID", (), "the title is empty, too long or has characters titles cannot have")
            )
        for name, value in (("page id", self.page_id), ("revision id", self.revision_id)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                out.append(Issue("REQUEST_INVALID", (), f"the {name} must be a positive integer"))
        if self.follow_redirect and self.revision_id is not None:
            out.append(Issue("REQUEST_INVALID", (), "a pinned revision is captured as it is; no redirect is followed"))
        return out

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaptureOutcome:
    status: str  # complete | partial | failed | deferred
    record: dict[str, Any]
    bundle: Path | None = None
    issues: list[Issue] = field(default_factory=list)
    artifacts: dict[str, bytes] = field(default_factory=dict)


def source_url(req: CaptureRequest, maxlag: int) -> str:
    params: dict[str, str] = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "revisions|info",
        "rvprop": "ids|timestamp|flags|size|sha1|contentmodel|content",
        "rvslots": "main",
        "maxlag": str(maxlag),
    }
    if req.title is not None:
        params["titles"] = req.title
    elif req.page_id is not None:
        params["pageids"] = str(req.page_id)
    else:
        params["revids"] = str(req.revision_id)
    if req.follow_redirect:
        params["redirects"] = "1"
    return f"https://{HOSTS[req.wiki]}/w/api.php?" + urllib.parse.urlencode(params)


def render_url(wiki: str, revision_id: int) -> str:
    return f"https://{HOSTS[wiki]}/w/rest.php/v1/revision/{int(revision_id)}/html"


def base36_to_sha1_hex(value: str) -> str | None:
    try:
        number = int(value, 36)
    except ValueError:
        return None
    text = format(number, "040x")
    return text if len(text) == 40 else None


def is_redirect(text: str, words: tuple[str, ...]) -> bool:
    head = text.lstrip()[:200]
    return any(re.match(rf"(?i){re.escape(w)}\s*:?\s*\[\[", head) for w in words)


def _attempts(answer: Answer, operation: str) -> list[dict[str, Any]]:
    return [{"operation": operation, **a.to_json()} for a in answer.attempts]


def _check_source(req: CaptureRequest, data: Any, issues: list[Issue]) -> dict[str, Any] | None:
    """Page and revision identity from the Action API answer, or None with issues."""
    q = data.get("query") if isinstance(data, dict) else None
    if not isinstance(q, dict):
        issues.append(Issue("API_ERROR", (), "no query object in the answer"))
        return None
    if q.get("badrevids"):
        issues.append(Issue("REVISION_NOT_FOUND", (), str(req.revision_id)))
        return None
    pages = q.get("pages")
    if not isinstance(pages, list) or len(pages) != 1 or not isinstance(pages[0], dict):
        issues.append(Issue("API_ERROR", (), "the answer does not hold exactly one page"))
        return None
    page = pages[0]
    if page.get("invalid"):
        issues.append(Issue("TITLE_INVALID", (), str(page.get("invalidreason", ""))[:200]))
        return None
    if page.get("missing"):
        issues.append(Issue("PAGE_MISSING", (), str(page.get("title", req.page_id))[:200]))
        return None
    redirects = q.get("redirects") or []
    if redirects:
        if not req.follow_redirect or len(redirects) > 1:
            issues.append(Issue("REDIRECT_LIMIT", (), f"{len(redirects)} redirect hops"))
            return None
        issues.append(Issue("REDIRECT_FOLLOWED", (), f"{redirects[0].get('from')} -> {redirects[0].get('to')}"))
    if page.get("ns") != 0:
        issues.append(Issue("NAMESPACE_UNSUPPORTED", (), f"namespace {page.get('ns')}"))
        return None
    if req.page_id is not None and page.get("pageid") != req.page_id:
        issues.append(Issue("PAGE_ID_MISMATCH", (), f"asked {req.page_id}, got {page.get('pageid')}"))
        return None
    revs = page.get("revisions")
    if not isinstance(revs, list) or len(revs) != 1 or not isinstance(revs[0], dict):
        issues.append(Issue("API_ERROR", (), "the page holds no single revision"))
        return None
    rev = revs[0]
    if req.revision_id is not None and rev.get("revid") != req.revision_id:
        issues.append(Issue("REVISION_ID_MISMATCH", (), f"asked {req.revision_id}, got {rev.get('revid')}"))
        return None
    if rev.get("texthidden") or rev.get("sha1hidden"):
        issues.append(Issue("REVISION_TEXT_HIDDEN", (), str(rev.get("revid"))))
        return None
    slot = (rev.get("slots") or {}).get("main")
    if not isinstance(slot, dict):
        issues.append(Issue("SLOT_MISSING", (), "no main slot"))
        return None
    if slot.get("texthidden"):
        issues.append(Issue("REVISION_TEXT_HIDDEN", (), str(rev.get("revid"))))
        return None
    if slot.get("contentmodel") != "wikitext":
        issues.append(Issue("CONTENT_MODEL_UNSUPPORTED", (), str(slot.get("contentmodel"))))
        return None
    content = slot.get("content")
    if not isinstance(content, str):
        issues.append(Issue("SLOT_MISSING", (), "the main slot has no content"))
        return None
    return {"page": page, "rev": rev, "content": content, "redirects": redirects}


def _check_render(body: bytes, headers: dict[str, str], page: dict[str, Any]) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    checks: dict[str, Any] = {}
    if len(body) > MAX_RENDER_BYTES:
        return checks, [Issue("RENDER_TOO_LARGE", (), f"{len(body)} bytes")]
    try:
        body.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return checks, [Issue("RENDER_NOT_UTF8")]
    m = _PROFILE.search(headers.get("content-type", ""))
    checks["html_version"] = m.group(1) if m else None
    end = _HEAD_END.search(body)
    head = body[: end.end() if end else min(len(body), 262144)].decode("utf-8")
    meta = dict(_META.findall(head))
    about = _ABOUT.search(head)
    checks["header_revision_id"] = headers.get("content-revision-id")
    checks["document_revision_id"] = about.group(1) if about else None
    checks["page_id"] = meta.get("mw:pageId")
    checks["namespace"] = meta.get("mw:pageNamespace")
    checks["revision_sha1_base36"] = meta.get("mw:revisionSHA1")
    checks["render_id"] = meta.get("x-mediawiki-render-id")
    version = checks["html_version"] or meta.get("mw:htmlVersion")
    checks["html_version"] = version
    if not version or not version.startswith(SUPPORTED_HTML):
        issues.append(Issue("RENDER_PROFILE_UNSUPPORTED", (), str(version)))
    revid = str(page["revision_id"])
    stated = [x for x in (checks["header_revision_id"], checks["document_revision_id"]) if x is not None]
    if not stated:
        issues.append(Issue("RENDER_REVISION_UNCHECKED", (), "neither header nor document states a revision"))
    elif any(x != revid for x in stated):
        issues.append(Issue("RENDER_REVISION_MISMATCH", (), f"render states {stated}, capture is {revid}"))
    if checks["page_id"] is not None and checks["page_id"] != str(page["page_id"]):
        issues.append(Issue("RENDER_REVISION_MISMATCH", (), f"page id {checks['page_id']}"))
    if checks["namespace"] is not None and checks["namespace"] != "0":
        issues.append(Issue("RENDER_REVISION_MISMATCH", (), f"namespace {checks['namespace']}"))
    sha = checks["revision_sha1_base36"]
    if sha is not None:
        checks["revision_sha1"] = base36_to_sha1_hex(sha)
        if checks["revision_sha1"] != page["sha1"]:
            issues.append(Issue("RENDER_REVISION_MISMATCH", (), "the render's revision SHA-1 differs"))
    return checks, issues


def capture_revision(
    request: CaptureRequest,
    fetch_policy: FetchPolicy | None = None,
    *,
    out: Path | None = None,
    transport: Transport | None = None,
    clock: Clock | None = None,
) -> CaptureOutcome:
    """Capture ``request``; publish a bundle at ``out`` when a source was captured and ``out`` is given."""
    policy = fetch_policy or FetchPolicy()
    clock = clock or SystemClock()
    issues: list[Issue] = list(request.problems())
    record: dict[str, Any] = {
        "schema": CAPTURE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "request": request.to_json(),
        "client": {"name": "citerift-wiki", "version": __version__, "policy": policy.to_json()},
        "started_at": utc_text(clock.now()),
        "page": None,
        "source": None,
        "render": {"state": "not_requested"},
        "attempts": [],
        "failure_artifacts": [],
        "not_before": None,
    }
    artifacts: dict[str, bytes] = {}
    if issues:
        return _finish(record, "failed", issues, artifacts, None, clock)
    fetcher = Fetcher(policy, transport, clock)
    profile = load_profile()

    def keep_failures(answer: Answer) -> None:
        for sha, body in answer.failure_bodies.items():
            artifacts[sha] = body
            record["failure_artifacts"].append(sha)

    src_url = source_url(request, policy.maxlag_s)
    answer = fetcher.get(src_url, expect="json")
    record["attempts"] += _attempts(answer, "source")
    keep_failures(answer)
    if answer.code is not None or answer.body is None:
        issues.append(Issue(answer.code or "API_ERROR", (), "source query"))
        status = "deferred" if answer.code == "DEFERRED_RETRY_AFTER" else "failed"
        record["not_before"] = answer.not_before
        return _finish(record, status, issues, artifacts, None, clock)
    checked = _check_source(request, answer.json, issues)
    if checked is None:
        return _finish(record, "failed", issues, artifacts, None, clock)
    content: str = checked["content"]
    page, rev = checked["page"], checked["rev"]
    try:
        text_bytes = content.encode("utf-8", "strict")
    except UnicodeEncodeError:
        issues.append(Issue("SOURCE_NOT_ENCODABLE"))
        return _finish(record, "failed", issues, artifacts, None, clock)
    if len(text_bytes) > MAX_SOURCE_BYTES:
        issues.append(Issue("SOURCE_TOO_LARGE", (), f"{len(text_bytes)} bytes"))
        return _finish(record, "failed", issues, artifacts, None, clock)
    sha1 = hashlib.sha1(text_bytes, usedforsecurity=False).hexdigest()
    if sha1 != rev.get("sha1") or len(text_bytes) != rev.get("size"):
        issues.append(Issue("SOURCE_HASH_MISMATCH", (), f"sha1 {sha1} vs {rev.get('sha1')}, size {len(text_bytes)}"))
        return _finish(record, "failed", issues, artifacts, None, clock)
    words = profile.wikis[request.wiki].redirect_words
    redirect = is_redirect(content, words)
    if redirect:
        code = "REDIRECT_LIMIT" if checked["redirects"] else "REDIRECT_NOT_FOLLOWED"
        issues.append(Issue(code, (), str(page.get("title"))[:200]))
        return _finish(record, "failed", issues, artifacts, None, clock)
    record["page"] = {
        "wiki": request.wiki,
        "host": HOSTS[request.wiki],
        "page_id": page.get("pageid"),
        "namespace": 0,
        "title": page.get("title"),
        "revision_id": rev.get("revid"),
        "parent_revision_id": rev.get("parentid"),
        "revision_timestamp": rev.get("timestamp"),
        "content_model": "wikitext",
        "sha1": sha1,
        "size": len(text_bytes),
        "is_latest": page.get("lastrevid") == rev.get("revid"),
        "redirect_followed": checked["redirects"][0] if checked["redirects"] else None,
    }
    src_sha = sha256_hex(text_bytes)
    response_sha = sha256_hex(answer.body)
    artifacts[src_sha] = text_bytes
    artifacts[response_sha] = answer.body
    record["source"] = {
        "url": src_url,
        "artifact": src_sha,
        "bytes": len(text_bytes),
        "response_artifact": response_sha,
    }
    status = "complete"
    if request.render:
        status = _capture_render(fetcher, request, record, issues, artifacts, keep_failures)
    return _finish(record, status, issues, artifacts, out, clock)


def _capture_render(
    fetcher: Fetcher,
    request: CaptureRequest,
    record: dict[str, Any],
    issues: list[Issue],
    artifacts: dict[str, bytes],
    keep_failures: Any,
) -> str:
    page = record["page"]
    url = render_url(request.wiki, page["revision_id"])
    answer = fetcher.get(url, expect="html")
    record["attempts"] += _attempts(answer, "render")
    keep_failures(answer)
    if answer.code is not None or answer.body is None:
        issues.append(Issue(answer.code or "HTTP_STATUS_UNEXPECTED", (), "render"))
        record["render"] = {"state": "failed", "url": url, "code": answer.code, "not_before": answer.not_before}
        return "partial"
    headers = {
        k: v
        for k, v in answer.headers.items()
        if k in ("content-type", "content-revision-id", "etag", "date", "last-modified", "content-language")
    }
    checks, render_issues = _check_render(answer.body, answer.headers, page)
    issues.extend(render_issues)
    sha = sha256_hex(answer.body)
    artifacts[sha] = answer.body
    accepted = not any(i.severity == "error" for i in render_issues)
    record["render"] = {
        "state": "captured" if accepted else "rejected",
        "url": url,
        "artifact": sha,
        "bytes": len(answer.body),
        "headers": headers,
        "checks": checks,
    }
    return "complete" if accepted else "partial"


def _finish(
    record: dict[str, Any],
    status: str,
    issues: list[Issue],
    artifacts: dict[str, bytes],
    out: Path | None,
    clock: Clock,
) -> CaptureOutcome:
    record["finished_at"] = utc_text(clock.now())
    record["status"] = status
    record["issues"] = [i.to_json() for i in sort_issues(issues)]
    bundle = None
    if out is not None and record["source"] is not None:
        try:
            bundle = publish_bundle(out, record, artifacts)
        except BundleError as exc:
            issues.append(exc.issue)
            record["issues"] = [i.to_json() for i in sort_issues(issues)]
            return CaptureOutcome("failed", record, None, issues, artifacts)
    return CaptureOutcome(status, record, bundle, issues, artifacts)
