"""Self-test of evaluate.py on DEVELOPMENT bundles (not an evaluation: the labels here are derived from the engine).

Usage: python selftest_evaluate.py BUNDLE EXTRACTION

1. Labels copied from the engine's own extraction must score precision = recall = 1 with no key, role, binding,
   render or marker disagreement (checks the matching and counting code).
2. Each perturbation (drop a use, drop a definition, change a key, turn a cited-work role into a marker target,
   change a render id, flip a marker to warning, add a non-target identifier the engine reported) must move exactly
   the metric it targets.
3. B1 and B0 run and report.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import ENGINE_MARKER, b1_predictions, engine_predictions, load_bundle, score_article

TEMPLATE_UNITS = ("citation_template", "external_data_template")


def labels_from_engine(art: Any, doc: dict[str, Any]) -> dict[str, Any]:
    text = art.text

    def at(cp: int, length: int = 12) -> dict[str, Any]:
        return {"cp": cp, "quote": text[cp : cp + length]}

    markers = {m["container_id"]: ENGINE_MARKER[m["state"]] for m in doc["markers"]}
    units_by_def: dict[str, list[dict[str, Any]]] = {}
    for un in doc["units"]:
        units_by_def.setdefault(un["definition_id"] or un["container_id"], []).append(un)
    defs = []
    for c in doc["containers"]:
        items = [(d["id"], d["source"]) for d in c["definitions"]] or [(c["id"], c["source"])]
        for did, src in items:
            uns = units_by_def.get(did, [])
            defs.append(
                {
                    "id": did,
                    "at": at(src["cp_start"]),
                    "kind": c["kind"],
                    "name": c["name"],
                    "group": c["group"],
                    "templates": [{"at": at(u["source"]["cp_start"])} for u in uns if u["kind"] in TEMPLATE_UNITS],
                    "unstructured": any(u["kind"] == "unstructured_text" for u in uns),
                    "render_note_id": c["render"]["region_id"] if c["render"]["state"] == "matched" else None,
                    "marker": markers.get(c["id"], "not_inspected"),
                }
            )
    first = {
        c["id"]: (c["definitions"][0]["source"] if c["definitions"] else c["source"])["cp_start"]
        for c in doc["containers"]
    }
    uses = []
    for u in doc["uses"]:
        r = u["render"]
        target: Any = "missing" if u["binding"] in ("definition_missing", "unbindable_name") else None
        if u["container_id"] in first:
            target = at(first[u["container_id"]])
        uses.append(
            {
                "id": u["id"],
                "at": at(u["source"]["cp_start"]),
                "binds_to": target,
                "render_ref_id": r["locator"]["element_id"] if r["state"] == "matched" and r.get("locator") else None,
            }
        )
    idents = [
        {
            "at": at(i["source"]["cp_start"], i["source"]["cp_end"] - i["source"]["cp_start"]),
            "scheme": i["scheme"],
            "role": i["role"],
            "key": i["normalization"]["normalized"],
        }
        for i in doc["identifiers"]
    ]
    return {
        "article": {
            "wiki": art.wiki,
            "revision_id": art.revision_id,
            "source_sha256": art.source_sha256,
            "window": list(art.window),
        },
        "definitions": defs,
        "uses": uses,
        "identifiers": idents,
    }


def summary(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "definitions": (r["definitions"]["tp"], r["definitions"]["fp"], r["definitions"]["fn"]),
        "units": (r["units"]["tp"], r["units"]["fp"], r["units"]["fn"]),
        "uses": (r["uses"]["tp"], r["uses"]["fp"], r["uses"]["fn"]),
        "binding": (r["uses"]["binding"]["correct"], r["uses"]["binding"]["total"]),
        "identifiers": (r["identifiers"]["tp"], r["identifiers"]["fp"], r["identifiers"]["fn"]),
        "key_errors": r["identifiers"]["key_errors"],
        "promotions": r["identifiers"]["promotions"],
        "role": (r["identifiers"]["role_agree"], r["identifiers"]["role_total"]),
        "render": (r["render"]["correct"], r["render"]["false_attachments"], r["render"]["abstained"]),
        "fabricated_negatives": r["markers"]["fabricated_negatives"],
        "invalid": len(r["invalid_annotations"]),
    }


def main() -> int:
    art = load_bundle(Path(sys.argv[1]))
    doc = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    pred = engine_predictions(doc)
    ann = labels_from_engine(art, doc)
    base = summary(score_article(art, ann, pred))
    print("identity", json.dumps(base))
    ok = base["key_errors"] == 0 and base["promotions"] == 0 and base["invalid"] == 0
    ok &= all(base[k][1] == 0 and base[k][2] == 0 for k in ("definitions", "units", "uses", "identifiers"))
    ok &= base["binding"][0] == base["binding"][1] and base["role"][0] == base["role"][1]
    ok &= base["render"][1] == 0 and base["render"][2] == 0

    def perturbed(name: str, change: Any, expect: Any) -> None:
        nonlocal ok
        a = copy.deepcopy(ann)
        try:
            change(a)
        except (IndexError, StopIteration):
            print(name, "not applicable: no such item in the window")
            return
        got = summary(score_article(art, a, pred))
        passed = expect(got)
        ok &= passed
        print(name, "ok" if passed else "FAILED", json.dumps(got))

    ws, we = art.window
    in_win = [k for k, u in enumerate(ann["uses"]) if ws <= u["at"]["cp"] < we]
    dfs = [k for k, d in enumerate(ann["definitions"]) if ws <= d["at"]["cp"] < we]
    cited = [
        k
        for k, i in enumerate(ann["identifiers"])
        if ws <= i["at"]["cp"] < we and i["role"] in ("primary_citation_field", "identifier_link")
    ]
    linked = [k for k in in_win if ann["uses"][k]["render_ref_id"]]
    perturbed("drop_use", lambda a: a["uses"].pop(in_win[0]), lambda g: g["uses"][1] == 1 and g["uses"][2] == 0)
    perturbed(
        "drop_definition",
        lambda a: a["definitions"].pop(dfs[0]),
        lambda g: g["definitions"][1] == 1,
    )
    perturbed(
        "key_change",
        lambda a: a["identifiers"][cited[0]].__setitem__("key", "10.0000/other"),
        lambda g: g["key_errors"] == 1,
    )
    perturbed(
        "promotion",
        lambda a: a["identifiers"][cited[0]].__setitem__("role", "marker_target"),
        lambda g: g["promotions"] == 1 and g["role"][0] == g["role"][1] - 1,
    )
    perturbed(
        "non_target",
        lambda a: a["identifiers"][cited[0]].__setitem__("role", "not_a_target"),
        lambda g: (
            g["identifiers"][1] == base["identifiers"][1] + 1 and g["identifiers"][0] == base["identifiers"][0] - 1
        ),
    )
    if linked:
        perturbed(
            "render_id",
            lambda a: a["uses"][linked[0]].__setitem__("render_ref_id", "cite_ref-other"),
            lambda g: g["render"][1] == 1,
        )
    perturbed(
        "marker_warning",
        lambda a: next(d for d in a["definitions"] if ws <= d["at"]["cp"] < we and d["marker"] == "none").__setitem__(
            "marker", "warning"
        ),
        lambda g: g["fabricated_negatives"] == 1,
    )
    perturbed(
        "bad_quote",
        lambda a: a["identifiers"][cited[0]]["at"].__setitem__("quote", "\u0000"),
        lambda g: g["invalid"] == 1,
    )
    print("b1_vs_engine_labels", json.dumps(summary(score_article(art, ann, b1_predictions(art)))))
    print("selftest", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
