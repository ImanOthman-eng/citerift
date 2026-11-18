"""Stage 04 Step 13: acquisition of the drawn articles and the expansion decision (PREREGISTRATION.md sections 4, 5).

Nothing here may run for the final sample before the owner has accepted the committed pre-registration.

**Campaign directory** (``C``): ``SEED.json`` and ``DRAW.json`` (``s13_draw.py``), ``ACQUISITION.json`` (this tool's
append-only log), ``bundles/<wiki>-<page_id>/`` (Stage 03 capture bundles), ``packets/<name>.json`` and
``extractions/<name>.json`` (``s13_packets.py``), ``rounds/<round>/`` (the packet list, label files and lock of one
annotation round), ``LOCK.json`` (all rounds), ``run/`` (``s13_run.py``) and ``SCORES.json`` (``s13_score.py``).

**Rounds.** ``primary`` acquires the primary positions of both languages. ``<wiki>-expansion-<k>`` acquires the
k-th expansion block of one language. A round is annotated and locked before the next round is decided.

**Acquisition of one position** (``PARAMETERS.json`` ``acquisition``): the current revision of the page id is
captured by the accepted Stage 03 capture (``citerift-wiki capture --page-id``, render on, no redirect following).
Exit 0 or 6 gives a bundle; exit 4 or 8 (unavailable, deferred) is retried twice, 300 s apart; anything else, or a
still-transient answer after the retries, is an acquisition failure. A captured bundle whose Stage 03 extraction is
neither ``complete`` nor ``partial`` is an acquisition failure too, and so is a captured page whose page id differs
from the drawn one or whose current (wiki, page id) or title meets the frame exclusion rule (exposure manifest or
listed tier: the manifest's "re-check drawn articles on capture identity"). Every position whose capture was started
counts as one attempt toward the ceiling of 200 (both languages together); retries of the same position do not.

**Replacement.** A failed primary position is replaced by the next unused ``reserve`` position of the same language
and stratum, in draw order; when that stratum's reserves are used up, it is not replaced. Expansion positions are not
replaced. Nothing else ever replaces an article: not its content, its labels or any engine output.

**Expansion** (``status``; engine-independent): after a language's rounds are locked, the language expands by its
next block when either count is short of ``PARAMETERS.json`` ``sampling.expansion``:

- identifier-reached truth-positive units: locked final labels with kind ``work_citation``, same_work not ``no``, and
  a record judged ``cited_work`` that an identifier of the unit reached as the original paper (at least 40);
- negative-proxy units: units with an eligible candidate-role identifier (``s13_baseline.eligible_keys``) none of
  whose keys is an identifier of any Retraction Watch record (at least 75).

Expansion stops when both are met, when the language's planned positions are used up, or at the ceiling.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s13_baseline as BL
import s13_frame as FR
import s13_packets as PK
from s13_common import EVALUATION, LANGUAGES, file_sha256, norm_title, read_json, write_json

FORMAT = "citerift-stage04-eval-acquisition/1"


def name_of(pos: dict[str, Any]) -> str:
    return f"{pos['wiki']}-{pos['page_id']}"


def load_log(campaign: Path) -> dict[str, Any]:
    path = campaign / "ACQUISITION.json"
    if path.exists():
        doc = read_json(path)
        if doc.get("format") != FORMAT:
            raise ValueError("ACQUISITION.json is not of this format")
        return doc
    return {"format": FORMAT, "attempts": []}


def attempts_used(log: dict[str, Any]) -> int:
    return len(log["attempts"])


def used(log: dict[str, Any]) -> set[tuple[str, int]]:
    return {(a["wiki"], int(a["page_id"])) for a in log["attempts"]}


def next_reserve(plan: dict[str, Any], log: dict[str, Any], wiki: str, stratum: str) -> dict[str, Any] | None:
    taken = used(log)
    for pos in plan[wiki]["positions"]:
        if pos["block"] == "reserve" and pos["stratum"] == stratum and (wiki, int(pos["page_id"])) not in taken:
            return pos
    return None


def round_positions(plan: dict[str, Any], round_name: str) -> list[dict[str, Any]]:
    if round_name == "primary":
        return [p for w in LANGUAGES for p in plan[w]["positions"] if p["block"] == "primary"]
    wiki, _, block = round_name.partition("-")
    if wiki not in LANGUAGES or not block.startswith("expansion-"):
        raise ValueError(f"unknown round {round_name!r}")
    return [p for p in plan[wiki]["positions"] if p["block"] == block]


CaptureFn = Callable[[dict[str, Any], Path], tuple[int, str]]
PacketFn = Callable[[Path], tuple[dict[str, Any], dict[str, Any]]]
ExcludeFn = Callable[[str, int, str], list[str]]
LISTED_TIER = EVALUATION / "frame" / "listed_tier.json"


def exposure_check() -> ExcludeFn:
    """The frame exclusion rule (``s13_frame.exclusion``) applied to a captured page's current id and title."""
    manifest = read_json(FR.EXPOSURE)
    if file_sha256(LISTED_TIER) != manifest["listed"]["output_sha256"]:
        raise ValueError("the committed listed tier is not the one the exposure manifest recorded")
    listed = read_json(LISTED_TIER)
    exp_ids, exp_titles = FR.exposure_keys(manifest)
    listed_ids = {int(i) for i in listed["page_ids"]}
    listed_titles = {w: {norm_title(w, t) for t in listed["titles"]} for w in LANGUAGES}

    exclude_listed = bool(read_json(EVALUATION / "PARAMETERS.json")["frame"]["exclude_listed_tier"])

    def excluded(wiki: str, page_id: int, title: str) -> list[str]:
        page = {"page_id": page_id, "title": title}
        return FR.applying(FR.exclusion(wiki, page, exp_ids, exp_titles, listed_ids, listed_titles), exclude_listed)

    return excluded


