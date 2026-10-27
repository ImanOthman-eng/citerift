"""Score the frozen protocol (docs/verification/stage-02/ai/protocol.json) on the held-out split.

The baseline is scored from the frozen bundles and thresholds. Model responses, when a recorded run exists,
are read from a JSONL file of {group_query_event, raw_output, failure, tool_uses, usage, latency_ms} records
and interpreted only through citerift.retraction.advisory.interpret; nothing here can write a fact.

Run: python docs/verification/stage-02/scripts/ai_evaluate.py --protocol P [--responses R] --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from citerift.retraction import advisory, ambiguity, stats


def _metrics(items: list[dict[str, Any]], decisions: list[tuple[str, str | None]]) -> dict[str, Any]:
    pos = [(i, d) for i, d in zip(items, decisions, strict=True) if i["label"] == "positive"]
    neg = [(i, d) for i, d in zip(items, decisions, strict=True) if i["label"] == "negative"]
    correct = [
        (i["label"] == "positive" and d[0] == "select" and d[1] == i["target"])
        or (i["label"] == "negative" and d[0] == "abstain")
        for i, d in zip(items, decisions, strict=True)
    ]
    selections = [(i, d) for i, d in zip(items, decisions, strict=True) if d[0] == "select"]
    right_sel = sum(1 for i, d in selections if d[1] == i["target"])
    confusions = sum(1 for i, d in selections if i["query_notice_key"] and d[1] == i["query_notice_key"])
    n = len(items)
    return {
        "n": n,
        "primary_correct": sum(correct),
        "primary_accuracy": sum(correct) / n,
        "primary_wilson_95": stats.wilson(sum(correct), n),
        "selections": len(selections),
        "coverage": len(selections) / n,
        "selection_precision": right_sel / len(selections) if selections else None,
        "selection_precision_wilson_95": stats.wilson(right_sel, len(selections)) if selections else None,
        "positive_recall": sum(1 for i, d in pos if d[0] == "select" and d[1] == i["target"]) / len(pos),
        "false_selections_on_negatives": sum(1 for _i, d in neg if d[0] == "select"),
        "abstention": sum(1 for d in decisions if d[0] == "abstain") / n,
        "notice_original_confusions": confusions,
        "per_stratum": {
            f"{lab}/{st}": sum(
                c for i, c in zip(items, correct, strict=True) if (i["label"], i["stratum"]) == (lab, st)
            )
            for lab, st in sorted({(i["label"], i["stratum"]) for i in items})
        },
        "correct_vector": correct,
    }


def baseline_decisions(items: list[dict[str, Any]], tau_s: float, tau_m: float) -> list[tuple[str, str | None]]:
    out = []
    for it in items:
        cands = [
            ambiguity.Candidate(**{k: c[k] for k in ("anchor", "event_id", "score", "cos_title", "year", "author")})
            for c in it["candidates"]
        ]
        out.append(ambiguity.decide(cands, tau_s, tau_m))
    return out


def model_decisions(items: list[dict[str, Any]], responses: dict[str, dict[str, Any]]) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for it in items:
        r = responses.get(it["group_query_event"])
        if r is None:
            s = advisory.interpret(None, it["bundle"], failure="NOT_RUN")
        else:
            s = advisory.interpret(
                r.get("raw_output"), it["bundle"], failure=r.get("failure"), tool_uses=tuple(r.get("tool_uses", ()))
            )
        anchor = None
        if s.decision == "select":
            anchor = next(c["anchor"] for c in it["candidates"] if c["candidate_id"] == s.candidate_id)
        out.append((s.decision, anchor))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--responses", type=Path)
    ap.add_argument("--split", default="heldout", choices=["tuning", "heldout"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--run-record", type=Path, help="measured run facts: index digests before/after, resource use")
    args = ap.parse_args(argv)
    if args.responses and not args.run_record:
        ap.error("--responses needs --run-record (fact writes and resource limits are gate criteria)")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    items = protocol["splits"][args.split]
    th = protocol["frozen_thresholds"]
    base = _metrics(items, baseline_decisions(items, th["tau_s"], th["tau_m"]))
    pos = [i for i in items if i["label"] == "positive"]
    report: dict[str, Any] = {
        "split": args.split,
        "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        "candidate_recall_at_5": sum(bool(i["candidate_recall_at_5"]) for i in pos) / len(pos),
        "baseline": base,
        "max_attainable_gain_pp": round(100 * (1 - base["primary_accuracy"]), 3),
    }
    if args.responses:
        responses = {}
        for line in args.responses.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                responses[r["group_query_event"]] = r
        model = _metrics(items, model_decisions(items, responses))
        b = sum(1 for x, y in zip(base["correct_vector"], model["correct_vector"], strict=True) if x and not y)
        c = sum(1 for x, y in zip(base["correct_vector"], model["correct_vector"], strict=True) if y and not x)
        gate = protocol["admission_gate"]
        gain = 100 * (model["primary_accuracy"] - base["primary_accuracy"])
        p = stats.mcnemar_exact_one_sided(b, c)
        report["model"] = model
        report["paired"] = {"b_baseline_right_model_wrong": b, "c_model_right_baseline_wrong": c, "p_one_sided": p}
        run = json.loads(args.run_record.read_text(encoding="utf-8"))
        report["run_record"] = run
        report["admission"] = {
            "eligible_groups_ok": len(items) >= gate["min_eligible_groups"],
            "gain_pp": gain,
            "gain_ok": gain >= gate["min_accuracy_gain_pp"],
            "p_ok": p < gate["max_p"],
            "coverage_ok": model["coverage"] >= gate["min_selection_coverage"],
            "false_selections_ok": model["false_selections_on_negatives"] <= base["false_selections_on_negatives"],
            "confusions_ok": model["notice_original_confusions"] == 0,
            "fact_writes_ok": run["index_artifact_digest_before"] == run["index_artifact_digest_after"]
            and run["prohibited_fact_writes"] == 0,
            "resource_limits_ok": run["resource_limits_met"] is True,
        }
        report["admission"]["admitted"] = all(v for k, v in report["admission"].items() if k.endswith("_ok"))
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {k: v for k, v in base.items() if k not in {"correct_vector", "per_stratum"}}
    print(json.dumps({"baseline": summary, "max_attainable_gain_pp": report["max_attainable_gain_pp"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
