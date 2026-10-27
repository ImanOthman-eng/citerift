"""Stage 01 feasibility probe for CITERIFT.

Reads the pinned Crossref Retraction Watch snapshot, cross-checks records with the Crossref REST API, and discovers
DOI citations in English and Arabic Wikipedia with documented MediaWiki API methods (PROTOCOL.md §3).

Standard library only. Every HTTP response is cached as JSON under --cache (outside the repository), so a rerun with
the same cache reproduces the same output without network access; --refresh fetches again. Only derived, minimal
records are written to --out.

Feasibility tooling for Stage 01 only: it is not CITERIFT's retraction engine (Stage 02) or extractor (Stage 03).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USER_AGENT = (
    "CITERIFT-Stage01-feasibility/0.1 (https://github.com/ImanOthman-eng/citerift; read-only research; "
    "contact via GitHub issues)"
)
RW_SOURCE = {
    "repository": "https://gitlab.com/crossref/retraction-watch-data",
    "commit": "a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4",
    "path": "retraction_watch.csv",
    "git_blob": "2a466638299c351ae50ae8e5736c410b96b99045",
    "sha256": "2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655",
    "readme_generated_on": "2026-10-23",
}
RW_URL = f"{RW_SOURCE['repository']}/-/raw/{RW_SOURCE['commit']}/{RW_SOURCE['path']}"
SAMPLE_SEED = 20261026
SAMPLE_SIZE = 200
MIN_INTERVAL = 1.0  # seconds between requests to one host (all Wikipedia editions count as one host)
MAX_ATTEMPTS = 6
TIMEOUT = 30
RETRY_STATUSES = {429, 500, 502, 503, 504}
# MediaWiki reports some overload conditions as HTTP 200 with an error body; they are retried like a 429.
TRANSIENT_API_ERRORS = {"maxlag", "cirrussearch-too-busy-error", "ratelimited"}
MISSING_DOI = {"", "unavailable"}
# Words that mark a retraction near a citation. Observed text only; their absence proves nothing.
RETRACTION_MARKERS = re.compile(r"retract|سحب|مسحوب|سُحب", re.IGNORECASE)


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_doi(doi: str) -> str:
    return doi.strip().lower()


class Client:
    """Throttled, retrying, caching HTTP JSON client."""

    def __init__(self, cache: Path, refresh: bool = False) -> None:
        self.cache = cache
        self.refresh = refresh
        self.cache.mkdir(parents=True, exist_ok=True)
        self.last: dict[str, float] = {}
        self.log: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        key = self.cache / (hashlib.sha256(full.encode()).hexdigest() + ".json")
        if key.is_file() and not self.refresh:
            cached: dict[str, Any] = json.loads(key.read_text(encoding="utf-8"))
            # Responses cached before 2026-10-27 may carry an API error body; they are not answers and are refetched.
            if cacheable(cached):
                self.log.append({"url": full, "status": cached["status"], "cached": True, "at": cached["retrieved_at"]})
                return cached
        host = urllib.parse.urlsplit(full).netloc
        wm = host.endswith((".wikipedia.org", ".wikimedia.org"))
        host = "wikimedia" if wm else host  # one rate limit for all Wikimedia hosts
        attempts: list[dict[str, Any]] = []
        result: dict[str, Any] | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            wait = MIN_INTERVAL - (time.monotonic() - self.last.get(host, 0.0))
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.monotonic()
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            req = urllib.request.Request(full, headers=headers)  # noqa: S310 - fixed https hosts
            status, retry_after, body = 0, None, b""
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 - fixed https hosts
                    status, body = r.status, r.read()
                    retry_after = r.headers.get("Retry-After")
            except urllib.error.HTTPError as e:
                status, body, retry_after = e.code, e.read(), e.headers.get("Retry-After")
            except (urllib.error.URLError, TimeoutError) as e:
                attempts.append({"attempt": attempt, "error": type(e).__name__, "at": now()})
                time.sleep(min(2**attempt, 60))
                continue
            entry = {"attempt": attempt, "status": status, "retry_after": retry_after, "at": now()}
            attempts.append(entry)
            if status == 200:
                try:
                    data = json.loads(body)
                except ValueError:
                    data = None
                entry["api_error"] = api_error(data)
                if entry["api_error"] not in TRANSIENT_API_ERRORS:
                    result = {"url": full, "status": status, "retrieved_at": now(), "body": data}
                    break
            elif status not in RETRY_STATUSES:
                result = {"url": full, "status": status, "retrieved_at": now(), "body": None}
                break
            delay = float(retry_after) if retry_after and retry_after.isdigit() else float(2**attempt)
            time.sleep(min(delay + 1, 120))
        if result is None:
            result = {"url": full, "status": "failed", "retrieved_at": now(), "body": None}
        result["attempts"] = attempts
        self.log.append({"url": full, "status": result["status"], "cached": False, "attempts": len(attempts)})
        if cacheable(result):
            key.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result


def api_error(body: Any) -> str | None:
    """The MediaWiki API error code of a response body, or None when the body carries no error."""
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return str(body["error"].get("code", "unknown"))
    return None


def cacheable(res: dict[str, Any]) -> bool:
    """Only an HTTP 200 JSON answer without an API error is cached or served from the cache."""
    return res["status"] == 200 and isinstance(res["body"], (dict, list)) and not api_error(res["body"])


def api_ok(res: dict[str, Any]) -> bool:
    """A usable Action API answer: HTTP 200, a JSON object, no error, and a query section."""
    body = res["body"]
    return (
        res["status"] == 200 and isinstance(body, dict) and not api_error(body) and isinstance(body.get("query"), dict)
    )


# ------------------------------------------------------------------ Retraction Watch


def rw_load(path: Path, check: bool = True) -> list[dict[str, str]]:
    if check and sha256_file(path) != RW_SOURCE["sha256"]:
        sys.exit(f"{path} is not the pinned snapshot (sha256 differs); download {RW_URL}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rw_record(r: dict[str, str]) -> dict[str, Any]:
    keep = ["Record ID", "RetractionNature", "RetractionDate", "RetractionDOI", "RetractionPubMedID"]
    keep += ["OriginalPaperDate", "OriginalPaperDOI", "OriginalPaperPubMedID", "Journal", "Publisher", "Title"]
    return {k: r[k] for k in keep}


def rw_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    idx: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        d = norm_doi(r["OriginalPaperDOI"])
        if d not in MISSING_DOI:
            idx.setdefault(d, []).append(r)
    return idx


def rw_profile(rows: list[dict[str, str]]) -> dict[str, Any]:
    missing = [norm_doi(r["OriginalPaperDOI"]) in MISSING_DOI for r in rows]
    natures: dict[str, set[str]] = {}
    for r in rows:
        d = norm_doi(r["OriginalPaperDOI"])
        if d not in MISSING_DOI:
            natures.setdefault(d, set()).add(r["RetractionNature"])
    same = sum(
        1
        for r in rows
        if norm_doi(r["OriginalPaperDOI"]) not in MISSING_DOI
        and norm_doi(r["OriginalPaperDOI"]) == norm_doi(r["RetractionDOI"])
    )
    pmid_missing = sum(r["OriginalPaperPubMedID"].strip() in ("", "0") for r in rows)
    notice_shared = Counter(
        norm_doi(r["RetractionDOI"]) for r in rows if norm_doi(r["RetractionDOI"]) not in MISSING_DOI
    )
    return {
        "records": len(rows),
        "by_nature": dict(Counter(r["RetractionNature"] for r in rows)),
        "original_doi_missing": sum(missing),
        "original_pmid_missing": pmid_missing,
        "notice_doi_missing": sum(norm_doi(r["RetractionDOI"]) in MISSING_DOI for r in rows),
        "notice_doi_equals_original_doi": same,
        "distinct_original_dois": len(natures),
        "original_dois_with_several_event_types": sum(len(v) > 1 for v in natures.values()),
        "event_type_combinations": {
            " + ".join(sorted(v)): n
            for v, n in Counter(frozenset(v) for v in natures.values() if len(v) > 1).most_common()
        },
        "notice_dois_shared_by_several_records": sum(1 for n in notice_shared.values() if n > 1),
        "date_format_example": rows[0]["RetractionDate"] if rows else None,
        "dates_not_m_d_yyyy_0_00": [
            {"record_id": r["Record ID"], "field": k, "value": r[k], "journal": r["Journal"]}
            for r in rows
            for k in ("RetractionDate", "OriginalPaperDate")
            if r[k] and not re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4} 0:00", r[k])
        ],
    }


def rw_sample(rows: list[dict[str, str]], n: int = SAMPLE_SIZE, seed: int = SAMPLE_SEED) -> list[dict[str, Any]]:
    seen: set[str] = set()
    frame = []
    for r in rows:
        d = norm_doi(r["OriginalPaperDOI"])
        if r["RetractionNature"] == "Retraction" and d not in MISSING_DOI and d not in seen:
            seen.add(d)
            frame.append(r)
    picked = random.Random(seed).sample(frame, n)  # noqa: S311 - reproducible sampling, not security
    return [{"frame_size": len(frame), **rw_record(r)} for r in picked]


# ------------------------------------------------------------------ Crossref


def crossref(client: Client, doi: str) -> dict[str, Any]:
    res = client.get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/()"))
    msg = (res["body"] or {}).get("message") if res["status"] == 200 else None
    out: dict[str, Any] = {"doi": doi, "url": res["url"], "status": res["status"], "retrieved_at": res["retrieved_at"]}
    if msg:
        out.update(
            {
                "type": msg.get("type"),
                "title": (msg.get("title") or [None])[0],
                "published": (msg.get("published") or {}).get("date-parts"),
                "updated_by": msg.get("updated-by"),
                "update_to": msg.get("update-to"),
                "relation": msg.get("relation"),
            }
        )
    return out


# ------------------------------------------------------------------ Wikipedia


def api(wiki: str) -> str:
    return f"https://{wiki}.wikipedia.org/w/api.php"


def wq(client: Client, wiki: str, **params: str) -> dict[str, Any]:
    base = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5"}
    return client.get(api(wiki), {**base, **params})


def m1_forms(doi: str) -> list[str]:
    """exturlusage queries for one DOI. The externallinks table is case-sensitive and stores CS1 DOI links with
    '/' percent-encoded (https://doi.org/10.1016%2FS0140-...), so a plain-slash query misses them (FEASIBILITY_REPORT
    §5.2). Raw links in wikitext keep the plain form. Other case variants and encodings are not queried."""
    forms = [f"doi.org/{doi.replace('/', '%2F')}"]
    if doi.lower() != doi:
        forms.append(f"doi.org/{doi.lower().replace('/', '%2F')}")
    forms += [f"doi.org/{doi}", f"dx.doi.org/{doi}"]
    return forms


def m1_exturlusage(client: Client, wiki: str, doi: str) -> dict[str, Any]:
    titles: set[str] = set()
    calls = []
    for form in m1_forms(doi):
        cont: dict[str, str] = {}
        while True:
            res = wq(client, wiki, list="exturlusage", euquery=form, eunamespace="0", eulimit="500", **cont)
            ok = api_ok(res)
            hits = sorted({p["title"] for p in res["body"]["query"].get("exturlusage", [])}) if ok else []
            calls.append(
                {
                    "url": res["url"],
                    "status": res["status"],
                    "api_error": api_error(res["body"]),
                    "ok": ok,
                    "retrieved_at": res["retrieved_at"],
                    "hits": hits,
                }
            )
            titles |= set(hits)
            if not ok or "continue" not in res["body"]:
                break
            cont = {k: str(v) for k, v in res["body"]["continue"].items()}
    return {"titles": sorted(titles), "calls": calls, "ok": all(c["ok"] for c in calls)}


def m2_search(client: Client, wiki: str, doi: str) -> dict[str, Any]:
    """CirrusSearch insource phrase query for one DOI (an OR of several insource phrases returned 0 hits, §5.2)."""
    query = f'insource:"{doi}"'
    titles: set[str] = set()
    calls = []
    offset: str | None = "0"
    while offset is not None:
        res = wq(client, wiki, list="search", srsearch=query, srnamespace="0", srlimit="50", srprop="", sroffset=offset)
        body = res["body"] if api_ok(res) else {}
        total = body.get("query", {}).get("searchinfo", {}).get("totalhits")
        # A complete answer states its total; an error body (e.g. cirrussearch-too-busy-error) is not "no hits".
        ok = isinstance(total, int)
        calls.append(
            {
                "url": res["url"],
                "status": res["status"],
                "api_error": api_error(res["body"]),
                "ok": ok,
                "retrieved_at": res["retrieved_at"],
                "totalhits": total,
            }
        )
        titles |= {p["title"] for p in body.get("query", {}).get("search", [])}
        offset = str(body["continue"]["sroffset"]) if ok and "continue" in body else None
    return {"query": query, "titles": sorted(titles), "calls": calls, "ok": all(c["ok"] for c in calls)}


def revision(client: Client, wiki: str, *, title: str | None = None, revid: int | None = None) -> dict[str, Any]:
    params = {"prop": "revisions", "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    params.update({"titles": title} if title is not None else {"revids": str(revid)})
    res = wq(client, wiki, **params)
    body = res["body"] if isinstance(res["body"], dict) else {}
    pages = body.get("query", {}).get("pages", [])
    if res["status"] != 200 or not pages or "revisions" not in pages[0]:
        gone = "badrevids" in body.get("query", {}) or (pages and ("missing" in pages[0] or "invalid" in pages[0]))
        reason = "request_failed" if res["status"] != 200 else "missing" if gone else "malformed_response"
        return {
            "ok": False,
            "reason": reason,
            "url": res["url"],
            "status": res["status"],
            "retrieved_at": res["retrieved_at"],
        }
    page, rev = pages[0], pages[0]["revisions"][0]
    return {
        "ok": True,
        "wiki": wiki,
        "title": page["title"],
        "pageid": page["pageid"],
        "revid": rev["revid"],
        "parentid": rev.get("parentid"),
        "timestamp": rev["timestamp"],
        "sha1": rev["sha1"],
        "content": rev["slots"]["main"]["content"],
        "url": res["url"],
        "retrieved_at": res["retrieved_at"],
    }


def doi_positions(text: str, doi: str) -> list[int]:
    """Start positions of doi (case-insensitive, also URL-encoded) that are not the prefix of a longer DOI.

    The search runs on the original text: lower-casing first can change its length (e.g. "İ") and shift every later
    position. A match followed by a letter or digit, or by one of ./_-:; and then a letter or digit, is part of a
    longer identifier (10.1109/fitme.2009.11 inside 10.1109/FITME.2009.112) and is not counted.
    """
    forms = {doi, urllib.parse.quote(doi, safe="/"), urllib.parse.quote(doi, safe="")}
    tail = r"(?![A-Za-z0-9]|[./_\-:;][A-Za-z0-9])"
    return sorted({m.start() for f in forms for m in re.finditer(re.escape(f) + tail, text, re.IGNORECASE)})


def template_start(text: str, pos: int) -> int | None:
    """Index of the "{{" that opens the innermost template containing pos, or None."""
    depth, i = 0, pos
    while i > 1:
        if text.startswith("}}", i - 2):
            depth += 1
            i -= 2
        elif text.startswith("{{", i - 2):
            if depth == 0:
                return i - 2
            depth -= 1
            i -= 2
        else:
            i -= 1
    return None


def template_end(text: str, start: int) -> int:
    depth, j = 0, start
    while j < len(text):
        if text.startswith("{{", j):
            depth += 1
            j += 2
        elif text.startswith("}}", j):
            depth -= 1
            j += 2
            if depth == 0:
                return j
        else:
            j += 1
    return len(text)


def reference_span(text: str, pos: int) -> tuple[int, int]:
    """The <ref>...</ref>, else the outermost template, else the line that contains pos (best effort)."""
    start = text.rfind("<ref", 0, pos)
    if start != -1 and text.rfind("</ref>", start, pos) == -1 and text.rfind("/>", start, pos) == -1:
        end = text.find("</ref>", pos)
        if end != -1:
            return start, end + 6
    outer = None
    probe = pos
    while (st := template_start(text, probe)) is not None:
        outer, probe = st, st
    if outer is not None:
        return outer, template_end(text, outer)
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    return line_start, len(text) if line_end == -1 else line_end


def enclosing_reference(text: str, pos: int, limit: int = 2000) -> str:
    start, end = reference_span(text, pos)
    return text[start:end][:limit]


def template_name(text: str, start: int) -> str:
    m = re.match(r"\{\{\s*([^|}\n]+?)\s*[|}]", text[start:])
    return m.group(1).strip().lower() if m else ""


def template_field(text: str, pos: int) -> str | None:
    """Name of the template parameter whose value contains pos, if any (best effort)."""
    window = text[max(0, pos - 20000) : pos].replace("{{!}}", "#####")
    window = re.sub(r"\[\[[^\]|\n]*\|", lambda m: "#" * len(m.group(0)), window)  # pipes of [[target|label]]
    field = re.search(r"\|\s*([^|=\n]{1,40}?)\s*=[^|}]*$", window)
    return field.group(1).strip() if field else None


def occurrence_role(text: str, pos: int) -> str:
    """How the DOI string at pos is used: as an identifier (doi parameter, doi.org or publisher URL, "DOI:" prefix,
    {{doi}} template) or only as text inside another field, such as the title of a retraction notice. Only identifier
    uses count as a citation of the DOI (FEASIBILITY_REPORT §5.3)."""
    before = text[max(0, pos - 80) : pos]
    inner = template_start(text, pos)
    if inner is not None and template_name(text, inner) in RETRACTED_TEMPLATES:
        return "in_retracted_template"  # {{Retracted|doi=<notice>}} names the notice; it is not a citation
    if re.search(r"\|\s*(?:doi|دوي)\s*=\s*$", before, re.IGNORECASE):
        return "doi_parameter"  # "دوي" is the Arabic alias used in Arabic Wikipedia citation templates
    if re.search(r"\{\{\s*doi(?:-inline)?\s*\|\s*$", before, re.IGNORECASE):
        return "doi_template"
    for role, pattern in (
        ("doi_url", r"(?:dx\.)?doi\.org/$"),
        ("publisher_url", r"https?://[^\s|\]]*/doi/(?:[a-z]+/)?$"),  # e.g. https://www.science.org/doi/<doi>
        ("doi_prefix", r"\bdoi\s*:\s*$"),  # e.g. "DOI:10.1016/..." as plain text in an older reference
    ):
        if re.search(pattern, before, re.IGNORECASE):
            field = template_field(text, pos)
            # Inside another field (e.g. a notice's title) it is a mention, not a link to or citation of the paper.
            if field is not None and field.lower() not in IDENTIFIER_FIELDS:
                return f"{role}_in_parameter:{field}"
            return role
    field = template_field(text, pos)
    return f"text_in_parameter:{field}" if field else "text"


# {{Retracted}} on enwiki (with the alias seen in data) and its Arabic localization; also used under the English
# name on arwiki (FEASIBILITY_REPORT §7.3).
RETRACTED_TEMPLATES = {"retracted", "retracted paper", "مصدر مسحوب"}
IDENTIFIER_FIELDS = {"url", "مسار", "doi", "دوي", "id", "archive-url", "مسار أرشيف", "chapter-url"}
IDENTIFIER_ROLES = {"doi_parameter", "doi_url", "doi_template", "publisher_url", "doi_prefix"}


def observe(rev: dict[str, Any], doi: str) -> dict[str, Any]:
    pos = doi_positions(rev["content"], doi)
    obs = {k: rev[k] for k in ("wiki", "title", "pageid", "revid", "parentid", "timestamp", "sha1", "retrieved_at")}
    obs["revision_url"] = f"https://{rev['wiki']}.wikipedia.org/w/index.php?oldid={rev['revid']}"
    obs["doi_occurrences"] = len(pos)
    obs["doi_present"] = bool(pos)
    roles = [occurrence_role(rev["content"], i) for i in pos]
    obs["occurrence_roles"] = roles
    # A citation of the DOI: the DOI is used as an identifier, not merely mentioned (e.g. in a notice's title).
    obs["confirmed"] = any(r in IDENTIFIER_ROLES for r in roles)
    obs["marked"] = False
    if pos:
        first = next((i for i, r in zip(pos, roles, strict=True) if r in IDENTIFIER_ROLES), pos[0])
        ref = enclosing_reference(rev["content"], first)
        obs["reference_markup"] = ref
        obs["context"] = rev["content"][max(0, first - 200) : first + 200]
        templates = re.findall(r"\{\{\s*([^|}\n]+?)\s*[|}]", ref)
        obs["templates"] = sorted(set(templates))
        obs["marked"] = marked(rev["content"], doi)
        obs["retraction_word_in_reference"] = bool(RETRACTION_MARKERS.search(ref))
        obs["named_ref"] = bool(re.match(r"<ref\s+name\s*=", ref))
    return obs


def discover(client: Client, wiki: str, doi: str, methods: tuple[str, ...]) -> dict[str, Any]:
    """Run the requested methods for one DOI, then confirm every candidate page in its latest revision."""
    empty: dict[str, Any] = {"titles": [], "calls": [], "ok": True, "skipped": True}
    m1 = m1_exturlusage(client, wiki, doi) if "m1" in methods else empty
    m2 = m2_search(client, wiki, doi) if "m2" in methods else empty
    observations = []
    for title in sorted(set(m1["titles"]) | set(m2["titles"])):
        rev = revision(client, wiki, title=title)
        if not rev["ok"]:
            observations.append({"wiki": wiki, "title": title, "confirmed": None, "fetch_status": rev["status"]})
            continue
        obs = observe(rev, doi)
        obs["found_by"] = [m for m, r in (("M1", m1), ("M2", m2)) if title in r["titles"]]
        observations.append(obs)
    return {
        "wiki": wiki,
        "doi": doi,
        "methods": list(methods),
        "m1": m1,
        "m2": m2,
        "complete": m1["ok"] and m2["ok"] and all(o["confirmed"] is not None for o in observations),
        "observations": observations,
    }


def revision_ids(client: Client, wiki: str, title: str) -> list[dict[str, Any]]:
    revs: list[dict[str, Any]] = []
    cont: dict[str, str] = {}
    while True:
        params = {"prop": "revisions", "titles": title, "rvprop": "ids|timestamp", "rvlimit": "500", "rvdir": "newer"}
        res = wq(client, wiki, **params, **cont)
        if res["status"] != 200:
            raise RuntimeError(f"revision list failed: {res['status']}")
        page = res["body"]["query"]["pages"][0]
        revs += page.get("revisions", [])
        if "continue" not in res["body"]:
            return revs
        cont = {k: str(v) for k, v in res["body"]["continue"].items()}


def cited(content: str, doi: str) -> bool:
    return any(occurrence_role(content, i) in IDENTIFIER_ROLES for i in doi_positions(content, doi))


def marked(content: str, doi: str) -> bool:
    """A {{Retracted}}-family template in a reference that cites doi, or directly after it on the same line (as in
    bibliography lists: {{cite journal ...}}{{Retracted ...}})."""
    for i in doi_positions(content, doi):
        if occurrence_role(content, i) in IDENTIFIER_ROLES:
            start, end = reference_span(content, i)
            stop = min(x for x in (content.find("\n", end), content.find("<ref", end), end + 300) if x != -1)
            names = re.findall(r"\{\{\s*([^|}\n]+?)\s*[|}]", content[start:stop])
            if any(n.strip().lower() in RETRACTED_TEMPLATES for n in names):
                return True
    return False


def first_revision_where(client: Client, wiki: str, title: str, doi: str, what: str) -> dict[str, Any]:
    """Bisect the history for the first revision where `what` ("cited" or "marked") holds.

    Assumes that once true it stays true. This is spot-checked on up to 4 evenly spaced later revisions; a
    violation means the bisection result is not reliable and is reported, not hidden.
    """
    test = cited if what == "cited" else marked
    revs = revision_ids(client, wiki, title)
    checked: dict[int, bool] = {}

    def holds(i: int) -> bool:
        if i not in checked:
            rev = revision(client, wiki, revid=revs[i]["revid"])
            if not rev["ok"]:  # a failed fetch is unknown, never "not cited"
                raise RuntimeError(f"revision {revs[i]['revid']} unavailable ({rev['status']})")
            checked[i] = test(rev["content"], doi)
        return checked[i]

    lo, hi = 0, len(revs) - 1
    if not holds(hi):
        return {"found": False, "revisions_in_history": len(revs)}
    while lo < hi:
        mid = (lo + hi) // 2
        if holds(mid):
            hi = mid
        else:
            lo = mid + 1
    later = len(revs) - 1 - lo
    spots = sorted({lo + 1 + (later * k) // 5 for k in range(1, 5)} - {len(revs)}) if later > 1 else []
    violations = [revs[i]["revid"] for i in spots if i < len(revs) and not holds(i)]
    before = revision(client, wiki, revid=revs[lo - 1]["revid"]) if lo > 0 else None
    first = revision(client, wiki, revid=revs[lo]["revid"])
    return {
        "found": True,
        "what": what,
        "revisions_in_history": len(revs),
        "probes": len(checked),
        "first": observe(first, doi),
        "before": observe(before, doi) if before else None,
        "monotonicity_spot_checks": [revs[i]["revid"] for i in spots if i < len(revs)],
        "monotonicity_violations": violations,
    }


REDIRECT = re.compile(r"\A\s*#\s*(redirect|تحويل)\b", re.IGNORECASE)


def langlinks(client: Client, wiki: str, titles: list[str], lang: str) -> dict[str, dict[str, Any]]:
    """Interlanguage link of each title to `lang`, with the outcome of the lookup stated, never guessed.

    Each title maps to {"status": ...}: "linked" (with "target"), "no_link" (successful, complete answer without a
    link), "source_missing" (the page does not exist on wiki), "request_failed" (with "http_status") or
    "malformed_response". A failed or malformed answer is never read as "no link". Batches of 50 titles follow
    `continue` until the answer is complete, and titles the API normalizes are mapped back to the requested form.
    """
    out: dict[str, dict[str, Any]] = {}
    for k in range(0, len(titles), 50):
        batch = titles[k : k + 50]
        alias: dict[str, str] = {}
        pages: dict[str, dict[str, Any]] = {}
        failure: dict[str, Any] | None = None
        cont: dict[str, str] = {}
        while True:
            res = wq(client, wiki, prop="langlinks", titles="|".join(batch), lllang=lang, lllimit="max", **cont)
            body = res["body"]
            if res["status"] != 200:
                failure = {"status": "request_failed", "http_status": res["status"]}
                break
            query = body.get("query") if isinstance(body, dict) else None
            if not isinstance(query, dict) or not isinstance(query.get("pages"), list) or "error" in body:
                failure = {"status": "malformed_response"}
                break
            alias.update({n["from"]: n["to"] for n in query.get("normalized", [])})
            for page in query["pages"]:
                rec = pages.setdefault(page.get("title", ""), {"missing": False, "links": []})
                rec["missing"] = rec["missing"] or "missing" in page or "invalid" in page
                rec["links"] += [x["title"] for x in page.get("langlinks", []) if x.get("lang") == lang]
            if "continue" not in body:
                break
            cont = {key: str(v) for key, v in body["continue"].items()}
        for t in batch:
            found = pages.get(alias.get(t, t))
            if failure is not None:
                out[t] = dict(failure)
            elif found is None:
                out[t] = {"status": "malformed_response"}
            elif found["missing"]:
                out[t] = {"status": "source_missing"}
            elif found["links"]:
                out[t] = {"status": "linked", "target": found["links"][0]}
            else:
                out[t] = {"status": "no_link"}
    return out


def crosswiki(client: Client, discovery: dict[str, Any], src: str, dst: str) -> list[dict[str, Any]]:
    """For each DOI cited on src, follow each citing article's interlanguage link to dst and check the DOI there.

    Every row states `link_status` (see langlinks) and, for a linked article, `dst_status`: "fetch_failed",
    "article_missing", "malformed_response", "redirect" (the link points to a redirect page, not followed),
    "doi_not_found", "doi_mention_only" or "doi_cited". Only the last three are observations of the article.
    """
    rows = []
    by_doi: dict[str, list[dict[str, Any]]] = {}
    for r in discovery["results"]:
        if r["wiki"] == src:
            by_doi.setdefault(r["doi"], []).extend(o for o in r["observations"] if o.get("confirmed"))
    for doi, obs in by_doi.items():
        links = langlinks(client, src, [o["title"] for o in obs], dst)
        for o in obs:
            row: dict[str, Any] = {"doi": doi, "src": {k: o[k] for k in ("wiki", "title", "revid", "sha1", "marked")}}
            link = links[o["title"]]
            row["link_status"] = link["status"]
            if "http_status" in link:
                row["link_http_status"] = link["http_status"]
            row["dst_title"] = link.get("target")
            if link["status"] == "linked":
                rev = revision(client, dst, title=link["target"])
                if not rev["ok"]:
                    row["dst_status"] = {
                        "request_failed": "fetch_failed",
                        "missing": "article_missing",
                        "malformed_response": "malformed_response",
                    }[rev["reason"]]
                    row["dst"] = {"fetch_status": rev["status"]}
                elif REDIRECT.match(rev["content"]):
                    row["dst_status"] = "redirect"
                    row["dst"] = {k: rev[k] for k in ("wiki", "title", "revid", "sha1", "timestamp")}
                else:
                    ob = observe(rev, doi)
                    row["dst"] = {k: ob[k] for k in ("wiki", "title", "revid", "sha1", "timestamp", "confirmed")}
                    row["dst"]["doi_present"] = ob["doi_present"]
                    row["dst"]["marked"] = ob.get("marked", False)
                    row["dst_status"] = (
                        "doi_cited" if ob["confirmed"] else "doi_mention_only" if ob["doi_present"] else "doi_not_found"
                    )
            rows.append(row)
    return rows


def absence_check(client: Client, wiki: str, revid: int, needles: list[str], context: int = 0) -> dict[str, Any]:
    """Count plain substrings in a pinned revision: a check of a negative control that does not reuse doi_positions.

    With context > 0, also keep that many characters on each side of every occurrence (short quotations).
    """
    rev = revision(client, wiki, revid=revid)
    if not rev["ok"]:
        return {"wiki": wiki, "revid": revid, "fetch_status": rev["status"]}
    text = rev["content"]
    low = text.casefold()
    counts = {n: low.count(n.casefold()) for n in needles}
    keep = ("wiki", "title", "revid", "timestamp", "sha1", "retrieved_at")
    out = {**{k: rev[k] for k in keep}, "length": len(text), "counts": counts}
    if context:
        out["contexts"] = {
            n: [
                {"offset": m.start(), "text": text[max(0, m.start() - context) : m.end() + context]}
                for m in re.finditer(re.escape(n), text, re.IGNORECASE)
            ]
            for n in needles
        }
    return out


def pubmed_link(pmid: str) -> re.Pattern[str]:
    return re.compile(rf"pubmed\.ncbi\.nlm\.nih\.gov/{re.escape(pmid)}(?!\d)|/pubmed/{re.escape(pmid)}(?!\d)")


REDLINK = re.compile(r'<a [^>]*class="new"[^>]*>.*?</a>', re.DOTALL)
CITE = re.compile(r"<cite\b.*?</cite>", re.DOTALL)


def tag_text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def rendered_references(html_text: str, doi: str | None, pmid: str | None = None) -> list[dict[str, Any]]:
    """Reference-list items of rendered article HTML that contain the DOI (or, given pmid, a PubMed link with that
    PMID), with what each item displays.

    Retraction wording is looked for outside links to missing pages (class "new"): a template that does not exist
    renders as a red link showing its own name (e.g. "قالب:Retracted"), which is recorded separately, not as a warning.
    Text inside the citation (<cite>) is skipped too, so a paper title such as "RETRACTED: …" is not a warning. The
    DOI must not be the prefix of a longer DOI. Limitation: the Arabic stem سحب also matches unrelated words.
    """
    items = []
    # MediaWiki writes the id as cite_note-… or, entity-encoded, cite&#95;note-…
    for part in re.split(r'<li id="cite(?:_|&#95;)note', html_text)[1:]:
        seg = part.split("</li>", 1)[0].split(">", 1)[-1]
        if contains_identifier(seg, doi, pmid):
            items.append(describe_segment(seg))
    return items


BLOCK = re.compile(r"<(li|p|dd)\b([^>]*)>(.*?)</\1>", re.DOTALL)


def rendered_other_items(html_text: str, doi: str | None, pmid: str | None = None) -> list[dict[str, Any]]:
    """List items, paragraphs and definition items outside the footnote list that contain the identifier, such as a
    "further reading" bibliography, described as rendered_references describes footnotes."""
    return [
        {**describe_segment(m.group(3)), "location": f"{m.group(1)}_outside_footnotes"}
        for m in BLOCK.finditer(html_text)
        if "cite_note" not in m.group(2)
        and "cite&#95;note" not in m.group(2)
        and contains_identifier(m.group(3), doi, pmid)
    ]


def contains_identifier(seg: str, doi: str | None, pmid: str | None) -> bool:
    plain = urllib.parse.unquote(html.unescape(seg))
    return bool(doi_positions(plain, doi) if doi else pmid and pubmed_link(pmid).search(plain))


def describe_segment(seg: str) -> dict[str, Any]:
    # The citation itself (<cite>, with the paper's title, e.g. "RETRACTED: …") is not a warning.
    text = tag_text(CITE.sub(" ", REDLINK.sub(" ", seg)))
    terms = [
        {"term": m.group(0), "context": text[max(0, m.start() - 60) : m.end() + 60]}
        for m in RETRACTION_MARKERS.finditer(text)
    ]
    redlinks = re.findall(r'<a [^>]*class="new"[^>]*title="([^"]*)"', seg)
    if terms:
        state = "warning_text"
    elif any(RETRACTION_MARKERS.search(t) for t in redlinks):
        state = "missing_template_link_only"
    else:
        state = "no_warning_text"
    return {"state": state, "warning_terms": terms, "missing_page_links": redlinks, "text_excerpt": tag_text(seg)[:300]}


def parse_html(client: Client, wiki: str, revid: int) -> tuple[dict[str, Any], str | None]:
    """Parser HTML of a pinned revision, or None when the render failed (an error body counts as a failure)."""
    params = {"action": "parse", "format": "json", "formatversion": "2", "oldid": str(revid), "prop": "text|revid"}
    res = client.get(api(wiki), {**params, "maxlag": "5"})
    out = {"wiki": wiki, "revid": revid, "url": res["url"], "status": res["status"]}
    out["retrieved_at"] = res["retrieved_at"]
    body = res["body"]
    parsed = body.get("parse") if res["status"] == 200 and isinstance(body, dict) and not api_error(body) else None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("text"), str):
        return {**out, "api_error": api_error(body)}, None
    return out, parsed["text"]


def render_check(client: Client, wiki: str, revid: int, doi: str) -> dict[str, Any]:
    """Rendered (parser HTML) check of the references that cite a DOI in a pinned revision.

    The state says what was inspected in the desktop parser output, not what every reader sees: skins, the mobile
    view, gadgets and CSS were not checked. A failed render is never read as an absent warning.
    """
    meta, text = parse_html(client, wiki, revid)
    out = {"wiki": wiki, "revid": revid, "doi": doi, **meta}
    if text is None:
        return {**out, "state": "render_unavailable"}
    refs = rendered_references(text, doi)
    return {**out, "state": rendered_state(refs), "references": refs}


def rendered_state(refs: list[dict[str, Any]]) -> str:
    states = {r["state"] for r in refs}
    if not refs:
        state = "reference_not_found_in_render"
    elif len(states) == 1:
        state = {
            "warning_text": "warning_text_in_rendered_reference",
            "missing_template_link_only": "missing_template_link_only_in_rendered_reference",
            "no_warning_text": "no_warning_text_in_inspected_rendered_reference",
        }[states.pop()]
    else:
        state = "mixed"
    return state


# ------------------------------------------------------------------ verification of a manifest


def verify_manifest(client: Client, manifest: dict[str, Any]) -> dict[str, Any]:
    """Re-fetch every pinned revision and Crossref record of a manifest and compare them with what it states.

    Each distinct revision is fetched once; each claim about it (case, timeline, sample observation) is checked.
    """
    problems = []
    revs: dict[tuple[str, int], dict[str, Any]] = {}
    works: dict[str, dict[str, Any]] = {}
    checks = 0

    def rev_of(wiki: str, revid: int) -> dict[str, Any]:
        if (wiki, revid) not in revs:
            revs[(wiki, revid)] = revision(client, wiki, revid=revid)
        return revs[(wiki, revid)]

    def work(doi: str) -> dict[str, Any]:
        if doi.lower() not in works:
            works[doi.lower()] = crossref(client, doi)
        return works[doi.lower()]

    pinned = [
        (case["case_id"], obs.get("checked_doi", case["original_doi"]), obs)
        for case in manifest["cases"]
        for obs in case.get("wikipedia", [])
    ]
    pinned += [
        (name, obs["doi"], obs) for name, agg in manifest["aggregates"].items() for obs in agg.get("observations", [])
    ]
    for label, doi, obs in pinned:
        checks += 1
        where = f"{label}: {obs['wiki']} revid {obs['revid']}"
        rev = rev_of(obs["wiki"], obs["revid"])
        if not rev["ok"]:
            problems.append(f"{where} not retrievable")
            continue
        if rev["sha1"] != obs["sha1"]:
            problems.append(f"{where} sha1 differs")
        ob = observe(rev, doi)
        if ob["doi_present"] != obs["doi_present"]:
            problems.append(f"{where} presence {ob['doi_present']}")
        if ob["confirmed"] != obs["cited_as_identifier"]:
            problems.append(f"{where} identifier {ob['confirmed']}")
    for case in manifest["cases"]:
        for tl in case.get("timeline", []):
            for key in ("first_cited", "first_marked"):
                for pin in (tl[key], (tl[key] or {}).get("previous_revision")):
                    if not pin:
                        continue
                    checks += 1
                    rev = rev_of(tl["wiki"], pin["revid"])
                    if not rev["ok"] or rev["sha1"] != pin["sha1"]:
                        problems.append(f"{case['case_id']}: timeline {tl['wiki']} revid {pin['revid']} differs")
        notices = [ev["notice_doi"] for ev in case.get("retraction_events", []) if ev.get("notice_doi")]
        notices += [case["notice_doi"]] if case.get("notice_doi") else []
        for doi in notices:
            checks += 1
            if work(doi)["status"] != 200:
                problems.append(f"{case['case_id']}: notice {doi} Crossref status {work(doi)['status']}")
        status = case.get("retraction_status")
        if status and status.get("value") == "not_found_in_checked_sources":
            checks += 1
            cr = work(case["original_doi"])
            if cr["status"] != status["crossref_status"] or cr.get("updated_by") != status["crossref_updated_by"]:
                problems.append(f"{case['case_id']}: Crossref record of {case['original_doi']} differs")
    return {
        "run_at": now(),
        "checks": checks,
        "distinct_revisions": len(revs),
        "distinct_crossref_works": len(works),
        "problems": problems,
    }


# ------------------------------------------------------------------ CLI


def write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cache", type=Path, required=True, help="response cache directory (outside the repository)")
    p.add_argument("--refresh", action="store_true", help="ignore cached responses")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("rw-profile", help="data-quality profile of the pinned snapshot")
    s.add_argument("--csv", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("sample", help="draw the systematic sample S")
    s.add_argument("--csv", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("lookup", help="Retraction Watch records and Crossref metadata for DOIs")
    s.add_argument("--csv", type=Path, required=True)
    s.add_argument("--dois", nargs="+", required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("discover", help="M1 + M2 discovery with confirmation for DOIs on wikis")
    s.add_argument("--dois-file", type=Path, required=True, help="JSON list of DOIs or of sample records")
    s.add_argument("--wikis", default="en,ar")
    s.add_argument("--methods", default="m1,m2", help="m1 (exturlusage), m2 (insource search), or both")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("first-revision", help="bisect history for the first revision citing (or marking) a DOI")
    s.add_argument("--wiki", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--doi", required=True)
    s.add_argument("--what", choices=["cited", "marked"], default="cited")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("crosswiki", help="follow interlanguage links of citing articles between two wikis")
    s.add_argument("--discovery", type=Path, required=True)
    s.add_argument("--src", required=True)
    s.add_argument("--dst", required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("absence-check", help="count plain substrings in pinned revisions (negative controls)")
    s.add_argument("--wiki", required=True)
    s.add_argument("--revids", nargs="+", type=int, required=True)
    s.add_argument("--needles", nargs="+", required=True)
    s.add_argument("--context", type=int, default=0, help="characters of context to keep around each occurrence")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("render-check", help="rendered (parser HTML) check of the references citing a DOI")
    s.add_argument("--wiki", required=True)
    s.add_argument("--revids", nargs="+", type=int, required=True)
    s.add_argument("--doi", required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("api-query", help="one read-only Action API query on a Wikimedia wiki, saved as returned")
    s.add_argument("--host", required=True, help="e.g. ar.wikipedia.org or meta.wikimedia.org")
    s.add_argument("--param", action="append", default=[], help="key=value, repeatable")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("verify", help="re-check every pinned revision and notice in a manifest")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--out", type=Path, help="also write the result as JSON")
    a = p.parse_args(argv)
    client = Client(a.cache, a.refresh)

    if a.cmd == "rw-profile":
        rows = rw_load(a.csv)
        prof = rw_profile(rows)
        write(a.out, {"source": RW_SOURCE, "file_bytes": a.csv.stat().st_size, "computed_at": now(), "profile": prof})
    elif a.cmd == "sample":
        rows = rw_load(a.csv)
        sample = rw_sample(rows)
        write(a.out, {"source": RW_SOURCE, "seed": SAMPLE_SEED, "n": SAMPLE_SIZE, "records": sample})
    elif a.cmd == "lookup":
        rows = rw_load(a.csv)
        idx = rw_index(rows)
        out = []
        for doi in a.dois:
            recs = [rw_record(r) for r in idx.get(norm_doi(doi), [])]
            as_notice = [r["Record ID"] for r in rows if norm_doi(r["RetractionDOI"]) == norm_doi(doi)]
            notices = sorted({r["RetractionDOI"] for r in recs if norm_doi(r["RetractionDOI"]) not in MISSING_DOI})
            out.append(
                {
                    "doi": doi,
                    "retraction_watch": recs,
                    "retraction_watch_records_naming_it_as_notice": as_notice,
                    "crossref_original": crossref(client, doi),
                    "crossref_notices": [crossref(client, n) for n in notices],
                }
            )
        write(a.out, {"source": RW_SOURCE, "results": out})
    elif a.cmd == "discover":
        raw = json.loads(a.dois_file.read_text(encoding="utf-8"))
        items = raw["records"] if isinstance(raw, dict) else raw
        dois = [i["OriginalPaperDOI"].strip() if isinstance(i, dict) else i for i in items]
        methods = tuple(a.methods.split(","))
        results = []
        for n, doi in enumerate(dois, 1):
            for wiki in a.wikis.split(","):
                results.append(discover(client, wiki, doi, methods))
            print(f"{n}/{len(dois)} {doi}", file=sys.stderr, flush=True)
        for r in results:
            for o in r["observations"]:
                o.pop("content", None)
        write(a.out, {"run_at": now(), "user_agent": USER_AGENT, "results": results, "request_log": client.log})
    elif a.cmd == "first-revision":
        res = first_revision_where(client, a.wiki, a.title, a.doi, a.what)
        write(a.out, {"wiki": a.wiki, "title": a.title, "doi": a.doi, "run_at": now(), **res})
    elif a.cmd == "crosswiki":
        rows = crosswiki(client, json.loads(a.discovery.read_text(encoding="utf-8")), a.src, a.dst)
        write(a.out, {"run_at": now(), "src": a.src, "dst": a.dst, "rows": rows})
    elif a.cmd == "absence-check":
        checks = [absence_check(client, a.wiki, r, a.needles, a.context) for r in a.revids]
        write(a.out, {"run_at": now(), "checks": checks})
    elif a.cmd == "render-check":
        checks = [render_check(client, a.wiki, r, a.doi) for r in a.revids]
        write(a.out, {"run_at": now(), "user_agent": USER_AGENT, "checks": checks})
    elif a.cmd == "api-query":
        params = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5"}
        params.update(dict(kv.split("=", 1) for kv in a.param))
        if params["action"] != "query":
            sys.exit("api-query only runs action=query")
        res = client.get(f"https://{a.host}/w/api.php", params)
        write(a.out, {k: res[k] for k in ("url", "status", "retrieved_at", "body")})
    elif a.cmd == "verify":
        result = verify_manifest(client, json.loads(a.manifest.read_text(encoding="utf-8")))
        result["manifest_sha256"] = hashlib.sha256(a.manifest.read_bytes()).hexdigest()
        result["refresh"] = a.refresh
        for prob in result["problems"]:
            print("MISMATCH", prob)
        print(
            f"verify: {result['checks']} checks of {result['distinct_revisions']} revisions and "
            f"{result['distinct_crossref_works']} Crossref works, {len(result['problems'])} problem(s)"
        )
        if a.out:
            write(a.out, result)
        return 1 if result["problems"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
