"""Stage 04 reading of a failed Stage 03 extraction document (owner decision D-050; Step 7 closure, finding IA-4).

Stage 03 reports every extraction failure as a document with ``status = "failed"`` (``citerift.wiki.extract``), never
as an exception. Its failure families:

- a **worker** failure: ``components.worker = {state: failed, code}`` with the same code as an issue
  (``failure_document``). The worker codes ``EXTRACTION_DEADLINE_EXCEEDED``, ``EXTRACTION_MEMORY_EXCEEDED`` and
  ``EXTRACTION_WORKER_FAILED`` are resource limits of the isolated worker; the same component also carries bundle,
  capture-verification, platform and digest codes;
- a **source** failure: ``components.source = {state: failed, code}`` for a parser limit (``LIMIT_*``,
  ``SOURCE_PARSE_LOSSY``), or ``{state: failed}`` without a code when the capture holds no supported source, with the
  code as an error issue;
- an **accounting** failure: the components ran, an accounting check failed, and the code is an error issue.

``extraction_failure`` maps a failed document to the ``Failed`` result of the EXTRACT step:

- a worker code of the three is that Stage 04 code; SPEC 9.3 makes it retryable (the controller decides);
- any other valid Stage 03 code is ``EXTRACTION_FAILED``, non-retryable, with the Stage 03 code as the reason, and the
  document is kept as evidence of the failing attempt;
- a document that contradicts the Stage 03 schema, a failure without a determinable code, a code Stage 03 does not
  define, or contradictory metadata (a worker code outside a failed worker component, a worker code that no issue
  carries) is ``ADAPTER_INCONSISTENT``. A worker failure is never guessed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from citerift.investigation.adapters import Failed
from citerift.investigation.schemas import problems
from citerift.investigation.workflow import EXTRACT_RETRYABLE
from citerift.wiki.issues import CATALOG

EXTRACTION_SCHEMA = "urn:citerift:schema:wiki:v1:extraction"
EXTRACTION_FAILED = "EXTRACTION_FAILED"
ADAPTER_INCONSISTENT = "ADAPTER_INCONSISTENT"
WORKER_CODES = EXTRACT_RETRYABLE


def _inconsistent(detail: str) -> Failed:
    return Failed(ADAPTER_INCONSISTENT, detail=f"Stage 03 failed document: {detail}")


def _known(code: Any) -> bool:
    return isinstance(code, str) and code in CATALOG


def extraction_failure(document: Any) -> Failed:
    """The EXTRACT failure for a Stage 03 extraction document whose ``status`` is ``"failed"`` (D-050)."""
    found = problems(document, EXTRACTION_SCHEMA)
    if found:
        return _inconsistent("schema: " + "; ".join(found[:3]))
    if document["status"] != "failed":
        return _inconsistent(f"status is {document['status']!r}, not 'failed'")
    components: Mapping[str, Any] = document["components"]
    issue_codes = [i["code"] for i in document["issues"]]
    error_codes = [i["code"] for i in document["issues"] if i["severity"] == "error"]
    worker = components.get("worker")
    if isinstance(worker, Mapping) and worker.get("state") == "failed":
        code = worker.get("code")
        if not _known(code):
            return _inconsistent(f"the failed worker component has no valid code ({code!r})")
        if code not in issue_codes:
            return _inconsistent(f"the worker code {code} is not among the document's issues")
        detail = f"Stage 03 worker failure {code}"
        if code in WORKER_CODES:
            return Failed(code, detail=detail, evidence=document)
        return Failed(EXTRACTION_FAILED, reason=code, detail=detail, evidence=document)
    # Not a worker failure: a worker code anywhere would contradict it.
    component_codes = [c.get("code") for _, c in sorted(components.items()) if c.get("state") == "failed"]
    if any(c in WORKER_CODES for c in [*component_codes, *issue_codes]):
        return _inconsistent("a worker code outside a failed worker component")
    if any(c is not None and not _known(c) for c in component_codes):
        return _inconsistent(f"a failed component carries an unknown code ({component_codes})")
    candidates = [c for c in component_codes if c is not None] + error_codes
    if not candidates:
        return _inconsistent("no failed component code and no error issue")
    code = candidates[0]
    if not _known(code):
        return _inconsistent(f"the failure code {code!r} is not a Stage 03 code")
    return Failed(EXTRACTION_FAILED, reason=code, detail=f"Stage 03 extraction failed: {code}", evidence=document)