def acquire_one(
    pos: dict[str, Any],
    campaign: Path,
    params: dict[str, Any],
    capture: CaptureFn,
    make_packet: PacketFn,
    sleep: Callable[[float], None] = time.sleep,
    excluded: ExcludeFn | None = None,
) -> dict[str, Any]:
    """Capture and extract one position; the attempt record (never raises for an acquisition failure)."""
    acq = params["acquisition"]
    name = name_of(pos)
    out = campaign / "bundles" / name
    tries: list[dict[str, Any]] = []
    for k in range(acq["transient_retries"] + 1):
        if out.exists():
            (campaign / "failed").mkdir(parents=True, exist_ok=True)
            shutil.move(str(out), str(campaign / "failed" / f"{name}.try{k}"))
        code, detail = capture(pos, out)
        tries.append({"exit": code, "detail": detail[-500:], "at": datetime.now(UTC).isoformat()})
        if code not in acq["transient_capture_exit_codes"] or k == acq["transient_retries"]:
            break
        sleep(acq["transient_retry_wait_seconds"])
    rec: dict[str, Any] = {**{k: pos[k] for k in ("wiki", "page_id", "title", "stratum", "block")}, "tries": tries}
    if tries[-1]["exit"] not in acq["acquired_capture_exit_codes"] or not out.is_dir():
        return {**rec, "status": "failed", "failure": "CAPTURE_FAILED"}
    packet, extraction = make_packet(out)
    if packet["extraction_status"] not in acq["acquired_extraction_status"]:
        return {
            **rec,
            "status": "failed",
            "failure": "EXTRACTION_FAILED",
            "extraction_status": packet["extraction_status"],
        }
    art = packet["article"]
    if int(art["page_id"]) != int(pos["page_id"]):
        return {**rec, "status": "failed", "failure": "PAGE_ID_MISMATCH", "captured_page_id": art["page_id"]}
    reasons = excluded(pos["wiki"], int(art["page_id"]), art["title"]) if excluded is not None else []
    if reasons:
        return {
            **rec,
            "status": "failed",
            "failure": "EXPOSED_AT_CAPTURE",
            "reasons": reasons,
            "captured_title": art["title"],
        }
    write_json(campaign / "packets" / f"{name}.json", packet)
    write_json(campaign / "extractions" / f"{name}.json", extraction)
    return {
        **rec,
        "status": "acquired",
        "name": name,
        "revision_id": packet["article"]["revision_id"],
        "extraction_digest": packet["extraction_digest"],
        "items": len(packet["items"] or []),
    }


def acquire_round(
    campaign: Path,
    round_name: str,
    params: dict[str, Any],
    capture: CaptureFn,
    make_packet: PacketFn,
    sleep: Callable[[float], None] = time.sleep,
    excluded: ExcludeFn | None = None,
) -> dict[str, Any]:
    """Acquire every position of a round, replacing failed primary positions by reserves; append to the log."""
    plan = read_json(campaign / "DRAW.json")["plan"]
    log = load_log(campaign)
    if any(a.get("round") == round_name for a in log["attempts"]):
        raise ValueError(f"round {round_name} was already acquired")
    ceiling = params["sampling"]["attempt_ceiling"]
    queue = list(round_positions(plan, round_name))
    while queue:
        pos = queue.pop(0)
        if attempts_used(log) >= ceiling:
            log.setdefault("ceiling_reached", []).append({"round": round_name, "skipped": name_of(pos)})
            break
        rec = acquire_one(pos, campaign, params, capture, make_packet, sleep, excluded)
        rec["round"] = round_name
        rec["attempt"] = attempts_used(log) + 1
        log["attempts"].append(rec)
        write_json(campaign / "ACQUISITION.json", log)
        if rec["status"] == "failed" and pos["block"] == "primary":
            rep = next_reserve(plan, log, pos["wiki"], pos["stratum"])
            queue_names = {name_of(q) for q in queue}
            if rep is not None and name_of(rep) not in queue_names:
                rec["replaced_by"] = name_of(rep)
                queue.insert(0, rep)
        sleep(params["acquisition"]["pause_between_captures_seconds"])
    acquired = [a["name"] for a in log["attempts"] if a.get("round") == round_name and a["status"] == "acquired"]
    write_json(campaign / "rounds" / round_name / "ARTICLES.json", {"round": round_name, "articles": acquired})
    write_json(campaign / "ACQUISITION.json", log)
    return log


