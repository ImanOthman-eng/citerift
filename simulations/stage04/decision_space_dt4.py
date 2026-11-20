"""The dt-4 abstract input domain, its oracle and its properties (owner decisions D-086 and D-087).

The **domain** is the dt-2 domain (``decision_space_dt2``: 25,264,896 cases) times the bibliographic state ``bib`` of
``dt4_reference.Case``: NONE (no event of the deciding lookup is in conflict or not established, and the check was
not unavailable), CONFLICT, UNAVAILABLE, NOT_ESTABLISHED: 101,059,584 cases. Within each chunk of
``decision_space.chunks()`` the cases come in the dt-2 order (``decision_space_dt2.iter_chunk``) with ``bib = NONE``,
then in the same order with CONFLICT, UNAVAILABLE and NOT_ESTABLISHED.

Checked over every case, against the **dt-2 oracle** (``oracle-dt2/``) and the **dt-3 oracle** (``oracle-dt3/``), not
against the model code of either:

- ``EQUIVALENCE_NONE_DT2`` and ``EQUIVALENCE_NONE_DT3``: with NONE the dt-4 decision is the dt-2 decision and the
  dt-3 decision without ``bc`` (property B5 of BIBLIOGRAPHIC_SPEC_2.md);
- ``EQUIVALENCE_CONFLICT_DT3``: with CONFLICT the dt-4 decision is the dt-3 decision with ``bc`` (D-13a unchanged);
- ``B4_NO_NEW_POSITIVE``: a dt-4 positive (D-14) only ever occurs with NONE, where dt-3 without ``bc`` gives the same
  positive (with the bib-2 property B4 on pairs, tested in ``test_final_bib2.py``, dt-4 never yields a positive dt-3
  would not);
- for UNAVAILABLE and NOT_ESTABLISHED, against the NONE twin (the dt-2 oracle's decision for the same case), the
  properties of ``PROPERTIES``: each changes a decision only where the twin is a D-14 positive, blocks every such
  positive with its own rule, class, status, value, disposition and reasons, and never creates or moves any other
  decision.

The decisions are written to the new oracle ``oracle-dt4/`` (one 16-bit decision index per case). The dt-1, dt-2 and
dt-3 oracles are read, never written.

Run: ``uv run python simulations/stage04/decision_space_dt4.py --out <dir> --oracle simulations/stage04/oracle-dt4``.
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
import decision_space_dt3 as DS3
import dt4_reference as R4

HERE = Path(__file__).resolve().parent
DT2_ORACLE = HERE / "oracle-dt2"
DT3_ORACLE = HERE / "oracle-dt3"
POSITIVE_RULE = "D-14"
PAIR_REASONS = DS2.PAIR_REASONS
STATES = ("NONE", "CONFLICT", "UNAVAILABLE", "NOT_ESTABLISHED")
EFFECT = {
    "CONFLICT": ("D-13a", "BIBLIOGRAPHIC_OBJECT_CONFLICT"),
    "UNAVAILABLE": ("D-13b", "BIBLIOGRAPHIC_CHECK_UNAVAILABLE"),
    "NOT_ESTABLISHED": ("D-13c", "BIBLIOGRAPHIC_OBJECT_NOT_ESTABLISHED"),
}

PROPERTIES = {
    "EQUIVALENCE_NONE_DT2": "with bib = NONE, the dt-4 decision is the dt-2 oracle's decision for the same case",
    "EQUIVALENCE_NONE_DT3": "with bib = NONE, the dt-4 decision is the dt-3 oracle's decision with bc = False",
    "EQUIVALENCE_CONFLICT_DT3": "with bib = CONFLICT, the dt-4 decision is the dt-3 oracle's decision with bc = True",
    "B4_NO_NEW_POSITIVE": "a dt-4 positive (D-14) occurs only with bib = NONE, and the dt-3 oracle (bc = False) gives "
    "the same positive",
    "BIB_TOTAL": "every case is decided by exactly one rule of dt-4",
    "BIB_NO_POSITIVE": "a case with bib other than NONE whose deciding lookup is matched never yields a positive",
    "BIB_ONLY_REMOVES_POSITIVES": "UNAVAILABLE and NOT_ESTABLISHED change a decision only where the NONE twin is a "
    "D-14 positive (D-1 to D-13 and D-15 to D-17 keep their place, class and reasons)",
    "BIB_EFFECT": "where UNAVAILABLE or NOT_ESTABLISHED changes a decision, the result is its rule (D-13b, D-13c), "
    "UNRESOLVED_IDENTITY, status uncertain, value null, disposition ABSTAIN, carrying its general reason and exactly "
    "the twin's pair reasons",
    "BIB_EVERY_POSITIVE_BLOCKED": "every dt-2 D-14 positive becomes D-13a, D-13b or D-13c under CONFLICT, UNAVAILABLE "
    "or NOT_ESTABLISHED respectively",
    "BIB_REASON_IFF": "each general bibliographic reason is a reason exactly when its state holds and the rule is its "
    "rule",
    "BIB_NO_NOTICE_OR_NOT_FOUND": "no bib state yields NOTICE_CITED or NOT_FOUND_IN_CHECKED_SOURCES that the twin "
    "lacks",
    "BIB_DETERMINISM": "deciding an equal case built from fresh objects gives an identical decision",
}

_ORACLES: dict[str, tuple[list[dict[str, Any]], array]] = {}  # type: ignore[type-arg]


def oracle(name: str) -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    if name not in _ORACLES:  # one load per worker process
        _ORACLES[name] = DS2.load_oracle(DT2_ORACLE) if name == "dt2" else DS3.load_oracle(DT3_ORACLE)
    return _ORACLES[name]


def to4(c: Any, bib: str) -> R4.Case:
    return R4.Case(c.use, c.shape, c.taint, c.multi, c.d, c.p, c.q2, c.wd, c.wp, c.w2, c.coname, c.rc, bib)


def iter_chunk(shape: str, use: str, t: int) -> Iterator[R4.Case]:
    for bib in STATES:
        for c in DS2.iter_chunk(shape, use, t):
            yield to4(c, bib)


def _fresh(c: R4.Case) -> R4.Case:
    def cp(lk: Any) -> Any:
        return None if lk is None else (str(lk[0]), str(lk[1]), bool(lk[2]))

    return R4.Case(
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
        str(c.bib),
    )


def check_case(c: R4.Case, dec: dict[str, Any], dt2: dict[str, Any], dt3: dict[str, Any], tally: DS.Tally) -> None:
    """``dt2``: the dt-2 oracle's decision for the case (the NONE twin); ``dt3``: the dt-3 oracle's decision with
    ``bc`` = (bib == CONFLICT)."""
    t: Any = tally
    t.check("BIB_TOTAL", dec["rule"] in R4.RULES, c, dec)
    t.check("BIB_DETERMINISM", R4.decide(_fresh(c)) == dec, c, dec)
    if dec["rule"] == POSITIVE_RULE:
        t.check("B4_NO_NEW_POSITIVE", c.bib == "NONE" and dt3 == dec, c, {"dt4": dec, "dt3": dt3})
    for state, (rule, reason) in EFFECT.items():
        has = reason in dec["reasons"]
        t.check("BIB_REASON_IFF", has == (c.bib == state and dec["rule"] == rule), c, dec)
    if c.bib == "NONE":
        t.check("EQUIVALENCE_NONE_DT2", dec == dt2, c, {"dt4": dec, "dt2": dt2})
        t.check("EQUIVALENCE_NONE_DT3", dec == dt3, c, {"dt4": dec, "dt3": dt3})
        return
    L = c.deciding()
    if L is not None and L[0] == "matched":
        t.check("BIB_NO_POSITIVE", not DS.finding(dec), c, dec)
    rule, reason = EFFECT[c.bib]
    if dt2["rule"] == POSITIVE_RULE:
        t.check("BIB_EVERY_POSITIVE_BLOCKED", dec["rule"] == rule, c, {"dt4": dec, "twin": dt2})
    ok = dec["class"] not in ("NOTICE_CITED", "NOT_FOUND_IN_CHECKED_SOURCES") or dec == dt2
    t.check("BIB_NO_NOTICE_OR_NOT_FOUND", ok, c, dec)
    if c.bib == "CONFLICT":
        t.check("EQUIVALENCE_CONFLICT_DT3", dec == dt3, c, {"dt4": dec, "dt3": dt3})
        return
    changed = dec != dt2
    t.check("BIB_ONLY_REMOVES_POSITIVES", not changed or dt2["rule"] == POSITIVE_RULE, c, {"dt4": dec, "twin": dt2})
    if changed:
        kept = sorted(r for r in dt2["reasons"] if r in PAIR_REASONS)
        ok = (
            dec["rule"] == rule
            and dec["class"] == "UNRESOLVED_IDENTITY"
            and dec["status"] == "uncertain"
            and dec["value"] is None
            and dec["disposition"] == "ABSTAIN"
            and dec["reasons"] == sorted([reason, *kept])
        )
        t.check("BIB_EFFECT", ok, c, {"dt4": dec, "twin": dt2})


def run_chunk(args: tuple[str, str, int]) -> dict[str, Any]:
    shape, use, t = args
    decisions2, table2 = oracle("dt2")
    decisions3, table3 = oracle("dt3")
    offset2 = DS2.chunk_offset(shape, use, t)
    offset3 = DS3.chunk_offset(shape, use, t)
    size2 = 2 * DS.chunk_size(shape)
    tally = DS.Tally()
    local: dict[str, int] = {}
    ids = array("H")
    rules: Counter[str] = Counter()
    for i, c in enumerate(iter_chunk(shape, use, t)):
        dec = R4.decide(c)
        j = i % size2
        dt2 = decisions2[table2[offset2 + j]]
        dt3 = decisions3[table3[offset3 + (size2 if c.bib == "CONFLICT" else 0) + j]]
        check_case(c, dec, dt2, dt3, tally)
        ids.append(local.setdefault(DS.dkey(dec), len(local)))
        rules[f"{c.bib}|{dec['rule']}"] += 1
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
    for name in ("dt4_reference.py", "stage02_abstraction.py"):
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
            for name, statement in PROPERTIES.items()
        },
        "model_version": R4.MODEL_VERSION,
        "table_version": R4.TABLE_VERSION,
        "model_digest": model_digest(),
        "dt2_oracle_manifest_sha256": sha256_file(DT2_ORACLE / "MANIFEST.json"),
        "dt3_oracle_manifest_sha256": sha256_file(DT3_ORACLE / "MANIFEST.json"),
        "elapsed_s": round(time.monotonic() - started, 1),
    }
    if oracle_dir is not None:
        summary["oracle"] = write_oracle(oracle_dir, decisions, table, per_shape)
    out.mkdir(parents=True, exist_ok=True)
    (out / "decision_space_dt4_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def write_oracle(
    oracle_dir: Path,
    decisions: list[dict[str, Any]],
    table: array,  # type: ignore[type-arg]
    per_shape: Counter[str],
) -> dict[str, Any]:
    oracle_dir.mkdir(parents=True, exist_ok=True)
    dec_path = oracle_dir / "dt4_decisions.json"
    dec_path.write_text(
        json.dumps(
            {"model_version": R4.MODEL_VERSION, "table_version": R4.TABLE_VERSION, "decisions": decisions},
            indent=0,
            sort_keys=True,
        )
        + "\n"
    )
    raw = table.tobytes() if sys.byteorder == "little" else DS._swap(table)
    tab_path = oracle_dir / "dt4_table.u16le.gz"
    with tab_path.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    manifest = {
        "oracle_version": "dt4-oracle/1",
        "model_version": R4.MODEL_VERSION,
        "table_version": R4.TABLE_VERSION,
        "model_digest": model_digest(),
        "dt2_oracle_manifest_sha256": sha256_file(DT2_ORACLE / "MANIFEST.json"),
        "dt3_oracle_manifest_sha256": sha256_file(DT3_ORACLE / "MANIFEST.json"),
        "encoding": "one little-endian uint16 per case, in the order of decision_space.chunks() and, within a chunk, "
        "decision_space_dt4.iter_chunk() (the dt-2 order with bib = NONE, then with CONFLICT, UNAVAILABLE and "
        "NOT_ESTABLISHED); the value indexes dt4_decisions.json 'decisions'",
        "cases": len(table),
        "cases_per_shape": dict(per_shape),
        "distinct_decisions": len(decisions),
        "table_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "files": {p.name: sha256_file(p) for p in (dec_path, tab_path)},
    }
    (oracle_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def load_oracle(oracle_dir: Path) -> tuple[list[dict[str, Any]], array]:  # type: ignore[type-arg]
    decisions = json.loads((oracle_dir / "dt4_decisions.json").read_text())["decisions"]
    with gzip.open(oracle_dir / "dt4_table.u16le.gz", "rb") as gz:
        raw = gz.read()
    table = array("H")
    table.frombytes(raw)
    if sys.byteorder != "little":
        table.byteswap()
    return decisions, table


def chunk_offset(shape: str, use: str, t: int) -> int:
    return 8 * DS.chunk_offset(shape, use, t)


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
