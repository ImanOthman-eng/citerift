"""Stage 03: the Wikipedia extraction engine for arwiki and enwiki (docs/verification/stage-03/SPECIFICATION.md).

Public API::

    capture_revision(request, fetch_policy)   network: pinned source revision plus a separately identified render
    extract_bundle(capture, config)           offline: deterministic extraction from a capture bundle
    verify_bundle(bundle)                     offline: integrity, schema and semantic checks of a bundle
    replay_bundle(bundle, pinned_config)      offline: re-extract and compare with a recorded extraction

The names are imported lazily so that ``import citerift.wiki`` stays cheap and never touches the network.
"""

from __future__ import annotations

import importlib
from typing import Any

__version__ = "1.0.0"

__all__ = [
    "CaptureRequest",
    "ExtractConfig",
    "FetchPolicy",
    "__version__",
    "capture_revision",
    "extract_bundle",
    "replay_bundle",
    "verify_bundle",
]

_LAZY = {
    "CaptureRequest": "citerift.wiki.capture",
    "capture_revision": "citerift.wiki.capture",
    "FetchPolicy": "citerift.wiki.fetch",
    "ExtractConfig": "citerift.wiki.extract",
    "extract_bundle": "citerift.wiki.extract",
    "replay_bundle": "citerift.wiki.verify",
    "verify_bundle": "citerift.wiki.verify",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(name)
