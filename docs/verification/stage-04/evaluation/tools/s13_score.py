"""Stage 04 Step 13: the pre-registered scorer (PREREGISTRATION.md sections 8 to 10; D-067, D-068, D-069).

Reads only: the locked final labels (``LOCK.json``), the packets, the retained Stage 03 extractions, the exports of
the one prediction run (``RUN.json``), the pinned Stage 02 index (plain SQL) and, for the sensitivity variants, the
retained Investigation Memory. It writes ``SCORES.json``. Every number, rule and threshold comes from
``PARAMETERS.json`` or from the definitions below, all committed and hashed before the draw.

Unit of analysis: a Stage 03 citation unit of a captured article revision. Per language:

- **engine positive unit**: a unit with at least one claim of the four positive classes (D-068);
- **attachment correct** (a positive claim c of unit u, final label L of u's item): L.kind is ``work_citation``,
  L.same_work is not ``no``, and among the records the claim's keys reach as the *original* paper (index ``ident``
  role ``original``) at least one is judged ``cited_work`` and none ``unrelated`` or ``cited_notice``; a positive
  unit is correct when every positive claim of it is; a positive unit outside the item set, or whose relevant
  judgments are all ``cannot_tell``, is counted incorrect (and reported separately);
- **truth-positive unit**: an item whose final label has kind ``work_citation``, same_work not ``no`` and at least
  one record judged ``cited_work`` (retrieval-scoped: units without a candidate record are not annotated);
- **engine negative unit**: a unit with a ``NOT_FOUND_IN_CHECKED_SOURCES`` claim and no positive claim.

Hazards (each must be 0): H1 notice counted as attachment (positive unit with kind ``notice_citation`` or a reached
record judged ``cited_notice``); H2 marker counted as attachment (kind ``retraction_marker``); H3 identity conflict
counted as attachment (same_work ``no``); H4 exact miss (a NOT_FOUND claim whose key is an identifier of the index).
Structural violations (each must be 0): S1 an investigation not COMPLETED or NEEDS_RESOLUTION, or without a passed
VERIFY and an export; S2 a forbidden phrase (S-7.7) in a summary or explanation; S3 a positive claim without
supporting evidence.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s13_acquire as AQ
import s13_baseline as BL
import s13_sensitivity as SV
from s13_common import EVALUATION, LANGUAGES, clopper_pearson, file_sha256, read_json, write_json

from citerift.investigation.explanations import FORBIDDEN

POSITIVE = ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")
SECONDARY = ("RETRACTED_WORK_CITED", "CONCERN_CITED")
NOT_FOUND = "NOT_FOUND_IN_CHECKED_SOURCES"
CONFLICT = "IDENTITY_CONFLICT"


def forbidden_in(text: str) -> list[str]:
    low = f" {text.lower()} "
    return [w for w in FORBIDDEN if any(f" {w}{end}" in low for end in (" ", ".", ",", ";", ":"))]


def export_claims(export: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    """The export manifest, its claim items (report chunks) and the explanation text of each claim."""
    manifest = read_json(export / "export.json")
    report = read_json(export / "report" / f"{manifest['report']}.json")
    items: list[dict[str, Any]] = []
    for chunk in report["components"]["claims"]["chunks"]:
        items += read_json(export / "report" / f"{chunk['chunk']}.json")["items"]
    texts: dict[str, str] = {}
    for f in sorted((export / "explanations").glob("*.json")):
        for e in read_json(f)["explanations"]:
            texts[e["claim_id"]] = f"{e.get('text') or ''} {e.get('chain') or ''}"
    return manifest, items, texts


def original_events(conn: sqlite3.Connection, keys: list[dict[str, str]]) -> set[str]:
    out: set[str] = set()
    for k in keys:
        for (eid,) in conn.execute(
            "SELECT e.event_id FROM ident i JOIN event e ON e.ordinal = i.ordinal "
            "WHERE i.scheme = ? AND i.norm = ? AND i.role = 'original'",
            (k["scheme"], k["normalized"]),
        ):
            out.add(eid)
    return out


def truth_positive(label: dict[str, Any] | None) -> bool:
    return (
        label is not None
        and label["kind"] == "work_citation"
        and label["same_work"] != "no"
        and "cited_work" in label["records"].values()
    )


def judge(
    keys: list[dict[str, str]], item: dict[str, Any] | None, label: dict[str, Any] | None, conn: sqlite3.Connection
) -> dict[str, Any]:
    """Correctness and hazards of one positive claim (by its keys) against the final label of its unit."""
    if item is None or label is None:
        return {"correct": False, "unannotated": True, "unverifiable": False, "hazards": []}
    events = original_events(conn, keys)
    judged = [label["records"][r["ref"]] for r in item["records"] if r["event_id"] in events]
    hazards = []
    if label["kind"] == "notice_citation" or "cited_notice" in judged:
        hazards.append("H1_NOTICE_AS_ATTACHMENT")
    if label["kind"] == "retraction_marker":
        hazards.append("H2_MARKER_AS_ATTACHMENT")
    if label["same_work"] == "no":
        hazards.append("H3_CONFLICT_AS_ATTACHMENT")
    correct = (
        label["kind"] == "work_citation"
        and label["same_work"] != "no"
        and "cited_work" in judged
        and not ({"unrelated", "cited_notice"} & set(judged))
    )
    unverifiable = not correct and (label["kind"] == "cannot_tell" or (bool(judged) and set(judged) == {"cannot_tell"}))
    return {"correct": correct, "unannotated": False, "unverifiable": unverifiable, "hazards": hazards}


def score_units(
    units: dict[str, list[dict[str, Any]]],
    items: dict[str, dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Unit-level outcome of one article for one set of unit classes (engine or a variant).

    ``units`` maps unit id to its claims as ``{"class", "keys"}``; ``items``/``labels`` are keyed by unit id."""
    out: dict[str, Any] = {"positive": [], "negative": [], "conflict": [], "hazards": []}
    for uid, claims in sorted(units.items()):
        pos = [c for c in claims if c["class"] in POSITIVE]
        label = labels.get(uid)
        if pos:
            verdicts = [judge(c["keys"], items.get(uid), label, conn) for c in pos]
            out["positive"].append(
                {
                    "unit_id": uid,
                    "classes": sorted({c["class"] for c in pos}),
                    "correct": all(v["correct"] for v in verdicts),
                    "unannotated": any(v["unannotated"] for v in verdicts),
                    "unverifiable": any(v["unverifiable"] for v in verdicts),
                }
            )
            out["hazards"] += [{"unit_id": uid, "hazard": h} for v in verdicts for h in v["hazards"]]
        elif any(c["class"] == NOT_FOUND for c in claims):
            out["negative"].append({"unit_id": uid, "truth_positive": truth_positive(label)})
        for c in claims:
            if c["class"] == NOT_FOUND:
                hit = [k for k in c["keys"] if BL.in_rw_fields(conn, k["scheme"], k["normalized"])]
                if hit:
                    out["hazards"].append({"unit_id": uid, "hazard": "H4_EXACT_MISS", "keys": hit})
        engine_conflict = any(c["class"] == CONFLICT for c in claims)
        if engine_conflict or (label is not None and label["same_work"] == "no"):
            out["conflict"].append(
                {
                    "unit_id": uid,
                    "engine_conflict": engine_conflict,
                    "engine_classes": sorted({c["class"] for c in claims}),
                    "label": label,
                    "annotated": label is not None,
                    "abstained": not pos,
                    "abstention_justified": None if label is None or pos else label["same_work"] != "yes",
                    "single_identifier_attachable": None if label is None else label["single_identifier_attachable"],
                    "converted_to_positive": bool(pos),
                }
            )
    return out


