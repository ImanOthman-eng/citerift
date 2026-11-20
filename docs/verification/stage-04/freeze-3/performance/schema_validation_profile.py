"""Freeze-3 candidate (owner decision D-083, item 13): a copy of
``freeze-2/performance/schema_validation_profile.py``, unchanged but for its paths; engine 0.4.0 (dt-3).

Stage 04 Step 12, owner section 13: where JSON Schema validation time goes in one production investigation.

One ``citerift-investigate run`` in this process (run it offline: ``unshare -rn``) with every validator call timed
per schema: total, number of calls, the first call and the mean of the later calls. ``schemas._validator`` and
``_ref_validator`` are already process-local caches (``functools.cache``), so a validator is built once per schema
per process; if the first call of a schema were much slower than its later calls, construction or lazy
initialisation would be material and a compiled-validator cache could help. Nothing that runs is changed: the
timers only wrap ``iter_errors``.

    unshare -rn uv run python docs/verification/stage-04/freeze-3/performance/schema_validation_profile.py \\
        --out FILE run --bundle BUNDLE --index INDEX --memory-root EMPTY_PRIVATE_DIR
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


def main(argv: list[str]) -> int:
    if argv[:1] != ["--out"] or len(argv) < 3:
        raise SystemExit("usage: --out FILE run ...")
    out_path, cli_argv = Path(argv[1]), argv[2:]
    from citerift.investigation import cli, schemas

    calls: dict[str, list[float]] = defaultdict(list)
    built: dict[str, float] = {}
    v, rv = schemas._validator, schemas._ref_validator

    class Timed:
        def __init__(self, inner: Any, key: str) -> None:
            self.inner, self.key = inner, key

        def iter_errors(self, instance: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return list(self.inner.iter_errors(instance))
            finally:
                calls[self.key].append(time.perf_counter() - t0)

    def wrap(factory: Any) -> Any:
        def get(key: str) -> Timed:
            t0 = time.perf_counter()
            inner = factory(key)
            built[key] = built.get(key, 0.0) + time.perf_counter() - t0
            return Timed(inner, key)

        return get

    schemas._validator = wrap(v)
    schemas._ref_validator = wrap(rv)
    t0 = time.perf_counter()
    code = cli.main(cli_argv)
    run_s = time.perf_counter() - t0
    rows = []
    for key, xs in sorted(calls.items(), key=lambda kv: -sum(kv[1])):
        rest = xs[1:]
        rows.append(
            {
                "schema": key,
                "calls": len(xs),
                "total_s": round(sum(xs), 4),
                "first_s": round(xs[0], 4),
                "later_mean_s": round(sum(rest) / len(rest), 4) if rest else None,
            }
        )
    total = sum(sum(xs) for xs in calls.values())
    firsts = sum(xs[0] for xs in calls.values())
    later = sum(sum(xs[1:]) / len(xs[1:]) for xs in calls.values() if len(xs) > 1)
    result = {
        "exit_code": code,
        "run_s": round(run_s, 3),
        "validation_s": round(total, 3),
        "validator_lookups_s": round(sum(built.values()), 4),
        "calls": sum(len(xs) for xs in calls.values()),
        "first_calls_s": round(firsts, 3),
        "first_call_excess_s": round(firsts - later, 3),
        "note": "first_call_excess_s estimates construction and lazy initialisation: the first call of each schema "
        "minus that schema's later mean (schemas with one call count fully)",
        "by_schema": rows,
    }
    out_path.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    sys.stderr.write(json.dumps({k: result[k] for k in result if k != "by_schema"}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
