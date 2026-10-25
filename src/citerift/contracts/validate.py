"""Load, validate and compare versions of the CITERIFT data contracts.

Validation has two layers:

1. JSON Schema (Draft 2020-12) for structure and per-field epistemic rules.
2. Semantic checks that JSON Schema cannot express, such as uniqueness of ids
   and references between records.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

INVESTIGATION_ID = "urn:citerift:schema:contracts:v1:investigation"


@dataclass(frozen=True)
class ContractProblem:
    code: str
    path: str
    message: str
    keyword: str | None = None

    def __str__(self) -> str:
        return f"{self.code} at {self.path or '<root>'}: {self.message}"


class ContractSet:
    """All schemas found under one directory, resolvable by their ``$id``."""

    def __init__(self, schemas: dict[str, dict[str, Any]]):
        self.schemas = schemas
        resources = [(sid, Resource.from_contents(s, default_specification=DRAFT202012)) for sid, s in schemas.items()]
        self.registry: Registry[Any] = Registry().with_resources(resources)

    def meta_problems(self) -> list[ContractProblem]:
        problems = []
        for sid, schema in self.schemas.items():
            for err in Draft202012Validator(Draft202012Validator.META_SCHEMA).iter_errors(schema):
                problems.append(ContractProblem("SCHEMA_INVALID", sid, err.message, str(err.validator)))
            if "x-citerift-version" not in schema:
                problems.append(ContractProblem("SCHEMA_UNVERSIONED", sid, "missing x-citerift-version"))
        return problems

    def validate(self, instance: Any, schema_id: str = INVESTIGATION_ID) -> list[ContractProblem]:
        validator = Draft202012Validator(self.schemas[schema_id], registry=self.registry)
        problems = [
            ContractProblem(
                "SCHEMA_VIOLATION",
                "/" + "/".join(str(p) for p in err.absolute_path),
                err.message,
                str(err.validator),
            )
            for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        ]
        if not problems and schema_id == INVESTIGATION_ID:
            problems = semantic_problems(instance)
        return problems


def semantic_problems(record: dict[str, Any]) -> list[ContractProblem]:
    problems: list[ContractProblem] = []
    citation_ids = [c["citation_id"] for c in record["citations"]]
    for i, cid in enumerate(citation_ids):
        if citation_ids.index(cid) != i:
            problems.append(
                ContractProblem("DUPLICATE_ID", f"/citations/{i}/citation_id", f"duplicate citation id {cid}")
            )
    assessment_ids = [a["assessment_id"] for a in record["assessments"]]
    for i, a in enumerate(record["assessments"]):
        if assessment_ids.index(a["assessment_id"]) != i:
            problems.append(
                ContractProblem(
                    "DUPLICATE_ID", f"/assessments/{i}/assessment_id", f"duplicate assessment id {a['assessment_id']}"
                )
            )
        if a["target_citation_id"] not in citation_ids:
            problems.append(
                ContractProblem(
                    "DANGLING_REFERENCE",
                    f"/assessments/{i}/target_citation_id",
                    f"no citation {a['target_citation_id']}",
                )
            )
    times = [e["at"] for e in record["events"]]
    if times != sorted(times):
        problems.append(ContractProblem("EVENT_ORDER", "/events", "events are not in chronological order"))
    status = record["status"]
    if status in ("partial", "failed") and not record["limitations"]:
        problems.append(
            ContractProblem("LIMITATIONS_REQUIRED", "/limitations", f"status '{status}' must state its limitations")
        )
    return problems


def load_contracts(schema_dir: Path) -> ContractSet:
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.rglob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        sid = schema.get("$id")
        if not isinstance(sid, str):
            raise ValueError(f"{path} has no $id")
        if sid in schemas:
            raise ValueError(f"duplicate $id {sid} in {path}")
        schemas[sid] = schema
    if not schemas:
        raise ValueError(f"no *.schema.json files under {schema_dir}")
    return ContractSet(schemas)


def check_backward_compatible(
    old: ContractSet, new: ContractSet, valid_fixtures: list[Any], schema_id: str = INVESTIGATION_ID
) -> list[str]:
    """Fixture-based compatibility: every record valid under ``old`` must stay valid under ``new``.

    This is an empirical check over the supplied fixtures, not a proof that the
    two schemas accept the same language.
    """
    broken = []
    for index, fixture in enumerate(valid_fixtures):
        if old.validate(fixture, schema_id):
            raise ValueError(f"fixture {index} is not valid under the old contract")
        problems = new.validate(fixture, schema_id)
        if problems:
            broken.append(f"fixture {index}: {problems[0]}")
    return broken


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citerift-contracts", description="Validate CITERIFT contracts")
    parser.add_argument("--schemas", type=Path, default=Path("schemas/contracts"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-schemas", help="validate every schema against the 2020-12 meta-schema")
    v = sub.add_parser("validate", help="validate JSON records")
    v.add_argument("files", nargs="+", type=Path)
    v.add_argument("--schema-id", default=INVESTIGATION_ID)
    args = parser.parse_args(argv)
    contracts = load_contracts(args.schemas)
    if args.command == "check-schemas":
        problems = contracts.meta_problems()
        for p in problems:
            print(p)
        print(f"{len(contracts.schemas)} schemas checked, {len(problems)} problems")
        return 1 if problems else 0
    failed = 0
    for path in args.files:
        problems = contracts.validate(json.loads(path.read_text(encoding="utf-8")), args.schema_id)
        print(f"{path}: {'valid' if not problems else 'INVALID'}")
        for p in problems:
            print(f"  {p}")
        failed += bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
