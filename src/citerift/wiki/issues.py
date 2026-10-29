"""Structured issues: stable codes, severity, affected entities, retryability, evidence (SPECIFICATION.md 10).

Every code an extraction or capture can emit is listed in CATALOG with its fixed severity and default
retryability, so that a reader can enumerate them and a test can check that nothing else is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# severity: "error" stops the affected component, "warning" limits a result, "info" records a fact.
CATALOG: dict[str, tuple[str, bool, str]] = {
    # Request and acquisition
    "REQUEST_INVALID": ("error", False, "the request names no valid wiki or more or less than one target"),
    "WIKI_UNSUPPORTED": ("error", False, "only arwiki and enwiki are supported"),
    "HTTP_TIMEOUT": ("error", True, "connection or read timed out"),
    "HTTP_CONNECTION_FAILED": ("error", True, "the connection could not be made"),
    "NETWORK_GATE_BUSY": ("error", True, "another process held the project network gate past the capture deadline"),
    "NETWORK_GATE_UNAVAILABLE": ("error", False, "the project network gate could not be opened or locked"),
    "HTTP_RATE_LIMITED": ("error", True, "HTTP 429"),
    "HTTP_UNAVAILABLE": ("error", True, "HTTP 502, 503 or 504"),
    "HTTP_SERVER_ERROR": ("error", True, "other HTTP 5xx"),
    "HTTP_FORBIDDEN": ("error", False, "HTTP 403; never bypassed"),
    "HTTP_NOT_FOUND": ("error", False, "HTTP 404"),
    "HTTP_STATUS_UNEXPECTED": ("error", False, "an HTTP status the client does not accept"),
    "API_MAXLAG": ("error", True, "MediaWiki maxlag error inside HTTP 200"),
    "API_RATELIMITED": ("error", True, "MediaWiki ratelimited error inside HTTP 200"),
    "API_ERROR": ("error", False, "another MediaWiki error inside HTTP 200"),
    "RESPONSE_NOT_JSON": ("error", True, "the body is not valid JSON"),
    "RESPONSE_CONTENT_TYPE": ("error", False, "the content type is not the expected one"),
    "RESPONSE_TOO_LARGE": ("error", False, "the body exceeds the wire, decompressed or retained limit"),
    "RESPONSE_ENCODING_UNSUPPORTED": ("error", False, "a content encoding other than identity or gzip"),
    "RESPONSE_INCOMPLETE": ("error", True, "the body is shorter than announced or the stream broke"),
    "RESPONSE_DECOMPRESSION_FAILED": ("error", False, "the gzip stream is invalid"),
    "DEADLINE_EXCEEDED": ("error", True, "the global capture deadline passed"),
    "DEFERRED_RETRY_AFTER": ("error", True, "Retry-After points past the capture deadline; not_before is recorded"),
    "ATTEMPTS_EXHAUSTED": ("error", True, "the attempt budget of the operation is spent"),
    "HOST_NOT_ALLOWED": ("error", False, "a URL outside the fixed Wikipedia hosts"),
    # Source revision identity
    "PAGE_MISSING": ("error", False, "the page does not exist"),
    "TITLE_INVALID": ("error", False, "the title is invalid"),
    "REVISION_NOT_FOUND": ("error", False, "the revision id does not exist (badrevids)"),
    "REVISION_TEXT_HIDDEN": ("error", False, "the revision text is hidden or deleted"),
    "NAMESPACE_UNSUPPORTED": ("error", False, "only namespace 0 is supported"),
    "CONTENT_MODEL_UNSUPPORTED": ("error", False, "only the wikitext content model is supported"),
    "SLOT_MISSING": ("error", False, "the main slot is missing from the answer"),
    "PAGE_ID_MISMATCH": ("error", False, "the answer names another page id than requested"),
    "REVISION_ID_MISMATCH": ("error", False, "the answer names another revision than requested"),
    "SOURCE_HASH_MISMATCH": ("error", False, "the slot SHA-1 or size does not match the extracted text"),
    "SOURCE_TOO_LARGE": ("error", False, "the slot text exceeds the source limit"),
    "SOURCE_NOT_ENCODABLE": ("error", False, "the slot text cannot be encoded as UTF-8 (lone surrogate)"),
    "REDIRECT_PAGE": ("warning", False, "the requested page is a redirect"),
    "REDIRECT_FOLLOWED": ("info", False, "a redirect was followed once, explicitly"),
    "REDIRECT_NOT_FOLLOWED": ("error", False, "the page is a redirect and following was not requested"),
    "REDIRECT_LIMIT": ("error", False, "a redirect led to another redirect; one hop is the limit"),
    # Render capture
    "RENDER_NOT_REQUESTED": ("info", False, "no render capture was requested"),
    "RENDER_PROFILE_UNSUPPORTED": ("error", False, "the HTML profile is not the supported Parsoid HTML 2.x"),
    "RENDER_REVISION_MISMATCH": ("error", False, "the render names another revision, page or source hash"),
    "RENDER_REVISION_UNCHECKED": ("error", False, "the render does not state its revision"),
    "RENDER_TOO_LARGE": ("error", False, "the HTML exceeds the render limit"),
    "RENDER_NOT_UTF8": ("error", False, "the HTML is not valid UTF-8"),
    # Bundles and storage
    "BUNDLE_PATH_UNSAFE": ("error", False, "a path is a symlink, escapes the bundle or already exists"),
    "BUNDLE_MALFORMED": ("error", False, "the bundle manifest is unreadable or invalid"),
    "BUNDLE_ARTIFACT_MISSING": ("error", False, "an artifact named by the manifest is missing"),
    "BUNDLE_ARTIFACT_CORRUPT": ("error", False, "an artifact does not match its SHA-256"),
    "BUNDLE_DIGEST_MISMATCH": ("error", False, "a recorded digest does not match the record"),
    "BUNDLE_SCHEMA_INVALID": ("error", False, "a record does not validate against its schema"),
    "BUNDLE_SEMANTIC_INVALID": ("error", False, "a record breaks a semantic rule"),
    "BUNDLE_UNLISTED_FILE": ("warning", False, "a file in the bundle that the capture record does not name"),
    "ANCHOR_MISMATCH": ("error", False, "a recorded source span or exact anchor does not match the source bytes"),
    "LOCATOR_MISMATCH": ("error", False, "a recorded render locator does not resolve to the recorded element"),
    "REPLAY_DIFFERS": ("error", False, "the replayed extraction differs from the recorded one"),
    "REPLAY_IDENTITY_MISMATCH": ("error", False, "the extractor, profile or parser differs from the recorded one"),
    "REPLAY_CONFIG_MISMATCH": ("error", False, "the pinned configuration differs from the recorded one"),
    "SCHEMA_ROOT_UNAVAILABLE": ("error", False, "the schema directory cannot be found (set CITERIFT_SCHEMAS)"),
    # Extraction resources
    "EXTRACTION_DEADLINE_EXCEEDED": ("error", True, "the extraction worker passed its wall deadline and was killed"),
    "EXTRACTION_MEMORY_EXCEEDED": ("error", False, "the extraction worker passed its memory limit"),
    "EXTRACTION_WORKER_FAILED": ("error", False, "the extraction worker ended without a valid result"),
    "LIMIT_NODES": ("error", False, "the parse tree exceeds the node limit"),
    "LIMIT_DEPTH": ("error", False, "the nesting exceeds the depth limit"),
    "LIMIT_OCCURRENCES": ("error", False, "the number of containers, uses or identifiers exceeds its limit"),
    "PLATFORM_UNSUPPORTED": ("error", False, "process limits are not available on this platform"),
    # Source extraction
    "SOURCE_PARSE_LOSSY": ("error", False, "the parse tree does not reproduce the source exactly"),
    "ANCHOR_NOT_EXACT": ("warning", False, "a node boundary could not be validated; no exact anchor is claimed"),
    "UNPARSED_MARKUP": ("warning", False, "markup left as text by the parser (for example nesting too deep)"),
    "REF_NAME_HAS_MARKUP": ("warning", False, "a ref name or group contains markup; it is not bound"),
    "REF_UNCLOSED": ("warning", False, "a ref tag is not closed"),
    "REF_DEFINITION_MISSING": ("warning", False, "a named use has no definition in the saved source"),
    "REF_DEFINITIONS_CONFLICT": ("warning", False, "two definitions with one name and group differ"),
    "REF_DEFINITIONS_DUPLICATE": ("info", False, "two identical definitions share one name and group"),
    "LIST_DEFINED_UNUSED": ("info", False, "a list-defined ref is never used in the saved source"),
    "LIST_DEFINED_WITHOUT_CONTENT": (
        "warning",
        False,
        "a ref inside a reference list has no content; it defines nothing and is not a use",
    ),
    "REF_IN_UNSUPPORTED_CONTEXT": ("warning", False, "a ref inside a construct the extractor does not support"),
    "GENERATED_REFERENCE_UNSUPPORTED": ("warning", False, "a template that generates references or uses"),
    "SUBREFERENCE_UNSUPPORTED": ("warning", False, "a subreference (details attribute) is not supported"),
    "TEMPLATE_UNSUPPORTED": ("info", False, "a template with identifier parameters that is not in the map"),
    "IDENTIFIER_PARAMETER_OVERRIDDEN": (
        "warning",
        False,
        "an identifier parameter repeated later in the same template; only the last value is used",
    ),
    "UNIT_BOUNDARY_UNRESOLVED": ("warning", False, "several identifiers in unstructured text; works not separated"),
    "DUPLICATE_TEMPLATE_PARAMETER": ("warning", False, "a template repeats a parameter; all values are kept"),
    "IDENTIFIER_VALUE_HAS_MARKUP": ("warning", False, "an identifier value contains markup; not normalized"),
    "IDENTIFIER_DECODING_FAILED": (
        "warning",
        False,
        "the structure around an identifier cannot be decoded (invalid percent encoding); not normalized",
    ),
    "IDENTIFIER_BOUNDARY_AMBIGUOUS": (
        "warning",
        False,
        "a text identifier ends in punctuation that may or may not belong",
    ),
    "IDENTIFIER_INVALID": ("info", False, "a candidate the Stage 02 normalizer rejects; kept with its issues"),
    "CO_REPORTED_IDENTIFIERS": ("info", False, "a unit reports several identifiers; their identity is not established"),
    # Render extraction and reconciliation
    "RENDER_PARSE_FAILED": ("error", False, "the HTML could not be parsed under the declared profile"),
    "DOM_ID_DUPLICATE": ("warning", False, "an element id occurs more than once; anchors to it are ambiguous"),
    "RENDER_NOTE_AMBIGUOUS": ("warning", False, "the rendered note of a reference cannot be identified uniquely"),
    "RENDER_TARGET_MISSING": ("warning", False, "a rendered use points to a note that is not in the HTML"),
    "RENDER_DATA_MW_INVALID": ("warning", False, "a data-mw attribute is not valid JSON"),
    "RECONCILIATION_UNAVAILABLE": ("warning", False, "no usable render for this revision; links unavailable"),
    "RECONCILIATION_AMBIGUOUS": ("warning", False, "more than one render element fits; no link is claimed"),
    "RECONCILIATION_ABSTAINED": ("warning", False, "source and render uses could not be paired unambiguously"),
    "RENDER_USE_UNMATCHED": ("info", False, "a rendered reference use has no matched source use"),
    "RENDER_BACKLINK_MISMATCH": ("warning", False, "a matched note's backlinks do not include every matched use"),
    "RENDER_CONTAINER_CONFLICT": ("warning", False, "the uses of one container point to more than one note"),
    "RENDER_TEMPLATE_OMITTED": ("warning", False, "MediaWiki left templates unexpanded (a parser limit warning)"),
    "RENDER_ONLY_IDENTIFIER": ("info", False, "an identifier link in a note that no source occurrence explains"),
    "SOURCE_ONLY": ("info", False, "a source entity has no render counterpart"),
    "RENDER_ONLY": ("info", False, "a render entity has no source counterpart (for example template-generated)"),
    "RENDER_IDENTIFIER_DISAGREES": ("warning", False, "the render shows an identifier the source unit does not"),
    # Markers
    "MARKER_REGION_NOT_INSPECTED": ("info", False, "a render region could not be inspected; no absence is stated"),
}


@dataclass(frozen=True)
class Issue:
    code: str
    entities: tuple[str, ...] = ()
    detail: str = ""
    evidence: tuple[str, ...] = ()
    retryable: bool | None = None
    severity: str = field(default="")

    def __post_init__(self) -> None:
        if self.code not in CATALOG:
            raise ValueError(f"unknown issue code {self.code}")
        if not self.severity:
            object.__setattr__(self, "severity", CATALOG[self.code][0])
        if self.retryable is None:
            object.__setattr__(self, "retryable", CATALOG[self.code][1])

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "retryable": self.retryable,
            "entities": list(self.entities),
            "detail": self.detail,
            "evidence": list(self.evidence),
        }


def sort_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda i: (i.code, i.entities, i.detail, i.evidence))
