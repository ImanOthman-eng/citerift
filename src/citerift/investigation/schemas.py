"""Schema validation of Stage 04 records against ``schemas/investigation/v1`` (Step 5).

The investigation schemas reference the accepted contracts, wiki and retraction schemas, so all four directories are
loaded into one registry. JSON Schema checks one document; the Memory invariants it cannot express are checked in
``fold.py``.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from citerift.contracts.formats import FORMAT_CHECKER
from citerift.contracts.validate import ContractSet, load_contracts

SCHEMA_ROOT_ENV = "CITERIFT_SCHEMAS"
PREFIX = "urn:citerift:schema:investigation:v1:"
COMMON = PREFIX + "common"
REQUEST = PREFIX + "request"
RECORD = PREFIX + "journal-record"
CLAIM = PREFIX + "claim"
REPORT = PREFIX + "report"
EVIDENCE_SET = PREFIX + "evidence-set"
PROJECTION_SET = PREFIX + "projection-set"
EVIDENCE_BATCH = PREFIX + "evidence-batch"
REPORT_CHUNK = PREFIX + "report-chunk"
LOOKUP_BATCH = PREFIX + "lookup-batch"
CANDIDATE_BATCH = PREFIX + "candidate-result-batch"
BUNDLE_OBSERVATION = PREFIX + "bundle-observation"
BUNDLE_ARTIFACT_SET = PREFIX + "bundle-artifact-set"
CANDIDATE_INPUTS = PREFIX + "candidate-inputs"
LOOKUP_OBSERVATION = PREFIX + "lookup-observation"
LOOKUP_PLAN = PREFIX + "lookup-plan"
DIRS = ("contracts", "wiki", "retraction", "investigation")


class SchemaRootUnavailable(Exception):
    """The schema directory cannot be found."""


def schema_root() -> Path:
    override = os.environ.get(SCHEMA_ROOT_ENV)
    return Path(override) if override else Path(__file__).resolve().parents[3] / "schemas"


@cache
def contracts() -> ContractSet:
    root = schema_root()
    merged: dict[str, dict[str, Any]] = {}
    for name in DIRS:
        if not (root / name).is_dir():
            raise SchemaRootUnavailable(str(root / name))
        merged.update(load_contracts(root / name).schemas)
    return ContractSet(merged)


@cache
def _validator(schema_id: str) -> Any:
    cs = contracts()
    return Draft202012Validator(cs.schemas[schema_id], registry=cs.registry, format_checker=FORMAT_CHECKER)


def problems(instance: Any, schema_id: str) -> list[str]:
    """Schema problems as ``/path: message`` lines in path order; empty when valid."""
    errors = sorted(_validator(schema_id).iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return ["/" + "/".join(str(p) for p in e.absolute_path) + ": " + e.message[:300] for e in errors]


@cache
def _ref_validator(ref: str) -> Any:
    cs = contracts()
    return Draft202012Validator({"$ref": ref}, registry=cs.registry, format_checker=FORMAT_CHECKER)


def ref_problems(instance: Any, ref: str) -> list[str]:
    """Schema problems of ``instance`` against one definition, named by an absolute reference (``urn:...#/$defs/x``)."""
    errors = sorted(_ref_validator(ref).iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return ["/" + "/".join(str(p) for p in e.absolute_path) + ": " + e.message[:300] for e in errors]
