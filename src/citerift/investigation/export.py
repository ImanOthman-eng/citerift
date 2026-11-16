"""The user export of a verified investigation (Step 10, owner items 14 and 15; SPEC S-9.7, 11.1, 11.2).

The authoritative report is the D-054 graph in Investigation Memory. The export is derived from it and never replaces
it. It is written only after the export gate passed (``operations.export``: ``verify`` gives ``passed``, so ASSEMBLE
and VERIFY committed, the lifecycle is ``COMPLETED`` or ``NEEDS_RESOLUTION`` and every check holds now) and only to
the directory the user names (``outputs.write_tree``).

Output is never flattened into one unbounded document: the export is a directory graph with the same bounded parts
as the report, and every component is present.

- ``export.json``: the export manifest: format and version, identities, lifecycle, report digest, projection-set
  digest, ``created_at`` (from the journal), the S-7.7 summary statement, the limitation statements and, for every
  other file, its path, SHA-256 and size;
- ``report/<digest>.json``: the report manifest and every chunk it names, as stored (file name = blob digest);
- ``evidence/<digest>.json``: every committed evidence batch the report names;
- ``observations/<digest>.json``: every observation blob the observations component names;
- ``explanations/<digest>.json``: the fixed-template explanations of the claims of one claims chunk (named by that
  chunk's digest, in the chunk's order);
- ``v1/<digest>.json``: one v1 record per projection, the stored body plus ``created_at`` (named by the body
  digest the projection set lists; validated against the unchanged v1 contract before anything is written);
- ``projection_set.json``: the projection set as stored.

No raw capture artifact (wikitext or HTML) is exported.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from citerift.investigation import explanations, projections
from citerift.investigation.canonical import canon
from citerift.investigation.memory import InvestigationMemory
from citerift.investigation.outputs import OperationError, target, write_tree

FORMAT = "citerift-investigation-export"
FORMAT_VERSION = "1"


def check_target(out: Path, memory_root: Path) -> None:
    target(out, memory_root)


def _pretty(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def files(mem: InvestigationMemory) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Every file of the export and the export manifest's content (without its file list)."""
    f = mem.view
    rec = next(r for r in f.committed_content() if r["kind"] == "report_recorded")["payload"]
    out: dict[str, bytes] = {}
    manifest_bytes = mem.blobs.get(rec["report"])
    manifest = json.loads(manifest_bytes)
    out[f"report/{rec['report']}.json"] = manifest_bytes
    claims: list[dict[str, Any]] = []
    for part in ("claims", "observations", "positive_works"):
        for ref in manifest["components"][part]["chunks"]:
            data = mem.blobs.get(ref["chunk"])
            out[f"report/{ref['chunk']}.json"] = data
            if part == "claims":
                items = json.loads(data)["items"]
                claims += [e["claim"] for e in items]
                expl = [explanations.claim_explanation(e) for e in items]
                out[f"explanations/{ref['chunk']}.json"] = _pretty({"chunk": ref["chunk"], "explanations": expl})
            if part == "observations":
                for item in json.loads(data)["items"]:
                    out[f"observations/{item['blob']}.json"] = mem.blobs.get(item["blob"])
    for b in manifest["components"]["evidence"]["batches"]:
        out[f"evidence/{b['batch']}.json"] = mem.blobs.get(b["batch"])
    created_at = f.records[0]["at"]
    pset_bytes = mem.blobs.get(rec["projection_set"])
    out["projection_set.json"] = pset_bytes
    for d in json.loads(pset_bytes)["projections"]:
        body = json.loads(mem.blobs.get(d))
        record = projections.v1_record(body, created_at)
        found = projections.record_problems(record)
        if found:
            raise OperationError("verify_failed", "V1_PROJECTION_INVALID", f"projection {d}: {found[0]}")
        out[f"v1/{d}.json"] = _pretty(record)
    about = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "investigation_key": manifest["investigation_key"],
        "investigation_id": manifest["investigation_id"],
        "lifecycle": f.lifecycle(),
        "terminal_state": manifest["terminal_state"],
        "outcome": manifest["outcome"],
        "created_at": created_at,
        "report": rec["report"],
        "projection_set": rec["projection_set"],
        "projection_count": rec["projection_count"],
        "content_digest": f.content_digest(),
        "summary": explanations.summary_statement(manifest, manifest["components"]["positive_works"]["count"]),
        "limitations": explanations.limitations(manifest, claims),
        "authoritative": "The authoritative report is the D-054 graph in Investigation Memory; this export is "
        "derived from it.",
    }
    return out, about


def write(mem: InvestigationMemory, out: Path, memory_root: Path) -> dict[str, Any]:
    entries, about = files(mem)
    listing = [
        {"path": p, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for p, d in sorted(entries.items())
    ]
    manifest = {**about, "files": listing}
    entries["export.json"] = _pretty(manifest)
    write_tree(out, entries, memory_root)
    return {
        "files": len(entries),
        "bytes": sum(len(d) for d in entries.values()),
        "export_manifest_sha256": hashlib.sha256(entries["export.json"]).hexdigest(),
        "report": about["report"],
        "projection_set": about["projection_set"],
        "canonical_manifest_digest": hashlib.sha256(canon(manifest)).hexdigest(),
    }
