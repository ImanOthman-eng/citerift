"""Stage 03 evaluation: draw the holdout, reserve and confirmation articles and the observed challenge set.

Usage: python select_sample.py OUT_DIR

Procedure (FROZEN_PROTOCOL.md section 3), per wiki (ar, en):
  1. ``list=random`` (namespace 0, non-redirects, 500 titles) gives a batch of random articles.
  2. ``prop=extlinks`` with ``elquery=doi.org`` (https), 50 page ids per request, keeps the articles whose
     current rendered output links to doi.org at least once (the population: articles that cite at least one
     work by DOI). ``elquery`` matches by link prefix, so this is a filter, not a count.
  3. Batches are drawn until at least NEEDED eligible articles exist or MAX_BATCHES batches were drawn.
  4. Eligible articles not in the development split are ordered by SHA-256 of
     ``citerift-stage03-holdout-v1|<wiki>|<page id>``; positions 1-10 are the holdout, 11-16 the reserve
     (used in order only if the locked annotations fall short of the minimum denominators), 17-22 the
     confirmation set (used only after a material repair that follows exposure of holdout predictions).
  5. Challenge (observed): articles transcluding the retraction-marker templates (``list=embeddedin``,
     namespace 0), not in any other split, ordered by SHA-256 of ``citerift-stage03-challenge-v1|<wiki>|<page id>``;
     the first CHALLENGE per wiki.

Every request goes through the production client (citerift.wiki.fetch: fixed hosts, maxlag, Retry-After, the
project network gate). Every attempt and every accepted body (by SHA-256) is kept. Revisions are pinned later by
``citerift-wiki capture --page-id``. No article content is read here.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.wiki.fetch import HOSTS, Fetcher, FetchPolicy

NEEDED = 22
MAX_BATCHES = 4
MAX_CONTINUE = 20
CHALLENGE = 3
MARKER_TEMPLATES = {"en": ["Template:Retracted"], "ar": ["قالب:مصدر مسحوب", "قالب:Retracted"]}
DEV = Path(__file__).resolve().parents[2] / "calibration"


def api(wiki: str, params: dict[str, str]) -> str:
    base = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5"}
    return f"https://{HOSTS[wiki]}/w/api.php?" + urllib.parse.urlencode({**base, **params})


class Run:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.requests: list[dict[str, Any]] = []
        (out / "artifacts").mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> Any:
        answer = Fetcher(FetchPolicy()).get(url, expect="json")
        entry: dict[str, Any] = {
            "url": url,
            "code": answer.code,
            "not_before": answer.not_before,
            "attempts": [a.to_json() for a in answer.attempts],
        }
        if answer.body is not None and answer.code is None:
            digest = hashlib.sha256(answer.body).hexdigest()
            (self.out / "artifacts" / digest).write_bytes(answer.body)
            entry["body_sha256"] = digest
        self.requests.append(entry)
        print(json.dumps({k: entry[k] for k in ("url", "code")}, ensure_ascii=False), file=sys.stderr)
        return answer.json if answer.code is None else None


def dev_pages() -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {"ar": set(), "en": set()}
    for name in ("dev_selection.json", "dev_selection_supplement.json"):
        for art in json.loads((DEV / name).read_text(encoding="utf-8")).get("articles", []):
            seen[art["wiki"]].add(art["title"])
    return seen


def order_key(salt: str, wiki: str, page_id: int) -> str:
    return hashlib.sha256(f"{salt}|{wiki}|{page_id}".encode()).hexdigest()


def draw(run: Run, wiki: str, excluded_titles: set[str]) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    eligible: dict[int, str] = {}
    failures: list[str] = []
    while len(eligible) < NEEDED and len(batches) < MAX_BATCHES:
        params = {"list": "random", "rnnamespace": "0", "rnfilterredir": "nonredirects", "rnlimit": "500"}
        data = run.get(api(wiki, params))
        if data is None:
            failures.append(f"batch {len(batches) + 1}: list=random failed")
            batches.append({"random": [], "with_doi_link": []})
            continue
        pages = [(int(p["id"]), p["title"]) for p in data["query"]["random"]]
        with_doi: list[int] = []
        for i in range(0, len(pages), 50):
            ids = "|".join(str(pid) for pid, _ in pages[i : i + 50])
            params = {"prop": "extlinks", "pageids": ids, "elquery": "doi.org", "elprotocol": "https", "ellimit": "max"}
            for _ in range(MAX_CONTINUE):  # a page with many DOI links can push the others into a continuation
                links = run.get(api(wiki, params))
                if links is None:
                    failures.append(f"batch {len(batches) + 1}: extlinks for ids {pages[i][0]}.. failed")
                    break
                with_doi += [int(p["pageid"]) for p in links["query"]["pages"] if p.get("extlinks")]
                if "continue" not in links:
                    break
                params = {**params, **{k: str(v) for k, v in links["continue"].items()}}
            else:
                failures.append(f"batch {len(batches) + 1}: extlinks for ids {pages[i][0]}.. still continued")
        with_doi = sorted(set(with_doi))
        titles = dict(pages)
        batches.append({"random": [{"page_id": pid, "title": t} for pid, t in pages], "with_doi_link": with_doi})
        for pid in with_doi:
            if titles[pid] not in excluded_titles:
                eligible[pid] = titles[pid]
    ordered = sorted(eligible, key=lambda pid: order_key("citerift-stage03-holdout-v1", wiki, pid))
    rows = [{"page_id": pid, "title": eligible[pid]} for pid in ordered]
    return {
        "batches": batches,
        "failures": failures,
        "eligible": len(eligible),
        "holdout": rows[:10],
        "reserve": rows[10:16],
        "confirmation": rows[16:22],
        "unused": rows[22:],
    }


def challenge(run: Run, wiki: str, taken: set[int], excluded_titles: set[str]) -> dict[str, Any]:
    found: dict[int, str] = {}
    for template in MARKER_TEMPLATES[wiki]:
        data = run.get(api(wiki, {"list": "embeddedin", "eititle": template, "einamespace": "0", "eilimit": "500"}))
        if data is None:
            continue
        for p in data["query"]["embeddedin"]:
            if int(p["pageid"]) not in taken and p["title"] not in excluded_titles:
                found[int(p["pageid"])] = p["title"]
    ordered = sorted(found, key=lambda pid: order_key("citerift-stage03-challenge-v1", wiki, pid))
    return {
        "templates": MARKER_TEMPLATES[wiki],
        "candidates": len(found),
        "selected": [{"page_id": pid, "title": found[pid]} for pid in ordered[:CHALLENGE]],
    }


def main() -> int:
    out = Path(sys.argv[1])
    run = Run(out)
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    dev = dev_pages()
    result: dict[str, Any] = {"started_at": started, "procedure": __doc__, "splits": {}, "challenge": {}}
    for wiki in ("ar", "en"):
        split = draw(run, wiki, dev[wiki])
        result["splits"][wiki] = split
        taken = {r["page_id"] for key in ("holdout", "reserve", "confirmation", "unused") for r in split[key]}
        result["challenge"][wiki] = challenge(run, wiki, taken, dev[wiki])
    result["finished_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["requests"] = run.requests
    (out / "selection.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
