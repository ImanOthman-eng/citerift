"""Stage 03 calibration: lxml versus selectolax (Lexbor) on identical retained Parsoid HTML.

For every retained HTML artifact, each parser extracts the same structural facts:
  - every element id, and the ids that occur more than once;
  - reference uses (typeof contains mw:Extension/ref): id, href target, data-mw name/group;
  - reference list items (li inside an element whose typeof contains mw:Extension/references; Parsoid puts
    the typeof on the ol or on a wrapping div): id and backlink targets;
  - transclusion elements (typeof contains mw:Transclusion): data-mw template targets;
  - the text content of every reference list item (Arabic and other Unicode kept as is);
and both are timed (wall and CPU, 5 runs each, after one warm-up) with peak RSS measured in a fresh process.
Disagreements are listed for direct inspection; agreement is not independent validation.

Run in an isolated environment that has both parsers (never the project environment):
  python parser_qualification.py ARTIFACT_DIR OUT.json [SYNTHETIC_DIR]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _dm(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except ValueError:
        return {"invalid": True}
    return value if isinstance(value, dict) else {"invalid": True}


def facts_lxml(data: bytes) -> dict[str, Any]:
    import lxml.html  # noqa: PLC0415 - each parser is imported only by the measurement that uses it

    doc = lxml.html.document_fromstring(data)
    ids = Counter(el.get("id") for el in doc.iter() if isinstance(el.tag, str) and el.get("id"))
    uses, notes, trans, texts = [], [], [], {}
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        ty = (el.get("typeof") or "").split()
        if "mw:Extension/ref" in ty:
            a = el.find(".//a")
            dm = _dm(el.get("data-mw"))
            uses.append([el.get("id"), a.get("href") if a is not None else None, dm.get("attrs", {})])
        if "mw:Transclusion" in ty:
            dm = _dm(el.get("data-mw"))
            trans.append(
                [
                    p["template"]["target"]["wt"].strip()
                    for p in dm.get("parts", [])
                    if isinstance(p, dict) and "template" in p
                ]
            )
        if "mw:Extension/references" in ty:
            for li in el.iter("li"):
                back = [a.get("href") for a in li.iter("a") if a.get("rel") == "mw:referencedBy"]
                notes.append([li.get("id"), back])
                texts[li.get("id")] = " ".join(li.text_content().split())
    return {
        "ids": len(ids),
        "dup_ids": sorted(k for k, v in ids.items() if v > 1),
        "uses": uses,
        "notes": notes,
        "transclusions": trans,
        "note_texts": texts,
    }


def facts_lexbor(data: bytes) -> dict[str, Any]:
    from selectolax.lexbor import LexborHTMLParser  # noqa: PLC0415

    tree = LexborHTMLParser(data.decode("utf-8"))
    ids: Counter[str] = Counter()
    uses, notes, trans, texts = [], [], [], {}
    for el in tree.root.traverse(include_text=False):
        attrs = el.attributes
        if attrs.get("id"):
            ids[attrs["id"]] += 1
        ty = (attrs.get("typeof") or "").split()
        if "mw:Extension/ref" in ty:
            a = el.css_first("a")
            dm = _dm(attrs.get("data-mw"))
            uses.append([attrs.get("id"), a.attributes.get("href") if a is not None else None, dm.get("attrs", {})])
        if "mw:Transclusion" in ty:
            dm = _dm(attrs.get("data-mw"))
            trans.append(
                [
                    p["template"]["target"]["wt"].strip()
                    for p in dm.get("parts", [])
                    if isinstance(p, dict) and "template" in p
                ]
            )
        if "mw:Extension/references" in ty:
            for li in el.traverse(include_text=False):  # iter() only yields direct children in selectolax
                if li.tag != "li":
                    continue
                back = [a.attributes.get("href") for a in li.css("a") if a.attributes.get("rel") == "mw:referencedBy"]
                notes.append([li.attributes.get("id"), back])
                texts[li.attributes.get("id")] = " ".join(li.text(deep=True).split())
    return {
        "ids": len(ids),
        "dup_ids": sorted(k for k, v in ids.items() if v > 1),
        "uses": uses,
        "notes": notes,
        "transclusions": trans,
        "note_texts": texts,
    }


PARSERS = {"lxml": facts_lxml, "lexbor": facts_lexbor}


def measure(name: str, path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    # Linux keeps ru_maxrss across fork and exec, so the parent's peak would leak into this process's figure.
    # Writing 5 to clear_refs resets the peak (VmHWM); the peak is then read from /proc/self/status.
    with open("/proc/self/clear_refs", "w") as f:
        f.write("5")
    fn = PARSERS[name]
    fn(data)
    walls, cpus = [], []
    for _ in range(5):
        w0, c0 = time.perf_counter(), time.process_time()
        fn(data)
        walls.append(time.perf_counter() - w0)
        cpus.append(time.process_time() - c0)
    status = Path("/proc/self/status").read_text()
    hwm = next(int(line.split()[1]) for line in status.splitlines() if line.startswith("VmHWM:"))
    return {"wall_s": sorted(walls)[2], "cpu_s": sorted(cpus)[2], "peak_rss_kib": hwm}


def main() -> int:
    if sys.argv[1] == "--measure":
        print(json.dumps(measure(sys.argv[2], sys.argv[3])))
        return 0
    art, out = sys.argv[1], sys.argv[2]
    rows = []
    paths = []
    for name in sorted(os.listdir(art)):
        path = os.path.join(art, name)
        data = Path(path).read_bytes()
        if data.startswith(b"<!DOCTYPE html>"):
            paths.append((name, path, data))
    # Malformed variants derived from the first artifact: truncated mid-document, an unclosed element run, and
    # an invalid data-mw attribute. Both parsers must recover without raising; their recoveries are compared.
    if paths and len(sys.argv) > 3:
        base = max(paths, key=lambda p: len(p[2]))[2]
        synth_dir = sys.argv[3]
        os.makedirs(synth_dir, exist_ok=True)
        variants = {
            "synthetic-truncated": base[: len(base) // 2],
            "synthetic-unclosed": base.replace(b"</li>", b"", 50),
            "synthetic-bad-data-mw": base.replace(b"data-mw='{", b"data-mw='{,", 20),
        }
        for vname, vdata in variants.items():
            vpath = os.path.join(synth_dir, vname)
            Path(vpath).write_bytes(vdata)
            paths.append((vname, vpath, vdata))
    for name, path, data in paths:
        try:
            a = facts_lxml(data)
        except Exception as e:
            a = {"error": repr(e)}
        try:
            b = facts_lexbor(data)
        except Exception as e:
            b = {"error": repr(e)}
        if "error" in a or "error" in b:
            rows.append(
                {"artifact": name, "bytes": len(data), "lxml_error": a.get("error"), "lexbor_error": b.get("error")}
            )
            continue
        diffs = {
            k: (a[k] if k != "note_texts" else len(a[k]), b[k] if k != "note_texts" else len(b[k]))
            for k in a
            if a[k] != b[k] and k != "note_texts"
        }
        text_diffs = [k for k in a["note_texts"] if a["note_texts"].get(k) != b["note_texts"].get(k)]
        perf = {}
        for p in PARSERS:
            r = subprocess.run(  # noqa: S603 - this script, with the running interpreter
                [sys.executable, __file__, "--measure", p, path], capture_output=True, text=True, check=True
            )
            perf[p] = json.loads(r.stdout)
        rows.append(
            {
                "artifact": name,
                "bytes": len(data),
                "uses": len(a["uses"]),
                "notes": len(a["notes"]),
                "transclusions": len(a["transclusions"]),
                "dup_ids_lxml": a["dup_ids"],
                "dup_ids_lexbor": b["dup_ids"],
                "structural_differences": diffs,
                "note_text_differences": text_diffs[:20],
                "note_text_difference_count": len(text_diffs),
                "performance": perf,
            }
        )
    Path(out).write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
