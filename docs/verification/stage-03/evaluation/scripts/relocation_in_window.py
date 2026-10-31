"""Supplementary to FROZEN_PROTOCOL.md section 8 (not a gate): the C-form use relocation restricted to the window.

Usage: python relocation_in_window.py SCORE_SPEC.json > relocation_in_window.json

The frozen ``evaluate.relocation`` counts as ``uses_wrong`` every rendered use the engine links for the citing
reference anywhere in the article, but the expected set holds only the annotated uses, which lie in the window.
A correct link for a use outside the window is therefore counted as wrong. This script repeats the C count with
the engine's uses restricted to those whose source start lies in the window, so that both sides cover the same
scope. Everything else is as in ``evaluate.relocation``; the frozen figures stay reported beside these.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "protocol" / "scripts"))

import evaluate as ev


def article(bundle: Path, ann_path: Path, ext_path: Path) -> dict[str, int]:
    art = ev.load_bundle(bundle)
    ann = json.loads(ann_path.read_text(encoding="utf-8"))
    doc = json.loads(ext_path.read_text(encoding="utf-8"))
    text, win = art.text, art.window
    defs = [d for d in ann["definitions"] if ev.at_ok(text, d["at"])]
    a_uses = [u for u in ann["uses"] if ev.at_ok(text, u["at"])]
    uses_by_container: dict[str, list[dict[str, Any]]] = {}
    for u in doc["uses"]:
        if u["container_id"] and ev.in_window(u["source"]["cp_start"], win):
            uses_by_container.setdefault(u["container_id"], []).append(u)
    containers = {c["id"]: c for c in doc["containers"]}
    out: Counter[str] = Counter()
    for a in ann["identifiers"]:
        if a["scheme"] != "doi" or a["role"] not in ev.CITED_WORK_ROLES or not a.get("key"):
            continue
        if not ev.at_ok(text, a["at"]) or not ev.in_window(a["at"]["cp"], win):
            continue
        s, e = a["at"]["cp"], a["at"]["cp"] + len(a["at"]["quote"])
        home = min((d for d in defs if d["at"]["cp"] <= s), key=lambda d: s - d["at"]["cp"], default=None)
        want = {
            u.get("render_ref_id")
            for u in a_uses
            if home and isinstance(u.get("binds_to"), dict) and u["binds_to"]["cp"] == home["at"]["cp"]
        } - {None}
        rec = next(
            (
                i
                for i in doc["identifiers"]
                if i["scheme"] == "doi" and min(e, i["source"]["cp_end"]) - max(s, i["source"]["cp_start"]) > 0
            ),
            None,
        )
        c = containers.get(rec["container_id"]) if rec and rec.get("container_id") else None
        got = (
            {
                u["render"]["locator"]["element_id"]
                for u in uses_by_container.get(c["id"], [])
                if u["render"]["state"] == "matched" and u["render"].get("locator")
            }
            if c
            else set()
        )
        out["uses_expected"] += len(want)
        out["uses_correct"] += len(want & got)
        out["uses_wrong"] += len(got - want)
    return dict(out)


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result: dict[str, Any] = {}
    for split, entries in spec["splits"].items():
        per: dict[str, Counter[str]] = {}
        for e in entries:
            name = Path(e["locked"]).name
            ann = e.get("adjudicated") or e["locked"]
            per.setdefault(name[:2], Counter()).update(article(Path(e["bundle"]), Path(ann), Path(e["extraction"])))
        result[split] = {w: dict(c) for w, c in per.items()}
    sys.stdout.write(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
