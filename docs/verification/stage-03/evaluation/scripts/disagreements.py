"""Item-level disagreements between locked annotations and engine extractions (FROZEN_PROTOCOL.md section 4.5).

Usage: python disagreements.py SCORE_SPEC.json > disagreements.json

Uses the frozen scorer's own reading and matching (``evaluate.py``: ``load_bundle``, ``engine_predictions``,
``match_points``, ``match_spans``), so every listed item is exactly one the scorer counts as an error. Listed per
article: definitions and units only one side has, uses only one side has, wrong bindings, render links that differ,
identifier occurrences only one side has, key differences, role differences (promotions marked), and marker
differences. Each item carries the annotated location and label and the engine's value, which is what the
adjudicating evaluator is shown for that item, and nothing else from the extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "protocol" / "scripts"))

import evaluate as ev


def _quote(text: str, s: int, e: int) -> str:
    return text[s : min(e, s + 120)]


def article_items(bundle: Path, ann_path: Path, ext_path: Path) -> dict[str, Any]:
    art = ev.load_bundle(bundle)
    ann = json.loads(ann_path.read_text(encoding="utf-8"))
    doc = json.loads(ext_path.read_text(encoding="utf-8"))
    pred = ev.engine_predictions(doc)
    text, win = art.text, art.window
    items: list[dict[str, Any]] = []

    def ok(it: dict[str, Any]) -> bool:
        return ev.at_ok(text, it["at"]) and ev.in_window(it["at"]["cp"], win)

    a_defs = [d for d in ann["definitions"] if ok(d)]
    a_uses = [u for u in ann["uses"] if ok(u)]
    a_ids = [i for i in ann["identifiers"] if ok(i)]
    p_defs = [p for p in pred.definitions if ev.in_window(p.start, win)]
    p_uses = [p for p in pred.uses if ev.in_window(p.start, win)]
    p_units = [p for p in pred.units if ev.in_window(p.start, win)]
    p_ids = [p for p in pred.identifiers if ev.in_window(p.start, win)]

    dm, dtaken = ev.match_points([(d["at"]["cp"], d) for d in a_defs], p_defs)
    for ai, d in enumerate(a_defs):
        if ai not in dm:
            items.append({"kind": "definition_missed", "annotated": d})
    for pi, p in enumerate(p_defs):
        if pi not in dtaken:
            items.append(
                {"kind": "definition_extra", "engine": {"cp": p.start, "quote": _quote(text, p.start, p.end), **p.data}}
            )
    for ai, pi in dm.items():
        want = a_defs[ai].get("marker")
        got = p_defs[pi].data.get("marker")
        if want not in (None, "cannot_tell") and want != got:
            items.append({"kind": "marker", "annotated": a_defs[ai], "engine_marker": got})

    tpl_a = []
    for d in ann["definitions"]:
        for t in d.get("templates", []):
            if ev.at_ok(text, t["at"]) and ev.in_window(t["at"]["cp"], win):
                tpl_a.append((t["at"]["cp"], {"definition": d.get("id"), "at": t["at"]}))
    tpl_p = [p for p in p_units if p.data["kind"] == "template"]
    um, utaken = ev.match_points(tpl_a, tpl_p)
    for ai, (_, t) in enumerate(tpl_a):
        if ai not in um:
            items.append({"kind": "template_unit_missed", "annotated": t})
    for pi, p in enumerate(tpl_p):
        if pi not in utaken:
            items.append(
                {"kind": "template_unit_extra", "engine": {"cp": p.start, "quote": _quote(text, p.start, p.end)}}
            )
    uns_p = [
        p
        for p in pred.units
        if p.data["kind"] == "unstructured" and any(d.start <= p.start < max(d.end, d.start + 1) for d in p_defs)
    ]
    uns_taken: set[int] = set()
    for ai, d in enumerate(a_defs):
        if not d.get("unstructured"):
            continue
        hit = None
        if ai in dm:
            pd = p_defs[dm[ai]]
            hit = next(
                (
                    k
                    for k, p in enumerate(uns_p)
                    if k not in uns_taken and pd.start <= p.start < max(pd.end, pd.start + 1)
                ),
                None,
            )
        if hit is None:
            items.append({"kind": "unstructured_unit_missed", "annotated": d})
        else:
            uns_taken.add(hit)
    for k, p in enumerate(uns_p):
        if k not in uns_taken:
            items.append(
                {"kind": "unstructured_unit_extra", "engine": {"cp": p.start, "quote": _quote(text, p.start, p.end)}}
            )

    um_, utk = ev.match_points([(u["at"]["cp"], u) for u in a_uses], p_uses)
    for ai, u in enumerate(a_uses):
        if ai not in um_:
            items.append({"kind": "use_missed", "annotated": u})
    for pi, p in enumerate(p_uses):
        if pi not in utk:
            items.append({"kind": "use_extra", "engine": {"cp": p.start, "quote": _quote(text, p.start, p.end)}})
    for ai, pi in um_.items():
        au, pu = a_uses[ai], p_uses[pi]
        target = au.get("binds_to")
        if isinstance(target, dict) and ev.at_ok(text, target):
            if not any(s <= target["cp"] < max(e, s + 1) for s, e in pu.data["targets"]):
                items.append({"kind": "binding", "annotated": au, "engine_binding": pu.data["binding"]})
        elif target == "missing" and pu.data["binding"] not in ("definition_missing", "unbindable_name"):
            items.append({"kind": "binding", "annotated": au, "engine_binding": pu.data["binding"]})
        want, got = au.get("render_ref_id"), pu.data.get("ref_id")
        if want != got:
            items.append({"kind": "render_link", "annotated": au, "engine_ref_id": got})

    spans = [(i["at"]["cp"], i["at"]["cp"] + len(i["at"]["quote"]), i["scheme"]) for i in a_ids]
    im, itaken = ev.match_spans(spans, p_ids)
    for ai, a in enumerate(a_ids):
        if ai not in im:
            if a["role"] != "not_a_target":
                items.append({"kind": "identifier_missed", "annotated": a})
            continue
        p = p_ids[im[ai]]
        engine = {"cp": p.start, "quote": _quote(text, p.start, p.end), **p.data}
        if a["role"] == "not_a_target":
            items.append({"kind": "identifier_not_a_target_reported", "annotated": a, "engine": engine})
            continue
        if a.get("key") != p.data.get("key"):
            items.append({"kind": "identifier_key", "annotated": a, "engine": engine})
        if a["role"] != p.data["role"]:
            promotion = a["role"] in ev.NON_PROMOTABLE and p.data["role"] in ev.CITED_WORK_ROLES
            items.append(
                {"kind": "identifier_promotion" if promotion else "identifier_role", "annotated": a, "engine": engine}
            )
    for pi, p in enumerate(p_ids):
        if pi not in itaken:
            items.append(
                {
                    "kind": "identifier_extra",
                    "engine": {"cp": p.start, "quote": _quote(text, p.start, p.end), **p.data},
                }
            )
    return {"article": art.key, "window": list(win), "items": items}


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for split, entries in spec["splits"].items():
        out[split] = [
            article_items(Path(e["bundle"]), Path(e["locked"]), Path(e["extraction"]))
            for e in sorted(entries, key=lambda x: x["locked"])
        ]
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
