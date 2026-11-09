"""Schema validation of Stage 03 records (schemas/wiki/v1, SPECIFICATION.md 8 and 14).

The wiki schemas reference the common v1 contract definitions, so both directories are loaded into one registry.
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
PREFIX = "urn:citerift:schema:wiki:v1:"
CAPTURE = PREFIX + "capture"
EXTRACTION = PREFIX + "extraction"
VERIFICATION = PREFIX + "verification"


class SchemaRootUnavailable(Exception):
    """The schema directory cannot be found."""


def schema_root() -> Path:
    """The repository ``schemas`` directory (override with CITERIFT_SCHEMAS)."""
    override = os.environ.get(SCHEMA_ROOT_ENV)
    return Path(override) if override else Path(__file__).resolve().parents[3] / "schemas"


@cache
def contracts() -> ContractSet:
    root = schema_root()
    if not (root / "contracts").is_dir() or not (root / "wiki").is_dir():
        raise SchemaRootUnavailable(str(root))
    return ContractSet({**load_contracts(root / "contracts").schemas, **load_contracts(root / "wiki").schemas})


@cache
def _validator(schema_id: str) -> Any:
    cs = contracts()
    return Draft202012Validator(cs.schemas[schema_id], registry=cs.registry, format_checker=FORMAT_CHECKER)


def validate(instance: Any, schema_id: str) -> list[str]:
    """Schema problems as ``path: message`` lines, in path order (empty when valid)."""
    errors = sorted(_validator(schema_id).iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return ["/" + "/".join(str(p) for p in e.absolute_path) + ": " + e.message[:300] for e in errors]
