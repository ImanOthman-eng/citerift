"""Corrective cycle (owner decision D-071 section 5): the post-failure oracle of dt-2 and the production table against
it.

- ``simulations/stage04/dt2_reference.py`` is a new reference model; the frozen Step 4 model and its oracle are kept
  and still pinned by ``test_simulation_step4.py``.
- ``simulations/stage04/oracle-dt2/`` is its frozen oracle over 25,264,896 abstract cases; its manifest digest is
  pinned here, so any change to it is visible.
- With ``rc = False`` the dt-2 oracle equals the frozen dt-1 oracle case for case (checked over the whole table).
- The production table (``citerift.investigation.dt1``, table version dt-2) gives the oracle's decision on one valid
  case per distinct decision, with and without ``rc``, through the production detector on concrete inputs.
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

from citerift.investigation import dt1
from citerift.investigation.adapters.detector import dt1_detector

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
sys.path.insert(0, str(SIM))

import decision_space as DS  # noqa: E402
import decision_space_dt2 as DS2  # noqa: E402
import dt2_reference as R2  # noqa: E402
import stage02_abstraction as A  # noqa: E402

# Pinned digest of the dt-2 oracle manifest (decision_space_dt2.py). Changing the oracle needs a visible change here.
ORACLE_DT2_MANIFEST_SHA256 = "60a21534a282dcb6269b0ec0a183c34e72e4ee8a259550311af601958196b8b0"

pytestmark = pytest.mark.simulation


def test_the_dt2_model_imports_neither_production_code_nor_the_frozen_model() -> None:
    tree = ast.parse((SIM / "dt2_reference.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {str(n.module) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m.startswith("citerift") or m.startswith("dt1_reference") for m in names), names


def test_the_dt2_oracle_is_frozen() -> None:
    oracle = SIM / "oracle-dt2"
    manifest_bytes = (oracle / "MANIFEST.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == ORACLE_DT2_MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((oracle / name).read_bytes()).hexdigest() == digest, name
    assert manifest["model_digest"] == DS2.model_digest()
    assert (
        manifest["frozen_dt1_oracle_manifest_sha256"]
        == hashlib.sha256((SIM / "oracle/MANIFEST.json").read_bytes()).hexdigest()
    )
    assert manifest["table_version"] == dt1.TABLE_VERSION == R2.TABLE_VERSION == "dt-2"
    assert manifest["cases"] == 2 * json.loads((SIM / "oracle/MANIFEST.json").read_text())["cases"]


_CACHE: dict[str, Any] = {}


def _tables() -> tuple[list[dict[str, Any]], array, list[dict[str, Any]], array]:  # type: ignore[type-arg]
    if not _CACHE:
        _CACHE["d2"] = DS2.load_oracle(SIM / "oracle-dt2")
        _CACHE["d1"] = DS.load_oracle(SIM / "oracle")
    return (*_CACHE["d1"], *_CACHE["d2"])


def test_rc_false_equals_the_frozen_dt1_oracle_case_for_case() -> None:
    dec1, tab1, dec2, tab2 = _tables()
    as2 = {json.dumps(d, sort_keys=True): i for i, d in enumerate(dec2)}
    map12 = array("H", (as2.get(json.dumps(d, sort_keys=True), 0xFFFF) for d in dec1))
    for shape, use, t in DS.chunks():
        off1, size = DS.chunk_offset(shape, use, t), DS.chunk_size(shape)
        off2 = DS2.chunk_offset(shape, use, t)
        got = tab2[off2 : off2 + size]
        want = array("H", (map12[i] for i in tab1[off1 : off1 + size]))
        assert got == want, (shape, use, t)


@pytest.mark.parametrize("chunk", [*[c for c in DS.chunks() if c[0] != "PAIR"][::5], ("PAIR", "CITED", 0)])
def test_the_dt2_oracle_matches_the_model(chunk: tuple[str, str, int]) -> None:
    _, _, dec2, tab2 = _tables()
    off = DS2.chunk_offset(*chunk)
    step = 997 if chunk[0] == "PAIR" else 1
    for i, c in enumerate(DS2.iter_chunk(*chunk)):
        if i % step == 0:
            assert dec2[tab2[off + i]] == R2.decide(c), c


def _representatives() -> dict[tuple[Any, ...], R2.Case]:
    """One valid dt-2 case per distinct decision (and shape): every valid NONE, DOI and PMID case, and every valid PAIR
    lookup triple under each use and taint set, each with rc False and True."""
    reps: dict[tuple[Any, ...], R2.Case] = {}

    def keep(case: R2.Case) -> None:
        if A.valid(case):  # type: ignore[arg-type]
            reps.setdefault((case.shape, *S9.model_key(expected(case))), case)

    for shape, use, t in DS.chunks():
        if shape != "PAIR":
            for case in DS2.iter_chunk(shape, use, t):
                keep(case)
    for use in R2.USES:
        for taint in A.taint_sets():
            for d, p, q2, sig in A.iter_valid_pair_lookups():
                for rc in (False, True):
                    keep(R2.Case(use, "PAIR", taint, False, d, p, q2, *sig[3:], rc))  # type: ignore[misc]
    return reps


def expected(c: R2.Case) -> dict[str, Any]:
    dec = R2.decide(c)
    if dec["kind"] == "failure":
        return {"rule": dec["rule"], "failure": dec["reasons"][0]}
    return {**dec, "reasons": sorted(S9.MODEL_REASON.get(r, r) for r in dec["reasons"])}


@pytest.fixture(scope="module")
def representatives() -> dict[tuple[Any, ...], R2.Case]:
    return _representatives()


def test_production_dt2_gives_the_oracle_decision_on_every_distinct_decision(
    representatives: dict[tuple[Any, ...], R2.Case],
) -> None:
    seen_rc = 0
    for case in representatives.values():
        inp, _ = S9.concretize(case)
        exp = expected(case)
        out = dt1_detector(inp)
        claim = dict(out.claims[0][0])
        got = {"rule": claim["rule"], "class": claim["class"], "status": claim["status"], "value": claim["value"]}
        assert got == {k: exp[k] for k in got}, case
        assert sorted(claim["reasons"]) == exp["reasons"], case
        seen_rc += "IDENTIFIER_ROLE_COLLISION" in claim["reasons"]
    assert seen_rc > 0
