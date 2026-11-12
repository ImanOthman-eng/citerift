"""VALIDATE: the request checks of SPEC 5.1 (Step 8).

The request schema (``urn:citerift:schema:investigation:v1:request``) already refuses a title-only or page-only
request. VALIDATE adds what a schema cannot state: the live configuration's D-042 arithmetic, a retained bundle that
Stage 03 ``open_bundle`` accepts, an index path that is an existing regular file, and a safe memory root. Each failure
is ``INPUT_INVALID`` with the reason of SPEC 5.1. Nothing is read from the network.
"""

from __future__ import annotations

import copy
import os
import stat
from pathlib import Path
from typing import Any

from citerift.investigation import ids
from citerift.investigation.adapters import Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.errors import PathUnsafe
from citerift.investigation.fsutil import check_memory_root
from citerift.investigation.schemas import REQUEST, problems
from citerift.wiki.bundle import BundleError, open_bundle

INVALID = "INPUT_INVALID"


def _bad(reason: str, detail: str) -> Failed:
    return Failed(INVALID, reason=reason, detail=detail[:1000])


def validate(req: StepRequest) -> StepResult:
    request: dict[str, Any] = copy.deepcopy(dict(req.request))
    found = problems(request, REQUEST)
    if found:
        return _bad("REVISION_NOT_PINNED", "request schema: " + "; ".join(found[:3]))
    cfg = request["config"]
    if request["mode"] == "live_capture":
        if cfg["fetch_policy_sha256"] is None or not ids.live_bound_consistent(cfg):
            return _bad("REVISION_NOT_PINNED", "a live capture needs its fetch policy and a consistent D-042 bound")
    else:
        if cfg["fetch_policy_sha256"] is not None or cfg["live_acquire_bound"] is not None:
            return _bad("BUNDLE_UNREADABLE", "a retained bundle has no fetch policy and no live bound")
        try:
            open_bundle(Path(request["subject"]["bundle_path"]))
        except BundleError as exc:
            return _bad("BUNDLE_UNREADABLE", f"{exc.issue.code}: {exc.issue.detail}")
        except OSError as exc:
            return _bad("BUNDLE_UNREADABLE", str(exc.strerror))
    try:
        st = os.stat(request["index_path"], follow_symlinks=False)
    except OSError as exc:
        return _bad("INDEX_PATH_INVALID", f"{request['index_path']}: {exc.strerror}")
    if not stat.S_ISREG(st.st_mode):
        return _bad("INDEX_PATH_INVALID", f"{request['index_path']} is not a regular file")
    try:
        check_memory_root(Path(request["memory_root"]))
    except PathUnsafe as exc:
        return _bad("MEMORY_ROOT_UNSAFE", exc.detail)
    out = {"validated": request}
    return Succeeded(blobs=(out,), outputs=(sha256_hex(canon(out)),))
