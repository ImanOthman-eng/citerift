"""Owner decisions D-086 and D-087: the oracle of dt-4 and the production table against it.

- ``simulations/stage04/dt4_reference.py`` is a new reference model (written separately from the specification); the
  Step 4, dt-2 and dt-3 models and oracles are kept unchanged.
- ``simulations/stage04/oracle-dt4/`` is its oracle over 101,059,584 abstract cases (the dt-2 domain times the state
  ``bib``: NONE, CONFLICT, UNAVAILABLE, NOT_ESTABLISHED); its manifest digest is pinned here, and the generator
  checked every case against the dt-2 and dt-3 oracles (``decision_space_dt4.py``; summary in
  ``final-cycle/simulation/decision_space_dt4_summary.json``, no violation).
- The table read back: with NONE it equals the dt-2 oracle and with CONFLICT the dt-3 oracle (bc True), and with
  UNAVAILABLE or NOT_ESTABLISHED a decision differs from its NONE twin only where the twin is a D-14 positive.
- The production table (``citerift.investigation.dt1``) gives the oracle's decision on one valid case per distinct
  decision and bib state, through the production detector on concrete inputs.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from array import array
from pathlib import Path
from typing import Any

import pytest
import step9_support as S9

from citerift.investigation import bibliographic as B
from citerift.investigation import dt1
from citerift.investigation.adapters.detector import dt1_detector

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
sys.path.insert(0, str(SIM))

import decision_space as DS  # noqa: E402
import decision_space_dt2 as DS2  # noqa: E402
import decision_space_dt3 as DS3  # noqa: E402
import decision_space_dt4 as DS4  # noqa: E402
import dt4_reference as R4  # noqa: E402
import stage02_abstraction as A  # noqa: E402

# Pinned digest of the dt-4 oracle manifest (decision_space_dt4.py). Changing the oracle needs a visible change here.
ORACLE_DT4_MANIFEST_SHA256 = "PENDING"
ORACLE_DT3_MANIFEST_SHA256 = "1c302c78161332b548b2bf81b3fdddf022b3f70ee24c7ed59485e33e255f7652"
ORACLE_DT2_MANIFEST_SHA256 = "60a21534a282dcb6269b0ec0a183c34e72e4ee8a259550311af601958196b8b0"

pytestmark = pytest.mark.simulation


def test_the_dt4_model_imports_neither_production_code_nor_an_earlier_model() -> None:
    tree = ast.parse((SIM / "dt4_reference.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {str(n.module) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    earlier = ("citerift", "dt1_reference", "dt2_reference", "dt3_reference", "bib_reference", "bib2_reference")
    assert not any(m.startswith(earlier) for m in names), names


def test_the_dt4_oracle_is_pinned_and_the_earlier_oracles_are_unchanged() -> None:
    oracle = SIM / "oracle-dt4"
    manifest_bytes = (oracle / "MANIFEST.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == ORACLE_DT4_MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((oracle / name).read_bytes()).hexdigest() == digest, name
    assert manifest["model_digest"] == DS4.model_digest()
    assert hashlib.sha256((SIM / "oracle-dt2" / "MANIFEST.json").read_bytes()).hexdigest() == ORACLE_DT2_MANIFEST_SHA256
    assert hashlib.sha256((SIM / "oracle-dt3" / "MANIFEST.json").read_bytes()).hexdigest() == ORACLE_DT3_MANIFEST_SHA256
    assert manifest["dt2_oracle_manifest_sha256"] == ORACLE_DT2_MANIFEST_SHA256
    assert manifest["dt3_oracle_manifest_sha256"] == ORACLE_DT3_MANIFEST_SHA256
    assert manifest["table_version"] == R4.TABLE_VERSION == dt1.TABLE_VERSION == "dt-4"
    assert manifest["cases"] == 4 * json.loads((SIM / "oracle-dt2" / "MANIFEST.json").read_bytes())["cases"]
    summary = json.loads(
        (REPO / "docs/verification/stage-04/final-cycle/simulation/decision_space_dt4_summary.json").read_text()
    )
    assert summary["oracle"] == manifest
    assert all(p["violations"] == 0 and p["checked"] > 0 for p in summary["properties"].values()), summary


_CACHE: dict[str, Any] = {}


def _tables() -> dict[str, tuple[list[dict[str, Any]], array]]:  # type: ignore[type-arg]
    if not _CACHE:
        _CACHE["d2"] = DS2.load_oracle(SIM / "oracle-dt2")
        _CACHE["d3"] = DS3.load_oracle(SIM / "oracle-dt3")
        _CACHE["d4"] = DS4.load_oracle(SIM / "oracle-dt4")
    return _CACHE


def _keys(decisions: list[dict[str, Any]]) -> list[str]:
    return [json.dumps(d, sort_keys=True) for d in decisions]


def test_the_dt4_table_read_back_against_the_dt2_and_dt3_tables() -> None:
    t = _tables()
    (dec2, tab2), (dec3, tab3), (dec4, tab4) = t["d2"], t["d3"], t["d4"]
    k2, k3, k4 = _keys(dec2), _keys(dec3), _keys(dec4)
    positive2 = {i for i, d in enumerate(dec2) if d["rule"] == "D-14"}
    rule_of = {i: d["rule"] for i, d in enumerate(dec4)}
    blocked = {"UNAVAILABLE": 0, "NOT_ESTABLISHED": 0}
    for shape, use, tt in DS.chunks():
        size = 2 * DS.chunk_size(shape)
        off2, off3, off4 = DS2.chunk_offset(shape, use, tt), DS3.chunk_offset(shape, use, tt), DS4.chunk_offset(
            shape, use, tt
        )
        twin = tab2[off2 : off2 + size]
        block = {s: tab4[off4 + n * size : off4 + (n + 1) * size] for n, s in enumerate(DS4.STATES)}
        assert [k4[i] for i in block["NONE"]] == [k2[i] for i in twin], (shape, use, tt)
        assert [k4[i] for i in block["NONE"]] == [k3[i] for i in tab3[off3 : off3 + size]]
        assert [k4[i] for i in block["CONFLICT"]] == [k3[i] for i in tab3[off3 + size : off3 + 2 * size]]
        for state, rule in (("UNAVAILABLE", "D-13b"), ("NOT_ESTABLISHED", "D-13c")):
            for i, (j2, j4) in enumerate(zip(twin, block[state], strict=True)):
                if j2 in positive2:
                    assert rule_of[j4] == rule, (shape, use, tt, i)
                    blocked[state] += 1
                else:
                    assert k4[j4] == k2[j2], (shape, use, tt, i)
    assert blocked == {"UNAVAILABLE": 1456, "NOT_ESTABLISHED": 1456}  # every dt-2 D-14 case, as for dt-3's D-13a


@pytest.mark.parametrize("chunk", [*[c for c in DS.chunks() if c[0] != "PAIR"][::5], ("PAIR", "CITED", 0)])
def test_the_dt4_oracle_matches_the_model(chunk: tuple[str, str, int]) -> None:
    dec4, tab4 = _tables()["d4"]
    off = DS4.chunk_offset(*chunk)
    step = 1999 if chunk[0] == "PAIR" else 1
    for i, c in enumerate(DS4.iter_chunk(*chunk)):
        if i % step == 0:
            assert dec4[tab4[off + i]] == R4.decide(c), c


# The detail reasons of the concrete pairs ``concretize`` builds for each bib state (step9_support): the abstract
# model's reasons are the rule's own; production adds the pair's bib-2 detail reasons (spec 6).
def _detail(state: str) -> tuple[str, ...]:
    if state == "UNAVAILABLE":
        return (S9.UNAVAILABLE_REASON,)
    cited = {"CONFLICT": S9.BC_CITED, "NOT_ESTABLISHED": S9.NE_CITED}.get(state)
    if cited is None:
        return ()
    return B.compare(B.CitedObject.from_json(cited), B.RecordObject.from_json(S9.BC_RECORD)).reasons


def test_the_concrete_pairs_have_their_states() -> None:
    def obj(cited: dict[str, Any]) -> str:
        return B.compare(B.CitedObject.from_json(cited), B.RecordObject.from_json(S9.BC_RECORD)).object

    assert (obj(S9.BC_CITED), _detail("CONFLICT")) == (B.MATERIAL_CONFLICT, ("BIB_AUTHORS_DISJOINT",))
    assert (obj(S9.NE_CITED), _detail("NOT_ESTABLISHED")) == (B.OBJ_NOT_ESTABLISHED, ("BIB_TITLE_EXTENDED",))


def expected(c: R4.Case) -> dict[str, Any]:
    dec = R4.decide(c)
    if dec["kind"] == "failure":
        return {"rule": dec["rule"], "failure": dec["reasons"][0]}
    rule_state = {"D-13a": "CONFLICT", "D-13b": "UNAVAILABLE", "D-13c": "NOT_ESTABLISHED"}.get(dec["rule"])
    extra = _detail(rule_state) if rule_state is not None else ()
    return {**dec, "reasons": sorted([*(S9.MODEL_REASON.get(r, r) for r in dec["reasons"]), *extra])}


def _representatives() -> dict[tuple[Any, ...], R4.Case]:
    """One valid dt-4 case per distinct decision (and shape and bib state): every valid NONE, DOI and PMID case, and
    every valid PAIR lookup triple under each use and taint set, each with rc False and True and every bib state."""
    reps: dict[tuple[Any, ...], R4.Case] = {}

    def keep(case: R4.Case) -> None:
        if A.valid(case):  # type: ignore[arg-type]
            reps.setdefault((case.shape, case.bib, *S9.model_key(expected(case))), case)

    for shape, use, t in DS.chunks():
        if shape != "PAIR":
            for case in DS4.iter_chunk(shape, use, t):
                keep(case)
    for use in R4.USES:
        for taint in A.taint_sets():
            for d, p, q2, sig in A.iter_valid_pair_lookups():
                for rc in (False, True):
                    for bib in DS4.STATES:
                        keep(R4.Case(use, "PAIR", taint, False, d, p, q2, *sig[3:], rc, bib))  # type: ignore[misc]
    return reps


@pytest.fixture(scope="module")
def representatives() -> dict[tuple[Any, ...], R4.Case]:
    return _representatives()


def test_production_dt4_gives_the_oracle_decision_on_every_distinct_decision(
    representatives: dict[tuple[Any, ...], R4.Case],
) -> None:
    seen = {"D-13a": 0, "D-13b": 0, "D-13c": 0, "D-14": 0, "rc": 0}
    for case in representatives.values():
        inp, _ = S9.concretize(case)
        exp = expected(case)
        out = dt1_detector(inp)
        claim = dict(out.claims[0][0])
        got = {"rule": claim["rule"], "class": claim["class"], "status": claim["status"], "value": claim["value"]}
        assert got == {k: exp[k] for k in got}, case
        assert sorted(claim["reasons"]) == exp["reasons"], case
        for rule in ("D-13a", "D-13b", "D-13c", "D-14"):
            seen[rule] += claim["rule"] == rule
        seen["rc"] += "IDENTIFIER_ROLE_COLLISION" in claim["reasons"]
    assert all(seen.values()), seen
