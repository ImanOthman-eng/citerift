"""ACQUIRE of a retained Stage 03 bundle, and the retention of any verified bundle in Memory (Step 8, IF-7).

``retained_acquire`` opens the bundle the request names with Stage 03 ``open_bundle`` (which refuses symbolic links,
non-regular files and a ``capture.json`` over 4 MiB), runs the accepted Stage 03 verification (``verify_bundle``),
checks the capture identity against the request key and the root rules (S-4.6, F-15), and returns:

- the exact ``capture.json`` bytes and every listed artifact as raw blobs (read through ``Bundle.artifact``, which
  verifies each artifact's digest);
- the canonical artifact set and the closed manifest (``citerift.investigation.retained``);
- one ``observation_recorded`` content record naming the manifest, and the root.

It uses no network and writes nothing: the controller publishes the blobs and commits the record (S-9.1). The
original bundle is read once; after ACQUIRE commits, every later step reads the retained bytes from Memory
(``reconstruct``), so the result never depends on the bundle path still existing.

``bundle_observation`` is shared with live ACQUIRE, which retains the bundle its supervised child published.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from citerift.investigation import ids, retained
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import canon, sha256_hex
from citerift.wiki.bundle import ARTIFACTS, CAPTURE_FILE, Bundle, BundleError, open_bundle
from citerift.wiki.verify import verify_bundle

SUBJECT_TYPE = "wikipedia_article_revision"
SOURCE_REF = {"engine": "citerift.wiki", "operation": "open_bundle", "locator": None}
MISMATCH = "ROOT_IDENTITY_MISMATCH"


@dataclass(frozen=True)
class Retention:
    """What ACQUIRE asks the controller to keep for one verified bundle."""

    manifest: dict[str, Any]
    artifact_set: dict[str, Any]
    raw: tuple[bytes, ...]  # the capture.json bytes, then every listed artifact in digest order
    root: dict[str, Any]

    @property
    def manifest_digest(self) -> str:
        return sha256_hex(canon(self.manifest))

    def result(self) -> Succeeded:
        obs = {"obs_kind": "bundle", "blob": self.manifest_digest, "source_ref": dict(SOURCE_REF)}
        return Succeeded(
            records=(ContentRecord("observation_recorded", obs),),
            blobs=(self.artifact_set, self.manifest),
            outputs=(self.manifest_digest,),
            root=self.root,
            raw_blobs=self.raw,
        )


class RetentionError(Exception):
    """A verified bundle that cannot be retained as the root of this request (a code of SPEC 9.3)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail[:1000]


def first_error(result: Mapping[str, Any]) -> tuple[str, str]:
    """The first error issue of a Stage 03 verification result (issues are sorted by Stage 03)."""
    for issue in result.get("issues") or []:
        if issue.get("severity") == "error":
            return str(issue.get("code")), str(issue.get("detail") or "")
    return "BUNDLE_SEMANTIC_INVALID", "verification failed without an error issue"


def bundle_observation(bundle: Bundle) -> Retention:
    """The IF-7 retention of a bundle that Stage 03 ``verify_bundle`` has passed."""
    cap = bundle.capture
    if cap.get("status") not in ("complete", "partial"):
        raise RetentionError("BUNDLE_SEMANTIC_INVALID", f"capture status {cap.get('status')!r} is not committed")
    page, source, render = cap["page"], cap["source"], cap["render"]
    listed = retained.listed_artifacts(cap)
    raw = [bundle.capture_bytes]
    arts: list[dict[str, Any]] = []
    for sha, roles in listed.items():
        data = bundle.artifact(sha, limit=retained.MAX_ARTIFACT_BYTES)  # verified against its name by Stage 03
        raw.append(data)
        arts.append({"sha256": sha, "bytes": len(data), "roles": roles})
    artifact_set = {"schema": retained.SET_SCHEMA, "schema_version": retained.SCHEMA_VERSION, "artifacts": arts}
    identity = {
        "wiki": page["wiki"],
        "page_id": page["page_id"],
        "revision_id": page["revision_id"],
        "capture_sha256": bundle.capture_sha256,
    }
    display = {"title": page["title"] if len(page["title"]) <= 1024 else None, "revision_sha1": page["sha1"]}
    manifest = {
        "schema": retained.MANIFEST_SCHEMA,
        "schema_version": retained.SCHEMA_VERSION,
        "engine": "citerift.wiki",
        "capture": {
            "blob": bundle.capture_sha256,
            "bytes": len(bundle.capture_bytes),
            "schema_version": cap["schema_version"],
        },
        "status": cap["status"],
        "identity": identity,
        "display": display,
        "source": {
            "artifact": source["artifact"],
            "bytes": source["bytes"],
            "response_artifact": source["response_artifact"],
        },
        "render": {"state": render["state"], "artifact": render.get("artifact")},
        "failure_artifact_count": sum(1 for roles in listed.values() if "failure" in roles),
        "artifact_set": {
            "blob": sha256_hex(canon(artifact_set)),
            "count": len(arts),
            "bytes": sum(a["bytes"] for a in arts),
        },
    }
    problem = retained.manifest_problem(manifest) or retained.set_problem(artifact_set, manifest)
    if problem is not None:
        raise RetentionError("BUNDLE_SEMANTIC_INVALID", f"the verified bundle gives no valid manifest: {problem}")
    root = {
        "root_id": ids.root_id(SUBJECT_TYPE, identity),
        "subject": {"type": SUBJECT_TYPE, "identity": identity, "display": display},
    }
    return Retention(manifest, artifact_set, tuple(raw), root)


