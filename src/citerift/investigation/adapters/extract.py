"""EXTRACT: the accepted Stage 03 extraction over the committed ACQUIRE bytes (Step 8).

The adapter rebuilds the bundle from Investigation Memory (the raw ``capture.json`` and artifacts IF-7 retained) in a
private temporary directory and runs ``citerift.wiki.extract.extract_bundle(path, config, isolated=True)``: the
offline Stage 03 worker with its wall and memory limits. The original bundle path is never read.

- A ``complete`` or ``partial`` document that is schema-valid, whose digest is its own, whose extractor and
  configuration are the ones this adapter ran, and whose capture fields equal the bound root (S-4.6) is committed as
  the extraction observation, exactly as Stage 03 returned it.
- A ``failed`` document is mapped by owner decision D-050 (``extraction.extraction_failure``): the worker codes stay
  retryable codes, every other valid Stage 03 code is ``EXTRACTION_FAILED`` with the code as the reason, and a
  malformed document is ``ADAPTER_INCONSISTENT``. Stage 03 science is never reinterpreted.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.adapters.acquire import committed_manifest, reconstruct
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.extraction import ADAPTER_INCONSISTENT, EXTRACTION_SCHEMA, extraction_failure
from citerift.investigation.schemas import problems
from citerift.wiki.canonical import digest as stage03_digest
from citerift.wiki.extract import ExtractConfig, extract_bundle, extractor_identity
from citerift.wiki.profile import load_profile

SOURCE_REF = {"engine": "citerift.wiki", "operation": "extract_bundle", "locator": None}
MISMATCH = "ROOT_IDENTITY_MISMATCH"
Extractor = Callable[[Any, ExtractConfig], dict[str, Any]]


def run_stage03(path: Any, config: ExtractConfig) -> dict[str, Any]:
    return extract_bundle(path, config, isolated=True)


def extraction_identity(config: ExtractConfig) -> dict[str, Any]:
    """The Stage 03 engine identity EXTRACT depends on (SPEC 10.3): extractor, profile, parsers and configuration."""
    return {"extractor": extractor_identity(load_profile()), "config_digest": stage03_digest(config.to_json())}


def document_problem(doc: Any, config: ExtractConfig) -> str | None:
    """Why a non-failed Stage 03 document cannot be committed, or None."""
    found = problems(doc, EXTRACTION_SCHEMA)
    if found:
        return "schema: " + "; ".join(found[:3])
    if doc["extraction_digest"] != stage03_digest({k: v for k, v in doc.items() if k != "extraction_digest"}):
        return "the document's extraction_digest is not its own digest"
    want = extraction_identity(config)
    if doc["extractor"] != want["extractor"] or doc["config_digest"] != want["config_digest"]:
        return "the document names another extractor or configuration than the one run"
    return None


def make_extract(config: ExtractConfig | None = None, extractor: Extractor = run_stage03) -> Callable[..., StepResult]:
    """The EXTRACT adapter for ``config`` (default: the Stage 03 defaults, part of the extraction identity)."""
    cfg = config or ExtractConfig()

    def extract(req: StepRequest) -> StepResult:
        if req.root is None:
            return Failed(ADAPTER_INCONSISTENT, detail="EXTRACT without a bound root")
        ident: Mapping[str, Any] = req.root["subject"]["identity"]
        manifest = committed_manifest(req)
        if manifest["identity"] != dict(ident):
            return Failed(MISMATCH, detail="the committed bundle is not the bound root's")
        with reconstruct(manifest, req.read_bytes) as path:
            doc = extractor(path, cfg)
        if not isinstance(doc, dict):
            return Failed(ADAPTER_INCONSISTENT, detail="Stage 03 returned no document")
        if doc.get("status") == "failed":
            return extraction_failure(doc)
        problem = document_problem(doc, cfg)
        if problem is not None:
            return Failed(ADAPTER_INCONSISTENT, detail=f"Stage 03 document: {problem}"[:1000])
        cap = doc["capture"]
        if any(cap[n] != ident[n] for n in ("wiki", "page_id", "revision_id", "capture_sha256")):
            return Failed(MISMATCH, detail="the extraction's capture is not the bound root")
        digest = sha256_hex(canon(doc, allow_float=True))
        obs = {"obs_kind": "extraction", "blob": digest, "source_ref": dict(SOURCE_REF)}
        return Succeeded(records=(ContentRecord("observation_recorded", obs),), blobs=(doc,), outputs=(digest,))

    return extract
