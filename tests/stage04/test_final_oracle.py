"""Final corrective cycle (owner decision D-083, item 3): the oracle of dt-3, kept as the reference of dt-4.

Owner decisions D-085 to D-087 replaced dt-3 by dt-4 in production (``test_final_oracle_dt4.py`` compares production
with the dt-4 oracle, which is itself checked against this oracle). The dt-3 model and oracle stay unchanged:

- ``simulations/stage04/dt3_reference.py`` is a new reference model; the frozen Step 4 model and oracle
  (``oracle/``) and the dt-2 model and oracle (``oracle-dt2/``) are kept unchanged and still pinned by
  ``test_simulation_step4.py`` and ``test_corrective_oracle.py``.
- ``simulations/stage04/oracle-dt3/`` is its oracle over 50,529,792 abstract cases (the dt-2 domain times the bit
  ``bc``: some event of the deciding lookup is in bib-1 MATERIAL_CONFLICT with the unit's own description); its
  manifest digest is pinned here, so any change to it is visible.
- With ``bc = False`` the dt-3 oracle equals the dt-2 oracle case for case (checked over the whole table), and with
  ``bc = True`` a decision differs from its dt-2 twin only where the twin is a D-14 positive, which becomes D-13a.
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

from citerift.investigation import dt1

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
sys.path.insert(0, str(SIM))

import decision_space as DS  # noqa: E402
import decision_space_dt2 as DS2  # noqa: E402
import decision_space_dt3 as DS3  # noqa: E402
import dt3_reference as R3  # noqa: E402

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
    assert manifest["table_version"] == R3.TABLE_VERSION == "dt-3" != dt1.TABLE_VERSION
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
