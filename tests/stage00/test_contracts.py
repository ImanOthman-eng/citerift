"""Versioned data contracts: positive fixtures, mutation-based negative cases, compatibility."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from citerift.contracts import check_backward_compatible, load_contracts
from citerift.contracts.formats import loads_strict
from citerift.contracts.validate import main as contracts_main

pytestmark = [pytest.mark.contracts]

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "schemas" / "contracts"
FIXTURES = Path(__file__).parent / "fixtures" / "contracts" / "v1"
VALID = sorted((FIXTURES / "valid").glob("*.json"))
CASES = loads_strict((FIXTURES / "invalid_cases.json").read_text(encoding="utf-8"))


def load(path: Path) -> Any:
    return loads_strict(path.read_text(encoding="utf-8"))


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


@pytest.mark.negative
def test_malformed_or_unversioned_schema_is_reported() -> None:
    from citerift.contracts.validate import ContractSet

    broken = ContractSet({"urn:citerift:schema:test:broken": {"type": "no-such-type"}})
    codes = {p.code for p in broken.meta_problems()}
    assert codes == {"SCHEMA_INVALID", "SCHEMA_UNVERSIONED"}


@pytest.mark.negative
def test_structural_violation_is_reported_as_schema_violation(contracts) -> None:  # type: ignore[no-untyped-def]
    problems = contracts.validate({"schema_version": "1.0.0"})
    assert problems
    assert {p.code for p in problems} == {"SCHEMA_VIOLATION"}


# ---------------------------------------------------------------- portability
#
# JSON Schema patterns are ECMA-262 regular expressions, but the Python
# validator runs them with ``re.search``: there ``$`` also matches before a
# trailing newline and ``\s``/``\d``/``\w`` mean something different. Every
# CITERIFT pattern is written in the subset where both engines agree.

PORTABLE_NON_SPACE = "[^\\s\\x00-\\x1f\\x7f-\\x9f\\ufeff]"
EDGE_CHARACTERS = [
    "\n",
    "\r",
    "\t",
    " ",
    "\x00",
    "\x1c",
    "\x7f",
    "\x85",
    "\xa0",
    "\u2028",
    "\u3000",
    "\ufeff",
    "\u0661",
]
PATTERN_SAMPLES = [
    "1.0.1",
    "0f8fad5b-d9cb-469f-a165-70867728950e",
    "2026-10-25T12:00:00Z",
    "2026-10-25T12:00:00.5Z",
    "10.5555/citerift.synthetic.0001",
    "10.5555/بحث-٢٠٢٠",
    "12345678",
    "en",
    "zh-yue",
    "https://example.org/a?b=c",
    "0" * 64,
    "a" * 40,
    "cmsg_ABCDEFGHIJKL",
    "00",
    "2020",
    "2020-03",
    "2020-03-01",
    "abc_def",
    "A.b-1:c",
]


def _schema_patterns() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def walk(node: Any, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "pattern" and isinstance(value, str):
                    found.append((where, value))
                else:
                    walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{where}/{i}")

    for path in sorted([*SCHEMAS.rglob("*.schema.json"), *(REPO / "schemas" / "governance").rglob("*.schema.json")]):
        walk(load(path), path.name)
    return found


@pytest.mark.regression
def test_schema_patterns_use_the_portable_subset() -> None:
    patterns = _schema_patterns()
    assert len(patterns) > 10
    for where, pattern in patterns:
        assert pattern.startswith("^"), where
        assert pattern.endswith("$(?!\\n)"), f"{where}: '$' must be followed by (?!\\n): {pattern}"
        stripped = pattern.replace(PORTABLE_NON_SPACE, "")
        for token in ("\\d", "\\D", "\\w", "\\W", "\\b", "\\B", "\\s", "\\S"):
            assert token not in stripped, f"{where}: {token} differs between Python and ECMA-262: {pattern}"


def _node() -> str | None:
    import shutil

    return shutil.which("node") or next((p for p in ("/opt/node22/bin/node",) if Path(p).exists()), None)


@pytest.mark.regression
def test_schema_patterns_agree_with_ecma262() -> None:
    """Differential test: Python ``re.search`` against JavaScript ``RegExp`` (u flag)."""
    import os
    import re
    import subprocess

    node = _node()
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node is required in CI for the ECMA-262 differential test")
        pytest.skip("node not installed")
    cases = []
    for _, pattern in _schema_patterns():
        for base in PATTERN_SAMPLES:
            variants = [base]
            for c in EDGE_CHARACTERS:
                variants += [base + c, c + base, base[:1] + c + base[1:], base[:-1] + c]
            cases += [(pattern, s) for s in variants]
    script = (
        "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "process.stdout.write(JSON.stringify(cases.map(([p, s]) => new RegExp(p, 'u').test(s))));"
    )
    result = subprocess.run([node, "-e", script], input=json.dumps(cases), capture_output=True, text=True, check=True)
    js = json.loads(result.stdout)
    disagreements = [(p, s) for (p, s), j in zip(cases, js, strict=True) if (re.search(p, s) is not None) != j]
    assert disagreements == [], disagreements[:10]
    assert any(js), "the samples must exercise matching strings, not only rejections"


@pytest.mark.regression
@pytest.mark.parametrize("seed", [3, 20261025])
def test_schema_patterns_agree_with_ecma262_on_random_strings(seed: int) -> None:
    """Seeded property: random strings over an adversarial alphabet get the same verdict in both engines."""
    import os
    import random
    import re
    import subprocess

    node = _node()
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node is required in CI for the ECMA-262 differential test")
        pytest.skip("node not installed")
    rng = random.Random(seed)
    alphabet = [*"0123456789abcfz-./:_TZ", *EDGE_CHARACTERS, "\u062d", "\u00e9", "\U0001f600"]
    cases = []
    for _, pattern in _schema_patterns():
        for _ in range(60):
            base = rng.choice(PATTERN_SAMPLES)
            if rng.random() < 0.5:
                i = rng.randrange(len(base) + 1)
                base = base[:i] + "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3))) + base[i:]
            cases.append((pattern, base))
    script = (
        "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "process.stdout.write(JSON.stringify(cases.map(([p, s]) => new RegExp(p, 'u').test(s))));"
    )
    result = subprocess.run([node, "-e", script], input=json.dumps(cases), capture_output=True, text=True, check=True)
    js = json.loads(result.stdout)
    disagreements = [(p, s) for (p, s), j in zip(cases, js, strict=True) if (re.search(p, s) is not None) != j]
    assert disagreements == [], f"seed {seed}: {disagreements[:10]}"
    assert 0 < sum(js) < len(js)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        ("/citations/0/article/title", "حمض نووي"),
        ("/subject_paper/identifiers/doi", "10.5555/بحث-٢٠٢٠"),
        ("/citations/1/article/language", "zh-yue"),
        ("/created_at", "2026-10-25T12:00:00.123456Z"),
        ("/subject_paper/retraction_date/value", "2020-02-29"),
    ],
)
def test_multilingual_and_precise_values_accepted(contracts, pointer: str, value: Any) -> None:  # type: ignore[no-untyped-def]
    mutated = apply_mutation(load(FIXTURES / "valid" / "investigation_full.json"), "set", pointer, value)
    assert [str(p) for p in contracts.validate(mutated)] == []


@pytest.mark.regression
def test_events_in_order_with_fractional_seconds_accepted(contracts) -> None:  # type: ignore[no-untyped-def]
    doc = load(FIXTURES / "valid" / "investigation_full.json")
    doc["events"] = [
        {"at": "2026-10-25T12:00:00Z", "kind": "first_event", "description": "first"},
        {"at": "2026-10-25T12:00:00.5Z", "kind": "second_event", "description": "second"},
        {"at": "2026-10-25T12:00:01Z", "kind": "third_event", "description": "third"},
    ]
    assert [str(p) for p in contracts.validate(doc)] == []


@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("value", ["2020-02-30", "2021-02-29", "2020-04-31"])
def test_impossible_retraction_dates_rejected(contracts, value: str) -> None:  # type: ignore[no-untyped-def]
    base = load(FIXTURES / "valid" / "investigation_full.json")
    for pointer, mutated in (
        (
            "/subject_paper/retraction_date/value",
            apply_mutation(base, "set", "/subject_paper/retraction_date/value", value),
        ),
        (
            "/subject_paper/retraction_date/alternatives/1/value",
            apply_mutation(
                base,
                "set",
                "/subject_paper/retraction_date",
                {
                    "status": "conflicting",
                    "value": None,
                    "alternatives": [
                        {"value": "2020-03", "provenance": base["subject_paper"]["retraction_date"]["provenance"]},
                        {"value": value, "provenance": base["subject_paper"]["retraction_date"]["provenance"]},
                    ],
                },
            ),
        ),
    ):
        problems = contracts.validate(mutated)
        assert [(p.code, p.path) for p in problems] == [("INVALID_DATE", pointer)], [str(p) for p in problems]


@pytest.mark.negative
@pytest.mark.regression
def test_duplicate_json_keys_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from citerift.contracts.formats import DuplicateKeyError, loads_strict

    with pytest.raises(DuplicateKeyError):
        loads_strict('{"status": "completed", "status": "failed"}')
    record = tmp_path / "dup.json"
    text = (FIXTURES / "valid" / "investigation_full.json").read_text(encoding="utf-8")
    record.write_text(
        text.replace('"status": "completed"', '"status": "completed", "status": "failed"', 1), encoding="utf-8"
    )
    assert contracts_main(["--schemas", str(SCHEMAS), "validate", str(record)]) == 1
    assert "UNREADABLE" in capsys.readouterr().out


@pytest.mark.negative
def test_date_time_format_rejects_impossible_instants() -> None:
    from citerift.contracts.formats import FORMAT_CHECKER, parse_utc_timestamp

    assert parse_utc_timestamp("2024-02-29T23:59:59Z") is not None
    for bad in ("2026-02-31T12:00:00Z", "2026-13-01T00:00:00Z", "2026-10-25T24:00:00Z", "2026-10-25T12:00:00", "x"):
        assert parse_utc_timestamp(bad) is None
        assert not FORMAT_CHECKER.conforms(bad, "date-time")
    assert FORMAT_CHECKER.conforms(5, "date-time"), "non-strings are the type keyword's job"
