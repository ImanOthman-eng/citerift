"""Exhaustive enumeration of the dt-1 abstract input domain and its properties (Step 4 items 2 to 4).

The **domain** is the product, per shape, of every abstract input dt-1 reads (``dt1_reference.Case``):

- ``NONE``: use (3) x taint subset (8) x witness bits (16)                                   =        384
- ``DOI``, ``PMID``: use (3) x taint (8) x multi (2) x lookup value (32) x witness bits (16) = 24,576 each
- ``PAIR``: use (3) x taint (8) x Q1(d) (32) x Q1(p) (32) x Q2 (32) x witness bits (16)    = 12,582,912

Structural restrictions (the case encoding cannot express them, so they are not enumerated): a ``NONE`` candidate
has no lookup and no ``CO_REPORTED_MULTIPLE``; a ``DOI`` (``PMID``) candidate has only the Q1(DOI) (Q1(PMID))
lookup; a ``PAIR`` candidate has all three lookups and never ``CO_REPORTED_MULTIPLE`` (S-6.5, CD-1).

Every case is decided by the reference model, classified valid or invalid by ``stage02_abstraction`` and checked
against the properties listed in ``PROPERTIES``. The decisions are written, in the canonical enumeration order, to
the frozen oracle (``oracle/``): a table of distinct decisions and one 16-bit decision index per case.

Run: ``uv run python simulations/stage04/decision_space.py --out <dir>`` (about five minutes on four processes).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from array import array
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dt1_reference as R
import stage02_abstraction as A

LOOKUPS = R.lookup_values()
BITS = list(product((False, True), repeat=4))  # (wd, wp, w2, coname)
TAINTS = A.taint_sets()
SHAPE_ORDER = ("NONE", "DOI", "PMID", "PAIR")
FINDING_KINDS = ("positive", "not_found")
UNAVAILABLE: R.Lookup = ("unavailable", "none", False)

PROPERTIES = {
    "TOTAL": "every case is decided by exactly one rule of D-1..D-17 (no case falls through the table)",
    "P1_VALID_NO_FAILURE": "no valid case reaches D-5 or D-17 (MM P1; D-17 unreachable on Stage 02's model)",
    "FAIL_CLOSED_INVALID": "no invalid case yields a positive finding or NOT_FOUND_IN_CHECKED_SOURCES",
    "DETERMINISM": "deciding an equal case built from fresh objects gives an identical decision, and the first-true "
    "rule equals the minimum-index true guard",
    "IDENTITY_DOMINANCE": "a cited PAIR candidate with kappa = INCOMPATIBLE is IDENTITY_CONFLICT whatever its "
    "projections, taint and availability (P3 a, gate 04-D); an invalid one may instead fail DETECT (D-5), never "
    "anything else",
    "NO_FINDING_UNDER_CONFLICT": "no case with kappa = INCOMPATIBLE yields a positive finding or not-found",
    "NO_NEGATIVE": "every value is a positive value, not_found_in_checked_sources or null; no class, value or reason "
    "means 'not retracted' (S-7.5, M-12)",
    "P5_NOT_FOUND_CONDITIONS": "NOT_FOUND_IN_CHECKED_SOURCES implies cited, keyed, untainted, every lookup available, "
    "none invalid, deciding lookup no_record with value not_found_in_checked_sources (MM P5)",
    "FAILURE_CONTAINMENT": "an unavailable lookup never yields a finding or not-found; kind failure only from D-5/D-17",
    "NOTICE_SEPARATION": "a notice_only deciding lookup never yields a finding or not-found; NOTICE_CITED has no "
    "value; a positive PAIR finding beside a notice_only key lookup carries KEY_RESULTS_DIFFER",
    "POSITIVE_FROM_DECIDING": "a positive class is reached only from a matched deciding lookup with a verified_fact "
    "projection of the same value",
    "UNKNOWN_PRESERVATION": "a deciding lookup outside the contract, or with an uncertain, ambiguous, gap or "
    "conflicting projection, never yields a finding or not-found",
    "MONOTONE_GUARDS": "when a monotone guard (D-5 invalid_query, D-6, D-7, D-8, D-13) holds, the result is no "
    "finding and no not-found (MM P4)",
    "STRENGTHEN_TAINT": "adding a taint reason never moves a case to a later tier and never creates a finding",
    "STRENGTHEN_WITNESS": "adding a witness bit (wd, wp, w2) never creates a finding; between valid cases it never "
    "moves a case to a later tier",
    "STRENGTHEN_UNAVAILABLE": "making any lookup unavailable never creates a finding or not-found",
    "AB2_REASONS": "every abstention, needs-resolution and failure carries at least one reason code (AB-2)",
    "STATUS_CONSISTENCY": "status, value and disposition are the functions of the class in SPEC 7.2 and 7.6",
    "P2_VALID": "on valid PAIR cases with all three lookups available, kappa = INCOMPATIBLE iff Q2 is "
    "ambiguous_identity (MM P2)",
    "TAINT_CLASS_INDEPENDENCE": "rule and class do not depend on which taint reasons are present, only on whether one "
    "is (checked across chunks)",
}


def chunks() -> list[tuple[str, str, int]]:
    """Canonical chunk order: shape, use, taint index."""
    return [(s, u, t) for s in SHAPE_ORDER for u in R.USES for t in range(len(TAINTS))]


def iter_chunk(shape: str, use: str, t: int) -> Iterator[R.Case]:
    taint = TAINTS[t]
    if shape == "NONE":
        for wd, wp, w2, co in BITS:
            yield R.Case(use, shape, taint, False, None, None, None, wd, wp, w2, co)
    elif shape in ("DOI", "PMID"):
        for multi in (False, True):
            for lk in LOOKUPS:
                for wd, wp, w2, co in BITS:
                    d, p = (lk, None) if shape == "DOI" else (None, lk)
                    yield R.Case(use, shape, taint, multi, d, p, None, wd, wp, w2, co)
    else:
        for d in LOOKUPS:
            for p in LOOKUPS:
                for q2 in LOOKUPS:
                    for wd, wp, w2, co in BITS:
                        yield R.Case(use, shape, taint, False, d, p, q2, wd, wp, w2, co)


def chunk_size(shape: str) -> int:
    return {"NONE": 16, "DOI": 2 * 32 * 16, "PMID": 2 * 32 * 16, "PAIR": 32**3 * 16}[shape]


def dkey(dec: dict[str, Any]) -> str:
    return json.dumps(dec, sort_keys=True, separators=(",", ":"))


def tier(dec: dict[str, Any]) -> int:
    return R.TIER[dec["rule"]]


def finding(dec: dict[str, Any]) -> bool:
    return dec["kind"] in FINDING_KINDS


def _fresh(c: R.Case) -> R.Case:
    """An equal case built from new objects (no shared tuples or sets)."""

    def cp(lk: R.Lookup | None) -> R.Lookup | None:
        return None if lk is None else (str(lk[0]), str(lk[1]), bool(lk[2]))

    return R.Case(
        str(c.use),
        str(c.shape),
        frozenset(set(c.taint)),
        bool(c.multi),
        cp(c.d),
        cp(c.p),
        cp(c.q2),
        bool(c.wd),
        bool(c.wp),
        bool(c.w2),
        bool(c.coname),
    )


class Tally:
    def __init__(self) -> None:
        self.violations: Counter[str] = Counter()
        self.examples: dict[str, list[Any]] = {}
        self.checked: Counter[str] = Counter()
        self.profile: Counter[str] = Counter()

    def check(self, name: str, ok: bool, c: R.Case, detail: Any = None) -> None:
        self.checked[name] += 1
        if not ok:
            self.violations[name] += 1
            ex = self.examples.setdefault(name, [])
            if len(ex) < 3:
                ex.append({"case": c.key(), "detail": detail})


def kappa_of(c: R.Case) -> str | None:
    """SPEC 6.5 coherence, restated here so that the property checks do not reuse the model's own function (a mutant
    of the model's coherence cannot also blind the check)."""
    if c.shape != "PAIR":
        return None
    if c.wd or c.wp or c.w2:
        return "INCOMPATIBLE"
    if c.d is None or c.p is None or "unavailable" in (c.d[0], c.p[0]):
        return "NOT_DETERMINED"
    return "COHERENT" if c.coname else "UNDETERMINED"


