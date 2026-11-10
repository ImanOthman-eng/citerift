"""Fail-first evidence: deliberate defects injected into the reference models must be detected (Step 4 item 9).

Each mutant changes one thing in a copy of the decision model or the controller model, through a function argument or
a temporary patch that is always undone. The Step 4 checks are then run unchanged. A mutant is **detected** when at
least one check reports a violation; the names of the checks that caught it are retained.

Decision mutants run on the mutant domain: every NONE, DOI and PMID case (49,536 cases, all checks) and every
cited, untainted PAIR case whose three lookups are within the Stage 02 contract or unavailable (21^3 x 16 = 148,176
cases, all checks except the strengthening ones). Controller mutants run the full controller exploration of
``controller_model`` for the four scenarios.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from itertools import product
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controller_model as C
import decision_space as S
import dt1_reference as R
import stage02_abstraction as A

Decide = Callable[[R.Case], dict[str, Any]]


# The reduced domain used by the fast test: one lookup value per state and projection family.
REDUCED_LOOKUPS: list[R.Lookup] = [
    ("matched", "vf:retracted", False),
    ("matched", "conf", False),
    ("matched", "unc", False),
    ("notice_only", "unc:notice", False),
    ("ambiguous_identity", "unc:ambiguous", False),
    ("no_record", "unc:not_found", False),
    ("unavailable", "none", False),
]


def mutant_domain(full: bool = True) -> Iterator[tuple[R.Case, bool]]:
    """Full: every NONE, DOI and PMID case, and the cited untainted PAIR cases with contract or unavailable lookups.
    Reduced (fast test): uses CITED and UNUSED, taint empty or {IDENTIFIER_UNCONFIRMED}, and seven PAIR lookups."""
    uses = R.USES if full else ("CITED", "UNUSED")
    taints = (
        range(len(S.TAINTS))
        if full
        else [S.TAINTS.index(frozenset()), S.TAINTS.index(frozenset({"IDENTIFIER_UNCONFIRMED"}))]
    )
    for shape in ("NONE", "DOI", "PMID"):
        for use in uses:
            for t in taints:
                for c in S.iter_chunk(shape, use, t):
                    yield c, True
    contract = [lk for lk in R.lookup_values() if R.well_formed(lk)] + [S.UNAVAILABLE] if full else REDUCED_LOOKUPS
    for d, p, q2 in product(contract, contract, contract):
        for wd, wp, w2, co in S.BITS:
            yield R.Case("CITED", "PAIR", frozenset(), False, d, p, q2, wd, wp, w2, co), False


def run_decision_checks(decide: Decide, full: bool = True) -> dict[str, int]:
    tally = S.Tally()
    for c, deep in mutant_domain(full):
        dec = decide(c)
        if dec.get("rule") is None:
            tally.check("TOTAL", False, c, dec)
            continue
        S.check_case(c, dec, A.valid(c), tally, deep=deep, decide=decide)
    return dict(tally.violations)


def _rules_moved(rule: str, before: str) -> tuple[str, ...]:
    out = [r for r in R.RULES if r != rule]
    out.insert(out.index(before), rule)
    return tuple(out)


def d_swap_identity_positive(c: R.Case) -> dict[str, Any]:
    return R.decide(c, _rules_moved("D-14", "D-6"))


def d_unavailable_before_identity(c: R.Case) -> dict[str, Any]:
    return R.decide(c, _rules_moved("D-13", "D-6"))


def d_remove_catch_all(c: R.Case) -> dict[str, Any]:
    return R.decide(c, tuple(r for r in R.RULES if r != "D-17"))


def d_remove_adapter_check(c: R.Case) -> dict[str, Any]:
    return R.decide(c, tuple(r for r in R.RULES if r != "D-5"))


def d_unavailable_as_no_record(c: R.Case) -> dict[str, Any]:
    nr: R.Lookup = ("no_record", "unc:not_found", False)

    def hide(lk: R.Lookup | None) -> R.Lookup | None:
        return nr if lk is not None and lk[0] == "unavailable" else lk

    return R.decide(
        R.Case(c.use, c.shape, c.taint, c.multi, hide(c.d), hide(c.p), hide(c.q2), c.wd, c.wp, c.w2, c.coname)
    )


def d_no_record_means_not_retracted(c: R.Case) -> dict[str, Any]:
    dec = R.decide(c)
    if dec.get("class") == "NOT_FOUND_IN_CHECKED_SOURCES":
        dec = {**dec, "value": "not_retracted"}
    return dec


def d_notice_as_retracted(c: R.Case) -> dict[str, Any]:
    dec = R.decide(c)
    if dec.get("class") == "NOTICE_CITED":
        dec = {
            **dec,
            "class": "RETRACTED_WORK_CITED",
            "status": "verified_fact",
            "value": "retracted",
            "disposition": "REPORT_FINDING",
            "kind": "positive",
        }
    return dec


def d_kappa_ignores_pair_witness(c: R.Case) -> dict[str, Any]:
    return R.decide(R.Case(c.use, c.shape, c.taint, c.multi, c.d, c.p, c.q2, c.wd, c.wp, False, c.coname))


def d_taint_ignored(c: R.Case) -> dict[str, Any]:
    return R.decide(R.Case(c.use, c.shape, frozenset(), c.multi, c.d, c.p, c.q2, c.wd, c.wp, c.w2, c.coname))


def d_loose_positive_guard(c: R.Case) -> dict[str, Any]:
    """D-14 reads only the status prefix (``vf:``), so a verified_fact without a contract value becomes positive."""
    L = c.deciding()
    if c.use == "CITED" and L is not None and L[0] == "matched" and L[1].startswith("vf:") and not R.well_formed(L):
        dec = R.decide(c)
        if dec["rule"] == "D-17":
            return {
                "rule": "D-14",
                "class": "RETRACTED_WORK_CITED",
                "status": "verified_fact",
                "value": "retracted",
                "disposition": "REPORT_FINDING",
                "kind": "positive",
                "reasons": [],
            }
    return R.decide(c)


def _step3_contract_violations(c: R.Case) -> list[str]:
    """D-5 exactly as Step 3 wrote it (fb39ede): invalid_query, or the P2 disagreement when all three are available."""
    out = []
    if any(lk[0] == "invalid_query" for lk in c.lookups()):
        out.append("INVALID_QUERY")
    if c.shape == "PAIR" and all(R.available(lk) for lk in (c.d, c.p, c.q2)) and c.q2 is not None:
        if (c.wd or c.wp or c.w2) != (c.q2[0] == "ambiguous_identity"):
            out.append("P2_DISAGREEMENT")
    return out


def d_step3_adapter_check(c: R.Case) -> dict[str, Any]:
    with patched(R, "contract_violations", _step3_contract_violations):
        return R.decide(c)


DECISION_MUTANTS: dict[str, tuple[str, Decide]] = {
    "MD-1": ("swap identity-conflict (D-6) and positive (D-14) precedence", d_swap_identity_positive),
    "MD-2": ("remove the catch-all fail-closed rule D-17", d_remove_catch_all),
    "MD-3": (
        "hide lookup-unavailable as no-record (adapter maps unavailable to no_record)",
        d_unavailable_as_no_record,
    ),
    "MD-4": ("treat no-record as 'not retracted' (value of D-16)", d_no_record_means_not_retracted),
    "MD-5": (
        "plan draft order: operational failure (D-13) before identity conflict (D-6)",
        d_unavailable_before_identity,
    ),
    "MD-6": ("remove the adapter-consistency rule D-5", d_remove_adapter_check),
    "MD-7": ("count a notice as the retracted work", d_notice_as_retracted),
    "MD-8": ("coherence ignores the pair query's witness (w2)", d_kappa_ignores_pair_witness),
    "MD-9": ("ignore identifier taint", d_taint_ignored),
    "MD-10": ("positive guard reads only the status, not the contract value", d_loose_positive_guard),
    "MD-11": ("D-5 as written in Step 3 (invalid_query and the P2 disagreement only)", d_step3_adapter_check),
}


@contextmanager
def patched(obj: Any, name: str, value: Any) -> Iterator[None]:
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


SCENARIOS = ((False, False), (False, True), (True, False), (True, True))


def run_controller_checks(scenarios: tuple[tuple[bool, bool], ...] = SCENARIOS) -> dict[str, int]:
    out: dict[str, int] = {}
    for live, conflict in scenarios:
        r = C.check(live, conflict)
        for k, v in r["properties"].items():
            if v["violations"]:
                out[k] = out.get(k, 0) + v["violations"]
    return out


_legal, _successors, _apply, _lam = C.legal, C.successors, C.apply, C.lam


def m_guard_allows_out_of_succeeded(rec: C.Record, s: C.State, live: bool) -> str | None:
    kind, i, _detail = rec
    if kind == "step_started" and i >= 0 and s.steps[i].status == "succeeded" and C.running_index(s) is None:
        return "T-RESTART"
    return _legal(rec, s, live)


def m_controller_reruns_committed(s: C.State, live: bool, conflict: bool) -> list[C.Edge]:
    out = _successors(s, live, conflict)
    if s.alive and not s.fresh and C.lam(s) == "RUNNING" and C.running_index(s) is None:
        done = [i for i, st in enumerate(s.steps) if st.status == "succeeded"]
        if done:
            rec = ("step_started", done[-1], "next")
            steps = list(s.steps)
            steps[done[-1]] = C.Step(status="running", attempts=1)
            out.append(("mutant:rerun", rec, C.replace(s, steps=tuple(steps))))
    return out


def m_reset_retry_counter(s: C.State, rec: C.Record, live: bool = False) -> C.State:
    t = _apply(s, rec, live)
    if rec[0] == "step_started":
        steps = list(t.steps)
        steps[rec[1]] = C.replace(steps[rec[1]], phi=0)
        t = C.replace(t, steps=tuple(steps))
    return t


def m_needs_resolution_completed(s: C.State) -> str | None:
    lc = _lam(s)
    return "COMPLETED" if lc == "NEEDS_RESOLUTION" else lc


def m_retry_off_by_one(rec: C.Record, s: C.State, live: bool) -> str | None:
    kind, i, detail = rec
    if kind == "step_failed" and detail == "retryable" and i >= 0 and s.steps[i].status == "running":
        if C.STEPS[i] in C.RETRYABLE and s.steps[i].phi + 1 <= C.BUDGET["A"]:
            return "T-FAIL-R"
    return _legal(rec, s, live)


def m_retry_off_by_one_controller(s: C.State, live: bool, conflict: bool) -> list[C.Edge]:
    out = []
    for label, rec, t in _successors(s, live, conflict):
        if rec is not None and rec[0] == "step_failed" and rec[2] == "budget" and label == "env:step_fails_retryable":
            changed: C.Record = (rec[0], rec[1], "retryable")
            out.append((label, changed, C.apply(s, changed, live)))
        else:
            out.append((label, rec, t))
    return out


def m_deferral_off_by_one(s: C.State, live: bool, conflict: bool) -> list[C.Edge]:
    out = []
    for label, rec, t in _successors(s, live, conflict):
        if rec is not None and rec[2] == "deferral_budget":
            changed: C.Record = ("step_deferred", rec[1], None)
            out.append((label, changed, C.apply(s, changed, live)))
        else:
            out.append((label, rec, t))
    return out


def m_content_before_root(rec: C.Record, s: C.State, live: bool) -> str | None:
    kind, i, _detail = rec
    if kind == "content" and i >= 0 and s.steps[i].status == "running" and C.running_index(s) == i:
        return "T-CONTENT"
    return _legal(rec, s, live)


def m_live_capture_semantics_for_retained(s: C.State, rec: C.Record, live: bool = False) -> C.State:
    return _apply(s, rec, True)


CONTROLLER_MUTANTS: dict[str, tuple[str, list[tuple[str, Any]]]] = {
    "MC-1": ("append guard permits an edge out of succeeded (restart)", [("legal", m_guard_allows_out_of_succeeded)]),
    "MC-2": ("a committed step is rerun by the controller", [("successors", m_controller_reruns_committed)]),
    "MC-3": ("retry counter reset when an attempt starts", [("apply", m_reset_retry_counter)]),
    "MC-4": ("NEEDS_RESOLUTION reported as COMPLETED", [("lam", m_needs_resolution_completed)]),
    "MC-5": (
        "retry budget off by one in the guard and the controller",
        [("legal", m_retry_off_by_one), ("successors", m_retry_off_by_one_controller)],
    ),
    "MC-6": ("deferral budget off by one (a seventh deferral is allowed)", [("successors", m_deferral_off_by_one)]),
    "MC-7": ("root-binding rule M-9 removed from the guard", [("legal", m_content_before_root)]),
    "MC-8": (
        "retained bundle re-acquired as a new capture on each attempt (F-09)",
        [("apply", m_live_capture_semantics_for_retained)],
    ),
}


def run(out: Path | None = None, full: bool = True) -> dict[str, Any]:
    results: dict[str, Any] = {}
    baseline_decision = run_decision_checks(R.decide, full)
    for mid, (desc, fn) in DECISION_MUTANTS.items():
        caught = run_decision_checks(fn, full)
        results[mid] = {"description": desc, "detected": bool(caught), "caught_by": caught}
    baseline_controller = run_controller_checks()
    C.LIMIT["states"] = 60_000
    try:
        for mid, (desc, patches) in CONTROLLER_MUTANTS.items():
            with _apply_patches(patches):
                caught = run_controller_checks()
            results[mid] = {"description": desc, "detected": bool(caught), "caught_by": caught}
    finally:
        C.LIMIT["states"] = 400_000
    summary = {
        "baseline_decision_violations": baseline_decision,
        "baseline_controller_violations": baseline_controller,
        "domain": "full mutant domain" if full else "reduced mutant domain (fast test)",
        "mutants_injected": len(results),
        "mutants_detected": sum(1 for r in results.values() if r["detected"]),
        "mutants": results,
    }
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "mutants.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


@contextmanager
def _apply_patches(patches: list[tuple[str, Any]]) -> Iterator[None]:
    saved = [(name, getattr(C, name)) for name, _ in patches]
    try:
        for name, fn in patches:
            setattr(C, name, fn)
        yield
    finally:
        for name, fn in saved:
            setattr(C, name, fn)


if __name__ == "__main__":
    s = run(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(json.dumps({k: v for k, v in s.items() if k != "mutants"}, indent=1))
    for mid, r in s["mutants"].items():
        print(mid, r["detected"], r["description"], sorted(r["caught_by"]))
    ok = not s["baseline_decision_violations"] and not s["baseline_controller_violations"]
    raise SystemExit(0 if ok and s["mutants_detected"] == s["mutants_injected"] else 1)
