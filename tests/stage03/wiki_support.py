"""Helpers for the Stage 03 tests: SYNTHETIC captures built through the production capture code.

Every synthetic bundle is produced by ``capture_revision`` with a scripted transport and clock, so it passes the
same identity checks as a live capture (SHA-1 and size of the source, revision, page and SHA-1 of the render). The
pages, revisions and texts are invented; they are never evidence about Wikipedia.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from citerift.wiki.capture import CaptureOutcome, CaptureRequest, capture_revision
from citerift.wiki.extract import ExtractConfig, extract_bundle
from citerift.wiki.fetch import FetchPolicy, RawResponse

REVISION = 900_000_001
PAGE = 900_000_002
HTML_TYPE = 'text/html; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/HTML/2.8.0"'
JSON_TYPE = "application/json; charset=utf-8"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ScriptedClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.base = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def now(self) -> datetime:
        return self.base + timedelta(seconds=self.t)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += max(0.0, seconds)


def _closed() -> None:
    return None


def response(status: int, headers: dict[str, str], body: bytes, chunks: int = 1) -> RawResponse:
    size = max(1, len(body) // chunks + 1)
    parts: Iterator[bytes] = iter([body[i : i + size] for i in range(0, len(body), size)] or [b""])
    return RawResponse(status, headers, parts, _closed)


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()


def base36(hex_digest: str) -> str:
    n, digits, out = int(hex_digest, 16), "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def api_answer(
    text: str,
    *,
    revision: int = REVISION,
    page: int = PAGE,
    title: str = "SYNTHETIC page",
    ns: int = 0,
    model: str = "wikitext",
    **rev_extra: Any,
) -> dict[str, Any]:
    rev = {
        "revid": revision,
        "parentid": 0,
        "timestamp": "2026-10-28T00:00:00Z",
        "size": len(text.encode("utf-8")),
        "sha1": sha1(text),
        "slots": {"main": {"contentmodel": model, "contentformat": "text/x-wiki", "content": text}},
    }
    rev.update(rev_extra)
    return {
        "batchcomplete": True,
        "query": {"pages": [{"pageid": page, "ns": ns, "title": title, "lastrevid": revision, "revisions": [rev]}]},
    }


def parsoid(body: str, text: str, *, revision: int = REVISION, page: int = PAGE, sha1_hex: str | None = None) -> bytes:
    """A minimal Parsoid HTML 2.8.0 document for ``body`` that identifies the given revision."""
    digest = base36(sha1_hex or sha1(text))
    head = (
        f'<!DOCTYPE html>\n<html prefix="dc: http://purl.org/dc/terms/ mw: http://mediawiki.org/rdf/" '
        f'about="https://example.invalid/wiki/Special:Redirect/revision/{revision}"><head>'
        f'<meta charset="utf-8"/><meta property="mw:pageId" content="{page}"/>'
        f'<meta property="mw:pageNamespace" content="0"/><meta property="mw:revisionSHA1" content="{digest}"/>'
        f'<meta property="mw:htmlVersion" content="2.8.0"/><title>SYNTHETIC</title></head>'
    )
    return (head + f'<body class="mw-content-ltr mw-parser-output">{body}</body></html>').encode()


def ref_sup(n: int, note: str, ref_id: str, name: str | None = None, group: str | None = None) -> str:
    attrs: dict[str, str] = {}
    if name is not None:
        attrs["name"] = name
    if group is not None:
        attrs["group"] = group
    dm = json.dumps({"name": "ref", "attrs": attrs, "body": {"id": f"mw-reference-text-{note}"}})
    label = f"{group} {n}" if group else str(n)
    return (
        f'<sup about="#mwt{n}" class="mw-ref reference" id="{ref_id}" rel="dc:references" '
        f'typeof="mw:Extension/ref" data-mw=\'{dm}\'><a href="./SYNTHETIC#{note}" style="counter-reset: '
        f'mw-Ref {n};"><span class="mw-reflink-text"><span class="cite-bracket">[</span>{label}'
        f'<span class="cite-bracket">]</span></span></a></sup>'
    )


def note_li(note: str, backlinks: list[str], inner: str) -> str:
    back = "".join(
        f'<a href="./SYNTHETIC#{b}" rel="mw:referencedBy"><span class="mw-linkback-text">↑ </span></a>'
        for b in backlinks
    )
    return (
        f'<li about="#{note}" id="{note}"><span class="mw-cite-backlink">{back}</span> '
        f'<span id="mw-reference-text-{note}" class="mw-reference-text reference-text">{inner}</span></li>'
    )


def references(items: list[str], group: str = "") -> str:
    dm = json.dumps({"name": "references", "attrs": {"group": group} if group else {}})
    return (
        f'<div class="mw-references-wrap" typeof="mw:Extension/references" about="#mwt900" '
        f"data-mw='{dm}'><ol class=\"mw-references references\">{''.join(items)}</ol></div>"
    )


def doi_link(doi: str, text: str | None = None) -> str:
    return f'<a rel="mw:ExtLink nofollow" href="https://doi.org/{doi}" class="external text">{text or doi}</a>'


Transport = Callable[[str, dict[str, str], float], RawResponse]


def scripted(answers: list[RawResponse | Exception]) -> tuple[Transport, list[str]]:
    seen: list[str] = []
    queue = list(answers)

    def transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
        seen.append(url)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return transport, seen


def capture(
    out: Path | None,
    text: str,
    html: bytes | None = None,
    *,
    wiki: str = "en",
    answer: dict[str, Any] | None = None,
    render_headers: dict[str, str] | None = None,
    request: CaptureRequest | None = None,
    policy: FetchPolicy | None = None,
) -> CaptureOutcome:
    """Capture a SYNTHETIC revision; ``html=None`` captures the source only."""
    answers: list[RawResponse | Exception] = [
        response(200, {"content-type": JSON_TYPE}, json.dumps(answer or api_answer(text), ensure_ascii=False).encode())
    ]
    if html is not None:
        headers = {"content-type": HTML_TYPE, "content-revision-id": str(REVISION)}
        headers.update(render_headers or {})
        answers.append(response(200, headers, html))
    transport, _ = scripted(answers)
    req = request or CaptureRequest(wiki, revision_id=REVISION, render=html is not None)
    return capture_revision(req, policy or FetchPolicy(), out=out, transport=transport, clock=ScriptedClock())


def bundle(tmp: Path, text: str, body: str | None = None, *, wiki: str = "en", name: str = "b") -> Path:
    html = parsoid(body, text) if body is not None else None
    outcome = capture(tmp / name, text, html, wiki=wiki)
    assert outcome.bundle is not None, [i.code for i in outcome.issues]
    return outcome.bundle


def extract(path: Path, *, isolated: bool = False, config: ExtractConfig | None = None) -> dict[str, Any]:
    return extract_bundle(path, config, isolated=isolated)


def codes(doc: dict[str, Any]) -> set[str]:
    return {i["code"] for i in doc["issues"]}


def by_role(doc: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in doc["identifiers"]:
        out.setdefault(i["role"], []).append(i["normalization"]["normalized"])
    return out


def slice_bytes(path: Path, doc: dict[str, Any], span: dict[str, int]) -> bytes:
    cap = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    data = (path / "artifacts" / cap["source"]["artifact"]).read_bytes()
    return data[span["byte_start"] : span["byte_end"]]
