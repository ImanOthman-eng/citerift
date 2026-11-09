"""Unstructured-unit false positives of a scored run, with the frozen scorer's matching (exposed data, design only).

Usage: python campaign_false_positives.py SCORE_SPEC.json [locked|adjudicated] > campaign_false_positives.json
Run with the repository root as working directory (2026-11-03: the confirmation campaign's score_spec.json and
``adjudicated``).
"""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("docs/verification/stage-03/protocol/scripts").resolve()))
v1 = importlib.import_module("evaluate")
v2 = importlib.import_module("evaluate_v2")


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


spec = load(sys.argv[1])
LABEL = sys.argv[2] if len(sys.argv) > 2 else "locked"
out = []
for ents in spec["splits"].values():
    for e in ents:
        art = v1.load_bundle(Path(e["bundle"]))
        doc = load(e["extraction"])
        ann = load(e.get(LABEL) or e["locked"])
        pred = v2.engine_predictions_v2(doc, art.text)
        text, win = art.text, art.window
        a_defs = [d for d in ann["definitions"] if v1.at_ok(text, d["at"]) and v1.in_window(d["at"]["cp"], win)]
        p_defs = [p for p in pred.definitions if v1.in_window(p.start, win)]
        dm, _ = v1.match_points([(d["at"]["cp"], d) for d in a_defs], p_defs)
        inv = {pi: ai for ai, pi in dm.items()}
        uns_p = [
            p
            for p in pred.units
            if p.data["kind"] == "unstructured" and any(d.start <= p.start < max(d.end, d.start + 1) for d in p_defs)
        ]
        taken = set()
        for ai, d in enumerate(a_defs):
            if d.get("unstructured") and ai in dm:
                pd = p_defs[dm[ai]]
                hit = next(
                    (
                        k
                        for k, p in enumerate(uns_p)
                        if k not in taken and pd.start <= p.start < max(pd.end, pd.start + 1)
                    ),
                    None,
                )
                if hit is not None:
                    taken.add(hit)
        for k, p in enumerate(uns_p):
            if k in taken:
                continue
            cands = [i for i, d in enumerate(p_defs) if d.start <= p.start < max(d.end, d.start + 1)]
            pdi = max(cands, key=lambda i: p_defs[i].start)
            ad = a_defs[inv[pdi]] if pdi in inv else None
            if True:
                out.append(
                    {
                        "article": art.key,
                        "wiki": art.wiki,
                        "cp": p.start,
                        "cp_end": p.end,
                        "def_kind": p_defs[pdi].data["kind"],
                        "label": None
                        if ad is None
                        else {
                            "templates": [t["at"].get("quote") for t in ad.get("templates", [])],
                            "unstructured": ad.get("unstructured"),
                        },
                        "body": text[p.start : p.end][:400],
                    }
                )
print(json.dumps(out, ensure_ascii=False, indent=1))
