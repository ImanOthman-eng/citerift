"""RF-04 fail-first case: extraction configurations with wrong types or out-of-range values.

Runs ``citerift-wiki extract`` with each configuration on one SYNTHETIC bundle and prints the exit code and the
first line of stderr. Expected: every invalid configuration is refused with exit 3 (invalid input) before any work.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle

from citerift.wiki.cli import main

CONFIGS = [
    {"worker_wall_s": -1},
    {"worker_memory_mib": True},
    {"max_nodes": "400000"},
    {"max_depth": 0},
    {"worker_wall_s": float("nan")},
]
rows = []
with tempfile.TemporaryDirectory() as tmp:
    b = bundle(Path(tmp), "A<ref>{{cite journal |doi=10.1000/x}}</ref>\n")
    for n, cfg in enumerate(CONFIGS):
        cfg_path = Path(tmp) / f"c{n}.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        err = Path(tmp) / f"e{n}.txt"
        saved = sys.stderr, sys.stdout
        with err.open("w", encoding="utf-8") as e, open(Path(tmp) / f"o{n}.txt", "w", encoding="utf-8") as o:
            sys.stderr, sys.stdout = e, o
            try:
                code = main(
                    ["extract", "--bundle", str(b), "--out", str(Path(tmp) / f"x{n}.json"), "--config", str(cfg_path)]
                )
            finally:
                sys.stderr, sys.stdout = saved
        first = (err.read_text(encoding="utf-8").strip().splitlines() or [""])[0]
        first = first.replace(tmp, "<tmp>")
        rows.append({"config": json.dumps(cfg), "exit": code, "stderr": first[:160]})
print(json.dumps(rows, indent=1))
