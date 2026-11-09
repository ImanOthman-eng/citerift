"""Compare two output directories of ``extract_all.py``: per use the render state and marker, and the basis; per
container the render state and region; per container the marker observation; per article the identifier render
states and the status. Prints counts per kind of change and a few examples.

Usage: python compare_runs.py <before dir> <after dir> [examples per kind]
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def marker_of(render: dict[str, Any]) -> str | None:
    return (render.get("locator") or {}).get("element_id")


def main(before: Path, after: Path, shown: int) -> None:
    tot: Counter[str] = Counter()
    ex: dict[str, list[object]] = {}

    def note(kind: str, example: object) -> None:
        tot[kind] += 1
        ex.setdefault(kind, []).append(example)

    for f in sorted(after.glob("*.json")):
        if f.name.startswith("_"):
            continue
        o = json.loads((before / f.name).read_text(encoding="utf-8"))
        n = json.loads(f.read_text(encoding="utf-8"))
        name = f.name[-40:]
        ou = {u["id"]: u["render"] for u in o["uses"]}
        for u in n["uses"]:
            x, y = ou.get(u["id"], {}), u["render"]
            mx, my = marker_of(x), marker_of(y)
            if (x.get("state"), mx) != (y.get("state"), my):
                moved = " DIFFERENT MARKER" if mx and my and mx != my else ""
                note(f"use {x.get('state')}->{y.get('state')}{moved}", (name, u["id"], mx, my))
            elif x.get("basis") != y.get("basis"):
                note("use basis only", (name, u["id"], x.get("basis"), y.get("basis")))
        oc = {c["id"]: c["render"] for c in o["containers"]}
        for c in n["containers"]:
            x, y = oc.get(c["id"], {}), c["render"]
            if x != y:
                moved = " region changed" if x.get("region_id") and y.get("region_id") else ""
                note(f"container {x.get('state')}->{y.get('state')}{moved}", (name, c["id"], x, y))
        om = {m.get("container_id"): m.get("state") for m in o["markers"]}
        nm = {m.get("container_id"): m.get("state") for m in n["markers"]}
        for k in sorted(set(om) | set(nm), key=str):
            if om.get(k) != nm.get(k):
                note(f"marker observation {om.get(k)}->{nm.get(k)}", (name, k))
        oi = {i["id"]: i["render"]["state"] for i in o["identifiers"]}
        for i in n["identifiers"]:
            if oi.get(i["id"]) != i["render"]["state"]:
                note(f"identifier {oi.get(i['id'])}->{i['render']['state']}", (name, i["id"]))
        if o["status"] != n["status"]:
            note(f"status {o['status']}->{n['status']}", name)
    for kind, count in sorted(tot.items()):
        print(count, kind)
        for e in ex[kind][:shown]:
            print("    ", str(e)[:330])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
