"""F4: retain the current source of the reuse template ({{r}} / {{استشهاد متعدد}}) and the module it invokes.

Usage: python template_sources.py OUT_DIR [WIKI ...]   (run from the repository root; default: en ar)

Read-only, bounded: at most 6 requests in total, through the production shared network gate (one request in flight
on the host, at least 10 s between attempts of any process, Retry-After honoured and recorded for every process).
For each wiki, request 1 is the template's wikitext (redirects followed); request 2 is the source of every module
it invokes. Every response is kept by SHA-256 together with its request in OUT_DIR/log.json.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.wiki.fetch import USER_AGENT, NetworkGate

HOSTS = {"en": "en.wikipedia.org", "ar": "ar.wikipedia.org"}
TEMPLATES = {"en": "Template:R", "ar": "قالب:استشهاد متعدد", "ar-ref": "قالب:R/ref"}  # ar-ref: the subtemplate ar calls
MAX_REQUESTS = 6
MIN_INTERVAL_S = 10.0
_INVOKE = re.compile(r"\{\{\s*#invoke:\s*([^|}]+)", re.IGNORECASE)


def get(wiki: str, params: dict[str, str], out: Path, log: list[dict[str, Any]]) -> dict[str, Any]:
    url = f"https://{HOSTS[wiki[:2]]}/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": "2"}
    )
    while True:
        if len(log) >= MAX_REQUESTS:
            raise RuntimeError("request ceiling reached")
        gate = NetworkGate.default()
        problem = gate.acquire(MIN_INTERVAL_S, 600.0)
        if problem:
            raise RuntimeError(problem)
        retry_after: float | None = None
        try:
            at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed Wikipedia hosts
                    status, headers, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
            except urllib.error.HTTPError as e:
                status, headers, raw = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
            ra = headers.get("retry-after", "")
            retry_after = float(ra) if ra.isdigit() else None
        finally:
            gate.release(retry_after)
        body = gzip.decompress(raw) if headers.get("content-encoding") == "gzip" else raw
        sha = hashlib.sha256(body).hexdigest()
        (out / "artifacts").mkdir(parents=True, exist_ok=True)
        (out / "artifacts" / sha).write_bytes(body)
        log.append({"url": url, "at": at, "status": status, "body_sha256": sha, "retry_after": ra or None})
        # Written after every attempt, so an interrupted run keeps its log.
        (out / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", "utf-8")
        if status == 200:
            data: dict[str, Any] = json.loads(body)
            if "error" in data:
                raise RuntimeError(f"API error {data['error'].get('code')}: {url}")
            return data
        if status not in (429, 503) or retry_after is None:
            raise RuntimeError(f"HTTP {status}: {url}")
        # The gate already holds the Retry-After time for every process; the next acquire waits for it.


def pages(data: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in data.get("query", {}).get("pages", []):
        rev = (p.get("revisions") or [{}])[0]
        out.append(
            {
                "title": p["title"],
                "missing": bool(p.get("missing")),
                "revid": rev.get("revid"),
                "sha1": rev.get("sha1"),
                "content": rev.get("slots", {}).get("main", {}).get("content"),
            }
        )
    return out


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    result: dict[str, Any] = {"user_agent": USER_AGENT, "wikis": {}}
    base = {"action": "query", "prop": "revisions", "rvprop": "ids|sha1|content", "rvslots": "main"}
    for wiki in sys.argv[2:] or ["en", "ar"]:
        title = TEMPLATES[wiki]
        data = get(wiki, {**base, "titles": title, "redirects": "1"}, out, log)
        found = pages(data)
        modules = sorted({m.strip() for p in found for m in _INVOKE.findall(p["content"] or "")})
        entry: dict[str, Any] = {"requested": title, "redirects": data.get("query", {}).get("redirects", [])}
        entry["templates"] = found
        if modules:
            data = get(wiki, {**base, "titles": "|".join("Module:" + m for m in modules), "redirects": "1"}, out, log)
            entry["modules"] = pages(data)
        result["wikis"][wiki] = entry
    result["log"] = log
    for wiki in result["wikis"].values():
        for p in [*wiki["templates"], *wiki.get("modules", [])]:
            if p["content"] is not None:
                p["content_sha256"] = hashlib.sha256(p["content"].encode("utf-8")).hexdigest()
    (out / f"template_sources_{'_'.join(result['wikis'])}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", "utf-8"
    )
    sys.stdout.write(f"{len(log)} requests\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
