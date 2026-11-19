"""The dt-3 abstract input domain, its oracle and its properties (final corrective cycle, owner decision D-083).

The **domain** is the dt-2 domain (``decision_space_dt2``: 25,264,896 cases) times the bit ``bc`` of
``dt3_reference.Case`` (some event of the deciding lookup is in bib-1 MATERIAL_CONFLICT with the candidate's own
description): 50,529,792 cases. Within each chunk of ``decision_space.chunks()`` the cases come in the dt-2 order
(``decision_space_dt2.iter_chunk``) with ``bc = False``, then in the same order with ``bc = True``.

Checked over every case, against the **dt-2 oracle** (``oracle-dt2/``, itself checked against the frozen dt-1 oracle
and the frozen Step 4 properties), not against the dt-2 model code:

- ``EQUIVALENCE_BC_FALSE``: with ``bc = False`` the dt-3 decision equals the dt-2 oracle's decision (so every
  property established for dt-2 holds for these cases unchanged);
- the bibliographic properties listed in ``PROPERTIES_BC``, comparing each ``bc = True`` case with its ``bc = False``
  twin (the dt-2 oracle's decision for the same case).

The decisions are written to the new oracle ``oracle-dt3/`` (one 16-bit decision index per case). The dt-1 and dt-2
oracles are read, never written.

Run: ``uv run python simulations/stage04/decision_space_dt3.py --out <dir> --oracle simulations/stage04/oracle-dt3``.
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
import decision_space_dt2 as DS2
import dt3_reference as R3

HERE = Path(__file__).resolve().parent
DT2_ORACLE = HERE / "oracle-dt2"
POSITIVE_RULE = "D-14"
PAIR_REASONS = DS2.PAIR_REASONS

PROPERTIES_BC = {
    "EQUIVALENCE_BC_FALSE": "with bc = False, the dt-3 decision is the dt-2 oracle's decision for the same case",
    "BC_TOTAL": "every bc = True case is decided by exactly one rule of dt-3",
    "BC_NO_POSITIVE": "a case with bc whose deciding lookup is matched never yields a positive finding",
    "BC_ONLY_REMOVES_POSITIVES": "bc changes a decision only where the dt-2 twin is a D-14 positive (it never creates "
    "or moves any other decision: D-1 to D-13 and D-15 to D-17 keep their place, class and reasons)",
    "BC_EFFECT": "where bc changes a decision, the result is D-13a UNRESOLVED_IDENTITY, status uncertain, value null, "
    "disposition ABSTAIN, carrying BIBLIOGRAPHIC_OBJECT_CONFLICT and exactly the twin's pair reasons",
    "BC_EVERY_POSITIVE_BLOCKED": "every dt-2 D-14 positive becomes D-13a under bc",
    "BC_REASON_IFF": "BIBLIOGRAPHIC_OBJECT_CONFLICT is a reason exactly when bc holds and the rule is D-13a",
    "BC_NO_NOTICE_OR_NOT_FOUND": "bc never yields NOTICE_CITED or NOT_FOUND_IN_CHECKED_SOURCES that the twin lacks",
    "BC_DETERMINISM": "deciding an equal bc case built from fresh objects gives an identical decision",
}

_DT2: tuple[list[dict[str, Any]], array] | None = None  # type: ignore[type-arg]


def dt2_oracle() -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    global _DT2  # noqa: PLW0603 - one load per worker process
    if _DT2 is None:
        _DT2 = DS2.load_oracle(DT2_ORACLE)
    return _DT2


def to3(c: Any, bc: bool) -> R3.Case:
    return R3.Case(c.use, c.shape, c.taint, c.multi, c.d, c.p, c.q2, c.wd, c.wp, c.w2, c.coname, c.rc, bc)


def iter_chunk(shape: str, use: str, t: int) -> Iterator[R3.Case]:
    for bc in (False, True):
        for c in DS2.iter_chunk(shape, use, t):
            yield to3(c, bc)


def _fresh(c: R3.Case) -> R3.Case:
    def cp(lk: Any) -> Any:
        return None if lk is None else (str(lk[0]), str(lk[1]), bool(lk[2]))

    return R3.Case(
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
        bool(c.bc),
    )


def check_bc(c: R3.Case, dec: dict[str, Any], twin: dict[str, Any], tally: DS.Tally) -> None:
    L = c.deciding()
    changed = dec != twin
    tally.check("BC_TOTAL", dec["rule"] in R3.RULES, c, dec)  # type: ignore[arg-type]
    if L is not None and L[0] == "matched":
        tally.check("BC_NO_POSITIVE", not DS.finding(dec), c, dec)  # type: ignore[arg-type]
    only = not changed or twin["rule"] == POSITIVE_RULE
    tally.check("BC_ONLY_REMOVES_POSITIVES", only, c, {"dt3": dec, "twin": twin})  # type: ignore[arg-type]
    if twin["rule"] == POSITIVE_RULE:
        tally.check("BC_EVERY_POSITIVE_BLOCKED", dec["rule"] == "D-13a", c, {"dt3": dec, "twin": twin})  # type: ignore[arg-type]
    if changed:
        kept = sorted(r for r in twin["reasons"] if r in PAIR_REASONS)
        ok = (
            dec["rule"] == "D-13a"
            and dec["class"] == "UNRESOLVED_IDENTITY"
            and dec["status"] == "uncertain"
            and dec["value"] is None
            and dec["disposition"] == "ABSTAIN"
            and dec["reasons"] == sorted(["BIBLIOGRAPHIC_OBJECT_CONFLICT", *kept])
        )
        tally.check("BC_EFFECT", ok, c, {"dt3": dec, "twin": twin})  # type: ignore[arg-type]
    ok = dec["class"] not in ("NOTICE_CITED", "NOT_FOUND_IN_CHECKED_SOURCES") or dec == twin
    tally.check("BC_NO_NOTICE_OR_NOT_FOUND", ok, c, dec)  # type: ignore[arg-type]
    tally.check("BC_DETERMINISM", R3.decide(_fresh(c)) == dec, c, dec)  # type: ignore[arg-type]


def run_chunk(args: tuple[str, str, int]) -> dict[str, Any]:
    shape, use, t = args
    decisions2, table2 = dt2_oracle()
    offset2 = DS2.chunk_offset(shape, use, t)
    size2 = 2 * DS.chunk_size(shape)
    tally = DS.Tally()
    local: dict[str, int] = {}
    ids = array("H")
    rules: Counter[str] = Counter()
    for i, c in enumerate(iter_chunk(shape, use, t)):
        dec = R3.decide(c)
        twin = decisions2[table2[offset2 + (i % size2)]]
        if not c.bc:
            tally.check("EQUIVALENCE_BC_FALSE", dec == twin, c, {"dt3": dec, "dt2": twin})  # type: ignore[arg-type]
        else:
            check_bc(c, dec, twin, tally)
        has = "BIBLIOGRAPHIC_OBJECT_CONFLICT" in dec["reasons"]
        tally.check("BC_REASON_IFF", has == (c.bc and dec["rule"] == "D-13a"), c, dec)  # type: ignore[arg-type]
        ids.append(local.setdefault(DS.dkey(dec), len(local)))
        rules[f"{'bc' if c.bc else 'no_bc'}|{dec['rule']}"] += 1
    return {
        "chunk": [shape, use, t],
        "n": len(ids),
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
    for name in ("dt3_reference.py", "stage02_abstraction.py"):
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
    decisions = [json.loads(k) for k in all_keys]
    summary: dict[str, Any] = {
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "distinct_decisions": len(decisions),
        "rules": dict(sorted(rules.items())),
        "properties": {
            name: {
                "statement": statement,
                "checked": checked.get(name, 0),
                "violations": violations.get(name, 0),
                "examples": examples.get(name, []),
            }
            for name, statement in PROPERTIES_BC.items()
        },
        "model_version": R3.MODEL_VERSION,
        "table_version": R3.TABLE_VERSION,
        "model_digest": model_digest(),
        "dt2_oracle_manifest_sha256": sha256_file(DT2_ORACLE / "MANIFEST.json"),
        "elapsed_s": round(time.monotonic() - started, 1),
    }
    if oracle_dir is not None:
        summary["oracle"] = write_oracle(oracle_dir, decisions, table, per_shape)
    out.mkdir(parents=True, exist_ok=True)
    (out / "decision_space_dt3_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def write_oracle(
    oracle_dir: Path,
    decisions: list[dict[str, Any]],
    table: array,  # type: ignore[type-arg]
    per_shape: Counter[str],
) -> dict[str, Any]:
    oracle_dir.mkdir(parents=True, exist_ok=True)
    dec_path = oracle_dir / "dt3_decisions.json"
    dec_path.write_text(
        json.dumps(
            {"model_version": R3.MODEL_VERSION, "table_version": R3.TABLE_VERSION, "decisions": decisions},
            indent=0,
            sort_keys=True,
        )
        + "\n"
    )
    raw = table.tobytes() if sys.byteorder == "little" else DS._swap(table)
    tab_path = oracle_dir / "dt3_table.u16le.gz"
    with tab_path.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    manifest = {
        "oracle_version": "dt3-oracle/1",
        "model_version": R3.MODEL_VERSION,
        "table_version": R3.TABLE_VERSION,
        "model_digest": model_digest(),
        "dt2_oracle_manifest_sha256": sha256_file(DT2_ORACLE / "MANIFEST.json"),
        "encoding": "one little-endian uint16 per case, in the order of decision_space.chunks() and, within a chunk, "
        "decision_space_dt3.iter_chunk() (the dt-2 order with bc = False, then with bc = True); the value indexes "
        "dt3_decisions.json 'decisions'",
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "distinct_decisions": len(decisions),
        "table_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "files": {p.name: sha256_file(p) for p in (dec_path, tab_path)},
    }
    (oracle_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def load_oracle(oracle_dir: Path) -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    decisions = json.loads((oracle_dir / "dt3_decisions.json").read_text())["decisions"]
    with gzip.open(oracle_dir / "dt3_table.u16le.gz", "rb") as gz:
        raw = gz.read()
    table = array("H")
    table.frombytes(raw)
    if sys.byteorder != "little":
        table.byteswap()
    return decisions, table


def chunk_offset(shape: str, use: str, t: int) -> int:
    return 4 * DS.chunk_offset(shape, use, t)


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
