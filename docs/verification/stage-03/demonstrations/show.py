"""Print focused views of a Stage 03 extraction document for the five demonstrations (DEMONSTRATIONS.md).

Usage:
  python show.py marker EXTRACTION                 marker observations that are not plain negatives, with evidence
  python show.py reuse EXTRACTION NAME             one named reference: definitions, every use and its rendered marker
  python show.py roles EXTRACTION                  identifiers whose role is not primary_citation_field
  python show.py multiwork EXTRACTION              references holding more than one citation unit
  python show.py captures BUNDLE BUNDLE            two captures of one revision: identity, hashes, byte differences

It only reads JSON and retained bytes; it computes nothing that the extraction document does not state, except the
byte comparison of ``captures``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load(path: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def marker(doc: dict[str, Any]) -> list[dict[str, Any]]:
    containers = {c["id"]: c for c in doc["containers"]}
    out = []
    for m in doc["markers"]:
        if m["state"] == "no_recognized_warning_in_inspected_region" and not m["source_marker_templates"]:
            continue
        c = containers[m["container_id"]]
        out.append(
            {
                "container": c["id"],
                "name": c["name"],
                "source_span_cp": [c["source"]["cp_start"], c["source"]["cp_end"]],
                "source_marker_templates": m["source_marker_templates"],
                "state": m["state"],
                "reason": m["reason"],
                "rendered_region": (m["region"] or {}).get("region_id"),
                "evidence": [{k: e.get(k) for k in ("kind", "part", "matched", "exclusion")} for e in m["evidence"]],
                "browser_visibility": m["browser_visibility"],
            }
        )
    return out


def reuse(doc: dict[str, Any], name: str) -> dict[str, Any]:
    (c,) = [c for c in doc["containers"] if c["name"] == name]
    uses = {u["id"]: u for u in doc["uses"]}
    return {
        "container": c["id"],
        "kind": c["kind"],
        "binding_state": c["binding_state"],
        "definitions": [d["source"]["cp_start"] for d in c["definitions"]],
        "render": {k: c["render"].get(k) for k in ("state", "region_id")},
        "uses": [
            {
                "use": uid,
                "source_cp": uses[uid]["source"]["cp_start"],
                "binding": uses[uid]["binding"],
                "render_state": uses[uid]["render"]["state"],
                "rendered_marker": (uses[uid]["render"].get("locator") or {}).get("element_id"),
            }
            for uid in c["use_ids"]
        ],
    }


def roles(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "raw": i["source"]["raw"],
            "scheme": i["scheme"],
            "key": (i["normalization"] or {}).get("normalized"),
            "role": i["role"],
            "role_reason": i["role_reason"],
            "template": (i["context"]["template"] or {}).get("canonical"),
            "param": i["context"]["param"],
            "container": i["container_id"],
        }
        for i in doc["identifiers"]
        if i["role"] != "primary_citation_field"
    ]


def multiwork(doc: dict[str, Any]) -> list[dict[str, Any]]:
    units = {u["id"]: u for u in doc["units"]}
    idents = {i["id"]: i for i in doc["identifiers"]}
    out = []
    for c in doc["containers"]:
        if len(c["unit_ids"]) < 2:
            continue
        out.append(
            {
                "container": c["id"],
                "name": c["name"],
                "units": [
                    {
                        "unit": uid,
                        "kind": units[uid]["kind"],
                        "template": (units[uid].get("template") or {}).get("canonical"),
                        "identifiers": [
                            (
                                idents[i]["scheme"],
                                (idents[i]["normalization"] or {}).get("normalized"),
                                idents[i]["role"],
                            )
                            for i in units[uid]["identifier_ids"]
                        ],
                    }
                    for uid in c["unit_ids"]
                ],
                "issues": sorted({i["code"] for i in doc["issues"] if c["id"] in i["entities"]}),
            }
        )
    return out


def captures(a: Path, b: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    caps = [json.loads((p / "capture.json").read_text(encoding="utf-8")) for p in (a, b)]
    for label, cap in zip(("first", "second"), caps, strict=True):
        out[label] = {
            "revision_id": cap["page"]["revision_id"],
            "source_artifact": cap["source"]["artifact"],
            "render_artifact": cap["render"].get("artifact"),
            "render_retrieved": cap["render"].get("retrieved_at"),
            "started_at": cap.get("started_at"),
        }
    ha = (a / "artifacts" / caps[0]["render"]["artifact"]).read_bytes()
    hb = (b / "artifacts" / caps[1]["render"]["artifact"]).read_bytes()
    diff = [i for i, (x, y) in enumerate(zip(ha, hb, strict=False)) if x != y]
    out["same_source_bytes"] = caps[0]["source"]["artifact"] == caps[1]["source"]["artifact"]
    out["html_lengths"] = [len(ha), len(hb)]
    out["differing_html_bytes"] = len(diff)
    if diff:
        lo, hi = max(0, diff[0] - 50), diff[-1] + 30
        out["first_difference_context"] = [ha[lo:hi].decode("utf-8", "replace"), hb[lo:hi].decode("utf-8", "replace")]
    return out


BEFORE_KEYS = {
    "F1-en-span": "F1 en span",
    "F1-ar-comment": "F1 ar comment",
    "F2-en-red-link-label": "F2 en red link label",
    "F3-en-hidden-ancestor": "F3 en hidden ancestor",
    "F3-ar-hidden-ancestor": "F3 ar hidden ancestor",
    "F4-en-numbered-reuse": "F4 {{r|1=a}}",
    "F4-ar-numbered-reuse": "F4 ar {{استشهاد متعدد|1=a}}",
}


def synthetic(directory: Path, before_path: Path) -> dict[str, Any]:
    """SYNTHETIC F1-F4 cases: the reviewed head's output (F1-F4_before.json, 049c48c) beside this run's."""
    before = json.loads(before_path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"label": "SYNTHETIC inputs, not observed Wikipedia revisions"}
    for ext in sorted(directory.glob("F*.extraction.json")):
        name = ext.name.removesuffix(".extraction.json")
        doc = load(str(ext))
        after: dict[str, Any] = {"status": doc["status"]}
        if doc["markers"] and doc["markers"][0]["region"] is not None:
            m = doc["markers"][0]
            after["state"] = m["state"]
            after["evidence"] = [
                {k: e.get(k) for k in ("kind", "part", "matched", "exclusion", "hidden_basis", "target") if e.get(k)}
                for e in m["evidence"]
            ]
            after["hidden_elements"] = m["region"]["hidden_elements"]
        else:
            after["uses"] = [[u["origin"], u["name"], u["binding"]] for u in doc["uses"]]
        out[name] = {
            "before_at_049c48c": before.get(BEFORE_KEYS.get(name, ""), "control (no before case)"),
            "after": after,
        }
    return out


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "marker":
        result: Any = marker(load(sys.argv[2]))
    elif cmd == "reuse":
        result = reuse(load(sys.argv[2]), sys.argv[3])
    elif cmd == "roles":
        result = roles(load(sys.argv[2]))
    elif cmd == "multiwork":
        result = multiwork(load(sys.argv[2]))
    elif cmd == "captures":
        result = captures(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "synthetic":
        result = synthetic(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(f"unknown command {cmd!r}")
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