def open_verified(path: Path) -> tuple[Bundle | None, Failed | None]:
    """Open and verify a bundle with the accepted Stage 03 functions; the failure carries the Stage 03 code."""
    try:
        bundle = open_bundle(path)
    except BundleError as exc:
        return None, Failed(exc.issue.code, detail=exc.issue.detail[:1000])
    except OSError as exc:  # a race or a permission problem below open_bundle's own checks
        return None, Failed("BUNDLE_MALFORMED", detail=f"{path.name}: {exc.strerror}"[:1000])
    result = verify_bundle(bundle)
    if not result.get("verified"):
        code, detail = first_error(result)
        return None, Failed(code, detail=f"Stage 03 verification: {detail}"[:1000])
    return bundle, None


def retain(bundle: Bundle, request_key: Mapping[str, Any]) -> StepResult:
    """Retention of a verified bundle for this request: the result, or the identity failure (S-4.6)."""
    try:
        kept = bundle_observation(bundle)
    except RetentionError as exc:
        return Failed(exc.code, detail=exc.detail)
    except BundleError as exc:  # an artifact changed between verification and retention
        return Failed(exc.issue.code, detail=exc.issue.detail[:1000])
    ident = kept.root["subject"]["identity"]
    if "capture_sha256" in request_key:
        if ident["capture_sha256"] != request_key["capture_sha256"]:
            return Failed(MISMATCH, detail="the bundle's capture_sha256 is not the request's")
    elif (ident["wiki"], ident["revision_id"]) != (request_key.get("wiki"), request_key.get("revision_id")):
        return Failed(MISMATCH, detail="the captured revision is not the requested one")
    return kept.result()


def retained_acquire(req: StepRequest) -> StepResult:
    """The ACQUIRE adapter of a retained-bundle request. No network, no timer (SPEC 9.2)."""
    bundle, failure = open_verified(Path(req.request["subject"]["bundle_path"]))
    if failure is not None or bundle is None:
        return failure if failure is not None else Failed("BUNDLE_SEMANTIC_INVALID", detail="no bundle")
    return retain(bundle, req.request_key)


# Reconstruction from Memory ----------------------------------------------------------------------------------------


def committed_manifest(req: StepRequest) -> dict[str, Any]:
    """The committed bundle observation manifest of this investigation (the ACQUIRE output)."""
    outputs = req.inputs.get("ACQUIRE") or ()
    for digest in outputs:
        value = req.read_blob(digest)
        if (
            isinstance(value, dict)
            and value.get("schema") == retained.MANIFEST_SCHEMA
            and retained.manifest_problem(value) is None
        ):
            return value
    raise RetentionError("ADAPTER_INCONSISTENT", "no committed bundle observation manifest")


@contextlib.contextmanager
def reconstruct(manifest: Mapping[str, Any], read_bytes: Callable[[str], bytes]) -> Iterator[Path]:
    """A private bundle directory rebuilt from the retained raw blobs: exactly ``capture.json`` and the listed
    artifacts, byte for byte. It exists only inside the ``with`` block (mode 0700, removed afterwards)."""
    artifact_set = json.loads(read_bytes(manifest["artifact_set"]["blob"]))  # canonical; raw bytes are never parsed
    problem = retained.set_problem(artifact_set, dict(manifest))
    if problem is not None:
        raise RetentionError("ADAPTER_INCONSISTENT", f"the retained artifact set is invalid: {problem}")
    base = Path(tempfile.mkdtemp(prefix="citerift-bundle-"))
    try:
        path = base / "bundle"
        (path / ARTIFACTS).mkdir(parents=True, mode=0o700)
        _write(path / CAPTURE_FILE, read_bytes(manifest["capture"]["blob"]), manifest["capture"]["blob"])
        for a in artifact_set["artifacts"]:
            _write(path / ARTIFACTS / a["sha256"], read_bytes(a["sha256"]), a["sha256"])
        yield path
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _write(path: Path, data: bytes, digest: str) -> None:
    if sha256_hex(data) != digest:  # read_bytes verifies, so this is a defect, never a silent repair
        raise RetentionError("ADAPTER_INCONSISTENT", f"retained blob {digest} does not hash to its name")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
