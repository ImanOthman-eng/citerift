"""Fail-first evidence of the revised freeze-3 (owner decisions D-086 and D-087): the bib-2 corpus
(``../corpus/BIB2_CORPUS.json``) decided at detector level by the engine of a given checkout.

Usage: ``uv run python fail_first_dt4.py <checkout root> > decided.json``, where the checkout is a clean git worktree
of the engine's commit: 6663314 (dt-2, engine 0.3.0), c3854b8 (dt-3, engine 0.4.0, the freeze-3 candidate D-085 did
not accept) or this commit (dt-4, engine 0.5.0).

Each corpus case with a record is decided as a matched retracted-work DOI candidate, through the engine's own NORMALIZE
reading of the case's source (dt-2: none; dt-3: bib-1 ``cited_object``; dt-4: bib-2 ``describe``, which may be
UNAVAILABLE) and the checkout's own ``step9_support.concretize`` and reference ``Case``, so each engine sees the
inputs its own code would commit. The corpus is read from this repository; the engine, the support module and the
reference come from the checkout, which must have no uncommitted change in ``src``, ``schemas``, ``tests/stage04`` or
``simulations/stage04`` (``engine_source``). The output records the provenance of this repository (``fc_provenance``)
and the checkout's commit.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(sys.argv[1]).resolve()
HERE = Path(__file__).resolve().parent
CORPUS = HERE.parents[1] / "corpus" / "BIB2_CORPUS.json"
sys.path[:0] = [
    str(ROOT / "src"),
    str(ROOT / "tests" / "stage04"),
    str(ROOT / "simulations" / "stage04"),
    str(HERE.parents[1]),
]

import step9_support as S9  # noqa: E402
from fc_provenance import finish, start  # noqa: E402

import citerift.investigation as ci  # noqa: E402
from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.detector import dt1_detector  # noqa: E402

if not Path(ci.__file__).resolve().is_relative_to(ROOT / "src"):
    raise SystemExit(f"the engine was imported from {ci.__file__}, not from {ROOT / 'src'}")
if not Path(S9.__file__).resolve().is_relative_to(ROOT):
    raise SystemExit(f"step9_support was imported from {S9.__file__}, not from {ROOT}")

TABLE = dt1.TABLE_VERSION
B: Any = None  # the checkout's bibliographic module (dt-3 and dt-4; dt-2 has none)
if TABLE != "dt-2":
    B = importlib.import_module("citerift.investigation.bibliographic")
if TABLE == "dt-2":
    import dt2_reference as R
elif TABLE == "dt-3":
    import dt3_reference as R  # type: ignore[no-redef]
elif TABLE == "dt-4":
    import dt4_reference as R  # type: ignore[no-redef]
else:
    raise SystemExit(f"unexpected table {TABLE}")


class WithBib:
    """The abstract case with the unit's description: ``bib`` (dt-3 support: a (description, record) pair) or
    ``bib_pair`` (dt-4 support: a (description, record, unavailability reason) triple)."""

    def __init__(self, case: Any, cited: Any, record: Any, reason: str | None) -> None:
        self._case = case
        if TABLE == "dt-3":
            self.bib = (cited, record)
        elif TABLE == "dt-4":
            self.bib_pair = (cited, record, reason)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._case, name)


def source_bytes(case: dict[str, Any]) -> bytes:
    if case.get("source_bytes_hex"):
        return bytes.fromhex(case["source_bytes_hex"])
    return str(case["source"]).encode("utf-8")


def normalize(case: dict[str, Any]) -> tuple[Any, str | None]:
    """The unit's description (and dt-4 unavailability reason) as this engine's NORMALIZE computes it."""
    data = source_bytes(case)
    if TABLE == "dt-2":
        return None, None
    if TABLE == "dt-3":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return None, None
        cited = B.cited_object(text, case["wiki"])
        return (cited.to_json() if cited is not None else None), None
    described = B.describe(data, case["wiki"])
    if isinstance(described, B.Unavailable):
        return None, described.reason
    return described.to_json(), None


def engine_source() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607

    paths = ("src", "schemas", "tests/stage04", "simulations/stage04")
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *paths).splitlines()
    if any("__pycache__" not in line for line in dirty):
        raise SystemExit(f"the checkout {ROOT} has uncommitted changes")
    return {"commit": git("rev-parse", "HEAD").strip(), "checked_paths": list(paths), "uncommitted": []}


def main() -> None:
    prov = start(Path(__file__))
    engine = engine_source()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    out: dict[str, Any] = {"engine": ci.__version__, "table_version": TABLE, "cases": {}}
    for c in corpus:
        if B is None:
            record: Any = c["record"]  # dt-2 reads no record fields
        else:
            parsed = B.RecordObject.from_json(c["record"])
            record = dataclasses.asdict(parsed) if parsed is not None else None
        if record is None:
            continue
        cited, reason = normalize(c)
        base = R.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None)
        inp, _ = S9.concretize(WithBib(base, cited, record, reason))
        claim = dict(dt1_detector(inp).claims[0][0])
        out["cases"][c["id"]] = {
            "expect_object": c["expect"]["object"],
            "rule": claim["rule"],
            "class": claim["class"],
            "reasons": sorted(claim["reasons"]),
        }
    finish(prov, Path(__file__))
    if engine_source() != engine:
        raise SystemExit("the checkout changed while the tool ran")
    out["engine_source"] = engine
    out["provenance"] = prov
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
