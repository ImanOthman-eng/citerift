"""Freeze-3 candidate (owner decision D-083, item 13): a copy of
``freeze-2/performance/verification_components.py``, unchanged but for its paths; it runs on engine 0.4.0 (table dt-3).

Stage 04 Step 12, owner decision OD-S12-1 (D-064): the D-062 identity-verification profile by component, and the
read passes it makes over the index.

Times, in one warm process (the file in the page cache, as in the retained warm benchmark), each component of
``adapters.lookup.identity_verification_problems`` on the given index, then the bare SQLite scans that each component
repeats, so that the cost of the redundant read passes is measured separately from the computation done on the rows.
One extra run under ``cProfile`` gives the functions that dominate the two largest components. Nothing is cached
between components and no check is skipped: the script only calls the same Stage 02 functions the profile calls.

Run from the repository root on a quiet machine, offline:

    unshare -rn uv run python -P docs/verification/stage-04/freeze-3/performance/verification_components.py \
        --index <accepted index> --repeats 5 --out <json>
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import pstats
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def timed(fn: Callable[[], Any]) -> float:
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def scan(conn: Any, query: str) -> Callable[[], int]:
    def run() -> int:
        n = 0
        for _ in conn.execute(query):
            n += 1
        return n

    return run


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    from citerift.investigation.adapters import lookup as L
    from citerift.retraction import export
    from citerift.retraction.query import Index
    from citerift.retraction.store import manifest_path_for, structural_problems

    path = args.index.resolve()

    def file_sha256() -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        return h.hexdigest()

    with Index(path) as ix:
        conn = ix.conn
        manifest_path = manifest_path_for(path)
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        components: dict[str, Callable[[], Any]] = {
            "whole_profile (identity_verification_problems)": lambda: L.identity_verification_problems(ix),
            "structural: PRAGMA integrity_check": lambda: conn.execute("PRAGMA integrity_check").fetchall(),
            "structural: PRAGMA foreign_key_check": lambda: conn.execute("PRAGMA foreign_key_check").fetchall(),
            "structural_problems (all of the above + invariants)": lambda: structural_problems(conn),
            "compute_digests": lambda: export.compute_digests(conn),
            "manifest_problems": lambda: export.manifest_problems(meta, manifest),
            "derivation_problems": lambda: export.derivation_problems(conn),
        }
        scans: dict[str, Callable[[], Any]] = {
            "file read + SHA-256 (I/O floor of one full pass)": file_sha256,
            "scan raw_record (digests: record lines)": scan(
                conn,
                "SELECT ordinal, line_start, line_end, record_id, fields, row_sha256, disposition, reasons "
                "FROM raw_record ORDER BY ordinal",
            ),
            "scan event JOIN raw_record (digests: event lines)": scan(
                conn,
                f"SELECT {', '.join('e.' + c for c in export.EVENT_COLUMNS)}, r.fields FROM event e "  # noqa: S608
                "JOIN raw_record r ON r.ordinal = e.ordinal ORDER BY e.ordinal",
            ),
            "scan raw_record SELECT * (derivation)": scan(conn, "SELECT * FROM raw_record ORDER BY ordinal"),
            "scan ident (derivation)": scan(
                conn,
                "SELECT ordinal, role, scheme, column_name, raw, input_form, norm, missing, transformations, issues "
                "FROM ident ORDER BY ordinal, id",
            ),
            "scan event ORDER BY event_id (derivation compare)": scan(
                conn,
                f"SELECT {', '.join(export.EVENT_COLUMNS)} FROM event ORDER BY event_id",  # noqa: S608
            ),
            "scan title_token (derivation compare)": scan(
                conn, "SELECT token, event_id FROM title_token ORDER BY token, event_id"
            ),
        }
        rows = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608 - fixed table names
            for t in ("raw_record", "event", "ident", "notice", "title_token", "token_df", "dup_group")
        }
        L.identity_verification_problems(ix)  # warm-up: page cache and imports
        samples: dict[str, list[float]] = {k: [] for k in [*components, *scans]}
        for _ in range(args.repeats):
            for name, fn in [*components.items(), *scans.items()]:
                samples[name].append(timed(fn))
        prof = cProfile.Profile()
        prof.enable()
        L.identity_verification_problems(ix)
        prof.disable()
    stats = pstats.Stats(prof)
    top = []
    for (file, line, func), (_cc, nc, tt, ct, _callers) in sorted(
        stats.stats.items(),  # type: ignore[attr-defined]
        key=lambda kv: kv[1][3],
        reverse=True,
    )[:30]:
        top.append({"function": f"{Path(file).name}:{line}:{func}", "calls": nc, "tottime_s": tt, "cumtime_s": ct})
    out = {
        "label": "Stage 04 Step 12 (D-064, OD-S12-1): the D-062 identity-verification profile by component and the "
        "read passes it makes; warm single process; not an evaluation",
        "python": sys.version.split()[0],
        "index_bytes": path.stat().st_size,
        "rows": rows,
        "repeats": args.repeats,
        "median_s": {k: round(statistics.median(v), 3) for k, v in samples.items()},
        "min_s": {k: round(min(v), 3) for k, v in samples.items()},
        "samples_s": {k: [round(x, 3) for x in v] for k, v in samples.items()},
        "cprofile_top_cumulative": top,
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in out["median_s"].items():
        print(f"{v:8.3f} s  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
