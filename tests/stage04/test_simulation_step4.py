"""Stage 04 Step 4: tests of the independent reference models and of the frozen dt-1 oracle.

These tests run the simulations in ``simulations/stage04`` on reduced but exhaustive slices (the full runs take
about fifteen minutes and are retained under ``docs/verification/stage-04/simulation``). They also pin the frozen
oracle, so that no later change, in particular by production code, can modify its own oracle silently.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from array import array
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "simulations" / "stage04"
EVIDENCE = ROOT / "docs" / "verification" / "stage-04" / "simulation"
sys.path.insert(0, str(SIM))

import bounds  # noqa: E402
import controller_model as C  # noqa: E402
import decision_space as S  # noqa: E402
import dt1_reference as R  # noqa: E402
import mutants as M  # noqa: E402
import stage02_abstraction as A  # noqa: E402
import stage02_conformance  # noqa: E402

# Every test here belongs to the simulation suite; mutant tests are also negative tests.
pytestmark = pytest.mark.simulation

# Pinned digest of the oracle manifest written by run_step4.py. Changing the oracle needs a visible change here.
ORACLE_MANIFEST_SHA256 = "411050772807cfbc5e2053431307516344984a759c489c746a490f1db3e27735"

# The modules that define the reference semantics import nothing from citerift; the conformance and bounds modules
# may read the accepted Stage 02 and Stage 03 engines; nothing may import Stage 04 production code.
PURE = ("dt1_reference.py", "stage02_abstraction.py", "decision_space.py", "controller_model.py", "mutants.py")
READS_ACCEPTED = {"stage02_conformance.py": ("citerift.retraction",), "bounds.py": ("citerift.wiki",)}


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_reference_models_are_independent_of_production_code() -> None:
    files = sorted(SIM.glob("*.py"))
    assert files
    for f in files:
        mods = _imports(f)
        assert not any(m == "citerift.investigation" or m.startswith("citerift.investigation.") for m in mods), f
        citerift = {m for m in mods if m == "citerift" or m.startswith("citerift.")}
        if f.name in PURE:
            assert not citerift, (f.name, citerift)
        elif f.name in READS_ACCEPTED:
            assert all(m.startswith(READS_ACCEPTED[f.name]) for m in citerift), (f.name, citerift)
        else:
            assert not citerift, (f.name, citerift)


def test_oracle_is_frozen() -> None:
    oracle = SIM / "oracle"
    manifest_bytes = (oracle / "MANIFEST.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == ORACLE_MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((oracle / name).read_bytes()).hexdigest() == digest, name
    assert manifest["model_digest"] == S.model_digest(), "the reference model changed: regenerate and review"
    assert manifest["model_version"] == R.MODEL_VERSION and manifest["table_version"] == R.TABLE_VERSION
    decisions, table = S.load_oracle(oracle)
    assert len(table) == manifest["cases"] == sum(S.chunk_size(s) for s, _, _ in S.chunks())
    raw = table.tobytes() if sys.byteorder == "little" else array("H", table).tobytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["table_raw_sha256"]
    assert len(decisions) == manifest["distinct_decisions"]


@pytest.mark.parametrize(
    "chunk",
    [(shape, use, t) for shape in ("NONE", "DOI", "PMID") for use in R.USES for t in range(len(S.TAINTS))]
    + [("PAIR", "CITED", 0), ("PAIR", "UNUSED", 7)],
)
def test_oracle_matches_reference_model(chunk: tuple[str, str, int]) -> None:
    decisions, table = _oracle()
    off = S.chunk_offset(*chunk)
    for k, c in enumerate(S.iter_chunk(*chunk)):
        assert decisions[table[off + k]] == R.decide(c), c


_ORACLE: list[object] = []


def _oracle() -> tuple[list[dict[str, object]], array]:  # type: ignore[type-arg]
    if not _ORACLE:
        _ORACLE.extend(S.load_oracle(SIM / "oracle"))
    return _ORACLE[0], _ORACLE[1]  # type: ignore[return-value]


def test_decision_properties_on_reduced_domain() -> None:
    assert M.run_decision_checks(R.decide, full=False) == {}


def test_full_run_evidence_has_no_violation() -> None:
    ds = json.loads((EVIDENCE / "decision_space_summary.json").read_text())
    assert ds["cases"] == 12_632_448
    assert ds["deep"] is True
    assert all(p["violations"] == 0 for p in ds["properties"].values())
    assert all(p["checked"] > 0 for p in ds["properties"].values())
    assert set(ds["rules_valid"]) == set(R.RULES) - {"D-5", "D-17"}
    mt = json.loads((EVIDENCE / "mutants.json").read_text())
    assert mt["mutants_detected"] == mt["mutants_injected"] == 19
    assert not mt["baseline_decision_violations"] and not mt["baseline_controller_violations"]


@pytest.mark.contracts
def test_stage02_conformance_of_the_abstraction() -> None:
    s = stage02_conformance.run()
    assert s["worlds"] == 192 and s["worlds_with_problems"] == 0 and s["signatures_equal"]
    assert s["stage02_case_probes"]["outside_contract"] == []


def test_abstraction_rejects_unreachable_signatures() -> None:
    d_no = ("no_record", "unc:not_found", False)
    q_ret = ("matched", "vf:retracted", False)
    # Q2 matched while neither key matched anything is not a Stage 02 result.
    c = R.Case("CITED", "PAIR", frozenset(), False, d_no, d_no, q_ret)
    assert "SIGNATURE_UNREACHABLE" in A.invalid_reasons(c)
    assert R.decide(c)["rule"] == "D-5"
    # A DOI-only query is never ambiguous.
    c = R.Case("CITED", "DOI", frozenset(), False, ("ambiguous_identity", "unc:ambiguous", False))
    assert A.invalid_reasons(c) and R.decide(c)["kind"] == "failure"


def test_identity_conflict_case_obokata_shape() -> None:
    """The arwiki 76190003 un-00013 shape: the DOI's record carries another PMID (witness in Q1(d)), the PMID names
    another work, Q2 is ambiguous. With any lookup unavailable the conflict still wins (owner decision F-01)."""
    d = ("matched", "vf:retracted", False)
    p = ("matched", "vf:retracted", False)
    q2 = ("ambiguous_identity", "unc:ambiguous", False)
    c = R.Case("CITED", "PAIR", frozenset(), False, d, p, q2, wd=True, wp=True, w2=True)
    assert A.valid(c)
    dec = R.decide(c)
    assert dec["class"] == "IDENTITY_CONFLICT" and dec["kind"] == "needs_resolution" and dec["value"] is None
    unavailable = ("unavailable", "none", False)
    c2 = R.Case("CITED", "PAIR", frozenset(), False, d, unavailable, unavailable, wd=True)
    assert A.valid(c2)
    dec2 = R.decide(c2)
    assert dec2["class"] == "IDENTITY_CONFLICT" and "LOOKUP_PARTIAL" in dec2["reasons"]


@pytest.mark.parametrize(("live", "conflict"), [(False, False), (False, True), (True, False), (True, True)])
def test_controller_model_properties(live: bool, conflict: bool) -> None:
    r = C.check(live, conflict)
    assert {k: v["violations"] for k, v in r["properties"].items() if v["violations"]} == {}
    assert r["max_attempts_per_step"]["ACQUIRE"] == (C.A_MAX + C.F_MAX if live else C.A_MAX)
    assert all(n == C.A_MAX for s, n in r["max_attempts_per_step"].items() if s != "ACQUIRE")
    reached = set(r["lifecycle_states_reached"])
    assert {"CREATED", "RUNNING", "FAILED", "STALE", "CORRUPT"} <= reached
    assert ("NEEDS_RESOLUTION" in reached) == conflict and ("COMPLETED" in reached) == (not conflict)
    assert ("BLOCKED" in reached) == live
    # F-09: a retained bundle converges to one content identity; a live capture does not (one per ACQUIRE attempt).
    assert r["completed_content_identities"] == (C.A_MAX + C.F_MAX if live else 1)


def test_controller_reaches_every_declared_state() -> None:
    lifecycle: set[str] = set()
    step_states: set[str] = set()
    for live in (False, True):
        for conflict in (False, True):
            r = C.check(live, conflict)
            lifecycle |= set(r["lifecycle_states_reached"])
            step_states |= {x.split(":")[1] for x in r["step_states_reached"]}
    assert set(C.LIFECYCLE) <= lifecycle
    assert set(C.STEP_STATES) == step_states


@pytest.mark.negative
@pytest.mark.parametrize("mid", sorted(M.CONTROLLER_MUTANTS))
def test_controller_mutants_are_detected(mid: str) -> None:
    _desc, patches = M.CONTROLLER_MUTANTS[mid]
    saved = C.LIMIT["states"]
    C.LIMIT["states"] = 30_000
    try:
        # One scenario per mutant: the conflict scenario for MC-4, the retained bundle for MC-8, else a live capture.
        scenario = {"MC-4": (True, True), "MC-8": (False, False)}.get(mid, (True, False))
        with M._apply_patches(patches):
            caught = M.run_controller_checks((scenario,))
    finally:
        C.LIMIT["states"] = saved
    assert caught, mid


@pytest.mark.negative
@pytest.mark.parametrize("mid", sorted(M.DECISION_MUTANTS))
def test_decision_mutants_are_detected(mid: str) -> None:
    _desc, fn = M.DECISION_MUTANTS[mid]
    assert M.run_decision_checks(fn, full=False), mid


def test_f11_symbolic_bounds() -> None:
    sym = bounds.symbolic()
    assert sym["attempts"]["live_total"] == 7 * C.A_MAX + C.A_MAX + C.F_MAX == 30
    assert sym["attempts"]["retained_total"] == 8 * C.A_MAX == 24
    assert sym["execution_records"]["live"] == 62 and sym["execution_records"]["retained"] == 50
    assert sym["retained_bound_s"]["isolated_workers"] == 720.0


def test_f11_characterization_response_head_is_not_bounded_by_the_timeout() -> None:
    """Characterizes the F-11 finding (not a desired behaviour): Stage 03's transport lets a server that drips the
    response head keep an attempt past its timeout. If this test starts failing, Stage 03 bounds the head and the
    F-11 conclusion must be revisited."""
    drip = [(0.0, b"HTTP/1.1 200 OK\r\n")] + [(0.4, b"X")] * 5 + [(0.0, b"-a: b\r\nContent-Length: 2\r\n\r\nok")]
    r = bounds._measure(drip, 0.8)
    assert r["elapsed_s"] >= 1.8 and r["outcome"].startswith("status 200")
