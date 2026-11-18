"""The dt-2 abstract input domain, its oracle and its properties (corrective cycle, owner decision D-071).

The **domain** is the frozen dt-1 domain (``decision_space``: 12,632,448 cases) times the bit ``rc`` of
``dt2_reference.Case`` (the deciding lookup holds a role-ambiguous event not covered by the PMID_ROLE_COLLISION bit):
25,264,896 cases. Within each chunk of ``decision_space.chunks()`` the cases come in the frozen order with ``rc =
False``, then in the same order with ``rc = True``.

Checked over every case, against the **frozen dt-1 oracle** (``oracle/``), not against the dt-1 model code:

- ``EQUIVALENCE_RC_FALSE``: with ``rc = False`` the dt-2 decision equals the frozen dt-1 oracle's decision;
- every per-case property of the frozen Step 4 checks (``decision_space.check_case``, shallow) on every case, with the
  frozen Stage 02 validity (``rc`` beside a deciding state other than matched is inert: see ``invalid_reasons``);
- the role-collision properties listed in ``PROPERTIES_RC``, comparing each ``rc = True`` case with its ``rc = False``
  twin.

The decisions are written to the new oracle ``oracle-dt2/`` (one 16-bit decision index per case). The frozen dt-1
oracle is read, never written.

Run: ``uv run python simulations/stage04/decision_space_dt2.py --out <dir> --oracle simulations/stage04/oracle-dt2``.
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
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import decision_space as DS
import dt2_reference as R2
import stage02_abstraction as A

HERE = Path(__file__).resolve().parent
DT1_ORACLE = HERE / "oracle"
LATER = ("D-10", "D-11", "D-12", "D-13", "D-14", "D-15", "D-16")  # rules a role collision may pre-empt (tier >= 5)

PROPERTIES_RC = {
    "EQUIVALENCE_RC_FALSE": "with rc = False, the dt-2 decision is the frozen dt-1 oracle's decision for the same case",
    "RC_NO_FINDING": "a case whose deciding lookup is matched and holds a role-ambiguous event (rc) never yields a "
    "positive finding or not-found",
    "RC_INERT_UNLESS_MATCHED": "rc changes nothing when the deciding lookup is not matched",
    "RC_PRECEDENCE": "rc never changes a decision of D-1 to D-9 (contract, identity conflict, contradiction, taint, "
    "ambiguity keep their place) and never moves a case to a later tier",
    "RC_EFFECT": "where rc changes a decision, the twin's rule was D-10 to D-16 and the result is D-10 "
    "UNRESOLVED_IDENTITY carrying IDENTIFIER_ROLE_COLLISION and the twin's pair reasons",
    "RC_REASON_IFF": "IDENTIFIER_ROLE_COLLISION is a reason exactly when rc holds and the rule is D-10",
    "RC_NO_NOTICE_FROM_COLLISION": "rc never yields NOTICE_CITED",
    "RC_DETERMINISM": "deciding an equal rc case built from fresh objects gives an identical decision",
}
PAIR_REASONS = ("KEY_RESULTS_DIFFER", "PAIR_UNCORROBORATED", "CO_REPORTED_MULTIPLE")

_DT1: tuple[list[dict[str, Any]], array] | None = None  # type: ignore[type-arg]


def dt1_oracle() -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    global _DT1  # noqa: PLW0603 - one load per worker process
    if _DT1 is None:
        _DT1 = DS.load_oracle(DT1_ORACLE)
    return _DT1


def to2(c: Any, rc: bool) -> R2.Case:
    return R2.Case(c.use, c.shape, c.taint, c.multi, c.d, c.p, c.q2, c.wd, c.wp, c.w2, c.coname, rc)


def iter_chunk(shape: str, use: str, t: int) -> Iterator[R2.Case]:
    for rc in (False, True):
        for c in DS.iter_chunk(shape, use, t):
            yield to2(c, rc)


def invalid_reasons(c: R2.Case) -> list[str]:
    """Stage 02 validity is that of the frozen abstraction. ``rc`` is a property of a matched deciding lookup (the
    production ``role_ambiguous`` is empty otherwise), so ``rc = True`` beside another deciding state encodes the same
    input as ``rc = False``; RC_INERT_UNLESS_MATCHED proves the model treats it so."""
    return A.invalid_reasons(c)  # type: ignore[arg-type]


def _fresh(c: R2.Case) -> R2.Case:
    def cp(lk: Any) -> Any:
        return None if lk is None else (str(lk[0]), str(lk[1]), bool(lk[2]))

    return R2.Case(
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
        bool(c.rc),
    )


def check_rc(c: R2.Case, dec: dict[str, Any], twin: dict[str, Any], tally: DS.Tally) -> None:
    L = c.deciding()
    matched = L is not None and L[0] == "matched"
    changed = dec != twin
    if matched:
        tally.check("RC_NO_FINDING", not DS.finding(dec), c, dec)  # type: ignore[arg-type]
    else:
        tally.check("RC_INERT_UNLESS_MATCHED", not changed, c, {"dt2": dec, "twin": twin})  # type: ignore[arg-type]
    early = twin["rule"] not in LATER
    ok = (not early or not changed) and (not changed or R2.TIER[dec["rule"]] <= R2.TIER[twin["rule"]])
    tally.check("RC_PRECEDENCE", ok, c, {"dt2": dec, "twin": twin})  # type: ignore[arg-type]
    if changed:
        kept = {r for r in twin["reasons"] if r in PAIR_REASONS}
        ok = (
            twin["rule"] in LATER
            and dec["rule"] == "D-10"
            and dec["class"] == "UNRESOLVED_IDENTITY"
            and "IDENTIFIER_ROLE_COLLISION" in dec["reasons"]
            and kept <= set(dec["reasons"])
        )
        tally.check("RC_EFFECT", ok, c, {"dt2": dec, "twin": twin})  # type: ignore[arg-type]
    tally.check("RC_NO_NOTICE_FROM_COLLISION", dec["class"] != "NOTICE_CITED" or twin == dec, c, dec)  # type: ignore[arg-type]
    tally.check("RC_DETERMINISM", R2.decide(_fresh(c)) == dec, c, dec)  # type: ignore[arg-type]


def run_chunk(args: tuple[str, str, int]) -> dict[str, Any]:
    shape, use, t = args
    decisions1, table1 = dt1_oracle()
    offset = DS.chunk_offset(shape, use, t)
    size = DS.chunk_size(shape)
    tally = DS.Tally()
    local: dict[str, int] = {}
    ids = array("H")
    n_valid = 0
    rules: Counter[str] = Counter()
    for i, c in enumerate(iter_chunk(shape, use, t)):
        dec = R2.decide(c)
        inv = invalid_reasons(c)
        valid = not inv
        n_valid += valid
        DS.check_case(c, dec, valid, tally, deep=False, decide=R2.decide)  # type: ignore[arg-type]
        twin = decisions1[table1[offset + (i % size)]]
        if not c.rc:
            tally.check("EQUIVALENCE_RC_FALSE", dec == twin, c, {"dt2": dec, "dt1": twin})  # type: ignore[arg-type]
        else:
            check_rc(c, dec, twin, tally)
        has = "IDENTIFIER_ROLE_COLLISION" in dec["reasons"]
        tally.check("RC_REASON_IFF", has == (c.rc and dec["rule"] == "D-10"), c, dec)  # type: ignore[arg-type]
        ids.append(local.setdefault(DS.dkey(dec), len(local)))
        rules[f"{'rc' if c.rc else 'no_rc'}|{'valid' if valid else 'invalid'}|{dec['rule']}"] += 1
    return {
        "chunk": [shape, use, t],
        "n": len(ids),
        "n_valid": n_valid,
        "local": local,
        "ids": ids.tobytes(),
        "violations": dict(tally.violations),
        "checked": dict(tally.checked),
        "examples": tally.examples,
        "rules": dict(rules),
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_digest() -> str:
    h = hashlib.sha256()
    for name in ("dt2_reference.py", "stage02_abstraction.py"):
        h.update(name.encode() + b"\0" + (HERE / name).read_bytes() + b"\0")
    return h.hexdigest()


def run(out: Path, oracle_dir: Path | None, workers: int) -> dict[str, Any]:
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_chunk, DS.chunks()))
    all_keys = sorted({k for r in results for k in r["local"]})
    gid = {k: i for i, k in enumerate(all_keys)}
    table = array("H")
    violations: Counter[str] = Counter()
    checked: Counter[str] = Counter()
    examples: dict[str, list[Any]] = {}
    rules: Counter[str] = Counter()
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
        rules.update(r["rules"])
        per_shape[r["chunk"][0]] += r["n"]
        per_shape_valid[r["chunk"][0]] += r["n_valid"]
    decisions = [json.loads(k) for k in all_keys]
    statements = {**{k: DS.PROPERTIES[k] for k in DS.PROPERTIES}, **PROPERTIES_RC}
    summary: dict[str, Any] = {
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "valid_per_shape": dict(per_shape_valid),
        "valid_per_shape_note": "valid cases of the dt-2 domain, rc = False and rc = True counted separately; rc = "
        "True beside a non-matched deciding lookup is valid and inert (reviewer finding A-09), so each frozen valid "
        "case is counted twice",
        "distinct_decisions": len(decisions),
        "rules": dict(sorted(rules.items())),
        "properties": {
            name: {
                "statement": statements[name],
                "checked": checked.get(name, 0),
                "violations": violations.get(name, 0),
                "examples": examples.get(name, []),
            }
            for name in statements
            if checked.get(name, 0) or name in PROPERTIES_RC
        },
        "not_rechecked_here": sorted(set(DS.PROPERTIES) - set(checked)),
        "model_version": R2.MODEL_VERSION,
        "table_version": R2.TABLE_VERSION,
        "model_digest": model_digest(),
        "dt1_oracle_manifest_sha256": sha256_file(DT1_ORACLE / "MANIFEST.json"),
        "elapsed_s": round(time.monotonic() - started, 1),
    }
    if oracle_dir is not None:
        summary["oracle"] = write_oracle(oracle_dir, decisions, table, per_shape)
    out.mkdir(parents=True, exist_ok=True)
    (out / "decision_space_dt2_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def write_oracle(
    oracle_dir: Path,
    decisions: list[dict[str, Any]],
    table: array,  # type: ignore[type-arg]
    per_shape: Counter[str],
) -> dict[str, Any]:
    oracle_dir.mkdir(parents=True, exist_ok=True)
    dec_path = oracle_dir / "dt2_decisions.json"
    dec_path.write_text(
        json.dumps(
            {"model_version": R2.MODEL_VERSION, "table_version": R2.TABLE_VERSION, "decisions": decisions},
            indent=0,
            sort_keys=True,
        )
        + "\n"
    )
    raw = table.tobytes() if sys.byteorder == "little" else DS._swap(table)
    tab_path = oracle_dir / "dt2_table.u16le.gz"
    with tab_path.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    manifest = {
        "oracle_version": "dt2-oracle/1",
        "model_version": R2.MODEL_VERSION,
        "table_version": R2.TABLE_VERSION,
        "model_digest": model_digest(),
        "frozen_dt1_oracle_manifest_sha256": sha256_file(DT1_ORACLE / "MANIFEST.json"),
        "encoding": "one little-endian uint16 per case, in the order of decision_space.chunks() and, within a chunk, "
        "decision_space_dt2.iter_chunk() (the frozen order with rc = False, then with rc = True); the value indexes "
        "dt2_decisions.json 'decisions'",
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "distinct_decisions": len(decisions),
        "table_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "files": {p.name: sha256_file(p) for p in (dec_path, tab_path)},
    }
    (oracle_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def load_oracle(oracle_dir: Path) -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    decisions = json.loads((oracle_dir / "dt2_decisions.json").read_text())["decisions"]
    with gzip.open(oracle_dir / "dt2_table.u16le.gz", "rb") as gz:
        raw = gz.read()
    table = array("H")
    table.frombytes(raw)
    if sys.byteorder != "little":
        table.byteswap()
    return decisions, table


def chunk_offset(shape: str, use: str, t: int) -> int:
    return 2 * DS.chunk_offset(shape, use, t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--oracle", type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args()
    s = run(args.out, args.oracle, args.workers)
    bad = {k: v["violations"] for k, v in s["properties"].items() if v["violations"]}
    print(json.dumps({"cases": s["cases"], "distinct_decisions": s["distinct_decisions"], "violations": bad,
                      "elapsed_s": s["elapsed_s"]}, indent=1))  # fmt: skip
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
