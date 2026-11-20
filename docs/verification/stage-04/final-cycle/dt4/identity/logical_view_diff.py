"""Revised freeze-3 (owner decisions D-086 and D-087): the scientific-invariance baselines of owner decisions
D-053/D-054 and D-055 under the dt-4 Stage 04 identity (the dt-4 copy of ``final-cycle/identity/logical_view_diff.py``,
kept unchanged as the record of the c3854b8 candidate).

The logical-view tests (``tests/stage04/test_d053_d054.py``, ``test_d055.py``) pin digests of synthetic investigations
that carry the Stage 04 identity (engine, decision table and schema versions). dt-4 changes that identity (0.4.0 /
dt-3 / 5.0.0 to 0.5.0 / dt-4 / 6.0.0; candidate inputs 2.0.0 to 3.0.0; detector ``/4 (dt-3)`` to ``/5 (dt-4)``), so
the digests change. This script runs the same ``equivalence.py`` logical views in this tree and in a checkout of the
freeze-3 candidate c3854b8 (``--old``), with the same legacy-bundle substitution the tests make, and reports every leaf
that differs, so that the re-pinned digests are shown to differ **only** in identity values, in digests derived from
them, and in the order of lists sorted by such digests (claim ids include the table version), never in a class, rule,
reason, key, disposition, question or count.

The output records the provenance of ``fc_provenance`` for this tree, with the step 7 equivalence scripts in the
checked set, and the old checkout's head, which must have no uncommitted change (reviewer finding D-03).

Usage (from the repository root): ``uv run python -P docs/.../logical_view_diff.py --old <checkout of c3854b8> --out F``
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
SCRIPTS = {
    "d053": "docs/verification/stage-04/review/step7/d053/equivalence.py",
    "d055": "docs/verification/stage-04/review/step7/d055/equivalence.py",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
sys.path.insert(0, str(HERE.parents[1]))

from fc_provenance import finish, start  # noqa: E402

EXTRA = ("docs/verification/stage-04/review/step7",)


def child(root: Path, which: str) -> dict[str, Any]:
    """Run in a fresh interpreter whose citerift package is ``root``'s."""
    code = f"""
import importlib.util, json, sys
sys.path[:0] = [{str(root / "src")!r}, {str(root / "tests" / "stage04")!r}]
from memory_support import with_legacy_bundle  # noqa
import citerift
assert citerift.__file__.startswith({str(root)!r}), citerift.__file__
spec = importlib.util.spec_from_file_location("eq", {str(root / SCRIPTS[which])!r})
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out = {{}}
for name, sc in m.SCENARIOS.items():
    got = m.logical_view(name) if {which!r} == "d055" else m.logical_view(__import__('pathlib').Path({str(root)!r}), sc)
    out[name] = {{"view": got["view"], "counts": got["counts"], "digest": with_legacy_bundle(got["view"], m._canon)}}
print(json.dumps(out, sort_keys=True, default=str))
"""
    res = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False, cwd=root)  # noqa: S603
    if res.returncode:
        raise SystemExit(f"{which} in {root}: {res.stderr[-3000:]}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def leaves(x: Any, path: str = "") -> dict[str, Any]:
    if isinstance(x, dict):
        out: dict[str, Any] = {}
        for k, v in x.items():
            out.update(leaves(v, f"{path}/{k}"))
        return out
    if isinstance(x, list):
        out = {}
        for i, v in enumerate(x):
            out.update(leaves(v, f"{path}[{i}]"))
        return out
    return {path: x}


IDENTITY = {
    ("0.4.0", "0.5.0"),
    ("dt-3", "dt-4"),
    ("5.0.0", "6.0.0"),
    ("4.0.0", "5.0.0"),
    ("2.0.0", "3.0.0"),
    ("citerift-dt1-detector/4 (dt-3)", "citerift-dt1-detector/5 (dt-4)"),
}


def kind(a: Any, b: Any) -> str:
    if (a, b) in IDENTITY:
        return "identity_value"
    if isinstance(a, str) and isinstance(b, str) and HEX64.match(a) and HEX64.match(b):
        return "derived_digest"
    return "OTHER"


def normal(x: Any) -> Any:
    """The view with every identity value and every 64-hex digest replaced by a placeholder and every list sorted:
    what remains is the scientific content (classes, rules, reasons, keys, dispositions, question kinds, counts)."""
    ids = {v for pair in IDENTITY for v in pair}
    if isinstance(x, dict):
        return {k: normal(v) for k, v in x.items()}
    if isinstance(x, list):
        return sorted((normal(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))
    if isinstance(x, str) and HEX64.match(x):
        return "<digest>"
    if isinstance(x, str) and x in ids:
        return "<identity>"
    return x


def old_head(old: Path) -> str:
    """The commit of the old checkout, which must have no uncommitted change outside caches."""

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(old), *args], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607

    dirty = [x for x in git("status", "--porcelain", "--untracked-files=all").splitlines() if "__pycache__" not in x]
    if dirty:
        raise SystemExit(f"the old checkout {old} has uncommitted changes: {dirty[:5]}")
    return git("rev-parse", "HEAD").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    prov = start(Path(__file__), extra=EXTRA)
    head = old_head(a.old)
    report: dict[str, Any] = {"old_root_head": head, "scripts": {}}
    other = 0
    for which in SCRIPTS:
        old, new = child(a.old.resolve(), which), child(REPO, which)
        rows = {}
        for name in old:
            lo, ln = leaves(old[name]["view"]), leaves(new[name]["view"])
            diffs = [
                {"path": p, "old": lo.get(p), "new": ln.get(p), "kind": kind(lo.get(p), ln.get(p))}
                for p in sorted(set(lo) | set(ln))
                if lo.get(p) != ln.get(p)
            ]
            same_content = normal(old[name]["view"]) == normal(new[name]["view"])
            other += 0 if same_content else 1
            rows[name] = {
                "equal_modulo_identity_digests_and_order": same_content,
                "old_digest": old[name]["digest"],
                "new_digest": new[name]["digest"],
                "counts_equal": old[name]["counts"] == new[name]["counts"],
                "leaves": len(lo),
                "differing": len(diffs),
                "by_kind": {
                    k: sum(d["kind"] == k for d in diffs) for k in ("identity_value", "derived_digest", "OTHER")
                },
                "identity_paths": sorted(
                    {re.sub(r"\[\d+\]", "[]", d["path"]) for d in diffs if d["kind"] == "identity_value"}
                ),
                "other_leaves_before_reordering": [d for d in diffs if d["kind"] == "OTHER"],
            }
            other += 0 if rows[name]["counts_equal"] else 1
        report["scripts"][which] = rows
    report["only_identity_digests_and_order"] = other == 0
    finish(prov, Path(__file__), extra=EXTRA)
    if old_head(a.old) != head:
        raise SystemExit("the old checkout changed while the tool ran")
    report["provenance"] = prov
    a.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({w: {n: r["by_kind"] for n, r in rows.items()} for w, rows in report["scripts"].items()}, indent=1)
    )
    print("only identity values, derived digests and the order they induce:", other == 0)
    return 0 if other == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
