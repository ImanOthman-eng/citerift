"""The ACQUIRE bundle observation: a closed manifest over raw retained blobs (Stage 04 Step 8, inherited finding IF-7).

A committed ACQUIRE records one bundle observation (``obs_kind = bundle``). Its blob is a small canonical manifest
(``urn:citerift:schema:investigation:v1:bundle-observation``) that names, by digest and size:

- the exact Stage 03 ``capture.json`` bytes, retained as a raw blob whose digest is the Stage 03 ``capture_sha256``
  (and so the root's capture identity, F-15);
- a canonical artifact-set blob (``bundle-artifact-set``) that lists every artifact ``capture.json`` lists, each
  retained as a raw blob.

Every artifact the capture lists is retained, not only the ones EXTRACT reads: Stage 03 ``verify_capture`` (used by
VERIFY, SPEC 9.7) reads and hashes every listed artifact and refuses an unlisted one, so a reconstruction from Memory
must hold exactly that set. Nothing else is copied (no attempt list, no issue list; those stay inside the retained
``capture.json`` bytes). The manifest has no unbounded list, so its size has a fixed maximum
(``docs/verification/stage-04/review/step8/if7_bound.json``).

This module holds the pure checks shared by Investigation Memory (M-3 on append and on open) and VERIFY. It reads no
file and imports no engine.
"""

from __future__ import annotations

from typing import Any

from citerift.investigation.schemas import BUNDLE_ARTIFACT_SET, BUNDLE_OBSERVATION, problems

MANIFEST_SCHEMA = BUNDLE_OBSERVATION
SET_SCHEMA = BUNDLE_ARTIFACT_SET
SCHEMA_VERSION = "1.0.0"
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024  # the limit Stage 03 verify_capture reads every listed artifact with
ROLES = ("failure", "render", "source", "source_response")


def manifest_problem(manifest: Any) -> str | None:
    """The first problem of a bundle observation manifest, or None."""
    found = problems(manifest, MANIFEST_SCHEMA)
    if found:
        return "; ".join(found[:3])
    if manifest["capture"]["blob"] != manifest["identity"]["capture_sha256"]:
        return "the capture blob is not the identity's capture_sha256"
    render = manifest["render"]
    if (render["artifact"] is not None) != (render["state"] in ("captured", "rejected")):
        return "a render artifact goes with a captured or rejected render, and only with it"
    if manifest["status"] != ("complete" if render["state"] in ("not_requested", "captured") else "partial"):
        return "the capture status does not follow the render state"
    return None


def set_problem(value: Any, manifest: dict[str, Any]) -> str | None:
    """The first problem of an artifact set against its (valid) manifest, or None."""
    found = problems(value, SET_SCHEMA)
    if found:
        return "; ".join(found[:3])
    arts = value["artifacts"]
    digests = [a["sha256"] for a in arts]
    if digests != sorted(set(digests)):
        return "artifacts are not sorted by digest and unique"
    if any(a["roles"] != sorted(set(a["roles"])) for a in arts):
        return "roles are not sorted and unique"
    ref = manifest["artifact_set"]
    if ref["count"] != len(arts) or ref["bytes"] != sum(a["bytes"] for a in arts):
        return "the manifest's artifact count or bytes are not the set's"
    by_role: dict[str, list[dict[str, Any]]] = {r: [] for r in ROLES}
    for a in arts:
        for r in a["roles"]:
            by_role[r].append(a)
    src = manifest["source"]
    expected = {"source": [src["artifact"]], "source_response": [src["response_artifact"]]}
    expected["render"] = [manifest["render"]["artifact"]] if manifest["render"]["artifact"] is not None else []
    for role, want in expected.items():
        if [a["sha256"] for a in by_role[role]] != want:
            return f"the set's {role} artifact is not the manifest's"
    if by_role["source"][0]["bytes"] != src["bytes"]:
        return "the source artifact size is not the manifest's"
    if len(by_role["failure"]) != manifest["failure_artifact_count"]:
        return "the number of failure artifacts is not the manifest's"
    return None


def listed_artifacts(capture: dict[str, Any]) -> dict[str, list[str]]:
    """Every artifact a (schema-valid) Stage 03 capture document lists, with its roles: the set Stage 03
    ``verify_capture`` reads (``citerift.wiki.verify``, ``_listed_artifacts``), re-derived here from the capture
    schema's fields because that function is private."""
    roles: dict[str, set[str]] = {}

    def add(sha: Any, role: str) -> None:
        if isinstance(sha, str):
            roles.setdefault(sha, set()).add(role)

    for sha in capture.get("failure_artifacts") or []:
        add(sha, "failure")
    source = capture.get("source") or {}
    add(source.get("artifact"), "source")
    add(source.get("response_artifact"), "source_response")
    render = capture.get("render") or {}
    add(render.get("artifact"), "render")
    add(render.get("response_artifact"), "render")
    return {sha: sorted(r) for sha, r in sorted(roles.items())}


def raw_references(manifest: dict[str, Any], artifact_set: dict[str, Any] | None) -> list[tuple[str, int]]:
    """The raw blobs a manifest names, with their sizes: the capture document, then every artifact of the set."""
    out = [(manifest["capture"]["blob"], manifest["capture"]["bytes"])]
    if artifact_set is not None:
        out += [(a["sha256"], a["bytes"]) for a in artifact_set["artifacts"]]
    return out