def check_case(
    c: R.Case, dec: dict[str, Any], valid: bool, tally: Tally, deep: bool = True, decide: Any = R.decide
) -> None:
    """Check every per-case property. Only ``decide`` (the model under test) and ``A.valid`` are used from outside
    this module; guards are re-read only for the internal first-true consistency check."""
    kappa = kappa_of(c)
    L = c.deciding()
    lks = c.lookups()
    tally.check("TOTAL", dec["rule"] in R.RULES, c, dec)
    if valid:
        tally.check("P1_VALID_NO_FAILURE", dec["rule"] not in ("D-5", "D-17"), c, dec)
    else:
        tally.check("FAIL_CLOSED_INVALID", not finding(dec), c, dec)
    if deep:
        g = R.guards(c)
        first_true = min((i for i, r in enumerate(R.RULES) if g[r]), default=None)
        same = decide(_fresh(c)) == dec and first_true is not None and R.RULES[first_true] == dec["rule"]
        tally.check("DETERMINISM", same, c, dec)
    if c.shape == "PAIR" and c.use == "CITED" and kappa == "INCOMPATIBLE":
        # Valid inputs: always IDENTITY_CONFLICT. Invalid inputs: IDENTITY_CONFLICT or a fail-closed DETECT failure.
        ok = dec["class"] == "IDENTITY_CONFLICT" or (not valid and dec["kind"] == "failure")
        tally.check("IDENTITY_DOMINANCE", ok, c, dec)
    if kappa == "INCOMPATIBLE":
        tally.check("NO_FINDING_UNDER_CONFLICT", not finding(dec), c, dec)
    value_ok = dec.get("value") in (*R.POSITIVE_VALUES, "not_found_in_checked_sources", None)
    words = " ".join([str(dec.get("class")), str(dec.get("value")), *dec["reasons"]]).upper()
    tally.check("NO_NEGATIVE", value_ok and "NOT_RETRACTED" not in words and "CLEAN" not in words, c, dec)
    if dec["class"] == "NOT_FOUND_IN_CHECKED_SOURCES":
        ok = (
            c.use == "CITED"
            and c.shape != "NONE"
            and not c.taint
            and all(lk[0] not in ("unavailable", "invalid_query") for lk in c.lookups())
            and L == ("no_record", "unc:not_found", False)
        )
        tally.check("P5_NOT_FOUND_CONDITIONS", ok, c, dec)
    if any(lk[0] == "unavailable" for lk in c.lookups()):
        tally.check("FAILURE_CONTAINMENT", not finding(dec), c, dec)
    if dec["kind"] == "failure":
        tally.check("FAILURE_CONTAINMENT", dec["rule"] in ("D-5", "D-17"), c, dec)
    if L is not None and L[0] == "notice_only":
        tally.check("NOTICE_SEPARATION", not finding(dec), c, dec)
    if dec["class"] == "NOTICE_CITED":
        tally.check("NOTICE_SEPARATION", dec["value"] is None, c, dec)
    if dec["kind"] == "positive" and c.shape == "PAIR":
        if not (c.d is not None and c.p is not None):
            raise AssertionError("model invariant")
        if "notice_only" in (c.d[0], c.p[0]):
            tally.check("NOTICE_SEPARATION", "KEY_RESULTS_DIFFER" in dec["reasons"], c, dec)
    if dec["kind"] == "positive":
        ok = L is not None and L[0] == "matched" and L[1] == f"vf:{dec['value']}" and R.well_formed(L)
        tally.check("POSITIVE_FROM_DECIDING", ok, c, dec)
    if L is not None and (
        not R.well_formed(L) or L[1] in ("unc", "unc:bridge_only", "unc:ambiguous", "unc:gap", "conf") or L[2]
    ):
        tally.check("UNKNOWN_PRESERVATION", not finding(dec), c, dec)
    monotone = (
        any(lk[0] == "invalid_query" for lk in lks)
        or kappa == "INCOMPATIBLE"
        or any(lk[0] == "matched" and lk[1] == "conf" for lk in lks)
        or bool(c.taint)
        or any(lk[0] == "unavailable" for lk in lks)
    )
    if monotone:
        tally.check("MONOTONE_GUARDS", not finding(dec), c, dec)
    if dec["kind"] in ("abstain", "abstain_unavailable", "needs_resolution", "failure"):
        tally.check("AB2_REASONS", bool(dec["reasons"]), c, dec)
    if dec["kind"] != "failure":
        cls = dec["class"]
        ok = (
            dec["status"] == R.CLASS_STATUS[cls]
            and dec["disposition"] == R.DISPOSITION[cls]
            and (dec["value"] is not None)
            == (cls in R.POSITIVE_CLASS.values() or cls == "NOT_FOUND_IN_CHECKED_SOURCES")
        )
        tally.check("STATUS_CONSISTENCY", ok, c, dec)
    if valid and c.shape == "PAIR" and all(R.available(lk) for lk in (c.d, c.p, c.q2)):
        if not (c.q2 is not None):
            raise AssertionError("model invariant")
        tally.check("P2_VALID", (kappa == "INCOMPATIBLE") == (c.q2[0] == "ambiguous_identity"), c, dec)
    if not deep:
        return
    for r in R.TAINT_REASONS:
        if r not in c.taint:
            d2 = decide(replace(c, taint=c.taint | {r}))
            ok = tier(d2) <= tier(dec) and (finding(dec) or not finding(d2))
            tally.check("STRENGTHEN_TAINT", ok, c, {"add": r, "after": d2["rule"], "before": dec["rule"]})
    if c.shape == "PAIR":
        for bit in ("wd", "wp", "w2"):
            if not getattr(c, bit):
                c2 = replace(c, **{bit: True})
                d2 = decide(c2)
                ok = (finding(dec) or not finding(d2)) and (not (valid and A.valid(c2)) or tier(d2) <= tier(dec))
                tally.check("STRENGTHEN_WITNESS", ok, c, {"add": bit, "after": d2["rule"], "before": dec["rule"]})
    for slot in ("d", "p", "q2"):
        lk = getattr(c, slot)
        if lk is not None and lk[0] != "unavailable":
            # A lookup that fails shows no witness and no co-naming event any more (S-6.5 counts available lookups).
            c2 = replace(c, **{slot: UNAVAILABLE})
            if slot == "d":
                c2 = replace(c2, wd=False)
            elif slot == "p":
                c2 = replace(c2, wp=False)
            else:
                c2 = replace(c2, w2=False)
            if c2.coname and not any(R.available(x) for x in (c2.d, c2.p)):
                c2 = replace(c2, coname=False)
            d2 = decide(c2)
            tally.check("STRENGTHEN_UNAVAILABLE", finding(dec) or not finding(d2), c, {"slot": slot, "after": d2})


