"""Owner decision D-086 (committed evidence must show why the bibliographic check was unavailable, and VERIFY and replay
must reproduce it) and D-087, end to end: one SYNTHETIC article and SYNTHETIC Stage 02 rows run through the production
operations (``operations.run``, ``verify``, ``replay``) with every socket refused.

The article cites five retracted works by DOI, each with a citation template the record's fields judge differently:

- ``exact``: the record's own title: D-14, a positive;
- ``longer``: the record's title with words added: D-13c (``BIB_TITLE_EXTENDED``);
- ``erratum``: the record's own title with ``|type=Erratum``: D-13a (``BIB_TITLE_RELATED_OBJECT``);
- ``oversized``: a template above the source bound: D-13b (``BIB_SOURCE_LIMIT_EXCEEDED``);
- ``hidden``: a title holding ``{{lang|...}}``: D-13b (``BIB_PARSE_FAILED``).

The unavailable units' ``cited_bibliography`` evidence records the reason; VERIFY passes and replay reproduces every
claim from the committed source, extraction and records.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from step10_support import Inv

from citerift.investigation import operations as ops

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


def _import(folder: str, name: str) -> Any:
    sys.path.insert(0, str(REPO / "tests" / folder))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(REPO / "tests" / folder))


TITLE = "Thermal drift of synthetic lattice sensors in coastal stations"
AUTHORS = "Mara Q Lindqvist;Tomas Oyelaran"
CASES = {
    "exact": "{{cite journal |last1=Lindqvist |title=" + TITLE + " |journal=Synthetic Journal |doi=10.5555/e2e.1}}",
    "longer": "{{cite journal |last1=Lindqvist |title=" + TITLE + ": extended data |doi=10.5555/e2e.2}}",
    "erratum": "{{cite journal |last1=Lindqvist |title=" + TITLE + " |type=Erratum |doi=10.5555/e2e.3}}",
    "oversized": "{{cite journal |last1=Lindqvist |title=" + TITLE + " |quote=" + "x" * 16400 + " |doi=10.5555/e2e.4}}",
    "hidden": "{{cite journal |last1=Lindqvist |title={{lang|en|" + TITLE + "}} |doi=10.5555/e2e.5}}",
}
EXPECT = {
    "exact": ("D-14", "RETRACTED_WORK_CITED", None),
    "longer": ("D-13c", "UNRESOLVED_IDENTITY", "BIB_TITLE_EXTENDED"),
    "erratum": ("D-13a", "UNRESOLVED_IDENTITY", "BIB_TITLE_RELATED_OBJECT"),
    "oversized": ("D-13b", "UNRESOLVED_IDENTITY", "BIB_SOURCE_LIMIT_EXCEEDED"),
    "hidden": ("D-13b", "UNRESOLVED_IDENTITY", "BIB_PARSE_FAILED"),
}
DOI = {name: f"10.5555/e2e.{i}" for i, name in enumerate(CASES, start=1)}


def _bundle(tmp: Path) -> Path:
    w = _import("stage03", "wiki_support")
    text, body, notes = "", "<p>", []
    for i, (name, template) in enumerate(CASES.items(), start=1):
        text += f'Claim {i}.<ref name="{name}">{template}</ref>\n'
        note, ref = f"cite_note-{name}-{i}", f"cite_ref-{name}_{i}-0"
        body += f"Claim {i}." + w.ref_sup(i, note, ref, name=name)
        notes.append(w.note_li(note, [ref], f"<cite>{TITLE}. {w.doi_link(DOI[name])}</cite>"))
    body += "</p>" + w.references(notes)
    tmp.mkdir(parents=True, exist_ok=True)
    path: Path = w.bundle(tmp, text, body)
    return path


def _index(tmp: Path) -> Path:
    rde = _import("stage02", "rde_support")
    rows = [
        rde.row(
            **{
                "Record ID": str(i),
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": DOI[name],
                "RetractionDOI": f"10.5555/notice.{i}",
                "Title": TITLE,
                "Author": AUTHORS,
            }
        )
        for i, name in enumerate(CASES, start=1)
    ]
    (tmp / "index").mkdir(parents=True, exist_ok=True)
    index: Path = rde.build_rows(tmp / "index", rows)
    return index


@pytest.fixture(scope="module")
def investigation(tmp_path_factory: pytest.TempPathFactory) -> Inv:
    tmp = tmp_path_factory.mktemp("e2e-dt4")
    return Inv(tmp, _bundle(tmp / "bundle"), _index(tmp))


def _blobs(inv: Inv) -> list[Any]:
    """The committed JSON blobs (the source artifact and other raw blobs are skipped)."""
    out = []
    for p in sorted((inv.dir / "blobs").iterdir()):
        try:
            out.append(json.loads(p.read_bytes()))
        except ValueError:
            continue
    return out


def _claims(inv: Inv) -> dict[str, dict[str, Any]]:
    """The committed claims by case name, through the committed candidate inputs (candidate reference to DOI)."""
    inputs = next(
        b for b in _blobs(inv) if isinstance(b, dict) and str(b.get("schema", "")).endswith(":candidate-inputs")
    )
    name_of = {doi: name for name, doi in DOI.items()}
    case_of = {c["cand_ref"]: name_of[c["keys"][0]["normalized"]] for c in inputs["candidates"]}
    claims = [c for b in _blobs(inv) for c in _claim_items(b)]
    by_case = {case_of[c["cand_ref"]]: c for c in claims}
    assert all(c == by_case[case_of[c["cand_ref"]]] for c in claims), "a claim committed twice differs"
    return by_case


def _claim_items(value: Any) -> list[dict[str, Any]]:
    """Every committed claim (a mapping with ``cand_ref``, ``rule`` and ``class``) inside a committed blob."""
    out: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if {"cand_ref", "rule", "class"} <= set(value):
            out.append(value)
        for v in value.values():
            out += _claim_items(v)
    elif isinstance(value, list):
        for v in value:
            out += _claim_items(v)
    return out


def _items(value: Any) -> list[dict[str, Any]]:
    """Every evidence-like mapping (with ``kind`` and ``value``) inside a committed blob."""
    out: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "kind" in value and "value" in value:
            out.append(value)
        for v in value.values():
            out += _items(v)
    elif isinstance(value, list):
        for v in value:
            out += _items(v)
    return out


def test_each_case_decides_its_rule_and_the_unavailable_reason_is_committed(investigation: Inv) -> None:
    assert investigation.code == 0, investigation.out
    claims = _claims(investigation)
    assert set(claims) == set(CASES), sorted(claims)
    for name, (rule, cls, detail) in EXPECT.items():
        claim = claims[name]
        assert (claim["rule"], claim["class"]) == (rule, cls), (name, claim["rule"], claim["class"], claim["reasons"])
        if detail is not None:
            assert detail in claim["reasons"], (name, claim["reasons"])
        if rule == "D-13b":
            assert "BIBLIOGRAPHIC_CHECK_UNAVAILABLE" in claim["reasons"]


def test_the_unavailable_evidence_records_why(investigation: Inv) -> None:
    """D-086: the units' committed ``cited_bibliography`` items state the reason of each unavailable check (and no
    description); the described units carry their bib-2 fields."""
    values = [i["value"] for b in _blobs(investigation) for i in _items(b) if i["kind"] == "cited_bibliography"]
    unavailable = {v["unavailable"] for v in values if "unavailable" in v}
    assert unavailable == {"BIB_SOURCE_LIMIT_EXCEEDED", "BIB_PARSE_FAILED"}, values
    assert all(set(v) == {"version", "unavailable"} and v["version"] == "bib-2" for v in values if "unavailable" in v)
    described = [v for v in values if "fields" in v]
    assert len(described) == 3 and all(v["version"] == "bib-2" for v in described)


def test_verify_passes_and_replay_reproduces_every_claim(investigation: Inv) -> None:
    out, code = ops.verify(investigation.root, investigation.key)
    assert code == 0 and out["result"] == "passed", out
    rep, code = ops.replay(investigation.root, investigation.key)
    assert rep["result"] == "reproduced" and rep["first_difference"] is None, rep
    assert rep["claims"] == len(CASES)
