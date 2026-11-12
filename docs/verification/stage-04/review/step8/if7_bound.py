"""IF-7 size bound of the ACQUIRE bundle observation (Stage 04 Step 8, owner item 2).

Builds the largest instances the schemas allow, checks them against the schemas, and measures their canonical bytes:

- the manifest (``bundle-observation``): every string at its maximum length in the widest UTF-8 form the canonical
  encoding keeps (4-byte code points; ``ensure_ascii=False``), every integer at its maximum;
- the artifact set (``bundle-artifact-set``): the maximum count, every entry with the largest size and all four roles;
- the journal record that commits the manifest (``observation_recorded``): it holds only the manifest digest.

It also derives, from Stage 03's own limits, the count bound the schema states for failure artifacts and the most raw
bytes one investigation can retain. Writes ``if7_bound.json`` beside itself.

Run: ``uv run python docs/verification/stage-04/review/step8/if7_bound.py``
"""

from __future__ import annotations

import json
from pathlib import Path

from citerift.investigation.blobs import MAX_BLOB_BYTES
from citerift.investigation.canonical import canon
from citerift.investigation.journal import MAX_RECORD_BYTES
from citerift.investigation.retained import MAX_ARTIFACT_BYTES, ROLES
from citerift.investigation.schemas import BUNDLE_ARTIFACT_SET, BUNDLE_OBSERVATION, problems
from citerift.wiki.bundle import MAX_CAPTURE_JSON
from citerift.wiki.capture import MAX_SOURCE_BYTES
from citerift.wiki.fetch import MAX_FAILURE_BODY, FetchPolicy
from citerift.wiki.profile import SUPPORTED_WIKIS

HEX = "f" * 64
MAX_ID = 9007199254740991
WIDE = "\U0001f600"  # 4 bytes in UTF-8, kept unescaped by the canonical encoding


def worst_manifest(count: int, total: int) -> dict[str, object]:
    wiki = max(SUPPORTED_WIKIS, key=len)
    return {
        "schema": BUNDLE_OBSERVATION,
        "schema_version": "1.0.0",
        "engine": "citerift.wiki",
        "capture": {"blob": HEX, "bytes": MAX_CAPTURE_JSON, "schema_version": "9999.9999.9999"},
        "status": "partial",
        "identity": {"wiki": wiki, "page_id": MAX_ID, "revision_id": MAX_ID, "capture_sha256": HEX},
        "display": {"title": WIDE * 1024, "revision_sha1": "f" * 40},
        "source": {"artifact": HEX, "bytes": MAX_SOURCE_BYTES, "response_artifact": HEX},
        "render": {"state": "rejected", "artifact": HEX},
        "failure_artifact_count": 65536,
        "artifact_set": {"blob": HEX, "count": count, "bytes": total},
    }


def main() -> int:
    count = 65539
    entry = {"sha256": HEX, "bytes": MAX_ARTIFACT_BYTES, "roles": list(ROLES)}
    one = len(canon(entry))
    artifact_set = {"schema": BUNDLE_ARTIFACT_SET, "schema_version": "1.0.0", "artifacts": [entry] * 2}
    set_problems = problems(artifact_set, BUNDLE_ARTIFACT_SET)  # the schema shape (uniqueness is checked elsewhere)
    set_bytes = len(canon(artifact_set)) + (count - 2) * (one + 1)
    schema_max_total = count * MAX_ARTIFACT_BYTES
    manifest = worst_manifest(count, schema_max_total)
    manifest_problems = problems(manifest, BUNDLE_OBSERVATION)
    manifest_bytes = len(canon(manifest))
    record = {
        "obs_kind": "bundle",
        "blob": HEX,
        "source_ref": {"engine": "citerift.wiki", "operation": "open_bundle", "locator": None},
    }
    listed = len(json.dumps(HEX)) + 1  # one failure_artifacts entry in capture.json: the quoted digest and a comma
    failures_by_capture = MAX_CAPTURE_JSON // listed
    policy = FetchPolicy()
    attempts = policy.max_attempts * 2  # the source and the render operation
    practical = {
        "capture_json": MAX_CAPTURE_JSON,
        "source_text": MAX_SOURCE_BYTES,
        "source_response": policy.max_body_bytes,
        "render_html": policy.max_body_bytes,
        "failure_bodies": attempts * MAX_FAILURE_BODY,
    }
    out = {
        "manifest": {
            "worst_case_bytes": manifest_bytes,
            "schema_valid": not manifest_problems,
            "problems": manifest_problems,
            "unbounded_lists": 0,
        },
        "artifact_set": {
            "max_count": count,
            "count_derivation": (
                f"failure_artifacts: capture.json is at most {MAX_CAPTURE_JSON} bytes and each listed digest takes at "
                f"least {listed} bytes, so at most {failures_by_capture} (< 65536 in the schema); plus source, "
                "source_response and render: 65539"
            ),
            "entry_bytes": one,
            "worst_case_bytes": set_bytes,
            "blob_limit_bytes": MAX_BLOB_BYTES,
            "within_blob_limit": set_bytes <= MAX_BLOB_BYTES,
            "schema_shape_valid": not set_problems,
        },
        "journal_record": {
            "payload_bytes": len(canon(record)),
            "record_limit_bytes": MAX_RECORD_BYTES,
            "note": "the record names the manifest by digest; nothing in it grows with the bundle",
        },
        "raw_blobs": {
            "per_artifact_limit_bytes": MAX_ARTIFACT_BYTES,
            "capture_json_limit_bytes": MAX_CAPTURE_JSON,
            "schema_bound_total_bytes": MAX_CAPTURE_JSON + schema_max_total,
            "stage03_practical_total_bytes": sum(practical.values()),
            "stage03_practical_parts": practical,
            "stage03_practical_note": (
                "Stage 03 keeps a failure body only when it is at most MAX_FAILURE_BODY bytes, one per failed "
                f"attempt, and makes at most max_attempts={policy.max_attempts} attempts for each of its two "
                "operations under the default policy"
            ),
        },
    }
    path = Path(__file__).with_suffix(".json")
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({"manifest": manifest_bytes, "set": set_bytes, "valid": not manifest_problems and not set_problems})
    )
    return 0 if not manifest_problems and not set_problems and set_bytes <= MAX_BLOB_BYTES else 1


if __name__ == "__main__":
    raise SystemExit(main())