def profile_key(c: R.Case, dec: dict[str, Any], inv: list[str]) -> str:
    """A small description of the case for the summaries: lookup states, the full deciding lookup, kappa."""

    def lk(x: R.Lookup | None) -> str | None:
        return None if x is None else f"{x[0]}|{x[1]}|{int(x[2])}"

    states = [None if x is None else x[0] for x in (c.d, c.p, c.q2)]
    conf = any(x[1] == "conf" for x in c.lookups())
    return json.dumps(
        [
            not inv,
            inv,
            c.use,
            c.shape,
            sorted(c.taint),
            c.multi,
            states,
            lk(c.deciding()),
            conf,
            kappa_of(c),
            dec["rule"],
            dec["class"],
            dec["kind"],
            dec["reasons"],
        ],
        separators=(",", ":"),
    )


def run_chunk(args: tuple[str, str, int, bool]) -> dict[str, Any]:
    shape, use, t, deep = args
    tally = Tally()
    local: dict[str, int] = {}
    ids = array("H")
    rules = array("B")
    n_valid = 0
    for c in iter_chunk(shape, use, t):
        dec = R.decide(c)
        inv = A.invalid_reasons(c)
        valid = not inv
        n_valid += valid
        check_case(c, dec, valid, tally, deep)
        k = dkey(dec)
        ids.append(local.setdefault(k, len(local)))
        rules.append(R.RULES.index(dec["rule"]))
        # The profile drops the witness bits and (for PAIR) keeps lookups, so it stays small enough to ship.
        tally.profile[profile_key(c, dec, inv)] += 1
    return {
        "chunk": [shape, use, t],
        "n": len(ids),
        "n_valid": n_valid,
        "local": local,
        "ids": ids.tobytes(),
        "rules": rules.tobytes(),
        "violations": dict(tally.violations),
        "checked": dict(tally.checked),
        "examples": tally.examples,
        "profile": dict(tally.profile),
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_digest() -> str:
    """SHA-256 over the two modules that define the semantics (the table, the abstraction). The enumeration order is
    fixed by ``chunks`` and ``iter_chunk`` and covered by the table digest itself."""
    here = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for name in ("dt1_reference.py", "stage02_abstraction.py"):
        h.update(name.encode() + b"\0" + (here / name).read_bytes() + b"\0")
    return h.hexdigest()


def run(out: Path, oracle_dir: Path | None, workers: int, deep: bool = True) -> dict[str, Any]:
    started = time.monotonic()
    todo = [(s, u, t, deep) for s, u, t in chunks()]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_chunk, todo))
    all_keys = sorted({k for r in results for k in r["local"]})
    gid = {k: i for i, k in enumerate(all_keys)}
    table = array("H")
    violations: Counter[str] = Counter()
    checked: Counter[str] = Counter()
    examples: dict[str, list[Any]] = {}
    profile: Counter[str] = Counter()
    rule_arrays: dict[tuple[str, str, int], bytes] = {}
    per_shape: Counter[str] = Counter()
    per_shape_valid: Counter[str] = Counter()
    for r in results:
        remap = {v: gid[k] for k, v in r["local"].items()}
        local_ids = array("H")
        local_ids.frombytes(r["ids"])
        table.extend(remap[i] for i in local_ids)
        violations.update(r["violations"])
        checked.update(r["checked"])
        for k, v in r["examples"].items():
            examples.setdefault(k, []).extend(v[: 3 - len(examples.get(k, []))])
        profile.update(r["profile"])
        rule_arrays[tuple(r["chunk"])] = r["rules"]
        per_shape[r["chunk"][0]] += r["n"]
        per_shape_valid[r["chunk"][0]] += r["n_valid"]
    # TAINT_CLASS_INDEPENDENCE: for one shape and use, every non-empty taint subset gives the same rule per case.
    for shape in SHAPE_ORDER:
        for use in R.USES:
            nonempty = [rule_arrays[(shape, use, t)] for t in range(len(TAINTS)) if TAINTS[t]]
            same = all(x == nonempty[0] for x in nonempty)
            checked["TAINT_CLASS_INDEPENDENCE"] += 1
            if not same:
                violations["TAINT_CLASS_INDEPENDENCE"] += 1
    decisions = [json.loads(k) for k in all_keys]
    out.mkdir(parents=True, exist_ok=True)
    summary = summarize(profile, decisions, table, per_shape, per_shape_valid)
    summary["properties"] = {
        name: {
            "statement": PROPERTIES[name],
            "checked": checked.get(name, 0),
            "violations": violations.get(name, 0),
            "examples": examples.get(name, []),
        }
        for name in PROPERTIES
    }
    summary["deep"] = deep
    summary["elapsed_s"] = round(time.monotonic() - started, 1)
    summary["model_version"] = R.MODEL_VERSION
    summary["table_version"] = R.TABLE_VERSION
    summary["model_digest"] = model_digest()
    if oracle_dir is not None:
        summary["oracle"] = write_oracle(oracle_dir, decisions, table, per_shape)
    (out / "decision_space_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def write_oracle(
    oracle_dir: Path, decisions: list[dict[str, Any]], table: array, per_shape: Counter[str]
) -> dict[str, Any]:  # type: ignore[type-arg]
    oracle_dir.mkdir(parents=True, exist_ok=True)
    dec_path = oracle_dir / "dt1_decisions.json"
    dec_path.write_text(
        json.dumps(
            {"model_version": R.MODEL_VERSION, "table_version": R.TABLE_VERSION, "decisions": decisions},
            indent=0,
            sort_keys=True,
        )
        + "\n"
    )
    raw = table.tobytes() if sys.byteorder == "little" else _swap(table)
    tab_path = oracle_dir / "dt1_table.u16le.gz"
    with tab_path.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    manifest = {
        "oracle_version": "dt1-oracle/1",
        "model_version": R.MODEL_VERSION,
        "table_version": R.TABLE_VERSION,
        "model_digest": model_digest(),
        "encoding": "one little-endian uint16 per case, in the order of decision_space.chunks() and iter_chunk(); "
        "the value indexes dt1_decisions.json 'decisions'",
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "distinct_decisions": len(decisions),
        "table_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "files": {p.name: sha256_file(p) for p in (dec_path, tab_path)},
    }
    (oracle_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def _swap(table: array) -> bytes:  # type: ignore[type-arg]
    t = array("H", table)
    t.byteswap()
    return t.tobytes()


def summarize(
    profile: Counter[str],
    decisions: list[dict[str, Any]],
    table: array,  # type: ignore[type-arg]
    per_shape: Counter[str],
    per_shape_valid: Counter[str],
) -> dict[str, Any]:
    rule_valid: Counter[str] = Counter()
    rule_invalid: Counter[str] = Counter()
    class_valid: Counter[str] = Counter()
    kind_valid: Counter[str] = Counter()
    kind_invalid: Counter[str] = Counter()
    invalid_reason: Counter[str] = Counter()
    rule_shape_valid: Counter[str] = Counter()
    for key, n in profile.items():
        valid, inv, _use, shape, _taint, _multi, _states, _L, _conf, _kappa, rule, cls, kind, _reasons = json.loads(key)
        if valid:
            rule_valid[rule] += n
            class_valid[str(cls)] += n
            kind_valid[kind] += n
            rule_shape_valid[f"{rule}|{shape}"] += n
        else:
            rule_invalid[rule] += n
            kind_invalid[kind] += n
            for x in inv:
                invalid_reason[x] += n
    total = sum(per_shape.values())
    n_valid = sum(per_shape_valid.values())
    return {
        "cases": total,
        "cases_valid": n_valid,
        "cases_invalid": total - n_valid,
        "cases_per_shape": dict(per_shape),
        "valid_per_shape": dict(per_shape_valid),
        "rules_valid": dict(rule_valid),
        "rules_invalid": dict(rule_invalid),
        "rules_by_shape_valid": dict(rule_shape_valid),
        "classes_valid": dict(class_valid),
        "kinds_valid": dict(kind_valid),
        "kinds_invalid": dict(kind_invalid),
        "invalid_reasons": dict(invalid_reason),
        "distinct_decisions": len(decisions),
        "dimensions": dimensions(profile),
    }


def dimensions(profile: Counter[str]) -> dict[str, Any]:
    """Counts for the input dimensions the owner named (Step 4 item 2): cases, valid cases, rules and kinds."""

    def lk_state(x: str | None) -> str | None:
        return None if x is None else x.split("|")[0]

    def lk_shape(x: str | None) -> str | None:
        return None if x is None else x.split("|")[1]

    preds: dict[str, Any] = {
        "eligibility UNUSED": lambda r: r["use"] == "UNUSED",
        "eligibility USE_NOT_ESTABLISHED": lambda r: r["use"] == "USE_NOT_ESTABLISHED",
        "no identifier (NONE)": lambda r: r["shape"] == "NONE",
        "DOI only": lambda r: r["shape"] == "DOI",
        "PMID only": lambda r: r["shape"] == "PMID",
        "DOI+PMID coherent (kappa COHERENT)": lambda r: r["kappa"] == "COHERENT",
        "DOI+PMID uncorroborated (kappa UNDETERMINED)": lambda r: r["kappa"] == "UNDETERMINED",
        "DOI+PMID not determined (kappa NOT_DETERMINED)": lambda r: r["kappa"] == "NOT_DETERMINED",
        "DOI+PMID incompatible (kappa INCOMPATIBLE)": lambda r: r["kappa"] == "INCOMPATIBLE",
        "identifier malformed (taint)": lambda r: "IDENTIFIER_MALFORMED" in r["taint"],
        "identifier unconfirmed (taint)": lambda r: "IDENTIFIER_UNCONFIRMED" in r["taint"],
        "identifier role unresolved (taint)": lambda r: "IDENTIFIER_ROLE_UNRESOLVED" in r["taint"],
        "adapter inconsistency (invalid input)": lambda r: not r["valid"],
        "multiple co-reported identifiers": lambda r: r["multi"],
        "lookup matched (deciding)": lambda r: lk_state(r["L"]) == "matched",
        "lookup no record (deciding)": lambda r: lk_state(r["L"]) == "no_record",
        "lookup ambiguous identity (deciding)": lambda r: lk_state(r["L"]) == "ambiguous_identity",
        "lookup notice only (deciding)": lambda r: lk_state(r["L"]) == "notice_only",
        "lookup unavailable (any)": lambda r: "unavailable" in r["states"],
        "lookup invalid query (any)": lambda r: "invalid_query" in r["states"],
        "lookup unknown state (any)": lambda r: "unknown_state" in r["states"],
        "outcome verified retraction": lambda r: lk_shape(r["L"]) == "vf:retracted",
        "outcome expression of concern": lambda r: lk_shape(r["L"]) == "vf:expression_of_concern",
        "outcome correction": lambda r: lk_shape(r["L"]) == "vf:correction",
        "outcome reinstatement": lambda r: lk_shape(r["L"]) == "vf:reinstated",
        "outcome unresolved status": lambda r: lk_shape(r["L"]) in ("unc", "unc:bridge_only"),
        "outcome conflicting source evidence (any)": lambda r: r["conf"],
        "outcome coverage gap": lambda r: lk_shape(r["L"]) == "unc:gap",
        "PMID role collision (deciding)": lambda r: r["L"] is not None and r["L"].endswith("|1"),
    }
    out: dict[str, Any] = {}
    for name in preds:
        out[name] = {
            "cases": 0,
            "valid": 0,
            "rules_valid": Counter(),
            "kinds_valid": Counter(),
            "rules_invalid": Counter(),
            "kinds_invalid": Counter(),
        }
    for key, n in profile.items():
        valid, _inv, use, shape, taint, multi, states, L, conf, kappa, rule, _cls, kind, _reasons = json.loads(key)
        row = {
            "valid": valid,
            "use": use,
            "shape": shape,
            "taint": taint,
            "multi": multi,
            "kappa": kappa,
            "L": L,
            "states": [x for x in states if x is not None],
            "conf": conf,
        }
        for name, pred in preds.items():
            if pred(row):
                o = out[name]
                o["cases"] += n
                if valid:
                    o["valid"] += n
                    o["rules_valid"][rule] += n
                    o["kinds_valid"][kind] += n
                else:
                    o["rules_invalid"][rule] += n
                    o["kinds_invalid"][kind] += n
    for o in out.values():
        for k in ("rules_valid", "kinds_valid", "rules_invalid", "kinds_invalid"):
            o[k] = dict(sorted(o[k].items()))
    return out


def load_oracle(oracle_dir: Path) -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    decisions = json.loads((oracle_dir / "dt1_decisions.json").read_text())["decisions"]
    with gzip.open(oracle_dir / "dt1_table.u16le.gz", "rb") as gz:
        raw = gz.read()
    table = array("H")
    table.frombytes(raw)
    if sys.byteorder != "little":
        table.byteswap()
    return decisions, table


def chunk_offset(shape: str, use: str, t: int) -> int:
    off = 0
    for s, u, tt in chunks():
        if (s, u, tt) == (shape, use, t):
            return off
        off += chunk_size(s)
    raise KeyError((shape, use, t))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--oracle", type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--shallow", action="store_true", help="skip the strengthening and determinism checks")
    args = ap.parse_args()
    s = run(args.out, args.oracle, args.workers, deep=not args.shallow)
    bad = {k: v["violations"] for k, v in s["properties"].items() if v["violations"]}
    print(
        json.dumps(
            {
                "cases": s["cases"],
                "valid": s["cases_valid"],
                "invalid": s["cases_invalid"],
                "distinct_decisions": s["distinct_decisions"],
                "violations": bad,
                "elapsed_s": s["elapsed_s"],
            },
            indent=1,
        )
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
