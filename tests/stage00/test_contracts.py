"""Versioned data contracts: positive fixtures, mutation-based negative cases, compatibility."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from citerift.contracts import check_backward_compatible, load_contracts
from citerift.contracts.validate import main as contracts_main

pytestmark = [pytest.mark.contracts]

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "schemas" / "contracts"
FIXTURES = Path(__file__).parent / "fixtures" / "contracts" / "v1"
VALID = sorted((FIXTURES / "valid").glob("*.json"))
CASES = json.loads((FIXTURES / "invalid_cases.json").read_text(encoding="utf-8"))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_mutation(doc: Any, op: str, pointer: str, value: Any = None) -> Any:
    doc = copy.deepcopy(doc)
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.lstrip("/").split("/")]
    parent = doc
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    last = parts[-1]
    if isinstance(parent, list):
        index = int(last)
        if op == "delete":
            del parent[index]
        else:
            parent[index] = value
    elif op == "delete":
        assert last in parent, f"{pointer} does not exist; the mutation would be a no-op"
        del parent[last]
    else:
        parent[last] = value
    return doc


@pytest.fixture(scope="module")
def contracts():  # type: ignore[no-untyped-def]
    return load_contracts(SCHEMAS)


def test_schemas_are_valid_and_versioned(contracts) -> None:  # type: ignore[no-untyped-def]
    assert contracts.meta_problems() == []
    assert set(contracts.schemas) == {
        "urn:citerift:schema:contracts:v1:common",
        "urn:citerift:schema:contracts:v1:investigation",
    }


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_fixtures_pass(contracts, path: Path) -> None:  # type: ignore[no-untyped-def]
    assert [str(p) for p in contracts.validate(load(path))] == []


def test_fixtures_are_marked_synthetic() -> None:
    for path in VALID:
        assert load(path)["synthetic"] is True


@pytest.mark.negative
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_invalid_cases_rejected_for_the_intended_reason(contracts, case: dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
    base = load(FIXTURES / "valid" / case["base"])
    assert contracts.validate(base) == [], "base fixture must be valid so only the mutation can fail it"
    mutated = apply_mutation(base, case["op"], case["path"], case.get("value"))
    problems = contracts.validate(mutated)
    assert problems, f"{case['name']} was accepted"
    reasons = {p.keyword for p in problems} | {p.code for p in problems}
    assert case["expect"] in reasons, [str(p) for p in problems]


@pytest.mark.negative
def test_wrong_types_and_non_objects_rejected(contracts) -> None:  # type: ignore[no-untyped-def]
    for instance in (None, [], "investigation", 1):
        assert contracts.validate(instance)


@pytest.mark.regression
def test_no_field_can_express_claim_truth(contracts) -> None:  # type: ignore[no-untyped-def]
    """A retracted citation must never be recorded as proof that a claim is false."""
    text = json.dumps(contracts.schemas)
    for forbidden in ("claim_is_false", "claim_false", "is_false", "not_retracted"):
        assert f'"{forbidden}"' not in text


def _versioned_copy(tmp_path: Path, mutate: Any) -> Path:
    target = tmp_path / "contracts"
    target.mkdir()
    for path in SCHEMAS.rglob("*.schema.json"):
        schema = load(path)
        if schema["$id"].endswith(":investigation"):
            mutate(schema)
        rel = path.relative_to(SCHEMAS)
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(json.dumps(schema), encoding="utf-8")
    return target


@pytest.mark.regression
def test_additive_minor_version_is_backward_compatible(contracts, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    def additive(schema: dict[str, Any]) -> None:
        schema["x-citerift-version"] = "1.1.0"
        schema["properties"]["review_notes"] = {"type": "string"}

    newer = load_contracts(_versioned_copy(tmp_path, additive))
    assert check_backward_compatible(contracts, newer, [load(p) for p in VALID]) == []


@pytest.mark.negative
@pytest.mark.regression
def test_breaking_change_is_detected(contracts, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    def breaking(schema: dict[str, Any]) -> None:
        schema["x-citerift-version"] = "1.1.0"
        schema["properties"]["review_notes"] = {"type": "string"}
        schema["required"].append("review_notes")

    newer = load_contracts(_versioned_copy(tmp_path, breaking))
    broken = check_backward_compatible(contracts, newer, [load(p) for p in VALID])
    assert len(broken) == len(VALID)


@pytest.mark.negative
def test_loader_rejects_bad_schema_sets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"no \*\.schema\.json"):
        load_contracts(tmp_path)
    (tmp_path / "a.schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
    with pytest.raises(ValueError, match=r"no \$id"):
        load_contracts(tmp_path)


def test_contracts_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert contracts_main(["--schemas", str(SCHEMAS), "check-schemas"]) == 0
    assert contracts_main(["--schemas", str(SCHEMAS), "validate", *map(str, VALID)]) == 0
    out = capsys.readouterr().out
    assert "2 schemas checked, 0 problems" in out


@pytest.mark.negative
def test_contracts_cli_rejects_invalid_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    assert contracts_main(["--schemas", str(SCHEMAS), "validate", str(bad)]) == 1
    assert "INVALID" in capsys.readouterr().out
