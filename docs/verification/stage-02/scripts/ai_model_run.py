"""Run the local open-model adapter on protocol v2 cases, calibrate the finalist on development data, and
score the frozen holdout run (docs/verification/stage-02/ai/v2/PROTOCOL_V2.md).

All predictions go through citerift.retraction.local_model.LocalAmbiguityModel.rank, the same entry point
as the CLI. Inputs are bundles only: no label, target or baseline decision reaches the model.

  screen-ids  the 40 screening case ids (seeded, from dev-set.json)
  score       rank each case's bundle; one JSON line per case (assessment, wall time); usage summary
  calibrate   choose the wrapper thresholds on development predictions; write the frozen manifest
  evaluate    v2 metrics, paired analysis and admission from holdout predictions and the baseline

Run in the inference environment, network denied after setup:
  .venv-infer/bin/python -I docs/verification/stage-02/scripts/ai_model_run.py score --manifest M
      --model-dir models/... --cases docs/verification/stage-02/ai/v2/dev-set.json [--ids FILE] --out P.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import resource
import socket
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from citerift.retraction import local_model, stats

SCREEN_SEED = 20261029
BOOT_SEED = 20261030


def _items(path: Path) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["items"]
    return data


def screen_ids(items: list[dict[str, Any]]) -> list[str]:
    rng = random.Random(SCREEN_SEED)  # noqa: S311 - a reproducible draw, not a secret
    order = sorted(items, key=lambda i: i["group_min_ordinal"])
    rng.shuffle(order)
    taken: Counter[str] = Counter()
    chosen = []
    for it in order:
        key = f"{it['label']}/{it['stratum']}"
        if taken[key] < 6:
            taken[key] += 1
            chosen.append(it["group_query_event"])
    rest = [it["group_query_event"] for it in order if it["group_query_event"] not in chosen]
    return sorted(chosen + rest[:4])


class _NoNetwork(socket.socket):
    def connect(self, *args: Any, **kwargs: Any) -> None:
        raise OSError("network access is disabled for local inference runs")


def cmd_score(args: argparse.Namespace) -> int:
    if args.deny_network:
        socket.socket = _NoNetwork  # type: ignore[misc]  # any connection attempt fails loudly
    manifest = local_model.load_manifest(args.manifest)
    items = _items(args.cases)
    if args.ids:
        wanted = set(json.loads(args.ids.read_text(encoding="utf-8")))
        items = [i for i in items if i["group_query_event"] in wanted]
    model = local_model.LocalAmbiguityModel(args.model_dir)
    times = []
    started = time.perf_counter()
    reasons: Counter[str] = Counter()
    pairs = tokens = 0
    with args.out.open("w", encoding="utf-8") as out:
        for it in items:
            t0 = time.perf_counter()
            a = model.rank(it["bundle"], manifest, local_model.Budget())
            wall = time.perf_counter() - t0
            if a.reason_codes[:1] not in (("BELOW_THRESHOLD_OR_MARGIN",), ()) and a.decision == "abstain":
                reasons[a.reason_codes[0]] += 1
            pairs += a.usage["pairs"]
            tokens += a.usage["tokens"]
            times.append(a.timing["case_s"])
            out.write(
                json.dumps(
                    {"group_query_event": it["group_query_event"], "wall_s": round(wall, 6), "assessment": a.to_json()},
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )
    warm = sorted(times[1:]) if len(times) > 1 else times
    summary = {
        "cases": len(items),
        "manifest_sha256": local_model.manifest_sha256(manifest),
        "cold_init_s": model.init_s,
        "warm_case_p50_s": warm[len(warm) // 2] if warm else None,
        "warm_case_p95_s": warm[min(len(warm) - 1, math.ceil(0.95 * len(warm)) - 1)] if warm else None,
        "max_case_s": max(times) if times else None,
        "total_wall_s": round(time.perf_counter() - started, 3),
        "pairs": pairs,
        "tokens": tokens,
        "failures_by_reason": dict(reasons),
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
        "network_denied": bool(args.deny_network),
        "predictions_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
    }
    args.out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


def _load_preds(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r["group_query_event"]] = r["assessment"]
    return out


def _anchor(item: dict[str, Any], cid: str | None) -> str | None:
    return next((c["anchor"] for c in item["candidates"] if c["candidate_id"] == cid), None)


def _correct(item: dict[str, Any], decision: str, anchor: str | None) -> bool:
    if item["label"] == "positive":
        return decision == "select" and anchor == item["target"]
    return decision == "abstain"


def _decide(a: dict[str, Any], wrapper: dict[str, Any]) -> tuple[str, str | None]:
    if not a["ranked"]:
        return "abstain", None  # a failure or an invalid bundle stays an abstention
    return local_model.decide([(r["candidate_id"], r["score"]) for r in a["ranked"]], wrapper)


def best_wrapper(
    items: list[dict[str, Any]], preds: dict[str, dict[str, Any]], max_neg_fs: int | None
) -> dict[str, Any]:
    tops = sorted({r["score"] for i in items for r in preds[i["group_query_event"]]["ranked"][:1]})
    lo, hi = math.floor(min(tops) * 4) / 4, math.ceil(max(tops) * 4) / 4
    grid = []
    ts = lo
    while ts <= hi + 1e-9:
        for tm in (0.0, 0.5, 1.0, 2.0, 3.0):
            w = {"tau_s": round(ts, 2), "tau_m": tm}
            dec = [(_decide(preds[i["group_query_event"]], w), i) for i in items]
            correct = sum(_correct(i, d, _anchor(i, c)) for (d, c), i in dec)
            neg_fs = sum(1 for (d, _c), i in dec if i["label"] == "negative" and d == "select")
            grid.append({**w, "correct": correct, "negative_false_selections": neg_fs})
        ts += 0.25
    ok = [g for g in grid if max_neg_fs is None or g["negative_false_selections"] <= max_neg_fs]
    best = max(ok or grid, key=lambda g: (g["correct"], g["tau_s"], g["tau_m"]))
    return {"best": best, "grid_size": len(grid), "feasible": bool(ok)}


def cmd_calibrate(args: argparse.Namespace) -> int:
    items = _items(args.cases)
    preds = _load_preds(args.preds)
    exclude = set(json.loads(args.exclude_ids.read_text(encoding="utf-8"))) if args.exclude_ids else set()
    items = [i for i in items if i["group_query_event"] in preds and i["group_query_event"] not in exclude]
    from ai_protocol_v2 import baseline_correct  # noqa: PLC0415 - script-local helper

    base_fs = sum(1 for i in items if i["label"] == "negative" and baseline_correct(i)[1] == "select")
    base_ok = sum(baseline_correct(i)[0] for i in items)
    result = best_wrapper(items, preds, base_fs)
    manifest = local_model.load_manifest(args.manifest)
    manifest["wrapper"] = {
        "tau_s": result["best"]["tau_s"],
        "tau_m": result["best"]["tau_m"],
        "state": "frozen",
        "calibrated_on": f"{len(items)} development cases ({args.cases.name}, screening cases excluded)",
        "development_correct": result["best"]["correct"],
        "development_negative_false_selections": result["best"]["negative_false_selections"],
        "development_baseline_correct": base_ok,
        "development_baseline_negative_false_selections": base_fs,
    }
    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "n": len(items),
                **result,
                "baseline_correct": base_ok,
                "baseline_neg_fs": base_fs,
                "manifest_sha256": local_model.manifest_sha256(manifest),
            },
            sort_keys=True,
        )
    )
    return 0


def _metrics(items: list[dict[str, Any]], dec: list[tuple[str, str | None]]) -> dict[str, Any]:
    n = len(items)
    pos = [k for k, i in enumerate(items) if i["label"] == "positive"]
    neg = [k for k, i in enumerate(items) if i["label"] == "negative"]
    correct = [_correct(i, d, a) for i, (d, a) in zip(items, dec, strict=True)]
    sel = [k for k, (d, _a) in enumerate(dec) if d == "select"]
    right_sel = sum(1 for k in sel if dec[k][1] == items[k]["target"])
    return {
        "n": n,
        "correct": sum(correct),
        "errors": n - sum(correct),
        "all_case_accuracy": sum(correct) / n,
        "all_case_accuracy_wilson_95": stats.wilson(sum(correct), n),
        "positive_recall": sum(correct[k] for k in pos) / len(pos) if pos else None,
        "selection_coverage": len(sel) / n,
        "selection_precision": right_sel / len(sel) if sel else None,
        "selection_precision_wilson_95": stats.wilson(right_sel, len(sel)) if sel else None,
        "negative_false_selections": sum(1 for k in neg if dec[k][0] == "select"),
        "negative_false_selection_rate": sum(1 for k in neg if dec[k][0] == "select") / len(neg) if neg else None,
        "candidate_recall_at_5": sum(bool(items[k]["candidate_recall_at_5"]) for k in pos) / len(pos) if pos else None,
        "abstention": {
            "all": sum(1 for d, _a in dec if d == "abstain") / n,
            "positives": sum(1 for k in pos if dec[k][0] == "abstain") / len(pos) if pos else None,
            "negatives": sum(1 for k in neg if dec[k][0] == "abstain") / len(neg) if neg else None,
        },
        "critical_confusions": sum(
            1 for k in sel if items[k]["query_notice_key"] and dec[k][1] == items[k]["query_notice_key"]
        ),
        "per_stratum": {
            s: {
                "n": sum(1 for i in items if f"{i['label']}/{i['stratum']}" == s),
                "correct": sum(c for i, c in zip(items, correct, strict=True) if f"{i['label']}/{i['stratum']}" == s),
            }
            for s in sorted({f"{i['label']}/{i['stratum']}" for i in items})
        },
        "correct_vector": correct,
    }


def cmd_evaluate(args: argparse.Namespace) -> int:
    items = _items(args.cases)
    preds = _load_preds(args.preds)
    manifest = local_model.load_manifest(args.manifest)
    attain = json.loads(args.attainability.read_text(encoding="utf-8"))["attainability"]
    base_dec = [(d, a) for d, a in attain["baseline_decisions"]]
    missing = [i["group_query_event"] for i in items if i["group_query_event"] not in preds]
    ai_dec = [
        _decide(preds[i["group_query_event"]], manifest["wrapper"])
        if i["group_query_event"] in preds
        else ("abstain", None)
        for i in items
    ]
    for i, (d, c) in zip(items, list(ai_dec), strict=True):
        a = preds.get(i["group_query_event"])
        if a is not None and (a["decision"], a["candidate_id"]) != (d, c):
            raise SystemExit(f"recorded decision differs from the frozen wrapper for {i['group_query_event']}")
    ai_dec = [(d, _anchor(i, c) if d == "select" else None) for i, (d, c) in zip(items, ai_dec, strict=True)]
    b, m = _metrics(items, base_dec), _metrics(items, ai_dec)
    bc, mc = b.pop("correct_vector"), m.pop("correct_vector")
    disc_b = sum(1 for x, y in zip(bc, mc, strict=True) if x and not y)
    disc_c = sum(1 for x, y in zip(bc, mc, strict=True) if y and not x)
    p = stats.mcnemar_exact_one_sided(disc_b, disc_c)
    eb, ea = b["errors"], m["errors"]
    rer = (eb - ea) / eb if eb else None
    rng = random.Random(BOOT_SEED)  # noqa: S311
    boots_rer, boots_diff = [], []
    n = len(items)
    for _ in range(10000):
        idx = [rng.randrange(n) for _ in range(n)]
        e_b = sum(not bc[k] for k in idx)
        e_a = sum(not mc[k] for k in idx)
        boots_diff.append((e_b - e_a) / n)
        if e_b:
            boots_rer.append((e_b - e_a) / e_b)
    boots_rer.sort()
    boots_diff.sort()

    def ci(xs: list[float]) -> list[float] | None:
        return [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]] if xs else None

    gate = json.loads(args.protocol.read_text(encoding="utf-8"))["admission"]
    checks = {
        "min_eligible_groups": n >= gate["min_eligible_groups"],
        "relative_error_reduction": rer is not None and rer >= gate["min_relative_error_reduction"],
        "one_sided_p": p < gate["max_one_sided_p"],
        "positive_recall": (m["positive_recall"] or 0) >= gate["min_positive_recall"],
        "negative_false_selections_not_above_baseline": m["negative_false_selections"]
        <= b["negative_false_selections"],
        "critical_confusions_zero": m["critical_confusions"] == 0,
        "prohibited_fact_writes_zero": args.index_digest_before == args.index_digest_after,
        "complete_predictions": not missing,
    }
    result = {
        "protocol_version": "2.0.0",
        "manifest_sha256": local_model.manifest_sha256(manifest),
        "predictions_sha256": hashlib.sha256(args.preds.read_bytes()).hexdigest(),
        "holdout_manifest_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "baseline": b,
        "model": m,
        "paired": {
            "b_baseline_right_model_wrong": disc_b,
            "c_model_right_baseline_wrong": disc_c,
            "exact_one_sided_p": p,
            "relative_error_reduction": rer,
            "relative_error_reduction_bootstrap_95": ci(boots_rer),
            "accuracy_difference": (eb - ea) / n,
            "accuracy_difference_bootstrap_95": ci(boots_diff),
        },
        "index_digest_before": args.index_digest_before,
        "index_digest_after": args.index_digest_after,
        "missing_predictions": missing,
        "admission_checks": checks,
        "resources_checked_separately": "see the run summary (resource limits are reported there)",
        "admitted_on_quality": all(checks.values()),
    }
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("paired", "admission_checks", "admitted_on_quality")}, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("screen-ids")
    s.add_argument("--cases", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("score")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--model-dir", type=Path, required=True)
    r.add_argument("--cases", type=Path, required=True)
    r.add_argument("--ids", type=Path)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--deny-network", action="store_true")
    c = sub.add_parser("calibrate")
    c.add_argument("--manifest", type=Path, required=True)
    c.add_argument("--cases", type=Path, required=True)
    c.add_argument("--preds", type=Path, required=True)
    c.add_argument("--exclude-ids", type=Path)
    c.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--manifest", type=Path, required=True)
    e.add_argument("--cases", type=Path, required=True)
    e.add_argument("--preds", type=Path, required=True)
    e.add_argument("--attainability", type=Path, required=True)
    e.add_argument("--protocol", type=Path, required=True)
    e.add_argument("--index-digest-before", required=True)
    e.add_argument("--index-digest-after", required=True)
    e.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.command == "screen-ids":
        ids = screen_ids(_items(args.cases))
        args.out.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
        print(len(ids))
        return 0
    return {"score": cmd_score, "calibrate": cmd_calibrate, "evaluate": cmd_evaluate}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
