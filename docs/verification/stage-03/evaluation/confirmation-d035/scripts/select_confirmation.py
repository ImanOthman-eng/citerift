"""Draw the confirmation-campaign frame (AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 4, which keeps the
procedure of AMENDMENT_2026-11-02_CONFIRMATION.md sections 3 and 9). This campaign has no warning challenge: STRATA
is empty, so no ``list=embeddedin`` request is made.

Usage (from the repository root): python select_confirmation.py EXPOSURE_SET_JSON CAMPAIGN_DIR

Holdout frame, per wiki: the procedure of the frozen ``select_sample.py``, with this campaign's bounds.

1. ``list=random`` (namespace 0, non-redirects, 500 titles) gives a batch.
2. ``prop=extlinks`` with ``elquery=doi.org`` (https), 50 page ids per request, keeps the articles whose rendered
   output links to doi.org.
3. Batches are drawn until the eligible articles reach the maximum (ar 48, en 32) or MAX_BATCHES were drawn.
4. Exposed page ids and titles are never eligible.
5. Eligible articles are ordered by the SHA-256 of ``SALT|<wiki>|<page id>``. Positions 1 to INITIAL are the
   initial holdout; the following positions, in blocks of BLOCK, are the ordered reserve.

Warning challenge, per wiki and stratum (retraction, concern, correction):

- the articles in namespace 0 that transclude the stratum's marker templates (``list=embeddedin``, at most
  MAX_CONTINUE pages of 500);
- not exposed, and not drawn into the holdout frame;
- an article is placed in the first stratum it belongs to;
- ordered by the SHA-256 of ``CHALLENGE_SALT|<wiki>|<stratum>|<page id>``; the first CHALLENGE_PER_STRATUM are taken.

Every request goes through the production client (fixed hosts, ``maxlag``, Retry-After, the project network gate).
Before each request, the campaign journal (CAMPAIGN_DIR/capture/captures.jsonl, shared with the capture driver)
must leave room for one worst-case run within the campaign ceilings. Each request is journalled there, and every
accepted body is kept by SHA-256. No article content is read. The draw holds the capture driver's lock, so no
capture runs meanwhile.

Waits and failures (review R6, RR-2):

- a request deferred by a server's Retry-After (through the network gate) is not a failed batch: the draw waits
  until ``not_before`` plus 1 s and sends it again; a wait over DRAW_MAX_WAIT_S stops the draw without writing
  SELECTION.json;
- a retryable failure is sent once more; a failure that is not retryable, a second failure, or a Retry-After the
  client could not read, fails that request, and the draw records it.

The draw is made once (``list=random`` cannot be repeated). If it is stopped before SELECTION.json is written, the
next draw starts afresh: its request numbers continue after the earlier ones, and SELECTION.json lists the earlier
requests (RR-13), so the restart is reported, never hidden.

Outputs: CAMPAIGN_DIR/selection/SELECTION.json and CAMPAIGN_DIR/selection/artifacts/.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
import campaign_capture as cc  # noqa: E402

SALT = "citerift-stage03-confirmation-d035-2026-11-03-v1"
CHALLENGE_SALT = "citerift-stage03-warning-challenge-d035-2026-11-03-v1"  # unused: no challenge
INITIAL = {"ar": 24, "en": 16}
MAXIMUM = {"ar": 48, "en": 32}
BLOCK = 4
MAX_BATCHES = {"ar": 6, "en": 4}
MAX_CONTINUE = 20
EMBEDDED_PAGES = 4
CHALLENGE_PER_STRATUM = 4
# No warning challenge in this campaign (AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 3).
STRATA: dict[str, list[tuple[str, list[str]]]] = {"ar": [], "en": []}
HOSTS = {"ar": "ar.wikipedia.org", "en": "en.wikipedia.org"}
DRAW_MAX_WAIT_S = 3600.0
DRAW_TRIES = 2
DRAW_MAX_DEFERRALS = 5

Get = Callable[[str], Any]


def api(wiki: str, params: dict[str, str]) -> str:
    base = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5"}
    return f"https://{HOSTS[wiki]}/w/api.php?" + urllib.parse.urlencode({**base, **params})


def order(salt: str, *parts: object) -> str:
    return hashlib.sha256("|".join([salt, *map(str, parts)]).encode()).hexdigest()


def _live_fetch(url: str) -> Any:
    from citerift.wiki.fetch import Fetcher, FetchPolicy  # noqa: PLC0415 - live path only

    return Fetcher(FetchPolicy()).get(url, expect="json")


class LiveGet:
    """One journalled, ceiling-checked request through the production client, sent again after a server-requested
    wait or once after a retryable failure."""

    def __init__(
        self,
        campaign: Path,
        fetch: Callable[[str], Any] = _live_fetch,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.capture = campaign / "capture"
        self.artifacts = campaign / "selection" / "artifacts"
        self.capture.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.fetch, self.clock, self.sleep = fetch, clock, sleep
        self.requests: list[dict[str, Any]] = []
        pat = re.compile(r"selection/request-([0-9]+)\Z")
        self.earlier = sorted(
            {e["key"] for e in cc._journal(self.capture) if pat.match(str(e.get("key")))}  # an interrupted draw
        )
        self.number = max((int(pat.match(k).group(1)) for k in self.earlier), default=0)  # type: ignore[union-attr]

    def __call__(self, url: str) -> Any:
        tries = deferrals = 0
        while True:
            entry = self._once(url)
            if entry["code"] is None:
                return entry.pop("_json")
            if entry["code"] == "DEFERRED_RETRY_AFTER":
                deferrals += 1
                when = cc._parse_time(entry["not_before"])
                wait = (when + cc.NOT_BEFORE_MARGIN_S - self.clock()) if when is not None else None
                if wait is None or wait > DRAW_MAX_WAIT_S or deferrals > DRAW_MAX_DEFERRALS:
                    raise SystemExit(
                        f"draw stopped: a server asked to wait until {entry['not_before']}; SELECTION.json is not"
                        " written, and a later draw starts afresh and lists these requests"
                    )
                self.sleep(max(0.0, wait))
                continue
            tries += 1
            problem = any(a.get("retry_after_problem") for a in entry["attempts"])
            if problem or entry["code"] not in cc.RETRYABLE or tries >= DRAW_TRIES:
                return None

    def _once(self, url: str) -> dict[str, Any]:
        log = self.capture / "captures.jsonl"
        attempts, accepted = cc.used(cc._journal(self.capture))
        if (
            attempts + cc.RUN_WORST_ATTEMPTS > cc.MAX_HTTP_ATTEMPTS
            or accepted + cc.RUN_WORST_BYTES > cc.MAX_ACCEPTED_BYTES
        ):
            raise SystemExit(f"campaign ceiling: draw stopped before a request ({attempts} attempts, {accepted} bytes)")
        if self.clock() >= cc.ACQUISITION_END:
            raise SystemExit("acquisition time limit: draw stopped before a request")
        self.number += 1
        key = f"selection/request-{self.number:04d}"
        now = datetime.now(UTC).isoformat(timespec="seconds")
        cc._append(log, {"event": "start", "key": key, "run": 1, "at": now, "url": url})
        answer = self.fetch(url)
        entry: dict[str, Any] = {
            "url": url,
            "code": answer.code,
            "not_before": answer.not_before,
            "attempts": [a.to_json() for a in answer.attempts],
        }
        if answer.body is not None and answer.code is None:
            digest = hashlib.sha256(answer.body).hexdigest()
            (self.artifacts / digest).write_bytes(answer.body)
            entry["body_sha256"] = digest
        cc._append(
            log,
            {
                "event": "end",
                "key": key,
                "run": 1,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "exit": 0 if answer.code is None else 1,
                "stdout": {
                    "status": "complete" if answer.code is None else "failed",
                    "capture": {"attempts": entry["attempts"]},
                },
            },
        )
        self.requests.append(entry)
        print(json.dumps({"url": url, "code": answer.code}, ensure_ascii=False), file=sys.stderr, flush=True)
        return {**entry, "_json": answer.json if answer.code is None else None}


def draw(get: Get, wiki: str, ex_ids: set[int], ex_titles: set[str]) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    eligible: dict[int, str] = {}
    failures: list[str] = []
    excluded: list[int] = []
    while len(eligible) < MAXIMUM[wiki] and len(batches) < MAX_BATCHES[wiki]:
        data = get(api(wiki, {"list": "random", "rnnamespace": "0", "rnfilterredir": "nonredirects", "rnlimit": "500"}))
        if data is None:
            failures.append(f"batch {len(batches) + 1}: list=random failed")
            batches.append({"random": [], "with_doi_link": []})
            continue
        pages = [(int(p["id"]), p["title"]) for p in data["query"]["random"]]
        with_doi: list[int] = []
        for i in range(0, len(pages), 50):
            params = {
                "prop": "extlinks",
                "pageids": "|".join(str(pid) for pid, _ in pages[i : i + 50]),
                "elquery": "doi.org",
                "elprotocol": "https",
                "ellimit": "max",
            }
            for _ in range(MAX_CONTINUE):
                links = get(api(wiki, params))
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
            if pid in ex_ids or titles[pid] in ex_titles:
                excluded.append(pid)
            else:
                eligible[pid] = titles[pid]
    ordered = sorted(eligible, key=lambda pid: order(SALT, wiki, pid))
    rows = [{"position": i + 1, "page_id": pid, "title": eligible[pid]} for i, pid in enumerate(ordered)]
    rows = rows[: MAXIMUM[wiki]]
    initial = rows[: INITIAL[wiki]]
    rest = rows[INITIAL[wiki] :]
    return {
        "batches": batches,
        "failures": failures,
        "excluded_as_exposed": sorted(set(excluded)),
        "eligible": len(eligible),
        "eligible_order": [{"page_id": pid, "title": eligible[pid]} for pid in ordered],
        "initial": initial,
        "reserve_blocks": [rest[i : i + BLOCK] for i in range(0, len(rest), BLOCK)],
    }


def challenge(get: Get, wiki: str, ex_ids: set[int], ex_titles: set[str]) -> dict[str, Any]:
    strata: dict[str, Any] = {}
    placed: set[int] = set()
    for stratum, templates in STRATA[wiki]:
        found: dict[int, str] = {}
        failures: list[str] = []
        for template in templates:
            params = {"list": "embeddedin", "eititle": template, "einamespace": "0", "eilimit": "500"}
            for _ in range(EMBEDDED_PAGES):
                data = get(api(wiki, params))
                if data is None:
                    failures.append(f"embeddedin {template} failed")
                    break
                for p in data["query"]["embeddedin"]:
                    pid, title = int(p["pageid"]), p["title"]
                    if pid not in ex_ids and title not in ex_titles and pid not in placed:
                        found[pid] = title
                if "continue" not in data:
                    break
                params = {**params, **{k: str(v) for k, v in data["continue"].items()}}
            else:
                failures.append(f"embeddedin {template}: more than {EMBEDDED_PAGES} pages, the rest not read")
        ordered = sorted(found, key=lambda pid: order(CHALLENGE_SALT, wiki, stratum, pid))
        chosen = ordered[:CHALLENGE_PER_STRATUM]
        placed.update(found)
        strata[stratum] = {
            "templates": templates,
            "candidates": len(found),
            "failures": failures,
            "selected": [{"page_id": pid, "title": found[pid]} for pid in chosen],
        }
    return strata


def select(get: Get, exposure: dict[str, Any]) -> dict[str, Any]:
    ex_ids = set(exposure["page_ids"])
    ex_titles = set(exposure["titles"])
    result: dict[str, Any] = {
        "procedure": __doc__,
        "salt": SALT,
        "challenge_salt": CHALLENGE_SALT,
        "bounds": {"initial": INITIAL, "maximum": MAXIMUM, "block": BLOCK, "max_batches": MAX_BATCHES},
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "frame": {},
        "challenge": {},
    }
    for wiki in ("ar", "en"):
        result["frame"][wiki] = draw(get, wiki, ex_ids, ex_titles)
    for wiki in ("ar", "en"):
        drawn = {r["page_id"] for r in result["frame"][wiki]["eligible_order"]}
        drawn |= {r["page_id"] for b in result["frame"][wiki]["batches"] for r in b["random"]}
        result["challenge"][wiki] = challenge(get, wiki, ex_ids | drawn, ex_titles)
    result["finished_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return result


def plan(selection: dict[str, Any], blocks: dict[str, int], with_challenge: bool) -> dict[str, Any]:
    """The capture plan: the initial holdout, the first ``blocks[wiki]`` reserve blocks, and the challenge."""
    arts: list[dict[str, Any]] = []
    for wiki in ("ar", "en"):
        f = selection["frame"][wiki]
        arts += [{"split": "holdout", "wiki": wiki, "page_id": r["page_id"]} for r in f["initial"]]
    for wiki in ("ar", "en"):
        for n, block in enumerate(selection["frame"][wiki]["reserve_blocks"][: blocks.get(wiki, 0)], start=1):
            arts += [{"split": f"reserve{n}", "wiki": wiki, "page_id": r["page_id"]} for r in block]
    if with_challenge:
        for wiki in ("ar", "en"):
            for stratum in selection["challenge"][wiki].values():
                arts += [{"split": "challenge", "wiki": wiki, "page_id": r["page_id"]} for r in stratum["selected"]]
    return {"campaign": "confirmation-d035", "articles": arts}


def main() -> int:
    exposure = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    campaign = Path(sys.argv[2]).resolve()
    out = campaign / "selection" / "SELECTION.json"
    if out.exists():
        raise SystemExit(f"{out} exists; the draw is made once")
    (campaign / "capture").mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(
        campaign / "capture" / "driver.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("a capture driver holds the campaign journal") from None
        cc.repair_journal(campaign / "capture")
        get = LiveGet(campaign)
        result = select(get, exposure)
        result["exposure_set_sha256"] = hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
        result["earlier_interrupted_draw_requests"] = get.earlier
        result["requests"] = get.requests
        cc._write_atomic(out, result)  # a kill never leaves a partial SELECTION.json (review R7, RF7-8)
    finally:
        os.close(lock_fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
