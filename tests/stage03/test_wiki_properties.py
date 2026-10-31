"""Metamorphic properties, schema resources, the import boundary and the acquisition simulation.

The generated articles are SYNTHETIC: seeded random combinations of reference constructs in both languages. A
metamorphic property states how the extraction must change (or not) when the source changes in a way whose effect
is known, so no expected output has to be written by hand.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle

from citerift.wiki import schemas
from citerift.wiki.canonical import canonical_bytes
from citerift.wiki.extract import extract_bundle

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261028

EN_BLOCKS = [
    'Claim.<ref name="{n}">{{{{cite journal |title=Work {k} |doi=10.{p}/{s} |pmid={m}}}}}</ref>',
    'Again.<ref name="{n}" />',
    "Plain.<ref>See https://doi.org/10.{p}/{s} for details.</ref>",
    "Labelled.<ref>Author. Title. doi:10.{p}/{s}</ref>",
    "Wrapped.<ref>{{{{doi|10.{p}/{s}}}}}</ref>",
    "Prose mentions 10.{p}/{s} without a reference.",
    "Hidden.<!-- doi=10.{p}/{s} -->",
    "Nowiki.<nowiki>10.{p}/{s}</nowiki>",
    "Note.{{{{efn|An aside with {{{{cite web |url=https://example.org/{s} |title=X}}}}}}}}",
    "Short.{{{{sfn|Author|2020|p=4}}}}",
    "Marked.<ref>{{{{cite journal |title=Gone |doi=10.{p}/{s}}}}} {{{{Retracted|doi=10.{p}/r{s}}}}}</ref>",
]
AR_BLOCKS = [
    'ادعاء.<ref name="{n}">{{{{استشهاد بدورية محكمة |عنوان=عمل {k} |دوي=10.{p}/{s} |بمد={m}}}}}</ref>',
    'مرة أخرى.<ref name="{n}" />',
    "نص.<ref>انظر https://doi.org/10.{p}/{s}</ref>",
    "دوي.<ref>{{{{دوي|10.{p}/{s}}}}}</ref>",
    "تعليق.<!-- 10.{p}/{s} -->",
]


def article(rng: random.Random, wiki: str, blocks: int = 8) -> str:
    pool = AR_BLOCKS if wiki == "ar" else EN_BLOCKS
    parts = []
    for k in range(blocks):
        tpl = rng.choice(pool)
        parts.append(
            tpl.format(
                n=f"r{rng.randint(1, 4)}",
                k=k,
                p=rng.randint(1000, 99999),
                s=f"abc.{rng.randint(1, 999)}",
                m=rng.randint(1, 99_999_999),
            )
        )
    return " ".join(parts) + "\n\n== References ==\n{{reflist}}\n"


def facts(doc: dict[str, Any], shift: int = 0) -> list[tuple[Any, ...]]:
    return sorted(
        (
            i["scheme"],
            i["role"],
            i["normalization"]["normalized"],
            i["source"]["raw"],
            i["source"]["cp_start"] - shift,
            i["source"]["cp_end"] - shift,
        )
        for i in doc["identifiers"]
    )


def structure(doc: dict[str, Any], shift: int = 0) -> list[tuple[Any, ...]]:
    return sorted(
        (c["kind"], c["binding_state"], c["source"]["cp_start"] - shift, len(c["use_ids"]), len(c["unit_ids"]))
        for c in doc["containers"]
    )


def cases(n: int) -> list[tuple[str, str]]:
    rng = random.Random(SEED)
    return [(w, article(rng, w)) for w in ("en", "ar") for _ in range(n)]


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text"), cases(6))
def test_prepending_prose_shifts_every_anchor_and_changes_nothing_else(tmp_path: Path, wiki: str, text: str) -> None:
    prefix = "مقدمة بلا مراجع، 😀 é\n\n" if wiki == "ar" else "An introduction without references, 😀 é\n\n"
    base = extract_bundle(bundle(tmp_path, text, wiki=wiki, name="a"), isolated=False)
    moved = extract_bundle(bundle(tmp_path, prefix + text, wiki=wiki, name="b"), isolated=False)
    assert facts(moved, len(prefix)) == facts(base) and facts(base)
    assert structure(moved, len(prefix)) == structure(base)
    assert moved["accounting"]["identifiers_by_role"] == base["accounting"]["identifiers_by_role"]


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text"), cases(4))
def test_appending_an_unrelated_section_keeps_existing_items(tmp_path: Path, wiki: str, text: str) -> None:
    tail = "\n== See also ==\n* [[Something]]\n"
    base = extract_bundle(bundle(tmp_path, text, wiki=wiki, name="a"), isolated=False)
    more = extract_bundle(bundle(tmp_path, text + tail, wiki=wiki, name="b"), isolated=False)
    assert facts(more) == facts(base) and structure(more) == structure(base)


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text"), cases(4))
def test_consistent_renaming_of_reference_names_keeps_bindings(tmp_path: Path, wiki: str, text: str) -> None:
    renamed = text
    for k in range(1, 5):
        renamed = renamed.replace(f'name="r{k}"', f'name="q{k}"')
    base = extract_bundle(bundle(tmp_path, text, wiki=wiki, name="a"), isolated=False)
    other = extract_bundle(bundle(tmp_path, renamed, wiki=wiki, name="b"), isolated=False)
    assert structure(other) == structure(base) and facts(other) == facts(base)
    assert [u["binding"] for u in other["uses"]] == [u["binding"] for u in base["uses"]]


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
def test_spacing_inside_template_fields_does_not_change_keys_or_roles(tmp_path: Path, wiki: str) -> None:
    name, field = ("استشهاد بدورية محكمة", "دوي") if wiki == "ar" else ("cite journal", "doi")
    tight = f"A.<ref>{{{{{name}|{field}=10.1234/AbC.9}}}}</ref>\n"
    loose = f"A.<ref>{{{{ {name} \n | {field} =  10.1234/AbC.9 \n}}}}</ref>\n"
    a = extract_bundle(bundle(tmp_path, tight, wiki=wiki, name="a"), isolated=False)
    b = extract_bundle(bundle(tmp_path, loose, wiki=wiki, name="b"), isolated=False)

    def key(doc: dict[str, Any]) -> list[tuple[str, str, str]]:
        # A field anchor covers the value as written; the Stage 02 normalizer records the outer-whitespace trim.
        return [(i["role"], i["normalization"]["normalized"], i["source"]["raw"].strip()) for i in doc["identifiers"]]

    assert key(a) == key(b) == [("primary_citation_field", "10.1234/abc.9", "10.1234/AbC.9")]
    assert "TRIM_OUTER_WHITESPACE" in b["identifiers"][0]["normalization"]["transformations"]


@pytest.mark.regression
def test_ascii_case_changes_the_raw_text_but_not_the_key(tmp_path: Path) -> None:
    lower = extract_bundle(
        bundle(tmp_path, "A.<ref>{{cite journal |doi=10.1000/abc}}</ref>\n", name="a"), isolated=False
    )
    upper = extract_bundle(
        bundle(tmp_path, "A.<ref>{{cite journal |doi=10.1000/ABC}}</ref>\n", name="b"), isolated=False
    )
    assert (
        lower["identifiers"][0]["normalization"]["normalized"] == upper["identifiers"][0]["normalization"]["normalized"]
    )
    assert lower["identifiers"][0]["source"]["raw"] != upper["identifiers"][0]["source"]["raw"]


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text"), cases(3))
def test_swapping_two_paragraphs_permutes_but_keeps_the_identifier_multiset(
    tmp_path: Path, wiki: str, text: str
) -> None:
    body, _, refs = text.partition("\n\n== References ==")
    swapped = "Second paragraph.<ref>{{cite journal |doi=10.5555/two}}</ref>\n\n" + body + "\n\n== References ==" + refs
    first = body + "\n\nSecond paragraph.<ref>{{cite journal |doi=10.5555/two}}</ref>\n\n== References ==" + refs
    a = extract_bundle(bundle(tmp_path, first, wiki=wiki, name="a"), isolated=False)
    b = extract_bundle(bundle(tmp_path, swapped, wiki=wiki, name="b"), isolated=False)

    def multiset(doc: dict[str, Any]) -> list[tuple[str, str, str]]:
        return sorted((i["scheme"], i["role"], str(i["normalization"]["normalized"])) for i in doc["identifiers"])

    assert multiset(a) == multiset(b)


@pytest.mark.reproducibility
def test_output_does_not_depend_on_hash_seed_or_locale(tmp_path: Path) -> None:
    text = cases(1)[0][1]
    b = bundle(tmp_path, text)
    code = (
        "import sys; from citerift.wiki.extract import extract_bundle; from citerift.wiki.canonical import "
        "canonical_bytes; sys.stdout.buffer.write(canonical_bytes(extract_bundle(sys.argv[1], isolated=False)))"
    )
    outputs = set()
    for seed, lang in (("0", "C"), ("1", "ar_SA.UTF-8"), ("4242", "en_US.UTF-8")):
        env = {**os.environ, "PYTHONHASHSEED": seed, "LANG": lang, "LC_ALL": lang, "TZ": "Asia/Riyadh"}
        proc = subprocess.run(
            [sys.executable, "-c", code, str(b)], capture_output=True, env=env, check=True, timeout=120
        )
        outputs.add(proc.stdout)
    assert len(outputs) == 1
    assert outputs.pop() == canonical_bytes(extract_bundle(b, isolated=False))


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text"), cases(5))
def test_generated_articles_satisfy_accounting_and_schema(tmp_path: Path, wiki: str, text: str) -> None:
    doc = extract_bundle(bundle(tmp_path, text, wiki=wiki), isolated=False)
    assert all(check["ok"] for check in doc["accounting"]["checks"]), doc["accounting"]["checks"]
    assert schemas.validate(doc, schemas.EXTRACTION) == []
    assert not any(
        i["role"] in ("primary_citation_field",) and "Retracted" in json.dumps(i["context"]) for i in doc["identifiers"]
    )


# ----------------------------------------------------------------------------------------- schemas


@pytest.mark.contracts
@pytest.mark.parametrize("name", ["capture", "extraction", "verification", "common"])
def test_wiki_schemas_are_valid_draft_2020_12(name: str) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((ROOT / "schemas" / "wiki" / "v1" / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == f"urn:citerift:schema:wiki:v1:{name}"


@pytest.mark.contracts
def test_schema_root_override_and_missing_root(tmp_path: Path) -> None:
    code = (
        "import json, sys; from citerift.wiki import schemas\n"
        "try:\n    schemas.contracts(); print('ok')\nexcept schemas.SchemaRootUnavailable as e: print('unavailable')\n"
    )
    for root, expected in ((ROOT / "schemas", "ok"), (tmp_path, "unavailable")):
        env = {**os.environ, "CITERIFT_SCHEMAS": str(root)}
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60, check=False
        )
        assert out.stdout.strip() == expected, out.stderr


@pytest.mark.contracts
def test_verification_without_schemas_fails_closed(tmp_path: Path) -> None:
    b = bundle(tmp_path, "A.<ref>{{cite journal |doi=10.1000/x}}</ref>\n")
    code = (
        "import json, sys; from citerift.wiki.verify import verify_bundle; "
        "print(json.dumps(verify_bundle(sys.argv[1])))"
    )
    env = {**os.environ, "CITERIFT_SCHEMAS": str(tmp_path / "none")}
    out = subprocess.run(
        [sys.executable, "-c", code, str(b)], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    report = json.loads(out.stdout)
    assert not report["verified"] and "SCHEMA_ROOT_UNAVAILABLE" in {i["code"] for i in report["issues"]}


@pytest.mark.contracts
def test_accepted_contract_schemas_are_untouched() -> None:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "c3346d1", "--", "schemas/contracts"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip("git history is not available in this checkout")
    assert proc.stdout.strip() == ""


# --------------------------------------------------------------------------------------- boundary


@pytest.mark.security
def test_runtime_imports_stay_inside_the_stage_boundary(tmp_path: Path) -> None:
    b = bundle(tmp_path, "A.<ref>{{cite journal |doi=10.1000/x |pmid=5}}</ref>\n")
    code = (
        "import sys, json\n"
        "from citerift.wiki import cli, capture, fetch\n"
        "from citerift.wiki.extract import extract_bundle\n"
        "from citerift.wiki.verify import verify_bundle, replay_bundle\n"
        "d = extract_bundle(sys.argv[1], isolated=False); verify_bundle(sys.argv[1], d); replay_bundle(sys.argv[1])\n"
        "print(json.dumps(sorted(sys.modules)))\n"
    )
    out = subprocess.run([sys.executable, "-c", code, str(b)], capture_output=True, text=True, check=True, timeout=120)
    loaded = set(json.loads(out.stdout))
    forbidden = {
        "sqlite3",
        "citerift.retraction.query",
        "citerift.retraction.policy",
        "citerift.retraction.advisory",
        "citerift.retraction.local_model",
    }
    assert loaded & forbidden == set()
    assert {m for m in loaded if m.startswith("citerift.retraction")} <= {
        "citerift.retraction",
        "citerift.retraction.identifiers",
    }


@pytest.mark.security
def test_no_dynamic_code_execution_in_the_engine() -> None:
    for path in sorted((ROOT / "src" / "citerift" / "wiki").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "eval(" not in text and "exec(" not in text, path.name
        assert "shell=True" not in text, path.name


# --------------------------------------------------------------------------------------- simulation


@pytest.mark.simulation
def test_fetch_policy_simulation_holds_every_invariant() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "simulations" / "stage03" / "fetch_policy_sim.py"), "400", str(SEED)],
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    summary = json.loads(proc.stdout)
    assert summary["failure_count"] == 0 and summary["sequences"] == 400
    assert {"DEFERRED_RETRY_AFTER", "ATTEMPTS_EXHAUSTED", "None"} <= set(summary["outcomes"])


@pytest.mark.simulation
def test_reconciliation_perturbation_simulation_has_no_wrong_attachment() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "simulations" / "stage03" / "reconcile_perturbation_sim.py"), "40", str(SEED)],
        capture_output=True,
        text=True,
        check=True,
        timeout=600,
    )
    summary = json.loads(proc.stdout)
    assert summary["failure_count"] == 0
    per = summary["per_perturbation"]
    assert per["none"]["linked"] == per["none"]["uses"] > 0
    assert all(p["wrong"] == 0 and p["wrong_notes"] == 0 for p in per.values())
