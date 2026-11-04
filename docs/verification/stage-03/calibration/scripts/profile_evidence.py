"""Stage 03 calibration: the API evidence behind the bilingual support profile (standard library only).

Bounded, read-only requests (one in flight, at least 10 s apart, Retry-After honored):
  1. enwiki: redirects to, and Arabic interlanguage links of, the citation, identifier-wrapper, marker and
     reference-list templates named below;
  2. arwiki: the same for the Arabic counterparts found in 1, plus the English names resolved on arwiki;
  3. both wikis: Module:Citation/CS1/Configuration (the parameter alias tables of the CS1 module);
  4. arwiki: the source of the localized retraction marker template.
Every response is kept by SHA-256 with its request, so the profile can be rebuilt and audited.

Usage: python profile_evidence.py OUT_DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
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
EN_TEMPLATES = [
    "Cite journal",
    "Cite web",
    "Cite book",
    "Cite news",
    "Citation",
    "Cite magazine",
    "Cite report",
    "Cite thesis",
    "Cite conference",
    "Cite encyclopedia",
    "Cite press release",
    "Cite arXiv",
    "Cite bioRxiv",
    "Cite medRxiv",
    "Cite AV media",
    "Cite dictionary",
    "Cite tech report",
    "Cite interview",
    "Cite speech",
    "Cite map",
    "Vcite journal",
    "Vcite book",
    "Vcite web",
    "Cite Q",
    "Doi",
    "PMID",
    "Retracted",
    "Expression of concern",
    "Erratum",
    "Reflist",
    "Refn",
    "Efn",
    "Efn-ua",
    "Efn-lr",
    "Notelist",
    "R",
    "Sfn",
    "Sfnp",
    "Harvnb",
    "Rp",
    "Cite court",
    "Cite Dictionary.com",
    "Webarchive",
    "Citation-attribution",
    "Lay source",
    "Unreliable medical source",
    "Cite episode",
    "Cite mailing list",
    "Cite newsgroup",
    "Cite podcast",
    "Cite serial",
    "Cite sign",
    "Cite SSRN",
    "Cite CiteSeerX",
    "Cite document",
]
# Template names seen in the development sources (calibration material only) that are not counterparts of the
# names above; their sources are fetched so the profile can say what they are.
AR_SEEN = [
    "استشهاد بويب",
    "استشهاد بمجلة",
    "استشهاد ببيان صحفي",
    "استشهاد بأرخايف",
    "استشهاد بموسوعة",
    "استشهاد بويكي بيانات",
    "أرشيف الويب",
    "مراجع",
    "مصدر مسحوب",
]
MIN_INTERVAL = 10.0
_last = [0.0]


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(wiki: str, params: dict[str, str], out: Path, log: list[dict[str, Any]]) -> dict[str, Any]:
    url = f"https://{HOSTS[wiki]}/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": "2"}
    )
    for attempt in range(1, 5):
        wait = MIN_INTERVAL - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed Wikipedia hosts
                status, headers, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            status, headers, raw = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
        body = gzip.decompress(raw) if headers.get("content-encoding") == "gzip" else raw
        sha = hashlib.sha256(body).hexdigest()
        (out / "artifacts" / sha).write_bytes(body)
        log.append(
            {
                "url": url,
                "attempt": attempt,
                "at": now(),
                "status": status,
                "body_sha256": sha,
                "retry_after": headers.get("retry-after"),
            }
        )
        if status == 200:
            data: dict[str, Any] = json.loads(body)
            if "error" not in data:
                return data
            if data["error"].get("code") not in ("maxlag", "ratelimited"):
                raise RuntimeError(f"API error {data['error'].get('code')}: {url}")
        ra = headers.get("retry-after", "")
        time.sleep(float(ra) + 1 if ra.isdigit() else 15)
    raise RuntimeError(f"failed: {url}")


def query_all(wiki: str, params: dict[str, str], out: Path, log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages: dict[str, dict[str, Any]] = {}
    extra: dict[str, Any] = {}
    cont: dict[str, str] = {}
    while True:
        data = get(wiki, {**params, **cont}, out, log)
        q = data.get("query", {})
        for key in ("redirects", "normalized"):
            extra.setdefault(key, []).extend(q.get(key, []))
        for p in q.get("pages", []):
            cur = pages.setdefault(p["title"], {k: v for k, v in p.items() if k not in ("redirects", "langlinks")})
            cur.setdefault("redirects", []).extend(p.get("redirects", []))
            cur.setdefault("langlinks", []).extend(p.get("langlinks", []))
        if "continue" not in data:
            return [{"pages": list(pages.values()), **extra}]
        cont = {k: str(v) for k, v in data["continue"].items()}


def main() -> int:
    out = Path(sys.argv[1])
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    result: dict[str, Any] = {"run_at": now(), "user_agent": USER_AGENT}
    # The API accepts at most 50 titles per request.
    batches = [EN_TEMPLATES[i : i + 40] for i in range(0, len(EN_TEMPLATES), 40)]
    base = {
        "action": "query",
        "prop": "redirects|langlinks|info",
        "rdlimit": "max",
        "rdnamespace": "10",
        "lllang": "ar",
        "lllimit": "max",
    }
    result["en_templates"] = [
        query_all("en", {**base, "titles": "|".join("Template:" + t for t in b)}, out, log)[0] for b in batches
    ]
    ar_names = sorted(
        {ll["title"] for r in result["en_templates"] for p in r["pages"] for ll in p.get("langlinks", [])}
    )
    result["ar_counterparts"] = ar_names
    ar_base = {"action": "query", "prop": "redirects|info", "rdlimit": "max", "rdnamespace": "10"}
    result["ar_templates"] = [
        query_all("ar", {**ar_base, "titles": "|".join(ar_names[i : i + 40])}, out, log)[0]
        for i in range(0, len(ar_names), 40)
    ]
    result["ar_english_names"] = [
        query_all(
            "ar",
            {"action": "query", "prop": "info", "redirects": "1", "titles": "|".join("Template:" + t for t in b)},
            out,
            log,
        )[0]
        for b in batches
    ]
    for wiki in ("en", "ar"):
        result[f"{wiki}_cs1_configuration"] = (
            get(
                wiki,
                {
                    "action": "query",
                    "prop": "revisions",
                    "rvprop": "ids|timestamp|sha1|content",
                    "rvslots": "main",
                    "titles": "Module:Citation/CS1/Configuration",
                },
                out,
                log,
            )["query"]["pages"][0]
            .get("revisions", [{}])[0]
            .get("revid")
        )
    result["ar_marker_template"] = get(
        "ar",
        {
            "action": "query",
            "prop": "revisions|info",
            "rvprop": "ids|timestamp|sha1|content",
            "rvslots": "main",
            "titles": "قالب:مصدر مسحوب|قالب:Retracted",
        },
        out,
        log,
    )

    # 5. Template sources (redirects resolved): which templates invoke the CS1 module, with which class.
    def sources(wiki: str, names: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        prefix = "Template:" if wiki == "en" else "قالب:"
        for i in range(0, len(names), 20):
            batch = names[i : i + 20]
            data = get(
                wiki,
                {
                    "action": "query",
                    "prop": "revisions",
                    "rvprop": "ids|sha1|content",
                    "rvslots": "main",
                    "redirects": "1",
                    "titles": "|".join(n if ":" in n else prefix + n for n in batch),
                },
                out,
                log,
            )
            q = data.get("query", {})
            for p in q.get("pages", []):
                rev = (p.get("revisions") or [{}])[0]
                content = rev.get("slots", {}).get("main", {}).get("content", "")
                invokes = sorted(set(re.findall(r"\{\{\s*#invoke:\s*([^|}]+?)\s*\|\s*([^|}]*)", content)))
                classes = sorted(set(re.findall(r"CitationClass\s*=\s*([^|}\s]+)", content)))
                rows.append(
                    {
                        "title": p["title"],
                        "missing": bool(p.get("missing")),
                        "revid": rev.get("revid"),
                        "sha1": rev.get("sha1"),
                        "invokes": invokes,
                        "citation_classes": classes,
                        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    }
                )
            rows.append({"redirects": q.get("redirects", []), "normalized": q.get("normalized", [])})
        return rows

    result["en_template_sources"] = sources("en", EN_TEMPLATES)
    result["ar_template_sources"] = sources("ar", sorted(set(ar_names) | set(AR_SEEN)))
    result["log"] = log
    (out / "profile_evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
