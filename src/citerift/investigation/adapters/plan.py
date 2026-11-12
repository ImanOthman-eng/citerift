"""The production adapters of plan-1 and the input identity source of SPEC 10.3 (Step 8).

``Integration`` wires one adapter per step to the accepted engines: Stage 03 for ACQUIRE (retained or live), EXTRACT
and VERIFY's capture check; Stage 02 for LOOKUP; and the Stage 04 transforms for VALIDATE, NORMALIZE, ASSEMBLE and
VERIFY. DETECT is the thin boundary around a detector that Step 9 supplies (``detector=None`` until then).

``Integration.environment`` is the controller's identity source: the request key fixed at creation; the bound root
(for a retained bundle whose path still exists, the capture digest found there, so a replaced bundle is STALE; when
the path is gone, the root Memory holds, because the result never depends on that path); the Stage 03 extraction
identity (extractor, profile, parsers, configuration digest); the Stage 02 index identity (snapshot, policy, lookup
schema version, file SHA-256); the Stage 04 engine identity with the Step 8 integration schema versions; and the
effective configuration.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import citerift
from citerift.investigation.adapters import StepAdapter, StepRequest, StepResult
from citerift.investigation.adapters.acquire import retained_acquire
from citerift.investigation.adapters.assemble import make_assemble
from citerift.investigation.adapters.detect import Detector, make_detect
from citerift.investigation.adapters.extract import extraction_identity, make_extract
from citerift.investigation.adapters.lookup import Opener, environment_identity, make_lookup
from citerift.investigation.adapters.normalize import normalize
from citerift.investigation.adapters.validate import validate
from citerift.investigation.adapters.verify import make_verify
from citerift.investigation.workflow import PLAN_VERSION
from citerift.retraction.query import Index
from citerift.wiki.bundle import BundleError, open_bundle
from citerift.wiki.extract import ExtractConfig

STAGE04_IDENTITY = {
    "engine_version": citerift.__version__,
    "table_version": "dt-1",
    "plan_version": PLAN_VERSION,
    "schema_version": "2.0.0",
}
# The Step 8 blob schemas the adapters write; a change of any is a change of the Stage 04 identity (STALE).
INTEGRATION_SCHEMAS = {
    "bundle-observation": "1.0.0",
    "bundle-artifact-set": "1.0.0",
    "candidate-inputs": "1.0.0",
    "lookup-observation": "1.0.0",
    "lookup-plan": "1.0.0",
}

IdentitySource = Callable[[Mapping[str, Any] | None], Mapping[str, Any]]


@dataclass(frozen=True)
class Integration:
    """The production adapter set. ``live`` is the live-ACQUIRE adapter (``adapters.live.make_live_acquire``); a
    retained-bundle investigation never calls it."""

    extract_config: ExtractConfig = field(default_factory=ExtractConfig)
    detector: Detector | None = None
    live: StepAdapter | None = None
    index_opener: Opener = Index
    stage04: Mapping[str, Any] = field(default_factory=lambda: dict(STAGE04_IDENTITY))

    def adapters(self) -> dict[str, StepAdapter]:
        def acquire(req: StepRequest) -> StepResult:
            if req.live:
                if self.live is None:
                    raise RuntimeError("a live capture needs the live ACQUIRE adapter")
                return self.live(req)
            return retained_acquire(req)

        return {
            "VALIDATE": validate,
            "ACQUIRE": acquire,
            "EXTRACT": make_extract(self.extract_config),
            "NORMALIZE": normalize,
            "LOOKUP": make_lookup(self.index_opener),
            "DETECT": make_detect(self.detector),
            "ASSEMBLE": make_assemble(self.stage04),
            "VERIFY": make_verify(self.detector, self.stage04),
        }

    def environment(self, created: Mapping[str, Any]) -> IdentitySource:
        """The identity source for the investigation whose ``investigation_created`` payload is ``created``."""
        request = copy.deepcopy(dict(created["request"]))
        request_key = copy.deepcopy(dict(created["request_key"]))

        def current(root: Mapping[str, Any] | None) -> Mapping[str, Any]:
            return {
                "request_key": copy.deepcopy(request_key),
                "root": root_identity(request, root),
                "extraction": extraction_identity(self.extract_config),
                "index": environment_identity(Path(request["index_path"])),
                "stage04": {**copy.deepcopy(dict(self.stage04)), "integration": dict(INTEGRATION_SCHEMAS)},
                "config": copy.deepcopy(request["config"]),
            }

        return current


def root_identity(request: Mapping[str, Any], root: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """The bound root's identity now. A retained bundle that is still at its path is re-read: a different capture
    there is a changed input (STALE). A missing path is not a change: Memory holds the retained bytes (IF-7)."""
    if root is None or request["mode"] != "retained_bundle":
        return copy.deepcopy(dict(root)) if root is not None else None
    path = Path(request["subject"]["bundle_path"])
    try:
        bundle = open_bundle(path)
    except (BundleError, OSError):
        if not path.exists():
            return copy.deepcopy(dict(root))
        return {**root, "capture_sha256": None}  # present but unreadable: not the bound capture
    return {**root, "capture_sha256": bundle.capture_sha256}
