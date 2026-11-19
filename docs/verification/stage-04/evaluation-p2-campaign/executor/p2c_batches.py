"""Stage 04 Step 14 under P2, executor glue: annotation batches, work directories, collection (P2 section 7).

Not pre-registered tooling and not part of the evaluation logic: it only copies files and records hashes. It never
reads, decides or changes a label's content; validation, disagreements, adjudication requirements and the lock are the
pre-registered ``p2_labels.py``.

- ``annotate``: per language, the round's articles with at least one item, in name order, in batches of at most
  ``PARAMETERS.json`` ``annotation.max_articles_per_instance``; for each batch, one work directory per role (A, B)
  holding only the guide, the batch's packets under ``items/`` and an empty ``out/`` (``ANNOTATOR_BRIEF.md``).
- ``adjudicate``: after A and B are combined, the disagreed items (``p2_labels.disagreements``) grouped by article,
  per language, in batches of at most six articles; one work directory per batch holding the guide, the batch's
  packets, ``disputed/<article>.json`` (item id and both labels) and an empty ``out/`` (``ADJUDICATOR_BRIEF.md``).
- ``collect``: copies each instance's ``out/labels-<instance>.json`` into ``rounds/<round>/labels/<role>/``.
- ``empty-adj``: the round's ADJ role file when A and B disagree on no item (no instance, no label).
- ``record``: records an instance's platform metadata and copies its transcript into ``rounds/<round>/transcripts/``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
EVALUATION = REPO / "docs/verification/stage-04/evaluation-p2"
sys.path.insert(0, str(EVALUATION / "tools"))

import p2_labels as LB  # noqa: E402
from p2_common import LANGUAGES, file_sha256, read_json, write_json  # noqa: E402

GUIDE = EVALUATION / "ANNOTATION_GUIDE.md"


def _tag(round_name: str) -> str:
    return "p" if round_name == "primary" else "e" + round_name.rsplit("-", 1)[1]


def _chunks(names: list[str], size: int) -> list[list[str]]:
    return [names[i : i + size] for i in range(0, len(names), size)]


def _work_dir(work: Path, instance: str, packets: list[Path]) -> dict[str, Any]:
    d = work / instance
    if d.exists():
        raise SystemExit(f"{d} exists: work directories are never reused")
    (d / "items").mkdir(parents=True)
    (d / "out").mkdir()
    shutil.copyfile(GUIDE, d / "ANNOTATION_GUIDE.md")
    for p in packets:
        shutil.copyfile(p, d / "items" / p.name)
    return {
        "instance": instance,
        "work": str(d),
        "guide_sha256": file_sha256(d / "ANNOTATION_GUIDE.md"),
        "items": {p.name: file_sha256(d / "items" / p.name) for p in packets},
    }


def annotate(campaign: Path, round_name: str, work: Path) -> dict[str, Any]:
    size = read_json(EVALUATION / "PARAMETERS.json")["annotation"]["max_articles_per_instance"]
    rdir = campaign / "rounds" / round_name
    articles = read_json(rdir / "ARTICLES.json")["articles"]
    batches = []
    for wiki in LANGUAGES:
        names = sorted(
            n for n in articles if n.startswith(f"{wiki}-") and read_json(campaign / "packets" / f"{n}.json")["items"]
        )
        for k, chunk in enumerate(_chunks(names, size), 1):
            packets = [campaign / "packets" / f"{n}.json" for n in chunk]
            batch = f"{wiki}-{_tag(round_name)}{k:02d}"
            batches.append(
                {
                    "batch": batch,
                    "wiki": wiki,
                    "articles": chunk,
                    "items": sum(len(read_json(p)["items"]) for p in packets),
                    "instances": {role: _work_dir(work, f"{role}-{batch}", packets) for role in ("A", "B")},
                }
            )
    no_items = sorted(n for n in articles if not read_json(campaign / "packets" / f"{n}.json")["items"])
    doc = {"round": round_name, "batches": batches, "articles_without_items": no_items}
    write_json(rdir / "BATCHES.json", doc)
    return doc


def adjudicate(campaign: Path, round_name: str, work: Path) -> dict[str, Any]:
    size = read_json(EVALUATION / "PARAMETERS.json")["annotation"]["max_articles_per_instance"]
    rdir = campaign / "rounds" / round_name
    a = LB.by_item(read_json(rdir / "A.json"))
    b = LB.by_item(read_json(rdir / "B.json"))
    dis = set(LB.disagreements(a, b))
    by_article: dict[str, list[str]] = {}
    for n in read_json(rdir / "ARTICLES.json")["articles"]:
        ids = [it["item_id"] for it in read_json(campaign / "packets" / f"{n}.json")["items"] or []]
        hit = [i for i in ids if i in dis]
        if hit:
            by_article[n] = hit
    batches = []
    for wiki in LANGUAGES:
        names = sorted(n for n in by_article if n.startswith(f"{wiki}-"))
        for k, chunk in enumerate(_chunks(names, size), 1):
            batch = f"{wiki}-{_tag(round_name)}{k:02d}"
            inst = f"ADJ-{batch}"
            meta = _work_dir(work, inst, [campaign / "packets" / f"{n}.json" for n in chunk])
            (work / inst / "disputed").mkdir()
            for n in chunk:
                disputed = {
                    "article": n,
                    "items": [{"item_id": i, "A": a[i], "B": b[i]} for i in by_article[n]],
                }
                (work / inst / "disputed" / f"{n}.json").write_text(
                    json.dumps(disputed, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
                )
            meta["disputed"] = {p.name: file_sha256(p) for p in sorted((work / inst / "disputed").iterdir())}
            batches.append(
                {
                    "batch": batch,
                    "wiki": wiki,
                    "articles": chunk,
                    "items": sum(len(by_article[n]) for n in chunk),
                    "instance": meta,
                }
            )
    doc = {"round": round_name, "disagreed_items": len(dis), "batches": batches}
    write_json(rdir / "ADJ_BATCHES.json", doc)
    return doc


def collect(campaign: Path, round_name: str, work: Path, role: str) -> list[str]:
    rdir = campaign / "rounds" / round_name
    if role == "ADJ":
        path = rdir / "ADJ_BATCHES.json"
        instances = [b["instance"]["instance"] for b in read_json(path)["batches"]] if path.exists() else []
    else:
        instances = [b["instances"][role]["instance"] for b in read_json(rdir / "BATCHES.json")["batches"]]
    dest = rdir / "labels" / role
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for inst in instances:
        src = work / inst / "out" / f"labels-{inst}.json"
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        shutil.copyfile(src, dest / src.name)
        out.append(str(dest / src.name))
    return out


KEPT_ATTACHMENTS = ("model",)


def record(campaign: Path, round_name: str, instance: str, agent_id: str, transcripts: Path, model: str) -> None:
    """Platform metadata of one instance and its transcript (or its absence, recorded as missing).

    The committed transcript keeps every user and assistant record (the brief, every tool call and result, every
    answer) and the platform's ``model`` attachment, unchanged. Platform context attachments (system prompt snapshots,
    tool listings, environment, organization and session identifiers) are left out of the public repository; their
    record types are listed, and the SHA-256 and line count of the platform's original file are recorded.
    """
    rdir = campaign / "rounds" / round_name
    path = rdir / "INSTANCES.json"
    doc = read_json(path) if path.exists() else {"round": round_name, "instances": {}}
    src = transcripts / f"agent-{agent_id}.jsonl"
    entry: dict[str, Any] = {
        "agent_id": agent_id,
        "requested_model": model,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    if src.is_file():
        lines = src.read_text(encoding="utf-8").splitlines()
        kept, dropped = [], set()
        for line in lines:
            rec = json.loads(line)
            att = (rec.get("attachment") or {}).get("type")
            if rec.get("type") in ("user", "assistant") or att in KEPT_ATTACHMENTS:
                kept.append(line)
            else:
                dropped.add(att or str(rec.get("type")))
        (rdir / "transcripts").mkdir(parents=True, exist_ok=True)
        dst = rdir / "transcripts" / f"{instance}.jsonl"
        dst.write_text("\n".join(kept) + "\n", encoding="utf-8")
        text = "\n".join(kept)
        entry["transcript"] = f"transcripts/{dst.name}"
        entry["transcript_sha256"] = file_sha256(dst)
        entry["platform_original"] = {"sha256": file_sha256(src), "lines": len(lines), "kept_lines": len(kept)}
        entry["left_out_record_types"] = sorted(dropped)
        entry["platform_models"] = sorted(set(re.findall(r'"model":"(claude-[^"]+)"', text)))
        stamps = [json.loads(x)["timestamp"] for x in kept if json.loads(x).get("type") in ("user", "assistant")]
        entry["first_timestamp"], entry["last_timestamp"] = (stamps[0], stamps[-1]) if stamps else (None, None)
    else:
        entry["transcript"] = None
        entry["transcript_missing"] = True
    doc["instances"][instance] = entry
    write_json(path, doc)


def empty_adj(campaign: Path, round_name: str) -> None:
    rdir = campaign / "rounds" / round_name
    if LB.disagreements(LB.by_item(read_json(rdir / "A.json")), LB.by_item(read_json(rdir / "B.json"))):
        raise SystemExit("A and B disagree: adjudication is required")
    write_json(rdir / "ADJ.json", {"format": LB.FORMAT, "annotator": "ADJ", "instances": [], "labels": []})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 14 P2 annotation batches (executor glue)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("annotate", "adjudicate", "collect", "record", "empty-adj"):
        p = sub.add_parser(name)
        p.add_argument("--campaign", type=Path, required=True)
        p.add_argument("--round", required=True)
        if name in ("annotate", "adjudicate", "collect"):
            p.add_argument("--work", type=Path, required=True)
        if name == "collect":
            p.add_argument("--role", choices=("A", "B", "ADJ"), required=True)
        if name == "record":
            p.add_argument("--instance", required=True)
            p.add_argument("--agent-id", required=True)
            p.add_argument("--transcripts", type=Path, required=True)
            p.add_argument("--model", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "annotate":
        doc = annotate(a.campaign, a.round, a.work)
        for b in doc["batches"]:
            print(b["batch"], len(b["articles"]), "articles,", b["items"], "items")
        print(len(doc["articles_without_items"]), "articles without items")
    elif a.cmd == "adjudicate":
        doc = adjudicate(a.campaign, a.round, a.work)
        print(doc["disagreed_items"], "disagreed items in", len(doc["batches"]), "batches")
    elif a.cmd == "collect":
        print("\n".join(collect(a.campaign, a.round, a.work, a.role)))
    elif a.cmd == "empty-adj":
        empty_adj(a.campaign, a.round)
    else:
        record(a.campaign, a.round, a.instance, a.agent_id, a.transcripts, a.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
