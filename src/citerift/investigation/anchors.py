"""The Stage-04-derived unit anchor of owner decision D-043 (Step 5 review finding SR-03; SPEC 4.3, S-12.1).

Stage 03 is authoritative for a unit's source span (``cp_start``, ``cp_end``, ``byte_start``, ``byte_end``) and emits
no hash for it. Stage 04 derives::

    unit_span_sha256 = SHA-256(source_artifact_bytes[byte_start:byte_end])      (half-open interval)

over the exact retained Stage 03 source artifact, never over normalized or reformatted text. Before deriving it,
``SourceArtifact`` verifies the artifact's digest, and ``unit_span_sha256`` verifies that the extraction belongs to
the bound root and names this artifact, that ``0 <= byte_start <= byte_end <= len(source)``, that the span lies on
UTF-8 code-point boundaries matching ``cp_start`` and ``cp_end``, and that every Stage 03 identifier anchor covering
exactly the same byte span has ``raw_sha256`` equal to the derived hash. Any mismatch raises ``SpanError``; nothing
falls back to another identity. VERIFY recomputes the hash with the same function (``verify_unit_span``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from citerift.investigation.canonical import sha256_hex
from citerift.investigation.errors import SpanError
from citerift.wiki.bundle import BundleError, open_bundle, read_artifact

_CHECKPOINT = 4096  # code points between stored byte offsets


class SourceArtifact:
    """The retained Stage 03 source artifact, verified against its digest, with a code-point → byte offset index."""

    def __init__(self, data: bytes, sha256: str) -> None:
        if sha256_hex(data) != sha256:
            raise SpanError("SOURCE_DIGEST_MISMATCH", "the source artifact does not hash to its recorded digest")
        try:
            self.text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise SpanError("SPAN_INVALID", "the source artifact is not UTF-8") from exc
        self.data = data
        self.sha256 = sha256
        self._marks = [0]
        offset = 0
        for i in range(0, len(self.text), _CHECKPOINT):
            offset += len(self.text[i : i + _CHECKPOINT].encode("utf-8"))
            self._marks.append(offset)

    def byte_offset(self, cp: int) -> int:
        block, rest = divmod(cp, _CHECKPOINT)
        start = block * _CHECKPOINT
        return self._marks[block] + len(self.text[start : start + rest].encode("utf-8"))


def _int(span: Mapping[str, Any], name: str) -> int:
    value = span.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise SpanError("SPAN_INVALID", f"{name} is not an integer")
    return value


def unit_span_sha256(
    source: SourceArtifact,
    span: Mapping[str, Any],
    *,
    extraction_capture: Mapping[str, Any],
    root_capture_sha256: str,
    identifiers: Iterable[Mapping[str, Any]] = (),
) -> str:
    """Derive the D-043 unit span hash. ``span`` is the unit's Stage 03 ``source``; ``extraction_capture`` is the
    extraction document's ``capture``; ``identifiers`` are its identifier records, whose ``source`` is a Stage 03
    exact anchor (``$defs/anchor``: span, ``raw`` and ``raw_sha256``)."""
    if extraction_capture.get("capture_sha256") != root_capture_sha256:
        raise SpanError("ROOT_IDENTITY_MISMATCH", "the extraction does not belong to the bound root")
    if extraction_capture.get("source_artifact") != source.sha256:
        raise SpanError("SOURCE_DIGEST_MISMATCH", "the extraction names another source artifact")
    b0, b1 = _int(span, "byte_start"), _int(span, "byte_end")
    c0, c1 = _int(span, "cp_start"), _int(span, "cp_end")
    if not 0 <= b0 <= b1 <= len(source.data):
        raise SpanError("SPAN_INVALID", f"byte span [{b0}, {b1}) is outside 0..{len(source.data)}")
    if not 0 <= c0 <= c1 <= len(source.text):
        raise SpanError("SPAN_INVALID", f"code-point span [{c0}, {c1}) is outside 0..{len(source.text)}")
    if source.byte_offset(c0) != b0 or source.byte_offset(c1) != b1:
        raise SpanError("SPAN_INVALID", "the byte span does not match the code-point span (not on boundaries)")
    digest = sha256_hex(source.data[b0:b1])
    for ident in identifiers:
        if not isinstance(ident, Mapping):
            raise SpanError("SPAN_INVALID", "an identifier record is not an object")
        anchor = ident.get("source")
        if anchor is None:
            continue  # an identifier without an exact anchor anchors no span
        if not isinstance(anchor, Mapping):
            raise SpanError("SPAN_INVALID", f"identifier {ident.get('id')} has a malformed anchor")
        if anchor.get("byte_start") == b0 and anchor.get("byte_end") == b1 and anchor.get("raw_sha256") != digest:
            raise SpanError("ANCHOR_MISMATCH", f"identifier {ident.get('id')} anchors the same span with another hash")
    return digest


def verify_unit_span(
    recorded: str,
    source: SourceArtifact,
    span: Mapping[str, Any],
    *,
    extraction_capture: Mapping[str, Any],
    root_capture_sha256: str,
    identifiers: Iterable[Mapping[str, Any]] = (),
) -> None:
    """VERIFY: recompute the hash from the retained bytes and compare it with the recorded value."""
    again = unit_span_sha256(
        source,
        span,
        extraction_capture=extraction_capture,
        root_capture_sha256=root_capture_sha256,
        identifiers=identifiers,
    )
    if again != recorded:
        raise SpanError("ANCHOR_MISMATCH", "the recorded unit span hash differs from the retained source bytes")


def read_retained_source(
    bundle: Path, extraction_capture: Mapping[str, Any], root_capture_sha256: str
) -> SourceArtifact:
    """Read the source artifact from a retained Stage 03 bundle through the accepted, read-only Stage 03 functions
    (``open_bundle``, ``read_artifact``, which refuse symbolic links and verify the artifact hash). The bundle must be
    the bound root's capture and name the same source artifact as the extraction."""
    try:
        b = open_bundle(bundle)
    except BundleError as exc:
        raise SpanError("SOURCE_DIGEST_MISMATCH", f"bundle: {exc.issue.code}") from exc
    if b.capture_sha256 != root_capture_sha256:
        raise SpanError("ROOT_IDENTITY_MISMATCH", "the bundle is not the bound root's capture")
    sha = (b.capture.get("source") or {}).get("artifact")
    if not isinstance(sha, str) or sha != extraction_capture.get("source_artifact"):
        raise SpanError("SOURCE_DIGEST_MISMATCH", "the bundle's source artifact is not the extraction's")
    try:
        data = read_artifact(bundle, sha)
    except BundleError as exc:
        raise SpanError("SOURCE_DIGEST_MISMATCH", f"source artifact: {exc.issue.code}") from exc
    return SourceArtifact(data, sha)