def proportion(x: int, n: int) -> dict[str, Any]:
    return clopper_pearson(x, n)


def summarize(articles: list[dict[str, Any]], params: dict[str, Any], key: str = "engine") -> dict[str, Any]:
    gates = params["gates"]
    out: dict[str, Any] = {}
    for wiki in LANGUAGES:
        arts = [a for a in articles if a["wiki"] == wiki]
        pos = [p for a in arts for p in a[key]["positive"]]
        neg = [n for a in arts for n in a[key]["negative"]]
        hazards = [h for a in arts for h in a[key]["hazards"]]
        n_pos, fp = len(pos), sum(1 for p in pos if not p["correct"])
        truth = [t for a in arts for t in a["truth_positive_units"]]
        found = {(a["article"], p["unit_id"]) for a in arts for p in a[key]["positive"] if p["correct"]}
        recall_x = sum(1 for t in truth if (t["article"], t["unit_id"]) in found)
        truth_id = [t for t in truth if t["identifier_reached"]]
        recall_id_x = sum(1 for t in truth_id if (t["article"], t["unit_id"]) in found)
        conflicts = [dict(c, article=a["article"]) for a in arts for c in a[key]["conflict"]]
        by_class = {}
        for cls in POSITIVE:
            rows = [p for p in pos if cls in p["classes"]]
            c = sum(1 for p in rows if p["correct"])
            by_class[cls] = {
                "n": len(rows),
                "correct": c,
                "incorrect": len(rows) - c,
                "precision": proportion(c, len(rows)),
            }
        sec = [p for p in pos if set(p["classes"]) & set(SECONDARY)]
        res: dict[str, Any] = {
            "articles": len(arts),
            "positive_units": n_pos,
            "false_attachments": fp,
            "unannotated_positive": sum(1 for p in pos if p["unannotated"]),
            "unverifiable_positive": sum(1 for p in pos if p["unverifiable"]),
            "positive_attachment_precision": proportion(n_pos - fp, n_pos),
            "false_attachment_rate": proportion(fp, n_pos),
            "by_class": by_class,
            "secondary_retracted_concern_precision": proportion(sum(1 for p in sec if p["correct"]), len(sec)),
            "negative_units": len(neg),
            "truth_positive_among_negatives": proportion(sum(1 for n in neg if n["truth_positive"]), len(neg)),
            "truth_positive_units": len(truth),
            "recall_retrieval_scoped": proportion(recall_x, len(truth)),
            "recall_identifier_reached": proportion(recall_id_x, len(truth_id)),
            "hazards": dict(Counter(h["hazard"] for h in hazards)),
            "identity_conflict": {
                "engine_cases": sum(1 for c in conflicts if c["engine_conflict"]),
                "label_only_cases": sum(1 for c in conflicts if not c["engine_conflict"]),
                "unannotated_engine_cases": sum(1 for c in conflicts if c["engine_conflict"] and not c["annotated"]),
                "converted_to_positive": sum(1 for c in conflicts if c["converted_to_positive"]),
                "cases": conflicts,
            },
        }
        if key == "engine":
            structural = [s for a in arts for s in a["structural"]]
            res["structural"] = dict(Counter(s["violation"] for s in structural))
            upper = res["false_attachment_rate"]["one_sided_95_upper"]
            res["gates"] = {
                "G1_positive_denominator": n_pos >= gates["min_positive_units"],
                "G2_false_attachment_bound": n_pos > 0 and upper <= gates["max_false_attachment_upper_95"],
                "G3_no_hazard": not hazards,
                "G4_no_structural_violation": not structural,
                "G5_negative_denominator": len(neg) >= gates["min_negative_units"],
            }
            res["passed"] = all(res["gates"].values())
        out[wiki] = res
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 scorer")
    ap.add_argument("--campaign", type=Path, required=True, help="the campaign directory")
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    params = read_json(EVALUATION / "PARAMETERS.json")
    run = read_json(a.campaign / "run" / "RUN.json")
    lock = read_json(a.campaign / "LOCK.json")
    for p, sha in lock["packets"].items():
        if file_sha256(a.campaign / "packets" / p) != sha:
            sys.exit(f"packet {p} changed after the lock")
    final = lock["final"]
    acquired = sorted(
        n for r in sorted((a.campaign / "rounds").glob("*")) for n in read_json(r / "ARTICLES.json")["articles"]
    )
    if acquired != sorted(art["article"] for art in run["articles"]):
        sys.exit("the run does not cover exactly the acquired articles")
    articles = []
    with sqlite3.connect(f"file:{a.index}?mode=ro", uri=True) as conn:
        for art in run["articles"]:
            articles.append(score_article(art, final, conn, a.campaign))
    scores = {
        "format": "citerift-stage04-eval-scores/1",
        "parameters_sha256": file_sha256(EVALUATION / "PARAMETERS.json"),
        "lock_sha256": file_sha256(a.campaign / "LOCK.json"),
        "run_sha256": file_sha256(a.campaign / "run" / "RUN.json"),
        "engine": summarize(articles, params),
        "baseline": summarize(articles, params, "baseline"),
        "sensitivity": {v: summarize(articles, params, f"variant_{v}") for v in ("a", "b", "c")},
        "not_computable_units": {v: sum(a[f"variant_{v}_not_computable"] for a in articles) for v in ("a", "b", "c")},
        "articles": articles,
    }
    scores["passed"] = all(scores["engine"][w]["passed"] for w in LANGUAGES)
    write_json(a.out, scores)
    for w in LANGUAGES:
        print(w, scores["engine"][w]["gates"], scores["engine"][w]["passed"])
    return 0


