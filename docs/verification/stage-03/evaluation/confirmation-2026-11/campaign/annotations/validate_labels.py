"""Format, quote and window check of evaluator label files (AMENDMENT_2026-11-02_CONFIRMATION.md section 7).

Usage (from the repository root): python validate_labels.py PACKETS_DIR OUT_DIR

Checks only what section 7 lets the executor check, and changes nothing:

- one label file per packet, named ``<wiki>-<revision_id>.json``, and no other file;
- the format name and the keys of the guide's section 4;
- ``article``: wiki, revision_id, source_sha256, html_sha256 and window equal to ``packet.json``;
- every ``at`` and ``binds_to`` (definitions, their templates, uses, identifiers) is a non-empty quote that occurs
  at its code point in ``source.wikitext``;
- role, scheme and marker values are those of the guide.

Prints one JSON report; exit 0 when every file is valid, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROLES = {
    "primary_citation_field",
    "identifier_link",
    "labeled_reference_text",
    "marker_target",
    "textual_mention",
    "unresolved",
    "not_a_target",
}
MARKERS = {"warning", "ambiguous", "missing_template_link_only", "none", "not_inspected", "cannot_tell"}
SCHEMES = {"doi", "pmid"}


def _at(text: str, at: Any) -> bool:
    if not isinstance(at, dict):
        return False
    cp, q = at.get("cp"), at.get("quote")
    if not isinstance(cp, int) or isinstance(cp, bool) or not isinstance(q, str) or q == "":
        return False
    return text[cp : cp + len(q)] == q


def check(packet: Path, label: Path) -> list[str]:
    info = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    text = (packet / "source.wikitext").read_text(encoding="utf-8")
    try:
        ann = json.loads(label.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"not JSON: {exc}"]
    p: list[str] = []
    if ann.get("format") != "citerift-stage03-annotation-v1":
        p.append("format")
    for k in ("article", "provenance", "definitions", "uses", "identifiers", "unresolved_notes"):
        if k not in ann:
            p.append(f"missing key {k}")
    if p:
        return p
    a = ann["article"]
    win = [info["window"]["cp_start"], info["window"]["cp_end"]]
    for k, want in (
        ("wiki", info["wiki"]),
        ("revision_id", info["revision_id"]),
        ("source_sha256", info["source_sha256"]),
        ("html_sha256", info["html_sha256"]),
        ("window", win),
    ):
        if a.get(k) != want:
            p.append(f"article.{k} is {a.get(k)!r}, packet has {want!r}")
    for d in ann["definitions"]:
        if not _at(text, d.get("at")):
            p.append(f"definition {d.get('id')}: quote not at cp")
        for t in d.get("templates", []):
            if not _at(text, t.get("at")):
                p.append(f"template in {d.get('id')}: quote not at cp")
        if d.get("marker") not in MARKERS:
            p.append(f"definition {d.get('id')}: marker {d.get('marker')!r}")
    for u in ann["uses"]:
        if not _at(text, u.get("at")):
            p.append(f"use {u.get('id')}: quote not at cp")
        if u.get("binds_to") is not None and not _at(text, u.get("binds_to")):
            p.append(f"use {u.get('id')}: binds_to quote not at cp")
    for i, it in enumerate(ann["identifiers"]):
        if not _at(text, it.get("at")):
            p.append(f"identifier {i}: quote not at cp")
        if it.get("scheme") not in SCHEMES:
            p.append(f"identifier {i}: scheme {it.get('scheme')!r}")
        if it.get("role") not in ROLES:
            p.append(f"identifier {i}: role {it.get('role')!r}")
    return p


def main() -> int:
    packets, out = Path(sys.argv[1]), Path(sys.argv[2])
    names = sorted(d.name for d in packets.iterdir() if d.is_dir())
    files = sorted(f.name for f in out.iterdir() if f.is_file())
    report: dict[str, Any] = {"missing": [], "extra": [], "problems": {}}
    report["missing"] = [n for n in names if f"{n}.json" not in files]
    report["extra"] = [f for f in files if f.removesuffix(".json") not in names]
    for n in names:
        if f"{n}.json" in files:
            prob = check(packets / n, out / f"{n}.json")
            if prob:
                report["problems"][n] = prob
    ok = not (report["missing"] or report["extra"] or report["problems"])
    report["valid"] = ok
    sys.stdout.write(json.dumps(report, indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