def negative_proxy_units(extraction: dict[str, Any], conn: sqlite3.Connection) -> int:
    return sum(
        1 for keys in BL.eligible_keys(extraction).values() if not any(BL.in_rw_fields(conn, s, n) for s, n in keys)
    )


def id_reached_truth_positive(item: dict[str, Any], label: dict[str, Any]) -> bool:
    if label["kind"] != "work_citation" or label["same_work"] == "no":
        return False
    for rec in item["records"]:
        if label["records"].get(rec["ref"]) == "cited_work" and any(
            r.endswith(" as original") for r in rec["reached_by"]
        ):
            return True
    return False


def status(campaign: Path, conn: sqlite3.Connection, params: dict[str, Any]) -> dict[str, Any]:
    """Per language: the two expansion counts over every locked round, and the decision for the next round."""
    exp = params["sampling"]["expansion"]
    log = load_log(campaign)
    plan = read_json(campaign / "DRAW.json")["plan"]
    out: dict[str, Any] = {"attempts_used": attempts_used(log), "ceiling": params["sampling"]["attempt_ceiling"]}
    for wiki in LANGUAGES:
        tp = neg = articles = 0
        locked_rounds = []
        for rdir in sorted((campaign / "rounds").glob("*")):
            lock_path = rdir / "LOCK.json"
            if not lock_path.exists():
                continue
            locked_rounds.append(rdir.name)
            final = read_json(lock_path)["final"]
            for name in read_json(rdir / "ARTICLES.json")["articles"]:
                if not name.startswith(f"{wiki}-"):
                    continue
                articles += 1
                packet = read_json(campaign / "packets" / f"{name}.json")
                for it in packet["items"] or []:
                    if it["item_id"] in final and id_reached_truth_positive(it, final[it["item_id"]]):
                        tp += 1
                neg += negative_proxy_units(read_json(campaign / "extractions" / f"{name}.json"), conn)
        done_blocks = {a["block"] for a in log["attempts"] if a["wiki"] == wiki}
        next_block = next(
            (f"expansion-{k}" for k in range(1, exp["max_blocks"] + 1) if f"expansion-{k}" not in done_blocks), None
        )
        has_positions = next_block is not None and any(p["block"] == next_block for p in plan[wiki]["positions"])
        short = tp < exp["min_identifier_reached_truth_positive_units"] or neg < exp["min_negative_proxy_units"]
        if not short:
            decision = "stop: both counts met"
        elif not has_positions:
            decision = "stop: no planned position left"
        elif out["attempts_used"] >= out["ceiling"]:
            decision = "stop: attempt ceiling reached"
        else:
            decision = f"expand: {wiki}-{next_block}"
        out[wiki] = {
            "locked_rounds": locked_rounds,
            "articles": articles,
            "identifier_reached_truth_positive_units": tp,
            "negative_proxy_units": neg,
            "decision": decision,
        }
    return out


def cli_capture(pos: dict[str, Any], out: Path) -> tuple[int, str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "citerift.wiki.cli",
        "capture",
        "--wiki",
        pos["wiki"],
        "--page-id",
        str(pos["page_id"]),
        "--out",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    return res.returncode, (res.stderr or "") + (res.stdout or "")[-300:]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 acquisition")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("acquire")
    r.add_argument("--campaign", type=Path, required=True)
    r.add_argument("--round", required=True)
    r.add_argument("--index", type=Path, required=True)
    s = sub.add_parser("status")
    s.add_argument("--campaign", type=Path, required=True)
    s.add_argument("--index", type=Path, required=True)
    a = ap.parse_args(argv)
    params = read_json(EVALUATION / "PARAMETERS.json")
    if a.cmd == "acquire":
        log = acquire_round(
            a.campaign, a.round, params, cli_capture, lambda b: PK.packet(b, a.index), excluded=exposure_check()
        )
        print(
            a.round,
            sum(1 for x in log["attempts"] if x.get("round") == a.round and x["status"] == "acquired"),
            "acquired;",
            attempts_used(log),
            "attempts used",
        )
        return 0
    with sqlite3.connect(f"file:{a.index}?mode=ro", uri=True) as conn:
        st = status(a.campaign, conn, params)
    write_json(a.campaign / "STATUS.json", st)
    print(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