def score_article(
    art: dict[str, Any], final: dict[str, Any], conn: sqlite3.Connection, campaign: Path
) -> dict[str, Any]:
    name = art["article"]
    packet = read_json(campaign / "packets" / f"{name}.json")
    items = {it["unit_id"]: it for it in packet["items"] or []}
    labels = {it["unit_id"]: final[it["item_id"]] for it in packet["items"] or [] if it["item_id"] in final}
    truth = [
        {"article": name, "unit_id": uid, "identifier_reached": AQ.id_reached_truth_positive(items[uid], lab)}
        for uid, lab in labels.items()
        if truth_positive(lab)
    ]
    structural = []
    units: dict[str, list[dict[str, Any]]] = {}
    if art["lifecycle"] not in ("COMPLETED", "NEEDS_RESOLUTION") or not art["verify_passed"] or not art["export"]:
        structural.append({"violation": "S1_NOT_COMPLETED_OR_UNVERIFIED", "article": name})
    else:
        manifest, claims, texts = export_claims(campaign / art["export"])
        for t in [manifest.get("summary") or "", *texts.values()]:
            for w in forbidden_in(t):
                structural.append({"violation": "S2_FORBIDDEN_PHRASE", "article": name, "phrase": w})
        for it in claims:
            c = it["claim"]
            units.setdefault(it["unit"]["unit_id"], []).append({"class": c["class"], "keys": c["candidate"]["keys"]})
            if c["class"] in POSITIVE and (c["supporting_count"] < 1 or not c["evidence_set"]):
                structural.append({"violation": "S3_POSITIVE_WITHOUT_EVIDENCE", "article": name})
    extraction = read_json(campaign / "extractions" / f"{name}.json")
    if extraction["extraction_digest"] != packet["extraction_digest"]:
        raise ValueError(f"{name}: the retained extraction is not the packet's")
    flagged = BL.flagged_units(extraction, conn)
    baseline_units = {
        u: [{"class": "RETRACTED_WORK_CITED", "keys": [{"scheme": s, "normalized": n} for s, n in sorted(k)]}]
        for u, k in BL.eligible_keys(extraction).items()
        if u in flagged
    }
    out = {
        "article": name,
        "wiki": art["wiki"],
        "truth_positive_units": truth,
        "structural": structural,
        "engine": score_units(units, items, labels, conn),
        "baseline": score_units(baseline_units, items, labels, conn),
    }
    if units:
        retained = SV.Retained(campaign / art["memory_root"], art["investigation_key"])
        if retained.one(SV.EXTRACTION)[1]["extraction_digest"] != packet["extraction_digest"]:
            raise ValueError(f"{name}: the engine extracted another extraction than the annotated one")
        var = SV.variants(campaign / art["memory_root"], art["investigation_key"])
        for v in ("a", "b", "c"):
            vu: dict[str, list[dict[str, Any]]] = {}
            for c in var[v].values():
                vu.setdefault(c["unit_id"], []).append({"class": c["class"], "keys": c["keys"]})
            out[f"variant_{v}"] = score_units(vu, items, labels, conn)
            out[f"variant_{v}_not_computable"] = sum(1 for c in var[v].values() if c["class"] == SV.NOT_COMPUTABLE)
    else:
        for v in ("a", "b", "c"):
            out[f"variant_{v}"] = {"positive": [], "negative": [], "conflict": [], "hazards": []}
            out[f"variant_{v}_not_computable"] = 0
    return out


if __name__ == "__main__":
    sys.exit(main())
