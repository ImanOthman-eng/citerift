"""Final corrective cycle (owner decision D-083, item 3): the oracle of dt-3 and the production table against it.

- ``simulations/stage04/dt3_reference.py`` is a new reference model; the frozen Step 4 model and oracle
  (``oracle/``) and the dt-2 model and oracle (``oracle-dt2/``) are kept unchanged and still pinned by
  ``test_simulation_step4.py`` and ``test_corrective_oracle.py``.
- ``simulations/stage04/oracle-dt3/`` is its oracle over 50,529,792 abstract cases (the dt-2 domain times the bit
  ``bc``: some event of the deciding lookup is in bib-1 MATERIAL_CONFLICT with the unit's own description); its
  manifest digest is pinned here, so any change to it is visible.
- With ``bc = False`` the dt-3 oracle equals the dt-2 oracle case for case (checked over the whole table), and with
  ``bc = True`` a decision differs from its dt-2 twin only where the twin is a D-14 positive, which becomes D-13a.
- The production table (``citerift.investigation.dt1``) gives the oracle's decision on one valid case per distinct
  decision, with ``bc`` False and True (and ``rc`` False and True), through the production detector on concrete
  inputs.
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
import dt3_reference as R3  # noqa: E402
import stage02_abstraction as A  # noqa: E402

# Pinned digest of the dt-3 oracle manifest (decision_space_dt3.py). Changing the oracle needs a visible change here.
ORACLE_DT3_MANIFEST_SHA256 = "1c302c78161332b548b2bf81b3fdddf022b3f70ee24c7ed59485e33e255f7652"
ORACLE_DT2_MANIFEST_SHA256 = "60a21534a282dcb6269b0ec0a183c34e72e4ee8a259550311af601958196b8b0"

pytestmark = pytest.mark.simulation


def test_the_dt3_model_imports_neither_production_code_nor_an_earlier_model() -> None:
    tree = ast.parse((SIM / "dt3_reference.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {str(n.module) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m.startswith(("citerift", "dt1_reference", "dt2_reference")) for m in names), names


def test_the_dt3_oracle_is_pinned_and_the_earlier_oracles_are_unchanged() -> None:
    oracle = SIM / "oracle-dt3"
    manifest_bytes = (oracle / "MANIFEST.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == ORACLE_DT3_MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((oracle / name).read_bytes()).hexdigest() == digest, name
    assert manifest["model_digest"] == DS3.model_digest()
    dt2_manifest = (SIM / "oracle-dt2" / "MANIFEST.json").read_bytes()
    assert hashlib.sha256(dt2_manifest).hexdigest() == ORACLE_DT2_MANIFEST_SHA256
    assert manifest["dt2_oracle_manifest_sha256"] == ORACLE_DT2_MANIFEST_SHA256
    assert manifest["table_version"] == R3.TABLE_VERSION == dt1.TABLE_VERSION == "dt-3"
    assert manifest["cases"] == 2 * json.loads(dt2_manifest)["cases"]


_CACHE: dict[str, Any] = {}


def _tables() -> tuple[list[dict[str, Any]], array, list[dict[str, Any]], array]:  # type: ignore[type-arg]
    if not _CACHE:
        _CACHE["d2"] = DS2.load_oracle(SIM / "oracle-dt2")
        _CACHE["d3"] = DS3.load_oracle(SIM / "oracle-dt3")
    return (*_CACHE["d2"], *_CACHE["d3"])


def test_bc_false_equals_the_dt2_oracle_and_bc_only_blocks_positives() -> None:
    dec2, tab2, dec3, tab3 = _tables()
    as3 = {json.dumps(d, sort_keys=True): i for i, d in enumerate(dec3)}
    map23 = array("H", (as3.get(json.dumps(d, sort_keys=True), 0xFFFF) for d in dec2))
    positive2 = {i for i, d in enumerate(dec2) if d["rule"] == "D-14"}
    d13a = {i for i, d in enumerate(dec3) if d["rule"] == "D-13a"}
    blocked = 0
    for shape, use, t in DS.chunks():
        size = 2 * DS.chunk_size(shape)
        off2, off3 = DS2.chunk_offset(shape, use, t), DS3.chunk_offset(shape, use, t)
        twin = tab2[off2 : off2 + size]
        assert tab3[off3 : off3 + size] == array("H", (map23[i] for i in twin)), (shape, use, t)
        with_bc = tab3[off3 + size : off3 + 2 * size]
        for i, (j2, j3) in enumerate(zip(twin, with_bc, strict=True)):
            if j2 in positive2:
                assert j3 in d13a, (shape, use, t, i)
                blocked += 1
            else:
                assert j3 == map23[j2], (shape, use, t, i)
    assert blocked == 1456  # every dt-2 D-14 case of the domain (decision_space_dt3_summary.json, rules no_bc|D-14)


@pytest.mark.parametrize("chunk", [*[c for c in DS.chunks() if c[0] != "PAIR"][::5], ("PAIR", "CITED", 0)])
def test_the_dt3_oracle_matches_the_model(chunk: tuple[str, str, int]) -> None:
    _, _, dec3, tab3 = _tables()
    off = DS3.chunk_offset(*chunk)
    step = 997 if chunk[0] == "PAIR" else 1
    for i, c in enumerate(DS3.iter_chunk(*chunk)):
        if i % step == 0:
            assert dec3[tab3[off + i]] == R3.decide(c), c


# The bib-1 reasons of the concrete conflicting pair ``concretize`` builds for ``bc`` (step9_support.BC_CITED and
# BC_RECORD): the abstract model's D-13a reasons are the rule's own; production adds the pair's bib-1 reasons (spec 6).
BC_REASONS = tuple(B.compare(B.CitedObject.from_json(S9.BC_CITED), B.RecordObject.from_json(S9.BC_RECORD)).reasons)


def test_the_concrete_bc_pair_is_a_material_conflict() -> None:
    out = B.compare(B.CitedObject.from_json(S9.BC_CITED), B.RecordObject.from_json(S9.BC_RECORD))
    assert out.object == B.MATERIAL_CONFLICT and BC_REASONS == ("BIB_AUTHORS_DISJOINT",)


def expected(c: R3.Case) -> dict[str, Any]:
    dec = R3.decide(c)
    if dec["kind"] == "failure":
        return {"rule": dec["rule"], "failure": dec["reasons"][0]}
    extra = BC_REASONS if dec["rule"] == "D-13a" else ()
    return {**dec, "reasons": sorted([*(S9.MODEL_REASON.get(r, r) for r in dec["reasons"]), *extra])}


def _representatives() -> dict[tuple[Any, ...], R3.Case]:
    """One valid dt-3 case per distinct decision (and shape): every valid NONE, DOI and PMID case, and every valid PAIR
    lookup triple under each use and taint set, each with rc and bc False and True."""
    reps: dict[tuple[Any, ...], R3.Case] = {}

    def keep(case: R3.Case) -> None:
        if A.valid(case):  # type: ignore[arg-type]
            reps.setdefault((case.shape, case.bc, *S9.model_key(expected(case))), case)

    for shape, use, t in DS.chunks():
        if shape != "PAIR":
            for case in DS3.iter_chunk(shape, use, t):
                keep(case)
    for use in R3.USES:
        for taint in A.taint_sets():
            for d, p, q2, sig in A.iter_valid_pair_lookups():
                for rc in (False, True):
                    for bc in (False, True):
                        keep(R3.Case(use, "PAIR", taint, False, d, p, q2, *sig[3:], rc, bc))  # type: ignore[misc]
    return reps


@pytest.fixture(scope="module")
def representatives() -> dict[tuple[Any, ...], R3.Case]:
    return _representatives()


def test_production_dt3_gives_the_oracle_decision_on_every_distinct_decision(
    representatives: dict[tuple[Any, ...], R3.Case],
) -> None:
    seen = {"D-13a": 0, "D-14": 0, "rc": 0}
    for case in representatives.values():
        inp, _ = S9.concretize(case)
        exp = expected(case)
        out = dt1_detector(inp)
        claim = dict(out.claims[0][0])
        got = {"rule": claim["rule"], "class": claim["class"], "status": claim["status"], "value": claim["value"]}
        assert got == {k: exp[k] for k in got}, case
        assert sorted(claim["reasons"]) == exp["reasons"], case
        seen["D-13a"] += claim["rule"] == "D-13a"
        seen["D-14"] += claim["rule"] == "D-14"
        seen["rc"] += "IDENTIFIER_ROLE_COLLISION" in claim["reasons"]
    assert all(seen.values()), seen
