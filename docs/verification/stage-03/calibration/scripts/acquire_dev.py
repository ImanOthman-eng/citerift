"""Stage 03 calibration: bounded acquisition of the development corpus (standard library only).

For each development article this fetches, one request at a time with at least MIN_INTERVAL seconds between
requests and Retry-After honored:
  1. the source revision (Action API query, prop=revisions|info, main slot, content in the same request);
  2. the legacy parser HTML of that revision (Action API parse, oldid);
  3. the Parsoid HTML of that revision (Core REST /v1/revision/{id}/html).
Every response body is kept, content-addressed by SHA-256, and every attempt (answers and failures) is logged.
This is calibration tooling, not the production client (src/citerift/wiki).

Usage: python acquire_dev.py SELECTION.json OUT_DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USER_AGENT = (
    "CITERIFT-Stage03-calibration/0.1 (https://github.com/ImanOthman-eng/citerift; read-only research; "
    "contact via GitHub issues)"
)
HOSTS = {"en": "en.wikipedia.org", "ar": "ar.wikipedia.org"}
MIN_INTERVAL = 10.0
MAX_ATTEMPTS = 4
TIMEOUT = 60
MAX_BODY = 32 * 1024 * 1024
_last = [0.0]


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url: str, log: list[dict[str, Any]], store: Path) -> tuple[int, dict[str, str], bytes | None]:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        wait = MIN_INTERVAL - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})  # noqa: S310
        t0 = time.monotonic()
        entry: dict[str, Any] = {"url": url, "attempt": attempt, "at": now()}
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 - fixed Wikipedia hosts
                status, headers, raw = r.status, dict(r.headers.items()), r.read(MAX_BODY + 1)
        except urllib.error.HTTPError as e:
            status, headers, raw = e.code, dict(e.headers.items()), e.read(MAX_BODY + 1)
        except (urllib.error.URLError, TimeoutError) as e:
            entry.update({"error": type(e).__name__, "detail": str(e)[:200], "seconds": round(time.monotonic() - t0, 3)})
            log.append(entry)
            continue
        wire = len(raw)
        body = gzip.decompress(raw) if headers.get("Content-Encoding", headers.get("content-encoding")) == "gzip" else raw
        sha = hashlib.sha256(body).hexdigest()
        (store / sha).write_bytes(body)
        entry.update(
            {
                "status": status,
                "seconds": round(time.monotonic() - t0, 3),
                "wire_bytes": wire,
                "body_bytes": len(body),
                "body_sha256": sha,
                "headers": {
                    k.lower(): v
                    for k, v in headers.items()
                    if k.lower()
                    in {"content-type", "retry-after", "content-revision-id", "etag", "content-encoding", "age", "date"}
                },
            }
        )
        log.append(entry)
        if status == 200:
            return status, entry["headers"], body
        if status in (429, 503) and attempt < MAX_ATTEMPTS:
            ra = entry["headers"].get("retry-after", "")
            time.sleep(float(ra) + 1 if ra.isdigit() else 10)
            continue
        return status, entry["headers"], body
    return 0, {}, None


def api(wiki: str, params: dict[str, str]) -> str:
    return f"https://{HOSTS[wiki]}/w/api.php?" + urllib.parse.urlencode(params)


def main() -> int:
    selection = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    store = out / "artifacts"
    store.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    results = []
    for item in selection["articles"]:
        wiki = item["wiki"]
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions|info",
            "rvprop": "ids|timestamp|flags|size|sha1|contentmodel|content",
            "rvslots": "main",
            "maxlag": "5",
        }
        if "revision_id" in item:
            params["revids"] = str(item["revision_id"])
        else:
            params["titles"] = item["title"]
        status, _, body = fetch(api(wiki, params), log, store)
        rec: dict[str, Any] = {"wiki": wiki, "request": item, "source_status": status}
        if status != 200 or body is None:
            results.append(rec)
            continue
        data = json.loads(body)
        page = data["query"]["pages"][0]
        rev = page["revisions"][0]
        revid = rev["revid"]
        rec.update(
            {
                "page_id": page["pageid"],
                "title": page["title"],
                "revision_id": revid,
                "source_sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        parse = {
            "action": "parse",
            "format": "json",
            "formatversion": "2",
            "oldid": str(revid),
            "prop": "text|revid|parsewarnings",
            "disableeditsection": "1",
            "maxlag": "5",
        }
        s2, _, b2 = fetch(api(wiki, parse), log, store)
        rec["parse_status"] = s2
        rec["parse_sha256"] = hashlib.sha256(b2).hexdigest() if b2 else None
        s3, h3, b3 = fetch(f"https://{HOSTS[wiki]}/w/rest.php/v1/revision/{revid}/html", log, store)
        rec["rest_status"] = s3
        rec["rest_sha256"] = hashlib.sha256(b3).hexdigest() if b3 else None
        rec["rest_headers"] = h3
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False)[:300], flush=True)
    manifest = {"run_at": now(), "user_agent": USER_AGENT, "min_interval_s": MIN_INTERVAL, "results": results, "log": log}
    (out / "acquisition.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
