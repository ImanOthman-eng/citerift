"""Reserve inclusion under FROZEN_PROTOCOL.md 7.2, from locked annotation counts only (no prediction is read).

Usage: python reserve_decision.py SELECTION_JSON CAPTURE_STATES_JSON ANNOTATION_DIR > RESERVE_DECISION.json

Bundle paths recorded under the session scratchpad are looked up in ../capture/bundles/ when absent.
Counts per article the in-window annotated items: target identifier occurrences (role other than not_a_target),
uses, definitions (in_window true) and linkable uses (uses with a render_ref_id). Holdout positions 1-10 always
count; reserve positions 11-16 are added in order, two at a time, while any per-language minimum is not met.
"""

import json
import sys
from pathlib import Path

MIN = {"target_identifiers": 50, "uses": 80, "definitions": 60, "linkable_uses": 60}


def counts(ann: dict) -> dict[str, int]:
    ws, we = ann["article"]["window"]

    def inside(at: dict) -> bool:
        return ws <= at["cp"] < we

    defs = [d for d in ann["definitions"] if d.get("in_window", True) and inside(d["at"])]
    uses = [u for u in ann["uses"] if inside(u["at"])]
    ids = [i for i in ann["identifiers"] if inside(i["at"]) and i["role"] != "not_a_target"]
    return {
        "target_identifiers": len(ids),
        "uses": len(uses),
        "definitions": len(defs),
        "linkable_uses": sum(1 for u in uses if u.get("render_ref_id")),
    }


def total(rows: list[dict]) -> dict[str, int]:
    return {k: sum((r["counts"] or {}).get(k, 0) for r in rows) for k in MIN}


def main() -> int:
    sel = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    states = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["articles"]
    ann_dir = Path(sys.argv[3])
    by_rev = {p.stem: p for p in ann_dir.glob("*.json") if p.name != "ANNOTATION_LOCK.json"}
    out = {}
    for wiki in ("ar", "en"):
        rows = []
        for split in ("holdout", "reserve"):
            for a in sel["splits"][wiki][split]:
                key = f"{split}/{wiki}-{a['page_id']}"
                bundle = states[key]["final"]["bundle"]
                rev = None
                if bundle:
                    path = Path(bundle)
                    if not path.exists():
                        path = (
                            Path(__file__).resolve().parents[1] / "capture" / "bundles" / path.parent.name / path.name
                        )
                    cap = json.loads((path / "capture.json").read_text(encoding="utf-8"))
                    rev = cap["page"]["revision_id"]
                f = by_rev.get(f"{wiki}-{rev}")
                c = counts(json.loads(f.read_text(encoding="utf-8"))) if f else None
                rows.append({"key": key, "revision_id": rev, "annotation": f.name if f else None, "counts": c})
        included = rows[:10]
        reserve = rows[10:]
        while any(total(included)[k] < v for k, v in MIN.items()) and reserve:
            included += reserve[:2]
            reserve = reserve[2:]
        out[wiki] = {
            "included": [r["key"] for r in included],
            "not_needed": [r["key"] for r in reserve],
            "totals": total(included),
            "minimums_met": {k: total(included)[k] >= v for k, v in MIN.items()},
            "rows": rows,
        }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
